"""Gera o fluxograma da esteira em LaTeX, a partir do código: `manual-unooria/fluxograma-dos-agentes.tex`.

Cada passo dos metadados (`pipeline.orchestrator.get_pipeline_agents_metadata`) vira um bloco do fluxograma, na ordem
em que roda, com o que faz, o objetivo, o que lê e o que grava — e o arquivo da sessão em que isso aparece. Nada é
escrito à mão: os loops e os paralelos vêm da árvore real do orquestrador; as entradas de um agente de modelo vêm das
variáveis do prompt dele; as de um verificador em código, dos campos da instância e das chaves que a classe lê do
estado; os arquivos, de `pipeline.artifacts.ARTIFACT_FILES`. Mudou a esteira, rode de novo:

    python scripts/gerar_fluxograma.py            # grava o .tex
    cd manual-unooria && tectonic -X compile fluxograma-dos-agentes.tex
"""
from __future__ import annotations

import inspect
import re
import sys
import time
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
warnings.filterwarnings("ignore")

SAIDA = RAIZ / "manual-unooria" / "fluxograma-dos-agentes.tex"

#: Variáveis que `agents/base.py` acrescenta a todo agente de modelo: contexto da execução, não insumo do passo.
RODAPE = {"heranca_degradada", "pedido_correcao", "notas_de_passagem", "mudancas_no_aprovado"}
PREFIXOS_RODAPE = ("anterior_", "rodada_anterior_", "bloqueio_modelo_", "retrabalho_")
#: Campos de um verificador que nomeiam chaves que ele LÊ / GRAVA.
CAMPOS_LEITURA = ("chave", "documentos", "status_keys", "fonte_key", "documento_key", "referencia_key", "spec_key",
                  "fontes")
#: Verificadores cujo `report_key` é o relatório que eles LEEM (o juiz escreveu antes), não o que gravam.
LEEM_O_RELATORIO = ("EnvelopeGateAgent", "DespachoTicketsAgent")
CAMPOS_ESCRITA = ("status_key", "report_key", "rodada_key", "round_key",
                  # o retrato do pedagógico que o A124 grava (PR 10)
                  "retrato_key")
#: Chaves de controle que não são artefato (contadores, envelopes, marcas de execução).
_CONTROLE = re.compile(r"(_rodada|_envelope|^reexecucoes$|^degradacoes$|^heranca_degradada$|^pipeline_|^agentes_degradados$"
                       r"|^tickets_|^juiz_.*_saida$|_entrada$|_documentos$)")


@dataclass
class Passo:
    numero: str
    nome: str
    agente: str
    etapa: str
    tipo: str              # modelo | codigo | portao | saida
    faz: str
    objetivo: str
    le: List[str] = field(default_factory=list)
    grava: List[str] = field(default_factory=list)
    loops: List[Tuple[str, int]] = field(default_factory=list)   # (nome do loop, rodadas), de fora para dentro
    paralelo: Optional[str] = None


def _ancestrais(raiz) -> Dict[str, List[Any]]:
    """`{nome do agente: [contêineres de fora para dentro]}` na árvore real."""
    saida: Dict[str, List[Any]] = {}

    def andar(agente, cadeia):
        saida.setdefault(agente.name, list(cadeia))
        for sub in getattr(agente, "sub_agents", []) or []:
            andar(sub, cadeia + [agente])

    andar(raiz, [])
    return saida


def _fonte_do_modo(agente) -> Optional[str]:
    """O código que o agente roda: a classe inteira, ou só o ramo do modo (`RastroCheckAgent`). None: modo sem ramo."""
    try:
        fonte = inspect.getsource(type(agente))
    except (OSError, TypeError):
        return ""
    modo = getattr(agente, "modo", None)
    if not modo:
        return fonte
    alvo = re.escape(modo)
    m = re.search(rf'self\.modo (?:== "{alvo}"|in \([^)]*"{alvo}"[^)]*\))(.*?)(?=\n {{8}}elif self\.modo|\n {{8}}else:|\Z)',
                  fonte, re.S)
    return m.group(1) if m else None


