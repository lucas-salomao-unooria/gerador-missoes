"""PR 3 do plano «Produto dono do contrato» (docs/planos/2026-10-23-produto-dono-do-contrato.md, D3 e D5): o de acordo
de produto fecha o contrato e grava.

- o cartão lista cada [PARÂMETRO], [PROPOSTA] e [ABERTO — dono: PO] do one-pager e da spec do Gate 0, agrupado pelo
  assunto, com a sugestão do agente e as respostas aceitar / outro valor / recusar / deixar para o design (só UI);
- as respostas viram troca de linha determinística no one-pager e na spec do Gate 0 («valor — PO, parecer de <data>»),
  gravada antes de o fluxo liberar o design;
- «Tudo de acordo» no comentário não aprova [PROPOSTA]; com ESTEIRA_ESTRITA não há de acordo sem resposta, só a exceção
  do admin, registrada;
- a decisão sobrevive ao refazer: volta preenchida quando o marcador reabre, segue nas notas de passagem, e a que o
  refazer apagou do texto aparece no cartão;
- o rastro conta o marcador aberto como pendência do PO; os padrões de `defaults-missao.md` aplicados aparecem como
  «padrão a confirmar» (D5).

Caso real: na exp02em1b (60cfa7f4) o PO decidiu 90 s, 45 palavras e «StoryPoll — não implementar» no de acordo de
21/10/2026 15:43 e nada foi gravado. Tudo sem modelo, sobre os estados do acervo (`tests/acervo`).
"""
from __future__ import annotations

import copy
import json
import re
import warnings
from pathlib import Path
from typing import Any, Dict

import pytest

from pipeline import passagem
from pipeline.passagem import (AGUARDANDO, DE_ACORDO, EXCECAO, LIBERADA, REFAZER, DecisaoInvalida, acoes_possiveis,
                               aplicar, novo_fluxo)
from tools import contrato_produto, rastro
from tools import fechar_contrato as fc
from tools.auth import Sessao

warnings.filterwarnings("ignore", category=DeprecationWarning)

ACERVO = Path(__file__).resolve().parent / "tests" / "acervo"
MISSAO = "exp02em1b-60cfa7f4"
#: O de acordo de produto da exp02em1b, 21/10/2026 15:43:51, como o PO o escreveu (conversa.json da sessão). O refazer de
#: produto de 23/10 o invalidou.
DE_ACORDO_21_10 = """Propostas:
[PROPOSTA: validar com PO: Preservação de duas seções do DS (unooriaai + unoovista) em sessão de 50 minutos] → aprovado
[PROPOSTA: validar com PO: Sinalização voluntária de EM13CO08 no Unoovista sem pop-up impositivo] → aprovado
[PROPOSTA P0b: validar com PO: Utilização do componente StoryPoll nativo do Unoovista como suporte ao Canal B das 4 habilidades] → ignorar / não implementar

Parâmetros:
[PARÂMETRO: a definir por produto: tempo de inatividade no chat] → 90s
[PARÂMETRO: a definir por produto: teto de palavras por parágrafo, sugestão: 45 palavras] → 45 palavras"""
COMENTARIO = "Tudo de acordo e podemos seguir design, conferi o contrato."


def _sessao(papel: str) -> Sessao:
    return Sessao(usuario=papel, papel=papel, emitida_em=0, expira_em=1e12, jti="x")


PO, ADMIN = _sessao("produto"), _sessao("admin")


def _estado(missao: str = MISSAO) -> Dict[str, Any]:
    return json.loads((ACERVO / missao / "estado.json").read_text(encoding="utf-8"))


def _produto_estado() -> Dict[str, Any]:
    """A sessão como estava no parecer de produto: one-pager e spec do Gate 0, sem o design."""
    e = _estado()
    base = {k: e[k] for k in ("one_pager", "spec_missao_gate0", "nucleo_narrativo") if k in e}
    base["spec_missao"] = e["spec_missao_gate0"]
    base["gate_final_status"] = "aprovado"
    return base


def _fluxo(*pareceres: Dict[str, Any]) -> Dict[str, Any]:
    return {**novo_fluxo(), "etapa": "produto", "situacao": AGUARDANDO, "versao": 3, "pareceres": list(pareceres)}


