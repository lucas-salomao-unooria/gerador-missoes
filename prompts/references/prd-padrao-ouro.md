# PRD Padrão Ouro — princípios e gabarito (consumo por agente de codificação)

> Consolidação de Cagan (SVPG), Google Design Docs, Atlassian, Pragmatic Engineer (RFCs), GitHub Spec Kit, AWS Kiro (EARS), Cucumber (Gherkin), ADR/MADR, C4, INVEST, Scrum Guide (DoD), Katalon (RTM), Fora Soft (NFR), Anthropic (context engineering / Claude Code) e AGENTS.md. Fontes listadas ao final.
>
> Revisto em 07/10/2026 contra o código da plataforma, depois da auditoria dos PRDs da exp01ef1b e da exp09ef1b: o teste do PRD é um agente de codificação implementar a missão **sem decidir nada de produto, pedagogia ou design**. Tudo o que ele precisaria decidir está escrito, ou está marcado.

## A. Princípios que o documento obedece

1. **O quê e por quê, separados do como.** Requisitos declaram necessidade, não mecanismo (Cagan, Spec Kit). O "como" vive na seção de plano técnico, explicitamente marcada — e nunca contamina os requisitos funcionais.
2. **Três camadas de contexto para o agente**: (a) regras duráveis do repositório (`AGENTS.md`/`CLAUDE.md` do monorepo — referenciadas, não copiadas); (b) o quê/por quê (este PRD); (c) o como (plano técnico e tarefas, seções 16–21 deste gabarito).
3. **Ambiguidade zero — ou declarada.** Toda lacuna vira `[NEEDS CLARIFICATION: pergunta]` (Spec Kit), e toda decisão que o agente tomou no lugar do PO vira `[PROPOSTA — validar com PO: …]`. O status do PRD é calculado pela esteira a partir desses marcadores e dos gates — o redator não o escreve.
4. **Critérios verificáveis por máquina.** Cada requisito funcional — e toda linha P0, sem exceção — tem critério de aceite em **EARS** (`QUANDO <gatilho>, O SISTEMA DEVE <resposta>` · `SE <condição indesejada>, ENTÃO…` · `ENQUANTO <estado>…` · `ONDE <feature opcional>…`) e/ou **Gherkin** (`Dado / Quando / Então`, 3–5 passos), e o teste que o prova nomeado como `arquivo › caso`. Cada NFR tem número, unidade, método de medição e a origem do número.
5. **IDs estáveis e rastreabilidade.** `RF-001`, `RNF-SEC-002`, `EVT-010`, `ENT-003`, `API-004`, `T-014`, `RISCO-002`, `ADR-001`. A matriz de rastreabilidade liga objetivo → RF → critério → tarefa → teste.
6. **Não-objetivos explícitos e "o que NÃO fazer" técnico.** É a defesa contra scope creep do agente (Google, Augment Code).
7. **Priorização com barra alta.** P0 = sem isso a missão não lança (e reprova na rubrica); P1 = necessário para o release; P2 = desejável. Rank-order dentro de cada classe.
8. **Contratos antes de código.** Rotas (Zod de entrada e de resposta escritos no próprio PRD), eventos, entidades e o vocabulário de estados definidos no PRD; o agente implementa contra eles. Nome de schema sem a definição ao lado não é contrato.
9. **Tarefas atômicas, ordenadas, com verificação.** Cada tarefa cita os RFs que cobre, os arquivos que toca e o comando que prova que ficou pronta. Tarefa que cobre o intervalo inteiro de requisitos (`RF-001..RF-014`) não é tarefa: é a lista de tarefas que ainda não foi escrita, e nenhum comando prova que ela ficou pronta. `[P]` marca o que pode rodar em paralelo. Ordem: contratos → testes → implementação.
10. **Documento vivo e versionado** com frontmatter, changelog e dono humano nomeado. O status não mora no frontmatter: a esteira o calcula pelos gates.
11. **Economia de contexto.** Resumo executivo de uma página no topo; detalhe em seções hierárquicas; referências por caminho de arquivo, não por cópia.
12. **Evidência de conclusão, não afirmação.** A Definition of Done exige saída de testes, comandos rodados e evidências e2e.
13. **A plataforma vence a spec no como.** O one-pager e a spec decidem o que a missão ensina, mede e diz; tipo de coluna, rota, componente, modelo de IA e mecanismo seguem a base da plataforma (o contrato e os moldes de `references/plataforma/`). O corpo segue a plataforma, e a divergência fica registrada na seção 19 com dono `produto`.
14. **Número tem origem.** Alvo, limiar, teto de tokens, peso de bundle, p95, FPS, duração e data trazem a origem entre parênteses (§17 do one-pager, bloco da spec, contrato da plataforma, medida com data) ou são `[PROPOSTA — validar com PO: …]`. Número sem origem é decisão que alguém tomou sem dizer.

## B. Gabarito — estrutura obrigatória do PRD de missão Unooria

O frontmatter não tem `status`, e o documento não tem seção «Status dos gates»: a esteira calcula o status do PRD pelos gates, e o dossiê da execução publica o de cada gate. Subseções vão em `##` dentro da seção (`## 14.2`), nunca no nível do título da seção.

