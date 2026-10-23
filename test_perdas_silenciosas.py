"""PR 2 do plano «Produto dono do contrato» (docs/planos/2026-10-23-produto-dono-do-contrato.md): as perdas
silenciosas do D0, sem mudar papéis.

- a spec é montada em código (Gate 0 + 13 + 14): o bloco 13 sumia quando o split acusava linhas-perdidas (60cfa7f4 e
  4fd72a9a), e o PRD da 4fd72a9a citava D0-1 e D0-6 de uma spec sem nenhum;
- a marca «Resolvido em [D0-n]» vira o mapa célula → D0, no bloco 13;
- a mudança do design no texto do Gate 0 vira `[ABERTO — dono: PO]` no cartão do parecer de design (bloqueia só com
  ESTEIRA_ESTRITA);
- a classe do D0 é conferida por lista branca e prefixo, e [D0-n] que fecha [PARÂMETRO]/[PROPOSTA] do Gate 0 sem parecer
  datado é decisão de produto, inclusive em duração, dados e acessibilidade;
- [D0-n] citado a jusante precisa existir no bloco 13 da spec apontada.

Tudo determinístico, sem modelo: as respostas do D0 e do D9 são as gravadas nas sessões do acervo (`tests/acervo`).
"""
from __future__ import annotations

import asyncio
import copy
import json
import warnings
from pathlib import Path
from typing import Any, Dict

import pytest
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.events import Event, EventActions
from google.adk.runners import InMemoryRunner
from google.genai import types
from typing_extensions import override

from agents.design import get_ambiente_simulado_split, get_fecha_lacunas_split
from tools import propagacao as pg
from tools import rastro

warnings.filterwarnings("ignore", category=DeprecationWarning)

ACERVO = Path(__file__).resolve().parent / "tests" / "acervo"
#: As 5 sessões do plano que chegaram ao design com a spec do Gate 0 gravada (estados de 23/10/2026).
CINCO = ("exp02em1b-60cfa7f4", "exp02ef1b-4fd72a9a", "exp03em1b-b2e7b4a3", "exp01em1b-76d9af6e", "exp06ef1b-53e011b6")


def _estado(missao: str) -> Dict[str, Any]:
    return json.loads((ACERVO / missao / "estado.json").read_text(encoding="utf-8"))


async def _executar(raiz: BaseAgent) -> Dict[str, Any]:
    runner = InMemoryRunner(agent=raiz, app_name="t")
    sessao = await runner.session_service.create_session(app_name="t", user_id="u", session_id="s")
    async for _ in runner.run_async(user_id="u", session_id=sessao.id,
                                    new_message=types.Content(role="user", parts=[types.Part(text="go")])):
        pass
    final = await runner.session_service.get_session(app_name="t", user_id="u", session_id="s")
    return dict(final.state)


def _rodar(estado: Dict[str, Any], *splits: BaseAgent) -> Dict[str, Any]:
    class Semente(BaseAgent):
        @override
        async def _run_async_impl(self, ctx):
            yield Event(invocation_id=ctx.invocation_id, author=self.name, actions=EventActions(state_delta=estado))

    return asyncio.run(_executar(SequentialAgent(name="R", sub_agents=[Semente(name="S"), *splits])))


def _splits(estrito: bool = False):
    d0, d9 = get_fecha_lacunas_split(), get_ambiente_simulado_split()
    d0.estrito = d9.estrito = estrito
    return d0, d9


def _remontar(state: Dict[str, Any], estrito: bool = False) -> Dict[str, Any]:
    """O design da sessão de novo, só com código: a spec do Gate 0, a resposta gravada do D0 e a do D9."""
    inicial = {k: v for k, v in state.items()
               if not k.startswith(("lacunas_status", "ambiente_status", "base_preservada", "spec_missao_gate0"))}
    inicial["spec_missao"] = state["spec_missao_gate0"]
    return _rodar(inicial, *_splits(estrito))


def _achados(st: Dict[str, Any], chave: str = "lacunas_status_envelope") -> Dict[str, Dict[str, Any]]:
    return {a["codigo"]: a for a in (st.get(chave) or {}).get("achados") or []}


# --------------------------------------------------------------------------- montagem em código
GATE0 = ("# Spec — exp99 v1\n\n**2EF · unoogaleria**\n\n## 0. Identificação de plataforma\n"
         + "".join(f"- Linha {i} da identificação da plataforma, com slug e seção do DS.\n" for i in range(40))
         + "\n## 6. Tetos aplicados\n- Teto de palavras: `[PARÂMETRO — a definir por produto: teto de palavras por "
           "string de interface, sugestão: 15]`.\n- `[ABERTO — dono: produto: Ratificação do teto de texto]`\n"
         + "\n## 12. Decisões fechadas neste gate\n- Debate: «O que a foto mostra?»\n\n## Glossário canônico\n"
           "| Ação | Rótulo |\n|---|---|\n| Confirmar | `Publicar no Álbum` |\n")
