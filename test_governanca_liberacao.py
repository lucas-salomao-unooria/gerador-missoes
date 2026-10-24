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
(23/10 16:03) e da exp02ef1b (22/10 15:27) são da conta design. As duas exceções do admin das sessões de 24/10 foram de
design — a de 23/10 15:57 na exp02ef1b dizia só «aprovado com falso positivo» —, e nenhuma de produto teve 🔴: a
justificativa obrigatória vale só para produto. Tudo sem modelo.
"""
from __future__ import annotations

import asyncio
import copy
import json
import re
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
    assert passagem.pendencias_de_conferencia(estado) == itens  # o que o cartão usa, sem montar a lista do contrato
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
    """A exp01em1b (e3980485) chegou ao parecer de produto com 4 conflitos «pedido × regra» em 🟡: decisões do PO que o
    semáforo amarelo não pedia a ninguém. O F7 das propostas P0b, que só resume itens da lista do contrato (19), não pede
    um segundo «Li e decidi»."""
    estado = _estado("exp01em1b-e3980485")
    itens = passagem.itens_de_conferencia(estado)
    pend = [i for i in itens if i["origem"] == passagem.PENDENCIA]
    assert {i["tipo"] for i in pend} == {"conflito-pedido-regra"}
    # os 3 conflitos da fidelidade do one-pager (🔴) citam 3 dos 4 pedidos da do núcleo (🟡): cada pedido é lido uma vez
    assert len(pend) == 4 and len(itens) - len(pend) == 19


def test_aberto_de_outro_dono_nao_e_pedido_ao_po_exp01ef1b():
    """Na exp01ef1b, o rastro da spec deixou em 🟡, como decisão humana, um «[ABERTO — dono: editorial: Confirmação
    documental dos códigos interdisciplinares EF15LP14…]»: não é do PO, e a conferência o pedia como pendência que o PO
    precisava decidir (revisão do PR #75, 24/10/2026)."""
    estado = _estado("exp01ef1b")
    achados = [a for a in estado["rastro_spec_status_envelope"]["achados"] if a.get("severidade") == "decisao_humana"]
    assert any("[ABERTO — dono: editorial:" in a["resumo"] for a in achados)
    assert passagem.pendencias_de_conferencia(estado) == []
    itens = passagem.itens_de_conferencia(estado)
    assert len(itens) == 14 and all(i["origem"] == passagem.CONTRATO for i in itens)
    # o mesmo vale para outro dono qualquer; o conflito «pedido × regra» segue pedindo leitura
    sintetico = {**VERDE, "gate_final_status": "amarelo", "gate_final_status_envelope": {"achados": [
        {"severidade": "decisao_humana", "codigo": "humano", "resumo": "[ABERTO — dono: design: altura da moldura]"},
        {"severidade": "decisao_humana", "codigo": "humano", "resumo": "[ABERTO—dono:plataforma: câmera no tablet]"},
        {"severidade": "decisao_humana", "codigo": "conflito-pedido-regra",
         "resumo": "O pedido conflita com uma regra da esteira — decisão do PO, não do agente: «sem a etapa 5»."}]}}
    assert [i["tipo"] for i in passagem.itens_de_conferencia(sintetico)] == ["conflito-pedido-regra"]


def test_f7_que_resume_a_lista_do_contrato_nao_pede_leitura_de_novo_exp02ef1b():
    """Na exp02ef1b, o F7 do gate final dizia «Parâmetros de inatividade (45s), processamento de IA, teto de palavras
    (15) e área mínima (10%) aguardam homologação pelo PO» — 4 dos 16 itens da lista do contrato, que o PO já responde
    um a um. Sem lista, o F7 é o único lugar da pendência e pede leitura (revisão do PR #75, 24/10/2026)."""
    estado = _estado("exp02ef1b-4fd72a9a")
    f7 = [a for a in estado["gate_final_status_envelope"]["achados"]
          if a.get("codigo") == "F7" and a.get("severidade") == "decisao_humana"]
    assert len(f7) == 1 and "aguardam homologação pelo PO" in f7[0]["resumo"]
    itens = passagem.itens_de_conferencia(estado)
    assert len(itens) == 16 and all(i["origem"] == passagem.CONTRATO for i in itens)
    # o cartão passa se a lista que ele já montou tem item; sem isso, a lista é montada aqui
    assert passagem.pendencias_de_conferencia(estado) == passagem.pendencias_de_conferencia(estado, True) == []
    assert [i["tipo"] for i in passagem.pendencias_de_conferencia(estado, contrato_aberto=False)] == ["F7"]


def test_mutante_conferencia_que_pede_o_que_nao_e_do_po_e_pega(monkeypatch):
    """Mutante: a conferência de antes da revisão do PR #75 — só o [ABERTO — dono: PO] ficava de fora, e o F7 entrava
    mesmo com a lista do contrato aberta. A exp01ef1b e a exp02ef1b pediam um «Li e decidi» cada."""
    import re

    monkeypatch.setattr(passagem, "_RE_MARCADOR_FORA_DA_CONFERENCIA", re.compile(
        r"\[(?:PAR[ÂA]METRO|PROPOSTA)\b|\[ABERTO\s*[—–-]\s*dono:\s*(?:o\s+)?PO\b", re.I))
    monkeypatch.setattr(passagem, "CODIGOS_QUE_RESUMEM_O_CONTRATO", frozenset())
    assert [i["tipo"] for i in passagem.pendencias_de_conferencia(_estado("exp01ef1b"))] == ["humano"]
    assert [i["tipo"] for i in passagem.pendencias_de_conferencia(_estado("exp02ef1b-4fd72a9a"))] == ["F7"]


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

    # o modelo de insumo tem «### 7. Design» antes da seção 7 do handoff (as sete sessões do acervo)
    handoff = ("# Handoff\n\n## 1. Modelo de insumo\n\n### 7. Design\n\nDS unoovista\n\n### 8. Dados\n\nnenhum\n\n"
               "## 6. Hipóteses\n\nH1\n\n## 7. Lacunas e pendências carregadas (dono e classe)\n\n- L1\n")
    novo = gov.com_pendencias(handoff, GOV_DUAS, "handoff_dev")
    assert novo.index("## 7. Lacunas") < novo.index(gov.TITULO_BLOCO) and f"### {gov.TITULO_BLOCO}" in novo
    real = _estado("exp02ef1b-4fd72a9a")["handoff_dev"]
    novo = gov.com_pendencias(real, GOV_DUAS, "handoff_dev")
    assert novo.index("## 7. Lacunas e pendências carregadas") < novo.index(gov.TITULO_BLOCO)
    # «Dependências» (a §15 do PRD) não é a seção de pendências, e sem número a 19 se acha pelo título
    prd = "# PRD\n\n# 15. Dependências e pré-requisitos\n\n- ADR\n\n# 21. Riscos\n\n### Questões abertas e pendências\n\n- Q1\n"
    novo = gov.com_pendencias(prd, GOV_DUAS, "prd_final")
    assert novo.index("Questões abertas e pendências") < novo.index(gov.TITULO_BLOCO)
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


#: Frase que faz do bloco um pré-requisito de codificação: confirmação de alguém «antes de» codificar, ou um responsável
#: que precisa agir. A banca de dev (LLM, «Ausência é NOK») lê o handoff, e o agente de codificação lê o PRD.
_RE_CONDICIONA_CODIFICACAO = re.compile(r"\bantes\s+d[ea]\s+(?:a\s+miss[ãa]o\s+ser\s+)?codific|\bconfirma\b"
                                        r"|\bquem\s+responde\b", re.I)


def test_bloco_e_registro_e_nao_condiciona_a_codificacao_exp02ef1b():
    """Com os pareceres reais da exp02ef1b (a conta design liberou produto em 22/10/2026 15:27:27), o item diz que é
    registro e não pede confirmação do PO antes de codificar — o D9 pede a marca, não um pré-requisito. Até a revisão do
    PR #75 ele dizia «Quem responde é o PO: ele confirma o one-pager e a spec de produto antes de a missão ser
    codificada», logo abaixo da abertura «Não impedem a codificação»."""
    g = passagem.governanca(FLUXO_EXP02EF1B)
    texto = gov.bloco(g)
    item = gov.linhas_do_bloco(g)[0]
    assert gov.ABERTURA_BLOCO in texto and item.endswith(gov.REGISTRO_SEM_CONDICAO)
    assert "`design (como Produto)` em 22/10/2026 15:27:27, e não pela conta `produto`" in item
    for g_ in (g, GOV_DUAS):
        assert not _RE_CONDICIONA_CODIFICACAO.search(gov.bloco(g_)), gov.bloco(g_)
    # o bloco com a redação antiga, já num documento, sai inteiro e dá lugar ao de agora
    antigo = gov.bloco(g).replace(gov.REGISTRO_SEM_CONDICAO, "Quem responde é o PO: ele confirma o one-pager e a spec "
                                  "de produto antes de a missão ser codificada.")
    prd = PRD.replace("- item\n", "- item\n\n" + antigo)
    novo = gov.com_pendencias(prd, g, "prd_final")
    assert novo.count(gov.TITULO_BLOCO) == 1 and not _RE_CONDICIONA_CODIFICACAO.search(novo)
    assert novo == gov.com_pendencias(PRD, g, "prd_final")


def test_mutante_bloco_que_condiciona_a_codificacao_e_pego(monkeypatch):
    """Mutante: o item volta a pedir a confirmação do PO antes de codificar."""
    monkeypatch.setattr(gov, "REGISTRO_SEM_CONDICAO", "Quem responde é o PO: ele confirma o one-pager e a spec de "
                        "produto antes de a missão ser codificada.")
    assert _RE_CONDICIONA_CODIFICACAO.search(gov.bloco(passagem.governanca(FLUXO_EXP02EF1B)))


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


def _rodar(agentes: list, estado: Dict[str, Any]) -> Dict[str, Any]:
    """Roda os agentes em sequência num runner mínimo e devolve o estado final. Sem modelo: os agentes aqui são
    determinísticos ou autores travados (o callback devolve o documento e o modelo não é chamado)."""
    from google.adk.agents.sequential_agent import SequentialAgent
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    async def rodar():
        runner = InMemoryRunner(agent=SequentialAgent(name="R", sub_agents=agentes), app_name="teste")
        await runner.session_service.create_session(app_name="teste", user_id="u", session_id="s", state=estado)
        async for _ in runner.run_async(user_id="u", session_id="s",
                                        new_message=types.Content(role="user", parts=[types.Part(text="go")])):
            pass
        final = await runner.session_service.get_session(app_name="teste", user_id="u", session_id="s")
        return dict(final.state)

    return asyncio.run(rodar())


def _a119():
    from agents.checkers import AnexoAprovadoAgent
    from tools.conteudo_aprovado import SECOES_PRD

    return AnexoAprovadoAgent(name="A119AnexoPrd", chave="prd_final", secoes=list(SECOES_PRD), rotulo="Anexo do PRD")


def test_anexo_do_prd_atualiza_o_bloco_tambem_na_correcao_pontual():
    """Na correção pontual o redator não roda (nem o callback dele): o A119 põe o bloco como está agora."""
    from tools.conteudo_aprovado import TITULO_ANEXO

    estado = {"prd_final": PRD, "one_pager": "# One-pager\n\n## 2. Currículo\n\nEF06CO01\n", gov.KEY_GOVERNANCA: GOV_DUAS}
    final = _rodar([_a119()], estado)["prd_final"]
    assert final.index(gov.TITULO_BLOCO) < final.index(TITULO_ANEXO)


#: O de acordo de produto em vigor da exp02ef1b, como está no `conversa.json` da sessão 4fd72a9a (bucket, 24/10/2026):
#: a conta design liberou produto em 22/10/2026 15:27:27. A exceção do admin de 23/10 15:57:54 foi de design, não de
#: produto. A sessão está em dev, aguardando parecer — o caminho do D11 é Refazer em dev → triagem → cascata.
PARECERES_EXP02EF1B = [
    {"etapa": "produto", "acao": "de_acordo", "autor": "design", "como": "design (como Produto)",
     "comentario": "Tudo de acordo e podemos seguir design", "quando": "22/10/2026 15:27:27", "rodada": 1,
     "valido": True, "excecao": False,
     "gates": {"gate_final_status": "🟡", "rastro_spec_status": "🟡", "bncc_status": "🟢"}},
    {"etapa": "design", "acao": "excecao", "autor": "admin", "como": "admin (como Design)",
     "comentario": "aprovado com falso positivo", "quando": "23/10/2026 15:57:54", "rodada": 7, "valido": True,
     "excecao": True, "gates": {"design_status": "🔴", "lacunas_status": "🔴"}},
]
FLUXO_EXP02EF1B = {**novo_fluxo(), "etapa": "dev", "situacao": AGUARDANDO, "versao": 22,
                   "pareceres": PARECERES_EXP02EF1B}
#: Uma linha do handoff da exp02ef1b que aparece uma vez só: a troca de dev da cascata.
LINHA_DO_HANDOFF = "- **Software clonado**: `Unoogaleria` (aplicativo e visualizador escolar de fotos e álbuns)."


def _dev_pontual_exp02ef1b():
    """O estado da correção pontual de dev da exp02ef1b, como `executar_correcao_stream` o monta: os documentos do
    editor, a troca aplicada, o estado travado e a governança gravada a partir dos pareceres."""
    from pipeline import reexecucao as rx
    from tools import edicao_pontual as ed

    estado = _estado("exp02ef1b-4fd72a9a")
    troca = {"documento": "handoff_dev", "de": LINHA_DO_HANDOFF,
             "para": LINHA_DO_HANDOFF.replace("fotos e álbuns", "fotos e álbuns da turma")}
    r = ed.aplicar(ed.documentos_da_etapa(estado, "dev"), [ed.Edicao(**troca)])
    assert r.ok
    limpo, _ = rx.preparar_estado_pontual(estado, "dev", "### Pedido, na íntegra\n\n> fotos e álbuns da turma",
                                          r.documentos, [troca])
    rx._com_governanca(limpo, {"session_id": "4fd72a9a", "fluxo": FLUXO_EXP02EF1B})
    return limpo, troca


def test_handoff_travado_na_correcao_pontual_de_dev_recebe_o_bloco_exp02ef1b():
    """Na correção pontual de dev o handoff está entre os documentos travados: o redator não roda, o callback dele também
    não, e nenhum passo depois do HandoffLoop reescreve o handoff. Antes da revisão do PR #75, o PRD da exp02ef1b saía
    com a pendência (pelo A119) e o handoff sem ela. Os autores rodam de verdade, travados, sem modelo."""
    from agents.dev import get_handoff_dev_agent, get_prd_writer_agent
    from tools import edicao_pontual as ed

    limpo, troca = _dev_pontual_exp02ef1b()
    assert {"handoff_dev", "prd_final"} <= set(limpo["documentos_travados"])
    assert [p["codigo"] for p in limpo[gov.KEY_GOVERNANCA]["pendencias"]] == [gov.LIBERADO_SEM_CONTA]
    assert gov.TITULO_BLOCO not in limpo["handoff_dev"]  # o handoff do acervo é anterior ao PR 9
    final = _rodar([get_handoff_dev_agent(), get_prd_writer_agent(), _a119()], limpo)
    for chave in ("handoff_dev", "prd_final"):
        assert final[chave].count(gov.TITULO_BLOCO) == 1, chave
        assert "`design (como Produto)` em 22/10/2026 15:27:27" in final[chave]
        assert "Exceção do admin em produto" not in final[chave]  # a de 23/10 15:57 foi de design
    handoff = final["handoff_dev"]
    assert handoff.index("## 7. Lacunas e pendências carregadas") < handoff.index(gov.TITULO_BLOCO)
    # nada além da troca: a prova das ordens de não mexer continua valendo, e a troca está lá
    assert troca["para"] in handoff
    assert ed.reaplicar(limpo["versao_anterior_handoff_dev"], handoff, "handoff_dev", [troca])


def test_mutante_handoff_travado_sem_governanca_e_pego(monkeypatch):
    """Mutante: o documento travado volta como o editor o deixou, sem as pendências de governança — o handoff da
    exp02ef1b em dev pontual saía sem o bloco."""
    import agents.callbacks as cb
    from agents.dev import get_handoff_dev_agent

    monkeypatch.setattr(cb, "documento_com_governanca", lambda state, chave, texto: texto)
    limpo, _ = _dev_pontual_exp02ef1b()
    assert gov.TITULO_BLOCO not in _rodar([get_handoff_dev_agent()], limpo)["handoff_dev"]


ITEM_DO_AUTOR = "- [PENDÊNCIA] H1 do corpo (25%) diverge do §17 (30%) — dono: produto"


def _prd_com_item_depois_do_bloco():
    """O PRD real da exp02ef1b com o bloco e, logo depois dele, um item que o retrabalho do PrdLoop pôs por troca ancorada
    na última linha do bloco — o caso da revisão do PR #75 (24/10/2026)."""
    from tools import edicao_pontual as ed
    from tools.conteudo_aprovado import remover_anexo

    estado = _estado("exp02ef1b-4fd72a9a")
    g = passagem.governanca(FLUXO_EXP02EF1B)
    prd = gov.com_pendencias(remover_anexo(estado["prd_final"]), g, "prd_final")
    ultima = gov.linhas_do_bloco(g)[-1]
    r = ed.aplicar({"prd_final": prd}, [ed.Edicao("prd_final", ultima, f"{ultima}\n{ITEM_DO_AUTOR}")])
    assert r.ok and ITEM_DO_AUTOR in r.documentos["prd_final"]
    return {"one_pager": estado["one_pager"], "prd_final": r.documentos["prd_final"], gov.KEY_GOVERNANCA: g}


def test_item_do_autor_depois_do_bloco_sobrevive_ao_a119():
    """O A119 troca o bloco pelo de agora: sai só o que a esteira escreveu (título, abertura e os dois itens), e o item
    que o autor pôs depois dele fica — antes ele sumia em silêncio, depois de os gates do loop o terem aprovado."""
    estado = _prd_com_item_depois_do_bloco()
    final = _rodar([_a119()], estado)["prd_final"]
    assert ITEM_DO_AUTOR in final and final.count(gov.TITULO_BLOCO) == 1
    assert final.index(ITEM_DO_AUTOR) < final.index(gov.TITULO_BLOCO) < final.index("# 20. Testes")
    corpo = final.split("# 20. Testes")[0]
    assert gov.com_pendencias(corpo, estado[gov.KEY_GOVERNANCA], "prd_final") == corpo  # idempotente
    # o bloco sai inteiro, e só ele
    assert gov.sem_bloco(corpo).count("Liberado sem a conta produto") == 0 and ITEM_DO_AUTOR in gov.sem_bloco(corpo)


def _sem_bloco_guloso(texto: str) -> str:
    """O `sem_bloco` de antes da revisão do PR #75: do título do bloco até o próximo título ou régua."""
    saida, dentro, achou = [], False, False
    for linha in (texto or "").splitlines(keepends=True):
        if gov._RE_TITULO_BLOCO.match(linha):
            dentro = achou = True
            while saida and not saida[-1].strip():
                saida.pop()
            continue
        if dentro and (gov._RE_TITULO.match(linha.rstrip("\n")) or gov._regua(linha)):
            dentro = False
            if saida and saida[-1].strip():
                saida.append("\n")
        if not dentro:
            saida.append(linha)
    return "".join(saida) if achou else texto


def test_mutante_sem_bloco_guloso_e_pego(monkeypatch):
    """Mutante: o `sem_bloco` que apaga tudo do título do bloco até o próximo título — o item do autor some no A119."""
    monkeypatch.setattr(gov, "sem_bloco", _sem_bloco_guloso)
    assert ITEM_DO_AUTOR not in _rodar([_a119()], _prd_com_item_depois_do_bloco())["prd_final"]


HANDOFF = "# Handoff\n\n## 6. Hipóteses\n\nH1\n\n## 7. Lacunas e pendências carregadas\n\n- L1\n\n## 8. Fim\n\nfim\n"


def test_base_do_autor_e_do_editor_vem_sem_o_bloco():
    """O bloco é da esteira, como o anexo: o autor não o recebe na base que mantém «palavra por palavra» — no refazer
    (`anterior_<chave>`), na rodada seguinte do loop (`rodada_anterior_<chave>`) e no editor da correção pontual."""
    from agents.checkers import SaidaDeLoopAgent
    from pipeline import reexecucao as rx
    from tools import edicao_pontual as ed

    com = {"prd_final": gov.com_pendencias(PRD, GOV_DUAS, "prd_final"),
           "handoff_dev": gov.com_pendencias(HANDOFF, GOV_DUAS, "handoff_dev")}
    assert all(gov.TITULO_BLOCO in t for t in com.values())
    estado = {**VERDE, **com, gov.KEY_GOVERNANCA: GOV_DUAS}
    limpo, _ = rx.preparar_estado(estado, "dev")
    docs = ed.documentos_da_etapa(estado, "dev")
    saida = SaidaDeLoopAgent(name="S", status_keys=["g_status"], rodada_key="r", max_rounds=3,
                             autor_keys=["prd_final", "handoff_dev"])
    rodada = _rodar([saida], {**estado, "g_status": "bloqueado"})
    for chave, original in (("prd_final", PRD), ("handoff_dev", HANDOFF)):
        assert limpo[f"versao_anterior_{chave}"] == original.strip()
        assert original.strip() in limpo[f"anterior_{chave}"] and gov.TITULO_BLOCO not in limpo[f"anterior_{chave}"]
        assert docs[chave] == original
        base = rodada[f"rodada_anterior_{chave}"]
        assert original.strip() in base and gov.TITULO_BLOCO not in base and "Liberado sem a conta produto" not in base


def test_retrabalho_por_trocas_esconde_o_bloco_do_editor_e_o_recoloca():
    """Na rodada de retrabalho o editor de trocas corrige o PRD sem ver o bloco, e o PRD volta com ele como está agora —
    o after_agent_callback do redator não roda quando a troca resolve."""
    import os
    from unittest import mock

    import agents.callbacks as cb
    from tools import edicao_pontual as ed

    vistos = []

    async def editor(pedido, etapa, documentos, *, erros="", achados=""):
        vistos.append(documentos["prd_final"])
        return ed.Proposta(modo=ed.MODO_PONTUAL, edicoes=[ed.Edicao("prd_final", "- item", "- item revisto")])

    contexto = _Contexto({"prd_final": gov.com_pendencias(PRD, GOV_DUAS, "prd_final"),
                          "retrabalho_prd_final": "M1: o item da 19.1 está incompleto", gov.KEY_GOVERNANCA: GOV_DUAS})
    with mock.patch.dict(os.environ, {"RETRABALHO_POR_TROCAS": "true"}), \
            mock.patch.object(cb, "PROPONENTE_DE_RETRABALHO", editor):
        conteudo = asyncio.run(cb.retrabalhar_por_trocas("prd_final")(contexto))
    assert vistos == [PRD]
    assert conteudo.parts[0].text == gov.com_pendencias(PRD.replace("- item", "- item revisto"), GOV_DUAS, "prd_final")


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


def test_cartao_com_a_lista_do_contrato_nao_pede_leitura_do_f7_exp02ef1b(tmp_path, monkeypatch):
    """O cartão de produto da exp02ef1b: a lista do contrato (16 itens) pede resposta ou «Li» a cada item, e o F7 que a
    resume não aparece de novo como «Li e decidi» — o cartão e o `aplicar` leem a mesma regra."""
    pytest.importorskip("streamlit.testing.v1")
    from streamlit.testing.v1 import AppTest

    e = _estado("exp02ef1b-4fd72a9a")
    estado = {k: e[k] for k in ("one_pager", "spec_missao_gate0", "nucleo_narrativo", "gate_final_status",
                                "gate_final_status_envelope")}
    estado["spec_missao"] = e["spec_missao_gate0"]
    run_dir = _sessao_em_disco(tmp_path, estado, _aguardando(versao=1))
    monkeypatch.setenv("GOV_RUN_DIR", str(run_dir))
    monkeypatch.setenv("GOV_PAPEL", "design")
    at = AppTest.from_function(_roteiro_do_cartao, default_timeout=60)
    at.run()
    assert not at.exception
    assert any("Contrato de produto em aberto — 16 item(ns)" in m.value for m in at.markdown)
    assert not [c for c in at.checkbox if c.label.startswith("Li e decidi:")]
    assert not any("Conferência de leitura" in m.value for m in at.markdown)
