/* Preenche a página com os dados de config.js e liga os botões de contato.
   Nada é enviado a servidor algum: o formulário só abre o WhatsApp com a mensagem pronta. */
(function () {
  'use strict';
  var cfg = window.SITE || {};
  var get = function (k) { return String(cfg[k] == null ? '' : cfg[k]).trim(); };
  var $$ = function (sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); };

  var LABELS = { responsible: 'seu nome ou razão social', deliveryDays: 'prazo de entrega', whatsapp: 'seu WhatsApp' };
  var phone = get('whatsapp').replace(/\D/g, '');
  var phoneOk = phone.length >= 10 && phone.length <= 15;
  var missing = [];

  function todo(el, key) {
    el.textContent = '[preencher: ' + (LABELS[key] || key) + ']';
    el.classList.add('todo');
    if (missing.indexOf(key) < 0) missing.push(key);
  }

  // Textos simples
  $$('[data-site]').forEach(function (el) {
    var key = el.getAttribute('data-site');
    var value = get(key);
    if (value) { el.textContent = key === 'cnpj' ? 'CNPJ ' + value : key === 'city' ? '· ' + value : value; }
    else if (el.hasAttribute('data-optional')) { el.textContent = ''; }
    else { todo(el, key); }
  });
  document.title = document.title.replace('GTech', get('brand') || 'GTech');

  // Preços: vazio significa "sob orçamento" (válido, não é pendência)
  $$('[data-price]').forEach(function (el) {
    var value = get(el.getAttribute('data-price'));
    var isQuote = !value || /or[çc]amento/i.test(value);  // "sob orçamento" não leva "A partir de"
    el.textContent = isQuote ? 'Sob orçamento' : (/^a partir/i.test(value) ? value : 'A partir de ' + value);
  });

  // Mensagem padrão e link do WhatsApp
  function waLink(text) {
    return 'https://wa.me/' + phone + '?text=' + encodeURIComponent(text);
  }
  var defaultMessage = (get('defaultMessage') || 'Olá! Quero saber mais.').replace('{brand}', get('brand') || '');

  $$('[data-cta]').forEach(function (a) {
    if (phoneOk) { a.href = waLink(defaultMessage); a.target = '_blank'; a.rel = 'noopener'; }
  });

  // Lista de contatos
  var rows = {
    whatsapp: phoneOk ? { href: waLink(defaultMessage), text: formatPhone(phone) } : null,
    email: get('email') ? { href: 'mailto:' + get('email'), text: get('email') } : null,
    instagram: get('instagram') ? { href: 'https://instagram.com/' + get('instagram').replace(/^@/, ''), text: '@' + get('instagram').replace(/^@/, '') } : null
  };
  Object.keys(rows).forEach(function (key) {
    var li = document.querySelector('[data-row="' + key + '"]');
    var a = document.querySelector('[data-link="' + key + '"]');
    if (!li || !a) return;
    if (rows[key]) { a.href = rows[key].href; a.textContent = rows[key].text; }
    else if (key === 'whatsapp') { a.removeAttribute('href'); todo(a, 'whatsapp'); }
    else { li.hidden = true; }
  });

  function formatPhone(d) {
    if (d.indexOf('55') === 0 && (d.length === 12 || d.length === 13)) {
      var local = d.slice(4);
      return '(' + d.slice(2, 4) + ') ' + local.slice(0, local.length - 4) + '-' + local.slice(-4);
    }
    return '+' + d;
  }

  // Formulário -> abre o WhatsApp com a mensagem pronta
  var form = document.getElementById('contact-form');
  var errBox = document.getElementById('form-error');
  function showError(msg) { errBox.textContent = msg; errBox.hidden = false; }
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    errBox.hidden = true;
    var nome = form.nome.value.trim();
    var empresa = form.empresa.value.trim();
    var msg = form.msg.value.trim();
    if (!nome || !empresa) { showError('Informe seu nome e o nome da empresa.'); return; }
    if (!phoneOk) { showError('O WhatsApp deste site ainda não foi configurado. Volte em instantes.'); return; }
    var text = 'Olá! Sou ' + nome + ', da empresa ' + empresa + '. Quero uma landing page.' + (msg ? '\n\n' + msg : '');
    window.open(waLink(text), '_blank', 'noopener');
  });

  // Aviso de configuração: aparece enquanto faltar algo obrigatório
  if (missing.length) document.getElementById('setup-banner').hidden = false;
})();
