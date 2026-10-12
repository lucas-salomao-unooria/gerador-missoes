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
from functools import lru_cache
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


#: Gates gravados fora da árvore das etapas (transversal).
_GATES_FORA_DA_ARVORE = {"diagnostico_status": "A117Diagnostico", "catalogo_indice_status": "A119RegistroCatalogo"}


@lru_cache(maxsize=1)
def passo_de_cada_gate() -> Dict[str, Tuple[int, str]]:
    """`{status_key: (num, letra)}`: o passo cujo agente grava o veredito, lido da árvore real das etapas."""
    from agents.design import build_design_stage
    from agents.dev import build_dev_stage
    from agents.produto import build_produto_stage
    from pipeline.orchestrator import iter_agent_tree

    mapa: Dict[str, Tuple[int, str]] = {}
    for raiz in (build_produto_stage(), build_design_stage(), build_dev_stage()):
        for _, agente in iter_agent_tree(raiz):
            passo = passo_do_agente(agente.name)
            if not passo or agente.name.endswith(("Retrabalho", "RetrabalhoBanca")):
                continue
            for atributo in ("status_key", "output_key"):
                chave = getattr(agente, atributo, None)
                if isinstance(chave, str) and chave.endswith("_status"):
                    mapa.setdefault(chave, passo)
    for chave, nome in _GATES_FORA_DA_ARVORE.items():
        mapa.setdefault(chave, passo_do_agente(nome))
    return mapa


def cor_do_veredito(valor: Any) -> str:
    """`vermelho`, `amarelo` ou vazio, para o que os gates gravam (`bloqueado`, `amarelo`, ícone…)."""
    # as mesmas regras do semáforo do app (`_status_icon`): `ressalvas`, `alerta` e `bypassed` também são 🟡
    texto = str(valor or "").strip().lower()
    if any(m in texto for m in ("bloque", "blocked", "vermelh", "reprov", "devolvid", "nao_apto", "não apto", "🔴", "⛔")):
        return "vermelho"
    if any(m in texto for m in ("amarel", "atenc", "atenç", "ressalva", "alerta", "warning", "bypass", "🟡", "⚠")):
        return "amarelo"
    return ""


def cores_dos_passos(gates: Optional[Dict[str, Any]]) -> Dict[Tuple[int, str], Tuple[str, str]]:
    """`{(num, letra): (cor, gate)}`: o pior veredito de cada passo."""
    mapa, cores = passo_de_cada_gate(), {}
    for chave, valor in (gates or {}).items():
        cor, passo = cor_do_veredito(valor), mapa.get(chave)
        if cor and passo and (cores.get(passo, ("",))[0] != "vermelho"):
            cores[passo] = (cor, chave)
    return cores


def etapa_do_agente(nome: str) -> str:
    """A etapa do passo do agente (`A065TelasRetrabalho` → design); vazio se não é passo da esteira."""
    p = passo_do_agente(nome)
    return next((q["etapa"] for q in passos_da_esteira() if p and q["num"] == p[0]), "")


def situacao_dos_passos(passos: List[Dict[str, Any]], etapa: str, agente_atual: str,
                        vistos: Iterable[str]) -> Dict[Tuple[int, str], str]:
    """`{(num, letra): feito | atual | pulado | pendente}`.

    `pulado` é o passo que ficou para trás sem emitir evento: verificador ou juiz que não tinha o que conferir, revisor
    que só roda com reprovação. Sem isso ele ficava cinza como «pendente», com a execução já adiante dele.

    Etapa anterior à que roda está feita; os agentes já iniciados nesta execução estão feitos (inclusive os que
    ficaram à frente quando um loop voltou); o atual pulsa. Um grupo paralelo inteiro pulsa quando o contêiner dele
    é o atual."""
    i_etapa = ORDEM_ETAPAS.index(etapa) if etapa in ORDEM_ETAPAS else -1
    atual = passo_do_agente(agente_atual)
    ja = {p for p in (passo_do_agente(n) for n in vistos) if p}
    adiante = max([n for n, _ in ja] + ([atual[0]] if atual else []), default=0)
    situacao: Dict[Tuple[int, str], str] = {}
    for p in passos:
        chave = (p["num"], p["letra"])
        i = ORDEM_ETAPAS.index(p["etapa"]) if p["etapa"] in ORDEM_ETAPAS else 99
        if atual and (chave == atual or (p["num"] == atual[0] and not atual[1] and p["letra"])):
            situacao[chave] = "atual"
        elif i < i_etapa or chave in ja or (p["letra"] and (p["num"], "") in ja):
            situacao[chave] = "feito"
        elif p["num"] < adiante:
            situacao[chave] = "pulado"
        else:
            situacao[chave] = "pendente"
    return situacao


