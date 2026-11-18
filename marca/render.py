"""Renderiza HTML em PNG usando o Chrome instalado (sem dependências Python).

Uso:  python render.py <arquivo.html> <saida.png> <largura> <altura> [rolagem_total]
Com 'full' no fim, a altura passa a ser a da página inteira.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

CHROME = next((p for p in (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
) if Path(p).exists()), None)


def shot(html: Path, png: Path, width: int, height: int, scale: float = 1.0, bg: str | None = None) -> None:
    if not CHROME:
        raise SystemExit("Chrome/Edge não encontrado.")
    png = png.resolve()  # o Chrome grava relativo ao diretório dele, não ao nosso
    png.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run([
            CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={profile}",
            f"--window-size={width},{height}", f"--force-device-scale-factor={scale}",
            "--virtual-time-budget=9000", *([f"--default-background-color={bg}"] if bg else []),
            f"--screenshot={png}", html.resolve().as_uri(),
        ], check=True, capture_output=True, timeout=120)


if __name__ == "__main__":
    h, p, w, ht = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    shot(h, p, w, ht, float(sys.argv[5]) if len(sys.argv) > 5 else 1.0)
