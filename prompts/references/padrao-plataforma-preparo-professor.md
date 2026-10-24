---
name: padrao-plataforma-preparo-professor
description: O preparo do professor — as cinco telas E0-PROF-01…05 e os estados. Padrão da plataforma, igual em toda missão. Jornada, fluxo, telas, protótipo e QA de design incluem esta definição e, cada um, só a parte dele (padrao-plataforma-preparo-professor-<agente>.md).
sources: [071_jornada, 072_fluxo, 075_telas, 079_prototipo, 088_qa_entregaveis, criterios-gate-estrutural, literatura-cognitiva]
status: padrão da plataforma (D7 do plano «Produto dono do contrato», 23/10/2026)
---

# Preparo do professor — padrão da plataforma (`E0-PROF-01…05`)

**O que este arquivo é.** Toda missão é aplicada pelo professor de **qualquer disciplina** — nos anos finais e no Médio, quem leva a turma é o professor de Português, de Biologia, de História —, e o preparo dele no hub é o mesmo em toda missão: escolher a missão, recortar a aula, gerar, curar, pôr no ar. Não é decisão de design por missão, nem contrato de produto por missão: é padrão da plataforma (decisão D7 do plano «Produto dono do contrato», 23/10/2026). Até 24/10/2026 o fluxo estava escrito, com pequenas variações, em cinco prompts de design (jornada, fluxo, telas, protótipo e QA); agora a definição mora aqui, e o que cada agente faz com ela, num arquivo dele (`padrao-plataforma-preparo-professor-jornada.md`, `-fluxo.md`, `-telas.md`, `-prototipo.md`, `-qa.md`). O que varia por missão vem da spec: o recorte e as rotas (bloco 8), o dashboard (bloco 9) e a tabela «a mesma missão em três aulas» (bloco 8).

**O que este arquivo não é.** As telas de condução (`E4-PROF-*`, dashboard, gates de etapa) continuam por missão, desenhadas a partir da spec. E o professor **não** declara habilidades BNCC da própria disciplina: o currículo da missão continua sendo o de letramento digital.

## As cinco telas do preparo (obrigatórias)

Ambiente = `Unooria Hub (kit configuração)`. Peso `serviço` (ou `alta` para o recorte e a curadoria). Uma por passo da jornada do professor:

- `E0-PROF-01` **Escolher a missão no catálogo.**
- `E0-PROF-02` **Recorte da aula** — disciplina (em `Selection`), tema, assuntos (em lista), contexto; o banco default como alternativa (botão «usar banco padrão»).
- `E0-PROF-03` **Geração em andamento** — progresso por polling; e o estado sem saldo de IA.
- `E0-PROF-04` **Curadoria do pacote** — prévia dos itens gerados, editar qualquer texto, regenerar item, aprovar.
- `E0-PROF-05` **Pôr a atividade no ar para a turma** — libera a missão na sala na hora; a plataforma não tem agendamento.

**Estados do preparo:** `vazio` · `gerando` · `sem saldo de IA` · `falha da geração (503)` · `pacote pronto` · `editado` · `ativado`.
