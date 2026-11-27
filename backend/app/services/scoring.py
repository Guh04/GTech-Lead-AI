"""Pontuação comercial (0-100) por regras transparentes: site (score) e marketing (marketing_score).

O objetivo comercial é vender landing pages. Quanto MENOS presença de conversão
a empresa tem e quanto MAIS formas de contato/atividade digital ela possui,
maior o potencial. Esta classe de regras é o ponto de extensão onde, no futuro,
um modelo de IA pode substituir ou complementar o cálculo (score_source = 'ai').

Critérios (somados, máximo 100):
  Landing page    : sem site 45 | site sem landing 30 | não verificado 15 | com landing 0
  Contato direto  : WhatsApp 20  (ou, sem WhatsApp, telefone 10)
  Redes sociais   : Instagram 10 | Facebook 5
  Responsável     : identificado 5
  "Não contatar"  : pontuação zero

Prioridade: >= 70 alta | 40-69 média | < 40 baixa.
"""
from app.models.enums import LandingStatus, Priority

THRESHOLD_HIGH = 70
THRESHOLD_MEDIUM = 40

_LANDING_POINTS = {
    LandingStatus.NONE.value: 45,
    LandingStatus.SITE_ONLY.value: 30,
    LandingStatus.UNKNOWN.value: 15,
    LandingStatus.HAS_LANDING.value: 0,
}


def compute_score(lead: dict) -> int:
    if lead.get("do_not_contact"):
        return 0
    score = _LANDING_POINTS.get(str(lead.get("landing_page_status") or "unknown"), 15)
    if lead.get("whatsapp"):
        score += 20
    elif lead.get("phone"):
        score += 10
    if lead.get("instagram"):
        score += 10
    if lead.get("facebook"):
        score += 5
    if lead.get("contact_name"):
        score += 5
    return max(0, min(100, score))


# ----------------------------------------------------------------------------- marketing
# Necessidade de marketing (0-100), a partir da avaliação MANUAL do Instagram.
# Quanto mais parado/fraco o perfil, maior a necessidade. None = ainda não avaliado.
#
#   Sem Instagram                  : 70 (não tem presença para trabalhar)
#   Último post   : nenhum 50 | +3 meses 45 | até 3 meses 30 | até 30 dias 10 | 7 dias 0 | ? 15
#   Engajamento   : nenhum 25 | baixo 15 | bom 0 | ? 8
#   Perfil        : amador 20 | profissional 0 | ? 7
#   Seguidores    : < 500 +10 | < 2000 +5   (só se informado)
#
# Precisa de marketing: >= 50.  Precisa de site: sem site ou site sem landing page.
MARKETING_THRESHOLD = 50
NO_INSTAGRAM_SCORE = 70
SITE_NEED_STATUSES = (LandingStatus.NONE.value, LandingStatus.SITE_ONLY.value)

_LAST_POST_POINTS = {"none": 50, "older": 45, "quarter": 30, "month": 10, "week": 0, "unknown": 15}
_ENGAGEMENT_POINTS = {"none": 25, "low": 15, "good": 0, "unknown": 8}
_QUALITY_POINTS = {"amateur": 20, "professional": 0, "unknown": 7}
IG_FIELDS = ("ig_last_post", "ig_engagement", "ig_quality", "ig_followers")


def instagram_evaluated(lead: dict) -> bool:
    return any(str(lead.get(k) or "unknown") != "unknown" for k in IG_FIELDS[:3]) or lead.get("ig_followers") is not None


def compute_marketing_score(lead: dict) -> int | None:
    if not lead.get("instagram"):
        return NO_INSTAGRAM_SCORE
    if not instagram_evaluated(lead):
        return None
    score = (
        _LAST_POST_POINTS.get(str(lead.get("ig_last_post") or "unknown"), 15)
        + _ENGAGEMENT_POINTS.get(str(lead.get("ig_engagement") or "unknown"), 8)
        + _QUALITY_POINTS.get(str(lead.get("ig_quality") or "unknown"), 7)
    )
    followers = lead.get("ig_followers")
    if followers is not None:
        score += 10 if followers < 500 else 5 if followers < 2000 else 0
    return max(0, min(100, score))


def priority_for(score: int) -> Priority:
    if score >= THRESHOLD_HIGH:
        return Priority.HIGH
    if score >= THRESHOLD_MEDIUM:
        return Priority.MEDIUM
    return Priority.LOW
