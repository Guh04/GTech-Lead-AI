"""Gera toda a identidade visual da GTech Digital Studio (HTML em src/ -> PNG em export/).

Uso:  python build.py            (tudo)
      python build.py logos      (só uma etapa: telas | logos | destaques | posts | feed | apresentacoes | manual)
Requer Chrome instalado e internet (Google Fonts). As telas dos sites demonstrativos vêm de demos/.
"""
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from render import shot

ROOT = Path(__file__).parent
SRC, OUT = ROOT / "src", ROOT / "export"

# ------------------------------------------------------------------ marca
INK, GRAPHITE, GRAPHITE2 = "#0A0C10", "#1B1F27", "#2A2F3A"
OFF, WHITE, BLUE, DEEP = "#F3F1EC", "#FFFFFF", "#1D4DFF", "#0B2A8F"
FONTS = '<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
BASE_CSS = f"""
:root{{--ink:{INK};--gr:{GRAPHITE};--gr2:{GRAPHITE2};--off:{OFF};--white:{WHITE};--blue:{BLUE};--deep:{DEEP}}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Inter,system-ui,sans-serif;-webkit-font-smoothing:antialiased}}
.serif{{font-family:"Instrument Serif",Georgia,serif;font-weight:400;letter-spacing:-.012em;line-height:1}}
.serif em{{font-style:italic;color:var(--blue)}}
.lbl{{font-size:20px;font-weight:600;letter-spacing:.18em;text-transform:uppercase}}
"""


def symbol(main: str, accent: str = BLUE, size: int = 100) -> str:
    """Símbolo: um G construído em ângulos retos; o bloco azul é a 'peça' que fecha o traço superior."""
    return (f'<svg width="{size}" height="{size}" viewBox="10 11 84 84" xmlns="http://www.w3.org/2000/svg">'
            f'<path d="M76 28H22V78H82V54H54" fill="none" stroke="{main}" stroke-width="12" stroke-linejoin="miter"/>'
            f'<rect x="76" y="22" width="12" height="12" fill="{accent}"/></svg>')


def lockup(color: str, accent: str = BLUE, size: int = 64, studio: bool = True) -> str:
    """Logo horizontal: símbolo + GTech (e Digital Studio)."""
    s = size
    sub = (f'<div style="font-size:{s*.2:.0f}px;font-weight:600;letter-spacing:.34em;text-transform:uppercase;'
           f'opacity:.72;margin-top:{s*.06:.0f}px">Digital Studio</div>') if studio else ""
    return (f'<div style="display:inline-flex;align-items:center;gap:{s*.3:.0f}px;color:{color}">{symbol(color, accent, s)}'
            f'<div><div style="font-size:{s*.62:.0f}px;font-weight:700;letter-spacing:-.04em;line-height:1">GTech</div>{sub}</div></div>')


def page(body: str, w: int, h: int, bg: str = WHITE, extra_css: str = "") -> str:
    return (f'<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">{FONTS}<style>{BASE_CSS}'
            f'html,body{{width:{w}px;height:{h}px;overflow:hidden;background:{bg}}}{extra_css}</style></head><body>{body}</body></html>')


def write(name: str, html: str) -> Path:
    p = SRC / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    return p


JOBS: list[tuple[Path, Path, int, int, float, str | None]] = []


def job(html_name: str, png_name: str, w: int, h: int, scale: float = 1.0, transparent: bool = False) -> None:
    JOBS.append((SRC / html_name, OUT / png_name, w, h, scale, "00000000" if transparent else None))


def run_jobs() -> None:
    def go(j):
        shot(j[0], j[1], j[2], j[3], j[4], j[5])
        print("ok", j[1].relative_to(ROOT))
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(go, JOBS))
    JOBS.clear()


