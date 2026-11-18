/* GTech Digital Studio — comportamento do site (JavaScript puro, sem dependências). */
(() => {
  'use strict';
  const S = window.SITE || {};
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  /* ---------- contato: links gerados a partir de js/config.js ---------- */
  const wa = (key) => `https://wa.me/${S.whatsapp}?text=${encodeURIComponent((S.messages || {})[key] || (S.messages || {}).contato || '')}`;
  $$('[data-wa]').forEach((a) => { a.href = wa(a.dataset.wa); a.target = '_blank'; a.rel = 'noopener noreferrer'; });
  $$('[data-mail]').forEach((a) => { a.href = `mailto:${S.email}`; a.textContent = S.email; });
  $$('[data-ig]').forEach((a) => { a.href = `https://instagram.com/${S.instagram}`; a.target = '_blank'; a.rel = 'noopener noreferrer'; a.textContent = `@${S.instagram}`; });
  $$('[data-legal]').forEach((el) => { el.textContent = [S.responsible, S.cnpj && `CNPJ ${S.cnpj}`, S.city].filter(Boolean).join(' · '); });
  $$('[data-year]').forEach((el) => { el.textContent = new Date().getFullYear(); });

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

  /* ---------- cabeçalho, botão flutuante e progresso do processo (um único listener de rolagem) ---------- */
  const hdr = $('.hdr');
  const fab = $('.wa-fab');
  const hero = $('.hero');
  const proc = $('.proc');
  const steps = $$('.step');
  let ticking = false;
  const onScroll = () => {
    const y = scrollY;
    hdr.classList.toggle('solid', y > 24);
    fab.classList.toggle('show', y > (hero ? hero.offsetHeight * 0.7 : 600));
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

  /* ---------- hero: telas dos projetos alternando com suavidade ---------- */
  const rotators = $$('[data-rotate]');
  if (rotators.length && !reduce) {
    let i = 0;
    const tick = () => {
      i += 1;
      rotators.forEach((box) => {
        const imgs = $$('img', box);
        imgs.forEach((im, k) => im.classList.toggle('on', k === i % imgs.length));
      });
      const label = $('[data-rotate-label]');
      const first = $('[data-rotate]');
      if (label && first) label.textContent = $$('img', first)[i % $$('img', first).length].dataset.name;
    };
    let timer = setInterval(tick, 4600);
    document.addEventListener('visibilitychange', () => {
      clearInterval(timer);
      if (!document.hidden) timer = setInterval(tick, 4600);
    });
  }

  /* ---------- rolagem suave para âncoras (com foco acessível) ---------- */
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
