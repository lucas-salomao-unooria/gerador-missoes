# Perguntas de produto — o que a missão precisa declarar para ser medida

Uma **pergunta de produto** é uma pergunta que, respondida, muda uma decisão nossa: o que
priorizar, o que cortar, o que encurtar, com quem conversar. Ela tem três partes — **a
pergunta, a decisão que ela dispara e o corte**. Se não dispara decisão, é curiosidade.

Três coisas diferentes eram tratadas como uma só, e é o que produzia KPI que ninguém usa:

| Camada | Responde | Quem lê | Onde se vê |
|---|---|---|---|
| **Log e observabilidade** | o sistema está de pé, rápido e sem erro? | engenharia | Google Cloud |
| **Telemetria de uso** | o que as pessoas fizeram, em que ordem, onde pararam? | ninguém "olha": é matéria-prima | `expNNefNb_*` e `telemetria_eventos` |
| **Produto** | a missão está funcionando como produto? | PO e engenharia | `painel de produto (PostHog)` — **ainda não existe na plataforma** (ver o fim deste documento) |
| **Relatório pedagógico** | o que esta turma entendeu? | só o professor | tela de resultados |

**A missão declara as duas últimas, e elas não se misturam.** Um número que serve às duas ao
mesmo tempo é coincidência, não desenho.

## As perguntas transversais — a lista do PO (23/09/2026)

São as 21 perguntas de observabilidade de produto definidas pelo PO. Valem igual para qualquer
missão, e por isso **não se reinventam**: um KPI que herda `T7` usa a pergunta de `T7`, com
estas palavras, e os sinais que o catálogo abaixo diz que a respondem — nunca um evento próprio
da mecânica escolhido por proximidade.

Cada pergunta tem **um dono de dado**, e é isso que decide quem a declara:

- **`missao`** — a missão responde, emitindo os eventos universais no bundle (`EVT-U*`) ou
  gravando os sinais do professor nas tabelas do próprio módulo (`EVT-P*`). **Toda missão herda
  todas as de dono `missao`**; `T21` só se a IA responde ao estudante em tempo real.
- **`plataforma`** — só o hub ou a api respondem (login, cadastro, abertura de missão no
  catálogo). A missão **não** as declara: listá-las no 9f é prometer um número que ela não tem
  como produzir. Ficam na lista de pendências de plataforma.

