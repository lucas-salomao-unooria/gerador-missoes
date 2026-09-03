# 🌌 Gerador de Missões Unooria — Produto → Design → Dev

Pipeline multiagente construído com o **Google ADK (Agent Development Kit)** que transforma o one-pager (ou a ideia) de uma missão de letramento digital em um **PRD padrão ouro**, pronto para alimentar um agente de codificação no monorepo `plataforma-unooria`.

Três áreas em sequência, cada uma com seus agentes especializados, dois pontos de paralelismo, um loop de correção e gates determinísticos:

```
one-pager / ideia (+ PDF/DOCX)
   │
   ▼
🧭 PRODUTO ──────────────────────────────────────────────────────────────────────
   P0  One-pager           normaliza ou redige o one-pager canônico (18 seções)
   ┌─ LoopAgent (≤ 3 rodadas) ────────────────────────────────────────────────┐
   │ P1  Gate estrutural    23 critérios · veredito binário 🟢/🔴 + envelope  │
   │ P1c Check (determinístico) lê o envelope → repete, segue ou bloqueia     │
   │ P1b Revisor            aplica o "complemento pronto pra colar"           │
   └──────────────────────────────────────────────────────────────────────────┘
   ┌─ ParallelAgent ──────────────────────────────────────────────────────────┐
   │ P2  Avaliação pedagógica   BNCC, professor, guardrails, affordance×guardrail│
   │ P3  Experiência do estudante  carga cognitiva, faixa etária, agência      │
   └──────────────────────────────────────────────────────────────────────────┘
   P4  Gate final de produto  🟢 LIBERADA / 🔴 BLOQUEADA para design/dev
   P5  Spec da missão         os 12 blocos — o contrato da construção
   │
   ▼
🎨 DESIGN (MCP do Figma nos agentes 🎨) ─────────────────────────────────────────
   D1  Briefing de ofício     aposta, arco, pico, beat memorável, não-negociáveis
   D2  Jornada (FigJam) 🎨    raias × 6 etapas, inventário de telas, direção por tela
   D3  Fluxo de telas (FigJam) 🎨  grafo com condições, gates, 5 testes, arestas
   D4  Copy PT-BR (passada 1) sheet de strings por tela
   D5  Wireframes lo-fi (Figma) 🎨  escala de cinza sobre a seção do DS do ambiente
   D6  Copy PT-BR (passada 2) revisão em contexto
   D7  QA de entregáveis 🎨   fidelidade à spec, diff de strings, D1–D7, ofício O1–O5
   │
   ▼
🛠️ DEV ──────────────────────────────────────────────────────────────────────────
   ┌─ ParallelAgent ─────┐  V1 Handoff para dev (insumo, stories 🔒, eventos, V1/V2)
   │                     │  V1b Brief de assets
   └─────────────────────┘
   ┌─ ParallelAgent — banca /validar-missao (72 critérios, 21 bloqueantes) ──┐
   │ V2a Produto & Narrativa · V2b Design & Imersão · V2c Pedagogia & BNCC   │
   │ V2d Dados, Telemetria & LGPD · V2e Técnica & Arquitetura                │
   └──────────────────────────────────────────────────────────────────────────┘
   V3  Consolidação da banca  🟢 / 🟡 / 🔴 determinístico
   V4  PRD padrão ouro        + contexto arquitetural da plataforma  ← ENTREGÁVEL
   │
   ▼
🧠 T · Aprendizado   catálogo, lacunas por classe, devoluções ao gate, candidatos a critério
```

---

## O que sai do pipeline

`output/<data>-<slug>/` com todos os artefatos em Markdown mais `estado.json`:

| Pasta | Artefatos |
|---|---|
| `produto/` | one-pager final, gate estrutural, avaliação pedagógica, experiência do estudante, gate final, **spec da missão** |
| `design/` | briefing de ofício, jornada + inventário + direção, fluxo (Mermaid + arestas), copy 1 e 2, cobertura dos wireframes, QA de entregáveis |
| `dev/` | handoff (modelo de insumo preenchido, stories, eventos, escopo), brief de assets, 5 relatórios da banca, consolidação |
| raiz | **`PRD.md`**, `aprendizado.md`, `estado.json`, `briefing-original.md` |

O **PRD** segue o gabarito de 25 seções em `prompts/references/prd-padrao-ouro.md` (Cagan/SVPG, Google Design Docs, Spec Kit, Kiro/EARS, Gherkin, ADR, C4, INVEST, DoD, RTM, checklist de NFR, LGPD art. 14, práticas de context engineering da Anthropic): frontmatter YAML com status e gates, resumo executivo, objetivos com KPIs e eventos, não-objetivos, personas, as 6 etapas, máquina de estados, user stories, RF com IDs e critérios EARS, RNF com número e método, UX com links Figma/FigJam, modelo de dados, contratos de API, eventos, pedagogia, dependências, arquitetura, **plano de implementação com caminhos reais do monorepo**, tarefas com comando de verificação, riscos, ADRs e `[NEEDS CLARIFICATION]`, testes e DoD, rollout, glossário, apêndices.

