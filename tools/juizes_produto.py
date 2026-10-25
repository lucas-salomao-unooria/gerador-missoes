"""Juízes de produto recontados em código: decisão do PO não é ressalva, e o contrato aberto vai ao de acordo.

Os juízes de LLM de produto — avaliação pedagógica (A029a), experiência do estudante (A029b) e gate final (A043) —
emitem `aprovado_com_ressalvas` e um envelope com achados `atencao` e `decisao_humana`; o `EnvelopeGateAgent` grava 🟡
quando há qualquer um deles. No levantamento de produto de 24/10/2026 (15 sessões):

- o gate final saiu 🟡 em 15 de 15 por construção: o `043` mandava pôr toda `[PROPOSTA]` do one-pager em «Decisões de
  produto pendentes (🔵)», com o veredito no máximo 🟡, e o one-pager sempre tem proposta (o `014` manda o autor marcar
  o que ele decide). Desde o PR 3 essas propostas vão, uma a uma, à lista do de acordo de produto
  (`tools/fechar_contrato.itens_em_aberto`), e o PO responde ali — o 🔵 repetia a lista e não deixava o gate discriminar;
- a ressalva sobre o que o PO já homologou voltava em cada juiz: na exp06ef1b (727a3c2d e 53e011b6, 08–10/10/2026) o
  tempo em tela de 29 min que o PO aceitou no Pedido 13 («Tempo em tela de 29 min: RESSALVA ACEITA») saiu como ressalva
  na experiência (6.2), na avaliação (4.1) e no gate final — o próprio achado dizendo «homologada pelo PO».

Aqui, sem mexer no que o juiz bloqueou:

- o achado que diz que o PO decidiu **continua contando** (🟡) e ganha a marca `a_conferir`, com a pista de onde a
  decisão parece estar (`tools.decisoes.RegistroDoPO.decisao_repetida`) ou o aviso de que o código não a achou. Até a
  3ª revisão do PR #80 (25/10/2026) o código o tirava da contagem quando achava a pista, e com ele saíam o achado misto
  («Tempo em tela de 29 min aceito pelo PO. Porém a Etapa 4 concentra três decisões seguidas sem feedback», 727a3c2d)
  e a denúncia sem número («O teto de 45 palavras por parágrafo aceito pelo PO no de acordo é excedido em vários
  parágrafos do chat», exp02em1b): separar a repetição da denúncia é interpretar o sentido, e interpretação não esconde
  pendência (princípio da C7, aprovado em 25/10/2026). O PO confere e responde;
- no gate final, o `decisao_humana` que só fala das propostas e dos parâmetros abertos vai para `na_lista_do_de_acordo`,
  quando a lista do de acordo tem itens e toda palavra de conteúdo do achado está neles (`_so_do_contrato`) — o item
  existe na lista que o PO responde no cartão. Sem itens na lista, ou com uma palavra que eles não têm, o achado fica:
  a pendência que o código não acha não some;
- sem nenhum achado que conte, o `aprovado_com_ressalvas` vira `aprovado` (`veredito_original` guarda o do juiz).

O relatório ganha uma nota com cada achado marcado ou retirado e o porquê: o que saiu da contagem não sai da vista.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

#: Severidades que tiram o gate do verde (`agents.callbacks.status_registrado`).
RESSALVAS = ("atencao", "atenção", "decisao_humana", "decisão humana", "ressalva", "oficio", "ofício")
_HUMANO = ("decisao_humana", "decisão humana")
_AMARELOS = ("aprovado_com_ressalvas", "apto_com_ressalvas", "ressalvas", "amarelo", "🟡")

#: O achado diz que o PO decidiu: «homologada pelo PO», «aceita pelo PO», «homologação formal do PO», «travado pelo
#: briefing do PO», «o PO homologou».
_RE_DO_PO = re.compile(
    r"\b(?:aprovad|homologad|ratificad|decidid|aceit|confirmad|travad|fixad|mantid|definid)[oa]s?\s+"
    r"(?:formal(?:mente)?\s+|expressamente\s+)?(?:pel[oa]|do|da)\s+(?:briefing\s+do\s+)?PO\b"
    r"|\b(?:homologa[çc][ãa]o|ratifica[çc][ãa]o|aprova[çc][ãa]o|decis[ãa]o)\s+(?:formal\s+)?d[oa]\s+PO\b"
    r"|\bo\s+PO\s+(?:j[áa]\s+)?(?:aprovou|homologou|ratificou|decidiu|aceitou|fixou|manteve)\b",
    re.IGNORECASE)
#: O `decisao_humana` do gate final que fala do contrato aberto: propostas, parâmetros, marcadores, P0a/P0b…
_RE_CONTRATO = re.compile(r"\bpropost\w*|\bpar[âa]metr\w*|\bmarcador\w*|\bP0[ab]\b|\[ABERTO|\[PROPOSTA|\[PAR[ÂA]METRO",
                          re.IGNORECASE)
#: … que esperam o PO.
_RE_ESPERA_O_PO = re.compile(r"aguard\w*|pendente\w*|a\s+validar|valida[çc][ãa]o|homologa[çc][ãa]o|ratifica[çc][ãa]o|"
                             r"parecer\s+do\s+PO", re.IGNORECASE)
#: O vocabulário com que o juiz nomeia o contrato aberto e a espera, sem dizer de qual item fala: «Propostas estruturais e
#: parâmetros de interface registrados no one-pager aguardando homologação do PO» (exp02em1b, 60cfa7f4). Sem acento.
_VOCABULARIO_DO_CONTRATO = frozenset("""
proposta propostas parametro parametros marcador marcadores aberto abertos aberta abertas pendente pendentes pendencia
pendencias aguarda aguardam aguardando aguardar homologacao homologar ratificacao ratificar validacao validar parecer
formal formais registrado registrados registrada registradas declarado declarados declarada declaradas definicao decisao decisoes produto pager spec missao
secao secoes bloco blocos estruturais estrutural ergonomicas ergonomicos numericos numericas interface quanto
""".split())
#: «Seção 18», «Bloco 12»: onde o item está, não do que ele trata.
_RE_ONDE = re.compile(r"\b(?:se[çc](?:[ãa]o|[õo]es)|blocos?)\s+\d{1,2}\b", re.IGNORECASE)


def _so_do_contrato(resumo: str, itens: List[Any]) -> bool:
    """O achado fala só dos itens da lista do de acordo: toda palavra de conteúdo dele, fora o vocabulário do contrato
    (`_VOCABULARIO_DO_CONTRATO`), está nos itens — assunto, sugestão e a linha de cada marcador. Comparação literal com a
    lista estruturada (`fechar_contrato.itens_em_aberto`), sem tolerância.

    Até a revisão do PR #80 (24/10/2026) bastava falar de proposta e de espera: «Propostas P0b e a divergência entre o
    briefing e o critério 6.2 aguardam homologação do PO» saía inteiro da contagem, com a divergência junto. Até a 3ª
    revisão (25/10/2026) tolerava-se uma palavra de fora quando havia mais dentro («layout Developer Console no DS
    ChatGPT», e89e91b3): a palavra de fora pode ser a pendência que nenhum item registra, e agora o achado fica."""
    from tools.decisoes import _e_conteudo, _palavras_planas

    def raiz(p: str) -> str:
        return p[:-1] if len(p) > 4 and p.endswith("s") else p

    texto_itens = " ".join(" ".join([i.assunto, i.sugestao] + [f"{o.descricao} {o.linha}" for o in i.ocorrencias])
                           for i in itens)
    dos_itens = {raiz(p) for p in _palavras_planas(texto_itens)}
    palavras = [p for p in _palavras_planas(_RE_ONDE.sub(" ", resumo))
                if _e_conteudo(p) and p not in _VOCABULARIO_DO_CONTRATO]
    return all(raiz(p) in dos_itens for p in palavras)


def _severidade(achado: Dict[str, Any]) -> str:
    return str(achado.get("severidade") or "").strip().lower()


def recontar(envelope: Optional[Dict[str, Any]], estado: Dict[str, Any],
             contrato_no_de_acordo: bool = False) -> Tuple[Optional[Dict[str, Any]], str]:
    """`(envelope recontado, nota para o relatório)`. Sem nada a recontar, o envelope volta como veio e a nota vazia.

    Envelope bloqueado não é tocado: o que o juiz reprovou, ele reprovou."""
    if not isinstance(envelope, dict) or not isinstance(envelope.get("achados"), list):
        return envelope, ""
    from agents.callbacks import _ENVELOPE_BLOQUEADO
    from tools import decisoes

    status = str(envelope.get("status") or envelope.get("veredito") or "").strip().lower()
    if status in _ENVELOPE_BLOQUEADO or any(_severidade(a) == "bloqueio" for a in envelope["achados"]
                                            if isinstance(a, dict)):
        return envelope, ""
    registro = decisoes.ha_registro_do_po(estado)
    itens: Optional[list] = None
    ficam: List[Any] = []
    a_conferir: List[Dict[str, Any]] = []
    no_de_acordo: List[Dict[str, Any]] = []
    for achado in envelope["achados"]:
        if not isinstance(achado, dict) or _severidade(achado) not in RESSALVAS:
            ficam.append(achado)
            continue
        resumo = str(achado.get("resumo") or "")
        if _RE_DO_PO.search(resumo) and not decisoes._PEDE_DECISAO.search(resumo):
            # continua contando: o código não separa a repetição da decisão da denúncia de que o documento a descumpre
            marcado = {**achado, "a_conferir": _a_conferir(resumo, registro)}
            a_conferir.append(marcado)
            ficam.append(marcado)
            continue
        if (contrato_no_de_acordo and _severidade(achado) in _HUMANO and _RE_CONTRATO.search(resumo)
                and _RE_ESPERA_O_PO.search(resumo)):
            if itens is None:
                from tools import fechar_contrato as fc

                # só os marcadores do contrato: o texto-chave acima do teto e a mudança do design também vão ao de acordo,
                # mas não são a «proposta» ou o «parâmetro» de que o achado fala
                try:
                    itens = [i for i in fc.itens_em_aberto(estado)
                             if i.tipo in (fc.PARAMETRO, fc.PROPOSTA, fc.ABERTO_PO, fc.ESCOLHA_AMBIENTE)]
                except Exception:  # noqa: BLE001 — sem a lista, o 🔵 fica: a recontagem não derruba o gate
                    itens = []
            if itens and _so_do_contrato(resumo, itens):
                no_de_acordo.append({**achado, "itens_no_de_acordo": len(itens)})
                continue
        ficam.append(achado)
    if not a_conferir and not no_de_acordo:
        return envelope, ""

    novo: Dict[str, Any] = {**envelope, "achados": ficam, "recontado_em_codigo": True}
    if no_de_acordo:
        novo["na_lista_do_de_acordo"] = no_de_acordo
    contam = [a for a in ficam if isinstance(a, dict) and _severidade(a) in RESSALVAS]
    if not contam:
        if status in _AMARELOS:
            novo["status"] = "aprovado"
            novo["veredito_original"] = envelope.get("status")
        if not any(isinstance(a, dict) and _severidade(a) in _HUMANO for a in ficam):
            # a decisão que pedia uma pessoa está na lista do de acordo, e o PO a responde lá
            novo["precisa_humano"] = False

    linhas = ["", "---", "> ⚖️ **Recontado em código** (`tools/juizes_produto.py`): "
              + (f"veredito `{envelope.get('status')}` → `aprovado`. " if novo.get("veredito_original") else "")]
    if a_conferir:
        linhas.append("> Estes achados dizem que o PO decidiu e **continuam contando** (🟡): o código não separa a "
                      "repetição da decisão da denúncia de que o documento a descumpre. O PO confere:")
        for a in a_conferir:
            linhas.append(f"> - 🔎 **a conferir** — «{str(a.get('resumo') or '')[:200]}» — {a['a_conferir'][:300]}")
    if no_de_acordo:
        linhas.append("> Estes achados não contam no veredito:")
        for a in no_de_acordo:
            linhas.append(f"> - 📋 **na lista do de acordo de produto** ({a['itens_no_de_acordo']} item(ns) do contrato "
                          f"aberto, que o PO responde no cartão do parecer) — «{str(a.get('resumo') or '')[:200]}»")
    return novo, "\n".join(linhas)


def _a_conferir(resumo: str, registro: Any) -> str:
    """A marca do achado que diz que o PO decidiu: «a conferir: parece repetir a decisão do PO <qual, de onde>», o que o
    PO recusou, ou que o código não achou o registro."""
    if registro:
        recusada = registro.decisao_recusada(resumo)
        if recusada:
            return f"a conferir: diz que o PO decidiu, mas parece falar do {recusada}"
        pista = registro.decisao_repetida(resumo)
        if pista:
            return f"a conferir: parece repetir a decisão do PO — {pista}"
        return ("a conferir: diz que o PO decidiu, e o código não achou de onde — nem no de acordo de produto, nem nos "
                "pedidos, pareceres de produto ou no one-pager que o PO anexou")
    return "a conferir: diz que o PO decidiu, e a sessão não tem pedido, parecer nem correção do PO"


def recontar_relatorio(relatorio: str, estado: Dict[str, Any], contrato_no_de_acordo: bool = False
                       ) -> Tuple[str, Optional[Dict[str, Any]]]:
    """O relatório de um juiz com o envelope recontado: `(relatorio, envelope)`, para a regressão e o gabarito — o
    `EnvelopeGateAgent` faz o mesmo sobre o relatório da execução."""
    from agents.callbacks import extrair_envelope

    envelope = extrair_envelope(relatorio or "")
    novo, nota = recontar(envelope, estado, contrato_no_de_acordo=contrato_no_de_acordo)
    if not nota:
        return relatorio, envelope
    import json

    return (relatorio or "") + nota + "\n\n```json\n" + json.dumps(novo, ensure_ascii=False) + "\n```\n", novo


def status_recontado(relatorio: str, estado: Dict[str, Any], contrato_no_de_acordo: bool = False) -> Dict[str, Any]:
    """`{status, achados}` no formato dos gates determinísticos, com o status como o dossiê o grava."""
    from agents.callbacks import STATUS_APROVADO, STATUS_BLOQUEADO, inferir_status, status_registrado

    texto, envelope = recontar_relatorio(relatorio, estado, contrato_no_de_acordo)
    # como o `EnvelopeGateAgent`: relatório sem veredito legível é bloqueio
    truncado = inferir_status(texto, envelope) not in (STATUS_APROVADO, STATUS_BLOQUEADO)
    registrado = STATUS_BLOQUEADO if truncado else status_registrado(texto, envelope)
    achados = [a for a in (envelope or {}).get("achados") or [] if isinstance(a, dict)]
    return {"status": registrado, "achados": [{**a, "codigo": str(a.get("codigo") or a.get("id") or "?")}
                                              for a in achados]}
