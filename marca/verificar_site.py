"""Verifica o site: links e arquivos, SEO, acessibilidade básica e JavaScript (via Chrome).

Uso: python verificar_site.py        (com o servidor do site em http://localhost:5500)
"""
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from render import CHROME

SITE = Path(__file__).resolve().parent.parent / "site"
BASE = "http://localhost:5500"
problems: list[str] = []


def bad(msg: str) -> None:
    problems.append(msg)
    print("PROBLEMA:", msg)


def pages() -> list[Path]:
    return [p for p in SITE.rglob("*.html") if not p.name.startswith("_")]


def check_links() -> int:
    checked = 0
    for html in pages():
        txt = html.read_text(encoding="utf-8")
        ids = set(re.findall(r'\bid="([^"]+)"', txt))
        for _, val in re.findall(r'\b(href|src)="([^"]+)"', txt):
            if val.startswith(("http", "mailto:", "tel:", "data:", "javascript:")) or "__SITE_URL__" in val:
                continue
            u = urlsplit(val)
            checked += 1
            if val.startswith("#"):
                if val != "#" and val[1:] not in ids:
                    bad(f"{html.relative_to(SITE)}: âncora inexistente {val}")
                continue
            path = u.path.lstrip("/") if u.path.startswith("/") else u.path
            target = (SITE / path).resolve() if u.path.startswith("/") else (html.parent / path).resolve()
            if not target.exists():
                bad(f"{html.relative_to(SITE)}: arquivo inexistente {val}")
            elif u.fragment and target.suffix == ".html":
                if u.fragment not in re.findall(r'\bid="([^"]+)"', target.read_text(encoding="utf-8")):
                    bad(f"{html.relative_to(SITE)}: âncora {val} não existe no destino")
    for css in SITE.rglob("*.css"):
        for val in re.findall(r"url\(([^)]+)\)", css.read_text(encoding="utf-8")):
            val = val.strip("'\"")
            if val.startswith(("data:", "http")):
                continue
            checked += 1
            if not (css.parent / val).resolve().exists():
                bad(f"{css.name}: url() inexistente {val}")
    return checked


def check_seo_and_a11y() -> None:
    for html in pages():
        rel = html.relative_to(SITE)
        txt = html.read_text(encoding="utf-8")
        if not re.search(r"<title>[^<]{10,}</title>", txt):
            bad(f"{rel}: título ausente ou curto")
        if 'name="description"' not in txt:
            bad(f"{rel}: sem meta description")
        if 'lang="pt-BR"' not in txt:
            bad(f"{rel}: sem lang pt-BR")
        if 'name="viewport"' not in txt:
            bad(f"{rel}: sem viewport")
        for img in re.findall(r"<img\b[^>]*>", txt):
            if " alt=" not in img:
                bad(f"{rel}: imagem sem alt: {img[:70]}")
        if len(re.findall(r"<h1\b", txt)) != 1 and rel.name != "index.html" and "projetos" not in str(rel):
            pass
        if rel.name == "index.html" and len(re.findall(r"<h1\b", txt)) != 1:
            bad("index.html: deve ter exatamente um <h1>")
    index = (SITE / "index.html").read_text(encoding="utf-8")
    for need in ('rel="canonical"', 'property="og:image"', 'name="twitter:card"', 'application/ld+json', 'rel="apple-touch-icon"'):
        if need not in index:
            bad(f"index.html: falta {need}")
    for f in ("assets/og-image.png", "assets/icons/apple-touch-icon.png", "robots.txt", "sitemap.xml", "404.html", "privacidade.html"):
        if not (SITE / f).exists():
            bad(f"arquivo ausente: {f}")


def dump(url: str, budget: int = 6000) -> tuple[str, str]:
    with tempfile.TemporaryDirectory() as prof:
        r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", f"--user-data-dir={prof}", "--enable-logging=stderr", "--v=0",
                            "--window-size=1440,900", f"--virtual-time-budget={budget}", "--dump-dom", url],
                           capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace")
    return r.stdout, r.stderr


def check_js() -> None:
    dom, err = dump(f"{BASE}/index.html")
    console = [l for l in err.splitlines() if "CONSOLE" in l and ("error" in l.lower() or "uncaught" in l.lower())]
    for l in console:
        bad(f"erro de console: {l[:160]}")
    cfg = (SITE / "js" / "config.js").read_text(encoding="utf-8")
    number = re.search(r'whatsapp:\s*"(\d+)"', cfg).group(1)
    wa = re.findall(r'href="https://wa\.me/(\d+)\?text=[^"]+"', dom)
    if len(wa) < 8 or set(wa) != {number}:
        bad(f"botões de WhatsApp: {len(wa)} com texto, números={set(wa)}")
    if 'class="w"' not in dom:
        bad("título do hero não foi dividido em palavras (JS)")
    if "--sp" not in dom:
        pass
    for token, label in ((r'href="https://instagram\.com/', "Instagram"), (r'href="mailto:', "e-mail"), (r"CNPJ \d", "CNPJ")):
        if not re.search(token, dom):
            bad(f"rodapé sem {label}")


def main() -> None:
    print("arquivos e links verificados:", check_links())
    check_seo_and_a11y()
    check_js()
    print("\nRESULTADO:", "tudo certo" if not problems else f"{len(problems)} problema(s)")


if __name__ == "__main__":
    main()
