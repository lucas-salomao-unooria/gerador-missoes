"""Entrypoint do agente raiz para o Google ADK e Vertex AI Agent Engine."""

import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from pipeline.orchestrator import create_mission_orchestrator

root_agent = create_mission_orchestrator()
agent = root_agent
