"""Gera capturas de teste do site (desktop, linha do tempo do hero e celular) em marca/export/_check-*.png.

As animações de entrada são neutralizadas só na cópia de teste (site/_check.html), para o print mostrar o layout final.
Uso: python check_site.py   (com o servidor do site rodando em http://localhost:5500)
"""
import pathlib

from PIL import Image

from render import shot

SITE = pathlib.Path(__file__).resolve().parent.parent / "site"
OUT = pathlib.Path(__file__).resolve().parent / "export"
URL = "http://localhost:5500/_check.html"
FORCE = ("<style>.rv{opacity:1!important;animation:none!important}.step{opacity:1!important}.wa-fab{display:none}"
         "body{animation:none!important}.hero .enter{opacity:1!important;transform:none!important;animation:none!important}"
         ".hero h1 .wi{transform:none!important;animation:none!important}</style>")


def main() -> None:
    src = (SITE / "index.html").read_text(encoding="utf-8")
    (SITE / "_check.html").write_text(src.replace("<head>", "<head>" + FORCE, 1), encoding="utf-8")
    tiles = []
    for t in (8300, 9600, 15500, 22500):
        p = OUT / f"_check-t{t}.png"
        shot(URL, p, 1440, 900, 1.0, None, t)
        tiles.append(Image.open(p).crop((620, 150, 1440, 900)).resize((410, 375)))
    sheet = Image.new("RGB", (820, 750), (30, 30, 30))
    for i, im in enumerate(tiles):
        sheet.paste(im, ((i % 2) * 410, (i // 2) * 375))
    sheet.save(OUT / "_check-hero-timeline.png")
    shot(URL, OUT / "_check-mobile.png", 390, 1250, 1)
    shot(URL, OUT / "_check-full.png", 1440, 5400)
    print("ok")


if __name__ == "__main__":
    main()
