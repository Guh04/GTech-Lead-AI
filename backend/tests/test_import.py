"""Importação de planilhas de leads (.csv e .xlsx)."""
import io

from openpyxl import Workbook

CSV = (
    "Nome do negócio,Instagram,WhatsApp / Telefone,Status,Por que é um bom lead,Ramo,Bairro / Cidade,Site atual,Data encontrado\n"
    "Estética Kirei,'@estetica_kirei,(15) 98131-4488,Novo,Sem site,Estética,\"Parque Campolim, Sorocaba\",Não tem,2026-11-18\n"
    "Studio Dafne,'@studiodafne,(15) 3333-4444,Contato realizado,Só Instagram,Unhas,\"Vila Hortência, Sorocaba\",www.dafne.com.br,2026-11-18\n"
    ",,,,,,,,\n"
    "Sem Telefone Ruim,,123,Novo,x,Salão,Sorocaba,Não tem,\n"
)


def post(client, ana, content: bytes, name="leads.csv", dry_run=False):
    return client.post(f"/api/leads/import?filename={name}&dry_run={'true' if dry_run else 'false'}", content=content, headers=ana)


def test_requires_login(client):
    assert client.post("/api/leads/import", content=b"a,b\n1,2").status_code == 401


def test_dry_run_saves_nothing(client, ana, fake):
    r = post(client, ana, CSV.encode(), dry_run=True)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["valid"] == 2 and body["invalid"] == 1 and body["imported"] == 0
    assert fake.rows["leads"] == []


def test_import_maps_columns(client, ana, fake):
    body = post(client, ana, CSV.encode("utf-8-sig")).json()
    assert body["imported"] == 2 and body["invalid"] == 1
    by_name = {x["company_name"]: x for x in fake.rows["leads"]}
    kirei, dafne = by_name["Estética Kirei"], by_name["Studio Dafne"]
    assert kirei["whatsapp"] == "15981314488" and kirei["phone"] is None  # celular -> WhatsApp
    assert kirei["instagram"] == "estetica_kirei"  # apóstrofo removido
    assert kirei["city"] == "Sorocaba" and kirei["segment"] == "Estética"
    assert kirei["landing_page_status"] == "none" and kirei["source"] == "import" and kirei["status"] == "new"
    assert "Bairro: Parque Campolim" in kirei["notes"] and "Por que é um bom lead: Sem site" in kirei["notes"]
    assert dafne["phone"] == "1533334444" and dafne["whatsapp"] is None  # fixo -> telefone
    assert dafne["website"] == "https://www.dafne.com.br" and dafne["landing_page_status"] == "site_only"
    assert dafne["status"] == "contacted"


def test_invalid_rows_are_reported_with_line(client, ana):
    body = post(client, ana, CSV.encode()).json()
    assert {e["line"] for e in body["errors"]} == {5}  # linha vazia é ignorada; a do telefone "123" falha
    assert "Telefone" in body["errors"][0]["reason"] or "WhatsApp" in body["errors"][0]["reason"]


def test_duplicates_are_skipped(client, ana, fake):
    post(client, ana, CSV.encode())
    again = post(client, ana, CSV.encode()).json()
    assert again["imported"] == 0 and again["duplicates"] == 2
    assert len(fake.rows["leads"]) == 2


def test_duplicate_inside_same_file(client, ana, fake):
    csv = "Empresa;Cidade\nA Loja;Sorocaba\na loja;sorocaba\n"
    body = post(client, ana, csv.encode()).json()
    assert body["imported"] == 1 and body["duplicates"] == 1


def test_semicolon_and_latin1(client, ana, fake):
    csv = "Empresa;Telefone;Cidade\nPadaria São João;(11) 3000-1111;Campinas\n".encode("cp1252")
    assert post(client, ana, csv).json()["imported"] == 1
    assert fake.rows["leads"][0]["company_name"] == "Padaria São João"


def test_xlsx(client, ana, fake):
    wb = Workbook()
    ws = wb.active
    ws.append(["Empresa", "WhatsApp", "Segmento"])
    ws.append(["Clínica Azul", 11987654321, "Clínica"])
    buf = io.BytesIO()
    wb.save(buf)
    body = post(client, ana, buf.getvalue(), name="leads.xlsx").json()
    assert body["imported"] == 1
    assert fake.rows["leads"][0]["whatsapp"] == "11987654321"


def test_roundtrip_of_own_export(client, ana, fake):
    client.post("/api/leads", json={"company_name": "Original", "city": "Campinas", "state": "SP", "whatsapp": "11999990000"}, headers=ana)
    exported = client.get("/api/leads/export", headers=ana).content
    client.post("/api/leads/cleanup?include_today=true", headers=ana)
    assert fake.rows["leads"] == []
    body = post(client, ana, exported).json()
    assert body["imported"] == 1 and body["invalid"] == 0
    assert fake.rows["leads"][0]["whatsapp"] == "11999990000"


def test_missing_company_column(client, ana):
    r = post(client, ana, b"Telefone;Cidade\n11999990000;Campinas\n")
    assert r.status_code == 422 and r.json()["error"]["code"] == "missing_company_column"


def test_empty_and_too_large(client, ana):
    assert post(client, ana, b"").status_code == 422
    assert post(client, ana, b"Empresa\n" + b"x" * (5 * 1024 * 1024 + 1)).status_code == 413


def test_import_is_per_user(client, ana, bia, fake):
    post(client, ana, CSV.encode())
    assert post(client, bia, CSV.encode()).json()["imported"] == 2
