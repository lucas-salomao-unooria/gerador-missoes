"""A esteira em movimento: todos os passos, o que já rodou e onde a execução está agora.

Sem Streamlit: devolve o HTML que o app põe num `components.html`. A tela de progresso mostrava só o nome do agente
atual (`agente atual: A065Telas`), e ninguém sabia quanto faltava nem em que parte da esteira a missão estava.

O passo de um agente sai do número no nome (`A065Telas` → 065): o retrabalho (`A065TelasRetrabalho`) e o juiz
interno (`A010FidelidadeNucleoJuiz`) caem no passo do agente pai, e os que rodam em paralelo (`A024a`, `A024b`)
ficam empilhados no mesmo passo.
"""

from __future__ import annotations

import html
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

_RE_PASSO = re.compile(r"^A(\d{3})([a-z]?)")

#: Ordem das etapas na esteira, como `pipeline/orchestrator.STAGES` as monta.
ORDEM_ETAPAS = ("produto", "design", "dev", "transversal")


def passo_do_agente(nome: str) -> Optional[Tuple[int, str]]:
    """`(65, "")` de `A065TelasRetrabalho`; `None` para o que não é passo da esteira (loops, contêineres)."""
    m = _RE_PASSO.match(nome or "")
    return (int(m.group(1)), m.group(2)) if m else None


def passos_da_esteira() -> List[Dict[str, Any]]:
    """Os passos na ordem, com a etapa de cada um, a partir dos metadados que a barra lateral também usa."""
    from pipeline.orchestrator import get_pipeline_agents_metadata

    passos = []
    for meta in get_pipeline_agents_metadata(active_only=False):
        p = passo_do_agente(meta["id"])
        if p:
            passos.append({"num": p[0], "letra": p[1], "etapa": meta["stage"], "etapa_nome": meta["stage_name"],
                           "rotulo": meta["name"], "icone": meta.get("icon", "")})
    return passos


def etapa_do_agente(nome: str) -> str:
    """A etapa do passo do agente (`A065TelasRetrabalho` → design); vazio se não é passo da esteira."""
    p = passo_do_agente(nome)
    return next((q["etapa"] for q in passos_da_esteira() if p and q["num"] == p[0]), "")


def situacao_dos_passos(passos: List[Dict[str, Any]], etapa: str, agente_atual: str,
                        vistos: Iterable[str]) -> Dict[Tuple[int, str], str]:
    """`{(num, letra): feito | atual | pendente}`.

    Etapa anterior à que roda está feita; os agentes já iniciados nesta execução estão feitos (inclusive os que
    ficaram à frente quando um loop voltou); o atual pulsa. Um grupo paralelo inteiro pulsa quando o contêiner dele
    é o atual."""
    i_etapa = ORDEM_ETAPAS.index(etapa) if etapa in ORDEM_ETAPAS else -1
    atual = passo_do_agente(agente_atual)
    ja = {p for p in (passo_do_agente(n) for n in vistos) if p}
    situacao: Dict[Tuple[int, str], str] = {}
    for p in passos:
        chave = (p["num"], p["letra"])
        i = ORDEM_ETAPAS.index(p["etapa"]) if p["etapa"] in ORDEM_ETAPAS else 99
        if atual and (chave == atual or (p["num"] == atual[0] and not atual[1] and p["letra"])):
            situacao[chave] = "atual"
        elif i < i_etapa or chave in ja or (p["letra"] and (p["num"], "") in ja):
            situacao[chave] = "feito"
        else:
            situacao[chave] = "pendente"
    return situacao


