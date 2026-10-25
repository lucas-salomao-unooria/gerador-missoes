"""O de acordo de produto fecha o contrato e grava. Determinístico, sem LLM.

Desde 21/09/2026 (fa39727) produto escreve `[PARÂMETRO — a definir por produto: …]` e `[PROPOSTA — validar com PO: …]`
no lugar de inventar, por regra de prompt (`014_secoes_apoio.md`). Nenhum passo exigia que o PO fechasse esses marcadores
antes do design, e o que ele decidia no de acordo não era gravado: na exp02em1b (60cfa7f4) o PO decidiu 90 s, 45
palavras e «StoryPoll — não implementar» no de acordo de 21/10/2026 15:43, o one-pager continuou com [PARÂMETRO] e com o
StoryPoll, e quem aplicou a decisão foi o D0, no design (plano «Produto dono do contrato», PR 3, decisões D3 e D5).

Aqui:

- `itens_em_aberto` lista cada [PARÂMETRO], [PROPOSTA] e [ABERTO — dono: PO] do one-pager e da spec do Gate 0, agrupado
  pelo assunto (o mesmo parâmetro aparece no one-pager, na spec e na lista de pendências), com a sugestão do agente e onde
  aparece. Quando a missão volta de design, entram também as mudanças que o D0/D9 quiseram fazer no texto do Gate 0
  (os `[ABERTO — dono: PO]` do cartão de design, PR 2).
- `respostas_anteriores` acha o que o PO já respondeu — no cartão, ou com «→» num de acordo antigo — para o cartão vir
  preenchido depois de um refazer: a decisão sobrevive a ele.
- `decidir` confere as respostas e monta as trocas de linha; `aplicar_edicoes` as executa sobre o texto; `gravar` grava
  no `estado.json` e nos artefatos da sessão. O texto que entra é «<valor> — PO, parecer de <data>».

«Tudo de acordo» no comentário não responde nada: só a lista do cartão responde, item a item ou pelo «Aceitar as
sugestões» clicado sobre a lista que está na tela (D3).
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import time
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from tools.rastro import cita_o_marcador

ACEITAR = "aceitar"
OUTRO = "outro"
RECUSAR = "recusar"
DESIGN = "design"
ROTULO_RESPOSTA = {ACEITAR: "Aceitar a sugestão", OUTRO: "Outro valor", RECUSAR: "Recusar",
                   DESIGN: "Deixar para o design"}

PARAMETRO = "parametro"
PROPOSTA = "proposta"
ABERTO_PO = "aberto_po"
MUDANCA_GATE0 = "mudanca_gate0"
#: Texto-chave que a criança lê acima do teto de palavras (PR 7 do plano, D1): o lint de produto o acusa, e o PO mantém o
#: texto ou escreve outro (`tools/textos_chave.py`).
TEXTO_TETO = "texto_teto"
#: Ambiente novo ou mini-jogo que a spec fixa sem o PO ter decidido (PR 8 do plano, D8): a escolha é dele, e entra na lista
#: como proposta mesmo quando o autor da spec não escreveu o marcador (`tools/ambiente.escolha_do_po`).
ESCOLHA_AMBIENTE = "escolha_ambiente"
ROTULO_TIPO = {PARAMETRO: "[PARÂMETRO]", PROPOSTA: "[PROPOSTA]", ABERTO_PO: "[ABERTO — dono: PO]",
               MUDANCA_GATE0: "Mudança do design no texto do Gate 0", TEXTO_TETO: "Texto-chave acima do teto",
               ESCOLHA_AMBIENTE: "[PROPOSTA] Ambiente novo ou mini-jogo"}

#: Onde o contrato aberto é procurado. A spec é a do Gate 0: na sessão anterior ao PR 6, `spec_missao` pode já trazer os
#: blocos 13 e 14 do design; na nova ela é a de produto, com o bloco 15 da completude, cujos marcadores entram na lista.
DOC_ONE_PAGER = "one_pager"
DOC_SPEC = "spec"
CHAVES_SPEC = ("spec_missao_gate0", "spec_missao")
ROTULO_DOC = {DOC_ONE_PAGER: "one-pager", DOC_SPEC: "spec do Gate 0"}

#: Decisões gravadas, da mais antiga à mais nova. Fica fora de toda lista de `pipeline/reexecucao.py`: sobrevive ao refazer.
KEY_DECISOES = "decisoes_do_po"

_RE_MARCADOR = re.compile(
    r"\[(PAR[ÂA]METRO|PROPOSTA)\b([^\]\n]{0,1500})\]"
    r"|\[ABERTO\s*[—–-]\s*dono:\s*(?:o\s+)?PO\b([^\]\n]{0,1500})\]")
#: «…», «...», «<x>»: o documento cita o formato do marcador, não abre pendência («L2 — Aplicação do marcador
#: `[PARÂMETRO — a definir por produto: …]`», one-pager da exp02em1b).
_RE_PLACEHOLDER = re.compile(r"^\s*(?:…|\.\.\.|<[^>]*>|x)?\s*$")
_RE_SUGESTAO = re.compile(r"sugest[ãa]o\s*:\s*([^·;|]+)", re.I)
_RE_PQ = re.compile(r"\bPQ-\d+\b")
#: Número que decide regra (tempo, teto, porcentagem): o «deixar para o design» não cabe nele.
_RE_NUMERO_DE_REGRA = re.compile(r"\d+(?:[.,]\d+)?\s*(?:%|s\b|seg|min|palavras|caracteres|tentativas|rodadas)", re.I)
#: O que é de UI: o «deixar para o design» só aparece para isto (componente, gesto, visual), e nunca para o que é de
#: produto (habilidade, Canal B, PQ e KPI, dados, revezamento, etapa e mecânica) — D1, D2 e D6 do plano.
_RE_UI = re.compile(r"\b(?:bot[õoã]\w*|[íi]cone\w*|layout|tooltip|affordance|lupa|zoom|toque|px|tipografia|"
                    r"destaque visual|indicador visual|visual|gesto\w*|arrast\w*|scroll|anima\w*|cor(?:es)?|"
                    r"contraste|selo|modal|overlay)\b", re.I)
_RE_PRODUTO = re.compile(r"\b(?:PQ-\d+|KPI|habilidade\w*|EF\d{2}\w*|EM13\w*|Canal\s*B|reten\w*|revezamento|LGPD|dados|"
                         r"m[ée]trica\w*|metas?|limiar\w*|aha|etapa\w*|mec[âa]nica\w*|narrativa|personagem|tempo|"
                         r"dura[çc][ãa]o|teto|inatividade|"
                         r"se[çc][ãa]o do DS|se[çc][õo]es do DS)\b", re.I)
_PALAVRAS_VAZIAS = frozenset("""validar definir produto proposta parametro sugestao para como pela pelo entre sobre
mais menos cada todo toda todos todas agente aberto dono porque quando onde qual quais quantos quantas proporcao""".split())


# ------------------------------------------------------------------ itens
@dataclass
class Ocorrencia:
    """Um marcador num documento: a linha inteira (é por ela que a troca acha o lugar) e o literal do marcador."""

    documento: str
    linha: str
    marcador: str
    tipo: str
    descricao: str = ""


@dataclass
class Item:
    """Uma decisão que o PO dá no de acordo: um assunto, com todas as vezes que ele aparece."""

    id: str
    tipo: str
    assunto: str
    sugestao: str = ""
    ui: bool = False
    ocorrencias: List[Ocorrencia] = field(default_factory=list)
    #: Só em `mudanca_gate0`: as trocas de linha que o D0/D9 quis fazer, por bloco da spec.
    trocas: List[Dict[str, Any]] = field(default_factory=list)
    bloco: str = ""
    detalhe: str = ""
    #: Só em `texto_teto`: o texto-chave como está no one-pager (é ele que a troca procura nas linhas).
    texto_chave: str = ""
    #: A proposta que pergunta a escolha da classe ou do ambiente (`tools/ambiente.sobre_a_escolha`), PR 8 (D8): só
    #: aceitar ou recusar. «Outro valor» gravava «unoojornal — PO, parecer de …» na linha da proposta do mini-jogo, a
    #: `secao_ds` seguia com ele e o código o lia como aprovado (revisão do PR #76, 24/10/2026). Outra seção é refazer
    #: produto: o PO recusa e pede a troca no Refazer.
    escolha_ambiente: bool = False
    #: O marcador que pergunta a classe e o ambiente da spec calada (o `[ABERTO — dono: PO: classe e ambiente da missão —
    #: …]` do 046), PR 8 (D8): a seção que o PO escreve entra também como `secao_ds` no bloco 0, logo depois de
    #: `ancora_secao` (o título do bloco), e `secao_sugerida` é a sugestão do agente quando ela é uma seção da lista.
    define_secao: bool = False
    ancora_secao: str = ""
    secao_sugerida: str = ""
    #: Só em `define_secao`: a seção que o briefing fixou com `secao_ds: <seção>` (trava explícita, que o manifesto
    #: bloqueia quando a spec declara outra) e as legadas que o PO fixou no briefing ou no one-pager dele
    #: (`rastro._legada_fixada_pelo_po`). Com a trava, só ela entra no bloco 0 (3ª revisão do PR #76, 24/10/2026).
    secao_travada: str = ""
    legadas_do_po: List[str] = field(default_factory=list)

    def opcoes(self) -> List[str]:
        if self.tipo in (MUDANCA_GATE0, ESCOLHA_AMBIENTE) or self.escolha_ambiente:
            return [ACEITAR, RECUSAR]
        if self.define_secao:
            # a seção da missão nunca fica para o design (D8); aceitar só quando a sugestão é uma seção da lista
            return ([ACEITAR] if self.secao_sugerida else []) + [OUTRO, RECUSAR]
        if self.tipo == TEXTO_TETO:
            # manter o texto aprovado (a sugestão) ou escrever outro; recusar o texto é escrever outro
            return [ACEITAR, OUTRO]
        saida = [ACEITAR] if self.sugestao else []
        saida += [OUTRO, RECUSAR]
        if self.ui:
            saida.append(DESIGN)
        return saida

    def onde(self) -> str:
        """«one-pager (1) · spec do Gate 0 (3)»."""
        contagem: Dict[str, int] = {}
        for o in self.ocorrencias:
            contagem[o.documento] = contagem.get(o.documento, 0) + 1
        if self.tipo == MUDANCA_GATE0:
            return f"spec do Gate 0 (bloco {self.bloco})" if self.bloco else ROTULO_DOC[DOC_SPEC]
        return " · ".join(f"{ROTULO_DOC.get(d, d)} ({n})" for d, n in contagem.items())


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn")


def _norm(texto: str) -> str:
    t = _sem_acento(texto).lower().replace("`", " ").replace("*", " ").replace("_", " ")
    return " ".join(t.split()).strip(" .,:;—–-|")


def _palavras(texto: str) -> set:
    return {p for p in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", _norm(texto)) if len(p) >= 4 and p not in _PALAVRAS_VAZIAS}


def _numeros(texto: str) -> set:
    from tools.propagacao import numeros

    return set(numeros(texto))


def _cabeca(descricao: str) -> str:
    """A proposta sem o «por quê» e a alternativa; o parâmetro sem a sugestão."""
    cabeca = re.split(r"\s+·\s+|,?\s*sugest[ãa]o\s*:", descricao or "", maxsplit=1, flags=re.I)[0]
    return cabeca.strip(" :—–-`*|")


def _descricao(tipo: str, interno: str) -> str:
    """O que vem depois de «a definir por produto:» / «validar com PO:» / «dono: PO:» — vazio se não há."""
    partes = re.split(r"(?:produto|PO)\s*:", interno or "", maxsplit=1)
    if len(partes) > 1:
        desc = partes[1]
    elif tipo == ABERTO_PO:
        desc = interno
    else:
        desc = re.sub(r"^\s*P0[ab]?\b", "", interno or "")
        desc = re.sub(r"^[\s—–:-]*(?:a\s+definir\s+por\s+produto|validar\s+com\s+(?:o\s+)?PO)\b", "", desc, flags=re.I)
    return desc.strip(" :—–-`*")


def _contexto(linha: str, marcador: str) -> str:
    """O assunto de um marcador sem descrição: a célula vizinha numa tabela («| PQ-01 | Qual a proporção… | … |
    `[PROPOSTA — validar com PO]` |»), ou a frase em volta."""
    if linha.lstrip().startswith("|"):
        celulas = [c.strip() for c in linha.strip().strip("|").split("|")]
        idx = next((i for i, c in enumerate(celulas) if marcador in c), len(celulas))
        antes = [c for c in celulas[:idx] if c.strip(" `*-—")]
        depois = [c for c in celulas[idx + 1:] if c.strip(" `*-—")]
        escolhidas = antes[:2] if antes else depois[:2]
        return " · ".join(re.sub(r"[`*]", "", c).strip() for c in escolhidas)
    resto = linha.replace(f"`{marcador}`", " ").replace(marcador, " ")
    return " ".join(re.sub(r"[`*]", "", resto).split()).strip(" -—–:|")[:240]


def _sugestao(tipo: str, descricao: str) -> str:
    m = _RE_SUGESTAO.search(descricao or "")
    if m:
        return m.group(1).strip(" .,`*")
    if tipo == PARAMETRO and re.match(r"^\s*\d", descricao or ""):
        # `[PARÂMETRO — a definir por produto: 35 palavras]`: a descrição é o próprio valor sugerido (exp01em1b)
        return descricao.strip(" .,`*")
    if tipo == PROPOSTA and descricao:
        return _cabeca(descricao)
    return ""


def _sugestao_do_item(tipo: str, descricao: str, assunto: str) -> str:
    """A proposta sem descrição dentro do marcador («| PQ-01 | … | `[PROPOSTA — validar com PO]` |») propõe a linha:
    aceitá-la é aprovar o que a linha diz."""
    return _sugestao(tipo, descricao) or (assunto if tipo == PROPOSTA else "")


def ocorrencias(texto: str, documento: str) -> List[Ocorrencia]:
    """Os marcadores do contrato aberto no texto, na ordem, com a linha onde estão."""
    saida: List[Ocorrencia] = []
    for linha in (texto or "").splitlines():
        for m in _RE_MARCADOR.finditer(linha):
            if m.group(1):
                tipo = PARAMETRO if m.group(1).upper().startswith("PAR") else PROPOSTA
                interno = m.group(2)
                if not interno.strip():
                    continue  # `[PROPOSTA]` sozinho é o nome do marcador citado na prosa
            else:
                tipo, interno = ABERTO_PO, m.group(3)
            desc = _descricao(tipo, interno)
            if _RE_PLACEHOLDER.match(desc) and ("…" in interno or "..." in interno or "<" in interno):
                continue
            if not desc and cita_o_marcador(linha[:m.start()]):
                # «… registradas com marcador normativo `[PROPOSTA P0b — validar com PO]`» (exp01em1b-e3980485): virava
                # o 12º item do cartão, e o «Aceitar as sugestões» gravava a frase de resumo como proposta aprovada
                continue
            saida.append(Ocorrencia(documento=documento, linha=linha, marcador=m.group(0), tipo=tipo, descricao=desc))
    return saida


def _parecidos(a: str, b: str) -> bool:
    """O mesmo assunto escrito duas vezes: «tempo de inatividade no chat» no one-pager, «… no chat, sugestão: 90
    segundos» na spec e «Calibração de nudge de inatividade no chat em 90 segundos» no bloco 12. PQ diferentes e números
    diferentes nunca são o mesmo assunto («35 palavras» e «50 palavras»)."""
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    pa, pb = set(_RE_PQ.findall(a or "")), set(_RE_PQ.findall(b or ""))
    if pa and pb:
        # «Metas e limiares das 5 perguntas PQ-01 a PQ-05» (exp02ef1b) não é a linha da PQ-01
        return pa == pb
    if pa or pb:
        return False
    xa, xb = _numeros(a), _numeros(b)
    if xa and xb and not (xa & xb):
        return False
    if min(len(na), len(nb)) >= 12 and (na.startswith(nb) or nb.startswith(na)):
        return True
    wa, wb = _palavras(a), _palavras(b)
    comuns = wa & wb
    menor = min(len(wa), len(wb))
    return len(comuns) >= 2 and len(comuns) * 5 >= menor * 3


def _id(tipo: str, assunto: str) -> str:
    return hashlib.sha1(f"{tipo}|{_norm(assunto)}".encode("utf-8")).hexdigest()[:10]


_FORCA = {PARAMETRO: 0, ABERTO_PO: 1, PROPOSTA: 2}


def _e_ui(texto: str) -> bool:
    return bool(_RE_UI.search(texto or "")) and not _RE_PRODUTO.search(texto or "") \
        and not _RE_NUMERO_DE_REGRA.search(texto or "")


def documentos(estado: Dict[str, Any]) -> Dict[str, str]:
    """`{documento: texto}` onde o contrato aberto é lido: o one-pager e a spec do Gate 0."""
    spec = str(estado.get("spec_missao_gate0") or estado.get("spec_missao") or "")
    return {DOC_ONE_PAGER: str(estado.get("one_pager") or ""), DOC_SPEC: spec}


def itens_em_aberto(estado: Dict[str, Any]) -> List[Item]:
    """Os itens que o PO decide no de acordo de produto, na ordem em que aparecem (one-pager primeiro)."""
    itens: List[Item] = []
    for documento, texto in documentos(estado).items():
        for oc in ocorrencias(texto, documento):
            assunto = _cabeca(oc.descricao) or _contexto(oc.linha, oc.marcador)
            sugestao = _sugestao_do_item(oc.tipo, oc.descricao, assunto)
            chave = f"{assunto} {sugestao}"
            alvo = next((i for i in itens if i.tipo != MUDANCA_GATE0 and (
                _parecidos(assunto, i.assunto) or _parecidos(chave, f"{i.assunto} {i.sugestao}"))), None)
            if alvo is None:
                alvo = Item(id=_id(oc.tipo, assunto), tipo=oc.tipo, assunto=assunto, sugestao=sugestao)
                itens.append(alvo)
            elif _FORCA[oc.tipo] < _FORCA.get(alvo.tipo, 9):
                # o parâmetro manda: a linha do bloco 12 que só registra a proposta do mesmo número é a mesma decisão
                alvo.tipo, alvo.sugestao = oc.tipo, sugestao or alvo.sugestao
            if not alvo.sugestao and sugestao:
                alvo.sugestao = sugestao
            if not any(o.documento == oc.documento and o.linha == oc.linha and o.marcador == oc.marcador
                       for o in alvo.ocorrencias):
                alvo.ocorrencias.append(oc)
    for item in itens:
        texto = " ".join([item.assunto, item.sugestao] + [o.descricao for o in item.ocorrencias])
        item.ui = _e_ui(texto)
    _marcar_escolhas_de_ambiente(estado, itens)
    return itens + escolhas_de_ambiente(estado) + mudancas_do_design(estado) + textos_acima_do_teto(estado)


def _marcar_escolhas_de_ambiente(estado: Dict[str, Any], itens: Sequence[Item]) -> None:
    """Marca a [PROPOSTA] (ou o [ABERTO — dono: PO]) que pergunta a escolha da classe ou do ambiente: só aceitar ou
    recusar, e a resposta é gravada como a de `tools/ambiente.escolha_do_po` a lê (PR 8, D8).

    Duas exceções, da revisão do PR #76 (24/10/2026):
    - a seção nova que o manifesto bloqueia por outro motivo (`ambiente.escolha_a_conferir`: repete uma coleção do DS, ou
      o briefing fixa outra com `secao_ds:`) não é escolha a aprovar — o «aceitar» não a liberaria. A proposta fica um
      item comum;
    - na spec calada (bloco 0 sem `secao_ds`), o marcador que pergunta a classe e o ambiente é `define_secao`: a seção
      que o PO escrever entra também no bloco 0. Até aqui a resposta ficava só no bloco 15, e o manifesto e o D9 seguiam
      acusando a `secao_ds` ausente. O item guarda a trava do briefing e as legadas que o PO fixou: com `secao_ds:
      <seção>` no briefing, só ela entra (a outra, o manifesto bloquearia), e a sugestão diferente dela não vira
      «aceitar» (3ª revisão do PR #76, 24/10/2026)."""
    from tools import ambiente as amb
    from tools import rastro

    spec = documentos(estado)[DOC_SPEC]
    briefing = str(estado.get("briefing") or "")
    decidido = amb.classe_e_ambiente(spec)
    secao = decidido["secao"] if decidido["nova"] else ""
    a_conferir = not decidido["nova"] or amb.escolha_a_conferir(decidido["secao"], briefing)
    ancora = next((l for l in spec.splitlines() if re.match(r"^##\s*\**\s*0\s*[.—–-]", l)), "")
    trava = rastro.secao_travada(briefing) if ancora and not decidido["secao"] else None
    travada = trava["secao"] if trava and trava["explicita"] else ""
    legadas = [l for l in rastro.SECOES_LEGADAS
               if rastro._legada_fixada_pelo_po(l, briefing, str(estado.get("one_pager_po") or ""))]
    for item in itens:
        if item.tipo not in (PROPOSTA, ABERTO_PO):
            continue
        textos = [o.descricao or item.assunto for o in item.ocorrencias] + [item.assunto]
        if (not decidido["secao"] and ancora
                and any(amb.pergunta_a_secao(t) and not re.search(r"\bextras?\b", t, re.I) for t in textos)):
            item.define_secao, item.ancora_secao, item.ui = True, ancora, False
            item.secao_travada, item.legadas_do_po = travada, legadas
            item.secao_sugerida = _secao_do_de_acordo(item.sugestao, levantar=False, travada=travada, legadas=legadas)
            continue
        if any(amb.sobre_a_escolha(t, secao) for t in textos):
            item.ui = False  # o ambiente nunca fica para o design (D8)
            if a_conferir:
                item.escolha_ambiente = True
                item.sugestao = item.sugestao or item.assunto


def _secao_do_de_acordo(valor: str, levantar: bool = True, travada: str = "", legadas: Sequence[str] = ()) -> str:
    """A seção que o PO escreveu para a spec calada, normalizada (`unoochat`), se ela é uma da lista de missão nova de
    `ambientes.md`, ou uma legada que o PO fixou (`legadas`: no briefing ou no one-pager dele). Fora dela,
    `RespostaInvalida` com o caminho — ou "" com `levantar` falso (a sugestão do agente).

    Com a trava explícita do briefing (`travada`: `secao_ds: <seção>`), só ela entra — inclusive a legada que o briefing
    fixou. Na 3ª revisão do PR #76 (24/10/2026), com o briefing em `secao_ds: unoochat`, a resposta «unoovista» era gravada
    no bloco 0 e o manifesto a bloqueava logo depois; a sugestão `unoogaleria` do agente aparecia como «Aceitar»; e com o
    briefing em `secao_ds: whatsappmobile` a resposta «whatsappmobile» era recusada como legada não fixada."""
    from tools import ambiente as amb
    from tools import rastro

    secao = re.sub(r"^secao_ds\s*:\s*", "", " ".join((valor or "").replace("`", " ").replace("*", " ").split()).lower())
    secao = re.sub(r"\s*:\s*", ":", secao).strip(" .;")
    validas = amb.secoes_para_o_de_acordo()
    nova_ou_jogo = bool(re.match(r"^(?:nova|minijogo):", secao))
    if travada:
        if secao == travada and not nova_ou_jogo and secao in rastro.secoes_ds():
            return secao
    elif secao in validas or secao in legadas:
        return secao
    if not levantar:
        return ""
    if travada and secao != travada:
        raise RespostaInvalida(
            f"«{valor}» não é a seção que o briefing fixou: `secao_ds: {travada}` é trava — a missão monta na "
            f"`{travada}`, e o manifesto bloquearia outra seção no bloco 0. Escreva `{travada}`; se a trava inviabiliza a "
            "mecânica, recuse este item e peça a troca no **Refazer** de produto, com o briefing corrigido.")
    if nova_ou_jogo:
        motivo = ("ambiente novo e mini-jogo pedem a spec refeita (os componentes da seção nova; no mini-jogo, as regras e "
                  "as fases no bloco 2): deixe este item sem resposta e peça-o no **Refazer** de produto")
    elif secao in rastro.SECOES_LEGADAS:
        motivo = ("seção legada só vale fixada no briefing ou no one-pager que o PO anexou (ADR-133 a 138): use a "
                  "sucessora da lista, ou peça a legada no **Refazer** de produto")
    else:
        motivo = "escreva uma seção da lista, como está"
    raise RespostaInvalida(f"«{valor}» não é seção para a spec: {motivo}. Seções da lista: "
                           + ", ".join(f"`{s}`" for s in validas) + ".")


def escolhas_de_ambiente(estado: Dict[str, Any]) -> List[Item]:
    """O ambiente novo ou o mini-jogo que o bloco 0 da spec fixa sem decisão do PO, sem marcador e sem o briefing o fixar:
    um item de proposta, para aceitar ou recusar (PR 8 do plano, decisão D8). Com o marcador escrito, o item é o do
    marcador; com a resposta gravada, não há item. O que o de acordo grava vai na linha da `secao_ds`, depois do valor —
    «— aprovada — PO, parecer de <data>» —, sem mudar o campo que o manifesto lê."""
    from tools import ambiente as amb

    docs = documentos(estado)
    spec = docs[DOC_SPEC]
    decidido = amb.classe_e_ambiente(spec)
    if not decidido["nova"]:
        return []
    if not amb.escolha_a_conferir(decidido["secao"], str(estado.get("briefing") or "")):
        # a regra do manifesto: a seção nova que repete uma coleção do DS (`nova:galeriadefotos` da exp01ef1b) ou que o
        # briefing não fixou porque fixou outra com `secao_ds:` é bloqueada lá, e o «aceitar» do PO não a liberaria — o
        # item pedia uma aprovação que o gate ignora (revisão do PR #76, 24/10/2026)
        return []
    escolha = amb.escolha_do_po(spec, docs[DOC_ONE_PAGER], str(estado.get("briefing") or ""),
                                estado.get(KEY_DECISOES) or [], decidido,
                                one_pager_po=str(estado.get("one_pager_po") or ""))
    if escolha != "silencio":
        return []
    linha = next((l for l in spec.splitlines()
                  if re.search(r"secao_ds\W{0,6}" + re.escape(decidido["secao"]).replace(":", r"\s*:\s*"), l, re.I)), "")
    if not linha:
        return []
    rotulo = "mini-jogo" if decidido["classe"] == amb.MINI_JOGO else "ambiente novo"
    return [Item(id=_id(ESCOLHA_AMBIENTE, decidido["secao"]), tipo=ESCOLHA_AMBIENTE,
                 assunto=f"{rotulo} `{decidido['secao']}` — a spec fixa a classe e o ambiente sem decisão do PO",
                 sugestao=f"aprovar o {rotulo} `{decidido['secao']}`",
                 ocorrencias=[Ocorrencia(documento=DOC_SPEC, linha=linha, marcador="", tipo=ESCOLHA_AMBIENTE)])]


def textos_acima_do_teto(estado: Dict[str, Any]) -> List[Item]:
    """Os textos-chave que a criança lê acima do teto de palavras — o do §15 aprovado, ou o da faixa (rascunho) —, um
    item cada, menos os que o PO já manteve ou reescreveu. O lint de produto os acusa (A024, `texto-chave-acima-do-teto`)
    e o PO decide aqui: manter o texto, ou escrever outro, que entra no one-pager no lugar dele."""
    from tools import textos_chave as tk

    one_pager = str(estado.get("one_pager") or "")
    if not one_pager.strip():
        return []
    teto = tk.teto_de_palavras(one_pager, str(estado.get("briefing") or ""))
    tcs = tk.da_sessao(estado)
    itens: List[Item] = []
    spec = documentos(estado)[DOC_SPEC]
    for tc, n in tk.acima_do_teto(tcs, teto, estado.get(KEY_DECISOES) or []):
        por = "por frase" if teto.get("por") == "frase" else "por texto"
        # o texto que o PO escreve no lugar entra no one-pager e na spec do Gate 0 que o copia (o Canal B do bloco 9):
        # trocado só no one-pager, a spec seguia com o texto velho e o conteúdo aprovado da spec o acusava
        ocorrencias = [Ocorrencia(documento=documento, linha=l, marcador=tc.texto, tipo=TEXTO_TETO)
                       for documento, texto in ((DOC_ONE_PAGER, one_pager), (DOC_SPEC, spec))
                       for l in dict.fromkeys(texto.splitlines()) if tc.texto in l]
        itens.append(Item(
            id=_id(TEXTO_TETO, tk.literal(tc.texto)), tipo=TEXTO_TETO,
            assunto=f"{tc.id} ({tc.origem}) «{tc.texto}» — {n} palavras, teto de {teto['valor']} {por} ({teto['origem']})",
            sugestao="manter o texto aprovado", texto_chave=tc.texto, ocorrencias=ocorrencias))
    return itens


# ------------------------------------------------------------------ mudanças do design no texto do Gate 0
_AUTOR_DO_SPLIT = {"fecha-lacunas": "D0", "ambiente-simulado": "D9"}


def mudancas_do_design(estado: Dict[str, Any]) -> List[Item]:
    """Os `[ABERTO — dono: PO]` do cartão de design (PR 2): o D0 ou o D9 quis mudar o texto do Gate 0 e o código
    descartou. Ficam no estado enquanto a missão volta de design a produto (Devolver) — é aí que o PO decide se a
    mudança vale. Só os que trazem as trocas por linha (`trocas`): sem elas não há o que gravar."""
    itens: List[Item] = []
    for chave in sorted(k for k in estado if str(k).endswith("_status_envelope")):
        envelope = estado.get(chave)
        for a in (envelope.get("achados") if isinstance(envelope, dict) else None) or []:
            if not (isinstance(a, dict) and a.get("aberto_dono_po") and a.get("trocas")):
                continue
            autor = str(a.get("autor") or a.get("agente_responsavel") or "design")
            autor = _AUTOR_DO_SPLIT.get(autor, autor)
            bloco = str(a.get("bloco") or "")
            onde = f"o bloco {bloco}" if bloco.isdigit() else f"«{bloco or 'a spec'}»"
            detalhe = "\n".join(f"- {l}" for t in a["trocas"] for l in t.get("antes") or []) + "\n" + "\n".join(
                f"+ {l}" for t in a["trocas"] for l in t.get("depois") or [])
            # o D9 recebe a spec do D0 e repete a mudança dele: a mesma troca é um item só
            ident = _id(MUDANCA_GATE0, bloco + json.dumps(a["trocas"], ensure_ascii=False, sort_keys=True))
            igual = next((i for i in itens if i.id == ident), None)
            if igual:
                if autor not in igual.assunto:
                    igual.assunto = igual.assunto.replace(" quis mudar ", f" e {autor} quiseram mudar ", 1)
                continue
            itens.append(Item(id=ident, tipo=MUDANCA_GATE0, assunto=f"{autor} quis mudar {onde} da spec do Gate 0",
                              sugestao="aplicar a mudança", trocas=list(a["trocas"]), bloco=bloco,
                              detalhe=detalhe.strip()))
    return itens


def trocas_de_linhas(antes: Sequence[str], depois: Sequence[str]) -> List[Dict[str, Any]]:
    """As trocas entre duas listas de linhas normalizadas, com a linha anterior como âncora (para inserção pura)."""
    saida: List[Dict[str, Any]] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, list(antes), list(depois), autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        saida.append({"antes": list(antes[i1:i2]), "depois": list(depois[j1:j2]),
                      "ancora": antes[i1 - 1] if i1 > 0 else ""})
    return saida


def _faixa_do_bloco(texto: str, bloco: str) -> Tuple[int, int]:
    """`(início, fim)` em caracteres do bloco `## <n>` (o texto inteiro se não acha)."""
    if not bloco:
        return 0, len(texto)
    marcas = list(re.finditer(r"^##\s+(.*)$", texto, re.MULTILINE))
    for i, m in enumerate(marcas):
        numero = re.match(r"\**\s*(\d{1,2})\b", m.group(1))
        chave = numero.group(1) if numero else _norm(m.group(1))
        if chave == bloco or (not numero and _norm(bloco) == chave):
            return m.start(), marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)
    return 0, len(texto)


