"""Redação da primeira mensagem de WhatsApp para um lead.

A mensagem-modelo (MODEL) é o texto definido pelo dono do sistema. Sem ANTHROPIC_API_KEY (ou se a IA
falhar) ela é usada como está. Com a chave, o Claude só varia levemente as palavras, mantendo a
estrutura e o conteúdo: mensagens idênticas enviadas em massa são um sinal clássico de spam para o
WhatsApp, então pequenas variações protegem o número. A IA não recebe dados do lead.
"""
import logging

import httpx

from app.core.config import Settings

log = logging.getLogger("gtech.outreach")

API_URL = "https://api.anthropic.com/v1/messages"
MAX_LEN = 900

MODEL = (
    "Olá, tudo bem?\n\n"
    "{intro} com {offer}.\n\n"
    "Estou entrando em contato para saber se vocês já possuem uma página própria para apresentar seus serviços "
    "e facilitar o contato com novos clientes.\n\n"
    "Caso tenham interesse, posso apresentar uma proposta de como poderíamos desenvolver uma página moderna e "
    "personalizada para o negócio de vocês.\n\n"
    "Fico à disposição!"
)

SYSTEM_PROMPT = (
    "Você reescreve uma mensagem de WhatsApp de prospecção, em português do Brasil. Receberá a mensagem-modelo. "
    "Devolva a MESMA mensagem com pequenas variações de palavras (sinônimos, ordem de uma frase), mantendo exatamente "
    "o mesmo conteúdo, a mesma estrutura de parágrafos separados por linha em branco, o mesmo tom educado e o mesmo "
    "tamanho. Mantenha o nome e a descrição do que a pessoa faz como estão. Não acrescente informações, promessas, "
    "elogios, emojis nem markdown. Responda apenas com o texto da mensagem."
)


def model_text(settings: Settings) -> str:
    name = settings.outreach_sender_name.strip()
    offer = settings.outreach_offer.strip()
    text = MODEL.format(name=name, offer=offer)
    if not name:  # sem nome configurado: "Meu nome é , trabalho com..." ficaria errado
        text = text.replace("Meu nome é , trabalho", "Trabalho")
    return text


def finish(text: str, settings: Settings) -> str:
    """Normaliza espaços (preservando os parágrafos) e garante o aviso de opt-out (LGPD / boa conduta)."""
    paragraphs = [" ".join(p.split()) for p in text.replace("\r", "").split("\n\n")]
    text = "\n\n".join(p for p in paragraphs if p)
    if len(text) > MAX_LEN:
        text = text[: MAX_LEN - 1].rstrip() + "…"
    opt_out = settings.outreach_opt_out.strip()
    if opt_out and "avisar" not in text.lower():
        text = f"{text}\n\n{opt_out}"
    return text


def template_message(lead: dict, settings: Settings) -> str:
    return finish(model_text(settings), settings)


async def _ask_claude(settings: Settings, http: httpx.AsyncClient) -> str:
    res = await http.post(
        API_URL,
        headers={"x-api-key": settings.anthropic_api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={
            "model": settings.outreach_model,
            "max_tokens": 500,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": model_text(settings)}],
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
    """Devolve (mensagem, origem) onde origem é 'ai' (variação da IA) ou 'template' (texto-modelo)."""
    if settings.anthropic_api_key.strip():
        try:
            return finish(await _ask_claude(settings, http), settings), "ai"
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            log.warning("IA indisponível para %s (%s); usando texto-modelo.", lead.get("company_name"), type(exc).__name__)
    return template_message(lead, settings), "template"
