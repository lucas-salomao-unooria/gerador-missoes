"""Achados 🟡 e 🔴 explicados para o PO no Streamlit (pedido do usuário em 25/10/2026).

«Explicar bem os erros amarelos e vermelhos: hoje eles têm limites de caracteres e aparecem cortados e são bem confusos,
até o PO fica confuso.» O catálogo (`tools/explicacoes.py`) cobre todo código do acervo, das sessões brutas de
24/10/2026 e dos PRs abertos (C3, C4); a exibição mostra a explicação simples e o trecho real inteiro, com o código e o
texto original nos detalhes técnicos; e os textos de `pipeline/passagem.py` que vão ao cartão e ao registro não cortam.
"""
from __future__ import annotations

import ast
import inspect
import json
import re
from pathlib import Path
from typing import Any, Dict

import pytest

from pipeline import passagem
from pipeline.passagem import AGUARDANDO, DecisaoInvalida, novo_fluxo
from tools import explicacoes as ex

RAIZ = Path(__file__).resolve().parent
ACERVO = RAIZ / "tests" / "acervo"

#: Os códigos das sessões brutas de 24/10/2026 (`analises-esteira/2026-10-24/raw`) que não estão no acervo versionado,
#: e os dos PRs abertos (C4: o espelho do Miro). Ficam aqui porque as sessões brutas não estão no repositório.
CODIGOS_FORA_DO_ACERVO = [
    ("adequacao_status", "alinhamento_curricular"), ("adequacao_status", "carga_cognitiva"),
    ("adequacao_status", "demanda-cognitiva"), ("adequacao_status", "evidencia-aprendizagem"),
    ("adequacao_status", "sem-artefato-observavel"), ("avaliacao_status", "4.1"),
    ("conteudo_aprovado_resumido_status", "decisao-atribuida-ao-po"), ("contrato_produto_status", "saeb-ausente"),
    ("diagnostico_status", "9.1"), ("diagnostico_status", "F7"), ("fidelidade_nucleo_status", "sem-prova"),
    ("fidelidade_status", "pedido-violado"), ("gate_estrutural_status", "4.6"), ("gate_estrutural_status", "5.6"),
    ("gate_estrutural_status", "7.4"), ("gate_estrutural_status", "9.1(i)"), ("gate_final_status", "F2"),
    ("miro_status", "miro-indisponivel"), ("miro_status", "miro-board-incompleto"),
]


def _estado(missao: str) -> Dict[str, Any]:
    return json.loads((ACERVO / missao / "estado.json").read_text(encoding="utf-8"))


def _missoes():
    return sorted(p.name for p in ACERVO.iterdir() if (p / "estado.json").exists())


# --------------------------------------------------------------------------- o catálogo cobre os códigos reais
def test_catalogo_cobre_todo_codigo_gravado_no_acervo():
    """Cada achado dos envelopes das 15 missões tem explicação que não é a genérica."""
    sem = []
    for missao in _missoes():
        for chave, env in _estado(missao).items():
            if not (chave.endswith("_envelope") and isinstance(env, dict)):
                continue
            gate = chave[: -len("_envelope")]
            for a in env.get("achados") or []:
                if isinstance(a, dict) and ex.explicar(a, gate).generica:
                    sem.append((missao, gate, a.get("codigo")))
    assert sem == [], f"códigos sem explicação: {sem}"


def test_catalogo_cobre_os_codigos_que_os_gates_recalculam_no_acervo():
    """A linha de base da regressão tem os códigos que os gates determinísticos dão hoje sobre o acervo."""
    base = json.loads((ACERVO / "linha-de-base.json").read_text(encoding="utf-8"))
    pares = [(g, c) for gates in base.values() for g, v in gates.items() for c in v.get("codigos", [])
             if c != "?"]  # «?» é o achado sem código: a regressão o grava assim, e a explicação vem do verificador
    assert ex.codigos_sem_explicacao(pares) == []


def test_catalogo_cobre_as_sessoes_brutas_e_os_prs_abertos():
    assert ex.codigos_sem_explicacao(CODIGOS_FORA_DO_ACERVO) == []


#: Os construtores de achado dos verificadores: o código vai como argumento, não num dicionário literal.
_CONSTRUTORES = {"falha", "falta", "_achado", "atencao", "bloqueio", "_falha", "_bloqueio", "_atencao"}
#: Onde o achado grava o campo da ficha técnica, que `rastro.relatorio_manifesto` usa como código.
_ARQUIVOS_DA_FICHA = {"rastro.py", "ambiente.py", "secoes.py"}


def _assinatura(fn: ast.FunctionDef):
    nomes = [a.arg for a in fn.args.args]
    chave = "codigo" if "codigo" in nomes else "campo" if "campo" in nomes else None
    if chave is None:
        return None
    padroes = {n: d.value for n, d in zip(nomes[len(nomes) - len(fn.args.defaults):], fn.args.defaults)
               if isinstance(d, ast.Constant)}
    i_sev = next((nomes.index(n) for n in ("severidade", "sev") if n in nomes), None)
    if fn.name.lstrip("_") in ("bloqueio", "falta"):
        fixa = "bloqueio"
    elif fn.name.lstrip("_") == "atencao":
        fixa = "atencao"
    elif i_sev is None:
        # a severidade está no dicionário que o construtor monta — constante ou calculada («?», pode ser bloqueio)
        sevs = {v.value if isinstance(v, ast.Constant) else "?" for n in ast.walk(fn) if isinstance(n, ast.Dict)
                for k, v in zip(n.keys, n.values) if isinstance(k, ast.Constant) and k.value == "severidade"}
        fixa = "?" if (not sevs or "?" in sevs) else "/".join(sorted(sevs))
    else:
        fixa = None
    return {"chave": chave, "i": nomes.index(chave), "i_sev": i_sev, "padrao": padroes.get("severidade"),
            "fixa": fixa}


