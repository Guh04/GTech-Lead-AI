// Ficha completa do lead (drawer lateral) com ações e histórico.
import { html, setHtml, $, formatDate, formatDateTime, timeAgo, formatPhone, whatsappLink, instagramLink, safeUrl, displayUrl } from '../utils.js';
import { openDrawer, renderIcons, icon, toast, toastError, statusBadge, priorityBadge, landingBadge, needBadges, scoreBar, confirmDialog, withLoading, errorState } from '../ui.js';
import { api } from '../api.js';
import { STATUSES, SOURCE_BY_KEY, ACTIVITY_ICONS, IG_LAST_POST, IG_ENGAGEMENT, IG_QUALITY, MARKETING_THRESHOLD } from '../constants.js';
import { openLeadForm } from './lead-form.js';

const item = (label, value, full = false) =>
  html`<div class="detail-item ${full ? 'full' : ''}"><dt>${label}</dt><dd>${value || html`<span class="faint">—</span>`}</dd></div>`;

function link(href, text, ext = true) {
  return href ? html`<a href="${href}" ${ext ? 'target="_blank" rel="noopener noreferrer"' : ''}>${text}</a>` : null;
}

function timeline(activities) {
  if (!activities.length) return html`<p class="muted">Nenhuma atividade registrada ainda.</p>`;
  return html`<ul class="timeline">${activities.map((a) => html`
    <li>
      <span class="tl-dot" data-type="${a.type}">${icon(ACTIVITY_ICONS[a.type] || 'circle')}</span>
      <div class="tl-text"><div>${a.description}</div><div class="tl-time" title="${formatDateTime(a.created_at)}">${timeAgo(a.created_at)}</div></div>
    </li>`)}</ul>`;
}

const options = (list, current) =>
  list.map((o) => html`<option value="${o.key}" ${o.key === current ? 'selected' : ''}>${o.label}</option>`);

function marketingSection(lead) {
  const ms = lead.marketing_score;
  const level = ms == null ? '' : ms >= 70 ? 'high' : ms >= MARKETING_THRESHOLD ? 'medium' : 'low';
  const summary = !lead.instagram
    ? 'Sem Instagram cadastrado: conta como precisando de marketing. Se encontrar o perfil, adicione em Editar e avalie aqui.'
    : ms == null
      ? 'Abra o Instagram do lead e preencha a avaliação abaixo para calcular a necessidade de marketing.'
      : ms >= MARKETING_THRESHOLD ? 'Perfil parado ou fraco: bom candidato para a parceria de marketing.' : 'Perfil ativo: pouca necessidade de marketing.';
  return html`
    <section class="detail-section">
      <h3>Marketing (Instagram)</h3>
      <div class="row" style="gap:16px;margin-bottom:8px">
        ${ms == null ? html`<span class="badge" data-tone="slate">Não avaliado</span>` : html`<div style="min-width:180px">${scoreBar(ms, level)}</div>`}
        ${lead.instagram ? html`<a class="btn btn-sm" href="${instagramLink(lead.instagram)}" target="_blank" rel="noopener noreferrer">${icon('instagram', 'icon-sm')}Abrir @${lead.instagram}</a>` : ''}
      </div>
      <p class="faint" style="font-size:12.5px;margin-bottom:12px">${summary}${lead.ig_checked_at ? ` Avaliado em ${formatDate(lead.ig_checked_at)}.` : ''}</p>
      ${lead.instagram ? html`
      <div class="detail-grid" style="margin:0">
        <div class="field"><label for="ig-last">Último post</label><select class="select" id="ig-last">${options(IG_LAST_POST, lead.ig_last_post)}</select></div>
        <div class="field"><label for="ig-eng">Engajamento</label><select class="select" id="ig-eng">${options(IG_ENGAGEMENT, lead.ig_engagement)}</select></div>
        <div class="field"><label for="ig-quality">Aparência do perfil</label><select class="select" id="ig-quality">${options(IG_QUALITY, lead.ig_quality)}</select></div>
        <div class="field"><label for="ig-followers">Seguidores</label><input class="input" id="ig-followers" type="number" min="0" step="1" inputmode="numeric" placeholder="ex.: 850" value="${lead.ig_followers ?? ''}"></div>
      </div>
      <div style="margin-top:10px"><button class="btn btn-sm btn-primary" id="ig-save">${icon('check', 'icon-sm')}Salvar avaliação</button></div>` : ''}
    </section>`;
}

