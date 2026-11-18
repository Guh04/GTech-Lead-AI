"""Contatos publicados no site da própria empresa (WhatsApp, telefone, Instagram, Facebook) viram dados do lead."""
import httpx
import pytest

from app.services.prospecting import site_analysis as sa
from app.services.prospecting.openstreetmap import tags_for_segment
from tests.test_openstreetmap import SEARCH, el, osm

BODY = "texto " * 80


def page(*links):
    anchors = "".join(f"<a href='{h}'>x</a>" for h in links)
    return f"<html><head><title>Empresa</title></head><body><h1>Oi</h1><p>{BODY}</p>{anchors}</body></html>"


@pytest.fixture(autouse=True)
def dns(monkeypatch):
    async def fake_resolve(host):
        return ["93.184.216.34"]

    monkeypatch.setattr(sa, "resolve_host", fake_resolve)


def test_extract_contacts_reads_explicit_links_only():
    got = sa.extract_contacts([
        "https://instagram.com/p/ABC123/",                 # post, não é perfil
        "https://www.instagram.com/clinica.sorriso/?hl=pt",
        "https://facebook.com/sharer/sharer.php?u=x",      # botão de compartilhar
        "https://www.facebook.com/clinicasorriso/",
        "https://wa.me/5519999990001?text=Oi",
        "https://api.whatsapp.com/send?phone=5519988887777&text=Oi",  # segundo WhatsApp: o primeiro vence
        "tel:+55 (19) 3342-5050",
        "https://wa.link/abc123",                          # link curto sem número: ignorado
        "mailto:contato@empresa.com",
    ])
    assert got == {
        "instagram": "clinica.sorriso", "facebook": "https://facebook.com/clinicasorriso",
        "whatsapp": "5519999990001", "phone": "551933425050",
    }
    assert sa.extract_contacts(["https://wa.link/abc", "tel:123", "https://example.com"]) == {}


def test_extract_contacts_handles_whatsapp_url_variants():
    assert sa.extract_contacts(["https://api.whatsapp.com/send/?phone=5511911112222&type=phone_number"]) == {"whatsapp": "5511911112222"}
    assert sa.extract_contacts(["whatsapp://send?phone=5511933334444"]) == {"whatsapp": "5511933334444"}
    assert sa.extract_contacts(["https://web.whatsapp.com/send?phone=+5511955556666"]) == {"whatsapp": "5511955556666"}


def test_site_contacts_fill_missing_lead_fields(make_client, ana, fake):
    c = make_client(osm_enabled=True)
    html = page("https://wa.me/5519999990001", "https://instagram.com/odontorm", "https://facebook.com/odontorm", "tel:+551933425050")
    fake.web_handler = lambda r: httpx.Response(200, text=html, headers={"content-type": "text/html"})
    osm(fake, [el(1, "Odonto RM", website="https://www.odontorm.example/")])
    s = c.post("/api/prospecting/search", json=SEARCH, headers=ana).json()
    lead = c.get("/api/leads", params={"search_id": s["id"]}, headers=ana).json()["items"][0]
    assert lead["whatsapp"] == "5519999990001" and lead["phone"] == "551933425050"
    assert lead["instagram"] == "odontorm" and lead["facebook"] == "https://facebook.com/odontorm"
    assert "lidos do site" in lead["notes"] and "WhatsApp" in lead["notes"]


def test_provider_data_wins_over_site_data(make_client, ana, fake):
    c = make_client(osm_enabled=True)
    html = page("https://wa.me/5519999990001", "https://instagram.com/do_site", "tel:+551933425050")
    fake.web_handler = lambda r: httpx.Response(200, text=html, headers={"content-type": "text/html"})
    osm(fake, [el(1, "Odonto RM", website="https://www.odontorm.example/", phone="19 3000-0000",
                  **{"contact:whatsapp": "+55 19 98888-0002", "contact:instagram": "do_osm"})])
    s = c.post("/api/prospecting/search", json=SEARCH, headers=ana).json()
    lead = c.get("/api/leads", params={"search_id": s["id"]}, headers=ana).json()["items"][0]
    assert (lead["whatsapp"], lead["phone"], lead["instagram"]) == ("5519988880002", "1930000000", "do_osm")
    assert "lidos do site" not in lead["notes"]


def test_whatsapp_link_used_as_website_becomes_whatsapp(make_client, ana, fake):
    c = make_client(osm_enabled=True)
    osm(fake, [el(1, "Só Zap", website="https://wa.me/5519977776666")])
    s = c.post("/api/prospecting/search", json=SEARCH, headers=ana).json()
    lead = c.get("/api/leads", params={"search_id": s["id"]}, headers=ana).json()["items"][0]
    assert lead["whatsapp"] == "5519977776666"


def test_osm_mobile_tag_is_used_as_phone_and_new_segments_exist(make_client, ana, fake):
    c = make_client(osm_enabled=True)
    osm(fake, [el(1, "Dentista Mobile", mobile="+55 19 98888-1111")])
    s = c.post("/api/prospecting/search", json=SEARCH, headers=ana).json()
    lead = c.get("/api/leads", params={"search_id": s["id"]}, headers=ana).json()["items"][0]
    assert lead["phone"] == "5519988881111"
    for seg in ["Ótica", "Floricultura", "Cafeteria", "Pousada", "Estúdio de tatuagem", "Lava-jato", "Eletricista", "Encanador",
                "Marcenaria", "Mercado", "Loja de roupas", "Ferragem"]:
        assert tags_for_segment(seg), seg
    assert tags_for_segment("Barbearia") == [("shop", "hairdresser")]  # "bar..." não vira outra coisa
