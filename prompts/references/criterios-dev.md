---
name: criterios-dev
description: Os 72 critérios do gate `/validar-missao` do time de dev, com a versão em que os lemos e o que a nossa esteira produz para cada bloqueante. Lido por handoff-dev e formato-spec; mantido por aprendizado.
sources: [chat]
---

# Critérios do gate de dev

**Versão lida:** 02/09/2026 (critérios). **Gabarito da plataforma reconferido em 16/09/2026** contra `plataforma-unooria@ba0de35` — as cópias canônicas estão em `references/plataforma/` (`versao-lida.json`). 72 critérios, 5 dimensões, **21 bloqueantes**.
Consolidação: 🟢 exige zero ❌ nos 72 — qualquer ❌ não bloqueante rebaixa
para 🟡.

⚠️ **Os critérios deles citam ADRs, tabelas e rotas reais do repositório.**
Quando um ADR muda, esta referência fica errada sem ninguém perceber.
Reconferir a cada emenda da nossa rubrica, e atualizar a versão lida acima.

## Bloqueantes, e quem produz do nosso lado

| # | Critério | Nosso produtor |
|---|---|---|
| PROD-01 | Identificação completa | spec bloco 0 |
| PROD-02 | Premissa em uma frase | spec bloco 1 |
| PROD-04 | Fluxo com estados nomeados | spec bloco 2 + `fluxo-figjam` |
| PROD-07 | Momento de conclusão | spec bloco 2 |
| PROD-08 | Decisão sobre a revelação | `brief-oficio` + `copy-ptbr` |
| DES-01 | Seção do DS nomeada e existente | `ambientes.md` + spec bloco 0 |
| DES-02 | Mapa "quem está falando", tela a tela | coluna `seção` no sheet |
| PED-01 | Códigos BNCC de Letramento Digital | spec bloco 11, conferido pelo `BnccCheck` contra `references/bncc-computacao.json` *(bloqueia apenas em letramento digital; outras regras passam como alerta)* |
| PED-02 | Matriz habilidade → evidência → interação → dado | `handoff-dev`, seção 3 |
| PED-04 | Gabarito com autor e revisor, só no servidor | spec bloco 9 *(precisa de dois nomes de pessoa)* |
| PED-06 | Graus de medida | spec bloco 9 |
| PED-07 | Nenhum ranking de crianças | rubrica 3.3 / 7.2 / 8.5 |
| DAD-01 | Vocabulário de telemetria (`verbo`, `objeto`, `resultado`, `contexto` — sem campo `dados`) | `handoff-dev`, entregável 5, conferido pelo `TelemetriaCheck` |
| DAD-02 | Canal certo | spec bloco 9 |
| DAD-03 | Entidades a persistir | `handoff-dev`, entregável 5 |
| DAD-04 | O que nunca vai ao bundle | spec bloco 9 |
| DAD-05 | Servidor calcula, nunca aceita | spec bloco 9 |
| DAD-07 | PII de menor | spec bloco 9 |
| DAD-08 | Texto livre de menor | spec bloco 9 |
| TEC-01 | Manifesto derivável (com `produto`, `unidade`, `permissoes`) | spec bloco 0 — ficha do manifesto, conferida pelo `ManifestoCheck` |
| TEC-02 | Módulo da api desenhado | *verdade do lado deles* |

## Duas coisas que o gate deles resolveu do nosso lado

**PROD-08** legitima a revelação fora do software, desde que o material do
debate faça parte do insumo. O teste de permanência do nosso 2.1 vale para
**interface** dentro da simulação, não para material de mediação — que o
nosso 4.2 exige. Origem da emenda: o gate deles.

**DES-01** dá o nome canônico das seções: `instanooria`, `unitube`,
`chatgpt`, `whatsappmobile`, `tiktooria`. Roblox não tem seção.

## O que continua fora do nosso alcance

- Verificação no repositório deles: DES-01 (a seção existe?), TEC-11 (dependência de DS pendente?)
- Dono humano nomeado: PED-04 pede pessoas, não "time pedagógico"
- Deriva dos critérios: ver o aviso no topo