BLOCO13 = ("## 13. Decisões D0\n\n### [D0-1] 2.estado_espera — Tela de espera\n- **Decisão:** a tela congela enquanto "
           "a professora fala.\n- **Base:** padrão `espera-de-professora`.\n")
BLOCO14 = "## 14. Ambiente simulado (D9)\n- **Nome do ambiente:** Unoogaleria\n- **Ponte:** `@edu/ui/ds-unoogaleria`\n"


def _saida_d0(passo5: str, tabela: str = "", envelope: Dict[str, Any] | None = None) -> str:
    env = envelope or {"agente": "fecha-lacunas", "status": "segue", "decisoes": [
        {"id": "D0-1", "campo": "2.estado_espera", "classe": "estado", "cor": "verde", "base": "padrao"}]}
    return ("# Fechamento de lacunas — exp99\n\n## Passo 2 — Lacunas classificadas e roteadas\n\n" + tabela
            + "\n## Passo 3 — Decisões [D0-n]\n\n### [D0-1] 2.estado_espera\nDecisão: a tela congela.\nBase: padrão.\n\n"
            + "## Passo 5 — Bloco 13\n\n" + passo5 + "\n## Passo 5b — Relatório de preenchimento\n\n"
            + "### [D0-1] Tela de espera\n**O que faltava:** o que a criança vê enquanto a professora fala.\n\n"
            + "## Passo 6 — Devolutiva ao produto\n\nNada.\n\n```json\n" + json.dumps(env, ensure_ascii=False) + "\n```\n")


def test_d0_que_emite_so_o_bloco_13_ganha_a_spec_do_gate0_montada_em_codigo():
    st = _rodar({"spec_missao": GATE0, "fechamento_lacunas": _saida_d0(BLOCO13)}, _splits()[0])
    assert st["spec_missao"].startswith(GATE0.rstrip()) and "## 13. Decisões D0" in st["spec_missao"]
    assert st["spec_missao_gate0"] == GATE0 and st["lacunas_status"] == "aprovado", _achados(st)
    assert st["relatorio_lacunas"].startswith("### [D0-1]")


def test_retrabalho_do_d0_troca_o_bloco_13_no_lugar_e_mantem_o_14():
    """No retrabalho só o D0 roda, e a spec já tem o bloco 14 do D9 (exp03ef1b, 23/10/2026): o 13 novo entra no lugar do
    antigo, antes do 14."""
    aceita = GATE0 + "\n" + BLOCO13 + "\n" + BLOCO14
    novo13 = BLOCO13.replace("a tela congela", "a tela congela e mostra a professora")
    st = _rodar({"spec_missao": aceita, "spec_missao_gate0": GATE0, "fechamento_lacunas": _saida_d0(novo13)},
                _splits()[0])
    spec = st["spec_missao"]
    assert "mostra a professora" in spec and spec.count("## 13.") == 1 and spec.index("## 13.") < spec.index("## 14.")
    assert "Unoogaleria" in spec and "linhas-perdidas" not in _achados(st)


def test_d0_no_formato_antigo_nao_muda_o_gate0_e_as_marcas_viram_o_mapa():
    """O D0 que ainda reemitir a spec inteira com « — Resolvido em [D0-1]» na linha do [ABERTO]: o texto do Gate 0 fica
    como estava, a marca vai para o mapa célula → D0 do bloco 13, e o rastro a reconhece."""
    marcada = GATE0.replace("Ratificação do teto de texto]`", "Ratificação do teto de texto]` — Resolvido em [D0-1]")
    st = _rodar({"spec_missao": GATE0, "fechamento_lacunas": _saida_d0(marcada + "\n" + BLOCO13)}, _splits()[0])
    spec = st["spec_missao"]
    assert "Resolvido em" not in spec and spec.startswith(GATE0.rstrip())
    assert "### Mapa célula → D0" in pg.bloco_13(spec) and "alterou-fora-do-proprio-bloco" not in _achados(st)
    assert rastro.mapa_celula_d0(spec) == {"[aberto - dono: produto: ratificação do teto de texto]": 1}
    r = rastro.varrer_lacunas(rastro.FONTES_SPEC, {"spec_missao": spec}, etapa_corrente="design")
    assert [x["d0"] for x in r["resolvidos"]] == ["D0-1"], r["achados"]
    # o mapa que aponta para um D0 que o bloco 13 não define não fecha nada
    sem_d0 = spec.replace("### [D0-1] 2.estado_espera — Tela de espera", "### Decisão removida")
    r = rastro.varrer_lacunas(rastro.FONTES_SPEC, {"spec_missao": sem_d0}, etapa_corrente="design")
    assert not r["resolvidos"] and any("Ratificação do teto" in a["trecho"] for a in r["achados"])


