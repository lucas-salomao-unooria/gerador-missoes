"""O aprendizado (A128) afirma o que o código conferiu, e o resto sai marcado como leitura do agente.

O A128 é um LLM que escreve o registro da execução a partir dos relatórios. Ele só enxerga o que os gates enxergaram, e
escrevia fatos que ninguém conferiu (levantamento de dev de 24/10/2026, C6):

- 53e011b6 (exp06ef1b, R10): «Mecânicas ausentes encontradas tardiamente: Nenhuma» e «Contagem de lacunas fechadas pelo
  dono errado: 0», num PRD que trocou a H3 e perdeu o teto de 35 palavras do §15;
- a linha de catálogo proposta com status «em produção» — promover é ato humano (`scripts/catalogo.py promover`).

Sem interpretar a prosa do agente (regex só para comparação literal sobre dado estruturado), duas coisas:

1. A coluna «Status» da linha de catálogo que o agente propõe é comparada, literalmente, com o vocabulário fechado do
   catálogo: status de promoção (`STATUS_HUMANOS`) é trocado pelo do registro automático, com a proposta dele ao lado.
2. Uma seção «Fatos conferidos em código» entra antes do envelope do agente, com os números lidos do estado — dossiê,
   parecer humano, catálogo, montagem do PRD, rastro e rodadas —, e a frase que diz o que não foi conferido.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

TITULO_FATOS = "## Fatos conferidos em código"
_RE_TITULO_FATOS = re.compile(r"^##\s*Fatos conferidos em c[óo]digo\b.*$", re.M)
#: A anotação que `corrigir_status_do_catalogo` deixa na célula: é dela, então lida de volta literalmente.
_RE_JA_TROCADO = re.compile(r"\(o agente propôs «([^»]+)»")
_RE_ENVELOPE_NO_FIM = re.compile(r"(?:\n[ \t]*(?:-{3,}|\*{3,})[ \t]*)?\s*```json\s(?:(?!```)[\s\S])*```\s*\Z")
#: Os achados da montagem do PRD e do handoff que respondem às afirmações que o agente fazia sem conferir.
CODIGOS_DA_MONTAGEM = (("hipotese-diverge", "Hipóteses do corpo diferentes das do §17"),
                       ("teto-ausente", "Tetos do §15 ausentes"),
                       ("teto-diverge", "Tetos do §15 com outro valor"),
                       ("numero-sem-origem", "Números de regra sem origem no contrato"),
                       ("texto-chave-reescrito", "Textos-chave reescritos"))
#: Rodadas que o registro conta, com o nome que o time usa.
RODADAS = (("gate_estrutural_rodada", "gate estrutural"), ("comite_canais_rodada", "comitê dos canais"),
           ("avaliacoes_rodada", "avaliações"), ("spec_rodada", "spec"), ("qa_design_rodada", "QA de design"),
           ("handoff_rodada", "handoff"), ("banca_rodada", "banca de dev"), ("prd_rodada", "PRD"))


def _norm(texto: str) -> str:
    import unicodedata

    return "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower())
                   if unicodedata.category(c) != "Mn").strip(" `*_")


def corrigir_status_do_catalogo(texto: str, status_automatico: str) -> Tuple[str, List[str]]:
    """O texto com a célula «Status» da linha de catálogo trocada quando o agente pôs um status de promoção. Devolve o
    texto e os status que ele propôs e foram trocados."""
    from tools.catalogo import STATUS_HUMANOS

    humanos = {_norm(s) for s in STATUS_HUMANOS}
    linhas = (texto or "").split("\n")
    trocados: List[str] = []
    coluna = None
    for i, bruta in enumerate(linhas):
        linha = bruta.strip()
        if not (linha.startswith("|") and linha.endswith("|") and len(linha) > 2):
            coluna = None
            continue
        if set(linha) <= set("|-: "):
            continue
        celulas = linha.strip("|").split("|")
        normal = [_norm(c) for c in celulas]
        if any("descoberta" in c for c in normal) and "status" in normal:
            coluna = normal.index("status")
            continue
        if coluna is None or coluna >= len(celulas):
            continue
        proposto = celulas[coluna].strip()
        ja = _RE_JA_TROCADO.search(proposto)
        if ja:
            # a célula que esta conferência já trocou (o aprendizado conferido de novo): a proposta do agente segue à vista
            trocados.append(ja.group(1))
            continue
        if _norm(proposto) in humanos:
            celulas[coluna] = (f" {status_automatico} (o agente propôs «{proposto.strip('`* ')}»: promover é ato "
                               "humano) ")
            trocados.append(proposto.strip("`* "))
            recuo = bruta[: len(bruta) - len(bruta.lstrip())]
            linhas[i] = recuo + "|" + "|".join(celulas) + "|"
    return "\n".join(linhas), trocados


def _codigos(envelope: Any) -> Dict[str, int]:
    contagem: Dict[str, int] = {}
    for a in (envelope.get("achados") or []) if isinstance(envelope, dict) else []:
        if isinstance(a, dict) and a.get("codigo"):
            contagem[str(a["codigo"])] = contagem.get(str(a["codigo"]), 0) + 1
    return contagem


def _lacunas_de_produto_a_jusante(state: Dict[str, Any]) -> int:
    """Pendências de produto que design e dev acharam: os tickets devolvidos a produto e os achados de dono produto nos
    rastros de design e de dev."""
    from pipeline.passagem import devolucoes_a_produto

    n = len(devolucoes_a_produto(state))
    for chave in ("rastro_design_status_envelope", "rastro_lacunas_status_envelope"):
        env = state.get(chave)
        for a in (env.get("achados") or []) if isinstance(env, dict) else []:
            if isinstance(a, dict) and str(a.get("etapa") or a.get("codigo") or "") in ("produto", "input"):
                n += 1
    return n


def fatos(state: Dict[str, Any], status_automatico: str, trocados: List[str]) -> str:
    """A seção «Fatos conferidos em código», lida do estado."""
    from tools import diagnostico, liberacao

    d = diagnostico.coletar(state)
    rotulo = {"aprovado": "🟢 tudo passou", "amarelo": "🟡 passou com ressalvas", "bloqueado": "🔴 há impedimentos"}
    linhas = [TITULO_FATOS, "",
              "Lidos do estado por código, depois que o agente escreveu. As seções acima são a leitura dele: contagem ou "
              "ausência («nenhuma», «0») que ele afirme e que não esteja nesta tabela nem no diagnóstico **não foi "
              "conferida**.", "",
              "| Fato | Valor | De onde vem |", "|---|---|---|",
              f"| Veredito do diagnóstico | {rotulo.get(d['veredito'], d['veredito'])} | `diagnostico-execucao.md` |",
              f"| Impedimentos · ressalvas · decisões de pessoa | {len(d['bloqueios'])} · {len(d['ressalvas'])} · "
              f"{len(d['humanos'])} | diagnóstico |",
              f"| Reprovações que uma pessoa liberou | {len(d.get('liberadas') or [])} | parecer humano |"]
    vermelhos = [g["rotulo"] for g in d["gates"] if g.get("icone") == "🔴"]
    linhas.append(f"| Gates em 🔴 | {', '.join(vermelhos) if vermelhos else 'nenhum'} | estado da missão |")
    linhas.append(f"| Status no catálogo | `{status_automatico}`"
                  + (f" (o agente propôs «{'», «'.join(trocados)}»; promover é ato humano)" if trocados else "")
                  + " | registro automático (`tools/catalogo.py`) |")
    parecer = liberacao.parecer_em_vigor([p for p in state.get("pareceres_humanos") or [] if isinstance(p, dict)])
    linhas.append(f"| Parecer humano em vigor | {parecer or 'nenhum registrado nesta execução'} | `conversa.json` |")
    for chave, rotulo_doc in (("montagem_prd_status", "PRD"), ("montagem_handoff_status", "handoff")):
        if chave not in state:
            linhas.append(f"| Montagem do {rotulo_doc} (números, hipóteses, tetos) | não medida nesta execução | — |")
            continue
        cont = _codigos(state.get(f"{chave}_envelope"))
        partes = [f"{nome}: {cont.get(cod, 0)}" for cod, nome in CODIGOS_DA_MONTAGEM]
        linhas.append(f"| Montagem do {rotulo_doc} | {' · '.join(partes)} | `{chave}` |")
    linhas.append(f"| Pendências de produto achadas por design ou dev | {_lacunas_de_produto_a_jusante(state)} | "
                  "devoluções a produto e rastros de design e de dev |")
    rodadas = [f"{nome} {state[k]}" for k, nome in RODADAS if isinstance(state.get(k), int) and state.get(k)]
    linhas.append(f"| Rodadas | {' · '.join(rodadas) if rodadas else '—'} | contadores dos loops |")
    return "\n".join(linhas) + "\n"


def conferir(texto: str, state: Dict[str, Any]) -> str:
    """O aprendizado com o status do catálogo conferido e os fatos em código antes do envelope do agente. Idempotente:
    a seção de fatos de antes sai e entra a de agora."""
    if not isinstance(texto, str) or not texto.strip():
        return texto
    from tools.catalogo import ficha_da_execucao

    status = str(ficha_da_execucao(state).get("status") or "em criação")
    corpo, trocados = corrigir_status_do_catalogo(texto, status)
    m = _RE_TITULO_FATOS.search(corpo)
    envelope = ""
    fim = _RE_ENVELOPE_NO_FIM.search(corpo)
    if fim:
        envelope = corpo[fim.start():].strip()
        corpo = corpo[: fim.start()]
    if m and m.start() < len(corpo):
        corpo = corpo[: m.start()]
    secao = fatos(state, status, trocados)
    return corpo.rstrip() + "\n\n" + secao + ("\n" + envelope + "\n" if envelope else "")
