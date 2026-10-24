---
name: padrao-plataforma-retencao-lgpd
description: Padrão da plataforma para retenção de dados e LGPD de menores. A missão cita este padrão em vez de decidir prazo, PII e texto livre por conta própria. Consolidado do que já existia no repositório (DAD-07 a DAD-10, formato-spec bloco 9, defaults-missao, infra) — não cria regra nova.
sources: [criterios-dev/4-dados-telemetria-lgpd (DAD-07, DAD-08, DAD-09, DAD-10), formato-spec (bloco 9 e mídia capturada), defaults-missao (classe dados), plataforma-unooria-infra, plano «Produto dono do contrato» (D6)]
status: rascunho v0 — validar com o usuário (produto e responsável de dados) antes de tratar como contrato
---

# Retenção de dados e LGPD — padrão da plataforma

**Por que existe.** Retenção e LGPD se repetem em toda missão, e o fechamento de lacunas (D0) as decidia no design, uma
missão de cada vez: na exp02ef1b o D0-8 fixou «retenção por ano letivo», e na exp03em1b o D0-7 escreveu retenção e
LGPD por conta própria (análise de 23/10/2026). Nenhum desses prazos tinha rotina que o cumprisse, e nenhum passou pelo
PO. Pela decisão D6 do plano «Produto dono do contrato», retenção e LGPD viram **padrão de plataforma**: este arquivo.

**Como se usa.** A spec de produto (bloco 9) e o passo de completude da spec (bloco 15) **citam** o padrão pelo nome —
`padrão: retencao-lacuna-assumida` — e só escrevem o que é próprio da missão (que tabela nova existe, que texto livre
de menor ela coleta e por quê). O design e o dev não reescrevem estas regras: citam este arquivo. Prazo diferente do
padrão é decisão do PO, como `[PROPOSTA — validar com PO: …]`.

**O que este arquivo não é.** Não é parecer jurídico nem política de privacidade: é o que o repositório já exige das
missões, num lugar só. O que estiver marcado 🟡 ainda não foi confirmado pela plataforma.

---

| Nome | Padrão | Fonte |
|---|---|---|
| `retencao-lacuna-assumida` 🟡 | A missão **não inventa prazo de retenção**. Toda tabela nova `expNNefNb_*` declara o prazo **com a rotina que o cumpre**, ou registra a **lacuna assumida por escrito**, com dono **responsável de dados (plataforma)**. Prazo sem rotina é decorativo e não entra (a plataforma já removeu um `expires_at` que nenhuma rotina cumpria). A telemetria analítica é particionada até 2028-12 e não tem rotina de expurgo: a retenção dela é lacuna assumida da plataforma, não da missão. | DAD-10 · `plataforma-unooria-infra.md` · `defaults-missao.md` (`retencao-declarada-ou-lacuna`) |
| `estudante-id-opaco` | `estudante_id` opaco (UUID) em todo dado; a identidade vem sempre do token (o que o cliente mandar nesses campos é descartado). Nome nunca em payload, log ou JSONB de longa duração — no máximo o primeiro nome, vivo só na camada de ficção, nunca gravado. Nenhuma PII em log em texto claro. | DAD-07 |
| `texto-livre-de-menor` | Texto livre digitado por menor **nunca** vai à telemetria analítica. Se a missão precisa dele, vai em **tabela própria, lida só pela professora da escola**, e a spec diz por quê. Payloads de longa duração aceitam só número, booleano ou vocabulário fechado. | DAD-08 · formato-spec bloco 9 · `defaults-missao.md` (`reflexao-e-texto-livre-de-menor`) |
| `dado-sensivel-so-com-decisao` | Missão que toca saúde, sofrimento ou família: nenhum agregado de gestor sem decisão formal; só a professora lê; agregado anonimizado exige DPA e k-anonimato. Sinal de risco tem resposta fixa definida (a IA não é chamada). | DAD-09 |
| `midia-de-menor-quatro-campos` | Voz, imagem, vídeo ou tela de criança não são coletados por padrão. Se a missão grava, o bloco 9 declara os quatro campos, sem exceção: **onde** (tabela com `escola_id` e RLS, ou bucket com caminho não adivinhável), **quanto tempo** (pelo `retencao-lacuna-assumida`), **quem lê** (só a professora da escola) e **o que acontece** sem autorização da família ou sem o recurso no aparelho. | formato-spec bloco 9 (mídia capturada) |
| `so-o-que-a-decisao-produz` | A coleta é só o que as decisões já definidas produzem (escolha, opções, ordem, etapa, cenário de dispositivo). Nome, voz, imagem, texto livre e tempo de tela não entram por padrão. Coleta nova é decisão do PO. | `defaults-missao.md` (classe `dados`) |

## Quem decide o quê

- **Plataforma (este arquivo):** as regras acima. Mudam aqui, uma vez, e valem para toda missão.
- **PO, por missão (no de acordo de produto):** coleta nova, texto livre de menor que a missão precisa, mídia de
  criança e prazo de retenção diferente da lacuna assumida — sempre como `[PROPOSTA — validar com PO: …]`.
- **Ninguém no design nem no dev:** prazo, PII e texto livre não são decididos depois do de acordo de produto. O D0 que
  decidir retenção é barrado em código (`tools/decisoes.py`, tópico de produto).