@pytest.mark.parametrize("estrito, severidade, status", [(False, "decisao_humana", "amarelo"), (True, "bloqueio", "bloqueado")])
def test_mudanca_no_texto_do_gate0_vira_aberto_dono_po(estrito, severidade, status):
    """A mudança do D0 no texto do Gate 0 não entra na spec e não some: `[ABERTO — dono: PO]` no cartão do parecer de
    design (o app abre o achado que pede pessoa), bloqueando só com ESTEIRA_ESTRITA. Na exp06ef1b-53e011b6 o D0 trocou
    «algoritmos» por «sistemas» no momento em tela da EF06CO10, sem pedido."""
    trocada = GATE0.replace("Linha 3 da identificação", "Linha três da identificação")
    st = _rodar({"spec_missao": GATE0, "fechamento_lacunas": _saida_d0(trocada + "\n" + BLOCO13)}, _splits(estrito)[0])
    aberto = _achados(st)["alterou-fora-do-proprio-bloco"]
    assert "Linha 3 da identificação" in st["spec_missao"] and "Linha três" not in st["spec_missao"]
    assert aberto["resumo"].startswith("[ABERTO — dono: PO: D0 quis mudar o bloco 0") and aberto["aberto_dono_po"]
    assert aberto["severidade"] == severidade and st["lacunas_status"] == status
    assert st["lacunas_status_envelope"]["precisa_humano"]
    # o cartão do parecer de design lista os gates da etapa com os achados (`app._render_motivos_do_semaforo`)
    from pipeline import passagem

    assert passagem.semaforo_da_etapa(st, "design")["lacunas_status"] == ("🔴" if estrito else "🟡")


def test_d9_que_muda_o_gate0_tambem_vira_aberto_e_o_bloco_13_continua_aviso():
    aceita = GATE0 + "\n" + BLOCO13
    copia = aceita.replace("sugestão: 15]`", "sugestão: 15]` (15 palavras)").replace("a tela congela", "a tela trava")
    d9 = ("# Ambiente simulado\n\n## Passo 4 — Spec consolidada\n\n" + copia + "\n" + BLOCO14
          + "\n## Bloco 14 — Ficha do ambiente\nnome: Unoogaleria\n\n```json\n"
          + json.dumps({"agente": "ambiente-simulado", "status": "dormente"}) + "\n```\n")
    st = _rodar({"spec_missao": aceita, "ambiente_simulado": d9}, _splits(False)[1])
    achados = (st.get("ambiente_status_envelope") or {}).get("achados") or []
    assert {a["severidade"] for a in achados} == {"decisao_humana", "atencao"}, achados
    assert any(a.get("aberto_dono_po") and "D9 quis mudar o bloco 6" in a["resumo"] for a in achados)
    assert "(15 palavras)" not in st["spec_missao"] and "a tela trava" not in st["spec_missao"]
    assert "## 14. Ambiente simulado" in st["spec_missao"]


def test_mutante_apagar_bloco_13_na_resposta_do_d0():
    """Mutante «apagar bloco 13»: o D0 sem o bloco não troca a spec, e o achado volta a ele como ticket."""
    st = _rodar({"spec_missao": GATE0, "fechamento_lacunas": _saida_d0("Sem decisões nesta rodada.\n")}, _splits()[0])
    assert st["spec_missao"] == GATE0 and st["lacunas_status"] == "bloqueado"
    assert _achados(st)["bloco-proprio-ausente"]["agente_responsavel"] == "fecha-lacunas"


