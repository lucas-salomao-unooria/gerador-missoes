"""Matriz de propagação: o que produto decidiu chega a jusante, e o que está a jusante nasceu em produto?

Só leitura: mede, não bloqueia. É o PR 1 do plano «Produto dono do contrato» (docs/planos/
2026-10-23-produto-dono-do-contrato.md). As cinco análises de 23/10/2026 contaram à mão, cada uma com o seu
script, o que o design decide no lugar de produto e o que o PRD diz sem origem no contrato; os números divergiam
entre analistas (9, 11 ou 13 decisões D0 «de produto», conforme o critério). Os PRs 2 a 9 mudam esse quadro, e
precisam de uma régua única, em código, para provar que mudaram. Esta é a régua. Quatro relatórios por sessão:

1. **pedido do PO × documentos** — cada texto entre aspas de um pedido do PO, contado em cada documento. Na
   exp02ef1b (23/10 13:24) os textos novos tinham 0 ocorrências em núcleo, one-pager e spec e de 1 a 13 a
   jusante; dos «textos atuais», 9 de 10 nunca estiveram em produto: o design os tinha escrito.
2. **classe real de cada [D0-n]** — a classe que o D0 declara é escolhida pelo próprio agente
   (`tools/decisoes.py` só barra `mecanica` e `curriculo` por igualdade, e `mecanica_param` passou). Aqui a classe
   sai do que a decisão faz: fecha [PARÂMETRO]/[PROPOSTA], toca tópico que o plano dá a produto, aplica parecer
   datado, contraria recusa do PO — ou é UI/UX.
3. **números e textos do corpo do PRD e do handoff sem origem no contrato** — com a procedência (produto, design,
   dev, só no documento), e o caminho inverso: número do one-pager (§10, §15, §17) ausente ou trocado no corpo
   (a cadeia 30% → 25% da H1 da exp02ef1b; as 35 palavras da exp06ef1b), e texto do §4 que não chegou à copy.
4. **[D0-n] citados a jusante e ausentes da spec** — o bloco 13 se perdeu em 2 de 5 sessões (linhas-perdidas), e o
   PRD da exp02ef1b cita D0-1 e D0-6 apontando para uma spec sem nenhum [D0-n].

`python -m tools.propagacao <estado.json | X.estado.json | pasta> [--sem-conversa] [--json] [--quadro]` (a conversa
da sessão, `X.json` ou `conversa.json` ao lado do estado, é lida quando existe); o acervo inteiro sai em
`python scripts/regressao_gates.py --propagacao`.
"""
from __future__ import annotations

import argparse
import functools
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------- documentos
#: Contrato de produto: o que o PO aprova (one-pager, núcleo, spec do Gate 0) e o que ele mesmo escreveu (briefing,
#: one-pager do PO). A `spec_missao` depois do design tem dois autores (blocos 13 e 14 são do D0 e do D9), e entra
#: só sem esses blocos, como `spec_produto`.
CONTRATO = ("briefing", "one_pager_po", "nucleo_narrativo", "one_pager", "spec_missao_gate0", "spec_produto")
#: A jusante, na ordem da esteira, com a etapa dona.
JUSANTE: Tuple[Tuple[str, str], ...] = (
    ("fechamento_lacunas", "design"), ("ambiente_simulado", "design"), ("brief_oficio", "design"),
    ("jornada_telas", "design"), ("fluxo_arestas", "design"), ("copy_strings", "design"),
    ("copy_strings_revisada", "design"), ("camada_caa", "design"), ("wireframes_cobertura", "design"),
    ("prototipo_html", "design"), ("prototipo_relatorio", "design"),
    # o pedagógico fecha o design desde o PR 10 (24/10/2026)
    ("one_pager_pedagogico", "design"),
    ("handoff_dev", "dev"), ("brief_assets", "dev"), ("banco_conteudo", "dev"), ("prd_final", "dev"),
)
#: Colunas da matriz do pedido (a mesma da matriz de 23/10/2026), com abreviação.
COLUNAS_PEDIDO: Tuple[Tuple[str, str], ...] = (
    ("one_pager_po", "po1p"), ("nucleo_narrativo", "nucl"), ("one_pager", "1p"),
    ("spec_missao_gate0", "spG0"), ("spec_produto", "spec"), ("fechamento_lacunas", "D0"),
    ("ambiente_simulado", "D9"), ("jornada_telas", "jorn"), ("copy_strings_revisada", "copy"),
    ("prototipo_html", "prot"), ("handoff_dev", "hand"), ("banco_conteudo", "banc"), ("prd_final", "PRD"),
    ("one_pager_pedagogico", "1pPed"),
)
#: Os documentos de saída onde se procura `[CONFLITO …]` (as notas de passagem trazem só a instrução).
DOCUMENTOS_DE_SAIDA = ("nucleo_narrativo", "one_pager", "spec_missao_gate0", "spec_missao") + tuple(
    k for k, _ in JUSANTE)

_RE_TITULO_13_14 = re.compile(r"^#{1,3}\s*\**\s*1[34]\s*[.—–-]", re.M)
_RE_TITULO_2 = re.compile(r"^#{1,2}\s", re.M)


def _blocos_do_design(spec: str) -> List[Tuple[int, int]]:
    """Trechos dos blocos 13 (D0) e 14 (D9) da spec: do título ao próximo título de nível 1 ou 2."""
    trechos = []
    for m in _RE_TITULO_13_14.finditer(spec or ""):
        prox = _RE_TITULO_2.search(spec, m.end())
        trechos.append((m.start(), prox.start() if prox else len(spec)))
    return trechos


def spec_de_produto(spec: str) -> str:
    """A spec sem os blocos 13 e 14, que são do design."""
    saida, pos = [], 0
    for ini, fim in _blocos_do_design(spec):
        saida.append(spec[pos:ini])
        pos = fim
    saida.append((spec or "")[pos:])
    return "".join(saida)


def bloco_13(spec: str) -> str:
    m = re.search(r"^#{1,3}\s*\**\s*13\s*[.—–-][^\n]*$", spec or "", re.M)
    if not m:
        return ""
    prox = _RE_TITULO_2.search(spec, m.end())
    return spec[m.start(): prox.start() if prox else len(spec)]


def documentos(state: Dict[str, Any]) -> Dict[str, str]:
    """Os documentos que os quatro relatórios leem, com a `spec_produto` (a spec sem os blocos do design)."""
    chaves = (set(CONTRATO) | set(DOCUMENTOS_DE_SAIDA) | set(CONTRATO_PROCEDENCIA) | set(PROCEDENCIA_DESIGN)
              | set(PROCEDENCIA_DEV) | set(CITAM_D0)) - {"spec_produto"}
    docs = {k: str(state.get(k) or "") for k in chaves}
    # desde o PR 6 os blocos 13 e 14 moram no anexo de design: a `spec_missao` da régua é a spec de produto mais o anexo,
    # como a da sessão anterior, que os trazia dentro (`tools.anexo_design.spec_consolidada`)
    from tools.anexo_design import spec_consolidada

    docs["spec_missao"] = spec_consolidada(state)
    docs["spec_produto"] = spec_de_produto(docs.get("spec_missao", ""))
    if spec_gate0_inferida(state):
        docs["spec_missao_gate0"] = docs["spec_produto"]
    return docs


def spec_gate0_inferida(state: Dict[str, Any]) -> bool:
    """Sem `spec_missao_gate0`, a spec do Gate 0 é a `spec_missao` sem os blocos 13 e 14. Sessões antigas e as que
    pararam em produto não gravam a cópia do Gate 0 (no acervo de 23/10/2026: exp01em1b, exp03ef1b, exp01em1b-e3980485,
    exp01em1b-76d9af6e e exp02em1b-60cfa7f4), e a régua contava 0 [PARÂMETRO] na spec do Gate 0 e dava ao design o
    que estava na spec de produto. É aproximação quando a sessão passou pelo design: edição em linha do A066/A068
    fora dos blocos 13/14 conta como produto, e o relatório avisa."""
    return not str(state.get("spec_missao_gate0") or "").strip() and bool(str(state.get("spec_missao") or "").strip())


