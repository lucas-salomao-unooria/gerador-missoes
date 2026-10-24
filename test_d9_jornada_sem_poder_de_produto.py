"""PR 8 do plano «Produto dono do contrato» (docs/planos/2026-10-23-produto-dono-do-contrato.md), decisão D8: o D9 e a
jornada sem poder de produto.

- produto decide a classe do ambiente (app clonado | mini-jogo), o ambiente e, no mini-jogo, as regras e as fases do
  jogo; ambiente novo e mini-jogo são escolha do PO, na lista do de acordo (`tools/ambiente.conferir_spec`,
  `tools/fechar_contrato.escolhas_de_ambiente`);
- o D9 lê o bloco 0 e emite só a ficha de UI do bloco 14: outro ambiente ou outra classe, regra ou fase de jogo, ou texto
  dele fora do bloco 14 bloqueia como decisão de produto; spec calada e troca pedida viram devolução a produto
  (`tools/ambiente.conferir_d9`, no split A068);
- a Seção 5 da jornada copia as regras e as fases da spec e só mapeia as telas: regra ou fase nova vira proposta ao PO
  (`tools/ambiente.conferir_jornada`, no gate das arestas A083b);
- a spec de antes deste PR, sem a linha `classe_ambiente`, é lida pela `secao_ds`, e as quatro missões que vão ser
  refeitas (exp02ef1b, exp02em1b, exp01em1b e exp03em1b) passam.

Mutantes: «D9 cria ambiente novo com a spec calada», «jornada inventa fase 3 do mini-jogo», «bloco 14 troca a
secao_ds». Tudo determinístico, sem modelo, sobre os estados do acervo (`tests/acervo`).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

import test_perdas_silenciosas as t
from agents.design import get_ambiente_simulado_split
from tools import ambiente as amb
from tools import arestas
from tools import fechar_contrato as fc
from tools.anexo_design import KEY_ANEXO, _bloco, montar_anexo
from tools.rastro import validar_manifesto

ACERVO = Path(__file__).resolve().parent / "tests" / "acervo"
#: As quatro missões que o usuário vai refazer depois deste PR, com a seção principal e as extras do bloco 0.
REFAZER = {
    "exp02ef1b-4fd72a9a": ("unoogaleria", []),
    "exp02em1b-60cfa7f4": ("unooriaai", ["unoovista"]),
    "exp01em1b-76d9af6e": ("unooriaai", ["unooria"]),
    "exp03em1b-b2e7b4a3": ("unoochat", []),
}
COM_D9 = sorted(p.name for p in ACERVO.iterdir() if (p / "estado.json").exists()
                and json.loads((p / "estado.json").read_text(encoding="utf-8")).get("ambiente_simulado"))
COM_JORNADA = sorted(p.name for p in ACERVO.iterdir() if (p / "estado.json").exists()
                     and json.loads((p / "estado.json").read_text(encoding="utf-8")).get("jornada_telas"))


def _estado(missao: str) -> Dict[str, Any]:
    return json.loads((ACERVO / missao / "estado.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- specs de teste
def _spec(secao: str = "unoogaleria", classe: Optional[str] = None, serie: str = "2EF", extra: str = "") -> str:
    linhas = [f"- `id: exp0{serie[0]}ef1b`", f"- `series: [\"{serie}\"]`", f"- `secao_ds: {secao}`"] if secao else [
        f"- `id: exp0{serie[0]}ef1b`", f"- `series: [\"{serie}\"]`"]
    if classe:
        linhas.append(f"- `classe_ambiente: {classe}`")
    return ("# Spec — exp99 v1\n\n## 0. Identificação de plataforma\n" + "\n".join(linhas) + "\n" + extra
            + "\n## 2. Mecanismo por etapa\n### Etapa 1 — Desafiar\n- Apresenta o álbum.\n" + REGRAS_E_FASES_SLOT
            + "\n## 4. Verbos e affordances\n- tocar · ordenar\n\n## 12. Decisões fechadas neste gate\n- nenhuma\n")


REGRAS_E_FASES_SLOT = "{regras_e_fases}"
REGRAS_E_FASES = """
### Regras e fases do mini-jogo

**Tipo de jogo:** ordenação — a criança põe as fotos na ordem em que aconteceram.

**Regras do jogo:**
- `R1` Toque na foto que veio primeiro.
- `R2` Arraste a foto até o varal.

| Fase | Nome | Ideia nova | Regra da fase | Verbo do jogo | Como vence | Como perde | Habilidade |
|---|---|---|---|---|---|---|---|
| 1 | Varal da manhã | ordem de duas fotos | Ponha a foto do café antes da escola. | ordenar | duas fotos no lugar | foto fora do lugar volta | `EF02CO05` |
| 2 | Varal da tarde | ordem de três fotos | Ponha as três fotos na ordem do dia. | ordenar | três fotos no lugar | foto fora do lugar volta | `EF02CO05` |

