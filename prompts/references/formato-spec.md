---
name: formato-spec
description: Gabarito da especificação de missão emitida pelo Gate 0 — o contrato que a esteira constrói. Lido por qa-conformidade e por todos os agentes de construção.
sources: [chat]
---

# Especificação de missão → `spec/<missao>-spec.md`

Emitida pelo agente 1 junto com o veredito 🟢. É a **fonte da verdade da construção** — a esteira constrói contra ela, não contra o one-pager. Campo em aberto não existe: se está aberto, a missão não passou.

```markdown
# Spec — <missão> v<x>

**Ano/faixa · Ambiente · Rubrica vX.X · Gate 0 aprovado em <data>**

## 0. Identificação de plataforma
Nome que o estudante vê · software clonado · classe do ambiente (app clonado | mini-jogo)
· por que este viewport · o que a seção do DS já traz.

**Ficha do manifesto — obrigatória, uma linha por campo, neste formato exato**
(um gate determinístico lê estas linhas; campo fora do formato conta como ausente):
- `id: expNNefNb` — **o identificador carrega o ano e o bimestre.** `NN` é o ano (01–09 no
  Fundamental, 01–03 no Médio), `ef`/`em` é a etapa, e o dígito antes do `b` é o bimestre
  (1–4). Exemplos: `exp01ef1b` = 1º ano do Fundamental, 1º bimestre; `exp05ef3b` = 5º ano do
  Fundamental, 3º bimestre; `exp02em2b` = 2º ano do Médio, 2º bimestre. Um gate determinístico
  confere que `series` e `unidade` abaixo **concordam** com o id — divergência trava, porque
  é o id que nomeia tabela, pasta e branch. Missão transversal (`series: []`) e ferramenta de
  professor não têm ano nem bimestre: essas seguem no formato antigo `exp-NN-<slug>`
- `produto: entre-redes | plano-de-aula | plano-de-ensino | bem-estar`
- `series: ["5EF"]` (formato da plataforma; `[]` = transversal/todas)
- `unidade: 1 | 2 | 3 | 4 | nenhuma` (`nenhuma` só em transversal ou ferramenta de professor)
- `publico: estudante | professor`
- `viewport: 375x812 | desktop | <largura>x<altura>`
- `permissoes: [forms, pointer-lock, downloads]` ou `permissoes: []` — **tudo o que a missão precisa do aparelho, inclusive o que a plataforma ainda não concede**. Tocar áudio e vídeo já é nativo e não se declara; gravar voz (`microphone`), usar a câmera (`camera`) ou gravar a tela (`display-capture`) são pré-requisitos de plataforma: declare, e o PRD sai 🟡 com o caminho de implementação. A tabela das três categorias está em `references/capacidades-plataforma.md`
- `capabilities: [telemetria, progresso, ia, avaliacao, tempo-real]` (só as usadas)
- `secao_ds: unooriaai | unoovista | unoochat | tiktooria | unoogaleria | unoojornal | unooblog | nova:<nome> | minijogo:<nome>` — a tradução do ambiente do briefing (ChatGPT → `unooriaai`, Instagram → `unoovista`, WhatsApp → `unoochat`, galeria de fotos → `unoogaleria`) está em `ambientes.md`, e a lista do que existe, no contrato da plataforma e no inventário do DS. **A seção que o briefing fixou é trava:** o bloco 0 a repete, e o que a coleção não oferece vai como pré-requisito do DS — o verificador bloqueia a spec que troca. As legadas (`chatgpt`, `instanooria`, `whatsappmobile`, `unootube`) só por decisão registrada do PO; o verificador as bloqueia (ADR-133 a 138). Nova exige componentes, responsável e prazo, e só quando nenhuma coleção do inventário cobre o app (o verificador bloqueia `nova:galeriadefotos`); `tiktooria`, `unoogaleria`, `unoojornal` e `unooblog` ainda não têm ponte em `@edu/ui` — a ponte é pré-requisito de plataforma.
- `classe_ambiente: app-clonado | mini-jogo` — campo da esteira, não do `experiencia.json`: **a classe do ambiente, decidida em produto** (desde 24/10/2026, PR 8 do plano «Produto dono do contrato», decisão D8; `ambiente-e-minijogo.md`). Mini-jogo é sempre `secao_ds: minijogo:<nome>`, só no 1º–5º ano; toda outra seção é app clonado — um gate confere que as duas linhas concordam. O D9, no design, lê a classe e a seção daqui e não as decide: spec calada volta a produto. Ambiente novo (`nova:<nome>`) ou mini-jogo que o briefing não fixou é escolha do PO: uma linha do bloco 0 traz `[PROPOSTA — validar com PO: … · por quê: … · alternativa: <a seção existente mais próxima>]` até o de acordo, e a spec que os fixa sem ela é bloqueada. Spec de antes de 24/10/2026, sem a linha, é lida pela `secao_ds`
- `secoes_ds_extras: [<seção>, …]` — as outras seções do DS que a missão usa além da principal (vazio = nenhuma; `varias-secoes.md`): cada uma da mesma lista de `secao_ds`, dentro do teto do ano, com linha no «Mapa de seções» e transição em «Transições» no bloco 14. O verificador confere as quatro coisas.
- `versao: 0.1.0` — semver inicial do `experiencia.json` (`versaoAtiva` no contrato da api). O PRD amarra a mesma versão em três lugares; aqui declara-se só a inicial
- `verbos: {interacted: "…", scored: "…", completed: "…"}` — **o que cada verbo xAPI significa NESTA missão**, uma frase por verbo usado na tabela de eventos do bloco 9. É campo do manifesto real (`experiencia.json#verbos`), não invenção da esteira: sem ele o dado analítico chega sem tradução e ninguém sabe o que `scored` mediu nesta missão
- `liberacao: por-turma` — **opcional, é o default e o único valor aceito** (ADR-69: a missão só abre na turma em que a professora liberou; o funil de estudante passa por `exigirMissaoLiberada`). Só escreva a linha se houver algo diferente a dizer, e aí ela será conferida.

