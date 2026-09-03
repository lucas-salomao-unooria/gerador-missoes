# Plataforma Unooria — Padrões arquiteturais de software

> Referência gerada a partir da leitura do monorepo `plataforma-unooria` (branch de trabalho, set/2026). Fonte de verdade em caso de divergência: `AGENTS.md` de cada pasta e `documentacao-latex/`. Reconferir a cada mudança de ADR.

Contexto de negócio: B2G para redes públicas; **1 contrato = 1 stack GCP**, isolamento lógico por `escola_id`; hub que embeda 48 experiências imersivas do 1º EF ao 3º EM; ~10k estudantes/contrato, picos de 2–4k simultâneos; produção prevista para nov/2026; uma pessoa desenvolve — *simplicidade > sofisticação*.

## 1. Stack e versões

- **Runtime/tooling**: Node `>=24`, **pnpm 9.12.0**, **Turborepo ^2.3** (`turbo.json`: `build`/`dev`/`lint`/`typecheck`/`test`; `build` e `typecheck` dependem de `^build`).
- **TypeScript ^5.7 strict** em tudo (`tsconfig.base.json`: `target ES2022`, `moduleResolution bundler`, `strict`, `noUncheckedIndexedAccess`). Proibido `any` (lint *error*).
- **Front hub**: **Next.js ^16.3 (App Router)** + **React 19.2**, `next-auth@5 beta` (Credentials), **Tailwind 3.4** com `theme.extend: {}` vazio de propósito.
- **Front experiências**: **Vite ^6.4 + React**, build 100% estático, `build.sourcemap: "hidden"`.
- **Back**: **NestJS ^10.4** (Express), `@nestjs/swagger@8`.
- **ORM/Banco**: **Prisma ^6.19** + **PostgreSQL 16**. RLS nativa do Postgres.
- **Cache/filas**: **não há Redis**. Fila = **Google Pub/Sub** só para telemetria analítica.
- **Auth**: OIDC. Hoje o **hub assina** tokens RS256 (`jose`) e publica JWKS em `/.well-known/jwks.json`; a api valida por `OIDC_ISSUER`/`OIDC_JWKS_URI`/`OIDC_AUDIENCE=plataforma-api`. **WSO2 Identity Server 7.3.0** é o IdP-alvo (`wso2/`). Senhas com `bcryptjs`.
- **IA**: Vertex AI Gemini (`apps/api/src/ai/vertex.provider.ts`), credencial **ADC** — nunca API key. Modelos por env (`VERTEX_MODEL`, `VERTEX_MODEL_LONGO`, `VERTEX_IMAGE_MODEL`), `VERTEX_LOCATION=global`.
- **i18n**: não existe. Produto monolíngue pt-BR; domínio em pt-BR, termos técnicos em inglês.
- **Validação**: **Zod ^3** em toda fronteira (body, query, `postMessage`, env, resposta) + `zod-to-json-schema` → OpenAPI.
- **Observabilidade**: OpenTelemetry (api, hub e OTel Web na SDK), `pino` + `nestjs-pino`, OTLP para `telemetry.googleapis.com`, Microsoft Clarity (ADR-60), `web-vitals`.
- **Testes**: **Jest 29 + ts-jest** na api; **Vitest ^3** no hub, SDK e experiências; **Playwright 1.62.1** (fixo) na suíte e2e caseira (`scripts/e2e/`).
- **Lint**: ESLint 9 flat config único (`eslint.config.mjs`).
- **Storage/objetos**: `@google-cloud/storage`, `sharp`, `marked` + `sanitize-html`.

## 2. Estrutura do monorepo

`pnpm-workspace.yaml`: `apps/*`, `apps/experiencias/*`, `packages/*`. Scope interno `@edu/*`.

