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
from pathlib import Path
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
    "spec_missao", "spec_missao_gate0", "bncc_status", "bncc_report", "fechamento_lacunas", "relatorio_lacunas", "lacunas_status",
    "ambiente_simulado", "ambiente_status",
    "brief_oficio", "jornada_telas", "fluxo_arestas", "copy_strings", "camada_caa",
    "wireframes_cobertura", "copy_strings_revisada", "qa_entregaveis_report", "design_status",
    "handoff_dev", "brief_assets", "manifesto_status", "manifesto_report", "telemetria_status", "telemetria_report",
    "rastro_lacunas_status", "rastro_lacunas_report", "prd_status", "prd_check_report",
    "validacao_produto_narrativa", "validacao_design_imersao",
    "validacao_pedagogia_bncc", "validacao_dados_lgpd", "validacao_tecnica_arquitetura",
    "validacao_dev_report", "dev_status", "prd_final", "aprendizado_registro",
    "pipeline_bloqueado", "pipeline_bloqueio_motivo",
}
# Variáveis estáticas substituídas pelo loader antes do ADK
CONFIG_VARS = {"figma_mcp_mode": "off", "figma_folder_url": "x", "figma_ds_file_key": "k", "figma_ds_v02_file_key": "k2", "gdrive_folder_url": "g"}

# Chaves obrigatórias (sem `?`) permitidas por área: existem sempre antes do agente rodar
REQUIRED_ALLOWED = {"one_pager", "gate_estrutural_report", "nucleo_narrativo"}

