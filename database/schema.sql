-- =============================================================================
-- GTech Lead AI - Esquema do banco de dados (PostgreSQL / Supabase)
--
-- Como usar: Supabase > SQL Editor > New query > cole este arquivo > Run.
-- Depois execute também o arquivo policies.sql (segurança / RLS).
--
-- O script é idempotente: pode ser executado novamente sem apagar dados
-- (usa "if not exists" / "create or replace").
-- =============================================================================

-- Extensão para busca textual rápida (ILIKE '%termo%') pelo nome da empresa.
create extension if not exists pg_trgm with schema extensions;


-- -----------------------------------------------------------------------------
-- Funções utilitárias
-- -----------------------------------------------------------------------------

-- Mantém updated_at sempre atualizado.
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;


-- -----------------------------------------------------------------------------
-- users: perfil do usuário (1:1 com auth.users, gerenciado pelo Supabase Auth)
-- -----------------------------------------------------------------------------
create table if not exists public.users (
  id          uuid primary key references auth.users (id) on delete cascade,
  email       text not null,
  full_name   text,
  role        text not null default 'member' check (role in ('admin', 'member')),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

drop trigger if exists trg_users_updated_at on public.users;
create trigger trg_users_updated_at
  before update on public.users
  for each row execute function public.set_updated_at();

-- Cria o perfil automaticamente quando um usuário é criado no Supabase Auth.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.users (id, email, full_name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data ->> 'full_name', split_part(new.email, '@', 1))
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Cria o perfil de usuários que já existiam antes deste script.
insert into public.users (id, email, full_name)
select u.id, u.email, split_part(u.email, '@', 1)
from auth.users u
on conflict (id) do nothing;


-- -----------------------------------------------------------------------------
-- prospecting_searches: histórico de pesquisas do futuro agente de IA
-- -----------------------------------------------------------------------------
create table if not exists public.prospecting_searches (
  id                uuid primary key default gen_random_uuid(),
  owner_id          uuid not null default auth.uid() references public.users (id) on delete cascade,
  region            text not null check (char_length(btrim(region)) between 2 and 200),
  state             text check (state ~ '^[A-Z]{2}$'),
  segments          text[] not null default '{}',
  desired_quantity  integer not null check (desired_quantity between 1 and 500),
  website_filter    text not null default 'any'
                      check (website_filter in ('any', 'with_site', 'without_site')),
  landing_filter    text not null default 'any'
                      check (landing_filter in ('any', 'none', 'site_only', 'has_landing', 'unknown')),
  status            text not null default 'running'
                      check (status in ('running', 'completed', 'failed')),
  provider          text,                       -- identificação do provedor/agente que executou
  results_count     integer not null default 0, -- empresas devolvidas pelo agente
  inserted_count    integer not null default 0, -- leads novos gravados
  duplicates_count  integer not null default 0, -- ignorados por já existirem
  error_message     text,
  created_at        timestamptz not null default now(),
  finished_at       timestamptz
);

create index if not exists idx_prospecting_owner_created
  on public.prospecting_searches (owner_id, created_at desc);


-- -----------------------------------------------------------------------------
-- leads: dados comerciais, presença digital, pontuação e estágio da negociação
-- -----------------------------------------------------------------------------
create table if not exists public.leads (
  id                     uuid primary key default gen_random_uuid(),
  owner_id               uuid not null default auth.uid() references public.users (id) on delete cascade,

  -- Dados comerciais
  company_name           text not null check (char_length(btrim(company_name)) between 2 and 200),
  contact_name           text,
  segment                text,
  city                   text,
  state                  text check (state ~ '^[A-Z]{2}$'),

  -- Contatos (somente dígitos; o backend normaliza antes de gravar)
  phone                  text check (phone ~ '^[0-9]{8,15}$'),
  whatsapp               text check (whatsapp ~ '^[0-9]{8,15}$'),

  -- Presença digital
  instagram              text,                  -- usuário sem "@"
  facebook               text,                  -- URL http(s)
  website                text,                  -- URL http(s)
  landing_page_status    text not null default 'unknown'
                           check (landing_page_status in ('none', 'site_only', 'has_landing', 'unknown')),

  -- Pontuação comercial
  score                  smallint not null default 0 check (score between 0 and 100),
  score_source           text not null default 'rules' check (score_source in ('rules', 'manual', 'ai')),
  priority               text not null default 'low' check (priority in ('high', 'medium', 'low')),

  -- Origem
  source                 text not null default 'manual'
                           check (source in ('manual', 'ai_agent', 'google_maps', 'import', 'other')),
  source_url             text,                  -- fonte pública da informação (LGPD: rastreabilidade)
  prospecting_search_id  uuid references public.prospecting_searches (id) on delete set null,

  -- Pipeline comercial
  status                 text not null default 'new'
                           check (status in ('new', 'analyzed', 'contacted', 'interested',
                                             'proposal_sent', 'closed_won', 'lost')),
  status_updated_at      timestamptz not null default now(),

  notes                  text,
  do_not_contact         boolean not null default false,  -- LGPD: opt-out / pedido do titular

  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now()
);

-- Evita duplicidades (por usuário):
--   mesma empresa na mesma cidade, mesmo telefone, mesmo WhatsApp, mesmo site.
create unique index if not exists uq_leads_owner_company_city
  on public.leads (owner_id, lower(btrim(company_name)), lower(btrim(coalesce(city, ''))));
create unique index if not exists uq_leads_owner_phone
  on public.leads (owner_id, phone) where phone is not null;
create unique index if not exists uq_leads_owner_whatsapp
  on public.leads (owner_id, whatsapp) where whatsapp is not null;
create unique index if not exists uq_leads_owner_website
  on public.leads (owner_id, lower(website)) where website is not null;

-- Índices para filtros, ordenação e painéis.
create index if not exists idx_leads_owner_status    on public.leads (owner_id, status);
create index if not exists idx_leads_owner_priority  on public.leads (owner_id, priority);
create index if not exists idx_leads_owner_score     on public.leads (owner_id, score desc);
create index if not exists idx_leads_owner_created   on public.leads (owner_id, created_at desc);
create index if not exists idx_leads_owner_segment   on public.leads (owner_id, segment);
create index if not exists idx_leads_owner_city      on public.leads (owner_id, city);
create index if not exists idx_leads_search          on public.leads (prospecting_search_id)
  where prospecting_search_id is not null;
create index if not exists idx_leads_company_trgm
  on public.leads using gin (company_name extensions.gin_trgm_ops);

drop trigger if exists trg_leads_updated_at on public.leads;
create trigger trg_leads_updated_at
  before update on public.leads
  for each row execute function public.set_updated_at();

-- Registra o momento em que o lead mudou de estágio no pipeline.
create or replace function public.leads_touch_status_updated_at()
returns trigger
language plpgsql
as $$
begin
  if new.status is distinct from old.status then
    new.status_updated_at = now();
  end if;
  return new;
end;
$$;

drop trigger if exists trg_leads_status_updated_at on public.leads;
create trigger trg_leads_status_updated_at
  before update on public.leads
  for each row execute function public.leads_touch_status_updated_at();


-- -----------------------------------------------------------------------------
-- lead_activities: histórico de eventos de cada lead
-- -----------------------------------------------------------------------------
create table if not exists public.lead_activities (
  id           uuid primary key default gen_random_uuid(),
  lead_id      uuid not null references public.leads (id) on delete cascade,
  owner_id     uuid not null default auth.uid() references public.users (id) on delete cascade,
  type         text not null
                 check (type in ('created', 'updated', 'status_changed', 'note', 'ai_analysis', 'message_prepared')),
  description  text not null check (char_length(btrim(description)) between 1 and 2000),
  metadata     jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now()
);

create index if not exists idx_activities_lead_created
  on public.lead_activities (lead_id, created_at desc);
create index if not exists idx_activities_owner_created
  on public.lead_activities (owner_id, created_at desc);


-- -----------------------------------------------------------------------------
-- outreach_messages: fila de abordagem por WhatsApp (a IA prepara, o usuário aprova e envia)
-- -----------------------------------------------------------------------------
create table if not exists public.outreach_messages (
  id           uuid primary key default gen_random_uuid(),
  owner_id     uuid not null default auth.uid() references public.users (id) on delete cascade,
  lead_id      uuid not null references public.leads (id) on delete cascade,
  body         text not null check (char_length(btrim(body)) between 1 and 1000),
  status       text not null default 'draft'
                 check (status in ('draft', 'approved', 'sent', 'skipped')),
  source       text not null default 'template' check (source in ('ai', 'template')),
  created_at   timestamptz not null default now(),
  approved_at  timestamptz,
  sent_at      timestamptz
);

-- No máximo uma mensagem pendente (rascunho/aprovada) por lead.
create unique index if not exists uq_outreach_open_per_lead
  on public.outreach_messages (lead_id) where status in ('draft', 'approved');
create index if not exists idx_outreach_owner_status
  on public.outreach_messages (owner_id, status, created_at desc);
-- Contagem de envios do dia (limite diário).
create index if not exists idx_outreach_owner_sent
  on public.outreach_messages (owner_id, sent_at desc) where status = 'sent';
