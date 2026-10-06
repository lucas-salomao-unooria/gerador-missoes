"""Testes do parecer humano entre etapas: regras, fluxo em disco, execução em segundo plano."""

import asyncio
import json
import os
import tempfile
import threading
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
CONFERENCIA = {"crenca": "B1: o feed mostra o que é popular — cai na comparação com os colegas no Resultado.",
               "fora": "C3, bolha: a semana 5 do bimestre faz o mapa da bolha; aqui não cabe em 50 min."}


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
        # o design também responde por produto (24/09/2026); o dev não
        self.assertEqual(acoes_possiveis(f, "dev", ESTADO_VERDE), [])
        with self.assertRaises(DecisaoInvalida):
            aplicar(f, DE_ACORDO, DEV, COMENTARIO, ESTADO_VERDE, CONFERENCIA)

    def test_design_tambem_responde_por_produto_e_dev_so_por_dev(self):
        f = _aguardando("produto")
        self.assertIn(DE_ACORDO, acoes_possiveis(f, "design", ESTADO_VERDE))
        self.assertEqual(acoes_possiveis(f, "dev", ESTADO_VERDE), [])
        novo, _ = aplicar(f, DE_ACORDO, DESIGN, COMENTARIO, ESTADO_VERDE, CONFERENCIA)
        self.assertEqual(novo["pareceres"][-1]["como"], "design (como Produto)")
        self.assertEqual(acoes_possiveis(_aguardando("dev"), "design", ESTADO_VERDE), [])
        self.assertEqual(acoes_possiveis(_aguardando("design"), "produto", ESTADO_VERDE), [])
        self.assertEqual([p for p in ("produto", "design", "dev", "admin") if passagem.pode_criar_missao(p)],
                         ["produto", "design", "admin"])
        self.assertEqual(passagem.rotulo_donos("produto"), "Produto ou Design")

    def test_comentario_curto_recusado(self):
        with self.assertRaises(DecisaoInvalida):
            aplicar(_aguardando(), DE_ACORDO, PO, "ok, de acordo!!!", ESTADO_VERDE)

    def test_de_acordo_libera_a_proxima_e_registra(self):
        novo, efeito = aplicar(_aguardando(), DE_ACORDO, PO, COMENTARIO, ESTADO_VERDE, CONFERENCIA)
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
        novo, _ = aplicar(f, EXCECAO, ADMIN, COMENTARIO, estado, CONFERENCIA)
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
        f, _ = aplicar(_aguardando(), DE_ACORDO, PO, COMENTARIO, ESTADO_VERDE, CONFERENCIA)
        devolvido, efeito = aplicar(f, DEVOLVER, DESIGN, "A mecânica não fecha com a tela de revelação.", ESTADO_VERDE)
        self.assertIsNone(efeito)
        self.assertEqual((devolvido["etapa"], devolvido["situacao"]), ("produto", DEVOLVIDA))
        # o de acordo do PO deixa de valer: a etapa está sob revisão
        self.assertFalse(devolvido["pareceres"][0]["valido"])
        # o PO decide; ao refazer, a devolutiva vai junto no pedido
        _, efeito = aplicar(devolvido, REFAZER, PO, "Troquei a revelação para a etapa 3.", ESTADO_VERDE)
        self.assertIn("A mecânica não fecha", efeito.pedido)
        # ou reafirma, e a missão volta a estar liberada para design
        reafirmado, _ = aplicar(devolvido, DE_ACORDO, PO, "Mantenho: a revelação está na etapa 3.", ESTADO_VERDE,
                               CONFERENCIA)
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

    def test_dev_devolve_a_design_depois_de_entregar(self):
        """Reabrir uma missão entregue era editar o conversa.json no bucket à mão (05/10/2026)."""
        f = _aguardando("dev", pareceres=[
            {"etapa": "produto", "acao": DE_ACORDO, "valido": True, "comentario": "a", "como": "produto", "quando": "1"},
            {"etapa": "design", "acao": DE_ACORDO, "valido": True, "comentario": "b", "como": "design", "quando": "2"},
        ])
        encerrando, _ = aplicar(f, DE_ACORDO, DEV, COMENTARIO, ESTADO_VERDE)
        entregue = concluir_execucao(encerrando, ok=True)
        self.assertEqual(acoes_possiveis(entregue, "dev", ESTADO_VERDE), [DEVOLVER])
        self.assertEqual(acoes_possiveis(entregue, "admin", ESTADO_VERDE), [DEVOLVER])
        self.assertEqual(acoes_possiveis(entregue, "design", ESTADO_VERDE), [], "quem reabre a entrega é o Dev")
        self.assertEqual(acoes_possiveis(entregue, "produto", ESTADO_VERDE), [])

        devolvido, efeito = aplicar(entregue, DEVOLVER, DEV, "A tela de revelação não cabe no componente do DS.", ESTADO_VERDE)
        self.assertIsNone(efeito, "devolver não refaz: o Design decide")
        self.assertEqual((devolvido["etapa"], devolvido["situacao"]), ("design", DEVOLVIDA))
        self.assertEqual([p["valido"] for p in devolvido["pareceres"]], [True, False, False, True])
        self.assertEqual((devolvido["pareceres"][-1]["etapa"], devolvido["pareceres"][-1]["como"]), ("design", "dev"))
        self.assertIsNone(passagem.dono_da_vez(entregue))
        self.assertEqual(passagem.dono_da_vez(devolvido), "design")

        # de Design para Produto, o caminho de sempre: refaz, volta ao parecer e aí pode devolver
        self.assertNotIn(DEVOLVER, acoes_possiveis(devolvido, "design", ESTADO_VERDE))
        refazendo, efeito = aplicar(devolvido, REFAZER, DESIGN, "Troquei a revelação pelo cartão do DS.", ESTADO_VERDE)
        self.assertIn("não cabe no componente do DS", efeito.pedido)
        self.assertIn(DEVOLVER, acoes_possiveis(concluir_execucao(refazendo, ok=True), "design", ESTADO_VERDE))

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

    def test_de_acordo_de_produto_libera_sem_conferencia_de_leitura(self):
        """25/09/2026: a conferência de leitura foi desligada — o time a sentiu como mais um bloqueio."""
        novo, _ = aplicar(_aguardando(), DE_ACORDO, PO, COMENTARIO, ESTADO_VERDE)
        self.assertNotIn("conferencia", novo["pareceres"][-1])

    def test_conferencia_de_leitura_quando_religada(self):
        """24/09/2026: o PO liberava missões rasas confiando no semáforo. O de acordo de produto
        pedia duas respostas que só quem leu o núcleo dá — e elas seguiam para design no comentário.
        Desligada em 25/09/2026; o mecanismo continua testado para quando for religada."""
        perguntas = {"produto": (("crenca", "Que crença do estudante cai no aha?"),
                                 ("fora", "Que conceito do material fica de fora?"))}
        with mock.patch.dict(passagem.CONFERENCIA_DE_ACORDO, perguntas):
            with self.assertRaises(DecisaoInvalida):
                aplicar(_aguardando(), DE_ACORDO, PO, COMENTARIO, ESTADO_VERDE)
            with self.assertRaises(DecisaoInvalida):
                aplicar(_aguardando(), DE_ACORDO, PO, COMENTARIO, ESTADO_VERDE, {**CONFERENCIA, "fora": "nenhum, ok"})
            novo, _ = aplicar(_aguardando(), DE_ACORDO, PO, COMENTARIO, ESTADO_VERDE, CONFERENCIA)
            p = novo["pareceres"][-1]
            self.assertEqual(p["conferencia"], CONFERENCIA)
            self.assertIn(CONFERENCIA["crenca"], p["comentario"])
            self.assertIn(CONFERENCIA["crenca"], notas_de_passagem(novo))
            # refazer não pede conferência, e as outras etapas não a têm
            aplicar(_aguardando(), REFAZER, PO, COMENTARIO, ESTADO_VERDE)
            novo, _ = aplicar(_aguardando("design"), DE_ACORDO, DESIGN, COMENTARIO, ESTADO_VERDE)
            self.assertNotIn("conferencia", novo["pareceres"][-1])

    def test_profundidade_vermelha_recusa_o_de_acordo_de_produto(self):
        estado = {**ESTADO_VERDE, "profundidade_status": "bloqueado"}
        self.assertNotIn(DE_ACORDO, acoes_possiveis(_aguardando(), "produto", estado))
        self.assertIn(REFAZER, acoes_possiveis(_aguardando(), "produto", estado))


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
        # progresso local isolado por teste, e processo "antigo" (fora da folga de quem acabou de subir)
        self.patches = [mock.patch.dict(os.environ, {"EXECUCAO_LOCAL_DIR": str(Path(self.tmp.name) / "local")}),
                        mock.patch.object(execucao_fundo, "_INICIO_PROCESSO", time.time() - 3600)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def _rodar(self, eventos):
        async def falso(*_a, **_k):
            for e in eventos:
                yield e

        with mock.patch.object(execucao_fundo, "_stream_do_efeito", lambda *a, **k: falso()):
            execucao_fundo.executar_efeito(self.run_dir, passagem.Efeito("iniciar", "design"), "")
            execucao_fundo.aguardar(self.run_dir, 5)

    def _bucket(self):
        return json.loads((self.run_dir / execucao_fundo.ARQUIVO).read_text())

    def test_sucesso_devolve_ao_parecer_do_dono(self):
        self._rodar([{"type": "etapa_started", "backup": ".correcoes/x"},
                     {"type": "agent_started", "agent_name": "D2Jornada"},
                     {"type": "etapa_completed", "result": SimpleNamespace(status="success")}])
        dados = execucao_fundo.ler_execucao(self.run_dir)
        self.assertEqual((dados["situacao"], dados["agente_atual"], dados["backup"]), ("concluida", "D2Jornada", ".correcoes/x"))
        self.assertEqual(self._bucket()["situacao"], "concluida")
        fluxo = passagem.ler_fluxo(self.run_dir)
        self.assertEqual((fluxo["situacao"], fluxo["versao"]), (AGUARDANDO, 5))

    def test_progresso_fica_local_e_o_bucket_so_recebe_inicio_backup_e_fim(self):
        """24/09/2026: gravar cada evento e o batimento no bucket (gcsfuse) coincidiu com o pânico do
        volume que derrubou a instância cinco vezes no meio do Dev. O bucket agora recebe três gravações."""
        eventos = [{"type": "etapa_started", "backup": ".correcoes/x"}]
        eventos += [{"type": "agent_started", "agent_name": f"A{i}"} for i in range(20)]
        eventos += [{"type": "gate_status", "status": {"dev_status": "aprovado"}},
                    {"type": "etapa_completed", "result": SimpleNamespace(status="success")}]
        with mock.patch.object(execucao_fundo, "_gravar", wraps=execucao_fundo._gravar) as no_bucket:
            self._rodar(eventos)
        self.assertEqual(no_bucket.call_count, 3)
        self.assertEqual(execucao_fundo.ler_execucao(self.run_dir)["agente_atual"], "A19")

    def test_falha_do_volume_nao_derruba_a_etapa(self):
        """`Stale file handle` e `Transport endpoint is not connected` no bucket matavam a thread."""
        sem_volume = Path(self.tmp.name) / "volume-caiu" / "execucao.json"  # pasta que não existe
        with mock.patch.object(execucao_fundo, "_caminho_bucket", lambda _r: sem_volume), \
                mock.patch.object(execucao_fundo, "TENTATIVAS", 1):
            self._rodar([{"type": "agent_started", "agent_name": "D2Jornada"},
                         {"type": "etapa_completed", "result": SimpleNamespace(status="success")}])
        self.assertEqual(passagem.ler_fluxo(self.run_dir)["situacao"], AGUARDANDO)

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
        solta = threading.Event()

        async def espera(*_a, **_k):
            while not solta.is_set():
                await asyncio.sleep(0.01)
            yield {"type": "etapa_completed", "result": SimpleNamespace(status="success")}

        with mock.patch.object(execucao_fundo, "_stream_do_efeito", lambda *a, **k: espera()):
            execucao_fundo.executar_efeito(self.run_dir, passagem.Efeito("iniciar", "design"), "")
            try:
                with self.assertRaises(execucao_fundo.ExecucaoEmAndamento):
                    execucao_fundo.executar_efeito(self.run_dir, passagem.Efeito("iniciar", "design"), "")
                self.assertTrue(execucao_fundo.em_execucao(self.run_dir))
                self.assertFalse(execucao_fundo.conferir_execucao_morta(self.run_dir))
            finally:
                solta.set()
                execucao_fundo.aguardar(self.run_dir, 5)

    def test_instancia_que_morreu_restaura_o_backup_e_devolve_ao_dono(self):
        """Depois de um reinício não há thread nem progresso local; o bucket ainda diz `executando`."""
        backup = self.run_dir / ".correcoes" / "b"
        backup.mkdir(parents=True)
        (backup / "estado.json").write_text('{"antes": true}')
        (self.run_dir / "estado.json").write_text('{"pela_metade": true}')
        execucao_fundo._gravar(self.run_dir, {"situacao": "executando", "tipo": "iniciar", "etapa": "design",
                                              "batimento": time.time(), "backup": ".correcoes/b"})
        self.assertFalse(execucao_fundo.em_execucao(self.run_dir))
        self.assertEqual(execucao_fundo.ler_execucao(self.run_dir)["situacao"], "executando")  # do bucket
        # logo depois de subir, a instância anterior pode estar fechando a etapa: espera a folga
        with mock.patch.object(execucao_fundo, "_INICIO_PROCESSO", time.time()):
            self.assertFalse(execucao_fundo.conferir_execucao_morta(self.run_dir))
        self.assertTrue(execucao_fundo.conferir_execucao_morta(self.run_dir))
        self.assertEqual(json.loads((self.run_dir / "estado.json").read_text()), {"antes": True})
        self.assertEqual(passagem.ler_fluxo(self.run_dir)["situacao"], FALHOU)
        self.assertEqual(self._bucket()["situacao"], "falhou")


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
