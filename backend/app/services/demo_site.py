"""Página de demonstração (proposta de design) para um lead que ainda não tem site.

Gera um único index.html autossuficiente a partir do cadastro do lead, para você publicar (ex.: Netlify Drop)
e enviar o link na abordagem. É uma SUGESTÃO de design: traz um aviso fixo dizendo que não é o site oficial da
empresa, e nunca inventa depoimentos, preços, endereço ou fotos. Todo texto vindo do lead é escapado.
"""
import io
import re
import unicodedata
import zipfile
import zlib
from html import escape
from urllib.parse import quote

# (palavras-chave do segmento, serviços sugeridos). Texto genérico e honesto: o dono ajusta depois.
_SEGMENTS = [
    (("barbearia", "barbeiro"), ["Corte de cabelo", "Barba e acabamento", "Atendimento com hora marcada"]),
    (("salao", "salão", "cabeleire", "beleza", "estetica", "estética", "manicure", "unha"), ["Cabelo e tratamentos", "Estética e cuidados", "Atendimento com hora marcada"]),
    (("restaurante", "lanchonete", "pizzaria", "hamburguer", "hambúrguer", "padaria", "confeitaria", "cafe", "café", "bar"), ["Cardápio completo", "Pedidos pelo WhatsApp", "Atendimento no local e entrega"]),
    (("clinica", "clínica", "dentista", "odonto", "fisio", "psicolog", "nutri", "veterin", "pet"), ["Consultas e avaliações", "Atendimento personalizado", "Agendamento pelo WhatsApp"]),
    (("academia", "personal", "crossfit", "pilates", "studio", "estúdio"), ["Treinos e modalidades", "Acompanhamento próximo", "Aula experimental pelo WhatsApp"]),
    (("oficina", "mecanic", "mecânic", "auto", "lava", "borracharia", "funilaria"), ["Revisão e manutenção", "Orçamento sem compromisso", "Atendimento ágil"]),
    (("advoca", "contab", "consultor", "imobili", "escritorio", "escritório"), ["Atendimento especializado", "Análise do seu caso", "Orçamento pelo WhatsApp"]),
    (("loja", "boutique", "moda", "roupa", "calcado", "calçado", "presente", "floricultura"), ["Produtos selecionados", "Novidades toda semana", "Compre pelo WhatsApp"]),
]
_DEFAULT = ["Conheça nossos serviços", "Atendimento personalizado", "Orçamento pelo WhatsApp"]


def _fold(text: str) -> str:
    return unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _fold(text)).strip("-") or "empresa"


def _services(segment: str | None) -> list[str]:
    seg = _fold(segment or "")
    for keys, items in _SEGMENTS:
        if any(_fold(k) in seg for k in keys):
            return items
    return _DEFAULT


def _digits(value: str | None) -> str:
    d = "".join(c for c in (value or "") if c.isdigit())
    return f"55{d}" if len(d) in (10, 11) else d


def _hue(name: str) -> int:
    return zlib.crc32(name.encode("utf-8")) % 360  # cor própria por empresa, estável entre gerações


def render_html(lead: dict) -> str:
    name = (lead.get("company_name") or "Sua empresa").strip()
    segment = (lead.get("segment") or "").strip()
    place = ", ".join(p for p in [lead.get("city"), lead.get("state")] if p)
    wa = _digits(lead.get("whatsapp"))
    ig = (lead.get("instagram") or "").strip().lstrip("@").rstrip("/").split("/")[-1]
    hue = _hue(name)
    e = escape  # nunca inserir texto do lead sem escapar

    wa_text = quote(f"Olá! Vi a página da {name} e quero saber mais.")
    cta = f"https://wa.me/{wa}?text={wa_text}" if wa else "#contato"
    cards = "".join(f"<div class='card'><span class='n'>{i}</span><h3>{e(s)}</h3></div>" for i, s in enumerate(_services(segment), 1))
    tagline = f"{e(segment).capitalize()} em {e(place)}" if segment and place else (e(segment).capitalize() or e(place) or "Bem-vindo")
    ig_link = f"<a class='btn ghost' href='https://instagram.com/{quote(ig)}' target='_blank' rel='noopener noreferrer'>Instagram @{e(ig)}</a>" if ig else ""

    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><title>{e(name)} | Proposta de página</title>
