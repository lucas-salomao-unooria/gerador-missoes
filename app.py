"""Interface Streamlit do Gerador de Missões Unooria.

Pipeline Produto → Design (Mermaid + Stitch) → Dev, orquestrado pelo Google ADK,
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
import streamlit.components.v1 as components
from PIL import Image

from config import get_settings
from pipeline.artifacts import generate_artifact_manifest
from pipeline.orchestrator import STAGES, get_pipeline_agents_metadata, get_pipeline_stages
from pipeline.runner import PipelineExecutionResult, run_orchestrator_pipeline_stream
from pipeline.session_store import (
    create_session_zip,
    delete_saved_session,
    extrair_metadados_frontmatter,
    extrair_titulo_missao,
    formatar_status_label,
    list_saved_sessions,
    load_saved_session,
    resolve_session_dir,
)
from prompts import get_prompt_raw, list_prompt_files, load_prompt, save_prompt
from tools.doc_parser import DocumentBatch, validate_and_process_batch
from tools.markdown_blocos import sanear_para_streamlit

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
    div[data-testid="stVerticalBlockBorderWrapper"] ::-webkit-scrollbar {
      width: 5px;
      height: 5px;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] ::-webkit-scrollbar-thumb {
      background: rgba(128, 128, 128, 0.35);
      border-radius: 4px;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] ::-webkit-scrollbar-thumb:hover {
      background: rgba(128, 128, 128, 0.6);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        min-width: 400px;
        max-width: 600px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

GATE_LABELS = {
    "micro_gate_status": "Micro-gate do núcleo",
    "gate_estrutural_status": "Gate estrutural",
    "gate_final_status": "Gate final de produto",
    "bncc_status": "Conformidade BNCC Computação",
    "lacunas_status": "Fechamento de lacunas",
    "ambiente_status": "Ambiente simulado",
    "design_status": "QA de design",
    "manifesto_status": "Ficha do manifesto",
    "telemetria_status": "Telemetria e arquitetura",
    "rastro_lacunas_status": "Rastro de lacunas",
    "dev_status": "Banca de dev",
    "prd_status": "Pendências do PRD",
    "diagnostico_status": "Diagnóstico da execução",
}


def _status_icon(value: Any) -> str:
    val = str(value).strip().lower()
    if val in ("aprovado", "success", "concluido", "concluído", "liberada", "apto", "verde", "🟢"):
        return "🟢"
    if val in ("bloqueado", "blocked", "bloqueada", "devolvido", "nao_apto", "não apto", "vermelho", "🔴"):
        return "🔴"
    if val in ("bypassed", "bypass", "amarelo", "🟡", "ressalvas", "ressalva", "alerta", "warning", "apto_com_ressalvas"):
        return "🟡"
    return "⚪"


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
                    "**Design** (briefing de ofício, jornada e fluxo em Mermaid, copy, telas no Stitch, protótipo HTML, QA) "
                    "e **Dev** (handoff, brief de assets, banca de validação em 5 dimensões) e entrega um "
                    "**PRD padrão ouro** com o contexto arquitetural da plataforma, pronto para um agente de codificação.\n\n"
                    "💡 *Anexe o one-pager em PDF/DOCX ou descreva: ano/série, ambiente simulado "
                    "(Instagram, YouTube, ChatGPT, TikTok ou WhatsApp), descoberta central e a decisão do estudante.*"
                ),
                "pipeline_result": None,
            }
        ]


@st.cache_data(show_spinner=False)
def _listar_sessoes_cached(_assinatura: str) -> List[Dict[str, Any]]:
    return list_saved_sessions()


def listar_sessoes() -> List[Dict[str, Any]]:
    """Histórico da sidebar, cacheado por uma assinatura barata do diretório de saída.

    `list_saved_sessions()` era chamada a cada rerun — inclusive ao digitar no filtro ou
    mexer em qualquer widget. A assinatura é (nome, mtime da pasta, mtime do conversa.json)
    das subpastas: muda quando uma missão é criada, removida ou regravada, e custa um
    `scandir` mais um `stat` por sessão, sem ler nenhum arquivo.

    O mtime do `conversa.json` entra porque, no bucket via GCS-FUSE, a "pasta" é um objeto
    marcador cuja data não muda quando os arquivos dentro dela mudam — uma sessão reexecutada
    por `scripts/rerodar_etapa.py` continuava 🔴 na lista até o processo reiniciar (2026-09-21).
    """
    def _mtime(caminho: Path) -> int:
        try:
            return int(caminho.stat().st_mtime)
        except OSError:
            return 0

    try:
        base = get_settings().output_path
        assinatura = repr(sorted(
            (p.name, _mtime(p), _mtime(p / "conversa.json"))
            for p in base.iterdir()
            if p.is_dir() and not p.name.startswith(".")
        ))
    except (FileNotFoundError, NotADirectoryError):
        assinatura = "[]"
    return _listar_sessoes_cached(assinatura)


@st.cache_data(show_spinner=False)
def _manifesto_cached(_assinatura: str, output_path: str) -> List[Dict[str, Any]]:
    return generate_artifact_manifest(Path(output_path))


def manifesto_da_sessao(output_path: Path) -> List[Dict[str, Any]]:
    """Manifesto de artefatos cacheado pelo mtime da pasta da missão.

    O `rglob` + `stat` de ~47 arquivos é barato em disco local, mas vira 47 RPCs quando o
    `OUTPUT_DIR` está montado via GCS-FUSE no Cloud Run — e rodava a cada rerun.
    """
    try:
        assinatura = f"{output_path}:{int(output_path.stat().st_mtime)}"
    except OSError:
        assinatura = str(output_path)
    return _manifesto_cached(assinatura, str(output_path))


def invalidar_cache_sessoes() -> None:
    """Limpa os caches de histórico após qualquer escrita em `output/`."""
    _listar_sessoes_cached.clear()
    _manifesto_cached.clear()


def tratar_retorno_oauth_miro() -> None:
    """Fecha a conexão com o Miro quando o navegador volta com `?code=…`.

    Roda antes de qualquer coisa desenhar: o retorno do OAuth é uma sessão nova do
    Streamlit, e a query string precisa ser consumida e limpa antes do primeiro rerun,
    senão o código de autorização fica preso na URL e é reapresentado (já usado) a cada
    interação.
    """
    params = st.query_params
    code = params.get("code")
    if not code:
        return

    from tools import miro_oauth

    try:
        estado = miro_oauth.concluir_conexao(code, params.get("state", ""))
        st.session_state["miro_aviso"] = (
            "success",
            f"✅ Miro conectado — o token expira em {estado.get('expira_em_min', '?')} min e renova sozinho.",
        )
    except Exception as exc:  # a UI não pode quebrar por causa de uma conexão externa
        st.session_state["miro_aviso"] = ("error", f"❌ Não deu para conectar ao Miro: {exc}")

    st.query_params.clear()


def render_integracoes(settings) -> None:
    """Card de integrações: status do Stitch e conexão OAuth do Miro."""
    from tools import miro_oauth

    st.markdown("#### 🔌 Integrações")
    with st.container(border=True):
        st.markdown(f"🎨 **Stitch (telas):** {settings.stitch_status_label}")

        aviso = st.session_state.pop("miro_aviso", None)
        if aviso:
            (st.success if aviso[0] == "success" else st.error)(aviso[1])

        if not settings.is_miro_enabled:
            st.markdown(f"🪞 **Miro (diagramas):** {settings.miro_status_label}")
            return

        try:
            estado = miro_oauth.token_store().status()
            rotulo = miro_oauth.status_label()
        except Exception as exc:
            st.markdown(f"🪞 **Miro (diagramas):** 🔴 {exc}")
            return

        st.markdown(f"🪞 **Miro (diagramas):** {rotulo}")

        if estado.get("conectado"):
            if st.button("Desconectar do Miro", use_container_width=True, key="miro_desconectar"):
                miro_oauth.token_store().apagar()
                st.rerun()
            return

        if st.button("🔗 Conectar ao Miro", use_container_width=True, key="miro_conectar"):
            try:
                st.session_state["miro_url_autorizacao"] = miro_oauth.iniciar_conexao()
            except Exception as exc:
                st.error(f"❌ Não deu para preparar a conexão: {exc}")

        url = st.session_state.get("miro_url_autorizacao")
        if url:
            # Link sem `target`: a autorização tem de acontecer NESTA aba. Numa aba nova,
            # o retorno cairia numa janela diferente da que o usuário está olhando.
            st.markdown(
                f'<a href="{url}" style="display:block;text-align:center;padding:.5rem;'
                'border-radius:.5rem;background:#4262ff;color:#fff;text-decoration:none;font-weight:600">'
                "Autorizar no Miro →</a>",
                unsafe_allow_html=True,
            )
            st.caption("Você escolhe o time no Miro e volta para cá automaticamente.")


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
        saved_sessions = listar_sessoes()
        total_sessions = len(saved_sessions)
        header_title = f"#### 🗂️ Histórico de Missões ({total_sessions})" if total_sessions > 0 else "#### 🗂️ Histórico de Missões"
        st.markdown(header_title)

        if not saved_sessions:
            st.caption("Nenhuma missão gravada ainda.")
        else:
            filtered_sessions = saved_sessions
            if total_sessions > 5:
                search_query = st.text_input(
                    "Filtrar missões",
                    placeholder="🔍 Filtrar histórico...",
                    label_visibility="collapsed",
                    key="history_search_query",
                ).strip().lower()
                if search_query:
                    filtered_sessions = [
                        s for s in saved_sessions
                        if search_query in s.get("title", "").lower() or search_query in s.get("dir_name", "").lower()
                    ]

            if not filtered_sessions:
                st.caption("Nenhuma missão encontrada com o filtro.")
            else:
                container_height = min(360, max(120, len(filtered_sessions) * 52))
                with st.container(height=container_height, border=True):
                    for s in filtered_sessions:
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
                                help=f"{s['title']}\n📅 {s['created_at']} | Status: {s.get('status_label', s['status'])} | 📄 {s['files_count']} arquivos",
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
                                invalidar_cache_sessoes()
                                if st.session_state.get("current_session_id") == s["dir_name"]:
                                    st.session_state.current_session_id = None
                                    st.session_state.messages = []
                                    init_session_state()
                                st.rerun()

        st.markdown("---")
        render_integracoes(settings)

        st.markdown("---")
        # st.markdown("#### 📡 Ambiente (`.env`)")
        # with st.container(border=True):
        #     st.markdown(f"🤖 **Modelo:** `{settings.gemini_model}`")
        #     st.markdown(f"🔑 **Gemini API:** {'🟢 configurada' if settings.is_gemini_configured() else '🔴 ausente'}")

        # st.markdown("---")
        # st.markdown("#### ⚙️ Execução")
        # stage_options = {"Produto": "produto", "Design": "design", "Dev": "dev"}
        # default_stages = [k for k, v in stage_options.items() if v in settings.pipeline_stages]
        # chosen = st.multiselect("Etapas ativas", list(stage_options), default=default_stages, help="Desligue etapas para testar só parte do pipeline.")
        # stages = [stage_options[c] for c in chosen] or ["produto"]

        stages = ["produto", "design", "dev"]

        # modo_estrito = st.toggle(
        #     "Modo estrito dos gates de produto",
        #     value=settings.produto_modo_estrito,
        #     help="Ligado: missão bloqueada no gate estrutural (após as rodadas) ou no gate final interrompe design e dev. "
        #     "Desligado: o pipeline segue e o PRD registra as pendências.",
        # )

        modo_estrito=True
            

        thinking_presets = {"Desativado": 0, "Rápido": 1024, "Equilibrado": 2048, "Aprofundado": 4096, "Avançado": 8192, "Máximo": 16384, "Automático": -1}
        by_val = {v: k for k, v in thinking_presets.items()}
        selected_label = st.select_slider("Nível de raciocínio", options=list(thinking_presets), value=by_val.get(settings.thinking_budget, "Avançado"))
        # include_thoughts = st.toggle("Exibir pensamentos dos agentes", value=settings.include_thoughts)
        include_thoughts=True

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


def update_pipeline_step_status(
    status: Dict[str, str],
    active_agent: Optional[str],
    event: Dict[str, Any],
    gates: Dict[str, Any],
) -> Optional[str]:
    """Atualiza o status dos agentes (pending, running, done, skipped) com base no evento do pipeline.
    
    Garante que agentes como o Revisor do one-pager (que só roda em caso de reprovação no gate)
    fiquem verdes (done) quando o gate estrutural aprova de primeira sem necessidade de correções.
    """
    et = event.get("type")
    if et == "agent_started":
        name = event.get("agent_name", "")
        if active_agent and status.get(active_agent) == "running":
            status[active_agent] = "done"
        active_agent = name
        if name in status:
            status[name] = "running"

        # Se avançou para agentes posteriores ao gate estrutural e o revisor ainda está pendente:
        if name not in (
            "A01NucleoNarrativo",
            "A02MicroGate",
            "A03MicroGateCheck",
            "A04SecoesApoio",
            "A05GateEstrutural",
            "A06GateEstruturalCheck",
            "A07RevisorOnePager",
        ):
            ge_st = str(gates.get("gate_estrutural_status", "")).strip().lower()
            if ge_st in ("aprovado", "success", "concluido", "concluído", "liberada", "apto", "verde", "🟢"):
                if status.get("A07RevisorOnePager") == "pending":
                    status["A07RevisorOnePager"] = "done"
            if status.get("A06GateEstruturalCheck") == "running":
                status["A06GateEstruturalCheck"] = "done"

    elif et == "agent_chunk":
        name = event.get("agent_name", "")
        if "não executado" in (event.get("chunk") or "") and name in status:
            status[name] = "skipped"

    elif et == "gate_status":
        new_status = event.get("status") or {}
        gates.update(new_status)
        ge_st = str(new_status.get("gate_estrutural_status") or gates.get("gate_estrutural_status") or "").strip().lower()
        if ge_st in ("aprovado", "success", "concluido", "concluído", "liberada", "apto", "verde", "🟢"):
            if status.get("A07RevisorOnePager") == "pending":
                status["A07RevisorOnePager"] = "done"
            if status.get("A06GateEstruturalCheck") == "running":
                status["A06GateEstruturalCheck"] = "done"
        if new_status.get("gate_final_status") and status.get("A12GateFinalProdutoCheck") == "running":
            status["A12GateFinalProdutoCheck"] = "done"
        if new_status.get("design_status") and status.get("A31QaEntregaveisCheck") == "running":
            status["A31QaEntregaveisCheck"] = "done"
        if new_status.get("dev_status") and status.get("A45ValidacaoDevCheck") == "running":
            status["A45ValidacaoDevCheck"] = "done"

    elif et == "pipeline_completed":
        result = event.get("result")
        is_blocked = getattr(result, "bloqueado", False) if result else False
        res_state = getattr(result, "state", {}) if result else {}

        for k in status:
            if status[k] == "running":
                status[k] = "done"

        # Se o gate estrutural foi aprovado (ou o pipeline avançou), o revisor fica concluído (verde):
        # O revisor do one-pager só roda quando o gate reprova: aprovado de primeira, ele
        # não tem o que corrigir — e isso é sucesso, não passo pulado.
        if status.get("A07RevisorOnePager") == "pending":
            status["A07RevisorOnePager"] = "done"

        # Nenhum agente deve permanecer indefinidamente com ícone de ampulheta (pending) após
        # conclusão. A esteira não pula mais ninguém por causa de gate reprovado: quem ficou
        # pendente aqui é agente condicional que não se aplicava à missão.
        for k in status:
            if status[k] == "pending":
                status[k] = "skipped"

    return active_agent


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
        active_agent = update_pipeline_step_status(status, active_agent, event, gates)

        if et == "agent_started":
            name = event["agent_name"]
            progress.info(f"🔄 Executando **{name}**…")
            render()
        elif et == "agent_chunk":
            if "não executado" in (event.get("chunk") or ""):
                render()
        elif et == "agent_tool_call":
            tool_log.append(f"{event['agent_name']} → {', '.join(event['tools'])}")
            progress.info(f"🧰 **{event['agent_name']}** chamou `{', '.join(event['tools'])}`")
        elif et == "agent_thought_chunk":
            progress.info(f"🧠 **{event['agent_name']}** raciocinando…")
        elif et == "gate_status":
            render()
        elif et == "pipeline_completed":
            result = event["result"]
            render()
            if result.bloqueado:
                motivo = getattr(result, "gate_que_bloqueou", None) or "gate de produto"
                progress.warning(
                    f"⛔ Missão bloqueada em **{result.duration_seconds:.0f}s** — **{motivo}**. "
                    f"O PRD não foi gerado; o relatório do gate diz o que faltou e de quem."
                )
            elif getattr(result, "bypassed", False):
                progress.warning(f"⚠️ Pipeline concluído com gates bypassados em **{result.duration_seconds:.0f}s**. PRD gerado com pendências — artefatos em `{result.output_dir}`.")
            else:
                progress.success(f"🎉 Pipeline concluído em **{result.duration_seconds:.0f}s**. Artefatos em `{result.output_dir}`.")
        elif et == "pipeline_error":
            result = event["result"]
            progress.error(f"❌ Erro: {event.get('error')}")
            render()
    if tool_log:
        with st.expander(f"🧰 Chamadas de ferramenta ({len(tool_log)})"):
            st.code("\n".join(tool_log))
    return result


def _supports_deferred_download() -> bool:
    """Informa se esta versão do Streamlit sabe gerar o arquivo só no clique."""
    try:
        from streamlit.runtime.media_file_manager import MediaFileManager
    except Exception:
        return False
    return hasattr(MediaFileManager, "add_deferred")


_DEFERRED_DOWNLOADS = _supports_deferred_download()


def download_button_lazy(
    label: str,
    data_fn,
    *,
    file_name: str,
    mime: str,
    key: str,
    help: Optional[str] = None,
    use_container_width: bool = True,
) -> bool:
    """Botão de download que materializa os bytes apenas quando o usuário clica.

    O modo antigo (bytes prontos a cada render) guardava o arquivo inteiro no
    MediaFileManager do Streamlit, que vive só na memória da instância. Quando a
    instância do Cloud Run reiniciava ou o coletor de mídia descartava o blob, a URL
    `/media/<hash>` que o navegador tinha respondia 404 — o erro de "arquivo não
    encontrado" mesmo com tudo íntegro no Cloud Storage.

    `on_click="ignore"` evita que o clique dispare um rerun; é o rerun que limpa as
    referências de mídia ainda em uso e leva o arquivo à coleta.
    """
    common = {
        "label": label,
        "file_name": file_name,
        "mime": mime,
        "key": key,
        "help": help,
        "use_container_width": use_container_width,
    }
    if _DEFERRED_DOWNLOADS:
        return st.download_button(data=data_fn, on_click="ignore", **common)

    # Streamlit antigo: sem geração adiada, resta materializar agora. Uma falha de
    # leitura aqui não pode derrubar a página inteira.
    try:
        payload = data_fn()
    except Exception as exc:
        st.error(f"❌ Falha ao preparar `{file_name}`: {exc}")
        return False
    return st.download_button(data=payload, **common)


def render_saida_agente(value: str, output_key: str, prefix: str):
    """Renderiza a saída de um agente na aba da etapa.

    Saídas em HTML (o protótipo) não passam por `st.markdown`: são 80 KB+ de HTML cru que o
    parser de markdown do Streamlit reprocessava e reenviava a cada rerun. Aqui o HTML só é
    montado quando o usuário pede a pré-visualização.
    """
    if output_key in ("prototipo_html", "prototipo_arquivo") or value.lstrip()[:15].lower().startswith("<!doctype html"):
        st.caption(f"Protótipo em HTML · {len(value) / 1024:.0f} KB")
        col_prev, col_dl = st.columns([1, 1])
        with col_prev:
            mostrar = st.toggle("👁️ Pré-visualizar", key=f"prev_{prefix}")
        with col_dl:
            download_button_lazy(
                "📥 Baixar HTML",
                lambda v=value: v,
                file_name=f"{output_key}.html",
                mime="text/html",
                key=f"dlhtml_{prefix}",
            )
        if mostrar:
            components.html(value, height=600, scrolling=True)
        return

    st.markdown(sanear_para_streamlit(value))


def render_pipeline_details(result: PipelineExecutionResult, key_prefix: str = ""):
    st.markdown("---")
    gates = result.gates
    sid = str(getattr(result, "session_id", None) or "session")
    prefix = f"{key_prefix}_{sid}" if key_prefix else f"{sid}_{id(result)}"

    # Título principal da missão e status amigável
    mission_title = extrair_titulo_missao(result.state, fallback="Missão")
    prd_text = getattr(result, "prd_gerado", None) or result.final_output
    prd_meta, _ = extrair_metadados_frontmatter(prd_text)

    # O status da missão reflete o veredito dos gates do pipeline
    if getattr(result, "bloqueado", False):
        mission_status = "bloqueado"
    elif getattr(result, "bypassed", False):
        mission_status = "bypassed"
    elif getattr(result, "status", None) in ("success", "aprovado"):
        mission_status = "aprovado"
    else:
        mission_status = getattr(result, "status", "aprovado")

    status_label = formatar_status_label(mission_status)

    col_t1, col_t2 = st.columns([4, 1.5])
    with col_t1:
        st.markdown(f"### 🎯 {mission_title}")
    with col_t2:
        st.markdown(f"**Status:** {status_label}")

    if gates:
        st.markdown("**Gates:** " + " · ".join(f"{_status_icon(v)} {GATE_LABELS[k]}" for k, v in gates.items() if k in GATE_LABELS))
    if getattr(result, "bypassed", False):
        st.warning("⚠️ **Atenção:** Esta missão avançou com gates bloqueados (modo estrito desativado / bypass). Verifique as pendências nos relatórios e na seção 20 do PRD.")
    # As seções são montadas sob demanda. `st.tabs` renderiza *todas* as abas no servidor —
    # uma aba fechada custa o mesmo que uma aberta — e isso fazia cada rerun enviar ~2 MB
    # (estado JSON + 48 expanders de markdown) ao navegador.
    ABAS = ["📘 PRD", "🧭 Produto", "🎨 Design", "🛠️ Dev", "🧠 Aprendizado", "💭 Pensamentos", "📦 Artefatos", "🔍 Estado (JSON)"]
    aba = st.segmented_control("Seções", ABAS, default=ABAS[0], key=f"aba_{prefix}", label_visibility="collapsed") or ABAS[0]

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
                if meta.get("id") == "A07RevisorOnePager" and "A07RevisorOnePager" not in (result.step_outputs or {}):
                    st.caption("ℹ️ *One-pager aprovado no gate estrutural sem necessidade de revisão. Exibindo a versão aprovada:*")
                render_saida_agente(value, output_key=key, prefix=f"{prefix}_{key}")
        if not shown:
            st.caption("Nenhuma saída registrada para esta etapa.")

    if aba == ABAS[0]:
        if prd_text:
            meta, body = extrair_metadados_frontmatter(prd_text)
            if meta:
                with st.expander("📋 Metadados do PRD", expanded=False):
                    m_c1, m_c2, m_c3 = st.columns(3)
                    m_c1.markdown(f"**ID:** `{meta.get('prd_id', '-')}`")
                    m_c1.markdown(f"**Versão:** `{meta.get('versao', '0.1.0')}`")
                    m_c2.markdown(f"**Série:** `{meta.get('serie', '-')}`")
                    m_c2.markdown(f"**Ambiente:** `{meta.get('ambiente_simulado', '-')}`")
                    m_c3.markdown(f"**Data:** `{meta.get('data', '-')}`")
                    m_c3.markdown(f"**Slug:** `{meta.get('slug_experiencia', '-')}`")
                    if "owners" in meta:
                        st.markdown(f"**Owners:** `{meta['owners']}`")
                    if "links" in meta:
                        st.markdown(f"**Links:** `{meta['links']}`")
                st.markdown(sanear_para_streamlit(body))
            else:
                st.markdown(sanear_para_streamlit(prd_text))
        else:
            st.info("O PRD não foi gerado (pipeline bloqueado ou etapa Dev desligada). Abaixo, a saída mais relevante:")
            st.markdown(sanear_para_streamlit(result.final_output))

    elif aba == ABAS[1]:
        stage_tab("produto")
    elif aba == ABAS[2]:
        stage_tab("design")
    elif aba == ABAS[3]:
        stage_tab("dev")
    elif aba == ABAS[4]:
        stage_tab("transversal")
    elif aba == ABAS[5]:
        if any(result.step_thoughts.values()):
            for agent, thoughts in result.step_thoughts.items():
                if thoughts.strip():
                    with st.expander(f"🧠 {agent}"):
                        st.markdown(sanear_para_streamlit(thoughts))
        else:
            st.info("Nenhum pensamento registrado.")

    elif aba == ABAS[6]:
        # 1. Diagramas e telas geradas
        links = []
        if links:
            st.markdown("#### 🗺️ Diagramas e telas")
            cols = st.columns(min(len(links), 3) or 1)
            for idx, link in enumerate(links):
                with cols[idx % len(cols)]:
                    with st.container(border=True):
                        st.markdown(f"**{link.get('title', 'Artefato')}**")
                        st.caption(f"Origem: `{link.get('source_agent_key', 'design')}`")
                        st.link_button("Abrir ↗", link["url"], key=f"link_{prefix}_{idx}", use_container_width=True)
            st.markdown("---")
        else:
            st.info("🗺️ A jornada e o fluxo saem em Mermaid (`design/09-diagramas.html`) e as telas, no Stitch.")

        # 2. Manifesto de Arquivos
        st.markdown("#### 📁 Arquivos da Missão")
        # Resolve o diretório pelo nome sob o OUTPUT_DIR corrente quando o caminho
        # absoluto gravado na execução não existe mais (troca de ambiente, redeploy).
        output_path = resolve_session_dir(result.output_dir)
        if output_path is None:
            st.error(
                "❌ Não foi possível localizar a pasta desta missão para montar os downloads.\n\n"
                f"- Caminho registrado: `{result.output_dir or '(vazio)'}`\n"
                f"- `OUTPUT_DIR` em uso: `{get_settings().output_path}`"
            )
        else:
            manifest = manifesto_da_sessao(output_path)

            if not manifest:
                st.warning(f"Nenhum artefato legível em `{output_path}`.")
            else:
                total_bytes = sum(it["size_bytes"] for it in manifest)
                col_zip, col_info = st.columns([2, 2])
                with col_zip:
                    download_button_lazy(
                        "📦 Baixar Todos os Artefatos (.ZIP)",
                        lambda p=output_path: create_session_zip(p),
                        file_name=f"artefatos_{sid[:12]}.zip",
                        mime="application/zip",
                        key=f"zip_{prefix}",
                        help="O pacote é montado no momento do clique, a partir dos arquivos da missão.",
                    )
                with col_info:
                    st.caption(f"{len(manifest)} arquivos · {total_bytes / 1024:.0f} KB")
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
                            with c_dl:
                                clean_path = re.sub(r"[^a-zA-Z0-9_-]", "_", str(it.get("path", "")))
                                download_button_lazy(
                                    "📥 Baixar",
                                    lambda f=full_fpath: f.read_bytes(),
                                    file_name=it["filename"],
                                    mime=it["mime_type"],
                                    key=f"dl_{prefix}_{cat_idx}_{item_idx}_{clean_path}",
                                )

    elif aba == ABAS[7]:
        # O estado é uma cópia integral de todos os artefatos (~1 MB). `st.json` o enviava
        # inteiro e expandido a cada rerun; aqui vai o índice das chaves e a inspeção de
        # uma por vez, com o JSON completo disponível por download.
        chaves = sorted(result.state.keys(), key=lambda k: len(str(result.state.get(k, ""))), reverse=True)
        total_kb = sum(len(str(v)) for v in result.state.values()) / 1024
        col_est1, col_est2 = st.columns([2, 2])
        with col_est1:
            download_button_lazy(
                "📥 Baixar estado completo (.json)",
                lambda: json.dumps(result.state, indent=2, ensure_ascii=False, default=str),
                file_name=f"estado_{sid[:12]}.json",
                mime="application/json",
                key=f"estado_{prefix}",
            )
        with col_est2:
            st.caption(f"{len(chaves)} chaves · {total_kb:.0f} KB no total")

        if chaves:
            chave = st.selectbox(
                "Inspecionar chave",
                chaves,
                format_func=lambda k: f"{k} · {len(str(result.state.get(k, ''))) / 1024:.1f} KB",
                key=f"estadokey_{prefix}",
            )
            valor = result.state.get(chave)
            if isinstance(valor, str):
                LIMITE = 20000
                st.code(valor[:LIMITE] + ("\n\n… (truncado — use o download acima)" if len(valor) > LIMITE else ""))
            else:
                st.json(valor, expanded=False)
        else:
            st.caption("Estado vazio.")

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        download_button_lazy(
            "📥 PRD (Markdown)",
            lambda: getattr(result, "prd_gerado", None) or result.final_output,
            file_name=f"PRD_{sid[:8]}.md",
            mime="text/markdown",
            key=f"prd_{prefix}",
        )
    with c2:
        download_button_lazy(
            "📥 Spec da missão",
            lambda: result.state.get("spec_missao") or "(spec não gerada)",
            file_name=f"spec_{sid[:8]}.md",
            mime="text/markdown",
            key=f"spec_{prefix}",
        )
    with c3:
        def _exportar_estado() -> str:
            export = {
                "session_id": result.session_id,
                "prompt": result.prompt,
                "attached_files": result.attached_files,
                "duration_seconds": result.duration_seconds,
                "gates": gates,
                "output_dir": result.output_dir,
                "state": result.state,
            }
            return json.dumps(export, indent=2, ensure_ascii=False, default=str)

        download_button_lazy(
            "📥 Estado completo (JSON)",
            _exportar_estado,
            file_name=f"missao_{sid[:8]}.json",
            mime="application/json",
            key=f"state_{prefix}",
        )
    if result.output_dir:
        st.caption(f"Artefatos gravados em `{result.output_dir}`")


def render_prompt_manager():
    st.markdown("### 📝 Prompts dos agentes")
    st.markdown("Cada agente lê um arquivo Markdown em `prompts/<área>/`. Diretivas `<!-- include: references/… -->` inserem conhecimento compartilhado em tempo de carga; `{chave}` / `{chave?}` são interpoladas pelo ADK a partir do estado da sessão.")
    areas = list_prompt_files()

    # Um mesmo prompt pode ser lido por mais de um nó: o revisor do one-pager (07) roda de novo como
    # retrabalho dentro do loop de avaliações (10c). Vale a PRIMEIRA ocorrência, que é a posição
    # canônica do agente na esteira — indexar pela última fazia o arquivo 07 aparecer rotulado "10c",
    # e portanto fora de ordem no seletor.
    metadata: Dict[str, Dict[str, Any]] = {}
    reusos: Dict[str, List[str]] = {}
    for m in get_pipeline_agents_metadata(active_only=False):
        arquivo = m.get("prompt_file")
        if not arquivo:
            continue
        if arquivo in metadata:
            reusos.setdefault(arquivo, []).append(m["name"])
        else:
            metadata[arquivo] = m

    def _ordem_do_agente(rel: str) -> tuple[int, str]:
        """`12 · Veredito` → (12, ''), `10c · Revisor` → (10, 'c'). Ordena pela esteira, não pelo nome do arquivo."""
        nome = metadata.get(rel, {}).get("name", rel)
        achado = re.match(r"\s*(\d+)([a-z]*)", nome)
        return (int(achado.group(1)), achado.group(2)) if achado else (999, "")

    # Ordem da esteira, não alfabética: alfabética abria o editor em Design, no meio do pipeline.
    ordem_das_areas = ["produto", "design", "dev", "transversal"]
    lista_areas = sorted(areas, key=lambda a: ordem_das_areas.index(a) if a in ordem_das_areas else 99)
    area = st.selectbox("Área", lista_areas, format_func=lambda a: {"produto": "🧭 Produto", "design": "🎨 Design", "dev": "🛠️ Dev", "transversal": "🧠 Transversal"}.get(a, a))
    arquivos = sorted(areas[area], key=lambda f: _ordem_do_agente(f"{area}/{f}"))
    fname = st.selectbox("Arquivo", arquivos, format_func=lambda f: f"{metadata.get(f'{area}/{f}', {}).get('name', f)}  ({f})")
    rel = f"{area}/{fname}"
    meta = metadata.get(rel)
    if meta:
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"**Agente:** `{meta['id']}`")
        c2.markdown(f"**Chave de saída:** `{meta['output_key']}`")
        c3.markdown(f"**Arquivo:** `prompts/{rel}`")
        st.info(f"💡 {meta['description']}")
        if reusos.get(rel):
            st.caption(f"♻️ Este mesmo prompt também roda como: {', '.join(f'**{n}**' for n in reusos[rel])} — editar aqui muda os dois.")

    with st.expander(f"🔢 Por que a numeração pula números em {area.title()}?"):
        st.markdown(
            "A numeração é **global e segue a ordem de execução da esteira**, contando todos os "
            "agentes. Os números ausentes são **agentes determinísticos**: regras em Python, sem "
            "prompt para editar (vivem em `agents/checkers.py` e `tools/`). Eles aparecem abaixo em "
            "cinza para você localizar o número que procura."
        )
        linhas = []
        for m in get_pipeline_agents_metadata(active_only=False):
            if m.get("stage") != area:
                continue
            if m.get("prompt_file"):
                linhas.append(f"- {m['icon']} **{m['name']}** — `prompts/{m['prompt_file']}`")
            else:
                linhas.append(f"- {m['icon']} {m['name']} — _regra em código, não editável aqui_")
        st.markdown("\n".join(linhas) or "_Nenhum agente nesta área._")

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
            final = load_prompt(rel, gdrive_folder_url=s.gdrive_folder_url or "(não configurada)", stitch_mcp_mode=s.stitch_mcp_mode, stitch_project_url_base=s.stitch_project_url_base, gate_max_rodadas=s.gate_estrutural_max_rodadas, qa_max_rodadas=s.qa_design_max_rodadas)
            st.caption(f"{len(final):,} caracteres após includes")
            st.code(final, language="markdown")
        except Exception as exc:
            st.error(f"Erro ao resolver includes: {exc}")

    st.markdown("---")
    st.markdown("#### 📚 Referências compartilhadas (`prompts/references/`)")
    from prompts import REFERENCES_DIR

    # Os arquivos próprios vêm primeiro; as cópias da plataforma, agrupadas no fim. Ordenar tudo
    # junto pelo caminho enterrava as referências editáveis no meio de 45 cópias sincronizadas.
    todas = sorted(p.relative_to(REFERENCES_DIR).as_posix() for p in REFERENCES_DIR.rglob("*.md"))
    refs = [r for r in todas if "/" not in r] + [r for r in todas if "/" in r]

    def _rotulo_ref(r: str) -> str:
        pasta, _, nome = r.rpartition("/")
        return f"📁 {pasta} · {nome}" if pasta else f"📄 {r}"

    ref = st.selectbox("Referência", refs, format_func=_rotulo_ref)
    ref_raw = get_prompt_raw(f"references/{ref}")
    sincronizada = ref.startswith("plataforma/")
    if sincronizada:
        st.warning(
            "🔒 Cópia sincronizada do repositório `plataforma-unooria`. Editar aqui **não** muda a "
            "plataforma e a alteração é desfeita no próximo `python scripts/sincronizar_plataforma.py`. "
            "Para mudar de verdade, altere na origem e rode o script."
        )
    ref_edit = st.text_area("Conteúdo da referência", value=ref_raw, height=380, key=f"ref_{ref}", disabled=sincronizada)
    if st.button("💾 Salvar referência", key=f"save_ref_{ref}", disabled=sincronizada):
        save_prompt(f"references/{ref}", ref_edit)
        st.success(f"✅ `references/{ref}` salva.")


def render_guia_de_uso() -> None:
    """Como usar o gerador, acima do anexo — é onde a decisão de escrever o briefing acontece.

    A esteira é boa em estruturar, auditar e formalizar, e ruim em adivinhar o que não foi dito:
    por desenho ela prefere marcar uma lacuna a inventar conteúdo. Por isso a qualidade da entrada
    é o que mais mexe no resultado, e o lugar de dizer isso é aqui, não só na documentação.
    """
    st.markdown(
        "**Como usar:** ① anexe o material do bimestre (`.docx`/`.pdf`) — é dele que saem os "
        "códigos da BNCC e o contexto real · ② escreva no chat abaixo um briefing com **ano, "
        "bimestre, ambiente, a descoberta e o mecanismo** · ③ acompanhe as etapas e baixe o **PRD** "
        "e o **one-pager pedagógico** no fim. Portão reprovado **não** interrompe a execução: ela "
        "vai até o fim e o diagnóstico diz onde atuar."
    )
    with st.expander("🥇 Como escrever um bom briefing (padrão ouro) e o que evitar"):
        st.markdown("**Um briefing que funciona:**")
        st.code(
            """Missão para o 5º ano do Fundamental, 3º bimestre, no ambiente do YouTube (unitube).