```markdown
---
prd_id: PRD-<slug>
titulo: <nome da missão>
versao: 0.1.0
slug_experiencia: expNNefNb
produto: entre-redes | plano-de-aula | plano-de-ensino | bem-estar
serie: ["4EF"]            # formato da plataforma; [] = transversal
unidade: 1 | 2 | 3 | 4 | nenhuma
ambiente_simulado: <o ambiente da spec (bloco 14): clone da lista fechada, ambiente novo ou mini-jogo>
secao_ds: <unooriaai|unoovista|unoochat|tiktooria|nova:<nome>|minijogo:<nome>>  # ambientes.md; legada só por decisão do PO
links: {stitch: <url do projeto>, miro: <url do board — omita se indisponível>, prototipo: design/08-prototipo.html, diagramas: design/09-diagramas.html, spec: produto/05-spec-missao.md, one_pager: produto/00-one-pager.md, pedagogico: one-pager-pedagogico.md}  # só caminhos que a sessão tem: não existe pasta spec/
data: AAAA-MM-DD
---

# 0. Resumo executivo (1 página)
Problema · para quem · descoberta central em uma frase · solução em uma linha · o número que a missão existe para mover (o KPI de evidência da seção 2, com alvo só se o §17 do one-pager ou o 9f o fixam) · a fase de lançamento da seção 21, sem data que ninguém homologou. Sem status de gate: o dossiê da execução os publica — o PRD da exp01ef1b (07/10/2026) abriu com uma seção «Status dos gates». Mini press release opcional (Amazon PR/FAQ).

# 1. Contexto e problema
Trilha/ano/unidade · problema de aprendizagem · evidências · alinhamento com a plataforma (Entre Redes) · o que já existe no catálogo e como esta missão se diferencia (critério 2.5).

# 2. Objetivos e métricas
North star pedagógica · **tabela de KPIs no formato abaixo, lida por gate determinístico** ·
guardrail metrics (o que não pode piorar) · hipóteses de validação **do §17 do one-pager, com as
palavras e os números delas** (meta que não está no one-pager nem no 9f não se inventa).
**KPI de evidência por habilidade** — quantos estudantes chegam a Atingiu em cada habilidade do
bloco 11 (uma linha pode cobrir várias), calculado sobre a coluna de nível que a seção 14 nomeia:
na plataforma, `evidencias.status` da habilidade (`exp_id` da missão, `habilidade = '<código>'`),
que a ficha da seção 14.2 alimenta pela porta `marcar` na transação da jogada. O nível nunca vai no
`track`, e a missão não grava nível em tabela própria. É o número que a missão existe para mover, e
um gate confere que cada habilidade aparece numa linha da tabela.

```
| KPI | PQ | Pergunta | Decisão | Corte | Tela | Evento(s) | Como calcula | Baseline | Alvo | Prazo |
|---|---|---|---|---|---|---|---|---|---|---|
| KPI-01 | T7 | De cada X turmas liberadas, quantas chegam ao fim da missão? | Menos da metade → encurtar ou dividir | missao · serie | — | `EVT-U01`, `EVT-U03` | turmas com `EVT-U03` / turmas com `EVT-U01` | sem baseline — primeira medição | sem meta — primeira medição | — |
| KPI-02 | PQ-01 | ... | ... | turma | `E3-ALU-02` | `EVT-005` | count(`EVT-005` com `contexto.tempo_ms` ≥ 120000) | 45% (playtest 12/08, n=23) | ≥ 80% (9f da spec, PQ-01) | piloto (seção 21) |
| KPI-03 | — | Quantos estudantes chegam a Atingiu em `<código>`? | Abaixo do limiar do §17 → rever a etapa que marca a habilidade; sem limiar, o PO o fixa depois da primeira medição | turma | `<tela do latch>` | `EVT-007` | estudantes com `evidencias.status` = 'atingiu' em `<código>` / estudantes da turma | sem baseline — primeira medição | sem meta — primeira medição | — |
```

**Cada coluna existe por um motivo, e um gate confere:** sem `Pergunta` e `Decisão` o número é
métrica de vaidade (34 dos 49 KPIs das primeiras execuções não tinham nenhuma das duas);
`Tela` é o que permite conferir que o evento dispara onde o KPI diz — havia KPI de uma tela
alimentado por evento de outra, e o número saía parecendo certo; `Baseline` traz o número com a
**origem entre parênteses** ou o literal `sem baseline — primeira medição`, porque `0%` não é
medida (20 dos 49 tinham `0%`); `Como calcula` cita os campos de `resultado`/`contexto` que o
evento de fato carrega.

**Alvo e Prazo só com origem.** Alvo é o número do §17 do one-pager ou do 9f da spec, com a origem
entre parênteses; sem ele, `sem meta — primeira medição`. Prazo vem do mesmo lugar, ou é `—`. O PRD
da exp09ef1b copiou para a KPI-01 o `≥ 70%` e os `2 meses` do exemplo que estava aqui; o da
exp01ef1b (07/10/2026) pôs `2 meses` em seis KPIs e alvo sem origem em todos os vinte.

KPI transversal (herdado de uma `T` de dono `missao` do catálogo de `perguntas-de-produto.md`)
usa `Tela: —`, **a pergunta da transversal com as palavras dela**, e **só os sinais que o catálogo
lista para ela** — nunca um evento próprio da mecânica, mesmo que pareça próximo. As de dono
`plataforma` (T1–T6, T13, T18) não viram KPI da missão: a missão não tem o dado. As
transversais não precisam de KPI próprio; o que a missão deve a elas é que a seção 13 traga
**todos os sinais universais** com o id e o objeto do catálogo: os `EVT-U*` na **tabela de eventos**
(com o verbo), e os `EVT-P*` — que são colunas do módulo, não telemetria — numa tabela própria
**«Sinais do professor»**, no formato do catálogo: `| Sinal | Objeto | Quando grava | Onde fica | Responde |`. Os ids `EVT-U*`/`EVT-P*` são reservados: evento da mecânica é `EVT-001`, `EVT-002`…


# 3. Não-objetivos e fora de escopo
Lista explícita com motivo. Inclui V2 (o que fica para depois) e o que a rubrica proíbe (ranking de crianças, nota formal, IA sem curadoria…). **Toda ausência do bloco 5 da spec entra aqui com as palavras da spec** — reescrita, a conferência não a acha e o redator a perde de vista.

# 4. Personas e jobs-to-be-done
Estudante (ano, faixa etária, perfil cognitivo — caps de decisão e leitura), Professor (preparo, condução, leitura), Gestor (só agregado). Cenários de dispositivo (1:1, 2–4 por aparelho, projeção única); com 2 a 4 por aparelho, a missão tem equipes (seção 17.1).

# 5. Experiência — narrativa e mecânica (as 6 etapas)
Desafiar → Navegar → Decidir → Resultado/Aha → Explicar → Refletir. Por etapa: o que o sistema apresenta, ordena, bloqueia e garante; verbo nativo; ator. Descoberta central e o beat exato. **Tempos e formatos de aula do §10 do one-pager:** a tabela por etapa (em tela · fora da tela), o total em tela com o mesmo número, os checkpoints com persistência de estado, o controle docente de ritmo e os cenários (aula única, 2 aulas, sessões fracionadas). O podcast de recapitulação no momento que o §11 diz. Ausências declaradas do ambiente. Briefing de ofício (aposta, pico, beat memorável, não-negociáveis).

# 6. Fluxo e máquina de estados
**Vocabulário único de estados.** Os estados são os do contrato de estados da spec (bloco 2), com o
nome que o banco grava — o valor do CHECK da migration e da constante do módulo (`regras/passos.ts`,
`vocabulario.ts`, no molde do Júri). Um nome por estado no PRD inteiro: stories, rotas, eventos,
testes. A api compara o texto do CHECK com o da constante num teste de Postgres; um terceiro nome,
vindo do design, é o que quem codifica teria de escolher sozinho. Se o design chamou um estado de
outro jeito (fluxo, protótipo, Stitch), a seção abre com o de-para `| No design | Estado do contrato |`,
e dali em diante só o do contrato. Por estado:

`| Estado | Tela(s) | O que o servidor grava ao entrar | Latch | Quem destrava | Timer | prefers-reduced-motion |`

- **Latch:** o carimbo `<acao>_em` e os valores do gesto, gravados no mesmo `UPDATE` e amarrados por
  CHECK ao estado gravado (no Júri, `votado_em` preenchido ⇔ `passo` além de `feed`). Estado que a
  etapa da turma impõe (a `galeria` do Júri) nunca é gravado.
- **Quem destrava:** o estudante (a ação), o professor (`POST …/gate`) ou o servidor (a regra).
- **Timer:** a duração com a origem (§10 do one-pager, spec) ou `—`. Nenhum avanço automático por
  tempo sem justificativa escrita (seção 10.2).
- **prefers-reduced-motion:** o que a animação vira (corte seco, sem zoom); o estado e o dado gravado
  não mudam.

Depois: tabela de transições (estado inicial · gatilho · regra · estado seguinte · responsável · reversível?), caminhos degenerados com rota, gates de professora, estados de falha na voz da ficção, reentrada (F5, outro dia), conclusão (`concluida_em` preenchido ⇔ estado final), zerar = rodada nova (seção 11). Diagrama Mermaid `stateDiagram-v2` com os mesmos nomes (o mesmo que o D3 emitiu, renomeado pelo de-para).

# 7. User stories — uma por tela
**Uma story por tela do inventário da jornada** (`design/02-jornada-telas.md`), do estudante e do
professor, na ordem da jornada; nenhuma agrupada. A exp01ef1b tinha 22 telas na jornada e 86 chaves
na copy revisada, e o PRD de 07/10/2026 trazia 9 stories (`E4-ALU-01..03` numa só) e nenhuma chave.
Cada story:

- Como/Quero/Para · etapa · estado(s) da seção 6 · RFs que sustenta · dependências. Itens 🔒 = requisito de conformidade (rubrica/BNCC/acessibilidade), não negociável.
- **Especificação da tela** (D5, `design/05-wireframes-cobertura.md`): elementos, ação (verbo nativo), resultado da ação, o que a tela mostra em cada estado, o frame no Stitch.
- **Copy — todas as chaves** que a copy revisada (`design/06-copy-strings-revisada.md`) dá para a tela, nenhuma de fora, em `| Chave | Onde vive |`. Onde vive: `bundle de textos` (`src/lib/textos.ts` da experiência) · `ficha de evidência no servidor` (enunciado e alternativas do Canal B, critério dos níveis) · `catálogo/guia do hub` (`catalogo.ts`, `guias/<expId>.ts`) · `aria-label`. A chave é citada; o texto final mora no sheet.
- **Acessibilidade da tela** e, quando a spec declara, a **CAA** da tela (seção 10.2).
- Critério de aceite da tela em EARS ou Gherkin — o mesmo que o RF repete.

# 8. Requisitos funcionais
Tabela `RF-xxx` · título · descrição (necessidade, não mecanismo) · prioridade P0/P1/P2 · rastreio (objetivo, story, critério da rubrica) · **critério de aceite EARS ou Gherkin em toda linha P0** (linha P0 sem critério não é requisito) · teste que o prova (`arquivo › caso`) · casos de borda. Mínimo obrigatório: estudante; professor — o recorte da aula (disciplina, tema, assuntos, contexto), a geração por IA com curadoria e homologação humana (seção 12.2), o banco curado padrão quando a spec o tem, o painel, o gate da turma, zerar (rodada nova), o roteiro de perguntas no momento que o one-pager diz; cada ação do professor do §9 do one-pager é um RF com rota; **podcast de recapitulação quando o §11 o traz** (quem toca — o professor: o podcast não tem rota de estudante, ADR-150 —, em que tela e em que momento, as falas do tema que o professor revisa na homologação, a linha no inventário da seção 15.2 e a tarefa); plataforma (persistência por turma e rodada, reentrada, falhas).

# 9. Requisitos não funcionais
Checklist com meta numérica, origem do número e método de medição por categoria: performance (p95, peso do bundle, mídia >2MB em bucket) · disponibilidade/recuperabilidade (F5, sessão expirada, offline) · segurança (gabarito server-side, nada no bundle, identidade do token) · **privacidade e LGPD para menores** (art. 14; `estudante_id` opaco; PII zero; texto livre em tabela própria; graus de medida scored/indicative/zero/none; retenção declarada ou lacuna assumida) · acessibilidade (WCAG 2.2 AA; áudio + pictograma em anos iniciais; contraste; teclado; `prefers-reduced-motion`; o detalhe por tela fica na seção 10.2) · usabilidade por faixa (tetos de palavras, decisões, duração de ato) · observabilidade (eventos, logs com `codigo`, OTel) · compatibilidade (Chromebook/desktop; viewport) · i18n (pt-BR único) · custo (IA: teto de tokens por turma/preparação; Cloud Run). A plataforma fixa poucos números (mídia ≥ 2 MB vai ao bucket, ADR-63; o resto está no contrato e nos `AGENTS.md`); p95, peso de bundle, FPS e teto de tokens que nenhuma fonte fixa são `[PROPOSTA — validar com PO: …]`.

# 10. UX, telas e design
## 10.1 Inventário e direção
Inventário de telas (ID `E<etapa>-<ator>-<n>`, peso, elementos, estados) · direção por tela (pico/alta) · **link do projeto no Stitch e a tabela de telas**, mais o protótipo navegável (`design/08-prototipo.html`) e a folha de diagramas (`design/09-diagramas.html`) · **como a experiência é embedada** (casca de aparelho pelo `viewport` do manifesto, ou janela do hub) · sheet de strings (chave `eN.tipo.nome`, seção `clone|unooria`, redundância; as chaves de cada tela estão na story dela) · mapa "quem está falando" tela a tela · viewport · permissões de iframe · assets com peso · interações instrumentadas.
## 10.2 Acessibilidade por tela e CAA
`| Tela | Nome acessível (chave do aria-label) | Foco ao entrar e ordem | aria-live (o que anuncia e quando) | prefers-reduced-motion | Avanço automático |`
Avanço automático é `não` por padrão; `sim` só com a justificativa escrita (a duração com origem e
por que a criança não precisa agir): tela que anda sozinha tira a vez de quem lê devagar ou usa
leitor de tela. **CAA, quando a spec a declara** (camada `design/04b-camada-caa.md`): a prancha (o
que traz, onde aparece — seção `unooria`, nunca dentro do clone —, a versão imprimível), os
pictogramas por conceito (IDs do brief de assets), as **chaves de instrução CAA** (as chaves de
áudio que cada símbolo lê), o alvo de toque e o modo de resposta alternativo de cada tela, que vira
RF. A exp01ef1b tinha camada CAA com prancha, e o PRD de 07/10/2026 nem a recebia.

# 11. Modelo de dados
Os tipos e as chaves são os da plataforma, não os da spec. Moldes da base:
`references/plataforma/exemplo-schema-exp.md` (o recorte do `schema.prisma`) e
`references/plataforma/exemplo-migration-exp06ef1b.md` (a migration que cria as tabelas do Júri, com
o bloco manual). O PRD da exp01ef1b (07/10/2026) declarou `turma_id` e `estudante_id` como `text`
sem FK, PK composta com `escola_id` e uma coluna `tentativa` no lugar da rodada.

- **Tipos:** `escola_id TEXT NOT NULL` em toda tabela (é o tenant que a RLS compara); `turma_id UUID NOT NULL`, denormalizado, com FK para `turmas(id)` `ON DELETE CASCADE`; `estudante_id UUID NOT NULL` com FK para `users(id)` `ON DELETE CASCADE` em **toda** tabela da missão, inclusive `_reflexoes` (a trava da identidade única: `identidade-unica.spec.ts` reprova coluna de pessoa sem FK); carimbo de pessoa que não pode travar a saída de ninguém (`criado_por`, `aprovado_por`) é UUID **sem** FK; ids `UUID DEFAULT gen_random_uuid()`.
- **Atividade = o pacote que o professor homologou** (`<id>_pacotes` no molde, ADR-112/130): `ativo`, `criado_por`, o conteúdo em `JSONB` validado pelo Zod da homologação (o CHECK cobra só a forma), contadores de IA (`ia_geracoes`, `ia_tokens`). Um ativo por turma por **índice único parcial** `WHERE ativo`. Nasce pronto (`ativo = false`); quem põe no ar é o professor, e pôr no ar libera a missão na sala (ADR-146).
- **Gate da turma** `<id>_gates_turma`, PK `turma_id`: qual pacote e qual **rodada** estão em andamento e a etapa coletiva (polling, ADR-93/94).
- **Sessão** `<id>_sessoes`: PK `id`, e `UNIQUE (pacote_id, rodada, estudante_id)` com nome dado à mão (`map:`; o nome gerado passa de 63 caracteres e o Postgres o corta). **Reaplicar soma a rodada, nada se apaga nem se arquiva**: a linha da rodada anterior fica, imutável, e é ela que o painel de habilidades lê. O que se conta por ação é `<acao>_tentativas`.
- **Estado** é `TEXT` com CHECK, nunca enum Prisma; o vocabulário do CHECK é o mesmo texto da constante do código, com os nomes da seção 6.
- **Latch** = carimbo `<acao>_em TIMESTAMPTZ` e os valores do gesto juntos, com CHECK de equivalência ao estado gravado; conclusão `concluida_em` preenchido ⇔ estado final.
- **Bloco manual da migration** (o Prisma não gera): os CHECKs, o índice parcial, `ENABLE` + `FORCE ROW LEVEL SECURITY` com a policy `escola_id = current_setting('app.escola_id', true)`, e o `GRANT SELECT, INSERT, UPDATE, DELETE` de cada tabela nova à role `app_runtime`, dentro do bloco `DO $$` que só concede se a role existe.
- `versao_instrumento TEXT NOT NULL DEFAULT '1.0.0'`. Texto livre de menor em tabela própria (`<id>_reflexoes` no molde da A Seleção, com `char_length` no CHECK), lida só por quem leciona, fora de log e telemetria (`observabilidade/redaction.ts`).
- **Nível de habilidade não mora em tabela da missão**: ela grava o que a criança fez (as colunas que a regra da seção 14.2 lê) e chama `EvidenciasService.marcar`; o nível fica em `evidencias_marcas` e `evidencias`, da plataforma. Sem tabela própria de enquete nem de nota.
- Os `EVT-P*` do catálogo gravam em colunas da missão: onde o catálogo diz `<modulo>_conteudo_turma`, no molde atual é o pacote (`ia_geracoes`, `ia_tokens`, `criado_em`) ou coluna nova nele; a tabela «Sinais do professor» diz a coluna real.

Sensibilidade (PII de menor?) e retenção por tabela (ou lacuna assumida por escrito). Tabelas-contrato entre experiências. O que **nunca** vai ao bundle. Diagrama Mermaid `erDiagram`.

# 12. Contratos de API
## 12.1 Rotas
Uma linha `API-xxx` por rota, no molde do Júri (`references/plataforma/exemplo-juri-contrato-rotas.md`; índice real em `references/plataforma/openapi-indice.md`). Estudante: `GET /<modulo>/sessao`, `GET /<modulo>/gate` e uma rota por jogada (`POST /<modulo>/<acao>`). Professor: `GET /<modulo>/turmas`, `GET …/turmas/:turmaId/painel`, `POST …/turmas/:turmaId/gate`, `POST …/turmas/:turmaId/zerar` (rodada nova, nunca `DELETE`), `GET …/turmas/:turmaId/pacotes`, `GET …/turmas/:turmaId/pacotes/:pacoteId`, `POST …/turmas/:turmaId/pacotes/:pacoteId/em-andamento` (põe no ar), `GET /<modulo>/professor/material` (o gabarito que o guia mostra) e as do preparo (seção 12.2). Para cada rota, sem exceção:

- **Papéis:** `@UseGuards(OidcGuard, RolesGuard)` e `@Roles` com os grupos de `auth/claims.ts` (`"estudante"`; `"professor", ...GESTORES`); seis papéis: `estudante · professor · gestor_escola · gestor_regional · gestor_contrato · admin`.
- **Funil de acesso:** estudante → `exigirMissaoLiberada` (403 `missao-nao-liberada`, ADR-69) → atividade em andamento (403 `atividade-nao-preparada`, ADR-130) → a sessão da (atividade, rodada) do gate; professor → turma que ele leciona (turma alheia é 404, nunca 403).
- **Corpo e resposta em Zod, escritos inline no PRD** — cada campo com tipo e limite —, e a saída do estudante como allowlist (o que não desce antes da hora: gabarito, acervo, regra). Nenhum `*Schema` ou `*Dto` citado sem a definição: o PRD da exp01ef1b (07/10/2026) mandava validar com `ParametrosDoPreparoExp01ef1bSchema` e não dizia o que ele tinha.
- **Erros:** tabela `código → status`, o `CodigoErro` e o `STATUS` de `<modulo>/erros.ts` (resposta com `codigo` e `mensagem`), na voz de cada zona (ficção para o estudante, plataforma para o professor).
- **Idempotência e lock:** o que o segundo clique devolve; o lock por estudante na sessão e o da turma — exclusivo para gate, zerar, homologar e pôr no ar; compartilhado para as jogadas que marcam evidência, que releem o gate e devolvem 409 `rodada-mudou` se o professor zerou no meio.
- **Rate limit:** `rateLimit` de `apps/api/src/comum/rate-limit.ts`, chave por usuário (nunca IP: a turma inteira sai pelo mesmo NAT da escola), teto por minuto com origem ou `[PROPOSTA …]`, 429 `muitas-requisicoes`.

Rotas de plataforma consumidas sem criar: `/progresso/:expId`, `/telemetry/batch`, `/salas/minhas`, `/evidencias/:expId/perguntas/:perguntaId` (Canal B), `/equipes/…`, `/podcast/:expId/…`. Missão não pendura rota em `/atividades` (o motor do Instanooria) nem em `/experiencias`.

## 12.2 IA no preparo
A IA só existe do lado do professor, antes da aula — salvo IA que responde ao estudante declarada na spec (molde `unoogpt`, quota do perfil `estudante`). Uma linha por chamada:
`| Chamada | Rota | Entrada (campos do recorte, delimitados como dado) | Saída (o Zod que o validar aplica — o mesmo da homologação) | Prompt | Modelo | Quota | Fallback por código | Moderação |`

- **Prompt:** em `apps/api/src/<modulo>/prompts.ts`, no servidor; nunca no bundle.
- **Modelo:** a família do `AiRequest.modelo` (`padrao` ou `longo`); o nome é o do contrato da base — `ia.modelo_padrao` para texto, `ia.modelo_imagem_padrao` para imagem — e o PRD não crava outro. Voz é do módulo de podcast (seção 15.2).
- **Quota:** `QuotaService.temSaldo` antes, débito no `aoUsarTokens` (inclusive as tentativas recusadas), perfil `professor` (ADR-105); o custo estimado por chamada com origem.
- **Fallback por código:** sem saldo → 429 `sem-saldo-de-ia`; falha → 503 `ia-indisponivel`, ou 200 com `usouIa: false` e o banco curado padrão quando a spec o tem; o que a tela do professor mostra em cada caso. 429 e 5xx do provedor já ganham nova tentativa dentro do `generateJson`; 4xx não.
- **Moderação:** `src/ai` não modera. A missão modera no domínio: o `validar` do `generateJson` (recusa e regenera com o motivo), `invariantes.ts` (termos proibidos e réguas de palavras, as mesmas na homologação), texto de pessoa delimitado no prompt, e texto de estudante, quando houver, filtrado antes de gravar.
- **Imagens em duas fases** (ADR-146, molde do Júri): `homologar` aprova os textos → `gerar-midia` gera aos poucos (poucas por chamada) → `…/pacotes/:pacoteId/imagens/:itemId/refazer` → `…/pacotes/:pacoteId/aprovar-imagens`; sem a segunda aprovação, `em-andamento` devolve 409 `imagens-nao-aprovadas`. Sem imagem, a tela tem a arte de reserva que a spec ou o design definem.
- **Cada ação do professor do §9 do one-pager é uma rota:** gerar o rascunho (`POST …/turmas/:turmaId/gerar-conteudo`, não persiste), regenerar um item, homologar (cria a atividade pronta; idempotente para o mesmo conteúdo), as imagens, pôr no ar, liberar etapa, zerar. Ação do §9 sem rota é decisão deixada para quem codifica.

# 13. Eventos, telemetria e analytics
Todo evento da tabela de eventos da spec (9.4) entra aqui com o **mesmo `verbo` e o mesmo `objeto`** — a conferência os procura literais.
Tabela `EVT-xxx` · `verbo` (sugerido `attempted|interacted|progressed|completed|scored`; não imposto pela api) · `objeto` (`namespace:slug`, estável) · quando dispara · `resultado` · `contexto` (objetos JSON; só número, booleano ou vocabulário fechado; nunca texto de menor, nome, e-mail) · caminho (analítico `track` · operacional rota do módulo · erro · vital · trace) · **onde é lido** (o que a professora vê: tabela `expNNefNb_*` + rota/tela do professor; o que só alimenta KPI de produto: `painel de produto (PostHog)`. Pub/Sub, `/telemetry/batch` e `telemetria_eventos` são transporte, nunca leitor; "aparece no dashboard" sem tabela nem painel nomeados é fantasia) · retenção · KPI que alimenta. **Não existe campo `dados`.** Volume por sessão (cabe em 50 eventos/10 s?) e o que é agregado no cliente. `experiencia.json#verbos` com o significado nesta missão + lista de objetos. Métricas proibidas (dwell no analítico, ranking). Versão do instrumento. Clarity recebe só `verbo:objeto`. Molde: `references/plataforma/exemplo-telemetria-exp06ef1b.md` (o `src/lib/telemetria.ts` do Júri: o voto e a alternativa escolhida não saem por `track`).

