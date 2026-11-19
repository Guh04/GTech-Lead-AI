// Importação de leads por planilha (.xlsx / .csv): escolhe o arquivo, mostra uma prévia e só então grava.
import { html, setHtml, $, formatNumber } from '../utils.js';
import { openModal, renderIcons, toast, toastError, withLoading, icon } from '../ui.js';
import { api } from '../api.js';

const MAX_BYTES = 5 * 1024 * 1024;

const pickStep = () => html`
  <p class="muted" style="margin-top:0">Envie uma planilha <b>.xlsx</b> ou <b>.csv</b> com um lead por linha. A primeira linha precisa ser o cabeçalho.</p>
  <label class="dropzone" for="imp-file" style="display:flex;flex-direction:column;align-items:center;gap:8px;padding:28px 16px;border:1px dashed var(--border-strong, #475569);border-radius:12px;cursor:pointer;text-align:center">
    ${icon('file-spreadsheet')}
    <strong id="imp-name">Clique para escolher a planilha</strong>
    <span class="muted" style="font-size:.85rem">até 5 MB e 2.000 leads por vez</span>
    <input id="imp-file" type="file" accept=".xlsx,.csv,.txt,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" hidden>
  </label>
  <div class="alert" data-tone="error" id="imp-alert" hidden style="margin-top:12px"></div>
  <details style="margin-top:14px"><summary class="muted" style="cursor:pointer">Quais colunas são reconhecidas?</summary>
    <p class="muted" style="font-size:.85rem">Empresa (ou "Nome do negócio" — <b>obrigatória</b>), Responsável, Segmento (ou "Ramo"), Cidade (ou "Bairro / Cidade"), Estado, Telefone, WhatsApp
    (ou "WhatsApp / Telefone"), Instagram, Facebook, Site (ou "Site atual"), Landing page, Status, Observações. Qualquer outra coluna (ex.: "Mensagem sugerida") é guardada nas observações do lead.
    Pontuação e prioridade são calculadas pelo sistema. Leads repetidos (mesma empresa na cidade, telefone, WhatsApp ou site) são ignorados.</p>
  </details>`;

const stat = (n, label, tone) => html`<div class="card" style="padding:12px 16px;flex:1;min-width:120px"><div style="font-size:1.6rem;font-weight:700;${tone ? `color:var(--${tone})` : ''}">${formatNumber(n)}</div><div class="muted" style="font-size:.85rem">${label}</div></div>`;

function previewStep(file, r) {
  const cols = r.columns;
  return html`
    <p style="margin-top:0"><b>${file.name}</b> · ${formatNumber(r.total)} linha(s) lidas</p>
    <div class="row" style="gap:10px;flex-wrap:wrap">
      ${stat(r.valid, 'serão importados', 'green')}
      ${stat(r.duplicates, 'já existem (ignorados)', 'yellow')}
      ${stat(r.invalid, 'com erro (ignorados)', r.invalid ? 'red' : '')}
    </div>
    <p class="muted" style="font-size:.85rem;margin:12px 0 4px">Colunas reconhecidas: ${cols.recognized.join(', ') || '—'}</p>
    ${cols.as_notes.length ? html`<p class="muted" style="font-size:.85rem;margin:0 0 4px">Guardadas nas observações: ${cols.as_notes.join(', ')}</p>` : ''}
    ${cols.ignored.length ? html`<p class="muted" style="font-size:.85rem;margin:0 0 4px">Ignoradas: ${cols.ignored.join(', ')}</p>` : ''}
    ${r.preview.length ? html`
      <div class="table-wrap" style="margin-top:12px"><table class="table"><thead><tr><th>Empresa</th><th>Segmento</th><th>Cidade</th><th>Contato</th></tr></thead><tbody>
        ${r.preview.map((l) => html`<tr><td>${l.company_name}</td><td>${l.segment || '—'}</td><td>${l.city || '—'}</td><td>${l.whatsapp || l.phone || '—'}</td></tr>`)}
      </tbody></table></div>
      ${r.valid > r.preview.length ? html`<p class="faint" style="font-size:.8rem;margin:4px 0 0">Prévia dos primeiros ${r.preview.length} leads.</p>` : ''}` : ''}
    ${r.errors.length ? html`<details style="margin-top:12px" open><summary style="cursor:pointer;color:var(--red)">${r.invalid} linha(s) com problema</summary>
      <ul style="margin:6px 0 0;padding-left:18px;font-size:.85rem">${r.errors.map((e) => html`<li>Linha ${e.line} — <b>${e.name}</b>: ${e.reason}</li>`)}</ul>
      ${r.invalid > r.errors.length ? html`<p class="faint" style="font-size:.8rem">…e mais ${r.invalid - r.errors.length}.</p>` : ''}</details>` : ''}
    ${r.duplicate_rows.length ? html`<details style="margin-top:8px"><summary class="muted" style="cursor:pointer">${r.duplicates} já cadastrado(s)</summary>
      <ul style="margin:6px 0 0;padding-left:18px;font-size:.85rem">${r.duplicate_rows.map((e) => html`<li>Linha ${e.line} — ${e.name}</li>`)}</ul></details>` : ''}`;
}