Campo em branco aqui é ❌ em PROD-01 e TEC-01 do gate de dev; sem série a api
não aplica regra por ano; sem `produto` o CI recusa o manifesto (ADR-87); sem
`unidade` a grade da sala não ordena (ADR-69).

## 1. Descoberta central
<frase única> — e o beat exato em que ela é vivida.
Logo abaixo, a **anatomia do aha** copiada da tabela 1.2 do one-pager (crença de
entrada · aposta comprometida · consequência sentida · virada · nomeação ·
transferência) e o **conceito limiar** do material com a etapa em que é vivido
(tabela 1.1). É o que design protege na tela do pico e dev mede no bloco 9: a
aposta que trava vira estado latch, e a consequência que muda por escolha vira regra
de sistema no bloco 2.

## 2. Mecanismo por etapa
Por etapa (1–6): o que o sistema **apresenta**, **ordena**, **bloqueia** e
**garante**. Não o que se espera do aluno — o que o sistema faz.
Onde a descoberta depende de sequência, a regra de sequência está aqui.

**Contrato de estados — obrigatório.** Uma linha por transição: estado
inicial, gatilho, regra, estado seguinte, responsável. **Estados com nome
próprio**, porque viram enum no código. Fecha com a frase que declara o
conjunto completo: "não existem outros caminhos de conclusão, correção
antecipada, reabertura de escolha ou mudança de pacote". Inclui:
conclusão (quem fecha, o que congela, o que reporta, o que ainda é
permitido) · estados latch · reentrada (F5, voltar noutro dia) · segunda
aplicação (o que re-sorteia, o que preserva, o que "zerar turma" apaga) ·
modos de erro **na voz da ficção**, como estado próprio, nunca confundidos
com decisão do aluno.