def codigos_emitidos():
    """`[(código, verificador, severidade, onde)]` de todo achado com código literal em `tools/`, `agents/` e
    `pipeline/`: dicionários `{"codigo": …}` e chamadas `falha(…)`, `_achado(…)`, `bloqueio(…)`, `atencao(…)`,
    `falta(…)`. A severidade «?» é a calculada na hora (ESTEIRA_ESTRITA, por exemplo): pode ser bloqueio. O campo da
    ficha técnica (`"campo": …`) sai com o verificador `manifesto_status`, onde ele é o código."""
    saida = []
    for pasta in ("tools", "agents", "pipeline"):
        for arq in sorted((RAIZ / pasta).rglob("*.py")):
            arvore = ast.parse(arq.read_text(encoding="utf-8"))

            def visita(no, locais):
                if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
                    locais = dict(locais)
                    for filho in ast.iter_child_nodes(no):
                        if isinstance(filho, (ast.FunctionDef, ast.AsyncFunctionDef)) and filho.name in _CONSTRUTORES:
                            sig = _assinatura(filho)
                            if sig:
                                locais[filho.name] = sig
                if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id in locais:
                    sig = locais[no.func.id]
                    arg = no.args[sig["i"]] if len(no.args) > sig["i"] else next(
                        (k.value for k in no.keywords if k.arg == sig["chave"]), None)
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        sev = sig["fixa"] or sig["padrao"]
                        dado = no.args[sig["i_sev"]] if sig["i_sev"] is not None and len(no.args) > sig["i_sev"] \
                            else next((k.value for k in no.keywords if k.arg in ("severidade", "sev")), None)
                        if dado is not None:
                            sev = dado.value if isinstance(dado, ast.Constant) else "?"
                        gate = "manifesto_status" if sig["chave"] == "campo" else ""
                        saida.append((arg.value, gate, sev or "?", f"{arq.name}:{no.lineno}"))
                if isinstance(no, ast.Dict):
                    d = {k.value: v for k, v in zip(no.keys, no.values) if isinstance(k, ast.Constant)}
                    sv = d.get("severidade")
                    sev = sv.value if isinstance(sv, ast.Constant) else "?"
                    if isinstance(d.get("codigo"), ast.Constant) and isinstance(d["codigo"].value, str):
                        saida.append((d["codigo"].value, "", sev, f"{arq.name}:{no.lineno}"))
                    if (arq.name in _ARQUIVOS_DA_FICHA and isinstance(d.get("campo"), ast.Constant)
                            and isinstance(d["campo"].value, str)):
                        saida.append((d["campo"].value, "manifesto_status", sev, f"{arq.name}:{no.lineno}"))
                for filho in ast.iter_child_nodes(no):
                    visita(filho, locais)

            visita(arvore, {})
    return saida


def test_codigos_do_codigo_fonte_tem_explicacao():
    """Todo código que um verificador escreve — em dicionário ou pelo construtor de achado — tem a entrada dele: o texto
    genérico é a rede, não o caminho. Até a revisão do PR #82 o teste só lia dicionários literais, e 138 códigos
    passados a `falha(…)`/`_achado(…)` caíam no genérico (`kpi-sem-evento`, `pq-faltando`, `prototipo-nao-abre`…)."""
    emitidos = codigos_emitidos()
    vistos = {c for c, *_ in emitidos}
    # a varredura enxerga os construtores, não só os dicionários
    assert {"kpi-sem-evento", "pq-faltando", "prototipo-nao-abre", "habilidade-sem-medida", "numero-divergente",
            "evento-sem-leitor", "secao_ds", "letramento", "eixo-divergente"} <= vistos
    assert len(vistos) > 300
    sem = sorted({(g, c, onde) for c, g, sev, onde in emitidos
                  if ex.explicar({"codigo": c, "severidade": sev, "resumo": "x"}, g).generica})
    assert sem == [], f"códigos sem explicação no catálogo: {sem}"


_SO_SEM_TRAVA = re.compile(r"[Nn]ão trava|não bloqueia|siga com ele registrado|siga e registre|não impede")


def test_achado_que_impede_seguir_nunca_diz_que_nao_trava_nem_manda_ao_de_acordo():
    """Com 🔴 o «De acordo» não aparece (`passagem.acoes_possiveis`). Revisão do PR #82: `letramento` e
    `eixo-divergente`, emitidos como bloqueio por `tools/bncc.py`, saíam com «🔴 Impede seguir» e, logo abaixo, «Não trava
    a etapa»; `secao_ds` (rastro e ambiente) e `decisao-atribuida-ao-po` (decisoes) também."""
    emitidos = codigos_emitidos()
    talvez_bloqueio = {(c, g) for c, g, sev, _ in emitidos if sev in ("bloqueio", "?")}
    assert {("letramento", ""), ("eixo-divergente", ""), ("secao_ds", "manifesto_status"),
            ("decisao-atribuida-ao-po", ""), ("numero-sem-origem", "")} <= talvez_bloqueio
    errados = []
    for c, g in sorted(talvez_bloqueio):
        i = ex.item({"codigo": c, "severidade": "bloqueio", "resumo": "x"}, g, "🔴")
        e = i.explicacao
        fazer = i.o_que_fazer
        if (_SO_SEM_TRAVA.search(" ".join((e.o_que_aconteceu, e.por_que_importa, fazer)))
                or "de acordo" in fazer.replace(ex.NO_VERMELHO, "")):
            errados.append((c, g, fazer))
    assert errados == []
    # o mesmo código em 🟡 continua dizendo que não trava, quando é o caso
    assert "Não trava a etapa" in ex.item({"codigo": "letramento", "severidade": "atencao", "resumo": "x"},
                                          "bncc_status", "🟡").o_que_fazer


