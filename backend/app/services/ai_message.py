"""Redação da primeira mensagem de WhatsApp para um lead.

Com ANTHROPIC_API_KEY, a mensagem é escrita pelo Claude. Sem chave (ou se a chamada falhar),
usa-se um texto-modelo. Em ambos os casos a mensagem termina com um aviso de opt-out.
"""
import logging

import httpx

from app.core.config import Settings

log = logging.getLogger("gtech.outreach")

API_URL = "https://api.anthropic.com/v1/messages"
OPT_OUT = "Se não quiser msg, é só avisar."
MAX_LEN = 300

SYSTEM_PROMPT = (
    "Você escreve a PRIMEIRA mensagem de WhatsApp de um profissional brasileiro para o dono de um pequeno negócio local. "
    "Regras: português do Brasil, bem informal, como uma pessoa digitando no celular. MUITO curta: no máximo 2 frases "
    "e 200 caracteres. Só UMA pergunta, no final. Sem emojis, sem markdown, sem listas, sem elogios exagerados, "
    "sem 'espero que esteja bem', sem palavras de marketing. Use SOMENTE os fatos fornecidos; nunca invente nada nem diga "
    "que viu algo que não foi informado. Diga o nome da empresa e quem você é, de forma direta. "
    "Não use urgência nem promessas. Exemplo de tom: 'Oi, tudo bem? Sou o Gui da GTech. Vi a Clínica X e faço sites "
    "pra atrair cliente. Posso te mostrar uma ideia rápida?'. Responda apenas com o texto da mensagem."
)

_LANDING_FACT = {
    "none": "A empresa não tem site próprio.",
    "site_only": "A empresa tem site, mas sem uma landing page focada em conversão.",
    "has_landing": "A empresa já tem landing page.",
}


def _where(lead: dict) -> str:
    return " / ".join(p for p in (lead.get("city"), lead.get("state")) if p)


def facts(lead: dict, settings: Settings) -> str:
    lines = [
        f"Empresa: {lead.get('company_name')}",
        f"Segmento: {lead.get('segment') or 'não informado'}",
        f"Local: {_where(lead) or 'não informado'}",
        f"Responsável: {lead.get('contact_name') or 'não informado'}",
        _LANDING_FACT.get(lead.get("landing_page_status"), "Situação do site: não verificada."),
        f"Quem escreve: {settings.outreach_sender_name or 'um profissional'} da {settings.outreach_sender_company}",
        f"O que oferece: {settings.outreach_offer}",
    ]
    return "\n".join(lines)


def template_message(lead: dict, settings: Settings) -> str:
    sender = settings.outreach_sender_name.strip()
    company = settings.outreach_sender_company
    who = f"Aqui é {sender} da {company}" if sender else f"Sou da {company}"
    hook = {
        "none": "e vi que vocês ainda não têm site",
        "site_only": "e vi que dá pra turbinar o site de vocês",
    }.get(lead.get("landing_page_status"), "")
    seen = f"Vi a {lead['company_name']}" + (f" {hook}" if hook else "")
    return finish(f"Oi, tudo bem? {who}. {seen}. Posso te mandar uma ideia rápida?")


def finish(text: str) -> str:
    """Normaliza o texto e garante o aviso de opt-out (LGPD / boa conduta)."""
    text = " ".join(text.split()).strip()
    if len(text) > MAX_LEN:
        text = text[: MAX_LEN - 1].rstrip() + "…"
    if "avisar" not in text.lower():
        text = f"{text} {OPT_OUT}"
    return text


async def _ask_claude(settings: Settings, http: httpx.AsyncClient, lead: dict) -> str:
    res = await http.post(
        API_URL,
        headers={"x-api-key": settings.anthropic_api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={
            "model": settings.outreach_model,
            "max_tokens": 400,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": facts(lead, settings)}],
        },
        timeout=settings.outreach_timeout_seconds,
    )
    res.raise_for_status()
    blocks = res.json().get("content") or []
    text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
    if not text:
        raise ValueError("resposta vazia da IA")
    return text


async def compose(settings: Settings, http: httpx.AsyncClient, lead: dict) -> tuple[str, str]:
    """Devolve (mensagem, origem) onde origem é 'ai' ou 'template'."""
    if settings.anthropic_api_key.strip():
        try:
            return finish(await _ask_claude(settings, http, lead)), "ai"
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            log.warning("IA indisponível para %s (%s); usando texto-modelo.", lead.get("company_name"), type(exc).__name__)
    return template_message(lead, settings), "template"