**Regras e fases do mini-jogo — obrigatória quando `classe_ambiente: mini-jogo`.** A subseção
`### Regras e fases do mini-jogo`, copiada do §4 do one-pager palavra por palavra, no formato de
`ambiente-e-minijogo.md`: tipo de jogo, as regras `R1`… (valem em todas as fases), a tabela das fases
(`| Fase | Nome | Ideia nova | Regra da fase | Verbo do jogo | Como vence | Como perde | Habilidade |`),
como o progresso aparece e a progressão. É conteúdo de produto desde 24/10/2026 (PR 8): a jornada só
mapeia as telas para as fases, e regra ou fase que a spec não tem, na jornada, vira proposta ao PO
(um gate em código confere). Sem ela, a spec de mini-jogo é bloqueada; se a decisão é do PO,
`[ABERTO — dono: PO: regras e fases do mini-jogo — …]`.

## 3. Caminhos degenerados — tratamento
| Caminho | O que acontece | Etapa preservada? |
Não escolheu nada · escolheu tudo · não usou a ferramenta ·
exploração mínima · terminou antes.

## 4. Verbos e affordances
Verbo nativo confirmado por ação, com antes / verbo / depois.

## 5. Ausências declaradas
O que o ambiente simulado NÃO tem, e por que cada ausência existe.
Reaparecimento é violação, não melhoria.

## 6. Tetos aplicados
Decisões do mesmo tipo (com a conta) · duração por ato · etapas
cognitivas por decisão · onde há scaffolding e onde a dica desaparece.
**Tempos e formatos de aula, copiados do §10 do one-pager:** a tabela por etapa (em tela · fora
da tela), o total em tela com o mesmo número (`Em tela: <n> min`), os checkpoints e os cenários de
aula (aula única, duas aulas, sessões fracionadas). Parecer que pede menos tempo vai para as
ressalvas do bloco 12; o número não muda aqui.

## 7. Acessibilidade
Canais por instrução (áudio / pictograma / texto), teto de palavras,
gestos que exigem demonstração animada.

## 8. Professora, preparação e parametrização com IA
**A missão é transversal: quem a prepara é o professor de qualquer disciplina.** Contrato de customização = **recorte da aula**: `disciplina` (lista fechada dos componentes curriculares da BNCC + `projeto-interdisciplinar`), `tema` (≤ 60 caracteres), `assuntos` (3 a 6 itens, ≤ 600 caracteres no total — os objetos de conhecimento da aula), `contexto` opcional (turma, escola, região, ≤ 120), `foco` opcional (≤ 120). Campos curtos porque alimentam um prompt: o teto é a primeira barreira contra injeção (mesmo desenho do esquema de parâmetros do preparo do Júri, em `references/plataforma/exemplo-juri-contrato-rotas.md`). O professor **não** declara habilidades BNCC da própria disciplina. · Regras e schemas Zod de geração de conteúdo por IA (Vertex AI Gemini, só via `apps/api/src/ai`), no molde dos schemas do Júri (exp06ef1b), incluindo a homologação em que o professor edita **qualquer** texto do pacote antes de aprovar · **Rotas do preparo docente: no módulo da própria missão, no molde do Júri (`juri-estadual`, exp06ef1b; `references/plataforma/exemplo-juri-contrato-rotas.md`) — `POST /<modulo>/turmas/«turmaId»/gerar-conteudo` → `GET …/conteudo` → `POST …/homologar` (o professor edita e aprova) → `POST …/gate` (libera a turma), com o painel em `GET …/turmas/«turmaId»/painel`; é o que `juri-estadual` (exp06ef1b), `quem-mandou-isso` (exp05ef1b) e `foto-conta` (exp01ef1b) fazem. O módulo `/atividades` é o motor do Instanooria (exp08ef1b) e **não se reusa**: citar `/atividades/«id»/aprovar`, `/pacote` ou `/curadoria` é citar rota que não existe** · fluxo de curadoria docente (preview, edição de postagens e aprovação **antes da aula**, ADR-66/67) · banco curado default (fallback imediato sem IA) · **tabela "A mesma missão em três aulas"** copiada do one-pager (Português, Ciências/Biologia, História: recorte · o que a IA gera · o que não muda), ou o marcador `[LIMITE DE TRANSVERSALIDADE — dono: produto]` onde couber · **perfil de quota de IA consumido** (`ia_quotas` por perfil, ADR-105) e o que o estudante e a professora veem sem saldo (429, na voz da ficção) · gatilhos de handoff · comportamento da plataforma em cada mediação e pausas (relógio coletivo = tabela `expNNefNb_gates_turma` por polling, ADR-93/94 — nunca WebSocket) · dados do painel docente · roteiro de perguntas, no momento em que o one-pager o coloca · **podcast de recapitulação** do §11 do one-pager: título, vozes, duração, quando toca, quem toca e o aviso ao professor (o roteiro fica no one-pager e ninguém a jusante o reescreve; nas 11 missões do bucket até 06/10/2026 nenhuma spec o trazia, e design e brief de assets reescreveram o áudio).

