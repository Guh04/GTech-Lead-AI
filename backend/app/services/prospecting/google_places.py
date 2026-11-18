"""Provedor de prospecção real: Google Places API (New) + análise do site de cada empresa.

Fluxo de cada pesquisa:
  1. Busca de texto "<segmento> em <região>, <UF>" na Places API (até 3 páginas de 20 por segmento).
  2. Para cada empresa: telefone, endereço, link do Google Maps e site informado no perfil público.
  3. O endereço do perfil é classificado: site próprio, rede social (vira instagram/facebook),
     página de links/WhatsApp (não conta como landing page) ou ausente.
  4. Sites próprios são abertos e analisados (site_analysis.py) para estimar se existe landing page.
  5. Os filtros "com/sem site" e "situação da landing page" do formulário são aplicados.

Somente dados comerciais públicos são lidos. Nenhuma mensagem é enviada a ninguém.
A pontuação e a prioridade são calculadas pelo sistema depois (services/scoring.py).

Custo: a busca solicita telefone e site (campos "Enterprise" do Text Search). Confira os preços e a
cota gratuita mensal vigentes no console do Google Cloud antes de pesquisas grandes.
"""
import asyncio
import logging
from dataclasses import dataclass

import httpx

from app.core.config import Settings
from app.schemas.prospecting import SearchRequest
from app.services.prospecting.base import ProspectingError
from app.services.prospecting.lead_builder import build_lead

log = logging.getLogger("gtech.prospecting.google")

ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join(
    [
        "places.id", "places.displayName", "places.formattedAddress", "places.addressComponents",
        "places.nationalPhoneNumber", "places.websiteUri", "places.googleMapsUri", "places.businessStatus",
        "nextPageToken",
    ]
)
PAGE_SIZE = 20
MAX_PAGES = 3  # limite da própria API: 60 resultados por busca
ANALYSIS_CONCURRENCY = 6


@dataclass
class Place:
    place_id: str
    name: str
    city: str | None
    state: str | None
    address: str | None
    phone: str | None
    maps_url: str | None
    website_raw: str | None


def _component(components: list[dict], *types: str, short: bool = False) -> str | None:
    for wanted in types:
        for comp in components:
            if wanted in comp.get("types", []):
                value = comp.get("shortText" if short else "longText")
                if value:
                    return value
    return None


def parse_place(raw: dict) -> Place | None:
    name = ((raw.get("displayName") or {}).get("text") or "").strip()
    place_id = raw.get("id")
    if not name or not place_id:
        return None
    if raw.get("businessStatus") not in (None, "OPERATIONAL"):
        return None  # fechada definitiva ou temporariamente
    comps = raw.get("addressComponents") or []
    state = _component(comps, "administrative_area_level_1", short=True)
    return Place(
        place_id=place_id,
        name=name,
        city=_component(comps, "locality", "administrative_area_level_2", "sublocality"),
        state=state.upper() if state and len(state) == 2 else None,
        address=raw.get("formattedAddress"),
        phone=raw.get("nationalPhoneNumber"),
        maps_url=raw.get("googleMapsUri"),
        website_raw=raw.get("websiteUri"),
    )


class GooglePlacesProvider:
    name = "google-places"

    def __init__(self, settings: Settings, http: httpx.AsyncClient):
        self._key = settings.google_places_api_key.strip()
        self._timeout = settings.google_places_timeout_seconds
        self._http = http

    # ------------------------------------------------------------------ API do Google
    async def _text_search(self, text: str, page_token: str | None) -> dict:
        body: dict = {"textQuery": text, "languageCode": "pt-BR", "regionCode": "BR", "pageSize": PAGE_SIZE}
        if page_token:
            body["pageToken"] = page_token
        headers = {"X-Goog-Api-Key": self._key, "X-Goog-FieldMask": FIELD_MASK, "Content-Type": "application/json"}
        try:
            res = await self._http.post(ENDPOINT, json=body, headers=headers, timeout=self._timeout)
        except httpx.TimeoutException as exc:
            raise ProspectingError("O Google Places demorou demais para responder. Tente novamente.") from exc
        except httpx.RequestError as exc:
            raise ProspectingError("Não foi possível conectar ao Google Places.") from exc
        if res.status_code == 200:
            try:
                return res.json()
            except ValueError as exc:
                raise ProspectingError("Resposta inválida do Google Places.") from exc
        raise ProspectingError(self._explain_error(res))

    @staticmethod
    def _explain_error(res: httpx.Response) -> str:
        try:
            err = res.json().get("error", {})
        except ValueError:
            err = {}
        status, message = err.get("status", ""), err.get("message", "")
        if res.status_code == 429 or status == "RESOURCE_EXHAUSTED":
            return "A cota do Google Places foi excedida. Aguarde ou revise os limites no Google Cloud."
        if status == "PERMISSION_DENIED" or res.status_code == 403:
            if "has not been used" in message or "disabled" in message.lower():
                return "A \"Places API (New)\" não está ativada neste projeto do Google Cloud. Ative-a e tente de novo."
            if "billing" in message.lower():
                return "O faturamento não está ativo no projeto do Google Cloud. Ative o faturamento para usar o Places."
            return "O Google recusou a chave (sem permissão). Verifique as restrições da chave e a Places API (New)."
        if "API key" in message or status == "INVALID_ARGUMENT" and "key" in message.lower():
            return "A chave do Google Places é inválida. Confira GOOGLE_PLACES_API_KEY em backend/.env."
        return f"O Google Places respondeu com erro ({res.status_code})."

    # ------------------------------------------------------------------ lead
    async def _build_lead(self, place: Place, segment: str, request: SearchRequest, gate: asyncio.Semaphore) -> dict | None:
        return await build_lead(
            self._http, gate, request, origin="Google Places", name=place.name, segment=segment, city=place.city,
            state=place.state, phone=place.phone, website_raw=place.website_raw, source_url=place.maps_url, address=place.address,
        )

    # ------------------------------------------------------------------ interface pública
    async def search(self, query: SearchRequest) -> list[dict]:
        per_segment = -(-query.desired_quantity // len(query.segments))  # teto da divisão
        seen: set[str] = set()
        results: list[dict] = []
        gate = asyncio.Semaphore(ANALYSIS_CONCURRENCY)

        for segment in query.segments:
            where = ", ".join(p for p in (query.region, query.state, "Brasil") if p)
            text = f"{segment} em {where}"
            token: str | None = None
            taken = 0
            for _ in range(MAX_PAGES):
                data = await self._text_search(text, token)
                places = []
                for raw in data.get("places", []):
                    place = parse_place(raw)
                    if place is None or place.place_id in seen:
                        continue
                    if query.state and place.state and place.state != query.state:
                        continue  # a busca por texto pode "vazar" para outro estado
                    seen.add(place.place_id)
                    places.append(place)
                built = await asyncio.gather(*(self._build_lead(p, segment, query, gate) for p in places))
                for lead in built:
                    if lead is not None and taken < per_segment:
                        results.append(lead)
                        taken += 1
                token = data.get("nextPageToken")
                if taken >= per_segment or not token:
                    break
        log.info("Google Places: %s empresa(s) após filtros", len(results))
        return results