def _chaves_lidas_no_codigo(agente) -> List[str]:
    """As chaves que a classe do verificador lê do estado, pelo código-fonte. `RastroCheckAgent` só no ramo do modo."""
    fonte = _fonte_do_modo(agente)
    if not fonte:
        # sem ramo próprio, as chaves vêm dos campos (as do código são de todos os modos)
        return []
    chaves = re.findall(r'state(?:\.get)?\(\s*"([a-z_0-9]+)"', fonte) + re.findall(r'state\["([a-z_0-9]+)"\]', fonte)
    # `for k in ("one_pager", "brief_escopo"): state.get(k)` — a tupla de chaves que o laço lê
    for linha in fonte.splitlines():
        if "state" in linha:
            for tupla in re.findall(r'for \w+ in \(([^)]*)\)', linha):
                chaves += re.findall(r'"([a-z_0-9]+)"', tupla)
    return list(dict.fromkeys(chaves))


def _chaves_gravadas_no_codigo(agente) -> List[str]:
    """Chaves gravadas por constante de módulo: `state_delta={bnc.KEY_ESCOPO: …}` → `escopo_banca`."""
    import importlib

    fonte = _fonte_do_modo(agente) or ""
    apelidos = dict((b, a) for a, b in re.findall(r"from tools import (\w+) as (\w+)", fonte))
    chaves = []
    for apelido, constante in re.findall(r"state_delta=\{(\w+)\.(KEY_[A-Z_]+)", fonte):
        try:
            valor = getattr(importlib.import_module(f"tools.{apelidos.get(apelido, apelido)}"), constante)
        except (ImportError, AttributeError):
            continue
        chaves.append(str(valor))
    return chaves


def _primeira_frase(texto: str, limite: int = 230) -> str:
    texto = re.sub(r"\s+", " ", re.sub(r"[`*_#>]", "", texto or "")).strip()
    m = re.match(r"(.+?[.!?])(\s|$)", texto)
    frase = (m.group(1) if m else texto).strip()
    return frase if len(frase) <= limite else frase[: limite - 1].rsplit(" ", 1)[0] + "…"


def _objetivo(agente, meta: Dict[str, Any]) -> str:
    """Para quê o passo existe: a primeira frase do prompt (quem o agente é) ou da docstring da classe."""
    from google.adk.agents.llm_agent import LlmAgent

    if isinstance(agente, LlmAgent) and meta.get("prompt_file"):
        from prompts import load_prompt

        try:
            corpo = load_prompt(meta["prompt_file"])
        except Exception:  # noqa: BLE001 - prompt que depende de configuração
            corpo = ""
        # a apresentação ("Você é o Agente P0a — …") diz quem é, não para quê: vale a primeira frase útil
        for bloco in re.split(r"\n\s*\n", corpo)[:8]:
            if bloco.strip().startswith(("#", "<!--", "---", "|", "```", "{")):
                continue
            limpo = re.sub(r"\s+", " ", re.sub(r"[`*_#>]", "", bloco)).strip()
            for frase in re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])", limpo):
                if len(frase) > 40 and not re.match(r"(Você é|Voce e)\b", frase):
                    return _primeira_frase(frase)
    doc = inspect.getdoc(type(agente)) or ""
    return _primeira_frase(doc) if doc and type(agente).__module__.startswith("agents") else ""


def _tipo(agente, meta: Dict[str, Any]) -> str:
    from google.adk.agents.llm_agent import LlmAgent

    from agents.checkers import SaidaDeLoopAgent

    if isinstance(agente, LlmAgent):
        return "modelo"
    if isinstance(agente, SaidaDeLoopAgent) or str(meta.get("output_key") or "").endswith("_rodada"):
        return "saida"
    chave = str(meta.get("output_key") or "")
    if chave.endswith(("_status", "_report")) or "check" in meta["id"].lower() or "veredito" in meta["name"].lower():
        return "portao"
    return "codigo"


