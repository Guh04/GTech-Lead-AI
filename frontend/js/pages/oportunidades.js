// Oportunidades: leads ativos agrupados por prioridade (alta, média, baixa).
import { api } from '../api.js';
import { $, html, setHtml, formatNumber, timeAgo, formatPhone } from '../utils.js';
import { renderIcons, icon, errorState, emptyState, statusBadge, landingBadge, withLoading } from '../ui.js';
import { openLeadDetail } from '../components/lead-detail.js';
import { PRIORITIES, PRIORITY_BY_KEY } from '../constants.js';

const PER_PAGE = 24;

/** Fatos objetivos do lead que explicam o potencial (espelham os critérios de pontuação). */
function reasons(l) {
  const out = [];
  const add = (ok, yes, no) => out.push({ ok, text: ok ? yes : no });
  if (l.landing_page_status === 'none') add(true, 'Não possui site nem landing page', '');
  else if (l.landing_page_status === 'site_only') add(true, 'Tem site, mas sem landing page de conversão', '');
  else if (l.landing_page_status === 'unknown') add(false, '', 'Landing page ainda não verificada');
  else add(false, '', 'Já possui landing page');
  add(Boolean(l.whatsapp), `WhatsApp: ${formatPhone(l.whatsapp)}`, 'Sem WhatsApp informado');
  if (l.instagram || l.facebook) add(true, 'Presença ativa em redes sociais', '');
  return out;
}

function card(l, i) {
  const place = [l.city, l.state].filter(Boolean).join(' / ');
  return html`
  <article class="card opp-card" data-id="${l.id}" tabindex="0" style="animation-delay:${Math.min(i, 12) * 30}ms" aria-label="${l.company_name}">
    <div class="opp-top">
      <div style="min-width:0">
        <div class="opp-title">${l.company_name}</div>
        <div class="muted" style="font-size:13px;margin-top:2px">${[l.segment, place].filter(Boolean).join(' · ') || 'Sem segmento ou cidade'}</div>
      </div>
      <div class="opp-score" data-priority="${l.priority}" title="Pontuação comercial">${l.score}</div>
    </div>
    <div class="opp-tags">${landingBadge(l.landing_page_status)}${statusBadge(l.status)}</div>
    <ul class="opp-reasons">${reasons(l).map((r) => html`<li class="${r.ok ? '' : 'neg'}">${icon(r.ok ? 'circle-check' : 'minus')}${r.text}</li>`)}</ul>
    <div class="opp-foot"><span>Cadastrado ${timeAgo(l.created_at)}</span><span class="row" style="gap:4px;color:var(--blue)">Ver ficha ${icon('arrow-right', 'icon-sm')}</span></div>
  </article>`;
}

export async function mount(view) {
  let alive = true;
  let active = 'high';
  let page = 1;
  let items = [];
  let total = 0;
  let counts = { high: 0, medium: 0, low: 0 };
  let thresholds = { high: 70, medium: 40 };

  const grid = $('#opp-grid', view);
  const state = $('#opp-state', view);
  const more = $('#opp-more', view);

  function renderTabs() {
    setHtml($('#opp-tabs', view), html`${PRIORITIES.map((p) => html`
      <button class="tab ${p.key === active ? 'active' : ''}" role="tab" aria-selected="${p.key === active}" data-tab="${p.key}">
        ${p.label} prioridade <span class="badge no-dot" data-tone="${p.tone}">${formatNumber(counts[p.key])}</span>
      </button>`)}`);
    const legend = { high: `Pontuação ≥ ${thresholds.high}`, medium: `Pontuação de ${thresholds.medium} a ${thresholds.high - 1}`, low: `Pontuação < ${thresholds.medium}` };
    $('#opp-legend', view).textContent = `${legend[active]} · exclui clientes fechados e perdidos`;
  }

  async function loadFacets() {
    const f = await api.facets();
    counts = f.priority_counts;
    thresholds = f.priority_thresholds || thresholds;
  }

  async function loadPage(reset) {
    if (reset) { page = 1; items = []; setHtml(grid, html`${Array.from({ length: 6 }, () => html`<div class="card opp-card"><div class="skeleton sk-line" style="width:60%"></div><div class="skeleton sk-line"></div><div class="skeleton sk-line" style="width:80%"></div></div>`)}`); }
    state.innerHTML = '';
    try {
      const res = await api.listLeads({ priority: active, active: 'true', sort: 'score_desc', page, page_size: PER_PAGE });
      if (!alive) return;
      items = reset ? res.items : [...items, ...res.items];
      total = res.total;
      grid.hidden = items.length === 0;
      setHtml(grid, html`${items.map((l, i) => card(l, i))}`);
      more.hidden = items.length >= total;
      if (items.length === 0) {
        setHtml(state, emptyState({
          icon: 'flame',
          title: `Nenhum lead de prioridade ${PRIORITY_BY_KEY[active].label.toLowerCase()}`,
          text: 'A prioridade é definida pela pontuação comercial de cada lead. Cadastre leads ou ajuste a pontuação para vê-los aqui.',
        }));
      }
      renderIcons();
    } catch (err) {
      if (!alive) return;
      grid.hidden = true;
      more.hidden = true;
      setHtml(state, errorState(err));
      renderIcons();
    }
  }

  async function refresh() {
    try { await loadFacets(); } catch { /* contadores são informativos */ }
    renderTabs();
    await loadPage(true);
  }

  view.addEventListener('click', async (e) => {
    const tab = e.target.closest('[data-tab]');
    if (tab) { active = tab.dataset.tab; renderTabs(); loadPage(true); return; }
    if (e.target.closest('[data-retry]')) { refresh(); return; }
    const c = e.target.closest('.opp-card[data-id]');
    if (c) openLeadDetail(c.dataset.id, { onChange: refresh });
  });
  view.addEventListener('keydown', (e) => {
    const c = e.target.closest?.('.opp-card[data-id]');
    if (c && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); openLeadDetail(c.dataset.id, { onChange: refresh }); }
  });
  more.addEventListener('click', () => withLoading(more, async () => { page += 1; await loadPage(false); }));

  renderTabs();
  await refresh();
  return () => { alive = false; };
}
