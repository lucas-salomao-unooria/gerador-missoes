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

    def test_nome_do_zip_e_o_slug_da_missao(self):
        from pipeline.session_store import nome_do_zip_de_artefatos

        spec = "---\nslug_experiencia: exp09ef1b\n---\n# O Visor Misterioso"
        self.assertEqual(nome_do_zip_de_artefatos({"spec_missao": spec}, "session_4e6cf385"), "artefatos_exp09ef1b.zip")
        self.assertEqual(nome_do_zip_de_artefatos({"one_pager": "Missão EXP01EF1B"}, "s"), "artefatos_exp01ef1b.zip")
        self.assertEqual(nome_do_zip_de_artefatos({"prd_final": "id: exp06ef2b"}, "s"), "artefatos_exp06ef2b.zip")
        # produto ainda gerando: sem documento com slug, fica o id da sessão
        self.assertEqual(nome_do_zip_de_artefatos({}, "session_4e6cf385abcdef"), "artefatos_session_4e6c.zip")

    def test_downloads_avulsos_usam_o_mesmo_identificador(self):
        from pipeline.session_store import identificador_da_missao

        self.assertEqual(identificador_da_missao({"spec_missao": "slug: exp09ef1b"}, "session_4e6cf385"), "exp09ef1b")
        self.assertEqual(identificador_da_missao({"spec_missao": "", "prd_final": "exp02ef3b"}, "s"), "exp02ef3b")
        self.assertEqual(identificador_da_missao({}, ""), "session")
        app = (Path(__file__).parent / "app.py").read_text(encoding="utf-8")
        self.assertNotIn("sid[:", app, "download nomeado pelo id da sessão em vez do slug")

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


class _Upload:
    """Imita o UploadedFile do Streamlit: só `name` e `getvalue()`."""

    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


class TestDocParser(unittest.TestCase):
    """Upload: 60 arquivos, 25 MB no total, `.md` e `.txt` aceitos (2026-09-21)."""

    def test_md_e_txt_entram_como_texto(self):
        from tools.doc_parser import process_document

        md = process_document("notas.md", "# Título\n\nCorpo **forte**.".encode("utf-8"))
        self.assertEqual((md.file_type, md.is_native_pdf, md.pdf_bytes), ("md", False, None))
        self.assertEqual(md.markdown_text, "# Título\n\nCorpo **forte**.")
        txt = process_document("briefing.TXT", b"linha 1\nlinha 2\n")
        self.assertEqual(txt.file_type, "txt")
        self.assertEqual(txt.markdown_text, "linha 1\nlinha 2")

    def test_txt_em_latin1_nao_quebra(self):
        from tools.doc_parser import process_document

        doc = process_document("acentos.txt", "Ação e coração".encode("latin-1"))
        self.assertEqual(doc.markdown_text, "Ação e coração")

    def test_extensao_desconhecida_e_recusada(self):
        from tools.doc_parser import process_document

        with self.assertRaises(ValueError):
            process_document("planilha.xlsx", b"x")

    def test_limites_de_quantidade_e_tamanho(self):
        from tools.doc_parser import MAX_FILES, MAX_TOTAL_BYTES, validate_and_process_batch

        self.assertEqual(MAX_FILES, 60)
        self.assertEqual(MAX_TOTAL_BYTES, 25 * 1024 * 1024)
        sessenta = [_Upload(f"a{i}.txt", b"ok") for i in range(60)]
        batch, err = validate_and_process_batch(sessenta)
        self.assertIsNone(err, err)
        self.assertEqual(batch.files_count, 60)
        _, err = validate_and_process_batch(sessenta + [_Upload("a61.txt", b"ok")])
        self.assertIn("61 arquivos", err or "")
        _, err = validate_and_process_batch([_Upload("grande.txt", b"x" * (MAX_TOTAL_BYTES + 1))])
        self.assertIn("Tamanho total excedido", err or "")

    def test_pdf_ilegivel_mantem_bytes_sem_texto(self):
        from tools.doc_parser import process_document

        doc = process_document("digitalizado.pdf", b"isto nao e um pdf")
        self.assertTrue(doc.is_native_pdf)
        self.assertEqual(doc.pdf_bytes, b"isto nao e um pdf")
        self.assertIsNone(doc.markdown_text)

    def test_mensagem_do_usuario_inclui_texto_e_nao_binario(self):
        from pipeline.runner import build_user_message
        from tools.doc_parser import DocumentBatch, process_document

        batch = DocumentBatch(documents=[process_document("guia.md", b"# Guia\nconteudo do md")])
        msg = build_user_message("briefing", batch)
        self.assertEqual(len(msg.parts), 1)
        self.assertIn("Documento de apoio (MD): guia.md", msg.parts[0].text)
        self.assertIn("conteudo do md", msg.parts[0].text)
        pdf = DocumentBatch(documents=[process_document("um.pdf", b"nao e pdf")])
        msg_pdf = build_user_message("briefing", pdf)
        self.assertEqual(len(msg_pdf.parts), 2)
        self.assertEqual(msg_pdf.parts[1].inline_data.mime_type, "application/pdf")