# --------------------------------------------------------------------------- normalização
def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower()) if unicodedata.category(c) != "Mn")


def _palavras(texto: str) -> List[str]:
    return re.sub(r"[^a-z0-9]+", " ", _sem_acento(texto)).split()


class _Corpus:
    """Cada documento normalizado uma vez só: o protótipo passa de 1 MB e a matriz consulta centenas de frases."""

    def __init__(self, docs: Dict[str, str]):
        self.docs = docs
        self._norm: Dict[str, str] = {}

    def norm(self, chave: str) -> str:
        if chave not in self._norm:
            self._norm[chave] = " " + " ".join(_palavras(self.docs.get(chave, ""))) + " "
        return self._norm[chave]

    def conta(self, chave: str, frase: str) -> Optional[int]:
        """Ocorrências da frase (palavras inteiras, sem caixa nem acento); None se o documento não existe."""
        if not self.docs.get(chave, "").strip():
            return None
        alvo = " ".join(_palavras(frase))
        return self.norm(chave).count(" " + alvo + " ") if alvo else 0


# --------------------------------------------------------------------------- 1. pedido do PO × documentos
_ASPAS = (("“", "”"), ('"', '"'), ("«", "»"))
_RE_TROCA = re.compile(r"\btroc\w*\s+([\"“«][^\"”»\n]{2,300}[\"”»])\s+por\s+([\"“«][^\"”»\n]{2,300}[\"”»])", re.I)
_RE_PASSA_A_SER = re.compile(r"([\"“«][^\"”»\n]{2,300}[\"”»])\s+passa\s+a\s+ser\s+([\"“«][^\"”»\n]{2,300}[\"”»])", re.I)
_RE_MARCA_ATUAL = re.compile(r"\btexto\s+atual\b|\batualmente\b|\bhoje\s+(?:est[áa]|diz|aparece)", re.I)
_RE_MARCA_NOVO = re.compile(r"\bajuste\s+solicitado\b|\baltera[çc][ãa]o\s+solicitada\b|\bnovo\s+texto\b|"
                            r"\btexto\s+novo\b|\bpassa\s+a\s+ser\b|\bdeve\s+ficar\b", re.I)


def _entre_aspas(texto: str) -> List[Tuple[int, str]]:
    """(posição, trecho) de cada citação; “…” pareia com ”, «…» com », e a reta abre e fecha alternadamente."""
    saida, aberta, inicio = [], None, 0
    for i, c in enumerate(texto or ""):
        if aberta is None:
            for a, f in _ASPAS:
                if c == a:
                    aberta, inicio = f, i + 1
                    break
        elif c == aberta:
            trecho = texto[inicio:i]
            if aberta == "»" and re.search(r"[“\"]", trecho):
                # «…» que cita outra citação é relato de gate colado no pedido (exp02ef1b, 23/10/2026 14:37): valem
                # as citações de dentro, não o relato inteiro
                saida += [(inicio + p, t) for p, t in _entre_aspas(trecho)]
            else:
                saida.append((inicio, trecho))
            aberta = None
        elif c == "\n" and texto[inicio:i].strip() and len(texto[inicio:i]) > 300:
            aberta = None  # aspa sem par não engole o pedido inteiro
    return saida


def frases_do_pedido(texto: str) -> List[Dict[str, str]]:
    """Textos entre aspas do pedido, cada um com o papel: `atual` (o que o PO cita para trocar), `novo` (o que pede)
    ou `citado`. O papel vem de «trocar X por Y», «X passa a ser Y» e dos rótulos «Texto atual» / «Ajuste solicitado»
    do formato por tela (exp02ef1b, 23/10/2026 13:24)."""
    papeis: Dict[int, str] = {}
    for rx in (_RE_TROCA, _RE_PASSA_A_SER):
        for m in rx.finditer(texto or ""):
            papeis[m.start(1) + 1] = "atual"
            papeis[m.start(2) + 1] = "novo"
    marcas = sorted([(m.start(), "atual") for m in _RE_MARCA_ATUAL.finditer(texto or "")]
                    + [(m.start(), "novo") for m in _RE_MARCA_NOVO.finditer(texto or "")]
                    + [(m.start(), "citado") for m in re.finditer(r"^#{1,6}\s|\bobserva[çc][ãa]o\b", texto or "",
                                                                     re.M | re.I)])
    saida, vistas = [], set()
    for pos, trecho in _entre_aspas(texto or ""):
        frase = re.sub(r"\s+", " ", trecho).strip()
        if len(_palavras(frase)) < 1 or len(frase) > 300 or frase in vistas:
            continue
        vistas.add(frase)
        papel = papeis.get(pos)
        if papel is None:
            anteriores = [p for q, p in marcas if q < pos]
            papel = anteriores[-1] if anteriores else "citado"
        saida.append({"texto": frase, "papel": papel})
    return saida