_CSS = """
.esteira{--fundo:transparent;--texto:#31333f;--trilho:rgba(128,128,128,.25);--feito:#15803d;
--feito-fundo:rgba(34,197,94,.30);--atual:#2563eb;--atual-fundo:rgba(37,99,235,.16);--pendente-fundo:rgba(128,128,128,.16);
--borda:rgba(128,128,128,.32);--vermelho:#b91c1c;--vermelho-fundo:rgba(239,68,68,.32);--amarelo:#92400e;
--amarelo-fundo:rgba(250,204,21,.45)}
.esteira.escuro{--texto:#fafafa;--feito:#86efac;--feito-fundo:rgba(34,197,94,.32);--atual:#3b82f6;
--vermelho:#fca5a5;--vermelho-fundo:rgba(239,68,68,.38);--amarelo:#fde047;--amarelo-fundo:rgba(234,179,8,.32)}
.esteira *{box-sizing:border-box}.esteira{margin:0;font-family:inherit;background:var(--fundo);color:var(--texto);
border:1px solid var(--borda);border-radius:12px;overflow:hidden;width:100%}
.esteira .topo{display:flex;align-items:center;gap:14px;padding:14px 16px;border-bottom:1px solid var(--borda);flex-wrap:wrap}
.esteira .agora{font-weight:700;font-size:17px}.esteira .agora small{opacity:.7;font-weight:400;font-size:14px}
.esteira .barra{flex:1;height:10px;border-radius:5px;background:var(--trilho);overflow:hidden;min-width:120px}
.esteira .barra i{display:block;height:100%;background:linear-gradient(90deg,#22c55e,#3b82f6);transition:width .6s}
.esteira .pct{opacity:.8;font-size:14px;white-space:nowrap;font-weight:600}
.esteira .custo{width:100%;font-size:15px;font-weight:600;font-variant-numeric:tabular-nums}
.esteira .legenda{display:flex;flex-wrap:wrap;gap:18px;font-size:14px;width:100%}
.esteira .legenda i{display:inline-block;width:16px;height:16px;border-radius:4px;margin-right:6px;vertical-align:-3px}
.esteira .raia{display:flex;gap:14px;align-items:flex-start;padding:12px 16px;border-bottom:1px solid var(--borda)}
.esteira .raia:last-child{border-bottom:0}
.esteira .raia.ativa{background:linear-gradient(90deg,transparent,var(--atual-fundo) 50%,transparent);background-size:200% 100%;
animation:corre 3s linear infinite}
@keyframes corre{from{background-position:100% 0}to{background-position:-100% 0}}
.esteira .nome{width:110px;flex:none;font-size:16px;font-weight:700;padding-top:4px}
.esteira .nome small{display:block;opacity:.7;font-weight:500;font-size:13px}
.esteira .passos{display:flex;flex-wrap:wrap;gap:6px;align-items:flex-start}
.esteira .grupo{display:flex;flex-direction:column;gap:3px}
.esteira .p{width:44px;height:30px;border-radius:7px;font-size:13px;font-weight:600;line-height:30px;text-align:center;
background:var(--pendente-fundo);opacity:.85;font-variant-numeric:tabular-nums;position:relative}
.esteira .grupo .p{height:20px;line-height:20px;font-size:11px}
.esteira .p.feito{background:var(--feito-fundo);color:var(--feito);opacity:1}
.esteira .p.pulado{background:transparent;border:2px dashed var(--borda);line-height:26px;opacity:.8}
.esteira .grupo .p.pulado{line-height:16px}
.esteira .p.vermelho{background:var(--vermelho-fundo);color:var(--vermelho);font-weight:800;opacity:1}
.esteira .p.amarelo{background:var(--amarelo-fundo);color:var(--amarelo);font-weight:800;opacity:1}
.esteira .p.atual{background:var(--atual);color:#fff;font-weight:800;opacity:1;animation:pulsa 1.2s ease-in-out infinite;z-index:1}
@keyframes pulsa{0%,100%{box-shadow:0 0 0 0 rgba(59,130,246,.65)}50%{box-shadow:0 0 0 8px rgba(59,130,246,0)}}
@media (prefers-reduced-motion: reduce){.esteira .p.atual,.esteira .raia.ativa{animation:none}}
"""