## 9. Evidências e dados
Campo por campo: o que é coletado, quando, finalidade, retenção, acesso. **Retenção, PII de menor, texto livre e mídia
seguem o padrão da plataforma** (`references/padrao-plataforma-retencao-lgpd.md`): cite o padrão pelo nome
(`padrão: retencao-lacuna-assumida`) e escreva só o que é da missão — prazo próprio não se inventa (decisão D6, 24/10/2026).
E a lista do que **não** é coletado nem calculado. Mais, obrigatoriamente:

**Graus de medida.** Por medida: `scored` (≥2 sinais independentes, tem
número) · `indicative` (1 sinal, texto, fora das médias) · `zero` (teve a
chance e não foi — entra na média) · `none` (a oportunidade não chegou —
sai da conta). Tratar "não teve chance" como "escolheu não" faz uma criança
parecer ter recusado o que nunca lhe foi oferecido, e o número será lido
por um adulto que decide sobre ela.

**Tabela de medidas — obrigatória, cabeçalho exato (um gate determinístico a lê):**

```
| Medida | Grau | Sinais | Canal | Tabela.coluna | Habilidade |
|---|---|---|---|---|---|
| `posts_no_mural` | `scored` | `salvar:post` + `submeter:mural` | operacional | `expNNefNb_sessoes.posts` | `EF06CO09` |
```

Identificador entre crases, um por célula. `scored` com menos de dois sinais nomeados é
reprovado: é a própria definição acima, e sem conferência o grau inflava — das 25 medidas
`scored` das primeiras execuções, só 10 nomeavam dois sinais.

**Canal por dado.** Cada dado em um de dois canais que não se misturam:
**operacional** (alimenta a mecânica em tempo real, rota síncrona) ou
**analítico** (análise posterior, em lote, sem garantia de ordem). Tempo de
exploração e dwell nunca no analítico.

**Texto livre de menor.** Existe? Por quê é necessário? **Quem lê?** Se
existe, vai em **tabela própria, lida só pelo professor da escola** — nunca
na telemetria analítica. Campos de payload aceitam só número, booleano ou
string de vocabulário fechado. O registro da reflexão que o critério 1.6
exige é, por definição, texto livre de menor: é legítimo e **precisa deste
campo preenchido**. O 1.6 e a regra de dados só colidem quando o destino
não está escrito.

**Segredo de servidor.** Lista do que nunca vai ao bundle: gabarito,
parâmetros ocultos, calibragem, vieses, prompt de sistema, e qualquer conta
cujo resultado antecipe o desfecho.

**Ficha do gabarito — obrigatória, uma linha, lida por gate:**

```
- `gabarito_servidor: sim`
```

**Gabarito.** Fonte da verdade pedagógica, com a declaração de que vive
exclusivamente no servidor. Quem assina não se declara aqui: autoria e revisão
são registro editorial, fechado fora da esteira.

**Falha nunca é decisão.** Estado de falha de plataforma (conexão, sessão expirada, mídia que não carregou) é sempre `none` para toda medida que dependia da tela que falhou — nunca `zero`, nunca um estado de escolha do estudante. O contrato de estados do bloco 2 nomeia a falha; o bloco 9 diz em que grau ela cai.