# ------------------------------------------------------------------ mockups
MOCK_CSS = """
.laptop{position:relative;width:var(--w,1000px)}
.laptop .scr{background:#0c0d10;border-radius:18px 18px 6px 6px;padding:calc(var(--w,1000px)*.012);box-shadow:0 0 0 2px #2b2e36 inset}
.laptop .scr .in{aspect-ratio:16/10;border-radius:8px;overflow:hidden;background:#fff}
.laptop .scr img{width:100%;height:100%;object-fit:cover;object-position:top;display:block}
.laptop .base{height:calc(var(--w,1000px)*.026);margin:0 -4%;background:linear-gradient(#cfd2d8,#9ea2ab);border-radius:2px 2px 18px 18px;position:relative}
.laptop .base:after{content:"";position:absolute;left:50%;top:0;transform:translateX(-50%);width:16%;height:38%;background:#8b8f98;border-radius:0 0 10px 10px}
.phone{position:relative;width:var(--w,300px);aspect-ratio:9/19;background:#0c0d10;border-radius:calc(var(--w,300px)*.15);padding:calc(var(--w,300px)*.035);box-shadow:0 0 0 2px #2b2e36 inset}
.phone .in{width:100%;height:100%;border-radius:calc(var(--w,300px)*.12);overflow:hidden;background:#fff}
.phone .in img{width:100%;height:100%;object-fit:cover;object-position:top;display:block}
.phone:before{content:"";position:absolute;top:calc(var(--w,300px)*.05);left:50%;transform:translateX(-50%);width:28%;height:calc(var(--w,300px)*.05);background:#0c0d10;border-radius:99px;z-index:2}
.sh{filter:drop-shadow(0 50px 50px rgba(8,10,16,.35)) drop-shadow(0 12px 14px rgba(8,10,16,.25))}
"""


def laptop(img: str, w: int, style: str = "") -> str:
    return (f'<div class="laptop sh" style="--w:{w}px;{style}"><div class="scr"><div class="in"><img src="../../export/telas/{img}"></div></div>'
            f'<div class="base"></div></div>')


def phone(img: str, w: int, style: str = "", pos: str = "top") -> str:
    return f'<div class="phone sh" style="--w:{w}px;{style}"><div class="in"><img src="../../export/telas/{img}" style="object-position:{pos}"></div></div>'


PROJECTS = {
    "clinica": dict(nome="Clínica médica", marca="Clínica Lumen", desc="Landing page com agendamento de consultas", pts=["Formulário de agendamento em destaque", "Hierarquia clara das especialidades", "Design clean, pensado para gerar confiança"]),
    "advocacia": dict(nome="Escritório de advocacia", marca="Nobre & Lacerda", desc="Site institucional corporativo", pts=["Tipografia elegante e sóbria", "Áreas de atuação apresentadas com clareza", "Chamada discreta para reunião"]),
    "estetica": dict(nome="Clínica de estética", marca="Atelier Seiva", desc="Landing page comercial", pts=["Visual sofisticado e acolhedor", "Tratamentos em destaque", "Foco em agendamento de avaliação"]),
    "servicos": dict(nome="Empresa de serviços", marca="Prumo Serviços Prediais", desc="Site institucional com orçamento", pts=["Serviços apresentados de forma direta", "Botões de orçamento em todo o percurso", "Processo de trabalho explicado em 3 passos"]),
}
NOTE = "Projeto conceitual · marca fictícia"


