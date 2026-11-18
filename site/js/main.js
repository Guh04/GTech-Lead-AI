/* GTech Digital Studio — comportamento do site (JavaScript puro, sem dependências). */
(() => {
  'use strict';
  const S = window.SITE || {};
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const finePointer = matchMedia('(hover: hover) and (pointer: fine)').matches;
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  /* ---------- contato: links gerados a partir de js/config.js ---------- */
  const wa = (key) => `https://wa.me/${S.whatsapp}?text=${encodeURIComponent((S.messages || {})[key] || (S.messages || {}).contato || '')}`;
  $$('[data-wa]').forEach((a) => { a.href = wa(a.dataset.wa); a.target = '_blank'; a.rel = 'noopener noreferrer'; });
  $$('[data-mail]').forEach((a) => { a.href = `mailto:${S.email}`; if (!a.classList.contains('mail')) a.textContent = S.email; });
  $$('[data-ig]').forEach((a) => { a.href = `https://instagram.com/${S.instagram}`; a.target = '_blank'; a.rel = 'noopener noreferrer'; a.textContent = `@${S.instagram}`; });
  $$('[data-legal]').forEach((el) => { el.textContent = [S.responsible, S.cnpj && `CNPJ ${S.cnpj}`, S.city].filter(Boolean).join(' · '); });
  $$('[data-year]').forEach((el) => { el.textContent = new Date().getFullYear(); });

  /* ---------- título do hero: palavra por palavra ---------- */
  const h1 = $('.hero h1');
  if (h1 && !reduce) {
    let i = 0;
    const split = (node) => {
      [...node.childNodes].forEach((child) => {
        if (child.nodeType === 3) {
          const frag = document.createDocumentFragment();
          child.textContent.split(/(\s+)/).forEach((part) => {
            if (!part) return;
            if (/^\s+$/.test(part)) { frag.append(' '); return; }
            const w = document.createElement('span'); w.className = 'w';
            const inner = document.createElement('span'); inner.className = 'wi'; inner.style.setProperty('--i', i++); inner.textContent = part;
            w.append(inner); frag.append(w);
          });
          child.replaceWith(frag);
        } else if (child.nodeType === 1) split(child);
      });
    };
    split(h1);
  }

  /* ---------- menu responsivo ---------- */
  const burger = $('.burger');
  const setMenu = (open) => {
    document.body.classList.toggle('menu-open', open);
    burger.setAttribute('aria-expanded', String(open));
    burger.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
  };
  burger.addEventListener('click', () => setMenu(!document.body.classList.contains('menu-open')));
  $$('.drawer a').forEach((a) => a.addEventListener('click', () => setMenu(false)));
  addEventListener('keydown', (e) => { if (e.key === 'Escape') setMenu(false); });
  matchMedia('(min-width: 901px)').addEventListener('change', (e) => { if (e.matches) setMenu(false); });

  /* ---------- rolagem: cabeçalho, botão flutuante, progresso da página e do processo ---------- */
  const hdr = $('.hdr');
  const fab = $('.wa-fab');
  const hero = $('.hero');
  const proc = $('.proc');
  const bar = $('.progress');
  const steps = $$('.step');
  let ticking = false;
  const onScroll = () => {
    const y = scrollY;
    hdr.classList.toggle('solid', y > 24);
    fab.classList.toggle('show', y > (hero ? hero.offsetHeight * 0.7 : 600));
    const max = document.documentElement.scrollHeight - innerHeight;
    if (bar) bar.style.setProperty('--sp', max > 0 ? Math.min(1, y / max).toFixed(4) : 0);
    if (proc) {
      const r = proc.getBoundingClientRect();
      const vh = innerHeight;
      const p = Math.min(1, Math.max(0, (vh * 0.8 - r.top) / (r.height + vh * 0.2)));
      proc.style.setProperty('--p', reduce ? 1 : p.toFixed(3));
      steps.forEach((s, i) => s.classList.toggle('on', reduce || p >= (i + 0.35) / steps.length));
    }
    ticking = false;
  };
  addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, { passive: true });
  addEventListener('resize', onScroll);
  onScroll();

  /* ---------- revelação progressiva ao rolar ---------- */
  const rv = $$('.rv');
  if (reduce || !('IntersectionObserver' in window)) {
    rv.forEach((el) => el.classList.add('in'));
  } else {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } });
    }, { threshold: 0.14, rootMargin: '0px 0px -6% 0px' });
    rv.forEach((el) => io.observe(el));
  }

  /* ---------- hero: telas dos projetos alternando e "rolando" sozinhas ---------- */
  const rotators = $$('[data-rotate]');
  const label = $('[data-rotate-label]');
  if (rotators.length) {
    const count = $$('img', rotators[0]).length;
    // As telas seguintes carregam em segundo plano logo após a abertura, para a troca nunca mostrar tela vazia.
    const warm = () => rotators.forEach((box) => $$('img', box).forEach((im) => { im.loading = 'eager'; }));
    if (document.readyState === 'complete') warm(); else addEventListener('load', warm, { once: true });
    const show = (idx) => {
      rotators.forEach((box) => {
        $$('img', box).forEach((im, k) => {
          if (k === idx) {
            im.getAnimations().forEach((a) => a.cancel());
            im.classList.toggle('leaving', false);
            im.classList.add('on');
            if (!reduce && im.animate) {
              // desliza a página até uma parte do conteúdo, como se alguém estivesse navegando
              const travel = Math.max(0, Math.min(im.offsetHeight - box.offsetHeight, box.offsetHeight * 1.15));
              im.animate([{ transform: 'translateY(0)' }, { transform: `translateY(-${travel}px)` }],
                { duration: 5400, delay: 900, easing: 'cubic-bezier(.45,0,.2,1)', fill: 'both' });
            }
          } else if (im.classList.contains('on')) {
            // a tela antiga fica por baixo até a nova estar 100% visível (sem vão entre as duas)
            im.classList.toggle('on', false);
            im.classList.toggle('leaving', true);
            setTimeout(() => {
              im.classList.toggle('leaving', false);
              if (!im.classList.contains('on')) im.getAnimations().forEach((a) => a.cancel());
            }, 1500);
          }
        });
      });
      if (label) label.textContent = $$('img', rotators[0])[idx].dataset.name;
    };
    if (!reduce && count > 1) {
      let idx = 0;
      let timer = null;
      const ready = (n) => rotators.every((box) => $$('img', box)[n].complete);
      const step = () => {
        const next = (idx + 1) % count;
        if (!ready(next)) { timer = setTimeout(step, 400); return; }  // espera a próxima tela carregar
        idx = next;
        show(idx);
        timer = setTimeout(step, 7000);
      };
      const start = () => { stop(); timer = setTimeout(step, 7000); };
      const stop = () => { if (timer) { clearTimeout(timer); timer = null; } };
      show(0);
      start();
      document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); else start(); });
    }
  }

  /* ---------- hero: paralaxe suave dos dispositivos com o mouse ---------- */
  const stage = $('[data-stage]');
  if (stage && hero && finePointer && !reduce) {
    let raf = 0;
    hero.addEventListener('pointermove', (e) => {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        const r = hero.getBoundingClientRect();
        stage.style.setProperty('--mx', (((e.clientX - r.left) / r.width) * 2 - 1).toFixed(3));
        stage.style.setProperty('--my', (((e.clientY - r.top) / r.height) * 2 - 1).toFixed(3));
        raf = 0;
      });
    });
    hero.addEventListener('pointerleave', () => { stage.style.setProperty('--mx', 0); stage.style.setProperty('--my', 0); });
  }

  /* ---------- cards do portfólio: inclinação sutil seguindo o mouse ---------- */
  if (finePointer && !reduce) {
    $$('[data-tilt]').forEach((card) => {
      card.addEventListener('pointermove', (e) => {
        const r = card.getBoundingClientRect();
        const px = (e.clientX - r.left) / r.width - 0.5;
        const py = (e.clientY - r.top) / r.height - 0.5;
        card.classList.add('moving');
        card.style.transform = `perspective(1200px) rotateX(${(-py * 5).toFixed(2)}deg) rotateY(${(px * 6).toFixed(2)}deg) translateY(-8px)`;
      });
      card.addEventListener('pointerleave', () => { card.classList.remove('moving'); card.style.transform = ''; });
    });
  }

  /* ---------- rolagem suave para âncoras ---------- */
  $$('a[href^="#"]').forEach((a) => a.addEventListener('click', (e) => {
    const id = a.getAttribute('href');
    if (id.length < 2) return;
    const el = document.getElementById(id.slice(1));
    if (!el) return;
    e.preventDefault();
    el.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
    history.replaceState(null, '', id);
  }));
})();