def _linha_normalizada(linha: str) -> str:
    return " ".join(linha.split())


def aplicar_trocas(texto: str, bloco: str, trocas: Sequence[Dict[str, Any]]) -> Optional[str]:
    """O texto com as trocas de linha aplicadas dentro do bloco, ou `None` se alguma não acha o lugar exato (uma vez)."""
    inicio, fim = _faixa_do_bloco(texto, bloco)
    linhas = texto[inicio:fim].split("\n")
    for troca in trocas:
        uteis = [(i, _linha_normalizada(l)) for i, l in enumerate(linhas)
                 if l.strip() and not re.fullmatch(r"\s*(?:-{3,}|\*{3,}|_{3,})\s*", l)]
        normas = [n for _, n in uteis]
        antes, depois = list(troca.get("antes") or []), list(troca.get("depois") or [])
        if antes:
            achados = [k for k in range(len(normas) - len(antes) + 1) if normas[k:k + len(antes)] == antes]
            if len(achados) != 1:
                return None
            primeiro, ultimo = uteis[achados[0]][0], uteis[achados[0] + len(antes) - 1][0]
            linhas[primeiro:ultimo + 1] = depois
        else:
            ancora = troca.get("ancora") or ""
            achados = [i for i, n in uteis if n == ancora] if ancora else []
            if len(achados) != 1:
                return None
            linhas[achados[0] + 1:achados[0] + 1] = depois
    return texto[:inicio] + "\n".join(linhas) + texto[fim:]


