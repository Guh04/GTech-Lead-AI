/* =============================================================================
   TENDÊNCIAS MAKEUP — conteúdo da página. Edite SOMENTE este arquivo.
   - Campos vazios ("") ou listas vazias aparecem em amarelo na página.
   - Nada aqui é produto, preço ou avaliação real: só entra o que a dona confirmar.
   ============================================================================= */
window.SITE = {
  brand: "Tendências Makeup",
  logo: "",                        // ex.: "assets/logo.png" (arquivo enviado pela dona)
  instagram: "tendenciasmakeups",
  whatsapp: "5515998421731",
  email: "",                       // opcional
  city: "",                        // [CONFIRMAR] ex.: "Sorocaba/SP"; deixe vazio se for só online
  responsible: "",                 // opcional: nome/razão social para o rodapé
  cnpj: "",                        // opcional

  eyebrow: "Maquiagem, cosméticos e acessórios",
  headline: "Maquiagem que acompanha as tendências",
  subheadline: "Sua make completa do R$ 10,00 ao premium. Loja física e on-line, com envio para todo o Brasil. Escolha pelas categorias e peça direto no WhatsApp.",

  // Categorias da loja.
  categories: [
    { title: "Maquiagem", text: "Base, pó, blush, batom, sombras e tudo para o rosto." },
    { title: "Unhas", text: "Esmaltes e itens para as unhas." },
    { title: "Cílios postiços", text: "Opções para realçar o olhar." },
    { title: "Cabelo", text: "Produtos e acessórios para o cabelo." },
    { title: "Acessórios", text: "Detalhes que completam o look." },
    { title: "Infantil", text: "Linha de maquiagem e beleza infantil." }
  ],

  // Produtos em destaque. Coloque as fotos REAIS em assets/ e liste aqui.
  // Exemplo: { src: "assets/batom-01.jpg", name: "Nome do produto", price: "R$ 29,90", category: "Maquiagem" }
  // Só mostre preço se for o preço real. Sem produtos cadastrados, aparecem espaços marcados.
  products: [],

  // Avaliações: a seção SÓ aparece com depoimentos REAIS e autorizados.
  //   { text: "Amei os produtos!", name: "Nome", context: "Cliente" }
  testimonials: [],

  // Benefícios. Confira cada um antes de publicar: só deixe o que a loja realmente cumpre.
  benefits: [
    { title: "Envio para todo o Brasil", text: "[CONFIRMAR] Enviamos para o seu endereço. Combine prazo e frete pelo WhatsApp." },
    { title: "Atendimento pelo WhatsApp", text: "Tire dúvidas, peça indicação de produtos e feche seu pedido direto com a loja." },
    { title: "Compra segura", text: "[CONFIRMAR] Formas de pagamento combinadas com a loja antes do envio." }
  ],

  steps: [
    { title: "Escolha os produtos", text: "Veja as categorias e os destaques, ou pergunte pelo que procura." },
    { title: "Chame no WhatsApp", text: "Envie o que quer e seu CEP. Respondemos com disponibilidade, valor e frete." },
    { title: "Combine o pagamento", text: "[CONFIRMAR] PIX ou cartão, conforme combinado com a loja." },
    { title: "Receba em casa", text: "[CONFIRMAR] O pedido é despachado e você acompanha pelo WhatsApp." }
  ],

  faq: [
    { q: "Como faço um pedido?", a: "Chame no WhatsApp, diga os produtos que quer e seu CEP. A loja responde com valores e frete." },
    { q: "Vocês enviam para o Brasil todo?", a: "[CONFIRMAR] Consulte o frete para a sua cidade pelo WhatsApp." },
    { q: "Quais as formas de pagamento?", a: "[CONFIRMAR] Informe a forma que prefere ao fazer o pedido." },
    { q: "Os produtos têm estoque?", a: "A disponibilidade é confirmada no atendimento, antes de fechar o pedido." }
  ],

  defaultMessage: "Olá! Vi o site da {brand} e quero fazer um pedido."
};
