---
name: candidatos-a-criterio
description: Problemas reais que nenhum critério da rubrica pega, com formulação candidata e contagem de ocorrências. Escrito por aprendizado, lido por qa-conformidade.
sources: [chat]
---

# Candidatos a critério

Uma ocorrência fica em observação. Duas ou mais viram proposta formal de emenda.

## C1 — A mecânica sustenta a descoberta central? · **pronto pra emenda**

**Problema:** o 2.4 verifica se a frase da descoberta existe e é articulável. Nenhum critério verifica se a mecânica **ensina** essa frase ou o oposto dela.
**Ocorrências:** Magia ou Truque v1 — a frase dizia "o TikTok não avisa" e a mecânica fazia o TikTok avisar com etiquetas coloridas, em dois lugares independentes (Ato 4 e Bloco 2 do podcast). Passou em 2.1, 2.2 e 2.4 individualmente.
**Formulação candidata:** *a descoberta central é sustentada pela mecânica — se o aluno descrevesse o que a plataforma fez com ele, a descrição não contradiz a frase-chave.*
**Teste de 30s:** ler a frase-chave; ler o que a plataforma faz na etapa Resultado; verificar se uma nega a outra. Estender aos artefatos secundários (podcast, falas do guia, textos do professor).
**Status:** **aplicado na v1.19 (22/09/2026) como critério 2.7 do gate estrutural**, mantendo o Passo 4.5 do agente 1 como verificação do autor.

## C2 — Pressuposto de leitura autônoma nos anos de alfabetização · **1 ocorrência**

**Problema:** o 6.1 testa vocabulário e extensão assumindo um aluno que decodifica. No 1º e 2º ano a alfabetização está em curso.
**Ocorrência:** Magia ou Truque v1 — 1º ano, abertura de 48 palavras e todas as instruções acionáveis só em texto.
**Formulação candidata:** *nos anos de alfabetização em curso, toda instrução acionável tem redundância não textual (áudio e pictograma).*
**Status:** **coberto na v1.19 (22/09/2026)** pelo sub-critério de áudio do 6.1 e pelo padrão `texto-icone-audio-anos-iniciais` de `defaults-missao.md`; a extensão da redundância ao 3º–5º fica registrada como pendência do pacote de anos iniciais.

## C3 — Não-negociável de ofício sem mecanismo · **2 ocorrências → pronto pra emenda**

**Problema:** o briefing de ofício declara não-negociáveis que dependem de o sistema garantir algo, e nenhum critério verifica se esse algo tem mecanismo. Os dois casos passaram no Gate 0 e foram pegos pelo agente 3.
**Ocorrências:**
- Magia ou Truque — "o primeiro dueto que o aluno abre é de um vídeo que ele salvou". Sem regra de ordenação ou bloqueio.
- Quem ficou fora — "uma voz forte fica ausente das três versões". A regra de geração escolhia por contraste e podia cobrir os 8 relatos.
**Formulação candidata:** *todo não-negociável de ofício que dependa de comportamento do sistema tem regra escrita (ordenação, bloqueio, restrição de geração) — intenção não basta.*
**Causa raiz identificada:** o briefing (agente 2) roda **depois** de o gate fechar a spec, então seus não-negociáveis nunca passam por verificação de mecanismo. Não é só critério faltando: é ordem de esteira errada.
**Status:** **aplicado na v1.19 (22/09/2026), opção A**: o briefing de ofício marca cada não-negociável com `[MECANISMO]` ou `[RS-n → gate-estrutural]` no formato da triagem de correção; o D7 do QA devolve os sem marca. A reordenação 1↔2 foi descartada — o modo de correção por etapa faz o `[RS-n]` chegar à spec sem mudar a orquestração.

## C4 — Affordance nativa em conflito com guardrail · **1 ocorrência**

**Problema:** um verbo pode ser 100% nativo (passa no 2.6) e ainda assim o comportamento real da plataforma violar um guardrail ético da missão. O 2.6 valida existência, não consequência.
**Ocorrência:** Quem ficou fora — a enquete do WhatsApp mostra quem votou o quê, contra o 8.5 (nenhuma comparação nominal). O one-pager assumia enquete nativa **e** resultado anônimo.
**Formulação candidata:** *para cada affordance nativa usada, o comportamento real da plataforma foi confrontado com os guardrails da missão; divergências deliberadas entram como ausência declarada.*
**Status:** observação. Provável recorrência em qualquer missão que use reações, visualizações ou status de leitura.

## C7 — Ausência de estados de falha de plataforma · **2 ocorrências → pronto pra emenda**

**Problema:** nenhum critério da v1.13 pede tratamento de falha técnica. Missões que persistem estado entre aulas e rodam em dispositivo compartilhado dependem de rede e de carregamento de imagem, e nenhuma delas especifica o que o estudante vê quando falha.
**Ocorrências:**
- Quem ficou fora (7º ano) — 21 telas, nenhum estado de falha (achado F1 do fluxo).
- A foto é real (5º ano) — contrato de estados com 11 transições, nenhuma de falha, apesar de afirmar que "não existem outros caminhos".
**Agravante:** onde o estado alimenta a evidência, falha técnica pode ser gravada como decisão pedagógica. Na missão do 5º ano existe `não concluída por encerramento` justamente para separar timer de escolha — e uma queda de conexão hoje cairia em `não encaminhada`.
**Formulação candidata:** *o contrato de estados cobre falha de plataforma — perda de conexão, sessão expirada e falha de carregamento de mídia — e nenhum estado de falha é registrado como decisão do estudante.*
**Teste de 30s:** procurar no documento as palavras conexão, offline, sessão, falha ou carregar. Se nenhuma aparecer numa missão com estado persistido, é ❌.
**Status:** **aplicado na v1.19 (22/09/2026)**: teste de contaminação no 9.4, regra "falha nunca é decisão" no bloco 9 da spec e no padrão `erro-na-voz-da-ficcao`.

