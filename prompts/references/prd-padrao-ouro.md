# PRD Padrão Ouro — princípios e gabarito (consumo por agente de codificação)

> Consolidação de Cagan (SVPG), Google Design Docs, Atlassian, Pragmatic Engineer (RFCs), GitHub Spec Kit, AWS Kiro (EARS), Cucumber (Gherkin), ADR/MADR, C4, INVEST, Scrum Guide (DoD), Katalon (RTM), Fora Soft (NFR), Anthropic (context engineering / Claude Code) e AGENTS.md. Fontes listadas ao final.

## A. Princípios que o documento obedece

1. **O quê e por quê, separados do como.** Requisitos declaram necessidade, não mecanismo (Cagan, Spec Kit). O "como" vive na seção de plano técnico, explicitamente marcada — e nunca contamina os requisitos funcionais.
2. **Três camadas de contexto para o agente**: (a) regras duráveis do repositório (`AGENTS.md`/`CLAUDE.md` do monorepo — referenciadas, não copiadas); (b) o quê/por quê (este PRD); (c) o como (plano técnico e tarefas, seções 16–21 deste gabarito).
3. **Ambiguidade zero — ou declarada.** Toda lacuna vira `[NEEDS CLARIFICATION: pergunta]` (Spec Kit). O PRD só recebe status `aprovado` com zero marcadores abertos.
4. **Critérios verificáveis por máquina.** Cada requisito funcional tem critérios de aceite em **EARS** (`QUANDO <gatilho>, O SISTEMA DEVE <resposta>` · `SE <condição indesejada>, ENTÃO…` · `ENQUANTO <estado>…` · `ONDE <feature opcional>…`) e/ou **Gherkin** (`Dado / Quando / Então`, 3–5 passos). Cada NFR tem número, unidade e método de medição.
5. **IDs estáveis e rastreabilidade.** `RF-001`, `RNF-SEC-002`, `EVT-010`, `ENT-003`, `API-004`, `T-014`, `RISCO-002`, `ADR-001`. A matriz de rastreabilidade liga objetivo → RF → critério → tarefa → teste.
6. **Não-objetivos explícitos e "o que NÃO fazer" técnico.** É a defesa contra scope creep do agente (Google, Augment Code).
7. **Priorização com barra alta.** P0 = sem isso a missão não lança (e reprova na rubrica); P1 = necessário para o release; P2 = desejável. Rank-order dentro de cada classe.
8. **Contratos antes de código.** Rotas (OpenAPI/Zod), eventos, entidades e enums de estado definidos no PRD; o agente implementa contra eles.
9. **Tarefas atômicas, ordenadas, com verificação.** Cada tarefa cita os RFs que cobre, os arquivos que toca e o comando que prova que ficou pronta. Tarefa que cobre o intervalo inteiro de requisitos (`RF-001..RF-014`) não é tarefa: é a lista de tarefas que ainda não foi escrita, e nenhum comando prova que ela ficou pronta. `[P]` marca o que pode rodar em paralelo. Ordem: contratos → testes → implementação.
10. **Documento vivo e versionado** com frontmatter, changelog e status; dono humano nomeado.
11. **Economia de contexto.** Resumo executivo de uma página no topo; detalhe em seções hierárquicas; referências por caminho de arquivo, não por cópia.
12. **Evidência de conclusão, não afirmação.** A Definition of Done exige saída de testes, comandos rodados e evidências e2e.

## B. Gabarito — estrutura obrigatória do PRD de missão Unooria

