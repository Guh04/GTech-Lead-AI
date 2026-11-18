// Formulário de cadastro/edição de lead (modal).
import { html, setHtml, $, $$ } from '../utils.js';
import { openModal, renderIcons, toast, withLoading, icon } from '../ui.js';
import { api } from '../api.js';
import { STATES, STATUSES, LANDING, SOURCES, SEGMENT_SUGGESTIONS } from '../constants.js';

const opt = (value, label, selected) => html`<option value="${value}" ${selected ? 'selected' : ''}>${label}</option>`;

function field(label, name, control, { required = false, hint = '', full = false } = {}) {
  return html`<div class="field ${full ? 'full' : ''}">
    <label for="lf-${name}">${label}${required ? html`<span class="req">*</span>` : ''}</label>
    ${control}
    ${hint ? html`<span class="hint">${hint}</span>` : ''}
    <span class="error" data-error="${name}" hidden></span>
  </div>`;
}

function formBody(lead, segments) {
  const v = (k) => lead?.[k] ?? '';
  const input = (name, type = 'text', extra = '') =>
    html`<input class="input" id="lf-${name}" name="${name}" type="${type}" value="${v(name)}" ${extra}>`;

  return html`
  <form id="lead-form" novalidate>
    <div class="alert" data-tone="error" id="lf-alert" hidden></div>
    <div class="form-grid" style="margin-top:0">
      <div class="form-section">Empresa</div>
      ${field('Nome da empresa', 'company_name', input('company_name', 'text', 'maxlength="200" required autocomplete="off"'), { required: true, full: true })}
      ${field('Responsável', 'contact_name', input('contact_name', 'text', 'maxlength="160" autocomplete="off"'), { hint: 'Quando identificado' })}
      ${field('Segmento', 'segment', html`<input class="input" id="lf-segment" name="segment" list="lf-segments" maxlength="120" value="${v('segment')}" autocomplete="off" placeholder="Ex.: Clínica odontológica">
        <datalist id="lf-segments">${segments.map((s) => html`<option value="${s}"></option>`)}</datalist>`)}
      ${field('Cidade', 'city', input('city', 'text', 'maxlength="120" autocomplete="off"'))}
      ${field('Estado', 'state', html`<select class="select" id="lf-state" name="state"><option value="">—</option>${STATES.map((s) => opt(s, s, lead?.state === s))}</select>`)}

      <div class="form-section">Contato</div>
      ${field('Telefone', 'phone', input('phone', 'tel', 'maxlength="24" placeholder="(11) 3000-0000" autocomplete="off"'))}
      ${field('WhatsApp', 'whatsapp', input('whatsapp', 'tel', 'maxlength="24" placeholder="(11) 99999-0000" autocomplete="off"'))}

      <div class="form-section">Presença digital</div>
      ${field('Site', 'website', input('website', 'text', 'maxlength="300" placeholder="www.empresa.com.br" autocomplete="off"'))}
      ${field('Situação da landing page', 'landing_page_status', html`<select class="select" id="lf-landing_page_status" name="landing_page_status">${LANDING.map((l) => opt(l.key, l.label, (lead?.landing_page_status || 'unknown') === l.key))}</select>`)}
      ${field('Instagram', 'instagram', input('instagram', 'text', 'maxlength="300" placeholder="@usuario ou link do perfil" autocomplete="off"'))}
      ${field('Facebook', 'facebook', input('facebook', 'text', 'maxlength="300" placeholder="Link da página" autocomplete="off"'))}

      <div class="form-section">Qualificação</div>
      ${field('Pontuação comercial', 'score', html`<input class="input" id="lf-score" name="score" type="number" min="0" max="100" step="1" inputmode="numeric" placeholder="Automática" value="${lead?.score_source === 'manual' ? lead.score : ''}">`, { hint: 'Deixe em branco para calcular automaticamente (0–100). A prioridade é definida pela pontuação.' })}
      ${field('Estágio no pipeline', 'status', html`<select class="select" id="lf-status" name="status">${STATUSES.map((s) => opt(s.key, s.label, (lead?.status || 'new') === s.key))}</select>`)}
      ${field('Origem do lead', 'source', html`<select class="select" id="lf-source" name="source">${SOURCES.map((s) => opt(s.key, s.label, (lead?.source || 'manual') === s.key))}</select>`)}
      ${field('Link da fonte pública', 'source_url', input('source_url', 'text', 'maxlength="500" placeholder="https://..." autocomplete="off"'), { hint: 'Onde a informação foi encontrada (LGPD)' })}

      <div class="form-section">Observações</div>
      ${field('Observações', 'notes', html`<textarea class="textarea" id="lf-notes" name="notes" maxlength="5000" placeholder="Informações relevantes sobre o lead...">${v('notes')}</textarea>`, { full: true })}
      <label class="check full"><input type="checkbox" name="do_not_contact" ${lead?.do_not_contact ? 'checked' : ''}>
        <span>Não contatar<small>Marque se a pessoa/empresa pediu para não ser contatada (LGPD).</small></span></label>
    </div>
  </form>`;
}

