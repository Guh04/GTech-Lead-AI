"""Abordagem por WhatsApp: a IA prepara, o usuário aprova e envia; limite diário protege o número."""
import json
from urllib.parse import parse_qs, urlsplit

import httpx

from tests.conftest import lead


def make_leads(client, ana, n=3, **extra):
    ids = []
    for i in range(n):
        r = client.post("/api/leads", json=lead(company_name=f"Empresa {i}", city=f"Cidade {i}", whatsapp=f"1199999000{i}", **extra), headers=ana)
        assert r.status_code == 201, r.text
        ids.append(r.json()["id"])
    return ids


def generate(client, ana, **body):
    return client.post("/api/outreach/generate", json={"count": 10, **body}, headers=ana)


def approve_and_send(client, ana, message_id):
    assert client.post(f"/api/outreach/{message_id}/approve", headers=ana).status_code == 200
    return client.post(f"/api/outreach/{message_id}/send", headers=ana)


def test_requires_login(client):
    assert client.get("/api/outreach/status").status_code == 401
    assert client.post("/api/outreach/generate", json={"count": 1}).status_code == 401


def test_generate_creates_drafts_only_for_eligible_leads(client, ana, fake):
    make_leads(client, ana, 2)
    client.post("/api/leads", json=lead(company_name="Sem Zap", city="X"), headers=ana)  # sem WhatsApp
    client.post("/api/leads", json=lead(company_name="Opt Out", city="Y", whatsapp="11988887777", do_not_contact=True), headers=ana)
    client.post("/api/leads", json=lead(company_name="Já Contatado", city="Z", whatsapp="11977776666", status="contacted"), headers=ana)

    r = generate(client, ana)
    assert r.status_code == 201
    assert r.json()["created"] == 2
    msgs = client.get("/api/outreach", headers=ana).json()
    assert {m["lead"]["company_name"] for m in msgs} == {"Empresa 0", "Empresa 1"}
    assert all(m["status"] == "draft" and m["source"] == "template" for m in msgs)
    assert all("avisar" in m["body"].lower() for m in msgs)  # opt-out sempre presente
    # Nada foi enviado nem o estágio do lead mudou.
    assert {l["status"] for l in fake.rows["leads"]} <= {"new", "contacted"}


def test_generate_is_idempotent_per_lead(client, ana):
    make_leads(client, ana, 2)
    assert generate(client, ana).json()["created"] == 2
    assert generate(client, ana).json()["created"] == 0  # leads já têm mensagem


def test_ai_message_is_used_when_key_is_set(make_client, ana, fake):
    captured = {}

    def handler(request: httpx.Request):
        captured["headers"], captured["body"] = request.headers, json.loads(request.content)
        return httpx.Response(200, json={"content": [{"type": "text", "text": "Oi! Sou o Gui da GTech. Posso ajudar?"}]})

    fake.anthropic_handler = handler
    c = make_client(anthropic_api_key="sk-test")
    make_leads(c, ana, 1)
    assert generate(c, ana).json()["created"] == 1
    msg = c.get("/api/outreach", headers=ana).json()[0]
    assert msg["source"] == "ai" and msg["body"].startswith("Oi! Sou o Gui")
    assert "avisar" in msg["body"].lower()  # opt-out acrescentado mesmo se a IA esquecer
    assert captured["headers"]["x-api-key"] == "sk-test"
    assert "Empresa 0" in captured["body"]["messages"][0]["content"]
    assert "whatsapp" not in captured["body"]["messages"][0]["content"].lower()  # telefone do lead não vai para a IA


def test_ai_failure_falls_back_to_template(make_client, ana, fake):
    fake.anthropic_handler = lambda request: httpx.Response(500, json={})
    c = make_client(anthropic_api_key="sk-test")
    make_leads(c, ana, 1)
    assert generate(c, ana).json()["created"] == 1
    assert c.get("/api/outreach", headers=ana).json()[0]["source"] == "template"


def test_cannot_send_without_approval(client, ana):
    make_leads(client, ana, 1)
    mid = generate(client, ana).json()["items"][0]["id"]
    r = client.post(f"/api/outreach/{mid}/send", headers=ana)
    assert r.status_code == 409 and r.json()["error"]["code"] == "not_approved"


def test_full_flow_sends_and_updates_lead(client, ana, fake):
    ids = make_leads(client, ana, 1)
    mid = generate(client, ana).json()["items"][0]["id"]
    r = approve_and_send(client, ana, mid)
    assert r.status_code == 200
    data = r.json()
    url = urlsplit(data["whatsapp_url"])
    assert url.netloc == "wa.me" and url.path == "/5511999990000"
    assert parse_qs(url.query)["text"][0] == data["message"]["body"]
    assert data["message"]["status"] == "sent" and data["message"]["sent_at"]
    assert data["status"]["sent_today"] == 1 and data["status"]["remaining"] == 19
    assert client.get(f"/api/leads/{ids[0]}", headers=ana).json()["status"] == "contacted"
    assert client.post(f"/api/outreach/{mid}/send", headers=ana).json()["error"]["code"] == "already_sent"


