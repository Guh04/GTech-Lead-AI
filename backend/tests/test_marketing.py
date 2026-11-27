"""Necessidade de marketing (avaliação manual do Instagram) e filtro por área da parceria."""
from tests.conftest import lead


def create(client, headers, **kw):
    r = client.post("/api/leads", json=lead(**kw), headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def names(client, headers, **params):
    r = client.get("/api/leads", params=params, headers=headers)
    assert r.status_code == 200, r.text
    return sorted(i["company_name"] for i in r.json()["items"])


def test_without_instagram_needs_marketing(client, ana):
    body = create(client, ana, company_name="Sem Insta", instagram=None)
    assert body["marketing_score"] == 70 and body["ig_last_post"] == "unknown" and body["ig_checked_at"] is None


def test_instagram_not_evaluated_is_pending(client, ana):
    body = create(client, ana, company_name="Com Insta", instagram="@cominsta")
    assert body["marketing_score"] is None


def test_evaluation_computes_score_and_date(client, ana):
    created = create(client, ana, company_name="Parado", instagram="@parado")
    r = client.put(f"/api/leads/{created['id']}", json={
        "ig_last_post": "older", "ig_engagement": "low", "ig_quality": "amateur", "ig_followers": 300,
    }, headers=ana)
    body = r.json()
    assert r.status_code == 200, r.text
    assert body["marketing_score"] == 45 + 15 + 20 + 10
    assert body["ig_checked_at"] is not None

    # perfil ativo e profissional: pouca necessidade
    r = client.put(f"/api/leads/{created['id']}", json={
        "ig_last_post": "week", "ig_engagement": "good", "ig_quality": "professional", "ig_followers": 12000,
    }, headers=ana)
    assert r.json()["marketing_score"] == 0

    # editar outro campo não apaga a avaliação nem a data
    checked = r.json()["ig_checked_at"]
    r = client.put(f"/api/leads/{created['id']}", json={"notes": "ok"}, headers=ana)
    assert r.json()["marketing_score"] == 0 and r.json()["ig_checked_at"] == checked

    # enviar null em campo obrigatório é ignorado (não quebra o banco)
    r = client.put(f"/api/leads/{created['id']}", json={"ig_last_post": None}, headers=ana)
    assert r.status_code == 200 and r.json()["ig_last_post"] == "week"


def test_removing_instagram_turns_into_marketing_need(client, ana):
    created = create(client, ana, company_name="Vai Sair", instagram="@vaisair")
    r = client.put(f"/api/leads/{created['id']}", json={"instagram": None}, headers=ana)
    assert r.json()["marketing_score"] == 70


def test_invalid_values_are_rejected(client, ana):
    created = create(client, ana, company_name="Inválido", instagram="@x1")
    r = client.put(f"/api/leads/{created['id']}", json={"ig_last_post": "ontem"}, headers=ana)
    assert r.status_code == 422
    r = client.put(f"/api/leads/{created['id']}", json={"ig_followers": -5}, headers=ana)
    assert r.status_code == 422


def test_filter_by_partnership_area_and_counts(client, ana):
    create(client, ana, company_name="So Site", landing_page_status="none", instagram="@sosite",
           ig_last_post="week", ig_engagement="good", ig_quality="professional")
    create(client, ana, company_name="So Marketing", landing_page_status="has_landing", instagram="@somkt",
           ig_last_post="none", ig_engagement="none", ig_quality="amateur")
    create(client, ana, company_name="Os Dois", landing_page_status="site_only", instagram=None)
    create(client, ana, company_name="A Avaliar", landing_page_status="has_landing", instagram="@avaliar")

    assert names(client, ana, need="site") == ["Os Dois", "So Site"]
    assert names(client, ana, need="marketing") == ["Os Dois", "So Marketing"]
    assert names(client, ana, need="both") == ["Os Dois"]
    assert names(client, ana, need="marketing_pending") == ["A Avaliar"]
    assert client.get("/api/leads", params={"need": "seo"}, headers=ana).status_code == 422

    r = client.get("/api/leads", params={"sort": "marketing_desc"}, headers=ana)
    order = [i["company_name"] for i in r.json()["items"]]
    assert order[0] == "So Marketing" and order[-1] == "A Avaliar"  # sem avaliação vai para o fim

    counts = client.get("/api/leads/facets", headers=ana).json()["need_counts"]
    assert counts == {"site": 2, "marketing": 2, "both": 1, "marketing_pending": 1}


def test_csv_has_marketing_columns(client, ana):
    create(client, ana, company_name="Csv Mkt", instagram="@csvmkt", ig_last_post="older", ig_followers=900)
    r = client.get("/api/leads/export", headers=ana)
    text = r.content.decode("utf-8-sig")
    header, row = text.splitlines()[:2]
    assert "Necessidade de marketing" in header and "Último post Instagram" in header
    assert "Mais de 3 meses" in row and "900" in row
