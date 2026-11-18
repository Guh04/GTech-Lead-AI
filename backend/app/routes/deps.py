"""Dependências compartilhadas pelas rotas (serviços já ligados ao usuário logado)."""
import logging
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from fastapi import Depends

from app.core.config import Settings
from app.core.security import current_user, get_db, get_http, require_supabase
from app.core.supabase import AuthUser, Database
from app.services.analytics_service import AnalyticsService
from app.services.lead_service import LeadService
from app.services.prospecting.service import ProspectingService, get_provider

log = logging.getLogger("gtech")


def lead_service(user: AuthUser = Depends(current_user), db: Database = Depends(get_db)) -> LeadService:
    return LeadService(db, user.id)


def _timezone(settings: Settings) -> ZoneInfo:
    try:
        return ZoneInfo(settings.app_timezone)
    except ZoneInfoNotFoundError:
        log.warning("APP_TIMEZONE inválido (%s); usando UTC.", settings.app_timezone)
        return ZoneInfo("UTC")


def analytics_service(
    user: AuthUser = Depends(current_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(require_supabase),
) -> AnalyticsService:
    return AnalyticsService(db, user.id, _timezone(settings))


def outreach_service(
    user: AuthUser = Depends(current_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(require_supabase),
    http: httpx.AsyncClient = Depends(get_http),
) -> OutreachService:
    return OutreachService(db, user.id, settings, http, _timezone(settings))


def prospecting_service(
    user: AuthUser = Depends(current_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(require_supabase),
    http: httpx.AsyncClient = Depends(get_http),
) -> ProspectingService:
    return ProspectingService(db, user.id, get_provider(settings, http))