class TestReexecucao(unittest.TestCase):
    """Fundação do modo correção: `pipeline/reexecucao.py` (2026-09-21)."""

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

    @staticmethod
    def _estado():
        return {
            "briefing": "b", "nucleo_narrativo": "n", "one_pager": "o", "one_pager_gate0": "o0",
            "gate_final_report": "gf", "spec_missao": "spec consolidada", "spec_missao_gate0": "spec gate0",
            "spec_rodada": 2, "bncc_report": "b", "one_pager_resumido": "r",
            "jornada_telas": "j", "miro_board": {"url_board": "u"}, "design_status": "aprovado",
            "handoff_dev": "h", "prd_final": "p", "dev_status": "aprovado", "prd_rodada": 2,
            "diagnostico_execucao": "d", "aprendizado_registro": "a",
            "reexecucoes": 8, "tickets_retrabalho": "t", "agentes_degradados": ["X"],
            "degradacoes": [{"gate": "Gate estrutural", "motivo": "Gate estrutural reprovado"},
                            {"gate": "Banca de dev", "motivo": "Banca de dev reprovado"}],
            "heranca_degradada": "velho", "pipeline_bloqueado": True, "pipeline_bloqueio_motivo": "Banca",
            "temp:x": 1,
        }

    def test_preparar_estado_por_etapa(self):
        from pipeline.reexecucao import preparar_estado

        limpo, removidas = preparar_estado(self._estado(), "spec", "PEDIDO")
        for chave in ("spec_missao", "spec_missao_gate0", "spec_rodada", "bncc_report", "one_pager_resumido",
                      "jornada_telas", "handoff_dev", "prd_final", "diagnostico_execucao", "aprendizado_registro",
                      "reexecucoes", "tickets_retrabalho", "agentes_degradados", "temp:x"):
            self.assertNotIn(chave, limpo, chave)
        for chave in ("briefing", "nucleo_narrativo", "one_pager", "one_pager_gate0", "gate_final_report", "miro_board"):
            self.assertIn(chave, limpo, chave)
        self.assertEqual(limpo["pedido_correcao"], "PEDIDO")
        self.assertIn("spec_missao", removidas)

        design, _ = preparar_estado(self._estado(), "design")
        self.assertEqual(design["spec_missao"], "spec gate0", "design refeito parte da spec do Gate 0")
        self.assertNotIn("jornada_telas", design)
        self.assertNotIn("pedido_correcao", design)

        dev, _ = preparar_estado(self._estado(), "dev")
        self.assertEqual(dev["spec_missao"], "spec consolidada", "dev lê a spec consolidada pelo D0")
        self.assertIn("jornada_telas", dev)
        self.assertNotIn("handoff_dev", dev)

        # `produto` virou etapa de correção em 23/09/2026 (refaz o one-pager e passa pelos gates de
        # produto): aceita, e apaga também a spec, que deriva dele. Inválida é etapa que não existe.
        produto, removidas_produto = preparar_estado(self._estado(), "produto")
        self.assertNotIn("spec_missao", produto)
        self.assertIn("spec_missao", removidas_produto)
        with self.assertRaises(ValueError):
            preparar_estado(self._estado(), "marketing")

    def test_reexecucao_guarda_a_versao_anterior_de_cada_autor(self):
        """Refazer produto para acrescentar uma pergunta de evidência devolvia outra missão: o autor
        recebia "o que não foi pedido continua como estava" sem ver como estava (06/10/2026)."""
        from pipeline.reexecucao import PREFIXO_ANTERIOR, preparar_estado

        produto, _ = preparar_estado(self._estado(), "produto", "PEDIDO")
        self.assertNotIn("nucleo_narrativo", produto)
        base = produto[PREFIXO_ANTERIOR + "nucleo_narrativo"]
        self.assertIn('<versao_anterior chave="nucleo_narrativo">\nn\n</versao_anterior>', base)
        self.assertIn("Parta dela", base)
        self.assertIn("spec gate0", produto[PREFIXO_ANTERIOR + "spec_missao"], "a spec do autor é a do Gate 0, não a do D0")
        # produto refeito apaga design e dev, que só rodam no próximo *iniciar*: a base deles fica guardada
        self.assertIn("j", produto[PREFIXO_ANTERIOR + "jornada_telas"])
        self.assertNotIn(PREFIXO_ANTERIOR + "gate_final_report", produto, "gate não recebe veredito velho")

        design, _ = preparar_estado(produto, "design")
        self.assertIn(PREFIXO_ANTERIOR + "jornada_telas", design, "a base sobrevive até a etapa dela rodar")
        self.assertNotIn(PREFIXO_ANTERIOR + "nucleo_narrativo", design, "produto não vai ser reescrito")

        dev, _ = preparar_estado(self._estado(), "dev")
        self.assertIn("h", dev[PREFIXO_ANTERIOR + "handoff_dev"])
        self.assertNotIn(PREFIXO_ANTERIOR + "jornada_telas", dev)
        self.assertNotIn(PREFIXO_ANTERIOR + "nucleo_narrativo", dev)

    def test_todo_documento_autoral_chega_ao_prompt_do_autor(self):
        from pipeline.orchestrator import create_mission_orchestrator, iter_agent_tree
        from pipeline.reexecucao import CHAVES_AUTORAIS, PREFIXO_ANTERIOR

        lidas = set()
        for _, agente in iter_agent_tree(create_mission_orchestrator(stages=["produto", "design", "dev"])):
            instrucao = getattr(agente, "instruction", "")
            if isinstance(instrucao, str):
                lidas |= {c for c in CHAVES_AUTORAIS if "{" + PREFIXO_ANTERIOR + c + "?}" in instrucao}
        self.assertEqual(sorted(CHAVES_AUTORAIS - lidas), [], "base guardada que nenhum autor lê")

    def test_heranca_preserva_so_gates_nao_refeitos(self):
        from pipeline.reexecucao import preparar_estado, recalcular_heranca

        dev, _ = preparar_estado(self._estado(), "dev")
        self.assertEqual([d["gate"] for d in dev["degradacoes"]], ["Gate estrutural"])
        self.assertTrue(dev["pipeline_bloqueado"])
        self.assertIn("Gate estrutural", dev["heranca_degradada"])
        self.assertNotIn("Banca", dev["heranca_degradada"])
        self.assertEqual(dev["pipeline_bloqueio_motivo"], "Gate estrutural reprovado")

        so_dev = recalcular_heranca({"degradacoes": [{"gate": "Banca de dev", "motivo": "x"},
                                                     {"gate": "Rótulo que não existe", "motivo": "y"}]}, "spec")
        self.assertEqual(so_dev["degradacoes"], [])
        self.assertFalse(so_dev["pipeline_bloqueado"])
        self.assertEqual((so_dev["pipeline_bloqueio_motivo"], so_dev["heranca_degradada"]), ("", ""))

        transversal, _ = preparar_estado(self._estado(), "transversal")
        self.assertEqual(len(transversal["degradacoes"]), 2, "transversal diagnostica a execução como está")

    def test_arquivos_das_chaves_inclui_exportacoes_com_marca(self):
        from pipeline.reexecucao import arquivos_das_chaves

        arquivos = arquivos_das_chaves({"one_pager_resumido", "prd_final"})
        self.assertIn("produto/00d-one-pager-resumido.md", arquivos)
        self.assertIn("produto/00d-one-pager-resumido.docx", arquivos)
        self.assertIn("produto/00d-one-pager-resumido.html", arquivos)
        self.assertIn("PRD.md", arquivos)

    def test_backup_fica_oculto_e_restaura(self):
        from pipeline.reexecucao import PASTA_CORRECOES, fazer_backup, restaurar_backup
        from pipeline.session_store import list_session_files

        run_dir = self.temp_dir / "20260101-000000-exp05ef2b"
        (run_dir / "dev").mkdir(parents=True)
        (run_dir / "estado.json").write_text("{}", encoding="utf-8")
        (run_dir / "PRD.md").write_text("prd v1", encoding="utf-8")
        (run_dir / "dev" / "01-handoff-dev.md").write_text("handoff v1", encoding="utf-8")
        (run_dir / "produto").mkdir()
        (run_dir / "produto" / "05-spec-missao.md").write_text("spec", encoding="utf-8")

        backup = fazer_backup(run_dir, "dev", ["prd_final", "handoff_dev"])
        self.assertTrue(backup.relative_to(run_dir).as_posix().startswith(PASTA_CORRECOES + "/"))
        self.assertFalse((run_dir / "PRD.md").exists(), "artefato da chave removida é movido, não copiado")
        self.assertTrue((backup / "PRD.md").exists() and (backup / "dev" / "01-handoff-dev.md").exists())
        self.assertTrue((backup / "estado.json").exists())
        self.assertTrue((run_dir / "produto" / "05-spec-missao.md").exists(), "etapa preservada fica no lugar")

        visiveis = [p.relative_to(run_dir).as_posix() for p in list_session_files(run_dir)]
        self.assertEqual(visiveis, ["estado.json", "produto/05-spec-missao.md"])
        self.assertFalse(any(f["path"].startswith(".") for f in generate_artifact_manifest(run_dir)))
        with zipfile.ZipFile(io.BytesIO(create_session_zip(run_dir))) as zf:
            self.assertFalse(any(PASTA_CORRECOES in n for n in zf.namelist()), zf.namelist())

        # nome antigo do script também fica fora do manifesto e da listagem
        (run_dir / "_reexecucoes" / "x").mkdir(parents=True)
        (run_dir / "_reexecucoes" / "x" / "PRD.md").write_text("antigo", encoding="utf-8")
        self.assertFalse(any("_reexecucoes" in f["path"] for f in generate_artifact_manifest(run_dir)))
        self.assertFalse(any("_reexecucoes" in p.as_posix() for p in list_session_files(run_dir)))

        (run_dir / "PRD.md").write_text("prd v2", encoding="utf-8")
        restaurados = restaurar_backup(run_dir, backup)
        self.assertIn("PRD.md", restaurados)
        self.assertEqual((run_dir / "PRD.md").read_text(encoding="utf-8"), "prd v1")
        self.assertEqual((run_dir / "dev" / "01-handoff-dev.md").read_text(encoding="utf-8"), "handoff v1")

    def test_mesclar_conversa_preserva_data_e_acumula_historico(self):
        from pipeline.reexecucao import RegistroCorrecao, historico_de, mensagem_de_correcao, mesclar_conversa

        run_dir = self.temp_dir / "20260101-000000-exp05ef2b"
        run_dir.mkdir()
        (run_dir / "estado.json").write_text(json.dumps({"prd_final": "# PRD", "spec_missao": "# Spec — Teste v1"}), encoding="utf-8")
        result = PipelineExecutionResult(session_id="session_1", user_id="user_1", prompt="briefing original",
                                         final_output="ok", state={"prd_final": "# PRD"}, status="success")
        save_session_record(run_dir=run_dir, session_id="session_1", user_id="user_1", prompt="briefing original",
                            result=result, messages=[{"role": "user", "content": "briefing original"},
                                                     {"role": "assistant", "content": "📘 PRD gerado."}])
        anterior = json.loads((run_dir / "conversa.json").read_text(encoding="utf-8"))
        anterior["created_at"] = "01/01/2026 10:00:00"
        anterior["reexecucoes"] = [{"etapa": "dev", "quando": "antes", "status": "bypassed"}]  # nome legado
        (run_dir / "conversa.json").write_text(json.dumps(anterior), encoding="utf-8")

        registro = RegistroCorrecao(quando="02/01/2026 11:00:00", etapa="dev", stages=["dev"], pedido="trocar X",
                                    status="success", triagem={"motivo": "toca só o handoff"})
        mesclar_conversa(run_dir, anterior, result, registro,
                         [{"role": "user", "content": "trocar X"}, {"role": "assistant", "content": mensagem_de_correcao(registro)}])
        nova = json.loads((run_dir / "conversa.json").read_text(encoding="utf-8"))
        self.assertEqual(nova["created_at"], "01/01/2026 10:00:00")
        self.assertEqual(nova["prompt"], "briefing original")
        self.assertEqual([m["content"] for m in nova["messages"]][:2], ["briefing original", "📘 PRD gerado."])
        self.assertEqual(nova["messages"][-2]["content"], "trocar X")
        self.assertIn("recomeçou de **dev**", nova["messages"][-1]["content"])
        self.assertEqual([h["etapa"] for h in nova["historico_correcoes"]], ["dev", "dev"])
        self.assertEqual(nova["historico_correcoes"][-1]["pedido"], "trocar X")
        self.assertEqual(historico_de(nova), nova["historico_correcoes"])

        carregado = load_saved_session(run_dir.name)
        self.assertIsNotNone(carregado)
        msgs, _, meta = carregado
        self.assertEqual(len(meta["historico_correcoes"]), 2)
        self.assertEqual(sum(1 for m in msgs if m.get("pipeline_result")), 1, "só a última resposta carrega o resultado")

    def test_save_session_record_sem_parametros_novos_nao_muda(self):
        run_dir = self.temp_dir / "20260101-000000-x"
        run_dir.mkdir()
        (run_dir / "estado.json").write_text("{}", encoding="utf-8")
        result = PipelineExecutionResult(session_id="s", user_id="u", prompt="p", final_output="o", state={})
        save_session_record(run_dir=run_dir, session_id="s", user_id="u", prompt="p", result=result, messages=[])
        data = json.loads((run_dir / "conversa.json").read_text(encoding="utf-8"))
        self.assertNotIn("historico_correcoes", data)
        self.assertRegex(data["created_at"], r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}$")

    def test_pedido_como_markdown(self):
        from pipeline.reexecucao import PedidoCorrecao
        from tools.doc_parser import DocumentBatch, process_document

        batch = DocumentBatch(documents=[process_document("tetos.md", b"bio: 150"), process_document("scan.pdf", b"nao e pdf")])
        pedido = PedidoCorrecao.de_doc_batch("Subir o teto de bio\npara 150.", batch)
        md = pedido.como_markdown("spec")
        self.assertIn("> Subir o teto de bio", md)
        self.assertIn("#### 📄 tetos.md", md)
        self.assertIn("bio: 150", md)
        self.assertIn("scan.pdf — anexado, mas sem texto extraível", md)
        self.assertIn("O que mudou nesta versão", md)
        self.assertIn("e design e dev, que derivam dela", md)
        self.assertIn("Nenhum.", PedidoCorrecao("x").como_markdown("dev"))