def test_letramento_explica_o_achado_real_no_ef_e_no_em():
    ef = {"severidade": "bloqueio", "codigo": "letramento", "resumo": (
        "Nenhuma habilidade de letramento digital (Cultura Digital) compatível com a série. É o único recorte da BNCC "
        "que bloqueia — e falta.")}
    i = ex.item(ef, "bncc_status", "🔴")
    assert i.explicacao.titulo == "Falta habilidade de letramento digital da série"
    assert "Ensino Médio" not in i.explicacao.o_que_aconteceu and "proposta" not in i.explicacao.o_que_aconteceu
    assert "Não trava" not in i.o_que_fazer and "de acordo" not in i.o_que_fazer
    em = {"severidade": "atencao", "codigo": "letramento", "resumo": (
        "Nenhuma habilidade da lista proposta de letramento digital do EM. O anexo não tem eixo no Médio, então isto "
        "não bloqueia — a avaliação pedagógica decide.")}
    i = ex.item(em, "bncc_status", "🟡")
    assert i.explicacao.titulo == "Nenhuma habilidade da lista proposta de letramento digital do Ensino Médio"
    assert "pedagogia" in i.o_que_fazer and "Não trava a etapa" in i.o_que_fazer
    # a família EM13 «proposta» é outro achado, com a entrada própria
    em13 = ex.item({"severidade": "atencao", "codigo": "EM13CO20", "resumo": "`EM13CO20` conta como letramento "
                    "digital pela leitura **proposta** do EM (sem eixo oficial) — validar com pedagogia."},
                   "bncc_status", "🟡")
    assert em13.explicacao.titulo == "Habilidade do Ensino Médio lida como letramento digital"
    assert em13.explicacao is not ex.CATALOGO["letramento"]


def test_bncc_real_letramento_e_eixo_divergente_no_cartao():
    """O achado que `tools/bncc.py` emite de verdade numa missão do EF (o caso da exp02ef1b, que volta à esteira): os
    dois saem 🔴, e o texto não diz o contrário."""
    from tools import bncc

    spec = ("## 0. Identificação\n- `series: [\"6EF\"]`\n\n## 11. Currículo\n"
            "- `EF06CO07` — Cultura Digital: texto qualquer.\n")
    achados = {a["codigo"]: a for a in bncc.validar_spec(spec)["achados"]}
    assert achados["letramento"]["severidade"] == achados["eixo-divergente"]["severidade"] == "bloqueio"
    for codigo, titulo in (("letramento", "Falta habilidade de letramento digital da série"),
                           ("eixo-divergente", "Habilidade classificada no eixo errado")):
        i = ex.item(achados[codigo], "bncc_status", "🔴")
        assert (i.severidade, i.explicacao.titulo) == ("bloqueio", titulo)
        assert "Não trava" not in i.o_que_fazer and "de acordo" not in i.o_que_fazer


def test_secao_ds_explica_o_bloqueio_e_a_pendencia_de_plataforma():
    legada = {"severidade": "bloqueio", "codigo": "secao_ds", "agente_responsavel": "produto", "resumo": (
        "`unoogaleria` é seção legada: missão nova não reproduz a identidade de app de terceiro (ADR-133 a 138) e usa "
        "`unoovista` — veja `ambientes.md`.")}
    i = ex.item(legada, "manifesto_status", "🔴")
    assert i.explicacao.titulo == "O ambiente da missão não pode seguir como está" and i.quem == ex.PO
    assert "Não trava" not in i.o_que_fazer
    ponte = {"severidade": "atencao", "codigo": "secao_ds", "agente_responsavel": "plataforma",
             "resumo": "`unoovista` existe no DS mas não tem ponte em `@edu/ui`."}
    i = ex.item(ponte, "manifesto_status", "🟡")
    assert i.explicacao.titulo == "Seção nova do design system" and i.quem == ex.DEV
    # o campo «produto» da ficha não é pendência de produto
    campo = ex.explicar({"severidade": "bloqueio", "codigo": "produto", "resumo": "x"}, "manifesto_status")
    assert campo.titulo.startswith("Ficha técnica da missão") and not campo.generica


def test_decisao_atribuida_ao_po_diz_o_caminho_que_existe():
    """⛔ sem registro do PO: o de acordo não aparece, e o pedido de Refazer é o registro que o faz cair para ⚠️
    (`decisoes.ha_registro_do_po`). ⚠️ com registro: confirmar no de acordo."""
    from tools import decisoes

    texto = "O PO decidiu manter 3 opções na escolha da etapa 5."
    sem, = decisoes.achados(texto, "O one-pager", registro_do_po=False)
    com, = decisoes.achados(texto, "O one-pager", registro_do_po=True)
    assert (sem["severidade"], com["severidade"]) == ("bloqueio", "atencao")
    i = ex.item(sem, "contrato_produto_status", "🔴")
    assert "use **Refazer** dizendo isso" in i.o_que_fazer and "de acordo" not in i.o_que_fazer
    assert "não tem nenhum pedido nem parecer do PO" in i.explicacao.o_que_aconteceu
    i = ex.item(com, "contrato_produto_status", "🟡")
    assert "confirme no comentário do de acordo" in i.o_que_fazer
    assert decisoes.ha_registro_do_po({"pedidos_do_po": [{"texto": "a decisão é minha"}]})


def test_rede_do_o_que_fazer_com_bloqueio():
    """A entrada sem variante de bloqueio perde o que só vale sem trava e ganha o caminho que existe."""
    exp = ex._x("t", "a", "b", "Confira o valor e registre no de acordo. Não trava a etapa.", ex.PO)
    assert ex.o_que_fazer(exp, ex.ATENCAO) == exp.o_que_fazer
    assert ex.o_que_fazer(exp, ex.BLOQUEIO) == ex.NO_VERMELHO
    exp = ex._x("t", "a", "b", "Use **Refazer** no parecer de produto, citando o ponto, ou siga com ele registrado.")
    assert ex.o_que_fazer(exp, ex.BLOQUEIO) == "Use **Refazer** no parecer de produto, citando o ponto."


