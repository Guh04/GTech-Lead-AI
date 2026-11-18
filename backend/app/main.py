"""GTech Lead AI - aplicação FastAPI.

Em desenvolvimento e produção simples, um único processo serve:
  /api/*  -> API REST
  /       -> frontend estático (pasta ../frontend)
"""
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.supabase import SupabaseAuth
from app.routes import analytics, auth, leads, prospecting

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("gtech")

CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
    "font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)


def create_app(settings: Settings | None = None, http_client: httpx.AsyncClient | None = None) -> FastAPI:
    """Fábrica da aplicação (permite injetar configuração e cliente HTTP nos testes)."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.http = http_client or httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=8.0))
        app.state.auth = SupabaseAuth(settings, app.state.http)
        if not settings.supabase_configured:
            log.warning("Supabase NÃO configurado: preencha SUPABASE_URL e SUPABASE_ANON_KEY em backend/.env")
        yield
        if http_client is None:
            await app.state.http.aclose()

    app = FastAPI(
        title="GTech Lead AI",
        description="API de gerenciamento e prospecção de leads comerciais.",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    app.state.settings = settings
    register_error_handlers(app)

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
        )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        path = request.url.path
        if path.startswith("/api"):
            response.headers.setdefault("Cache-Control", "no-store")
        else:
            if path not in ("/docs", "/redoc"):
                response.headers.setdefault("Content-Security-Policy", CSP)
            # Arquivos estáticos: sempre revalida (ETag), assim atualizações aparecem sem limpar o cache.
            response.headers.setdefault("Cache-Control", "no-cache")
        return response

    for router in (auth.router, leads.router, analytics.router, prospecting.router):
        app.include_router(router, prefix="/api")

    frontend = settings.frontend_path
    if frontend.is_dir():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    else:
        log.warning("Pasta do frontend não encontrada: %s", frontend)

    return app


app = create_app()
