"""PR 6 do plano «Produto dono do contrato» (docs/planos/2026-10-23-produto-dono-do-contrato.md): o D0 dividido por dono e
a spec de produto imutável depois do de acordo (decisões D2, D6 e D10).

- o que o D0 fechava no design e é de produto fecha em produto, no passo de completude da spec (prompt 046), que emite só
  o bloco 15 — o código o monta na spec do A045, e o que é do PO cai na lista do de acordo do PR 3;
- o D0 fica só com UI/UX (gesto, scaffolding, acessibilidade de componente, dispositivo) e grava, com o D9, num anexo de
  design (`anexo_design_spec`): a `spec_missao` não muda no design, e o refazer de design não a volta ao Gate 0;
- design, dev, montagem e rastro leem a spec de produto mais o anexo (`tools.anexo_design.spec_consolidada`), e a sessão
  anterior ao PR 6, com os blocos 13 e 14 dentro da spec, continua lida como antes.

Tudo determinístico, sem modelo.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

import pytest
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.loop_agent import LoopAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.events import Event, EventActions
from google.genai import types
from typing_extensions import override

import test_perdas_silenciosas as t
from agents.callbacks import manter_completude_entre_rodadas
from agents.produto import get_completude_spec_agent, get_completude_spec_split
from tools import anexo_design as ad
from tools import fechar_contrato as fc
from tools import montagem
from tools import rastro

# --------------------------------------------------------------------------- a resposta do passo de completude
SPEC_A045 = ("# Spec — exp99 v1\n\n**2EF · unoogaleria**\n\n## 0. Identificação de plataforma\n"
             + "".join(f"- Linha {i} da identificação da plataforma, com slug e seção do DS.\n" for i in range(30))
             + "\n## 2. Mecanismo por etapa\n- Estado de espera da professora: `[ABERTO — dono: produto: tela de espera "
               "sem descrição]`\n- Inatividade: `[PARÂMETRO — a definir por produto: tempo de inatividade no chat, "
               "sugestão: 90 segundos]`\n"
             + "\n## 12. Decisões fechadas neste gate\n- nenhuma\n\n## Glossário canônico\n| Ação | Rótulo |\n|---|---|\n"
               "| Confirmar | `Publicar` |\n")
BLOCO15 = ("## 15. Completude de produto\n\n### Decisões [CP-n]\n\n### [CP-1] 2.estado_espera — Tela de espera\n"
           "- **Decisão:** a tela congela enquanto a professora fala, sem affordance de avanço.\n"
           "- **Base:** padrão `espera-de-professor`.\n\n"
           "### Padrões da plataforma aplicados\n- `espera-de-professor` — bloco 2\n"
           "- `retencao-lacuna-assumida` — bloco 9\n\n"
           "### Para o PO decidir no de acordo\n- 8.painel: `[PROPOSTA — validar com PO: o painel mostra a proporção de "
           "duplas que trocaram a intenção · por quê: é a medida da virada · alternativa: só a contagem]`\n\n"
           "### Mapa célula → decisão\n\n| Marcador da spec | Decisão |\n|---|---|\n"
           "| `[ABERTO — dono: produto: tela de espera sem descrição]` | [CP-1] |\n")


def _saida(bloco: str = BLOCO15, decisoes=None, passo3: str = "", status: str = "segue_com_pendencias") -> str:
    env = {"agente": "completude-spec", "status": status, "decisoes": decisoes if decisoes is not None else [
        {"id": "CP-1", "campo": "2.estado_espera", "classe": "estado", "cor": "verde", "base": "padrao"}]}
    return ("# Completude da spec — exp99\n\n**Veredito: 🟡 COMPLETA COM 1 DECISÃO DO PO NO DE ACORDO**\n\n"
            "## Passo 1 — Varredura\n\n...\n\n## Passo 2 — Lacunas classificadas\n\n...\n\n"
            "## Passo 3 — Decisões [CP-n]\n\n" + (passo3 or "### [CP-1] 2.estado_espera — Tela de espera\n"
                                                 "Decisão: a tela congela.\nBase: padrão: espera-de-professor.\n")
            + "\n## Passo 4 — Bloco 15\n\n" + bloco + "\n## Passo 5 — Relatório de completude\n\n"
            "### [CP-1] Tela de espera\n**O que faltava:** o que a criança vê enquanto a professora fala.\n\n"
            "## Passo 6 — Testes 1–6 — resultado\n\nok\n\n```json\n" + json.dumps(env, ensure_ascii=False) + "\n```\n")


def _completude(estado: Dict[str, Any]) -> Dict[str, Any]:
    return t._rodar(estado, get_completude_spec_split())


def _achados(st: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return t._achados(st, "completude_status_envelope")


# --------------------------------------------------------------------------- 1. o bloco 15, montado em código
def test_completude_monta_o_bloco_15_sem_tocar_a_spec_do_a045():
    st = _completude({"spec_missao": SPEC_A045, "completude_spec": _saida()})
    spec = st["spec_missao"]
    assert spec.startswith(SPEC_A045.rstrip()) and spec.count("## 15. Completude de produto") == 1
    assert st["relatorio_completude"].startswith("### [CP-1]") and "Passo 6" not in st["relatorio_completude"]
    # «segue_com_pendencias»: a pergunta ao PO vai ao de acordo, e a etapa não sai verde
    assert st["completude_status"] == "amarelo", _achados(st)


def test_completude_que_reescreve_a_spec_tem_a_mudanca_descartada():
    """O passo emite só o bloco 15: a linha do A045 que ele quis mudar fica como estava, com atenção — em produto não há PO
    a consultar sobre o próprio texto, e a mudança vai como proposta no bloco 15."""
    trocada = SPEC_A045.replace("Linha 3 da identificação", "Linha três da identificação")
    st = _completude({"spec_missao": SPEC_A045, "completude_spec": _saida(trocada + "\n" + BLOCO15)})
    assert "Linha 3 da identificação" in st["spec_missao"] and "Linha três" not in st["spec_missao"]
    fora = _achados(st)["alterou-fora-do-proprio-bloco"]
    assert fora["severidade"] == "atencao" and fora["etapa"] == "produto" and not fora.get("aberto_dono_po")


def test_mutante_apagar_bloco_15_na_resposta_da_completude():
    """Mutante «apagar bloco 15»: sem o bloco a spec fica como o A045 a escreveu, e o achado é bloqueio de produto."""
    st = _completude({"spec_missao": SPEC_A045, "completude_spec": _saida("Nada a completar.\n")})
    assert st["spec_missao"] == SPEC_A045 and st["completude_status"] == "bloqueado"
    ausente = _achados(st)["bloco-proprio-ausente"]
    assert ausente["etapa"] == "produto"


def test_completude_de_novo_troca_o_bloco_15_no_lugar():
    novo = BLOCO15.replace("sem affordance de avanço", "sem affordance de avanço nem de voltar")
    st = _completude({"spec_missao": SPEC_A045 + "\n" + BLOCO15, "completude_spec": _saida(novo)})
    assert st["spec_missao"].count("## 15.") == 1 and "nem de voltar" in st["spec_missao"]


def test_completude_que_fecha_parametro_sem_parecer_volta_e_a_que_pergunta_passa():
    """O [CP-n] que fecha o [PARÂMETRO] da spec sem parecer datado decide no lugar do PO (o D0-5 da exp02em1b, 90 s): volta.
    O que escreve o marcador com a sugestão é o que se pede; com parecer datado do PO, é atenção para a pessoa conferir."""
    fecha = ("### [CP-2] 3.inatividade_chat — Tempo de inatividade no chat\nDecisão: aviso depois de 90 segundos.\n"
             "Base: {base}\n")
    decisoes = [{"id": "CP-2", "campo": "3.inatividade_chat", "classe": "parametro", "cor": "verde", "base": "inferencia"}]
    st = _completude({"spec_missao": SPEC_A045, "completude_spec": _saida(
        passo3=fecha.format(base="inferência: o padrão de 90 s da plataforma"), decisoes=decisoes)})
    assert st["completude_status"] == "bloqueado" and "[CP-2]" in _achados(st)["decisao-do-po-pelo-agente"]["resumo"]
    # o que o código acusou vai à completude na rodada seguinte do loop dela
    assert "⛔ `decisao-do-po-pelo-agente`" in st["completude_report"]

    pergunta = ("### [CP-2] 3.inatividade_chat — Tempo de inatividade no chat\nDecisão: `[PARÂMETRO — a definir por "
                "produto: tempo de inatividade no chat · sugestão: 90 segundos]`\nBase: inferência\n")
    st = _completude({"spec_missao": SPEC_A045, "completude_spec": _saida(passo3=pergunta, decisoes=decisoes)})
    assert "decisao-do-po-pelo-agente" not in _achados(st)

    notas = "### Produto · Produto · 21/10/2026 15:43:51\n> tempo de inatividade no chat → 90s"
    st = _completude({"spec_missao": SPEC_A045, "notas_de_passagem": notas, "completude_spec": _saida(
        passo3=fecha.format(base="Parecer de Produto (21/10/2026)"), decisoes=decisoes)})
    assert "decisao-do-po-pelo-agente" not in _achados(st) and "decisao-do-po-pelo-parecer" in _achados(st)


def test_correcao_pontual_nao_desfaz_a_troca_do_editor_no_bloco_15():
    """Na correção pontual de produto o editor troca a spec montada; a resposta da completude, travada, é a antiga, e montar
    de novo desfaria a troca. O split não roda."""
    from agents.callbacks import KEY_DOCUMENTOS_TRAVADOS, KEY_MODO_CORRECAO
    from tools import edicao_pontual

    assert "completude_spec" in edicao_pontual.travados("produto") and "completude_spec" in edicao_pontual.travados("spec")
    editada = (SPEC_A045 + "\n" + BLOCO15).replace("sem affordance de avanço", "com o mapa da turma")
    st = _completude({"spec_missao": editada, "completude_spec": _saida(), KEY_MODO_CORRECAO: "pontual",
                      KEY_DOCUMENTOS_TRAVADOS: list(edicao_pontual.travados("produto"))})
    assert st["spec_missao"] == editada and "completude_status" not in st


# --------------------------------------------------------------------------- 2. uma chamada a mais por refazer (D14)
def test_completude_so_roda_de_novo_se_a_spec_perdeu_o_bloco_15():
    class Ctx:
        def __init__(self, state):
            self.state = state

    assert manter_completude_entre_rodadas(Ctx({"spec_missao": SPEC_A045})) is None  # primeira rodada: roda
    editada = (SPEC_A045 + "\n" + BLOCO15).replace("sem affordance de avanço", "com a troca do retrabalho")
    conteudo = manter_completude_entre_rodadas(Ctx({"spec_rodada": 1, "spec_missao": editada, "completude_spec": _saida()}))
    texto = conteudo.parts[0].text
    assert "com a troca do retrabalho" in texto and "sem affordance de avanço" not in texto
    assert "Passo 5 — Relatório" in texto  # o resto da resposta anterior fica
    # o A045 reescreveu a spec inteira sem o bloco 15: a completude roda de novo
    assert manter_completude_entre_rodadas(Ctx({"spec_rodada": 1, "spec_missao": SPEC_A045,
                                                "completude_spec": _saida()})) is None


def test_agente_de_completude_na_segunda_rodada_nao_chama_o_modelo():
    """O agente de verdade, com o callback: na rodada 2 com o bloco 15 na spec ele não chama o modelo (sem chave de API,
    chamar falharia), grava a resposta com o bloco atual, e o split monta o mesmo bloco — a troca do retrabalho fica."""
    editada = (SPEC_A045 + "\n" + BLOCO15).replace("sem affordance de avanço", "com a troca do retrabalho")
    st = t._rodar({"spec_rodada": 1, "spec_missao": editada, "completude_spec": _saida()},
                  get_completude_spec_agent(), get_completude_spec_split())
    assert "com a troca do retrabalho" in st["completude_spec"] and st["spec_missao"].count("## 15.") == 1
    assert "com a troca do retrabalho" in st["spec_missao"]


class _A045(BaseAgent):
    """O autor da spec: na primeira rodada escreve a spec; nas seguintes, o retrabalho por trocas mexe numa linha (e o
    bloco 15 fica), ou — `reescreve` — o autor a reescreve inteira, sem o bloco."""

    reescreve: bool = False

    @override
    async def _run_async_impl(self, ctx):
        atual = str(ctx.session.state.get("spec_missao") or "")
        texto = SPEC_A045 if (self.reescreve or not atual) else atual.replace("Linha 2 ", "Linha dois ")
        yield Event(invocation_id=ctx.invocation_id, author=self.name, actions=EventActions(state_delta={"spec_missao": texto}))


class _Completude(BaseAgent):
    """O passo de completude, contando as chamadas ao modelo. O callback é o de verdade; o `output_key` do LlmAgent é
    imitado: o `Content` devolvido pelo callback vai para `completude_spec`."""

    @override
    async def _run_async_impl(self, ctx):
        n = int(ctx.session.state.get("chamadas_completude") or 0) + 1
        yield Event(invocation_id=ctx.invocation_id, author=self.name,
                    actions=EventActions(state_delta={"completude_spec": _saida(), "chamadas_completude": n}))


def _callback_com_output_key(callback_context):
    conteudo = manter_completude_entre_rodadas(callback_context)
    if conteudo is not None:
        callback_context.state["completude_spec"] = conteudo.parts[0].text
    return conteudo


class _Rodada(BaseAgent):
    @override
    async def _run_async_impl(self, ctx):
        n = int(ctx.session.state.get("spec_rodada") or 0) + 1
        yield Event(invocation_id=ctx.invocation_id, author=self.name, actions=EventActions(state_delta={"spec_rodada": n}))


@pytest.mark.parametrize("reescreve, chamadas", [(False, 1), (True, 2)])
def test_spec_loop_de_duas_rodadas_chama_a_completude_uma_vez(reescreve, chamadas):
    loop = LoopAgent(name="SpecLoop", max_iterations=2, sub_agents=[
        _A045(name="A045", reescreve=reescreve),
        _Completude(name="A045b", before_agent_callback=_callback_com_output_key),
        get_completude_spec_split(),
        _Rodada(name="A059")])
    st = t._rodar({}, loop)
    assert st["chamadas_completude"] == chamadas and st["spec_missao"].count("## 15.") == 1
    if not reescreve:
        assert "Linha dois" in st["spec_missao"], "a troca do retrabalho se perdeu na montagem"


class _CompletudeQueErraUmaVez(BaseAgent):
    """Na primeira chamada decide no lugar do PO (fecha o [PARÂMETRO] de 90 s); na segunda, pergunta."""

    @override
    async def _run_async_impl(self, ctx):
        n = int(ctx.session.state.get("chamadas_completude") or 0) + 1
        decisoes = [{"id": "CP-2", "campo": "3.inatividade_chat", "classe": "parametro", "cor": "verde", "base": "inferencia"}]
        errada = _saida(passo3="### [CP-2] 3.inatividade_chat — Tempo de inatividade no chat\nDecisão: aviso depois de 90 "
                               "segundos.\nBase: inferência\n", decisoes=decisoes)
        yield Event(invocation_id=ctx.invocation_id, author=self.name, actions=EventActions(state_delta={
            "completude_spec": errada if n == 1 else _saida(), "chamadas_completude": n}))


def _loop_da_completude(autor: BaseAgent) -> LoopAgent:
    from agents.checkers import SaidaDeLoopAgent
    from agents.produto import COMPLETUDE_MAX_RODADAS

    return LoopAgent(name="CompletudeLoop", max_iterations=COMPLETUDE_MAX_RODADAS, sub_agents=[
        autor, get_completude_spec_split(),
        SaidaDeLoopAgent(name="A045d", status_keys=["completude_status"], rodada_key="completude_rodada",
                         max_rounds=COMPLETUDE_MAX_RODADAS, aceitos=["aprovado", "amarelo", ""])])


def test_completude_reprovada_pelo_codigo_refaz_so_ela_uma_vez():
    """O 🔴 da completude deixaria produto sem *de acordo* até um refazer inteiro: a segunda rodada é só dela, com o que o
    código acusou — a única chamada além do teto, e só quando ela falha."""
    st = t._rodar({"spec_missao": SPEC_A045},
                  _loop_da_completude(_CompletudeQueErraUmaVez(name="A045b", before_agent_callback=_callback_com_output_key)))
    assert st["chamadas_completude"] == 2 and st["completude_status"] == "amarelo"
    # o relatório é o da última rodada: a que passou
    assert st["completude_report"].rstrip().endswith("Nada a corrigir.")
    assert st["spec_missao"].count("## 15.") == 1 and "aviso depois de 90" not in st["spec_missao"]


def test_completude_que_passa_nao_roda_de_novo_no_loop_dela():
    st = t._rodar({"spec_missao": SPEC_A045},
                  _loop_da_completude(_Completude(name="A045b", before_agent_callback=_callback_com_output_key)))
    assert st["chamadas_completude"] == 1 and st["completude_rodada"] == 1


def test_produto_ganha_exatamente_uma_chamada_de_modelo_no_spec_loop():
    """O teto do D14: uma chamada a mais por refazer de produto. No SpecLoop, o único agente de modelo novo é o A045b."""
    from google.adk.agents.llm_agent import LlmAgent

    from agents.produto import build_produto_stage
    from pipeline.orchestrator import iter_agent_tree

    spec_loop = next(a for _, a in iter_agent_tree(build_produto_stage()) if a.name == "SpecLoop")
    assert [a.name for _, a in iter_agent_tree(spec_loop) if isinstance(a, LlmAgent)] == [
        "A045SpecMissao", "A045bCompletudeSpec", "A049JuizEvidenciaLlm", "A051JuizPerguntas",
        "A057aBancaProdutoNarrativa", "A057bBancaPedagogiaBncc"]


# --------------------------------------------------------------------------- 3. o de acordo lista o que é do PO
def test_pergunta_e_padrao_do_bloco_15_chegam_ao_de_acordo():
    """O que a completude deixa ao PO é item da lista do de acordo (PR 3), sem mecanismo novo; o padrão citado aparece como
    «padrão a confirmar» enquanto `defaults-missao.md` for rascunho (D5), sem aceite por item."""
    st = _completude({"spec_missao": SPEC_A045, "completude_spec": _saida()})
    itens = fc.itens_em_aberto(st)
    painel = next(i for i in itens if "painel mostra a proporção" in i.assunto + i.sugestao)
    assert painel.tipo == fc.PROPOSTA and any(o.documento == fc.DOC_SPEC for o in painel.ocorrencias)
    nomes = {p["nome"]: p["rotulo"] for p in fc.padroes_aplicados(st, "produto")}
    assert nomes.get("espera-de-professor") == "padrão a confirmar"
    d = fc.decidir(itens, fc.aceitar_sugestoes(itens), "24/10/2026 10:00:00", "produto")
    novos, falhas = fc.aplicar_edicoes(st, d.edicoes)
    assert not falhas and "aprovada — PO, parecer de 24/10/2026" in novos["spec_missao"]
    assert "## 15. Completude de produto" in novos["spec_missao"]


# --------------------------------------------------------------------------- 4. o D0 só de UI/UX
def _saida_d0(campo: str, classe: str, decisao: str) -> str:
    env = {"agente": "fecha-lacunas", "status": "segue", "decisoes": [
        {"id": "D0-1", "campo": campo, "classe": classe, "cor": "verde", "base": "inferencia"}]}
    return t._saida_d0(t.BLOCO13, envelope=env).replace(
        "### [D0-1] 4.gesto_arrastar\nDecisão: demonstração no primeiro uso.", f"### [D0-1] {campo}\nDecisão: {decisao}")


@pytest.mark.parametrize("campo, classe, decisao, barra", [
    # o revezamento de 4 operadores da exp03em1b (D0-8) veio com classe de dispositivo
    ("10.cenario_2_4", "dispositivo", "revezamento de papéis com 2 a 4 operadores por aparelho.", True),
    # a retenção por ano letivo da exp02ef1b (D0-8)
    ("9.retencao_e_acesso", "dados", "os dados ficam guardados por um ano letivo.", True),
    ("8.painel_docente", "acessibilidade", "o painel mostra 6 métricas por dupla.", True),
    ("10.cenario_projecao", "dispositivo", "na projeção a tela usa 1366×768 e alvos de 88×88.", False),
    ("7.contraste", "acessibilidade", "nenhum estado comunicado só por cor.", False),
])
def test_d0_ux_barra_tema_de_produto_mesmo_com_classe_de_ui(campo, classe, decisao, barra):
    st = t._rodar({"spec_missao": t.GATE0, "fechamento_lacunas": _saida_d0(campo, classe, decisao)}, t._splits()[0])
    assert ("decisao-de-produto-pelo-agente" in t._achados(st)) is barra, t._achados(st)
    assert st["spec_missao"] == t.GATE0


def test_mutante_d0_que_escreve_na_spec_de_produto_nao_entra():
    """Mutante «o D0 escreve no bloco 15»: o texto de produto que o design quis mudar — inclusive o bloco 15 — não entra na
    spec nem no anexo, e vira `[ABERTO — dono: PO]` no cartão do parecer de design."""
    spec = t.GATE0 + "\n" + BLOCO15
    mudada = spec.replace("sem affordance de avanço", "com botão de voltar")
    st = t._rodar({"spec_missao": spec, "fechamento_lacunas": t._saida_d0(mudada + "\n" + t.BLOCO13)}, t._splits()[0])
    assert st["spec_missao"] == spec and "com botão de voltar" not in st["anexo_design_spec"]
    aberto = t._achados(st)["alterou-fora-do-proprio-bloco"]
    assert aberto["aberto_dono_po"] and "bloco 15" in aberto["resumo"]


def test_d9_sem_o_bloco_14_nao_troca_o_anexo_pela_copia_do_13():
    """O D9 que recopia o bloco 13 (mudado) e esquece o 14: montado, o anexo seria a cópia dele do 13. Fica como estava."""
    anexo = ad.montar_anexo(t.BLOCO13)
    copia = (t.GATE0 + "\n" + t.BLOCO13).replace("mostra a demonstração", "esconde a demonstração")
    d9 = ("# Ambiente simulado\n\n## Passo 4 — Spec consolidada\n\n" + copia
          + "\n## Bloco 14 — Ficha do ambiente\nnome: Unoogaleria\n\n```json\n"
          + json.dumps({"agente": "ambiente-simulado", "status": "dormente"}) + "\n```\n")
    st = t._rodar({"spec_missao": t.GATE0, ad.KEY_ANEXO: anexo, "ambiente_simulado": d9}, t._splits()[1])
    assert st[ad.KEY_ANEXO] == anexo and st["spec_missao"] == t.GATE0


# --------------------------------------------------------------------------- 5. quem lê: rastro e montagem
def test_rastro_le_o_mapa_do_bloco_15_e_cobra_cp_orfao():
    st = _completude({"spec_missao": SPEC_A045, "completude_spec": _saida()})
    r = rastro.varrer_lacunas(rastro.FONTES_SPEC, st, etapa_corrente="produto")
    assert [x["d0"] for x in r["resolvidos"]] == ["CP-1"], r["achados"]
    assert not any("tela de espera sem descrição" in a["trecho"] for a in r["achados"])
    # mutante «apagar bloco 15»: o mapa some com o bloco, a lacuna volta a ser cobrada e a citação fica órfã
    sem15 = {**st, "spec_missao": SPEC_A045, "jornada_telas": "- A tela de espera segue o [CP-1].\n"}
    r = rastro.varrer_lacunas(rastro.FONTES_DESIGN, sem15, etapa_corrente="design")
    assert any("tela de espera sem descrição" in a["trecho"] for a in r["achados"])
    orfao = next(a for a in r["achados"] if a.get("codigo") == "cp-orfao")
    assert orfao["trecho"] == "CP-1" and orfao["severidade"] == "bloqueio"


def test_rastro_de_design_le_o_anexo():
    assert any(f["chave"] == ad.KEY_ANEXO for f in rastro.FONTES_DESIGN)
    anexo = ad.montar_anexo(t.BLOCO13 + "\n- `[ABERTO — dono: PO: revezamento no cenário 2–4 — sugestão: o padrão]`\n")
    r = rastro.varrer_lacunas(rastro.FONTES_DESIGN, {"spec_missao": t.GATE0, ad.KEY_ANEXO: anexo}, etapa_corrente="design")
    pendente = next(a for a in r["achados"] if "revezamento no cenário" in a["trecho"])
    assert pendente["documento"] == "anexo de design da spec" and pendente["severidade"] == "decisao_humana"


def test_montagem_le_o_bloco_13_do_anexo_com_a_regua_da_epoca():
    """A linha do bloco 13 entra no contrato da montagem se a decisão passa pela lista do D0 da época: na missão anterior
    ao PR 6 (blocos dentro da spec), `duracao` era do design; na nova (com anexo), é de produto e não conta."""
    bloco = "## 13. Decisões D0\n\n- [D0-1] 3.inatividade — aviso depois de 37 segundos.\n"
    fech = ('## Passo 3 — Decisões\n\n### [D0-1] 3.inatividade\nDecisão: aviso depois de 37 segundos.\nBase: inferência.\n'
            '\n## Passo 4\n')
    env = {"decisoes": [{"id": "D0-1", "campo": "3.inatividade", "classe": "duracao", "cor": "verde"}]}
    legado = {"spec_missao": t.GATE0 + "\n" + bloco, "fechamento_lacunas": fech, "lacunas_status_envelope": env}
    novo = {"spec_missao": t.GATE0, ad.KEY_ANEXO: ad.montar_anexo(bloco), "fechamento_lacunas": fech,
            "lacunas_status_envelope": env}
    assert "37 segundos" in montagem.bloco_13_da_lista_branca(legado)[0]
    texto, de_produto = montagem.bloco_13_da_lista_branca(novo)
    assert "37 segundos" not in texto and de_produto == ["D0-1"]


# --------------------------------------------------------------------------- 6. o anexo e a sessão antiga
def test_spec_consolidada_soma_o_anexo_e_le_a_sessao_antiga_como_esta():
    anexo = ad.montar_anexo(t.BLOCO14 + "\n" + t.BLOCO13)
    assert ad.blocos_do_anexo(anexo).index("## 13.") < ad.blocos_do_anexo(anexo).index("## 14.")
    nova = ad.spec_consolidada({"spec_missao": t.GATE0, ad.KEY_ANEXO: anexo})
    assert nova.startswith(t.GATE0.rstrip()) and "## 13." in nova and "## 14." in nova and "# Anexo" not in nova
    antiga = t.GATE0 + "\n" + t.BLOCO13 + "\n" + t.BLOCO14
    assert ad.spec_consolidada({"spec_missao": antiga}) == antiga
    assert ad.spec_de_produto_legada({"spec_missao": t.GATE0}) is None
    assert ad.spec_de_produto_legada({"spec_missao": antiga, "spec_missao_gate0": t.GATE0}) == t.GATE0
    assert ad.spec_de_produto_legada({"spec_missao": antiga}).strip() == t.GATE0.strip()


@pytest.mark.parametrize("missao", t.CINCO)
def test_refazer_de_design_das_sessoes_antigas_volta_a_spec_de_produto_e_monta_o_anexo(missao):
    """As missões que o usuário vai refazer (exp02ef1b, exp02em1b, exp01em1b, exp03em1b) e a exp06ef1b: o refazer de
    design devolve a spec de produto uma vez, e o D0 e o D9 gravados montam o anexo sem tocar nela."""
    from pipeline.reexecucao import preparar_estado

    estado = t._estado(missao)
    limpo, _ = preparar_estado(estado, "design")
    assert limpo["spec_missao"] == estado["spec_missao_gate0"] and not ad.tem_blocos_do_design(limpo["spec_missao"])
    limpo.update({k: estado[k] for k in ("fechamento_lacunas", "ambiente_simulado") if estado.get(k)})
    st = t._rodar(limpo, *t._splits())
    assert st["spec_missao"] == estado["spec_missao_gate0"]
    assert "## 13." in st[ad.KEY_ANEXO] and "## 14." in st[ad.KEY_ANEXO]
    # refazer de novo, agora com o anexo: no-op na spec
    de_novo, _ = preparar_estado(st, "design")
    assert de_novo["spec_missao"] == st["spec_missao"] and ad.KEY_ANEXO not in de_novo


# --------------------------------------------------------------------------- 5. o CompletudeLoop dentro do SpecLoop
# Revisão do PR #73 (24/10/2026): o LoopAgent do ADK encerra no primeiro `escalate` de qualquer subagente, e o
# CompletudeLoop, posto direto no SpecLoop, encerrava o SpecLoop logo depois da completude — sem BNCC, gates, banca e A059,
# e sem segunda rodada. Os testes abaixo usam o SpecLoop de `_build_spec_loop`, com o CompletudeLoop real.
class _Marcador(BaseAgent):
    """Um agente posterior à completude no SpecLoop (o lugar do A046BnccCheck): conta quantas vezes rodou."""

    @override
    async def _run_async_impl(self, ctx):
        n = int(ctx.session.state.get("rodou_depois_da_completude") or 0) + 1
        yield Event(invocation_id=ctx.invocation_id, author=self.name,
                    actions=EventActions(state_delta={"rodou_depois_da_completude": n}))


class _CompletudeQueSempreErra(BaseAgent):
    """Decide no lugar do PO toda vez: o código a reprova sempre."""

    @override
    async def _run_async_impl(self, ctx):
        n = int(ctx.session.state.get("chamadas_completude") or 0) + 1
        decisoes = [{"id": "CP-2", "campo": "3.inatividade_chat", "classe": "parametro", "cor": "verde", "base": "inferencia"}]
        errada = _saida(passo3="### [CP-2] 3.inatividade_chat — Tempo de inatividade no chat\nDecisão: aviso depois de 90 "
                               "segundos.\nBase: inferência\n", decisoes=decisoes)
        yield Event(invocation_id=ctx.invocation_id, author=self.name, actions=EventActions(state_delta={
            "completude_spec": errada, "chamadas_completude": n}))


def _spec_loop_real(monkeypatch, completude: BaseAgent, *, reescreve: bool = False, rodadas: int = 2) -> LoopAgent:
    """O SpecLoop de `_build_spec_loop`, com o elemento da completude como ele o monta (o CompletudeLoop real, isolado),
    só o modelo trocado: o A045 é o falso, a completude conta as chamadas, e os agentes de modelo do resto (juízes, banca)
    dão lugar a um marcador e à saída da rodada."""
    import agents.produto as produto
    from agents.checkers import LoopIsolado
    from config import get_settings

    monkeypatch.setattr(produto, "get_completude_spec_agent", lambda **kw: completude)
    loop = produto._build_spec_loop({}, get_settings(), rodadas)
    assert [a.name for a in loop.sub_agents[:3]] == ["A045SpecMissao", "CompletudeLoopIsolado", "A046BnccCheck"]
    elemento = loop.sub_agents[1]
    assert isinstance(elemento, LoopIsolado) and elemento.sub_agents[0].name == "CompletudeLoop"
    assert elemento.sub_agents[0].sub_agents[0] is completude
    loop.sub_agents = [_A045(name="A045", reescreve=reescreve), elemento, _Marcador(name="A046BnccCheck"),
                       _Rodada(name="A059")]
    return loop


@pytest.mark.parametrize("reescreve, chamadas", [(False, 1), (True, 2)])
def test_spec_loop_real_roda_o_que_vem_depois_da_completude_e_faz_a_segunda_rodada(monkeypatch, reescreve, chamadas):
    loop = _spec_loop_real(monkeypatch, _Completude(name="A045b", before_agent_callback=_callback_com_output_key),
                           reescreve=reescreve)
    st = t._rodar({}, loop)
    assert st["rodou_depois_da_completude"] == 2, "o SpecLoop encerrou na saída da completude"
    assert st["spec_rodada"] == 2 and st["chamadas_completude"] == chamadas
    assert st["spec_missao"].count("## 15.") == 1
    if not reescreve:
        assert "Linha dois" in st["spec_missao"], "a troca do retrabalho se perdeu na montagem"


def test_mutante_completude_loop_sem_isolar_encerra_o_spec_loop():
    """O defeito que o `isolar` conserta: com o CompletudeLoop direto no SpecLoop, o marcador não roda."""
    from agents.produto import _completude_loop

    completude = _completude_loop()
    completude.sub_agents[0] = _Completude(name="A045b", before_agent_callback=_callback_com_output_key)
    loop = LoopAgent(name="SpecLoop", max_iterations=2, sub_agents=[
        _A045(name="A045"), completude, _Marcador(name="A046BnccCheck"), _Rodada(name="A059")])
    st = t._rodar({}, loop)
    assert "rodou_depois_da_completude" not in st and "spec_rodada" not in st


def test_completude_reprovada_sempre_nao_passa_do_teto_nas_rodadas_da_spec(monkeypatch):
    """O LoopIsolado zera `completude_rodada` a cada volta do SpecLoop. Sem a marca de quem chamou o modelo na volta, a
    completude ainda reprovada chamaria o modelo de novo a cada rodada da spec: são 2 chamadas, as da primeira volta."""
    loop = _spec_loop_real(monkeypatch, _CompletudeQueSempreErra(name="A045b",
                                                                 before_agent_callback=_callback_com_output_key),
                           rodadas=3)
    st = t._rodar({}, loop)
    assert st["rodou_depois_da_completude"] == 3 and st["spec_rodada"] == 3
    assert st["chamadas_completude"] == 2 and st["completude_status"] == "bloqueado"


def test_completude_que_erra_uma_vez_no_spec_loop_real(monkeypatch):
    loop = _spec_loop_real(monkeypatch, _CompletudeQueErraUmaVez(name="A045b",
                                                                 before_agent_callback=_callback_com_output_key))
    st = t._rodar({}, loop)
    assert st["rodou_depois_da_completude"] == 2 and st["chamadas_completude"] == 2
    assert st["completude_status"] == "amarelo" and "aviso depois de 90" not in st["spec_missao"]


# --------------------------------------------------------------------------- 6. correção pontual de sessão antiga
def _completude_com_os_callbacks_do_agente_real() -> BaseAgent:
    """A completude que conta as chamadas ao modelo, com a cadeia de callbacks do A045bCompletudeSpec de verdade (travar
    na correção pontual, retrabalho por trocas, herança e `manter_completude_entre_rodadas`), e o `output_key` imitado."""
    import inspect

    cadeia = get_completude_spec_agent().canonical_before_agent_callbacks

    async def _callbacks(callback_context):
        for callback in cadeia:
            conteudo = callback(callback_context=callback_context)
            conteudo = await conteudo if inspect.isawaitable(conteudo) else conteudo
            if conteudo is not None:
                callback_context.state["completude_spec"] = conteudo.parts[0].text
                return conteudo
        return None

    return _Completude(name="A045b", before_agent_callback=_callbacks)


@pytest.mark.parametrize("missao", ["exp02ef1b-4fd72a9a", "exp02em1b-60cfa7f4", "exp03em1b-b2e7b4a3"])
def test_produto_pontual_de_sessao_antiga_nao_roda_a_completude(monkeypatch, missao):
    """A sessão anterior ao PR 6 não tem `completude_spec` para travar. O plano reconduz a exp02ef1b e a exp02em1b por
    produto pontual (D11/D12): a spec sai só com as trocas pedidas — sem bloco 15 nem chamada de modelo."""
    import agents.produto as produto
    from agents.callbacks import COMPLETUDE_PULADA_NA_CORRECAO, KEY_DOCUMENTOS_TRAVADOS
    from agents.checkers import isolar
    from agents.produto import _completude_loop
    from pipeline.artifacts import e_mensagem_de_pulo
    from pipeline.reexecucao import preparar_estado_pontual
    from tools import edicao_pontual

    estado = t._estado(missao)
    assert not str(estado.get("completude_spec") or "").strip()
    docs = edicao_pontual.documentos_da_etapa(estado, "produto")
    spec = docs["spec_missao"]
    linha = next(l for l in spec.splitlines() if len(l.strip()) > 30)
    editada = spec.replace(linha, linha + " (troca do PO)", 1)
    limpo, _ = preparar_estado_pontual(estado, "produto", "Trocar uma linha.", {**docs, "spec_missao": editada},
                                       [{"documento": "spec_missao", "de": linha, "para": linha + " (troca do PO)"}])
    assert "completude_spec" not in limpo[KEY_DOCUMENTOS_TRAVADOS]
    monkeypatch.setattr(produto, "get_completude_spec_agent", lambda **kw: _completude_com_os_callbacks_do_agente_real())
    st = t._rodar(limpo, isolar(_completude_loop()))
    assert "chamadas_completude" not in st, "a completude chamou o modelo na correção pontual"
    assert st["spec_missao"] == editada and "## 15." not in st["spec_missao"]
    assert st["completude_spec"] == COMPLETUDE_PULADA_NA_CORRECAO and e_mensagem_de_pulo(st["completude_spec"])
    assert "completude_status" not in st


def test_produto_pontual_com_completude_mantem_a_resposta_e_nao_monta(monkeypatch):
    """Sessão nova: a resposta fica como está e o split não monta de novo (a troca do editor no bloco 15 fica) — mesmo se
    a lista de travados não a trouxer."""
    import agents.produto as produto
    from agents.callbacks import KEY_DOCUMENTOS_TRAVADOS, KEY_MODO_CORRECAO
    from agents.checkers import isolar
    from agents.produto import _completude_loop

    monkeypatch.setattr(produto, "get_completude_spec_agent", lambda **kw: _completude_com_os_callbacks_do_agente_real())
    editada = (SPEC_A045 + "\n" + BLOCO15).replace("sem affordance de avanço", "com o mapa da turma")
    st = t._rodar({"spec_missao": editada, "completude_spec": _saida(), KEY_MODO_CORRECAO: "pontual",
                   KEY_DOCUMENTOS_TRAVADOS: ["spec_missao"]}, isolar(_completude_loop()))
    assert "chamadas_completude" not in st
    assert st["spec_missao"] == editada and st["completude_spec"] == _saida() and "completude_status" not in st
