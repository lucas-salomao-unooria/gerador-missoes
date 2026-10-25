"""One-pager do PO grande demais para ser reescrito: o documento é montado por código, e o modelo devolve só as trocas.

Teste de ponta a ponta de 25/10/2026, 3ef2b: o one-pager do PO tem 360 mil caracteres (≈107 mil tokens), mais do que o
modelo devolve numa resposta. O A014 o reescrevia inteiro e era cortado sempre perto de 218 mil caracteres, no §9a ou
no §12a; a conferência acusava «399 trechos do PO perdidos», o retrabalho pedia de novo a reescrita inteira, e o A037
(«perdeu 979 trechos») fazia o mesmo. Nenhuma reescrita integral podia dar certo, e o comitê dos canais rodava até o teto.

Com o one-pager do PO acima de `tools.contexto.SAIDA_SEGURA`, quem escreve o `one_pager` — seções de apoio (A014),
revisores (A028, A034) e restaurador (A037) — não o reescreve:

- **o código monta a base**: o one-pager do PO (ou o da rodada anterior), com as seções 0, 1, 3 e 4 copiadas do
  núcleo narrativo e a 18-parcial do núcleo no fim da seção 18 — o que o A014 fazia à mão («copiado do núcleo — não
  alterar»), agora sem erro de cópia;
- **o modelo devolve só trocas**, no formato de `tools/edicao_pontual.py`, pelo editor de trocas (o mesmo da correção
  pontual e do retrabalho dos loops), com a tarefa do papel e os relatórios que ele lia;
- **o código aplica** as trocas que se aplicam e respeitam o one-pager do PO (`tools.one_pager_po.perdidos_pela_edicao`);
  a que não se aplica vira pendência à vista do PO, `[ABERTO — dono: PO: …]` no fim da seção 18, sem decidir por ele.

O texto do PO não passa pelo modelo, então não pode ser cortado nem parafraseado. Com o one-pager do PO que cabe (os das
15 missões do acervo e das 3 normais do e2e, de 12 a 71 mil caracteres) nada aqui roda.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Optional, Tuple

from tools.contexto import grande

#: Os papéis que escrevem o `one_pager`, e o fragmento de prompt com a tarefa de cada um.
PAPEIS = {
    "secoes_apoio": "produto/_one_pager_por_trocas_secoes_apoio.md",
    "revisor": "produto/_one_pager_por_trocas_revisor.md",
    "restaurador": "produto/_one_pager_por_trocas_restaurador.md",
}
#: As seções do núcleo narrativo, que o one-pager traz «exatamente como estão no núcleo» (`014_secoes_apoio.md`).
SECOES_DO_NUCLEO = (0, 1, 3, 4)
TITULO_NUCLEO_18 = "Decisões e propostas do núcleo narrativo (18-parcial)"
TITULO_PENDENCIAS = "Trocas da esteira que não se aplicaram — para o PO decidir"
#: As trocas que não se aplicaram, para o diagnóstico: `[{papel, motivo, de, para, falha}]`.
KEY_TROCAS_NAO_APLICADAS = "trocas_nao_aplicadas"

_RE_TITULO = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.M)
_RE_NUMERO = re.compile(r"^(\d{1,2})(?:[a-z])?(-parcial)?(?=[.\s—–-]|$)", re.I)
_RE_BRIEF = re.compile(r"^(?:#{1,6}\s*|\*\*)\s*MISS[ÃA]O DIGITAL UNOORIA\s*·\s*BRIEFING DE ESCOPO[^\n]*", re.M)


def por_trocas(state: Mapping[str, Any]) -> bool:
    """O one-pager desta missão é montado por trocas: o do PO não cabe numa resposta do modelo."""
    return grande(str(state.get("one_pager_po") or ""))


# ------------------------------------------------------------------ seções numeradas
def _chave(titulo: str) -> Optional[str]:
    m = _RE_NUMERO.match(titulo.strip("*_ "))
    if not m:
        return None
    return f"{int(m.group(1))}{'-parcial' if m.group(2) else ''}"


def blocos(texto: str) -> Dict[str, Tuple[int, int]]:
    """`{seção: (início, fim)}` das seções numeradas de nível 1 e 2, antes do brief de escopo.

    A seção vai do primeiro título com o número até o próximo título de nível 1 ou 2 que não seja dela: «## 0.1 A ideia»
    e «## 0.2 …» são da seção 0 (one-pager da 3ef2b); «## 18-parcial» é seção própria; «## Histórico de versões» e o
    brief encerram a anterior. Os títulos do brief («# 1. O QUE É ESTA MISSÃO», no one-pager da 1em1b) não contam."""
    texto = texto or ""
    m_brief = _RE_BRIEF.search(texto)
    limite = m_brief.start() if m_brief else len(texto)
    titulos = [(m.start(), len(m.group(1)), m.group(2)) for m in _RE_TITULO.finditer(texto) if m.start() < limite]
    saida: Dict[str, Tuple[int, int]] = {}
    atual: Optional[str] = None
    inicio = 0
    for ini, nivel, titulo in titulos:
        if nivel > 2:
            continue
        chave = _chave(titulo)
        if chave == atual and chave is not None:
            continue
        if atual is not None and atual not in saida:
            saida[atual] = (inicio, ini)
        atual, inicio = chave, ini
    if atual is not None and atual not in saida:
        saida[atual] = (inicio, limite)
    return saida


def _trocar_bloco(texto: str, chave: str, novo: str) -> str:
    ini, fim = blocos(texto)[chave]
    return texto[:ini] + novo.rstrip() + "\n\n" + texto[fim:].lstrip("\n")


def _rebaixar(texto: str) -> str:
    """Um nível a mais em cada título: a 18-parcial entra como subseção da 18."""
    return _RE_TITULO.sub(lambda m: f"#{m.group(1)} {m.group(2)}" if len(m.group(1)) < 6 else m.group(0), texto)


def _subsecao(texto: str, titulo: str, ini_secao: int, fim_secao: int) -> Optional[Tuple[int, int]]:
    """`(início, fim)` da subseção «### <titulo>» dentro de [ini_secao, fim_secao): até o próximo título de nível ≤ 3."""
    for m in _RE_TITULO.finditer(texto, ini_secao, fim_secao):
        if len(m.group(1)) == 3 and m.group(2).strip("*_ ") == titulo:
            prox = next((x.start() for x in _RE_TITULO.finditer(texto, m.end(), fim_secao) if len(x.group(1)) <= 3),
                        fim_secao)
            return m.start(), prox
    return None


def _no_fim_da_18(texto: str, titulo: str, corpo: str) -> str:
    """A subseção «### <titulo>» com `corpo` no fim da seção 18 (trocada, se já existe). Sem seção 18, antes do brief ou
    no fim do documento."""
    bloco = f"### {titulo}\n\n{corpo.strip()}\n\n"
    b = blocos(texto)
    if "18" in b:
        ini, fim = b["18"]
        existente = _subsecao(texto, titulo, ini, fim)
        if existente:
            return texto[:existente[0]] + bloco + texto[existente[1]:]
        return texto[:fim].rstrip() + "\n\n" + bloco + texto[fim:]
    m = _RE_BRIEF.search(texto)
    fim = m.start() if m else len(texto)
    return texto[:fim].rstrip() + "\n\n" + bloco + texto[fim:]


def sincronizar_com_nucleo(base: str, nucleo: str) -> str:
    """A base com as seções 0, 1, 3 e 4 do núcleo e a 18-parcial dele no fim da seção 18.

    Seção que o núcleo não tem fica como está na base. É o que o A014 fazia — «trazendo as seções 0, 1, 3 e 4 exatamente
    como estão no núcleo» e incorporando a 18-parcial na 18 —, por código: o núcleo da 3ef2b tem só a seção 4 com 97 mil
    caracteres, e a cópia à mão era onde o corte caía."""
    texto = base or ""
    nucleo = nucleo or ""
    b_nucleo = blocos(nucleo)
    for n in SECOES_DO_NUCLEO:
        chave = str(n)
        if chave in b_nucleo and chave in blocos(texto):
            ini, fim = b_nucleo[chave]
            texto = _trocar_bloco(texto, chave, nucleo[ini:fim])
    if "18-parcial" in b_nucleo:
        ini, fim = b_nucleo["18-parcial"]
        corpo = nucleo[ini:fim]
        corpo = corpo[corpo.find("\n") + 1:] if "\n" in corpo else ""  # sem o título da 18-parcial
        if corpo.strip():
            texto = _no_fim_da_18(texto, TITULO_NUCLEO_18, _rebaixar(corpo))
    return texto


# ------------------------------------------------------------------ a base e as pendências
def base_do_papel(state: Mapping[str, Any], papel: str) -> str:
    """O documento sobre o qual as trocas do papel são feitas.

    As seções de apoio partem do one-pager da rodada anterior (ou, na primeira, do one-pager do PO) com o núcleo de agora;
    revisor e restaurador, do one-pager como está."""
    atual = str(state.get("one_pager") or "")
    po = str(state.get("one_pager_po") or "")
    if papel == "secoes_apoio":
        return sincronizar_com_nucleo(atual if atual.strip() else po, str(state.get("nucleo_narrativo") or ""))
    return atual if atual.strip() else po


def _sem_colchete(texto: str, limite: int = 200) -> str:
    """Trecho para dentro de um marcador `[ABERTO — …]`: uma linha, sem colchetes (fechariam o marcador)."""
    t = re.sub(r"\s+", " ", texto or "").strip().replace("[", "(").replace("]", ")")
    return t[:limite] + ("…" if len(t) > limite else "")


def linha_de_pendencia(papel: str, motivo: str, de: str, para: str, falha: str) -> str:
    return (f"- [ABERTO — dono: PO: a esteira ({papel}) quis trocar «{_sem_colchete(de)}» por «{_sem_colchete(para)}»"
            f"{' — ' + _sem_colchete(motivo, 240) if motivo else ''}, e a troca não se aplicou ({_sem_colchete(falha, 240)}). "
            "O texto ficou como estava; decida se a mudança entra]")


def linha_do_editor(papel: str, pendencia: str) -> str:
    """O que o editor não pôs numa troca e devolveu como pendência (conflito com regra, decisão do PO)."""
    return (f"- [ABERTO — dono: PO: {_sem_colchete(pendencia, 400)} — a esteira ({papel}) não aplicou; decida se a mudança "
            "entra]")


def com_pendencias(texto: str, linhas: List[str]) -> str:
    """O documento com as pendências no fim da seção 18, sem repetir as que já estão lá."""
    if not linhas:
        return texto
    b = blocos(texto)
    existentes: List[str] = []
    if "18" in b:
        sub = _subsecao(texto, TITULO_PENDENCIAS, *b["18"])
        if sub:
            existentes = [l for l in texto[sub[0]:sub[1]].splitlines() if l.startswith("- [ABERTO")]
    todas = list(dict.fromkeys(existentes + linhas))
    return _no_fim_da_18(texto, TITULO_PENDENCIAS, "\n".join(todas))


# ------------------------------------------------------------------ o pedido ao editor
_INSUMOS = {
    "secoes_apoio": (("Briefing e pedido do PO", "briefing"),
                     ("Comitê dos canais — painel A (rodada anterior)", "comite_canal_a_report"),
                     ("Comitê dos canais — painel B (rodada anterior)", "comite_canal_b_report"),
                     ("Comitê final (rodada anterior)", "comite_final_report"),
                     ("Contrato de evidência do one-pager (§12a), conferido em código", "evidencia_one_pager_report"),
                     ("Conferência do one-pager do PO na rodada anterior", "one_pager_po_report")),
    "revisor": (("Briefing e pedido do PO", "briefing"),
                ("Relatório do gate estrutural", "gate_estrutural_report"),
                ("Contrato de plataforma e origem dos parâmetros", "contrato_produto_report"),
                ("Parecer de adequação pedagógica", "adequacao_report"),
                ("Avaliação pedagógica", "avaliacao_pedagogica_report"),
                ("Experiência do estudante", "experiencia_aluno_report")),
    "restaurador": (("Briefing e pedido do PO", "briefing"),
                    ("Conferência — one-pager do PO × one-pager atual", "one_pager_po_report"),
                    ("Comitê dos canais — painel A", "comite_canal_a_report"),
                    ("Comitê dos canais — painel B", "comite_canal_b_report"),
                    ("Comitê final", "comite_final_report")),
}


def _perdidos_por_extenso(state: Mapping[str, Any], documento: str) -> str:
    """Os trechos do PO que faltam no documento, cada um com a linha inteira do PO: o relatório da conferência corta os
    longos, e o restaurador copia do PO, não da lista."""
    from tools.one_pager_po import conferir

    po = str(state.get("one_pager_po") or "")
    if not po.strip() or not documento.strip():
        return ""
    pedidos = "\n".join(str(p.get("texto") or "") for p in state.get("pedidos_do_po") or [] if isinstance(p, dict))
    from tools.comite import texto_votos

    resultado = conferir(po, documento + "\n\n" + str(state.get("brief_escopo") or ""), str(state.get("briefing") or ""),
                         pedidos, texto_votos(dict(state)))
    linhas, vistas = [], set()
    for u in resultado.get("perdidas") or []:
        if u["linha"] in vistas:
            continue
        vistas.add(u["linha"])
        linhas.append(f"- seção «{u['secao'] or '(sem título)'}»: {u['linha'].strip()}")
    return "\n".join(linhas)


def pedido(state: Mapping[str, Any], papel: str, base: str, motivos: str = "") -> str:
    """O pedido ao editor de trocas: as regras comuns, a tarefa do papel e os relatórios que o autor lia."""
    from prompts import load_prompt
    from tools.contexto import estimar_tokens

    insumos = []
    for rotulo, chave in _INSUMOS[papel]:
        texto = str(state.get(chave) or "").strip()
        if texto:
            insumos.append(f"### {rotulo}\n\n{texto}")
    if papel == "restaurador":
        perdidos = _perdidos_por_extenso(state, base)
        if perdidos:
            insumos.append("### Os trechos do PO que faltam, por extenso (copie daqui, letra por letra)\n\n" + perdidos)
    for rotulo, chave in (("Pedido de correção desta execução", "pedido_correcao"),
                          ("Notas de passagem desta missão", "notas_de_passagem")):
        texto = str(state.get(chave) or "").strip()
        if texto:
            insumos.append(f"### {rotulo}\n\n{texto}")
    if motivos.strip():
        insumos.append("### O que os gates reprovaram na rodada anterior (retrabalho)\n\n" + motivos.strip())
    return load_prompt("produto/_one_pager_por_trocas.md",
                       tarefa_do_papel=load_prompt(PAPEIS[papel]),
                       tamanho_do_po=f"{estimar_tokens(str(state.get('one_pager_po') or '')):,}".replace(",", "."),
                       insumos_do_papel="\n\n".join(insumos) or "(nenhum relatório nesta rodada)")
