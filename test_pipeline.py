"""Testes estruturais do pipeline Produto → Design → Dev (sem chamadas a LLM).

Execução: `python test_pipeline.py` (ou `pytest test_pipeline.py`).

Cobre:
  1. carga de todos os prompts, resolução de includes e segurança da interpolação do ADK;
  2. montagem da árvore de agentes (Sequential / Parallel / Loop) e unicidade de output_keys;
  3. parsing do envelope JSON e inferência de status;
  4. controle de fluxo determinístico (EnvelopeGateAgent + marcar_heranca) com agentes falsos.
"""

from __future__ import annotations

import json
import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator

os.environ.setdefault("STITCH_MCP_MODE", "off")
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
    KEY_AGENTES_DEGRADADOS,
    KEY_DEGRADACOES,
    KEY_HERANCA,
    KEY_PIPELINE_BLOQUEADO,
    extrair_envelope,
    extrair_slug,
    inferir_status,
    marcar_heranca,
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
    "contrato_produto_report", "contrato_produto_status",
    "avaliacao_pedagogica_report", "experiencia_aluno_report", "adequacao_report", "gate_final_report", "gate_final_status",
    "spec_missao", "spec_missao_gate0", "bncc_status", "bncc_report", "fechamento_lacunas", "relatorio_lacunas", "lacunas_status",
    "ambiente_simulado", "ambiente_status",
    "brief_oficio", "jornada_telas", "fluxo_arestas", "copy_strings", "camada_caa",
    "wireframes_cobertura", "copy_strings_revisada", "qa_entregaveis_report", "design_status",
    "prototipo_html", "prototipo_arquivo", "prototipo_relatorio", "stitch_links", "diagramas_html",
    "miro_links", "miro_board",
    "handoff_dev", "brief_assets", "manifesto_status", "manifesto_report", "telemetria_status", "telemetria_report",
    "rastro_lacunas_status", "rastro_lacunas_report",
    "prototipo_lint_report", "evidencia_report", "evidencia_status", "kpis_report", "kpis_status", "perguntas_po",
    "perguntas_report", "perguntas_status", "juiz_perguntas_report", "juiz_perguntas_status",
    "juiz_perguntas_rodada", "execucao", "prototipo_lint_status", "brief_escopo", "brief_escopo_status", "prd_status", "prd_check_report",
    "validacao_produto_narrativa", "validacao_design_imersao",
    "validacao_pedagogia_bncc", "validacao_dados_lgpd", "validacao_tecnica_arquitetura",
    "validacao_dev_report", "dev_status", "prd_final", "one_pager_pedagogico", "one_pager_resumido", "aprendizado_registro",
    "pipeline_bloqueado", "pipeline_bloqueio_motivo",
    "diagnostico_execucao", "diagnostico_status", "qa_design_rodada", "tickets_retrabalho",
    "one_pager_gate0", "spec_rodada", "handoff_rodada", "banca_rodada", "reexecucoes",
    "adequacao_status", "avaliacoes_rodada",
    "missoes_vizinhas", "catalogo_missoes", "ficha_catalogo", "catalogo_status",
    "degradacoes", "heranca_degradada", "agentes_degradados",
    # modo correção (pipeline/reexecucao.py): pedido lido por todo agente, triagem e seu insumo
    "pedido_correcao", "triagem_correcao", "mapa_da_missao",
}
# Variáveis estáticas substituídas pelo loader antes do ADK
CONFIG_VARS = {"gdrive_folder_url": "g", "stitch_mcp_mode": "off", "stitch_project_url_base": "u", "gate_max_rodadas": 3, "qa_max_rodadas": 1}

# Chaves obrigatórias (sem `?`) permitidas por área: existem sempre antes do agente rodar
REQUIRED_ALLOWED = {"one_pager", "gate_estrutural_report", "nucleo_narrativo"}

