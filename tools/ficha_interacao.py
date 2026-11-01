"""A ficha de interação: a seção 4 do núcleo e do one-pager escrita momento a momento (29/10/2026).

O time achava o one-pager confuso — «não fica claro o que o estudante tem que fazer» — e o design desenhava telas sem
saber quantos itens, que gesto, o que acontece se o estudante não age nem o que abre o momento seguinte. A causa estava
na origem: o 004 escrevia o §4 por etapa, num parágrafo de atributos soltos, e a exp09ef1b saiu com um gesto descrito de
dois jeitos na mesma etapa, a Etapa 4 com três ordens diferentes, um caminho (A2) que nenhuma tela tratava e o texto de
espera fora do §4. O 0.2 só reconta o que o §4 diz, e contou a mesma ação duas vezes.

Agora cada etapa do §4 traz de 1 a 4 fichas `#### Momento E.k — <quem faz o quê>`, cada uma com os mesmos rótulos, na
mesma ordem. Este módulo lê as fichas (`extrair`) e confere o que dá para conferir sem ler: campo que falta, gesto fora
da lista ou sem quantidade, escolha sem opções, `Libera` sem destino, momento que nada alcança, caminho sem fim, ramo
sem condição e a consequência sem um relato por opção do Decidir. `[ABERTO — …]` e `[PROPOSTA …]` contam como campo
preenchido: a ficha bloqueia por falta de campo, não por decisão que é do PO.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

AGENTE = "ficha-interacao"

#: Rótulos da ficha, na ordem em que o 004 os escreve. «Só para quem» só existe em ramo; «Opções» só em escolha.
CAMPOS = ("Quem age", "Só para quem", "Na tela", "Opções", "Gesto", "Resposta na hora", "Se não fizer", "Se errar",
          "Libera", "Fica registrado", "Texto de tela")
CAMPOS_OBRIGATORIOS = ("Quem age", "Na tela", "Gesto", "Resposta na hora", "Se não fizer", "Se errar", "Libera",
                       "Fica registrado", "Texto de tela")
#: Primeira palavra do campo «Gesto». Só esperar e falar dispensam a quantidade.
GESTOS = ("tocar", "arrastar", "deslizar", "digitar", "escolher", "ordenar", "marcar", "rolar", "ler", "ouvir",
          "esperar", "falar")
GESTOS_SEM_QUANTIDADE = ("esperar", "falar")
#: Sinônimos e flexões frequentes em fichas de interação mapeados para os 12 verbos canônicos.
_SINONIMOS_GESTO: Dict[str, str] = {
    "clicar": "tocar", "clica": "tocar", "toca": "tocar", "apertar": "tocar", "aperta": "tocar",
    "pressionar": "tocar", "pressiona": "tocar", "acionar": "tocar", "aciona": "tocar", "abrir": "tocar",
    "abre": "tocar", "confirmar": "tocar", "confirma": "tocar", "enviar": "tocar", "envia": "tocar",
    "selecionar": "escolher", "seleciona": "escolher", "escolhe": "escolher", "optar": "escolher", "opta": "escolher",
    "votar": "escolher", "vota": "escolher", "definir": "escolher", "define": "escolher",
    "preencher": "digitar", "preenche": "digitar", "digita": "digitar", "escrever": "digitar", "escreve": "digitar",
    "inserir": "digitar", "insere": "digitar", "redigir": "digitar", "redige": "digitar",
    "arrasta": "arrastar", "mover": "arrastar", "move": "arrastar", "puxar": "arrastar", "posicionar": "arrastar",
    "desliza": "deslizar", "passar": "deslizar", "ajustar": "deslizar", "ajusta": "deslizar", "calibrar": "deslizar",
    "ordena": "ordenar", "classificar": "ordenar", "classifica": "ordenar", "organizar": "ordenar",
    "organiza": "ordenar", "priorizar": "ordenar", "prioriza": "ordenar", "ranquear": "ordenar",
    "marca": "marcar", "assinalar": "marcar", "assinala": "marcar", "checar": "marcar", "destacar": "marcar",
    "rola": "rolar", "percorrer": "rolar", "percorre": "rolar", "navegar": "rolar", "navega": "rolar",
    "le": "ler", "observar": "ler", "observa": "ler", "visualizar": "ler", "visualiza": "ler",
    "examinar": "ler", "examina": "ler", "conferir": "ler", "confere": "ler", "analisar": "ler", "analisa": "ler",
    "comparar": "ler", "compara": "ler", "inspecionar": "ler",
    "ouve": "ouvir", "escutar": "ouvir", "escuta": "ouvir", "reproduzir": "ouvir",
    "espera": "esperar", "aguardar": "esperar", "aguarda": "esperar",
    "fala": "falar", "debater": "falar", "debate": "falar", "conversar": "falar", "conversa": "falar",
    "discutir": "falar", "discute": "falar", "explicar": "falar", "explica": "falar", "apresentar": "falar",
}
#: Momentos na missão inteira e por etapa: menos que isso não descreve a tela; mais deixa de ser uma missão de aula.
MIN_MOMENTOS = 6
MAX_MOMENTOS = 14
MAX_MOMENTOS_POR_ETAPA = 4
#: A etapa do Decidir e a da consequência (Resultado/Aha): a consequência tem um relato por opção da escolha.
ETAPA_DECIDIR = 3
ETAPA_CONSEQUENCIA = 4

_RE_ETAPA = re.compile(r"^#{2,3}\s*\**\s*Etapa\s+(\d)\b[^\n]*$", re.M | re.I)
_RE_MOMENTO = re.compile(r"^#{3,5}\s*\**\s*Momento\s+(\d)\.(\d{1,2})([a-z]?)\b\s*[—–:-]?\s*(.*?)\**\s*$", re.M | re.I)
_RE_CAMPO = re.compile(r"^\s*(?:[-*•]\s+)?\*\*\s*(Quem age|S[óo] para quem|Na tela|Op[çc][õo]es(?:\s*\(\s*\d+\s*\))?|Gesto|"
                       r"Resposta na hora|Se n[ãa]o fizer|Se errar|Libera|Fica registrado|Texto de tela)\s*:?\s*\*\*\s*:?"
                       r"\s*(.*)$", re.M | re.I)
_RE_DESTINO = re.compile(r"Momento\s+(\d\.\d{1,2}[a-z]?)|\bfim da miss[ãa]o\b", re.I)
_RE_SE_OPCAO = re.compile(
    r"^\s*(?:[-*•]\s+)?\**\s*(?:Se|Quando)\s+(?:escolheu\s+|escolher\s+|marcou\s+|selecionou\s+)?[\"“«']([^\"”»'\n]+)[\"”»']\s*\**\s*[:—–-]",
    re.M | re.I,
)
_RE_ASPAS = re.compile(r"[\"“«]([^\"”»\n]+)[\"”»]")
_RE_MARCADOR = re.compile(r"\[(?:ABERTO|PROPOSTA|PAR[ÂA]METRO)\b", re.I)
_RE_N_OPCOES = re.compile(r"\(\s*(\d+)\s*\)")


@dataclass
class Momento:
    id: str                      # "3.2", "2.2a"
    etapa: int                   # a do ID
    etapa_secao: Optional[int]   # a do `### Etapa E` em que a ficha está
    titulo: str
    campos: Dict[str, str] = field(default_factory=dict)
    corpo: str = ""

    @property
    def ramo(self) -> bool:
        return self.id[-1].isalpha()


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKC", texto or "").casefold()
    texto = re.sub(r"[\"“”«»'‘’*_`]", "", texto)
    return re.sub(r"\s+", " ", texto).strip(" .,;:!?…—–-")


def _rotulo(bruto: str) -> str:
    """O nome canônico do campo: «Opções (3)» → «Opções»; caixa e acento como em `CAMPOS`."""
    chave = _normalizar(re.sub(r"\(.*\)", "", bruto))
    for campo in CAMPOS:
        if _normalizar(campo) == chave:
            return campo
    return bruto.strip()


def _secao_4(texto: str) -> str:
    from tools.conteudo_aprovado import secao

    return secao(texto or "", 4) or texto or ""


def extrair(texto: str) -> List[Momento]:
    """As fichas `#### Momento E.k` da seção 4, com os campos de cada uma e a etapa em que estão."""
    s4 = _secao_4(texto)
    etapas = [(m.start(), int(m.group(1))) for m in _RE_ETAPA.finditer(s4)]
    titulos = list(_RE_MOMENTO.finditer(s4))
    momentos: List[Momento] = []
    for i, m in enumerate(titulos):
        fim = titulos[i + 1].start() if i + 1 < len(titulos) else len(s4)
        prox_etapa = next((ini for ini, _ in etapas if m.end() < ini < fim), None)
        corpo = s4[m.end():prox_etapa if prox_etapa is not None else fim]
        etapa_secao = next((n for ini, n in reversed(etapas) if ini < m.start()), None)
        campos: Dict[str, str] = {}
        brutos: Dict[str, str] = {}
        for c in _RE_CAMPO.finditer(corpo):
            nome = _rotulo(c.group(1))
            if nome not in campos:
                campos[nome] = c.group(2).strip()
                brutos[nome] = c.group(1)
        if "Opções" in brutos:
            n = _RE_N_OPCOES.search(brutos["Opções"])
            campos["Opções (n)"] = n.group(1) if n else ""
        momentos.append(Momento(id=f"{m.group(1)}.{int(m.group(2))}{m.group(3).lower()}", etapa=int(m.group(1)),
                                etapa_secao=etapa_secao, titulo=m.group(4).strip(), campos=campos, corpo=corpo))
    return momentos


def etapas_da_secao(texto: str) -> List[int]:
    return sorted({int(m.group(1)) for m in _RE_ETAPA.finditer(_secao_4(texto))})


def _achado(codigo: str, resumo: str, severidade: str = "bloqueio") -> Dict[str, str]:
    return {"codigo": codigo, "resumo": resumo, "severidade": severidade, "etapa": "produto",
            "agente_responsavel": AGENTE}


def _preenchido(valor: str) -> bool:
    return bool(_RE_MARCADOR.search(valor) or _RE_ASPAS.search(valor)) or len(valor.split()) >= 2 or valor.strip().casefold() in {"nada", "nada.",
                                                                                                     "—", "-"}


def _destinos(libera: str) -> List[str]:
    return [m.group(1).lower() if m.group(1) else "fim" for m in _RE_DESTINO.finditer(libera or "")]


def validar(texto: str) -> Dict[str, Any]:
    """As fichas da seção 4: campos, gesto, quantidade, opções, caminho dos `Libera`, ramos e consequência por opção."""
    momentos = extrair(texto)
    achados: List[Dict[str, str]] = []
    if not momentos:
        achados.append(_achado("secao-4-sem-fichas", "A seção 4 não tem fichas `#### Momento E.k — <quem faz o quê>`: "
                                                     "cada etapa se escreve momento a momento, com os rótulos da "
                                                     "ficha de interação. Sem elas o design inventa a tela.", "atencao"))
        return {"status": "amarelo", "achados": achados, "momentos": 0, "abertos": 0}

    ids = [m.id for m in momentos]
    por_id = {m.id: m for m in momentos}
    for repetido in sorted({i for i in ids if ids.count(i) > 1}):
        achados.append(_achado("momento-repetido", f"O Momento {repetido} aparece mais de uma vez na seção 4."))

    for etapa in etapas_da_secao(texto):
        n_etapa = sum(1 for m in momentos if m.etapa_secao == etapa)
        if not n_etapa:
            achados.append(_achado("etapa-sem-momento", f"A Etapa {etapa} não tem nenhuma ficha `#### Momento "
                                                        f"{etapa}.1 — …`."))
        elif n_etapa > MAX_MOMENTOS_POR_ETAPA:
            achados.append(_achado("momentos-fora-da-faixa", f"A Etapa {etapa} tem {n_etapa} momentos; cabem até "
                                                             f"{MAX_MOMENTOS_POR_ETAPA}: junte o que é o mesmo gesto.",
                                   "atencao"))
    if not MIN_MOMENTOS <= len(momentos) <= MAX_MOMENTOS:
        achados.append(_achado("momentos-fora-da-faixa", f"A missão tem {len(momentos)} momento(s); são de "
                                                         f"{MIN_MOMENTOS} a {MAX_MOMENTOS}.", "atencao"))

    for m in momentos:
        nome = f"Momento {m.id}"
        if m.etapa_secao is not None and m.etapa != m.etapa_secao:
            achados.append(_achado("momento-fora-da-etapa", f"O {nome} está dentro da Etapa {m.etapa_secao}: o número "
                                                            "do momento começa pelo da etapa."))
        faltam = [c for c in CAMPOS_OBRIGATORIOS if c not in m.campos]
        if faltam:
            achados.append(_achado("campo-ausente", f"O {nome} não tem " + ", ".join(f"«{c}»" for c in faltam)
                                   + ". Campo que você não sabe leva `[ABERTO — dono: PO: <o que falta>]`."))
        for c in CAMPOS_OBRIGATORIOS:
            valor = m.campos.get(c)
            if valor is None or _preenchido(valor) or (c == "Quem age" and valor.split()):
                continue
            if c == "Texto de tela" and "nenhum texto novo" in _normalizar(valor):
                continue
            if c in ("Se não fizer", "Se errar") and _normalizar(m.campos.get("Quem age", "")) in {"sistema",
                                                                                                    "professor"}:
                continue
            achados.append(_achado("campo-vazio", f"O campo «{c}» do {nome} está vazio: diga o que a tela faz, ou "
                                                  "marque `[ABERTO — dono: PO: …]`."))

        gesto = m.campos.get("Gesto", "")
        if gesto.split() and not _RE_MARCADOR.match(gesto.strip()):
            verbo_bruto = _normalizar(gesto.split()[0])
            verbo_sem_acento = "".join(c for c in unicodedata.normalize("NFD", verbo_bruto)
                                       if unicodedata.category(c) != "Mn")
            verbo = verbo_bruto if verbo_bruto in GESTOS else _SINONIMOS_GESTO.get(verbo_sem_acento, verbo_bruto)
            if verbo not in GESTOS:
                from tools import classificador

                leitura = classificador.gesto_equivalente_ficha(gesto)
                if leitura.rotulo == "equivalente":
                    achados.append(_achado("gesto-fora-da-lista", f"O gesto do {nome} começa com «{gesto.split()[0]}»; "
                                           "prefira abrir com um destes verbos canônicos: " + ", ".join(GESTOS) + ".",
                                           "atencao"))
                else:
                    achados.append(_achado("gesto-fora-da-lista", f"O gesto do {nome} começa com «{gesto.split()[0]}»; "
                                           "use um destes: " + ", ".join(GESTOS) + "."))
            elif verbo not in GESTOS_SEM_QUANTIDADE:
                quantidade = re.split(r"\s[—–]\s", gesto, maxsplit=1)[0]
                if not re.search(r"\d", quantidade) and not _RE_MARCADOR.search(quantidade):
                    achados.append(_achado("gesto-sem-quantidade", f"O gesto do {nome} não diz quantas vezes nem "
                                                                   "sobre quantos itens: «escolher · 1 de 3 cartões», "
                                                                   "«ordenar · 3 critérios»."))
            if verbo == "escolher":
                opcoes = m.campos.get("Opções")
                n = m.campos.get("Opções (n)", "")
                if opcoes is None:
                    achados.append(_achado("escolha-sem-opcoes", f"O {nome} pede uma escolha e não tem a linha "
                                                                 "`**Opções (n):** \"A\" · \"B\" · \"C\"`."))
                elif not _RE_MARCADOR.search(opcoes) and n and int(n) != len(_RE_ASPAS.findall(opcoes)):
                    achados.append(_achado("escolha-sem-opcoes", f"As opções do {nome} dizem {n} e trazem "
                                                                 f"{len(_RE_ASPAS.findall(opcoes))} entre aspas."))

        for campo_detalhe in ("Na tela", "Resposta na hora"):
            val_det = m.campos.get(campo_detalhe, "")
            if val_det and not _RE_MARCADOR.search(val_det) and len(val_det.split()) < 4:
                achados.append(_achado("mecanica-pouco-detalhada",
                                       f"O campo «{campo_detalhe}» do {nome} está telegráfico («{val_det}»): detalhe "
                                       "quais elementos/quantidades aparecem na tela e o que muda visualmente na hora.",
                                       "atencao"))

        tela = m.campos.get("Texto de tela", "")
        if tela and not _RE_ASPAS.search(tela) and "nenhum texto novo" not in _normalizar(tela) \
                and not _RE_MARCADOR.search(tela):
            achados.append(_achado("texto-de-tela-ausente", f"O «Texto de tela» do {nome} não traz o texto entre "
                                                            "aspas, palavra por palavra, nem diz «nenhum texto novo»."))

        libera = m.campos.get("Libera", "")
        if libera and not _RE_MARCADOR.search(libera):
            destinos = _destinos(libera)
            if not destinos:
                achados.append(_achado("libera-sem-destino", f"O «Libera» do {nome} não diz para onde vai: "
                                                             "`<condição> → Momento E.k` ou «fim da missão»."))
            for d in destinos:
                if d != "fim" and d not in por_id:
                    achados.append(_achado("libera-sem-destino", f"O {nome} libera o Momento {d}, que não existe na "
                                                                 "seção 4."))

        if m.ramo and "Só para quem" not in m.campos:
            achados.append(_achado("ramo-sem-condicao", f"O {nome} é um caminho de parte da turma (tem letra) e não "
                                                        "diz «Só para quem»."))
        if not m.ramo and "Só para quem" in m.campos:
            achados.append(_achado("ramo-sem-condicao", f"O {nome} diz «Só para quem», mas não tem letra: caminho de "
                                                        f"parte da turma é `Momento {m.id}a`, `{m.id}b`."))

    alcancados = {d for m in momentos for d in _destinos(m.campos.get("Libera", "")) if d != "fim"}
    # `Libera` em aberto pode levar a qualquer momento: não dá para acusar quem ficou sem caminho
    libera_em_aberto = any(_RE_MARCADOR.search(m.campos.get("Libera", "")) for m in momentos)
    for m in momentos[1:]:
        if m.id not in alcancados and not libera_em_aberto:
            achados.append(_achado("momento-inalcancavel", f"Nenhum «Libera» leva ao Momento {m.id}: de onde o "
                                                           "estudante chega a ele?"))
    if not any("fim" in _destinos(m.campos.get("Libera", "")) for m in momentos):
        achados.append(_achado("sem-fim", "Nenhum «Libera» termina em «fim da missão»."))

    opcoes_decidir = [o for m in momentos if m.etapa == ETAPA_DECIDIR and m.campos.get("Opções")
                      for o in _RE_ASPAS.findall(m.campos["Opções"])]
    consequencia = next((m for m in momentos if m.etapa == ETAPA_CONSEQUENCIA), None)
    if opcoes_decidir and consequencia is not None:
        relatos = {_normalizar(o) for o in _RE_SE_OPCAO.findall(consequencia.corpo)}
        sem_relato = [o for o in opcoes_decidir if _normalizar(o) not in relatos]
        if sem_relato:
            achados.append(_achado("consequencia-sem-opcao", f"O Momento {consequencia.id} (a consequência) não tem a "
                                   "linha `- Se \"<opção>\": …` para " + ", ".join(f"«{o}»" for o in sem_relato)
                                   + ": cada opção do Decidir tem o seu relato."))

    abertos = sum(len(_RE_MARCADOR.findall(m.corpo)) for m in momentos)
    bloqueia = any(a["severidade"] == "bloqueio" for a in achados)
    status = "bloqueado" if bloqueia else ("amarelo" if achados else "aprovado")
    return {"status": status, "achados": achados, "momentos": len(momentos), "abertos": abertos}


def relatorio(resultado: Dict[str, Any], missao: str = "", envelope: Optional[Dict[str, Any]] = None) -> str:
    """O relatório da ficha. `envelope` troca o JSON do fim — o `MecanicaCheckAgent` põe ali o da mecânica inteira."""
    icone = {"aprovado": "🟢", "amarelo": "🟡", "bloqueado": "🔴"}[resultado["status"]]
    linhas = [f"# Ficha de interação{f' — {missao}' if missao else ''}", "", f"**Veredito: {icone}**", "",
              f"Momentos na seção 4: {resultado.get('momentos', 0)} · campos em aberto para o PO: "
              f"{resultado.get('abertos', 0)}", ""]
    if resultado["achados"]:
        linhas += ["## Achados", ""]
        linhas += [f"- {'🔴' if a['severidade'] == 'bloqueio' else '🟡'} `{a['codigo']}` — {a['resumo']}"
                   for a in resultado["achados"]]
        linhas += ["", "Corrija a ficha no campo apontado. Se o achado é de caminho (momento que nada libera, ramo que "
                   "não volta), a correção é de mecanismo — registre na 18-parcial.", ""]
    env = envelope or {"agente": AGENTE, "missao": missao, "status": resultado["status"],
                       "achados": resultado["achados"], "precisa_humano": False}
    linhas += ["```json", json.dumps(env, ensure_ascii=False, indent=1), "```", ""]
    return "\n".join(linhas)


def pior(*status: str) -> str:
    ordem = {"aprovado": 0, "amarelo": 1, "bloqueado": 2}
    return max(status, key=lambda s: ordem.get(s, 0))
