"""Análise de sites: classifica se a empresa tem site e se ele funciona como landing page.

O resultado é uma HEURÍSTICA sobre a página inicial (não é uma auditoria). Ela só afirma
o que consegue observar no HTML:

  - site inacessível / sem resposta HTML        -> unknown      (não dá para afirmar nada)
  - página acessível SEM elemento de conversão  -> site_only    (existe, mas não converte)
  - página com título + texto + chamada para ação
    (formulário, WhatsApp, telefone, e-mail ou botão de contato) -> has_landing

O usuário pode corrigir qualquer classificação manualmente na tela do lead.

Segurança: o sistema só busca endereços públicos (bloqueia localhost, redes privadas e
metadados de nuvem), limita redirecionamentos, tempo e tamanho da resposta.
"""
import asyncio
import ipaddress
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx

from app.models.enums import LandingStatus

MAX_BYTES = 400_000
MAX_REDIRECTS = 3
TIMEOUT = httpx.Timeout(8.0, connect=5.0)
USER_AGENT = "Mozilla/5.0 (compatible; GTechLeadAI/1.0; verificacao de site comercial)"

# Perfis em redes sociais não são "site próprio": viram os campos instagram/facebook.
SOCIAL_HOSTS = {
    "instagram.com": "instagram",
    "facebook.com": "facebook",
    "fb.com": "facebook",
    "fb.me": "facebook",
    "m.facebook.com": "facebook",
}
# Páginas de links / mensageiros / marketplaces: existem, mas não são landing page própria.
LINK_ONLY_HOSTS = (
    "linktr.ee", "beacons.ai", "bio.link", "linkin.bio", "taplink.cc", "lnk.bio", "wa.me", "api.whatsapp.com",
    "whatsapp.com", "ifood.com.br", "mercadolivre.com.br", "olx.com.br", "wixsite.com", "business.site",
    "google.com", "goo.gl", "maps.app.goo.gl",
)

_CTA_WORDS = re.compile(
    r"or[çc]amento|agende|agendar|solicite|fale\s+(conosco|com)|entre\s+em\s+contato|chame\s+no\s+whats|"
    r"whatsapp|quero\s+saber|marcar\s+(consulta|hor[áa]rio)|reserve|contrate|peça\s+j[áa]|pe[çc]a\s+j[áa]",
    re.I,
)
_PARKED = re.compile(
    r"dom[ií]nio\s+(est[áa]\s+)?[àa]\s+venda|this\s+domain\s+(is\s+for\s+sale|may\s+be\s+for\s+sale)|"
    r"em\s+constru[çc][ãa]o|coming\s+soon|p[áa]gina\s+n[ãa]o\s+encontrada|account\s+suspended|"
    r"it\s+works!|welcome\s+to\s+nginx|apache2?\s+(ubuntu\s+)?default\s+page",
    re.I,
)


class Fetch:
    def __init__(self, url: str, status: int, text: str, content_type: str):
        self.url, self.status, self.text, self.content_type = url, status, text, content_type


# --------------------------------------------------------------------------- SSRF
async def resolve_host(host: str) -> list[str]:
    """Resolve o host para IPs (isolado para poder ser substituído nos testes)."""
    infos = await asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM)
    return list({info[4][0] for info in infos})


async def is_public_url(url: str) -> bool:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return False
    if parts.port not in (None, 80, 443):
        return False
    host = parts.hostname
    try:
        addresses = [str(ipaddress.ip_address(host))]
    except ValueError:
        try:
            addresses = await resolve_host(host)
        except OSError:
            return False
    if not addresses:
        return False
    return all(ipaddress.ip_address(a).is_global for a in addresses)


# --------------------------------------------------------------------- classificação
def host_of(url: str) -> str:
    return (urlsplit(url).hostname or "").lower().removeprefix("www.")


def classify_url(url: str | None) -> tuple[str, str | None]:
    """Decide o que um endereço informado pelo Google representa.

    Retorna (tipo, valor): ('none', None) | ('instagram'|'facebook', url) | ('link_only', url) | ('website', url).
    """
    if not url:
        return "none", None
    host = host_of(url)
    for domain, kind in SOCIAL_HOSTS.items():
        if host == domain or host.endswith("." + domain):
            return kind, url
    if any(host == d or host.endswith("." + d) for d in LINK_ONLY_HOSTS):
        return "link_only", url
    return "website", url


