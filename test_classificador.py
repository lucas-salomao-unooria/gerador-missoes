"""O classificador de sentido da C7 (`tools/classificador.py`) e a política de severidade (`tools/severidade.py`).

Pergunta estreita, rótulo de lista fechada, citação conferida em código, cache pelo hash (pergunta, versão, modelo,
entrada), «nao_sei» em qualquer falha — e nunca a chave no estado, no cache nem no log. O modelo aqui é falso
(`_chamar_modelo`): teste não chama modelo.
"""
from __future__ import annotations

import hashlib
import json
import logging

import pytest

from tools import classificador as C
from tools import severidade as sev

CHAVE_FALSA = "AIzaSy-CHAVE-FALSA-DO-TESTE-0123456789"
HIP = {"hipotese_no_documento": "- **H1:** Se mais de 25% das duplas desistirem de ajustar a moldura, a hipótese falha.",
       "hipotese_aprovada_no_17": "- **Hipótese 1:** Mais de 30% das duplas desistirem de ajustar a moldura.",
       "numero": "25%"}


@pytest.fixture
def ligado(monkeypatch):
    """O classificador ligado, com chave falsa e sem cache de teste: o que não está na sessão vai ao modelo falso."""
    monkeypatch.setenv(C.ENV_MODO, "ligado")
    monkeypatch.setenv(C.ENV_CACHE_FIXO, "")
    monkeypatch.delenv(C.ENV_GRAVAR_CACHE_FIXO, raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", CHAVE_FALSA)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    chamadas = []

    def responder(resposta):
        def falso(pergunta, prompt, modelo):
            chamadas.append(prompt)
            if isinstance(resposta, Exception):
                raise resposta
            return (resposta(prompt) if callable(resposta) else resposta), {"entrada": 500, "saida": 20,
                                                                             "pensamento": 280}
        monkeypatch.setattr(C, "_chamar_modelo", falso)
        return chamadas

    return responder


def _meta(prompt: str) -> str:
    return json.dumps({"citacao": "mais de 25% das duplas desistirem", "rotulo": "meta"})


# ------------------------------------------------------------------ o prompt versionado
#: O prompt inteiro de cada pergunta, pela versão. Mudou o texto, sobe a versão (o hash do cache leva a versão) e o
#: gabarito é regravado e remedido (`scripts/gravar_cache_classificador.py --gabarito`). São os prompts da fase A.
PROMPTS = {
    ("numero_da_hipotese", "v1"): "955e302a94ad3833",
    ("rotulo_de_botao", "v1"): "d23103e69b1dd529",
    ("item_do_pedido_classe", "v2"): "b302374d159b1fca",
    ("decisao_do_po_confirmada", "v1"): "36ef4a48645019f4",
    ("ressalva_repete_decisao_do_po", "v1"): "965e9d31b1290aee",
    ("alteracao_po_autorizada", "v1"): "3ccd0db320ab042d",
    ("gesto_equivalente_ficha", "v1"): "f5bf4132ad9460ba",
    ("papel_equivalente_glossario", "v1"): "62159fb0db460444",
    ("aspas_conceito_ou_fala", "v1"): "032e6b7bc0b7e760",
    ("virada_tem_crenca", "v1"): "6cec82521300ac8b",
    ("nomes_assistente_distintos", "v1"): "e1d2f0d83d390696",
}
_CAMPOS = ("hipotese_no_documento", "hipotese_aprovada_no_17", "numero", "documento", "cabecalho_da_tabela", "linha",
           "candidato", "item", "linhas_anteriores_no_pedido", "registros_do_po", "ressalva",
           "alteracao_declarada", "gesto", "papel_canonico", "virada", "termos", "trecho")


def test_texto_do_prompt_preso_a_versao():
    for p in C.TODAS_AS_PERGUNTAS.values():
        texto = p.prompt(p.montar({k: f"<{k}>" for k in _CAMPOS}))
        assert (p.id, p.versao) in PROMPTS, f"{p.id} {p.versao}: versão nova sem o hash registrado aqui"
        assert hashlib.sha256(texto.encode()).hexdigest()[:16] == PROMPTS[(p.id, p.versao)], (
            f"o prompt de {p.id} mudou sem subir a versão {p.versao}")
        assert C.NAO_SEI in p.rotulos_com_nao_sei and C.NAO_SEI not in p.rotulos


def test_chave_do_cache_muda_com_versao_modelo_e_entrada():
    texto = C.NUMERO_DA_HIPOTESE.montar(HIP)
    base = C.chave(C.NUMERO_DA_HIPOTESE, texto, "gemini-3.8-flash")
    outra_versao = C.Pergunta("numero_da_hipotese", "v9", ("meta", "mecanica"), "x", lambda e: "")
    assert C.chave(outra_versao, texto, "gemini-3.8-flash") != base
    assert C.chave(C.NUMERO_DA_HIPOTESE, texto, "outro-modelo") != base
    assert C.chave(C.NUMERO_DA_HIPOTESE, texto + " ", "gemini-3.8-flash") != base
    assert C.chave(C.NUMERO_DA_HIPOTESE, texto, "gemini-3.8-flash") == base


# ------------------------------------------------------------------ a resposta conferida
def test_citacao_confere_a_menos_de_aspas_enfase_e_espacos():
    assert C.citacao_confere("«mais de 25%»  das *duplas*", "Se mais de 25% das duplas desistirem")
    assert not C.citacao_confere("mais de 30% das duplas", "Se mais de 25% das duplas desistirem")
    assert not C.citacao_confere("de", "Se mais de 25%")  # curta demais para provar


def test_resposta_do_modelo_vale_com_citacao_no_trecho(ligado):
    ligado(_meta)
    leitura = C.numero_da_hipotese(**HIP)
    assert (leitura.rotulo, leitura.origem, leitura.motivo) == ("meta", "modelo", "")
    assert "25%" in leitura.explicada()


@pytest.mark.parametrize("resposta,motivo", [
    (json.dumps({"citacao": "um trecho que não está na entrada", "rotulo": "meta"}), "a citação não está no trecho"),
    (json.dumps({"citacao": "mais de 25% das duplas", "rotulo": "talvez"}), "rótulo fora da lista"),
    ("não é JSON", "resposta sem JSON"),
])
def test_resposta_sem_prova_vira_nao_sei(ligado, resposta, motivo):
    ligado(resposta)
    leitura = C.numero_da_hipotese(**HIP)
    assert leitura.nao_sei and motivo in leitura.motivo


def test_nao_sei_do_modelo_vale_sem_citacao(ligado):
    ligado(json.dumps({"citacao": "", "rotulo": "nao_sei"}))
    leitura = C.numero_da_hipotese(**HIP)
    assert leitura.nao_sei and leitura.motivo == ""


def test_erro_do_modelo_nunca_derruba_e_nao_vaza_a_chave(ligado, caplog):
    ligado(RuntimeError(f"401 para a chave {CHAVE_FALSA}"))
    with caplog.at_level(logging.WARNING), C.sessao({}, "gate") as s:
        leitura = C.numero_da_hipotese(**HIP)
    assert leitura.nao_sei and leitura.motivo == "erro do modelo (RuntimeError)"
    assert CHAVE_FALSA not in caplog.text and CHAVE_FALSA not in json.dumps(s.delta(), ensure_ascii=False)
    # o erro não fica no cache: a próxima execução pergunta de novo
    assert not s.cache


def test_sem_chave_desligado_e_fora_do_cache_de_teste_viram_nao_sei(ligado, monkeypatch):
    chamadas = ligado(_meta)
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    assert C.numero_da_hipotese(**HIP).motivo == "sem chave do modelo"
    monkeypatch.setenv("GOOGLE_API_KEY", CHAVE_FALSA)
    monkeypatch.setenv(C.ENV_MODO, "desligado")
    assert C.numero_da_hipotese(**HIP).motivo == "classificador desligado"
    monkeypatch.setenv(C.ENV_MODO, "so_cache")
    assert C.numero_da_hipotese(**HIP).motivo == "fora do cache"
    assert not chamadas


# ------------------------------------------------------------------ o cache e o custo na sessão
def test_cache_da_sessao_responde_igual_sem_chamar_de_novo(ligado):
    chamadas = ligado(_meta)
    with C.sessao({}, "montagem_prd_status") as s:
        primeira = C.numero_da_hipotese(**HIP)
    delta = s.delta()
    registro = delta[C.KEY]
    assert len(chamadas) == 1 and primeira.rotulo == "meta"
    assert registro["custo"]["chamadas"] == 1 and registro["custo"]["usd"] > 0
    assert registro["custo"]["por_gate"]["montagem_prd_status"]["chamadas"] == 1
    entrada = next(iter(registro["cache"].values()))
    assert entrada == {"p": "numero_da_hipotese", "v": "v1", "r": "meta", "c": "mais de 25% das duplas desistirem"}
    # a reexecução, com o estado que o gate gravou: a mesma resposta, sem chamada nem custo novo
    estado = {C.KEY: registro}
    with C.sessao(estado, "montagem_prd_status") as s2:
        segunda = C.numero_da_hipotese(**HIP)
    assert len(chamadas) == 1 and (segunda.rotulo, segunda.origem) == ("meta", "sessao")
    # e não regrava o cache inteiro no estado: nada mudou (revisão do PR #85)
    assert s2.do_cache == 1 and s2.delta() == {}


def test_gate_sem_chamada_nem_leitura_nova_nao_regrava_o_estado(monkeypatch):
    """O «nao_sei» sem chamada (desligado, sem chave, fora do cache de teste) também não mexe no estado."""
    monkeypatch.setenv(C.ENV_MODO, "desligado")
    with C.sessao({}, "gate") as s:
        assert C.numero_da_hipotese(**HIP).nao_sei
    assert s.nao_sei == 1 and s.delta() == {}


def test_gate_que_nao_le_nada_nao_mexe_no_estado():
    with C.sessao({}, "gate") as s:
        pass
    assert s.delta() == {}


def test_limite_de_chamadas_por_gate(ligado, monkeypatch):
    chamadas = ligado(_meta)
    monkeypatch.setattr(C, "LIMITE_POR_GATE", 2)
    entradas = [{**HIP, "hipotese_no_documento": HIP["hipotese_no_documento"] + f" ({i})"} for i in range(4)]
    with C.sessao({}, "gate"):
        lidas = C.ler(C.NUMERO_DA_HIPOTESE, entradas)
    assert len(chamadas) == 2
    assert sum(1 for l in lidas if l.rotulo == "meta") == 2
    assert [l.motivo for l in lidas if l.nao_sei] == ["limite de 2 chamadas do gate"] * 2


def test_cache_do_estado_tem_teto(ligado, monkeypatch):
    ligado(_meta)
    monkeypatch.setattr(C, "MAX_ENTRADAS", 3)
    antigo = {f"h{i}": {"p": "x", "v": "v1", "r": "meta", "c": ""} for i in range(3)}
    with C.sessao({C.KEY: {"cache": antigo}}, "gate") as s:
        C.numero_da_hipotese(**HIP)
    cache = s.delta()[C.KEY]["cache"]
    assert len(cache) == 3 and "h0" not in cache  # sai a mais antiga


def test_sem_sessao_aberta_le_sem_gravar_estado(ligado):
    ligado(_meta)
    assert C.numero_da_hipotese(**HIP).rotulo == "meta"


def test_cache_de_teste_e_gravado_so_quando_pedido(ligado, monkeypatch, tmp_path):
    chamadas = ligado(_meta)
    arquivo = tmp_path / "cache.json"
    monkeypatch.setenv(C.ENV_CACHE_FIXO, str(arquivo))
    monkeypatch.setenv(C.ENV_GRAVAR_CACHE_FIXO, "1")
    monkeypatch.setenv(C.ENV_MODO, "so_cache")
    assert C.numero_da_hipotese(**HIP).rotulo == "meta"
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    assert len(dados["leituras"]) == 1 and CHAVE_FALSA not in arquivo.read_text(encoding="utf-8")
    monkeypatch.delenv(C.ENV_GRAVAR_CACHE_FIXO)
    leitura = C.numero_da_hipotese(**HIP)
    assert (leitura.rotulo, leitura.origem) == ("meta", "cache_de_teste") and len(chamadas) == 1
    # a leitura que veio do cache de teste entra no da sessão: sem chamada, mas é leitura nova e vai ao estado
    with C.sessao({}, "gate") as s:
        C.numero_da_hipotese(**HIP)
    assert s.chamadas == 0 and len(s.delta()[C.KEY]["cache"]) == 1


def test_custo_da_sessao_soma_por_gate():
    estado = {C.KEY: {"custo": {"chamadas": 3, "usd": 0.01, "tokens": {"entrada": 1}, "por_gate": {}}}}
    assert C.custo_da_sessao(estado)["chamadas"] == 3
    assert C.custo_da_sessao({}) == {}


# ------------------------------------------------------------------ os registros do PO, como a fase A os leu
def test_registros_do_po_no_formato_da_fase_a():
    estado = {
        "pedidos_do_po": [{"origem": "refazer Produto · PO · 21/10", "texto": "Tirar o StoryPoll."}],
        "pareceres_humanos": [{"acao": "refazer", "etapa": "produto", "comentario": "não entra"},
                              {"acao": "de_acordo", "etapa": "produto", "quando": "21/10 15:43",
                               "comentario": "90 s e 45 palavras"}],
        "decisoes_do_po": [{"assunto": "duração", "resposta": "aceitar"}],
        "one_pager_po": "linha sem nada\nO teto de 45 palavras por balão vale para o chat da missão",
    }
    texto = C.registros_do_po(estado, "teto de 45 palavras por balão no chat")
    assert "### Pedido 1 · refazer Produto · PO · 21/10\nTirar o StoryPoll." in texto
    assert "### Parecer de_acordo · produto · 21/10 15:43\n90 s e 45 palavras" in texto and "não entra" not in texto
    assert '### Decisão gravada no de acordo\n{"assunto": "duração", "resposta": "aceitar"}' in texto
    assert "O teto de 45 palavras por balão" in texto and "linha sem nada" not in texto
    assert C.registros_do_po({}, "x") == "(a sessão não tem nenhum registro do PO)"


# ------------------------------------------------------------------ a política de severidade
def test_so_o_que_o_codigo_prova_bloqueia():
    assert sev.por_prova("bloqueio", sev.PROVA) == "bloqueio"
    assert sev.por_prova("bloqueio", sev.INTERPRETACAO) == "atencao"
    assert sev.por_prova("bloqueio", sev.INTERPRETACAO, rebaixada="decisao_humana") == "decisao_humana"
    assert sev.por_prova("atencao", sev.INTERPRETACAO) == "atencao"


@pytest.mark.parametrize("codigo,rotulo,esperado", [
    (True, "meta", sev.CONCORDAM_SIM),
    (False, "mecanica", sev.CONCORDAM_NAO),
    (True, "mecanica", sev.DUVIDA),
    (False, "meta", sev.DUVIDA),
    (True, "nao_sei", sev.DUVIDA),
    (False, "nao_sei", sev.DUVIDA),
])
def test_leitura_dupla(codigo, rotulo, esperado):
    assert sev.leitura_dupla(codigo, C.Leitura(rotulo), "meta") == esperado
