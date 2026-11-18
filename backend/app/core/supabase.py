"""Acesso ao Supabase: Auth (GoTrue) e banco (PostgREST), via HTTP.

Decisão de segurança: o backend usa APENAS a chave pública (anon) + o JWT do usuário
logado em cada chamada. Assim o PostgreSQL aplica as políticas RLS de verdade e
nenhuma chave de serviço (service_role) precisa existir na aplicação.
"""
import hashlib
import logging
import re
import time
from dataclasses import dataclass

import httpx

from app.core.config import Settings
from app.core.errors import AppError

log = logging.getLogger("gtech.supabase")

Filter = tuple[str, str]  # ("status", "eq.new")

NOT_READY_MSG = (
    "As tabelas do banco ainda não foram criadas ou estão sem permissão. "
    "Execute database/schema.sql e depois database/policies.sql no SQL Editor do Supabase."
)

_DUPLICATE_MESSAGES = {
    "uq_leads_owner_company_city": "Já existe um lead com este nome de empresa nesta cidade.",
    "uq_leads_owner_phone": "Já existe um lead cadastrado com este telefone.",
    "uq_leads_owner_whatsapp": "Já existe um lead cadastrado com este WhatsApp.",
    "uq_leads_owner_website": "Já existe um lead cadastrado com este site.",
}


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str
    token: str
    full_name: str | None = None


def unreachable() -> AppError:
    return AppError(
        503,
        "supabase_unreachable",
        "Não foi possível conectar ao Supabase. Verifique SUPABASE_URL, sua conexão com a internet e se o projeto está ativo.",
    )


def _json(res: httpx.Response) -> dict:
    try:
        data = res.json()
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


