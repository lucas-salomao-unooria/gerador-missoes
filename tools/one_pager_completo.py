"""O one-pager de produto completo: o canônico com a missão contada em linguagem clara no topo (28/10/2026).

Até aqui Produto entregava dois documentos — o canônico de 18 seções e o resumido do A061 — e o time de negócio e de
produto não entendia o que a missão faz lendo nenhum dos dois: o canônico fala a língua dos gates (slot, gate, SVG,
determinístico), e o resumido repetia o canônico em outra ordem. O modelo que o time aprovou
(`Unooria_One_Page_Completo_Porta_Voz_dos_Dados.docx`) é um documento só: as seções do canônico, com duas seções novas
logo depois da identificação —

- `## 0.1 A ideia`: a missão inteira em prosa, do professor que libera ao fechamento, com os números exatos;
- `## 0.2 Como a missão funciona passo a passo`: um `### n. <o que acontece>` por passo, do preparo do professor ao
  fechamento com a turma, cada um num parágrafo curto que alguém de negócio lê sem glossário;

— e o brief de escopo no fim (`documento_para_exportar`). O redator (`prompts/produto/061_one_pager_completo.md`)
escreve só as duas seções; `encaixar` as põe no one-pager, e `validar` confere o que dá para conferir sem ler: as duas
seções existem com a forma certa, nenhum jargão da esteira, nenhum número que o resto do one-pager não tenha e nenhuma
fala entre aspas que não esteja, palavra por palavra, no resto do one-pager. O conteúdo já foi decidido e auditado nas
seções de baixo; estas duas só contam.
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

AGENTE = "one-pager-completo"

TITULO_IDEIA = "## 0.1 A ideia"
TITULO_PASSO_A_PASSO = "## 0.2 Como a missão funciona passo a passo"

#: Passos do 0.2: do preparo do professor ao fechamento. O modelo tem 13; menos de 7 não conta as 5 etapas com o
#: professor antes e depois, e mais de 16 deixa de ser leitura rápida.
MIN_PASSOS = 7
MAX_PASSOS = 16
#: Parágrafos do 0.1 e palavras por passo do 0.2: o modelo tem 6 parágrafos e passos de 40 a 60 palavras.
MIN_PARAGRAFOS_IDEIA = 3
#: Com os rótulos da ficha (Na tela, O estudante, Acontece, Se não fizer, Libera), uma frase cada já passa de 120.
MAX_PALAVRAS_PASSO = 150
#: Número até aqui é contagem do dia a dia («3 publicações», «passo 2»): não precisa estar no resto do one-pager.
MAIOR_NUMERO_LIVRE = 12
#: Fala entre aspas com pelo menos tantas palavras é texto de tela: tem de estar, igual, no resto do one-pager.
MIN_PALAVRAS_FALA = 4
#: Tamanho de frase calibrado no 0.2 do modelo (média 14,9, máximo 27). O 0.1 do modelo (média 21,6, máximo 36) e o
#: da exp09ef1b de 28/10 (média 29,6, máximo 72) são o que o time achou difícil (29/10/2026) — não são a régua.
MAX_PALAVRAS_FRASE = 30
MAX_MEDIA_FRASE = 18
MAX_PALAVRAS_IDEIA = 800
#: O 0.1 em seis parágrafos, cada um aberto pelo rótulo em negrito, na ordem, com o teto de palavras de cada um. A
#: cronologia pura do modelo deixava de fora o problema, a crença errada e o que o estudante aprende: «rasa».
BLOCOS_IDEIA: Tuple[Tuple[str, int], ...] = (
    ("Em uma frase", 45), ("A situação", 110), ("O que o estudante faz", 280),
    ("A virada", 140), ("O que o estudante aprende", 125), ("O papel do professor", 100),
)
#: Folga sobre o teto de cada bloco, para o verificador não brigar por uma palavra.
FOLGA_BLOCO = 1.2
#: Nomes genéricos distintos para o assistente/IA no 0.1 e no 0.2: mais que isso, o leitor acha que são personagens
#: diferentes («assistente», «máquina», «robô» e «inteligência artificial» na mesma saída).
MAX_NOMES_DA_MESMA_COISA = 2

_RE_IDEIA = re.compile(r"^#{2,3}\s*\**\s*0\.1\b[^\n]*$", re.M)
_RE_PASSO_A_PASSO = re.compile(r"^#{2,3}\s*\**\s*0\.2\b[^\n]*$", re.M)
_RE_H2_OU_H1 = re.compile(r"^#{1,2}\s+\S[^\n]*$", re.M)
_RE_SECAO_1 = re.compile(r"^##\s*\**\s*1\s*(?:\.(?!\d)|[—–-])[^\n]*$", re.M)
_RE_SECAO_0 = re.compile(r"^##\s*\**\s*0\s*(?:\.(?!\d)|[—–-])[^\n]*$", re.M)
_RE_PASSO = re.compile(r"^###\s*\**\s*(\d{1,2})\s*[.)—–-]\s*(.+?)\**\s*$", re.M)
_RE_NUMERO = re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)?(?![\w])")
_RE_FALA = re.compile(r"[\"“«]([^\"“”«»\n]{3,}?)[\"”»]")
_RE_ID_TELA = re.compile(r"\bE\d[-_](?:ALU|PROF|SIS)[-_]\d{2}", re.I)

#: Jargão da esteira e de engenharia que o time de negócio não lê. A tradução vai no relatório, para o redator.
JARGAO: Tuple[Tuple[str, str], ...] = (
    (r"\bgates?\b", "o momento em que a tela trava até o professor liberar"),
    (r"\blatch\b", "a escolha que não volta"),
    (r"\benums?\b", "as opções"),
    (r"\bflags?\b", "a marcação"),
    (r"\bslots?\b", "envios, vagas ou chances — o nome que o estudante vê"),
    (r"\bsvg\b", "o gráfico"),
    (r"\bjson\b", "os dados"),
    (r"\bpolling\b", "a tela do estudante espera o professor"),
    (r"\bpayload\b", "o que é enviado"),
    (r"\bendpoints?\b", "o sistema"),
    (r"\biframe\b", "a tela da missão"),
    (r"\bpostmessage\b", "o aviso que a missão manda à plataforma"),
    (r"\bhash\b", "a confirmação de que é a mesma planilha"),
    (r"\btrigger(?:ed)?\b", "o que dispara"),
    (r"\bdetermin[íi]stic[oa]s?\b", "que sempre responde do mesmo jeito"),
    (r"\brenderiza\w*", "mostra"),
    (r"\bparametriza\w*", "configura, escolhe"),
    (r"\bwireframes?\b", "o desenho da tela"),
    (r"\bfront-?end\b|\bback-?end\b", "a tela, o sistema"),
    (r"\bAPI\b", "o sistema"),
    (r"\bcanal [AB]\b", "o que mostra que ele aprendeu — a ação que ele faz na tela"),
    (r"\bcotas?\b", "envios, publicações, chances — o nome que o estudante vê"),
    (r"\bcontrato de evid[êe]ncia\b", "o que mostra que ele aprendeu"),
    (r"\bregra tern[áa]ria\b", "como a escolha dele mostra se aprendeu"),
    (r"\bpropicia\w*|\boportuniza\w*", "faz, deixa"),
    (r"\bmobiliza\w*", "usa, põe em jogo"),
    (r"\bressignifica\w*", "repensa"),
    (r"\bproblematiza\w*", "põe em dúvida"),
    (r"\bprotagonismo\b", "o estudante decide"),
    (r"\bmedia[çc][ãa]o docente\b", "o professor conduz"),
    (r"\bdiscentes?\b|\balunos?\b|\balunas?\b", "estudante"),
    (r"\bjob[- ]to[- ]be[- ]done\b", "o que o personagem pede"),
    (r"\bcardinalidade\b", "o número exato"),
    (r"\bdieg[ée]tic[oa]s?\b", "dentro da história"),
    (r"\baffordances?\b", "o que dá para fazer na tela"),
    (r"\bP0[ab]\b", "o que a frase quer dizer, sem o nome interno da etapa"),
    (r"\bRegra \d+\b", "o que a regra garante, sem o número dela"),
    (r"§\s*\d", "o nome da seção, sem o número"),
)

#: Palavra de relatório: português correto, mas não é como se conta a missão numa reunião com o comercial. Sementes
#: tiradas do 0.1 e do 0.2 da exp09ef1b (28/10/2026), que o time achou difíceis.
PALAVRAS_DIFICEIS: Tuple[Tuple[str, str], ...] = (
    (r"\bleitura [óo]ptica\b|\bOCR\b", "o sistema lê as páginas fotografadas"),
    (r"\bformativ[oa]s?\b", "o que o professor vê de cada estudante, em coisas concretas"),
    (r"\bdeliber\w+", "decidir, decisão"),
    (r"\bor[çc]ament[áa]ri[oa]s?\b", "do dinheiro, da verba"),
    (r"\bsistematiz\w+|\bformaliz\w+", "resume, dá nome"),
    (r"\bsubmet\w+", "envia"),
    (r"\bemit[ei]\w*", "dá, mostra, escreve"),
    (r"\bm[óo]dulos?\b", "parte, caso extra"),
    (r"\bplen[áa]ri[oa]s?\b", "com a turma toda"),
    (r"\bmedia[çc][ãa]o\b|\bmedeia\b", "o professor conduz a conversa"),
    (r"\bdocumental\b", "ter os papéis em dia"),
    (r"\bassimetri\w+", "um lado tem mais do que o outro"),
    (r"\bperante\b", "diante de"),
    (r"\bdecorr\w+", "acontece por causa de"),
    (r"\bartefatos?\b", "o gráfico ou o texto que ele faz"),
    (r"\bestruturad[oa]s?\b", "guiado, com opções prontas"),
    (r"\bcontextualiz\w+", "explica o contexto"),
    (r"\bfuncionalidades?\b", "o que dá pra fazer"),
    (r"\binteragir\b|\binterage\b", "a ação concreta: toca, arrasta, escreve"),
)
#: Nomes genéricos da mesma coisa — o assistente da história. «IA» só em maiúsculas: «ia» é verbo.
NOMES_DO_ASSISTENTE: Tuple[Tuple[str, int], ...] = (
    (r"\brob[ôo]s?\b", re.I), (r"\bm[áa]quinas?\b", re.I), (r"\bintelig[êe]ncia artificial\b", re.I),
    (r"\bIA\b", 0), (r"\bbots?\b", re.I), (r"\balgoritmos?\b", re.I), (r"\bassistente\b", re.I),
)
#: Número por extenso acima da contagem do dia a dia: o redator escrevia «vinte e quatro vagas», «doze mil reais» e
#: «cento e oitenta páginas» e escapava da conferência dos números, que lê dígitos (exp09ef1b ao vivo, 30/10/2026).
_RE_NUMERO_POR_EXTENSO = re.compile(r"\b(?:treze|quatorze|catorze|quinze|dezesseis|dezessete|dezoito|dezenove|vinte|"
                                    r"trinta|quarenta|cinquenta|sessenta|setenta|oitenta|noventa|cem|cento|duzent[oa]s|"
                                    r"trezent[oa]s|quatrocent[oa]s|quinhent[oa]s|mil|milh[ãõ]o|milh[õo]es)\b", re.I)
_RE_FUTURO = re.compile(r"\b(?:dever[áã]o?|ser[áã]o? capaz(?:es)?|poder[áã]o? ser)\b", re.I)
_RE_CRENCA = re.compile(r"\b(?:acha|acham|achava|achavam|acredita|acreditam|acreditava|parece|parecia|imagina|"
                        r"aposta|apostam|pensa|pensam|pensava)\b", re.I)
_RE_ROTULO = re.compile(r"^\s*\*\*([^*\n]+?)\.?\*\*", re.M)


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKC", texto or "").casefold()
    texto = re.sub(r"[\"“”«»'‘’*_`]", "", texto)
    return re.sub(r"\s+", " ", texto).strip(" .,;:!?…—–-")


def _bloco(texto: str, titulo: "re.Pattern[str]") -> Optional[Tuple[int, int]]:
    """Início e fim do bloco que começa no título: vai até o próximo título `#` ou `##`."""
    m = titulo.search(texto or "")
    if not m:
        return None
    prox = _RE_H2_OU_H1.search(texto, m.end())
    return m.start(), prox.start() if prox else len(texto)


def secoes(texto: str) -> Tuple[str, str]:
    """O corpo do 0.1 e o do 0.2, sem o título; "" para o que falta."""
    corpos = []
    for titulo in (_RE_IDEIA, _RE_PASSO_A_PASSO):
        achado = _bloco(texto, titulo)
        bloco = texto[achado[0]:achado[1]] if achado else ""
        corpos.append(bloco.split("\n", 1)[1].strip() if "\n" in bloco else "")
    return corpos[0], corpos[1]


def leitura_do_redator(saida: str) -> str:
    """As duas seções que o redator entregou, com os títulos fixos, sem preâmbulo nem envelope."""
    from pipeline.artifacts import sem_envelope_do_agente

    texto = str(sem_envelope_do_agente(saida or "") or "")
    texto = re.sub(r"^```(?:markdown|md)?\s*\n|\n```\s*$", "", texto.strip())
    ideia, passos = secoes(texto)
    partes = []
    if ideia:
        partes.append(f"{TITULO_IDEIA}\n\n{ideia}")
    if passos:
        partes.append(f"{TITULO_PASSO_A_PASSO}\n\n{passos}")
    return "\n\n".join(partes)


def sem_leitura(one_pager: str) -> str:
    """O one-pager sem o 0.1 e o 0.2 — o resto, que é a fonte de toda conferência."""
    texto = one_pager or ""
    for titulo in (_RE_IDEIA, _RE_PASSO_A_PASSO):
        achado = _bloco(texto, titulo)
        if achado:
            ini, fim = achado
            texto = texto[:ini].rstrip() + "\n\n" + texto[fim:].lstrip()
    return texto.strip() + "\n"


def encaixar(one_pager: str, leitura: str) -> str:
    """O one-pager com o 0.1 e o 0.2 de `leitura` logo antes da seção 1 (no lugar dos que havia).

    Sem seção 1, entram depois da seção 0; sem as duas, depois do título do documento. Leitura vazia não mexe em nada.
    """
    if not (leitura or "").strip() or not (one_pager or "").strip():
        return one_pager
    base = sem_leitura(one_pager)
    m = _RE_SECAO_1.search(base)
    if m:
        pos = m.start()
    else:
        s0 = _RE_SECAO_0.search(base)
        prox = _RE_H2_OU_H1.search(base, s0.end()) if s0 else None
        if s0:
            pos = prox.start() if prox else len(base)
        else:
            h1 = re.search(r"^#\s+[^\n]*\n", base, re.M)
            pos = h1.end() if h1 else 0
    return base[:pos].rstrip() + "\n\n" + leitura.strip() + "\n\n" + base[pos:].lstrip()


def _achado(codigo: str, resumo: str, severidade: str = "bloqueio") -> Dict[str, str]:
    return {"codigo": codigo, "resumo": resumo, "severidade": severidade, "etapa": "produto",
            "agente_responsavel": AGENTE}


def _paragrafos(corpo: str) -> List[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", corpo or "") if p.strip()]


def _numeros(texto: str) -> set:
    return {n.replace(",", ".") for n in _RE_NUMERO.findall(texto or "")}


def _sem_titulos_de_passo(corpo: str) -> str:
    return _RE_PASSO.sub("", corpo or "")


def _sem_falas(texto: str) -> str:
    """Cada fala entre aspas vira uma palavra só: texto de tela copiado não conta como frase longa nem palavra difícil."""
    # o ponto final de dentro da fala fecha a frase de fora («… conselheiro.” Três cartões…», exp09ef1b ao vivo)
    return _RE_FALA.sub(lambda m: "«fala»" + ("." if m.group(1).rstrip()[-1:] in ".!?…" else ""), texto or "")


def _frases(texto: str) -> List[str]:
    """As frases do texto, sem rótulos em negrito, sem títulos de passo e com cada fala valendo uma palavra."""
    corpo = _sem_falas(_sem_titulos_de_passo(texto))
    corpo = _RE_ROTULO.sub("", corpo)
    corpo = re.sub(r"[*_`]", "", corpo)
    pedacos = re.split(r"(?<=[.!?…])\s+(?=[A-ZÁÂÃÉÊÍÓÔÕÚÇ«\"“(])|\n", corpo)
    return [p.strip() for p in pedacos if len(p.split()) >= 2]


def _blocos_da_ideia(ideia: str) -> List[Tuple[str, str]]:
    """Os parágrafos do 0.1 abertos por rótulo em negrito: (rótulo, texto), na ordem em que aparecem."""
    blocos = []
    for p in _paragrafos(ideia):
        m = _RE_ROTULO.match(p)
        if m:
            blocos.append((m.group(1).strip().rstrip(".:").strip(), p[m.end():].strip()))
    return blocos


def _linguagem(nome: str, texto: str) -> List[Dict[str, str]]:
    """L1 (frase curta), L3 (presente), L6b (palavra de relatório) e L7 (um termo por frase) numa seção."""
    achados: List[Dict[str, str]] = []
    frases = _frases(texto)
    for f in frases:
        n = len(f.split())
        if n > MAX_PALAVRAS_FRASE:
            achados.append(_achado("frase-longa", f"Frase de {n} palavras no {nome} («{f[:90]}…»): divida em duas ou "
                                                  f"mais, com até {MAX_PALAVRAS_FRASE} palavras cada.", "atencao"))
        if f.count("—") >= 3:
            achados.append(_achado("conceitos-numa-frase", f"Frase com mais de um termo traduzido no {nome} "
                                                           f"(«{f[:90]}…»): dê uma frase a cada termo.", "atencao"))
    if frases:
        media = sum(len(f.split()) for f in frases) / len(frases)
        if media > MAX_MEDIA_FRASE:
            achados.append(_achado("frases-longas-em-media", f"As frases do {nome} têm em média {media:.1f} palavras; "
                                                             f"o teto é {MAX_MEDIA_FRASE}. Uma ideia por frase.",
                                   "atencao"))
    sem_falas = _sem_falas(_sem_titulos_de_passo(texto))
    vistos = set()
    for padrao, troca in PALAVRAS_DIFICEIS:
        for m in re.finditer(padrao, sem_falas, re.I):
            termo = m.group(0)
            if termo.casefold() in vistos:
                continue
            vistos.add(termo.casefold())
            achados.append(_achado("palavra-dificil", f"«{termo}» no {nome}: é palavra de relatório. Escreva {troca}."))
    extenso = [m.group(0) for m in _RE_NUMERO_POR_EXTENSO.finditer(sem_falas)]
    if extenso:
        achados.append(_achado("numero-por-extenso", f"Número escrito por extenso no {nome} («{extenso[0]}»…): escreva "
                                                     "o número com algarismos, igual ao do resto do one-pager — "
                                                     "«24 vagas», «R$ 12.000», «180 registros»."))
    for m in _RE_FUTURO.finditer(sem_falas):
        achados.append(_achado("futuro-ou-condicional", f"«{m.group(0)}» no {nome}: conte no presente — «o estudante "
                                                        "escolhe», «a tela trava»."))
    return achados


def _forma_da_ideia(ideia: str) -> List[Dict[str, str]]:
    """O 0.1 com os seis rótulos, na ordem, cada bloco no seu tamanho, e a virada dizendo o que se achava antes."""
    achados: List[Dict[str, str]] = []
    palavras = len(_sem_falas(ideia).split())
    if palavras > MAX_PALAVRAS_IDEIA:
        achados.append(_achado("ideia-longa", f"O 0.1 tem {palavras} palavras; cabe em até {MAX_PALAVRAS_IDEIA}. "
                                              "Corte explicação, nunca a ação do estudante.", "atencao"))
    blocos = _blocos_da_ideia(ideia)
    achados_por_rotulo = {_normalizar(r): t for r, t in blocos}
    esperados = [_normalizar(r) for r, _ in BLOCOS_IDEIA]
    faltam = [r for r, _ in BLOCOS_IDEIA if _normalizar(r) not in achados_por_rotulo]
    if faltam:
        achados.append(_achado("ideia-sem-bloco", "O 0.1 abre cada parágrafo com o rótulo em negrito, na ordem: "
                               + ", ".join(f"«**{r}.**»" for r, _ in BLOCOS_IDEIA) + ". Faltam: "
                               + ", ".join(f"«{r}»" for r in faltam) + "."))
    else:
        ordem = [_normalizar(r) for r, _ in blocos if _normalizar(r) in esperados]
        if ordem != esperados:
            achados.append(_achado("ideia-sem-bloco", "Os blocos do 0.1 vão nesta ordem: "
                                   + " → ".join(r for r, _ in BLOCOS_IDEIA) + "."))
    for rotulo, teto in BLOCOS_IDEIA:
        texto = achados_por_rotulo.get(_normalizar(rotulo))
        if texto is None:
            continue
        n = len(_sem_falas(texto).split())
        if n > teto * FOLGA_BLOCO:
            achados.append(_achado("bloco-longo", f"O bloco «{rotulo}» do 0.1 tem {n} palavras; cabe em até {teto}.",
                                   "atencao"))
    virada = achados_por_rotulo.get(_normalizar("A virada"))
    if virada is not None and not _RE_CRENCA.search(_sem_falas(virada)):
        achados.append(_achado("virada-sem-crenca", "O bloco «A virada» não diz o que o estudante achava antes. "
                                                    "Comece pela crença de entrada da seção 1.2, com «acha», "
                                                    "«acredita» ou «parece»."))
    return achados


_RE_LINHA_MOMENTO = re.compile(r"^\s*[*_]?[^*\n]*\bmomentos?\s+([^*\n]+?)[*_]?\s*$", re.M | re.I)
_RE_ID_MOMENTO = re.compile(r"\b(\d\.\d{1,2}[a-z]?)\b")
_RE_ROTULO_PASSO = re.compile(r"^\s*(?:[-*•]\s+)?\*\*\s*(S[óo] para quem|Na tela|O estudante|O professor|Acontece|"
                              r"Se n[ãa]o fizer|Libera)\s*:?\s*\*\*\s*:?\s*(.*)$", re.M | re.I)


def _ordem_do_momento(ident: str) -> Tuple[int, int]:
    """«3.2» → (3, 2); a letra do caminho não conta: 2.2a e 2.2b vêm em qualquer ordem entre si."""
    etapa, k = re.match(r"(\d)\.(\d{1,2})", ident).groups()
    return int(etapa), int(k)


def _passos_e_campos(passos: str) -> List[Dict[str, Any]]:
    titulos = list(_RE_PASSO.finditer(passos or ""))
    lista = []
    for i, t in enumerate(titulos):
        fim = titulos[i + 1].start() if i + 1 < len(titulos) else len(passos)
        corpo = passos[t.end():fim]
        linha = _RE_LINHA_MOMENTO.search(corpo)
        campos = {}
        for c in _RE_ROTULO_PASSO.finditer(corpo):
            campos.setdefault(_normalizar(c.group(1)), c.group(2).strip())
        lista.append({"n": t.group(1), "titulo": t.group(2).strip(), "corpo": corpo, "campos": campos,
                      "momentos": [m.lower() for m in _RE_ID_MOMENTO.findall(linha.group(1))] if linha else []})
    return lista


def _passos_contra_a_ficha(passos: str, resto: str) -> List[Dict[str, str]]:
    """O 0.2 contra as fichas da seção 4: campos de cada passo, um momento por passo, na ordem, sem ação repetida."""
    from tools import ficha_interacao as fi

    achados: List[Dict[str, str]] = []
    lista = _passos_e_campos(passos)
    meio = lista[1:-1] if len(lista) > 2 else []
    for p in meio:
        faltam = [r for r, chaves in (("Na tela", ("na tela",)), ("O estudante/O professor", ("o estudante",
                                                                                                "o professor")),
                                      ("Acontece", ("acontece",)), ("Libera", ("libera",)))
                  if not any(k in p["campos"] for k in chaves)]
        if faltam:
            achados.append(_achado("passo-sem-campos", f"O passo {p['n']} não tem " + ", ".join(f"**{f}:**"
                                   for f in faltam) + ": cada passo diz o que aparece, o que a pessoa faz, o que "
                                   "acontece e o que abre o passo seguinte."))
        if "o estudante" in p["campos"] and "se não fizer" not in p["campos"]:
            achados.append(_achado("passo-sem-se-nao-fizer", f"O passo {p['n']} é do estudante e não diz **Se não "
                                                             "fizer:** — o que a tela faz enquanto ele não age."))
    # o mesmo botão na ação de dois passos só é caminho diferente se os dois disserem para quem
    def caminho(p: Dict[str, Any]) -> bool:
        return "só para quem" in p["campos"]

    vistos: Dict[str, Dict[str, Any]] = {}
    for p in lista:
        for botao in _RE_FALA.findall(p["campos"].get("o estudante", "")):
            chave = _normalizar(botao)
            antes = vistos.get(chave)
            if antes and not (caminho(antes) and caminho(p)):
                achados.append(_achado("acao-repetida", f"O estudante toca em «{botao}» no passo {antes['n']} e no "
                                                        f"passo {p['n']}: ou é o mesmo momento (junte), ou são "
                                                        "caminhos diferentes (os dois dizem **Só para quem:**)."))
            vistos.setdefault(chave, p)

    momentos = fi.extrair(resto)
    if not momentos:
        return achados
    ids = [m.id for m in momentos]
    ramos = {m.id for m in momentos if m.ramo}
    contados: Dict[str, str] = {}
    sequencia: List[str] = []
    for p in meio:
        if not p["momentos"]:
            achados.append(_achado("passo-sem-momento", f"O passo {p['n']} não diz que momento da seção 4 conta: "
                                                        "linha `*<Etapa> · momento E.k*` logo abaixo do título."))
            continue
        letras = {m[-1] for m in p["momentos"] if m in ramos}
        if letras and "só para quem" not in p["campos"]:
            achados.append(_achado("ramo-sem-condicao", f"O passo {p['n']} conta um caminho de parte da turma e não diz "
                                                        "**Só para quem:**."))
        if len(letras) > 1:
            achados.append(_achado("ramo-sem-condicao", f"O passo {p['n']} junta caminhos diferentes "
                                                        f"({', '.join(p['momentos'])}): um passo por caminho."))
        for m in p["momentos"]:
            if m not in ids:
                achados.append(_achado("momento-inexistente", f"O passo {p['n']} cita o momento {m}, que a seção 4 "
                                                              "não tem."))
            elif m in contados:
                achados.append(_achado("momento-contado-duas-vezes", f"O momento {m} está nos passos {contados[m]} "
                                                                     f"e {p['n']}: um momento, um passo."))
            else:
                contados[m] = p["n"]
                sequencia.append(m)
    for m in ids:
        if m not in contados:
            achados.append(_achado("momento-nao-contado", f"O momento {m} da seção 4 não está em nenhum passo do 0.2."))
    ordem = [_ordem_do_momento(m) for m in sequencia]
    if any(b < a for a, b in zip(ordem, ordem[1:])):
        achados.append(_achado("passos-fora-da-ordem-da-missao", "Os passos do 0.2 contam os momentos fora da ordem "
                                                                 "da seção 4: " + " → ".join(sequencia) + "."))
    return achados


def _nomes_do_assistente(texto: str) -> List[str]:
    sem_falas = _sem_falas(_sem_titulos_de_passo(texto))
    return [re.search(p, sem_falas, f).group(0) for p, f in NOMES_DO_ASSISTENTE if re.search(p, sem_falas, f)]


def validar(one_pager: str) -> Dict[str, Any]:
    """O 0.1 e o 0.2 do one-pager: forma, linguagem e fidelidade ao resto do one-pager."""
    ideia, passos = secoes(one_pager)
    resto = sem_leitura(one_pager)
    achados: List[Dict[str, str]] = []

    if not ideia:
        achados.append(_achado("ideia-ausente", f"Falta a seção `{TITULO_IDEIA}`: a missão inteira em prosa."))
    else:
        if re.search(r"^\s*(?:[-*•]|\d+[.)])\s+|^\s*\|", ideia, re.M):
            achados.append(_achado("ideia-com-lista", "O 0.1 é prosa: tire os bullets, a lista numerada ou a tabela."))
        if len(_paragrafos(ideia)) < MIN_PARAGRAFOS_IDEIA:
            achados.append(_achado("ideia-curta", f"O 0.1 conta a missão inteira em pelo menos {MIN_PARAGRAFOS_IDEIA} "
                                                  "parágrafos, do professor que libera ao fechamento."))
        achados += _forma_da_ideia(ideia)
        achados += _linguagem("0.1", ideia)
    if passos:
        achados += _linguagem("0.2", passos)
        achados += _passos_contra_a_ficha(passos, resto)
    nomes = _nomes_do_assistente(f"{ideia}\n\n{passos}")
    if len(nomes) > MAX_NOMES_DA_MESMA_COISA:
        achados.append(_achado("um-nome-por-coisa", "O assistente da história aparece como " + ", ".join(
            f"«{n}»" for n in nomes) + ": use um nome só, o mesmo do one-pager, do começo ao fim."))
    contagem = 0
    if not passos:
        achados.append(_achado("passo-a-passo-ausente", f"Falta a seção `{TITULO_PASSO_A_PASSO}`."))
    else:
        titulos = list(_RE_PASSO.finditer(passos))
        contagem = len(titulos)
        numeros = [int(t.group(1)) for t in titulos]
        if not MIN_PASSOS <= contagem <= MAX_PASSOS:
            achados.append(_achado("passos-fora-da-faixa", f"O 0.2 tem {contagem} passo(s) `### n. …`; são de "
                                                           f"{MIN_PASSOS} a {MAX_PASSOS}, do preparo do professor ao "
                                                           "fechamento com a turma."))
        if numeros and numeros != list(range(1, contagem + 1)):
            achados.append(_achado("passos-fora-de-ordem", "Os passos do 0.2 vão numerados de 1 em diante, sem pular."))
        if titulos:
            fim_1 = titulos[1].start() if len(titulos) > 1 else len(passos)
            if "professor" not in _normalizar(passos[titulos[0].start():fim_1]):
                achados.append(_achado("primeiro-passo-sem-professor", "O passo 1 é o professor preparando e "
                                                                       "liberando a atividade.", "atencao"))
        for i, t in enumerate(titulos):
            fim = titulos[i + 1].start() if i + 1 < len(titulos) else len(passos)
            palavras = len(passos[t.end():fim].split())
            if not palavras:
                achados.append(_achado("passo-vazio", f"O passo {t.group(1)} («{t.group(2).strip()}») está sem texto."))
            elif palavras > MAX_PALAVRAS_PASSO:
                achados.append(_achado("passo-longo", f"O passo {t.group(1)} tem {palavras} palavras; cabe em até "
                                                      f"{MAX_PALAVRAS_PASSO}. Corte explicação, não fato.", "atencao"))

    leitura = f"{ideia}\n\n{_sem_titulos_de_passo(passos)}"
    vistos = set()
    for padrao, traducao in JARGAO:
        for m in re.finditer(padrao, leitura, re.I):
            termo = m.group(0)
            if termo.casefold() in vistos:
                continue
            vistos.add(termo.casefold())
            achados.append(_achado("jargao", f"«{termo}» no 0.1/0.2: quem lê é o time de negócio. Escreva "
                                             f"{traducao}."))
    for m in _RE_ID_TELA.finditer(leitura):
        achados.append(_achado("id-de-tela", f"«{m.group(0)}» no 0.1/0.2: diga o que a tela mostra, em palavras."))

    for n in sorted(_numeros(leitura) - _numeros(resto)):
        if "." in n or float(n) > MAIOR_NUMERO_LIVRE:
            achados.append(_achado("numero-sem-origem", f"O número {n} do 0.1/0.2 não aparece no resto do one-pager: "
                                                        "copie o número de lá, ou tire-o."))

    resto_normalizado = _normalizar(resto)
    for m in _RE_FALA.finditer(leitura):
        fala = _normalizar(m.group(1))
        if len(fala.split()) >= MIN_PALAVRAS_FALA and fala not in resto_normalizado:
            from tools import classificador

            ini_f = max(0, leitura.rfind("\n", 0, m.start()) + 1)
            fim_f = leitura.find("\n", m.end())
            linha_f = leitura[ini_f:len(leitura) if fim_f < 0 else fim_f].strip()
            leitura_cls = classificador.aspas_conceito_ou_fala(linha_f, m.group(1).strip())
            sev_fala = "atencao" if leitura_cls.rotulo in ("termo_ou_conceito", "termo_conceito") else "bloqueio"
            achados.append(_achado("fala-reescrita", f"A fala «{m.group(1).strip()[:120]}» não está, palavra por "
                                                     "palavra, no resto do one-pager: copie o texto da tela ou tire "
                                                     "as aspas e conte com as suas palavras.", sev_fala))

    bloqueia = any(a["severidade"] == "bloqueio" for a in achados)
    status = "bloqueado" if bloqueia else ("amarelo" if achados else "aprovado")
    return {"status": status, "achados": achados, "passos": contagem,
            "palavras": len(f"{ideia} {_sem_titulos_de_passo(passos)}".split())}


def relatorio(resultado: Dict[str, Any], missao: str = "") -> str:
    icone = {"aprovado": "🟢 PRONTO PARA LEITURA", "amarelo": "🟡 COM RESSALVAS",
             "bloqueado": "🔴 VOLTA AO REDATOR"}[resultado["status"]]
    linhas = [f"# Leitura clara do one-pager (0.1 e 0.2) — {missao or 'missão'}", "", f"**Veredito: {icone}**", "",
              f"Passos no 0.2: {resultado.get('passos', 0)} · palavras no 0.1 e no 0.2: {resultado.get('palavras', 0)}",
              ""]
    if resultado["achados"]:
        linhas += ["## Achados", ""]
        for a in resultado["achados"]:
            marca = "❌" if a["severidade"] == "bloqueio" else "⚠️"
            linhas.append(f"- {marca} **{a['codigo']}** — {a['resumo']}")
    else:
        linhas.append("Nenhum achado: as duas seções existem, sem jargão, com números e falas do resto do one-pager.")
    linhas += ["", "```json", json.dumps(
        {"agente": AGENTE, "missao": missao, "status": resultado["status"], "achados": resultado["achados"]},
        ensure_ascii=False, indent=2), "```"]
    return "\n".join(linhas)


def documento_para_exportar(state: Dict[str, Any]) -> Any:
    """O one-pager como o time o lê: o canônico (com o 0.1 e o 0.2) e, no fim, o brief de escopo.

    O A023 separa o brief do one-pager antes do revisor (`agents.produto.get_brief_escopo_split`), e ele ficava só em
    `produto/00f-brief-escopo.md`. O modelo do time traz os dois num documento só.
    """
    one_pager = state.get("one_pager")
    if not isinstance(one_pager, str) or not one_pager.strip():
        return one_pager
    brief = state.get("brief_escopo")
    if not isinstance(brief, str) or not brief.strip() or _normalizar(brief[:200]) in _normalizar(one_pager):
        return one_pager
    return one_pager.rstrip() + "\n\n---\n\n" + brief.strip() + "\n"