| ID | Pergunta (do PO) | Decisão que dispara | Corte | Dono | Sinais |
|---|---|---|---|---|---|
| `T1` | De X professores vinculados à rede, quantos entraram na plataforma? | `[PROPOSTA — validar com PO]` <50% → problema de ativação: conversa com a rede antes de nova escola | rede · escola | plataforma | — |
| `T2` | De X alunos de uma turma, quantos entraram na plataforma? | `[PROPOSTA — validar com PO]` <70% → acesso do estudante trava: rever credencial e primeiro acesso | turma · escola · rede | plataforma | — |
| `T3` | De X gestores (escola e rede) vinculados, quantos entraram no dashboard nos últimos X meses? | `[PROPOSTA — validar com PO]` <30% → o dashboard não serve ao gestor: entrevistar antes de evoluir | escola · rede | plataforma | — |
| `T4` | De X gestores vinculados, quantos cadastraram usuários (professor ou aluno), manualmente ou por importação? | `[PROPOSTA — validar com PO]` cadastro concentrado no suporte → simplificar a importação | escola · rede | plataforma | — |
| `T5` | Quais missões o professor mais abre? | `[PROPOSTA — validar com PO]` missão pouco aberta → rever a vitrine do catálogo, não a missão | missao · serie | plataforma | — |
| `T6` | De cada X professores que abriram uma missão no painel, quantos liberaram para a turma? | Conversão baixa → a tela de preparo gera insegurança: simplificar ou reforçar o guia | missao · serie | plataforma | — |
| `T7` | De cada X turmas liberadas, quantas chegam ao fim da missão? | Menos da metade → longa demais ou travando: entra na fila antes de qualquer feature nova | missao · serie | missao | `EVT-U01`, `EVT-U03` |
| `T8` | Comparando todas as missões, em que etapa da jornada (abertura, ação central, reflexão, resultado) os alunos mais abandonam? | `[PROPOSTA — validar com PO]` abandono concentrado numa etapa → redesenhar aquela etapa antes das outras | etapa · missao · serie | missao | `EVT-U02` |
| `T9` | Que proporção dos alunos de uma turma inicia a missão depois que o professor libera? | `[PROPOSTA — validar com PO]` <70% → a entrada trava: rever o pareamento e o aviso de liberação | turma · missao · serie | missao | `EVT-U01` |
| `T10` | Na etapa em que o aluno travou (T8), ele travou por erro técnico ou ficou inativo? | Aula perdida por falha silenciosa é prioridade acima de feature; inatividade → rever a instrução da etapa | missao · serie · etapa | missao | `EVT-U04`, `EVT-U05` |
| `T11` | Quanto tempo o aluno leva entre receber o desafio e avançar para as próximas etapas, da segunda até a final? | Passa do teto de tempo em tela → encurtar a etapa mais longa ou dividir a missão | missao · serie | missao | `EVT-U02` |
| `T12` | Dentro do tempo total, quanto é interação ativa e quanto é espera (resposta da IA, ou não entender o que fazer)? | `[PROPOSTA — validar com PO]` espera >30% do tempo → atacar a maior fonte de espera | missao · etapa | missao | `EVT-U02`, `EVT-U04`; `EVT-U06` **só se a IA responde ao estudante** (spec herda `T21`) — sem isso, a espera medida é só a de não entender o que fazer |
| `T13` | Dos alunos que iniciam ou completam uma missão, quantos iniciam ou completam as demais liberadas no mesmo ano? | `[PROPOSTA — validar com PO]` retorno baixo → a trilha não se sustenta: rever a sequência | aluno · turma · escola · rede | plataforma | — |
| `T14` | O professor que inicia a configuração da missão consegue terminar, ou trava no meio? | `[PROPOSTA — validar com PO]` <80% termina → simplificar o preparo | missao · serie | missao | `EVT-P01`, `EVT-P03` |
| `T15` | De X professores que acessaram a missão, quantos iniciaram a customização? | `[PROPOSTA — validar com PO]` <50% → a customização não é percebida: rever a entrada do preparo | missao · serie | missao | `EVT-P01` |
| `T16` | Quantas vezes, em média, o professor rejeita a proposta de tema da IA antes de aprovar? | `[PROPOSTA — validar com PO]` >2 rejeições → o prompt de geração erra o recorte: rever antes de escalar | missao · disciplina | missao | `EVT-P02`, `EVT-P03` |
| `T17` | O professor volta para ver o resultado da turma depois da aula? | Não volta → o relatório não entrega valor: avisar por e-mail, depois redesenhar | escola | missao | `EVT-P04` |
| `T18` | De professores que liberaram uma missão, quantos configuram uma segunda (ou mais) no mesmo ano? | Retorno baixo → produto "de uma vez": entender o que faltou antes de vender mais | professor · escola · rede | plataforma | — |
| `T19` | Quantas aulas leva para o professor aplicar a missão do começo ao fim? | Passa do número de aulas declarado → encurtar ou dividir | missao · serie | missao | `EVT-P05` |
| `T20` | Quanto custa de IA por missão customizada pelo professor? | Acima do teto → otimizar antes de escalar para mais redes | missao · rede | missao | `EVT-P02` |
| `T21` | Quanto custa por interação nas missões em que a IA responde ao aluno em tempo real? | Acima do teto → otimizar o turno antes de escalar | missao · rede | missao (só se a IA responde ao estudante) | `EVT-U06`, `EVT-P06` |

## O catálogo de sinais universais

Os sinais têm **o mesmo id, o mesmo verbo e o mesmo objeto em toda missão** — é o que permite
comparar missões entre si (`T8` é, literalmente, "comparando todas as missões"). Um id do
catálogo nunca é reaproveitado para um evento próprio da mecânica: os eventos da missão são
`EVT-001`, `EVT-002`…, e os universais são estes.

**Eventos do estudante (`EVT-U*`)** — emitidos no bundle com `track(verbo, objeto, { resultado, contexto })`
da SDK. A SDK já acrescenta sozinha `ts`, `estudanteId`, `escolaId`, `expId`, `expVersion` e
`sessaoId`; **não** acrescenta etapa nem turma, por isso a etapa vai em `contexto` e a turma se
obtém pela matrícula.

| Sinal | Verbo | Objeto | Quando dispara | `resultado` | `contexto` | Responde |
|---|---|---|---|---|---|---|
| `EVT-U01` | `attempted` | `missao:iniciar` | Ao renderizar a primeira tela do estudante — também na reentrada | `{"retomada": false}` | `{"etapa": "E1"}` | T7, T9 |
| `EVT-U02` | `progressed` | `etapa:entrar` | Ao entrar em cada etapa E1…E6 | `{"etapa": "E2"}` | `{"pedagogical_role": "core_action"}` | T8, T11, T12 |
| `EVT-U03` | `completed` | o `expId` da missão | Automático, ao chamar `concluir()` da SDK — a missão **tem** de chamá-lo | o que a missão passa a `concluir()` | — | T7 |
| `EVT-U04` | `interacted` | `aviso:inatividade` | Ao exibir o aviso de inatividade da etapa | `{"segundos_sem_acao": 90}` | `{"etapa": "E2"}` | T10, T12 |
| `EVT-U05` | `attempted` | `erro:exibir` | Ao exibir um estado de erro diegético (sem sinal, sessão expirada, conteúdo que não carregou, IA sem saldo) | `{"codigo": "sem-sinal"}` | `{"etapa": "E2"}` | T10 |
| `EVT-U06` | `attempted` | `ia:responder` | A cada resposta da IA ao estudante — só em missão em que a IA responde em tempo real | `{"latencia_ms": 2300, "sucesso": true}` | `{"etapa": "E3"}` | T12, T21 |

