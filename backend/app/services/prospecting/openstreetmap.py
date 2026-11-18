"""Provedor GRATUITO de prospecção: OpenStreetMap (Overpass API) + análise do site de cada empresa.

Não exige chave nem cartão. Em troca, a cobertura é menor que a do Google: só aparecem empresas que
alguém cadastrou no OpenStreetMap, e muitas não têm telefone ou site. Os dados são de colaboradores
do OpenStreetMap (licença ODbL), por isso cada lead registra a atribuição na observação.

Fluxo: o Nominatim (geocodificador do OSM) acha o município -> UMA consulta ao Overpass traz os
estabelecimentos de todos os segmentos naquela área -> o site de cada um é classificado
(lead_builder / site_analysis).

Privacidade: aos serviços públicos do OSM são enviados apenas o nome do município/estado e as
categorias dos segmentos. Nenhum dado seu ou de seus leads é enviado.
"""
import asyncio
import logging
import re
import unicodedata

import httpx

from app.core.config import Settings
from app.schemas.prospecting import SearchRequest
from app.services.prospecting.base import ProspectingError
from app.services.prospecting.lead_builder import build_lead

log = logging.getLogger("gtech.prospecting.osm")

USER_AGENT = "GTechLeadAI/1.0 (prospeccao de empresas; dados abertos OSM)"
ATTRIBUTION = "Dados © colaboradores do OpenStreetMap (ODbL)."
ANALYSIS_CONCURRENCY = 6

# prefixos de palavras do segmento (sem acento) -> categorias do OpenStreetMap
SEGMENT_RULES: list[tuple[tuple[str, ...], list[tuple[str, str]]]] = [
    (("odont", "dentist"), [("amenity", "dentist"), ("healthcare", "dentist")]),
    (("estetic",), [("shop", "beauty")]),
    (("salao", "cabelei"), [("shop", "hairdresser")]),
    (("barbear",), [("shop", "hairdresser")]),
    (("advoc",), [("office", "lawyer")]),
    (("contab",), [("office", "accountant")]),
    (("imobil",), [("office", "estate_agent")]),
    (("academia", "fitness", "crossfit"), [("leisure", "fitness_centre")]),
    (("restaur", "lanchonete"), [("amenity", "restaurant")]),
    (("padaria",), [("shop", "bakery")]),
    (("farmaci",), [("amenity", "pharmacy")]),
    (("pet", "veterin"), [("shop", "pet"), ("amenity", "veterinary")]),
    (("oficina", "mecanic"), [("shop", "car_repair")]),
    (("arquitet",), [("office", "architect")]),
    (("psicolog",), [("healthcare", "psychotherapist"), ("office", "therapist")]),
    (("fisioter",), [("healthcare", "physiotherapist")]),
    (("medic", "clinica geral"), [("amenity", "clinic"), ("amenity", "doctors")]),
    (("idioma", "ingles"), [("amenity", "language_school")]),
    (("autoescola",), [("amenity", "driving_school")]),
    (("fotograf",), [("shop", "photo"), ("craft", "photographer")]),
    (("constru", "reforma"), [("craft", "builder"), ("office", "construction_company")]),
]


UF_NAMES = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal",
    "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina",
    "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins",
}