# ------------------------------------------------------------------ logos
def build_logos() -> None:
    sym_svg = lambda main, acc: f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="10 11 84 84"><path d="M76 28H22V78H82V54H54" fill="none" stroke="{main}" stroke-width="12" stroke-linejoin="miter"/><rect x="76" y="22" width="12" height="12" fill="{acc}"/></svg>'
    (OUT / "logos").mkdir(parents=True, exist_ok=True)
    for nome, main, acc in [("simbolo-escuro", INK, BLUE), ("simbolo-claro", WHITE, BLUE), ("simbolo-azul", BLUE, BLUE), ("simbolo-mono-preto", INK, INK), ("simbolo-mono-branco", WHITE, WHITE)]:
        (OUT / "logos" / f"{nome}.svg").write_text(sym_svg(main, acc), encoding="utf-8")

    def tile(name, inner, w, h, bg, transparent=False):
        write(f"logos/{name}.html", page(f'<div style="width:{w}px;height:{h}px;display:grid;place-items:center">{inner}</div>', w, h, "transparent" if transparent else bg))
        job(f"logos/{name}.html", f"logos/{name}.png", w, h, transparent=transparent)

    tile("horizontal-escuro", lockup(INK, BLUE, 140), 1200, 400, OFF)
    tile("horizontal-claro", lockup(WHITE, BLUE, 140), 1200, 400, INK)
    tile("horizontal-escuro-transparente", lockup(INK, BLUE, 140), 1200, 400, OFF, True)
    tile("horizontal-claro-transparente", lockup(WHITE, BLUE, 140), 1200, 400, INK, True)
    tile("compacto-escuro", lockup(INK, BLUE, 140, studio=False), 900, 400, OFF)
    tile("compacto-claro", lockup(WHITE, BLUE, 140, studio=False), 900, 400, INK)
    tile("perfil-instagram", symbol(WHITE, BLUE, 520), 1080, 1080, INK)
    tile("perfil-instagram-claro", symbol(INK, BLUE, 520), 1080, 1080, OFF)

    # Aplicações em fundos diferentes + papelaria
    cell = lambda bg, inner, fg="": f'<div style="background:{bg};display:grid;place-items:center;{fg}">{inner}</div>'
    card_front = f'<div style="width:520px;height:300px;background:{INK};border-radius:6px;padding:34px;display:flex;flex-direction:column;justify-content:space-between;box-shadow:0 30px 50px rgba(0,0,0,.25)">{lockup(WHITE, BLUE, 56)}<div style="color:#8a8f9a;font-size:15px;line-height:1.6;letter-spacing:.02em">Landing pages e sites profissionais<br>contato@seudominio.com.br</div></div>'
    card_back = f'<div style="width:520px;height:300px;background:{BLUE};border-radius:6px;display:grid;place-items:center;box-shadow:0 30px 50px rgba(0,0,0,.25)">{symbol(WHITE, INK, 120)}</div>'
    grid = (
        '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;grid-template-rows:380px 380px 520px;gap:0;width:1920px;height:1280px">'
        + cell(INK, lockup(WHITE, BLUE, 96)) + cell(OFF, lockup(INK, BLUE, 96)) + cell(BLUE, lockup(WHITE, INK, 96))
        + cell(GRAPHITE, symbol(WHITE, BLUE, 170)) + cell(WHITE, symbol(INK, BLUE, 170)) + cell("linear-gradient(135deg,#1d2a5c,#0a0c10)", lockup(WHITE, BLUE, 96, studio=False))
        + f'<div style="grid-column:1/3;background:{OFF};display:flex;align-items:center;justify-content:center;gap:40px;position:relative">{card_front}{card_back}</div>'
        + f'<div style="background:{INK};display:grid;place-items:center">{symbol(WHITE, BLUE, 260)}</div></div>'
    )
    write("logos/aplicacoes.html", page(grid, 1920, 1280, INK))
    job("logos/aplicacoes.html", "logos/aplicacoes.png", 1920, 1280)