# 14. Pedagogia e conformidade
## 14.1 Matriz
Matriz habilidade BNCC — **exatamente as do bloco 11 da spec** (código, confirmado ou 🔵 a validar) → evidência observável → interação → dado gravado (as colunas da seção 11) → **régua inteira: Atingiu, Em processo e Não atingiu, por extenso** → canal (A, B, A + B) → no Canal B, remissão à pergunta e às alternativas no anexo (§12a) → onde o nível mora (`evidencias.status`). Competências socioemocionais do §2 do one-pager. Rastreabilidade curricular. Graus de medida.
## 14.2 Ficha de evidência — o que o servidor calcula
Uma linha por marcador, no formato da `FichaPedagogica` (`references/plataforma/evidencia-fichas-tipos.md`), que vai para `apps/api/src/evidencias/fichas/<expId>.ts` e para `fichas/index.ts`:
`| Habilidade | Marcador | Tipo | Pergunta | Regra | Nível | Grava na transação de | Critério para o professor |`

- **Tipo:** `acao` (a missão observa e diz o nível; vale a melhor marca) ou `multipla_escolha` (o nível sai do gabarito da pergunta, no servidor; vale a primeira resposta).
- **Pergunta:** o id, com remissão ao enunciado e às alternativas no anexo (§12a); o `status` de cada alternativa é o gabarito e nunca desce ao estudante.
- **Regra:** predicado sobre o que o servidor gravou, com o nome das colunas da seção 11 — `cadeia_tentativas = 1 → atingiu; 2–3 → em_processo; mais → nao_atingiu` (Júri). No Canal B, a regra é o gabarito.
- **Grava na transação de:** a rota e o latch em que `EvidenciasService.marcar(tx, …)` roda; o resolvedor (`registrarContexto` no `onModuleInit`) devolve `null` fora da (atividade, rodada) do gate. Toda rodada mede tudo de novo (ADR-145).
- **Critério para o professor:** o texto dos três níveis que o painel mostra (`criterios.atingiu`, `em_processo`, `nao_atingiu`; com dois marcadores, a `observacao` — "vale o melhor").
- **Régua que não vira predicado sobre dado gravado** — "cumpre ordenadamente a rotina", "demonstra compreensão" — é `[PROPOSTA — validar com PO: <o predicado sobre colunas da seção 11> · por quê · alternativa]`, e a coluna que falta entra na seção 11. No PRD da exp01ef1b (07/10/2026) uma habilidade era medida por «cumpre ordenadamente a rotina investigativa da E1 à E4», e nenhuma coluna guardava isso.