EXPECTED_AGENTS = {
    "NucleoNarrativoLoop", "NucleoNarrativoAgent", "MicroGateAgent", "MicroGateCheck", "SecoesApoioAgent",
    "GateEstruturalLoop", "GateEstruturalAgent", "GateEstruturalCheck", "RevisorOnePagerAgent",
    "AvaliacoesParalelas", "AvaliacaoPedagogicaAgent", "ExperienciaAlunoAgent", "GateFinalProdutoAgent",
    "GateFinalProdutoCheck", "SpecMissaoAgent", "BnccCheck", "DesignStage", "FechaLacunasAgent", "FechaLacunasSplit",
    "AmbienteSimuladoAgent", "AmbienteSimuladoSplit", "BriefOficioAgent", "JornadaFigJamAgent",
    "FluxoFigJamAgent", "CopyPtBrAgent", "CaaAgent", "WireframesFigmaAgent", "CopyRevisaoAgent", "QaEntregaveisAgent",
    "QaEntregaveisCheck", "DevStage", "ManifestoCheck", "HandoffParalelo", "HandoffDevAgent", "BriefAssetsAgent",
    "TelemetriaCheck", "LacunaCheck", "PrdCheck",
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


# --------------------------------------------------------------------------- 5. split D0/D9
def test_secao_split_d0_e_d9():
    from agents.design import get_ambiente_simulado_split, get_fecha_lacunas_split

    spec_original = "# Spec — Teste v1\n\n**1EF · instanooria**\n\n## 0. Identificação de plataforma\n" + ("Slug exp-99-teste. " * 90) + "\n\n## 12. Decisões fechadas neste gate\nnenhuma\n"
    spec_consolidada = spec_original + "\n## 13. Decisões D0\n[D0-1] 2.estado_espera — Decisão: tela congela.\n"
    d0_out = (
        "# Fechamento de lacunas — teste\n**Veredito: 🟢 SEGUE PARA D1**\n\n## Passo 1 — Varredura\n...\n"
        "## Passo 5 — Spec consolidada (texto original do Gate 0, blocos 0–12 intocados, + bloco 13)\n" + spec_consolidada +
        "\n## Passo 5b — Relatório de preenchimento — `relatorio-preenchimento.md` · Google Docs: GDOCS indisponível\n"
        "### [D0-1] Tela de espera\n**O que faltava:** o que a criança vê enquanto a professora fala.\n**O que entrou:** a tela congela.\n\n"
        "## Passo 6 — Devolutiva ao produto\n- nada\n\n## Testes 1–6 — resultado\nok\n\n"
        '```json\n{"agente": "fecha-lacunas", "missao": "exp-99-teste", "status": "segue_com_pendencias", "decisoes": [], "respec": []}\n```'
    )
    root = SequentialAgent(
        name="Root",
        sub_agents=[
            FakeAgent(name="Spec", key="spec_missao", text=spec_original),
            FakeAgent(name="D0", key="fechamento_lacunas", text=d0_out),
            get_fecha_lacunas_split(),
        ],
    )
    _, state = asyncio.run(_run(root))
    assert state["spec_missao"].startswith("# Spec — Teste v1"), state["spec_missao"][:80]
    assert "## 13. Decisões D0" in state["spec_missao"] and "Passo 5b" not in state["spec_missao"]
    assert state["spec_missao_gate0"] == spec_original
    assert state["relatorio_lacunas"].startswith("### [D0-1]") and "Passo 6" not in state["relatorio_lacunas"]
    assert state["lacunas_status"] == "aprovado"
    assert not state.get(KEY_PIPELINE_BLOQUEADO)

    # D9 dormente: reemite a spec (blocos 1–13 + bloco 14); o split troca spec_missao e não bloqueia
    spec_com_14 = spec_consolidada + "\n## 14. Ambiente simulado (D9)\ninstanooria · dormente\n"
    d9_out = (
        "# Ambiente simulado — teste\n**Veredito: ⚪ DORMENTE (spec já nomeia instanooria)**\n\n"
        "## Passo 4 — Spec consolidada (blocos 1–13 do D0 intocados + bloco 14)\n" + spec_com_14 +
        "\n## Bloco 14 — Ficha do ambiente\nnome: instanooria\n\n## Testes — resultado\nok\n\n"
        '```json\n{"agente": "ambiente-simulado", "missao": "exp-99-teste", "status": "dormente"}\n```'
    )
    root2 = SequentialAgent(
        name="Root2",
        sub_agents=[
            FakeAgent(name="Spec", key="spec_missao", text=spec_consolidada),
            FakeAgent(name="D9", key="ambiente_simulado", text=d9_out),
            get_ambiente_simulado_split(),
        ],
    )
    _, state2 = asyncio.run(_run(root2))
    assert "## 14. Ambiente simulado" in state2["spec_missao"] and "## 13. Decisões D0" in state2["spec_missao"]
    assert "Bloco 14 — Ficha" not in state2["spec_missao"]
    assert state2["ambiente_status"] == "aprovado"

    # D9 sem a seção de spec (saída fora do formato) e com aguarda_gate: mantém a spec, marca 🔴, pipeline segue
    d9_ruim = '# Ambiente simulado\n**Veredito: 🔴 AGUARDA GATE 0**\n\n```json\n{"agente": "ambiente-simulado", "status": "aguarda_gate"}\n```'
    root3 = SequentialAgent(
        name="Root3",
        sub_agents=[
            FakeAgent(name="Spec", key="spec_missao", text=spec_consolidada),
            FakeAgent(name="D9", key="ambiente_simulado", text=d9_ruim),
            get_ambiente_simulado_split(),
            FakeAgent(name="Jusante", key="brief_oficio", text="brief", before_agent_callback=skip_if_blocked),
        ],
    )
    _, state3 = asyncio.run(_run(root3))
    assert state3["spec_missao"] == spec_consolidada
    assert state3["ambiente_status"] == "bloqueado"
    assert state3.get("brief_oficio") == "brief" and not state3.get(KEY_PIPELINE_BLOQUEADO)
    print("   ✓ split D0/D9: spec consolidada, cópia da original, relatório separado, status informativo")


# --------------------------------------------------------------------------- 6. BNCC Computação
_SPEC_BNCC = """# Spec — Teste v1

**5EF · unitube · Rubrica v1.17**

## 0. Identificação de plataforma
Slug `exp-77-teste` · séries `["5EF"]` · unidade B2 · `publico: estudante` · unitube · viewport 375×812.

## 1. Descoberta central
Popularidade não é confiabilidade.

## 11. Currículo
- {codigos}

## 12. Decisões fechadas neste gate
nenhuma
"""


def test_bncc_validador_e_gate():
    from agents.checkers import BnccCheckAgent
    from tools.bncc import extrair_serie, habilidades, validar_spec

    assert len(habilidades()) == 130
    assert extrair_serie('séries `["5EF"]`')["anos"] == {5}
    assert extrair_serie("1º–2º ano · tiktooria")["anos"] == {1, 2}
    assert extrair_serie("2ª série do Ensino Médio")["em"] is True

    ok = validar_spec(_SPEC_BNCC.format(codigos="EF05CO08 — momento em tela: escolher vídeo · EF05CO02 — grafo do canal"))
    assert ok["status"] == "aprovado" and ok["anos"] == [5] and ok["tem_letramento"], ok["achados"]

    ruim = validar_spec(_SPEC_BNCC.format(codigos="EF04CO08 · EF05CO02 · EF05CO99"))
    cods = {a["codigo"] for a in ruim["achados"] if a["severidade"] == "bloqueio"}
    assert ruim["status"] == "bloqueado" and {"EF04CO08", "EF05CO99", "letramento"} <= cods, cods

    so_pc = validar_spec(_SPEC_BNCC.format(codigos="EF05CO02 · EF15CO02"))
    assert so_pc["status"] == "bloqueado" and any(a["codigo"] == "letramento" for a in so_pc["achados"])

    em_ok = validar_spec(_SPEC_BNCC.replace('`["5EF"]`', '`["2EM"]`').replace("5EF", "2EM").format(codigos="EM13CO14 · EM13CO01"))
    assert em_ok["status"] == "aprovado" and em_ok["em"] is True, em_ok["achados"]
    em_sem_letramento = validar_spec(_SPEC_BNCC.replace('`["5EF"]`', '`["2EM"]`').replace("5EF", "2EM").format(codigos="EM13CO01"))
    assert em_sem_letramento["status"] == "aprovado", "no EM (sem eixo oficial) basta uma habilidade EM13 existente"
    assert any(a["codigo"] == "letramento" and a["severidade"] == "atencao" for a in em_sem_letramento["achados"])
    em_ano_errado = validar_spec(_SPEC_BNCC.replace('`["5EF"]`', '`["2EM"]`').replace("5EF", "2EM").format(codigos="EF09CO10"))
    assert em_ano_errado["status"] == "bloqueado", "habilidade do Fundamental em missão de EM bloqueia"
    em_vazio = validar_spec(_SPEC_BNCC.replace('`["5EF"]`', '`["2EM"]`').replace("5EF", "2EM").format(codigos="(nenhuma)"))
    assert em_vazio["status"] == "bloqueado", "missão de EM sem nenhuma habilidade EM13 bloqueia"

    sem_serie = validar_spec("# Spec\n## 0. Identificação\nslug x\n## 11. Currículo\nEF05CO08\n## 12.\n")
    assert sem_serie["status"] == "bloqueado" and any(a["codigo"] == "serie" for a in sem_serie["achados"])

    # gate estrito: spec não conforme bloqueia o pipeline e pula o jusante
    root = SequentialAgent(
        name="Root",
        sub_agents=[
            FakeAgent(name="Spec", key="spec_missao", text=_SPEC_BNCC.format(codigos="EF04CO08 · EF05CO02")),
            BnccCheckAgent(name="BnccCheck", estrito=True),
            FakeAgent(name="Jusante", key="brief_oficio", text="brief", before_agent_callback=skip_if_blocked),
        ],
    )
    _, state = asyncio.run(_run(root))
    assert state["bncc_status"] == "bloqueado" and state.get(KEY_PIPELINE_BLOQUEADO) is True
    assert "brief_oficio" not in state and "🔴 BLOQUEADO" in state["bncc_report"]
    assert state["bncc_status_envelope"]["agente"] == "bncc-check"

    # spec conforme: segue
    root2 = SequentialAgent(
        name="Root2",
        sub_agents=[
            FakeAgent(name="Spec", key="spec_missao", text=_SPEC_BNCC.format(codigos="EF05CO08 · EF05CO02")),
            BnccCheckAgent(name="BnccCheck", estrito=True),
            FakeAgent(name="Jusante", key="brief_oficio", text="brief", before_agent_callback=skip_if_blocked),
        ],
    )
    _, state2 = asyncio.run(_run(root2))
    assert state2["bncc_status"] == "aprovado" and state2.get("brief_oficio") == "brief" and not state2.get(KEY_PIPELINE_BLOQUEADO)
    print("   ✓ BNCC: 130 habilidades; EF bloqueia código inexistente, ano errado, sem letramento e sem série; EM exige ≥1 EM13; gate trava a esteira")


# --------------------------------------------------------------------------- 7. rastro (manifesto · telemetria · lacunas)
_SPEC_MANIFESTO_OK = """# Spec — Teste v1

## 0. Identificação de plataforma
Nome: Teste. Ficha do manifesto:
- `id: exp-77-teste`
- `produto: entre-redes`
- `series: ["5EF"]`
- `unidade: 2`
- `publico: estudante`
- `viewport: 375x812`
- `permissoes: [forms]`
- `capabilities: [telemetria, progresso]`
- `secao_ds: unitube`
- `liberacao: por-turma`

## 1. Descoberta central
x
"""

_HANDOFF_OK = """# Handoff — teste
## 3. Spec de interação e eventos
| EVT | verbo | objeto | quando dispara | resultado | contexto | caminho | onde é lido |
|---|---|---|---|---|---|---|---|
| EVT-001 | interacted | video:escolha | ao tocar | {"escolhido": true} | {"etapa": 3} | analítico | exp_77_sessoes · GET /teste/turmas/:turmaId/painel |
## 5. Telemetria e entidades
Tabelas: `exp_77_sessoes`, `exp_77_gates_turma` (polling curto).
"""


def test_rastro_manifesto_telemetria_lacunas():
    from agents.checkers import RastroCheckAgent
    from tools.rastro import classificar_dono, validar_manifesto, validar_telemetria, varrer_lacunas

    ok = validar_manifesto(_SPEC_MANIFESTO_OK)
    assert ok["status"] == "aprovado", ok["achados"]
    ruim = validar_manifesto(_SPEC_MANIFESTO_OK.replace("- `produto: entre-redes`\n", "").replace("`unidade: 2`", "`unidade: 7`").replace("`permissoes: [forms]`", "`permissoes: [camera]`"))
    campos = {a["campo"] for a in ruim["achados"] if a["severidade"] == "bloqueio"}
    assert ruim["status"] == "bloqueado" and {"produto", "unidade", "permissoes"} <= campos, campos
    tiktok = validar_manifesto(_SPEC_MANIFESTO_OK.replace("secao_ds: unitube", "secao_ds: tiktooria"))
    assert tiktok["status"] == "amarelo" and tiktok["achados"][0]["etapa"] == "plataforma"

    t_ok = validar_telemetria(_HANDOFF_OK)
    assert t_ok["status"] == "aprovado", t_ok["achados"]
    t_ruim = validar_telemetria(_HANDOFF_OK.replace("| resultado | contexto |", "| dados | canal |").replace("polling curto", "WebSocket hub:pause") + "\n@Roles(\"admin-contrato\")")
    cods = {a["codigo"] for a in t_ruim["achados"] if a["severidade"] == "bloqueio"}
    assert t_ruim["status"] == "bloqueado" and {"resultado-contexto", "campo-dados", "websocket", "papeis"} <= cods, cods
    assert validar_telemetria("sem tabela nenhuma")["status"] == "bloqueado"

    assert classificar_dono("jornada", "dev") == "design"
    assert classificar_dono("gate-estrutural", "dev") == "produto"
    assert classificar_dono("plataforma", "dev") == "plataforma"
    assert classificar_dono("dono: input", "dev") == "input"
    assert classificar_dono("qualquer coisa", "design") == "design"
    st = {
        "spec_missao": "spec [ABERTO — gate-estrutural] e RS-2 pendente",
        "handoff_dev": "handoff [LACUNA — dono: wireframes] e [verificar no repositório: nome da tabela] e [LACUNA — dono: plataforma]",
        "prd_final": "prd [NEEDS CLARIFICATION: qual ADR?, dono: plataforma]",
    }
    fontes = [
        {"chave": "spec_missao", "rotulo": "spec", "etapa_padrao": "produto"},
        {"chave": "handoff_dev", "rotulo": "handoff", "etapa_padrao": "dev"},
    ]
    r = varrer_lacunas(fontes, st)
    assert r["status"] == "bloqueado" and r["por_etapa"] == {"input": 0, "produto": 2, "design": 1, "dev": 1, "plataforma": 1}, r["por_etapa"]
    so_plat = varrer_lacunas([{"chave": "prd_final", "rotulo": "PRD", "etapa_padrao": "dev"}], st)
    assert so_plat["status"] == "amarelo" and so_plat["por_etapa"]["plataforma"] == 1
    assert varrer_lacunas(fontes, {"spec_missao": "limpo", "handoff_dev": "limpo"})["status"] == "aprovado"

    # gate: lacuna de design bloqueia e pula o jusante; só plataforma segue com 🟡
    root = SequentialAgent(
        name="Root",
        sub_agents=[
            FakeAgent(name="Spec", key="spec_missao", text="# Spec\nSlug: exp-77-teste\n"),
            FakeAgent(name="Handoff", key="handoff_dev", text=st["handoff_dev"]),
            RastroCheckAgent(name="LacunaCheck", modo="lacunas", rotulo="Rastro", report_key="rastro_lacunas_report", status_key="rastro_lacunas_status", fontes=fontes, estrito=True),
            FakeAgent(name="Jusante", key="prd_final", text="prd", before_agent_callback=skip_if_blocked),
        ],
    )
    _, state = asyncio.run(_run(root))
    assert state["rastro_lacunas_status"] == "bloqueado" and state.get(KEY_PIPELINE_BLOQUEADO) is True and "prd_final" not in state
    assert "**design `1`**" in state["rastro_lacunas_report"]
    root2 = SequentialAgent(
        name="Root2",
        sub_agents=[
            FakeAgent(name="Handoff", key="handoff_dev", text="[LACUNA — dono: plataforma] ponte tiktooria"),
            RastroCheckAgent(name="LacunaCheck", modo="lacunas", rotulo="Rastro", report_key="rastro_lacunas_report", status_key="rastro_lacunas_status", fontes=fontes, estrito=True),
            FakeAgent(name="Jusante", key="prd_final", text="prd", before_agent_callback=skip_if_blocked),
        ],
    )
    _, state2 = asyncio.run(_run(root2))
    assert state2["rastro_lacunas_status"] == "amarelo" and state2.get("prd_final") == "prd" and not state2.get(KEY_PIPELINE_BLOQUEADO)
    root3 = SequentialAgent(
        name="Root3",
        sub_agents=[
            FakeAgent(name="Spec", key="spec_missao", text=_SPEC_MANIFESTO_OK.replace("- `liberacao: por-turma`\n", "")),
            RastroCheckAgent(name="ManifestoCheck", modo="manifesto", rotulo="Manifesto", report_key="manifesto_report", status_key="manifesto_status", estrito=True),
            FakeAgent(name="Jusante", key="handoff_dev", text="h", before_agent_callback=skip_if_blocked),
        ],
    )
    _, state3 = asyncio.run(_run(root3))
    assert state3["manifesto_status"] == "bloqueado" and "handoff_dev" not in state3
    print("   ✓ rastro: manifesto, telemetria e lacunas por dono; bloqueio impede o jusante; só plataforma segue 🟡")


# --------------------------------------------------------------------------- 8. cópias da plataforma
def test_referencias_plataforma_sincronizadas():
    import json
    import subprocess
    from prompts import REFERENCES_DIR

    pasta = REFERENCES_DIR / "plataforma"
    manifesto = json.loads((pasta / "versao-lida.json").read_text(encoding="utf-8"))
    faltando = [a["destino"] for a in manifesto["arquivos"] if not (pasta / a["destino"]).exists()]
    assert not faltando, f"cópias ausentes: {faltando} — rode scripts/sincronizar_plataforma.py"
    assert len(manifesto["arquivos"]) >= 40
    plataforma = Path(manifesto["plataforma_dir"])
    if (plataforma / ".git").exists():
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=plataforma, capture_output=True, text=True).stdout.strip()
        if head and head != manifesto["commit"]:
            print(f"   ⚠️ plataforma-unooria está em {head}, cópias lidas de {manifesto['commit']} — considere rodar scripts/sincronizar_plataforma.py")
    print(f"   ✓ {len(manifesto['arquivos'])} cópias da plataforma presentes (commit {manifesto['commit']}, {manifesto['data_commit']})")


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
        test_secao_split_d0_e_d9,
        test_bncc_validador_e_gate,
        test_rastro_manifesto_telemetria_lacunas,
        test_referencias_plataforma_sincronizadas,
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
