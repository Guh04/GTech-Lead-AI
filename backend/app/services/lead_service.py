"""Regras de negócio de leads: CRUD, filtros, pontuação, histórico e exportação."""
import csv
import io
import re
from collections import Counter
from dataclasses import dataclass

from app.core.errors import not_found
from app.core.supabase import Database, Filter
from app.models.enums import (
    CLOSED_STATUSES,
    STATUS_LABELS,
    ActivityType,
    LandingStatus,
    LeadSource,
    LeadStatus,
    Priority,
    ScoreSource,
)
from app.schemas.lead import LeadCreate, LeadUpdate
from app.services import scoring
from app.services.activity_service import ActivityService

SORTS = {
    "created_desc": "created_at.desc",
    "created_asc": "created_at.asc",
    "score_desc": "score.desc,created_at.desc",
    "score_asc": "score.asc,created_at.desc",
    "name_asc": "company_name.asc",
}

# Campos que nunca podem ser gravados como NULL
_NOT_NULLABLE = {"landing_page_status", "status", "source", "do_not_contact"}
# Campos que, ao mudar, devem aparecer no histórico como "atualização"
_FIELD_LABELS = {
    "company_name": "nome", "contact_name": "responsável", "segment": "segmento", "city": "cidade",
    "state": "estado", "phone": "telefone", "whatsapp": "WhatsApp", "instagram": "Instagram",
    "facebook": "Facebook", "website": "site", "landing_page_status": "landing page", "score": "pontuação",
    "source": "origem", "source_url": "fonte", "notes": "observações", "do_not_contact": "não contatar",
}


@dataclass
class LeadFilters:
    search: str | None = None
    segment: str | None = None
    city: str | None = None
    state: str | None = None
    priority: Priority | None = None
    status: LeadStatus | None = None
    landing_status: LandingStatus | None = None
    source: LeadSource | None = None
    active: bool = False
    search_id: str | None = None
    sort: str = "created_desc"


def _search_term(term: str) -> str:
    """Remove caracteres com significado especial no filtro 'or' do PostgREST / ILIKE."""
    return re.sub(r'[%_*,()"\\]', " ", term).strip()


def build_filters(f: LeadFilters) -> list[Filter]:
    out: list[Filter] = []
    if f.search:
        term = _search_term(f.search)
        if term:
            # valores entre aspas: pontos e dois-pontos no termo não confundem o parser do PostgREST
            out.append(("or", f'(company_name.ilike."*{term}*",contact_name.ilike."*{term}*")'))
    if f.segment:
        out.append(("segment", f"eq.{f.segment}"))
    if f.city:
        out.append(("city", f"eq.{f.city}"))
    if f.state:
        out.append(("state", f"eq.{f.state}"))
    if f.priority:
        out.append(("priority", f"eq.{f.priority.value}"))
    if f.status:
        out.append(("status", f"eq.{f.status.value}"))
    if f.landing_status:
        out.append(("landing_page_status", f"eq.{f.landing_status.value}"))
    if f.source:
        out.append(("source", f"eq.{f.source.value}"))
    if f.active:
        closed = ",".join(s.value for s in CLOSED_STATUSES)
        out.append(("status", f"not.in.({closed})"))
    if f.search_id:
        out.append(("prospecting_search_id", f"eq.{f.search_id}"))
    return out


