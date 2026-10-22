"""Quem decidiu? O agente não decide no lugar do PO — e quando decide, o documento diz que foi ele.

As três gerações da exp03ef1b (07/10/2026) escreveram decisões que o PO nunca tomou: "Candidato A
aprovado pelo PO", "P0a/P0b homologadas em 24/09", "Quem decidiu: PO (via One-pager v2.2)",
"Rejeitada criação prematura de seção nova". Nenhuma sessão tinha parecer do PO. A decisão do agente,
apresentada como do PO, some da revisão humana: o PO lê "aprovado" e não revisa.

A regra (`references/decisoes-do-agente.md`): o agente só decide quando há coerência e ganho
pedagógico ou funcional claro, e mesmo assim escreve `[PROPOSTA — validar com PO: …]` — a etapa sai
🟡, nunca verde, e a proposta chega ao PO. Este módulo confere as duas metades, em código:

- **decisão atribuída ao PO** sem nenhum registro do PO na sessão (pedido de refazer, parecer, pedido de
  correção) é ⛔: o autor reescreve como proposta. Com registro, é ⚠️ — o código não sabe se o parecer
  diz aquilo, e quem confere é uma pessoa;
- **proposta do agente** é ⚠️ listada: não bloqueia, mas tira a etapa do verde.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

#: Particípio de decisão + "pelo PO". "aprovado pelo PO", "homologadas pelo responsável de produto".
_PARTICIPIO = r"(?:aprovad|homologad|ratificad|decidid|validad|confirmad|fechad|definid|escolhid|autorizad)[oa]s?"
_PO = r"(?:PO|P\.O\.|product owner|respons[áa]vel de produto)"
RE_ATRIBUIDA_AO_PO = re.compile(
    rf"\b{_PARTICIPIO}\s+(?:formalmente\s+|explicitamente\s+)?pel[oa]\s+{_PO}\b"
    rf"|\b(?:o|a)\s+{_PO}\s+(?:j[áa]\s+)?(?:aprovou|homologou|ratificou|decidiu|validou|confirmou|escolheu|definiu|fechou|autorizou)\b"
    rf"|quem\s+decidiu\W{{0,6}}(?:o\s+)?{_PO}\b"
    rf"|\bdecis(?:[ãa]o|[õo]es)\s+(?:fechadas?|tomadas?)\W{{0,6}}(?:pel[oa]\s+)?{_PO}\b"
    rf"|\b{_PO}\s*\(via\b"
    # "PO no one-pager v1.8.0" na coluna «quem decidiu» da spec da exp06ef1b (08/10/2026): o ambiente e a mecânica
    # que a esteira trocou saíram atribuídos ao PO, e a regra não reconhecia a forma
    rf"|\b{_PO}\s+(?:no|na|em|pelo|pela|via)\s+(?:one[- ]?pager|parecer|documento|vers[ãa]o)\b",
    re.IGNORECASE,
)
#: A frase pede a decisão em vez de afirmá-la: "a validar pelo PO", "pendente de homologação pelo PO".
_PEDE_DECISAO = re.compile(
    r"\[PROPOSTA|\[ABERTO|\[DECIS[ÃA]O PENDENTE|🔵|pendente|a\s+validar|validar\s+com|aguard|"
    r"a\s+(?:homologar|aprovar|ratificar|decidir|definir|confirmar)|precisa(?:r)?\s+(?:ser\s+)?(?:aprovad|homologad|validad|decidid)|"
    r"deve(?:rá)?\s+(?:ser\s+)?(?:aprovad|homologad|validad|decidid)|depende\s+d[eo]|cabe\s+ao|sujeit[oa]\s+[àa]|"
    r"n[ãa]o\s+(?:foi|foram|est[áa]|est[ãa]o|h[áa])|sem\s+(?:aprova|homologa|decis|parecer)|ainda\s+n[ãa]o|se\s+o\s+PO",
    re.IGNORECASE,
)
#: A fonte da decisão é o briefing, que é do PO: "Quem decidiu: PO no briefing" é verdade.
_FONTE_BRIEFING = re.compile(r"\bbriefing\b", re.IGNORECASE)
RE_PROPOSTA = re.compile(r"\[PROPOSTA[^\]\n]{0,300}\]", re.IGNORECASE)


def atribuicoes_ao_po(texto: str) -> List[str]:
    """Linhas que afirmam uma decisão do PO (e não a pedem)."""
    saida: List[str] = []
    from tools.conteudo_aprovado import remover_anexo

    # o anexo do PRD é a esteira dizendo que o PO aprovou o one-pager — e aprovou, antes do dev
    for linha in remover_anexo(texto or "").splitlines():
        if RE_ATRIBUIDA_AO_PO.search(linha) and not _PEDE_DECISAO.search(linha) and not _FONTE_BRIEFING.search(linha):
            saida.append(re.sub(r"\s+", " ", linha).strip()[:220])
    return saida


def propostas(texto: str) -> List[str]:
    """Marcadores `[PROPOSTA …]` na ordem em que aparecem, sem repetição."""
    vistos: List[str] = []
    for m in RE_PROPOSTA.finditer(texto or ""):
        trecho = re.sub(r"\s+", " ", m.group(0)).strip()
        if trecho not in vistos:
            vistos.append(trecho)
    return vistos


def ha_registro_do_po(state: Dict[str, Any]) -> bool:
    """A sessão tem alguma palavra do PO: pedido de refazer, parecer de acordo com nota, pedido de correção, ou o
    one-pager que ele anexou. Com ela, a atribuição vira ⚠️ a conferir — o que a esteira mudou no one-pager do PO quem
    barra é a conferência trecho a trecho (`tools/one_pager_po.py`)."""
    return bool(state.get("pedidos_do_po") or str(state.get("notas_de_passagem") or "").strip()
                or str(state.get("pedido_correcao") or "").strip() or str(state.get("one_pager_po") or "").strip())


def achados(texto: str, documento: str, registro_do_po: bool, etapa: str = "produto") -> List[Dict[str, str]]:
    """Achados do documento: decisão atribuída ao PO (⛔ sem registro, ⚠️ com) e propostas a revisar (⚠️)."""
    saida: List[Dict[str, str]] = []
    atribuidas = atribuicoes_ao_po(texto)
    if atribuidas:
        lista = "\n".join(f"    - «{a}»" for a in atribuidas[:8])
        if registro_do_po:
            saida.append({"severidade": "atencao", "codigo": "decisao-atribuida-ao-po", "etapa": etapa, "resumo": (
                f"{documento}: {len(atribuidas)} decisão(ões) atribuída(s) ao PO. A sessão tem parecer do PO, mas o código "
                "não sabe se ele diz isto — confira antes do de acordo:\n" + lista)})
        else:
            saida.append({"severidade": "bloqueio", "codigo": "decisao-atribuida-ao-po", "etapa": etapa, "resumo": (
                f"{documento}: {len(atribuidas)} decisão(ões) atribuída(s) ao PO, e a sessão não tem nenhum parecer, pedido "
                "ou correção do PO. O agente não decide no lugar dele: reescreva cada uma como `[PROPOSTA — validar com PO: "
                "<o que foi decidido> · por quê]` — a etapa sai 🟡 e o PO revisa.\n" + lista)})
    abertas = propostas(texto)
    if abertas:
        lista = "\n".join(f"    - {p}" for p in abertas[:12]) + (f"\n    - … e mais {len(abertas) - 12}" if len(abertas) > 12 else "")
        saida.append({"severidade": "atencao", "codigo": "propostas-a-revisar", "etapa": etapa, "resumo": (
            f"{documento}: {len(abertas)} proposta(s) do agente esperando o PO — não bloqueiam, mas a etapa não sai verde:\n"
            + lista)})
    return saida


def com_achados(resultado: Dict[str, Any], novos: List[Dict[str, str]]) -> Dict[str, Any]:
    """Soma achados a um resultado `{status, achados}` e recalcula o status pela pior severidade."""
    if not novos:
        return resultado
    todos = list(resultado.get("achados") or []) + novos
    if any(a["severidade"] == "bloqueio" for a in todos):
        status = "bloqueado"
    else:
        status = "amarelo" if resultado.get("status") == "aprovado" else resultado.get("status", "amarelo")
    return {**resultado, "achados": todos, "status": status}


_RE_CELULAS = re.compile(r"^\s*\|(.+)\|\s*$")
#: A fonte da lacuna é o parecer de quem liberou a etapa (`notas_de_passagem`): «Parecer humano do produto (21/10/2026)».
_FONTE_PARECER = re.compile(r"\bparecer\b", re.IGNORECASE)


def lacunas_fechadas_pelo_agente(relatorio_lacunas: str, com_parecer: bool = False) -> List[str]:
    """Linhas da tabela do D0 com classe `mecanica`/`curriculo` e cor que não é vermelha.

    O prompt do D0 diz que as duas classes são sempre vermelhas — decisão humana. Na exp01ef1b o D0-7
    saiu `classe: curriculo, cor: verde` e marcou "Resolvido" num `[ABERTO — dono: editorial]`: a
    pendência sumiu do dossiê. Lido pelo nome das colunas «Classe» e «Cor».

    `com_parecer` (a sessão tem parecer do PO): a linha cuja fonte é o parecer não é do agente — a decisão
    humana já foi tomada, e o D0 só a aplicou. Na exp02em1b (22/10/2026) o PO aprovou no parecer de produto as
    duas propostas de mecânica, o D0 fechou-as citando o parecer, e este gate mandou reabri-las para o PO.
    Essas linhas saem em `lacunas_fechadas_pelo_parecer`, para a pessoa conferir.
    """
    return [linha for linha, parecer in _lacunas_fechadas(relatorio_lacunas) if not (com_parecer and parecer)]


def lacunas_fechadas_pelo_parecer(relatorio_lacunas: str) -> List[str]:
    """As linhas de `lacunas_fechadas_pelo_agente` cuja fonte cita o parecer humano."""
    return [linha for linha, parecer in _lacunas_fechadas(relatorio_lacunas) if parecer]


def _lacunas_fechadas(relatorio_lacunas: str) -> List[tuple]:
    """`(linha, fonte_cita_parecer)` de cada lacuna de mecânica ou currículo que não saiu vermelha."""
    import unicodedata

    def norm(t: str) -> str:
        return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn").strip(" `*_")

    saida: List[tuple] = []
    cabecalho: List[str] = []
    for linha in (relatorio_lacunas or "").splitlines():
        m = _RE_CELULAS.match(linha)
        if not m:
            cabecalho = []
            continue
        celulas = [c.strip() for c in m.group(1).split("|")]
        if re.fullmatch(r"[\s:|-]+", m.group(1)):
            continue
        if not cabecalho:
            cabecalho = [norm(c) for c in celulas]
            continue
        if "classe" not in cabecalho or "cor" not in cabecalho:
            continue
        d = dict(zip(cabecalho, celulas))
        classe, cor = norm(d.get("classe", "")), norm(d.get("cor", ""))
        if classe in ("mecanica", "curriculo") and cor and "vermelh" not in cor and "🔴" not in d.get("cor", ""):
            fonte = " ".join(v for k, v in d.items() if k.startswith(("fonte", "base")))
            saida.append((re.sub(r"\s+", " ", linha.strip())[:220], bool(_FONTE_PARECER.search(fonte))))
    return saida