function render(lead, activities) {
  const site = safeUrl(lead.website);
  const fb = safeUrl(lead.facebook);
  const src = safeUrl(lead.source_url);
  const wa = whatsappLink(lead.whatsapp);
  const place = [lead.city, lead.state].filter(Boolean).join(' / ');

  return html`
    <div class="drawer-head">
      <div style="min-width:0;flex:1">
        <h2 style="font-size:19px;line-height:1.25">${lead.company_name}</h2>
        <p class="muted" style="margin-top:2px">${[lead.segment, place].filter(Boolean).join(' · ') || 'Sem segmento ou localização'}</p>
        <div class="row" style="margin-top:10px;gap:8px">${statusBadge(lead.status)}${priorityBadge(lead.priority)}${landingBadge(lead.landing_page_status)}${needBadges(lead)}</div>
      </div>
      <button class="btn btn-ghost btn-icon btn-sm" data-close aria-label="Fechar">${icon('x')}</button>
    </div>

    <div class="drawer-body">
      ${lead.do_not_contact ? html`<div class="alert" data-tone="error">${icon('ban')}<div><strong>Não contatar</strong>Este lead pediu para não ser contatado. Respeite a solicitação (LGPD).</div></div>` : ''}

      <section class="detail-section">
        <h3>Ações rápidas</h3>
        <div class="row">
          ${wa && !lead.do_not_contact ? html`<a class="btn btn-sm" href="${wa}" target="_blank" rel="noopener noreferrer">${icon('message-circle', 'icon-sm')}Abrir WhatsApp</a>` : ''}
          ${lead.phone && !lead.do_not_contact ? html`<a class="btn btn-sm" href="tel:${lead.phone}">${icon('phone', 'icon-sm')}Ligar</a>` : ''}
          ${site ? html`<a class="btn btn-sm" href="${site}" target="_blank" rel="noopener noreferrer">${icon('globe', 'icon-sm')}Visitar site</a>` : ''}
          ${lead.instagram ? html`<a class="btn btn-sm" href="${instagramLink(lead.instagram)}" target="_blank" rel="noopener noreferrer">${icon('instagram', 'icon-sm')}Instagram</a>` : ''}
        </div>
        <p class="faint" style="font-size:12px;margin-top:8px">As ações abrem o aplicativo ou site em uma nova janela. Nenhuma mensagem é enviada automaticamente.</p>
      </section>

      <section class="detail-section">
        <h3>Pipeline comercial</h3>
        <div class="row">
          <select class="select" id="ld-status" style="max-width:260px" aria-label="Estágio no pipeline">
            ${STATUSES.map((s) => html`<option value="${s.key}" ${s.key === lead.status ? 'selected' : ''}>${s.label}</option>`)}
          </select>
          <span class="faint" style="font-size:12.5px">Desde ${formatDate(lead.status_updated_at)}</span>
        </div>
      </section>

      <section class="detail-section">
        <h3>Pontuação comercial</h3>
        <div class="row" style="gap:16px">
          <div style="min-width:180px">${scoreBar(lead.score, lead.priority)}</div>
          <span class="faint" style="font-size:12.5px">${lead.score_source === 'manual' ? 'Definida manualmente' : lead.score_source === 'ai' ? 'Calculada por IA' : 'Calculada automaticamente'}</span>
        </div>
      </section>

      <section class="detail-section">
        <h3>Contato</h3>
        <dl class="detail-grid" style="margin:0">
          ${item('Responsável', lead.contact_name)}
          ${item('Telefone', lead.phone ? formatPhone(lead.phone) : '')}
          ${item('WhatsApp', lead.whatsapp ? formatPhone(lead.whatsapp) : '')}
          ${item('Cidade / UF', place)}
        </dl>
      </section>

      <section class="detail-section">
        <h3>Presença digital</h3>
        <dl class="detail-grid" style="margin:0">
          ${item('Site', link(site, displayUrl(site)))}
          ${item('Landing page', landingBadge(lead.landing_page_status))}
          ${item('Instagram', lead.instagram ? link(instagramLink(lead.instagram), `@${lead.instagram}`) : '')}
          ${item('Facebook', link(fb, displayUrl(fb)))}
        </dl>
      </section>

      ${marketingSection(lead)}

      <section class="detail-section">
        <h3>Origem</h3>
        <dl class="detail-grid" style="margin:0">
          ${item('Origem do lead', SOURCE_BY_KEY[lead.source]?.label || lead.source)}
          ${item('Fonte pública', link(src, displayUrl(src)))}
          ${item('Cadastrado em', formatDateTime(lead.created_at))}
          ${item('Atualizado em', formatDateTime(lead.updated_at))}
        </dl>
      </section>

      ${lead.notes ? html`<section class="detail-section"><h3>Observações</h3><div class="notes-box">${lead.notes}</div></section>` : ''}

      <section class="detail-section">
        <h3>Histórico</h3>
        <div class="field" style="margin-bottom:16px">
          <textarea class="textarea" id="ld-note" style="min-height:64px" maxlength="2000" placeholder="Registrar uma anotação (ligação, reunião, retorno...)"></textarea>
          <div><button class="btn btn-sm" id="ld-note-btn">${icon('plus', 'icon-sm')}Adicionar anotação</button></div>
        </div>
        <div id="ld-timeline">${timeline(activities)}</div>
      </section>
    </div>

    <div class="drawer-foot">
      <button class="btn" id="ld-edit">${icon('pencil', 'icon-sm')}Editar</button>
      <span class="spacer"></span>
      <button class="btn btn-danger" id="ld-delete">${icon('trash-2', 'icon-sm')}Excluir</button>
    </div>`;
}