def coletar() -> List[Passo]:
    from google.adk.agents.llm_agent import LlmAgent
    from google.adk.agents.loop_agent import LoopAgent
    from google.adk.agents.parallel_agent import ParallelAgent
    from prompts import list_state_variables

    from pipeline.orchestrator import create_mission_orchestrator, get_pipeline_agents_metadata, iter_agent_tree

    raiz = create_mission_orchestrator(stages=["produto", "design", "dev"], com_transversal=True)
    por_nome = {a.name: a for _, a in iter_agent_tree(raiz)}
    cadeias = _ancestrais(raiz)
    passos: List[Passo] = []
    for meta in get_pipeline_agents_metadata(active_only=False):
        agente = por_nome[meta["id"]]
        tipo = _tipo(agente, meta)
        le: List[str] = []
        grava: List[str] = [meta["output_key"]] if meta.get("output_key") else []
        if isinstance(agente, LlmAgent):
            for v in list_state_variables(str(agente.instruction)):
                if v not in RODAPE and not v.startswith(PREFIXOS_RODAPE) and v != meta.get("output_key"):
                    le.append(v)
        else:
            campos = list(CAMPOS_LEITURA) + [c for c in type(agente).model_fields
                                              if c.endswith(("_key", "_keys")) and c not in CAMPOS_ESCRITA]
            for campo in dict.fromkeys(campos):
                valor = getattr(agente, campo, None)
                info = type(agente).model_fields.get(campo)
                if (getattr(agente, "modo", None) and info is not None and valor == info.default
                        and f"self.{campo}" not in (_fonte_do_modo(agente) or "")):
                    # o verificador de vários modos traz campos que só alguns modos leem: o padrão não é insumo deste
                    continue
                if isinstance(valor, str) and valor:
                    le.append(valor)
                elif isinstance(valor, dict):
                    le += [str(k) for k in valor]
                elif isinstance(valor, (list, tuple)):
                    # lista de chaves, ou de documentos descritos por dicionário ({"chave": …, "rotulo": …})
                    le += [str(v.get("chave") or "") if isinstance(v, dict) else str(v) for v in valor]
            le += _chaves_lidas_no_codigo(agente)
            grava += _chaves_gravadas_no_codigo(agente)
            for campo in CAMPOS_ESCRITA:
                valor = getattr(agente, campo, None)
                if isinstance(valor, str) and valor:
                    # o portão de envelope lê o relatório que o juiz escreveu e grava o status
                    (le if campo == "report_key" and type(agente).__name__ in LEEM_O_RELATORIO else grava).append(valor)
        grava = list(dict.fromkeys(g for g in grava if g))
        le = [x for x in dict.fromkeys(le) if x and x not in grava]
        loops, paralelo = [], None
        for c in cadeias.get(agente.name, []):
            if isinstance(c, LoopAgent):
                loops.append((c.name, int(getattr(c, "max_iterations", 0) or 0)))
            elif isinstance(c, ParallelAgent):
                paralelo = c.name
        numero = meta["name"].split("·")[0].strip()
        nome = meta["name"].split("·", 1)[1].strip() if "·" in meta["name"] else meta["name"]
        passos.append(Passo(numero=numero, nome=nome, agente=meta["id"], etapa=meta["stage"], tipo=tipo,
                            faz=meta.get("description") or "", objetivo=_objetivo(agente, meta),
                            le=le, grava=grava, loops=loops, paralelo=paralelo))
    return passos