## 14.3 Guardrails e o que cada adulto vê
Gabarito (só no servidor). Guardrails de IA (8.1/8.2: geração restrita à preparação docente com curadoria humana obrigatória antes do consumo pelo estudante; IA nunca avalia formalmente o estudante; fallback para banco curado padrão quando a spec o tem) e éticos (8.3–8.6). Papel do erro. O que cada adulto vê (o estudante nunca vê o próprio nível; não há ranking).

# 15. Dependências, integrações e **pré-requisitos de plataforma**
## 15.1 Pré-requisitos de plataforma
Tabela própria e obrigatória quando a missão pede capacidade que a plataforma ainda não tem: capacidade · por que a mecânica precisa dela · arquivos a tocar (contrato da api, migration do CHECK, `ExpFrame`, teste, repasse nas rotas do hub) · componente de design system a criar · ADR necessária · o que acontece sem ela (degradação). Cada linha vira também item da seção 19 com dono `plataforma`, e a esteira marca o PRD 🟡 (`aprovado-com-pendencias-de-plataforma`). A tabela das capacidades, com o caminho de cada uma, está em `references/capacidades-plataforma.md`. Depois disso: seção do DS e componentes faltantes (com responsável e prazo) · `@unooria/design-system` na última versão publicada (não crave número) · SDK · módulos da api reutilizados (`evidencias`, `equipes`, `podcast`, `salas`) · IA (seção 12.2) · outras missões (contrato e fallback).
## 15.2 Inventário de conteúdo — obrigatório
Todos os IDs V1 do brief de assets (`dev/01b-brief-assets.md`) e todas as entradas do banco de conteúdo (`dev/01e-banco-conteudo.md`), um por linha, nenhum de fora:
`| ID | O que é | Telas | Destino | Caminho | Peso | Quem produz |`
Destino: bundle (< 2 MB, `apps/experiencias/<id>/public/…`) · bucket `-assets` (≥ 2 MB, `midia-externa.json`, ADR-63) · servidor (`conteudo.ts`, `fichas/<expId>.ts`) · gerado no preparo pela IA (o pacote) · catálogo ou guia do hub. O texto é referenciado pelo ID e pelo arquivo do banco, não copiado. A exp01ef1b tinha 29 IDs no brief, e o PRD de 07/10/2026 citava um.

