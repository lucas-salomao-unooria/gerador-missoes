"""Callbacks e utilitários determinísticos do pipeline.

- Leitura do envelope JSON de roteamento (references/contrato-saida.md) que os gates
  devolvem ao final do relatório.
- `skip_if_blocked`: before_agent_callback que pula um agente (ou um container inteiro)
  quando o pipeline foi bloqueado por um gate de produto em modo estrito.
"""

from __future__ import annotations

import json
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
        if status in ("aprovado", "concluido", "concluído", "liberada", "apto", "verde", "🟢"):
            return STATUS_APROVADO
        if status in ("bloqueado", "bloqueada", "devolvido", "nao_apto", "não apto", "vermelho", "🔴"):
            return STATUS_BLOQUEADO
        if status in ("apto_com_ressalvas", "ressalvas", "amarelo", "🟡"):
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
