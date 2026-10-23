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
    "mapa_conceitual", "ideacao_mecanismos", "cobertura_report", "profundidade_report", "profundidade_status",
    "profundidade_rodada", "nucleo_rodada",
    "fidelidade_nucleo_report", "fidelidade_report", "fidelidade_entrada", "fidelidade_documentos", "interpretacao_entrada", "mecanica_report",
    "one_pager", "gate_estrutural_report", "gate_estrutural_status", "gate_estrutural_rodada",
    "contrato_produto_report", "contrato_produto_status",
    "avaliacao_pedagogica_report", "experiencia_aluno_report", "adequacao_report", "gate_final_report", "gate_final_status",
    "spec_missao", "spec_missao_gate0", "bncc_status", "bncc_report", "fechamento_lacunas", "relatorio_lacunas", "lacunas_status",
    "ambiente_simulado", "ambiente_status",
    "brief_oficio", "jornada_telas", "fluxo_arestas", "copy_strings", "camada_caa",
    "wireframes_cobertura", "copy_strings_revisada", "qa_entregaveis_report", "design_status",
    "prototipo_html", "prototipo_arquivo", "prototipo_relatorio", "stitch_links", "diagramas_html",
    "miro_links", "miro_board",
    "handoff_dev", "brief_assets", "banco_conteudo", "conteudo_report", "manifesto_status", "manifesto_report", "telemetria_status", "telemetria_report",
    "rastro_lacunas_status", "rastro_lacunas_report",
    "rastro_spec_status", "rastro_spec_report", "rastro_design_status", "rastro_design_report",
    "conteudo_aprovado", "conteudo_aprovado_spec_report", "conteudo_aprovado_spec_status", "conteudo_aprovado_prd_report",
    "conteudo_aprovado_prd_status", "conteudo_aprovado_pedagogico_report", "conteudo_aprovado_pedagogico_status",
    "prototipo_lint_report", "consistencia_report", "qa_afirmacoes_report", "evidencia_report", "evidencia_status", "kpis_report", "kpis_status", "perguntas_po", "material_anexado", "one_pager_po", "one_pager_po_report", "juiz_achados_entrada",
    "juiz_contrato_produto_saida", "juiz_evidencia_saida", "juiz_telemetria_saida",
    # os comitês pedagógicos (15/10/2026)
    "evidencia_one_pager_report", "mecanica_one_pager_report", "comite_canal_a_report", "comite_canal_b_report",
    "comite_final_report", "comite_canal_a_curriculo", "comite_canal_a_medida", "comite_canal_a_vivencia",
    "comite_canal_b_curriculo", "comite_canal_b_medida", "comite_canal_b_experiencia", "comite_final_pedagogia",
    "comite_final_qualidade", "comite_final_imersao",
    "juiz_fidelidade_saida", "juiz_fidelidade_nucleo_saida", "interpretacao_fidelidade_saida",
    "interpretacao_fidelidade_nucleo_saida", "interpretacao_fidelidade_design_saida", "interpretacao_fidelidade_dev_saida",
    # a banca nas quatro posições (08/10/2026)
    *("rodada_anterior_" + c for c in ("spec_missao", "one_pager_resumido", "handoff_dev", "brief_assets",
                                       "prd_final", "one_pager_pedagogico", "banco_conteudo", "mapa_conceitual",
                                       "ideacao_mecanismos", "nucleo_narrativo", "one_pager", "fechamento_lacunas",
                                       "ambiente_simulado", "brief_oficio", "jornada_telas", "fluxo_arestas",
                                       "copy_strings", "camada_caa", "wireframes_cobertura", "copy_strings_revisada",
                                       "prototipo_html")),
    "contradicoes_documento", "contradicoes_referencia", "coerencia_prd_report", "coerencia_prd_status",
    "coerencia_pedagogico_report", "coerencia_pedagogico_status", "juiz_coerencia_pedagogico_saida",
    "juiz_coerencia_prd_saida",
    "escopo_banca", "banca_produto_report", "banca_produto_status", "banca_produto_narrativa", "banca_produto_pedagogia",
    "banca_design_report", "banca_design_status", "banca_design_narrativa", "banca_design_imersao",
    "banca_entrada_report", "banca_entrada_status", "banca_entrada_narrativa", "banca_entrada_imersao",
    "banca_entrada_pedagogia",
    # 07/10/2026 (noite): resumido × canônico, fidelidade ao refazer de design e de dev, matriz final do dev,
    # spec consolidada × one-pager, o que mudou no one-pager desde a versão anterior e os retratos que o medem
    "conteudo_aprovado_resumido_report", "conteudo_aprovado_resumido_status", "resumido_rodada",
    "fidelidade_design_report", "fidelidade_design_status", "juiz_fidelidade_design_saida",
    "fidelidade_dev_report", "fidelidade_dev_status", "juiz_fidelidade_dev_saida",
    "rastreabilidade_dev_report", "rastreabilidade_dev_status",
    "conteudo_aprovado_spec_design_report", "conteudo_aprovado_spec_design_status",
    "mudancas_no_aprovado", "conteudo_aprovado_base_design", "conteudo_aprovado_base_dev",
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
    # correção pontual (tools/edicao_pontual.py): o editor, fora da esteira, e o que a linha de base lê
    "pedido_pontual", "documentos_pontuais", "etapa_da_correcao", "erros_da_edicao", "achados_da_edicao",
    "edicao_pontual", "edicoes_pontuais", "modo_correcao", "documentos_travados", "linha_de_base",
    "linha_de_base_report",
    # parecer humano entre etapas (`pipeline/passagem.py`): notas no rodapé, pareceres no dossiê
    "notas_de_passagem", "pareceres_humanos",
    # conversa com as etapas (`pipeline/conversa_etapas.py`): fora da esteira, só o agente de conversa lê
    "etapa_da_conversa", "etapa_do_parecer", "contexto_da_etapa", "conversa_anterior", "resposta_conversa",
    # versão anterior de cada documento autoral, quando a etapa é refeita (pipeline/reexecucao.py)
    *("anterior_" + c for c in (
        "mapa_conceitual", "ideacao_mecanismos", "nucleo_narrativo", "one_pager", "spec_missao", "one_pager_resumido",
        "fechamento_lacunas", "ambiente_simulado", "brief_oficio", "jornada_telas", "fluxo_arestas", "copy_strings",
        "camada_caa", "wireframes_cobertura", "copy_strings_revisada", "prototipo_html",
        "handoff_dev", "brief_assets", "banco_conteudo", "prd_final", "one_pager_pedagogico")),
}
# Variáveis estáticas substituídas pelo loader antes do ADK
CONFIG_VARS = {"stitch_mcp_mode": "off", "stitch_project_url_base": "u", "gate_max_rodadas": 3, "qa_max_rodadas": 1}

# Chaves obrigatórias (sem `?`) permitidas por área: existem sempre antes do agente rodar
REQUIRED_ALLOWED = {"one_pager", "gate_estrutural_report", "nucleo_narrativo"}

EXPECTED_AGENTS = {
    "A002MapaConceitual", "A003IdeacaoMecanismos", "A006CoberturaConceitual", "A008JuizProfundidade",
    "A011ProfundidadeCheck", "A013NucleoCheck", "A010FidelidadeNucleo", "A060FidelidadeProduto", "A009ContaDaVirada",
    "NucleoNarrativoLoop", "A004NucleoNarrativo", "A007MicroGate", "A012MicroGateCheck", "A014SecoesApoio",
    "GateEstruturalLoop", "A024ContratoProdutoCheck", "A026GateEstrutural", "A027GateEstruturalCheck", "A028RevisorOnePager",
    "AvaliacoesParalelas", "A029aAvaliacaoPedagogica", "A029bExperienciaEstudante",
    "A029cAdequacaoPedagogica",
    "A033AdequacaoCheck",
    "A034RevisorOnePagerParecer",
    "AvaliacoesLoop", "A043GateFinalProduto",
    "A044GateFinalProdutoCheck", "A045SpecMissao", "A046BnccCheck", "A061OnePagerResumido", "DesignStage", "A065FechaLacunas", "A066FechaLacunasSplit",
    "A067AmbienteSimulado", "A068AmbienteSimuladoSplit", "A070BriefOficio", "A071Jornada",
    "A072Fluxo", "A073CopyPtBr", "A074Caa", "A075Telas", "A077CopyRevisao", "A088QaEntregaveis",
    "A079Prototipo", "A080ArtefatosDesign", "A084EspelhoMiro", "A082Consistencia", "A089QaAfirmacoes", "A090QaEntregaveisCheck", "DevStage", "A099ManifestoCheck", "HandoffParalelo", "A100aHandoffDev", "A100bBriefAssets", "A104BancoConteudo", "A105ConteudoCheck",
    "A101TelemetriaCheck", "A107LacunaCheck", "A114PrdCheck",
    "BancaValidacaoDev", "A109aBancaDadosLgpd", "A109bBancaTecnicaArquitetura",
    # a banca nas quatro posições (08/10/2026): fim de produto, fim de design e entrada do dev
    "A057aBancaProdutoNarrativa", "A057bBancaPedagogiaBncc", "A058BancaConsolidacao",
    "A086aBancaProdutoNarrativa", "A086bBancaDesignImersao", "A087BancaConsolidacao",
    "A097aBancaProdutoNarrativa", "A097bBancaDesignImersao", "A097cBancaPedagogiaBncc", "A098BancaConsolidacao",
    "DevConstrucao",
    "A110ConsolidacaoBanca", "A111ValidacaoDevCheck", "A113PrdWriter", "A120OnePagerPedagogico",
    "A128Aprendizado",
    "A127Diagnostico", "ProdutoStage",
    # os comitês pedagógicos (15/10/2026): o dos canais envolve os autores, o final envolve a cadeia de produto
    "ComiteCanaisLoop", "ComiteFinalLoop", "NucleoNarrativoLoopIsolado", "ComiteCanaisLoopIsolado",
    "A018EvidenciaOnePager", "A019ComiteCanais", "A019aComiteCanalACurriculo", "A019bComiteCanalAMedida",
    "A019cComiteCanalAVivencia", "A019dComiteCanalBCurriculo", "A019eComiteCanalBMedida", "A019fComiteCanalBExperiencia",
    "A020VotosCanalA", "A021VotosCanalB", "A022ComiteCanaisRodada", "A038EvidenciaOnePagerFinal",
    "A039ContaDaViradaOnePager", "A040ComiteFinal", "A040aComiteFinalPedagogia", "A040bComiteFinalQualidade",
    "A040cComiteFinalImersao", "A041VotosFinal", "A042ComiteFinalRodada",
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
    # A profundidade conta ANTES do veredito do micro-gate: na última rodada o `A012MicroGateCheck`
    # encerra o loop ao reprovar, e a rodada ficaria sem status de profundidade.
    assert [a.name for a in micro.sub_agents] == ["A004NucleoNarrativo", "A005VizinhasCatalogo", "A006CoberturaConceitual",
                                                  "A007MicroGate", "A008JuizProfundidade", "A009ContaDaVirada", "A010FidelidadeNucleo",
                                                  "A011ProfundidadeCheck", "A012MicroGateCheck", "A013NucleoCheck"]
    produto = next(a for _, a in iter_agent_tree(orchestrator) if a.name == "ProdutoStage")
    assert [a.name for a in produto.sub_agents][:5] == ["A001VizinhasCatalogo", "A002MapaConceitual",
                                                        "A003IdeacaoMecanismos", "ComiteFinalLoop", "A043GateFinalProduto"]
    # os comitês só julgam: o loop de cada um envolve quem escreve a missão, isolado (`agents/comite.py`)
    final = produto.find_agent("ComiteFinalLoop")
    assert [a.name for a in final.sub_agents] == [
        "ComiteCanaisLoopIsolado", "GateEstruturalLoopIsolado", "AvaliacoesLoopIsolado", "OnePagerPoLoopIsolado",
        "A038EvidenciaOnePagerFinal", "A039ContaDaViradaOnePager", "A040ComiteFinal", "A041VotosFinal",
        "A042ComiteFinalRodada"]
    assert final.max_iterations == settings.comite_final_max_rodadas
    canais = produto.find_agent("ComiteCanaisLoop")
    assert [a.name for a in canais.sub_agents] == [
        "NucleoNarrativoLoopIsolado", "SecoesApoioLoopIsolado", "A017OnePagerExiste", "A018EvidenciaOnePager",
        "A019ComiteCanais", "A020VotosCanalA", "A021VotosCanalB", "A022ComiteCanaisRodada"]
    assert canais.max_iterations == settings.comite_max_rodadas
    assert [j.output_key for j in canais.find_agent("A019ComiteCanais").sub_agents] == [
        "comite_canal_a_curriculo", "comite_canal_a_medida", "comite_canal_a_vivencia",
        "comite_canal_b_curriculo", "comite_canal_b_medida", "comite_canal_b_experiencia"]

    loop = next(a for _, a in iter_agent_tree(orchestrator) if a.name == "GateEstruturalLoop")
    assert isinstance(loop, LoopAgent) and loop.max_iterations == settings.gate_estrutural_max_rodadas
    # O lint vem antes do gate, dentro do loop: cada rodada relê a versão corrente do one-pager.
    # `A023BriefEscopoSplit` entra desde 23/09/2026: o A014 entrega one-pager E brief de escopo
    # na mesma `output_key`, e o A07 devolve só o one-pager revisado — o brief evaporava a
    # cada execução, sem erro e sem artefato.
    # o juiz de achados roda entre o lint e o gate: o gate estrutural lê o relatório já revisto
    assert [a.name for a in loop.sub_agents] == ["A023BriefEscopoSplit", "A024ContratoProdutoCheck", "A025JuizContratoProduto",
                                                 "A026GateEstrutural", "A027GateEstruturalCheck", "A028RevisorOnePager"]
    banca = next(a for _, a in iter_agent_tree(orchestrator) if a.name == "BancaValidacaoDev")
    # dentro do dev só dados e técnica; produto, design e pedagogia rodam no fim das etapas e na entrada (08/10/2026)
    assert [j.name for j in banca.sub_agents] == ["A109aBancaDadosLgpd", "A109bBancaTecnicaArquitetura"]

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
    assert [a.name for a in so_produto.sub_agents] == ["ProdutoStage", "A127Diagnostico", "A128Aprendizado", "A129RegistroCatalogo"]
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
        "\n## Passo 5b — Relatório de preenchimento — `relatorio-preenchimento.md`\n"
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
    # desde 09/10/2026 os blocos 0–13 vêm da spec aceita pelo código (`montar_sobre_aceita`): o D9 que devolve só o
    # bloco 14 não apaga nada — a spec fica inteira, com o bloco novo no fim
    assert state_frag["spec_missao"].startswith(spec_grande.rstrip()), "a spec foi trocada por um fragmento"
    assert state_frag["spec_missao"].count("## 14. Ambiente simulado") == 1

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
            BnccCheckAgent(name="A046BnccCheck", estrito=True),
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
            BnccCheckAgent(name="A046BnccCheck", estrito=True),
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
- `secao_ds: unoovista`
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
    tiktok = validar_manifesto(_SPEC_MANIFESTO_OK.replace("secao_ds: unoovista", "secao_ds: tiktooria"))
    assert tiktok["status"] == "amarelo" and tiktok["achados"][0]["etapa"] == "plataforma"
    # 06/10/2026: a lista fixa aceitava só as seções legadas e reprovava `unooriaai` — a missão do 9º ano
    # saiu em `chatgpt`. Agora as seções vêm do contrato, e a legada em missão nova bloqueia com a sucessora.
    uai = validar_manifesto(_SPEC_MANIFESTO_OK.replace("secao_ds: unoovista", "secao_ds: unooriaai"))
    assert uai["status"] == "aprovado", uai["achados"]
    gpt = validar_manifesto(_SPEC_MANIFESTO_OK.replace("secao_ds: unoovista", "secao_ds: chatgpt"))
    assert gpt["status"] == "bloqueado" and "unooriaai" in gpt["achados"][0]["resumo"], gpt["achados"]

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
    # o handoff é quem descreve a implementação: gabarito no bundle bloqueia aqui também,
    # e dizer que ele NÃO vai ao bundle não é achado
    no_bundle = layout_livre + "\nO gabarito das alternativas vai no bundle do cliente.\n"
    assert {a["codigo"] for a in validar_telemetria(no_bundle)["achados"]} == {"gabarito-no-cliente"}
    nega = layout_livre + "\nO gabarito nunca vai no bundle do cliente: a correção é no servidor.\n"
    assert validar_telemetria(nega)["status"] == "aprovado", validar_telemetria(nega)["achados"]

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
    # escrevê-los — 065_fechamento_lacunas.md manda carimbar o RS-n, e 34/47 mandam marcar o
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

    # o D0 consolida, por contrato, a lista do que FECHOU — e o varredor lia a linha que
    # registra o fechamento como a pendência que ela fechou. Uma linha dessas bloqueou o PRD
    # da sessão exp04ef1b em 25/09/2026, com os outros vinte gates verdes ou amarelos.
    # A marca só vale para o `[D0-n]` que o bloco 13 de fato decidiu.
    resolvidas = {
        "spec_missao": (
            "## Bloco 13 — decisões do fechamento de lacunas\n"
            "- [D0-09] Teto de texto: 30 palavras por resumo.\n\n"
            "### Lista consolidada de itens `[ABERTO — dono]`\n"
            "- `[ABERTO — dono: produto: Ratificação do teto de texto por resumo]` (§6) — Resolvido em [D0-09].\n"
        ),
        "handoff_dev": "limpo",
    }
    r_resolv = varrer_lacunas(fontes, resolvidas)
    assert r_resolv["status"] == "aprovado", r_resolv["achados"]
    assert [x["d0"] for x in r_resolv["resolvidos"]] == ["D0-9"], r_resolv["resolvidos"]   # o número sai sem o zero à esquerda

    # citar um D0 que o bloco 13 não decidiu não fecha nada: a pendência continua aberta.
    # (ratificar é ato do PO, então ela pesa como decisão humana — o que importa aqui é que
    # ela NÃO foi dada por fechada.)
    inventado = dict(resolvidas, spec_missao=resolvidas["spec_missao"].replace("[D0-09].", "[D0-77]."))
    r_inv = varrer_lacunas(fontes, inventado)
    assert not r_inv["resolvidos"] and len(r_inv["achados"]) == 1, r_inv

    # e sem a referência da decisão também não fecha
    sem_ref = {"spec_missao": "- `[ABERTO — dono: produto: Ratificação do teto]` (§6) — Resolvido.", "handoff_dev": "limpo"}
    r_sem = varrer_lacunas(fontes, sem_ref)
    assert not r_sem["resolvidos"] and len(r_sem["achados"]) == 1, r_sem

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
            RastroCheckAgent(name="A107LacunaCheck", modo="lacunas", rotulo="Rastro", report_key="rastro_lacunas_report", status_key="rastro_lacunas_status", fontes=fontes, estrito=True),
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
            RastroCheckAgent(name="A107LacunaCheck", modo="lacunas", rotulo="Rastro", report_key="rastro_lacunas_report", status_key="rastro_lacunas_status", fontes=fontes, estrito=True),
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
            RastroCheckAgent(name="A099ManifestoCheck", modo="manifesto", rotulo="Manifesto", report_key="manifesto_report", status_key="manifesto_status", estrito=True),
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
            "- `capabilities: [telemetria, progresso]`\n- `secao_ds: unoovista`\n"
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
            RastroCheckAgent(name="A099ManifestoCheck", modo="manifesto", rotulo="Manifesto", report_key="manifesto_report", status_key="manifesto_status", estrito=True),
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
            FakeAgent(name="Prd2", key="prd_final", text="rascunho [ABERTO — coordenação pedagógica: confirmar semana]",
                      before_agent_callback=marcar_heranca),
            check("Check2"),
        ],
    )
    _, state = asyncio.run(_run(root))
    assert state["prd_status"] == "amarelo", state.get("prd_check_report")
    assert state.get(KEY_PIPELINE_BLOQUEADO) is False, "a reprovação da rodada 1 não pode sobreviver ao 🟡 da rodada 2"
    assert not state.get(KEY_DEGRADACOES), state.get(KEY_DEGRADACOES)
    assert not state.get(KEY_HERANCA)
    # o redator da rodada 2 rodou sob a reprovação da 1 e foi anotado; com o gate aprovado, a
    # anotação sai — a geração de 23/09 terminou sem impedimento e com o PRD listado como provisório
    assert state.get("agentes_degradados") == [], state.get("agentes_degradados")
    print("   ✓ gate 🔴 → 🟡 limpa a degradação, destrava a execução e tira o 'provisório' de quem rodou nela")


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
    assert [a.name for a in orch.sub_agents] == ["ProdutoStage", "A127Diagnostico", "A128Aprendizado", "A129RegistroCatalogo"]
    produto = orch.sub_agents[0]
    # o resumido em loop com a conferência contra o canônico (07/10/2026)
    assert [a.name for a in produto.sub_agents] == ["SpecLoop", "A060FidelidadeProduto", "OnePagerResumidoLoop"]
    assert [a.name for a in produto.sub_agents[2].sub_agents] == [
        "A061OnePagerResumido", "A062ConteudoAprovadoResumido", "A063ResumidoRodada"]
    # `A048EvidenciaCheck` entra desde 23/09/2026: grau `scored` com dois sinais, habilidade do
    # bloco 11 com momento e medida, gabarito no servidor. Eram três exigências que a spec
    # declarava em prosa e nenhuma verificação tocava — PED-04 é bloqueante e ninguém o conferia.
    # `A050PerguntasCheck` e o juiz `A051JuizPerguntas` entram em 23/09/2026: as cinco perguntas
    # de produto do sub-bloco 9f nasciam na spec sem nenhum gate, e o `validar_kpis` do PRD recebia
    # a spec como parâmetro morto — a pergunta podia morrer entre produto e dev sem deixar rastro.
    assert [a.name for a in produto.sub_agents[0].sub_agents] == [
        "A045SpecMissao", "A046BnccCheck", "A047ManifestoCheckProduto", "A048EvidenciaCheck",
        # juiz de achados (23/09/2026): o regex marca "gabarito no cliente", o juiz decide se o texto
        # afirma ou cita para vedar, e o achado só sai com citação literal conferida
        "A049JuizEvidencia",
        "A050PerguntasCheck", "A051JuizPerguntas", "A052JuizPerguntasCheck",
        # rastro de lacunas da spec (25/09/2026): a pendência de produto só era cobrada em dev,
        # que não reescreve a spec — e barrava o PRD da exp04ef1b sem ninguém poder fechá-la
        "A053RastroSpec",
        # spec × one-pager aprovado (06/10/2026): a spec aplicava ressalvas que o PO tinha recusado —
        # a exp06ef1b perdeu uma habilidade e cinco minutos de tela — e ninguém via
        "A054ConteudoAprovadoSpec",
        # a banca no fim de produto (08/10/2026): o achado volta ao autor da spec antes do parecer
        "A055ConteudoAprovado", "A056EscopoBanca", "A057Banca", "A058BancaConsolidacao", "A059SpecCheck"]
    assert produto.sub_agents[0].max_iterations == max(1, get_settings().spec_max_rodadas)
    nomes = [a.name for _, a in iter_agent_tree(orch)]
    assert "A004NucleoNarrativo" not in nomes and "A026GateEstrutural" not in nomes
    assert not any(getattr(a, "include_contents", "none") == "default" for _, a in iter_agent_tree(orch) if isinstance(a, LlmAgent)), \
        "nenhum agente da correção lê a mensagem do usuário: o pedido viaja pelo estado"

    completo = create_mission_orchestrator(stages=["spec", "design", "dev"])
    assert [a.name for a in completo.sub_agents] == ["ProdutoStage", "DesignStage", "DevStage", "A127Diagnostico", "A128Aprendizado", "A129RegistroCatalogo"]
    todos = [a.name for _, a in iter_agent_tree(completo)]
    assert len(todos) == len(set(todos)), "nome duplicado na árvore parcial"
    # "produto" e "spec" juntos: a etapa inteira vence
    assert "A004NucleoNarrativo" in [a.name for _, a in iter_agent_tree(create_mission_orchestrator(stages=["produto", "spec"]))]

    try:
        build_produto_stage(a_partir_de="design")
        assert False, "a_partir_de inválido deveria falhar"
    except ValueError:
        pass

    assert [s["key"] for s in stages_para_ui(["spec", "design", "dev"])] == ["spec", "design", "dev", "transversal"]
    assert [s["key"] for s in stages_para_ui(["dev"])] == ["dev", "transversal"]
    assert [s["key"] for s in stages_para_ui(["produto", "design", "dev"])] == ["produto", "design", "dev", "transversal"]
    assert [m["id"] for m in STAGE_SPEC["agents"]] == [
        "A045SpecMissao", "A046BnccCheck", "A047ManifestoCheckProduto", "A048EvidenciaCheck",
        "A050PerguntasCheck", "A051JuizPerguntas", "A052JuizPerguntasCheck",
        "A054ConteudoAprovadoSpec", "A057aBancaProdutoNarrativa", "A057bBancaPedagogiaBncc", "A058BancaConsolidacao",
        "A059SpecCheck", "A060FidelidadeProduto", "A061OnePagerResumido",
        "A062ConteudoAprovadoResumido", "A063ResumidoRodada"]
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
    """A triagem vê a mensagem e os anexos (como o A004), grava em `triagem_correcao` e fica fora da esteira."""
    from agents.transversal import TRANSVERSAL_METADATA, get_triagem_correcao_agent
    from prompts.loader import list_state_variables

    agente = get_triagem_correcao_agent()
    assert agente.include_contents == "default"
    assert agente.output_key == "triagem_correcao"
    instr = str(agente.instruction)
    assert "{mapa_da_missao?}" in instr and "{briefing?}" in instr
    assert '"etapa": "produto | spec | design | dev | nenhuma"' in instr
    assert all(m["id"] != "A000TriagemCorrecao" for m in TRANSVERSAL_METADATA)
    for var in list_state_variables(instr):
        # o aviso de resposta cortada pelo modelo é por agente (`agents.callbacks.registrar_corte_do_modelo`)
        assert var in KNOWN_STATE_KEYS or var.startswith("bloqueio_modelo_"), var
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

    pulo = "⏭️ `A113PrdWriter` não executado — pipeline bloqueado (Ficha do manifesto bloqueado (1 lacuna(s)))."
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
        agent_name = "A071Jornada"

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


def _fora_de_codigo(md: str) -> list:
    """Linhas que o Streamlit renderiza como markdown: cercas pareadas como no CommonMark.

    Qualquer cerca abre; só a cerca nua, da mesma marca e com tamanho >= fecha. É a regra que o
    react-markdown do Streamlit segue e que o saneamento antigo (alternar a cada ```) não seguia.
    """
    import re

    fora, aberta = [], None
    for linha in md.split("\n"):
        m = re.match(r"^\s*(`{3,}|~{3,})(.*)$", linha)
        if m and aberta is None:
            aberta = m.group(1)
            continue
        if m and aberta and m.group(1)[0] == aberta[0] and len(m.group(1)) >= len(aberta) and not m.group(2).strip():
            aberta = None
            continue
        if aberta is None:
            fora.append(linha)
    return fora


