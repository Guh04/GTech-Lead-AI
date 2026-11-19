// Gerenciamento de leads: busca, filtros, ordenação, CRUD e exportação CSV.
import { api } from '../api.js';
import { $, html, setHtml, debounce, hashParams, formatNumber, formatDate, formatPhone } from '../utils.js';
import { renderIcons, icon, toast, toastError, errorState, emptyState, skeletonRows, statusBadge, priorityBadge, landingBadge, scoreBar, confirmDialog, withLoading } from '../ui.js';
import { openLeadDetail } from '../components/lead-detail.js';
import { openLeadForm } from '../components/lead-form.js';
import { openLeadImport } from '../components/lead-import.js';
import { STATUSES, PRIORITIES, LANDING, PAGE_SIZE } from '../constants.js';

const FILTER_IDS = { search: 'f-search', segment: 'f-segment', city: 'f-city', priority: 'f-priority', status: 'f-status', landing_status: 'f-landing', sort: 'f-sort' };

function fillSelect(sel, options, current) {
  const first = sel.options[0];
  sel.replaceChildren(first, ...options.map(([value, label]) => {
    const o = document.createElement('option');
    o.value = value;
    o.textContent = label;
    return o;
  }));
  sel.value = current && options.some(([v]) => v === current) ? current : '';
}

