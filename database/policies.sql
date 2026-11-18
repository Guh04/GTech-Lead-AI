-- =============================================================================
-- GTech Lead AI - Políticas de segurança (Row Level Security)
--
-- Execute DEPOIS de schema.sql (Supabase > SQL Editor).
--
-- Modelo: cada usuário autenticado enxerga e altera SOMENTE os próprios dados
-- (owner_id = auth.uid()). O papel "anon" (visitante sem login) não tem acesso
-- a nada. O backend usa o token (JWT) do próprio usuário nas chamadas ao banco,
-- portanto estas políticas são aplicadas de verdade e NENHUMA chave de serviço
-- (service_role) é necessária na aplicação.
-- =============================================================================

alter table public.users                enable row level security;
alter table public.leads                enable row level security;
alter table public.lead_activities      enable row level security;
alter table public.prospecting_searches enable row level security;

-- Privilégios de tabela: visitantes anônimos sem acesso; usuários logados
-- só passam se as políticas abaixo permitirem.
revoke all on public.users, public.leads, public.lead_activities, public.prospecting_searches from anon;
grant select, update                   on public.users                to authenticated;
grant select, insert, update, delete   on public.leads                to authenticated;
grant select, insert, delete           on public.lead_activities      to authenticated;
grant select, insert, update           on public.prospecting_searches to authenticated;

-- ---------------------------------------------------------------- users ------
drop policy if exists "users_select_own" on public.users;
create policy "users_select_own" on public.users
  for select to authenticated
  using (id = (select auth.uid()));

drop policy if exists "users_update_own" on public.users;
create policy "users_update_own" on public.users
  for update to authenticated
  using (id = (select auth.uid()))
  with check (id = (select auth.uid()));

-- ---------------------------------------------------------------- leads ------
drop policy if exists "leads_select_own" on public.leads;
create policy "leads_select_own" on public.leads
  for select to authenticated
  using (owner_id = (select auth.uid()));

drop policy if exists "leads_insert_own" on public.leads;
create policy "leads_insert_own" on public.leads
  for insert to authenticated
  with check (owner_id = (select auth.uid()));

drop policy if exists "leads_update_own" on public.leads;
create policy "leads_update_own" on public.leads
  for update to authenticated
  using (owner_id = (select auth.uid()))
  with check (owner_id = (select auth.uid()));

drop policy if exists "leads_delete_own" on public.leads;
create policy "leads_delete_own" on public.leads
  for delete to authenticated
  using (owner_id = (select auth.uid()));

-- ------------------------------------------------------- lead_activities ------
drop policy if exists "activities_select_own" on public.lead_activities;
create policy "activities_select_own" on public.lead_activities
  for select to authenticated
  using (owner_id = (select auth.uid()));

-- Só é possível registrar atividade em um lead que pertence ao próprio usuário.
drop policy if exists "activities_insert_own" on public.lead_activities;
create policy "activities_insert_own" on public.lead_activities
  for insert to authenticated
  with check (
    owner_id = (select auth.uid())
    and exists (
      select 1 from public.leads l
      where l.id = lead_id and l.owner_id = (select auth.uid())
    )
  );

drop policy if exists "activities_delete_own" on public.lead_activities;
create policy "activities_delete_own" on public.lead_activities
  for delete to authenticated
  using (owner_id = (select auth.uid()));

-- -------------------------------------------------- prospecting_searches ------
drop policy if exists "searches_select_own" on public.prospecting_searches;
create policy "searches_select_own" on public.prospecting_searches
  for select to authenticated
  using (owner_id = (select auth.uid()));

drop policy if exists "searches_insert_own" on public.prospecting_searches;
create policy "searches_insert_own" on public.prospecting_searches
  for insert to authenticated
  with check (owner_id = (select auth.uid()));

drop policy if exists "searches_update_own" on public.prospecting_searches;
create policy "searches_update_own" on public.prospecting_searches
  for update to authenticated
  using (owner_id = (select auth.uid()))
  with check (owner_id = (select auth.uid()));

-- ------------------------------------------------------ outreach_messages ------
alter table public.outreach_messages enable row level security;
revoke all on public.outreach_messages from anon;
grant select, insert, update, delete on public.outreach_messages to authenticated;

drop policy if exists "outreach_select_own" on public.outreach_messages;
create policy "outreach_select_own" on public.outreach_messages
  for select to authenticated
  using (owner_id = (select auth.uid()));

-- Só é possível criar mensagem para um lead que pertence ao próprio usuário.
drop policy if exists "outreach_insert_own" on public.outreach_messages;
create policy "outreach_insert_own" on public.outreach_messages
  for insert to authenticated
  with check (
    owner_id = (select auth.uid())
    and exists (
      select 1 from public.leads l
      where l.id = lead_id and l.owner_id = (select auth.uid())
    )
  );

drop policy if exists "outreach_update_own" on public.outreach_messages;
create policy "outreach_update_own" on public.outreach_messages
  for update to authenticated
  using (owner_id = (select auth.uid()))
  with check (owner_id = (select auth.uid()));

drop policy if exists "outreach_delete_own" on public.outreach_messages;
create policy "outreach_delete_own" on public.outreach_messages
  for delete to authenticated
  using (owner_id = (select auth.uid()));
