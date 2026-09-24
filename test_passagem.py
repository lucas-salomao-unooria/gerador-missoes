"""Testes do parecer humano entre etapas: regras, fluxo em disco, execução em segundo plano."""

import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from pipeline import execucao_fundo, passagem
from pipeline.passagem import (
    AGUARDANDO, DE_ACORDO, DEVOLVER, DEVOLVIDA, ENCERRANDO, ENTREGUE, EXCECAO, FALHOU, GERANDO, INICIAR,
    LIBERADA, REFAZENDO, REFAZER, ConflitoDeVersao, DecisaoInvalida, acoes_possiveis, aplicar,
    concluir_execucao, notas_de_passagem, novo_fluxo, registrar_fluxo,
)
from tools.auth import Sessao

COMENTARIO = "Conferi a mecânica e o teto de bio; ajustei a descoberta central."


def _sessao(papel: str) -> Sessao:
    return Sessao(usuario=papel, papel=papel, emitida_em=0, expira_em=1e12, jti="x")


PO, DESIGN, DEV, ADMIN = (_sessao(p) for p in ("produto", "design", "dev", "admin"))
ESTADO_VERDE = {"gate_final_status": "aprovado", "design_status": "aprovado", "dev_status": "aprovado",
                "one_pager": "v1", "jornada_telas": "j1", "prd_final": "p1"}


def _aguardando(etapa="produto", **extra):
    return {**novo_fluxo(), "etapa": etapa, "situacao": AGUARDANDO, **extra}


