---
name: lacunas-abertas
description: Registro único de todas as lacunas das missões — origem, classe, dono, status e o que cada uma bloqueia. Escrito por aprendizado, lido em pré-check obrigatório pelo qa-entregaveis.
sources: [chat]
---

# Lacunas abertas

**Regra que governa este arquivo: missão com qualquer lacuna aberta não passa pelo Gate Final.**

Três disciplinas:
1. **Toda lacuna nasce com dono.** Quem encontrou não é dono; dono é quem pode fechá-la.
2. **Fechar exige apontar onde ficou escrito** — bloco da spec, chave do sheet, ou nó do arquivo. Sem isso, "fechada" quer dizer "esquecida".
3. **Classe é obrigatória.** É o que liga este registro a `candidatos-a-criterio.md` e o que faz a contagem entre missões funcionar.

Classes em uso: `intenção sem mecanismo` · `caminho degenerado` · `não-negociável sem mecanismo` · `affordance nativa × guardrail` · `autodeclaração aceita pelo gate` · `decisão de produto` · `validação externa` · `documental`

---

## Magia ou Truque? (1º EF, TikTok) — Gate 0 🔴

| ID | Origem | Classe | Dono | Status | Bloqueia |
|---|---|---|---|---|---|
| MT-01 | Gate 0 rev2 · 4.3 | intenção sem mecanismo | agente 1 | 🔴 aberta | spec — o primeiro dueto tem que ser de um vídeo salvo e nada garante |
| MT-02 | Gate 0 rev2 · 4.4 | caminho degenerado | agente 1 | 🔴 aberta | spec — quem não salvou nada perde o Ato 3 inteiro |
| MT-03 | Gate 0 · 6.4 | decisão de produto | **Artur** | 🔵 aberta | agente 5 — TikTok ou YouTube Shorts define o chrome |
| MT-04 | Gate 0 v1.1 · 8.3 | decisão de produto | Artur + resp. de dados | 🔵 aberta | spec — retenção, acesso da coordenação, texto às famílias |
| MT-05 | Gate 0 · 5.1/5.6 | validação externa | time pedagógico | 🔵 aberta | argumento curricular da entrega |
| MT-06 | Gate 0 v1.1 · 8.1/8.2 | documental | agente 1 | 🟡 aberta | nada — declarar N/A de IA, uma linha |
| MT-07 | Gate 0 v1.1 · 9.1/9.2 | documental | agente 1 | 🟡 aberta | agente 7 — sem requisitos técnicos não há estimativa |

## Quem ficou fora da mensagem? (7º EF, WhatsApp) — Gate Final 🔁 r2

| ID | Origem | Classe | Dono | Status | Onde fechou / o que bloqueia |
|---|---|---|---|---|---|
| QF-01 | Gate 0 · S1 | intenção sem mecanismo | Claude *(teste)* | ✅ fechada | spec bloco 2 — slot 1 é o boletim do próprio estudante |
| QF-02 | Gate 0 · S2 | caminho degenerado | Claude *(teste)* | ✅ fechada | spec blocos 2 e 3 — exatamente 4, abertura bloqueada |
| QF-03 | Gate 0 · S3 | caminho degenerado | Claude *(teste)* | ✅ fechada | one-pager v1.1 + spec bloco 3 — janela de revisão |
| QF-04 | Gate 0 · S4 | intenção sem mecanismo | Claude *(teste)* | ✅ fechada | spec bloco 2 — Amara em modo admin |
| QF-05 | jornada · L1 | não-negociável sem mecanismo | Claude *(teste)* | ✅ fechada | spec v1.2 bloco 2 — união ≤6 + tag `voz_de_impacto` |
| QF-06 | jornada · L2 | affordance nativa × guardrail | Claude *(teste)* | ✅ fechada | spec v1.2 bloco 5 — enquete sem lista de votantes |
| QF-07 | jornada · L3 | affordance nativa × guardrail | Claude *(teste)* | ✅ fechada | spec v1.2 bloco 2 — versões re-renderizadas |
| QF-08 | wireframes · A1 | não-negociável sem mecanismo | Claude *(teste)* | ✅ fechada | spec v1.2 bloco 2 — fixadas como âncora |
| QF-09 | Gate Final · D6b-01 | intenção sem mecanismo | **agente 1** | 🔴 aberta | handoff sem desfazer — falta uma aresta, não um botão |
| QF-10 | Gate Final · D6b-02 | — | agente 5 | 🔴 aberta | painel sem distribuição de progresso |
| QF-11 | Gate Final · D1-01 | — | agente 5 | ✅ fechada | 21 de 21 telas construídas — verificação pendente na r3 |
| QF-12 | Gate Final · D1b-01 | autodeclaração aceita pelo gate | agente 4 | ✅ fechada | `copy/…-strings-professora.md`, 24 strings |
| QF-13 | Gate Final · D1b-03 | — | **Artur** | 🟡 aberta | 5ª categoria do check D1b: chrome nativo da plataforma |
| QF-14 | fluxo · F1 | caminho degenerado | **agente 1** | 🔴 aberta | spec — nenhum nó de erro de plataforma nas 21 telas |
| QF-15 | Gate 0 · D1/D2 | validação externa | time pedagógico | 🔵 aberta | EF69LP03, EF07CO08 e rastreabilidade seguem `[PREMISSA]` |
| QF-16 | fluxo · legibilidade | documental | agente 3b | 🟡 aberta | camada de rótulos não verificada visualmente (rede) |
| QF-17 | copy professora | — | agente 1 | 🟡 aberta | spec — não existe copy de erro nem de conexão perdida |