**Podcast (ADR-150): não há mp3 no inventário.** O podcast é recurso da plataforma (`apps/api/src/podcast/`, tabela `podcast_roteiros`, rotas `/podcast/:expId/turmas/:turmaId`), e o áudio é sintetizado e guardado por ela. A missão registra uma `FonteDoPodcast` no `onModuleInit` (`PodcastService.registrarFonte`; molde `jornal-escola/podcast.ts` + `podcast-fonte.ts`) com: o roteiro do §11 em blocos de até 4.000 bytes; as **vagas do tema** — as falas que contam o que a turma viu na atividade, de 12 a 60 palavras, até 400 bytes, sem link, e-mail nem @ —; os falantes por timbre neutro e o pedido de voz. `POST …/falas-do-tema` devolve o rascunho das vagas sem gravar; a homologação da missão recebe as falas que o professor revisou (`falasDoTemaSchema(vagas)`) e as grava com `gravarFalasDoPodcast` na mesma transação; `POST …/gerar` sintetiza um trecho por chamada. O id da atividade é UUID (`podcast_roteiros.atividade_id`). No inventário entra o roteiro (Anexo §11), com destino `podcast.ts`. O PRD da exp01ef1b (07/10/2026) apontava um `aud-exp01ef1b-01.mp3` no bucket, que a plataforma não usa.

