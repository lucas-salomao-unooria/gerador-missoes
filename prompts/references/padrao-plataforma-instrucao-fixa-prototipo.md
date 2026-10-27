---
name: padrao-plataforma-instrucao-fixa-prototipo
description: A instrução fixa no protótipo — o palco como página do hub (mobile) ou janela com overlay (desktop), elemento irmão do quadro, recolher e o teste 9. Só o agente de protótipo inclui; a definição está em padrao-plataforma-instrucao-fixa.md.
sources: [079_prototipo, padrao-plataforma-instrucao-fixa]
status: proposta v2 de 26/10/2026, a validar com o PO
---

# Instrução fixa — no protótipo

Só com `instrucao_fixa: sim`. Sem a linha, não desenhe nada disto.

- **Aparelho mobile (`375x812`).** O palco é a **página do hub**: o aparelho e o painel de instrução (produto) lado a lado. O painel de revisão (à direita) é ferramenta de revisão e não se confunde com a instrução: se faltar largura em 1280, é o painel de revisão que recolhe (botão), nunca a instrução.
- **Tela cheia de desktop e projeção.** A janela do hub com o overlay por cima do quadro, em **elemento irmão do quadro** (fora de `.quadro-tela`), para o teste da cor e a regra «cor não vaza para dentro do quadro» seguirem valendo.
- **Texto e estado.** O texto vem do sheet (`eN.instrucao.*`), caractere a caractere. O estado de cada quadro vem da Seção 3b da jornada e vai no atributo `data-instrucao` (`visivel` · `recolhida` · `oculta`) do quadro.
- **Recolher.** Por botão (alvo de 64px) e por `Esc`; a instrução abre ao entrar na etapa e fica recolhida onde a Seção 3b manda. Respeite `prefers-reduced-motion`.
- **Exceção da DES-13.** A instrução é camada do hub: cabeçalho e borda próprios, lo-fi nos nove tokens, e nenhum elemento dela dentro do quadro do clone.
- **Teste 9 — instrução fixa.** O texto sai do sheet? O estado bate com a Seção 3b? Ela está fora do quadro, em elemento irmão? Recolhe por botão e por `Esc`? Declare o resultado no relatório.
