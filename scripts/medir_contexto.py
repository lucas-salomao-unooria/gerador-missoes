#!/usr/bin/env python3
"""scripts/medir_contexto.py

Mede, sem chamar o modelo, o tamanho da instrução de cada agente da esteira sobre um estado salvo — antes e depois do
orçamento de contexto (`tools/contexto.py`, G20 do e2e de 25/10/2026) — e estima o custo de entrada com as chamadas que a
sessão registrou (`custo_missao.execucoes[].tokens_por_agente`, ou o `execucao.tokens_por_agente` da última execução).

A instrução é montada como o ADK a monta: o prompt do agente com as `{chaves}` do estado. O histórico da conversa não
entra (só o A004 o recebia, e desde o G01 ele recebe só a mensagem do PO). É estimativa: caracteres ÷ 3,3.

Uso:
    python scripts/medir_contexto.py <estado.json> [<estado.json> …] [--etapa produto] [--po one-pager-do-po.md]
           [--detalhe]

`--po` troca o one-pager do PO do estado (e o material anexado) por outro — é como se mede o one-pager da 3ef2b, que caiu
antes de gravar estado: o estado de uma missão normal com o one-pager de 360 mil caracteres no lugar do dela.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
if not os.environ.get("BASE_PLATAFORMA_DIR") and (RAIZ / "fixtures" / "base-plataforma").exists():
    os.environ["BASE_PLATAFORMA_DIR"] = str(RAIZ / "fixtures" / "base-plataforma")

_VAR = re.compile(r"{+[^{}]*}+")
_NOME = re.compile(r"^(?:app:|user:|temp:)?[A-Za-z_][A-Za-z0-9_]*$")


def interpolar(template: str, state: Dict[str, Any]) -> str:
    """O `{chave}`/`{chave?}` do ADK (`google.adk.utils.instructions_utils`): o que não é nome de variável fica."""
    def troca(m: "re.Match[str]") -> str:
        nome = m.group().lstrip("{").rstrip("}").strip()
        opcional = nome.endswith("?")
        nome = nome.rstrip("?")
        if not _NOME.match(nome):
            return m.group()
        valor = state.get(nome)
        if valor is None:
            return "" if opcional else m.group()
        return valor if isinstance(valor, str) else str(valor)
    return _VAR.sub(troca, template)


def agentes(etapas: Iterable[str]) -> List[Any]:
    """Os LlmAgent da esteira das etapas, na ordem da árvore (um por nome)."""
    from google.adk.agents.llm_agent import LlmAgent

    from pipeline.orchestrator import create_mission_orchestrator

    raiz = create_mission_orchestrator(stages=list(etapas), com_transversal=False)
    vistos: Dict[str, Any] = {}

    def visita(a: Any) -> None:
        if isinstance(a, LlmAgent) and a.name not in vistos:
            vistos[a.name] = a
        for filho in getattr(a, "sub_agents", None) or []:
            visita(filho)

    visita(raiz)
    return list(vistos.values())


def _e_juiz(agente: Any) -> bool:
    cbs = agente.before_model_callback or []
    cbs = cbs if isinstance(cbs, list) else [cbs]
    return any(getattr(cb, "__name__", "") == "orcamento_de_contexto_juiz" for cb in cbs)


def medir(state: Dict[str, Any], etapas: Iterable[str] = ("produto", "design", "dev"),
          lista: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
    """`[{agente, juiz, antes, depois, cortes, po_primeiro}]` em tokens estimados. `lista`: os agentes já montados."""
    from tools import contexto

    linhas = []
    for a in lista if lista is not None else agentes(etapas):
        if not isinstance(a.instruction, str):
            continue
        instrucao = interpolar(a.instruction, state)
        nova, cortes = instrucao, []
        if _e_juiz(a) and a.name not in contexto.SEM_ORCAMENTO:
            nova, cortes = contexto.cortar_para_o_orcamento(nova, state)
        nova = contexto.po_primeiro(nova, state)
        linhas.append({"agente": a.name, "juiz": _e_juiz(a), "antes": contexto.estimar_tokens(instrucao),
                       "depois": contexto.estimar_tokens(nova), "cortes": cortes,
                       "po_primeiro": nova.startswith(contexto.TITULO_PO_PRIMEIRO)})
    return linhas


def chamadas(state: Dict[str, Any]) -> Dict[str, int]:
    """Quantas chamadas cada agente fez na missão: soma das linhas de `custo_missao` que têm os tokens por agente, ou o
    `execucao` da última execução."""
    total: Dict[str, int] = {}
    linhas = [l for l in (state.get("custo_missao") or {}).get("execucoes") or [] if l.get("tokens_por_agente")]
    fontes = [l["tokens_por_agente"] for l in linhas] or [(state.get("execucao") or {}).get("tokens_por_agente") or {}]
    for fonte in fontes:
        for agente, t in fonte.items():
            total[agente] = total.get(agente, 0) + int(t.get("chamadas", 0) or 0)
    return total


def _milhares(n: float) -> str:
    return f"{int(round(n)):,}".replace(",", ".")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("estados", nargs="+", type=Path)
    ap.add_argument("--etapa", action="append", choices=["produto", "design", "dev"])
    ap.add_argument("--po", type=Path, help="one-pager do PO (markdown) no lugar do do estado")
    ap.add_argument("--material", type=Path, help="com --po: o material anexado (padrão: o próprio one-pager do PO)")
    ap.add_argument("--chamadas", type=Path, action="append",
                    help="estado.json de onde ler as chamadas por agente (padrão: o próprio estado)")
    ap.add_argument("--detalhe", action="store_true")
    args = ap.parse_args(argv)
    etapas = args.etapa or ["produto", "design", "dev"]
    from tools.custo import preco

    entrada = (preco("gemini-3.8-flash") or (0.75, 3.75, 0.075))[0]
    for caminho in args.estados:
        state = json.loads(caminho.read_text(encoding="utf-8"))
        if args.po:
            po = args.po.read_text(encoding="utf-8")
            antigo = str(state.get("one_pager_po") or "")
            state["one_pager_po"] = po
            state["material_anexado"] = args.material.read_text(encoding="utf-8") if args.material else po
            # o one-pager da missão é o do PO, como o G02 o monta, e a conferência o preserva
            state["one_pager"] = po if not antigo else str(state.get("one_pager") or "").replace(antigo, po) or po
            state["one_pager_po_status"] = "aprovado"
        n = chamadas(state)
        for extra in args.chamadas or []:
            for agente, c in chamadas(json.loads(extra.read_text(encoding="utf-8"))).items():
                n[agente] = n.get(agente, 0) + c
        linhas = medir(state, etapas)
        antes = sum(l["antes"] * n.get(l["agente"], 0) for l in linhas)
        depois = sum(l["depois"] * n.get(l["agente"], 0) for l in linhas)
        mudaram = [l for l in linhas if l["antes"] != l["depois"]]
        print(f"## {caminho}")
        print(f"agentes: {len(linhas)} · com instrução diferente: {len(mudaram)} · chamadas contadas: {sum(n.values())}")
        print(f"entrada estimada (instrução × chamadas): {_milhares(antes)} → {_milhares(depois)} tokens · "
              f"US$ {antes * entrada / 1e6:.2f} → US$ {depois * entrada / 1e6:.2f}")
        maior = max(linhas, key=lambda l: l["antes"])
        print(f"maior instrução: {maior['agente']} com {_milhares(maior['antes'])} → {_milhares(maior['depois'])} tokens")
        for l in (linhas if args.detalhe else mudaram):
            marca = " (PO no começo)" if l["po_primeiro"] else ""
            print(f"- {l['agente']}{' [juiz]' if l['juiz'] else ''}: {_milhares(l['antes'])} → {_milhares(l['depois'])}"
                  f" × {n.get(l['agente'], 0)} chamada(s){marca}" + (f" — {'; '.join(l['cortes'])}" if l["cortes"] else ""))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