class TestRegras(unittest.TestCase):
    def test_so_o_dono_e_o_admin_agem(self):
        f = _aguardando("produto")
        self.assertIn(DE_ACORDO, acoes_possiveis(f, "produto", ESTADO_VERDE))
        self.assertIn(DE_ACORDO, acoes_possiveis(f, "admin", ESTADO_VERDE))
        self.assertEqual(acoes_possiveis(f, "design", ESTADO_VERDE), [])
        with self.assertRaises(DecisaoInvalida):
            aplicar(f, DE_ACORDO, DESIGN, COMENTARIO, ESTADO_VERDE)

    def test_comentario_curto_recusado(self):
        with self.assertRaises(DecisaoInvalida):
            aplicar(_aguardando(), DE_ACORDO, PO, "ok, de acordo!!!", ESTADO_VERDE)

    def test_de_acordo_libera_a_proxima_e_registra(self):
        novo, efeito = aplicar(_aguardando(), DE_ACORDO, PO, COMENTARIO, ESTADO_VERDE)
        self.assertIsNone(efeito)
        self.assertEqual((novo["etapa"], novo["situacao"]), ("design", LIBERADA))
        p = novo["pareceres"][-1]
        self.assertEqual((p["etapa"], p["acao"], p["como"], p["valido"]), ("produto", DE_ACORDO, "produto", True))
        self.assertEqual(p["gates"], {"gate_final_status": "🟢"})

    def test_vermelho_bloqueia_de_acordo_e_so_admin_libera_com_excecao(self):
        estado = {**ESTADO_VERDE, "gate_final_status": "bloqueado"}
        f = _aguardando()
        self.assertNotIn(DE_ACORDO, acoes_possiveis(f, "produto", estado))
        self.assertNotIn(EXCECAO, acoes_possiveis(f, "produto", estado))
        self.assertIn(EXCECAO, acoes_possiveis(f, "admin", estado))
        novo, _ = aplicar(f, EXCECAO, ADMIN, COMENTARIO, estado)
        self.assertTrue(novo["pareceres"][-1]["excecao"])
        self.assertEqual(novo["pareceres"][-1]["como"], "admin (como Produto)")
        self.assertEqual(novo["situacao"], LIBERADA)

    def test_iniciar_nao_pede_comentario_e_dispara_a_etapa(self):
        f = {**novo_fluxo(), "etapa": "design", "situacao": LIBERADA}
        novo, efeito = aplicar(f, INICIAR, DESIGN, "", ESTADO_VERDE)
        self.assertEqual(novo["situacao"], GERANDO)
        self.assertEqual((efeito.tipo, efeito.etapa), ("iniciar", "design"))
        self.assertEqual(novo["pareceres"], [])

    def test_refazer_volta_ao_mesmo_dono_com_o_comentario_como_pedido(self):
        novo, efeito = aplicar(_aguardando(), REFAZER, PO, COMENTARIO, ESTADO_VERDE)
        self.assertEqual((efeito.tipo, efeito.etapa, efeito.pedido), ("refazer", "produto", COMENTARIO))
        self.assertEqual(novo["situacao"], REFAZENDO)
        depois = concluir_execucao(novo, ok=True)
        self.assertEqual((depois["etapa"], depois["situacao"]), ("produto", AGUARDANDO))

    def test_devolver_nao_refaz_e_reabre_o_parecer_anterior(self):
        f, _ = aplicar(_aguardando(), DE_ACORDO, PO, COMENTARIO, ESTADO_VERDE)
        devolvido, efeito = aplicar(f, DEVOLVER, DESIGN, "A mecânica não fecha com a tela de revelação.", ESTADO_VERDE)
        self.assertIsNone(efeito)
        self.assertEqual((devolvido["etapa"], devolvido["situacao"]), ("produto", DEVOLVIDA))
        # o de acordo do PO deixa de valer: a etapa está sob revisão
        self.assertFalse(devolvido["pareceres"][0]["valido"])
        # o PO decide; ao refazer, a devolutiva vai junto no pedido
        _, efeito = aplicar(devolvido, REFAZER, PO, "Troquei a revelação para a etapa 3.", ESTADO_VERDE)
        self.assertIn("A mecânica não fecha", efeito.pedido)
        # ou reafirma, e a missão volta a estar liberada para design
        reafirmado, _ = aplicar(devolvido, DE_ACORDO, PO, "Mantenho: a revelação está na etapa 3.", ESTADO_VERDE)
        self.assertEqual((reafirmado["etapa"], reafirmado["situacao"]), ("design", LIBERADA))

    def test_design_pode_devolver_depois_de_gerar(self):
        f = _aguardando("design")
        self.assertIn(DEVOLVER, acoes_possiveis(f, "design", ESTADO_VERDE))
        self.assertNotIn(DEVOLVER, acoes_possiveis(_aguardando("produto"), "produto", ESTADO_VERDE))

    def test_refazer_produto_invalida_os_pareceres_a_jusante(self):
        f = _aguardando("dev", pareceres=[
            {"etapa": "produto", "acao": DE_ACORDO, "valido": True, "comentario": "a", "como": "produto", "quando": "1"},
            {"etapa": "design", "acao": DE_ACORDO, "valido": True, "comentario": "b", "como": "design", "quando": "2"},
        ])
        devolvido, _ = aplicar(f, DEVOLVER, DEV, "O contrato de telemetria não cabe no fluxo.", ESTADO_VERDE)
        self.assertEqual(devolvido["etapa"], "design")
        self.assertTrue(devolvido["pareceres"][0]["valido"])
        self.assertFalse(devolvido["pareceres"][1]["valido"])

    def test_de_acordo_do_dev_encerra_a_missao(self):
        novo, efeito = aplicar(_aguardando("dev"), DE_ACORDO, DEV, COMENTARIO, ESTADO_VERDE)
        self.assertEqual(novo["situacao"], ENCERRANDO)
        self.assertEqual(efeito.tipo, "encerrar")
        self.assertEqual(concluir_execucao(novo, ok=True)["situacao"], ENTREGUE)

    def test_falha_de_execucao_permite_rodar_de_novo(self):
        f = {**novo_fluxo(), "etapa": "design", "situacao": GERANDO}
        falhou = concluir_execucao(f, ok=False)
        self.assertEqual(falhou["situacao"], FALHOU)
        self.assertEqual(acoes_possiveis(falhou, "design", ESTADO_VERDE), [INICIAR])
        refazendo = {**f, "situacao": REFAZENDO}
        self.assertEqual(acoes_possiveis(concluir_execucao(refazendo, ok=False), "design", ESTADO_VERDE), [REFAZER])

    def test_assinatura_muda_quando_a_etapa_e_refeita(self):
        a = passagem.assinatura_da_etapa(ESTADO_VERDE, "produto")
        b = passagem.assinatura_da_etapa({**ESTADO_VERDE, "one_pager": "v2"}, "produto")
        self.assertNotEqual(a, b)
        # e não depende do que as etapas seguintes produziram
        c = passagem.assinatura_da_etapa({**ESTADO_VERDE, "prd_final": "outro"}, "produto")
        self.assertEqual(a, c)