def ja_aplicadas(texto: str, trocas: Sequence[Dict[str, Any]]) -> bool:
    """As linhas novas de todas as trocas já estão no texto (e as que elas tiram, não)."""
    normas = {_linha_normalizada(l) for l in (texto or "").split("\n") if l.strip()}
    return all(set(t.get("depois") or []) <= normas and not (set(t.get("antes") or []) & normas) for t in trocas)


# ------------------------------------------------------------------ respostas
def _texto_gravado(item: Item, oc: Ocorrencia, resposta: str, valor: str, data: str) -> str:
    """O que entra no lugar do marcador: «<valor> — PO, parecer de <data>»."""
    marca = f"PO, parecer de {data}"
    cabeca = _cabeca(oc.descricao)
    if item.escolha_ambiente:
        # a escolha da classe ou do ambiente, também no [ABERTO — dono: PO]: «aprovada|recusada — PO, parecer de <data>:
        # <a proposta>», a forma que `tools/ambiente.escolha_do_po` lê
        proposta = oc.descricao or item.assunto
        return f"{'aprovada' if resposta == ACEITAR else 'recusada'} — {marca}" + (f": {proposta}" if proposta else "")
    if resposta == DESIGN:
        return f"[ABERTO — dono: design: {cabeca or item.assunto} · deixado para o design no parecer de produto de {data}]"
    if resposta == RECUSAR:
        genero = "recusada" if oc.tipo == PROPOSTA else "recusado"
        return f"{genero} — {marca}" + (f": {cabeca}" if cabeca else "")
    if resposta == OUTRO:
        if oc.tipo == PROPOSTA and cabeca:
            return f"{valor} — {marca} (no lugar da proposta: {cabeca})"
        return f"{valor} — {marca}"
    if oc.tipo == PROPOSTA:
        return f"aprovada — {marca}" + (f": {oc.descricao}" if oc.descricao else "")
    return f"{item.sugestao} — {marca}"


