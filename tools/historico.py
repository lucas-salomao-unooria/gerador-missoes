"""Série temporal das execuções — a única forma de responder "estamos melhorando?".

Os mesmos ~20 identificadores de achado reapareciam sessão após sessão nas 14 primeiras
execuções, e nada media a tendência: não havia registro do que cada execução produziu, então
nem a queda nem a piora eram visíveis. Uma linha por execução, append-only, ao lado do índice
de missões no bucket.

É deliberadamente magro: veredito por gate, contagem de achados por gate, custo e duração. O
conteúdo dos achados vive na sessão; aqui fica o que se compara entre execuções.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ARQUIVO = "_historico.jsonl"


def caminho(base: Optional[Path] = None) -> Path:
    from tools.catalogo import caminho_indice

    return caminho_indice(base).parent / ARQUIVO


def linha_da_execucao(state: Dict[str, Any], sessao: str = "") -> Dict[str, Any]:
    from tools.diagnostico import GATES, coletar

    dossie = coletar(state)
    execucao = state.get("execucao") or {}
    tokens = execucao.get("tokens") or {}
    achados_por_gate: Dict[str, int] = {}
    for gate in GATES:
        env = state.get(f"{gate['status']}_envelope") or {}
        achados_por_gate[gate["status"]] = len(env.get("achados") or [])

    return {
        "sessao": sessao,
        "quando": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "missao": state.get("missao") or "",
        "veredito": dossie.get("veredito"),
        "gates": {g["status"]: state.get(g["status"]) for g in GATES if state.get(g["status"])},
        "achados_por_gate": {k: v for k, v in achados_por_gate.items() if v},
        "achados_total": sum(achados_por_gate.values()),
        "modelo": execucao.get("modelo"),
        "duracao_s": execucao.get("duracao_s"),
        "tokens": tokens.get("entrada", 0) + tokens.get("saida", 0),
        "chamadas": tokens.get("chamadas", 0),
    }


def registrar(state: Dict[str, Any], sessao: str = "", base: Optional[Path] = None) -> Dict[str, Any]:
    """Acrescenta a linha desta execução. Append-only: o histórico não se reescreve."""
    linha = linha_da_execucao(state, sessao)
    destino = caminho(base)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("a", encoding="utf-8") as saida:
        saida.write(json.dumps(linha, ensure_ascii=False) + "\n")
    return linha


def carregar(base: Optional[Path] = None, ultimas: int = 0) -> List[Dict[str, Any]]:
    destino = caminho(base)
    if not destino.exists():
        return []
    linhas = []
    for bruta in destino.read_text(encoding="utf-8").splitlines():
        bruta = bruta.strip()
        if not bruta:
            continue
        try:
            linhas.append(json.loads(bruta))
        except json.JSONDecodeError:  # pragma: no cover - linha corrompida não derruba a leitura
            continue
    return linhas[-ultimas:] if ultimas else linhas


def tendencia(base: Optional[Path] = None, janela: int = 10) -> Dict[str, Any]:
    """Compara a última metade da janela com a primeira — a pergunta é "melhorou?"."""
    linhas = carregar(base, ultimas=janela)
    if len(linhas) < 4:
        return {"execucoes": len(linhas), "suficiente": False}
    meio = len(linhas) // 2
    antes, depois = linhas[:meio], linhas[meio:]

    def media(grupo: List[Dict[str, Any]], campo: str) -> float:
        valores = [g.get(campo) or 0 for g in grupo]
        return sum(valores) / len(valores) if valores else 0.0

    def bloqueadas(grupo: List[Dict[str, Any]]) -> float:
        return sum(1 for g in grupo if g.get("veredito") == "bloqueado") / len(grupo)

    return {
        "execucoes": len(linhas),
        "suficiente": True,
        "achados": {"antes": round(media(antes, "achados_total"), 1), "depois": round(media(depois, "achados_total"), 1)},
        "bloqueadas": {"antes": round(bloqueadas(antes), 2), "depois": round(bloqueadas(depois), 2)},
        "tokens": {"antes": round(media(antes, "tokens")), "depois": round(media(depois, "tokens"))},
    }