def _plain(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def tags_for_segment(segment: str) -> list[tuple[str, str]]:
    """Categorias do OSM para um segmento digitado em português; lista vazia se não houver."""
    plain = _plain(segment)
    words = re.findall(r"[a-z0-9]+", plain)
    found: list[tuple[str, str]] = []
    for prefixes, tags in SEGMENT_RULES:
        if any(any(w.startswith(p) for w in words) or (" " in p and p in plain) for p in prefixes):
            found.extend(t for t in tags if t not in found)
    return found


def supported_segments_hint() -> str:
    return "odontologia, estética, salão de beleza, barbearia, advocacia, contabilidade, imobiliária, academia, restaurante, padaria, farmácia, pet shop, oficina mecânica, arquitetura, psicologia, fisioterapia, clínica médica, escola de idiomas, autoescola, fotografia, construção e reformas"


class OpenStreetMapProvider:
    name = "openstreetmap"

    def __init__(self, settings: Settings, http: httpx.AsyncClient):
        self._nominatim = settings.osm_nominatim_url.rstrip("/")
        self._urls = [u.strip() for u in settings.osm_overpass_url.split(",") if u.strip()]
        self._timeout = settings.osm_timeout_seconds
        self._delay = settings.osm_retry_delay_seconds
        self._http = http

    async def _overpass(self, query: str) -> dict:
        """Consulta o Overpass: tenta cada servidor até 2 vezes quando o serviço gratuito está sobrecarregado."""
        busy = False
        last_error: str | None = None
        for url in self._urls:
            for attempt in range(2):
                if attempt:
                    await asyncio.sleep(self._delay)
                try:
                    res = await self._http.post(url, data={"data": query}, headers={"User-Agent": USER_AGENT}, timeout=self._timeout)
                except httpx.TimeoutException:
                    busy = True
                    break  # servidor lento: passa para o próximo em vez de esperar de novo
                except httpx.RequestError:
                    last_error = "Não foi possível conectar ao OpenStreetMap."
                    break
                if res.status_code in (429, 502, 503, 504):
                    busy = True
                    continue
                if res.status_code != 200:
                    last_error = f"O OpenStreetMap respondeu com erro ({res.status_code})."
                    break
                try:
                    return res.json()
                except ValueError:
                    busy = True  # resposta de erro em HTML/texto enviada com status 200
                    break
        if busy:
            raise ProspectingError("O serviço gratuito do OpenStreetMap está ocupado ou lento. Tente novamente em alguns minutos.")
        raise ProspectingError(last_error or "Não foi possível consultar o OpenStreetMap.")

    async def _area_id(self, region: str, state: str | None) -> int | None:
        """Acha o município no Nominatim e devolve o id de área do Overpass (relação + 3.600.000.000)."""
        params = {"city": region, "country": "Brasil", "format": "jsonv2", "limit": 5}
        if state:
            params["state"] = UF_NAMES.get(state, state)
        try:
            res = await self._http.get(f"{self._nominatim}/search", params=params, headers={"User-Agent": USER_AGENT}, timeout=30)
        except httpx.RequestError as exc:
            raise ProspectingError("Não foi possível consultar o buscador de municípios do OpenStreetMap.") from exc
        if res.status_code in (429, 502, 503, 504):
            raise ProspectingError("O buscador de municípios do OpenStreetMap está ocupado. Tente novamente em alguns minutos.")
        if res.status_code != 200:
            raise ProspectingError(f"O buscador de municípios do OpenStreetMap respondeu com erro ({res.status_code}).")
        try:
            places = res.json()
        except ValueError as exc:
            raise ProspectingError("Resposta inválida do buscador de municípios do OpenStreetMap.") from exc
        for place in places if isinstance(places, list) else []:
            if place.get("osm_type") == "relation" and place.get("category") == "boundary" and isinstance(place.get("osm_id"), int):
                return 3_600_000_000 + place["osm_id"]
        return None

    @staticmethod
    def _first(value: str | None) -> str | None:
        return value.split(";")[0].strip() if value else None

    async def search(self, query: SearchRequest) -> list[dict]:
        unsupported = [s for s in query.segments if not tags_for_segment(s)]
        if unsupported:
            raise ProspectingError(
                f"O OpenStreetMap não tem categoria para: {', '.join(unsupported)}. "
                f"Segmentos suportados: {supported_segments_hint()}."
            )
        area = await self._area_id(query.region, query.state)
        if area is None:
            where = f" ({query.state})" if query.state else ""
            raise ProspectingError(f'Município "{query.region}"{where} não encontrado no OpenStreetMap. Informe o nome exato do município.')

        segment_tags = {seg: tags_for_segment(seg) for seg in query.segments}
        selectors = "".join(f'nwr["{k}"="{v}"](area.a);' for k, v in dict.fromkeys(t for tags in segment_tags.values() for t in tags))
        per_segment = -(-query.desired_quantity // len(query.segments))
        fetch_limit = min(1000, max(100, query.desired_quantity * 6))  # folga para empresas sem nome ou filtradas
        # UMA consulta para todos os segmentos: o serviço gratuito agradece (menos carga, menos erros)
        data = await self._overpass(f"[out:json][timeout:55];area({area})->.a;({selectors});out tags center {fetch_limit};")

        # cada estabelecimento vai para o primeiro segmento cujas categorias ele possui
        per_seg: dict[str, list] = {seg: [] for seg in query.segments}
        seen: set[tuple[str, int]] = set()
        for el in data.get("elements", []):
            tags = el.get("tags") or {}
            key = (el.get("type", ""), el.get("id", 0))
            name = (tags.get("name") or "").strip()
            if not name or key in seen:
                continue
            for seg, wanted in segment_tags.items():
                if any(tags.get(k) == v for k, v in wanted):
                    seen.add(key)
                    per_seg[seg].append((el, tags, name))
                    break

        gate = asyncio.Semaphore(ANALYSIS_CONCURRENCY)
        results: list[dict] = []
        for segment, candidates in per_seg.items():
            built = await asyncio.gather(*(
                build_lead(
                    self._http, gate, query, origin="OpenStreetMap", name=name, segment=segment,
                    city=tags.get("addr:city"), state=query.state,
                    phone=self._first(tags.get("phone") or tags.get("contact:phone") or tags.get("mobile") or tags.get("contact:mobile")),
                    whatsapp=self._first(tags.get("contact:whatsapp")),
                    website_raw=self._first(tags.get("website") or tags.get("contact:website")),
                    instagram_raw=tags.get("contact:instagram"), facebook_raw=tags.get("contact:facebook"),
                    source_url=f"https://www.openstreetmap.org/{el['type']}/{el['id']}",
                    address=", ".join(p for p in (tags.get("addr:street"), tags.get("addr:housenumber"), tags.get("addr:suburb")) if p) or None,
                    attribution=ATTRIBUTION,
                )
                for el, tags, name in candidates
            ))
            results.extend([lead for lead in built if lead is not None][:per_segment])
        log.info("OpenStreetMap: %s empresa(s) após filtros", len(results))
        return results
