"""Montagem comum dos leads encontrados por qualquer provedor (Google Places, OpenStreetMap...).

Recebe os dados brutos de uma empresa, classifica o endereço informado (site próprio, rede social,
página de links), analisa o site quando existe e aplica os filtros do formulário de pesquisa.
Retorna um dicionário no formato de LeadCreate, ou None se a empresa não passar nos filtros.
"""
import asyncio

import httpx

from app.models.enums import LandingFilter, LandingStatus, WebsiteFilter
from app.schemas import normalize as n
from app.schemas.prospecting import SearchRequest
from app.services.prospecting.site_analysis import analyze_website, classify_url


def _safe(fn, value):
    """Normaliza um campo opcional; valor mal formado vira None em vez de descartar a empresa."""
    try:
        return fn(value) if value else None
    except ValueError:
        return None


def wants_site(request: SearchRequest, has_site: bool) -> bool:
    if request.website_filter == WebsiteFilter.WITH_SITE:
        return has_site
    if request.website_filter == WebsiteFilter.WITHOUT_SITE:
        return not has_site
    return True


def wants_landing(request: SearchRequest, status: LandingStatus) -> bool:
    return request.landing_filter in (LandingFilter.ANY, LandingFilter(status.value))


async def build_lead(
    http: httpx.AsyncClient,
    gate: asyncio.Semaphore,
    request: SearchRequest,
    *,
    origin: str,
    name: str,
    segment: str,
    city: str | None,
    state: str | None,
    phone: str | None = None,
    whatsapp: str | None = None,
    website_raw: str | None = None,
    instagram_raw: str | None = None,
    facebook_raw: str | None = None,
    source_url: str | None = None,
    address: str | None = None,
    attribution: str | None = None,
) -> dict | None:
    kind, url = classify_url(website_raw)
    website = _safe(lambda v: n.normalize_url(v, "Site"), url) if kind in ("website", "link_only") else None
    instagram = _safe(n.normalize_instagram, url if kind == "instagram" else instagram_raw)
    facebook = _safe(n.normalize_facebook, url if kind == "facebook" else facebook_raw)

    if not wants_site(request, website is not None):
        return None

    found: dict[str, str] = {}  # contatos que a própria empresa publica no site/link
    if website is None:
        landing, reason = LandingStatus.NONE, f"sem site informado no perfil público ({origin})"
        if instagram or facebook:
            reason = f"perfil público ({origin}) informa apenas rede social"
    elif kind == "link_only":
        landing, reason = LandingStatus.SITE_ONLY, "endereço é página de links, mensageiro ou marketplace (não é landing page própria)"
        found = extract_contacts([website])  # ex.: o "site" é um link wa.me/55...
    else:
        async with gate:
            landing, reason, found = await analyze_website_full(http, website)

    if not wants_landing(request, landing):
        return None

    # Dados do provedor têm prioridade; o que veio do site só preenche o que está vazio.
    whatsapp = _safe(n.normalize_phone, whatsapp) or _safe(n.normalize_phone, found.get("whatsapp"))
    phone = _safe(n.normalize_phone, phone) or _safe(n.normalize_phone, found.get("phone"))
    from_site = [label for key, label, had in (
        ("whatsapp", "WhatsApp", bool(whatsapp) and whatsapp == _safe(n.normalize_phone, found.get("whatsapp"))),
        ("instagram", "Instagram", not instagram and bool(found.get("instagram"))),
        ("facebook", "Facebook", not facebook and bool(found.get("facebook"))),
    ) if had and found.get(key)]
    instagram = instagram or _safe(n.normalize_instagram, found.get("instagram"))
    facebook = facebook or _safe(n.normalize_facebook, found.get("facebook"))

    notes = [f"Encontrado via {origin}. Landing page: {landing.value} ({reason})."]
    if from_site:
        notes.append(f"Contatos lidos do site da própria empresa: {', '.join(from_site)}.")
    if address:
        notes.append(f"Endereço: {address}.")
    if attribution:
        notes.append(attribution)
    return {
        "company_name": name,
        "segment": segment,
        "city": city or request.region,
        "state": state or request.state,
        "phone": _safe(n.normalize_phone, phone),
        "whatsapp": _safe(n.normalize_phone, whatsapp),
        "instagram": instagram,
        "facebook": facebook,
        "website": website,
        "landing_page_status": landing.value,
        "source_url": source_url,
        "notes": " ".join(notes),
    }
