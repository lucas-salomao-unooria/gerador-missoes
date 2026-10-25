"""Linha de base da correção pontual: o 🔴 que a correção não causou não é dela. Determinístico.

Numa correção, os gates julgam a missão inteira de novo. Até 19/10/2026 isso fazia a troca de um número sair com
bloqueios que a missão não tinha: o juiz de LLM sorteia outra leitura do mesmo texto, e gate criado depois da geração
julga o que ninguém tocou com regra nova (exp03em1b, 13/10/2026: 🔴 em BNCC e fidelidade; exp03em1b de 14/10: brief e
rastro de 🟢 para 🟡 com a spec 97% igual).

Na correção pontual (`tools/edicao_pontual.py`) se sabe exatamente o que mudou: o texto que as trocas puseram. Então
cada achado bloqueante de cada gate é classificado contra o veredito do mesmo gate antes da correção:

- **da edição** — a citação cai no texto que a correção pôs: bloqueia. É o que a correção quebrou.
- **pré-existente** — o mesmo achado já bloqueava antes: continua bloqueando, marcado. A correção não o causou, e
  rebaixá-lo deixaria passar no *de acordo* um 🔴 que existia (o BNCC das exp03em1b de 14/10).
- **texto inalterado** — a citação cai em texto que a correção não tocou, e o gate não bloqueava por isso antes:
  vira atenção. É ruído do juiz ou regra posterior à versão aprovada; fica à vista no relatório, sem travar.
- **sem citação** — o gate aponta estrutura, não trecho ("o §12a não tem a tabela", "a seção 1.3 não existe"). É da
  correção quando o resumo põe entre aspas um texto que as trocas tiraram ou puseram, ou nomeia a seção ou etapa que
  elas editaram: bloqueia. Senão, **fora da correção**: vira atenção. Foi o que sobrou na reexecução real da exp03em1b
  (19/10/2026): os 10 🔴 vinham de gates criados depois da versão aprovada (comitês, §12a, conta da virada, banca) e
  da seção de DS legada — nenhum ligado às 4 trocas do número.
- **falha de execução** — o juiz não respondeu (`dimensao-ausente`): bloqueia. Não é veredito sobre a missão, mas
  resposta que não chegou não é aprovação.
- **documento novo** — o gate julga um documento que a correção gerou inteiro, porque ele faltava: o one-pager
  pedagógico da missão desenhada antes do PR 10, que o redator escreve na correção pontual de design. Bloqueia, como na
  geração — o texto todo é desta execução, e rebaixá-lo como «trecho que a correção não tocou» aprovaria no de acordo
  de design um documento que ninguém conferiu. Não volta ao editor, que não tem o documento (revisão do PR #79,
  24/10/2026).
"""
from __future__ import annotations

import difflib
import json
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from tools import citacoes
from tools.envelope_relatorio import relatorio_com_envelope, relatorio_do_gate

KEY_LINHA_DE_BASE = "linha_de_base"
KEY_LINHA_DE_BASE_REPORT = "linha_de_base_report"
#: Semelhança mínima entre os resumos para dois achados sem código contarem como o mesmo.
SEMELHANCA_MINIMA = 0.6

DA_EDICAO = "da-edicao"
PRE_EXISTENTE = "pre-existente"
TEXTO_INALTERADO = "texto-inalterado"
FORA_DA_CORRECAO = "fora-da-correcao"
FALHA_DE_EXECUCAO = "falha-de-execucao"
DOCUMENTO_NOVO = "documento-novo"
#: Códigos de achado que dizem que o juiz não respondeu — não são leitura da missão.
CODIGOS_DE_FALHA = frozenset({"dimensao-ausente"})
#: Onde um achado sem citação aponta: "Seção 12a", "§9", "bloco 11", "Etapa 5".
_RE_LUGAR = re.compile(r"(se[cç][aã]o|§|bloco|etapa)\s*(\d+(?:\.\d+)?[a-z]?)", re.I)
_RE_ASPAS = re.compile(r"[«“\"`]([^«»“”\"`]{12,})[»”\"`]")


