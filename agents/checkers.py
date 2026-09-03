"""Agentes determinísticos (sem LLM) que leem o envelope de um gate e roteiam o pipeline.

`EnvelopeGateAgent` é um BaseAgent que:
  1. lê o relatório gravado em `state[report_key]`;
  2. extrai o envelope JSON e infere o status (aprovado | bloqueado | indefinido);
  3. grava `state[status_key]`, `state[status_key + "_envelope"]` e, se configurado,
     incrementa um contador de rodadas;
  4. quando dentro de um LoopAgent, encerra o loop (escalate) ao aprovar ou ao
     esgotar as rodadas; quando o gate falha em modo estrito, marca o pipeline
     como bloqueado para que os agentes a jusante sejam pulados.
"""

from __future__ import annotations

from typing import AsyncGenerator, Optional

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types
from typing_extensions import override

from .callbacks import (
    KEY_PIPELINE_BLOQUEADO,
    KEY_PIPELINE_MOTIVO,
    STATUS_APROVADO,
    STATUS_BLOQUEADO,
    extrair_envelope,
    inferir_status,
)


class EnvelopeGateAgent(BaseAgent):
    """Lê o veredito de um relatório e decide se o pipeline segue, repete ou para."""

    report_key: str
    status_key: str
    rotulo: str = "Gate"
    round_key: Optional[str] = None
    max_rounds: int = 1
    escalate_on_approve: bool = False
    block_pipeline_on_fail: bool = True
    treat_indefinido_as_blocked: bool = True

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        relatorio = str(state.get(self.report_key, "") or "")
        envelope = extrair_envelope(relatorio)
        status = inferir_status(relatorio, envelope)
        if status not in (STATUS_APROVADO, STATUS_BLOQUEADO):
            status = STATUS_BLOQUEADO if self.treat_indefinido_as_blocked else STATUS_APROVADO

        rodada = int(state.get(self.round_key, 0) or 0) + 1 if self.round_key else 1
        delta = {self.status_key: status, f"{self.status_key}_envelope": envelope or {}}
        if self.round_key:
            delta[self.round_key] = rodada

        esgotou = rodada >= self.max_rounds
        escalate = False
        if status == STATUS_APROVADO:
            msg = f"✅ {self.rotulo}: aprovado" + (f" na rodada {rodada}." if self.round_key else ".")
            escalate = self.escalate_on_approve
        else:
            bloqueia_agora = self.block_pipeline_on_fail and (esgotou or not self.round_key)
            if self.round_key and not esgotou:
                msg = (
                    f"🔁 {self.rotulo}: bloqueado na rodada {rodada}/{self.max_rounds} — "
                    f"o revisor aplicará as correções e o gate será reexecutado."
                )
            elif bloqueia_agora:
                msg = (
                    f"⛔ {self.rotulo}: bloqueado"
                    + (f" após {rodada} rodada(s)" if self.round_key else "")
                    + ". Modo estrito ativo — design e dev não serão executados. "
                    "Veja o alerta e o relatório executivo do gate."
                )
                delta[KEY_PIPELINE_BLOQUEADO] = True
                delta[KEY_PIPELINE_MOTIVO] = f"{self.rotulo} bloqueado"
                escalate = True
            else:
                msg = (
                    f"⚠️ {self.rotulo}: bloqueado"
                    + (f" após {rodada} rodada(s)" if self.round_key else "")
                    + ". Modo estrito desligado — o pipeline segue e o PRD registrará as pendências."
                )
                escalate = bool(self.round_key)

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=msg)]),
            actions=EventActions(state_delta=delta, escalate=escalate or None),
        )
