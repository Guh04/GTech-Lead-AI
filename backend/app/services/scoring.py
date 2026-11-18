"""Pontuação comercial (0-100) por regras transparentes.

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


def priority_for(score: int) -> Priority:
    if score >= THRESHOLD_HIGH:
        return Priority.HIGH
    if score >= THRESHOLD_MEDIUM:
        return Priority.MEDIUM
    return Priority.LOW
