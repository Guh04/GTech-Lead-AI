"""Dashboard e relatórios."""
from fastapi import APIRouter, Depends, Query

from app.routes.deps import analytics_service
from app.schemas.analytics import DashboardOut, ReportOut
from app.services.analytics_service import AnalyticsService

router = APIRouter(tags=["analytics"])


@router.get("/dashboard", response_model=DashboardOut, summary="Indicadores do dashboard")
async def dashboard(
    days: int = Query(30, ge=7, le=365, description="Período do gráfico de leads por dia"),
    svc: AnalyticsService = Depends(analytics_service),
):
    return await svc.dashboard(days)


@router.get("/reports", response_model=ReportOut, summary="Relatórios comerciais")
async def reports(
    days: int = Query(90, ge=0, le=3650, description="Período em dias (0 = todo o período)"),
    svc: AnalyticsService = Depends(analytics_service),
):
    return await svc.report(days)
