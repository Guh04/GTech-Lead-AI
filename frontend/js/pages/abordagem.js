// Abordagem: fila de mensagens de WhatsApp preparadas pela IA.
// Fluxo: gerar -> revisar/editar -> aprovar -> enviar (abre o WhatsApp com o texto pronto).
// O sistema nunca envia sozinho; o limite diário é aplicado pelo backend.
import { api } from '../api.js';
import { $, $$, html, setHtml, formatPhone, formatDateTime } from '../utils.js';
import { renderIcons, icon, toast, toastError, errorState, emptyState, withLoading } from '../ui.js';

const SOURCE_LABEL = { ai: 'Escrita pela IA', template: 'Texto-modelo' };
const TAB_LABEL = { draft: 'Para aprovar', approved: 'Aprovadas', sent: 'Enviadas', skipped: 'Descartadas' };
const EMPTY = {
  draft: { icon: 'message-square-plus', title: 'Nenhuma mensagem para aprovar', text: 'Use “Gerar mensagens” para a IA preparar as próximas abordagens.' },
  approved: { icon: 'circle-check', title: 'Nenhuma mensagem aprovada', text: 'As mensagens aprovadas ficam aqui, prontas para enviar.' },
  sent: { icon: 'send', title: 'Nenhuma mensagem enviada', text: 'O histórico de envios aparece aqui.' },
  skipped: { icon: 'archive', title: 'Nenhuma mensagem descartada', text: '' },
};

