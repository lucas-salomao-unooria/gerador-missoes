---
name: padrao-plataforma-preparo-professor
description: O preparo do professor — as cinco telas E0-PROF-01…05, os estados, o grafo do professor com o caminho curto, o trilho no protótipo e a conferência do QA. Padrão da plataforma, igual em toda missão; jornada, fluxo, telas, protótipo e QA de design o citam.
sources: [071_jornada, 072_fluxo, 075_telas, 079_prototipo, 088_qa_entregaveis, criterios-gate-estrutural, literatura-cognitiva]
status: padrão da plataforma (D7 do plano «Produto dono do contrato», 23/10/2026)
---

# Preparo do professor — padrão da plataforma (`E0-PROF-01…05`)

**O que este arquivo é.** Toda missão é aplicada pelo professor de **qualquer disciplina** — nos anos finais e no Médio, quem leva a turma é o professor de Português, de Biologia, de História —, e o preparo dele no hub é o mesmo em toda missão: escolher a missão, recortar a aula, gerar, curar, pôr no ar. Não é decisão de design por missão, nem contrato de produto por missão: é padrão da plataforma (decisão D7 do plano «Produto dono do contrato», 23/10/2026). Até 24/10/2026 o fluxo estava escrito, com pequenas variações, em cinco prompts de design (jornada, fluxo, telas, protótipo e QA); agora mora aqui, e cada um deles o cita. O que varia por missão vem da spec: o recorte e as rotas (bloco 8), o dashboard (bloco 9) e a tabela «a mesma missão em três aulas» (bloco 8).

**O que este arquivo não é.** As telas de condução (`E4-PROF-*`, dashboard, gates de etapa) continuam por missão, desenhadas a partir da spec. E o professor **não** declara habilidades BNCC da própria disciplina: o currículo da missão continua sendo o de letramento digital.

## As cinco telas do preparo (obrigatórias)

Ambiente = `Unooria Hub (kit configuração)`. Peso `serviço` (ou `alta` para o recorte e a curadoria). Uma por passo da jornada do professor:

- `E0-PROF-01` **Escolher a missão no catálogo.**
- `E0-PROF-02` **Recorte da aula** — disciplina (em `Selection`), tema, assuntos (em lista), contexto; o banco default como alternativa (botão «usar banco padrão»). **Construída nos dois estados**, conforme o critério 4.3 (teste de posição): banco padrão em primeiro nível e recorte abaixo (missão de 1º–5º ano); recorte em primeiro nível com o banco padrão a um toque (6º ano em diante).
- `E0-PROF-03` **Geração em andamento** — progresso por polling; e o estado sem saldo de IA.
- `E0-PROF-04` **Curadoria do pacote** — prévia dos itens gerados, editar qualquer texto, regenerar item, aprovar.
- `E0-PROF-05` **Pôr a atividade no ar para a turma** — libera a missão na sala na hora; a plataforma não tem agendamento.

**Estados do preparo:** `vazio` · `gerando` · `sem saldo de IA` · `falha da geração (503)` · `pacote pronto` · `editado` · `ativado`. Nas telas (Stitch), os estados a gerar são: padrão · gerando · sem saldo · pacote pronto.

**A tela de recorte e a de curadoria saem preenchidas com uma das três aulas da tabela «a mesma missão em três aulas» do bloco 8 — uma disciplina diferente do banco default**, para que quem lê veja o que o professor de Biologia ou de História faria.

## Na jornada (Seção 1c)

Tabela própria, **colunas** = os passos do preparo no hub mais a aula: `Escolher a missão → Recorte da aula (disciplina · tema · assuntos · contexto) → Geração pela IA → Curadoria do pacote → Pôr no ar → Conduzir (gates) → Depois (relatório)`. **Raias:** Professor — vê · Professor — faz · O que muda na tela · O que a plataforma faz (geração assíncrona por polling de progresso, quota de IA e o que aparece sem saldo, banco default, congelamento do pacote) · Estado (vazio · gerando · sem saldo · pacote pronto · editado · ativado). Fonte: bloco 8 da spec (recorte, schema, rotas do preparo — gerar, homologar o pacote, pôr no ar —, curadoria) e bloco 9 (dashboard). Célula sem resposta na spec é `⚠️ lacuna` com dono `gate-estrutural`. Feche com uma linha por disciplina da tabela «a mesma missão em três aulas» do bloco 8: o que muda na tela de curadoria em cada caso (é isso que o wireframe da tela de recorte vai mostrar preenchido).

