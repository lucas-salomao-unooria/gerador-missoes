"""O que o PRD e o handoff afirmam sobre a plataforma existe nela?

A missão do 9º ano (06/10/2026) saiu da esteira com o PRD citando uma "ADR-108 (Proposta)" quando a
última ADR era a 148, o DS "v0.2.2" quando era o 0.2.18, a ponte `@edu/ui/ds-chatgpt` para uma missão
nova, tabelas próprias de enquete e de nota quando a evidência já é genérica, "zerar" que arquiva
sessões quando a plataforma abre rodada, e agendamento que a plataforma não tem. Nenhum gate conferia:
o contrato da plataforma não existia como lista.

Agora existe: o `contrato-plataforma.json` da base fixada na execução (`prompts/base_plataforma.py`),
extraído do código pela própria plataforma. Este módulo confere o texto contra ele, no molde de
`tools/rotas_plataforma.py`. Linha marcada `[PENDÊNCIA PLATAFORMA]` (ou "pendência de plataforma",
"a criar") é pedido à plataforma, não afirmação — não é conferida. Linha que cita a coisa para
proibi-la também não.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List

from prompts import base_plataforma

_RE_PEDIDO = re.compile(r"pend[êe]ncia\s+(de\s+)?plataforma|\[\s*pend|a criar|rota nova|nova rota", re.IGNORECASE)
_RE_PROIBICAO = re.compile(
    r"\bn[ãa]o\s+(?:utiliz|us[ae]|cham|consum|cri[ae]|invent|import|crav|cit)|\bnunca\b|\binexistente|"
    r"\bproibid|\bvedad|\bn[ãa]o existe", re.IGNORECASE)
_RE_ADR = re.compile(r"\bADR-(\d{1,4})\b")
_RE_ADR_PROPOSTA = re.compile(r"\bADR-(\d{1,4})\b[^\n]{0,30}\b(propost|nova|a criar)", re.IGNORECASE)
_RE_PONTE = re.compile(r"@edu/ui/(ds(?:-[a-z]+)?)\b")
_RE_VERSAO_DS = re.compile(
    r"(?:design[- ]system|\bDS\b|@unooria/design-system)[^\n]{0,40}?\bv?\^?(0\.\d+\.\d+)\b", re.IGNORECASE)
_RE_PORTA = re.compile(r"\bporta[^\n]{0,40}?\b(5[12]\d\d)\b|\b(5[12]\d\d)\b[^\n]{0,20}\bporta\b", re.IGNORECASE)
_RE_TABELA_PROPRIA = re.compile(
    r"\b(exp\d{2}(?:ef|em)\d+b_[a-z_]*(?:poll|enquete|respostas|score|pontuac|nota)[a-z_]*)\b", re.IGNORECASE)
_RE_ARQUIVADA = re.compile(r"status\s*=\s*['\"]?arquivad|\bmarca[^\n]{0,40}\barquivad", re.IGNORECASE)
_RE_AGENDA = re.compile(r"\bagend(ar|ad[oa]|amento)\b", re.IGNORECASE)
_RE_JSON = re.compile(r"```json\s*\n(.*?)```", re.DOTALL)
_RE_SUFIXO_DE_INDICE = re.compile(r"_(idx|pkey|fkey|key|por_escola|unique|uniq)$", re.IGNORECASE)
#: Pontes das seções legadas (ADR-133 a 138): existem para as missões antigas, não para missão nova.
PONTES_LEGADAS = {"ds-chatgpt": "ds-unooriaai", "ds-insta": "ds-unoovista", "ds-whatsapp": "ds-unoochat",
                  "ds-unootube": None}


def _linhas_afirmativas(texto: str) -> Iterable[str]:
    for linha in (texto or "").splitlines():
        if _RE_PEDIDO.search(linha) or _RE_PROIBICAO.search(linha):
            continue
        yield linha


def _achado(codigo: str, resumo: str, severidade: str = "bloqueio", etapa: str = "dev") -> Dict[str, str]:
    return {"severidade": severidade, "codigo": codigo, "etapa": etapa, "resumo": resumo}


def _manifestos(texto: str) -> List[Dict[str, Any]]:
    """Blocos JSON do documento que têm cara de `experiencia.json`."""
    encontrados = []
    for bloco in _RE_JSON.findall(texto or ""):
        try:
            dados = json.loads(bloco)
        except json.JSONDecodeError:
            continue
        if isinstance(dados, dict) and "capabilities" in dados and ("series" in dados or "publico" in dados):
            encontrados.append(dados)
    return encontrados


def validar_contrato(texto: str) -> List[Dict[str, str]]:
    """Achados sobre o que o documento afirma da plataforma e o contrato da base desmente."""
    try:
        c = base_plataforma.contrato()
    except base_plataforma.BaseIndisponivel:
        return []
    adr = c.get("adr") or {}
    ultima, proxima = int(adr.get("ultima") or 0), int(adr.get("proxima") or 0)
    ds = c.get("design_system") or {}
    pontes = {str(p.get("ponte") or "").split("/")[-1] for p in ds.get("pontes") or []}
    versao_ds = re.sub(r"[^\d.]", "", str(ds.get("dependencia") or ""))
    portas = {str(v): k for k, v in ((c.get("portas") or {}).get("ocupadas") or {}).items()}
    man = c.get("manifesto") or {}
    achados: List[Dict[str, str]] = []
    vistos: set = set()

    def uma_vez(chave: str, achado: Dict[str, str]) -> None:
        if chave not in vistos:
            vistos.add(chave)
            achados.append(achado)

    for linha in _linhas_afirmativas(texto):
        for m in _RE_ADR_PROPOSTA.finditer(linha):
            n = int(m.group(1))
            if proxima and n != proxima:
                uma_vez(f"adr-proposta-{n}", _achado(
                    "adr-numero-errado",
                    f"`ADR-{n}` aparece como decisão nova, mas a última ADR da plataforma é a {ultima} e a próxima é a "
                    f"**ADR-{proxima}** (contrato da plataforma). A ADR-{n} já existe com outro assunto."))
        for m in _RE_ADR.finditer(linha):
            n = int(m.group(1))
            if ultima and n > proxima:
                uma_vez(f"adr-inexistente-{n}", _achado(
                    "adr-inexistente", f"`ADR-{n}` não existe: a última ADR da plataforma é a {ultima}."))
        for m in _RE_PONTE.finditer(linha):
            ponte = m.group(1)
            if pontes and ponte not in pontes:
                uma_vez(f"ponte-{ponte}", _achado(
                    "ponte-inexistente",
                    f"`@edu/ui/{ponte}` não existe. As pontes da plataforma são: "
                    + ", ".join(f"`@edu/ui/{p}`" for p in sorted(pontes)) + "."))
            elif ponte in PONTES_LEGADAS:
                sucessora = PONTES_LEGADAS[ponte]
                uma_vez(f"ponte-legada-{ponte}", _achado(
                    "ponte-legada",
                    f"`@edu/ui/{ponte}` é a ponte de uma seção legada: missão nova não reproduz a identidade de app de "
                    f"terceiro (ADR-133 a 138)" + (f" e usa `@edu/ui/{sucessora}`" if sucessora else "")
                    + " — veja `ambientes.md`. A legada só por decisão registrada do PO.", etapa="produto"))
        for m in _RE_VERSAO_DS.finditer(linha):
            if versao_ds and m.group(1) != versao_ds:
                uma_vez(f"ds-{m.group(1)}", _achado(
                    "ds-versao-cravada",
                    f"O documento crava o DS em `{m.group(1)}`; a plataforma está em `^{versao_ds}` e segue sempre a "
                    f"última versão publicada (versão única, ADR-139). Não crave número.", severidade="atencao"))
        for m in _RE_PORTA.finditer(linha):
            porta = m.group(1) or m.group(2)
            if porta in portas:
                uma_vez(f"porta-{porta}", _achado(
                    "porta-ocupada",
                    f"A porta {porta} já é da `{portas[porta]}`. A próxima livre é a "
                    f"{(c.get('portas') or {}).get('proxima_livre', '?')} (contrato da plataforma)."))
        for m in _RE_TABELA_PROPRIA.finditer(linha):
            tabela = _RE_SUFIXO_DE_INDICE.sub("", _RE_SUFIXO_DE_INDICE.sub("", m.group(1).lower()))
            uma_vez(f"tabela-{tabela}", _achado(
                "evidencia-tabela-propria",
                f"`{tabela}` guarda enquete ou nota por missão. A evidência pedagógica é genérica (módulo "
                f"`evidencias/`, E14): ficha em `apps/api/src/evidencias/fichas/<expId>.ts`, Canal B pelas rotas "
                f"`/evidencias/:expId/perguntas/:id`. Não crie tabela própria."))
        if _RE_ARQUIVADA.search(linha) and re.search(r"zer|reaplic|reinici|sess", linha, re.IGNORECASE):
            uma_vez("zerar-arquivada", _achado(
                "zerar-arquiva",
                "\"Zerar\" que arquiva sessões não é o modelo da plataforma: zerar abre uma **rodada** nova sem apagar "
                "nada (molde da A Seleção e do Júri, no contrato e nos exemplares)."))
        if _RE_AGENDA.search(linha):
            uma_vez("agendamento", _achado(
                "agendamento-inexistente",
                "A plataforma não tem agendamento: pôr a atividade no ar libera a missão na sala na hora (ADR-146). "
                "Se a missão precisa de agendamento, é `[PENDÊNCIA PLATAFORMA]` com dono."))

    for dados in _manifestos(texto):
        fora = sorted(set(dados) - set(man.get("chaves") or dados))
        if fora:
            uma_vez("manifesto-chaves", _achado(
                "manifesto-chave-inexistente",
                f"O manifesto traz {fora}, que não são chaves de `experiencia.json`. As aceitas são "
                f"{man.get('chaves')} (contrato da plataforma)."))
        for cap in dados.get("capabilities") or []:
            if man.get("capabilities") and cap not in man["capabilities"]:
                uma_vez(f"cap-{cap}", _achado(
                    "manifesto-capability", f"`{cap}` não é capability da plataforma ({man['capabilities']}).",
                    severidade="atencao", etapa="plataforma"))
        for perm in dados.get("permissoes") or []:
            if man.get("permissoes_iframe") and perm not in man["permissoes_iframe"]:
                uma_vez(f"perm-{perm}", _achado(
                    "manifesto-permissao", f"`{perm}` não é permissão de iframe concedida ({man['permissoes_iframe']}).",
                    severidade="atencao", etapa="plataforma"))
    return achados
