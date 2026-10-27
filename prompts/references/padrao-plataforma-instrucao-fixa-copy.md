---
name: padrao-plataforma-instrucao-fixa-copy
description: A instrução fixa na copy — chave, texto-chave, registro de voz, parâmetro do professor e teto de palavras. Só o agente de copy da passada 1 inclui; a definição está em padrao-plataforma-instrucao-fixa.md.
sources: [073_copy_ptbr, padrao-plataforma-instrucao-fixa]
status: proposta v2 de 26/10/2026, a validar com o PO
---

# Instrução fixa — na copy

Só com `instrucao_fixa: sim`. Sem a linha, escreva `n/a — capacidade não ativada` na seção do sheet.

- **Chave.** Uma por etapa em que o texto muda, no padrão `eN.instrucao.<nome>`. O texto é o `TC-nn` do one-pager, palavra por palavra; não reescreva nem encurte. Texto que o PO ainda não aprovou é `[ABERTO — dono: PO: texto da instrução fixa na etapa N]`.
- **Voz.** Registro do personagem-guia ou da Unooria, nunca o da plataforma simulada: a instrução vive fora do clone, e a voz da ficção fica dentro do aparelho. Um registro só.
- **Parâmetro do professor** (por exemplo, o tema do recorte da aula). Não há convenção de variável de texto de tela: marque `[ABERTO — dono: plataforma: quem interpola o recorte no texto da instrução]` e use na chave o valor do banco padrão como amostra. Proposta: usar só o `tema` do recorte (até 60 caracteres).
- **Faixa.** O teto de palavras por frase da faixa vale. No 1º–2º ano, `texto+ícone+áudio`; a partir do 3º ano, sem narração por padrão.
- **Spoiler.** A frase fixa fica visível durante toda a decisão: ela não pode entregar a descoberta (D3b do QA).
- **Sheet.** Seção «Instrução fixa» com as chaves `eN.instrucao.*` e o estado por etapa da Seção 3b da jornada.
