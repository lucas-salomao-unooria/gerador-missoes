# Plataforma Unooria — Padrões de infraestrutura e operação

> Referência gerada a partir de `Fundacao Plataforma Unooria/`, `Identidade Plataforma Unooria/`, `fabrica-de-missoes/` e `plataforma-unooria/{docker,wso2,.github}` (set/2026). Sem valores de segredo — apenas nomes.

## 1. Cloud, projetos e ambientes

- **Provedor único: Google Cloud.** DNS na **Cloudflare** (zona `unooria.com`, proxy desligado). Terraform >= 1.6, state em GCS, um `.tfvars` por ambiente (`envs/dev|hml|prd.tfvars`) + workspace com guardrail.
- Projetos GCP: `entre-redes-dev`, `entre-redes-hml`, prd placeholder. IdP apartado: `wso2-unooria` (dev) / `unooria-identity-prod` — “o encerramento de um contrato jamais derruba o login dos demais”.
- **Região** `us-east1`; **Vertex AI usa `vertex_location = "global"`**.
- Naming: `plataforma-unooria-<env>-*`, `idp-<env>-*`. Labels `app`, `env`, `managed_by=terraform`, `cost_center`.
- Componentes só em dev: n8n, Storybook, OpenReplay.

## 2. Compute — Cloud Run, jobs e bastion

| Serviço | Nome | CPU/Mem | min/max | Concurrency | Notas |
|---|---|---|---|---|---|
| Hub (Next.js) | `plataforma-unooria-<env>-frontend` | 1/1Gi (prd 2/2Gi) | 1 / 5 | 80 | CPU sempre alocada, VPC egress |
| API (NestJS) | `plataforma-unooria-<env>-api` | 2/2Gi | 1 / 5 | 80 | `timeout 900s`; trabalho em processo após `202` (geração IA) |
| Storybook | `plataforma-unooria-dev-storybook` | 1/512Mi | 0 / 3 | — | scale-to-zero, CDN, só dev |
| n8n | `fabricademissoes-dev` | 2/2Gi | 1 / 3 | 80 | session affinity, só dev |
| WSO2 IS | `idp-dev-is` | 2/4Gi | 1 / **1** | 800 | `max_instances = 1` travado (Hazelcast) |

- Probes HTTP (`/healthz` na api, `/api/healthz` no hub), `startup_cpu_boost`.
- **Jobs**: `plataforma-unooria-<env>-migrate` (`prisma migrate deploy`, roda **antes** do deploy da api) e `idp-dev-dbinit`.
- **Bastion** `e2-micro` sem IP externo, acesso via IAP (`terraform output db_tunnel_command`).
- **Experiências (missões) NUNCA viram serviço no Cloud Run** — são bundles estáticos em bucket.

## 3. Rede, LB, WAF, DNS e certificados

- VPC sem subnets automáticas; PSA para Cloud SQL privado; Cloud NAT; **Direct VPC egress** (sem connector).
- **Um Global External HTTPS LB** por ambiente, IP estático, Serverless NEGs para `frontend`/`api`/`storybook`/`n8n` e **backend buckets** para `exp` (CDN TTL 3600) e `assets` (CDN TTL 86400). A api nunca é cacheada. Cloud Run com `INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER`.
- **Cloud Armor**: OWASP CRS 3.3 (`sqli`, `xss`, `lfi`, `rfi`, `rce`, `scannerdetection`, `protocolattack`, sensitivity 1); exclusão da assinatura `921150` nos prefixos `/unoogpt/` e `/ai/` (quebra de linha em texto livre do estudante); allow `/telemetry/ingest`; throttle 2000 req/min/IP → 429; adaptive protection L7. IdP: allowlist admin por CIDR, rate-based ban em auth.
- Certificados via **Certificate Manager**, um por hostname, validação DNS.
- Domínios dev: `entreredes-dev`, `api-entreredes-dev`, `exp-entreredes-dev`, `assets-entreredes-dev`, `storybook-dev` (`.unooria.com`); hml com `-hml`; prd `prd.unooria.com` / `api-prd.unooria.com`. IdP: `idp-dev.unooria.com` / `idp.unooria.com` (o hostname é o `iss` e é congelado).

## 4. Banco de dados e storage