# 16. Arquitetura da solução (plano técnico)
Contexto da plataforma resumido (monorepo, hub + api + experiência estática, SDK/postMessage `PROTOCOL_VERSION`, tenancy com seis papéis, trancas catálogo → disponibilidade → liberação por turma → atividade em andamento, cinco caminhos de dado, sala por polling curto ADR-93/94, fuso único ADR-98/99). Diagrama C4 nível 1–2 (Mermaid). Alternativas consideradas e trade-offs. Decisões que exigem ADR nova (a próxima do contrato).

# 17. Plano de implementação — arquivos e convenções
Lista de **arquivos a criar/alterar com caminho completo**. Molde: o Júri — `apps/api/src/juri-estadual/` + `apps/experiencias/exp06ef1b/` (atividade, gate, rodada, ficha, equipe, podcast); `apps/api/src/a-selecao/` para zerar = rodada e para texto livre de menor (as reflexões); `apps/api/src/unoogpt/` para IA que responde ao estudante. O módulo da api: `vocabulario.ts`, `conteudo.ts`, `invariantes.ts`, `erros.ts`, `contrato-de-rotas.ts`, `prompts.ts`, `regras/` (puras: passos, evidência, painel), service com `comTenancy`, controllers por papel, `preparo.service.ts`, `podcast.ts` + `podcast-fonte.ts` quando há podcast, o module, `AGENTS.md` + `CLAUDE.md` e a linha na tabela de módulos de `apps/api/AGENTS.md`. A ficha em `apps/api/src/evidencias/fichas/<expId>.ts` + `fichas/index.ts`. Suítes `apps/api/tests/<modulo>-regras.spec.ts` (sem banco) e `<modulo>-postgres.spec.ts` (RLS isolando, CHECK × constante, latches, zerar, preparo com IA falsa). Na experiência, o que trocar primeiro no scaffold (porta, manifesto, seção do clone em `main.tsx`, eventos em `lib/telemetria.ts`, contrato em `lib/tipos.ts`, textos em `lib/textos.ts` — a fiação já vem pronta desde a ADR-106). Bibliotecas permitidas/proibidas; variáveis de ambiente; `AGENTS.md` + `CLAUDE.md` + `README.md` da pasta; LaTeX (`12-experiencias`, `13-api`, `08-modelo-de-dados`, `18-adr`).
## 17.1 Manifesto `public/experiencia.json`
Completo, com as chaves do contrato da base (`id`, `nome`, `versao`, `series`, `unidade`, `produto`, `capabilities`, `viewport`, `publico`, `permissoes`, `verbos`), no molde de `references/plataforma/exemplo-manifesto-exp06ef1b.md`. O `id` sai de `series[0]` + `unidade` (ADR-110: `6EF` + unidade 1 = `exp06ef1b`) e não se escolhe. **Se o id já está na tabela de experiências do contrato, a missão é atualização da existente:** a mesma pasta, o mesmo módulo da api (as rotas dele valem como estão), a mesma porta, versão acima da publicada, nunca `pnpm new:exp`, e na seção 19 `[ABERTO — dono: PO: substituir a existente ou outro código]`. Se o PO já decidiu (pedido ou parecer na sessão, com data), a seção 19 registra a decisão no lugar do marcador: `Decisão do PO (<pedido|parecer>, DD/MM/AAAA): substituir a existente, versão X.Y.Z` — e só a que está na sessão; decisão que você não encontra nos pedidos ou pareceres continua `[ABERTO — dono: PO: …]`. O PRD da exp01ef1b (07/10/2026) mandava `pnpm new:exp exp01ef1b` na porta 5186 e um módulo novo, e a plataforma já tem a exp01ef1b (O Que a Foto Conta, porta 5183, módulo `foto-conta`). Versão em três lugares (`experiencia.json`, `package.json`, `EXP_VERSION` + `versao.test.ts`); campo novo de manifesto entra também em `apps/hub/scripts/publicar-manifesto.mjs`. **Equipes não são chave do manifesto:** com o cenário de 2 a 4 por aparelho, a missão entra em `EXPERIENCIAS_COM_EQUIPE` e `EXPERIENCIAS_COM_ATIVIDADE` (`apps/api/src/equipes/regras.ts`) e em `FONTES` (`equipes/atividades.ts`), e o painel conta por computador (`mapaDeEquipes` + `colapsarEmUnidades`). Entrar nessas listas exige atualizar também `apps/api/tests/equipes-regras.spec.ts`, que lista as missões à mão — sem isso o teste da plataforma reprova.
## 17.2 Nascimento, porta, migration e seed
Comandos exatos: `pnpm worktree criar expNNefNb --fatia api/<mod>,hub/<rota>,exp/<id>` sobre `origin/dev-local`; `pnpm new:exp <id>` (só id novo); `pnpm turbo typecheck lint test build`; `node scripts/e2e/rodar.mjs estudante`. Porta: a próxima livre do contrato em `apps/hub/lib/experiencias-dev.ts` (e o teste dele), `--strictPort` no `dev` do `package.json`, `CORS_ORIGINS` em `.env.example` e no `docker-compose.dev.yml` (com o serviço da experiência), `docker-compose.yml`. Migration nova com o bloco manual (seção 11); nunca tocar `migrations/` existentes. Seed: o catálogo `experiencias` sai dos manifestos; a liberação de demo é o `expId` na turma "A" da série em `LIBERACOES_DE_DEMO` (`apps/api/prisma/catalogo-e-liberacoes.ts`). `midia-externa.json` se houver mídia ≥ 2 MB (ADR-63).
## 17.3 Hub do professor
| O quê | Arquivo | O que a missão acrescenta |
|---|---|---|
| Catálogo da trilha | `apps/hub/lib/entre-redes/catalogo.ts` | a constante `MISSAO_<NOME>` (`anoSlug`, `unidadeSlug`, `unidade`, `expId`, `titulo`, `resumo`, `status`, `ficha` com competência, duração, formato, atos e preparo, e `estudante` com título e chamada que não entregam a virada) e a entrada em `MISSOES_PUBLICADAS`; testes `catalogo.test.ts` e `missoes-do-estudante.test.ts` |
| Guia da aula | `apps/hub/lib/entre-redes/guias/<expId>.ts` + `guias/index.ts` | o `GuiaDaAula` como dado (objetivos, bncc com exatamente uma principal, antes, roteiro, debate, mediação, depois, cuidados, adaptações, dúvidas); missão nova nasce com guia |
| Ficha da missão | `apps/hub/app/(plataforma)/professor/entre-redes/[ano]/[unidade]/page.tsx` + `missao-<slug>.tsx` | o ramo `missao.expId === MISSAO_<NOME>.expId` (o `despachante-da-ficha.test.ts` reprova missão órfã) |
| Resultados e painel da aula | `…/[unidade]/resultados/page.tsx` + `resultados-<slug>.tsx`, `painel-da-aula-<slug>.tsx`, `zerar-turma-<slug>.tsx` | o ramo no despachante; o painel de habilidades é o genérico (`components/evidencias/`), não se refaz; com podcast, o tocador das falas |
| Guia com blocos vivos | `…/[unidade]/guia/page.tsx` | o `case` em `blocosDaMissao(expId)` quando o guia mostra conteúdo da atividade (o material com gabarito) |
| Nova atividade (preparo) | `…/[unidade]/atividades/nova/page.tsx` + `criar-<slug>.tsx`; `apps/hub/lib/entre-redes/atividades.ts` (`MISSOES_COM_ATIVIDADE`, `caminhoDoEmAndamento`); `apps/hub/lib/atividades-servidor.ts` | as telas `E0-PROF-*`; com podcast, as falas do tema que o professor revisa |
| Espelho do contrato | `apps/hub/lib/<modulo>-tipos.ts` + teste | os tipos que o hub lê da api, com teste que lê a api como texto |
| BFF | `apps/hub/app/api/plataforma/[...path]/route.ts` | o slug do módulo em `PREFIXOS_PERMITIDOS` (sem ele, 404 `bff-prefixo-recusado`), com o comentário de por que a tela é client-side |
| Rotas da missão | `apps/hub/lib/rotas-da-missao.ts` | nada: são derivadas do catálogo (`disponivel` com `expId`) e do guia registrado (ADR-100) |

