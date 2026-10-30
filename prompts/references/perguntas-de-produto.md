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

## As perguntas transversais — a lista do PO (revisada em 24/09/2026)

São as 21 perguntas de observabilidade de produto definidas pelo PO, com a pergunta, a decisão,
o grupo de missão, o pilar e o corte **nas palavras dele**. Valem igual para qualquer missão do
grupo, e por isso **não se reinventam**: um KPI que herda `T7` usa a pergunta e a decisão de
`T7`, e os sinais que o catálogo abaixo diz que a respondem — nunca um evento próprio da mecânica
escolhido por proximidade.

Cada pergunta tem **um dono de dado**, e é isso que decide quem a declara:

- **`missao`** — a missão responde, emitindo os eventos universais no bundle (`EVT-U*`) ou
  gravando os sinais do professor nas tabelas do próprio módulo (`EVT-P*`).
- **`plataforma`** — só o hub ou a api respondem (login, cadastro, abertura de missão no
  catálogo). A missão **não** as declara: listá-las no 9f é prometer um número que ela não tem
  como produzir. Ficam na lista de pendências de plataforma.

E um **grupo de missão**, que decide quais missões herdam a pergunta:

- **universal** — toda missão.
- **customização de tema (IA)** — só a missão em que o professor customiza o tema com a IA
  (`gerar-conteudo` + homologação no preparo): `T15`, `T16`, `T20`. Na `T14`, que é universal, é
  este grupo que traz a etapa de aprovação da IA para dentro da configuração.
- **IA conversacional em tempo real** — só a missão em que a IA responde ao aluno (tipo UnoGPT):
  `T21`, e a parte "espera por resposta da IA" da `T12`.

Os **pilares** agrupam as perguntas no painel: adoção do professor, adoção do aluno, adoção do
gestor, funil, custo e qualidade de IA.

