"""Abordagem por WhatsApp: fila de mensagens preparadas pela IA, aprovação e envio com limite diário."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.models.enums import OutreachStatus
from app.routes.deps import outreach_service
from app.schemas.outreach import GenerateRequest, MessageUpdate, OutreachStatusOut
from app.services.outreach_service import OutreachService

router = APIRouter(prefix="/outreach", tags=["outreach"])


@router.get("/status", response_model=OutreachStatusOut, summary="Limite diário e envios de hoje")
async def status(svc: OutreachService = Depends(outreach_service)):
    return await svc.status()


@router.get("/counts", summary="Quantidade de mensagens por situação")
async def counts(svc: OutreachService = Depends(outreach_service)):
    return await svc.counts()


@router.get("", summary="Fila de mensagens")
async def list_messages(
    status: OutreachStatus | None = None, limit: int = Query(100, ge=1, le=200), svc: OutreachService = Depends(outreach_service)
):
    return await svc.list(status, limit)


@router.post("/generate", status_code=201, summary="Gerar rascunhos de mensagem para os melhores leads com WhatsApp")
async def generate(body: GenerateRequest, svc: OutreachService = Depends(outreach_service)):
    return await svc.generate(body.count, body.search_id)


@router.patch("/{message_id}", summary="Editar o texto (volta para rascunho)")
async def edit(message_id: UUID, body: MessageUpdate, svc: OutreachService = Depends(outreach_service)):
    return await svc.edit(str(message_id), body.body)


@router.post("/{message_id}/approve", summary="Aprovar a mensagem")
async def approve(message_id: UUID, svc: OutreachService = Depends(outreach_service)):
    return await svc.approve(str(message_id))


@router.post("/{message_id}/skip", summary="Descartar a mensagem")
async def skip(message_id: UUID, svc: OutreachService = Depends(outreach_service)):
    return await svc.skip(str(message_id))


@router.post(
    "/{message_id}/send",
    summary="Registrar o envio e obter o link do WhatsApp",
    description="Aplica o limite diário e o intervalo mínimo. O sistema não envia nada: devolve o link wa.me com o texto pronto.",
)
async def send(message_id: UUID, svc: OutreachService = Depends(outreach_service)):
    return await svc.send(str(message_id))
