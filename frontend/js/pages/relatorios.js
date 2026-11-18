// Relatórios: todos os dados vêm de GET /api/reports (agregações sobre o banco).
import { api } from '../api.js';
import { $, html, setHtml, formatNumber, formatPercent, formatDate, formatDateTime } from '../utils.js';
import { renderIcons, icon, errorState, emptyState, statusBadge } from '../ui.js';
import { timeSeriesChart, rankBarChart, destroyCharts } from '../charts.js';
import { openLeadDetail } from '../components/lead-detail.js';
import { STATUS_BY_KEY } from '../constants.js';

// Estágios 1–5: rampa sequencial azul (ordem do funil). Fechado/Perdido: cores de status.
const FUNNEL_COLORS = {
  new: '#86b6ef', analyzed: '#5598e7', contacted: '#3987e5', interested: '#256abf', proposal_sent: '#1c5cab',
  closed_won: '#22c55e', lost: '#ef4444',
};
const GRANULARITY = { day: 'por dia', week: 'por semana', month: 'por mês' };
const SEARCH_STATUS = { running: ['Em execução', 'blue'], completed: ['Concluída', 'green'], failed: ['Falhou', 'red'] };

function kpi(label, value, foot, tone = '', iconName = 'users') {
  return html`<div class="card kpi" data-tone="${tone}"><div class="kpi-top"><span class="kpi-label">${label}</span><span class="kpi-icon">${icon(iconName)}</span></div>
    <div class="kpi-value num">${value}</div><div class="kpi-foot">${foot}</div></div>`;
}

function renderFunnel(funnel) {
  const max = Math.max(1, ...funnel.map((f) => f.count));
  return html`<div class="funnel">${funnel.map((f) => html`
    <div class="funnel-row"><span class="muted">${STATUS_BY_KEY[f.status].label}</span>
      <div class="funnel-bar"><i style="width:${(f.count / max) * 100}%;background:${FUNNEL_COLORS[f.status]}"></i></div>
      <b class="num">${formatNumber(f.count)}</b></div>`)}</div>`;
}

export async function mount(view) {
  let alive = true;
  const daysSel = $('#rep-days', view);
  const state = $('#rep-state', view);

  async function load() {
    state.innerHTML = '';
    setHtml($('#rep-kpis', view), html`${[0, 1, 2, 3].map(() => html`<div class="card kpi"><div class="skeleton sk-line" style="width:50%"></div><div class="skeleton" style="height:30px;width:40%"></div></div>`)}`);
    try {
      const d = await api.get('/reports', { days: daysSel.value });
      if (!alive) return;
      const c = d.conversion;
      const days = Number(daysSel.value);

      $('#rep-sub', view).textContent = days
        ? `Leads cadastrados nos últimos ${days} dias — ${formatNumber(d.total_in_period)} no período.`
        : `Todos os leads cadastrados — ${formatNumber(d.total_in_period)} no total.`;
      $('#rep-period-sub', view).textContent = `Agrupado ${GRANULARITY[d.granularity]}`;

      setHtml($('#rep-kpis', view), html`
        ${kpi('Leads no período', formatNumber(c.total), 'Cadastrados no período', '', 'users')}
        ${kpi('Clientes fechados', formatNumber(c.closed_won), 'Negócios ganhos', 'green', 'badge-check')}
        ${kpi('Taxa de conversão', formatPercent(c.conversion_rate), 'Fechados ÷ total de leads', 'cyan', 'trending-up')}
        ${kpi('Taxa de ganho', c.win_rate === null ? '—' : formatPercent(c.win_rate), c.win_rate === null ? 'Sem negociações encerradas' : 'Fechados ÷ (fechados + perdidos)', 'yellow', 'target')}`);

      setHtml($('#rep-funnel', view), c.total ? renderFunnel(d.funnel) : emptyState({ icon: 'filter', title: 'Sem dados', text: 'O funil aparece quando houver leads no período.' }));

      destroyCharts();
      const has = d.leads_by_period.some((p) => p.count > 0);
      $('#rep-period-empty', view).hidden = has;
      if (has) timeSeriesChart($('#rep-chart-period', view), d.leads_by_period, { label: 'Leads', mode: d.granularity === 'month' ? 'month' : 'day', type: 'bar' });

      $('#rep-segment-empty', view).hidden = d.leads_by_segment.length > 0;
      if (d.leads_by_segment.length) rankBarChart($('#rep-chart-segment', view), d.leads_by_segment.map((s) => ({ label: s.segment, count: s.count })));
      $('#rep-region-empty', view).hidden = d.leads_by_region.length > 0;
      if (d.leads_by_region.length) rankBarChart($('#rep-chart-region', view), d.leads_by_region.map((r) => ({ label: r.state, count: r.count })));

      setHtml($('#rep-closed', view), d.closed_clients.length
        ? html`<table class="table"><thead><tr><th>Empresa</th><th class="hide-sm">Segmento</th><th>Fechado em</th></tr></thead><tbody>
            ${d.closed_clients.map((l) => html`<tr class="clickable" data-lead="${l.id}"><td><div class="cell-main">${l.company_name}</div><div class="cell-sub">${[l.city, l.state].filter(Boolean).join(' / ')}</div></td>
            <td class="hide-sm">${l.segment || '—'}</td><td class="nowrap muted">${formatDate(l.status_updated_at)}</td></tr>`)}</tbody></table>`
        : emptyState({ icon: 'badge-check', title: 'Nenhum cliente fechado', text: 'Leads movidos para “Cliente fechado” no pipeline aparecem aqui.' }));

      setHtml($('#rep-history', view), d.prospecting_history.length
        ? html`<table class="table"><thead><tr><th>Data</th><th>Região</th><th>Status</th><th>Leads</th></tr></thead><tbody>
            ${d.prospecting_history.map((s) => html`<tr><td class="nowrap muted">${formatDateTime(s.created_at)}</td><td>${s.region}${s.state ? ` / ${s.state}` : ''}</td>
            <td><span class="badge" data-tone="${(SEARCH_STATUS[s.status] || [])[1] || 'slate'}">${(SEARCH_STATUS[s.status] || [s.status])[0]}</span></td><td class="num">${formatNumber(s.inserted_count)}</td></tr>`)}</tbody></table>`
        : emptyState({ icon: 'history', title: 'Sem pesquisas', text: 'O histórico de pesquisas de prospecção aparecerá aqui.' }));
      renderIcons();
    } catch (err) {
      if (!alive) return;
      setHtml($('#rep-kpis', view), '');
      setHtml(state, errorState(err));
      renderIcons();
      $('[data-retry]', state)?.addEventListener('click', load);
    }
  }

  daysSel.addEventListener('change', load);
  $('#rep-refresh', view).addEventListener('click', load);
  view.addEventListener('click', (e) => {
    const row = e.target.closest('[data-lead]');
    if (row) openLeadDetail(row.dataset.lead, { onChange: load });
  });

  await load();
  return () => { alive = false; };
}
