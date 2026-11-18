"""Autenticação (Supabase Auth intermediado pelo backend) e saúde da aplicação."""
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.core.security import _bearer, current_user, get_auth, get_settings_dep
from app.core.supabase import AuthUser, SupabaseAuth

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=1, max_length=256)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10, max_length=2048)


@router.get("/health", summary="Estado do servidor")
async def health(settings: Settings = Depends(get_settings_dep)):
    return {
        "status": "ok",
        "supabase_configured": settings.supabase_configured,
        "message": None
        if settings.supabase_configured
        else "Preencha SUPABASE_URL e SUPABASE_ANON_KEY em backend/.env e reinicie o servidor.",
    }


@router.post("/auth/login", summary="Entrar com e-mail e senha")
async def login(body: LoginRequest, auth: SupabaseAuth = Depends(get_auth)):
    return await auth.sign_in(body.email.strip(), body.password)


@router.post("/auth/refresh", summary="Renovar a sessão")
async def refresh(body: RefreshRequest, auth: SupabaseAuth = Depends(get_auth)):
    return await auth.refresh(body.refresh_token)


@router.post("/auth/logout", status_code=204, summary="Sair")
async def logout(request: Request, auth: SupabaseAuth = Depends(get_auth)):
    await auth.sign_out(_bearer(request))
    return Response(status_code=204)


@router.get("/me", summary="Usuário logado")
async def me(user: AuthUser = Depends(current_user)):
    return {"id": user.id, "email": user.email, "full_name": user.full_name}