def test_codigo_desconhecido_cai_no_generico_honesto_com_o_detalhe():
    achado = {"codigo": "codigo-que-ninguem-conhece", "resumo": "Texto técnico do verificador.", "severidade": "atencao"}
    exp = ex.explicar(achado, "prd_status")
    assert exp.generica and exp.titulo == "Ponto técnico apontado pela esteira"
    assert "ainda não tem explicação em linguagem simples" in exp.o_que_aconteceu
    assert exp.texto_e_o_caso  # o texto original sai à vista, não só nos detalhes
    assert ex.codigos_sem_explicacao([("prd_status", "codigo-que-ninguem-conhece")]) == [
        ("prd_status", "codigo-que-ninguem-conhece")]
    assert ex.quem_resolve(achado, "prd_status", exp) == ex.DEV


def test_familias_de_codigo():
    bncc = ex.explicar({"codigo": "EM13CO20", "resumo": "`EM13CO20` conta como letramento digital pela leitura "
                                                        "**proposta** do EM (sem eixo oficial)"}, "bncc_status")
    assert bncc.titulo == "Habilidade do Ensino Médio lida como letramento digital"
    perdido = ex.explicar({"codigo": "perdido-texto_tela-copy"}, "rastreabilidade_status")
    assert perdido.titulo == "Nem tudo o que foi aprovado chegou aos textos das telas" and perdido.quem == ex.DESIGN
    assert ex.explicar({"codigo": "perdido-estado-prd"}, "rastreabilidade_dev_status").quem == ex.DEV
    # critério numerado e id de juiz: a explicação é a do revisor, e o texto do juiz é o caso
    for gate, codigo in (("gate_estrutural_status", "9.1(i)"), ("juiz_perguntas_status", "J3"),
                         ("comite_canal_a_status", "A2-01"), ("design_status", "D8b")):
        exp = ex.explicar({"codigo": codigo, "resumo": "x"}, gate)
        assert not exp.generica and exp.texto_e_o_caso, (gate, codigo)
    # o padrão do juiz de adequação vence o código livre
    assert ex.explicar({"codigo": "2", "padrao": "repertorio-nao-declarado"}, "adequacao_status").titulo == \
        "A missão supõe algo que a criança pode não saber"
    assert ex.explicar({"codigo": "F7"}, "gate_final_status").quem == ex.PO
    assert ex.explicar({"codigo": "P3-notificacao-onisciente-plataforma"}, "profundidade_status").titulo == \
        "Ponto fraco de profundidade pedagógica"
    # banca sem código: o revisor
    assert ex.explicar({"resumo": "x", "dimensao": "banca_produto_pedagogia"}, "banca_produto_status").texto_e_o_caso


def test_quem_resolve_pelo_dono_do_trecho_ou_pela_etapa():
    rotulo = {"codigo": "rotulo-divergente", "resumo": "x"}
    assert ex.quem_resolve({**rotulo, "agente_responsavel": "jornada"}, "consistencia_status") == ex.DESIGN
    assert ex.quem_resolve({**rotulo, "agente_responsavel": "prd-writer"}, "prd_status") == ex.DEV
    assert ex.quem_resolve({"codigo": "nao-tratado", "etapa": "produto"}, "fidelidade_nucleo_status") == ex.PO
    assert ex.quem_resolve({"codigo": "nao-tratado", "etapa": "design"}, "fidelidade_design_status") == ex.DESIGN
    assert ex.quem_resolve({"codigo": "juiz-sem-voto"}, "profundidade_status") == ex.ESTEIRA


def test_severidade_em_palavras():
    assert ex.severidade_em_palavras("bloqueio") == ("🔴", "Impede seguir até ser resolvido")
    assert ex.severidade_em_palavras("atencao") == ("🟡", "Pode seguir, mas alguém precisa conferir")
    assert ex.severidade_em_palavras("decisao_humana")[0] == "🧑"
    assert "impedimento" in ex.SEMAFORO_EM_PALAVRAS["⛔"]


# --------------------------------------------------------------------------- os três exemplos do PR (tom)
def test_os_tres_exemplos_reais_do_pr():
    """Um 🔴 da montagem do PRD, um 🟡 de fidelidade e um ⛔ de decisão atribuída ao PO, das sessões reais."""
    montagem = {"severidade": "bloqueio", "codigo": "hipotese-diverge", "resumo": (
        "A H1 do §17 do one-pager não tem número, e o PRD lhe dá 180 s: «- **H1 (Usabilidade Nativa)**: Estudantes do "
        "5º ano executam o verbo nativo de encaminhar via bottom-sheet sem necessidade de instruções ext». Meta de "
        "hipótese é decisão do PO: copie a hipótese do §17 com as palavras dela, ou marque `[PROPOSTA — validar com "
        "PO: …]`.")}
    i = ex.item(montagem, "montagem_prd_status", "🔴")
    assert (i.explicacao.titulo, i.quem, i.severidade) == ("A meta da hipótese mudou no caminho", ex.PO, "bloqueio")
    assert i.trechos[0].startswith("- **H1 (Usabilidade Nativa)**")

    fidelidade = {"id": "F1", "severidade": "atencao", "codigo": "nao-tratado", "etapa": "produto", "resumo": (
        "Pedido do PO sem prova de que foi aplicado: «Vamos fazer os seguintes ajustes: ⚠️ Explicitar que o estudante "
        "não possui botão de reinício avulso em tela, dependendo exclusivamente de nova rodada disparada pelo "
        "professor.». O documento nucleo_narrativo não trata da ausência de botão de reinício avulso.")}
    i = ex.item(fidelidade, "fidelidade_nucleo_status", "🟡")
    assert (i.explicacao.titulo, i.quem) == ("Pedido do PO sem sinal de que foi feito", ex.PO)
    assert i.trechos == ["Vamos fazer os seguintes ajustes: ⚠️ Explicitar que o estudante não possui botão de reinício "
                         "avulso em tela, dependendo exclusivamente de nova rodada disparada pelo professor."]

    atribuida = {"severidade": "bloqueio", "codigo": "decisao-atribuida-ao-po", "resumo": (
        "O one-pager: 2 decisão(ões) atribuída(s) ao PO, e a sessão não tem nenhum parecer, pedido ou correção do PO. "
        "O agente não decide no lugar dele: reescreva cada uma como `[PROPOSTA — validar com PO: <o que foi decidido> "
        "· por quê]` — a etapa sai 🟡 e o PO revisa.\n"
        "    - «5. **Tetos de palavras cravados (homologados pelo PO):** 60 palavras por balão»\n"
        "    - «O PO decidiu manter 3 opções na escolha da etapa 5»")}
    i = ex.item(atribuida, "contrato_produto_status", "🔴")
    assert (i.explicacao.titulo, i.quem) == ("Decisão escrita como se fosse do PO", ex.PO)
    assert i.trechos == ["5. **Tetos de palavras cravados (homologados pelo PO):** 60 palavras por balão",
                         "O PO decidiu manter 3 opções na escolha da etapa 5"]


