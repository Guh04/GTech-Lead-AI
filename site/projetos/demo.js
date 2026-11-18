/* Comportamento compartilhado pelos 4 sites demonstrativos (JavaScript puro). */
(() => {
  // Menu responsivo
  const btn = document.querySelector('.mb');
  const nav = document.querySelector('.links');
  if (btn && nav) {
    const set = (open) => { nav.classList.toggle('open', open); btn.setAttribute('aria-expanded', String(open)); };
    btn.addEventListener('click', () => set(!nav.classList.contains('open')));
    nav.addEventListener('click', (e) => { if (e.target.closest('a')) set(false); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') set(false); });
  }

  // Formulários de demonstração: validam e respondem, mas NÃO enviam nada a lugar nenhum.
  document.querySelectorAll('form.demo-form').forEach((form) => {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      if (!form.checkValidity()) { form.reportValidity(); return; }
      const box = document.createElement('div');
      box.className = 'demo-ok';
      box.setAttribute('role', 'status');
      box.innerHTML = '<strong>Solicitação de exemplo registrada.</strong><span>Nesta demonstração nenhum dado é enviado. No site real, este formulário abriria o WhatsApp ou o e-mail da empresa.</span>';
      form.replaceWith(box);
      box.scrollIntoView({ block: 'nearest', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    });
  });

  // Links "#" sem destino (botões de exemplo) não devem pular a página para o topo.
  document.querySelectorAll('a[href="#"]').forEach((a) => a.addEventListener('click', (e) => {
    e.preventDefault();
    const target = document.querySelector('form.demo-form, #contato, #agendar, #orcamento');
    if (target) target.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'center' });
  }));
})();
