"""Provedor gratuito OpenStreetMap (Nominatim + Overpass). Nenhuma chamada real: tudo é simulado."""
from urllib.parse import parse_qs

import httpx
import pytest

from app.services.prospecting import site_analysis as sa
from app.services.prospecting.openstreetmap import tags_for_segment

SEARCH = {"region": "Campinas", "state": "SP", "segments": ["Clínica odontológica"], "desired_quantity": 10}
LANDING_HTML = "<html><head><title>Odonto</title></head><body><h1>Implantes</h1><p>%s</p><a href='https://wa.me/5519999990001'>Fale conosco</a></body></html>" % ("texto " * 80)


@pytest.fixture(autouse=True)
def dns(monkeypatch):
    async def fake_resolve(host):
        return ["93.184.216.34"]

    monkeypatch.setattr(sa, "resolve_host", fake_resolve)


def el(i, name, kind="dentist", **tags):
    base = {"amenity": "dentist"} if kind == "dentist" else {"shop": "hairdresser"}
    return {"type": "node", "id": i, "tags": {**base, **({"name": name} if name else {}), **tags}}


def osm(fake, elements, area_found=True, status=200, nominatim_status=200):
    seen = {"nominatim": [], "overpass": []}

    def nominatim(request: httpx.Request):
        seen["nominatim"].append(dict(request.url.params))
        if nominatim_status != 200:
            return httpx.Response(nominatim_status, text="busy")
        if not area_found:
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=[
            {"osm_type": "node", "osm_id": 5, "category": "place"},  # ignorado: não é limite administrativo
            {"osm_type": "relation", "osm_id": 123, "category": "boundary", "type": "administrative"},
        ])

    def overpass(request: httpx.Request):
        query = parse_qs(request.content.decode())["data"][0]
        seen["overpass"].append({"query": query, "ua": request.headers.get("user-agent")})
        if status != 200:
            return httpx.Response(status, text="busy")
        return httpx.Response(200, json={"elements": elements})

    fake.nominatim_handler, fake.overpass_handler = nominatim, overpass
    return seen


def test_segment_mapping():
    assert ("amenity", "dentist") in tags_for_segment("Clínica odontológica")
    assert ("shop", "pet") in tags_for_segment("Pet shop")
    assert ("office", "lawyer") in tags_for_segment("Advocacia")
    assert ("shop", "hairdresser") in tags_for_segment("Salão de beleza")
    assert tags_for_segment("Energia solar") == [] and tags_for_segment("Competência") == []
    for s in ["Clínica odontológica", "Clínica de estética", "Advocacia", "Contabilidade", "Imobiliária", "Academia", "Salão de beleza",
              "Barbearia", "Restaurante", "Pet shop", "Oficina mecânica", "Arquitetura e design", "Psicologia", "Fisioterapia",
              "Escola de idiomas", "Autoescola", "Fotografia", "Construção e reformas"]:
        assert tags_for_segment(s), s


def test_default_provider_is_osm_and_can_be_disabled(make_client, ana):
    assert make_client(osm_enabled=True).get("/api/prospecting/status", headers=ana).json()["provider"] == "openstreetmap"
    assert make_client(osm_enabled=True, google_places_api_key="k").get("/api/prospecting/status", headers=ana).json()["provider"] == "google-places"
    assert make_client(osm_enabled=True, prospecting_api_url="https://agent.test").get("/api/prospecting/status", headers=ana).json()["provider"] == "api-externa"
    assert make_client(osm_enabled=False).get("/api/prospecting/status", headers=ana).json()["available"] is False


def test_search_saves_leads_with_osm_data(make_client, ana, fake):
    c = make_client(osm_enabled=True)
    fake.web_handler = lambda r: httpx.Response(200, text=LANDING_HTML, headers={"content-type": "text/html"})
    seen = osm(fake, [
        el(1, "Oralcamp", phone="+55 19 3342 5050", **{"addr:street": "Rua Visconde de Taunay", "addr:housenumber": "184"}),
        el(2, "Odonto RM", website="https://www.odontorm.example/", **{"contact:whatsapp": "+55 19 99999-0002"}),
        el(3, "Odonto Insta", **{"contact:instagram": "https://instagram.com/odontoinsta"}),
        el(4, None),  # sem nome: descartado
        el(1, "Oralcamp"),  # repetido
    ])
    r = c.post("/api/prospecting/search", json=SEARCH, headers=ana)
    assert r.status_code == 201, r.text
    s = r.json()
    assert (s["status"], s["inserted_count"], s["provider"]) == ("completed", 3, "openstreetmap")

    by = {l["company_name"]: l for l in c.get("/api/leads", params={"search_id": s["id"]}, headers=ana).json()["items"]}
    assert by["Oralcamp"]["landing_page_status"] == "none" and by["Oralcamp"]["phone"] == "551933425050"
    assert by["Oralcamp"]["source_url"] == "https://www.openstreetmap.org/node/1" and by["Oralcamp"]["city"] == "Campinas"
    assert "OpenStreetMap" in by["Oralcamp"]["notes"] and "Rua Visconde de Taunay" in by["Oralcamp"]["notes"]
    assert by["Odonto RM"]["landing_page_status"] == "has_landing" and by["Odonto RM"]["whatsapp"] == "5519999990002"
    assert by["Odonto Insta"]["instagram"] == "odontoinsta" and by["Odonto Insta"]["landing_page_status"] == "none"

    # município via Nominatim (nome completo do estado) e UMA consulta ao Overpass; User-Agent identificado
    assert seen["nominatim"] == [{"city": "Campinas", "country": "Brasil", "format": "jsonv2", "limit": "5", "state": "São Paulo"}]
    assert len(seen["overpass"]) == 1
    assert "area(3600000123)" in seen["overpass"][0]["query"] and 'nwr["amenity"="dentist"](area.a)' in seen["overpass"][0]["query"]
    assert "GTechLeadAI" in seen["overpass"][0]["ua"]


