"""O que o PO aprovou no one-pager chega inteiro à spec, ao PRD e ao one-pager pedagógico.

Auditoria das 11 missões do bucket em 06/10/2026: nenhuma spec trazia o podcast de recapitulação,
nenhuma trazia a tabela de tempos por etapa com os cenários de aula, e a spec aplicava as ressalvas
🟡 dos pareceres que o PO não tinha incorporado — a exp06ef1b perdeu a EF06CO07 (o PO aprovou "o
contrato de evidência com 4 habilidades") e passou de 29 para 24 minutos em tela; a exp04ef1b, de
29 para 25. Tudo a jusante segue a spec, e o PRD ainda trocava o contrato de evidência por chaves
de string: das quatro perguntas do Canal B da exp06ef1b, nenhuma chegou ao PRD. O dev devolveu a
missão por "inconsistência entre PRD e documentação de produto", e nenhum gate tinha acusado nada,
porque nenhum conferia um documento contra o one-pager aprovado.

Duas peças, as duas sem LLM:

- **Anexo literal.** As seções do one-pager que os gabaritos a jusante não tinham onde pôr —
  currículo, papel do professor, tempos e cenários de aula, podcast, contrato de evidência,
  hipóteses — são copiadas pela esteira para o fim do PRD e do one-pager pedagógico. O redator
  remete a elas e não as reescreve. O texto das réguas e das perguntas não é interpretado: o §12a
  muda de forma de missão para missão (tabela de quatro colunas, de cinco, subseções por
  habilidade), e um parser dele erraria em silêncio. Inteiro, ele não tem como perder nada.
- **Conferência.** Só o que tem estrutura firme: os códigos BNCC (§12a do one-pager → bloco 11 da
  spec → §14 do PRD e o pedagógico), o tempo total em tela (§10), o podcast (§11), um KPI por
  habilidade no PRD e os caminhos de artefato que o documento cita. Calibrado nos documentos das 11
  missões: as divergências que ele acusa são as que a auditoria encontrou lendo.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from tools import bncc

AGENTE = "conteudo-aprovado"

#: Seções do one-pager (`prompts/produto/04_secoes_apoio.md`); a numeração é a mesma nas 11 missões.
TITULOS = {
    2: "Currículo",
    9: "Papel do professor e parametrização com IA",
    10: "Modularidade, tempos sugeridos e controle do professor",
    11: "Podcast de recapitulação",
    12: "Evidências e dados, com o contrato de evidência por habilidade",
    17: "Hipóteses de validação",
}
SECOES_PRD: Tuple[int, ...] = (2, 9, 10, 11, 12, 17)
SECOES_PEDAGOGICO: Tuple[int, ...] = (10, 11, 12)

#: O título do anexo é também o marcador: comentário HTML apareceria cru no `.docx` do pedagógico.
TITULO_ANEXO = "Anexo — conteúdo aprovado pelo PO"
NOTA_ANEXO = (
    "> Copiado pela esteira, sem reescrita, de «{origem}», a versão que o PO aprovou. É a fonte do que "
    "a missão ensina e mede, do podcast, dos tempos e do papel do professor. O corpo deste documento "
    "remete a este anexo; se os dois divergirem, vale o anexo, e a divergência é defeito do corpo."
)

_RE_TITULO = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_RE_CERCA = re.compile(r"^\s*(```|~~~)")
_RE_12A = re.compile(r"^#{2,5}\s*12a\b", re.M | re.I)


# --------------------------------------------------------------------------- seções
def _titulos(texto: str) -> List[Tuple[int, int, int, str]]:
    """(início da linha, fim da linha, nível, título) de cada título fora de bloco de código.

    O PRD tem `# Iniciar frente de trabalho…` dentro do bloco bash da seção 17: lido como título,
    cortava a seção 17 no meio.
    """
    saida: List[Tuple[int, int, int, str]] = []
    pos, cerca = 0, False
    for linha in (texto or "").splitlines(keepends=True):
        if _RE_CERCA.match(linha):
            cerca = not cerca
        elif not cerca:
            m = _RE_TITULO.match(linha.rstrip("\n"))
            if m:
                saida.append((pos, pos + len(linha), len(m.group(1)), m.group(2)))
        pos += len(linha)
    return saida


def secao(texto: str, numero: int) -> Optional[str]:
    """Corpo da seção `numero` (`## 11. Podcast…`, `# 14. Pedagogia…`), sem o título.

    Vai até o próximo título de nível igual ou mais alto. `12a.` não é a seção 12 e `14.1` não é a
    14 — o `bncc.secao_bloco` cortava a 13 do PRD da exp09ef1b no `### 13.1`, e a seção saía vazia.
    """
    titulos = _titulos(texto)
    padrao = re.compile(rf"^{numero}\s*(?:\.(?![\dA-Za-z])|[—–-])")
    for i, (_, fim, nivel, titulo) in enumerate(titulos):
        if padrao.match(titulo.strip("*_ ")):
            fim_secao = next((ini for ini, _, n, _ in titulos[i + 1:] if n <= nivel), len(texto))
            return texto[fim:fim_secao]
    return None


def _origem(one_pager: str) -> str:
    for _, _, nivel, titulo in _titulos(one_pager):
        if nivel == 1:
            return titulo.strip("*_ ")
    return "one-pager de produto"


# --------------------------------------------------------------------------- anexo
def remover_anexo(texto: str) -> str:
    """O documento sem o anexo (e sem a divisória que o precede). Idempotente."""
    if not texto:
        return texto or ""
    for ini, _, nivel, titulo in _titulos(texto):
        if nivel == 1 and titulo.strip("*_ ").startswith(TITULO_ANEXO):
            corpo = texto[:ini].rstrip()
            if corpo.endswith("---"):
                corpo = corpo[:-3].rstrip()
            return corpo + "\n"
    return texto


def anexo(one_pager: str, secoes: Sequence[int]) -> str:
    """As seções aprovadas, literais, sob um título único. Vazio se o one-pager não tem nenhuma."""
    partes = []
    for numero in secoes:
        corpo = (secao(one_pager or "", numero) or "").strip()
        # a divisória que fecha cada seção do one-pager vira ruído entre as seções do anexo
        corpo = re.sub(r"\n-{3,}\s*$", "", corpo).strip()
        if corpo:
            partes.append(f"## {TITULOS.get(numero, f'Seção {numero}')} — one-pager §{numero}\n\n{corpo}\n")
    if not partes:
        return ""
    return "\n".join(["---", "", f"# {TITULO_ANEXO}", "", NOTA_ANEXO.format(origem=_origem(one_pager)), "", *partes])


def com_anexo(documento: str, one_pager: str, secoes: Sequence[int]) -> str:
    """O documento com o anexo atual no fim, trocando o de uma rodada anterior."""
    corpo = remover_anexo(documento or "").rstrip()
    extra = anexo(one_pager, secoes)
    return f"{corpo}\n\n{extra}" if extra else corpo + "\n"


# --------------------------------------------------------------------------- o que se confere
def codigos_aprovados(one_pager: str) -> List[str]:
    """Códigos de Computação do contrato de evidência (§12a); sem §12a, os do currículo (§2)."""
    s12 = secao(one_pager or "", 12) or ""
    m = _RE_12A.search(s12)
    if m:
        codigos = bncc.extrair_codigos(s12[m.start():])
        if codigos:
            return codigos
    return bncc.extrair_codigos(secao(one_pager or "", 2) or "")


def _decisao_pendente(*textos: str) -> bool:
    return any(bncc._DECISAO_RE.search(t or "") for t in textos)


_RE_EM_TELA_APROVADO = re.compile(r"em\s+tela\W{0,6}(\d{1,3})\s*min", re.I)
_RE_TEMPO_DECLARADO = (
    re.compile(r"\b(\d{1,3})\s*min(?:utos)?\b\s+(?:de\s+\w+\s+)?em\s+tela", re.I),  # "24 minutos em tela"
    re.compile(r"\btotal\s+(?:em|de|na)\s+tela\b[^0-9\n]{0,60}?(\d{1,3})\s*min", re.I),  # "tempo total em tela: 24 min"
    re.compile(r"\bem\s+tela\W{1,6}(\d{1,3})\s*min", re.I),  # "Em tela: 24 min"
)
#: Linha de decisão descartada: "Alternativa descartada: manter 29 min em tela" não é contradição.
_RE_LINHA_DESCARTADA = re.compile(r"descart|alternativa|anterior|\bantes\b", re.I)
#: Número logo depois disto discute o teto ou a ressalva, não declara o total. Vale para o número, não
#: para a linha: «Tempo total em tela: 24 minutos (o teto de referência da rubrica é 25)» declara 24.
_RE_NUMERO_DISCUTIDO = re.compile(r"rubrica|ressalva|teto de refer", re.I)


def tempo_aprovado(one_pager: str) -> Optional[int]:
    """O total em tela do §10 (`Em tela: 29 min`). Dois totais diferentes no §10: não há um aprovado."""
    valores = {int(n) for n in _RE_EM_TELA_APROVADO.findall(secao(one_pager or "", 10) or "")}
    return valores.pop() if len(valores) == 1 else None


def _linhas_fora_de_codigo(texto: str) -> Iterable[str]:
    cerca = False
    for linha in (texto or "").splitlines():
        if _RE_CERCA.match(linha):
            cerca = not cerca
        elif not cerca:
            yield linha


_RE_TETO = re.compile(r"teto|≤|<=|limite|m[áa]xim|exceder|\bat[ée]\s*$", re.I)


def tempos_divergentes(texto: str, alvo: int) -> List[Tuple[int, str]]:
    """Linhas que declaram outro total em tela.

    Número abaixo de 60% do aprovado é de uma etapa, não do total. Teto («não pode exceder 25 min»,
    «≤ 25 min») só contradiz quando fica abaixo do aprovado: «20 min em tela, abaixo do teto de 25»
    está certo; «29 aprovados» com «não pode exceder 25» manda o código cortar a missão.
    """
    achados: List[Tuple[int, str]] = []
    for linha in _linhas_fora_de_codigo(texto):
        if _RE_LINHA_DESCARTADA.search(linha):
            continue
        numeros: List[Tuple[int, bool]] = []
        for rx in _RE_TEMPO_DECLARADO:
            for m in rx.finditer(linha):
                antes = linha[max(0, m.start(1) - 40):m.start(1)]
                if _RE_NUMERO_DISCUTIDO.search(antes):
                    continue
                numeros.append((int(m.group(1)), bool(_RE_TETO.search(antes[-30:]))))
        if not numeros or any(n == alvo for n, _ in numeros):
            continue
        for n, teto in numeros:
            # o piso vale para os dois: «máximo de 6 minutos em tela na Etapa 5» é teto de uma etapa
            if n >= alvo * 0.6 and (n < alvo if teto else True):
                achados.append((n, linha.strip()))
                break
    return achados


_RE_SEM_PODCAST = re.compile(r"n[ãa]o se aplica|sem podcast|n[ãa]o h[áa] podcast|n[ãa]o tem podcast", re.I)
_RE_PODCAST = re.compile(r"podcast", re.I)


def tem_podcast(one_pager: str) -> bool:
    s11 = (secao(one_pager or "", 11) or "").strip()
    return len(s11) >= 200 and not _RE_SEM_PODCAST.search(s11[:400])


_RE_ARTEFATO = re.compile(r"(?<![\w/.-])((?:produto|design|dev|spec)/[\w./-]+?\.(?:md|html|docx|json|pdf))\b")


def artefatos_inexistentes(texto: str, validos: Iterable[str]) -> List[str]:
    """Caminhos de artefato da sessão (`produto/…`, `design/…`, `dev/…`) que a sessão não tem.

    Os PRDs das 11 missões apontavam `spec/<slug>-spec.md`, `design/04-copy-ptbr.md`,
    `design/08-prototipo-navegavel.html` — o primeiro vinha do próprio gabarito do PRD.
    """
    conhecidos = set(validos)
    vistos: List[str] = []
    for caminho in _RE_ARTEFATO.findall(texto or ""):
        if caminho not in conhecidos and caminho not in vistos:
            vistos.append(caminho)
    return vistos


# --------------------------------------------------------------------------- validação
def _achado(codigo: str, resumo: str, etapa: str, severidade: str = "bloqueio") -> Dict[str, str]:
    return {"severidade": severidade, "codigo": codigo, "etapa": etapa, "resumo": resumo}


def _status(achados: List[Dict[str, str]]) -> str:
    if any(a["severidade"] == "bloqueio" for a in achados):
        return "bloqueado"
    return "amarelo" if achados else "aprovado"


def _lista(codigos: Iterable[str]) -> str:
    return ", ".join(f"`{c}`" for c in codigos)


def _comparar_codigos(aprovados: Sequence[str], declarados: Sequence[str], onde: str, origem: str,
                      etapa: str, correcao_falta: str, correcao_sobra: str) -> List[Dict[str, str]]:
    achados = []
    faltam = [c for c in aprovados if c not in declarados]
    sobram = [c for c in declarados if c not in aprovados]
    if faltam:
        achados.append(_achado(
            "habilidade-perdida",
            f"{_lista(faltam)} {'está' if len(faltam) == 1 else 'estão'} em {origem} e "
            f"{'saiu' if len(faltam) == 1 else 'saíram'} de {onde}. {correcao_falta}", etapa))
    if sobram:
        achados.append(_achado(
            "habilidade-acrescentada",
            f"{_lista(sobram)} {'aparece' if len(sobram) == 1 else 'aparecem'} em {onde} e não "
            f"{'está' if len(sobram) == 1 else 'estão'} em {origem}. {correcao_sobra}", etapa))
    return achados


def _tempo(texto: str, one_pager: str, onde: str, etapa: str) -> List[Dict[str, str]]:
    alvo = tempo_aprovado(one_pager)
    if alvo is None:
        return []
    divergentes = tempos_divergentes(texto, alvo)
    if not divergentes:
        return []
    exemplos = "; ".join(f"«{linha[:140]}»" for _, linha in divergentes[:3])
    return [_achado(
        "tempo-alterado",
        f"O one-pager aprovado dá {alvo} min em tela (§10), e {onde} declara outro total: {exemplos}. "
        f"Use {alvo} min e a tabela por etapa do §10. Se um parecer pediu menos tempo, a recomendação "
        f"é do PO decidir no one-pager — aqui ela entra só como ressalva não incorporada.", etapa)]


def validar_spec(spec: str, one_pager: str) -> Dict[str, Any]:
    """A spec traduz o one-pager aprovado: mesmas habilidades, mesmo tempo, o podcast declarado."""
    achados: List[Dict[str, str]] = []
    bloco11 = bncc.secao_bloco(spec or "", 11) or ""
    aprovados = codigos_aprovados(one_pager)
    if aprovados and not _decisao_pendente(bloco11, secao(one_pager or "", 2) or ""):
        achados += _comparar_codigos(
            aprovados, bncc.extrair_codigos(bloco11), "o bloco 11 da spec",
            "o contrato de evidência do one-pager aprovado (§12a)", "produto",
            "A spec traduz o one-pager, não o revisa: recoloque cada uma no bloco 11, com a linha da matriz "
            "copiada do §12a (canal, ação, régua ternária). Se um parecer recomendou tirá-la, a recomendação "
            "vai para o bloco 12 como ressalva não incorporada — quem tira habilidade é o PO, no one-pager.",
            "A spec não acrescenta habilidade: tire-a do bloco 11, ou, se a lista oficial obriga a trocá-la, "
            "marque `[ABERTO — dono: produto: …]` dizendo por quê.")
    achados += _tempo(spec, one_pager, "a spec", "produto")
    if tem_podcast(one_pager) and not _RE_PODCAST.search(spec or ""):
        achados.append(_achado(
            "podcast-ausente",
            "O one-pager aprovado tem podcast de recapitulação (§11) e a spec não o menciona. Declare-o no "
            "bloco 8: título, vozes, duração, quando toca e quem toca, copiados do §11 — o roteiro fica no "
            "one-pager. Sem isso, design e dev reescrevem ou esquecem o áudio (aconteceu nas 11 missões).",
            "produto"))
    return {"status": _status(achados), "achados": achados, "codigos": aprovados,
            "tempo": tempo_aprovado(one_pager), "podcast": tem_podcast(one_pager)}


def _linhas_de_kpi(prd: str) -> List[str]:
    return [l for l in _linhas_fora_de_codigo(prd) if l.lstrip().startswith("|") and re.search(r"\bKPI-?\d", l)]


def validar_prd(prd: str, spec: str, one_pager: str, artefatos: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """O corpo do PRD (sem o anexo) contra a spec e o one-pager aprovado."""
    achados: List[Dict[str, str]] = []
    corpo = remover_anexo(prd or "")
    da_spec = bncc.extrair_codigos(bncc.secao_bloco(spec or "", 11) or "")
    s14 = secao(corpo, 14)
    if da_spec:
        if s14 is None:
            achados.append(_achado("secao-14-ausente", "O PRD não tem a seção `# 14. Pedagogia e conformidade`, "
                                   "onde fica a matriz das habilidades.", "dev"))
        else:
            achados += _comparar_codigos(
                da_spec, bncc.extrair_codigos(s14), "a matriz da seção 14 do PRD", "o bloco 11 da spec", "dev",
                "Toda habilidade da spec tem linha na matriz, com a régua inteira — Atingiu, Em processo e "
                "Não atingiu — e a pergunta do Canal B remetendo ao anexo (§12a). O PRD não reabre currículo.",
                "O PRD não acrescenta habilidade: tire-a da matriz.")
        linhas_kpi = _linhas_de_kpi(corpo)
        sem_kpi = [c for c in da_spec if not any(c in l for l in linhas_kpi)]
        if sem_kpi:
            achados.append(_achado(
                "habilidade-sem-kpi",
                f"Nenhum KPI da seção 2 mede quantos estudantes atingem {_lista(sem_kpi)}. A evidência pedagógica "
                f"é o número que a missão existe para mover: acrescente o KPI (uma linha pode cobrir várias "
                f"habilidades) com a pergunta «Quantos estudantes chegam a Atingiu em <código>?», a decisão com "
                f"limiar, os `EVT-` das ações que o servidor classifica e o cálculo sobre a coluna de nível que "
                f"o servidor grava — nunca `resultado.nivel`, o nível não vai no `track`.", "dev"))
    achados += _tempo(corpo, one_pager, "o PRD", "dev")
    if tem_podcast(one_pager):
        tem_rf = any(re.search(r"\bRF-\d", l) and _RE_PODCAST.search(l) for l in _linhas_fora_de_codigo(corpo))
        if not tem_rf:
            achados.append(_achado(
                "podcast-sem-requisito",
                "O one-pager aprovado tem podcast de recapitulação (§11, no anexo) e nenhum requisito funcional "
                "do PRD o cita. Acrescente o RF (quem toca, em que tela, em que momento — o aviso do §11 diz "
                "quando), a linha do asset no inventário de conteúdo e a tarefa que o liga.", "dev"))
    if artefatos is not None:
        achados += _artefatos(corpo, artefatos, "o PRD")
    return {"status": _status(achados), "achados": achados, "codigos": da_spec,
            "tempo": tempo_aprovado(one_pager), "podcast": tem_podcast(one_pager)}


def _artefatos(texto: str, artefatos: Iterable[str], onde: str) -> List[Dict[str, str]]:
    validos = sorted(set(artefatos))
    faltam = artefatos_inexistentes(texto, validos)
    if not faltam:
        return []
    mais_citados = [p for p in validos if p.startswith(("produto/05", "produto/00-", "design/0", "dev/01"))][:12]
    return [_achado(
        "artefato-inexistente",
        f"{onde.capitalize()} cita {_lista(faltam)}, que não {'existe' if len(faltam) == 1 else 'existem'} na sessão. "
        f"Os caminhos reais: {_lista(mais_citados)}.", "dev")]


def validar_pedagogico(pedagogico: str, spec: str, one_pager: str,
                       artefatos: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """O corpo do one-pager pedagógico (sem o anexo) contra a spec e o one-pager aprovado."""
    achados: List[Dict[str, str]] = []
    corpo = remover_anexo(pedagogico or "")
    da_spec = bncc.extrair_codigos(bncc.secao_bloco(spec or "", 11) or "")
    if da_spec:
        achados += _comparar_codigos(
            da_spec, bncc.extrair_codigos(corpo), "o one-pager pedagógico", "o bloco 11 da spec", "dev",
            "Cada habilidade entra em «O que a missão ensina» e em «Como a gente sabe que a criança aprendeu», "
            "com o código entre parênteses.",
            "O pedagógico não acrescenta habilidade: tire-a.")
    achados += _tempo(corpo, one_pager, "o one-pager pedagógico", "dev")
    if tem_podcast(one_pager) and not _RE_PODCAST.search(corpo):
        achados.append(_achado(
            "podcast-ausente",
            "O one-pager aprovado tem podcast de recapitulação (§11) e o pedagógico não o menciona. A seção "
            "«O podcast do fechamento» diz o título, quem fala, quanto dura, quando tocar e quem toca; o "
            "roteiro vai no anexo, para o time pedagógico aprovar o texto.", "dev"))
    if artefatos is not None:
        achados += _artefatos(corpo, artefatos, "o one-pager pedagógico")
    return {"status": _status(achados), "achados": achados, "codigos": da_spec,
            "tempo": tempo_aprovado(one_pager), "podcast": tem_podcast(one_pager)}


# --------------------------------------------------------------------------- relatório
def relatorio(resultado: Dict[str, Any], documento: str, missao: str = "") -> str:
    icone = {"aprovado": "🟢 FIEL AO ONE-PAGER APROVADO", "amarelo": "🟡 COM RESSALVAS",
             "bloqueado": "🔴 DIVERGE DO ONE-PAGER APROVADO"}[resultado["status"]]
    tempo = f"{resultado['tempo']} min em tela" if resultado.get("tempo") else "sem total em tela no §10"
    linhas = [f"# Conteúdo aprovado × {documento} — {missao or 'missão'}", "", f"**Veredito: {icone}**", "",
              f"Habilidades conferidas: {_lista(resultado.get('codigos') or []) or 'nenhuma'} · {tempo} · "
              f"podcast no one-pager: {'sim' if resultado.get('podcast') else 'não'}", ""]
    if resultado["achados"]:
        linhas += ["## Achados", ""]
        for a in resultado["achados"]:
            marca = "❌" if a["severidade"] == "bloqueio" else "⚠️"
            linhas.append(f"- {marca} **{a['codigo']}** — {a['resumo']}")
    else:
        linhas.append("Nenhum achado: habilidades, tempo em tela e podcast batem com o one-pager aprovado.")
    linhas += ["", "```json", json.dumps(
        {"agente": AGENTE, "missao": missao, "documento": documento, "status": resultado["status"],
         "achados": resultado["achados"]}, ensure_ascii=False, indent=2), "```"]
    return "\n".join(linhas)
