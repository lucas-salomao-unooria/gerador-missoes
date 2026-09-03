"""Interface Streamlit do Gerador de Missões Unooria.

Pipeline Produto → Design (com MCP do Figma) → Dev, orquestrado pelo Google ADK,
com acompanhamento em tempo real por etapa, inspeção dos artefatos e editor de prompts.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st
from PIL import Image

from config import get_settings
from pipeline.artifacts import extract_figma_links, generate_artifact_manifest
from pipeline.orchestrator import STAGES, get_pipeline_agents_metadata, get_pipeline_stages
from pipeline.runner import PipelineExecutionResult, run_orchestrator_pipeline_stream
from pipeline.session_store import (
    create_session_zip,
    delete_saved_session,
    list_saved_sessions,
    load_saved_session,
)
from prompts import get_prompt_raw, list_prompt_files, load_prompt, save_prompt
from tools.doc_parser import DocumentBatch, validate_and_process_batch

favicon = None
if os.path.exists("images/logo.png"):
    try:
        favicon = Image.open("images/logo.png")
    except Exception:
        favicon = None

st.set_page_config(page_title="Gerador de Missões", page_icon=favicon or "🌌", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
    .main-header { font-family: 'Inter', sans-serif; font-weight: 700;
      background: linear-gradient(135deg, #7FA5E2 0%, #716C98 60%, #0E1039 100%);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.2rem; }
    .badge-step { display:inline-block; padding:3px 9px; border-radius:12px; font-size:0.74rem; font-weight:600; }
    .badge-pending { background: rgba(107,114,128,.15); border:1px solid rgba(107,114,128,.3); }
    .badge-running { background: rgba(59,130,246,.15); color:#2563EB; border:1px solid rgba(59,130,246,.35); }
    .badge-done { background: rgba(16,185,129,.15); color:#059669; border:1px solid rgba(16,185,129,.35); }
    .badge-skipped { background: rgba(245,158,11,.15); color:#B45309; border:1px solid rgba(245,158,11,.35); }
    .agent-card { padding:8px 10px; border-radius:10px; border:1px solid rgba(128,128,128,.2);
      background: var(--secondary-background-color); margin-bottom:6px; font-size:0.82rem; }
    .stage-title { font-weight:700; margin: 10px 0 4px 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

GATE_LABELS = {
    "gate_estrutural_status": "Gate estrutural",
    "gate_final_status": "Gate final de produto",
    "design_status": "QA de design",
    "dev_status": "Banca de dev",
}


def _status_icon(value: Any) -> str:
    return {"aprovado": "🟢", "bloqueado": "🔴", "indefinido": "⚪"}.get(str(value), "⚪")


def init_session_state():
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "👋 Olá! Sou o **Gerador de Missões Unooria**.\n\n"
                    "Envie o one-pager (ou a ideia) de uma missão. O pipeline passa por **Produto** "
                    "(gate estrutural, avaliação pedagógica, experiência do estudante, gate final e spec), "
                    "**Design** (briefing de ofício, jornada e fluxo no FigJam, copy e wireframes lo-fi no Figma, QA) "
                    "e **Dev** (handoff, brief de assets, banca de validação em 5 dimensões) e entrega um "
                    "**PRD padrão ouro** com o contexto arquitetural da plataforma, pronto para um agente de codificação.\n\n"
                    "💡 *Anexe o one-pager em PDF/DOCX ou descreva: ano/série, ambiente simulado "
                    "(Instagram, YouTube, ChatGPT, TikTok ou WhatsApp), descoberta central e a decisão do estudante.*"
                ),
                "pipeline_result": None,
            }
        ]


def render_sidebar() -> Dict[str, Any]:
    settings = get_settings()
    with st.sidebar:
        if os.path.exists("images/marca.png"):
            st.image("images/marca.png", use_container_width=True)
        elif os.path.exists("images/logo.png"):
            st.image("images/logo.png", use_container_width=True)

        if st.button("➕ Nova Missão", type="primary", use_container_width=True):
            st.session_state.current_session_id = None
            st.session_state.messages = []
            init_session_state()
            st.rerun()

        st.markdown("---")
        st.markdown("#### 🗂️ Histórico de Missões")
        saved_sessions = list_saved_sessions()
        if not saved_sessions:
            st.caption("Nenhuma missão gravada ainda.")
        else:
            for s in saved_sessions[:15]:
                is_active = st.session_state.get("current_session_id") == s["dir_name"]
                col_btn, col_del = st.columns([5, 1])
                disp_title = s["title"]
                if len(disp_title) > 24:
                    disp_title = disp_title[:22] + "…"
                btn_label = f"{s['status_icon']} {disp_title}"
                with col_btn:
                    if st.button(
                        btn_label,
                        key=f"sess_{s['dir_name']}",
                        use_container_width=True,
                        type="primary" if is_active else "secondary",
                        help=f"{s['title']}\n📅 {s['created_at']} | Status: {s['status']} | 📄 {s['files_count']} arquivos",
                    ):
                        loaded = load_saved_session(s["dir_name"])
                        if loaded:
                            msgs, res, meta = loaded
                            st.session_state.current_session_id = s["dir_name"]
                            st.session_state.messages = msgs
                            st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_{s['dir_name']}", help=f"Excluir {s['title']}"):
                        delete_saved_session(s["dir_name"])
                        if st.session_state.get("current_session_id") == s["dir_name"]:
                            st.session_state.current_session_id = None
                            st.session_state.messages = []
                            init_session_state()
                        st.rerun()

        st.markdown("---")
        st.markdown("#### 📡 Ambiente (`.env`)")
        with st.container(border=True):
            st.markdown(f"🤖 **Modelo:** `{settings.gemini_model}`")
            st.markdown(f"🔑 **Gemini API:** {'🟢 configurada' if settings.is_gemini_configured() else '🔴 ausente'}")
            st.markdown(f"🎨 **Figma MCP:** {settings.figma_status_label()}")

        st.markdown("---")
        st.markdown("#### ⚙️ Execução")
        stage_options = {"Produto": "produto", "Design": "design", "Dev": "dev"}
        default_stages = [k for k, v in stage_options.items() if v in settings.pipeline_stages]
        chosen = st.multiselect("Etapas ativas", list(stage_options), default=default_stages, help="Desligue etapas para testar só parte do pipeline.")
        stages = [stage_options[c] for c in chosen] or ["produto"]

        modo_estrito = st.toggle(
            "Modo estrito dos gates de produto",
            value=settings.produto_modo_estrito,
            help="Ligado: missão bloqueada no gate estrutural (após as rodadas) ou no gate final interrompe design e dev. "
            "Desligado: o pipeline segue e o PRD registra as pendências.",
        )

        thinking_presets = {"Desativado": 0, "Rápido": 1024, "Equilibrado": 2048, "Aprofundado": 4096, "Avançado": 8192, "Máximo": 16384, "Automático": -1}
        by_val = {v: k for k, v in thinking_presets.items()}
        selected_label = st.select_slider("Nível de raciocínio", options=list(thinking_presets), value=by_val.get(settings.thinking_budget, "Equilibrado"))
        include_thoughts = st.toggle("Exibir pensamentos dos agentes", value=settings.include_thoughts)

        if settings.figma_default_folder_url:
            st.link_button("📁 Abrir pasta no Figma ↗", settings.figma_default_folder_url, use_container_width=True)

        st.markdown("---")
        st.markdown("#### 🧩 Etapas e agentes")
        for stage in get_pipeline_stages(active_only=False):
            if stage["key"] not in stages and stage["key"] != "transversal":
                continue
            st.markdown(f"<div class='stage-title'>{stage['icon']} {stage['name']}</div>", unsafe_allow_html=True)
            for meta in stage["agents"]:
                st.markdown(
                    f"<div style='font-size:0.78rem;margin-left:6px;'>{meta['icon']} {meta['name']}"
                    f"<br><span style='opacity:.65;font-size:.7rem'>state: <code>{meta['output_key']}</code></span></div>",
                    unsafe_allow_html=True,
                )

        st.markdown("---")
        if st.button("🗑️ Limpar conversa", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    return {"stages": stages, "modo_estrito": modo_estrito, "thinking_budget": thinking_presets[selected_label], "include_thoughts": include_thoughts}


async def execute_pipeline(prompt: str, opts: Dict[str, Any], progress, steps_container, doc_batch: Optional[DocumentBatch]):
    active = set(opts["stages"]) | {"transversal"}
    stages = [s for s in STAGES if s["key"] in active]
    status: Dict[str, str] = {m["id"]: "pending" for s in stages for m in s["agents"]}
    gates: Dict[str, Any] = {}
    tool_log: List[str] = []

    def render():
        with steps_container.container():
            cols = st.columns(len(stages))
            for col, stage in zip(cols, stages):
                with col:
                    st.markdown(f"**{stage['icon']} {stage['name']}**")
                    for m in stage["agents"]:
                        s = status.get(m["id"], "pending")
                        badge = {
                            "pending": "<span class='badge-step badge-pending'>⏳</span>",
                            "running": "<span class='badge-step badge-running'>🔄</span>",
                            "done": "<span class='badge-step badge-done'>✅</span>",
                            "skipped": "<span class='badge-step badge-skipped'>⏭️</span>",
                        }[s]
                        st.markdown(f"<div class='agent-card'>{badge} {m['icon']} {m['name']}</div>", unsafe_allow_html=True)
            if gates:
                st.markdown("**Gates:** " + " · ".join(f"{_status_icon(v)} {GATE_LABELS.get(k, k)}" for k, v in gates.items() if k in GATE_LABELS))

    render()
    result: Optional[PipelineExecutionResult] = None
    active_agent: Optional[str] = None

    async for event in run_orchestrator_pipeline_stream(
        prompt=prompt,
        thinking_budget=opts["thinking_budget"],
        include_thoughts=opts["include_thoughts"],
        modo_estrito=opts["modo_estrito"],
        stages=opts["stages"],
        doc_batch=doc_batch,
    ):
        et = event.get("type")
        if et == "agent_started":
            name = event["agent_name"]
            if active_agent and status.get(active_agent) == "running":
                status[active_agent] = "done"
            active_agent = name
            if name in status:
                status[name] = "running"
            progress.info(f"🔄 Executando **{name}**…")
            render()
        elif et == "agent_chunk":
            name = event["agent_name"]
            if "não executado" in (event.get("chunk") or "") and name in status:
                status[name] = "skipped"
        elif et == "agent_tool_call":
            tool_log.append(f"{event['agent_name']} → {', '.join(event['tools'])}")
            progress.info(f"🎨 **{event['agent_name']}** chamou Figma MCP: `{', '.join(event['tools'])}`")
        elif et == "agent_thought_chunk":
            progress.info(f"🧠 **{event['agent_name']}** raciocinando…")
        elif et == "gate_status":
            gates.update(event["status"])
            render()
        elif et == "pipeline_completed":
            result = event["result"]
            for k in status:
                if status[k] == "running":
                    status[k] = "done"
                if result.bloqueado and status[k] == "pending":
                    status[k] = "skipped"
            render()
            if result.bloqueado:
                progress.warning(f"⛔ Missão bloqueada nos gates de produto em **{result.duration_seconds:.0f}s** — veja o relatório e o alerta.")
            else:
                progress.success(f"🎉 Pipeline concluído em **{result.duration_seconds:.0f}s**. Artefatos em `{result.output_dir}`.")
        elif et == "pipeline_error":
            result = event["result"]
            progress.error(f"❌ Erro: {event.get('error')}")
            render()
    if tool_log:
        with st.expander(f"🎨 Chamadas ao Figma MCP ({len(tool_log)})"):
            st.code("\n".join(tool_log))
    return result


def render_pipeline_details(result: PipelineExecutionResult, key_prefix: str = ""):
    st.markdown("---")
    gates = result.gates
    sid = str(getattr(result, "session_id", None) or "session")
    prefix = f"{key_prefix}_{sid}" if key_prefix else f"{sid}_{id(result)}"
    if gates:
        st.markdown("**Gates:** " + " · ".join(f"{_status_icon(v)} {GATE_LABELS[k]}" for k, v in gates.items() if k in GATE_LABELS))
    tabs = st.tabs(["📘 PRD", "🧭 Produto", "🎨 Design", "🛠️ Dev", "🧠 Aprendizado", "💭 Pensamentos", "📦 Artefatos & Figma", "🔍 Estado (JSON)"])

    with tabs[0]:
        if result.state.get("prd_final"):
            st.markdown(result.state["prd_final"])
        else:
            st.info("O PRD não foi gerado (pipeline bloqueado ou etapa Dev desligada). Abaixo, a saída mais relevante:")
            st.markdown(result.final_output)

    def stage_tab(stage_key: str):
        stage = next(s for s in STAGES if s["key"] == stage_key)
        shown = False
        for meta in stage["agents"]:
            key = meta["output_key"]
            value = result.state.get(key)
            if not value or not isinstance(value, str):
                continue
            shown = True
            with st.expander(f"{meta['icon']} {meta['name']}", expanded=False):
                st.markdown(value)
        if not shown:
            st.caption("Nenhuma saída registrada para esta etapa.")

    with tabs[1]:
        stage_tab("produto")
    with tabs[2]:
        stage_tab("design")
    with tabs[3]:
        stage_tab("dev")
    with tabs[4]:
        stage_tab("transversal")
    with tabs[5]:
        if any(result.step_thoughts.values()):
            for agent, thoughts in result.step_thoughts.items():
                if thoughts.strip():
                    with st.expander(f"🧠 {agent}"):
                        st.markdown(thoughts)
        else:
            st.info("Nenhum pensamento registrado.")

    with tabs[6]:
        # 1. Links do Figma & FigJam
        links = getattr(result, "figma_links", []) or extract_figma_links(result.state)
        if links:
            st.markdown("#### 🎨 Links do Figma & FigJam")
            cols = st.columns(min(len(links), 3) or 1)
            for idx, link in enumerate(links):
                with cols[idx % len(cols)]:
                    with st.container(border=True):
                        st.markdown(f"**{link.get('title', 'Arquivo Figma')}**")
                        st.caption(f"Origem: `{link.get('source_agent_key', 'design')}`")
                        st.link_button("Abrir no Figma ↗", link["url"], key=f"figma_{prefix}_{idx}", use_container_width=True)
            st.markdown("---")
        else:
            st.info("🎨 Nenhum link direto do Figma/FigJam registrado nesta execução (artefatos gerados em Markdown/Mermaid).")

        # 2. Manifesto de Arquivos
        st.markdown("#### 📁 Arquivos da Missão")
        if result.output_dir and os.path.exists(result.output_dir):
            output_path = Path(result.output_dir)
            manifest = getattr(result, "artifacts_manifest", []) or generate_artifact_manifest(output_path)

            col_zip, _ = st.columns([2, 2])
            with col_zip:
                zip_bytes = create_session_zip(output_path)
                st.download_button(
                    "📦 Baixar Todos os Artefatos (.ZIP)",
                    data=zip_bytes,
                    file_name=f"artefatos_{sid[:12]}.zip",
                    mime="application/zip",
                    key=f"zip_{prefix}",
                    use_container_width=True,
                )
            st.markdown("")

            grouped: Dict[str, List[Dict[str, Any]]] = {}
            for item in manifest:
                grouped.setdefault(item["category"], []).append(item)

            for cat_idx, (cat, items) in enumerate(grouped.items()):
                with st.expander(f"{cat} ({len(items)} arquivos)", expanded=True):
                    for item_idx, it in enumerate(items):
                        c_name, c_size, c_dl = st.columns([3, 1, 1.5])
                        c_name.markdown(f"📄 `{it['path']}`")
                        c_size.caption(it["size_str"])
                        full_fpath = output_path / it["path"]
                        if full_fpath.exists():
                            with c_dl:
                                file_bytes = full_fpath.read_bytes()
                                clean_path = re.sub(r"[^a-zA-Z0-9_-]", "_", str(it.get("path", "")))
                                st.download_button(
                                    "📥 Baixar",
                                    data=file_bytes,
                                    file_name=it["filename"],
                                    mime=it["mime_type"],
                                    key=f"dl_{prefix}_{cat_idx}_{item_idx}_{clean_path}",
                                    use_container_width=True,
                                )
        else:
            st.caption("Diretório de saída não localizado para carregar os arquivos.")

    with tabs[7]:
        st.json({k: v for k, v in result.state.items()})

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            "📥 PRD (Markdown)",
            data=result.state.get("prd_final") or result.final_output,
            file_name=f"PRD_{sid[:8]}.md",
            mime="text/markdown",
            key=f"prd_{prefix}",
            use_container_width=True,
        )
    with c2:
        st.download_button(
            "📥 Spec da missão",
            data=result.state.get("spec_missao") or "(spec não gerada)",
            file_name=f"spec_{sid[:8]}.md",
            mime="text/markdown",
            key=f"spec_{prefix}",
            use_container_width=True,
        )
    with c3:
        export = {"session_id": result.session_id, "prompt": result.prompt, "attached_files": result.attached_files, "duration_seconds": result.duration_seconds, "gates": gates, "output_dir": result.output_dir, "state": result.state}
        st.download_button(
            "📥 Estado completo (JSON)",
            data=json.dumps(export, indent=2, ensure_ascii=False, default=str),
            file_name=f"missao_{sid[:8]}.json",
            mime="application/json",
            key=f"state_{prefix}",
            use_container_width=True,
        )
    if result.output_dir:
        st.caption(f"Artefatos gravados em `{result.output_dir}`")


def render_prompt_manager():
    st.markdown("### 📝 Prompts dos agentes")
    st.markdown("Cada agente lê um arquivo Markdown em `prompts/<área>/`. Diretivas `<!-- include: references/… -->` inserem conhecimento compartilhado em tempo de carga; `{chave}` / `{chave?}` são interpoladas pelo ADK a partir do estado da sessão.")
    areas = list_prompt_files()
    metadata = {m["prompt_file"]: m for m in get_pipeline_agents_metadata(active_only=False) if m.get("prompt_file")}
    area = st.selectbox("Área", list(areas), format_func=lambda a: {"produto": "🧭 Produto", "design": "🎨 Design", "dev": "🛠️ Dev", "transversal": "🧠 Transversal"}.get(a, a))
    fname = st.selectbox("Arquivo", areas[area], format_func=lambda f: f"{metadata.get(f'{area}/{f}', {}).get('name', f)}  ({f})")
    rel = f"{area}/{fname}"
    meta = metadata.get(rel)
    if meta:
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"**Agente:** `{meta['id']}`")
        c2.markdown(f"**Chave de saída:** `{meta['output_key']}`")
        c3.markdown(f"**Arquivo:** `prompts/{rel}`")
        st.info(f"💡 {meta['description']}")

    raw = get_prompt_raw(rel)
    tab_edit, tab_final = st.tabs(["✏️ Editar (fonte)", "👁️ Prompt final (includes resolvidos)"])
    with tab_edit:
        edited = st.text_area("Conteúdo", value=raw, height=520, key=f"ta_{rel}")
        c_save, c_reload, _ = st.columns([1.5, 1.5, 4])
        if c_save.button("💾 Salvar", type="primary", key=f"save_{rel}", use_container_width=True):
            save_prompt(rel, edited)
            st.success(f"✅ `{rel}` salvo. As próximas execuções usarão esta versão.")
        if c_reload.button("🔄 Recarregar", key=f"reload_{rel}", use_container_width=True):
            st.rerun()
    with tab_final:
        s = get_settings()
        try:
            final = load_prompt(rel, figma_mcp_mode=s.figma_mcp_mode, figma_folder_url=s.figma_default_folder_url or "(não configurada)", figma_ds_file_key=s.figma_ds_file_key, figma_ds_v02_file_key=s.figma_ds_v02_file_key)
            st.caption(f"{len(final):,} caracteres após includes")
            st.code(final, language="markdown")
        except Exception as exc:
            st.error(f"Erro ao resolver includes: {exc}")

    st.markdown("---")
    st.markdown("#### 📚 Referências compartilhadas (`prompts/references/`)")
    from prompts import REFERENCES_DIR

    refs = sorted(p.relative_to(REFERENCES_DIR).as_posix() for p in REFERENCES_DIR.rglob("*.md"))
    ref = st.selectbox("Referência", refs)
    ref_raw = get_prompt_raw(f"references/{ref}")
    ref_edit = st.text_area("Conteúdo da referência", value=ref_raw, height=380, key=f"ref_{ref}")
    if st.button("💾 Salvar referência", key=f"save_ref_{ref}"):
        save_prompt(f"references/{ref}", ref_edit)
        st.success(f"✅ `references/{ref}` salva.")


def main():
    init_session_state()
    opts = render_sidebar()

    st.markdown("<h1 class='main-header'>Gerador de Missões</h1>", unsafe_allow_html=True)
    st.markdown("**Produto → Design (Figma MCP) → Dev** · pipeline multiagente no Google ADK que transforma um one-pager em um **PRD padrão ouro** pronto para codificação.")
    st.markdown("---")

    tab_chat, tab_prompts = st.tabs(["💬 Pipeline", "📝 Prompts e referências"])

    with tab_chat:
        for idx, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("pipeline_result"):
                    render_pipeline_details(msg["pipeline_result"], key_prefix=f"msg_{idx}")

        doc_batch: Optional[DocumentBatch] = None
        with st.expander("📎 Anexar one-pager / documentos de apoio (PDF ou Word — até 10 arquivos / 25 MB)", expanded=False):
            uploaded = st.file_uploader("Arquivos para o agente P0 (one-pager):", type=["pdf", "docx", "doc"], accept_multiple_files=True, key="docs")
            if uploaded:
                batch, err = validate_and_process_batch(uploaded)
                if err:
                    st.error(err)
                elif batch:
                    doc_batch = batch
                    st.success(f"✅ {batch.files_count} arquivo(s) — {batch.total_mb:.2f} MB")

        user_prompt = st.chat_input("Descreva a missão (ano, ambiente, descoberta central, decisão do estudante) ou envie o one-pager…")
        if user_prompt:
            settings = get_settings()
            if not settings.is_gemini_configured():
                st.warning("⚠️ `GOOGLE_API_KEY` não configurada no `.env`.")
            display = user_prompt
            if doc_batch and doc_batch.documents:
                display += "\n\n📎 **Anexos:** " + ", ".join(f"`{d.name}`" for d in doc_batch.documents)
            st.session_state.messages.append({"role": "user", "content": display})
            with st.chat_message("user"):
                st.markdown(display)

            with st.chat_message("assistant"):
                progress = st.empty()
                steps = st.empty()
                progress.info("🚀 Iniciando o orquestrador…")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(execute_pipeline(user_prompt, opts, progress, steps, doc_batch))
                finally:
                    loop.close()
                if result:
                    summary = result.state.get("prd_final") and "📘 **PRD gerado.** Veja as abas abaixo." or result.final_output
                    st.markdown(summary if len(summary) < 4000 else summary[:4000] + "\n\n…")
                    render_pipeline_details(result, key_prefix="live")
                    st.session_state.messages.append({"role": "assistant", "content": summary if len(summary) < 4000 else "Resultado do pipeline:", "pipeline_result": result})
                    if result.output_dir:
                        dir_name = Path(result.output_dir).name
                        st.session_state.current_session_id = dir_name
                        try:
                            from pipeline.session_store import save_session_record
                            save_session_record(
                                run_dir=Path(result.output_dir),
                                session_id=result.session_id,
                                user_id=result.user_id,
                                prompt=user_prompt,
                                result=result,
                                messages=st.session_state.messages,
                                attached_files=[d.name for d in doc_batch.documents] if doc_batch else [],
                            )
                        except Exception as exc:
                            pass

    with tab_prompts:
        render_prompt_manager()


if __name__ == "__main__":
    main()
