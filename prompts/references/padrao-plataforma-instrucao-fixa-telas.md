---
name: padrao-plataforma-instrucao-fixa-telas
description: A instrução fixa nas telas — a superfície «camada do hub» no Stitch, as duas composições por viewport, componentes e medidas. Só o agente de telas inclui; a definição está em padrao-plataforma-instrucao-fixa.md.
sources: [075_telas, padrao-plataforma-instrucao-fixa]
status: proposta v2 de 26/10/2026, a validar com o PO
---

# Instrução fixa — nas telas

Só com `instrucao_fixa: sim`. Sem a linha, não construa nada disto.

- **Superfície nova: «camada do hub».** Nem o clone (estudante) nem o kit do professor. O DESIGN.md do Stitch é montado em código e precisa declarar essa terceira superfície: se faltar, registre `[ABERTO — dono: plataforma: superfície «camada do hub» no DESIGN.md do Stitch]` em «Lacunas».
- **Duas composições por estado, conforme o viewport do bloco 0**, cada uma com uma linha na tabela «Geração no Stitch» (`DESKTOP`):
  - `375x812`: a página do hub, com o aparelho e o painel ao lado. A tela do clone continua descrita por dentro, como hoje.
  - tela cheia de desktop (e projeção): a tela do clone com o overlay por cima, nos estados aberto e recolhido.
- **Anotação em cada frame do estudante:** `instrução fixa: visível | recolhida | oculta`, igual à Seção 3b da jornada.
- **Componentes** só do kit do hub (o kit «missão aberta» já lista `Collapse`); o que faltar vai para `Componentes locais (candidatos)`, nunca para dentro do iframe.
- **Overlay e painel:** ancorados numa borda, fora da ação principal; você define posição e medidas por tela. Alvos ≥ 64×64 px (≥ 88×88 na projeção), vão ≥ 16 px, foco na ordem de leitura, cabeçalho e borda próprios. São lo-fi: os nove tokens, e nenhum token da `unooria` no frame do clone.
