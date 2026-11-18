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
  document.title = (get('brand') || 'Site') + ' | ' + (get('eyebrow') || '');

  // Logo no topo (se configurado); senão fica o nome em letra cursiva
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
    var d = phone, local = d.slice(4);
    wa.textContent = d.indexOf('55') === 0 && (d.length === 12 || d.length === 13)
      ? '(' + d.slice(2, 4) + ') ' + local.slice(0, local.length - 4) + '-' + local.slice(-4) : '+' + d;
  } else { wa.textContent = '[preencher: whatsapp]'; wa.classList.add('todo'); }
  var handle = get('instagram').replace(/^@/, '');
  if (handle) {
    ig.href = 'https://instagram.com/' + encodeURIComponent(handle); ig.textContent = '@' + handle;
    $('#insta-link').href = ig.href;
  } else { ig.textContent = '[preencher: instagram]'; ig.classList.add('todo'); $('#insta-link').hidden = true; pending.push('instagram'); }
  if (get('email')) { mail.href = 'mailto:' + get('email'); mail.textContent = get('email'); }
  else $('[data-row="email"]').hidden = true;

  // Serviços
  var services = $('#services');
  (cfg.services || []).forEach(function (s) {
    var card = el('article', 'card');
    card.appendChild(el('h3', null, s.title));
    card.appendChild(el('p', null, s.text));
    services.appendChild(card);
  });

  // Galeria (ou espaços marcados enquanto não houver arquivos)
  var gallery = $('#gallery');
  var items = cfg.gallery || [];
  if (items.length) {
    items.forEach(function (g) {
      var fig = el('figure', 'tile');
      if (g.type === 'video') {
        var v = document.createElement('video');
        v.src = g.src + '#t=' + (g.at || 0.1); v.controls = true; v.preload = 'metadata'; v.playsInline = true; v.setAttribute('aria-label', g.alt || 'Vídeo');
        fig.appendChild(v);
      } else {
        var img = document.createElement('img');
        img.src = g.src; img.alt = g.alt || ''; img.loading = 'lazy';
        fig.appendChild(img);
      }
      gallery.appendChild(fig);
    });
  } else {
    for (var i = 0; i < 8; i++) {
      var ph = el('figure', 'tile placeholder');
      ph.appendChild(el('span', 'todo', 'Adicione aqui'));
      gallery.appendChild(ph);
    }
    pending.push('galeria de trabalhos');
  }

  // Depoimentos: a seção só aparece se houver depoimentos reais cadastrados
  var tList = (cfg.testimonials || []).filter(function (t) { return t && (t.text || t.image); });
  if (tList.length) {
    var tBox = $('#testimonials');
    tList.forEach(function (t) {
      var fig = el('figure', 'quote' + (t.image && !t.text ? ' quote-img' : ''));
      if (t.image) {
        var im = document.createElement('img');
        im.src = t.image; im.alt = t.alt || ('Mensagem de ' + (t.name || 'cliente')); im.loading = 'lazy';
        fig.appendChild(im);
      }
      if (t.text) {
        var bq = el('blockquote', null, '“' + t.text + '”');
        fig.appendChild(bq);
      }
      if (t.name) {
        var cap = el('figcaption');
        cap.appendChild(el('b', null, t.name));
        if (t.context) cap.appendChild(el('span', null, t.context));
        fig.appendChild(cap);
      }
      tBox.appendChild(fig);
    });
    $('#depoimentos').hidden = false;
    $('#nav-testimonials').hidden = false;
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
    var text = 'Olá! Sou ' + nome + '. Quero um orçamento para: ' + form.tipo.value + '.' + (det ? '\nData e local: ' + det : '');
    window.open(waLink(text), '_blank', 'noopener');
  });

  // Aviso de pendências (some quando tudo estiver preenchido)
  if (pending.length) {
    var b = $('#setup-banner');
    b.textContent = 'Versão de revisão. Falta preencher em config.js: ' + pending.join(', ') + '. Textos marcados [CONFIRMAR] no arquivo precisam ser conferidos.';
    b.hidden = false;
  }
})();