# ------------------------------------------------------------------ manual
def build_manual() -> None:
    sw = lambda nome, hexa, fg, uso: (f'<div style="background:{hexa};color:{fg};padding:26px;height:230px;display:flex;flex-direction:column;justify-content:space-between;'
                                       f'{"border:1px solid #d9d6cf;" if hexa in (OFF, WHITE) else ""}"><div class="lbl" style="font-size:15px">{nome}</div>'
                                       f'<div><div style="font-size:30px;font-weight:600;letter-spacing:-.02em">{hexa}</div><div style="font-size:15px;opacity:.7;margin-top:4px">{uso}</div></div></div>')
    body = f"""
<div style="width:1920px;height:1900px;background:{OFF};padding:90px 110px;color:{INK}">
  <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid {INK};padding-bottom:28px">
    {lockup(INK, BLUE, 70)}<div class="lbl" style="font-size:17px;color:#6b6f78">Manual de marca · v1</div></div>
  <div style="display:grid;grid-template-columns:1.15fr .85fr;gap:70px;margin-top:70px">
    <div><div class="lbl" style="color:{BLUE};font-size:15px">01 · Conceito</div>
      <div class="serif" style="font-size:96px;margin:22px 0 26px">Um G construído<br>peça por <em>peça</em>.</div>
      <p style="font-size:21px;line-height:1.6;color:#4b4f58;max-width:760px">O símbolo é um G em ângulos retos, desenhado como uma estrutura. O traço superior termina em um bloco azul: a peça que fecha a construção. Representa o que o estúdio faz: montar a presença digital de um negócio com precisão e acabamento.</p></div>
    <div style="background:{INK};display:grid;place-items:center;height:430px">{symbol(WHITE, BLUE, 250)}</div></div>
  <div class="lbl" style="color:{BLUE};font-size:15px;margin:80px 0 22px">02 · Cores</div>
  <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:0">{sw("Preto", INK, WHITE, "Fundos, texto, logo")}{sw("Grafite", GRAPHITE, WHITE, "Superfícies escuras")}{sw("Off-white", OFF, INK, "Fundo principal claro")}{sw("Branco", WHITE, INK, "Cartões, respiro")}{sw("Azul elétrico", BLUE, WHITE, "Destaque. Use com moderação")}</div>
  <p style="font-size:17px;color:#6b6f78;margin-top:16px">Proporção sugerida: 60% off-white ou preto · 30% grafite ou branco · 10% azul. Sem degradês chamativos, brilhos ou efeitos 3D.</p>
  <div class="lbl" style="color:{BLUE};font-size:15px;margin:70px 0 22px">03 · Tipografia</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:0;border:1px solid #d9d6cf">
    <div style="padding:40px;background:{WHITE}"><div class="lbl" style="font-size:14px;color:#6b6f78">Títulos · Instrument Serif</div><div class="serif" style="font-size:110px;margin-top:14px">Aa <em>Sites</em></div><p style="font-size:17px;color:#4b4f58;margin-top:12px">Grande, com respiro. Use itálico azul em uma palavra-chave por título.</p></div>
    <div style="padding:40px;background:{WHITE};border-left:1px solid #d9d6cf"><div class="lbl" style="font-size:14px;color:#6b6f78">Texto e rótulos · Inter</div><div style="font-size:110px;font-weight:700;letter-spacing:-.04em;line-height:1;margin-top:14px">Aa 123</div><p style="font-size:17px;color:#4b4f58;margin-top:12px">Peso 400 para textos, 600 em rótulos em caixa-alta com espaçamento aberto.</p></div></div>
  <div class="lbl" style="color:{BLUE};font-size:15px;margin:70px 0 22px">04 · Uso do logo</div>
  <div style="display:grid;grid-template-columns:1.3fr 1fr 1fr;gap:20px">
    <div style="background:{WHITE};border:1px solid #d9d6cf;padding:40px;display:grid;place-items:center;position:relative;height:250px"><div style="outline:1.5px dashed {BLUE};outline-offset:34px">{lockup(INK, BLUE, 70)}</div><div style="position:absolute;bottom:14px;left:20px;font-size:14px;color:#6b6f78">Área de proteção: a altura do símbolo ao redor</div></div>
    <div style="background:{WHITE};border:1px solid #d9d6cf;padding:30px;height:250px"><div style="font-size:15px;font-weight:600;color:#1a7f4b">FAZER</div><p style="font-size:16px;color:#4b4f58;margin-top:10px;line-height:1.7">Usar a versão clara sobre preto ou azul e a escura sobre off-white. Manter o bloco azul. Largura mínima de 120 px.</p></div>
    <div style="background:{WHITE};border:1px solid #d9d6cf;padding:30px;height:250px"><div style="font-size:15px;font-weight:600;color:#c0352b">NÃO FAZER</div><p style="font-size:16px;color:#4b4f58;margin-top:10px;line-height:1.7">Esticar, girar ou recolorir o símbolo. Aplicar sobre fotos sem contraste. Adicionar sombras, brilhos ou degradês.</p></div></div>
</div>"""
    write("manual.html", page(body, 1920, 1900, OFF))
    job("manual.html", "manual-de-marca.png", 1920, 1900)


# ------------------------------------------------------------------ destaques
ICONS = {
    "Serviços": '<g fill="none" stroke="#fff" stroke-width="3.2" stroke-linejoin="round"><path d="M50 18 82 34 50 50 18 34Z"/><path d="M18 50 50 66 82 50"/><path d="M18 66 50 82 82 66"/></g>',
    "Portfólio": '<g fill="none" stroke="#fff" stroke-width="3.2"><rect x="18" y="22" width="48" height="48"/><rect x="34" y="38" width="48" height="48" fill="#0A0C10"/></g>',
    "Projetos": '<g fill="none" stroke="#fff" stroke-width="3.2"><rect x="14" y="24" width="72" height="54" rx="3"/><path d="M14 38H86"/><path d="M28 54H58M28 64H46"/></g>',
    "Sobre": None,
    "Contato": '<g fill="none" stroke="#fff" stroke-width="3.2" stroke-linejoin="round"><path d="M18 26H82V66H44L28 80V66H18Z"/><path d="M32 42H68M32 52H56"/></g>',
}