def capturar(estado: Dict[str, Any], chaves_status: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    """O veredito de cada gate antes da correção: `{status_key: {status, achados}}`. Gate ausente fica de fora."""
    base: Dict[str, Dict[str, Any]] = {}
    for k in chaves_status:
        if not str(k).endswith("_status") or k not in estado:
            continue
        envelope = estado.get(f"{k}_envelope")
        achados = envelope.get("achados") if isinstance(envelope, dict) else None
        base[k] = {"status": str(estado.get(k) or ""),
                   "achados": [a for a in (achados or []) if isinstance(a, dict)]}
    return base


def _norm(texto: str) -> str:
    from tools.fidelidade import _norm as norm

    return norm(texto or "")


def _mesmo_achado(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    codigo_a = str(a.get("codigo") or a.get("id") or "").strip().lower()
    codigo_b = str(b.get("codigo") or b.get("id") or "").strip().lower()
    alvo_a = str(a.get("habilidade") or a.get("classe") or "").strip().lower()
    alvo_b = str(b.get("habilidade") or b.get("classe") or "").strip().lower()
    if codigo_a and codigo_a == codigo_b and alvo_a == alvo_b:
        return True
    ra, rb = _norm(str(a.get("resumo") or ""))[:300], _norm(str(b.get("resumo") or ""))[:300]
    return bool(ra and rb) and difflib.SequenceMatcher(None, ra, rb, autojunk=False).ratio() >= SEMELHANCA_MINIMA


def lugares_editados(anteriores: Dict[str, str], edicoes: Iterable[Dict[str, Any]]) -> set:
    """`{("secao", "9"), ("etapa", "5")…}`: os títulos sob os quais cada troca caiu, na versão anterior."""
    lugares = set()
    for e in edicoes:
        doc = str((anteriores or {}).get(str(e.get("documento") or "")) or "")
        pos = doc.find(str(e.get("de") or "")) if e.get("de") else -1
        if pos < 0:
            continue
        titulos = [l for l in doc[:pos].splitlines() if l.lstrip().startswith("#")]
        trecho = (titulos[-1] if titulos else "") + "\n" + str(e.get("de") or "")
        lugares |= _lugares(trecho)
        for n in re.findall(r"^#+\s*(\d+(?:\.\d+)?[a-z]?)[.\s]", titulos[-1] if titulos else ""):
            lugares.add(("secao", n.lower()))
    return lugares


def _lugares(texto: str) -> set:
    saida = set()
    for tipo, numero in _RE_LUGAR.findall(texto or ""):
        tipo = "etapa" if tipo.lower() == "etapa" else "secao"
        saida.add((tipo, numero.lower()))
    return saida


def classificar(achado: Dict[str, Any], base_do_gate: Optional[Dict[str, Any]], alterado_norm: str,
                lugares: Optional[set] = None) -> str:
    """De onde vem um achado bloqueante — ver o docstring do módulo. `alterado_norm` é o texto que as trocas tiraram
    e puseram, normalizado; `lugares`, as seções e etapas que elas editaram."""
    from tools.fidelidade import _citacao_confere

    cit = citacoes.citacao(achado)
    if cit and alterado_norm and _citacao_confere(cit, alterado_norm):
        return DA_EDICAO
    anteriores = [b for b in ((base_do_gate or {}).get("achados") or []) if citacoes.bloqueante(b)]
    if any(_mesmo_achado(achado, b) for b in anteriores):
        return PRE_EXISTENTE
    if cit and len(cit.split()) >= citacoes.MIN_PALAVRAS:
        return TEXTO_INALTERADO
    if str(achado.get("codigo") or "") in CODIGOS_DE_FALHA:
        return FALHA_DE_EXECUCAO
    resumo = str(achado.get("resumo") or "")
    if alterado_norm and any(_citacao_confere(q, alterado_norm) for q in _RE_ASPAS.findall(resumo)):
        return DA_EDICAO
    if lugares and _lugares(resumo) & lugares:
        return DA_EDICAO
    return FORA_DA_CORRECAO


def aplicar(estado: Dict[str, Any], base: Dict[str, Dict[str, Any]], edicoes: Iterable[Dict[str, Any]],
            chaves_status: Iterable[str], anteriores: Optional[Dict[str, str]] = None,
            gates_de_documento_novo: Iterable[str] = (),
            ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """`(delta, linhas)`: os vereditos reescritos e o que aconteceu com cada achado bloqueante.

    Só rebaixa: nenhum veredito sobe para 🔴 aqui. Gate que perde todos os bloqueios vira 🟡 (`veredito_original`
    guarda o que o juiz deu). Sem bloqueio vivo nas etapas refeitas, a marca de degradação delas cai.
    `gates_de_documento_novo`: os gates de um documento que a correção gerou inteiro — os bloqueios deles ficam
    (`DOCUMENTO_NOVO`).
    """
    novos_docs = set(gates_de_documento_novo)
    chaves_status = list(chaves_status)
    edicoes = [dict(e) for e in edicoes]
    # o que as trocas tiraram e o que puseram: um achado sobre qualquer dos dois é da correção
    alterado_norm = _norm("\n".join(str(e.get(c) or "") for e in edicoes for c in ("de", "para")))
    lugares = lugares_editados(anteriores or {}, edicoes)
    delta: Dict[str, Any] = {}
    linhas: List[Dict[str, Any]] = []
    for k in chaves_status:
        envelope = estado.get(f"{k}_envelope")
        if not isinstance(envelope, dict) or not isinstance(envelope.get("achados"), list):
            continue
        achados = [dict(a) if isinstance(a, dict) else a for a in envelope["achados"]]
        bloqueios = [a for a in achados if isinstance(a, dict) and citacoes.bloqueante(a)]
        if not bloqueios:
            continue
        rebaixados = 0
        for a in bloqueios:
            origem = DOCUMENTO_NOVO if k in novos_docs else classificar(a, base.get(k), alterado_norm, lugares)
            linhas.append({"gate": k, "origem": origem, "codigo": str(a.get("codigo") or a.get("id") or ""),
                           "resumo": str(a.get("resumo") or "")[:240], "antes": (base.get(k) or {}).get("status") or "—"})
            a["linha_de_base"] = origem
            if origem in (TEXTO_INALTERADO, FORA_DA_CORRECAO):
                a["severidade_original"] = a.get("severidade")
                a["severidade"] = "atencao"
                motivo = "trecho inalterado" if origem == TEXTO_INALTERADO else "não ligado às trocas"
                a["resumo"] = f"[não causado pela correção — {motivo}] {a.get('resumo') or ''}".strip()
                rebaixados += 1
        novo = {**envelope, "achados": achados}
        nota = ""
        if rebaixados and rebaixados == len(bloqueios) and str(estado.get(k) or "") == "bloqueado":
            novo.update(status="amarelo", veredito_original=envelope.get("status"))
            delta[k] = "amarelo"
            nota = (f"---\n> 📏 **Linha de base da correção pontual:** {rebaixados} bloqueio(s) não ligados às trocas da "
                    "correção (trecho que ela não tocou, ou regra que este gate não aplicava à versão aprovada) — "
                    "rebaixados a atenção. Veredito: 🟡.")
        relatorio_key = relatorio_do_gate(k)
        if rebaixados and relatorio_key and isinstance(estado.get(relatorio_key), str):
            # O relatório termina no envelope novo e o cabeçalho diz o veredito novo. Até 25/10/2026 só a nota entrava, e
            # a fidelidade de e89e91b3 e 60cfa7f4 seguia «Veredito: 🔴» com o envelope antigo no fim e o status em 🟡
            texto = estado[relatorio_key]
            # e a marca de cada achado rebaixado também: «🔴 **F21**» seguia no corpo da fidelidade de 60cfa7f4 com o achado
            # já em atenção no envelope (F26 em e89e91b3). É a troca que o #84 (C2) faz em `relatorio_rebaixado`, aqui
            # para os dois PRs ficarem com uma regra só (revisão do PR #83, 25/10/2026)
            for a in achados:
                if isinstance(a, dict) and a.get("linha_de_base") in (TEXTO_INALTERADO, FORA_DA_CORRECAO) and a.get("id"):
                    texto = texto.replace(f"🔴 **{a['id']}**", f"🟡 **{a['id']}**")
            delta[relatorio_key] = relatorio_com_envelope(texto, novo, nota)
        elif nota and not relatorio_key and isinstance(estado.get(k[: -len("_status")] + "_report"), str):
            # gate sem relatório próprio (`SEM_RELATORIO_PROPRIO`): o relatório é a resposta do agente, com o envelope
            # dele, e fica; a nota do veredito 🟡 entra no fim, como até 25/10/2026, para relatório e status não divergirem
            chave_nota = k[: -len("_status")] + "_report"
            delta[chave_nota] = estado[chave_nota] + "\n\n" + nota
        delta[f"{k}_envelope"] = novo
    delta.update(_degradacoes_sem_gate_vivo(estado, delta, chaves_status))
    return delta, linhas


#: O veredito do cabeçalho de um relatório de gate: «**Veredito: 🔴** · 55 item(ns)…», «**Veredito: 🔴 CONTRADIZ…**».
_RE_VEREDITO_VERMELHO = re.compile(r"(Veredito:\s*\**\s*)🔴")


def relatorio_rebaixado(relatorio: str, envelope: Dict[str, Any], ids: Iterable[str]) -> str:
    """O relatório com o texto de acordo com o veredito rebaixado: cabeçalho 🟡, a marca de cada achado rebaixado 🟡
    (`🔴 **F21**` → `🟡 **F21**`) e o envelope JSON do fim igual ao do estado.

    Até 25/10/2026 a linha de base só acrescentava a nota no fim: o `fidelidade_status` ficava 🟡 e o relatório que o PO
    abria começava por «**Veredito: 🔴**», com o envelope ainda «bloqueado» (exp02em1b, 60cfa7f4, 23/10; exp01em1b,
    e89e91b3) — o texto contradizia o status (C2)."""
    texto = _RE_VEREDITO_VERMELHO.sub(r"\1🟡", relatorio or "", count=1)
    for i in ids:
        if i:
            texto = texto.replace(f"🔴 **{i}**", f"🟡 **{i}**")
    blocos = list(re.finditer(r"```json\s*(.*?)```", texto, re.S))
    if blocos:
        try:
            dados = json.loads(blocos[-1].group(1))
        except json.JSONDecodeError:
            dados = None
        if isinstance(dados, dict) and "status" in dados:
            ultimo = blocos[-1]
            novo = {**dados, **{k: envelope[k] for k in ("status", "achados", "veredito_original") if k in envelope}}
            texto = (texto[:ultimo.start()] + "```json\n" + json.dumps(novo, ensure_ascii=False, indent=1) + "\n```"
                     + texto[ultimo.end():])
    return texto


def _degradacoes_sem_gate_vivo(estado: Dict[str, Any], delta: Dict[str, Any],
                               chaves_status: List[str]) -> Dict[str, Any]:
    from agents.callbacks import (KEY_AGENTES_DEGRADADOS, KEY_DEGRADACOES, KEY_HERANCA, KEY_PIPELINE_BLOQUEADO,
                                  KEY_PIPELINE_MOTIVO, texto_de_heranca)

    vivos = [k for k in chaves_status if str(delta.get(k, estado.get(k)) or "") == "bloqueado"]
    if vivos or not any(str(estado.get(k) or "") == "bloqueado" for k in chaves_status):
        return {}
    # nenhum gate das etapas refeitas segue 🔴: a reprovação que as marcou caiu com a linha de base
    return {KEY_DEGRADACOES: [], KEY_HERANCA: texto_de_heranca([]), KEY_PIPELINE_BLOQUEADO: False,
            KEY_PIPELINE_MOTIVO: "", KEY_AGENTES_DEGRADADOS: []}


ROTULO_ORIGEM = {DA_EDICAO: "🔴 causado pela correção", PRE_EXISTENTE: "🔴 já bloqueava antes",
                 TEXTO_INALTERADO: "🟡 trecho inalterado — rebaixado",
                 FORA_DA_CORRECAO: "🟡 não ligado às trocas — rebaixado",
                 FALHA_DE_EXECUCAO: "🔴 o juiz não respondeu — mantido",
                 DOCUMENTO_NOVO: "🔴 documento gerado nesta correção — mantido"}


def relatorio(linhas: List[Dict[str, Any]], edicoes_md: str, missao: str = "") -> str:
    """O relatório que o PO lê: o que a correção trocou e de onde veio cada bloqueio."""
    partes = [f"# Linha de base da correção pontual{f' — {missao}' if missao else ''}", "",
              "A correção foi aplicada como edição: os documentos diferem da versão anterior **só** pelas trocas "
              "abaixo. Os gates julgaram a missão inteira; cada bloqueio foi comparado com o veredito do mesmo gate "
              "antes da correção.", "", "## Trocas aplicadas", "", edicoes_md or "Nenhuma troca.", "",
              "## Bloqueios dos gates", ""]
    if not linhas:
        partes.append("Nenhum gate bloqueou.")
    else:
        partes += ["| Gate | Antes | Origem | Achado |", "|---|---|---|---|"]
        for l in linhas:
            resumo = l["resumo"].replace("|", "/").replace("\n", " ")
            partes.append(f"| `{l['gate']}` | {l['antes']} | {ROTULO_ORIGEM.get(l['origem'], l['origem'])} | "
                          f"{(l['codigo'] + ' — ') if l['codigo'] else ''}{resumo} |")
    partes += ["", f"**Bloqueios que a correção pode ter causado:** {len(bloqueios_novos(linhas))}."]
    return "\n".join(partes) + "\n"


def bloqueios_novos(linhas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Os bloqueios que a correção pode ter causado: voltam ao editor no ciclo seguinte."""
    return [l for l in linhas if l["origem"] == DA_EDICAO]
