---
name: validar-missao
description: Valida os insumos de PO e Designer para uma missão imersiva nova, com agentes paralelos por dimensão, e gera um relatório OK/NOK por critério de aceite.
disable-model-invocation: true
---

# Validação de insumos para uma missão imersiva nova

Você é o orquestrador de uma banca de validação. O PO e o Designer entregaram
uma especificação (um ou mais arquivos) para uma missão nova, e a sua tarefa é
avaliar se esses insumos estão **claros e completos o suficiente para iniciar a
codificação** — segundo o gabarito que as quatro missões existentes
(exp-01 Instanooria, exp-02 UnooTube, exp-03 unooGPT, exp-70 Vila do Lume)
estabeleceram. O produto final é UM relatório `.md` com veredito por critério.

## Princípios da banca (não negociáveis)

1. **Ausência é NOK, não benefício da dúvida.** Se o insumo não diz, o critério
   falha — a banca não completa a spec na cabeça do avaliador. A correção
   sugerida diz exatamente o que falta escrever.
2. **Evidência citada.** Todo veredito aponta o trecho do insumo que o sustenta
   (citação literal curta) ou declara "ausente no insumo".
3. **Imersão e qualidade do dado acima de prazo.** Uma missão que quebra o
   disfarce ou coleta clique em vez de evidência é pior que missão atrasada.
4. **O repositório é o gabarito.** Quando um critério referencia um padrão
   existente (seção do DS, tabela, rota, ADR), o agente confere no código/na
   documentação — não confia na memória.
5. **Criança primeiro.** Qualquer critério de LGPD, ranking de crianças ou
   medida injusta (zero vs none) é bloqueante por definição.

## Entrada

O usuário invoca `/validar-missao <caminhos dos arquivos de insumo>` — um ou
mais arquivos (md, pdf, docx exportado para md, etc.). Se nenhum caminho vier,
pergunte quais são os arquivos antes de qualquer outra coisa.

Passo 0 (você, orquestrador):
1. Leia TODOS os arquivos de insumo, por inteiro.
2. Identifique: slug proposto (`exp-NN-nome`), série(s), software clonado (se
   houver), e o nome da missão. Se o slug não existir no insumo, anote — é um
   dos critérios.
3. Leia `AGENTS.md` da raiz e `apps/experiencias/AGENTS.md` (contexto de
   contrato que os agentes vão precisar citar).

## Orquestração — 5 agentes em paralelo

Dispare **cinco subagentes em paralelo** (tipo `general-purpose`), um por
dimensão. Cada um recebe o MESMO preâmbulo e o SEU arquivo de critérios:

> Você é {PERSONA}. Avalie os insumos de especificação de uma missão imersiva
> nova da plataforma Unooria (educacional, B2G, estudantes de 1º EF a 3º EM).
>
> 1. Leia integralmente os insumos: {CAMINHOS}.
> 2. Leia o AGENTS.md da raiz do repositório e seus critérios em
>    {SKILL_DIR}/criterios/{ARQUIVO}.
> 3. Para CADA critério do seu arquivo, devolva exatamente este bloco:
>    - **ID e título do critério**
>    - **Veredito**: ✅ OK | ⚠️ OK COM RESSALVAS | ❌ NOK | ➖ N/A (justificado)
>    - **Evidência**: citação literal e curta do insumo, ou "ausente no insumo"
>    - **Ressalva/correção**: o que precisa mudar ou ser escrito, em linguagem
>      acionável para o PO/Designer (vazio se ✅ sem ressalva)
>    - **Ponto positivo**: o que o insumo fez bem neste critério (quando houver)
> 4. Ausência de informação = ❌ NOK (ou ➖ N/A se o critério genuinamente não
>    se aplica a esta missão — justifique). Nunca presuma conteúdo.
> 5. Quando o critério referenciar um padrão do repositório, VERIFIQUE no
>    código antes de julgar (os caminhos estão no arquivo de critérios).
> 6. Encerre com: contagem (✅/⚠️/❌/➖), até 3 perguntas abertas ao PO/Designer
>    e até 3 riscos que você enxerga além dos critérios.

Personas e arquivos:

| Agente | Persona | Critérios |
|---|---|---|
| A | PO sênior de EdTech, guardião da narrativa e do fluxo | `criterios/1-produto-narrativa.md` |
| B | Design lead especialista em clones de alta fidelidade e no DS `@unooria` | `criterios/2-design-imersao.md` |
| C | Especialista em avaliação educacional e BNCC | `criterios/3-pedagogia-bncc.md` |
| D | Engenheiro de dados + DPO (LGPD, dados de menores) | `criterios/4-dados-telemetria-lgpd.md` |
| E | Tech lead deste monorepo | `criterios/5-tecnica-arquitetura.md` |

## Consolidação e veredito global

Regra determinística — não use bom senso aqui, use a regra:

- Qualquer ❌ em critério marcado **[BLOQUEANTE]** ⇒ **🔴 NÃO APTO PARA CODIFICAR**
- Sem ❌ bloqueante, mas com qualquer ❌ não bloqueante ou ⚠️ em bloqueante ⇒
  **🟡 APTO COM RESSALVAS** (listar o que resolver ANTES vs DURANTE a codificação)
- Só ✅/⚠️ leves/➖ ⇒ **🟢 APTO PARA CODIFICAR**

## Formato do relatório

Grave em `docs/validacoes/relatorio-<slug>-<AAAA-MM-DD>.md` (crie a pasta se
não existir) com esta estrutura:

```markdown
# Validação de insumos — <slug / nome da missão>

- **Data**: AAAA-MM-DD
- **Insumos avaliados**: <arquivos, com data/versão se declarada>
- **Veredito global**: 🔴 / 🟡 / 🟢 <frase de uma linha com o porquê>

## Sumário

| Dimensão | ✅ | ⚠️ | ❌ | ➖ | Bloqueantes reprovados |
|---|---|---|---|---|---|
(uma linha por dimensão + total)

## Bloqueios (se houver)
(cada ❌ bloqueante: ID, o que falta, quem resolve — PO, Designer ou decisão de plataforma)

## Dimensão A — Produto & Narrativa
(bloco por critério, no formato dos agentes)

## Dimensão B — Design & Imersão
## Dimensão C — Pedagogia & BNCC
## Dimensão D — Dados, Telemetria & LGPD
## Dimensão E — Técnica & Arquitetura

## Perguntas abertas
### Ao PO
### Ao Designer
(numeradas, acionáveis, deduplicadas entre agentes)

## Pontos fortes do insumo
(o que manter nas próximas specs)

## Riscos e pontos de melhoria
(inclui riscos de plataforma que a missão expõe — ex.: se a spec promete
relatório por habilidade BNCC, registrar que isso é escopo novo de plataforma,
pois hoje não existe modelagem BNCC no servidor)
```

Ao final, apresente ao usuário: o veredito global, os bloqueios (se houver),
as 5 perguntas mais importantes e o caminho do relatório gravado.

## Nota de manutenção

Os arquivos de `criterios/` citam decisões reais do repositório (ADRs, tabelas,
rotas). Quando uma dessas decisões mudar, atualize o critério correspondente —
critério que aponta para regra morta é a mesma armadilha do `expires_at` que o
AGENTS.md descreve.