| Workspace | Nome | Responsabilidade | Depende de |
|---|---|---|---|
| `apps/hub` | `@edu/hub` | Next.js: landing, login, áreas por papel (`/estudante`, `/professor`, `/admin`, `/analise`), embed de experiências (`/exp/[expId]`, `/dev-embed`), BFF (`/api/plataforma/[...path]`), assinatura de tokens e JWKS | `@edu/sdk`, `@edu/ui`, `@edu/conteudo-exp-01`, `@unooria/design-system` |
| `apps/api` | `@edu/api` | NestJS: tenancy/RLS, identidade e rostering, módulos por experiência, IA, telemetria, observabilidade, OpenAPI | Prisma/Postgres |
| `apps/experiencias/*` | `@edu/exp-NN-*` | bundles Vite estáticos publicados em `gs://<contrato>-exp/<expId>/<versao>/` | `@edu/sdk`, `@edu/ui`, DS |
| `packages/sdk` | `@edu/sdk` | **única porta** da experiência para fora: handshake `postMessage`, token, `api.*`, `track()`, `progresso`, `concluir()`, Clarity, OTel Web, captura de erros | zod, otel, web-vitals |
| `packages/ui` | `@edu/ui` | pontes de re-export para as seções do `@unooria/design-system` (`./ds`, `./ds-insta`, `./ds-unootube`, `./ds-chatgpt`) + `styles/plataforma.css` | `@unooria/design-system` |
| `packages/conteudo-exp-01` | `@edu/conteudo-exp-01` | copy da revelação da exp-01, lida pela experiência **e** pelo guia do professor | — |

Experiências existentes: `_template`, `exp-01-instanooria` (8º ano U1), `exp-02-unootube` (4º ano U1), `exp-03-unoogpt` (2ª EM U1), `exp-70-vila-do-lume` (transversal, jogo 3D), `exp-90-plano-de-aula` (professor), `exp-91-bem-estar` (professor).

Regra de criação de pacote: só com **dois ou mais consumidores**. `AGENTS.md` é canônico por pasta; `CLAUDE.md` é sempre `@AGENTS.md`; `README.md` é para pessoas.

## 3. Padrões de código

- **Organização**: modular por domínio na api (módulo Nest por assunto) e por rota no hub (App Router, grupo `(plataforma)`). Nas experiências: `src/app/` (telas) + `src/lib/` (regras puras, tipos, telemetria, api) + `src/bootstrap.tsx` + `src/main.tsx`.
- **Nomes**: domínio em pt-BR (`estudante`, `escola`, `turma`, `experiencia`, `missao`, `trilha`); técnico em inglês (`provider`, `guard`, `batch`). Arquivos em kebab-case pt-BR.
- **Componentes**: função + hooks; **proibido criar componente de UI local** — tudo vem do `@unooria/design-system` pela ponte certa.
- **Estado**: **nenhuma lib de estado**. `useState`/`useEffect`/`useCallback` + RSC no hub.
- **Data fetching**: hub → Server Components com `apiDoServidor()` (`apps/hub/lib/api-servidor.ts`) e BFF `/api/plataforma/[...path]`. Experiência → **só** `exp.api.get/post/put/patch/delete` da SDK, com `timeoutMs` por chamada.
- **Validação**: Zod em 100% das fronteiras; schemas em `<modulo>/contrato-de-rotas.ts`, fonte do OpenAPI. Sem `class-validator`.
- **Erros**: `FiltroDeExcecao` global na api (`ZodError` → 400 `{codigo:"corpo-invalido"}`; resto → 500 `{codigo:"erro-interno", requestId}`). **Proibido `try/catch` que engole erro**. Experiência: `exp:erro` troca a tela no hub; registro via SDK → `POST /observabilidade/erros-cliente`.
- **Logging**: pino JSON; **nada de `console.*`**; toda linha com um **`codigo` estável**; redaction por chave (`cpf`, `nome`, `email`, `token`, `texto`, `transcricao`).

## 4. Backend / API

