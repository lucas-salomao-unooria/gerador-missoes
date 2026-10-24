"""PR 9 do plano «Produto dono do contrato» (docs/planos/2026-10-23-produto-dono-do-contrato.md, D9): governança da
liberação de produto.

- a conta design continua liberando produto (58c3ed1, 24/09/2026), mas quem liberou — papel e data — fica no registro, no
  estado e à vista em 🟡 «liberado sem a conta produto» no cartão, no catálogo e no dossiê; a marca sobrevive a refazer de
  design e de dev, à correção pontual e à cascata do PR 5, e chega ao handoff e ao PRD, por código, na seção de
  pendências;
- a exceção do admin que libera produto com 🔴 exige justificativa escrita (não vazia, não só espaço ou pontuação),
  gravada com autor e data; sem ela o botão não libera;
- a conferência de leitura do de acordo de produto (desligada em 05feeaf, 25/09/2026) volta só quando há marcador aberto:
  o PO confirma ter lido ou decidido cada item; sem marcador, o de acordo segue como antes.

Casos reais: no acervo de 23/10/2026, 1 de 5 liberações de produto veio da conta produto; as em vigor da exp02em1b
(23/10 16:03) e da exp02ef1b (22/10 15:27) são da conta design, e a exceção do admin de 23/10 15:57 na exp02ef1b dizia
«aprovado com falso positivo». Tudo sem modelo.
"""
from __future__ import annotations

import asyncio
import copy
import json
import warnings
from pathlib import Path
from typing import Any, Dict

import pytest

from pipeline import passagem
from pipeline.passagem import (AGUARDANDO, DE_ACORDO, DEVOLVER, EXCECAO, INICIAR, LIBERADA, REFAZER, DecisaoInvalida,
                               acoes_possiveis, aplicar, concluir_execucao, novo_fluxo)
from tools import governanca as gov
from tools.auth import Sessao

warnings.filterwarnings("ignore", category=DeprecationWarning)

ACERVO = Path(__file__).resolve().parent / "tests" / "acervo"
COMENTARIO = "Conferi o one-pager e a spec; os parâmetros seguem como a sugestão do agente."
JUSTIFICATIVA = "O gate final acusou o §12a por falso positivo; o PO refaz produto na volta do design."


def _sessao(papel: str) -> Sessao:
    return Sessao(usuario=papel, papel=papel, emitida_em=0, expira_em=1e12, jti="x")


PO, DESIGN, DEV, ADMIN = (_sessao(p) for p in ("produto", "design", "dev", "admin"))
VERDE = {"gate_final_status": "aprovado", "design_status": "aprovado", "dev_status": "aprovado",
         "one_pager": "v1", "jornada_telas": "j1", "prd_final": "p1"}
VERMELHO = {**VERDE, "gate_final_status": "bloqueado"}


def _aguardando(etapa: str = "produto", **extra: Any) -> Dict[str, Any]:
    return {**novo_fluxo(), "etapa": etapa, "situacao": AGUARDANDO, **extra}


def _estado(missao: str) -> Dict[str, Any]:
    return json.loads((ACERVO / missao / "estado.json").read_text(encoding="utf-8"))


def _liberado_pelo_design() -> Dict[str, Any]:
    novo, _ = aplicar(_aguardando(), DE_ACORDO, DESIGN, COMENTARIO, VERDE)
    return novo


# --------------------------------------------------------------------------- quem liberou
def test_design_libera_produto_e_o_registro_diz_quem_com_papel_e_data():
    novo = _liberado_pelo_design()
    registro = novo["pareceres"][-1]
    assert (novo["etapa"], novo["situacao"]) == ("design", LIBERADA)  # a conta design continua liberando (58c3ed1)
    assert registro["liberado_sem_conta_produto"] is True
    assert (registro["autor"], registro["como"]) == ("design", "design (como Produto)") and registro["quando"]
    g = passagem.governanca(novo)
    assert g["liberacao"]["papel"] == "design" and not g["liberacao"]["conta_produto"]
    assert [p["codigo"] for p in g["pendencias"]] == [gov.LIBERADO_SEM_CONTA]
    assert gov.marca(g) == f"🟡 liberado sem a conta produto — design (como Produto), {registro['quando']}"


def test_conta_produto_libera_sem_marca_e_o_admin_tambem_e_outra_conta():
    novo, _ = aplicar(_aguardando(), DE_ACORDO, PO, COMENTARIO, VERDE)
    assert "liberado_sem_conta_produto" not in novo["pareceres"][-1]
    assert passagem.governanca(novo)["pendencias"] == [] and gov.marca(passagem.governanca(novo)) == ""
    pelo_admin, _ = aplicar(_aguardando(), DE_ACORDO, ADMIN, COMENTARIO, VERDE)
    assert pelo_admin["pareceres"][-1]["liberado_sem_conta_produto"] is True
    assert passagem.governanca(pelo_admin)["liberacao"]["como"] == "admin (como Produto)"
    # design e dev não são produto: a marca é só da liberação de produto
    design, _ = aplicar(_aguardando("design"), DE_ACORDO, DESIGN, COMENTARIO, VERDE)
    assert "liberado_sem_conta_produto" not in design["pareceres"][-1]


