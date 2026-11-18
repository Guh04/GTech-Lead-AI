"""Google Places + análise de sites. Nenhuma chamada real: tudo passa por transportes simulados."""
import itertools
import json

import httpx
import pytest

from app.models.enums import LandingStatus
from app.services.prospecting import site_analysis as sa

LANDING_HTML = """<html><head><title>Clínica Sorriso - Implantes</title></head><body>
<h1>Implantes dentários em Campinas</h1><p>%s</p>
<a href="https://wa.me/5519999990001">Fale conosco no WhatsApp</a><form><input name="nome"></form></body></html>""" % ("Texto institucional. " * 30)
SITE_ONLY_HTML = "<html><head><title>Empresa</title></head><body><h1>Bem-vindo</h1><p>%s</p></body></html>" % ("Sobre nós e nossa história. " * 30)
PARKED_HTML = "<html><head><title>Em construção</title></head><body><p>Site em construção</p></body></html>"

SEARCH = {"region": "Campinas", "state": "SP", "segments": ["Odontologia"], "desired_quantity": 10}


_PHONES = itertools.count(1000000)


def place(pid, name, website=None, phone=None, state="SP", status="OPERATIONAL"):
    return {
        "id": pid, "displayName": {"text": name}, "formattedAddress": f"Rua A, 10 - {state}", "businessStatus": status,
        "nationalPhoneNumber": phone or "(19) 3%03d-%04d" % divmod(next(_PHONES), 10000),
        "websiteUri": website, "googleMapsUri": f"https://maps.google.com/?cid={pid}",
        "addressComponents": [
            {"longText": "Campinas", "shortText": "Campinas", "types": ["locality"]},
            {"longText": "São Paulo", "shortText": state, "types": ["administrative_area_level_1"]},
        ],
    }


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def dns(monkeypatch):
    async def fake_resolve(host):
        return {"localhost": ["127.0.0.1"]}.get(host) or (["10.0.0.5"] if host.startswith("interno") else ["93.184.216.34"])

    monkeypatch.setattr(sa, "resolve_host", fake_resolve)


def sites(pages: dict):
    def handler(request: httpx.Request):
        entry = pages.get(request.url.host)
        if entry is None:
            raise httpx.ConnectError("sem resposta")
        if isinstance(entry, httpx.Response):
            return entry
        return httpx.Response(200, text=entry, headers={"content-type": "text/html; charset=utf-8"})

    return handler


# --------------------------------------------------------------------------- heurística
def test_classify_html():
    assert sa.classify_html(LANDING_HTML)[0] == LandingStatus.HAS_LANDING
    assert sa.classify_html(SITE_ONLY_HTML)[0] == LandingStatus.SITE_ONLY
    assert sa.classify_html(PARKED_HTML)[0] == LandingStatus.SITE_ONLY
    # script/style não contam como conteúdo nem como chamada para ação
    only_script = "<html><title>x</title><body><script>var a='wa.me form orçamento';</script><h1>Oi</h1><p>%s</p></body></html>" % ("texto " * 80)
    assert sa.classify_html(only_script)[0] == LandingStatus.SITE_ONLY
    assert sa.classify_html("<<<não é html>>>")[0] == LandingStatus.SITE_ONLY


def test_classify_url():
    assert sa.classify_url(None) == ("none", None)
    assert sa.classify_url("https://www.instagram.com/clinica")[0] == "instagram"
    assert sa.classify_url("https://pt-br.facebook.com/clinica")[0] == "facebook"
    assert sa.classify_url("https://linktr.ee/clinica")[0] == "link_only"
    assert sa.classify_url("https://wa.me/5519999990001")[0] == "link_only"
    assert sa.classify_url("https://www.clinica.com.br/")[0] == "website"
    assert sa.classify_url("https://naoinstagram.com/x")[0] == "website"


# ------------------------------------------------------------------------------- SSRF
@pytest.mark.anyio
async def test_is_public_url_blocks_internal_targets():
    for bad in ["http://127.0.0.1/", "http://localhost/", "http://10.1.2.3/", "http://169.254.169.254/latest/meta-data",
                "http://[::1]/", "http://interno.example/", "ftp://a.example/", "http://a.example:8080/", "file:///etc/passwd"]:
        assert not await sa.is_public_url(bad), bad
    assert await sa.is_public_url("https://clinica.example/")


