"""Pacote contendo os 8 agentes especializados do pipeline sequencial ADK."""

from .a1_requirements import get_requirements_agent
from .a2_figma_inspector import get_figma_inspector_agent
from .a3_mission_architect import get_mission_architect_agent
from .a4_mechanics import get_mechanics_agent
from .a5_ui_ux import get_ui_ux_designer_agent
from .a6_tech_architect import get_tech_architect_agent
from .a7_code_generator import get_code_generator_agent
from .a8_qa_validator import get_qa_validator_agent

__all__ = [
    "get_requirements_agent",
    "get_figma_inspector_agent",
    "get_mission_architect_agent",
    "get_mechanics_agent",
    "get_ui_ux_designer_agent",
    "get_tech_architect_agent",
    "get_code_generator_agent",
    "get_qa_validator_agent",
]