---

## Controle de fluxo (determinístico, sem LLM)

- Cada gate termina com um **envelope JSON** (`references/contrato-saida.md`). O `EnvelopeGateAgent` (`agents/checkers.py`) lê o envelope, grava o status no `session.state` e decide: **repetir** (loop gate ↔ revisor), **seguir** ou **bloquear**.
- Em **modo estrito** (`PRODUTO_MODO_ESTRITO=true`, padrão), missão bloqueada no gate estrutural após as rodadas ou no gate final **interrompe design e dev**: os agentes a jusante carregam o `before_agent_callback` `skip_if_blocked` e são pulados; a saída final vira o relatório do gate com o alerta ao responsável de produto. Com o modo desligado, o pipeline segue e o PRD registra as pendências no frontmatter e na seção 20.
- QA de design e banca de dev **não bloqueiam** o PRD: seus vereditos entram no frontmatter (`gates`) e nas pendências.
- Decisões de produto (🔵) nunca são tomadas por agente: ficam marcadas `[DECISÃO PENDENTE — responsável de produto]` até um humano decidir.

---

## Estrutura do projeto

```
gerador-missoes/
├── app.py                      Streamlit: pipeline ao vivo por etapa, artefatos, editor de prompts e referências
├── config.py                   AppSettings (Gemini, pipeline, Figma MCP, saída)
├── test_pipeline.py            testes estruturais (prompts, árvore, envelope, fluxo com agentes falsos)
├── agents/
│   ├── base.py                 fábrica de LlmAgent (thinking, include_contents, callbacks)
│   ├── callbacks.py            envelope JSON, inferência de status, skip_if_blocked
│   ├── checkers.py             EnvelopeGateAgent (BaseAgent determinístico)
│   ├── produto/__init__.py     P0…P5 + build_produto_stage (Sequential › Loop › Parallel)
│   ├── design/__init__.py      D1…D7 + build_design_stage (toolsets Figma por agente)
│   ├── dev/__init__.py         V1…V4 + build_dev_stage (banca em paralelo)
│   └── transversal/__init__.py T · aprendizado
├── pipeline/
│   ├── orchestrator.py         árvore de agentes, metadados por etapa
│   ├── runner.py               Runner ADK + streaming de eventos (thoughts, tools, gates)
│   └── artifacts.py            grava output/<data>-<slug>/
├── prompts/
│   ├── loader.py               includes (`<!-- include: references/x.md -->`) + variáveis
│   ├── produto/  design/  dev/  transversal/   um .md por agente
│   └── references/             rubricas, gabaritos, plataforma-unooria-{software,infra,design-system}.md, prd-padrao-ouro.md
├── tools/
│   ├── figma_mcp.py            McpToolset do Figma (remote OAuth · desktop · stdio · off)
│   └── doc_parser.py           PDF nativo + DOCX via MarkItDown
├── scripts/figma_oauth.py      fluxo OAuth 2.1 do MCP remoto do Figma
├── output/                     artefatos por execução (ignorado no git)
└── agentes-para-converter/     material de origem (skills de produto, agentes de design, gate de dev)
```

### Mapa de conversão (origem → agente do pipeline)

