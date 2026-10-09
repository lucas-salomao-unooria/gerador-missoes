"""O que o QA de design afirma, conferido contra o que existe.

Na missão do 9º ano (exp09ef1b, 06/10/2026) o QA de entregáveis aprovou o design escrevendo, ao lado
do link do Stitch, "todas as 16 telas ativas e vinculadas" — o projeto tinha **6**. E apontou o
protótipo em `design/08-prototipo-navegavel.html`, quando o arquivo que a esteira grava é
`design/08-prototipo.html`. As duas frases são verificáveis em código, e nenhum código as verificava:
o QA é um modelo, e o que ele escreve sobre contagem e nome de arquivo é afirmação, não fato.

Aqui se conferem só as afirmações que têm resposta exata:

- contagem de telas ("todas as N telas", "N de M telas", "N/M telas", "N telas encontradas de M")
  contra o inventário da jornada, o projeto no Stitch (quando a linha fala do Stitch) e o arquivo do
  protótipo (quando fala do protótipo ou do lint);
- nome de artefato citado (`design/…`, `dev/…`, `produto/…`, `NN-nome.ext`) contra os arquivos que
  `pipeline/artifacts.py` de fato grava.

E, separado, a cobertura do Stitch contra o inventário (`cobertura_stitch`), que o
`ArtefatosDesignAgent` cobra: tela do inventário que não está no Stitch não foi desenhada.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Optional, Set

AGENTE = "qa-afirmacoes"

_RE_ID_TELA = re.compile(r"\bE\d-(?:ALU|PROF|SIS)-\d{2}\b")
_RE_TODAS = re.compile(r"\btodas\s+as\s+(\d+)\s+telas\b", re.I)
_RE_PARCIAL = re.compile(r"\b(\d+)\s*(?:/|de)\s*(\d+)\s+telas\b|\b(\d+)\s+telas\s+encontradas\s+de\s+(\d+)\b", re.I)
_RE_ARTEFATO = re.compile(r"(?<![\w/.-])((?:design|dev|produto)/[\w.-]+\.(?:md|html|docx|json)|\d{2}[a-z]?-[\w-]+\.(?:md|html|docx))\b")


def telas_do_inventario(jornada: str) -> List[str]:
    """As telas da tabela «Seção 3» da jornada (`tools/telas.py`); sem a tabela, os IDs citados."""
    from tools import telas

    inv = [t["id"] for t in telas.inventario(jornada)["telas"]]
    return sorted(set(inv)) if inv else sorted(set(_RE_ID_TELA.findall(jornada or "")))


def telas_do_stitch(folha: str) -> Optional[List[str]]:
    """Os títulos das telas na folha `design/10-stitch-telas.md`, ou None quando não há projeto.

    Só a primeira tabela conta: a seção "Visão do professor" repete as telas de professor.
    """
    texto = folha or ""
    if "| Tela |" not in texto:
        return [] if "Nenhuma tela encontrada" in texto else None
    primeira = texto.split("## Visão do professor")[0]
    telas = []
    for linha in primeira.splitlines():
        s = linha.strip()
        if not s.startswith("|") or s.startswith("| Tela |") or re.fullmatch(r"\|[\s:|-]+\|?", s):
            continue
        telas.append(s.strip("|").split("|")[0].strip())
    return telas


def cobertura_stitch(folha: str, jornada: str) -> Dict[str, Any]:
    """Telas no Stitch × inventário da jornada. Menos telas que o inventário = bloqueio, dono `telas`."""
    telas = telas_do_stitch(folha)
    inventario = telas_do_inventario(jornada)
    achados: List[Dict[str, str]] = []
    # Tela com ID fora do padrão não entra no inventário nem na geração (`stitch_geracao.itens_do_relatorio`
    # descarta a linha): na exp01ef1b (08/10/2026) a Sessão B e as telas de erro — seis telas — ficaram com zero
    # telas no Stitch e o status saiu 🟢. Ela é tela do inventário que não foi desenhada.
    from tools.telas import inventario as inventario_completo

    fora = inventario_completo(jornada or "")["fora_do_padrao"]
    if telas is not None and fora:
        achados.append({
            "severidade": "bloqueio", "codigo": "stitch-tela-sem-id", "etapa": "design", "agente_responsavel": "jornada",
            "resumo": f"{len(fora)} tela(s) do inventário com ID fora do padrão `E<etapa>-<ator>-<nn>` não foram ao Stitch: "
                      f"{', '.join(fora)}. Renumere na jornada — sub-etapa continua a numeração da etapa (Sessão B da Etapa 5 → "
                      f"`E5-ALU-04`, `E5-ALU-05`…); tela de erro vai para a etapa em que acontece (`E3-SIS-01`) — e as "
                      f"telas são geradas na rodada seguinte.",
        })
    if telas is None or not inventario:
        status = "bloqueado" if achados else "aprovado"
        return {"status": status, "achados": achados, "stitch": telas, "inventario": inventario, "faltando": []}
    from tools.telas import ids as ids_de_tela

    # Por CONJUNTO de IDs, não por contagem: cinco telas no Stitch, três delas estados da mesma tela,
    # aprovavam um inventário de cinco com três IDs faltando (auditoria de 07/10/2026). E a lista vai
    # inteira no ticket — cortada em 10, o retrabalho desenhava só as dez e o resto nunca chegava.
    no_stitch = {i for t in telas for i in ids_de_tela(t)}
    faltando = [t for t in inventario if t not in no_stitch]
    if faltando:
        achados.append({
            "severidade": "bloqueio", "codigo": "stitch-incompleto", "etapa": "design", "agente_responsavel": "telas",
            "resumo": f"O Stitch tem {len(no_stitch & set(inventario))} de {len(inventario)} tela(s) do inventário da jornada. "
                      f"Faltam: {', '.join(faltando)}. Tela que não está no Stitch não foi desenhada — o protótipo e o "
                      f"PRD a descrevem de memória. Gere cada uma no mesmo projeto, sem priorizar.",
        })
    status = "bloqueado" if achados else "aprovado"
    return {"status": status, "achados": achados, "stitch": telas, "inventario": inventario, "faltando": faltando}


def _arquivos_validos(arquivos: Iterable[str]) -> Set[str]:
    """Caminhos que a esteira grava, sem extensão: o `.md` também sai em `.docx` e `.html`."""
    validos = set()
    for a in arquivos:
        sem_ext = a.rsplit(".", 1)[0]
        validos |= {sem_ext, sem_ext.rsplit("/", 1)[-1]}
    return validos


def conferir_qa(qa: str, folha_stitch: str = "", jornada: str = "", prototipo_html: str = "",
                arquivos: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """Cada contagem de telas e cada nome de artefato que o relatório do QA afirma, contra o real."""
    if arquivos is None:
        from pipeline.artifacts import ARTIFACT_FILES

        arquivos = [nome for _, nome in ARTIFACT_FILES]
    validos = _arquivos_validos(arquivos)
    inventario = telas_do_inventario(jornada)
    # a folha tem uma linha por estado; a afirmação do QA conta telas: «22 de 22 telas … 38 estados» (exp06ef1b)
    linhas_stitch = telas_do_stitch(folha_stitch)
    stitch = sorted({i for t in linhas_stitch for i in _RE_ID_TELA.findall(t)}) if linhas_stitch is not None else None
    no_prototipo = sorted(set(_RE_ID_TELA.findall(prototipo_html or ""))) if prototipo_html else None
    achados: List[Dict[str, Any]] = []
    vistos: Set[tuple] = set()

    def falha(codigo: str, resumo: str, linha: str) -> None:
        if (codigo, resumo) in vistos:
            return
        vistos.add((codigo, resumo))
        achados.append({"severidade": "bloqueio", "codigo": codigo, "etapa": "design", "agente_responsavel": None,
                        "resumo": f"{resumo} Trecho do QA: `{linha.strip()[:200].replace('`', chr(39))}`"})

    for linha in (qa or "").splitlines():
        afirmadas = [(int(m.group(1)), None) for m in _RE_TODAS.finditer(linha)]
        for m in _RE_PARCIAL.finditer(linha):
            achadas, total = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
            afirmadas.append((int(total), int(achadas)))
        if not afirmadas:
            continue
        fala_do_stitch = bool(re.search(r"stitch", linha, re.I))
        fala_do_prototipo = bool(re.search(r"prot[óo]tipo|\blint\b", linha, re.I))
        # «todas as 5 telas do preparo `E0-PROF-01` a `05`» fala de um grupo nomeado, não do projeto inteiro
        cita_grupo = bool(_RE_ID_TELA.search(linha))
        for total, achadas in afirmadas:
            contadas = achadas if achadas is not None else total
            if cita_grupo and inventario and contadas < len(inventario):
                continue
            if fala_do_stitch and stitch is not None and contadas != len(stitch):
                falha("afirmacao-stitch", f"O QA afirma {contadas} telas no Stitch; o projeto tem {len(stitch)}.", linha)
            if fala_do_prototipo and no_prototipo is not None and contadas != len(no_prototipo):
                falha("afirmacao-prototipo", f"O QA afirma {contadas} telas no protótipo; o arquivo tem "
                                             f"{len(no_prototipo)}.", linha)
            # "todas as N" e "a de N" afirmam também o tamanho do inventário — salvo quando falam do Stitch
            if inventario and not fala_do_stitch and total != len(inventario):
                falha("afirmacao-inventario", f"O QA afirma {total} telas no inventário; a jornada declara "
                                              f"{len(inventario)}.", linha)
    for m in _RE_ARTEFATO.finditer(qa or ""):
        citado = m.group(1)
        sem_ext = citado.rsplit(".", 1)[0]
        if sem_ext not in validos:
            linha = (qa or "")[(qa or "").rfind("\n", 0, m.start()) + 1:].split("\n", 1)[0]
            falha("arquivo-inexistente", f"O QA cita `{citado}`, que a esteira não grava (o protótipo é "
                                         f"`design/08-prototipo.html`; a lista está em `pipeline/artifacts.py`).", linha)
    status = "bloqueado" if achados else "aprovado"
    return {"status": status, "achados": achados, "inventario": inventario, "stitch": stitch, "prototipo": no_prototipo}


def relatorio(resultado: Dict[str, Any], missao: str = "") -> str:
    icone = {"aprovado": "🟢", "bloqueado": "🔴"}[resultado["status"]]
    linhas = [f"# Afirmações do QA conferidas{f' — {missao}' if missao else ''}", "",
              f"**Veredito: {icone}** · contagens de telas e nomes de arquivo que o QA escreveu, contra o que existe.", ""]
    contagens = []
    if resultado.get("inventario"):
        contagens.append(f"inventário da jornada: {len(resultado['inventario'])}")
    if resultado.get("stitch") is not None:
        contagens.append(f"Stitch: {len(resultado['stitch'])}")
    if resultado.get("prototipo") is not None:
        contagens.append(f"protótipo: {len(resultado['prototipo'])}")
    if contagens:
        linhas += ["Telas de fato — " + " · ".join(contagens) + ".", ""]
    if not resultado["achados"]:
        linhas.append("- Nenhuma afirmação divergente.")
    for a in resultado["achados"]:
        linhas.append(f"- ⛔ `{a['codigo']}` — {a['resumo']}")
    env = {"agente": AGENTE, "missao": missao, "status": resultado["status"], "achados": resultado["achados"],
           "precisa_humano": False}
    return "\n".join(linhas) + "\n\n```json\n" + json.dumps(env, ensure_ascii=False, indent=1) + "\n```\n"
