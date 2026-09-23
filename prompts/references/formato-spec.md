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
Nome que o estudante vê · software clonado · por que este viewport · o que a
seção do DS já traz.

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
- `secao_ds: instanooria | unitube | chatgpt | whatsappmobile | tiktooria | nova:<nome> | minijogo:<nome>` (nova exige componentes, responsável e prazo; `tiktooria` ainda não tem ponte em `@edu/ui`)
- `versao: 0.1.0` — semver inicial do `experiencia.json` (`versaoAtiva` no contrato da api). O PRD amarra a mesma versão em três lugares; aqui declara-se só a inicial
- `verbos: {interacted: "…", scored: "…", completed: "…"}` — **o que cada verbo xAPI significa NESTA missão**, uma frase por verbo usado na tabela de eventos do bloco 9. É campo do manifesto real (`experiencia.json#verbos`), não invenção da esteira: sem ele o dado analítico chega sem tradução e ninguém sabe o que `scored` mediu nesta missão
- `liberacao: por-turma` — **opcional, é o default e o único valor aceito** (ADR-69: a missão só abre na turma em que a professora liberou; o funil de estudante passa por `exigirMissaoLiberada`). Só escreva a linha se houver algo diferente a dizer, e aí ela será conferida.

Campo em branco aqui é ❌ em PROD-01 e TEC-01 do gate de dev; sem série a api
não aplica regra por ano; sem `produto` o CI recusa o manifesto (ADR-87); sem
`unidade` a grade da sala não ordena (ADR-69).

## 1. Descoberta central
<frase única> — e o beat exato em que ela é vivida.

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

## 7. Acessibilidade
Canais por instrução (áudio / pictograma / texto), teto de palavras,
gestos que exigem demonstração animada.

## 8. Professora, preparação e parametrização com IA
**A missão é transversal: quem a prepara é o professor de qualquer disciplina.** Contrato de customização = **recorte da aula**: `disciplina` (lista fechada dos componentes curriculares da BNCC + `projeto-interdisciplinar`), `tema` (≤ 60 caracteres), `assuntos` (3 a 6 itens, ≤ 600 caracteres no total — os objetos de conhecimento da aula), `contexto` opcional (turma, escola, região, ≤ 120), `foco` opcional (≤ 120). Campos curtos porque alimentam um prompt: o teto é a primeira barreira contra injeção (mesmo desenho de `ParametrosDoPreparoSchema` da exp-08, em `references/plataforma/exemplo-contrato-rotas-exp-08.md`). O professor **não** declara habilidades BNCC da própria disciplina. · Regras e schemas Zod de geração de conteúdo por IA (Vertex AI Gemini, só via `apps/api/src/ai`), no molde dos schemas da exp-08, incluindo a homologação em que o professor edita **qualquer** texto do pacote antes de aprovar · **Rotas: instancie o padrão de Atividade que a plataforma já tem** (`POST /atividades` cria em rascunho → gerar → `geracao/progresso` por polling → aprovar/reescrever → `ativar`), nunca uma rota de preparo nova por missão · fluxo de curadoria docente (preview, edição de postagens e aprovação **antes da aula**, ADR-66/67) · banco curado default (fallback imediato sem IA) · **tabela "A mesma missão em três aulas"** copiada do one-pager (Português, Ciências/Biologia, História: recorte · o que a IA gera · o que não muda), ou o marcador `[LIMITE DE TRANSVERSALIDADE — dono: produto]` onde couber · **perfil de quota de IA consumido** (`ia_quotas` por perfil, ADR-105) e o que o estudante e a professora veem sem saldo (429, na voz da ficção) · gatilhos de handoff · comportamento da plataforma em cada mediação e pausas (relógio coletivo = tabela `expNNefNb_gates_turma` por polling, ADR-93/94 — nunca WebSocket) · dados do painel docente · roteiro de perguntas.

## 9. Evidências e dados
Campo por campo: o que é coletado, quando, finalidade, retenção, acesso.
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
quando dispara · `resultado` · `contexto` · caminho · **onde é lido** (tabela
`expNNefNb_*` e rota/tela do professor). Ninguém lê `telemetria_eventos` para
relatório de missão: toda medida que a professora vê nasce de tabela própria
do módulo, gravada pela rota operacional.

**Perguntas de produto desta missão (sub-bloco 9f).** A missão declara o que se quer SABER
sobre ela como produto — separado do que o professor lê sobre a turma. Três fichas e uma tabela:

