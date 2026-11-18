"""Agregações para o dashboard e para os relatórios (sempre sobre dados reais do banco)."""
import asyncio
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.supabase import Database, Filter
from app.models.enums import PIPELINE_ORDER, LeadStatus, Priority
from app.services.activity_service import ActivityService

NO_SEGMENT = "Sem segmento"
NO_STATE = "Não informado"


def _local_date(iso: str, tz: ZoneInfo) -> date:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(tz).date()


def _pct(part: int, whole: int) -> float:
    return round(part * 100 / whole, 1) if whole else 0.0


def _totals(rows: list[dict]) -> dict:
    by_status = Counter(r["status"] for r in rows)
    return {
        "total": len(rows),
        **{s.value: by_status.get(s.value, 0) for s in PIPELINE_ORDER},
        "high_priority": sum(1 for r in rows if r["priority"] == Priority.HIGH.value),
    }


def _ranked(rows: list[dict], key: str, empty_label: str, limit: int) -> list[tuple[str, int]]:
    counts = Counter((r.get(key) or empty_label) for r in rows)
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].casefold()))[:limit]


def _bucket_start(d: date, granularity: str) -> date:
    if granularity == "week":
        return d - timedelta(days=d.weekday())  # segunda-feira
    if granularity == "month":
        return d.replace(day=1)
    return d


def _next_bucket(d: date, granularity: str) -> date:
    if granularity == "week":
        return d + timedelta(days=7)
    if granularity == "month":
        return date(d.year + (d.month == 12), (d.month % 12) + 1, 1)
    return d + timedelta(days=1)


def series(rows: list[dict], tz: ZoneInfo, start: date, end: date, granularity: str) -> list[dict]:
    """Contagem de leads por dia/semana/mês, preenchendo com zero os períodos vazios."""
    counts: Counter[date] = Counter()
    for r in rows:
        counts[_bucket_start(_local_date(r["created_at"], tz), granularity)] += 1
    out, cursor = [], _bucket_start(start, granularity)
    while cursor <= end:
        out.append({"date": cursor.isoformat(), "count": counts.get(cursor, 0)})
        cursor = _next_bucket(cursor, granularity)
    return out


def period_start(days: int, tz: ZoneInfo) -> tuple[date, datetime]:
    """Primeiro dia (local) do período e o instante UTC correspondente à meia-noite dele."""
    start = datetime.now(tz).date() - timedelta(days=days - 1)
    start_utc = datetime(start.year, start.month, start.day, tzinfo=tz).astimezone(timezone.utc)
    return start, start_utc


class AnalyticsService:
    def __init__(self, db: Database, owner_id: str, tz: ZoneInfo):
        self.db = db
        self.owner_id = owner_id
        self.tz = tz

    # ---------------------------------------------------------------- dashboard
    async def dashboard(self, days: int) -> dict:
        start, _ = period_start(days, self.tz)
        all_rows, latest, activities = await asyncio.gather(
            self.db.select_all("leads", columns="id,status,priority,segment,created_at"),
            self.db.select("leads", order="created_at.desc", limit=8),
            ActivityService(self.db, self.owner_id).recent(10),
        )
        totals = _totals(all_rows)
        return {
            "period_days": days,
            "totals": totals,
            "conversion_rate": _pct(totals["closed_won"], totals["total"]),
            # leads fora do intervalo são ignorados pela série (que só emite os dias do período)
            "leads_by_period": series(all_rows, self.tz, start, datetime.now(self.tz).date(), "day"),
            "leads_by_segment": [{"segment": s, "count": c} for s, c in _ranked(all_rows, "segment", NO_SEGMENT, 8)],
            "recent_activities": activities,
            "latest_leads": latest[0],
        }

    # ---------------------------------------------------------------- relatórios
    async def report(self, days: int) -> dict:
        today = datetime.now(self.tz).date()
        filters: list[Filter] = []
        start = None
        if days > 0:
            start, start_utc = period_start(days, self.tz)
            filters.append(("created_at", f"gte.{start_utc.isoformat()}"))

        rows, history = await asyncio.gather(
            self.db.select_all("leads", columns="id,status,priority,segment,state,created_at", filters=filters),
            self.db.select("prospecting_searches", order="created_at.desc", limit=10),
        )
        closed, _ = await self.db.select(
            "leads", filters=[*filters, ("status", f"eq.{LeadStatus.CLOSED_WON.value}")], order="status_updated_at.desc", limit=20
        )

        if days == 0:
            granularity = "month"
            start = min((_local_date(r["created_at"], self.tz) for r in rows), default=today)
        else:
            granularity = "day" if days <= 31 else "week" if days <= 120 else "month"

        totals = _totals(rows)
        decided = totals["closed_won"] + totals["lost"]
        return {
            "period_days": days,
            "granularity": granularity,
            "total_in_period": totals["total"],
            "leads_by_period": series(rows, self.tz, start, today, granularity) if (rows or days > 0) else [],
            "leads_by_segment": [{"segment": s, "count": c} for s, c in _ranked(rows, "segment", NO_SEGMENT, 10)],
            "leads_by_region": [{"state": s, "count": c} for s, c in _ranked(rows, "state", NO_STATE, 10)],
            "funnel": [{"status": s.value, "count": totals[s.value]} for s in PIPELINE_ORDER],
            "conversion": {
                "total": totals["total"],
                "closed_won": totals["closed_won"],
                "lost": totals["lost"],
                "conversion_rate": _pct(totals["closed_won"], totals["total"]),
                "win_rate": _pct(totals["closed_won"], decided) if decided else None,
            },
            "closed_clients": closed,
            "prospecting_history": history[0],
        }
