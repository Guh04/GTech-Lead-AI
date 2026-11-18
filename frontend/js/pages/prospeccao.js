// Prospecção: formulário de pesquisa, histórico e resultados.
// A busca em si é executada por um provedor configurado no backend (Google Places ou API externa).
// Nada aqui é simulado.
import { api } from '../api.js';
import { $, $$, html, setHtml, formatDateTime, formatNumber, hashParams } from '../utils.js';
import { renderIcons, icon, toast, toastError, errorState, emptyState, withLoading, statusBadge, priorityBadge, landingBadge, scoreBar } from '../ui.js';
import { openLeadDetail } from '../components/lead-detail.js';
import { STATES, LANDING, SEGMENT_SUGGESTIONS } from '../constants.js';

const SEARCH_STATUS = {
  running: { label: 'Em execução', tone: 'blue' },
  completed: { label: 'Concluída', tone: 'green' },
  failed: { label: 'Falhou', tone: 'red' },
};
const SITE_LABEL = { any: 'Todas', with_site: 'Com site', without_site: 'Sem site' };

export async function mount(view) {
  let alive = true;
  const selected = new Set();
  let searches = [];
  let shownSearchId = null;

  // --- formulário ------------------------------------------------------------
  const stateSel = $('#p-state', view);
  STATES.forEach((s) => stateSel.append(new Option(s, s)));
  const landingSel = $('#p-landing', view);
  landingSel.append(new Option('Qualquer situação', 'any'));
  LANDING.filter((l) => l.key !== 'unknown').forEach((l) => landingSel.append(new Option(l.label, l.key)));

  const qty = $('#p-qty', view);
  qty.addEventListener('input', () => { $('#p-qty-out', view).textContent = qty.value; });

  function renderChips() {
    const all = [...new Set([...SEGMENT_SUGGESTIONS, ...selected])];
    setHtml($('#p-chips', view), html`${all.map((s) => html`<button type="button" class="chip ${selected.has(s) ? 'selected' : ''}" data-seg="${s}" aria-pressed="${selected.has(s)}">${selected.has(s) ? icon('check') : ''}${s}</button>`)}`);
    $('#p-selected-hint', view).textContent = selected.size
      ? `${selected.size} ${selected.size === 1 ? 'segmento selecionado' : 'segmentos selecionados'}.`
      : 'Nenhum segmento selecionado.';
    renderIcons();
  }
  renderChips();

  $('#p-chips', view).addEventListener('click', (e) => {
    const chip = e.target.closest('[data-seg]');
    if (!chip) return;
    const s = chip.dataset.seg;
    selected.has(s) ? selected.delete(s) : selected.add(s);
    renderChips();
  });
  const addCustom = () => {
    const input = $('#p-custom', view);
    const v = input.value.trim();
    if (v) { selected.add(v); input.value = ''; renderChips(); }
    input.focus();
  };
  $('#p-add', view).addEventListener('click', addCustom);
  $('#p-custom', view).addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); addCustom(); } });

  // --- status do agente --------------------------------------------------------
  async function loadAgentStatus() {
    const box = $('#agent-status', view);
    try {
      const s = await api.get('/prospecting/status');
      if (!alive) return;
      setHtml(box, s.available
        ? html`<div class="alert" data-tone="success">${icon('plug-zap')}<div><strong>Busca automática ativa</strong>Provedor: ${s.provider}. Ao iniciar, o sistema pesquisa empresas reais e salva os leads encontrados.</div></div>`
        : html`<div class="alert" data-tone="warning">${icon('plug')}<div><strong>Busca automática não configurada</strong>${s.message}</div></div>`);
      renderIcons();
    } catch (err) {
      setHtml(box, html`<div class="alert" data-tone="error">${icon('circle-alert')}<div>${err.message}</div></div>`);
      renderIcons();
    }
  }

  // --- resultados e histórico -----------------------------------------------------
  async function showResults(search) {
    shownSearchId = search.id;
    const where = [search.region, search.state].filter(Boolean).join(' / ');
    $('#results-title', view).textContent = 'Resultados encontrados';
    $('#results-sub', view).textContent = `${where} · ${(search.segments || []).join(', ') || 'sem segmentos'} · ${formatDateTime(search.created_at)}`;
    const box = $('#results', view);
    setHtml(box, html`<div class="page-loading" style="min-height:120px"><div class="spinner"></div></div>`);
    try {
      const res = await api.listLeads({ search_id: search.id, sort: 'score_desc', page_size: 100 });
      if (!alive || shownSearchId !== search.id) return;
      if (search.status === 'failed') {
        setHtml(box, html`<div class="alert" data-tone="error" style="margin:16px 20px">${icon('circle-alert')}<div><strong>A pesquisa falhou</strong>${search.error_message || 'Erro não informado pelo provedor.'}</div></div>`);
      } else if (!res.items.length) {
        setHtml(box, emptyState({ icon: 'search-x', title: 'Nenhum lead novo nesta pesquisa', text: `A busca retornou ${search.results_count} resultado(s); ${search.duplicates_count} já existiam na sua base.` }));
      } else {
        setHtml(box, html`<table class="table"><thead><tr><th>Empresa</th><th class="hide-sm">Segmento</th><th>Landing page</th><th>Prioridade</th><th class="hide-sm">Pontuação</th><th>Estágio</th></tr></thead>
          <tbody>${res.items.map((l) => html`<tr class="clickable" data-lead="${l.id}">
            <td><div class="cell-main">${l.company_name}</div><div class="cell-sub">${[l.city, l.state].filter(Boolean).join(' / ')}</div></td>
            <td class="hide-sm">${l.segment || '—'}</td><td>${landingBadge(l.landing_page_status)}</td><td>${priorityBadge(l.priority)}</td>
            <td class="hide-sm">${scoreBar(l.score, l.priority)}</td><td>${statusBadge(l.status)}</td></tr>`)}</tbody></table>`);
      }
      renderIcons();
    } catch (err) {
      setHtml(box, errorState(err));
      renderIcons();
    }
  }

  function renderHistory() {
    const box = $('#history', view);
    if (!searches.length) {
      setHtml(box, emptyState({ icon: 'history', title: 'Nenhuma pesquisa realizada', text: 'As pesquisas executadas ficarão registradas aqui.' }));
      return;
    }
    setHtml(box, html`<table class="table"><thead><tr><th>Data</th><th>Região</th><th class="hide-sm">Segmentos</th><th class="hide-sm">Site</th><th>Status</th><th>Leads</th></tr></thead>
      <tbody>${searches.map((s) => html`<tr class="clickable" data-search="${s.id}">
        <td class="nowrap muted">${formatDateTime(s.created_at)}</td>
        <td><div class="cell-main">${s.region}${s.state ? ` / ${s.state}` : ''}</div><div class="cell-sub">Meta: ${formatNumber(s.desired_quantity)} leads</div></td>
        <td class="hide-sm" style="max-width:220px"><span class="truncate" style="display:block" title="${(s.segments || []).join(', ')}">${(s.segments || []).join(', ') || '—'}</span></td>
        <td class="hide-sm">${SITE_LABEL[s.website_filter] || s.website_filter}</td>
        <td><span class="badge" data-tone="${SEARCH_STATUS[s.status]?.tone || 'slate'}" ${s.error_message ? html`title="${s.error_message}"` : ''}>${SEARCH_STATUS[s.status]?.label || s.status}</span></td>
        <td class="num">${formatNumber(s.inserted_count)} <span class="faint">/ ${formatNumber(s.results_count)}</span></td></tr>`)}</tbody></table>`);
  }

  async function loadHistory() {
    try {
      searches = await api.get('/prospecting/history', { limit: 30 });
      if (!alive) return;
      renderHistory();
      renderIcons();
    } catch (err) {
      setHtml($('#history', view), errorState(err));
      renderIcons();
    }
  }

  // --- envio ------------------------------------------------------------------------
  $('#prosp-form', view).addEventListener('submit', async (e) => {
    e.preventDefault();
    const errBox = $('#prosp-error', view);
    errBox.hidden = true;
    const region = $('#p-region', view).value.trim();
    const problems = [];
    if (region.length < 2) problems.push('Informe a cidade ou região.');
    if (!selected.size) problems.push('Selecione ao menos um segmento.');
    if (problems.length) {
      setHtml(errBox, html`${icon('circle-alert')}<div>${problems.join(' ')}</div>`);
      errBox.hidden = false;
      renderIcons();
      return;
    }
    const body = {
      region,
      state: stateSel.value || null,
      segments: [...selected],
      desired_quantity: Number(qty.value),
      website_filter: $('input[name="website_filter"]:checked', view).value,
      landing_filter: landingSel.value,
    };
    try {
      const search = await withLoading($('#p-submit', view), () => api.post('/prospecting/search', body));
      toast(`Pesquisa concluída: ${search.inserted_count} novo(s) lead(s) adicionados.`, 'success');
      await loadHistory();
      showResults(search);
    } catch (err) {
      setHtml(errBox, html`${icon(err.status === 503 ? 'plug' : 'circle-alert')}<div><strong>${err.status === 503 ? 'Busca indisponível' : 'Não foi possível iniciar a pesquisa'}</strong>${err.message}</div>`);
      errBox.dataset.tone = err.status === 503 ? 'warning' : 'error';
      errBox.hidden = false;
      renderIcons();
      loadHistory();
    }
  });

  view.addEventListener('click', (e) => {
    const leadRow = e.target.closest('[data-lead]');
    if (leadRow) { openLeadDetail(leadRow.dataset.lead, { onChange: () => { const s = searches.find((x) => x.id === shownSearchId); if (s) showResults(s); } }); return; }
    const row = e.target.closest('[data-search]');
    if (row) showResults(searches.find((s) => s.id === row.dataset.search));
    if (e.target.closest('[data-retry]')) loadHistory();
  });
  $('#hist-refresh', view).addEventListener('click', loadHistory);

  setHtml($('#results', view), emptyState({ icon: 'radar', title: 'Nenhuma pesquisa selecionada', text: 'Inicie uma pesquisa ou selecione uma do histórico para ver os leads encontrados.' }));
  renderIcons();
  await Promise.all([loadAgentStatus(), loadHistory()]);
  const wanted = hashParams().search;
  if (wanted) { const s = searches.find((x) => x.id === wanted); if (s) showResults(s); }
  return () => { alive = false; };
}
