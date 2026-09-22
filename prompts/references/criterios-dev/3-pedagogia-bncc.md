# Dimensão C — Pedagogia & BNCC

Referências do gabarito: `documentacao-latex/secoes/12-experiencias.tex`
(graus de medida, zero vs none, ranking), `apps/api/src/vila/mapeamento.ts` e
`leitura.ts` (graus por tipo), `apps/api/src/unootube/catalogo.ts` (gabarito
`factual`).

**Fato de plataforma que o avaliador precisa saber:** hoje NÃO existe
modelagem estruturada de BNCC no servidor — nenhuma tabela de habilidade,
competência ou descritor; BNCC aparece só como texto livre em
`exp90ef1b_referencias` e em prompts. Nenhuma experiência declara habilidade de
forma rastreável. Toda promessa de "relatório por habilidade" na spec é escopo
novo de plataforma e deve ser sinalizada como tal no relatório.

## PED-01 [BLOQUEANTE para Letramento Digital] — Habilidades BNCC com código explícito
A spec lista as habilidades alvo com código oficial (ex.: `EFxxCOxx`), poucas e priorizadas (uma missão que "cobre" dez habilidades não mede nenhuma).
**Regra de bloqueio da BNCC:** As **únicas regras da BNCC que bloqueiam de fato são as de letramento digital** (BNCC Computação — Cultura Digital / uso crítico, seguro e consciente de tecnologias). Falha ou ausência nessas habilidades = ❌ bloqueante. Habilidades de disciplinas tradicionais ou competências gerais citadas sem código verificado **não bloqueiam** a missão: passam com ressalvas no relatório, registradas como itens de alerta (⚠️).

## PED-02 [BLOQUEANTE] — Matriz habilidade → evidência → interação → dado
Para CADA habilidade: qual comportamento observável evidencia a habilidade,
qual interação da missão o captura, e onde isso é gravado (evento de
telemetria, coluna, tabela). Sem essa matriz a missão coleta cliques, não
evidências. Gabarito: na exp-01, "foi atrás do que o feed não dava" ⇒ eventos
`abriu_busca`/`buscou` ⇒ componente `Investigacao` do dossiê.

## PED-03 — Medida vs cosmético, item a item
O que no conteúdo é gabarito (na exp-02, `factual`) e o que é cosmético
intencional (rótulos de views/inscritos — não aleatórios: o fake tem os
números grandes, e há teste garantindo). Cada elemento numérico visível ao
estudante classificado como um ou outro.

## PED-04 [BLOQUEANTE] — Gabarito fechado, só no servidor
A fonte da verdade pedagógica (o que é correto/confiável/severo) está definida
no insumo. E a spec reconhece que o gabarito vive
exclusivamente no servidor (regra 3) — se ela prevê o cliente sabendo a
resposta "para dar feedback imediato", é ❌ aqui e em DAD-04.

**Quem assina o gabarito não é exigência deste critério** (decisão de produto de
2026-09-22). Pedir dois nomes de pessoa reprovava a missão por um ato que nenhum
agente pratica: a spec escrevia `[ABERTO — responsável de produto: nomear autor e
revisor]` porque o gabarito do bloco 9 mandava, e a banca bloqueava por esse mesmo
marcador. Autoria e revisão são registro editorial, fechado fora da esteira.

## PED-05 — Nota e score declarados
A missão produz nota? Qual, exatamente, e em que escala (na exp-02: fontes
confiáveis 0–3, calculado do gabarito no servidor)? Se a missão deliberadamente
NÃO produz nota (exp-03 conclui sem `score` — "um número faria o hub exibir
pontuação que o instrumento se recusa a produzir"), a spec declara isso e o
professor sabe o que ler no lugar.

## PED-06 [BLOQUEANTE] — Graus de medida e zero vs none
Toda medida sobre criança distingue: `scored` (≥2 sinais independentes, tem
número), `indicative` (1 sinal, descrito em texto, fora das médias), `zero`
(teve a chance e não foi — entra na média) e `none` (a oportunidade não chegou
— sai da conta). Tratar "não teve chance" como "escolheu não" faz uma criança
parecer ter recusado o que nunca lhe foi oferecido — e esse número será lido
por um adulto que decide sobre ela. A spec define, por medida, o que conta
como cada grau.

## PED-07 [BLOQUEANTE] — Nenhum ranking de crianças
Nenhuma tela ordenável com medida de criança; listagem de turma não tem coluna
de valor/pontuação (uma coluna "Poder" ordenável viraria ranking — o smoke da
exp-03 falha se aparecer). Valores individuais vivem na tela de UMA criança,
com o grau ao lado. Comparação entre pares só com colegas FICTÍCIOS, com
distribuição desenhada para a lição (exp-02). Pontuação real de menor nunca é
exposta a outro menor (LGPD).

## PED-08 — O instrumento não se contamina
Mecânicas de jogo não podem ter custo que distorça a medida: na exp-70, um
golpe que custasse fagulha faria a criança que caiu parecer MENOS generosa no
retrato de valores. A spec separa explicitamente o que cada camada lê (escolhas
com custo vs julgamento sobre mensagens) e garante que uma não escreve na
outra.

## PED-09 — Adequação à série, aplicada por quem sabe a série
Vocabulário, carga de leitura e regras por ano — e QUEM as aplica: regras que
dependem da série são da api (só ela sabe a série; a bolha B não é servida em
1EF–5EF por regra de servidor). Spec para série nova (ex.: 1EF, pré-leitor)
descreve como a missão funciona sem leitura fluente.

## PED-10 — A criança sabe que é medida?
Decisão explícita. Se o instrumento exige espontaneidade, não há tela de
resultado dentro do jogo (exp-70: "no instante em que ela se sabe medida, a
próxima partida vira atuação"). Se há revelação, o que é dito sobre os dados é
VERDADE ("nenhum dado seu saiu daqui" — e o software cumpre).

## PED-11 — O papel do erro
O que acontece pedagogicamente quando o estudante "erra": o software julga
(feedback imediato), o resultado julga (ranking fictício), ou o debate julga
(o software se recusa a julgar — exp-03 aceita "foi intuição, não olhei dado"
sem punir)? Decisão declarada, coerente com a habilidade medida.

## PED-12 — O que cada adulto vê
Professor: leitura individual (graus + transcrição/detalhe) e visão de turma
(agregados + o que pede ação). Gestor: SÓ agregado — a linha de uma criança
não abre para gestor (controllers separados). A spec desenha as duas leituras
e não promete ao gestor o que é do professor.

## PED-13 — Validade da reaplicação
Jogar de novo mede algo ou vira atuação/memorização? O que é re-sorteado e o
que é descartado na segunda rodada. Coerente com PROD-14.

## PED-14 — Transparência e consentimento
O que escola/responsáveis precisam saber sobre a simulação e os dados
coletados; a copy de transparência para o estudante (quando houver revelação)
é verdadeira e verificável.

## PED-15 — Plano de validação pedagógica
Como a hipótese pedagógica será testada antes/durante a codificação: playtest
em papel, turma piloto, critérios de sucesso (a ficha da exp-03 nasceu de dois
playtests documentados). "Validamos depois que estiver pronto" = ⚠️.
