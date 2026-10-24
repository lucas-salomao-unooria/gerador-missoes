---
name: padrao-plataforma-preparo-professor-fluxo
description: O preparo do professor no fluxo — o segundo grafo, com o caminho curto do banco padrão, a volta da curadoria, o gate de ativação e os rótulos do bloco 8. Só o agente de fluxo inclui; a definição das cinco telas está em padrao-plataforma-preparo-professor.md.
sources: [072_fluxo, padrao-plataforma-preparo-professor]
status: padrão da plataforma (D7 do plano «Produto dono do contrato», 23/10/2026)
---

# Preparo do professor — no fluxo, o segundo grafo (obrigatório)

Em **bloco Mermaid próprio**, sob o título fixo `## Fluxo do professor (Mermaid — obrigatório)`: nós `E0-PROF-01…05` (escolher a missão · recorte da aula · geração em andamento · curadoria do pacote · pôr no ar) com os estados encostados `vazio`, `gerando`, `sem saldo de IA`, `falha da geração (503)`, `pacote pronto`, `editado`, `ativado`; a decisão `banco default × gerar com IA`, com o **caminho curto** `E0-PROF-02 -->|usar banco padrão| E0-PROF-05` como aresta própria (o critério 4.3 exige que a missão rode inteira por ele); a volta `curadoria → editar → aprovar`; o gate `ativar atividade`, cuja saída liga ao grafo do estudante pela aresta `atividade ativada → E1-ALU-01`; e os gates de condução (liberar etapa, pausar, zerar turma) com as duas saídas. Os cinco testes do fluxo valem para este grafo também. Rótulos de aresta vêm do bloco 8 da spec (`POST /<modulo>/turmas/«turmaId»/gerar-conteudo`, `GET …/conteudo`, `POST …/homologar`, `POST …/gate`) — nada inventado. O módulo `/atividades` é o motor do Instanooria e não se reusa (`formato-spec`, bloco 8).
