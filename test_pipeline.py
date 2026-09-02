"""Script de teste e validação da estrutura do Pipeline Orquestrador Google ADK."""

import sys
from pipeline.orchestrator import create_mission_orchestrator, get_pipeline_agents_metadata
from config import get_settings


def test_structure():
    """Valida a instanciação dos 8 agentes, metadados e orquestrador ADK."""
    print("=" * 60)
    print("🚀 Iniciando Teste Estrutural do Pipeline ADK (8 Agentes)")
    print("=" * 60)

    settings = get_settings()
    print(f"📦 Configurações Carregadas:")
    print(f"   - App Name: {settings.app_name}")
    print(f"   - Modelo Padrão: {settings.gemini_model}")
    print(f"   - Figma MCP Command: {settings.figma_mcp_command}")
    print(f"   - Figma Key Configurada: {'SIM' if settings.is_figma_configured() else 'NÃO (Fallback Ativo)'}")
    print(f"   - Gemini API Key Configurada: {'SIM' if settings.is_gemini_configured() else 'NÃO'}")

    metadata = get_pipeline_agents_metadata()
    print(f"\n📋 Metadados das Etapas ({len(metadata)} Agentes):")
    for item in metadata:
        print(f"   [{item['step']}/8] {item['icon']} {item['name']} (Key: {item['output_key']})")

    assert len(metadata) == 8, f"Esperado 8 agentes, encontrado {len(metadata)}"

    print("\n🔨 Instanciando SequentialAgent do Google ADK...")
    orchestrator = create_mission_orchestrator()
    print(f"   - Nome do Orquestrador: {orchestrator.name}")
    print(f"   - Quantidade de Subagentes: {len(orchestrator.sub_agents)}")

    assert len(orchestrator.sub_agents) == 8, f"Esperado 8 subagentes, encontrado {len(orchestrator.sub_agents)}"

    for idx, agent in enumerate(orchestrator.sub_agents, 1):
        tools_count = len(getattr(agent, "tools", []) or [])
        output_key = getattr(agent, "output_key", "None")
        cfg = getattr(agent, "generate_content_config", None)
        th = getattr(cfg, "thinking_config", None) if cfg else None
        budget_str = f"Thinking Budget: {th.thinking_budget}" if th else "Sem Thinking"
        print(f"   ✓ Subagente {idx}: {agent.name} (Key: {output_key}, Tools: {tools_count}, {budget_str})")

    # Teste de propagação customizada do Thinking
    custom_orch = create_mission_orchestrator(thinking_budget=4096, include_thoughts=True)
    for agent in custom_orch.sub_agents:
        assert agent.generate_content_config.thinking_config.thinking_budget == 4096, "Falha na propagação do thinking_budget!"

    print("\n" + "=" * 60)
    print("✅ TESTE ESTRUTURAL E DE PROPAGAÇÃO DO THINKING CONCLUÍDO COM SUCESSO TOTAL!")
    print("=" * 60)


if __name__ == "__main__":
    test_structure()