def test_registro_antigo_sem_autor_le_o_papel_do_como_e_sem_nenhum_nao_acusa():
    assert gov.liberou_sem_conta_produto({"etapa": "produto", "acao": "de_acordo", "como": "design (como Produto)"})
    assert not gov.liberou_sem_conta_produto({"etapa": "produto", "acao": "de_acordo", "como": "produto"})
    assert not gov.liberou_sem_conta_produto({"etapa": "produto", "acao": "de_acordo"})
    assert not gov.liberou_sem_conta_produto({"etapa": "produto", "acao": "refazer", "autor": "design"})


def test_marca_sobrevive_a_refazer_de_design_e_dev_a_cascata_e_ao_refazer_nao_aplicado():
    f = _liberado_pelo_design()
    quando = f["pareceres"][-1]["quando"]
    f, _ = aplicar(f, INICIAR, DESIGN, "", VERDE)
    f = concluir_execucao(f, ok=True)
    # refazer de design com item de produto: é a cascata do PR 5 (produto pontual → design)
    divisao = {"etapa": "design", "itens": [{"n": 1, "texto": "Trocar «Publicar no Álbum» por «Colocar no álbum».",
                                             "dono": "produto", "forcado": True, "regra": ["texto do one-pager"]}],
               "contexto": ""}
    f, efeito = aplicar(f, REFAZER, DESIGN, "Trocar o texto da 5B como o PO pediu em 23/10.", VERDE, divisao=divisao)
    assert efeito.tipo == "refazer"
    f = concluir_execucao(f, ok=False, pede_devolver=True)  # refazer que não aplicou nada
    assert passagem.governanca(f)["liberacao"]["quando"] == quando
    f, _ = aplicar(f, REFAZER, DESIGN, "Refazer a jornada da etapa 3 sem a aba.", VERDE)
    f = concluir_execucao(f, ok=True)
    f, _ = aplicar(f, DE_ACORDO, DESIGN, COMENTARIO, VERDE)
    f, _ = aplicar(f, INICIAR, DEV, "", VERDE)
    f = concluir_execucao(f, ok=True)
    f, _ = aplicar(f, REFAZER, DEV, "Refazer o handoff com a tabela de eventos completa.", VERDE)
    f = concluir_execucao(f, ok=True)
    g = passagem.governanca(f)
    assert [p["codigo"] for p in g["pendencias"]] == [gov.LIBERADO_SEM_CONTA]
    assert g["liberacao"]["quando"] == quando


def test_refazer_de_produto_troca_a_marca_pela_da_proxima_liberacao_e_o_historico_fica():
    f = _liberado_pelo_design()
    f, _ = aplicar(f, DEVOLVER, DESIGN, "A mecânica não fecha com a tela de revelação.", VERDE)
    assert passagem.governanca(f)["liberacao"] is None  # devolvida: nenhuma liberação em vigor
    f, _ = aplicar(f, REFAZER, PO, "Troquei a revelação para a etapa 3.", VERDE)
    f = concluir_execucao(f, ok=True)
    f, _ = aplicar(f, DE_ACORDO, PO, COMENTARIO, VERDE)
    g = passagem.governanca(f)
    assert g["pendencias"] == [] and g["liberacao"]["conta_produto"]
    assert [(h["papel"], h["valido"]) for h in g["historico"]] == [("design", False), ("produto", True)]


def test_devolucao_automatica_a_produto_tira_a_liberacao_em_vigor():
    f = _liberado_pelo_design()
    f, _ = aplicar(f, INICIAR, DESIGN, "", VERDE)
    tickets = {"gate_estrutural": [{"id": "QA-1", "resumo": "A spec não diz quantas fotos a 5A tem."}]}
    f = concluir_execucao(f, ok=True, estado={"devolucoes_a_produto": tickets})
    assert f["etapa"] == "produto" and passagem.governanca(f)["liberacao"] is None


# --------------------------------------------------------------------------- exceção do admin com 🔴
@pytest.mark.parametrize("texto", ["", "   ", "...", "— !!!", "\n\t", "_ _", "«»"])
def test_justificativa_trivial_e_recusada(texto):
    assert not gov.justificativa_valida(texto)
    with pytest.raises(DecisaoInvalida, match="justificativa escrita"):
        aplicar(_aguardando(), EXCECAO, ADMIN, COMENTARIO, VERMELHO, justificativa=texto)


@pytest.mark.parametrize("texto", ["x", "7", "Falso positivo no §12a.", "  ok  "])
def test_justificativa_sem_minimo_arbitrario(texto):
    assert gov.justificativa_valida(texto)
    novo, _ = aplicar(_aguardando(), EXCECAO, ADMIN, COMENTARIO, VERMELHO, justificativa=texto)
    assert novo["pareceres"][-1]["justificativa_excecao"]["texto"] == texto.strip()