PARECER_21_10 = {"etapa": "produto", "acao": DE_ACORDO, "autor": "produto", "como": "produto",
                 "comentario": DE_ACORDO_21_10, "quando": "21/10/2026 15:43:51", "rodada": 1, "valido": False}


def _por_assunto(itens, trecho: str):
    return next(i for i in itens if trecho in i.assunto)


def _marcadores(itens):
    """Os itens dos marcadores (PR 3), sem os textos-chave acima do teto que o PR 7 acrescentou à lista."""
    return [i for i in itens if getattr(i, "tipo", None) != fc.TEXTO_TETO and (
        not isinstance(i, dict) or i.get("tipo") != fc.TEXTO_TETO)]


def _sem_teto(registros):
    return [r for r in registros if r.get("tipo") != fc.TEXTO_TETO]


# --------------------------------------------------------------------------- a lista do cartão
def test_lista_agrupa_o_mesmo_assunto_do_one_pager_e_da_spec():
    """60cfa7f4: 4 [PARÂMETRO] e 13 [PROPOSTA] na spec do Gate 0, 3 + 3 no one-pager — 10 decisões. O parâmetro do
    one-pager sem sugestão ganha a da spec (90 s); a linha do bloco 12 que registra a mesma proposta é o mesmo item."""
    itens = _marcadores(fc.itens_em_aberto(_produto_estado()))
    assert len(itens) == 10
    tempo = _por_assunto(itens, "tempo de inatividade no chat")
    assert tempo.tipo == fc.PARAMETRO and tempo.sugestao == "90 segundos"
    assert {o.documento for o in tempo.ocorrencias} == {"one_pager", "spec"}
    assert any("Calibração de nudge" in o.linha for o in tempo.ocorrencias)
    assert _por_assunto(itens, "teto de palavras por parágrafo").sugestao == "45 palavras"
    story = _por_assunto(itens, "StoryPoll nativo")
    assert story.tipo == fc.PROPOSTA and len(story.ocorrencias) == 3
    # as PQ sem descrição no marcador pegam a linha da tabela, uma por item
    assert sum(1 for i in itens if i.assunto.startswith("PQ-0")) == 5
    # a citação do formato («`[PARÂMETRO — a definir por produto: …]`», L2 do one-pager) não é item
    assert not any("…" == i.assunto for i in itens)


def test_marcador_citado_depois_de_marcador_nao_e_item():
    """exp01em1b-e3980485, uma das missões que serão refeitas: «Quatro propostas pontuais submetidas ao PO registradas
    com marcador normativo `[PROPOSTA P0b — validar com PO]`» virava o 12º item, e o «Aceitar as sugestões» gravava a
    frase de resumo como proposta aprovada. O [PROPOSTA] sem descrição em prosa que não cita o marcador continua item
    (exp03ef1b-317df247, exp05ef1b)."""
    itens = _marcadores(fc.itens_em_aberto(_estado("exp01em1b-e3980485")))
    assert len(itens) == 11
    assert not any("Nenhuma pendência" in i.assunto for i in itens)
    assert any("dois cards anônimos" in i.assunto for i in fc.itens_em_aberto(_estado("exp03ef1b-317df247")))
    assert any(i.assunto.startswith("Manutenção da cota de 8 mensagens") or "cota de 8 mensagens" in i.assunto
               for i in fc.itens_em_aberto(_estado("exp05ef1b")))
    # o rastro lê igual: a frase de resumo não é pendência do PO
    spec = fc.documentos(_estado("exp01em1b-e3980485"))[fc.DOC_SPEC]
    resumo = next(l for l in spec.splitlines() if "marcador normativo" in l)
    r = rastro.varrer_lacunas(rastro.FONTES_SPEC, {"spec_missao": resumo}, etapa_corrente="produto")
    assert r["achados"] == [] and r["status"] == "aprovado"


def test_deixar_para_o_design_so_no_que_e_de_ui():
    itens = fc.itens_em_aberto(_estado("exp03em1b-b2e7b4a3"))
    lupa = _por_assunto(itens, "lupa/zoom")
    assert fc.DESIGN in lupa.opcoes()
    assert fc.DESIGN not in _por_assunto(itens, "Santos Dumont").opcoes()  # muda o que acontece após o Aha
    assert all(fc.DESIGN not in i.opcoes() for i in fc.itens_em_aberto(_produto_estado()))