- **Padrão de módulo de domínio** (`apps/api/AGENTS.md`): **`catalogo.ts` (dados fixos) + `regras.ts` (funções puras, sem Prisma/HTTP) + `<x>.service.ts` (sempre via `comTenancy`) + controllers separados por papel + `contrato-de-rotas.ts` (Zod) + `<x>.module.ts`**. Exemplar: `apps/api/src/unootube/`. Prefixo de rota = slug (`/unootube/*`).
- **Contrato**: REST/JSON, sem versionamento de URL. Versionamento existe no bundle (path no bucket) e no protocolo `postMessage` (`PROTOCOL_VERSION`).
- **OpenAPI derivado do Zod** (ADR-36/37): decorator `@Contrato({resumo, descricao, corpo, query, params, resposta, notas, acesso, status})`; `tests/openapi-cobertura.spec.ts` cobra `@Contrato` em **todas** as rotas. `docs/openapi.json` versionado.
- **AuthN/AuthZ**: `OidcGuard` (JWKS); claims `{ usuarioId(sub), escolaId, turmaId?, perfil }`, `aud: plataforma-api`, RS256, TTL 15 min. **RBAC**: `@Roles(...)` + `RolesGuard`, `PERFIS = ["estudante","professor","gestor","admin-contrato"]`. Acessos alternativos: `publica`, `servico`, `push` (`PubSubPushGuard`), `token-no-corpo` (beacon).
- **Multi-tenancy**: contrato = stack GCP; **escola = `escola_id` + RLS**; turma/estudante = claims. `PrismaService.comTenancy(fn, escolaId?)` abre transação e `set_config('app.escola_id', ...)`. **RLS é rede de segurança**: todo service repete `escola_id` no `where`. `users`, `turmas`, `lotacoes` estão **fora** da RLS.
- **Migrações**: Prisma Migrate em `apps/api/prisma/migrations/` com nomes descritivos; CHECKs, triggers, RLS e partições **na migration**. Renomear é `RENAME`, nunca DROP/CREATE.

## 5. Modelo de domínio

- **Plataforma (sem prefixo)**: `Escola`, `Lotacao`, `PeriodoLetivo`, `Turma`, `Matricula`, `User` (`cpf` único por contrato, `username` único por escola), `PerfilPortatil`, `Progresso`, `TelemetriaEvento`, `Experiencia` (**manifesto**), `IaUsoDiario` (quota).
- **Por experiência (prefixo `exp_NN_`)**: exp-01 `Activity`, `Post`, `Run`, `Event`, `Dossier`, `Reflexao`…; exp-02 `UnootubeSessao`; exp-03 `UnoogptSessao|Mensagem|Marco|Simulacao|RelogioTurma`; exp-70 `VilaSessao|VilaPerfil|VilaBolha`. Tabela-contrato entre duas experiências leva os dois números (`exp_01_exp_70_perfis_importados`).
- **"Missão" é modelada em três camadas, sem motor genérico**:
  1. **Catálogo estático** — `apps/hub/lib/entre-redes/catalogo.ts`: `Missao = { anoSlug, unidadeSlug, unidade, expId?, titulo, resumo, status: "disponivel"|"em-breve", ficha?: FichaDaMissao, estudante?: {titulo, chamada} }`; `FichaDaMissao = { competencia, duracao, formato, atos: AtoDaMissao[], preparo: string[] }`. Trilha = 12 anos × 4 unidades.
  2. **Manifesto de runtime** — `public/experiencia.json` / tabela `experiencias`: `{ id, nome, versao, series[], capabilities[], viewport?, publico?, permissoes[], verbos{} }`. `capabilities ∈ {telemetria, progresso, ia, avaliacao, tempo-real}`; `series: []` = todas; `publico ∈ {estudante, professor}`; `permissoes ∈ {pointer-lock, forms}`.
  3. **Estado server-side por experiência** — módulo próprio na api. **Não existe módulo genérico de avaliação** (ADR-9).
- **Máquinas de estado** como *string com CHECK na migration* (sem enum Prisma). Ex.: `Activity.etapa ∈ investigacao|conclusao|debate|explicabilidade|perdidos|reflexao|fim`; `Run.fase ∈ onboarding|feed|encerramento|conclusao|revelacao|dossie|comparacao`.
- **XP / badges / gamificação: NÃO EXISTEM.** `score` opcional no `exp:concluir` é progresso, **não nota**. Rankings usam colegas **fictícios** (LGPD).
- **Não há modelagem estruturada de BNCC no servidor** — só texto livre. Relatório por habilidade é escopo novo de plataforma.

## 6. Eventos, telemetria e analytics

- **Dois canais que não se misturam**:
  - **Operacional**: `POST /runs/:id/eventos` — síncrono, transacional, lock consultivo por run. Dwell **nunca** passa por Pub/Sub.
  - **Analítico**: `exp.track()` → batch 50 eventos / 10 s → `POST /telemetry/batch` → Pub/Sub → push `POST /telemetry/ingest` → `telemetria_eventos` (`ON CONFLICT DO NOTHING`). Beacon em `pagehide`.
