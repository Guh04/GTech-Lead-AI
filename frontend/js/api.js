// Cliente da API do backend (FastAPI).
import { ApiError, getSession, refreshSession, clearSession } from './auth.js';
import { buildQuery } from './utils.js';

async function send(method, path, { body, params } = {}, retry = true) {
  const session = getSession();
  const headers = { Accept: 'application/json' };
  if (session?.access_token) headers.Authorization = `Bearer ${session.access_token}`;
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  let res;
  try {
    res = await fetch(`/api${path}${buildQuery(params)}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError('Não foi possível conectar ao servidor. Verifique sua conexão e se o backend está em execução.', { code: 'network' });
  }

  // Token vencido: tenta renovar uma vez e repete a chamada.
  if (res.status === 401 && retry && session?.refresh_token) {
    try {
      await refreshSession();
      return send(method, path, { body, params }, false);
    } catch {
      clearSession();
      window.dispatchEvent(new CustomEvent('auth:expired'));
      throw new ApiError('Sua sessão expirou. Entre novamente.', { status: 401, code: 'session_expired' });
    }
  }
  if (res.status === 401) {
    clearSession();
    window.dispatchEvent(new CustomEvent('auth:expired'));
    throw new ApiError('Sua sessão expirou. Entre novamente.', { status: 401, code: 'session_expired' });
  }

  if (res.status === 204) return null;

  const isJson = (res.headers.get('content-type') || '').includes('application/json');
  const data = isJson ? await res.json().catch(() => null) : null;

  if (!res.ok) {
    const e = data?.error || {};
    throw new ApiError(e.message || `Erro inesperado (${res.status}).`, {
      status: res.status,
      code: e.code || 'error',
      details: e.details || null,
    });
  }
  return data;
}

/** Baixa um arquivo (CSV) respeitando o token de autenticação. */
async function download(path, params, filename) {
  const session = getSession();
  let res;
  try {
    res = await fetch(`/api${path}${buildQuery(params)}`, {
      headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {},
    });
  } catch {
    throw new ApiError('Não foi possível conectar ao servidor.', { code: 'network' });
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new ApiError(data?.error?.message || 'Não foi possível gerar o arquivo.', { status: res.status });
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const api = {
  get: (path, params) => send('GET', path, { params }),
  post: (path, body) => send('POST', path, { body }),
  put: (path, body) => send('PUT', path, { body }),
  patch: (path, body) => send('PATCH', path, { body }),
  delete: (path) => send('DELETE', path),
  download,

  // Atalhos de domínio
  health: async () => {
    const res = await fetch('/api/health');
    if (!res.ok) throw new ApiError('Servidor indisponível.', { status: res.status });
    return res.json();
  },
  listLeads: (params) => send('GET', '/leads', { params }),
  facets: () => send('GET', '/leads/facets'),
  getLead: (id) => send('GET', `/leads/${id}`),
  createLead: (data) => send('POST', '/leads', { body: data }),
  updateLead: (id, data) => send('PUT', `/leads/${id}`, { body: data }),
  deleteLead: (id) => send('DELETE', `/leads/${id}`),
  moveLead: (id, status) => send('PATCH', `/leads/${id}/status`, { body: { status } }),
  leadActivities: (id) => send('GET', `/leads/${id}/activities`),
  addNote: (id, description) => send('POST', `/leads/${id}/activities`, { body: { description } }),
};
