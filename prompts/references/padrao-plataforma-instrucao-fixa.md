---
name: padrao-plataforma-instrucao-fixa
description: A instrução fixa do estudante — capacidade opcional da plataforma, ativada por missão: painel ao lado do aparelho no viewport mobile e overlay sobre o conteúdo em tela cheia de desktop, sempre como camada do hub. Jornada, copy, telas, protótipo e QA de design incluem esta definição e, cada um, só a parte dele (padrao-plataforma-instrucao-fixa-<agente>.md).
sources: [071_jornada, 073_copy_ptbr, 075_telas, 079_prototipo, 088_qa_entregaveis, ambientes, criterios-dev/2-design-imersao, capacidades-plataforma]
status: proposta v2 de 26/10/2026, a validar com o PO — a direção veio da sessão de trabalho, sem parecer do PO; depende de pré-requisito de plataforma
---

# Instrução fixa do estudante — padrão da plataforma (opcional por missão)

**O que é.** A tarefa da missão — o que o estudante deve decidir — fica à vista durante a decisão, numa camada **do hub**, fora do iframe e fora do clone. Não é tela do inventário, não é affordance do ambiente e não é prancha CAA.

**Quando existe.** Só quando a spec traz `instrucao_fixa: sim` no bloco 0 (campo da esteira, como `classe_ambiente`; o nome no manifesto é pendência de plataforma). Sem a linha, vale `nao` e **nada deste arquivo se aplica**: escreva `n/a — capacidade não ativada` onde o prompt pedir. A esteira nunca a ativa por conta própria: quem pede é o PO, no one-pager.

**O texto.** É texto-chave (`TC-nn`) do one-pager. A copy o copia palavra por palavra; ninguém o reescreve nem o encurta.

## Como aparece — conforme o viewport do bloco 0

| Viewport | Apresentação |
|---|---|
| `375x812` (casca de aparelho) | **Painel ao lado do aparelho**, na página do hub |
| `desktop` ou sem viewport (tela cheia), e a projeção única (viewport docente 1366×768) | **Overlay** não modal sobre o conteúdo |
| `<largura>x<altura>` personalizado | Sem regra até a plataforma responder: escreva `[ABERTO — dono: plataforma: apresentação da instrução fixa no viewport personalizado]` |

## Estados — por tela do estudante

`visível` · `recolhida` · `oculta`. Padrão proposto (a validar com o PO): **visível** onde o estudante decide; **recolhida** na tela `pico` e no aha, porque o pico tem o menor teto de elementos e o aha não pode ser precedido de lembrete; **oculta** fora da etapa em que a tarefa vale. A alternativa é visível em todas as etapas. A instrução abre ao entrar na etapa, o estudante a recolhe a uma aba, e `Esc` também recolhe.

## A exceção à DES-13 — só para esta capacidade

A DES-13 e a lista «Proibido dentro da simulação» barram painel da Unooria dentro da simulação, e o overlay cobre o conteúdo do clone. **Origem da exceção:** direção indicada em 26/10/2026 («no caso de tela cheia de desktop, pode ser apresentado como um overlay em cima do conteúdo»), sem parecer do PO; o conflito com a DES-13 segue para o parecer dele. A exceção é escrita e restrita, e vale só se **todas** as condições valem:

1. **Camada do hub**, acima do iframe e fora do DOM da experiência: nenhum token da seção `unooria` entra no clone.
2. **Não modal**: não prende o foco nem bloqueia o clique fora do painel.
3. **Recolhível** por botão e por `Esc`; recolhida na tela `pico` e no aha.
4. **Fora da ação principal**: ancorada numa borda; o D5 define posição e medidas por tela.
5. **Reconhecível como camada do hub**: cabeçalho e borda próprios, para o estudante não a tomar por parte do app clonado.
6. **Acessível**: alvo ≥ 64×64 px (≥ 88×88 na projeção), vão ≥ 16 px, contraste ≥ 4,5:1, foco na ordem de leitura.

Instrução desenhada dentro do iframe, ou com token da `unooria` no DOM do clone, continua violação da DES-13.

## O que depende da plataforma

É capacidade de layout do hub, não Permissions Policy (`capacidades-plataforma.md`): o PRD a leva como pré-requisito de plataforma, e a degradação sem ela é a instrução só na tela de contexto antes. Pendências: o espaço no layout da visão do estudante, a origem do texto (manifesto ou ponte postMessage), quem interpola o recorte da aula e o comportamento da camada em 1366×768.