def test_markdown_saneado_cercas_aninhadas_e_tabelas():
    """Artefato cru na tela: `#`, `|` e `**` à mostra dentro de bloco de código.

    Regressão de 2026-10-07 (auditoria sobre as sessões do bucket): o agente embrulha a spec e
    o PRD em ```markdown e abre ```typescript/```sql dentro. O renderizador fecha o invólucro
    no primeiro ``` nu e dali em diante código e texto trocam de lugar — no PRD da exp06ef1b,
    front matter e seções 0–4 em código, e a seção 5 também. O `.md` em disco sai
    desembrulhado (`desembrulhar_cerca`), mas a tela lê o estado, que nunca foi.
    """
    from tools.markdown_blocos import desembrulhar_documento, sanear_para_streamlit as sanear

    # spec da exp07ef1b: frase de abertura, invólucro, bloco interno com linguagem, ``` órfão no fim
    spec = (
        "Abaixo segue o contrato consolidado.\n\n```markdown\n# Spec — A Seleção v1.0\n\n"
        "```typescript\nexport const lote = z.object({})\n```\n\n## 9. Regras de geração\n"
        "| Perfil | Posts |\n|---|---|\n| @folhaoficial_ | 4 |\n```\n\n---"
    )
    fora = _fora_de_codigo(sanear(spec))
    assert "# Spec — A Seleção v1.0" in fora, "o título da spec ficou dentro do bloco de código"
    assert "## 9. Regras de geração" in fora and "| @folhaoficial_ | 4 |" in fora
    assert "export const lote = z.object({})" not in fora, "o typescript tem de continuar código"
    assert "```markdown" not in sanear(spec)

    # PRD da exp06ef1b: invólucro na 1ª linha e bloco NU dentro (cenários de dispositivo)
    prd = (
        "```markdown\n---\nprd_id: PRD-exp06ef1b\ntitulo: O Júri Estadual de Projetos\n---\n\n"
        "### Cenários de dispositivo\n\n```\nCENÁRIO A (1:1 — Ideal)\n```\n\n---\n\n"
        "# 5. Experiência — narrativa e mecânica\n\n| Etapa | Ação |\n|---|---|\n| E1 | ler |\n```"
    )
    fora = _fora_de_codigo(sanear(prd))
    assert "# 5. Experiência — narrativa e mecânica" in fora and "| E1 | ler |" in fora
    assert "CENÁRIO A (1:1 — Ideal)" not in fora
    # aba PRD: o metadado só aparece se o invólucro sair antes de ler o front matter
    from pipeline.session_store import extrair_metadados_frontmatter
    meta, corpo = extrair_metadados_frontmatter(desembrulhar_documento(prd))
    assert meta.get("prd_id") == "PRD-exp06ef1b" and corpo.startswith("### Cenários")

    # D0 (fechamento de lacunas): a spec citada no meio do relatório, com ```sql dentro
    d0 = (
        "Relatório do D0.\n\n```markdown\n# Spec — Quem Mandou Isso?\n\n```sql\nselect 1;\n```\n\n"
        "## 9. Bloco de dados\ntexto\n```\n\nFim do relatório.\n"
    )
    fora = _fora_de_codigo(sanear(d0))
    assert "## 9. Bloco de dados" in fora and "Fim do relatório." in fora and "select 1;" not in fora

    # o que NÃO pode mudar: trecho citado sem título, bem fechado, no meio do gate estrutural
    gate = (
        "Trecho proposto:\n\n```markdown\n### 2.4 Avaliação externa\n* **Descritor SAEB:** N/A\n```\n\n"
        "Justificativa do gate.\nSegunda linha.\nTerceira linha.\nQuarta linha.\nQuinta linha.\n"
    )
    assert sanear(gate) == gate
    assert desembrulhar_documento("# normal\ntexto") == "# normal\ntexto"
    assert sanear("```sql\nSELECT 1;\n```") == "```sql\nSELECT 1;\n```"

    # cerca órfã: depois dela só markdown (ou nada) → sai; depois dela código → fecha no fim
    assert "```" not in sanear("# T\n\ntexto\n```\n\n---")
    assert "```" not in sanear("```\n## Seção que ficou presa\n| a | b |\n")
    assert sanear("texto\n```py\nx=1\n").endswith("```\n")

    # `$` dentro de bloco aninhado é código: sem `\`, que o leitor via escrito no PL/pgSQL
    aninhado = "```markdown\n# Doc\n\n```sql\nDO $$ x $$;\n```\n\nCusta R$ 5.\n```"
    assert "DO $$ x $$;" in sanear(aninhado) and r"Custa R\$ 5." in sanear(aninhado)
    assert "DO $$" in sanear("~~~sql\nDO $$\n~~~\nR$ 1") and r"R\$ 1" in sanear("~~~sql\nDO $$\n~~~\nR$ 1")
    assert sanear(r"já escapado R\$ 3") == r"já escapado R\$ 3"

    # front matter na aba Dev (PRD da exp01ef1b): sem isso, <hr> + um <h2> com todas as chaves
    fm = sanear("---\nprd_id: PRD-exp01ef1b\nlinks:\n  stitch: https://x\n---\n\n# 0. Resumo executivo")
    assert fm.startswith("```yaml\nprd_id: PRD-exp01ef1b") and "# 0. Resumo executivo" in _fora_de_codigo(fm)

    # `---` colado no parágrafo (one-pager pedagógico): divisória, não <h2> do parágrafo inteiro
    ped = "**O momento do \"ahá\":**  \nNo mesmo segundo, o telão projeta o gráfico.\n---\n## Próxima"
    assert "gráfico.\n\n---" in sanear(ped)

    # tabela: separador com uma coluna a mais (aprendizado da exp07ef1b) — saía tudo como texto
    t1 = sanear("| ID | Origem | Classe |\n|---|---|---|---|\n| D0-1 | fecha-lacunas | documental |")
    assert t1.split("\n")[1] == "|---|---|---|"
    # tabela sem cabeçalho (experiência do aluno da exp06ef1b)
    t2 = sanear("Resumo:\n\n| Obrigatórios | ✅ 4 | ⚠️ 1 | ❌ 0 |\n| Desejáveis | ✅ 2 | ⚠️ 0 | ❌ 0 |")
    assert "| | | | |\n|---|---|---|---|\n| Obrigatórios" in t2
    # `|` dentro de crase numa célula (aresta A18 do fluxo da 4e6cf385): a última coluna sumia
    t3 = sanear("| ID | Guarda | Nota |\n|---|---|---|\n| A18 | `etapa == 'E1' | 'E4'` | espera |")
    assert r"`etapa == 'E1' \| 'E4'`" in t3
    # `<br>` na célula (handoff da exp07ef1b) aparecia escrito; no mermaid ele é do diagrama
    t4 = sanear("| Regra | Itens |\n|---|---|\n| R1 | - Cardinalidade.<br>- Modal irreversível |")
    assert "| R1 | - Cardinalidade. · Modal irreversível |" in t4
    mer = "```mermaid\nflowchart LR\n  A[\"E1<br/>Lista\"]\n```"
    assert sanear(mer) == mer
    print("   ✓ invólucro ```markdown aninhado, cerca órfã, front matter, `---`, tabelas e <br> saneados")


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
            ArtefatosDesignAgent(name="A080ArtefatosDesign"),
        ],
    )
    _, state = asyncio.run(_run(root))
    assert state["prototipo_arquivo"] == doc
    assert "Relatório do protótipo" in state["prototipo_relatorio"]
    assert state["diagramas_html"].count("<section>") == 1
    assert "prototipo_arquivo" not in "".join(load_prompt(f"design/{n}", **CONFIG_VARS) for n in ["088_qa_entregaveis.md"])
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
                EspelhoMiroAgent(name="A084EspelhoMiro"),
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
                EspelhoMiroAgent(name="A084EspelhoMiro"),
                EspelhoMiroAgent(name="A084EspelhoMiroRetrabalho"),
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
                EspelhoMiroAgent(name="A084EspelhoMiro"),
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

    assert e_mensagem_de_pulo("⏭️ `A120OnePagerPedagogico` não executado — pipeline bloqueado (x).")
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
            {"one_pager_pedagogico": "⏭️ `A120OnePagerPedagogico` não executado — pipeline bloqueado (x)."},
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
        # 6º ano, com o N/A do SAEB: desde 23/09/2026 o 5º ano sem descritor é amarelo, e este teste
        # não é sobre SAEB — é sobre a menção proibitiva ao WebSocket não contar como uso.
        "## 0. Identificação\n* Ano/série: [\"6EF\"]\n\n## 2. Currículo\n* EF06CO09 — Cultura Digital.\n"
        "* **Descritor SAEB:** N/A — ano não avaliado pelo SAEB.\n\n"
        "## 16. Requisitos técnicos e escopo\n* Sala sincronizada por polling HTTP em exp06ef1b_gates_turma; nunca WebSocket (ADR-93).\n"
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
def test_base_da_plataforma_lida_do_bucket_e_fixada_por_execucao():
    """06/10/2026: a cópia no git parou em 16/09 e a missão do 9º ano saiu pedindo `chatgpt`, ADR-108 e
    DS 0.2.2. A base agora vem do bucket (`prompts/base_plataforma.py`); aqui, da fotografia em
    `fixtures/base-plataforma`. Toda cópia que um prompt inclui tem de existir nela, o contrato tem de
    trazer as listas fechadas, e a falta da base é erro com mensagem — nunca cópia velha em silêncio."""
    import re as _re
    import tempfile
    import threading
    from prompts import PROMPTS_DIR, base_plataforma as bp, get_prompt_raw, load_prompt, save_prompt

    bp.esquecer_cache()
    base = bp.ler_atual()
    assert base.commit != "?" and base.ds_versao != "?", base
    c = bp.contrato(base)
    secoes = {s["secao"] for s in c["design_system"]["secoes"]}
    assert {"unooria", "unooriaai", "unoovista", "unoochat"} <= secoes, secoes
    assert c["adr"]["proxima"] == c["adr"]["ultima"] + 1
    assert str(c["portas"]["proxima_livre"]) not in {str(v) for v in c["portas"]["ocupadas"].values()}
    assert {"forms", "downloads"} <= set(c["manifesto"]["permissoes_iframe"])

    # toda cópia citada por um prompt existe na base publicada
    citados = set()
    for md in PROMPTS_DIR.rglob("*.md"):
        citados |= set(_re.findall(r"include:\s*references/plataforma/([\w.-]+\.md)", md.read_text(encoding="utf-8")))
    citados.discard("contrato-plataforma.md")
    faltando = sorted(n for n in citados if not (base.pasta_plataforma / "arquivos" / n).exists())
    assert not faltando, f"prompts incluem cópias que a plataforma não publica: {faltando}"

    # o contrato e o inventário chegam renderizados, com as chaves neutralizadas
    essencial = load_prompt("references/plataforma-unooria-essencial.md")
    assert "Contrato da plataforma" in essencial and "unooriaai" in essencial
    assert f"ADR-{c['adr']['proxima']}" in essencial
    assert "unooriaai" in get_prompt_raw("references/ds-componentes.md")
    from prompts import list_state_variables
    for copia in ("exemplo-juri-contrato-rotas.md", "openapi-indice.md", "agents-raiz.md"):
        sobra = list_state_variables(get_prompt_raw(f"references/plataforma/{copia}"))
        assert not sobra, f"{copia}: o ADK interpolaria {sobra}"

    # cada arquivo da base entra uma vez só por prompt
    prd = load_prompt("dev/113_prd_writer.md")
    assert prd.count("<!-- início de references/plataforma/contrato-plataforma.md -->") == 1

    # a base não se edita pela esteira
    try:
        save_prompt("references/plataforma/agents-raiz.md", "x")
        raise AssertionError("save_prompt gravou numa cópia da base")
    except ValueError:
        pass

    # sem base: erro que diz onde procurou
    with tempfile.TemporaryDirectory() as vazio:
        try:
            bp.ler_atual(Path(vazio))
            raise AssertionError("base ausente não pode ser silenciosa")
        except bp.BaseIndisponivel as exc:
            assert "atual.json" in str(exc) and "gcloud storage rsync" in str(exc)

    # a base fixada vale só para a thread da execução
    falsa = bp.Base(raiz=base.raiz, commit="outro", branch="b", data_commit="d", gerado_em="g",
                    pasta_plataforma=base.pasta_plataforma, ds_versao=base.ds_versao, ds_commit="x",
                    pasta_ds=base.pasta_ds)
    vista = {}
    bp.fixar(falsa)
    try:
        t2 = threading.Thread(target=lambda: vista.update(outra=bp.ativa().commit))
        t2.start(); t2.join()
        assert bp.ativa().commit == "outro" and vista["outra"] == base.commit
    finally:
        bp.fixar(None)
    print(f"   ✓ base da plataforma: {base.resumo()} · {len(citados)} cópias citadas, todas presentes")


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
            DiagnosticoAgent(name="A127Diagnostico", description="d"),
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
            BnccCheckAgent(name="A046BnccCheck", description="bncc", estrito=True),
            SaidaDeLoopAgent(
                name="A059SpecCheck", description="saida", rotulo="Spec",
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
            "- `secao_ds: unoovista`\n- `liberacao: por-turma`\n"
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
    from agents.dev import agentes_em_ordem, DEV_METADATA, build_dev_stage

    nomes = {m["id"] for m in DEV_METADATA}
    assert {"A113PrdWriter", "A114PrdCheck", "A118PrdRodada"} <= nomes, sorted(nomes)

    def achatar(agentes):
        for a in agentes:
            yield a
            yield from achatar(getattr(a, "sub_agents", []) or [])

    loop = [a for a in achatar([build_dev_stage()]) if a.name == "PrdLoop"]
    assert loop, "PrdLoop não está montado na etapa de dev"
    dentro = {a.name for a in achatar(loop[0].sub_agents)}
    assert {"A113PrdWriter", "A114PrdCheck", "A118PrdRodada"} <= dentro, sorted(dentro)
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

    revisor = metadata["produto/revisor_one_pager.md"]["name"]
    assert revisor.startswith("028"), revisor
    assert reusos["produto/revisor_one_pager.md"], "o reuso precisa ficar visível para quem edita"

    # o número do rótulo tem que crescer junto com o nome do arquivo, dentro de cada área
    import re

    from prompts import list_prompt_files

    for area, arquivos in list_prompt_files().items():
        numeros = []
        # prompt compartilhado por vários passos (revisor, bancas A–C, juízes) não leva número no nome do arquivo
        for f in sorted(a for a in arquivos if re.match(r"\d", a)):
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
    # `base` vazio: sem ele a saúde também conta as sessões do `output/` real da máquina, e o
    # teste passava ou falhava conforme o que o desenvolvedor tinha gerado.
    import tempfile
    from pathlib import Path
    vazio = Path(tempfile.mkdtemp())
    saude = saude_do_indice(cego, base=vazio)
    assert saude["cegas"] == 2 and saude["fracao_cega"] == 1.0
    assert "praticamente desligada" in (aviso_de_indice_cego(saude) or "")
    cheio = {"missoes": [{"slug": "a", "tipo_decisao": "escolher fonte", "porta_abstracao": "explicar",
                          "descoberta": "o feed esconde o que eu não sigo", "ambiente": "instanooria"}]}
    assert aviso_de_indice_cego(saude_do_indice(cheio, base=vazio)) is None
    # os dois defeitos juntos: um aviso não pode esconder o outro
    (vazio / "20260922-181029-exp06ef1b").mkdir()
    (vazio / "20260922-181029-exp06ef1b" / "estado.json").write_text("{}")
    ambos = aviso_de_indice_cego(saude_do_indice(cego, base=vazio)) or ""
    assert "praticamente desligada" in ambos and "exp06ef1b" in ambos, ambos

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
    assert "{gate_estrutural_rodada?}" in load_prompt("produto/026_gate_estrutural.md")

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
            "| Código | Momento em tela | Ação observável | O que não conta | Medida do bloco 9 | Canal de evidência | Regra ternária |\n"
            "|---|---|---|---|---|---|---|\n"
            "| `EF06CO09` | `E3-ALU-01` (Decidir) | fixa 1 post | rolar o feed | `posts_no_mural` | A + B | "
            "Atingiu: fixa post com fonte aberta · Em processo: fixa sem abrir a fonte · Não atingiu: não salva |\n")
    assert validar(base)["status"] == "aprovado", validar(base)["achados"]

    # (a) `scored` exige os dois sinais que a própria definição do bloco 9 pede
    um_sinal = base.replace("`salvar:post` + `submeter:mural`", "`salvar:post`")
    assert "scored-1-sinal" in {a["codigo"] for a in validar(um_sinal)["achados"]}

    # (b) habilidade declarada sem dado que a meça é currículo no papel
    sem_medida = base.replace("| `posts_no_mural` | A + B |", "| — | A + B |")
    assert "habilidade-sem-medida" in {a["codigo"] for a in validar(sem_medida)["achados"]}

    # (b') v1.21 — a matriz diz de onde sai o nível e a regra que o separa, por extenso
    marcador_antigo = base.replace("| Canal de evidência | Regra ternária |", "| Marcador |").replace(
        "| A + B | Atingiu: fixa post com fonte aberta · Em processo: fixa sem abrir a fonte · Não atingiu: não salva |",
        "| ternário |")
    codigos = {a["codigo"] for a in validar(marcador_antigo)["achados"]}
    assert {"habilidade-sem-canal", "regra-ternaria-ausente"} <= codigos, codigos
    so_escala = base.replace("Atingiu: fixa post com fonte aberta · Em processo: fixa sem abrir a fonte · Não atingiu: não salva",
                             "ternário 🟢🟡🔴")
    assert "regra-ternaria-ausente" in {a["codigo"] for a in validar(so_escala)["achados"]}
    # o Canal B vale no 1º–2º ano: três alternativas visíveis ao mesmo tempo cabem no teto da
    # faixa (3.5, opção visível +1) — conferir a tela é dos pareceres, não deste gate
    segundo_ano = "## 0. Identificação\nSéries: `[\"2EF\"]`\n" + base
    assert validar(segundo_ano)["status"] == "aprovado", validar(segundo_ano)["achados"]

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

    qa = load_prompt("design/088_qa_entregaveis.md")
    # F1 — não havia NENHUMA linha de acessibilidade contável na esteira: era texto sem verificação
    assert "4,5:1" in qa and "Ordem de foco" in qa, "contraste e ordem de foco não são contáveis"
    assert "64×64" in qa, "o alvo de toque já existia e não pode ter saído"
    # A-01 (auditoria de 23/09/2026): as linhas contáveis viviam dentro da D8b, que só roda
    # com CAA `concluido` — 4 das 14 missões medidas saíram sem nenhuma verificação. Elas têm de
    # estar numa dimensão que roda sempre, e a D8b não pode voltar a ser a única dona delas.
    import re as _re
    d4a = _re.search(r"\*\*D4a — Acessibilidade.*?(?=\n\*\*D5 —)", qa, _re.S)
    assert d4a, "a dimensão de acessibilidade de toda missão (D4a) sumiu"
    for linha in ("4,5:1", "64×64", "Ordem de foco", "nada-so-por-cor"):
        assert linha in d4a.group(0), f"{linha} saiu da D4a"
    assert "Roda sempre" in d4a.group(0)
    d8b = _re.search(r"\*\*D8b — Camada CAA.*?(?=\n\n)", qa, _re.S).group(0)
    assert "4,5:1" not in d8b, "o contraste voltou a depender da camada CAA"
    assert "D4a" in qa.split("## Veredito por dimensão")[1], "a D4a não aparece no template de saída"

    # F4 — o micro-gate testa spoiler no núcleo e nada testava depois: copy, tela e protótipo
    # podiam entregar de graça o que a missão existe para a criança descobrir
    assert "D3b" in qa and "Spoiler a jusante" in qa

    # F5 — dois a quatro por aparelho é o primeiro cenário da escola pública, não variação de luxo
    telas = load_prompt("design/075_telas.md")
    assert "estado degradado 2–4 por aparelho" in telas
    # desde 07/10/2026 nenhuma tela se corta (o Stitch saía com 27% a 68% do inventário): o 2–4 está
    # entre as telas obrigatórias como todas as outras
    i_regra = telas.index("todas, sem priorizar nem resumir")
    i_degradado = telas.index("estado degradado 2–4 por aparelho")
    assert i_degradado > i_regra, "o 2–4 precisa estar sob a regra de que nenhuma tela se corta"

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
    from tools.kpis import validar_kpis, extrair_perguntas_do_briefing, catalogo, sinais_exigidos

    # os sinais universais das transversais de dono `missao`, copiados do catálogo como o redator faria
    universais = "".join(
        f"| {s} | {catalogo()['sinais'][s].get('verbo', '—')} | "
        f"{catalogo()['sinais'][s]['objeto'].replace('<expId>', 'exp06ef1b')} | catálogo "
        f"| `{{\"x\": 1}}` | — | painel de produto (PostHog) |\n"
        for s in sorted(sinais_exigidos(False)))
    bom = ("## 2. Objetivos\n"
           "| KPI | Pergunta | Decisão | Corte | Tela | Evento(s) | Como calcula | Baseline | Alvo | Prazo |\n"
           "|---|---|---|---|---|---|---|---|---|---|\n"
           "| KPI-01 | quantas turmas chegam ao fim? | <50% encurta | missao · serie | E3-ALU-02 | EVT-005 "
           "| count(EVT-005) | sem baseline — primeira medição | sem meta — primeira medição | 2 meses |\n"
           "## 13. Eventos\n"
           "| EVT | Verbo | Objeto | Quando dispara | resultado | contexto | Onde é lido |\n|---|---|---|---|---|---|---|\n"
           "| EVT-005 | interacted | mural:salvar | Toque em Salvar, na tela E3-ALU-02 | `{\"ok\": true}` | `{\"ms\": 1}` | `exp06ef1b_sessoes` |\n"
           + universais)
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

    # a mensagem traz a saída, não só o erro (a rodada 2 de 23/09 deixou os dois que não traziam)
    msg = [a["resumo"] for a in validar_kpis(bom.replace("na tela E3-ALU-02", "na tela E3-ALU-01"))["achados"]
           if a["codigo"] == "kpi-tela-divergente"][0]
    assert "Nenhum evento da tabela dispara nessa tela" in msg, msg
    msg = [a["resumo"] for a in validar_kpis(bom.replace("count(EVT-005)", "count(contexto.detalhes)"))["achados"]
           if a["codigo"] == "payload-nao-computa"][0]
    assert "`ms`" in msg and "Coluna de tabela do módulo não é campo do evento" in msg, msg

    # o catálogo: sinal universal ausente, reaproveitado para outro evento, e KPI herdado com evento próprio
    assert "sinal-universal-ausente" in cods(bom.replace("| EVT-U04 |", "| EVT-904 |"))
    assert "sinal-universal-divergente" in cods(bom.replace("etapa:entrar", "sessao:iniciar"))
    herdado = ("\n| KPI | PQ | Pergunta | Decisão | Corte | Tela | Evento(s) | Como calcula | Baseline | Alvo | Prazo |\n"
               "|---|---|---|---|---|---|---|---|---|---|---|\n"
               "| KPI-02 | T7 | De cada X turmas liberadas, quantas chegam ao fim da missão? | <50% encurta | missao "
               "| — | {evt} | turmas com EVT-U03 / turmas com EVT-U01 | sem baseline — primeira medição | sem meta — primeira medição | 2 meses |\n\n")
    com = lambda evt, t="T7": bom.replace("## 13. Eventos", herdado.format(evt=evt).replace("T7", t) + "## 13. Eventos")
    assert validar_kpis(com("EVT-U01, EVT-U03"))["status"] == "aprovado", validar_kpis(com("EVT-U01, EVT-U03"))["achados"]
    assert "kpi-herdada-evento" in cods(com("EVT-U01, EVT-005")), "o caso de 23/09: a lupa medindo T1"
    assert "kpi-herdada-plataforma" in cods(com("EVT-U01", t="T1"))
    assert "kpi-herdada-inexistente" in cods(com("EVT-U01", t="T30"))

    # o PO escreve em português; a esteira normaliza
    tabela = extrair_perguntas_do_briefing(
        "## Perguntas de produto\nAulas: 1\nHerdar: T1, T2\n"
        "- quantas duplas trocam de escolha? → decisão: se <20%, reforçar a mediação → corte: turma\n")
    assert "declared_lessons: 1" in tabela and "PQ-01" in tabela and "| PO |" in tabela
    assert extrair_perguntas_do_briefing("briefing sem o bloco") == ""

    print("   ✓ KPI: pergunta, decisão, corte, evento na tela certa e baseline honesto — tudo conferido")


def test_kpi_payload_por_calculo_e_evt_p_sem_payload():
    """PRD da exp01ef1b (Detetive da Foto, 29/09/2026): 5 bloqueios `payload-nao-computa`, 3 falsos.

    O gate cobrava cada campo do cálculo de cada evento da célula (KPI-04 com U04 e U05, cada campo
    no seu), e a tabela «Sinais do professor» zerava o payload dos `EVT-P`. Os 2 que ficaram são
    reais: `resultado.tokens` num `EVT-P02` — o sinal do professor é coluna, não tem payload.
    """
    from tools.kpis import validar_kpis

    cab = "| KPI | Pergunta | Decisão | Corte | Tela | Evento(s) | Como calcula | Baseline | Alvo | Prazo |\n|---|---|---|---|---|---|---|---|---|---|\n"
    kpi = "| {id} | pergunta? | decide | missao | — | {evt} | {calc} | sem baseline — primeira medição | 1 | piloto |\n"
    eventos = (
        "\n| EVT | Verbo | Objeto | Quando dispara | `resultado` | `contexto` | Onde é lido |\n|---|---|---|---|---|---|---|\n"
        "| `EVT-U02` | progressed | etapa:entrar | Ao entrar em E2 | `{\"etapa\": \"E2\"}` | `{\"pedagogical_role\": \"core_action\"}` | painel de produto (PostHog) |\n"
        "| `EVT-U04` | interacted | aviso:inatividade | Aviso na E3 | `{\"segundos_sem_acao\": 20}` | `{\"etapa\": \"E3\"}` | painel de produto (PostHog) |\n"
        "| `EVT-U05` | attempted | erro:exibir | Erro na E4 | `{\"codigo\": \"sem-sinal\"}` | `{\"etapa\": \"E4\"}` | painel de produto (PostHog) |\n"
        "| `EVT-P02` | interacted | conteudo:gerar | POST gerar-conteudo | `{\"tokens\": 3500}` | — | `exp01ef1b_conteudo_turma.geracoes` |\n"
        "\n| Sinal | Objeto | Quando grava | Onde fica | Responde |\n|---|---|---|---|---|\n"
        "| `EVT-P02` | `conteudo:gerar` | A cada POST | `exp01ef1b_conteudo_turma.tokens_usados` (soma) | T20 |\n")

    def achados(evt, calc):
        prd = cab + kpi.format(id="KPI-01", evt=evt, calc=calc) + eventos
        return [a for a in validar_kpis(prd)["achados"] if a["codigo"] == "payload-nao-computa"]

    # cada campo no evento que o carrega: não é defeito
    assert not achados("`EVT-U04`, `EVT-U05`", "count(`EVT-U05` com `resultado.codigo`) vs count(`EVT-U04` com `resultado.segundos_sem_acao`)")
    # evento na célula que o cálculo não usa não paga pelo campo
    assert not achados("`EVT-U02`, `EVT-U04`", "sum(`EVT-U04` com `resultado.segundos_sem_acao`)")
    # campo que nenhum evento do cálculo carrega continua pego
    assert achados("`EVT-U04`", "count(`EVT-U04` com `resultado.codigo`)")
    # `EVT-P` não tem payload, mesmo que o redator o escreva na tabela — e a mensagem diz onde ele grava
    msg = achados("`EVT-P02`", "sum(`resultado.tokens` em `EVT-P02`)")
    assert msg and "sinal do professor" in msg[0]["resumo"] and "tokens_usados" in msg[0]["resumo"], msg
    # o cálculo com a coluna passa
    assert not achados("`EVT-P02`", "sum(`exp01ef1b_conteudo_turma.tokens_usados` de `EVT-P02`)")