def build_destaques() -> None:
    for nome, ic in ICONS.items():
        art = symbol(WHITE, BLUE, 440) if ic is None else f'<svg width="520" height="520" viewBox="0 0 100 100">{ic}<rect x="76" y="14" width="10" height="10" fill="{BLUE}"/></svg>'
        body = (f'<div style="width:1080px;height:1920px;background:{INK};position:relative;display:grid;place-items:center">'
                f'<div style="width:760px;height:760px;border-radius:50%;border:2px solid {GRAPHITE2};display:grid;place-items:center">{art}</div>'
                f'<div class="lbl" style="position:absolute;bottom:260px;left:0;right:0;text-align:center;color:#8a8f9a;font-size:26px">{nome}</div></div>')
        slug = nome.lower().replace("ó", "o").replace("ç", "c")
        write(f"destaques/{slug}.html", page(body, 1080, 1920, INK))
        job(f"destaques/{slug}.html", f"instagram/destaques/destaque-{slug}.png", 1080, 1920)


# ------------------------------------------------------------------ posts
def post_shell(inner: str, bg: str, fg: str, tag: str, foot: str = "", n: int = 0) -> str:
    mark = lockup(fg, BLUE, 44, studio=False)
    return (f'<div style="width:1080px;height:1350px;background:{bg};color:{fg};position:relative;overflow:hidden">'
            f'<div style="position:absolute;top:60px;left:64px;right:64px;display:flex;justify-content:space-between;align-items:center">{mark}'
            f'<div class="lbl" style="font-size:16px;opacity:.6">{tag}</div></div>{inner}'
            f'<div style="position:absolute;left:64px;right:64px;bottom:56px;display:flex;justify-content:space-between;font-size:16px;opacity:.6;letter-spacing:.04em"><span>GTech Digital Studio</span><span>{foot}</span></div></div>')


