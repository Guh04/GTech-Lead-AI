// Utilitários gerais: template HTML seguro, formatação e helpers.

// ---------------------------------------------------------------------------
// Template HTML com escape automático (proteção contra XSS).
// Todo valor interpolado é escapado, a não ser que venha de outro `html` ou `raw`.
// Importante porque os leads (no futuro) virão de fontes externas / agente de IA.
// ---------------------------------------------------------------------------
class SafeHtml {
  constructor(value) { this.value = value; }
  toString() { return this.value; }
}

const ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

export function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => ESCAPES[c]);
}

function renderValue(v) {
  if (v instanceof SafeHtml) return v.value;
  if (Array.isArray(v)) return v.map(renderValue).join('');
  if (v === null || v === undefined || v === false) return '';
  return esc(v);
}

export function html(strings, ...values) {
  let out = '';
  strings.forEach((s, i) => {
    out += s;
    if (i < values.length) out += renderValue(values[i]);
  });
  return new SafeHtml(out);
}

/** Marca uma string como HTML confiável (use apenas para conteúdo produzido por nós). */
export const raw = (s) => new SafeHtml(String(s));

/** Atribui HTML seguro a um elemento. */
export function setHtml(el, content) {
  el.innerHTML = content instanceof SafeHtml ? content.value : esc(content);
  return el;
}

// ---------------------------------------------------------------------------
// DOM
// ---------------------------------------------------------------------------
export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

export function debounce(fn, wait = 300) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
}

// ---------------------------------------------------------------------------
// Formatação
// ---------------------------------------------------------------------------
const nf = new Intl.NumberFormat('pt-BR');
export const formatNumber = (n) => nf.format(Number(n) || 0);

export function formatPercent(n, digits = 1) {
  return `${(Number(n) || 0).toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: digits })}%`;
}

const dateFmt = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
const dateTimeFmt = new Intl.DateTimeFormat('pt-BR', {
  day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
});

export function formatDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '—' : dateFmt.format(d);
}

export function formatDateTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '—' : dateTimeFmt.format(d);
}

const rtf = new Intl.RelativeTimeFormat('pt-BR', { numeric: 'auto' });
export function timeAgo(iso) {
  if (!iso) return '';
  const diff = (new Date(iso).getTime() - Date.now()) / 1000;
  const abs = Math.abs(diff);
  if (abs < 60) return 'agora mesmo';
  if (abs < 3600) return rtf.format(Math.round(diff / 60), 'minute');
  if (abs < 86400) return rtf.format(Math.round(diff / 3600), 'hour');
  if (abs < 86400 * 30) return rtf.format(Math.round(diff / 86400), 'day');
  return formatDate(iso);
}

/** "YYYY-MM-DD" -> Date local (evita deslocamento de fuso). */
export function parseDay(str) {
  const [y, m, d] = String(str).split('-').map(Number);
  return new Date(y, (m || 1) - 1, d || 1);
}

export function formatDay(str, mode = 'day') {
  const d = parseDay(str);
  if (mode === 'month') return d.toLocaleDateString('pt-BR', { month: 'short', year: '2-digit' }).replace('.', '');
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
}

/** Telefone brasileiro a partir de dígitos. */
export function formatPhone(digits) {
  if (!digits) return '';
  let d = String(digits).replace(/\D/g, '');
  let prefix = '';
  if ((d.length === 12 || d.length === 13) && d.startsWith('55')) { prefix = '+55 '; d = d.slice(2); }
  if (d.length === 11) return `${prefix}(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
  if (d.length === 10) return `${prefix}(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
  return prefix + d;
}

export function whatsappLink(digits) {
  if (!digits) return null;
  const d = String(digits).replace(/\D/g, '');
  const full = d.length === 10 || d.length === 11 ? `55${d}` : d;
  return `https://wa.me/${full}`;
}

export const instagramLink = (handle) => (handle ? `https://instagram.com/${encodeURIComponent(handle)}` : null);

/** Só devolve URLs http(s); qualquer outra coisa (ex.: javascript:) vira null. */
export function safeUrl(url) {
  try {
    const u = new URL(url);
    return u.protocol === 'http:' || u.protocol === 'https:' ? u.href : null;
  } catch {
    return null;
  }
}

export function displayUrl(url) {
  return String(url || '').replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '');
}

export function initials(text) {
  const parts = String(text || '?').replace(/@.*/, '').split(/[\s._-]+/).filter(Boolean);
  return ((parts[0]?.[0] || '?') + (parts[1]?.[0] || '')).toUpperCase();
}

/** Parâmetros da URL do hash: "#/leads?status=new" -> { status: 'new' }. */
export function hashParams() {
  const q = location.hash.split('?')[1] || '';
  return Object.fromEntries(new URLSearchParams(q));
}

/** Monta query string ignorando valores vazios. */
export function buildQuery(params) {
  const q = new URLSearchParams();
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') q.set(k, v);
  });
  const s = q.toString();
  return s ? `?${s}` : '';
}
