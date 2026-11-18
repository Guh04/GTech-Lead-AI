"""Schemas de leads (entrada e saída da API)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import (
    LandingStatus,
    LeadSource,
    LeadStatus,
    Priority,
    ScoreSource,
)
from app.schemas import normalize as n


class _LeadFields(BaseModel):
    """Campos editáveis de um lead, com normalização/validação."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    company_name: str | None = None
    contact_name: str | None = None
    segment: str | None = None
    city: str | None = None
    state: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    instagram: str | None = None
    facebook: str | None = None
    website: str | None = None
    landing_page_status: LandingStatus = LandingStatus.UNKNOWN
    # Pontuação manual (0-100). Vazio/None = cálculo automático por regras.
    score: int | None = Field(default=None, ge=0, le=100)
    status: LeadStatus = LeadStatus.NEW
    source: LeadSource = LeadSource.MANUAL
    source_url: str | None = None
    notes: str | None = None
    do_not_contact: bool = False

    @field_validator("company_name", mode="before")
    @classmethod
    def _company(cls, v):
        text = n.clean_text(v, 200, "Nome")
        if text is not None and len(text) < 2:
            raise ValueError("O nome da empresa precisa ter ao menos 2 caracteres.")
        return text

    @field_validator("contact_name", mode="before")
    @classmethod
    def _contact(cls, v):
        return n.clean_text(v, 160, "Nome do responsável")

    @field_validator("segment", "city", mode="before")
    @classmethod
    def _short_text(cls, v):
        return n.clean_text(v, 120)

    @field_validator("state", mode="before")
    @classmethod
    def _state(cls, v):
        return n.normalize_state(v)

    @field_validator("phone", "whatsapp", mode="before")
    @classmethod
    def _phones(cls, v):
        return n.normalize_phone(v)

    @field_validator("instagram", mode="before")
    @classmethod
    def _instagram(cls, v):
        return n.normalize_instagram(v)

    @field_validator("facebook", mode="before")
    @classmethod
    def _facebook(cls, v):
        return n.normalize_facebook(v)

    @field_validator("website", mode="before")
    @classmethod
    def _website(cls, v):
        return n.normalize_url(v, "Site")

    @field_validator("source_url", mode="before")
    @classmethod
    def _source_url(cls, v):
        return n.normalize_url(v, "Link da fonte")

    @field_validator("notes", mode="before")
    @classmethod
    def _notes(cls, v):
        return n.clean_multiline(v, 5000)


class LeadCreate(_LeadFields):
    company_name: str = Field(..., description="Nome da empresa (obrigatório)")

    @field_validator("company_name", mode="before")
    @classmethod
    def _company_required(cls, v):
        text = n.clean_text(v, 200, "Nome")
        if not text or len(text) < 2:
            raise ValueError("Informe o nome da empresa (mínimo de 2 caracteres).")
        return text


class LeadUpdate(_LeadFields):
    """PUT parcial: só os campos enviados são alterados; null limpa campos opcionais."""

    landing_page_status: LandingStatus | None = None  # type: ignore[assignment]
    status: LeadStatus | None = None  # type: ignore[assignment]
    source: LeadSource | None = None  # type: ignore[assignment]
    do_not_contact: bool | None = None  # type: ignore[assignment]

    @field_validator("company_name", mode="after")
    @classmethod
    def _company_not_empty(cls, v):
        if v is None:
            raise ValueError("O nome da empresa não pode ficar vazio.")
        return v


class StatusChange(BaseModel):
    status: LeadStatus


class LeadOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    company_name: str
    contact_name: str | None = None
    segment: str | None = None
    city: str | None = None
    state: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    instagram: str | None = None
    facebook: str | None = None
    website: str | None = None
    landing_page_status: LandingStatus
    score: int
    score_source: ScoreSource
    priority: Priority
    source: LeadSource
    source_url: str | None = None
    prospecting_search_id: UUID | None = None
    status: LeadStatus
    status_updated_at: datetime
    notes: str | None = None
    do_not_contact: bool
    created_at: datetime
    updated_at: datetime


class LeadPage(BaseModel):
    items: list[LeadOut]
    total: int
    page: int
    page_size: int


class Facets(BaseModel):
    segments: list[str]
    cities: list[str]
    states: list[str]
    priority_counts: dict[str, int]  # somente leads ativos (exclui fechados e perdidos)
    priority_thresholds: dict[str, int]
    status_counts: dict[str, int]