| ID | Pergunta (do PO) | Grupo de missão | Pilar | Decisão que dispara (do PO) | Corte | Dono | Sinais |
|---|---|---|---|---|---|---|---|
| `T1` | De X professores vinculados à rede, quantos entraram na plataforma? | universal | adoção do professor | Entrada baixa mesmo com acesso liberado aciona conversa com o gestor da rede antes de investir em melhoria de conteúdo. | rede · escola | plataforma | — |
| `T2` | De X alunos de uma turma, quantos entraram na plataforma? | universal | adoção do aluno | Separa problema de acesso (login, dispositivo, senha) de problema de engajamento com a missão. | turma · escola · rede | plataforma | — |
| `T3` | De X gestores (escola e rede) vinculados, quantos entraram no dashboard nos últimos X meses? | universal | adoção do gestor | Se o gestor não entra, o relatório não está gerando valor pra ele. É risco de renovação, não só de produto. | escola · rede | plataforma | — |
| `T4` | De X gestores (escola e rede) vinculados, quantos realizaram o cadastro de usuários (professor e/ou aluno), seja manual ou via importação? | universal | adoção do gestor (onboarding) | Se o cadastro trava aqui, nada a jusante (professor, aluno, missão) sequer começa a existir na plataforma. É o primeiro ponto de funil do produto inteiro: cadastro baixo é prioridade de correção antes de qualquer outra métrica fazer sentido. | escola · rede | plataforma | — |
| `T5` | Quais missões o professor mais abre? | universal | funil | Missão nunca aberta tem problema de descoberta ou de nome na plataforma. Investigar antes de criar missão nova. | missao · serie | plataforma | — |
| `T6` | De cada X professores que abriram uma missão no painel do professor, quantos liberaram pra turma? | universal | adoção do professor · funil | Conversão baixa aponta pra atrito ou insegurança na tela de preparação. Simplificar antes de mexer em conteúdo. | missao · serie | plataforma | — |
| `T7` | De cada X turmas liberadas, quantas chegam ao fim da missão? | universal | adoção do aluno · funil | Se a conclusão ficar abaixo de 50%, entra na fila de investigação antes de qualquer feature nova. | missao · serie | missao | `EVT-U01`, `EVT-U03` |
| `T8` | Comparando entre todas as missões, em que etapa da jornada (abertura, ação central, resultado, explicação) os alunos mais abandonam? | universal | funil | Etapa com abandono desproporcional em várias missões ao mesmo tempo é sinal estrutural. Prioridade de redesenho transversal, não conserto pontual. | etapa · missao · serie | missao | `EVT-U02` |
| `T9` | Que proporção dos alunos de uma turma inicia a missão depois que o professor libera? | universal | adoção do aluno | Participação consistentemente baixa aponta pra problema de acesso (laboratório, dispositivo), não de desinteresse. Investigar antes de mudar a missão. | turma · missao · serie | missao | `EVT-U01` |
| `T10` | Na etapa em que o aluno travou (T8), ele travou por erro técnico ou simplesmente ficou inativo? | universal | funil | Abandono que coincide com erro técnico registrado é prioridade de bug, não de redesign. Sem erro, entra na fila de investigação de UX. | missao · serie · etapa | missao | `EVT-U04`, `EVT-U05` |
| `T11` | Quanto tempo o aluno leva entre receber o desafio da missão e avançar pras próximas etapas, da segunda etapa até a etapa final? | universal | funil | Tempo muito curto sugere que pulou sem entender a proposta; tempo muito longo sugere confusão. Os dois pedem revisão de clareza do texto. É aproximação, não medida direta de compreensão. | missao · serie | missao | `EVT-U02` |
| `T12` | Dentro do tempo total da missão, quanto é interação ativa do aluno e quanto é espera (por resposta da IA ou por não entender o que deve ser feito)? | universal na métrica; a leitura de causa muda por grupo — "espera por resposta da IA" só em IA conversacional em tempo real | funil · custo | Espera concentrada logo após uma ação do aluno é latência: resolve com loading melhor ou troca de modelo. Espera distribuída sem padrão é desengajamento ou instrução confusa: resolve redesenhando a tela. Fora da IA conversacional, espera alta tende a ser confusão sobre o que fazer, não latência de IA. | missao · etapa | missao | `EVT-U02`, `EVT-U04`; `EVT-U06` **só em IA conversacional** (spec herda `T21`) |
| `T13` | Dos alunos que iniciam e/ou completam uma missão, quantos iniciam e/ou completam as demais liberadas no mesmo ano? | universal | adoção do aluno (retenção) | Queda forte da primeira pras próximas indica engajamento por novidade, não interesse sustentado. A sequência de missões ao longo do ano precisa reforçar valor, não só entregar bem na estreia. | aluno · turma · escola · rede | plataforma | — |
| `T14` | O professor que inicia a configuração da missão consegue terminar, ou trava no meio? | universal; a complexidade varia — sem customização de tema a configuração é turma e data, com customização entra a aprovação da IA | adoção do professor | Se muitos iniciam e não terminam, a configuração está complexa demais. Encurtar ou pré-preencher. | missao · serie | missao | `EVT-P01`, `EVT-P03` **com customização de tema**; sem ela, o fim da configuração é a liberação da turma (`liberacoes.liberada_em`, plataforma) |
| `T15` | De X professores que acessaram a missão, quantos iniciaram a customização? | customização de tema (IA) | adoção do professor | Separa quem nem chega a considerar customizar (problema de descoberta da funcionalidade ou de valor percebido) de quem começa e desiste (fricção na tela, coberto pela T14). Pouca gente iniciando aponta pra problema antes da tela. | missao · serie | missao | `EVT-P01` |
| `T16` | Quantas vezes, em média, o professor rejeita a proposta de tema da IA antes de aprovar? | customização de tema (IA) | adoção do professor · qualidade de IA | Rejeição alta é sinal de que a qualidade da primeira geração da IA não está boa o suficiente. Prioridade de ajuste no motor de geração, não na tela. | missao · disciplina | missao | `EVT-P02`, `EVT-P03` |
| `T17` | O professor volta pra ver o resultado da turma depois da aula? | universal | adoção do professor | Se não volta, o relatório não está entregando valor. Primeiro teste é notificação por e-mail. Se mesmo assim não voltar, repensar o relatório do zero. | escola | missao | `EVT-P04` |
| `T18` | De professores que liberaram uma missão, quantos configuram uma segunda (ou mais) dentro do mesmo ano? | universal | adoção do professor (retenção) | Recorrência baixa mesmo com liberação alta indica que a primeira experiência não convenceu. Pode ser conteúdo, esforço de configuração ou falta de missão relevante pra série dele. | professor · escola · rede | plataforma | — |
| `T19` | Quantas aulas leva para o professor aplicar a missão do começo ao fim? | universal | adoção do professor · funil | Se o número de aulas necessárias passar do que o professor consegue encaixar no planejamento dele, a missão perde espaço na grade antes mesmo de começar. Acima do esperado entra na fila pra encurtar ou dividir em partes menores. | missao · serie | missao | `EVT-P05` |
| `T20` | Quanto custa de IA por missão customizada pelo professor? | customização de tema (IA) | custo | Se o custo por missão customizada passar do teto definido, otimizar o motor de geração antes de escalar customização pra mais redes. | missao · rede | missao | `EVT-P02` |
| `T21` | Quanto custa por interação nas missões onde a IA responde ao aluno em tempo real (tipo UnoGPT)? | IA conversacional em tempo real | custo | Se o custo por mensagem nas missões de conversa livre passar do teto definido, otimizar antes de escalar pra mais redes. | missao · rede | missao | `EVT-U06`, `EVT-P06` |

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
| `EVT-U02` | `progressed` | `etapa:entrar` | Ao entrar em cada etapa E1…E5 | `{"etapa": "E2"}` | `{"pedagogical_role": "core_action"}` | T8, T11, T12 |
| `EVT-U03` | `completed` | o `expId` da missão | Automático, ao chamar `concluir()` da SDK — a missão **tem** de chamá-lo | o que a missão passa a `concluir()` | — | T7 |
| `EVT-U04` | `interacted` | `aviso:inatividade` | Ao exibir o aviso de inatividade da etapa | `{"segundos_sem_acao": 90}` | `{"etapa": "E2"}` | T10, T12 |
| `EVT-U05` | `attempted` | `erro:exibir` | Ao exibir um estado de erro diegético (sem sinal, sessão expirada, conteúdo que não carregou, IA sem saldo) | `{"codigo": "sem-sinal"}` | `{"etapa": "E2"}` | T10 |
| `EVT-U06` | `attempted` | `ia:responder` | A cada resposta da IA ao estudante — só em missão em que a IA responde em tempo real | `{"latencia_ms": 2300, "sucesso": true}` | `{"etapa": "E3"}` | T12, T21 |

