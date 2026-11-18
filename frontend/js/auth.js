// Sessão do usuário (Supabase Auth, intermediada pelo backend).
// O frontend nunca recebe chaves do Supabase: apenas o token do próprio usuário.

const KEY = 'gtech.session';

export class ApiError extends Error {
  constructor(message, { status = 0, code = 'error', details = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export function getSession() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || null;
  } catch {
    return null;
  }
}

function saveSession(data) {
  const session = {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    expires_at: Date.now() + (Number(data.expires_in) || 3600) * 1000,
    user: data.user,
  };
  try { localStorage.setItem(KEY, JSON.stringify(session)); } catch { /* armazenamento bloqueado */ }
  return session;
}

export function clearSession() {
  try { localStorage.removeItem(KEY); } catch { /* ignore */ }
}

/** Requisição simples ao backend sem token (login / refresh). */
async function post(path, body) {
  let res;
  try {
    res = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError('Não foi possível conectar ao servidor. Verifique se o backend está em execução.', { code: 'network' });
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const e = data.error || {};
    throw new ApiError(e.message || 'Falha na autenticação.', { status: res.status, code: e.code, details: e.details });
  }
  return data;
}

export async function login(email, password) {
  return saveSession(await post('/api/auth/login', { email, password }));
}

let refreshing = null;

/** Renova o token. Chamadas simultâneas compartilham a mesma requisição. */
export function refreshSession() {
  const current = getSession();
  if (!current?.refresh_token) return Promise.reject(new ApiError('Sessão expirada.', { status: 401, code: 'session_expired' }));
  if (!refreshing) {
    refreshing = post('/api/auth/refresh', { refresh_token: current.refresh_token })
      .then(saveSession)
      .catch((err) => {
        if (err.status === 401 || err.status === 400) clearSession();
        throw err;
      })
      .finally(() => { refreshing = null; });
  }
  return refreshing;
}

export async function logout() {
  const s = getSession();
  clearSession();
  if (s?.access_token) {
    try {
      await fetch('/api/auth/logout', { method: 'POST', headers: { Authorization: `Bearer ${s.access_token}` } });
    } catch { /* sair localmente já é suficiente */ }
  }
}