def _resposta_do_texto(direita: str, sugestao: str) -> Tuple[str, str]:
    """«→ aprovado», «→ 90s», «→ ignorar / não implementar» de um de acordo escrito à mão (exp02em1b, 21/10/2026)."""
    from tools.propagacao import _RE_RECUSA

    direita = direita.strip(" .;`*")
    if _RE_RECUSA.search("x → " + direita):
        return RECUSAR, ""
    if re.match(r"^(?:aprovad[oa]s?|aceit[oa]s?|aceitar|ok|sim|de acordo|confirmad[oa]s?|mantid[oa]s?)\b", direita, re.I):
        return ACEITAR, ""
    if sugestao and _numeros(direita) and _numeros(direita) == _numeros(sugestao):
        return ACEITAR, ""
    return OUTRO, direita


def _decisoes_em_texto(comentario: str) -> List[Tuple[str, str]]:
    """`(lado esquerdo, lado direito)` de cada linha «<marcador ou assunto> → <decisão>» do comentário."""
    saida = []
    for linha in (comentario or "").splitlines():
        partes = re.split(r"\s*(?:→|->)\s*", linha, maxsplit=1)
        if len(partes) == 2 and partes[0].strip() and partes[1].strip():
            saida.append((partes[0].strip(), partes[1].strip()))
    return saida