# --------------------------------------------------------------------------- trechos inteiros
def test_trechos_saem_inteiros_com_aspas_aninhadas_e_listas():
    longo = "palavra " * 400
    achado = {"resumo": f"O texto «{longo.strip()}» e «a «b» c». Trecho: `linha do QA inteira`\n"
                        "    - «- **item 1**»\n    - item 2",
              "citacao": "citação do juiz"}
    ts = ex.trechos(achado)
    assert ts[0] == "citação do juiz"
    assert "linha do QA inteira" in ts and longo.strip() in ts and "**item 1**" not in ts
    assert "- **item 1**" in ts and "item 2" in ts
    # aspas dentro de aspas são um trecho só, e o item recuado não vira trecho de novo pelas aspas dele
    assert "a «b» c" in ts and "b" not in ts and "«- **item 1**»" not in ts


def test_linha_de_diff_dita_em_palavras_e_linha_do_rastro_e_o_trecho():
    diff = {"resumo": "D9 alterou fora do bloco 14:\n    -| A | velho |\n    +| A | novo |"}
    assert ex.trechos(diff) == ["Como está: | A | velho |", "Como o agente quis deixar: | A | novo |"]
    rastro = {"codigo": "humano", "resumo": "- `[ABERTO — dono: editorial: confirmar EF15LP14 na grade do 1º ano]`"}
    assert ex.trechos(rastro) == ["[ABERTO — dono: editorial: confirmar EF15LP14 na grade do 1º ano]"]


def test_rebaixado_pela_linha_de_base_vira_nota_em_palavras():
    a = {"severidade": "atencao", "severidade_original": "bloqueio", "codigo": "exigencia-dispensada",
         "resumo": "[não causado pela correção — não ligado às trocas] O juiz tratou como contexto: «Frase.»."}
    assert "já existia antes da última correção" in ex.nota_de_rebaixamento(a)
    assert ex.sem_prefixo(a["resumo"]).startswith("O juiz tratou")
    assert ex.trechos(a) == ["Frase."]


def test_itens_do_semaforo_ordem_repeticao_e_verificador_sem_detalhe():
    estado = {
        "fidelidade_status": "amarelo", "fidelidade_nucleo_status": "amarelo", "gate_final_status": "bloqueado",
        "fidelidade_status_envelope": {"achados": [{"severidade": "atencao", "codigo": "nao-tratado", "resumo": "R"}]},
        "fidelidade_nucleo_status_envelope": {"achados": [
            {"severidade": "atencao", "codigo": "nao-tratado", "resumo": "R"},
            {"severidade": "bloqueio", "codigo": "pedido-violado", "resumo": "P"}]},
    }
    semaforo = {"fidelidade_status": "🟡", "fidelidade_nucleo_status": "🟡", "gate_final_status": "🔴"}
    itens = ex.itens_do_semaforo(estado, semaforo)
    # o bloqueio dentro do verificador 🟡 vira decisão de pessoa (revisão do PR #82); o 🔴 sem detalhe impede seguir
    assert [i.severidade for i in itens] == ["bloqueio", "decisao_humana", "atencao"]
    repetido = next(i for i in itens if i.achado.get("codigo") == "nao-tratado")
    assert repetido.tambem_em == ["fidelidade_nucleo_status"]
    sem_detalhe = next(i for i in itens if i.gate == "gate_final_status")
    assert "sem dizer por quê" in sem_detalhe.explicacao.titulo
    assert ex.contagem(itens) == "1 impede seguir · 1 pede decisão · 1 para conferir"
    assert ex.contagem(itens[:1] * 2) == "2 impedem seguir"


# --------------------------------------------------------------------------- passagem.py não corta
def _estado_com_pendencias(n: int, tamanho: int) -> Dict[str, Any]:
    achados = [{"severidade": "decisao_humana", "codigo": "conflito-pedido-regra",
                "resumo": f"Pendência {k}: " + "x" * tamanho + " fim"} for k in range(n)]
    return {"gate_final_status": "amarelo", "gate_final_status_envelope": {"achados": achados}}


def test_pendencia_da_conferencia_leva_o_assunto_inteiro():
    itens = passagem.pendencias_de_conferencia(_estado_com_pendencias(1, 1200), contrato_aberto=False)
    assert len(itens) == 1 and itens[0]["assunto"].endswith(" fim") and len(itens[0]["assunto"]) > 1200


def test_conferir_leitura_lista_todos_os_que_faltam_inteiros():
    itens = passagem.pendencias_de_conferencia(_estado_com_pendencias(7, 300), contrato_aberto=False)
    with pytest.raises(DecisaoInvalida) as exc:
        passagem.conferir_leitura(itens, {}, [])
    msg = str(exc.value)
    assert "sem leitura confirmada" in msg and "e mais" not in msg
    assert all(i["assunto"] in msg for i in itens)
    registro = passagem.conferir_leitura(itens, {}, [i["id"] for i in itens])
    assert all(r["assunto"].endswith(" fim") for r in registro)