| Origem (`agentes-para-converter/`) | Agente(s) |
|---|---|
| `produto/gate-estrutural-unooria` | P1 Gate estrutural (+ P1b Revisor, P1c Check) |
| `produto/avaliacao-pedagogica-unooria` | P2 |
| `produto/experiencia-aluno-unooria` | P3 |
| `produto/gate-final-unooria` | P4 (+ P4c Check) |
| `design/agents/1-qa-conformidade` | dividido: veredito → P1–P4; **emissão da spec → P5** |
| `design/agents/2-brief-oficio` | D1 |
| `design/agents/3-jornada-figjam` (+ gate de ofício 3') | D2 (o gate de ofício O1–O5 roda dentro do D7) |
| `design/agents/3b-fluxo-figjam` | D3 |
| `design/agents/4-copy-ptbr` (passadas 1 e 2) | D4 e D6 |
| `design/agents/5-wireframes-figma` | D5 |
| `design/agents/6-qa-entregaveis` | D7 (+ D7c Check) |
| `design/agents/7-handoff-dev` | V1 |
| `design/agents/7b-brief-assets` | V1b |
| `dev/validar-missao` (5 agentes paralelos) | V2a–V2e + V3 consolidação |
| `design/agents/T-aprendizado` | T |
| — (novo) | P0 One-pager, V4 PRD padrão ouro |

As `references/` das três origens foram copiadas para `prompts/references/` e são **incluídas** nos prompts em tempo de carga; editar uma referência muda todos os agentes que a usam.

---

## Contexto da plataforma no PRD

Três referências geradas pela leitura dos repositórios da Unooria e injetadas no redator do PRD e na banca de dev:

- `prompts/references/plataforma-unooria-software.md` — monorepo (pnpm/Turbo, Next 16, NestJS, Prisma/Postgres 16, Zod→OpenAPI, tenancy/RLS, SDK `postMessage`, canais operacional × analítico, xAPI, modelo de missão em três camadas, testes, DoD, ADRs, **passo a passo para criar uma missão**).
- `prompts/references/plataforma-unooria-infra.md` — GCP (Cloud Run, LB + Cloud Armor, Cloud SQL, buckets `-exp`/`-assets`, Pub/Sub, WSO2, Secret Manager, CI/CD, limites, LGPD).
- `prompts/references/plataforma-unooria-design-system.md` — `@unooria/design-system` (seis marcas, tokens, componentes, fileKeys do Figma, kit por tipo de tela, riscos).

Reconferir essas referências a cada mudança de ADR — critério que aponta para regra morta é a armadilha que o `AGENTS.md` da plataforma descreve.

---

## Figma MCP

| Modo (`FIGMA_MCP_MODE`) | O que dá | Como |
|---|---|---|
| `remote` | **Escrita** (`use_figma`, `create_new_file`, `generate_diagram`), FigJam, leitura, skills (`get_figma_skill`) | `python scripts/figma_oauth.py` uma vez (OAuth 2.1 com PKCE via SDK `mcp`; grava `.figma_mcp_tokens.json`, renovado automaticamente). O servidor oficial **não aceita** Personal Access Token. |
| `desktop` | Leitura via app Figma Desktop (`http://127.0.0.1:3845/mcp`) | Ativar o servidor MCP no app; sem auth |
| `stdio` | Só leitura (`get_figma_data`, `download_figma_images`) via `figma-developer-mcp` | `FIGMA_API_KEY` (PAT) + Node/npx |
| `off` (padrão) | Nenhuma ferramenta | Design entrega jornada, fluxo (Mermaid) e wireframes como especificação em Markdown |

Os agentes de design são instruídos a chamar `get_figma_skill` (`figma-use`, `figma-use-figjam`, `figma-generate-diagram`, `figma-generate-design`, `figma-create-new-file`) antes de qualquer escrita, a devolver **URL, fileKey e node IDs**, e a degradar para Markdown quando as ferramentas faltam. O D7 audita o **arquivo**, não o relatório (`get_screenshot`, `get_metadata`, `get_variable_defs`, `get_figjam`).

---

## Como executar

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # preencha GOOGLE_API_KEY; ajuste FIGMA_MCP_MODE
python test_pipeline.py       # testes estruturais, sem chamadas a LLM
streamlit run app.py          # http://localhost:8501
```

Na interface: escolha as etapas ativas (Produto / Design / Dev), o modo estrito, o nível de raciocínio; anexe o one-pager (PDF/DOCX) ou descreva a missão; acompanhe cada agente e os gates em tempo real; baixe o PRD, a spec e o estado. A aba **Prompts e referências** edita qualquer `.md` e mostra o prompt final com os includes resolvidos.

Execução por linha de comando:

```python
from pipeline import run_orchestrator_pipeline_sync
r = run_orchestrator_pipeline_sync("Missão 4º EF no YouTube sobre popularidade × confiabilidade…", stages=["produto"])
print(r.gates, r.output_dir)
```

---

## Notas de arquitetura

- **ADK 2.8**: `SequentialAgent`/`ParallelAgent`/`LoopAgent` estão marcados como *deprecated* em favor de `Workflow` (grafo com rotas). Continuam funcionais e são a base desta estrutura; o roteamento condicional é feito por estado + callbacks (padrão validado nos testes). Migrar para `Workflow` é o próximo passo natural quando ele aceitar aninhamento em sub-agentes.
- Todos os agentes, exceto o P0, rodam com `include_contents='none'`: trabalham só com a instrução interpolada do estado (`{chave}` / `{chave?}`), o que mantém o contexto enxuto e determinístico. O P0 é o único que recebe a mensagem original e os anexos.
- `{chave}` sem `?` lança erro se a chave não existir no estado; o `test_pipeline.py` verifica que só `one_pager` e `gate_estrutural_report` são obrigatórias e que nenhuma referência contém `{identificador}` que o ADK tentaria interpolar.
- Segurança: um Personal Access Token do Figma esteve versionado em `.env.example` e neste README em versões anteriores do repositório. Ele foi removido dos arquivos, mas **continua no histórico do git — revogue-o e gere outro**.