## A foto é real. A legenda também? (5º EF, WhatsApp) — Gate 0 🔴

| ID | Origem | Classe | Dono | Status | Bloqueia |
|---|---|---|---|---|---|
| FL-01 | Gate 0 · Ato 6 | intenção sem mecanismo | agente 1 | 🔴 aberta | comparação rodada 1 × 2 sem mecanismo e sem tela nativa (risco 2.1) |
| FL-02 | Gate 0 · Ato 4 | caminho degenerado | agente 1 | 🔴 aberta | consequência assimétrica — nada acontece para quem encaminhou zero |
| FL-03 | Gate 0 · seção 19 | caminho degenerado | agente 1 | 🔴 aberta | nenhum estado de falha de plataforma no contrato de estados |
| FL-04 | Gate 0 · seção 9 | documental | agente 1 | 🟡 aberta | projeção única: sem regra quando a soma dos cartões não fecha |
| FL-05 | Gate 0 · 9.1 | documental | agente 1 | 🟡 aberta | agente 7 — sem lista de requisitos técnicos |

---

## Contagem

**29 lacunas · 10 fechadas · 19 abertas** — 9 🔴, 4 🔵, 6 🟡

**Nenhuma das três missões pode passar pelo Gate Final.**

A missão do 5º ano é a primeira a chegar com **zero lacunas de dono externo** — nada esperando decisão do Artur nem do time pedagógico. Todas as cinco são do agente 1.

### Por classe (é isto que vira emenda de rubrica)

| Classe | n | Nota |
|---|---|---|
| intenção sem mecanismo | 5 | → `candidatos-a-criterio` C1/C3, pronto pra emenda |
| caminho degenerado | 7 | → Passo 4.4 do agente 1 já implementado. **Classe mais frequente do registro** |
| affordance nativa × guardrail | 2 | → C4, segunda ocorrência |
| não-negociável sem mecanismo | 2 | → C3, causa raiz é a ordem 1↔2 |
| decisão de produto | 2 | ambas do Artur |
| validação externa | 2 | ambas do time pedagógico |
| autodeclaração aceita pelo gate | 1 | → C5, corrigido no agente 6 |
| documental | 6 | custo baixo, nenhuma bloqueia mecânica |

### O achado do primeiro dia deste registro

**8 das 10 lacunas fechadas foram fechadas por mim**, marcadas `Claude (teste)`. Todas eram decisão de produto ou de mecânica — dono real era o agente 1 com o time, ou o Artur.

Numa esteira de verdade, oito lacunas fechadas pelo dono errado **é o achado**, não a nota de rodapé. O registro existe para que isso apareça em vez de ficar diluído em quatro arquivos.