/**
 * Abre a ficha de um lead.
 * @param {string} id
 * @param {{onChange?: () => void}} opts  chamado após editar/excluir/mover/anotar
 */
export async function openLeadDetail(id, { onChange } = {}) {
  let changed = false;
  const drawer = openDrawer({ onClose: () => { if (changed) onChange?.(); } });
  const panel = drawer.panel;
  setHtml(panel, html`<div class="drawer-head"><div class="skeleton sk-line" style="width:60%;height:22px"></div></div>
    <div class="drawer-body"><div class="skeleton sk-block"></div><div class="skeleton sk-block"></div></div>`);

  const load = async () => {
    try {
      const [lead, activities] = await Promise.all([api.getLead(id), api.leadActivities(id)]);
      setHtml(panel, render(lead, activities));
      renderIcons();
      bind(lead);
    } catch (err) {
      setHtml(panel, html`<div class="drawer-head"><span class="spacer"></span><button class="btn btn-ghost btn-icon btn-sm" data-close aria-label="Fechar">${icon('x')}</button></div>${errorState(err)}`);
      renderIcons();
      $('[data-retry]', panel)?.addEventListener('click', load);
      $('[data-close]', panel)?.addEventListener('click', drawer.close);
    }
  };

  const bind = (lead) => {
    $('[data-close]', panel).addEventListener('click', drawer.close);

    $('#ld-status', panel).addEventListener('change', async (e) => {
      const select = e.target;
      select.disabled = true;
      try {
        await api.moveLead(lead.id, select.value);
        toast('Estágio atualizado.', 'success');
        changed = true;
        await load();
      } catch (err) {
        toastError(err);
        select.value = lead.status;
        select.disabled = false;
      }
    });

    $('#ig-save', panel)?.addEventListener('click', async (e) => {
      const raw = $('#ig-followers', panel).value.trim();
      const followers = raw === '' ? null : Number(raw);
      if (followers !== null && (!Number.isInteger(followers) || followers < 0)) {
        toast('Informe os seguidores como um número inteiro (ou deixe em branco).', 'error');
        return;
      }
      try {
        await withLoading(e.currentTarget, () => api.updateLead(lead.id, {
          ig_last_post: $('#ig-last', panel).value,
          ig_engagement: $('#ig-eng', panel).value,
          ig_quality: $('#ig-quality', panel).value,
          ig_followers: followers,
        }));
        toast('Avaliação do Instagram salva.', 'success');
        changed = true;
        await load();
      } catch (err) { toastError(err); }
    });

    $('#ld-note-btn', panel).addEventListener('click', async (e) => {
      const ta = $('#ld-note', panel);
      const text = ta.value.trim();
      if (!text) { ta.focus(); return; }
      try {
        await withLoading(e.currentTarget, () => api.addNote(lead.id, text));
        toast('Anotação registrada.', 'success');
        changed = true;
        await load();
      } catch (err) { toastError(err); }
    });

    $('#ld-edit', panel).addEventListener('click', async () => {
      const saved = await openLeadForm({ lead });
      if (saved) { changed = true; await load(); }
    });

    $('#ld-delete', panel).addEventListener('click', async () => {
      const ok = await confirmDialog({
        title: 'Excluir lead',
        message: `Tem certeza que deseja excluir "${lead.company_name}"?`,
        detail: 'O lead e todo o seu histórico serão removidos permanentemente. Esta ação não pode ser desfeita.',
        confirmLabel: 'Excluir definitivamente',
        danger: true,
      });
      if (!ok) return;
      try {
        await api.deleteLead(lead.id);
        toast('Lead excluído.', 'success');
        changed = true;
        drawer.close();
      } catch (err) { toastError(err); }
    });
  };

  await load();
}
