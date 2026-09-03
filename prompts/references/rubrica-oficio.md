---
name: rubrica-oficio
description: Régua de devolução do gate de ofício — perguntas falsificáveis sobre execução, e os tetos de densidade por faixa e tier. Lido pelo principal no gate de ofício e pelos agentes de construção. Escrito por aprendizado.
sources: [chat]
---

# Rubrica de ofício v0.1

Conformidade é do agente 6. Aqui se mede **execução**: uma entrega pode cumprir todo obrigatório da v1.13 e ainda ser medíocre. Hoje nada no pipeline reprova por isso.

Cada item devolve ou não devolve. **Item que precisa de debate pra responder está mal redigido** — reescreva ou tire. É a única defesa contra esta rubrica virar gosto em três missões.

Higiene contável não mora aqui — mora em `references/pronto.md`.

---

## Tetos de densidade

Elementos por tela, por faixa e por tier. Conta como elemento: bloco de texto, affordance interativa, mídia, ícone com significado, container visualmente distinto. **Não** conta chrome nativo da plataforma, que é fundo reconhecível e vem da biblioteca.

| Faixa | `pico` | `alta` | `média` | `serviço` |
|---|:-:|:-:|:-:|:-:|
| 1º–2º ano | 3 | 4 | 5 | 2 |
| 3º–5º ano | 4 | 6 | 8 | 3 |
| 6º–9º ano | 5 | 8 | 10 | 3 |
| EM | 6 | 9 | 12 | 4 |

⚠️ **v0.1 — números a calibrar.** São ponto de partida derivado dos caps de carga decisória do 3.5, não medição. A primeira missão que os aplicar gera a primeira correção; **registre o desvio em vez de burlar o número.**

**Regra que não depende de calibragem:** a tela `pico` tem menos elementos que suas vizinhas na ordem do arco. Essa é comparativa e vale mesmo se todos os números acima estiverem errados. Se o pico é a tela mais cheia da missão, a hierarquia está invertida e o wireframe construiu a inversão fielmente.

---

## O1 — Hierarquia

| Pergunta | Devolve quando |
|---|---|
| O que salta primeiro na tela é o que a Seção 4 declarou? | Salta outra coisa, ou saltam duas |
| O que a Seção 4 mandou recuar recuou de fato? | Continua no primeiro nível de leitura |
| A tela `pico` é a mais enxuta do trecho? | É a mais cheia |
| Teto de elementos respeitado, por contagem? | Acima, sem desvio registrado |

## O2 — Voz

| Pergunta | Devolve quando |
|---|---|
| Cobrindo o nome do falante, dá pra dizer quem fala? | Não dá em duas ou mais strings |
| Os três registros aparecem nos beats que o mapa de beats mandou? | Registro fora do beat, ou colapsado |
| A contagem de exclamações na missão inteira mantém a força? | Quase toda string tem uma |
| Alguma string entrega a conclusão antes da vivência? | Uma basta |

Os testes da boca, do exclamativo e do "quem fala" são do `copy-ptbr` e **rodam aqui**, não lá. Quem escreveu sempre reconhece a própria voz.

## O3 — Fidelidade de ambiente

| Pergunta | Devolve quando |
|---|---|
| Screenshot sem legenda: alguém do time diz que app é? | Não diz, ou diz errado |
| Affordances nas posições reais, na ordem real? | Fora de posição |
| Ausência declarada no bloco 5 da spec continua ausente? | Reapareceu por realismo |
| Componente da biblioteca reusado onde existia? | Redesenhado do zero |

Enquanto `references/ambientes.md` não tiver biblioteca do ambiente e lista de ausências, **O3 devolve por causa que não é do agente 5.** Registre como lacuna de biblioteca, não como ticket, ou o staff paga por dívida de produto.

## O4 — O beat sobrevive

| Pergunta | Devolve quando |
|---|---|
| O beat `MEMORÁVEL` tem tela própria, com peso proporcional? | Virou uma linha entre outras |
| O `PICO` está na tela do beat que o mapa de beats marcou? | Deslocou sem registro |
| O `AHA` usa affordance nativa? | Usa tela de sistema |
| Cada não-negociável está na tela ou string onde deveria? | Ausente sem decisão registrada |

## O5 — Legibilidade da ação

| Pergunta | Devolve quando |
|---|---|
| Em cada tela, dá pra saber o que fazer em 3 segundos? | Não dá em qualquer tela `pico` ou `alta` |
| A consequência da ação é visível na própria tela? | Só aparece duas telas depois |
| Estados de espera e vazio parecem intencionais? | Parecem tela quebrada |

---

## Disciplina de emenda

Mesma da rubrica de conformidade: **critério de ofício sem missão de origem é opinião.**

```
**Item:** O1–O5 — expansão ou pergunta nova
**Pergunta:** redigida, com o "devolve quando"
**Origem:** a missão onde a falta apareceu, e por que O1–O5 não pegaram
**Calibragem:** se mexe em número, o desvio observado que motivou
```

Devolução feita por preferência que não está aqui **nem** na direção que o principal escreveu não é devolução — é candidato a emenda. O staff tem direito de recusar.

## Changelog

| Versão | Mudança |
|---|---|
| v0.1 | Régua inicial. O1–O5 e tetos derivados dos caps do 3.5, a calibrar na primeira missão. Origem: o pipeline não tinha nenhum gate de execução — só de conformidade. |
