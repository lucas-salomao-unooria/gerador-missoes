---
name: padrao-plataforma-revezamento
description: Padrão da plataforma para o aparelho compartilhado (2–4 estudantes por aparelho) — o que a missão não prescreve, o que a conta e a evidência registram e o que ainda depende de validação. A missão cita este padrão em vez de escrever um protocolo de revezamento próprio. Consolidado do que já existia no repositório; não cria regra nova.
sources: [criterios-gate-estrutural (10.1 e 10.2), defaults-missao (classe dispositivo), pedido do PO na exp06ef1b (08/10/2026), plano «Produto dono do contrato» (D6)]
status: rascunho v0 — validar com o usuário (produto e pedagogia) antes de tratar como contrato
---

# Aparelho compartilhado e revezamento — padrão da plataforma

**Por que existe.** O critério 10.2 do gate estrutural pede, para cada etapa com decisão, quem toca, como o grupo
decide e o que se registra no desacordo. Cada missão respondia de um jeito: piloto e copiloto alternando por etapa
(exp03ef1b), papéis «Operador da Câmera» e «Diretor de Cena» invertidos pela interface (exp02ef1b), um estudante por
etapa (exp02em1b), e o fechamento de lacunas (D0) prescreveu revezamento de 2 a 4 operadores no design (exp03em1b D0-8,
exp01em1b D0-4). Na exp06ef1b, em 08/10/2026, o PO recusou o revezamento prescrito pela missão:

> «O arranjo de dispositivos (individual, dupla ou grupo) é definido pela infraestrutura da escola e gerenciado pela
> plataforma Unooria, não pela missão. A mecânica pedagógica funciona identicamente em qualquer configuração.»

Pela decisão D6 do plano «Produto dono do contrato», o protocolo de revezamento vira **padrão de plataforma**: este
arquivo. A missão cita o padrão e não reescreve protocolo.

**Como se usa.** O bloco 10 da spec de produto e o passo de completude (bloco 15) citam o padrão pelo nome —
`padrão: revezamento-pela-plataforma` — e só escrevem o que é da missão: o **teste da descoberta** (com o aparelho
compartilhado, o grupo chega ao Resultado com consequência própria?). O design (D0-UX) adapta a tela ao cenário, sem
criar papel nem regra de revezamento.

---

| Nome | Padrão | Fonte |
|---|---|---|
| `revezamento-pela-plataforma` | A missão **não prescreve papéis nem rodízio** entre estudantes do mesmo aparelho, e a interface não força a troca de quem toca. O arranjo (individual, dupla ou grupo) é da escola e da plataforma; a mecânica funciona igual em qualquer configuração. | pedido do PO, exp06ef1b (08/10/2026) · D6 |
| `conta-e-evidencia-do-grupo` 🟡 | Em 2–4 por aparelho a **conta é do grupo**, com identidade escolhida pelo grupo por affordance nativa; a decisão é do grupo e a evidência é **por grupo**, não por criança; a plataforma não tenta inferir quem tocou. | `defaults-missao.md` (`2-4-decide-em-grupo-registra-por-grupo`) · critério 10.1 · 8.4 (não rotular estudante) |
| `tres-cenarios-sempre` | Os três cenários existem em toda missão — **1:1**, **2–4 por aparelho**, **projeção única** — e a spec responde, para cada um, «o que muda» e «a descoberta chega?». | critério 10.1 · `defaults-missao.md` (`tres-cenarios`) |
| `teste-da-descoberta-continua` | O teste do critério 10.2 continua valendo e é da missão: com o aparelho compartilhado, o grupo chega ao Resultado com consequência própria. Se a consequência só existe para quem tocou, a missão degrada para plateia — isso a missão resolve na mecânica, não com papel de revezamento. | critério 10.2 |

## O que ainda não está decidido 🟡

- **O que se registra quando o grupo discorda.** O critério 10.2 pede essa resposta, e o repositório não tem um padrão
  confirmado: a evidência por grupo (`conta-e-evidencia-do-grupo`) registra a escolha que o grupo confirmou na tela, e
  não há registro de desacordo à parte. Até o usuário validar, a missão que precisar de outra coisa a escreve como
  `[PROPOSTA — validar com PO: …]`.
- **Se 10.2 aceita a citação deste padrão no lugar do protocolo por etapa.** O critério foi ajustado para aceitar (ver
  `criterios-gate-estrutural.md`); a confirmação final é do usuário.

## Quem decide o quê

- **Plataforma (este arquivo):** que a missão não prescreve revezamento, a conta e a evidência do grupo, os três
  cenários.
- **PO, por missão:** qualquer papel, rodízio ou regra de desacordo próprios da missão — só como `[PROPOSTA — validar
  com PO: …]` no de acordo de produto.
- **Ninguém no design:** o D0-UX que decidir revezamento é barrado em código (`tools/decisoes.py`, tópico de produto).
