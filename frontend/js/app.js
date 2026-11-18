// Ponto de entrada do frontend: decide entre configuração, login e aplicação.
import { api } from './api.js';
import { login, logout, getSession, clearSession } from './auth.js';
import { startRouter, stopRouter, reload } from './router.js';
import { openLeadForm } from './components/lead-form.js';
import { html, setHtml, $, initials } from './utils.js';
import { renderIcons, icon, toastError, withLoading } from './ui.js';

const authView = $('#auth-view');
const authCard = $('#auth-card');
const appEl = $('#app');

const BRAND = html`<div class="brand"><img src="assets/logo.svg" alt="" width="34" height="34">
  <div><div class="brand-name">GTech <span>Lead AI</span></div><div class="brand-tag">Inteligência comercial</div></div></div>`;

function showAuth(content) {
  stopRouter();
  appEl.hidden = true;
  authView.hidden = false;
  setHtml(authCard, html`${BRAND}${content}`);
  renderIcons();
}

// ---------------------------------------------------------------------------
// Telas de estado
// ---------------------------------------------------------------------------
function showBackendDown(message) {
  showAuth(html`
    <h1>Servidor indisponível</h1>
    <p class="muted" style="margin-top:6px">${message}</p>
    <div class="alert" data-tone="warning" style="margin-top:18px">${icon('triangle-alert')}<div>
      Abra o sistema pelo endereço do backend (por exemplo <b>http://localhost:8000</b>) depois de iniciá-lo com
      <code class="mono">uvicorn app.main:app --reload</code> na pasta <b>backend</b>.</div></div>
    <button class="btn btn-primary" id="retry" style="margin-top:18px;width:100%">${icon('refresh-cw', 'icon-sm')}Tentar novamente</button>`);
  $('#retry').addEventListener('click', boot);
}

function showSetup(health) {
  showAuth(html`
    <h1>Configure o Supabase</h1>
    <p class="muted" style="margin-top:6px">${health.message || 'O backend ainda não está conectado a um projeto Supabase.'}</p>
    <ol class="setup-steps">
      <li>Crie um projeto em <b>supabase.com</b>.</li>
      <li>No <b>SQL Editor</b>, execute <code>database/schema.sql</code> e depois <code>database/policies.sql</code>.</li>
      <li>Em <b>Authentication → Users</b>, crie seu usuário (e-mail e senha).</li>
      <li>Copie <code>backend/.env.example</code> para <code>backend/.env</code> e preencha <code>SUPABASE_URL</code> e <code>SUPABASE_ANON_KEY</code> (Project Settings → API).</li>
      <li>Reinicie o backend e clique em verificar.</li>
    </ol>
    <button class="btn btn-primary" id="retry" style="margin-top:20px;width:100%">${icon('refresh-cw', 'icon-sm')}Verificar novamente</button>`);
  $('#retry').addEventListener('click', boot);
}

function showLogin(notice = '') {
  showAuth(html`
    <h1>Entrar</h1>
    <p class="muted">Acesse o painel de gestão de leads.</p>
    ${notice ? html`<div class="alert" data-tone="warning" style="margin-top:16px">${icon('info')}<div>${notice}</div></div>` : ''}
    <form id="login-form" novalidate>
      <div class="alert" data-tone="error" id="login-error" hidden></div>
      <div class="field"><label for="email">E-mail</label>
        <input class="input" id="email" type="email" autocomplete="username" required autofocus></div>
      <div class="field"><label for="password">Senha</label>
        <input class="input" id="password" type="password" autocomplete="current-password" required></div>
      <button class="btn btn-primary" type="submit" id="login-btn" style="width:100%;height:42px">Entrar</button>
    </form>`);

  const form = $('#login-form');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const errBox = $('#login-error');
    errBox.hidden = true;
    const email = $('#email').value.trim();
    const password = $('#password').value;
    if (!email || !password) {
      setHtml(errBox, html`${icon('circle-alert')}<div>Informe e-mail e senha.</div>`);
      errBox.hidden = false;
      renderIcons();
      return;
    }
    try {
      await withLoading($('#login-btn'), () => login(email, password));
      await enterApp();
    } catch (err) {
      setHtml(errBox, html`${icon('circle-alert')}<div>${err.message}</div>`);
      errBox.hidden = false;
      renderIcons();
    }
  });
}

// ---------------------------------------------------------------------------
// Aplicação
// ---------------------------------------------------------------------------
async function enterApp() {
  const me = await api.get('/me');
  $('#user-name').textContent = me.full_name || me.email;
  $('#user-email').textContent = me.email;
  $('#user-avatar').textContent = initials(me.full_name || me.email);

  authView.hidden = true;
  appEl.hidden = false;
  renderIcons();
  startRouter();
}

async function boot() {
  let health;
  try {
    health = await api.health();
  } catch {
    showBackendDown('Não foi possível se comunicar com o backend do GTech Lead AI.');
    return;
  }
  if (!health.supabase_configured) {
    showSetup(health);
    return;
  }
  if (!getSession()) {
    showLogin();
    return;
  }
  try {
    await enterApp();
  } catch (err) {
    if (err.code === 'network') showBackendDown(err.message);
    else if (err.status === 503) showSetup({ message: err.message });
    else { clearSession(); showLogin('Sua sessão expirou. Entre novamente.'); }
  }
}

// ---------------------------------------------------------------------------
// Eventos globais
// ---------------------------------------------------------------------------
$('#logout-btn').addEventListener('click', async () => {
  await logout();
  showLogin();
});

$('#new-lead-btn').addEventListener('click', async () => {
  try {
    const saved = await openLeadForm();
    if (saved) reload();
  } catch (err) { toastError(err); }
});

$('#menu-toggle').addEventListener('click', () => {
  const sidebar = $('#sidebar');
  const open = sidebar.classList.toggle('open');
  $('.sidebar-scrim')?.remove();
  if (open) {
    const scrim = document.createElement('div');
    scrim.className = 'sidebar-scrim';
    scrim.addEventListener('click', () => { sidebar.classList.remove('open'); scrim.remove(); });
    document.body.appendChild(scrim);
  }
});

window.addEventListener('auth:expired', () => showLogin('Sua sessão expirou. Entre novamente.'));

boot();
