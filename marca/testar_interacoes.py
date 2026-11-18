"""Testa interações no Chrome: menu móvel, âncoras, formulários e menu das 4 demonstrações.

Injeta um script em cópias temporárias (_t_*.html) que clica nos elementos e grava o resultado no <title>.
Uso: python testar_interacoes.py   (servidor em http://localhost:5500)
"""
import re
import subprocess
import tempfile
from pathlib import Path

from render import CHROME

SITE = Path(__file__).resolve().parent.parent / "site"
BASE = "http://localhost:5500"

INDEX_TEST = """<script>addEventListener('load',function(){setTimeout(function(){var r=[];
 var b=document.querySelector('.burger');b.click();r.push('menu_abre='+document.body.classList.contains('menu-open')+'/'+b.getAttribute('aria-expanded'));
 document.querySelector('.drawer nav a').click();r.push('menu_fecha_ao_clicar='+!document.body.classList.contains('menu-open'));
 b.click();dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'}));r.push('esc_fecha='+!document.body.classList.contains('menu-open'));
 r.push('cards='+document.querySelectorAll('.card').length+' hrefs_ok='+[].every.call(document.querySelectorAll('.card'),function(c){return /projetos\\/\\w+\\/index\\.html$/.test(c.getAttribute('href'))}));
 r.push('processo_steps='+document.querySelectorAll('.step').length+' rv='+document.querySelectorAll('.rv').length);
 r.push('hero_palavras='+document.querySelectorAll('.hero h1 .wi').length);
 document.title='T|'+r.join(' ; ')},500)})</script></body>"""

DEMO_TEST = """<script>addEventListener('load',function(){var r=[];
 var f=document.querySelector('form.demo-form');f.requestSubmit();r.push('bloqueia_vazio='+!!document.querySelector('form.demo-form'));
 f.querySelectorAll('input,select,textarea').forEach(function(el){if(el.tagName==='SELECT')el.selectedIndex=1;else if(el.required)el.value='11999990000'});
 f.requestSubmit();r.push('responde='+!!document.querySelector('.demo-ok'));
 var mb=document.querySelector('.mb');mb.click();r.push('menu='+document.querySelector('.links').classList.contains('open'));
 r.push('voltar_portfolio='+!!document.querySelector('.demobar a[href="../../index.html#projetos"]'));
 r.push('faq='+document.querySelectorAll('details.faq').length);
 document.title='T|'+r.join(' ; ')})</script></body>"""


def run(name: str, html: str, test: str, budget: int = 5000) -> str:
    tmp = SITE / name
    tmp.write_text(html.replace("</body>", test), encoding="utf-8")
    try:
        with tempfile.TemporaryDirectory() as prof:
            r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", f"--user-data-dir={prof}", "--window-size=1440,900",
                                f"--virtual-time-budget={budget}", "--dump-dom", f"{BASE}/{name.replace(chr(92), '/')}"],
                               capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace")
    finally:
        tmp.unlink(missing_ok=True)
    m = re.search(r"<title>T\|([^<]*)", r.stdout)
    return m.group(1) if m else "SEM RESULTADO"


def main() -> None:
    ok = True
    out = run("_t_index.html", (SITE / "index.html").read_text(encoding="utf-8"), INDEX_TEST)
    print("index   :", out)
    ok &= "menu_abre=true/true" in out and "menu_fecha_ao_clicar=true" in out and "esc_fecha=true" in out and "hrefs_ok=true" in out
    for k in ("clinica", "advocacia", "estetica", "servicos"):
        out = run(f"projetos/{k}/_t.html", (SITE / "projetos" / k / "index.html").read_text(encoding="utf-8"), DEMO_TEST)
        print(f"{k:9}:", out)
        ok &= all(x in out for x in ("bloqueia_vazio=true", "responde=true", "menu=true", "voltar_portfolio=true"))
    print("\nRESULTADO:", "todas as interações funcionam" if ok else "HÁ FALHAS")


if __name__ == "__main__":
    main()
