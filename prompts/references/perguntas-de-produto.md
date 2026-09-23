# Perguntas de produto — o que a missão precisa declarar para ser medida

Uma **pergunta de produto** é uma pergunta que, respondida, muda uma decisão nossa: o que
priorizar, o que cortar, o que encurtar, com quem conversar. Ela tem três partes — **a
pergunta, a decisão que ela dispara e o corte**. Se não dispara decisão, é curiosidade.

Três coisas diferentes eram tratadas como uma só, e é o que produzia KPI que ninguém usa:

| Camada | Responde | Quem lê | Onde se vê |
|---|---|---|---|
| **Log e observabilidade** | o sistema está de pé, rápido e sem erro? | engenharia | Google Cloud |
| **Telemetria de uso** | o que as pessoas fizeram, em que ordem, onde pararam? | ninguém "olha": é matéria-prima | `expNNefNb_*` e Pub/Sub |
| **Produto** | a missão está funcionando como produto? | PO e engenharia | painel |
| **Relatório pedagógico** | o que esta turma entendeu? | só o professor | tela de resultados |

**A missão declara as duas últimas, e elas não se misturam.** Um número que serve às duas ao
mesmo tempo é coincidência, não desenho.

## As perguntas transversais — toda missão herda

Valem igual para qualquer missão, independentemente da mecânica, e por isso não se reinventam.

| ID | Pergunta | Decisão que dispara | Corte |
|---|---|---|---|
| `T1` | De cada 10 professores que abriram a missão, quantos liberaram para uma turma? | Conversão baixa → a tela de preparo gera insegurança: simplificar ou reforçar o guia | missao · escola |
| `T2` | De cada 10 turmas liberadas, quantas chegaram ao fim? | Menos da metade → longa demais ou travando: entra na fila antes de qualquer feature nova | missao · serie |
| `T3` | A missão cabe numa aula? (tempo do início ao fim contra o nº de aulas declarado) | Passa do teto em missão de 1 aula → encurtar ou dividir | missao |
| `T4` | O professor voltou para ver o resultado da turma? Em quantos dias? | Não volta → o relatório não entrega valor: avisar por e-mail, depois redesenhar | escola · missao |
| `T5` | Quantas escolas da rede usaram contra quantas só receberam acesso? | Escola inativa é problema de ativação → conversa com o gestor da rede | rede · escola |
| `T6` | O professor que usou uma vez voltou em 30 dias? | Retorno baixo → produto "de uma vez": entender o que faltou antes de vender mais | escola |
| `T7` | O que estragou aulas: missão não liberada, sessão expirada, tela que não carregou, IA sem saldo? | Aula perdida por falha silenciosa é prioridade acima de feature | missao · escola |
| `T8` | Quanto custa de IA uma aula, por aluno? | Acima do teto → otimizar antes de escalar para mais redes | missao · escola |

## Vocabulário fechado

**Corte:** `rede` · `escola` · `missao` · `serie` · `turma` · `professor`.

**Papel pedagógico da tela** (`pedagogical_role`), derivado da etapa: E1 Desafiar → `intro` ·
E2 Navegar e E3 Decidir → `core_action` · E4 Resultado/Aha → `result` · E5 Explicar e E6
Refletir → `reflection`. As telas do professor (`E0-PROF-*`) não emitem `screen_viewed` de
estudante.

## Baseline honesto

Um número só é baseline se alguém o mediu. Escreva **o número com a origem entre parênteses**
(`45% (playtest de 12/08, n=23)`) ou o literal **`sem baseline — primeira medição`**.

`0%`, `—` e `N/A` são **proibidos**: não são medida, são espaço em branco vestido de número, e
um alvo calculado sobre eles é opinião com aparência de meta. Nas primeiras 14 execuções, 20
dos 49 KPIs tinham baseline `0%`.

## O que a missão declara

Cada missão herda as transversais e acrescenta **2 a 4 perguntas próprias**, que dependem da
mecânica dela. A regra é a mesma: pergunta, decisão, corte — e um evento que a responda.

Quem decide quais perguntas importam é o **PO**. Quando o briefing não as traz, o agente
propõe a partir da decisão central da missão e marca `[PROPOSTA — validar com PO]`: proposta
não bloqueia, mas fica visível para quem decide.

## O que NUNCA é medido

Nome, e-mail, CPF, matrícula. Qualquer texto que a criança escreva — reflexão, mensagem,
justificativa, termo de busca: dele sai a **medida** (`respondeu: true`), nunca o conteúdo. E
as respostas do check-in de bem-estar, que são questionário de saúde mental.
