/* =============================================================================
   VEM DE STORY — conteúdo da página. Edite SOMENTE este arquivo.
   - Campos vazios ("") ou listas vazias aparecem em amarelo na página.
   ============================================================================= */
window.SITE = {
  brand: "Vem de Story",
  logo: "assets/logo-claro.png",   // versão clara, fundo transparente (original em assets/logo.png)
  instagram: "vemdestory",
  whatsapp: "5515992899935",
  email: "",                     // opcional
  city: "Sorocaba/SP",
  responsible: "",               // opcional: nome ou razão social, para o rodapé
  cnpj: "",                      // opcional

  eyebrow: "Storymaker em Sorocaba",
  headline: "Transforme momentos em conteúdo que conecta",
  subheadline: "Cobertura de casamentos, festas infantis e eventos em vídeos pensados para o Instagram, para você reviver e compartilhar cada detalhe.",

  // Serviços. Troque, apague ou acrescente conforme o que ela realmente oferece.
  services: [
    { title: "Casamentos", text: "Os momentos mais especiais do dia registrados em vídeos curtos, prontos para os stories e para guardar para sempre." },
    { title: "Festas infantis", text: "Cada sorriso e cada detalhe da festa, registrados com carinho e transformados em conteúdo para a família compartilhar." },
    { title: "Eventos e marcas", text: "Cobertura de eventos, inaugurações e ações de empresas, para sua marca aparecer com mais presença nas redes." }
  ],

  // Galeria. Coloque os arquivos na pasta assets/ e liste aqui (só com autorização de quem aparece).
  // Exemplos:  { src: "assets/casamento-01.jpg", alt: "Casamento de ..." },
  //            { src: "assets/festa-01.mp4", alt: "Festa infantil", type: "video" }
  gallery: [
    { src: "assets/festa3.mp4", alt: "Vídeo de festa infantil", type: "video" },
    { src: "assets/natal-01.mp4", alt: "Vídeo de evento de Natal", type: "video" },
    { src: "assets/bloom.mp4", alt: "Vídeo de evento: Bloom", type: "video" },
    { src: "assets/fest2.mp4", alt: "Vídeo de trabalho da Vem de Story", type: "video" },
    { src: "assets/natal-02.mp4", alt: "Vídeo de evento de Natal (completo)", type: "video", at: 4 }   // "at" = segundo usado como miniatura
  ],

  // Depoimentos. A seção SÓ aparece quando houver pelo menos um. Use apenas feedbacks REAIS,
  // com autorização de quem enviou. Dois formatos (pode misturar):
  //   texto:  { text: "Amei o resultado!", name: "Ana Souza", context: "Casamento, 2025" }
  //   print:  { image: "assets/feedback-01.jpg", name: "Cliente de festa infantil", alt: "Print do feedback" }
  //           (apague dados pessoais do print, como telefone e sobrenome, se a pessoa não autorizou)
  testimonials: [],

  // Como funciona. Ajuste para o processo real dela.
  steps: [
    { title: "Você conta sobre o evento", text: "Tipo de evento, data, local e o que não pode ficar de fora." },
    { title: "Receba a proposta", text: "Enviamos o que está incluso, o valor e as condições, por escrito." },
    { title: "Reserva da data", text: "Com a proposta aprovada, sua data fica reservada." },
    { title: "Dia do evento", text: "A gente cuida do registro enquanto você aproveita o momento." }
  ],

  // Valores: vazio = "Sob orçamento"
  priceNote: "Cada evento é único. Conte o que você precisa e receba uma proposta por escrito.",

  faq: [
    { q: "Como peço um orçamento?", a: "Chame no WhatsApp informando o tipo de evento, a data, o local e o horário aproximado." },
    { q: "Você atende fora de Sorocaba?", a: "A atuação principal é em Sorocaba e região. Para outras cidades, consulte pelo WhatsApp." },
    { q: "Posso ver exemplos de trabalhos?", a: "Sim. Veja a galeria desta página e o Instagram @vemdestory." }
  ],

  defaultMessage: "Olá! Vi o site da {brand} e quero um orçamento."
};