class SupabaseAuth:
    """Autenticação via Supabase Auth."""

    def __init__(self, settings: Settings, http: httpx.AsyncClient):
        self._s = settings
        self._http = http
        self._cache: dict[str, tuple[float, AuthUser]] = {}

    @property
    def _headers(self) -> dict[str, str]:
        return {"apikey": self._s.supabase_anon_key}

    async def _post(self, path: str, **kwargs) -> httpx.Response:
        try:
            return await self._http.post(f"{self._s.supabase_base_url}/auth/v1{path}", headers=self._headers, **kwargs)
        except httpx.RequestError as exc:
            log.warning("Supabase Auth inacessível: %s", exc)
            raise unreachable() from exc

    @staticmethod
    def _session(data: dict) -> dict:
        user = data.get("user") or {}
        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in", 3600),
            "user": {"id": user.get("id"), "email": user.get("email")},
        }

    async def sign_in(self, email: str, password: str) -> dict:
        res = await self._post("/token", params={"grant_type": "password"}, json={"email": email, "password": password})
        if res.status_code == 200:
            return self._session(res.json())
        data = _json(res)
        text = f"{data.get('error_code', '')} {data.get('msg', '')} {data.get('error_description', '')}".lower()
        if res.status_code == 429 or "rate" in text:
            raise AppError(429, "too_many_attempts", "Muitas tentativas de login. Aguarde alguns minutos e tente novamente.")
        if "not confirmed" in text:
            raise AppError(401, "email_not_confirmed", "Confirme seu e-mail antes de entrar (veja a caixa de entrada).")
        if res.status_code in (400, 401, 403, 422):
            raise AppError(401, "invalid_credentials", "E-mail ou senha incorretos.")
        if res.status_code in (404, 502, 503):
            raise AppError(503, "supabase_error", "O Supabase não respondeu como esperado. Confira SUPABASE_URL e SUPABASE_ANON_KEY.")
        log.error("Falha inesperada no login: %s %s", res.status_code, res.text[:300])
        raise AppError(502, "auth_error", "Não foi possível autenticar no momento. Tente novamente.")

    async def refresh(self, refresh_token: str) -> dict:
        res = await self._post("/token", params={"grant_type": "refresh_token"}, json={"refresh_token": refresh_token})
        if res.status_code == 200:
            return self._session(res.json())
        if res.status_code >= 500:
            raise AppError(502, "auth_error", "Não foi possível renovar a sessão agora.")
        raise AppError(401, "session_expired", "Sua sessão expirou. Entre novamente.")

    async def sign_out(self, token: str) -> None:
        self._cache.pop(self._key(token), None)
        try:
            await self._http.post(
                f"{self._s.supabase_base_url}/auth/v1/logout",
                params={"scope": "local"},  # encerra só esta sessão (o padrão "global" deslogaria todos os dispositivos)
                headers={**self._headers, "Authorization": f"Bearer {token}"},
            )
        except httpx.RequestError:
            pass  # o frontend já descartou o token

    @staticmethod
    def _key(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    async def verify(self, token: str) -> AuthUser:
        """Valida o JWT consultando o Supabase (funciona com qualquer algoritmo de assinatura)."""
        key = self._key(token)
        hit = self._cache.get(key)
        if hit and hit[0] > time.monotonic():
            return hit[1]
        try:
            res = await self._http.get(
                f"{self._s.supabase_base_url}/auth/v1/user",
                headers={**self._headers, "Authorization": f"Bearer {token}"},
            )
        except httpx.RequestError as exc:
            log.warning("Supabase Auth inacessível: %s", exc)
            raise unreachable() from exc
        if res.status_code in (401, 403):
            raise AppError(401, "session_expired", "Sua sessão expirou. Entre novamente.")
        if res.status_code != 200:
            raise AppError(502, "auth_error", "Não foi possível validar sua sessão agora.")
        data = res.json()
        meta = data.get("user_metadata") or {}
        user = AuthUser(id=data["id"], email=data.get("email") or "", token=token, full_name=meta.get("full_name"))
        if len(self._cache) > 500:
            self._cache.clear()
        self._cache[key] = (time.monotonic() + 30, user)  # cache curto: evita 1 chamada ao Auth por requisição
        return user


class Database:
    """Cliente mínimo do PostgREST, executado em nome de um usuário (JWT dele)."""

    def __init__(self, settings: Settings, http: httpx.AsyncClient, token: str):
        self._base = f"{settings.supabase_base_url}/rest/v1"
        self._http = http
        self._headers = {
            "apikey": settings.supabase_anon_key,
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    async def _request(self, method: str, table: str, *, params=None, json=None, prefer: str | None = None) -> httpx.Response:
        headers = dict(self._headers)
        if prefer:
            headers["Prefer"] = prefer
        try:
            res = await self._http.request(method, f"{self._base}/{table}", params=params, json=json, headers=headers)
        except httpx.RequestError as exc:
            log.warning("PostgREST inacessível: %s", exc)
            raise unreachable() from exc
        if res.status_code >= 400:
            raise self._to_error(res)
        return res

    @staticmethod
    def _to_error(res: httpx.Response) -> AppError:
        data = _json(res)
        code = str(data.get("code", ""))
        text = f"{data.get('message', '')} {data.get('details', '')}"
        log.warning("Erro do banco %s [%s]: %s", res.status_code, code, text[:300])

        if res.status_code == 401 or code in {"PGRST301", "PGRST303"} or "jwt" in text.lower():
            return AppError(401, "session_expired", "Sua sessão expirou. Entre novamente.")
        if code == "23505":
            for constraint, message in _DUPLICATE_MESSAGES.items():
                if constraint in text:
                    return AppError(409, "duplicate_lead", message)
            return AppError(409, "duplicate", "Já existe um registro com estes dados.")
        if code in {"23514", "22P02", "22001", "22023"}:
            return AppError(422, "invalid_data", "Algum dado informado não é aceito pelo banco. Revise os campos e tente novamente.")
        if code == "23503":
            return AppError(409, "reference_error", "O registro relacionado não existe mais.")
        if code == "42501" and "row-level security" in text:
            table = re.search(r'table "([^"]+)"', text)
            return AppError(
                503, "database_policy_missing",
                f"O banco recusou a gravação em \"{table.group(1) if table else 'uma tabela'}\" por falta de política de segurança (RLS). "
                "Execute novamente o arquivo database/policies.sql no SQL Editor do Supabase.",
            )
        if code in {"PGRST205", "PGRST200", "42P01", "42501"} or res.status_code in (403, 404):
            return AppError(503, "database_not_ready", NOT_READY_MSG)
        return AppError(502, "database_error", "O banco de dados retornou um erro inesperado. Tente novamente.")

    async def select(
        self,
        table: str,
        *,
        columns: str = "*",
        filters: list[Filter] | None = None,
        order: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        count: bool = False,
    ) -> tuple[list[dict], int | None]:
        params: list[Filter] = [("select", columns), *(filters or [])]
        if order:
            params.append(("order", order))
        if limit is not None:
            params.append(("limit", str(limit)))
        if offset:
            params.append(("offset", str(offset)))
        res = await self._request("GET", table, params=params, prefer="count=exact" if count else None)
        total = None
        if count:
            m = re.search(r"/(\d+|\*)$", res.headers.get("content-range", ""))
            total = int(m.group(1)) if m and m.group(1) != "*" else None
        return res.json(), total

    async def select_all(
        self,
        table: str,
        *,
        columns: str = "*",
        filters: list[Filter] | None = None,
        order: str | None = None,
        page_size: int = 1000,
        max_rows: int = 50_000,
    ) -> list[dict]:
        """Lê todas as linhas, em páginas (o PostgREST limita cada resposta)."""
        rows: list[dict] = []
        offset = 0
        while len(rows) < max_rows:
            batch, _ = await self.select(table, columns=columns, filters=filters, order=order, limit=page_size, offset=offset)
            rows.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
        return rows[:max_rows]

    async def insert(self, table: str, row: dict) -> dict:
        res = await self._request("POST", table, json=row, prefer="return=representation")
        data = res.json()
        return data[0] if isinstance(data, list) and data else {}

    async def update(self, table: str, values: dict, filters: list[Filter]) -> list[dict]:
        res = await self._request("PATCH", table, params=filters, json=values, prefer="return=representation")
        return res.json()

    async def delete(self, table: str, filters: list[Filter]) -> list[dict]:
        res = await self._request("DELETE", table, params=filters, prefer="return=representation")
        return res.json()