**Como o progresso aparece:** um mapa com dois varais; o feito fica colorido.
"""


def _spec_minijogo(**kw) -> str:
    return _spec("minijogo:varal-do-dia", "mini-jogo", **kw).replace(REGRAS_E_FASES_SLOT, REGRAS_E_FASES)


def _spec_app(secao: str = "unoogaleria", **kw) -> str:
    return _spec(secao, **kw).replace(REGRAS_E_FASES_SLOT, "")


def _codigos(achados) -> list:
    return sorted(a.get("codigo") for a in achados)


# --------------------------------------------------------------------------- 1. produto decide classe e ambiente
@pytest.mark.parametrize("missao", sorted(REFAZER))
def test_as_quatro_missoes_a_refazer_sao_app_clonado_lido_da_secao_ds(missao):
    """Leitura tolerante: a spec de antes do PR 8 não tem `classe_ambiente`, e a classe vem da `secao_ds`."""
    secao, extras = REFAZER[missao]
    estado = _estado(missao)
    d = amb.classe_e_ambiente(str(estado["spec_missao_gate0"]))
    assert (d["secao"], d["extras"], d["classe"], d["declarada"], d["nova"]) == (
        secao, extras, amb.APP_CLONADO, None, False)
    # o manifesto não ganha achado de classe nem de escolha do PO
    r = validar_manifesto(estado["spec_missao_gate0"], briefing=estado.get("briefing") or "",
                          one_pager=estado.get("one_pager") or "", decisoes_do_po=estado.get("decisoes_do_po") or [])
    assert not [a for a in r["achados"] if a.get("codigo")], r["achados"]
    assert r["campos"]["classe_ambiente"] == amb.APP_CLONADO


def test_classe_declarada_que_nao_concorda_com_a_secao_bloqueia_em_produto():
    r = amb.conferir_spec(_spec_app(classe="mini-jogo"), serie="2EF")
    assert _codigos(r) == ["classe-ambiente-divergente"] and r[0]["etapa"] == "produto"
    assert amb.conferir_spec(_spec_app(classe="app-clonado"), serie="2EF") == []


def test_minijogo_so_no_1o_ao_5o_ano():
    """Condição 1 do gate de aplicabilidade, que saiu da Passada 1b do D9 e foi para produto."""
    pr = "\n- Classe: mini-jogo `[PROPOSTA — validar com PO: mini-jogo `minijogo:varal-do-dia` · por quê: ordenar]`\n"
    assert "minijogo-fora-da-faixa" in _codigos(amb.conferir_spec(_spec_minijogo(serie="6EF", extra=pr), serie="6EF"))
    assert _codigos(amb.conferir_spec(_spec_minijogo(extra=pr), serie="2EF")) == ["escolha-de-ambiente-com-o-po"]


def test_minijogo_sem_regras_e_fases_na_spec_bloqueia_e_com_a_pergunta_ao_po_fica_atencao():
    pr = "\n- `[PROPOSTA — validar com PO: mini-jogo `minijogo:varal-do-dia`]`\n"
    sem = _spec("minijogo:varal-do-dia", "mini-jogo", extra=pr).replace(REGRAS_E_FASES_SLOT, "")
    assert "minijogo-sem-regras-e-fases" in _codigos(amb.conferir_spec(sem, serie="2EF"))
    perguntada = sem.replace("- nenhuma", "- `[ABERTO — dono: PO: regras e fases do mini-jogo — quantas fases]`")
    codigos = _codigos(amb.conferir_spec(perguntada, serie="2EF"))
    assert "minijogo-regras-e-fases-com-o-po" in codigos and "minijogo-sem-regras-e-fases" not in codigos
    rf = amb.regras_e_fases(_spec_minijogo())
    assert sorted(rf["fases"]) == [1, 2] and sorted(rf["regras"]) == [1, 2]
    assert rf["fases"][2]["regra"] == "Ponha as três fotos na ordem do dia."


@pytest.mark.parametrize("onde, esperado", [
    ("", "escolha-de-ambiente-sem-o-po"),
    ("- `[PROPOSTA — validar com PO: mini-jogo `minijogo:varal-do-dia` · por quê: verbos de ordenar]`\n",
     "escolha-de-ambiente-com-o-po"),
    ("- Classe: mini-jogo — aprovada — PO, parecer de 24/10/2026: mini-jogo `minijogo:varal-do-dia`\n", None),
    ("- Classe: mini-jogo — recusada — PO, parecer de 24/10/2026: mini-jogo `minijogo:varal-do-dia`\n",
     "escolha-de-ambiente-recusada"),
    # o parâmetro de uma fase do mini-jogo é outra decisão do PO: não responde a escolha da classe
    ("- `[PARÂMETRO — a definir por produto: duração da fase do mini-jogo, sugestão: 90 s]`\n"
     "- Duração do mini-jogo: 90 s — PO, parecer de 24/10/2026\n", "escolha-de-ambiente-sem-o-po"),
])
def test_mini_jogo_e_escolha_do_po_nunca_decidida_em_silencio(onde, esperado):
    r = [a for a in amb.conferir_spec(_spec_minijogo(extra=onde), serie="2EF") if a["campo"] == "secao_ds"]
    assert _codigos(r) == ([esperado] if esperado else []), r
    if esperado in ("escolha-de-ambiente-sem-o-po", "escolha-de-ambiente-recusada"):
        assert r[0]["severidade"] == "bloqueio" and r[0]["etapa"] == "produto"


def test_briefing_ou_one_pager_do_po_que_fixa_o_ambiente_novo_e_decisao_dele():
    spec = _spec_app("nova:pistagrama")
    assert _codigos(amb.conferir_spec(spec, briefing="secao_ds: nova:pistagrama")) == []
    assert _codigos(amb.conferir_spec(spec, one_pager_po="# One-pager\nSeção do DS: `nova:pistagrama`\n")) == []
    assert _codigos(amb.conferir_spec(spec)) == ["escolha-de-ambiente-sem-o-po"]
    assert _codigos(amb.conferir_spec(_spec_minijogo(), briefing="Quero um mini-jogo de ordenar fotos.")) == []
    # a decisão gravada pelo de acordo também vale
    decisao = [{"tipo": fc.ESCOLHA_AMBIENTE, "assunto": "ambiente novo `nova:pistagrama`", "resposta": fc.ACEITAR}]
    assert _codigos(amb.conferir_spec(spec, decisoes_do_po=decisao)) == []


def test_manifesto_leva_o_dono_da_spec_calada_a_produto():
    """A spec sem `secao_ds` era «Dono: design (D9) quando a spec cala»: desde o PR 8 é de produto."""
    r = validar_manifesto(_spec_app("").replace(REGRAS_E_FASES_SLOT, ""))
    secao = [a for a in r["achados"] if a["campo"] == "secao_ds"]
    assert secao and secao[0]["etapa"] == "produto" and "D9" in secao[0]["resumo"]


# --------------------------------------------------------------------------- 2. o de acordo de produto
def test_ambiente_novo_sem_marcador_vira_proposta_no_de_acordo_e_a_resposta_grava():
    spec = _spec_minijogo()
    estado = {"spec_missao": spec, "one_pager": "# One-pager\n"}
    itens = [i for i in fc.itens_em_aberto(estado) if i.tipo == fc.ESCOLHA_AMBIENTE]
    assert len(itens) == 1 and itens[0].opcoes() == [fc.ACEITAR, fc.RECUSAR]
    assert "minijogo:varal-do-dia" in itens[0].assunto and fc.ROTULO_TIPO[fc.ESCOLHA_AMBIENTE].startswith("[PROPOSTA]")
    d = fc.decidir(itens, {itens[0].id: {"resposta": fc.ACEITAR}}, "24/10/2026 09:00:00", "produto")
    novos, falhas = fc.aplicar_edicoes(estado, d.edicoes)
    assert not falhas
    linha = next(l for l in novos["spec_missao"].splitlines() if "secao_ds" in l)
    assert linha.endswith("— aprovada — PO, parecer de 24/10/2026")
    gravado = {**estado, **novos, "decisoes_do_po": d.decisoes}
    # o campo continua legível, a escolha tem dono, e o item não volta
    assert amb.classe_e_ambiente(novos["spec_missao"])["secao"] == "minijogo:varal-do-dia"
    assert amb.escolha_do_po(novos["spec_missao"], decisoes_do_po=d.decisoes) == "aprovada"
    assert not [i for i in fc.itens_em_aberto(gravado) if i.tipo == fc.ESCOLHA_AMBIENTE]
    assert not fc.decisoes_perdidas(gravado, fc.itens_em_aberto(gravado))
    # recusado, a spec que ainda o fixa é bloqueada no manifesto
    r = fc.decidir(itens, {itens[0].id: {"resposta": fc.RECUSAR}}, "24/10/2026 09:00:00", "produto")
    recusada, _ = fc.aplicar_edicoes(estado, r.edicoes)
    assert "escolha-de-ambiente-recusada" in _codigos(amb.conferir_spec(recusada["spec_missao"], serie="2EF"))


def test_com_o_marcador_escrito_o_item_e_o_do_marcador_e_app_clonado_nao_tem_item():
    pr = "- `[PROPOSTA — validar com PO: mini-jogo `minijogo:varal-do-dia` · por quê: verbos de ordenar]`\n"
    itens = fc.itens_em_aberto({"spec_missao": _spec_minijogo(extra=pr)})
    assert not [i for i in itens if i.tipo == fc.ESCOLHA_AMBIENTE]
    assert [i for i in itens if i.tipo == fc.PROPOSTA and "minijogo" in i.assunto]
    assert not fc.escolhas_de_ambiente({"spec_missao": _spec_app()})
    for missao in REFAZER:
        assert not fc.escolhas_de_ambiente(_estado(missao))


# --------------------------------------------------------------------------- 2b. revisão do PR #76: só a escolha responde
PROPOSTA_3EF = ("- [PROPOSTA — validar com PO: mini-jogo `minijogo:varal-do-dia` no lugar de app clonado · por quê: os verbos "
                "são genéricos · alternativa: unoojornal]\n")


def test_proposta_da_escolha_so_aceita_ou_recusa_e_a_resposta_grava_a_escolha():
    """A proposta que pergunta a classe só tem aceitar ou recusar: «outro valor» gravava «unoojornal — PO, parecer de …»
    na linha dela, a `secao_ds` seguia com o mini-jogo, e o código lia como aprovado (revisão do PR #76)."""
    estado = {"spec_missao": _spec_minijogo(extra=PROPOSTA_3EF)}
    itens = fc.itens_em_aberto(estado)
    escolha = [i for i in itens if i.escolha_ambiente]
    assert len(escolha) == 1 and escolha[0].tipo == fc.PROPOSTA and escolha[0].opcoes() == [fc.ACEITAR, fc.RECUSAR]
    assert amb.escolha_do_po(estado["spec_missao"]) == "pendente"
    with pytest.raises(fc.RespostaInvalida):
        fc.decidir(itens, {escolha[0].id: {"resposta": fc.OUTRO, "valor": "unoojornal"}}, "24/10/2026 10:00:00", "c")
    for resposta, esperado in ((fc.ACEITAR, "aprovada"), (fc.RECUSAR, "recusada")):
        d = fc.decidir(itens, {escolha[0].id: {"resposta": resposta}}, "24/10/2026 10:00:00", "produto")
        novos, falhas = fc.aplicar_edicoes(estado, d.edicoes)
        assert not falhas
        assert amb.escolha_do_po(novos["spec_missao"]) == esperado
        assert amb.escolha_do_po(estado["spec_missao"], decisoes_do_po=d.decisoes) == esperado
        assert not [i for i in fc.itens_em_aberto({**estado, **novos, "decisoes_do_po": d.decisoes})
                    if i.tipo == fc.ESCOLHA_AMBIENTE]
    # os parâmetros do jogo continuam com «outro valor»: não são a escolha
    parametro = "- `[PARÂMETRO — a definir por produto: duração da fase do `minijogo:varal-do-dia`, sugestão: 90 s]`\n"
    outros = [i for i in fc.itens_em_aberto({"spec_missao": _spec_minijogo(extra=PROPOSTA_3EF + parametro)})
              if not i.escolha_ambiente]
    assert outros and all(fc.OUTRO in i.opcoes() for i in outros)


def test_outro_valor_na_proposta_da_escolha_e_recusa_e_vai_a_produto():
    """Mutante «o PO responde outro valor ao mini-jogo»: a resposta de antes do PR, ainda no texto ou no registro, é
    recusa da seção proposta — o manifesto bloqueia, e o D9 não monta o jogo."""
    gravada = ("- unoojornal — PO, parecer de 24/10/2026 (no lugar da proposta: mini-jogo `minijogo:varal-do-dia` no "
               "lugar de app clonado)\n")
    spec = _spec_minijogo(extra=gravada)
    assert amb.escolha_do_po(spec) == "recusada"
    recusa = [a for a in amb.conferir_spec(spec, serie="2EF") if a["codigo"] == "escolha-de-ambiente-recusada"]
    assert recusa and recusa[0]["severidade"] == "bloqueio" and "«unoojornal»" in recusa[0]["resumo"]
    assert "escolha-de-ambiente-recusada" in [a.get("codigo") for a in validar_manifesto(spec)["achados"]]
    casca = ("## 14. Ambiente simulado (D9)\n\n- **Nome:** Varal · **Seção do DS:** `minijogo:varal-do-dia` · "
             "**Classe:** mini-jogo\n")
    d9 = amb.conferir_d9(_saida_d9(casca), None, {"spec_missao": spec})
    assert "escolha-de-ambiente-recusada" in _codigos(d9["achados"])
    registro = [{"id": "x", "tipo": fc.PROPOSTA, "assunto": "mini-jogo `minijogo:varal-do-dia` no lugar de app clonado",
                 "resposta": fc.OUTRO, "valor": "unoojornal"}]
    assert amb.escolha_do_po(_spec_minijogo(extra=PROPOSTA_3EF), decisoes_do_po=registro) == "recusada"


@pytest.mark.parametrize("linha", [
    # o [PARÂMETRO] respondido que cita a seção não é a escolha da classe
    "- Duração da fase do `minijogo:varal-do-dia`: 90 s — PO, parecer de 24/10/2026\n",
    # nem a proposta de um parâmetro do jogo, aprovada
    "- aprovada — PO, parecer de 24/10/2026: duração da fase do `minijogo:varal-do-dia` em 90 s\n",
    # nem a proposta que tira o mini-jogo, aprovada
    "- aprovada — PO, parecer de 24/10/2026: usar a `unoochat` no lugar do `minijogo:varal-do-dia`\n",
])
def test_linha_que_so_cita_a_secao_nao_responde_a_escolha(linha):
    spec = _spec_minijogo(extra=linha)
    assert amb.escolha_do_po(spec) == "silencio"
    assert "escolha-de-ambiente-sem-o-po" in _codigos(amb.conferir_spec(spec, serie="2EF"))
    assert [i for i in fc.itens_em_aberto({"spec_missao": spec}) if i.tipo == fc.ESCOLHA_AMBIENTE]


def test_registro_da_escolha_de_outra_secao_nao_responde_por_esta():
    """A recusa de `nova:pistagrama` não é a do `minijogo:varal-do-dia`: sem comparar a seção, ele saía «recusado» e o de
    acordo não abria o item dele."""
    outra = [{"tipo": fc.ESCOLHA_AMBIENTE, "assunto": "ambiente novo `nova:pistagrama` — a spec fixa…", "resposta": "recusar"}]
    spec = _spec_minijogo()
    assert amb.escolha_do_po(spec, decisoes_do_po=outra) == "silencio"
    assert [i for i in fc.itens_em_aberto({"spec_missao": spec, "decisoes_do_po": outra})
            if i.tipo == fc.ESCOLHA_AMBIENTE]
    desta = [{"tipo": fc.ESCOLHA_AMBIENTE, "assunto": "mini-jogo `minijogo:varal-do-dia` — a spec fixa…",
              "resposta": "recusar"}]
    assert amb.escolha_do_po(spec, decisoes_do_po=desta) == "recusada"


@pytest.mark.parametrize("briefing, esperado", [
    ("Quero um mini-jogo de ordenar fotos.", "briefing"),
    ("secao_ds: minijogo:varal-do-dia", "briefing"),
    ("Não é mini-jogo: a turma usa a galeria.", "silencio"),
    ("Nada de mini-jogo nesta missão.", "silencio"),
    ("App clonado, em vez de mini-jogo.", "silencio"),
    ("secao_ds: minijogo:outro-jogo", "silencio"),
])
def test_briefing_so_decide_o_minijogo_quando_o_pede(briefing, esperado):
    assert amb.escolha_do_po(_spec_minijogo(), briefing=briefing) == esperado


# --------------------------------------------------------------------------- 3. o D9: só a ficha do bloco 14
BLOCO14_GALERIA = ("## 14. Ambiente simulado (D9)\n\n### 14.1 Ficha\n- **Nome do app que o estudante vê:** Unoogaleria\n"
                   "- **Seção do DS:** `unoogaleria` · **Classe:** app clonado\n- **Chrome:** álbum, grade e visualizador.\n")


def _saida_d9(bloco14: str = BLOCO14_GALERIA, envelope: Optional[Dict[str, Any]] = None, devolucao: str = "Nenhuma.",
              antes: str = "") -> str:
    env = envelope or {"agente": "ambiente-simulado", "status": "dormente",
                       "ambiente": {"nome": "Unoogaleria", "classe": "app-clonado", "secao_ds": "unoogaleria"},
                       "devolucao": None}
    return ("# Ambiente simulado — exp99\n\n**Veredito: ⚪ DORMENTE**\n\n## Passo 1 — O que a spec decidiu\n\nunoogaleria.\n\n"
            "## Passo 2 — Os verbos do bloco 4 no ambiente decidido\n\n| Verbo | Rótulo |\n|---|---|\n| tocar | Tocar |\n\n"
            f"## Passo 3 — Devolução a produto\n\n{devolucao}\n\n## Passo 4 — Bloco 14 do anexo de design (só ele)\n\n"
            + antes + bloco14 + "\n## Testes — resultado\n\nok\n\n```json\n" + json.dumps(env, ensure_ascii=False)
            + "\n```\n")


def _d9(spec: str, saida: str, estrito: bool = False, anexo: str = "") -> Dict[str, Any]:
    split = get_ambiente_simulado_split()
    split.estrito = estrito
    estado = {"spec_missao": spec, "ambiente_simulado": saida}
    if anexo:
        estado[KEY_ANEXO] = anexo
    return t._rodar(estado, split)


def _achados(st: Dict[str, Any]) -> list:
    return (st.get("ambiente_status_envelope") or {}).get("achados") or []


def test_d9_dormente_com_a_ficha_da_spec_passa_e_grava_so_o_bloco_14():
    st = _d9(_spec_app(), _saida_d9(), estrito=True, anexo=montar_anexo(t.BLOCO13))
    assert st["ambiente_status"] == "aprovado", _achados(st)
    assert "## 14. Ambiente simulado" in st[KEY_ANEXO] and "## 13. Decisões D0" in st[KEY_ANEXO]
    assert st["spec_missao"] == _spec_app()


@pytest.mark.parametrize("estrito", [False, True])
def test_mutante_d9_cria_ambiente_novo_com_a_spec_calada(estrito):
    """Mutante «D9 cria ambiente novo com a spec calada»: tem de virar devolução, não criação. O bloco 14 com o ambiente
    que ele inventou não entra no anexo; a spec calada e a sugestão dele vão ao PO."""
    calada = _spec_app("")
    criado = BLOCO14_GALERIA.replace("`unoogaleria` · **Classe:** app clonado", "`nova:pistagrama` · **Classe:** app clonado")
    env = {"agente": "ambiente-simulado", "status": "novo",
           "ambiente": {"nome": "Pistagrama", "classe": "app-clonado", "secao_ds": "nova:pistagrama", "novo": True}}
    st = _d9(calada, _saida_d9(criado, env), estrito=estrito, anexo=montar_anexo(t.BLOCO13))
    assert "pistagrama" not in st[KEY_ANEXO].lower() and "## 14." not in st[KEY_ANEXO], "o D9 criou o ambiente"
    achados = {a["codigo"]: a for a in _achados(st)}
    assert achados["ambiente-ausente-na-spec"]["agente_responsavel"] == "PO"
    devolucao = achados["devolucao-a-produto"]
    assert devolucao["resumo"].startswith("[PROPOSTA — validar com PO: o D9 sugeriu `nova:pistagrama`")
    assert devolucao["agente_responsavel"] == "PO" and "Refazer" in devolucao["resumo"]
    assert st["ambiente_status"] == ("bloqueado" if estrito else "amarelo")
    assert st["ambiente_status_envelope"].get("precisa_humano") or estrito
    # não é ticket do D9: outra rodada dele não decide o ambiente
    assert "decisao-de-produto-pelo-agente" not in achados


def test_mutante_bloco_14_troca_a_secao_ds():
    """Mutante «bloco 14 troca a secao_ds»: a ficha do `unoovista` numa spec `unoogaleria` é decisão de produto — bloqueia,
    volta ao D9 como ticket, e não entra no anexo; a troca vai ao PO como sugestão."""
    anexo = montar_anexo(t.BLOCO13 + "\n" + BLOCO14_GALERIA)
    trocado = BLOCO14_GALERIA.replace("Unoogaleria", "Unoovista").replace("`unoogaleria`", "`unoovista`")
    st = _d9(_spec_app(), _saida_d9(trocado), anexo=anexo)
    assert st[KEY_ANEXO] == anexo and "unoovista" not in st[KEY_ANEXO]
    produto = [a for a in _achados(st) if a["codigo"] == "decisao-de-produto-pelo-agente"]
    assert len(produto) == 1 and produto[0]["agente_responsavel"] == "ambiente-simulado"
    assert "`unoovista`" in produto[0]["resumo"] and st["ambiente_status"] == "bloqueado"
    assert any(a["codigo"] == "devolucao-a-produto" and "`unoovista`" in a["resumo"] for a in _achados(st))
    # a extra declarada no bloco 0 e a seção da plataforma (`unooria`) podem aparecer na ficha
    com_extra = _spec_app().replace("- `secao_ds: unoogaleria`", "- `secao_ds: unoogaleria`\n- `secoes_ds_extras: [unoovista]`")
    extra = BLOCO14_GALERIA + "\n### 14.2 Ficha da extra\n- **Seção do DS:** `unoovista`\n- **Seção do DS:** `unooria`\n"
    assert _d9(com_extra, _saida_d9(extra))["ambiente_status"] == "aprovado"


@pytest.mark.parametrize("linha, nomeadas", [
    ("- **Seção do DS:** `ds-unoogaleria` (ponte `@edu/ui/ds-unoogaleria`)", ["unoogaleria"]),
    ("- **Seção do Design System:** `Unoogaleria` sobre `wireframe-cinza`", ["unoogaleria"]),
    ("- **Seção do DS:** nenhuma seção nova; a galeria da missão", []),
    ("- **Seção do DS:** `galeriadefotos`", ["galeriadefotos"]),
])
def test_leitura_da_secao_na_ficha_tolera_a_forma_e_pega_a_inventada(linha, nomeadas):
    """A ponte e o nome com caixa nomeiam a seção; a coleção do lo-fi e a prosa sem crase não são seção; o nome inventado
    sem prefixo (`galeriadefotos`, a exp01ef1b de 06/10) é — e é o que o bloco 0 não decidiu."""
    assert amb.secoes_do_bloco_14("## 14. Ambiente simulado (D9)\n" + linha + "\n") == nomeadas


def test_bloco_14_que_troca_a_classe_bloqueia():
    ficha = ("## 14. Ambiente simulado (D9)\n\n# Mini-jogo — Varal\n- **Seção do DS:** `unoogaleria`\n"
             "- **Classe:** mini-jogo\n")
    st = _d9(_spec_app(), _saida_d9(ficha))
    assert "decisao-de-produto-pelo-agente" in _codigos(_achados(st)) and st["ambiente_status"] == "bloqueado"
    assert "mini-jogo" in next(a for a in _achados(st) if a["codigo"] == "decisao-de-produto-pelo-agente")["resumo"]


def test_bloco_14_com_regra_ou_fase_de_jogo_bloqueia_e_a_citacao_literal_da_spec_nao():
    spec = _spec_minijogo(extra="- Classe: mini-jogo — aprovada — PO, parecer de 24/10/2026: `minijogo:varal-do-dia`\n")
    casca = ("## 14. Ambiente simulado (D9)\n\n# Mini-jogo — Varal do dia\n- **Seção do DS:** `minijogo:varal-do-dia`\n"
             "- **Classe:** mini-jogo\n- **Área de jogo:** o varal, no centro da tela.\n")
    env = {"agente": "ambiente-simulado", "status": "dormente",
           "ambiente": {"classe": "mini-jogo", "secao_ds": "minijogo:varal-do-dia"}, "devolucao": None}
    assert _d9(spec, _saida_d9(casca, env))["ambiente_status"] == "aprovado"
    inventada = casca + ("- **Como se vence uma fase:** pendurar três fotos em dez segundos.\n"
                         "### Regras e fases\n- `R3` Quem errar perde uma vida.\n")
    st = _d9(spec, _saida_d9(inventada, env))
    jogo = [a for a in _achados(st) if a["codigo"] == "decisao-de-produto-pelo-agente"]
    assert jogo and "R3" in jogo[0]["resumo"] and "Como se vence" in jogo[0]["resumo"]
    copiada = casca + "\n**Como o progresso aparece:** um mapa com dois varais; o feito fica colorido.\n"
    assert _d9(spec, _saida_d9(copiada, env))["ambiente_status"] == "aprovado"


MINIJOGO_APROVADO = "- `secao_ds: minijogo:varal-do-dia` — aprovada — PO, parecer de 24/10/2026"
ENV_MINIJOGO = {"agente": "ambiente-simulado", "status": "dormente",
                "ambiente": {"classe": "mini-jogo", "secao_ds": "minijogo:varal-do-dia"}, "devolucao": None}


@pytest.mark.parametrize("secao, decidida, linha", [
    # o prompt 067 manda montar «a seção do DS `minijogo-<nome>` sobre `unooria`»
    ("minijogo:varal-do-dia", MINIJOGO_APROVADO, "- **Seção do DS:** `minijogo-varal-do-dia` sobre `unooria`"),
    ("minijogo:varal-do-dia", MINIJOGO_APROVADO, "- **Seção do DS:** `minijogo:varal-do-dia` · **Classe:** mini-jogo"),
    # o ambiente novo aprovado, nomeado sem o prefixo `nova:`
    ("nova:pistagrama", "- `secao_ds: nova:pistagrama` — aprovada — PO, parecer de 24/10/2026",
     "- **Seção do DS:** `pistagrama` · **Classe:** app clonado"),
])
def test_ficha_do_minijogo_e_do_ambiente_novo_aprovados_nao_e_falso_positivo(secao, decidida, linha):
    """Revisão do PR #76: a ficha com `minijogo-<nome>` ou com o nome do ambiente novo sem prefixo bloqueava como decisão
    de produto e era descartada do anexo — justamente no caminho que o PO aprovou."""
    spec = _spec(secao, serie="2EF").replace(f"- `secao_ds: {secao}`", decidida).replace(REGRAS_E_FASES_SLOT,
                                                                                       REGRAS_E_FASES)
    assert amb.escolha_do_po(spec) == "aprovada"
    r = amb.conferir_d9(_saida_d9("## 14. Ambiente simulado (D9)\n\n" + linha + "\n"), None, {"spec_missao": spec})
    assert not r["descartar"] and r["achados"] == [], r["achados"]
    assert secao in r["nomeadas"]
    # o mesmo nome numa spec que decidiu outra seção continua sendo a seção inventada
    outra = amb.conferir_d9(_saida_d9("## 14. Ambiente simulado (D9)\n\n" + linha + "\n"), None,
                            {"spec_missao": _spec_app("unoochat")})
    assert outra["descartar"] and "decisao-de-produto-pelo-agente" in _codigos(outra["achados"])


@pytest.mark.parametrize("linha, bloqueia", [
    # a linha que o template do 067 prescreve: a classe depois de «·»
    ("- **Seção do DS:** `unoogaleria` · **Classe:** mini-jogo", True),
    ("- **Nome:** Galeria · **Seção do DS:** `unoogaleria` · **Classe:** app clonado · **Dispositivo:** celular", False),
])
def test_classe_depois_do_ponto_na_linha_da_secao_e_lida(linha, bloqueia):
    st = _d9(_spec_app(), _saida_d9("## 14. Ambiente simulado (D9)\n\n" + linha + "\n", {"agente": "ambiente-simulado"}))
    assert ("decisao-de-produto-pelo-agente" in _codigos(_achados(st))) is bloqueia, _achados(st)
    assert (st["ambiente_status"] == "bloqueado") is bloqueia


@pytest.mark.parametrize("trecho, bloqueia", [
    ("### Regras do jogo\n- `R1` Toque na foto certa.\n", True),
    ("| Fase | Nome |\n|---|---|\n| 1 | Varal da noite |\n", True),
    ("| # | Regra da fase | Como vence |\n|---|---|---|\n| 1 | Pendure tudo | três fotos |\n", True),
    # a tabela da ficha com a coluna «#» não é de fases
    ("| # | Componente | Tokens usados |\n|---|---|---|\n| 1 | Área de jogo | `space-4` |\n", False),
    # a linha da tabela de fases igual à da spec é cópia, não decisão
    ("| Fase | Nome | Ideia nova | Regra da fase | Verbo do jogo | Como vence | Como perde | Habilidade |\n"
     "|---|---|---|---|---|---|---|---|\n| 1 | Varal da manhã | ordem de duas fotos | Ponha a foto do café antes da "
     "escola. | ordenar | duas fotos no lugar | foto fora do lugar volta | `EF02CO05` |\n", False),
])
def test_regra_e_fase_de_jogo_em_qualquer_lugar_do_bloco_14(trecho, bloqueia):
    """Só sob um título «Regras … fases» a regra e a tabela eram vistas: «### Regras do jogo» com `R1`, ou «| Fase | Nome
    |» solta, passavam (revisão do PR #76)."""
    spec = _spec_minijogo().replace("- `secao_ds: minijogo:varal-do-dia`", MINIJOGO_APROVADO)
    casca = ("## 14. Ambiente simulado (D9)\n\n- **Nome:** Varal · **Seção do DS:** `minijogo:varal-do-dia` · "
             "**Classe:** mini-jogo\n\n" + trecho)
    st = _d9(spec, _saida_d9(casca, ENV_MINIJOGO))
    assert ("decisao-de-produto-pelo-agente" in _codigos(_achados(st))) is bloqueia, _achados(st)


def test_secao_nova_fora_do_bloco_14_com_regra_de_jogo_bloqueia_e_sem_jogo_e_atencao():
    """«## Regras e fases do mini-jogo» depois do bloco 14 era descartada só com atenção, e escapava ao gate do jogo."""
    spec = _spec_minijogo().replace("- `secao_ds: minijogo:varal-do-dia`", MINIJOGO_APROVADO)
    casca = ("## 14. Ambiente simulado (D9)\n\n- **Seção do DS:** `minijogo:varal-do-dia` · **Classe:** mini-jogo\n\n")
    jogo = casca + "## Regras e fases do mini-jogo\n\n- `R3` Quem errar perde uma vida.\n"
    st = _d9(spec, _saida_d9(jogo, ENV_MINIJOGO))
    produto = [a for a in _achados(st) if a["codigo"] == "decisao-de-produto-pelo-agente"]
    assert len(produto) == 1 and "R3" in produto[0]["resumo"] and st["ambiente_status"] == "bloqueado"
    assert "perde uma vida" not in st[KEY_ANEXO]
    notas = _d9(spec, _saida_d9(casca + "## Notas da ficha\n\n- conferir o contraste no projetor.\n", ENV_MINIJOGO))
    assert notas["ambiente_status"] == "amarelo" and _codigos(_achados(notas)) == ["alterou-fora-do-proprio-bloco"]
    # a seção nova que copia a regra da spec palavra por palavra não decide nada
    copia = _d9(spec, _saida_d9(casca + "## Regras do jogo (da spec)\n\n- `R1` Toque na foto que veio primeiro.\n",
                                ENV_MINIJOGO))
    assert "decisao-de-produto-pelo-agente" not in _codigos(_achados(copia))


@pytest.mark.parametrize("passo3", [
    "Nenhuma. Nenhum verbo pede `[PROPOSTA — validar com PO: …]`.",
    "Nenhuma — o formato seria `[PROPOSTA — validar com PO: <a troca> · por quê: <…> · alternativa: <…>]`.",
])
def test_placeholder_no_passo_3_nao_e_devolucao(passo3):
    """«Nenhuma. Nenhum verbo pede `[PROPOSTA — validar com PO: …]`» virava a devolução «…», bloqueio com
    ESTEIRA_ESTRITA (revisão do PR #76)."""
    assert amb.devolucoes_do_d9(_saida_d9(devolucao=passo3)) == []
    assert _d9(_spec_app(), _saida_d9(devolucao=passo3), estrito=True)["ambiente_status"] == "aprovado"


def test_correcao_pontual_com_o_d9_travado_confere_so_o_bloco_14():
    """Na correção pontual de design o D9 não roda e a resposta é a de antes: na exp01em1b-76d9af6e, a que escreveu nos
    blocos 2, 3, 7 e 10 do Gate 0. O ticket iria ao D9, que não pode reescrever, e o design ficava 🔴 sem saída. Com ele
    travado, o texto fora do bloco 14 é descartado com atenção; fora da correção pontual, continua bloqueando."""
    estado = _estado("exp01em1b-76d9af6e")
    produto = estado["spec_missao_gate0"]
    bloco13 = _bloco(estado["spec_missao"], "13") or _bloco(str(estado["fechamento_lacunas"]), "13")
    base = {k: estado[k] for k in ("ambiente_simulado", "fechamento_lacunas", "briefing", "one_pager") if k in estado}
    base.update({"spec_missao": produto, KEY_ANEXO: montar_anexo(bloco13)})
    split = get_ambiente_simulado_split()
    split.estrito = True
    travado = t._rodar({**base, "modo_correcao": "pontual", "documentos_travados": ["ambiente_simulado"]}, split)
    assert travado["ambiente_status"] == "amarelo", _achados(travado)
    assert not [a for a in _achados(travado) if a["severidade"] == "bloqueio"]
    assert any("Refazer completo de design" in a["resumo"] for a in _achados(travado))
    outro_split = get_ambiente_simulado_split()
    outro_split.estrito = True
    solto = t._rodar(dict(base), outro_split)
    assert solto["ambiente_status"] == "bloqueado"
    assert "decisao-de-produto-pelo-agente" in _codigos(_achados(solto))


@pytest.mark.parametrize("estrito, status", [(False, "amarelo"), (True, "bloqueado")])
def test_d9_que_pede_outro_ambiente_devolve_a_produto_e_emite_a_ficha_da_spec(estrito, status):
    env = {"agente": "ambiente-simulado", "status": "dormente",
           "ambiente": {"classe": "app-clonado", "secao_ds": "unoogaleria"},
           "devolucao": [{"motivo": "verbo-sem-casca", "proposta": "trocar a `unoogaleria` pelo `unoochat`",
                          "por_que": "o verbo encaminhar não existe numa galeria", "alternativa": "unoovista"}]}
    st = _d9(_spec_app(), _saida_d9(envelope=env), estrito=estrito)
    assert "## 14. Ambiente simulado" in st[KEY_ANEXO]
    devolucao = [a for a in _achados(st) if a["codigo"] == "devolucao-a-produto"]
    assert len(devolucao) == 1 and "trocar a `unoogaleria` pelo `unoochat`" in devolucao[0]["resumo"]
    assert "por quê: o verbo encaminhar" in devolucao[0]["resumo"] and st["ambiente_status"] == status
    # a proposta escrita só no Passo 3 também é lida
    so_texto = _saida_d9(devolucao="- [PROPOSTA — validar com PO: trocar a galeria pelo chat · por quê: encaminhar]")
    assert any("trocar a galeria pelo chat" in a["resumo"] for a in _achados(_d9(_spec_app(), so_texto)))


def test_texto_do_d9_fora_do_bloco_14_bloqueia_como_decisao_de_produto():
    """O D9 que recopia a spec e acrescenta uma linha ao bloco 2 escreveu produto: bloqueia e volta a ele (o padrão do
    A066). A linha não entra em lugar nenhum."""
    spec = _spec_app()
    copia = spec.replace("- Apresenta o álbum.", "- Apresenta o álbum.\n- Estado `ERRO_MIDIA_FALHOU`: aviso de contingência.")
    st = _d9(spec, _saida_d9(antes=copia + "\n"))
    produto = [a for a in _achados(st) if a["codigo"] == "decisao-de-produto-pelo-agente"]
    assert [a["bloco"] for a in produto] == ["2"] and not produto[0].get("aberto_dono_po")
    assert "ERRO_MIDIA_FALHOU" in produto[0]["resumo"] and st["ambiente_status"] == "bloqueado"
    assert st["spec_missao"] == spec and "ERRO_MIDIA_FALHOU" not in st[KEY_ANEXO]
    # a cópia igual não é mudança
    assert _d9(spec, _saida_d9(antes=spec + "\n"))["ambiente_status"] == "aprovado"
    # e o ticket vai ao D9: o código está na lista que o A089 leva ao retrabalho
    import inspect
    from agents.checkers import QaAfirmacoesAgent

    assert "decisao-de-produto-pelo-agente" in inspect.getsource(QaAfirmacoesAgent)


def test_exp01em1b_76d9af6e_o_d9_escreveu_no_gate0_e_o_codigo_o_pega():
    """A resposta gravada do D9 da exp01em1b-76d9af6e (23/10/2026), refeita pelo split: os blocos 2, 3, 7 e 10 que ele
    mudou são decisão de produto dele; o bloco 0, ele recopiou do D0 de antes do PR 2."""
    r = amb.reavaliar_d9(_estado("exp01em1b-76d9af6e"))
    produto = [a for a in r["achados"] if a["codigo"] == "decisao-de-produto-pelo-agente"]
    assert {a["bloco"] for a in produto} == {"2", "3", "7", "10"} and r["status"] == "bloqueado"
    assert any("ERRO_MIDIA_FALHOU" in a["resumo"] for a in produto)
    assert any("Demonstração de primeiro uso" in a["resumo"] for a in produto)


@pytest.mark.parametrize("missao", COM_D9)
def test_a_ficha_gravada_no_acervo_nomeia_o_ambiente_da_spec_e_nao_traz_jogo(missao):
    """Sem falso positivo no acervo: nenhuma das 12 fichas gravadas troca o ambiente ou a classe, nem traz regra de jogo."""
    estado = _estado(missao)
    r = amb.conferir_d9(str(estado["ambiente_simulado"]), None,
                        {**estado, "spec_missao": estado.get("spec_missao_gate0") or estado["spec_missao"]})
    assert not r["descartar"], (r["nomeadas"], r["classes"], r["decidido"])
    assert not [a for a in r["achados"] if a["codigo"] == "decisao-de-produto-pelo-agente"], r["achados"]
    assert r["nomeadas"], "a ficha não nomeou a seção — o leitor não a achou"


@pytest.mark.parametrize("missao", sorted(REFAZER))
def test_refazer_das_quatro_missoes_com_o_d9_novo_passa(missao):
    """O refazer de design com o D9 deste PR: ele responde só com o bloco 14 (o da sessão gravada), sobre a spec de produto
    e o anexo com o bloco 13 — o split grava a ficha, e nada bloqueia, com ESTEIRA_ESTRITA."""
    estado = _estado(missao)
    gravada = str(estado["ambiente_simulado"])
    from agents.callbacks import extrair_envelope

    bloco14 = amb.bloco_14(amb._passo4(gravada) or "")
    env = extrair_envelope(gravada) or {}
    novo = {"agente": "ambiente-simulado", "status": "dormente", "ambiente": env.get("ambiente"), "devolucao": None}
    produto = estado["spec_missao_gate0"]
    # a 4fd72a9a e a 60cfa7f4 perderam o bloco 13 da spec (o defeito que o PR 2 consertou): no refazer, o D0 roda antes e
    # o escreve — aqui, o da resposta gravada dele
    bloco13 = _bloco(estado["spec_missao"], "13") or _bloco(str(estado["fechamento_lacunas"]), "13")
    anexo = montar_anexo(bloco13)
    st = _d9(produto, _saida_d9(bloco14, novo), estrito=True, anexo=anexo)
    assert st["ambiente_status"] != "bloqueado", _achados(st)
    assert not [a for a in _achados(st) if a["severidade"] == "bloqueio"]
    assert "## 14." in st[KEY_ANEXO] and "## 13." in st[KEY_ANEXO] and st["spec_missao"] == produto


# --------------------------------------------------------------------------- 4. a jornada só mapeia as telas
JORNADA = """# Jornada — exp99

## Seção 3 — Inventário de telas
| ID | Etapa |
|---|---|
| E2-ALU-01 | 2 |

## Seção 5 — Regras, fases e mecânicas

**As regras do jogo:**

```
R1 Toque na foto que veio primeiro.
R2 Arraste a foto até o varal.
```

| Fase | Nome (da spec) | Regra da fase (da spec, igual) | Telas (IDs do inventário) | Beat | Estados |
|---|---|---|---|---|---|
| 1 | Varal da manhã | Ponha a foto do café antes da escola. | E2-ALU-01 | B2 | em fase · vencida · perdida |
| 2 | Varal da tarde | Ponha as três fotos na ordem do dia. | E2-ALU-02 | B3 | em fase · vencida · perdida |
{extra}
## Lacunas
- nenhuma
"""


def _jornada(extra: str = "") -> str:
    return JORNADA.replace("{extra}", extra)


def test_jornada_que_copia_as_regras_e_as_fases_da_spec_passa():
    r = amb.conferir_jornada(_spec_minijogo(), _jornada())
    assert r["achados"] == [] and r["contagem"]["fases_da_jornada"] == 2 == r["contagem"]["fases_da_spec"]


@pytest.mark.parametrize("estrito, severidade", [(False, "decisao_humana"), (True, "bloqueio")])
def test_mutante_jornada_inventa_fase_3_do_minijogo(estrito, severidade):
    """Mutante «jornada inventa fase 3 do mini-jogo»: a fase que a spec não tem vira proposta ao PO, pelo gate das arestas
    (A083b), com dono PO — não entra no jogo da missão."""
    fase3 = "| 3 | Varal da noite | Ponha a foto do jantar por último. | E2-ALU-03 | B4 | em fase · vencida · perdida |\n"
    estado = {"spec_missao": _spec_minijogo(), "jornada_telas": _jornada(fase3)}
    r = arestas.validar(estado, estrito=estrito)
    fase = [a for a in r["achados"] if a["codigo"] == "fase-fora-da-spec"]
    assert len(fase) == 1 and fase[0]["severidade"] == severidade and fase[0]["agente_responsavel"] == "PO"
    assert fase[0]["resumo"].startswith("[PROPOSTA — validar com PO: a jornada acrescenta a fase 3 «Varal da noite»")
    assert r["status"] == ("bloqueado" if estrito else "amarelo")
    assert "Mini-jogo: 3 fase(s)" in arestas.relatorio(r, "exp99")
    assert arestas.propostas(r)[0].endswith("]")


def test_jornada_que_muda_ou_acrescenta_regra_vira_proposta_e_fase_sem_tela_e_atencao():
    mudada = _jornada().replace("R2 Arraste a foto até o varal.", "R2 Arraste a foto até o varal antes do tempo acabar.\n"
                                                                   "R3 Quem errar três vezes recomeça o jogo.")
    codigos = _codigos(amb.conferir_jornada(_spec_minijogo(), mudada)["achados"])
    assert codigos == ["regra-de-jogo-mudada", "regra-fora-da-spec"]
    outra = _jornada().replace("| Ponha as três fotos na ordem do dia. |", "| Ponha as três fotos em cinco segundos. |")
    assert _codigos(amb.conferir_jornada(_spec_minijogo(), outra)["achados"]) == ["regra-de-fase-mudada"]
    sem_a_2 = "\n".join(l for l in _jornada().splitlines() if not l.startswith("| 2 |"))
    faltou = amb.conferir_jornada(_spec_minijogo(), sem_a_2)["achados"]
    assert _codigos(faltou) == ["fase-sem-tela"] and faltou[0]["severidade"] == "atencao"
    assert faltou[0]["agente_responsavel"] == "jornada"


def test_jornada_com_jogo_numa_missao_de_app_clonado_vira_proposta():
    r = amb.conferir_jornada(_spec_app(), _jornada())
    assert _codigos(r["achados"]) == ["jogo-fora-da-spec"] and "mini-jogo é escolha do PO" in r["achados"][0]["resumo"]


@pytest.mark.parametrize("missao", COM_JORNADA)
def test_jornada_do_acervo_sem_falso_positivo(missao):
    """As 12 jornadas do acervo são de app clonado, com a Seção 5 «n/a»: nenhuma regra, fase ou proposta."""
    estado = _estado(missao)
    spec = str(estado.get("spec_missao_gate0") or estado.get("spec_missao") or "")
    r = amb.conferir_jornada(spec, str(estado["jornada_telas"]))
    assert r["achados"] == [] and r["contagem"]["fases_da_jornada"] == 0 == r["contagem"]["regras_da_jornada"]


# --------------------------------------------------------------------------- 5. triagem, decisões e prompts
@pytest.mark.parametrize("pedido, vai", [
    ("Trocar o ambiente para o Unoovista.", True),
    ("Transformar a etapa 3 num mini-jogo de ordenar.", True),
    ("Usar a unoochat no lugar da galeria.", True),
    ("Criar um ambiente novo para a etapa 5.", True),
    ("O botão do mini-jogo ficou pequeno: aumentar.", False),
    ("Deixar o texto que aparece dentro do ambiente mais curto.", False),
    ("Não trocar o ambiente.", False),
    # revisão do PR #76: a devolução do D9 que o PO cola no Refazer, e as formas naturais da troca
    ("[PROPOSTA — validar com PO: trocar a `unoogaleria` pelo `unoochat` · por quê: o verbo encaminhar não existe numa "
     "galeria · alternativa: unoovista]", True),
    ("[PROPOSTA — validar com PO: `unoochat` no lugar da `unoogaleria` · por quê: encaminhar]", True),
    ("Trocar a unoogaleria pelo unoochat.", True),
    ("Mudar para o unoovista.", True),
    ("Passar a missão para a seção unoovista.", True),
    ("Mini-jogo no lugar de app clonado na etapa 3.", True),
    # e o que é de design: seção de documento, classe CSS, ambiente sonoro, verbo da missão
    ("Adicionar uma seção nova na tela de reflexão com as respostas da turma.", False),
    ("Criar uma seção nova no relatório do professor.", False),
    ("Alterar a classe CSS do botão de enviar.", False),
    ("Mudar o ambiente sonoro da tela 3 para mais calmo.", False),
    ("O aluno vê que sua ação mudou o ambiente.", False),
    ("O aluno deve passar a foto para o unoochat.", False),
])
def test_triagem_leva_a_troca_de_ambiente_a_produto(pedido, vai):
    from tools.triagem_pedido import regra_de_produto

    motivos = regra_de_produto(pedido, {})
    assert any(m.startswith(("muda o ambiente ou a classe", "proposta de troca do ambiente")) for m in motivos) is vai, \
        motivos


def test_triagem_sem_falso_positivo_nos_pedidos_do_acervo():
    """Nenhum pedido do PO gravado no acervo troca o ambiente: nenhuma frase deles casa a troca de ambiente."""
    import re

    from tools.triagem_pedido import _RE_PROPOSTA_DE_AMBIENTE, _RE_TROCA_DE_AMBIENTE

    frases = 0
    for p in ACERVO.glob("*/estado.json"):
        for pedido in json.loads(p.read_text(encoding="utf-8")).get("pedidos_do_po") or []:
            texto = str(pedido.get("texto") or "") if isinstance(pedido, dict) else str(pedido)
            for frase in re.split(r"(?<=[.!?:])\s+|\n+", texto):
                frases += 1
                assert not _RE_TROCA_DE_AMBIENTE.search(frase), (p.parent.name, frase)
            assert not _RE_PROPOSTA_DE_AMBIENTE.search(texto), (p.parent.name, texto[:200])
    assert frases > 50


def test_classe_ambiente_e_do_po_no_d0_e_na_completude():
    from tools.decisoes import classe_de_produto, decisoes_d0_de_produto

    assert classe_de_produto("ambiente").startswith("classe `ambiente` é de produto")
    completude = ("## Passo 3 — Decisões [CP-n]\n\n[CP-1] 0.classe_ambiente\nDecisão: mini-jogo de ordenar.\n"
                  "Base: inferência: a faixa é 2º ano.\n")
    env = {"decisoes": [{"id": "CP-1", "campo": "0.classe_ambiente", "classe": "ambiente", "cor": "verde",
                         "base": "inferencia"}]}
    sem_parecer, _ = decisoes_d0_de_produto(completude, env, _spec_app(), prefixo="CP")
    assert sem_parecer and "classe `ambiente`" in sem_parecer[0]


def test_prompts_de_produto_decidem_e_o_d9_e_a_jornada_nao():
    from prompts import load_prompt
    from prompts.loader import get_prompt_raw

    referencia = get_prompt_raw("references/ambiente-e-minijogo.md")
    for trecho in ("ambiente existente antes de ambiente novo", "Gate de aplicabilidade", "Faixa **1º–5º ano**",
                   "### Regras e fases do mini-jogo", "[PROPOSTA — validar com PO: mini-jogo"):
        assert trecho.lower() in referencia.lower(), trecho
    for prompt in ("produto/004_nucleo_narrativo.md", "produto/045_spec_missao.md", "produto/046_completude_spec.md"):
        assert "Gate de aplicabilidade" in load_prompt(prompt), prompt
    d9 = get_prompt_raw("design/067_ambiente_simulado.md")
    assert "Você não decide nada de produto" in d9 and "Passada 2b" not in d9 and "[RS-AMB]" not in d9
    # o prompt diz o que o código faz: no bloco 13 do D0 o texto do D9 é atenção, não bloqueio (revisão do PR #76)
    assert "no bloco 13, descarta com atenção" in d9 and "bloco 13 do anexo **(código)**" not in get_prompt_raw(
        "references/pronto.md")
    assert "## Bloco 14 — Ficha do ambiente" in d9 and '"status": "dormente", "ambiente"' in d9
    jornada = get_prompt_raw("design/071_jornada.md")
    assert "Agora você copia e mapeia: nada mais." in jornada and "O jogo desta missão é seu" not in jornada
    formato = get_prompt_raw("references/formato-spec.md")
    assert "`classe_ambiente: app-clonado | mini-jogo`" in formato and "Regras e fases do mini-jogo" in formato


def test_split_do_d9_confere_o_ambiente_e_o_catalogo_diz_o_que_mudou():
    from agents.design import DESIGN_METADATA

    assert get_ambiente_simulado_split().conferir_ambiente
    meta = {m["id"]: m["description"] for m in DESIGN_METADATA}
    assert "Sem poder de produto" in meta["A067AmbienteSimulado"]
    assert "decisão de produto" in meta["A068AmbienteSimuladoSplit"]
    assert "Seção 5 da jornada" in meta["A083bArestasContrato"]