def test_devolucao_automatica_leva_todos_os_tickets_inteiros():
    tickets = [{"id": f"QA-{k}", "codigo": "gate-estrutural", "resumo": f"Ticket {k} " + "y" * 600 + " fim"}
               for k in range(15)]
    fluxo = {**novo_fluxo(), "etapa": "design", "situacao": passagem.GERANDO}
    novo = passagem.concluir_execucao(fluxo, True, {passagem.KEY_DEVOLUCOES_A_PRODUTO: {"design_status": tickets}})
    comentario = novo["pareceres"][-1]["comentario"]
    assert all(t["resumo"] in comentario for t in tickets) and "… e mais" not in comentario


def test_tickets_que_comecam_igual_nao_viram_um_so():
    comum = "z" * 200
    estado = {passagem.KEY_DEVOLUCOES_A_PRODUTO: {"design_status": [
        {"id": "T", "resumo": comum + " primeiro"}, {"id": "T", "resumo": comum + " segundo"}]}}
    assert len(passagem.devolucoes_a_produto(estado)) == 2


def test_lista_inteira():
    assert passagem.lista_inteira(["a  b", "", "c\nd"]) == "\n- a b\n- c d"


# --------------------------------------------------------------------------- nenhuma função de exibição corta
def test_funcoes_de_exibicao_nao_cortam_texto():
    import app

    funcoes = [app._texto_da_missao, app._lista_com_ver_todos, app._render_detalhes_tecnicos,
               app._render_item_explicado, app._render_achados_explicados, app._render_motivos_do_semaforo,
               app._render_conferencia_de_leitura, app._render_contrato_aberto, ex.trechos, ex.item,
               ex.itens_do_semaforo, ex.explicacao_de_pendencia, passagem.pendencias_de_conferencia,
               passagem.conferir_leitura, passagem._devolver_a_produto, passagem.lista_inteira]
    for f in funcoes:
        fonte = inspect.getsource(f)
        # o hash que dá o id do item (`hexdigest()[:10]`) não é texto de ninguém
        assert not re.search(r"(?<!hexdigest\(\))\[\s*:\s*\d+\s*\]", fonte), f"{f.__name__} corta texto"
        assert "[:n]" not in fonte or f is app._lista_com_ver_todos, f.__name__


# --------------------------------------------------------------------------- o cartão no app (AppTest)
def _sessao_em_disco(tmp_path: Path, estado: Dict[str, Any], fluxo: Dict[str, Any]) -> Path:
    run_dir = tmp_path / "20261025-090000-session_explica"
    run_dir.mkdir()
    (run_dir / "estado.json").write_text(json.dumps(estado), encoding="utf-8")
    (run_dir / "conversa.json").write_text(json.dumps({"session_id": "s", "fluxo": fluxo}), encoding="utf-8")
    return run_dir


def _roteiro_do_cartao():
    import json
    import os
    from pathlib import Path

    import app
    import streamlit as st
    from tools.auth import Sessao

    papel = os.environ["EXPLICA_PAPEL"]
    st.session_state["auth_sessao"] = Sessao(usuario=papel, papel=papel, emitida_em=0, expira_em=1e12, jti="x")
    run_dir = Path(os.environ["EXPLICA_RUN_DIR"])
    fluxo = json.loads((run_dir / "conversa.json").read_text(encoding="utf-8"))["fluxo"]
    app._render_trilha(fluxo)
    app._painel_decisao(run_dir, fluxo, {})


def _textos(at) -> str:
    partes = [m.value for m in at.markdown] + [c.value for c in at.caption] + [w.value for w in at.warning]
    partes += [c.label for c in at.checkbox] + [e.label for e in at.expander] + [t.label for t in at.toggle]
    return "\n".join(str(p) for p in partes)


def _rodar(tmp_path, monkeypatch, estado, etapa, papel):
    pytest.importorskip("streamlit.testing.v1")
    from streamlit.testing.v1 import AppTest

    run_dir = _sessao_em_disco(tmp_path, estado, {**novo_fluxo(), "etapa": etapa, "situacao": AGUARDANDO})
    monkeypatch.setenv("EXPLICA_RUN_DIR", str(run_dir))
    monkeypatch.setenv("EXPLICA_PAPEL", papel)
    at = AppTest.from_function(_roteiro_do_cartao, default_timeout=120)
    at.run()
    assert not at.exception, at.exception
    return at


def test_cartao_do_de_acordo_de_produto_explica_com_estado_real(tmp_path, monkeypatch):
    """O cartão de produto da exp02ef1b: legenda em palavras, grupo do PO aberto, explicação simples antes do código."""
    estado = _estado("exp02ef1b-4fd72a9a")
    at = _rodar(tmp_path, monkeypatch, estado, "produto", "produto")
    texto = _textos(at)
    assert "🔴 impede seguir até ser resolvido · 🟡 pode seguir, mas alguém precisa conferir" in texto
    assert "🧑 Para o PO decidir" in texto
    assert "Propostas esperando a homologação do PO" in texto
    assert "**O que fazer:**" in texto and "Por que importa:" in texto
    assert "Quem resolve: **PO (produto)**" in texto
    assert any(e.label == "🔧 Detalhes técnicos" for e in at.expander)
    # o código cru não é mais a primeira coisa que o PO lê
    assert not any(m.value.startswith(("❌ `", "⚠️ `", "🧑 `")) for m in at.markdown)


def test_semaforo_do_design_com_estado_real_e_ver_todos(tmp_path, monkeypatch):
    estado = _estado("exp02em1b-60cfa7f4")
    at = _rodar(tmp_path, monkeypatch, estado, "design", "design")
    texto = _textos(at)
    assert "🎨 Para o design" in texto and "Linhas do documento sumiram ao ser reescrito" in texto
    ver_todos = [t for t in at.toggle if t.label.startswith("Ver todos (")]
    assert ver_todos, "a lista longa precisa do «Ver todos»"
    antes = len(at.markdown)
    ver_todos[0].set_value(True).run()
    assert not at.exception and len(at.markdown) > antes


