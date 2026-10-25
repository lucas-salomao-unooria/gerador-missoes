"""Gabarito do espelho no Miro (A084 — `tools/miro_cliente.conferir_espelho`), da volta V13 do levantamento de deficiências
de design de 24/10/2026 (DS-095, defeito da esteira): na exp06ef1b (727a3c2d, 28/09/2026) o espelho falhou, os cinco gates
de design ficaram 🟢 e o PO só soube ao abrir a missão — «Fluxos não foram gerados, algum problema na ponte mermaid-miro».
O único conserto foi refazer o design inteiro (1.698 s).

O estado da 1ª execução foi sobrescrito, e o motivo exato não ficou: o caso roda o A084 sobre o Mermaid real da jornada e
do fluxo da missão (o estado que o PO tinha em 08/10/2026, R04) com o Miro falhando. O board ausente TEM de aparecer no
semáforo do design — 🟡, porque o board é espelho e não bloqueia o de acordo — e nunca 🟢; o Miro desligado por
configuração é ⚪. A mensagem não leva credencial.
"""
from __future__ import annotations

import httpx
import pytest

from agents.checkers import EspelhoMiroAgent
from gabarito_estados import estado, rodar
from pipeline.passagem import semaforo_da_etapa
from tools import diagnostico
from tools import miro_cliente as mc

TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJtaXJvLXRlc3RlIn0.c2VncmVkby1kby1taXJv"


def _missao() -> dict:
    st = estado("R04")
    return {k: st[k] for k in ("spec_missao", "jornada_telas", "fluxo_arestas")}


class _MiroQueFalha:
    def __init__(self, erro: BaseException):
        self.erro = erro

    def __call__(self, *_a, **_kw):
        raise self.erro


class _MiroQueResponde:
    """O MCP do Miro de mentira: cria o board e aceita o SVG; `recusar` itens, se pedido."""

    def __init__(self, recusar: int = 0):
        self.recusar = recusar

    def __call__(self, *_a, **_kw):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def chamar(self, ferramenta, _argumentos):
        if ferramenta == "board_create":
            return {"viewLink": "https://miro.com/app/board/uXjTESTE=/"}
        return {"result_svg": "", "failed_items": [{"id": i} for i in range(self.recusar)]}


def _espelhar(monkeypatch, sessao, ligado: bool = True, inicial=None) -> dict:
    import config

    monkeypatch.setattr(mc, "SessaoMiro", sessao)
    real = config.get_settings()

    class _Config:
        def __getattr__(self, nome):
            return getattr(real, nome)

        is_miro_enabled = ligado

    monkeypatch.setattr(config, "get_settings", lambda: _Config())
    return rodar(inicial if inicial is not None else _missao(), EspelhoMiroAgent(name="A084EspelhoMiro"))


@pytest.mark.parametrize("erro", [
    httpx.HTTPStatusError("401", request=httpx.Request("POST", "https://mcp.miro.com/"),
                          response=httpx.Response(401, request=httpx.Request("POST", "https://mcp.miro.com/"))),
    httpx.ConnectTimeout("timeout"),
    RuntimeError(f"Miro respondeu erro em board_create: Authorization: Bearer {TOKEN}"),
], ids=["conexao-expirada", "tempo-esgotado", "erro-com-credencial"])
def test_v13_board_ausente_aparece_no_semaforo_do_design_em_amarelo(monkeypatch, erro):
    st = _espelhar(monkeypatch, _MiroQueFalha(erro))
    assert "MIRO: indisponível" in st["miro_links"]
    assert st[mc.KEY_STATUS] == "amarelo"
    achados = st[f"{mc.KEY_STATUS}_envelope"]["achados"]
    assert [a["codigo"] for a in achados] == ["miro-indisponivel"] and achados[0]["severidade"] == "atencao"
    assert semaforo_da_etapa(st, "design")[mc.KEY_STATUS] == "🟡"
    dossie = {g["rotulo"]: g["icone"] for g in diagnostico.coletar(st)["gates"]}
    assert dossie[mc.ROTULO_GATE] == "🟡"
    # nenhuma credencial na folha, no relatório, no envelope
    for texto in (st["miro_links"], st[mc.KEY_REPORT], str(st[f"{mc.KEY_STATUS}_envelope"])):
        assert TOKEN not in texto and "eyJ" not in texto


def test_board_completo_e_verde(monkeypatch):
    st = _espelhar(monkeypatch, _MiroQueResponde())
    assert st["miro_board"]["url_board"] == "https://miro.com/app/board/uXjTESTE=/"
    assert st[mc.KEY_STATUS] == "aprovado" and semaforo_da_etapa(st, "design")[mc.KEY_STATUS] == "🟢"


def test_board_sem_o_fluxo_e_amarelo(monkeypatch):
    """O fluxo que não chegou ao board é o que o PO não viu na V13 («Fluxos não foram gerados»)."""
    inicial = {**_missao(), "fluxo_arestas": "# Fluxo de telas\n\nsem o bloco Mermaid\n"}
    st = _espelhar(monkeypatch, _MiroQueResponde(), inicial=inicial)
    assert st[mc.KEY_STATUS] == "amarelo"
    assert "sem o diagrama de fluxo" in st[f"{mc.KEY_STATUS}_envelope"]["achados"][0]["resumo"]


def test_item_recusado_pelo_miro_e_amarelo(monkeypatch):
    st = _espelhar(monkeypatch, _MiroQueResponde(recusar=2))
    assert st[mc.KEY_STATUS] == "amarelo" and "2 item(ns) recusado(s)" in st[mc.KEY_REPORT]


def test_miro_desligado_e_branco_nunca_verde(monkeypatch):
    st = _espelhar(monkeypatch, _MiroQueFalha(AssertionError("não chama o Miro desligado")), ligado=False)
    assert st[mc.KEY_STATUS] == mc.DESLIGADO and semaforo_da_etapa(st, "design")[mc.KEY_STATUS] == "⚪"
    assert st[f"{mc.KEY_STATUS}_envelope"]["achados"] == []
