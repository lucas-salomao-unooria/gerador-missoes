"""Coerência entre documentos: o glossário canônico da spec, conferido em código.

Na missão do 9º ano (exp09ef1b, 06/10/2026) o mesmo órgão saiu da esteira com quatro nomes:
"Conselho Municipal de Apoio Social" na spec, "Conselho Municipal de Recursos" na copy e no PRD,
"Comissão Municipal de Recursos Comunitários" no handoff e "Comissão de Recursos Comunitários" no
núcleo e no brief de assets. João, Ana e Luana, beneficiários de 14 anos no briefing, viraram
"Coordenação: João" nos cards da copy. O Mesa Aberta abria "24 novas vagas em 2 dias por semana" no
one-pager e tinha "180 dias de assinaturas" alguns parágrafos depois. Seis ações tinham dois rótulos
de botão diferentes entre jornada, fluxo e copy ("Usar banco padrão" × "Usar Banco Padrão Oficial").
Cada documento, lido sozinho, estava bem escrito; nenhum agente lia os cinco juntos, e nenhum tinha
uma lista do que é canônico.

Agora a spec traz o bloco `## Glossário canônico` (`prompts/produto/13_spec_missao.md`) e este módulo
confere os documentos a jusante contra ele:

- variante proibida de uma entidade = **bloqueio** (é o mesmo órgão com outro nome na tela);
- personagem perto de "coordena/responsável" quando o papel canônico é outro = atenção;
- número do glossário com outro valor, junto da mesma unidade e da mesma entidade = atenção;
- rótulo de botão citado entre aspas/crases, diferente do canônico da mesma ação = atenção;
- arquivo citado com nome parecido com o canônico, mas diferente = atenção;
- spec sem glossário = atenção (`glossario-ausente`).

E, para o modelo de dados (`conferir_colunas`): coluna citada que o DDL do próprio documento não
declara = atenção (`exp09ef1b_sessoes.projeto_homologado` no bloco 9 da spec); a mesma coluna com
dois tipos = **bloqueio** (`escola_id UUID` no DDL da spec, `escola_id TEXT` no PRD).

As heurísticas são estreitas de propósito: atenção vira leitura humana, e um verificador que acusa
o que não existe deixa de ser lido.
"""
from __future__ import annotations

import html as _html
import json
import re
import unicodedata
from typing import Any, Dict, List, Optional, Set, Tuple

AGENTE = "consistencia-check"

#: Dono de cada documento conferido no design — é quem o QA manda reescrever.
DONOS = {
    "jornada": "jornada",
    "fluxo": "fluxo",
    "copy revisada": "copy-ptbr-revisao",
    "protótipo": "prototipo",
    "PRD": "prd-writer",
    "banco de conteúdo": "banco-conteudo",
    "brief de assets": "brief-assets",
}

_RE_SECAO_GLOSSARIO = re.compile(
    r"^#{1,3}\s*(?:\d+[a-z]?\.?\s*)?Gloss[áa]rio\s+can[ôo]nico\b[^\n]*$(.*?)(?=^#{1,2}\s|\Z)", re.M | re.S | re.I)
_RE_PAPEL_DE_GESTAO = re.compile(r"\bcoordena\w*|\brespons[áa]ve(?:l|is)\b", re.I)
_RE_ROTULO_CONTEXTO = re.compile(r"bot[ãa]o|\bcta\b|clica|clique|\btoca\b|\btoque\b|r[óo]tulo|\bbutton\b|\blabel\b", re.I)
#: A chave de string de um botão na tabela de copy: `e0.rotulo.botao_configurar`, `e2.cta.enviar`.
_RE_CHAVE_DE_BOTAO = re.compile(r"\b\w+\.\w+\.\w*(?:bot[aã]o|cta)\w*|\b\w+\.(?:bot[aã]o|cta)\.\w+", re.I)
_RE_ENTRE_ASPAS = re.compile(r"[“\"«`]([^”\"»`\n]{2,60})[”\"»`]")
_RE_ARQUIVO = re.compile(r"(?<![\w/.-])((?:[\w-]+/)*[\w.-]+\.(?:html|md|docx|pdf|json|csv))\b")
_PALAVRAS_VAZIAS = frozenset("a o as os de da do das dos e em para com por um uma no na nos nas ao aos à às".split())
_NUMEROS_POR_EXTENSO = {
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6, "sete": 7,
    "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12, "quinze": 15, "vinte": 20, "trinta": 30,
}


# ------------------------------------------------------------------ texto
def _dobrar(texto: str) -> str:
    """Minúsculas sem acento, **com o mesmo comprimento**: as posições valem no texto original."""
    return "".join((unicodedata.normalize("NFD", c)[:1].lower() or c)[:1] for c in (texto or ""))


