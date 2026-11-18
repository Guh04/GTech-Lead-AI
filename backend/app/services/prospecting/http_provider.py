"""Provedor genérico: delega a busca a uma API externa de prospecção.

Só é ativado se PROSPECTING_API_URL estiver definido. Contrato esperado
(documentado em docs/README.md):

  POST {PROSPECTING_API_URL}/search
  Authorization: Bearer {PROSPECTING_API_KEY}   (se configurada)
  Corpo : {region, state, segments[], desired_quantity, website_filter, landing_filter}
  Resposta 200: {"leads": [ {company_name, segment, city, state, phone, ...}, ... ]}
"""
import httpx

from app.core.config import Settings
from app.schemas.prospecting import SearchRequest
from app.services.prospecting.base import ProspectingError


class HttpProspectingProvider:
    name = "api-externa"

    def __init__(self, settings: Settings, http: httpx.AsyncClient):
        self._url = settings.prospecting_api_url.rstrip("/") + "/search"
        self._key = settings.prospecting_api_key
        self._timeout = settings.prospecting_timeout_seconds
        self._http = http

    async def search(self, query: SearchRequest) -> list[dict]:
        headers = {"Authorization": f"Bearer {self._key}"} if self._key else {}
        try:
            res = await self._http.post(self._url, json=query.model_dump(mode="json"), headers=headers, timeout=self._timeout)
        except httpx.TimeoutException as exc:
            raise ProspectingError("O agente de prospecção demorou demais para responder.") from exc
        except httpx.RequestError as exc:
            raise ProspectingError("Não foi possível conectar ao agente de prospecção.") from exc
        if res.status_code != 200:
            raise ProspectingError(f"O agente de prospecção respondeu com erro ({res.status_code}).")
        try:
            leads = res.json().get("leads")
        except (ValueError, AttributeError) as exc:
            raise ProspectingError("Resposta inválida do agente de prospecção.") from exc
        if not isinstance(leads, list):
            raise ProspectingError("Resposta inválida do agente de prospecção (campo 'leads' ausente).")
        return leads
