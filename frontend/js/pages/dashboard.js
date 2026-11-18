// Dashboard: todos os números vêm de GET /api/dashboard (dados reais do banco).
import { api } from '../api.js';
import { $, html, setHtml, formatNumber, formatPercent, timeAgo, formatDateTime } from '../utils.js';
import { renderIcons, icon, errorState, emptyState, statusBadge, priorityBadge, scoreBar, toastError } from '../ui.js';
import { timeSeriesChart, rankBarChart, destroyCharts } from '../charts.js';
import { openLeadDetail } from '../components/lead-detail.js';
import { openLeadForm } from '../components/lead-form.js';
import { ACTIVITY_ICONS } from '../constants.js';

const KPI_DEFS = [
  { key: 'total', label: 'Total de leads', icon: 'users', tone: '', href: '#/leads', foot: () => 'Todos os cadastros' },
  { key: 'new', label: 'Leads novos', icon: 'sparkles', tone: 'violet', href: '#/leads?status=new', foot: () => 'Aguardando análise' },
  { key: 'high_priority', label: 'Alta prioridade', icon: 'flame', tone: 'red', href: '#/leads?priority=high&sort=score_desc', foot: () => 'Maior potencial comercial' },
  { key: 'contacted', label: 'Contatados', icon: 'phone-call', tone: '', href: '#/leads?status=contacted', foot: () => 'Contato realizado' },
  { key: 'interested', label: 'Interessados', icon: 'thumbs-up', tone: 'cyan', href: '#/leads?status=interested', foot: () => 'Demonstraram interesse' },
  { key: 'proposal_sent', label: 'Propostas enviadas', icon: 'file-text', tone: 'yellow', href: '#/leads?status=proposal_sent', foot: () => 'Aguardando resposta' },
  { key: 'closed_won', label: 'Clientes fechados', icon: 'badge-check', tone: 'green', href: '#/leads?status=closed_won', foot: () => 'Negócios ganhos' },
];

function kpiSkeleton() {
  return html`${KPI_DEFS.map(() => html`<div class="card kpi"><div class="skeleton sk-line" style="width:55%"></div><div class="skeleton" style="height:30px;width:40%"></div><div class="skeleton sk-line" style="width:70%"></div></div>`)}`;
}

function renderKpis(totals) {
  return html`${KPI_DEFS.map((k, i) => html`
    <a class="card kpi" data-tone="${k.tone}" href="${k.href}" style="animation-delay:${i * 40}ms">
      <div class="kpi-top"><span class="kpi-label">${k.label}</span><span class="kpi-icon">${icon(k.icon)}</span></div>
      <div class="kpi-value num">${formatNumber(totals[k.key])}</div>
      <div class="kpi-foot">${k.key === 'total' ? k.foot() : totals.total ? `${formatPercent((totals[k.key] / totals.total) * 100, 0)} do total` : k.foot()}</div>
    </a>`)}`;
}

function renderConversion(data) {
  const t = data.totals;
  const open = Math.max(0, t.total - t.closed_won - t.lost);
  return html`
    <div class="row" style="gap:24px;flex-wrap:nowrap">
      <div class="ring-wrap">
        <div class="ring" style="--p:${Math.min(100, data.conversion_rate)}"></div>
        <div class="ring-label"><b class="num">${formatPercent(data.conversion_rate)}</b><span>conversão</span></div>
      </div>
      <div class="stack" style="gap:10px;flex:1;min-width:0">
        <div class="row" style="justify-content:space-between"><span class="muted">Clientes fechados</span><b class="num" style="color:var(--green)">${formatNumber(t.closed_won)}</b></div>
        <div class="row" style="justify-content:space-between"><span class="muted">Em negociação</span><b class="num">${formatNumber(open)}</b></div>
        <div class="row" style="justify-content:space-between"><span class="muted">Perdidos</span><b class="num" style="color:var(--red)">${formatNumber(t.lost)}</b></div>
      </div>
    </div>
    <p class="faint" style="font-size:12.5px;margin-top:16px">${t.total ? `${formatNumber(t.closed_won)} de ${formatNumber(t.total)} leads viraram clientes.` : 'A taxa será calculada assim que houver leads cadastrados.'}</p>`;
}

