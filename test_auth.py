"""Testes do login: hash scrypt, JWT de 4 h com relógio injetado, travamento e revogação."""

import json
import tempfile
import unittest
from pathlib import Path

import jwt

from tools.auth import (
    MAX_FALHAS,
    TRAVA_SEGUNDOS,
    ConfiguracaoDeLoginAusente,
    Revogacoes,
    Travas,
    autenticar,
    conferir_hash,
    configuracao_de_login,
    emitir_token,
    gerar_credenciais,
    gerar_hash,
    validar_token,
)

SEGREDO = "s" * 48
T0 = 1_790_000_000.0


def _cfg(horas: float = 4.0):
    senhas, contas, _ = gerar_credenciais()
    return senhas, configuracao_de_login(json.dumps(contas), SEGREDO, horas)


class TestHash(unittest.TestCase):
    def test_senha_certa_e_errada(self):
        h = gerar_hash("abc123")
        self.assertTrue(conferir_hash("abc123", h))
        self.assertFalse(conferir_hash("abc124", h))

    def test_hash_malformado_nao_explode(self):
        self.assertFalse(conferir_hash("x", "md5$qualquer"))
        self.assertFalse(conferir_hash("x", "lixo"))

    def test_salt_diferente_a_cada_hash(self):
        self.assertNotEqual(gerar_hash("mesma"), gerar_hash("mesma"))


class TestConfiguracao(unittest.TestCase):
    def test_sem_credenciais_recusa(self):
        with self.assertRaises(ConfiguracaoDeLoginAusente):
            configuracao_de_login("", SEGREDO)

    def test_segredo_curto_recusa(self):
        _, contas, _ = gerar_credenciais()
        with self.assertRaises(ConfiguracaoDeLoginAusente):
            configuracao_de_login(json.dumps(contas), "curto")

    def test_json_invalido_recusa(self):
        with self.assertRaises(ConfiguracaoDeLoginAusente):
            configuracao_de_login("{nao json", SEGREDO)

    def test_papel_invalido_recusa(self):
        with self.assertRaises(ConfiguracaoDeLoginAusente):
            configuracao_de_login(json.dumps({"x": {"hash": gerar_hash("a"), "papel": "chefe"}}), SEGREDO)

    def test_gerar_credenciais_traz_as_quatro_contas(self):
        senhas, contas, segredo = gerar_credenciais()
        self.assertEqual(set(senhas), {"produto", "design", "dev", "admin"})
        self.assertGreaterEqual(len(segredo), 48)
        self.assertEqual(len(set(senhas.values())), 4)
        for usuario, conta in contas.items():
            self.assertEqual(conta["papel"], usuario)
            self.assertTrue(conferir_hash(senhas[usuario], conta["hash"]))


class TestLogin(unittest.TestCase):
    def setUp(self):
        self.senhas, self.cfg = _cfg()

    def test_login_valido_emite_sessao_de_4h(self):
        sessao, motivo = autenticar(self.cfg, "Design", self.senhas["design"], agora=T0, travas=Travas())
        self.assertEqual(motivo, "")
        self.assertEqual(sessao.papel, "design")
        self.assertEqual(sessao.expira_em - sessao.emitida_em, 4 * 3600)

    def test_senha_errada_e_usuario_inexistente_tem_a_mesma_mensagem(self):
        travas = Travas()
        _, m1 = autenticar(self.cfg, "design", "errada", agora=T0, travas=travas)
        _, m2 = autenticar(self.cfg, "fulano", "errada", agora=T0, travas=travas)
        self.assertEqual(m1, m2)

    def test_trava_apos_cinco_falhas_e_libera_depois(self):
        travas = Travas()
        for _ in range(MAX_FALHAS):
            autenticar(self.cfg, "dev", "errada", agora=T0, travas=travas)
        sessao, motivo = autenticar(self.cfg, "dev", self.senhas["dev"], agora=T0 + 10, travas=travas)
        self.assertIsNone(sessao)
        self.assertIn("Muitas tentativas", motivo)
        sessao, _ = autenticar(self.cfg, "dev", self.senhas["dev"], agora=T0 + TRAVA_SEGUNDOS + 1, travas=travas)
        self.assertIsNotNone(sessao)

    def test_trava_e_por_usuario(self):
        travas = Travas()
        for _ in range(MAX_FALHAS):
            autenticar(self.cfg, "dev", "errada", agora=T0, travas=travas)
        sessao, _ = autenticar(self.cfg, "produto", self.senhas["produto"], agora=T0, travas=travas)
        self.assertIsNotNone(sessao)

    def test_admin_age_por_qualquer_papel_e_assina_como_admin(self):
        admin, _ = autenticar(self.cfg, "admin", self.senhas["admin"], agora=T0, travas=Travas())
        design, _ = autenticar(self.cfg, "design", self.senhas["design"], agora=T0, travas=Travas())
        self.assertTrue(admin.pode_agir_como("produto"))
        self.assertEqual(admin.assinatura_de("produto"), "admin (como Produto)")
        self.assertFalse(design.pode_agir_como("produto"))
        self.assertEqual(design.assinatura_de("design"), "design")


