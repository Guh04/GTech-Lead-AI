# GTech Lead AI

Painel web de gerenciamento e prospecção de leads comerciais. Hoje é a central de cadastro, qualificação e acompanhamento de leads; amanhã será o centro de controle de um agente de IA que encontra empresas sem landing page.

- **Frontend:** HTML5 + CSS3 + JavaScript puro (sem frameworks), Chart.js e Lucide (arquivos locais em `frontend/assets/vendor`).
- **Backend:** Python + FastAPI.
- **Banco e login:** Supabase (PostgreSQL + Supabase Auth), protegido por RLS.

## Estrutura

```
gtech-lead-ai/
├── frontend/
│   ├── index.html            casca da aplicação (sidebar, topbar, login)
│   ├── pages/                HTML de cada página (dashboard, leads, ...)
│   ├── js/
│   │   ├── app.js            inicialização, login, configuração
│   │   ├── router.js         navegação por hash, sem recarregar a página
│   │   ├── api.js / auth.js  cliente da API e sessão
│   │   ├── ui.js / utils.js  toasts, modais, badges, template HTML seguro
│   │   ├── charts.js         tema dos gráficos
│   │   ├── components/       formulário e ficha do lead
│   │   └── pages/            lógica de cada página
│   ├── css/                  tokens, base, layout, componentes, páginas
│   └── assets/               logo e bibliotecas (vendor/)
├── backend/
│   ├── app/
│   │   ├── main.py           cria o app, serve a API (/api) e o frontend (/)
│   │   ├── core/             config, erros, cliente Supabase, autenticação
│   │   ├── models/           enums do domínio
│   │   ├── schemas/          validação de entrada/saída (Pydantic)
│   │   ├── routes/           endpoints
│   │   └── services/         regras de negócio (leads, pontuação, analytics, prospecção)
│   ├── tests/                testes automatizados
│   ├── requirements.txt
│   └── .env.example
├── database/
│   ├── schema.sql            tabelas, índices, restrições, triggers
│   └── policies.sql          políticas RLS
└── docs/README.md
```

## Páginas

| Página | O que faz |
|---|---|
| Dashboard | 7 indicadores, leads por período, por segmento, taxa de conversão, atividades recentes e últimos leads. Tudo calculado do banco. |
| Leads | Cadastro, edição, exclusão com confirmação, busca por nome, filtros (segmento, cidade, prioridade, status, landing page), ordenação, ficha completa, histórico, anotações e exportação CSV. |
| Oportunidades | Leads ativos por prioridade (alta, média, baixa), ordenados pela pontuação. |
| Pipeline | Kanban com 7 etapas. Arraste os cartões ou use "Mover para…" (celular). |
| Prospecção | Formulário (região, segmentos, quantidade, filtros), histórico e resultados. **A busca real usa o OpenStreetMap (gratuito) ou o Google Places (ver abaixo).** |
| Relatórios | Leads por período, segmento e região, funil, taxa de conversão e de ganho, clientes fechados, histórico de prospecção. |

## Como a pontuação funciona

A pontuação (0–100) é gravada no banco e calculada por regras transparentes em `backend/app/services/scoring.py`. O foco é vender landing pages: quanto menos presença de conversão e quanto mais canais de contato, maior o potencial.

| Critério | Pontos |
|---|---|
| Sem site / site sem landing / não verificado / com landing | 45 / 30 / 15 / 0 |
| WhatsApp (ou, sem ele, telefone) | 20 (ou 10) |
| Instagram / Facebook | 10 / 5 |
| Responsável identificado | 5 |
| Marcado "Não contatar" | 0 |

Prioridade: **alta ≥ 70**, **média 40–69**, **baixa < 40**. No formulário você pode informar uma pontuação manual (ela passa a valer até você apagá-la). Futuramente, um modelo de IA pode gravar `score_source = 'ai'`.

## Executar localmente (Windows)