class TestExecutarCorrecao(unittest.TestCase):
    """`executar_correcao_stream` com o runner simulado: sem LLM, mas com disco de verdade."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_output = os.environ.get("OUTPUT_DIR")
        os.environ["OUTPUT_DIR"] = str(self.temp_dir)
        self.run_dir = self.temp_dir / "20260101-000000-exp05ef2b"
        (self.run_dir / "dev").mkdir(parents=True)
        estado = {"briefing": "briefing original", "spec_missao": "# Spec — Teste v1", "jornada_telas": "j",
                  "handoff_dev": "h antigo", "prd_final": "prd antigo", "reexecucoes": 3,
                  "degradacoes": [{"gate": "Gate estrutural", "motivo": "Gate estrutural reprovado"}],
                  "pipeline_bloqueado": True}
        (self.run_dir / "estado.json").write_text(json.dumps(estado), encoding="utf-8")
        (self.run_dir / "PRD.md").write_text("prd antigo", encoding="utf-8")
        (self.run_dir / "dev" / "01-handoff-dev.md").write_text("h antigo", encoding="utf-8")
        (self.run_dir / "conversa.json").write_text(json.dumps({
            "session_id": "session_abc", "user_id": "user_xyz", "created_at": "01/01/2026 10:00:00",
            "prompt": "briefing original", "messages": [{"role": "user", "content": "briefing original"},
                                                        {"role": "assistant", "content": "📘 PRD gerado."}],
        }), encoding="utf-8")
        self.chamadas = []

    def tearDown(self):
        if self.original_output is not None:
            os.environ["OUTPUT_DIR"] = self.original_output
        else:
            os.environ.pop("OUTPUT_DIR", None)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _runner_falso(self, falhar=False):
        chamadas = self.chamadas

        async def falso(**kwargs):
            chamadas.append(kwargs)
            yield {"type": "pipeline_started"}
            if falhar:
                yield {"type": "pipeline_error", "error": "cota esgotada", "result": None}
                return
            estado_final = dict(kwargs["initial_state"], handoff_dev="h novo", prd_final="prd novo")
            # o runner real grava os artefatos; aqui só o que o merge precisa
            (Path(kwargs["run_dir"]) / "PRD.md").write_text("prd novo", encoding="utf-8")
            (Path(kwargs["run_dir"]) / "estado.json").write_text(json.dumps(estado_final), encoding="utf-8")
            result = PipelineExecutionResult(session_id=kwargs["session_id"], user_id=kwargs["user_id"],
                                             prompt=kwargs["prompt"], final_output="ok", state=estado_final,
                                             status="success", output_dir=str(kwargs["run_dir"]))
            yield {"type": "pipeline_completed", "result": result}

        return falso

    def test_fluxo_completo_grava_na_mesma_pasta_e_preserva_conversa(self):
        import asyncio

        import pipeline.runner as runner_mod
        from pipeline.reexecucao import PedidoCorrecao, executar_correcao_stream

        pedido = PedidoCorrecao(texto="trocar o teto de bio para 150")
        with mock.patch.object(runner_mod, "run_orchestrator_pipeline_stream", self._runner_falso()):
            async def coletar():
                return [e async for e in executar_correcao_stream(self.run_dir, "dev", pedido, {"etapa": "dev", "motivo": "só handoff"}, thinking_budget=7)]
            eventos = asyncio.run(coletar())

        tipos = [e["type"] for e in eventos]
        self.assertEqual(tipos[0], "correcao_started")
        self.assertEqual(tipos[-1], "correcao_completed")
        self.assertIn("pipeline_completed", tipos)

        kw = self.chamadas[0]
        self.assertEqual((kw["prompt"], kw["session_id"], kw["user_id"]), ("briefing original", "session_abc", "user_xyz"))
        self.assertEqual(kw["stages"], ["dev"])
        self.assertFalse(kw["registrar_conversa"])
        self.assertEqual(kw["thinking_budget"], 7)
        self.assertEqual(kw["run_dir"], self.run_dir)
        estado_inicial = kw["initial_state"]
        self.assertNotIn("handoff_dev", estado_inicial)
        self.assertNotIn("reexecucoes", estado_inicial)
        self.assertIn("jornada_telas", estado_inicial)
        self.assertIn("> trocar o teto de bio para 150", estado_inicial["pedido_correcao"])
        self.assertEqual([d["gate"] for d in estado_inicial["degradacoes"]], ["Gate estrutural"], "reprovação de produto preservada")

        registro = eventos[-1]["registro"]
        self.assertEqual((registro["etapa"], registro["status"], registro["pedido"]), ("dev", "success", "trocar o teto de bio para 150"))
        self.assertEqual(registro["triagem"]["motivo"], "só handoff")
        backup = self.run_dir / registro["backup"]
        self.assertTrue(backup.is_dir() and backup.parent.name == ".correcoes")
        self.assertEqual((backup / "PRD.md").read_text(encoding="utf-8"), "prd antigo")
        self.assertEqual((self.run_dir / "PRD.md").read_text(encoding="utf-8"), "prd novo")

        conversa = json.loads((self.run_dir / "conversa.json").read_text(encoding="utf-8"))
        self.assertEqual(conversa["created_at"], "01/01/2026 10:00:00")
        self.assertEqual(conversa["prompt"], "briefing original")
        self.assertEqual([m["content"] for m in conversa["messages"]][:3], ["briefing original", "📘 PRD gerado.", "trocar o teto de bio para 150"])
        self.assertIn("recomeçou de **dev**", conversa["messages"][-1]["content"])
        self.assertEqual(conversa["historico_correcoes"][0]["etapa"], "dev")
        self.assertEqual(conversa["status"], "success")

    def test_desfazer_restaura_e_registra(self):
        import pipeline.runner as runner_mod
        from pipeline.reexecucao import PedidoCorrecao, correcao_desfazivel, desfazer_correcao, executar_correcao_sync

        with mock.patch.object(runner_mod, "run_orchestrator_pipeline_stream", self._runner_falso()):
            result, registro = executar_correcao_sync(self.run_dir, "dev", PedidoCorrecao(texto="trocar X"), {"etapa": "spec", "motivo": "m"})
        self.assertEqual(registro["etapa_sugerida"], "spec", "a triagem sugeriu spec e a pessoa escolheu dev")
        self.assertEqual((self.run_dir / "PRD.md").read_text(encoding="utf-8"), "prd novo")
        conversa = json.loads((self.run_dir / "conversa.json").read_text(encoding="utf-8"))
        self.assertIsNotNone(correcao_desfazivel(conversa))

        desfeita = desfazer_correcao(self.run_dir)
        self.assertEqual((desfeita["etapa"], desfeita["status"]), ("dev", "desfeita"))
        self.assertTrue(desfeita["desfeita_em"])
        self.assertEqual((self.run_dir / "PRD.md").read_text(encoding="utf-8"), "prd antigo")
        estado = json.loads((self.run_dir / "estado.json").read_text(encoding="utf-8"))
        self.assertEqual(estado["prd_final"], "prd antigo")
        conversa = json.loads((self.run_dir / "conversa.json").read_text(encoding="utf-8"))
        self.assertEqual(conversa["created_at"], "01/01/2026 10:00:00")
        self.assertEqual([m["content"] for m in conversa["messages"]][:2], ["briefing original", "📘 PRD gerado."])
        self.assertIn("desfeita", conversa["messages"][-1]["content"])
        self.assertNotIn("trocar X", [m["content"] for m in conversa["messages"]][:-1], "as mensagens da correção desfeita saem")
        self.assertEqual([h["status"] for h in conversa["historico_correcoes"]], ["desfeita"])
        self.assertIsNone(correcao_desfazivel(conversa), "não há segunda correção para desfazer")
        self.assertIsNone(desfazer_correcao(self.run_dir))

    def test_erro_restaura_backup_e_registra(self):
        import asyncio

        import pipeline.runner as runner_mod
        from pipeline.reexecucao import executar_correcao_sync

        with mock.patch.object(runner_mod, "run_orchestrator_pipeline_stream", self._runner_falso(falhar=True)):
            result, registro = executar_correcao_sync(self.run_dir, "dev")

        self.assertIsNone(result)
        self.assertEqual(registro["status"], "error")
        self.assertEqual((self.run_dir / "PRD.md").read_text(encoding="utf-8"), "prd antigo", "artefato movido para o backup voltou")
        self.assertEqual((self.run_dir / "dev" / "01-handoff-dev.md").read_text(encoding="utf-8"), "h antigo")
        conversa = json.loads((self.run_dir / "conversa.json").read_text(encoding="utf-8"))
        self.assertEqual(conversa["created_at"], "01/01/2026 10:00:00")
        self.assertIn("Correção não aplicada", conversa["messages"][-1]["content"])
        self.assertEqual(conversa["historico_correcoes"][0]["status"], "error")
        self.assertEqual(len(conversa["messages"]), 3, "sem pedido de texto, só a resposta do assistente entra")

    def test_transversal_e_so_esta_etapa(self):
        import asyncio

        import pipeline.runner as runner_mod
        from pipeline.reexecucao import executar_correcao_sync

        with mock.patch.object(runner_mod, "run_orchestrator_pipeline_stream", self._runner_falso()):
            executar_correcao_sync(self.run_dir, "transversal")
            executar_correcao_sync(self.run_dir, "design", so_esta_etapa=True)
        self.assertEqual(self.chamadas[0]["stages"], ["transversal"])
        self.assertIn("degradacoes", self.chamadas[0]["initial_state"], "transversal não mexe na herança")
        self.assertEqual(self.chamadas[1]["stages"], ["design"])

    def test_briefing_inicial_preserva_o_salvo(self):
        from pipeline.runner import briefing_inicial

        self.assertEqual(briefing_inicial({"briefing": "A"}, "B"), "A")
        self.assertEqual(briefing_inicial({}, "B"), "B")
        self.assertEqual(briefing_inicial(None, ""), "")


class TestTriagem(unittest.TestCase):
    """Parse da triagem e mapa da missão — sem LLM."""

    def test_parse_do_envelope(self):
        from pipeline.reexecucao import Triagem

        ok = Triagem.de_texto('Toca a spec.\n```json\n{"agente":"triagem-correcao","status":"triado","etapa":"Spec","motivo":"muda o bloco 11","resumo_pedido":"trocar EF06CO09","resumo_anexos":"","confianca":"alta"}\n```')
        self.assertEqual((ok.etapa, ok.motivo, ok.confianca), ("spec", "muda o bloco 11", "alta"))
        self.assertTrue(ok.confiavel and ok.reexecuta)

        nenhuma = Triagem.de_texto('```json\n{"status":"triado","etapa":"nenhuma","motivo":"é pergunta"}\n```')
        self.assertTrue(nenhuma.confiavel)
        self.assertFalse(nenhuma.reexecuta)

        so_etapa = Triagem.de_texto('```json\n{"etapa":"dev"}\n```')
        self.assertEqual(so_etapa.etapa, "dev", "a triagem não é gate: não precisa de `status` no envelope")

        refaz_produto = Triagem.de_texto('```json\n{"agente":"triagem-correcao","etapa":"produto"}\n```')
        self.assertEqual(refaz_produto.etapa, "produto", "produto é etapa de correção desde 23/09/2026")

        for ruim in ("sem envelope", '```json\n{"agente":"triagem-correcao","etapa":"marketing"}\n```', '```json\n{"agente":"x","motivo":"sem etapa"}\n```'):
            t = Triagem.de_texto(ruim)
            self.assertEqual(t.etapa, "indefinida", ruim)
            self.assertFalse(t.confiavel)
            self.assertEqual(t.bruto, ruim)

    def test_mapa_da_missao(self):
        from pipeline.reexecucao import montar_mapa_da_missao

        mapa = montar_mapa_da_missao({
            "one_pager": "# One-pager — X", "spec_missao": "# Spec — Teste v1\n\n## 0. Identificação\n- `id: exp05ef2b`\n## 2. Mecanismo\n### Etapa 1",
            "jornada_telas": "j", "handoff_dev": "h", "prd_final": "p", "prd_status": "amarelo", "design_status": "aprovado",
        })
        self.assertIn("exp05ef2b", mapa)
        self.assertIn("produto (one-pager), spec, design, dev (com PRD)", mapa)
        self.assertIn("design=aprovado", mapa)
        self.assertIn("prd=amarelo", mapa)
        self.assertIn("0. Identificação · 2. Mecanismo · Etapa 1", mapa)
        self.assertIn("handoff_dev, prd_final", mapa)
        self.assertIn("nenhuma", montar_mapa_da_missao({}))


class TestAcompanharEsteira(unittest.TestCase):
    """O acompanhamento do app trata os eventos de correção além dos do runner (sem Streamlit real)."""

    def test_eventos_de_correcao(self):
        import asyncio

        import app as app_mod
        from pipeline.orchestrator import stages_para_ui

        result = PipelineExecutionResult(session_id="s", user_id="u", prompt="p", final_output="ok", state={}, status="success")

        async def stream():
            yield {"type": "correcao_started", "etapa": "dev", "stages": ["dev"], "backup": ".correcoes/x-dev", "chaves_removidas": []}
            yield {"type": "agent_started", "agent_name": "A34HandoffDev"}
            yield {"type": "pipeline_completed", "result": result}
            yield {"type": "correcao_completed", "result": result, "registro": {"etapa": "dev", "status": "success"}}

        progress, steps = mock.MagicMock(), mock.MagicMock()
        with mock.patch.object(app_mod, "st", mock.MagicMock()):
            res, registro = asyncio.run(app_mod._acompanhar_esteira(stream(), stages_para_ui(["dev"]), progress, steps))
        self.assertIs(res, result)
        self.assertEqual(registro["etapa"], "dev")
        self.assertTrue(any("Correção a partir de **dev**" in str(c.args[0]) for c in progress.info.call_args_list))

        async def stream_erro():
            yield {"type": "correcao_started", "etapa": "dev", "stages": ["dev"], "backup": "b", "chaves_removidas": []}
            yield {"type": "pipeline_error", "error": "cota", "result": None}
            yield {"type": "correcao_error", "error": "cota", "registro": {"etapa": "dev", "status": "error"}}

        progress2 = mock.MagicMock()
        with mock.patch.object(app_mod, "st", mock.MagicMock()):
            res2, reg2 = asyncio.run(app_mod._acompanhar_esteira(stream_erro(), stages_para_ui(["dev"]), progress2, mock.MagicMock()))
        self.assertIsNone(res2)
        self.assertEqual(reg2["status"], "error")
        self.assertTrue(progress2.error.called)
