---
name: celulas-consumidas
description: Checklist de toda célula da spec que os agentes de design (D1–D9) e o handoff de dev vão procurar, e das seções do one-pager que o design recebe literais. Lido na varredura pelo passo de completude da spec (produto, prompt 046 — as células de produto) e pelo D0-UX (design — o que a spec deixa de UI/UX). Célula ausente aqui é lacuna que a esteira vai redescobrir seis vezes.
sources: [formato-spec, prompts/design/*, tools/conteudo_aprovado.py (SECOES_DESIGN), auditoria de 07/10/2026, test_celulas_consumidas.py]
---

# Células consumidas pela esteira

Uma linha por célula que algum agente **lê como contrato**. A varredura percorre esta lista contra a spec e marca cada linha ✅ presente · ⚠️ ausente · 🟡 ambígua. Desde 24/10/2026 (PR 6 do plano «Produto dono do contrato») ela roda duas vezes: em produto, o passo de completude da spec fecha as células de produto (estado, handoff, evidência, dados e retenção, duração e tetos, painel docente, PQ e KPI, texto do professor, revezamento) no bloco 15 da spec, antes do de acordo; no design, o D0-UX só decide o que é de UI/UX (a tela de cada estado, gesto, scaffolding, acessibilidade de componente, dispositivo) no bloco 13 do anexo de design. A coluna "Quem consome" diz quem devolveria a missão se a célula não existisse — é a mesma informação que o D0 usa na coluna "Bloqueia" dos pedidos de re-spec.

**Notação.** `bloco.campo`, com os blocos de `references/formato-spec.md`. Agentes de design: D0 fecha-lacunas · D9 ambiente simulado · D1 briefing de ofício · D2 jornada · D3 fluxo · D4 copy, passada 1 · D4b camada CAA · D5 telas · D6 copy revisada, passada 2 · D8 protótipo · D7 QA de entregáveis. Entre parênteses vai o detalhe — a seção, o teste ou, logo depois de D7, a **dimensão do QA**: `D7 (D8)` é a dimensão D8 do QA (ambiente simulado), não o protótipo. Fora do design: V1 é a implementação (handoff de dev e PRD); TEC-01 e as bancas são do gate de dev. **Lacuna do consumidor** marca o agente que deveria ler a célula e cujo prompt não diz como; a lista está no fim. O D0 roteia a lacuna a ele mesmo assim — o conserto é no prompt, não na spec.

**O que entra na varredura.**
- **Blocos 0–12 e o `## Glossário canônico`** — o texto do Gate 0, célula a célula.
- **Conteúdo aprovado** — as seções do one-pager que a esteira copia literais para o design. Não são células: cada linha diz em que célula da spec a seção se espelha. Quando a célula-espelho falta, a seção é a base do preenchimento (`one-pager §N`).
- **Blocos 13, 14 e 15 não entram.** O 15 é a saída do passo de completude (spec de produto); o 13 é a saída do próprio D0 e o 14 é escrito pelo D9, que roda depois — os dois no anexo de design, fora da spec. O 13 e o 14 estão aqui para dizer de que célula cada campo herda a lacuna e quem os lê.

## Bloco 0 — Identificação de plataforma

| Célula | Quem consome | Sem ela |
|---|---|---|
| 0.slug `expNNefNb` (o `id` da ficha) | todos (envelope `missao`), artefatos, V1 | Arquivos e envelopes sem identificador |
| 0.nome que o estudante vê | D4, D7 | Copy sem título canônico |
| 0.série(s) no formato da plataforma | D2 (tetos), D4 (registro por faixa), D4b (gate CAA), D7 (D6 e D6b: regras do 1º–5º), D9 (Passada 1b) | Ninguém sabe a faixa; tetos e CAA não decidem |
| 0.software clonado + **seção do DS** | D9 (dormente ou não), D2, D5, D7 (D8) | D9 decide; se nem D9 puder, é vermelho |
| 0.viewport (celular 375×812 dentro do desktop · desktop cheio) e por quê | D2 (cenários), D5 (frames e `deviceType` do Stitch), D8 (moldura de aparelho ou janela do hub), D9 | Frames no tamanho errado; quem revisa o protótipo mede a tela errada |
| 0.produto (`entre-redes` …) e 0.unidade (1–4) — ficha do manifesto | V1, `ManifestoCheck`, TEC-01 | O CI recusa o manifesto (ADR-87) e a grade da sala não ordena (ADR-69) |
| 0.permissoes do iframe (`forms`, `pointer-lock`, `downloads`) | D5, V1, TEC-01 | Submit ou download bloqueado em silêncio pelo sandbox |
| 0.liberacao por turma (ADR-69) — linha opcional | V1 (`exigirMissaoLiberada`; manifesto do handoff de dev) | Nada: ausente vale `por-turma`, o default e único valor aceito — não é lacuna. Nenhum agente de design lê a célula: o «pôr no ar» (`E0-PROF-05`) de jornada, fluxo, copy, telas e protótipo é fixo nos prompts (libera na hora, sem agendamento) |

## Bloco 1 — Descoberta central

| Célula | Quem consome | Sem ela |
|---|---|---|
| 1.frase única da descoberta | D1 (aposta, forma do arco), D9 (Passada 1b condição 3) | Briefing sem eixo; tudo vira "mecânica" |
| 1.beat exato em que é vivida | D1 (PICO/AHA), D2 (tela do aha) | Aha sem tela |

## Bloco 2 — Mecanismo por etapa

| Célula | Quem consome | Sem ela |
|---|---|---|
| 2.etapa N: o que o sistema apresenta · ordena · bloqueia · garante (N = 1–6) | D1 (mecanismo por beat), D2 (raias), D3 (estados), D8 (painel da etapa quando o one-pager cala; tempos dos momentos scriptados, teste 8), D9 (mini-jogo: o tipo de jogo carrega a mecânica; intervalo de fases) | Beat sem mecanismo — classe "não-negociável sem mecanismo" |
| 2.regra de sequência onde a descoberta depende de ordem | D2, D3 | Fluxo aceita qualquer ordem |
| 2.contrato de estados: uma linha por transição (inicial, gatilho, regra, seguinte, responsável) | D3 (nós e arestas; inclui o estado da pergunta do Canal B entre o Refletir e a conclusão), V1 (enum) | Grafo inventa estados `DEC_*`/`DEG_*` sem base |
| 2.estados com nome próprio | D3, D5 (frame por estado), V1 | Estado sem nome não vira frame nem enum |
| 2.frase que fecha o conjunto ("não existem outros caminhos…") | D3 (teste 1 e 2) | Grafo sem fechamento |
| 2.conclusão: quem fecha, o que congela, o que reporta, o que ainda é permitido | D3, D5 (tela de congelamento sem affordance), D8 (tela de congelamento: só a saída declarada da demo, teste 5), D7 (D6: controle de avanço e congelamento) | Tela final com botão que não devia existir |
| 2.estados latch / trava síncrona | D2 (raia da professora), D3, D5 | Trava desenhada com escape |
| 2.reentrada (F5, voltar noutro dia) | D3 (aresta de retorno), V1 | Teste 5 do fluxo sem resposta |
| 2.segunda aplicação (re-sorteia · preserva · "zerar turma" apaga) | D3, V1 | Estado de turma indefinido |
| 2.modos de erro **na voz da ficção**, como estado próprio (conexão, sessão expirada, mídia) | D3 (nós vermelhos), D4 (strings de falha), D5 (frames de falha), D6 (item 6: string própria por estado), D7 (D5: estados de erro existem), D9 (mini-jogo: falhas dentro da casca) | Erro genérico do sistema no meio do clone — DES-13 |
| 2.falha de mídia: imagem, áudio ou vídeo que não carrega — o que a criança vê na voz da ficção, o que faz, o que se preserva (one-pager §8) | D3 (nó próprio com aresta de volta), D4 e D6 (string da falha), D5 (frame de falha), D4b (prancha imprimível para falha de áudio), D7 (D5), V1 (grau `none` no bloco 9) | Tela de mídia sem estado de falha: até 07/10/2026 a falha de mídia do §8 não chegava a tela nenhuma |
| 2.estado de espera de professor em toda tela ligada a handoff | D2, D5 (estado "Espera de professor"), D6 (item 6: string própria) | Criança sem tela enquanto a professora fala |

## Bloco 3 — Caminhos degenerados

| Célula | Quem consome | Sem ela |
|---|---|---|
| 3.não escolheu nada → o que acontece · etapa preservada? | D3 (rota), D5 (estado vazio) | Teste 3 do fluxo falha |
| 3.escolheu tudo | D3, D5 | idem |
| 3.não usou a ferramenta | D3, D5 | idem |
| 3.exploração mínima | D3, D5 | idem |
| 3.terminou antes | D3 (o que faz enquanto espera), D2 (raia) | Espera passiva sem tela |

## Bloco 4 — Verbos e affordances

| Célula | Quem consome | Sem ela |
|---|---|---|
| 4.lista de verbos nativos confirmados (antes / verbo / depois) | D2 (raia "Estudante — faz"), D4 (rótulo literal), D4b (affordance nativa como CAA), D9 (Passada 1 e 1b), D7 (D8) | Verbo inventado na jornada; D9 não consegue testar o ambiente |
| 4.affordance por verbo (o que na tela dispara o verbo) | D5 (componente), D4b (modo de resposta) | Wireframe sem alvo de toque definido |

## Bloco 5 — Ausências declaradas

| Célula | Quem consome | Sem ela |
|---|---|---|
| 5.o que o ambiente simulado NÃO tem, com o motivo de cada ausência | D1 ("sai de propósito"), D4 (ausência de áudio → `texto+ícone`), D4b (ausência de áudio → pictograma + texto), D5 (não completar por realismo), D6 (nada de texto para o ausente), D7 (D1, D7 e D8: ausência que reapareceu), D8 (monta o chrome e as ausências da spec) | Alguém "completa" a interface e a fidelidade cai; a copy marca áudio numa spec de "zero áudio" (exp01ef1b: 39 strings) |

## Bloco 6 — Tetos aplicados

| Célula | Quem consome | Sem ela |
|---|---|---|
| 6.contagem de decisões do mesmo tipo (com a conta) | D2 (cap de decisões), D7 (recontagem por frame), D9 (cap não pode mudar) | Contagem infla no wireframe sem que ninguém perceba |
| 6.duração por ato | D1 (pico em que minuto; minutos até a primeira ação), D7 (D4: duração dos atos com a leitura construída; D7: minutos até a primeira ação) | Ritmo sem teto. A jornada não tem campo de tempo: esta lacuna não se roteia ao D2 |
| 6.tempos e formatos de aula copiados do §10: tabela por etapa (em tela · fora da tela), `Em tela: <n> min`, checkpoints e cenários de aula (aula única · duas aulas · sessões fracionadas) | D2 (coluna ⟨CHECKPOINT / PAUSA DOCENTE⟩ quando há divisão de aulas ou pausa), D3 (checkpoints e cenários de aula viram estados e arestas — lê o §10 no conteúdo aprovado), D7 (D5: checkpoints modulares e salvamento de estado) | Missão de duas aulas sem ponto de retomada; o tempo em tela muda sem o PO (exp06ef1b: de 29 para 24 min) |
| 6.etapas cognitivas por decisão | D2 (peso da tela), D4 (teto de palavras) | Densidade uniforme |
| 6.onde há scaffolding e onde a dica desaparece | D2, D5 (estado "Primeira vez com scaffolding"), D4b, D7 (D4: scaffolding no primeiro uso) | Apoio desenhado onde não devia, ou ausente onde devia |

## Bloco 7 — Acessibilidade

| Célula | Quem consome | Sem ela |
|---|---|---|
| 7.canais por instrução (áudio · pictograma · texto) | D4 (`texto+ícone+áudio` em anos iniciais — **exceto** quando a spec declara ausência de áudio, no bloco 5 ou no 14: aí `texto+ícone` e a pendência `[ABERTO — dono]` com dono PO em «Strings que precisam de decisão»), D4b (pictograma + áudio), D5 (botão de áudio, quando a copy o pede), D6 (item 4: a redundância sobreviveu ao build), D7 (D4: redundância em anos iniciais) | Instrução só escrita para quem não lê; ou áudio prescrito numa spec sem áudio, que o PRD veta |
| 7.teto de palavras por string | D4, D6, D7 (D4: teto por string) | Strings sem régua |
| 7.gestos que exigem demonstração animada | D5, D4b | Gesto sem demonstração |

## Bloco 8 — Professora, preparação e parametrização com IA

| Célula | Quem consome | Sem ela |
|---|---|---|
| 8.recorte da aula: `disciplina` (lista fechada) · `tema` · `assuntos` (3 a 6) · `contexto` e `foco` opcionais, com os tetos de caracteres | D2 (Seção 1c e raia "Preparação docente"), D4 (rótulos e ajuda do recorte), D5 (`E0-PROF-02`), D8 (trilho do professor), D7 (D6 e D6c), V1 | Tela de recorte sem campos; prompt de IA sem o teto que é a primeira barreira contra injeção |
| 8.regras e schemas de geração de conteúdo por IA + banco curado default | D4 (schema que os prompts preenchem; amostras do banco), D6 (reemite prompts, schemas e banco sem mudança), D7 (D1b: dinâmico vs fixo) | Copy não separa string fixa de conteúdo gerado; a revisão descartava prompts e banco em 8 de 8 sessões (07/10/2026) |
| 8.caminho curto pelo banco default — o professor toca só «usar banco padrão» (critério 4.3) | D2 (`E0-PROF-02` com o banco como alternativa), D3 (aresta própria `E0-PROF-02 → E0-PROF-05`), D5 (posição do botão por faixa), D7 (D6 e D6b: telas e toques do preparo) | A missão não roda sem IA e o 4.3 reprova |
| 8.fluxo de curadoria docente (prévia, edição de qualquer texto, regenerar item, aprovação antes da aula) | D2 (Seção 1c), D3 (volta curadoria → editar → aprovar), D4 (textos de editar, regenerar, aprovar), D5 (`E0-PROF-04`), D8 (trilho do professor), D7 (D6 e D6c) | Tela docente sem estados |
| 8.tabela «A mesma missão em três aulas» (Português, Ciências/Biologia, História: recorte · o que a IA gera · o que não muda), ou o marcador `[LIMITE DE TRANSVERSALIDADE — dono: produto]` (one-pager §9b) | D2 (a Seção 1c fecha com uma linha por disciplina), D4 (o recorte de cada aula como amostra), D5 (recorte e curadoria preenchidos com uma aula fora do banco default), D8 (trilho do professor preenchido do mesmo jeito), D7 (D6c: teste das três disciplinas) | Tela de recorte preenchida só com o default; a transversalidade não é testada |
| 8.perfil de quota de IA (`ia_quotas`, ADR-105) e o que se vê sem saldo (429) ou com a geração em falha, na voz da ficção | D2 (raia "O que a plataforma faz"; estado `sem saldo`), D3 (estados `sem saldo de IA` e `falha da geração (503)`), D4 (mensagens de geração, de falha e de saldo esgotado), D5 (`E0-PROF-03` sem saldo), D2 (o estudante sem saldo de IA) | Professor sem saída quando o saldo acaba; erro técnico cru na tela |
| 8.rotas do preparo docente no módulo da missão: `gerar-conteudo` → `conteudo` → `homologar` → `gate`, com o painel em `…/painel` (nunca `/atividades`) | D2 (Seção 1c: fonte do preparo), D3 (rótulos das arestas do fluxo do professor — do módulo da missão), V1 | Fluxo do professor rotulado com rota que não existe |
| 8.gatilhos de handoff: o que aciona a entrada da professora | D2 (raias cruzadas), D3 (aresta condicionada), D4 (instruções de gatilho, uma linha por momento), D5 (estado de espera), D7 (D6: gatilho em tela) | Handoff sem gatilho — classe `handoff` |
| 8.comportamento da plataforma em cada mediação (pausa · continua · trava) | D2, D3, D5, D7 (D6: mediação e pausas em sala) | Trava sem contrato |
| 8.controles do professor durante a aula — liberar etapa · pausar · congelar · zerar turma — e o relógio coletivo (`expNNefNb_gates_turma` por polling, ADR-93/94, nunca WebSocket), no momento que o §10 define | D2 (⟨CHECKPOINT / PAUSA DOCENTE⟩; raia "Professor"), D3 (gates de condução com as duas saídas; travas e liberações do §9 e do §10 viram estados), D5 (controles de handoff; travas na tela do professor), D8 (marca «trava» na barra superior), D7 (D6: controle de avanço e congelamento) | Travas do professor perdidas, como na exp01ef1b |
| 8.dados do painel docente | D2 (tela docente), D4 (leitura do dashboard em linguagem de sala de aula), D5 (dashboard da condução, 4.4), D7 (D6: os dados da raia de evidência, nada além, nada a menos), V1 | Painel vazio |
| 8.roteiro de perguntas do debate (≥ 3, escritas, no momento em que o one-pager o coloca) | D4 (copy-fonte da professora), D4b (lido em voz alta como está, conteúdo aprovado §9), D6 (copiado palavra por palavra do conteúdo aprovado §9), D8 (indireto: reproduz a copy revisada caractere a caractere), D7 (D6: roteiro ≥ 3) | Professora inventa a mediação — classe `copy-fonte`; na exp01ef1b a spec reescreveu a pergunta 1 |
| 8.podcast de recapitulação: título, vozes, duração, quando toca, quem toca e o aviso ao professor (o roteiro fica no §11) | D4 (falas do §11 literais, pelo one-pager), D6 (mantém as falas; revisa só a voz), D7 (o que o PO aprovou e o design perdeu) | Nenhuma das 11 specs do bucket até 06/10/2026 trazia o podcast; design e brief de assets reescreveram o áudio |

## Bloco 9 — Evidências e dados

| Célula | Quem consome | Sem ela |
|---|---|---|
| 9.campo por campo: o que é coletado, quando, finalidade, retenção, acesso | D2 (raia "Evidência capturada"), D7 (D3: nada fora do bloco 9), V1, banca DAD | Coleta aparece no wireframe sem contrato |
| 9.lista do que **não** é coletado nem calculado | D5, D7 | Campo de nome, voz ou imagem entra "por engano" |
| 9.grau de medida por medida (`scored` · `indicative` · `zero` · `none`) | D5 (evidência individual com o grau ao lado), V1, banca DAD | Criança que não teve a chance conta como recusa |
| 9.canal por dado (operacional · analítico) | V1 | Latência e ordem indefinidas |
| 9.texto livre de menor: existe? por quê? quem lê? | D4 (campo de reflexão), D7, banca DAD | Reflexão do 1.6 sem destino |
| 9.segredo de servidor (gabarito, parâmetros, prompt) | V1, banca TEC | Gabarito no bundle |
| 9.tabela de eventos `track(verbo, objeto, resultado, contexto)`: verbo · objeto · quando dispara · resultado · contexto · caminho · onde é lido | D5 (seção «Interações instrumentadas»), V1 | Interação que vira dado redesenhada sem avisar quem a lê; evento sem leitor |
| 9.pergunta de evidência (Canal B): a pergunta e as três alternativas literais do §12a, o nível de cada uma (só no servidor), o componente que a renderiza e o retorno «resposta enviada» | D4b (lida em voz alta, sem paráfrase), D6 (copiada palavra por palavra), D7 (confere contra o conteúdo aprovado), V1, D2 (tela própria da pergunta) | A camada CAA parafraseia as alternativas (exp01ef1b); o nível vaza para o cliente |

## Bloco 10 — Cenários de dispositivo

| Célula | Quem consome | Sem ela |
|---|---|---|
| 10.cenário 1:1 — o que muda · a descoberta chega? | D2 (coluna "Cenário"), D5, D7 (D5: três cenários construídos) | Célula "descoberta chega?" em branco |
| 10.cenário 2–4 por aparelho — o que muda · a descoberta chega? | D2, D4b (prancha imprimível para dispositivo compartilhado), D5 (estado "Degradado"), D6 (string do estado degradado), D7 (D5) | idem |
| 10.cenário projeção única — o que muda · a descoberta chega? | D2, D5 (1366×768, `DESKTOP`), D4b (88×88), D8 (desktop cheio; alvo de 88 px), D7 (D4a: alvo ≥ 88×88 na projeção) | idem |

## Bloco 11 — Currículo

| Célula | Quem consome | Sem ela |
|---|---|---|
| 11.habilidades e códigos confirmados | D2 (coluna "Habilidade"), D7 (D2 curricular), D9 (mini-jogo: uma por fase) | Tela sem momento em tela; fase vira enfeite |
| 11.momento em tela de cada habilidade | D2, D7 | QA e banca inferem — e inferência é achado |
| 11.qual código é o de **letramento digital** (Cultura Digital) | D7 (confere em `references/bncc-computacao-letramento-digital.md`) | Código de outro eixo passa como núcleo |

## Bloco 12 — Decisões fechadas neste gate

| Célula | Quem consome | Sem ela |
|---|---|---|
| 12.decisão · quem decidiu · data · alternativas descartadas | D0 (não repetir como lacuna o que foi decidido), D7 (pendências herdadas) | D0 reabre o que o Gate 0 fechou |
| 12.decisão em aberto — `[ABERTO — dono]` no bloco 12 e no campo afetado | D0 (é a lista inicial de lacunas; fecha com uma linha no mapa célula → D0 do bloco 13), D7 (pendências humanas herdadas), rastro de lacunas (`A092RastroDesign` cobra a linha até o mapa do D0) | Lacuna sem dono; a pendência que o D0 fechou volta a barrar o design e o PRD |

## Glossário canônico

| Célula | Quem consome | Sem ela |
|---|---|---|
| Glossário.Entidades — nome canônico e variantes proibidas | coerência entre documentos (`A082Consistencia`, sobre jornada, fluxo, copy revisada e protótipo), D7 (lê esse relatório e endereça o ticket ao dono), D0 e D9 (copiam o glossário intocado) | O órgão com quatro nomes da exp09ef1b passa, porque ninguém lê os documentos juntos |
| Glossário.Personagens — nome, idade, papel na história | `A082Consistencia`, D7, D0 e D9, como acima · construção: D2, D3, D4, D6, D8 | O beneficiário de 14 anos vira coordenador na copy (exp09ef1b) |
| Glossário.Números — o quê, valor, unidade | `A082Consistencia`, D7, D0 e D9, como acima · construção: D2, D3, D4, D6, D8 | O mesmo número com duas unidades em dois documentos |
| Glossário.Rótulos de botão por ação | `A082Consistencia`, D7, D0 e D9, como acima · construção: D2, D3, D4, D6, D8 | A mesma ação com dois rótulos de botão (exp09ef1b: seis) |
| Glossário.Arquivos — artefato e nome do arquivo | `A082Consistencia` e a conferência das afirmações do QA (`A089QaAfirmacoes`), D7, D0 e D9 | QA e protótipo citam arquivo que a esteira não grava |

## Conteúdo aprovado — seções do one-pager copiadas literais para o design

O `A064ConteudoAprovadoDesign` copia estas seções, sem reescrita, para `conteudo_aprovado`, cada uma sob o título `## <título> — one-pager §N`. Fluxo, CAA, telas, copy revisada e QA as recebem porque não leem o one-pager; para o que a missão ensina e mede, os textos literais, os tempos e o papel do professor, vale este texto quando a spec diverge. Jornada e copy (passada 1) leem as mesmas seções no one-pager inteiro.

| Célula | Quem consome | Sem ela |
|---|---|---|
| §0 Identificação — espelho: bloco 0 | D7 (série, faixa e produto conferidos contra o design) | A série e o público só chegavam pela ficha da spec |
| §1 Descoberta central e anatomia do aha (1.1 conceitos vividos em tela, 1.2 anatomia do aha, 1.3 conta da virada) — espelho: bloco 1 | D3 (a virada vira o estado do pico), D5 (a tela do aha mostra a consequência que a 1.2 descreve), D7 (D2: a virada chega à tela) | A virada e os números do núcleo só chegavam pela spec; o banco de conteúdo lia o núcleo de antes da revisão do one-pager |
| §2 Currículo — espelho: bloco 11 | D7 (D2 curricular; confere o design contra o aprovado) | O código que o PO aprovou some (exp06ef1b perdeu a EF06CO07 seguindo um parecer que o PO recusou) |
| §3 Narrativa e personagem-guia — espelho: bloco 1 e glossário canônico | D4b (a voz da personagem na prancha), D6 (falas da personagem palavra por palavra), D7 | O nome e a voz da personagem mudavam de um documento para outro |
| §4 As 6 etapas — mecanismo e o que a tela mostra — espelho: bloco 2 | D3 (o que acontece em cada etapa e em que ordem; o detalhe de estado segue a spec), D4b (a pergunta da aposta e as alternativas na prancha), D5 (o texto entre aspas é o que a tela exibe), D6 (texto de tela palavra por palavra), D7 (confere contra o conteúdo aprovado) | A spec levava 81 de 153 textos de tela do §4 nas dez sessões de outubro, e o protótipo de 18% a 45% (07/10/2026) |
| §5 Verificação de ambiente — espelho: bloco 14 (ficha do ambiente) | D3 (o que o ambiente permite vira aresta), D5 (os escapes nativos que a tela mostra), D7 | As affordances e os escapes que o PO aprovou só chegavam pela ficha do D9 |
| §6 Verbos e affordances — espelho: bloco 4 | D3 (cada gesto vira aresta), D4b (modo de resposta alternativo ao gesto), D5 (a affordance aparece na tela), D7 | O gesto que o one-pager aprovou trocava de forma entre fluxo e telas |
| §7 Caminhos degenerados — espelho: bloco 3 | D3 (cada caminho degenerado vira aresta de tratamento), D5 (o estado de tela do tratamento), D6 (a copy do tratamento), D7 | A spec levava 26 de 41 textos do §7 (dez sessões de outubro); fluxo e telas os viam só por ela |
| §8 Estados de falha — espelho: 2.modos de erro e 2.falha de mídia | D3 (nós de falha), D4b (falha de áudio → prancha), D5 (frame de falha), D6 (string por estado de falha), D7 (D5) | A falha de mídia não chegava a tela nenhuma (07/10/2026) |
| §9 Papel do professor e parametrização com IA (9a preparo, 9b três aulas, roteiro do debate) — espelho: bloco 8 | D3 (travas e liberações viram estados e arestas), D4b (perguntas do debate lidas como estão), D5 (telas do professor: preparo, travas, painel), D6 (perguntas do debate palavra por palavra), D7 (D6b: contagem de preparo do 9a) | Na exp01ef1b se perderam as travas do professor e a redação do debate |
| §10 Modularidade, tempos sugeridos e controle do professor — espelho: 6.tempos e formatos de aula | D3 (checkpoints e cenários de aula), D7 (D4 e D5: duração e checkpoints) | O tempo em tela muda sem o PO (exp06ef1b: 29 → 24 min; exp04ef1b: 29 → 25) |
| §11 Podcast de recapitulação — espelho: 8.podcast | D4 (falas literais, pelo one-pager), D6 (falas palavra por palavra), D7 | A copy reescreve as falas (exp01ef1b: as 9) e o banco grava outro roteiro |
| §12 Evidências e dados, com o contrato de evidência por habilidade (12a, Canal B) — espelho: bloco 9 e matriz do bloco 11 | D4b (Canal B sem paráfrase), D6 (Canal B palavra por palavra), D7 | O Canal B se perde no caminho (exp06ef1b: nenhuma das quatro perguntas chegou ao PRD) |
| §13 Cenários de dispositivo — espelho: bloco 10 | D2 (pelo one-pager, como contexto), D4b (dispositivo compartilhado e projeção), D5 (degradado e projeção), D7 (D5: três cenários) | Fluxo, CAA, telas e QA não liam projeção nem 2 a 4 por aparelho (07/10/2026) |
| §14 Guardrails e IA — espelho: bloco 5 (ausências declaradas) e bloco 8 (IA) | D6 (sem rótulo pejorativo, sem ranking, o que a IA não diz), D7 | A spec levava 2 de 11 textos do §14 (dez sessões de outubro) |
| §15 Tetos aplicados à faixa — espelho: bloco 6 | D5 (densidade por tela), D6 (teto de palavras por string), D7 | A revisão da copy não via o teto da faixa que o PO aprovou |
| §16 Requisitos técnicos e escopo — espelho: bloco 0 e escopo V1/V2 do bloco 12 | D5 (o que a V1 tem em tela), D7 (escopo V1 × V2 conferido no design) | O escopo V1/V2 que o PO aprovou não chegava ao design nem à banca |
| §17 Hipóteses de validação — sem espelho na spec | D7 (cada hipótese com a tela ou o evento que a observa) | — |
| §18 Decisões de direção, trade-offs e propostas — espelho: bloco 12 | D3, D5, D6 (o trade-off que o PO aceitou não se desfaz no design), D7 (as `[PROPOSTA]` seguem marcadas) | Os trade-offs aprovados e as propostas pendentes só chegavam pela spec |

## Bloco 15 — Completude de produto

Fora da varredura: é a saída do passo de completude da spec, em produto (desde 24/10/2026). Fica na spec de produto, e o PO o aprova no de acordo com o resto.

| Célula | Quem consome | Sem ela |
|---|---|---|
| 15.decisões `[CP-n]` — célula de produto preenchida, decisão, base declarada | D0 (o que o bloco respondeu não se decide de novo), D9 (copia intocado), D1, D2, D3, D4, D5, D7 (leem a célula preenchida como contrato), V1, rastro de lacunas (o mapa célula → decisão só fecha com o `[CP-n]` aqui), gate de `[CP-n]` órfão | O design volta a decidir produto; a pendência fechada volta a barrar |
| 15.padrões da plataforma aplicados | D0 (não reaplica), D7, V1 | O mesmo padrão aplicado duas vezes, com textos diferentes |
| 15.perguntas ao PO — `[PARÂMETRO]`, `[PROPOSTA]`, `[ABERTO — dono: PO]` com a sugestão | D0 (usa a sugestão como pendente, nunca a fecha), D7, V1 | O design decide no lugar do PO |

## Bloco 13 — Decisões D0

Fora da varredura: é a saída do próprio D0.

| Célula | Quem consome | Sem ela |
|---|---|---|
| 13.decisões `[D0-n]` — célula preenchida, decisão, base, reversível | todos de D1 a D8 (leem a célula preenchida como contrato), D9 (copia o bloco palavra por palavra, teste 4b), D7 (`[D0-n]` que contraria a spec original vira ticket `fecha-lacunas`), rastro de lacunas (o mapa célula → D0 só fecha com o `[D0-n]` aqui), gate de `[D0-n]` órfão (toda citação a jusante precisa existir aqui) | A jusante cita decisão que a spec não tem; a pendência fechada volta a barrar |
| 13.`RS-n` pendentes — re-spec que o Gate 0 não respondeu | D7 (riscos aceitos; `RS-n` negado e contornado, ou pendente e honrado pela tela, é ⛔), rastro de lacunas | Os agentes a jusante redescobrem a lacuna, um por um |

## Bloco 14 — Ambiente simulado

Fora da varredura: o D9 escreve o bloco depois do D0. Cada campo herda de uma célula dos blocos 0–5 — lacuna lá é lacuna aqui, e o D0 a roteia pela célula de origem.

| Célula | Quem consome | Sem ela |
|---|---|---|
| 14.verbos do bloco 4 → rótulo literal na tela → componente do DS (origem: 4.lista de verbos) | D2 (raia "Estudante — faz"), D4 (rótulo caractere a caractere), D5 (componente), D8 (rótulos nativos), D7 (D8: rótulo literal) | Verbo reescrito na copy; componente inventado |
| 14.seção do DS e chrome (origem: 0.software clonado + seção do DS) | D2 (o chrome que o ambiente já tem), D5 (importa a seção), D8 (chrome do app clonado), D7 (D8: a seção importada é a decidida) | Barra de abas desenhada do zero |
| 14.padrão de conteúdo e schema mínimo | D4 (schema mínimo dos prompts de geração) | Prompt de geração com campo que o ambiente não tem |
| 14.estados que a seção já traz (vazio · carregando · falha de conexão · degradado) | D2 (estados do inventário) | Estado redesenhado que o ambiente já tinha |
| 14.o que a plataforma real não tem (origem: bloco 5) | D1 (sai de propósito), D4 (ausência de áudio declarada → `texto+ícone`), D5 (o que o ambiente não tem), D6 e D8 (nada do que é ausente), D7 (D8: continua ausente) | O ambiente "completo" volta pela tela ou pela copy |
| 14.mini-jogo: tipo de jogo, fase, vitória, derrota, mapa de mundo, demonstração, e o pedido à jornada (intervalo de fases, uma habilidade do bloco 11 por fase) | D2 (Seção 5: regras e fases), D3 (fase = nó com três estados; `perdida` nunca vai ao início), D4 (strings do jogo, seção `unooria`), D4b (o verbo do jogo é a affordance nativa), D5 (frames de fase, mapa e demonstração), D7 (D8c) | Área de jogo vazia no wireframe; o dev inventa a regra |

## Lacunas conhecidas dos consumidores

O consumidor existe e a célula chega a ele, mas o prompt dele não diz o que fazer com ela. O D0 roteia a lacuna mesmo assim; o conserto é no prompt.

Nenhuma aberta. As oito achadas em 07/10/2026 foram fechadas nos prompts no mesmo dia: §8 e §13 anunciados no conteúdo aprovado (D3, D4b, D5, D6, D7); exceção de ausência de áudio também na CAA, na copy revisada e no QA; ausências proibidas na copy revisada e no protótipo; glossário declarado em jornada, fluxo, copy e protótipo; o que o estudante vê sem saldo de IA e a tela própria da pergunta do Canal B na jornada; rótulos de rota do módulo da missão no fluxo do professor; hipóteses do §17 com tela ou evento que as observa, no QA.

## Regra de manutenção

Linha nova entra quando um agente de construção **devolveu** por falta dela — o `aprendizado` registra a recorrência e propõe a linha — ou quando um prompt de design passa a ler a célula. O segundo caso é cobrado por `test_celulas_consumidas.py`: prompt de design que cita um bloco sem linha que o aponte, agente citado que não existe, bloco que o formato da spec não tem e seção do conteúdo aprovado sem linha falham o teste. Célula que nenhum agente consome sai: checklist que ninguém lê treina o D0 a preencher o que ninguém pediu.