```markdown
---
prd_id: PRD-<slug>
titulo: <nome da missão>
versao: 0.1.0
status: draft | em-revisao | aprovado-com-pendencias-de-plataforma | aprovado | em-implementacao | lancado
slug_experiencia: expNNefNb
produto: entre-redes | plano-de-aula | plano-de-ensino | bem-estar
serie: ["4EF"]            # formato da plataforma; [] = transversal
unidade: 1 | 2 | 3 | 4 | nenhuma
ambiente_simulado: <o ambiente da spec (bloco 14): clone da lista fechada, ambiente novo ou mini-jogo>
secao_ds: <instanooria|unitube|chatgpt|tiktooria|whatsappmobile|nova:<nome>|minijogo:<nome>>
links: {stitch: <url do projeto>, miro: <url do board — omita se indisponível>, prototipo: design/08-prototipo.html, diagramas: design/09-diagramas.html, spec: spec/<slug>-spec.md, one_pager: ...}
data: AAAA-MM-DD
---

# 0. Resumo executivo (1 página)
Problema · para quem · descoberta central em uma frase · solução em uma linha · métrica-alvo · prazo · status dos gates. Mini press release opcional (Amazon PR/FAQ).

# 1. Contexto e problema
Trilha/ano/unidade · problema de aprendizagem · evidências · alinhamento com a plataforma (Entre Redes) · o que já existe no catálogo e como esta missão se diferencia (critério 2.5).

# 2. Objetivos e métricas
North star pedagógica · **tabela de KPIs no formato abaixo, lida por gate determinístico** ·
guardrail metrics (o que não pode piorar) · hipóteses de validação.

```
| KPI | PQ | Pergunta | Decisão | Corte | Tela | Evento(s) | Como calcula | Baseline | Alvo | Prazo |
|---|---|---|---|---|---|---|---|---|---|---|
| KPI-01 | T7 | De cada X turmas liberadas, quantas chegam ao fim da missão? | Menos da metade → encurtar ou dividir | missao · serie | — | `EVT-U01`, `EVT-U03` | turmas com `EVT-U03` / turmas com `EVT-U01` | sem baseline — primeira medição | ≥ 70% | 2 meses |
| KPI-02 | PQ-01 | ... | ... | turma | `E3-ALU-02` | `EVT-005` | count(`EVT-005` com `contexto.tempo_ms` ≥ 120000) | 45% (playtest 12/08, n=23) | ≥ 80% | piloto |
```

**Cada coluna existe por um motivo, e um gate confere:** sem `Pergunta` e `Decisão` o número é
métrica de vaidade (34 dos 49 KPIs das primeiras execuções não tinham nenhuma das duas);
`Tela` é o que permite conferir que o evento dispara onde o KPI diz — havia KPI de uma tela
alimentado por evento de outra, e o número saía parecendo certo; `Baseline` traz o número com a
**origem entre parênteses** ou o literal `sem baseline — primeira medição`, porque `0%` não é
medida (20 dos 49 tinham `0%`); `Como calcula` cita os campos de `resultado`/`contexto` que o
evento de fato carrega.

KPI transversal (herdado de uma `T` de dono `missao` do catálogo de `perguntas-de-produto.md`)
usa `Tela: —`, **a pergunta da transversal com as palavras dela**, e **só os sinais que o catálogo
lista para ela** — nunca um evento próprio da mecânica, mesmo que pareça próximo. As de dono
`plataforma` (T1–T6, T13, T18) não viram KPI da missão: a missão não tem o dado. As
transversais não precisam de KPI próprio; o que a missão deve a elas é que a seção 13 traga
**todos os sinais universais** com o id e o objeto do catálogo: os `EVT-U*` na **tabela de eventos**
(com o verbo), e os `EVT-P*` — que são colunas do módulo, não telemetria — numa tabela própria
**«Sinais do professor»**, no formato do catálogo: `| Sinal | Objeto | Quando grava | Onde fica | Responde |`. Os ids `EVT-U*`/`EVT-P*` são reservados: evento da mecânica é `EVT-001`, `EVT-002`…


# 3. Não-objetivos e fora de escopo
Lista explícita com motivo. Inclui V2 (o que fica para depois) e o que a rubrica proíbe (ranking de crianças, nota formal, IA sem curadoria…).

# 4. Personas e jobs-to-be-done
Estudante (ano, faixa etária, perfil cognitivo — caps de decisão e leitura), Professor (preparo, condução, leitura), Gestor (só agregado). Cenários de dispositivo (1:1, 2–4 por aparelho, projeção única).

# 5. Experiência — narrativa e mecânica (as 6 etapas)
Desafiar → Navegar → Decidir → Resultado/Aha → Explicar → Refletir. Por etapa: o que o sistema apresenta, ordena, bloqueia e garante; verbo nativo; ator. Descoberta central e o beat exato. Checkpoints modulares entre etapas com persistência de estado, tempos sugeridos de execução, controle docente de ritmo, podcast de recapitulação e flexibilidade para formatos de aula (50 min, 2 aulas ou sessões fracionadas). Ausências declaradas do ambiente. Briefing de ofício (aposta, pico, beat memorável, não-negociáveis).

# 6. Fluxo e máquina de estados
Estados com nome próprio (viram enum), tabela de transições (estado inicial · gatilho · regra · estado seguinte · responsável · reversível?), caminhos degenerados com rota, gates de professora, estados de falha na voz da ficção, reentrada (F5, outro dia), latch, conclusão, segunda aplicação. Diagrama Mermaid `stateDiagram-v2` (o mesmo que o D3 emitiu).

# 7. User stories (INVEST)
Uma por tela do inventário: Como/Quero/Para · especificação da tela (D5) · chaves de string · etapa · critérios sustentados · estados · dependências. Itens 🔒 = requisito de conformidade (rubrica/BNCC/acessibilidade), não negociável.

# 8. Requisitos funcionais
Tabela `RF-xxx` · título · descrição (necessidade, não mecanismo) · prioridade P0/P1/P2 · rastreio (objetivo, story, critério da rubrica) · **critérios de aceite EARS/Gherkin** · casos de borda. Mínimo obrigatório: estudante, professor (tela de preparação docente `E0-PROF-01` com parametrização de tema/palavras-chave, geração de conteúdo via IA com curadoria e aprovação humana, ativação do banco curado padrão `banco_default`, dashboard, gatilhos, roteiro), plataforma (persistência de conteúdo por turma, reentrada, falhas).

# 9. Requisitos não funcionais
Checklist com meta numérica e método de medição por categoria: performance (p95, peso do bundle, mídia >2MB em bucket) · disponibilidade/recuperabilidade (F5, sessão expirada, offline) · segurança (gabarito server-side, nada no bundle, identidade do token) · **privacidade e LGPD para menores** (art. 14; `estudante_id` opaco; PII zero; texto livre em tabela própria; graus de medida scored/indicative/zero/none; retenção declarada ou lacuna assumida) · acessibilidade (WCAG 2.2 AA; áudio + pictograma em anos iniciais; contraste; teclado; `prefers-reduced-motion`) · usabilidade por faixa (tetos de palavras, decisões, duração de ato) · observabilidade (eventos, logs com `codigo`, OTel) · compatibilidade (Chromebook/desktop; viewport) · i18n (pt-BR único) · custo (IA: teto de tokens por turma/preparação; Cloud Run).

# 10. UX, telas e design
Inventário de telas (ID `E<etapa>-<ator>-<n>`, peso, elementos, estados) · direção por tela (pico/alta) · **link do projeto no Stitch e a tabela de telas**, mais o protótipo navegável (`design/08-prototipo.html`) e a folha de diagramas (`design/09-diagramas.html`) · **como a experiência é embedada** (casca de aparelho pelo `viewport` do manifesto, ou janela do hub) · sheet de strings (chave `eN.tipo.nome`, seção `clone|unooria`, redundância) · mapa "quem está falando" tela a tela · viewport · permissões de iframe · assets com peso · interações instrumentadas.

# 11. Modelo de dados
Entidades `expNNefNb_*` com campos, tipos, PK (sessão: `[escolaId, estudanteId]`), `turma_id` denormalizado, `versao_instrumento`, `tentativa`, sensibilidade (PII de menor?), retenção (ou lacuna assumida por escrito), `escola_id NOT NULL` + RLS (`ENABLE` + `FORCE`, policy `app.escola_id`) e exceções justificadas. Estado = **string com CHECK na migration**, nunca enum Prisma. `expNNefNb_conteudo_turma` quando há preparação docente (molde `exp08ef1b_conteudo_turma`: pacote `Json`, `aprovado_por_professor`, `usou_banco_default`). `expNNefNb_gates_turma` quando há relógio coletivo (ADR-93/94). Texto livre de menor em tabela própria com `chars_count`, fora de log e telemetria. Tabelas-contrato entre experiências. O que **nunca** vai ao bundle. Diagrama Mermaid `erDiagram`. Moldes: `references/plataforma/exemplo-schema-exp.md` e `exemplo-migration-exp-04.md`.

# 12. Contratos de API
Rotas por papel na forma consagrada pelas missões recentes (exp-06/07/08): `GET /<slug>/sessao`, ações do estudante, `GET /<slug>/gate`, `GET /<slug>/turmas`, `GET /<slug>/turmas/:turmaId/painel`, `POST /<slug>/turmas/:turmaId/gate`, `POST /<slug>/turmas/:turmaId/gerar-conteudo`, `POST /<slug>/turmas/:turmaId/homologar` (ou `/aprovar-pacote`), `DELETE /<slug>/turmas/:turmaId` (zerar). Para cada rota: método, `@UseGuards(OidcGuard, RolesGuard)`, `@Roles` com os grupos de `auth/claims.ts` (seis papéis: `estudante · professor · gestor_escola · gestor_regional · gestor_contrato · admin`), `@Contrato` com Zod de entrada e **de resposta**, `exigirMissaoLiberada` no funil de estudante (403 `missao-nao-liberada`, ADR-69), códigos de erro de domínio nomeados, idempotência e locks (largada, cliques duplos). Rotas de plataforma consumidas sem criar (`/progresso/:expId`, `/telemetry/batch`, `/ai/gerar`, `/salas/minhas`). Formato OpenAPI resumido; índice real em `references/plataforma/openapi-indice.md`.

# 13. Eventos, telemetria e analytics
Tabela `EVT-xxx` · `verbo` (sugerido `attempted|interacted|progressed|completed|scored`; não imposto pela api) · `objeto` (`namespace:slug`, estável) · quando dispara · `resultado` · `contexto` (objetos JSON; só número, booleano ou vocabulário fechado; nunca texto de menor, nome, e-mail) · caminho (analítico `track` · operacional rota do módulo · erro · vital · trace) · **onde é lido** (o que a professora vê: tabela `expNNefNb_*` + rota/tela do professor; o que só alimenta KPI de produto: `painel de produto (PostHog)`. Pub/Sub, `/telemetry/batch` e `telemetria_eventos` são transporte, nunca leitor; "aparece no dashboard" sem tabela nem painel nomeados é fantasia) · retenção · KPI que alimenta. **Não existe campo `dados`.** Volume por sessão (cabe em 50 eventos/10 s?) e o que é agregado no cliente. `experiencia.json#verbos` com o significado nesta missão + lista de objetos. Métricas proibidas (dwell no analítico, ranking). Versão do instrumento. Clarity recebe só `verbo:objeto`. Molde: `references/plataforma/exemplo-telemetria-exp-08.md`.

