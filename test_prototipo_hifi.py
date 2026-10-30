"""Protótipo hi-fi com o DS real (30/10/2026): as partes determinísticas do kit, sem modelo e sem navegador.

O agente de código escreve as telas; o que decide se elas entram é código — o inventário vira quadros,
os lotes isolam a fundação, e o lint reprova import fora do DS, cor escrita à mão e fonte própria.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.prototipo_hifi import dados_da_missao, lotes
from tools.prototipo_hifi import ferramentas

JORNADA = """# Jornada — exp99ef1b (Missão de Teste)

## Seção 3 — Inventário de telas

| ID | Etapa | Ator | Ambiente | Propósito | Peso | Elementos na tela | Ação (verbo nativo) | Resultado da ação | Estados | Cenário de dispositivo | Habilidade (bloco 11) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `E0-PROF-01` | 0 | PROF | Unooria Hub | Escolher a missão | serviço | Grid | Clicar | Avança | padrão · hover | 1:1 / Projeção | — |
| `E2-ALU-01` | 2 | ALU | `unooriaai` | Auditar | alta | Chat | Digitar | Mostra | diálogo padrão · gerando resposta | Desktop base (1024×768) / Bancada | — |
| `E2-SIS-01` | 2 | SIS | `unooriaai` | Inspecionar | serviço | Modal | Fechar | Volta | visualização normal | Desktop base / Bancada | — |
| `E6-ALU-01` | 6 | ALU | `unooriaai` | Caso bônus | média | Tabelas | Cruzar | Selo | neutro | Desktop base / Bancada | — |

## Seção 3b — Instrução fixa por tela
"""

ONE_PAGER = """# One-pager

## 0.2 Como a missão funciona passo a passo

### 1. O professor prepara e libera a atividade
Ele escolhe a missão e libera.

## 4. As etapas

### Etapa 2 — Navegar
O estudante investiga os projetos no chat.

### Etapa 6 — Refletir
Resto de versão antiga.
"""


def _sessao(tmp_path: Path) -> Path:
    (tmp_path / "design").mkdir()
    (tmp_path / "produto").mkdir()
    (tmp_path / "design" / "02-jornada-telas.md").write_text(JORNADA, encoding="utf-8")
    (tmp_path / "produto" / "00-one-pager.md").write_text(ONE_PAGER, encoding="utf-8")
    return tmp_path


def test_inventario_vira_um_quadro_por_estado_sem_a_etapa_6(tmp_path):
    m = dados_da_missao(_sessao(tmp_path))
    pares = [(q["id"], q["estado"]) for q in m["quadros"]]
    assert pares == [("E0-PROF-01", "padrão"), ("E0-PROF-01", "hover"), ("E2-ALU-01", "diálogo padrão"),
                     ("E2-ALU-01", "gerando resposta"), ("E2-SIS-01", "visualização normal")]
    assert m["missao"] == "exp99ef1b" and m["titulo"] == "Missão de Teste"


def test_tamanho_do_quadro_vem_do_cenario_ou_do_ator(tmp_path):
    m = {(q["id"], q["estado"]): q for q in dados_da_missao(_sessao(tmp_path))["quadros"]}
    assert (m[("E0-PROF-01", "padrão")]["largura"], m[("E0-PROF-01", "padrão")]["altura"]) == (1366, 768)
    assert (m[("E2-ALU-01", "diálogo padrão")]["largura"], m[("E2-ALU-01", "diálogo padrão")]["altura"]) == (1024, 768)


def test_painel_da_etapa_vem_do_one_pager(tmp_path):
    etapas = dados_da_missao(_sessao(tmp_path))["etapas"]
    assert etapas["2"]["texto"].startswith("O estudante investiga") and etapas["2"]["fonte"] == "One-pager §4"
    assert etapas["0"]["texto"] == "Ele escolhe a missão e libera."


def test_fundacao_leva_uma_ancora_por_ator_e_o_resto_vai_por_etapa(tmp_path):
    plano = lotes(dados_da_missao(_sessao(tmp_path)))
    assert plano[0] == {"nome": "fundacao", "ids": ["E0-PROF-01", "E2-ALU-01"], "fundacao": True}
    assert plano[1:] == [{"nome": "etapa-2", "ids": ["E2-SIS-01"], "fundacao": False}]


def _ws_com_tela(tmp_path: Path, fonte: str, nome: str = "E2-ALU-01.tsx") -> Path:
    (tmp_path / "telas").mkdir(parents=True, exist_ok=True)
    (tmp_path / "telas" / nome).write_text(fonte, encoding="utf-8")
    return tmp_path


def test_lint_aceita_tela_so_com_ds_e_tokens(tmp_path):
    ws = _ws_com_tela(tmp_path, 'import React from "react";\nimport { Button } from "@unooria/design-system/unooriaai";\n'
                                'import { JanelaUnooriaAI } from "./_comum";\n'
                                'export const estados = { "padrão": () => <div style={{ background: "var(--uai-color-bg)" }}><Button /></div> };\n')
    assert ferramentas.lint(ws) == {"ok": True, "achados": []}


def test_lint_reprova_import_fora_do_ds_cor_fonte_e_estados_ausentes(tmp_path):
    ws = _ws_com_tela(tmp_path, 'import styled from "styled-components";\n'
                                'export const Tela = () => <div style={{ color: "#7FA5E2", fontFamily: "Inter" }} />;\n')
    codigos = {a["codigo"] for a in ferramentas.lint(ws)["achados"]}
    assert codigos == {"import-fora-do-ds", "cor-escrita-a-mao", "fonte-propria", "sem-export-estados"}


def test_lint_ignora_cor_em_comentario(tmp_path):
    ws = _ws_com_tela(tmp_path, '// o DS antigo usava #FFFFFF aqui\nexport const estados = {};\n')
    assert ferramentas.lint(ws)["ok"]


def test_rastreio_de_texto_aponta_a_linha_inventada():
    quadros = [{"id": "E2-ALU-01", "estado": "padrão",
                "texto": ["Começar Análise", "Bem-vindo ao conselho escolar", "Texto que ninguém escreveu"]}]
    r = ferramentas.rastrear_texto(quadros, "Bem-vindo ao Conselho Escolar! … Começar Análise")
    assert r["por_quadro"][0]["fora"] == ["Texto que ninguém escreveu"]
    assert r["percentual"] == 66.7  # 2 de 3 linhas com 12+ caracteres casam; a inventada não


def test_indice_recusa_estado_fora_do_inventario(tmp_path):
    (tmp_path / "dados").mkdir()
    (tmp_path / "dados" / "missao.json").write_text(json.dumps({"quadros": [{"id": "E2-ALU-01", "estado": "padrão"}]}))
    assert ferramentas.indice(tmp_path, "E2-ALU-01", "padrão") == 0
    with pytest.raises(ValueError):
        ferramentas.indice(tmp_path, "E2-ALU-01", "rm -rf /")