**Sinais do professor (`EVT-P*`)** — as telas do professor vivem no hub, que não tem `track`.
Esses sinais são **gravados pela rota do próprio módulo da missão**, em colunas das tabelas dela;
o "evento" é a escrita da coluna, e o leitor é a própria tabela.

| Sinal | Objeto | Quando grava | Onde fica | Responde |
|---|---|---|---|---|
| `EVT-P01` | `preparo:iniciar` | Na primeira chamada de qualquer rota do preparo da turma | `<modulo>_conteudo_turma.preparo_iniciado_em` | T14, T15 |
| `EVT-P02` | `conteudo:gerar` | A cada `POST …/gerar-conteudo`, **inclusive rascunho não aprovado** | `<modulo>_conteudo_turma.geracoes` (+1) e `tokens_usados` (soma) | T16, T20 |
| `EVT-P03` | `conteudo:homologar` | Ao homologar o conteúdo | `<modulo>_conteudo_turma.aprovado_em` e `aprovado_por` | T14, T16 |
| `EVT-P04` | `painel:ver` | A cada `GET …/painel` do professor | `<modulo>_conteudo_turma.painel_visto_em` (primeira vez) e `painel_vistas` (+1) | T17 |
| `EVT-P05` | `gate:liberar` | A cada etapa que o professor libera no gate — linha nova, nunca sobrescrita | `<modulo>_gates_historico (turma_id, etapa, liberada_em)` | T19 |
| `EVT-P06` | `ia:consumir` | A cada chamada de IA feita para o estudante | `<modulo>_sessoes.tokens_gastos` (soma) e `chamadas_ia` (+1) | T21 |

Na tabela de eventos do PRD e do handoff, cada sinal herdado aparece **com o id do catálogo**,
o verbo e o objeto acima, e na coluna "Onde é lido" o leitor: o `painel de produto (PostHog)`
para os `EVT-U*`, a tabela do módulo para os `EVT-P*`.

```json
{
  "transversais": {
    "T1": {"dono": "plataforma", "sinais": []},
    "T2": {"dono": "plataforma", "sinais": []},
    "T3": {"dono": "plataforma", "sinais": []},
    "T4": {"dono": "plataforma", "sinais": []},
    "T5": {"dono": "plataforma", "sinais": []},
    "T6": {"dono": "plataforma", "sinais": []},
    "T7": {"dono": "missao", "sinais": ["EVT-U01", "EVT-U03"]},
    "T8": {"dono": "missao", "sinais": ["EVT-U02"]},
    "T9": {"dono": "missao", "sinais": ["EVT-U01"]},
    "T10": {"dono": "missao", "sinais": ["EVT-U04", "EVT-U05"]},
    "T11": {"dono": "missao", "sinais": ["EVT-U02"]},
    "T12": {"dono": "missao", "sinais": ["EVT-U02", "EVT-U04", "EVT-U06"]},
    "T13": {"dono": "plataforma", "sinais": []},
    "T14": {"dono": "missao", "sinais": ["EVT-P01", "EVT-P03"]},
    "T15": {"dono": "missao", "sinais": ["EVT-P01"]},
    "T16": {"dono": "missao", "sinais": ["EVT-P02", "EVT-P03"]},
    "T17": {"dono": "missao", "sinais": ["EVT-P04"]},
    "T18": {"dono": "plataforma", "sinais": []},
    "T19": {"dono": "missao", "sinais": ["EVT-P05"]},
    "T20": {"dono": "missao", "sinais": ["EVT-P02"]},
    "T21": {"dono": "missao", "sinais": ["EVT-U06", "EVT-P06"], "so_se": "ia_responde_estudante"}
  },
  "sinais": {
    "EVT-U01": {"verbo": "attempted", "objeto": "missao:iniciar"},
    "EVT-U02": {"verbo": "progressed", "objeto": "etapa:entrar"},
    "EVT-U03": {"verbo": "completed", "objeto": "<expId>"},
    "EVT-U04": {"verbo": "interacted", "objeto": "aviso:inatividade"},
    "EVT-U05": {"verbo": "attempted", "objeto": "erro:exibir"},
    "EVT-U06": {"verbo": "attempted", "objeto": "ia:responder", "so_se": "ia_responde_estudante"},
    "EVT-P01": {"objeto": "preparo:iniciar"},
    "EVT-P02": {"objeto": "conteudo:gerar"},
    "EVT-P03": {"objeto": "conteudo:homologar"},
    "EVT-P04": {"objeto": "painel:ver"},
    "EVT-P05": {"objeto": "gate:liberar"},
    "EVT-P06": {"objeto": "ia:consumir", "so_se": "ia_responde_estudante"}
  }
}
```