## 17.4 O que NÃO fazer
Seção técnica, não vazia (a lista mínima está no prompt do redator).

# 18. Tarefas (decompostas e ordenadas)
`T-xxx` · descrição atômica · RFs cobertos · arquivos · dependências · `[P]` se paralelizável · **comando de verificação** · teste que a prova (`arquivo › caso`). Ordem: contratos → testes → implementação → docs.

# 19. Decisões (ADR) e pendências
## 19.1 ADR
Log ADR (título · status · contexto · decisão · alternativas · consequências); decisão nova é a próxima ADR do contrato.
## 19.2 Pendências
Marcadores `[NEEDS CLARIFICATION: <pergunta>, dono: <produto|design|dev|plataforma>]`, `[ABERTO — dono: …]` e 🔵 consolidados aqui, com dono e prazo. Pendência de dono **plataforma**, externo ou PO é humana, resolvida na codificação ou na validação, e a esteira marca o PRD 🟡; pendência de produto, design ou dev impede o PRD. **Divergências spec × plataforma** numa tabela própria, como registro — o corpo já seguiu a plataforma, então não é marcador: `| O que a spec ou o one-pager dizem | O que a plataforma tem (fonte) | O que o PRD seguiu | Dono |`, dono `produto`. As ressalvas dos pareceres não incorporadas (bloco 12 da spec) também entram como registro.
## 19.3 Decisões do agente a revisar
Toda `[PROPOSTA — validar com PO: …]` da spec, dos documentos de design e do handoff que o PRD recebe e que o PO ainda não respondeu, com o texto literal do marcador e a origem, mais as do próprio PRD: `| Proposta (literal) | Origem (arquivo › seção) | Onde o PRD a aplica |`. O marcador não some no caminho: a spec da exp01ef1b tinha cinco propostas ao PO, e o PRD de 07/10/2026 nenhuma.