def test_parametro_sem_sugestao_nao_tem_aceitar():
    itens = fc.itens_em_aberto(_estado("exp02ef1b-4fd72a9a"))
    sem = _por_assunto(itens, "tempo de processamento de geração assíncrona")
    assert sem.sugestao == "" and sem.opcoes() == [fc.OUTRO, fc.RECUSAR]
    # «Metas e limiares das 5 perguntas PQ-01 a PQ-05» não é a linha da PQ-01
    assert _por_assunto(itens, "Metas e limiares").ocorrencias[0].linha.lstrip().startswith("- ")


# --------------------------------------------------------------------------- o caso real
def test_de_acordo_de_21_10_volta_preenchido_e_grava_no_one_pager_e_na_spec(tmp_path):
    """O de acordo escrito à mão em 21/10 volta ao cartão já respondido (a decisão sobrevive ao refazer de 23/10), e o
    novo de acordo grava 90 s, 45 palavras e a recusa do StoryPoll no one-pager e na spec do Gate 0."""
    estado = _produto_estado()
    fluxo = _fluxo(PARECER_21_10)
    itens = fc.itens_em_aberto(estado)
    anteriores = fc.respostas_anteriores(estado, fluxo, itens)
    esperado = {"tempo de inatividade no chat": fc.ACEITAR, "teto de palavras por parágrafo": fc.ACEITAR,
                "Preservação de duas seções": fc.ACEITAR, "Sinalização voluntária de EM13CO08": fc.ACEITAR,
                "StoryPoll nativo": fc.RECUSAR}
    for trecho, resposta in esperado.items():
        assert anteriores[_por_assunto(itens, trecho).id]["resposta"] == resposta, trecho
    assert all(i.id not in anteriores for i in itens if i.assunto.startswith("PQ-0"))
    # o PO confirma o que já tinha respondido e aceita as sugestões do resto, sobre a lista na tela
    respostas = fc.aceitar_sugestoes(itens, anteriores)

    (tmp_path / "estado.json").write_text(json.dumps(estado, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "conversa.json").write_text(json.dumps({"fluxo": fluxo}, ensure_ascii=False), encoding="utf-8")
    novo, efeito = aplicar(fluxo, DE_ACORDO, PO, COMENTARIO, estado, decisoes=respostas, estrito=True)
    assert efeito is None and novo["situacao"] == LIBERADA and novo["etapa"] == "design"
    registro = novo["pareceres"][-1]
    assert not registro["sem_resposta"] and len(_sem_teto(registro["decisoes_contrato"])) == 10
    # e os textos-chave acima do teto da faixa (PR 7) foram mantidos pelo «Aceitar as sugestões», sem troca no texto
    assert {d["resposta"] for d in registro["decisoes_contrato"] if d["tipo"] == fc.TEXTO_TETO} == {fc.ACEITAR}
    gravado = passagem.registrar_decisao(tmp_path, fluxo, novo, DE_ACORDO)
    assert gravado["versao"] == 4

    final = json.loads((tmp_path / "estado.json").read_text(encoding="utf-8"))
    data = registro["quando"].split()[0]
    for chave in ("one_pager", "spec_missao_gate0", "spec_missao"):
        texto = final[chave]
        assert f"90 segundos — PO, parecer de {data}" in texto, chave
        assert f"45 palavras — PO, parecer de {data}" in texto, chave
        assert f"recusada — PO, parecer de {data}: Utilização do componente StoryPoll" in texto, chave
        assert not re.search(r"\[PROPOSTA[^\]]*StoryPoll", texto), chave
    assert not re.search(r"\[(PAR[ÂA]METRO|PROPOSTA)", final["spec_missao_gate0"])
    # sobra no one-pager só a citação do formato
    assert re.findall(r"\[PAR[ÂA]METRO[^\]]*\]", final["one_pager"]) == ["[PARÂMETRO — a definir por produto: …]"]
    # o artefato do one-pager é reescrito, e as decisões ficam no estado (fora de toda lista do refazer)
    assert f"90 segundos — PO, parecer de {data}" in (tmp_path / "produto" / "00-one-pager.md").read_text(encoding="utf-8")
    # e o .html do one-pager, que é o que se lê, sai regerado com as respostas — antes ficava com os [PARÂMETRO]
    assert f"90 segundos — PO, parecer de {data}" in (tmp_path / "produto" / "00-one-pager.html").read_text(encoding="utf-8")
    assert len(_sem_teto(final[fc.KEY_DECISOES])) == 10
    # o design recebe as decisões nas notas de passagem
    notas = passagem.notas_de_passagem(gravado)
    assert "Decisões do PO no contrato de produto" in notas and "StoryPoll" in notas and "**Recusar**" in notas
    # e o rastro da spec deixa de ver pendência do PO
    r = rastro.varrer_lacunas(rastro.FONTES_SPEC, {"spec_missao": final["spec_missao_gate0"]}, etapa_corrente="produto")
    assert not [a for a in r["achados"] if a["tipo"] in ("parametro", "proposta")]


def test_storypoll_recusado_avisa_as_mencoes_que_ficam_no_texto():
    """D12: o de acordo grava a recusa no lugar da proposta; o StoryPoll citado no resto do texto sai por Refazer."""
    estado = _produto_estado()
    story = _por_assunto(fc.itens_em_aberto(estado), "StoryPoll nativo")
    assert fc.mencoes_fora(estado, story)["StoryPoll"] >= 12


# --------------------------------------------------------------------------- D3: o de acordo não sai aberto
def test_tudo_de_acordo_sem_a_lista_nao_aprova_proposta_e_com_estrita_recusa():
    estado = _produto_estado()
    with pytest.raises(DecisaoInvalida, match="sem resposta"):
        aplicar(_fluxo(), DE_ACORDO, PO, COMENTARIO, estado, estrito=True)
    # sem a estrita, o item sem resposta sai — e, desde o PR 9, com a leitura de cada um confirmada no cartão
    with pytest.raises(DecisaoInvalida, match="sem leitura confirmada"):
        aplicar(_fluxo(), DE_ACORDO, PO, COMENTARIO, estado, estrito=False)
    lidos = [i["id"] for i in passagem.itens_de_conferencia(estado)]
    novo, _ = aplicar(_fluxo(), DE_ACORDO, PO, COMENTARIO, estado, estrito=False, leitura=lidos)
    registro = novo["pareceres"][-1]
    assert registro["decisoes_contrato"] == [] and registro["edicoes_contrato"] == []
    assert len(_sem_teto(registro["sem_resposta"])) == 10


def test_resposta_parcial_com_estrita_lista_o_que_falta():
    estado = _produto_estado()
    itens = fc.itens_em_aberto(estado)
    so_um = {itens[0].id: {"resposta": fc.ACEITAR}}
    with pytest.raises(DecisaoInvalida, match=f"{len(itens) - 1} item"):
        aplicar(_fluxo(), DE_ACORDO, PO, COMENTARIO, estado, decisoes=so_um, estrito=True)


def test_excecao_do_admin_sai_com_o_que_ficou_sem_resposta():
    estado = _produto_estado()
    assert EXCECAO in acoes_possiveis(_fluxo(), "admin", estado, estrito=True)
    assert EXCECAO not in acoes_possiveis(_fluxo(), "produto", estado, estrito=True)
    assert EXCECAO not in acoes_possiveis(_fluxo(), "admin", estado, estrito=False)
    lidos = [i["id"] for i in passagem.itens_de_conferencia(estado)]
    novo, _ = aplicar(_fluxo(), EXCECAO, ADMIN, "Libero sem fechar: o PO decide os parâmetros depois.", estado,
                      estrito=True, leitura=lidos)
    registro = novo["pareceres"][-1]
    assert registro["excecao"] and len(_sem_teto(registro["sem_resposta"])) == 10
    assert "item(ns) do contrato de produto sem resposta" in passagem.notas_de_passagem(novo)


@pytest.mark.parametrize("resposta, valor, erro", [
    (fc.DESIGN, "", "só vale para o que é de UI"),
    (fc.OUTRO, "", "escreva o outro valor"),
    (fc.OUTRO, "60 s] e mais", "colchetes"),
])
def test_resposta_que_nao_cabe_no_item_e_recusada(resposta, valor, erro):
    estado = _produto_estado()
    item = fc.itens_em_aberto(estado)[0]
    with pytest.raises(DecisaoInvalida, match=re.escape(erro)):
        aplicar(_fluxo(), DE_ACORDO, PO, COMENTARIO, estado,
                decisoes={item.id: {"resposta": resposta, "valor": valor}}, estrito=False)


def test_outro_valor_e_deixar_para_o_design_entram_no_texto():
    estado = _estado("exp03em1b-b2e7b4a3")
    itens = fc.itens_em_aberto(estado)
    lupa, aba = _por_assunto(itens, "lupa/zoom"), _por_assunto(itens, "Santos Dumont")
    d = fc.decidir(itens, {lupa.id: {"resposta": fc.DESIGN}, aba.id: {"resposta": fc.OUTRO, "valor": "Sem 3ª aba"}},
                   "24/10/2026 09:00:00", "produto")
    novos, falhas = fc.aplicar_edicoes(estado, d.edicoes)
    assert not falhas
    spec = novos["spec_missao_gate0"]
    assert "Sem 3ª aba — PO, parecer de 24/10/2026 (no lugar da proposta: Abertura automática" in spec
    assert "[ABERTO — dono: design: Inclusão de um botão opcional de lupa/zoom" in spec
    # o item deixado para o design é do design fechar: bloqueia o rastro de design até o D0 decidi-lo
    r = rastro.varrer_lacunas(rastro.FONTES_SPEC, {"spec_missao": spec}, etapa_corrente="design")
    deixado = [a for a in r["achados"] if "deixado para o design" in a["trecho"]]
    assert deixado and deixado[0]["etapa"] == "design" and deixado[0]["severidade"] == "bloqueio"


# --------------------------------------------------------------------------- sobrevive ao refazer
def test_decisao_sobrevive_ao_refazer_de_produto(tmp_path):
    from pipeline.reexecucao import preparar_estado

    estado = _produto_estado()
    itens = fc.itens_em_aberto(estado)
    fluxo = _fluxo()
    novo, _ = aplicar(fluxo, DE_ACORDO, PO, COMENTARIO, estado, decisoes=fc.aceitar_sugestoes(itens), estrito=True)
    (tmp_path / "estado.json").write_text(json.dumps(estado, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "conversa.json").write_text(json.dumps({"fluxo": fluxo}, ensure_ascii=False), encoding="utf-8")
    passagem.registrar_decisao(tmp_path, fluxo, novo, DE_ACORDO)
    gravado = json.loads((tmp_path / "estado.json").read_text(encoding="utf-8"))

    # o PO pede refazer de produto: o de acordo é invalidado, mas as decisões seguem nas notas e no estado
    devolvido = {**novo, "etapa": "produto", "situacao": AGUARDANDO}
    refeito, _ = aplicar(devolvido, REFAZER, PO, "Refazer a seção 4 com o texto novo do PO.", gravado, estrito=True)
    assert not refeito["pareceres"][-2]["valido"]
    assert "Decisões do PO no contrato de produto" in passagem.notas_de_passagem(refeito)
    limpo, _ = preparar_estado(gravado, "produto", "pedido")
    assert len(_sem_teto(limpo[fc.KEY_DECISOES])) == 10 and "90 segundos — PO" in limpo["anterior_one_pager"]

    # o autor reescreve o one-pager e reabre o marcador: volta ao cartão já respondido
    reaberto = {**gravado, "one_pager": estado["one_pager"]}
    itens2 = fc.itens_em_aberto(reaberto)
    anteriores = fc.respostas_anteriores(reaberto, refeito, itens2)
    tempo = _por_assunto(itens2, "tempo de inatividade no chat")
    # o marcador reaberto no one-pager não traz sugestão: volta o valor que o PO aceitou
    assert (anteriores[tempo.id]["resposta"], anteriores[tempo.id]["valor"]) == (fc.OUTRO, "90 segundos")
    assert not fc.decisoes_perdidas(reaberto, itens2)

    # o autor reescreve a linha sem o valor e sem o marcador: a decisão perdida aparece no cartão
    data = novo["pareceres"][-1]["quando"].split()[0]
    sumiu = {**gravado}
    for chave in ("one_pager", "spec_missao_gate0", "spec_missao"):
        sumiu[chave] = gravado[chave].replace(f"90 segundos — PO, parecer de {data}", "um tempo de inatividade")
    perdidas = fc.decisoes_perdidas(sumiu, fc.itens_em_aberto(sumiu))
    assert [d["assunto"] for d in perdidas] == ["tempo de inatividade no chat"]

    # com ESTEIRA_ESTRITA, o de acordo não sai com a decisão fora do texto: o design não a aplica, e ela sumiria
    refeito = passagem.concluir_execucao(refeito, True)
    with pytest.raises(DecisaoInvalida, match="não está\\(ão\\) mais no one-pager"):
        aplicar(refeito, DE_ACORDO, PO, COMENTARIO, sumiu, estrito=True)
    assert EXCECAO in acoes_possiveis(refeito, "admin", sumiu, estrito=True)
    # sem a estrita, sai — e as notas dizem que a decisão não está no texto, em vez de «já está gravada»
    liberado, _ = aplicar(refeito, DE_ACORDO, PO, COMENTARIO, sumiu, estrito=False)
    registro = liberado["pareceres"][-1]
    assert [d["assunto"] for d in registro["decisoes_fora_do_texto"]] == ["tempo de inatividade no chat"]
    notas = passagem.notas_de_passagem(liberado)
    linha = next(l for l in notas.splitlines() if "tempo de inatividade no chat" in l)
    assert "não está no texto: vale a decisão" in linha
    assert sum("não está no texto: vale a decisão" in l for l in notas.splitlines()) == 1
    # com a decisão de volta ao texto, a marca sai das notas
    de_volta, _ = aplicar(refeito, DE_ACORDO, PO, COMENTARIO, gravado, estrito=True)
    assert "não está no texto" not in passagem.notas_de_passagem(de_volta)


def test_lint_de_numero_sem_origem_aceita_so_o_numero_que_o_po_decidiu():
    """Sem isto, o refazer de produto reabria o número decidido: o lint chamava «90 segundos — PO, parecer de …» de
    número sem origem, e o revisor o trocava de volta por [PARÂMETRO]. Mas a marca sozinha não é origem: um autor que
    escreve «60 segundos — PO, parecer de …» sem o PO ter decidido 60 é pego."""
    estado = _produto_estado()
    itens = fc.itens_em_aberto(estado)
    d = fc.decidir(itens, fc.aceitar_sugestoes(itens), "24/10/2026 09:00:00", "produto")
    novos, falhas = fc.aplicar_edicoes(estado, d.edicoes)
    assert not falhas
    one_pager = novos["one_pager"]
    assert "90 segundos — PO, parecer de 24/10/2026" in one_pager

    def sem_origem(texto, decisoes):
        r = contrato_produto.validar_one_pager(texto, nucleo=estado.get("nucleo_narrativo", ""),
                                               decisoes_do_po=decisoes)
        return " ".join(a["resumo"] for a in r["achados"] if a["codigo"] == "numero-sem-origem")

    assert "90 segundos" in sem_origem(one_pager, [])  # sem a decisão gravada, o número não tem origem
    assert "90 segundos" not in sem_origem(one_pager, d.decisoes)
    inventado = one_pager.replace("90 segundos — PO, parecer de", "60 segundos — PO, parecer de")
    assert "60 segundos" in sem_origem(inventado, d.decisoes)
    # a proposta recusada não dá origem ao número dela
    recusa = [{**x, "resposta": fc.RECUSAR} for x in d.decisoes]
    assert "90 segundos" in sem_origem(one_pager, recusa)
    assert not contrato_produto._tem_marcador("Após 90 segundos — PO, parecer de 24/10/2026, exibe o nudge.")


# --------------------------------------------------------------------------- mudança do design no Gate 0
def test_mudanca_do_design_no_gate0_aceita_na_devolucao_entra_no_texto():
    """A mudança que o D0 quis fazer no Gate 0 (PR 2) volta a produto pela devolução, e o «aceitar» a põe no texto:
    o D0 refeito sobre a spec nova não acusa mais nada. Recusada, nada muda."""
    import test_perdas_silenciosas as t

    trocada = t.GATE0.replace("Linha 3 da identificação", "Linha três da identificação")
    st = t._rodar({"spec_missao": t.GATE0, "fechamento_lacunas": t._saida_d0(trocada + "\n" + t.BLOCO13)},
                  t._splits(True)[0])
    itens = [i for i in fc.itens_em_aberto(st) if i.tipo == fc.MUDANCA_GATE0]
    assert len(itens) == 1 and itens[0].assunto == "D0 quis mudar o bloco 0 da spec do Gate 0"
    assert itens[0].opcoes() == [fc.ACEITAR, fc.RECUSAR]
    recusa = fc.decidir(itens, {itens[0].id: {"resposta": fc.RECUSAR}}, "24/10/2026 09:00:00", "produto")
    assert recusa.edicoes == [] and recusa.decisoes[0]["gravado"] == "mudança recusada"
    d = fc.decidir(itens, {itens[0].id: {"resposta": fc.ACEITAR}}, "24/10/2026 09:00:00", "produto")
    novos, falhas = fc.aplicar_edicoes(st, d.edicoes)
    assert not falhas
    assert "Linha três da identificação" in novos["spec_missao"] and "Linha 3 da identificação" not in novos["spec_missao"]
    # PR 6: o bloco 13 mora no anexo de design, e a spec de produto é a única cópia do texto a trocar
    assert "## 13. Decisões D0" not in novos["spec_missao"] and "## 13. Decisões D0" in st["anexo_design_spec"]
    de_novo = t._rodar({"spec_missao": novos["spec_missao"],
                        "fechamento_lacunas": t._saida_d0(trocada + "\n" + t.BLOCO13)}, t._splits(True)[0])
    assert "alterou-fora-do-proprio-bloco" not in t._achados(de_novo) and de_novo["lacunas_status"] == "aprovado"


@pytest.mark.parametrize("missao", ["exp01em1b-76d9af6e", "exp06ef1b-53e011b6"])
def test_mudancas_reais_do_d0_e_do_d9_se_aplicam_inteiras(missao):
    """As mudanças que o D0 e o D9 gravados fizeram no Gate 0 (5 blocos na 76d9af6e, 2 na 53e011b6) se aplicam por
    código; a mesma troca trazida pelos dois é um item só."""
    import test_perdas_silenciosas as t

    st = t._remontar(t._estado(missao), estrito=True)
    itens = [i for i in fc.itens_em_aberto(st) if i.tipo == fc.MUDANCA_GATE0]
    assert len(itens) == {"exp01em1b-76d9af6e": 5, "exp06ef1b-53e011b6": 2}[missao]
    d = fc.decidir(itens, {i.id: {"resposta": fc.ACEITAR} for i in itens}, "24/10/2026 09:00:00", "produto")
    _, falhas = fc.aplicar_edicoes(st, d.edicoes)
    assert not falhas


# --------------------------------------------------------------------------- rastro e padrões
def test_rastro_conta_marcador_aberto_como_pendencia_do_po():
    texto = ("- Teto: `[PARÂMETRO — a definir por produto: teto de palavras, sugestão: 45 palavras]`.\n"
             "| PQ-01 | Qual a proporção…? | `[PROPOSTA — validar com PO]` |\n"
             "- L2 — Aplicação do marcador `[PARÂMETRO — a definir por produto: …]`.\n"
             "- Os marcadores [PARÂMETRO] e [PROPOSTA] saem do de acordo.\n"
             "- Quatro propostas registradas com marcador normativo `[PROPOSTA P0b — validar com PO]`.\n")
    r = rastro.varrer_lacunas(rastro.FONTES_SPEC, {"spec_missao": texto}, etapa_corrente="produto")
    tipos = sorted(a["tipo"] for a in r["achados"])
    assert tipos == ["parametro", "proposta"], r["achados"]
    assert {a["etapa"] for a in r["achados"]} == {"humano"} and r["status"] == "amarelo"
    assert {a["severidade"] for a in r["achados"]} == {"decisao_humana"}


def test_padroes_aplicados_sao_padrao_a_confirmar_enquanto_o_arquivo_for_rascunho(tmp_path):
    estado = _estado("exp03em1b-b2e7b4a3")
    padroes = fc.padroes_aplicados(estado, "design")
    nomes = [p["nome"] for p in padroes]
    assert "erro-na-voz-da-ficcao" in nomes and "conclusao-congela" in nomes
    assert not fc.defaults_validados() and {p["rotulo"] for p in padroes} == {"padrão a confirmar"}
    assert next(p for p in padroes if p["nome"] == "conclusao-congela")["amarelo"]
    assert fc.padroes_aplicados(estado, "produto") == []
    # validado o arquivo, o rótulo muda sozinho — sem aceite item a item
    ref = tmp_path / "prompts" / "references"
    ref.mkdir(parents=True)
    ref.joinpath("defaults-missao.md").write_text(
        "---\nstatus: validado com produto em 30/10/2026\n---\n| `erro-na-voz-da-ficcao` | x | y |\n", encoding="utf-8")
    assert fc.defaults_validados(tmp_path)
    assert fc.padroes_aplicados(estado, "design", tmp_path) == [
        {"nome": "erro-na-voz-da-ficcao", "amarelo": False, "rotulo": "padrão aplicado"}]


def test_conflito_de_versao_desfaz_a_gravacao(tmp_path):
    estado = _produto_estado()
    itens = fc.itens_em_aberto(estado)
    fluxo = _fluxo()
    novo, _ = aplicar(fluxo, DE_ACORDO, PO, COMENTARIO, estado, decisoes=fc.aceitar_sugestoes(itens), estrito=True)
    original = json.dumps(estado, ensure_ascii=False)
    (tmp_path / "estado.json").write_text(original, encoding="utf-8")
    # outra pessoa decidiu antes: o fluxo em disco está na versão 9
    (tmp_path / "conversa.json").write_text(json.dumps({"fluxo": {**fluxo, "versao": 9}}), encoding="utf-8")
    # o one-pager em disco existia; a spec do Gate 0 não
    (tmp_path / "produto").mkdir()
    (tmp_path / "produto" / "00-one-pager.md").write_text(estado["one_pager"], encoding="utf-8")
    with pytest.raises(passagem.ConflitoDeVersao):
        passagem.registrar_decisao(tmp_path, fluxo, novo, DE_ACORDO)
    assert (tmp_path / "estado.json").read_text(encoding="utf-8") == original
    # os .md reescritos voltam também: antes ficavam com a decisão que o conflito desfez
    assert (tmp_path / "produto" / "00-one-pager.md").read_text(encoding="utf-8") == estado["one_pager"]
    assert not (tmp_path / "produto" / "05a-spec-missao-gate0.md").exists()
    assert not (tmp_path / "produto" / "00-one-pager.html").exists()


# --------------------------------------------------------------------------- o cartão no app
def test_cartao_do_app_mostra_a_lista_preenchida_e_aceita_as_sugestoes():
    pytest.importorskip("streamlit.testing.v1")
    from streamlit.testing.v1 import AppTest

    def roteiro():
        import json
        from pathlib import Path

        import streamlit as st

        import app
        estado = json.loads(Path("tests/acervo/exp02em1b-60cfa7f4/estado.json").read_text(encoding="utf-8"))
        fluxo = {"etapa": "produto", "situacao": "aguardando_parecer", "versao": 3, "pareceres": [
            {"etapa": "produto", "acao": "de_acordo", "como": "produto", "quando": "21/10/2026 15:43:51",
             "valido": False, "comentario": "[PARÂMETRO: a definir por produto: tempo de inatividade no chat] → 90s"}]}
        st.session_state["_respostas"] = app._render_contrato_aberto(Path("/tmp/sessao-teste"), fluxo, estado)

    # os textos-chave acima do teto (PR 7) entram na mesma lista, com «manter o texto aprovado» como sugestão
    teto = len(fc.textos_acima_do_teto(_estado()))
    at = AppTest.from_function(roteiro, default_timeout=60)
    at.run()
    assert not at.exception and len(at.radio) == 10 + teto
    respostas = at.session_state["_respostas"]
    assert sorted(r["resposta"] for r in respostas.values()) == [""] * (9 + teto) + [fc.ACEITAR]
    at.button[0].click().run()
    respostas = at.session_state["_respostas"]
    assert all(r["resposta"] == fc.ACEITAR for r in respostas.values())
    assert sum(1 for r in respostas.values() if r["origem"] == "aceitar as sugestões") == 9 + teto