- **Cloud SQL PostgreSQL 16**, sem IP público, `ssl ENCRYPTED_ONLY`, `max_connections = 100`, Query Insights. dev `db-f1-micro` zonal sem backup; hml `db-custom-1-3840` com PITR; prd `db-custom-2-7680` **REGIONAL (HA)**, backups 04:00, PITR 7 dias, 14 backups retidos. Databases: `unooriadb`, `n8n_db` (dev). Senha e `DATABASE_URL` em Secret Manager.
- **Sem Redis/Memorystore.**
- **Buckets GCS** (`uniform_bucket_level_access`):
  - `<project_id>-exp` — bundles das experiências, **público + CDN**, layout `<expId>/<versao>/`; rollback = apontar `versaoAtiva` no manifesto.
  - `<project_id>-assets` — imagens geradas por IA (`atividades/<escolaId>/<activityId>/<postId>.webp`) e mídia pesada (`exp-02-unootube/videos/*.mp4`), **público + CDN**. **Dado de estudante NUNCA entra aqui.**
  - `<project_id>-exp-mapas` — sourcemaps, privado.
  - `<project_id>-planos` — planos de aula, privado, versionado.
  - `<project_id>-n8n-storage` (dev) e buckets do OpenReplay.

## 5. Mensageria — Pub/Sub (canal analítico)

- Tópico `plataforma-unooria-<env>-telemetria`; subscription **push** `-telemetria-ingest` → `$<url_api>/telemetry/ingest`, ack 60s, retenção 7 dias, retry 10s–600s, **sem DLQ**.
- Push autenticado por OIDC token da SA `-push`, `audience = url_api`.
- Entrega **at-least-once**; gravação idempotente por `event_id`.
- Fluxo: `SDK → POST /telemetry/batch → tópico → push → POST /telemetry/ingest → telemetria_eventos`. O canal operacional (`/runs/:id/eventos`) é síncrono e fica **fora** do Pub/Sub.

## 6. Identidade, IAM e segredos

- **WSO2 Identity Server 7.3.0**; **1 contrato = 1 tenant** (`/t/<contrato>/`); fluxo OIDC; claims `escola_id` e `perfil` no **access token** (`perfil` single-valued). Usuários de teste locais: `estudante.teste`, `professor.teste`, `gestor.teste`, `admin.contrato`.
- Hoje o emissor real é o **hub** (RS256 + JWKS em `/.well-known/jwks.json`); a api valida `OIDC_ISSUER`/`OIDC_JWKS_URI`/`OIDC_AUDIENCE = plataforma-api`. Migrar para WSO2 = trocar essas envs.
- Service accounts por função (`-run`, `-api` com `pubsub.publisher`, `-push`, `-deployer`, `-bastion` sem roles). A `-api` tem `roles/aiplatform.user`.
- Secret Manager: `-token-signing-key`, `-auth-secret`, `-perfil-import-token`, `-planos-import-token`, `-db-password`, `-database-url`, `-n8n-encryption-key`; IdP: `-admin-password`, `-internal-crypto-key`, `-keystore-*`.
- **GitHub OIDC / Workload Identity Federation** — sem chave JSON de SA.

## 7. Observabilidade

- 3 uptime checks por ambiente (`/readyz` da api, `/api/healthz` e `/.well-known/jwks.json` do hub), 60s, 3 regiões; alerta quando 2 de 3 regiões falham por 2 min → e-mail.
- Cloud Trace / Error Reporting / OTLP (`telemetry.googleapis.com`); amostragem `obs_trace_ratio` 0.1 (dev), 0.05 (hml). Logs estruturados em `jsonPayload` correlacionados por trace.
- OpenReplay (session replay) só em dev; Microsoft Clarity via `NEXT_PUBLIC_CLARITY_PROJECT_ID`.

## 8. Automação e CI/CD

