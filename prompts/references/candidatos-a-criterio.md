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
**Status:** implementado como Passo 4.5 do agente 1. Emenda formal pendente.

## C2 — Pressuposto de leitura autônoma nos anos de alfabetização · **1 ocorrência**

**Problema:** o 6.1 testa vocabulário e extensão assumindo um aluno que decodifica. No 1º e 2º ano a alfabetização está em curso.
**Ocorrência:** Magia ou Truque v1 — 1º ano, abertura de 48 palavras e todas as instruções acionáveis só em texto.
**Formulação candidata:** *nos anos de alfabetização em curso, toda instrução acionável tem redundância não textual (áudio e pictograma).*
**Status:** observação. Segunda ocorrência antes de propor.

## C3 — Não-negociável de ofício sem mecanismo · **2 ocorrências → pronto pra emenda**

**Problema:** o briefing de ofício declara não-negociáveis que dependem de o sistema garantir algo, e nenhum critério verifica se esse algo tem mecanismo. Os dois casos passaram no Gate 0 e foram pegos pelo agente 3.
**Ocorrências:**
- Magia ou Truque — "o primeiro dueto que o aluno abre é de um vídeo que ele salvou". Sem regra de ordenação ou bloqueio.
- Quem ficou fora — "uma voz forte fica ausente das três versões". A regra de geração escolhia por contraste e podia cobrir os 8 relatos.
**Formulação candidata:** *todo não-negociável de ofício que dependa de comportamento do sistema tem regra escrita (ordenação, bloqueio, restrição de geração) — intenção não basta.*
**Causa raiz identificada:** o briefing (agente 2) roda **depois** de o gate fechar a spec, então seus não-negociáveis nunca passam por verificação de mecanismo. Não é só critério faltando: é ordem de esteira errada.
**Status:** pronto pra emenda, **mais** proposta de reordenar 1↔2.

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
**Status:** pronto pra emenda.

## C8 — Consequência assimétrica · **1 ocorrência**

**Problema:** os critérios 1.4 e 3.2 pedem que o resultado reflita a ação, e são satisfeitos quando existe consequência para **uma** direção do erro. Missão de julgamento tem duas direções — confiar demais e desconfiar demais — e a revelação costuma responder só à primeira.
**Ocorrência:** A foto é real (5º ano) — a consequência "recai sobre o conteúdo que chegou ao jornal", e quem encaminhou zero não recebe nada, apesar de a seção 18 declarar que o objetivo não é gerar desconfiança generalizada.
**Formulação candidata:** *quando a missão pede julgamento, a revelação responde aos dois erros possíveis — o excesso e a falta —, e não só ao que produz conteúdo visível.*
**Status:** observação. Provável recorrência em toda missão de classificar/curar.