def test_excecao_com_vermelho_em_produto_grava_a_justificativa_com_autor_e_data():
    novo, _ = aplicar(_aguardando(), EXCECAO, ADMIN, COMENTARIO, VERMELHO, justificativa=JUSTIFICATIVA)
    registro = novo["pareceres"][-1]
    j = registro["justificativa_excecao"]
    assert (j["texto"], j["autor"], j["como"]) == (JUSTIFICATIVA, "admin", "admin (como Produto)")
    assert j["quando"] == registro["quando"] and j["gates_vermelhos"] == ["gate_final_status"]
    g = passagem.governanca(novo)
    assert [p["codigo"] for p in g["pendencias"]] == [gov.LIBERADO_SEM_CONTA, gov.EXCECAO_COM_VERMELHO]
    assert g["pendencias"][1]["justificativa"]["texto"] == JUSTIFICATIVA


def test_so_a_excecao_com_vermelho_em_produto_exige_justificativa():
    assert passagem.exige_justificativa("produto", EXCECAO, VERMELHO)
    assert not passagem.exige_justificativa("produto", DE_ACORDO, VERMELHO)
    assert not passagem.exige_justificativa("produto", EXCECAO, VERDE)  # a exceção do contrato aberto (D3)
    estado_design = {**VERDE, "design_status": "bloqueado"}
    assert not passagem.exige_justificativa("design", EXCECAO, estado_design)
    # design e dev seguem como antes: a exceção de 22/10 10:35 na exp02em1b era de design
    novo, _ = aplicar(_aguardando("design"), EXCECAO, ADMIN, COMENTARIO, estado_design)
    assert novo["pareceres"][-1]["excecao"] and "justificativa_excecao" not in novo["pareceres"][-1]


def test_mutante_justificativa_que_aceita_so_pontuacao_e_pega():
    """Mutante: `justificativa_valida` que aceita qualquer texto não vazio. «...» passaria como justificativa."""
    original = gov.justificativa_valida
    try:
        gov.justificativa_valida = lambda t: bool(str(t or "").strip())
        aplicar(_aguardando(), EXCECAO, ADMIN, COMENTARIO, VERMELHO, justificativa="...")
    finally:
        gov.justificativa_valida = original
    with pytest.raises(DecisaoInvalida):
        aplicar(_aguardando(), EXCECAO, ADMIN, COMENTARIO, VERMELHO, justificativa="...")


# --------------------------------------------------------------------------- conferência de leitura
def test_sem_marcador_aberto_o_de_acordo_segue_como_antes():
    assert passagem.itens_de_conferencia(VERDE) == []
    novo, _ = aplicar(_aguardando(), DE_ACORDO, PO, COMENTARIO, VERDE)
    assert "conferencia_de_leitura" not in novo["pareceres"][-1]


def _produto_exp02em1b() -> Dict[str, Any]:
    e = _estado("exp02em1b-60cfa7f4")
    base = {k: e[k] for k in ("one_pager", "spec_missao_gate0", "nucleo_narrativo") if k in e}
    base["spec_missao"] = e["spec_missao_gate0"]
    base["gate_final_status"] = "aprovado"
    return base


def test_com_contrato_aberto_cada_item_e_decidido_ou_lido():
    estado = _produto_exp02em1b()
    itens = passagem.itens_de_conferencia(estado)
    assert itens and all(i["origem"] == passagem.CONTRATO for i in itens)
    with pytest.raises(DecisaoInvalida, match="sem leitura confirmada"):
        aplicar(_aguardando(), DE_ACORDO, PO, COMENTARIO, estado, estrito=False)
    # um respondido, os outros marcados «Li» na lista (`lido` na resposta) — e o registro diz qual foi qual
    primeiro = itens[0]["id"]
    decisoes = {i["id"]: {"resposta": "", "lido": True} for i in itens[1:]}
    from tools import fechar_contrato as fc
    item0 = fc.itens_em_aberto(estado)[0]
    decisoes[primeiro] = {"resposta": fc.OUTRO if fc.ACEITAR not in item0.opcoes() else fc.ACEITAR, "valor": "90 s"}
    novo, _ = aplicar(_aguardando(), DE_ACORDO, PO, COMENTARIO, estado, decisoes=decisoes, estrito=False)
    conf = novo["pareceres"][-1]["conferencia_de_leitura"]
    assert [c["como"] for c in conf] == ["decidido"] + ["lido"] * (len(itens) - 1)
    # faltando um, a mensagem diz quantos
    del decisoes[itens[-1]["id"]]
    with pytest.raises(DecisaoInvalida, match="1 ainda sem leitura"):
        aplicar(_aguardando(), DE_ACORDO, PO, COMENTARIO, estado, decisoes=decisoes, estrito=False)


def test_com_estrita_o_lido_nao_substitui_a_resposta():
    estado = _produto_exp02em1b()
    lidos = [i["id"] for i in passagem.itens_de_conferencia(estado)]
    with pytest.raises(DecisaoInvalida, match="sem resposta"):
        aplicar(_aguardando(), DE_ACORDO, PO, COMENTARIO, estado, estrito=True, leitura=lidos)


