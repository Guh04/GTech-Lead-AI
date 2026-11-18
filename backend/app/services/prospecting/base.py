"""Contrato de um provedor de prospecção (o futuro agente de IA).

Qualquer implementação (API própria, Google Places, buscador + análise de sites,
modelo de IA...) só precisa cumprir esta interface. O restante do sistema
(gravação dos leads, deduplicação, histórico, pontuação) já está pronto e
independe de como a busca é feita.

Ideias de provedores futuros (NÃO implementados nesta versão):
  - Google Maps / Places API para localizar empresas por região e segmento
  - Análise automática de sites (detectar ausência de landing page)
  - Classificação de leads por IA (score_source = 'ai')
  - Geração de abordagens comerciais (sempre com aprovação do usuário)
"""
from typing import Protocol

from app.schemas.prospecting import SearchRequest


class ProspectingError(Exception):
    """Falha ao executar a busca (mensagem pode ser exibida ao usuário)."""


class ProspectingProvider(Protocol):
    name: str

    async def search(self, query: SearchRequest) -> list[dict]:
        """Retorna empresas encontradas. Cada item usa os campos de LeadCreate:
        company_name (obrigatório), contact_name, segment, city, state, phone, whatsapp,
        instagram, facebook, website, landing_page_status, source_url, notes.
        """
        ...
