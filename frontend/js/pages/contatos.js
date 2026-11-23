// Contatos: chamar leads no WhatsApp com 1 clique (mensagem pronta) e tratar os leads sem WhatsApp.
// O envio é sempre feito por você no WhatsApp; o backend aplica o limite diário e o intervalo mínimo.
import { api } from '../api.js';
import { $, $$, html, setHtml, formatPhone, instagramLink, safeUrl, displayUrl } from '../utils.js';
import { renderIcons, icon, toast, toastError, errorState, emptyState, withLoading, priorityBadge, statusBadge } from '../ui.js';

const PAGE_SIZE = 100;

/** Celular brasileiro (DDD + 9 + 8 dígitos) tem boa chance de ter WhatsApp. */
function looksLikeMobile(digits) {
  let d = String(digits || '').replace(/\D/g, '');
  if (d.length === 13 && d.startsWith('55')) d = d.slice(2);
  return d.length === 11 && d[2] === '9' ? d : null;
}

export async function mount(view) {
  let alive = true;
  let tab = 'with';
  let status = null;
  let items = [];
  let total = 0;
  let timer = null;
  let waitUntil = 0; // epoch ms em que o próximo envio é liberado

  const callBtn = (l) => html`<button class="btn btn-primary btn-sm" data-act="call" data-id="${l.id}">${icon('message-circle', 'icon-sm')}<span data-call-label>Chamar</span></button>`;

  function rowWith(l) {
    return html`<tr data-row="${l.id}">
      <td><div class="cell-main">${l.company_name}</div><div class="cell-sub">${[l.segment, [l.city, l.state].filter(Boolean).join(' / ')].filter(Boolean).join(' · ')}</div></td>
      <td class="nowrap">${formatPhone(l.whatsapp)}</td>
      <td class="hide-sm">${priorityBadge(l.priority)}</td>
      <td class="hide-sm">${statusBadge(l.status)}</td>
      <td style="text-align:right"><div class="row" style="justify-content:flex-end;gap:6px"><button class="btn btn-sm" data-act="demo" data-id="${l.id}" data-name="${l.company_name}" title="Baixar uma página de demonstração com o nome desta empresa">${icon('download', 'icon-sm')}Demo</button>${callBtn(l)}</div></td>
    </tr>`;
  }

  function rowWithout(l) {
    const mobile = looksLikeMobile(l.phone);
    const ig = instagramLink(l.instagram);
    const site = safeUrl(l.website);
    return html`<tr data-row="${l.id}">
      <td><div class="cell-main">${l.company_name}</div><div class="cell-sub">${[l.segment, [l.city, l.state].filter(Boolean).join(' / ')].filter(Boolean).join(' · ')}</div></td>
      <td class="nowrap">${l.phone ? formatPhone(l.phone) : html`<span class="faint">sem telefone</span>`}</td>
      <td class="hide-sm">${ig ? html`<a href="${ig}" target="_blank" rel="noopener noreferrer">@${l.instagram}</a>` : ''}${ig && site ? ' · ' : ''}${site ? html`<a href="${site}" target="_blank" rel="noopener noreferrer">${displayUrl(site)}</a>` : ''}${!ig && !site ? html`<span class="faint">—</span>` : ''}</td>
      <td style="text-align:right">
        <div class="row" style="justify-content:flex-end;gap:6px">
          ${mobile ? html`<button class="btn btn-primary btn-sm" data-act="use-phone" data-id="${l.id}" data-phone="${mobile}" title="Celular: provavelmente tem WhatsApp">${icon('message-circle', 'icon-sm')}Usar como WhatsApp</button>` : ''}
          ${l.phone ? html`<button class="btn btn-sm" data-act="copy" data-phone="${l.phone}">${icon('copy', 'icon-sm')}Copiar</button><a class="btn btn-sm" href="tel:${l.phone}">${icon('phone', 'icon-sm')}Ligar</a>` : ''}
        </div>
      </td>
    </tr>`;
  }

  function renderList(extra = '') {
    const box = $('#ct-list', view);
    if (!items.length) {
      setHtml(box, emptyState(tab === 'with'
        ? { icon: 'message-circle-off', title: 'Ninguém para chamar agora', text: 'Todos os leads com WhatsApp já foram chamados, ou ainda não há leads. Rode uma busca na Prospecção.' }
        : { icon: 'circle-check', title: 'Nenhum lead sem WhatsApp', text: 'Todos os leads encontrados têm WhatsApp cadastrado.' }));
      return;
    }
    const head = tab === 'with'
      ? html`<tr><th>Empresa</th><th>WhatsApp</th><th class="hide-sm">Prioridade</th><th class="hide-sm">Estágio</th><th></th></tr>`
      : html`<tr><th>Empresa</th><th>Telefone</th><th class="hide-sm">Instagram / site</th><th></th></tr>`;
    setHtml(box, html`<table class="table"><thead>${head}</thead><tbody>${items.map(tab === 'with' ? rowWith : rowWithout)}</tbody></table>
      ${total > items.length ? html`<p class="faint" style="font-size:12.5px;padding:12px 16px">Mostrando ${items.length} de ${total}. Os próximos aparecem conforme você chama os primeiros.</p>` : ''}${extra}`);
    renderIcons();
    paintWait();
  }

  function renderStatus() {
    if (!status) return;
    const pct = Math.min(100, Math.round((status.sent_today / status.daily_limit) * 100));
    const reached = status.remaining <= 0;
    setHtml($('#ct-status', view), html`
      <div class="alert" data-tone="${reached ? 'warning' : 'info'}">${icon(reached ? 'shield-alert' : 'shield-check')}
        <div style="flex:1">
          <strong>${status.sent_today} de ${status.daily_limit} chamadas hoje${reached ? ' · limite atingido, continue amanhã' : ` · restam ${status.remaining}`}</strong>
          <div style="height:6px;border-radius:6px;background:var(--input);margin-top:8px;overflow:hidden"><i style="display:block;height:100%;width:${pct}%;background:var(--blue)"></i></div>
        </div>
      </div>`);
    renderIcons();
  }

  /** Mostra a contagem regressiva nos botões enquanto o intervalo mínimo entre envios não passou. */
  function paintWait() {
    const left = Math.max(0, Math.ceil((waitUntil - Date.now()) / 1000));
    const blocked = (status && status.remaining <= 0) || left > 0;
    $$('[data-act="call"]', view).forEach((b) => {
      b.disabled = blocked;
      const label = $('[data-call-label]', b);
      if (label) label.textContent = left > 0 ? `Aguarde ${left}s` : 'Chamar';
    });
    if (left <= 0 && timer) { clearInterval(timer); timer = null; }
  }

  function startWait(seconds) {
    waitUntil = Date.now() + seconds * 1000;
    if (!timer && seconds > 0) timer = setInterval(paintWait, 500);
    paintWait();
  }

  // Filtros comuns às abas e aos contadores.
  const filters = () => ({
    contactable: $('#ct-only-new', view).checked || undefined,
    landing_status: $('#ct-no-site', view).checked ? 'none' : undefined,
  });

  async function loadCounts() {
    // Só os totais; as listas completas vêm sob demanda.
    try {
      const [w, wo] = await Promise.all([
        api.listLeads({ has_whatsapp: true, ...filters(), page_size: 1 }),
        api.listLeads({ has_whatsapp: false, ...filters(), page_size: 1 }),
      ]);
      if (!alive) return;
      $('[data-tab-label="with"]', view).textContent = `Com WhatsApp (${w.total})`;
      $('[data-tab-label="without"]', view).textContent = `Sem WhatsApp (${wo.total})`;
    } catch { /* os números das abas são só informativos */ }
  }

  async function load() {
    setHtml($('#ct-list', view), html`<div class="page-loading" style="min-height:140px"><div class="spinner"></div></div>`);
    try {
      const [res, st] = await Promise.all([
        api.listLeads({
          has_whatsapp: tab === 'with',
          ...filters(),
          sort: 'score_desc',
          page_size: PAGE_SIZE,
        }),
        api.get('/outreach/status'),
      ]);
      if (!alive) return;
      items = res.items;
      total = res.total;
      status = st;
      renderStatus();
      renderList();
      if (st.wait_seconds > 0) startWait(st.wait_seconds);
    } catch (err) {
      if (alive) { setHtml($('#ct-list', view), errorState(err)); renderIcons(); }
    }
    loadCounts();
  }

  function removeRow(id) {
    items = items.filter((l) => l.id !== id);
    total = Math.max(0, total - 1);
    $(`[data-row="${id}"]`, view)?.remove();
    if (!items.length) renderList();
  }

  $('#ct-tabs', view).addEventListener('change', (e) => { tab = e.target.value; load(); });
  $('#ct-only-new', view).addEventListener('change', load);
  $('#ct-no-site', view).addEventListener('change', load);

  view.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-act]');
    if (!btn || btn.disabled) return;
    const id = btn.dataset.id;
    try {
      switch (btn.dataset.act) {
        case 'call': {
          // A janela precisa abrir logo após o clique; por isso aguardamos só a resposta do servidor.
          const res = await withLoading(btn, () => api.post(`/outreach/quick/${id}`));
          status = res.status;
          renderStatus();
          if (res.delivery !== 'link') {
            toast(res.delivery === 'unknown' ? 'Envio sem confirmação do WhatsMCP. Confira a conversa antes de tentar de novo.' : 'Mensagem enviada pelo WhatsApp.', res.delivery === 'unknown' ? 'warning' : 'success');
          } else {
            const w = window.open(res.whatsapp_url, '_blank');
            if (w) w.opener = null;
            else toast('O navegador bloqueou a janela do WhatsApp. Permita pop-ups para este site.', 'warning');
          }
          if ($('#ct-only-new', view).checked) removeRow(id);
          startWait(res.status.wait_seconds || status.min_interval_seconds);
          break;
        }
        case 'demo': {
          const name = (btn.dataset.name || 'empresa').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'empresa';
          await withLoading(btn, () => api.download(`/leads/${id}/demo`, undefined, `demo-${name}.zip`));
          toast('Demo baixada. Arraste o ZIP em netlify.com/drop para gerar o link e envie ao lead.', 'success');
          break;
        }
        case 'use-phone': {
          await withLoading(btn, () => api.updateLead(id, { whatsapp: btn.dataset.phone }));
          toast('Telefone definido como WhatsApp. O lead foi para “Com WhatsApp”.', 'success');
          removeRow(id);
          loadCounts();
          break;
        }
        case 'copy':
          await navigator.clipboard.writeText(btn.dataset.phone);
          toast('Número copiado.', 'success');
          break;
        default:
      }
    } catch (err) {
      toastError(err);
      if (btn.dataset.act === 'call') load(); // limite/intervalo: atualiza contador e botões
    }
  });

  // ---- Envio automático: chama os leads da lista um a um, respeitando intervalo e limite diário.
  // Roda neste navegador (precisa da aba aberta) e só existe com WhatsMCP configurado.
  const MIN_GAP_MS = 40000;
  let autoRunning = false;
  const autoBtn = $('#ct-auto-btn', view);
  const autoMsg = $('#ct-auto-msg', view);
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  async function sleepWhileAlive(ms, label) {
    const end = Date.now() + ms;
    while (alive && autoRunning && Date.now() < end) {
      autoMsg.textContent = `${label} Próximo envio em ${Math.ceil((end - Date.now()) / 1000)}s`;
      await sleep(500);
    }
  }

  async function runAuto() {
    autoRunning = true;
    autoBtn.textContent = 'Parar envio automático';
    let sent = 0;
    const skipped = new Set();
    try {
      while (alive && autoRunning) {
        if (tab !== 'with') tab = 'with';
        const lead = items.find((l) => !skipped.has(l.id));
        if (!lead) { autoMsg.textContent = `Fim da lista. ${sent} enviada(s) nesta rodada.`; break; }
        if (status && status.remaining <= 0) { autoMsg.textContent = `Limite diário atingido. ${sent} enviada(s) nesta rodada.`; break; }
        const waitMs = Math.max((status?.wait_seconds || 0) * 1000, 0);
        if (waitMs > 0) await sleepWhileAlive(waitMs, 'Aguardando intervalo.');
        if (!alive || !autoRunning) break;
        autoMsg.textContent = `Enviando para ${lead.company_name}…`;
        try {
          const res = await api.post(`/outreach/quick/${lead.id}`);
          status = res.status;
          renderStatus();
          sent += 1;
          skipped.add(lead.id);
          if ($('#ct-only-new', view).checked) removeRow(lead.id);
          if (res.delivery === 'unknown') { toast('Envio sem confirmação do WhatsMCP. Parei por segurança: confira a conversa.', 'warning'); break; }
        } catch (err) {
          const code = err?.code || err?.data?.error?.code;
          if (code === 'too_soon') { await load(); continue; }
          if (code === 'not_on_whatsapp') { skipped.add(lead.id); removeRow(lead.id); toast(`${lead.company_name}: sem WhatsApp, pulei.`, 'warning'); continue; }
          if (code === 'already_contacted') { skipped.add(lead.id); removeRow(lead.id); continue; }
          skipped.add(lead.id); // falha neste lead: para tudo para você ver o motivo
          toastError(err);
          autoMsg.textContent = `Parado por erro em ${lead.company_name}. ${sent} enviada(s).`;
          break;
        }
        // Garante pelo menos 40s entre envios, mesmo que o servidor aceite menos.
        const gap = Math.max(MIN_GAP_MS, (status?.min_interval_seconds || 0) * 1000);
        await sleepWhileAlive(gap, `${sent} enviada(s).`);
      }
    } finally {
      autoRunning = false;
      autoBtn.textContent = 'Enviar automático';
      if (alive) load();
    }
  }

  autoBtn.addEventListener('click', () => {
    if (autoRunning) { autoRunning = false; autoMsg.textContent = 'Parando…'; return; }
    const hide = $('#ct-only-new', view);
    if (!hide.checked) { hide.checked = true; load().then(runAuto); return; } // nunca repete quem já foi chamado
    runAuto();
  });

  renderIcons();
  await load();
  $('#ct-auto', view).hidden = !(status && status.auto_send);
  return () => { alive = false; autoRunning = false; if (timer) clearInterval(timer); };
}
