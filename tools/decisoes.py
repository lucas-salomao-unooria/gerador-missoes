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
                      "painel", "pq-kpi", "revezamento", "regra", "mecanica", "curriculo")
#: Prefixos de classe que são sempre de produto — decisão do PO (plano «Produto dono do contrato», PR 2).
PREFIXOS_DE_PRODUTO = ("mecanica", "curriculo", "parametro")


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

