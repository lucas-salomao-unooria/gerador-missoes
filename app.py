"""Aplicação Streamlit: Interface Chatbot com Orquestrador de 8 Agentes do Google ADK e Figma MCP.
Padrão Ouro de arquitetura para visualização interativa do pipeline sequencial.
"""

import asyncio
import json
import os
import time
from typing import Any, Dict, List, Optional
import streamlit as st
from config import get_settings
from pipeline.orchestrator import get_pipeline_agents_metadata
from pipeline.runner import run_orchestrator_pipeline_stream, PipelineExecutionResult
from prompts import get_prompt_raw, save_prompt
from PIL import Image
from tools.doc_parser import validate_and_process_batch, DocumentBatch

# Carregamento do Favicon a partir da pasta images/
favicon = None
if os.path.exists("images/logo.png"):
    try:
        favicon = Image.open("images/logo.png")
    except Exception:
        favicon = None

# Configuração da página Streamlit
st.set_page_config(
    page_title="Gerador de Missões",
    page_icon=favicon or "🌌",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilização CSS customizada para acabamento premium
st.markdown(
    """
    <style>
    .main-header {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        background: linear-gradient(135deg, #6366F1 0%, #A855F7 50%, #EC4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .badge-step {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-right: 6px;
    }
    .badge-pending {
        background-color: rgba(107, 114, 128, 0.15);
        color: inherit;
        border: 1px solid rgba(107, 114, 128, 0.3);
    }
    .badge-running {
        background-color: rgba(59, 130, 246, 0.15);
        color: #2563EB;
        border: 1px solid rgba(59, 130, 246, 0.35);
    }
    .badge-done {
        background-color: rgba(16, 185, 129, 0.15);
        color: #059669;
        border: 1px solid rgba(16, 185, 129, 0.35);
    }
    .stChatMessage {
        border-radius: 12px;
        margin-bottom: 0.8rem;
    }
    .agent-card {
        padding: 12px 14px;
        border-radius: 10px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        background-color: var(--secondary-background-color);
        color: var(--text-color);
        margin-bottom: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_session_state():
    """Inicializa as variáveis de estado de sessão do Streamlit."""
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "👋 Olá! Sou o seu **Orquestrador de Missões Google ADK**.\n\n"
                    "Possuo um pipeline sequencial de **8 Agentes LLM Especializados** "
                    "com integração ao **Figma MCP** para transformar qualquer ideia em uma "
                    "especificação completa de missão, design, mecânica, código e validação de QA.\n\n"
                    "💡 *Experimente enviar uma ideia como:* 'Missão de infiltração cibernética em uma megacorporação' "
                    "ou 'Missão medieval de escolta de caravana com emboscadas dinâmicas'."
                ),
                "pipeline_result": None,
            }
        ]

    if "current_pipeline_status" not in st.session_state:
        st.session_state.current_pipeline_status = {}


def render_sidebar():
    """Renderiza a barra lateral limpa com status dos agentes e atalhos."""
    settings = get_settings()

    with st.sidebar:
        # Marca da aplicação no topo da sidebar
        if os.path.exists("images/marca.png"):
            st.image("images/marca.png", use_container_width=True)
        elif os.path.exists("images/logo.png"):
            st.image("images/logo.png", use_container_width=True)

        st.markdown("### ⚙️ Pipeline")
        st.markdown("---")

        # Status do Ambiente carregado do .env
        st.markdown("#### 📡 Status do Ambiente (`.env`)")
        
        gemini_status = "🟢 Configurada" if settings.is_gemini_configured() else "🔴 Ausente no .env"
        figma_status = "🟢 Conectado" if settings.is_figma_configured() else "🟡 Não configurado"
        
        with st.container(border=True):
            st.markdown(f"🤖 **Modelo:** `{settings.gemini_model}`")
            st.markdown(f"🔑 **Gemini API:** {gemini_status}")
            st.markdown(f"🎨 **Figma MCP:** {figma_status}")

        # Controle de Nível de Raciocínio (User-Friendly)
        st.markdown("---")
        st.markdown("#### 🧠 Nível de Raciocínio")

        thinking_presets = {
            "Desativado": 0,
            "Rápido": 1024,
            "Equilibrado": 2048,
            "Aprofundado": 4096,
            "Avançado": 8192,
            "Máximo": 16384,
            "Automático": -1,
        }
        presets_by_val = {v: k for k, v in thinking_presets.items()}

        current_val = getattr(settings, "thinking_budget", 2048)
        default_label = presets_by_val.get(current_val, "Equilibrado")

        selected_label = st.select_slider(
            "Profundidade de Reflexão:",
            options=list(thinking_presets.keys()),
            value=default_label,
            help="Define o nível de análise e reflexão de cada agente antes de gerar o resultado.",
        )
        selected_budget = thinking_presets[selected_label]
        st.session_state.thinking_budget = selected_budget
        os.environ["THINKING_BUDGET"] = str(selected_budget)

        include_thoughts_toggle = st.toggle(
            "Exibir pensamentos dos agentes",
            value=getattr(settings, "include_thoughts", True),
            help="Exibe o passo a passo da reflexão interna de cada agente na aba de resultados.",
        )
        st.session_state.include_thoughts = include_thoughts_toggle
        os.environ["INCLUDE_THOUGHTS"] = str(include_thoughts_toggle).lower()

        folder_url = getattr(settings, "figma_default_folder_url", os.getenv("FIGMA_DEFAULT_FOLDER_URL", ""))
        if folder_url:
            st.link_button("📁 Abrir Pasta no Figma ↗", folder_url, use_container_width=True)

        st.markdown("---")
        # Mapa dos 8 Agentes
        st.markdown("#### 🤖 Etapas do Pipeline")
        metadata = get_pipeline_agents_metadata()
        for agent_meta in metadata:
            st.markdown(
                f"<div style='font-size: 0.83rem; margin-bottom: 8px;'>"
                f"{agent_meta.get('icon', '🤖')} <b>{agent_meta.get('name', '')}</b><br>"
                f"<span style='opacity: 0.7; font-size: 0.74rem;'>State: <code>{agent_meta.get('output_key', '')}</code></span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.markdown("---")
        if st.button("🗑️ Limpar Conversa", use_container_width=True):
            st.session_state.messages = []
            st.session_state.current_pipeline_status = {}
            st.rerun()


async def execute_adk_pipeline(
    prompt: str,
    progress_placeholder,
    steps_container,
    doc_batch: Optional[DocumentBatch] = None,
):
    """Executa o pipeline ADK assincronamente e atualiza a UI do Streamlit com o progresso de cada agente."""
    settings = get_settings()
    metadata = get_pipeline_agents_metadata()
    agent_id_map = {m["id"]: m for m in metadata}

    # Inicializa estados visuais para cada um dos 8 agentes
    agent_statuses = {
        m["id"]: {
            "status": "pending",
            "icon": m["icon"],
            "name": m["name"],
            "output_key": m["output_key"],
            "output": "",
            "time_taken": 0.0,
        }
        for m in metadata
    }

    def update_steps_ui():
        with steps_container.container():
            st.markdown("#### ⚡ Execução do Pipeline ADK em Tempo Real")
            cols = st.columns(4)
            for idx, m in enumerate(metadata):
                col_idx = idx % 4
                agent_id = m["id"]
                info = agent_statuses[agent_id]
                status = info["status"]

                if status == "pending":
                    badge = "<span class='badge-step badge-pending'>⏳ Pendente</span>"
                elif status == "running":
                    badge = "<span class='badge-step badge-running'>🔄 Executando...</span>"
                else:
                    badge = "<span class='badge-step badge-done'>✅ Concluído</span>"

                with cols[col_idx]:
                    st.markdown(
                        f"<div class='agent-card'>"
                        f"<div>{info['icon']} <b>{m['step']}. {m['name'].split('. ')[-1]}</b></div>"
                        f"<div style='margin-top: 6px;'>{badge}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

    update_steps_ui()

    final_result: Optional[PipelineExecutionResult] = None
    active_agent: Optional[str] = None
    agent_start_time = time.time()

    t_budget = st.session_state.get("thinking_budget", getattr(settings, "thinking_budget", 2048))
    inc_thoughts = st.session_state.get("include_thoughts", getattr(settings, "include_thoughts", True))

    async for event in run_orchestrator_pipeline_stream(
        prompt=prompt,
        thinking_budget=t_budget,
        include_thoughts=inc_thoughts,
        doc_batch=doc_batch,
    ):
        event_type = event.get("type")

        if event_type == "agent_started":
            agent_name = event.get("agent_name")
            if active_agent and active_agent in agent_statuses:
                agent_statuses[active_agent]["status"] = "done"
                agent_statuses[active_agent]["time_taken"] = time.time() - agent_start_time

            active_agent = agent_name
            agent_start_time = time.time()
            if active_agent in agent_statuses:
                agent_statuses[active_agent]["status"] = "running"
            
            progress_placeholder.info(f"🔄 Executando Agente: **{active_agent}**...")
            update_steps_ui()

        elif event_type == "agent_chunk":
            agent_name = event.get("agent_name")
            if agent_name in agent_statuses:
                agent_statuses[agent_name]["output"] = event.get("accumulated", "")

        elif event_type == "agent_thought_chunk":
            agent_name = event.get("agent_name")
            progress_placeholder.info(f"🧠 Agente **{agent_name}** raciocinando...")

        elif event_type == "pipeline_completed":
            if active_agent and active_agent in agent_statuses:
                agent_statuses[active_agent]["status"] = "done"
                agent_statuses[active_agent]["time_taken"] = time.time() - agent_start_time

            # Marca todos os agentes como concluídos
            for a_id in agent_statuses:
                if agent_statuses[a_id]["status"] != "done":
                    agent_statuses[a_id]["status"] = "done"

            final_result = event.get("result")
            progress_placeholder.success(
                f"🎉 Pipeline concluído com sucesso em **{final_result.duration_seconds:.2f}s**!"
            )
            update_steps_ui()

        elif event_type == "pipeline_error":
            progress_placeholder.error(f"❌ Erro durante a execução: {event.get('error')}")
            final_result = event.get("result")
            update_steps_ui()

    return final_result


def render_pipeline_details(result: PipelineExecutionResult):
    """Exibe o resultado detalhado com abas para cada etapa e opções de exportação."""
    st.markdown("---")
    st.markdown("### 📦 Resultados Consolidados do Pipeline")

    tab_titles = [
        "🏆 Relatório Final",
        "🧠 Reflexão dos Agentes",
        "📋 1. Requisitos",
        "🎨 2. Figma MCP",
        "🗺️ 3. Narrativa",
        "⚙️ 4. Mecânicas",
        "📱 5. UI/UX",
        "🏗️ 6. Arquitetura",
        "💻 7. Código Gerado",
        "🔍 Estado Raw (ADK State)",
    ]

    tabs = st.tabs(tab_titles)

    # 1. Relatório Final
    with tabs[0]:
        st.markdown(result.final_output)

    # 2. Reflexão dos Agentes
    with tabs[1]:
        step_thoughts = getattr(result, "step_thoughts", {})
        if step_thoughts and any(step_thoughts.values()):
            st.markdown("#### 🧠 Reflexão e Planejamento dos Agentes:")
            for agent_name, thoughts in step_thoughts.items():
                if thoughts.strip():
                    with st.expander(f"🧠 Reflexão de **{agent_name}**", expanded=False):
                        st.markdown(thoughts)
        else:
            st.info("Nenhuma reflexão detalhada foi registrada para esta execução.")

    # 3. Requisitos
    with tabs[2]:
        output_req = result.state.get("requirements_spec") or result.step_outputs.get("RequirementsAgent", "Nenhum dado registrado.")
        st.markdown(output_req)

    # 4. Figma MCP
    with tabs[3]:
        output_figma = result.state.get("figma_design_context") or result.step_outputs.get("FigmaInspectorAgent", "Nenhum dado registrado.")
        st.markdown(output_figma)

    # 5. Narrativa
    with tabs[4]:
        output_narr = result.state.get("mission_architecture") or result.step_outputs.get("MissionArchitectAgent", "Nenhum dado registrado.")
        st.markdown(output_narr)

    # 6. Mecânicas
    with tabs[5]:
        output_mec = result.state.get("game_mechanics") or result.step_outputs.get("MechanicsAgent", "Nenhum dado registrado.")
        st.markdown(output_mec)

    # 7. UI/UX
    with tabs[6]:
        output_ui = result.state.get("ui_ux_flow") or result.step_outputs.get("UIUXDesignerAgent", "Nenhum dado registrado.")
        st.markdown(output_ui)

    # 8. Arquitetura
    with tabs[7]:
        output_tech = result.state.get("technical_blueprint") or result.step_outputs.get("TechArchitectAgent", "Nenhum dado registrado.")
        st.markdown(output_tech)

    # 9. Código
    with tabs[8]:
        output_code = result.state.get("generated_implementation") or result.step_outputs.get("CodeGeneratorAgent", "Nenhum dado registrado.")
        st.markdown(output_code)

    # 10. Estado Raw
    with tabs[9]:
        st.json(result.state)

    # Botões de Download
    st.markdown("---")
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        attached_str = f"\nDocumentos Anexados: {', '.join(result.attached_files)}" if getattr(result, "attached_files", None) else ""
        full_markdown = f"""# Relatório Consolidado de Missão - Google ADK Pipeline
Prompt: {result.prompt}{attached_str}
Duração: {result.duration_seconds:.2f}s
Session ID: {result.session_id}

{result.final_output}

---
## 1. Requisitos
{result.state.get('requirements_spec', '')}

---
## 2. Figma Design Context
{result.state.get('figma_design_context', '')}

---
## 3. Arquitetura da Missão
{result.state.get('mission_architecture', '')}

---
## 4. Mecânicas e Regras
{result.state.get('game_mechanics', '')}

---
## 5. Fluxo UI/UX
{result.state.get('ui_ux_flow', '')}

---
## 6. Blueprint Técnico
{result.state.get('technical_blueprint', '')}

---
## 7. Implementação em Código
{result.state.get('generated_implementation', '')}
"""
        st.download_button(
            label="📥 Baixar Pacote Completo (Markdown)",
            data=full_markdown,
            file_name=f"missao_{result.session_id[:8]}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with col_dl2:
        export_json = {
            "session_id": result.session_id,
            "prompt": result.prompt,
            "attached_files": getattr(result, "attached_files", []),
            "duration_seconds": result.duration_seconds,
            "state": result.state,
            "step_outputs": result.step_outputs,
        }
        st.download_button(
            label="📥 Baixar Estado Completo (JSON)",
            data=json.dumps(export_json, indent=2, ensure_ascii=False),
            file_name=f"missao_{result.session_id[:8]}.json",
            mime="application/json",
            use_container_width=True,
        )


def render_prompt_manager():
    """Renderiza a interface para visualização, edição e salvamento dos prompts dos 8 agentes."""
    st.markdown("### 📝 Gerenciador de Prompts dos Agentes (.md)")
    st.markdown(
        "Visualize e edite as instruções do sistema de cada um dos **8 agentes** do pipeline. "
        "As alterações são salvas diretamente nos arquivos `.md` na pasta `prompts/` e aplicadas imediatamente."
    )
    st.markdown("---")

    DEFAULT_PROMPT_FILES = {
        "RequirementsAgent": "a1_requirements.md",
        "FigmaInspectorAgent": "a2_figma_inspector.md",
        "MissionArchitectAgent": "a3_mission_architect.md",
        "MechanicsAgent": "a4_mechanics.md",
        "UIUXDesignerAgent": "a5_ui_ux.md",
        "TechArchitectAgent": "a6_tech_architect.md",
        "CodeGeneratorAgent": "a7_code_generator.md",
        "QAValidatorAgent": "a8_qa_validator.md",
    }

    metadata = get_pipeline_agents_metadata()
    agent_options = {}
    for m in metadata:
        agent_id = m.get("id", "")
        p_file = m.get("prompt_file") or DEFAULT_PROMPT_FILES.get(agent_id, f"a{m.get('step', 1)}.md")
        m["prompt_file"] = p_file
        label = f"{m.get('icon', '🤖')} {m.get('name', agent_id)} ({p_file})"
        agent_options[label] = m

    selected_label = st.selectbox(
        "Selecione o Agente para visualizar/editar o prompt:",
        list(agent_options.keys()),
        index=0,
    )
    agent_meta = agent_options[selected_label]
    prompt_file = agent_meta.get("prompt_file") or DEFAULT_PROMPT_FILES.get(agent_meta.get("id", ""), "a1_requirements.md")

    # Metadados e informações do Agente selecionado
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.markdown(f"**Identificador:** `{agent_meta['id']}`")
    with col_info2:
        st.markdown(f"**Chave de Saída (State):** `{agent_meta['output_key']}`")
    with col_info3:
        st.markdown(f"**Arquivo no Disco:** `prompts/{prompt_file}`")

    st.info(f"💡 **Propósito:** {agent_meta['description']}")

    # Lê o conteúdo bruto do arquivo
    try:
        raw_prompt = get_prompt_raw(prompt_file)
    except Exception as e:
        st.error(f"Erro ao ler prompt: {e}")
        raw_prompt = ""

    tab_edit, tab_preview = st.tabs(["✏️ Editor de Texto (Markdown)", "👁️ Visualização Renderizada"])

    with tab_edit:
        edited_prompt = st.text_area(
            label="Conteúdo do Prompt do Sistema:",
            value=raw_prompt,
            height=460,
            key=f"text_area_{prompt_file}",
            help="Edite o prompt em Markdown. Variáveis como {requirements_spec} ou {figma_design_context} são interpoladas dinamicamente pelo Google ADK.",
        )

        col_save, col_reload, col_space = st.columns([1.5, 1.5, 4])
        with col_save:
            if st.button("💾 Salvar Prompt", type="primary", key=f"btn_save_{prompt_file}", use_container_width=True):
                save_prompt(prompt_file, edited_prompt)
                st.success(f"✅ Prompt `{prompt_file}` salvo com sucesso! Os próximos disparos usarão esta instrução.")

        with col_reload:
            if st.button("🔄 Recarregar do Disco", key=f"btn_reload_{prompt_file}", use_container_width=True):
                st.rerun()

    with tab_preview:
        st.markdown("#### Pré-visualização do Prompt Formatado:")
        st.markdown(edited_prompt)


def main():
    """Função principal da interface Streamlit."""
    init_session_state()
    render_sidebar()

    # Cabeçalho Principal
    st.markdown("<h1 class='main-header'>Gerador de Missões</h1>", unsafe_allow_html=True)
    st.markdown(
        "**Pipeline Sequencial de 8 Agentes LLM** integrado com **Figma MCP** para especificação, design e implementação automatizada de missões."
    )
    st.markdown("---")

    # Abas principais: Chatbot vs Editor de Prompts
    tab_chat, tab_prompts = st.tabs(["💬 Chatbot do Pipeline", "📝 Editor de Prompts (8 Agentes)"])

    with tab_chat:
        # Renderiza mensagens anteriores do histórico
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("pipeline_result"):
                    render_pipeline_details(msg["pipeline_result"])

        # Seletor e Validador de Documentos de Apoio (PDF Nativo e DOCX/DOC via MarkItDown)
        doc_batch: Optional[DocumentBatch] = None
        with st.expander("📎 Anexar Documentos de Apoio (PDF ou Word — até 10 arquivos / 25 MB)", expanded=False):
            uploaded_files = st.file_uploader(
                "Arraste ou selecione arquivos para alimentar o Agente 1 (Requisitos):",
                type=["pdf", "docx", "doc"],
                accept_multiple_files=True,
                help=(
                    "• PDFs são processados nativamente pelo Gemini 3.7 (visão multimodal, tabelas e diagramas).\n"
                    "• Documentos Word (.docx/.doc) são convertidos via Microsoft MarkItDown.\n"
                    "• Limite: máximo de 10 arquivos e até 25 MB no total."
                ),
                key="attached_mission_docs",
            )
            if uploaded_files:
                batch_result, error_msg = validate_and_process_batch(uploaded_files)
                if error_msg:
                    st.error(error_msg)
                elif batch_result:
                    doc_batch = batch_result
                    st.success(
                        f"✅ **{doc_batch.files_count} arquivo(s)** anexado(s) com sucesso "
                        f"({doc_batch.total_mb:.2f} MB / 25.0 MB)."
                    )
                    cols_docs = st.columns(min(doc_batch.files_count, 3))
                    for idx, doc in enumerate(doc_batch.documents):
                        col_target = cols_docs[idx % len(cols_docs)]
                        type_badge = "🎨 PDF Nativo" if doc.is_native_pdf else "📝 Word (MarkItDown)"
                        with col_target.container(border=True):
                            st.markdown(f"**{doc.name}**")
                            st.caption(f"{type_badge} • {doc.size_mb:.2f} MB")

        # Entrada de Chat
        user_prompt = st.chat_input("Descreva a missão ou funcionalidade que deseja gerar...")

        if user_prompt:
            # Validação da Chave API
            settings = get_settings()
            if not settings.is_gemini_configured() and not os.getenv("GOOGLE_API_KEY"):
                st.warning(
                    "⚠️ **Atenção:** A chave `GOOGLE_API_KEY` do Gemini não foi configurada! "
                    "Por favor, configure-a no arquivo `.env` para executar os agentes."
                )

            # Adiciona mensagem do usuário com indicação de documentos se houver
            display_content = user_prompt
            if doc_batch and doc_batch.documents:
                files_badge_list = [
                    f"`{d.name}` ({'PDF Nativo' if d.is_native_pdf else 'Word Convertido'})"
                    for d in doc_batch.documents
                ]
                display_content += f"\n\n📎 **Anexos ({doc_batch.files_count}):** " + ", ".join(files_badge_list)

            st.session_state.messages.append({"role": "user", "content": display_content})
            with st.chat_message("user"):
                st.markdown(display_content)

            # Resposta do Assistente / Pipeline
            with st.chat_message("assistant"):
                progress_placeholder = st.empty()
                steps_container = st.empty()

                progress_placeholder.info("🚀 Iniciando o orquestrador sequencial do Google ADK...")

                # Executa o loop assíncrono
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    execute_adk_pipeline(
                        user_prompt,
                        progress_placeholder,
                        steps_container,
                        doc_batch=doc_batch,
                    )
                )

                if result:
                    st.markdown(result.final_output)
                    render_pipeline_details(result)

                    # Salva a resposta no histórico
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": result.final_output,
                            "pipeline_result": result,
                        }
                    )

    with tab_prompts:
        render_prompt_manager()


if __name__ == "__main__":
    main()
