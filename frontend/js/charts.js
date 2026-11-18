// Configuração padrão dos gráficos (Chart.js) no tema escuro do GTech Lead AI.
// Princípios: uma única série por gráfico (sem eixo duplo), marcas finas,
// grade discreta, tooltip no hover e cores vindas dos tokens do design system.
import { formatDay, formatNumber } from './utils.js';

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

let registry = [];

/** Destrói todos os gráficos criados (chamado pelo roteador ao trocar de página). */
export function destroyCharts() {
  registry.forEach((c) => c.destroy());
  registry = [];
}

function applyDefaults() {
  const C = window.Chart;
  if (!C || C.__gtech) return;
  C.defaults.color = css('--text-2');
  C.defaults.font.family = css('--font');
  C.defaults.font.size = 12;
  C.defaults.maintainAspectRatio = false;
  C.defaults.animation = { duration: 650, easing: 'easeOutQuart' };
  C.defaults.plugins.legend.display = false;
  C.defaults.plugins.tooltip = {
    ...C.defaults.plugins.tooltip,
    backgroundColor: '#0f1626',
    borderColor: css('--border-strong'),
    borderWidth: 1,
    titleColor: css('--text'),
    bodyColor: css('--text-2'),
    padding: 10,
    cornerRadius: 8,
    displayColors: false,
    titleFont: { weight: '600' },
  };
  C.__gtech = true;
}

const integerTicks = { precision: 0, callback: (v) => (Number.isInteger(v) ? formatNumber(v) : null) };

function register(canvas, config) {
  applyDefaults();
  const chart = new window.Chart(canvas, config);
  registry.push(chart);
  return chart;
}

/** Série temporal. `points` = [{date:'YYYY-MM-DD', count}] */
export function timeSeriesChart(canvas, points, { label = 'Leads', mode = 'day', type = 'line' } = {}) {
  const labels = points.map((p) => formatDay(p.date, mode));
  const data = points.map((p) => p.count);
  const color = css('--chart-1');
  const isBar = type === 'bar';

  const ctx = canvas.getContext('2d');
  const grad = ctx.createLinearGradient(0, 0, 0, canvas.clientHeight || 280);
  grad.addColorStop(0, 'rgba(57, 135, 229, 0.30)');
  grad.addColorStop(1, 'rgba(57, 135, 229, 0)');

  return register(canvas, {
    type: isBar ? 'bar' : 'line',
    data: {
      labels,
      datasets: [{
        label,
        data,
        borderColor: color,
        backgroundColor: isBar ? color : grad,
        fill: !isBar,
        borderWidth: 2,
        tension: 0.35,
        pointRadius: points.length > 45 ? 0 : 3,
        pointHoverRadius: 6,
        pointBackgroundColor: color,
        pointBorderColor: css('--card'),
        pointBorderWidth: 2,
        borderRadius: isBar ? { topLeft: 4, topRight: 4 } : 0,
        borderSkipped: false,
        maxBarThickness: 36,
      }],
    },
    options: {
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { grid: { display: false }, border: { color: css('--chart-axis') }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 10 } },
        y: { beginAtZero: true, grid: { color: css('--chart-grid') }, border: { display: false }, ticks: integerTicks },
      },
      plugins: {
        tooltip: { callbacks: { label: (c) => `${formatNumber(c.parsed.y)} ${c.parsed.y === 1 ? 'lead' : 'leads'}` } },
      },
    },
  });
}

/** Barras horizontais para ranking (segmento, região). `items` = [{label, count}] */
export function rankBarChart(canvas, items, { label = 'Leads' } = {}) {
  const color = css('--chart-1');
  return register(canvas, {
    type: 'bar',
    data: {
      labels: items.map((i) => i.label),
      datasets: [{
        label,
        data: items.map((i) => i.count),
        backgroundColor: color,
        hoverBackgroundColor: '#5598e7',
        borderRadius: { topRight: 4, bottomRight: 4 },
        borderSkipped: false,
        barThickness: 18,
      }],
    },
    options: {
      indexAxis: 'y',
      scales: {
        x: { beginAtZero: true, grid: { color: css('--chart-grid') }, border: { display: false }, ticks: integerTicks },
        y: { grid: { display: false }, border: { color: css('--chart-axis') }, ticks: { autoSkip: false } },
      },
      plugins: {
        tooltip: { callbacks: { label: (c) => `${formatNumber(c.parsed.x)} ${c.parsed.x === 1 ? 'lead' : 'leads'}` } },
      },
    },
  });
}
