---
name: teto-palavras-por-faixa
description: Teto de palavras dos textos-chave que a criança lê (texto de tela do §4 e opções de escolha), por faixa, para o lint de produto acusar antes do de acordo o texto aprovado acima do teto. Vale só quando o §15 do one-pager não declara teto de palavras.
sources: [073_copy_ptbr, criterios-experiencia, literatura-cognitiva]
status: rascunho v0 — validar com produto (PM) e pedagogia antes de tratar como contrato
---

# Teto de palavras por faixa (textos-chave)

**O que este arquivo é.** O lint de produto (A024, `tools/contrato_produto.py`) acusa, antes do de acordo, todo texto-chave que a criança lê e que passa do teto de palavras (plano «Produto dono do contrato», PR 7). O texto acima do teto vira item do cartão do de acordo de produto: o PO mantém o texto ou escreve outro. Quem decide é o PO; o lint só mostra.

**De onde vem o teto, na ordem:**

1. **O §15 do one-pager aprovado** («Tetos aplicados à faixa»), quando ele declara teto de palavras com número decidido — é o que o PO aprovou para a missão (os 35 palavras por balão da exp06ef1b). Com vários tetos na mesma missão (legendas, cartões, balões), vale o maior: o lint não sabe a que tipo de texto cada texto-chave pertence, e o maior não acusa texto que outro teto permitiria. Número dentro de `[PARÂMETRO]` ou `[PROPOSTA]` ainda não é teto aprovado, e zero («0 palavras de leitura autônoma») é ausência de leitura, não teto. O teto do §15 conta o texto inteiro.
2. **Sem teto de palavras no §15, a tabela abaixo**, por frase.

**Até ser validada, esta tabela é rascunho.** O repositório não tinha teto de palavras por faixa para texto de tela: tinha a calibragem por frase da copy (`prompts/design/073_copy_ptbr.md`, «Calibragem por faixa») e a cláusula de defasagem do critério 6.1 (`criterios-experiencia.md`: no 9º ano e no Médio, o teto por string é o do 6º–9º, [CONVENÇÃO]). Os números abaixo são esses — nenhum foi inventado aqui. Se o PO quiser outro teto, o caminho é escrevê-lo no §15 do one-pager da missão, ou mudar esta tabela uma vez, com produto e pedagogia.

| Faixa | Anos | Teto (palavras por frase) | De onde |
|---|---|---|---|
| `1-2` | 1º e 2º ano EF | 10 | 073, «Calibragem por faixa»: frase de 6–10 palavras |
| `3-5` | 3º ao 5º ano EF | 15 | 073: até ~15 palavras |
| `6-9` | 6º ao 9º ano EF | 20 | 073: até ~20 palavras |
| `EM` | Ensino Médio | 20 | critério 6.1, cláusula de defasagem (a): o teto do 6º–9º [CONVENÇÃO]; a 073 diz «livre, enxuto» |

**O que o lint conta.** Os textos-chave lidos pela criança: texto de tela do §4 e as opções de cada escolha. O podcast é ouvido e o roteiro do §9 é lido pelo professor: ficam de fora.