- **Payload (xAPI simplificado)**: `{ eventId, ts, estudanteId, escolaId, expId, expVersion, sessaoId, verbo, objeto, resultado?, contexto? }`. **Verbos**: `attempted | interacted | completed | scored | progressed`. Nome `verbo:objeto`. Cada experiência documenta verbos/objetos no README e em `experiencia.json#verbos`.
- **Destino é Postgres** (`telemetria_eventos` particionada por mês), não BigQuery.
- **Observabilidade**: OTel; rótulos nunca com `escola_id`/`estudante_id`. Clarity via `packages/sdk/src/clarity.ts`.
- **LGPD / menores**: `estudanteId` opaco, **nada de PII** em evento; CPF numa coluna só; bem-estar é dado de saúde (art. 11) sem rota de gestor; **retenção sem prazo declarado** deliberadamente (prazo só com a rotina que o cumpre).

## 7. Design system / UI (visão do consumidor)

- **Regra de ouro**: todo elemento de interface vem de `@unooria/design-system` (última versão). Componente novo **nasce no repo `storybook-unooria`** e chega por versão publicada. Nunca componente local.
- **Seções que nunca se cruzam**: `unooria` (plataforma) e clones `instanooria`, `unitube`, `chatgpt`, `whatsappmobile`, `tiktooria`. Pontes em `packages/ui`.
- **A linha entre seções é a REVELAÇÃO**: o critério é "quem está falando?" (a ficção ou a escola) — ADR-22.
- **Aparelho**: o hub desenha a casca via `components/DispositivoFrame.tsx` a partir do `viewport` do manifesto (375×812 = celular; ausente = desktop).
- Folha de fonte é linha separada e obrigatória; ícones são fonte de ligadura (Material Symbols Rounded).

## 8. Testes

- **api**: Jest, `apps/api/tests/*.spec.ts` (~60), 9 de 23 suítes de integração com Postgres real.
- **hub/sdk/experiências**: Vitest, teste ao lado do arquivo.
- **Sem limiar numérico de cobertura**; o mínimo doutrinário são os **contratos**: bridge, telemetria, guards de tenancy, schema de resposta, cobertura de `@Contrato`.
- **E2E**: suíte caseira `node scripts/e2e/rodar.mjs [papel|papel/suíte]`, **por papel** (`publico → estudante → professor → gestor → admin-contrato`), evidências em `testes/<papel>/<suíte>/`. Esperas correm **contra o erro** (`esperarOuFalharCedo`).

## 9. Qualidade, CI e Definition of Done

- Conventional Commits (`feat|fix|chore|docs|ci|refactor|test|perf|build|style|revert`, escopo = slug). Hooks em `.githooks/`.
- Fluxo: trabalho → PR `dev` → `dev→hml` → `hml→main`; merge dispara deploy; sem rebase.
- CI: Postgres 16, `pnpm install --frozen-lockfile`, `migrate:deploy`, `pnpm turbo typecheck lint test build`.
- **DoD**: typecheck+lint+test; e2e do papel afetado se mexeu em tela; input externo com Zod; queries escopadas por tenancy; sem segredo no client; docs de contrato; `AGENTS.md` da pasta no mesmo commit; `documentacao-latex/` atualizada e `main.pdf` regerado, com ADR nova se houve alternativa descartada.

## 10. Documentação LaTeX

`PU-DOC-001` (~332 págs.), seções `00-siglas` … `20-conclusao`, com `03-requisitos` (RF/RNF rastreáveis), `05-arquitetura-software` (C4), `07-tenancy-seguranca` (matriz papel × rota × tela), `08-modelo-de-dados`, `10-telemetria`, `12-experiencias` (catálogo), `13-api`, `14-design-system`, `18-adr` (**64 ADRs**). Apêndices: `c-endpoints` gerado de `docs/openapi.json`, `e-dicionario-de-dados`.

ADRs mais citadas: 9 (gabarito server-side por experiência), 22 (linha da revelação), 36/37 (OpenAPI do Zod), 46 (`hubOrigin`), 48 (teto de 30MB), 49 (vazamento de tenancy), 57/58 (OTel), 60 (Clarity), 61 (worktree), 64 (relógio do marco).

## 11. Como criar uma nova missão (passo a passo canônico)

