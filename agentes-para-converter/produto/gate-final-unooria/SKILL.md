---
name: gate-final-unooria
description: "Gate final de segurança da esteira de validação de missões Unooria. Confere se a missão final está coerente com os vereditos do gate estrutural, avaliação pedagógica e experiência do estudante; bloqueia release quando há obrigatório aberto, correção não incorporada, contradição ou decisão de implementação ainda indefinida. Use SEMPRE depois das três skills quando Vini pedir validação completa, saída final, missão pronta ou liberação para design/dev."
---

# Gate Final — Missões Unooria

Esta skill responde uma única pergunta: **a versão final da missão pode ser entregue para design/dev com segurança, sem contradizer a rubrica nem esconder pendências?**

Não reavalia pedagogia ou faixa etária do zero. Atua como controle de release sobre a missão final e os três relatórios anteriores. Leia `references/criterios-gate-final.md` antes de rodar.

## Entradas necessárias

Usar, sempre que disponíveis:

1. a **missão final já corrigida**;
2. o veredito mais recente de `gate-estrutural-unooria`;
3. o veredito mais recente de `avaliacao-pedagogica-unooria`;
4. o veredito mais recente de `experiencia-aluno-unooria`.

Se algum relatório não existir ou estiver claramente baseado numa versão anterior da missão, F1 = ❌. Não inventar o resultado ausente.

## Como executar

1. Ler `references/criterios-gate-final.md`.
2. Confirmar que os três relatórios avaliam a mesma versão da missão.
3. Fazer uma varredura de todos os obrigatórios e localizar qualquer ❌, 🔵 ou N/A por falta de informação.
4. Conferir se cada correção exigida realmente entrou na missão final.
5. Procurar contradições entre missão e relatórios.
6. Reaplicar o teste de implementação cega do 9.1 apenas como regressão: correções posteriores não podem reabrir regras.
7. Verificar se a descoberta central continua intacta.
8. Emitir o veredito de release.

## Regra de rerun

Se o gate final encontrar falha que pertence a uma das três skills, **não reavaliar tudo automaticamente**. Indicar qual skill precisa ser rerodada após a correção. Se a correção afetar mecanismo central, handoff ou carga decisória, rerodar todas as dimensões impactadas.

## Formato da saída

1. **Veredito no topo:** `🟢 LIBERADA PARA DESIGN/DEV` ou `🔴 BLOQUEADA PARA DESIGN/DEV`.
2. **Tabela apenas dos F-criteria não-✅**: critério, status, evidência da inconsistência.
3. **Pendências de release**, cada uma com `onde está`, `por que bloqueia`, `skill responsável`, `menor correção necessária`.
4. **Riscos aceitos (⚠️)**, se existirem, separados de bloqueios.
5. Se tudo estiver verde, uma frase curta: “As três avaliações e a missão final estão coerentes; nenhum obrigatório ou decisão de implementação permanece aberto.”

## Posição na esteira

```
gerador-missao-unooria
    ↓
gate-estrutural-unooria
    ↓
avaliacao-pedagogica-unooria + experiencia-aluno-unooria
    ↓
>>> gate-final-unooria <<<
    ↓
design/dev
```

Este gate é obrigatório quando o pedido for “roda tudo”, “valida completa”, “está pronta?”, “libera para design/dev” ou equivalente.
