"""Módulo orquestrador sequencial do Google ADK (SequentialAgent).
Monta o pipeline padrão ouro composto pelos 8 LLM Agents especializados.
"""

from typing import Any, Dict, List
from google.adk.agents.sequential_agent import SequentialAgent
from agents import (
    get_requirements_agent,
    get_figma_inspector_agent,
    get_mission_architect_agent,
    get_mechanics_agent,
    get_ui_ux_designer_agent,
    get_tech_architect_agent,
    get_code_generator_agent,
    get_qa_validator_agent,
)
from config import get_settings


def get_pipeline_agents_metadata() -> List[Dict[str, Any]]:
    """Retorna a lista de metadados das 8 etapas do pipeline para exibição e monitoramento."""
    return [
        {
            "step": 1,
            "id": "RequirementsAgent",
            "name": "1. Analisador de Requisitos",
            "icon": "📋",
            "output_key": "requirements_spec",
            "prompt_file": "a1_requirements.md",
            "description": "Extrai metas, regras funcionais e escopo a partir do briefing.",
        },
        {
            "step": 2,
            "id": "FigmaInspectorAgent",
            "name": "2. Inspetor de Design Figma",
            "icon": "🎨",
            "output_key": "figma_design_context",
            "prompt_file": "a2_figma_inspector.md",
            "description": "Conecta via MCP para inspecionar componentes, cores e tipografia.",
        },
        {
            "step": 3,
            "id": "MissionArchitectAgent",
            "name": "3. Arquiteto da Missão & Narrativa",
            "icon": "🗺️",
            "output_key": "mission_architecture",
            "prompt_file": "a3_mission_architect.md",
            "description": "Elabora lore, fases da jornada e matriz de objetivos e recompensas.",
        },
        {
            "step": 4,
            "id": "MechanicsAgent",
            "name": "4. Motor de Regras & Mecânicas",
            "icon": "⚙️",
            "output_key": "game_mechanics",
            "prompt_file": "a4_mechanics.md",
            "description": "Define máquina de estados (FSM), fórmulas de pontuação e lógica.",
        },
        {
            "step": 5,
            "id": "UIUXDesignerAgent",
            "name": "5. Designer de Telas UI/UX",
            "icon": "📱",
            "output_key": "ui_ux_flow",
            "prompt_file": "a5_ui_ux.md",
            "description": "Mapeia fluxo de telas, layout do HUD e vínculo com o Figma.",
        },
        {
            "step": 6,
            "id": "TechArchitectAgent",
            "name": "6. Arquiteto de Software",
            "icon": "🏗️",
            "output_key": "technical_blueprint",
            "prompt_file": "a6_tech_architect.md",
            "description": "Projeta schemas de dados (JSON/Pydantic), APIs e barramento de eventos.",
        },
        {
            "step": 7,
            "id": "CodeGeneratorAgent",
            "name": "7. Gerador de Código & Configs",
            "icon": "💻",
            "output_key": "generated_implementation",
            "prompt_file": "a7_code_generator.md",
            "description": "Gera código Python da máquina de estados, configs JSON e testes.",
        },
        {
            "step": 8,
            "id": "QAValidatorAgent",
            "name": "8. Auditor de QA & Validação Final",
            "icon": "🏆",
            "output_key": "final_delivery_report",
            "prompt_file": "a8_qa_validator.md",
            "description": "Audita todas as etapas, valida consistência e emite o relatório ouro.",
        },
    ]


def create_mission_orchestrator(
    name: str = "MissionPipelineOrchestrator",
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
) -> SequentialAgent:
    """Cria a instância do orquestrador SequentialAgent do Google ADK contendo os 8 agentes em sequência estrita.
    
    A execução passa o InvocationContext compartilhado entre todos os subagentes,
    permitindo que as chaves de saída (output_key) alimentem os passos seguintes via {chave}.
    O orçamento de raciocínio (thinking_budget) é aplicado uniformemente a cada subagente.
    """
    settings = get_settings()
    t_budget = thinking_budget if thinking_budget is not None else getattr(settings, "thinking_budget", 2048)
    inc_thoughts = include_thoughts if include_thoughts is not None else getattr(settings, "include_thoughts", True)

    # Instanciação dos 8 subagentes especializados com o controle de Thinking
    a1 = get_requirements_agent(thinking_budget=t_budget, include_thoughts=inc_thoughts)
    a2 = get_figma_inspector_agent(thinking_budget=t_budget, include_thoughts=inc_thoughts)
    a3 = get_mission_architect_agent(thinking_budget=t_budget, include_thoughts=inc_thoughts)
    a4 = get_mechanics_agent(thinking_budget=t_budget, include_thoughts=inc_thoughts)
    a5 = get_ui_ux_designer_agent(thinking_budget=t_budget, include_thoughts=inc_thoughts)
    a6 = get_tech_architect_agent(thinking_budget=t_budget, include_thoughts=inc_thoughts)
    a7 = get_code_generator_agent(thinking_budget=t_budget, include_thoughts=inc_thoughts)
    a8 = get_qa_validator_agent(thinking_budget=t_budget, include_thoughts=inc_thoughts)

    sub_agents = [a1, a2, a3, a4, a5, a6, a7, a8]

    orchestrator = SequentialAgent(
        name=name,
        sub_agents=sub_agents,
        description=(
            "Orquestrador sequencial de 8 agentes para geração de missões completas, "
            "integrando requisitos, design Figma via MCP, narrativa, mecânicas, UI/UX, "
            "arquitetura técnica, geração de código e validação de QA."
        ),
    )

    return orchestrator