def pedidos_do_po(state: Dict[str, Any], conversa: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    """Pedidos do PO gravados no estado e, com a conversa, os do histórico de correções que o estado não tem."""
    pedidos = [{"origem": str(p.get("origem") or ""), "etapa": str(p.get("etapa") or ""), "texto": str(p.get("texto") or "")}
               for p in state.get("pedidos_do_po") or [] if isinstance(p, dict)]
    # o mesmo pedido chega pelos dois caminhos com espaços ou prefixo diferentes: compara as palavras, e um contido no
    # outro é o mesmo pedido (exp02em1b, refazer de produto de 23/10/2026 11:01 e a correção das 11:04)
    vistos = [" ".join(_palavras(p["texto"])) for p in pedidos]
    for h in (conversa or {}).get("historico_correcoes") or []:
        texto = str(h.get("pedido") or "")
        chave = " ".join(_palavras(texto))
        if chave and not any(chave in v or v in chave for v in vistos if v):
            vistos.append(chave)
            pedidos.append({"origem": f"correção · {h.get('etapa', '')} · {h.get('quando', '')}",
                            "etapa": str(h.get("etapa") or ""), "texto": texto})
    return pedidos


def pedido_x_documentos(state: Dict[str, Any], conversa: Optional[Dict[str, Any]] = None,
                        corpus: Optional[_Corpus] = None) -> List[Dict[str, Any]]:
    """Relatório 1: cada frase de cada pedido, contada em cada documento, com a situação:
    `em-produto` (aparece no contrato), `so-a-jusante` (0 no contrato, presente em design ou dev) ou `ausente`."""
    corpus = corpus or _Corpus(documentos(state))
    contrato = [k for k in CONTRATO if k not in ("briefing", "one_pager_po")]
    saida = []
    for p in pedidos_do_po(state, conversa):
        frases = []
        for f in frases_do_pedido(p["texto"]):
            if len(_palavras(f["texto"])) < 2:
                continue  # palavra solta («Pronto») casa com qualquer texto: a matriz de 23/10 também a deixou de fora
            contagens = {k: corpus.conta(k, f["texto"]) for k, _ in COLUNAS_PEDIDO}
            em_contrato = sum(corpus.conta(k, f["texto"]) or 0 for k in contrato)
            a_jusante = sum(corpus.conta(k, f["texto"]) or 0 for k, _ in JUSANTE if k not in ("fechamento_lacunas",
                                                                                              "ambiente_simulado"))
            situacao = "em-produto" if em_contrato else ("so-a-jusante" if a_jusante else "ausente")
            frases.append({**f, "contagens": contagens, "em_contrato": em_contrato, "a_jusante": a_jusante,
                           "situacao": situacao})
        if frases:
            saida.append({**{k: p[k] for k in ("origem", "etapa")}, "frases": frases})
    return saida


# --------------------------------------------------------------------------- 2. classe real de cada [D0-n]
_RE_D0_CABECALHO = re.compile(r"^[#>\s`*-]*\[(D0-\d+)\]\**\s*(.*)$", re.M)
_RE_CAMPO = re.compile(r"\*{0,2}(Decis[ãa]o|Base|Revers[íi]vel|Risco se errado)\*{0,2}\s*:\s*\**\s*", re.I)
#: Data do parecer, nos dois formatos que o D0 escreve: «21/10/2026» e «Parecer de Produto (2026-10-23)» (exp03ef1b).
_RE_DATA = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b|\b(\d{4})-(\d{2})-(\d{2})\b")
#: Classes que são de produto por prefixo (o que o PR 2 passa a barrar por lista branca): `mecanica_param` da exp02ef1b
#: (10% da moldura) passou pelo gate porque a comparação era por igualdade.
CLASSES_DE_PRODUTO = ("mecanica", "curriculo", "parametro")
#: Tópicos que o plano (tabela «Agente por agente», A065) leva a produto, procurados no campo e no título da decisão.
_TOPICO_PRODUTO: Tuple[Tuple[str, "re.Pattern[str]"], ...] = (
    ("painel docente", re.compile(r"painel|dashboard")),
    ("perguntas de produto e KPI", re.compile(r"perguntas?_?de?_?produto|\b9f\b|\bpq\b|\bkpi")),
    ("dados e retenção", re.compile(r"retenc|evidencias_dados|nao_coletad")),
    # a instrução de gatilho também aparece só no padrão citado na base (`instrucao-de-gatilho-para-professora`)
    ("texto do professor ou podcast", re.compile(r"instrucao_(?:de_)?gatilho|instrucao_(?:d[ao]_)?professor|"
                                                 r"gatilhos?_(?:de_)?handoff|gatilho_para_professor|roteiro|podcast|"
                                                 r"fala_d[ao]_professor|texto_d[ao]_professor")),
    ("revezamento", re.compile(r"revezamento|cenario_compartilhado")),
)
#: No texto da decisão: protocolo de revezamento e prazo de guarda de dados são produto mesmo sob campo de dispositivo
#: (exp03em1b D0-8 e exp01em1b D0-4, 21–23/10/2026: o PO tinha recusado revezamento na exp06ef1b).
_TEXTO_PRODUTO: Tuple[Tuple[str, "re.Pattern[str]"], ...] = (
    ("revezamento", re.compile(r"revezamento", re.I)),
    ("dados e retenção", re.compile(r"reten[çc][ãa]o|ano letivo|anonimiza", re.I)),
)


def topico_de_produto(d: Dict[str, Any]) -> str:
    """O tópico que o plano dá a produto (painel, PQ e KPI, dados e retenção, texto do professor, revezamento) no campo,
    no título ou no texto da decisão, ou "" — a mesma régua de `classificar_d0`, para o D0-UX do PR 6."""
    chave = re.sub(r"[\s-]+", "_", _sem_acento(f"{d.get('campo', '')} {d.get('titulo', '')} {d.get('base', '')}"))
    for nome, rx in _TOPICO_PRODUTO:
        if rx.search(chave):
            return nome
    for nome, rx in _TEXTO_PRODUTO:
        if rx.search(str(d.get("decisao") or "")):
            return nome
    return ""


#: Número que decide regra de produto (tempo, teto, porcentagem). `px` é alvo de toque: acessibilidade de componente.
_RE_NUMERO = re.compile(r"(?<![\w.,/])(\d+(?:[.,]\d+)?)\s?(%|segundos?\b|seg\b|s\b|minutos?\b|min\b|palavras\b|caracteres\b|px\b)",
                        re.I)
_UNIDADE = {"segundo": "s", "segundos": "s", "seg": "s", "s": "s", "minuto": "min", "minutos": "min", "min": "min",
            "%": "%", "palavras": "palavras", "caracteres": "caracteres", "px": "px"}
_ALIAS = {"s": ("s", "seg", "segundo", "segundos"), "min": ("min", "minuto", "minutos"), "%": ("%",),
          "palavras": ("palavras",), "caracteres": ("caracteres",), "px": ("px",)}
#: Parecer genérico não aprova PROPOSTA (decisão D3 do plano): o D0-4 da exp02ef1b tornou PQ-01..05 «contratuais»
#: citando o «Tudo de acordo e podemos seguir design» de 22/10/2026, dado pela conta design.
_RE_PARECER_GENERICO = re.compile(r"tudo\s+de\s+acordo|de\s+acordo\s+e\s+(?:podemos\s+)?segu|sem\s+ressalvas|pode\s+seguir",
                                  re.I)
_RE_FONTE_DE_AGENTE = re.compile(r"adequa|pedag[óo]gic|estrutural|\bgate\b|banca|comit|juiz|avalia", re.I)
#: Item que o PO recusou num parecer: «[PROPOSTA …: … StoryPoll …] → ignorar / não implementar» (exp02em1b, 21/10/2026).
_RE_RECUSA = re.compile(r"^(.*?)(?:→|->)\s*(?:ignorar|n[ãa]o\s+implementar|recus|remov|rejeit|n[ãa]o\s+aprovad|vetad)",
                        re.I | re.M)
_RE_TERMO_PROPRIO = re.compile(r"`([^`\n]{3,40})`|\b([A-Z][a-z]+[A-Z]\w*)\b")
_PALAVRAS_VAZIAS = set("""a o as os de da do das dos e em no na nos nas um uma por para com sem que se ao aos
sugestao definir produto validar po proposta parametro p0a p0b mais menos como pela pelo""".split())


def alvo_de_toque_minimo(raiz: Optional[Path] = None) -> int:
    """O alvo de toque do padrão `alvo-64-88-vao-16` (prompts/references/defaults-missao.md); 64 se não achar."""
    caminho = (raiz or Path(__file__).resolve().parent.parent) / "prompts" / "references" / "defaults-missao.md"
    try:
        m = re.search(r"alvo-(\d+)-\d+", caminho.read_text(encoding="utf-8"))
    except OSError:
        m = None
    return int(m.group(1)) if m else 64


#: O redator escreve número em LaTeX: «$\ge 80\%$ das duplas», «Teto estrito de $\le 15$ palavras» (PRD e handoff da
#: exp02ef1b-4fd72a9a, 22/10/2026). Só `$` e `\le` saíam, e toda porcentagem com `\%` ficava fora da conferência — o
#: «$\ge 80\%$» inventado no PRD não era número (revisão do PR #77, 24/10/2026).
_LATEX = ((re.compile(r"\\leq?(?![A-Za-z])"), "≤"), (re.compile(r"\\geq?(?![A-Za-z])"), "≥"),
          (re.compile(r"\\lt(?![A-Za-z])"), "<"), (re.compile(r"\\gt(?![A-Za-z])"), ">"), (re.compile(r"\\%"), "%"),
          (re.compile(r"\$"), ""))


def sem_latex(texto: str) -> str:
    """O texto com `$`, `\\le`/`\\leq`, `\\ge`/`\\geq`, `\\lt`/`\\gt` e `\\%` trocados pelo que eles escrevem."""
    texto = texto or ""
    if "$" not in texto and "\\" not in texto:
        return texto
    return _sem_latex(texto)


@functools.lru_cache(maxsize=256)
def _sem_latex(texto: str) -> str:
    """`sem_latex` com cache: `tem_numero` relê o mesmo contrato a cada número do corpo."""
    for rx, troca in _LATEX:
        texto = rx.sub(troca, texto)
    return texto


def numeros(texto: str) -> List[Tuple[str, str]]:
    """(número, unidade canônica) de cada número com unidade, na ordem, sem repetição — também em LaTeX
    (`sem_latex`)."""
    vistos: List[Tuple[str, str]] = []
    for m in _RE_NUMERO.finditer(sem_latex(texto)):
        tok = (m.group(1).replace(",", "."), _UNIDADE[m.group(2).lower()])
        if tok not in vistos:
            vistos.append(tok)
    return vistos


def tem_numero(texto: str, tok: Tuple[str, str]) -> bool:
    n, u = tok
    num = re.escape(n).replace(r"\.", "[.,]")
    for a in _ALIAS[u]:
        fim = r"\b" if a[-1].isalnum() else ""
        if re.search(rf"(?<![\w.,]){num}\s?{re.escape(a)}{fim}", sem_latex(texto), re.I):
            return True
    return False


def _significativas(texto: str) -> set:
    return {p for p in _palavras(re.sub(r"_", " ", texto)) if len(p) >= 4 and p not in _PALAVRAS_VAZIAS}


def marcadores_abertos(texto: str) -> List[Dict[str, str]]:
    """`[PARÂMETRO …]` e `[PROPOSTA …]`, com a descrição (o que vem depois de «produto:» / «PO:»)."""
    saida = []
    for m in re.finditer(r"\[(PAR[ÂA]METRO|PROPOSTA)([^\]\n]{0,400})\]", texto or ""):
        tipo = "parametro" if m.group(1).upper().startswith("PAR") else "proposta"
        resto = m.group(2)
        desc = re.split(r"(?:produto|PO)\s*:", resto, maxsplit=1)
        descricao = (desc[1] if len(desc) > 1 else re.sub(r"^\s*P0[ab]?\s*[—–:-]?", "", resto)).strip(" :—–-")
        saida.append({"tipo": tipo, "texto": m.group(0), "descricao": descricao})
    return saida


def fecha_marcador(campo_titulo: str, decisao: str, marcadores: Sequence[Dict[str, str]]) -> Optional[str]:
    """O primeiro [PARÂMETRO]/[PROPOSTA] de `marcadores` que a decisão fecha, ou `None`: o assunto do marcador está no
    campo e no título da decisão (2 palavras ou mais, e ao menos um terço das dele), ou a decisão adota o número que o
    marcador sugere. É a régua que deu, na exp02ef1b, os 15 palavras, os 10%, os 45 s e as PQ-01..05 do D0 como
    fechamento de marcador do produto; `tools/decisoes.py` a usa no gate do D0 (PR 2)."""
    palavras_d0 = _significativas(campo_titulo)
    numeros_d0 = numeros(decisao)
    for mk in marcadores:
        desc = _significativas(mk["descricao"].split("sugest")[0])
        comuns = desc & palavras_d0
        sugeridos = numeros(mk.get("sugestao", mk["descricao"]))
        if (len(comuns) >= 2 and len(comuns) * 3 >= len(desc)) or any(
                t in numeros_d0 and t[1] != "px" for t in sugeridos):
            return mk["texto"]
    return None


def _pareceres_texto(state: Dict[str, Any], conversa: Optional[Dict[str, Any]]) -> str:
    """Tudo o que o PO disse na sessão: notas de passagem, pedidos e, com a conversa, os pareceres (com a data)."""
    partes = [str(state.get("notas_de_passagem") or "")]
    partes += [str(p.get("origem") or "") + "\n" + str(p.get("texto") or "") for p in state.get("pedidos_do_po") or []
               if isinstance(p, dict)]
    fluxo = (conversa or {}).get("fluxo") or {}
    for p in fluxo.get("pareceres") or [] if isinstance(fluxo, dict) else []:
        if isinstance(p, dict):
            partes.append(f"{p.get('acao', '')} · {p.get('como', '')} · {p.get('quando', '')}\n{p.get('comentario', '')}")
    for h in (conversa or {}).get("historico_correcoes") or []:
        partes.append(f"{h.get('quando', '')}\n{h.get('pedido', '')}")
    return "\n\n".join(x for x in partes if x.strip())


def recusas_do_po(pareceres: str) -> List[Dict[str, Any]]:
    """Itens que o PO recusou num parecer, com os termos próprios (CamelCase ou entre crases) que os identificam."""
    saida = []
    for m in _RE_RECUSA.finditer(pareceres or ""):
        item = m.group(1).strip()
        termos = sorted({a or b for a, b in _RE_TERMO_PROPRIO.findall(item)})
        if termos:
            saida.append({"item": item[:240], "termos": termos})
    return saida


def decisoes_d0(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """As decisões do D0: o envelope dá classe, cor e base declaradas; o «Passo 3» do fechamento dá o texto."""
    return decisoes_do_agente(str(state.get("fechamento_lacunas") or ""), state.get("lacunas_status_envelope") or {})


def decisoes_do_agente(fechamento: str, envelope: Dict[str, Any], prefixo: str = "D0") -> List[Dict[str, Any]]:
    """As decisões `[<prefixo>-n]` de uma resposta no formato do D0: as do D0 (`D0`) ou as do passo de completude de
    produto (`CP`, prompt 046, PR 6), que segue o mesmo formato — «Passo 3» com as decisões e o envelope com a classe."""
    i = fechamento.find("Passo 3")
    j = fechamento.find("Passo 4", i + 1) if i >= 0 else -1
    trecho = fechamento[i:j] if i >= 0 and j > i else fechamento
    textos: Dict[str, Dict[str, str]] = {}
    cabecalho_re = _RE_D0_CABECALHO if prefixo == "D0" else re.compile(
        rf"^[#>\s`*-]*\[({re.escape(prefixo)}-\d+)\]\**\s*(.*)$", re.M)
    cabecalhos = list(cabecalho_re.finditer(trecho))
    for k, m in enumerate(cabecalhos):
        if m.group(1) in textos:
            continue
        corpo = trecho[m.end(): cabecalhos[k + 1].start() if k + 1 < len(cabecalhos) else len(trecho)]
        campos: Dict[str, str] = {}
        partes = _RE_CAMPO.split(corpo)
        for nome, valor in zip(partes[1::2], partes[2::2]):
            chave = _sem_acento(nome).split()[0]
            campos.setdefault(chave, re.sub(r"\s+", " ", valor.replace("```", " ")).strip(" -—*`"))
        textos[m.group(1)] = {"titulo": m.group(2).strip(" *`"), "decisao": campos.get("decisao", corpo.strip()[:1500]),
                              "base_texto": campos.get("base", "")}
    envelope = envelope if isinstance(envelope, dict) else {}
    declaradas = [d for d in envelope.get("decisoes") or [] if isinstance(d, dict) and d.get("id")]
    if not declaradas:
        declaradas = [{"id": i} for i in textos]
    saida = []
    for d in declaradas:
        t = textos.get(d["id"], {})
        saida.append({"id": d["id"], "campo": str(d.get("campo") or ""), "classe": str(d.get("classe") or "?"),
                      "cor": str(d.get("cor") or "?"), "base": str(d.get("base") or "?"),
                      "titulo": t.get("titulo", ""), "decisao": t.get("decisao", ""), "base_texto": t.get("base_texto", "")})
    return saida


def classificar_d0(d: Dict[str, Any], docs: Dict[str, str], pareceres: str = "",
                   recusas: Optional[List[Dict[str, Any]]] = None, alvo_minimo: int = 64) -> Dict[str, Any]:
    """Classe real de uma decisão D0, com os motivos. Em ordem:

    - `contraria-produto`: mantém o que o PO recusou num parecer (o D0-7 da exp02em1b confirmou o StoryPoll que o PO
      mandou não implementar em 21/10/2026);
    - `aplica-parecer`: a base cita um parecer humano datado e específico — decisão do PO que só o D0 gravou
      (`nao_gravada` quando o número decidido não está no one-pager: 90 s e 45 palavras da exp02em1b);
    - `produto`: classe de produto por prefixo, fecha [PARÂMETRO]/[PROPOSTA] ou pendência do contrato, ou toca tópico
      que o plano dá a produto (painel, PQ/KPI, dados e retenção, texto do professor ou podcast, revezamento);
    - `ux`: o resto (estado, gesto, scaffolding, acessibilidade de componente, dispositivo, copy de tela).

    `contraria_padrao` marca alvo de toque abaixo do padrão da plataforma (exp03em1b D0-9, 48 px contra 64): é
    acessibilidade, fica no D0-UX, mas contraria `defaults-missao.md`. `numeros_novos` só informa.
    """
    motivos: List[str] = []
    classe = _sem_acento(d.get("classe", ""))
    campo_titulo = f"{d.get('campo', '')} {d.get('titulo', '')}"
    chave = re.sub(r"[\s-]+", "_", _sem_acento(f"{campo_titulo} {d.get('base', '')}"))
    decisao = d.get("decisao", "")
    base_texto = d.get("base_texto", "") or d.get("base", "")
    contrato = "\n".join(docs.get(k, "") for k in ("nucleo_narrativo", "one_pager", "spec_missao_gate0"))
    flags: Dict[str, Any] = {}

    # contraria: termo próprio de um item recusado, mantido na decisão
    for r in recusas or []:
        achados = [t for t in r["termos"] if re.search(rf"\b{re.escape(t)}\b", f"{campo_titulo} {decisao}", re.I)]
        if achados:
            return {**d, "classe_real": "contraria-produto", "motivos": [f"mantém {', '.join(achados)}, recusado pelo PO: "
                                                                         f"«{r['item'][:120]}»"], **flags}

    # aplica parecer: «parecer» + data, que não seja relatório de agente nem «tudo de acordo»
    cita_parecer = bool(re.search(r"\bparecer\b", base_texto, re.I)) and not _RE_FONTE_DE_AGENTE.search(base_texto)
    datas = [f"{a}/{b}/{c}" if a else f"{f}/{e}/{y}" for a, b, c, y, e, f in _RE_DATA.findall(base_texto)]
    generico = bool(_RE_PARECER_GENERICO.search(base_texto))
    if cita_parecer and datas and not generico:
        conferido = bool(pareceres) and all(x in pareceres for x in datas)
        # sugestão não é decisão gravada: o one-pager da exp02em1b tinha «[PARÂMETRO …, sugestão: 45 palavras]» e, no
        # registro de mudanças, «com sugestão de 45 palavras» — a linha com marcador ou sugestão não conta
        one_pager = "\n".join(l for l in docs.get("one_pager", "").splitlines()
                              if not re.search(r"\[(?:PAR[ÂA]METRO|PROPOSTA)|sugest", l, re.I))
        nao_gravados = [f"{n} {u}" for n, u in numeros(decisao) if u != "px" and not tem_numero(one_pager, (n, u))]
        motivos.append(f"base cita parecer de {', '.join(datas)}" + ("" if conferido else " (data não conferida nos pareceres)"))
        if nao_gravados:
            flags["nao_gravada"] = nao_gravados
            motivos.append(f"o one-pager não tem {', '.join(nao_gravados)}: a decisão do PO só ficou no D0")
        return {**d, "classe_real": "aplica-parecer", "motivos": motivos, **flags}
    if cita_parecer and generico:
        motivos.append("base é parecer genérico («tudo de acordo»), que não aprova PROPOSTA (D3)")

    # produto
    if classe.startswith(CLASSES_DE_PRODUTO):
        motivos.append(f"classe declarada `{d.get('classe')}` é de produto")
    if re.search(r"pendencia", chave):
        motivos.append("fecha pendência do contrato")
    numeros_d0 = numeros(decisao)
    fechado = fecha_marcador(campo_titulo, decisao, marcadores_abertos(contrato))
    if fechado:
        motivos.append(f"fecha {fechado[:110]}")
    # número que o contrato não tem só informa: na rodada de 23/10/2026 eram tempos de animação e passos de slider
    # (exp02em1b D0-3, exp03em1b D0-9), que são UI; o número de regra de produto chega aqui fechando um [PARÂMETRO]
    novos = [f"{n} {u}" for n, u in numeros_d0 if u in ("s", "min", "%", "palavras") and not tem_numero(contrato, (n, u))]
    if novos:
        flags["numeros_novos"] = novos
    for nome, rx in _TOPICO_PRODUTO:
        if rx.search(chave):
            motivos.append(f"tópico de produto: {nome}")
            break
    else:
        for nome, rx in _TEXTO_PRODUTO:
            if rx.search(decisao):
                motivos.append(f"tópico de produto no texto: {nome}")
                break

    pequenos = [int(a) for a, b in re.findall(r"\b(\d{2})\s?[x×]\s?(\d{2})\s?px", decisao) if int(a) < alvo_minimo]
    if pequenos:
        flags["contraria_padrao"] = f"alvo de toque {min(pequenos)} px abaixo de {alvo_minimo} px (defaults-missao)"
    if motivos:
        return {**d, "classe_real": "produto", "motivos": motivos, **flags}
    return {**d, "classe_real": "ux", "motivos": [f"classe `{d.get('classe')}` sem marcador aberto nem tópico de produto"],
            **flags}


def classe_real_d0(state: Dict[str, Any], conversa: Optional[Dict[str, Any]] = None,
                   docs: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """Relatório 2: cada [D0-n] com a classe declarada e a classe real."""
    docs = docs or documentos(state)
    pareceres = _pareceres_texto(state, conversa)
    recusas = recusas_do_po(pareceres)
    alvo = alvo_de_toque_minimo()
    return [classificar_d0(d, docs, pareceres, recusas, alvo) for d in decisoes_d0(state)]


# --------------------------------------------------------------------------- 3. números e textos sem origem
#: Onde procurar a procedência (a mesma ordem da análise do consumidor do PRD, 23/10/2026).
PROCEDENCIA_DESIGN = ("fechamento_lacunas", "ambiente_simulado", "brief_oficio", "jornada_telas", "fluxo_arestas",
                      "copy_strings", "copy_strings_revisada", "wireframes_cobertura", "camada_caa", "prototipo_relatorio")
PROCEDENCIA_DEV = ("handoff_dev", "brief_assets", "banco_conteudo")
CONTRATO_PROCEDENCIA = ("briefing", "one_pager_po", "nucleo_narrativo", "one_pager", "spec_missao_gate0")
SECOES_DE_NUMERO = (10, 15, 17)


def _procedencia(achou: Callable[[str], bool], proprio: str) -> Tuple[str, List[str]]:
    """Onde o trecho nasceu: no contrato, nos blocos do design da spec, em design, em dev ou só no próprio documento."""
    onde_contrato = [k for k in CONTRATO_PROCEDENCIA if achou(k)]
    if onde_contrato:
        return "produto", onde_contrato
    if achou("spec_missao"):
        # não é só bloco 13/14: o A066/A068 também edita em linha a spec aprovada no Gate 0
        return "design", ["spec_missao (fora da spec do Gate 0)"]
    for etapa, chaves in (("design", PROCEDENCIA_DESIGN), ("dev", PROCEDENCIA_DEV)):
        onde = [k for k in chaves if k != proprio and achou(k)]
        if onde:
            return etapa, onde
    return "so-no-documento", []


def _citacoes(texto: str, minimo: int = 4) -> List[str]:
    saida = []
    for _, t in _entre_aspas(texto):
        t = re.sub(r"\s+", " ", t).strip()
        if len(_palavras(t)) >= minimo and t not in saida and "\n" not in t:
            saida.append(t)
    return saida


def _assinatura(linha: str) -> set:
    """Palavras da linha que a identificam: as significativas e os números sem unidade («Sessão 2», «Hipótese 1»).
    Sem os números, «Subtotal Sessão 2 | 12 min | 30 min» do one-pager casava com «Subtotal Sessão 1 | 12 min |
    25 min» do PRD da exp02ef1b, e o 30 saía trocado por 25."""
    sem_unidade = _RE_NUMERO.sub(" ", (linha or "").replace("$", ""))
    return _significativas(linha) | {f"#{n}" for n in re.findall(r"(?<![\w.,])\d+(?![\w.,]*\d)", sem_unidade)}


def _sobreposicao(a: set, b: set) -> float:
    return len(a & b) / max(1, len(a | b))


def contrato_no_corpo(one_pager: str, corpo: str, secoes: Sequence[int] = SECOES_DE_NUMERO) -> List[Dict[str, str]]:
    """Números do one-pager (§10, §15, §17) que o corpo não traz: `trocado` quando a linha correspondente do corpo
    (a mais parecida, por palavras) tem outro número da mesma unidade — H1 da exp02ef1b, 30% no one-pager e 25% no
    corpo do PRD —, `ausente` quando o número não aparece no corpo (as 35 palavras da exp06ef1b). `secoes` restringe:
    o gate do PR 4 (`tools/montagem.py`) confere só o §15 e o §17 — o tempo do §10 é do A116."""
    from tools.conteudo_aprovado import secao

    linhas_corpo = [(l, _assinatura(l)) for l in (corpo or "").splitlines() if l.strip()]
    saida = []
    for n_secao in secoes:
        for linha in (secao(one_pager or "", n_secao) or "").splitlines():
            # zero não é regra que propague («0 palavras de leitura autônoma», «0 min» de mediação na tabela de tempos)
            toks = [t for t in numeros(linha) if t[1] != "px" and float(t[0]) != 0]
            if not toks or re.search(r"\[PAR[ÂA]METRO", linha, re.I):
                continue
            sig = _assinatura(linha)
            melhor = max(linhas_corpo, key=lambda lc: _sobreposicao(sig, lc[1]), default=None)
            parecida = melhor if melhor and _sobreposicao(sig, melhor[1]) >= 0.5 else None
            for tok in toks:
                if parecida is not None and not tem_numero(parecida[0], tok):
                    # trocado só quando a linha do corpo traz número da mesma unidade que a linha do contrato não tem:
                    # «Aula única (50 min)» no corpo da exp06ef1b repete o 50 do contrato, não troca os 29 min
                    outros = [t for t in numeros(parecida[0]) if t[1] == tok[1] and not tem_numero(linha, t)]
                    if outros:
                        saida.append({"secao": f"§{n_secao}", "situacao": "trocado", "contrato": _fmt(tok),
                                      "corpo": ", ".join(_fmt(t) for t in outros),
                                      "linha": linha.strip()[:200], "linha_corpo": parecida[0].strip()[:200]})
                        continue
                if not tem_numero(corpo, tok):
                    saida.append({"secao": f"§{n_secao}", "situacao": "ausente", "contrato": _fmt(tok),
                                  "corpo": "", "linha": linha.strip()[:200], "linha_corpo": ""})
    return saida


def _fmt(tok: Tuple[str, str]) -> str:
    return f"{tok[0]}%" if tok[1] == "%" else f"{tok[0]} {tok[1]}"


def _presente_citado(curto: str, texto: str) -> bool:
    """Texto curto (até 3 palavras: «Lugar», «Cor da roupa») só conta entre aspas, crases ou célula de tabela —
    a palavra solta aparece em qualquer frase. Mais longo, conta a frase normalizada."""
    alvo = " ".join(_palavras(curto))
    if not alvo:
        return False
    if len(alvo.split()) > 3:
        return f" {alvo} " in " " + " ".join(_palavras(texto)) + " "
    corpo = re.sub(r"[^a-z0-9\"“”«»'`|*]+", " ", _sem_acento(texto))
    padrao = r"\s*".join(re.escape(p) for p in alvo.split())
    return bool(re.search(rf"[\"“”«»'`|*]\s*{padrao}\s*[\"“”«»'`|*]", corpo))


def textos_do_s4(one_pager: str) -> List[str]:
    """Textos entre aspas do §4 do one-pager (o que a criança lê ou ouve), de qualquer tamanho."""
    from tools.conteudo_aprovado import secao

    s4 = secao(one_pager or "", 4) or ""
    saida = []
    for _, t in _entre_aspas(s4):
        t = re.sub(r"\s+", " ", t).strip(" .")
        if _palavras(t) and len(t) <= 300 and t not in saida:
            saida.append(t)
    return saida


def sem_origem(state: Dict[str, Any], docs: Optional[Dict[str, str]] = None,
               corpus: Optional[_Corpus] = None) -> Dict[str, Any]:
    """Relatório 3: números e textos do corpo do PRD e do handoff, por procedência; e o contrato que não chegou."""
    from tools.conteudo_aprovado import remover_anexo

    docs = docs or documentos(state)
    corpus = corpus or _Corpus(docs)
    saida: Dict[str, Any] = {}
    for chave, rotulo in (("prd_final", "prd"), ("handoff_dev", "handoff")):
        texto = remover_anexo(docs.get(chave, ""))
        if not texto.strip():
            continue
        nums: Dict[str, List[Dict[str, Any]]] = {}
        for tok in numeros(texto):
            proc, onde = _procedencia(lambda k: tem_numero(docs.get(k, ""), tok), chave)
            nums.setdefault(proc, []).append({"numero": _fmt(tok), "onde": onde[:3]})
        txts: Dict[str, List[Dict[str, Any]]] = {}
        for frase in _citacoes(texto):
            proc, onde = _procedencia(lambda k: bool(corpus.conta(k, frase)), chave)
            txts.setdefault(proc, []).append({"texto": frase[:160], "onde": onde[:3]})
        saida[rotulo] = {"numeros": nums, "textos": txts}
        if rotulo == "prd":
            # só o PRD: o handoff não repete a tabela de tempos do §10, e cada linha dela virava «ausente»
            saida[rotulo]["contrato_no_corpo"] = contrato_no_corpo(docs.get("one_pager", ""), texto)
    s4 = textos_do_s4(docs.get("one_pager", ""))
    if s4:
        chegada = {}
        for chave in ("copy_strings_revisada", "prototipo_html", "prd_final"):
            alvo = remover_anexo(docs.get(chave, "")) if chave == "prd_final" else docs.get(chave, "")
            if alvo.strip():
                faltam = [t for t in s4 if not _presente_citado(t, alvo)]
                chegada[chave] = {"chegaram": len(s4) - len(faltam), "total": len(s4), "faltam": faltam}
        saida["s4_a_jusante"] = chegada
    return saida


# --------------------------------------------------------------------------- 4. [D0-n] a jusante × spec
_RE_D0 = re.compile(r"\bD0-(\d+)\b")
#: Onde uma citação [D0-n] aponta para a spec: produto (que nunca deveria citá-los) e a jusante.
CITAM_D0 = ("one_pager", "nucleo_narrativo", "brief_oficio", "jornada_telas", "fluxo_arestas",
            "copy_strings_revisada", "camada_caa", "wireframes_cobertura", "prototipo_html", "handoff_dev",
            "banco_conteudo", "prd_final", "one_pager_pedagogico")


def d0_a_jusante(state: Dict[str, Any], docs: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Relatório 4: ids [D0-n] definidos no bloco 13 da spec, se o bloco está lá, e cada citação a jusante de id que
    o bloco não tem. As marcas «Resolvido em [D0-n]» nas células da spec ficam quando o bloco 13 se perde (exp01ef1b,
    exp05ef1b e exp03ef1b-317df247 citam D0-1 e D0-7, ou D0-1 e D0-2, fora dele): contá-las como definição escondia
    os órfãos. Elas saem à parte, em `fora_do_bloco_13`."""
    from tools.conteudo_aprovado import remover_anexo

    docs = docs or documentos(state)
    spec = docs.get("spec_missao", "")
    b13 = bloco_13(spec)
    na_spec = sorted({int(x) for x in _RE_D0.findall(b13)})
    fora_do_bloco = sorted({int(x) for x in _RE_D0.findall(spec.replace(b13, "") if b13 else spec)})
    citacoes, orfas = {}, {}
    for k in CITAM_D0:
        texto = docs.get(k, "")
        if k == "prd_final":
            texto = remover_anexo(texto)
        ids = _RE_D0.findall(texto)
        if ids:
            citacoes[k] = {"mencoes": len(ids), "ids": sorted({int(x) for x in ids})}
            fora = sorted({int(x) for x in ids} - set(na_spec))
            if fora:
                orfas[k] = fora
    return {"decisoes": len(decisoes_d0(state)), "na_spec": na_spec, "bloco_13": bool(b13.strip()),
            "fora_do_bloco_13": fora_do_bloco, "citacoes": citacoes, "orfas": orfas}


# --------------------------------------------------------------------------- quadro e relatório
_RE_CONFLITO_INSTRUCAO = re.compile(r"\[CONFLITO\s*[—–-]\s*([^×\]\n]{1,40}?)\s*×")


def marcadores(state: Dict[str, Any], docs: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """[PARÂMETRO]/[PROPOSTA] abertos no one-pager e na spec do Gate 0; [CONFLITO] nos documentos e nas notas."""
    docs = docs or documentos(state)

    def conta(k: str, tipo: str) -> int:
        return sum(1 for m in marcadores_abertos(docs.get(k, "")) if m["tipo"] == tipo)

    return {
        "spec_gate0_inferida": spec_gate0_inferida(state),
        "one_pager": {"parametro": conta("one_pager", "parametro"), "proposta": conta("one_pager", "proposta")},
        "spec_gate0": {"parametro": conta("spec_missao_gate0", "parametro"), "proposta": conta("spec_missao_gate0", "proposta")},
        "conflito_documentos": sum(len(re.findall(r"\[CONFLITO", str(state.get(k) or ""))) for k in DOCUMENTOS_DE_SAIDA),
        # a instrução de registrar o conflito, pelo lado que ela opõe ao one-pager: «pedido do PO» ou «parecer»
        "conflito_instrucao": sorted({re.sub(r"\s+", " ", m).strip() for m in _RE_CONFLITO_INSTRUCAO.findall(
            str(state.get("notas_de_passagem") or ""))}),
    }


def avaliar(state: Dict[str, Any], conversa: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Os quatro relatórios e as contagens do quadro, para uma sessão."""
    docs = documentos(state)
    corpus = _Corpus(docs)
    env = state.get("lacunas_status_envelope") or {}
    d0 = classe_real_d0(state, conversa, docs)
    # os textos do §4 pelo extrator da matriz de rastreabilidade, o mesmo que deu 73/85 na copy e 69/85 no protótipo
    # no quadro do plano; o de `sem_origem` conta toda citação do §4, inclusive as opções curtas («Lugar»)
    from tools import rastreabilidade

    s4 = {c: v for c, v in (rastreabilidade.matriz(state)["cobertura"].get("texto_tela") or {}).items() if v}
    return {
        "pedidos": pedido_x_documentos(state, conversa, corpus),
        "d0": d0,
        "d0_respec": len(env.get("respec") or []),
        "sem_origem": sem_origem(state, docs, corpus),
        "d0_a_jusante": d0_a_jusante(state, docs),
        "marcadores": marcadores(state, docs),
        "s4_rastreabilidade": s4,
    }


def quadro(resultados: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """As contagens do quadro «O que os dados mostram», somadas sobre as sessões."""
    from collections import Counter

    com_d0 = {m: r for m, r in resultados.items() if r["d0"]}
    cores = Counter(_sem_acento(d["cor"]) for r in com_d0.values() for d in r["d0"])
    reais = Counter(d["classe_real"] for r in com_d0.values() for d in r["d0"])
    frases = [f for r in resultados.values() for p in r["pedidos"] for f in p["frases"]]
    return {
        "sessoes": len(resultados),
        "sessoes_com_d0": len(com_d0),
        "d0_por_sessao": {m: len(r["d0"]) for m, r in com_d0.items()},
        "d0_total": sum(len(r["d0"]) for r in com_d0.values()),
        "d0_cores": dict(cores),
        "d0_respec": sum(r["d0_respec"] for r in com_d0.values()),
        "d0_classe_real": dict(reais),
        "d0_nao_gravada": sum(1 for r in com_d0.values() for d in r["d0"] if d.get("nao_gravada")),
        "d0_contraria_padrao": sum(1 for r in com_d0.values() for d in r["d0"] if d.get("contraria_padrao")),
        "d0_no_one_pager": sum(r["d0_a_jusante"]["citacoes"].get("one_pager", {}).get("mencoes", 0) for r in resultados.values()),
        "bloco_13_na_spec": f"{sum(1 for r in com_d0.values() if r['d0_a_jusante']['bloco_13'])} de {len(com_d0)}",
        "d0_orfaos": {m: r["d0_a_jusante"]["orfas"] for m, r in resultados.items() if r["d0_a_jusante"]["orfas"]},
        "conflito_documentos": sum(r["marcadores"]["conflito_documentos"] for r in resultados.values()),
        "conflito_instrucao_nas_notas": {
            v: sum(1 for r in resultados.values() if v in r["marcadores"]["conflito_instrucao"])
            for v in sorted({v for r in resultados.values() for v in r["marcadores"]["conflito_instrucao"]})},
        "parametro_one_pager": {m: r["marcadores"]["one_pager"]["parametro"] for m, r in resultados.items()
                                if r["marcadores"]["one_pager"]["parametro"]},
        "spec_gate0": {m: r["marcadores"]["spec_gate0"] for m, r in resultados.items()
                       if any(r["marcadores"]["spec_gate0"].values())},
        "spec_gate0_inferida": sorted(m for m, r in resultados.items() if r["marcadores"]["spec_gate0_inferida"]),
        "s4_na_copy": _soma_fracoes(r["s4_rastreabilidade"].get("copy") for r in com_d0.values()),
        "s4_no_prototipo": _soma_fracoes(r["s4_rastreabilidade"].get("prototipo") for r in com_d0.values()),
        "frases_de_pedido_so_a_jusante": sum(1 for f in frases if f["situacao"] == "so-a-jusante"),
        "contrato_trocado_ou_ausente_no_prd": {
            m: [f"{c['secao']} {c['contrato']} {c['situacao']}" + (f" ({c['corpo']})" if c["corpo"] else "")
                for c in r["sem_origem"].get("prd", {}).get("contrato_no_corpo", [])]
            for m, r in resultados.items() if r["sem_origem"].get("prd", {}).get("contrato_no_corpo")},
    }


def _soma_fracoes(fracoes: Iterable[Optional[Tuple[int, int]]]) -> str:
    validas = [f for f in fracoes if f]
    return f"{sum(a for a, _ in validas)}/{sum(b for _, b in validas)}"


def _celula(v: Optional[int]) -> str:
    return "-" if v is None else str(v)


def relatorio(res: Dict[str, Any], missao: str = "") -> str:
    """Os quatro relatórios em markdown."""
    L = [f"# Propagação — {missao or 'missão'}", "",
         "Só leitura: mede o que produto decidiu e por onde passou, sem bloquear nada "
         "(plano «Produto dono do contrato», PR 1).", ""]
    mk = res["marcadores"]
    L += [f"Marcadores abertos: one-pager {mk['one_pager']['parametro']} [PARÂMETRO] e {mk['one_pager']['proposta']} "
          f"[PROPOSTA]; spec do Gate 0 {mk['spec_gate0']['parametro']} e {mk['spec_gate0']['proposta']}"
          + (" (sem `spec_missao_gate0`: lida da `spec_missao` sem os blocos 13/14, com as edições em linha do "
             "design, se houver)" if mk.get("spec_gate0_inferida") else "") + ". "
          f"[CONFLITO] nos documentos: {mk['conflito_documentos']}"
          + (f" (a instrução está nas notas de passagem: {', '.join(mk['conflito_instrucao'])} × one-pager)."
             if mk["conflito_instrucao"] else "."), ""]

    L += ["## 1. Pedido do PO × documentos", ""]
    if not res["pedidos"]:
        L += ["Nenhum pedido do PO com texto entre aspas.", ""]
    for p in res["pedidos"]:
        so = sum(1 for f in p["frases"] if f["situacao"] == "so-a-jusante")
        L += [f"### {p['origem']} · etapa {p['etapa']}", "",
              f"{len(p['frases'])} frase(s); {so} só a jusante (0 no contrato).", "",
              "| papel | situação | " + " | ".join(a for _, a in COLUNAS_PEDIDO) + " | frase |",
              "|---|---|" + "---:|" * len(COLUNAS_PEDIDO) + "---|"]
        for f in p["frases"]:
            L.append(f"| {f['papel']} | {f['situacao']} | " + " | ".join(_celula(f["contagens"][k]) for k, _ in COLUNAS_PEDIDO)
                     + f" | {f['texto'][:90].replace('|', '/')} |")
        L.append("")

    L += ["## 2. Classe real de cada [D0-n]", ""]
    if not res["d0"]:
        L += ["Sem decisões D0 (a sessão não passou pelo fechamento de lacunas).", ""]
    else:
        L += [f"Pedidos de re-spec ao Gate 0: {res['d0_respec']}.", "",
              "| D0 | campo | classe declarada | cor | base | classe real | motivos |", "|---|---|---|---|---|---|---|"]
        for d in res["d0"]:
            motivos = "; ".join(d["motivos"]) + (f"; ⚠️ {d['contraria_padrao']}" if d.get("contraria_padrao") else "") + (
                f"; ℹ️ número que o contrato não tem: {', '.join(d['numeros_novos'][:4])}" if d.get("numeros_novos") else "")
            L.append(f"| {d['id']} | {d['campo']} | {d['classe']} | {d['cor']} | {d['base']} | **{d['classe_real']}** | "
                     f"{motivos.replace('|', '/')[:300]} |")
        L.append("")

    L += ["## 3. Números e textos do corpo do PRD e do handoff sem origem no contrato", ""]
    so = res["sem_origem"]
    if not any(k in so for k in ("prd", "handoff")):
        L += ["Sem PRD nem handoff.", ""]
    for rotulo in ("prd", "handoff"):
        if rotulo not in so:
            continue
        r = so[rotulo]
        L += [f"### {rotulo.upper() if rotulo == 'prd' else 'Handoff'} (corpo, sem o anexo)", ""]
        for nome, chave in (("Números", "numeros"), ("Textos entre aspas (4+ palavras)", "textos")):
            cont = {k: len(v) for k, v in r[chave].items()}
            L.append(f"- {nome}: " + (", ".join(f"{k} {v}" for k, v in sorted(cont.items())) or "nenhum"))
            for proc in ("design", "dev", "so-no-documento"):
                itens = r[chave].get(proc) or []
                if itens:
                    exemplos = "; ".join((i.get("numero") or f"«{i['texto'][:60]}»") + (f" ({', '.join(i['onde'])})" if i["onde"] else "")
                                         for i in itens[:8])
                    L.append(f"  - {proc}: {exemplos}" + (" …" if len(itens) > 8 else ""))
        for c in r.get("contrato_no_corpo", []):
            L.append(f"- ⚠️ one-pager {c['secao']}: {c['contrato']} {c['situacao']}"
                     + (f" — corpo traz {c['corpo']}: «{c['linha_corpo'][:120]}»" if c["corpo"] else f" — «{c['linha'][:120]}»"))
        L.append("")
    if so.get("s4_a_jusante") or res.get("s4_rastreabilidade"):
        L += ["### Textos do §4 do one-pager a jusante", ""]
        for chave, (feitos, total) in (res.get("s4_rastreabilidade") or {}).items():
            L.append(f"- {chave} (extrator da matriz de rastreabilidade): {feitos}/{total}")
        for chave, v in (so.get("s4_a_jusante") or {}).items():
            L.append(f"- {chave} (toda citação do §4): {v['chegaram']}/{v['total']}" + (
                f" — faltam: {'; '.join('«' + t[:50] + '»' for t in v['faltam'][:6])}" + (" …" if len(v["faltam"]) > 6 else "")
                if v["faltam"] else ""))
        L.append("")

    j = res["d0_a_jusante"]
    L += ["## 4. [D0-n] citados a jusante e ausentes da spec", "",
          f"Decisões D0: {j['decisoes']}. No bloco 13 da spec: {', '.join(f'D0-{i}' for i in j['na_spec']) or 'nenhuma'}; "
          f"bloco 13 {'presente' if j['bloco_13'] else 'ausente'}."
          + (f" Citados na spec fora do bloco 13 (marcas, não definição): "
             f"{', '.join(f'D0-{i}' for i in j['fora_do_bloco_13'])}." if j.get("fora_do_bloco_13") else ""), ""]
    for k, c in j["citacoes"].items():
        orf = j["orfas"].get(k)
        L.append(f"- {k}: {c['mencoes']} menção(ões), ids {', '.join(f'D0-{i}' for i in c['ids'])}"
                 + (f" — ⚠️ fora da spec: {', '.join(f'D0-{i}' for i in orf)}" if orf else ""))
    L.append("")
    return "\n".join(L)


def relatorio_quadro(q: Dict[str, Any]) -> str:
    L = ["# Quadro da propagação", "", "| Medida | Valor |", "|---|---|"]
    for k, v in q.items():
        L.append(f"| {k} | {json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v} |")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- linha de comando
def _conversa_ao_lado(estado: Path) -> Optional[Path]:
    """A conversa da sessão: `X.json` ao lado de `X.estado.json` (cópia do bucket) ou `conversa.json` na pasta."""
    nome = estado.name
    candidatos = [estado.with_name(nome[: -len(".estado.json")] + ".json")] if nome.endswith(".estado.json") else []
    candidatos.append(estado.with_name("conversa.json"))
    return next((c for c in candidatos if c.exists() and c != estado), None)


def estados_em(caminhos: Iterable[Path]) -> List[Tuple[str, Path]]:
    saida = []
    for c in caminhos:
        if c.is_dir():
            if (c / "estado.json").exists():
                saida.append((c.name, c / "estado.json"))
            saida += [(p.name.split(".")[0], p) for p in sorted(c.glob("*.estado.json"))]
            saida += [(p.parent.name, p) for p in sorted(c.glob("*/estado.json"))]
        elif c.exists():
            saida.append((c.parent.name if c.name == "estado.json" else c.name.split(".")[0], c))
    return saida


def avaliar_arquivos(estados: Sequence[Tuple[str, Path]], conversas: bool = True) -> Dict[str, Dict[str, Any]]:
    resultados = {}
    for missao, caminho in estados:
        state = json.loads(caminho.read_text(encoding="utf-8"))
        conv = None
        if conversas:
            c = _conversa_ao_lado(caminho)
            conv = json.loads(c.read_text(encoding="utf-8")) if c else None
        resultados[missao] = avaliar(state, conv)
    return resultados


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Matriz de propagação (só leitura) sobre estados de sessão.")
    ap.add_argument("caminhos", nargs="+", type=Path, help="estado.json, X.estado.json ou pastas que os contenham")
    ap.add_argument("--sem-conversa", action="store_true", help="não ler a conversa ao lado do estado")
    ap.add_argument("--json", action="store_true", help="saída em JSON")
    ap.add_argument("--quadro", action="store_true", help="só o quadro somado")
    args = ap.parse_args(argv)
    resultados = avaliar_arquivos(estados_em(args.caminhos), conversas=not args.sem_conversa)
    if args.json:
        print(json.dumps({"quadro": quadro(resultados), "sessoes": resultados}, ensure_ascii=False, indent=2))
        return 0
    if not args.quadro:
        for m, r in resultados.items():
            print(relatorio(r, m))
    print(relatorio_quadro(quadro(resultados)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
