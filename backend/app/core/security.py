"""Dependências de autenticação e acesso ao banco para as rotas."""
import httpx
from fastapi import Depends, Request

from app.core.config import Settings
from app.core.errors import AppError
from app.core.supabase import AuthUser, Database, SupabaseAuth


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_http(request: Request) -> httpx.AsyncClient:
    return request.app.state.http


def require_supabase(settings: Settings = Depends(get_settings_dep)) -> Settings:
    if not settings.supabase_configured:
        raise AppError(
            503,
            "supabase_not_configured",
            "O Supabase não está configurado. Preencha SUPABASE_URL e SUPABASE_ANON_KEY em backend/.env e reinicie o servidor.",
        )
    return settings


def get_auth(request: Request, _: Settings = Depends(require_supabase)) -> SupabaseAuth:
    return request.app.state.auth  # criado uma vez no startup (mantém o cache de tokens)


def _bearer(request: Request) -> str:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise AppError(401, "not_authenticated", "Você precisa entrar para acessar este recurso.")
    return token.strip()


async def current_user(request: Request, auth: SupabaseAuth = Depends(get_auth)) -> AuthUser:
    return await auth.verify(_bearer(request))


def get_db(
    user: AuthUser = Depends(current_user),
    settings: Settings = Depends(require_supabase),
    http: httpx.AsyncClient = Depends(get_http),
) -> Database:
    return Database(settings, http, user.token)