#: O marcador citado entre colchetes no lado esquerdo de uma linha «→» do pedido de refazer.
_RE_MARCADOR_CITADO = re.compile(r"\[(?:PAR[ÂA]METRO|PROPOSTA|ABERTO)\b", re.I)


def _assunto_do_texto(esquerda: str) -> str:
    m = re.search(r"\[(PAR[ÂA]METRO|PROPOSTA|ABERTO)\b([^\]]*)\]", esquerda)
    if not m:
        return esquerda.strip(" -*`")
    tipo = PARAMETRO if m.group(1).upper().startswith("PAR") else PROPOSTA if m.group(1).upper() == "PROPOSTA" else ABERTO_PO
    return _cabeca(_descricao(tipo, m.group(2)))


def respostas_anteriores(estado: Dict[str, Any], fluxo: Optional[Dict[str, Any]],
                         itens: Sequence[Item]) -> Dict[str, Dict[str, str]]:
    """`{id: {resposta, valor, origem}}`: o que o PO já respondeu a cada item, da decisão mais nova.

    O refazer de produto invalida o de acordo de produto e reescreve o one-pager: o marcador que o autor reabrir volta
    ao cartão já respondido, e a pessoa confirma. Vale o cartão (`decisoes_contrato` dos pareceres e `decisoes_do_po`
    do estado) e o de acordo escrito à mão com «→», que era como o PO decidia antes deste cartão — o da exp02em1b de
    21/10/2026 15:43, que o refazer de 23/10 invalidou.

    O *refazer* também decide: a linha «[PROPOSTA …] → aprovado» num pedido de refazer, de qualquer etapa, é a resposta
    do PO àquele marcador, e o autor que refaz nem sempre fecha o marcador no texto (R11/R12 da exp02em1b no
    levantamento de 24/10/2026: as propostas que o PO aprovou seguiam `[PROPOSTA]` no PRD). No refazer só conta a linha
    cujo lado esquerdo cita o marcador entre colchetes — «Título → Outro título» é pedido de mudança, não resposta."""
    registros: List[Tuple[str, Dict[str, Any]]] = []
    for p in (fluxo or {}).get("pareceres") or []:
        if p.get("acao") == "refazer":
            quando = str(p.get("quando") or "")
            for esquerda, direita in _decisoes_em_texto(str(p.get("comentario") or "")):
                if _RE_MARCADOR_CITADO.search(esquerda):
                    registros.append((quando, {"assunto": _assunto_do_texto(esquerda), "texto_direita": direita,
                                               "origem": f"refazer de {quando}"}))
            continue
        if p.get("etapa") != "produto" or p.get("acao") not in ("de_acordo", "excecao"):
            continue
        quando = str(p.get("quando") or "")
        for d in p.get("decisoes_contrato") or []:
            registros.append((quando, d))
        for esquerda, direita in _decisoes_em_texto(str(p.get("comentario") or "")):
            registros.append((quando, {"assunto": _assunto_do_texto(esquerda), "texto_direita": direita,
                                       "origem": f"de acordo de {quando}"}))
    for d in estado.get(KEY_DECISOES) or []:
        if isinstance(d, dict):
            registros.append((str(d.get("quando") or ""), d))

    def ordem(quando: str) -> str:
        m = re.match(r"(\d{2})/(\d{2})/(\d{4})\s*(\S*)", quando or "")
        return f"{m.group(3)}{m.group(2)}{m.group(1)}{m.group(4)}" if m else ""

    registros.sort(key=lambda r: ordem(r[0]))
    saida: Dict[str, Dict[str, str]] = {}
    for item in itens:
        for quando, d in registros:
            if (item.tipo == TEXTO_TETO) != (d.get("tipo") == TEXTO_TETO):
                # o texto-chave acima do teto só casa com a decisão dele, pelo ID: pelo assunto, «teto de palavras por
                # parágrafo → 45 palavras» (de acordo de 21/10 da exp02em1b) trocava o texto do Canal B por «45 palavras»
                continue
            mesmo = d.get("id") == item.id or (item.tipo != TEXTO_TETO and d.get("assunto")
                                               and _parecidos(str(d["assunto"]), item.assunto))
            if not mesmo:
                continue
            if "texto_direita" in d:
                resposta, valor = _resposta_do_texto(d["texto_direita"], item.sugestao)
            else:
                resposta, valor = str(d.get("resposta") or ""), str(d.get("valor") or "")
                anterior = str(d.get("sugestao") or "")
                if (resposta == ACEITAR and item.tipo != PROPOSTA and anterior
                        and _norm(anterior) != _norm(item.sugestao)):
                    # o PO aceitou a sugestão daquela versão (90 segundos); o marcador reaberto pode vir sem sugestão,
                    # ou com outra — o que vale é o valor que ele aceitou
                    resposta, valor = OUTRO, anterior
            if resposta not in item.opcoes() or (resposta == OUTRO and not valor.strip()):
                continue
            saida[item.id] = {"resposta": resposta, "valor": valor,
                              "origem": str(d.get("origem") or f"parecer de {quando}")}
    return saida


