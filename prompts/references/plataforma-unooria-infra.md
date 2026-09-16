# Plataforma Unooria — infraestrutura (índice sobre as cópias sincronizadas)

> **Fonte da verdade são as cópias em `references/plataforma/`** (ver `versao-lida.json`). Este arquivo é só o índice e o que mais muda num PRD.

## O que mais muda num PRD de missão

- **1 contrato = 1 stack GCP** (Cloud Run api + hub, Cloud SQL Postgres 16 com RLS, buckets `-exp` e `-assets`, Pub/Sub para o canal analítico, LB + Cloud Armor, WSO2 IS). Isolamento lógico por `escola_id`.
- **Cloud Run não sustenta WebSocket** para a sala: relógio coletivo é polling HTTP curto (ADR-93/94).
- **Bundle da experiência** publicado em `gs://«contrato»-exp/<expId>/<versao>/`; o CI faz upsert do manifesto e ativa `versaoAtiva`; rollback é trocar `versaoAtiva`. Mídia ≥ 2 MB vai ao bucket `-assets` e o CI **recusa publicar** sem ela (`midia-externa.json`, ADR-63).
- **Quatro ambientes** (`dev-local → dev → hml → main`, ADR-101); deploy parcial tem procedimento; token do deploy vai direto ao Docker.
- **Observabilidade**: OTLP para `telemetry.googleapis.com` via proxy da api (o `resource` precisa de `gcp.project_id`), pino JSON com `codigo` estável e redaction, Clarity (ADR-60), Web Vitals. Sem OpenReplay.
- **Telemetria analítica** particionada até 2028-12, sem rotina de expurgo; retenção é lacuna assumida por escrito (DAD-10). Pub/Sub sem DLQ ainda (`«contrato»-telemetria-dlq` pendente).
- **Sessão** do hub expira com 2 h de inatividade (ADR-95/96). **WAF** não inspeciona corpo autenticado nem texto de estudante (ADR-62).

<!-- include: references/plataforma/infra.md -->

<!-- include: references/plataforma/regras-infra.md -->

<!-- include: references/plataforma/regras-git-e-branches.md -->

<!-- include: references/plataforma/regras-ferramentas-externas.md -->

<!-- include: references/plataforma/regras-documentacao-latex.md -->

<!-- include: references/plataforma/regras-arquivos-de-instrucao.md -->