EXPECTED_AGENTS = {
    "NucleoNarrativoLoop", "A01NucleoNarrativo", "A02MicroGate", "A03MicroGateCheck", "A04SecoesApoio",
    "GateEstruturalLoop", "A04bContratoProdutoCheck", "A05GateEstrutural", "A06GateEstruturalCheck", "A07RevisorOnePager",
    "AvaliacoesParalelas", "A08AvaliacaoPedagogica", "A09ExperienciaEstudante",
    "A10AdequacaoPedagogica",
    "A10bAdequacaoCheck",
    "A07RevisorOnePagerParecer",
    "AvaliacoesLoop", "A11GateFinalProduto",
    "A12GateFinalProdutoCheck", "A13SpecMissao", "A14BnccCheck", "A16bOnePagerResumido", "DesignStage", "A17FechaLacunas", "A18FechaLacunasSplit",
    "A19AmbienteSimulado", "A20AmbienteSimuladoSplit", "A21BriefOficio", "A22Jornada",
    "A23Fluxo", "A24CopyPtBr", "A25Caa", "A26Telas", "A27CopyRevisao", "A30QaEntregaveis",
    "A28Prototipo", "A29ArtefatosDesign", "A29bEspelhoMiro", "A31QaEntregaveisCheck", "DevStage", "A33ManifestoCheck", "HandoffParalelo", "A34HandoffDev", "A35BriefAssets",
    "A36TelemetriaCheck", "A38LacunaCheck", "A48PrdCheck",
    "BancaValidacaoDev", "A39BancaProdutoNarrativa", "A40BancaDesignImersao",
    "A41BancaPedagogiaBncc", "A42BancaDadosLgpd", "A43BancaTecnicaArquitetura",
    "A44ConsolidacaoBanca", "A45ValidacaoDevCheck", "A47PrdWriter", "A49OnePagerPedagogico",
    "A51Aprendizado",
    "A50Diagnostico", "ProdutoStage",
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

    # output_keys: únicos exceto one_pager (P0b e revisor escrevem a mesma chave de propósito) e
    # as instâncias de retrabalho, que reescrevem a chave do agente original — é o que faz a
    # correção do QA chegar a quem consome o artefato.
    e_retrabalho = lambda nome: "Retrabalho" in nome
    keys = [a.output_key for a in llm_agents if a.output_key and not e_retrabalho(a.name)]
    dupes = {k for k in keys if keys.count(k) > 1} - {"one_pager"}
    assert not dupes, f"output_keys duplicados: {dupes}"
    retrabalho = {a.name: a.output_key for a in llm_agents if e_retrabalho(a.name)}
    originais = {a.output_key for a in llm_agents if not e_retrabalho(a.name)}
    assert set(retrabalho.values()) <= originais, "retrabalho tem de reescrever a chave do agente original"
    assert set(keys) <= KNOWN_STATE_KEYS

    # loop e paralelos
    micro = next(a for _, a in iter_agent_tree(orchestrator) if a.name == "NucleoNarrativoLoop")
    assert isinstance(micro, LoopAgent) and micro.max_iterations == MICRO_GATE_MAX_RODADAS
    assert [a.name for a in micro.sub_agents] == ["A01NucleoNarrativo", "A01bVizinhasCatalogo", "A02MicroGate", "A03MicroGateCheck"]

    loop = next(a for _, a in iter_agent_tree(orchestrator) if a.name == "GateEstruturalLoop")
    assert isinstance(loop, LoopAgent) and loop.max_iterations == settings.gate_estrutural_max_rodadas
    # O lint vem antes do gate, dentro do loop: cada rodada relê a versão corrente do one-pager.
    # `A04bBriefEscopoSplit` entra desde 23/09/2026: o A04 entrega one-pager E brief de escopo
    # na mesma `output_key`, e o A07 devolve só o one-pager revisado — o brief evaporava a
    # cada execução, sem erro e sem artefato.
    assert [a.name for a in loop.sub_agents] == ["A04bBriefEscopoSplit", "A04bContratoProdutoCheck", "A05GateEstrutural", "A06GateEstruturalCheck", "A07RevisorOnePager"]
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
    assert [a.name for a in so_produto.sub_agents] == ["ProdutoStage", "A50Diagnostico", "A51Aprendizado", "A52RegistroCatalogo"]
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
    assert extrair_slug("Slug: exp06ef4b · nome") == "exp06ef4b"
    print("   ✓ envelope JSON e inferência de status")


# --------------------------------------------------------------------------- 4. fluxo determinístico
class FakeAgent(BaseAgent):
    extra_delta: dict = {}
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
            actions=EventActions(state_delta={**delta, **(self.extra_delta or {})}),
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


def test_gate_loop_reprova_e_jusante_segue_marcado():
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
    jusante = FakeAgent(name="Jusante", key="spec_missao", text="spec", before_agent_callback=marcar_heranca)
    root = SequentialAgent(name="Root", sub_agents=[loop, jusante])
    events, state = asyncio.run(_run(root))

    assert state["gate_estrutural_status"] == "bloqueado"
    assert state["gate_estrutural_rodada"] == 2
    assert state.get("revisoes") == 1, "o revisor deve rodar só na rodada 1 (na última o check escala)"
    assert state.get(KEY_PIPELINE_BLOQUEADO) is True
    # A esteira não aborta mais: o agente a jusante roda, e o que o diagnóstico precisa
    # (quem reprovou, quem herdou a reprovação) fica registrado no estado.
    assert state.get("spec_missao") == "spec", "o agente a jusante deve rodar mesmo com gate reprovado"
    assert "Jusante" in (state.get(KEY_AGENTES_DEGRADADOS) or []), "o jusante deve ficar marcado como degradado"
    degradacoes = state.get(KEY_DEGRADACOES) or []
    assert degradacoes and degradacoes[0]["gate"] == "Gate"
    assert "Gate" in (state.get(KEY_HERANCA) or ""), "o aviso de herança precisa citar o gate que reprovou"
    print("   ✓ loop reprova após 2 rodadas, revisor roda 1x, jusante segue marcado")


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
    jusante = FakeAgent(name="Jusante", key="spec_missao", text="spec", before_agent_callback=marcar_heranca)
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
            FakeAgent(name="Jusante", key="spec_missao", text="spec", before_agent_callback=marcar_heranca),
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
    # `segue_com_pendencias` é o que o nome diz: segue, COM pendências. Desde 23/09/2026 o
    # dossiê grava o veredito como o agente o deu, em vez de achatar tudo em "aprovado" — em
    # 14 execuções nenhum gate de LLM aparecia amarelo, embora os relatórios estivessem cheios
    # de amarelo. O ROTEAMENTO continua binário: a esteira segue.
    assert state["lacunas_status"] == "amarelo"
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

    # D9 devolvendo SÓ o bloco 14 sob o heading do Passo 4: é o pedaço novo, não a spec
    # consolidada. Aceitá-lo apagava blocos 0–13 — a ficha do manifesto sumia e o dev
    # bloqueava com 10 campos ausentes (visto em 2026-09-17: spec de 35 KB virou 5 KB).
    spec_grande = spec_consolidada + ("Bloco de spec com conteúdo real. " * 400)
    so_o_bloco = "## 14. Ambiente simulado (D9)\n" + ("instanooria, chrome, verbos e tokens. " * 60)
    d9_fragmento = (
        "# Ambiente simulado — teste\n\n"
        "## Passo 4 — Spec consolidada (blocos 1–13 + bloco 14)\n" + so_o_bloco +
        "\n## Bloco 14 — Ficha do ambiente\nnome: instanooria\n"
    )
    # o fragmento passa em `minimo_chars`; é a comparação com o documento atual que o pega
    assert len(so_o_bloco) > 1500
    root_frag = SequentialAgent(
        name="RootFrag",
        sub_agents=[
            FakeAgent(name="Spec", key="spec_missao", text=spec_grande),
            FakeAgent(name="D9", key="ambiente_simulado", text=d9_fragmento),
            get_ambiente_simulado_split(),
        ],
    )
    _, state_frag = asyncio.run(_run(root_frag))
    assert state_frag["spec_missao"] == spec_grande, "a spec foi trocada por um fragmento"

    # D9 sem a seção de spec (saída fora do formato) e com aguarda_gate: mantém a spec, marca 🔴, pipeline segue
    d9_ruim = '# Ambiente simulado\n**Veredito: 🔴 AGUARDA GATE 0**\n\n```json\n{"agente": "ambiente-simulado", "status": "aguarda_gate"}\n```'
    root3 = SequentialAgent(
        name="Root3",
        sub_agents=[
            FakeAgent(name="Spec", key="spec_missao", text=spec_consolidada),
            FakeAgent(name="D9", key="ambiente_simulado", text=d9_ruim),
            get_ambiente_simulado_split(),
            FakeAgent(name="Jusante", key="brief_oficio", text="brief", before_agent_callback=marcar_heranca),
        ],
    )
    _, state3 = asyncio.run(_run(root3))
    assert state3["spec_missao"] == spec_consolidada
    # `aguarda_gate` é o D9 devolvendo a decisão ao Gate 0 / PO: pendência humana, não
    # impedimento. Lido como bloqueio, travava a esteira num impasse que nenhum agente
    # resolve — não existe loop que devolva a decisão ao Gate 0 (23/09/2026).
    assert state3["ambiente_status"] == "amarelo"
    assert state3.get("brief_oficio") == "brief" and not state3.get(KEY_PIPELINE_BLOQUEADO)
    print("   ✓ split D0/D9: spec consolidada, cópia da original, relatório separado, status informativo")


# --------------------------------------------------------------------------- 6. BNCC Computação
_SPEC_BNCC = """# Spec — Teste v1

**5EF · unitube · Rubrica v1.17**

## 0. Identificação de plataforma
Slug `exp05ef2b` · séries `["5EF"]` · unidade B2 · `publico: estudante` · unitube · viewport 375×812.

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
            BnccCheckAgent(name="A14BnccCheck", estrito=True),
            FakeAgent(name="Jusante", key="brief_oficio", text="brief", before_agent_callback=marcar_heranca),
        ],
    )
    _, state = asyncio.run(_run(root))
    assert state["bncc_status"] == "bloqueado" and state.get(KEY_PIPELINE_BLOQUEADO) is True
    # O currículo reprovado não interrompe o design: ele segue marcado, e o diagnóstico registra.
    assert state.get("brief_oficio") == "brief" and "🔴 BLOQUEADO" in state["bncc_report"]
    assert "Jusante" in (state.get(KEY_AGENTES_DEGRADADOS) or [])
    assert state["bncc_status_envelope"]["agente"] == "bncc-check"

    # spec conforme: segue
    root2 = SequentialAgent(
        name="Root2",
        sub_agents=[
            FakeAgent(name="Spec", key="spec_missao", text=_SPEC_BNCC.format(codigos="EF05CO08 · EF05CO02")),
            BnccCheckAgent(name="A14BnccCheck", estrito=True),
            FakeAgent(name="Jusante", key="brief_oficio", text="brief", before_agent_callback=marcar_heranca),
        ],
    )
    _, state2 = asyncio.run(_run(root2))
    assert state2["bncc_status"] == "aprovado" and state2.get("brief_oficio") == "brief" and not state2.get(KEY_PIPELINE_BLOQUEADO)
    print("   ✓ BNCC: 130 habilidades; EF bloqueia código inexistente, ano errado, sem letramento e sem série; EM exige ≥1 EM13; gate trava a esteira")


# --------------------------------------------------------------------------- 7. rastro (manifesto · telemetria · lacunas)
_SPEC_MANIFESTO_OK = """# Spec — Teste v1

## 0. Identificação de plataforma
Nome: Teste. Ficha do manifesto:
- `id: exp05ef2b`
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
| EVT-001 | interacted | video:escolha | ao tocar | {"escolhido": true} | {"etapa": 3} | analítico | exp05ef2b_sessoes · GET /teste/turmas/:turmaId/painel |
## 5. Telemetria e entidades
Tabelas: `exp05ef2b_sessoes`, `exp05ef2b_gates_turma` (polling curto).
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

    # falso positivo 1: `objeto`/`resultado`/`contexto` vivem na célula de campos, e não
    # cada um na sua coluna. O contrato está cumprido; exigir o layout reprovava handoff
    # correto (visto em 2026-09-17 no exp-08).
    layout_livre = """# Handoff
| Evento | Verbo xAPI | Quando dispara | Campos | Canal |
|---|---|---|---|---|
| `publicar:postagem:capa` | `scored` | ao tocar Compartilhar | `objeto: "postagem:capa"`, `resultado: { focoId: "B" }`, `contexto: { zoom }` | Operacional |
Tabelas: `exp08ef2b_gates_turma` lida por polling HTTP de 3s.
"""
    assert validar_telemetria(layout_livre)["status"] == "aprovado", validar_telemetria(layout_livre)["achados"]

    # falso positivo 2: citar WebSocket para DESCARTÁ-LO é o comportamento correto, e
    # menção CONDICIONAL ("só se a infra mudar", "fase 2") é descarte, não proposta.
    # Era a forma de 5 dos 8 achados de WebSocket das 14 primeiras execuções — todos em
    # handoffs cujo canal declarado já era o polling certo (corte A4, 23/09/2026).
    nega = layout_livre + "\n| Sincronização | Polling de 3s | WebSocket dedicado só se a infra mudar | Cloud Run não sustenta WebSocket (ADR-93/94) |\n"
    r_nega = validar_telemetria(nega)
    assert r_nega["status"] == "aprovado", r_nega["achados"]
    roadmap = layout_livre + "\nWebSocket fica para a fase 2.\n"
    assert validar_telemetria(roadmap)["status"] == "aprovado", validar_telemetria(roadmap)["achados"]
    sem_canal = layout_livre.replace("Tabelas: `exp08ef2b_gates_turma` lida por polling HTTP de 3s.", "Sala sincroniza por WebSocket dedicado.")
    assert validar_telemetria(sem_canal)["status"] == "bloqueado"

    # falso positivo 3: handoff bom REPETE as proibições para o dev não errar. Citar a
    # regra não é violá-la — e cada termo proibido tinha esse mesmo furo.
    repete_regras = layout_livre + """
- **Vocabulário de telemetria**: `track(verbo, objeto, { resultado, contexto })` estrito. Proibido campo `dados`.
- Papel `admin-contrato` não existe mais: são seis papéis desde o ADR-80.
- `AI_DAILY_TOKEN_QUOTA` foi removida; a quota vive em `ia_quotas` por perfil.
- Estado nunca é `enum` Prisma: é string com CHECK na migration.
- `POST /runs/:id/eventos` é do motor da exp-01 e não deve ser usado aqui.
"""
    r_repete = validar_telemetria(repete_regras)
    assert r_repete["status"] == "aprovado", r_repete["achados"]

    # mas USAR de verdade continua pegando. O sinal é a chave no payload ou a coluna na
    # tabela — não a frase em prosa, que é onde a regra aparece citada.
    propoe = layout_livre + '\npayload do evento: `{ "dados": { "foco": "A" } }`\n'
    assert {a["codigo"] for a in validar_telemetria(propoe)["achados"]} == {"campo-dados"}
    coluna = layout_livre.replace("| Campos | Canal |", "| dados | Canal |")
    assert {a["codigo"] for a in validar_telemetria(coluna)["achados"]} == {"campo-dados"}

    assert classificar_dono("jornada", "dev") == "design"
    assert classificar_dono("gate-estrutural", "dev") == "produto"
    assert classificar_dono("plataforma", "dev") == "plataforma"
    assert classificar_dono("dono: input", "dev") == "input"
    assert classificar_dono("qualquer coisa", "design") == "design"

    # O `dono:` cabe num colchete; quem fecha a pendência está na frase ao lado. A prosa em
    # volta só é consultada quando o dono declarado resultaria em bloqueio, e só é capaz de
    # aliviar o achado — jamais de agravá-lo.
    assert classificar_dono(
        "dono: produto", "produto",
        contexto="Confirmação da semana letiva junto à coordenação pedagógica da rede parceira",
    ) == "externo"
    assert classificar_dono("dono: produto", "produto") == "produto"  # sem contexto, como antes
    assert classificar_dono("dono: plataforma", "dev", contexto="responsabilidade do produto") == "plataforma"
    assert classificar_dono("dono: wireframes", "dev", contexto="a jornada ainda não fechou") == "design"
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
    # Desde 23/09/2026 os dois marcadores de dono fixo mudaram de etapa, e a contagem reflete
    # isso: `RS-n pendente` é pedido ao Gate 0/PO (humano, não produto) e
    # `[verificar no repositório]` é instrução para quem codifica (plataforma, não dev). Os
    # dois eram bloqueantes e os prompts mandavam escrevê-los — ver `references/donos-e-etapas.md`.
    assert r["por_etapa"] == {"input": 0, "produto": 1, "design": 1, "dev": 0, "plataforma": 2, "externo": 0, "humano": 1}, r["por_etapa"]
    assert r["status"] == "bloqueado", "gate-estrutural e wireframes continuam impedindo"
    so_plat = varrer_lacunas([{"chave": "prd_final", "rotulo": "PRD", "etapa_padrao": "dev"}], st)
    assert so_plat["status"] == "amarelo" and so_plat["por_etapa"]["plataforma"] == 1
    assert varrer_lacunas(fontes, {"spec_missao": "limpo", "handoff_dev": "limpo"})["status"] == "aprovado"

    # dono humano FORA da esteira (coordenação pedagógica, rede parceira, consultoria)
    # não trava o PRD: a validação humana acontece DEPOIS, com o PRD na mão. E a mesma
    # pendência propagada para outro documento conta uma vez só — o D9 reemite a spec
    # inteira, e isso fazia 1 pendência de produto virar "1 produto + 1 design".
    externo = "`[ABERTO — Coordenação Pedagógica / Designer Instrucional Externo]`: validar a semana da unidade na grade."
    st_ext = {"spec_missao": "spec\n" + externo, "handoff_dev": "handoff limpo"}
    r_ext = varrer_lacunas(fontes, st_ext)
    assert r_ext["status"] == "amarelo", r_ext["achados"]
    assert r_ext["por_etapa"]["externo"] == 1 and r_ext["por_etapa"]["produto"] == 0

    # Regressão de 2026-09-20 (sessão b2d9): a missão saía 🔴 por duas pendências sobre a semana
    # letiva em que a aula seria dada — coisa que ninguém na esteira decide. `criterios-pedagogicos.md`
    # (critério 5.5) já mandava registrar isso como 🔵 que "não bloqueia"; era o classificador que
    # discordava. O 🔵 sem dono reconhecível passou a cair em `externo`, não em `produto`.
    st_semana = {
        "spec_missao": (
            "* Rastreabilidade Bimestral: 6º ano, 1º bimestre. "
            "🔵 (Pendência 5.5: alocação da semana letiva exata a ser confirmada na implantação da rede escolar).\n"
            "* `[ABERTO — dono: produto]`: Confirmação da semana letiva exata junto à coordenação "
            "pedagógica da rede parceira. Não impede a construção de software."
        ),
        "handoff_dev": "handoff limpo",
    }
    r_semana = varrer_lacunas(fontes, st_semana)
    assert r_semana["status"] == "amarelo", r_semana["achados"]
    assert r_semana["por_etapa"]["externo"] == 2 and r_semana["por_etapa"]["produto"] == 0

    # Mas 🔵 que nomeia uma etapa da esteira continua barrando: o default mudou, o julgamento não.
    r_azul_design = varrer_lacunas(fontes, {"spec_missao": "🔵 falta o wireframe da tela de perfil", "handoff_dev": "limpo"})
    assert r_azul_design["status"] == "bloqueado" and r_azul_design["por_etapa"]["design"] == 1

    # `RS-n pendente` e `[verificar no repositório:]` têm dono fixo, e desde 23/09/2026 o dono
    # mudou: os dois eram bloqueantes (produto e dev) enquanto os PRÓPRIOS PROMPTS mandavam
    # escrevê-los — 17_fechamento_lacunas.md manda carimbar o RS-n, e 34/47 mandam marcar o
    # que só quem tem o monorepo confere. A esteira reprovava o agente por obedecer. Agora:
    # RS-n é pedido ao Gate 0/PO (humano) e o marcador de repositório é de plataforma.
    r_fixos = varrer_lacunas(fontes, {
        "spec_missao": "RS-3 pendente conforme a coordenação da rede parceira",
        "handoff_dev": "[verificar no repositório: nome da tabela] com a coordenação externa",
    })
    assert r_fixos["status"] == "amarelo", r_fixos["achados"]
    assert r_fixos["por_etapa"]["humano"] == 1 and r_fixos["por_etapa"]["plataforma"] == 1
    assert r_fixos["por_etapa"]["produto"] == 0 and r_fixos["por_etapa"]["dev"] == 0

    # Mas um documento CRAVEJADO de "verificar no repositório" não conhece o próprio gabarito:
    # aí a ausência deixa de ser pendência de plataforma e vira defeito de construção.
    muitos = " ".join(f"[verificar no repositório: campo {i}]" for i in range(9))
    r_muitos = varrer_lacunas(fontes, {"spec_missao": "limpo", "handoff_dev": muitos})
    assert r_muitos["status"] == "bloqueado", r_muitos["achados"]
    assert any(a.get("codigo") == "gabarito-desconhecido" for a in r_muitos["achados"]), r_muitos["achados"]
    assert r_ext["achados"][0]["severidade"] == "atencao"

    fontes_com_d9 = fontes + [{"chave": "ambiente_simulado", "rotulo": "ambiente simulado (D9)", "etapa_padrao": "design"}]
    st_dup = dict(st_ext, ambiente_simulado="spec reemitida\n" + externo)
    r_dup = varrer_lacunas(fontes_com_d9, st_dup)
    assert len(r_dup["achados"]) == 1, "a mesma pendência contou duas vezes"
    assert r_dup["achados"][0]["documento"] == "spec"
    assert r_dup["achados"][0]["tambem_em"] == ["ambiente simulado (D9)"]

    # e dono de etapa da esteira continua bloqueando, em qualquer documento
    st_dev = {"spec_missao": "spec [ABERTO — gate-estrutural]", "handoff_dev": "limpo"}
    assert varrer_lacunas(fontes, st_dev)["status"] == "bloqueado"

    # citar o formato do marcador não é ter uma pendência. A spec e o D9 fecham com
    # "Lista de pendências `[ABERTO — dono]` consolidada: nenhuma" e isso barrava o PRD
    # por lacuna de produto e de design (visto em 2026-09-17 no exp-08).
    citacao = {
        "spec_missao": "**Lista de pendências `[ABERTO — dono]` consolidada:**\n*Nenhuma pendência em aberto.*",
        "handoff_dev": "Marque o que faltar como `[LACUNA — dono: x]` ou `[NEEDS CLARIFICATION: …]`.",
    }
    assert varrer_lacunas(fontes, citacao)["status"] == "aprovado", varrer_lacunas(fontes, citacao)["achados"]

    # e um marcador de verdade, com dono preenchido, continua bloqueando
    real = {"spec_missao": "decisão pendente [ABERTO — gate-estrutural]", "handoff_dev": "limpo"}
    r_real = varrer_lacunas(fontes, real)
    assert r_real["status"] == "bloqueado" and r_real["por_etapa"]["produto"] == 1, r_real["por_etapa"]

    # gate: lacuna de design bloqueia e pula o jusante; só plataforma segue com 🟡
    root = SequentialAgent(
        name="Root",
        sub_agents=[
            FakeAgent(name="Spec", key="spec_missao", text="# Spec\nSlug: exp05ef2b\n"),
            FakeAgent(name="Handoff", key="handoff_dev", text=st["handoff_dev"]),
            RastroCheckAgent(name="A38LacunaCheck", modo="lacunas", rotulo="Rastro", report_key="rastro_lacunas_report", status_key="rastro_lacunas_status", fontes=fontes, estrito=True),
            FakeAgent(name="Jusante", key="prd_final", text="prd", before_agent_callback=marcar_heranca),
        ],
    )
    _, state = asyncio.run(_run(root))
    assert state["rastro_lacunas_status"] == "bloqueado" and state.get(KEY_PIPELINE_BLOQUEADO) is True
    # O PRD sai mesmo com o rastro reprovado — sem ele não há o que diagnosticar.
    assert state.get("prd_final") == "prd"
    assert "**design `1`**" in state["rastro_lacunas_report"]
    root2 = SequentialAgent(
        name="Root2",
        sub_agents=[
            FakeAgent(name="Handoff", key="handoff_dev", text="[LACUNA — dono: plataforma] ponte tiktooria"),
            RastroCheckAgent(name="A38LacunaCheck", modo="lacunas", rotulo="Rastro", report_key="rastro_lacunas_report", status_key="rastro_lacunas_status", fontes=fontes, estrito=True),
            FakeAgent(name="Jusante", key="prd_final", text="prd", before_agent_callback=marcar_heranca),
        ],
    )
    _, state2 = asyncio.run(_run(root2))
    assert state2["rastro_lacunas_status"] == "amarelo" and state2.get("prd_final") == "prd" and not state2.get(KEY_PIPELINE_BLOQUEADO)
    root3 = SequentialAgent(
        name="Root3",
        sub_agents=[
            # `liberacao` ausente é default (corte A8); o que reprova é declarar outro
            # valor — aqui a ficha perde o `id`, que não tem default nenhum.
            FakeAgent(name="Spec", key="spec_missao", text=_SPEC_MANIFESTO_OK.replace("- `id: exp05ef2b`\n", "")),
            RastroCheckAgent(name="A33ManifestoCheck", modo="manifesto", rotulo="Manifesto", report_key="manifesto_report", status_key="manifesto_status", estrito=True),
            FakeAgent(name="Jusante", key="handoff_dev", text="h", before_agent_callback=marcar_heranca),
        ],
    )
    _, state3 = asyncio.run(_run(root3))
    # Manifesto reprovado não impede o handoff: ele sai marcado, e o diagnóstico aponta o dono.
    assert state3["manifesto_status"] == "bloqueado" and state3.get("handoff_dev") == "h"
    print("   ✓ rastro: manifesto, telemetria e lacunas por dono; reprovado marca a herança e segue; só plataforma 🟡")


_BLOCO9_COMPLETO = (
    "A gravação vai para `exp05ef2b_audios` (escola_id, RLS). Retenção de 60 dias. "
    "Quem lê: só a professora da escola, nunca rota de gestor."
)


def test_capacidade_de_plataforma_nao_bloqueia():
    """Capacidade que a plataforma ainda não concede é pré-requisito, não impedimento.

    A missão declara o que precisa (gravar voz, câmera, vídeo); o gate marca dono
    `plataforma`, o PRD sai 🟡 e o pipeline segue. Só é bloqueio quando o valor não
    existe no navegador, quando já é concedido a todas (declarar derruba o deploy)
    ou quando a missão captura mídia de criança sem dizer onde ela fica.
    """
    from agents.checkers import RastroCheckAgent
    from tools.rastro import validar_manifesto

    def spec(permissoes: str, bloco9: str = "sem coleta de mídia") -> str:
        return (
            "# Spec — Teste v1\n\n## 0. Identificação de plataforma\n"
            "- `id: exp02ef1b`\n- `produto: entre-redes`\n- `series: [\"2EF\"]`\n"
            "- `unidade: 1`\n- `publico: estudante`\n- `viewport: 375x812`\n"
            f"- `permissoes: {permissoes}`\n"
            "- `capabilities: [telemetria, progresso]`\n- `secao_ds: instanooria`\n"
            "- `liberacao: por-turma`\n\n"
            f"## 9. Evidências e dados\n{bloco9}\n\n## 10. Cenários\nx\n"
        )

    # o que já funciona hoje: nada a declarar além das três permissões
    assert validar_manifesto(spec("[forms]"))["status"] == "aprovado"

    # gravar voz: pendência de PLATAFORMA, e o bloco 9 diz onde a mídia fica
    r = validar_manifesto(spec("[forms, microphone]", _BLOCO9_COMPLETO))
    assert r["status"] == "amarelo", r["achados"]
    donos = {a["etapa"] for a in r["achados"]}
    assert donos == {"plataforma"}, donos
    assert all(a["severidade"] == "atencao" for a in r["achados"])
    assert any("capacidades-plataforma" in a["resumo"] for a in r["achados"])

    # gravar vídeo = câmera + microfone, mesma regra
    assert validar_manifesto(spec("[camera, microphone]", _BLOCO9_COMPLETO))["status"] == "amarelo"

    # capturar mídia de criança sem dizer onde fica é problema de PRODUTO
    r = validar_manifesto(spec("[microphone]"))
    assert r["status"] == "bloqueado"
    assert any(a["etapa"] == "produto" and "bloco 9" in a["resumo"] for a in r["achados"])

    # já concedido a todas: declarar derruba o deploy com 400
    r = validar_manifesto(spec("[autoplay]"))
    assert r["status"] == "amarelo" and r["achados"][0]["etapa"] == "dev"
    assert "já é concedido" in r["achados"][0]["resumo"]

    # valor que não existe no navegador continua bloqueio
    assert validar_manifesto(spec("[telepatia]"))["status"] == "bloqueado"

    # capability fora do vocabulário: pendência de plataforma, não bloqueio
    r = validar_manifesto(spec("[forms]").replace("[telemetria, progresso]", "[telemetria, realidade-aumentada]"))
    assert r["status"] == "amarelo" and r["achados"][0]["etapa"] == "plataforma"

    # o gate com amarelo NÃO impede o jusante
    root = SequentialAgent(
        name="Root",
        sub_agents=[
            FakeAgent(name="Spec", key="spec_missao", text=spec("[forms, microphone]", _BLOCO9_COMPLETO)),
            RastroCheckAgent(name="A33ManifestoCheck", modo="manifesto", rotulo="Manifesto", report_key="manifesto_report", status_key="manifesto_status", estrito=True),
            FakeAgent(name="Jusante", key="prd_final", text="prd", before_agent_callback=marcar_heranca),
        ],
    )
    _, state = asyncio.run(_run(root))
    assert state["manifesto_status"] == "amarelo"
    assert state.get("prd_final") == "prd" and not state.get(KEY_PIPELINE_BLOQUEADO)
    assert "pré-requisito" in state["manifesto_report"]
    print("   ✓ capacidades: microfone/câmera viram pendência de plataforma (🟡) e o PRD segue; sem bloco 9 é produto; inventado é bloqueio")


def test_regressao_sessao_8f76_falsos_positivos():
    """Sessão 8f76 (exp06ef1b, 2026-09-21): a missão saiu 🔴 por quatro leituras erradas dos
    verificadores. A spec, o handoff e o PRD estavam como o gabarito manda — o defeito era do leitor."""
    from tools.rastro import classificar_dono, validar_manifesto, validar_telemetria, varrer_lacunas

    # 1. A prosa do bloco 0 repete "viewport:" ANTES da ficha; a linha da ficha é quem manda.
    spec = _SPEC_MANIFESTO_OK.replace(
        "Nome: Teste. Ficha do manifesto:",
        "- **Software clonado:** Instagram (feed, perfis, DMs)\n"
        "- **Por que este viewport:** Viewport mobile vertical padrão (`375x812`), fidelidade da rolagem.\n"
        "**Ficha do manifesto — obrigatória, uma linha por campo, neste formato exato:**",
    )
    r_man = validar_manifesto(spec)
    assert r_man["status"] == "aprovado", r_man["achados"]
    assert r_man["campos"]["viewport"] == "375x812"
    # e ficha com valor inválido continua reprovando, mesmo com a prosa por perto
    assert validar_manifesto(spec.replace("`viewport: 375x812`", "`viewport: celular`"))["status"] == "bloqueado"

    # 2. Dono flexionado ou acentuado: "coordenador pedagógico" é gente de fora, não produto.
    assert classificar_dono("coordenador pedagógico: conferir rastreabilidade semanal com grade do Entre Redes", "produto") == "externo"
    assert classificar_dono("Coordenação pedagógica da rede", "produto") == "externo"
    assert classificar_dono("pedagógico", "dev") == "produto"  # o acento não apaga o token de produto

    # 2b. Dono escrito como slug com hífen (PRD de correção, 2026-09-21): a palavra continua valendo,
    # e `design-system` continua caindo em plataforma antes de virar "design".
    assert classificar_dono("Conferir rastreabilidade semanal, dono: coordenador-pedagogico, prazo: x", "dev") == "externo"
    assert classificar_dono("Gravar o podcast no bucket, dono: estudio-audio, prazo: hml", "dev") == "externo"
    assert classificar_dono("especialista curricular: confirmar alocação na matriz do Entre Redes", "produto") == "externo"
    assert classificar_dono("dono: design-system", "dev") == "plataforma"
    assert classificar_dono("dono: handoff-dev", "design") == "dev"

    # 3. `dono: produto` no fim do marcador não esconde que o pedido é homologação (ato humano).
    assert classificar_dono(
        "Homologação cadastral definitiva do slug de catálogo (exp-NN vs exp06ef1b), dono: produto, prazo: release", "dev"
    ) == "humano"
    # o corpo do marcador só alivia: pedido de construção com dono produto segue produto
    assert classificar_dono("Definir regra de cardinalidade do bloco 2, dono: produto", "dev") == "produto"

    # Os três marcadores literais da spec da sessão, no rastro antes do PRD: nenhum bloqueia.
    fontes = [{"chave": "spec_missao", "rotulo": "spec da missão", "etapa_padrao": "produto"}]
    st = {"spec_missao": (
        "- Bios das contas candidatas: `[ABERTO — produto: homologar teto de 120 caracteres para bios]`.\n"
        "- Legendas dos posts: `[ABERTO — produto: homologar teto de 60 palavras por legenda]`.\n"
        "- `[ABERTO — coordenador pedagógico: conferir rastreabilidade semanal com grade do Entre Redes]`\n"
    )}
    r = varrer_lacunas(fontes, st)
    assert r["status"] == "amarelo", r["achados"]
    assert r["por_etapa"] == {"input": 0, "produto": 0, "design": 0, "dev": 0, "plataforma": 0, "externo": 1, "humano": 2}, r["por_etapa"]

    # e o PRD com o NEEDS CLARIFICATION do slug sai 🟡, como o gate estrutural e o gate final já diziam
    prd = {"prd_final": "1. `[NEEDS CLARIFICATION: Homologação cadastral definitiva do slug de catálogo (exp-NN vs exp06ef1b), dono: produto, prazo: release]`."}
    r_prd = varrer_lacunas([{"chave": "prd_final", "rotulo": "PRD", "etapa_padrao": "dev"}], prd)
    assert r_prd["status"] == "amarelo" and r_prd["por_etapa"]["humano"] == 1, r_prd["achados"]

    # 4. Descartar WebSocket com "sem custos de", "(sem WebSockets)" e "sem suporte a" é seguir a plataforma.
    handoff = _HANDOFF_OK + (
        "\n| Sincronização de Sala | Polling HTTP curto (3–5s) na tabela `exp05ef2b_gates_turma`. | Polling atende ao Cloud Run sem custos de WebSocket ou infraestrutura durável. |\n"
        "- Sincronização via polling HTTP em tabela de gates (sem WebSockets).\n"
        "1. **Relógio coletivo:** polling de 3–5s em `exp05ef2b_gates_turma`. Sem suporte a WebSockets.\n"
        "Zero WebSockets ou `hub:pause` como canal de sincronização.\n"
    )
    r_tel = validar_telemetria(handoff)
    assert r_tel["status"] == "aprovado", r_tel["achados"]
    # propor WebSocket de verdade continua sendo pego
    propoe = validar_telemetria(_HANDOFF_OK + "\nA sala usa WebSocket dedicado para o relógio coletivo.")
    assert {a["codigo"] for a in propoe["achados"]} == {"websocket-mencao"}, propoe["achados"]


def test_gate_amarelo_limpa_degradacao_da_rodada_anterior():
    """Regressão de 2026-09-21 (exp06ef1b): o prd-check reprovou na rodada 1 e saiu 🟡 na 2, mas
    só `aprovado` limpava a marca — a execução terminava `pipeline_bloqueado` com zero impedimento
    e o diagnóstico listava o PRD como provisório."""
    from agents.checkers import RastroCheckAgent

    fontes = [{"chave": "prd_final", "rotulo": "PRD", "etapa_padrao": "dev"}]

    def check(nome):
        return RastroCheckAgent(
            name=nome, modo="lacunas", rotulo="Pendências do PRD", report_key="prd_check_report",
            status_key="prd_status", fontes=fontes, agente="prd-check", estrito=True,
        )

    root = SequentialAgent(
        name="Root",
        sub_agents=[
            FakeAgent(name="Prd1", key="prd_final", text="rascunho [NEEDS CLARIFICATION: qual cardinalidade?, dono: produto]"),
            check("Check1"),
            FakeAgent(name="Prd2", key="prd_final", text="rascunho [ABERTO — coordenação pedagógica: confirmar semana]"),
            check("Check2"),
        ],
    )
    _, state = asyncio.run(_run(root))
    assert state["prd_status"] == "amarelo", state.get("prd_check_report")
    assert state.get(KEY_PIPELINE_BLOQUEADO) is False, "a reprovação da rodada 1 não pode sobreviver ao 🟡 da rodada 2"
    assert not state.get(KEY_DEGRADACOES), state.get(KEY_DEGRADACOES)
    assert not state.get(KEY_HERANCA)
    print("   ✓ gate 🔴 → 🟡 limpa a degradação e destrava a execução")


def test_diagnostico_respeita_veredito_do_gate():
    """Regressão de 2026-09-21 (exp06ef1b, DES-14): a banca aprovou com `nok_bloqueantes: 0`, mas
    rotulou um ❌ de critério não bloqueante como `severidade: bloqueio`, e o diagnóstico contava
    isso como impedimento — execução 🔴 com todos os gates 🟢/🟡."""
    from tools.diagnostico import coletar

    st = {
        "dev_status": "aprovado",
        "dev_status_envelope": {"status": "aprovado", "veredito": "amarelo", "achados": [
            {"id": "DES-14", "severidade": "bloqueio", "agente_responsavel": "wireframes", "resumo": "telas docentes sem nós"},
        ]},
        "prd_status": "amarelo",
        "prd_status_envelope": {"achados": [{"severidade": "bloqueio", "codigo": "x", "resumo": "y"}]},
    }
    d = coletar(st)
    assert d["veredito"] != "bloqueado", d["veredito"]
    assert not d["bloqueios"] and len(d["ressalvas"]) == 2, (d["bloqueios"], d["ressalvas"])

    # gate reprovado continua produzindo impedimento
    st_ruim = dict(st, prd_status="bloqueado")
    d_ruim = coletar(st_ruim)
    assert d_ruim["veredito"] == "bloqueado" and len(d_ruim["bloqueios"]) == 1
    print("   ✓ diagnóstico: achado 'bloqueio' de gate aprovado vira ressalva; de gate reprovado, impedimento")


def test_estagio_produto_parcial_spec():
    """Modo correção a partir da spec: só SpecLoop + one-pager resumido, sem núcleo nem gates."""
    from google.adk.agents.llm_agent import LlmAgent

    from agents.produto import build_produto_stage
    from pipeline.orchestrator import STAGE_SPEC, create_mission_orchestrator, iter_agent_tree, stages_para_ui

    orch = create_mission_orchestrator(stages=["spec"])
    assert [a.name for a in orch.sub_agents] == ["ProdutoStage", "A50Diagnostico", "A51Aprendizado", "A52RegistroCatalogo"]
    produto = orch.sub_agents[0]
    assert [a.name for a in produto.sub_agents] == ["SpecLoop", "A16bOnePagerResumido"]
    # `A15bEvidenciaCheck` entra desde 23/09/2026: grau `scored` com dois sinais, habilidade do
    # bloco 11 com momento e medida, gabarito no servidor. Eram três exigências que a spec
    # declarava em prosa e nenhuma verificação tocava — PED-04 é bloqueante e ninguém o conferia.
    # `A15cPerguntasCheck` e o juiz `A15dJuizPerguntas` entram em 23/09/2026: as cinco perguntas
    # de produto do sub-bloco 9f nasciam na spec sem nenhum gate, e o `validar_kpis` do PRD recebia
    # a spec como parâmetro morto — a pergunta podia morrer entre produto e dev sem deixar rastro.
    assert [a.name for a in produto.sub_agents[0].sub_agents] == [
        "A13SpecMissao", "A14BnccCheck", "A15ManifestoCheckProduto", "A15bEvidenciaCheck",
        "A15cPerguntasCheck", "A15dJuizPerguntas", "A15eJuizPerguntasCheck", "A16SpecCheck"]
    assert produto.sub_agents[0].max_iterations == max(1, get_settings().spec_max_rodadas)
    nomes = [a.name for _, a in iter_agent_tree(orch)]
    assert "A01NucleoNarrativo" not in nomes and "A05GateEstrutural" not in nomes
    assert not any(getattr(a, "include_contents", "none") == "default" for _, a in iter_agent_tree(orch) if isinstance(a, LlmAgent)), \
        "nenhum agente da correção lê a mensagem do usuário: o pedido viaja pelo estado"

    completo = create_mission_orchestrator(stages=["spec", "design", "dev"])
    assert [a.name for a in completo.sub_agents] == ["ProdutoStage", "DesignStage", "DevStage", "A50Diagnostico", "A51Aprendizado", "A52RegistroCatalogo"]
    todos = [a.name for _, a in iter_agent_tree(completo)]
    assert len(todos) == len(set(todos)), "nome duplicado na árvore parcial"
    # "produto" e "spec" juntos: a etapa inteira vence
    assert "A01NucleoNarrativo" in [a.name for _, a in iter_agent_tree(create_mission_orchestrator(stages=["produto", "spec"]))]

    try:
        build_produto_stage(a_partir_de="design")
        assert False, "a_partir_de inválido deveria falhar"
    except ValueError:
        pass

    assert [s["key"] for s in stages_para_ui(["spec", "design", "dev"])] == ["spec", "design", "dev", "transversal"]
    assert [s["key"] for s in stages_para_ui(["dev"])] == ["dev", "transversal"]
    assert [s["key"] for s in stages_para_ui(["produto", "design", "dev"])] == ["produto", "design", "dev", "transversal"]
    assert [m["id"] for m in STAGE_SPEC["agents"]] == [
        "A13SpecMissao", "A14BnccCheck", "A15ManifestoCheckProduto", "A15bEvidenciaCheck",
        "A15cPerguntasCheck", "A15dJuizPerguntas", "A15eJuizPerguntasCheck",
        "A16SpecCheck", "A16bOnePagerResumido"]
    print("   ✓ estágio parcial spec: SpecLoop + resumido, sem núcleo; stages_para_ui resolve spec")


def test_bloco_de_correcao_em_todos_os_agentes():
    """Modo correção: o pedido chega a todo agente LLM pelo rodapé de `agents/base.py`, como a herança."""
    from google.adk.agents.llm_agent import LlmAgent

    from pipeline.orchestrator import create_mission_orchestrator, iter_agent_tree

    llms = [a for _, a in iter_agent_tree(create_mission_orchestrator(stages=["produto", "design", "dev"])) if isinstance(a, LlmAgent)]
    assert llms, "árvore sem agentes LLM?"
    sem_bloco = [a.name for a in llms if "{pedido_correcao?}" not in str(a.instruction)]
    assert not sem_bloco, f"agentes sem o bloco de correção: {sem_bloco}"
    sem_heranca = [a.name for a in llms if "{heranca_degradada?}" not in str(a.instruction)]
    assert not sem_heranca, sem_heranca
    print(f"   ✓ {len(llms)} agentes LLM leem `pedido_correcao` e `heranca_degradada`")


def test_agente_de_triagem_configurado():
    """A triagem vê a mensagem e os anexos (como o A01), grava em `triagem_correcao` e fica fora da esteira."""
    from agents.transversal import TRANSVERSAL_METADATA, get_triagem_correcao_agent
    from prompts.loader import list_state_variables

    agente = get_triagem_correcao_agent()
    assert agente.include_contents == "default"
    assert agente.output_key == "triagem_correcao"
    instr = str(agente.instruction)
    assert "{mapa_da_missao?}" in instr and "{briefing?}" in instr
    assert '"etapa": "spec | design | dev | nenhuma"' in instr
    assert all(m["id"] != "A00TriagemCorrecao" for m in TRANSVERSAL_METADATA)
    for var in list_state_variables(instr):
        assert var in KNOWN_STATE_KEYS, var
    print("   ✓ triagem: include_contents=default, output triagem_correcao, fora dos metadados")


def test_rotulos_de_gate_cobertos_pelo_mapa_de_heranca():
    """Modo correção: a herança de gates não refeitos é preservada por rótulo. Se um rótulo da
    árvore real não estiver em `ROTULOS_GATE_POR_ETAPA`, a reprovação dele cai em silêncio."""
    from agents.checkers import BnccCheckAgent, EnvelopeGateAgent, RastroCheckAgent
    from pipeline.orchestrator import create_mission_orchestrator, iter_agent_tree
    from pipeline.reexecucao import ROTULOS_GATE_POR_ETAPA

    faltando = set()
    for _, agente in iter_agent_tree(create_mission_orchestrator(stages=["produto", "design", "dev"])):
        if isinstance(agente, (EnvelopeGateAgent, BnccCheckAgent, RastroCheckAgent)):
            if agente.rotulo not in ROTULOS_GATE_POR_ETAPA:
                faltando.add(agente.rotulo)
    assert not faltando, f"rótulos sem etapa no mapa de herança: {sorted(faltando)}"
    print("   ✓ todo gate da árvore tem etapa no mapa de herança do modo correção")


def test_mensagem_de_pulo_nao_vira_prd():
    """O texto que o ADK grava ao pular um agente não pode virar PRD nem artefato."""
    from pipeline.artifacts import e_mensagem_de_pulo

    pulo = "⏭️ `A47PrdWriter` não executado — pipeline bloqueado (Ficha do manifesto bloqueado (1 lacuna(s)))."
    assert e_mensagem_de_pulo(pulo)
    assert not e_mensagem_de_pulo("# PRD — missão\n\nconteúdo de verdade")
    assert not e_mensagem_de_pulo(None) and not e_mensagem_de_pulo("")

    from pipeline.runner import PipelineExecutionResult

    bloqueado = PipelineExecutionResult(
        session_id="s", user_id="u", prompt="p", final_output="",
        state={"prd_final": pulo, "pipeline_bloqueado": True, "pipeline_bloqueio_motivo": "Ficha do manifesto bloqueado"},
    )
    assert bloqueado.prd_gerado is None
    assert bloqueado.gate_que_bloqueou == "Ficha do manifesto bloqueado"
    ok = PipelineExecutionResult(session_id="s", user_id="u", prompt="p", final_output="", state={"prd_final": "# PRD\n..."})
    assert ok.prd_gerado and ok.gate_que_bloqueou is None
    print("   ✓ mensagem de pulo não vira PRD.md nem 'PRD gerado' na tela; o motivo do bloqueio é o do gate que travou")


def test_contencao_de_resposta_de_ferramenta():
    """Resposta de ferramenta MCP não pode estourar o teto de contexto do modelo.

    O D5 pedindo tela ao Stitch acumula respostas grandes,
    o dump de `get_figjam` e a imagem de `get_screenshot` no MESMO turno —
    `include_contents="none"` não descarta histórico de chamada de ferramenta. Foi
    assim que um prompt de 22 KB estourou 1.048.576 tokens.
    """
    import json as _json

    from agents.base import create_llm_agent
    from agents.callbacks import (
        MCP_ORCAMENTO_POR_AGENTE,
        MCP_RESPOSTA_MAX,
        barrar_ferramenta_sem_orcamento,
        limitar_resposta_de_ferramenta,
    )

    class _Tool:
        name = "get_screenshot"

    class _Ctx:
        agent_name = "A22Jornada"

        def __init__(self):
            self.state = {}

    ctx = _Ctx()

    # imagem nunca volta ao contexto
    imagem = {"content": [{"mimeType": "image/png", "data": "A" * 900_000}]}
    r = limitar_resposta_de_ferramenta(tool=_Tool(), args={}, tool_context=ctx, tool_response=imagem)
    assert len(_json.dumps(r)) < 1_000 and "captura de 900000" in _json.dumps(r)

    # dump grande de board é truncado, e a estrutura some em favor de um trecho
    grande = {"nodes": [{"id": f"n{i}", "texto": "x" * 400} for i in range(500)]}
    r = limitar_resposta_de_ferramenta(tool=_Tool(), args={}, tool_context=ctx, tool_response=grande)
    assert len(_json.dumps(r)) <= MCP_RESPOSTA_MAX + 2_000

    # resposta pequena passa intacta (None = não substitui)
    assert limitar_resposta_de_ferramenta(tool=_Tool(), args={}, tool_context=_Ctx(), tool_response={"ok": True}) is None

    # o gasto é debitado por agente, e o orçamento esgotado recusa a próxima chamada
    assert ctx.state[f"temp:mcp_gasto_{ctx.agent_name}"] > 0
    assert barrar_ferramenta_sem_orcamento(tool=_Tool(), args={}, tool_context=ctx) is None
    ctx.state[f"temp:mcp_gasto_{ctx.agent_name}"] = MCP_ORCAMENTO_POR_AGENTE + 1
    recusa = barrar_ferramenta_sem_orcamento(tool=_Tool(), args={}, tool_context=ctx)
    assert recusa and recusa["recusado"] and "entregue o documento" in recusa["motivo"]

    # trava de assinatura: o ADK chama todo callback por keyword, e o nome do
    # parâmetro é parte do contrato. Um nome errado só falha em tempo de execução,
    # no meio de uma esteira — então a conferência tem que ser aqui.
    import inspect

    from agents.callbacks import marcar_heranca

    contrato = {
        marcar_heranca: ("before_agent_callback", ["callback_context"]),
        barrar_ferramenta_sem_orcamento: ("before_tool_callback", ["tool", "args", "tool_context"]),
        limitar_resposta_de_ferramenta: ("after_tool_callback", ["tool", "args", "tool_context", "tool_response"]),
    }
    for fn, (papel, exigidos) in contrato.items():
        params = list(inspect.signature(fn).parameters)
        faltando = [p for p in exigidos if p not in params]
        assert not faltando, f"{fn.__name__} como {papel}: o ADK passa {exigidos}, faltam {faltando} (tem {params})"

    # a contenção entra sozinha em todo agente COM ferramentas, e só neles
    def _ferramenta_de_teste() -> str:
        """Ferramenta qualquer, só para o agente nascer com `tools`."""
        return "ok"

    com = create_llm_agent(name="ComTools", instruction="x", description="d", tools=[_ferramenta_de_teste])
    sem = create_llm_agent(name="SemTools", instruction="x", description="d")
    assert com.before_tool_callback and com.after_tool_callback
    assert not sem.before_tool_callback and not sem.after_tool_callback
    print("   ✓ contenção de MCP: imagem fora do contexto, dump truncado, orçamento por agente, aplicada a todo agente com ferramentas")


def test_markdown_saneado_para_streamlit():
    """O `$` da prosa não é LaTeX, e cerca aberta não engole o resto do documento.

    Regressão de 2026-09-20: saídas de agente apareciam com trechos em itálico matemático ou
    viravam um bloco de código gigante. O Streamlit lê `$…$` como KaTeX; "custa R$ 10, no
    máximo R$ 30" some entre os dois cifrões.
    """
    from tools.markdown_blocos import limpar, sanear_para_streamlit

    assert sanear_para_streamlit("custa R$ 10 ou R$ 30") == r"custa R\$ 10 ou R\$ 30"
    # dentro de crase é código, e código fica como o agente escreveu
    assert sanear_para_streamlit("use `$VAR` e R$ 5") == r"use `$VAR` e R\$ 5"
    # dentro de cerca também: `DO $$ … END $$` é PL/pgSQL, não bloco LaTeX
    cercado = "```sql\nDO $$ x $$;\n```\ndepois R$ 9\n"
    assert "DO $$ x $$;" in sanear_para_streamlit(cercado)
    assert r"depois R\$ 9" in sanear_para_streamlit(cercado)
    # cerca aberta pelo agente ganha fechamento, senão o resto da página vira código
    assert sanear_para_streamlit("texto\n```py\nx=1\n").endswith("```\n")
    assert sanear_para_streamlit("sem cifrao") == "sem cifrao"

    # `limpar()` tira só o envelope de contrato do fim — um ```json citado no meio do
    # documento é conteúdo do leitor e sumia sem aviso no DOCX e no HTML do one-pager.
    doc = (
        "# Relatório\n\nExemplo de payload:\n\n```json\n{\"a\": 1}\n```\n\n"
        "Segue o texto.\n\n---\n```json\n{\"agente\": \"x\"}\n```\n"
    )
    limpo = limpar(doc)
    assert '"a": 1' in limpo and "Segue o texto" in limpo and "agente" not in limpo


def test_artefatos_html_e_links():
    """Protótipo, diagramas e links: o HTML nunca entra em prompt, e o link sim."""
    from agents.checkers import ArtefatosDesignAgent
    from tools.artefatos_html import extrair_prototipo, montar_folha_de_diagramas
    from tools.stitch_cliente import extrair_project_id, extrair_screen_ids, listar_telas

    doc = "<!doctype html><html><body><main>tela</main></body></html>"
    html, relatorio = extrair_prototipo(f"antes\n```html\n{doc}\n```\n# Protótipo\nTelas: 3")
    assert html == doc and relatorio.startswith("antes") and "Telas: 3" in relatorio
    assert extrair_prototipo("só um relatório, sem documento")[0] is None
    # sem cerca, mas com documento inteiro
    assert extrair_prototipo(f"nota\n{doc}\nfim")[0] == doc

    folha = montar_folha_de_diagramas("Missão", "a\n```mermaid\nflowchart LR\nA-->B\n```", "b\n```mermaid\nstateDiagram-v2\n[*] --> S\n```")
    assert folha and folha.count("<section>") == 2 and "flowchart LR" in folha
    assert montar_folha_de_diagramas("M", "sem diagrama", None) is None

    # A página fica gravada em disco e busca a CDN a cada abertura: a versão vai pinada no
    # patch, não na tag flutuante `@11`, senão um release novo quebra execuções antigas.
    assert "mermaid@11.4.1" in folha and "mermaid@11/" not in folha
    # E cada diagrama renderiza isolado: com `startOnLoad`, um Mermaid de sintaxe inválida
    # derrubava o desenho de todos os outros e a página abria vazia, sem dizer qual falhou.
    assert "startOnLoad: false" in folha and "mermaid.run(" in folha

    for texto, esperado in [
        ("**Projeto:** `12041009326340699841`", "12041009326340699841"),
        ("projects/9988776655443322", "9988776655443322"),
        ("nada", None),
    ]:
        assert extrair_project_id(texto) == esperado, texto

    # o `list_screens` do Stitch devolve `{}` mesmo para projeto COM telas (visto em
    # 2026-09-17). Sem a reserva por id, a folha de links sai vazia e o PRD perde a
    # prévia de todas as telas, embora elas existam.
    relatorio_d5 = """
    | `E4-PROF-01` | PICO | `dc2b98d9a9ae4608b955be811da3c2ca` | `DESKTOP` |
    | `E1-ALU-01` | Inicial | `9d1964dd932e4cc59e9c9ee2dd209491` | `MOBILE` |
    | repetida | — | `DC2B98D9A9AE4608B955BE811DA3C2CA` | — |
    """
    assert extrair_screen_ids(relatorio_d5) == [
        "dc2b98d9a9ae4608b955be811da3c2ca",
        "9d1964dd932e4cc59e9c9ee2dd209491",
    ]
    assert extrair_screen_ids("sem id nenhum") == [] and extrair_screen_ids(None) == []

    chamadas = []

    def _falso_chamar(ferramenta, argumentos, timeout=180):
        chamadas.append((ferramenta, argumentos))
        if ferramenta == "list_screens":
            return {}  # o vazio que o Stitch devolve de verdade
        i = argumentos["name"].rsplit("/", 1)[-1]
        return {"name": argumentos["name"], "title": f"tela {i[:4]}", "width": 780, "height": 2332,
                "deviceType": "MOBILE", "screenshot": {"downloadUrl": f"https://img/{i}"}}

    import tools.stitch_cliente as _sc

    original = _sc.chamar
    try:
        _sc.chamar = _falso_chamar
        telas = listar_telas("555", ["aa" * 16, "bb" * 16])
    finally:
        _sc.chamar = original
    assert [t["id"] for t in telas] == ["aa" * 16, "bb" * 16]
    assert telas[0]["url_imagem"] == f"https://img/{'aa' * 16}"
    assert chamadas[0][0] == "list_screens" and len(chamadas) == 3
    # sem ids reportados não há a quem recorrer: devolve vazio em vez de inventar
    try:
        _sc.chamar = _falso_chamar
        assert listar_telas("555") == []
    finally:
        _sc.chamar = original

    # o agente separa o HTML do relatório e monta os diagramas, sem rede e sem Stitch
    root = SequentialAgent(
        name="Root",
        sub_agents=[
            FakeAgent(name="Jornada", key="jornada_telas", text="j\n```mermaid\nflowchart LR\nA-->B\n```"),
            FakeAgent(name="Proto", key="prototipo_html", text=f"```html\n{doc}\n```\n# Relatório do protótipo"),
            ArtefatosDesignAgent(name="A29ArtefatosDesign"),
        ],
    )
    _, state = asyncio.run(_run(root))
    assert state["prototipo_arquivo"] == doc
    assert "Relatório do protótipo" in state["prototipo_relatorio"]
    assert state["diagramas_html"].count("<section>") == 1
    assert "prototipo_arquivo" not in "".join(load_prompt(f"design/{n}", **CONFIG_VARS) for n in ["30_qa_entregaveis.md"])
    print("   ✓ artefatos: protótipo separado do relatório, diagramas montados do Mermaid, projeto do Stitch reconhecido")


def test_visao_do_professor_nos_diagramas_e_na_folha_do_stitch():
    """O segundo grafo (professor) vira diagrama nomeado; a folha do Stitch denuncia a ausência dele."""
    from tools.artefatos_html import e_diagrama_do_professor, extrair_mermaid_com_titulos, montar_folha_de_diagramas
    from tools.stitch_cliente import montar_folha_de_links

    fluxo = (
        "## Grafo (Mermaid — obrigatório)\n```mermaid\nstateDiagram-v2\n[*] --> E1\n```\n\n"
        "## Fluxo do professor (Mermaid — obrigatório)\n```mermaid\nstateDiagram-v2\n[*] --> E0PROF01\n```\n"
    )
    blocos = extrair_mermaid_com_titulos(fluxo)
    assert [t for t, _ in blocos] == ["Grafo", "Fluxo do professor"]
    assert e_diagrama_do_professor(blocos[1][0]) and not e_diagrama_do_professor(blocos[0][0])

    folha = montar_folha_de_diagramas("M", None, fluxo)
    assert folha.count("<section>") == 2 and "<h2>Fluxo do professor</h2>" in folha

    # No Miro, o grafo do professor é um widget próprio com id estável.
    import tools.miro_cliente as _mc

    diagramas = []
    for chave, titulo_bloco, documento in (("fluxo", "Fluxo de telas", fluxo),):
        b = _mc.extrair_mermaid_com_titulos(documento)
        diagramas.append({"id": chave, "titulo": titulo_bloco, "mermaid": b[0][1]})
        prof = next((m for t, m in b[1:] if _mc.e_diagrama_do_professor(t)), None)
        if prof:
            diagramas.append({"id": f"{chave}-professor", "titulo": "Fluxo do professor", "mermaid": prof})
    svg = _mc.montar_svg(diagramas)
    assert 'id="fluxo"' in svg and 'id="fluxo-professor"' in svg

    dados = {"url_projeto": "https://stitch/p/1", "project_id": "1", "telas": [
        {"titulo": "E2-ALU-01 — Feed", "dispositivo": "MOBILE", "largura": 780, "altura": 1768, "url_imagem": "https://img/a"},
        {"titulo": "E4-PROF-01 — Telão", "dispositivo": "DESKTOP", "largura": 2732, "altura": 2048, "url_imagem": "https://img/b"},
    ]}
    sem_preparo = montar_folha_de_links(dados, "exp06ef1b")
    assert "## Visão do professor" in sem_preparo and "E4-PROF-01" in sem_preparo
    assert "[LACUNA — dono: telas]" in sem_preparo and "E0-PROF-01…05" in sem_preparo

    dados["telas"].append({"titulo": "E0-PROF-02 — Recorte da aula", "dispositivo": "DESKTOP", "url_imagem": "https://img/c"})
    com_preparo = montar_folha_de_links(dados, "exp06ef1b")
    assert "[LACUNA" not in com_preparo and "E0-PROF-02" in com_preparo
    print("   ✓ visão do professor: segundo grafo nomeado nos diagramas e no Miro; folha do Stitch denuncia preparo ausente")


def test_miro_espelha_o_mermaid_sem_rede():
    """O espelho publica o mesmo Mermaid da folha HTML e reusa o board entre rodadas."""
    import re

    from agents.checkers import EspelhoMiroAgent
    from tools.miro_cliente import ids_dos_widgets, montar_svg

    # O corpo do diagrama vai escapado: sem isso o `-->` de cada aresta viraria tag.
    svg = montar_svg([{"id": "fluxo", "titulo": "Fluxo & cia", "mermaid": "flowchart TD\n A[Um] --> B[Dois]"}])
    assert "--&gt;" in svg and "-->" not in svg
    assert 'data-type="diagram"' in svg and "Fluxo &amp; cia" in svg
    assert "data-miro-id" not in svg  # primeira publicação não tem id do servidor

    # Com o mapa de ids, o mesmo SVG vira update em vez de duplicata.
    svg2 = montar_svg([{"id": "fluxo", "titulo": "F", "mermaid": "flowchart TD\n A-->B"}], {"fluxo": "345"})
    assert 'data-miro-id="345"' in svg2
    assert ids_dos_widgets('<svg><foreignObject id="fluxo" data-type="diagram" data-miro-id="345">x</foreignObject></svg>') == {"fluxo": "345"}

    chamadas = []

    def _falsa_sessao(*_a, **_kw):
        class _S:
            def __enter__(self_):
                return self_

            def __exit__(self_, *_e):
                return False

            def chamar(self_, ferramenta, argumentos):
                chamadas.append((ferramenta, argumentos))
                if ferramenta == "board_create":
                    return {"miro_url": "https://miro.com/app/board/uXjTESTE=/", "name": argumentos["name"]}
                # O servidor devolve o SVG carimbado com um id por elemento; é daí que
                # sai o mapa que a rodada seguinte reenvia.
                locais = re.findall(r'<foreignObject id="([^"]+)"', argumentos["svg"])
                carimbados = "".join(
                    f'<foreignObject id="{i}" data-type="diagram" data-miro-id="77{n}">m</foreignObject>'
                    for n, i in enumerate(locais)
                )
                return {"success": True, "result_svg": f"<svg>{carimbados}</svg>"}

        return _S()

    import tools.miro_cliente as _mc

    original = _mc.SessaoMiro
    try:
        _mc.SessaoMiro = _falsa_sessao
        root = SequentialAgent(
            name="Root",
            sub_agents=[
                FakeAgent(name="Jornada", key="jornada_telas", text="j\n```mermaid\nflowchart TD\nA-->B\n```"),
                FakeAgent(name="Fluxo", key="fluxo_arestas", text="f\n```mermaid\nflowchart LR\nC-->D\n```"),
                EspelhoMiroAgent(name="A29bEspelhoMiro"),
            ],
        )
        _, state = asyncio.run(_run(root))
    finally:
        _mc.SessaoMiro = original

    assert "uXjTESTE" in state["miro_links"]
    assert state["miro_board"]["widgets"] == {"jornada": "770", "fluxo": "771"}
    assert [c[0] for c in chamadas] == ["board_create", "canvas_create_from_svg"]
    # o board nasce uma vez: a rodada seguinte atualiza o que já existe
    assert chamadas[1][1]["svg"].count('data-type="diagram"') == 2

    # Duas passagens na mesma sessão é o que acontece numa rodada de QA com retrabalho:
    # a segunda tem de ATUALIZAR o board da primeira, não criar outro.
    chamadas.clear()
    try:
        _mc.SessaoMiro = _falsa_sessao
        root = SequentialAgent(
            name="Root2",
            sub_agents=[
                FakeAgent(name="Jornada", key="jornada_telas", text="j\n```mermaid\nflowchart TD\nA-->B\n```"),
                EspelhoMiroAgent(name="A29bEspelhoMiro"),
                EspelhoMiroAgent(name="A29bEspelhoMiroRetrabalho"),
            ],
        )
        _, state = asyncio.run(_run(root))
    finally:
        _mc.SessaoMiro = original

    assert [c[0] for c in chamadas] == ["board_create", "canvas_create_from_svg", "canvas_update_from_svg"], chamadas
    # O id que o servidor devolveu na criação volta no update: é o que evita a duplicata.
    assert 'data-miro-id="770"' in chamadas[2][1]["svg"]
    assert chamadas[2][1]["miro_url"] == "https://miro.com/app/board/uXjTESTE=/"
    print("   ✓ miro: Mermaid escapado, board reusado entre rodadas, ids de widget preservados")


def test_miro_indisponivel_nao_derruba_a_esteira():
    """Integração fora do ar vira folha com a nota, nunca bloqueio nem artefato ausente."""
    import httpx

    from agents.checkers import EspelhoMiroAgent
    from tools.miro_cliente import folha_de_indisponibilidade, motivo_de_indisponibilidade

    resposta = httpx.Response(401, request=httpx.Request("POST", "https://mcp.miro.com/"))
    erro = httpx.HTTPStatusError("401", request=resposta.request, response=resposta)
    assert "reconecte" in motivo_de_indisponibilidade(erro)
    assert "limite de uso" in motivo_de_indisponibilidade(
        httpx.HTTPStatusError("429", request=resposta.request, response=httpx.Response(429, request=resposta.request))
    )
    assert "tempo esgotado" in motivo_de_indisponibilidade(httpx.TimeoutException("t"))

    folha = folha_de_indisponibilidade("sem conexão", "missão x")
    assert "MIRO: indisponível — sem conexão" in folha
    assert "não é um achado de QA" in folha

    def _explode(*_a, **_kw):
        raise erro

    import tools.miro_cliente as _mc

    original = _mc.SessaoMiro
    try:
        _mc.SessaoMiro = _explode
        root = SequentialAgent(
            name="Root",
            sub_agents=[
                FakeAgent(name="Jornada", key="jornada_telas", text="j\n```mermaid\nflowchart TD\nA-->B\n```"),
                EspelhoMiroAgent(name="A29bEspelhoMiro"),
            ],
        )
        _, state = asyncio.run(_run(root))
    finally:
        _mc.SessaoMiro = original

    # A folha SAI mesmo na falha: chave vazia em ARTIFACT_FILES vira "ausente" no diagnóstico.
    assert "MIRO: indisponível" in state["miro_links"]
    assert "design_status" not in state and "pipeline_bloqueado" not in state
    print("   ✓ miro: falha vira folha de indisponibilidade, sem bloquear a esteira")


def test_desembrulhar_cerca_do_documento():
    """O PRD vem dentro de ```markdown; salvo assim, o .md abre como bloco de código.

    O agente embrulha o documento inteiro para marcar onde ele começa e termina. Sem
    desembrulhar, o front matter do PRD deixa de ser front matter (visto em 2026-09-17:
    PRD de 79 KB inteiro dentro de uma cerca).
    """
    from pipeline.artifacts import desembrulhar_cerca

    # invólucro real, com blocos de código legítimos dentro
    doc = "```markdown\n---\nprd_id: X\n---\n# T\n\n```json\n{\"a\": 1}\n```\n\nfim\n```"
    limpo = desembrulhar_cerca(doc)
    assert limpo.startswith("---\nprd_id: X") and limpo.endswith("fim")
    assert limpo.count("```") == 2, "comeu os blocos internos"

    # o que NÃO pode ser tocado
    assert desembrulhar_cerca("# Documento normal\ntexto") == "# Documento normal\ntexto"
    sql = "```sql\nSELECT 1;\n```"
    assert desembrulhar_cerca(sql) == sql, "um arquivo que É um bloco de código"
    impar = "```markdown\n# A\n```\nsolto\n"
    assert desembrulhar_cerca(impar) == impar, "cerca desbalanceada é ambígua"
    assert desembrulhar_cerca(None) is None and desembrulhar_cerca("") == ""
    print("   ✓ cerca externa do documento removida; blocos internos, sql e casos ambíguos intactos")


def test_one_pager_pedagogico_em_docx():
    """O documento de validação humana sai também em .docx — o time que o aprova não lê Markdown."""
    import tempfile

    from tools.docx_export import markdown_para_docx

    md = (
        "# O Detetive da Legenda\n\n"
        "**Para o 2º ano** · **50 minutos**\n\n"
        "## Em uma frase\n"
        "A criança descobre que a legenda muda o que a foto **parece** dizer.\n\n"
        "## O que você faz\n"
        "- Antes: escolhe o tema\n"
        "- Durante: para a turma para conversar\n\n"
        "## O que precisamos que você aprove\n"
        "1. A conversa final fecha a descoberta com crianças de sete anos?\n"
        "2. O tempo de cada etapa cabe numa aula?\n\n"
        "| Etapa | O que acontece |\n|---|---|\n| Começo | A criança vê a foto |\n| Fim | Ela escolhe a legenda |\n\n"
        "---\n```json\n{\"agente\": \"one-pager-pedagogico\", \"status\": \"concluido\"}\n```\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        destino = Path(tmp) / "one-pager-pedagogico.docx"
        assert markdown_para_docx(md, destino, "Missão") == destino and destino.exists()

        from docx import Document

        doc = Document(str(destino))
        titulos = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
        texto = "\n".join(p.text for p in doc.paragraphs)
        # O nome da missão abre o documento na capa da marca; as seções seguem como
        # `Heading`, que é o que dá navegação no Word e sumário no Google Docs.
        capa = doc.tables[0].cell(0, 0).text
        assert "O Detetive da Legenda" in capa and "ONE-PAGER" in capa.upper()
        assert "O que precisamos que você aprove" in titulos and "Em uma frase" in titulos
        assert len(doc.tables) == 2 and doc.tables[1].cell(0, 0).text == "Etapa"
        assert [p.text for p in doc.paragraphs if p.style.name == "List Number"]
        assert [p.text for p in doc.paragraphs if p.style.name == "List Bullet"]
        # o envelope de roteamento é da esteira, não do leitor
        assert "one-pager-pedagogico" not in texto and "```" not in texto
        # negrito preservado, marcação não
        assert "**" not in texto and "parece" in texto

    # a mensagem de pulo não vira documento
    from pipeline.artifacts import e_mensagem_de_pulo

    assert e_mensagem_de_pulo("⏭️ `A49OnePagerPedagogico` não executado — pipeline bloqueado (x).")
    print("   ✓ one-pager pedagógico: .docx com títulos, listas e tabela; envelope e marcação fora do documento")


def test_one_pagers_com_identidade_visual():
    """Os dois one-pagers saem em `.docx` e `.html` com a marca — são eles que circulam fora do time."""
    import tempfile
    import zipfile

    from pipeline.artifacts import exportar_one_pagers
    from tools import marca

    estado = {
        "one_pager": "# One-pager — Missão Ilha\n\n## 0. Identificação\n* **Slug:** `exp03ilha`\n",
        "one_pager_resumido": (
            "# MISSÃO DIGITAL UNOORIA · 3º ANO EF\n\n## Detetives da Ilha\n\n"
            "> **Descoberta central:** Eu escolhi a fonte antes de saber o peso da escolha.\n\n"
            "| Campo | Valor |\n|---|---|\n| Ambiente simulado | YouTube (unitube) |\n"
        ),
        "one_pager_pedagogico": (
            "# Detetives da Ilha\n\n"
            "> **O que pedimos a você:** aprovar ou recusar.\n\n"
            "## As telas\n- Protótipo: [abrir](design/08-prototipo.html)\n"
        ),
    }
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        gerados = exportar_one_pagers(estado, run_dir, "exp03ilha")
        nomes = sorted(p.relative_to(run_dir).as_posix() for p in gerados)
        assert nomes == [
            "one-pager-pedagogico.docx",
            "one-pager-pedagogico.html",
            "produto/00-one-pager.docx",
            "produto/00-one-pager.html",
            "produto/00d-one-pager-resumido.docx",
            "produto/00d-one-pager-resumido.html",
        ]

        # O `.html` abre sozinho depois de baixado: logotipo embutido, nada em disco ao lado.
        pagina = (run_dir / "one-pager-pedagogico.html").read_text(encoding="utf-8")
        assert f"#{marca.NAVY}" in pagina and "data:image/png;base64," in pagina
        assert "Detetives da Ilha" in pagina and 'href="design/08-prototipo.html"' in pagina
        assert "<blockquote>" in pagina  # o pedido de aprovação abre o documento

        # O `.docx` carrega a marca: fundo navy na capa, Montserrat nos títulos, link clicável.
        with zipfile.ZipFile(run_dir / "one-pager-pedagogico.docx") as z:
            documento = z.read("word/document.xml").decode()
            assert f'w:fill="{marca.NAVY}"' in documento and "<w:hyperlink" in documento
            assert marca.FONTE_CORPO in z.read("word/styles.xml").decode()
            assert any(n.startswith("word/media/") for n in z.namelist())

    # Sem o documento, nada é escrito: a esteira bloqueada não produz capa de missão nenhuma.
    with tempfile.TemporaryDirectory() as tmp:
        vazio = exportar_one_pagers(
            {"one_pager_pedagogico": "⏭️ `A49OnePagerPedagogico` não executado — pipeline bloqueado (x)."},
            Path(tmp),
            "exp03ilha",
        )
        assert vazio == [] and not list(Path(tmp).iterdir())
    print("   ✓ one-pagers de produto, resumido e pedagógico: .docx e .html com a identidade visual da Unooria")


def test_one_pager_resumido_no_formato_do_time_de_produto():
    """O resumido tem a forma do documento que o time de produto escrevia à mão: caixas e tabelas.

    Três caixas (descoberta, diferenciação, takeaway) e três tabelas (ficha, etapas, marcadores)
    é o mínimo que o formato exige — se o exportador perder qualquer uma, o `.docx` que o time
    lê deixa de ser o formato deles.
    """
    import tempfile

    import docx

    from pipeline.artifacts import exportar_one_pagers

    documento = (
        "# MISSÃO DIGITAL UNOORIA · 6º ANO EF\n\n"
        "One-pager para avaliação pedagógica — v1 (primeira versão gerada)\n\n"
        "## O algoritmo que me formou\n\n"
        "> **Descoberta central:** Eu só segui 1 conta e isso decidiu quase tudo que eu vi depois.\n\n"
        "| Campo | Valor |\n|---|---|\n| Ambiente simulado | Instagram (instanooria) |\n| Duração | 2 aulas de 50 min |\n\n"
        "## 1. A ideia\n\nO professor libera o início.\n\n"
        "## 2. Componente curricular\n\n> **Diferenciação de mecanismo frente a \"A Seleção\":** cardinalidade 1, não 3.\n\n"
        "## 4. As 6 etapas da missão\n\n| # | Etapa | Quem conduz | O que o estudante vive |\n|---|---|---|---|\n"
        "| 1 | Desafiar | Léo | Recebe a DM. |\n| 2 | Navegar | Estudante | Segue 1 conta. |\n\n"
        "## 6. Contrato de evidência por habilidade (ternário)\n\n"
        "| Marcador | Critério | Status |\n|---|---|---|\n| Presente | Nomeia o risco | Atingiu |\n"
        "| Genérico | Risco genérico | Em processo |\n| Ausente | Nenhum risco | Não atingiu |\n\n"
        "## 7. O takeaway da missão\n\n> O algoritmo aprende com suas interações.\n\n"
        "---\n\n```json\n{\"agente\": \"one-pager-resumido\", \"status\": \"concluido\"}\n```\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        gerados = exportar_one_pagers({"one_pager_resumido": documento}, run_dir, "exp06ef1b")
        assert sorted(p.name for p in gerados) == ["00d-one-pager-resumido.docx", "00d-one-pager-resumido.html"]

        pagina = (run_dir / "produto/00d-one-pager-resumido.html").read_text(encoding="utf-8")
        assert pagina.count("<blockquote>") == 3, "as três caixas do formato viram blockquote"
        assert pagina.count("<table>") == 3, "ficha, etapas e marcadores viram tabela"
        assert "One-pager resumido" in pagina and "avaliação pedagógica" in pagina

        doc = docx.Document(str(run_dir / "produto/00d-one-pager-resumido.docx"))
        assert len(doc.tables) >= 4  # capa + ficha + etapas + marcadores
        textos = "\n".join(p.text for p in doc.paragraphs)
        assert "Descoberta central" in textos and "takeaway" in textos.lower()
        assert '"agente"' not in textos, "o envelope não vai para o documento que o time lê"
    print("   ✓ one-pager resumido: três caixas e três tabelas sobrevivem ao .docx e ao .html")


# Trechos literais do one-pager gerado para "O algoritmo que me formou" (6º EF), que passou pelo
# gate estrutural com estes erros. É o corpus de regressão do lint: se ele deixar de pegar um
# destes, o erro volta a nascer em Produto e a ser descoberto no Dev.
ONE_PAGER_COM_ERROS_CONHECIDOS = """# One-pager — O algoritmo que me formou v1

## 0. Identificação
* **Ano/série:** ["6EF"]
* **Ambiente simulado:** Instagram (seção do DS: instanooria)

## 1. Descoberta central
"Eu só segui 1 conta — e isso decidiu, sem eu saber, quase tudo que eu ia ver depois."

## 2. Currículo
### Habilidades de Computação Complementares
* EF06CO07 — Mundo Digital: Entender o processo de transmissão de dados, como a informação é quebrada em pedaços.
  * Aplicação na missão: Serve de base para a compreensão técnica de como as requisições de feed trafegam.
* EF06CO09 — Cultura Digital: Apresentar conduta e linguagem apropriadas ao se comunicar em ambiente digital.
### Descritor SAEB (Língua Portuguesa — 9º ano / EFII)
* D14: Distinguir um fato da opinião relativa a esse fato.

## 4. As 6 etapas — mecanismo, não intenção
* O feed é liberado em 3 blocos de exatamente 3 posts (9 de um banco de 12).

## 7. Caminhos degenerados
* Após 60 segundos de inatividade, uma pulsação visual suave destaca os 3 botões "Seguir".
* O sistema exige um tempo mínimo de permanência técnica de 4 segundos por bloco.
* Se o estudante digitar menos de 20 caracteres por campo, o botão exibe aviso.

## 8. Estados de falha
* O estado da conta seguida e as curtidas são retidos em localStorage. O app tenta reconexão a cada 5 segundos.

## 16. Requisitos técnicos e escopo
* Motor de distribuição do feed em 3 blocos rígidos controlados por WebSocket via dashboard docente.
* Sincronização: WebSocket com protocolo de fallback para polling HTTP a cada 3 segundos.
* Estado Local: Cache de contingência em IndexedDB no navegador.
* Assets: WebP (peso máximo de 150 KB por imagem de post).

## 17. Hipóteses de validação
* H1: nada aqui.
"""


def test_lint_do_one_pager_pega_os_erros_conhecidos():
    """Os quatro erros que o gate deixou passar viram achado antes de o gate ler."""
    from tools.contrato_produto import relatorio_markdown, validar_one_pager

    r = validar_one_pager(ONE_PAGER_COM_ERROS_CONHECIDOS, nucleo="3 blocos de exatamente 3 posts", briefing="")
    por_codigo = {a["codigo"]: a for a in r["achados"]}

    assert r["status"] == "bloqueado"
    assert por_codigo["websocket"]["severidade"] == "bloqueio" and "16" in por_codigo["websocket"]["resumo"]
    assert "8, 16" in por_codigo["estado-cliente"]["resumo"]
    assert "6º" in por_codigo["saeb-fora-do-ano"]["resumo"]
    numeros = por_codigo["numero-sem-origem"]["resumo"]
    for esperado in ("60 segundos", "4 segundos", "20 caracteres", "5 segundos", "3 segundos", "150 kb"):
        assert esperado in numeros, f"faltou {esperado} na lista de números sem origem"
    assert "EF06CO07" in por_codigo["codigo-fora-do-eixo"]["resumo"]
    assert "EF06CO09" not in por_codigo["codigo-fora-do-eixo"]["resumo"]  # Cultura Digital não é sinal

    relatorio = relatorio_markdown(r, "exp06ef1b")
    envelope = extrair_envelope(relatorio)
    assert envelope["status"] == "bloqueado" and envelope["agente"] == "contrato-produto"
    assert all(a["criterio"] for a in envelope["achados"])  # cada achado diz em que critério o gate aplica

    # Número que tem origem no núcleo ou no briefing deixa de ser achado; marcador também.
    r2 = validar_one_pager(
        ONE_PAGER_COM_ERROS_CONHECIDOS.replace("de 4 segundos por bloco", "de 4 segundos por bloco [PARÂMETRO — a definir por produto: tempo mínimo]"),
        nucleo="pulsação após 60 segundos",
        briefing="mínimo de 20 caracteres por campo",
    )
    numeros2 = {a["codigo"]: a for a in r2["achados"]}["numero-sem-origem"]["resumo"]
    for removido in ("60 segundos", "4 segundos", "20 caracteres"):
        assert removido not in numeros2

    # Menção proibitiva não é uso: o one-pager que cita WebSocket para descartá-lo passa limpo.
    limpo = validar_one_pager(
        "## 0. Identificação\n* Ano/série: [\"5EF\"]\n\n## 2. Currículo\n* EF05CO09 — Cultura Digital.\n\n"
        "## 16. Requisitos técnicos e escopo\n* Sala sincronizada por polling HTTP em exp05ef1b_gates_turma; nunca WebSocket (ADR-93).\n"
    )
    assert limpo["status"] == "aprovado" and limpo["achados"] == []
    print("   ✓ lint do one-pager: WebSocket, estado de cliente, SAEB fora do ano e números sem origem viram achado antes do gate")


def test_bncc_reconhece_decisao_de_produto_pendente():
    """Sem código porque o time ainda precisa decidir não é 'código faltando' — é a decisão."""
    from tools.bncc import validar_spec

    spec = (
        "# Spec — O algoritmo que me formou v1\n\n## 0. Identificação de plataforma\n* Série(s): [\"6EF\"]\n\n"
        "## 11. Currículo\n[ABERTO — dono: produto: nenhuma habilidade de Cultura Digital do 6º ano descreve escolher uma conta "
        "e ver o feed afunilar; alternativas: migrar para o 8º ano · ancorar em EF69LP03]\n\n## 12. Decisões\n"
    )
    r = validar_spec(spec)
    codigos = [a["codigo"] for a in r["achados"]]
    assert r["status"] == "bloqueado"
    assert "decisao-produto" in codigos and "sem-codigo" not in codigos and "letramento" not in codigos
    print("   ✓ gate BNCC: decisão de produto pendente bloqueia com a mensagem certa, não como código faltando")


def test_schema_de_ferramenta_saneado():
    """Schema de servidor MCP chega quebrado e o modelo recusa a requisição inteira.

    O Stitch publica `$ref` para `$defs` que ele mesmo omite. O ADK repassa o schema
    de resposta ao Gemini como `response_json_schema`, e a requisição volta com
    `400 reference to undefined schema at properties.variantScreenInstance` — no
    agente que estava no ar quando a lista foi montada, que pode nem usar a ferramenta.
    """
    from mcp.types import Tool

    from tools.mcp_saneado import _sanear, remendar_entrada

    # referência órfã na ENTRADA é remendada, não removida: ali o schema é necessário
    entrada = {
        "type": "object",
        "properties": {"a": {"$ref": "#/$defs/Faltante"}, "b": {"$ref": "#/$defs/Existe"}},
        "$defs": {"Existe": {"type": "string"}},
    }
    remendada = remendar_entrada(entrada)
    assert sorted(remendada["$defs"]) == ["Existe", "Faltante"]
    assert sorted(entrada["$defs"]) == ["Existe"], "o schema original não pode ser mutado"
    assert remendar_entrada({"type": "object"}) == {"type": "object"}
    assert remendar_entrada(None) is None

    # schema de RESPOSTA é descartado: o modelo não precisa dele e é ele que quebra
    t = Tool(
        name="upload_design_md",
        description="d",
        inputSchema={"type": "object", "properties": {"p": {"$ref": "#/$defs/Orfa"}}},
        outputSchema={"type": "object", "properties": {"variantScreenInstance": {"$ref": "#/$defs/Sumida"}}},
    )
    mexidos = _sanear(t)
    assert t.outputSchema is None
    assert "Orfa" in (t.inputSchema.get("$defs") or {})
    assert len(mexidos) == 2

    # os dois toolsets da esteira usam a versão saneada
    from tools.mcp_saneado import McpToolsetSaneado

    for modulo in ("tools.stitch_mcp",):
        fonte = Path(modulo.replace(".", "/") + ".py").read_text(encoding="utf-8")
        assert "McpToolsetSaneado(" in fonte and "= McpToolset(" not in fonte, modulo
    assert issubclass(McpToolsetSaneado, __import__("google.adk.tools.mcp_tool.mcp_toolset", fromlist=["McpToolset"]).McpToolset)
    print("   ✓ schema saneado: resposta descartada, referência órfã remendada na entrada, nos dois toolsets")


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


# --------------------------------------------------------------------------- esteira que não aborta
def test_esteira_nao_aborta_e_emite_diagnostico():
    """Gate reprovado não pode custar os documentos: é deles que sai o diagnóstico.

    Antes, um 🔴 gravava `pipeline_bloqueado` e todo agente a jusante era pulado — não
    saía PRD, one-pager nem relatório, e não havia o que analisar. Este teste trava o
    comportamento novo: tudo é produzido, marcado, e o dossiê explica o que houve.
    """
    from agents.checkers import DiagnosticoAgent

    reprovado = 'x\n```json\n{"agente": "g", "status": "bloqueado", "achados": [{"id": "L1", "severidade": "bloqueio", "codigo": "1.4", "agente_responsavel": "gate-estrutural", "resumo": "sem tratamento para quem nao escolhe"}], "precisa_humano": true}\n```'
    root = SequentialAgent(
        name="Root",
        sub_agents=[
            FakeAgent(name="Gate", key="gate_estrutural_report", text=reprovado),
            EnvelopeGateAgent(
                name="Check", rotulo="Gate estrutural", report_key="gate_estrutural_report",
                status_key="gate_estrutural_status", block_pipeline_on_fail=True,
            ),
            FakeAgent(name="Spec", key="spec_missao", text="# Spec\nSlug: exp05ef2b\n", before_agent_callback=marcar_heranca),
            FakeAgent(name="Prd", key="prd_final", text="# PRD", before_agent_callback=marcar_heranca),
            FakeAgent(name="OnePager", key="one_pager_pedagogico", text="# One-pager", before_agent_callback=marcar_heranca),
            DiagnosticoAgent(name="A50Diagnostico", description="d"),
        ],
    )
    _, state = asyncio.run(_run(root))

    # 1. os documentos existem, apesar do gate reprovado
    for chave in ("spec_missao", "prd_final", "one_pager_pedagogico"):
        assert state.get(chave), f"{chave} deveria ter sido produzido mesmo com gate reprovado"

    # 2. quem rodou depois da reprovação ficou marcado
    assert set(state[KEY_AGENTES_DEGRADADOS]) == {"Spec", "Prd", "OnePager"}
    assert "Gate estrutural" in state[KEY_HERANCA]

    # 3. o diagnóstico saiu e é acionável
    dossie = state["diagnostico_execucao"]
    assert "# Diagnóstico da execução" in dossie
    assert "sem tratamento para quem nao escolhe" in dossie, "o achado precisa aparecer no dossiê"
    assert "gate-estrutural" in dossie, "o dono do conserto precisa aparecer"
    assert "Por onde começar" in dossie
    assert state["diagnostico_status"] == "bloqueado"
    assert state["diagnostico_status_envelope"]["precisa_humano"] is True
    print("   ✓ gate reprovado: documentos saem, herança marcada, diagnóstico acionável emitido")


def test_status_desconhecido_nao_vira_bloqueio_silencioso():
    """Valor de envelope fora do vocabulário tem de ser visível, não virar 🔴 sem aviso.

    Foi assim que `aprovado_com_ressalvas` quase derrubou a esteira: os prompts passaram a
    emiti-lo, `inferir_status` não o conhecia, e a decisão caía numa heurística de texto que
    testa os tokens de bloqueio primeiro.
    """
    from agents.callbacks import inferir_status

    for valor in ("aprovado", "aprovado_com_ressalvas", "apto_com_ressalvas", "amarelo"):
        assert inferir_status("", {"status": valor}) == "aprovado", f"{valor} deveria contar como aprovado"
    assert inferir_status("", {"status": "bloqueado"}) == "bloqueado"

    # Todo `status` citado nos prompts precisa ser reconhecido pelo código.
    import re as _re

    from prompts.loader import get_prompt_raw, list_prompt_files

    vocabulario = set()
    for area, arquivos in list_prompt_files().items():
        for nome in arquivos:
            for linha in get_prompt_raw(f"{area}/{nome}").splitlines():
                # Só o `status` do envelope raiz: é o que `inferir_status` lê. Objetos
                # aninhados têm vocabulário próprio (ex.: `respec.status: aceito|negado`).
                if '"agente"' not in linha:
                    continue
                depois = linha.split('"agente"', 1)[1]
                m = _re.search(r'"status":\s*((?:"[a-z_]+"\s*\|?\s*)+)', depois)
                if m:
                    vocabulario |= {v.strip().strip('"') for v in m.group(1).split("|") if v.strip()}
    ignorados = {"concluido", "devolvido", "nao_aplicavel", "parcial", "segue", "segue_com_pendencias",
                 "dormente", "existente", "novo", "aguarda_gate", "passa", "nao_passa", "amarelo"}
    for valor in sorted(vocabulario - ignorados):
        assert inferir_status("", {"status": valor}) in ("aprovado", "bloqueado"), (
            f"prompt emite status '{valor}' que inferir_status não reconhece — "
            "a decisão cairia na heurística de texto"
        )
    print(f"   ✓ vocabulário de status dos prompts ({len(vocabulario)} valores) reconhecido pelo código")


def test_despacho_reexecuta_so_quem_tem_ticket():
    """O QA endereça cada ticket a um dono; só esses donos rodam de novo — mais o pósfixo.

    Reexecutar a etapa inteira para consertar uma string custaria todas as chamadas de
    ferramenta outra vez. E a correção de quem emite dois documentos numa resposta só
    (D0, D9) precisa do split logo atrás, senão fica presa no relatório.
    """
    from agents.checkers import DespachoTicketsAgent

    envelope_qa = {
        "agente": "qa-entregaveis",
        "status": "bloqueado",
        "achados": [
            {"id": "T1", "severidade": "bloqueio", "codigo": "D4", "agente_responsavel": "copy-ptbr-revisao", "resumo": "texto longo demais"},
            {"id": "T2", "severidade": "bloqueio", "codigo": "D8", "agente_responsavel": "ambiente-simulado", "resumo": "verbo sem rotulo literal"},
            {"id": "T3", "severidade": "bloqueio", "codigo": "D2", "agente_responsavel": "gate-estrutural", "resumo": "mecanica da missao"},
            {"id": "T4", "severidade": "atencao", "codigo": "D1", "agente_responsavel": "jornada", "resumo": "so atencao, nao dispara"},
        ],
    }
    qa = "QA\n```json\n" + json.dumps(envelope_qa, ensure_ascii=False) + "\n```"
    despacho = DespachoTicketsAgent(
        name="Despacho",
        rotulo="Retrabalho",
        report_key="qa_entregaveis_report",
        mapa={
            "copy-ptbr-revisao": ["CopyRet"],
            "ambiente-simulado": ["AmbienteRet", "AmbienteSplitRet"],
            "jornada": ["JornadaRet"],
        },
        ordem=["ambiente-simulado", "jornada", "copy-ptbr-revisao"],
        externos=["gate-estrutural"],
        posfixo=["PrototipoRet"],
        sub_agents=[
            FakeAgent(name="AmbienteRet", key="ambiente_simulado", text="amb", marker_key="n_amb"),
            FakeAgent(name="AmbienteSplitRet", key="spec_missao", text="spec com bloco 14", marker_key="n_split"),
            FakeAgent(name="JornadaRet", key="jornada_telas", text="jor", marker_key="n_jornada"),
            FakeAgent(name="CopyRet", key="copy_strings_revisada", text="copy", marker_key="n_copy"),
            FakeAgent(name="PrototipoRet", key="prototipo_html", text="html", marker_key="n_proto"),
        ],
    )
    root = SequentialAgent(
        name="Root",
        sub_agents=[FakeAgent(name="Qa", key="qa_entregaveis_report", text=qa), despacho],
    )
    _, state = asyncio.run(_run(root))

    # os dois donos de bloqueio rodaram; o split do ambiente veio junto
    assert state.get("n_amb") == 1 and state.get("n_split") == 1, "cadeia do ambiente incompleta"
    assert state.get("n_copy") == 1
    # severidade 'atencao' não dispara retrabalho
    assert state.get("n_jornada") is None, "ticket de atenção não deve reexecutar ninguém"
    # o pósfixo roda porque houve retrabalho
    assert state.get("n_proto") == 1, "o protótipo precisa ser refeito quando algo de que ele deriva mudou"
    print("   ✓ despacho seletivo: cadeia completa, atenção não dispara, pósfixo roda, externo não")


def test_despacho_nao_roda_quando_aprovado():
    from agents.checkers import DespachoTicketsAgent

    qa = "QA\n```json\n" + json.dumps({"agente": "qa-entregaveis", "status": "aprovado", "achados": []}) + "\n```"
    despacho = DespachoTicketsAgent(
        name="Despacho", rotulo="Retrabalho", report_key="qa_entregaveis_report",
        mapa={"caa": ["CaaRet"]}, ordem=["caa"], posfixo=["ProtoRet"],
        sub_agents=[
            FakeAgent(name="CaaRet", key="camada_caa", text="caa", marker_key="n_caa"),
            FakeAgent(name="ProtoRet", key="prototipo_html", text="h", marker_key="n_proto"),
        ],
    )
    root = SequentialAgent(name="Root", sub_agents=[FakeAgent(name="Qa", key="qa_entregaveis_report", text=qa), despacho])
    _, state = asyncio.run(_run(root))
    assert state.get("n_caa") is None and state.get("n_proto") is None
    print("   ✓ QA aprovado: nenhum retrabalho, nem o pósfixo")


def test_orcamento_global_freia_o_retrabalho():
    """Os tetos por loop somam; o orçamento global é o freio da conta total."""
    from agents.checkers import KEY_REEXECUCOES, DespachoTicketsAgent

    envelope = {
        "agente": "qa-entregaveis", "status": "bloqueado",
        "achados": [{"id": "T1", "severidade": "bloqueio", "codigo": "D1", "agente_responsavel": "caa", "resumo": "x"}],
    }
    qa = "QA\n```json\n" + json.dumps(envelope) + "\n```"
    despacho = DespachoTicketsAgent(
        name="Despacho", rotulo="Retrabalho", report_key="qa_entregaveis_report",
        mapa={"caa": ["CaaRet"]}, ordem=["caa"],
        sub_agents=[FakeAgent(name="CaaRet", key="camada_caa", text="caa", marker_key="n_caa")],
    )
    # estado já no limite do orçamento
    gasto = FakeAgent(name="Gasto", key="_tmp", text="x")
    gasto.extra_delta = {KEY_REEXECUCOES: get_settings().orcamento_reexecucoes}
    root = SequentialAgent(
        name="Root",
        sub_agents=[FakeAgent(name="Qa", key="qa_entregaveis_report", text=qa), gasto, despacho],
    )
    _, state = asyncio.run(_run(root))
    assert state.get("n_caa") is None, "com o orçamento estourado, nenhum agente pode ser reexecutado"
    print("   ✓ orçamento global esgotado: retrabalho vira pendência humana, esteira segue")


def test_loop_da_spec_corrige_na_segunda_rodada():
    """O gate determinístico reprova, o autor reescreve, o gate confere de novo — sem humano.

    É o padrão que a Onda 2 generalizou: quem julga não conserta, quem conserta não julga,
    e quem decide repetir é o orquestrador — não uma instrução em prosa dentro do prompt.
    """
    from agents.checkers import BnccCheckAgent, SaidaDeLoopAgent

    class SpecQueAprende(BaseAgent):
        """Primeira passada com código inexistente; na segunda, lê o relatório e corrige."""

        @override
        async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
            state = ctx.session.state
            corrigindo = bool(str(state.get("bncc_report") or ""))
            codigo = "EF02CO05" if corrigindo else "EF02CO99"
            spec = (
                "# Spec — exp02ef1b\n\n## 0. Identificação de plataforma\n"
                "- `id: exp02ef1b`\n- `series: [\"2EF\"]`\n\n"
                f"## 11. Currículo\n| {codigo} | Cultura Digital | momento em tela |\n"
            )
            yield Event(
                invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                content=types.Content(role="model", parts=[types.Part(text="spec")]),
                actions=EventActions(state_delta={
                    "spec_missao": spec,
                    "n_spec": int(state.get("n_spec", 0) or 0) + 1,
                }),
            )

    loop = LoopAgent(
        name="SpecLoop",
        max_iterations=2,
        sub_agents=[
            SpecQueAprende(name="Spec", description="spec"),
            BnccCheckAgent(name="A14BnccCheck", description="bncc", estrito=True),
            SaidaDeLoopAgent(
                name="A16SpecCheck", description="saida", rotulo="Spec",
                status_keys=["bncc_status"], rodada_key="spec_rodada", max_rounds=2,
            ),
        ],
    )
    _, state = asyncio.run(_run(SequentialAgent(name="Root", sub_agents=[loop])))

    assert state["n_spec"] == 2, "a spec tinha de ser reescrita uma vez"
    assert state["bncc_status"] == "aprovado", "a segunda versão tinha de passar no gate"
    assert state["spec_rodada"] == 2
    assert not state.get(KEY_PIPELINE_BLOQUEADO), "corrigido dentro do loop não deixa resíduo de bloqueio"
    print("   ✓ loop da spec: gate reprova, autor corrige com o relatório, gate aprova na 2ª rodada")


def test_id_da_experiencia_carrega_ano_e_bimestre():
    """`exp05ef3b` = 5º ano do Fundamental, 3º bimestre — e `series`/`unidade` têm de concordar."""
    from tools.rastro import decompor_id, validar_manifesto

    assert decompor_id("exp01ef1b") == {"serie": "1EF", "unidade": 1}
    assert decompor_id("exp05ef3b") == {"serie": "5EF", "unidade": 3}
    assert decompor_id("exp02em2b") == {"serie": "2EM", "unidade": 2}
    assert decompor_id("exp04em1b") is None, "o Ensino Médio tem três anos, não quatro"
    assert decompor_id("exp05ef5b") is None, "o ano letivo tem quatro bimestres"
    assert decompor_id("exp-06-rastro-do-boato") is None

    def ficha(idm, series, unidade):
        return (
            "# Spec\n\n## 0. Identificação de plataforma\n"
            f"- `id: {idm}`\n- `produto: entre-redes`\n- `series: [\"{series}\"]`\n"
            f"- `unidade: {unidade}`\n- `publico: estudante`\n- `viewport: 375x812`\n"
            "- `permissoes: [forms]`\n- `capabilities: [telemetria]`\n"
            "- `secao_ds: unitube`\n- `liberacao: por-turma`\n"
        )

    ok = validar_manifesto(ficha("exp05ef3b", "5EF", 3))
    assert not [a for a in ok["achados"] if a["campo"] in ("id", "series", "unidade")], ok["achados"]

    serie_errada = validar_manifesto(ficha("exp05ef3b", "7EF", 3))
    assert any(a["campo"] == "series" for a in serie_errada["achados"]), "id e series divergentes têm de travar"

    bimestre_errado = validar_manifesto(ficha("exp05ef3b", "5EF", 1))
    assert any(a["campo"] == "unidade" for a in bimestre_errado["achados"]), "id e unidade divergentes têm de travar"

    formato_velho = validar_manifesto(ficha("exp-77-teste", "5EF", 3))
    assert any(a["campo"] == "id" for a in formato_velho["achados"]), "missão com ano e bimestre não usa o formato antigo"
    print("   ✓ id carrega ano e bimestre; series e unidade são conferidas contra ele")


def test_ato_humano_nao_bloqueia_a_esteira():
    """Homologar, nomear autoria e licenciar não são lacunas de construção.

    Nenhum agente produz esses atos, então tratá-los como bloqueio reprovava a missão por algo
    que nenhuma rodada de correção poderia resolver — e empurrava para o dono errado, porque o
    marcador caía na etapa padrão do gate que o leu.
    """
    from tools.rastro import classificar_dono, varrer_lacunas

    for texto in ("responsável de produto: nomear autor e revisor",
                  "responsável editorial Entre Redes",
                  "homologação jurídica da licença de uso do acervo"):
        assert classificar_dono(texto, "dev") == "humano", texto

    estado = {
        "prd_final": (
            "[NEEDS CLARIFICATION: Homologação nominal dos autores do gabarito] "
            "e [verificar no repositório: nome da tabela] "
            "e [ABERTO — dono: handoff-dev: contrato da rota de progresso]"
        )
    }
    r = varrer_lacunas([{"chave": "prd_final", "rotulo": "PRD", "etapa_padrao": "dev"}], estado)
    severidades = {a["etapa"]: a["severidade"] for a in r["achados"]}
    assert severidades["humano"] == "decisao_humana", "ato humano é decisão, não impedimento"
    # `[verificar no repositório]` é pendência de PLATAFORMA desde 23/09/2026: os agentes não
    # têm o monorepo por desenho (só as cópias sincronizadas) e os prompts 34 e 47 mandam
    # escrever o marcador. Tratá-lo como lacuna de dev era punir o agente por obedecer.
    assert severidades["plataforma"] == "atencao", "marcador de repositório é pendência de plataforma"
    assert severidades["dev"] == "bloqueio", "lacuna real de dev continua bloqueando"
    print("   ✓ ato humano vira decisão; marcador de repositório é plataforma; lacuna de dev bloqueia")


def test_prd_inconsistente_consigo_mesmo_e_barrado():
    """PRD sem lacuna nenhuma ainda pode ser inútil para quem codifica.

    Dois prefixos de tabela, um requisito P0 sem teste, um evento lido no lugar errado — nada
    disso é marcador de lacuna, e todos fazem o agente de codificação escolher um caminho ao
    acaso. O gabarito já exigia essas regras em prosa; faltava alguém conferir.
    """
    from tools.rastro import validar_prd

    limpo = (
        "| RF-001 | P0 | o estudante escolhe |\n"
        "Matriz: RF-001 coberto por `teste/rf001.spec.ts`.\n"
        "T-001 implementa RF-001.\n"
        "Tabela `exp02ef1b_sessoes`.\n"
        "| EVT-001 | interacted | onde é lido: `exp02ef1b_sessoes` + painel |\n"
        "Diretório `apps/experiencias/exp02ef1b/`.\n"
        # Desde o corte A2 (23/09/2026) o plano de implementação também é conferido aqui:
        # eram os TEC-07/08/09/10 que a banca cobrava do handoff, uma etapa antes de o PRD
        # existir. PRD "limpo" passou a incluí-los.
        "Porta em `apps/hub/lib/experiencias-dev.ts` (`strictPort`, `CORS_ORIGINS`).\n"
        "Versão em `experiencia.json`, `package.json` e `EXP_VERSION` (`versao.test.ts`).\n"
        "Walkthrough: `node scripts/e2e/rodar.mjs estudante`. Invariantes em `invariantes.ts`.\n"
    )
    assert validar_prd(limpo)["status"] == "aprovado", validar_prd(limpo)["achados"]

    quebrado = limpo + "Migration cria `exp_02ef1b_gates_turma`.\n"
    r = validar_prd(quebrado)
    assert r["status"] == "bloqueado"
    assert any(a["codigo"] == "prefixo-tabela" for a in r["achados"])
    print("   ✓ consistência interna do PRD: prefixo híbrido é barrado antes de chegar em quem codifica")


def test_achado_de_evento_nomeia_o_evento_e_mostra_a_linha():
    """O relatório precisa dizer QUAL evento está errado, não só que há um errado.

    Numa tabela larga o identificador do evento cai no meio da linha: recortar o começo
    escondia justamente a evidência de quem ia corrigir, e o achado chegava ao humano sem
    o dado que o torna acionável.
    """
    from tools.rastro import validar_prd

    linha = (
        "| **Autonomia de Enquadramento** | 45% hesita | ≥ 85% em < 90s | Piloto | "
        "`EVT-002` (`enquadrar:crop:foto`) | `telemetria_eventos` |\n"
    )
    achados = validar_prd(linha)["achados"]
    evento = [a for a in achados if a["codigo"] == "evento-sem-leitor"]
    assert evento, achados
    assert "EVT-002" in evento[0]["resumo"]
    assert "telemetria_eventos" in evento[0]["resumo"]
    print("   ✓ achado de telemetria nomeia o evento e carrega a linha inteira como evidência")


def test_prd_cita_experiencia_existente_sem_virar_caminho_divergente():
    """Regressão de 2026-09-22 (exp08ef2b): o PRD manda imitar `apps/experiencias/exp-08-manifesto-ia/`
    como exemplar canônico, e o gate lia isso como a missão declarando duas pastas."""
    from tools.rastro import validar_prd

    base = """---
prd_id: PRD-exp08ef2b
---
## 12. Estrutura
Bundle em `apps/experiencias/exp08ef2b/`.
Imitar o exemplar canônico: `apps/experiencias/exp-08-manifesto-ia/` e `apps/api/src/manifesto-ia/`.
Porta 5184 evita colisão com `exp-08-manifesto-ia` (5182) e `exp-04-o-que-a-foto-conta` (5183).
"""
    r = validar_prd(base)
    assert "caminho-divergente" not in {a["codigo"] for a in r["achados"]}, r["achados"]

    # mas a missão nova com duas pastas próprias continua sendo bloqueio: é o `exp-NN` vs `expNNefNb`
    duas = base + "\nO bundle também aparece como `apps/experiencias/exp-08-rota-invisivel/`.\n"
    achados = {a["codigo"]: a for a in validar_prd(duas)["achados"]}
    assert "caminho-divergente" in achados, achados
    assert achados["caminho-divergente"]["severidade"] == "bloqueio"
    print("   ✓ PRD cita experiência existente sem virar caminho divergente")


def test_prd_tem_ciclo_de_correcao():
    """O gate do PRD julgava sem poder devolver — era o único beco da esteira.

    Todo outro gate determinístico da esteira tem um ciclo que devolve o achado ao autor.
    O do PRD não tinha: detectava defeito de contrato no entregável final e seguia para o
    one-pager com o defeito intacto, deixando para o humano o que tem correção certa.
    """
    from agents.dev import DEV_METADATA, build_dev_stage

    nomes = {m["id"] for m in DEV_METADATA}
    assert {"A47PrdWriter", "A48PrdCheck", "A48PrdRodada"} <= nomes, sorted(nomes)

    def achatar(agentes):
        for a in agentes:
            yield a
            yield from achatar(getattr(a, "sub_agents", []) or [])

    loop = [a for a in achatar([build_dev_stage()]) if a.name == "PrdLoop"]
    assert loop, "PrdLoop não está montado na etapa de dev"
    dentro = {a.name for a in achatar(loop[0].sub_agents)}
    assert {"A47PrdWriter", "A48PrdCheck", "A48PrdRodada"} <= dentro, sorted(dentro)
    print("   ✓ redator do PRD e gate de consistência estão no mesmo loop, com saída por rodada")


def test_cobertura_por_intervalo_conta_como_rastro():
    """`RF-001..RF-014` cobre requisito tanto quanto listá-los um a um.

    Contar ocorrências do identificador acusava ausência de rastro onde o rastro existia — um PRD
    bem escrito cita o requisito na declaração e na matriz, e é a matriz que nomeia a tarefa. Pior:
    a mesma cegueira deixava passar a tarefa que engole a missão inteira, que é o defeito de
    verdade escondido atrás da notação.
    """
    from tools.rastro import validar_prd

    prd = (
        "| **RF-013** | Reentrada resiliente | P0 | DADO que recarregue, O SISTEMA DEVE restaurar |\n"
        "| `T-005` | Implementar serviço | RF-011, RF-012, RF-013 | src/api.ts |\n"
        "| `RF-013` | Reentrada resiliente | `T-005` | `test/reentrada.spec.ts` |\n"
    )
    assert not [a for a in validar_prd(prd)["achados"] if a["codigo"] == "rf-sem-rastro"]

    por_intervalo = prd.replace("RF-011, RF-012, RF-013", "RF-001..RF-014")
    achados = validar_prd(por_intervalo)["achados"]
    assert not [a for a in achados if a["codigo"] == "rf-sem-rastro"], achados
    nao_atomica = [a for a in achados if a["codigo"] == "tarefa-nao-atomica"]
    assert nao_atomica, achados
    assert nao_atomica[0]["severidade"] == "atencao"
    assert "14 requisitos" in nao_atomica[0]["resumo"]
    print("   ✓ intervalo conta como rastro, e a tarefa que cobre 14 requisitos vira ressalva")


def test_prompt_reusado_mantem_o_numero_canonico():
    """Um prompt lido por dois nós não pode herdar o rótulo do segundo.

    O revisor do one-pager (07) roda de novo como retrabalho dentro do loop de avaliações (10c).
    Indexar os metadados por arquivo mantendo a última ocorrência fazia o arquivo 07 aparecer
    rotulado "10c" no editor — no meio da lista e fora da ordem da esteira.
    """
    from pipeline.orchestrator import get_pipeline_agents_metadata

    metadata, reusos = {}, {}
    for m in get_pipeline_agents_metadata(active_only=False):
        arquivo = m.get("prompt_file")
        if not arquivo:
            continue
        if arquivo in metadata:
            reusos.setdefault(arquivo, []).append(m["name"])
        else:
            metadata[arquivo] = m

    revisor = metadata["produto/07_revisor_one_pager.md"]["name"]
    assert revisor.startswith("07"), revisor
    assert reusos["produto/07_revisor_one_pager.md"], "o reuso precisa ficar visível para quem edita"

    # o número do rótulo tem que crescer junto com o nome do arquivo, dentro de cada área
    import re

    from prompts import list_prompt_files

    for area, arquivos in list_prompt_files().items():
        numeros = []
        for f in sorted(arquivos):
            nome = metadata.get(f"{area}/{f}", {}).get("name", f)
            achado = re.match(r"\s*(\d+)", nome)
            numeros.append(int(achado.group(1)) if achado else 999)
        assert numeros == sorted(numeros), f"{area}: rótulos fora de ordem — {numeros}"
    print("   ✓ prompt reusado mantém o número canônico e a lista do editor sai em ordem")


# --------------------------------------------------------------------- catálogo de missões
def _ficha(**kw):
    base = {"sessao": "s1", "slug": "exp06ef1b", "nome": "N", "ano": "6EF", "bimestre": 1,
            "ambiente": "instanooria", "eixo": "algoritmos e bolhas de informação",
            "descoberta": "o feed esconde posts a partir das contas que eu sigo",
            "tipo_decisao": "seguir uma conta e comparar o feed depois", "porta_abstracao": "explicar",
            "habilidade_primaria": "EF06CO09", "status": "em criação", "gates": {}, "origem": "esteira"}
    base.update(kw)
    return base


def test_catalogo_semelhanca_separa_repetida_de_distinta():
    """O score recupera e ordena; quem reprova é o V5. Mas repetida tem de pontuar acima de distinta."""
    from tools import catalogo as cat

    igual = _ficha(sessao="s2", descoberta="o feed esconde posts por causa das contas que sigo")
    outra = _ficha(sessao="s3", ano="4EF", ambiente="unitube", eixo="desinformação e credibilidade",
                   descoberta="popularidade não é o mesmo que confiabilidade num vídeo",
                   tipo_decisao="escolher 3 de 10 vídeos pela credibilidade")
    s_igual, s_outra = cat.semelhanca(_ficha(), igual), cat.semelhanca(_ficha(), outra)
    assert s_igual >= cat.LIMIAR_PARECIDA, s_igual
    assert s_outra < 0.2, s_outra
    print(f"   ✓ catálogo: missão repetida {s_igual:.2f} × distinta {s_outra:.2f}")


def test_catalogo_vizinhas_filtra_por_ano_ambiente_e_eixo():
    from tools import catalogo as cat

    indice = {"versao": 1, "missoes": [
        _ficha(sessao="s2", slug="exp07ef1b", ano="7EF",
               descoberta="o feed muda conforme quem eu sigo, e ninguém me avisa"),  # ano vizinho
        _ficha(sessao="s3", slug="exp01ef1b", ano="1EF", ambiente="tiktooria",
               eixo="privacidade", descoberta="outra coisa completamente", tipo_decisao="x"),  # longe
        _ficha(sessao="s4", slug="exp09ef1b", ano="9EF", status="descartada"),  # descartada sai
    ]}
    achadas = cat.vizinhas(_ficha(), indice, n=5)
    slugs = [m["slug"] for m in achadas]
    assert "exp07ef1b" in slugs and "exp01ef1b" not in slugs and "exp09ef1b" not in slugs, slugs
    assert achadas[0]["semelhanca"] >= achadas[-1]["semelhanca"]
    # Reexecução: a mesma missão já registrada não pode aparecer como repetição de si mesma.
    com_ela_mesma = {"versao": 1, "missoes": [_ficha(sessao="outra-sessao")]}
    assert cat.vizinhas(_ficha(sessao=""), com_ela_mesma) == []
    print(f"   ✓ catálogo: vizinhas filtram por ano/ambiente/eixo e ignoram descartada ({slugs})")


def test_catalogo_registra_detecta_slug_colidido_e_preserva_status_humano():
    """O slug deriva de ano+bimestre, então duas missões do mesmo bimestre colidem — é achado, não erro."""
    import tempfile
    from pathlib import Path

    from tools import catalogo as cat

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        cat.registrar(_ficha(sessao="s1"), base=base)
        r = cat.registrar(_ficha(sessao="s2", descoberta="outra descoberta bem diferente daqui"), base=base)
        assert "slug-colidido" in [a["codigo"] for a in r["achados"]], r["achados"]
        assert r["total"] == 2

        promovido = cat.carregar(base=base)
        next(m for m in promovido["missoes"] if m["sessao"] == "s1")["status"] = "aprovada"
        cat.gravar(promovido, base=base)
        cat.registrar(_ficha(sessao="s1"), base=base)  # a esteira roda de novo sobre a mesma sessão
        final = next(m for m in cat.carregar(base=base)["missoes"] if m["sessao"] == "s1")
        assert final["status"] == "aprovada", final["status"]
    print("   ✓ catálogo: slug colidido vira achado e status promovido por pessoa vence o derivado")


def test_catalogo_lacuna_desarma_a_comparacao_e_tabela_vazia_avisa():
    from tools import catalogo as cat

    assert cat.tem_lacuna(_ficha(descoberta="[preencher do manifesto]"))
    assert cat.tem_lacuna(_ficha(tipo_decisao=""))
    assert not cat.tem_lacuna(_ficha())
    vazia = cat.tabela_markdown([])
    assert "|" not in vazia and "vazio" in vazia, vazia
    print("   ✓ catálogo: campo por preencher desarma a comparação; índice vazio avisa em vez de tabela oca")


def test_catalogo_ficha_le_slug_ano_ambiente_e_descoberta_do_estado():
    from tools import catalogo as cat

    state = {
        "spec_missao": "# Spec — O feed que me escolheu v1\n\n## 0. Identificação de plataforma\n"
                       "* Slug: `exp06ef1b` · Série(s): [\"6EF\"] · Seção do DS: `instanooria`\n\n"
                       "## 1. Descoberta central\n- **Frase-síntese da descoberta:** \"Eu segui uma conta e o feed mudou sozinho.\"\n"
                       "- Eixo temático: algoritmos de recomendação e bolhas\n\n"
                       "## 11. Currículo\n| `EF06CO09` | Cultura Digital | letramento digital |\n",
        "gate_final_status": "bloqueado",
        "pipeline_bloqueado": True,
    }
    f = cat.ficha_da_execucao(state, sessao="20260922-000000-exp06ef1b")
    assert f["slug"] == "exp06ef1b" and f["ano"] == "6EF" and f["bimestre"] == 1
    assert f["ambiente"] == "instanooria" and f["habilidade_primaria"] == "EF06CO09"
    assert f["descoberta"].startswith("Eu segui uma conta"), f["descoberta"]
    assert f["status"] == "bloqueada", "missão bloqueada entra no índice — senão a mesma ideia volta"
    print("   ✓ catálogo: ficha lê slug, ano, bimestre, ambiente, habilidade e descoberta da spec")


def test_cortes_da_auditoria_de_23_09():
    """Os cortes A2/A4/A8/A9 da auditoria de 23/09/2026, cada um com o caso real que o motivou.

    Os três primeiros derrubam achado que nenhuma rodada de correção podia fechar; o quarto
    põe no PRD uma pergunta que a banca fazia ao handoff — e que o PRD é quem responde.
    """
    from tools.rastro import validar_telemetria, validar_manifesto, validar_prd

    base = (
        "| Evento | Verbo xAPI | Objeto | resultado | contexto |\n"
        "| E1 | interacted | `chat:amara` | `{\"ok\": true}` | `{\"n\": 1}` |\n"
        "Tabelas: `exp08ef2b_gates_turma` lida por polling HTTP de 3s. Grava em `exp08ef2b_sessoes`.\n"
    )
    # A4 — as cinco formas reais de descartar WebSocket nas 14 primeiras execuções
    for forma in (
        "Cloud Run é stateless e não sustenta conexões persistentes WebSocket com autoscaling.",
        "/// Não usa WebSocket (ADR-93/94). Linha única por turma.",
        "Comunicação síncrona operada unicamente por polling HTTP (proibição de WebSockets).",
        "Relógio coletivo operado por polling. Não utiliza WebSocket.",
        "Ratificado o uso exclusivo de polling, eliminando qualquer dependência de WebSockets.",
    ):
        r = validar_telemetria(base + forma + "\n")
        assert r["status"] == "aprovado", (forma, r["achados"])
    # …e propor de verdade continua sendo apontado
    propoe = validar_telemetria(base + "A sala usa WebSocket dedicado para o relógio coletivo.\n")
    assert {a["codigo"] for a in propoe["achados"]} == {"websocket-mencao"}, propoe["achados"]

    # A8 — `liberacao` ausente é default; declarar outro valor é que reprova
    sem_liberacao = _SPEC_MANIFESTO_OK.replace("- `liberacao: por-turma`\n", "")
    assert validar_manifesto(sem_liberacao)["status"] == "aprovado", validar_manifesto(sem_liberacao)["achados"]
    outra = _SPEC_MANIFESTO_OK.replace("- `liberacao: por-turma`", "- `liberacao: aberta`")
    assert "liberacao" in {a.get("campo") for a in validar_manifesto(outra)["achados"]}

    # A2 — o plano de implementação é conferido no PRD, com severidade de atenção
    prd_sem_plano = "# PRD\n`exp06ef1b_sessoes` guarda a sessão.\n| RF-001 | P0 | T-001 |\n"
    cods = {a["codigo"]: a["severidade"] for a in validar_prd(prd_sem_plano)["achados"]}
    for esperado in ("plano-sem-porta", "plano-sem-versao", "plano-sem-e2e", "plano-sem-invariantes"):
        assert cods.get(esperado) == "atencao", (esperado, cods)
    prd_com_plano = prd_sem_plano + (
        "Porta em `apps/hub/lib/experiencias-dev.ts` com `strictPort`. `EXP_VERSION` e `versao.test.ts`.\n"
        "`node scripts/e2e/rodar.mjs estudante`. Invariantes em `invariantes.ts`.\n"
    )
    assert not [a for a in validar_prd(prd_com_plano)["achados"] if a["codigo"].startswith("plano-sem-")]

    print("   ✓ cortes de 23/09: WebSocket descartado não é achado, liberação é default, plano de implementação confere no PRD")


def test_veredito_reproduzivel_e_retry_em_toda_chamada():
    """Quem julga tem seed; quem inventa, não. E ninguém chama o modelo sem rede.

    Dois gates sobre o mesmo artefato precisam dar o mesmo veredito — senão a matriz
    antes × depois de uma sessão vira ruído e não há como saber se uma mudança de critério
    funcionou. Já os agentes que INVENTAM ficam na amostragem livre: achatá-los aproxima as
    missões umas das outras e colide com o gate de semelhança do catálogo (V5).

    O retry vale para todos: a esteira faz de 33 a 55 chamadas e a banca dispara cinco
    validadores em paralelo; um 429 no meio derrubava vinte minutos sem nada reaproveitável.
    """
    from agents.produto import (get_micro_gate_agent, get_gate_estrutural_agent,
                                get_gate_final_produto_agent, get_avaliacao_pedagogica_agent,
                                get_adequacao_pedagogica_agent, get_experiencia_aluno_agent,
                                get_nucleo_narrativo_agent, get_secoes_apoio_agent)
    from agents.design import get_qa_entregaveis_agent
    from agents.dev import get_validador_agents, get_consolidacao_banca_agent
    from agents.checkers import ConsolidacaoBancaAgent

    # o consolidador da banca deixou de ser LlmAgent em 23/09/2026: o veredito é contado em
    # código a partir dos cinco envelopes, com os bloqueantes lidos dos arquivos de critério
    assert isinstance(get_consolidacao_banca_agent(), ConsolidacaoBancaAgent)

    juizes = ([get_micro_gate_agent(), get_gate_estrutural_agent(), get_avaliacao_pedagogica_agent(),
               get_experiencia_aluno_agent(), get_adequacao_pedagogica_agent(),
               get_gate_final_produto_agent(), get_qa_entregaveis_agent()] + get_validador_agents())
    for ag in juizes:
        c = ag.generate_content_config
        assert c.temperature is not None, f"{ag.name} emite veredito sem temperatura fixa"
        assert c.seed is not None, f"{ag.name} emite veredito sem seed"

    for ag in (get_nucleo_narrativo_agent(), get_secoes_apoio_agent()):
        assert ag.generate_content_config.temperature is None, f"{ag.name} inventa: amostragem não se achata"

    for ag in juizes + [get_nucleo_narrativo_agent()]:
        ro = ag.generate_content_config.http_options.retry_options
        assert ro.attempts >= 2 and 429 in ro.http_status_codes, f"{ag.name} chama o modelo sem retry"

    print(f"   ✓ {len(juizes)} juízes com seed fixo, agentes criativos livres, retry com backoff em todos")


def test_donos_e_etapas_e_fonte_unica():
    """A regra que o agente lê e a que o classificador aplica saem do mesmo arquivo.

    Enquanto a lista de tokens vivia só em `tools/rastro.py`, o prompt mandava escrever um
    marcador que o gate reprovava, e a lista acumulou cinco correções datadas — uma por
    sessão quebrada. `references/donos-e-etapas.md` tem a prosa (que os prompts incluem) e a
    cerca JSON (que o código lê): mudar a regra passa a mexer nas duas metades de uma vez.
    """
    import json, re
    from prompts import REFERENCES_DIR
    from tools.rastro import (ETAPAS, ETAPAS_NAO_BLOQUEANTES, _TOKENS_ETAPA, _DONOS_ROTEAVEIS,
                              _DONO_DO_MARCADOR, _etapa_por_tokens, classificar_dono, varrer_lacunas)

    texto = (REFERENCES_DIR / "donos-e-etapas.md").read_text(encoding="utf-8")
    contrato = json.loads(re.search(r"```json\s*(\{.*?\})\s*```", texto, re.DOTALL).group(1))

    assert tuple(contrato["ordem_precedencia"]) == ETAPAS
    assert set(contrato["etapas"]) == set(_TOKENS_ETAPA)
    assert set(ETAPAS_NAO_BLOQUEANTES) == {e for e, d in contrato["etapas"].items() if not d["bloqueia"]}
    # a prosa da tabela e o JSON não podem divergir sobre quem bloqueia
    for etapa, dados in contrato["etapas"].items():
        marca = "**sim**" if dados["bloqueia"] else "não (🟡)"
        assert f"| `{etapa}` | {marca} |" in texto, f"a tabela em prosa discorda do JSON sobre {etapa}"

    # Todo slug CANÔNICO que o despacho aciona precisa cair numa etapa — senão o ticket some
    # em `checkers.py`. Os apelidos (`lacunas` para `fecha-lacunas`) ficam de fora de
    # propósito: como token soltos casariam prosa comum ("gate-rastro-lacunas") e roubariam
    # marcadores de outras etapas.
    for slug in set(_DONOS_ROTEAVEIS.values()):
        assert _etapa_por_tokens(slug) is not None, f"slug roteável `{slug}` não pertence a etapa nenhuma"

    # os donos que a auditoria de 23/09 corrigiu, um a um
    for texto_dono, esperado in (("PO", "humano"), ("Product Owner", "humano"), ("PM", "humano"),
                                 ("Responsável de Dados", "externo"), ("parceiro Entre Redes", "externo"),
                                 ("design system", "plataforma"), ("telas", "design"), ("assets", "dev")):
        assert classificar_dono(texto_dono, "produto") == esperado, texto_dono
    # e o que NÃO pode ter mudado: marcador com dono de agente continua bloqueando
    assert classificar_dono("decisão pendente [ABERTO — gate-estrutural]", "produto") == "produto"

    assert _DONO_DO_MARCADOR["rs_pendente"] == "humano"
    assert _DONO_DO_MARCADOR["verificar_repositorio"] == "plataforma"

    print(f"   ✓ donos e etapas: {len(ETAPAS)} etapas e {len(set(_DONOS_ROTEAVEIS.values()))} slugs, "
          f"prosa e código lidos do mesmo arquivo")


def test_erro_de_grafia_nao_vira_erro_de_arquitetura():
    """Regressão da exp04ef1b (22/09/2026): um underscore produzia duas acusações falsas.

    O handoff escreveu `exp_04ef1b_gates_turma` — a tabela CERTA com grafia errada — e
    declarou o canal corretamente ("nunca WebSocket, conforme ADR-93/94"). Como os dois
    detectores exigiam a grafia sem underscore para RECONHECER a tabela, o gate emitiu
    `tabela-leitura` ("nenhuma tabela nomeada") e `websocket` ("WebSocket como canal de
    sala"), ambos falsos — enquanto o defeito que existia de fato, o prefixo quebrado, não
    era nomeado por ninguém.

    Um defeito, um achado, com o nome que ele tem.
    """
    from tools.rastro import validar_telemetria

    base = ("| Evento | Verbo xAPI | Objeto | resultado | contexto |\n"
            "| E1 | interacted | `chat:amara` | `{}` | `{}` |\n"
            "Nunca WebSocket (ADR-93/94): a sala sincroniza por polling HTTP de 3s.\n")

    torto = base + "Relógio em `exp_04ef1b_gates_turma`; sessão em `exp_04ef1b_sessoes`.\n"
    cods = {a["codigo"]: a["severidade"] for a in validar_telemetria(torto)["achados"]}
    assert cods.get("prefixo-tabela") == "bloqueio", cods
    assert "tabela-leitura" not in cods, "a tabela foi nomeada, só com grafia errada"
    assert "websocket" not in cods, "o canal está declarado: grafia errada não é arquitetura errada"

    certo = base + "Relógio em `exp04ef1b_gates_turma`; sessão em `exp04ef1b_sessoes`.\n"
    assert validar_telemetria(certo)["status"] == "aprovado", validar_telemetria(certo)["achados"]

    # e o controle: sem tabela nenhuma, o bloqueio de leitura continua
    assert "tabela-leitura" in {a["codigo"] for a in validar_telemetria(base)["achados"]}

    # `polling` sozinho não serve de escudo para quem propõe WebSocket de verdade
    escudo = ("| Evento | Verbo | Objeto | resultado | contexto |\n| E1 | interacted | `a:b` | `{}` | `{}` |\n"
              "Usamos polling. A sala sincroniza por WebSocket dedicado.\n")
    assert "websocket" in {a["codigo"] for a in validar_telemetria(escudo)["achados"]}

    print("   ✓ prefixo com underscore é achado próprio; canal declarado com grafia errada não vira WebSocket")


def test_banca_consolidada_em_codigo_enxerga_todos_os_bloqueantes():
    """O consolidador da banca prometia veredito determinístico e era um LlmAgent.

    Em 14 execuções leu 122 achados e aprovou 14 vezes. E a lista de bloqueantes que o prompt
    dele carregava omitia `DES-14` — visão do professor completa, declarada bloqueante nos
    critérios desde 22/09/2026. A visão do professor podia faltar inteira e a banca liberava.

    A lista passa a ser lida dos próprios arquivos de `references/criterios-dev/`: uma fonte,
    sem cópia para divergir.
    """
    from tools.banca import todos_bloqueantes, consolidar, FORA_DA_ESTEIRA

    travam = todos_bloqueantes()
    assert len(travam) == 22, sorted(travam)
    assert "DES-14" in travam, "o bloqueante que o prompt do consolidador não enxergava"

    # ❌ em bloqueante reprova
    r = consolidar({"validacao_design_imersao": {"achados": [
        {"codigo": "DES-14", "severidade": "bloqueio", "resumo": "sem visão do professor"}]}})
    assert r["status"] == "bloqueado", r

    # dimensão que não respondeu é bloqueio, nunca aprovação
    assert consolidar({"validacao_dados_lgpd": None})["status"] == "bloqueado"

    # o que pede ato no monorepo vira pendência declarada e não rebaixa o veredito
    r_plat = consolidar({"validacao_tecnica_arquitetura": {"achados": [
        {"codigo": "TEC-09", "severidade": "bloqueio", "resumo": "sem roteiro de walkthrough"}]}})
    assert r_plat["status"] == "aprovado", r_plat
    assert r_plat["achados"][0]["classe"] == "pendencia-plataforma"
    assert "TEC-09" in FORA_DA_ESTEIRA

    # o veredito global é o PIOR das dimensões
    r_misto = consolidar({
        "validacao_produto_narrativa": {"achados": []},
        "validacao_pedagogia_bncc": {"achados": [{"codigo": "PED-09", "severidade": "bloqueio", "resumo": "x"}]},
    })
    assert r_misto["status"] == "amarelo", r_misto  # PED-09 não é bloqueante

    print(f"   ✓ banca consolidada em código: {len(travam)} bloqueantes lidos dos critérios, DES-14 incluído")


def test_gaps_estruturais_da_auditoria():
    """Quatro coisas que a esteira perdia em silêncio (auditoria de 23/09/2026)."""
    from tools.catalogo import saude_do_indice, aviso_de_indice_cego
    from tools.prototipo import validar as lint_prototipo
    from agents.produto import get_brief_escopo_split

    # G1 — o gate de semelhança se autodesliga quando o índice está incompleto, e ninguém sabe
    cego = {"missoes": [{"slug": "a", "tipo_decisao": "—", "porta_abstracao": "—"},
                        {"slug": "b", "tipo_decisao": "[preencher do manifesto]", "porta_abstracao": "x"}]}
    saude = saude_do_indice(cego)
    assert saude["cegas"] == 2 and saude["fracao_cega"] == 1.0
    assert "praticamente desligada" in (aviso_de_indice_cego(saude) or "")
    cheio = {"missoes": [{"slug": "a", "tipo_decisao": "escolher fonte", "porta_abstracao": "explicar",
                          "descoberta": "o feed esconde o que eu não sigo", "ambiente": "instanooria"}]}
    assert aviso_de_indice_cego(saude_do_indice(cheio)) is None

    # G2 — o brief de escopo sai do one-pager antes do revisor o apagar
    split = get_brief_escopo_split()
    assert split.source_key == "one_pager" and split.extracoes[0]["chave"] == "brief_escopo"

    # G3 — o protótipo deixa de se auto-aprovar: o lint toca o arquivo
    assert lint_prototipo("")["status"] == "bloqueado"
    assert lint_prototipo("<html><body>E1-ALU-01 TODO</body></html>")["status"] == "bloqueado"
    faltando = lint_prototipo("<html><body>E1-ALU-01</body></html>", ["E1-ALU-01", "E3-ALU-02"])
    assert {a["codigo"] for a in faltando["achados"]} == {"telas-ausentes"}
    assert lint_prototipo("<html><body>E1-ALU-01 E3-ALU-02</body></html>",
                          ["E1-ALU-01", "E3-ALU-02"])["status"] == "aprovado"

    # G4 — o gate estrutural passa a receber a rodada que o prompt afirma receber
    from prompts.loader import load_prompt
    assert "{gate_estrutural_rodada?}" in load_prompt("produto/05_gate_estrutural.md")

    print("   ✓ gaps estruturais: índice cego avisa, brief sobrevive ao revisor, protótipo é lido, gate sabe a rodada")


def test_pedagogia_falsificavel():
    """Os critérios pedagógicos deixam de valer só como prosa (auditoria de 23/09/2026)."""
    from tools.evidencia import validar
    from tools.catalogo import recorrencias
    from tools.diagnostico import GATES

    # os três pareceres pedagógicos passam a ter gate no dossiê
    chaves = {g["status"] for g in GATES}
    for k in ("avaliacao_status", "experiencia_status", "adequacao_status", "evidencia_status"):
        assert k in chaves, f"{k} sem gate: o veredito existia e ninguém o lia"

    base = ("## 9. Evidências\n"
            "| Medida | Grau | Sinais | Canal | Tabela.coluna | Habilidade |\n|---|---|---|---|---|---|\n"
            "| `posts_no_mural` | `scored` | `salvar:post` + `submeter:mural` | operacional | `exp06ef1b_sessoes.posts` | `EF06CO09` |\n"
            "- `gabarito_servidor: sim`\n"
            "## 11. Currículo\n"
            "| Código | Momento em tela | Ação observável | O que não conta | Medida do bloco 9 | Marcador |\n|---|---|---|---|---|---|\n"
            "| `EF06CO09` | `E3-ALU-01` (Decidir) | fixa 1 post | rolar o feed | `posts_no_mural` | ternário |\n")
    assert validar(base)["status"] == "aprovado", validar(base)["achados"]

    # (a) `scored` exige os dois sinais que a própria definição do bloco 9 pede
    um_sinal = base.replace("`salvar:post` + `submeter:mural`", "`salvar:post`")
    assert "scored-1-sinal" in {a["codigo"] for a in validar(um_sinal)["achados"]}

    # (b) habilidade declarada sem dado que a meça é currículo no papel
    sem_medida = base.replace("| `posts_no_mural` | ternário |", "| — | ternário |")
    assert "habilidade-sem-medida" in {a["codigo"] for a in validar(sem_medida)["achados"]}

    # (c) PED-04 é bloqueante e nada o conferia
    assert "gabarito-nao-declarado" in {a["codigo"] for a in validar(base.replace("- `gabarito_servidor: sim`", ""))["achados"]}
    assert "gabarito-no-cliente" in {a["codigo"] for a in validar(base + "\nO gabarito fica no bundle do cliente.\n")["achados"]}
    # ...mas a spec que CUMPRE a regra falando do bundle não é acusada
    cumpre = base + "\n**Garante:** ausência total de pistas de gabarito no bundle do cliente.\n"
    assert "gabarito-no-cliente" not in {a["codigo"] for a in validar(cumpre)["achados"]}

    # o achado que volta em duas missões diferentes vira candidato a regra
    idx = {"missoes": [
        {"slug": "a", "achados_pedagogicos": [{"padrao": "termo-sem-ancoragem", "resumo": "x"}]},
        {"slug": "b", "achados_pedagogicos": [{"padrao": "termo-sem-ancoragem", "resumo": "y"}]},
        {"slug": "a", "achados_pedagogicos": [{"padrao": "termo-sem-ancoragem", "resumo": "z"}]},
        {"slug": "a", "achados_pedagogicos": [{"padrao": "so-desta", "resumo": "w"}]},
        {"slug": "a", "achados_pedagogicos": [{"padrao": "so-desta", "resumo": "w"}]},
        {"slug": "a", "achados_pedagogicos": [{"padrao": "so-desta", "resumo": "w"}]}]}
    rec = recorrencias(idx)
    assert [r["padrao"] for r in rec] == ["termo-sem-ancoragem"], rec
    print("   ✓ pedagogia: 4 gates novos, grau/matriz/gabarito conferidos, achado recorrente identificado")


def test_conteudo_imersao_e_escola_publica():
    """Acessibilidade contável, spoiler a jusante e o cenário que não se corta."""
    from prompts.loader import load_prompt

    qa = load_prompt("design/30_qa_entregaveis.md")
    # F1 — não havia NENHUMA linha de acessibilidade contável na esteira: era texto sem verificação
    assert "4,5:1" in qa and "Ordem de foco" in qa, "contraste e ordem de foco não são contáveis"
    assert "64×64" in qa, "o alvo de toque já existia e não pode ter saído"

    # F4 — o micro-gate testa spoiler no núcleo e nada testava depois: copy, tela e protótipo
    # podiam entregar de graça o que a missão existe para a criança descobrir
    assert "D3b" in qa and "Spoiler a jusante" in qa

    # F5 — dois a quatro por aparelho é o primeiro cenário da escola pública, não variação de luxo
    telas = load_prompt("design/26_telas.md")
    assert "estado degradado 2–4 por aparelho" in telas
    i_excecao = telas.index("Exceção que não se prioriza para fora")
    i_degradado = telas.index("estado degradado 2–4 por aparelho")
    assert i_degradado > i_excecao, "o 2–4 precisa estar DENTRO da exceção que não se corta"

    print("   ✓ conteúdo: contraste e foco contáveis, spoiler testado a jusante, cenário 2–4 blindado")


def test_kpi_aponta_para_algo_que_o_mede():
    """O KPI deixa de ser número solto (auditoria de 23/09/2026).

    Nos 14 PRDs medidos: 34 KPIs sem pergunta e sem decisão — métrica de vaidade por
    definição; 20 com baseline `0%`, que não é medida mas espaço em branco vestido de número;
    KPI de uma tela alimentado por evento de OUTRA, com o número saindo parecendo certo; e
    evento declarando leitura em `/telemetry/batch`, que é a fila de entrada, não um leitor.
    O `telemetria-check` deu verde em cinco dessas sessões: confere o formato do evento, não
    se o KPI fecha com ele.
    """
    from tools.kpis import validar_kpis, extrair_perguntas_do_briefing

    bom = ("## 2. Objetivos\n"
           "| KPI | Pergunta | Decisão | Corte | Tela | Evento(s) | Como calcula | Baseline | Alvo | Prazo |\n"
           "|---|---|---|---|---|---|---|---|---|---|\n"
           "| KPI-01 | quantas turmas chegam ao fim? | <50% encurta | missao · serie | E3-ALU-02 | EVT-005 "
           "| count(EVT-005) | sem baseline — primeira medição | 70% | 2 meses |\n"
           "## 13. Eventos\n"
           "| EVT | Quando dispara | resultado | contexto | Onde é lido |\n|---|---|---|---|---|\n"
           "| EVT-005 | Toque em Salvar, na tela E3-ALU-02 | `{\"ok\": true}` | `{\"ms\": 1}` | `exp06ef1b_sessoes` |\n")
    assert validar_kpis(bom)["status"] == "aprovado", validar_kpis(bom)["achados"]

    def cods(txt):
        return {a["codigo"] for a in validar_kpis(txt)["achados"]}

    # o caso real: "Retenção na Mesa de Limpeza" alimentado por evento de "Salvar no Mural"
    assert "kpi-tela-divergente" in cods(bom.replace("na tela E3-ALU-02", "na tela E3-ALU-01"))
    # …mas o KPI que declara só a ETAPA casa com qualquer tela dela
    assert "kpi-tela-divergente" not in cods(bom.replace("| E3-ALU-02 | EVT-005 |", "| E3 | EVT-005 |"))

    assert "baseline-zero" in cods(bom.replace("sem baseline — primeira medição", "0%"))
    assert "baseline-ausente" in cods(bom.replace("sem baseline — primeira medição", "—"))
    assert "kpi-sem-pergunta" in cods(bom.replace("| quantas turmas chegam ao fim? |", "|  |"))
    assert "kpi-sem-decisao" in cods(bom.replace("| <50% encurta |", "|  |"))
    assert "payload-nao-computa" in cods(bom.replace("count(EVT-005)", "count(resultado.falso_neutro)"))
    assert "kpi-evento-inexistente" in cods(bom.replace("| EVT-005 | count", "| EVT-099 | count"))
    assert "leitura-sem-leitor" in cods(bom.replace("`exp06ef1b_sessoes` |", "`/telemetry/batch` |"))
    assert "kpi-aponta-tabela-ou-rota" in cods(bom.replace("| EVT-005 | count", "| `exp06ef1b_sessoes` | count"))

    # o PO escreve em português; a esteira normaliza
    tabela = extrair_perguntas_do_briefing(
        "## Perguntas de produto\nAulas: 1\nHerdar: T1, T2\n"
        "- quantas duplas trocam de escolha? → decisão: se <20%, reforçar a mediação → corte: turma\n")
    assert "declared_lessons: 1" in tabela and "PQ-01" in tabela and "| PO |" in tabela
    assert extrair_perguntas_do_briefing("briefing sem o bloco") == ""

    print("   ✓ KPI: pergunta, decisão, corte, evento na tela certa e baseline honesto — tudo conferido")


def test_custo_e_tendencia_da_esteira():
    """Quanto custa gerar uma missão, e estamos melhorando? Duas perguntas sem resposta até agora."""
    import tempfile, pathlib as _p
    from tools import historico
    from tools.diagnostico import bloco_de_execucao

    # O `usage_metadata` de cada evento era descartado: ninguém sabia o custo nem qual agente pesa
    st = {"execucao": {"modelo": "gemini-3.8-flash", "seed_juiz": 20260923, "temperatura_juiz": 0.1,
                       "duracao_s": 742.3, "tokens": {"entrada": 1_840_000, "saida": 210_000, "chamadas": 41},
                       "tokens_por_agente": {"A47PrdWriter": {"entrada": 390_000, "saida": 48_000, "chamadas": 2}}}}
    bloco = bloco_de_execucao(st)
    assert "2.050.000" in bloco, "o total de tokens precisa aparecer no dossiê"
    assert "seed `20260923`" in bloco, "sem seed e modelo, duas execuções não são comparáveis"
    assert "A47PrdWriter" in bloco and "390.000" in bloco
    assert bloco_de_execucao({}) == "", "execução sem o bloco não quebra o dossiê"

    # série temporal: a queda de achados entre a primeira e a segunda metade da janela
    base = _p.Path(tempfile.mkdtemp())
    for i in range(6):
        historico.registrar({"execucao": {"modelo": "m", "duracao_s": 700,
                                          "tokens": {"entrada": 100_000, "saida": 10_000, "chamadas": 40}},
                             "rastro_lacunas_status": "aprovado",
                             "rastro_lacunas_status_envelope": {"achados": [{"x": 1}] * (5 - i)}},
                            sessao=f"s{i}", base=base)
    assert len(historico.carregar(base)) == 6
    t = historico.tendencia(base)
    assert t["suficiente"] and t["achados"]["depois"] < t["achados"]["antes"], t
    assert historico.tendencia(_p.Path(tempfile.mkdtemp()))["suficiente"] is False

    print("   ✓ custo por agente no dossiê, execução reproduzível e tendência de achados medida")


def test_agentes_novos_rodam_de_ponta_a_ponta():
    """Os agentes determinísticos novos, exercitados pelo ADK — não só pelas funções que chamam.

    Dois bugs só apareceram numa execução real, porque os testes cobriam `tools/` mas nunca
    instanciavam os agentes: um ramo de `RastroCheckAgent` inserido no bloco que monta a
    mensagem em vez do que calcula o resultado (`UnboundLocalError: msg`), e `extrair_slug`
    recebendo o dicionário de estado quando espera o TEXTO do one-pager (`TypeError`). Os dois
    custaram 20 minutos de execução cada.
    """
    from agents.checkers import ConsolidacaoBancaAgent, PrototipoLintAgent, RastroCheckAgent

    spec = ("# Spec — `id: exp06ef1b`\n## 9. Evidências\n"
            "| Medida | Grau | Sinais | Canal | Tabela.coluna | Habilidade |\n|---|---|---|---|---|---|\n"
            "| `posts` | `scored` | `a:b` + `c:d` | operacional | `exp06ef1b_sessoes.p` | `EF06CO09` |\n"
            "- `gabarito_servidor: sim`\n## 11. Currículo\n"
            "| Código | Momento em tela | Ação observável | O que não conta | Medida do bloco 9 | Marcador |\n"
            "|---|---|---|---|---|---|\n| `EF06CO09` | `E3-ALU-02` | fixa | rola | `posts` | ternário |\n")

    root = SequentialAgent(name="R", sub_agents=[
        FakeAgent(name="Spec", key="spec_missao", text=spec),
        FakeAgent(name="Jornada", key="jornada_telas", text="| E1-ALU-01 | abertura |\n"),
        FakeAgent(name="Proto", key="prototipo_arquivo", text="<html><body>E1-ALU-01</body></html>"),
        FakeAgent(name="Prd", key="prd_final", text="# PRD\n`exp06ef1b_sessoes`\n"),
        FakeAgent(name="V1", key="validacao_produto_narrativa",
                  text='```json\n{"status": "aprovado", "achados": []}\n```'),
        RastroCheckAgent(name="A15bEvidenciaCheck", modo="evidencia", rotulo="Matriz de evidência",
                         report_key="evidencia_report", status_key="evidencia_status", estrito=False),
        RastroCheckAgent(name="A48bKpisCheck", modo="kpis", rotulo="KPI",
                         report_key="kpis_report", status_key="kpis_status", estrito=False),
        RastroCheckAgent(name="A15cPerguntasCheck", modo="perguntas", rotulo="Perguntas de produto (9f)",
                         report_key="perguntas_report", status_key="perguntas_status", estrito=False),
        PrototipoLintAgent(name="A29cPrototipoLint"),
        ConsolidacaoBancaAgent(name="A44", fontes=["validacao_produto_narrativa"]),
    ])
    _, st = asyncio.run(_run(root))

    # cada agente gravou status E relatório — é o que faltava quando os bugs passaram
    for chave, relatorio in (("evidencia_status", "evidencia_report"), ("kpis_status", "kpis_report"),
                             ("perguntas_status", "perguntas_report"),
                             ("prototipo_lint_status", "prototipo_lint_report")):
        assert st.get(chave), f"{chave} não foi gravado"
        assert st.get(relatorio), f"{relatorio} não foi gravado"
    assert st["evidencia_status"] == "aprovado", st.get("evidencia_report", "")[:200]
    # o protótipo não tem a tela E3-ALU-02 que a jornada declara
    assert st["prototipo_lint_status"] == "aprovado", "jornada só declara E1-ALU-01 neste teste"
    assert st.get("validacao_dev_report"), "a banca consolidada não gerou relatório"
    assert (st.get("dev_status_envelope") or {}).get("status") == "aprovado"

    # a spec deste teste não traz o 9f: o gate precisa dizer isso em vez de estourar
    assert st["perguntas_status"] == "bloqueado"
    assert "9f" in st["perguntas_report"]

    print("   ✓ agentes novos rodam pelo ADK: evidência, KPI, perguntas do 9f, lint e banca")


_SPEC_9F = """
- `declared_lessons: 1`
- `core_action: scored decisao:mural`
- `perguntas_herdadas: T1, T2, T4`

| PQ | Pergunta | Decisão que dispara | Corte | Etapa | Ação (verbo:objeto) | Origem |
|---|---|---|---|---|---|---|
| PQ-01 | quantas duplas trocam de escolha depois do Aha? | <20% → reforçar a mediação na etapa 3 | turma | E4 | `progressed aha:revelacao` | PO |
| PQ-02 | quantas turmas chegam ao mural? | <50% → encurtar a etapa 3 | turma | E5 | `scored decisao:mural` | PO |
| PQ-03 | quantos abrem a aba de fontes? | <30% → dar pista na copy | missao | E2 | `interacted aba:fontes` | [PROPOSTA — validar com PO] |
| PQ-04 | quantos refazem a escolha antes de salvar? | >40% → a decisão está confusa | turma | E4 | `attempted decisao:mural` | [PROPOSTA — validar com PO] |
| PQ-05 | quantos professores abrem o painel antes da aula? | <50% → mudar o convite | escola | E0 | `opened painel:professor` | [PROPOSTA — validar com PO] |

| Verbo | Objeto | Quando dispara | Resultado | Contexto | Caminho | Onde é lido |
|---|---|---|---|---|---|---|
| progressed | aha:revelacao | ao virar a carta | {"trocou": true} | {"etapa": 4} | analítico | exp09ef1b_sessoes |
| scored | decisao:mural | ao salvar no mural | {"acertos": 3} | {"tempo_ms": 120000} | operacional | exp09ef1b_sessoes |
| interacted | aba:fontes | ao abrir a aba | {"aberta": true} | — | analítico | exp09ef1b_sessoes |
| attempted | decisao:mural | a cada troca | {"trocas": 2} | — | analítico | exp09ef1b_sessoes |
| opened | painel:professor | ao abrir o painel | {"aberto": true} | — | analítico | exp09ef1b_gates_turma |
"""


def test_perguntas_de_produto_9f():
    """As cinco perguntas do 9f: quantidade fechada, decisão com limiar, e uma ação que a spec
    de fato emite e que carrega número. Até 23/09/2026 nada disso era conferido — a pergunta
    nascia na spec sem gate e chegava ao PRD já convertida em KPI."""
    from tools.kpis import PQ_POR_MISSAO, validar_9f

    assert PQ_POR_MISSAO == 5
    ok = validar_9f(_SPEC_9F)
    assert ok["status"] == "aprovado", [a["codigo"] for a in ok["achados"]]
    assert ok["perguntas"] == 5

    # Uma a menos é lacuna: o número é fechado justamente para o PO não receber página em branco.
    quatro = validar_9f(_SPEC_9F.replace(
        "| PQ-05 | quantos professores abrem o painel antes da aula? | <50% → mudar o convite | escola | E0 | `opened painel:professor` | [PROPOSTA — validar com PO] |\n", ""))
    assert quatro["status"] == "bloqueado"
    assert [a["codigo"] for a in quatro["achados"]] == ["pq-faltando"]

    # Ação que a tabela de eventos não declara: a pergunta não tem como ser respondida.
    orfa = validar_9f(_SPEC_9F.replace("`interacted aba:fontes`", "`interacted aba:inexistente`"))
    assert orfa["status"] == "bloqueado"
    assert any(a["codigo"] == "pq-acao-sem-evento" for a in orfa["achados"])

    # Evento que existe mas não carrega nada: diz que aconteceu, não quanto.
    mudo = validar_9f(_SPEC_9F.replace('| interacted | aba:fontes | ao abrir a aba | {"aberta": true} | — |',
                                       "| interacted | aba:fontes | ao abrir a aba | — | — |"))
    assert any(a["codigo"] == "pq-evento-nao-mede" for a in mudo["achados"])

    # Decisão sem limiar não é decisão: ninguém sabe quando agir.
    vaga = validar_9f(_SPEC_9F.replace("<30% → dar pista na copy", "melhorar a experiência"))
    assert any(a["codigo"] == "pq-decisao-sem-limiar" for a in vaga["achados"])

    # Encher linguiça para chegar a cinco: a mesma pergunta duas vezes.
    repetida = validar_9f(_SPEC_9F.replace("quantos abrem a aba de fontes?", "quantas turmas chegam ao mural?"))
    assert any(a["codigo"] == "pq-duplicada" for a in repetida["achados"])

    # `core_action` que a tabela de eventos não emite: a decisão central não é medida por nada.
    sem_core = validar_9f(_SPEC_9F.replace("`core_action: scored decisao:mural`", "`core_action: scored decisao:fantasma`"))
    assert any(a["codigo"] == "core-action-sem-evento" for a in sem_core["achados"])

    print("   ✓ 9f: cinco perguntas, decisão com limiar, ação que existe no bloco 9 e mede")


def test_kpis_cruza_o_prd_com_a_spec():
    """`validar_kpis` recebia a spec e nunca a lia: o PRD era conferido contra si mesmo, e uma
    pergunta decidida em produto podia sumir no caminho sem que nenhum gate notasse."""
    from tools.kpis import validar_kpis

    prd = """
| KPI | PQ | Pergunta | Decisão | Corte | Tela | Evento(s) | Como calcula | Baseline | Alvo | Prazo |
|---|---|---|---|---|---|---|---|---|---|---|
| KPI-01 | PQ-01 | trocam de escolha? | <20% → reforçar | turma | E4-ALU-02 | `EVT-001` | razão | sem baseline — primeira medição | 20% | 11/2026 |
| KPI-02 | PQ-09 | inventada aqui | <10% → nada | turma | E4-ALU-02 | `EVT-001` | razão | sem baseline — primeira medição | 10% | 11/2026 |

| ID | Verbo | Objeto | Quando dispara | Resultado | Contexto | Onde é lido |
|---|---|---|---|---|---|---|
| EVT-001 | progressed | aha:revelacao | E4-ALU-02 | {"trocou": true} | — | exp09ef1b_sessoes |
"""
    r = validar_kpis(prd, _SPEC_9F)
    codigos = [a["codigo"] for a in r["achados"]]
    assert r["status"] == "bloqueado"
    # quatro perguntas da spec ficaram sem KPI, e uma PQ do PRD não existe na spec
    assert codigos.count("pq-sem-kpi") == 4
    assert "kpi-pq-inexistente" in codigos
    assert any("PQ-09" in a["resumo"] for a in r["achados"])

    # Sem spec o gate não inventa achado: é o caso do modo correção que só refaz o PRD.
    assert not [a for a in validar_kpis(prd, "")["achados"] if a["codigo"].startswith("pq-")]

    print("   ✓ KPI ↔ spec: pergunta que morreu entre produto e dev, e KPI que inventou pergunta")


if __name__ == "__main__":
    print("=" * 64)
    print("🚀 Teste estrutural — Gerador de Missões Unooria (Produto → Design → Dev)")
    print("=" * 64)
    s = get_settings()
    print(f"   modelo: {s.gemini_model} · Stitch MCP: {s.stitch_mcp_mode} · etapas: {s.pipeline_stages} · estrito: {s.produto_modo_estrito}")
    # Descoberta automática: a lista literal ficou defasada (um nome inexistente
    # derrubava a suíte inteira com NameError, e 25 dos 51 testes nunca rodavam).
    # `globals()` é a fonte da verdade — teste novo entra sozinho.
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    print(f"   {len(tests)} testes descobertos")
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
