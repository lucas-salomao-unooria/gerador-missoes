---
name: pipeline
description: A ordem dos agentes, os dois pontos de decisão humana, e o que cada handoff carrega. Leia antes de acionar qualquer agente.
sources: [chat]
---

# Pipeline de missões Unooria

```
one-pager
   │
   ▼
[1] qa-conformidade ──── 🔴 → ◆ ALERTA AO ARTUR, nada roda
   │  Gate 0 (veredito binário): rubrica + BNCC + PNED
   │  + mecanismo vs. intenção + caminhos degenerados.
   │  ► emite spec/<missao>-spec.md — o contrato da esteira
   ▼
[2] brief-oficio
   │  Aposta, forma do arco, pico, beat, não-negociáveis.
   │  Manda no COMO, nunca no O QUÊ.
   ▼
[3] jornada-figjam
   │  raias no tempo → inventário de telas
   ▼
[3b] fluxo-figjam
   │  grafo de telas: transições, decisões, gates
   │  → lista de arestas + os 5 testes de fluxo
   ▼
[4] copy-ptbr — passada 1
   │  → sheet de strings
   ▼
[5] wireframes-figma
   │  Monta sobre a biblioteca do ambiente.
   ▼
[4] copy-ptbr — passada 2 (revisão em contexto)
   │
   ▼
[3'] gate de ofício ──── devolve → volta ao staff, teto de 2 rodadas
   │  O principal assina a execução do que especificou.
   │  O1–O5 contra jornada/<missao>-direcao.md
   ▼
[6] qa-entregaveis ──── pré-check: lacuna aberta → não passa, roteia por dono
   │  ❌ aberto → loop de feedback, teto de 3 rodadas
   │  D1–D6 + D6b (professora como usuária) + D7 (aderência ao briefing)
   ▼
   ◆ DECISÃO HUMANA 2 — Artur entra. Aprovação final.
   │
   ├──────────────┐
   ▼              ▼
[7] handoff-dev  [7b] brief-assets     ← paralelos, mesmas pré-condições
   stories 🔒     inventário de assets
   spec/eventos   spec por tipo
   escopo V1/V2   ordem de produção
```

**[T] aprendizado** roda transversalmente, acionado de dentro do fluxo: ao fechar o Gate 0, ao fechar o Gate Final, ao fim do handoff, e a cada mudança de versão da rubrica. Nunca edita prompt de agente — escreve em `references/`.

## Dois pontos de decisão humana, não um

**Decisão 1 é no Gate 0, não antes do agente 5.** Missão com 🔵 aberto que afete ambiente, affordance ou tela não passa do gate: ela bloqueia, gera os dois relatórios e alerta você. Construir com o ambiente em aberto é o modo mais caro de errar aqui — o custo aparece dois agentes depois, quando alguém já desenhou.

**Decisão 2 é no Gate Final**, com a missão inteira construída.

## A divisão de escopo

**Agente 1 valida e especifica.** Nada passa se não puder ser entregue do jeito certo. Se passou, a esteira tem tudo: mecanismo em toda etapa, todo caminho tratado, toda decisão fechada. Veredito é binário — "aprovado com ressalvas" não existe mais.

**A esteira constrói contra a spec**, não contra o one-pager. O one-pager é intenção do time; a spec é o contrato.

**Agente 6 valida a nossa esteira**, não a de upstream. Ele pergunta *"a esteira produziu certo?"*, não *"a missão está boa?"*.

**Devolução ao agente 1 é falha do gate**, não fluxo. Contagem de devoluções por missão é a métrica de saúde do agente 1, e a meta é zero.

**O agente 3 é o principal; 3b, 4 e 5 são staff.** O principal traduz o mapa de beats em direção por tela e assina a execução. Staff executa com qualidade técnica verificável — `references/pronto.md` para o que se conta, `references/rubrica-oficio.md` para o que se julga.

**Três camadas de verificação, três donos**, porque se verificam de formas diferentes: `pronto` é contagem, feita pelo próprio agente; o 3' é julgamento com régua escrita; o 6 é critério de rubrica. Misturar as duas últimas recria o conflito de veredito que o agente 6 já evita.

**O agente 2 manda no COMO e fala só com o principal.** Direção que chega direto ao staff cria duas fontes, e o staff escolhe a mais fácil.

## Referências compartilhadas

`references/rubrica-atual.md` · `catalogo-missoes.md` · `marco-legal.md` · `padroes-aprendidos.md` · `candidatos-a-criterio.md` · `glossario-copy.md` · `exemplares.md` · `ambientes.md` · `pronto.md` · `rubrica-oficio.md` · `criterios-dev.md` · `wireframe-cinza.md` · `decisoes-ds.md` · `evidencia-sala.md` · `orcamento-agentes.md`

## Lacuna conhecida

Não existe agente de **enquadramento de problema** antes do Gate 0. O pipeline começa num one-pager pronto e audita pra baixo: nada pergunta qual problema de aprendizagem a missão resolve, qual é a aposta, e o que faria a gente matá-la.
