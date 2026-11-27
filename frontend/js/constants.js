// Constantes de domínio compartilhadas pelo frontend.
// Os valores (keys) precisam ser idênticos aos aceitos pelo backend/banco.

/** Estágios do pipeline, na ordem comercial. */
export const STATUSES = [
  { key: 'new', label: 'Novo lead', tone: 'slate', color: '#64748b', icon: 'sparkles' },
  { key: 'analyzed', label: 'Analisado', tone: 'violet', color: '#8b7df0', icon: 'search-check' },
  { key: 'contacted', label: 'Contato realizado', tone: 'blue', color: '#3b82f6', icon: 'phone-call' },
  { key: 'interested', label: 'Interessado', tone: 'cyan', color: '#22b8cf', icon: 'thumbs-up' },
  { key: 'proposal_sent', label: 'Proposta enviada', tone: 'yellow', color: '#f59e0b', icon: 'file-text' },
  { key: 'closed_won', label: 'Cliente fechado', tone: 'green', color: '#22c55e', icon: 'badge-check' },
  { key: 'lost', label: 'Perdido', tone: 'red', color: '#ef4444', icon: 'circle-x' },
];
export const STATUS_BY_KEY = Object.fromEntries(STATUSES.map((s) => [s.key, s]));

export const PRIORITIES = [
  { key: 'high', label: 'Alta', tone: 'red' },
  { key: 'medium', label: 'Média', tone: 'yellow' },
  { key: 'low', label: 'Baixa', tone: 'slate' },
];
export const PRIORITY_BY_KEY = Object.fromEntries(PRIORITIES.map((p) => [p.key, p]));

/** Situação da landing page do lead. */
export const LANDING = [
  { key: 'none', label: 'Sem site', tone: 'red', hint: 'Não possui site nem landing page' },
  { key: 'site_only', label: 'Site sem landing', tone: 'yellow', hint: 'Tem site, mas não tem landing page de conversão' },
  { key: 'has_landing', label: 'Com landing page', tone: 'green', hint: 'Já possui landing page' },
  { key: 'unknown', label: 'Não verificado', tone: 'slate', hint: 'Ainda não analisado' },
];
export const LANDING_BY_KEY = Object.fromEntries(LANDING.map((l) => [l.key, l]));

export const SOURCES = [
  { key: 'manual', label: 'Cadastro manual' },
  { key: 'ai_agent', label: 'Agente de IA' },
  { key: 'google_maps', label: 'Google Maps' },
  { key: 'import', label: 'Importação' },
  { key: 'other', label: 'Outra' },
];
export const SOURCE_BY_KEY = Object.fromEntries(SOURCES.map((s) => [s.key, s]));

export const STATES = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA',
  'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
];

/** Sugestões de segmentos (apenas atalhos; o usuário pode digitar qualquer outro). */
export const SEGMENT_SUGGESTIONS = [
  'Clínica odontológica', 'Clínica de estética', 'Advocacia', 'Contabilidade', 'Imobiliária',
  'Academia', 'Salão de beleza', 'Barbearia', 'Restaurante', 'Pet shop', 'Oficina mecânica',
  'Arquitetura e design', 'Psicologia', 'Nutrição', 'Fisioterapia', 'Escola de idiomas',
  'Autoescola', 'Energia solar', 'Construção e reformas', 'Fotografia',
  'Ótica', 'Floricultura', 'Cafeteria', 'Pousada', 'Estúdio de tatuagem', 'Lava-jato', 'Eletricista',
  'Encanador', 'Marcenaria', 'Mercado', 'Loja de roupas', 'Material de construção',
];

export const ACTIVITY_ICONS = {
  created: 'plus-circle',
  updated: 'pencil',
  status_changed: 'arrow-right-left',
  note: 'message-square-text',
  ai_analysis: 'bot',
  message_prepared: 'send',
};

export const PAGE_SIZE = 15;

// ---------------------------------------------------------------------------
// Parceria site + marketing: avaliação manual do Instagram
// (regras e pesos em backend/app/services/scoring.py)
// ---------------------------------------------------------------------------
export const MARKETING_THRESHOLD = 50;

export const IG_LAST_POST = [
  { key: 'unknown', label: 'Não avaliado' },
  { key: 'week', label: 'Nos últimos 7 dias' },
  { key: 'month', label: 'Nos últimos 30 dias' },
  { key: 'quarter', label: 'Nos últimos 3 meses' },
  { key: 'older', label: 'Há mais de 3 meses' },
  { key: 'none', label: 'Nenhum post' },
];
export const IG_ENGAGEMENT = [
  { key: 'unknown', label: 'Não avaliado' },
  { key: 'good', label: 'Bom (curtidas e comentários)' },
  { key: 'low', label: 'Baixo (poucas curtidas)' },
  { key: 'none', label: 'Nenhum (sem interação)' },
];
export const IG_QUALITY = [
  { key: 'unknown', label: 'Não avaliado' },
  { key: 'professional', label: 'Profissional (bio, destaques, identidade)' },
  { key: 'amateur', label: 'Amador (fotos soltas, sem padrão)' },
];

/** Filtro por área da parceria. */
export const NEEDS = [
  { key: 'site', label: 'Precisa de site' },
  { key: 'marketing', label: 'Precisa de marketing' },
  { key: 'both', label: 'Precisa dos dois' },
  { key: 'marketing_pending', label: 'Instagram a avaliar' },
];