## C8 — Consequência assimétrica · **1 ocorrência**

**Problema:** os critérios 1.4 e 3.2 pedem que o resultado reflita a ação, e são satisfeitos quando existe consequência para **uma** direção do erro. Missão de julgamento tem duas direções — confiar demais e desconfiar demais — e a revelação costuma responder só à primeira.
**Ocorrência:** A foto é real (5º ano) — a consequência "recai sobre o conteúdo que chegou ao jornal", e quem encaminhou zero não recebe nada, apesar de a seção 18 declarar que o objetivo não é gerar desconfiança generalizada.
**Formulação candidata:** *quando a missão pede julgamento, a revelação responde aos dois erros possíveis — o excesso e a falta —, e não só ao que produz conteúdo visível.*
**Status:** **absorvido na v1.19 (22/09/2026)** pelo "teste dos dois erros" do critério 6.6 (piso de desafio): revelação que responde só ao excesso ou só à falta é ⚠️.

## C9 — Profundidade: o conceito do material e o ápice do aha · **3 ocorrências + devolutiva do time pedagógico**

**Problema:** o 2.4 verifica se a frase da descoberta existe; o micro-gate verifica se ela não é entregue antes. Nenhum critério verificava se a missão trabalha o conceito do material do bimestre, nem se o aha desmente uma crença que o estudante pôs à prova com uma escolha dele — a missão rasa passava em tudo.
**Ocorrências:** A Foto do Mural (`exp02ef1b`, 23/09/2026, duas rodadas) — só o enquadramento do material, aha por zoom-out igual para qualquer escolha; O Rastro do Boato (6º ano, 2º bimestre, 23/09/2026) — testou julgamento individual quando o material dizia "incentivos estruturais", e revelou por painel com percentuais; `exp06ef1b` (22/09/2026) — "Painel Comparativo" onde o one-pager v5 revisado pelo time mostrava os posts que nunca apareceram. Devolutiva do time pedagógico em 24/09/2026: "missões rasas, o aha não tem ápice".
**Formulação aplicada:** `criterios-profundidade.md` — anatomia do aha em seis passos e seis dimensões com nota de 1 a 4, veredito contado em código (`tools/profundidade.py`).
**Status:** **aplicado na v1.20 (24/09/2026)**: mapa conceitual do material (A00c), ideação de três mecanismos (A00d), tabelas 1.1 e 1.2 no núcleo, cobertura conceitual em código (A01c), juiz de profundidade no loop do núcleo (A02b/A03b) e conferência de leitura no *de acordo* de produto (desligada em 25/09/2026: o time a sentiu como mais um bloqueio; fica comentada em `pipeline/passagem.py`). Os cortes (P1–P3 ≥ 3) são **[CONVENÇÃO]** até serem calibrados contra os pares "versão da IA → versão revisada pelo time pedagógico".

## C10 — Evidência por habilidade sem regra que separe os três níveis · **revisão do PO**

**Problema:** a matriz de evidência do bloco 11 ligava cada habilidade a um momento, a uma ação e a uma medida, mas a última coluna dizia só «ternário»: a escala sem a regra. O que separa Atingiu de Em processo e de Não atingiu ficava para quem implementa, e habilidade cuja ação não mostra o nível (curtir não é avaliar credibilidade) não tinha como ser lida.
**Ocorrências:** revisão dos prompts de produto pelo PO, entregue fora do git em 24/09/2026 (`01`, `04`, `05`, `08`, `10`, `13`): contrato de evidência por habilidade em dois canais — ação observada (A) e pergunta de três alternativas depois do Refletir (B).
**Formulação aplicada:** Regra 17 do núcleo, seção 12a do one-pager, 7.3 e 5.2, colunas «Canal de evidência» e «Regra ternária» conferidas em `tools/evidencia.py`. Ajustes à proposta, para não descer a régua: o Canal B **soma** evidência e não substitui o exercício em tela (5.2) nem o registro do Refletir; o foco primário tem sempre Canal A (Regra 12); uma resposta de três alternativas é `indicative`, nunca `scored` sozinha; a pergunta conta no teto de telas e minutos, e no 1º–2º ano mostra as três alternativas ao mesmo tempo (3.5: opção visível sobe o teto de duas para três), narradas (6.1) — o veto que a primeira versão desta integração trazia saiu por decisão de produto, 25/09/2026; o nível é calculado no servidor pela rota operacional e nunca trafega no `track`; níveis por extenso, porque 🟢 🟡 🔴 são veredito de gate; componente local quando o DS da seção não tem enquete.
**Status:** **aplicado na v1.21 (25/09/2026)**.