def aceitar_sugestoes(itens: Sequence[Item], respostas: Optional[Dict[str, Dict[str, str]]] = None
                      ) -> Dict[str, Dict[str, str]]:
    """As respostas com «aceitar» em todo item ainda sem resposta que tem sugestão — o botão sobre a lista do cartão."""
    novas = {k: dict(v) for k, v in (respostas or {}).items()}
    for item in itens:
        if not (novas.get(item.id) or {}).get("resposta") and ACEITAR in item.opcoes():
            novas[item.id] = {"resposta": ACEITAR, "valor": "", "origem": "aceitar as sugestões"}
    return novas


class RespostaInvalida(ValueError):
    """Uma resposta que não cabe no item (outro valor vazio, deixar para o design o que não é de UI)."""


@dataclass
class Decisao:
    """O que o de acordo grava: as decisões, o que ficou sem resposta e as trocas de linha."""

    decisoes: List[Dict[str, Any]] = field(default_factory=list)
    sem_resposta: List[Dict[str, str]] = field(default_factory=list)
    edicoes: List[Dict[str, Any]] = field(default_factory=list)


def decidir(itens: Sequence[Item], respostas: Optional[Dict[str, Dict[str, str]]], quando: str, como: str) -> Decisao:
    """Confere as respostas e monta as trocas. Pura. `quando` é «dd/mm/aaaa hh:mm:ss»: a data vai para o texto."""
    data = (quando or time.strftime("%d/%m/%Y")).split()[0]
    respostas = respostas or {}
    saida = Decisao()
    por_linha: Dict[Tuple[str, str], str] = {}
    for item in itens:
        r = respostas.get(item.id) or {}
        resposta, valor = str(r.get("resposta") or ""), " ".join(str(r.get("valor") or "").split())
        if not resposta:
            saida.sem_resposta.append({"id": item.id, "tipo": item.tipo, "assunto": item.assunto})
            continue
        if resposta not in item.opcoes():
            raise RespostaInvalida(f"«{ROTULO_RESPOSTA.get(resposta, resposta)}» não cabe em «{item.assunto[:80]}»"
                                   + (": deixar para o design só vale para o que é de UI" if resposta == DESIGN else ""))
        if resposta == OUTRO and not valor:
            raise RespostaInvalida(f"«{item.assunto[:80]}»: escreva o outro valor.")
        if any(c in valor for c in "[]\n|"):
            raise RespostaInvalida(f"«{item.assunto[:80]}»: o valor não pode ter colchetes nem barra vertical.")
        gravado = ""
        if item.tipo == TEXTO_TETO:
            # manter não troca nada; outro texto entra no lugar do texto-chave, em toda linha do one-pager que o traz
            if resposta == OUTRO:
                for oc in item.ocorrencias:
                    atual = por_linha.get((oc.documento, oc.linha), oc.linha)
                    por_linha[(oc.documento, oc.linha)] = atual.replace(item.texto_chave, valor)
                gravado = valor
            else:
                gravado = f"«{item.texto_chave}» mantido acima do teto — PO, parecer de {data}"
            saida.decisoes.append({
                "id": item.id, "tipo": item.tipo, "assunto": item.assunto, "sugestao": item.sugestao,
                "resposta": resposta, "valor": valor, "gravado": gravado, "quando": quando, "como": como,
                "origem": str(r.get("origem") or "cartão do de acordo"), "ocorrencias": len(item.ocorrencias),
                # o texto que vale depois da decisão: o lint e o cartão não o acusam de novo
                "texto": valor if resposta == OUTRO else item.texto_chave,
            })
            continue
        if item.tipo == MUDANCA_GATE0:
            if resposta == ACEITAR:
                saida.edicoes.append({"tipo": "trocas", "documento": DOC_SPEC, "bloco": item.bloco,
                                      "trocas": item.trocas})
            gravado = "mudança aplicada à spec do Gate 0" if resposta == ACEITAR else "mudança recusada"
        if item.tipo == ESCOLHA_AMBIENTE:
            # a decisão vai depois do valor da `secao_ds`: o campo continua legível para o manifesto e o D9, e a escolha
            # passa a ter dono (`tools/ambiente.escolha_do_po` lê «aprovada|recusada — PO, parecer de»)
            gravado = f"{'aprovada' if resposta == ACEITAR else 'recusada'} — PO, parecer de {data}"
            for oc in item.ocorrencias:
                atual = por_linha.get((oc.documento, oc.linha), oc.linha)
                por_linha[(oc.documento, oc.linha)] = atual.rstrip() + f" — {gravado}"
            saida.decisoes.append({
                "id": item.id, "tipo": item.tipo, "assunto": item.assunto, "sugestao": item.sugestao,
                "resposta": resposta, "valor": valor, "gravado": gravado, "quando": quando, "como": como,
                "origem": str(r.get("origem") or "cartão do de acordo"), "ocorrencias": len(item.ocorrencias),
            })
            continue
        if item.define_secao and resposta in (ACEITAR, OUTRO):
            # A spec calada: a seção que o PO escolheu entra também no bloco 0, como `secao_ds`, logo depois do título —
            # é o campo que o manifesto e o D9 leem. Só ficava no bloco 15, e a missão seguia com `secao_ds` ausente e
            # `ambiente-ausente-na-spec` (revisão do PR #76, 24/10/2026). A classe vem da seção: toda seção da lista é app
            # clonado; ambiente novo e mini-jogo pedem o Refazer (`_secao_do_de_acordo`)
            secao = _secao_do_de_acordo(valor if resposta == OUTRO else item.secao_sugerida,
                                        travada=item.secao_travada, legadas=item.legadas_do_po)
            atual = por_linha.get((DOC_SPEC, item.ancora_secao), item.ancora_secao)
            por_linha[(DOC_SPEC, item.ancora_secao)] = (atual.rstrip()
                                                         + f"\n- `secao_ds: {secao}` — PO, parecer de {data}")
        for oc in item.ocorrencias:
            texto = _texto_gravado(item, oc, resposta, valor, data)
            gravado = gravado or texto
            atual = por_linha.get((oc.documento, oc.linha), oc.linha)
            por_linha[(oc.documento, oc.linha)] = _trocar_marcador(atual, oc.marcador, texto)
        saida.decisoes.append({
            "id": item.id, "tipo": item.tipo, "assunto": item.assunto, "sugestao": item.sugestao,
            "resposta": resposta, "valor": valor, "gravado": gravado, "quando": quando, "como": como,
            "origem": str(r.get("origem") or "cartão do de acordo"), "ocorrencias": len(item.ocorrencias),
        })
    saida.edicoes = [{"tipo": "linha", "documento": d, "de": l, "para": p}
                     for (d, l), p in por_linha.items() if p != l] + saida.edicoes
    return saida


