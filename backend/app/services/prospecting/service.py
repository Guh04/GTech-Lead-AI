"""Orquestra uma pesquisa de prospecção: histórico, chamada ao provedor e gravação dos leads."""
import logging
from datetime import datetime, timezone

import httpx
from pydantic import ValidationError

from app.core.config import Settings
from app.core.errors import AppError
from app.core.supabase import Database
from app.models.enums import LeadSource, LeadStatus, SearchStatus
from app.schemas.lead import LeadCreate
from app.schemas.prospecting import ProspectingStatus, SearchRequest
from app.services.lead_service import LeadService
from app.services.prospecting.base import ProspectingError, ProspectingProvider
from app.services.prospecting.google_places import GooglePlacesProvider
from app.services.prospecting.http_provider import HttpProspectingProvider
from app.services.prospecting.openstreetmap import OpenStreetMapProvider

log = logging.getLogger("gtech.prospecting")

NOT_CONFIGURED = (
    "Nenhum agente de prospecção está conectado. Para ativar a busca real, defina OSM_ENABLED=true (gratuito), "
    "GOOGLE_PLACES_API_KEY ou PROSPECTING_API_URL em backend/.env e reinicie o servidor."
)


def get_provider(settings: Settings, http: httpx.AsyncClient) -> ProspectingProvider | None:
    """Ponto único de registro de provedores, por prioridade: Google Places (chave), API externa (URL), OpenStreetMap (gratuito)."""
    if settings.google_places_api_key.strip():
        return GooglePlacesProvider(settings, http)
    if settings.prospecting_api_url.strip():
        return HttpProspectingProvider(settings, http)
    if settings.osm_enabled:
        return OpenStreetMapProvider(settings, http)
    return None


class ProspectingService:
    def __init__(self, db: Database, owner_id: str, provider: ProspectingProvider | None):
        self.db = db
        self.owner_id = owner_id
        self.provider = provider

    def status(self) -> ProspectingStatus:
        if self.provider is None:
            return ProspectingStatus(available=False, message=NOT_CONFIGURED)
        return ProspectingStatus(available=True, provider=self.provider.name, message="Agente de prospecção conectado.")

    async def history(self, limit: int = 30) -> list[dict]:
        rows, _ = await self.db.select("prospecting_searches", order="created_at.desc", limit=limit)
        return rows

    async def run(self, request: SearchRequest) -> dict:
        if self.provider is None:
            raise AppError(503, "prospecting_not_configured", NOT_CONFIGURED)

        search = await self.db.insert(
            "prospecting_searches",
            {
                "owner_id": self.owner_id,
                **request.model_dump(mode="json"),
                "status": SearchStatus.RUNNING.value,
                "provider": self.provider.name,
            },
        )
        try:
            candidates = await self.provider.search(request)
        except ProspectingError as exc:
            await self._finish(search["id"], SearchStatus.FAILED, error=str(exc))
            raise AppError(502, "prospecting_failed", str(exc)) from exc
        except Exception as exc:  # provedor com bug não pode deixar a pesquisa "em execução" para sempre
            log.exception("Provedor de prospecção falhou")
            await self._finish(search["id"], SearchStatus.FAILED, error="Falha inesperada no agente de prospecção.")
            raise AppError(502, "prospecting_failed", "Falha inesperada no agente de prospecção.") from exc

        leads = LeadService(self.db, self.owner_id)
        inserted = duplicates = invalid = 0
        for item in candidates[: request.desired_quantity]:
            try:
                data = {k: v for k, v in dict(item).items() if k not in {"score", "status", "source", "do_not_contact"}}
                payload = LeadCreate.model_validate({**data, "source": LeadSource.AI_AGENT, "status": LeadStatus.NEW})
            except (ValidationError, TypeError, ValueError):
                invalid += 1
                continue
            try:
                await leads.create(payload, search_id=search["id"])
                inserted += 1
            except AppError as exc:
                if exc.status != 409:
                    await self._finish(search["id"], SearchStatus.FAILED, error=exc.message, counts=(len(candidates), inserted, duplicates))
                    raise
                duplicates += 1

        error = f"{invalid} resultado(s) descartado(s) por dados inválidos." if invalid else None
        return await self._finish(search["id"], SearchStatus.COMPLETED, error=error, counts=(len(candidates), inserted, duplicates))

    async def _finish(self, search_id: str, status: SearchStatus, *, error: str | None = None, counts: tuple[int, int, int] = (0, 0, 0)) -> dict:
        found, inserted, duplicates = counts
        rows = await self.db.update(
            "prospecting_searches",
            {
                "status": status.value,
                "results_count": found,
                "inserted_count": inserted,
                "duplicates_count": duplicates,
                "error_message": error,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
            [("id", f"eq.{search_id}")],
        )
        return rows[0] if rows else {}