/** Abre o assistente de importação. Resolve true se algum lead foi importado. */
export function openLeadImport() {
  return new Promise((resolve) => {
    let imported = false;
    let file = null;
    const modal = openModal({
      title: 'Importar planilha de leads',
      body: pickStep(),
      footer: html`<button type="button" class="btn" data-close>Cancelar</button>`,
      onClose: () => resolve(imported),
    });
    const body = modal.bodySlot;
    const foot = modal.footSlot;

    const showError = (msg) => {
      const box = $('#imp-alert', body);
      if (!box) return toast(msg, 'error');
      setHtml(box, html`${icon('circle-alert')}<div>${msg}</div>`);
      box.hidden = false;
      renderIcons();
    };

    const restart = () => {
      file = null;
      setHtml(body, pickStep());
      setHtml(foot, html`<button type="button" class="btn" data-close>Cancelar</button>`);
      bindPicker();
      renderIcons();
    };

    async function analyze(chosen) {
      file = chosen;
      $('#imp-name', body).textContent = `Lendo ${chosen.name}...`;
      let result;
      try {
        result = await api.importLeads(chosen, true);
      } catch (err) {
        $('#imp-name', body).textContent = 'Clique para escolher a planilha';
        return showError(err.message);
      }
      setHtml(body, previewStep(chosen, result));
      setHtml(foot, html`
        <button type="button" class="btn" id="imp-back">Escolher outro arquivo</button>
        <button type="button" class="btn btn-primary" id="imp-go" ${result.valid ? '' : 'disabled'}>${icon('upload', 'icon-sm')}Importar ${formatNumber(result.valid)} lead(s)</button>`);
      renderIcons();
      $('#imp-back', foot).addEventListener('click', restart);
      $('#imp-go', foot).addEventListener('click', async (e) => {
        try {
          const done = await withLoading(e.currentTarget, () => api.importLeads(chosen, false));
          imported = done.imported > 0;
          toast(`${done.imported} lead(s) importado(s)${done.duplicates ? `, ${done.duplicates} já existiam` : ''}${done.invalid ? `, ${done.invalid} com erro` : ''}.`, done.imported ? 'success' : 'info');
          modal.close();
        } catch (err) { toastError(err); }
      });
    }

    function bindPicker() {
      $('#imp-file', body).addEventListener('change', (e) => {
        const chosen = e.target.files?.[0];
        if (!chosen) return;
        if (chosen.size > MAX_BYTES) return showError('Arquivo muito grande (máximo de 5 MB).');
        analyze(chosen);
      });
    }
    bindPicker();
  });
}