def test_custo_e_tendencia_da_esteira():
    """Quanto custa gerar uma missão, e estamos melhorando? Duas perguntas sem resposta até agora."""
    import tempfile, pathlib as _p
    from tools import historico
    from tools.diagnostico import bloco_de_execucao

    # O `usage_metadata` de cada evento era descartado: ninguém sabia o custo nem qual agente pesa
    st = {"execucao": {"modelo": "gemini-3.8-flash", "seed_juiz": 20260923, "temperatura_juiz": 0.1,
                       "duracao_s": 742.3, "tokens": {"entrada": 1_840_000, "saida": 210_000, "chamadas": 41},
                       "tokens_por_agente": {"A113PrdWriter": {"entrada": 390_000, "saida": 48_000, "chamadas": 2}}}}
    bloco = bloco_de_execucao(st)
    assert "2.050.000" in bloco, "o total de tokens precisa aparecer no dossiê"
    assert "seed `20260923`" in bloco, "sem seed e modelo, duas execuções não são comparáveis"
    assert "A113PrdWriter" in bloco and "390.000" in bloco
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
            "| Código | Momento em tela | Ação observável | O que não conta | Medida do bloco 9 | Canal de evidência | Regra ternária |\n"
            "|---|---|---|---|---|---|---|\n| `EF06CO09` | `E3-ALU-02` | fixa | rola | `posts` | A | "
            "Atingiu: fixa com fonte · Em processo: fixa sem fonte · Não atingiu: não fixa |\n")

    root = SequentialAgent(name="R", sub_agents=[
        FakeAgent(name="Spec", key="spec_missao", text=spec),
        FakeAgent(name="Jornada", key="jornada_telas", text="| E1-ALU-01 | abertura |\n"),
        FakeAgent(name="Proto", key="prototipo_arquivo", text="<html><body>E1-ALU-01</body></html>"),
        FakeAgent(name="Prd", key="prd_final", text="# PRD\n`exp06ef1b_sessoes`\n"),
        FakeAgent(name="V1", key="validacao_produto_narrativa",
                  text='```json\n{"status": "aprovado", "achados": []}\n```'),
        RastroCheckAgent(name="A048EvidenciaCheck", modo="evidencia", rotulo="Matriz de evidência",
                         report_key="evidencia_report", status_key="evidencia_status", estrito=False),
        RastroCheckAgent(name="A115KpisCheck", modo="kpis", rotulo="KPI",
                         report_key="kpis_report", status_key="kpis_status", estrito=False),
        RastroCheckAgent(name="A050PerguntasCheck", modo="perguntas", rotulo="Perguntas de produto (9f)",
                         report_key="perguntas_report", status_key="perguntas_status", estrito=False),
        PrototipoLintAgent(name="A081PrototipoLint"),
        ConsolidacaoBancaAgent(name="A110", fontes=["validacao_produto_narrativa"]),
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
- `perguntas_herdadas: T7, T8, T9, T10, T11, T12, T14, T15, T16, T17, T19, T20`

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
| attempted | missao:iniciar | primeira tela do estudante | {"retomada": false} | {"etapa": "E1"} | analítico | painel de produto (PostHog) |
| progressed | etapa:entrar | ao entrar em cada etapa | {"etapa": "E2"} | {"pedagogical_role": "core_action"} | analítico | painel de produto (PostHog) |
| interacted | aviso:inatividade | ao exibir o aviso | {"segundos_sem_acao": 90} | {"etapa": "E2"} | analítico | painel de produto (PostHog) |
| attempted | erro:exibir | ao exibir erro diegético | {"codigo": "sem-sinal"} | {"etapa": "E2"} | analítico | painel de produto (PostHog) |
"""


def test_transversais_do_po_por_grupo_de_missao():
    """A revisão do PO de 24/09/2026 deu a cada pergunta grupo, pilar e decisão. O grupo muda quem
    herda: T15, T16 e T20 só na missão com customização de tema por IA, T21 só na IA conversacional.
    Antes, toda missão era cobrada de `geracoes` de um `gerar-conteudo` que podia nem ter."""
    from tools.kpis import catalogo, sinais_exigidos, condicoes_da_missao, validar_9f

    c = catalogo()
    assert len(c["transversais"]) == 21 and len(c["perguntas"]) == 21
    for t, info in c["transversais"].items():
        assert info.get("grupo") in ("universal", "customizacao_tema", "ia_conversacional"), t
        assert info.get("pilar"), f"{t} sem pilar"
    assert {t for t, i in c["transversais"].items() if i["grupo"] == "customizacao_tema"} == {"T15", "T16", "T20"}
    assert {t for t, i in c["transversais"].items() if i["grupo"] == "ia_conversacional"} == {"T21"}
    # as decisões são as do PO: nenhuma proposta do agente sobra na tabela das transversais
    canon = (Path(__file__).parent / "prompts/references/perguntas-de-produto.md").read_text(encoding="utf-8")
    tabela = canon.split("## O catálogo de sinais universais")[0].split("| `T1` |", 1)[1]
    assert "PROPOSTA" not in tabela, "sobrou decisão proposta pelo agente na tabela do PO"

    universal = set(sinais_exigidos(False, False))
    assert not universal & {"EVT-P01", "EVT-P02", "EVT-P03", "EVT-P06", "EVT-U06"}, universal
    assert {"EVT-P01", "EVT-P02", "EVT-P03"} <= set(sinais_exigidos(False, True))

    # o grupo sai da ficha de herdadas; sem ela, do preparo com gerar-conteudo
    assert condicoes_da_missao("- `perguntas_herdadas: T7, T8, T16`") == {"customizacao_tema"}
    assert condicoes_da_missao("- `perguntas_herdadas: T7, T8`\nO professor chama gerar-conteudo.") == set()
    assert condicoes_da_missao("preparo: POST /x/turmas/:id/gerar-conteudo") == {"customizacao_tema"}
    assert condicoes_da_missao("- `perguntas_herdadas: T7, T21`") == {"ia_conversacional"}

    # missão sem customização: herdar só as universais não é falta
    sem_custom = _SPEC_9F.replace("T14, T15, T16, T17, T19, T20", "T14, T17, T19")
    assert sem_custom != _SPEC_9F
    assert "herdada-faltando" not in [a["codigo"] for a in validar_9f(sem_custom)["achados"]]
    # com o preparo por IA na spec, deixar T15/T16/T20 de fora é falta
    com_preparo = sem_custom + "\nPreparo: `POST /exp09ef1b/turmas/:turmaId/gerar-conteudo`.\n"
    assert "herdada-faltando" in [a["codigo"] for a in validar_9f(com_preparo)["achados"]]
    print("   ✓ transversais do PO: grupo, pilar e decisão; sinais cobrados só do grupo da missão")


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

    # As transversais do PO: as de dono `missao` são herdadas inteiras, as de `plataforma` não se
    # declaram, e o evento universal do estudante nasce no bloco 9 com o verbo e o objeto do catálogo.
    def cods(txt):
        return [a["codigo"] for a in validar_9f(txt)["achados"]]
    assert "herdada-plataforma" in cods(_SPEC_9F.replace("T7, T8,", "T1, T7, T8,"))
    assert "herdada-faltando" in cods(_SPEC_9F.replace("T7, T8,", "T8,"))
    assert "herdada-inexistente" in cods(_SPEC_9F.replace("T7, T8,", "T30, T7, T8,"))
    assert "sinal-universal-ausente" in cods(_SPEC_9F.replace("| progressed | etapa:entrar |", "| progressed | etapa:outra |"))

    print("   ✓ 9f: cinco perguntas, decisão com limiar, ação que existe no bloco 9 e mede; herdadas e sinais do catálogo")


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


def test_ia_ao_estudante_e_decidida_pela_spec():
    """24/09/2026: o PRD pôs `EVT-U06` (IA responde) no KPI de espera de uma missão cuja IA só atua no
    preparo docente; o gate leu "o PRD emite sinal de IA" e exigiu o `EVT-P06` de custo. Mandava
    acrescentar um evento de algo que não existe. A spec decide; o PRD que contradiz é o achado."""
    from tools.kpis import validar_kpis

    prd = """
| ID | Verbo | Objeto | Quando dispara | Resultado | Contexto | Onde é lido |
|---|---|---|---|---|---|---|
| EVT-U06 | attempted | ia:responder | resposta da IA | {"latencia_ms": 1800} | — | painel de produto |
"""
    sem_t21 = "- `perguntas_herdadas`: T7, T12, T20\n"
    com_t21 = "- `perguntas_herdadas`: T7, T12, T20, T21\n"

    sem = validar_kpis(prd, sem_t21)["achados"]
    assert any(a["codigo"] == "sinal-ia-sem-ia-ao-estudante" and "Tire o evento" in a["resumo"] for a in sem)
    assert not any("EVT-P06" in a["resumo"] and a["codigo"] == "sinal-universal-ausente" for a in sem)

    com = validar_kpis(prd, com_t21)["achados"]
    assert not any(a["codigo"] == "sinal-ia-sem-ia-ao-estudante" for a in com)
    assert any(a["codigo"] == "sinal-universal-ausente" and "EVT-P06" in a["resumo"] for a in com)

    # sem spec (correção que só refaz o PRD), o próprio PRD continua sendo a pista
    assert any("EVT-P06" in a["resumo"] for a in validar_kpis(prd, "")["achados"])
    print("   ✓ IA ao estudante: a spec decide, e o PRD que a contradiz é apontado")


def test_sinais_do_professor_em_tabela_propria_e_prosa_nao_emite():
    """24/09/2026, segunda rodada da mesma missão: o PRD copiou a tabela de `EVT-P*` do catálogo à
    risca (coluna «Quando grava») e o gate, que só lia a de «Quando dispara», deu 13 achados de sinal
    inexistente. E o changelog que dizia "expurgo de `EVT-U06`" contava como emissão do evento."""
    from tools.kpis import validar_kpis

    prd = """
| KPI | PQ | Pergunta | Decisão | Corte | Tela | Evento(s) | Como calcula | Baseline | Alvo | Prazo |
|---|---|---|---|---|---|---|---|---|---|---|
| KPI-01 | T15 | De X professores que acessaram a missão, quantos iniciaram a customização? | <50% → rever | missao | — | `EVT-P01` | razão | sem baseline — primeira medição | 50% | 11/2026 |

| ID | Verbo | Objeto | Quando dispara | Resultado | Contexto | Onde é lido |
|---|---|---|---|---|---|---|
| EVT-001 | progressed | aha:revelacao | E4-ALU-02 | {"ok": true} | — | exp09ef1b_sessoes |

| Sinal | Objeto | Quando grava | Onde fica | Responde |
|---|---|---|---|---|
| `EVT-P01` | `preparo:iniciar` | Primeira chamada de preparo da turma | `exp09ef1b_conteudo_turma.preparo_iniciado_em` | T14, T15 |

- O que mudou nesta versão: expurgo definitivo de `EVT-U06`, a IA não responde ao estudante.
"""
    achados = validar_kpis(prd, "- `perguntas_herdadas`: T15\n")["achados"]
    codigos = {a["codigo"] for a in achados}
    assert "kpi-evento-inexistente" not in codigos, achados
    assert not any(a["codigo"] == "sinal-universal-ausente" and "EVT-P01" in a["resumo"] for a in achados)
    assert "sinal-ia-sem-ia-ao-estudante" not in codigos
    print("   ✓ EVT-P* na tabela do catálogo contam, e citar um evento na prosa não o emite")


def test_sinal_do_professor_em_lista_e_rota_proibida():
    """24/09/2026, terceira rodada: os `EVT-P*` vieram em lista (id e objeto do catálogo) e o gate só
    lia tabelas; e a linha em que o redator PROIBIA as rotas erradas ("**NÃO** utilizar `PUT /salas`")
    virava `rota-inexistente`. A rota errada usada de verdade continua bloqueando."""
    from tools.kpis import validar_kpis
    from tools.rotas_plataforma import validar_rotas

    prd = """
| KPI | PQ | Pergunta | Decisão | Corte | Tela | Evento(s) | Como calcula | Baseline | Alvo | Prazo |
|---|---|---|---|---|---|---|---|---|---|---|
| KPI-01 | T15 | De X professores que acessaram a missão, quantos iniciaram a customização? | <50% → rever | missao | — | `EVT-P01` | razão | sem baseline — primeira medição | 50% | 11/2026 |

| ID | Verbo | Objeto | Quando dispara | Resultado | Contexto | Onde é lido |
|---|---|---|---|---|---|---|
| EVT-001 | progressed | aha:revelacao | E4-ALU-02 | {"ok": true} | — | exp09ef1b_sessoes |

- `EVT-P01` (`preparo:iniciar`): gravado em `exp09ef1b_conteudo_turma.preparo_iniciado_em`. (Alimenta `T14`, `T15`).
"""
    achados = validar_kpis(prd, "- `perguntas_herdadas`: T15\n")["achados"]
    assert not [a for a in achados if "EVT-P01" in a["resumo"]], achados
    # citação solta na prosa não declara o sinal
    solta = prd.replace("- `EVT-P01` (`preparo:iniciar`)", "O `EVT-P01` foi revisto")
    assert any(a["codigo"] == "kpi-evento-inexistente" for a in validar_kpis(solta, "")["achados"])

    proibida = "- **NÃO** utilizar rotas inexistentes como `PUT /salas` ou `GET /turmas/:id/painel`.\n"
    assert not validar_rotas(proibida)
    assert validar_rotas("O professor chama `POST /salas/turma/:turmaId/missoes/exp04ef3b`.\n")
    print("   ✓ EVT-P* em lista contam, e rota citada para ser proibida não é rota em uso")


def test_campo_dados_so_no_evento_e_nao_no_concluir_da_sdk():
    """24/09/2026: o handoff chamava `handle.concluir({ score: 100, dados: {...} })` — assinatura
    certa da SDK (`packages/sdk/src/types.ts`) — e o gate de telemetria bloqueou como se fosse um
    evento com `dados`. Pegava até a prosa "linguagem de dados:"."""
    from tools.rastro import validar_telemetria

    def pega(texto):
        return "campo-dados" in [a["codigo"] for a in validar_telemetria(texto)["achados"]]

    assert pega("O front chama `track('interacted', 'tabela:abrir', { dados: { etapa: 'E1' } })`.")
    assert pega("| ID | Verbo | Objeto | dados |\n|---|---|---|---|\n| EVT-001 | x | y | z |\n")
    assert not pega("Invoca `handle.concluir({ score: 100, dados: { conclusao: true } })` da SDK.")
    assert not pega("- **Correção da linguagem pedagógica de dados:** trocada a expressão.")
    print("   ✓ campo `dados` só bloqueia no evento, não no concluir() da SDK nem na prosa")


def test_coluna_kpi_na_tabela_de_eventos_e_rota_proibida_no_changelog():
    """24/09/2026, refazer de Dev da exp04ef3b já com o fix do `dados`: o PRD pôs na tabela de eventos
    uma coluna «KPI» de volta, e o gate leu cada evento como um KPI sem pergunta, decisão nem baseline
    (27 bloqueios, com os 11 KPIs completos). E a rota errada citada para ser vedada — "❌ NÃO inventar
    rota" e "menção indevida" no changelog — virava `rota-verbo-errado`."""
    from tools.kpis import validar_kpis
    from tools.rotas_plataforma import validar_rotas

    kpi = ("| KPI | PQ | Pergunta | Decisão | Corte | Tela | Evento(s) | Como calcula | Baseline | Alvo | Prazo |\n"
           "|---|---|---|---|---|---|---|---|---|---|---|\n"
           "| KPI-08 | PQ-02 | Quantos estudantes abrem a tabela de apuração antes de selecionar o rascunho do post? "
           "| `<40%` indica affordance da gaveta retrátil invisível | turma | `E1-ALU-01` | `EVT-001` "
           "| count(`EVT-001`) / total(`EVT-U01`) | sem baseline — primeira medição | ≥ 60% | Piloto |\n\n")
    eventos = ("| Evento | Verbo | Objeto | Quando dispara | `resultado` | `contexto` | Caminho | Onde é lido | Retenção | KPI |\n"
               "|---|---|---|---|---|---|---|---|---|---|\n"
               "| `EVT-001` | `interacted` | `dm:abrir_tabela` | Estudante toca na aba de apuração na E1 "
               "| `{\"tempo_ate_abrir_s\": 4}` | `{\"etapa\": \"E1\"}` | operacional "
               "| `exp04ef3b_sessoes.abriu_tabela` / `GET /painel` | 1 ano letivo | KPI-08 |\n")
    achados = validar_kpis(kpi + eventos)["achados"]
    falsos = {"kpi-sem-pergunta", "kpi-sem-decisao", "baseline-ausente"}
    assert not [a for a in achados if a["codigo"] in falsos], achados
    # o KPI de verdade sem pergunta continua pego
    sem_pergunta = kpi.replace("| Quantos estudantes abrem a tabela de apuração antes de selecionar o rascunho do post? ", "|  ")
    assert "kpi-sem-pergunta" in {a["codigo"] for a in validar_kpis(sem_pergunta + eventos)["achados"]}

    assert not validar_rotas("- ❌ NÃO inventar rota `DELETE /turmas/:turmaId`. A limpeza para segunda aplicação "
                             "é no módulo da própria missão: `DELETE /exp04ef3b/turmas/:turmaId`.\n")
    assert not validar_rotas("| `0.1.0` | 2026-09-24 | PRD Writer | Substituição da menção indevida a "
                             "`DELETE /turmas/:id` pela rota canônica do módulo `DELETE /exp04ef3b/turmas/:turmaId`. |\n")
    assert validar_rotas("Ao fim, `DELETE /turmas/:id`.\n"), "a rota errada usada de verdade continua bloqueando"
    print("   ✓ coluna KPI na tabela de eventos não vira KPI, e rota vedada no changelog não é rota em uso")


def test_nome_do_marcador_entre_crases_nao_e_pendencia():
    """24/09/2026: "Todos os marcadores `[NEEDS CLARIFICATION]` foram saneados" deixava o PRD 🟡 por
    uma pendência humana que a própria frase dizia não existir."""
    from tools.rastro import varrer_lacunas

    def achados(texto):
        return varrer_lacunas([{"chave": "x", "rotulo": "X", "etapa_padrao": "dev"}], {"x": texto})["achados"]

    assert not achados("- Nenhuma questão aberta. Todos os marcadores `[NEEDS CLARIFICATION]` foram saneados.\n")
    assert achados("A rota do painel não foi confirmada. [NEEDS CLARIFICATION]\n")
    assert achados("Rota: `[NEEDS CLARIFICATION: qual endpoint lê a turma, dono: dev]`\n")
    print("   ✓ o nome do marcador citado entre crases não vira pendência")


def test_todo_relatorio_de_gate_tem_onde_aparecer_na_tela():
    """24/09/2026: o gate de KPIs bloqueava o Dev e a tela não tinha passo para mostrar o relatório —
    ele não estava nos metadados. O lint do protótipo estava igual. Relatório novo sem passo falha aqui."""
    from pipeline.orchestrator import create_mission_orchestrator, get_pipeline_agents_metadata, iter_agent_tree

    mostrados = {m["output_key"] for m in get_pipeline_agents_metadata(active_only=False)}
    invisiveis = sorted({f"{a.name} → {a.report_key}" for _, a in iter_agent_tree(create_mission_orchestrator())
                         if getattr(a, "report_key", None) and a.report_key not in mostrados})
    assert not invisiveis, invisiveis
    print("   ✓ todo relatório de gate tem um passo na tela")


def test_todo_gate_gravado_aparece_no_dossie():
    """O cruzamento da auditoria de 23/09/2026, como teste: todo `status_key` que um agente da
    árvore grava está no dossiê. Eram três fora, e um deles reprovava protótipo sem que quem lia
    o diagnóstico soubesse. Gate novo que nascer invisível falha aqui."""
    from pipeline.orchestrator import create_mission_orchestrator, iter_agent_tree
    from tools.diagnostico import CONSULTIVOS, GATES

    # gravados DEPOIS do diagnóstico, ou o próprio diagnóstico: não cabem nele por construção
    fora_por_construcao = {"catalogo_status", "diagnostico_status"}
    consultivos = {c["chave"].replace("_report", "_status") for c in CONSULTIVOS}
    gravados = {getattr(a, "status_key", "") for _, a in iter_agent_tree(
        create_mission_orchestrator(stages=["produto", "design", "dev"]))} - {"", None}
    no_dossie = {g["status"] for g in GATES}
    invisiveis = gravados - no_dossie - consultivos - fora_por_construcao
    assert not invisiveis, f"gates que gravam status e não aparecem no dossiê: {sorted(invisiveis)}"
    print("   ✓ todo gate gravado aparece no dossiê (catálogo e diagnóstico fora por construção)")


def test_lint_do_prototipo_roda_de_novo_no_retrabalho():
    """O retrabalho reconstruía o protótipo e o QA da rodada 2 lia o lint da rodada 1 — sobre o
    HTML velho — com a instrução de tratá-lo como fato."""
    from agents.design import POSFIXO_RETRABALHO, _agentes_de_retrabalho

    assert "A081PrototipoLintRetrabalho" in POSFIXO_RETRABALHO
    # depois de separar o HTML do relatório, senão lint o documento antigo de novo
    assert POSFIXO_RETRABALHO.index("A080ArtefatosDesignRetrabalho") < POSFIXO_RETRABALHO.index("A081PrototipoLintRetrabalho")
    nomes = {a.name for a in _agentes_de_retrabalho()}
    assert set(POSFIXO_RETRABALHO) <= nomes, f"posfixo sem agente: {set(POSFIXO_RETRABALHO) - nomes}"
    print("   ✓ o lint do protótipo roda de novo depois de todo retrabalho de design")


def test_brief_ausente_nao_sai_verde():
    """Sem o brief, o split escrevia ⚠️ no log e gravava o status do ENVELOPE do one-pager:
    `aprovado`. O GAP-09 voltava com cara de sucesso."""
    from agents.produto import get_brief_escopo_split

    envelope = '```json\n{"agente": "secoes-apoio", "status": "aprovado"}\n```'
    sem = asyncio.run(_run(SequentialAgent(name="R", sub_agents=[
        FakeAgent(name="A014", key="one_pager", text="# One-pager\n\nSó o canônico.\n\n" + envelope),
        get_brief_escopo_split(),
    ])))[1]
    assert sem["brief_escopo_status"] == "amarelo", sem["brief_escopo_status"]
    assert any(a["codigo"] == "secao-ausente" for a in sem["brief_escopo_status_envelope"]["achados"])

    brief = "**MISSÃO DIGITAL UNOORIA · BRIEFING DE ESCOPO**\n\n" + ("Escopo da missão. " * 20)
    com = asyncio.run(_run(SequentialAgent(name="R", sub_agents=[
        FakeAgent(name="A014", key="one_pager", text="# One-pager\n\n" + brief + "\n\n" + envelope),
        get_brief_escopo_split(),
    ])))[1]
    assert com["brief_escopo_status"] == "aprovado" and com.get("brief_escopo")

    # como as duas rodadas de 23/09 escreveram: título em heading, e o one-pager sem envelope
    # (é documento, não veredito) — antes, brief nunca separado e `envelope-ilegivel` sempre
    heading = "# MISSÃO DIGITAL UNOORIA · BRIEFING DE ESCOPO (LEITURA RÁPIDA)\n\n" + ("Escopo da missão. " * 20)
    h = asyncio.run(_run(SequentialAgent(name="R", sub_agents=[
        FakeAgent(name="A014", key="one_pager", text="# One-pager\n\nSó o canônico.\n\n" + heading),
        get_brief_escopo_split(),
    ])))[1]
    assert h["brief_escopo_status"] == "aprovado" and h["brief_escopo"].startswith("Escopo"), h.get("brief_escopo_status")
    assert not h["brief_escopo_status_envelope"].get("achados"), h["brief_escopo_status_envelope"]
    print("   ✓ brief de escopo ausente sai 🟡 com achado, presente sai verde — em negrito ou heading")



def test_indice_defasado_chega_ao_micro_gate_e_ao_dossie():
    """O caso de produção em 23/09/2026: 14 sessões no bucket e 1 missão no índice. Nenhuma linha
    furada, fração cega 0%, e portanto nenhum aviso — o V5 comparava a missão nova contra UMA. E o
    aviso que existia só saía no relatório do catálogo, que roda depois do dossiê."""
    import os
    import tempfile
    from pathlib import Path

    from agents.checkers import VizinhasCatalogoAgent
    from tools import catalogo as cat

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        cat.registrar(_ficha(), base=base)  # só a exp06ef1b está no índice, e completa
        for pasta in ("20260922-181029-exp06ef1b", "20260922-004159-exp05ef1b", "20260921-124345-exp01ef1b"):
            (base / pasta).mkdir()
            (base / pasta / "estado.json").write_text("{}")
        (base / "20260922-102140-exp02ef1b").mkdir()   # sem estado.json: execução que não terminou
        (base / "amostra-identidade-visual").mkdir()   # pasta que não é sessão

        saude = cat.saude_do_indice(base=base)
        assert saude["fracao_cega"] == 0.0, "o caso é justamente o de nenhuma linha furada"
        assert saude["fora_do_indice"] == ["exp01ef1b", "exp05ef1b"], saude["fora_do_indice"]

        antes = os.environ.get("OUTPUT_DIR")
        os.environ["OUTPUT_DIR"] = tmp
        try:
            _, st = asyncio.run(_run(SequentialAgent(name="R", sub_agents=[
                FakeAgent(name="B", key="briefing", text="Missão para o 6º ano do fundamental."),
                VizinhasCatalogoAgent(name="A001VizinhasCatalogo"),
            ])))
            assert st["catalogo_indice_status"] == "amarelo"
            assert st["missoes_vizinhas"].startswith("> ⚠️"), "o aviso precisa vir ANTES da tabela que o V5 julga"
            assert "exp05ef1b" in st["missoes_vizinhas"] and "exp01ef1b" in st["missoes_vizinhas"]
            assert [a["codigo"] for a in st["catalogo_indice_status_envelope"]["achados"]] == ["indice-defasado"]

            for slug, sessao in (("exp05ef1b", "s5"), ("exp01ef1b", "s1b")):
                cat.registrar(_ficha(slug=slug, sessao=sessao, ano=slug[3:5].lstrip("0") + "EF",
                                     descoberta=f"descoberta própria da {slug}"), base=base)
            _, st = asyncio.run(_run(SequentialAgent(name="R", sub_agents=[
                FakeAgent(name="B", key="briefing", text="Missão para o 6º ano do fundamental."),
                VizinhasCatalogoAgent(name="A001VizinhasCatalogo"),
            ])))
            assert st["catalogo_indice_status"] == "aprovado", st["catalogo_indice_status_envelope"]
        finally:
            if antes is None:
                os.environ.pop("OUTPUT_DIR", None)
            else:
                os.environ["OUTPUT_DIR"] = antes

    from tools.diagnostico import GATES
    assert "catalogo_indice_status" in {g["status"] for g in GATES}
    print("   ✓ índice defasado: o micro-gate lê o aviso antes da tabela e o dossiê mostra 🟡")



def test_ficha_do_catalogo_le_pelo_nome_da_coluna():
    """13 das 14 fichas reconstruídas em 23/09/2026 saíam com `tipo_decisao` vazio: o parser lia a
    linha do aprendizado POR POSIÇÃO, com o slug primeiro, e o 51 escreve `|Ano|Bim|Nome|…|` sem
    slug. A linha era descartada sempre, e o registro automático repetia o defeito em toda missão
    nova. O ambiente saía vazio nas 5 com `secao_ds: nova:…`."""
    from tools import catalogo as cat

    # a linha como o 51 de fato a escreveu na exp06ef1b (8 colunas, sem slug)
    real = """### Linha proposta para `references/catalogo-missoes.md`

| Ano | Bim | Nome | Ambiente | Eixo temático | Descoberta central (aha) | Tipo de decisão | Status |
|---|---|---|---|---|---|---|---|
| 6º EF | 1º | O algoritmo que me formou | InstaNooria (Instagram) | Algoritmos / bolhas | Eu só segui 1 conta e isso decidiu o resto. | Seguir 1 perfil e fixar 1 post de síntese | Aprovada |
"""
    f = cat._linha_do_aprendizado(real)
    assert f["tipo_decisao"] == "Seguir 1 perfil e fixar 1 post de síntese", f
    assert f["descoberta"].startswith("Eu só segui") and f["ano"] == "6º EF"

    # o formato que o prompt pede: outra ordem, com slug e campo por preencher
    pedido = """|Slug|Ano|Bim|Nome|Ambiente|Eixo temático|Descoberta central (aha)|Tipo de decisão|Porta de abstração|Habilidade primária|Status|
|---|---|---|---|---|---|---|---|---|---|---|
|exp04ef1b|4º EF|1º|N|unitube|credibilidade|views não é confiança|escolher 3 de 10 vídeos|explicar|[preencher do manifesto]|em criação|
"""
    g = cat._linha_do_aprendizado(pedido)
    assert g["slug"] == "exp04ef1b" and g["tipo_decisao"] == "escolher 3 de 10 vídeos"
    assert "habilidade_primaria" not in g, "campo por preencher volta vazio para a extração do núcleo tentar"

    # ambiente pelo `secao_ds`: canônico, e ambiente novo com o nome
    assert cat._ambiente_da_spec("- `secao_ds: instanooria`") == "instanooria"
    assert cat._ambiente_da_spec("- **secao_ds**: `nova:galeria-infantil`") == "nova:galeria-infantil"
    assert cat._ambiente_da_spec("- `secao_ds: inventado`") == ""

    ficha = cat.ficha_da_execucao({"aprendizado_registro": real,
                                   "spec_missao": "## 0. Ficha\n- `secao_ds: nova:galeria-infantil`\n"})
    assert ficha["tipo_decisao"] and ficha["ambiente"] == "nova:galeria-infantil"
    assert not cat.tem_lacuna(ficha), "ficha completa não pode sair cega para o V5"
    print("   ✓ ficha do catálogo lida pelo nome da coluna; ambiente novo não sai vazio")



def test_nenhum_prompt_manda_usar_ferramenta_que_o_agente_nao_tem():
    """O D0 foi instruído, de 16 a 23/09/2026, a criar um Google Docs com `create_file` — e nunca
    recebeu ferramenta nenhuma, em modo nenhum. As 14 sessões escreveram "GDOCS: indisponível" em
    9 redações. Instrução para ferramenta ausente não falha: é desobedecida em silêncio.

    O Stitch é o caso legítimo e diferente: ferramenta CONDICIONAL, anexada por
    `stitch_tools_or_empty` quando `STITCH_MCP_MODE` está ligado (em produção, `remote`), e com
    o que fazer quando não está escrito nos dois prompts. Aqui ele vem desligado (linha 21), então
    o que se confere é que só os agentes que recebem o Stitch falam das ferramentas dele.
    """
    import re as _re
    from google.adk.agents.llm_agent import LlmAgent
    from pipeline.orchestrator import create_mission_orchestrator, iter_agent_tree

    llms = [a for _, a in iter_agent_tree(create_mission_orchestrator(stages=["produto", "design", "dev"]))
            if isinstance(a, LlmAgent)]
    drive = _re.compile(r"google drive|google docs|gdocs|create_file|gdrive", _re.I)
    stitch = _re.compile(r"\b(?:upload_design_md|list_screens|get_screen|create_project|generate_screen)\w*", _re.I)
    com_stitch = ("A075Telas", "A088QaEntregaveis")  # os que chamam `stitch_tools_or_empty`

    falhas = {a.name: sorted(set(drive.findall(str(a.instruction)))) for a in llms}
    falhas = {k: v for k, v in falhas.items() if v}
    assert not falhas, f"instrução para ferramenta do Drive, que nenhum agente recebe: {falhas}"
    fora = {a.name: sorted(set(stitch.findall(str(a.instruction)))) for a in llms
            if not a.name.startswith(com_stitch)}
    fora = {k: v for k, v in fora.items() if v}
    assert not fora, f"ferramenta do Stitch citada em agente que não recebe o Stitch: {fora}"
    from config import get_settings
    assert not hasattr(get_settings(), "gdrive_folder_url")
    print(f"   ✓ {len(llms)} agentes de LLM: nenhum instruído a usar o Drive; Stitch só onde é anexado")



def test_despacho_traduz_o_dono_e_nunca_descarta_ticket_em_silencio():
    """A-15 (auditoria de 23/09/2026). O despacho casava só o nome literal do dono: a banca escreveu
    `wireframes` 16 vezes, `spec` 15 e `copy` 2 nas 14 sessões, e tudo iria para lugar nenhum. Havia
    três descartes silenciosos — sem dono, dono desconhecido, agente de retrabalho ausente."""
    import json as _json
    from agents.checkers import DespachoTicketsAgent

    achados = [
        {"id": "T1", "severidade": "bloqueio", "agente_responsavel": "Wireframes", "resumo": "tela sem estado vazio"},
        {"id": "T2", "severidade": "bloqueio", "agente_responsavel": "spec", "resumo": "a spec não decide a cardinalidade"},
        {"id": "T3", "severidade": "bloqueio", "agente_responsavel": "inventado", "resumo": "dono que não existe"},
        {"id": "T4", "severidade": "bloqueio", "agente_responsavel": "", "resumo": "ninguém foi apontado"},
        {"id": "T5", "severidade": "bloqueio", "agente_responsavel": "jornada", "resumo": "o mapa aponta para agente ausente"},
        {"id": "T6", "severidade": "atencao", "agente_responsavel": "inventado", "resumo": "ressalva não é roteada"},
    ]
    relatorio = "QA\n```json\n" + _json.dumps({"status": "bloqueado", "achados": achados}) + "\n```"
    despacho = DespachoTicketsAgent(
        name="Despacho", report_key="qa", rotulo="Retrabalho de teste",
        mapa={"telas": "TelasR", "jornada": ["JornadaInexistente"]},
        externos=["spec-missao"],
        sub_agents=[FakeAgent(name="TelasR", key="telas_refeitas", text="telas corrigidas")],
    )
    eventos, st = asyncio.run(_run(SequentialAgent(name="R", sub_agents=[
        FakeAgent(name="QA", key="qa", text=relatorio), despacho])))

    assert st.get("telas_refeitas") == "telas corrigidas", "`Wireframes` tinha de chegar ao agente de telas"
    sem_rota = {r["id"]: r for r in st.get("tickets_sem_rota") or []}
    assert set(sem_rota) == {"T3", "T4", "T5"}, sorted(sem_rota)
    assert "nenhum agente" in sem_rota["T3"]["motivo"]
    assert "não disse quem conserta" in sem_rota["T4"]["motivo"]
    assert "JornadaInexistente" in sem_rota["T5"]["motivo"]
    texto = " ".join(p.text for e in eventos if e.content for p in (e.content.parts or []) if getattr(p, "text", None))
    assert "`T2` → `spec-missao`" in texto, "o nome traduzido tinha de chegar à lista de externos"
    assert "Sem quem execute" in texto and "`T3`" in texto

    from tools.diagnostico import coletar
    d = coletar({"tickets_sem_rota": st["tickets_sem_rota"]})
    humanos = [a for a in d["humanos"] if a["codigo"] == "ticket-sem-rota"]
    assert len(humanos) == 3 and d["veredito"] == "amarelo" and d["precisa_humano"]
    print("   ✓ despacho: nome traduzido pela fonte única, e ticket sem rota vira pendência humana no dossiê")


def test_banca_consolidada_entrega_o_dono_ao_despacho():
    """De 22 a 23/09/2026 a consolidação determinística da banca descartava `agente_responsavel` e
    `id` do envelope que o despacho lê: todo ticket da banca chegava sem dono e era jogado fora."""
    from agents.callbacks import extrair_envelope
    from tools import banca

    dim = {"status": "bloqueado", "contagem": {"nok_bloqueantes": 1},
           "achados": [{"id": "DES-01", "codigo": "DES-01", "severidade": "bloqueio",
                        "agente_responsavel": "telas", "resumo": "a tela quebra a imersão"}]}
    resultado = banca.consolidar({"validacao_design_imersao": dim})
    env = extrair_envelope(banca.relatorio(resultado, "exp06ef1b")) or {}
    achado = next(a for a in env["achados"] if a.get("codigo") == "DES-01")
    assert achado.get("agente_responsavel") == "telas" and achado.get("id") == "DES-01", achado
    print("   ✓ banca consolidada: id e dono chegam ao despacho")


def test_todo_dono_que_um_gate_pode_escrever_tem_destino():
    """O cruzamento que revelou o A-15, como teste: cada nome da lista fechada que o envelope do QA
    de design e o da banca oferecem, traduzido pela fonte única, cai numa rota ou num externo — e
    toda rota aponta para um agente que existe."""
    import re as _re
    from agents.checkers import DespachoTicketsAgent
    from pipeline.orchestrator import create_mission_orchestrator, iter_agent_tree
    from prompts import load_prompt
    from tools.rastro import normalizar_dono

    despachos = {a.name: a for _, a in iter_agent_tree(create_mission_orchestrator(stages=["produto", "design", "dev"]))
                 if isinstance(a, DespachoTicketsAgent)}
    kw = dict(stitch_mcp_mode="off", stitch_project_url_base="u", gate_max_rodadas=3, qa_max_rodadas=2)
    fontes = {"A091DespachoDesign": "design/088_qa_entregaveis.md", "A112DespachoBanca": "dev/validacao_design_imersao.md"}
    for nome, prompt in fontes.items():
        d = despachos[nome]
        bloco = _re.search(r'"agente_responsavel":\s*((?:"[^"]+"\s*\|?\s*)+)', load_prompt(prompt, **kw)).group(1)
        oferecidos = {x.strip() for x in _re.findall(r'"([^"]+)"', bloco) for x in x.split("|")} - {"null", ""}
        destinos = set(d.mapa) | set(d.externos or [])
        sem = sorted(o for o in oferecidos if normalizar_dono(o) not in destinos)
        assert not sem, f"{nome}: o envelope oferece donos sem destino: {sem}"
        existentes = {s.name for s in d.sub_agents}
        for slug, alvo in d.mapa.items():
            for agente in ([alvo] if isinstance(alvo, str) else alvo):
                assert agente in existentes, f"{nome}: `{slug}` aponta para {agente}, que não existe"
    print("   ✓ todo dono que o QA e a banca podem escrever tem rota ou vira externo; toda rota existe")



# ── Quem reescreve lê o que o gate pediu (auditoria v3, 23/09/2026) ──────────────────────────
# Duas perguntas feitas a todos os agentes de uma vez acharam dois agentes que reescreviam às
# cegas: o brief de assets, reexecutado pela banca sem ler ticket nem relatório (A-16), e o
# revisor do one-pager, que o loop das avaliações repetia por um relatório que ele não recebia
# (A-17). Toda vez que um cruzamento assim foi feito sobre a árvore inteira, achou defeito.
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.loop_agent import LoopAgent
from agents.checkers import (BnccCheckAgent, DespachoTicketsAgent, EnvelopeGateAgent,
                             RastroCheckAgent, SaidaDeLoopAgent)
from pipeline.orchestrator import iter_agent_tree

def _dentro(a):
    for s in getattr(a, "sub_agents", []) or []:
        yield s
        yield from _dentro(s)

def _reexecutados_sem_pedido(raiz):
    """Agente que um despacho reexecuta e que não lê nem o ticket nem o relatório do gate."""
    falhas = []
    for _, d in iter_agent_tree(raiz):
        if isinstance(d, DespachoTicketsAgent):
            for s in d.sub_agents:
                txt = str(getattr(s, "instruction", ""))
                if isinstance(s, LlmAgent) and "{" + d.tickets_key not in txt and "{" + d.report_key not in txt:
                    falhas.append(f"{d.name} → {s.name}")
    return falhas

def _gates_que_ninguem_le(raiz):
    """Gate que faz o loop repetir, e cujo relatório nenhum autor do loop recebe."""
    falhas = []
    for _, loop in iter_agent_tree(raiz):
        if not isinstance(loop, LoopAgent):
            continue
        dentro = list(_dentro(loop))
        if any(isinstance(a, DespachoTicketsAgent) for a in dentro):
            continue  # quem corrige é o despacho — coberto pela outra regra
        gates = [g for g in dentro if isinstance(g, (EnvelopeGateAgent, RastroCheckAgent, BnccCheckAgent))]
        repetem = {k for s in dentro if isinstance(s, SaidaDeLoopAgent) for k in s.status_keys}
        repetem |= {g.status_key for g in gates if isinstance(g, EnvelopeGateAgent) and g.round_key}
        relatorios = {getattr(g, "report_key", "") for g in gates}
        autores = [a for a in dentro if isinstance(a, LlmAgent) and a.output_key not in relatorios]
        for g in gates:
            if g.status_key in repetem and getattr(g, "report_key", ""):
                if not any("{" + g.report_key in str(a.instruction) for a in autores):
                    falhas.append(f"{loop.name}: {g.name} reprova e nenhum de {[a.name for a in autores]} lê {{{g.report_key}}}")
    return falhas


def test_todo_agente_reexecutado_le_o_que_o_gate_pediu():
    from pipeline.orchestrator import create_mission_orchestrator
    orch = create_mission_orchestrator(stages=["produto", "design", "dev"])
    falhas = _reexecutados_sem_pedido(orch)
    assert not falhas, f"reexecutado sem ler o ticket nem o relatório do gate: {falhas}"
    falhas = _gates_que_ninguem_le(orch)
    assert not falhas, f"gate que repete o loop sem que nenhum autor leia o relatório: {falhas}"
    print("   ✓ quem é reexecutado lê o ticket; todo gate que repete um loop tem um autor que o lê")



def test_correcao_parcial_apaga_tudo_que_a_etapa_vai_regravar():
    """Toda chave que um agente da etapa grava é apagada quando a correção recomeça dali.

    Em 23/09/2026 seis gates novos tinham ficado fora das listas: o contador do juiz das perguntas
    sobrevivia (a correção começava com as rodadas esgotadas) e o veredito da execução anterior
    podia aparecer no dossiê da nova. Gate novo que nascer sem entrar na lista falha aqui.
    """
    from pipeline.orchestrator import create_mission_orchestrator, iter_agent_tree
    from pipeline.reexecucao import CHAVES_EXECUCAO, CHAVES_POR_ETAPA, ETAPA_PARA_STAGES

    anteriores = {"produto": frozenset(), "spec": frozenset(),
                  "design": CHAVES_POR_ETAPA["spec"] - CHAVES_POR_ETAPA["design"],
                  "dev": CHAVES_POR_ETAPA["spec"] - CHAVES_POR_ETAPA["dev"]}
    for etapa in ("produto", "spec", "design", "dev"):
        escritas = set()
        for _, a in iter_agent_tree(create_mission_orchestrator(stages=ETAPA_PARA_STAGES[etapa])):
            if a.name in ("A127Diagnostico", "A128Aprendizado", "A129RegistroCatalogo"):
                continue  # transversal: refeitos em toda execução
            for attr in ("output_key", "report_key", "status_key", "round_key", "rodada_key"):
                if getattr(a, attr, None):
                    escritas.add(getattr(a, attr))
            if getattr(a, "status_key", None):
                escritas.add(a.status_key + "_envelope")
        # o retrabalho da banca reescreve documentos de design: numa correção de dev eles são o
        # insumo, e apagá-los apagaria o design
        fora = escritas - CHAVES_POR_ETAPA[etapa] - CHAVES_EXECUCAO - anteriores[etapa]
        assert not fora, f"correção a partir de `{etapa}` não apaga o que a etapa regrava: {sorted(fora)}"
        rodadas = {k for k in escritas if "rodada" in k} - anteriores[etapa]
        assert rodadas <= CHAVES_POR_ETAPA[etapa], f"contador de rodada sobrevive à correção: {sorted(rodadas)}"
    assert "tickets_sem_rota" in CHAVES_EXECUCAO
    print("   ✓ correção parcial apaga tudo que a etapa regrava, contadores de rodada inclusive")



def test_criterios_da_rubrica_declaram_a_mesma_versao():
    """Os quatro arquivos de critério da rubrica de produto dizem, no título, qual versão vale.
    `criterios-experiencia.md` tinha as notas v1.18 e v1.19 e nenhum título dizendo qual das duas
    estava em vigor — o único dos quatro que o versionamento de 22/09/2026 deixou de fora."""
    import re as _re
    from prompts import REFERENCES_DIR
    versoes = {}
    for nome in ("criterios-gate-estrutural.md", "criterios-pedagogicos.md",
                 "criterios-experiencia.md", "criterios-gate-final.md"):
        m = _re.search(r"Rubrica v(\d+\.\d+)", (REFERENCES_DIR / nome).read_text(encoding="utf-8").splitlines()[0])
        versoes[nome] = m.group(1) if m else None
    assert None not in versoes.values(), f"critério sem versão no título: {versoes}"
    assert len(set(versoes.values())) == 1, f"versões divergentes: {versoes}"
    print(f"   ✓ os quatro critérios da rubrica de produto declaram v{next(iter(versoes.values()))}")



def test_material_anexado_chega_a_quem_o_usa_como_fonte():
    """A-19 (23/09/2026). O conteúdo dos anexos existia só na mensagem, que só o núcleo narrativo
    lê. A spec, a avaliação pedagógica e o one-pager resumido são instruídos a usar o material do
    Entre Redes como fonte primária e nunca o viam: 5 das 7 sessões que o anexaram entregaram um
    resumido dizendo "material do bimestre não anexado"."""
    import re as _re
    from google.adk.agents.llm_agent import LlmAgent
    from pipeline.orchestrator import create_mission_orchestrator, iter_agent_tree
    from pipeline.runner import material_dos_anexos
    from tools.doc_parser import DocumentBatch, ProcessedDocument

    grande = "habilidade EF06CO09 " * 30000  # ~600 KB: nada é cortado, por decisão
    lote = DocumentBatch(documents=[
        ProcessedDocument(name="entre_redes_6ano.docx", file_type="docx", size_bytes=1, markdown_text=grande),
        ProcessedDocument(name="plano.pdf", file_type="pdf", size_bytes=1, is_native_pdf=True,
                          pdf_bytes=b"%PDF", markdown_text="texto extraído do PDF"),
        ProcessedDocument(name="digitalizado.pdf", file_type="pdf", size_bytes=1, is_native_pdf=True, pdf_bytes=b"%PDF"),
    ])
    material = material_dos_anexos(lote)
    assert grande.strip() in material, "o material foi cortado — não pode haver limite"
    assert "texto extraído do PDF" in material, "o PDF vai ao modelo como arquivo; ao estado, como texto"
    assert "digitalizado.pdf" in material and "sem texto extraível" in material
    assert material_dos_anexos(None) == ""

    # quem cita o material anexado como fonte tem de recebê-lo — salvo quem lê a mensagem inteira
    cita = _re.compile(r"material[^.\n]{0,60}anexad|anexad[^.\n]{0,60}material", _re.I)
    sem = [a.name for _, a in iter_agent_tree(create_mission_orchestrator(stages=["produto", "design", "dev"]))
           if isinstance(a, LlmAgent) and getattr(a, "include_contents", "none") != "default"
           and cita.search(str(a.instruction)) and "{material_anexado" not in str(a.instruction)]
    assert not sem, f"citam o material anexado como fonte e não o recebem: {sem}"
    print("   ✓ material anexado: guardado inteiro, e chega à spec, à avaliação e ao resumido")


def test_correcao_de_produto_refaz_desde_o_nucleo_com_o_material_da_origem():
    """A-04 (23/09/2026). A triagem mandava para `spec` os pedidos de mecânica, etapas e narrativa,
    e a correção a partir da spec não refaz o one-pager nem passa pelos gates de produto."""
    import json as _json
    import tempfile
    from pipeline.orchestrator import create_mission_orchestrator, iter_agent_tree
    from pipeline.reexecucao import (CHAVES_PRODUTO, ETAPA_PARA_STAGES, PedidoCorrecao, Triagem,
                                     executar_correcao_stream, material_para_refazer_produto, preparar_estado)
    from pipeline.runner import CABECALHO_MATERIAL_GUARDADO, mensagem_do_usuario

    # 1. refaz produto, design e dev — e os gates de produto estão na árvore
    assert ETAPA_PARA_STAGES["produto"] == ["produto", "design", "dev"]
    nomes = [a.name for _, a in iter_agent_tree(create_mission_orchestrator(stages=ETAPA_PARA_STAGES["produto"]))]
    for gate in ("A004NucleoNarrativo", "A026GateEstrutural", "A029aAvaliacaoPedagogica", "A043GateFinalProduto"):
        assert gate in nomes, gate
    assert len(nomes) == len(set(nomes))

    # 2. apaga o que produto grava, preserva o que ele lê da geração original
    estado = {"briefing": "missão do 6º ano", "perguntas_po": "PQ", "material_anexado": "material",
              "nucleo_narrativo": "velho", "one_pager": "velho", "gate_final_report": "velho", "spec_missao": "velha",
              "gate_estrutural_rodada": 2, "degradacoes": [{"gate": "Gate estrutural"}]}
    limpo, removidas = preparar_estado(estado, "produto", "pedido")
    for k in ("nucleo_narrativo", "one_pager", "gate_final_report", "spec_missao", "gate_estrutural_rodada"):
        assert k not in limpo and k in removidas, k
    assert limpo["briefing"] and limpo["perguntas_po"] and limpo["material_anexado"] == "material"
    assert not limpo.get("degradacoes"), "todos os gates vão ser refeitos: nenhuma reprovação é herdada"
    assert {"brief_escopo", "missoes_vizinhas", "catalogo_indice_status"} <= CHAVES_PRODUTO

    # 3. o núcleo recebe o material guardado na mensagem — só quando refaz produto
    msg = mensagem_do_usuario("briefing", None, {"material_anexado": "### 📄 entre redes"}, ["produto", "design", "dev"])
    texto = msg.parts[0].text
    assert CABECALHO_MATERIAL_GUARDADO in texto and "entre redes" in texto
    assert "entre redes" not in mensagem_do_usuario("briefing", None, {"material_anexado": "### 📄 entre redes"}, ["spec"]).parts[0].text

    # 4. sessão antiga, sem material guardado
    sem_material = {"briefing": "b"}
    com_anexo = {"attached_files": ["entre_redes_6ano.docx"]}
    assert material_para_refazer_produto({"material_anexado": "salvo"}, com_anexo, None) == ("salvo", None)
    reanexado = PedidoCorrecao(texto="mude a etapa 3", anexos=[("entre_redes_6ano.docx", "conteúdo")])
    material, recusa = material_para_refazer_produto(sem_material, com_anexo, reanexado)
    assert recusa is None and "conteúdo" in material
    material, recusa = material_para_refazer_produto(sem_material, com_anexo, PedidoCorrecao(texto="mude a etapa 3"))
    assert material is None and "entre_redes_6ano.docx" in recusa and "Anexe de novo" in recusa
    assert material_para_refazer_produto(sem_material, {"attached_files": []}, None) == ("", None)

    # 5. a recusa não toca a sessão: nem backup, nem estado
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        (run_dir / "estado.json").write_text(_json.dumps({"briefing": "b", "one_pager": "intacto"}))
        (run_dir / "conversa.json").write_text(_json.dumps({"session_id": "s", "user_id": "u",
                                                            "attached_files": ["entre_redes_6ano.docx"]}))

        async def _coletar():
            return [e async for e in executar_correcao_stream(run_dir, "produto", PedidoCorrecao(texto="mude"))]
        eventos = asyncio.run(_coletar())
        assert [e["type"] for e in eventos] == ["correcao_error"], [e["type"] for e in eventos]
        assert not (run_dir / ".correcoes").exists(), "a recusa criou backup"
        assert _json.loads((run_dir / "estado.json").read_text())["one_pager"] == "intacto"

    # 6. a triagem sabe escolher produto
    tri = Triagem.de_texto('ok\n```json\n{"agente": "triagem-correcao", "etapa": "produto", "motivo": "muda a mecânica", '
                           '"resumo_pedido": "x", "resumo_anexos": "", "confianca": "alta"}\n```')
    assert tri.etapa == "produto" and tri.reexecuta
    print("   ✓ correção de produto: refaz desde o núcleo, com o material da origem, e recusa sem ele")



def test_lint_do_prototipo_nao_confunde_portugues_com_rascunho():
    """Em 23/09/2026 o lint bloqueou um protótipo por "você aprendeu que **todo** enquadramento conta
    uma história": ignorava caixa, e `todo`, `a definir` e `placeholder` são palavras comuns — a
    última é o nome da convenção do DS para a caixa de mídia do wireframe."""
    from tools.prototipo import validar
    base = '<html><body><section id="E1-ALU-01">'
    def acusa(corpo):
        return any(a["codigo"] == "marcador-de-rascunho" for a in validar(base + corpo + "</section></body></html>", ["E1-ALU-01"])["achados"])
    assert not acusa("Você aprendeu que todo enquadramento conta uma história.")
    assert not acusa("<style>/* Linhas X de placeholder do DS */</style>oi")
    assert not acusa("O tema da aula é a definir pelo professor.")
    assert not acusa('<input placeholder="Digite sua legenda">')
    assert acusa("TODO: texto final") and acusa("Olá [[nome_da_turma]]") and acusa("Legenda: [a definir]")
    assert acusa("Lorem ipsum dolor")
    print("   ✓ lint do protótipo: rascunho de verdade acusa, português não")



def test_saeb_verde_onde_nao_se_aplica_amarelo_onde_falta_ou_sobra():
    """Regra de 23/09/2026, a pedido: ano que o SAEB não avalia com "N/A" é verde; descritor citado
    nesse ano, ou ano avaliado sem descritor, é amarelo com a indicação. A regra anterior acusava o
    próprio "N/A — ano não avaliado pelo SAEB" que manda escrever, e lia o 2º ano como 1º ao 5º."""
    from tools.contrato_produto import validar_one_pager

    def saeb(slug, linha):
        op = f"# One-pager\n## 0. Ficha\n- id: `{slug}`\n## 2. Currículo\n{linha}\n- **Rastreabilidade:** x\n## 3. Outra\n"
        return [a["codigo"] for a in validar_one_pager(op)["achados"] if a["codigo"].startswith("saeb")]
    na = "- **Descritor SAEB:** N/A — ano não avaliado pelo SAEB."
    assert saeb("exp06ef1b", na) == [] and saeb("exp08ef2b", na) == [] and saeb("exp02em1b", na) == []
    assert saeb("exp05ef1b", na) == ["saeb-ausente"], "o 5º ano é avaliado: N/A é falta"
    assert saeb("exp05ef1b", "- **BNCC:** x") == ["saeb-ausente"]
    assert saeb("exp09ef1b", "- **Descritor SAEB:** Matemática — D12: resolver problema.") == []
    assert saeb("exp03em1b", "- **Descritor SAEB:** Língua Portuguesa — D05.") == []
    assert saeb("exp04ef1b", "- **Descritor SAEB:** Língua Portuguesa — D05.") == ["saeb-fora-do-ano"]
    # descritor por extenso, em subtópico — a matriz de alfabetização do 2º ano não usa `Dnn`
    assert saeb("exp02ef1b", "- **Descritor SAEB:**\n  - *Língua Portuguesa — 2º ano:* Localizar informação explícita em textos compostos por imagem e texto verbal.") == []
    # título com os descritores em tópicos embaixo
    titulo = "### Descritor SAEB Associado\n* **Língua Portuguesa — D14:** distinguir fato de opinião.\n* **Língua Portuguesa — D15:** reconhecer relações."
    assert saeb("exp07ef1b", titulo) == ["saeb-fora-do-ano"]
    print("   ✓ SAEB: N/A verde onde não se aplica; descritor que falta ou sobra fica amarelo")



def test_leitor_de_evento_e_o_mesmo_nos_dois_gates_e_nos_documentos():
    """Na geração de teste de 23/09/2026 seis impedimentos vinham de o PRD escrever "Pub/Sub" como
    leitor de eventos que só alimentam KPI de produto. O gate estava certo — Pub/Sub é transporte —,
    mas nenhum documento dizia ao redator quem é o leitor desse evento, e os dois gates discordavam
    entre si: o de KPI aceitava PostHog, o do PRD não."""
    from prompts import REFERENCES_DIR
    from tools.kpis import LEITOR_VALIDO, validar_kpis
    from tools.rastro import validar_prd
    import re as _re

    linha_evt = "| {id} | interacted | foto:miniatura | E2-ALU-01 | {{\"foto_id\": \"x\"}} | — | analítico | {leitor} |"
    cab = "| ID | Verbo | Objeto | Quando dispara | Resultado | Contexto | Caminho | Onde é lido |\n|---|---|---|---|---|---|---|---|\n"
    for leitor, esperado in (("Pub/Sub", True), ("telemetria_eventos", True),
                             ("painel de produto (PostHog)", False), ("exp02ef1b_sessoes", False)):
        prd = cab + linha_evt.format(id="EVT-001", leitor=leitor) + "\n"
        k = any(a["codigo"] == "leitura-sem-leitor" for a in validar_kpis(prd)["achados"])
        p = any(a["codigo"] == "evento-sem-leitor" for a in validar_prd(prd)["achados"])
        assert k == p == esperado, (leitor, k, p)
    for nome in ("prd-padrao-ouro.md", "formato-spec.md", "perguntas-de-produto.md"):
        assert "painel de produto (PostHog)" in (REFERENCES_DIR / nome).read_text(encoding="utf-8"), nome
    print("   ✓ leitor de evento: tabela do módulo ou painel de produto, igual nos dois gates e nos três documentos")



def test_juizes_de_produto_leem_o_briefing_e_contam_so_o_tempo_em_tela():
    """Na geração de teste de 23/09/2026 a missão foi reprovada duas vezes por obedecer ao PO — o
    briefing proibia áudio, a rubrica exige áudio no 1º–2º ano, e nenhum dos três juízes de produto
    recebia o briefing — e o one-pager escreveu "45 minutos em tela" para a aula inteira, com 15 min
    de mediação oral dentro, e o teto de tempo-aluno leu isso ao pé da letra."""
    from agents.produto import (get_avaliacao_pedagogica_agent, get_experiencia_aluno_agent,
                                get_gate_final_produto_agent)
    from prompts import REFERENCES_DIR, load_prompt
    for agente in (get_avaliacao_pedagogica_agent(), get_experiencia_aluno_agent(), get_gate_final_produto_agent()):
        instr = str(agente.instruction)
        assert "{briefing?}" in instr, f"{agente.name} não recebe o briefing"
        assert "não é reprovada por obedecer" in instr, f"{agente.name} sem a regra do conflito briefing × rubrica"
    assert "nunca 🔴" in str(get_gate_final_produto_agent().instruction)
    apoio = load_prompt("produto/014_secoes_apoio.md", gate_max_rodadas=3)
    assert "`Em tela (aluno)`" in apoio and "`Fora da tela`" in apoio
    exp = (REFERENCES_DIR / "criterios-experiencia.md").read_text(encoding="utf-8")
    assert "Tempo-aluno é o tempo em tela" in exp
    print("   ✓ juízes de produto leem o briefing; o teto de tempo conta só o tempo em tela")



def test_bncc_confere_eixo_texto_e_o_que_e_declarado():
    """A alucinação da exp06ef1b (22/09/2026): `EF06CO07` apresentado como Cultura Digital e
    letramento digital, com texto inventado e atribuído a um material do Entre Redes que não tinha
    sido anexado. Oficialmente é Mundo Digital, sobre transmissão de dados. O gate aprovou: o código
    existia, era do ano, e um `EF06CO09` citado entre parênteses contou como letramento."""
    from tools.bncc import validar_spec
    of7 = "Entender o processo de transmissão de dados, como a informação é quebrada em pedaços, transmitida em pacotes através de múltiplos equipamentos, e reconstruída no destino."
    of9 = "Apresentar conduta e linguagem apropriadas ao se comunicar em ambiente digital, considerando a ética e o respeito."
    inventado = "Discutir o impacto das tecnologias digitais na sociedade, na cultura e nas relações humanas."
    def spec(item, extra=""):
        return f"# Spec\n## 0. Ficha\n- séries: [\"6EF\"]\n## 11. Currículo\n{item}\n{extra}\n## 12. Decisões\n"
    def cods(r): return {a["codigo"] for a in r["achados"]}

    alucinado = spec(f"* **`EF06CO07` — Cultura Digital**\n  * **Habilidade:** *{inventado}*\n  * **Momento em tela:** Etapa 4.",
                     "(o letramento digital equivalente corresponde a `EF06CO09`).")
    r = validar_spec(alucinado)
    assert r["status"] == "bloqueado" and {"eixo-divergente", "texto-divergente", "letramento"} <= cods(r), cods(r)

    certo = spec(f"* **`EF06CO09` — Cultura Digital**\n  * **Texto oficial:** {of9}\n  * **Momento em tela:** Etapa 4.")
    assert validar_spec(certo)["status"] == "aprovado", cods(validar_spec(certo))

    # texto do material do Entre Redes: vale quando o material anexado o traz
    do_material = spec(f"* **`EF06CO09` — Cultura Digital**\n  * **Habilidade (Entre Redes):** *{inventado}*\n  * **Momento em tela:** Etapa 4.")
    assert "texto-divergente" in cods(validar_spec(do_material))
    assert "texto-divergente" not in cods(validar_spec(do_material, material="Unidade 1. " + inventado + " Fim."))

    # rótulo do momento que menciona a palavra habilidade não é o texto dela
    momento = spec(f"* **`EF06CO09` — Cultura Digital**\n  * *Texto oficial:* {of9}\n  * *Momento em tela que exercita a habilidade:* O estudante fixa um post e explica por que confia nele.")
    assert validar_spec(momento)["status"] == "aprovado", cods(validar_spec(momento))

    # tabela: só a coluna da habilidade é conferida
    tabela = spec("| Eixo | Código | Habilidade (texto oficial) | Momento em tela |\n|---|---|---|---|\n"
                  f"| Mundo Digital | `EF06CO07` | *{inventado}* | Etapa 4: o estudante compara dois feeds lado a lado. |\n"
                  f"| Cultura Digital | `EF06CO09` | {of9} | Etapa 5: o estudante escolhe o que publicar. |")
    assert "texto-divergente" in cods(validar_spec(tabela))

    # EM não tem eixo: `EM13CO25` como Cultura Digital é a leitura proposta, não "na BNCC ele é None"
    of25 = "Dialogar em ambientes virtuais com segurança e respeito às diferenças culturais e pessoais, reconhecendo e denunciando atitudes abusivas."
    em = f"# Spec\n## 0. Ficha\n- séries: [\"1EM\"]\n## 11. Currículo\n* **`EM13CO25` — Cultura Digital**\n  * **Texto oficial:** {of25}\n  * **Momento em tela:** Etapa 3.\n## 12. Decisões\n"
    r = validar_spec(em)
    assert r["status"] == "aprovado" and "eixo-divergente" not in cods(r), r["achados"]
    assert not any("None" in a["resumo"] for a in r["achados"]), r["achados"]
    # vale para as três séries, e EM13 fora da lista proposta como Cultura Digital continua bloqueando
    for s in ("2EM", "3EM"):
        assert validar_spec(em.replace("1EM", s))["status"] == "aprovado", s
    from tools.bncc import habilidades
    fora = em.replace("EM13CO25", "EM13CO01").replace(of25, habilidades()["EM13CO01"]["habilidade"])
    assert "eixo-divergente" in cods(validar_spec(fora)), validar_spec(fora)["achados"]
    print("   ✓ BNCC: eixo e texto conferidos contra o oficial (ou o material), e letramento só do que é declarado")



def test_rotas_citadas_em_modulo_da_plataforma_existem_nela():
    """Nas 14 sessões, 22 afirmações de rota inexistente ou com verbo errado em módulos que a
    plataforma já tem — `DELETE /turmas/:id` apagaria uma turma inteira a partir de uma missão. A
    maioria vinha de um prompt que mandava "instanciar o padrão de Atividade que a plataforma já
    tem (`POST /atividades` → … → aprovar)": `/atividades` é o motor da exp-01, e cada missão
    construída tem o preparo no próprio módulo."""
    import os
    import tools.rotas_plataforma as rp
    from tools.rastro import validar_prd

    def cods(txt):
        return [a["codigo"] for a in rp.validar_rotas(txt)]
    rp._cache.clear()
    assert cods("O professor chama `PUT /atividades/:id/revisar`.") == ["rota-inexistente"]
    assert cods("Ao fim, `DELETE /turmas/:id`.") == ["rota-verbo-errado"]
    assert cods("Libera com `PUT /salas/turma/:turmaId/missoes/exp09ef1b`.") == [], "slug no lugar do parâmetro casa"
    assert cods("Módulo `apps/api/src/detetives-bento/`: `POST /detetives-bento/turmas/:id/gate`.") == [], "módulo novo é proposta"
    assert cods("Módulo `apps/api/src/quem-mandou-isso/`: `POST /quem-mandou-isso/mural`.") == [], "o módulo que o documento declara é dele"
    assert cods("`POST /atividades/:id/aprovar` — rota nova, pendência de plataforma.") == [], "proposta marcada não é afirmação"
    assert cods("`GET /experiencias/exp07ef1b/sessao`") == ["rota-fora-do-modulo"]
    assert "rota-inexistente" in [a["codigo"] for a in validar_prd("| RF-001 | P0 | `PUT /atividades/:id/revisar` | T-001 |")["achados"]]

    # a URL vence quando responde; sem ela, ou se falhar, a base da plataforma serve
    antes = os.environ.get("PLATAFORMA_OPENAPI_URL")
    os.environ["PLATAFORMA_OPENAPI_URL"] = "http://127.0.0.1:9/docs-json"
    try:
        rp._cache.clear()
        rotas, origem = rp.carregar()
        assert rotas and "base da plataforma" in origem, origem
    finally:
        if antes is None:
            os.environ.pop("PLATAFORMA_OPENAPI_URL", None)
        else:
            os.environ["PLATAFORMA_OPENAPI_URL"] = antes
        rp._cache.clear()

    from prompts import REFERENCES_DIR, load_prompt
    for texto in ((REFERENCES_DIR / "formato-spec.md").read_text(encoding="utf-8"),
                  load_prompt("produto/045_spec_missao.md"), load_prompt("dev/113_prd_writer.md")):
        assert "instancie o padrão de Atividade" not in texto and "padrão de Atividade da plataforma" not in texto
        assert "não se reusa" in texto
    print("   ✓ rotas: inexistente e verbo errado acusados; proposta, módulo próprio e slug no parâmetro passam")



def test_prd_conferido_contra_o_contrato_da_plataforma():
    """Aceite com o PRD da missão do 9º ano (06/10/2026), que saiu da esteira "sem lacunas": cada
    trecho abaixo é literal dele, e cada um era uma afirmação falsa sobre a plataforma."""
    from tools.conferir_prd_plataforma import validar_contrato
    from tools.rastro import validar_prd

    def cods(texto):
        return sorted(a["codigo"] for a in validar_contrato(texto))

    assert cods("- **ADR-108 (Proposta):** Adoção de componentes de enquete estruturada") == ["adr-numero-errado"]
    assert cods("- Seção `@unooria/design-system` v0.2.2 ativa.") == ["ds-versao-cravada"]
    assert cods("- **Pontes consumidas:** `@edu/ui/ds` e `@edu/ui/ds-chatgpt` (para a experiência do estudante).") == ["ponte-legada"]
    assert cods("- **`exp09ef1b_respostas_poll`**: Respostas das enquetes estruturadas.") == ["evidencia-tabela-propria"]
    assert cods("**O SISTEMA DEVE** marcar as sessões ativas como `arquivada`, reiniciar o gate para `E1`") == ["zerar-arquiva"]
    assert cods("selecionar minha turma e liberar a missão imediatamente ou agendar data e horário") == ["agendamento-inexistente"]
    assert cods("Porta de dev: 5185.") == ["porta-ocupada"]
    assert cods('```json\n{"id": "exp09ef1b", "series": ["9EF"], "capabilities": ["telemetria"], "secao_ds": "chatgpt"}\n```') \
        == ["manifesto-chave-inexistente"]

    # o que está certo, proibido ou pedido à plataforma não é acusado
    assert cods("Decisão nova: ADR-150 (proposta). Porta 5186. Ponte `@edu/ui/ds-unooriaai`.") == []
    assert cods("NÃO usar `@edu/ui/ds-chatgpt` nem agendar a missão.") == []
    assert cods("Agendamento da liberação — [PENDÊNCIA PLATAFORMA], dono: dev.") == []
    assert "adr-numero-errado" in [a["codigo"] for a in validar_prd("ADR-108 (Proposta): enquete no chat.")["achados"]]
    print("   ✓ contrato da plataforma: ADR, DS, ponte legada, tabela de enquete, zerar, agenda, porta, manifesto")


def test_componentes_do_ds_conferidos_contra_o_inventario():
    """32% dos componentes que as telas das 14 sessões chamavam "do DS" não existiam na seção — o
    prompt de telas dizia ao agente "você não tem como conferir o catálogo"."""
    import tools.componentes_ds as cds
    from prompts import load_prompt

    cds._cache.clear()
    marcas, mapa, _ = cds.carregar()
    assert "PostCard" in marcas["instanooria"] and "LikeButton" not in marcas["instanooria"]
    assert mapa.get("unitube") == "unootube"

    def tela(secao, ds, locais=""):
        spec = f"- `secao_ds: {secao}`"
        w = "| ID tela | Componentes do DS | Componentes locais (candidatos) |\n|---|---|---|\n" + f"| E1-ALU-01 | {ds} | {locais} |\n"
        return [(a["codigo"], a["severidade"]) for a in cds.validar(w, spec)]
    assert tela("instanooria", "`PostCard`, `StoriesTray`, `Button`, `DataViz`") == []
    assert tela("instanooria", "`LikeButton`") == [("componente-inexistente", "bloqueio")]
    assert tela("instanooria", "`PostCard`", "`LikeButton`, `FeedContainer`") == [], "coluna de locais não é conferida"
    assert tela("chatgpt", "`MessageBubble`") == [("componente-inexistente", "bloqueio")], "componente de outro clone"
    assert "ChatBubble" in cds.validar("| Componentes do DS |\n|---|\n| `MessageBubble` |\n", "- `secao_ds: chatgpt`")[0]["resumo"]
    assert tela("nova:galeria-infantil", "`GradeAlbum2x2`") == [("componente-inexistente", "atencao")]
    assert tela("unitube", "`VideoCard`") == [], "unitube é a marca unootube"

    for prompt in ("design/075_telas.md", "design/067_ambiente_simulado.md"):
        texto = load_prompt(prompt, stitch_mcp_mode="off", stitch_project_url_base="u")
        assert "Você não tem como conferir" not in texto and "`PostCard`" in texto, prompt

    # as seções que a lista fixa antiga nunca viu (06/10/2026): missão nova no UnooriaAI é conferida
    assert {"unooriaai", "unoovista", "unoochat"} <= set(marcas), sorted(marcas)
    assert tela("unooriaai", "`Composer`, `ChatBubble`") == []
    assert tela("unooriaai", "`ChatPollEmbed`") == [("componente-inexistente", "bloqueio")]
    print("   ✓ componentes do DS: inventário nos prompts, coluna conferida, nome parecido sugerido")



def test_juiz_de_achados_so_retira_com_citacao_conferida():
    """Frente B (23/09/2026): 5 de 5 menções a WebSocket acusadas em 22–23/09 eram falsas —
    "Nenhum protocolo WebSocket é utilizado", "sem necessidade de WebSocket", o envelope do próprio
    agente. O regex continua achando; o juiz decide; o código confere a citação. Falha fechada."""
    import json as _json
    from agents.checkers import JuizDeAchadosAgent
    from tools.rastro import frases_afirmativas, validar_telemetria

    handoff = ("## Canal\nA sala sincroniza por polling HTTP curto em `exp05ef1b_gates_turma` (ADR-93).\n"
               "Nenhum protocolo WebSocket ou canal socket.io é utilizado na plataforma.\n"
               "| EVT-001 | interacted | post:feed | ao curtir | {\"x\": 1} | — | analítico | exp05ef1b_sessoes |\n"
               '```json\n{"codigo": "websocket-mencao"}\n```\n')
    assert frases_afirmativas(handoff, r"websocket") == ["Nenhum protocolo WebSocket ou canal socket.io é utilizado na plataforma."], \
        "o envelope JSON não é prosa"
    gate = validar_telemetria(handoff)
    assert "websocket-mencao" in {a["codigo"] for a in gate["achados"]}

    linha = "Nenhum protocolo WebSocket ou canal socket.io é utilizado na plataforma."
    def rodar(resposta, doc=handoff):
        env = {"status": gate["status"], "achados": gate["achados"]}
        juiz = FakeAgent(name="JuizFalso", key="juiz_saida_teste", text=resposta, marker_key="juiz_rodou")
        agente = JuizDeAchadosAgent(name="Juiz", status_key="telemetria_status", report_key="telemetria_report",
                                    fonte_key="handoff_dev", saida_key="juiz_saida_teste", sub_agents=[juiz])
        _, st = asyncio.run(_run(SequentialAgent(name="R", sub_agents=[
            FakeAgent(name="Doc", key="handoff_dev", text=doc,
                      extra_delta={"telemetria_status_envelope": env, "telemetria_status": gate["status"],
                                   "telemetria_report": "relatório\n```json\n" + _json.dumps(env) + "\n```"}),
            agente])))
        return st
    def resposta(veredito, citacoes):
        return "leitura\n```json\n" + _json.dumps({"agente": "juiz-de-achados", "decisoes": [
            {"id": "C1", "veredito": veredito, "citacoes": citacoes}]}, ensure_ascii=False) + "\n```"

    st = rodar(resposta("cita_para_descartar", [linha]))
    assert "websocket-mencao" not in {a["codigo"] for a in st["telemetria_status_envelope"]["achados"]}
    assert "Revisto pelo juiz" in st["telemetria_report"] and linha[:30] in st["telemetria_report"]
    assert "websocket-mencao" not in st["telemetria_report"].split("## Revisto")[0], "o envelope do relatório também é reescrito"

    st = rodar(resposta("cita_para_descartar", ["Nenhum WebSocket foi usado em lugar algum desta missão."]))
    assert "websocket-mencao" in {a["codigo"] for a in st["telemetria_status_envelope"]["achados"]}, "citação inventada não vale"
    st = rodar("não sei")
    assert "websocket-mencao" in {a["codigo"] for a in st["telemetria_status_envelope"]["achados"]}, "resposta inválida: fica"
    st = rodar(resposta("afirma_uso", [linha]))
    assert "websocket-mencao" in {a["codigo"] for a in st["telemetria_status_envelope"]["achados"]}

    sem_candidato = handoff.replace(linha, "O canal é o polling acima.")
    st = rodar(resposta("cita_para_descartar", [linha]), doc=sem_candidato)
    assert not st.get("juiz_rodou"), "sem candidato o juiz não roda — não custa chamada"
    print("   ✓ juiz de achados: retira só com citação conferida; inválido, inventado ou 'afirma' mantém; sem candidato não roda")


# --------------------------------------------------------------------------- profundidade pedagógica
_MATERIAL_6ANO = (
    "Modelagem simplificada do funcionamento de um algoritmo de recomendação: dados de entrada, padrões "
    "identificados, previsão e reforço. *Modelar o funcionamento do algoritmo: SE o usuário clica em X, ENTÃO "
    "recebe mais de X.* Os estudantes mapeiam os conteúdos que consomem e identificam: que perfil o algoritmo "
    "construiu sobre eles? | **Semana 5** | **Mapeando a bolha** |")
_MAPA_6ANO = """# Mapa conceitual do material — 6º ano · 1º bimestre

| ID | Conceito | Papel | Trecho do material | O que o estudante faz para viver o conceito |
|---|---|---|---|---|
| C1 | O algoritmo aprende com o que eu faço e me devolve mais do mesmo | limiar | "SE o usuário clica em X, ENTÃO recebe mais de X" (Semana 2) | seguir uma conta e ver o feed mudar |
| C2 | O app monta um perfil de mim que mostra umas coisas e esconde outras | núcleo | "que perfil o algoritmo construiu sobre eles" (Semana 4) | comparar o perfil com o de um colega |
| C3 | A bolha é o conjunto do que eu nunca vejo | apoio | "Mapeando a bolha" (Semana 5) | montar o mapa da turma |

| ID | Crença de entrada | Origem | Conceito que a derruba |
|---|---|---|---|
| B1 | "O feed mostra o que está bombando para todo mundo" | [INFERÊNCIA] | C1 |

```json
{"agente": "mapa-conceitual", "status": "aprovado", "fonte": "material", "limiar": "C1"}
```"""
_ANATOMIA_6ANO = [
    ("Crença de entrada", "B1 — o feed mostra o que está bombando para todo mundo"),
    ("Aposta comprometida", "segue exatamente 1 das 3 contas e a escolha trava antes do Explorar"),
    ("Consequência sentida", "cada bloco do feed dele vem reponderado pelo ângulo da conta que ELE seguiu"),
    ("Virada", "os destaques de 4 colegas lado a lado, e depois os 3 posts que nunca apareceram para ele"),
    ("Nomeação", "Léo nomeia perfil algorítmico citando a conta que o próprio estudante seguiu"),
    ("Transferência", "pesquisa de trabalho só no TikTok: o risco é ___ porque ___, com marcador de mecanismo"),
]


def _nucleo_6ano(linha_c1="| C1 — aprende e devolve | Decidir · Resultado/Aha | segue 1 conta e vê o feed reponderar a cada bloco | pergunta por que o seu feed mudou |",
                 linha_c2="| C2 — perfil | fora | cabe na semana 4 do bimestre, que faz o mapeamento do próprio perfil | — |",
                 anatomia=None) -> str:
    passos = _ANATOMIA_6ANO if anatomia is None else anatomia
    return "\n".join([
        "# Núcleo narrativo — O algoritmo que me formou v1", "", "## 1. Descoberta central", "Eu só segui 1 conta.", "",
        "### 1.1 Conceitos do material vividos em tela",
        "| Conceito | Etapa | O que o estudante faz em tela | Como o professor aprofunda |",
        "|---|---|---|---|", linha_c1, linha_c2, "",
        "### 1.2 Anatomia do aha", "| Passo | Nesta missão |", "|---|---|",
        *[f"| {p} | {t} |" for p, t in passos], "", "## 4. As 6 etapas", "…",
    ])


def test_cobertura_conceitual_confere_o_nucleo_contra_o_mapa():
    """24/09/2026: o time pedagógico devolvia missões que não trabalhavam o conceito do material.
    O limiar do mapa precisa estar no Decidir ou no aha; conceito núcleo tem destino; a anatomia tem os
    seis passos. Defeito do mapa é ressalva: ele roda fora do loop, e o núcleo não o conserta."""
    from tools.profundidade import validar_cobertura

    ok = validar_cobertura(_nucleo_6ano(), _MAPA_6ANO, _MATERIAL_6ANO)
    assert ok["status"] == "aprovado", ok["achados"]
    assert ok["cobertos"] == ["C1"]

    def codigos(r):
        return {a["codigo"]: a["severidade"] for a in r["achados"]}

    so_no_navegar = validar_cobertura(_nucleo_6ano(linha_c1="| C1 | Navegar | segue 1 conta e vê o feed reponderar a cada bloco | — |"),
                                      _MAPA_6ANO, _MATERIAL_6ANO)
    assert codigos(so_no_navegar) == {"limiar-fora-do-aha": "bloqueio"}
    limiar_fora = validar_cobertura(_nucleo_6ano(linha_c1="| C1 | fora | o bimestre cobre isso na semana 2, com cartas | — |"),
                                    _MAPA_6ANO, _MATERIAL_6ANO)
    assert codigos(limiar_fora) == {"limiar-fora": "bloqueio"}
    sem_c2 = validar_cobertura(_nucleo_6ano(linha_c2=""), _MAPA_6ANO, _MATERIAL_6ANO)
    assert codigos(sem_c2) == {"conceito-sem-destino": "bloqueio"}
    fora_sem_motivo = validar_cobertura(_nucleo_6ano(linha_c2="| C2 | fora | não cabe | — |"), _MAPA_6ANO, _MATERIAL_6ANO)
    assert codigos(fora_sem_motivo) == {"fora-sem-justificativa": "bloqueio"}
    sem_virada = validar_cobertura(_nucleo_6ano(anatomia=[p for p in _ANATOMIA_6ANO if p[0] != "Virada"]),
                                   _MAPA_6ANO, _MATERIAL_6ANO)
    assert codigos(sem_virada) == {"anatomia-incompleta": "bloqueio"}
    marcador = validar_cobertura(_nucleo_6ano(anatomia=[(p, "<a preencher pelo autor do núcleo>") if p == "Virada" else (p, t)
                                                       for p, t in _ANATOMIA_6ANO]), _MAPA_6ANO, _MATERIAL_6ANO)
    assert codigos(marcador) == {"anatomia-incompleta": "bloqueio"}
    sem_tabelas = validar_cobertura("# Núcleo\n\n## 1. Descoberta central\nfrase", _MAPA_6ANO, _MATERIAL_6ANO)
    assert {"cobertura-ausente", "conceito-sem-destino", "anatomia-ausente"} <= set(codigos(sem_tabelas))

    # o mapa que cita o que o material não tem é ressalva, e não gasta a rodada do núcleo
    inventado = _MAPA_6ANO.replace('"Mapeando a bolha"', '"a bolha filtra o mundo inteiro de cada um"')
    r = validar_cobertura(_nucleo_6ano(), inventado, _MATERIAL_6ANO)
    assert (r["status"], codigos(r)) == ("amarelo", {"trecho-inexistente": "atencao"})
    # sem material, não há o que conferir na citação; sem mapa, a cobertura não é medida — e diz isso
    assert validar_cobertura(_nucleo_6ano(), _MAPA_6ANO, "")["status"] == "aprovado"
    assert codigos(validar_cobertura(_nucleo_6ano(), "", _MATERIAL_6ANO)) == {"mapa-ausente": "atencao"}
    print("   ✓ cobertura conceitual: limiar no Decidir/aha, núcleo com destino, anatomia completa; mapa ruim é ressalva")


def test_veredito_de_profundidade_e_contado_nas_notas():
    """O juiz escreve o status, mas quem decide são as notas que ele deu: 'aprovado' com o ápice em 2 é
    bloqueio. Nota ausente é bloqueio. A cobertura em código bloqueada bloqueia por cima."""
    import json as _json
    from tools.profundidade import consolidar, veredito_por_notas

    def juiz(status, **notas):
        base = {"P1": 3, "P2": 3, "P3": 3, "P4": 3, "P5": 3, "P6": 3, **notas}
        return f"# Juiz\n```json\n{_json.dumps({'status': status, 'notas': base, 'aha_em_uma_frase': 'eu achava que'})}\n```"

    assert consolidar(juiz("aprovado"))["status"] == "aprovado"
    incoerente = consolidar(juiz("aprovado", P3=2))
    assert incoerente["status"] == "bloqueado"
    assert {"veredito-incoerente", "p3-abaixo-do-corte"} <= {a["codigo"] for a in incoerente["achados"]}
    assert consolidar(juiz("aprovado", P5=2))["status"] == "amarelo"
    assert consolidar(juiz("aprovado", P6=1))["status"] == "bloqueado"
    # o juiz pode ser mais severo que as notas, nunca menos
    assert consolidar(juiz("bloqueado"))["status"] == "bloqueado"
    assert veredito_por_notas({"P1": 3})[0] == "bloqueado"
    assert veredito_por_notas({d: "4" for d in ("P1", "P2", "P3", "P4", "P5", "P6")})[0] == "aprovado"
    assert consolidar("")["status"] == "bloqueado"
    assert consolidar(juiz("aprovado"), {"status": "bloqueado", "achados": [
        {"severidade": "bloqueio", "codigo": "limiar-fora-do-aha", "resumo": "x"}]})["status"] == "bloqueado"
    assert consolidar(juiz("aprovado"))["aha_em_uma_frase"] == "eu achava que"
    print("   ✓ profundidade: status recontado nas notas, juiz só pode endurecer, cobertura bloqueada bloqueia")


def test_loop_do_nucleo_so_sai_com_micro_gate_e_profundidade():
    """Spoiler resolvido com missão rasa não é núcleo pronto: o loop só encerra com os dois aprovados. E a
    profundidade reprovada não trava a esteira — o freio é o parecer humano, que não aceita *de acordo* com 🔴."""
    import json as _json
    from agents.callbacks import KEY_PIPELINE_BLOQUEADO
    from agents.checkers import CoberturaConceitualAgent, ProfundidadeCheckAgent, SaidaDeLoopAgent
    from pipeline import passagem

    micro_ok = '# Micro\n```json\n{"agente": "micro-gate", "status": "passa", "falhas": []}\n```'

    def juiz(p3):
        notas = {"P1": 3, "P2": 3, "P3": p3, "P4": 3, "P5": 3, "P6": 3}
        return f"# Juiz\n```json\n{_json.dumps({'status': 'aprovado', 'notas': notas})}\n```"

    def rodar(texto_juiz):
        loop = LoopAgent(name="NucleoNarrativoLoop", max_iterations=2, sub_agents=[
            FakeAgent(name="A004NucleoNarrativo", key="nucleo_narrativo", text=_nucleo_6ano(), marker_key="vezes_nucleo"),
            CoberturaConceitualAgent(name="A006CoberturaConceitual"),
            FakeAgent(name="A007MicroGate", key="micro_gate_report", text=micro_ok),
            FakeAgent(name="A008JuizProfundidade", key="profundidade_report", text=texto_juiz),
            ProfundidadeCheckAgent(name="A011ProfundidadeCheck"),
            EnvelopeGateAgent(name="A012MicroGateCheck", rotulo="Micro-gate do núcleo", report_key="micro_gate_report",
                              status_key="micro_gate_status", round_key="micro_gate_rodada", max_rounds=2,
                              escalate_on_approve=False, block_pipeline_on_fail=False),
            SaidaDeLoopAgent(name="A013NucleoCheck", status_keys=["micro_gate_status", "profundidade_status"],
                             rodada_key="nucleo_rodada", max_rounds=2),
        ])
        insumos = FakeAgent(name="Insumos", key="mapa_conceitual", text=_MAPA_6ANO,
                            extra_delta={"material_anexado": _MATERIAL_6ANO})
        return asyncio.run(_run(SequentialAgent(name="R", sub_agents=[insumos, loop])))[1]

    st = rodar(juiz(3))
    assert (st["vezes_nucleo"], st["profundidade_status"], st["micro_gate_status"]) == (1, "aprovado", "aprovado")
    assert st["cobertura_resultado"]["cobertos"] == ["C1"]

    st = rodar(juiz(2))
    assert st["vezes_nucleo"] == 2, "profundidade reprovada devolve o núcleo mesmo com o micro-gate aprovado"
    assert (st["profundidade_status"], st["profundidade_rodada"]) == ("bloqueado", 2)
    assert st["profundidade_status_envelope"]["notas"]["P3"] == 2
    assert not st.get(KEY_PIPELINE_BLOQUEADO), "a profundidade não trava a esteira: quem trava é o parecer"
    fluxo = {**passagem.novo_fluxo(), "situacao": passagem.AGUARDANDO}
    assert passagem.DE_ACORDO not in passagem.acoes_possiveis(fluxo, "produto", st)

    # PROFUNDIDADE_ESTRITA=false: o núcleo ainda volta ao autor; só o veredito final vira 🟡
    import os as _os
    from unittest import mock as _mock
    with _mock.patch.dict(_os.environ, {"PROFUNDIDADE_ESTRITA": "false"}):
        st = rodar(juiz(2))
    assert (st["vezes_nucleo"], st["profundidade_status"]) == (2, "amarelo")
    assert "profundidade-nao-estrita" in {a["codigo"] for a in st["profundidade_status_envelope"]["achados"]}
    assert passagem.DE_ACORDO in passagem.acoes_possiveis(fluxo, "produto", st)
    print("   ✓ loop do núcleo: sai só com micro-gate e profundidade; profundidade 🔴 recusa o de acordo, sem travar a esteira")


def test_profundidade_entra_no_dossie_na_correcao_e_nos_artefatos():
    from pipeline.artifacts import ARTIFACT_FILES
    from pipeline.reexecucao import CHAVES_PRODUTO
    from tools.diagnostico import GATES
    from agents.produto import get_ideacao_mecanismos_agent, get_juiz_profundidade_agent, get_mapa_conceitual_agent

    assert any(g["status"] == "profundidade_status" and g["rodada"] == "profundidade_rodada" for g in GATES)
    novas = {"mapa_conceitual", "ideacao_mecanismos", "cobertura_report", "cobertura_resultado", "profundidade_report",
             "profundidade_status", "profundidade_status_envelope", "profundidade_rodada", "nucleo_rodada"}
    assert novas <= CHAVES_PRODUTO, novas - CHAVES_PRODUTO
    salvos = {k for k, _ in ARTIFACT_FILES}
    assert {"mapa_conceitual", "ideacao_mecanismos", "cobertura_report", "profundidade_report"} <= salvos
    # o juiz e o mapa emitem o mesmo resultado para a mesma entrada; a ideação inventa
    assert get_juiz_profundidade_agent().generate_content_config.seed is not None
    assert get_mapa_conceitual_agent().generate_content_config.seed is not None
    assert get_ideacao_mecanismos_agent().generate_content_config.temperature is None
    print("   ✓ profundidade no dossiê, apagada numa correção de produto, salva em artefato; juiz com seed, ideação livre")


def test_rastro_cobra_cada_etapa_pelo_que_e_dela():
    """25/09/2026, exp04ef1b: `[ABERTO — dono: produto: Ratificação formal do teto de texto…] —
    Resolvido em [D0-09]` barrou o PRD. O rastro só rodava em dev, que não reescreve a spec; o D0 já
    tinha fechado a pendência; e «ratificação» não contava como decisão humana, ao contrário das três
    «Homologação…» da mesma lista. Nenhuma das três coisas dependia de quem estava no parecer de dev."""
    from agents.design import build_design_stage
    from agents.dev import agentes_em_ordem, build_dev_stage
    from agents.produto import _build_spec_loop
    from config import get_settings
    from pipeline.passagem import chaves_da_etapa
    from tools.rastro import FONTES_DESIGN, FONTES_DEV, FONTES_SPEC, relatorio_lacunas, varrer_lacunas

    # a lista do bloco 12 e o bloco 13 da missão real, encurtados
    spec = ("## 12. Decisões fechadas neste gate\n"
            "- `[ABERTO — dono: produto: Ratificação formal do teto de texto entre 25 e 35 palavras por resumo]` (§6) — Resolvido em [D0-09].\n"
            "- `[ABERTO — dono: produto: Homologação dos limiares de H1 e H2]` (§9f) — Resolvido em [D0-11].\n"
            "## 13. Decisões D0\n"
            "- **[D0-9] Bloco 6:** Ratificado o teto de 25 a 35 palavras por resumo.\n"
            "- **[D0-11] Bloco 9f:** limiares homologados.\n")
    # o ambiente simulado carrega a spec copiada: a mesma linha, num documento de design
    estado = {"spec_missao": spec, "ambiente_simulado": spec + "\n## 14. Ambiente simulado\n", "handoff_dev": "ok"}
    r = varrer_lacunas(FONTES_DEV, estado, etapa_corrente="dev")
    assert r["status"] == "aprovado", r["achados"]
    assert {x["d0"] for x in r["resolvidos"]} == {"D0-9", "D0-11"}
    # a marca só fecha o que o bloco 13 decidiu: D0 inexistente é pendência aberta
    sem_d0 = spec.replace("- **[D0-9] Bloco 6:** Ratificado o teto de 25 a 35 palavras por resumo.\n", "")
    aberto = varrer_lacunas(FONTES_SPEC, {"spec_missao": sem_d0}, etapa_corrente="produto")
    assert [a["etapa"] for a in aberto["achados"]] == ["humano"], aberto["achados"]
    # ratificar é o mesmo ato de homologar: decisão do PO, 🟡 no parecer de produto
    ratifica = "- `[ABERTO — dono: produto: Ratificação formal do teto de texto]`\n"
    r = varrer_lacunas(FONTES_SPEC, {"spec_missao": ratifica}, etapa_corrente="produto")
    assert r["status"] == "amarelo" and r["achados"][0]["severidade"] == "decisao_humana", r["achados"]
    assert "⛔" not in relatorio_lacunas(r, "Rastro de lacunas da spec"), "decisão humana não é impedimento"

    # cada etapa bloqueia pelo que é dela
    lacuna_produto = "- `[ABERTO — dono: produto: definir o teto de palavras]`\n"
    lacuna_design = "- `[LACUNA — dono: jornada: tela de erro sem texto]`\n"
    r = varrer_lacunas(FONTES_SPEC, {"spec_missao": lacuna_produto + lacuna_design}, etapa_corrente="produto")
    por_etapa = {a["etapa"]: (a["severidade"], a.get("motivo")) for a in r["achados"]}
    assert r["status"] == "bloqueado" and por_etapa["produto"] == ("bloqueio", None)
    assert por_etapa["design"] == ("atencao", "adiante"), "lacuna de design na spec é cobrada no design"
    assert "A spec **não fecha**" in relatorio_lacunas(r, "Rastro de lacunas da spec")
    # no design, a de produto na spec aprovada é herança; a de design, dele
    r = varrer_lacunas(FONTES_DESIGN, {"spec_missao": lacuna_produto + lacuna_design}, etapa_corrente="design")
    por_etapa = {a["etapa"]: (a["severidade"], a.get("motivo")) for a in r["achados"]}
    assert por_etapa == {"produto": ("atencao", "heranca"), "design": ("bloqueio", None)}, por_etapa
    # mas a pendência de produto que um documento de design ESCREVEU é do design reescrever
    r = varrer_lacunas(FONTES_DESIGN, {"spec_missao": "ok", "jornada_telas": lacuna_produto}, etapa_corrente="design")
    assert r["status"] == "bloqueado", r["achados"]
    # em dev, o que é de design num documento de design é herança; o do handoff, de dev
    r = varrer_lacunas(FONTES_DEV, {"spec_missao": "ok", "jornada_telas": lacuna_design,
                                    "handoff_dev": "- `[LACUNA — dono: handoff: rota do painel]`\n"}, etapa_corrente="dev")
    por_etapa = {a["etapa"]: (a["severidade"], a.get("motivo")) for a in r["achados"]}
    assert por_etapa == {"design": ("atencao", "heranca"), "dev": ("bloqueio", None)}, por_etapa
    # sem etapa corrente (reavaliação avulsa), nada muda
    assert varrer_lacunas(FONTES_DEV, {"spec_missao": lacuna_produto})["status"] == "bloqueado"

    # e os três pontos estão ligados na esteira
    spec_loop = _build_spec_loop({}, get_settings(), 2)
    rastro_spec = next(a for a in spec_loop.sub_agents if a.name == "A053RastroSpec")
    saida = next(a for a in spec_loop.sub_agents if a.name == "A059SpecCheck")
    assert rastro_spec.etapa == "produto" and "rastro_spec_status" in saida.status_keys
    rastro_design = next(a for a in build_design_stage().sub_agents if a.name == "A092RastroDesign")
    assert rastro_design.name == "A092RastroDesign" and rastro_design.etapa == "design"
    a38 = next(a for a in agentes_em_ordem(build_dev_stage()) if a.name == "A107LacunaCheck")
    assert a38.etapa == "dev" and a38.fontes == FONTES_DEV
    assert "rastro_spec_status" in chaves_da_etapa("produto") and "rastro_design_status" in chaves_da_etapa("design")
    print("   ✓ rastro por etapa: D0 fecha, ratificação é do PO, cada etapa cobra o que é dela")


def test_kpis_leem_intervalo_de_etapas():
    """25/09/2026, exp04ef1b: «Ao entrar em cada etapa E1..E6» era lido como E1 e E6, e o `EVT-U02`
    deixava sem evento os KPIs de E2 e E4 — dois 🔴 de um evento que dispara em todas as etapas."""
    from tools.kpis import _etapas, validar_kpis

    assert _etapas("Ao entrar em cada etapa E1..E6") == {f"E{n}" for n in range(1, 7)}
    assert _etapas("de E2 a E4") == {"E2", "E3", "E4"} and _etapas("E2 e E4") == {"E2", "E4"}
    assert _etapas("E3-ALU-02") == set(), "tela não é etapa"
    prd = ("| KPI | Pergunta | Decisão que dispara | Corte | Tela | Evento |\n|---|---|---|---|---|---|\n"
           "| KPI-05 | quanto tempo leva? | > 10 min → encurtar | missao | `E2-ALU-01` | `EVT-U02` |\n\n"
           "| Evento | Verbo | Objeto | Quando dispara | `resultado` | `contexto` |\n|---|---|---|---|---|---|\n"
           "| `EVT-U02` | `progressed` | `etapa:entrar` | Ao entrar em cada etapa E1..E6 | `{\"etapa\": \"E2\"}` | — |\n")
    assert "kpi-tela-divergente" not in {a["codigo"] for a in validar_kpis(prd, "")["achados"]}
    print("   ✓ KPI: intervalo de etapas expandido")


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


# --------------------------------------------------------------------------- fidelidade ao PO (06/10/2026)
def _fixture_exp09(nome):
    return (Path(__file__).resolve().parent / "fixtures" / "exp09ef1b" / nome).read_text(encoding="utf-8")


def test_pedidos_do_po_acumulam_e_chegam_a_todas_as_etapas():
    """Na missão do 9º ano o segundo *refazer* apagou o primeiro, que definia os caminhos A/B e a frase
    da descoberta inteira. Agora todos os pedidos seguem, do mais antigo ao mais novo, nas notas que
    todo agente de toda etapa lê, e numa lista estruturada para o verificador de fidelidade."""
    import json as _json
    from pipeline import passagem

    fluxo = _json.loads(_fixture_exp09("fluxo.json"))
    pedidos = passagem.pedidos_do_po(fluxo)
    assert len(pedidos) == 2 and all(p["etapa"] == "produto" for p in pedidos)
    assert "Caminho A (maioria): não perguntou" in pedidos[0]["texto"]
    notas = passagem.notas_de_passagem(fluxo)
    assert notas.index("### Pedido 1") < notas.index("### Pedido 2") < notas.index("## Pareceres de quem liberou")
    assert "Caminho A (maioria): não perguntou" in notas, "o primeiro pedido não pode sumir"
    print("   ✓ pedidos do PO: os dois refazer da exp09ef1b chegam juntos, em ordem")


def test_de_acordo_com_conteudo_e_recusado():
    """06/10/2026: o *de acordo* do Dev trazia as perguntas de Canal B reescritas, e na última etapa ele
    só encerra a missão — o texto não chegou a documento nenhum."""
    import json as _json
    from types import SimpleNamespace
    from pipeline import passagem

    fluxo = _json.loads(_fixture_exp09("fluxo.json"))
    do_dev = next(p["comentario"] for p in fluxo["pareceres"] if p["etapa"] == "dev")
    assert passagem.parece_ajuste(do_dev, ultima_etapa=True)
    assert passagem.parece_ajuste("Conferi o PRD e os critérios de aceite; segue para a codificação sem mudanças.", ultima_etapa=True) == ""
    assert passagem.parece_ajuste("Pergunta 2: trocar o cenário por creches.", ultima_etapa=False)
    sessao = SimpleNamespace(papel="dev", assinatura_de=lambda etapa: "dev")
    aguardando = {"etapa": "dev", "situacao": passagem.AGUARDANDO, "versao": 1, "pareceres": []}
    try:
        passagem.aplicar(aguardando, passagem.DE_ACORDO, sessao, do_dev, {})
        raise AssertionError("o de acordo com perguntas novas não pode encerrar a missão")
    except passagem.DecisaoInvalida as exc:
        assert "Refazer" in str(exc)
    _, efeito = passagem.aplicar(aguardando, passagem.REFAZER, sessao, do_dev, {})
    assert efeito.tipo == "refazer" and "Pergunta" in efeito.pedido
    print("   ✓ de acordo com conteúdo: recusado, com o caminho do Refazer")


def test_fidelidade_confere_o_pedido_do_po_com_citacao():
    """Aceite com a exp09ef1b: o checklist sai dos dois pedidos e do briefing; a frase entre aspas das
    TRAVAS é conferida em código; o juiz só vale com citação que exista no documento."""
    import json as _json
    from pipeline import passagem
    from tools import fidelidade as fid

    fluxo = _json.loads(_fixture_exp09("fluxo.json"))
    pedidos = [(p["origem"], p["texto"]) for p in passagem.pedidos_do_po(fluxo)]
    itens = fid.montar_checklist(pedidos, _fixture_exp09("briefing.md"))
    por_tipo = {t: [i for i in itens if i["tipo"] == t] for t in ("ajuste", "validacao", "literal", "trava", "briefing")}
    assert len(por_tipo["ajuste"]) == 3 and any("Caminho A (maioria)" in i["texto"] for i in por_tipo["ajuste"])
    assert any("tem dois modos" in i["texto"] for i in por_tipo["validacao"]), "o checklist que o próprio PO escreveu"
    assert any("confirma ou muda sua escolha" in i["texto"] for i in por_tipo["briefing"])
    assert any("Mesa Aberta: 24 novas vagas" in i["texto"] for i in por_tipo["briefing"]), "elementos fixos sob subtítulo"
    assert len(itens) <= fid.MAX_ITENS and len({i["id"] for i in itens}) == len(itens)

    docs = {"nucleo_narrativo": _fixture_exp09("nucleo.md"), "spec_missao": _fixture_exp09("spec.md")}
    ab = next(i for i in por_tipo["ajuste"] if "Caminho A (maioria)" in i["texto"])
    revoto = next(i for i in por_tipo["briefing"] if "confirma ou muda" in i["texto"])
    trava = por_tipo["trava"][0]
    juiz = "```json\n" + _json.dumps({"decisoes": [
        {"id": ab["id"], "veredito": "violado", "citacao": "Caminho A (Investigação Ativa de Lacunas)",
         "explicacao": "o núcleo chama de A quem perguntou"},
        {"id": revoto["id"], "veredito": "conflito_com_regra", "explicacao": "Regra 7 do núcleo: decisão irreversível"},
        {"id": trava["id"], "veredito": "atendido", "citacao": "isto não está escrito em documento nenhum da missão"},
    ]}, ensure_ascii=False) + "\n```"
    r = fid.aplicar(itens, juiz, docs)
    cod = {a["id"]: (a["codigo"], a["severidade"]) for a in r["achados"]}
    assert cod[ab["id"]] == ("pedido-violado", "bloqueio")
    assert cod[revoto["id"]] == ("conflito-pedido-regra", "decisao_humana")
    assert cod[trava["id"]] == ("sem-prova", "bloqueio"), "citação que não está no documento não prova nada"
    assert r["status"] == "bloqueado"
    literal = next(i for i in itens if i["tipo"] == "literal")
    assert literal["id"] in {c["id"] for c in r["conferidos"]}, "frase da trava (com reticências) presente pelo começo"
    assert fid.aplicar([dict(literal, texto="Eu achei que estava avaliando, e quase deixei de fora quem mais precisava de ajuda")],
                       "", docs)["achados"][0]["codigo"] == "frase-do-po-alterada"
    # citações reais da primeira execução com IA, que a marcação do documento escondia
    for citacao in ("Ao clicar, a interface trava permanentemente (latch: locked), impedindo qualquer retorno",
                    "dois estudantes, Lia e Davi, por excesso de faltas injustificadas"):
        assert fid._norm(citacao) in fid._norm(docs["nucleo_narrativo"] + docs["spec_missao"]), citacao
    doc_norm = fid._norm(docs["nucleo_narrativo"] + docs["spec_missao"])
    assert fid._citacao_confere("Ao clicar, a interface trava permanentemente (latch: locked)... impedindo qualquer retorno", doc_norm)
    assert not fid._citacao_confere("Ao clicar, a interface trava permanentemente... o aluno pode votar de novo quando quiser", doc_norm)
    rel = fid.relatorio(r, itens, "exp09ef1b", "núcleo")
    assert "🔴" in rel and "🔵" in rel and '"status": "bloqueado"' in rel
    print(f"   ✓ fidelidade: {len(itens)} itens da exp09ef1b; A/B trocado bloqueia, revoto vira decisão do PO")


def test_semaforo_honesto_quando_um_gate_pede_uma_pessoa():
    """06/10/2026, exp09ef1b: a banca gravou `precisa_humano: true` com três ressalvas, e o texto do mesmo
    dossiê disse "Nada travando. As ressalvas acima são opcionais". E a colisão de slug, "decisão de
    produto" no próprio texto, nascia `atencao` e rodava depois do dossiê."""
    from tools import catalogo
    from tools.diagnostico import coletar, relatorio_markdown

    state = {"dev_status": "amarelo", "dev_status_envelope": {"status": "amarelo", "precisa_humano": True, "achados": [
        {"id": "DES-06", "severidade": "atencao", "resumo": "data-gpt-theme no bootstrap"},
        {"id": "DAD-10", "severidade": "atencao", "resumo": "expurgo sem scheduler"}]}}
    d = coletar(state)
    assert len(d["humanos"]) == 2 and d["precisa_humano"]
    texto = relatorio_markdown(d, "exp09ef1b", state=state)
    assert "Nada travando" not in texto and "o que falta são decisões" in texto

    ficha = {"slug": "exp09ef1b", "sessao": "nova", "descoberta": "outra"}
    col = catalogo.colisao_de_slug(ficha, [{"slug": "exp09ef1b", "sessao": "20260924-014635-exp09ef1b", "descoberta": "x"}])
    assert col and col[0]["severidade"] == "decisao_humana"
    assert catalogo.colisao_de_slug(ficha, [{"slug": "exp09ef1b", "sessao": "nova"}]) == []
    env = catalogo.relatorio_markdown({"status": "amarelo", "achados": col, "ficha": ficha, "total": 9, "vizinhas": []}, "exp09ef1b")
    assert '"precisa_humano": true' in env
    print("   ✓ semáforo: gate que pede pessoa vira decisão listada; colisão de slug é decisão de produto")


def test_conta_da_virada_refeita_em_codigo():
    """exp09ef1b: com só "menor custo por vaga", o projeto que deveria perder (Mesa Aberta, R$ 500) já
    vencia antes da virada. Com um critério de comprovação declarado, a mesma virada fecha."""
    from tools import mecanica as mec

    cab = "### 1.3 Conta da virada\n| Opção | Critério | Melhor quando | Peso | Antes | Depois |\n|---|---|---|---|---|---|\n"
    custo = ("| Mesa Aberta | custo por vaga (R$) | menor | 1 | 500 | 500 |\n"
             "| Ponto de Apoio | custo por vaga (R$) | menor | 1 | 667 | 667 |\n"
             "| Conexão para Continuar | custo por vaga (R$) | menor | 1 | 600 | 600 |\n")
    venc = "\n**Vencedor antes:** Conexão para Continuar · **Vencedor depois:** Mesa Aberta\n"
    so_custo = mec.validar(cab + custo + venc)
    assert {a["codigo"] for a in so_custo["achados"]} == {"conta-nao-fecha", "sem-virada"}
    comprovacao = ("| Mesa Aberta | registros comprovados | maior | 1 | 0 | 180 |\n"
                   "| Ponto de Apoio | registros comprovados | maior | 1 | 4 | 4 |\n"
                   "| Conexão para Continuar | registros comprovados | maior | 1 | 12 | 12 |\n")
    fecha = mec.validar(cab + custo + comprovacao + venc)
    assert fecha["status"] == "aprovado", fecha["achados"]
    assert fecha["calculo"]["antes"][0][0] == "Conexão para Continuar" and fecha["calculo"]["depois"][0][0] == "Mesa Aberta"
    assert mec.validar("## 1. Descoberta\n")["achados"][0]["codigo"] == "conta-ausente"
    assert mec.validar("### 1.3 Conta da virada\n**Não se aplica:** a missão não tem recomendação de máquina nem ranking.\n")["status"] == "aprovado"
    assert mec._numero("R$ 12.000") == 12000 and mec._numero("12,5") == 12.5
    print("   ✓ conta da virada: o custo por vaga da exp09ef1b não fecha; com comprovação declarada, fecha")


#: O glossário que a spec da exp09ef1b deveria ter trazido: valores tirados do briefing do PO.
_GLOSSARIO_EXP09 = """
## Glossário canônico

### Entidades
| Nome canônico | Variantes proibidas |
|---|---|
| Comissão Municipal de Recursos Comunitários | "Conselho Municipal de Apoio Social"; "Conselho Municipal de Recursos"; "Comissão de Recursos Comunitários" |
| Mesa Aberta | — |
| Ponto de Apoio | — |
| Conexão para Continuar | — |

### Personagens
| Nome | Idade | Papel na história |
|---|---|---|
| João | 14 | beneficiário do Mesa Aberta: nem sempre tem refeição no contraturno |
| Ana | 14 | beneficiária do Ponto de Apoio |
| Luana | 14 | beneficiária do Conexão para Continuar |

### Números
| O quê | Valor | Unidade |
|---|---|---|
| Vagas novas do Mesa Aberta | 24 | vagas |
| Dias de atendimento do Mesa Aberta | 2 | dias por semana |
| Vagas novas do Ponto de Apoio | 18 | vagas |
| Vagas novas do Conexão para Continuar | 20 | vagas |

### Rótulos de botão por ação
| Ação | Rótulo |
|---|---|
| Usar o banco padrão no preparo | Usar banco padrão |
| Gerar o cenário com IA | Gerar Cenário com IA |
| Liberar a missão para a turma | Liberar Missão Agora |
| Liberar a auditoria dos cadernos (Gate E4) | Liberar Auditoria dos Cadernos (Gate E4) |

### Arquivos
| Artefato | Nome do arquivo |
|---|---|
| Protótipo navegável | design/08-prototipo.html |
"""


def test_coerencia_entre_documentos_contra_o_glossario():
    """exp09ef1b: o órgão com quatro nomes, João/Ana/Luana (14 anos) como "Coordenação" na copy, o Mesa
    Aberta de 2 dias por semana com "180 dias" de registros, rótulos de botão em dobro e o QA citando um
    arquivo que não existe. Textos reais da execução; o glossário é o que a spec deveria ter trazido."""
    import re

    from tools import consistencia as cons

    spec = _fixture_exp09("spec.md") + _GLOSSARIO_EXP09
    docs = {"copy revisada": _fixture_exp09("copy_revisada.md"), "one-pager": _fixture_exp09("one_pager.md"),
            "jornada": _fixture_exp09("jornada.md"), "QA": _fixture_exp09("qa_entregaveis.md")}
    r = cons.validar(spec, docs)
    assert r["status"] == "bloqueado"
    por = lambda cod: [a for a in r["achados"] if a["codigo"] == cod]
    variantes = {re.search(r"«([^»]+)»", a["resumo"]).group(1) for a in por("variante-proibida")}
    assert variantes == {"Conselho Municipal de Recursos", "Conselho Municipal de Apoio Social",
                         "Comissão de Recursos Comunitários"}, variantes
    assert not [a for a in por("variante-proibida") if "«Comissão Municipal de Recursos Comunitários»" in a["resumo"].split(" é variante")[0]]
    assert {a["documento"] for a in por("papel-divergente")} == {"copy revisada", "one-pager"}
    assert any("Coordenação: João" in a["resumo"] for a in por("papel-divergente"))
    assert any("180 dias" in a["resumo"] for a in por("numero-divergente"))
    assert not any("18 vagas" in a["resumo"] for a in por("numero-divergente")), "as 18 vagas são do Ponto de Apoio"
    rotulos = " ".join(a["resumo"] for a in por("rotulo-divergente"))
    for visto in ("Usar Banco Padrão Oficial", "Gerar com IA", "Liberar para a Turma", "Liberar Gate E4"):
        assert f"«{visto}»" in rotulos, visto
    assert any("08-prototipo-navegavel.html" in a["resumo"] for a in por("arquivo-divergente"))

    # glossário com um quinto nome canônico: os quatro nomes que circularam são acusados, e a variante
    # que é pedaço do canônico ("Conselho Municipal de Recursos") só conta quando aparece solta
    quinto = _GLOSSARIO_EXP09.replace(
        '| Comissão Municipal de Recursos Comunitários | "Conselho Municipal de Apoio Social"; "Conselho Municipal de Recursos"; "Comissão de Recursos Comunitários" |',
        '| Conselho Municipal de Recursos Comunitários | "Conselho Municipal de Apoio Social"; "Conselho Municipal de Recursos"; '
        '"Comissão Municipal de Recursos Comunitários"; "Comissão de Recursos Comunitários" |')
    r4 = cons.validar(_fixture_exp09("spec.md") + quinto, docs)
    assert len({re.search(r"«([^»]+)»", a["resumo"]).group(1) for a in r4["achados"] if a["codigo"] == "variante-proibida"}) == 4
    limpo = cons.validar(_fixture_exp09("spec.md") + quinto, {"copy": "O Conselho Municipal de Recursos Comunitários abriu o edital."})
    assert limpo["status"] == "aprovado", limpo["achados"]

    # sem glossário: atenção, nunca silêncio
    assert [a["codigo"] for a in cons.validar(_fixture_exp09("spec.md"), docs)["achados"]] == ["glossario-ausente"]
    print("   ✓ coerência: 4 nomes do órgão, coordenadores de 14 anos, 180 dias, rótulos em dobro e arquivo inexistente")


def test_prd_coluna_inexistente_e_tipo_divergente():
    """exp09ef1b: a tabela de eventos da spec gravava em `exp09ef1b_sessoes.projeto_homologado`, que o DDL
    não declara, e o PRD usou `escola_id TEXT` (conforme a plataforma). Textos reais da execução.
    No Padrão Ouro (Etapa 2), a spec não dita tipos DDL SQL; a checagem contra a spec confere
    presença de colunas, e tipos de infraestrutura são validados contra a plataforma."""
    from tools import consistencia as cons
    from tools.rastro import validar_prd

    spec = _fixture_exp09("spec.md")
    da_spec = cons.conferir_colunas(spec, rotulo="spec")
    assert [a["codigo"] for a in da_spec] == ["coluna-inexistente"] and "projeto_homologado" in da_spec[0]["resumo"]

    prd = _fixture_exp09("prd_modelo_de_dados.md")
    assert not cons.conferir_colunas(prd), "sozinho, o modelo de dados do PRD é coerente"

    # Comparação entre dois DDLs completos (referência não é 'spec') bloqueia divergência de tipo:
    ddl_uuid = "CREATE TABLE exp09_extra (escola_id UUID NOT NULL);"
    contra = cons.conferir_colunas(prd, referencia=ddl_uuid, rotulo_ref="plataforma_legada")
    assert any(a["codigo"] == "tipo-divergente-de-plataforma_legada" and a["severidade"] == "bloqueio" for a in contra)

    # Contra a plataforma canônica: escola_id TEXT é o esperado, não gera bloqueio da plataforma
    contra_plat = cons.conferir_colunas(prd)
    assert not any(a["codigo"] == "tipo-divergente-da-plataforma" for a in contra_plat)

    # Se o PRD tentar usar escola_id UUID (divergindo da plataforma): bloqueia estritamente
    prd_divergente_plat = prd + "\n```sql\nCREATE TABLE exp09ef1b_errada (escola_id UUID NOT NULL);\n```\n"
    achados_plat = cons.conferir_colunas(prd_divergente_plat)
    assert any(a["codigo"] == "tipo-divergente-da-plataforma" and a["severidade"] == "bloqueio" for a in achados_plat)

    # o mesmo documento com os dois tipos internamente: bloqueio sem precisar da spec
    misturado = prd + "\n```sql\nCREATE TABLE exp09ef1b_extra (\n    id UUID PRIMARY KEY,\n    escola_id UUID NOT NULL\n);\n```\n"
    assert any(a["codigo"] == "tipo-divergente" and "escola_id" in a["resumo"] for a in cons.conferir_colunas(misturado))

    r = validar_prd(prd + "\nA tarefa T-004 grava em `exp09ef1b_sessoes.projeto_homologado`.\n", spec=spec)
    codigos = {a["codigo"] for a in r["achados"]}
    assert "coluna-inexistente" in codigos
    print("   ✓ PRD: escola_id TEXT segue a plataforma; tipos de infraestrutura validados estritamente")


def test_gate_de_coerencia_no_design():
    from agents.design import POSFIXO_RETRABALHO, build_design_stage

    nomes = [a.name for a in build_design_stage().sub_agents]
    assert nomes.index("A081PrototipoLint") < nomes.index("A082Consistencia") < nomes.index("QaDesignLoop")
    assert POSFIXO_RETRABALHO.index("A081PrototipoLintRetrabalho") < POSFIXO_RETRABALHO.index("A082ConsistenciaRetrabalho")
    from agents.design import get_consistencia_check

    estado = {"spec_missao": _fixture_exp09("spec.md") + _GLOSSARIO_EXP09,
              "copy_strings_revisada": _fixture_exp09("copy_revisada.md"),
              "prototipo_arquivo": "<html><body><div data-screen-id='E1-ALU-01'>Conselho Municipal de Recursos"
                                   "<button>Liberar para a Turma</button></div></body></html>"}

    class Semente(BaseAgent):
        @override
        async def _run_async_impl(self, ctx):
            yield Event(invocation_id=ctx.invocation_id, author=self.name, actions=EventActions(state_delta=estado))

    _, st = asyncio.run(_run(SequentialAgent(name="R", sub_agents=[Semente(name="S"), get_consistencia_check()])))
    assert st["consistencia_status"] == "bloqueado"
    env = st["consistencia_status_envelope"]
    assert {a["agente_responsavel"] for a in env["achados"] if a["codigo"] == "variante-proibida"} == {"copy-ptbr-revisao", "prototipo"}
    assert any(a["codigo"] == "coluna-inexistente" and a["severidade"] == "atencao" for a in env["achados"])
    print("   ✓ gate de coerência roda no design, depois do lint e antes do QA, e de novo no retrabalho")


def test_afirmacoes_do_qa_conferidas_em_codigo():
    """exp09ef1b: o QA aprovou escrevendo "todas as 16 telas ativas e vinculadas" ao lado do link de um Stitch
    com 6, e apontou `design/08-prototipo-navegavel.html`, que a esteira não grava. Textos reais."""
    from tools import afirmacoes as af

    qa, folha, jornada = _fixture_exp09("qa_entregaveis.md"), _fixture_exp09("stitch_telas.md"), _fixture_exp09("jornada.md")
    assert len(af.telas_do_inventario(jornada)) == 16 and len(af.telas_do_stitch(folha)) == 6

    cob = af.cobertura_stitch(folha, jornada)
    assert cob["status"] == "bloqueado" and cob["achados"][0]["agente_responsavel"] == "telas"
    assert "E3-ALU-01" in cob["faltando"] and "E0-PROF-01" not in cob["faltando"]

    r = af.conferir_qa(qa, folha, jornada)
    assert r["status"] == "bloqueado"
    assert {a["codigo"] for a in r["achados"]} == {"afirmacao-stitch", "arquivo-inexistente"}, r["achados"]
    assert any("16 telas no Stitch; o projeto tem 6" in a["resumo"] for a in r["achados"])
    assert any("08-prototipo-navegavel.html" in a["resumo"] for a in r["achados"])
    # "Todas as 16 telas … protótipo" e "16 de 16 telas no lint" batem com o inventário: não são acusadas
    assert not [a for a in r["achados"] if a["codigo"] == "afirmacao-inventario"]
    # com o protótipo à mão, a afirmação "16/16 no lint" passa a ser conferida contra o arquivo
    html = "<html><body>" + "".join(f"<section data-screen-id='{t}'></section>" for t in af.telas_do_inventario(jornada)[:12]) + "</body></html>"
    assert any(a["codigo"] == "afirmacao-prototipo" for a in af.conferir_qa(qa, folha, jornada, html)["achados"])
    # QA honesto: nada a acusar
    assert af.conferir_qa("Stitch com 6 telas: 6 de 16 telas desenhadas no Stitch. Protótipo em design/08-prototipo.html.",
                          folha, jornada)["status"] == "aprovado"

    # no loop: o envelope aprovado do QA é reescrito como bloqueado, com o ticket do Stitch para `telas`
    from agents.checkers import QaAfirmacoesAgent

    estado = {"qa_entregaveis_report": qa, "stitch_links": folha, "jornada_telas": jornada,
              "stitch_status": cob["status"], "stitch_status_envelope": {"status": cob["status"], "achados": cob["achados"]}}

    class Semente(BaseAgent):
        @override
        async def _run_async_impl(self, ctx):
            yield Event(invocation_id=ctx.invocation_id, author=self.name, actions=EventActions(state_delta=estado))

    assert extrair_envelope(qa)["status"] == "aprovado"
    _, st = asyncio.run(_run(SequentialAgent(name="R", sub_agents=[Semente(name="S"), QaAfirmacoesAgent(name="A089")])))
    env = extrair_envelope(st["qa_entregaveis_report"])
    assert env["status"] == "bloqueado" and inferir_status(st["qa_entregaveis_report"], env) == "bloqueado"
    assert {a["codigo"] for a in env["achados"]} >= {"afirmacao-stitch", "arquivo-inexistente", "stitch-incompleto"}
    assert any(a.get("agente_responsavel") == "telas" for a in env["achados"])
    assert st["qa_afirmacoes_status"] == "bloqueado"

    from agents.design import build_qa_design_loop

    # a banca de design vem antes do QA (08/10/2026); o QA, as afirmações e o veredito seguem em sequência
    nomes_qa = [a.name for a in build_qa_design_loop().sub_agents]
    i = nomes_qa.index("A088QaEntregaveis")
    assert nomes_qa[:3] == ["A085EscopoBanca", "A086Banca", "A087BancaConsolidacao"]
    assert nomes_qa[i:i + 3] == ["A088QaEntregaveis", "A089QaAfirmacoes", "A090QaEntregaveisCheck"]
    print("   ✓ afirmações do QA: 16 telas num Stitch com 6 e um arquivo que não existe reprovam a rodada")


def test_banco_de_conteudo_escrito_e_status_humano_no_brief():
    """exp09ef1b: o brief marcava "Homologado", "Pronto para corte" e "Roteiro aprovado" para conteúdo que ninguém
    escreveu (12 PDFs, atas, cadernos, a tabela da Linha 302), e a IA simulada tinha quatro falas. Brief real."""
    from tools import conteudo as ct
    from tools.rastro import validar_prd

    brief, spec = _fixture_exp09("brief_assets.md"), _fixture_exp09("spec.md")
    r = ct.validar(brief, "", spec)
    assert r["status"] == "bloqueado"
    humanos = " ".join(a["resumo"] for a in r["achados"] if a["codigo"] == "status-humano")
    for visto in ("Homologado", "Pronto para corte", "Roteiro aprovado"):
        assert f"«{visto}»" in humanos, visto
    assert any(a["codigo"] == "status-fora-do-vocabulario" and "Especificado" in a["resumo"] for a in r["achados"])
    # os itens de texto do brief real: documentos, textos e o roteiro do podcast; pictograma e prompt ficam fora
    assert set(r["ids"]) == {"doc-exp09ef1b-01", "doc-exp09ef1b-02", "doc-exp09ef1b-03", "txt-exp09ef1b-01",
                             "txt-exp09ef1b-02", "txt-exp09ef1b-03", "aud-exp09ef1b-01"}
    assert any(a["codigo"] == "banco-vazio" for a in r["achados"])
    assert ct.estados_de_fala(spec) == ["E1_INICIAL", "E2_INVESTIGANDO_CHAT", "E2_CADERNOS_DESBLOQUEADOS", "E4_AUDITORIA_REVELADA"]

    # banco parcial: os IDs sem bloco, o bloco raso e as falas que faltam são acusados
    corpo = "Registro de campo. " * 12
    banco = ("# Banco de conteúdo — exp09ef1b\n\n## Itens do brief\n\n"
             f"### txt-exp09ef1b-02 · Tabelas do transporte\n**Status:** escrito\n\n{corpo}\n\n"
             f"### doc-exp09ef1b-01 · Cadernos de campo\n**Status:** escrito\n\n{corpo}\n\n"
             "### doc-exp09ef1b-02 · Ficha\n**Status:** escrito\n\nCurta.\n\n"
             "## Falas da IA simulada\n\n### `E1_INICIAL` · boas-vindas\nBem-vindo à comissão.\n\n"
             "### Pergunta fora do tema\nVoltemos aos projetos.\n")
    p = ct.validar(brief.replace("Homologado", "escrito").replace("Pronto para corte", "escrito")
                   .replace("Roteiro aprovado", "a produzir").replace("Especificado", "rascunho"), banco, spec)
    codigos = [a["codigo"] for a in p["achados"]]
    assert "status-humano" not in codigos and "status-fora-do-vocabulario" not in codigos
    ausente = next(a for a in p["achados"] if a["codigo"] == "conteudo-ausente")
    assert "txt-exp09ef1b-01" in ausente["resumo"] and "aud-exp09ef1b-01" in ausente["resumo"]
    assert "txt-exp09ef1b-02" not in ausente["resumo"]
    assert any(a["codigo"] == "conteudo-raso" and "doc-exp09ef1b-02" in a["resumo"] for a in p["achados"])
    falas = " ".join(a["resumo"] for a in p["achados"] if a["codigo"] == "fala-ausente")
    assert "E4_AUDITORIA_REVELADA" in falas and "aviso de limite" in falas and "E1_INICIAL" not in falas
    assert ct.validar(brief, banco.replace("**Status:** escrito", "**Status:** homologado"), spec)["status"] == "bloqueado"

    # PRD: tarefa que consome conteúdo sem bloco bloqueia, salvo marcada; sem banco, não se acusa
    prd = ("| T-007 | Montar `base_dados_conselho.json` a partir de `txt-exp09ef1b-01` | RF-004 |\n"
           "| T-008 | Tabela do transporte (`txt-exp09ef1b-02`) | RF-005 |\n")
    assert [a["resumo"][:7] for a in ct.tarefas_sem_conteudo(prd, banco)] == ["`T-007`"]
    assert not ct.tarefas_sem_conteudo(prd.replace("| RF-004 |", "| RF-004 [BLOQUEADA — dono: conteúdo] |"), banco)
    assert not ct.tarefas_sem_conteudo(prd, "")
    assert "tarefa-sem-conteudo" in {a["codigo"] for a in validar_prd(prd, banco=banco)["achados"]}

    # os prompts: o brief tem vocabulário fechado, e o PRD lê o banco
    assert "`a produzir | rascunho | escrito`" in load_prompt("dev/100b_brief_assets.md")
    assert "{banco_conteudo?}" in load_prompt("dev/113_prd_writer.md")
    print("   ✓ banco de conteúdo: Homologado/Pronto para corte do brief real e os IDs sem texto bloqueiam")


def test_banco_de_conteudo_no_estagio_de_dev():
    from agents.dev import agentes_em_ordem, build_dev_stage
    from pipeline.artifacts import ARTIFACT_FILES

    nomes = [a.name for a in agentes_em_ordem(build_dev_stage())]
    # desde 07/10/2026 o banco e o verificador estão num loop: o bloqueio volta ao banco com o relatório
    assert nomes.index("HandoffLoop") < nomes.index("BancoLoop") < nomes.index("A107LacunaCheck")
    loop = next(a for a in agentes_em_ordem(build_dev_stage()) if a.name == "BancoLoop")
    assert [a.name for a in loop.sub_agents] == ["A104BancoConteudo", "A105ConteudoCheck", "A106BancoRodada"]
    assert ("banco_conteudo", "dev/01e-banco-conteudo.md") in ARTIFACT_FILES

    estado = {"spec_missao": _fixture_exp09("spec.md") + _GLOSSARIO_EXP09, "brief_assets": _fixture_exp09("brief_assets.md"),
              "banco_conteudo": "## Itens do brief\n\n### txt-exp09ef1b-01 · Base\n**Status:** escrito\n\n"
                                "O Conselho Municipal de Recursos recebeu três projetos. Coordenação: João. " * 3}

    class Semente(BaseAgent):
        @override
        async def _run_async_impl(self, ctx):
            yield Event(invocation_id=ctx.invocation_id, author=self.name, actions=EventActions(state_delta=estado))

    original = next(a for a in loop.sub_agents if a.name == "A105ConteudoCheck")
    check = original.model_copy(update={"parent_agent": None})
    _, st = asyncio.run(_run(SequentialAgent(name="R", sub_agents=[Semente(name="S"), check])))
    assert st["conteudo_status"] == "bloqueado"
    codigos = {a["codigo"] for a in st["conteudo_status_envelope"]["achados"]}
    assert {"status-humano", "conteudo-ausente", "variante-proibida", "papel-divergente"} <= codigos, codigos
    print("   ✓ banco de conteúdo entre o handoff e o rastro de lacunas, conferido também contra o glossário")


# --------------------------------------------------------------------- animação da esteira
def test_animacao_da_esteira_marca_o_passo_atual_e_o_que_ja_rodou():
    from pipeline.esteira_visual import etapa_do_agente, html_da_esteira, passos_da_esteira, situacao_dos_passos

    passos = passos_da_esteira()
    # o retrabalho cai no passo do agente pai, e a etapa sai do número
    assert etapa_do_agente("A075TelasRetrabalho") == "design"
    s = situacao_dos_passos(passos, "design", "A075TelasRetrabalho", ["A065FechaLacunas"])
    assert s[(75, "")] == "atual" and s[(65, "")] == "feito"
    assert all(v == "feito" for (n, _), v in s.items() if n < 64)  # produto inteiro antes do design
    assert s[(113, "")] == "pendente"
    # o contêiner paralelo pulsa o grupo inteiro
    s = situacao_dos_passos(passos, "produto", "A057Banca", [])
    assert s[(57, "a")] == s[(57, "b")] == "atual"
    h = html_da_esteira("design", "A075Telas", [], titulo="⏳", decorrido_s=65)
    assert 'class="p atual"' in h and "1 min 05 s" in h


# --------------------------------------------------------------------- custo da missão
def test_custo_soma_as_execucoes_e_cobra_cache_e_pensamento(monkeypatch):
    from datetime import date

    from tools import custo

    monkeypatch.setenv("COTACAO_USD_BRL", "5")
    # 1M de entrada (200 mil em cache), 100 mil de saída e 100 mil de pensamento, na tarifa de 2026
    t = {"entrada": 1_000_000, "cache": 200_000, "saida": 100_000, "pensamento": 100_000, "chamadas": 3}
    usd = custo.custo_usd(t, "gemini-3.8-flash", date(2026, 10, 12))
    assert abs(usd - (0.8 * 0.75 + 0.2 * 0.075 + 0.2 * 3.75)) < 1e-9
    assert custo.preco("gemini-3.8-flash", date(2027, 1, 1)) == (1.50, 7.50, 0.15)
    assert custo.custo_usd(t, "modelo-desconhecido") is None

    # o redator do PRD pode usar outro modelo; modelo sem preço não entra e é avisado
    e1 = custo.custo_da_execucao({"A004NucleoNarrativo": t}, "gemini-3.8-flash", {})
    e2 = custo.custo_da_execucao({"A113PrdWriter": t, "A014SecoesApoio": t}, "gemini-3.8-flash",
                                 {"A113PrdWriter": "outro-modelo"})
    assert e2["modelos_sem_preco"] == ["outro-modelo"] and e2["usd"] == e1["usd"]
    # refazer soma ao total, não substitui
    total = custo.acumular(custo.acumular(None, e1, ["produto"]), e2, ["design"])
    assert len(total["execucoes"]) == 2
    assert total["total"]["tokens"]["entrada"] == 3_000_000
    assert abs(total["total"]["brl"] - round(e1["brl"] + e2["brl"], 2)) < 0.011
    assert custo.brl(1234.5) == "R$ 1.234,50"


def test_custo_da_missao_sobrevive_ao_refazer():
    from pipeline.reexecucao import preparar_estado

    estado = {"custo_missao": {"execucoes": [{"usd": 1.0}], "total": {"usd": 1.0}}, "spec_missao": "x"}
    for etapa in ("produto", "spec", "design", "dev", "transversal"):
        limpo, _ = preparar_estado(estado, etapa)
        assert limpo["custo_missao"] == estado["custo_missao"], etapa


def test_cotacao_vem_da_ptax_e_cai_no_padrao_sem_rede(monkeypatch):
    import io
    import json as _json
    from datetime import date

    from tools import custo

    monkeypatch.delenv("COTACAO_USD_BRL", raising=False)
    custo._CACHE_PTAX.clear()
    corpo = _json.dumps({"value": [{"cotacaoVenda": 5.01, "dataHoraCotacao": "2026-10-08 13:00:00"},
                                   {"cotacaoVenda": 4.9892, "dataHoraCotacao": "2026-10-09 13:07:30"}]}).encode()
    monkeypatch.setattr(custo.urllib.request, "urlopen", lambda url, timeout: io.BytesIO(corpo))
    assert custo.ptax_venda(date(2026, 10, 12)) == (4.9892, "PTAX 09/10/2026")

    custo._CACHE_PTAX.clear()

    def sem_rede(url, timeout):
        raise OSError("sem rede")

    monkeypatch.setattr(custo.urllib.request, "urlopen", sem_rede)
    assert custo.cotacao_usd_brl() == (custo.COTACAO_PADRAO, "padrão (PTAX indisponível)")
    monkeypatch.setenv("COTACAO_USD_BRL", "5,10")
    assert custo.cotacao_usd_brl() == (5.10, "COTACAO_USD_BRL")


def test_restaurar_backup_nao_apaga_o_custo_e_soma_o_que_a_falha_gastou(tmp_path):
    import json as _json

    from pipeline.reexecucao import restaurar_backup
    from tools.custo import acumular, texto_ao_vivo

    linha = {"tokens": {"entrada": 1000, "saida": 10, "chamadas": 2}, "usd": 1.0, "brl": 5.0}
    antes = acumular(None, linha, ["produto"])                     # o que o backup guardou
    depois = acumular(antes, linha, ["design"])                    # uma execução completou depois do backup
    backup = tmp_path / ".correcoes" / "x"
    backup.mkdir(parents=True)
    (backup / "estado.json").write_text(_json.dumps({"spec_missao": "velha", "custo_missao": antes}))
    (tmp_path / "estado.json").write_text(_json.dumps({"spec_missao": "nova", "custo_missao": depois}))

    falha = {"tokens": {"entrada": 500, "saida": 5, "chamadas": 1}, "usd": 0.5, "brl": 2.5}
    restaurar_backup(tmp_path, backup, falha, ["dev"])
    estado = _json.loads((tmp_path / "estado.json").read_text())
    assert estado["spec_missao"] == "velha"                        # o documento volta
    custo = estado["custo_missao"]                                 # o custo não volta
    assert len(custo["execucoes"]) == 3 and custo["execucoes"][-1]["falhou"] is True
    assert custo["total"]["brl"] == 12.5
    # execução que caiu antes da primeira chamada ao modelo não vira linha
    restaurar_backup(tmp_path, backup, {"tokens": {"chamadas": 0}}, ["dev"])
    assert len(_json.loads((tmp_path / "estado.json").read_text())["custo_missao"]["execucoes"]) == 3
    assert texto_ao_vivo(falha, {"brl": 10}).startswith("💰 R$ 2,50 nesta execução · R$ 12,50 na missão")


def test_animacao_pinta_o_veredito_e_marca_o_que_nao_precisou_rodar():
    from pipeline.esteira_visual import cores_dos_passos, html_da_esteira, passos_da_esteira, situacao_dos_passos

    # o juiz 025 não emitiu evento e a execução já está no 027: ficou para trás sem rodar
    s = situacao_dos_passos(passos_da_esteira(), "produto", "A027GateEstruturalCheck", ["A024ContratoProdutoCheck"])
    assert s[(25, "")] == "pulado" and s[(24, "")] == "feito" and s[(28, "")] == "pendente"
    cores = cores_dos_passos({"gate_estrutural_status": "bloqueado", "bncc_status": "amarelo",
                              "micro_gate_status": "aprovado"})
    assert cores[(27, "")][0] == "vermelho" and cores[(46, "")][0] == "amarelo" and (12, "") not in cores
    h = html_da_esteira("produto", "A050PerguntasCheck", ["A027GateEstruturalCheck", "A046BnccCheck"],
                        gates={"gate_estrutural_status": "bloqueado", "bncc_status": "amarelo"}, escuro=True)
    assert 'class="p vermelho"' in h and 'class="p amarelo"' in h and "não precisou rodar" in h
    assert "class='esteira escuro'" in h


def test_fidelidade_entende_texto_ditado_sem_aspas_pelo_interprete():
    """exp03em1b (21/10/2026): o PO ditou o critério novo sem aspas («Remover “X” e usar: Y»), a correção aplicou Y
    letra por letra e a fidelidade saiu 🔴 por `citou-o-pedido`. O intérprete (LLM, só o pedido) diz o que é texto a pôr
    e a tirar; o código confere cada trecho no item e no documento."""
    import json as _json

    from tools import fidelidade as fid

    origem = "refazer Produto · produto · 21/10/2026 15:49:07"
    novo = "marcou corretamente no checklist os elementos de truncamento de eixo e recorte de escala como vetores de distorção"
    velho = "associando a desmontagem geométrica"
    itens = [
        {"id": "F1", "origem": origem, "tipo": "pedido",
         "texto": "Corrigir os critérios ternários do Canal A das seguintes habilidades."},
        {"id": "F2", "origem": origem, "tipo": "pedido",
         "texto": f"Remover “{velho}” e usar: {novo}."},
        {"id": "F3", "origem": origem, "tipo": "pedido",
         "texto": "Em processo: Abriu o anexo somente após o nudge do sistema e não voltou à base."},
    ]
    anterior = {"one_pager": f"**Atingiu:** Desmonta o gráfico {velho}.\n**Em processo:** Abre o anexo tarde."}
    docs = {"one_pager": f"**Atingiu:** {novo[0].upper()}{novo[1:]}.\n"
                         "**Em processo:** Abriu o anexo somente após o nudge do sistema e não voltou à base."}
    juiz = "```json\n" + _json.dumps({"decisoes": [
        {"id": "F1", "veredito": "atendido", "citacao": "Corrigir os critérios ternários do Canal A das seguintes habilidades."},
        {"id": "F2", "veredito": "atendido", "citacao": novo},
        {"id": "F3", "veredito": "atendido", "citacao": "Abriu o anexo somente após o nudge do sistema e não voltou à base."},
    ]}, ensure_ascii=False) + "\n```"

    def leitura(**por_id):
        base = {"F1": {"cabecalho": True}, "F2": {"inserir": [novo], "remover": [velho], "outras_exigencias": False},
                "F3": {"inserir": ["Abriu o anexo somente após o nudge do sistema e não voltou à base."],
                       "outras_exigencias": False}}
        base.update(por_id)
        return "```json\n" + _json.dumps({"itens": [{"id": k, **v} for k, v in base.items()]}, ensure_ascii=False) + "\n```"

    # sem o intérprete, o que a esteira fazia: a citação está no documento, mas também no pedido
    r = fid.aplicar(itens, juiz, docs, anteriores=anterior)
    assert {(a["id"], a["codigo"]) for a in r["achados"]} == {("F1", "citou-o-pedido"), ("F2", "citou-o-pedido")}
    # com ele: texto ditado no corpo, texto velho fora, e o cabeçalho vale pela prova dos itens que anuncia
    r = fid.aplicar(itens, juiz, docs, anteriores=anterior, interpretacao=fid.interpretacao(leitura(), itens))
    assert r["status"] == "aprovado", r["achados"]
    prova = {c["id"]: c["prova"] for c in r["conferidos"]}
    assert prova["F2"].startswith("texto ditado no documento") and prova["F1"].startswith("cabeçalho do pedido")

    # o texto velho ficou: bloqueio, mesmo com o novo no lugar
    com_velho = {"one_pager": docs["one_pager"] + f"\nO aluno desmonta o gráfico {velho}."}
    r = fid.aplicar(itens, juiz, com_velho, anteriores=anterior, interpretacao=fid.interpretacao(leitura(), itens))
    assert ("F2", "remocao-nao-aplicada", "bloqueio") in {(a["id"], a["codigo"], a["severidade"]) for a in r["achados"]}
    # ...a não ser que tenha saído do lugar pedido e fique só onde já estava por direito
    anterior2 = {"one_pager": anterior["one_pager"] + f"\nNa mecânica, o aluno vai {velho}."}
    docs2 = {"one_pager": docs["one_pager"] + f"\nNa mecânica, o aluno vai {velho}."}
    assert fid.aplicar(itens, juiz, docs2, anteriores=anterior2,
                       interpretacao=fid.interpretacao(leitura(), itens))["status"] == "aprovado"
    # sem versão anterior não há como contar: atenção, nunca bloqueio
    r = fid.aplicar(itens, juiz, docs2, interpretacao=fid.interpretacao(leitura(), itens))
    assert ("F2", "remocao-a-conferir", "atencao") in {(a["id"], a["codigo"], a["severidade"]) for a in r["achados"]}

    # o que o intérprete devolve só vale se está no item, letra por letra: trecho inventado é descartado
    inventado = fid.interpretacao(leitura(F2={"inserir": ["um critério que o PO nunca escreveu no pedido"],
                                              "outras_exigencias": False}), itens)
    assert inventado["F2"]["inserir"] == [] and fid.aplicar(itens, juiz, docs, anteriores=anterior,
                                                           interpretacao=inventado)["status"] == "bloqueado"
    # item que pede mais do que o texto (ou na dúvida, sem a resposta): a prova em código não basta
    mais = fid.interpretacao(leitura(F2={"inserir": [novo], "remover": [velho]}), itens)
    assert mais["F2"]["outras_exigencias"] is True
    assert "F2" in {a["id"] for a in fid.aplicar(itens, juiz, docs, anteriores=anterior, interpretacao=mais)["achados"]}
    # o veredito `violado` do juiz prevalece sobre o texto presente
    violado = juiz.replace('"F2", "veredito": "atendido"', '"F2", "veredito": "violado"')
    assert fid.aplicar(itens, violado, docs, anteriores=anterior,
                       interpretacao=fid.interpretacao(leitura(), itens))["status"] == "bloqueado"
    # cabeçalho com um item do mesmo pedido sem prova não se aprova pela vizinhança
    r = fid.aplicar(itens, juiz, {"one_pager": f"**Atingiu:** {novo}."}, anteriores=anterior,
                    interpretacao=fid.interpretacao(leitura(), itens))
    assert "F1" in {a["id"] for a in r["achados"]}
    # o intérprete só lê o pedido do PO: o briefing não entra
    assert [i["id"] for i in fid.para_o_interprete(itens + [{"id": "F9", "origem": "briefing", "tipo": "briefing",
                                                             "texto": "x"}])] == ["F1", "F2", "F3"]


def test_fidelidade_tem_interprete_deterministico_que_nao_ve_os_documentos():
    from agents.juiz import get_fidelidade_check

    a = get_fidelidade_check("AXFid", status_key="fidelidade_status", report_key="fidelidade_report",
                             documentos=["one_pager"], onde="teste")
    juiz, interprete = a.sub_agents
    assert interprete.output_key == "interpretacao_fidelidade_saida"
    assert interprete.generate_content_config.temperature == get_settings().temperatura_juiz
    assert interprete.generate_content_config.seed is not None
    assert "{interpretacao_entrada?}" in interprete.instruction
    assert "{fidelidade_documentos?}" not in interprete.instruction, "o intérprete lê só o pedido"


# --- exp02em1b (22/10/2026): o design saiu 🔴 com três falsos positivos de gate, nenhum defeito da missão ---------
_NOTAS_PARECER_EXP02EM1B = (
    "## Pareceres de quem liberou as etapas\n\n### Produto · produto · 21/10/2026 15:43:51\n\n> Propostas:\n"
    "> [PROPOSTA: validar com PO: Preservação de duas seções do DS (unooriaai + unoovista) em sessão de 50 minutos] → aprovado\n"
    "> [PROPOSTA: validar com PO: Sinalização voluntária de EM13CO08 no Unoovista sem pop-up impositivo] → aprovado\n")
_SPEC_GATE0_EXP02EM1B = (
    "# Spec — exp02em1b v1.2\n\n## 8. Professora, preparação e parametrização com IA\n"
    "1. Vocês acham que a rede entregou essa postagem às duas da manhã porque o texto era bom?\n"
    "2. O que o algoritmo ganha quando alguém fica acordado reagindo a uma postagem polêmica?\n"
    + "".join(f"- Linha {i} do roteiro do debate coletivo com a turma inteira sobre a amplificação do post.\n"
              for i in range(30))
    + "\n## 12. Decisões fechadas neste gate\n"
    "| Preservação de 2 seções do DS (`unooriaai` + `unoovista`) em aula de 50 min | `[PROPOSTA — validar com PO]` |\n"
    "| Sinalização voluntária de `EM13CO08` via menus contextuais sem pop-up impositivo | `[PROPOSTA — validar com PO]` |\n")
_D0_7 = ("| `[D0-7]` | `0.duas_secoes_ds` e `12.pendencia_duas_secoes` | Homologação da preservação das 2 seções do DS "
         "(`unooriaai` e `unoovista`) em aula de 50 minutos. | Parecer do responsável de produto (21/10/2026) | Não precisa (verde) |\n")
_D0_8 = ("| `[D0-8]` | `2.sinalizacao_voluntaria_co08` e `12.pendencia_co08` | Homologação da sinalização voluntária de "
         "`EM13CO08` via menus de contexto sem janelas impositivas. | Parecer do responsável de produto (21/10/2026) | "
         "Não precisa (verde) |\n")
_D0_CANAL_B = ("| `[D0-{n}]` | `9.componente_canal_b` e `12.pendencia_storypoll` | Adoção da alternativa de Modal Neutro de "
               "Verificação institucional para o Canal B. | Parecer do responsável de produto (21/10/2026) | Sim (amarelo) |\n")


def _saida_d0(tabela_passo2: str, bloco13: str, gate0: str = _SPEC_GATE0_EXP02EM1B) -> str:
    return ("## Passo 2 — Classificar e rotear\n\n| ID | Célula (bloco.campo) | Classe | Cor | Fonte de preenchimento | "
            "Quem consumiria |\n|---|---|---|---|---|---|\n" + tabela_passo2
            + "\n## Passo 5 — Spec consolidada\n\n" + gate0 + "\n## 13. Decisões D0\n\n| Decisão | Célula | Decisão tomada | "
            "Base | Reversível? |\n|---|---|---|---|---|\n" + bloco13
            + "\n## Passo 5b — Relatório de preenchimento\n\n" + "O D0 preencheu as lacunas com o parecer do produto. " * 3
            + "\n\n## Passo 6 — Devolutiva ao produto\n\nNada.\n\n```json\n"
            + json.dumps({"agente": "fecha-lacunas", "missao": "exp02em1b", "status": "aprovado", "achados": []}) + "\n```\n")


def _rodar_split_d0(estado, estrito=None):
    from agents.design import get_fecha_lacunas_split

    class Semente(BaseAgent):
        @override
        async def _run_async_impl(self, ctx):
            yield Event(invocation_id=ctx.invocation_id, author=self.name, actions=EventActions(state_delta=estado))

    split = get_fecha_lacunas_split()
    if estrito is not None:
        split.estrito = estrito
    _, st = asyncio.run(_run(SequentialAgent(name="R", sub_agents=[Semente(name="S"), split])))
    return st


def _codigos(st, chave="lacunas_status_envelope"):
    return {a["codigo"]: a for a in (st.get(chave) or {}).get("achados") or []}


def test_d0_fecha_lacuna_de_mecanica_pelo_parecer_do_po_sem_bloquear():
    """exp02em1b: o PO aprovou no parecer de produto as duas propostas de mecânica; o D0 aplicou o parecer e o gate o
    acusou de decidir no lugar do PO. Com parecer na sessão e a fonte citando-o, é ⚠️ a conferir; sem parecer, ⛔."""
    tabela = ("| L-07 | `0.duas_secoes_ds` / `12.pendencia_duas_secoes` | `mecanica` | Verde | Parecer humano do produto "
              "(21/10/2026) | D2, D5 |\n"
              "| L-08 | `2.voluntariedade_co08` / `12.pendencia_co08` | `mecanica` | Verde | Parecer humano do produto "
              "(21/10/2026) | D2, D4 |\n")
    fonte = _saida_d0(tabela, _D0_7 + _D0_8 + _D0_CANAL_B.format(n=9))
    st = _rodar_split_d0({"fechamento_lacunas": fonte, "spec_missao": _SPEC_GATE0_EXP02EM1B,
                          "notas_de_passagem": _NOTAS_PARECER_EXP02EM1B})
    achados = _codigos(st)
    assert st["lacunas_status"] == "amarelo", achados
    assert "decisao-de-produto-pelo-agente" not in achados
    assert achados["mecanica-pelo-parecer"]["severidade"] == "atencao" and "L-07" in achados["mecanica-pelo-parecer"]["resumo"]

    # sem parecer na sessão, citar um parecer não basta
    st = _rodar_split_d0({"fechamento_lacunas": fonte, "spec_missao": _SPEC_GATE0_EXP02EM1B})
    assert st["lacunas_status"] == "bloqueado" and "decisao-de-produto-pelo-agente" in _codigos(st)
    # com parecer, mas fechada por inferência do agente, continua ⛔
    inferida = tabela.replace("Parecer humano do produto (21/10/2026)", "inferência na faixa")
    st = _rodar_split_d0({"fechamento_lacunas": _saida_d0(inferida, _D0_7 + _D0_8), "spec_missao": _SPEC_GATE0_EXP02EM1B,
                          "notas_de_passagem": _NOTAS_PARECER_EXP02EM1B})
    assert st["lacunas_status"] == "bloqueado" and "decisao-de-produto-pelo-agente" in _codigos(st)


def test_d0_reescreve_o_proprio_bloco_13_sem_acusar_linhas_perdidas():
    """exp02em1b: a rodada 1 do D0 (reprovada) virou a base da preservação; a rodada 2 tirou do bloco 13 o [D0-7] e o
    [D0-8] e foi acusada de apagar o que «o autor de antes» escreveu — o autor era ela mesma. O texto do Gate 0
    (blocos 0–12) continua protegido."""
    rodada1 = _saida_d0("", _D0_7 + _D0_8 + _D0_CANAL_B.format(n=9))
    st1 = _rodar_split_d0({"fechamento_lacunas": rodada1, "spec_missao": _SPEC_GATE0_EXP02EM1B})
    assert "[D0-8]" in st1["spec_missao"]

    rodada2 = _saida_d0("", _D0_CANAL_B.format(n=7))
    st2 = _rodar_split_d0({**st1, "fechamento_lacunas": rodada2})
    assert "linhas-perdidas" not in _codigos(st2), _codigos(st2)

    # Desde 23/10/2026 a spec é montada em código (plano «Produto dono do contrato», PR 2): a pergunta que o D0 deixou de
    # copiar não some — fica do Gate 0 —, e a mudança que ele fez no texto do Gate 0 vira `[ABERTO — dono: PO]` no
    # cartão do parecer de design: decisão humana, que só bloqueia com ESTEIRA_ESTRITA.
    sem_pergunta = _saida_d0("", _D0_CANAL_B.format(n=7), gate0=_SPEC_GATE0_EXP02EM1B.replace(
        "2. O que o algoritmo ganha quando alguém fica acordado reagindo a uma postagem polêmica?\n", ""))
    st3 = _rodar_split_d0({**st1, "fechamento_lacunas": sem_pergunta}, estrito=False)
    aberto = _codigos(st3)["alterou-fora-do-proprio-bloco"]
    assert "o algoritmo ganha" in st3["spec_missao"] and "linhas-perdidas" not in _codigos(st3)
    assert aberto["severidade"] == "decisao_humana" and aberto["resumo"].startswith("[ABERTO — dono: PO")
    assert "o algoritmo ganha" in aberto["resumo"] and "[D0-8]" not in aberto["resumo"]
    assert st3["lacunas_status"] == "amarelo" and st3["lacunas_status_envelope"]["precisa_humano"]
    st3e = _rodar_split_d0({**st1, "fechamento_lacunas": sem_pergunta}, estrito=True)
    assert st3e["lacunas_status"] == "bloqueado"
    assert _codigos(st3e)["alterou-fora-do-proprio-bloco"]["severidade"] == "bloqueio"


def test_afirmacao_do_qa_em_telas_estados_conta_as_linhas_do_stitch():
    """exp02em1b: o QA escreveu «todas as 50 telas/estados» — a primeira tabela da folha do Stitch tem 50 linhas de
    estado de 19 telas — e o gate comparou 50 com 19."""
    from tools import afirmacoes as af

    ids = ["E0-PROF-01", "E1-ALU-01", "E2-ALU-01"]
    jornada = "## Seção 3\n\n| ID | Tela | Estados |\n|---|---|---|\n" + "\n".join(f"| {i} | t | padrão |" for i in ids)
    folha = "| Tela | Dispositivo |\n|---|---|\n" + "\n".join(
        f"| {i} — {e} | DESKTOP |" for i in ids for e in ("padrão", "erro"))
    linha = "2. Projeto Stitch `projects/1` (todas as {n} telas{s} geradas em escala de cinza lo-fi rigorosa).\n"
    assert af.conferir_qa(linha.format(n=6, s="/estados"), folha, jornada)["status"] == "aprovado"
    assert af.conferir_qa(linha.format(n=3, s="/estados"), folha, jornada)["status"] == "aprovado"
    for n, s in ((6, ""), (5, "/estados")):
        r = af.conferir_qa(linha.format(n=n, s=s), folha, jornada)
        assert [a["codigo"] for a in r["achados"]] == ["afirmacao-stitch"], (n, s, r["achados"])


def test_qa_que_relata_o_ticket_de_arquivo_inexistente_nao_e_acusado_de_novo():
    """exp01em1b (22/10/2026): na rodada 2 o QA relatou o ticket da rodada 1 — «Citação no relatório de QA ao caminho
    inexistente `design/04-copy-passada2.md`» — e o gate o acusou de citar o arquivo outra vez. Toda rodada que
    relatasse o ticket seria reprovada por ele. Só deixa de acusar o caminho que a rodada anterior acusou, com a
    negação colada nele."""
    from agents.checkers import QaAfirmacoesAgent
    from tools import afirmacoes as af

    p, outro = "design/04-copy-passada2.md", "design/06-copy-ptbr.md"
    relato = ("3. **Ticket QA-A1 (`arquivo-inexistente`):**\n"
              f"   - *Apontamento:* Citação no relatório de QA ao caminho inexistente `{p}`.\n"
              "   - *Situação na rodada 2:* **RESOLVIDO.** Referências agora apontam para `design/08-prototipo.html`.\n")
    assert af.conferir_qa(relato, ja_apontados=[p])["status"] == "aprovado"
    assert af.conferir_qa(f"- QA-A1: `{p}`, que a esteira não grava — RESOLVIDO.", ja_apontados=[p])["status"] == "aprovado"
    # sem rodada anterior que o tenha acusado, ou citado como real, continua reprovando
    for qa, apontados in ((relato, []), (f"- ONDE: `{p}`, tabela de strings.", [p]),
                          (f"- ONDE: `{p}` — não existe divergência entre as chaves.", [p]),
                          (f"- Chave inexistente no glossário; ver `{p}`, tabela.", [p])):
        assert af.conferir_qa(qa, ja_apontados=apontados)["status"] == "bloqueado", qa
    r = af.conferir_qa(f"- Caminho inexistente `{p}`; agora em `{outro}`.", ja_apontados=[p])
    assert [a["resumo"].split("`")[1] for a in r["achados"]] == [outro]

    # no loop: o envelope da rodada 1 ainda está no estado quando o A089 roda na rodada 2
    rodada1 = af.conferir_qa(f"- ONDE: `{p}`, tabela de strings.")
    assert af.arquivos_apontados(rodada1) == [p]
    estado = {"qa_entregaveis_report": relato + '\n```json\n{"agente": "qa-entregaveis", "status": "aprovado", "achados": []}\n```\n',
              "qa_afirmacoes_status_envelope": {"status": "bloqueado", "achados": rodada1["achados"]}}

    class Semente(BaseAgent):
        @override
        async def _run_async_impl(self, ctx):
            yield Event(invocation_id=ctx.invocation_id, author=self.name, actions=EventActions(state_delta=estado))

    _, st = asyncio.run(_run(SequentialAgent(name="R", sub_agents=[Semente(name="S"), QaAfirmacoesAgent(name="A089")])))
    assert st["qa_afirmacoes_status"] == "aprovado", st["qa_afirmacoes_status_envelope"]


def test_d0_so_aceita_o_parecer_humano_registrado_na_sessao():
    """«Parecer de Adequação Pedagógica» é relatório da esteira, e parecer sem data não se confere: os dois continuam ⛔."""
    from tools.decisoes import lacunas_fechadas_pelo_agente, lacunas_fechadas_pelo_parecer

    tabela = ("| ID | Célula | Classe | Cor | Fonte de preenchimento | Quem |\n|---|---|---|---|---|---|\n"
              "| L-07 | `0.x` | `mecanica` | Verde | {} | D2 |\n")
    humano = tabela.format("Parecer humano do produto (21/10/2026)")
    assert not lacunas_fechadas_pelo_agente(humano, _NOTAS_PARECER_EXP02EM1B)
    assert lacunas_fechadas_pelo_parecer(humano, _NOTAS_PARECER_EXP02EM1B)
    assert lacunas_fechadas_pelo_agente(humano)  # sem parecer na sessão
    for fonte in ("Parecer de Adequação Pedagógica (21/10/2026)", "parecer do gate estrutural", "Parecer do PO",
                  "Parecer do PO (15/10/2026)"):
        assert lacunas_fechadas_pelo_agente(tabela.format(fonte), _NOTAS_PARECER_EXP02EM1B), fonte


def test_rubrica_de_producao_do_podcast_nao_e_fala():
    """exp02em1b (22/10/2026): «Trilha sonora» aparecia duas vezes no §11 e, por isso, contava como personagem — as
    rubricas de música viraram falas literais, e o banco, que as reescreveu, foi reprovado no dev («1 de 15»). Nos 60
    one-pagers do bucket, «Áudio de vinheta» e «Efeito sonoro» tinham o mesmo destino."""
    from tools.conteudo_aprovado import literais

    s11 = ("## 11. Podcast de recapitulação\n\n**[Bloco 1: Abertura — ~15s]**\n"
           "- **Trilha sonora:** Batida eletrônica leve, moderna e curiosa.\n"
           "- **Alex:** E aí, galera! Bem-vindos ao podcast da missão de hoje, sobre o efeito amplificador.\n"
           "- **Sam:** Hoje a gente vai entender por que aquele post bombou às duas da manhã.\n"
           "- **Efeito sonoro:** Notificação de celular vibrando três vezes seguidas na mesa.\n"
           "- **Áudio de vinheta:** Assinatura sonora da Unooria tocando por alguns segundos.\n"
           "**[Bloco 5: Encerramento — ~15s]**\n"
           "- **Sam:** Pense nisso e converse com sua turma e seu professor. Valeu, e até a próxima missão!\n"
           "- **Alex:** Até mais, galera! Desconectem-se e descansem!\n"
           "- **Trilha sonora:** Encerramento enérgico que esmaece gradualmente.\n"
           "- **Efeito sonoro:** Notificação de celular vibrando três vezes seguidas na mesa.\n"
           "- **Áudio de vinheta:** Assinatura sonora da Unooria tocando por alguns segundos.\n\n## 12. Evidência\n")
    falas = literais(s11)["podcast"]
    assert len(falas) == 4 and all(not f.startswith(("Batida", "Encerramento", "Notificação", "Assinatura")) for f in falas)
    # personagem com nome composto continua sendo voz
    assert "Bom dia, turma! Hoje vamos falar de algoritmos." in literais(
        "## 11. Podcast\n- **Professora Helena:** Bom dia, turma! Hoje vamos falar de algoritmos.\n"
        "- **Professora Helena:** E vamos descobrir quem decide o que aparece no seu feed.\n## 12. x\n")["podcast"]


def test_a089_aceita_ticket_de_gate_sem_codigo():
    """exp03em1b (22/10/2026): a banca de design saiu bloqueada; o achado dela tem `id` (`DES-06`), não `codigo`
    (`tools/banca._envelope_json` só grava o que veio), e o A089 caiu com KeyError: 'codigo' ao montar o ticket —
    quatro execuções de design seguidas falharam sem veredito."""
    from agents.checkers import QaAfirmacoesAgent

    banca = {"id": "DES-06", "severidade": "bloqueio", "agente_responsavel": "telas", "dimensao": "banca_design_imersao",
             "resumo": "A tela E3-ALU-01 não mostra o feed do Unoovista que a spec descreve."}
    estado = {"qa_entregaveis_report": '```json\n{"agente": "qa-entregaveis", "status": "aprovado", "achados": []}\n```\n',
              "banca_design_status": "bloqueado",
              "banca_design_status_envelope": {"status": "bloqueado", "achados": [banca]}}

    class Semente(BaseAgent):
        @override
        async def _run_async_impl(self, ctx):
            yield Event(invocation_id=ctx.invocation_id, author=self.name, actions=EventActions(state_delta=estado))

    _, st = asyncio.run(_run(SequentialAgent(name="R", sub_agents=[Semente(name="S"), QaAfirmacoesAgent(name="A089")])))
    env = extrair_envelope(st["qa_entregaveis_report"])
    assert env["status"] == "bloqueado"
    ticket = next(a for a in env["achados"] if a.get("agente_responsavel") == "telas")
    assert ticket["id"] == "DES-06" and "DES-06" in st["qa_entregaveis_report"]


_RECUSA_STITCH = "Resource has been exhausted (e.g. check quota)."


def test_stitch_que_recusa_por_cota_vira_pendencia_externa_sem_retrabalho():
    """exp03em1b (22/10/2026): a cota do Stitch acabou; ele respondeu a recusa como texto numa resposta de sucesso, a
    esteira registrou «sem resposta do Stitch» nas 53 telas, conciliou e tentou de novo, e o ticket foi ao agente de
    telas — que não tinha o que consertar. A recusa vai ao relatório com o texto do Stitch, sem conciliação nem nova
    tentativa, e o bloqueio fica sem dono (pendência externa)."""
    from tools import afirmacoes as af
    from tools import stitch_geracao as sg
    from tools.stitch_cliente import recusa

    assert recusa({"texto": _RECUSA_STITCH}) and recusa({"texto": "The caller does not have permission"})
    assert not recusa({"texto": "Tela gerada."}) and not recusa({"screens": []}) and not recusa(None)

    chamadas, esperas = [], []

    def stitch(ferramenta, argumentos):
        chamadas.append(ferramenta)
        if ferramenta == "generate_screen_from_text":
            return {"texto": _RECUSA_STITCH}
        return {}

    itens = [{"id": "E1-ALU-01", "estado": e, "dispositivo": "MOBILE", "prompt": "Galeria.", "origem": "telas"}
             for e in ("padrão", "erro")]
    saida = sg.gerar(itens, {}, projeto="4044680601076201931", design_system="assets/1", titulo_projeto="x",
                     chamar=stitch, paralelo=2, esperar=esperas.append)
    assert all(r["erro"] == f"Stitch recusou: {_RECUSA_STITCH}" for r in saida["resultado"]), saida["resultado"]
    assert chamadas.count("generate_screen_from_text") == 2 and not esperas, "recusa não se concilia nem se repete"
    assert sg.recusa_da_geracao(saida) == _RECUSA_STITCH

    folha = "| Tela | Dispositivo |\n|---|---|\n"
    jornada = "## Seção 3\n\n| ID | Tela | Estados |\n|---|---|---|\n| E1-ALU-01 | t | padrão |\n"
    externo = af.cobertura_stitch(folha, jornada, recusa=_RECUSA_STITCH)
    a = externo["achados"][0]
    assert externo["status"] == "bloqueado" and a["codigo"] == "stitch-recusou" and a["agente_responsavel"] is None
    assert a["classe"] == "pendencia-externa" and _RECUSA_STITCH in a["resumo"]
    # sem recusa, a tela que falta continua indo ao agente de telas
    assert af.cobertura_stitch(folha, jornada)["achados"][0]["agente_responsavel"] == "telas"


def test_afirmacao_do_qa_e_conferida_na_parte_da_frase_em_que_esta():
    """exp03em1b (22/10/2026): «0 de 23 telas … geradas no Stitch; protótipo HTML navegável íntegro com 23 telas» — o
    gate viu «protótipo» na mesma linha e comparou o 0 do Stitch com as 23 telas do protótipo."""
    from tools import afirmacoes as af

    ids = [f"E1-ALU-0{i}" for i in range(1, 4)]
    jornada = "## Seção 3\n\n| ID | Tela | Estados |\n|---|---|---|\n" + "\n".join(f"| {i} | t | padrão |" for i in ids)
    html = "<html>" + "".join(f"<section data-screen-id='{i}'></section>" for i in ids) + "</html>"
    folha = "| Tela | Dispositivo |\n|---|---|\n"
    linha = ("**Inspeção:** Stitch conferido (projeto `projects/1` consultado via `list_screens`: 0 de 3 telas do "
             "inventário geradas no Stitch; protótipo HTML navegável íntegro com 3 telas inventariadas)")
    assert not af.conferir_qa(linha, folha, jornada, html)["achados"]
    # o mesmo, em duas frases da mesma linha
    duas = ("O gerador upstream do Stitch não realizou o upload das telas no projeto `projects/1` (0 de 3 telas no "
            "Stitch). A liberação deve ser homologada com base no protótipo HTML funcional (`design/08-prototipo.html`).")
    assert not af.conferir_qa(duas, folha, jornada, html)["achados"]
    # a afirmação errada sobre o protótipo, no trecho dele, continua acusada
    errada = linha.replace("íntegro com 3 telas inventariadas", "íntegro com 3 de 3 telas, e todas as 5 telas no lint")
    codigos = {a["codigo"] for a in af.conferir_qa(errada, folha, jornada, html)["achados"]}
    assert "afirmacao-prototipo" in codigos and "afirmacao-stitch" not in codigos, codigos


def test_lint_acusa_protótipo_que_mostra_todos_os_quadros_ao_mesmo_tempo():
    """exp03em1b (22/10/2026): `.quadro-tela { display: none }` escondia os quadros, mas `.moldura-mobile` e
    `.moldura-desktop` declaravam `display: flex` depois, com o mesmo peso — as 61 telas ficavam empilhadas (rolagem
    infinita) e os botões, que trocavam a tela ativa, pareciam não funcionar. O lint de texto deu 🟢."""
    from tools import prototipo as lint

    css = (".quadro-tela { display: none; position: relative; }\n"
           ".quadro-tela.tela-ativa { display: flex; flex-direction: column; }\n"
           ".moldura-mobile { width: 375px; height: 812px; display: flex; flex-direction: column; }\n"
           ".moldura-desktop { width: 980px; display: flex; }\n")
    quadros = ('<div class="quadro-tela moldura-desktop tela-ativa" data-screen-id="E0-PROF-01">E0-PROF-01</div>'
               '<div class="quadro-tela moldura-desktop" data-screen-id="E0-PROF-02">E0-PROF-02</div>'
               '<div class="quadro-tela moldura-mobile" data-screen-id="E1-ALU-01">E1-ALU-01</div>')
    html = f"<html><head><style>{css}</style></head><body>{quadros}</body></html>"
    r = lint.validar(html, ["E0-PROF-01", "E0-PROF-02", "E1-ALU-01"])
    achado = next(a for a in r["achados"] if a["codigo"] == "quadros-todos-visiveis")
    assert r["status"] == "bloqueado" and achado["severidade"] == "bloqueio" and ".moldura-" in achado["resumo"]

    # escondendo com um seletor mais forte que o da moldura, só o ativo aparece
    certo = html.replace(".quadro-tela { display: none;", ".quadro-tela:not(.tela-ativa) { display: none !important; }\n"
                                                         ".quadro-tela {")
    assert not [a for a in lint.validar(certo, ["E0-PROF-01", "E0-PROF-02", "E1-ALU-01"])["achados"]
                if a["codigo"] == "quadros-todos-visiveis"]
    # a regra de ocultar vindo depois da moldura também resolve
    depois = html.replace("</style>", ".quadro-tela:not(.tela-ativa) { display: none; }</style>")
    assert lint.validar(depois, ["E0-PROF-01", "E0-PROF-02", "E1-ALU-01"])["status"] == "aprovado"
    # protótipo que esconde pelo JavaScript (sem regra de ocultar no CSS) não é julgado aqui
    js = html.replace(".quadro-tela { display: none;", ".quadro-tela {")
    assert lint.validar(js, ["E0-PROF-01", "E0-PROF-02", "E1-ALU-01"])["status"] == "aprovado"


def test_stitch_desligado_na_execucao_nao_gera_nem_confere(monkeypatch):
    """22/10/2026: a cota do Stitch acabou com tantos repasses, e os prompts de geração ainda não foram refinados. O
    controle da barra lateral (desligado por padrão) vale para a execução inteira: com ele desligado, o modo vira
    `off` — sem ferramentas MCP, prompts dizendo `off`, nada gerado (A076), nada colhido nem conferido (A080)."""
    import config
    from agents.checkers import ArtefatosDesignAgent, StitchGeracaoAgent
    from tools.stitch_mcp import stitch_tools_or_empty

    monkeypatch.setenv("STITCH_MCP_MODE", "remote")
    monkeypatch.setenv("STITCH_API_KEY", "chave-de-teste")
    monkeypatch.delenv("STITCH_LIGADO", raising=False)
    s = config.AppSettings()
    monkeypatch.setattr(config, "get_settings", lambda: s)
    import tools.stitch_mcp as sm
    monkeypatch.setattr(sm, "get_settings", lambda: s, raising=False)
    try:
        config.fixar_stitch(None)
        assert s.stitch_mcp_mode == "off" and not s.is_stitch_enabled, "sem nada fixado, vale STITCH_LIGADO (padrão: não)"
        assert s.stitch_configurado and "Gerar telas no Stitch" in s.stitch_status_label
        assert stitch_tools_or_empty(["list_screens"]) == []
        config.fixar_stitch(True)
        assert s.stitch_mcp_mode == "remote" and s.is_stitch_enabled
        config.fixar_stitch(False)
        assert s.stitch_mcp_mode == "off"

        chamadas = []
        monkeypatch.setattr("tools.stitch_cliente.chamar", lambda *a, **k: chamadas.append(a) or {})
        estado = {"wireframes_cobertura": "## Geração no Stitch\n| ID | Estado | Dispositivo | Prompt |\n|---|---|---|---|\n"
                                          "| E1-ALU-01 | padrão | MOBILE | Galeria. |\n",
                  "jornada_telas": "## Seção 3\n\n| ID | Tela | Estados |\n|---|---|---|\n| E1-ALU-01 | t | padrão |\n",
                  "stitch_project_id": "4044680601076201931", "prototipo_html": "<html><body>x</body></html>"}

        class Semente(BaseAgent):
            @override
            async def _run_async_impl(self, ctx):
                yield Event(invocation_id=ctx.invocation_id, author=self.name, actions=EventActions(state_delta=estado))

        _, st = asyncio.run(_run(SequentialAgent(name="R", sub_agents=[
            Semente(name="S"), StitchGeracaoAgent(name="A076"), ArtefatosDesignAgent(name="A080")])))
        assert not chamadas, "desligado, o Stitch não é chamado"
        assert "stitch_status" not in st and "stitch_links" not in st and not st.get("stitch_geracao")
    finally:
        config.fixar_stitch(None)


def test_stitch_ligado_vem_do_env_fora_do_app(monkeypatch):
    import config

    monkeypatch.setenv("STITCH_MCP_MODE", "remote")
    monkeypatch.setenv("STITCH_API_KEY", "chave-de-teste")
    monkeypatch.setenv("STITCH_LIGADO", "true")
    config.fixar_stitch(None)
    assert config.AppSettings().is_stitch_enabled
    monkeypatch.setenv("STITCH_MCP_MODE", "off")
    assert not config.AppSettings().is_stitch_enabled and not config.AppSettings().stitch_configurado


def test_rastro_nao_le_pictograma_azul_como_pendencia():
    """exp02ef1b (23/10/2026): a missão usa «🟡 Brincar · 🔵 Estudar · 🟢 Comer» como pictogramas de intenção; o rastro
    lê 🔵 como «pendência a validar» e achou 13 — uma delas bloqueio de design, porque «Estilo wireframe» vinha depois.
    Pictograma entre aspas, numa série de cores ou como rótulo curto de célula não é marcador; o 🔵 canônico continua."""
    from tools.rastro import varrer_lacunas

    linhas_reais = (
        '| E3-ALU-01 | primeira vez (scaffolding 5s) | MOBILE | E3-ALU-01 — Trava-Enquadramento. Barra inferior com 3 chips '
        'seletores: "🟡 Brincar", "🔵 Estudar", "🟢 Comer". Rodapé: Botão primário "Confirmar Enquadramento" desabilitado. '
        'Estilo wireframe cinza puro. |\n'
        "- Seletor horizontal com 3 chips/pictogramas de intenção comunicativa (🟡 Brincar, 🔵 Estudar, 🟢 Comer).\n"
        "| `E3-ALU-01` | `e3.tag.estudar` | rótulo de UI | `unoogaleria` | 🔵 Estudar | 2 | `texto+ícone` | `plataforma simulada` |\n"
        "| 🟡 BRINCAR             | 🔵 ESTUDAR             | 🟢 COMER               | 📷 ENQUADRAR           |\n"
        '*"Toque no símbolo do que você quer mostrar (🟡 Brincar, 🔵 Estudar ou 🟢 Comer)."*\n'
        "| `E3-ALU-01` | E3 | ALU | Tocar (pictograma 🟡🔵🟢) → Arrastar e Redimensionar (moldura) → Tocar |\n")
    fontes = [{"chave": "wireframes_cobertura", "rotulo": "telas", "etapa_padrao": "design"}]
    r = varrer_lacunas(fontes, {"wireframes_cobertura": linhas_reais}, etapa_corrente="design")
    assert not [a for a in r["achados"] if a["tipo"] == "a_validar"], r["achados"]
    assert r["status"] == "aprovado"

    # o 🔵 de verdade continua sendo pendência
    canonicos = ("- Código EM13CO08: 🔵 a validar com a coordenação pedagógica.\n"
                 "| 5.1 | BNCC Computação — letramento digital mapeado | 🔵 |\n"
                 "| EF06CO03 | 🔵 a validar | evidência na Etapa 3 |\n")
    r = varrer_lacunas(fontes, {"wireframes_cobertura": canonicos}, etapa_corrente="design")
    assert len([a for a in r["achados"] if a["tipo"] == "a_validar"]) == 3, r["achados"]


def test_fidelidade_nao_le_descricao_como_ordem_de_preservacao():
    """exp01em1b (23/10/2026): o pedido de refazer trazia «Isso resolve P3 (…) e P6 (o apressado que não mexe no banco
    e o investigador que monta a correção têm desfechos diferentes no reteste).» — a oração relativa descreve o aluno,
    não manda preservar, e saía 🔴 `preservacao-sem-prova`. «Manter o restante» segue bloqueando sem prova: sem trocas
    pontuais, nada prova que o restante ficou (`test_preservar_todo_o_restante_se_prova_pelas_trocas`)."""
    from tools import fidelidade as fid

    descricao = ("Isso resolve P3 (a escolha do aluno tem consequência, a correção que ele monta muda o resultado) e P6 "
                 "(o apressado que não mexe no banco e o investigador que monta a correção têm desfechos diferentes no reteste).")
    assert not fid.so_preservacao(descricao)
    assert fid.so_preservacao("Não mexer no podcast.") and fid.so_preservacao("Manter o restante")
    # ordem de verdade, mesmo com «que não»: infinitivo ou dever
    assert fid.so_preservacao("O que NÃO deve mudar (preservar integralmente)")
    assert fid.so_preservacao("O que NÃO mudar: foco primário EF01CO06 intacto")
    assert not fid.so_preservacao("O resto é fricção de interface que não gera aprendizagem.")



def test_fidelidade_prova_texto_ditado_e_nao_cobra_remocao_do_que_nao_existia():
    """exp02em1b (23/10/2026), reprocesso de produto por correção pontual:
    - F5 era o próprio texto do overlay, entre aspas; o juiz disse «atendido» sem citação, o intérprete marcou «outras
      exigências», e o texto literal no one-pager não contou como prova → 🔴 `sem-prova`.
    - F27 mandava trocar «abre a Central de Apoio» no critério da CO08 — o critério dizia «acessa a central de apoio»;
      a troca foi feita, e a tabela de verbos ganhou «abre a Central de Apoio, seleciona relato e encaminha». 0 → 1
      ocorrência virou 🔴 `remocao-nao-aplicada`."""
    from tools import fidelidade as fid

    cta = ("Você é moderador do perfil do grêmio estudantil no Unoovista. O post sobre dietas viralizou e saiu da bolha da "
           "escola. O perfil é responsabilidade de vocês: analisem a repercussão e decidam o que fazer com a publicação.")
    origem = "refazer Produto · produto · 23/10/2026"
    # o título da seção seguinte do pedido, sem ponto final, gruda no item do texto ditado
    itens = [{"id": "F5", "origem": origem, "tipo": "pedido", "texto": f"“{cta}” 2. Central de Apoio — nova tela"},
             {"id": "F27", "origem": origem, "tipo": "pedido",
              "texto": "Atualizar o critério da CO08: onde diz “abre a Central de Apoio”, trocar para “encaminha um relato "
                       "pela Central de Apoio”."}]
    antes = ("Overlay: nenhum.\n| `encaminhar` relato | aciona o atendimento. |\n"
             "Atingiu: preserva privacidade, denuncia perfis e busca ajuda (acessa a central de apoio).")
    agora = (f"Overlay fixo nas bordas do Unoovista: “{cta}”\n"
             "| `encaminhar` relato | abre a Central de Apoio, seleciona relato e encaminha à escola. |\n"
             "Atingiu: preserva privacidade, denuncia perfis e encaminha um relato pela Central de Apoio.")
    juiz = '```json\n{"decisoes":[{"id":"F5","veredito":"atendido","citacao":""},' \
           '{"id":"F27","veredito":"atendido","citacao":"encaminha um relato pela Central de Apoio"}]}\n```'
    leitura = ('```json\n{"itens":[{"id":"F5","inserir":["' + cta + '"],"remover":[],"outras_exigencias":true,'
               '"cabecalho":false},{"id":"F27","inserir":["encaminha um relato pela Central de Apoio"],'
               '"remover":["abre a Central de Apoio"],"outras_exigencias":true,"cabecalho":false}]}\n```')
    r = fid.aplicar(itens, juiz, {"one_pager": agora}, anteriores={"one_pager": antes},
                    interpretacao=fid.interpretacao(leitura, itens))
    assert not [a for a in r["achados"] if a["severidade"] == "bloqueio"], r["achados"]
    assert "F5" in {c["id"] for c in r["conferidos"]}
    assert [(a["id"], a["codigo"]) for a in r["achados"]] == [("F27", "remocao-a-conferir")], r["achados"]

    # a remoção que existia e não saiu continua bloqueando
    r = fid.aplicar(itens[1:], juiz, {"one_pager": agora + "\nAtingiu: abre a Central de Apoio."},
                    anteriores={"one_pager": antes + "\nAtingiu: abre a Central de Apoio."},
                    interpretacao=fid.interpretacao(leitura, itens))
    assert [(a["id"], a["codigo"]) for a in r["achados"]] == [("F27", "remocao-nao-aplicada")], r["achados"]


def test_gates_e_geracao_consistentes_no_retrabalho_e_na_correcao_pontual():
    """23/10/2026 — três inconsistências entre geração e gate, cada uma sem resposta que passasse:
    - exp03ef1b: no retrabalho só o D0 roda; a spec que ele reemite não tem o bloco 14 do D9, e ninguém o regravava;
    - exp02ef1b: o PO colou os relatos de gate no refazer; a esteira os leu como ordem («manda tirar «Publicar no Álbum»»)
      e o editor desfez a troca que o próprio PO tinha pedido;
    - exp02ef1b: a troca pedida pelo PO mudou a linha do glossário da spec, e o gate de preservação a acusava de perdida."""
    from agents.design import get_fecha_lacunas_split
    from tools import fidelidade as fid

    # relato de gate colado não vira item
    colado = ("Ajustes necessários:\n❌ remocao-nao-aplicada · O pedido manda tirar «Publicar no Álbum», e nenhuma "
              "ocorrência saiu do documento: «Botão: “Publicar no Álbum” Ajuste solicitado: Para o exemplo de leitura:».\n")
    original = "Botão: “Publicar no Álbum”\nAjuste solicitado: Botão: “Colocar no álbum”."
    itens = fid.montar_checklist([("refazer Design · design · 23/10 13:24", original), ("refazer Design · design · 23/10 14:37", colado)], "")
    assert not [i for i in itens if "manda tirar" in i["texto"] or "remocao-nao-aplicada" in i["texto"]], itens
    assert fid.sem_relatos_de_gate(colado).strip() == "Ajustes necessários:"
    # o que o PO escreveu depois da seta é dele e fica
    assert fid.sem_relatos_de_gate("❌ sem-codigo · Nenhum código no bloco 11. -> as habilidades foram trabalhadas") == "as habilidades foram trabalhadas"

    gate0 = ("# Spec — exp03ef1b\n\n## 8. Professora\n" + "".join(f"- Roteiro {i} do debate com a turma sobre a foto da escola.\n" for i in range(30))
             + "\n## Glossário canônico\n| Ação | Rótulo |\n|---|---|\n| Confirmar o segundo envio na Fase 5B | `Publicar no Álbum` |\n")
    bloco14 = "## 14. Ambiente simulado (D9)\n- **Nome do ambiente que o estudante vê:** Unoojornal\n- **Ponte de importação:** `@edu/ui/ds-unoojornal`\n"
    aceita = gate0 + "\n## 13. Decisões D0\n| `[D0-1]` | x |\n\n" + bloco14

    def saida_d0(spec):
        return ("## Passo 5 — Spec consolidada\n\n" + spec + "\n## Passo 5b — Relatório de preenchimento\n\n"
                + "O D0 preencheu as lacunas desta rodada de retrabalho. " * 3 + "\n\n## Passo 6 — Devolutiva\n\nNada.\n"
                '```json\n{"agente": "fecha-lacunas", "status": "aprovado", "achados": []}\n```\n')

    def rodar(estado, estrito=False):
        class Semente(BaseAgent):
            @override
            async def _run_async_impl(self, ctx):
                yield Event(invocation_id=ctx.invocation_id, author=self.name, actions=EventActions(state_delta=estado))
        split = get_fecha_lacunas_split()
        split.estrito = estrito
        _, st = asyncio.run(_run(SequentialAgent(name="R", sub_agents=[Semente(name="S"), split])))
        return st

    # retrabalho do D0 sem o bloco 14: ele volta da versão aceita, e nada é acusado de perdido
    st = rodar({"fechamento_lacunas": saida_d0(gate0 + "\n## 13. Decisões D0\n| `[D0-1]` | x |\n"), "spec_missao": aceita})
    assert "Ponte de importação" in st["spec_missao"] and st["lacunas_status"] != "bloqueado", st.get("lacunas_status_envelope")

    # A troca que o PO pediu em design muda a linha do glossário, que é texto do Gate 0. Desde 23/10/2026 a spec é
    # montada em código: a troca não entra na spec de produto — vale, mas no documento de produto (plano «Produto dono
    # do contrato», D4 e D11) — e vira `[ABERTO — dono: PO]` no cartão do parecer, dizendo que o PO a pediu.
    trocada = aceita.replace("`Publicar no Álbum`", "`Colocar no álbum`")
    pedidos = [{"etapa": "design", "texto": original}]
    st = rodar({"fechamento_lacunas": saida_d0(trocada.split("\n## 14")[0]), "spec_missao": aceita, "pedidos_do_po": pedidos})
    achados = {a["codigo"]: a for a in (st.get("lacunas_status_envelope") or {}).get("achados") or []}
    aberto = achados["alterou-fora-do-proprio-bloco"]
    assert "`Publicar no Álbum`" in st["spec_missao"] and "Colocar no álbum" not in st["spec_missao"]
    assert aberto["severidade"] == "decisao_humana" and "o PO mandou trocar" in aberto["resumo"], aberto
    assert "linhas-perdidas" not in achados and st["lacunas_status"] == "amarelo"
    # sem pedido que cite o texto, a mesma mudança é do D0 — e, com ESTEIRA_ESTRITA, bloqueia
    st = rodar({"fechamento_lacunas": saida_d0(trocada.split("\n## 14")[0]), "spec_missao": aceita}, estrito=True)
    aberto = {a["codigo"]: a for a in st["lacunas_status_envelope"]["achados"]}["alterou-fora-do-proprio-bloco"]
    assert st["lacunas_status"] == "bloqueado" and "o PO mandou trocar" not in aberto["resumo"]
