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
    ws = _ws_com_tela(tmp_path, 'import React from "react";\nimport { Button } from "@edu/ui/ds-unooriaai";\n'
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


def _ws_com_inventario(tmp_path: Path) -> Path:
    (tmp_path / "dados").mkdir(exist_ok=True)
    (tmp_path / "dados" / "missao.json").write_text(json.dumps({"quadros": [
        {"id": "E3-ALU-01", "estado": "vazio", "acao": "Marcar 1 projeto / Clicar «Registrar Decisão»"},
        {"id": "E3-SIS-01", "estado": "espera de gate ativa", "acao": "Aguardar mediação oral"}]}), encoding="utf-8")
    return tmp_path


def test_lint_reprova_tela_com_acao_que_nao_responde_a_nada(tmp_path):
    ws = _ws_com_tela(_ws_com_inventario(tmp_path), 'export const estados = { "vazio": () => <div>parada</div> };\n', "E3-ALU-01.tsx")
    assert [a["codigo"] for a in ferramentas.lint(ws)["achados"]] == ["tela-sem-interacao"]


def test_lint_aceita_tela_de_espera_sem_interacao(tmp_path):
    ws = _ws_com_tela(_ws_com_inventario(tmp_path), 'export const estados = { "espera de gate ativa": () => <div>…</div> };\n', "E3-SIS-01.tsx")
    assert ferramentas.lint(ws)["ok"]


def test_lint_reprova_ir_para_tela_ou_estado_fora_do_inventario(tmp_path):
    ws = _ws_com_tela(_ws_com_inventario(tmp_path),
                      'import { useMissao } from "../casca-api";\n'
                      'export const estados = { "vazio": () => { const { ir } = useMissao();\n'
                      '  return <button onClick={() => { ir("E3-SIS-01"); ir("E3-SIS-01", "inventado"); ir("E9-ALU-01"); }} /> } };\n',
                      "E3-ALU-01.tsx")
    trechos = [a["trecho"] for a in ferramentas.lint(ws)["achados"]]
    assert trechos == ["ir(\"E3-SIS-01\", 'inventado')", 'ir("E9-ALU-01")']


def test_lint_aceita_imagem_gerada_e_reprova_a_que_nao_existe(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "caderno.webp").write_bytes(b"RIFF")
    ws = _ws_com_tela(tmp_path, 'import a from "../assets/caderno.webp";\nimport b from "../assets/sumiu.webp";\n'
                                'import { X } from "../dados/mock";\nexport const estados = {};\n')
    assert [(a["codigo"], a["trecho"]) for a in ferramentas.lint(ws)["achados"]] == [("imagem-inexistente", "../assets/sumiu.webp")]


def test_secao_do_quadro_vem_do_ambiente_com_hub_e_apelido():
    from tools.prototipo_hifi import secao_do_ambiente
    secoes = ["unooria", "unooriaai", "instanooria", "whatsappmobile", "unootube"]
    assert secao_do_ambiente("`unooriaai`", secoes) == "unooriaai"
    assert secao_do_ambiente("Unooria Hub", secoes) == "unooria"
    assert secao_do_ambiente("unitube", secoes) == "unootube"
    assert secao_do_ambiente("WhatsApp Mobile", secoes) == "whatsappmobile"
    assert secao_do_ambiente("Instanooria (feed)", secoes) == "instanooria"


def test_quadro_leva_a_secao_e_a_missao_leva_os_temas(tmp_path):
    m = dados_da_missao(_sessao(tmp_path), ["unooria", "unooriaai"])
    assert {(q["id"], q["secao"]) for q in m["quadros"]} == {("E0-PROF-01", "unooria"), ("E2-ALU-01", "unooriaai"), ("E2-SIS-01", "unooriaai")}
    assert m["temas"]["whatsappmobile"] == ("data-wa-theme", "dark")


def test_lint_reprova_import_direto_do_ds_e_arquivo_fora_do_contrato(tmp_path):
    ws = _ws_com_tela(tmp_path, 'import { Button } from "@unooria/design-system/unooriaai";\nexport const estados = {};\n')
    (ws / "telas" / "teste-pb.tsx").write_text("export {};\n", encoding="utf-8")
    assert {a["codigo"] for a in ferramentas.lint(ws)["achados"]} == {"import-direto-do-ds", "arquivo-fora-do-contrato"}


def test_lint_do_css_da_missao_exige_token_e_escopo(tmp_path):
    (tmp_path / "estilos").mkdir()
    (tmp_path / "estilos" / "missao.css").write_text(
        "/* #fff em comentário não conta */\n"
        ".hifi-experiencia .uai-tela, .hifi-hub .x { background: var(--uai-bg-primary, #fff); gap: 8px; }\n"
        ".app { color: #222; }\n@keyframes pulso { from { opacity: 0 } to { opacity: 1 } }\n", encoding="utf-8")
    achados = [(a["codigo"], a["trecho"]) for a in ferramentas.lint(tmp_path)["achados"]]
    assert achados == [("cor-escrita-a-mao", "#222"), ("seletor-sem-escopo", ".app")]


def test_identificador_com_cara_de_documento_precisa_estar_nos_insumos():
    quadros = [{"texto": ["Protocolo: CMAS-2026-EXP09", "Autos: 2026/09-EF", "Prazo 14/02/2026 09:41", "Código DOSSIE-9EF"]}]
    assert ferramentas.identificadores_sem_fonte(quadros, "o código da turma é DOSSIE-9EF") == [
        "CMAS-2026-EXP09", "2026/09-EF", "14/02/2026", "09:41"]


def test_lacunas_visiveis_sao_listadas_uma_vez():
    quadros = [{"texto": ["[[LACUNA: código da turma]]", "x"]}, {"texto": ["[[LACUNA: código da turma]]"]}]
    assert ferramentas.lacunas(quadros) == ["código da turma"]


def test_estado_com_barra_ou_crase_dentro_de_parenteses_e_um_estado_so():
    from tools import telas
    jornada = ("## Seção 3 — Inventário de telas\n\n| ID | Etapa | Estados |\n|---|---|---|\n"
               "| `E2-ALU-02` | 2 | processando OCR (0.8s / 1.2s) · dados incorporados |\n"
               "| `E2-SIS-01` | 2 | visualização normal · `ERRO_MIDIA_FALHOU` (extrato texto) |\n")
    estados = {t["id"]: t["estados"] for t in telas.inventario(jornada)["telas"]}
    assert estados == {"E2-ALU-02": ["processando OCR (0.8s / 1.2s)", "dados incorporados"],
                       "E2-SIS-01": ["visualização normal", "ERRO_MIDIA_FALHOU (extrato texto)"]}


def test_gerador_acha_publica_e_empacota_o_prototipo_da_sessao(tmp_path):
    import base64
    import gzip
    import importlib.util
    import io
    import zipfile
    from tools.prototipo_hifi import no_gerador as hifi

    (tmp_path / "sessao").mkdir()
    sessao = _sessao(tmp_path / "sessao")
    assert hifi.tem_insumos(sessao) and not hifi.pronto(sessao) and hifi.em_andamento(sessao) is None
    ws = tmp_path / "ws"
    for rel, texto in {"prototipo.html": "<!doctype html><title>P</title>", "RELATORIO.md": "# r",
                       "relatorios/final.json": '{"telas": 3}', "capturas/E2-ALU-01--padrao.png": "png",
                       "capturas/E2-ALU-01--padrao--interacao.png": "png", "telas/E2-ALU-01.tsx": "export {};",
                       "dados/mock.ts": "export {};", "estilos/missao.css": "", "plataforma.tsx": ""}.items():
        (ws / rel).parent.mkdir(parents=True, exist_ok=True)
        (ws / rel).write_text(texto, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("ph", "scripts/prototipo_hifi.py")
    ph = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ph)
    ph.publicar(ws, hifi.pasta(sessao))

    assert hifi.pronto(sessao) and hifi.resumo(sessao) == {"telas": 3}
    # a captura da interação é do trabalho do agente, não do resultado
    assert sorted(p.name for p in (hifi.pasta(sessao) / "capturas").iterdir()) == ["E2-ALU-01--padrao.png"]
    nomes = zipfile.ZipFile(io.BytesIO(hifi.zip_das_telas(sessao))).namelist()
    assert sorted(nomes) == ["dados/mock.ts", "estilos/missao.css", "plataforma.tsx", "telas/E2-ALU-01.tsx"]
    assert gzip.decompress(base64.b64decode(hifi.html_comprimido(sessao))).startswith(b"<!doctype html>")


def test_geracao_que_parou_sem_publicar_mostra_o_fim_do_log(tmp_path):
    from tools.prototipo_hifi import no_gerador as hifi

    sessao = tmp_path
    log = tmp_path / "geracao.log"
    log.write_text("…\nRuntimeError: cota esgotada\n", encoding="utf-8")
    hifi.pasta(sessao).mkdir(parents=True)
    (hifi.pasta(sessao) / "execucao.json").write_text(json.dumps({"pid": 999999, "workspace": str(tmp_path), "log": str(log)}))
    assert hifi.em_andamento(sessao) is None
    assert "cota esgotada" in hifi.falhou(sessao)