def test_cartao_mostra_o_texto_longo_inteiro_e_a_pendencia_inteira(tmp_path, monkeypatch):
    longo = "Pedido do PO: " + " ".join(f"palavra{k}" for k in range(500)) + " fim do pedido."
    estado = {"one_pager": "x", "fidelidade_nucleo_status": "amarelo",
              "fidelidade_nucleo_status_envelope": {"achados": [
                  {"severidade": "atencao", "codigo": "nao-tratado", "etapa": "produto", "resumo": f"Sem prova: «{longo}»."},
                  {"severidade": "decisao_humana", "codigo": "conflito-pedido-regra", "etapa": "produto",
                   "resumo": f"Conflita com a regra: «{longo} 2»."}]}}
    at = _rodar(tmp_path, monkeypatch, estado, "produto", "produto")
    texto = _textos(at)
    assert f"> {longo}" in texto  # o trecho da missão, inteiro
    assert any(c.label.startswith("Li e decidi:") and c.label.endswith(f"«{longo} 2».") for c in at.checkbox)
    assert "Seu pedido esbarra numa regra da esteira" in texto


def test_login_continua_de_pe(tmp_path, monkeypatch):
    """O app inteiro, sem sessão: só o formulário de login, sem exceção; com a senha certa, entra."""
    pytest.importorskip("streamlit.testing.v1")
    from streamlit.testing.v1 import AppTest

    from tools.auth import gerar_credenciais

    senhas, contas, _ = gerar_credenciais()
    monkeypatch.setenv("AUTH_CREDENCIAIS", json.dumps(contas))
    monkeypatch.setenv("AUTH_SEGREDO_JWT", "s" * 48)
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
    at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=120)
    at.run()
    assert not at.exception, at.exception
    assert [b.label for b in at.button if b.label == "Entrar"] or any(
        getattr(b, "label", "") == "Entrar" for b in at.get("button"))
    usuario = next(iter(senhas))
    at.text_input[0].set_value(usuario)
    at.text_input[1].set_value(senhas[usuario])
    next(b for b in at.button if b.label == "Entrar").click().run()
    assert not at.exception, at.exception
    assert at.session_state["auth_sessao"].usuario == usuario


def test_matriz_de_rastreabilidade_grava_a_lista_inteira_para_o_cartao():
    """O resumo da matriz traz só 6 itens de 70 caracteres (volta aos autores no retrabalho); o cartão mostra todos,
    inteiros, pelo campo `faltando`. A exp03em1b tem 15 itens faltando; a exp02em1b caiu para 6 depois que a C4 (#81)
    tirou as lacunas e as falas dos textos de tela."""
    from tools import rastreabilidade

    estado = _estado("exp03em1b-b2e7b4a3")
    achados = [a for a in rastreabilidade.matriz(estado)["achados"] if len(a.get("faltando") or []) > 6]
    assert achados, "o acervo tem matriz com mais de 6 itens faltando"
    for a in achados:
        ts = ex.trechos(a)
        assert len(ts) == len(a["faltando"])
        assert all(f["texto"] in t for f, t in zip(a["faltando"], ts))


def test_rastro_leva_a_linha_e_o_marcador_inteiros_ao_cartao():
    """`rastro.varrer_lacunas` cortava a linha em 200 caracteres e o marcador em 160 (revisão do PR #82): as linhas
    «[ABERTO — dono: PO: …» das sessões de 24/10/2026 passam disso, e o cartão as mostrava partidas no meio da palavra."""
    from tools import rastro

    pergunta = "confirmar com a coordenação pedagógica se a habilidade EF15AR05 entra na grade do 1º ano " * 4
    linha = f"- Tempo de tela por etapa [ABERTO — dono: PO: {pergunta.strip()}] fica para o parecer."
    assert len(linha) > 300
    r = rastro.varrer_lacunas([{"chave": "spec_missao", "rotulo": "spec", "etapa_padrao": "produto"}],
                              {"spec_missao": "# Spec\n\n" + linha + "\n"}, etapa_corrente="produto")
    achado, = r["achados"]
    assert achado["contexto"] == linha and pergunta.strip() in achado["trecho"]
    relatorio = rastro.relatorio_lacunas(r, "Rastro da spec", "exp00ef1b")
    assert pergunta.strip() in relatorio
    envelope = json.loads(relatorio[relatorio.index("{", relatorio.rindex("```json")):relatorio.rindex("```")])
    assert envelope["achados"][0]["resumo"] == linha


# --------------------------------------------------------------------------- revisão 2 do PR #82
# o envelope real da session_274a2e75 (exp03ef1b, 07/10/2026): adequação 🟡 com um achado do juiz em bloqueio
_ADEQUACAO_274A2E75 = {
    "agente": "adequacao-pedagogica", "missao": "exp03ef1b", "status": "aprovado_com_ressalvas", "placar": 16,
    "ajustes_exigidos": 1, "precisa_humano": False,
    "achados": [
        {"id": "E2-A1", "severidade": "bloqueio", "codigo": "demanda_cognitiva", "padrao": "repertorio-nao-declarado",
         "resumo": "ícone de raio isolado para ação/o quê exige abstração semiótica incompatível com 3º ano"},
        {"id": "E1-A1", "severidade": "atencao", "codigo": "alinhamento_curricular", "padrao": "verbo-desalinhado",
         "resumo": "habilidade EF03CO08 figura como foco primário mas tarefa é essencialmente decomposição EF03CO03"},
    ],
}
# o achado real da session_8ce9c32d (exp04ef1b, 25/09/2026): rastro de dev 🟡 com a pendência de produto em bloqueio
_RASTRO_8CE9C32D = {
    "agente": "rastro-lacunas", "status": "bloqueado", "veredito": "vermelho", "precisa_humano": True,
    "achados": [{"severidade": "bloqueio", "classe": "aberto", "codigo": "produto", "agente_responsavel": "produto",
                 "documento": "ambiente simulado",
                 "resumo": "- `[ABERTO — dono: produto: Ratificação formal do teto de texto entre 25 e 35 palavras por "
                           "resumo]` (§6) — Resolvido em "}],
}


