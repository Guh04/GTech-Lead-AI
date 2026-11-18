"""Funções de normalização/validação de campos de entrada (todas em português)."""
import re
from urllib.parse import urlsplit

from app.models.enums import UF_LIST

_INSTAGRAM_RE = re.compile(r"^[A-Za-z0-9._]{1,30}$")


def clean_text(value: str | None, max_len: int, label: str = "Texto") -> str | None:
    """Remove espaços extras; texto vazio vira None."""
    if value is None:
        return None
    text = re.sub(r"[ \t]+", " ", str(value)).strip()
    if not text:
        return None
    if len(text) > max_len:
        raise ValueError(f"{label} muito longo (máximo de {max_len} caracteres).")
    return text


def clean_multiline(value: str | None, max_len: int) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\r\n", "\n").strip()
    if not text:
        return None
    if len(text) > max_len:
        raise ValueError(f"Texto muito longo (máximo de {max_len} caracteres).")
    return text


def normalize_phone(value: str | None) -> str | None:
    """Mantém apenas dígitos (8 a 15)."""
    if value is None or not str(value).strip():
        return None
    digits = re.sub(r"\D", "", str(value))
    if not 8 <= len(digits) <= 15:
        raise ValueError("Telefone inválido. Informe o número com DDD (8 a 15 dígitos).")
    return digits


def normalize_state(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    uf = str(value).strip().upper()
    if uf not in UF_LIST:
        raise ValueError("Estado inválido. Use a sigla com 2 letras (ex.: SP).")
    return uf


def normalize_url(value: str | None, label: str = "Endereço") -> str | None:
    """Garante uma URL http(s) válida. Bloqueia esquemas perigosos (javascript:, data: ...)."""
    if value is None or not str(value).strip():
        return None
    raw = str(value).strip()
    if len(raw) > 500:
        raise ValueError(f"{label} muito longo.")
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", raw) and not re.match(r"^https?://", raw, re.I):
        raise ValueError(f"{label} inválido. Use um link começando com http:// ou https://.")
    if not re.match(r"^https?://", raw, re.I):
        raw = f"https://{raw}"
    parts = urlsplit(raw)
    host = (parts.hostname or "").lower()
    if not host or "." not in host or " " in raw:
        raise ValueError(f"{label} inválido. Exemplo: www.empresa.com.br")
    netloc = host + (f":{parts.port}" if parts.port else "")
    path = parts.path.rstrip("/")
    url = f"{parts.scheme.lower()}://{netloc}{path}"
    if parts.query:
        url += f"?{parts.query}"
    return url


def normalize_instagram(value: str | None) -> str | None:
    """Aceita @usuario, usuario ou link do perfil; guarda só o usuário."""
    if value is None or not str(value).strip():
        return None
    raw = str(value).strip()
    m = re.match(r"^(?:https?://)?(?:www\.)?instagram\.com/([^/?#\s]+)", raw, re.I)
    handle = (m.group(1) if m else raw).lstrip("@").strip().rstrip("/")
    if not _INSTAGRAM_RE.match(handle):
        raise ValueError("Instagram inválido. Use @usuario ou o link do perfil.")
    return handle.lower()


def normalize_facebook(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    raw = str(value).strip()
    if "." not in raw and "/" not in raw and ":" not in raw:
        if not re.match(r"^[A-Za-z0-9.\-]{2,100}$", raw.lstrip("@")):
            raise ValueError("Facebook inválido. Use o link da página.")
        return f"https://facebook.com/{raw.lstrip('@')}"
    return normalize_url(raw, "Facebook")
