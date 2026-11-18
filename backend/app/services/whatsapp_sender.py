"""Envio de mensagens pelo WhatsApp conectado no WhatsMCP (servidor MCP sobre HTTP, JSON-RPC).

Só é usado quando WHATSMCP_API_KEY está definida e o usuário clicou em enviar uma mensagem já aprovada.
"""
import json
import logging

import httpx

from app.core.config import Settings

log = logging.getLogger("gtech.whatsapp")


class SendFailed(Exception):
    """Nada foi enviado (chave inválida, serviço fora do ar, recusa). É seguro tentar de novo."""


class SendUnknown(Exception):
    """A requisição saiu mas a resposta não chegou: a mensagem pode ter sido enviada. NÃO reenviar."""


_REASONS = {
    "recipient_not_contact": "o número não é um contato válido para esta conta",
    "rate_limited": "limite de envios do plano do WhatsMCP atingido",
}


def _parse(text: str) -> dict:
    text = text.strip()
    if text.startswith("{"):
        return json.loads(text)
    for line in text.splitlines():  # resposta em formato SSE
        if line.startswith("data:"):
            return json.loads(line[5:].strip())
    raise ValueError("resposta inesperada do WhatsMCP")


async def send_text(settings: Settings, http: httpx.AsyncClient, phone: str, text: str) -> str:
    """Envia um texto e devolve 'sent' ou 'queued'. `phone` em formato internacional, só dígitos."""
    # force=True: leads são desconhecidos da agenda do número; sem isso o WhatsMCP recusa o envio 1:1.
    arguments: dict = {"to": phone, "text": text, "force": True}
    if settings.whatsmcp_account_id.strip():
        arguments["account_id"] = settings.whatsmcp_account_id.strip()
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "wa_send_message", "arguments": arguments}}
    headers = {
        "Authorization": f"Bearer {settings.whatsmcp_api_key.strip()}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    try:
        res = await http.post(settings.whatsmcp_url, headers=headers, json=payload, timeout=settings.whatsmcp_timeout_seconds)
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        raise SendFailed("Não foi possível conectar ao WhatsMCP.") from exc
    except httpx.HTTPError as exc:
        log.warning("WhatsMCP sem resposta (%s); envio sem confirmação.", type(exc).__name__)
        raise SendUnknown from exc

    if res.status_code in (401, 403):
        raise SendFailed("Chave do WhatsMCP inválida ou sem permissão. Confira WHATSMCP_API_KEY em backend/.env.")
    if res.status_code >= 500:
        raise SendUnknown
    if res.status_code >= 400:
        raise SendFailed(f"O WhatsMCP recusou a requisição (HTTP {res.status_code}).")

    try:
        data = _parse(res.text)
    except (ValueError, json.JSONDecodeError) as exc:
        raise SendUnknown from exc
    if "error" in data:
        raise SendFailed(f"WhatsMCP: {data['error'].get('message', 'erro')}")
    result = data.get("result") or {}
    out = result.get("structuredContent")
    if out is None:
        try:
            out = json.loads(next(b["text"] for b in result.get("content", []) if b.get("type") == "text"))
        except (StopIteration, ValueError, KeyError):
            out = {}
    if result.get("isError") or out.get("status") == "refused":
        reason = out.get("reason") or out.get("error") or "recusado"
        raise SendFailed(f"O WhatsMCP não enviou: {_REASONS.get(reason, reason)}.")
    status = out.get("status")
    if status in ("sent", "queued"):
        return status
    raise SendUnknown  # resposta sem status claro: trata como incerto para nunca duplicar