def _trocar_marcador(linha: str, marcador: str, texto: str) -> str:
    """A linha com o marcador trocado pelo texto, sem a crase que o envolvia — inclusive a que fecha depois do ponto
    («1. `[PROPOSTA — validar com PO: …].`», one-pager da exp02em1b)."""
    com_crase = re.compile("`" + re.escape(marcador) + r"([.,;:]?)`")
    if com_crase.search(linha):
        return com_crase.sub(lambda m: texto + m.group(1), linha)
    return linha.replace(marcador, texto)


_RE_TERMO_PROPRIO = re.compile(r"`([^`\n]{3,40})`|\b([A-Z][a-z]+[A-Z]\w*)\b")


def mencoes_fora(estado: Dict[str, Any], item: Item) -> Dict[str, int]:
    """`{termo: vezes}` dos nomes próprios da proposta (`StoryPoll`) no one-pager e na spec, fora das linhas do item.

    O de acordo grava a recusa no lugar do marcador; o resto do texto continua falando da proposta. Na exp02em1b o
    StoryPoll aparecia 12 vezes no one-pager além da proposta recusada em 21/10: tirá-lo do texto é correção de produto
    (Refazer), e o cartão avisa (D12)."""
    termos = {a or b for a, b in _RE_TERMO_PROPRIO.findall(item.assunto)}
    if not termos:
        return {}
    linhas_do_item = {o.linha for o in item.ocorrencias}
    saida: Dict[str, int] = {}
    for texto in documentos(estado).values():
        for linha in texto.splitlines():
            if linha in linhas_do_item:
                continue
            for termo in termos:
                n = linha.count(termo)
                if n:
                    saida[termo] = saida.get(termo, 0) + n
    return saida


# ------------------------------------------------------------------ aplicar e gravar
def _chaves(documento: str, estado: Dict[str, Any]) -> List[str]:
    if documento == DOC_ONE_PAGER:
        return ["one_pager"]
    return [k for k in CHAVES_SPEC if str(estado.get(k) or "").strip()]


def aplicar_edicoes(estado: Dict[str, Any], edicoes: Iterable[Dict[str, Any]]) -> Tuple[Dict[str, str], List[str]]:
    """`(documentos novos, falhas)`. Pura. Tudo ou nada: com uma falha, nada é devolvido.

    A troca de linha acha a linha inteira, igual, e troca todas as iguais; a spec é trocada na do Gate 0 e na consolidada
    (que repete o texto do Gate 0 com os blocos 13 e 14), onde a linha estiver — e precisa estar em uma delas."""
    novos: Dict[str, str] = {}
    falhas: List[str] = []
    for n, e in enumerate(edicoes, 1):
        chaves = _chaves(str(e.get("documento") or ""), estado)
        alguma = False
        for chave in chaves:
            texto = novos.get(chave, str(estado.get(chave) or ""))
            if e.get("tipo") == "trocas":
                trocado = aplicar_trocas(texto, str(e.get("bloco") or ""), e.get("trocas") or [])
                if trocado is not None:
                    novos[chave], alguma = trocado, True
                elif ja_aplicadas(texto, e.get("trocas") or []):
                    alguma = True  # o D0 e o D9 trouxeram mudanças que se sobrepõem, e a outra já pôs estas linhas
                continue
            linhas = texto.split("\n")
            achou = False
            for i, linha in enumerate(linhas):
                if linha.rstrip("\r") == e["de"]:
                    linhas[i] = e["para"] + ("\r" if linha.endswith("\r") else "")
                    achou = True
            if achou:
                novos[chave], alguma = "\n".join(linhas), True
        if not alguma:
            falhas.append(f"troca {n} ({ROTULO_DOC.get(str(e.get('documento')), e.get('documento'))}): "
                          + ("as linhas do design não estão mais, iguais, na spec do Gate 0" if e.get("tipo") == "trocas"
                             else f"a linha não está mais no documento: «{str(e.get('de'))[:120]}»"))
    return ({} if falhas else novos), falhas


#: Marca do arquivo que não existia antes de `gravar`: o `desfazer` o apaga em vez de reescrevê-lo.
_NAO_EXISTIA = "\x00não existia"