_CSS = """
:root{--fundo:#ffffff;--texto:#1f2430;--suave:#6b7280;--trilho:#e5e7eb;--feito:#15803d;--feito-fundo:#dcfce7;
--atual:#2563eb;--atual-fundo:#dbeafe;--pendente-fundo:#f3f4f6;--borda:#e5e7eb}
@media (prefers-color-scheme: dark){:root{--fundo:#0f1117;--texto:#e5e7eb;--suave:#9ca3af;--trilho:#262a35;
--feito:#4ade80;--feito-fundo:#14301f;--atual:#3b82f6;--atual-fundo:#172554;--pendente-fundo:#1b1e27;--borda:#262a35}}
*{box-sizing:border-box}body{margin:0;font-family:"Source Sans Pro",system-ui,sans-serif;background:var(--fundo);color:var(--texto)}
.topo{display:flex;align-items:center;gap:12px;padding:10px 12px;border-bottom:1px solid var(--borda);flex-wrap:wrap}
.agora{font-weight:600}.agora small{color:var(--suave);font-weight:400}
.barra{flex:1;height:6px;border-radius:3px;background:var(--trilho);overflow:hidden;min-width:80px}
.barra i{display:block;height:100%;background:linear-gradient(90deg,var(--feito),var(--atual));transition:width .6s}
.pct{color:var(--suave);font-size:12px;white-space:nowrap}
.custo{width:100%;font-size:12px;color:var(--suave);font-variant-numeric:tabular-nums}
.raia{display:flex;gap:10px;align-items:flex-start;padding:8px 12px;border-bottom:1px solid var(--borda)}
.raia.ativa{background:linear-gradient(90deg,transparent,var(--atual-fundo) 50%,transparent);background-size:200% 100%;
animation:corre 3s linear infinite}
@keyframes corre{from{background-position:100% 0}to{background-position:-100% 0}}
.nome{width:92px;flex:none;font-size:13px;font-weight:600;padding-top:3px}
.nome small{display:block;color:var(--suave);font-weight:400;font-size:11px}
.passos{display:flex;flex-wrap:wrap;gap:4px;align-items:flex-start}
.grupo{display:flex;flex-direction:column;gap:2px}
.p{width:30px;height:22px;border-radius:5px;font-size:9px;line-height:22px;text-align:center;
background:var(--pendente-fundo);color:var(--suave);font-variant-numeric:tabular-nums;position:relative}
.grupo .p{height:14px;line-height:14px}
.p.feito{background:var(--feito-fundo);color:var(--feito)}
.p.atual{background:var(--atual);color:#fff;font-weight:700;animation:pulsa 1.2s ease-in-out infinite;z-index:1}
@keyframes pulsa{0%,100%{box-shadow:0 0 0 0 rgba(37,99,235,.55)}50%{box-shadow:0 0 0 6px rgba(37,99,235,0)}}
@media (prefers-reduced-motion: reduce){.p.atual,.raia.ativa{animation:none}}
"""


def html_da_esteira(etapa: str, agente_atual: str, vistos: Iterable[str] = (), *,
                    titulo: str = "", decorrido_s: Optional[int] = None, custo: str = "") -> str:
    """A página da animação: uma raia por etapa, um bloco por passo, o atual pulsando e a raia ativa correndo."""
    passos = passos_da_esteira()
    situacao = situacao_dos_passos(passos, etapa, agente_atual, list(vistos))
    feitos = sum(1 for s in situacao.values() if s == "feito")
    pct = round(100 * feitos / max(1, len(situacao)))
    atual = next((p for p in passos if situacao[(p["num"], p["letra"])] == "atual"), None)
    agora = (f"{atual['icone']} {html.escape(atual['rotulo'])}" if atual
             else html.escape(agente_atual or "iniciando…"))
    tempo = f" · {decorrido_s // 60} min {decorrido_s % 60:02d} s" if decorrido_s is not None else ""

    def bloco(q: Dict[str, Any]) -> str:
        s = situacao[(q["num"], q["letra"])]
        return f'<div class="p {s}" title="{html.escape(q["rotulo"])}">{q["num"]:03d}{q["letra"]}</div>'

    raias = []
    for chave in ORDEM_ETAPAS:
        da_etapa = [p for p in passos if p["etapa"] == chave]
        if not da_etapa:
            continue
        blocos, i = [], 0
        while i < len(da_etapa):
            grupo = [q for q in da_etapa[i:] if q["num"] == da_etapa[i]["num"]]
            blocos.append(bloco(grupo[0]) if len(grupo) == 1 else
                          '<div class="grupo">' + "".join(bloco(q) for q in grupo) + "</div>")
            i += len(grupo)
        n_feitos = sum(1 for p in da_etapa if situacao[(p["num"], p["letra"])] == "feito")
        ativa = " ativa" if chave == etapa else ""
        raias.append(f'<div class="raia{ativa}"><div class="nome">{html.escape(da_etapa[0]["etapa_nome"])}'
                     f'<small>{n_feitos}/{len(da_etapa)}</small></div><div class="passos">{"".join(blocos)}</div></div>')

    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{_CSS}</style></head><body>"
            f'<div class="topo"><div class="agora">{html.escape(titulo)} {agora}<small>{tempo}</small></div>'
            f'<div class="barra"><i style="width:{pct}%"></i></div><div class="pct">{pct}% dos passos</div>'
            + (f'<div class="custo">{html.escape(custo)}</div>' if custo else "") + "</div>"
            + "".join(raias) + "</body></html>")
