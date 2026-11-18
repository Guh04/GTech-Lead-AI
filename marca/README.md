# Identidade visual — GTech Digital Studio

Tudo aqui é gerado por código a partir de [`build.py`](build.py), então dá para ajustar uma cor, um texto ou um layout e refazer em segundos.

## O que tem em `export/`
| Pasta / arquivo | Conteúdo |
|---|---|
| `logos/*.svg` | Símbolo vetorial (escuro, claro, azul, mono preto, mono branco) |
| `logos/horizontal-*`, `compacto-*` | Logo horizontal e compacto, em fundo claro/escuro e com fundo transparente |
| `logos/perfil-instagram*.png` | Foto de perfil 1080×1080 |
| `logos/aplicacoes.png` | Logo em 6 fundos + cartão de visita |
| `manual-de-marca.png` | Conceito, cores, tipografia e regras de uso |
| `instagram/destaques/` | 5 capas de destaque 1080×1920 |
| `instagram/posts/` | 9 publicações 1080×1350 |
| `instagram/feed-9-publicacoes.png` | Planejamento visual do feed (publique de 9 para 1) |
| `instagram/perfil-preview.png` | Como o perfil fica (bio, destaques e grade) |
| `apresentacoes/` | 4 apresentações de projeto 1920×1080 com mockups |
| `telas/` | Capturas desktop e mobile dos 4 sites demonstrativos |

Bio, nome do perfil e legendas: [`instagram-bio.md`](instagram-bio.md).

## Projetos demonstrativos (`../site/projetos/`)
Quatro sites HTML/CSS/JS navegáveis, que também são o portfólio do site: `clinica` · `advocacia` · `estetica` · `servicos`.
São **projetos conceituais com marcas fictícias** (Clínica Lumen, Nobre & Lacerda, Atelier Seiva, Prumo). Todos trazem o aviso no rodapé e não usam depoimentos, números ou fotos de terceiros.

## Sistema de marca (resumo)
- **Símbolo:** um G em ângulos retos; o bloco azul fecha o traço superior ("a peça que completa a construção").
- **Cores:** preto `#0A0C10`, grafite `#1B1F27`, off-white `#F3F1EC`, branco, azul elétrico `#1D4DFF` (destaque, ~10%).
- **Tipografia:** Instrument Serif (títulos, itálico azul em uma palavra) e Inter (texto e rótulos).

## Como regenerar
```
python build.py            # tudo
python build.py posts      # só uma etapa: telas | logos | destaques | posts | apresentacoes | manual | feed
```
Precisa de Chrome instalado e internet (Google Fonts). Os HTML intermediários ficam em `src/`.

## Observações
- Os logos horizontais em PNG usam as fontes carregadas na renderização. Para uso em documentos, prefira os PNGs; o SVG vetorial é só o símbolo.
- No preview do perfil, `wa.me/seunumero` é um espaço reservado: troque pelo seu número.
- `python build.py telas` também atualiza as imagens WebP do site em `../site/assets/images/`.