def build_posts() -> None:
    P = {}
    # 1 manifesto
    P[1] = post_shell(f'<div style="position:absolute;left:64px;right:64px;bottom:150px"><div class="serif" style="font-size:132px">Presença digital com <em>acabamento</em> de estúdio.</div>'
                      f'<div style="margin-top:36px;font-size:26px;line-height:1.5;color:#9aa0ac;max-width:760px">Criamos landing pages e sites profissionais para empresas que querem ser encontradas e lembradas.</div></div>'
                      f'<div style="position:absolute;right:64px;top:300px;width:300px;height:300px;border:2px solid {GRAPHITE2}"></div><div style="position:absolute;right:64px;top:300px;width:60px;height:60px;background:{BLUE}"></div>',
                      INK, WHITE, "Estúdio de sites", "01")
    # 2 clínica
    P[2] = post_shell(f'<div style="position:absolute;left:0;right:0;top:250px;display:grid;place-items:center">{laptop("clinica-desktop.png", 940, "transform:perspective(2200px) rotateY(-12deg) rotateX(3deg)")}</div>'
                      f'<div style="position:absolute;right:90px;top:680px">{phone("clinica-mobile.png", 250, "transform:rotate(4deg)")}</div>'
                      f'<div style="position:absolute;left:64px;bottom:150px"><div class="lbl" style="color:{BLUE};font-size:18px">Clínica médica</div><div class="serif" style="font-size:78px;margin-top:12px;max-width:620px">Landing page com <em>agendamento</em> de consultas.</div></div>',
                      OFF, INK, "Projeto conceitual", NOTE)
    # 3 serviços
    rows = "".join(f'<div style="display:flex;align-items:baseline;gap:34px;border-top:1px solid {GRAPHITE2};padding:34px 0"><span class="lbl" style="color:{BLUE};font-size:20px;width:50px">0{i}</span><span class="serif" style="font-size:78px">{t}</span></div>'
                   for i, t in enumerate(["Landing pages", "Sites institucionais", "Sites comerciais", "Redesign de sites", "Páginas para conversão"], 1))
    P[3] = post_shell(f'<div style="position:absolute;left:64px;right:64px;top:210px"><div class="serif" style="font-size:112px;margin-bottom:54px">O que <em>desenvolvemos</em></div>{rows}</div>',
                      GRAPHITE, WHITE, "Serviços", "Slide 1")
    # 4 advocacia
    P[4] = post_shell(f'<div style="position:absolute;left:30px;top:300px">{laptop("advocacia-desktop.png", 840, "transform:perspective(2200px) rotateY(14deg) rotateX(3deg)")}</div>'
                      f'<div style="position:absolute;right:76px;top:610px">{phone("advocacia-mobile.png", 260, "transform:rotate(-3deg)")}</div>'
                      f'<div style="position:absolute;left:64px;bottom:150px"><div class="lbl" style="color:{BLUE};font-size:18px">Escritório de advocacia</div><div class="serif" style="font-size:78px;margin-top:12px;max-width:640px">Site institucional com <em>presença</em> corporativa.</div></div>',
                      INK, WHITE, "Projeto conceitual", NOTE)
    # 5 pergunta
    P[5] = post_shell(f'<div style="position:absolute;left:64px;right:64px;top:260px"><div class="serif" style="font-size:150px;color:#fff">Sua empresa precisa de um <span style="font-style:italic;color:{INK}">site profissional?</span></div>'
                      f'<div style="margin-top:54px;font-size:30px;line-height:1.5;max-width:780px;color:rgba(255,255,255,.88)">Se o seu cliente procura você na internet e não encontra, ele procura outra empresa.</div></div>'
                      f'<div style="position:absolute;left:64px;bottom:150px;display:inline-block;background:#fff;color:{BLUE};font-weight:700;font-size:24px;padding:20px 38px;border-radius:99px">Peça uma proposta · link na bio</div>',
                      BLUE, WHITE, "Conteúdo", "")
    # 6 estética
    P[6] = post_shell(f'<div style="position:absolute;left:64px;right:64px;top:230px;display:flex;justify-content:center;gap:34px;align-items:flex-start">'
                      f'{phone("estetica-mobile.png", 300, "margin-top:70px", "0% 0%")}{phone("estetica-mobile.png", 340, "", "0% 14%")}{phone("estetica-mobile.png", 300, "margin-top:70px", "0% 33%")}</div>'
                      f'<div style="position:absolute;left:64px;bottom:150px"><div class="lbl" style="color:{BLUE};font-size:18px">Clínica de estética</div><div class="serif" style="font-size:78px;margin-top:12px;max-width:720px">Landing page <em>sofisticada</em>, pensada para o celular.</div></div>',
                      OFF, INK, "Projeto conceitual", NOTE)
    # 7 diferenciais
    items = [("Design sob medida", "Cada projeto parte da identidade e do público do negócio."), ("Celular e desktop", "Páginas que funcionam bem em qualquer tamanho de tela."),
             ("Pensado para contato", "Estrutura que leva o visitante ao WhatsApp ou ao orçamento."), ("Processo claro", "Do briefing à publicação, você sabe cada etapa.")]
    cards = "".join(f'<div style="background:#fff;padding:40px 36px;height:400px;display:flex;flex-direction:column;justify-content:space-between"><span class="lbl" style="color:{BLUE};font-size:18px">0{i}</span>'
                    f'<div><div class="serif" style="font-size:54px">{t}</div><div style="font-size:21px;line-height:1.5;color:#5b606a;margin-top:14px">{d}</div></div></div>' for i, (t, d) in enumerate(items, 1))
    P[7] = post_shell(f'<div style="position:absolute;left:64px;right:64px;top:230px"><div class="serif" style="font-size:112px;margin-bottom:50px">Como <em>trabalhamos</em></div>'
                      f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:2px;background:#dcd9d2;border:2px solid #dcd9d2">{cards}</div></div>', OFF, INK, "Diferenciais", "")
    # 8 desktop x mobile
    P[8] = post_shell(f'<div style="position:absolute;left:64px;top:270px">{laptop("servicos-desktop.png", 700, "transform:perspective(2000px) rotateY(10deg)")}</div>'
                      f'<div style="position:absolute;right:90px;top:360px">{phone("servicos-mobile.png", 270)}</div>'
                      f'<div class="lbl" style="position:absolute;left:64px;top:230px;font-size:16px;color:#8a8f9a">Desktop</div><div class="lbl" style="position:absolute;right:150px;top:320px;font-size:16px;color:#8a8f9a">Mobile</div>'
                      f'<div style="position:absolute;left:64px;bottom:150px"><div class="lbl" style="color:#6f8cff;font-size:18px">Empresa de serviços</div><div class="serif" style="font-size:78px;margin-top:12px;max-width:760px">Um site, <em style="color:#6f8cff">duas telas</em>, o mesmo cuidado.</div></div>',
                      GRAPHITE, WHITE, "Projeto conceitual", NOTE)
    # 9 CTA
    P[9] = post_shell(f'<div style="position:absolute;right:-170px;top:210px;opacity:1">{symbol(GRAPHITE2, BLUE, 760)}</div>'
                      f'<div style="position:absolute;left:64px;right:64px;bottom:170px"><div class="serif" style="font-size:128px;max-width:880px">Vamos construir a presença digital do seu <em>negócio?</em></div>'
                      f'<div style="margin-top:44px;display:inline-block;background:{BLUE};color:#fff;font-weight:700;font-size:24px;padding:20px 38px;border-radius:99px">Orçamento pelo WhatsApp · link na bio</div></div>',
                      INK, WHITE, "Contato", "")
    for n, inner in P.items():
        write(f"posts/{n:02d}.html", page(inner, 1080, 1350, INK))
        job(f"posts/{n:02d}.html", f"instagram/posts/post-{n:02d}.png", 1080, 1350)


# ------------------------------------------------------------------ feed + perfil
def build_feed() -> None:
    order = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    thumbs = "".join(f'<div style="aspect-ratio:3/4;overflow:hidden;position:relative"><img src="../export/instagram/posts/post-{n:02d}.png" style="width:100%;height:100%;object-fit:cover"></div>' for n in order)
    body = (f'<div style="width:1920px;height:1760px;background:{OFF};padding:80px 110px;color:{INK}"><div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:46px">'
            f'<div><div class="lbl" style="color:{BLUE};font-size:15px">Planejamento do feed</div><div class="serif" style="font-size:84px;margin-top:14px">As primeiras <em>9</em> publicações</div></div>'
            f'<div style="font-size:19px;line-height:1.6;color:#4b4f58;max-width:560px;text-align:right">Alternância entre texto e projeto, em xadrez. Publique de <b>9 para 1</b> (a 1 fica no topo à esquerda).</div></div>'
            f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;width:1080px;margin:auto">{thumbs}</div></div>')
    write("feed.html", page(body, 1920, 1760, OFF))
    job("feed.html", "instagram/feed-9-publicacoes.png", 1920, 1760)

    def hl_icon(nome):
        ic = ICONS[nome]
        art = symbol(WHITE, BLUE, 62) if ic is None else f'<svg width="62" height="62" viewBox="0 0 100 100">{ic}<rect x="76" y="14" width="10" height="10" fill="{BLUE}"/></svg>'
        return (f'<div style="text-align:center;width:150px"><div style="width:132px;height:132px;margin:auto;border-radius:50%;background:{INK};display:grid;place-items:center;border:4px solid #fff;outline:2px solid #d7d7d7">{art}</div>'
                f'<div style="font-size:22px;margin-top:12px;color:#222">{nome}</div></div>')
    hl = "".join(hl_icon(n) for n in ["Serviços", "Portfólio", "Projetos", "Sobre", "Contato"])
    small = "".join(f'<div style="aspect-ratio:3/4;overflow:hidden"><img src="../export/instagram/posts/post-{n:02d}.png" style="width:100%;height:100%;object-fit:cover"></div>' for n in order)
    body = (f'<div style="width:1080px;height:1920px;background:#fff;color:#111;padding:60px 48px"><div style="display:flex;align-items:center;gap:44px">'
            f'<div style="width:200px;height:200px;border-radius:50%;background:{INK};display:grid;place-items:center;flex:none">{symbol(WHITE, BLUE, 110)}</div>'
            f'<div style="display:flex;gap:52px;font-size:26px;color:#333"><div style="text-align:center"><b style="font-size:34px;display:block">9</b>publicações</div></div></div>'
            f'<div style="margin-top:28px;font-size:30px;line-height:1.45"><b>GTech Digital Studio | Sites e Landing Pages</b><div style="color:#6b6b6b;font-size:25px">Agência de web design</div>'
            f'<div style="margin-top:6px">Landing pages e sites profissionais para empresas.<br>Design sob medida, rápido e pronto para converter.<br>Orçamento pelo WhatsApp 👇</div><div style="color:{BLUE};font-weight:600;margin-top:6px">wa.me/seunumero</div></div>'
            f'<div style="display:flex;gap:14px;margin-top:30px"><div style="flex:1;background:{BLUE};color:#fff;font-weight:600;font-size:26px;text-align:center;padding:20px;border-radius:12px">Entrar em contato</div><div style="flex:1;background:#efefef;font-weight:600;font-size:26px;text-align:center;padding:20px;border-radius:12px">Ver projetos</div></div>'
            f'<div style="display:flex;justify-content:space-between;margin:44px 0 40px;padding:0 6px">{hl}</div><div style="display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin:0 -48px">{small}</div></div>')
    write("perfil.html", page(body, 1080, 1920, WHITE))
    job("perfil.html", "instagram/perfil-preview.png", 1080, 1920)


# ------------------------------------------------------------------ apresentações
def build_presentations() -> None:
    for i, (k, p) in enumerate(PROJECTS.items()):
        dark = i % 2 == 0
        bg, fg, mut = (INK, WHITE, "#9aa0ac") if dark else (OFF, INK, "#5b606a")
        pts = "".join(f'<div style="display:flex;gap:16px;align-items:flex-start;margin-top:18px;font-size:24px;line-height:1.4;color:{mut}"><span style="flex:none;width:12px;height:12px;background:{BLUE};margin-top:9px"></span>{t}</div>' for t in p["pts"])
        body = (f'<div style="width:1920px;height:1080px;background:{bg};color:{fg};position:relative;overflow:hidden">'
                f'<div style="position:absolute;left:110px;top:90px">{lockup(fg, BLUE, 52, studio=False)}</div>'
                f'<div style="position:absolute;left:110px;top:290px;width:700px"><div class="lbl" style="color:{BLUE};font-size:18px">Projeto 0{i+1} · {p["nome"]}</div>'
                f'<div class="serif" style="font-size:104px;margin:22px 0 14px">{p["marca"]}</div><div style="font-size:30px;color:{mut}">{p["desc"]}</div><div style="margin-top:34px">{pts}</div></div>'
                f'<div style="position:absolute;left:860px;top:210px">{laptop(k + "-desktop.png", 880, "transform:perspective(2400px) rotateY(-10deg) rotateX(2deg)")}</div>'
                f'<div style="position:absolute;left:1500px;top:480px">{phone(k + "-mobile.png", 260, "transform:rotate(3deg)")}</div>'
                f'<div style="position:absolute;left:110px;bottom:60px;font-size:17px;color:{mut}">{NOTE} · desenvolvido pela GTech Digital Studio</div></div>')
        write(f"apresentacoes/{k}.html", page(body, 1920, 1080, bg))
        job(f"apresentacoes/{k}.html", f"apresentacoes/projeto-0{i+1}-{k}.png", 1920, 1080)


def build_telas() -> None:
    """Capturas dos sites demonstrativos (fonte única: site/projetos).

    - export/telas/*-desktop|mobile.png : página inteira, usadas nos posts e apresentações.
    - site/assets/images/*.webp         : primeira dobra (viewport), usadas no portfólio do site.
    """
    demos = ROOT.parent / "site" / "projetos"
    for k in PROJECTS:
        page_ = (demos / k / "index.html").resolve().as_uri() + "?shot"  # ?shot esconde a faixa de aviso nas capturas
        JOBS.append((page_, OUT / "telas" / f"{k}-desktop.png", 1440, 1500, 1.0, None))
        JOBS.append((page_, OUT / "telas" / f"{k}-mobile.png", 390, 1700, 2.0, None))
        JOBS.append((page_, SRC / "_site" / f"{k}-desktop.png", 1440, 900, 1.0, None))
        JOBS.append((page_, SRC / "_site" / f"{k}-mobile.png", 390, 844, 2.0, None))


def to_webp() -> None:
    """Converte as capturas do site para WebP (menores) em site/assets/images/."""
    from PIL import Image
    dest = ROOT.parent / "site" / "assets" / "images"
    dest.mkdir(parents=True, exist_ok=True)
    for png in (SRC / "_site").glob("*.png"):
        Image.open(png).convert("RGB").save(dest / (png.stem + ".webp"), "WEBP", quality=84, method=6)
        print("webp", (dest / (png.stem + ".webp")).name)


STEPS = {"telas": build_telas, "logos": build_logos, "destaques": build_destaques, "posts": build_posts,
         "apresentacoes": build_presentations, "manual": build_manual, "feed": build_feed}

if __name__ == "__main__":
    SRC.mkdir(exist_ok=True)
    chosen = sys.argv[1:] or list(STEPS)
    MOCK = f"<style>{MOCK_CSS}</style>"
    # Mockups e posts compartilham o CSS dos dispositivos: injeta em BASE_CSS.
    BASE_CSS += MOCK_CSS
    # Ordem importa: telas -> (logos, destaques, posts, apresentações, manual) -> feed (usa posts e destaques)
    for name in [s for s in STEPS if s in chosen and s != "feed"]:
        STEPS[name]()
        run_jobs()
        if name == "telas":
            to_webp()
    if "feed" in chosen:
        build_feed()
        run_jobs()
