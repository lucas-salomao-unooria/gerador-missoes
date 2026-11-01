---
name: restaurar-one-pager-do-po
description: "Devolve ao one-pager os trechos do one-pager do PO que a esteira reescreveu sem pedido. Roda só quando a conferência determinística (one-pager do PO × gerado) acha trecho perdido."
---

Você restaura o one-pager da missão. O PO anexou o one-pager dele, e uma conferência em código achou trechos que
sumiram ou foram reescritos sem que o pedido do PO mandasse. Sua tarefa é devolvê-los — só isso.

## Insumos

**One-pager atual (o que a esteira escreveu):**

{one_pager}

**Conferência — one-pager do PO × one-pager atual (a lista do que restaurar):**

{one_pager_po_report?}

**Briefing e pedido do PO:**

{briefing?}

{pedido_correcao?}

**Votos dos comitês pedagógicos (o que eles mandaram corrigir também vale como pedido):**

{comite_canal_a_report?}

{comite_final_report?}

<!-- include: references/one-pager-do-po.md -->

## Regras

1. **Cada trecho listado volta como o PO escreveu, no mesmo lugar** (a seção que o relatório indica). Copie do
   one-pager do PO, não da lista: a lista corta os trechos longos.
2. **Se o texto atual no lugar do trecho veio de um gate ou parecer**, ele sai do corpo e vira, ao lado do texto do PO,
   `[PROPOSTA — validar com PO: <o que o gate ou parecer pedia> — <por quê>]`. Nada se perde: a decisão volta ao PO.
3. **Se a mudança foi pedida pelo PO ou pelo voto de um comitê pedagógico**, mantenha o texto novo e registre a
   linha na tabela «Alterações sobre o one-pager do PO», com o trecho do pedido ou do voto entre aspas, copiado
   literalmente do briefing, do pedido ou do relatório do comitê.
3b. **Seção 4 em fichas de interação.** O núcleo reorganiza a seção 4 do PO em fichas `#### Momento E.k`, com as palavras dele nos campos. Isso não é perda: restaure o trecho **dentro da ficha** do momento a que ele pertence (no campo que ele descreve), sem desfazer as fichas nem voltar para a prosa antiga.
4. **Não mexa no resto.** O que não está na lista fica exatamente como está no one-pager atual.
5. Devolva o one-pager inteiro, do título à última seção, sem comentário antes ou depois.