@pytest.mark.anyio
async def test_redirect_to_private_address_is_not_followed(fake):
    hits = []

    def handler(request):
        hits.append(request.url.host)
        return httpx.Response(302, headers={"location": "http://interno.example/admin"})

    fake.web_handler = handler
    async with fake.client() as http:
        status, _ = await sa.analyze_website(http, "https://clinica.example")
    assert status == LandingStatus.UNKNOWN
    assert hits == ["clinica.example"]  # nunca chegou ao destino interno


@pytest.mark.anyio
async def test_analyze_website_failures_are_unknown(fake):
    async with fake.client() as http:
        fake.web_handler = sites({"fora.example": httpx.Response(500, text="erro")})
        assert (await sa.analyze_website(http, "https://fora.example"))[0] == LandingStatus.UNKNOWN
        fake.web_handler = sites({"pdf.example": httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"})})
        assert (await sa.analyze_website(http, "https://pdf.example"))[0] == LandingStatus.UNKNOWN
        fake.web_handler = sites({})
        assert (await sa.analyze_website(http, "https://caiu.example"))[0] == LandingStatus.UNKNOWN


# ------------------------------------------------------------------------ provedor completo
def places_api(fake, pages_of_places, status=200, body=None):
    captured = {"calls": []}

    def handler(request: httpx.Request):
        data = json.loads(request.content)
        captured["calls"].append({"body": data, "key": request.headers.get("x-goog-api-key"), "mask": request.headers.get("x-goog-fieldmask"), "url": str(request.url)})
        if status != 200:
            return httpx.Response(status, json=body or {})
        idx = len(captured["calls"]) - 1
        page = pages_of_places[min(idx, len(pages_of_places) - 1)]
        out = {"places": page}
        if idx + 1 < len(pages_of_places):
            out["nextPageToken"] = f"tok{idx + 1}"
        return httpx.Response(200, json=out)

    fake.places_handler = handler
    return captured


def test_status_reports_google_provider(make_client, ana):
    c = make_client(google_places_api_key="chave-google")
    assert c.get("/api/prospecting/status", headers=ana).json()["provider"] == "google-places"


def test_search_saves_real_fields_and_classifies_sites(make_client, ana, fake):
    c = make_client(google_places_api_key="chave-google")
    cap = places_api(fake, [[
        place("p1", "Sem Site Odonto", phone="(19) 3234-5678"),
        place("p2", "Insta Odonto", website="https://www.instagram.com/instaodonto"),
        place("p3", "Landing Odonto", website="https://landing.example/"),
        place("p4", "Site Simples", website="https://simples.example/"),
        place("p5", "Site Fora do Ar", website="https://fora.example/"),
        place("p6", "Só Links", website="https://linktr.ee/solinks"),
        place("p7", "Fechada", status="CLOSED_PERMANENTLY"),
        place("p8", "Outro Estado", state="RJ"),
    ]])
    fake.web_handler = sites({"landing.example": LANDING_HTML, "simples.example": SITE_ONLY_HTML, "fora.example": httpx.Response(503, text="x")})

    r = c.post("/api/prospecting/search", json=SEARCH, headers=ana)
    assert r.status_code == 201, r.text
    s = r.json()
    assert (s["status"], s["results_count"], s["inserted_count"]) == ("completed", 6, 6)
    assert s["provider"] == "google-places"

    # chave só no cabeçalho (nunca na URL) e consulta montada corretamente
    call = cap["calls"][0]
    assert call["key"] == "chave-google" and "chave-google" not in call["url"]
    assert call["body"]["textQuery"] == "Odontologia em Campinas, SP, Brasil" and call["body"]["regionCode"] == "BR"
    assert "places.websiteUri" in call["mask"]

    items = c.get("/api/leads", params={"search_id": s["id"], "page_size": 50}, headers=ana).json()["items"]
    by = {l["company_name"]: l for l in items}
    assert set(by) == {"Sem Site Odonto", "Insta Odonto", "Landing Odonto", "Site Simples", "Site Fora do Ar", "Só Links"}
    assert by["Sem Site Odonto"]["landing_page_status"] == "none" and by["Sem Site Odonto"]["website"] is None
    assert by["Sem Site Odonto"]["phone"] == "1932345678" and by["Sem Site Odonto"]["city"] == "Campinas"
    assert by["Sem Site Odonto"]["segment"] == "Odontologia" and by["Sem Site Odonto"]["source"] == "ai_agent"
    assert by["Sem Site Odonto"]["source_url"].startswith("https://maps.google.com")
    assert by["Insta Odonto"]["instagram"] == "instaodonto" and by["Insta Odonto"]["landing_page_status"] == "none"
    assert by["Landing Odonto"]["landing_page_status"] == "has_landing" and by["Landing Odonto"]["website"] == "https://landing.example"
    assert by["Site Simples"]["landing_page_status"] == "site_only"
    assert by["Site Fora do Ar"]["landing_page_status"] == "unknown"
    assert by["Só Links"]["landing_page_status"] == "site_only"
    # pontuação feita pelo sistema: sem landing e sem site vale mais que quem já tem landing
    assert by["Sem Site Odonto"]["score"] > by["Landing Odonto"]["score"]
    assert "Google Places" in by["Sem Site Odonto"]["notes"]


def test_filters_without_site_and_landing_none(make_client, ana, fake):
    c = make_client(google_places_api_key="k")
    places_api(fake, [[place("p1", "Sem Site"), place("p2", "Com Landing", website="https://landing.example"), place("p3", "Site Simples", website="https://simples.example")]])
    fake.web_handler = sites({"landing.example": LANDING_HTML, "simples.example": SITE_ONLY_HTML})

    s = c.post("/api/prospecting/search", json={**SEARCH, "website_filter": "without_site"}, headers=ana).json()
    assert s["inserted_count"] == 1
    s = c.post("/api/prospecting/search", json={**SEARCH, "website_filter": "with_site", "landing_filter": "site_only"}, headers=ana).json()
    names = [l["company_name"] for l in c.get("/api/leads", params={"search_id": s["id"]}, headers=ana).json()["items"]]
    assert names == ["Site Simples"]


def test_pagination_and_desired_quantity_across_segments(make_client, ana, fake):
    c = make_client(google_places_api_key="k")
    page1 = [place(f"a{i}", f"Empresa A{i}") for i in range(3)]
    page2 = [place(f"b{i}", f"Empresa B{i}") for i in range(3)]
    cap = places_api(fake, [page1, page2])
    body = {**SEARCH, "segments": ["Odontologia"], "desired_quantity": 5}
    s = c.post("/api/prospecting/search", json=body, headers=ana).json()
    assert len(cap["calls"]) == 2 and cap["calls"][1]["body"]["pageToken"] == "tok1"
    assert s["inserted_count"] == 5  # 3 + 2: respeita a quantidade pedida


def test_duplicates_are_not_inserted_twice(make_client, ana, fake):
    c = make_client(google_places_api_key="k")
    places_api(fake, [[place("p1", "Empresa Repetida")]])
    first = c.post("/api/prospecting/search", json=SEARCH, headers=ana).json()
    second = c.post("/api/prospecting/search", json=SEARCH, headers=ana).json()
    assert (first["inserted_count"], second["inserted_count"], second["duplicates_count"]) == (1, 0, 1)


@pytest.mark.parametrize("status,body,expected", [
    (403, {"error": {"status": "PERMISSION_DENIED", "message": "Places API (New) has not been used in project 1 before or it is disabled."}}, "não está ativada"),
    (429, {"error": {"status": "RESOURCE_EXHAUSTED"}}, "cota"),
    (400, {"error": {"status": "INVALID_ARGUMENT", "message": "API key not valid. Please pass a valid API key."}}, "chave"),
    (500, {}, "erro (500)"),
])
def test_google_errors_are_explained_and_recorded(make_client, ana, fake, status, body, expected):
    c = make_client(google_places_api_key="k")
    places_api(fake, [[]], status=status, body=body)
    r = c.post("/api/prospecting/search", json=SEARCH, headers=ana)
    assert r.status_code == 502 and expected in r.json()["error"]["message"]
    history = c.get("/api/prospecting/history", headers=ana).json()
    assert history[0]["status"] == "failed" and expected in history[0]["error_message"]
    assert fake.rows["leads"] == []


def test_google_unreachable(make_client, ana, fake):
    c = make_client(google_places_api_key="k")

    def boom(request):
        raise httpx.ConnectError("sem rede")

    fake.places_handler = boom
    r = c.post("/api/prospecting/search", json=SEARCH, headers=ana)
    assert r.status_code == 502 and "conectar" in r.json()["error"]["message"]