# 14. Pedagogia e conformidade
Matriz habilidade BNCC (código, confirmado ou 🔵 a validar) → evidência observável → interação → dado gravado. Competência socioemocional nomeada. Rastreabilidade curricular. Gabarito (só no servidor). Graus de medida. Guardrails de IA (8.1/8.2: geração restrita à preparação docente com curadoria humana obrigatória antes do consumo pelo estudante; IA nunca avalia formalmente o estudante; fallback para banco curado padrão) e éticos (8.3–8.6). Papel do erro. O que cada adulto vê.

# 15. Dependências, integrações e **pré-requisitos de plataforma**
**Pré-requisitos de plataforma** — tabela própria e obrigatória quando a missão pede capacidade que a plataforma ainda não tem: capacidade · por que a mecânica precisa dela · arquivos a tocar (contrato da api, migration do CHECK, `ExpFrame`, teste, repasse nas rotas do hub) · componente de design system a criar · ADR necessária · o que acontece sem ela (degradação). Cada linha vira também item da seção 19, e o frontmatter sai `aprovado-com-pendencias-de-plataforma`. A tabela das capacidades, com o caminho de cada uma, está em `references/capacidades-plataforma.md`. Depois disso: seção do DS e componentes faltantes (com responsável e prazo) · versão do `@unooria/design-system` · SDK · módulos da api reutilizados · IA (Vertex AI Gemini no backend NestJS via `apps/api/src/ai`, quota, banco default curado para contingência) · outras missões (contrato e fallback) · conteúdo autoral (inventário, quem produz).