def test_mutante_apagar_bloco_13_da_spec_deixa_as_citacoes_orfas():
    """Mutante «apagar bloco 13» na spec: quem cita [D0-n] a jusante cita o que a spec não tem — bloqueio do design no
    documento de design, do PRD no PRD; no dev, o órfão de um documento de design fica 🟡 (herança)."""
    state = _remontar(_estado("exp06ef1b-53e011b6"))
    estado = {**_estado("exp06ef1b-53e011b6"), "spec_missao": state["spec_missao"]}
    assert not rastro.d0_orfaos(rastro.FONTES_DEV + [{"chave": "prd_final", "rotulo": "PRD", "etapa_padrao": "dev"}], estado)
    mutante = copy.deepcopy(estado)
    mutante["spec_missao"] = mutante["spec_missao"].replace(pg.bloco_13(mutante["spec_missao"]), "")
    mutante["jornada_telas"] += "\n- A tela de espera segue o [D0-1].\n"
    mutante["prd_final"] = "## 1. Visão\nA retomada segue a Decisão contratual [D0-1].\n"
    design = rastro.varrer_lacunas(rastro.FONTES_DESIGN, mutante, etapa_corrente="design")
    assert design["status"] == "bloqueado" and any(a["codigo"] == "d0-orfao" and a["severidade"] == "bloqueio"
                                                   for a in design["achados"] if a.get("documento") == "jornada")
    prd = rastro.varrer_lacunas([{"chave": "prd_final", "rotulo": "PRD", "etapa_padrao": "dev"}], mutante)
    assert [a["trecho"] for a in prd["achados"] if a.get("codigo") == "d0-orfao"] == ["D0-1"]
    dev = rastro.varrer_lacunas(rastro.FONTES_DEV, mutante, etapa_corrente="dev")
    assert {a["severidade"] for a in dev["achados"] if a.get("codigo") == "d0-orfao" and a["documento"] == "jornada"} \
        == {"atencao"}


# --------------------------------------------------------------------------- lista branca e marcadores do Gate 0
_TABELA = ("| ID | Célula (bloco.campo) | Classe | Cor | Fonte de preenchimento | Quem consumiria |\n|---|---|---|---|---|---|\n"
           "| L-01 | `2.area_moldura` | `{classe}` | 🟢 | One-pager §18 | D3 |\n")


@pytest.mark.parametrize("classe, barra", [("mecanica_x", True), ("mecanica_param", True), ("parametro-tempo", True),
                                           ("curriculo", True), ("inventada", True), ("estado", False),
                                           ("`handoff` / `copy-fonte`", False)])
def test_mutante_classe_mecanica_x_barrada_por_prefixo_e_lista_branca(classe, barra):
    """Mutante «classe mecanica_x»: a `mecanica_param` da exp02ef1b passou porque a comparação era por igualdade."""
    st = _rodar({"spec_missao": GATE0, "fechamento_lacunas": _saida_d0(BLOCO13, _TABELA.format(classe=classe))},
                _splits()[0])
    assert ("decisao-de-produto-pelo-agente" in _achados(st)) is barra, _achados(st)


def test_classe_de_produto_so_no_envelope_tambem_e_barrada():
    env = {"agente": "fecha-lacunas", "status": "segue", "decisoes": [
        {"id": "D0-1", "campo": "2.estado_espera", "classe": "mecanica_x", "cor": "verde", "base": "padrao"}]}
    st = _rodar({"spec_missao": GATE0, "fechamento_lacunas": _saida_d0(BLOCO13, envelope=env)}, _splits()[0])
    assert "classe `mecanica_x` é de produto" in _achados(st)["decisao-de-produto-pelo-agente"]["resumo"]


def test_exp02ef1b_d0_que_fecha_parametro_e_proposta_e_produto_em_qualquer_classe():
    """4fd72a9a: o teto de 15 palavras (acessibilidade), a moldura de 10% (mecanica_param), os 45 s (duração) e as
    PQ-01..05 (dados, «Tudo de acordo» genérico) fecharam marcador do Gate 0 sem parecer datado. D0-5 a D0-8, não."""
    st = _remontar(_estado("exp02ef1b-4fd72a9a"))
    resumo = _achados(st)["decisao-de-produto-pelo-agente"]["resumo"]
    for d0 in ("[D0-1]", "[D0-2]", "[D0-3]", "[D0-4]"):
        assert d0 in resumo, d0
    for d0 in ("[D0-5]", "[D0-6]", "[D0-7]", "[D0-8]"):
        assert d0 not in resumo, d0
    assert "classe `acessibilidade`" in resumo and "classe `duracao`" in resumo and "classe `dados`" in resumo


