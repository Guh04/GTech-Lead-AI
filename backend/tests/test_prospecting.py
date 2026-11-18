"""Prospecção: nada é simulado quando não há agente; com agente, os leads são gravados sem duplicar."""
import httpx

from tests.conftest import lead

SEARCH = {
    "region": "Campinas", "state": "sp", "segments": ["Odontologia", " odontologia ", "Advocacia"],
    "desired_quantity": 10, "website_filter": "without_site", "landing_filter": "none",
}


def test_status_without_agent_is_honest(client, ana):
    s = client.get("/api/prospecting/status", headers=ana).json()
    assert s["available"] is False and "agente" in s["message"].lower()
    assert client.get("/api/prospecting/history", headers=ana).json() == []


def test_search_without_agent_returns_503_and_creates_nothing(client, ana, fake):
    r = client.post("/api/prospecting/search", json=SEARCH, headers=ana)
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "prospecting_not_configured"
    assert fake.rows["prospecting_searches"] == [] and fake.rows["leads"] == []  # nenhum resultado falso


def test_search_validation(client, ana):
    bad = [
        {**SEARCH, "segments": []},
        {**SEARCH, "region": " "},
        {**SEARCH, "desired_quantity": 0},
        {**SEARCH, "desired_quantity": 501},
        {**SEARCH, "state": "ZZ"},
        {**SEARCH, "website_filter": "talvez"},
    ]
    for payload in bad:
        assert client.post("/api/prospecting/search", json=payload, headers=ana).status_code == 422, payload
    assert client.post("/api/prospecting/search", json=SEARCH).status_code == 401


def agent_with(fake, leads=None, status=200):
    captured = {}

    def handler(request: httpx.Request):
        import json

        captured["body"] = json.loads(request.content)
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(status, json={"leads": leads or []})

    fake.agent_handler = handler
    return captured


def test_search_with_agent_saves_leads_dedupes_and_records_history(make_client, ana, fake):
    c = make_client(prospecting_api_url="https://agent.test/api", prospecting_api_key="chave-do-agente")
    # lead já existente: o agente vai devolvê-lo de novo
    assert c.post("/api/leads", json=lead(company_name="Já Existia", city="Campinas"), headers=ana).status_code == 201
    captured = agent_with(fake, leads=[
        {"company_name": "Nova 1", "city": "Campinas", "state": "SP", "segment": "Odontologia", "landing_page_status": "none",
         "whatsapp": "(19) 99999-0001", "source_url": "https://maps.exemplo/nova1", "score": 100, "status": "closed_won"},
        {"company_name": "Nova 2", "city": "Campinas", "state": "SP", "website": "nova2.com.br"},
        {"company_name": "Já Existia", "city": "Campinas"},
        {"city": "Sem nome"},  # inválido
    ])
    assert c.get("/api/prospecting/status", headers=ana).json() == {"available": True, "provider": "api-externa", "message": "Agente de prospecção conectado."}

    r = c.post("/api/prospecting/search", json=SEARCH, headers=ana)
    assert r.status_code == 201, r.text
    s = r.json()
    assert (s["status"], s["results_count"], s["inserted_count"], s["duplicates_count"]) == ("completed", 4, 2, 1)
    assert "descartado" in s["error_message"]
    assert s["segments"] == ["Odontologia", "Advocacia"] and s["state"] == "SP"

    # contrato enviado ao agente
    assert captured["body"]["region"] == "Campinas" and captured["body"]["website_filter"] == "without_site"
    assert captured["auth"] == "Bearer chave-do-agente"

    # leads gravados com origem do agente, vinculados à pesquisa, estágio inicial e pontuação PRÓPRIA (não a do agente)
    found = c.get("/api/leads", params={"search_id": s["id"], "sort": "score_desc"}, headers=ana).json()
    assert found["total"] == 2
    top = found["items"][0]
    assert top["company_name"] == "Nova 1" and top["source"] == "ai_agent" and top["status"] == "new"
    assert top["score"] == 45 + 20 and top["score_source"] == "rules"
    assert top["prospecting_search_id"] == s["id"]

    hist = c.get("/api/prospecting/history", headers=ana).json()
    assert len(hist) == 1 and hist[0]["id"] == s["id"]


def test_quantity_limits_how_many_leads_are_saved(make_client, ana, fake):
    c = make_client(prospecting_api_url="https://agent.test")
    agent_with(fake, leads=[{"company_name": f"E{i}"} for i in range(8)])
    s = c.post("/api/prospecting/search", json={**SEARCH, "desired_quantity": 3}, headers=ana).json()
    assert s["inserted_count"] == 3


def test_agent_failure_is_reported_and_logged(make_client, ana, fake):
    c = make_client(prospecting_api_url="https://agent.test")
    agent_with(fake, status=500)
    r = c.post("/api/prospecting/search", json=SEARCH, headers=ana)
    assert r.status_code == 502 and r.json()["error"]["code"] == "prospecting_failed"
    hist = c.get("/api/prospecting/history", headers=ana).json()
    assert hist[0]["status"] == "failed" and "500" in hist[0]["error_message"]

    fake.agent_handler = lambda request: (_ for _ in ()).throw(httpx.ConnectError("offline"))
    r = c.post("/api/prospecting/search", json=SEARCH, headers=ana)
    assert r.status_code == 502 and "conectar" in r.json()["error"]["message"]

    fake.agent_handler = lambda request: httpx.Response(200, json={"resultado": []})
    assert c.post("/api/prospecting/search", json=SEARCH, headers=ana).status_code == 502


def test_history_is_private_per_user(make_client, ana, bia, fake):
    c = make_client(prospecting_api_url="https://agent.test")
    agent_with(fake, leads=[{"company_name": "Algo"}])
    c.post("/api/prospecting/search", json=SEARCH, headers=ana)
    assert len(c.get("/api/prospecting/history", headers=ana).json()) == 1
    assert c.get("/api/prospecting/history", headers=bia).json() == []
