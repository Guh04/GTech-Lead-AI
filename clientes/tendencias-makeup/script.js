/* Monta a página a partir de config.js. Tudo é inserido com textContent (sem HTML dinâmico).
   Nada é enviado a servidor algum: o formulário só abre o WhatsApp com a mensagem pronta. */
(function () {
  'use strict';
  var cfg = window.SITE || {};
  var get = function (k) { return String(cfg[k] == null ? '' : cfg[k]).trim(); };
  var $ = function (sel) { return document.querySelector(sel); };
  var $$ = function (sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); };
  var pending = [];

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  // Textos simples
  $$('[data-site]').forEach(function (node) {
    var key = node.getAttribute('data-site');
    var value = get(key);
    if (value) node.textContent = value;
    else if (node.hasAttribute('data-optional')) node.textContent = '';
    else { node.textContent = '[preencher: ' + key + ']'; node.classList.add('todo'); pending.push(key); }
  });
  document.title = get('brand') + ' | ' + get('eyebrow');

  // Logo no topo (se configurado)
  if (get('logo')) {
    var logoLink = $('.logo');
    var logoImg = document.createElement('img');
    logoImg.src = get('logo'); logoImg.alt = get('brand'); logoImg.className = 'logo-img';
    logoLink.textContent = ''; logoLink.appendChild(logoImg);
  }

  // WhatsApp
  var phone = get('whatsapp').replace(/\D/g, '');
  var phoneOk = phone.length >= 10 && phone.length <= 15;
  var waLink = function (text) { return 'https://wa.me/' + phone + '?text=' + encodeURIComponent(text); };
  var defaultMessage = (get('defaultMessage') || 'Olá!').replace('{brand}', get('brand'));
  $$('[data-cta]').forEach(function (a) {
    if (phoneOk) { a.href = waLink(defaultMessage); a.target = '_blank'; a.rel = 'noopener'; }
  });
  if (!phoneOk) pending.push('whatsapp');

  // Contatos
  var wa = $('#c-wa'), ig = $('#c-ig'), mail = $('#c-mail');
  if (phoneOk) {
    wa.href = waLink(defaultMessage);
    var local = phone.slice(4);
    wa.textContent = phone.indexOf('55') === 0 && (phone.length === 12 || phone.length === 13)
      ? '(' + phone.slice(2, 4) + ') ' + local.slice(0, local.length - 4) + '-' + local.slice(-4) : '+' + phone;
  } else { wa.textContent = '[preencher: whatsapp]'; wa.classList.add('todo'); }
  var handle = get('instagram').replace(/^@/, '');
  if (handle) {
    ig.href = 'https://instagram.com/' + encodeURIComponent(handle); ig.textContent = '@' + handle;
    $('#insta-link').href = ig.href;
  } else { ig.textContent = '[preencher: instagram]'; ig.classList.add('todo'); $('#insta-link').hidden = true; pending.push('instagram'); }
  if (get('email')) { mail.href = 'mailto:' + get('email'); mail.textContent = get('email'); }
  else $('[data-row="email"]').hidden = true;

  // Categorias e benefícios (cartões simples)
  function cards(boxId, list) {
    var box = $(boxId);
    (list || []).forEach(function (s) {
      var card = el('article', 'card');
      card.appendChild(el('h3', null, s.title));
      card.appendChild(el('p', null, s.text));
      box.appendChild(card);
    });
  }
  cards('#categories', cfg.categories);
  cards('#benefits', cfg.benefits);

  // Produtos: só aparecem os cadastrados; sem nenhum, mostra espaços marcados (nunca produto inventado)
  var productBox = $('#products');
  var products = cfg.products || [];
  if (products.length) {
    products.forEach(function (p) {
      var card = el('article', 'product');
      var img = document.createElement('img');
      img.src = p.src; img.alt = p.name || 'Produto'; img.loading = 'lazy';
      card.appendChild(img);
      if (p.category) card.appendChild(el('span', 'product-cat', p.category));
      card.appendChild(el('h3', null, p.name || ''));
      if (p.price) card.appendChild(el('p', 'price', p.price));
      var a = el('a', 'btn btn-ghost btn-sm', 'Pedir este produto');
      if (phoneOk) { a.href = waLink('Olá! Quero o produto: ' + (p.name || '')); a.target = '_blank'; a.rel = 'noopener'; }
      card.appendChild(a);
      productBox.appendChild(card);
    });
  } else {
    for (var i = 0; i < 4; i++) {
      var ph = el('div', 'product placeholder');
      ph.appendChild(el('span', 'todo', 'Foto e nome do produto'));
      productBox.appendChild(ph);
    }
    pending.push('produtos em destaque (fotos reais)');
  }

  // Avaliações: a seção só aparece com depoimentos reais cadastrados
  var tList = (cfg.testimonials || []).filter(function (t) { return t && t.text; });
  if (tList.length) {
    var tBox = $('#testimonials');
    tList.forEach(function (t) {
      var fig = el('figure', 'quote');
      fig.appendChild(el('blockquote', null, '“' + t.text + '”'));
      if (t.name) {
        var cap = el('figcaption');
        cap.appendChild(el('b', null, t.name));
        if (t.context) cap.appendChild(el('span', null, t.context));
        fig.appendChild(cap);
      }
      tBox.appendChild(fig);
    });
    $('#depoimentos').hidden = false;
  }

  // Passos e perguntas
  var steps = $('#steps');
  (cfg.steps || []).forEach(function (s, i) {
    var li = el('li');
    li.appendChild(el('span', 'step-n', String(i + 1)));
    li.appendChild(el('h3', null, s.title));
    li.appendChild(el('p', null, s.text));
    steps.appendChild(li);
  });
  var faq = $('#faq');
  (cfg.faq || []).forEach(function (f) {
    var d = el('details');
    d.appendChild(el('summary', null, f.q));
    d.appendChild(el('p', null, f.a));
    faq.appendChild(d);
  });

  // Formulário -> WhatsApp
  var form = $('#contact-form'), err = $('#form-error');
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    err.hidden = true;
    var nome = form.nome.value.trim();
    if (!nome) { err.textContent = 'Informe seu nome.'; err.hidden = false; return; }
    if (!phoneOk) { err.textContent = 'O WhatsApp deste site ainda não foi configurado.'; err.hidden = false; return; }
    var det = form.detalhes.value.trim();
    var text = 'Olá! Sou ' + nome + '. Quero fazer um pedido. Categoria: ' + form.tipo.value + '.' + (det ? '\nProcuro: ' + det : '');
    window.open(waLink(text), '_blank', 'noopener');
  });

  // Aviso de pendências (some quando tudo estiver resolvido)
  var confirmar = JSON.stringify(cfg).indexOf('[CONFIRMAR]') !== -1;
  if (pending.length || confirmar) {
    var b = $('#setup-banner');
    b.textContent = 'Versão de revisão. ' + (pending.length ? 'Falta preencher em config.js: ' + pending.join(', ') + '. ' : '') +
      (confirmar ? 'Confira os textos marcados [CONFIRMAR] com a loja.' : '');
    b.hidden = false;
  }
})();
