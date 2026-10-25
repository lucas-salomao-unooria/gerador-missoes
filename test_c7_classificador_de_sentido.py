"""C7 — regras de sentido: o classificador LLM estreito entra só onde a fase A mediu ganho, e interpretação nunca bloqueia
sozinha (`tools/severidade.py`).

O classificador é falso aqui (`_ler_falso`): cada teste diz o que ele lê, e o que se confere é o que o gate faz com a
leitura — incluindo «nao_sei», que é o que a esteira recebe sem chave, com erro ou fora do cache.

- `hipotese-diverge`: 🔴 só quando o código e o classificador leem a meta e o número diverge; discordância ou «nao_sei»
  → `hipotese-a-conferir` 🟡 com as duas leituras;
- `rotulo-divergente`: o «é botão?» filtra o candidato da prosa sem chave; a célula da chave de copy não passa por ele;
- `exigencia-dispensada`: 🟡; o juiz e o classificador lendo contexto dispensam;
- decisão do PO e recontagem dos juízes: a leitura ordena e explica o «a conferir», nunca o apaga;
- `numero-sem-origem`, `preservacao-sem-prova` e as guardas do fluxo: interpretação → 🟡.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List

import pytest

from tools import classificador as C
from tools import consistencia, decisoes, fidelidade, juizes_produto, montagem


def _ler_falso(monkeypatch, responder: Callable[[str, Dict[str, Any]], str]) -> List[tuple]:
    """Troca `classificador.ler`: `responder(pergunta, entrada)` dá o rótulo; a citação é o começo da entrada."""
    vistos: List[tuple] = []

    def ler(pergunta, entradas):
        saida = []
        for e in entradas:
            vistos.append((pergunta.id, e))
            rotulo = responder(pergunta.id, e)
            texto = pergunta.montar(e)
            saida.append(C.Leitura(rotulo, "" if rotulo == C.NAO_SEI else texto.splitlines()[1][:60], "modelo"))
        return saida

    monkeypatch.setattr(C, "ler", ler)
    return vistos


# ------------------------------------------------------------------ hipótese: dupla leitura
ONE_PAGER = """# One-pager — teste

## 15. Tetos
- no máximo 20 palavras por balão.

## 17. Hipóteses de validação
- **Hipótese 1 (Usabilidade):** a dupla ajusta a moldura.
  - *Indica falha:* Mais de 30% das duplas desistirem de ajustar a moldura e confirmarem na posição default.