function renderActivities(items) {
  if (!items.length) return emptyState({ icon: 'history', title: 'Sem atividades ainda', text: 'Cadastros, mudanças de estágio e anotações aparecerão aqui.' });
  return html`<ul class="list">${items.map((a) => html`
    <li class="clickable" data-lead="${a.lead_id}">
      <span class="tl-dot" data-type="${a.type}">${icon(ACTIVITY_ICONS[a.type] || 'circle')}</span>
      <div class="tl-text" style="min-width:0">
        <div><b>${a.lead_name || 'Lead removido'}</b></div>
        <div class="muted truncate" style="white-space:normal">${a.description}</div>
        <div class="tl-time" title="${formatDateTime(a.created_at)}">${timeAgo(a.created_at)}</div>
      </div>
    </li>`)}</ul>`;
}

function renderLatest(leads) {
  if (!leads.length) return emptyState({ icon: 'users', title: 'Nenhum lead cadastrado', text: 'Cadastre seu primeiro lead para começar a acompanhar o funil comercial.', action: html`<button class="btn btn-primary" data-new-lead style="margin-top:8px">${icon('plus', 'icon-sm')}Cadastrar lead</button>` });
  return html`<table class="table">
    <thead><tr><th>Empresa</th><th class="hide-sm">Segmento</th><th class="hide-sm">Cidade</th><th>Estágio</th><th class="hide-sm">Prioridade</th><th class="hide-sm">Pontuação</th><th>Cadastro</th></tr></thead>
    <tbody>${leads.map((l) => html`
      <tr class="clickable" data-lead="${l.id}">
        <td><div class="cell-main">${l.company_name}</div><div class="cell-sub">${l.contact_name || ''}</div></td>
        <td class="hide-sm">${l.segment || '—'}</td>
        <td class="hide-sm">${[l.city, l.state].filter(Boolean).join(' / ') || '—'}</td>
        <td>${statusBadge(l.status)}</td>
        <td class="hide-sm">${priorityBadge(l.priority)}</td>
        <td class="hide-sm">${scoreBar(l.score, l.priority)}</td>
        <td class="nowrap muted">${timeAgo(l.created_at)}</td>
      </tr>`)}</tbody></table>`;
}

export async function mount(view) {
  const state = $('#dash-state', view);
  const daysSel = $('#dash-days', view);
  setHtml($('#kpis', view), kpiSkeleton());

  let alive = true;

  async function load() {
    state.innerHTML = '';
    try {
      const data = await api.get('/dashboard', { days: daysSel.value });
      if (!alive) return;
      const hasLeads = data.totals.total > 0;

      setHtml($('#kpis', view), renderKpis(data.totals));
      setHtml($('#conversion', view), renderConversion(data));
      setHtml($('#activities', view), renderActivities(data.recent_activities));
      setHtml($('#latest', view), renderLatest(data.latest_leads));

      destroyCharts();
      const periodEmpty = $('#chart-period-empty', view);
      const hasPeriod = data.leads_by_period.some((p) => p.count > 0);
      periodEmpty.hidden = hasPeriod;
      periodEmpty.textContent = hasLeads ? 'Nenhum lead cadastrado neste período.' : 'Os gráficos aparecem assim que houver leads cadastrados.';
      if (hasPeriod) timeSeriesChart($('#chart-period', view), data.leads_by_period, { label: 'Leads cadastrados' });

      const segEmpty = $('#chart-segment-empty', view);
      segEmpty.hidden = data.leads_by_segment.length > 0;
      segEmpty.textContent = 'Sem segmentos cadastrados ainda.';
      if (data.leads_by_segment.length) {
        rankBarChart($('#chart-segment', view), data.leads_by_segment.map((s) => ({ label: s.segment, count: s.count })));
      }
      renderIcons();
    } catch (err) {
      if (!alive) return;
      setHtml($('#kpis', view), '');
      setHtml(state, errorState(err));
      renderIcons();
      $('[data-retry]', state)?.addEventListener('click', load);
    }
  }

  daysSel.addEventListener('change', load);
  $('#dash-refresh', view).addEventListener('click', load);
  view.addEventListener('click', async (e) => {
    const row = e.target.closest('[data-lead]');
    if (row) { openLeadDetail(row.dataset.lead, { onChange: load }); return; }
    if (e.target.closest('[data-new-lead]')) {
      try { if (await openLeadForm()) load(); } catch (err) { toastError(err); }
    }
  });

  await load();
  return () => { alive = false; };
}
