"""Contrato de plataforma e origem dos parâmetros, conferidos no one-pager ainda em Produto.

Quatro erros do one-pager canônico nasciam aqui e só eram pegos duas etapas depois, ou nunca:
WebSocket como canal de sala (o A36 reprova no Dev, com o design já feito); progresso do
estudante atribuído a `localStorage`/`IndexedDB` (o estado de missão é do servidor, critério
4.6); descritor SAEB num ano que a prova não avalia; e números apresentados como fato sem
origem no núcleo nem no briefing ("4 segundos por bloco", "20 caracteres", "150 KB").

Este módulo não decide nada: produz achados que o gate estrutural (P1) converte em ❌ pelo
critério indicado e que o revisor (P1b) aplica. ⛔ é violação de contrato de plataforma; ⚠️ é
sinal para o gate ou para o parecer pedagógico conferir.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Set

from tools.bncc import extrair_codigos, extrair_serie, habilidades, secao_bloco
from tools.rastro import _usado_afirmativamente

#: Seções do one-pager canônico onde uma tecnologia de sala ou de cliente costuma ser nomeada.
SECOES_TECNICAS = (8, 10, 12, 16)
#: Seções onde um número sem origem vira regra de sistema (caminho degenerado, falha,
#: professor, tempos, tetos, requisitos). A seção 4 fica fora: é o núcleo, e o núcleo é a origem.
SECOES_NUMERICAS = (7, 8, 9, 10, 15, 16)
#: Anos do Fundamental avaliados pelo SAEB. No Médio a prova é na 3ª série; `em=True` passa.
ANOS_SAEB: Set[int] = {2, 5, 9}

_RE_WEBSOCKET = r"websocket|socket\.io|hub:pause"
_RE_ESTADO_CLIENTE = r"localstorage|indexeddb|sessionstorage"
_RE_SAEB = re.compile(r"\bSAEB\b|\bD\d{1,2}\b")
#: Número com unidade que vira regra de sistema. Cardinalidades soltas ("3 posts") ficam de
#: fora: estão no núcleo e o gate as conta pelo critério 9.1(a).
_RE_NUMERO = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(segundos?|seg\b|s\b|milissegundos?|ms\b|caracteres|KB|MB|GB|px|%)",
    re.IGNORECASE,
)
_MARCADORES = ("[PROPOSTA", "[PARÂMETRO", "[PARAMETRO", "[DECISÃO PENDENTE", "[DECISAO PENDENTE", "🔵")
_RE_ETAPA = re.compile(r"desafiar|navegar|decidir|resultado|aha|explicar|refletir|etapa", re.IGNORECASE)


def _linhas(texto: str) -> List[str]:
    return [l for l in (texto or "").splitlines() if l.strip()]


def _tem_marcador(linha: str) -> bool:
    return any(m in linha for m in _MARCADORES)


def _numeros_com_unidade(texto: str) -> Set[str]:
    return {f"{m.group(1).replace(',', '.')} {m.group(2).lower()}" for m in _RE_NUMERO.finditer(texto or "")}


def _serie(one_pager: str) -> Dict[str, Any]:
    bloco0 = secao_bloco(one_pager, 0)
    serie = extrair_serie(bloco0 or "")
    if not serie["anos"] and not serie["em"]:
        serie = extrair_serie(one_pager[:2000])
    return serie


def validar_one_pager(one_pager: str, nucleo: str = "", briefing: str = "") -> Dict[str, Any]:
    """Aplica as regras ao one-pager. Devolve `status`, `achados` e a série lida."""
    texto = one_pager or ""
    achados: List[Dict[str, str]] = []

    def bloqueio(codigo: str, criterio: str, resumo: str) -> None:
        achados.append({"severidade": "bloqueio", "codigo": codigo, "criterio": criterio, "resumo": resumo})

    def atencao(codigo: str, criterio: str, resumo: str) -> None:
        achados.append({"severidade": "atencao", "codigo": codigo, "criterio": criterio, "resumo": resumo})

    # 1. Canal de sala — a mesma regra do A36, aplicada onde o erro nasce.
    for n in SECOES_TECNICAS:
        secao = secao_bloco(texto, n)
        if secao and _usado_afirmativamente(secao, _RE_WEBSOCKET):
            bloqueio(
                "websocket", "9.1(h)",
                f"Seção {n} propõe WebSocket, socket.io ou `hub:pause` como canal de sala. A plataforma sincroniza a turma por "
                "polling HTTP curto em `expNNefNb_gates_turma` (ADR-93/94); Cloud Run não sustenta WebSocket. Reescrever como polling, sem inventar o intervalo.",
            )

    # 2. Estado de missão é do servidor — nenhuma seção de apoio nomeia armazenamento de cliente.
    secoes_cliente = [str(n) for n in range(5, 19) if (s := secao_bloco(texto, n)) and _usado_afirmativamente(s, _RE_ESTADO_CLIENTE)]
    if secoes_cliente:
        atencao(
            "estado-cliente", "4.6",
            f"Seção(ões) {', '.join(secoes_cliente)} atribuem progresso ou cache a `localStorage`/`IndexedDB`/`sessionStorage`. "
            "Checkpoints e estado de missão vivem no servidor (critério 4.6); o one-pager não nomeia tecnologia de cliente — diz o que se preserva, não onde.",
        )

    # 3. SAEB só nos anos avaliados.
    serie = _serie(texto)
    secao2 = secao_bloco(texto, 2) or ""
    if _RE_SAEB.search(secao2) and not serie["em"] and serie["anos"] and not (serie["anos"] & ANOS_SAEB):
        anos = ", ".join(f"{a}º" for a in sorted(serie["anos"]))
        atencao(
            "saeb-fora-do-ano", "5.6",
            f"A seção 2 cita descritor SAEB numa missão de {anos} ano. O SAEB avalia 2º, 5º e 9º do Fundamental e a 3ª série do Médio; "
            "fora desses anos a linha é \"N/A — ano não avaliado pelo SAEB\", não um descritor emprestado de outro ano.",
        )

    # 4. Número com unidade sem origem no núcleo nem no briefing e sem marcador.
    origem = _numeros_com_unidade((nucleo or "") + "\n" + (briefing or ""))
    sem_origem: List[str] = []
    for n in SECOES_NUMERICAS:
        secao = secao_bloco(texto, n)
        if not secao:
            continue
        for linha in _linhas(secao):
            if _tem_marcador(linha):
                continue
            novos = sorted(_numeros_com_unidade(linha) - origem)
            if novos:
                sem_origem.append(f"§{n}: {', '.join(novos)} — “{linha.strip()[:110]}”")
    if sem_origem:
        atencao(
            "numero-sem-origem", "9.1(i)",
            f"{len(sem_origem)} parâmetro(s) numérico(s) apresentados como fato sem origem no núcleo nem no briefing e sem marcador "
            "`[PARÂMETRO — a definir por produto: …]` ou `[PROPOSTA P0b]`. Ou o número vem da fonte, ou vira marcador:\n"
            + "\n".join(f"    - {s}" for s in sem_origem),
        )

    # 5. Código de Computação fora de Cultura Digital sem momento em tela — sinal para o parecer.
    habs = habilidades()
    linhas2 = _linhas(secao2)
    for i, linha in enumerate(linhas2):
        for c in extrair_codigos(linha):
            hab = habs.get(c)
            if not hab or hab["eixo"] == "CD":
                continue
            janela = " ".join(linhas2[i : i + 3])
            if not _RE_ETAPA.search(janela):
                atencao(
                    "codigo-fora-do-eixo", "5.2",
                    f"`{c}` ({hab['eixo']}: “{hab['habilidade'][:80]}…”) está na seção 2 sem a etapa em que o estudante exercita o texto oficial. "
                    "Código que o livro cita mas a ação em tela não exercita sai do documento.",
                )

    if any(a["severidade"] == "bloqueio" for a in achados):
        status = "bloqueado"
    elif achados:
        status = "amarelo"
    else:
        status = "aprovado"
    return {"status": status, "achados": achados, "serie": {"anos": sorted(serie["anos"]), "em": serie["em"]}}


def relatorio_markdown(resultado: Dict[str, Any], missao: str = "") -> str:
    r = resultado
    icone = {"aprovado": "🟢 CONFORME", "amarelo": "🟡 CONFORME COM AVISOS", "bloqueado": "🔴 VIOLAÇÃO DE CONTRATO"}[r["status"]]
    linhas = [
        f"# Contrato de plataforma e origem dos parâmetros — {missao or 'missão'}",
        "",
        f"**Veredito: {icone}** · one-pager × contrato da plataforma (`references/capacidades-plataforma.md`, ADR-93/94) e origem dos números.",
        "",
        "O gate estrutural aplica cada achado no critério indicado: ⛔ é ❌ direto, ⚠️ entra no complemento pronto pra colar.",
        "",
        "## Achados",
        "",
    ]
    if r["achados"]:
        for a in r["achados"]:
            linhas.append(f"- {'⛔' if a['severidade'] == 'bloqueio' else '⚠️'} **{a['codigo']}** (critério {a['criterio']}) — {a['resumo']}")
    else:
        linhas.append("- Nenhum. Sala por polling, estado no servidor, SAEB no ano certo, números com origem ou marcador.")
    linhas.append("")
    envelope = {
        "agente": "contrato-produto",
        "missao": missao or "",
        "rodada": 1,
        "status": "aprovado" if r["status"] == "aprovado" else ("apto_com_ressalvas" if r["status"] == "amarelo" else "bloqueado"),
        "veredito": {"aprovado": "verde", "amarelo": "amarelo", "bloqueado": "vermelho"}[r["status"]],
        "achados": [
            {"severidade": a["severidade"], "classe": "contrato-produto", "codigo": a["codigo"], "criterio": a["criterio"], "agente_responsavel": "secoes-apoio", "resumo": a["resumo"].split("\n")[0]}
            for a in r["achados"]
        ],
        "precisa_humano": False,
    }
    linhas.append("```json")
    linhas.append(json.dumps(envelope, ensure_ascii=False))
    linhas.append("```")
    return "\n".join(linhas)
