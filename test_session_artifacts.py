"""Testes da persistência de artefatos, do histórico de sessões e da detecção do MCP do Stitch."""

import io
import json
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from unittest import mock

from config import AppSettings, _detect_miro_mode, _detect_stitch_mode, get_settings
from pipeline.artifacts import generate_artifact_manifest, save_run_artifacts
from pipeline.runner import PipelineExecutionResult
from pipeline.session_store import (
    create_session_zip,
    delete_saved_session,
    extrair_metadados_frontmatter,
    extrair_titulo_missao,
    formatar_status_label,
    list_saved_sessions,
    load_saved_session,
    resolve_session_dir,
    save_session_record,
)


class TestStitchModeAutoDetect(unittest.TestCase):
    """O Figma saiu da esteira (sem cliente oficial); o Stitch é o MCP que restou."""

    def test_auto_detect_remote_when_key_present(self):
        os.environ["STITCH_MCP_MODE"] = "auto"
        os.environ["STITCH_API_KEY"] = "chave-de-teste"
        self.assertEqual(_detect_stitch_mode(), "remote")

    def test_explicit_mode_honored(self):
        os.environ["STITCH_MCP_MODE"] = "off"
        self.assertEqual(_detect_stitch_mode(), "off")
        os.environ["STITCH_MCP_MODE"] = "proxy"
        self.assertEqual(_detect_stitch_mode(), "proxy")

    def test_modo_auto_chega_resolvido_ao_settings(self):
        """O `auto` tem de virar `remote` no campo, não sobrar como string literal.

        Sem o par campo `_raw` + propriedade, o pydantic-settings populava o campo
        direto de STITCH_MCP_MODE e o `default_factory` nunca rodava: o modo saía
        "auto", que não é nem `remote` nem `proxy`, e o Stitch ficava desligado com a
        chave no lugar — silenciosamente, porque o rótulo da UI dizia só "desconhecido".
        """
        with mock.patch.dict(os.environ, {"STITCH_MCP_MODE": "auto", "STITCH_API_KEY": "chave-de-teste"}):
            self.assertEqual(AppSettings().stitch_mcp_mode, "remote")
            self.assertTrue(AppSettings().is_stitch_enabled)


