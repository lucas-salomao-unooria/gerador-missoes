"""Área de PRODUTO — do briefing ao spec fechado da missão.

Ordem (SequentialAgent):
  p0  OnePagerAgent            → one_pager
  ┌─ LoopAgent (≤ N rodadas) ─────────────────────────────────────────┐
  │ p1  GateEstruturalAgent    → gate_estrutural_report               │
  │ p1c GateEstruturalCheck    → gate_estrutural_status (escalate)    │
  │ p1b RevisorOnePagerAgent   → one_pager (corrigido)                │
  └───────────────────────────────────────────────────────────────────┘
  ┌─ ParallelAgent ──────────────────────────────────────────────────┐
  │ p2  AvaliacaoPedagogicaAgent → avaliacao_pedagogica_report       │
  │ p3  ExperienciaAlunoAgent    → experiencia_aluno_report          │
  └───────────────────────────────────────────────────────────────────┘
  p4  GateFinalProdutoAgent    → gate_final_report
  p4c GateFinalCheck           → gate_final_status
  p5  SpecMissaoAgent          → spec_missao   (saída final de Produto)
"""

from __future__ import annotations

import warnings
from typing import Optional

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.loop_agent import LoopAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.sequential_agent import SequentialAgent

from agents.base import create_llm_agent
from agents.callbacks import skip_if_blocked
from agents.checkers import EnvelopeGateAgent
from config import get_settings
from prompts import load_prompt

warnings.filterwarnings("ignore", category=DeprecationWarning, module="google.adk.agents")


def get_one_pager_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="OnePagerAgent",
        description="Normaliza (ou redige) o one-pager da missão a partir do briefing e dos documentos anexados.",
        instruction=load_prompt("produto/p0_one_pager.md"),
        output_key="one_pager",
        include_contents="default",  # único agente que vê a mensagem original e os anexos
        **kw,
    )


def get_gate_estrutural_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="GateEstruturalAgent",
        description="Gate estrutural: completude, ambiente, verbos nativos, logística, evidências e fechamento de spec.",
        instruction=load_prompt("produto/p1_gate_estrutural.md"),
        output_key="gate_estrutural_report",
        **kw,
    )


def get_revisor_one_pager_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="RevisorOnePagerAgent",
        description="Aplica ao one-pager as correções prontas do gate estrutural, sem inventar decisões de produto.",
        instruction=load_prompt("produto/p1b_revisor_one_pager.md"),
        output_key="one_pager",
        **kw,
    )


def get_avaliacao_pedagogica_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="AvaliacaoPedagogicaAgent",
        description="Avaliação pedagógica: descoberta central, papel do professor, BNCC e guardrails éticos.",
        instruction=load_prompt("produto/p2_avaliacao_pedagogica.md"),
        output_key="avaliacao_pedagogica_report",
        before_agent_callback=skip_if_blocked,
        **kw,
    )


def get_experiencia_aluno_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="ExperienciaAlunoAgent",
        description="Experiência do aluno por faixa etária: carga decisória, linguagem, duração e complexidade.",
        instruction=load_prompt("produto/p3_experiencia_aluno.md"),
        output_key="experiencia_aluno_report",
        before_agent_callback=skip_if_blocked,
        **kw,
    )


def get_gate_final_produto_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="GateFinalProdutoAgent",
        description="Gate final de produto: coerência entre missão e vereditos; libera ou bloqueia para design/dev.",
        instruction=load_prompt("produto/p4_gate_final.md"),
        output_key="gate_final_report",
        before_agent_callback=skip_if_blocked,
        **kw,
    )


def get_spec_missao_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="SpecMissaoAgent",
        description="Traduz o one-pager aprovado na especificação de missão (12 blocos) — o contrato da construção.",
        instruction=load_prompt("produto/p5_spec_missao.md"),
        output_key="spec_missao",
        before_agent_callback=skip_if_blocked,
        **kw,
    )


