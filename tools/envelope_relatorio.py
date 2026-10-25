"""O veredito de um gate tem uma fonte só: o `*_status` gravado. Envelope e relatório dizem o mesmo que ele.

Cada gate grava três coisas: o status (`<gate>_status`), o envelope (`<gate>_status_envelope`, com os achados) e o
relatório (`<gate>_report`, que termina no mesmo envelope em JSON). O semáforo e o de acordo leem o status; o dossiê, o
catálogo e o cartão do parecer leem o envelope; quem abre o arquivo lê o relatório. Quando um passo reescreve um dos três
sem os outros, cada leitor vê uma missão diferente:

- 8ce9c32d (exp04ef1b, 25/09/2026, R03 do levantamento de dev de 24/10): o relatório do rastro de lacunas gravado dizia
  🟡 com 1 lacuna; o envelope continuava 🔴 com 4. O dossiê listou as 4, e o catálogo registrou a missão `bloqueada`
  depois do «De acordo para codificação».
- e89e91b3 e 60cfa7f4 (21/10/2026): a linha de base da correção pontual rebaixou a fidelidade a 🟡 no status e no
  envelope, e o relatório seguiu com «**Veredito: 🔴**» no cabeçalho e o envelope antigo no fim
  (`tools/linha_de_base.py` só acrescentava uma nota).

Aqui ficam as duas metades da regra: quem reescreve o envelope reescreve o relatório junto (`relatorio_com_envelope`), e
quem lê o envelope de uma sessão antiga recebe o que concorda com o status (`envelope_do_gate`). Comparação literal sobre
dado estruturado: o status do envelope em JSON, nunca a prosa do relatório.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

#: O relatório de cada gate quando não é `<gate>_report` (o EnvelopeGateAgent lê de um `report_key` com outro nome). Os
#: splits do D0 e do D9 (`lacunas_status`, `ambiente_status`) ficam fora de propósito: o relatório deles é a resposta do
#: agente, com o envelope do agente, e o do gate soma os achados que o código conferiu — divergir ali é o desenho.
RELATORIO_DO_GATE: Dict[str, str] = {
    "design_status": "qa_entregaveis_report",
    "dev_status": "validacao_dev_report",
    "prd_status": "prd_check_report",
    "avaliacao_status": "avaliacao_pedagogica_report",
    "experiencia_status": "experiencia_aluno_report",
}
SEM_RELATORIO_PROPRIO = frozenset({"lacunas_status", "ambiente_status", "completude_status"})

_RE_BLOCO_JSON = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
_RE_VEREDITO = re.compile(r"\*\*Veredito:\s*[^*\n]*\*\*")
_ICONE = {"aprovado": "🟢", "amarelo": "🟡", "bloqueado": "🔴"}


def categoria(valor: Any) -> str:
    """aprovado | amarelo | bloqueado | "" — o status gravado (`*_status`) no mesmo vocabulário do envelope."""
    v = str(valor or "").strip().lower()
    if v in ("bloqueado", "devolvido", "blocked", "reprovado", "vermelho", "🔴"):
        return "bloqueado"
    if v in ("amarelo", "aprovado_com_ressalvas", "apto_com_ressalvas", "ressalvas", "🟡", "parcial"):
        return "amarelo"
    if v in ("aprovado", "apto", "verde", "concluido", "concluído", "🟢"):
        return "aprovado"
    return ""


def categoria_do_envelope(envelope: Optional[Dict[str, Any]]) -> str:
    if not isinstance(envelope, dict) or not envelope:
        return ""
    from agents.callbacks import status_registrado

    return categoria(status_registrado("", envelope))


def relatorio_do_gate(chave_status: str) -> str:
    """A chave do relatório do gate, ou vazio para os gates cujo relatório não carrega o envelope do gate."""
    if chave_status in SEM_RELATORIO_PROPRIO or not chave_status.endswith("_status"):
        return ""
    return RELATORIO_DO_GATE.get(chave_status) or chave_status[: -len("_status")] + "_report"


def _ultimo_envelope(relatorio: str) -> Optional[Dict[str, Any]]:
    from agents.callbacks import extrair_envelope

    return extrair_envelope(relatorio or "")


def concordam(relatorio: str, envelope: Optional[Dict[str, Any]]) -> bool:
    """O último envelope do relatório tem o mesmo veredito que o envelope gravado. Relatório sem envelope não discorda."""
    do_relatorio = _ultimo_envelope(relatorio)
    if do_relatorio is None:
        return True
    return categoria_do_envelope(do_relatorio) == categoria_do_envelope(envelope)


def relatorio_com_envelope(relatorio: str, envelope: Dict[str, Any], nota: str = "") -> str:
    """O relatório com o envelope gravado no lugar do último bloco ```json (ou no fim), a nota antes dele e o cabeçalho
    «**Veredito: …**» trocado quando o veredito do envelope mudou. É o que `tools/juiz_achados.reescrever_relatorio` já
    fazia para o juiz de achados, aqui para todo passo que reescreve o envelope de outro gate."""
    texto = relatorio or ""
    cat = categoria_do_envelope(envelope)
    antigo = _ultimo_envelope(texto)
    if cat and antigo is not None and categoria_do_envelope(antigo) != cat:
        texto = _RE_VEREDITO.sub(f"**Veredito: {_ICONE[cat]} {cat} (revisto — ver a nota no fim)**", texto, count=1)
    novo = "```json\n" + json.dumps(envelope, ensure_ascii=False) + "\n```"
    blocos = [m for m in _RE_BLOCO_JSON.finditer(texto) if _bloco_e_envelope(m.group(1))]
    if blocos:
        ultimo = blocos[-1]
        corpo = texto[: ultimo.start()].rstrip()
        resto = texto[ultimo.end():].strip()
    else:
        corpo, resto = texto.rstrip(), ""
    partes = [corpo]
    if resto:
        partes.append(resto)
    if nota:
        partes.append(nota.strip())
    partes.append(novo)
    return "\n\n".join(p for p in partes if p) + "\n"


def _bloco_e_envelope(bruto: str) -> bool:
    try:
        dado = json.loads(bruto)
    except ValueError:
        return False
    return isinstance(dado, dict) and ("status" in dado or "veredito" in dado)


def envelope_do_gate(state: Dict[str, Any], chave_status: str) -> Dict[str, Any]:
    """O envelope que concorda com o status gravado do gate — o que o dossiê, o catálogo e o cartão devem ler.

    O gravado, quando concorda com o status (o caso de toda sessão desde esta correção). Quando não concorda e o último
    envelope do relatório concorda, o do relatório: é o da sessão em que um passo regravou relatório e status sem o
    envelope (8ce9c32d, 25/09/2026). Nenhum dos dois concordando, o gravado, como antes."""
    gravado = state.get(f"{chave_status}_envelope")
    gravado = gravado if isinstance(gravado, dict) else {}
    status = categoria(state.get(chave_status))
    if not status or categoria_do_envelope(gravado) in ("", status):
        return gravado
    chave_relatorio = relatorio_do_gate(chave_status)
    do_relatorio = _ultimo_envelope(str(state.get(chave_relatorio) or "")) if chave_relatorio else None
    if do_relatorio is not None and categoria_do_envelope(do_relatorio) == status:
        return {**do_relatorio, "envelope_do_relatorio": True}
    return gravado
