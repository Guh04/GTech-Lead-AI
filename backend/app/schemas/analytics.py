"""Schemas das respostas de dashboard e relatórios."""
from datetime import datetime

from pydantic import BaseModel

from app.schemas.activity import RecentActivityOut
from app.schemas.lead import LeadOut


class Totals(BaseModel):
    total: int
    new: int
    analyzed: int
    contacted: int
    interested: int
    proposal_sent: int
    closed_won: int
    lost: int
    high_priority: int


class PeriodPoint(BaseModel):
    date: str  # YYYY-MM-DD (início do dia/semana/mês)
    count: int


class SegmentPoint(BaseModel):
    segment: str
    count: int


class RegionPoint(BaseModel):
    state: str
    count: int


class FunnelStage(BaseModel):
    status: str
    count: int


class DashboardOut(BaseModel):
    period_days: int
    totals: Totals
    conversion_rate: float  # clientes fechados / total de leads (%)
    leads_by_period: list[PeriodPoint]
    leads_by_segment: list[SegmentPoint]
    recent_activities: list[RecentActivityOut]
    latest_leads: list[LeadOut]


class Conversion(BaseModel):
    total: int
    closed_won: int
    lost: int
    conversion_rate: float  # fechados / total (%)
    win_rate: float | None  # fechados / (fechados + perdidos) (%); None se nada foi encerrado


class SearchOut(BaseModel):
    id: str
    region: str
    state: str | None = None
    segments: list[str]
    desired_quantity: int
    website_filter: str
    landing_filter: str
    status: str
    provider: str | None = None
    results_count: int
    inserted_count: int
    duplicates_count: int
    error_message: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


class ReportOut(BaseModel):
    period_days: int  # 0 = todo o período
    granularity: str  # day | week | month
    total_in_period: int
    leads_by_period: list[PeriodPoint]
    leads_by_segment: list[SegmentPoint]
    leads_by_region: list[RegionPoint]
    funnel: list[FunnelStage]
    conversion: Conversion
    closed_clients: list[LeadOut]
    prospecting_history: list[SearchOut]