**Servidor calcula, nunca aceita.** O que o cliente envia (medidas brutas)
e o que o servidor deriva.

**Pergunta de evidência (Canal B), quando a matriz do bloco 11 a declara.** A pergunta, as três
alternativas com o nível de cada uma (a spec não fixa a ordem: o servidor sorteia a cada
exibição), o componente que a renderiza — do DS da seção, ou local com responsável, nunca
chamado "do DS" sem estar lá — e o retorno ao estudante, que é só a confirmação de envio. A
resposta vai pela **rota operacional do módulo**, com o identificador opaco da alternativa; o
servidor calcula o nível pelo mapeamento fixo e grava na tabela do módulo, lida pela tela do
professor. O nível **nunca** trafega no `track`: quem chama `track` é o cliente, e o cliente que
conhece o nível conhece o gabarito. Uma resposta é um sinal só — a medida é `indicative`, e vira
`scored` apenas somada a um sinal de Canal A da mesma habilidade. O bloco 2 ganha o estado da
pergunta entre o Refletir e a conclusão, e a falha de plataforma nesse estado é `none`.

**Mídia capturada do estudante.** Se a missão grava voz, foto, vídeo ou tela
(`microphone`, `camera`, `display-capture` no bloco 0), este bloco declara, sem
exceção: **onde a mídia é gravada** (tabela `expNNefNb_*` com `escola_id` e RLS,
ou arquivo no bucket com caminho não adivinhável), **quanto tempo fica**
(retenção ou lacuna assumida por escrito), **quem lê** (só a professora da
escola — nunca rota de gestor, nunca telemetria, nunca Clarity) e **o que
acontece quando a família não autoriza ou o aparelho não tem o recurso**. Voz e
imagem de criança são dado pessoal e não são coletados por padrão: sem esses
quatro campos a missão não passa pela banca de dados.

**Eventos — o contrato real da plataforma.** Cada evento é
`track(verbo, objeto, <resultado?, contexto?>)`: `verbo` e `objeto` são strings
(objeto na convenção `namespace:slug`, ex.: `chat:amara`, `missao:concluida`);
`resultado` e `contexto` são objetos JSON com número, booleano ou vocabulário
fechado. **Não existe campo `dados`** — a api descarta chave desconhecida em
silêncio. A spec traz a tabela de eventos com estas colunas: verbo · objeto ·
quando dispara · `resultado` · `contexto` · caminho · **onde é lido**. São dois
leitores, e só dois: o que a professora vê nasce de tabela própria do módulo
(`expNNefNb_*` + rota/tela do professor), gravada pela rota operacional; o que só
alimenta uma pergunta de produto do 9f é lido no `painel de produto (PostHog)`.
Pub/Sub, `/telemetry/batch` e `telemetria_eventos` são transporte — escrever um
deles como leitor é dizer que ninguém lê.

**Perguntas de produto desta missão (sub-bloco 9f).** A missão declara o que se quer SABER
sobre ela como produto — separado do que o professor lê sobre a turma. Três fichas e uma tabela:

```
- `declared_lessons: 1`        (quantas aulas a missão ocupa; 1, 2 ou fracionada→2)
- `core_action: scored decisao:mural`   (o verbo:objeto que É a decisão central; um só)
- `perguntas_herdadas: T7, T8, T9, T10, T11, T12, T14, T15, T16, T17, T19, T20`   (universais T7–T12, T14, T17, T19; + T15, T16, T20 com customização de tema por IA; + T21 com IA conversacional)

| PQ | Pergunta | Decisão que dispara | Corte | Etapa | Ação (verbo:objeto) | Origem |
|---|---|---|---|---|---|---|
| PQ-01 | quantas duplas trocam de escolha depois do Aha? | <20% → o Aha não chega: reforçar a mediação | turma | E4 | `progressed aha:revelacao` | PO |
```