def build_produto_stage(
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
    modo_estrito: Optional[bool] = None,
    max_rodadas: Optional[int] = None,
) -> SequentialAgent:
    """Monta a etapa de Produto como SequentialAgent aninhado."""
    settings = get_settings()
    estrito = settings.produto_modo_estrito if modo_estrito is None else modo_estrito
    rodadas = max(1, max_rodadas or settings.gate_estrutural_max_rodadas)
    kw = {"thinking_budget": thinking_budget, "include_thoughts": include_thoughts}

    gate_loop = LoopAgent(
        name="GateEstruturalLoop",
        description="Gate estrutural ↔ revisor do one-pager até aprovar ou esgotar as rodadas.",
        max_iterations=rodadas,
        sub_agents=[
            get_gate_estrutural_agent(**kw),
            EnvelopeGateAgent(
                name="GateEstruturalCheck",
                description="Lê o envelope do gate estrutural e decide repetir, seguir ou bloquear.",
                rotulo="Gate estrutural",
                report_key="gate_estrutural_report",
                status_key="gate_estrutural_status",
                round_key="gate_estrutural_rodada",
                max_rounds=rodadas,
                escalate_on_approve=True,
                block_pipeline_on_fail=estrito,
            ),
            get_revisor_one_pager_agent(**kw),
        ],
    )

    avaliacoes = ParallelAgent(
        name="AvaliacoesParalelas",
        description="Avaliação pedagógica e experiência do aluno rodam em paralelo sobre a mesma versão da missão.",
        sub_agents=[get_avaliacao_pedagogica_agent(**kw), get_experiencia_aluno_agent(**kw)],
        before_agent_callback=skip_if_blocked,
    )

    return SequentialAgent(
        name="ProdutoStage",
        description="Área de Produto: one-pager → gate estrutural → avaliações → gate final → spec da missão.",
        sub_agents=[
            get_one_pager_agent(**kw),
            gate_loop,
            avaliacoes,
            get_gate_final_produto_agent(**kw),
            EnvelopeGateAgent(
                name="GateFinalProdutoCheck",
                description="Lê o veredito do gate final de produto (🟢 liberada / 🔴 bloqueada).",
                rotulo="Gate final de produto",
                report_key="gate_final_report",
                status_key="gate_final_status",
                block_pipeline_on_fail=estrito,
            ),
            get_spec_missao_agent(**kw),
        ],
    )


PRODUTO_METADATA = [
    {"id": "OnePagerAgent", "name": "P0 · One-pager da missão", "icon": "📝", "output_key": "one_pager", "prompt_file": "produto/p0_one_pager.md", "description": "Normaliza ou redige o one-pager a partir do briefing e dos anexos."},
    {"id": "GateEstruturalAgent", "name": "P1 · Gate estrutural", "icon": "🚧", "output_key": "gate_estrutural_report", "prompt_file": "produto/p1_gate_estrutural.md", "description": "23 critérios: estrutura, ambiente, logística, evidências, viabilidade e infraestrutura."},
    {"id": "GateEstruturalCheck", "name": "P1c · Veredito do gate (determinístico)", "icon": "🔀", "output_key": "gate_estrutural_status", "prompt_file": None, "description": "Lê o envelope JSON e decide repetir, seguir ou bloquear."},
    {"id": "RevisorOnePagerAgent", "name": "P1b · Revisor do one-pager", "icon": "🩹", "output_key": "one_pager", "prompt_file": "produto/p1b_revisor_one_pager.md", "description": "Aplica o complemento pronto-pra-colar do gate; não inventa decisão de produto."},
    {"id": "AvaliacaoPedagogicaAgent", "name": "P2 · Avaliação pedagógica", "icon": "🎓", "output_key": "avaliacao_pedagogica_report", "prompt_file": "produto/p2_avaliacao_pedagogica.md", "description": "BNCC, professor, guardrails e affordance × guardrail (paralelo com P3)."},
    {"id": "ExperienciaAlunoAgent", "name": "P3 · Experiência do aluno", "icon": "🧒", "output_key": "experiencia_aluno_report", "prompt_file": "produto/p3_experiencia_aluno.md", "description": "Carga cognitiva, faixa etária e agência (paralelo com P2)."},
    {"id": "GateFinalProdutoAgent", "name": "P4 · Gate final de produto", "icon": "🏁", "output_key": "gate_final_report", "prompt_file": "produto/p4_gate_final.md", "description": "Coerência entre missão e vereditos; libera ou bloqueia para design/dev."},
    {"id": "GateFinalProdutoCheck", "name": "P4c · Veredito final (determinístico)", "icon": "🔀", "output_key": "gate_final_status", "prompt_file": None, "description": "Lê o envelope do gate final."},
    {"id": "SpecMissaoAgent", "name": "P5 · Spec da missão", "icon": "📜", "output_key": "spec_missao", "prompt_file": "produto/p5_spec_missao.md", "description": "Os 12 blocos da spec — contrato contra o qual design e dev constroem."},
]
