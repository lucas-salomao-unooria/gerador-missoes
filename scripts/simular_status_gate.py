"""Script de simulação para extração e inferência de status no pipeline.

Valida o comportamento de:
1. extrair_envelope() e inferir_status() em agents/callbacks.py
2. Retorno exato para as strings e envelopes solicitados
3. Interpretação pelo pipeline ("aprovado", "bloqueado" ou "indefinido")
4. Comportamento do EnvelopeGateAgent com treat_indefinido_as_blocked=True
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# Garante que a raiz do repositório está no sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Configura variáveis de ambiente antes de carregar o ADK
os.environ.setdefault("FIGMA_MCP_MODE", "off")
os.environ.setdefault("GOOGLE_API_KEY", "teste-simulacao")

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.events import Event, EventActions
from google.adk.runners import InMemoryRunner
from google.genai import types
from typing_extensions import override

from agents.callbacks import (
    KEY_PIPELINE_BLOQUEADO,
    KEY_PIPELINE_MOTIVO,
    STATUS_APROVADO,
    STATUS_BLOQUEADO,
    STATUS_INDEFINIDO,
    _APROVADO_TOKENS,
    _BLOQUEADO_TOKENS,
    extrair_envelope,
    inferir_status,
    marcar_heranca,
)
from agents.checkers import EnvelopeGateAgent


class FakeAgent(BaseAgent):
    """Agente fake para simular produtor de relatório ou agente a jusante."""

    key: str
    text: str
    executou: bool = False

    @override
    async def _run_async_impl(self, ctx: InvocationContext):
        self.executou = True
        delta = {self.key: self.text}
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=f"Executou {self.name}")]),
            actions=EventActions(state_delta=delta),
        )


async def executar_runner(root_agent: BaseAgent, initial_state: dict | None = None):
    """Executa a árvore de agentes com InMemoryRunner e retorna (events, state)."""
    runner = InMemoryRunner(agent=root_agent, app_name="simulacao_gate")
    session = await runner.session_service.create_session(
        app_name="simulacao_gate",
        user_id="user_test",
        session_id="session_test",
        state=initial_state or {},
    )
    events = []
    async for ev in runner.run_async(
        user_id="user_test",
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text="iniciar")]),
    ):
        events.append(ev)
    final_session = await runner.session_service.get_session(
        app_name="simulacao_gate",
        user_id="user_test",
        session_id=session.id,
    )
    return events, dict(final_session.state)


def main():
    print("=" * 80)
    print("SIMULAÇÃO DE EXTRAÇÃO E INFERÊNCIA DE STATUS (agents/callbacks.py)")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # 1. Definição dos Casos de Teste Solicitados
    # -------------------------------------------------------------------------
    status_str = "aprovado_com_ressalvas"
    cabecalho_solicitado = "Gate Final de Produto — exp-01 v1\n**Veredito: 🟡 LIBERADA COM RESSALVAS**"
    envelope_solicitado = {"status": "aprovado_com_ressalvas"}

    print("\n[1] ENTRADAS DO TESTE SOLICITADAS:")
    print(f"  • status string : {status_str!r}")
    print(f"  • cabeçalho     :\n{cabecalho_solicitado}")
    print(f"  • envelope dict : {envelope_solicitado}")

    # -------------------------------------------------------------------------
    # 2. Teste de extrair_envelope()
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("PARTE 1: TESTE DE extrair_envelope()")
    print("=" * 80)

    texto_com_bloco_json = f"""{cabecalho_solicitado}

## Cobertura (F1)
Cobertura estrutural e pedagógica validada.