def _norm(texto: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[`*_]", " ", _dobrar(texto))).strip(" .:")


def _limpa(celula: str) -> str:
    return re.sub(r"^[\s`*“\"«']+|[\s`*”\"»'.]+$", "", celula or "").strip()


def _palavras(texto: str) -> Set[str]:
    return {p for p in re.findall(r"[a-z0-9]+", _dobrar(texto)) if p not in _PALAVRAS_VAZIAS and len(p) >= 2}


def _numero(texto: str) -> Optional[float]:
    from tools.mecanica import _numero as num

    bruto = _dobrar(texto or "").strip()
    if bruto in _NUMEROS_POR_EXTENSO:
        return float(_NUMEROS_POR_EXTENSO[bruto])
    return num(texto)


def _padrao_nome(nome: str) -> str:
    return r"(?<![a-z0-9])" + r"\s+".join(re.escape(p) for p in _dobrar(nome).split()) + r"(?![a-z0-9])"


def _linha_de(texto: str, pos: int, largura: int = 180) -> str:
    ini = texto.rfind("\n", 0, pos) + 1
    fim = texto.find("\n", pos)
    linha = texto[ini: fim if fim >= 0 else len(texto)]
    rel = pos - ini
    if len(linha) > largura:
        a = max(0, rel - largura // 2)
        linha = ("…" if a else "") + linha[a: a + largura] + "…"
    return linha.strip().replace("`", "'")


def texto_de_html(documento: str) -> str:
    """O texto que a pessoa lê no protótipo: sem script, estilo e marcação."""
    sem = re.sub(r"<(script|style)\b.*?</\1>", " ", documento or "", flags=re.S | re.I)
    sem = re.sub(r"<br\s*/?>|</(?:p|div|li|h\d|tr|section|button)>", "\n", sem, flags=re.I)
    return _html.unescape(re.sub(r"<[^>]+>", " ", sem))


def _tabelas(bloco: str) -> List[List[List[str]]]:
    """Tabelas Markdown do bloco, cada uma como lista de linhas (cabeçalho primeiro)."""
    tabelas: List[List[List[str]]] = []
    atual: List[List[str]] = []
    for linha in (bloco or "").splitlines() + [""]:
        s = linha.strip()
        if s.startswith("|"):
            if not re.fullmatch(r"\|[\s:|-]+\|?", s):
                atual.append([c.strip() for c in s.strip("|").split("|")])
            continue
        if atual:
            tabelas.append(atual)
            atual = []
    return tabelas


# ------------------------------------------------------------------ glossário
def _variantes(celula: str) -> List[str]:
    entre_aspas = re.findall(r"[“\"«`]([^”\"»`]+)[”\"»`]", celula or "")
    brutas = entre_aspas or re.split(r"\s*(?:;|·|,|<br\s*/?>|\s/\s)\s*", celula or "")
    return [v for v in (_limpa(b) for b in brutas) if v and _norm(v) not in ("", "-", "—", "nenhuma", "nenhum")]


def extrair_glossario(spec: str) -> Optional[Dict[str, List[Dict[str, Any]]]]:
    """As cinco tabelas do `## Glossário canônico`, ou None quando a spec não o traz.

    Cada tabela é reconhecida pelo cabeçalho, não pela ordem nem pelo subtítulo: o autor é um modelo
    e a ordem das seções é a primeira coisa que ele muda.
    """
    m = _RE_SECAO_GLOSSARIO.search(spec or "")
    if not m:
        return None
    g: Dict[str, List[Dict[str, Any]]] = {"entidades": [], "personagens": [], "numeros": [], "rotulos": [], "arquivos": []}
    for tabela in _tabelas(m.group(1)):
        cab = [_norm(c) for c in tabela[0]]

        def col(*nomes: str) -> Optional[int]:
            return next((i for i, c in enumerate(cab) if any(n in c for n in nomes)), None)

        def cel(linha: List[str], i: Optional[int]) -> str:
            return _limpa(linha[i]) if i is not None and i < len(linha) else ""

        linhas = tabela[1:]
        if col("valor") is not None and col("unidade") is not None:  # antes de "idade": "unidade" contém "idade"
            i_oque = col("o que", "o quê", "item", "grandeza")
            i_oque = 0 if i_oque is None else i_oque
            g["numeros"] += [{"oque": cel(l, i_oque), "valor": _numero(cel(l, col("valor"))), "bruto": cel(l, col("valor")),
                              "unidade": cel(l, col("unidade"))} for l in linhas if cel(l, i_oque)]
        elif col("variante") is not None:
            i_nome, i_var = col("canonico", "nome", "entidade") or 0, col("variante")
            g["entidades"] += [{"nome": cel(l, i_nome), "variantes": _variantes(l[i_var] if i_var < len(l) else "")}
                               for l in linhas if cel(l, i_nome)]
        elif col("idade") is not None:
            i_nome, i_idade, i_papel = col("nome", "personagem") or 0, col("idade"), col("papel")
            g["personagens"] += [{"nome": cel(l, i_nome), "idade": _numero(cel(l, i_idade)), "papel": cel(l, i_papel)}
                                 for l in linhas if cel(l, i_nome)]
        elif col("rotulo") is not None:
            i_acao = col("acao")
            i_acao = 0 if i_acao is None else i_acao
            g["rotulos"] += [{"acao": cel(l, i_acao), "rotulo": cel(l, col("rotulo"))} for l in linhas if cel(l, col("rotulo"))]
        elif col("arquivo") is not None:
            i_arq = col("arquivo")
            g["arquivos"] += [{"artefato": cel(l, 0 if i_arq else 1), "arquivo": cel(l, i_arq)} for l in linhas if cel(l, i_arq)]
    return g


# ------------------------------------------------------------------ verificações do glossário
def _achado(severidade: str, codigo: str, resumo: str, documento: str, etapa: str = "design") -> Dict[str, str]:
    return {"severidade": severidade, "codigo": codigo, "etapa": etapa, "documento": documento,
            "agente_responsavel": DONOS.get(documento, ""), "resumo": resumo}


#: Antes ou depois de uma variante curta, o sinal de que ela está como rótulo ("Para todos", `Quem viu`, **Insta**,
#: célula de tabela) e não como locução da frase ("ativa a missão para todos os dispositivos").
_SINAL_DE_ROTULO = set("\"“”«»'`*|[]")


def _como_rotulo(texto: str, a: int, b: int) -> bool:
    antes = texto[:a].rstrip()[-1:]
    depois = texto[b:].lstrip()[:1]
    return antes in _SINAL_DE_ROTULO or depois in _SINAL_DE_ROTULO


def _linha_do_glossario(texto: str, pos: int, canonicos: List[str]) -> bool:
    """A ocorrência está numa linha de tabela que também traz um nome canônico do glossário: é a lista de variantes
    (a mesma variante pode ser listada na linha de outra entidade — «App Escola» na do Unoovista e na do Unooria)."""
    ini = texto.rfind("\n", 0, pos) + 1
    fim = texto.find("\n", pos)
    linha = texto[ini: fim if fim >= 0 else len(texto)]
    return linha.lstrip().startswith("|") and any(re.search(_padrao_nome(c), _dobrar(linha)) for c in canonicos if c)


def _entidades(g: Dict[str, Any], rotulo: str, texto: str) -> List[Dict[str, str]]:
    """Variante proibida usada. As ocorrências disputam o texto da mais longa para a mais curta: o canônico
    "Conselho Municipal de Recursos Comunitários" protege o trecho, mas a variante "Conselho Municipal de
    Recursos" solta (sem "Comunitários") é acusada.

    Não contam (exp01ef1b, 08/10/2026 — 13 dos 21 bloqueios eram isto): a linha de tabela que traz o canônico junto,
    que é o glossário republicado listando as variantes; e a variante de até duas palavras fora de posição de rótulo,
    que é locução da frase ("ativa a missão para todos os dispositivos" não é o botão «Para todos»)."""
    d = _dobrar(texto)
    achados = []
    canonicos = [e["nome"] for e in g["entidades"]]
    for ent in g["entidades"]:
        cands: List[Tuple[int, int, str, bool]] = []
        for nome, proibida in [(ent["nome"], False)] + [(v, True) for v in ent["variantes"]]:
            curta = len(nome.split()) <= 2
            cands += [(m.start(), m.end(), nome, proibida) for m in re.finditer(_padrao_nome(nome), d)
                      if not proibida or not (_linha_do_glossario(texto, m.start(), canonicos)
                                              or (curta and not _como_rotulo(texto, m.start(), m.end())))]
        ocupado: List[Tuple[int, int]] = []
        usos: Dict[str, List[int]] = {}
        for a, b, nome, proibida in sorted(cands, key=lambda c: -(c[1] - c[0])):
            if any(a < y and x < b for x, y in ocupado):
                continue
            ocupado.append((a, b))
            if proibida:
                usos.setdefault(nome, []).append(a)
        for nome, posicoes in usos.items():
            achados.append(_achado(
                "bloqueio", "variante-proibida",
                f"{rotulo}: «{nome}» ({len(posicoes)}×) é variante proibida — o nome canônico é «{ent['nome']}». "
                f"Trecho: `{_linha_de(texto, min(posicoes))}`", rotulo))
    return achados


def _segmento(texto: str, pos: int) -> Tuple[int, int]:
    """A frase ou a célula de tabela em volta de `pos`."""
    delim = ".|\n;!?"
    ini = max(texto.rfind(c, 0, pos) for c in delim) + 1
    fins = [i for i in (texto.find(c, pos) for c in delim) if i >= 0]
    return ini, (min(fins) if fins else len(texto))


def _personagens(g: Dict[str, Any], rotulo: str, texto: str) -> List[Dict[str, str]]:
    achados = []
    for p in g["personagens"]:
        nome = p["nome"]
        if not nome:
            continue
        papel_gestao = bool(_RE_PAPEL_DE_GESTAO.search(p.get("papel") or ""))
        viu_papel = viu_idade = False
        for m in re.finditer(r"(?<!\w)" + re.escape(nome) + r"(?!\w)", texto):
            ini, fim = _segmento(texto, m.start())
            trecho = texto[ini:fim]
            if not papel_gestao and not viu_papel and _RE_PAPEL_DE_GESTAO.search(trecho):
                viu_papel = True
                achados.append(_achado(
                    "atencao", "papel-divergente",
                    f"{rotulo}: {nome} aparece como quem coordena ou responde por algo, e o papel canônico é "
                    f"«{p.get('papel') or '—'}». Trecho: `{_linha_de(texto, m.start())}`", rotulo))
            idade = re.match(r"\W{0,3}\s*(\d{1,2})\s*anos", texto[m.end():m.end() + 12])
            if p.get("idade") and idade and not viu_idade and float(idade.group(1)) != p["idade"]:
                viu_idade = True
                achados.append(_achado(
                    "atencao", "idade-divergente",
                    f"{rotulo}: {nome} com {idade.group(1)} anos; o glossário diz {int(p['idade'])}. "
                    f"Trecho: `{_linha_de(texto, m.start())}`", rotulo))
    return achados


def _mencoes(g: Dict[str, Any], d: str) -> List[Tuple[int, str]]:
    """Onde cada entidade ou personagem é citado no texto dobrado, sob o nome canônico."""
    mencoes = []
    for ent in g["entidades"]:
        for nome in [ent["nome"]] + ent["variantes"]:
            mencoes += [(m.start(), ent["nome"]) for m in re.finditer(_padrao_nome(nome), d)]
    for p in g["personagens"]:
        mencoes += [(m.start(), p["nome"]) for m in re.finditer(_padrao_nome(p["nome"]), d)]
    return sorted(mencoes)


def _dono_do_numero(mencoes: List[Tuple[int, str]], d: str, pos: int, alcance: int = 200) -> Optional[str]:
    """A entidade mais próxima ANTES do número, na mesma linha; sem ela, a mais próxima depois.
    "Mesa Aberta (24 vagas…), Ponto de Apoio (18 vagas…)": as 18 vagas são do Ponto de Apoio."""
    ini = d.rfind("\n", 0, pos) + 1
    fim = d.find("\n", pos)
    fim = len(d) if fim < 0 else fim
    antes = [(p, n) for p, n in mencoes if max(ini, pos - alcance) <= p < pos]
    if antes:
        return antes[-1][1]
    depois = [(p, n) for p, n in mencoes if pos < p <= min(fim, pos + alcance)]
    return depois[0][1] if depois else None


def _numeros(g: Dict[str, Any], rotulo: str, texto: str) -> List[Dict[str, str]]:
    d = _dobrar(texto)
    nomes = [e["nome"] for e in g["entidades"]] + [p["nome"] for p in g["personagens"]]
    mencoes = _mencoes(g, d)
    extenso = "|".join(_NUMEROS_POR_EXTENSO)
    # (entidade, cabeça da unidade) → valores aceitos: duas linhas do glossário com a mesma unidade
    # e a mesma entidade (vagas novas × vagas totais) não se acusam uma à outra
    aceitos: Dict[Tuple[str, str], Set[float]] = {}
    linhas = []
    for n in g["numeros"]:
        if n.get("valor") is None:
            continue
        entidade = max((x for x in nomes if x and re.search(_padrao_nome(x), _dobrar(n["oque"]))), key=len, default=None)
        unidade = _dobrar(n["unidade"]).strip()
        if not entidade or not unidade:
            continue
        if "r$" in unidade or unidade in ("reais", "real"):
            cabeca, padrao = "r$", r"r\$\s*(\d[\d.,]*)"
        else:
            cabeca = re.findall(r"[a-z]+", unidade)[0] if re.findall(r"[a-z]+", unidade) else ""
            if len(cabeca) < 2:
                continue
            raiz = r"(?:vez(?:es)?|x)" if cabeca in ("vez", "vezes") else re.escape(cabeca.rstrip("s")) + "s?"
            padrao = rf"(?<![\w.,])(\d[\d.,]*|{extenso})\s*(?:de\s+)?{raiz}(?![a-z])"
        aceitos.setdefault((entidade, cabeca), set()).add(n["valor"])
        linhas.append((n, entidade, cabeca, padrao))
    achados = []
    vistos: Set[Tuple[str, str, float]] = set()
    for n, entidade, cabeca, padrao in linhas:
        for m in re.finditer(padrao, d):
            valor = _numero(texto[m.start(1):m.end(1)])
            if valor is None or valor in aceitos[(entidade, cabeca)]:
                continue
            if _dono_do_numero(mencoes, d, m.start()) != entidade or (entidade, cabeca, valor) in vistos:
                continue
            vistos.add((entidade, cabeca, valor))
            achados.append(_achado(
                "atencao", "numero-divergente",
                f"{rotulo}: {entidade} com {texto[m.start():m.end()].strip()}; o glossário fixa «{n['oque']}» = "
                f"{n['bruto']} {n['unidade']}. Trecho: `{_linha_de(texto, m.start())}`", rotulo))
    return achados


def _candidatos_a_rotulo(texto: str) -> List[Tuple[str, int]]:
    """Textos citados como rótulo: entre aspas/crases numa linha que fala de botão, ou na célula de uma
    linha da tabela de copy cuja chave é de botão (`e0.rotulo.botao_configurar`)."""
    cands: List[Tuple[str, int]] = []
    pos = 0
    for linha in texto.splitlines(keepends=True):
        if _RE_ROTULO_CONTEXTO.search(linha):
            cands += [(m.group(1), pos + m.start()) for m in _RE_ENTRE_ASPAS.finditer(linha)]
        if linha.lstrip().startswith("|") and _RE_CHAVE_DE_BOTAO.search(linha):
            cands += [(c, pos) for c in (x.strip() for x in linha.strip().strip("|").split("|"))]
        pos += len(linha)
    saida = []
    for bruto, p in cands:
        c = _limpa(bruto)
        if not c or not re.search(r"[A-Za-zÀ-ú]", c) or re.search(r"[_/]|\w\.\w|^E\d-|^[A-Z0-9_]+$", c):
            continue
        if not 1 <= len(c.split()) <= 8:
            continue
        saida.append((c, p))
    return saida


def _rotulos(g: Dict[str, Any], rotulo: str, texto: str) -> List[Dict[str, str]]:
    if not g["rotulos"]:
        return []
    canonicos = {_norm(r["rotulo"]) for r in g["rotulos"]}
    achados, vistos = [], set()
    for cand, pos in _candidatos_a_rotulo(texto):
        if _norm(cand) in canonicos:
            continue
        palavras = _palavras(cand)
        if not palavras:
            continue
        melhor, nota = None, 0.0
        for r in g["rotulos"]:
            ref = _palavras(r["rotulo"]) | _palavras(r["acao"])
            n = len(palavras & ref) / len(palavras)
            if n > nota:
                melhor, nota = r, n
        if not melhor or nota < 0.6 or (melhor["acao"], _norm(cand)) in vistos:
            continue
        vistos.add((melhor["acao"], _norm(cand)))
        achados.append(_achado(
            "atencao", "rotulo-divergente",
            f"{rotulo}: o botão de «{melhor['acao']}» aparece como «{cand}»; o rótulo canônico é «{melhor['rotulo']}». "
            f"Trecho: `{_linha_de(texto, pos)}`", rotulo))
    return achados


def _arquivos(g: Dict[str, Any], rotulo: str, texto: str) -> List[Dict[str, str]]:
    canonicos = {a["arquivo"].rsplit("/", 1)[-1]: a for a in g["arquivos"] if a.get("arquivo")}
    achados, vistos = [], set()
    for m in _RE_ARQUIVO.finditer(texto):
        base = m.group(1).rsplit("/", 1)[-1]
        if base in canonicos or base in vistos:
            continue
        for nome, a in canonicos.items():
            mesma_ext = base.rsplit(".", 1)[-1] == nome.rsplit(".", 1)[-1]
            prefixo = re.match(r"\d+[a-z]?-", nome)
            parecido = (prefixo and base.startswith(prefixo.group(0))) or base[:8] == nome[:8]
            if mesma_ext and parecido:
                vistos.add(base)
                achados.append(_achado(
                    "atencao", "arquivo-divergente",
                    f"{rotulo}: cita `{m.group(1)}`, e o arquivo de «{a['artefato']}» é `{a['arquivo']}`.", rotulo))
                break
    return achados


# ------------------------------------------------------------------ modelo de dados
_FAMILIAS = [
    ("uuid", r"uuid"),
    ("texto", r"text|varchar|character|char|string|citext"),
    ("inteiro", r"int|integer|bigint|smallint|serial|bigserial|int2|int4|int8"),
    ("booleano", r"boolean|bool"),
    ("data", r"timestamptz|timestamp|date|datetime|time"),
    ("json", r"jsonb|json"),
    ("decimal", r"numeric|decimal|float|double|real|money"),
]
_RE_TIPO = r"(?:" + "|".join(p for _, p in _FAMILIAS) + r")"


def _familia(tipo: str) -> str:
    t = _dobrar(tipo).strip()
    return next((f for f, p in _FAMILIAS if re.fullmatch(p, t)), t)


def _declaracoes(texto: str) -> Dict[str, Dict[str, Dict[str, Set[str]]]]:
    """`{tabela: {coluna: {família: {tipos como escritos}}}}` do DDL SQL, do erDiagram e da prosa
    (`- **\\`tabela\\`**: … \\`coluna TIPO\\``) do documento."""
    decl: Dict[str, Dict[str, Dict[str, Set[str]]]] = {}

    def anota(tabela: str, coluna: str, tipo: str) -> None:
        decl.setdefault(tabela.lower(), {}).setdefault(coluna.lower(), {}).setdefault(_familia(tipo), set()).add(tipo)

    for m in re.finditer(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"]?(\w+)[`\"]?\s*\((.*?)\)\s*;", texto or "", re.S | re.I):
        for linha in m.group(2).splitlines():
            s = linha.strip()
            if not s or re.match(r"(?:CONSTRAINT|PRIMARY|UNIQUE|FOREIGN|CHECK|EXCLUDE|--)\b", s, re.I):
                continue
            c = re.match(r"[`\"]?(\w+)[`\"]?\s+(" + _RE_TIPO + r")\b", s, re.I)
            if c:
                anota(m.group(1), c.group(1), c.group(2))
    for bloco in re.findall(r"erDiagram(.*?)(?:```|\Z)", texto or "", re.S):
        for ent, corpo in re.findall(r"([\w-]+)\s*\{([^}]*)\}", bloco):
            for linha in corpo.splitlines():
                c = re.match(r"\s*(" + _RE_TIPO + r")\w*\s+(\w+)", linha, re.I)
                if c:
                    anota(ent, c.group(2), c.group(1))
    for linha in (texto or "").splitlines():
        t = re.match(r"\s*[-*]\s*\*\*`?(\w+_\w+)`?\*\*", linha)
        if not t:
            continue
        for c in re.finditer(r"`(\w+)\s+(" + _RE_TIPO + r")\b[^`]*`", linha, re.I):
            anota(t.group(1), c.group(1), c.group(2))
    return decl


def _por_coluna(decl: Dict[str, Dict[str, Dict[str, Set[str]]]], coluna: str) -> Dict[str, Set[str]]:
    junto: Dict[str, Set[str]] = {}
    for colunas in decl.values():
        for fam, tipos in colunas.get(coluna, {}).items():
            junto.setdefault(fam, set()).update(tipos)
    return junto


def _tipos(fams: Dict[str, Set[str]]) -> str:
    return " × ".join(sorted("/".join(sorted(t)) for t in fams.values()))


def conferir_colunas(texto: str, referencia: str = "", rotulo: str = "PRD", rotulo_ref: str = "spec",
                     etapa: str = "dev") -> List[Dict[str, str]]:
    """O documento contra o próprio modelo de dados, e (com `referencia`) contra o da spec.

    - coluna citada (`tabela.coluna` com tabela declarada, ou "coluna \\`x\\`") que nenhum DDL ou
      erDiagram do documento declara = atenção;
    - a mesma coluna com dois tipos no documento = bloqueio — por tabela, e para chaves `*_id` entre
      tabelas (é a mesma chave: `escola_id` não pode ser UUID numa e TEXT na outra);
    - a coluna com tipo diferente do que a spec declara = bloqueio.
    """
    decl = _declaracoes(texto)
    achados: List[Dict[str, str]] = []
    if not decl:
        return achados

    def falha(sev: str, codigo: str, resumo: str) -> None:
        achados.append({"severidade": sev, "codigo": codigo, "etapa": etapa, "documento": rotulo,
                        "agente_responsavel": DONOS.get(rotulo, ""), "resumo": resumo})

    citadas = set()
    for m in re.finditer(r"(?<![\w.])(\w+)\.(\w+)\b", texto or ""):
        tabela, coluna = m.group(1).lower(), m.group(2).lower()
        if tabela in decl and coluna not in decl[tabela] and (tabela, coluna) not in citadas:
            citadas.add((tabela, coluna))
            falha("atencao", "coluna-inexistente",
                  f"{rotulo}: cita `{m.group(1)}.{m.group(2)}`, e o modelo de dados do próprio documento não declara essa "
                  f"coluna em `{m.group(1)}` (colunas: {', '.join(sorted(decl[tabela]))}). Quem codifica vai inventar a coluna "
                  f"ou ler de outra.")
    todas = {c for cols in decl.values() for c in cols}
    for m in re.finditer(r"\bcolunas?\s+`(\w+)`", texto or "", re.I):
        if m.group(1).lower() not in todas and ("*", m.group(1).lower()) not in citadas:
            citadas.add(("*", m.group(1).lower()))
            falha("atencao", "coluna-inexistente",
                  f"{rotulo}: cita a coluna `{m.group(1)}`, que nenhuma tabela do modelo de dados declara.")

    for tabela, colunas in sorted(decl.items()):
        for coluna, fams in sorted(colunas.items()):
            if len(fams) > 1 and not coluna.endswith("_id"):
                falha("bloqueio", "tipo-divergente",
                      f"{rotulo}: `{tabela}.{coluna}` declarada com dois tipos ({_tipos(fams)}).")
    for coluna in sorted(c for c in todas if c.endswith("_id")):
        fams = _por_coluna(decl, coluna)
        if len(fams) > 1:
            falha("bloqueio", "tipo-divergente",
                  f"{rotulo}: `{coluna}` aparece com dois tipos ({_tipos(fams)}). A chave é a mesma em todas as tabelas: "
                  f"a migration, o Prisma e a política de RLS (`current_setting(...)::uuid`) precisam de um tipo só.")

    if referencia:
        ref = _declaracoes(referencia)

        def divergente(nome: str, resumo: str) -> None:
            # O PRD que segue a migration publicada e registra a troca não está errado: a spec é que inventou o tipo.
            # Na exp06ef1b (10/10/2026) o PRD copiou a migration da Júri (`turma_id UUID`, `assuntos TEXT`), anotou
            # «Seguiu a plataforma» em cada linha — e saiu 🔴 três vezes por concordar com a plataforma.
            if _divergencia_registrada(texto, nome):
                achados.append({"severidade": "atencao", "codigo": "tipo-divergente-registrado", "etapa": "produto",
                                "documento": rotulo_ref, "agente_responsavel": "spec",
                                "resumo": f"{resumo} O {rotulo} seguiu a plataforma e registrou a troca; a {rotulo_ref} "
                                          "é que precisa acompanhar."})
            else:
                falha("bloqueio", "tipo-divergente-da-spec", resumo)

        for coluna in sorted(c for c in todas if c.endswith("_id")):
            nossas, delas = _por_coluna(decl, coluna), _por_coluna(ref, coluna)
            if nossas and delas and not set(nossas) & set(delas):
                divergente(coluna, f"`{coluna}` é {_tipos(nossas)} no {rotulo} e {_tipos(delas)} na {rotulo_ref}. "
                                   f"Um dos dois está errado, e quem codifica escolhe ao acaso.")
        for tabela, colunas in sorted(decl.items()):
            for coluna, fams in sorted(colunas.items()):
                delas = ref.get(tabela, {}).get(coluna)
                if delas and not coluna.endswith("_id") and not set(fams) & set(delas):
                    divergente(coluna, f"`{tabela}.{coluna}` é {_tipos(fams)} no {rotulo} e {_tipos(delas)} na {rotulo_ref}.")
    return achados


def _divergencia_registrada(texto: str, coluna: str) -> bool:
    """Uma linha do documento cita a coluna e diz que seguiu a plataforma (tabela de divergências da seção 19)."""
    alvo = re.compile(rf"(?<![\w]){re.escape(coluna)}(?![\w])", re.I)
    return any(alvo.search(l) and re.search(r"segu\w*\s+(?:a\s+)?plataforma|molde\s+d[ao]\s+j[úu]ri", l, re.I)
               for l in (texto or "").splitlines())


# ------------------------------------------------------------------ entrada
def variantes_aprovadas(g: Dict[str, Any], aprovado: str) -> List[Tuple[str, str]]:
    """(variante, canônico) das variantes proibidas que o one-pager aprovado usa.

    O glossário nasce na spec, escrito por um agente que transforma em proibição o que o PO escreveu: na exp01ef1b
    proibiu «Quem viu» (está no título aprovado), «Olhinho» (está numa fala aprovada do podcast) e «Visualizadores»
    (10× no one-pager). O design obedecia ao glossário e perdia o texto aprovado — ou não obedecia e bloqueava.
    """
    d = _dobrar(aprovado or "")
    return [(v, ent["nome"]) for ent in (g or {}).get("entidades", []) for v in ent["variantes"]
            if d and re.search(_padrao_nome(v), d)]


def glossario_contra_o_aprovado(spec: str, aprovado: str) -> List[Dict[str, str]]:
    """O gate de produto: variante proibida pelo glossário que o one-pager aprovado usa volta ao autor da spec."""
    g = extrair_glossario(spec)
    return [{"severidade": "bloqueio", "codigo": "glossario-proibe-o-aprovado", "etapa": "produto",
             "agente_responsavel": "spec-missao",
             "resumo": (f"O glossário canônico proíbe «{v}» (canônico «{c}»), e o one-pager aprovado usa «{v}». Termo "
                        "que o PO escreveu não é variante proibida: tire-o da coluna de variantes, ou trate-o como "
                        "outra entidade se for outra coisa (as pessoas que viram não são o botão que as mostra).")}
            for v, c in variantes_aprovadas(g, aprovado)] if g else []


def validar(spec: str, documentos: Dict[str, str], exigir_glossario: bool = True, etapa: str = "design",
            aprovado: str = "") -> Dict[str, Any]:
    """Confere cada documento (`{rótulo: texto}`) contra o glossário canônico da spec.

    `aprovado` é o one-pager que o PO aprovou: variante que ele usa não é proibida em documento nenhum — o conflito
    é do glossário, e o gate de produto o devolve ao autor da spec (`glossario_contra_o_aprovado`)."""
    g = extrair_glossario(spec)
    if g and aprovado:
        usadas = {_norm(v) for v, _ in variantes_aprovadas(g, aprovado)}
        g = {**g, "entidades": [{**e, "variantes": [v for v in e["variantes"] if _norm(v) not in usadas]}
                                for e in g["entidades"]]}
    achados: List[Dict[str, str]] = []
    if g is None:
        if exigir_glossario:
            achados.append(_achado("atencao", "glossario-ausente",
                                   "A spec não traz o bloco `## Glossário canônico` (entidades, personagens, números, rótulos "
                                   "de botão, arquivos): não há contra o que conferir os nomes da jornada, do fluxo, da copy, "
                                   "do protótipo e do PRD. Foi assim que o mesmo órgão saiu com quatro nomes na exp09ef1b.",
                                   "spec", etapa="produto"))
    elif not any(g.values()):
        if exigir_glossario:
            achados.append(_achado("atencao", "glossario-vazio",
                                   "A spec tem o título `## Glossário canônico`, mas nenhuma tabela legível dentro dele.",
                                   "spec", etapa="produto"))
    else:
        for rotulo, texto in documentos.items():
            if not (texto or "").strip():
                continue
            for checar in (_entidades, _personagens, _numeros, _rotulos, _arquivos):
                for a in checar(g, rotulo, texto):
                    a["etapa"] = etapa
                    achados.append(a)
    status = "bloqueado" if any(a["severidade"] == "bloqueio" for a in achados) else ("amarelo" if achados else "aprovado")
    return {"status": status, "achados": achados, "glossario": g}


def validar_estado(state: Dict[str, Any]) -> Dict[str, Any]:
    """O gate do design: jornada, fluxo, copy revisada e protótipo contra o glossário, mais as colunas
    que a própria spec cita (rebaixadas a atenção: não é o design que reescreve a spec)."""
    spec = str(state.get("spec_missao", "") or "")
    documentos = {
        "jornada": str(state.get("jornada_telas", "") or ""),
        "fluxo": str(state.get("fluxo_arestas", "") or ""),
        "copy revisada": str(state.get("copy_strings_revisada", "") or ""),
        "protótipo": texto_de_html(str(state.get("prototipo_arquivo", "") or "")),
    }
    aprovado = "\n".join(str(state.get(k, "") or "") for k in ("one_pager", "one_pager_po"))
    resultado = validar(spec, documentos, aprovado=aprovado)
    for a in conferir_colunas(spec, rotulo="spec", etapa="produto"):
        a["severidade"] = "atencao"
        a["resumo"] += " (Da spec: o design não a reescreve; o PRD é conferido de novo contra ela.)"
        resultado["achados"].append(a)
    achados = resultado["achados"]
    resultado["status"] = ("bloqueado" if any(a["severidade"] == "bloqueio" for a in achados)
                           else ("amarelo" if achados else "aprovado"))
    return resultado


def relatorio(resultado: Dict[str, Any], missao: str = "") -> str:
    icone = {"aprovado": "🟢", "amarelo": "🟡", "bloqueado": "🔴"}[resultado["status"]]
    linhas = [f"# Coerência entre documentos{f' — {missao}' if missao else ''}", "",
              f"**Veredito: {icone}** · os documentos conferidos contra o `## Glossário canônico` da spec e o modelo "
              f"de dados contra ele mesmo.", ""]
    g = resultado.get("glossario") or {}
    if g:
        linhas.append("Glossário lido: " + " · ".join(f"{len(v)} {k}" for k, v in g.items()) + ".")
        linhas.append("")
    if not resultado["achados"]:
        linhas.append("- Nenhuma divergência: nomes, papéis, números, rótulos e arquivos batem com o glossário.")
    for a in resultado["achados"]:
        linhas.append(f"- {'⛔' if a['severidade'] == 'bloqueio' else '⚠️'} `{a['codigo']}` — {a['resumo']}")
    if resultado["achados"]:
        linhas += ["", "Corrija no documento de quem escreveu (o dono vai no envelope). O glossário é a fonte: se ele "
                   "estiver errado, a correção é na spec, nunca uma terceira variante."]
    env = {"agente": AGENTE, "missao": missao, "status": resultado["status"], "precisa_humano": False,
           "achados": [{"severidade": a["severidade"], "classe": "consistencia", "codigo": a["codigo"],
                        "etapa": a.get("etapa", "design"), "agente_responsavel": a.get("agente_responsavel") or None,
                        "resumo": a["resumo"]} for a in resultado["achados"]]}
    return "\n".join(linhas) + "\n\n```json\n" + json.dumps(env, ensure_ascii=False, indent=1) + "\n```\n"
