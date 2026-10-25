"""Quem decidiu? O agente não decide no lugar do PO — e quando decide, o documento diz que foi ele.

As três gerações da exp03ef1b (07/10/2026) escreveram decisões que o PO nunca tomou: "Candidato A
aprovado pelo PO", "P0a/P0b homologadas em 24/09", "Quem decidiu: PO (via One-pager v2.2)",
"Rejeitada criação prematura de seção nova". Nenhuma sessão tinha parecer do PO. A decisão do agente,
apresentada como do PO, some da revisão humana: o PO lê "aprovado" e não revisa.

A regra (`references/decisoes-do-agente.md`): o agente só decide quando há coerência e ganho
pedagógico ou funcional claro, e mesmo assim escreve `[PROPOSTA — validar com PO: …]` — a etapa sai
🟡, nunca verde, e a proposta chega ao PO. Este módulo confere as duas metades, em código:

- **decisão atribuída ao PO** sem nenhum registro do PO na sessão (pedido de refazer, parecer, pedido de
  correção) é ⛔: o autor reescreve como proposta. Com registro, é ⚠️ a conferir por uma pessoa — menos a que o
  registro estruturado do PO confirma (`RegistroDoPO`: a decisão do de acordo e a linha idêntica no one-pager que ele
  anexou), que sai da lista;
- **proposta do agente** é ⚠️ listada: não bloqueia, mas tira a etapa do verde.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

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


def _linhas_atribuidas(texto: str) -> List[str]:
    """As linhas inteiras que afirmam uma decisão do PO (e não a pedem), com espaço único."""
    saida: List[str] = []
    from tools.conteudo_aprovado import remover_anexo

    # o anexo do PRD é a esteira dizendo que o PO aprovou o one-pager — e aprovou, antes do dev
    for linha in remover_anexo(texto or "").splitlines():
        if RE_ATRIBUIDA_AO_PO.search(linha) and not _PEDE_DECISAO.search(linha) and not _FONTE_BRIEFING.search(linha):
            saida.append(re.sub(r"\s+", " ", linha).strip())
    return saida


def atribuicoes_ao_po(texto: str) -> List[str]:
    """Linhas que afirmam uma decisão do PO (e não a pedem)."""
    return [linha[:220] for linha in _linhas_atribuidas(texto)]


def propostas(texto: str) -> List[str]:
    """Marcadores `[PROPOSTA …]` na ordem em que aparecem, sem repetição."""
    vistos: List[str] = []
    for m in RE_PROPOSTA.finditer(texto or ""):
        trecho = re.sub(r"\s+", " ", m.group(0)).strip()
        if trecho not in vistos:
            vistos.append(trecho)
    return vistos


# ------------------------------------------------------------------ a decisão que o registro do PO confirma
#: Palavra que não conta como conteúdo ao comparar um texto com o assunto de uma decisão do PO: o vocabulário da própria
#: atribuição.
_SEM_CONTEUDO = frozenset("""homologado homologada homologados homologadas homologacao ratificado ratificada ratificados
ratificadas ratificacao aprovado aprovada aprovados aprovadas aprovacao decidido decidida decisao decisoes pedido pedidos
parecer pareceres formal formalmente pelo pela pelos pelas como para sobre conforme esta este isso essa esse foram sido
""".split())
_RE_NUMERO_COM_UNIDADE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(%|s\b|seg(?:undos?)?\b|min(?:utos?)?\b|palavras?\b|caracteres\b|itens\b|tentativas\b|"
    r"rodadas\b|px\b|vagas\b|cart[õo]es\b|perguntas\b)", re.IGNORECASE)
#: «homologada pelo PO no Pedido 13»: o número é o das notas de passagem («### Pedido 13 · …»), na ordem de
#: `pedidos_do_po` (`pipeline/passagem.notas_de_passagem`). Só para a pista do «a conferir».
_RE_PEDIDO_N = re.compile(r"\bpedido\s+(?:n[ºo°.]?\s*)?(\d{1,3})\b", re.IGNORECASE)


def _palavras_planas(texto: str) -> List[str]:
    import unicodedata

    sem = "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower()) if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z0-9]+", sem)


def _e_conteudo(palavra: str) -> bool:
    return palavra.isdigit() or (len(palavra) >= 4 and palavra not in _SEM_CONTEUDO)


def _normalizado(valor: str, unidade: str) -> str:
    u = unidade.lower()
    u = ("s" if u.startswith("s") else "min" if u.startswith("min") else "palavras" if u.startswith("palavra")
         else "cartoes" if u.startswith("cart") else u)
    return f"{valor.replace(',', '.')} {u}"


def numeros_com_unidade(texto: str) -> List[str]:
    """`["29 min", "60 s", "25 palavras"]`, na ordem e normalizados («60 segundos» e «60s» são «60 s»)."""
    saida: List[str] = []
    for valor, unidade in _RE_NUMERO_COM_UNIDADE.findall(texto or ""):
        n = _normalizado(valor, unidade)
        if n not in saida:
            saida.append(n)
    return saida


#: A referência do critério com que o juiz compara o valor que o PO decidiu: «(29 min) excede o teto de 25 min» (P053,
#: 727a3c2d), «excede o teto de 25 min» (P157, 53e011b6). Só depois da comparação — exceder, ultrapassar, passar,
#: superar, acima de —, para que «o limite de 30 s da Seção 7» não passe por referência.
_RE_REFERENCIA_DO_CRITERIO = re.compile(
    r"\b(?:exced\w*|(?:ultra)?pass\w*|super\w*|acima)\s+(?:d?[oa]s?\s+)?(?:tetos?|limites?|cap|recomenda[çc][ãa]o|"
    r"recomendad[oa]s?)\s+(?:\w+\s+){0,2}?de\s*$", re.IGNORECASE)


def numeros_divergentes(texto: str, decididos: Sequence[str], aceitos: Sequence[str] = ()) -> List[str]:
    """Os números com unidade do texto na unidade de um valor `decididos` que não são nenhum dos `decididos` nem dos
    `aceitos`: o valor que o texto contrapõe à decisão.

    Revisão do PR #80 (24/10/2026): bastava o valor decidido aparecer no texto, e a linha que mostra o documento
    descumprindo a decisão («Aviso de inatividade no chat aos 30 segundos (… 90 segundos homologado pelo PO)», exp02em1b)
    saía confirmada como se a repetisse. A referência do critério (`_RE_REFERENCIA_DO_CRITERIO`) não conta."""
    unidades = {n.split(" ", 1)[1] for n in decididos}
    ok = set(decididos) | set(aceitos)
    saida: List[str] = []
    for m in _RE_NUMERO_COM_UNIDADE.finditer(texto or ""):
        n = _normalizado(m.group(1), m.group(2))
        if n.split(" ", 1)[1] not in unidades or n in ok or n in saida:
            continue
        if _RE_REFERENCIA_DO_CRITERIO.search(texto[max(0, m.start() - 80):m.start()]):
            continue
        saida.append(n)
    return saida


def _paragrafos(texto: str) -> List[str]:
    """O texto em parágrafos: linha em branco ou item numerado («2. Tetos de palavras: HOMOLOGADOS.») separa."""
    blocos = re.split(r"\n\s*\n|\n(?=\s*\d{1,2}[.)]\s)", texto or "")
    return [b.strip() for b in blocos if b.strip()]


_RE_ITEM_NUMERADO = re.compile(r"^\s*\d{1,2}[.)]\s")


def _unidades(texto: str) -> List[str]:
    """O item numerado inteiro ou, fora dele, a linha: o trecho do PO que a pista do «a conferir» mostra. É corte pela
    forma do texto, não pelo sentido."""
    saida: List[str] = []
    for paragrafo in _paragrafos(texto):
        if _RE_ITEM_NUMERADO.match(paragrafo):
            saida.append(paragrafo)
        else:
            saida += [linha.strip() for linha in paragrafo.splitlines() if linha.strip()]
    return saida


def _linha_plana(linha: str) -> str:
    """A linha com espaço único e sem as bordas: a forma em que a linha do documento e a do anexo do PO se comparam."""
    return re.sub(r"\s+", " ", linha or "").strip()


def _trecho(texto: str, limite: int = 120) -> str:
    plano = _linha_plana(texto)
    return plano if len(plano) <= limite else plano[:limite].rstrip() + "…"


class RegistroDoPO:
    """O que o PO deixou registrado na sessão, para conferir a decisão que um documento atribui a ele.

    É o que `ha_registro_do_po` devolve: verdadeiro quando há algum registro — como era o booleano. Confirma a
    atribuição só o que é **estruturado**, comparado literalmente (princípio da C7, aprovado em 25/10/2026: regex só para
    comparação literal sobre dado estruturado; interpretação de sentido nunca esconde pendência nem bloqueia sozinha):

    - a decisão que o PO aceitou ou escreveu no cartão do de acordo de produto (`decisoes_do_po`, PR 3), do mesmo
      assunto e com o mesmo valor, sem outro valor na mesma unidade (`decisao_gravada`). A recusada nunca confirma;
    - a linha idêntica no one-pager que o PO anexou (`one_pager_po`, `linha_do_anexo`).

    O texto livre dos pedidos e pareceres **não confirma** nada. Até a 3ª revisão do PR #80 (25/10/2026) o código lia
    neles a decisão — seis palavras literais num item com verbo de decisão e sem negação, o «Pedido N» citado, a marca
    `[HOMOLOGADO pelo PO]` que o PO mandou escrever —, e cada variação de recusa em prosa que as regex não previam virava
    confirmação: sobre o parecer real da exp02em1b (21/10/2026 15:43:51), 12 de 27 maneiras de dizer não ao StoryPoll
    («→ não, manter o quiz atual», «→ sem aprovação», «→ aprovado? não»…) confirmavam «aprovado pelo PO». Esse texto
    agora só dá a pista de onde a decisão parece estar (`decisao_repetida`), para o PO conferir."""

    def __init__(self, fontes: Sequence[Tuple[str, str]] = (), decisoes: Sequence[Dict[str, Any]] = (),
                 one_pager_po: str = "", pedidos: Sequence[str] = (), ha: Optional[bool] = None,
                 estado: Optional[Dict[str, Any]] = None):
        from tools.fidelidade import sem_relatos_de_gate

        #: O que o PO escreveu, como o estado o guarda (pedidos, pareceres, decisões e anexo): a entrada do classificador
        #: de sentido, que só dá a pista (`leituras_do_classificador`).
        self.estado = {k: (estado or {}).get(k) for k in ("pedidos_do_po", "pareceres_humanos", "decisoes_do_po",
                                                          "one_pager_po")}

        #: `(de onde, texto)` do que o PO escreveu: os pedidos, o pedido corrente, os pareceres de produto, o anexo, o
        #: briefing. Só para a pista.
        self.fontes = [(rotulo, sem_relatos_de_gate(str(t or ""))) for rotulo, t in fontes if str(t or "").strip()]
        #: Os pedidos de refazer, na ordem das notas de passagem: o «Pedido N» é `pedidos[N - 1]`.
        self.pedidos = [sem_relatos_de_gate(str(t or "")) for t in pedidos]
        self.decisoes = [d for d in decisoes or [] if isinstance(d, dict)]
        self.linhas_do_anexo = {_linha_plana(l) for l in str(one_pager_po or "").splitlines() if _linha_plana(l)}
        self._ha = bool(self.fontes or self.decisoes) if ha is None else bool(ha)

    def __bool__(self) -> bool:
        return self._ha

    # -------------------------------------------------- confirmação: só o estruturado
    def _decisoes_do_assunto(self, texto: str, respostas: tuple, minimo: float = 0.0) -> List[Dict[str, Any]]:
        """As decisões do de acordo, com resposta em `respostas`, de que o texto fala: o mesmo assunto — duas palavras de
        conteúdo em comum, e ao menos a fração `minimo` das do assunto."""
        palavras = set(_palavras_planas(texto))
        saida: List[Dict[str, Any]] = []
        for d in self.decisoes:
            if str(d.get("resposta") or "") not in respostas:
                continue
            do_assunto = {p for p in _palavras_planas(str(d.get("assunto") or "")) if _e_conteudo(p)}
            comuns = do_assunto & palavras
            if len(comuns) >= 2 and len(comuns) >= minimo * len(do_assunto):
                saida.append(d)
        return saida

    @staticmethod
    def _valor(d: Dict[str, Any]) -> str:
        from tools.fechar_contrato import OUTRO

        if str(d.get("resposta") or "") == OUTRO:
            return str(d.get("valor") or "")
        return str(d.get("sugestao") or d.get("valor") or "")

    def decisao_gravada(self, texto: str) -> str:
        """O assunto da decisão do de acordo (`decisoes_do_po`) que o texto repete — mesmo assunto, o valor decidido
        literalmente no texto e nenhum outro número na unidade dele (`numeros_divergentes`).

        Só a sugestão que o PO aceitou e o valor que ele escreveu: a recusada não é decisão a favor. Até a revisão do PR
        #80 (24/10/2026) a recusa contava com o valor da sugestão, e «StoryPoll … (aprovado pelo PO)» saía confirmada
        pela recusa do StoryPoll."""
        from tools.fechar_contrato import ACEITAR, OUTRO

        numeros, plano = set(numeros_com_unidade(texto)), " ".join(_palavras_planas(texto))
        for d in self._decisoes_do_assunto(texto, (ACEITAR, OUTRO)):
            valor = self._valor(d)
            if not valor.strip():
                continue
            do_valor = numeros_com_unidade(valor)
            if do_valor and numeros_divergentes(texto, do_valor):
                continue  # «… de 90 segundos homologado pelo PO, mas a Seção 7 dispara o aviso aos 30 segundos»
            if (bool(do_valor) and set(do_valor) <= numeros) or (
                    len(valor) >= 8 and " ".join(_palavras_planas(valor)) in plano):
                return f"{str(d.get('assunto') or '')[:80]} ({d.get('quando') or 'de acordo de produto'})"
        return ""

    def decisao_recusada(self, texto: str) -> str:
        """O item que o PO recusou no de acordo e de que o texto parece falar; "" se nenhum.

        O mesmo assunto, com ao menos metade das palavras de conteúdo dele — duas em comum não bastam para dizer que
        «unooriaai + unoovista … habilidades» fala do StoryPoll recusado —, e o valor recusado quando ele tem número. É
        comparação de palavras, não de sentido: impede a confirmação e vai na mensagem do ⚠️, mas não bloqueia sozinha."""
        from tools.fechar_contrato import RECUSAR

        numeros = set(numeros_com_unidade(texto))
        for d in self._decisoes_do_assunto(texto, (RECUSAR,), minimo=0.5):
            recusado = set(numeros_com_unidade(f"{d.get('sugestao') or ''} {d.get('assunto') or ''}"))
            if not recusado or recusado <= numeros:
                quando = d.get("quando") or "de acordo de produto"
                return f"«{str(d.get('assunto') or '')[:80]}», recusado pelo PO no de acordo ({quando})"
        return ""

    def linha_do_anexo(self, linha: str) -> str:
        """A linha está, idêntica (a menos de espaços), no one-pager que o PO anexou."""
        if _linha_plana(linha) in self.linhas_do_anexo:
            return "linha idêntica no one-pager que o PO anexou"
        return ""

    def confirma(self, linha: str) -> str:
        """Por que a atribuição da linha ao PO está no registro estruturado dele; "" quando não está — ou quando ela
        parece falar do que o PO recusou no de acordo (`decisao_recusada`): registros que se contradizem, uma pessoa
        confere."""
        if self.decisao_recusada(linha):
            return ""
        return self.decisao_gravada(linha) or self.linha_do_anexo(linha)

    # -------------------------------------------------- pista do classificador: ordena e explica, não confirma
    def leituras_do_classificador(self, linhas: Sequence[str], documento: str) -> Dict[str, Any]:
        """`{linha: Leitura}` do classificador de sentido (`tools/classificador.decisao_do_po_confirmada`) sobre o que o
        PO escreveu na sessão. É pista: ordena a lista do «a conferir» (a que ele não lê como confirmada primeiro) e
        explica cada linha. Nunca tira a linha da lista: na fase A da C7 (25/10/2026) ele acertou 53 de 53 casos, mas
        com 0 erro em 38 positivos o erro ainda pode chegar a ~8%, e um falso «confirmada» esconderia uma atribuição
        falsa ao PO — a confirmação continua sendo só a do registro estruturado (`confirma`)."""
        from tools import classificador

        linhas = list(dict.fromkeys(linhas))
        if not linhas:
            return {}
        lidas = classificador.ler(classificador.DECISAO_DO_PO_CONFIRMADA, [
            {"documento": documento, "linha": linha, "registros_do_po": classificador.registros_do_po(self.estado, linha)}
            for linha in linhas])
        return dict(zip(linhas, lidas))

    # -------------------------------------------------- pista: de onde a decisão parece vir (não confirma nada)
    def decisao_repetida(self, texto: str) -> str:
        """De onde parece vir a decisão que o texto atribui ao PO — a pista do «a conferir» que o PO lê; "" sem pista.

        Não tira nada da contagem nem confirma nada (3ª revisão do PR #80, 25/10/2026): até ali, o achado de juiz com
        pista saía do veredito, e o achado misto («29 min aceito pelo PO. Porém a Etapa 4 concentra três decisões sem
        feedback», 727a3c2d) e a denúncia sem número («o teto de 45 palavras aceito pelo PO é excedido em vários
        parágrafos», exp02em1b) sumiam com ela. A pista vem, nesta ordem, da decisão do de acordo do mesmo assunto, do
        «Pedido N» citado e do item ou linha do PO que traz o primeiro número com unidade do texto — e diz quando o texto
        traz outro valor na mesma unidade."""
        from tools.fechar_contrato import ACEITAR, OUTRO

        numeros = numeros_com_unidade(texto)

        def com_divergencia(pista: str, decididos: Sequence[str], aceitos: Sequence[str] = ()) -> str:
            outros = numeros_divergentes(texto, decididos, aceitos) if decididos else []
            return pista + (f"; o texto traz outro valor na mesma unidade ({', '.join(outros)})" if outros else "")

        for d in self._decisoes_do_assunto(texto, (ACEITAR, OUTRO)):
            valor = self._valor(d)
            pista = (f"a decisão «{str(d.get('assunto') or '')[:80]}: {_trecho(valor, 60)}» do de acordo de produto "
                     f"({d.get('quando') or 'sem data'})")
            return com_divergencia(pista, numeros_com_unidade(valor))
        def melhor(candidatos: List[Tuple[str, List[str], List[str]]]) -> str:
            """O primeiro trecho sem outro valor na mesma unidade; sem ele, o primeiro, com a divergência dita."""
            for pista, decididos, do_item in candidatos:
                if not numeros_divergentes(texto, decididos, do_item):
                    return pista
            pista, decididos, do_item = candidatos[0]
            return com_divergencia(pista, decididos, do_item)

        for m in _RE_PEDIDO_N.finditer(texto):
            n = int(m.group(1))
            if not 1 <= n <= len(self.pedidos):
                continue
            candidatos = []
            for unidade in _unidades(self.pedidos[n - 1]):
                do_item = numeros_com_unidade(unidade)
                comuns = [x for x in do_item if x in numeros]
                if comuns:
                    candidatos.append((f"o Pedido {n}: «{_trecho(unidade)}»", comuns, do_item))
            return melhor(candidatos) if candidatos else f"o Pedido {n}, sem item com o mesmo número"
        if numeros:
            candidatos = [(f"{rotulo}: «{_trecho(unidade)}»", numeros[:1], numeros_com_unidade(unidade))
                          for rotulo, texto_do_po in self.fontes for unidade in _unidades(texto_do_po)
                          if numeros[0] in numeros_com_unidade(unidade)]
            if candidatos:
                return melhor(candidatos)
        return ""


def _pareceres_de_produto(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Os pareceres que são palavra do PO sobre produto: de produto, válidos (não invalidados por um refazer depois) e de
    uma pessoa — a devolução automática da esteira (`autor: "esteira"`, `pipeline/passagem._devolver_a_produto`) não é o
    PO (M2 da 3ª revisão do PR #80, 25/10/2026)."""
    return [p for p in state.get("pareceres_humanos") or [] if isinstance(p, dict)
            and str(p.get("autor") or "") != "esteira" and p.get("valido", True) is not False
            and str(p.get("etapa") or "produto") == "produto"]


def ha_registro_do_po(state: Dict[str, Any]) -> RegistroDoPO:
    """A sessão tem alguma palavra do PO: pedido de refazer, parecer de acordo com nota, pedido de correção, ou o
    one-pager que ele anexou. Com ela, a atribuição vira ⚠️ a conferir — o que a esteira mudou no one-pager do PO quem
    barra é a conferência trecho a trecho (`tools/one_pager_po.py`).

    Devolve o `RegistroDoPO`, verdadeiro nos mesmos casos em que o booleano de antes era: com ele, `achados` deixa de
    pedir conferência da atribuição que o registro estruturado do PO confirma — a decisão do de acordo e a linha idêntica
    no one-pager anexado."""
    from pipeline.reexecucao import texto_do_pedido

    ha = bool(state.get("pedidos_do_po") or str(state.get("notas_de_passagem") or "").strip()
              or str(state.get("pedido_correcao") or "").strip() or str(state.get("one_pager_po") or "").strip())
    pedidos = [str(p.get("texto") or "") for p in state.get("pedidos_do_po") or [] if isinstance(p, dict)]
    fontes: List[Tuple[str, str]] = [(f"o Pedido {n}", t) for n, t in enumerate(pedidos, 1)]
    fontes.append(("o pedido corrente", texto_do_pedido(str(state.get("pedido_correcao") or ""))))
    fontes += [(f"o parecer de produto de {p.get('quando') or 'data não registrada'}", str(p.get("comentario") or ""))
               for p in _pareceres_de_produto(state)]
    fontes += [("o one-pager que o PO anexou", str(state.get("one_pager_po") or "")),
               ("o briefing", str(state.get("briefing") or ""))]
    return RegistroDoPO(fontes, state.get("decisoes_do_po") or [], str(state.get("one_pager_po") or ""), pedidos, ha=ha,
                        estado=state)


#: A ordem da lista do «a conferir» pela leitura do classificador: a que ele não lê como confirmada vem primeiro.
_ORDEM_DA_PISTA = {"nao_confirmada": 0, "nao_sei": 1, "confirmada": 2}


def achados(texto: str, documento: str, registro_do_po: Any, etapa: str = "produto",
            chave: str = "") -> List[Dict[str, str]]:
    """Achados do documento: decisão atribuída ao PO (⛔ sem registro, ⚠️ com) e propostas a revisar (⚠️).

    Com o `RegistroDoPO` (e não só o booleano), a atribuição que o registro estruturado do PO confirma — a decisão do de
    acordo e a linha idêntica no one-pager anexado — sai da lista; se todas saem, não há achado. As outras ficam ⚠️ com
    a dúvida explicada linha a linha: a que parece falar do que o PO recusou no de acordo, e a pista de onde a decisão
    parece estar nos pedidos e pareceres, que o código não lê como decisão (3ª revisão do PR #80, 25/10/2026). Até ali a
    que parecia falar do recusado era ⛔ — comparação de palavras bloqueando sozinha.

    O classificador de sentido (C7) lê cada linha que fica contra o que o PO escreveu na sessão: a lista sai com a que
    ele não lê como confirmada primeiro, e a leitura dele vai na dúvida da linha. Ele nunca tira linha da lista.
    `chave` é a chave do documento no estado (`one_pager`, `spec_missao`, `prd_final`…), como a fase A o mediu."""
    saida: List[Dict[str, str]] = []
    linhas = _linhas_atribuidas(texto)
    conferidas = 0
    duvidas: Dict[str, str] = {}
    if linhas and registro_do_po and isinstance(registro_do_po, RegistroDoPO):
        restantes = [linha for linha in linhas if not registro_do_po.confirma(linha)]
        conferidas, linhas = len(linhas) - len(restantes), restantes
        for linha in linhas:
            recusada = registro_do_po.decisao_recusada(linha)
            pista = registro_do_po.decisao_repetida(linha) if not recusada else ""
            duvidas[linha] = (f"parece falar do {recusada}" if recusada
                              else f"o código não lê como decisão o que parece ser {pista}" if pista else "")
        leituras = registro_do_po.leituras_do_classificador(linhas, chave or documento)
        for linha, lida in leituras.items():
            if lida.nao_sei:
                continue
            frase = ("o classificador de sentido lê a confirmação do PO" if lida.rotulo == "confirmada"
                     else "o classificador de sentido não lê confirmação do PO")
            frase += (f" («{lida.citacao[:140]}»)" if lida.citacao.strip() else "") + (
                " — é pista, não confirma: confira" if lida.rotulo == "confirmada" else "")
            duvidas[linha] = f"{duvidas[linha]}; {frase}" if duvidas[linha] else frase
        linhas = sorted(linhas, key=lambda l: _ORDEM_DA_PISTA.get(getattr(leituras.get(l), "rotulo", "nao_sei"), 1))
    if linhas:
        lista = "\n".join(f"    - «{linha[:220]}»" + (f" — {duvidas[linha][:400]}" if duvidas.get(linha) else "")
                          for linha in linhas[:8])
        if registro_do_po:
            outras = (f" ({conferidas} outra(s) estão no registro estruturado do PO e não vão à lista)" if conferidas
                      else "")
            leu = ("o código só confirma a atribuição pelo registro estruturado — a decisão gravada no cartão do de acordo "
                   "de produto (aceitar ou outro valor) ou a linha idêntica no one-pager que o PO anexou —, e estas não "
                   "estão lá" if isinstance(registro_do_po, RegistroDoPO) else "o código não sabe se ele diz isto")
            saida.append({"severidade": "atencao", "codigo": "decisao-atribuida-ao-po", "etapa": etapa, "resumo": (
                f"{documento}: {len(linhas)} decisão(ões) atribuída(s) ao PO{outras}. A sessão tem parecer do PO, mas "
                f"{leu} — confira antes do de acordo:\n" + lista)})
        else:
            saida.append({"severidade": "bloqueio", "codigo": "decisao-atribuida-ao-po", "etapa": etapa, "resumo": (
                f"{documento}: {len(linhas)} decisão(ões) atribuída(s) ao PO, e a sessão não tem nenhum parecer, pedido "
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
#: Relatórios da própria esteira que também se chamam parecer («Parecer de Adequação Pedagógica»): não são do PO.
_FONTE_DE_AGENTE = re.compile(r"adequa|pedag[óo]gic|estrutural|\bgate\b|banca|comit|juiz|avalia", re.IGNORECASE)
_RE_DATA = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")


def _cita_parecer_humano(fonte: str, pareceres: str) -> bool:
    """A fonte cita um parecer humano que existe na sessão: diz «parecer», não é relatório de agente, e cada data
    que ela traz está nos pareceres registrados. Sem data, não há como conferir — e não conta."""
    if not _FONTE_PARECER.search(fonte) or _FONTE_DE_AGENTE.search(fonte):
        return False
    datas = _RE_DATA.findall(fonte)
    return bool(datas) and all(d in pareceres for d in datas)


#: As classes que o D0 podia declarar até o PR 6 (prompt 065, Passo 2), com o design decidindo duração, dados, estados e
#: texto do professor. Ficam para ler as sessões anteriores (a montagem do PRD de uma missão desenhada antes do PR 6).
#: A conferência era por igualdade com `mecanica` e `curriculo`, e a `mecanica_param` da exp02ef1b (10% da moldura,
#: 23/10/2026) passou: o rótulo é do próprio agente.
CLASSES_D0_LEGADO = ("estado", "handoff", "evidencia", "dispositivo", "copy-fonte", "acessibilidade", "dados", "duracao",
                     "mecanica", "curriculo")
#: As classes do D0-UX (PR 6, decisão D2): o design decide só UI/UX — o estado de tela (falha, espera, vazio, reentrada na
#: voz da ficção: decomposição, D7), gesto, desvanecimento do apoio (scaffolding), acessibilidade de componente e
#: adaptação de tela por dispositivo. Pela régua do PR 1 (`tools/propagacao.classificar_d0`), é onde estão as cerca de 20
#: das 34 decisões D0 do acervo que o plano mantém no design. O resto do D0 virou o passo de completude da spec em produto
#: (`prompts/produto/046_completude_spec.md`): as 9 decisões que criavam produto e as 2 que aplicavam decisão do PO nunca
#: gravada saíram do design (plano, «Agente por agente», A065).
CLASSES_D0 = ("estado", "gesto", "scaffolding", "acessibilidade", "dispositivo")
#: As classes do passo de completude de produto (prompt 046): o que o D0 decidia no lugar do PO e mais o que o plano dá a
#: produto — teto, painel docente, PQ e KPI, retenção, revezamento, regra por inferência (D6: retenção e revezamento são
#: padrão de plataforma; painel e PQ/KPI, por missão). `estado` aparece nas duas: em produto, o contrato de estados do
#: bloco 2 com o padrão da plataforma aplicado (D5); no design, a tela de cada estado.
CLASSES_DE_PRODUTO = ("estado", "handoff", "evidencia", "copy-fonte", "dados", "retencao", "duracao", "teto", "parametro",
                      "painel", "pq-kpi", "revezamento", "regra", "mecanica", "curriculo", "ambiente")
#: Prefixos de classe que são sempre de produto — decisão do PO (plano «Produto dono do contrato», PR 2). `ambiente`
#: desde o PR 8 (D8): a classe do ambiente, o ambiente novo e as regras e fases do mini-jogo.
PREFIXOS_DE_PRODUTO = ("mecanica", "curriculo", "parametro", "ambiente")


def _norm_classe(texto: str) -> str:
    import unicodedata

    return "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower())
                   if unicodedata.category(c) != "Mn").strip(" `*_")


def classe_de_produto(classe: str, legado: bool = False) -> str:
    """O motivo de a classe declarada pelo D0 ser de produto, ou "" se é uma classe que o design decide.

    Lista branca e prefixo: `mecanica*`, `curriculo*` e `parametro*` são de produto; o que não está na lista também,
    porque a lista é o que o prompt deixa o D0 decidir. Classe composta («`handoff` / `copy-fonte`») vale por partes.

    Desde o PR 6 a lista é a do D0-UX (`CLASSES_D0`): handoff, evidência, dados, duração e texto do professor são do
    passo de completude de produto; o estado fica no design só como tela (o contrato de estados é de produto). `legado=True` lê com a lista de antes (`CLASSES_D0_LEGADO`): a missão desenhada
    antes do PR 6 decidiu essas classes no design, e o PRD dela as cita — reler com a régua nova mudaria o veredito do
    que já foi aprovado."""
    lista = CLASSES_D0_LEGADO if legado else CLASSES_D0
    partes = [p for p in (_norm_classe(x) for x in re.split(r"[/·,+]|\be\b", _norm_classe(classe))) if p]
    for parte in partes or [""]:
        if parte.startswith(PREFIXOS_DE_PRODUTO):
            return f"classe `{parte}` é de produto"
        if not legado and parte not in lista and parte.startswith(CLASSES_DE_PRODUTO):
            return f"classe `{parte}` é de produto — decide-a o passo de completude da spec, em produto (prompt 046)"
        if parte not in lista:
            return f"classe `{parte or '—'}` fora da lista do D0{'' if legado else '-UX'} ({', '.join(lista)})"
    return ""


def lacunas_fechadas_pelo_agente(relatorio_lacunas: str, pareceres: str = "") -> List[str]:
    """Linhas da tabela do D0 com classe de produto (`classe_de_produto`) e cor que não é vermelha.

    O prompt do D0 diz que as duas classes são sempre vermelhas — decisão humana. Na exp01ef1b o D0-7
    saiu `classe: curriculo, cor: verde` e marcou "Resolvido" num `[ABERTO — dono: editorial]`: a
    pendência sumiu do dossiê. Lido pelo nome das colunas «Classe» e «Cor».

    `pareceres` (o texto dos pareceres e pedidos do PO na sessão): a linha cuja fonte é um desses pareceres não é
    do agente — a decisão humana já foi tomada, e o D0 só a aplicou. Na exp02em1b (22/10/2026) o PO aprovou no
    parecer de produto as duas propostas de mecânica, o D0 fechou-as citando o parecer, e este gate mandou
    reabri-las para o PO. Essas linhas saem em `lacunas_fechadas_pelo_parecer`, para a pessoa conferir.
    """
    return [linha for linha, humano in _lacunas_fechadas(relatorio_lacunas, pareceres) if not humano]


def lacunas_fechadas_pelo_parecer(relatorio_lacunas: str, pareceres: str) -> List[str]:
    """As linhas de `lacunas_fechadas_pelo_agente` cuja fonte cita um parecer humano registrado em `pareceres`."""
    return [linha for linha, humano in _lacunas_fechadas(relatorio_lacunas, pareceres) if humano]


def _lacunas_fechadas(relatorio_lacunas: str, pareceres: str = "") -> List[tuple]:
    """`(linha, fonte_cita_parecer_humano)` de cada lacuna de mecânica ou currículo que não saiu vermelha."""
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
        classe, cor = d.get("classe", ""), norm(d.get("cor", ""))
        if classe_de_produto(classe) and cor and "vermelh" not in cor and "🔴" not in d.get("cor", ""):
            fonte = " ".join(v for k, v in d.items() if k.startswith(("fonte", "base")))
            saida.append((re.sub(r"\s+", " ", linha.strip())[:220], bool(pareceres) and _cita_parecer_humano(fonte, pareceres)))
    return saida


def _parecer_datado(base: str, pareceres: str) -> bool:
    """A base cita um parecer humano registrado na sessão, com data, e não é o «Tudo de acordo» genérico — que não
    aprova PROPOSTA (plano, D3: o D0-4 da exp02ef1b tornou PQ-01..05 «contratuais» a partir de um)."""
    from tools.propagacao import _RE_PARECER_GENERICO

    # o D0 também escreve a data em ISO («Parecer de Produto (2026-10-23)», exp03ef1b); o parecer gravado é dd/mm/aaaa
    base = re.sub(r"\b(\d{4})-(\d{2})-(\d{2})\b", r"\3/\2/\1", base or "")
    return bool(pareceres) and _cita_parecer_humano(base, pareceres) and not _RE_PARECER_GENERICO.search(base)


def _marcadores_com_contexto(texto: str) -> List[Dict[str, str]]:
    """Os [PARÂMETRO]/[PROPOSTA] do texto; o que não traz descrição dentro dos colchetes — «| Preservação de 2 seções
    do DS … | `[PROPOSTA — validar com PO]` |», bloco 12 da exp02em1b — ganha a da própria linha. O número sugerido
    continua só o de dentro do marcador: «aula de 50 min» na linha não é sugestão."""
    from tools.propagacao import marcadores_abertos

    saida: List[Dict[str, str]] = []
    for linha in (texto or "").splitlines():
        for mk in marcadores_abertos(linha):
            if not mk["descricao"].strip(" `*|"):
                contexto = linha.replace(mk["texto"], " ")
                mk = {**mk, "descricao": contexto, "sugestao": ""}
            saida.append(mk)
    return saida


#: A decisão que escreve o marcador em vez de decidir: «[PARÂMETRO — a definir por produto: … · sugestão: 45 s]».
_RE_DEIXA_AO_PO = re.compile(r"\[(?:PAR[ÂA]METRO|PROPOSTA)\b|\[ABERTO\s*[—–-]\s*dono:\s*(?:o\s+)?PO\b", re.I)


def decisoes_d0_de_produto(fechamento: str, envelope: Dict[str, Any] | None, spec_gate0: str,
                           pareceres: str = "", classes_na_tabela: bool = True, topicos: bool = False,
                           prefixo: str = "D0", legado: bool = False) -> tuple:
    """`(sem_parecer, pelo_parecer)`: as decisões [D0-n] que decidem no lugar do PO, em linhas para o achado.

    Todo [D0-n] que fecha um [PARÂMETRO] ou promove uma [PROPOSTA] da spec do Gate 0 é decisão de produto, qualquer
    que seja a classe — inclusive duração, dados e acessibilidade, que a tabela de autoridade do D0 deixa em verde ou
    amarelo. Foi assim que o teto de 15 palavras, a moldura de 10%, os 45 s e as PQ-01..05 da exp02ef1b, e o StoryPoll
    da exp02em1b, saíram do D0 sem o PO (plano «Produto dono do contrato», PR 2). Com parecer datado na base, a decisão
    é do PO e o D0 só a aplicou: sai em `pelo_parecer`, para a pessoa conferir.

    `classes_na_tabela=False` (o D0 não trouxe a tabela do Passo 2 com Classe e Cor): a classe declarada no envelope é
    conferida aqui, por lista branca e prefixo.

    `topicos=True` (o D0-UX do PR 6): a decisão que trata de painel docente, PQ e KPI, retenção de dados, revezamento ou
    texto do professor é de produto mesmo com classe de UI — o revezamento da exp03em1b (D0-8) e a retenção da exp02ef1b
    (D0-8) vieram com classe `dispositivo` e `dados`. `prefixo="CP"` confere as decisões do passo de completude de
    produto (prompt 046): em produto, o que fecha [PARÂMETRO]/[PROPOSTA] sem parecer datado também é do PO."""
    from tools.propagacao import decisoes_do_agente, fecha_marcador, topico_de_produto

    marcadores = _marcadores_com_contexto(spec_gate0)
    sem_parecer: List[str] = []
    pelo_parecer: List[str] = []
    for d in decisoes_do_agente(fechamento, envelope or {}, prefixo):
        if "vermelh" in _norm_classe(d["cor"]) or "🔴" in d["cor"]:
            continue
        if prefixo != "D0" and _RE_DEIXA_AO_PO.search(d["decisao"]):
            continue  # a decisão da completude que escreve o marcador deixa a pergunta ao PO: é o que se pede dela
        motivos = []
        fechado = fecha_marcador(f"{d['campo']} {d['titulo']}", d["decisao"], marcadores) if marcadores else None
        if fechado:
            motivos.append(f"fecha {fechado[:110]}")
        # classe que o D0 não declarou («?»: sem envelope) não tem o que conferir; o marcador fechado, sim
        if prefixo == "D0" and not classes_na_tabela and d["classe"] not in ("", "?") and classe_de_produto(
                d["classe"], legado=legado):
            motivos.append(classe_de_produto(d["classe"], legado=legado))
        if prefixo != "D0" and _norm_classe(d["classe"]).startswith("ambiente"):
            # PR 8 (D8): a classe do ambiente, o ambiente novo e as regras e fases do mini-jogo são do PO — a completude
            # pergunta, não decide (prompt 046)
            motivos.append("classe `ambiente`: classe, ambiente e regras e fases do mini-jogo são decisão do PO")
        if topicos and not motivos:
            topico = topico_de_produto(d)
            if topico:
                motivos.append(f"tópico de produto: {topico}")
        if not motivos:
            continue
        linha = f"[{d['id']}] {d['campo'] or d['titulo']} · classe `{d['classe']}` · " + " · ".join(motivos)
        base = f"{d.get('base_texto', '')} {d.get('base', '')}"
        (pelo_parecer if _parecer_datado(base, pareceres) else sem_parecer).append(re.sub(r"\s+", " ", linha)[:260])
    return sem_parecer, pelo_parecer


def tabela_de_classes(relatorio_lacunas: str) -> bool:
    """O texto traz a tabela do Passo 2 com as colunas «Classe» e «Cor»."""
    for linha in (relatorio_lacunas or "").splitlines():
        m = _RE_CELULAS.match(linha)
        if m:
            cab = [_norm_classe(c) for c in m.group(1).split("|")]
            if "classe" in cab and "cor" in cab:
                return True
    return False