def test_parecer_datado_libera_e_tudo_de_acordo_nao():
    from tools.decisoes import decisoes_d0_de_produto

    spec = "## 3. Caminhos\n- `[PARÂMETRO — a definir por produto: tempo de inatividade no chat, sugestão: 90 segundos]`\n"

    def fechamento(base):
        return ("## Passo 3 — Decisões [D0-n]\n\n### [D0-5] 3.inatividade_chat — Tempo de inatividade no chat\n"
                f"Decisão: aviso depois de 90 segundos.\nBase: {base}\n\n## Passo 4 — RS\n")

    env = {"decisoes": [{"id": "D0-5", "campo": "3.inatividade_chat", "classe": "duracao", "cor": "verde"}]}
    pareceres = "### Produto · Produto · 21/10/2026 15:43:51\n> tempo de inatividade no chat → 90s"
    assert decisoes_d0_de_produto(fechamento("Parecer de Produto (21/10/2026)"), env, spec, pareceres)[0] == []
    assert decisoes_d0_de_produto(fechamento("Parecer de Produto (2026-10-21)"), env, spec, pareceres)[0] == []
    assert decisoes_d0_de_produto(fechamento("Parecer de Produto (21/10/2026): «Tudo de acordo»"), env, spec, pareceres)[0]
    # o parecer citado tem de estar na sessão
    assert decisoes_d0_de_produto(fechamento("Parecer de Produto (21/10/2026)"), env, spec, "")[0]
    # a mesma decisão, vermelha (re-spec), não é decisão do agente
    vermelha = {"decisoes": [{**env["decisoes"][0], "cor": "vermelho"}]}
    assert decisoes_d0_de_produto(fechamento("inferência"), vermelha, spec, "") == ([], [])


# --------------------------------------------------------------------------- acervo: antes e depois
@pytest.mark.parametrize("missao", ("exp02em1b-60cfa7f4", "exp02ef1b-4fd72a9a"))
def test_bloco_13_nao_se_perde_mais_nas_sessoes_que_o_perderam(missao):
    """Reprodução sem modelo: a resposta gravada do D0 e a do D9, montadas pelo código sobre a spec do Gate 0 da sessão.
    Antes o split acusava linhas-perdidas e o D9 montava por cima do Gate 0 — sem o bloco 13."""
    state = _estado(missao)
    assert not pg.d0_a_jusante(state)["bloco_13"] and pg.d0_a_jusante(state)["orfas"]
    st = _remontar(state, estrito=True)
    spec = st["spec_missao"]
    assert spec.startswith(state["spec_missao_gate0"].rstrip()), "o texto do Gate 0 mudou"
    assert "## 14." in spec and spec.index("## 13.") < spec.index("## 14.")
    assert "linhas-perdidas" not in _achados(st) and "linhas-perdidas" not in _achados(st, "ambiente_status_envelope")
    depois = pg.d0_a_jusante({**state, "spec_missao": spec})
    assert depois["bloco_13"] and depois["orfas"] == {}, depois["orfas"]
    assert set(depois["na_spec"]) >= {int(d["id"].split("-")[1]) for d in pg.decisoes_d0(state)}


def test_acervo_bloco_13_em_5_de_5_e_nenhum_d0_orfao_depois_da_montagem():
    """A régua do PR 1 (`tools/propagacao.py`) sobre as 5 sessões do plano: antes, bloco 13 em 3 de 5 e 35 citações
    órfãs; depois da montagem em código, 5 de 5 e nenhuma."""
    antes, depois = {}, {}
    for missao in CINCO:
        state = _estado(missao)
        antes[missao] = pg.d0_a_jusante(state)
        depois[missao] = pg.d0_a_jusante({**state, "spec_missao": _remontar(state)["spec_missao"]})
    assert sum(r["bloco_13"] for r in antes.values()) == 3
    assert sum(len(v) for r in antes.values() for v in r["orfas"].values()) == 35
    assert sum(r["bloco_13"] for r in depois.values()) == 5
    assert {m: r["orfas"] for m, r in depois.items() if r["orfas"]} == {}


def test_instabilidade_do_d0_compara_so_o_bloco_13():
    """O refazer de uma sessão gravada com o D0 antigo (spec inteira) contra o D0 novo (só o bloco 13): o texto do Gate 0
    não é «linha perdida» do D0, que não o escreve mais."""
    anterior = _saida_d0(GATE0 + "\n" + BLOCO13)
    st = _rodar({"spec_missao": GATE0, "fechamento_lacunas": _saida_d0(BLOCO13),
                 "versao_anterior_fechamento_lacunas": anterior}, _splits()[0])
    assert "autor-instavel" not in _achados(st), _achados(st)
    sem_decisao = _saida_d0("## 13. Decisões D0\n\nNenhuma lacuna encontrada.\n")
    st = _rodar({"spec_missao": GATE0, "fechamento_lacunas": sem_decisao,
                 "versao_anterior_fechamento_lacunas": anterior}, _splits()[0])
    assert "autor-instavel" in _achados(st) and "a tela congela" in _achados(st)["autor-instavel"]["resumo"]
