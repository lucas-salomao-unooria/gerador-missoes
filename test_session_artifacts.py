"""Testes para a camada de persistência de artefatos, histórico de sessões e Figma MCP automático."""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from config import _detect_figma_mode, get_settings
from pipeline.artifacts import extract_figma_links, generate_artifact_manifest, save_run_artifacts
from pipeline.runner import PipelineExecutionResult
from pipeline.session_store import (
    create_session_zip,
    delete_saved_session,
    extrair_metadados_frontmatter,
    extrair_titulo_missao,
    formatar_status_label,
    list_saved_sessions,
    load_saved_session,
    save_session_record,
)


class TestFigmaModeAutoDetect(unittest.TestCase):
    def test_auto_detect_stdio_when_key_present(self):
        os.environ["FIGMA_MCP_MODE"] = "auto"
        os.environ["FIGMA_API_KEY"] = "figd_teste123"
        mode = _detect_figma_mode()
        self.assertEqual(mode, "stdio")

    def test_explicit_mode_honored(self):
        os.environ["FIGMA_MCP_MODE"] = "off"
        mode = _detect_figma_mode()
        self.assertEqual(mode, "off")

        os.environ["FIGMA_MCP_MODE"] = "stdio"
        mode = _detect_figma_mode()
        self.assertEqual(mode, "stdio")


