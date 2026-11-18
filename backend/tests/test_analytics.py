"""Dashboard e relatórios: números reais calculados a partir dos dados do banco."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from tests.conftest import lead

TZ = ZoneInfo("America/Sao_Paulo")


def mk(client, headers, name, **kw):
    r = client.post("/api/leads", json=lead(company_name=name, **kw), headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def backdate(fake, lead_id, days_ago, hour=12):
    """Altera created_at direto na 'tabela' (equivale a um lead cadastrado no passado)."""
    day = datetime.now(TZ).date() - timedelta(days=days_ago)
    when = datetime(day.year, day.month, day.day, hour, tzinfo=TZ).astimezone(timezone.utc)
    next(r for r in fake.rows["leads"] if r["id"] == lead_id)["created_at"] = when.isoformat()


def test_empty_database_returns_zeros(client, ana):
    d = client.get("/api/dashboard", headers=ana).json()
    assert d["totals"]["total"] == 0 and d["conversion_rate"] == 0
    assert d["leads_by_segment"] == [] and d["recent_activities"] == [] and d["latest_leads"] == []
    assert len(d["leads_by_period"]) == 30 and sum(p["count"] for p in d["leads_by_period"]) == 0

    r = client.get("/api/reports", headers=ana).json()
    assert r["total_in_period"] == 0 and r["leads_by_period"] != [] and r["conversion"]["win_rate"] is None
    assert client.get("/api/reports", params={"days": 0}, headers=ana).json()["leads_by_period"] == []


def test_dashboard_totals_conversion_and_lists(client, ana, fake):
    leads = [
        mk(client, ana, "L1", segment="Odontologia", landing_page_status="none", whatsapp="19911110001", instagram="l1", contact_name="X"),  # high
        mk(client, ana, "L2", segment="Odontologia"),
        mk(client, ana, "L3", segment="Advocacia"),
        mk(client, ana, "L4", segment=None),
        mk(client, ana, "L5", segment="Advocacia"),
        mk(client, ana, "L6", segment="Odontologia"),
    ]
    move = lambda i, s: client.patch(f"/api/leads/{leads[i]['id']}/status", json={"status": s}, headers=ana)  # noqa: E731
    move(1, "analyzed"); move(2, "contacted"); move(3, "interested"); move(4, "proposal_sent"); move(5, "closed_won")  # noqa: E702

    d = client.get("/api/dashboard", headers=ana).json()
    t = d["totals"]
    assert t == {"total": 6, "new": 1, "analyzed": 1, "contacted": 1, "interested": 1, "proposal_sent": 1,
                 "closed_won": 1, "lost": 0, "high_priority": 1}
    assert d["conversion_rate"] == round(100 / 6, 1)

    assert d["leads_by_segment"][0] == {"segment": "Odontologia", "count": 3}
    assert {"segment": "Sem segmento", "count": 1} in d["leads_by_segment"]

    assert [x["company_name"] for x in d["latest_leads"]][:2] == ["L6", "L5"]
    acts = d["recent_activities"]
    assert len(acts) == 10 and acts[0]["lead_name"] in {"L1", "L2", "L3", "L4", "L5", "L6"}
    assert acts[0]["type"] == "status_changed"


def test_dashboard_period_series_is_zero_filled_and_uses_local_timezone(client, ana, fake):
    a, b, c = mk(client, ana, "Hoje"), mk(client, ana, "Há3"), mk(client, ana, "Há3b")
    backdate(fake, b["id"], 3)
    backdate(fake, c["id"], 3, hour=23)  # 23h locais ainda é o mesmo dia local (mesmo que já seja o dia seguinte em UTC)
    old = mk(client, ana, "Antigo")
    backdate(fake, old["id"], 60)

    d = client.get("/api/dashboard", params={"days": 7}, headers=ana).json()
    series = {p["date"]: p["count"] for p in d["leads_by_period"]}
    today = datetime.now(TZ).date()
    assert len(series) == 7
    assert series[today.isoformat()] == 1
    assert series[(today - timedelta(days=3)).isoformat()] == 2
    assert sum(series.values()) == 3  # o lead de 60 dias atrás fica fora do gráfico, mas entra nos totais
    assert d["totals"]["total"] == 4
    assert client.get("/api/dashboard", params={"days": 3}, headers=ana).status_code == 422
    _ = a


def test_reports_period_granularity_and_funnel(client, ana, fake):
    leads = [mk(client, ana, f"R{i}", segment="Odontologia" if i % 2 else "Advocacia", state="SP" if i < 3 else "PR") for i in range(5)]
    client.patch(f"/api/leads/{leads[0]['id']}/status", json={"status": "closed_won"}, headers=ana)
    client.patch(f"/api/leads/{leads[1]['id']}/status", json={"status": "lost"}, headers=ana)
    client.patch(f"/api/leads/{leads[2]['id']}/status", json={"status": "closed_won"}, headers=ana)
    backdate(fake, leads[4]["id"], 200)

    r30 = client.get("/api/reports", params={"days": 30}, headers=ana).json()
    assert r30["granularity"] == "day" and len(r30["leads_by_period"]) == 30
    assert r30["total_in_period"] == 4 and r30["conversion"]["closed_won"] == 2
    assert r30["conversion"]["conversion_rate"] == 50.0
    assert r30["conversion"]["win_rate"] == round(2 * 100 / 3, 1)
    assert [f["status"] for f in r30["funnel"]] == ["new", "analyzed", "contacted", "interested", "proposal_sent", "closed_won", "lost"]
    assert {f["status"]: f["count"] for f in r30["funnel"]}["closed_won"] == 2
    assert {x["state"]: x["count"] for x in r30["leads_by_region"]} == {"SP": 3, "PR": 1}
    assert {x["segment"]: x["count"] for x in r30["leads_by_segment"]} == {"Odontologia": 2, "Advocacia": 2}
    assert {l["company_name"] for l in r30["closed_clients"]} == {"R0", "R2"}

    assert client.get("/api/reports", params={"days": 90}, headers=ana).json()["granularity"] == "week"
    r365 = client.get("/api/reports", params={"days": 365}, headers=ana).json()
    assert r365["granularity"] == "month" and r365["total_in_period"] == 5
    assert sum(p["count"] for p in r365["leads_by_period"]) == 5

    all_time = client.get("/api/reports", params={"days": 0}, headers=ana).json()
    assert all_time["granularity"] == "month" and all_time["total_in_period"] == 5
    assert all_time["leads_by_period"][0]["date"].endswith("-01")  # início de mês
    assert sum(p["count"] for p in all_time["leads_by_period"]) == 5


def test_analytics_are_isolated_per_user(client, ana, bia):
    mk(client, ana, "Da Ana")
    assert client.get("/api/dashboard", headers=bia).json()["totals"]["total"] == 0
    assert client.get("/api/reports", headers=bia).json()["total_in_period"] == 0
    assert client.get("/api/dashboard", headers=ana).json()["totals"]["total"] == 1


def test_large_datasets_are_paginated_when_reading(client, ana, fake):
    """O PostgREST limita respostas: a leitura precisa paginar para somar corretamente."""
    owner = next(iter(fake.tokens.values()))
    now = datetime.now(timezone.utc).isoformat()
    for i in range(2300):
        fake.rows["leads"].append({
            "id": f"00000000-0000-0000-0000-{i:012d}", "owner_id": owner, "company_name": f"B{i}", "segment": "Massa", "state": "SP",
            "status": "new", "priority": "low", "score": 15, "score_source": "rules", "source": "manual", "landing_page_status": "unknown",
            "do_not_contact": False, "created_at": now, "updated_at": now, "status_updated_at": now,
        })
    d = client.get("/api/dashboard", headers=ana).json()
    assert d["totals"]["total"] == 2300
    assert d["leads_by_segment"] == [{"segment": "Massa", "count": 2300}]