export async function mount(view) {
  let alive = true;
  let tab = 'draft';
  let status = null;
  let counts = {};

  const msgBox = (m) => {
    const lead = m.lead || {};
    const place = [lead.city, lead.state].filter(Boolean).join(' / ');
    const editable = m.status === 'draft' || m.status === 'approved';
    return html`<article class="card" data-msg="${m.id}" style="padding:16px">
      <div class="row" style="justify-content:space-between;align-items:flex-start">
        <div>
          <div class="cell-main">${lead.company_name || 'Lead removido'}</div>
          <div class="cell-sub">${[lead.segment, place].filter(Boolean).join(' · ')}${lead.whatsapp ? html` · ${formatPhone(lead.whatsapp)}` : ''}</div>
        </div>
        <span class="badge" data-tone="${m.source === 'ai' ? 'blue' : 'slate'}">${SOURCE_LABEL[m.source] || m.source}</span>
      </div>
      ${editable
        ? html`<textarea class="textarea" data-body rows="4" maxlength="1000" style="margin-top:12px" aria-label="Texto da mensagem">${m.body}</textarea>`
        : html`<p style="margin-top:12px;white-space:pre-wrap">${m.body}</p>`}
      <div class="row" style="margin-top:12px">
        ${m.status === 'draft' ? html`<button class="btn btn-primary btn-sm" data-act="approve">${icon('check', 'icon-sm')}Aprovar</button>` : ''}
        ${m.status === 'approved' ? html`<button class="btn btn-primary btn-sm" data-act="send">${icon('send', 'icon-sm')}Enviar no WhatsApp</button>` : ''}
        ${editable ? html`<button class="btn btn-sm" data-act="save">${icon('save', 'icon-sm')}Salvar texto</button><button class="btn btn-sm btn-ghost" data-act="skip">${icon('x', 'icon-sm')}Descartar</button>` : ''}
        ${m.status === 'sent' ? html`<span class="faint" style="font-size:12.5px">Enviada em ${formatDateTime(m.sent_at)}</span>` : ''}
        ${m.status === 'approved' ? html`<span class="faint" style="font-size:12px">Ao editar, será preciso aprovar de novo.</span>` : ''}
      </div>
    </article>`;
  };

  function renderStatus() {
    if (!status) return;
    const pct = Math.min(100, Math.round((status.sent_today / status.daily_limit) * 100));
    const reached = status.remaining <= 0;
    setHtml($('#ab-status', view), html`
      <div class="alert" data-tone="${reached ? 'warning' : 'info'}">${icon(reached ? 'shield-alert' : 'shield-check')}
        <div style="flex:1">
          <strong>${status.sent_today} de ${status.daily_limit} envios hoje${reached ? ' · limite atingido, continue amanhã' : ''}</strong>
          <div style="height:6px;border-radius:6px;background:var(--input);margin:8px 0;overflow:hidden"><i style="display:block;height:100%;width:${pct}%;background:var(--blue)"></i></div>
          O limite diário e um intervalo mínimo de ${status.min_interval_seconds}s entre envios reduzem o risco de bloqueio do número.
          ${status.ai_configured ? '' : html`<br>Sem IA configurada: as mensagens usam texto-modelo. Defina ANTHROPIC_API_KEY em backend/.env para mensagens personalizadas.`}
        </div>
      </div>`);
    renderIcons();
  }

  function renderTabCounts() {
    $$('[data-tab-label]', view).forEach((el) => { el.textContent = `${TAB_LABEL[el.dataset.tabLabel]} (${counts[el.dataset.tabLabel] || 0})`; });
  }

  async function loadStatus() {
    try {
      status = await api.get('/outreach/status');
      if (alive) renderStatus();
    } catch (err) {
      if (alive) { setHtml($('#ab-status', view), html`<div class="alert" data-tone="error">${icon('circle-alert')}<div>${err.message}</div></div>`); renderIcons(); }
    }
  }

  async function loadList() {
    const box = $('#ab-list', view);
    try {
      const [items, c] = await Promise.all([api.get('/outreach', { status: tab }), api.get('/outreach/counts')]);
      if (!alive) return;
      counts = c;
      renderTabCounts();
      setHtml(box, items.length ? html`${items.map(msgBox)}` : emptyState(EMPTY[tab]));
    } catch (err) {
      if (alive) setHtml(box, errorState(err));
    }
    renderIcons();
  }

  const refreshAll = () => Promise.all([loadStatus(), loadList()]);

  $('#ab-tabs', view).addEventListener('change', (e) => { tab = e.target.value; loadList(); });
  $('#ab-refresh', view).addEventListener('click', refreshAll);

  $('#ab-generate', view).addEventListener('click', async (e) => {
    const count = Math.max(1, Math.min(100, Number($('#ab-count', view).value) || 10));
    try {
      const res = await withLoading(e.currentTarget, () => api.post('/outreach/generate', { count }));
      toast(
        res.created
          ? `${res.created} mensagem(ns) preparada(s) para aprovação.`
          : 'Nenhum lead elegível (precisa ter WhatsApp, não estar em “não contatar” e ainda não ter mensagem).',
        res.created ? 'success' : 'info',
      );
      tab = 'draft';
      const radio = $('input[name="ab-tab"][value="draft"]', view);
      if (radio) radio.checked = true;
      await refreshAll();
    } catch (err) {
      toastError(err);
    }
  });

  view.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-act]');
    if (!btn) return;
    const card = btn.closest('[data-msg]');
    const id = card.dataset.msg;
    const body = $('[data-body]', card)?.value.trim();
    try {
      await withLoading(btn, async () => {
        switch (btn.dataset.act) {
          case 'save':
            await api.patch(`/outreach/${id}`, { body });
            toast('Texto salvo. Aprove para liberar o envio.', 'success');
            break;
          case 'approve':
            if (body) await api.patch(`/outreach/${id}`, { body }); // aprova exatamente o texto que está na tela
            await api.post(`/outreach/${id}/approve`);
            toast('Mensagem aprovada.', 'success');
            break;
          case 'skip':
            await api.post(`/outreach/${id}/skip`);
            break;
          case 'send': {
            if (body !== undefined && body !== $('[data-body]', card).defaultValue.trim()) {
              throw new Error('Você editou o texto. Clique em “Salvar texto” e aprove novamente antes de enviar.');
            }
            const res = await api.post(`/outreach/${id}/send`);
            const w = window.open(res.whatsapp_url, '_blank');
            if (w) w.opener = null;
            toast(w ? 'WhatsApp aberto. Confira o texto e clique em enviar lá.' : 'O navegador bloqueou a janela. Permita pop-ups para abrir o WhatsApp.', w ? 'success' : 'warning');
            break;
          }
          default:
        }
      });
      await refreshAll();
    } catch (err) {
      toastError(err);
      refreshAll();
    }
  });

  renderIcons();
  await refreshAll();
  return () => { alive = false; };
}
