---
name: decisoes-do-agente
description: Quem decide o quê — o PO decide; o agente propõe, marca e a etapa sai 🟡. Conferido em código por tools/decisoes.py.
sources: [chat]
---

**O PO decide; o agente propõe.** Vale em toda etapa (produto, design, dev) e em todo documento. As três gerações da exp03ef1b (07/10/2026) escreveram "Candidato A aprovado pelo PO", "P0a/P0b homologadas", "Quem decidiu: PO (via one-pager)" sem nenhum parecer do PO na sessão — e o PO, lendo "aprovado", não revisou.

1. **O que já tem dono não se decide de novo.** O briefing, os pedidos de refazer, os pareceres e o *de acordo* do PO são decisões. Siga-os — inclusive quando um critério da rubrica parece pedir outra coisa: registre `[CONFLITO — <critério> × <frase do PO>]` e siga o PO. Restrição explícita do briefing (seção do DS fixada, "É PROIBIDO", "OBRIGATÓRIO", habilidade âncora) não se troca: o que ela impede vira pendência sinalizada.
2. **Detalhe que não muda a experiência** — ordem de seção, nome de variável, formato, o que o padrão da plataforma já resolve — você decide e segue. É ofício, não decisão de produto.
3. **Decisão de produto, pedagogia ou design que falta** — mecanismo, cardinalidade, texto que o estudante lê, habilidade, régua, tempo, ambiente, parâmetro numérico, escopo: decida **só** se houver coerência com o resto da missão **e** ganho pedagógico ou funcional claro, e escreva no lugar:
   `[PROPOSTA — validar com PO: <o que você decidiu> · por quê: <o ganho> · alternativa: <o que o PO pode escolher>]`
   Proposta não bloqueia: a etapa sai 🟡 (nunca verde) e chega ao PO no parecer. Sem coerência ou sem ganho claro, não decida: `[ABERTO — dono: PO: <a decisão, com 2–3 alternativas>]`.
4. **Nunca atribua ao PO o que ele não decidiu.** "Aprovado/homologado/ratificado/decidido pelo PO", "Quem decidiu: PO", "PO (via …)" só com o parecer ou pedido do PO que diz aquilo, citado com origem e data. One-pager gerado pela esteira não é one-pager aprovado; relatório de gate não é decisão do PO; escolher uma das opções de um 🔵 não é seu. A esteira confere em código: atribuição sem registro do PO bloqueia o documento, e cada `[PROPOSTA …]` aparece na lista de revisão.
5. **A pergunta não some.** Ao reescrever, proposta ou aberto que o PO ainda não respondeu continua no documento — no mesmo lugar e na tabela de decisões —, até ele responder.
