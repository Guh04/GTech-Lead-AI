// Componentes de interface compartilhados: toasts, modais, confirmação, drawer e badges.
import { html, setHtml, raw, esc, $ } from './utils.js';
import { PRIORITY_BY_KEY, STATUS_BY_KEY, LANDING_BY_KEY } from './constants.js';

/** Converte <i data-lucide="..."> em SVG. Seguro de chamar várias vezes. */
export function renderIcons() {
  if (window.lucide) window.lucide.createIcons();
}

export const icon = (name, cls = '') => html`<i data-lucide="${name}" class="icon ${cls}"></i>`;

// ---------------------------------------------------------------------------
// Toasts
// ---------------------------------------------------------------------------
const TOAST_ICON = { success: 'circle-check', error: 'circle-alert', warning: 'triangle-alert', info: 'info' };

export function toast(message, tone = 'info', title = '') {
  const host = $('#toasts');
  const el = document.createElement('div');
  el.className = 'toast';
  el.dataset.tone = tone;
  el.setAttribute('role', tone === 'error' ? 'alert' : 'status');
  setHtml(el, html`${icon(TOAST_ICON[tone] || 'info')}<div>${title ? html`<strong>${title}</strong>` : ''}<span>${message}</span></div>`);
  host.appendChild(el);
  renderIcons();
  const ttl = tone === 'error' ? 7000 : 4000;
  const close = () => {
    el.classList.add('leaving');
    setTimeout(() => el.remove(), 240);
  };
  setTimeout(close, ttl);
  el.addEventListener('click', close);
}
export const toastOk = (m) => toast(m, 'success');
export const toastError = (err) => toast(err?.message || String(err), 'error');

// ---------------------------------------------------------------------------
// Modal genérico
// ---------------------------------------------------------------------------
const root = () => $('#overlay-root');

/**
 * Abre um modal. Retorna { el, close }.
 * `onClose` é chamado uma única vez quando o modal fecha (por qualquer motivo).
 */
export function openModal({ title, body, footer, size = '', onClose }) {
  const backdrop = document.createElement('div');
  backdrop.className = 'modal-backdrop';
  setHtml(backdrop, html`
    <div class="modal ${size}" role="dialog" aria-modal="true" aria-label="${title}">
      <div class="modal-head">
        <h2>${title}</h2>
        <button class="btn btn-ghost btn-icon btn-sm" data-close aria-label="Fechar">${icon('x')}</button>
      </div>
      <div class="modal-body" data-slot="body"></div>
      ${footer ? html`<div class="modal-foot" data-slot="foot"></div>` : ''}
    </div>`);
  root().appendChild(backdrop);
  const previouslyFocused = document.activeElement;

  const bodySlot = $('[data-slot="body"]', backdrop);
  if (body) setHtml(bodySlot, body);
  const footSlot = $('[data-slot="foot"]', backdrop);
  if (footer && footSlot) setHtml(footSlot, footer);
  renderIcons();

  let closed = false;
  const close = (result) => {
    if (closed) return;
    closed = true;
    document.removeEventListener('keydown', onKey);
    backdrop.remove();
    previouslyFocused?.focus?.();
    onClose?.(result);
  };
  const onKey = (e) => { if (e.key === 'Escape') close(); };
  document.addEventListener('keydown', onKey);
  // Fecha só se o clique começou e terminou no fundo (evita fechar ao selecionar texto).
  let downOnBackdrop = false;
  backdrop.addEventListener('mousedown', (e) => { downOnBackdrop = e.target === backdrop; });
  backdrop.addEventListener('click', (e) => {
    if (e.target === backdrop && downOnBackdrop) close();
    if (e.target.closest('[data-close]')) close();
  });

  const focusable = backdrop.querySelector('input, select, textarea, button:not([data-close])');
  focusable?.focus();
  return { el: backdrop, bodySlot, footSlot, close };
}

