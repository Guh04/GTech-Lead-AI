"""Configuração da aplicação (variáveis de ambiente / arquivo backend/.env)."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Supabase: somente a chave pública (anon). O acesso aos dados é protegido por RLS.
    supabase_url: str = ""
    supabase_anon_key: str = ""

    app_env: str = "development"
    app_timezone: str = "America/Sao_Paulo"
    cors_origins: str = ""
    frontend_dir: str = ""  # opcional: caminho alternativo para a pasta do frontend

    # Agente de prospecção (fase futura)
    prospecting_api_url: str = ""
    prospecting_api_key: str = ""
    prospecting_timeout_seconds: float = 120.0

    # Google Places API (New): provedor de prospecção real (tem prioridade sobre PROSPECTING_API_URL)
    google_places_api_key: str = ""
    google_places_timeout_seconds: float = 20.0

    # OpenStreetMap (Overpass): busca gratuita, sem chave. Usada se nenhum outro provedor estiver configurado.
    osm_enabled: bool = True
    # Um ou mais servidores Overpass separados por vírgula; se um falhar, o próximo é tentado.
    osm_overpass_url: str = "https://overpass-api.de/api/interpreter,https://overpass.openstreetmap.fr/api/interpreter,https://overpass.kumi.systems/api/interpreter"
    osm_nominatim_url: str = "https://nominatim.openstreetmap.org"  # acha o município pelo nome
    osm_retry_delay_seconds: float = 3.0
    osm_timeout_seconds: float = 60.0

    # Abordagem por WhatsApp: a IA escreve, o usuário aprova e envia (nada é enviado sozinho).
    anthropic_api_key: str = ""  # vazio = mensagens geradas por texto-modelo, sem IA
    outreach_model: str = "claude-haiku-5-5"
    outreach_timeout_seconds: float = 30.0
    # Proteção do número: limite de envios por dia e intervalo mínimo entre dois envios.
    outreach_daily_limit: int = Field(20, ge=1, le=1000)
    outreach_min_interval_seconds: int = Field(45, ge=0, le=3600)
    # Dados usados na assinatura/oferta das mensagens.
    outreach_sender_name: str = "Gustavo"
    outreach_sender_company: str = "GTech Digital Studio"
    outreach_offer: str = "criação de landing pages e sites profissionais para empresas"
    # Linha final para quem não quer receber mensagens (boa conduta / LGPD). Vazio = não acrescenta.
    outreach_opt_out: str = "Se não quiser receber mensagens, é só avisar."

    # WhatsMCP: envio real pelo WhatsApp conectado (servidor MCP sobre HTTP). Sem chave = abre o link wa.me.
    whatsmcp_api_key: str = ""
    whatsmcp_url: str = "https://api.whatsmcp.com/mcp"
    whatsmcp_account_id: str = ""  # opcional: só necessário se houver mais de um número pareado
    whatsmcp_timeout_seconds: float = 30.0

    @property
    def whatsmcp_configured(self) -> bool:
        return bool(self.whatsmcp_api_key.strip())

    @property
    def supabase_configured(self) -> bool:
        return self.supabase_url.startswith(("http://", "https://")) and bool(self.supabase_anon_key.strip())

    @property
    def supabase_base_url(self) -> str:
        return self.supabase_url.strip().rstrip("/")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def frontend_path(self) -> Path:
        return Path(self.frontend_dir) if self.frontend_dir else PROJECT_DIR / "frontend"


@lru_cache
def get_settings() -> Settings:
    return Settings()
