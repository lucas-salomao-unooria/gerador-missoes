---
name: celulas-consumidas
description: Checklist de toda célula da spec que os agentes de design (D1–D7) e o handoff de dev vão procurar. Lido pelo fecha-lacunas na varredura (Passo 1). Célula ausente aqui é lacuna que a esteira vai redescobrir seis vezes.
sources: [formato-spec, prompts d1–d7, v1]
---

# Células consumidas pela esteira

Uma linha por célula que algum agente **lê como contrato**. A varredura do D0 percorre esta lista contra a spec e marca cada linha ✅ presente · ⚠️ ausente · 🟡 ambígua. A coluna "Quem consome" diz quem devolveria a missão se a célula não existisse — é a mesma informação que o D0 usa na coluna "Bloqueia" dos pedidos de re-spec.

Notação: `bloco.campo`. Blocos são os de `references/formato-spec.md` (0–12). O bloco 13 (Decisões D0) e o bloco 14 (Ambiente simulado, D9) são acrescentados pela própria esteira e não entram na varredura.

## Bloco 0 — Identificação de plataforma

| Célula | Quem consome | Sem ela |
|---|---|---|
| 0.slug `exp-NN-<nome>` | todos (envelope `missao`), artefatos, V1 | Arquivos e envelopes sem identificador |
| 0.nome que o estudante vê | D4, D7 | Copy sem título canônico |
| 0.série(s) no formato da plataforma | D2 (tetos), D4 (registro por faixa), D4b (gate CAA), D9 (Passada 1b) | Ninguém sabe a faixa; tetos e CAA não decidem |
| 0.unidade da trilha / bimestre | catálogo, V1 | Diferenciação 2.5 e bimestre do card sem base |
| 0.software clonado + **seção do DS** | D9 (dormente ou não), D2, D5, D7 (D8) | D9 decide; se nem D9 puder, é vermelho |
| 0.viewport (celular 375×812 dentro do desktop · desktop cheio) e por quê | D2 (cenários), D5 (frames), D9 | Frames no tamanho errado |

## Bloco 1 — Descoberta central

| Célula | Quem consome | Sem ela |
|---|---|---|
| 1.frase única da descoberta | D1 (aposta, forma do arco), D9 (Passada 1b condição 3) | Briefing sem eixo; tudo vira "mecânica" |
| 1.beat exato em que é vivida | D1 (PICO/AHA), D2 (tela do aha) | Aha sem tela |

## Bloco 2 — Mecanismo por etapa

| Célula | Quem consome | Sem ela |
|---|---|---|
| 2.etapa N: o que o sistema apresenta · ordena · bloqueia · garante (N = 1–6) | D1 (mecanismo por beat), D2 (raias), D3 (estados) | Beat sem mecanismo — classe "não-negociável sem mecanismo" |
| 2.regra de sequência onde a descoberta depende de ordem | D2, D3 | Fluxo aceita qualquer ordem |
| 2.contrato de estados: uma linha por transição (inicial, gatilho, regra, seguinte, responsável) | D3 (nós e arestas), V1 (enum) | Grafo inventa estados `DEC_*`/`DEG_*` sem base |
| 2.estados com nome próprio | D3, D5 (frame por estado), V1 | Estado sem nome não vira frame nem enum |
| 2.frase que fecha o conjunto ("não existem outros caminhos…") | D3 (teste 1 e 2) | Grafo sem fechamento |
| 2.conclusão: quem fecha, o que congela, o que reporta, o que ainda é permitido | D3, D5 (tela de congelamento sem affordance) | Tela final com botão que não devia existir |
| 2.estados latch / trava síncrona | D2 (raia da professora), D3, D5 | Trava desenhada com escape |
| 2.reentrada (F5, voltar noutro dia) | D3 (aresta de retorno), V1 | Teste 5 do fluxo sem resposta |
| 2.segunda aplicação (re-sorteia · preserva · "zerar turma" apaga) | D3, V1 | Estado de turma indefinido |
| 2.modos de erro **na voz da ficção**, como estado próprio (conexão, sessão expirada, mídia) | D3 (nós vermelhos), D4 (strings de falha), D5 (frames de falha) | Erro genérico do sistema no meio do clone — DES-13 |
| 2.estado de espera de professor em toda tela ligada a handoff | D2, D5 (estado "Espera de professor") | Criança sem tela enquanto a professora fala |

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
| 4.lista de verbos nativos confirmados (antes / verbo / depois) | D2 (raia "Estudante — faz"), D4 (rótulo literal), D4b (affordance nativa como CAA), D9 (Passada 1 e 1b), D7 (D8) | Verbo inventado na jornada; D9 não consegue testar os cinco ambientes |
| 4.affordance por verbo (o que na tela dispara o verbo) | D5 (componente), D4b (modo de resposta) | Wireframe sem alvo de toque definido |