class TestArtifactsAndSessionStore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_output = os.environ.get("OUTPUT_DIR")
        os.environ["OUTPUT_DIR"] = str(self.temp_dir)

    def tearDown(self):
        if self.original_output is not None:
            os.environ["OUTPUT_DIR"] = self.original_output
        else:
            os.environ.pop("OUTPUT_DIR", None)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_extract_figma_links(self):
        state = {
            "jornada_telas": "Board no FigJam: https://www.figma.com/board/mPw4Hhx9ptkgcHtySaSilO/Jornada-Teste?node-id=1-23",
            "wireframes_cobertura": "Telas no Figma: https://www.figma.com/design/i0HRQSBtQQ9ZXDYiJPRnGv/Wireframes-Teste",
            "prd_final": "Consulte o FigJam em https://www.figma.com/board/mPw4Hhx9ptkgcHtySaSilO/Jornada-Teste",
        }
        links = extract_figma_links(state)
        self.assertEqual(len(links), 2)
        urls = [l["url"] for l in links]
        self.assertTrue(any("mPw4Hhx9ptkgcHtySaSilO" in u for u in urls))
        self.assertTrue(any("i0HRQSBtQQ9ZXDYiJPRnGv" in u for u in urls))

    def test_save_run_artifacts_and_manifest(self):
        state = {
            "one_pager": "# One-pager — Missão Astronomia v1.0\n* **Nome que o estudante vê:** Caçadores de Cometas\n* **Slug:** `exp-01-cacadores-cometas`",
            "spec_missao": "# Spec — Missão Astronomia v1.0\n* **Slug:** `exp-01-cacadores-cometas`",
            "jornada_telas": "https://www.figma.com/board/abc12345/Jornada-Cometas",
            "prd_final": "# PRD Padrão Ouro — Caçadores de Cometas",
        }
        run_dir = save_run_artifacts(state, session_id="test_sess_01", prompt="Criar missão de cometas")
        self.assertIsNotNone(run_dir)
        self.assertTrue((run_dir / "PRD.md").exists())
        self.assertTrue((run_dir / "produto/00-one-pager.md").exists())
        self.assertTrue((run_dir / "produto/05-spec-missao.md").exists())
        self.assertTrue((run_dir / "figma/figma-links.json").exists())
        self.assertTrue((run_dir / "manifesto-artefatos.json").exists())

        manifest = generate_artifact_manifest(run_dir)
        self.assertGreater(len(manifest), 3)
        filenames = [m["filename"] for m in manifest]
        self.assertIn("PRD.md", filenames)
        self.assertIn("00-one-pager.md", filenames)

    def test_session_lifecycle(self):
        state = {
            "one_pager": "# One-pager — Missão Vulcão\n* **Nome que o estudante vê:** Detetives do Vulcão\n* **Slug:** `exp-02-vulcao`",
            "prd_final": "# PRD Final",
        }
        run_dir = save_run_artifacts(state, session_id="sess_vulcao", prompt="Missão sobre vulcões")
        self.assertIsNotNone(run_dir)

        # Mock result
        class MockResult:
            session_id = "sess_vulcao"
            user_id = "user_test"
            status = "success"
            duration_seconds = 42.5
            gates = {"gate_final_status": "aprovado"}
            attached_files = []
            step_thoughts = {}

        save_session_record(
            run_dir=run_dir,
            session_id="sess_vulcao",
            user_id="user_test",
            prompt="Missão sobre vulcões",
            result=MockResult(),
            messages=[
                {"role": "user", "content": "Missão sobre vulcões"},
                {"role": "assistant", "content": "PRD Final"},
            ],
        )

        # List saved sessions
        sessions = list_saved_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["title"], "Detetives do Vulcão")
        self.assertEqual(sessions[0]["status_icon"], "🟢")

        # Load saved session
        loaded = load_saved_session(sessions[0]["dir_name"])
        self.assertIsNotNone(loaded)
        msgs, res, meta = loaded
        self.assertEqual(len(msgs), 2)
        self.assertEqual(res.session_id, "sess_vulcao")
        self.assertEqual(meta["title"], "Detetives do Vulcão")
        self.assertFalse(res.bypassed)
        self.assertEqual(res.status_icon, "🟢")

        # Create zip
        zip_bytes = create_session_zip(run_dir)
        self.assertGreater(len(zip_bytes), 100)

        # Delete session
        ok = delete_saved_session(sessions[0]["dir_name"])
        self.assertTrue(ok)
        self.assertEqual(len(list_saved_sessions()), 0)

    def test_session_bypassed_shows_yellow_icon(self):
        """Quando um gate é bloqueado mas o pipeline avança (bypass) e gera PRD, status deve ser amarelo (🟡)."""
        state = {
            "one_pager": "# One-pager — Missão Bypass\n* **Nome que o estudante vê:** Detetives da Ilha\n* **Slug:** `exp-03-ilha`",
            "gate_estrutural_status": "aprovado",
            "gate_final_status": "bloqueado",
            "prd_final": "# PRD com pendências gerado em bypass",
        }
        run_dir = save_run_artifacts(state, session_id="sess_bypass", prompt="Missão com bypass")
        self.assertIsNotNone(run_dir)

        res_obj = PipelineExecutionResult(
            session_id="sess_bypass",
            user_id="user_test",
            prompt="Missão com bypass",
            final_output="PRD",
            status="bypassed",
            duration_seconds=50.0,
            state=state,
            step_outputs={},
            step_thoughts={},
            attached_files=[],
        )

        save_session_record(
            run_dir=run_dir,
            session_id="sess_bypass",
            user_id="user_test",
            prompt="Missão com bypass",
            result=res_obj,
            messages=[
                {"role": "user", "content": "Missão com bypass"},
                {"role": "assistant", "content": "🟡 **PRD gerado com ressalvas (gates bypassados).** Veja as abas abaixo."},
            ],
        )

        sessions = list_saved_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["status_icon"], "🟡")
        self.assertEqual(sessions[0]["status"], "bypassed")

        loaded = load_saved_session(sessions[0]["dir_name"])
        self.assertIsNotNone(loaded)
        msgs, res, meta = loaded
        self.assertEqual(res.status, "bypassed")
        self.assertTrue(res.bypassed)
        self.assertEqual(res.status_icon, "🟡")
        self.assertIn("🟡", msgs[1]["content"])

        delete_saved_session(sessions[0]["dir_name"])

    def test_session_blocked_shows_red_icon(self):
        """Quando o pipeline é bloqueado em modo estrito e não gera PRD, status deve ser vermelho (🔴)."""
        state = {
            "one_pager": "# One-pager — Missão Bloqueada\n* **Nome que o estudante vê:** Detetives da Floresta\n* **Slug:** `exp-04-floresta`",
            "gate_estrutural_status": "bloqueado",
            "pipeline_bloqueado": True,
        }
        run_dir = save_run_artifacts(state, session_id="sess_bloqueada", prompt="Missão bloqueada")
        self.assertIsNotNone(run_dir)

        res_obj = PipelineExecutionResult(
            session_id="sess_bloqueada",
            user_id="user_test",
            prompt="Missão bloqueada",
            final_output="Gate estrutural bloqueado.",
            status="blocked",
            duration_seconds=20.0,
            state=state,
            step_outputs={},
            step_thoughts={},
            attached_files=[],
        )

        save_session_record(
            run_dir=run_dir,
            session_id="sess_bloqueada",
            user_id="user_test",
            prompt="Missão bloqueada",
            result=res_obj,
            messages=[
                {"role": "user", "content": "Missão bloqueada"},
                {"role": "assistant", "content": "Gate estrutural bloqueado."},
            ],
        )

        sessions = list_saved_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["status_icon"], "🔴")
        self.assertIn(sessions[0]["status"], ("blocked", "bloqueado"))

        loaded = load_saved_session(sessions[0]["dir_name"])
        self.assertIsNotNone(loaded)
        msgs, res, meta = loaded
        self.assertTrue(res.bloqueado)
        self.assertEqual(res.status_icon, "🔴")

        delete_saved_session(sessions[0]["dir_name"])

    def test_status_icon_helper(self):
        from app import _status_icon
        self.assertEqual(_status_icon("aprovado"), "🟢")
        self.assertEqual(_status_icon("success"), "🟢")
        self.assertEqual(_status_icon("bypassed"), "🟡")
        self.assertEqual(_status_icon("bypass"), "🟡")
        self.assertEqual(_status_icon("ressalvas"), "🟡")
        self.assertEqual(_status_icon("bloqueado"), "🔴")
        self.assertEqual(_status_icon("blocked"), "🔴")
        self.assertEqual(_status_icon("desconhecido"), "⚪")

    def test_extrair_titulo_frontmatter_yaml(self):
        prd_text = (
            "---\n"
            "prd_id: PRD-exp-15-autoria-ia\n"
            "titulo: \"O Diário de Criação com IA: Quem é o Autor?\"\n"
            "versao: 0.1.0\n"
            "status: em-revisao\n"
            "slug_experiencia: exp-15-autoria-ia\n"
            "serie: [\"3EM\"]\n"
            "ambiente_simulado: chatgpt\n"
            "---\n\n"
            "# 0. Resumo executivo\n"
            "Conteúdo da missão..."
        )
        # Teste com prd_final no state
        title = extrair_titulo_missao({"prd_final": prd_text})
        self.assertEqual(title, "O Diário de Criação com IA: Quem é o Autor?")

        # Teste com fallback recebendo texto de frontmatter bruto
        title_from_fallback = extrair_titulo_missao({}, fallback=prd_text)
        self.assertEqual(title_from_fallback, "O Diário de Criação com IA: Quem é o Autor?")

    def test_extrair_metadados_frontmatter(self):
        prd_text = (
            "---\n"
            "prd_id: PRD-exp-15-autoria-ia\n"
            "titulo: \"O Diário de Criação com IA: Quem é o Autor?\"\n"
            "status: em-revisao\n"
            "---\n\n"
            "# 0. Resumo executivo\n"
            "Conteúdo"
        )
        meta, body = extrair_metadados_frontmatter(prd_text)
        self.assertEqual(meta.get("prd_id"), "PRD-exp-15-autoria-ia")
        self.assertEqual(meta.get("titulo"), "O Diário de Criação com IA: Quem é o Autor?")
        self.assertEqual(meta.get("status"), "em-revisao")
        self.assertTrue(body.startswith("# 0. Resumo executivo"))
        self.assertNotIn("prd_id:", body)

    def test_load_saved_session_prevents_duplication(self):
        state = {
            "prd_final": (
                "---\n"
                "prd_id: PRD-exp-15-autoria-ia\n"
                "titulo: \"O Diário de Criação com IA: Quem é o Autor?\"\n"
                "status: em-revisao\n"
                "---\n\n"
                "# 0. Resumo executivo"
            )
        }
        run_dir = save_run_artifacts(state, session_id="sess_dup_test", prompt="Missão com IA")

        class MockResult:
            session_id = "sess_dup_test"
            user_id = "user_test"
            status = "success"
            duration_seconds = 10.0
            gates = {}
            attached_files = []
            step_thoughts = {}

        # Simula salvar histórico com a mensagem de boas-vindas acidentalmente incluída
        save_session_record(
            run_dir=run_dir,
            session_id="sess_dup_test",
            user_id="user_test",
            prompt="Missão com IA",
            result=MockResult(),
            messages=[
                {"role": "assistant", "content": "👋 Olá! Sou o Gerador de Missões Unooria."},
                {"role": "user", "content": "Missão com IA"},
                {"role": "assistant", "content": "📘 PRD gerado."},
            ],
        )

        sessions = list_saved_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["title"], "O Diário de Criação com IA: Quem é o Autor?")

        # Ao carregar, a mensagem de boas-vindas deve ter sido removida e apenas a resposta final tem pipeline_result
        loaded = load_saved_session(sessions[0]["dir_name"])
        self.assertIsNotNone(loaded)
        msgs, res, meta = loaded

        # Deve conter apenas 2 mensagens: 1 do usuário e 1 do assistente
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["role"], "user")
        self.assertIsNone(msgs[0]["pipeline_result"])

        self.assertEqual(msgs[1]["role"], "assistant")
        self.assertIsNotNone(msgs[1]["pipeline_result"], "Somente a mensagem final do assistente deve ter pipeline_result")

        # Metadados limpos
        self.assertEqual(meta["title"], "O Diário de Criação com IA: Quem é o Autor?")
        self.assertEqual(meta["status_label"], "🟡 Em revisão")

        delete_saved_session(sessions[0]["dir_name"])

    def test_update_pipeline_step_status_revisor_turns_done_on_gate_approval(self):
        from app import update_pipeline_step_status
        from pipeline.runner import PipelineExecutionResult

        status = {
            "OnePagerAgent": "done",
            "GateEstruturalAgent": "done",
            "GateEstruturalCheck": "running",
            "RevisorOnePagerAgent": "pending",
            "AvaliacaoPedagogicaAgent": "pending",
        }
        gates = {}
        active_agent = "GateEstruturalCheck"

        # GateEstruturalCheck aprova o gate estrutural na rodada 1
        active_agent = update_pipeline_step_status(
            status,
            active_agent,
            {"type": "gate_status", "status": {"gate_estrutural_status": "aprovado"}},
            gates,
        )
        self.assertEqual(status["GateEstruturalCheck"], "done")
        self.assertEqual(status["RevisorOnePagerAgent"], "done", "Revisor deve ficar verde (done) ao aprovar o gate")

        # Início do próximo agente (AvaliacaoPedagogicaAgent)
        active_agent = update_pipeline_step_status(
            status,
            active_agent,
            {"type": "agent_started", "agent_name": "AvaliacaoPedagogicaAgent"},
            gates,
        )
        self.assertEqual(active_agent, "AvaliacaoPedagogicaAgent")
        self.assertEqual(status["RevisorOnePagerAgent"], "done")
        self.assertEqual(status["AvaliacaoPedagogicaAgent"], "running")

        # Conclusão do pipeline
        res = PipelineExecutionResult(
            session_id="test",
            user_id="user",
            prompt="p",
            final_output="out",
            state={"gate_estrutural_status": "aprovado"},
        )
        update_pipeline_step_status(
            status,
            active_agent,
            {"type": "pipeline_completed", "result": res},
            gates,
        )
        self.assertEqual(status["RevisorOnePagerAgent"], "done")
        self.assertEqual(status["AvaliacaoPedagogicaAgent"], "done")
        self.assertNotIn("pending", status.values(), "Nenhum agente ativo deve ficar como pending (ampulheta)")

    def test_update_pipeline_step_status_revisor_runs_when_gate_blocked(self):
        from app import update_pipeline_step_status

        status = {
            "OnePagerAgent": "done",
            "GateEstruturalAgent": "done",
            "GateEstruturalCheck": "running",
            "RevisorOnePagerAgent": "pending",
        }
        gates = {}
        active_agent = "GateEstruturalCheck"

        # Gate bloqueado na rodada 1: revisor ainda pendente até iniciar
        active_agent = update_pipeline_step_status(
            status,
            active_agent,
            {"type": "gate_status", "status": {"gate_estrutural_status": "bloqueado"}},
            gates,
        )
        self.assertEqual(status["RevisorOnePagerAgent"], "pending")

        # Revisor inicia a execução
        active_agent = update_pipeline_step_status(
            status,
            active_agent,
            {"type": "agent_started", "agent_name": "RevisorOnePagerAgent"},
            gates,
        )
        self.assertEqual(status["RevisorOnePagerAgent"], "running")

        # Próxima rodada do gate inicia
        active_agent = update_pipeline_step_status(
            status,
            active_agent,
            {"type": "agent_started", "agent_name": "GateEstruturalAgent"},
            gates,
        )
        self.assertEqual(status["RevisorOnePagerAgent"], "done")


if __name__ == "__main__":
    unittest.main()