### 1. Pré-requisitos
- Python 3.11 ou superior (`python --version`). Baixe em python.org se necessário.
- Uma conta gratuita no [Supabase](https://supabase.com).

### 2. Banco de dados (Supabase)
1. Crie um projeto em supabase.com.
2. Abra **SQL Editor → New query**, cole o conteúdo de `database/schema.sql` e clique em **Run**.
3. Faça o mesmo com `database/policies.sql`.
4. Em **Authentication → Users → Add user**, crie o seu usuário (e-mail e senha). Marque *Auto Confirm User*.
5. Em **Authentication → Sign In / Providers**, desative **Allow new users to sign up** (o sistema não tem tela de cadastro; só quem você criar entra).
6. Em **Project Settings → API**, copie a **Project URL** e a chave **anon / public**.

### 3. Backend
No PowerShell, dentro da pasta do projeto:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
notepad .env        # preencha SUPABASE_URL e SUPABASE_ANON_KEY
uvicorn app.main:app --reload
```

Abra **http://localhost:8000** e entre com o usuário criado. A documentação interativa da API fica em **http://localhost:8000/docs**.

> Se o PowerShell bloquear a ativação do ambiente virtual, execute uma vez: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

Sem o `.env` preenchido o sistema abre normalmente e mostra uma tela explicando o que falta configurar.

### 4. Testes
```powershell
cd backend
pip install -r requirements.txt
python -m pytest
```
Os testes usam um Supabase simulado em memória (`tests/fake_supabase.py`) e não precisam de credenciais.

Teste ponta a ponta no navegador (opcional, usa o Chrome instalado):
```powershell
pip install playwright
python -m tests.e2e_server          # terminal 1
python -m tests.e2e_browser         # terminal 2
```

## API

Todas as rotas (exceto `/api/health` e `/api/auth/*`) exigem `Authorization: Bearer <token>` do Supabase Auth. Erros seguem `{"error": {"code", "message", "details"}}` com mensagens em português.

| Método e rota | Descrição |
|---|---|
| `GET /api/leads` | Lista com filtros `search, segment, city, state, priority, status, landing_status, source, active, search_id`, `sort` (`created_desc, created_asc, score_desc, score_asc, name_asc`), `page`, `page_size` (até 500) |
| `POST /api/leads` | Cadastra lead (normaliza telefone, URLs e Instagram; rejeita duplicidades com 409) |
| `GET /api/leads/{id}` | Ficha do lead |
| `PUT /api/leads/{id}` | Edita; só os campos enviados são alterados |
| `DELETE /api/leads/{id}` | Exclui (e o histórico, em cascata) |
| `PATCH /api/leads/{id}/status` | Move de etapa no pipeline |
| `GET/POST /api/leads/{id}/activities` | Histórico / nova anotação |
| `GET /api/leads/facets` | Segmentos, cidades e contadores para filtros |
| `GET /api/leads/export` | CSV (UTF-8 com BOM, separador `;`) respeitando os filtros |
| `GET /api/dashboard?days=30` | Indicadores do dashboard |
| `GET /api/reports?days=90` | Relatórios (`days=0` = todo o período) |
| `GET /api/prospecting/status` | Há provedor de busca conectado? |
| `GET /api/prospecting/history` | Histórico de pesquisas |
| `POST /api/prospecting/search` | Executa uma pesquisa (503 enquanto não houver provedor) |
| `POST /api/auth/login`, `/refresh`, `/logout`, `GET /api/me` | Sessão |

## Segurança

- **Nenhuma chave secreta no frontend.** O navegador nunca recebe chaves do Supabase, só o token do próprio usuário.
- **Sem `service_role`.** O backend usa apenas a chave pública (`anon`) junto com o token do usuário; quem protege os dados é o **RLS** do PostgreSQL (`database/policies.sql`): cada usuário só enxerga e altera os próprios registros, e visitantes anônimos não têm acesso a nada.
- Entradas validadas e normalizadas no servidor; links só aceitam `http(s)` (bloqueia `javascript:`); todo conteúdo exibido é escapado (XSS); CSV protegido contra injeção de fórmulas.
- Cabeçalhos de segurança (CSP, `X-Frame-Options`, `nosniff`). Em `APP_ENV=production` a documentação `/docs` é desativada.
- As chaves (Supabase e Google) ficam só no `.env` do servidor. Nunca versione o arquivo `.env` (já está no `.gitignore`).

## Prospecção (fase 2)

**Nada é simulado.** Sem provedor configurado, *Iniciar pesquisa* valida os dados e informa que não há busca ativa; nenhum lead falso é criado. O sistema grava o histórico, salva os leads com origem "Agente de IA" ligados à pesquisa, evita duplicidades e calcula a pontuação.

### Provedores de busca (por prioridade)

O sistema usa o primeiro que estiver configurado em `backend/.env`: **Google Places** (`GOOGLE_PLACES_API_KEY`) → **API externa** (`PROSPECTING_API_URL`) → **OpenStreetMap** (gratuito, ligado por padrão; `OSM_ENABLED=false` desliga).

### OpenStreetMap (gratuito, sem chave nem cartão)

Funciona assim que o servidor sobe. Resolve o município (informe o nome exato; com o estado, evita homônimos), busca estabelecimentos da categoria do segmento no OpenStreetMap e analisa o site de cada um (mesma análise descrita abaixo).

- **Segmentos suportados** (o OSM usa categorias fixas): odontologia, estética, salão de beleza, barbearia, advocacia, contabilidade, imobiliária, academia, restaurante, padaria, farmácia, pet shop/veterinário, oficina mecânica, arquitetura, psicologia, fisioterapia, clínica médica, escola de idiomas, autoescola, fotografia, construção e reformas. Um segmento fora da lista gera um aviso claro; nada é inventado.
- **Cobertura menor que a do Google:** só aparecem empresas cadastradas por colaboradores, e muitas não têm telefone nem site. Empresas sem site ficam como "sem landing page", o que é bom para prospecção, mas **confirme antes de abordar**: a empresa pode ter site que não está no mapa.
- **Serviço público gratuito:** o Overpass pode ficar lento ou recusar pedidos; o sistema tenta de novo e usa um servidor reserva, e avisa quando não consegue. Uso esperado: pesquisas ocasionais, acionadas por você (não automatize em lote). Só o nome do município e a categoria são enviados ao serviço. Os dados são © colaboradores do OpenStreetMap (ODbL); cada lead registra essa atribuição.

### Google Places + análise de sites (pago, maior cobertura)

Exige conta do Google Cloud com faturamento (há cota gratuita mensal; confira os preços vigentes). Ativado ao definir `GOOGLE_PLACES_API_KEY` em `backend/.env` (reinicie o servidor). Para cada segmento, o sistema:

1. Pesquisa "*segmento* em *região, UF*" na **Places API (New)** (até 60 resultados por segmento), descartando empresas fechadas e de outro estado.
2. Lê telefone, endereço, link do Google Maps e o endereço de site do perfil público.
3. Classifica o endereço do perfil: site próprio; **rede social** (vira Instagram/Facebook do lead, sem site); página de links/WhatsApp/marketplace (conta como site, mas não como landing page).
4. Abre o site próprio (somente endereços públicos; bloqueia localhost, redes privadas e redirecionamentos para elas) e **estima** a landing page pela página inicial:
   - sem resposta ou sem HTML → `unknown` (o sistema não afirma o que não observou);
   - sem formulário, WhatsApp, telefone clicável ou botão de contato, ou página genérica/em construção → `site_only`;
   - com título, conteúdo e chamada para ação → `has_landing`.
5. Aplica os filtros do formulário (com/sem site, situação da landing page) e a quantidade desejada (dividida entre os segmentos).

Limites a saber: a classificação é uma heurística sobre a página inicial (sites montados só em JavaScript podem ser lidos como `site_only`); corrija manualmente na ficha do lead quando precisar. O telefone vem do perfil do Google e **não** é marcado como WhatsApp (o Google não informa isso). A pesquisa é síncrona: com muitos segmentos e sites lentos pode levar dezenas de segundos.

**Como obter a chave:** no [Google Cloud Console](https://console.cloud.google.com/) crie um projeto, ative o faturamento, ative **Places API (New)**, crie uma chave em *APIs e serviços > Credenciais* e restrinja-a à Places API (New). A busca pede telefone e site (campos do nível "Enterprise"): confira o preço e a cota gratuita mensal vigentes antes de pesquisas grandes e defina um limite de gasto no Google Cloud. A chave fica só no `.env` do servidor; nunca no navegador.

### API externa (alternativa)

Se `GOOGLE_PLACES_API_KEY` estiver vazio e `PROSPECTING_API_URL` definido (e, opcionalmente, `PROSPECTING_API_KEY`), o backend delega a busca a um agente seu:

```
POST {PROSPECTING_API_URL}/search
Authorization: Bearer {PROSPECTING_API_KEY}
{"region": "Campinas", "state": "SP", "segments": ["Odontologia"],
 "desired_quantity": 30, "website_filter": "any|with_site|without_site",
 "landing_filter": "any|none|site_only|has_landing|unknown"}
```
Espera `200` com `{"leads": [{"company_name": "...", "segment": "...", "city": "...", "state": "SP", "phone": "...", "whatsapp": "...", "instagram": "...", "facebook": "...", "website": "...", "landing_page_status": "none", "source_url": "https://fonte-publica", "notes": "..."}]}`. Só `company_name` é obrigatório; a pontuação é sempre calculada pelo sistema.

Novos provedores em Python: implemente `backend/app/services/prospecting/base.py` e registre em `get_provider()` (`service.py`).

Próximos passos previstos: classificação por IA (`score_source = 'ai'`), abordagens personalizadas com aprovação do usuário (atividade `message_prepared`, já aceita no banco) e exportação para Google Sheets.

### LGPD
- Use apenas informações comerciais públicas e registre a fonte em cada lead (`source_url`).
- O campo **Não contatar** zera a pontuação e remove os atalhos de WhatsApp e telefone da ficha.
- O sistema **nunca envia mensagens automaticamente**: "Abrir WhatsApp" apenas abre a conversa para você decidir. Qualquer integração futura de disparo deve exigir aprovação do usuário.
- Para atender pedidos de exclusão de dados, basta excluir o lead (o histórico é removido junto).

## Publicar na internet

O FastAPI serve a API e o frontend no mesmo endereço, então basta hospedar **um** serviço Python. Qualquer plataforma que rode aplicações Python serve (Render, Railway, Fly.io, VPS...). Exemplo no **Render**:

1. Suba o projeto para um repositório no GitHub (o `.env` não é enviado).
2. No Render: **New → Web Service**, escolha o repositório.
3. Configure:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Em **Environment**, cadastre: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `APP_ENV=production`, `APP_TIMEZONE=America/Sao_Paulo`.
5. Publique e acesse a URL gerada (HTTPS).

Antes de divulgar:
- Mantenha o cadastro público do Supabase **desativado** e crie os usuários manualmente.
- Se hospedar o frontend em outro domínio, preencha `CORS_ORIGINS` com a URL dele.
- Planos gratuitos costumam "adormecer" o serviço; a primeira abertura pode demorar.

## Limitações conhecidas

- Os agregados do dashboard e dos relatórios são calculados no backend lendo os leads do usuário (até 50 mil). Para volumes muito maiores, migre para funções SQL (RPC).
- A pesquisa de prospecção é síncrona (a requisição espera o agente). Para buscas longas, evolua para execução em segundo plano.
- O backend foi testado com um Supabase simulado; a primeira execução contra o projeto real deve ser acompanhada (veja "Primeiro uso" abaixo).

## Primeiro uso (checklist)

1. Executou `schema.sql` e `policies.sql` sem erros?
2. Criou o usuário em Authentication → Users?
3. `.env` com `SUPABASE_URL` e `SUPABASE_ANON_KEY` (a chave **anon**)?
4. Entrou em http://localhost:8000, cadastrou um lead e viu o número no dashboard?

Se aparecer *"As tabelas do banco ainda não foram criadas ou estão sem permissão"*, reveja o passo 1 (principalmente o `policies.sql`).
