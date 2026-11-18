"""Endpoints de leads."""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.models.enums import LandingStatus, LeadSource, LeadStatus, Priority
from app.routes.deps import lead_service, today_cutoff
from app.schemas.activity import ActivityOut, NoteCreate
from app.schemas.lead import Facets, LeadCreate, LeadOut, LeadPage, LeadUpdate, StatusChange
from app.services.lead_service import SORTS, LeadFilters, LeadService

router = APIRouter(prefix="/leads", tags=["leads"])


def filters(
    search: str | None = Query(None, max_length=100, description="Busca por nome da empresa ou responsável"),
    segment: str | None = Query(None, max_length=120),
    city: str | None = Query(None, max_length=120),
    state: str | None = Query(None, min_length=2, max_length=2),
    priority: Priority | None = None,
    status: LeadStatus | None = None,
    landing_status: LandingStatus | None = None,
    source: LeadSource | None = None,
    active: bool = Query(False, description="Somente leads em negociação (exclui fechados e perdidos)"),
    search_id: UUID | None = Query(None, description="Leads encontrados por uma pesquisa de prospecção"),
    has_whatsapp: bool | None = Query(None, description="true = somente com WhatsApp; false = somente sem"),
    contactable: bool = Query(False, description="Somente leads ainda não contatados e sem pedido de 'não contatar'"),
    sort: str = Query("created_desc", pattern="^(" + "|".join(SORTS) + ")$"),
) -> LeadFilters:
    return LeadFilters(
        search=search, segment=segment, city=city, state=state.upper() if state else None, priority=priority,
        status=status, landing_status=landing_status, source=source, active=active,
        search_id=str(search_id) if search_id else None, has_whatsapp=has_whatsapp, contactable=contactable, sort=sort,
    )


@router.get("", response_model=LeadPage, summary="Listar leads (com filtros, ordenação e paginação)")
async def list_leads(
    f: LeadFilters = Depends(filters),
    page: int = Query(1, ge=1, le=100_000),
    page_size: int = Query(20, ge=1, le=500),
    svc: LeadService = Depends(lead_service),
):
    return await svc.list(f, page, page_size)


@router.get("/facets", response_model=Facets, summary="Valores para filtros e contadores")
async def facets(svc: LeadService = Depends(lead_service)):
    return await svc.facets()


@router.get("/{lead_id}/demo", summary="Página de demonstração (ZIP) para o lead, pronta para publicar")
async def demo_site(lead_id: UUID, svc: LeadService = Depends(lead_service)):
    lead = await svc.get(str(lead_id))
    return Response(
        content=demo_site_service.build_zip(lead),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="demo-{demo_site_service.slug(lead["company_name"])}.zip"'},
    )


@router.get("/export", summary="Exportar leads para CSV (respeita os filtros)")
async def export_csv(f: LeadFilters = Depends(filters), svc: LeadService = Depends(lead_service)):
    content = await svc.export_csv(f)
    filename = f"gtech-leads-{date.today().isoformat()}.csv"
    return Response(
        content=content.encode("utf-8-sig"),  # BOM: o Excel reconhece os acentos
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"},
    )


@router.post("", response_model=LeadOut, status_code=201, summary="Cadastrar lead")
async def create_lead(body: LeadCreate, svc: LeadService = Depends(lead_service)):
    return await svc.create(body)


@router.get("/cleanup/preview", summary="Quantos leads de dias anteriores seriam apagados (nada é apagado)")
async def cleanup_preview(
    include_today: bool = Query(False, description="true = também considera os leads de hoje"),
    cutoff: str = Depends(today_cutoff),
    svc: LeadService = Depends(lead_service),
):
    return await svc.cleanup_preview(None if include_today else cutoff)


@router.post(
    "/cleanup",
    summary="Apagar leads de dias anteriores",
    description="Apaga leads criados antes de hoje que ainda estão como novo/analisado e sem 'não contatar'. "
    "Leads já contatados, em negociação, fechados ou com pedido de não contato são preservados.",
)
async def cleanup(
    include_today: bool = Query(False, description="true = apaga também os leads de hoje que ainda não foram contatados"),
    cutoff: str = Depends(today_cutoff),
    svc: LeadService = Depends(lead_service),
):
    return await svc.cleanup(None if include_today else cutoff)


@router.get("/{lead_id}", response_model=LeadOut, summary="Detalhes de um lead")
async def get_lead(lead_id: UUID, svc: LeadService = Depends(lead_service)):
    return await svc.get(str(lead_id))


@router.put("/{lead_id}", response_model=LeadOut, summary="Editar lead (somente os campos enviados são alterados)")
async def update_lead(lead_id: UUID, body: LeadUpdate, svc: LeadService = Depends(lead_service)):
    return await svc.update(str(lead_id), body)


@router.patch("/{lead_id}/status", response_model=LeadOut, summary="Mover lead de estágio no pipeline")
async def move_lead(lead_id: UUID, body: StatusChange, svc: LeadService = Depends(lead_service)):
    return await svc.move_status(str(lead_id), body.status)


@router.delete("/{lead_id}", status_code=204, summary="Excluir lead")
async def delete_lead(lead_id: UUID, svc: LeadService = Depends(lead_service)):
    await svc.delete(str(lead_id))
    return Response(status_code=204)


@router.get("/{lead_id}/activities", response_model=list[ActivityOut], summary="Histórico do lead")
async def lead_activities(lead_id: UUID, svc: LeadService = Depends(lead_service)):
    await svc.get(str(lead_id))
    return await svc.activities.for_lead(str(lead_id))


@router.post("/{lead_id}/activities", response_model=ActivityOut, status_code=201, summary="Registrar anotação")
async def add_note(lead_id: UUID, body: NoteCreate, svc: LeadService = Depends(lead_service)):
    return await svc.add_note(str(lead_id), body.description)
