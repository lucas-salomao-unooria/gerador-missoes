"""Testes do rastreamento detalhado de custos, tokens, etapas e painel administrativo."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict

import pytest


def test_enriquecer_tokens_e_decomposicao_financeira(monkeypatch: pytest.MonkeyPatch) -> None:
    from tools import custo

    monkeypatch.setenv("COTACAO_USD_BRL", "5.00")
    bruto = {
        "entrada": 100_000,
        "cache": 60_000,
        "ferramentas_entrada": 5_000,
        "saida": 10_000,
        "pensamento": 5_000,
        "maior_entrada": 50_000,
        "chamadas": 4,
        "do_cache": 1,
    }
    enriq = custo.enriquecer_tokens(bruto)
    assert enriq["entrada"] == 100_000
    assert enriq["cache"] == 60_000
    assert enriq["entrada_sem_cache"] == 40_000
    assert enriq["taxa_cache_pct"] == 60.0
    assert enriq["ferramentas_entrada"] == 5_000
    assert enriq["saida"] == 10_000
    assert enriq["pensamento"] == 5_000
    assert enriq["saida_total"] == 15_000
    assert enriq["taxa_pensamento_pct"] == 33.3
    assert enriq["total_tokens"] == 115_000
    assert enriq["maior_entrada"] == 50_000
    assert enriq["chamadas"] == 4
    assert enriq["do_cache"] == 1

    # gemini-3-flash-preview: entrada=$0.50/1M, saida=$3.00/1M, cache=$0.05/1M
    det = custo.detalhar_custo_usd(bruto, "gemini-3-flash-preview", dia=date(2026, 11, 1), cotacao=5.0)
    assert det is not None
    # 40k * $0.50/1M = $0.02
    assert det["usd_entrada_sem_cache"] == pytest.approx(0.02, abs=1e-6)
    # 60k * $0.05/1M = $0.003
    assert det["usd_cache"] == pytest.approx(0.003, abs=1e-6)
    # 10k * $3.00/1M = $0.03
    assert det["usd_saida"] == pytest.approx(0.03, abs=1e-6)
    # 5k * $3.00/1M = $0.015
    assert det["usd_pensamento"] == pytest.approx(0.015, abs=1e-6)
    # economia cache: 60k * ($0.50 - $0.05)/1M = $0.027
    assert det["economia_cache_usd"] == pytest.approx(0.027, abs=1e-6)
    assert det["usd"] == pytest.approx(0.02 + 0.003 + 0.03 + 0.015, abs=1e-6)
    assert det["brl"] == pytest.approx(det["usd"] * 5.0, abs=1e-4)


def test_mapeamento_de_etapa_do_agente() -> None:
    from tools import custo

    assert custo.etapa_do_agente("A001DecisorEscopo") == "produto"
    assert custo.etapa_do_agente("A063GateFinalProduto") == "produto"
    assert custo.etapa_do_agente("A064SuperAgenteDesign") == "design"
    assert custo.etapa_do_agente("A094QAEntregaveisDesign") == "design"
    assert custo.etapa_do_agente("A095BancaEntradaDevA") == "dev"
    assert custo.etapa_do_agente("A113PrdWriter") == "dev"
    assert custo.etapa_do_agente("A127ConsolidacaoAprendizado") == "transversal"
    assert custo.etapa_do_agente("hifi:lote-1") == "prototipo-hifi"
    assert custo.etapa_do_agente("ClassificadorDeSentido:produto") == "produto"
    assert custo.etapa_do_agente("ClassificadorDeSentido:design") == "design"
    assert custo.etapa_do_agente("ClassificadorDeSentido:dev") == "dev"
    assert custo.etapa_do_agente("A000EditorPontual", etapas_execucao=["design"]) == "design"


def test_registrar_e_consumir_uso_externo_dict_e_adk_state() -> None:
    from google.adk.sessions.state import State
    from tools import custo

    # 1. Dict comum
    estado_dict: Dict[str, Any] = {}
    custo.registrar_uso_externo(
        estado_dict,
        "A000EditorPontual",
        {"entrada": 1200, "cache": 400, "saida": 300, "pensamento": 100, "maior_entrada": 1200, "chamadas": 1},
        modelo="gemini-3.8-flash",
        etapa="produto",
    )
    custo.registrar_uso_externo(
        estado_dict,
        "A000EditorPontual",
        {"entrada": 800, "cache": 200, "saida": 150, "pensamento": 50, "maior_entrada": 800, "chamadas": 1},
        modelo="gemini-3.8-flash",
        etapa="produto",
    )
    por_ag, modelos = custo.consumir_uso_externo(estado_dict)
    assert custo.KEY_USO_EXTERNO not in estado_dict
    assert por_ag["A000EditorPontual:produto"]["entrada"] == 2000
    assert por_ag["A000EditorPontual:produto"]["cache"] == 600
    assert por_ag["A000EditorPontual:produto"]["saida"] == 450
    assert por_ag["A000EditorPontual:produto"]["pensamento"] == 150
    assert por_ag["A000EditorPontual:produto"]["maior_entrada"] == 1200
    assert por_ag["A000EditorPontual:produto"]["chamadas"] == 2
    assert modelos["A000EditorPontual:produto"] == "gemini-3.8-flash"
    assert custo.etapa_do_agente("A000EditorPontual:produto") == "produto"

    # 2. ADK State (não herda de dict)
    adk_state = State(value={}, delta={})
    custo.registrar_uso_externo(
        adk_state,
        "A000ConversaEtapa",
        {"entrada": 5000, "cache": 3000, "saida": 400, "pensamento": 200, "maior_entrada": 5000, "chamadas": 1},
        modelo="gemini-3-flash-preview",
        etapa="design",
    )
    por_ag2, modelos2 = custo.consumir_uso_externo(adk_state)
    assert por_ag2["A000ConversaEtapa:design"]["entrada"] == 5000
    assert modelos2["A000ConversaEtapa:design"] == "gemini-3-flash-preview"
    assert custo.etapa_do_agente("A000ConversaEtapa:design") == "design"


def test_custo_da_execucao_acumular_e_detalhar_missao(monkeypatch: pytest.MonkeyPatch) -> None:
    from tools import custo

    monkeypatch.setenv("COTACAO_USD_BRL", "5.00")

    por_agente_exec1 = {
        "A001DecisorEscopo": {
            "entrada": 50_000,
            "cache": 20_000,
            "ferramentas_entrada": 0,
            "saida": 4_000,
            "pensamento": 2_000,
            "maior_entrada": 30_000,
            "chamadas": 2,
        },
        "A064SuperAgenteDesign": {
            "entrada": 80_000,
            "cache": 50_000,
            "ferramentas_entrada": 1_000,
            "saida": 8_000,
            "pensamento": 4_000,
            "maior_entrada": 45_000,
            "chamadas": 3,
        },
    }
    modelos_exec1 = {
        "A001DecisorEscopo": "gemini-3-flash-preview",
        "A064SuperAgenteDesign": "gemini-3.8-flash",
    }
    linha1 = custo.custo_da_execucao(
        por_agente_exec1,
        "gemini-3.8-flash",
        modelos_exec1,
        etapas=["produto", "design"],
        duracao_s=42.5,
    )
    assert linha1["duracao_s"] == 42.5
    assert "produto" in linha1["por_etapa"]
    assert "design" in linha1["por_etapa"]
    assert linha1["por_etapa"]["produto"]["tokens"]["entrada"] == 50_000
    assert linha1["por_etapa"]["design"]["tokens"]["entrada"] == 80_000
    assert "gemini-3-flash-preview" in linha1["por_modelo"]
    assert "gemini-3.8-flash" in linha1["por_modelo"]

    acumulado = custo.acumular(None, linha1, ["produto", "design"])

    # Segunda execução: etapa dev
    por_agente_exec2 = {
        "A113PrdWriter": {
            "entrada": 100_000,
            "cache": 70_000,
            "ferramentas_entrada": 0,
            "saida": 15_000,
            "pensamento": 5_000,
            "maior_entrada": 60_000,
            "chamadas": 2,
        }
    }
    linha2 = custo.custo_da_execucao(
        por_agente_exec2,
        "gemini-3.8-flash",
        {"A113PrdWriter": "gemini-3.8-flash"},
        etapas=["dev"],
        duracao_s=30.0,
    )
    acumulado = custo.acumular(acumulado, linha2, ["dev"])

    estado = {custo.KEY_CUSTO: acumulado}
    det = custo.detalhar_missao(estado)
    assert det["tem_dados"] is True
    assert det["num_execucoes"] == 2
    assert det["tokens"]["entrada"] == 230_000
    assert det["tokens"]["cache"] == 140_000
    assert det["tokens"]["entrada_sem_cache"] == 90_000
    assert det["tokens"]["saida"] == 27_000
    assert det["tokens"]["pensamento"] == 11_000
    assert det["tokens"]["saida_total"] == 38_000
    assert {"produto", "design", "dev"}.issubset(set(det["por_etapa"].keys()))
    assert len(det["por_agente"]) == 3
    soma_pct = sum(b["pct_custo"] for b in det["por_etapa"].values())
    assert soma_pct == pytest.approx(100.0, abs=0.3)


def test_consolidar_missoes_e_session_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from pipeline import session_store
    from tools import custo

    monkeypatch.setenv("COTACAO_USD_BRL", "5.00")
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))

    linha = custo.custo_da_execucao(
        {
            "A001DecisorEscopo": {"entrada": 20_000, "cache": 10_000, "saida": 2_000, "pensamento": 1_000, "chamadas": 1},
            "A113PrdWriter": {"entrada": 40_000, "cache": 20_000, "saida": 5_000, "pensamento": 2_000, "chamadas": 1},
        },
        "gemini-3.8-flash",
        {"A001DecisorEscopo": "gemini-3-flash-preview", "A113PrdWriter": "gemini-3.8-flash"},
        etapas=["produto", "dev"],
    )
    custo_missao = custo.acumular(None, linha, ["produto", "dev"])

    run_dir = tmp_path / "sessao_teste_1"
    run_dir.mkdir(parents=True)
    estado = {
        "slug_missao": "exp01-teste",
        "one_pager": "# Missão Teste\nConteúdo",
        custo.KEY_CUSTO: custo_missao,
    }
    import json
    (run_dir / "estado.json").write_text(json.dumps(estado), encoding="utf-8")
    resultado_fake = SimpleNamespace(
        state=estado,
        status="success",
        duration_seconds=12.5,
        gates={"gate_estrutural": "APROVADO"},
        step_thoughts={},
        attached_files=[],
    )
    session_store.save_session_record(
        run_dir=run_dir,
        session_id="sessao_teste_1",
        user_id="admin",
        prompt="Briefing teste",
        result=resultado_fake,
        messages=[{"role": "user", "content": "Briefing teste"}],
    )

    sessoes = session_store.list_saved_sessions()
    assert len(sessoes) == 1
    assert "custo_resumo" in sessoes[0]
    assert sessoes[0]["custo_resumo"]["brl"] == custo_missao["total"]["brl"]
    assert "produto" in sessoes[0]["custo_resumo"]["por_etapa"]
    assert "dev" in sessoes[0]["custo_resumo"]["por_etapa"]

    enriquecidas = session_store.carregar_custos_das_sessoes(sessoes)
    consolidado = custo.consolidar_missoes(enriquecidas)
    assert consolidado["num_missoes"] == 1
    assert consolidado["missoes_com_custo"] == 1
    assert consolidado["brl"] == pytest.approx(custo_missao["total"]["brl"], abs=0.01)
    assert "produto" in consolidado["por_etapa"]
    assert "dev" in consolidado["por_etapa"]
    assert len(consolidado["por_agente"]) == 2


def test_arquitetura_hibrida_modelos_camadas_e_orcamento_juiz(monkeypatch: pytest.MonkeyPatch) -> None:
    from google.adk.agents.llm_agent import LlmAgent

    from config import get_settings
    from pipeline.orchestrator import create_mission_orchestrator
    from tools import custo

    monkeypatch.setenv("COTACAO_USD_BRL", "5.00")
    settings = get_settings()
    assert settings.gemini_model == "gemini-3.8-flash"
    assert settings.gemini_model_classificador == "gemini-3.5-flash-lite"
    assert settings.gemini_model_parecer == "gemini-3.5-flash-lite"
    assert settings.thinking_budget == 8192
    assert settings.thinking_budget_juiz == 2048

    orch = create_mission_orchestrator()
    agentes: Dict[str, LlmAgent] = {}

    def _coletar(ag: Any) -> None:
        if isinstance(ag, LlmAgent):
            agentes[ag.name] = ag
        for sub in getattr(ag, "sub_agents", []) or []:
            _coletar(sub)

    _coletar(orch)

    # Autores permanecem em gemini-3.8-flash com thinking_budget=8192
    for nome_autor in ("A004NucleoNarrativo", "A045SpecMissao", "A061OnePagerCompleto", "A079Prototipo", "A113PrdWriter"):
        ag = agentes[nome_autor]
        assert ag.model == settings.gemini_model
        assert ag.generate_content_config.thinking_config.thinking_budget == 8192

    # Juízes de loop crítico permanecem em gemini-3.8-flash, mas com thinking_budget_juiz=2048
    for nome_juiz in ("A007MicroGate", "A008JuizProfundidade", "A026GateEstrutural", "A043GateFinalProduto", "A057aBancaProdutoNarrativa", "A088QaEntregaveis"):
        ag = agentes[nome_juiz]
        assert ag.model == settings.gemini_model
        assert ag.generate_content_config.thinking_config.thinking_budget == 2048

    # Camada 1 e Camada 2 usam gemini-3.5-flash-lite e thinking_budget=2048
    for nome_lite in (
        "A025JuizContratoProdutoLlm",
        "A049JuizEvidenciaLlm",
        "A102JuizTelemetriaLlm",
        "A010FidelidadeNucleoInterprete",
        "A060FidelidadeProdutoInterprete",
        "A094FidelidadeDesignInterprete",
        "A126FidelidadeDevInterprete",
        "A029aAvaliacaoPedagogica",
        "A029bExperienciaEstudante",
        "A029cAdequacaoPedagogica",
        "A051JuizPerguntas",
        "A128Aprendizado",
    ):
        ag = agentes[nome_lite]
        assert ag.model == "gemini-3.5-flash-lite", f"{nome_lite} deveria usar gemini-3.5-flash-lite"
        assert ag.generate_content_config.thinking_config.thinking_budget == 2048

    # Precificação de gemini-3.5-flash-lite ($0.25/1M input, $1.50/1M output, $0.025/1M cache)
    mapa = custo.modelos_dos_agentes(settings)
    res = custo.custo_da_execucao(
        {
            "ClassificadorDeSentido": {"entrada": 100_000, "cache": 0, "saida": 10_000, "pensamento": 0, "chamadas": 10},
            "A029aAvaliacaoPedagogica": {"entrada": 100_000, "cache": 0, "saida": 10_000, "pensamento": 0, "chamadas": 1},
            "A004NucleoNarrativo": {"entrada": 100_000, "cache": 0, "saida": 10_000, "pensamento": 0, "chamadas": 1},
        },
        settings.gemini_model,
        mapa,
        etapas=["produto"],
    )
    assert res["tokens_por_agente"]["ClassificadorDeSentido"]["modelo"] == "gemini-3.5-flash-lite"
    assert res["tokens_por_agente"]["A029aAvaliacaoPedagogica"]["modelo"] == "gemini-3.5-flash-lite"
    assert res["tokens_por_agente"]["A004NucleoNarrativo"]["modelo"] == "gemini-3.8-flash"
    # Flash-Lite ($0.04) vs Flash 3.8 ($0.1125) na mesma quantidade de tokens
    assert res["tokens_por_agente"]["ClassificadorDeSentido"]["usd"] == pytest.approx(0.04, abs=1e-6)
    assert res["tokens_por_agente"]["A004NucleoNarrativo"]["usd"] == pytest.approx(0.1125, abs=1e-6)


def test_soft_delete_preserva_sessao_e_custos_e_filtra_por_papel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Missões excluídas não são apagadas fisicamente; somem para dev/produto/design,
    aparecem para admin com [EXCLUÍDA] e continuam contabilizadas no painel de custos.
    """
    import json
    from pipeline import session_store
    from tools import custo

    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("COTACAO_USD_BRL", "5.00")

    linha = custo.custo_da_execucao(
        {"A004NucleoNarrativo": {"entrada": 10000, "cache": 0, "saida": 2000, "pensamento": 0, "chamadas": 3}},
        "gemini-3.8-flash",
        {},
        etapas=["produto"],
    )
    custo_missao = custo.acumular(None, linha, ["produto"])

    s1 = tmp_path / "20261101-100000-session_ativa01"
    s2 = tmp_path / "20261101-110000-session_excl02"

    class _MockResult:
        def __init__(self, sid: str, titulo: str) -> None:
            self.session_id = sid
            self.user_id = "user_test"
            self.status = "success"
            self.duration_seconds = 12.0
            self.gates = {"gate_final_status": "aprovado"}
            self.attached_files = []
            self.step_thoughts = {}
            self.state = {
                "one_pager": f"# One-pager\n* **Nome que o estudante vê:** {titulo}\n* **Slug:** `exp-01-teste`",
                custo.KEY_CUSTO: custo_missao,
            }

    for pasta, sid, titulo in (
        (s1, "session_ativa01", "Missão Ativa"),
        (s2, "session_excl02", "Missão Excluída"),
    ):
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / "produto").mkdir(exist_ok=True)
        (pasta / "produto" / "00-one-pager.md").write_text("# Missão\n", encoding="utf-8")
        mock_res = _MockResult(sid, titulo)
        (pasta / "estado.json").write_text(json.dumps(mock_res.state, ensure_ascii=False), encoding="utf-8")
        session_store.save_session_record(
            run_dir=pasta,
            session_id=sid,
            user_id="user_test",
            prompt=titulo,
            result=mock_res,
            messages=[{"role": "user", "content": "Brief"}],
            fluxo={"etapa": "produto", "situacao": "aguardando_parecer", "atualizado_em": "2026-11-01T10:00:00"},
        )

    # Exclusão lógica (soft delete): não remove a pasta nem os artefatos
    ok = session_store.delete_saved_session(s2.name)
    assert ok is True
    assert s2.exists() and (s2 / "conversa.json").exists()
    assert (s2 / ".excluida").exists()

    # Regravar conversa.json (ex.: runner/correção) preserva excluida=True
    session_store.save_session_record(
        run_dir=s2,
        session_id="session_excl02",
        user_id="user_test",
        prompt="Missão Excluída",
        result=_MockResult("session_excl02", "Missão Excluída"),
        messages=[{"role": "user", "content": "Brief"}],
    )

    todas = session_store.list_saved_sessions()
    assert len(todas) == 2
    por_dir = {s["dir_name"]: s for s in todas}
    assert por_dir[s1.name]["excluida"] is False
    assert por_dir[s2.name]["excluida"] is True
    assert por_dir[s2.name]["excluida_em"] != ""

    # Filtro de visibilidade para perfis não-admin vs admin
    for papel in ("produto", "design", "dev"):
        visiveis = todas if papel == "admin" else [s for s in todas if not s.get("excluida")]
        assert [s["dir_name"] for s in visiveis] == [s1.name]

    visiveis_admin = todas
    assert len(visiveis_admin) == 2
    labels_admin = [
        f"{'[EXCLUÍDA] ' if s.get('excluida') else ''}{s['status_icon']} {s['title']}"
        for s in visiveis_admin
    ]
    assert any(lbl.startswith("[EXCLUÍDA] ") and "Missão Excluída" in lbl for lbl in labels_admin)

    # Consolidação de custos mantém tanto ativas quanto excluídas
    enriquecidas = session_store.carregar_custos_das_sessoes(todas)
    painel = custo.consolidar_missoes(enriquecidas)
    assert painel["num_missoes"] == 2
    assert painel["missoes_com_custo"] == 2
    missoes_painel = {m["dir_name"]: m for m in painel["missoes"]}
    assert missoes_painel[s2.name]["excluida"] is True
    assert missoes_painel[s2.name]["brl"] > 0


