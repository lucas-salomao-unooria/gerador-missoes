# Critérios do Gate Final Unooria — Rubrica v1.16

Este gate não substitui as três avaliações anteriores. Ele valida a **coerência da saída final** e decide se a missão pode ser liberada para design/dev.

|#|Critério|Tipo|Teste prático|
|-|-|-|-|
|F1|**Cobertura da esteira** — Gate estrutural, avaliação pedagógica e experiência do estudante foram executados sobre a mesma versão da missão.|Obrigatório|Os três vereditos existem e apontam para a mesma versão? Se uma skill avaliou versão anterior às correções, → ❌ e rerodar a skill afetada.|
|F2|**Nenhum obrigatório aberto** — Não há ❌, 🔵 ou N/A por falta de informação em critério obrigatório.|Obrigatório|Varra os três relatórios. ⚠️ só pode passar se for risco consciente que não deixa regra/fonte obrigatória aberta. Qualquer obrigatório ❌/🔵/N/A-falta-info → ❌ final.|
|F3|**Correções incorporadas** — Toda correção que sustentou mudança de veredito aparece de fato na missão final.|Obrigatório|Compare a missão final com as correções exigidas. Não aceite “corrigido” apenas no relatório; a redação/regra precisa estar no one-pager.|
|F4|**Coerência entre missão e vereditos** — Nenhum relatório afirma algo contradito pelo documento final.|Obrigatório|Ex.: relatório diz “exatamente 4 com bloqueio” mas missão só diz “escolha 4”; relatório diz “BNCC confirmada” sem fonte; missão diz “pronta” e mantém pendência obrigatória. Contradição → ❌.|
|F5|**Fechamento de implementação** — A versão final continua passando no teste de implementação cega depois das correções pedagógicas/etárias.|Obrigatório|Reaplique apenas o núcleo do 9.1: cardinalidade/bloqueio, geração de outputs, estados incompletos, quem termina cedo, conta/ator publicador, permissões/handoffs e fallbacks. Correções posteriores podem ter reaberto uma decisão de produto.|
|F6|**Descoberta central preservada** — As correções das três skills não descaracterizaram o mecanismo oculto ou o aha moment.|Obrigatório|A frase de descoberta, a ação principal e a virada ainda formam a mesma cadeia causal? Se uma correção transformou a missão em outra experiência, → ❌ e devolver para revisão, não “consertar” silenciosamente no gate final.|
|F7|**Rastreabilidade de pendências e riscos** — Desejáveis/⚠️ restantes estão explicitamente registrados sem serem apresentados como obrigatórios resolvidos.|Obrigatório|Todo risco remanescente tem status, impacto e dono/hipótese quando aplicável. Não pode haver pendência escondida sob “pronta”.|
|F8|**Veredito único de release** — A saída distingue qualidade da missão de liberação para produção.|Obrigatório|Emitir apenas **🟢 LIBERADA PARA DESIGN/DEV** ou **🔴 BLOQUEADA PARA DESIGN/DEV**. Não usar “pronta” se F1–F7 não estiverem verdes.|

## Regra de segurança

O gate final é conservador: ele **não cria novas soluções de produto por conta própria**. Se detectar uma decisão aberta, aponta exatamente a lacuna e devolve para a skill responsável/revisão da missão. Só pode aplicar correções editoriais triviais que não mudem mecânica.

## Roteamento da falha

- Estrutura, estados, cardinalidade, ownership, fallback → `gate-estrutural-unooria`.
- BNCC, rastreabilidade, professor, guardrails → `avaliacao-pedagogica-unooria`.
- Carga, linguagem, ritmo, espera, complexidade etária → `experiencia-aluno-unooria`.
- Contradição entre relatórios ou correção não incorporada → corrigir a missão e rerodar apenas as skills afetadas antes de repetir o gate final.
