from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import LandingFilter, WebsiteFilter
from app.schemas import normalize as n


class SearchRequest(BaseModel):
    """Parâmetros de uma pesquisa de prospecção (também enviados ao provedor/agente)."""

    model_config = ConfigDict(extra="ignore")

    region: str
    state: str | None = None
    segments: list[str] = Field(..., min_length=1, max_length=20)
    desired_quantity: int = Field(30, ge=1, le=500)
    website_filter: WebsiteFilter = WebsiteFilter.ANY
    landing_filter: LandingFilter = LandingFilter.ANY

    @field_validator("region", mode="before")
    @classmethod
    def _region(cls, v):
        text = n.clean_text(v, 200)
        if not text or len(text) < 2:
            raise ValueError("Informe a cidade ou região (mínimo de 2 caracteres).")
        return text

    @field_validator("state", mode="before")
    @classmethod
    def _state(cls, v):
        return n.normalize_state(v)

    @field_validator("segments", mode="before")
    @classmethod
    def _segments(cls, v):
        if not isinstance(v, list):
            raise ValueError("Informe a lista de segmentos.")
        cleaned: list[str] = []
        for item in v:
            text = n.clean_text(item, 120, "Segmento")
            if text and text.casefold() not in {c.casefold() for c in cleaned}:
                cleaned.append(text)
        if not cleaned:
            raise ValueError("Selecione ao menos um segmento.")
        return cleaned


class ProspectingStatus(BaseModel):
    available: bool
    provider: str | None = None
    message: str
