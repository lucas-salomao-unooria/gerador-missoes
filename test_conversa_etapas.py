"""Testes da conversa com as etapas: arquivo fora dos artefatos, recorte do contexto, agente."""

import asyncio
import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from pipeline import conversa_etapas as conversa
from pipeline import passagem
from pipeline.passagem import AGUARDANDO, DE_ACORDO, GERANDO, novo_fluxo

COMENTARIO = "Conferi a mecânica e o teto de bio; ajustei a descoberta central."


def _fluxo(etapa="design", situacao=AGUARDANDO, **extra):
    return {**novo_fluxo(), "etapa": etapa, "situacao": situacao, **extra}


class TestArquivo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run_dir = Path(self.tmp.name) / "20260924-120000-session_x"
        self.run_dir.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _troca(self, etapa, texto="Por que o gate ficou 🟡?"):
        p = conversa.pergunta(etapa, texto, "design", "design")
        return p, conversa.resposta(etapa, "Porque…", p, {"jornada_telas": "j1"})

    def test_grava_em_ordem_e_separa_por_etapa(self):
        conversa.registrar(self.run_dir, *self._troca("design"))
        conversa.registrar(self.run_dir, *self._troca("dev", "Que eventos o PRD define?"))
        mensagens = conversa.ler(self.run_dir)
        self.assertEqual([m["role"] for m in mensagens], ["user", "assistant", "user", "assistant"])
        self.assertEqual(len(conversa.da_etapa(mensagens, "design")), 2)
        self.assertEqual(mensagens[1]["responde_a"], mensagens[0]["id"])
        self.assertEqual(conversa.da_etapa(mensagens, "dev")[0]["texto"], "Que eventos o PRD define?")

    def test_fica_fora_dos_artefatos(self):
        from pipeline.artifacts import generate_artifact_manifest
        from pipeline.session_store import list_session_files

        (self.run_dir / "PRD.md").write_text("# PRD")
        conversa.registrar(self.run_dir, *self._troca("dev"))
        self.assertNotIn(conversa.ARQUIVO, [p.name for p in list_session_files(self.run_dir)])
        manifesto = json.dumps(generate_artifact_manifest(self.run_dir))
        self.assertIn("PRD.md", manifesto)
        self.assertNotIn(conversa.ARQUIVO, manifesto)

    def test_runner_regravando_conversa_json_nao_apaga_a_conversa(self):
        """O runner regrava o `conversa.json` do zero ao fim da etapa: a conversa não pode morar lá."""
        from pipeline.session_store import save_session_record

        conversa.registrar(self.run_dir, *self._troca("design"))
        save_session_record(run_dir=self.run_dir, session_id="s", user_id="u", prompt="p",
                            result=SimpleNamespace(state={}), messages=[])
        self.assertEqual(len(conversa.ler(self.run_dir)), 2)

    def test_arquivo_ilegivel_vai_para_o_lado_em_vez_de_sobrescrito(self):
        (self.run_dir / conversa.ARQUIVO).write_text("{ quebrado")
        self.assertEqual(conversa.ler(self.run_dir), [])
        conversa.registrar(self.run_dir, *self._troca("produto"))
        self.assertEqual(len(conversa.ler(self.run_dir)), 2)
        guardados = [p for p in self.run_dir.iterdir() if ".ilegivel-" in p.name]
        self.assertEqual(len(guardados), 1)
        self.assertEqual(guardados[0].read_text(), "{ quebrado")

    def test_duas_pessoas_ao_mesmo_tempo_nao_perdem_pergunta(self):
        threads = [threading.Thread(target=conversa.registrar, args=(self.run_dir, *self._troca("dev", f"p{i}")))
                   for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        perguntas = {m["texto"] for m in conversa.ler(self.run_dir) if m["role"] == "user"}
        self.assertEqual(perguntas, {f"p{i}" for i in range(20)})

    def test_resposta_de_versao_refeita(self):
        _, r = self._troca("design")
        self.assertFalse(conversa.de_outra_versao(r, passagem.assinatura_da_etapa({"jornada_telas": "j1"}, "design")))
        self.assertTrue(conversa.de_outra_versao(r, passagem.assinatura_da_etapa({"jornada_telas": "j2"}, "design")))


ESTADO = {
    "spec_missao": "# Spec\n## 1. Descoberta central", "one_pager": "# One-pager",
    "gate_final_status": "amarelo", "gate_final_report": "relatório do gate final",
    "jornada_telas": "jornada", "fluxo_arestas": "fluxo", "copy_strings": "copy v1",
    "copy_strings_revisada": "copy v2", "prototipo_html": "<html>…</html>", "diagramas_html": "<svg/>",
    "qa_entregaveis_report": "qa", "prototipo_lint_report": "lint", "design_status": "amarelo", "design_status_envelope": {"status": "amarelo"},
    "brief_oficio": "briefing de ofício", "prd_final": "# PRD", "handoff_dev": "handoff",
}


class TestContexto(unittest.TestCase):
    def test_design_le_o_que_responde_e_deixa_de_fora_html_versao_velha_e_veredito(self):
        docs = conversa.documentos_da_etapa(ESTADO, "design")
        self.assertEqual(docs[:3], ["jornada_telas", "fluxo_arestas", "copy_strings_revisada"])
        self.assertIn("spec_missao", docs)
        # a spec vem depois dos documentos prioritários e antes do resto da etapa
        self.assertLess(docs.index("qa_entregaveis_report"), docs.index("spec_missao"))
        self.assertLess(docs.index("spec_missao"), docs.index("prototipo_lint_report"))
        for fora in ("prototipo_html", "diagramas_html", "copy_strings", "design_status", "design_status_envelope",
                     "prd_final", "one_pager"):
            self.assertNotIn(fora, docs)

    def test_documento_pulado_nao_entra(self):
        self.assertIn("brief_oficio", conversa.documentos_da_etapa(ESTADO, "design"))
        estado = {**ESTADO, "brief_oficio": "⏭️ A070BriefOficio não executado: etapa bloqueada"}
        self.assertNotIn("brief_oficio", conversa.documentos_da_etapa(estado, "design"))

    def test_produto_nao_le_documento_de_design(self):
        docs = conversa.documentos_da_etapa(ESTADO, "produto")
        self.assertEqual(docs[:2], ["one_pager", "spec_missao"])
        self.assertNotIn("jornada_telas", docs)

    def test_conversa_unica_le_as_tres_etapas(self):
        docs = conversa.documentos_da_etapa(ESTADO, conversa.MISSAO)
        self.assertEqual(docs[:3], ["one_pager", "spec_missao", "jornada_telas"])
        for dentro in ("prd_final", "handoff_dev", "qa_entregaveis_report"):
            self.assertIn(dentro, docs)
        self.assertNotIn("prototipo_html", docs)
        ctx = conversa.montar_contexto(ESTADO, _fluxo(), conversa.MISSAO)
        self.assertIn("### Situação de toda a missão", ctx)
        self.assertIn("design_status", ctx)

    def test_conversa_unica_muda_de_versao_quando_qualquer_etapa_e_refeita(self):
        r = conversa.resposta(conversa.MISSAO, "ok", conversa.pergunta(conversa.MISSAO, "?", "u", "admin"), ESTADO)
        self.assertFalse(conversa.de_outra_versao(r, conversa.assinatura(ESTADO, conversa.MISSAO)))
        refeito = {**ESTADO, "prd_final": "# PRD v2"}
        self.assertTrue(conversa.de_outra_versao(r, conversa.assinatura(refeito, conversa.MISSAO)))

    def test_orcamento_corta_e_lista_o_que_ficou_de_fora(self):
        estado = {"jornada_telas": "j" * 30_000, "fluxo_arestas": "f" * 30_000, "copy_strings_revisada": "c" * 10}
        ctx = conversa.montar_contexto(estado, _fluxo(), "design", orcamento=55_000)
        self.assertIn('cortado="só os primeiros 25000 de 30000 caracteres"', ctx)
        self.assertIn("o resto deste documento não coube", ctx)
        # depois de cortar não sobra orçamento: a copy fica de fora, nomeada
        self.assertIn("Fora do contexto por tamanho", ctx)
        self.assertIn("`copy_strings_revisada`", ctx)

    def test_contexto_tem_semaforo_pareceres_e_situacao(self):
        parecer = {"etapa": "produto", "acao": DE_ACORDO, "como": "produto", "quando": "24/09/2026 10:00:00",
                   "comentario": COMENTARIO, "rodada": 1, "conferencia": {"crenca": "B1 cai no Resultado."}}
        ctx = conversa.montar_contexto(ESTADO, _fluxo(pareceres=[parecer]), "design")
        self.assertIn("🟡 `design_status` = amarelo", ctx)
        self.assertIn("Produto · de acordo", ctx)
        self.assertIn(COMENTARIO, ctx)
        self.assertIn("B1 cai no Resultado.", ctx)
        self.assertIn("aguardando parecer de Design", ctx)
        self.assertIn('<documento chave="spec_missao"', ctx)
        self.assertIn('origem="etapa anterior"', ctx)

    def test_situacao_de_etapa_futura_e_em_execucao(self):
        ctx = conversa.montar_contexto({"one_pager": "x"}, _fluxo("produto"), "dev")
        self.assertIn("ainda não começou", ctx)
        self.assertIn("Nenhum documento desta etapa foi gravado ainda.", ctx)
        ctx = conversa.montar_contexto(ESTADO, _fluxo("design", GERANDO), "design", {"agente_atual": "A073CopyPtBr"})
        self.assertIn("Design gerando agora (agente atual: A073CopyPtBr)", ctx)

    def test_historico_so_as_ultimas_trocas_e_cortadas(self):
        mensagens = []
        for i in range(10):
            p = conversa.pergunta("dev", f"pergunta {i}", "dev", "dev")
            mensagens += [p, conversa.resposta("dev", "r" * 5_000, p, {})]
        texto = conversa.historico_para_modelo(mensagens)
        self.assertNotIn("pergunta 3", texto)
        self.assertIn("pergunta 4", texto)
        self.assertIn("pergunta 9", texto)
        self.assertIn(" […]", texto)
        self.assertNotIn("r" * 2_501, texto)


class TestAgente(unittest.TestCase):
    def test_agente_configurado_e_fora_da_esteira(self):
        from agents.transversal import TRANSVERSAL_METADATA, get_conversa_etapa_agent
        from prompts.loader import list_state_variables

        agente = get_conversa_etapa_agent()
        self.assertEqual(agente.include_contents, "default")
        self.assertEqual(agente.output_key, "resposta_conversa")
        self.assertTrue(all(m["id"] != "A000ConversaEtapa" for m in TRANSVERSAL_METADATA))
        instr = str(agente.instruction)
        self.assertIn(conversa.PEDIDO_RASCUNHO, instr)
        # o que o prompt lê é exatamente o que `estado_da_conversa` entrega (fora o rodapé comum a todo agente)
        entregue = set(conversa.estado_da_conversa("dev", ESTADO, _fluxo("dev"), []))
        lidas = {v for v in list_state_variables(instr) if not v.startswith("bloqueio_modelo_")} - {
            "heranca_degradada", "pedido_correcao", "notas_de_passagem"}
        self.assertEqual(lidas, entregue)

    def test_responder_passa_contexto_e_pergunta_e_devolve_a_saida(self):
        recebido = {}

        class Servico:
            async def create_session(self, app_name, user_id, state):
                self.sessao = SimpleNamespace(id="s1", state=dict(state))
                recebido["state"] = state
                return self.sessao

            async def get_session(self, app_name, user_id, session_id):
                return self.sessao

        class Runner:
            def __init__(self, agent, app_name):
                self.session_service = Servico()

            async def run_async(self, user_id, session_id, new_message):
                recebido["mensagem"] = new_message.parts[0].text
                self.session_service.sessao.state["resposta_conversa"] = "  O PRD define 7 eventos.  "
                return
                yield

        with mock.patch("google.adk.runners.InMemoryRunner", Runner):
            saida = asyncio.run(conversa.responder("Que eventos o PRD define?", "dev", ESTADO, _fluxo("dev"), []))
        self.assertEqual(saida, "O PRD define 7 eventos.")
        self.assertEqual(recebido["mensagem"], "Que eventos o PRD define?")
        self.assertIn('<documento chave="prd_final"', recebido["state"]["contexto_da_etapa"])
        self.assertEqual(recebido["state"]["etapa_da_conversa"], "Dev")

    def test_resposta_vazia_e_falha(self):
        class Servico:
            async def create_session(self, **kw):
                self.sessao = SimpleNamespace(id="s1", state={})
                return self.sessao

            async def get_session(self, **kw):
                return self.sessao

        class Runner:
            def __init__(self, agent, app_name):
                self.session_service = Servico()

            async def run_async(self, **kw):
                return
                yield

        with mock.patch("google.adk.runners.InMemoryRunner", Runner):
            with self.assertRaises(RuntimeError):
                asyncio.run(conversa.responder("?", "dev", ESTADO, _fluxo("dev"), []))


if __name__ == "__main__":
    unittest.main()
