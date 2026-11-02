"""Lint determinístico do protótipo HTML — o D8 deixa de se auto-aprovar.

O QA de design julgava o HTML que o próprio agente de design gerou, lendo o relatório dele
em vez do arquivo. Não havia nenhuma conferência mecânica: um protótipo com metade das telas,
com `TODO` na tela de pico ou que nem abre passava se o relatório dissesse que estava pronto.

As perguntas aqui são todas de FATO — o arquivo abre? as telas declaradas estão nele? sobrou
marcador de rascunho? — e por isso cabem em código. Julgar se a tela está BOA continua sendo
trabalho do QA.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

AGENTE = "prototipo-lint"

_RE_ID_TELA = re.compile(r"\bE\d-(?:ALU|PROF|SIS)-\d{2}\b")
#: Marcador de rascunho de quem escreve código — em MAIÚSCULAS, como se escreve. Em 23/09/2026 a
#: regra ignorava caixa e bloqueou um protótipo por "você aprendeu que **todo** enquadramento conta
#: uma história": em português, `todo` e `a definir` são palavras, e `placeholder` é o nome da
#: convenção do DS para a caixa de mídia do wireframe. Colchete de marcador conta em qualquer caixa.
_RE_RASCUNHO = re.compile(r"\b(?:TODO|FIXME|XXX)\b|(?i:lorem ipsum|\[\s*preencher|\[\s*a definir|\[\[[^\]]*\]\])")
#: Comentários não vão à tela da criança: CSS, HTML e JS de linha.
_RE_COMENTARIO = re.compile(r"/\*.*?\*/|<!--.*?-->|(?<![:\w])//[^\n]*", re.S)
_RE_TAG_ABERTA = re.compile(r"<(html|body)\b", re.IGNORECASE)


def validar(html: str, telas_declaradas: Optional[List[str]] = None) -> Dict[str, Any]:
    """Confere o protótipo contra o inventário de telas da jornada."""
    texto = html or ""
    achados: List[Dict[str, str]] = []

    def falha(codigo: str, resumo: str, severidade: str = "bloqueio") -> None:
        achados.append({"severidade": severidade, "codigo": codigo, "etapa": "design", "resumo": resumo})

    if not texto.strip():
        falha("prototipo-vazio", "O protótipo chegou vazio: não há arquivo para o QA inspecionar.")
        return {"status": "bloqueado", "achados": achados, "telas": [], "declaradas": telas_declaradas or []}

    if not _RE_TAG_ABERTA.search(texto):
        falha("prototipo-nao-abre", "Sem `<html>` nem `<body>`: o arquivo não é uma página que o navegador abre.")

    telas = sorted(set(_RE_ID_TELA.findall(texto)))
    declaradas = sorted(set(telas_declaradas or []))
    telas_e6 = [t for t in telas if t.startswith("E6-")]
    if telas_e6:
        falha("etapa-6-removida",
              f"O protótipo traz tela(s) da Etapa 6 ({', '.join(telas_e6[:6])}): a missão termina na Etapa 5 "
              "(Explicar) e não deve ter Etapa 6 de transferência.")
    for m_alu in re.finditer(r'data-screen-id\s*=\s*["\'](E\d-ALU-\d{2})["\']([^>]*>.*?)(?=data-screen-id\s*=|</body>|$)', texto, re.I | re.S):
        bloco_alu = re.sub(r"<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>", " ", m_alu.group(2), flags=re.I | re.S)
        if re.search(r"\bpodcast\b", bloco_alu, re.I) and not re.search(r"\b(?:sem|n[ãa]o)\s+podcast\b", bloco_alu, re.I):
            falha("podcast-na-tela-do-estudante",
                  f"A tela do estudante `{m_alu.group(1)}` no protótipo menciona podcast: o podcast de recapitulação "
                  "é exclusivo da visão do professor (`E*-PROF-*`).")
            break
    if declaradas:
        faltando = [t for t in declaradas if t not in telas]
        if faltando:
            falha("telas-ausentes",
                  f"{len(faltando)} tela(s) do inventário não aparecem no protótipo: {', '.join(faltando[:6])}"
                  + ("…" if len(faltando) > 6 else "")
                  + ". O QA inspeciona o que está na tela, não o que o relatório promete.")
        sobrando = [t for t in telas if t not in declaradas]
        if sobrando:
            falha("telas-nao-declaradas",
                  f"Tela no protótipo que o inventário não declara: {', '.join(sobrando[:6])}. "
                  f"Ou a jornada está desatualizada, ou o protótipo inventou tela.",
                  severidade="atencao")
    elif not telas:
        falha("sem-id-de-tela",
              "Nenhum identificador `E<etapa>-<ator>-<n>` no protótipo: sem isso não há como "
              "casar tela construída com tela declarada, e o QA vira leitura de relatório.")

    visiveis = quadros_sempre_visiveis(texto)
    if visiveis:
        falha("quadros-todos-visiveis",
              f"{visiveis['visiveis']} quadros ficam visíveis ao mesmo tempo: `{visiveis['esconde']}` esconde os quadros, "
              f"mas `{visiveis['reexibe']}` declara `display` depois, com peso igual ou maior, e os reexibe. O protótipo vira "
              f"uma rolagem com todas as telas empilhadas, e a navegação parece não funcionar. Esconda os quadros com um "
              f"seletor mais forte que o da moldura (`.quadro-tela:not(.tela-ativa) {{ display: none !important; }}`) ou "
              f"tire o `display` da classe de moldura.")

    rascunhos = sorted(set(m.group(0) for m in _RE_RASCUNHO.finditer(_RE_COMENTARIO.sub(" ", texto))))
    if rascunhos:
        falha("marcador-de-rascunho",
              f"Marcador de rascunho no protótipo ({', '.join(rascunhos[:4])}): o que vai ao QA "
              f"é o que a criança veria.")

    bloqueios = [a for a in achados if a["severidade"] == "bloqueio"]
    status = "bloqueado" if bloqueios else ("amarelo" if achados else "aprovado")
    return {"status": status, "achados": achados, "telas": telas, "declaradas": declaradas}


_RE_ESTILO = re.compile(r"<style\b[^>]*>(.*?)</style>", re.S | re.I)
_RE_REGRA_CSS = re.compile(r"([^{}]+)\{([^{}]*)\}")
#: `.a.b` e `.a:not(.b)` — o conserto que o achado recomenda usa o `:not`
_RE_SO_CLASSES = re.compile(r"^((?:\.[\w-]+)+)((?::not\(\.[\w-]+\))*)$")
_RE_DISPLAY = re.compile(r"(?:^|;)\s*display\s*:\s*([\w-]+)\s*(!\s*important)?", re.I)
_RE_QUADRO = re.compile(r"<[a-z][\w-]*\b[^>]*\bdata-screen-id\s*=[^>]*>", re.I)
_RE_CLASSE_ATTR = re.compile(r"\bclass\s*=\s*[\"']([^\"']*)[\"']", re.I)
_RE_ESTILO_ATTR = re.compile(r"\bstyle\s*=\s*[\"']([^\"']*)[\"']", re.I)


def quadros_sempre_visiveis(html: str) -> Optional[Dict[str, Any]]:
    """O CSS esconde os quadros e outra regra os reexibe: `{visiveis, esconde, reexibe}`, ou None.

    Uma cascata em miniatura, só com seletores de classe (`.a`, `.a.b`): para cada quadro `[data-screen-id]`, a regra
    de `display` que vence — `!important`, depois mais classes, depois a última. Só julga o quadro que alguma regra
    manda esconder: protótipo que esconde pelo JavaScript não tem essa regra, e fica de fora. Na exp03em1b
    (22/10/2026) `.moldura-mobile { display: flex }` vinha depois de `.quadro-tela { display: none }` e as 61 telas
    apareciam juntas.
    """
    css = _RE_COMENTARIO.sub(" ", " ".join(_RE_ESTILO.findall(html or "")))
    regras = []
    for ordem, (seletores, corpo) in enumerate(_RE_REGRA_CSS.findall(css)):
        m = None
        for m in _RE_DISPLAY.finditer(corpo):
            pass  # a última declaração de display do bloco vale
        if not m:
            continue
        for seletor in (s.strip() for s in seletores.split(",")):
            s = _RE_SO_CLASSES.match(seletor)
            if s:
                fora = set(re.findall(r":not\(\.([\w-]+)\)", s.group(2)))
                regras.append({"classes": set(s.group(1)[1:].split(".")), "fora": fora, "seletor": seletor,
                               "valor": m.group(1).lower(), "importante": bool(m.group(2)), "ordem": ordem})
    visiveis, esconde, reexibe = 0, "", ""
    for tag in _RE_QUADRO.findall(html or ""):
        c = _RE_CLASSE_ATTR.search(tag)
        classes = set(c.group(1).split()) if c else set()
        valem = [r for r in regras if r["classes"] <= classes and not r["fora"] & classes]
        oculta = next((r for r in valem if r["valor"] == "none"), None)
        if not oculta:
            continue
        vence = max(valem, key=lambda r: (r["importante"], len(r["classes"]) + len(r["fora"]), r["ordem"]))
        inline = _RE_DISPLAY.search(";" + (_RE_ESTILO_ATTR.search(tag) or [None, ""])[1])
        valor = inline.group(1).lower() if inline and not vence["importante"] else vence["valor"]
        if valor != "none":
            visiveis += 1
            if vence["valor"] != "none" and not reexibe and vence["classes"] != oculta["classes"] | {"tela-ativa"}:
                esconde, reexibe = oculta["seletor"], vence["seletor"]
    if visiveis < 2:
        return None
    return {"visiveis": visiveis, "esconde": esconde or ".quadro-tela", "reexibe": reexibe or "estilo do quadro"}


def relatorio(resultado: Dict[str, Any], missao: str = "") -> str:
    import json
    icone = {"aprovado": "🟢 PROTÓTIPO ÍNTEGRO", "amarelo": "🟡 COM RESSALVAS", "bloqueado": "🔴 BLOQUEADO"}[resultado["status"]]
    linhas = [f"# Lint do protótipo — {missao or 'missão'}", "", f"**Veredito: {icone}**", "",
              f"Telas no arquivo: **{len(resultado['telas'])}**"
              + (f" · declaradas no inventário: **{len(resultado['declaradas'])}**" if resultado["declaradas"] else ""),
              ""]
    if resultado["achados"]:
        linhas += ["## Achados", ""]
        for a in resultado["achados"]:
            marca = "❌" if a["severidade"] == "bloqueio" else "⚠️"
            linhas.append(f"- {marca} **{a['codigo']}** — {a['resumo']}")
    else:
        linhas.append("Nenhum achado: o arquivo abre, tem os identificadores de tela e não traz marcador de rascunho.")
    linhas += ["", "```json", json.dumps(
        {"agente": AGENTE, "missao": missao, "status": resultado["status"], "achados": resultado["achados"]},
        ensure_ascii=False, indent=2), "```"]
    return "\n".join(linhas)