/** Confirmação (ex.: exclusão). Resolve true/false. */
export function confirmDialog({ title, message, confirmLabel = 'Confirmar', danger = false, detail = '' }) {
  return new Promise((resolve) => {
    let decided = false;
    const m = openModal({
      title,
      size: 'sm',
      body: html`
        <div class="confirm-icon">${icon(danger ? 'trash-2' : 'circle-help')}</div>
        <p>${message}</p>
        ${detail ? html`<p class="muted" style="margin-top:8px">${detail}</p>` : ''}`,
      footer: html`
        <button class="btn" data-act="cancel">Cancelar</button>
        <button class="btn ${danger ? 'btn-danger-solid' : 'btn-primary'}" data-act="ok">${confirmLabel}</button>`,
      onClose: () => { if (!decided) resolve(false); },
    });
    m.el.addEventListener('click', (e) => {
      const act = e.target.closest('[data-act]')?.dataset.act;
      if (!act) return;
      decided = true;
      resolve(act === 'ok');
      m.close();
    });
    $('[data-act="cancel"]', m.el)?.focus();
  });
}

// ---------------------------------------------------------------------------
// Drawer lateral
// ---------------------------------------------------------------------------
export function openDrawer({ onClose } = {}) {
  const scrim = document.createElement('div');
  scrim.className = 'drawer-backdrop';
  const panel = document.createElement('aside');
  panel.className = 'drawer';
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-modal', 'true');
  root().append(scrim, panel);
  const previouslyFocused = document.activeElement;

  let closed = false;
  const close = () => {
    if (closed) return;
    closed = true;
    document.removeEventListener('keydown', onKey);
    scrim.remove();
    panel.remove();
    previouslyFocused?.focus?.();
    onClose?.();
  };
  const onKey = (e) => {
    // Não fecha o drawer se houver um modal por cima.
    if (e.key === 'Escape' && !$('.modal-backdrop')) close();
  };
  document.addEventListener('keydown', onKey);
  scrim.addEventListener('click', close);
  return { panel, close };
}

// ---------------------------------------------------------------------------
// Peças visuais
// ---------------------------------------------------------------------------
export function statusBadge(key) {
  const s = STATUS_BY_KEY[key];
  return s ? html`<span class="badge" data-tone="${s.tone}">${s.label}</span>` : html`<span class="badge">${key}</span>`;
}

export function priorityBadge(key) {
  const p = PRIORITY_BY_KEY[key];
  return p ? html`<span class="badge" data-tone="${p.tone}">${p.label}</span>` : '';
}

export function landingBadge(key) {
  const l = LANDING_BY_KEY[key];
  return l ? html`<span class="badge" data-tone="${l.tone}" title="${l.hint}">${l.label}</span>` : '';
}

export function scoreBar(score, priority) {
  const s = Math.max(0, Math.min(100, Number(score) || 0));
  return html`<span class="score" data-priority="${priority}" title="Pontuação comercial: ${s}/100"><span class="score-bar"><i style="width:${s}%"></i></span><b>${s}</b></span>`;
}

export function emptyState({ icon: ic = 'inbox', title, text = '', action = '' }) {
  return html`<div class="empty"><div class="empty-icon">${icon(ic, 'icon-lg')}</div><h3>${title}</h3>${text ? html`<p>${text}</p>` : ''}${action}</div>`;
}

export function errorState(err, retryLabel = 'Tentar novamente') {
  return html`<div class="empty"><div class="empty-icon" style="background:var(--red-soft);color:var(--red)">${icon('circle-alert', 'icon-lg')}</div>
    <h3>Não foi possível carregar</h3><p>${err?.message || 'Ocorreu um erro inesperado.'}</p>
    <button class="btn" data-retry style="margin-top:8px">${icon('refresh-cw', 'icon-sm')}${retryLabel}</button></div>`;
}

export const spinnerBlock = () => html`<div class="page-loading"><div class="spinner"></div></div>`;

export function skeletonRows(n = 5, cols = 5) {
  return html`${Array.from({ length: n }, () => html`<tr>${Array.from({ length: cols }, () => html`<td><div class="skeleton sk-line" style="width:${60 + Math.random() * 35}%"></div></td>`)}</tr>`)}`;
}

/** Executa `fn` com o botão em estado de carregamento. */
export async function withLoading(btn, fn) {
  if (!btn) return fn();
  btn.classList.add('is-loading');
  btn.disabled = true;
  try {
    return await fn();
  } finally {
    btn.classList.remove('is-loading');
    btn.disabled = false;
  }
}

export { esc };