## No fluxo — o segundo grafo (obrigatório)

Em **bloco Mermaid próprio**, sob o título fixo `## Fluxo do professor (Mermaid — obrigatório)`: nós `E0-PROF-01…05` (escolher a missão · recorte da aula · geração em andamento · curadoria do pacote · pôr no ar) com os estados encostados `vazio`, `gerando`, `sem saldo de IA`, `falha da geração (503)`, `pacote pronto`, `editado`, `ativado`; a decisão `banco default × gerar com IA`, com o **caminho curto** `E0-PROF-02 -->|usar banco padrão| E0-PROF-05` como aresta própria (o critério 4.3 exige que a missão rode inteira por ele); a volta `curadoria → editar → aprovar`; o gate `ativar atividade`, cuja saída liga ao grafo do estudante pela aresta `atividade ativada → E1-ALU-01`; e os gates de condução (liberar etapa, pausar, zerar turma) com as duas saídas. Os cinco testes do fluxo valem para este grafo também. Rótulos de aresta vêm do bloco 8 da spec (`POST /<modulo>/turmas/«turmaId»/gerar-conteudo`, `GET …/conteudo`, `POST …/homologar`, `POST …/gate`) — nada inventado. O módulo `/atividades` é o motor do Instanooria e não se reusa (`formato-spec`, bloco 8).

## No protótipo — o trilho do professor (obrigatório)

Telas de professor são sempre desktop cheio, sem moldura de aparelho. **O trilho do professor é obrigatório e começa antes da aula:** `E0-PROF-01…05` navegáveis (escolher a missão → recorte da aula → geração em andamento → curadoria → ativar), com a tela de recorte e a de curadoria preenchidas com uma das três aulas da tabela do bloco 8 (disciplina diferente do banco default), e a transição «atividade ativada» levando à primeira tela do estudante. Quem revisa precisa conseguir percorrer o que o professor de Biologia ou de História faria, sem ler a spec.

## Na conferência do QA de design

- **Construídas no Stitch e no protótipo** — as cinco telas, verificadas na folha `stitch_links` e no trilho do protótipo, não só na jornada: tela do professor ausente do Stitch é ⛔ com dono `telas`.
- **O fluxo do professor existe como segundo grafo** no documento de fluxo e aparece no board do Miro (folha `miro_links`): ausência é ticket com dono `fluxo`. Botão de ativação do banco curado padrão, e o **caminho curto** `E0-PROF-01 → 02 → 05` («usar banco padrão», pulando geração e curadoria) presente como aresta própria no segundo grafo: ausência é ticket com dono `fluxo`. Em missão de 1º–5º, o banco padrão é a primeira ação visível de `E0-PROF-02` (4.3, teste de posição), senão ticket com dono `telas`.
- **Teste das três disciplinas.** A tela de recorte (`E0-PROF-02`) e a de curadoria (`E0-PROF-04`) mostram uma aula de disciplina **diferente do banco default** (tabela «a mesma missão em três aulas» do bloco 8)? As três linhas da tabela cabem no formulário sem mudar a mecânica, as cardinalidades ou a descoberta central? Formulário que só aceita um tipo de conteúdo, ou tela preenchida só com o default, é ticket com dono `telas`; mecânica que só funciona com um tipo de conteúdo é ⛔ com dono `gate-estrutural`, salvo `[LIMITE DE TRANSVERSALIDADE]` declarado na spec.
- **Simulação de preparo em minutos (missão de 1º–5º ano).** Percorra `E0-PROF-01…05` como a professora da rede municipal que não fez formação em tecnologia e conte telas, toques e decisões até `ativado`, pelo caminho curto e pelo caminho com IA; a contagem vai no relatório e confere com a seção 9a da spec (contagem de preparo, `[CONVENÇÃO]` — acordo interno, não medida: `literatura-cognitiva.md` §6 registra o preparo docente sem tempo medido).
