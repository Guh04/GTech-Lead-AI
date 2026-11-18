/* =============================================================================
   BARBEARIA VICTOR ORTIZ — conteúdo da página. Edite SOMENTE este arquivo.
   Fonte: bio pública do Instagram @barbeariavictorortiz. Nada foi inventado:
   o que não está no perfil fica vazio (aparece em amarelo) ou marcado [CONFIRMAR].
   ============================================================================= */
window.SITE = {
  brand: "Barbearia Victor Ortiz",
  logo: "",                      // [CONFIRMAR] pedir o arquivo da logo ao cliente e salvar em assets/
  instagram: "barbeariavictorortiz",
  whatsapp: "5515981229144",     // do link da bio do Instagram
  email: "",                     // opcional
  city: "Sorocaba/SP",
  responsible: "",               // opcional
  cnpj: "",                      // opcional

  eyebrow: "Barbearia em Sorocaba · Desde 2016",
  headline: "Corte com precisão e atendimento personalizado",
  subheadline: "Cortes modernos e clássicos para adultos e crianças, em Sorocaba desde 2016. Agende seu horário pelo WhatsApp.",

  // [CONFIRMAR] com o cliente: serviços reais, e se faz barba (a logo cita "cabelo e barba")
  services: [
    { title: "Cortes modernos", text: "Cortes atuais, feitos com precisão e do jeito que você pediu." },
    { title: "Cortes clássicos", text: "O corte tradicional bem executado, com acabamento caprichado." },
    { title: "Adulto e infantil", text: "Atendimento para todas as idades, com o mesmo cuidado para os pequenos." }
  ],

  // Galeria: só com fotos que o cliente autorizar (ex.: do próprio Instagram, com permissão). Salvar em assets/.
  gallery: [],

  // Depoimentos: só reais e autorizados. A seção só aparece quando houver pelo menos um.
  testimonials: [],

  // [CONFIRMAR] ajustar ao jeito real de agendar dele
  steps: [
    { title: "Chame no WhatsApp", text: "Envie uma mensagem com o serviço e o dia que prefere." },
    { title: "Combine o horário", text: "A barbearia confirma o horário disponível." },
    { title: "Venha e relaxe", text: "É só chegar no horário combinado." }
  ],

  priceNote: "Consulte os valores e os horários livres direto pelo WhatsApp.",

  // [CONFIRMAR] respostas reais (endereço, horários, formas de pagamento etc.)
  faq: [
    { q: "Como agendo um horário?", a: "Chame no WhatsApp e informe o serviço e o dia que prefere." },
    { q: "Atendem crianças?", a: "Sim, o atendimento é para adultos e crianças." },
    { q: "Posso ver exemplos de trabalhos?", a: "Sim, veja o Instagram @barbeariavictorortiz." }
  ],

  defaultMessage: "Olá! Vi o site da {brand} e quero agendar um horário."
};
