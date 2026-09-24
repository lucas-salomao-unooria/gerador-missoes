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
13. **`_template` de experiência traz a fiação inteira desde a ADR-106 (16/09/2026)**: manifesto completo, DS `^0.2.2` + `@edu/ui`, `bootstrap.tsx`, `lib/{tipos,api,telemetria,textos}.ts`, `versao.test.ts` e `vitest` — e **nenhum componente de interface**, de propósito. O PRD lista o que trocar primeiro (`_template/AGENTS.md`), não o que falta.
14. **DoD** exige, além de typecheck/lint/test/e2e por papel e LaTeX, provar no painel `/unooria` que a experiência **desliga** (ADR-87/88).
15. **Idioma** (ADR-91): três zonas; o clone não se traduz. **Breadcrumb** é do layout (ADR-77). **Sessão** de 2 h de inatividade (ADR-95/96). A tela de recusa diz **por que** não entrou (ADR-97).

Exemplares a imitar: `apps/api/src/manifesto-ia/` + `apps/experiencias/exp-08-manifesto-ia/` (preparação docente + gate de turma), `apps/api/src/rastro-boato/` (texto livre de menor). `apps/api/src/unootube/` é de agosto e ficou para trás.

<!-- include: references/plataforma-unooria-api.md -->

<!-- include: references/plataforma-unooria-monorepo.md -->

<!-- include: references/plataforma-unooria-contratos.md -->
