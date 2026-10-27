"""Pacote do designer de 26/10/2026: a instrução fixa do estudante e o protótipo com pronto próprio.

O pacote chegou como pasta solta, editado sobre a main. Três pontos dele tocam código: o protótipo passou
a incluir só a seção dele de `pronto.md` (gerada por script), o QA passou a endereçar o protótipo como
`prototipo-navegavel` — nome que o despacho não conhecia —, e os valores do lo-fi ganharam hexadecimal na
coleção, com `acao-secundaria` transparente. Aqui se prova que os três seguem amarrados.
"""
import re
import subprocess
import sys
from pathlib import Path

from prompts import load_prompt
from prompts.loader import get_prompt_raw

RAIZ = Path(__file__).resolve().parent
KW = dict(stitch_mcp_mode="off", stitch_project_url_base="u", gate_max_rodadas=3, qa_max_rodadas=2)


def test_pronto_do_prototipo_confere_com_a_fonte():
    r = subprocess.run([sys.executable, str(RAIZ / "scripts" / "gerar_pronto_prototipo.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    prototipo = load_prompt("design/079_prototipo.md", **KW)
    assert "<!-- início de references/pronto-prototipo.md -->" in prototipo
    # só a seção dele: as contas dos outros agentes não chegam ao protótipo
    assert "<!-- início de references/pronto.md -->" not in prototipo and "## fecha-lacunas" not in prototipo


def test_qa_endereca_o_prototipo_pelo_nome_do_proprio_prompt():
    from tools.rastro import normalizar_dono

    assert normalizar_dono("prototipo-navegavel") == normalizar_dono("`prototipo`") == "prototipo"
    assert "prototipo-navegavel" in get_prompt_raw("design/088_qa_entregaveis.md")


def test_tokens_do_stitch_sao_os_da_colecao_wireframe_cinza():
    from tools.stitch_geracao import TOKENS, design_md

    colecao = get_prompt_raw("references/wireframe-cinza.md")
    valores = {m.group(1).replace("/", "-"): m.group(2)
               for m in re.finditer(r"^\| `([a-z]+/[a-z]+)` \| ([^|]+) \|", colecao, re.M)}
    assert set(valores) == {nome for nome, _ in TOKENS}
    for nome, valor in TOKENS:
        hexa = re.search(r"#[0-9A-F]{6}", valor)
        if hexa:
            assert hexa.group(0) in valores[nome], nome
        else:  # a ação secundária é contorno sobre fundo transparente, nos dois lados
            assert "transparent" in valor and "transparente" in valores[nome], nome
    assert "#EDEDED" not in design_md() and "vão de 16 px" in design_md()


def test_instrucao_fixa_chega_a_cada_agente_so_com_a_parte_dele():
    partes = {"design/071_jornada.md": "jornada", "design/073_copy_ptbr.md": "copy", "design/075_telas.md": "telas",
              "design/079_prototipo.md": "prototipo", "design/088_qa_entregaveis.md": "qa"}
    for prompt, parte in partes.items():
        texto = load_prompt(prompt, **KW)
        assert "<!-- início de references/padrao-plataforma-instrucao-fixa.md -->" in texto, prompt
        incluidas = set(re.findall(r"<!-- início de references/padrao-plataforma-instrucao-fixa-([a-z]+)\.md -->", texto))
        assert incluidas == {parte}, (prompt, incluidas)
    # ninguém a ativa por conta própria: só o PO, no one-pager
    assert "o agente nunca a ativa por conta própria" in get_prompt_raw("references/formato-spec.md")
