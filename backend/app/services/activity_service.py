"""Registro e consulta do histórico (lead_activities)."""
import logging

from app.core.errors import AppError
from app.core.supabase import Database
from app.models.enums import ActivityType

log = logging.getLogger("gtech.activities")


class ActivityService:
    def __init__(self, db: Database, owner_id: str):
        self.db = db
        self.owner_id = owner_id

    async def log(self, lead_id: str, type_: ActivityType, description: str, metadata: dict | None = None) -> None:
        """Grava um evento. Falhas aqui nunca derrubam a operação principal."""
        try:
            await self.db.insert(
                "lead_activities",
                {
                    "lead_id": lead_id,
                    "owner_id": self.owner_id,
                    "type": type_.value,
                    "description": description,
                    "metadata": metadata or {},
                },
            )
        except AppError as exc:
            log.warning("Não foi possível registrar atividade (%s): %s", type_.value, exc.message)

    async def for_lead(self, lead_id: str, limit: int = 100) -> list[dict]:
        rows, _ = await self.db.select(
            "lead_activities",
            filters=[("lead_id", f"eq.{lead_id}")],
            order="created_at.desc",
            limit=limit,
        )
        return rows

    async def recent(self, limit: int = 10) -> list[dict]:
        rows, _ = await self.db.select(
            "lead_activities",
            columns="id,lead_id,type,description,metadata,created_at,lead:leads(company_name)",
            order="created_at.desc",
            limit=limit,
        )
        for row in rows:
            lead = row.pop("lead", None) or {}
            row["lead_name"] = lead.get("company_name")
        return rows