function collect(form) {
  const fd = new FormData(form);
  const str = (k) => {
    const s = String(fd.get(k) ?? '').trim();
    return s === '' ? null : s;
  };
  const scoreRaw = String(fd.get('score') ?? '').trim();
  return {
    company_name: String(fd.get('company_name') ?? '').trim(),
    contact_name: str('contact_name'),
    segment: str('segment'),
    city: str('city'),
    state: str('state'),
    phone: str('phone'),
    whatsapp: str('whatsapp'),
    instagram: str('instagram'),
    facebook: str('facebook'),
    website: str('website'),
    landing_page_status: fd.get('landing_page_status'),
    score: scoreRaw === '' ? null : Number(scoreRaw),
    status: fd.get('status'),
    source: fd.get('source'),
    source_url: str('source_url'),
    notes: str('notes'),
    do_not_contact: fd.get('do_not_contact') === 'on',
  };
}

function showErrors(root, err) {
  $$('.invalid', root).forEach((el) => el.classList.remove('invalid'));
  $$('[data-error]', root).forEach((el) => { el.hidden = true; el.textContent = ''; });
  const alertBox = $('#lf-alert', root);
  alertBox.hidden = true;

  const fieldErrors = Array.isArray(err.details) ? err.details : [];
  let shown = 0;
  fieldErrors.forEach(({ field: f, message }) => {
    const slot = $(`[data-error="${f}"]`, root);
    if (!slot) return;
    slot.textContent = message;
    slot.hidden = false;
    $(`[name="${f}"]`, root)?.classList.add('invalid');
    shown++;
  });
  if (shown === 0 || err.status !== 422) {
    setHtml(alertBox, html`${icon('circle-alert')}<div><strong>${err.status === 409 ? 'Lead duplicado' : 'Não foi possível salvar'}</strong>${err.message}</div>`);
    alertBox.hidden = false;
    renderIcons();
  }
  const first = $('.invalid', root);
  (first || alertBox).scrollIntoView?.({ block: 'center', behavior: 'smooth' });
  first?.focus();
}

/**
 * Abre o formulário. Resolve com o lead salvo, ou null se o usuário cancelar.
 * @param {{lead?: object}} opts  lead existente para edição
 */
export async function openLeadForm({ lead = null } = {}) {
  const editing = Boolean(lead);
  let segments = [...SEGMENT_SUGGESTIONS];
  try {
    const facets = await api.facets();
    segments = [...new Set([...(facets.segments || []), ...SEGMENT_SUGGESTIONS])].sort((a, b) => a.localeCompare(b, 'pt-BR'));
  } catch { /* sugestões são opcionais */ }

  return new Promise((resolve) => {
    let saved = null;
    const modal = openModal({
      title: editing ? 'Editar lead' : 'Novo lead',
      body: formBody(lead, segments),
      footer: html`
        <button type="button" class="btn" data-close>Cancelar</button>
        <button type="submit" class="btn btn-primary" form="lead-form" id="lf-submit">${icon('check', 'icon-sm')}${editing ? 'Salvar alterações' : 'Cadastrar lead'}</button>`,
      onClose: () => resolve(saved),
    });

    const form = $('#lead-form', modal.el);
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const data = collect(form);
      if (!data.company_name) {
        showErrors(modal.el, { status: 422, details: [{ field: 'company_name', message: 'Informe o nome da empresa.' }] });
        return;
      }
      try {
        await withLoading($('#lf-submit', modal.el), async () => {
          saved = editing ? await api.updateLead(lead.id, data) : await api.createLead(data);
        });
        toast(editing ? 'Lead atualizado com sucesso.' : 'Lead cadastrado com sucesso.', 'success');
        modal.close();
      } catch (err) {
        showErrors(modal.el, err);
      }
    });
  });
}