# 16. Arquitetura da solução (plano técnico)
Contexto da plataforma resumido (monorepo, hub + api + experiência estática, SDK/postMessage `PROTOCOL_VERSION`, tenancy com seis papéis, três trancas catálogo → disponibilidade → liberação por turma, cinco caminhos de dado, sala por polling curto ADR-93/94, fuso único ADR-98/99). Diagrama C4 nível 1–2 (Mermaid). Alternativas consideradas e trade-offs. Decisões que exigem ADR nova.

# 17. Plano de implementação — arquivos e convenções
Lista de **arquivos a criar/alterar com caminho completo**; módulo a imitar (`apps/api/src/manifesto-ia/` + `apps/experiencias/exp-08-manifesto-ia/`; `apps/api/src/rastro-boato/` para texto livre de menor — `unootube` ficou para trás); o que trocar primeiro no scaffold do `_template` (porta, manifesto, seção do clone em `main.tsx`, eventos em `lib/telemetria.ts`, contrato em `lib/tipos.ts` — a fiação já vem pronta desde a ADR-106); bibliotecas permitidas/proibidas; comandos exatos (`pnpm worktree criar expNNefNb --fatia api/<mod>,hub/<rota>,exp/<id>` sobre `origin/dev-local`, `pnpm new:exp`, `pnpm turbo typecheck lint test build`, `node scripts/e2e/rodar.mjs estudante`); variáveis de ambiente; manifesto `experiencia.json` completo (com `produto`, `unidade`, `permissoes`); versão em três lugares (`experiencia.json`, `package.json`, `EXP_VERSION` + `versao.test.ts`); entrada em `apps/hub/lib/entre-redes/catalogo.ts` (`ficha` + copy de estudante — sem copy não vai à tela) e rota em `lib/rotas-da-missao.ts` (ADR-100); porta em `apps/hub/lib/experiencias-dev.ts` (próxima livre, `strictPort`, também em `CORS_ORIGINS`); migration; seed em `prisma/catalogo-e-liberacoes.ts`; `midia-externa.json` se houver mídia ≥ 2 MB (ADR-63); `AGENTS.md` + `CLAUDE.md` + `README.md` da pasta; LaTeX (`12-experiencias`, `13-api`, `08-modelo-de-dados`, `18-adr`). Seção **"O que NÃO fazer"** técnica.