Tema do bimestre (material Entre Redes anexado): como a recomendação de conteúdo
funciona e por que duas pessoas veem coisas diferentes.

O que quero que a criança descubra: que o que ela vê no feed não é "o que existe",
e sim o que o sistema aprendeu que ela costuma assistir.

Ideia de mecanismo: ela monta a playlist de um personagem a partir de um banco de
vídeos. Depois vê o feed que aquele personagem passa a receber. Dois colegas com
playlists diferentes recebem feeds diferentes, e isso fica visível na tela.

Restrições: 50 minutos, aula única, dois estudantes por tablet.
A professora precisa conseguir pausar a turma antes da revelação.

Em aberto: não sei se o banco deve ter 8 ou 12 vídeos.""",
            language="text",
        )
        st.markdown(
            "**Por que funciona:** ano e bimestre explícitos (sem eles o primeiro portão já "
            "reprova) · a descoberta está escrita **como descoberta**, não como objetivo de aula "
            "(*\"o que ela vê não é o que existe\"*, e não *\"vai aprender sobre algoritmos\"*) · "
            "há um **mecanismo**, uma cadeia de ações, não uma intenção · as **restrições de sala** "
            "aparecem (tempo, dispositivo, controle da professora) · a **dúvida está declarada**, "
            "então a esteira decide e registra a decisão em vez de decidir sem você saber."
        )
        st.markdown("---")
        st.markdown("**O que evitar:**")
        st.markdown(
            "| Entrada problemática | O que acontece |\n"
            "| --- | --- |\n"
            "| *\"Missão sobre fake news para o Fundamental.\"* | Sem ano, bimestre, ambiente nem "
            "mecanismo. A esteira inventa os quatro, e inventa o mais genérico possível. "
            "**Pior caso de uso da ferramenta.** |\n"
            "| *\"O estudante navega por um feed com posts falsos e descobre que foram "
            "manipulados.\"* | O briefing **entrega a virada**. Há um portão só para isso (agente "
            "02), mas o estrago já aconteceu: a ideia nasceu sem segredo. |\n"
            "| *\"Uma missão que desenvolva pensamento crítico e cidadania digital.\"* | Intenção "
            "sem mecanismo. Se você remover a frase, a missão continua igual — então ela não "
            "descreve nada construível. |\n"
            "| *\"O estudante avalia 15 perfis e classifica cada um como confiável ou não.\"* | "
            "15 decisões do mesmo tipo excedem o teto da faixa etária. Vira ressalva ou reprovação "
            "no agente 09. |\n"
            "| *\"Fazer no Roblox, que as crianças amam.\"* | Ambiente fora da lista fechada "
            "(Instagram, YouTube, ChatGPT, TikTok, WhatsApp). Não existe seção de design system "
            "para construir. |\n"
            "| *\"A criança conversa com a IA e reflete sobre o que aprendeu.\"* | Reflexão "
            "genérica. O critério pede uma **provocação concreta**: alguém que não fez a missão "
            "consegue responder? Se sim, não serve. |\n"
            "| Briefing de oito páginas com todas as telas já desenhadas. | A esteira vira "
            "transcritora — você paga ~50 chamadas para formatar o que já tinha. |\n"
        )
        st.info(
            "📎 **Anexos valem mais que adjetivos.** Dois parágrafos do material real do bimestre "
            "valem mais que uma página de descrição: é de lá que vêm os códigos da BNCC, que a "
            "esteira confere contra o anexo oficial do MEC."
        )


def main():
    tratar_retorno_oauth_miro()
    init_session_state()
    opts = render_sidebar()

    st.markdown("<h1 class='main-header'>Gerador de Missões</h1>", unsafe_allow_html=True)
    st.markdown("**Produto → Design → Dev** · pipeline multiagente no Google ADK que transforma um one-pager em um **PRD padrão ouro** pronto para codificação.")
    st.markdown("---")

    # Mesmo motivo das seções de `render_pipeline_details`: com `st.tabs`, o editor de
    # prompts era montado a cada rerun mesmo fechado — e ele resolve includes, chegando a
    # ~380 KB de payload por interação.
    SECOES = ["💬 Pipeline", "📝 Prompts e referências"]
    secao = st.segmented_control("Seção", SECOES, default=SECOES[0], key="secao_principal", label_visibility="collapsed") or SECOES[0]

    if secao == SECOES[0]:
        for idx, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("pipeline_result"):
                    render_pipeline_details(msg["pipeline_result"], key_prefix=f"msg_{idx}")

        render_guia_de_uso()

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
            # Inicia conversa limpa para a nova missão (evita acumular sessões anteriores)
            st.session_state.messages = [{"role": "user", "content": display}]
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
                    if getattr(result, "prd_gerado", None):
                        if getattr(result, "bypassed", False):
                            summary = "🟡 **PRD gerado com ressalvas (gates bypassados).** Veja as abas abaixo."
                        else:
                            summary = "📘 **PRD gerado.** Veja as abas abaixo."
                    elif getattr(result, "bloqueado", False):
                        motivo = getattr(result, "gate_que_bloqueou", None) or "um gate da esteira"
                        summary = (
                            f"⛔ **PRD não gerado — {motivo}.** A esteira parou no gate que faltou informação; "
                            f"o relatório dele, nas abas abaixo, diz o que faltou e quem resolve."
                        )
                    else:
                        summary = result.final_output
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
                            invalidar_cache_sessoes()
                        except Exception as exc:
                            pass

    else:
        render_prompt_manager()


if __name__ == "__main__":
    main()