```
- `declared_lessons: 1`        (quantas aulas a missão ocupa; 1, 2 ou fracionada→2)
- `core_action: scored decisao:mural`   (o verbo:objeto que É a decisão central; um só)
- `perguntas_herdadas: T1, T2, T3, T4, T7`

| PQ | Pergunta | Decisão que dispara | Corte | Etapa | Ação (verbo:objeto) | Origem |
|---|---|---|---|---|---|---|
| PQ-01 | quantas duplas trocam de escolha depois do Aha? | <20% → o Aha não chega: reforçar a mediação | turma | E4 | `progressed aha:revelacao` | PO |
```

`declared_lessons` existe porque sem ele a missão de duas aulas aparece com metade de conclusão
**por desenho**, e as melhores são lidas como as piores. `core_action` é o que separa "o aluno
passou pela decisão" de "o aluno abriu a missão". `Origem` é `PO` quando veio do briefing, e
`[PROPOSTA — validar com PO]` quando o agente propôs: proposta não bloqueia, mas fica visível.

<!-- include: references/perguntas-de-produto.md -->

**Cinco caminhos de dado, não dois.** Analítico (`track` →
`/telemetry/batch|beacon` → Pub/Sub, sem ordem); operacional (rota síncrona do
próprio módulo gravando em `expNNefNb_sessoes` — missão nova **não herda**
`POST /runs/:id/eventos`, que é do motor da exp-01); erros de cliente; Web
Vitals; traces OTLP (atributo fora da allowlist do proxy some). Declare o
caminho de cada dado.

**Versão do instrumento e segunda aplicação.** `versao_instrumento` inicial
na linha da sessão, o que acontece com linhas antigas quando sobe, e se
"zerar turma" apaga ou incrementa `tentativa`.

**O prefixo da tabela é o id inteiro, sem separador interno.** A missão `exp05ef3b` usa `exp05ef3b_sessoes`, nunca `exp_05ef3b_` nem `exp_05_`. O identificador já carrega ano e bimestre; quebrá-lo com underscore recria o formato antigo e desalinha migration, Prisma e o `@@map`.

**Tabelas e RLS.** Toda tabela `expNNefNb_*` com `escola_id NOT NULL`, `ENABLE`
+ `FORCE ROW LEVEL SECURITY` e policy por `app.escola_id`; exceção de RLS só
justificada por escrito. Estado é **string com CHECK na migration**, nunca
enum Prisma. Texto livre de menor em tabela própria com `chars_count`, fora de
log e de telemetria.

**Fuso.** Toda data vem de `config.fuso` do handshake / `FUSO_DA_PLATAFORMA`
(ADR-98/99); proibido formatar data na mão.

## 10. Cenários de dispositivo
Os três, com o que muda e a garantia de que a descoberta chega.

## 11. Currículo
Habilidades e códigos **confirmados**, com o momento em tela de cada um.

**Matriz de evidência — obrigatória, uma linha por código de Computação:**

```
| Código | Momento em tela | Ação observável | O que não conta | Medida do bloco 9 | Marcador |
|---|---|---|---|---|---|
| `EF06CO09` | `E3-ALU-01` (Decidir) | seleciona até 4 posts e fixa 1 | rolar o feed sem salvar | `posts_no_mural` | ternário |
```

A coluna «Medida do bloco 9» precisa nomear uma medida que existe lá — habilidade declarada que
nada mede é currículo no papel, e some do relatório do professor. Nas primeiras execuções, 40
códigos de Computação foram declarados e ~38 não tinham nenhum dado ligado.

## 12. Decisões fechadas neste gate
Decisão · quem decidiu · data · alternativas descartadas.
```

## Regra de alteração

A spec só muda por reabertura do Gate 0. Agente de construção não edita spec — se ela estiver errada ou incompleta, devolve, e isso é registrado como falha do gate.

**Blocos acrescentados pela esteira de design (não alteram os blocos 0–12).** Depois do Gate 0, dois agentes anexam blocos à spec sem tocar no texto original:

- **Bloco 13 — Decisões D0** (`fecha-lacunas`): decisões `[D0-n]` que preenchem ausências deriváveis da missão, com base declarada, e os pedidos de re-spec `[RS-n]` pendentes. Preenche ausência, nunca altera presença.
- **Bloco 14 — Ambiente simulado** (`ambiente-simulado`): a ficha do ambiente — nome, seção do DS, verbos do bloco 4 com rótulo literal, dispositivo nativo, estados e o que a plataforma real não tem. Emitido mesmo quando a spec já nomeia o ambiente (dormente).

Bloco 0–12 diferente do texto do Gate 0 continua sendo violação; bloco 13 ou 14 ausente numa spec que passou pela esteira de design é sinal de que D0 ou D9 não rodaram.