def _com_pendencia_do_po(estado: Dict[str, Any]) -> Dict[str, Any]:
    achado = {"severidade": "decisao_humana", "codigo": "F7",
              "resumo": "Parâmetros de inatividade e de teto de palavras aguardam homologação pelo PO."}
    return {**estado, "gate_final_status": "amarelo",
            "gate_final_status_envelope": {"status": "apto_com_ressalvas", "achados": [
                achado, {"severidade": "atencao", "codigo": "F3", "resumo": "Ressalva cosmética."},
                {"severidade": "decisao_humana", "codigo": "humano",
                 "resumo": "- `[ABERTO — dono: PO: fixar o teto de palavras]` (já está na lista do contrato)"}]},
            "fidelidade_nucleo_status": "amarelo",
            "fidelidade_nucleo_status_envelope": {"status": "apto_com_ressalvas", "achados": [dict(achado)]},
            # gate de design não é de produto
            "design_status": "amarelo",
            "design_status_envelope": {"achados": [{"severidade": "decisao_humana", "codigo": "D8b",
                                                    "resumo": "Licença ARASAAC dos pictogramas."}]}}


def test_pendencia_amarela_que_pede_o_po_entra_uma_vez_e_pede_leitura():
    estado = _com_pendencia_do_po(VERDE)
    itens = passagem.itens_de_conferencia(estado)
    assert [(i["origem"], i["tipo"]) for i in itens] == [(passagem.PENDENCIA, "F7")]
    with pytest.raises(DecisaoInvalida, match="sem leitura confirmada"):
        aplicar(_aguardando(), DE_ACORDO, PO, COMENTARIO, estado)
    novo, _ = aplicar(_aguardando(), DE_ACORDO, PO, COMENTARIO, estado, leitura=[itens[0]["id"]])
    assert novo["pareceres"][-1]["conferencia_de_leitura"][0]["como"] == "lido"
    from tools.diagnostico import bloco_de_passagens

    assert "Conferência de leitura: 1 marcador(es) aberto(s) — 0 decidido(s) na lista do contrato, 1 lido(s)." in \
        bloco_de_passagens({"pareceres_humanos": novo["pareceres"]})
    # refazer e devolver não pedem conferência
    aplicar(_aguardando(), REFAZER, PO, COMENTARIO, estado)


def test_excecao_do_admin_tambem_confirma_a_leitura():
    estado = {**_com_pendencia_do_po(VERDE), "gate_final_status": "bloqueado"}
    ident = passagem.itens_de_conferencia(estado)[0]["id"]
    with pytest.raises(DecisaoInvalida, match="sem leitura confirmada"):
        aplicar(_aguardando(), EXCECAO, ADMIN, COMENTARIO, estado, justificativa=JUSTIFICATIVA)
    novo, _ = aplicar(_aguardando(), EXCECAO, ADMIN, COMENTARIO, estado, justificativa=JUSTIFICATIVA, leitura=[ident])
    assert novo["pareceres"][-1]["excecao"]


def test_pendencias_reais_da_exp01em1b_pedem_leitura():
    """A exp01em1b (e3980485) chegou ao parecer de produto com 4 conflitos «pedido × regra» e o F7 das propostas P0b em
    🟡: decisões do PO que o semáforo amarelo não pedia a ninguém."""
    estado = _estado("exp01em1b-e3980485")
    pend = [i for i in passagem.itens_de_conferencia(estado) if i["origem"] == passagem.PENDENCIA]
    assert {i["tipo"] for i in pend} == {"conflito-pedido-regra", "F7"}
    # os 3 conflitos da fidelidade do one-pager (🔴) citam 3 dos 4 pedidos da do núcleo (🟡): cada pedido é lido uma vez
    assert len(pend) == 5


def test_mutante_conferencia_sempre_ligada_e_pega():
    """Mutante: a conferência pedida mesmo sem marcador aberto — o bloqueio que fez o time desligá-la em 25/09/2026."""
    original = passagem.itens_de_conferencia
    try:
        passagem.itens_de_conferencia = lambda e: [{"id": "x", "origem": "pendencia", "tipo": "t", "assunto": "a"}]
        with pytest.raises(DecisaoInvalida):
            aplicar(_aguardando(), DE_ACORDO, PO, COMENTARIO, VERDE)
    finally:
        passagem.itens_de_conferencia = original
    aplicar(_aguardando(), DE_ACORDO, PO, COMENTARIO, VERDE)


# --------------------------------------------------------------------------- estado, reexecução e disco
def test_chave_de_governanca_sobrevive_a_toda_reexecucao():
    from pipeline import reexecucao as rx

    for chaves in (rx.CHAVES_PRODUTO, rx.CHAVES_SPEC, rx.CHAVES_DESIGN, rx.CHAVES_DEV, rx.CHAVES_TRANSVERSAL,
                   rx.CHAVES_EXECUCAO):
        assert gov.KEY_GOVERNANCA not in chaves
    g = passagem.governanca(_liberado_pelo_design())
    for etapa in ("produto", "spec", "design", "dev", "transversal"):
        limpo, _ = rx.preparar_estado({**VERDE, gov.KEY_GOVERNANCA: g}, etapa)
        assert limpo[gov.KEY_GOVERNANCA] == g


