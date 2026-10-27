---
name: padrao-plataforma-instrucao-fixa-jornada
description: A instrução fixa na jornada — a Seção 3b, o estado por tela e os três cenários de dispositivo. Só o agente de jornada inclui; a definição está em padrao-plataforma-instrucao-fixa.md.
sources: [071_jornada, padrao-plataforma-instrucao-fixa]
status: proposta v2 de 26/10/2026, a validar com o PO
---

# Instrução fixa — na jornada

Só com `instrucao_fixa: sim`. Sem a linha, escreva `n/a — capacidade não ativada` na Seção 3b.

- **Não é tela.** O ID `E<etapa>-<ator>-<nn>` não tem ator de hub, e ID fora do formato some do Stitch e da conferência. A instrução é **anotação por tela**.
- **Seção 3b — Instrução fixa por tela.** Uma linha por tela do estudante: `| ID | Estado (visível · recolhida · oculta) | Texto-chave (TC-nn) | Por quê |`. Padrão proposto: visível onde há decisão; recolhida na tela `pico` e no aha; oculta fora da etapa em que a tarefa vale. O estado vem do bloco 2 da spec; o que ele não traz é `[ABERTO — dono: PO: estado da instrução fixa na etapa …]`.
- **Teto de elementos.** A instrução vive fora do iframe e, por padrão, não conta no teto da Seção 4. Se decidir assim, escreva `[PROPOSTA — validar com PO: a instrução fixa não conta no teto de elementos da tela · por quê: vive fora do aparelho e recolhe no pico · alternativa: contar como um bloco de texto]`.
- **Cenários de dispositivo (Seção 2).** Na linha «O que muda na tela»: 1 estudante por aparelho mobile, painel ao lado; 2–4 por aparelho, igual ao 1:1; projeção única, overlay (viewport docente, alvos de 88 px). Se o viewport do bloco 0 for desktop, o overlay vale também no 1:1.
