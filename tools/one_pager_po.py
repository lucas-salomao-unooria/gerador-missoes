"""O one-pager que o PO anexou é a missão: a esteira completa e confere, não redesenha.

Até 08/10/2026, um one-pager anexado a uma conversa nova só chegava ao núcleo narrativo (o único agente que
lê a mensagem): as seções de apoio, os revisores e os pareceres trabalhavam sobre o que a esteira tinha
escrito, e nada comparava o resultado com o que o PO mandou. O reprocessamento da exp06ef1b pediu "não
alterar a narrativa, o mecanismo e a estrutura" e saiu com 261 de 307 trechos do PO trocados — a Etapa 5
virou outro mecanismo, os tempos mudaram, o podcast e o Canal B foram reescritos —, todos os gates 🟢.

Aqui a conferência é de fato, trecho a trecho, como `tools/preservacao.py` faz no design: cada linha (e cada
célula de tabela) com conteúdo do one-pager do PO está no gerado — igual, ou com 85% dos trigramas. Saem
da conta só duas coisas, e as duas em código:

- a habilidade que o pedido manda remover (a linha que a cita pode sumir);
- a alteração que o autor declara na tabela «Alterações sobre o one-pager do PO» citando, entre aspas,
  o trecho do pedido que a manda fazer — a citação é conferida no briefing e nos pedidos.

O que um parecer ou gate achar que deve mudar não entra na conta: vira `[PROPOSTA — validar com PO: …]`
ao lado do texto do PO, que fica. Quem decide é o PO.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Set

from tools.preservacao import _RE_MARCADOR, _trigramas
from tools.preservacao import _norm as _norm_base

AGENTE = "one-pager-do-po"
MIN_PALAVRAS = 6
FRACAO = 0.85
#: Um anexo é one-pager canônico quando traz ao menos tantas seções numeradas distintas, entre elas a 4.
SECOES_MINIMAS = 8
TITULO_ALTERACOES = "Alterações sobre o one-pager do PO"
#: Teto de trechos listados por seção no relatório: o autor recebe a contagem inteira e os primeiros
#: de cada seção, que bastam para ele achar o que reescreveu.
MAX_POR_SECAO = 15

_RE_DOC = re.compile(r"^### 📄 [^\n]*$", re.M)
_RE_SECAO_NUMERADA = re.compile(r"^#{1,4}\s*(\d{1,2})[a-z]?\.\s", re.M)
_RE_TITULO = re.compile(r"^#{1,4}\s+(.+?)\s*$")
_RE_SEPARADOR = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")
_RE_VERSAO = re.compile(r"\bv\d+(?:\.\d+)+\b")
_RE_CODIGO = re.compile(r"\bE[FM]\d{2}[A-Z]{2}\d{2,3}\b")
_RE_REMOVER = re.compile(r"remov|desvincul|exclu|retir|tirar|tire\b|descart|sem a habilidade", re.IGNORECASE)
#: Seções do gerado que não contam como presença: o changelog e a própria tabela de alterações citam o
#: texto do PO, e colar o trecho ali não pode valer como preservá-lo.
_RE_SECAO_NAO_CONTA = re.compile(r"o que mudou|changelog|altera[çc][õo]es sobre o one-pager", re.IGNORECASE)
_RE_ASPAS = re.compile(r"[«“\"]([^«»“”\"]{12,})[»”\"]")


def _norm(texto: str) -> str:
    return _norm_base(_RE_VERSAO.sub("vX", texto or ""))


def extrair(material: str) -> str:
    """O one-pager canônico entre os anexos (`material_anexado`), sem o cabeçalho do anexo; "" se nenhum.

    A apostila do bimestre vem no mesmo material: só conta o anexo com as seções numeradas do formato
    canônico (ao menos `SECOES_MINIMAS`, entre elas a 4 — as etapas). Havendo dois, vale o mais completo.
    """
    texto = material or ""
    inicios = [m.start() for m in _RE_DOC.finditer(texto)] or [0]
    melhor, melhor_n = "", 0
    for i, ini in enumerate(inicios):
        fim = inicios[i + 1] if i + 1 < len(inicios) else len(texto)
        bloco = texto[ini:fim]
        numeros = {int(n) for n in _RE_SECAO_NUMERADA.findall(bloco) if int(n) <= 18}
        if len(numeros) >= SECOES_MINIMAS and 4 in numeros and len(numeros) > melhor_n:
            melhor, melhor_n = _RE_DOC.sub("", bloco, count=1).strip(), len(numeros)
    return melhor


def _linhas_por_secao(doc: str):
    """(seção, linha) de cada linha do documento, pulando o que não é conteúdo da missão."""
    secao, pular = "", False
    for linha in (doc or "").splitlines():
        m = _RE_TITULO.match(linha)
        if m:
            secao = m.group(1).strip()
            pular = bool(_RE_SECAO_NAO_CONTA.search(secao))
            continue
        if pular or _RE_SEPARADOR.match(linha) or "data:image" in linha:
            continue
        yield secao, linha


def unidades(doc: str) -> List[Dict[str, str]]:
    """Os trechos a preservar: cada linha com conteúdo e, nas tabelas, cada célula.

    Célula, não linha: o docx do PO vira tabela markdown com outro alinhamento, e a mesma linha de
    tabela raramente sai idêntica; a célula sai. A linha inteira vai junto para a regra de remoção
    (a célula do Canal B de uma habilidade removida não cita o código, a linha cita).
    """
    saida: List[Dict[str, str]] = []
    for secao, linha in _linhas_por_secao(doc):
        if _RE_MARCADOR.search(linha):  # lacuna que o PO deixou aberta: fechá-la é trabalho da esteira
            continue
        partes = linha.split("|") if linha.strip().startswith("|") else [linha]
        for parte in partes:
            if len(_norm(parte).split()) >= MIN_PALAVRAS:
                saida.append({"secao": secao, "texto": parte.strip(), "linha": linha})
    return saida


def _ancoras_faltando(trecho: str, palavras_novo: Set[str]) -> List[str]:
    """Números e nomes próprios do trecho que não estão no gerado.

    A régua de 85% dos trigramas existe porque o docx do PO e o markdown da esteira formatam diferente (na
    v1.5.2 da exp06ef1b, a correspondência exata dava 3 falsos positivos e a de 85%, nenhum). Mas ela deixa
    passar a troca de uma palavra no fim da linha — "Bia e Rafa" virando "Bia e Tiago". Na correspondência
    aproximada, então, o que carrega a decisão — número e nome — tem de continuar no documento.
    """
    tokens = re.findall(r"\w+", trecho or "")
    ancoras = [t for i, t in enumerate(tokens) if t.isdigit() or (i > 0 and t[:1].isupper() and len(t) >= 3)]
    return [a for a in ancoras if _norm(a) not in palavras_novo]


def _sem_secoes_que_nao_contam(doc: str) -> str:
    return "\n".join(linha for _, linha in _linhas_por_secao(doc))


def codigos_retirados(texto: str) -> Set[str]:
    """Habilidades que o texto manda tirar: o código aparece numa frase com verbo de remoção."""
    frases = re.split(r"(?<=[.!?\n])\s+", texto or "")
    return {c for f in frases if _RE_REMOVER.search(f) for c in _RE_CODIGO.findall(f)}


def codigos_removidos(po: str, briefing: str = "", pedidos: str = "") -> Set[str]:
    """Habilidades do one-pager do PO que o pedido manda tirar."""
    return codigos_retirados(f"{briefing}\n{pedidos}") & set(_RE_CODIGO.findall(po or ""))


def alteracoes_declaradas(gerado: str) -> List[Dict[str, str]]:
    """As linhas da tabela «Alterações sobre o one-pager do PO»: trecho do PO, como ficou, pedido citado."""
    dentro, saida = False, []
    for linha in (gerado or "").splitlines():
        m = _RE_TITULO.match(linha)
        if m:
            dentro = TITULO_ALTERACOES.lower() in m.group(1).lower()
            continue
        if not dentro or not linha.strip().startswith("|") or _RE_SEPARADOR.match(linha):
            continue
        celulas = [c.strip() for c in linha.strip().strip("|").split("|")]
        if len(celulas) >= 3 and not re.match(r"trecho", celulas[0], re.IGNORECASE):
            saida.append({"trecho": celulas[0], "ficou": celulas[1], "pedido": celulas[-1]})
    return saida


def _parecido(a_norm: str, b_norm: str) -> bool:
    if not a_norm or not b_norm:
        return False
    if a_norm in b_norm or b_norm in a_norm:
        return True
    ta = _trigramas(a_norm)
    return bool(ta) and len(ta & _trigramas(b_norm)) / len(ta) >= FRACAO


def _pedido_confere(celula: str, fonte: str) -> Optional[str]:
    """A citação do pedido na célula, se ela existe no briefing ou nos pedidos do PO."""
    from tools.fidelidade import _citacao_confere
    from tools.fidelidade import _norm as norm_cit

    fonte_norm = norm_cit(fonte)
    for citacao in _RE_ASPAS.findall(celula or ""):
        if len(citacao.split()) >= 4 and _citacao_confere(citacao, fonte_norm):
            return citacao
    return None


def conferir(po: str, gerado: str, briefing: str = "", pedidos: str = "") -> Dict[str, Any]:
    """Cada trecho do one-pager do PO está no gerado, ou saiu por ordem do pedido conferida em código."""
    vazio = {"total": 0, "perdidas": [], "removidas": 0, "declaradas": 0, "codigos_removidos": []}
    # Sem one-pager não há o que conferir — e o autor ficou mudo. Com ou sem anexo do PO, isso reprova, para o loop
    # chamá-lo de novo: na exp03ef1b (08/10/2026) o A014 terminou sem texto duas vezes e o gate estrutural quebrou.
    if not (gerado or "").strip():
        return {**vazio, "status": "bloqueado", "aplica": bool((po or "").strip()),
                "achados": [{"severidade": "bloqueio", "codigo": "one-pager-vazio", "etapa": "produto",
                             "resumo": "O one-pager gerado está vazio: o autor terminou sem texto. Escreva o one-pager inteiro."}]}
    if not (po or "").strip():
        return {**vazio, "status": "aprovado", "aplica": False, "achados": []}

    novo = _norm(_sem_secoes_que_nao_contam(gerado))
    tri_novo = _trigramas(novo)
    removidos = codigos_removidos(po, briefing, pedidos)
    fonte = f"{briefing}\n{pedidos}"
    declaradas = alteracoes_declaradas(gerado)
    validas = [_norm(d["trecho"]) for d in declaradas if _pedido_confere(d["pedido"], fonte)]
    sem_prova = [d for d in declaradas if not _pedido_confere(d["pedido"], fonte)]

    palavras_novo = set(re.findall(r"\w+", novo))
    todas = unidades(po)
    perdidas: List[Dict[str, str]] = []
    n_removidas = n_declaradas = 0
    for u in todas:
        n = _norm(u["texto"])
        if n in novo:
            continue
        tri = _trigramas(n)
        if tri and len(tri & tri_novo) / len(tri) >= FRACAO and not _ancoras_faltando(u["texto"], palavras_novo):
            continue
        if removidos and set(_RE_CODIGO.findall(u["linha"])) & removidos:
            n_removidas += 1
            continue
        if any(_parecido(n, t) for t in validas):
            n_declaradas += 1
            continue
        perdidas.append(u)

    achados: List[Dict[str, str]] = []
    por_secao: Dict[str, List[str]] = {}
    for u in perdidas:
        por_secao.setdefault(u["secao"] or "(sem título)", []).append(u["texto"])
    for secao, textos in por_secao.items():
        lista = "\n".join(f"    - «{t[:300]}»" for t in textos[:MAX_POR_SECAO])
        mais = f"\n    - … e mais {len(textos) - MAX_POR_SECAO}" if len(textos) > MAX_POR_SECAO else ""
        achados.append({
            "severidade": "bloqueio", "codigo": "trecho-do-po-perdido", "etapa": "produto",
            "agente_responsavel": "one-pager",
            "resumo": (f"§ «{secao}»: {len(textos)} trecho(s) do one-pager do PO sumiram ou foram reescritos. "
                       f"Devolva cada um como o PO escreveu, no mesmo lugar:\n{lista}{mais}"),
        })
    for d in sem_prova:
        achados.append({
            "severidade": "bloqueio", "codigo": "alteracao-sem-pedido", "etapa": "produto",
            "agente_responsavel": "one-pager",
            "resumo": (f"A alteração «{d['trecho'][:160]}» → «{d['ficou'][:160]}» não cita, entre aspas, um trecho que "
                       "exista no pedido do PO. Sem o pedido, devolva o texto do PO e, se achar que precisa mudar, "
                       "escreva ao lado `[PROPOSTA — validar com PO: …]`."),
        })
    return {"status": "bloqueado" if achados else "aprovado", "aplica": True, "achados": achados,
            "total": len(todas), "perdidas": perdidas, "removidas": n_removidas, "declaradas": n_declaradas,
            "codigos_removidos": sorted(removidos)}


def relatorio(resultado: Dict[str, Any], missao: str = "") -> str:
    titulo = f"# One-pager do PO × one-pager gerado — {missao or 'missão'}"
    if not resultado.get("aplica") and resultado["status"] == "aprovado":
        return "\n".join([titulo, "", "**Veredito: 🟢 NÃO SE APLICA**", "",
                          "Nenhum anexo traz um one-pager no formato canônico: a missão nasce do briefing.", "",
                          "```json", json.dumps({"agente": AGENTE, "missao": missao, "status": "aprovado",
                                                 "achados": []}, ensure_ascii=False), "```"])
    icone = ("🟢 PRESERVA O ONE-PAGER DO PO" if resultado["status"] == "aprovado"
             else "🔴 ONE-PAGER VAZIO" if any(a["codigo"] == "one-pager-vazio" for a in resultado["achados"])
             else "🔴 REESCREVEU O ONE-PAGER DO PO")
    total, perdidas = resultado["total"], len(resultado["perdidas"])
    preservados = total - perdidas - resultado["removidas"] - resultado["declaradas"]
    removidos = ", ".join(resultado["codigos_removidos"]) or "nenhuma habilidade"
    linhas = [titulo, "", f"**Veredito: {icone}**", "",
              f"Trechos do PO: **{total}** · preservados: **{preservados}** · removidos pelo pedido ({removidos}): "
              f"**{resultado['removidas']}** · alterados com o pedido citado: **{resultado['declaradas']}** · "
              f"perdidos: **{perdidas}**", "",
              "O one-pager que o PO anexou é a missão aprovada. Só muda o que o pedido dele manda mudar — e cada "
              f"mudança vai para a tabela «{TITULO_ALTERACOES}» com o trecho do pedido entre aspas. O que um parecer "
              "ou gate sugerir fica como `[PROPOSTA — validar com PO: …]` ao lado do texto do PO, que não sai.", ""]
    if resultado["achados"]:
        linhas += ["## Achados", ""] + [f"- ❌ **{a['codigo']}** — {a['resumo']}" for a in resultado["achados"]]
    envelope = [{k: (v.split("\n")[0] if k == "resumo" else v) for k, v in a.items()} for a in resultado["achados"]]
    linhas += ["", "```json", json.dumps({"agente": AGENTE, "missao": missao, "status": resultado["status"],
                                          "achados": envelope}, ensure_ascii=False, indent=2), "```"]
    return "\n".join(linhas)
