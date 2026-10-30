---
name: formato-relatorios
description: Gabaritos de saída dos gates — esquema de ID, achados, resumos, alertas e tickets. Lido por qa-conformidade, qa-entregaveis e pelo gate de ofício.
sources: [chat]
---

# Esquema de ID — vale em todo relatório da esteira

| Prefixo | O que é | Severidade no envelope |
|---|---|---|
| `L<n>` | Lacuna que bloqueia | `bloqueio` |
| `A<n>` | Atenção, não bloqueia | `atencao` |
| `D<n>` | Decisão de produto | `decisao_humana` |
| `O<n>` | Achado de ofício | `oficio` |
| `T<n>` | Ticket do Gate Final | conforme o achado |

Numeração contínua por relatório, reiniciando a cada rodada. **Um ID por
achado, e o mesmo ID viaja no markdown e no envelope** — é o que permite
contar classe por missão sem reconstruir à mão.


# Resumo executivo do Gate 0 → `qa/<missao>-resumo.md`

```markdown
# <Missão> — Resumo do Gate 0

**Ano/faixa:** · **Ambiente:** · **Rubrica:** vX.X · **Data:**
**Veredito: 🔴 BLOQUEADO | 🟡 APROVADO COM RESSALVAS | 🟢 APROVADO**
<uma frase dizendo o que isso significa na prática>

## 🔴 NO GO — bloqueiam o avanço (n)
- **[código] Título curto** — o problema em uma frase.
  **Corrigir:** a ação, em uma linha. *(custo: baixo/médio/alto)*

## 💡 Sugestões e Recomendações para Itens Bloqueados (Como Sanar)
Para cada item 🔴 bloqueado:
- **[código] Como sanar:** orientação prática, acionável e direta de como ajustar a mecânica, narrativa ou regra.
- **Alternativa recomendada:** affordance nativa, copy ou mecânica sugerida para destravar o critério sem reabrir decisão de produto.
- **Exemplo de aplicação / redação:** texto ou especificação pronta para o revisor colar e sanar o bloqueio.

## 🟡 ATENÇÃO / ITENS DE ALERTA — não bloqueiam, mas precisam de ajuste (n)
- mesmo formato (inclui ressalvas e itens de alerta da BNCC de disciplinas tradicionais, socioemocionais ou pendências documentais).

> [!NOTE]
> **Regra curricular de bloqueio da BNCC:** apenas habilidades relativas a **letramento digital** (BNCC Computação — Cultura Digital) têm o poder de bloquear a missão (🔴 NO GO). As demais regras da BNCC (disciplinas curriculares tradicionais, socioemocionais, códigos complementares) entram obrigatoriamente nesta seção como **itens de alerta (🟡 ATENÇÃO)** com ressalvas, permitindo o avanço da missão.

## 🔵 DECISÃO DE PRODUTO — fora do alcance do QA (n)
- **[código] Título curto** — a escolha que precisa ser feita e por quem.

## 🎨 SINAIS DE OFÍCIO — insumo pro briefing (n)
- **[beat] Sinal** — e a alternativa sugerida.

## ✅ Não mexer — está resolvido
- 3 a 5 bullets do que está sólido e não deve ser tocado na correção.

## Placar
| | ✅ | 🟡 | 🔴 |
|---|:-:|:-:|:-:|
| Obrigatórios | | | |
| Condicionais | | | |
| Desejáveis | | | |

**Menor caminho pro verde:** as 2–3 correções que destravam mais critérios por esforço.
```

# Alerta ao Artur → mensagem, não arquivo

```markdown
**⛔ <Missão> — <ano> — <ambiente>**
**Gate 0: <veredito>** · rubrica vX.X

**O que trava (n):**
- [código] uma linha cada

**Precisa de decisão sua (n):**
- [código] a escolha, e por que não é do QA

**Menor caminho pro verde:** 1 a 3 itens.
**Relatórios:** `qa/<missao>-gate0.md` · `qa/<missao>-resumo.md`
```

