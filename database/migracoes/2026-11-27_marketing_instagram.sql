-- =============================================================================
-- Migração: avaliação do Instagram e necessidade de marketing (parceria site + marketing)
-- Rode UMA vez no Supabase: SQL Editor -> New query -> cole este arquivo -> Run.
-- É seguro rodar de novo (só cria o que ainda não existe).
-- =============================================================================

alter table public.leads
  add column if not exists ig_last_post    text not null default 'unknown'
    check (ig_last_post in ('unknown', 'week', 'month', 'quarter', 'older', 'none')),
  add column if not exists ig_engagement   text not null default 'unknown'
    check (ig_engagement in ('unknown', 'good', 'low', 'none')),
  add column if not exists ig_quality      text not null default 'unknown'
    check (ig_quality in ('unknown', 'professional', 'amateur')),
  add column if not exists ig_followers    integer check (ig_followers >= 0),
  add column if not exists ig_checked_at   timestamptz,
  add column if not exists marketing_score smallint check (marketing_score between 0 and 100);

create index if not exists idx_leads_owner_marketing
  on public.leads (owner_id, marketing_score desc nulls last);

-- Leads que já existem: quem não tem Instagram já entra como "precisa de marketing" (70).
-- Quem tem Instagram fica "a avaliar" (null) até você preencher a avaliação na ficha do lead.
update public.leads set marketing_score = 70 where instagram is null and marketing_score is null;

-- Faz o PostgREST (API do Supabase) enxergar as colunas novas imediatamente.
notify pgrst, 'reload schema';
