"""Domínio: valores permitidos (espelham os CHECKs de database/schema.sql)."""
from enum import StrEnum


class LeadStatus(StrEnum):
    NEW = "new"
    ANALYZED = "analyzed"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    PROPOSAL_SENT = "proposal_sent"
    CLOSED_WON = "closed_won"
    LOST = "lost"


# Ordem do funil comercial
PIPELINE_ORDER = list(LeadStatus)

STATUS_LABELS = {
    LeadStatus.NEW: "Novo lead",
    LeadStatus.ANALYZED: "Analisado",
    LeadStatus.CONTACTED: "Contato realizado",
    LeadStatus.INTERESTED: "Interessado",
    LeadStatus.PROPOSAL_SENT: "Proposta enviada",
    LeadStatus.CLOSED_WON: "Cliente fechado",
    LeadStatus.LOST: "Perdido",
}

# Estágios que encerram a negociação (não aparecem em "Oportunidades")
CLOSED_STATUSES = (LeadStatus.CLOSED_WON, LeadStatus.LOST)


class Priority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class LandingStatus(StrEnum):
    NONE = "none"  # sem site nem landing page
    SITE_ONLY = "site_only"  # tem site, mas não tem landing page
    HAS_LANDING = "has_landing"
    UNKNOWN = "unknown"


class LeadSource(StrEnum):
    MANUAL = "manual"
    AI_AGENT = "ai_agent"
    GOOGLE_MAPS = "google_maps"
    IMPORT = "import"
    OTHER = "other"


class ScoreSource(StrEnum):
    RULES = "rules"
    MANUAL = "manual"
    AI = "ai"


class ActivityType(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    STATUS_CHANGED = "status_changed"
    NOTE = "note"
    AI_ANALYSIS = "ai_analysis"
    MESSAGE_PREPARED = "message_prepared"


class SearchStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class OutreachStatus(StrEnum):
    DRAFT = "draft"  # gerada pela IA, aguardando aprovação
    APPROVED = "approved"  # aprovada pelo usuário, pronta para enviar
    SENT = "sent"  # o usuário abriu o WhatsApp e enviou
    SKIPPED = "skipped"  # descartada


class WebsiteFilter(StrEnum):
    ANY = "any"
    WITH_SITE = "with_site"
    WITHOUT_SITE = "without_site"


class LandingFilter(StrEnum):
    ANY = "any"
    NONE = "none"
    SITE_ONLY = "site_only"
    HAS_LANDING = "has_landing"
    UNKNOWN = "unknown"


UF_LIST = (
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO"
).split()
