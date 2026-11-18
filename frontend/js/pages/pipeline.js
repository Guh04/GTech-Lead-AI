// Pipeline comercial em formato Kanban com arrastar-e-soltar.
import { api } from '../api.js';
import { $, $$, html, setHtml, debounce, formatPhone, timeAgo } from '../utils.js';
import { renderIcons, icon, toast, toastError, errorState, priorityBadge } from '../ui.js';
import { openLeadDetail } from '../components/lead-detail.js';
import { openLeadForm } from '../components/lead-form.js';
import { STATUSES, STATUS_BY_KEY, PRIORITIES, LANDING_BY_KEY } from '../constants.js';

const LIMIT = 500;

function cardHtml(l) {
  const s = STATUS_BY_KEY[l.status];
  const place = [l.city, l.state].filter(Boolean).join('/');
  return html`
  <article class="kcard" draggable="true" data-id="${l.id}" style="--c:${s.color}">
    <div class="kcard-title">${l.company_name}</div>
    <div class="kcard-meta">
      ${l.segment ? html`<span>${icon('building-2')}${l.segment}</span>` : ''}
      ${place ? html`<span>${icon('map-pin')}${place}</span>` : ''}
      ${l.whatsapp || l.phone ? html`<span>${icon('phone')}${formatPhone(l.whatsapp || l.phone)}</span>` : ''}
    </div>
    <div class="row" style="gap:6px">
      ${priorityBadge(l.priority)}
      <span class="badge no-dot" title="Pontuação comercial">${icon('target', 'icon-sm')}${l.score}</span>
      <span class="faint" style="font-size:12px;margin-left:auto" title="Tempo neste estágio">${timeAgo(l.status_updated_at)}</span>
    </div>
    <div class="kcard-foot">
      <select class="select" data-move aria-label="Mover ${l.company_name} para">
        <option value="">Mover para…</option>
        ${STATUSES.filter((x) => x.key !== l.status).map((x) => html`<option value="${x.key}">${x.label}</option>`)}
      </select>
    </div>
  </article>`;
}

export async function mount(view) {
  const board = $('#board', view);
  const state = $('#pl-state', view);
  let leads = [];
  let total = 0;
  let alive = true;
  let reqId = 0;
  const filters = { search: '', priority: '' };

  const sel = $('#pl-priority', view);
  PRIORITIES.forEach((p) => sel.append(new Option(`Prioridade ${p.label.toLowerCase()}`, p.key)));

  function renderBoard() {
    setHtml(board, html`${STATUSES.map((s) => {
      const items = leads.filter((l) => l.status === s.key);
      return html`
      <section class="kcol" data-status="${s.key}" style="--c:${s.color}" aria-label="${s.label}">
        <header class="kcol-head"><span class="kcol-dot"></span><span class="kcol-title">${s.label}</span><span class="kcol-count num">${items.length}</span></header>
        <div class="kcol-body">
          ${items.length ? items.map(cardHtml) : html`<div class="kcol-empty">Arraste um lead para cá</div>`}
        </div>
      </section>`;
    })}`);
    renderIcons();
  }

  async function load() {
    const my = ++reqId;
    state.innerHTML = '';
    setHtml(board, html`${STATUSES.map((s) => html`<section class="kcol"><header class="kcol-head"><span class="kcol-dot" style="--c:${s.color}"></span><span class="kcol-title">${s.label}</span></header><div class="kcol-body"><div class="skeleton sk-block"></div></div></section>`)}`);
    try {
      const res = await api.listLeads({ ...filters, sort: 'score_desc', page: 1, page_size: LIMIT });
      if (!alive || my !== reqId) return;
      leads = res.items;
      total = res.total;
      if (total > LIMIT) {
        setHtml(state, html`<div class="alert" data-tone="warning" style="margin-bottom:16px">${icon('triangle-alert')}<div>Exibindo os ${LIMIT} leads de maior pontuação de ${total}. Use a pesquisa ou o filtro para refinar.</div></div>`);
      } else if (total === 0 && !filters.search && !filters.priority) {
        setHtml(state, html`<div class="alert" data-tone="info" style="margin-bottom:16px">${icon('info')}<div>Nenhum lead no pipeline ainda. <a href="#" data-new>Cadastre o primeiro lead</a> para começar.</div></div>`);
      }
      renderBoard();
      renderIcons();
    } catch (err) {
      if (!alive || my !== reqId) return;
      board.innerHTML = '';
      setHtml(state, errorState(err));
      renderIcons();
    }
  }

  /** Move o lead com atualização otimista; reverte se a API falhar. */
  async function move(id, status) {
    const lead = leads.find((l) => l.id === id);
    if (!lead || lead.status === status) return;
    const previous = { status: lead.status, status_updated_at: lead.status_updated_at };
    lead.status = status;
    lead.status_updated_at = new Date().toISOString();
    renderBoard();
    $(`.kcard[data-id="${id}"]`, board)?.classList.add('saving');
    try {
      const updated = await api.moveLead(id, status);
      Object.assign(lead, updated);
      toast(`"${lead.company_name}" movido para ${STATUS_BY_KEY[status].label}.`, 'success');
    } catch (err) {
      Object.assign(lead, previous);
      toastError(err);
    }
    if (alive) renderBoard();
  }

  // --- arrastar e soltar -------------------------------------------------------
  let draggingId = null;
  board.addEventListener('dragstart', (e) => {
    const card = e.target.closest('.kcard');
    if (!card) return;
    draggingId = card.dataset.id;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', draggingId);
    requestAnimationFrame(() => card.classList.add('dragging'));
  });
  board.addEventListener('dragend', () => {
    draggingId = null;
    $$('.dragging, .drag-over', board).forEach((el) => el.classList.remove('dragging', 'drag-over'));
  });
  board.addEventListener('dragover', (e) => {
    const col = e.target.closest('.kcol');
    if (!col || !draggingId) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    $$('.drag-over', board).forEach((el) => el !== col && el.classList.remove('drag-over'));
    col.classList.add('drag-over');
  });
  board.addEventListener('drop', (e) => {
    const col = e.target.closest('.kcol');
    if (!col || !draggingId) return;
    e.preventDefault();
    const id = draggingId;
    draggingId = null;
    move(id, col.dataset.status);
  });

  // --- seletor "Mover para" e abertura da ficha ----------------------------------
  board.addEventListener('change', (e) => {
    const s = e.target.closest('[data-move]');
    if (!s || !s.value) return;
    move(s.closest('.kcard').dataset.id, s.value);
  });
  board.addEventListener('click', (e) => {
    if (e.target.closest('[data-move]')) return;
    const card = e.target.closest('.kcard');
    if (card) openLeadDetail(card.dataset.id, { onChange: load });
  });
  state.addEventListener('click', async (e) => {
    if (e.target.closest('[data-retry]')) load();
    if (e.target.closest('[data-new]')) {
      e.preventDefault();
      try { if (await openLeadForm()) load(); } catch (err) { toastError(err); }
    }
  });

  $('#pl-search', view).addEventListener('input', debounce((e) => { filters.search = e.target.value.trim(); load(); }, 350));
  sel.addEventListener('change', () => { filters.priority = sel.value; load(); });

  await load();
  return () => { alive = false; };
}