def _safe_csv(value) -> str:
    """Evita injeção de fórmulas ao abrir o CSV no Excel/Sheets."""
    text = "" if value is None else str(value)
    if text[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


CSV_COLUMNS = [
    ("company_name", "Empresa"), ("contact_name", "Responsável"), ("segment", "Segmento"), ("city", "Cidade"),
    ("state", "Estado"), ("phone", "Telefone"), ("whatsapp", "WhatsApp"), ("instagram", "Instagram"),
    ("facebook", "Facebook"), ("website", "Site"), ("landing_page_status", "Landing page"),
    ("priority", "Prioridade"), ("score", "Pontuação"), ("status", "Estágio"), ("source", "Origem"),
    ("source_url", "Fonte pública"), ("do_not_contact", "Não contatar"), ("created_at", "Cadastrado em"), ("notes", "Observações"),
]
_CSV_VALUE_LABELS = {
    "landing_page_status": {"none": "Sem site", "site_only": "Site sem landing", "has_landing": "Com landing page", "unknown": "Não verificado"},
    "priority": {"high": "Alta", "medium": "Média", "low": "Baixa"},
    "status": {s.value: label for s, label in STATUS_LABELS.items()},
    "source": {"manual": "Cadastro manual", "ai_agent": "Agente de IA", "google_maps": "Google Maps", "import": "Importação", "other": "Outra"},
}


class LeadService:
    def __init__(self, db: Database, owner_id: str):
        self.db = db
        self.owner_id = owner_id
        self.activities = ActivityService(db, owner_id)

    # ------------------------------------------------------------------ leitura
    async def list(self, f: LeadFilters, page: int, page_size: int) -> dict:
        rows, total = await self.db.select(
            "leads",
            filters=build_filters(f),
            order=SORTS.get(f.sort, SORTS["created_desc"]),
            limit=page_size,
            offset=(page - 1) * page_size,
            count=True,
        )
        return {"items": rows, "total": total if total is not None else len(rows), "page": page, "page_size": page_size}

    async def get(self, lead_id: str) -> dict:
        rows, _ = await self.db.select("leads", filters=[("id", f"eq.{lead_id}")], limit=1)
        if not rows:
            raise not_found("Lead")
        return rows[0]

    async def facets(self) -> dict:
        rows = await self.db.select_all("leads", columns="segment,city,state,priority,status")
        active = [r for r in rows if r["status"] not in {s.value for s in CLOSED_STATUSES}]
        pc = Counter(r["priority"] for r in active)
        sc = Counter(r["status"] for r in rows)

        def distinct(key: str) -> list[str]:
            return sorted({r[key] for r in rows if r.get(key)}, key=str.casefold)

        return {
            "segments": distinct("segment"),
            "cities": distinct("city"),
            "states": distinct("state"),
            "priority_counts": {p.value: pc.get(p.value, 0) for p in Priority},
            "priority_thresholds": {"high": scoring.THRESHOLD_HIGH, "medium": scoring.THRESHOLD_MEDIUM},
            "status_counts": {s.value: sc.get(s.value, 0) for s in LeadStatus},
        }

    async def export_csv(self, f: LeadFilters) -> str:
        rows = await self.db.select_all(
            "leads", filters=build_filters(f), order=SORTS.get(f.sort, SORTS["created_desc"]), max_rows=20_000
        )
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
        writer.writerow([label for _, label in CSV_COLUMNS])
        for r in rows:
            line = []
            for key, _ in CSV_COLUMNS:
                value = r.get(key)
                if key in _CSV_VALUE_LABELS:
                    value = _CSV_VALUE_LABELS[key].get(value, value)
                elif key == "do_not_contact":
                    value = "Sim" if value else "Não"
                elif key == "created_at" and value:
                    value = str(value)[:10]
                line.append(_safe_csv(value))
            writer.writerow(line)
        return buf.getvalue()

    # ------------------------------------------------------------------ escrita
    def _apply_scoring(self, data: dict, explicit_score: bool, manual_score: int | None) -> None:
        """Define score, score_source e priority em `data` (dados completos do lead)."""
        if explicit_score and manual_score is not None:
            data["score"], data["score_source"] = manual_score, ScoreSource.MANUAL.value
        else:
            data["score"], data["score_source"] = scoring.compute_score(data), ScoreSource.RULES.value
        data["priority"] = scoring.priority_for(data["score"]).value

    async def create(self, payload: LeadCreate, *, search_id: str | None = None) -> dict:
        data = payload.model_dump(mode="json")
        manual = data.pop("score")
        self._apply_scoring(data, True, manual)
        data["owner_id"] = self.owner_id
        if search_id:
            data["prospecting_search_id"] = search_id
        lead = await self.db.insert("leads", data)
        origin = "pelo agente de IA" if lead.get("source") == LeadSource.AI_AGENT.value else "manualmente"
        await self.activities.log(
            lead["id"], ActivityType.CREATED, f"Lead cadastrado {origin} (pontuação {lead['score']}).",
            {"score": lead["score"], "source": lead.get("source")},
        )
        return lead

    async def update(self, lead_id: str, payload: LeadUpdate) -> dict:
        existing = await self.get(lead_id)
        changes = payload.model_dump(mode="json", exclude_unset=True)
        for key in list(changes):
            if changes[key] is None and key in _NOT_NULLABLE:
                del changes[key]

        merged = {**existing, **changes}
        score_given = "score" in changes
        manual = changes.pop("score", None)
        if score_given or existing.get("score_source") == ScoreSource.RULES.value:
            self._apply_scoring(merged, score_given, manual)
        else:  # pontuação manual/IA preservada; só a prioridade acompanha
            merged["priority"] = scoring.priority_for(int(existing["score"])).value
        for key in ("score", "score_source", "priority"):
            changes[key] = merged[key]

        rows = await self.db.update("leads", changes, [("id", f"eq.{lead_id}")])
        if not rows:
            raise not_found("Lead")
        lead = rows[0]

        if lead["status"] != existing["status"]:
            await self._log_status_change(lead_id, existing["status"], lead["status"])
        changed = [_FIELD_LABELS[k] for k in _FIELD_LABELS if k in payload.model_fields_set and existing.get(k) != lead.get(k)]
        if changed:
            await self.activities.log(lead_id, ActivityType.UPDATED, f"Dados atualizados: {', '.join(changed)}.", {"fields": changed})
        return lead

    async def _log_status_change(self, lead_id: str, old: str, new: str) -> None:
        await self.activities.log(
            lead_id,
            ActivityType.STATUS_CHANGED,
            f"Estágio alterado de “{STATUS_LABELS[LeadStatus(old)]}” para “{STATUS_LABELS[LeadStatus(new)]}”.",
            {"from": old, "to": new},
        )

    async def move_status(self, lead_id: str, status: LeadStatus) -> dict:
        existing = await self.get(lead_id)
        if existing["status"] == status.value:
            return existing
        rows = await self.db.update("leads", {"status": status.value}, [("id", f"eq.{lead_id}")])
        if not rows:
            raise not_found("Lead")
        await self._log_status_change(lead_id, existing["status"], status.value)
        return rows[0]

    async def delete(self, lead_id: str) -> None:
        rows = await self.db.delete("leads", [("id", f"eq.{lead_id}")])
        if not rows:
            raise not_found("Lead")

    async def add_note(self, lead_id: str, text: str) -> dict:
        await self.get(lead_id)  # garante que existe e pertence ao usuário
        return await self.db.insert(
            "lead_activities",
            {"lead_id": lead_id, "owner_id": self.owner_id, "type": ActivityType.NOTE.value, "description": text, "metadata": {}},
        )
