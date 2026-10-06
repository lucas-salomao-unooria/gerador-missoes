"""O banco de conteúdo existe? O brief de assets declara; o código confere se alguém escreveu.

Na missão do 9º ano (exp09ef1b, 06/10/2026) o "banco padrão" saiu da esteira só descrito: 12 PDFs do
Conexão para Continuar, atas do Ponto de Apoio, os cadernos de campo do Mesa Aberta, a tabela de
cancelamentos da Linha 302 e o dossiê histórico da cidade apareciam no brief de assets, com peso e
tela, e nenhuma linha deles estava escrita. A IA simulada tinha quatro falas no roteiro inteiro. E a
coluna Status do brief dizia "Homologado", "Pronto para corte" e "Roteiro aprovado" para arquivos
que não existiam — o PRD leu o status como fato e mandou codificar sobre conteúdo nenhum.

Agora o `A35bBancoConteudo` escreve o texto integral de cada item, e este módulo confere:

1. a coluna Status do brief só aceita `a produzir | rascunho | escrito` — homologar, aprovar e dar
   "pronto" é ato humano, e agente que o escreve está afirmando o que ninguém fez (**bloqueio**);
2. todo ID de conteúdo escrito do inventário (`txt-`, `doc-`, `tab-`, `ata-`, `dos-`, `rot-`, e
   `aud-`/`vid-`, que têm roteiro) tem bloco no banco (**bloqueio**). `pic-` e `ia-` ficam de fora:
   pictograma é desenho, e prompt de sistema é engenharia, escrita no PRD;
3. todo estado do contrato da spec em que a IA simulada fala tem fala no banco, e há boas-vindas,
   resposta para pergunta fora do tema e aviso de limite (**atenção**).
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Dict, List, Optional, Set

AGENTE = "conteudo-check"

#: Status que um agente pode escrever. O resto é decisão de gente.
VOCABULARIO_STATUS = ("a produzir", "rascunho", "escrito")
#: Prefixos de ID cujo item é TEXTO a escrever (ou roteiro, no caso de áudio e vídeo).
PREFIXOS_DE_CONTEUDO = ("txt", "doc", "tab", "ata", "dos", "rot", "aud", "vid")

_RE_ID_CONTEUDO = re.compile(r"\b(?:%s)-[a-z0-9]+(?:-[a-z0-9]+)*-\d{1,3}\b" % "|".join(PREFIXOS_DE_CONTEUDO), re.I)
_RE_ID_QUALQUER = re.compile(r"\b[a-z]{2,4}-[a-z0-9]+(?:-[a-z0-9]+)*-\d{1,3}\b", re.I)
_RE_HUMANO = re.compile(r"homologad|aprovad|pronto|validad|assinad|liberad|congelad", re.I)
#: Linha do contrato em que quem fala é a IA. "Responde à enquete" é o estudante, e "Emitir Parecer" é
#: rótulo de botão: o verbo tem de ser da IA.
_RE_FALA_DA_IA = re.compile(r"\bIA\b|assistente|boas-vindas|\bemite\s+parecer", re.I)
_RE_BLOQUEADA = re.compile(r"\[\s*BLOQUEAD[AO]\s*[—–-]+\s*dono\s*:\s*conte[úu]do", re.I)
#: Falas que toda IA simulada precisa ter, além das do contrato de estados.
FALAS_OBRIGATORIAS = {
    "boas-vindas": r"boas[- ]vindas",
    "pergunta fora do tema": r"fora\s+do\s+tema",
    "aviso de limite": r"\blimite\b",
}


def _norm(texto: str) -> str:
    sem = "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[`*_]", "", sem)).strip(" .")


def _tabela_de_inventario(brief: str) -> List[Dict[str, str]]:
    """As linhas da tabela do inventário (a que tem as colunas ID e Status)."""
    linhas: List[Dict[str, str]] = []
    cab: Optional[List[str]] = None
    for linha in (brief or "").splitlines():
        s = linha.strip()
        if not s.startswith("|"):
            cab = None
            continue
        if re.fullmatch(r"\|[\s:|-]+\|?", s):
            continue
        celulas = [c.strip() for c in s.strip("|").split("|")]
        normal = [_norm(c) for c in celulas]
        if "id" in normal and any(c.startswith("status") for c in normal):
            cab = normal
            continue
        if cab and len(celulas) >= len(cab):
            linhas.append({nome: celulas[i] for i, nome in enumerate(cab)})
    return linhas


def blocos_do_banco(banco: str) -> Dict[str, str]:
    """`{id: corpo}` dos blocos do banco: o heading começa pelo ID do brief (`### txt-exp09ef1b-01 · …`)."""
    blocos: Dict[str, str] = {}
    partes = re.split(r"^(#{2,4}\s+.*)$", banco or "", flags=re.M)
    for i in range(1, len(partes) - 1, 2):
        m = re.match(r"#{2,4}\s+[`*]*([a-z]{2,4}-[a-z0-9]+(?:-[a-z0-9]+)*-\d{1,3})\b", partes[i], re.I)
        if m:
            blocos[m.group(1).lower()] = partes[i + 1]
    return blocos


def estados_de_fala(spec: str) -> List[str]:
    """Estados do contrato da spec em que a IA simulada fala (boas-vindas, responde, emite parecer)."""
    m = re.search(r"^#{2,4}\s*Contrato de estados\b(.*?)(?=^#{1,3}\s|\Z)", spec or "", re.M | re.S | re.I)
    estados: List[str] = []
    for linha in (m.group(1) if m else "").splitlines():
        e = re.match(r"\s*(?:\d+\.|[-*])\s*`([A-Z0-9_]+)`", linha)
        if e and _RE_FALA_DA_IA.search(linha) and e.group(1) not in estados:
            estados.append(e.group(1))
    return estados


def validar(brief: str, banco: str, spec: str = "") -> Dict[str, Any]:
    achados: List[Dict[str, str]] = []

    def falha(codigo: str, resumo: str, severidade: str = "bloqueio", dono: str = "banco-conteudo") -> None:
        achados.append({"severidade": severidade, "codigo": codigo, "etapa": "dev", "agente_responsavel": dono,
                        "resumo": resumo})

    inventario = _tabela_de_inventario(brief)
    for item in inventario:
        status = _norm(item.get("status", ""))
        ident = re.sub(r"[`*]", "", item.get("id", "")).strip()
        if status and status not in VOCABULARIO_STATUS:
            humano = bool(_RE_HUMANO.search(status))
            falha("status-humano" if humano else "status-fora-do-vocabulario",
                  f"`{ident}` está com Status «{item.get('status', '').strip()}» no brief. O vocabulário é "
                  f"`a produzir | rascunho | escrito`"
                  + (" — homologar, aprovar e dar «pronto» é ato humano, e o arquivo nem existe." if humano else "."),
                  dono="brief-assets")

    ids = [i for i in (re.sub(r"[`*]", "", it.get("id", "")).strip().lower() for it in inventario) if i]
    if not ids:
        ids = sorted({m.group(0).lower() for m in _RE_ID_QUALQUER.finditer(brief or "")})
    de_conteudo = [i for i in dict.fromkeys(ids) if _RE_ID_CONTEUDO.fullmatch(i)]
    blocos = blocos_do_banco(banco)
    if not (banco or "").strip() and de_conteudo:
        falha("banco-vazio", f"O banco de conteúdo não foi escrito, e o brief declara {len(de_conteudo)} item(ns) de texto: "
                             f"{', '.join(de_conteudo)}.")
    else:
        sem_bloco = [i for i in de_conteudo if i not in blocos]
        if sem_bloco:
            falha("conteudo-ausente", f"{len(sem_bloco)} item(ns) do brief sem bloco no banco: {', '.join(sem_bloco)}. "
                                      f"Cada um precisa do texto integral, com o heading começando pelo ID.")
        for i in de_conteudo:
            corpo = blocos.get(i, "")
            if i in blocos and len(re.sub(r"\s+", "", corpo)) < 120:
                falha("conteudo-raso", f"O bloco `{i}` tem menos de 120 caracteres: é descrição, não o texto que o "
                                       f"estudante lê.", "atencao")
        for linha in (banco or "").splitlines():
            st = re.search(r"\*\*Status:?\*\*:?\s*([^·|\n*]+)", linha)
            if st and _norm(st.group(1)) not in VOCABULARIO_STATUS:
                falha("status-humano", f"O banco marca um bloco como «{st.group(1).strip()}». Quem escreve o banco "
                                       f"marca `escrito`; homologar é da curadoria humana.")
                break

    estados = estados_de_fala(spec)
    if estados and (banco or "").strip():
        titulos = "\n".join(re.findall(r"^#{2,4}\s+.*$", banco, re.M))
        sem_fala = [e for e in estados if e not in titulos]
        if sem_fala:
            falha("fala-ausente", f"Estado(s) do contrato em que a IA simulada fala, sem fala no banco: "
                                  f"{', '.join(sem_fala)}.", "atencao")
        for nome, padrao in FALAS_OBRIGATORIAS.items():
            if not re.search(padrao, titulos, re.I):
                falha("fala-ausente", f"A IA simulada não tem fala de {nome} no banco.", "atencao")

    status = "bloqueado" if any(a["severidade"] == "bloqueio" for a in achados) else ("amarelo" if achados else "aprovado")
    return {"status": status, "achados": achados, "ids": de_conteudo, "blocos": sorted(blocos), "estados": estados}


def tarefas_sem_conteudo(prd: str, banco: str) -> List[Dict[str, str]]:
    """Tarefa do PRD que consome um ID de conteúdo sem bloco no banco, sem `[BLOQUEADA — dono: conteúdo]`.

    O PRD da exp09ef1b mandava montar a base do assistente simulado (`base_dados_conselho.json`) sobre um
    item "Homologado" que não existia: quem codifica teria de escrever a fala da IA sozinho.
    """
    if not (banco or "").strip():
        return []
    blocos = blocos_do_banco(banco)
    achados, vistos = [], set()
    for linha in (prd or "").splitlines():
        tarefa = re.search(r"\bT-\d{3}\b", linha)
        if not tarefa or _RE_BLOQUEADA.search(linha):
            continue
        for m in _RE_ID_CONTEUDO.finditer(linha):
            ident = m.group(0).lower()
            if ident in blocos or (tarefa.group(0), ident) in vistos:
                continue
            vistos.add((tarefa.group(0), ident))
            achados.append({"severidade": "bloqueio", "codigo": "tarefa-sem-conteudo", "etapa": "dev",
                            "resumo": f"`{tarefa.group(0)}` consome `{m.group(0)}`, que não tem bloco no banco de conteúdo "
                                      f"(`dev/01e-banco-conteudo.md`). Ou o conteúdo é escrito, ou a tarefa leva "
                                      f"`[BLOQUEADA — dono: conteúdo]` — quem codifica não inventa o texto."})
    return achados


def relatorio(resultado: Dict[str, Any], missao: str = "") -> str:
    icone = {"aprovado": "🟢", "amarelo": "🟡", "bloqueado": "🔴"}[resultado["status"]]
    linhas = [f"# Banco de conteúdo conferido{f' — {missao}' if missao else ''}", "",
              f"**Veredito: {icone}** · {len(resultado['ids'])} item(ns) de texto no brief, "
              f"{len(resultado['blocos'])} bloco(s) no banco, {len(resultado['estados'])} estado(s) de fala da IA na spec.", ""]
    if not resultado["achados"]:
        linhas.append("- Todo item do brief tem texto escrito, o Status está no vocabulário e a IA simulada tem fala em cada estado.")
    for a in resultado["achados"]:
        linhas.append(f"- {'⛔' if a['severidade'] == 'bloqueio' else '⚠️'} `{a['codigo']}` — {a['resumo']}")
    env = {"agente": AGENTE, "missao": missao, "status": resultado["status"], "achados": resultado["achados"],
           "precisa_humano": False}
    return "\n".join(linhas) + "\n\n```json\n" + json.dumps(env, ensure_ascii=False, indent=1) + "\n```\n"