<style>
:root{{--a:hsl({hue} 70% 45%);--a2:hsl({hue} 70% 35%);--soft:hsl({hue} 60% 96%);--ink:#16181d;--mut:#5b6270}}
*{{box-sizing:border-box}}body{{margin:0;font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--ink);background:#fff}}
.demo{{background:#fff7d6;color:#6b5200;border-bottom:1px solid #f0d77a;padding:10px 16px;text-align:center;font-size:.88rem}}
.wrap{{width:min(100% - 32px,960px);margin-inline:auto}}
header{{padding:18px 0}}header .wrap{{display:flex;align-items:center;justify-content:space-between;gap:12px}}
.logo{{font-weight:800;font-size:1.25rem;color:var(--a2)}}
.hero{{background:linear-gradient(160deg,var(--soft),#fff);padding:72px 0 64px;text-align:center}}
.hero p.k{{display:inline-block;color:var(--a2);font-weight:700;letter-spacing:.08em;text-transform:uppercase;font-size:.78rem;margin:0 0 12px}}
h1{{font-size:clamp(2rem,6vw,3.4rem);line-height:1.1;margin:0 0 14px}}.lead{{color:var(--mut);max-width:54ch;margin:0 auto 26px;font-size:1.1rem}}
.btn{{display:inline-block;padding:13px 26px;border-radius:999px;background:var(--a);color:#fff;font-weight:700;text-decoration:none;border:2px solid var(--a)}}
.btn:hover{{background:var(--a2);border-color:var(--a2)}}.btn.ghost{{background:transparent;color:var(--a2)}}.btn.ghost:hover{{background:var(--soft)}}
.actions{{display:flex;flex-wrap:wrap;gap:12px;justify-content:center}}
section{{padding:64px 0}}h2{{text-align:center;font-size:clamp(1.5rem,4vw,2.1rem);margin:0 0 32px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px}}
.card{{border:1px solid #e6e8ee;border-radius:16px;padding:24px;background:#fff}}.card h3{{margin:10px 0 0;font-size:1.1rem}}
.n{{display:inline-grid;place-items:center;width:32px;height:32px;border-radius:50%;background:var(--soft);color:var(--a2);font-weight:800}}
.cta{{background:var(--a2);color:#fff;text-align:center}}.cta h2{{color:#fff}}.cta .btn{{background:#fff;color:var(--a2);border-color:#fff}}
footer{{padding:28px 0;color:var(--mut);font-size:.85rem;text-align:center}}
</style></head><body>
<div class="demo"><strong>Demonstração criada pela GTech Digital Studio para {e(name)}.</strong> Esta não é a página oficial da empresa: é uma sugestão de design, com textos de exemplo.</div>
<header><div class="wrap"><span class="logo">{e(name)}</span><a class="btn" href="{cta}" target="_blank" rel="noopener noreferrer">Chamar no WhatsApp</a></div></header>
<div class="hero"><div class="wrap"><p class="k">{tagline}</p><h1>{e(name)}</h1>
<p class="lead">Uma página simples e rápida para quem procura {e(name)} encontrar tudo em um só lugar e chamar direto no WhatsApp.</p>
<div class="actions"><a class="btn" href="{cta}" target="_blank" rel="noopener noreferrer">Chamar no WhatsApp</a>{ig_link}</div></div></div>
<section><div class="wrap"><h2>O que você encontra aqui</h2><div class="grid">{cards}</div></div></section>
<section class="cta" id="contato"><div class="wrap"><h2>Fale com {e(name)}</h2>
<p>{("Atendimento em " + e(place) + ". ") if place else ""}Toque no botão e envie sua mensagem.</p>
<a class="btn" href="{cta}" target="_blank" rel="noopener noreferrer">Chamar no WhatsApp</a></div></section>
<footer><div class="wrap">Proposta de página criada pela GTech Digital Studio. Textos, fotos e serviços serão ajustados com você.</div></footer>
</body></html>
"""


def build_zip(lead: dict) -> bytes:
    """ZIP com index.html na raiz (pronto para arrastar no Netlify Drop)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("index.html", render_html(lead))
    return buf.getvalue()
