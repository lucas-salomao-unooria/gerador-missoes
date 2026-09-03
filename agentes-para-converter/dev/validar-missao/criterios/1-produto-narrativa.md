# Dimensão A — Produto & Narrativa

Critérios com **[BLOQUEANTE]** reprovados com ❌ impedem a codificação.
Referências do gabarito: `documentacao-latex/secoes/12-experiencias.tex`,
`apps/experiencias/AGENTS.md`, manifestos `public/experiencia.json` das
exp-01/02/03/70.

## PROD-01 [BLOQUEANTE] — Identificação completa
A spec declara: slug (`exp-NN-nome`), nome da missão, série(s) alvo no formato
da plataforma (`["4EF"]`, `["2EM"]`… ou `[]` = transversal a TODAS as séries),
unidade da trilha, e `publico: estudante`. Sem série definida não há como a api
aplicar regras por ano (a exp-70 não serve a bolha B em 1EF–5EF porque a API
sabe a série).

## PROD-02 [BLOQUEANTE] — Premissa em uma frase
Qual software a missão clona (ou que mundo próprio ela constrói) e qual é a
tensão/pergunta central. Ex.: exp-02 = "em quais fontes você confiaria?";
exp-03 = "decidir com o que os dados mostram, sob relógio". Se a premissa não
cabe numa frase, o insumo ainda não sabe o que a missão é.

## PROD-03 — Objetivo na ficção ≠ objetivo pedagógico
Os dois estão declarados e são distintos. Na exp-03 o propósito declarado NÃO é
acertar a alocação — é experimentar que perguntas melhores produzem respostas
melhores. Spec que confunde "vencer o jogo" com "aprender X" produz medida
errada.

## PROD-04 [BLOQUEANTE] — Fluxo completo com estados nomeados
Lista ordenada ou diagrama: entrada/briefing → progressão → conclusão →
pós-conclusão. Cada estado tem nome (vira enum no código: `Tela`, `PASSOS`,
`FASES_DA_RUN`). Fluxo "o estudante navega e aprende" sem estados é NOK.

## PROD-05 — Reentrada e recomeço
O que acontece: no F5 no meio da missão; ao voltar noutro dia; ao reiniciar.
Regra validada na exp-02: briefing NÃO repete no F5 (cai direto no feed), e o
único caminho de volta ao briefing é reiniciar pelo perfil. A spec precisa
decidir isso, não deixar para o dev.

## PROD-06 — Estados que não andam para trás (latch)
Quais marcos, uma vez atingidos, não regridem (ex.: `ranking_desbloqueado` na
exp-02 — remover um salvo depois não tranca o ranking de novo; estado que anda
para trás confunde a criança e o professor). E o que congela após a pontuação
ser reportada (salvos congelados; reiniciar descongela).

## PROD-07 [BLOQUEANTE] — Momento de conclusão
Quem fecha a missão é o estudante, por ação explícita (botão), ou um evento?
O que a conclusão congela, o que ela reporta (`score`? sem score?), e o que
ainda é permitido depois. Gabarito exp-02: o 3º salvo habilita "Concluir
missão", mas quem fecha é o estudante — a distância entre os dois eventos é
dado (tempo revendo a escolha).

## PROD-08 [BLOQUEANTE] — Decisão sobre a revelação
Três respostas válidas, e a spec escolhe UMA explicitamente:
(a) revelação no software, com roteiro tela a tela e a linha de "quem está
falando" (exp-01, exp-02); (b) sem revelação no software — a lição acontece no
debate conduzido pelo professor, e o material desse debate FAZ PARTE do insumo
(exp-03, exp-70); (c) híbrido, descrito. Ausência de decisão = ❌. Promessa de
"guia do professor a escrever depois" repete a pendência registrada da exp-03
(guia vazio onde a lição acontece) = ⚠️ no mínimo, ❌ se a lição depende dele.

## PROD-09 — A revelação não pode mentir
Se há revelação, os textos variam conforme o que de fato aconteceu com aquele
estudante (na exp-01, `telaDoLadoSemeado` muda para perfil / redistribuído /
sorteio — dizer "escolhido a partir de como você jogou" a quem caiu no sorteio
quebraria a única tela que existe para não mentir). A spec lista as variações.

## PROD-10 — Papel do professor especificado
Preparo (o que ele configura/valida antes), condução (o que ele controla
durante), acompanhamento (o que ele vê ao vivo e O QUE PEDE AÇÃO — na exp-01 o
monitor destaca só `ociosoHaMs`), ficha da missão, e ações destrutivas (zerar
turma: o que apaga e o que preserva). "O professor acompanha" sem verbos é NOK.

## PROD-11 — Aula síncrona e relógio coletivo
Se a missão é síncrona: quem dá a largada (o professor, para a turma inteira),
o que fica travado antes dela, como o estudante descobre que pode começar
(polling — ele não tem o que enviar para descobrir), e o que "+tempo" faz (na
exp-03, o pivô impede a narrativa de rebobinar). Se assíncrona, declarar.

## PROD-12 — Material de condução do debate
Se qualquer parte da lição acontece fora do software, o roteiro do debate vem
NO insumo: perguntas, o que projetar (na exp-70 o guia projeta as três bolhas
lado a lado — e os textos vêm da API, nunca de cópia), tempo estimado.

## PROD-13 — Modos de erro com a ficção preservada
O que o estudante vê quando: a IA está indisponível, a rede cai, a quota acaba.
A ficção não quebra: na exp-03 vira "O Cientista não conseguiu responder
agora" (e não debita); na exp-01 reações ao vivo indisponíveis devolvem lista
vazia sem erro. Stack trace, branding da plataforma ou silêncio dentro do
clone = imersão quebrada.

## PROD-14 — Segunda aplicação
O que acontece se a turma jogar de novo: a 2ª rodada mede algo? O que precisa
ser re-sorteado (na exp-70, zerar a turma apaga as BOLHAS junto — repetir o
mesmo golpe não mede nada) e o que é preservado (perfis já importados por outra
missão não são tocados)?

## PROD-15 — Dependências entre missões
Se esta missão consome ou alimenta outra (como exp-70 → exp-01), a spec declara
o contrato E o comportamento sem a dependência (fallback honesto: sem perfil da
Vila, o Instanooria cai no sorteio balanceado — "que é honesto sobre não
saber").

## PROD-16 — Escopo do conteúdo autoral
Inventário do conteúdo que a missão exige (a exp-02 tem 21 vídeos + 39 colegas
fictícios; a exp-03 tem 8 fontes + 4 bairros; a exp-70 tem 5 mensagens × 3
bolhas): quantos itens, quem produz, critério de qualidade e de revisão. Sem
isso a estimativa de esforço é ficção.