`declared_lessons` existe porque sem ele a missão de duas aulas aparece com metade de conclusão
**por desenho**, e as melhores são lidas como as piores. `core_action` é o que separa "o aluno
passou pela decisão" de "o aluno abriu a missão". `Origem` é `PO` quando veio do briefing, e
`[PROPOSTA — validar com PO]` quando o agente propôs: proposta não bloqueia, mas fica visível.

`perguntas_herdadas` não é escolha: são as transversais de dono `missao` do catálogo abaixo, e
cada uma cobra seus sinais. A tabela de eventos do bloco 9 traz as linhas dos eventos universais
do estudante (`EVT-U*`) **com o verbo e o objeto do catálogo, sem adaptar**, e o modelo conceitual traz as
colunas dos sinais do professor (`EVT-P*`) nas tabelas do módulo (a especificação de DDL SQL com tipos e constraints cabe exclusivamente ao PRD na etapa de Dev). Um gate confere os dois.

<!-- include: references/perguntas-de-produto.md -->

**Cinco caminhos de dado, não dois.** Analítico (`track` →
`/telemetry/batch|beacon` → Pub/Sub, sem ordem); operacional (rota síncrona do
próprio módulo gravando em `expNNefNb_sessoes` — missão nova **não herda**
`POST /runs/:id/eventos`, que é do motor da exp-01); erros de cliente; Web
Vitals; traces OTLP (atributo fora da allowlist do proxy some). Declare o
caminho de cada dado.

**Versão do instrumento e segunda aplicação.** `versao_instrumento` inicial
na linha da sessão, o que acontece com linhas antigas quando sobe, e se
"zerar turma" abre rodada nova: a linha da rodada anterior fica, imutável, e é ela que o painel de habilidades lê — nada se apaga nem se arquiva (o que se conta por ação é `<acao>_tentativas`).

**O prefixo da tabela é o id inteiro, sem separador interno.** A missão `exp05ef3b` usa `exp05ef3b_sessoes`, nunca `exp_05ef3b_` nem `exp_05_`. O identificador já carrega ano e bimestre; quebrá-lo com underscore recria o formato antigo e desalinha migration, Prisma e o `@@map`.

**Tabelas e modelo conceitual.** O Bloco 9 define as tabelas e colunas conceituais necessárias para a pedagogia e telemetria (ex.: `expNNefNb_*`), separando o que é operacional e o que é analítico. Toda tabela conceitual deve prever isolamento por `escola_id`. Detalhamento de DDL SQL (`CREATE TABLE`, tipos SQL, chaves estrangeiras, constraints e RLS) é responsabilidade exclusiva da Seção 11 do PRD. Texto livre de menor em entidade própria com `chars_count`, fora de log e de telemetria.

**Fuso.** Toda data vem de `config.fuso` do handshake / `FUSO_DA_PLATAFORMA`
(ADR-98/99); proibido formatar data na mão.

## 10. Cenários de dispositivo
Os três, com o que muda e a garantia de que a descoberta chega. **Aparelho compartilhado segue o padrão da plataforma**
(`references/padrao-plataforma-revezamento.md`): cite `padrão: revezamento-pela-plataforma` — a missão não prescreve
papéis nem rodízio (o PO recusou na exp06ef1b) — e escreva só o teste da descoberta no cenário 2–4.

## 11. Currículo
Habilidades e códigos **confirmados**, com o momento em tela de cada um — **os mesmos do contrato
de evidência (§12a) do one-pager aprovado**, nem um a mais, nem um a menos. Mais as competências
socioemocionais e os descritores SAEB do §2, copiados.

**Matriz de evidência — obrigatória, uma linha por código de Computação:**

```
| Código | Momento em tela | Ação observável | O que não conta | Medida do bloco 9 | Canal de evidência | Regra ternária |
|---|---|---|---|---|---|---|
| `EF06CO09` | `E3-ALU-01` (Decidir) | seleciona até 4 posts e fixa 1 | rolar o feed sem salvar | `posts_no_mural` | A | Atingiu: fixa um post cuja fonte abriu · Em processo: salva posts, mas fixa um sem abrir a fonte · Não atingiu: não salva nenhum |
```