# ---------------------------------------------------------------------- HTML parsing
class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.h1 = 0
        self.forms = 0
        self.cta_links = 0
        self.buttons_text: list[str] = []
        self.text_parts: list[str] = []
        self._skip = 0
        self._in_title = False
        self._in_button = False
        self._in_a = False
        self.hrefs: list[str] = []  # todos os links da página (para extrair contatos)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style", "noscript", "svg", "template"):
            self._skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "h1":
            self.h1 += 1
        elif tag == "form":
            self.forms += 1
        elif tag in ("button",):
            self._in_button = True
        elif tag == "a":
            self._in_a = True
            if len(self.hrefs) < 400 and a.get("href"):
                self.hrefs.append(a["href"].strip())
            href = (a.get("href") or "").strip().lower()
            if href.startswith(("tel:", "mailto:")) or re.search(r"wa\.me/|api\.whatsapp\.com|wa\.link/|whatsapp://", href):
                self.cta_links += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg", "template"):
            self._skip = max(0, self._skip - 1)
        elif tag == "title":
            self._in_title = False
        elif tag == "button":
            self._in_button = False
        elif tag == "a":
            self._in_a = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
            return
        if self._skip:
            return
        text = data.strip()
        if not text:
            return
        self.text_parts.append(text)
        if self._in_button or self._in_a:
            self.buttons_text.append(text)

    @property
    def text(self) -> str:
        return " ".join(self.text_parts)


def classify_html(html_text: str) -> tuple[LandingStatus, str]:
    """Aplica a heurística ao HTML da página inicial. Retorna (status, motivo)."""
    parser = _PageParser()
    try:
        parser.feed(html_text)
        parser.close()
    except Exception:  # HTML muito quebrado: usa o que foi lido até aqui
        pass
    text = parser.text
    sample = f"{parser.title} {text[:3000]}"
    if len(text) < 200 and _PARKED.search(sample):
        return LandingStatus.SITE_ONLY, "página genérica, em construção ou domínio sem uso"

    has_cta_button = any(_CTA_WORDS.search(t) for t in parser.buttons_text)
    conversion = parser.forms > 0 or parser.cta_links > 0 or has_cta_button
    has_content = len(text) >= 300 and (parser.h1 > 0 or bool(parser.title.strip()))
    if conversion and has_content:
        return LandingStatus.HAS_LANDING, "página com conteúdo e chamada para ação (formulário, WhatsApp, telefone ou botão de contato)"
    if not conversion:
        return LandingStatus.SITE_ONLY, "site sem formulário, WhatsApp, telefone clicável ou botão de contato na página inicial"
    return LandingStatus.SITE_ONLY, "página com pouco conteúdo"


# --------------------------------------------------------------------------- fetch
async def fetch_page(http: httpx.AsyncClient, url: str) -> Fetch | None:
    """Baixa a página inicial seguindo poucos redirecionamentos, sempre revalidando o destino."""
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        if not await is_public_url(current):
            return None
        try:
            async with http.stream("GET", current, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.5"}, timeout=TIMEOUT, follow_redirects=False) as res:
                if res.status_code in (301, 302, 303, 307, 308) and res.headers.get("location"):
                    current = urljoin(current, res.headers["location"])
                    continue
                content_type = res.headers.get("content-type", "").lower()
                body = b""
                async for chunk in res.aiter_bytes():
                    body += chunk
                    if len(body) >= MAX_BYTES:
                        break
                encoding = res.charset_encoding or "utf-8"
                return Fetch(current, res.status_code, body.decode(encoding, errors="replace"), content_type)
        except (httpx.HTTPError, LookupError, ValueError):
            return None
    return None


async def analyze_website(http: httpx.AsyncClient, url: str) -> tuple[LandingStatus, str]:
    """Classifica o site de uma empresa. Em caso de dúvida, devolve 'unknown' (nunca inventa)."""
    page = await fetch_page(http, url)
    if page is None:
        return LandingStatus.UNKNOWN, "site não acessível a partir do servidor"
    if page.status >= 400:
        return LandingStatus.UNKNOWN, f"site respondeu com erro HTTP {page.status}"
    if "html" not in page.content_type and "<html" not in page.text[:2000].lower():
        return LandingStatus.UNKNOWN, "o endereço não retornou uma página HTML"
    return classify_html(page.text)