class TestToken(unittest.TestCase):
    def setUp(self):
        self.senhas, self.cfg = _cfg()
        self.sessao, _ = autenticar(self.cfg, "produto", self.senhas["produto"], agora=T0, travas=Travas())
        self.token = emitir_token(self.cfg, self.sessao)

    def test_valido_dentro_das_4h(self):
        s = validar_token(self.cfg, self.token, agora=T0 + 4 * 3600 - 1)
        self.assertEqual(s.usuario, "produto")
        self.assertEqual(s.jti, self.sessao.jti)

    def test_expira_em_4h_absolutas(self):
        self.assertIsNone(validar_token(self.cfg, self.token, agora=T0 + 4 * 3600))

    def test_assinatura_de_outra_chave_recusada(self):
        outro = configuracao_de_login(json.dumps(self.cfg.contas), "o" * 48)
        self.assertIsNone(validar_token(outro, self.token, agora=T0 + 60))

    def test_token_adulterado_recusado(self):
        dados = jwt.decode(self.token, options={"verify_signature": False})
        dados["papel"] = "admin"
        forjado = jwt.encode(dados, "chave-errada-" + "x" * 40, algorithm="HS256")
        self.assertIsNone(validar_token(self.cfg, forjado, agora=T0 + 60))

    def test_alg_none_recusado(self):
        dados = jwt.decode(self.token, options={"verify_signature": False})
        forjado = jwt.encode(dados, None, algorithm="none")
        self.assertIsNone(validar_token(self.cfg, forjado, agora=T0 + 60))

    def test_conta_removida_invalida_o_token(self):
        contas = {k: v for k, v in self.cfg.contas.items() if k != "produto"}
        sem_produto = configuracao_de_login(json.dumps(contas), SEGREDO)
        self.assertIsNone(validar_token(sem_produto, self.token, agora=T0 + 60))

    def test_vazio_ou_lixo(self):
        self.assertIsNone(validar_token(self.cfg, "", agora=T0))
        self.assertIsNone(validar_token(self.cfg, "a.b.c", agora=T0))

    def test_revogado_recusado_e_limpo_apos_expirar(self):
        with tempfile.TemporaryDirectory() as tmp:
            rev = Revogacoes(Path(tmp) / ".auth" / "revogados.json")
            rev.revogar(self.sessao, agora=T0 + 60)
            self.assertIsNone(validar_token(self.cfg, self.token, agora=T0 + 120, revogados=rev))
            # depois do exp, a entrada sai do arquivo na próxima revogação
            outro, _ = autenticar(self.cfg, "dev", self.senhas["dev"], agora=T0 + 5 * 3600, travas=Travas())
            rev.revogar(outro, agora=T0 + 5 * 3600)
            dados = json.loads(rev.caminho.read_text())
            self.assertNotIn(self.sessao.jti, dados)
            self.assertIn(outro.jti, dados)


class TestConfigDoApp(unittest.TestCase):
    def test_settings_expoem_campos_de_login(self):
        import os
        from unittest import mock
        from config import AppSettings
        with mock.patch.dict(os.environ, {"AUTH_CREDENCIAIS": "", "AUTH_SEGREDO_JWT": ""}):
            s = AppSettings()
            with self.assertRaises(ConfiguracaoDeLoginAusente):
                configuracao_de_login(s.auth_credenciais, s.auth_segredo_jwt, s.auth_horas_sessao)
            self.assertEqual(s.auth_horas_sessao, 4.0)


if __name__ == "__main__":
    unittest.main()