def test_bloqueio_dentro_de_verificador_amarelo_vira_decisao_de_pessoa():
    """O juiz grava bloqueio dentro de envelope 🟡: o «De acordo» aparece, então o cartão não diz «Impede seguir»."""
    estado = {"adequacao_status": "amarelo", "adequacao_status_envelope": _ADEQUACAO_274A2E75}
    itens = ex.itens_do_semaforo(estado, {"adequacao_status": "🟡"}, "produto")
    raio = next(i for i in itens if i.achado["codigo"] == "demanda_cognitiva")
    assert raio.severidade == ex.DECISAO_HUMANA and raio.rebaixado_pelo_verificador
    assert "ficou 🟡" in raio.nota and "não impede seguir" in raio.nota
    assert raio.achado["severidade"] == "bloqueio", "o original continua nos detalhes técnicos"
    assert "ou siga com ele registrado" in raio.o_que_fazer and ex.NO_VERMELHO not in raio.o_que_fazer
    assert ex.contagem(itens) == "1 pede decisão · 1 para conferir"
    # no verificador 🔴, o mesmo achado continua impedindo seguir
    vermelho = ex.item(_ADEQUACAO_274A2E75["achados"][0], "adequacao_status", "🔴")
    assert vermelho.severidade == ex.BLOQUEIO and not vermelho.rebaixado_pelo_verificador and not vermelho.nota


def test_cartao_de_design_ou_dev_nao_manda_ao_refazer_de_produto():
    """No cartão de dev não há «Refazer de produto»: o caminho é o Refazer da etapa com o item mandado a Produto (D4)."""
    estado = {"rastro_lacunas_status": "amarelo", "rastro_lacunas_status_envelope": _RASTRO_8CE9C32D}
    (i,) = ex.itens_do_semaforo(estado, {"rastro_lacunas_status": "🟡"}, "dev")
    assert i.severidade == ex.DECISAO_HUMANA
    assert "Refazer** de produto" not in i.o_que_fazer
    assert "**Refazer** desta etapa com ela" in i.o_que_fazer and i.o_que_fazer.endswith(ex.PRODUTO_PELA_ETAPA)
    assert "mandar a Produto" in ex.PRODUTO_PELA_ETAPA and "**Devolver**" in ex.PRODUTO_PELA_ETAPA
    # no cartão de produto o botão existe, e o texto fica como está
    (p,) = ex.itens_do_semaforo(estado, {"rastro_lacunas_status": "🟡"}, "produto")
    assert "use **Refazer** de produto com ela" in p.o_que_fazer and ex.PRODUTO_PELA_ETAPA not in p.o_que_fazer
    # nenhuma entrada do catálogo sai com «Refazer de produto» em design ou dev, em qualquer severidade
    for exp in list(ex.CATALOGO.values()) + list(ex.PADROES.values()):
        for sev in ex.SEVERIDADE:
            for etapa in ("design", "dev"):
                assert "Refazer** de produto" not in ex.o_que_fazer(exp, sev, etapa)


def test_amarelo_que_manda_ao_de_acordo_avisa_quando_outro_ponto_e_vermelho():
    """Um 🔴 em qualquer verificador da etapa esconde o «De acordo» (`passagem.acoes_possiveis`)."""
    estado = {
        "rastro_lacunas_status": "amarelo", "dev_status": "bloqueado",
        "rastro_lacunas_status_envelope": {"achados": [
            {"severidade": "decisao_humana", "codigo": "humano", "resumo": "- `[ABERTO — dono: produto: limiar]`"}]},
    }
    semaforo = passagem.semaforo_da_etapa(estado, "dev")
    assert semaforo == {"dev_status": "🔴", "rastro_lacunas_status": "🟡"}
    assert passagem.DE_ACORDO not in passagem.acoes_possiveis(
        {**novo_fluxo(), "etapa": "dev", "situacao": AGUARDANDO}, "dev", estado)
    humano = next(i for i in ex.itens_do_semaforo(estado, semaforo, "dev") if i.gate == "rastro_lacunas_status")
    assert humano.etapa_travada and humano.o_que_fazer.endswith(ex.OUTRO_NO_VERMELHO)
    # sem 🔴 na etapa, o mesmo item manda ao de acordo, sem o aviso
    (livre,) = ex.itens_do_semaforo(estado, {"rastro_lacunas_status": "🟡"}, "dev")
    assert not livre.etapa_travada and ex.OUTRO_NO_VERMELHO not in livre.o_que_fazer
    assert "de acordo" in livre.o_que_fazer
    # sem etapa (resultado sem parecer humano) não há «De acordo» a esconder
    (sem,) = [i for i in ex.itens_do_semaforo(estado, semaforo) if i.gate == "rastro_lacunas_status"]
    assert ex.OUTRO_NO_VERMELHO not in sem.o_que_fazer
    # o que não fala do de acordo nem manda seguir não ganha o aviso
    exp = ex._x("t", "a", "b", "Use **Refazer** pedindo que o trecho volte, citando-o.")
    assert ex.o_que_fazer(exp, ex.ATENCAO, "dev", True) == exp.o_que_fazer


def test_cartao_de_dev_com_vermelho_e_amarelo_real(tmp_path, monkeypatch):
    """No cartão: o bloqueio do juiz em 🟡 sai como decisão com a nota, e o Refazer de produto vira o da etapa."""
    estado = {"dev_status": "amarelo", "prd_status": "aprovado", "rastro_lacunas_status": "amarelo",
              "rastro_lacunas_status_envelope": _RASTRO_8CE9C32D}
    at = _rodar(tmp_path, monkeypatch, estado, "dev", "dev")
    texto = _textos(at)
    assert "Refazer** de produto" not in texto
    assert ex.PRODUTO_PELA_ETAPA in texto
    assert "o verificador que o reuniu ficou 🟡" in texto
