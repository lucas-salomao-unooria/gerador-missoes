# Plataforma Unooria — software (índice sobre as cópias sincronizadas)

> **Fonte da verdade são as cópias em `references/plataforma/`**, sincronizadas do monorepo `plataforma-unooria` por `scripts/sincronizar_plataforma.py` (commit e data em `references/plataforma/versao-lida.json`). Este arquivo é só o índice e a lista do que mais muda num PRD de missão. Quando a plataforma mudar, rode o script de novo — não edite as cópias nem reescreva resumos à mão.

## O que mais muda num PRD de missão (leia antes de escrever)

1. **Missão vive dentro da turma.** Três trancas em série: catálogo (manifesto) → disponibilidade (`admin`, ADR-87) → **liberação por turma** pela professora (ADR-69). O funil de estudante passa por `exigirMissaoLiberada` (403 `missao-nao-liberada`); sem linha em `liberacoes` a missão não abre. Sem copy de estudante no catálogo do hub ela não aparece.
2. **Manifesto tem `produto` e `unidade`.** `experiencia.json` = `id, nome, versao, produto (entre-redes | plano-de-aula | plano-de-ensino | bem-estar), series[] ([] = todas), unidade (1–4), capabilities[], viewport?, publico, permissoes[] (pointer-lock | forms | downloads), verbos`. Campo novo de manifesto tem cinco pontos de toque (Zod, coluna, `publicar-manifesto.mjs`, seed, `_template`).
3. **Seis papéis, não quatro** (ADR-80): `estudante · professor · gestor_escola · gestor_regional · gestor_contrato · admin`. `@Roles` usa os grupos de `auth/claims.ts`.
4. **Evento de telemetria é `track(verbo, objeto, «resultado, contexto»)`.** Não existe campo `dados`; chave desconhecida é descartada em silêncio. `resultado` e `contexto` são objetos JSON; identidade vem do token. Objeto na convenção `namespace:slug`. **Ninguém lê `telemetria_eventos` para relatório de missão**: toda medida que a professora vê nasce de tabela `exp_NN_*` própria, lida pela rota do módulo.
5. **Cinco caminhos de dado**: analítico (`track` → `/telemetry/batch|beacon` → Pub/Sub), operacional (rota síncrona do próprio módulo — `POST /runs/:id/eventos` é do motor da exp-01, não genérica), erros de cliente, Web Vitals (10 %), traces OTLP (allowlist no proxy; atributo fora dela some).
6. **Sala sincroniza por polling HTTP curto, nunca WebSocket** (ADR-93/94). Relógio coletivo = tabela `exp_NN_gates_turma`; não há `hub:pause` como canal de sala.
7. **Dados de missão nova** (moldes exp-04/06/07/08): uma tabela por coisa com `@@map("exp_NN_…")`, sessão com PK `[escolaId, estudanteId]`, `turma_id` denormalizado, `versao_instrumento`, `tentativa`, estado como **string com CHECK na migration** (nunca enum Prisma), texto livre de menor em tabela própria com `chars_count`, `ENABLE` + `FORCE ROW LEVEL SECURITY` + policy `app.escola_id`, exceções de RLS só justificadas. `invariantes.ts` por módulo (campos sensíveis e termos proibidos).
8. **Graus de medida** (`scored/indicative/zero/none`) não são primitiva de plataforma: existem em 2 de 11 módulos como tipo de leitura do relatório do professor. O PRD diz onde moram e quem transforma sinal em grau.
9. **Currículo existe no servidor** (`apps/api/src/curriculo/`, EF + EM + Computação extraídos do PDF homologado, ADR-73). Não marque BNCC como escopo novo.
10. **IA**: só via `apps/api/src/ai`; quota é **dado** em `ia_quotas` por perfil, editada pelo `admin` (ADR-105) — não há `AI_DAILY_TOKEN_QUOTA_*`; `generateJson` cobra por callback (ADR-74); mock falha fechado; conteúdo gerado passa por curadoria docente antes da aula (ADR-66/67).
11. **Fuso único** (ADR-98/99): `config.fuso` no handshake e `FUSO_DA_PLATAFORMA` nas três superfícies; proibido formatar data na mão.
12. **Fluxo de código** (ADR-61/71/101/103/104): frente nasce em worktree sobre `origin/dev-local` com `--fatia`; quatro ambientes `dev-local → dev → hml → main`; tag semver só em `main`. Versão em três lugares (`experiencia.json`, `package.json`, `EXP_VERSION`).
13. **`_template` de experiência traz só `App.tsx`, `main.tsx`, `index.html`, `vite.config.ts` e o manifesto** — sem DS (`@unooria/design-system@^0.2.2`, React 19), sem `@edu/ui`, sem teste. O PRD lista o que o template não dá.
14. **DoD** exige, além de typecheck/lint/test/e2e por papel e LaTeX, provar no painel `/unooria` que a experiência **desliga** (ADR-87/88).
15. **Idioma** (ADR-91): três zonas; o clone não se traduz. **Breadcrumb** é do layout (ADR-77). **Sessão** de 2 h de inatividade (ADR-95/96). A tela de recusa diz **por que** não entrou (ADR-97).