A coluna «Medida do bloco 9» precisa nomear uma medida que existe lá — habilidade declarada que
nada mede é currículo no papel, e some do relatório do professor. Nas primeiras execuções, 40
códigos de Computação foram declarados e ~38 não tinham nenhum dado ligado.

«Canal de evidência» é `A` (ação do estudante, classificada pelo servidor) ou `A + B` (a ação
mais a pergunta de múltipla escolha depois do Refletir), copiado da seção 12a do one-pager — `B`
sozinho não existe: toda habilidade tem Canal A, e um código confere; não confundir com o canal do
dado (operacional × analítico) do bloco 9. «Regra ternária» diz o que separa
**Atingiu**, **Em processo** e **Não atingiu** — por extenso, porque os círculos coloridos são
veredito de gate. Com `A + B`, a regra da ação vem primeiro e o mapeamento das três alternativas a acompanha;
a pergunta com as alternativas vai no bloco 9. O Canal B **soma** evidência: a linha continua com momento em tela e
ação observável. No 1º e no 2º ano, as três alternativas ficam na tela ao mesmo tempo (opção
visível sobe o teto da faixa de duas para três, critério 3.5) e são narradas (6.1).

A regra ternária tem de ser **alcançável e sem buraco**: cada nível descreve um resultado que a
interface deixa acontecer (se a tela não deixa repetir categoria, "repetiu a categoria" não é nível),
as faixas não se sobrepõem, e toda combinação possível de respostas cai em exatamente um nível — conte
as combinações (3 regiões × 4 rótulos, por exemplo) e diga onde cai cada uma. Quem codifica não pode
ter de inventar a classificação de um caso que a regra esqueceu (exp03ef1b, 07/10/2026: "4 certas +
pânico" e "≤1 certa" ficavam sem nível; "3 certas + 1 distrator" caía em dois).

## 12. Decisões fechadas neste gate
Decisão · quem decidiu · data · alternativas descartadas. Quem decide é o PO; parecer recomenda. A
coluna «quem decidiu» diz a fonte verdadeira, uma de três: **briefing** (a frase do PO no briefing);
**PO — <pedido de refazer ou parecer, com data>** (só se a sessão tem esse registro); ou **agente —
`[PROPOSTA — validar com PO]`**. O one-pager que a esteira gerou ainda não é one-pager aprovado: "PO
no one-pager aprovado" sem *de acordo* do PO é decisão do agente apresentada como do PO, e o
verificador bloqueia (`tools/decisoes.py`).

**Ressalvas dos pareceres não incorporadas** — o que um parecer ou gate recomendou e o one-pager
aprovado manteve diferente. Registro para o PO, sem marcador: não trava nada, e a spec segue o
one-pager.

```
| Parecer | Item | O que recomendou | O que o one-pager manteve |
|---|---|---|---|
| Adequação pedagógica | A2 | tirar `EF06CO07` do contrato | quatro habilidades, com `EF06CO07` |
```

## Glossário canônico
> Todo documento a jusante (jornada, fluxo, copy, protótipo, brief de assets, banco de conteúdo,
> PRD) usa só os nomes desta seção. Um verificador determinístico confere cada um contra ela:
> variante proibida em tela é bloqueio.

### Entidades
| Nome canônico | Variantes proibidas |
|---|---|
| <órgão, projeto, empresa, plataforma — o nome que aparece em tela> | "<outro nome que já circulou>"; "<sigla ou abreviação que não vale>" |

### Personagens
| Nome | Idade | Papel na história |
|---|---|---|
| <nome> | <anos> | <o que a pessoa é na história, com o verbo: "beneficiário do X", "coordena o Y"> |

### Números
| O quê | Valor | Unidade |
|---|---|---|
| <grandeza com a entidade no nome: "vagas novas do X"> | <número> | <vagas · dias por semana · R$ · …> |

### Rótulos de botão por ação
| Ação | Rótulo |
|---|---|
| <o que o botão faz, em verbo> | <o texto exato do botão> |

### Arquivos
| Artefato | Nome do arquivo |
|---|---|
| Protótipo navegável | design/08-prototipo.html |
```

## Regra de alteração

A spec só muda por reabertura do Gate 0. Agente de construção não edita spec — se ela estiver errada ou incompleta, devolve, e isso é registrado como falha do gate.

O `## Glossário canônico` faz parte do texto do Gate 0, como os blocos 0–12: quem acrescenta bloco depois dele o copia intocado.

**Bloco acrescentado em produto, antes do de acordo (é texto de produto como os blocos 0–12).** Desde 24/10/2026
(PR 6 do plano «Produto dono do contrato») o que o D0 fechava no design e é de produto fecha em produto, antes da banca e
do parecer:

- **Bloco 15 — Completude de produto** (`completude-spec`, passo 045b, prompt 046): decisões `[CP-n]` que preenchem as células de produto que a esteira consome (estado, handoff, evidência, dados e retenção, duração e tetos, painel docente, PQ e KPI, texto do professor, revezamento), com base declarada; os padrões da plataforma aplicados; as perguntas ao PO (`[PARÂMETRO]`, `[PROPOSTA]`, `[ABERTO — dono: PO]`) que o de acordo responde; e o mapa célula → decisão. O passo emite só o bloco 15, e o código o monta na spec sem tocar os blocos 0–12.

**Anexo de design (não altera a spec de produto).** Depois do de acordo de produto a `spec_missao` não muda mais. Os dois
agentes de design gravam num documento à parte, `design/00-anexo-design-spec.md` (`anexo_design_spec`):

- **Bloco 13 — Decisões D0** (`fecha-lacunas`, D0-UX): decisões `[D0-n]` só de UI/UX — a tela de cada estado, gesto, scaffolding, acessibilidade de componente, dispositivo — que preenchem ausências deriváveis da missão, com base declarada, os pedidos de re-spec `[RS-n]` pendentes e os `[ABERTO — dono: PO]` do que é de produto. Preenche ausência, nunca altera presença.
- **Bloco 14 — Ambiente simulado** (`ambiente-simulado`): a ficha **de UI** do ambiente que o bloco 0 decidiu — uma por seção quando a missão usa mais de uma, mais o «Mapa de seções» e as «Transições» — nome, seção do DS, chrome, navegação, affordances, verbos do bloco 4 com rótulo literal e componente, dispositivo nativo, estados e o que a plataforma real não tem; para ambiente novo ou mini-jogo, a seção do DS só com tokens existentes. Desde o PR 8 (24/10/2026, decisão D8) o D9 não decide nada: a classe e o ambiente são os do bloco 0, e as regras e as fases do mini-jogo, as do bloco 2. Um gate no split bloqueia o bloco 14 que nomeia ambiente ou classe diferente do bloco 0, que traz regra ou fase de jogo, ou o texto do D9 fora do bloco 14 — decisão de produto; a spec calada e a troca que o D9 julgar necessária voltam a produto como `[PROPOSTA — validar com PO]`.

A fonte da verdade para codar é a spec de produto mais o anexo de design; o PRD deriva delas (D10). O anexo é montado
pelo código: D0 e D9 emitem o próprio bloco, e o que vier diferente do texto de produto (blocos 0–12, glossário, bloco
15) é descartado e aparece ao PO como `[ABERTO — dono: PO]` no cartão do parecer de design. O `[ABERTO — …]` que uma
decisão fechou fica registrado no **mapa célula → decisão** do bloco que a tomou (`| marcador literal | [D0-n] |` no 13,
`| marcador literal | [CP-n] |` no 15), e o rastro de lacunas deixa de cobrar essa linha. Missão gerada antes do PR 6
traz os blocos 13 e 14 dentro da spec; a esteira ainda a lê assim, e o design refeito monta o anexo.