export async function mount(view) {
  const el = (key) => $(`#${FILTER_IDS[key]}`, view);
  const initial = hashParams();
  const filters = { search: '', segment: '', city: '', priority: '', status: '', landing_status: '', sort: 'created_desc', ...pick(initial) };
  let page = 1;
  let reqId = 0;
  let alive = true;
  let rows = [];

  function pick(obj) {
    return Object.fromEntries(Object.keys(FILTER_IDS).filter((k) => obj[k]).map((k) => [k, obj[k]]));
  }

  // --- filtros estáticos -----------------------------------------------------
  fillSelect(el('priority'), PRIORITIES.map((p) => [p.key, `Prioridade ${p.label.toLowerCase()}`]), filters.priority);
  fillSelect(el('status'), STATUSES.map((s) => [s.key, s.label]), filters.status);
  fillSelect(el('landing_status'), LANDING.map((l) => [l.key, l.label]), filters.landing_status);
  el('search').value = filters.search;
  el('sort').value = filters.sort;

  // --- segmentos e cidades vêm do banco ---------------------------------------
  api.facets().then((f) => {
    if (!alive) return;
    fillSelect(el('segment'), f.segments.map((s) => [s, s]), filters.segment);
    fillSelect(el('city'), f.cities.map((c) => [c, c]), filters.city);
  }).catch(() => { /* filtros dinâmicos são opcionais; a lista funciona sem eles */ });

  const params = () => ({ ...filters, page, page_size: PAGE_SIZE });
  const hasFilters = () => ['search', 'segment', 'city', 'priority', 'status', 'landing_status'].some((k) => filters[k]);

  // --- renderização -------------------------------------------------------------
  function renderRows(items) {
    return html`${items.map((l) => html`
      <tr class="clickable" data-id="${l.id}">
        <td><div class="cell-main">${l.company_name}</div><div class="cell-sub">${l.contact_name || 'Responsável não identificado'}</div></td>
        <td class="hide-sm">${l.segment || html`<span class="faint">—</span>`}</td>
        <td class="hide-sm nowrap">${[l.city, l.state].filter(Boolean).join(' / ') || html`<span class="faint">—</span>`}</td>
        <td class="hide-sm nowrap">${l.whatsapp || l.phone ? formatPhone(l.whatsapp || l.phone) : html`<span class="faint">—</span>`}${l.whatsapp ? html` <span class="faint" title="WhatsApp">${icon('message-circle', 'icon-sm')}</span>` : ''}</td>
        <td class="hide-sm">${landingBadge(l.landing_page_status)}</td>
        <td>${priorityBadge(l.priority)}</td>
        <td class="hide-sm">${scoreBar(l.score, l.priority)}</td>
        <td>${statusBadge(l.status)}</td>
        <td class="hide-sm nowrap muted">${formatDate(l.created_at)}</td>
        <td><div class="actions-cell">
          <button class="btn btn-ghost btn-icon btn-sm" data-act="edit" title="Editar" aria-label="Editar ${l.company_name}">${icon('pencil', 'icon-sm')}</button>
          <button class="btn btn-ghost btn-icon btn-sm" data-act="delete" title="Excluir" aria-label="Excluir ${l.company_name}">${icon('trash-2', 'icon-sm')}</button>
        </div></td>
      </tr>`)}`;
  }

  function renderPagination(total) {
    const box = $('#pagination', view);
    const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    box.hidden = total === 0;
    if (total === 0) return;
    const from = (page - 1) * PAGE_SIZE + 1;
    const to = Math.min(total, page * PAGE_SIZE);
    setHtml(box, html`<span>Mostrando <b>${from}–${to}</b> de <b>${formatNumber(total)}</b> leads</span>
      <div class="row"><button class="btn btn-sm" data-page="prev" ${page <= 1 ? 'disabled' : ''}>${icon('chevron-left', 'icon-sm')}Anterior</button>
      <span class="muted">Página ${page} de ${pages}</span>
      <button class="btn btn-sm" data-page="next" ${page >= pages ? 'disabled' : ''}>Próxima${icon('chevron-right', 'icon-sm')}</button></div>`);
  }

  async function load() {
    const my = ++reqId;
    $('#f-clear', view).hidden = !hasFilters();
    const state = $('#leads-state', view);
    state.innerHTML = '';
    $('#leads-table', view).hidden = false;
    setHtml($('#leads-body', view), skeletonRows(6, 10));
    try {
      const res = await api.listLeads(params());
      if (!alive || my !== reqId) return;
      // Se a página ficou vazia (ex.: após excluir o último item), volta uma página.
      const lastPage = Math.max(1, Math.ceil(res.total / PAGE_SIZE));
      if (page > lastPage) { page = lastPage; return load(); }

      rows = res.items;
      setHtml($('#leads-body', view), renderRows(res.items));
      $('#leads-table', view).hidden = res.items.length === 0;
      if (res.items.length === 0) {
        setHtml(state, hasFilters()
          ? emptyState({ icon: 'search-x', title: 'Nenhum lead encontrado', text: 'Nenhum lead corresponde aos filtros aplicados. Tente ajustar ou limpar os filtros.' })
          : emptyState({ icon: 'users', title: 'Nenhum lead cadastrado', text: 'Cadastre seu primeiro lead manualmente. Se a busca automática estiver ativa, os leads encontrados na Prospecção também aparecerão aqui.', action: html`<button class="btn btn-primary" data-new style="margin-top:8px">${icon('plus', 'icon-sm')}Cadastrar lead</button> <button class="btn" data-import style="margin-top:8px">${icon('upload', 'icon-sm')}Importar planilha</button>` }));
      }
      renderPagination(res.total);
      renderIcons();
    } catch (err) {
      if (!alive || my !== reqId) return;
      $('#leads-table', view).hidden = true;
      $('#pagination', view).hidden = true;
      setHtml(state, errorState(err));
      renderIcons();
    }
  }

  // --- eventos -------------------------------------------------------------------
  const onFilter = (key) => () => { filters[key] = el(key).value; page = 1; load(); };
  ['segment', 'city', 'priority', 'status', 'landing_status', 'sort'].forEach((k) => el(k).addEventListener('change', onFilter(k)));
  el('search').addEventListener('input', debounce(() => { filters.search = el('search').value.trim(); page = 1; load(); }, 350));

  $('#f-clear', view).addEventListener('click', () => {
    Object.assign(filters, { search: '', segment: '', city: '', priority: '', status: '', landing_status: '' });
    ['search', 'segment', 'city', 'priority', 'status', 'landing_status'].forEach((k) => { el(k).value = ''; });
    page = 1;
    load();
  });

  const create = async () => {
    try { if (await openLeadForm()) load(); } catch (err) { toastError(err); }
  };
  $('#add-btn', view).addEventListener('click', create);

  $('#import-btn', view).addEventListener('click', async () => {
    if (await openLeadImport()) { page = 1; load(); }
  });

  $('#export-btn', view).addEventListener('click', async (e) => {
    try {
      const { page: _p, page_size: _s, ...f } = params();
      await withLoading(e.currentTarget, () => api.download('/leads/export', f, `gtech-leads-${new Date().toISOString().slice(0, 10)}.csv`));
      toast('Exportação concluída. O arquivo respeita os filtros aplicados.', 'success');
    } catch (err) { toastError(err); }
  });

  // Limpeza: mostra a prévia (nada é apagado) e só apaga após confirmação explícita.
  // includeToday=false: só leads de dias anteriores. includeToday=true: tudo que ainda não foi contatado.
  const runCleanup = async (btn, includeToday) => {
    const params = includeToday ? { include_today: true } : undefined;
    const what = includeToday ? 'que ainda não foram contatados' : 'de dias anteriores';
    try {
      const prev = await withLoading(btn, () => api.get('/leads/cleanup/preview', params));
      if (!prev.deletable) {
        toast(prev.protected ? `Nada a apagar: os ${prev.protected} lead(s) restantes já foram contatados ou pediram para não ser contatados.` : `Não há leads ${what}.`, 'info');
        return;
      }
      const ok = await confirmDialog({
        title: includeToday ? 'Limpar leads não contatados' : 'Limpar leads de dias anteriores',
        message: `Apagar ${prev.deletable} lead(s) ${what}?`,
        detail: `${includeToday ? 'Isso inclui os leads de hoje. ' : 'Os leads de hoje ficam. '}${prev.protected ? `${prev.protected} lead(s) serão mantidos por já terem sido contatados, estarem em negociação ou terem pedido para não ser contatados. ` : ''}Atenção: se você chamou alguém fora do sistema e não mudou o estágio do lead, ele ainda conta como “não contatado” e será apagado. O histórico e as mensagens dos leads apagados também são removidos. Esta ação não pode ser desfeita.`,
        confirmLabel: `Apagar ${prev.deletable} lead(s)`,
        danger: true,
      });
      if (!ok) return;
      const res = await api.post(`/leads/cleanup${includeToday ? '?include_today=true' : ''}`);
      toast(`${res.deleted} lead(s) apagados.`, 'success');
      page = 1;
      load();
    } catch (err) { toastError(err); }
  };
  $('#cleanup-btn', view).addEventListener('click', (e) => runCleanup(e.currentTarget, false));
  $('#cleanup-all-btn', view).addEventListener('click', (e) => runCleanup(e.currentTarget, true));

  view.addEventListener('click', async (e) => {
    if (e.target.closest('[data-new]')) return create();
    if (e.target.closest('[data-import]')) return $('#import-btn', view).click();
    if (e.target.closest('[data-retry]')) return load();

    const pageBtn = e.target.closest('[data-page]');
    if (pageBtn) { page += pageBtn.dataset.page === 'next' ? 1 : -1; load(); window.scrollTo({ top: 0, behavior: 'smooth' }); return; }

    const tr = e.target.closest('tr[data-id]');
    if (!tr) return;
    const lead = rows.find((r) => r.id === tr.dataset.id);
    const act = e.target.closest('[data-act]')?.dataset.act;

    if (act === 'edit') {
      try { if (await openLeadForm({ lead })) load(); } catch (err) { toastError(err); }
    } else if (act === 'delete') {
      const ok = await confirmDialog({
        title: 'Excluir lead',
        message: `Tem certeza que deseja excluir "${lead.company_name}"?`,
        detail: 'O lead e todo o seu histórico serão removidos permanentemente. Esta ação não pode ser desfeita.',
        confirmLabel: 'Excluir definitivamente',
        danger: true,
      });
      if (!ok) return;
      try {
        await api.deleteLead(lead.id);
        toast('Lead excluído.', 'success');
        load();
      } catch (err) { toastError(err); }
    } else {
      openLeadDetail(tr.dataset.id, { onChange: load });
    }
  });

  await load();
  return () => { alive = false; };
}
