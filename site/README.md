# Site / landing page da GTech

Página estática (HTML, CSS e JS puros). Não tem servidor nem banco de dados.

## Como personalizar
Edite **só** o arquivo [`config.js`](config.js): marca, WhatsApp, e-mail, Instagram, seu nome ou razão social, CNPJ, cidade, prazo e preços.
Enquanto faltar algo obrigatório, a página mostra um aviso amarelo no topo e destaca os campos pendentes em amarelo.
Preço vazio aparece como "Sob orçamento".

Os textos (títulos, perguntas, planos) estão em [`index.html`](index.html); troque pelo que for verdade para o seu serviço.

## Antes de publicar, confira
- O prazo e os preços são os que você realmente cumpre.
- Não existem depoimentos, números ou clientes inventados. Os modelos da seção "Modelos" estão marcados como demonstração. Quando tiver trabalhos reais (com autorização do cliente), troque os modelos por eles.
- O WhatsApp abre com o número correto (teste no celular).

## Testar localmente
Abra `index.html` no navegador, ou na pasta `site`: `python -m http.server 5500` e acesse http://localhost:5500.

## Publicar de graça
Netlify, Cloudflare Pages ou Vercel: envie a pasta `site/` (sem build). Depois aponte o seu domínio próprio.

## Privacidade (LGPD)
O formulário só monta a mensagem e abre o WhatsApp do visitante. O site não coleta, guarda nem envia dados, e não usa cookies nem rastreadores. Se você adicionar Google Analytics, pixel ou outro rastreador, será preciso aviso de cookies e política de privacidade.