## Bloco 5 — Ausências declaradas

| Célula | Quem consome | Sem ela |
|---|---|---|
| 5.o que o ambiente simulado NÃO tem, com o motivo de cada ausência | D1 ("sai de propósito"), D5 (não completar por realismo), D7 (fidelidade) | Alguém "completa" a interface e a fidelidade cai |

## Bloco 6 — Tetos aplicados

| Célula | Quem consome | Sem ela |
|---|---|---|
| 6.contagem de decisões do mesmo tipo (com a conta) | D2 (cap de decisões), D7 (recontagem por frame), D9 (cap não pode mudar) | Contagem infla no wireframe sem que ninguém perceba |
| 6.duração por ato | D1 (minutos até a primeira ação), D2, D7 | Ritmo sem teto |
| 6.etapas cognitivas por decisão | D2 (peso da tela), D4 (teto de palavras) | Densidade uniforme |
| 6.onde há scaffolding e onde a dica desaparece | D2, D5 (estado "Primeira vez com scaffolding"), D4b | Apoio desenhado onde não devia, ou ausente onde devia |

## Bloco 7 — Acessibilidade

| Célula | Quem consome | Sem ela |
|---|---|---|
| 7.canais por instrução (áudio · pictograma · texto) | D4 (`texto+ícone+áudio` em anos iniciais), D4b, D5 (botão de áudio) | Instrução só escrita para quem não lê |
| 7.teto de palavras por string | D4, D6 | Strings sem régua |
| 7.gestos que exigem demonstração animada | D5, D4b | Gesto sem demonstração |

## Bloco 8 — Professora, preparação e parametrização com IA

| Célula | Quem consome | Sem ela |
|---|---|---|
| 8.inputs aceitos da professora (tema, foco, contexto) | D2 (raia da professora), V1 | Painel docente sem campos |
| 8.regras e schemas de geração de conteúdo por IA + banco curado default | D4 (schema que os prompts preenchem), D7 (D1b: dinâmico vs fixo) | Copy não separa string fixa de conteúdo gerado |
| 8.fluxo de curadoria docente (preview, edição, aprovação) | D2, D3 | Tela docente sem estados |
| 8.gatilhos de handoff: o que aciona a entrada da professora | D2 (raias cruzadas), D3 (aresta condicionada), D5 (estado de espera) | Handoff sem gatilho — classe `handoff` |
| 8.comportamento da plataforma em cada mediação (pausa · continua · trava) | D2, D3, D5 | Trava sem contrato |
| 8.dados do painel docente | D2 (tela docente), V1 | Painel vazio |
| 8.roteiro de perguntas da roda (≥ 3 perguntas escritas) | D4 (copy-fonte da professora), D7 (D6b) | Professora inventa a mediação — classe `copy-fonte` |

## Bloco 9 — Evidências e dados

| Célula | Quem consome | Sem ela |
|---|---|---|
| 9.campo por campo: o que é coletado, quando, finalidade, retenção, acesso | D7 (D3: nada fora do bloco 9), V1, banca DAD | Coleta aparece no wireframe sem contrato |
| 9.lista do que **não** é coletado nem calculado | D5, D7 | Campo de nome, voz ou imagem entra "por engano" |
| 9.grau de medida por medida (`scored` · `indicative` · `zero` · `none`) | V1, banca DAD | Criança que não teve a chance conta como recusa |
| 9.canal por dado (operacional · analítico) | V1 | Latência e ordem indefinidas |
| 9.texto livre de menor: existe? por quê? quem lê? | D4 (campo de reflexão), D7, banca DAD | Reflexão do 1.6 sem destino |
| 9.segredo de servidor (gabarito, parâmetros, prompt) | V1, banca TEC | Gabarito no bundle |
| 9.gabarito com autor e revisor nomeados | banca PED | Fonte pedagógica sem dono |

## Bloco 10 — Cenários de dispositivo

| Célula | Quem consome | Sem ela |
|---|---|---|
| 10.cenário 1:1 — o que muda · a descoberta chega? | D2 (coluna "Cenário"), D5 | Célula "descoberta chega?" em branco |
| 10.cenário 2–4 por aparelho — o que muda · a descoberta chega? | D2, D5 (estado "Degradado") | idem |
| 10.cenário projeção única — o que muda · a descoberta chega? | D2, D5 (1366×768), D4b (88×88) | idem |

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
| 12.`[ABERTO — dono]` por campo em aberto | D0 (é a lista inicial de lacunas), D7 | Lacuna sem dono |

## Regra de manutenção

Linha nova entra aqui só quando um agente de construção **devolveu** por falta dela — o `aprendizado` registra a recorrência e propõe a linha. Célula que nenhum agente consome sai: checklist que ninguém lê treina o D0 a preencher o que ninguém pediu.
