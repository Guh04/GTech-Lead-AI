"""Prospecção: histórico e (futura) execução de pesquisas pelo agente de IA."""
from fastapi import APIRouter, Depends, Query

from app.routes.deps import prospecting_service
from app.schemas.analytics import SearchOut
from app.schemas.prospecting import ProspectingStatus, SearchRequest
from app.services.prospecting.service import ProspectingService

router = APIRouter(prefix="/prospecting", tags=["prospecting"])


@router.get("/status", response_model=ProspectingStatus, summary="Há um agente de prospecção conectado?")
async def status(svc: ProspectingService = Depends(prospecting_service)):
    return svc.status()


@router.get("/history", response_model=list[SearchOut], summary="Histórico de pesquisas")
async def history(limit: int = Query(30, ge=1, le=100), svc: ProspectingService = Depends(prospecting_service)):
    return await svc.history(limit)


@router.post(
    "/search",
    response_model=SearchOut,
    status_code=201,
    summary="Iniciar pesquisa de prospecção",
    description="Executa a pesquisa no agente configurado e grava os leads encontrados (origem 'ai_agent'). "
    "Retorna 503 enquanto nenhum agente estiver conectado.",
)
async def search(body: SearchRequest, svc: ProspectingService = Depends(prospecting_service)):
    return await svc.run(body)
