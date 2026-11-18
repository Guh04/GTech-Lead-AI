"""Limpeza de leads de dias anteriores: só apaga o que não andou no funil e não pediu opt-out."""
from datetime import datetime, timedelta, timezone

from tests.conftest import lead


def make(client, ana, fake, name, *, days_ago=0, **extra):
    r = client.post("/api/leads", json=lead(company_name=name, city=name, **extra), headers=ana)
    assert r.status_code == 201, r.text
    row = next(x for x in fake.rows["leads"] if x["id"] == r.json()["id"])
    row["created_at"] = (datetime.now(timezone.utc) - timedelta(days=days_ago, hours=1 if days_ago else 0)).isoformat()
    return r.json()["id"]


def names(fake):
    return {x["company_name"] for x in fake.rows["leads"]}


def test_requires_login(client):
    assert client.get("/api/leads/cleanup/preview").status_code == 401
    assert client.post("/api/leads/cleanup").status_code == 401


def test_preview_deletes_nothing(client, ana, fake):
    make(client, ana, fake, "Hoje")
    make(client, ana, fake, "Ontem", days_ago=1)
    make(client, ana, fake, "Contatado", days_ago=2, status="contacted")
    r = client.get("/api/leads/cleanup/preview", headers=ana).json()
    assert r == {"deletable": 1, "protected": 1}
    assert names(fake) == {"Hoje", "Ontem", "Contatado"}


def test_cleanup_keeps_today_and_protects_progress_and_opt_out(client, ana, fake):
    make(client, ana, fake, "Hoje")
    make(client, ana, fake, "Ontem Novo", days_ago=1)
    make(client, ana, fake, "Antigo Analisado", days_ago=5, status="analyzed")
    make(client, ana, fake, "Antigo Contatado", days_ago=3, status="contacted")
    make(client, ana, fake, "Antigo Interessado", days_ago=3, status="interested")
    make(client, ana, fake, "Antigo Opt Out", days_ago=3, do_not_contact=True)
    r = client.post("/api/leads/cleanup", headers=ana)
    assert r.status_code == 200 and r.json() == {"deleted": 2}
    assert names(fake) == {"Hoje", "Antigo Contatado", "Antigo Interessado", "Antigo Opt Out"}


def test_cleanup_also_removes_history_and_queue_of_deleted_leads(client, ana, fake):
    old = make(client, ana, fake, "Antigo", days_ago=2, whatsapp="11999990000", landing_page_status="none")
    client.post("/api/outreach/generate", json={"count": 5}, headers=ana)
    assert fake.rows["outreach_messages"] and fake.rows["lead_activities"]
    client.post("/api/leads/cleanup", headers=ana)
    assert old not in {x["id"] for x in fake.rows["leads"]}
    assert fake.rows["outreach_messages"] == [] and fake.rows["lead_activities"] == []


def test_cleanup_is_per_user(client, ana, bia, fake):
    make(client, ana, fake, "Da Ana", days_ago=2)
    assert client.post("/api/leads/cleanup", headers=bia).json() == {"deleted": 0}
    assert names(fake) == {"Da Ana"}


def test_cleanup_including_today_keeps_only_contacted_and_opt_out(client, ana, fake):
    make(client, ana, fake, "Hoje Novo")
    make(client, ana, fake, "Ontem Novo", days_ago=1)
    make(client, ana, fake, "Hoje Contatado", status="contacted")
    make(client, ana, fake, "Hoje Interessado", status="interested")
    make(client, ana, fake, "Hoje Opt Out", do_not_contact=True)
    assert client.get("/api/leads/cleanup/preview", params={"include_today": "true"}, headers=ana).json() == {"deletable": 2, "protected": 3}
    assert names(fake) >= {"Hoje Novo"}  # a prévia não apaga nada
    r = client.post("/api/leads/cleanup", params={"include_today": "true"}, headers=ana)
    assert r.json() == {"deleted": 2}
    assert names(fake) == {"Hoje Contatado", "Hoje Interessado", "Hoje Opt Out"}


def test_default_cleanup_still_keeps_today(client, ana, fake):
    make(client, ana, fake, "Hoje Novo")
    assert client.post("/api/leads/cleanup", headers=ana).json() == {"deleted": 0}
    assert names(fake) == {"Hoje Novo"}
