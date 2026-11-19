# Tendências Makeup: landing page (versão de revisão)

Página estática. Todo o conteúdo está em [`config.js`](config.js). Cliente: loja de maquiagem, cosméticos e acessórios (WhatsApp +55 15 99842-1731).

## O que falta antes de publicar
1. **Instagram da loja** (`instagram` no config.js).
2. **Produtos reais:** fotos na pasta `assets/` e listadas em `products` (nome, categoria e preço só se for o real). Sem isso a página mostra espaços marcados, nunca produtos inventados.
3. **Logo** (enviar o arquivo e preencher `logo`) e conferir as cores com o Instagram da loja.
4. **Conferir os textos marcados [CONFIRMAR]:** envio para todo o Brasil, formas de pagamento, prazo e cidade.
5. **Avaliações:** só entram depoimentos reais e autorizados (`testimonials`). Enquanto vazio, a seção fica oculta.
6. **Aprovação** da dona da loja sobre o conteúdo final.

Enquanto faltar algo, a página mostra um aviso amarelo no topo. Ele some sozinho quando tudo estiver resolvido.

## Escopo
É uma landing page: o pedido é fechado pelo WhatsApp. Carrinho, painel administrativo, estoque e pagamento online (PIX/cartão) fazem parte de uma loja virtual completa, que seria um projeto à parte.

## Publicar
Arraste **a pasta inteira** `tendencias-makeup` para o Netlify Drop (netlify.com/drop) e deixe o acesso público.

## Privacidade (LGPD)
O formulário só abre o WhatsApp do visitante com a mensagem pronta. A página não coleta dados, não usa cookies nem rastreadores.
