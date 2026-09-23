# Padrões de achado pedagógico — vocabulário fechado

Os pareceres de adequação, avaliação e experiência produziram **40 achados de conteúdo real em
14 execuções e nenhum foi fechado**: cada um nascia com um id novo (`E3-A1` era "enunciado
longo" numa sessão, "900 palavras em 10 min" na outra, "termo em inglês" na terceira), e sem
nome estável não há como perceber que o mesmo defeito voltou pela quarta vez.

Ao emitir um achado, classifique-o num destes slugs e ponha no campo `padrao` do envelope. Se
nenhum servir, use `outro` e descreva — slug novo entra aqui depois de aparecer três vezes.

| Slug | O que é |
|---|---|
| `termo-sem-ancoragem` | Palavra técnica ou abstrata usada antes de existir metáfora concreta que a sustente |
| `estrangeirismo-na-interface` | Termo em inglês na tela do estudante fora do clone (dentro do clone é fidelidade) |
| `enunciado-longo` | Texto acima do teto de palavras da faixa, ou tempo de leitura incompatível com a etapa |
| `habilidade-sem-mobilizacao-ativa` | Código BNCC declarado, mas a ação em tela não exercita o verbo do texto oficial |
| `habilidade-decorativa` | Habilidade citada que nenhuma ação sustenta — some do relatório do professor |
| `verbo-desalinhado` | A ação em tela é mais fraca que o verbo da habilidade (reconhecer × analisar) |
| `tempo-insuficiente-etapa` | A etapa não cabe no tempo declarado para ela |
| `dependencia-de-telao` | A missão só funciona com projeção, sem alternativa quando não há |
| `digitacao-longa-celular` | Texto longo exigido em viewport de celular |
| `sem-artefato-observavel` | Objetivo declarado sem nada observável que mostre se foi atingido |
| `repertorio-nao-declarado` | A missão pressupõe repertório prévio que não está declarado |
| `referencia-classe-media` | Exemplo, objeto ou situação que supõe um cotidiano que não é o da rede pública |
| `outro` | Nenhum acima — descreva, e se repetir três vezes vira slug |

**Como isto fecha o ciclo.** O agente 51 lê os padrões que apareceram em **três ou mais
sessões de duas ou mais missões** e propõe a regra permanente no prompt a montante. O que vira
regra deixa de ser achado: é assim que o mesmo defeito para de voltar.