def test_cada_etapa_que_comeca_grava_a_governanca_dos_pareceres():
    from pipeline import reexecucao as rx

    f = _liberado_pelo_design()
    estado: Dict[str, Any] = {gov.KEY_GOVERNANCA: {"liberacao": None, "pendencias": [], "historico": []}}
    rx._com_governanca(estado, {"fluxo": f})
    assert estado[gov.KEY_GOVERNANCA] == passagem.governanca(f)
    sem_fluxo: Dict[str, Any] = {}
    rx._com_governanca(sem_fluxo, {"session_id": "s"})
    assert gov.KEY_GOVERNANCA not in sem_fluxo


def test_registrar_decisao_grava_no_estado_e_o_refazer_de_produto_atualiza(tmp_path):
    fluxo = _aguardando(versao=2)
    (tmp_path / "conversa.json").write_text(json.dumps({"fluxo": fluxo}), encoding="utf-8")
    (tmp_path / "estado.json").write_text(json.dumps(VERDE), encoding="utf-8")
    novo, _ = aplicar(fluxo, DE_ACORDO, DESIGN, COMENTARIO, VERDE)
    gravado = passagem.registrar_decisao(tmp_path, fluxo, novo, DE_ACORDO)
    estado = json.loads((tmp_path / "estado.json").read_text(encoding="utf-8"))
    g = estado[gov.KEY_GOVERNANCA]
    assert g["pendencias"][0]["codigo"] == gov.LIBERADO_SEM_CONTA and g["liberacao"]["como"] == "design (como Produto)"
    devolvido, _ = aplicar(gravado, DEVOLVER, DESIGN, "A mecânica não fecha com a tela de revelação.", VERDE)
    passagem.registrar_decisao(tmp_path, gravado, devolvido, DEVOLVER)
    estado = json.loads((tmp_path / "estado.json").read_text(encoding="utf-8"))
    assert estado[gov.KEY_GOVERNANCA]["liberacao"] is None and len(estado[gov.KEY_GOVERNANCA]["historico"]) == 1


