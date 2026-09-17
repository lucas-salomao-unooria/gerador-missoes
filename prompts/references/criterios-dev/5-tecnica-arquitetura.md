# Dimensão E — Técnica & Arquitetura

Referências do gabarito: `AGENTS.md` raiz, `apps/experiencias/AGENTS.md`,
`apps/api/AGENTS.md`, `apps/experiencias/_template/`,
`apps/api/src/manifesto-ia/` e `apps/api/src/rastro-boato/` (exemplares
atuais do padrão de módulo; `unootube` é de agosto e ficou para trás),
`apps/api/src/ai/` (provider + quota). O avaliador confere no repositório o
que a spec pressupõe existir.

## TEC-01 [BLOQUEANTE] — Manifesto derivável da spec
Com o insumo em mãos dá para preencher o `public/experiencia.json` inteiro:
`id`, `nome`, `versao` inicial, **`produto`** (ADR-87 — o CI recusa manifesto
sem ele), `series` (`[]` = transversal), **`unidade`** (1–4, ordena a grade da
sala, ADR-69), `publico`, `capabilities` (`telemetria`, `progresso`, `ia`,
`avaliacao`, `tempo-real`), `viewport` (só se casca de aparelho), `permissoes`
(`pointer-lock`, `forms`, `downloads` — só o que o iframe precisa) e `verbos`.
Campo indecidível pela spec = lacuna dela. **Permissão que a plataforma ainda
não concede não é erro da spec**: é pré-requisito de plataforma (a tabela está
em `references/capacidades-plataforma.md`), avaliado como ⚠️ com o caminho de
implementação, nunca ❌.

## TEC-02 [BLOQUEANTE] — Módulo da api desenhado
Se há gabarito, estado de missão ou visão de professor (quase sempre há):
módulo próprio `apps/api/src/<slug-curto>/` com `catalogo.ts` (dados),
`regras.ts` (funções PURAS, sem Prisma/HTTP — testáveis), service com
`comTenancy`, e controllers SEPARADOS por papel (nunca `@Roles` misto com
exceção por método; seis papéis via grupos de `auth/claims.ts`), com
`exigirMissaoLiberada` no funil de estudante (ADR-69) e relógio coletivo por
polling em `exp_NN_gates_turma` (ADR-93/94), nunca WebSocket. A spec permite
escrever o esqueleto: entidades do catálogo, regras principais, rotas por papel.

## TEC-03 — Rotas e erros de domínio enumerados
Lista de rotas por papel com códigos de erro de domínio nomeados (409
`LIMITE_SALVOS`/`RANKING_BLOQUEADO`, `relogio-nao-comecou`) — o cliente traduz
código em copy da ficção, então os códigos são contrato de produto, não
detalhe de implementação.

## TEC-04 — IA dentro das cinco camadas
Se a missão usa IA: (a) toda chamada via provider de `apps/api/src/ai` — nunca
do bundle; (b) `QuotaService.temSaldo` ANTES, `consumir` DEPOIS e no `finally`
(quota que não conta a falha não protege nada); (c) teto por sessão se for
conversacional (`TETO_CHAMADAS_SESSAO`/`TETO_TOKENS_SESSAO` — a quota diária
não sabe que uma partida custa duas ordens de grandeza mais que um turno de
tutor); (d) a missão ABRE e funciona com `AI_PROVIDER=mock`; (e) falha de
IA/quota nunca quebra a missão (fallback dentro da ficção, sem debitar);
(f) se há números em jogo, NENHUM número sai da LLM — motor determinístico +
function-calling, o modelo só narra.

## TEC-05 — Contas antecipatórias sobem para a api
Qualquer cálculo cujo resultado permitiria ao estudante antecipar o desfecho
(ou ler a calibragem) roda no servidor e chega pronto ao cliente (as três
contas da exp-03: minuto da cidade, projeção de rotas, alcance por bairro).
A spec identifica essas contas.

## TEC-06 — Relógio coletivo bem definido
Se há aula síncrona: relógio por turma no servidor (tabela própria, como
`exp_03_relogio_turma`), largada IDEMPOTENTE (dois cliques não rebobinam),
"+tempo" com pivô (não recalcula o passado), estudante descobre por polling.
Ações do professor: largada, +tempo, encerrar, modo livre, redefinir.

## TEC-07 — Contrato de bundle estático
Vite + React + `@edu/sdk`, `dist/` 100% estático no bucket — a missão NUNCA
vira serviço no Cloud Run. Porta de dev nova registrada em
`apps/hub/lib/experiencias-dev.ts`, `strictPort: true`, `base: "./"`,
`allowedHosts` com `host.docker.internal`. Nada aqui exige serviço novo,
WebSocket próprio ou estado no cliente entre sessões — se a spec exige,
levantar como decisão de arquitetura (ADR) antes de codar.

## TEC-08 — Versão única em três lugares
`versao` do manifesto = `version` do `package.json` = constante de versão do
bundle (`EXP_VERSION`) — o CI lê do manifesto e a divergência já causou bug;
o skew da constante do bundle torna a análise de telemetria cega à versão
real (defeito presente hoje nas quatro missões). A spec só precisa declarar a
versão inicial; o critério existe para o plano de implementação incluir a
fonte única.

## TEC-09 — Smoke walkthrough desenhado com asserções honestas
O insumo permite roteirizar o walkthrough: quais passos, e asserções que
FALHAM quando a funcionalidade quebra — sobreviver a F5 (o dado veio do
banco), DOIS contextos de navegador se professor e estudante interagem (um só
passaria com o relógio quebrado), espera que corre contra o erro
(`esperarOuFalharCedo`), zerar a turma no começo (estado server-side sobrevive
ao teste anterior). Asserção que passa com a feature quebrada é pior que
nenhuma.

## TEC-10 — Testes de contrato mínimos
Regras puras testadas; guard de tenancy; sanitizador com teste de `grep` dos
campos sensíveis no `dist/`; invariantes de produto em LISTA ÚNICA importada
por código, sanitizador, prompt e teste (padrão `unoogpt/invariantes.ts`).
A spec fornece os invariantes (termos proibidos na tela, campos sensíveis).

## TEC-11 — Dependências de DS resolvidas antes
Componentes novos no `storybook-unooria` publicados e a versão do
`@unooria/design-system` atualizada (`pnpm up -r --latest` deliberado — caret
`^0.1.x` não sobe minor) ANTES da codificação da missão. A spec lista essas
dependências com status.

## TEC-12 — Esforço e risco dimensionados
O que é padrão já pavimentado (módulo api, bridge, manifesto, walkthrough) vs
o que é NOVO de plataforma (ex.: modelagem BNCC no servidor, seção de DS nova,
mecânica 3D). Cada item novo de plataforma tem decisão/ADR prevista. Uma
pessoa desenvolve; simplicidade > sofisticação; prazo de produção: 2026-11.

## TEC-13 — Documentação alcançável
A spec contém o suficiente para escrever, no mesmo PR: a ficha do catálogo
(`secoes/12-experiencias.tex`), o modelo de dados
(`secoes/08-modelo-de-dados.tex` + dicionário), as rotas (`secoes/13-api.tex`)
e ADRs para toda decisão com alternativa descartada. Se não dá para escrever a
ficha a partir do insumo, o insumo está incompleto.