Exemplares a imitar: `apps/api/src/manifesto-ia/` + `apps/experiencias/exp-08-manifesto-ia/` (preparação docente + gate de turma), `apps/api/src/rastro-boato/` (texto livre de menor). `apps/api/src/unootube/` é de agosto e ficou para trás.

## Doutrina (cópias)

<!-- include: references/plataforma/agents-raiz.md -->

<!-- include: references/plataforma/glossario-dominio.md -->

<!-- include: references/plataforma/arquitetura.md -->

<!-- include: references/plataforma/agents-api.md -->

<!-- include: references/plataforma/agents-experiencias.md -->

<!-- include: references/plataforma/agents-hub.md -->

<!-- include: references/plataforma/agents-sdk.md -->

<!-- include: references/plataforma/agents-api-salas.md -->

<!-- include: references/plataforma/agents-api-telemetry.md -->

<!-- include: references/plataforma/agents-api-ai.md -->

<!-- include: references/plataforma/agents-api-experiencias.md -->

<!-- include: references/plataforma/agents-api-recursos.md -->

<!-- include: references/plataforma/agents-e2e.md -->

## Regras transversais (cópias de `docs/regras/`)

<!-- include: references/plataforma/regras-manifesto-de-experiencias.md -->

<!-- include: references/plataforma/regras-bridge-postmessage.md -->

<!-- include: references/plataforma/regras-convencoes-de-codigo.md -->

<!-- include: references/plataforma/regras-definition-of-done.md -->

<!-- include: references/plataforma/regras-idioma-da-interface.md -->

<!-- include: references/plataforma/regras-o-que-nao-fazer.md -->

<!-- include: references/plataforma/regras-comandos.md -->

## Contratos (código canônico, dentro de cerca)

<!-- include: references/plataforma/contrato-manifesto.md -->

<!-- include: references/plataforma/contrato-telemetria.md -->

<!-- include: references/plataforma/contrato-progresso.md -->

<!-- include: references/plataforma/guarda-liberacao.md -->

<!-- include: references/plataforma/perfis-claims.md -->

<!-- include: references/plataforma/produtos-catalogo.md -->

<!-- include: references/plataforma/series.md -->

<!-- include: references/plataforma/sdk-types.md -->

<!-- include: references/plataforma/experiencias-dev-portas.md -->

## Exemplar de missão nova (exp-08 Manifesto IA · migration da exp-04 · modelos exp-04/06/07/08)

<!-- include: references/plataforma/exemplo-manifesto-exp-08.md -->

<!-- include: references/plataforma/exemplo-contrato-rotas-exp-08.md -->

<!-- include: references/plataforma/exemplo-invariantes-exp-08.md -->

<!-- include: references/plataforma/exemplo-telemetria-exp-08.md -->

<!-- include: references/plataforma/exemplo-schema-exp.md -->

<!-- include: references/plataforma/exemplo-migration-exp-04.md -->

## Rotas existentes e decisões

<!-- include: references/plataforma/openapi-indice.md -->

<!-- include: references/plataforma/decisoes-adr.md -->