def test_sessao_sem_liberacao_de_produto_nao_ganha_a_chave(tmp_path):
    (tmp_path / "estado.json").write_text(json.dumps(VERDE), encoding="utf-8")
    assert not passagem.gravar_governanca(tmp_path, _aguardando())
    assert gov.KEY_GOVERNANCA not in json.loads((tmp_path / "estado.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- dossiê e catálogo
def test_dossie_marca_a_liberacao_sem_a_conta_produto_e_traz_a_justificativa():
    from tools.diagnostico import bloco_de_passagens

    f = _liberado_pelo_design()
    texto = bloco_de_passagens({"pareceres_humanos": f["pareceres"]})
    assert "- 🟡 **Liberado sem a conta produto — o de acordo de produto em vigor é de design (como Produto)" in texto
    assert "design (como Produto) 🟡 *liberado sem a conta produto* de acordo" in texto
    excecao, _ = aplicar(_aguardando(), EXCECAO, ADMIN, COMENTARIO, VERMELHO, justificativa=JUSTIFICATIVA)
    texto = bloco_de_passagens({"pareceres_humanos": excecao["pareceres"]})
    j = excecao["pareceres"][-1]["justificativa_excecao"]
    assert f"Justificativa da exceção, escrita por admin (como Produto) em {j['quando']}: «{JUSTIFICATIVA}»" in texto
    assert "Exceção do admin com 🔴 em produto" in texto
    # exceção anterior à regra: sem justificativa, e o dossiê diz
    antiga = dict(excecao["pareceres"][-1])
    antiga.pop("justificativa_excecao")
    assert "Sem justificativa registrada" in bloco_de_passagens({"pareceres_humanos": [antiga]})


def test_catalogo_mostra_quem_liberou_sem_mudar_o_status():
    from tools import catalogo

    f = _liberado_pelo_design()
    estado = {**_estado("exp06ef1b"), gov.KEY_GOVERNANCA: passagem.governanca(f)}
    ficha = catalogo.ficha_da_execucao(estado, sessao="s")
    assert ficha["liberacao_produto"].startswith("🟡 liberado sem a conta produto — design (como Produto)")
    assert ficha["status"] == catalogo.ficha_da_execucao(_estado("exp06ef1b"), sessao="s")["status"]
    assert "**Liberação de produto:** 🟡 liberado sem a conta produto" in catalogo.relatorio_markdown(
        {"ficha": ficha, "total": 1, "vizinhas": [], "achados": []})
    # sessão que só tem os pareceres copiados pela rodada final, e sessão sem parecer humano
    assert catalogo.ficha_da_execucao({"pareceres_humanos": f["pareceres"]})["liberacao_produto"]
    assert catalogo.ficha_da_execucao(_estado("exp06ef1b"))["liberacao_produto"] == ""


# --------------------------------------------------------------------------- handoff e PRD
GOV_DUAS = gov.de_produto([{"etapa": "produto", "acao": "excecao", "autor": "admin", "como": "admin (como Produto)",
                            "quando": "23/10/2026 15:57:54", "valido": True,
                            "gates": {"gate_final_status": "🔴", "bncc_status": "🟢"},
                            "justificativa_excecao": {"texto": "status do gate: 🔴 bloqueado por falso positivo, 90 s",
                                                      "autor": "admin", "como": "admin (como Produto)",
                                                      "quando": "23/10/2026 15:57:54"}}])
PRD = "# PRD\n\n## 18. Riscos\n\ntexto\n\n---\n\n## 19. Pendências\n\n### 19.1 Abertas\n\n- item\n\n---\n\n## 20. Fim\n\nfim\n"


def test_bloco_entra_no_fim_da_secao_19_e_e_idempotente():
    novo = gov.com_pendencias(PRD, GOV_DUAS, "prd_final")
    secao_19 = novo.split("## 19. Pendências")[1].split("## 20. Fim")[0]
    assert f"### {gov.TITULO_BLOCO}" in secao_19 and secao_19.index("19.1 Abertas") < secao_19.index(gov.TITULO_BLOCO)
    assert "**Liberado sem a conta produto**" in secao_19 and "**Exceção do admin em produto" in secao_19
    assert gov.com_pendencias(novo, GOV_DUAS, "prd_final") == novo
    assert gov.sem_bloco(novo) == PRD
    # sem pendência (a conta produto liberou depois do refazer), o bloco sai
    assert gov.com_pendencias(novo, gov.de_produto([]), "prd_final") == PRD


def test_bloco_vai_a_secao_7_do_handoff_e_o_anexo_fica_no_fim():
    from tools.conteudo_aprovado import TITULO_ANEXO, com_anexo

    handoff = "# Handoff\n\n## 6. Hipóteses\n\nH1\n\n## 7. Lacunas e pendências carregadas (dono e classe)\n\n- L1\n"
    novo = gov.com_pendencias(handoff, GOV_DUAS, "handoff_dev")
    assert novo.index("## 7. Lacunas") < novo.index(gov.TITULO_BLOCO)
    com = com_anexo(PRD, "# One-pager\n\n## 2. Currículo\n\nEF06CO01\n", [2])
    novo = gov.com_pendencias(com, GOV_DUAS, "prd_final")
    assert novo.index(gov.TITULO_BLOCO) < novo.index("## 20. Fim") < novo.index(TITULO_ANEXO)
    assert gov.sem_bloco(novo) == com
    # sem a seção de pendências, o bloco entra no fim do corpo, como seção própria
    assert gov.com_pendencias("# PRD\n\nsó corpo\n", GOV_DUAS, "prd_final").endswith(
        gov.linhas_do_bloco(GOV_DUAS)[-1] + "\n")


def test_bloco_nao_leva_texto_livre_nem_marcador_de_lacuna():
    """A justificativa (aqui com «status do gate: 🔴 … 90 s») fica no parecer e no dossiê: no PRD ela viraria status de gate
    no corpo e número sem origem — que o redator não tem como consertar."""
    texto = gov.bloco(GOV_DUAS)
    assert "falso positivo" not in texto and "90 s" not in texto
    assert "[" not in texto and "🔵" not in texto
    from tools.conferir_prd_plataforma import _decisao_do_po_provada

    assert not _decisao_do_po_provada(texto, {"23/10/2026"})


def _gates_que_leem_handoff_e_prd(state: Dict[str, Any]) -> Dict[str, Any]:
    """Os gates determinísticos de dev que leem o handoff ou o PRD, como `scripts/regressao_gates.py` os chama."""
    import scripts.regressao_gates as rg
    from pipeline.artifacts import caminhos_de_artefato
    from tools import cobertura_design, conteudo_aprovado, kpis, montagem, prd_codavel, rastro
    from tools.anexo_design import spec_consolidada
    from tools.conferir_prd_plataforma import _decisao_do_po_provada, datas_do_po

    spec, prd, handoff = spec_consolidada(state), str(state.get("prd_final") or ""), str(state.get("handoff_dev") or "")
    banco, one_pager = str(state.get("banco_conteudo") or ""), str(state.get("one_pager") or "")
    def r(resultado: Dict[str, Any]) -> Any:
        return rg._extrair_status_e_codigos(resultado), len(resultado.get("achados") or [])

    return {
        "telemetria": r(rastro.validar_telemetria(handoff)),
        "montagem_handoff": r(montagem.validar_handoff(state)),
        "lacunas": r(rastro.varrer_lacunas(rastro.FONTES_DEV, state, etapa_corrente="dev")),
        "prd_rastro": r(rastro.validar_prd(prd, spec=spec, banco=banco, aprovado=one_pager)),
        "prd_cobertura": r(cobertura_design.validar(prd, {**state, "spec_missao": spec})),
        "prd_codavel": r(prd_codavel.validar(prd, spec, banco, handoff=handoff)),
        "kpis": r(kpis.validar_kpis(prd, spec, one_pager=one_pager)),
        "conteudo_aprovado_prd": r(conteudo_aprovado.validar_prd(prd, spec, one_pager, caminhos_de_artefato())),
        "montagem_prd": r(montagem.validar_prd(state)),
        # a decisão do PO sobre a experiência que já existe (`existente-sem-decisao`): o bloco não a prova
        "decisao_do_po": _decisao_do_po_provada(prd, datas_do_po(state)),
    }


#: Três das sete missões do acervo com PRD: a exp02ef1b (liberada pela conta design em 22/10/2026), a exp06ef1b (o maior
#: PRD) e a exp01ef1b. As sete deram o mesmo veredito com o bloco na medição do PR 9; aqui ficam três pelo tempo da suíte.
MISSOES_COM_PRD = ("exp02ef1b-4fd72a9a", "exp06ef1b-53e011b6", "exp01ef1b")


@pytest.mark.parametrize("missao", MISSOES_COM_PRD)
def test_bloco_nao_muda_veredito_de_gate_nenhum_no_acervo(missao):
    """O bloco entra no handoff e no PRD da missão com as duas pendências, e os gates determinísticos que os leem
    (montagem, rastro, status de gate no corpo, PRD codável, KPIs, conteúdo aprovado, telemetria) dão o mesmo veredito,
    os mesmos códigos e o mesmo número de achados."""
    estado = _estado(missao)
    antes = _gates_que_leem_handoff_e_prd(estado)
    com = copy.deepcopy(estado)
    for chave in ("prd_final", "handoff_dev"):
        if com.get(chave):
            com[chave] = gov.com_pendencias(com[chave], GOV_DUAS, chave)
            assert gov.TITULO_BLOCO in com[chave]
    assert _gates_que_leem_handoff_e_prd(com) == antes


def test_bloco_atualizado_na_correcao_pontual_nao_conta_como_mudanca_do_autor():
    """Na correção pontual o A119 põe o bloco no PRD que não o tinha (sessão anterior ao PR 9): a prova das ordens de não
    mexer («versão anterior + as trocas, nada além») e a diferença linha a linha ignoram o que a esteira escreve, como
    já ignoravam o anexo."""
    from tools import edicao_pontual
    from tools.fidelidade import _diferenca

    troca = [{"documento": "prd_final", "de": "- item", "para": "- item revisto"}]
    atual = gov.com_pendencias(PRD.replace("- item", "- item revisto"), GOV_DUAS, "prd_final")
    assert edicao_pontual.reaplicar(PRD, atual, "prd_final", troca)
    assert _diferenca(PRD, gov.com_pendencias(PRD, GOV_DUAS, "prd_final")) == ([], [])


class _Contexto:
    def __init__(self, state: Dict[str, Any]):
        self.state = state


def test_callback_do_redator_registra_e_troca_o_bloco():
    from agents.callbacks import registrar_governanca

    state = {"prd_final": PRD, gov.KEY_GOVERNANCA: GOV_DUAS}
    registrar_governanca("prd_final")(_Contexto(state))
    assert gov.TITULO_BLOCO in state["prd_final"]
    # o refazer de produto com a conta produto: a próxima rodada do redator tira o bloco
    state[gov.KEY_GOVERNANCA] = gov.de_produto([{"etapa": "produto", "acao": "de_acordo", "autor": "produto",
                                                 "como": "produto", "quando": "24/10/2026 09:00:00"}])
    registrar_governanca("prd_final")(_Contexto(state))
    assert state["prd_final"] == PRD
    # sessão sem parecer humano: nada muda
    sem = {"handoff_dev": "# Handoff\n\n## 7. Lacunas e pendências\n\n- L1\n"}
    registrar_governanca("handoff_dev")(_Contexto(sem))
    assert sem["handoff_dev"] == "# Handoff\n\n## 7. Lacunas e pendências\n\n- L1\n"


def test_redator_e_handoff_tem_o_callback():
    from agents.dev import get_handoff_dev_agent, get_prd_writer_agent

    for agente in (get_handoff_dev_agent(), get_prd_writer_agent()):
        nomes = [c.__name__ for c in agente.after_agent_callback]
        assert f"registrar_governanca_{agente.output_key}" in nomes


def test_anexo_do_prd_atualiza_o_bloco_tambem_na_correcao_pontual():
    """Na correção pontual o redator não roda (nem o callback dele): o A119 põe o bloco como está agora."""
    from google.adk.agents.sequential_agent import SequentialAgent
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    from agents.checkers import AnexoAprovadoAgent
    from tools.conteudo_aprovado import TITULO_ANEXO

    async def rodar(estado):
        agente = AnexoAprovadoAgent(name="A119AnexoPrd", chave="prd_final", secoes=[2])
        runner = InMemoryRunner(agent=SequentialAgent(name="R", sub_agents=[agente]), app_name="teste")
        await runner.session_service.create_session(app_name="teste", user_id="u", session_id="s", state=estado)
        async for _ in runner.run_async(user_id="u", session_id="s",
                                        new_message=types.Content(role="user", parts=[types.Part(text="go")])):
            pass
        final = await runner.session_service.get_session(app_name="teste", user_id="u", session_id="s")
        return dict(final.state)

    estado = {"prd_final": PRD, "one_pager": "# One-pager\n\n## 2. Currículo\n\nEF06CO01\n", gov.KEY_GOVERNANCA: GOV_DUAS}
    final = asyncio.run(rodar(estado))["prd_final"]
    assert final.index(gov.TITULO_BLOCO) < final.index(TITULO_ANEXO)


# --------------------------------------------------------------------------- o cartão no app
def _sessao_em_disco(tmp_path: Path, estado: Dict[str, Any], fluxo: Dict[str, Any]) -> Path:
    run_dir = tmp_path / "20261024-090000-session_gov"
    run_dir.mkdir()
    (run_dir / "estado.json").write_text(json.dumps(estado), encoding="utf-8")
    (run_dir / "conversa.json").write_text(json.dumps({"session_id": "s", "fluxo": fluxo}), encoding="utf-8")
    return run_dir


def _roteiro_do_cartao():
    import json
    import os
    from pathlib import Path

    import streamlit as st

    import app
    from tools.auth import Sessao

    papel = os.environ["GOV_PAPEL"]
    # a sessão que o login (JWT de 4 h) põe no `st.session_state`
    st.session_state["auth_sessao"] = Sessao(usuario=papel, papel=papel, emitida_em=0, expira_em=1e12, jti="x")
    run_dir = Path(os.environ["GOV_RUN_DIR"])
    fluxo = json.loads((run_dir / "conversa.json").read_text(encoding="utf-8"))["fluxo"]
    app._render_trilha(fluxo)
    app._painel_decisao(run_dir, fluxo, {})


def test_cartao_mostra_a_marca_e_a_excecao_com_vermelho_so_libera_com_justificativa(tmp_path, monkeypatch):
    pytest.importorskip("streamlit.testing.v1")
    from streamlit.testing.v1 import AppTest

    estado = {**VERMELHO, "gate_final_status_envelope": {"achados": [
        {"severidade": "bloqueio", "codigo": "F1", "resumo": "O §12a não fecha."}]}}
    run_dir = _sessao_em_disco(tmp_path, estado, {**_aguardando(versao=4), "pareceres": [
        {"etapa": "produto", "acao": "de_acordo", "autor": "design", "como": "design (como Produto)",
         "comentario": "Tudo de acordo e podemos seguir design", "quando": "22/10/2026 15:27:27", "valido": False}]})
    monkeypatch.setenv("GOV_RUN_DIR", str(run_dir))
    monkeypatch.setenv("GOV_PAPEL", "admin")
    at = AppTest.from_function(_roteiro_do_cartao, default_timeout=60)
    at.run()
    assert not at.exception
    excecao = next(b for b in at.button if b.label == "⚠️ Liberar com exceção")
    assert excecao.disabled
    at.text_area(key=f"parecer_{run_dir.name}_4").set_value(COMENTARIO)
    at.text_area(key=f"justificativa_{run_dir.name}_4").set_value("   ...  ").run()
    assert next(b for b in at.button if b.label == "⚠️ Liberar com exceção").disabled
    at.text_area(key=f"justificativa_{run_dir.name}_4").set_value(JUSTIFICATIVA).run()
    excecao = next(b for b in at.button if b.label == "⚠️ Liberar com exceção")
    assert not excecao.disabled
    excecao.click().run()
    fluxo = json.loads((run_dir / "conversa.json").read_text(encoding="utf-8"))["fluxo"]
    registro = fluxo["pareceres"][-1]
    assert (fluxo["etapa"], fluxo["situacao"]) == ("design", LIBERADA)
    assert registro["justificativa_excecao"]["texto"] == JUSTIFICATIVA
    assert registro["justificativa_excecao"]["como"] == "admin (como Produto)"
    estado_gravado = json.loads((run_dir / "estado.json").read_text(encoding="utf-8"))
    assert [p["codigo"] for p in estado_gravado[gov.KEY_GOVERNANCA]["pendencias"]] == [
        gov.LIBERADO_SEM_CONTA, gov.EXCECAO_COM_VERMELHO]


def test_cartao_do_design_liberado_pede_a_leitura_da_pendencia_e_marca_a_liberacao(tmp_path, monkeypatch):
    pytest.importorskip("streamlit.testing.v1")
    from streamlit.testing.v1 import AppTest

    estado = _com_pendencia_do_po(VERDE)
    run_dir = _sessao_em_disco(tmp_path, estado, _aguardando(versao=1))
    monkeypatch.setenv("GOV_RUN_DIR", str(run_dir))
    monkeypatch.setenv("GOV_PAPEL", "design")
    at = AppTest.from_function(_roteiro_do_cartao, default_timeout=60)
    at.run()
    assert not at.exception
    leitura = [c for c in at.checkbox if c.label.startswith("Li e decidi:")]
    assert len(leitura) == 1 and "homologação pelo PO" in leitura[0].label
    at.text_area(key=f"parecer_{run_dir.name}_1").set_value(COMENTARIO)
    de_acordo = next(b for b in at.button if b.label.startswith("✅ De acordo"))
    de_acordo.click().run()
    assert any("sem leitura confirmada" in e.value for e in at.error)
    next(c for c in at.checkbox if c.label.startswith("Li e decidi:")).check()
    next(b for b in at.button if b.label.startswith("✅ De acordo")).click().run()
    fluxo = json.loads((run_dir / "conversa.json").read_text(encoding="utf-8"))["fluxo"]
    assert fluxo["situacao"] == LIBERADA and fluxo["pareceres"][-1]["liberado_sem_conta_produto"]
    # a trilha do cartão, agora, mostra a marca
    at = AppTest.from_function(_roteiro_do_cartao, default_timeout=60)
    at.run()
    assert any("Liberado sem a conta produto — o de acordo de produto em vigor é de design (como Produto)" in c.value
               for c in at.caption)
