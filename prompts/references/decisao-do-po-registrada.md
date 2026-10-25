## Decisão do PO registrada não é ressalva

O PO já decidiu o que está registrado: nas notas de passagem desta missão, no fim desta instrução — as «Decisões do PO
no contrato de produto», que o de acordo de produto grava (`decisoes_do_po`), os pedidos de refazer e os pareceres de quem
liberou as etapas — e no próprio one-pager quando ele cita o pedido ou o parecer que a sustenta («homologado pelo PO no
Pedido 13», `[HOMOLOGADO pelo PO]`, «<valor> — PO, parecer de <data>»). Decisão registrada **não é risco aceito, ressalva nem pendência**: não a liste nos achados, nem como
⚠️ nem como 🔵 — mesmo quando o critério a reprovaria. Se o critério e a decisão divergem, diga uma vez, na prosa do
relatório, que o PO decidiu contra o critério e em qual registro, sem severidade.

Na exp06ef1b (08/10/2026) o PO aceitou no Pedido 13 os 29 min em tela de uma aula de 50; a experiência do estudante
(6.2), a avaliação pedagógica (4.1) e o gate final voltaram com a mesma ressalva, cada um escrevendo «homologada pelo
PO», e a etapa nunca saiu verde. Um código confere depois (`tools/juizes_produto.py`): o achado que só repete uma decisão
que os registros do PO confirmam sai da contagem, e o relatório diz qual.

O que **não** está registrado continua com você: a decisão atribuída ao PO sem o parecer que a sustente é ❌ de coerência
(`references/decisoes-do-agente.md`) — o PO não ratifica fato consumado.
