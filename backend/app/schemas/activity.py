from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ActivityType
from app.schemas.normalize import clean_multiline


class ActivityOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    lead_id: UUID
    type: ActivityType
    description: str
    metadata: dict = Field(default_factory=dict)
    created_at: datetime


class RecentActivityOut(ActivityOut):
    lead_name: str | None = None


class NoteCreate(BaseModel):
    description: str

    @field_validator("description", mode="before")
    @classmethod
    def _clean(cls, v):
        text = clean_multiline(v, 2000)
        if not text:
            raise ValueError("Escreva o texto da anotação.")
        return text