# 18. Tarefas (decompostas e ordenadas)
`T-xxx` · descrição atômica · RFs cobertos · arquivos · dependências · `[P]` se paralelizável · **comando de verificação**. Ordem: contratos → testes → implementação → docs.

# 19. Decisões (ADR) e questões abertas
Log ADR (título · status · contexto · decisão · alternativas · consequências). Questões abertas com dono e prazo — **deve estar vazia para status aprovado**. Marcadores `[NEEDS CLARIFICATION: <pergunta>, dono: <produto|design|dev|plataforma>]` consolidados aqui. Pendência cujo dono é **plataforma** (decisão de ADR nova, componente de DS a criar) é pendência humana resolvida na codificação: o PRD sai `aprovado-com-pendencias-de-plataforma` (🟡), nunca `aprovado`. Pendência de produto, design ou dev impede o PRD.

# 20. Testes e Definition of Done
Estratégia (unit de regras puras, contrato, tenancy, sanitizador com grep no `dist/`, smoke e2e por papel com asserções que falham quando quebra) · matriz de rastreabilidade RF → critério → teste → tarefa · DoD do monorepo (typecheck+lint+test, e2e do papel, Zod nas fronteiras, tenancy, sem segredo no client, `AGENTS.md`, LaTeX + ADR) · evidências exigidas.