def html_da_esteira(etapa: str, agente_atual: str, vistos: Iterable[str] = (), *,
                    titulo: str = "", decorrido_s: Optional[int] = None, custo: str = "", escuro: bool = False,
                    gates: Optional[Dict[str, Any]] = None) -> str:
    """A página da animação: uma raia por etapa, um bloco por passo, o atual pulsando e a raia ativa correndo."""
    passos = passos_da_esteira()
    situacao = situacao_dos_passos(passos, etapa, agente_atual, list(vistos))
    feitos = sum(1 for s in situacao.values() if s == "feito")
    pct = round(100 * feitos / max(1, len(situacao)))
    atual = next((p for p in passos if situacao[(p["num"], p["letra"])] == "atual"), None)
    agora = (f"{atual['icone']} {html.escape(atual['rotulo'])}" if atual
             else html.escape(agente_atual or "iniciando…"))
    tempo = f" · {decorrido_s // 60} min {decorrido_s % 60:02d} s" if decorrido_s is not None else ""

    cores = cores_dos_passos(gates)

    def bloco(q: Dict[str, Any]) -> str:
        chave = (q["num"], q["letra"])
        s = situacao[chave]
        cor, gate = cores.get(chave, ("", ""))
        # o veredito pinta o passo já feito; o atual continua azul enquanto roda
        classe = cor if cor and s != "atual" else s
        dica = q["rotulo"] + (f" — {gate}: {(gates or {}).get(gate)}" if gate else "")
        return f'<div class="p {classe}" title="{html.escape(dica)}">{q["num"]:03d}{q["letra"]}</div>'

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

    # sem iframe (`st.html`): a altura acompanha o conteúdo, sem barra de rolagem, e o CSS vale só dentro de .esteira
    # o bloco do `st.html` não herda a cor de texto do tema: quem chama diz se o tema ativo é escuro
    return (f"<style>{_CSS}</style><div class='esteira{' escuro' if escuro else ''}'>"
            f'<div class="topo"><div class="agora">{html.escape(titulo)} {agora}<small>{tempo}</small></div>'
            f'<div class="barra"><i style="width:{pct}%"></i></div><div class="pct">{pct}% dos passos</div>'
            + (f'<div class="custo">{html.escape(custo)}</div>' if custo else "")
            + '<div class="legenda"><span><i style="background:var(--feito-fundo)"></i>feito</span>'
              '<span><i style="background:var(--atual)"></i>agora</span>'
              '<span><i style="background:var(--amarelo-fundo)"></i>atenção</span>'
              '<span><i style="background:var(--vermelho-fundo)"></i>bloqueio</span>'
              '<span><i style="border:2px dashed var(--borda)"></i>não precisou rodar</span>'
              '<span><i style="background:var(--pendente-fundo)"></i>ainda não rodou</span></div>' + "</div>"
            + "".join(raias) + "</div>")