# ------------------------------------------------------------------ LaTeX
def _tex(texto: str) -> str:
    """Escapa para LaTeX e troca o que a fonte não tem."""
    trocas = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{",
              "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    saida = "".join(trocas.get(c, c) for c in texto or "")
    saida = re.sub(r"[\U0001F000-\U0001FAFF☀-➿️]", "", saida)   # emoji: a fonte não tem
    saida = saida.replace("→", r"$\rightarrow$").replace("↔", r"$\leftrightarrow$").replace("×", r"$\times$")
    saida = saida.replace("≥", r"$\geq$").replace("≤", r"$\leq$").replace("≈", r"$\approx$").replace("∥", r"$\parallel$")
    saida = saida.replace("§", r"\S{}")
    return saida


def _chaves(chaves: List[str], arquivos: Dict[str, str], limite: int = 9) -> str:
    uteis = [c for c in chaves if not _CONTROLE.search(c)]
    controle = len(chaves) - len(uteis)
    itens = []
    for c in uteis[:limite]:
        arq = arquivos.get(c)
        itens.append(r"\cod{" + _tex(c) + "}" + (r"\,\arq{" + _tex(arq) + "}" if arq else ""))
    if len(uteis) > limite:
        itens.append(f"+{len(uteis) - limite}")
    if controle:
        itens.append(r"\textit{+" + str(controle) + " de controle}")
    return ", ".join(itens) or r"\textit{nada do estado da sessão (configuração fixa do passo)}"


ROTULO_TIPO = {"modelo": "MODELO", "codigo": "CÓDIGO", "portao": "PORTÃO", "saida": "SAÍDA DE LOOP"}
ESTILO_TIPO = {"modelo": "pmodelo", "codigo": "pcodigo", "portao": "pportao", "saida": "psaida"}
ETAPAS = {"produto": "Produto", "design": "Design", "dev": "Dev", "transversal": "Transversal"}


def _peso(p: Passo) -> int:
    """Altura estimada do bloco, em linhas, para quebrar as páginas."""
    texto = len(p.faz) + len(p.objetivo) + 18 * (len(p.le) + len(p.grava))
    return 4 + texto // 105


def paginas(passos: List[Passo], capacidade: int = 44) -> List[List[Passo]]:
    saida: List[List[Passo]] = [[]]
    usado = 0
    etapa = None
    for p in passos:
        w = _peso(p)
        if saida[-1] and (usado + w > capacidade or p.etapa != etapa):
            saida.append([])
            usado = 0
        saida[-1].append(p)
        usado += w
        etapa = p.etapa
    return [pg for pg in saida if pg]


def _figura(pagina: List[Passo], indice: Dict[str, int], arquivos: Dict[str, str],
            inicio_do_loop: Dict[str, Passo], fim_do_loop: Dict[str, Passo]) -> str:
    linhas = [r"\begin{center}", r"\begin{tikzpicture}[node distance=0.42cm]"]
    anterior = None
    for p in pagina:
        nid = f"n{indice[p.agente]}"
        posicao = f"below=of {anterior}" if anterior else ""
        cor = {"modelo": "unLavanda", "codigo": "unNavy", "portao": "unAzul!80!unNavy", "saida": "sinalAmbar"}[p.tipo]
        rotulo = (r"{\sffamily\bfseries\small " + _tex(p.numero) + r"\hspace{0.5em}" + _tex(p.nome) + r"}\hfill"
                  r"{\sffamily\tiny\color{white}\colorbox{" + cor + "}{" + ROTULO_TIPO[p.tipo] + r"}}\\[1pt]"
                  r"{\tiny\ttfamily\color{unLavanda}" + _tex(p.agente) + r"}\\[2pt]")
        corpo = []
        comecam = [n for n, _ in p.loops if inicio_do_loop[n] is p]
        if comecam:
            corpo.append(r"\ciclo{$\circlearrowright$ começa aqui: " + ", ".join(
                rf"\cod{{{_tex(n)}}} (até {dict(p.loops)[n]} rodadas)" for n in comecam) + "}")
        corpo.append(r"\campo{Faz}" + _tex(p.faz))
        if p.objetivo and _tex(p.objetivo) not in _tex(p.faz):
            corpo.append(r"\campo{Objetivo}" + _tex(p.objetivo))
        corpo.append(r"\campo{Entra}" + _chaves(p.le, arquivos))
        corpo.append(r"\campo{Sai}" + _chaves(p.grava, arquivos))
        if p.loops:
            corpo.append(r"\campo{Ciclo}" + r" $\supset$ ".join(r"\cod{" + _tex(n) + "}" for n, _ in p.loops))
        if p.paralelo:
            corpo.append(r"\campo{Roda}em paralelo com os demais de \cod{" + _tex(p.paralelo) + "}")
        terminam = [n for n, _ in p.loops if fim_do_loop[n] is p]
        if terminam:
            corpo.append(r"\ciclo{$\circlearrowleft$ fim do ciclo: " + "; ".join(
                rf"\cod{{{_tex(n)}}} --- reprovado, volta ao passo {_tex(inicio_do_loop[n].numero)}" for n in terminam)
                + "}")
        texto = rotulo + r"\\[1pt]".join(corpo)
        linhas.append(rf"\node[{ESTILO_TIPO[p.tipo]}{', ' + posicao if posicao else ''}] ({nid}) {{{texto}}};")
        if anterior:
            linhas.append(rf"\draw[fluxo] ({anterior}.south) -- ({nid}.north);")
        anterior = nid
    # faixas de loop: uma linha âmbar à esquerda por nível de aninhamento; a volta, quando o ciclo cabe na página
    faixas: Dict[str, Tuple[int, List[Passo]]] = {}
    for p in pagina:
        for nivel, (loop, _) in enumerate(p.loops):
            faixas.setdefault(loop, (nivel, []))[1].append(p)
    for loop, (nivel, nos) in faixas.items():
        x = 0.25 + 0.3 * nivel
        topo, base = f"n{indice[nos[0].agente]}", f"n{indice[nos[-1].agente]}"
        linhas.append(rf"\draw[loopfaixa] ([xshift=-{x}cm]{topo}.north west) -- ([xshift=-{x}cm]{base}.south west);")
        if inicio_do_loop[loop] is nos[0] and fim_do_loop[loop] is nos[-1] and topo != base:
            linhas.append(rf"\draw[loopvolta] ([xshift=-{x}cm]{base}.south west) -- ++(-0.18,0) |- "
                          rf"([xshift=-{x}cm]{topo}.north west);")
    linhas += [r"\end{tikzpicture}", r"\end{center}"]
    return "\n".join(linhas)


PREAMBULO = r"""% =============================================================================
%  FLUXOGRAMA DA ESTEIRA — GERADO POR scripts/gerar_fluxograma.py. NÃO EDITE À MÃO:
%  mude o código (metadados, prompts, árvore) e rode o script de novo.
%  Compilar com:  tectonic -X compile fluxograma-dos-agentes.tex
% =============================================================================
\documentclass[10pt,a4paper]{article}
\usepackage[brazil]{babel}
\usepackage[default]{sourcesanspro}
\usepackage{fontspec}
\setsansfont{Montserrat-Regular.otf}[BoldFont=Montserrat-Bold.otf,ItalicFont=Montserrat-Italic.otf,BoldItalicFont=Montserrat-BoldItalic.otf]
\setmonofont{SourceCodePro-Regular.otf}[BoldFont=SourceCodePro-Bold.otf,Scale=0.90]
\usepackage{microtype}
\usepackage{amssymb}
\usepackage[a4paper,top=2.0cm,bottom=1.8cm,left=2.6cm,right=1.6cm,headheight=14pt,footskip=0.9cm]{geometry}
\usepackage[table]{xcolor}
\usepackage{graphicx,booktabs,tabularx,array,fancyhdr,enumitem}
\usepackage{tikz}
\usetikzlibrary{positioning,arrows.meta,calc,fit,backgrounds}
\usepackage[hidelinks,pdfusetitle]{hyperref}
\definecolor{unNavy}{HTML}{0E1039}
\definecolor{unLavanda}{HTML}{8B85AC}
\definecolor{unAzul}{HTML}{7FA5E2}
\definecolor{unPapel}{HTML}{F5F5FA}
\definecolor{unLinha}{HTML}{D9D7E4}
\definecolor{unTexto}{HTML}{2B2D45}
\definecolor{sinalAmbar}{HTML}{B07A22}
\color{unTexto}
\setlength{\parindent}{0pt}
\newcommand{\cod}[1]{{\ttfamily\footnotesize #1}}
\newcommand{\arq}[1]{{\sffamily\tiny\color{unLavanda}[#1]}}
\newcommand{\campo}[1]{{\sffamily\bfseries\scriptsize\color{unNavy}#1:}\ }
\newcommand{\ciclo}[1]{{\sffamily\scriptsize\bfseries\color{sinalAmbar}#1}}
\pagestyle{fancy}\fancyhf{}
\renewcommand{\headrulewidth}{0.4pt}
\fancyhead[L]{\sffamily\scriptsize\color{unNavy}\textbf{unooria} \textbar\ Fluxograma da esteira}
\fancyhead[R]{\sffamily\scriptsize\color{unLavanda}\leftmark}
\fancyfoot[R]{\sffamily\scriptsize\color{unNavy}\thepage}
\fancyfoot[L]{\sffamily\scriptsize\color{unLavanda}Gerado do código em %DATA% · complementa o Manual do Gerador de Missões}
\tikzset{
  passo/.style={rectangle,rounded corners=3pt,draw=unLinha,line width=0.6pt,fill=white,text width=14.4cm,
    align=left,inner sep=5pt,font=\scriptsize},
  pmodelo/.style={passo,draw=unLavanda,fill=unLavanda!7},
  pcodigo/.style={passo,draw=unNavy!55,fill=unPapel},
  pportao/.style={passo,draw=unAzul!80!unNavy,fill=unAzul!10,line width=0.9pt},
  psaida/.style={passo,draw=sinalAmbar,fill=sinalAmbar!7,dashed},
  fluxo/.style={-{Stealth[length=2mm]},draw=unNavy!70,line width=0.7pt},
  loopfaixa/.style={draw=sinalAmbar,line width=1.1pt},
  loopvolta/.style={-{Stealth[length=2mm]},draw=sinalAmbar,line width=0.8pt,dashed,rounded corners=2pt},
  contlabel/.style={font=\sffamily\tiny\itshape,text=sinalAmbar,inner sep=1pt},
}
\begin{document}
"""


def _capa(passos: List[Passo]) -> str:
    por_etapa: Dict[str, List[Passo]] = {}
    for p in passos:
        por_etapa.setdefault(p.etapa, []).append(p)
    numeros = {p.numero.rstrip("abcdefghij") for p in passos}
    tipos = {t: sum(1 for p in passos if p.tipo == t) for t in ROTULO_TIPO}
    loops: Dict[str, Tuple[int, List[str]]] = {}
    for p in passos:
        for nome, rodadas in p.loops:
            loops.setdefault(nome, (rodadas, []))[1].append(p.numero)
    linhas = [
        r"\thispagestyle{empty}",
        r"{\sffamily\color{unNavy}\Huge\bfseries Fluxograma da esteira}\\[0.4em]",
        r"{\sffamily\color{unLavanda}\Large os " + str(len(numeros)) + " passos numerados (" + str(len(passos))
        + r" blocos), na ordem em que rodam}\\[1.2em]",
        r"Cada bloco é um agente ou portão da árvore real do orquestrador: o que faz, para quê existe, o que lê do "
        r"estado da sessão e o que grava --- com o arquivo da sessão em que aparece, entre colchetes. Este documento "
        r"é \textbf{gerado do código} por \cod{scripts/gerar\_fluxograma.py} e complementa o \emph{Manual do Gerador de "
        r"Missões}, que explica o porquê de cada regra; aqui está o mapa passo a passo.\\[1em]",
        r"\begin{tikzpicture}[node distance=0.25cm]",
        r"\node[pmodelo,text width=3.4cm] (a) {\textbf{MODELO} --- agente de linguagem (" + str(tipos["modelo"]) + ")};",
        r"\node[pcodigo,text width=3.4cm,right=of a] (b) {\textbf{CÓDIGO} --- passo determinístico (" + str(tipos["codigo"]) + ")};",
        r"\node[pportao,text width=3.4cm,right=of b] (c) {\textbf{PORTÃO} --- grava um veredito (" + str(tipos["portao"]) + ")};",
        r"\node[psaida,text width=3.4cm,right=of c] (d) {\textbf{SAÍDA DE LOOP} --- repete ou segue (" + str(tipos["saida"]) + ")};",
        r"\end{tikzpicture}\\[0.8em]",
        r"{\scriptsize Cada \textcolor{sinalAmbar}{\textbf{linha âmbar}} à esquerda é um ciclo de correção --- uma por "
        r"nível de aninhamento ---, e a seta tracejada é a volta quando o ciclo inteiro cabe na página. O bloco diz onde o "
        r"ciclo começa ($\circlearrowright$), a que ciclos pertence e para onde volta quando reprova ($\circlearrowleft$). "
        r"``de controle'' são contadores, envelopes e marcas de execução, que não são artefato.}\\[1em]",
        r"{\sffamily\bfseries\color{unNavy} As etapas}\\[0.3em]",
        r"\begin{tabularx}{\textwidth}{l r X}\toprule Etapa & Blocos & Passos \\ \midrule",
    ]
    for etapa, lista in por_etapa.items():
        linhas.append(f"{ETAPAS.get(etapa, etapa)} & {len(lista)} & {_tex(lista[0].numero)} a {_tex(lista[-1].numero)} \\\\")
    linhas += [r"\bottomrule\end{tabularx}\\[1em]", r"{\sffamily\bfseries\color{unNavy} Os ciclos de correção}\\[0.3em]",
               r"{\footnotesize\begin{tabularx}{\textwidth}{l c X}\toprule Loop & Teto & Passos \\ \midrule"]
    for nome, (rodadas, nums) in loops.items():
        linhas.append(rf"\cod{{{_tex(nome)}}} & {rodadas} & {_tex(nums[0])} a {_tex(nums[-1])} ({len(nums)} blocos) \\")
    linhas += [r"\bottomrule\end{tabularx}}", r"\newpage"]
    return "\n".join(linhas)


def gerar() -> str:
    from pipeline.artifacts import ARTIFACT_FILES

    passos = coletar()
    arquivos: Dict[str, str] = {}
    for chave, caminho in ARTIFACT_FILES:
        arquivos.setdefault(chave, caminho)
    indice = {p.agente: i for i, p in enumerate(passos)}
    pgs = paginas(passos)
    inicio_do_loop: Dict[str, Passo] = {}
    fim_do_loop: Dict[str, Passo] = {}
    for p in passos:
        for nome, _ in p.loops:
            inicio_do_loop.setdefault(nome, p)
            fim_do_loop[nome] = p
    corpo = [PREAMBULO.replace("%DATA%", time.strftime("%d/%m/%Y")), _capa(passos)]
    etapa = None
    for n, pg in enumerate(pgs):
        if pg[0].etapa != etapa:
            etapa = pg[0].etapa
            corpo.append(r"\markboth{" + ETAPAS.get(etapa, etapa) + "}{}")
            corpo.append(r"{\sffamily\bfseries\Large\color{unNavy}" + ETAPAS.get(etapa, etapa) + r"}\\[0.3em]")
        corpo.append(_figura(pg, indice, arquivos, inicio_do_loop, fim_do_loop))
        corpo.append(r"\newpage")
    corpo.append(r"\end{document}")
    return "\n".join(corpo) + "\n"


if __name__ == "__main__":
    SAIDA.write_text(gerar(), encoding="utf-8")
    print(f"gravado: {SAIDA.relative_to(RAIZ)}")
