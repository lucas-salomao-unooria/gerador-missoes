"""Área de PRODUTO — do briefing ao spec fechado da missão.

Ordem (SequentialAgent):
  ┌─ LoopAgent (≤ 2 rodadas) ─────────────────────────────────────────┐
  │ p0a NucleoNarrativoAgent   → nucleo_narrativo                     │
  │ p0mg MicroGateAgent        → micro_gate_report                    │
  │ p0mgc MicroGateCheck       → micro_gate_status (escalate)         │
  └───────────────────────────────────────────────────────────────────┘
  p0b SecoesApoioAgent         → one_pager  (núcleo + seções 2, 5–18 + brief)
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

# O prompt do micro-gate fixa o teto em 2 rodadas: na segunda reprovação o problema é de
# mecanismo, não de redação, e o relatório sai com `precisa_humano`.
MICRO_GATE_MAX_RODADAS = 2


def get_nucleo_narrativo_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="NucleoNarrativoAgent",
        description="Núcleo narrativo da missão (seções 0, 1, 3 e 4): descoberta central, gap de informação, escolha significativa e as 6 etapas.",
        instruction=load_prompt("produto/p0a-nucleo-narrativo-unooria.md"),
        output_key="nucleo_narrativo",
        include_contents="default",  # único agente que vê a mensagem original e os anexos
        **kw,
    )


def get_micro_gate_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="MicroGateAgent",
        description="Micro-gate do núcleo: spoiler (4 padrões), gap de informação real, escolha significativa e job-to-be-done no Desafiar.",
        instruction=load_prompt("produto/p0-micro-gate-unooria.md"),
        output_key="micro_gate_report",
        **kw,
    )


def get_secoes_apoio_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="SecoesApoioAgent",
        description="Seções de apoio (2 e 5–18) e brief de escopo sobre o núcleo aprovado: completa o one-pager canônico que o gate estrutural audita.",
        instruction=load_prompt("produto/p0b-secoes-apoio-unooria.md"),
        output_key="one_pager",
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

    nucleo_loop = LoopAgent(
        name="NucleoNarrativoLoop",
        description="Núcleo narrativo ↔ micro-gate de spoiler/gap até passar ou esgotar as rodadas.",
        max_iterations=MICRO_GATE_MAX_RODADAS,
        sub_agents=[
            get_nucleo_narrativo_agent(**kw),
            get_micro_gate_agent(**kw),
            EnvelopeGateAgent(
                name="MicroGateCheck",
                description="Lê o envelope do micro-gate: aprovado segue para as seções de apoio, reprovado devolve o núcleo ao P0a.",
                rotulo="Micro-gate do núcleo",
                report_key="micro_gate_report",
                status_key="micro_gate_status",
                round_key="micro_gate_rodada",
                max_rounds=MICRO_GATE_MAX_RODADAS,
                escalate_on_approve=True,
                # Quem bloqueia a missão é o gate estrutural (P1). O micro-gate esgotado
                # segue adiante com o achado registrado — o problema é de mecanismo e o P1 o audita.
                block_pipeline_on_fail=False,
            ),
        ],
    )

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
        description="Área de Produto: núcleo narrativo ↔ micro-gate → seções de apoio → gate estrutural → avaliações → gate final → spec da missão.",
        sub_agents=[
            nucleo_loop,
            get_secoes_apoio_agent(**kw),
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
    {"id": "NucleoNarrativoAgent", "name": "P0a · Núcleo narrativo", "icon": "🎬", "output_key": "nucleo_narrativo", "prompt_file": "produto/p0a-nucleo-narrativo-unooria.md", "description": "Seções 0, 1, 3 e 4 a partir do briefing e dos anexos: descoberta, narrativa e as 6 etapas."},
    {"id": "MicroGateAgent", "name": "P0mg · Micro-gate do núcleo", "icon": "🕵️", "output_key": "micro_gate_report", "prompt_file": "produto/p0-micro-gate-unooria.md", "description": "Spoiler, gap de informação, escolha significativa e job-to-be-done — binário, até 2 rodadas."},
    {"id": "MicroGateCheck", "name": "P0mgc · Veredito do micro-gate (determinístico)", "icon": "🔀", "output_key": "micro_gate_status", "prompt_file": None, "description": "Lê o envelope do micro-gate e decide se o núcleo volta ao P0a ou segue."},
    {"id": "SecoesApoioAgent", "name": "P0b · Seções de apoio e brief", "icon": "📝", "output_key": "one_pager", "prompt_file": "produto/p0b-secoes-apoio-unooria.md", "description": "Completa o one-pager canônico (seções 2 e 5–18) e o brief de escopo sobre o núcleo aprovado."},
    {"id": "GateEstruturalAgent", "name": "P1 · Gate estrutural", "icon": "🚧", "output_key": "gate_estrutural_report", "prompt_file": "produto/p1_gate_estrutural.md", "description": "23 critérios: estrutura, ambiente, logística, evidências, viabilidade e infraestrutura."},
    {"id": "GateEstruturalCheck", "name": "P1c · Veredito do gate (determinístico)", "icon": "🔀", "output_key": "gate_estrutural_status", "prompt_file": None, "description": "Lê o envelope JSON e decide repetir, seguir ou bloquear."},
    {"id": "RevisorOnePagerAgent", "name": "P1b · Revisor do one-pager", "icon": "🩹", "output_key": "one_pager", "prompt_file": "produto/p1b_revisor_one_pager.md", "description": "Aplica o complemento pronto-pra-colar do gate; não inventa decisão de produto."},
    {"id": "AvaliacaoPedagogicaAgent", "name": "P2 · Avaliação pedagógica", "icon": "🎓", "output_key": "avaliacao_pedagogica_report", "prompt_file": "produto/p2_avaliacao_pedagogica.md", "description": "BNCC, professor, guardrails e affordance × guardrail (paralelo com P3)."},
    {"id": "ExperienciaAlunoAgent", "name": "P3 · Experiência do aluno", "icon": "🧒", "output_key": "experiencia_aluno_report", "prompt_file": "produto/p3_experiencia_aluno.md", "description": "Carga cognitiva, faixa etária e agência (paralelo com P2)."},
    {"id": "GateFinalProdutoAgent", "name": "P4 · Gate final de produto", "icon": "🏁", "output_key": "gate_final_report", "prompt_file": "produto/p4_gate_final.md", "description": "Coerência entre missão e vereditos; libera ou bloqueia para design/dev."},
    {"id": "GateFinalProdutoCheck", "name": "P4c · Veredito final (determinístico)", "icon": "🔀", "output_key": "gate_final_status", "prompt_file": None, "description": "Lê o envelope do gate final."},
    {"id": "SpecMissaoAgent", "name": "P5 · Spec da missão", "icon": "📜", "output_key": "spec_missao", "prompt_file": "produto/p5_spec_missao.md", "description": "Os 12 blocos da spec — contrato contra o qual design e dev constroem."},
]