class TestMiroModeAutoDetect(unittest.TestCase):
    """O Miro espelha jornada e fluxo; o Mermaid continua sendo a fonte."""

    def test_auto_vira_remote(self):
        """Não há credencial no ambiente para consultar: quem autoriza é o navegador."""
        with mock.patch.dict(os.environ, {"MIRO_MODE": "auto"}):
            self.assertEqual(_detect_miro_mode(), "remote")
            self.assertTrue(AppSettings().is_miro_enabled)

    def test_ausencia_de_variavel_tambem_liga(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MIRO_MODE", None)
            self.assertEqual(_detect_miro_mode(), "remote")

    def test_off_desliga(self):
        with mock.patch.dict(os.environ, {"MIRO_MODE": "off"}):
            self.assertEqual(_detect_miro_mode(), "off")
            s = AppSettings()
            self.assertFalse(s.is_miro_enabled)
            self.assertIn("Desligado", s.miro_status_label)


class TestMiroTokenStore(unittest.TestCase):
    """A conexão do Miro em disco, sem tocar a rede.

    O arquivo guarda um refresh token de 60 dias: quem o tiver entra nos boards do time
    sem passar pelo navegador. Por isso permissão e atomicidade são asserção, não zelo.
    """

    def setUp(self):
        from tools.miro_oauth import MiroTokenStore

        self.temp_dir = Path(tempfile.mkdtemp())
        self.store = MiroTokenStore(self.temp_dir / ".miro_mcp_tokens.json")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sem_arquivo_nao_ha_conexao(self):
        self.assertEqual(self.store.load(), {})
        self.assertIsNone(self.store.client())
        self.assertFalse(self.store.status()["conectado"])
        with self.assertRaises(RuntimeError):
            self.store.access_token()

    def test_round_trip_de_client_e_tokens(self):
        self.store.gravar_client({"client_id": "cli-sintetico", "client_secret": "seg", "redirect_uri": "http://localhost:8501"})
        self.store.gravar_tokens({"access_token": "access-sintetico", "refresh_token": "refresh-sintetico", "expires_in": 3600})

        self.assertEqual(self.store.client()["client_id"], "cli-sintetico")
        self.assertEqual(self.store.access_token(), "access-sintetico")

        estado = self.store.status()
        self.assertTrue(estado["conectado"])
        self.assertTrue(estado["renovavel"])
        self.assertGreater(estado["expira_em_min"], 55)

    def test_arquivo_protegido_e_sem_temporario_residual(self):
        self.store.gravar_tokens({"access_token": "a", "expires_in": 3600})
        self.assertEqual(oct(self.store.path.stat().st_mode)[-3:], "600")
        self.assertEqual(list(self.temp_dir.glob("*.tmp")), [])

    def test_arquivo_corrompido_vale_como_sem_conexao(self):
        """Um JSON quebrado não pode derrubar a sidebar inteira."""
        self.store.path.write_text("{ isto não é json", encoding="utf-8")
        self.assertEqual(self.store.load(), {})
        self.assertFalse(self.store.status()["conectado"])

    def test_token_vencido_renova_e_guarda_o_refresh_rotacionado(self):
        """O Miro rotaciona o refresh a cada renovação: perder o novo é perder a conexão."""
        from tools import miro_oauth

        self.store.gravar_client({"client_id": "cli", "client_secret": "seg", "redirect_uri": "u"})
        self.store.gravar_tokens({"access_token": "velho", "refresh_token": "refresh-1", "expires_in": 3600})
        # Força o vencimento sem esperar uma hora.
        dados = self.store.load()
        dados["expires_at"] = 0
        self.store._save(dados)

        resposta = mock.Mock()
        resposta.json.return_value = {"access_token": "novo", "refresh_token": "refresh-2", "expires_in": 3600}
        resposta.raise_for_status.return_value = None

        with mock.patch.object(miro_oauth, "descobrir_endpoints", return_value={"token_endpoint": "https://mcp.miro.com/token"}), \
             mock.patch.object(miro_oauth.httpx, "post", return_value=resposta) as post:
            self.assertEqual(self.store.access_token(), "novo")

        self.assertEqual(post.call_args.kwargs["data"]["grant_type"], "refresh_token")
        self.assertEqual(self.store.load()["tokens"]["refresh_token"], "refresh-2")

    def test_refresh_omitido_preserva_o_anterior(self):
        """Quando o servidor não manda refresh novo, o antigo continua valendo."""
        self.store.gravar_tokens({"access_token": "a1", "refresh_token": "refresh-1", "expires_in": 3600})
        self.store.gravar_tokens({"access_token": "a2", "expires_in": 3600})
        self.assertEqual(self.store.load()["tokens"]["refresh_token"], "refresh-1")

    def test_pendente_guarda_o_pkce_entre_duas_sessoes(self):
        """Ir ao Miro e voltar abre sessão nova no Streamlit: o verifier tem de estar em disco."""
        self.store.gravar_pendente("state-abc", "verifier-xyz")
        self.assertEqual(self.store.ler_pendente()["code_verifier"], "verifier-xyz")
        self.store.limpar_pendente()
        self.assertIsNone(self.store.ler_pendente())

    def test_pendente_expira(self):
        self.store.gravar_pendente("state-abc", "verifier-xyz")
        dados = self.store.load()
        dados["pendente"]["criado_em"] = 0
        self.store._save(dados)
        self.assertIsNone(self.store.ler_pendente())

    def test_state_divergente_descarta_a_autorizacao(self):
        """Resposta que não corresponde ao pedido que fizemos não vira conexão."""
        from tools import miro_oauth

        self.store.gravar_pendente("state-certo", "verifier")
        with mock.patch.object(miro_oauth, "token_store", return_value=self.store), \
             mock.patch.object(miro_oauth, "trocar_codigo") as trocar:
            with self.assertRaises(RuntimeError):
                miro_oauth.concluir_conexao("codigo", "state-forjado")
        trocar.assert_not_called()
        self.assertIsNone(self.store.ler_pendente())

    def test_apagar_derruba_a_conexao(self):
        self.store.gravar_tokens({"access_token": "a", "expires_in": 3600})
        self.store.apagar()
        self.assertFalse(self.store.path.exists())
        self.assertFalse(self.store.status()["conectado"])


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

    def test_save_run_artifacts_and_manifest(self):
        state = {
            "one_pager": "# One-pager — Missão Astronomia v1.0\n* **Nome que o estudante vê:** Caçadores de Cometas\n* **Slug:** `exp03ef1b`",
            "spec_missao": "# Spec — Missão Astronomia v1.0\n* **Slug:** `exp03ef1b`",
            "prd_final": "# PRD Padrão Ouro — Caçadores de Cometas",
        }
        run_dir = save_run_artifacts(state, session_id="test_sess_01", prompt="Criar missão de cometas")
        self.assertIsNotNone(run_dir)
        self.assertTrue((run_dir / "PRD.md").exists())
        self.assertTrue((run_dir / "produto/00-one-pager.md").exists())
        self.assertTrue((run_dir / "produto/05-spec-missao.md").exists())
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
            "prd_id: PRD-exp08ef2b\n"
            "titulo: \"O Diário de Criação com IA: Quem é o Autor?\"\n"
            "versao: 0.1.0\n"
            "status: em-revisao\n"
            "slug_experiencia: exp08ef2b\n"
            "serie: [\"3EM\"]\n"
            "ambiente_simulado: chatgpt\n"
            "---\n\n"
            "# 0. Resumo executivo\n"
            "Conteúdo da missão..."
        )
        # O título vai para o histórico prefixado por ano e bimestre, tirados do identificador
        # da missão — sem isso, duas missões do mesmo ano ficam indistinguíveis na lista.
        title = extrair_titulo_missao({"prd_final": prd_text})
        self.assertEqual(title, "8EF-2B · O Diário de Criação com IA: Quem é o Autor?")

        # Teste com fallback recebendo texto de frontmatter bruto
        title_from_fallback = extrair_titulo_missao({}, fallback=prd_text)
        self.assertEqual(title_from_fallback, "O Diário de Criação com IA: Quem é o Autor?")

        # Sem identificador dedutível, o título sai como antes — nada de prefixo inventado
        sem_id = extrair_titulo_missao({"prd_final": "---\ntitulo: Missão Avulsa\n---\n"})
        self.assertEqual(sem_id, "Missão Avulsa")

    def test_titulo_nao_arrasta_o_resumo_da_spec(self):
        """Regressão de 2026-09-20: o cabeçalho da missão virava um parágrafo inteiro.

        O bloco 0 da spec é prosa corrida (`references/formato-spec.md:17` pede
        "Nome que o estudante vê · software clonado · por que este viewport"), e o regex de
        `Nome que o estudante vê:` capturava a linha até o fim.
        """
        spec = (
            "# Spec — exp06ef1b\n\n## 0. Identificação de plataforma\n"
            "Nome que o estudante vê: O algoritmo que me formou. Software clonado: Instagram "
            "(`instanooria`). Viewport: `375x812` (emulação mobile estrita em container "
            "responsivo com proporção nativa de smartphone).\n"
            "- `id: exp06ef1b`\n- `unidade: 1`\n"
        )
        self.assertEqual(
            extrair_titulo_missao({"spec_missao": spec}),
            "6EF-1B · O algoritmo que me formou",
        )

        # O núcleo narrativo traz o nome limpo e é lido antes da spec.
        nucleo = "* **Nome que o estudante vê:** O algoritmo que me formou\n"
        self.assertEqual(
            extrair_titulo_missao({"nucleo_narrativo": nucleo, "spec_missao": spec}),
            "6EF-1B · O algoritmo que me formou",
        )

        # Título já curto atravessa intacto; versão e viewport não são fim de frase.
        self.assertEqual(
            extrair_titulo_missao({"prd_final": "---\ntitulo: O Detalhe que Muda Tudo\n---\n"}),
            "O Detalhe que Muda Tudo",
        )

        # Sem ponto nem separador, o corte é por tamanho, em fronteira de palavra.
        longo = "---\ntitulo: " + "palavra " * 30 + "\n---\n"
        curto = extrair_titulo_missao({"prd_final": longo})
        self.assertLessEqual(len(curto), 71)
        self.assertTrue(curto.endswith("…"))
        self.assertNotIn("  ", curto)

    def test_extrair_metadados_frontmatter(self):
        prd_text = (
            "---\n"
            "prd_id: PRD-exp08ef2b\n"
            "titulo: \"O Diário de Criação com IA: Quem é o Autor?\"\n"
            "status: em-revisao\n"
            "---\n\n"
            "# 0. Resumo executivo\n"
            "Conteúdo"
        )
        meta, body = extrair_metadados_frontmatter(prd_text)
        self.assertEqual(meta.get("prd_id"), "PRD-exp08ef2b")
        self.assertEqual(meta.get("titulo"), "O Diário de Criação com IA: Quem é o Autor?")
        self.assertEqual(meta.get("status"), "em-revisao")
        self.assertTrue(body.startswith("# 0. Resumo executivo"))
        self.assertNotIn("prd_id:", body)

    def test_load_saved_session_prevents_duplication(self):
        state = {
            "prd_final": (
                "---\n"
                "prd_id: PRD-exp08ef2b\n"
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
        # o histórico mostra ano e bimestre na frente, para a lista se organizar sozinha
        self.assertEqual(sessions[0]["title"], "8EF-2B · O Diário de Criação com IA: Quem é o Autor?")

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

        # Metadados limpos e status refletindo aprovação dos gates
        self.assertEqual(meta["title"], "8EF-2B · O Diário de Criação com IA: Quem é o Autor?")
        self.assertEqual(meta["status_label"], "🟢 Aprovado")

        delete_saved_session(sessions[0]["dir_name"])

    def test_update_pipeline_step_status_revisor_turns_done_on_gate_approval(self):
        from app import update_pipeline_step_status
        from pipeline.runner import PipelineExecutionResult

        status = {
            "OnePagerAgent": "done",
            "A05GateEstrutural": "done",
            "A06GateEstruturalCheck": "running",
            "A07RevisorOnePager": "pending",
            "A08AvaliacaoPedagogica": "pending",
        }
        gates = {}
        active_agent = "A06GateEstruturalCheck"

        # A06GateEstruturalCheck aprova o gate estrutural na rodada 1
        active_agent = update_pipeline_step_status(
            status,
            active_agent,
            {"type": "gate_status", "status": {"gate_estrutural_status": "aprovado"}},
            gates,
        )
        self.assertEqual(status["A06GateEstruturalCheck"], "done")
        self.assertEqual(status["A07RevisorOnePager"], "done", "Revisor deve ficar verde (done) ao aprovar o gate")

        # Início do próximo agente (A08AvaliacaoPedagogica)
        active_agent = update_pipeline_step_status(
            status,
            active_agent,
            {"type": "agent_started", "agent_name": "A08AvaliacaoPedagogica"},
            gates,
        )
        self.assertEqual(active_agent, "A08AvaliacaoPedagogica")
        self.assertEqual(status["A07RevisorOnePager"], "done")
        self.assertEqual(status["A08AvaliacaoPedagogica"], "running")

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
        self.assertEqual(status["A07RevisorOnePager"], "done")
        self.assertEqual(status["A08AvaliacaoPedagogica"], "done")
        self.assertNotIn("pending", status.values(), "Nenhum agente ativo deve ficar como pending (ampulheta)")

    def test_update_pipeline_step_status_revisor_runs_when_gate_blocked(self):
        from app import update_pipeline_step_status

        status = {
            "OnePagerAgent": "done",
            "A05GateEstrutural": "done",
            "A06GateEstruturalCheck": "running",
            "A07RevisorOnePager": "pending",
        }
        gates = {}
        active_agent = "A06GateEstruturalCheck"

        # Gate bloqueado na rodada 1: revisor ainda pendente até iniciar
        active_agent = update_pipeline_step_status(
            status,
            active_agent,
            {"type": "gate_status", "status": {"gate_estrutural_status": "bloqueado"}},
            gates,
        )
        self.assertEqual(status["A07RevisorOnePager"], "pending")

        # Revisor inicia a execução
        active_agent = update_pipeline_step_status(
            status,
            active_agent,
            {"type": "agent_started", "agent_name": "A07RevisorOnePager"},
            gates,
        )
        self.assertEqual(status["A07RevisorOnePager"], "running")

        # Próxima rodada do gate inicia
        active_agent = update_pipeline_step_status(
            status,
            active_agent,
            {"type": "agent_started", "agent_name": "A05GateEstrutural"},
            gates,
        )
        self.assertEqual(status["A07RevisorOnePager"], "done")



class TestSessionZip(unittest.TestCase):
    """Regressões do pacote .ZIP de artefatos.

    O download em massa passou a falhar com "arquivo não encontrado" mesmo com os
    artefatos íntegros no bucket, porque os bytes eram materializados a cada render e
    ficavam sujeitos à coleta de mídia do Streamlit. A geração precisa ser estável,
    tolerante a arquivos ilegíveis e capaz de reencontrar a pasta quando o caminho
    absoluto registrado na execução pertence a outro ambiente.
    """

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_output = os.environ.get("OUTPUT_DIR")
        os.environ["OUTPUT_DIR"] = str(self.temp_dir)

        self.run_dir = self.temp_dir / "20260914-120000-exp03ef1b"
        (self.run_dir / "produto").mkdir(parents=True)
        (self.run_dir / "PRD.md").write_text("# PRD\n", encoding="utf-8")
        (self.run_dir / "produto" / "00-one-pager.md").write_text("# One-pager\n", encoding="utf-8")
        (self.run_dir / ".oculto.md").write_text("ignorar\n", encoding="utf-8")

    def tearDown(self):
        if self.original_output is not None:
            os.environ["OUTPUT_DIR"] = self.original_output
        else:
            os.environ.pop("OUTPUT_DIR", None)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _names(self, blob: bytes):
        return sorted(zipfile.ZipFile(io.BytesIO(blob)).namelist())

    def test_zip_contains_visible_files_only(self):
        names = self._names(create_session_zip(self.run_dir))
        self.assertEqual(names, ["PRD.md", "produto/00-one-pager.md"])

    def test_zip_is_byte_identical_across_calls(self):
        """Bytes estáveis mantêm o mesmo hash de mídia no Streamlit entre reruns."""
        self.assertEqual(create_session_zip(self.run_dir), create_session_zip(self.run_dir))

    def test_zip_resolves_stale_absolute_path(self):
        """Caminho de outro ambiente (ex.: /app/output) resolve pelo OUTPUT_DIR atual."""
        stale = Path("/app/output") / self.run_dir.name
        self.assertEqual(resolve_session_dir(stale), self.run_dir)
        self.assertEqual(self._names(create_session_zip(stale)), ["PRD.md", "produto/00-one-pager.md"])

    def test_missing_directory_raises_clear_error(self):
        with self.assertRaises(FileNotFoundError) as ctx:
            create_session_zip(self.temp_dir / "nao-existe")
        self.assertIn("não encontrado", str(ctx.exception))

    def test_empty_directory_raises(self):
        vazia = self.temp_dir / "20260914-130000-vazia"
        vazia.mkdir()
        with self.assertRaises(FileNotFoundError):
            create_session_zip(vazia)

    def test_unreadable_file_is_skipped_not_fatal(self):
        """Um arquivo ilegível não pode derrubar o pacote inteiro."""
        protegido = self.run_dir / "produto" / "01-gate-estrutural.md"
        protegido.write_text("# Gate\n", encoding="utf-8")
        protegido.chmod(0o000)
        try:
            if os.access(protegido, os.R_OK):
                self.skipTest("execução com privilégios que ignoram permissões de arquivo")

            names = self._names(create_session_zip(self.run_dir))
        finally:
            protegido.chmod(0o644)

        self.assertIn("PRD.md", names)
        self.assertNotIn("produto/01-gate-estrutural.md", names)
        self.assertIn("ARQUIVOS-NAO-INCLUIDOS.txt", names)


if __name__ == "__main__":
    unittest.main()
