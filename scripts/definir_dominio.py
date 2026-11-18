"""Troca o endereço do site em todos os arquivos que precisam dele (canonical, compartilhamento, sitemap).

Uso:   python scripts/definir_dominio.py https://www.seudominio.com.br
Pode rodar de novo com outro endereço (por exemplo, quando trocar do .pages.dev para o domínio próprio).
"""
import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"
FILES = ["index.html", "privacidade.html", "robots.txt", "sitemap.xml"]
TOKEN = "__SITE_URL__"


def main() -> None:
    if len(sys.argv) != 2 or not re.fullmatch(r"https?://[^\s/]+", sys.argv[1].rstrip("/")):
        raise SystemExit("Informe o endereço completo, sem barra no final. Ex.: python scripts/definir_dominio.py https://www.seudominio.com.br")
    new = sys.argv[1].rstrip("/")
    index = (SITE / "index.html").read_text(encoding="utf-8")
    m = re.search(r'<link rel="canonical" href="([^"]*?)/">', index)
    old = m.group(1) if m else TOKEN
    for name in FILES:
        p = SITE / name
        txt = p.read_text(encoding="utf-8")
        p.write_text(txt.replace(old, new), encoding="utf-8")
        print("ok", name)
    print(f"Endereço do site definido: {new}")


if __name__ == "__main__":
    main()