def gravar(run_dir: Path, decisao: Dict[str, Any]) -> Dict[str, str]:
    """Grava no `estado.json` da sessão as trocas e as decisões de um de acordo, e reescreve os artefatos tocados.

    `decisao` é o registro do parecer (`decisoes_contrato`, `edicoes_contrato`). Devolve o texto anterior de cada arquivo
    que reescreveu (`{"estado.json": …, "produto/00-one-pager.md": …}`), para quem gravou desfazer se o fluxo não puder
    ser registrado — os `.md` também: só o `estado.json` voltava, e o one-pager em disco ficava com a decisão desfeita."""
    from pipeline.artifacts import ARTIFACT_FILES, desembrulhar_cerca

    caminho = Path(run_dir) / "estado.json"
    anterior = caminho.read_text(encoding="utf-8")
    estado = json.loads(anterior)
    novos, falhas = aplicar_edicoes(estado, decisao.get("edicoes_contrato") or [])
    if falhas:
        raise RespostaInvalida("A gravação no one-pager e na spec falhou: " + "; ".join(falhas))
    estado.update(novos)
    estado[KEY_DECISOES] = list(estado.get(KEY_DECISOES) or []) + list(decisao.get("decisoes_contrato") or [])
    arquivos = dict(ARTIFACT_FILES)
    destinos = {arquivos[chave]: Path(run_dir) / arquivos[chave] for chave in novos if chave in arquivos}
    guardado: Dict[str, str] = {"estado.json": anterior}
    for relativo, destino in destinos.items():
        guardado[relativo] = destino.read_text(encoding="utf-8") if destino.exists() else _NAO_EXISTIA
    try:
        caminho.write_text(json.dumps(estado, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        for chave, texto in novos.items():
            if chave in arquivos:
                destino = destinos[arquivos[chave]]
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_text(desembrulhar_cerca(texto).strip() + "\n", encoding="utf-8")
    except OSError:
        desfazer(run_dir, guardado)
        raise
    return guardado


def desfazer(run_dir: Path, anterior: Dict[str, str]) -> None:
    """Volta o `estado.json` e os artefatos gravados por `gravar` (o fluxo não pôde ser registrado)."""
    for relativo, texto in anterior.items():
        destino = Path(run_dir) / relativo
        if texto == _NAO_EXISTIA:
            destino.unlink(missing_ok=True)
        elif texto:
            destino.write_text(texto, encoding="utf-8")


def exportar_one_pager(run_dir: Path) -> List[Path]:
    """Regera o `.docx` e o `.html` do one-pager de produto depois que o de acordo gravou as respostas nele.

    Os dois saem do Markdown em `pipeline.artifacts.exportar_one_pagers`, que só rodava ao fim de uma execução: até a
    próxima etapa salvar os artefatos, o documento para gente ler ficava com os [PARÂMETRO] que o PO já tinha fechado.
    Só o de produto: o resumido não é editado pelo de acordo, e o pedagógico baixa as telas do Stitch. Falha aqui não
    desfaz a decisão — o Markdown e o `estado.json` já estão gravados; perde-se a formatação, não o conteúdo."""
    from agents.callbacks import extrair_slug
    from pipeline.artifacts import exportar_one_pagers

    try:
        estado = json.loads((Path(run_dir) / "estado.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    one_pager = str(estado.get("one_pager") or "")
    if not one_pager.strip():
        return []
    slug = extrair_slug(str(estado.get("spec_missao") or one_pager)) or Path(run_dir).name
    return exportar_one_pagers({"one_pager": one_pager}, Path(run_dir), slug)


# ------------------------------------------------------------------ o que o cartão e os agentes leem
def decisoes_perdidas(estado: Dict[str, Any], itens: Sequence[Item]) -> List[Dict[str, Any]]:
    """Decisões gravadas que o one-pager e a spec não têm mais, e cujo marcador também não voltou: o refazer de produto
    reescreveu o trecho. É a linha de base das decisões do PO — sem ela o refazer as apagava calado."""
    docs = documentos(estado)
    corpo = docs[DOC_ONE_PAGER] + "\n" + docs[DOC_SPEC]
    ultimas: Dict[str, Dict[str, Any]] = {}
    for d in estado.get(KEY_DECISOES) or []:
        if isinstance(d, dict) and d.get("id"):
            ultimas[str(d["id"])] = d
    saida = []
    for d in ultimas.values():
        if d.get("tipo") == MUDANCA_GATE0 or not d.get("gravado"):
            continue
        if d.get("tipo") == TEXTO_TETO and d.get("resposta") != OUTRO:
            continue  # manter o texto não grava nada no one-pager
        if str(d["gravado"]) in corpo or (d.get("resposta") == DESIGN and "deixado para o design" in corpo):
            continue
        if any(i.id == d["id"] or _parecidos(str(d.get("assunto") or ""), i.assunto) for i in itens):
            continue  # reaberto: volta ao cartão, já respondido
        if d.get("tipo") == ESCOLHA_AMBIENTE and _escolha_em_vigor(estado, d):
            continue
        saida.append(d)
    return saida


def _escolha_em_vigor(estado: Dict[str, Any], d: Dict[str, Any]) -> bool:
    """A escolha do ambiente novo ou do mini-jogo que o PO respondeu continua valendo sem o sufixo no texto.

    O refazer de produto reescreve a linha da `secao_ds` sem «— aprovada — PO, parecer de …», mas a `escolha_do_po` honra
    a decisão pelo registro e não reabre o item: a seção que importa continua lá. Contá-la como perdida travava o de
    acordo com ESTEIRA_ESTRITA e mandava «Use Refazer» para uma decisão em vigor (revisão do PR #76, 24/10/2026). A
    recusa de uma seção que a spec não fixa mais também foi cumprida: o refazer trocou o ambiente, como a recusa pedia."""
    from tools import ambiente as amb

    m = re.search(r"`\s*((?:nova|minijogo)\s*:\s*[a-z0-9][a-z0-9-]*)\s*`", str(d.get("assunto") or ""), re.I)
    if not m:
        return False
    secao = re.sub(r"\s*:\s*", ":", m.group(1).lower())
    docs = documentos(estado)
    decidido = amb.classe_e_ambiente(docs[DOC_SPEC])
    if decidido["secao"] != secao:
        return d.get("resposta") == RECUSAR
    escolha = amb.escolha_do_po(docs[DOC_SPEC], docs[DOC_ONE_PAGER], str(estado.get("briefing") or ""),
                                estado.get(KEY_DECISOES) or [], decidido,
                                one_pager_po=str(estado.get("one_pager_po") or ""))
    return escolha in ("aprovada", "recusada")


def notas(fluxo: Optional[Dict[str, Any]]) -> str:
    """Markdown das decisões do PO no contrato, para as notas de passagem — de todos os de acordo de produto, inclusive
    os que um refazer invalidou: a decisão não deixa de valer porque a etapa foi refeita. A mais nova vence.

    A decisão que o último de acordo de produto registrou como fora do texto (`decisoes_fora_do_texto`: o refazer a
    apagou, e o PO liberou assim) sai marcada — dizer aos agentes que ela «já está gravada» fazia o design seguir o
    texto e a decisão sumir a jusante."""
    ultimas: Dict[str, Dict[str, Any]] = {}
    fora: set = set()
    for p in (fluxo or {}).get("pareceres") or []:
        if p.get("etapa") == "produto" and p.get("acao") in ("de_acordo", "excecao"):
            for d in p.get("decisoes_contrato") or []:
                ultimas[str(d.get("id") or d.get("assunto"))] = d
            fora = {str(d.get("id") or d.get("assunto")) for d in p.get("decisoes_fora_do_texto") or []}
            for d in p.get("decisoes_fora_do_texto") or []:
                ultimas.setdefault(str(d.get("id") or d.get("assunto")), d)
    if not ultimas:
        return ""
    linhas = ["## Decisões do PO no contrato de produto", "",
              "O PO respondeu no de acordo de produto, e as respostas estão gravadas no one-pager e na spec do Gate 0 "
              "(«<valor> — PO, parecer de <data>»). Elas valem como o resto do texto aprovado: não as reabra, não as "
              "decida de novo e não as aplique por conta própria — o texto do one-pager e da spec já as traz. Proposta "
              "recusada não se implementa. Item deixado para o design é do design decidir (UI).", ""]
    if fora & set(ultimas):
        linhas += ["As marcadas **«não está no texto»** são a exceção: um refazer de produto apagou a resposta do "
                   "one-pager e da spec depois que o PO decidiu, e o de acordo saiu assim. Vale a decisão, não o texto: "
                   "não a decida de novo e não siga o que o texto disser em contrário sobre o mesmo assunto — registre a "
                   "divergência como pendência de produto (`[ABERTO — dono: PO]`).", ""]
    for chave, d in ultimas.items():
        valor = f" «{d['valor']}»" if d.get("valor") else ""
        marca = " — **não está no texto: vale a decisão**" if chave in fora else ""
        linhas.append(f"- {ROTULO_TIPO.get(d.get('tipo'), d.get('tipo'))} {d.get('assunto', '')[:160]} → "
                      f"**{ROTULO_RESPOSTA.get(d.get('resposta'), d.get('resposta'))}**{valor} "
                      f"({d.get('como', '') or 'parecer anterior'}, {d.get('quando', '')}){marca}")
    return "\n".join(linhas) + "\n"


# ------------------------------------------------------------------ padrões da plataforma (D5)
def _defaults(raiz: Optional[Path] = None) -> Tuple[str, Dict[str, bool]]:
    """`(status do arquivo, {nome: amarelo})` de `prompts/references/defaults-missao.md`."""
    caminho = (raiz or Path(__file__).resolve().parent.parent) / "prompts" / "references" / "defaults-missao.md"
    try:
        texto = caminho.read_text(encoding="utf-8")
    except OSError:
        return "", {}
    status = (re.search(r"^status:\s*(.+)$", texto, re.MULTILINE) or [None, ""])[1].strip()
    nomes = {m.group(1): bool(m.group(2)) for m in re.finditer(r"^\|\s*`([a-z0-9-]+)`\s*(🟡)?\s*\|", texto, re.MULTILINE)}
    return status, nomes


def defaults_validados(raiz: Optional[Path] = None) -> bool:
    """O arquivo de padrões deixou de ser rascunho? Enquanto for, todo padrão aplicado é «padrão a confirmar» (D5)."""
    status, _ = _defaults(raiz)
    return bool(status) and not status.lower().startswith("rascunho")


#: Onde cada etapa aplica padrão: produto, no one-pager e na spec — o passo de completude os aplica no bloco 15 desde o
#: PR 6 (D5) —; o D0-UX, no bloco 13 do anexo de design.
_DOCS_DOS_PADROES = {"design": ("fechamento_lacunas", "anexo_design_spec", "ambiente_simulado")}


def padroes_aplicados(estado: Dict[str, Any], etapa: str, raiz: Optional[Path] = None) -> List[Dict[str, Any]]:
    """`[{nome, amarelo, rotulo}]` dos padrões de `defaults-missao.md` citados nos documentos da etapa.

    O arquivo é rascunho v0 e é a base de 16 das 34 decisões D0 do acervo (plano, D5): até ser validado, o cartão
    lista cada padrão aplicado como «padrão a confirmar», sem pedir aceite item a item."""
    status, nomes = _defaults(raiz)
    rotulo = "padrão a confirmar" if not defaults_validados(raiz) else "padrão aplicado"
    if etapa == "produto":
        texto = "\n".join(documentos(estado).values())
    else:
        texto = "\n".join(str(estado.get(k) or "") for k in _DOCS_DOS_PADROES.get(etapa, ()))
    saida = []
    for nome, amarelo in nomes.items():
        if re.search(rf"(?<![a-z0-9-]){re.escape(nome)}(?![a-z0-9-])", texto):
            saida.append({"nome": nome, "amarelo": amarelo, "rotulo": rotulo})
    return saida


def como_dicts(itens: Iterable[Item]) -> List[Dict[str, Any]]:
    return [asdict(i) for i in itens]