**Sinais do professor (`EVT-P*`)** — as telas do professor vivem no hub, que não tem `track`.
Esses sinais são **gravados pela rota do próprio módulo da missão**, em colunas das tabelas dela;
o "evento" é a escrita da coluna, e o leitor é a própria tabela. `EVT-P01`–`EVT-P03` só existem
na missão com customização de tema por IA; `EVT-P06`, só na IA conversacional.

| Sinal | Objeto | Quando grava | Onde fica | Responde |
|---|---|---|---|---|
| `EVT-P01` | `preparo:iniciar` | Na primeira chamada de qualquer rota do preparo da turma | `<modulo>_pacotes.preparo_iniciado_em` | T14, T15 |
| `EVT-P02` | `conteudo:gerar` | A cada `POST …/gerar-conteudo`, **inclusive rascunho não aprovado** | `<modulo>_pacotes.ia_geracoes` (+1) e `ia_tokens` (soma) | T16, T20 |
| `EVT-P03` | `conteudo:homologar` | Ao homologar o conteúdo | `<modulo>_pacotes.aprovado_em` e `aprovado_por` | T14, T16 |
| `EVT-P04` | `painel:ver` | A cada `GET …/painel` do professor | `<modulo>_pacotes.painel_visto_em` (primeira vez) e `painel_vistas` (+1) | T17 |
| `EVT-P05` | `gate:liberar` | A cada etapa que o professor libera no gate — linha nova, nunca sobrescrita | `<modulo>_gates_historico (turma_id, etapa, liberada_em)` | T19 |
| `EVT-P06` | `ia:consumir` | A cada chamada de IA feita para o estudante | `<modulo>_sessoes.tokens_gastos` (soma) e `chamadas_ia` (+1) | T21 |