## Vocabulário fechado

**Corte:** `rede` · `escola` · `missao` · `serie` · `turma` · `professor` · `etapa` · `aluno` · `disciplina`.

**Papel pedagógico da tela** (`pedagogical_role`), derivado da etapa: E1 Desafiar → `intro` ·
E2 Navegar e E3 Decidir → `core_action` · E4 Resultado/Aha → `result` · E5 Explicar e E6
Refletir → `reflection`. É o que `EVT-U02` leva em `contexto`, e é o que permite a `T8`
comparar a mesma fase em missões de mecânicas diferentes. As telas do professor (`E0-PROF-*`)
não emitem `EVT-U02`.

## Baseline honesto

Um número só é baseline se alguém o mediu. Escreva **o número com a origem entre parênteses**
(`45% (playtest de 12/08, n=23)`) ou o literal **`sem baseline — primeira medição`**.

`0%`, `—` e `N/A` são **proibidos**: não são medida, são espaço em branco vestido de número, e
um alvo calculado sobre eles é opinião com aparência de meta. Nas primeiras 14 execuções, 20
dos 49 KPIs tinham baseline `0%`.

## O que a missão declara

Cada missão herda as transversais de dono `missao` — e, por isso, **emite todos os sinais delas**
— e acrescenta **exatamente 5 perguntas próprias**, que dependem da mecânica. A regra é a mesma:
pergunta, decisão, corte — e um evento que a responda.

As transversais não precisam de uma linha de KPI cada uma no PRD: elas são lidas no painel de
produto **comparando missões**, e o que a missão deve a elas é o sinal instrumentado. Se o PRD
escrever um KPI para uma transversal, ele usa a pergunta dela e só os sinais do catálogo.

Quem decide quais perguntas importam é o **PO**. Quando o briefing não as traz, o agente
propõe a partir da decisão central da missão e marca `[PROPOSTA — validar com PO]`: proposta
não bloqueia, mas fica visível para quem decide.

## O que NUNCA é medido

Nome, e-mail, CPF, matrícula. Qualquer texto que a criança escreva — reflexão, mensagem,
justificativa, termo de busca: dele sai a **medida** (`respondeu: true`), nunca o conteúdo. E
as respostas do check-in de bem-estar, que são questionário de saúde mental.

## O que é da plataforma (plataforma-unooria em `085fc57`, 23/09/2026)

Estado de cada pergunta de dono `plataforma`, e do que as de dono `missao` ainda dependem fora
dela. Nada disso a missão resolve; o PRD cita como pendência de plataforma (🟡), nunca como
lacuna da missão.

| Pergunta ou dependência | O que já existe | O que falta |
|---|---|---|
| T1, T2 — quem entrou | só o **primeiro acesso** (`users.senha_definida_em`); o panorama do gestor conta quem nunca entrou | registro de login ou de último acesso — hoje o login não grava nada |
| T3 — gestor no dashboard | nada | registro de acesso ao dashboard |
| T4 — cadastro de usuários | `users.created_at` | quem cadastrou, e se foi manual ou importação (não há registro de lote) |
| T5, T6 — professor abriu a missão | numerador de T6: `liberacoes` (`liberada_por`, `liberada_em`) | registro de "professor abriu a missão no painel" — hoje só o Clarity vê, por rota |
| T13 — demais missões do ano | `progresso` (`__conclusao.em`), `concluido_em` das tabelas de cada missão, `liberacoes` | só a consulta: o dado existe |
| T18 — segunda missão no ano | `liberacoes.liberada_por` e `liberada_em` | só a consulta: o dado existe (reabrir não guarda histórico) |
| Painel de produto | **não existe**: PostHog tem zero ocorrências no código; só o Clarity está instalado (dev e hml), e ele recebe `verbo:objeto` sem a carga útil | instalar o painel e ler `telemetria_eventos`, que hoje **ninguém lê** |
| Turma nos eventos | `telemetria_eventos` tem `escola_id` e `estudante_id` | `turma_id` — hoje a turma sai por JOIN com `matriculas`, que erra quando o aluno troca de turma |
| Erros contáveis (T10) | erro de JavaScript vai para o log (`/observabilidade/erros-cliente`) | "sessão expirada" e "missão não liberada" não são registrados em lugar contável — por isso a missão emite `EVT-U05` |
| Custo em dinheiro (T20, T21) | tokens: `ia_uso_diario` por usuário e dia, e colunas `tokens_*` em algumas missões | custo em R$ por modelo, e atribuição da chamada à missão |