def test_edit_resets_approval(client, ana):
    make_leads(client, ana, 1)
    mid = generate(client, ana).json()["items"][0]["id"]
    client.post(f"/api/outreach/{mid}/approve", headers=ana)
    r = client.patch(f"/api/outreach/{mid}", json={"body": "  Texto novo.  "}, headers=ana)
    assert r.status_code == 200 and r.json()["body"] == "Texto novo." and r.json()["status"] == "draft"
    assert client.post(f"/api/outreach/{mid}/send", headers=ana).status_code == 409  # precisa aprovar de novo
    assert client.patch(f"/api/outreach/{mid}", json={"body": "  "}, headers=ana).status_code == 422
    assert client.patch(f"/api/outreach/{mid}", json={"body": "x" * 1001}, headers=ana).status_code == 422


def test_daily_limit_blocks_sending_and_generating(make_client, ana):
    c = make_client(outreach_daily_limit=2)
    make_leads(c, ana, 4)
    r = generate(c, ana)
    assert r.json()["created"] == 2  # a fila nunca passa do que ainda pode ser enviado hoje
    first, second = (m["id"] for m in r.json()["items"])
    assert approve_and_send(c, ana, first).status_code == 200
    assert approve_and_send(c, ana, second).status_code == 200
    assert c.get("/api/outreach/status", headers=ana).json()["remaining"] == 0

    blocked = generate(c, ana)
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "daily_limit_reached"
    # Mesmo aprovada, uma terceira mensagem não pode ser enviada.
    third = c.post("/api/leads", json=lead(company_name="Extra", city="Q", whatsapp="11955554444"), headers=ana).json()["id"]
    assert third


def test_limit_applies_even_for_manually_queued_extra_message(make_client, ana, fake):
    c = make_client(outreach_daily_limit=1)
    make_leads(c, ana, 2)
    first = generate(c, ana).json()["items"][0]["id"]
    assert approve_and_send(c, ana, first).status_code == 200
    # Cria um rascunho "à força" (como se tivesse sido gerado antes do limite) e tenta enviar.
    lead_id = next(l["id"] for l in fake.rows["leads"] if l["company_name"] == "Empresa 1")
    uid = fake.rows["leads"][0]["owner_id"]
    fake.rows["outreach_messages"].append({
        "id": "00000000-0000-4000-8000-000000000001", "owner_id": uid, "lead_id": lead_id, "body": "Oi",
        "status": "approved", "source": "template", "created_at": "2026-01-01T00:00:00+00:00", "approved_at": None, "sent_at": None,
    })
    r = c.post("/api/outreach/00000000-0000-4000-8000-000000000001/send", headers=ana)
    assert r.status_code == 429 and r.json()["error"]["code"] == "daily_limit_reached"


def test_minimum_interval_between_sends(make_client, ana):
    c = make_client(outreach_min_interval_seconds=300)
    make_leads(c, ana, 2)
    a, b = (m["id"] for m in generate(c, ana).json()["items"])
    assert approve_and_send(c, ana, a).status_code == 200
    r = approve_and_send(c, ana, b)
    assert r.status_code == 429 and r.json()["error"]["code"] == "too_soon"
    assert 0 < c.get("/api/outreach/status", headers=ana).json()["wait_seconds"] <= 300


def test_do_not_contact_set_after_queueing_blocks_send(client, ana):
    ids = make_leads(client, ana, 1)
    mid = generate(client, ana).json()["items"][0]["id"]
    client.post(f"/api/outreach/{mid}/approve", headers=ana)
    client.put(f"/api/leads/{ids[0]}", json={"do_not_contact": True}, headers=ana)
    r = client.post(f"/api/outreach/{mid}/send", headers=ana)
    assert r.status_code == 409 and r.json()["error"]["code"] == "do_not_contact"
    assert client.get("/api/outreach/status", headers=ana).json()["sent_today"] == 0


def test_skip_frees_nothing_but_removes_from_pending(client, ana):
    make_leads(client, ana, 1)
    mid = generate(client, ana).json()["items"][0]["id"]
    assert client.post(f"/api/outreach/{mid}/skip", headers=ana).json()["status"] == "skipped"
    assert client.post(f"/api/outreach/{mid}/approve", headers=ana).status_code == 409
    counts = client.get("/api/outreach/counts", headers=ana).json()
    assert counts["skipped"] == 1 and counts["draft"] == 0


def test_generate_limited_to_a_search(client, ana, fake):
    ids = make_leads(client, ana, 2)
    sid = "11111111-1111-4111-8111-111111111111"
    next(l for l in fake.rows["leads"] if l["id"] == ids[0])["prospecting_search_id"] = sid
    assert generate(client, ana, search_id=sid).json()["created"] == 1
    assert generate(client, ana, search_id="nao-e-uuid").status_code == 422


def test_users_are_isolated(client, ana, bia):
    make_leads(client, ana, 1)
    mid = generate(client, ana).json()["items"][0]["id"]
    assert client.get("/api/outreach", headers=bia).json() == []
    assert client.post(f"/api/outreach/{mid}/approve", headers=bia).status_code == 404
    assert client.get("/api/outreach/status", headers=bia).json()["sent_today"] == 0
