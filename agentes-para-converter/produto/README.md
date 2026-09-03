# 4 Skills de Validação de Missões Unooria — Rubrica v1.17

**Origem desta versão:** incorpora os 8 gaps identificados no relatório consolidado do Gate 0 (5 execuções, 3 missões, 8 devoluções) e no agente `1-qa-conformidade.md`. Nenhum critério anterior foi removido.

## O que é novo na v1.17 (vs. v1.16)

### gate-estrutural-unooria
- **Passos 4.3 / 4.4 / 4.5** incorporados como steps explícitos no processo de avaliação: mecanismo vs. intenção, caminhos degenerados (5 cenários), mecânica sustenta descoberta central (inclusive em artefatos secundários)
- **Critério 9.4 — Estados de falha mapeados** (obrigatório): para cada dependência do fluxo (dado, conexão, conteúdo, ação de outro ator), o documento precisa descrever o que acontece quando a dependência falha
- **Veredito binário** explicitado com teste de sobrevivência de ⚠️: nomear agentes a jusante e demonstrar que nenhum precisa daquilo
- **Formato de remediação estruturado**: ONDE · POR QUÊ · IMPACTO · COMO (2-3 alternativas com affordance, custo, critério resolvido/aberto) · Recomendação
- **4 saídas obrigatórias**: relatório completo, relatório executivo, alerta ao Artur (em 🔴 ou 🔵), sinais de ofício (🎨)
- **Protocolo de segunda rodada**: reauditoria de correções com verificação de regressão
- **Rastreio de devoluções**: devolução de agente a jusante registrada como falha do gate

### avaliacao-pedagogica-unooria
- **Critério 8.6 — Affordance nativa × guardrail ético** (obrigatório): verbo pode ser 100% nativo (passa no 2.6) e o comportamento real da plataforma violar um guardrail ético. Testa a consequência, não só a existência

### experiencia-aluno-unooria
- Sem alteração

### gate-final-unooria
- Sem alteração (já cobria coerência transversal; os gaps eram todos upstream)

## As 4 skills, em ordem de execução

```
Gerador de missão (gerador-missao-unooria, já existente) → Missão crua
    ↓
1. gate-estrutural-unooria → Completude, formato, spec fechada, mecanismo, caminhos degenerados
    ↓ (corrige antes de seguir)
2. avaliacao-pedagogica-unooria → BNCC, professor, guardrails, affordance × guardrail
3. experiencia-aluno-unooria → Carga cognitiva, faixa etária, agência
    (2 e 3 podem rodar em paralelo)
    ↓
4. gate-final-unooria → Regressão de segurança: coerência + release para design/dev
```

## Contagem total de critérios

| Skill | Obrigatórios | Condicionais | Desejáveis | Total |
|---|:-:|:-:|:-:|:-:|
| gate-estrutural | 19 | 1 | 3 | 23 |
| avaliacao-pedagogica | 14 | 1 | 3 | 18 |
| experiencia-aluno | 8 | 1 | 2 | 11 |
| gate-final | 8 | 0 | 0 | 8 |
| **Total** | **49** | **3** | **8** | **60** |

## Instalação

Copie cada pasta para o diretório de skills do usuário, mantendo a estrutura interna (`SKILL.md` + `references/`).

## Migração

A skill `rubrica-missao-unooria` original pode ser desativada depois que estas 4 estiverem instaladas. As 4 skills v1.16 são substituídas por estas v1.17.