- **n8n = “Fábrica de Missões”** (dev), Cloud Run `fabricademissoes-dev`, banco `n8n_db`; nenhum workflow versionado. Repo local `fabrica-de-missoes` sobe `pgvector/pgvector:pg16` + `n8n` (RAG); `init-db.sql` só cria extensões `vector` e `uuid-ossp` (não há schema de missão ali).
- **GitHub Actions**: `ci.yml` (typecheck+lint+test com Postgres) e `deploy.yml` (push em `dev`/`hml`): `verificar → mudancas → deploy-api (build → job de migrations → deploy → sonda) → deploy-hub → publicar-exps → ativar-exps → smoke (Playwright)`. `forcar = true` republica tudo.
- Vars de environment: `GCP_PROJECT`, `REGION`, `AR_REPO`, `WIF_PROVIDER`, `DEPLOY_SA`, `API_SERVICE`, `HUB_SERVICE`, `MIGRATE_JOB`, `API_URL`, `HUB_ORIGIN`, `EXP_BUCKET`, `ASSETS_BUCKET`, `ASSETS_BASE_URL`, `EXP_MAPAS_BUCKET`, `CLARITY_PROJECT_ID`; secret `TOKEN_SIGNING_KEY_PEM`.
- Artifact Registry `<region>-docker.pkg.dev/<project>/<repo>/{api,hub}:<sha>`; tag = commit SHA.
- Dev local: `Dockerfile.dev` (Node 26 slim, pnpm 9.12.0), `docker-compose.dev.yml`.

## 9. Requisitos não funcionais implícitos

- **LGPD / menores**: separação público × privado nos buckets; api é a única dona do Postgres; isolamento por `escola_id`; Cloud SQL sem IP público.
- **Segurança**: TLS obrigatório, ingress só via LB, Cloud Armor por backend, WIF sem chaves, secrets nunca em env plain, bastion via IAP.
- **Limites**: `max_connections = 100`; `api_timeout_seconds = 900`; 2000 req/min/IP; `max_instances` 5; ≤80 req concorrentes por instância; mídia >2 MB fora do git e do bundle; escolas atrás de um único NAT.
- **Custos**: `min_instances = 1` + CPU sempre alocada é o item mais caro; IdP prd ~US$440/mês.
- **Produção da fundação ainda não está de pé** (projeto prd placeholder).

## 10. Implicações para implementar e publicar uma missão

1. Código em `apps/experiencias/<exp-id>/`, a partir de `_template`. Publicar exige `package.json`, `public/experiencia.json` e `dist/` — senão o CI pula silenciosamente.
2. **Versão vem do manifesto**: `experiencia.json.versao` define `gs://<project>-exp/<expId>/<versao>/` e a `versaoAtiva`. Divergir do `package.json` gera 404 no hub.
3. Buckets: bundle → `-exp`; imagens e mídia >2 MB → `-assets` (`ASSETS_PUBLIC_URL`); sourcemaps → `-exp-mapas`. **Nunca** dado de estudante em bucket público.
4. Mídia pesada exige `midia-externa.json` `{prefixo, arquivos[]}`; o CI falha se os arquivos não estiverem em `gs://$ASSETS_BUCKET/$prefixo/`. Upload: `gcloud storage rsync -r <dir>/public/videos gs://$ASSETS_BUCKET/$prefixo/`.
5. Autenticação: iframe chama a api com token RS256 do hub (`OIDC_AUDIENCE = plataforma-api`), claims `escola_id` e `perfil`.
6. CORS: origem do bundle em `api_cors_origins`; origem nova exige `api_cors_extra_origins`.
7. Envs relevantes: `NEXT_PUBLIC_API_URL`, `API_INTERNAL_URL`, `NEXT_PUBLIC_CDN_EXP_URL`, `HUB_ORIGIN`, `ASSETS_BUCKET`/`ASSETS_PUBLIC_URL`, `PLANOS_BUCKET`, `TELEMETRIA_TOPIC`, `VERTEX_*`, `OBS_TRACE_RATIO(_CLIENTE)`, `LOG_LEVEL`, `AI_PROVIDER`.
8. Eventos analíticos via `/telemetry/batch` com `event_id` estável (at-least-once, sem DLQ). Eventos de motor/adaptação pelo caminho síncrono.
9. IA só via Vertex (`AI_PROVIDER = vertex`, `VERTEX_LOCATION = global`, ADC); respeitar timeout 900s.
10. Schema entra por Prisma e é aplicado pelo job `-migrate` antes do deploy.
11. WAF: rota nova com texto livre pode bater na regra `921150` (403 no LB sem log na api) — declarar prefixo para exclusão.
12. Deploy: push em `dev`/`hml`; verificação pós-deploy `/healthz`, `/readyz`, `/.well-known/jwks.json`, smoke Playwright.
