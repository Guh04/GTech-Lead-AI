// Roteador por hash (#/dashboard). Carrega o HTML da página (frontend/pages/*.html)
// e o módulo JS correspondente (frontend/js/pages/*.js) sem recarregar a aplicação.
import { $, $$, setHtml, html } from './utils.js';
import { renderIcons, errorState, spinnerBlock } from './ui.js';
import { destroyCharts } from './charts.js';

export const ROUTES = {
  dashboard: { title: 'Dashboard' },
  leads: { title: 'Leads' },
  oportunidades: { title: 'Oportunidades' },
  pipeline: { title: 'Pipeline comercial' },
  prospeccao: { title: 'Prospecção' },
  relatorios: { title: 'Relatórios' },
};
const DEFAULT_ROUTE = 'dashboard';

const fragmentCache = new Map();
let current = null; // { name, unmount }
let navToken = 0;

function currentName() {
  const name = location.hash.replace(/^#\/?/, '').split(/[/?]/)[0];
  return ROUTES[name] ? name : DEFAULT_ROUTE;
}

async function loadFragment(name) {
  if (!fragmentCache.has(name)) {
    const res = await fetch(`pages/${name}.html`);
    if (!res.ok) throw new Error(`Página "${name}" não encontrada.`);
    fragmentCache.set(name, await res.text());
  }
  return fragmentCache.get(name);
}

export async function navigate() {
  const name = currentName();
  const token = ++navToken;
  const view = $('#view');

  // Limpa a página anterior
  try { await current?.unmount?.(); } catch (e) { console.error(e); }
  destroyCharts();
  current = null;

  // Marca menu ativo e título
  $$('.nav-link').forEach((a) => a.classList.toggle('active', a.dataset.route === name));
  $('#topbar-page').textContent = ROUTES[name].title;
  document.title = `${ROUTES[name].title} · GTech Lead AI`;
  $('#sidebar').classList.remove('open');
  $('.sidebar-scrim')?.remove();

  setHtml(view, spinnerBlock());
  try {
    const [fragment, mod] = await Promise.all([loadFragment(name), import(`./pages/${name}.js`)]);
    if (token !== navToken) return; // usuário já navegou para outra página
    // Contêiner novo a cada navegação: listeners da página anterior desaparecem junto com ele.
    const root = document.createElement('div');
    root.className = 'page-root page-enter';
    root.innerHTML = fragment;
    view.replaceChildren(root);
    renderIcons();
    const unmount = await mod.mount(root, { reload });
    if (token !== navToken) { unmount?.(); return; }
    current = { name, unmount };
    renderIcons();
    window.scrollTo({ top: 0 });
  } catch (err) {
    if (token !== navToken) return;
    console.error(err);
    setHtml(view, errorState(err));
    renderIcons();
    $('[data-retry]', view)?.addEventListener('click', () => navigate());
  }
}

/** Remonta a página atual (usado após criar/editar leads). */
export function reload() {
  return navigate();
}

let navBound = false;

export function startRouter() {
  window.addEventListener('hashchange', navigate);
  if (!navBound) {
    navBound = true;
    // Clicar no item de menu da página atual atualiza os dados (o hash não muda, então não há navegação).
    $('#nav').addEventListener('click', (e) => {
      const link = e.target.closest('a[data-route]');
      if (link && link.dataset.route === currentName()) navigate();
    });
  }
  if (!location.hash) location.hash = `#/${DEFAULT_ROUTE}`;
  else navigate();
}

export function stopRouter() {
  window.removeEventListener('hashchange', navigate);
  navToken++;
  current?.unmount?.();
  current = null;
  destroyCharts();
}

export { html };