# 20. Testes e Definition of Done
Estratégia (unit de regras puras, contrato, tenancy, Postgres com CHECK × constante, sanitizador com grep no `dist/`, smoke e2e por papel em `scripts/e2e/<papel>/NN-slug.mjs` com asserções que falham quando quebra) · **todo teste nomeado como `arquivo › caso`** (`apps/api/tests/<modulo>-postgres.spec.ts › zerar abre a rodada 2 sem apagar a 1`) — "testes de integração" não é teste · matriz de rastreabilidade RF → critério → teste (`arquivo › caso`) → tarefa · DoD do monorepo (typecheck+lint+test, e2e do papel, Zod nas fronteiras, tenancy, sem segredo no client, `AGENTS.md`, LaTeX + ADR) · evidências exigidas.

# 21. Plano de lançamento
Fases `dev-local → dev → hml → main` (ADR-101; PR `--base dev-local`; tag semver só em `main`), `status` no catálogo (`em-breve` → `disponivel`), disponibilidade no painel `/unooria` (a DoD exige provar que a experiência **desliga**, ADR-87/88), liberação por turma pela professora (ADR-69), critérios de avanço e rollback (`node apps/hub/scripts/publicar-manifesto.mjs <exp> --versao x.y.z`), comunicação a professores, playtest piloto. **Data só com origem:** prazo que aparece no contexto (briefing, calendário da rede, "para o 2º bimestre") não é data de lançamento homologada; a seção diz a fase e, se o one-pager ou a spec fixam uma data, cita a origem — senão, `[PROPOSTA — validar com PO: …]`.

# 22. Apêndices e changelog
**O anexo do conteúdo aprovado é da esteira.** Depois do PRD, ela cola `# Anexo — conteúdo aprovado pelo PO` com as seções §2, §9, §10, §11, §12 e §17 do one-pager, literais; o corpo remete a ele e não o reescreve.

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
- **Tabela de outra missão não se cita pelo nome completo** (o `exp06ef1b_…` do Júri): o PRD tem um prefixo de tabela só, e o gate de consistência acusa dois. O molde se cita pelo arquivo da base ou pelo módulo (`juri-estadual`, `a-selecao`).
- **Copy: cite todas as chaves, não reescreva o texto.** Cada story traz todas as chaves da tela e o lugar onde cada uma vive (seção 7); o texto final mora no sheet revisado, e o PRD não o parafraseia. O conteúdo pedagógico aprovado (perguntas e alternativas do Canal B, roteiro do podcast, roteiro do debate) não é copy de tela: está no anexo, e o corpo remete a ele.
- Todo RF P0 deve ter pelo menos um critério EARS **e** aparecer em pelo menos uma tarefa e um teste nomeado (`arquivo › caso`).
- O PRD referencia caminhos reais do monorepo (`apps/experiencias/expNNefNb/…`, `apps/api/src/<modulo>/…`) e os exemplares canônicos a imitar (`apps/api/src/juri-estadual/`, `apps/experiencias/exp06ef1b/`, `apps/experiencias/_template/`). O UnooTube está arquivado (`backup-unootube`, ADR-116), e a pasta da exp08ef4b é `apps/experiencias/exp08ef4b/` — não há `exp-08-manifesto-ia`.
- **Molde da base é só o que existe em `references/plataforma/`:** `exemplo-schema-exp.md`, `exemplo-migration-exp06ef1b.md`, `exemplo-manifesto-exp06ef1b.md`, `exemplo-telemetria-exp06ef1b.md`, `exemplo-juri-contrato-rotas.md`, `exemplo-juri-invariantes.md`, `exemplo-juri-agents.md`, `exemplo-a-selecao-contrato-rotas.md`, `evidencia-fichas-tipos.md`, `openapi-indice.md`. Este gabarito citava `exemplo-migration-exp-04.md` e `exemplo-telemetria-exp-08.md`, que a base nunca publicou.
- Todo número que não é medida da plataforma traz a origem entre parênteses ou é `[PROPOSTA — validar com PO: …]` (princípio 14).
- Tamanho: resumo executivo ≤ 1 página; corpo completo sem limite artificial, mas sem repetir o que outra seção já disse — referenciar por número de seção.

## D. Anti-padrões que o gabarito bloqueia

| Anti-padrão | Bloqueio no gabarito |
|---|---|
| Linguagem vaga ("rápido", "intuitivo") | RF só com EARS/Gherkin; RNF só com número + origem + método |
| "Como" dentro do requisito | Seção 8 declara necessidade; mecanismo vai para 16–18 |
| Métricas de vaidade | KPI exige pergunta, decisão, baseline com origem e EVT vinculado; alvo e prazo só com origem |
| Escopo que cresce na mão do agente | Seções 3 e 17.4 ("O que NÃO fazer") obrigatórias e não vazias |
| Lacuna resolvida por adivinhação | `[NEEDS CLARIFICATION]` ou `[PROPOSTA …]`, consolidados na seção 19 |
| Proposta do agente que some no caminho | Seção 19.3 com o marcador literal e a origem |
| Story que agrupa telas ou omite a copy | Uma story por tela, com todas as chaves e onde cada uma vive |
| O mesmo estado com três nomes | Vocabulário único da seção 6, igual ao CHECK |
| Schema citado sem definição | Zod inline na seção 12.1 |
| Régua que o servidor não consegue calcular | Predicado sobre colunas na seção 14.2, ou `[PROPOSTA …]` |
| "Parece pronto" | Toda tarefa com comando de verificação e teste `arquivo › caso`; DoD exige evidência |
| Tudo P0 | P0 restrito ao que a rubrica exige (🔒) e à descoberta central |
| Sem rastreabilidade | IDs estáveis + matriz na seção 20 |
| PRD estático | Frontmatter com versão + changelog na seção 22; o status é da esteira |

## E. Fontes

Cagan — *How to Write a Good PRD* (svpg.com) · Thoughtworks — *Spec-driven development* (2025) · GitHub Spec Kit `spec-driven.md` · AWS Kiro — Specs e requirements (EARS) · Anthropic — *Claude Code best practices* e *Effective context engineering for AI agents* · agents.md · Pragmatic Engineer — *RFCs and Design Docs* · *Design Docs at Google* · Mavin — EARS · Cucumber — Gherkin reference · adr.github.io · c4model.com · Agile Alliance — INVEST · Scrum Guide — Definition of Done · Katalon — Requirements Traceability Matrix · Moesif — Contract-first API · Fora Soft — NFR checklist (14 categorias) · Centercode — 5 common PRD mistakes · Augment Code — Spec-driven development · Amazon Working Backwards — PR/FAQ · Lenny's Newsletter — templates favoritos · Atlassian — PRD template · LGPD art. 14 (dados de crianças e adolescentes).
