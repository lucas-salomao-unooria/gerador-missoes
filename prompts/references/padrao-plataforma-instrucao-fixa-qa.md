---
name: padrao-plataforma-instrucao-fixa-qa
description: A instrução fixa no QA de entregáveis — o que cada dimensão confere a mais e como a exceção da DES-13 é auditada. Só o agente de QA de design inclui; a definição está em padrao-plataforma-instrucao-fixa.md.
sources: [088_qa_entregaveis, padrao-plataforma-instrucao-fixa]
status: proposta v2 de 26/10/2026, a validar com o PO
---

# Instrução fixa — no QA de entregáveis

Só com `instrucao_fixa: sim` na spec. Sem a linha, a capacidade não existe e a ausência não é achado.

- **D1 e D1b.** A chave `eN.instrucao.*` do sheet bate, caractere a caractere, com o frame e com o protótipo, e com o `TC-nn` do one-pager. O estado de cada tela bate entre a Seção 3b da jornada, a especificação e o protótipo.
- **D3b.** O texto fica visível durante a decisão: aplique o teste do spoiler a ele.
- **D4 e D4a.** Teto de palavras por frase; contraste ≥ 4,5:1; alvo ≥ 64×64 px (88×88 na projeção) e vão ≥ 16 px; a instrução vem antes do conteúdo na ordem de foco; recolher por teclado (`Esc`).
- **D5 e D6.** A projeção única usa o overlay. A professora sabe o que a turma está vendo?
- **O1.** A tela `pico` recolhe a instrução; instrução aberta no pico é achado de ofício, sem bloqueio.
- **DES-13.** A instrução é a exceção escrita: não aponte violação quando as seis condições da definição valem. Descumprir uma é ❌ com dono `telas` (composição), `copy-ptbr-revisao` (texto) ou `prototipo-navegavel` (HTML). Instrução dentro do quadro do clone, ou com token da `unooria` no DOM do clone, é ❌ por DES-13.
- **Dono do pré-requisito.** A capacidade depende da plataforma. Falta de suporte no hub não é defeito do design: é pendência de plataforma, registrada em «Riscos aceitos».