- **Hipótese 2 (Leitura):** a criança lê o pictograma sozinha.
"""


def _hipotese(texto_h1: str) -> str:
    return f"# 2. Objetivos\n\n### Hipóteses de validação\n- **H1 (Usabilidade):** {texto_h1}\n"


def _situacoes(corpo: str, contrato: str = "") -> List[Dict[str, str]]:
    return montagem.hipoteses_reescritas(ONE_PAGER, corpo, "", contrato or ONE_PAGER)


def test_h1_30x25_bloqueia_so_quando_o_codigo_e_o_classificador_leem_meta(monkeypatch):
    corpo = _hipotese("Se mais de 25% das duplas desistirem de ajustar a moldura e confirmarem na posição default.")
    _ler_falso(monkeypatch, lambda p, e: "meta")
    h = _situacoes(corpo)
    assert [(x["situacao"], x["corpo"]) for x in h] == [("trocado", "25%")]

    for lido in ("mecanica", C.NAO_SEI):
        _ler_falso(monkeypatch, lambda p, e, lido=lido: lido)
        h = _situacoes(corpo)
        assert [(x["situacao"], x["corpo"]) for x in h] == [("leitura-a-conferir", "25%")], lido
        assert "o código lê meta" in h[0]["leituras"]


def test_meta_que_o_codigo_isenta_e_o_classificador_le_vira_duvida(monkeypatch):
    """O held-out da fase A: a duração que o contrato tem era isenta pelo código e era a meta da hipótese (4 de 13)."""
    contrato = ONE_PAGER + "\n## 4. Etapas\n- A criança escolhe o pictograma em até 15 s.\n"
    corpo = "# 2. Objetivos\n\n### Hipóteses de validação\n- **H2 (Leitura):** a criança escolhe o pictograma em até 15 s.\n"
    _ler_falso(monkeypatch, lambda p, e: "meta")
    h = montagem.hipoteses_reescritas(ONE_PAGER, corpo, "", contrato)
    assert [(x["situacao"], x["corpo"]) for x in h] == [("leitura-a-conferir", "15 s")]
    assert "o código lê parâmetro da mecânica" in h[0]["leituras"]
    _ler_falso(monkeypatch, lambda p, e: "mecanica")
    assert montagem.hipoteses_reescritas(ONE_PAGER, corpo, "", contrato) == []


def test_o_classificador_le_o_numero_com_a_hipotese_do_17(monkeypatch):
    corpo = _hipotese("Se mais de 25% das duplas desistirem de ajustar a moldura.")
    vistos = _ler_falso(monkeypatch, lambda p, e: "meta")
    _situacoes(corpo)
    assert vistos == [("numero_da_hipotese", {
        "hipotese_no_documento": "- **H1 (Usabilidade):** Se mais de 25% das duplas desistirem de ajustar a moldura.\n",
        "hipotese_aprovada_no_17": montagem._itens_de_hipotese(ONE_PAGER.split("## 17.")[1])[1],
        "numero": "25%"})]


def test_duvida_da_leitura_sai_como_hipotese_a_conferir_no_prd(monkeypatch):
    from test_montagem import _prd, _sintetico

    estado = _sintetico(prd_final=_prd({"Mais de 30% das duplas confirmarem": "Mais de 25% das duplas confirmarem"}))
    _ler_falso(monkeypatch, lambda p, e: "meta")
    r = montagem.validar_prd(estado)
    assert any(a["codigo"] == "hipotese-diverge" and a["severidade"] == "bloqueio" for a in r["achados"])
    _ler_falso(monkeypatch, lambda p, e: C.NAO_SEI)
    r = montagem.validar_prd(estado)
    duvida = [a for a in r["achados"] if a["codigo"] == "hipotese-a-conferir"]
    assert not [a for a in r["achados"] if a["codigo"] == "hipotese-diverge"]
    assert duvida and duvida[0]["severidade"] == "atencao" and "o classificador não respondeu" in duvida[0]["resumo"]


# ------------------------------------------------------------------ número sem origem
def test_numero_sem_origem_e_atencao_no_prd(monkeypatch):
    from test_montagem import _prd, _sintetico

    _ler_falso(monkeypatch, lambda p, e: "meta")
    estado = _sintetico(prd_final=_prd({"no máximo 8 minutos (§15": "no máximo 8 minutos e 45 segundos de espera (§15"}))
    estado["prd_final"] += "\n- RF-01: a criança tem 7 tentativas para ajustar a moldura.\n"
    r = montagem.validar_prd(estado)
    sem = [a for a in r["achados"] if a["codigo"] == "numero-sem-origem"]
    assert sem and all(a["severidade"] == "atencao" for a in sem) and "Não bloqueia" in sem[0]["resumo"]


# ------------------------------------------------------------------ rótulo de botão
GLOSSARIO = """# Spec — teste

## Glossário canônico

### Rótulos de botão
| Ação | Rótulo canônico |
|---|---|
| Publicar o post no feed | Publicar no feed |
"""


def _rotulos(texto: str, documento: str = "fluxo") -> List[Dict[str, str]]:
    r = consistencia.validar(GLOSSARIO, {documento: texto})
    return [a for a in r["achados"] if a["codigo"] == "rotulo-divergente"]


def test_e_botao_filtra_so_a_prosa_sem_chave(monkeypatch):
    prosa = "O estudante toca o botão «Publicar post no feed» e a tela confirma.\n"
    vistos = _ler_falso(monkeypatch, lambda p, e: "outro")
    assert _rotulos(prosa) == []
    assert vistos and vistos[0][1]["candidato"] == "Publicar post no feed" and vistos[0][1]["documento"] == "fluxo"
    _ler_falso(monkeypatch, lambda p, e: "rotulo_de_botao")
    assert len(_rotulos(prosa)) == 1
    # sem leitura, o 🟡 fica
    _ler_falso(monkeypatch, lambda p, e: C.NAO_SEI)
    assert len(_rotulos(prosa)) == 1 and _rotulos(prosa)[0]["severidade"] == "atencao"


def test_celula_da_chave_de_copy_nao_passa_pelo_classificador(monkeypatch):
    copy = ("| Chave | Texto |\n|---|---|\n| `e2.rotulo.botao_publicar` | Publicar post no feed |\n")
    vistos = _ler_falso(monkeypatch, lambda p, e: "outro")
    assert len(_rotulos(copy, "copy revisada")) == 1 and vistos == []


def test_o_classificador_recebe_o_cabecalho_da_tabela(monkeypatch):
    tabela = ("| Tela | Ação (verbo nativo) | Botão |\n|---|---|---|\n"
              "| `E2-ALU-01` | `Publicar` | botão «Publicar post no feed» |\n")
    vistos = _ler_falso(monkeypatch, lambda p, e: "rotulo_de_botao")
    _rotulos(tabela)
    assert vistos[0][1]["cabecalho_da_tabela"] == "| Tela | Ação (verbo nativo) | Botão |"
    assert vistos[0][1]["linha"].startswith("| `E2-ALU-01`")


# ------------------------------------------------------------------ exigência dispensada
PEDIDO = """Ajustes no critério da habilidade:

EM13CO13 — substituir o critério por observáveis:

- Atingiu: o aluno deve publicar a errata e assumir a autoria em público.
"""


def _fidelidade(monkeypatch, rotulo: str):
    vistos = _ler_falso(monkeypatch, lambda p, e: rotulo)
    itens = fidelidade.montar_checklist([("refazer Produto · PO · 25/10", PEDIDO)], "")
    alvo = next(i for i in itens if "Atingiu" in i["texto"])
    assert fidelidade.exige_acao(alvo["texto"])
    juiz = "```json\n" + json.dumps({"decisoes": [
        {"id": i["id"], "veredito": "contexto" if i is alvo else "atendido", "citacao": "x", "explicacao": ""}
        for i in itens]}) + "\n```"
    r = fidelidade.aplicar(itens, juiz, {"one_pager": "texto que não tem o critério"})
    return r, alvo, vistos


def test_exigencia_dispensada_e_atencao_e_leva_as_linhas_anteriores(monkeypatch):
    r, alvo, vistos = _fidelidade(monkeypatch, "exigencia")
    meus = [a for a in r["achados"] if a["id"] == alvo["id"]]
    assert [(a["codigo"], a["severidade"]) for a in meus] == [("exigencia-dispensada", "atencao")]
    assert "o classificador lê «exigência»" in meus[0]["resumo"]
    entrada = next(e for p, e in vistos if p == "item_do_pedido_classe")
    assert entrada["linhas_anteriores_no_pedido"] == ("Ajustes no critério da habilidade:\n"
                                                      "EM13CO13 — substituir o critério por observáveis:")


def test_juiz_e_classificador_lendo_contexto_dispensam(monkeypatch):
    r, alvo, _ = _fidelidade(monkeypatch, "contexto")
    assert not [a for a in r["achados"] if a["id"] == alvo["id"]]
    assert any(c["id"] == alvo["id"] and "classificador" in c["prova"] for c in r["conferidos"])


def test_sem_leitura_a_exigencia_fica_a_conferir(monkeypatch):
    r, alvo, _ = _fidelidade(monkeypatch, C.NAO_SEI)
    meus = [a for a in r["achados"] if a["id"] == alvo["id"]]
    assert [(a["codigo"], a["severidade"]) for a in meus] == [("exigencia-dispensada", "atencao")]
    assert r["status"] != "bloqueado" or any(a["severidade"] == "bloqueio" for a in r["achados"])


def test_linhas_anteriores_do_item():
    assert fidelidade.linhas_anteriores(PEDIDO, "Atingiu: o aluno deve publicar a errata") == (
        "Ajustes no critério da habilidade:\nEM13CO13 — substituir o critério por observáveis:")
    assert fidelidade.linhas_anteriores(PEDIDO, "(item 2) EM13CO13 — substituir o critério") == (
        "Ajustes no critério da habilidade:")
    assert fidelidade.linhas_anteriores(PEDIDO, "Ajustes no critério da habilidade:") == ""
    assert fidelidade.linhas_anteriores(PEDIDO, "frase que não está no pedido") == ""


def test_preservacao_sem_prova_e_atencao(monkeypatch):
    _ler_falso(monkeypatch, lambda p, e: "exigencia")
    itens = fidelidade.montar_checklist([("refazer", "Não alterar a narrativa da Etapa 3 em nenhum documento.")], "")
    r = fidelidade.aplicar(itens, "", {"one_pager": "texto"}, anteriores={"one_pager": "outro texto"})
    sem = [a for a in r["achados"] if a["codigo"] == "preservacao-sem-prova"]
    assert sem and sem[0]["severidade"] == "atencao" and r["status"] == "amarelo"


# ------------------------------------------------------------------ decisão do PO: pista que ordena, nunca apaga
def _registro(**estado: Any) -> decisoes.RegistroDoPO:
    estado = {"pedidos_do_po": [{"origem": "refazer", "texto": "Ajustar a duração para 90 s."}], **estado}
    return decisoes.ha_registro_do_po(estado)


DOC = ("- O tempo de 90 s foi aprovado pelo PO.\n"
       "- O StoryPoll foi aprovado pelo PO.\n")


def test_pista_do_classificador_ordena_e_explica_sem_apagar(monkeypatch):
    vistos = _ler_falso(monkeypatch, lambda p, e: "confirmada" if "90 s" in e["linha"] else "nao_confirmada")
    achado = decisoes.achados(DOC, "O one-pager", _registro(), chave="one_pager")[0]
    assert achado["codigo"] == "decisao-atribuida-ao-po" and achado["severidade"] == "atencao"
    linhas = [l for l in achado["resumo"].splitlines() if l.strip().startswith("- «")]
    # as duas ficam; a que ele não lê confirmada vem primeiro
    assert len(linhas) == 2 and "StoryPoll" in linhas[0] and "90 s" in linhas[1]
    assert "não lê confirmação do PO" in linhas[0] and "é pista, não confirma" in linhas[1]
    assert {e["documento"] for _, e in vistos} == {"one_pager"}
    assert "### Pedido 1 · refazer\nAjustar a duração para 90 s." in vistos[0][1]["registros_do_po"]


def test_sem_registro_do_po_a_atribuicao_bloqueia_sem_perguntar(monkeypatch):
    vistos = _ler_falso(monkeypatch, lambda p, e: "confirmada")
    achado = decisoes.achados(DOC, "O one-pager", decisoes.ha_registro_do_po({}), chave="one_pager")[0]
    assert achado["severidade"] == "bloqueio" and vistos == []


def test_recontagem_dos_juizes_marca_a_leitura_e_continua_contando(monkeypatch):
    _ler_falso(monkeypatch, lambda p, e: "repete_decisao_do_po" if "29 min" in e["ressalva"] else "aponta_problema")
    envelope = {"status": "aprovado_com_ressalvas", "achados": [
        {"severidade": "atencao", "resumo": "Tempo em tela de 29 min aceito pelo PO no Pedido 13."},
        {"severidade": "atencao", "resumo": "O teto de 45 palavras aceito pelo PO é excedido no chat."}]}
    novo, nota = juizes_produto.recontar(envelope, {"pedidos_do_po": [{"texto": "Tempo de 29 min: aceito."}]})
    assert len(novo["achados"]) == 2 and novo["status"] == "aprovado_com_ressalvas"
    marcas = {a["resumo"][:20]: a for a in novo["achados"]}
    assert "só repete a decisão do PO" in marcas["Tempo em tela de 29 "]["a_conferir"]
    assert "aponta um problema" in marcas["O teto de 45 palavra"]["a_conferir"]
    # a que aponta problema vem primeiro na nota
    assert nota.index("45 palavras") < nota.index("29 min")


# ------------------------------------------------------------------ guardas do fluxo
def test_guarda_lida_por_regex_nao_bloqueia_nem_com_estrito():
    from tools import arestas

    for estrito in (False, True):
        assert arestas._achado("guarda-exige-acerto", "x", estrito)["severidade"] == "decisao_humana"
        assert arestas._achado("guarda-afrouxada", "x", estrito)["severidade"] == "decisao_humana"


# ------------------------------------------------------------------ o gate devolve o cache ao estado
def test_gate_de_montagem_grava_o_cache_e_o_custo_no_estado(monkeypatch):
    import asyncio

    from google.adk.runners import InMemoryRunner
    from google.genai import types

    from agents.checkers import RastroCheckAgent
    from test_montagem import _prd, _sintetico

    monkeypatch.setenv(C.ENV_MODO, "ligado")
    monkeypatch.setenv(C.ENV_CACHE_FIXO, "")
    monkeypatch.setenv("GOOGLE_API_KEY", "AIzaSy-CHAVE-FALSA")
    monkeypatch.setattr(C, "_chamar_modelo", lambda p, prompt, m: (json.dumps(
        {"citacao": "Mais de 25% das duplas confirmarem", "rotulo": "meta"}), {"entrada": 600, "saida": 10,
                                                                             "pensamento": 300}))
    estado = _sintetico(prd_final=_prd({"Mais de 30% das duplas confirmarem": "Mais de 25% das duplas confirmarem"}))
    gate = RastroCheckAgent(name="A116bMontagemPrd", modo="montagem_prd", report_key="montagem_prd_report",
                            status_key="montagem_prd_status", rotulo="PRD monta, não decide")

    async def rodar():
        runner = InMemoryRunner(agent=gate, app_name="t")
        await runner.session_service.create_session(app_name="t", user_id="u", session_id="s", state=estado)
        async for _ in runner.run_async(user_id="u", session_id="s",
                                        new_message=types.Content(role="user", parts=[types.Part(text="go")])):
            pass
        return dict((await runner.session_service.get_session(app_name="t", user_id="u", session_id="s")).state)

    final = asyncio.run(rodar())
    assert final["montagem_prd_status"] == "bloqueado"
    registro = final[C.KEY]
    assert registro["custo"]["por_gate"]["montagem_prd_status"]["chamadas"] == 1
    assert [v["r"] for v in registro["cache"].values()] == ["meta"]
    assert "CHAVE-FALSA" not in json.dumps(registro)
    # a variável de contexto foi fechada: fora do gate não há sessão aberta
    assert C._SESSAO.get() is None