1. `git switch -c exp-NN-slug` a partir de `origin/dev`. `pnpm new:exp exp-NN-slug` → copia `apps/experiencias/_template`.
2. Front: `apps/experiencias/exp-NN-slug/src/` — `main.tsx`/`bootstrap.tsx` (handshake), `app/<slug>-app.tsx` + `app/componentes/*`, `lib/` (`tipos.ts` com `EXP_ID`/`EXP_VERSION`, `api.ts`, `telemetria.ts`, regras puras + `.test.ts`), `estilos/globals.css`, `vite.config.ts` (porta fixa `strictPort`, `base: "./"`, `sourcemap: "hidden"`, `allowedHosts: ["host.docker.internal"]`).
3. `public/experiencia.json`: `{ id, nome, versao, series[], capabilities[], viewport?, publico?, permissoes[], verbos{} }`. `permissoes: ["forms"]` obrigatório se houver `<form>`.
4. Backend (se houver gabarito/estado/visão do professor): módulo `apps/api/src/<slug>/` com `catalogo.ts`, `regras.ts`, `<slug>.service.ts`, `<slug>.controller.ts` (estudante) + `<slug>-turmas.controller.ts` (professor), `contrato-de-rotas.ts`, `<slug>.module.ts` — registrado em `app.module.ts`.
5. Persistência: migration Prisma nova + modelos `@@map("exp_NN_...")`, `escola_id NOT NULL`, RLS, CHECKs e índices na migration.
6. Catálogo: entrada `Missao` em `apps/hub/lib/entre-redes/catalogo.ts` com `ficha` completa e **`estudante: {titulo, chamada}`** (sem isso não aparece em `/estudante`). Porta de dev em `apps/hub/lib/experiencias-dev.ts`.
7. E2E: `scripts/e2e/estudante/NN-slug.mjs` (ou `professor/`), com `registrar({titulo, mostra, prova})`.
8. Docs: `AGENTS.md` + `CLAUDE.md` + `README.md` da experiência; LaTeX (`12-experiencias.tex`, `13-api.tex` + `c-endpoints.tex`, `08-modelo-de-dados.tex` + `e-dicionario-de-dados.tex`, ADR em `18-adr.tex`); regerar `main.pdf`.

**Contratos a seguir**
- Handshake `postMessage` v2 (`packages/sdk/src/bridge.ts`): `exp:ready` → `hub:init {token, estudante{id,nome,serie,turmaId,escolaId}, config{clarityProjectId, expId, obs<traceRatio>}, apiUrl}` → `exp:concluir {score?, dados?}`; `exp:token-expirando`/`hub:token`; `exp:estado`; `exp:erro {mensagem≤256, hash≤16}`; `hub:pause|hub:resume`. `targetOrigin` explícito; token só em memória.
- Toda rota nova: `@UseGuards(OidcGuard, RolesGuard)` + `@Roles(...)` + `@Contrato({...})` com schema Zod de **resposta** + `comTenancy` + `escola_id` no `where`.
- **Regra 3**: gabarito, correção e pontuação são **server-side**; tipo público `Omit<X, "gabarito">` (padrão `semGabarito()`).
- Identidade sempre do token; turma conferida contra a **matrícula**.
- IA: só via `apps/api/src/ai` (`AiProvider.generate`), `QuotaService.temSaldo` antes e `consumir` depois (no `finally`); missão abre com `AI_PROVIDER=mock`; nenhum número sai da LLM.

**Eventos a emitir**
- `exp.track(verbo, objeto, {resultado, contexto})` com verbos do vocabulário, objetos estáveis, **sem PII**. `exp.concluir(<score>)` ao final.
- Trilha pedagógica (o que o professor lê) gravada pela **api** em tabela própria (padrão `exp_03_marcos`), nunca pelo canal analítico.

**Componentes a usar**
- `@edu/ui/ds` quando **a escola** fala; `@edu/ui/ds-<clone>` quando **a ficção** fala. Folha da seção + folha de fonte. Handlers de `Modal` com `useCallback`.
- No hub: `montarEmbed()` → `ExpHost`/`ExpFrame`/`DispositivoFrame`; header `components/header-plataforma.tsx`.

**Ao publicar**: subir `versao` do manifesto **e** `version` do `package.json` juntos. Mexeu em `packages/sdk`? Sobe a versão de todas as experiências.
