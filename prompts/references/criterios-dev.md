---
name: criterios-dev
description: Os 73 critérios do gate `/validar-missao` do time de dev, com a versão em que os lemos e o que a nossa esteira produz para cada bloqueante. Lido por handoff-dev e formato-spec; mantido por aprendizado.
sources: [chat]
---

# Critérios do gate de dev

**Versão lida:** 02/09/2026 (critérios). **Gabarito da plataforma reconferido em 16/09/2026** contra `plataforma-unooria@ba0de35` — as cópias canônicas vêm da base da plataforma publicada no bucket (o commit lido aparece no diagnóstico de cada execução). 73 critérios, 5 dimensões, **22 bloqueantes** (contagem real dos cinco arquivos: 16 + 14 + 15 + 15 + 13; DES-14 nasceu do lado de cá em 21/09/2026 e ganhou severidade em 22/09).
Consolidação: 🟢 exige zero ❌ nos 73 — qualquer ❌ não bloqueante rebaixa
para 🟡.

⚠️ **Os critérios deles citam ADRs, tabelas e rotas reais do repositório.**
Quando um ADR muda, esta referência fica errada sem ninguém perceber.
Reconferir a cada emenda da nossa rubrica, e atualizar a versão lida acima.

## Bloqueantes, e quem produz do nosso lado

| # | Critério | Nosso produtor |
|---|---|---|
| PROD-01 | Identificação completa | spec bloco 0 |
| PROD-02 | Premissa em uma frase | spec bloco 1 |
| PROD-04 | Fluxo com estados nomeados | spec bloco 2 + `fluxo` |
| PROD-07 | Momento de conclusão | spec bloco 2 |
| PROD-08 | Decisão sobre a revelação | `brief-oficio` + `copy-ptbr` |
| DES-01 | Seção do DS nomeada e existente | `ambientes.md` + spec bloco 0 |
| DES-02 | Mapa "quem está falando", tela a tela | coluna `seção` no sheet |
| DES-14 | Visão do professor completa e transversal (cinco telas do preparo, segundo grafo) — **critério escrito e classificado por esta esteira**, não pelo time da plataforma | `061_jornada.md` §1c + `062_fluxo.md` segundo grafo + folha `stitch_links` (D6 do QA já bloqueia a montante) |
| PED-01 | Códigos BNCC de Letramento Digital | spec bloco 11, conferido pelo `BnccCheck` contra `references/bncc-computacao.json` *(bloqueia apenas em letramento digital; outras regras passam como alerta)* |
| PED-02 | Matriz habilidade → evidência → interação → dado | `handoff-dev`, seção 3 |
| PED-04 | Gabarito definido, só no servidor | spec bloco 9 |
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

## O que o gate deles não bloqueia e o nosso bloqueia antes

O banco de dev é lido em versão datada e não é desta esteira — exceto DES-14, que nasceu do lado de cá. Quatro critérios de imersão são não bloqueantes lá; para cada um, o juízo equivalente já é bloqueante a montante, e a banca não pode relaxar por achar que "o banco pega depois":

| Banco de dev | O que pergunta | Equivalente bloqueante a montante (nosso) |
|---|---|---|
| DES-03 | O clone é fiel, com lista do que difere | O3 da rubrica de ofício com a tabela de ausências de `ambientes.md`; 2.3 (diegese, obrigatório); `premissa-imersao.md` |
| DES-07 | Estados vazios parecem intencionais | O5; padrão `vazio-e-carregando`; 9.4 com o teste de contaminação |
| DES-08 | Copy real e adequada à série | 6.1 com a cláusula de defasagem; D4 do QA com `literatura-cognitiva-resumo.md` |
| DES-13 | Marca fora do disfarce | D8b do QA e a regra de `ambientes.md` (já bloqueantes) |
| DES-14 | Visão do professor completa e transversal | D6 e D6c do QA (bloqueio para tela do professor ausente) — e DES-14 é `[BLOQUEANTE]` também no banco, por decisão desta esteira |

Se a esteira pode acrescentar critério ao banco (DES-14), a objeção "não é nosso" a promover DES-03 enfraquece: fica registrado como decisão de produto em aberto.

## Duas coisas que o gate deles resolveu do nosso lado

**PROD-08** legitima a revelação fora do software, desde que o material do
debate faça parte do insumo. O teste de permanência do nosso 2.1 vale para
**interface** dentro da simulação, não para material de mediação — que o
nosso 4.2 exige. Origem da emenda: o gate deles.

**DES-01** dá o nome canônico das seções: as do contrato da plataforma (base publicada).
Para missão nova, `unooriaai`, `unoovista` ou `unoochat` — e `tiktooria`, `unoogaleria`, `unoojornal`,
`unooblog`, que existem sem ponte; a tradução do ambiente está em `ambientes.md`, e a seção que o
briefing fixou é trava; as legadas (`instanooria`, `unootube`, `chatgpt`, `whatsappmobile`) só por decisão
registrada do PO (ADR-133 a 138). Roblox não tem seção.

## O que continua fora do nosso alcance

- Verificação no repositório deles: DES-01 (a seção existe?), TEC-11 (dependência de DS pendente?)
- Deriva dos critérios: ver o aviso no topo
