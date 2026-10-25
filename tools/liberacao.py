"""O gate que uma pessoa liberou: o estado, o dossiê e o catálogo seguem o parecer humano em vigor.

Com o parecer humano (`pipeline/passagem.py`), o 🔴 de um gate deixa de ser a palavra final: o dono da etapa dá *de
acordo* (que só sai sem 🔴) e o `admin` libera com exceção, com o gate vermelho à vista. Até 25/10/2026 o resto da
esteira não sabia disso, e a reprovação liberada continuava mandando:

- 4fd72a9a (exp02ef1b, 23/10/2026, R13 do levantamento de dev de 24/10): o admin liberou o design com exceção às 15:57,
  com o QA de entregáveis e o D0 em 🔴. O dev rodou com `pipeline_bloqueado` e «QA de entregáveis (design) reprovado»
  herdados — 33 agentes marcados como provisórios — e o `conversa.json` gravou `status: blocked` numa missão que
  aguardava o parecer de dev.
- 60cfa7f4 (exp02em1b, 22/10/2026, R12): o dossiê disse «🔴 há impedimentos · 4 impedimento(s)», com o QA de design, as
  afirmações e o D0 que a exceção do admin de 22/10 10:35 liberou e com o de acordo de dev dado.
- 8ce9c32d (exp04ef1b, 25/09/2026, R03): o catálogo registrou `bloqueada` depois do «De acordo para codificação».

A regra, sem interpretar texto: um gate em 🔴 está liberado quando o parecer em vigor da etapa dele (o último *de
acordo* ou exceção ainda válido — o refazer o invalida) foi dado **vendo o gate em 🔴** (`gates` do registro, o semáforo
gravado no momento da decisão). Gate que ficou vermelho depois, sem ninguém ver, continua impedimento. Uma reprovação
registrada (`degradacoes`) está liberada quando a etapa do gate tem parecer em vigor e nenhum gate da etapa está
vermelho sem ter sido visto. A reprovação liberada não some: vai para `degradacoes_liberadas`, com quem liberou e
quando, e o dossiê a mostra.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

LIBERA = ("de_acordo", "excecao")
ETAPAS = ("produto", "design", "dev")
#: As reprovações que uma pessoa liberou, com quem e quando. Recalculada dos pareceres a cada etapa que começa: o refazer
#: invalida o parecer, e a reprovação liberada por ele volta a valer se continuar.
KEY_LIBERADAS = "degradacoes_liberadas"
ROTULO_ACAO = {"de_acordo": "de acordo", "excecao": "liberação com exceção"}
#: A etapa do parecer que cobre cada etapa de reprovação (`pipeline.reexecucao.ROTULOS_GATE_POR_ETAPA` usa `spec`,
#: que é produto no parecer).
_ETAPA_DO_PARECER = {"produto": "produto", "spec": "produto", "design": "design", "dev": "dev"}


def _icone(valor: Any) -> str:
    from pipeline.passagem import _icone as icone

    return icone(valor)


def em_vigor(pareceres: Optional[Iterable[Any]]) -> Dict[str, Dict[str, Any]]:
    """`{etapa: parecer}` com o último *de acordo* ou exceção ainda válido de cada etapa. Pura."""
    saida: Dict[str, Dict[str, Any]] = {}
    for p in pareceres or []:
        if (isinstance(p, dict) and p.get("etapa") in ETAPAS and p.get("acao") in LIBERA
                and p.get("valido", True)):
            saida[p["etapa"]] = p
    return saida


def vermelhos_nao_vistos(estado: Dict[str, Any], etapa: str, parecer: Dict[str, Any]) -> List[str]:
    """Os gates da etapa em 🔴 agora que não estavam em 🔴 quando o parecer foi dado."""
    from pipeline.passagem import semaforo_da_etapa

    vistos = parecer.get("gates") or {}
    return sorted(k for k, icone in semaforo_da_etapa(estado, etapa).items()
                  if icone == "🔴" and vistos.get(k) != "🔴")


def descricao(parecer: Optional[Dict[str, Any]]) -> str:
    """«liberação com exceção — admin, 23/10/2026 15:57:54»."""
    if not parecer:
        return ""
    acao = ROTULO_ACAO.get(str(parecer.get("acao") or ""), str(parecer.get("acao") or ""))
    como = str(parecer.get("como") or parecer.get("autor") or "?")
    return f"{acao} — {como}, {parecer.get('quando') or '?'}"


def gate_liberado(estado: Dict[str, Any], chave_status: str,
                  pareceres: Optional[Iterable[Any]]) -> Optional[Dict[str, Any]]:
    """O parecer em vigor que liberou o gate `chave_status`, em 🔴 agora e em 🔴 quando a pessoa decidiu; ou `None`."""
    if _icone(estado.get(chave_status)) != "🔴":
        return None
    for parecer in em_vigor(pareceres).values():
        if (parecer.get("gates") or {}).get(chave_status) == "🔴":
            return parecer
    return None


def _etapa_da_degradacao(degradacao: Dict[str, Any]) -> Optional[str]:
    from pipeline.reexecucao import ROTULOS_GATE_POR_ETAPA

    return _ETAPA_DO_PARECER.get(ROTULOS_GATE_POR_ETAPA.get(str(degradacao.get("gate") or "").strip(), ""))


def separar_degradacoes(estado: Dict[str, Any], pareceres: Optional[Iterable[Any]]
                        ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """`(vigentes, liberadas)` das reprovações registradas em `degradacoes`. Reprovação de gate sem etapa conhecida fica
    vigente — sem saber de que etapa ela é, não há parecer que a cubra."""
    vigor = em_vigor(pareceres)
    vigentes: List[Dict[str, Any]] = []
    liberadas: List[Dict[str, Any]] = []
    for d in estado.get("degradacoes") or []:
        if not isinstance(d, dict):
            continue
        etapa = _etapa_da_degradacao(d)
        parecer = vigor.get(etapa or "")
        if parecer is None or vermelhos_nao_vistos(estado, etapa, parecer):
            vigentes.append(d)
            continue
        liberadas.append({**d, "etapa": etapa, "acao": parecer.get("acao"),
                          "como": str(parecer.get("como") or parecer.get("autor") or ""),
                          "quando": str(parecer.get("quando") or "")})
    return vigentes, liberadas


def aplicar(estado: Dict[str, Any], pareceres: Optional[Iterable[Any]]) -> Dict[str, Any]:
    """O delta que faz o estado refletir os pareceres: as reprovações liberadas saem de `degradacoes` (e da herança e do
    `pipeline_bloqueado` que elas sustentavam) e ficam em `degradacoes_liberadas`. Pura; vazio quando nada muda."""
    from agents.callbacks import (KEY_DEGRADACOES, KEY_HERANCA, KEY_PIPELINE_BLOQUEADO, KEY_PIPELINE_MOTIVO,
                                  texto_de_heranca)

    pareceres = list(pareceres or [])
    vigor = em_vigor(pareceres)
    # as liberadas de antes que continuam cobertas pelo mesmo parecer: o refazer o invalidou, e a reprovação volta a valer
    # se o gate continuar vermelho na execução nova (ela é registrada de novo pelo gate)
    anteriores = [l for l in estado.get(KEY_LIBERADAS) or [] if isinstance(l, dict)
                  and (vigor.get(str(l.get("etapa") or "")) or {}).get("quando") == l.get("quando")]
    vigentes, liberadas = separar_degradacoes(estado, pareceres)
    if not liberadas and anteriores == list(estado.get(KEY_LIBERADAS) or []):
        return {}
    vistas = {(l.get("gate"), l.get("quando")) for l in liberadas}
    delta: Dict[str, Any] = {KEY_LIBERADAS: [l for l in anteriores if (l.get("gate"), l.get("quando")) not in vistas]
                             + liberadas}
    if liberadas:
        delta[KEY_DEGRADACOES] = vigentes
        delta[KEY_HERANCA] = texto_de_heranca(vigentes)
        delta[KEY_PIPELINE_BLOQUEADO] = bool(vigentes)
        delta[KEY_PIPELINE_MOTIVO] = str(vigentes[0].get("motivo") or "") if vigentes else ""
    return delta


def bloqueada(estado: Dict[str, Any], pareceres: Optional[Iterable[Any]] = None) -> bool:
    """A missão segue bloqueada depois dos pareceres: reprovação vigente que nenhuma pessoa liberou, ou o gate final de
    produto em 🔴 sem liberação. `pareceres` ausente: os que a rodada final copia para o estado (`pareceres_humanos`).

    Sem parecer humano é a regra de antes (`pipeline_bloqueado` ou gate final 🔴)."""
    if pareceres is None:
        pareceres = [p for p in estado.get("pareceres_humanos") or [] if isinstance(p, dict)]
    pareceres = list(pareceres)
    gate_final = str(estado.get("gate_final_status", "")).lower().startswith("bloq")
    if not pareceres:
        return bool(estado.get("pipeline_bloqueado")) or gate_final
    vigentes, liberadas = separar_degradacoes(estado, pareceres)
    if gate_final and gate_liberado(estado, "gate_final_status", pareceres) is None:
        return True
    if vigentes:
        return True
    # `pipeline_bloqueado` sem reprovação registrada é de sessão antiga: só a liberação de alguma reprovação o desfaz
    return bool(estado.get("pipeline_bloqueado")) and not liberadas and not (estado.get("degradacoes") or [])


def parecer_em_vigor(pareceres: Optional[Iterable[Any]]) -> str:
    """O parecer em vigor da etapa mais adiantada: «dev: de acordo — dev, 25/09/2026 16:14:33». Vazio sem parecer."""
    vigor = em_vigor(pareceres)
    for etapa in reversed(ETAPAS):
        if etapa in vigor:
            return f"{etapa}: {descricao(vigor[etapa])}"
    return ""