def test_multiple_segments_use_one_query_and_each_place_goes_to_its_segment(make_client, ana, fake):
    c = make_client(osm_enabled=True)
    seen = osm(fake, [el(1, "Dentista A"), el(2, "Barbearia B", kind="hair"), el(3, "Dentista C")])
    body = {**SEARCH, "segments": ["Odontologia", "Barbearia"]}
    s = c.post("/api/prospecting/search", json=body, headers=ana).json()
    assert len(seen["overpass"]) == 1
    q = seen["overpass"][0]["query"]
    assert 'nwr["amenity"="dentist"]' in q and 'nwr["shop"="hairdresser"]' in q
    by = {l["company_name"]: l["segment"] for l in c.get("/api/leads", params={"search_id": s["id"]}, headers=ana).json()["items"]}
    assert by == {"Dentista A": "Odontologia", "Dentista C": "Odontologia", "Barbearia B": "Barbearia"}


def test_without_site_filter(make_client, ana, fake):
    c = make_client(osm_enabled=True)
    osm(fake, [el(1, "Sem Site"), el(2, "Com Site", website="https://x.example")])
    s = c.post("/api/prospecting/search", json={**SEARCH, "website_filter": "without_site"}, headers=ana).json()
    assert s["inserted_count"] == 1


def test_query_injection_is_not_possible(make_client, ana, fake):
    c = make_client(osm_enabled=True)
    seen = osm(fake, [])
    c.post("/api/prospecting/search", json={**SEARCH, "region": 'X"];out;//', "segments": ["Odontologia"]}, headers=ana)
    # o nome do município vai só ao Nominatim (como parâmetro de URL); a consulta Overpass usa apenas o id numérico
    assert seen["overpass"] and '"];out;//' not in seen["overpass"][0]["query"]


@pytest.mark.parametrize("kwargs,expected", [
    ({"area_found": False}, "não encontrado"),
    ({"nominatim_status": 429}, "ocupado"),
    ({"nominatim_status": 500}, "erro (500)"),
    ({"status": 429}, "ocupado"),
    ({"status": 502}, "ocupado"),
    ({"status": 500}, "erro (500)"),
])
def test_osm_errors_are_explained(make_client, ana, fake, kwargs, expected):
    c = make_client(osm_enabled=True)
    osm(fake, [], **kwargs)
    r = c.post("/api/prospecting/search", json=SEARCH, headers=ana)
    assert r.status_code == 502 and expected in r.json()["error"]["message"]
    assert c.get("/api/prospecting/history", headers=ana).json()[0]["status"] == "failed"
    assert fake.rows["leads"] == []


def test_unsupported_segment_lists_supported_ones(make_client, ana, fake):
    c = make_client(osm_enabled=True)
    seen = osm(fake, [])
    r = c.post("/api/prospecting/search", json={**SEARCH, "segments": ["Energia solar", "Advocacia"]}, headers=ana)
    msg = r.json()["error"]["message"]
    assert r.status_code == 502 and "Energia solar" in msg and "advocacia" in msg
    assert seen == {"nominatim": [], "overpass": []}  # nem chegou a consultar os serviços


def test_transient_failure_is_retried_then_falls_back_to_mirror(make_client, ana, fake):
    c = make_client(osm_enabled=True)
    osm(fake, [])
    hosts = []

    def handler(request: httpx.Request):
        hosts.append(request.url.host)
        if request.url.host == "overpass-api.de":
            return httpx.Response(502, text="Bad gateway")
        return httpx.Response(200, json={"elements": [el(9, "Só no Espelho")]})

    fake.overpass_handler = handler
    s = c.post("/api/prospecting/search", json=SEARCH, headers=ana).json()
    assert s["inserted_count"] == 1
    assert hosts == ["overpass-api.de", "overpass-api.de", "overpass.kumi.systems"]
