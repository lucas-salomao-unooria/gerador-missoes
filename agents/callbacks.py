"""Callbacks e utilitários determinísticos do pipeline.

- Leitura do envelope JSON de roteamento (references/contrato-saida.md) que os gates
  devolvem ao final do relatório.
- `skip_if_blocked`: before_agent_callback que pula um agente (ou um container inteiro)
  quando o pipeline foi bloqueado por um gate de produto em modo estrito.
- `limitar_resposta_de_ferramenta` / `barrar_ferramenta_sem_orcamento`: contenção do
  que as ferramentas MCP devolvem ao contexto do turno. Sem elas, um agente de design
  que constrói um board no FigJam acumula dezenas de respostas de `use_figma`, o dump
  de `get_figjam` e a imagem de `get_screenshot` — tudo no MESMO turno, porque o
  histórico de chamada de ferramenta não é conversa e `include_contents="none"` não o
  descarta. Foi assim que o D2 estourou o teto de 1.048.576 tokens do Gemini com um
  prompt de 22 KB.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

from google.adk.agents.callback_context import CallbackContext
from google.genai import types

# Chaves de estado usadas pelo controle de fluxo
KEY_PIPELINE_BLOQUEADO = "pipeline_bloqueado"
KEY_PIPELINE_MOTIVO = "pipeline_bloqueio_motivo"

_JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)

STATUS_APROVADO = "aprovado"
STATUS_BLOQUEADO = "bloqueado"
STATUS_INDEFINIDO = "indefinido"

_APROVADO_TOKENS = ("🟢", "APROVADO", "LIBERADA PARA DESIGN/DEV", "APTO PARA CODIFICAR", "APROVADO PARA REVISÃO HUMANA")
_BLOQUEADO_TOKENS = ("🔴", "BLOQUEADO", "BLOQUEADA PARA DESIGN/DEV", "NÃO APTO", "IMPASSE")


def extrair_envelope(texto: str) -> Optional[Dict[str, Any]]:
    """Retorna o último bloco ```json {...}``` do texto como dict (ou None)."""
    if not texto:
        return None
    matches = _JSON_BLOCK_RE.findall(texto)
    for raw in reversed(matches):
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and ("status" in data or "veredito" in data):
                return data
        except json.JSONDecodeError:
            continue
    return None


def inferir_status(texto: str, envelope: Optional[Dict[str, Any]] = None) -> str:
    """Normaliza o veredito de um relatório em aprovado | bloqueado | indefinido."""
    if envelope:
        status = str(envelope.get("status") or envelope.get("veredito") or "").strip().lower()
        if status in ("aprovado", "concluido", "concluído", "liberada", "apto", "passa", "verde", "🟢"):
            return STATUS_APROVADO
        if status in ("bloqueado", "bloqueada", "devolvido", "nao_apto", "não apto", "nao_passa", "não passa", "vermelho", "🔴", "aguarda_gate"):
            return STATUS_BLOQUEADO
        if status in ("apto_com_ressalvas", "ressalvas", "amarelo", "🟡"):
            return STATUS_APROVADO
        # D0 (fecha-lacunas): segue | segue_com_pendencias · D9 (ambiente-simulado): dormente | existente | novo
        if status in ("segue", "segue_com_pendencias", "dormente", "existente", "novo", "nao_aplicavel", "não aplicável"):
            return STATUS_APROVADO
    cabecalho = (texto or "")[:1500].upper()
    if any(tok in cabecalho for tok in _BLOQUEADO_TOKENS):
        return STATUS_BLOQUEADO
    if any(tok in cabecalho for tok in _APROVADO_TOKENS):
        return STATUS_APROVADO
    return STATUS_INDEFINIDO


def skip_if_blocked(callback_context: CallbackContext) -> Optional[types.Content]:
    """before_agent_callback: pula o agente/container quando o pipeline está bloqueado."""
    if callback_context.state.get(KEY_PIPELINE_BLOQUEADO):
        motivo = callback_context.state.get(KEY_PIPELINE_MOTIVO, "gate de produto bloqueado")
        return types.Content(
            role="model",
            parts=[
                types.Part(
                    text=(
                        f"⏭️ `{callback_context.agent_name}` não executado — "
                        f"pipeline bloqueado ({motivo})."
                    )
                )
            ],
        )
    return None


def extrair_slug(one_pager: str) -> str:
    """Procura um slug `exp-NN-nome` no one-pager/spec; vazio se não houver."""
    if not one_pager:
        return ""
    m = re.search(r"\bexp-(?:\d{2,3}|xx)-[a-z0-9][a-z0-9-]*", one_pager, re.IGNORECASE)
    return m.group(0).lower() if m else ""


# --------------------------------------------------------------------- MCP: contenção
logger = logging.getLogger("callbacks")

#: Teto por STRING dentro da resposta de uma ferramenta.
MCP_STRING_MAX = 6_000
#: Teto para a resposta inteira de UMA chamada, já podada.
MCP_RESPOSTA_MAX = 24_000
#: Orçamento acumulado de resposta de ferramenta POR AGENTE. O Gemini aceita ~1M
#: tokens; isto reserva a maior parte para a instrução e para a saída.
MCP_ORCAMENTO_POR_AGENTE = 600_000

_BASE64_LONGO = re.compile(r"^[A-Za-z0-9+/=\s]{2000,}$")
_CHAVES_DE_MIDIA = ("inlinedata", "inline_data", "mimetype", "mime_type", "imagedata", "image_data", "base64")


def _chave_de_midia(chave: str) -> bool:
    return chave.lower().replace("-", "_") in _CHAVES_DE_MIDIA or "screenshot" in chave.lower()


def _podar(valor: Any, chave: str = "") -> Any:
    """Poda recursiva: imagem vira aviso, string longa é truncada, estrutura é preservada."""
    if isinstance(valor, str):
        if _BASE64_LONGO.match(valor) or (_chave_de_midia(chave) and len(valor) > 512):
            return (
                f"<captura de {len(valor)} caracteres removida do contexto. A chamada FUNCIONOU e o nó existe no "
                "arquivo — é isso que a captura prova. A imagem em si não é lida pelo modelo (chega como texto "
                "codificado), então a conferência VISUAL é do revisor humano: registre no relatório o que ele deve "
                "olhar, e não peça a captura de novo.>"
            )
        if len(valor) > MCP_STRING_MAX:
            return valor[:MCP_STRING_MAX] + f"\n…[cortado: mais {len(valor) - MCP_STRING_MAX} caracteres]"
        return valor
    if isinstance(valor, dict):
        return {k: _podar(v, str(k)) for k, v in valor.items()}
    if isinstance(valor, list):
        podada = [_podar(v, chave) for v in valor[:50]]
        if len(valor) > 50:
            podada.append(f"…[cortado: mais {len(valor) - 50} itens]")
        return podada
    return valor


def _tamanho(obj: Any) -> int:
    try:
        return len(json.dumps(obj, ensure_ascii=False, default=str))
    except Exception:
        return len(str(obj))


def _chave_do_orcamento(agent_name: str) -> str:
    # `temp:` não é persistido no estado da sessão nem salvo nos artefatos.
    return f"temp:mcp_gasto_{agent_name}"


def limitar_resposta_de_ferramenta(tool: Any, args: Dict[str, Any], tool_context: Any, tool_response: Any) -> Optional[Dict[str, Any]]:
    """after_tool_callback: poda a resposta e debita o orçamento do agente.

    Devolver um dict SUBSTITUI o que o modelo recebe. Imagem nunca volta ao contexto:
    o agente já a viu quando a pediu, e reenviá-la custa o turno inteiro.
    """
    bruto = _tamanho(tool_response)
    resposta = _podar(tool_response) if bruto > MCP_STRING_MAX else tool_response

    if _tamanho(resposta) > MCP_RESPOSTA_MAX:
        texto = json.dumps(resposta, ensure_ascii=False, default=str)[:MCP_RESPOSTA_MAX]
        resposta = {
            "resposta_truncada": True,
            "motivo": (
                f"A resposta de `{getattr(tool, 'name', 'ferramenta')}` tinha {bruto} caracteres e não cabe no contexto. "
                "Trabalhe com o trecho abaixo; não peça a mesma leitura de novo."
            ),
            "trecho": texto,
        }

    gasto = int(tool_context.state.get(_chave_do_orcamento(tool_context.agent_name), 0) or 0) + _tamanho(resposta)
    tool_context.state[_chave_do_orcamento(tool_context.agent_name)] = gasto
    if bruto > MCP_RESPOSTA_MAX:
        logger.info(
            "%s: resposta de %s podada de %d para %d caracteres (gasto acumulado: %d)",
            tool_context.agent_name, getattr(tool, "name", "?"), bruto, _tamanho(resposta), gasto,
        )
    return resposta if resposta is not tool_response else None


def barrar_ferramenta_sem_orcamento(tool: Any, args: Dict[str, Any], tool_context: Any) -> Optional[Dict[str, Any]]:
    """before_tool_callback: quando o orçamento do agente acaba, recusa e manda concluir.

    Devolver um dict PULA a ferramenta. É melhor o agente entregar o markdown com o
    board pela metade do que a execução inteira morrer com 400 do modelo.
    """
    gasto = int(tool_context.state.get(_chave_do_orcamento(tool_context.agent_name), 0) or 0)
    if gasto < MCP_ORCAMENTO_POR_AGENTE:
        return None
    logger.warning("%s: orçamento de MCP esgotado (%d caracteres) — recusando %s", tool_context.agent_name, gasto, getattr(tool, "name", "?"))
    return {
        "recusado": True,
        "motivo": (
            "Orçamento de contexto desta etapa esgotado: as respostas de ferramenta já somam "
            f"{gasto} caracteres. **Pare de chamar ferramentas agora** e entregue o documento "
            "em Markdown com o que já foi construído, declarando no relatório o que ficou por fazer "
            "no arquivo e por quê."
        ),
    }
