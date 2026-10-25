"""`RotaDeAchadosAgent`: antes do fim do loop, o achado sobre o conteúdo do one-pager vai ao PO (`tools/rota_achados.py`).

Roda no `SpecLoop` logo antes do `A059SpecCheck`: marca na banca de produto o bloqueio cuja citação é do one-pager e não
da spec, e o `SaidaDeLoopAgent` não devolve ao autor da spec o gate que só reprova por ele (76d9af6e, PED-06,
23/10/2026). O veredito do gate não muda; o relatório e o envelope passam a dizer a rota, juntos
(`tools/envelope_relatorio.py`).
"""
from __future__ import annotations

import copy
from typing import Any, AsyncGenerator, Dict, List

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types
from pydantic import Field
from typing_extensions import override


class RotaDeAchadosAgent(BaseAgent):
    """Determinístico: o bloqueio que cita o one-pager, e não a spec, é marcado para ir ao PO (`rota: po`)."""

    status_keys: List[str] = Field(default_factory=list)
    #: O documento de quem decide (o one-pager) e o do autor do loop (a spec).
    dono_key: str = "one_pager"
    autor_key: str = "spec_missao"

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from tools import rota_achados
        from tools.envelope_relatorio import relatorio_com_envelope, relatorio_do_gate

        state = ctx.session.state
        dono = str(state.get(self.dono_key) or "")
        autor = str(state.get(self.autor_key) or "")
        delta: Dict[str, Any] = {}
        linhas: List[str] = []
        for chave in self.status_keys:
            envelope = state.get(f"{chave}_envelope")
            if not isinstance(envelope, dict):
                continue
            envelope = copy.deepcopy(envelope)
            marcados = rota_achados.marcar(envelope, dono, autor)
            if not marcados:
                continue
            delta[f"{chave}_envelope"] = envelope
            relatorio_key = relatorio_do_gate(chave)
            if isinstance(state.get(relatorio_key), str):
                nota = ("---\n> 🧑 **Rota dos achados:** " + ", ".join(
                    f"`{a.get('id') or a.get('codigo') or 'achado'}`" for a in marcados)
                    + " cita(m) o one-pager, e a spec não pode contrariá-lo: vai(ão) ao PO no parecer de produto "
                    "(Refazer com a mudança), não ao autor da spec. O veredito do gate não muda.")
                delta[relatorio_key] = relatorio_com_envelope(state[relatorio_key], envelope, nota)
            sobra = len(rota_achados.bloqueios_do_autor(envelope))
            linhas.append(f"🧑 `{chave}`: {len(marcados)} bloqueio(s) sobre o conteúdo do one-pager vão ao PO; "
                          f"{sobra} ficam com o autor da spec.")
        if not delta:
            return
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    content=types.Content(role="model", parts=[types.Part(text="\n".join(linhas))]),
                    actions=EventActions(state_delta=delta))