class TestNotas(unittest.TestCase):
    def test_so_os_de_acordo_validos_viram_notas(self):
        f = {"pareceres": [
            {"etapa": "produto", "acao": DE_ACORDO, "valido": False, "comentario": "velho", "como": "produto", "quando": "1"},
            {"etapa": "produto", "acao": DE_ACORDO, "valido": True, "comentario": "novo", "como": "produto", "quando": "2"},
            {"etapa": "design", "acao": DEVOLVER, "valido": True, "comentario": "devolutiva", "como": "design", "quando": "3"},
        ]}
        notas = notas_de_passagem(f)
        self.assertIn("> novo", notas)
        self.assertNotIn("velho", notas)
        self.assertNotIn("devolutiva", notas)
        self.assertEqual(notas_de_passagem(None), "")


class TestDisco(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run_dir = Path(self.tmp.name) / "20260923-120000-session_x"
        self.run_dir.mkdir()
        (self.run_dir / "conversa.json").write_text(json.dumps({"session_id": "s", "fluxo": _aguardando()}))

    def tearDown(self):
        self.tmp.cleanup()

    def test_conflito_de_versao(self):
        lido = passagem.ler_fluxo(self.run_dir)
        registrar_fluxo(self.run_dir, lido, lido["versao"])
        with self.assertRaises(ConflitoDeVersao):
            registrar_fluxo(self.run_dir, lido, lido["versao"])

    def test_save_session_record_preserva_o_fluxo(self):
        from pipeline.session_store import save_session_record

        with mock.patch.dict(os.environ, {"OUTPUT_DIR": self.tmp.name}):
            result = SimpleNamespace(state={"one_pager": "x"}, status="success", gates={}, duration_seconds=1,
                                     attached_files=[], step_thoughts={})
            save_session_record(self.run_dir, "s", "u", "prompt", result, [{"role": "user", "content": "oi"}])
        conversa = json.loads((self.run_dir / "conversa.json").read_text())
        self.assertEqual(conversa["fluxo"]["situacao"], AGUARDANDO)

    def test_sessao_antiga_sem_fluxo(self):
        (self.run_dir / "conversa.json").write_text(json.dumps({"session_id": "s"}))
        self.assertIsNone(passagem.ler_fluxo(self.run_dir))

    def test_lista_de_sessoes_expoe_o_fluxo(self):
        from pipeline.session_store import list_saved_sessions

        with mock.patch.dict(os.environ, {"OUTPUT_DIR": self.tmp.name}):
            sessoes = list_saved_sessions()
        self.assertEqual(sessoes[0]["fluxo_etapa"], "produto")
        self.assertEqual(sessoes[0]["fluxo_situacao"], AGUARDANDO)


class TestExecucaoFundo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run_dir = Path(self.tmp.name) / "missao"
        self.run_dir.mkdir()
        fluxo = {**novo_fluxo(), "etapa": "design", "situacao": GERANDO, "versao": 4}
        (self.run_dir / "conversa.json").write_text(json.dumps({"fluxo": fluxo}))

    def tearDown(self):
        self.tmp.cleanup()

    def _rodar(self, eventos):
        async def falso(*_a, **_k):
            for e in eventos:
                yield e

        with mock.patch.object(execucao_fundo, "_stream_do_efeito", lambda *a, **k: falso()):
            execucao_fundo.executar_efeito(self.run_dir, passagem.Efeito("iniciar", "design"), "")
            execucao_fundo.aguardar(self.run_dir, 5)

    def test_sucesso_devolve_ao_parecer_do_dono(self):
        self._rodar([{"type": "etapa_started", "backup": ".correcoes/x"},
                     {"type": "agent_started", "agent_name": "D2Jornada"},
                     {"type": "etapa_completed", "result": SimpleNamespace(status="success")}])
        dados = execucao_fundo.ler_execucao(self.run_dir)
        self.assertEqual((dados["situacao"], dados["agente_atual"], dados["backup"]), ("concluida", "D2Jornada", ".correcoes/x"))
        fluxo = passagem.ler_fluxo(self.run_dir)
        self.assertEqual((fluxo["situacao"], fluxo["versao"]), (AGUARDANDO, 5))

    def test_erro_marca_falhou(self):
        self._rodar([{"type": "etapa_error", "error": "cota do modelo"}])
        self.assertEqual(execucao_fundo.ler_execucao(self.run_dir)["erro"], "cota do modelo")
        self.assertEqual(passagem.ler_fluxo(self.run_dir)["situacao"], FALHOU)

    def test_excecao_no_stream_nao_deixa_gerando_para_sempre(self):
        async def quebra(*_a, **_k):
            raise RuntimeError("boom")
            yield  # pragma: no cover

        with mock.patch.object(execucao_fundo, "_stream_do_efeito", lambda *a, **k: quebra()):
            execucao_fundo.executar_efeito(self.run_dir, passagem.Efeito("iniciar", "design"), "")
            execucao_fundo.aguardar(self.run_dir, 5)
        self.assertEqual(passagem.ler_fluxo(self.run_dir)["situacao"], FALHOU)

    def test_uma_execucao_por_sessao(self):
        execucao_fundo._gravar(self.run_dir, {"situacao": "executando", "batimento": time.time()})
        with self.assertRaises(execucao_fundo.ExecucaoEmAndamento):
            execucao_fundo.executar_efeito(self.run_dir, passagem.Efeito("iniciar", "design"), "")

    def test_batimento_velho_vira_falha_e_restaura_o_backup(self):
        backup = self.run_dir / ".correcoes" / "b"
        backup.mkdir(parents=True)
        (backup / "estado.json").write_text('{"antes": true}')
        (self.run_dir / "estado.json").write_text('{"pela_metade": true}')
        execucao_fundo._gravar(self.run_dir, {"situacao": "executando", "batimento": time.time() - 600,
                                              "backup": ".correcoes/b"})
        self.assertFalse(execucao_fundo.em_execucao(self.run_dir))
        self.assertTrue(execucao_fundo.conferir_execucao_morta(self.run_dir))
        self.assertEqual(json.loads((self.run_dir / "estado.json").read_text()), {"antes": True})
        self.assertEqual(passagem.ler_fluxo(self.run_dir)["situacao"], FALHOU)


class TestOrquestradorEDossie(unittest.TestCase):
    def test_sem_transversal_nao_monta_diagnostico_nem_catalogo(self):
        from pipeline.orchestrator import create_mission_orchestrator, iter_agent_tree

        nomes = {a.name for _, a in iter_agent_tree(create_mission_orchestrator(stages=["produto"], com_transversal=False))}
        self.assertNotIn("A50Diagnostico", nomes)
        self.assertNotIn("A52RegistroCatalogo", nomes)
        com = {a.name for _, a in iter_agent_tree(create_mission_orchestrator(stages=["produto"]))}
        self.assertIn("A50Diagnostico", com)

    def test_dossie_ganha_a_secao_passagens(self):
        from tools.diagnostico import bloco_de_passagens

        texto = bloco_de_passagens({"pareceres_humanos": [
            {"etapa": "produto", "acao": "refazer", "como": "produto", "quando": "1", "comentario": "trocar a revelação"},
            {"etapa": "produto", "acao": "de_acordo", "como": "produto", "quando": "2", "comentario": "ok agora"},
            {"etapa": "dev", "acao": "excecao", "como": "admin (como Dev)", "quando": "3", "comentario": "exceção"},
        ]})
        self.assertIn("## Passagens", texto)
        self.assertIn("### Produto — 1 volta(s)", texto)
        self.assertIn("liberou com exceção", texto)
        self.assertEqual(bloco_de_passagens({}), "")


if __name__ == "__main__":
    unittest.main()
