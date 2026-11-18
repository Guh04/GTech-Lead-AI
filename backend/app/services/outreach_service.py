"""Fila de abordagem por WhatsApp.

Fluxo: a IA gera rascunhos -> o usuário revisa/edita e APROVA -> o usuário clica em enviar (o sistema registra,
aplica o limite diário e abre o WhatsApp com o texto pronto). Nada é enviado sem uma ação explícita do usuário.
"""
import logging
import math
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx

from app.core.config import Settings
from app.core.errors import AppError, not_found
from app.core.supabase import Database
from app.models.enums import ActivityType, LeadStatus, OutreachStatus
from app.schemas.outreach import OutreachStatusOut
from app.services import ai_message
from app.services.lead_service import LeadService

log = logging.getLogger("gtech.outreach")

LEAD_EMBED = "*,lead:leads(company_name,segment,city,state,whatsapp,do_not_contact,status)"
OPEN = f"({OutreachStatus.DRAFT.value},{OutreachStatus.APPROVED.value})"


def whatsapp_url(digits: str, text: str) -> str:
    d = "".join(c for c in digits if c.isdigit())
    if len(d) in (10, 11):
        d = f"55{d}"
    return f"https://wa.me/{d}?text={quote(text)}"


class OutreachService:
    def __init__(self, db: Database, owner_id: str, settings: Settings, http: httpx.AsyncClient, tz: ZoneInfo):
        self.db = db
        self.owner_id = owner_id
        self.settings = settings
        self.http = http
        self.tz = tz
        self.leads = LeadService(db, owner_id)

    # ------------------------------------------------------------------ limites
    def _start_of_today(self) -> str:
        now = datetime.now(self.tz)
        return now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc).isoformat()

    async def status(self) -> OutreachStatusOut:
        rows, total = await self.db.select(
            "outreach_messages",
            columns="sent_at",
            filters=[("status", f"eq.{OutreachStatus.SENT.value}"), ("sent_at", f"gte.{self._start_of_today()}")],
            order="sent_at.desc",
            limit=1,
            count=True,
        )
        sent = total if total is not None else len(rows)
        limit = self.settings.outreach_daily_limit
        wait = 0
        if rows and rows[0].get("sent_at"):
            last = datetime.fromisoformat(rows[0]["sent_at"].replace("Z", "+00:00"))
            ready = last + timedelta(seconds=self.settings.outreach_min_interval_seconds)
            wait = max(0, math.ceil((ready - datetime.now(timezone.utc)).total_seconds()))
        return OutreachStatusOut(
            daily_limit=limit,
            sent_today=sent,
            remaining=max(0, limit - sent),
            min_interval_seconds=self.settings.outreach_min_interval_seconds,
            wait_seconds=wait,
            ai_configured=bool(self.settings.anthropic_api_key.strip()),
        )

    # ------------------------------------------------------------------ leitura
    async def list(self, status: OutreachStatus | None, limit: int = 100) -> list[dict]:
        filters = [("status", f"eq.{status.value}")] if status else []
        rows, _ = await self.db.select(
            "outreach_messages", columns=LEAD_EMBED, filters=filters, order="created_at.desc", limit=limit
        )
        return rows

    async def counts(self) -> dict[str, int]:
        rows = await self.db.select_all("outreach_messages", columns="status")
        out = {s.value: 0 for s in OutreachStatus}
        for r in rows:
            out[r["status"]] = out.get(r["status"], 0) + 1
        return out

    async def _get(self, message_id: str) -> dict:
        rows, _ = await self.db.select("outreach_messages", filters=[("id", f"eq.{message_id}")], limit=1)
        if not rows:
            raise not_found("Mensagem")
        return rows[0]

    # ------------------------------------------------------------------ geração
    async def generate(self, count: int, search_id: str | None = None) -> dict:
        st = await self.status()
        _, open_count = await self.db.select(
            "outreach_messages", columns="id", filters=[("status", f"in.{OPEN}")], limit=1, count=True
        )
        room = st.remaining - (open_count or 0)
        if st.remaining <= 0:
            raise AppError(409, "daily_limit_reached", f"O limite diário de {st.daily_limit} mensagens já foi atingido. Continue amanhã para proteger seu número.")
        if room <= 0:
            raise AppError(409, "queue_full", "Você já tem mensagens pendentes suficientes para o limite de hoje. Aprove, envie ou descarte as pendentes antes de gerar mais.")
        count = min(count, room)

        already = {r["lead_id"] for r in await self.db.select_all("outreach_messages", columns="lead_id")}
        filters = [
            ("whatsapp", "not.is.null"),
            ("do_not_contact", "eq.false"),
            ("status", f"in.({LeadStatus.NEW.value},{LeadStatus.ANALYZED.value})"),
        ]
        if search_id:
            filters.append(("prospecting_search_id", f"eq.{search_id}"))
        candidates, _ = await self.db.select(
            "leads", filters=filters, order="score.desc,created_at.desc", limit=min(count + len(already), 1000)
        )
        candidates = [c for c in candidates if c["id"] not in already][:count]

        created = []
        for lead in candidates:
            body, source = await ai_message.compose(self.settings, self.http, lead)
            try:
                row = await self.db.insert(
                    "outreach_messages",
                    {"owner_id": self.owner_id, "lead_id": lead["id"], "body": body, "status": OutreachStatus.DRAFT.value, "source": source},
                )
            except AppError as exc:
                if exc.status == 409:  # corrida: já existe pendente para este lead
                    continue
                raise
            await self.leads.activities.log(
                lead["id"], ActivityType.MESSAGE_PREPARED,
                "Mensagem de WhatsApp preparada" + (" pela IA." if source == "ai" else " (texto-modelo)."),
                {"outreach_id": row["id"], "source": source},
            )
            created.append(row)
        return {"created": len(created), "requested": count, "items": created}

    # ------------------------------------------------------------------ ações do usuário
    async def edit(self, message_id: str, body: str) -> dict:
        msg = await self._get(message_id)
        if msg["status"] not in (OutreachStatus.DRAFT.value, OutreachStatus.APPROVED.value):
            raise AppError(409, "not_editable", "Só é possível editar mensagens pendentes.")
        # Editar uma mensagem aprovada exige nova aprovação.
        rows = await self.db.update(
            "outreach_messages",
            {"body": body, "status": OutreachStatus.DRAFT.value, "approved_at": None},
            [("id", f"eq.{message_id}"), ("status", f"in.{OPEN}")],
        )
        if not rows:
            raise AppError(409, "not_editable", "Só é possível editar mensagens pendentes.")
        return rows[0]

    async def approve(self, message_id: str) -> dict:
        msg = await self._get(message_id)
        if msg["status"] != OutreachStatus.DRAFT.value:
            raise AppError(409, "not_draft", "Só é possível aprovar mensagens em rascunho.")
        rows = await self.db.update(
            "outreach_messages",
            {"status": OutreachStatus.APPROVED.value, "approved_at": datetime.now(timezone.utc).isoformat()},
            [("id", f"eq.{message_id}"), ("status", f"eq.{OutreachStatus.DRAFT.value}")],
        )
        if not rows:
            raise AppError(409, "not_draft", "Só é possível aprovar mensagens em rascunho.")
        return rows[0]

    async def skip(self, message_id: str) -> dict:
        msg = await self._get(message_id)
        if msg["status"] not in (OutreachStatus.DRAFT.value, OutreachStatus.APPROVED.value):
            raise AppError(409, "not_skippable", "Só é possível descartar mensagens pendentes.")
        rows = await self.db.update(
            "outreach_messages", {"status": OutreachStatus.SKIPPED.value}, [("id", f"eq.{message_id}"), ("status", f"in.{OPEN}")]
        )
        if not rows:
            raise AppError(409, "not_skippable", "Só é possível descartar mensagens pendentes.")
        return rows[0]

    async def quick_send(self, lead_id: str) -> dict:
        """Atalho de 1 clique: prepara a mensagem (ou usa a pendente do lead), aprova e registra o envio.

        A ação do usuário (clicar em "Chamar") é a aprovação. O limite diário e o intervalo mínimo valem igual.
        """
        lead = await self.leads.get(lead_id)
        if lead.get("do_not_contact"):
            raise AppError(409, "do_not_contact", "Este lead pediu para não ser contatado.")
        if not lead.get("whatsapp"):
            raise AppError(409, "no_whatsapp", "Este lead não tem WhatsApp cadastrado.")
        st = await self.status()  # confere o limite ANTES de gastar uma chamada de IA
        if st.remaining <= 0:
            raise AppError(429, "daily_limit_reached", f"Limite diário de {st.daily_limit} mensagens atingido. Continue amanhã para proteger seu número.")
        if st.wait_seconds > 0:
            raise AppError(429, "too_soon", f"Aguarde {st.wait_seconds}s antes do próximo envio para evitar bloqueios.")

        pending, _ = await self.db.select(
            "outreach_messages", filters=[("lead_id", f"eq.{lead_id}"), ("status", f"in.{OPEN}")], limit=1
        )
        if pending:
            message_id = pending[0]["id"]
            if pending[0]["status"] == OutreachStatus.DRAFT.value:
                await self.approve(message_id)
        else:
            body, source = await ai_message.compose(self.settings, self.http, lead)
            row = await self.db.insert(
                "outreach_messages",
                {
                    "owner_id": self.owner_id, "lead_id": lead_id, "body": body, "source": source,
                    "status": OutreachStatus.APPROVED.value, "approved_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            message_id = row["id"]
        return await self.send(message_id)

    async def send(self, message_id: str) -> dict:
        """Registra o envio (limite diário + intervalo) e devolve o link do WhatsApp com o texto pronto."""
        msg = await self._get(message_id)
        if msg["status"] == OutreachStatus.SENT.value:
            raise AppError(409, "already_sent", "Esta mensagem já foi enviada.")
        if msg["status"] != OutreachStatus.APPROVED.value:
            raise AppError(409, "not_approved", "Aprove a mensagem antes de enviar.")

        lead = await self.leads.get(msg["lead_id"])
        if lead.get("do_not_contact"):
            raise AppError(409, "do_not_contact", "Este lead pediu para não ser contatado.")
        if not lead.get("whatsapp"):
            raise AppError(409, "no_whatsapp", "Este lead não tem WhatsApp cadastrado.")

        st = await self.status()
        if st.remaining <= 0:
            raise AppError(429, "daily_limit_reached", f"Limite diário de {st.daily_limit} mensagens atingido. Continue amanhã para proteger seu número.")
        if st.wait_seconds > 0:
            raise AppError(429, "too_soon", f"Aguarde {st.wait_seconds}s antes do próximo envio para evitar bloqueios.")

        rows = await self.db.update(
            "outreach_messages",
            {"status": OutreachStatus.SENT.value, "sent_at": datetime.now(timezone.utc).isoformat()},
            [("id", f"eq.{message_id}"), ("status", f"eq.{OutreachStatus.APPROVED.value}")],
        )
        if not rows:
            raise AppError(409, "already_sent", "Esta mensagem já foi enviada.")
        if lead["status"] in (LeadStatus.NEW.value, LeadStatus.ANALYZED.value):
            await self.leads.move_status(lead["id"], LeadStatus.CONTACTED)
        await self.leads.activities.log(
            lead["id"], ActivityType.MESSAGE_PREPARED, "Mensagem de WhatsApp enviada (aberta pelo usuário).", {"outreach_id": message_id}
        )
        return {"message": rows[0], "whatsapp_url": whatsapp_url(lead["whatsapp"], msg["body"]), "status": (await self.status()).model_dump()}