Na tabela de eventos do PRD e do handoff, cada sinal herdado aparece **com o id do catálogo**,
o verbo e o objeto acima, e na coluna "Onde é lido" o leitor: o `painel de produto (PostHog)`
para os `EVT-U*`, a tabela do módulo para os `EVT-P*`.

```json
{
  "transversais": {
    "T1": {"dono": "plataforma", "grupo": "universal", "pilar": ["adocao_professor"], "sinais": []},
    "T2": {"dono": "plataforma", "grupo": "universal", "pilar": ["adocao_aluno"], "sinais": []},
    "T3": {"dono": "plataforma", "grupo": "universal", "pilar": ["adocao_gestor"], "sinais": []},
    "T4": {"dono": "plataforma", "grupo": "universal", "pilar": ["adocao_gestor"], "sinais": []},
    "T5": {"dono": "plataforma", "grupo": "universal", "pilar": ["funil"], "sinais": []},
    "T6": {"dono": "plataforma", "grupo": "universal", "pilar": ["adocao_professor", "funil"], "sinais": []},
    "T7": {"dono": "missao", "grupo": "universal", "pilar": ["adocao_aluno", "funil"], "sinais": ["EVT-U01", "EVT-U03"]},
    "T8": {"dono": "missao", "grupo": "universal", "pilar": ["funil"], "sinais": ["EVT-U02"]},
    "T9": {"dono": "missao", "grupo": "universal", "pilar": ["adocao_aluno"], "sinais": ["EVT-U01"]},
    "T10": {"dono": "missao", "grupo": "universal", "pilar": ["funil"], "sinais": ["EVT-U04", "EVT-U05"]},
    "T11": {"dono": "missao", "grupo": "universal", "pilar": ["funil"], "sinais": ["EVT-U02"]},
    "T12": {"dono": "missao", "grupo": "universal", "pilar": ["funil", "custo"], "sinais": ["EVT-U02", "EVT-U04", "EVT-U06"]},
    "T13": {"dono": "plataforma", "grupo": "universal", "pilar": ["adocao_aluno"], "sinais": []},
    "T14": {"dono": "missao", "grupo": "universal", "pilar": ["adocao_professor"], "sinais": ["EVT-P01", "EVT-P03"]},
    "T15": {"dono": "missao", "grupo": "customizacao_tema", "pilar": ["adocao_professor"], "sinais": ["EVT-P01"], "so_se": "customizacao_tema"},
    "T16": {"dono": "missao", "grupo": "customizacao_tema", "pilar": ["adocao_professor", "qualidade_ia"], "sinais": ["EVT-P02", "EVT-P03"], "so_se": "customizacao_tema"},
    "T17": {"dono": "missao", "grupo": "universal", "pilar": ["adocao_professor"], "sinais": ["EVT-P04"]},
    "T18": {"dono": "plataforma", "grupo": "universal", "pilar": ["adocao_professor"], "sinais": []},
    "T19": {"dono": "missao", "grupo": "universal", "pilar": ["adocao_professor", "funil"], "sinais": ["EVT-P05"]},
    "T20": {"dono": "missao", "grupo": "customizacao_tema", "pilar": ["custo"], "sinais": ["EVT-P02"], "so_se": "customizacao_tema"},
    "T21": {"dono": "missao", "grupo": "ia_conversacional", "pilar": ["custo"], "sinais": ["EVT-U06", "EVT-P06"], "so_se": "ia_conversacional"}
  },
  "sinais": {
    "EVT-U01": {"verbo": "attempted", "objeto": "missao:iniciar"},
    "EVT-U02": {"verbo": "progressed", "objeto": "etapa:entrar"},
    "EVT-U03": {"verbo": "completed", "objeto": "<expId>"},
    "EVT-U04": {"verbo": "interacted", "objeto": "aviso:inatividade"},
    "EVT-U05": {"verbo": "attempted", "objeto": "erro:exibir"},
    "EVT-U06": {"verbo": "attempted", "objeto": "ia:responder", "so_se": "ia_conversacional"},
    "EVT-P01": {"objeto": "preparo:iniciar", "so_se": "customizacao_tema"},
    "EVT-P02": {"objeto": "conteudo:gerar", "so_se": "customizacao_tema"},
    "EVT-P03": {"objeto": "conteudo:homologar", "so_se": "customizacao_tema"},
    "EVT-P04": {"objeto": "painel:ver"},
    "EVT-P05": {"objeto": "gate:liberar"},
    "EVT-P06": {"objeto": "ia:consumir", "so_se": "ia_conversacional"}
  }
}
```

