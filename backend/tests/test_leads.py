"""CRUD de leads: validação, pontuação, duplicidades, filtros, histórico, isolamento (RLS) e CSV."""
import uuid

from tests.conftest import lead


def create(client, headers, **kw):
    r = client.post("/api/leads", json=lead(**kw), headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------- criação / normalização
def test_create_minimal_lead_has_defaults_and_score(client, ana):
    body = create(client, ana, company_name="Padaria Pão Quente", city=None, state=None)
    assert body["status"] == "new" and body["source"] == "manual"
    assert body["landing_page_status"] == "unknown"
    assert body["score"] == 15 and body["priority"] == "low" and body["score_source"] == "rules"
    assert "owner_id" not in body


def test_score_rules_and_priority(client, ana):
    hot = create(client, ana, company_name="Sem Site Ltda", landing_page_status="none", whatsapp="(19) 99999-1111",
                 instagram="@semsite", contact_name="Maria")
    assert hot["score"] == 45 + 20 + 10 + 5 and hot["priority"] == "high"

    mid = create(client, ana, company_name="Só Telefone", landing_page_status="none", phone="1930001111")
    assert mid["score"] == 55 and mid["priority"] == "medium"

    done = create(client, ana, company_name="Já Tem Landing", landing_page_status="has_landing", whatsapp="19988887777")
    assert done["score"] == 20 and done["priority"] == "low"

    blocked = create(client, ana, company_name="Não Contatar", landing_page_status="none", whatsapp="19977776666",
                     do_not_contact=True)
    assert blocked["score"] == 0 and blocked["priority"] == "low"


def test_manual_score_and_recompute_on_update(client, ana):
    created = create(client, ana, landing_page_status="none", score=90)
    assert created["score"] == 90 and created["score_source"] == "manual" and created["priority"] == "high"

    # alterar outros campos mantém a pontuação manual
    r = client.put(f"/api/leads/{created['id']}", json={"notes": "ligar amanhã"}, headers=ana)
    assert r.json()["score"] == 90 and r.json()["score_source"] == "manual"

    # score = null devolve o controle às regras
    r = client.put(f"/api/leads/{created['id']}", json={"score": None}, headers=ana)
    assert r.json()["score"] == 45 and r.json()["score_source"] == "rules" and r.json()["priority"] == "medium"


def test_rules_score_follows_edits(client, ana):
    created = create(client, ana, landing_page_status="unknown")
    assert created["score"] == 15
    r = client.put(f"/api/leads/{created['id']}", json={"landing_page_status": "none", "whatsapp": "19999990000"}, headers=ana)
    assert r.json()["score"] == 65 and r.json()["priority"] == "medium"


def test_inputs_are_normalized(client, ana):
    body = create(
        client, ana, company_name="  Studio   Lume  ", state="sp", phone="+55 (11) 3000-1234", whatsapp="(11) 99999-0000",
        instagram="https://www.instagram.com/Studio.Lume/?hl=pt", website="WWW.StudioLume.com.br/", facebook="studiolume",
        source_url="fonte.com/pagina",
    )
    assert body["company_name"] == "Studio Lume" and body["state"] == "SP"
    assert body["phone"] == "551130001234" and body["whatsapp"] == "11999990000"
    assert body["instagram"] == "studio.lume"
    assert body["website"] == "https://www.studiolume.com.br"
    assert body["facebook"] == "https://facebook.com/studiolume"
    assert body["source_url"] == "https://fonte.com/pagina"


def test_invalid_inputs_are_rejected_with_field_messages(client, ana):
    cases = {
        "website": "javascript:alert(1)",
        "source_url": "data:text/html,<script>",
        "facebook": "ftp://x.com/y",
        "state": "XX",
        "phone": "123",
        "instagram": "não é válido!",
        "landing_page_status": "talvez",
        "score": 150,
    }
    for field, value in cases.items():
        r = client.post("/api/leads", json=lead(**{field: value}), headers=ana)
        assert r.status_code == 422, field
        assert r.json()["error"]["details"][0]["field"] == field


def test_duplicates_are_blocked_with_clear_messages(client, ana, bia):
    create(client, ana, company_name="Café do Zé", city="Campinas", phone="1930000000", whatsapp="19999990000",
           website="https://cafedoze.com.br")
    cases = [
        (dict(company_name="  CAFÉ DO ZÉ ", city="campinas"), "nome de empresa nesta cidade"),
        (dict(company_name="Outro 1", city="X", phone="(19) 3000-0000"), "telefone"),
        (dict(company_name="Outro 2", city="X", whatsapp="19 99999-0000"), "WhatsApp"),
        (dict(company_name="Outro 3", city="X", website="CAFEDOZE.com.br".lower()), "site"),
    ]
    for payload, expected in cases:
        r = client.post("/api/leads", json=payload, headers=ana)
        assert r.status_code == 409, payload
        assert r.json()["error"]["code"] == "duplicate_lead"
        assert expected in r.json()["error"]["message"]

    # mesma empresa em outra cidade é permitida; outro usuário também pode cadastrar a mesma empresa
    assert client.post("/api/leads", json=lead(company_name="Café do Zé", city="Sorocaba"), headers=ana).status_code == 201
    assert client.post("/api/leads", json=lead(company_name="Café do Zé", city="Campinas", phone="1930000000"), headers=bia).status_code == 201


def test_update_into_duplicate_is_blocked(client, ana):
    a = create(client, ana, company_name="A Empresa", phone="1930001111")
    b = create(client, ana, company_name="B Empresa")
    r = client.put(f"/api/leads/{b['id']}", json={"phone": "(19) 3000-1111"}, headers=ana)
    assert r.status_code == 409 and "telefone" in r.json()["error"]["message"]
    assert client.get(f"/api/leads/{a['id']}", headers=ana).status_code == 200


# --------------------------------------------------------------------------- leitura
def test_get_update_delete_cycle(client, ana):
    created = create(client, ana)
    lid = created["id"]
    assert client.get(f"/api/leads/{lid}", headers=ana).json()["company_name"] == "Clínica Sorriso"

    r = client.put(f"/api/leads/{lid}", json={"segment": "Odontologia", "contact_name": "Dra. Lúcia"}, headers=ana)
    assert r.status_code == 200 and r.json()["segment"] == "Odontologia" and r.json()["city"] == "Campinas"

    # null limpa campos opcionais; nome não pode ser vazio
    assert client.put(f"/api/leads/{lid}", json={"segment": None}, headers=ana).json()["segment"] is None
    assert client.put(f"/api/leads/{lid}", json={"company_name": None}, headers=ana).status_code == 422
    assert client.put(f"/api/leads/{lid}", json={"company_name": "   "}, headers=ana).status_code == 422

    assert client.delete(f"/api/leads/{lid}", headers=ana).status_code == 204
    assert client.get(f"/api/leads/{lid}", headers=ana).status_code == 404
    assert client.delete(f"/api/leads/{lid}", headers=ana).status_code == 404
    assert client.put(f"/api/leads/{lid}", json={"notes": "x"}, headers=ana).status_code == 404


def test_unknown_and_malformed_ids(client, ana):
    assert client.get(f"/api/leads/{uuid.uuid4()}", headers=ana).status_code == 404
    r = client.get("/api/leads/nao-e-uuid", headers=ana)
    assert r.status_code == 422 and r.json()["error"]["details"][0]["field"] == "lead_id"


def test_each_user_only_sees_their_own_leads(client, ana, bia):
    mine = create(client, ana, company_name="Só da Ana")
    assert client.get("/api/leads", headers=bia).json()["total"] == 0
    assert client.get(f"/api/leads/{mine['id']}", headers=bia).status_code == 404
    assert client.put(f"/api/leads/{mine['id']}", json={"notes": "invasão"}, headers=bia).status_code == 404
    assert client.patch(f"/api/leads/{mine['id']}/status", json={"status": "lost"}, headers=bia).status_code == 404
    assert client.delete(f"/api/leads/{mine['id']}", headers=bia).status_code == 404
    assert client.post(f"/api/leads/{mine['id']}/activities", json={"description": "x"}, headers=bia).status_code == 404
    assert client.get(f"/api/leads/{mine['id']}", headers=ana).json()["notes"] is None  # intacto


def _seed(client, ana):
    data = [
        dict(company_name="Alfa Odonto", segment="Odontologia", city="Campinas", state="SP", landing_page_status="none", whatsapp="19911110001", instagram="alfa"),
        dict(company_name="Beta Advogados", segment="Advocacia", city="Campinas", state="SP", landing_page_status="site_only", phone="1930001000"),
        dict(company_name="Gama Estética", segment="Estética", city="Curitiba", state="PR", landing_page_status="has_landing", whatsapp="41911110002"),
        dict(company_name="Delta Odonto Kids", segment="Odontologia", city="Curitiba", state="PR", landing_page_status="none", whatsapp="41911110003", contact_name="Paulo"),
    ]
    return [create(client, ana, **d) for d in data]


def test_list_filters_search_sort_pagination(client, ana):
    _seed(client, ana)

    def ids(**params):
        r = client.get("/api/leads", params=params, headers=ana)
        assert r.status_code == 200, r.text
        return [x["company_name"] for x in r.json()["items"]], r.json()["total"]

    assert ids()[1] == 4
    assert ids(search="odonto")[0] == ["Delta Odonto Kids", "Alfa Odonto"]  # mais recentes primeiro
    assert ids(search="paulo")[0] == ["Delta Odonto Kids"]  # busca também no responsável
    assert ids(segment="Odontologia")[1] == 2
    assert ids(city="Curitiba")[1] == 2
    assert ids(state="pr")[1] == 2
    assert ids(landing_status="none")[1] == 2
    assert ids(priority="high")[0] == ["Delta Odonto Kids", "Alfa Odonto"]
    assert ids(priority="low")[0] == ["Gama Estética"]

    names, _ = ids(sort="score_desc")
    assert names[0] == "Alfa Odonto" and names[-1] == "Gama Estética"  # 75, 70, 40, 20
    assert ids(sort="score_asc")[0][0] == "Gama Estética"
    assert ids(sort="name_asc")[0] == ["Alfa Odonto", "Beta Advogados", "Delta Odonto Kids", "Gama Estética"]

    page1 = client.get("/api/leads", params={"page_size": 3, "sort": "name_asc"}, headers=ana).json()
    page2 = client.get("/api/leads", params={"page_size": 3, "page": 2, "sort": "name_asc"}, headers=ana).json()
    assert (page1["total"], len(page1["items"]), len(page2["items"])) == (4, 3, 1)
    assert page2["items"][0]["company_name"] == "Gama Estética"

    # combinação de filtros e busca com caracteres especiais não quebra
    assert ids(segment="Odontologia", city="Campinas")[0] == ["Alfa Odonto"]
    assert ids(search="a%_*,()\"\\")[1] >= 0
    assert client.get("/api/leads", params={"sort": "hack"}, headers=ana).status_code == 422
    assert client.get("/api/leads", params={"page_size": 9999}, headers=ana).status_code == 422


def test_active_filter_excludes_closed_and_lost(client, ana):
    a, b, c = [create(client, ana, company_name=n) for n in ("L1", "L2", "L3")]
    client.patch(f"/api/leads/{b['id']}/status", json={"status": "closed_won"}, headers=ana)
    client.patch(f"/api/leads/{c['id']}/status", json={"status": "lost"}, headers=ana)
    active = client.get("/api/leads", params={"active": "true"}, headers=ana).json()
    assert [x["company_name"] for x in active["items"]] == ["L1"]
    assert client.get("/api/leads", headers=ana).json()["total"] == 3
    _ = a


def test_facets(client, ana):
    _seed(client, ana)
    f = client.get("/api/leads/facets", headers=ana).json()
    assert f["segments"] == ["Advocacia", "Estética", "Odontologia"]
    assert f["cities"] == ["Campinas", "Curitiba"] and f["states"] == ["PR", "SP"]
    assert f["priority_counts"] == {"high": 2, "medium": 1, "low": 1}
    assert f["priority_thresholds"] == {"high": 70, "medium": 40}
    assert f["status_counts"]["new"] == 4


# ------------------------------------------------------------------ pipeline e histórico
def test_status_move_logs_history_and_updates_timestamp(client, ana, fake):
    lid = create(client, ana)["id"]
    before = client.get(f"/api/leads/{lid}", headers=ana).json()["status_updated_at"]

    r = client.patch(f"/api/leads/{lid}/status", json={"status": "contacted"}, headers=ana)
    assert r.status_code == 200 and r.json()["status"] == "contacted"
    assert r.json()["status_updated_at"] >= before

    # mover para o mesmo estágio não gera histórico duplicado
    client.patch(f"/api/leads/{lid}/status", json={"status": "contacted"}, headers=ana)
    # PUT com status também registra a mudança
    client.put(f"/api/leads/{lid}", json={"status": "interested"}, headers=ana)

    acts = client.get(f"/api/leads/{lid}/activities", headers=ana).json()
    types = [a["type"] for a in acts]
    assert types.count("status_changed") == 2 and types.count("created") == 1
    descriptions = " | ".join(a["description"] for a in acts)
    assert "Novo lead" in descriptions and "Contato realizado" in descriptions and "Interessado" in descriptions

    assert client.patch(f"/api/leads/{lid}/status", json={"status": "inexistente"}, headers=ana).status_code == 422


def test_all_pipeline_stages_are_accepted(client, ana):
    lid = create(client, ana)["id"]
    for stage in ["analyzed", "contacted", "interested", "proposal_sent", "closed_won", "lost", "new"]:
        r = client.patch(f"/api/leads/{lid}/status", json={"status": stage}, headers=ana)
        assert r.status_code == 200 and r.json()["status"] == stage


def test_notes_and_activity_history(client, ana):
    lid = create(client, ana)["id"]
    r = client.post(f"/api/leads/{lid}/activities", json={"description": "  Liguei, pediu retorno na sexta.  "}, headers=ana)
    assert r.status_code == 201 and r.json()["type"] == "note"
    assert r.json()["description"] == "Liguei, pediu retorno na sexta."
    assert client.post(f"/api/leads/{lid}/activities", json={"description": "   "}, headers=ana).status_code == 422
    assert client.get(f"/api/leads/{uuid.uuid4()}/activities", headers=ana).status_code == 404

    client.put(f"/api/leads/{lid}", json={"segment": "Odonto"}, headers=ana)
    acts = client.get(f"/api/leads/{lid}/activities", headers=ana).json()
    assert acts[0]["type"] == "updated" and "segmento" in acts[0]["description"]


def test_delete_removes_history(client, ana, fake):
    lid = create(client, ana)["id"]
    assert fake.rows["lead_activities"]
    client.delete(f"/api/leads/{lid}", headers=ana)
    assert fake.rows["lead_activities"] == []


# ------------------------------------------------------------------------------ CSV
def test_csv_export_respects_filters_and_escapes_formulas(client, ana):
    create(client, ana, company_name="=HYPERLINK(\"http://evil\")", segment="Odontologia", notes="linha1\nlinha2; com ponto e vírgula")
    create(client, ana, company_name="Padaria Doce", segment="Alimentação")

    r = client.get("/api/leads/export", headers=ana)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    raw = r.content
    assert raw.startswith(b"\xef\xbb\xbf")  # BOM para o Excel
    text = raw.decode("utf-8-sig")
    lines = text.split("\r\n")
    assert lines[0].startswith("Empresa;Responsável;Segmento")
    assert "'=HYPERLINK" in text and ";=HYPERLINK" not in text and not text.startswith("=")
    assert "Padaria Doce" in text and "Nova" not in text
    assert '"linha1\nlinha2; com ponto e vírgula"' in text

    filtered = client.get("/api/leads/export", params={"segment": "Alimentação"}, headers=ana).content.decode("utf-8-sig")
    assert "Padaria Doce" in filtered and "HYPERLINK" not in filtered
    assert "Novo lead" in filtered  # estágio traduzido
    assert client.get("/api/leads/export").status_code == 401
