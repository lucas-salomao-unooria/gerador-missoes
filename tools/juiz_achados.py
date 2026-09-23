"""Juiz de achados: o regex acha, o LLM decide, o código confere a citação.

Nove achados dos gates determinísticos respondem à mesma pergunta — o texto AFIRMA o uso de algo que
a plataforma veda, ou CITA para vedar? — e o regex responde com uma lista de negações que sempre fica
atrás da próxima redação. Das menções a WebSocket acusadas em 22 e 23/09/2026, 5 de 5 eram falsas:
"Nenhum protocolo WebSocket é utilizado", "sem necessidade de arquitetura de WebSocket", o envelope
JSON do próprio agente.

A divisão (plano da frente B, `tools/bncc.py:11-13`): o regex continua sendo a rede larga — nada que
ele não marque chega aqui —, o juiz julga só as linhas marcadas, e a decisão só vale com citação
literal que exista no documento. Resposta vazia, JSON inválido ou citação que não está no texto: o
achado fica. Na dúvida, falha fechada.
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

#: código do achado → (padrão que o gate usa, pergunta para o juiz)
PADROES: Dict[str, Tuple[str, str]] = {
    "websocket": (r"websocket|socket\.io|hub:pause",
                  "a linha declara WebSocket, socket.io ou `hub:pause` como canal da missão, ou só o cita para descartar, proibir ou dizer que não existe?"),
    "websocket-mencao": (r"websocket|socket\.io|hub:pause",
                         "a linha propõe WebSocket, socket.io ou `hub:pause` como via de sincronização, ou só o cita para descartar, proibir ou dizer que não existe?"),
    "estado-cliente": (r"localstorage|indexeddb|sessionstorage",
                       "a linha guarda progresso ou estado da missão no navegador (localStorage, IndexedDB, sessionStorage), ou só o cita para proibir?"),
    "campo-dados": (r"\|\s*`?dados`?\s*\||[`\"']?\bdados\b[`\"']?\s*:",
                    "a linha usa um campo `dados` no evento de telemetria, ou só diz que esse campo não existe / não deve ser usado?"),
    "admin-contrato": (r"admin-contrato|@Roles\([^)]*[\"']gestor[\"']",
                       "a linha propõe o papel admin-contrato ou @Roles('gestor') na missão, ou só o cita para vedar?"),
    "rota-motor": (r"/runs/(:id|\{?\w*[iI]d\}?)/eventos",
                   "a linha propõe a missão nova usando POST /runs/:id/eventos, ou só diz que ela não herda essa rota?"),
    "quota-env": (r"AI_DAILY_TOKEN_QUOTA",
                  "a linha configura a quota de IA pela variável AI_DAILY_TOKEN_QUOTA, ou só diz que ela não existe mais?"),
    "enum-estado": (r"\benum\b[^\n]{0,60}\b(estado|status)\b",
                    "a linha declara o estado como enum do Prisma, ou só diz que estado não é enum?"),
    "gabarito-no-cliente": (r"gabarito[^\n]{0,90}\b(no cliente|bundle|front-?end|navegador|localstorage)",
                            "a linha põe o gabarito no cliente (bundle, navegador), ou só diz que ele NÃO vai para lá?"),
}
MAX_FRASES = 6


def _norm(texto: str) -> str:
    sem = "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[`*_\"“”'|]+", " ", re.sub(r"\s+", " ", sem)).strip()


def _decisoes(saida_juiz: str) -> List[Dict[str, Any]]:
    """As decisões do último bloco JSON que as traz — pelo campo que importa, não pelo `status`."""
    for bruto in reversed(re.findall(r"```json\s*(.*?)```", saida_juiz or "", re.DOTALL)):
        try:
            dados = json.loads(bruto)
        except json.JSONDecodeError:
            continue
        if isinstance(dados, dict) and isinstance(dados.get("decisoes"), list):
            return dados["decisoes"]
    return []


def candidatos(achados: List[Dict[str, Any]], documento: str) -> List[Dict[str, Any]]:
    """Um candidato por código julgável presente nos achados, com as linhas que o dispararam."""
    from tools.rastro import frases_afirmativas
    saida, vistos = [], set()
    for a in achados or []:
        codigo = str(a.get("codigo") or "")
        if codigo not in PADROES or codigo in vistos:
            continue
        vistos.add(codigo)
        frases = frases_afirmativas(documento, PADROES[codigo][0])[:MAX_FRASES]
        if frases:
            saida.append({"id": f"C{len(saida) + 1}", "codigo": codigo, "pergunta": PADROES[codigo][1], "frases": frases})
    return saida


def aplicar(achados: List[Dict[str, Any]], cands: List[Dict[str, Any]], saida_juiz: str,
            documento: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """`(achados que ficam, retirados)`. Só sai o achado cujas linhas o juiz julgou TODAS "cita para
    descartar", com citação que exista no documento."""
    decisoes = {str(d.get("id")): d for d in _decisoes(saida_juiz) if isinstance(d, dict)}
    doc = _norm(documento)
    retirar: Dict[str, str] = {}
    for c in cands:
        d = decisoes.get(c["id"])
        if not d or str(d.get("veredito", "")).strip().lower() != "cita_para_descartar":
            continue
        # uma citação por linha marcada: uma só provaria que UMA delas cita para vedar
        citacoes = [str(x) for x in (d.get("citacoes") or ([d["citacao"]] if d.get("citacao") else []))]
        conferidas = [x for x in citacoes if len(_norm(x)) >= 12 and _norm(x) in doc]
        if len(conferidas) >= len(c["frases"]):
            retirar[c["codigo"]] = conferidas[0]
    ficam = [a for a in achados if str(a.get("codigo") or "") not in retirar]
    return ficam, [{"codigo": k, "citacao": v} for k, v in retirar.items()]


def status_de(achados: List[Dict[str, Any]]) -> str:
    if any(str(a.get("severidade", "")).lower() == "bloqueio" for a in achados):
        return "bloqueado"
    return "amarelo" if achados else "aprovado"


def reescrever_relatorio(relatorio: str, envelope: Dict[str, Any], retirados: List[Dict[str, str]]) -> str:
    """O relatório com o envelope JSON atualizado e a seção do que o juiz retirou, com a citação."""
    novo_env = "```json\n" + json.dumps(envelope, ensure_ascii=False, indent=2) + "\n```"
    blocos = list(re.finditer(r"```json.*?```", relatorio or "", re.DOTALL))
    corpo = (relatorio[:blocos[-1].start()] + novo_env + relatorio[blocos[-1].end():]) if blocos else (relatorio or "") + "\n\n" + novo_env
    linhas = ["", "## Revisto pelo juiz de achados", "",
              "O regex marcou estas linhas; o juiz leu cada uma e retirou o achado porque o texto cita para vedar, "
              "não para usar. A decisão só vale com a frase literal abaixo, conferida no documento.", ""]
    linhas += [f"- `{r['codigo']}` retirado — «{r['citacao'][:220]}»" for r in retirados]
    return corpo.rstrip() + "\n" + "\n".join(linhas) + "\n"