## Vocabulário fechado

**Corte:** `rede` · `escola` · `missao` · `serie` · `turma` · `professor` · `etapa` · `aluno` · `disciplina`.

**Papel pedagógico da tela** (`pedagogical_role`), derivado da etapa: E1 Desafiar → `intro` ·
E2 Navegar e E3 Decidir → `core_action` · E4 Resultado/Aha → `result` · E5 Explicar → `reflection`
(não há E6 desde 29/10/2026). É o que `EVT-U02` leva em `contexto`, e é o que permite a `T8`
comparar a mesma fase em missões de mecânicas diferentes. As telas do professor (`E0-PROF-*`)
não emitem `EVT-U02`.

## Baseline honesto

Um número só é baseline se alguém o mediu. Escreva **o número com a origem entre parênteses**
(`45% (playtest de 12/08, n=23)`) ou o literal **`sem baseline — primeira medição`**.

`0%`, `—` e `N/A` são **proibidos**: não são medida, são espaço em branco vestido de número, e
um alvo calculado sobre eles é opinião com aparência de meta. Nas primeiras 14 execuções, 20
dos 49 KPIs tinham baseline `0%`.

## O que a missão declara

Cada missão herda as transversais de dono `missao` **do seu grupo** — e, por isso, **emite todos
os sinais delas** — e acrescenta **exatamente 5 perguntas próprias**, que dependem da mecânica. A
regra é a mesma: pergunta, decisão, corte — e um evento que a responda.

Na ficha `perguntas_herdadas`: toda missão herda `T7`–`T12`, `T14`, `T17`, `T19`; a missão com
customização de tema por IA herda também `T15`, `T16`, `T20` (e emite `EVT-P01`–`EVT-P03`); a
missão com IA conversacional em tempo real herda também `T21` (e emite `EVT-U06` e `EVT-P06`). É
a lista de herdadas que diz a que grupo a missão pertence — o gate cobra os sinais a partir dela.

As transversais não precisam de uma linha de KPI cada uma no PRD: elas são lidas no painel de
produto **comparando missões**, e o que a missão deve a elas é o sinal instrumentado. Se o PRD
escrever um KPI para uma transversal, ele usa a pergunta dela e só os sinais do catálogo.

Quem decide quais perguntas importam é o **PO**. Quando o briefing não as traz, o agente
propõe a partir da decisão central da missão e marca `[PROPOSTA — validar com PO]`: proposta
não bloqueia, mas fica visível para quem decide.

## O que NUNCA é medido

Nome, e-mail, CPF, matrícula. Qualquer texto que a criança escreva — resposta, mensagem,
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