Curto. O detalhe está no relatório; o alerta traz o que exige ação.

# Bloco de achado 🔴 (Passo 5 do Gate 0)

```markdown
### `L<n>` — 🔴

**CLASSE:** uma de — caminho degenerado · intenção sem mecanismo ·
affordance × guardrail · não-negociável sem mecanismo · ausência de estados
de falha · documental · decisão de produto · validação externa.
Classe nova exige registro em `candidatos-a-criterio.md`.

**ONDE:** etapa/seção exata, com o documento **citado literalmente**.
**POR QUÊ:** qual teste prático falhou, e o que o documento diz (ou não diz).
**IMPACTO:** o que quebra na experiência do aluno, em uma frase.

**COMO — alternativas de mecânica:**
1. [Alternativa] — o que muda na tela, qual affordance nativa usa, custo
   (baixo/médio/alto), qual critério resolve, e se abre risco em outro.
2. [Alternativa]
3. [Alternativa, se houver]

**Recomendação:** qual, e por quê.
```

Toda alternativa proposta respeita: uma seção do DS para missão nova (`ambientes.md`), e a que o briefing fixou quando fixou · verbo nativo real da plataforma · nenhuma interface Unooria dentro da simulação (escapes: contexto antes, fechamento depois) · os tetos da faixa · nenhum julgamento do aluno como pessoa.

Se nenhuma alternativa dentro da lista fechada resolver, diga isso: a missão precisa mudar de mecanismo, não forçar encaixe.

# Ticket do Gate Final (agente 6)

```markdown
### [ID] — [D1–D7] — [🔴 bloqueia / 🟡 ressalva]
**Agente responsável:** jornada | fluxo | telas | copy-ptbr | qa-conformidade
**ONDE:** frame, ID de tela, chave de string, aresta ou célula da jornada
**O QUÊ:** a divergência, com o que existe hoje citado
**POR QUÊ:** critério da rubrica, bloco da spec, ou direção do briefing afetada
**COMO:** correção esperada, específica o suficiente para ser executada sem nova interpretação
```

Um ticket vai para **um** agente. Se a correção exige dois, quebre em dois com a ordem de execução explícita (jornada antes de fluxo, fluxo antes de wireframe, copy antes de wireframe).

# Alerta do Gate Final → mensagem, não arquivo

```
**Missão:** [nome] — [ano] — [ambiente]
**Status:** APROVADO PARA REVISÃO HUMANA | IMPASSE APÓS 3 RODADAS

**Links:** folha de diagramas · board no Miro · projeto no Stitch · sheet de copy

**Veredito por dimensão:** D1 ✅ · D2 ⚠️ · D3 ✅ · D4 ✅ · D5 ✅ · D6 ✅

**O que mudou no caminho:** rodadas executadas, quantos tickets por agente, as 2–3 correções que mais mexeram no resultado.

**Precisa de decisão sua (não de execução):**
- códigos BNCC/SAEB marcados a validar com o time pedagógico
- ressalvas ⚠️ que aceitei conscientemente, e por quê
- trade-offs onde duas alternativas eram defensáveis e escolhi uma

**Onde eu olharia primeiro:** 2–3 pontos específicos, com frame ou tela.
```

Não encha o alerta com o que passou. O que passou está no relatório.

# Ticket do gate de ofício

```markdown
### `O<n>` — [O1–O5] — 🔁 devolve

**Agente responsável:** copy-ptbr | telas | fluxo
**DIREÇÃO:** a linha de `jornada/<missao>-direcao.md`, citada literalmente
**CONSTRUÍDO:** o que existe hoje, com frame ou chave de string
**ITEM DA RÉGUA:** O1–O5, e o "devolve quando" que se aplica
**COMO:** a correção esperada, executável sem nova interpretação
```

Ticket sem a direção citada não é ticket — é gosto, e o staff tem o direito
de recusar.
