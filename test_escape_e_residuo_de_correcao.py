"""Falsos 🔴 do dev da exp03em1b (sessão 20261027-144710-session_db50c2a9, 28/10/2026).

- A fala do podcast saía «perdida» no banco: o one-pager escreve `\\*truncamento de eixo\\*` (escape de markdown) e o banco
  `*truncamento de eixo*`; `fidelidade._norm` tirava o `*` e deixava a barra.
- O handoff anotou a retirada do código órfão («`[RESOLVIDA]` — Expurgo de D0-4: Código órfão expurgado…») e o rastro
  leu a anotação como citação do D0-4 — o motivo do bloqueio do dev.
- O anexo citou o marcador que a decisão do PO fechou («encerra … a pendência anterior `[ABERTO — dono: PO: …]`») e o
  rastro o contou como pendência aberta.

Os trechos são literais da sessão (`analises-esteira/2026-10-28/db50c2a9/`, fora do repositório).
"""
from __future__ import annotations

FALA_ONE_PAGER = ("**Alex:** Essa técnica tem nome na ciência de dados: chama-se \\*truncamento de eixo\\*. Quando você "
                  "joga o início do gráfico de barras para oitenta por cento")
FALA_BANCO = ("**Alex:** Essa técnica tem nome na ciência de dados: chama-se *truncamento de eixo*. Quando você "
              "joga o início do gráfico de barras para oitenta por cento")

ANEXO = ("# Anexo de design\n\n## 13. Decisões D0\n\n### [D0-1] lupa\nTexto.\n\n"
         "*Esta decisão do PO encerra em definitivo a pendência anterior `[ABERTO — dono: PO: 2.conclusao]`.*\n\n"
         "## 14. Ambiente simulado (D9)\n\nFicha.\n")
LINHA_EXPURGO = ("- `[RESOLVIDA]` — **Expurgo de D0-4:** Código órfão expurgado integralmente na rodada 2 do QA de "
                 "entregáveis.")


def _estado(handoff: str, anexo: str = ANEXO) -> dict:
    from tools.anexo_design import KEY_ANEXO

    return {"spec_missao": "# Spec\n\nCorpo.\n", KEY_ANEXO: anexo, "handoff_dev": handoff}


def test_escape_de_markdown_nao_separa_a_fala_do_banco():
    from tools.conteudo_aprovado import literais_ausentes
    from tools.fidelidade import _norm

    assert _norm(FALA_ONE_PAGER) == _norm(FALA_BANCO)
    assert literais_ausentes(FALA_BANCO, [FALA_ONE_PAGER]) == []
    # mutante: a fala trocada continua ausente
    assert literais_ausentes(FALA_BANCO.replace("oitenta", "noventa"), [FALA_ONE_PAGER]) != []


def test_anotacao_da_retirada_do_orfao_nao_e_citacao():
    from tools.rastro import FONTES_DEV, d0_orfaos

    assert d0_orfaos(FONTES_DEV, _estado(f"# Handoff\n\n{LINHA_EXPURGO}\n")) == []
    # mutante: a citação de verdade continua órfã
    orfaos = d0_orfaos(FONTES_DEV, _estado("# Handoff\n\nO player segue a decisão [D0-4].\n"))
    assert [o["trecho"] for o in orfaos] == ["D0-4"]


def test_marcador_citado_como_encerrado_nao_e_pendencia():
    from tools.rastro import FONTES_DEV, varrer_lacunas

    r = varrer_lacunas(FONTES_DEV, _estado("# Handoff\n\nNada.\n"), etapa_corrente="dev")
    assert r["status"] == "aprovado" and r["achados"] == []
    # mutante: o mesmo marcador, sem quem o encerre, continua pendência do PO
    aberto = ANEXO.replace("*Esta decisão do PO encerra em definitivo a pendência anterior", "*Falta decidir:")
    r = varrer_lacunas(FONTES_DEV, _estado("# Handoff\n\nNada.\n", aberto), etapa_corrente="dev")
    assert any("2.conclusao" in a.get("trecho", "") for a in r["achados"])
