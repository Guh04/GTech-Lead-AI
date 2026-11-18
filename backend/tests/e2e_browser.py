"""Teste ponta a ponta no navegador (Playwright + Chrome instalado).

Pré-requisitos:  pip install playwright   e   python -m tests.e2e_server   (outro terminal)
Execução:        python -m tests.e2e_browser [pasta_de_screenshots]
"""
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = "http://127.0.0.1:8765"
SHOTS = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("e2e-shots")
SHOTS.mkdir(parents=True, exist_ok=True)
problems: list[str] = []
passed: list[str] = []


def check(name: str, ok: bool, extra: str = ""):
    (passed if ok else problems).append(name + (f" -> {extra}" if extra and not ok else ""))
    print(("  ok   " if ok else "  FAIL ") + name + (f"  [{extra}]" if extra and not ok else ""))


def api(page, method, path, body=None):
    """Chama a API usando o token da sessão do navegador (para preparar dados)."""
    token = json.loads(page.evaluate("localStorage.getItem('gtech.session')"))["access_token"]
    res = page.request.fetch(f"{BASE}/api{path}", method=method, headers={"Authorization": f"Bearer {token}"}, data=body)
    return res.json() if res.body() else None


with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True, locale="pt-BR")
    page = ctx.new_page()
    console_errors: list[str] = []
    page.on("pageerror", lambda e: console_errors.append(f"pageerror: {e}"))
    page.on("console", lambda m: console_errors.append(f"console: {m.text}") if m.type == "error" else None)
    page.on("requestfailed", lambda r: console_errors.append(f"requestfailed: {r.url}"))
    page.on("response", lambda r: console_errors.append(f"http {r.status}: {r.url}") if r.status >= 400 and "/api/" not in r.url else None)

    print("\n== Login")
    page.goto(BASE)
    expect(page.get_by_role("heading", name="Entrar")).to_be_visible()
    page.fill("#email", "teste@gtech.com")
    page.fill("#password", "senha-errada")
    page.click("#login-btn")
    expect(page.locator("#login-error")).to_contain_text("E-mail ou senha incorretos")
    check("login com senha errada mostra mensagem clara", True)
    page.screenshot(path=SHOTS / "01-login.png")
    page.fill("#password", "senha-teste")
    page.click("#login-btn")
    expect(page.locator("#topbar-page")).to_have_text("Dashboard")
    check("login correto abre o dashboard", True)

    print("\n== Dashboard vazio")
    expect(page.locator("#kpis .kpi")).to_have_count(7)
    values = [t.strip() for t in page.locator("#kpis .kpi-value").all_inner_texts()]
    check("7 indicadores, todos 0 com banco vazio", values == ["0"] * 7, str(values))
    expect(page.get_by_text("Nenhum lead cadastrado")).to_be_visible()
    page.screenshot(path=SHOTS / "02-dashboard-vazio.png")

    print("\n== Cadastro de lead pela interface")
    page.click("#new-lead-btn")
    expect(page.get_by_role("dialog")).to_be_visible()
    page.click("#lf-submit")  # vazio
    expect(page.locator('[data-error="company_name"]')).to_have_text("Informe o nome da empresa.")
    check("validação do formulário (nome obrigatório)", True)
    page.fill("#lf-company_name", "Clínica Odonto Sorriso")
    page.fill("#lf-contact_name", "Dra. Helena")
    page.fill("#lf-segment", "Clínica odontológica")
    page.fill("#lf-city", "Campinas")
    page.select_option("#lf-state", "SP")
    page.fill("#lf-whatsapp", "(19) 99999-1234")
    page.fill("#lf-instagram", "@odontosorriso")
    page.select_option("#lf-landing_page_status", "none")
    page.fill("#lf-notes", "Encontrada pelo Instagram, sem site.")
    page.screenshot(path=SHOTS / "03-form-lead.png")
    page.click("#lf-submit")
    expect(page.locator(".toast")).to_contain_text("Lead cadastrado com sucesso")
    check("lead cadastrado e toast de sucesso", True)
    expect(page.locator("#kpis .kpi-value").first).to_have_text("1")  # página recarregou com dado real
    check("dashboard atualizou com dado real", True)

    print("\n== Duplicidade")
    page.click("#new-lead-btn")
    page.fill("#lf-company_name", "Clínica Odonto Sorriso")
    page.fill("#lf-city", "Campinas")
    page.click("#lf-submit")
    expect(page.locator("#lf-alert")).to_contain_text("nome de empresa nesta cidade")
    check("duplicidade bloqueada com mensagem compreensível", True)
    page.keyboard.press("Escape")

    # dados adicionais via API para exercitar listas/filtros/pipeline
    for body in [
        dict(company_name="Barbearia Navalha", segment="Barbearia", city="Campinas", state="SP", landing_page_status="site_only", phone="1930001111"),
        dict(company_name="Advocacia Lima & Souza", segment="Advocacia", city="Curitiba", state="PR", landing_page_status="has_landing", whatsapp="41999990000", contact_name="Dr. Lima"),
        dict(company_name="Pet Shop Au-Au", segment="Pet shop", city="Curitiba", state="PR", landing_page_status="none", whatsapp="41988880000", instagram="petshopauau"),
        dict(company_name="<img src=x onerror=window.__xss=1>", segment="Teste XSS", city="Rio", state="RJ"),
    ]:
        assert api(page, "POST", "/leads", body)["id"]

    print("\n== Dashboard com dados")
    page.click('a[data-route="dashboard"]')
    expect(page.locator("#kpis .kpi-value").first).to_have_text("5")
    expect(page.locator("#chart-period")).to_be_visible()
    expect(page.locator("#latest tbody tr")).to_have_count(5)
    check("gráfico por período e últimos leads renderizados", True)
    check("XSS: HTML do nome é exibido como texto, nunca executado", page.evaluate("window.__xss") is None)
    expect(page.locator("#latest").get_by_text("<img src=x onerror=window.__xss=1>")).to_be_visible()
    page.wait_for_timeout(900)  # fim das animações
    page.screenshot(path=SHOTS / "04-dashboard.png", full_page=True)

    print("\n== Leads")
    page.click('a[data-route="leads"]')
    expect(page.locator("#leads-body tr")).to_have_count(5)
    page.fill("#f-search", "pet")
    expect(page.locator("#leads-body tr")).to_have_count(1)
    expect(page.locator("#leads-body")).to_contain_text("Pet Shop Au-Au")
    check("pesquisa por nome", True)
    page.fill("#f-search", "")
    expect(page.locator("#leads-body tr")).to_have_count(5)
    page.select_option("#f-city", "Curitiba")
    expect(page.locator("#leads-body tr")).to_have_count(2)
    check("filtro por cidade", True)
    page.select_option("#f-priority", "high")
    expect(page.locator("#leads-body tr")).to_have_count(1)
    check("filtro por prioridade", True)
    page.click("#f-clear")
    expect(page.locator("#leads-body tr")).to_have_count(5)
    page.select_option("#f-sort", "score_desc")
    first = page.locator("#leads-body tr").first
    expect(first).to_contain_text("Clínica Odonto Sorriso")  # 45+20+10+5 = 80
    check("ordenação por pontuação", True)
    page.select_option("#f-segment", "Barbearia")
    expect(page.locator("#leads-body tr")).to_have_count(1)
    page.select_option("#f-segment", "")
    page.select_option("#f-status", "contacted")
    expect(page.get_by_text("Nenhum lead encontrado")).to_be_visible()
    check("estado vazio de filtros", True)
    page.click("#f-clear")
    page.screenshot(path=SHOTS / "05-leads.png")

    print("\n== CSV")
    with page.expect_download() as dl:
        page.click("#export-btn")
    path = dl.value.path()
    csv_text = Path(path).read_bytes().decode("utf-8-sig")
    check("CSV baixado com cabeçalho e 5 leads", csv_text.startswith("Empresa;") and csv_text.count("\r\n") == 6, csv_text[:60])

    print("\n== Ficha, edição e exclusão")
    page.locator("#leads-body tr", has_text="Clínica Odonto Sorriso").click()
    expect(page.locator(".drawer")).to_contain_text("Dra. Helena")
    expect(page.locator(".drawer")).to_contain_text("(19) 99999-1234")
    expect(page.locator(".drawer a[href^='https://wa.me/']")).to_be_visible()
    page.fill("#ld-note", "Retornar na segunda.")
    page.click("#ld-note-btn")
    expect(page.locator("#ld-timeline")).to_contain_text("Retornar na segunda.")
    check("ficha completa + anotação no histórico", True)
    page.select_option("#ld-status", "contacted")
    expect(page.locator("#ld-timeline")).to_contain_text("Contato realizado")
    page.screenshot(path=SHOTS / "06-ficha.png")
    page.click("#ld-edit")
    page.fill("#lf-city", "Valinhos")
    page.click("#lf-submit")
    expect(page.locator(".drawer")).to_contain_text("Valinhos")
    check("edição pela ficha", True)
    page.click(".drawer [data-close]")
    page.locator("#leads-body tr", has_text="Barbearia Navalha").locator('[data-act="delete"]').click()
    expect(page.get_by_role("dialog")).to_contain_text("Tem certeza")
    page.click('[data-act="cancel"]')
    expect(page.locator("#leads-body tr")).to_have_count(5)
    page.locator("#leads-body tr", has_text="Barbearia Navalha").locator('[data-act="delete"]').click()
    page.click('[data-act="ok"]')
    expect(page.locator("#leads-body tr")).to_have_count(4)
    check("exclusão exige confirmação (cancelar mantém, confirmar remove)", True)

    print("\n== Pipeline (Kanban)")
    page.click('a[data-route="pipeline"]')
    expect(page.locator(".kcol")).to_have_count(7)
    expect(page.locator('.kcol[data-status="new"] .kcard')).to_have_count(3)
    expect(page.locator('.kcol[data-status="contacted"] .kcard')).to_have_count(1)
    card = page.locator('.kcol[data-status="new"] .kcard', has_text="Pet Shop Au-Au")
    card.drag_to(page.locator('.kcol[data-status="interested"] .kcol-body'))
    expect(page.locator('.kcol[data-status="interested"] .kcard')).to_have_count(1)
    check("arrastar e soltar move o lead de estágio", True)
    page.reload()
    expect(page.locator('.kcol[data-status="interested"] .kcard')).to_have_count(1)
    check("movimentação persistida no banco (sobrevive a recarregar)", True)
    page.locator('.kcol[data-status="new"] .kcard', has_text="Advocacia").locator("[data-move]").select_option("proposal_sent")
    expect(page.locator('.kcol[data-status="proposal_sent"] .kcard')).to_have_count(1)
    check("seletor 'Mover para' funciona", True)
    page.wait_for_timeout(500)
    page.screenshot(path=SHOTS / "07-pipeline.png")

    print("\n== Oportunidades")
    page.click('a[data-route="oportunidades"]')
    expect(page.locator(".opp-card").first).to_be_visible()
    expect(page.locator("#opp-tabs .tab")).to_have_count(3)
    page.click('[data-tab="medium"]')
    page.wait_for_timeout(400)
    page.screenshot(path=SHOTS / "08-oportunidades.png")
    page.click('[data-tab="high"]')
    expect(page.locator(".opp-card").first).to_contain_text("Clínica Odonto Sorriso")
    check("oportunidades por prioridade", True)

    print("\n== Prospecção")
    page.click('a[data-route="prospeccao"]')
    expect(page.locator("#agent-status")).to_contain_text("Busca automática não configurada")
    page.click("#p-submit")
    expect(page.locator("#prosp-error")).to_contain_text("Informe a cidade ou região")
    page.fill("#p-region", "Campinas")
    page.click('[data-seg="Barbearia"]')
    page.click('[data-seg="Pet shop"]')
    page.fill("#p-custom", "Estúdio de tatuagem")
    page.keyboard.press("Enter")
    expect(page.locator("#p-selected-hint")).to_have_text("3 segmentos selecionados.")
    page.click("#p-submit")
    expect(page.locator("#prosp-error")).to_contain_text("Nenhum agente de prospecção está conectado")
    check("sem agente: mensagem clara e nenhuma pesquisa simulada", True)
    expect(page.locator("#history")).to_contain_text("Nenhuma pesquisa realizada")
    page.screenshot(path=SHOTS / "09-prospeccao.png", full_page=True)

    print("\n== Relatórios")
    page.click('a[data-route="relatorios"]')
    expect(page.locator("#rep-kpis .kpi")).to_have_count(4)
    expect(page.locator("#rep-chart-segment")).to_be_visible()
    expect(page.locator("#rep-funnel .funnel-row")).to_have_count(7)
    page.select_option("#rep-days", "0")
    expect(page.locator("#rep-sub")).to_contain_text("Todos os leads")
    page.wait_for_timeout(900)
    page.screenshot(path=SHOTS / "10-relatorios.png", full_page=True)
    check("relatórios com gráficos e funil", True)

    print("\n== Responsivo (celular)")
    page.set_viewport_size({"width": 390, "height": 844})
    page.click('a[data-route="leads"]') if page.locator("#sidebar.open").count() else page.goto(f"{BASE}/#/leads")
    expect(page.locator("#menu-toggle")).to_be_visible()
    page.wait_for_timeout(500)  # fim da transição da sidebar
    check("sidebar escondida no celular", not page.locator("#sidebar").is_visible() or page.evaluate("document.querySelector('#sidebar').getBoundingClientRect().right <= 0"))
    page.click("#menu-toggle")
    page.wait_for_timeout(400)
    page.screenshot(path=SHOTS / "11-mobile-menu.png")
    page.click('a[data-route="dashboard"]')
    page.wait_for_timeout(900)
    page.screenshot(path=SHOTS / "12-mobile-dashboard.png", full_page=True)
    overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
    check("sem rolagem horizontal da página no celular (dashboard)", not overflow)
    page.goto(f"{BASE}/#/pipeline")
    page.wait_for_timeout(700)
    page.screenshot(path=SHOTS / "13-mobile-pipeline.png")
    page.set_viewport_size({"width": 820, "height": 1100})
    page.goto(f"{BASE}/#/leads")
    page.wait_for_timeout(700)
    page.screenshot(path=SHOTS / "14-tablet-leads.png")

    print("\n== Sair")
    page.set_viewport_size({"width": 1440, "height": 900})
    page.click("#logout-btn")
    expect(page.get_by_role("heading", name="Entrar")).to_be_visible()
    check("logout volta ao login", True)

    # 401 (senha errada), 409 (duplicidade) e 503 (sem agente) são respostas esperadas e já verificadas acima
    unexpected = [e for e in console_errors if not re.search(r"status of (401|409|503)", e)]
    check("nenhum erro inesperado de console / requisição falha", not unexpected, "; ".join(unexpected[:5]))
    browser.close()

print(f"\n{len(passed)} verificações ok, {len(problems)} problemas")
for pr in problems:
    print("PROBLEMA:", pr)
sys.exit(1 if problems else 0)
