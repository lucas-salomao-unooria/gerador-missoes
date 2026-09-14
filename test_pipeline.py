"""Testes estruturais do pipeline Produto → Design → Dev (sem chamadas a LLM).

Execução: `python test_pipeline.py` (ou `pytest test_pipeline.py`).

Cobre:
  1. carga de todos os prompts, resolução de includes e segurança da interpolação do ADK;
  2. montagem da árvore de agentes (Sequential / Parallel / Loop) e unicidade de output_keys;
  3. parsing do envelope JSON e inferência de status;
  4. controle de fluxo determinístico (EnvelopeGateAgent + skip_if_blocked) com agentes falsos.
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import AsyncGenerator

os.environ.setdefault("FIGMA_MCP_MODE", "off")
os.environ.setdefault("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY", "teste"))

from google.adk.agents.base_agent import BaseAgent  # noqa: E402
from google.adk.agents.invocation_context import InvocationContext  # noqa: E402
from google.adk.agents.llm_agent import LlmAgent  # noqa: E402
from google.adk.agents.loop_agent import LoopAgent  # noqa: E402
from google.adk.agents.sequential_agent import SequentialAgent  # noqa: E402
from google.adk.events import Event, EventActions  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.adk.utils import instructions_utils  # noqa: E402
from google.genai import types  # noqa: E402
from typing_extensions import override  # noqa: E402

from agents.callbacks import (  # noqa: E402
    KEY_PIPELINE_BLOQUEADO,
    extrair_envelope,
    extrair_slug,
    inferir_status,
    skip_if_blocked,
)
from agents.checkers import EnvelopeGateAgent  # noqa: E402
from agents.produto import MICRO_GATE_MAX_RODADAS  # noqa: E402
from config import get_settings  # noqa: E402
from pipeline.orchestrator import (  # noqa: E402
    create_mission_orchestrator,
    get_pipeline_agents_metadata,
    iter_agent_tree,
)
from prompts import list_prompt_files, list_state_variables, load_prompt  # noqa: E402

# Chaves que existem no session.state em algum ponto do pipeline
KNOWN_STATE_KEYS = {
    "briefing", "nucleo_narrativo", "micro_gate_report", "micro_gate_status", "micro_gate_rodada",
    "one_pager", "gate_estrutural_report", "gate_estrutural_status", "gate_estrutural_rodada",
    "avaliacao_pedagogica_report", "experiencia_aluno_report", "gate_final_report", "gate_final_status",
    "spec_missao", "brief_oficio", "jornada_telas", "fluxo_arestas", "copy_strings", "camada_caa",
    "wireframes_cobertura", "copy_strings_revisada", "qa_entregaveis_report", "design_status",
    "handoff_dev", "brief_assets", "validacao_produto_narrativa", "validacao_design_imersao",
    "validacao_pedagogia_bncc", "validacao_dados_lgpd", "validacao_tecnica_arquitetura",
    "validacao_dev_report", "dev_status", "prd_final", "aprendizado_registro",
    "pipeline_bloqueado", "pipeline_bloqueio_motivo",
}
# Variáveis estáticas substituídas pelo loader antes do ADK
CONFIG_VARS = {"figma_mcp_mode": "off", "figma_folder_url": "x", "figma_ds_file_key": "k", "figma_ds_v02_file_key": "k2"}

# Chaves obrigatórias (sem `?`) permitidas por área: existem sempre antes do agente rodar
REQUIRED_ALLOWED = {"one_pager", "gate_estrutural_report", "nucleo_narrativo"}

EXPECTED_AGENTS = {
    "NucleoNarrativoLoop", "NucleoNarrativoAgent", "MicroGateAgent", "MicroGateCheck", "SecoesApoioAgent",
    "GateEstruturalLoop", "GateEstruturalAgent", "GateEstruturalCheck", "RevisorOnePagerAgent",
    "AvaliacoesParalelas", "AvaliacaoPedagogicaAgent", "ExperienciaAlunoAgent", "GateFinalProdutoAgent",
    "GateFinalProdutoCheck", "SpecMissaoAgent", "DesignStage", "BriefOficioAgent", "JornadaFigJamAgent",
    "FluxoFigJamAgent", "CopyPtBrAgent", "CaaAgent", "WireframesFigmaAgent", "CopyRevisaoAgent", "QaEntregaveisAgent",
    "QaEntregaveisCheck", "DevStage", "HandoffParalelo", "HandoffDevAgent", "BriefAssetsAgent",
    "BancaValidacaoDev", "ValidacaoProdutoNarrativaAgent", "ValidacaoDesignImersaoAgent",
    "ValidacaoPedagogiaBnccAgent", "ValidacaoDadosLgpdAgent", "ValidacaoTecnicaArquiteturaAgent",
    "ConsolidacaoBancaAgent", "ValidacaoDevCheck", "PrdWriterAgent", "AprendizadoAgent", "ProdutoStage",
}


# --------------------------------------------------------------------------- 1. prompts
def test_prompts_carregam_e_interpolacao_segura():
    areas = list_prompt_files()
    assert set(areas) >= {"produto", "design", "dev", "transversal"}, areas
    total = 0
    for area, files in areas.items():
        for fname in files:
            if fname.startswith("_"):
                continue
            content = load_prompt(f"{area}/{fname}", **CONFIG_VARS)
            total += 1
            assert "<!-- include:" not in content, f"include não resolvido em {area}/{fname}"
            # variáveis de estado declaradas
            for var in list_state_variables(content):
                assert var in KNOWN_STATE_KEYS, f"{area}/{fname}: variável desconhecida {{{var}}}"
            # simulação do regex do ADK: qualquer {nome} válido tem de ser chave conhecida
            for match in instructions_utils._TEMPLATE_VAR_PATTERN.finditer(content):
                raw = match.group().lstrip("{").rstrip("}").strip()
                optional = raw.endswith("?")
                name = raw.removesuffix("?")
                if instructions_utils._is_valid_state_name(name):
                    assert name in KNOWN_STATE_KEYS, f"{area}/{fname}: `{match.group()}` seria interpolado pelo ADK e não é chave de estado"
                    if not optional:
                        assert name in REQUIRED_ALLOWED, f"{area}/{fname}: `{{{name}}}` deveria ser opcional (`{{{name}?}}`)"
    assert total >= 24, f"esperado ≥ 24 prompts, encontrado {total}"
    print(f"   ✓ {total} prompts carregados; includes resolvidos; interpolação do ADK segura")


# --------------------------------------------------------------------------- 2. árvore
def test_arvore_de_agentes():
    settings = get_settings()
    assert settings.figma_mcp_mode == "off"
    orchestrator = create_mission_orchestrator(stages=["produto", "design", "dev"])
    assert isinstance(orchestrator, SequentialAgent)

    names = {}
    llm_agents = []
    for depth, agent in iter_agent_tree(orchestrator):
        assert agent.name not in names, f"nome duplicado: {agent.name}"
        names[agent.name] = depth
        if isinstance(agent, LlmAgent):
            llm_agents.append(agent)

    missing = EXPECTED_AGENTS - set(names)
    assert not missing, f"agentes ausentes: {missing}"

    # output_keys: únicos exceto one_pager (P0 e revisor escrevem a mesma chave de propósito)
    keys = [a.output_key for a in llm_agents if a.output_key]
    dupes = {k for k in keys if keys.count(k) > 1} - {"one_pager"}
    assert not dupes, f"output_keys duplicados: {dupes}"
    assert set(keys) <= KNOWN_STATE_KEYS

    # loop e paralelos
    micro = next(a for _, a in iter_agent_tree(orchestrator) if a.name == "NucleoNarrativoLoop")
    assert isinstance(micro, LoopAgent) and micro.max_iterations == MICRO_GATE_MAX_RODADAS
    assert [a.name for a in micro.sub_agents] == ["NucleoNarrativoAgent", "MicroGateAgent", "MicroGateCheck"]

    loop = next(a for _, a in iter_agent_tree(orchestrator) if a.name == "GateEstruturalLoop")
    assert isinstance(loop, LoopAgent) and loop.max_iterations == settings.gate_estrutural_max_rodadas
    assert [a.name for a in loop.sub_agents] == ["GateEstruturalAgent", "GateEstruturalCheck", "RevisorOnePagerAgent"]
    banca = next(a for _, a in iter_agent_tree(orchestrator) if a.name == "BancaValidacaoDev")
    assert len(banca.sub_agents) == 5

    # metadados coerentes com a árvore
    meta_ids = {m["id"] for m in get_pipeline_agents_metadata()}
    assert meta_ids <= set(names), meta_ids - set(names)

    # propagação do thinking budget
    custom = create_mission_orchestrator(thinking_budget=4096, stages=["produto"])
    for _, agent in iter_agent_tree(custom):
        if isinstance(agent, LlmAgent):
            assert agent.generate_content_config.thinking_config.thinking_budget == 4096

    # etapas desligáveis
    so_produto = create_mission_orchestrator(stages=["produto"])
    assert [a.name for a in so_produto.sub_agents] == ["ProdutoStage", "AprendizadoAgent"]
    print(f"   ✓ árvore com {len(names)} agentes ({len(llm_agents)} LLM); loop, paralelos e metadados coerentes")


# --------------------------------------------------------------------------- 3. envelope
def test_envelope_e_status():
    texto = (
        "# Gate\n**Veredito: 🔴 BLOQUEADO**\n...\n```json\n"
        '{"agente": "gate-estrutural", "missao": "exp-12-teste", "rodada": 1, "status": "bloqueado", "achados": []}\n```'
    )
    env = extrair_envelope(texto)
    assert env and env["status"] == "bloqueado"
    assert inferir_status(texto, env) == "bloqueado"
    assert inferir_status("**Veredito: 🟢 LIBERADA PARA DESIGN/DEV**") == "aprovado"
    assert inferir_status("Veredito global: 🟡 APTO COM RESSALVAS", {"status": "aprovado", "veredito": "amarelo"}) == "aprovado"
    assert inferir_status("texto sem veredito") == "indefinido"
    assert extrair_slug("Slug: exp-12-magia-ou-truque · nome") == "exp-12-magia-ou-truque"
    print("   ✓ envelope JSON e inferência de status")


# --------------------------------------------------------------------------- 4. fluxo determinístico
class FakeAgent(BaseAgent):
    """Agente falso: grava um texto no estado (como faria output_key) e emite um evento."""

    key: str
    text: str
    marker_key: str = ""

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        delta = {self.key: self.text}
        if self.marker_key:
            delta[self.marker_key] = int(ctx.session.state.get(self.marker_key, 0)) + 1
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=self.text[:40])]),
            actions=EventActions(state_delta=delta),
        )


async def _run(root: BaseAgent):
    runner = InMemoryRunner(agent=root, app_name="teste")
    session = await runner.session_service.create_session(app_name="teste", user_id="u", session_id="s")
    events = []
    async for ev in runner.run_async(
        user_id="u", session_id=session.id, new_message=types.Content(role="user", parts=[types.Part(text="go")])
    ):
        events.append(ev)
    final = await runner.session_service.get_session(app_name="teste", user_id="u", session_id="s")
    return events, dict(final.state)


def test_gate_loop_bloqueia_e_pula_jusante():
    bloqueado = 'x\n```json\n{"agente": "g", "status": "bloqueado"}\n```'
    loop = LoopAgent(
        name="Loop",
        max_iterations=2,
        sub_agents=[
            FakeAgent(name="Gate", key="gate_estrutural_report", text=bloqueado),
            EnvelopeGateAgent(
                name="Check", rotulo="Gate", report_key="gate_estrutural_report", status_key="gate_estrutural_status",
                round_key="gate_estrutural_rodada", max_rounds=2, escalate_on_approve=True, block_pipeline_on_fail=True,
            ),
            FakeAgent(name="Revisor", key="one_pager", text="revisado", marker_key="revisoes"),
        ],
    )
    jusante = FakeAgent(name="Jusante", key="spec_missao", text="spec", before_agent_callback=skip_if_blocked)
    root = SequentialAgent(name="Root", sub_agents=[loop, jusante])
    events, state = asyncio.run(_run(root))

    assert state["gate_estrutural_status"] == "bloqueado"
    assert state["gate_estrutural_rodada"] == 2
    assert state.get("revisoes") == 1, "o revisor deve rodar só na rodada 1 (na última o check escala)"
    assert state.get(KEY_PIPELINE_BLOQUEADO) is True
    assert "spec_missao" not in state, "agente a jusante deveria ter sido pulado"
    textos = [p.text for e in events if e.author == "Jusante" for p in e.content.parts]
    assert textos and "não executado" in textos[0]
    print("   ✓ loop bloqueia após 2 rodadas, revisor roda 1x, jusante pulado")


def test_gate_loop_aprova_e_segue():
    aprovado = '**Veredito: 🟢 APROVADO**\n```json\n{"agente": "g", "status": "aprovado"}\n```'
    loop = LoopAgent(
        name="Loop",
        max_iterations=3,
        sub_agents=[
            FakeAgent(name="Gate", key="gate_estrutural_report", text=aprovado),
            EnvelopeGateAgent(
                name="Check", rotulo="Gate", report_key="gate_estrutural_report", status_key="gate_estrutural_status",
                round_key="gate_estrutural_rodada", max_rounds=3, escalate_on_approve=True, block_pipeline_on_fail=True,
            ),
            FakeAgent(name="Revisor", key="one_pager", text="revisado", marker_key="revisoes"),
        ],
    )
    jusante = FakeAgent(name="Jusante", key="spec_missao", text="spec", before_agent_callback=skip_if_blocked)
    root = SequentialAgent(name="Root", sub_agents=[loop, jusante])
    _, state = asyncio.run(_run(root))
    assert state["gate_estrutural_status"] == "aprovado"
    assert state["gate_estrutural_rodada"] == 1
    assert "revisoes" not in state, "revisor não deve rodar quando o gate aprova"
    assert state.get("spec_missao") == "spec"
    assert not state.get(KEY_PIPELINE_BLOQUEADO)
    print("   ✓ loop aprova na rodada 1 e o pipeline segue")


def test_modo_nao_estrito_nao_bloqueia():
    bloqueado = '```json\n{"agente": "g", "status": "bloqueado"}\n```'
    root = SequentialAgent(
        name="Root",
        sub_agents=[
            FakeAgent(name="Gate", key="gate_final_report", text=bloqueado),
            EnvelopeGateAgent(name="Check", rotulo="Gate final", report_key="gate_final_report", status_key="gate_final_status", block_pipeline_on_fail=False),
            FakeAgent(name="Jusante", key="spec_missao", text="spec", before_agent_callback=skip_if_blocked),
        ],
    )
    _, state = asyncio.run(_run(root))
    assert state["gate_final_status"] == "bloqueado" and state.get("spec_missao") == "spec"
    print("   ✓ modo não estrito registra o bloqueio e segue")


if __name__ == "__main__":
    print("=" * 64)
    print("🚀 Teste estrutural — Gerador de Missões Unooria (Produto → Design → Dev)")
    print("=" * 64)
    s = get_settings()
    print(f"   modelo: {s.gemini_model} · Figma MCP: {s.figma_mcp_mode} · etapas: {s.pipeline_stages} · estrito: {s.produto_modo_estrito}")
    tests = [
        test_prompts_carregam_e_interpolacao_segura,
        test_arvore_de_agentes,
        test_envelope_e_status,
        test_gate_loop_bloqueia_e_pula_jusante,
        test_gate_loop_aprova_e_segue,
        test_modo_nao_estrito_nao_bloqueia,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as exc:
            failed += 1
            print(f"   ✗ {t.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"   ✗ {t.__name__}: {type(exc).__name__}: {exc}")
    print("=" * 64)
    if failed:
        print(f"❌ {failed} teste(s) falharam")
        sys.exit(1)
    print("✅ TODOS OS TESTES ESTRUTURAIS PASSARAM")