# 21. Plano de lançamento
Fases `dev-local → dev → hml → main` (ADR-101; PR `--base dev-local`; tag semver só em `main`), `status` no catálogo (`em-breve` → `disponivel`), disponibilidade no painel `/unooria` (a DoD exige provar que a experiência **desliga**, ADR-87/88), liberação por turma pela professora (ADR-69), critérios de avanço e rollback (`node apps/hub/scripts/publicar-manifesto.mjs <exp> --versao x.y.z`), comunicação a professores, playtest piloto.

# 22. Apêndices e changelog
**Links, não cópias.** Os relatórios dos gates, a spec, o briefing de ofício, as arestas do fluxo, o
sheet de strings, o brief de assets e o insumo de dev já são arquivos próprios da sessão: aponte
para eles pelo caminho (`produto/01-gate-estrutural.md`, `design/03-fluxo-arestas.md`…). Copiá-los
para dentro do PRD dobrava o documento sem acrescentar informação e envelhecia à primeira correção.
Aqui fica só o histórico de versões deste PRD.
```

## C. Regras de redação para o agente escritor

- Português brasileiro; termos técnicos e identificadores no original.
- Uma ideia por frase. Tabelas para tudo que é lista paralela (RF, RNF, EVT, ENT, T, RISCO).
- Nunca inventar código BNCC, rota, tabela, componente ou ADR: se a fonte upstream não confirma, marcar `🔵 a validar` ou `[NEEDS CLARIFICATION]`.
- Nunca transcrever copy quando existe chave de string; referenciar a chave.
- Todo RF P0 deve ter pelo menos um critério EARS **e** aparecer em pelo menos uma tarefa e um teste.
- O PRD referencia caminhos reais do monorepo (`apps/experiencias/expNNefNb/…`, `apps/api/src/<slug>/…`) e os exemplares canônicos a imitar (`apps/api/src/unootube/`, `apps/experiencias/_template/`).
- Tamanho: resumo executivo ≤ 1 página; corpo completo sem limite artificial, mas sem repetir o que outra seção já disse — referenciar por número de seção.

## D. Anti-padrões que o gabarito bloqueia

| Anti-padrão | Bloqueio no gabarito |
|---|---|
| Linguagem vaga ("rápido", "intuitivo") | RF só com EARS/Gherkin; RNF só com número + método |
| "Como" dentro do requisito | Seção 8 declara necessidade; mecanismo vai para 16–18 |
| Métricas de vaidade | KPI exige baseline, alvo, prazo e EVT vinculado |
| Escopo que cresce na mão do agente | Seções 3 e 17 ("O que NÃO fazer") obrigatórias e não vazias |
| Lacuna resolvida por adivinhação | `[NEEDS CLARIFICATION]` + seção 19 vazia para aprovar |
| "Parece pronto" | Toda tarefa com comando de verificação; DoD exige evidência |
| Tudo P0 | P0 restrito ao que a rubrica exige (🔒) e à descoberta central |
| Sem rastreabilidade | IDs estáveis + matriz na seção 20 |
| PRD estático | Frontmatter com versão/status + changelog na seção 22 |

## E. Fontes

Cagan — *How to Write a Good PRD* (svpg.com) · Thoughtworks — *Spec-driven development* (2025) · GitHub Spec Kit `spec-driven.md` · AWS Kiro — Specs e requirements (EARS) · Anthropic — *Claude Code best practices* e *Effective context engineering for AI agents* · agents.md · Pragmatic Engineer — *RFCs and Design Docs* · *Design Docs at Google* · Mavin — EARS · Cucumber — Gherkin reference · adr.github.io · c4model.com · Agile Alliance — INVEST · Scrum Guide — Definition of Done · Katalon — Requirements Traceability Matrix · Moesif — Contract-first API · Fora Soft — NFR checklist (14 categorias) · Centercode — 5 common PRD mistakes · Augment Code — Spec-driven development · Amazon Working Backwards — PR/FAQ · Lenny's Newsletter — templates favoritos · Atlassian — PRD template · LGPD art. 14 (dados de crianças e adolescentes).
