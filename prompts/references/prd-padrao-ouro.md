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
9. **Tarefas atômicas, ordenadas, com verificação.** Cada tarefa cita os RFs que cobre, os arquivos que toca e o comando que prova que ficou pronta. `[P]` marca o que pode rodar em paralelo. Ordem: contratos → testes → implementação.
10. **Documento vivo e versionado** com frontmatter, changelog e status; dono humano nomeado.
11. **Economia de contexto.** Resumo executivo de uma página no topo; detalhe em seções hierárquicas; referências por caminho de arquivo, não por cópia.
12. **Evidência de conclusão, não afirmação.** A Definition of Done exige saída de testes, comandos rodados e evidências e2e.

## B. Gabarito — estrutura obrigatória do PRD de missão Unooria

```markdown
---
prd_id: PRD-<slug>
titulo: <nome da missão>
versao: 0.1.0
status: draft | em-revisao | aprovado | em-implementacao | lancado
slug_experiencia: exp-NN-<nome>
serie: ["4EF"]            # formato da plataforma; [] = transversal
ambiente_simulado: <instagram|youtube|chatgpt|tiktok|whatsapp>
secao_ds: <instanooria|unitube|chatgpt|tiktooria|whatsappmobile>
owners: {produto: <nome>, design: <nome>, dev: <nome>, pedagogico: <nome>}
gates: {estrutural: 🟢|🔴, pedagogico: ..., experiencia: ..., final: ..., design: ..., dev: 🟢|🟡|🔴}
links: {figjam: <url>, figma: <url>, spec: spec/<slug>-spec.md, one_pager: ...}
needs_clarification: 0
data: AAAA-MM-DD
---

# 0. Resumo executivo (1 página)
Problema · para quem · descoberta central em uma frase · solução em uma linha · métrica-alvo · prazo · status dos gates. Mini press release opcional (Amazon PR/FAQ).

# 1. Contexto e problema
Trilha/ano/unidade · problema de aprendizagem · evidências · alinhamento com a plataforma (Entre Redes) · o que já existe no catálogo e como esta missão se diferencia (critério 2.5).

# 2. Objetivos e métricas
North star pedagógica · 2–4 KPIs com baseline, alvo, prazo e **evento que o alimenta** (EVT-xxx) · guardrail metrics (o que não pode piorar: tempo de ato, taxa de erro de plataforma, quebra de imersão) · hipóteses de validação (9.3) e plano de playtest.

# 3. Não-objetivos e fora de escopo
Lista explícita com motivo. Inclui V2 (o que fica para depois) e o que a rubrica proíbe (ranking de crianças, nota formal, IA sem curadoria…).

# 4. Personas e jobs-to-be-done
Estudante (ano, faixa etária, perfil cognitivo — caps de decisão e leitura), Professor (preparo, condução, leitura), Gestor (só agregado). Cenários de dispositivo (1:1, 2–4 por aparelho, projeção única).

# 5. Experiência — narrativa e mecânica (as 6 etapas)
Desafiar → Navegar → Decidir → Resultado/Aha → Explicar → Refletir. Por etapa: o que o sistema apresenta, ordena, bloqueia e garante; verbo nativo; ator. Descoberta central e o beat exato. Checkpoints modulares entre etapas com persistência de estado, tempos sugeridos de execução, controle docente de ritmo, podcast de recapitulação e flexibilidade para formatos de aula (50 min, 2 aulas ou sessões fracionadas). Ausências declaradas do ambiente. Briefing de ofício (aposta, pico, beat memorável, não-negociáveis).

# 6. Fluxo e máquina de estados
Estados com nome próprio (viram enum), tabela de transições (estado inicial · gatilho · regra · estado seguinte · responsável · reversível?), caminhos degenerados com rota, gates de professora, estados de falha na voz da ficção, reentrada (F5, outro dia), latch, conclusão, segunda aplicação. Diagrama Mermaid `stateDiagram-v2` + link do FigJam.

# 7. User stories (INVEST)
Uma por tela do inventário: Como/Quero/Para · frame do Figma · chaves de string · etapa · critérios sustentados · estados · dependências. Itens 🔒 = requisito de conformidade (rubrica/BNCC/acessibilidade), não negociável.

# 8. Requisitos funcionais
Tabela `RF-xxx` · título · descrição (necessidade, não mecanismo) · prioridade P0/P1/P2 · rastreio (objetivo, story, critério da rubrica) · **critérios de aceite EARS/Gherkin** · casos de borda. Mínimo obrigatório: estudante, professor (dashboard, gatilhos, customização, roteiro), plataforma (persistência, reentrada, falhas).

# 9. Requisitos não funcionais
Checklist com meta numérica e método de medição por categoria: performance (p95, peso do bundle, mídia >2MB em bucket) · disponibilidade/recuperabilidade (F5, sessão expirada, offline) · segurança (gabarito server-side, nada no bundle, identidade do token) · **privacidade e LGPD para menores** (art. 14; `estudante_id` opaco; PII zero; texto livre em tabela própria; graus de medida scored/indicative/zero/none; retenção declarada ou lacuna assumida) · acessibilidade (WCAG 2.2 AA; áudio + pictograma em anos iniciais; contraste; teclado; `prefers-reduced-motion`) · usabilidade por faixa (tetos de palavras, decisões, duração de ato) · observabilidade (eventos, logs com `codigo`, OTel) · compatibilidade (Chromebook/desktop; viewport) · i18n (pt-BR único) · custo (IA: teto de tokens por sessão; Cloud Run).

# 10. UX, telas e design
Inventário de telas (ID `E<etapa>-<ator>-<n>`, peso, elementos, estados) · direção por tela (pico/alta) · links dos frames Figma (fileKey + nodeId) · sheet de strings (chave `eN.tipo.nome`, seção `clone|unooria`, redundância) · mapa "quem está falando" tela a tela · viewport · permissões de iframe · assets com peso · interações instrumentadas.

# 11. Modelo de dados
Entidades `exp_NN_*` com campos, tipos, sensibilidade (PII de menor?), retenção, canal (operacional × analítico), `escola_id NOT NULL` + RLS. Enums de estado. Tabelas-contrato entre experiências. O que **nunca** vai ao bundle. Diagrama Mermaid `erDiagram`.

# 12. Contratos de API
Rotas por papel (`/<slug>/*`), método, guards, `@Roles`, schema Zod de entrada e **de resposta**, códigos de erro de domínio nomeados (409 `LIMITE_SALVOS`…), idempotência e locks (relógio coletivo, cliques duplos). Formato OpenAPI resumido.

# 13. Eventos, telemetria e analytics
Tabela `EVT-xxx` · verbo (`attempted|interacted|progressed|completed|scored`) · objeto · quando dispara · campos (`dados` só número/booleano/vocabulário fechado) · canal · aparece no dashboard como · retenção · KPI que alimenta. Volume estimado por sessão × turma. Métricas proibidas. Versão do instrumento.

# 14. Pedagogia e conformidade
Matriz habilidade BNCC (código, confirmado ou 🔵 a validar) → evidência observável → interação → dado gravado. Competência socioemocional nomeada. Rastreabilidade curricular. Gabarito (autor e revisor nomeados; só no servidor). Graus de medida. Guardrails de IA (8.1/8.2) e éticos (8.3–8.6). Papel do erro. O que cada adulto vê.

# 15. Dependências e integrações
Seção do DS e componentes faltantes (com responsável e prazo) · versão do `@unooria/design-system` · SDK · módulos da api reutilizados · IA (provider, quota, mock) · outras missões (contrato e fallback) · conteúdo autoral (inventário, quem produz).

# 16. Arquitetura da solução (plano técnico)
Contexto da plataforma resumido (monorepo, hub + api + experiência estática, SDK/postMessage, tenancy, canais de dado). Diagrama C4 nível 1–2 (Mermaid). Alternativas consideradas e trade-offs. Decisões que exigem ADR nova.

# 17. Plano de implementação — arquivos e convenções
Lista de **arquivos a criar/alterar com caminho completo**, módulo a imitar (exemplar canônico), bibliotecas permitidas/proibidas, comandos exatos (`pnpm new:exp`, `pnpm turbo typecheck lint test build`, `node scripts/e2e/rodar.mjs estudante`), variáveis de ambiente, manifesto `experiencia.json` completo, entrada no catálogo, migration, porta de dev. Seção **"O que NÃO fazer"** técnica.

# 18. Tarefas (decompostas e ordenadas)
`T-xxx` · descrição atômica · RFs cobertos · arquivos · dependências · `[P]` se paralelizável · **comando de verificação**. Ordem: contratos → testes → implementação → docs.

# 19. Riscos e mitigações
Tabela risco · probabilidade · impacto · mitigação · dono. Pre-mortem curto.

# 20. Decisões (ADR) e questões abertas
Log ADR (título · status · contexto · decisão · alternativas · consequências). Questões abertas com dono e prazo — **deve estar vazia para status aprovado**. Marcadores `[NEEDS CLARIFICATION]` consolidados aqui.

# 21. Testes e Definition of Done
Estratégia (unit de regras puras, contrato, tenancy, sanitizador com grep no `dist/`, smoke e2e por papel com asserções que falham quando quebra) · matriz de rastreabilidade RF → critério → teste → tarefa · DoD do monorepo (typecheck+lint+test, e2e do papel, Zod nas fronteiras, tenancy, sem segredo no client, `AGENTS.md`, LaTeX + ADR) · evidências exigidas.

# 22. Plano de lançamento
Fases (dev → hml → main), feature flag/`status` no catálogo (`em-breve` → `disponivel`), critérios de avanço e rollback (`versaoAtiva`), comunicação a professores, playtest piloto.

# 23. Glossário
Termos de domínio com definição única (aluno/estudante, missão/experiência/atividade, ato/etapa, handoff, gate, latch, seção do DS, canal operacional/analítico, graus de medida).

# 24. Apêndices e changelog
Relatórios dos gates (resumos), spec, briefing de ofício, arestas do fluxo, sheet de strings, brief de assets, insumo de dev (modelo-de-insumo preenchido), relatório da banca de dev. Histórico de versões.
```

## C. Regras de redação para o agente escritor

- Português brasileiro; termos técnicos e identificadores no original.
- Uma ideia por frase. Tabelas para tudo que é lista paralela (RF, RNF, EVT, ENT, T, RISCO).
- Nunca inventar código BNCC, rota, tabela, componente ou ADR: se a fonte upstream não confirma, marcar `🔵 a validar` ou `[NEEDS CLARIFICATION]`.
- Nunca transcrever copy quando existe chave de string; referenciar a chave.
- Todo RF P0 deve ter pelo menos um critério EARS **e** aparecer em pelo menos uma tarefa e um teste.
- O PRD referencia caminhos reais do monorepo (`apps/experiencias/exp-NN-<slug>/…`, `apps/api/src/<slug>/…`) e os exemplares canônicos a imitar (`apps/api/src/unootube/`, `apps/experiencias/_template/`).
- Tamanho: resumo executivo ≤ 1 página; corpo completo sem limite artificial, mas sem repetir o que outra seção já disse — referenciar por número de seção.

## D. Anti-padrões que o gabarito bloqueia

| Anti-padrão | Bloqueio no gabarito |
|---|---|
| Linguagem vaga ("rápido", "intuitivo") | RF só com EARS/Gherkin; RNF só com número + método |
| "Como" dentro do requisito | Seção 8 declara necessidade; mecanismo vai para 16–18 |
| Métricas de vaidade | KPI exige baseline, alvo, prazo e EVT vinculado |
| Escopo que cresce na mão do agente | Seções 3 e 17 ("O que NÃO fazer") obrigatórias e não vazias |
| Lacuna resolvida por adivinhação | `[NEEDS CLARIFICATION]` + seção 20 vazia para aprovar |
| "Parece pronto" | Toda tarefa com comando de verificação; DoD exige evidência |
| Tudo P0 | P0 restrito ao que a rubrica exige (🔒) e à descoberta central |
| Sem rastreabilidade | IDs estáveis + matriz na seção 21 |
| PRD estático | Frontmatter com versão/status + changelog na seção 24 |

## E. Fontes

Cagan — *How to Write a Good PRD* (svpg.com) · Thoughtworks — *Spec-driven development* (2025) · GitHub Spec Kit `spec-driven.md` · AWS Kiro — Specs e requirements (EARS) · Anthropic — *Claude Code best practices* e *Effective context engineering for AI agents* · agents.md · Pragmatic Engineer — *RFCs and Design Docs* · *Design Docs at Google* · Mavin — EARS · Cucumber — Gherkin reference · adr.github.io · c4model.com · Agile Alliance — INVEST · Scrum Guide — Definition of Done · Katalon — Requirements Traceability Matrix · Moesif — Contract-first API · Fora Soft — NFR checklist (14 categorias) · Centercode — 5 common PRD mistakes · Augment Code — Spec-driven development · Amazon Working Backwards — PR/FAQ · Lenny's Newsletter — templates favoritos · Atlassian — PRD template · LGPD art. 14 (dados de crianças e adolescentes).