```json
{{
  "agente": "gate-final-produto",
  "status": "aprovado_com_ressalvas"
}}
```
"""
    env_extraido = extrair_envelope(texto_com_bloco_json)
    print(f"Input text com bloco json -> extrair_envelope()")
    print(f"Resultado retornado: {env_extraido}")
    assert env_extraido == {"agente": "gate-final-produto", "status": "aprovado_com_ressalvas"}
    print("-> extrair_envelope() extraiu com sucesso o bloco ```json ```.")

    # -------------------------------------------------------------------------
    # 3. Teste exato de inferir_status()
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("PARTE 2: RETORNO EXATO DE inferir_status()")
    print("=" * 80)

    # Cenário A: Apenas o envelope {"status": "aprovado_com_ressalvas"} sem texto
    ret_env_only = inferir_status(texto="", envelope=envelope_solicitado)
    print(f"A) inferir_status(texto='', envelope={envelope_solicitado}):")
    print(f"   -> Retorno exato: {ret_env_only!r}")

    # Cenário B: Apenas o cabeçalho solicitado, sem envelope
    ret_cab_only = inferir_status(texto=cabecalho_solicitado, envelope=None)
    print(f"\nB) inferir_status(texto=cabecalho_solicitado, envelope=None):")
    print(f"   -> Retorno exato: {ret_cab_only!r}")

    # Cenário C: Cabeçalho solicitado + envelope solicitado juntos
    ret_cab_e_env = inferir_status(texto=cabecalho_solicitado, envelope=envelope_solicitado)
    print(f"\nC) inferir_status(texto=cabecalho_solicitado, envelope={envelope_solicitado}):")
    print(f"   -> Retorno exato: {ret_cab_e_env!r}")

    # Cenário D: Relatório realista (> 1500 caracteres, json no final conforme p4_gate_final.md)
    corpo_longo = "\n## Detalhes da Avaliação\n" + ("Análise técnica e pedagógica sem termos-chave...\n" * 35)
    relatorio_realista = f"{cabecalho_solicitado}\n{corpo_longo}\n```json\n{{\"agente\": \"gate-final-produto\", \"status\": \"aprovado_com_ressalvas\"}}\n```"
    env_realista = extrair_envelope(relatorio_realista)
    ret_realista = inferir_status(texto=relatorio_realista, envelope=env_realista)
    print(f"\nD) inferir_status(texto=relatorio_realista (>1500 chars), envelope=env_realista):")
    print(f"   Tamanho total do relatório: {len(relatorio_realista)} caracteres")
    print(f"   Tamanho analisado para cabeçalho: 1500 caracteres")
    print(f"   -> Retorno exato: {ret_realista!r}")

    # Cenário E: Caso incidental (relatório muito curto < 1500 chars onde o JSON fica dentro do cabeçalho)
    ret_curto = inferir_status(texto=texto_com_bloco_json, envelope=env_extraido)
    print(f"\nE) inferir_status(texto=relatorio_curto (<1500 chars), envelope=env_extraido):")
    print(f"   Tamanho total: {len(texto_com_bloco_json)} caracteres")
    print(f"   -> Retorno exato: {ret_curto!r}")
    print(f"   * Nota técnica: No cenário E, o retorno é 'aprovado' apenas porque o JSON no final")
    print(f"     está dentro dos primeiros 1500 caracteres e contém a substring 'aprovado'")
    print(f"     em 'aprovado_com_ressalvas'. No cabeçalho real ou em relatórios normais (>1500 chars),")
    print(f"     o retorno é estritamente 'indefinido'.")

    # Comparativo de tokens
    print("\n--- POR QUE OCORRE A FALHA NA INFERÊNCIA? ---")
    print("1. Na verificação de ENVELOPE:")
    print("   Status aceitos para aprovação em callbacks.py (linhas 59-67):")
    print("     - ('aprovado', 'concluido', 'concluído', 'liberada', 'apto', 'passa', 'verde', '🟢')")
    print("     - ('apto_com_ressalvas', 'ressalvas', 'amarelo', '🟡')")
    print("     - ('segue', 'segue_com_pendencias', 'dormente', 'existente', 'novo', 'nao_aplicavel', 'não aplicável')")
    print("   -> 'aprovado_com_ressalvas' NÃO está em nenhuma dessas tuplas!")
    print("\n2. No fallback de CABEÇALHO:")
    print(f"   _BLOQUEADO_TOKENS = {_BLOQUEADO_TOKENS}")
    print(f"   _APROVADO_TOKENS  = {_APROVADO_TOKENS}")
    print("   No cabeçalho 'Gate Final de Produto — exp-01 v1\\n**Veredito: 🟡 LIBERADA COM RESSALVAS**':")
    print("     - Nenhum token de bloqueio está presente.")
    print("     - Nenhum token de aprovação está presente:")
    print("       * '🟡' não está em _APROVADO_TOKENS (apenas '🟢')")
    print("       * 'APROVADO' não aparece como palavra no cabeçalho")
    print("       * 'LIBERADA PARA DESIGN/DEV' não bate (o texto tem 'LIBERADA COM RESSALVAS')")
    print("   -> Portanto, a inferência resulta em: STATUS_INDEFINIDO ('indefinido').")

    # -------------------------------------------------------------------------
    # 4. Demonstração de Interpretação pelo Pipeline
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("PARTE 3: DEMONSTRAÇÃO DA INTERPRETAÇÃO PELO PIPELINE")
    print("=" * 80)
    print("A função inferir_status() pode retornar:")
    print("  • STATUS_APROVADO  = 'aprovado'")
    print("  • STATUS_BLOQUEADO = 'bloqueado'")
    print("  • STATUS_INDEFINIDO = 'indefinido'")
    print("\nComo o pipeline interpreta esse veredito?")
    print("Em agents/checkers.py (linhas 76-78 do EnvelopeGateAgent):")
    print("  status = inferir_status(relatorio, envelope)")
    print("  if status not in (STATUS_APROVADO, STATUS_BLOQUEADO):")
    print("      status = STATUS_BLOQUEADO if self.treat_indefinido_as_blocked else STATUS_APROVADO")
    print("\nPortanto:")
    print("  - Quando status é 'indefinido':")
    print("    • Com treat_indefinido_as_blocked=True  => interpretado como 'bloqueado'")
    print("    • Com treat_indefinido_as_blocked=False => interpretado como 'aprovado'")

    # -------------------------------------------------------------------------
    # 5. Execução do EnvelopeGateAgent com treat_indefinido_as_blocked=True
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("PARTE 4: COMPORTAMENTO DO EnvelopeGateAgent (treat_indefinido_as_blocked=True)")
    print("=" * 80)

    async def executar_simulacao_gate():
        # Testamos o cenário em que o relatório emite o cabeçalho e envelope solicitados
        relatorio_gate = relatorio_realista

        # Cenário 1: treat_indefinido_as_blocked = True (comportamento padrão)
        print("\n>>> EXECUÇÃO CENÁRIO 1: treat_indefinido_as_blocked = True (Padrão do Pipeline)")
        fake_gate_p4 = FakeAgent(
            name="A11GateFinalProduto",
            key="gate_final_report",
            text=relatorio_gate,
        )
        check_p4_bloqueante = EnvelopeGateAgent(
            name="A12GateFinalProdutoCheck",
            rotulo="Gate Final de Produto",
            report_key="gate_final_report",
            status_key="gate_final_status",
            block_pipeline_on_fail=True,
            treat_indefinido_as_blocked=True,
        )
        jusante_design = FakeAgent(
            name="DesignStage",
            key="design_output",
            text="Artefatos de design gerados com sucesso",
            before_agent_callback=marcar_heranca,
        )

        pipeline_bloqueado = SequentialAgent(
            name="PipelineProdutoDesign",
            sub_agents=[fake_gate_p4, check_p4_bloqueante, jusante_design],
        )

        events_1, state_1 = await executar_runner(pipeline_bloqueado)

        print("\n[Status Final no Session State]")
        print(f"  • gate_final_status        : {state_1.get('gate_final_status')!r}")
        print(f"  • gate_final_status_envelope: {state_1.get('gate_final_status_envelope')}")
        print(f"  • pipeline_bloqueado       : {state_1.get(KEY_PIPELINE_BLOQUEADO)!r}")
        print(f"  • pipeline_bloqueio_motivo  : {state_1.get(KEY_PIPELINE_MOTIVO)!r}")
        print(f"  • Agente DesignStage rodou?: {'design_output' in state_1} (esperado: False, pois foi pulado)")

        print("\n[Eventos emitidos pelo Runner]")
        for ev in events_1:
            if ev.content and ev.content.parts:
                for part in ev.content.parts:
                    if part.text:
                        print(f"   [{ev.author}]: {part.text.strip()}")

        # Cenário 2: treat_indefinido_as_blocked = False (para demonstração comparativa)
        print("\n" + "-" * 70)
        print(">>> EXECUÇÃO CENÁRIO 2: treat_indefinido_as_blocked = False (Comparativo)")
        fake_gate_p4_2 = FakeAgent(
            name="A11GateFinalProduto",
            key="gate_final_report",
            text=relatorio_gate,
        )
        check_p4_permissivo = EnvelopeGateAgent(
            name="A12GateFinalProdutoCheck",
            rotulo="Gate Final de Produto",
            report_key="gate_final_report",
            status_key="gate_final_status",
            block_pipeline_on_fail=True,
            treat_indefinido_as_blocked=False,
        )
        jusante_design_2 = FakeAgent(
            name="DesignStage",
            key="design_output",
            text="Artefatos de design gerados com sucesso",
            before_agent_callback=marcar_heranca,
        )

        pipeline_permissivo = SequentialAgent(
            name="PipelineProdutoDesign2",
            sub_agents=[fake_gate_p4_2, check_p4_permissivo, jusante_design_2],
        )

        events_2, state_2 = await executar_runner(pipeline_permissivo)

        print("\n[Status Final no Session State]")
        print(f"  • gate_final_status        : {state_2.get('gate_final_status')!r}")
        print(f"  • pipeline_bloqueado       : {state_2.get(KEY_PIPELINE_BLOQUEADO)!r}")
        print(f"  • Agente DesignStage rodou?: {'design_output' in state_2} (esperado: True)")

        print("\n[Eventos emitidos pelo Runner]")
        for ev in events_2:
            if ev.content and ev.content.parts:
                for part in ev.content.parts:
                    if part.text:
                        print(f"   [{ev.author}]: {part.text.strip()}")

    asyncio.run(executar_simulacao_gate())

    print("\n" + "=" * 80)
    print("CONCLUSÃO GERAL DA SIMULAÇÃO")
    print("=" * 80)
    print("1. extrair_envelope() funciona perfeitamente para extrair o bloco JSON.")
    print("2. inferir_status() retorna 'indefinido' porque:")
    print("   - 'aprovado_com_ressalvas' não consta nas palavras-chave do envelope;")
    print("   - '🟡 LIBERADA COM RESSALVAS' não bate com _APROVADO_TOKENS.")
    print("3. O pipeline interpreta o status 'indefinido' através do EnvelopeGateAgent.")
    print("4. Com treat_indefinido_as_blocked=True:")
    print("   - O status é forçado para 'bloqueado';")
    print("   - pipeline_bloqueado é setado para True;")
    print("   - O fluxo é escalado e os agentes a jusante (DesignStage) são PULADOS (marcar_heranca).")
    print("=" * 80)


if __name__ == "__main__":
    main()
