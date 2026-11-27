"""Supabase falso (Auth + PostgREST) em memória, usado APENAS nos testes.

Implementa, no nível HTTP (httpx.MockTransport), o subconjunto do PostgREST que a
aplicação usa: filtros eq/neq/ilike/in/not.in/gte/lte/or, order, limit/offset,
Prefer count=exact, return=representation, embed "lead:leads(...)".
Emula também: RLS (cada usuário só vê as próprias linhas), os índices únicos de
database/schema.sql e os triggers de updated_at / status_updated_at.
"""
import json
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlsplit

import httpx

SUPABASE_URL = "https://fake-project.supabase.co"
ANON_KEY = "anon-key-for-tests"

TABLES = ("leads", "lead_activities", "prospecting_searches", "users", "outreach_messages")
OWNED = ("leads", "lead_activities", "prospecting_searches", "outreach_messages")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class FakeSupabase:
    def __init__(self):
        self.users: dict[str, dict] = {}  # email -> {id, password}
        self.tokens: dict[str, str] = {}  # access_token -> user id
        self.refresh_tokens: dict[str, str] = {}  # refresh_token -> user id
        self.rows: dict[str, list[dict]] = {t: [] for t in TABLES}
        self.requests: list[tuple[str, str]] = []
        self.auth_calls = 0  # chamadas a /auth/v1/user (testa o cache)
        self.fail_with: httpx.RequestError | None = None
        self.missing_tables = False
        self.agent_handler = lambda request: httpx.Response(200, json={"leads": []})
        self.overpass_handler = lambda request: httpx.Response(200, json={"elements": []})  # OpenStreetMap simulado
        self.nominatim_handler = lambda request: httpx.Response(200, json=[{"osm_type": "relation", "osm_id": 123, "category": "boundary", "type": "administrative"}])
        self.places_handler = lambda request: httpx.Response(200, json={})  # Google Places simulado
        self.web_handler = lambda request: httpx.Response(404)  # sites das empresas (domínios *.example)
        self.whatsmcp_calls: list[dict] = []

        def whatsmcp(request: httpx.Request):  # WhatsMCP simulado: wa_send_message sempre "sent"
            body = json.loads(request.content)
            self.whatsmcp_calls.append({"auth": request.headers.get("authorization"), "args": body["params"]["arguments"]})
            out = {"status": "sent", "message_id": "ABC"}
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": json.dumps(out)}], "structuredContent": out}})

        self.whatsmcp_handler = whatsmcp
        self.anthropic_handler = lambda request: httpx.Response(200, json={"content": [{"type": "text", "text": "Olá! Mensagem da IA."}]})

    # ------------------------------------------------------------------ helpers
    def add_user(self, email: str, password: str = "senha-segura") -> str:
        uid = str(uuid.uuid4())
        self.users[email] = {"id": uid, "password": password}
        return uid

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handle))

    def _issue(self, uid: str) -> dict:
        access, refresh = f"at-{uuid.uuid4()}", f"rt-{uuid.uuid4()}"
        self.tokens[access] = uid
        self.refresh_tokens[refresh] = uid
        email = next(e for e, u in self.users.items() if u["id"] == uid)
        return {"access_token": access, "refresh_token": refresh, "expires_in": 3600, "user": {"id": uid, "email": email}}

    def login(self, email: str, password: str = "senha-segura") -> str:
        return self._issue(self.users[email]["id"])["access_token"]

    # ------------------------------------------------------------------ dispatch
    def handle(self, request: httpx.Request) -> httpx.Response:
        if self.fail_with:
            raise self.fail_with
        url = urlsplit(str(request.url))
        self.requests.append((request.method, url.path))
        if url.hostname == "agent.test":  # agente de prospecção simulado (testes do provedor HTTP)
            return self.agent_handler(request)
        if url.hostname == "nominatim.openstreetmap.org":
            return self.nominatim_handler(request)
        if url.hostname in ("overpass-api.de", "overpass.kumi.systems"):
            return self.overpass_handler(request)
        if url.hostname == "api.whatsmcp.com":
            return self.whatsmcp_handler(request)
        if url.hostname == "api.anthropic.com":
            return self.anthropic_handler(request)
        if url.hostname == "places.googleapis.com":
            return self.places_handler(request)
        if url.hostname and url.hostname.endswith(".example"):
            return self.web_handler(request)
        if request.headers.get("apikey") != ANON_KEY:
            return httpx.Response(401, json={"message": "No API key found in request"})
        if url.path.startswith("/auth/v1"):
            return self._auth(request, url)
        if url.path.startswith("/rest/v1/"):
            return self._rest(request, url)
        return httpx.Response(404, json={})

    # ---------------------------------------------------------------------- Auth
    def _bearer_uid(self, request) -> str | None:
        return self.tokens.get(request.headers.get("authorization", "").removeprefix("Bearer ").strip())

    def _auth(self, request: httpx.Request, url) -> httpx.Response:
        path = url.path.removeprefix("/auth/v1")
        query = dict(parse_qsl(url.query))
        if path == "/user":
            self.auth_calls += 1
            uid = self._bearer_uid(request)
            if not uid:
                return httpx.Response(401, json={"msg": "invalid JWT"})
            email = next(e for e, u in self.users.items() if u["id"] == uid)
            return httpx.Response(200, json={"id": uid, "email": email, "user_metadata": {"full_name": "Usuário Teste"}})
        if path == "/token":
            body = json.loads(request.content)
            if query.get("grant_type") == "password":
                user = self.users.get(body.get("email"))
                if not user or user["password"] != body.get("password"):
                    return httpx.Response(400, json={"error_code": "invalid_credentials", "msg": "Invalid login credentials"})
                return httpx.Response(200, json=self._issue(user["id"]))
            uid = self.refresh_tokens.pop(body.get("refresh_token", ""), None)
            if not uid:
                return httpx.Response(400, json={"error_code": "refresh_token_not_found", "msg": "Invalid Refresh Token"})
            return httpx.Response(200, json=self._issue(uid))
        if path == "/logout":
            self.tokens.pop(request.headers.get("authorization", "").removeprefix("Bearer ").strip(), None)
            return httpx.Response(204)
        return httpx.Response(404, json={})

    # ----------------------------------------------------------------- PostgREST
    def _rest(self, request: httpx.Request, url) -> httpx.Response:
        table = url.path.removeprefix("/rest/v1/")
        uid = self._bearer_uid(request)
        if not uid:
            return httpx.Response(401, json={"code": "PGRST301", "message": "JWT expired"})
        if self.missing_tables or table not in TABLES:
            return httpx.Response(404, json={"code": "PGRST205", "message": f"Could not find the table 'public.{table}'"})

        params = parse_qsl(url.query, keep_blank_values=True)
        prefer = request.headers.get("prefer", "")
        visible = [r for r in self.rows[table] if table not in OWNED or r.get("owner_id") == uid]  # RLS

        if request.method == "GET":
            matched = self._filter(visible, params)
            matched = self._order(matched, params)
            total = len(matched)
            offset = int(dict(params).get("offset", 0))
            limit = int(dict(params)["limit"]) if "limit" in dict(params) else None
            page = matched[offset: offset + limit if limit is not None else None]
            out = [self._project(table, r, dict(params).get("select", "*")) for r in page]
            headers = {}
            if "count=exact" in prefer:
                end = offset + len(page) - 1
                headers["content-range"] = f"{offset}-{max(end, offset)}/{total}" if page else f"*/{total}"
            return httpx.Response(200, json=out, headers=headers)

        if request.method == "POST":
            body = json.loads(request.content)
            if table in OWNED and body.get("owner_id", uid) != uid:
                return httpx.Response(403, json={"code": "42501", "message": "new row violates row-level security policy"})
            row, err = self._insert(table, body, uid)
            return err or httpx.Response(201, json=[row])

        if request.method == "PATCH":
            body = json.loads(request.content)
            changed = []
            for row in self._filter(visible, params):
                updated = {**row, **body}
                err = self._check_unique(table, updated, ignore=row)
                if err:
                    return err
                if "status" in body and body["status"] != row.get("status"):
                    updated["status_updated_at"] = _now()
                updated["updated_at"] = _now()
                row.clear()
                row.update(updated)
                changed.append(dict(row))
            return httpx.Response(200, json=changed)

        if request.method == "DELETE":
            doomed = self._filter(visible, params)
            ids = {r["id"] for r in doomed}
            self.rows[table] = [r for r in self.rows[table] if r["id"] not in ids]
            if table == "leads":  # ON DELETE CASCADE
                self.rows["lead_activities"] = [a for a in self.rows["lead_activities"] if a["lead_id"] not in ids]
                self.rows["outreach_messages"] = [a for a in self.rows["outreach_messages"] if a["lead_id"] not in ids]
            return httpx.Response(200, json=doomed)
        return httpx.Response(405, json={})

    # ------------------------------------------------------------------- filtros
    def _filter(self, rows, params):
        for key, value in params:
            if key in {"select", "order", "limit", "offset"}:
                continue
            if key == "or":
                conds = [c.split(".", 1) for c in value.strip("()").split(",")]  # [[coluna, "ilike.*x*"], ...]
                rows = [r for r in rows if any(self._match(r, col, expr) for col, expr in conds)]
            else:
                rows = [r for r in rows if self._match(r, key, value)]
        return rows

    @staticmethod
    def _match(row, column, expr) -> bool:
        op, _, arg = expr.partition(".")
        negate = False
        if op == "not":
            negate = True
            op, _, arg = arg.partition(".")
        if arg.startswith('"') and arg.endswith('"'):  # valores entre aspas (como o PostgREST)
            arg = arg[1:-1]
        cell = row.get(column)
        if op == "eq":
            result = str(cell).lower() == arg.lower() if isinstance(cell, bool) else str(cell) == arg
        elif op == "neq":
            result = str(cell) != arg
        elif op == "ilike":
            pattern = "^" + re.escape(arg).replace(r"\*", ".*") + "$"
            result = cell is not None and re.match(pattern, str(cell), re.I | re.S) is not None
        elif op == "in":
            result = str(cell) in arg.strip("()").split(",")
        elif op == "is":
            result = cell is None if arg == "null" else str(cell).lower() == arg.lower()
        elif op in ("gte", "lte", "lt"):
            if cell is None:
                result = False
            elif column.endswith("_at"):
                a, b = _dt(cell), _dt(arg)
                result = a >= b if op == "gte" else a <= b if op == "lte" else a < b
            else:
                if isinstance(cell, (int, float)) and not isinstance(cell, bool):
                    arg = float(arg)
                result = cell >= arg if op == "gte" else cell <= arg if op == "lte" else cell < arg
        else:
            raise AssertionError(f"operador não suportado pelo fake: {op}")
        return not result if negate else result

    @staticmethod
    def _order(rows, params):
        spec = dict(params).get("order")
        if not spec:
            return rows
        for part in reversed(spec.split(",")):
            col, *mods = part.split(".")
            desc = "desc" in mods
            nulls_last = "nullslast" in mods or ("nullsfirst" not in mods and not desc)  # padrão do Postgres
            present = [r for r in rows if r.get(col) is not None]
            missing = [r for r in rows if r.get(col) is None]
            present = sorted(
                present,
                key=lambda r: str(r.get(col)).casefold() if isinstance(r.get(col), str) and not col.endswith("_at") else r.get(col),
                reverse=desc,
            )
            rows = present + missing if nulls_last else missing + present
        return rows

    def _project(self, table, row, select: str):
        out = {k: v for k, v in row.items()}
        m = re.search(r"(\w+):(\w+)\(([^)]*)\)", select)
        if m:
            alias, ref, cols = m.groups()
            fk = "lead_id" if ref == "leads" else None
            target = next((r for r in self.rows[ref] if r["id"] == row.get(fk)), None)
            out[alias] = {c: target.get(c) for c in cols.split(",")} if target else None
        return out

    # ------------------------------------------------------------------ inserção
    def _insert(self, table, body, uid):
        row = dict(body)
        row.setdefault("id", str(uuid.uuid4()))
        now = _now()
        row.setdefault("created_at", now)
        if table in OWNED:
            row.setdefault("owner_id", uid)
        if table == "leads":
            row.setdefault("updated_at", now)
            row.setdefault("status_updated_at", now)
            for k, v in {"landing_page_status": "unknown", "status": "new", "source": "manual", "do_not_contact": False,
                         "score_source": "rules", "priority": "low", "score": 0}.items():
                row.setdefault(k, v)
            for k in ("contact_name", "segment", "city", "state", "phone", "whatsapp", "instagram", "facebook",
                      "website", "source_url", "notes", "prospecting_search_id"):
                row.setdefault(k, None)
            if len((row.get("company_name") or "").strip()) < 2:
                return None, httpx.Response(400, json={"code": "23514", "message": "violates check constraint"})
            err = self._check_unique(table, row)
            if err:
                return None, err
        if table == "lead_activities":
            if not any(r["id"] == row["lead_id"] and r["owner_id"] == uid for r in self.rows["leads"]):
                return None, httpx.Response(403, json={"code": "42501", "message": "row-level security"})
            row.setdefault("metadata", {})
        if table == "outreach_messages":
            if not any(r["id"] == row["lead_id"] and r["owner_id"] == uid for r in self.rows["leads"]):
                return None, httpx.Response(403, json={"code": "42501", "message": "row-level security"})
            row.setdefault("status", "draft"), row.setdefault("source", "template")
            row.setdefault("approved_at", None), row.setdefault("sent_at", None)
            if row["status"] in ("draft", "approved") and any(
                r["lead_id"] == row["lead_id"] and r["status"] in ("draft", "approved") for r in self.rows[table]
            ):
                return None, self._dup("uq_outreach_open_per_lead")
        if table == "prospecting_searches":
            row.setdefault("results_count", 0), row.setdefault("inserted_count", 0), row.setdefault("duplicates_count", 0)
            row.setdefault("error_message", None), row.setdefault("finished_at", None), row.setdefault("provider", None)
        self.rows[table].append(row)
        return dict(row), None

    def _check_unique(self, table, row, ignore=None):
        if table != "leads":
            return None
        norm = lambda v: (v or "").strip().lower()  # noqa: E731
        for other in self.rows["leads"]:
            if other is ignore or other["owner_id"] != row["owner_id"]:
                continue
            if norm(other["company_name"]) == norm(row["company_name"]) and norm(other.get("city")) == norm(row.get("city")):
                return self._dup("uq_leads_owner_company_city")
            for col, name in (("phone", "uq_leads_owner_phone"), ("whatsapp", "uq_leads_owner_whatsapp")):
                if row.get(col) and other.get(col) == row[col]:
                    return self._dup(name)
            if row.get("website") and other.get("website") and other["website"].lower() == row["website"].lower():
                return self._dup("uq_leads_owner_website")
        return None

    @staticmethod
    def _dup(constraint: str) -> httpx.Response:
        return httpx.Response(
            409,
            json={"code": "23505", "message": f'duplicate key value violates unique constraint "{constraint}"', "details": "Key already exists."},
        )
