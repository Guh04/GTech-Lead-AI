# Site da GTech Digital Studio

Site institucional em **HTML, CSS e JavaScript puros** (sem frameworks, sem build, sem cookies nem rastreadores).

```
site/
  index.html              página principal
  css/style.css           estilos do site     css/fonts.css  fontes locais
  js/main.js              animações, menu e rolagem
  js/config.js            ← telefone, e-mail, Instagram, CNPJ e mensagens do WhatsApp
  assets/images/          telas dos projetos (WebP)     assets/fonts/  Instrument Serif e Inter
  favicon.svg
  projetos/
    clinica/  advocacia/  estetica/  servicos/    4 demonstrações navegáveis (index.html cada)
    demo.css  demo.js                              partes comuns das demonstrações
```

## Ver no computador
Na pasta `site`: `python -m http.server 5500` e abra http://localhost:5500
(ou abra o `index.html` com duplo clique).

## Trocar contato e mensagens
Edite só [`js/config.js`](js/config.js). Cada botão de WhatsApp abre uma mensagem diferente
(orçamento, cada serviço, portfólio, contato).

## Projetos demonstrativos
São **conceituais, com marcas e dados fictícios**, e dizem isso na página. Não os apresente como trabalhos de clientes.
Os formulários deles não enviam nada; só mostram uma resposta de exemplo.

## Imagens do portfólio
As imagens em `assets/images/` são capturas das demonstrações. Para refazê-las depois de mudar uma demo:
`cd ../marca && python build.py telas` (precisa de Chrome e do Pillow: `pip install pillow`).

## Acessibilidade e desempenho
Respeita `prefers-reduced-motion`, tem foco visível, menu acessível por teclado (Esc fecha), textos alternativos nas imagens,
fontes hospedadas no próprio site e imagens em WebP com `width`/`height` definidos.

## Publicar de graça
Arraste a pasta `site/` em **netlify.com/drop** (ou Cloudflare Pages / Vercel, sem build). Depois aponte o seu domínio.

## Privacidade (LGPD)
O site não coleta nem envia dados e não usa cookies. Os botões só abrem o WhatsApp, o e-mail ou o Instagram do visitante.
Se você adicionar Google Analytics, pixel ou outro rastreador, será preciso aviso de cookies e política de privacidade.
