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
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

from config import get_settings
from pipeline import conversa_etapas, execucao_fundo, passagem
from pipeline.artifacts import generate_artifact_manifest
from pipeline.orchestrator import STAGES, get_pipeline_agents_metadata, get_pipeline_stages, stages_para_ui
from pipeline.reexecucao import (
    ETAPA_PARA_STAGES,
    PedidoCorrecao,
    RegistroCorrecao,
    Triagem,
    carregar_sessao,
    correcao_desfazivel,
    desfazer_correcao,
    executar_correcao_stream,
    historico_de,
    mensagem_de_correcao,
    triar_pedido,
)
from pipeline.runner import PipelineExecutionResult, run_orchestrator_pipeline_stream
from pipeline.session_store import (
    create_session_zip,
    delete_saved_session,
    extrair_metadados_frontmatter,
    extrair_titulo_missao,
    formatar_status_label,
    list_saved_sessions,
    load_saved_session,
    identificador_da_missao,
    nome_do_zip_de_artefatos,
    resolve_session_dir,
)
from prompts import get_prompt_raw, list_prompt_files, load_prompt
from tools.auth import (
    ROTULO_PAPEL,
    ConfiguracaoDeLoginAusente,
    Revogacoes,
    Sessao,
    autenticar,
    configuracao_de_login,
    emitir_token,
    validar_token,
)
from tools.doc_parser import EXTENSOES_ACEITAS, DocumentBatch, validate_and_process_batch
from tools.markdown_blocos import desembrulhar_documento, sanear_para_streamlit

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
    /* só aberta: com a largura mínima fixa, a barra recolhida deixava uma faixa com pedaços dela à esquerda */
    [data-testid="stSidebar"][aria-expanded="true"] {
        min-width: 400px;
        max-width: 600px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

GATE_LABELS = {
    "micro_gate_status": "Micro-gate do núcleo",
    "fidelidade_nucleo_status": "Fidelidade ao pedido do PO (núcleo)",
    "mecanica_status": "Conta da virada",
    "fidelidade_status": "Fidelidade ao pedido do PO e ao briefing",
    "gate_estrutural_status": "Gate estrutural",
    "gate_final_status": "Gate final de produto",
    "bncc_status": "Conformidade BNCC Computação",
    "lacunas_status": "Fechamento de lacunas",
    "ambiente_status": "Ambiente simulado",
    "consistencia_status": "Coerência entre documentos",
    "stitch_status": "Telas no Stitch × inventário",
    "qa_afirmacoes_status": "Afirmações do QA conferidas",
    "design_status": "QA de design",
    "manifesto_status": "Ficha do manifesto",
    "conteudo_status": "Banco de conteúdo",
    "telemetria_status": "Telemetria e arquitetura",
    "rastro_spec_status": "Rastro de lacunas da spec",
    "rastro_design_status": "Rastro de lacunas do design",
    "rastro_lacunas_status": "Rastro de lacunas",
    "dev_status": "Banca de dev",
    "prd_status": "Pendências do PRD",
    "diagnostico_status": "Diagnóstico da execução",
}


# Os gates novos entravam na esteira e ficavam sem rótulo aqui: o semáforo mostrava `kpis_status` cru
# (24/09/2026). O diagnóstico já tem o rótulo de cada gate; o dicionário acima só troca o nome.
from tools.diagnostico import GATES as _GATES_DO_DIAGNOSTICO  # noqa: E402

for _g in _GATES_DO_DIAGNOSTICO:
    GATE_LABELS.setdefault(_g["status"], _g["rotulo"])


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
    if "correcao_pendente" not in st.session_state:
        st.session_state.correcao_pendente = None
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
                    "(Instagram, YouTube, ChatGPT, TikTok ou WhatsApp), descoberta central e a decisão do estudante.*\n\n"
                    "💬 *Com uma missão aberta no histórico, o campo de mensagem **pergunta à etapa** que você "
                    "escolher (produto, design ou dev), sem mudar nada. Para mudar a missão, use Refazer no cartão "
                    "de passagem. Numa missão sem parecer humano, ele pede a correção direto.*"
                ),
                "pipeline_result": None,
            }
        ]


@st.cache_data(show_spinner=False)
def _listar_sessoes_cached(assinatura: str) -> List[Dict[str, Any]]:
    # sem `_` no nome: o `st.cache_data` deixa de fora da chave todo parâmetro que começa com `_`,
    # e a assinatura nunca invalidava o cache — missão gravada por outro processo (o script de
    # reexecução, a etapa em segundo plano) não aparecia até alguém chamar `.clear()`
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
def _manifesto_cached(assinatura: str, output_path: str) -> List[Dict[str, Any]]:
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


# ------------------------------------------------------------------ login
def _revogacoes() -> Revogacoes:
    return Revogacoes(get_settings().output_path / ".auth" / "revogados.json")


def sessao_atual() -> Optional[Sessao]:
    """Quem está logado nesta sessão do Streamlit. `exigir_login` garante que existe em `main`."""
    return st.session_state.get("auth_sessao")


def exigir_login() -> Sessao:
    """Devolve a sessão válida ou desenha só o formulário de login e para o script.

    O token vive em `st.session_state` durante a aba e num cookie (`tools/cookie_sessao.py`) para
    sobreviver ao recarregar. A expiração é absoluta, 4 h depois do login, conferida a cada rerun.
    As revogações ("Sair") são lidas só quando o token chega pelo cookie, isto é, uma vez por aba:
    dentro da aba, sair já apaga o token do estado, e reler o arquivo do bucket a cada rerun
    custaria uma RPC do GCS-FUSE por clique.
    """
    from tools.cookie_sessao import apagar_cookie, gravar_cookie, ler_cookie

    settings = get_settings()
    try:
        cfg = configuracao_de_login(settings.auth_credenciais, settings.auth_segredo_jwt, settings.auth_horas_sessao)
    except ConfiguracaoDeLoginAusente as exc:
        st.error(f"🔒 O login não está configurado: {exc}. Gere as credenciais com "
                 "`python scripts/gerar_credenciais.py --env` (local) ou publique os segredos no Secret Manager.")
        st.stop()

    agora = time.time()
    token = st.session_state.get("auth_token")
    veio_do_cookie = False
    if not token and not st.session_state.get("auth_saiu"):
        token = ler_cookie()
        veio_do_cookie = bool(token)
    sessao = validar_token(cfg, token, agora, _revogacoes() if veio_do_cookie else None) if token else None

    if sessao:
        st.session_state.auth_token = token
        st.session_state.auth_sessao = sessao
        gravar_cookie(token, int(sessao.expira_em - agora))
        return sessao

    aviso = None
    if token and not veio_do_cookie:
        aviso = f"⏱️ Sua sessão expirou ({settings.auth_horas_sessao:g} h). Entre de novo."
    for chave in ("auth_token", "auth_sessao"):
        st.session_state.pop(chave, None)
    if token or st.session_state.get("auth_saiu"):
        apagar_cookie()

    _, meio, _ = st.columns([1, 1.2, 1])
    with meio:
        st.markdown("<h1 class='main-header'>Gerador de Missões</h1>", unsafe_allow_html=True)
        if aviso:
            st.info(aviso)
        with st.form("login", border=True):
            usuario = st.text_input("Usuário", placeholder="produto, design, dev ou admin")
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar", type="primary", use_container_width=True)
        if entrar:
            nova, motivo = autenticar(cfg, usuario, senha)
            if nova:
                st.session_state.auth_token = emitir_token(cfg, nova)
                st.session_state.auth_sessao = nova
                st.session_state.auth_saiu = False
                st.rerun()
            st.error(motivo)
        st.caption(f"A sessão vale {settings.auth_horas_sessao:g} h a partir do login.")
    st.stop()


def sair() -> None:
    sessao = sessao_atual()
    if sessao:
        try:
            _revogacoes().revogar(sessao)
        except OSError:
            pass  # sem o arquivo, o token ainda expira sozinho; o cookie é apagado de qualquer forma
    # a missão aberta e a fila também saem: a próxima pessoa no mesmo navegador não herda a tela
    for chave in ("auth_token", "auth_sessao", "current_session_id", "messages", "correcao_pendente",
                  "aviso_fila_mostrado"):
        st.session_state.pop(chave, None)
    st.session_state.auth_saiu = True
    st.rerun()


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


# ------------------------------------------------------------------ parecer humano
SITUACOES_PENDENTES = (passagem.AGUARDANDO, passagem.LIBERADA, passagem.DEVOLVIDA, passagem.FALHOU)


def _abrir_sessao(dir_name: str) -> None:
    loaded = load_saved_session(dir_name)
    if loaded:
        st.session_state.current_session_id = dir_name
        st.session_state.messages = loaded[0]
        st.session_state.correcao_pendente = None


def render_aguardando_voce(sessoes: List[Dict[str, Any]], sessao: Optional[Sessao]) -> None:
    """Fila das missões paradas no papel de quem está logado. É o aviso: não há Slack nem e-mail."""
    if not sessao:
        return
    minhas = [s for s in sessoes if s.get("fluxo_situacao") in SITUACOES_PENDENTES
              and passagem.pode_agir(sessao.papel, s.get("fluxo_etapa") or "")]
    if not minhas:
        return
    if not st.session_state.get("aviso_fila_mostrado"):
        st.toast(f"📥 {len(minhas)} missão(ões) aguardando {sessao.rotulo}.")
        st.session_state.aviso_fila_mostrado = True
    st.markdown(f"#### 📥 Aguardando você ({len(minhas)})")
    for s in minhas:
        o_que = passagem.quem_age({"etapa": s["fluxo_etapa"], "situacao": s["fluxo_situacao"]})
        titulo = s["title"] if len(s["title"]) <= 26 else s["title"][:24] + "…"
        if st.button(f"{titulo} · {o_que}", key=f"fila_{s['dir_name']}", use_container_width=True,
                     help=f"Parado desde {s.get('fluxo_atualizado_em') or '?'}"):
            _abrir_sessao(s["dir_name"])
            st.rerun()
    st.markdown("---")


def _opcoes_runner(opts: Dict[str, Any]) -> Dict[str, Any]:
    return {"thinking_budget": opts["thinking_budget"], "include_thoughts": opts["include_thoughts"],
            "modo_estrito": opts["modo_estrito"]}


@st.cache_data(show_spinner=False, max_entries=8)
def _estado_cached(caminho: str, mtime: float) -> Dict[str, Any]:
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def estado_da_sessao(run_dir: Path) -> Dict[str, Any]:
    """`estado.json` cacheado pelo mtime: ~1 MB, e o cartão de passagem o consulta a cada rerun."""
    caminho = run_dir / "estado.json"
    try:
        return _estado_cached(str(caminho), caminho.stat().st_mtime)
    except (OSError, ValueError):
        return {}


ROTULO_ACAO = {
    passagem.DE_ACORDO: "✅ De acordo — liberar para {prox}",
    passagem.REFAZER: "↩️ Refazer {etapa}",
    passagem.INICIAR: "▶️ Iniciar {etapa}",
    passagem.DEVOLVER: "⤴️ Devolver a {ant}",
    passagem.EXCECAO: "⚠️ Liberar com exceção",
}


def _rotulo_acao(acao: str, etapa: str, fluxo: Dict[str, Any]) -> str:
    if acao == passagem.DE_ACORDO and not passagem.proxima_etapa(etapa):
        return "✅ De acordo — entregar a missão"
    if acao == passagem.INICIAR and fluxo.get("situacao") == passagem.FALHOU:
        return f"🔁 Rodar {passagem.ROTULO_ETAPA[etapa]} de novo"
    ant = passagem.etapa_anterior(etapa)
    prox = passagem.proxima_etapa(etapa)
    return ROTULO_ACAO[acao].format(etapa=passagem.ROTULO_ETAPA[etapa],
                                    prox=passagem.ROTULO_ETAPA.get(prox or "", ""),
                                    ant=passagem.ROTULO_ETAPA.get(ant or "", ""))


def _citar(texto: str) -> str:
    return "\n".join(f"> {l}" if l.strip() else ">" for l in (texto or "").splitlines())


def _render_trilha(fluxo: Dict[str, Any]) -> None:
    pareceres = fluxo.get("pareceres") or []
    liberadas = {p["etapa"] for p in pareceres if p.get("acao") in (passagem.DE_ACORDO, passagem.EXCECAO) and p.get("valido", True)}
    marcas = []
    for etapa in passagem.ORDEM:
        if etapa in liberadas:
            icone = "✅"
        elif etapa == fluxo["etapa"] and fluxo.get("situacao") != passagem.ENTREGUE:
            icone = "🔄"
        else:
            icone = "⬜"
        marcas.append(f"{icone} {passagem.ROTULO_ETAPA[etapa]}")
    st.markdown(" → ".join(marcas))
    if pareceres:
        with st.expander(f"🗒️ Pareceres ({len(pareceres)})", expanded=False):
            nomes = {passagem.DE_ACORDO: "de acordo", passagem.REFAZER: "refazer", passagem.DEVOLVER: "devolveu",
                     passagem.EXCECAO: "liberou com exceção"}
            for p in reversed(pareceres):
                invalido = "" if p.get("valido", True) else " · ~~substituído por uma versão refeita~~"
                st.markdown(f"**{passagem.ROTULO_ETAPA.get(p['etapa'], p['etapa'])}** · {nomes.get(p['acao'], p['acao'])} · "
                            f"{p['como']} · {p['quando']} (rodada {p.get('rodada', 1)}){invalido}\n\n{_citar(p['comentario'])}")


def _tema_escuro() -> bool:
    """O tema ativo do app (inclusive o que vem do sistema), para o que é desenhado com `st.html`."""
    try:
        return st.context.theme.type == "dark"
    except Exception:
        return False


@st.fragment(run_every=5)
def _painel_execucao(run_dir_str: str) -> None:
    """Progresso da etapa em segundo plano. Quando ela termina, recarrega a missão inteira."""
    run_dir = Path(run_dir_str)
    execucao_fundo.conferir_execucao_morta(run_dir)
    dados = execucao_fundo.ler_execucao(run_dir) or {}
    if dados.get("situacao") != "executando" and not execucao_fundo.em_execucao(run_dir):
        invalidar_cache_sessoes()
        _abrir_sessao(run_dir.name)
        st.rerun(scope="app")
    tipo = {"nova": "Gerando", "iniciar": "Gerando", "refazer": "Refazendo", "encerrar": "Fechando o dossiê de"}.get(
        dados.get("tipo", ""), "Rodando")
    etapa = passagem.ROTULO_ETAPA.get(dados.get("etapa", ""), dados.get("etapa", ""))
    decorrido = int(time.time() - float(dados.get("iniciado_em") or time.time()))
    from pipeline.esteira_visual import html_da_esteira

    from tools.custo import texto_ao_vivo

    custo_vivo = dados.get("custo") or {}
    st.html(html_da_esteira(dados.get("etapa", ""), dados.get("agente_atual") or "", dados.get("vistos") or [],
                            titulo=f"⏳ {tipo} {etapa} ·", decorrido_s=decorrido,
                            custo=texto_ao_vivo(custo_vivo.get("execucao"), custo_vivo.get("missao_antes")),
                            escuro=_tema_escuro(), gates=dados.get("gates") or {}))
    gates = dados.get("gates") or {}
    if gates:
        st.caption(" · ".join(f"{_status_icon(v)} {GATE_LABELS.get(k, k)}" for k, v in gates.items() if k in GATE_LABELS))
    st.caption("A execução continua no servidor mesmo se você fechar esta aba. A missão volta para a fila de quem dá o próximo parecer.")


def _render_motivos_do_semaforo(estado: Dict[str, Any], semaforo: Dict[str, str]) -> None:
    """O porquê de cada 🔴 e 🟡, direto no cartão: quem dá o parecer decide sem abrir relatório.

    Antes do parecer humano, isso vinha no dossiê final. Agora o dossiê só roda depois do de acordo do
    Dev, e o cartão mostrava o 🔴 sem dizer o que bloqueou (24/09/2026).
    """
    for chave, icone in semaforo.items():
        if icone not in ("🔴", "🟡"):
            continue
        envelope = estado.get(f"{chave}_envelope")
        achados = [a for a in (envelope.get("achados") if isinstance(envelope, dict) else None) or []
                   if isinstance(a, dict) and a.get("resumo")]
        rotulo = GATE_LABELS.get(chave, chave)
        # 🟡 que pede pessoa abre como o 🔴: decisão humana escondida num expander fechado era o
        # "Nada travando" da tela (06/10/2026).
        pede_pessoa = (isinstance(envelope, dict) and bool(envelope.get("precisa_humano"))) or any(
            str(a.get("severidade")) == "decisao_humana" for a in achados)
        with st.expander(f"{icone} {rotulo} — {len(achados)} achado(s)", expanded=icone == "🔴" or pede_pessoa):
            if not achados:
                st.caption("O gate não detalhou os achados no envelope: veja o relatório dele nos passos da esteira.")
            for a in achados:
                marca = {"bloqueio": "❌", "decisao_humana": "🧑"}.get(str(a.get("severidade")), "⚠️")
                codigo = f"`{a['codigo']}` · " if a.get("codigo") else ""
                st.markdown(f"{marca} {codigo}{a['resumo']}")


def _render_profundidade(estado: Dict[str, Any]) -> None:
    """As notas do juiz de profundidade e o aha em uma frase, antes do parecer de produto.

    O semáforo verde nunca mediu profundidade, e o PO liberava confiando nele (24/09/2026). Aqui ele
    vê, sem abrir relatório, onde a missão é rasa — e o que o juiz entendeu como o aha.
    """
    from tools.profundidade import DIMENSOES, NOME_DIMENSAO

    envelope = estado.get("profundidade_status_envelope")
    if not isinstance(envelope, dict) or not envelope.get("notas"):
        return
    notas = envelope["notas"]
    icone = _status_icon(estado.get("profundidade_status"))
    st.markdown(f"**🎯 Profundidade pedagógica** {icone} — "
                + " · ".join(f"{NOME_DIMENSAO[d]} **{notas.get(d) or '—'}/4**" for d in DIMENSOES))
    if envelope.get("aha_em_uma_frase"):
        st.caption(f"Aha, como o juiz o leu: {envelope['aha_em_uma_frase']}")
    if envelope.get("ponto_mais_fraco"):
        st.caption(f"Ponto mais fraco, segundo o juiz: {envelope['ponto_mais_fraco']}")


def _decidir(run_dir: Path, fluxo: Dict[str, Any], acao: str, comentario: str,
             estado: Dict[str, Any], opts: Dict[str, Any], conferencia: Optional[Dict[str, str]] = None) -> None:
    sessao = sessao_atual()
    try:
        novo, efeito = passagem.aplicar(fluxo, acao, sessao, comentario, estado, conferencia)
        gravado = passagem.registrar_fluxo(run_dir, novo, fluxo.get("versao", 0))
        if efeito:
            execucao_fundo.executar_efeito(run_dir, efeito, passagem.notas_de_passagem(gravado), **_opcoes_runner(opts))
    except (passagem.DecisaoInvalida, passagem.ConflitoDeVersao, execucao_fundo.ExecucaoEmAndamento) as exc:
        st.error(str(exc))
        return
    execucao_fundo.notificar({"tipo": "parecer", "run_dir": str(run_dir), "acao": acao, "etapa": fluxo["etapa"],
                              "autor": sessao.assinatura_de(fluxo["etapa"])})
    invalidar_cache_sessoes()
    st.rerun()


def _painel_decisao(run_dir: Path, fluxo: Dict[str, Any], opts: Dict[str, Any]) -> None:
    sessao = sessao_atual()
    etapa, situacao = fluxo["etapa"], fluxo.get("situacao")
    estado = estado_da_sessao(run_dir)
    if situacao == passagem.ENTREGUE:
        st.success("📦 Missão entregue: as três etapas têm parecer de acordo e o dossiê final foi gerado.")
        if not passagem.acoes_possiveis(fluxo, sessao.papel, estado):
            return
        st.caption("Viu depois da entrega que o design precisa mudar? Devolva ao Design com o que mudar e por quê: "
                   "os de acordo de Design e Dev deixam de valer e a missão volta para a fila do Design.")

    semaforo = passagem.semaforo_da_etapa(estado, etapa)
    if semaforo and situacao in (passagem.AGUARDANDO, passagem.DEVOLVIDA):
        st.markdown("**Semáforo da etapa:** " + " · ".join(f"{icone} {GATE_LABELS.get(k, k)}" for k, icone in semaforo.items()))
        if etapa == "produto":
            _render_profundidade(estado)
        _render_motivos_do_semaforo(estado, semaforo)
    if situacao == passagem.DEVOLVIDA:
        dev = passagem.ultima_devolutiva(fluxo, etapa)
        if dev:
            st.warning(f"⤴️ **Devolvida por {dev['como']}** em {dev['quando']}:\n\n{_citar(dev['comentario'])}")
    if situacao == passagem.LIBERADA:
        anterior = passagem.etapa_anterior(etapa)
        ultimo = next((p for p in reversed(fluxo.get("pareceres") or [])
                       if p.get("etapa") == anterior and p.get("acao") in (passagem.DE_ACORDO, passagem.EXCECAO)), None)
        if ultimo:
            st.success(f"Parecer de **{passagem.ROTULO_ETAPA[anterior]}** ({ultimo['como']}, {ultimo['quando']}):\n\n{_citar(ultimo['comentario'])}")
    if situacao == passagem.FALHOU:
        erro = (execucao_fundo.ler_execucao(run_dir) or {}).get("erro") or "sem detalhe"
        st.error(f"❌ A última execução de {passagem.ROTULO_ETAPA[etapa]} falhou: {erro}")
        if not (run_dir / "estado.json").exists():
            st.caption("A geração não chegou a gravar o estado da missão. Crie a missão de novo pelo ➕ Nova Missão.")
            return

    acoes = passagem.acoes_possiveis(fluxo, sessao.papel, estado)
    if "🔴" in semaforo.values() and situacao in (passagem.AGUARDANDO, passagem.DEVOLVIDA):
        st.warning("🔴 Há gate reprovado nesta etapa: ela não pode ser liberada. Refaça com um comentário do que mudar"
                   + (", ou libere com exceção (fica registrado no dossiê)." if passagem.EXCECAO in acoes
                      else ", ou peça ao admin uma liberação com exceção."))
    if not acoes:
        dono = passagem.dono_da_vez(fluxo)
        st.caption(f"🔒 Aguardando **{passagem.rotulo_donos(dono or '')}**. Você está como {sessao.rotulo}.")
        return

    comentario = ""
    if any(a != passagem.INICIAR for a in acoes):
        chave_comentario = f"parecer_{run_dir.name}_{fluxo.get('versao', 0)}"
        # o rascunho vem da conversa com as etapas, desenhada depois deste cartão: só dá para
        # preencher o campo antes de ele existir, no rerun seguinte ao botão
        rascunho = st.session_state.pop(f"rascunho_parecer_{run_dir.name}", None)
        if rascunho:
            st.session_state[chave_comentario] = rascunho
            st.info("📝 O comentário abaixo é um rascunho tirado da conversa com as etapas. Revise antes de decidir.")
        comentario = st.text_area(
            "Comentário (obrigatório para parecer, refazer ou devolver)",
            key=chave_comentario, height=140,
            placeholder=("De acordo: o que você conferiu e decidiu — segue para os agentes das próximas etapas.\n"
                         if passagem.proxima_etapa(etapa) else
                         "De acordo: o que você conferiu. É a última etapa: o comentário não chega a agente nenhum.\n")
                        + ("Mudança de conteúdo (perguntas, textos, regras): use Refazer, que aplica o pedido.\n"
                           if etapa == "produto" else
                           "Mudança no que o one-pager aprovou (perguntas, textos, regras, habilidades, tempos): "
                           "devolva até Produto — o one-pager só muda lá. Refazer aqui muda o que é desta etapa.\n")
                        + "Refazer ou devolver: o que precisa mudar, e por quê.")
        st.caption(f"Mínimo de {passagem.MIN_CARACTERES_COMENTARIO} letras ou números. Iniciar não pede comentário.")
    # As perguntas de conferência só existem para quem libera a etapa: refazer e devolver não as pedem.
    perguntas = next((passagem.perguntas_de_conferencia(etapa, a) for a in acoes
                      if passagem.perguntas_de_conferencia(etapa, a)), ())
    conferencia: Dict[str, str] = {}
    if perguntas:
        st.markdown("**Para liberar, responda com o que você leu no núcleo (1.1 e 1.2):**")
        for chave, pergunta in perguntas:
            conferencia[chave] = st.text_input(pergunta, key=f"conferencia_{chave}_{run_dir.name}_{fluxo.get('versao', 0)}")
    colunas = st.columns(len(acoes))
    for coluna, acao in zip(colunas, acoes):
        primario = acao in (passagem.DE_ACORDO, passagem.INICIAR)
        if coluna.button(_rotulo_acao(acao, etapa, fluxo), key=f"acao_{acao}_{run_dir.name}_{fluxo.get('versao', 0)}",
                         type="primary" if primario else "secondary", use_container_width=True):
            _decidir(run_dir, fluxo, acao, comentario, estado, opts, conferencia)


def render_passagem(run_dir: Path, opts: Dict[str, Any]) -> bool:
    """Cartão do parecer humano da missão aberta. `True` se a missão segue por pareceres."""
    fluxo = passagem.ler_fluxo(run_dir)
    if not fluxo:
        return False
    # só quando o fluxo diz que a etapa roda: a checagem lê o bucket, e cada rerun de missão parada
    # pagaria uma leitura no gcsfuse à toa
    if fluxo.get("situacao") in passagem.EM_EXECUCAO and execucao_fundo.conferir_execucao_morta(run_dir):
        fluxo = passagem.ler_fluxo(run_dir) or fluxo
    with st.container(border=True):
        st.markdown(f"#### 🧭 Passagem — {passagem.quem_age(fluxo)}")
        _render_trilha(fluxo)
        if fluxo.get("situacao") in passagem.EM_EXECUCAO or execucao_fundo.em_execucao(run_dir):
            _painel_execucao(str(run_dir))
        else:
            # entre as etapas o custo fica à vista: o detalhe da execução, onde ele também aparece, fica fora do cartão
            render_custo_da_missao(estado_da_sessao(run_dir), f"passagem_{run_dir.name}")
            _painel_decisao(run_dir, fluxo, opts)
    return True


def _iniciar_missao_com_parecer(user_prompt: str, doc_batch: Optional[DocumentBatch], opts: Dict[str, Any]) -> None:
    """Missão nova com parecer humano: cria a pasta já, e produto roda em segundo plano.

    A pasta nasce antes da execução (sem o slug no nome, que só existe no fim) para a missão aparecer
    no histórico como "Produto gerando" e o progresso ter onde ser gravado.
    """
    sessao = sessao_atual()
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    run_dir = get_settings().output_path / f"{time.strftime('%Y%m%d-%H%M%S')}-{session_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    display = user_prompt
    if doc_batch and doc_batch.documents:
        display += "\n\n📎 **Anexos:** " + ", ".join(f"`{d.name}`" for d in doc_batch.documents)
    primeira_linha = next((l.strip() for l in user_prompt.splitlines() if l.strip()), "Missão")
    conversa = {
        "session_id": session_id, "user_id": sessao.usuario, "title": primeira_linha[:60],
        "created_at": time.strftime("%d/%m/%Y %H:%M:%S"), "prompt": user_prompt,
        "attached_files": [d.name for d in doc_batch.documents] if doc_batch else [],
        "status": "executando", "messages": [{"role": "user", "content": display}], "gates": {},
        "pipeline_bloqueado": False, "has_prd": False, "files_count": 0, "fluxo": passagem.novo_fluxo(),
    }
    (run_dir / "conversa.json").write_text(json.dumps(conversa, indent=2, ensure_ascii=False), encoding="utf-8")
    execucao_fundo.iniciar_nova(run_dir, user_prompt, sessao.usuario, session_id, doc_batch, **_opcoes_runner(opts))
    st.session_state.current_session_id = run_dir.name
    st.session_state.messages = conversa["messages"]
    invalidar_cache_sessoes()
    st.rerun()


EXEMPLOS_DE_PERGUNTA = ("Por que o gate final ficou 🟡? · O design seguiu a spec na tela de resultado? · "
                        "Que eventos de telemetria o PRD define? · O que a banca reprovou, e por quê?")


def render_conversa_etapas(run_dir: Path, fluxo: Dict[str, Any]) -> Tuple[str, Any]:
    """Um chat só, sobre a missão inteira, sem mudar nada (`pipeline/conversa_etapas.py`).

    Até 12/10/2026 eram três abas, uma por etapa, e a pergunta que cruzava etapas ("o PRD trouxe os eventos do
    handoff?") não tinha onde ser feita. As perguntas antigas, gravadas com a etapa delas, continuam no histórico.
    Devolve a chave da conversa e o espaço onde a pergunta em andamento aparece enquanto o modelo responde.
    """
    mensagens = conversa_etapas.ler(run_dir)
    with st.container(border=True):
        st.markdown("#### 💬 Conversa sobre a missão")
        st.caption("Pergunte sobre produto, design, dev ou a passagem entre eles no campo de mensagem. A conversa "
                   "fica no histórico da missão, à vista de todos, e não altera nenhum documento: para mudar a "
                   "missão, use Refazer no cartão de passagem.")
        if not mensagens:
            st.caption(f"Ninguém perguntou nada ainda. Exemplos: {EXEMPLOS_DE_PERGUNTA}")
        else:
            estado = estado_da_sessao(run_dir)
            assinaturas = {e: conversa_etapas.assinatura(estado, e) for e in (*passagem.ORDEM, conversa_etapas.MISSAO)}
            with st.container(height=520) if len(mensagens) > 6 else st.container():
                for m in mensagens:
                    etapa_m = m.get("etapa") or conversa_etapas.MISSAO
                    with st.chat_message(m.get("role", "user")):
                        if m.get("role") == "user":
                            sobre = "" if etapa_m == conversa_etapas.MISSAO else f" · sobre {conversa_etapas.rotulo(etapa_m)}"
                            st.caption(f"**{ROTULO_PAPEL.get(m.get('como'), m.get('como'))}** · {m.get('quando')}{sobre}")
                        elif conversa_etapas.de_outra_versao(m, assinaturas.get(etapa_m, "")):
                            st.caption("↺ Resposta sobre uma versão anterior da missão: uma etapa foi refeita depois.")
                        st.markdown(sanear_para_streamlit(str(m.get("texto") or "")))
            _botao_rascunho(run_dir, fluxo, conversa_etapas.MISSAO, estado, mensagens)
        em_andamento = st.container()
    return conversa_etapas.MISSAO, em_andamento


def _botao_rascunho(run_dir: Path, fluxo: Dict[str, Any], etapa: str, estado: Dict[str, Any],
                    da_etapa: List[Dict[str, Any]]) -> None:
    """Leva a conversa ao comentário do parecer, para quem tem o parecer em mãos."""
    sessao = sessao_atual()
    if fluxo.get("situacao") in passagem.EM_EXECUCAO:
        return
    if not any(a != passagem.INICIAR for a in passagem.acoes_possiveis(fluxo, sessao.papel, estado)):
        return
    if not st.button("📝 Rascunhar o comentário do parecer com esta conversa", key=f"rascunho_{run_dir.name}_{etapa}"):
        return
    with st.spinner("Escrevendo o rascunho…"):
        try:
            texto = _run_async(conversa_etapas.rascunhar_comentario(etapa, estado, fluxo, da_etapa))
        except Exception as exc:
            st.error(f"Não consegui escrever o rascunho agora: {exc}")
            return
    st.session_state[f"rascunho_parecer_{run_dir.name}"] = texto
    st.rerun()


def _perguntar_a_etapa(run_dir: Path, etapa: str, texto: str, em_andamento: Any) -> None:
    """Responde e grava pergunta e resposta juntas: se o modelo falhar, nada entra no histórico."""
    sessao = sessao_atual()
    fluxo = passagem.ler_fluxo(run_dir)
    estado = estado_da_sessao(run_dir)
    anteriores = conversa_etapas.ler(run_dir)
    pergunta = conversa_etapas.pergunta(etapa, texto, sessao.usuario, sessao.papel)
    with em_andamento:
        with st.chat_message("user"):
            st.caption(f"**{sessao.rotulo}** · agora")
            st.markdown(texto)
        with st.chat_message("assistant"):
            with st.spinner(f"Lendo os documentos de {conversa_etapas.rotulo(etapa)}…"):
                try:
                    saida = _run_async(conversa_etapas.responder(
                        texto, etapa, estado, fluxo, anteriores, execucao_fundo.ler_execucao(run_dir)))
                except Exception as exc:
                    st.error(f"Não consegui responder agora: {exc}. A pergunta não foi gravada; tente de novo.")
                    return
    conversa_etapas.registrar(run_dir, pergunta, conversa_etapas.resposta(etapa, saida, pergunta, estado))
    st.rerun()


def render_sidebar() -> Dict[str, Any]:
    settings = get_settings()
    with st.sidebar:
        if os.path.exists("images/marca.png"):
            st.image("images/marca.png", use_container_width=True)
        elif os.path.exists("images/logo.png"):
            st.image("images/logo.png", use_container_width=True)

        sessao = sessao_atual()
        if sessao:
            col_quem, col_sair = st.columns([3, 1])
            col_quem.markdown(f"👤 Conectado como **{sessao.rotulo}**  \n"
                              f"<span style='opacity:.65;font-size:.8rem'>expira às "
                              f"{time.strftime('%H:%M', time.localtime(sessao.expira_em))}</span>",
                              unsafe_allow_html=True)
            if col_sair.button("Sair", key="auth_sair", use_container_width=True):
                sair()
            if MANUAL_PDF.exists():
                st.download_button("📘 Manual do gerador (PDF)", data=_bytes_do_manual(str(MANUAL_PDF), MANUAL_PDF.stat().st_mtime),
                                   file_name=MANUAL_PDF.name, mime="application/pdf", use_container_width=True,
                                   key="baixar_manual_pdf")

        if st.button("➕ Nova Missão", type="primary", use_container_width=True):
            st.session_state.current_session_id = None
            st.session_state.messages = []
            init_session_state()
            st.rerun()

        parecer_humano = settings.parecer_humano
        if sessao and sessao.papel == "admin":
            parecer_humano = st.toggle(
                "Parecer humano entre etapas", value=settings.parecer_humano, key="parecer_humano",
                help="Ligado: cada etapa para e espera o parecer do dono (de acordo, refazer, devolver). "
                     "Desligado: a esteira roda direto, como antes — para testes.")

        st.markdown("---")
        saved_sessions = listar_sessoes()
        render_aguardando_voce(saved_sessions, sessao)
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
                            # qualquer papel exclui (decisão de 24/09/2026); só não com etapa rodando,
                            # senão a thread em segundo plano seguiria gravando numa pasta apagada
                            if st.button("🗑️", key=f"del_{s['dir_name']}", help=f"Excluir {s['title']}",
                                         disabled=s.get("fluxo_situacao") in passagem.EM_EXECUCAO):
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

    return {"stages": stages, "modo_estrito": modo_estrito, "thinking_budget": thinking_presets[selected_label],
            "include_thoughts": include_thoughts, "parecer_humano": parecer_humano}


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
            "A004NucleoNarrativo",
            "A007MicroGate",
            "A012MicroGateCheck",
            "A014SecoesApoio",
            "A021GateEstrutural",
            "A022GateEstruturalCheck",
            "A023RevisorOnePager",
        ):
            ge_st = str(gates.get("gate_estrutural_status", "")).strip().lower()
            if ge_st in ("aprovado", "success", "concluido", "concluído", "liberada", "apto", "verde", "🟢"):
                if status.get("A023RevisorOnePager") == "pending":
                    status["A023RevisorOnePager"] = "done"
            if status.get("A022GateEstruturalCheck") == "running":
                status["A022GateEstruturalCheck"] = "done"

    elif et == "agent_chunk":
        name = event.get("agent_name", "")
        if "não executado" in (event.get("chunk") or "") and name in status:
            status[name] = "skipped"

    elif et == "gate_status":
        new_status = event.get("status") or {}
        gates.update(new_status)
        ge_st = str(new_status.get("gate_estrutural_status") or gates.get("gate_estrutural_status") or "").strip().lower()
        if ge_st in ("aprovado", "success", "concluido", "concluído", "liberada", "apto", "verde", "🟢"):
            if status.get("A023RevisorOnePager") == "pending":
                status["A023RevisorOnePager"] = "done"
            if status.get("A022GateEstruturalCheck") == "running":
                status["A022GateEstruturalCheck"] = "done"
        if new_status.get("gate_final_status") and status.get("A034GateFinalProdutoCheck") == "running":
            status["A034GateFinalProdutoCheck"] = "done"
        if new_status.get("design_status") and status.get("A080QaEntregaveisCheck") == "running":
            status["A080QaEntregaveisCheck"] = "done"
        if new_status.get("dev_status") and status.get("A101ValidacaoDevCheck") == "running":
            status["A101ValidacaoDevCheck"] = "done"

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
        if status.get("A023RevisorOnePager") == "pending":
            status["A023RevisorOnePager"] = "done"

        # Nenhum agente deve permanecer indefinidamente com ícone de ampulheta (pending) após
        # conclusão. A esteira não pula mais ninguém por causa de gate reprovado: quem ficou
        # pendente aqui é agente condicional que não se aplicava à missão.
        for k in status:
            if status[k] == "pending":
                status[k] = "skipped"

    return active_agent


async def _acompanhar_esteira(stream, stages: List[Dict[str, Any]], progress, steps_container):
    """Consome os eventos de uma execução — nova ou correção — e desenha o progresso.

    Devolve `(result, registro)`: `registro` só existe numa correção (`correcao_completed` /
    `correcao_error`); numa execução nova é `None`.
    """
    status: Dict[str, str] = {m["id"]: "pending" for s in stages for m in s["agents"]}
    gates: Dict[str, Any] = {}
    tool_log: List[str] = []

    def render():
        from pipeline.esteira_visual import etapa_do_agente, html_da_esteira
        from tools.custo import texto_ao_vivo

        with steps_container.container():
            rodou = [k for k, v in status.items() if v in ("done", "running")]
            etapa_atual = etapa_do_agente(active_agent or "")
            st.html(html_da_esteira(etapa_atual, active_agent or "", rodou, titulo="🔄",
                                    custo=texto_ao_vivo(custo_vivo.get("custo"), custo_vivo.get("missao_antes")),
                                    escuro=_tema_escuro(), gates=gates))
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

    active_agent: Optional[str] = None
    custo_vivo: Dict[str, Any] = {}
    render()
    result: Optional[PipelineExecutionResult] = None
    registro: Optional[Dict[str, Any]] = None

    async for event in stream:
        et = event.get("type")
        if et == "correcao_started":
            progress.info(
                f"🔧 Correção a partir de **{event['etapa']}** — etapas: {', '.join(event['stages'])}. "
                f"Cópia do estado anterior em `{event['backup']}`."
            )
            continue
        if et == "correcao_completed":
            registro = event.get("registro")
            result = event.get("result") or result
            continue
        if et == "correcao_error":
            registro = event.get("registro")
            progress.error(f"❌ Correção não aplicada: {event.get('error')}. A sessão voltou ao estado anterior.")
            continue
        active_agent = update_pipeline_step_status(status, active_agent, event, gates)

        if et == "custo_parcial":
            custo_vivo = event
            continue
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
    return result, registro


async def execute_pipeline(prompt: str, opts: Dict[str, Any], progress, steps_container, doc_batch: Optional[DocumentBatch]):
    """Missão nova, do zero."""
    sessao = sessao_atual()
    stream = run_orchestrator_pipeline_stream(
        prompt=prompt,
        user_id=sessao.usuario if sessao else None,
        thinking_budget=opts["thinking_budget"],
        include_thoughts=opts["include_thoughts"],
        modo_estrito=opts["modo_estrito"],
        stages=opts["stages"],
        doc_batch=doc_batch,
    )
    result, _ = await _acompanhar_esteira(stream, stages_para_ui(opts["stages"]), progress, steps_container)
    return result


async def execute_correcao(run_dir: Path, etapa: str, pedido: PedidoCorrecao, triagem: Optional[Triagem], opts: Dict[str, Any], progress, steps_container):
    """Correção de uma sessão aberta: só as etapas a partir de `etapa`, na mesma pasta."""
    stream = executar_correcao_stream(
        run_dir, etapa, pedido, triagem,
        thinking_budget=opts["thinking_budget"],
        include_thoughts=opts["include_thoughts"],
        modo_estrito=opts["modo_estrito"],
    )
    return await _acompanhar_esteira(stream, stages_para_ui(ETAPA_PARA_STAGES[etapa]), progress, steps_container)


def _run_async(coro):
    """Roda uma corrotina num loop próprio (o Streamlit não tem loop ativo no script)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


ETAPAS_DE_CORRECAO = ["produto", "spec", "design", "dev"]
LEGENDAS_ETAPA = {"produto": "Missão inteira, desde o núcleo (~30 min)", "spec": "Spec + design + dev (~20 min)",
                  "design": "Design + dev (~15 min)", "dev": "Só dev (~7 min)"}


def _iniciar_correcao(user_prompt: str, doc_batch: Optional[DocumentBatch]) -> None:
    """Mensagem enviada com uma sessão aberta: registra o pedido, roda a triagem e abre o card de confirmação."""
    run_dir = get_settings().output_path / str(st.session_state.current_session_id)
    display = user_prompt
    if doc_batch and doc_batch.documents:
        display += "\n\n📎 **Anexos:** " + ", ".join(f"`{d.name}`" for d in doc_batch.documents)
    st.session_state.messages.append({"role": "user", "content": display})
    pedido = PedidoCorrecao.de_doc_batch(user_prompt, doc_batch)
    try:
        estado, _, _ = carregar_sessao(run_dir)
    except Exception:
        estado = {}
    with st.spinner("🧭 Triando o pedido…"):
        triagem = _run_async(triar_pedido(pedido, doc_batch, estado))
    st.session_state.correcao_pendente = {"pedido": pedido, "triagem": triagem, "run_dir": str(run_dir)}
    st.rerun()


def _render_card_correcao(pendente: Dict[str, Any], opts: Dict[str, Any]) -> None:
    """Decisão da triagem, escolha final da etapa e botões Aplicar / Cancelar."""
    triagem: Triagem = pendente["triagem"]
    pedido: PedidoCorrecao = pendente["pedido"]
    run_dir = Path(pendente["run_dir"])
    with st.chat_message("assistant"):
        if triagem.etapa in ETAPAS_DE_CORRECAO:
            st.markdown(f"🧭 **Triagem:** recomeçar de **{triagem.etapa}** — {triagem.motivo}")
            indice: Optional[int] = ETAPAS_DE_CORRECAO.index(triagem.etapa)
        elif triagem.etapa == "nenhuma":
            st.markdown(f"🧭 **Triagem:** o pedido não altera a missão — {triagem.motivo}\n\nSe ainda assim quiser refazer uma etapa, escolha abaixo.")
            indice = None
        else:
            st.warning(f"🧭 A triagem não conseguiu decidir ({triagem.motivo or 'sem resposta'}). Escolha a etapa manualmente.")
            indice = None
        if triagem.resumo_pedido:
            st.caption(f"**O que muda:** {triagem.resumo_pedido}")
        if pedido.anexos_sem_texto:
            st.caption("📎 Sem texto extraível: " + ", ".join(f"`{n}`" for n in pedido.anexos_sem_texto)
                       + ". A triagem os leu como arquivo; para os agentes verem o texto integral, anexe .docx, .md ou .txt.")
        escolha = st.radio(
            "Recomeçar de", ETAPAS_DE_CORRECAO, index=indice, horizontal=True,
            captions=[LEGENDAS_ETAPA[e] for e in ETAPAS_DE_CORRECAO], key="correcao_etapa",
        )
        st.caption("As etapas anteriores à escolhida não são reavaliadas: ficam como estão e servem de insumo.")
        col_ok, col_nao = st.columns([1, 1])
        aplicar = col_ok.button("▶️ Aplicar correção", type="primary", disabled=escolha is None, key="correcao_aplicar", use_container_width=True)
        cancelar = col_nao.button("✖️ Cancelar", key="correcao_cancelar", use_container_width=True)
    if cancelar:
        if st.session_state.messages and st.session_state.messages[-1].get("role") == "user":
            st.session_state.messages.pop()
        st.session_state.correcao_pendente = None
        st.rerun()
    if aplicar and escolha:
        st.session_state.correcao_pendente = None
        _aplicar_correcao(run_dir, escolha, pedido, triagem, opts)


def _aplicar_correcao(run_dir: Path, etapa: str, pedido: PedidoCorrecao, triagem: Triagem, opts: Dict[str, Any]) -> None:
    with st.chat_message("assistant"):
        progress = st.empty()
        steps = st.empty()
        progress.info(f"🔧 Iniciando a correção a partir de **{etapa}**…")
        result, registro = _run_async(execute_correcao(run_dir, etapa, pedido, triagem, opts, progress, steps))
        resumo = mensagem_de_correcao(RegistroCorrecao(**registro)) if registro else "❌ Correção não aplicada."
        if result:
            st.markdown(resumo)
            render_pipeline_details(result, key_prefix="live")
            st.session_state.messages.append({"role": "assistant", "content": resumo, "pipeline_result": result})
        else:
            st.error(resumo)
            st.session_state.messages.append({"role": "assistant", "content": resumo})
        invalidar_cache_sessoes()


def _historico_da_sessao(result: PipelineExecutionResult) -> List[Dict[str, Any]]:
    """Correções já aplicadas nesta sessão, lidas do `conversa.json` da pasta (arquivo pequeno)."""
    pasta = getattr(result, "output_dir", None)
    if not pasta:
        return []
    try:
        return historico_de(json.loads((Path(pasta) / "conversa.json").read_text(encoding="utf-8")))
    except Exception:
        return []


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


def render_custo_da_missao(estado: Dict[str, Any], prefix: str) -> None:
    """Tokens e custo da missão inteira — todas as execuções, refazer incluído (`tools/custo.py`)."""
    from tools.custo import KEY_CUSTO, brl, milhares

    custo = estado.get(KEY_CUSTO) or {}
    total = custo.get("total") or {}
    if not total:
        st.caption("💰 Custo: esta missão foi gerada antes da contagem de custo.")
        return
    t = total.get("tokens") or {}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Custo total da missão", brl(float(total.get("brl") or 0)), help=f"US$ {float(total.get('usd') or 0):.4f}")
    c2.metric("Tokens de entrada", milhares(int(t.get("entrada") or 0)),
              help=f"{milhares(int(t.get('cache') or 0))} vieram do cache, a 10% do preço")
    c3.metric("Tokens de saída", milhares(int(t.get("saida") or 0) + int(t.get("pensamento") or 0)),
              help=f"{milhares(int(t.get('pensamento') or 0))} de pensamento (cobrados como saída)")
    c4.metric("Execuções", len(custo.get("execucoes") or []), help=f"{milhares(int(t.get('chamadas') or 0))} chamadas ao modelo")
    with st.expander("💰 Custo por execução", expanded=False):
        linhas = ["| Quando | Etapas | Entrada | Saída | Pensamento | US$ | Cotação | R$ |",
                  "|---|---|--:|--:|--:|--:|--:|--:|"]
        for e in custo.get("execucoes") or []:
            tk = e.get("tokens") or {}
            etapas_e = ", ".join(e.get("etapas") or []) + (" · ⚠️ falhou" if e.get("falhou") else "")
            linhas.append(f"| {e.get('quando', '?')} | {etapas_e} | {milhares(int(tk.get('entrada') or 0))} "
                          f"| {milhares(int(tk.get('saida') or 0))} | {milhares(int(tk.get('pensamento') or 0))} "
                          f"| {float(e.get('usd') or 0):.4f} | {float(e.get('cotacao') or 0):.4f} "
                          f"({e.get('fonte_cotacao', '?')}) | {brl(float(e.get('brl') or 0))} |")
        st.markdown("\n".join(linhas))
        sem_preco = sorted({m for e in custo.get("execucoes") or [] for m in e.get("modelos_sem_preco") or []})
        if sem_preco:
            st.warning(f"Modelo sem preço na tabela: {', '.join(sem_preco)}. O consumo dele não entrou no custo.")
        st.caption("Preço Standard da API do Gemini por 1 milhão de tokens. O real usa a cotação do momento de cada "
                   "execução: PTAX de venda do Banco Central, ou `COTACAO_USD_BRL` quando definida no ambiente. "
                   "A conversa sobre a missão e a triagem de correção não entram.")


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
    render_custo_da_missao(result.state or {}, prefix)
    if getattr(result, "bypassed", False):
        st.warning("⚠️ **Atenção:** Esta missão avançou com gates bloqueados (modo estrito desativado / bypass). Verifique as pendências nos relatórios e na seção 20 do PRD.")
    historico = _historico_da_sessao(result)
    if historico:
        with st.expander(f"🔧 Histórico de correções ({len(historico)})", expanded=False):
            for h in historico:
                linha = f"- **{h.get('quando', '?')}** · recomeçou de `{h.get('etapa', '?')}` · {h.get('status', '?')}"
                if h.get("etapa_sugerida") and h["etapa_sugerida"] != h.get("etapa"):
                    linha += f" (triagem sugeriu `{h['etapa_sugerida']}`)"
                linha += f" — {h['pedido']}" if h.get("pedido") else " — reexecução sem pedido"
                if h.get("backup"):
                    linha += f" · cópia anterior em `{h['backup']}`"
                if h.get("desfeita_em"):
                    linha += f" · desfeita em {h['desfeita_em']}"
                st.markdown(linha)
            pasta = Path(getattr(result, "output_dir", "") or "")
            com_fluxo = pasta.is_dir() and passagem.ler_fluxo(pasta) is not None
            if com_fluxo:
                # restaurar o conversa.json de antes voltaria os pareceres no tempo, sem ninguém decidir
                st.caption("Com parecer humano, o desfazer fica desligado: o caminho é **Refazer** no cartão de passagem.")
            elif correcao_desfazivel({"historico_correcoes": historico}) and pasta.is_dir():
                st.caption("Desfazer restaura os documentos, o estado e a conversa de antes da última correção. A cópia fica guardada.")
                if st.button("↩️ Desfazer a última correção", key=f"desfazer_{prefix}"):
                    registro = desfazer_correcao(pasta)
                    invalidar_cache_sessoes()
                    if registro:
                        recarregada = load_saved_session(pasta.name)
                        if recarregada:
                            st.session_state.messages = recarregada[0]
                            st.session_state.current_session_id = pasta.name
                        st.session_state.correcao_pendente = None
                        st.rerun()
                    else:
                        st.warning("Não havia correção para desfazer.")
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
            if key == "prototipo_html":
                # a saída do A069 vem como ```html … ``` + envelope JSON; o iframe abriria em modo
                # quirks com as crases e o JSON escritos na página. O arquivo limpo está no estado.
                value = result.state.get("prototipo_arquivo") or value
            with st.expander(f"{meta['icon']} {meta['name']}", expanded=False):
                if meta.get("id") == "A023RevisorOnePager" and "A023RevisorOnePager" not in (result.step_outputs or {}):
                    st.caption("ℹ️ *One-pager aprovado no gate estrutural sem necessidade de revisão. Exibindo a versão aprovada:*")
                render_saida_agente(value, output_key=key, prefix=f"{prefix}_{key}")
        if not shown:
            st.caption("Nenhuma saída registrada para esta etapa.")

    if aba == ABAS[0]:
        if prd_text:
            # o PRD do estado pode vir dentro de ```markdown (só o PRD.md em disco sai desembrulhado):
            # sem tirar o invólucro antes, o front matter não é reconhecido e os metadados somem
            meta, body = extrair_metadados_frontmatter(desembrulhar_documento(prd_text))
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
                        file_name=nome_do_zip_de_artefatos(result.state, sid),
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
                file_name=f"estado_{identificador_da_missao(result.state, sid)}.json",
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
    missao = identificador_da_missao(result.state, sid)
    pasta = Path(result.output_dir) if result.output_dir else None

    def _one_pager(chave: str, base: str):
        """O `.docx` com a marca quando a exportação existe; senão o Markdown do estado; `None` se não foi gerado."""
        from pipeline.artifacts import e_mensagem_de_pulo

        docx = pasta / f"{base}.docx" if pasta else None
        if docx and docx.exists():
            return (lambda d=docx: d.read_bytes()), f"{Path(base).name}_{missao}.docx", \
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        texto = str(result.state.get(chave) or "")
        if not texto.strip() or e_mensagem_de_pulo(texto):
            return None
        return (lambda t=texto: t), f"{Path(base).name}_{missao}.md", "text/markdown"

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if pasta and pasta.exists():
            download_button_lazy(
                "📦 Download total",
                lambda p=pasta: create_session_zip(p),
                file_name=nome_do_zip_de_artefatos(result.state, sid),
                mime="application/zip",
                key=f"zip_total_{prefix}",
                help="Todos os artefatos da missão num .zip.",
            )
        else:
            st.button("📦 Download total", disabled=True, use_container_width=True, key=f"zip_total_{prefix}",
                      help="A pasta da missão ainda não foi gravada.")
    # quem gera cada um: sem ele, o botão fica desabilitado em vez de baixar um arquivo vazio
    for col, (rotulo, chave, base, quem) in zip((c2, c3, c4), (
            ("📄 One-pager de produto", "one_pager", "produto/00-one-pager", "a etapa de Produto"),
            ("📄 One-pager resumido", "one_pager_resumido", "produto/00d-one-pager-resumido", "o fim de Produto"),
            ("📄 One-pager pedagógico", "one_pager_pedagogico", "one-pager-pedagogico", "o fim de Dev"))):
        with col:
            pronto = _one_pager(chave, base)
            if pronto:
                dados, nome, mime = pronto
                download_button_lazy(rotulo, dados, file_name=nome, mime=mime, key=f"{chave}_{prefix}")
            else:
                st.button(rotulo, disabled=True, use_container_width=True, key=f"{chave}_{prefix}",
                          help=f"Ainda não gerado: sai em {quem}.")
    if result.output_dir:
        st.caption(f"Artefatos gravados em `{result.output_dir}`")


def zip_dos_prompts() -> bytes:
    """Todos os prompts num .zip: `fonte/` como estão em `prompts/` (com as diretivas de include) e `final/` com os
    includes resolvidos, como o agente os recebe. Referência que vem da base da plataforma e não pôde ser lida fica de
    fora do `final/`, com a razão em `final/_LEIA-ME.txt`."""
    import io
    import zipfile

    from prompts import PROMPTS_DIR

    s = get_settings()
    falhas: List[str] = []
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for caminho in sorted(PROMPTS_DIR.rglob("*.md")):
            rel = caminho.relative_to(PROMPTS_DIR).as_posix()
            zf.writestr(f"fonte/{rel}", caminho.read_text(encoding="utf-8"))
        for area, arquivos in list_prompt_files().items():
            for nome in arquivos:
                rel = f"{area}/{nome}"
                try:
                    zf.writestr(f"final/{rel}", load_prompt(
                        rel, stitch_mcp_mode=s.stitch_mcp_mode, stitch_project_url_base=s.stitch_project_url_base,
                        gate_max_rodadas=s.gate_estrutural_max_rodadas, qa_max_rodadas=s.qa_design_max_rodadas))
                except Exception as exc:  # base da plataforma fora do ar: a fonte continua no zip
                    falhas.append(f"{rel}: {exc}")
        if falhas:
            zf.writestr("final/_LEIA-ME.txt", "Prompts sem a versão final (includes não resolvidos):\n" + "\n".join(falhas))
    return buffer.getvalue()


#: O manual na 3ª edição (outubro de 2026), que vai na imagem com o resto do repositório.
MANUAL_PDF = Path(__file__).resolve().parent / "manual-unooria" / "manual-gerador-missoes.pdf"


@st.cache_data(show_spinner=False)
def _bytes_do_manual(caminho: str, mtime: float) -> bytes:
    """Lido uma vez por versão do arquivo: o botão é desenhado a cada rerun da barra lateral."""
    return Path(caminho).read_bytes()


def render_prompt_manager():
    st.markdown("### 📝 Prompts dos agentes")
    st.info("🔒 Somente leitura: os prompts vão dentro da imagem publicada, e mudar um prompt é mudar o código — por "
            "pull request no repositório.")
    if st.button("📦 Preparar .zip com todos os prompts", key="preparar_zip_prompts"):
        with st.spinner("Juntando os prompts e resolvendo os includes…"):
            st.session_state["zip_prompts"] = zip_dos_prompts()
    if st.session_state.get("zip_prompts"):
        st.download_button("⬇️ Baixar prompts.zip", data=st.session_state["zip_prompts"], file_name="prompts-gerador-missoes.zip",
                           mime="application/zip", key="baixar_zip_prompts")
    st.markdown("Cada agente lê um arquivo Markdown em `prompts/<área>/`. Diretivas `<!-- include: references/… -->` inserem conhecimento compartilhado em tempo de carga; `{chave}` / `{chave?}` são interpoladas pelo ADK a partir do estado da sessão.")
    areas = list_prompt_files()

    # Um mesmo prompt pode ser lido por mais de um nó: o revisor do one-pager (023) roda de novo movido pelo
    # parecer (029), e as bancas A–C rodam no fim de produto, no fim de design e na entrada do dev. Vale a
    # PRIMEIRA ocorrência, que é a posição canônica na esteira; as outras aparecem como reúso.
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

    # os juízes genéricos e os dois agentes fora da esteira não estão nos metadados: quem os usa vem da árvore
    from pipeline.orchestrator import ROTULO_PROMPT_COMPARTILHADO, passos_dos_prompts_compartilhados

    for rel, agentes in passos_dos_prompts_compartilhados().items():
        if rel in metadata or not agentes:
            continue
        rotulo = ROTULO_PROMPT_COMPARTILHADO.get(rel, rel)
        numero = re.match(r"A(\d{3}[a-z]?)", agentes[0])
        if numero and not re.match(r"\d", rotulo):
            rotulo = f"{numero.group(1)} · {rotulo}"
        metadata[rel] = {"id": agentes[0], "name": rotulo, "output_key": "—",
                         "description": "Prompt compartilhado: cada agente abaixo o usa com os seus próprios documentos."}
        if len(agentes) > 1:
            reusos[rel] = agentes[1:]

    def _ordem_do_agente(rel: str) -> tuple[int, str]:
        """`023 · Revisor` → (23, ''), `024b · Experiência` → (24, 'b'). Ordena pela esteira, não pelo nome do arquivo."""
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
    tab_edit, tab_final = st.tabs(["📄 Fonte", "👁️ Prompt final (includes resolvidos)"])
    with tab_edit:
        st.code(raw, language="markdown")
    with tab_final:
        s = get_settings()
        try:
            final = load_prompt(rel, stitch_mcp_mode=s.stitch_mcp_mode, stitch_project_url_base=s.stitch_project_url_base, gate_max_rodadas=s.gate_estrutural_max_rodadas, qa_max_rodadas=s.qa_design_max_rodadas)
            st.caption(f"{len(final):,} caracteres após includes")
            st.code(final, language="markdown")
        except Exception as exc:
            st.error(f"Erro ao resolver includes: {exc}")

    st.markdown("---")
    st.markdown("#### 📚 Referências compartilhadas (`prompts/references/`)")
    from prompts import REFERENCES_DIR, base_plataforma

    # Os arquivos próprios vêm primeiro; as cópias da plataforma, agrupadas no fim. Ordenar tudo
    # junto pelo caminho enterrava as referências editáveis no meio de 45 cópias sincronizadas.
    todas = sorted(p.relative_to(REFERENCES_DIR).as_posix() for p in REFERENCES_DIR.rglob("*.md"))
    refs = [r for r in todas if "/" not in r] + [r for r in todas if "/" in r]
    try:
        base = base_plataforma.ativa()
        st.caption(base.resumo())
        refs += ["ds-componentes.md", "plataforma/contrato-plataforma.md"]
        refs += [f"plataforma/{n}" for n in base_plataforma.listar_copias(base)]
    except base_plataforma.BaseIndisponivel as exc:
        st.warning(f"Base da plataforma indisponível: {exc}")

    def _rotulo_ref(r: str) -> str:
        pasta, _, nome = r.rpartition("/")
        return f"📁 {pasta} · {nome}" if pasta else f"📄 {r}"

    ref = st.selectbox("Referência", refs, format_func=_rotulo_ref)
    ref_raw = get_prompt_raw(f"references/{ref}")
    sincronizada = base_plataforma.eh_da_base(f"references/{ref}")
    if sincronizada:
        st.warning(
            "🔒 Vem da base publicada pela plataforma e pelo storybook (bucket). Não se edita aqui: "
            "mude na origem; o CI publica de novo a cada push em `dev-local` ou versão do DS."
        )
    st.code(ref_raw, language="markdown")


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
            """Missão para o 5º ano do Fundamental, 3º bimestre, no ambiente do YouTube (unootube).

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
    # O retorno do OAuth do Miro vem antes do login: é uma aba nova e, sem isso, o `?code=` se
    # perderia na tela de login. Ele não mostra dados — valida o `state` e guarda o token.
    tratar_retorno_oauth_miro()
    exigir_login()
    init_session_state()
    opts = render_sidebar()

    st.markdown("<h1 class='main-header'>Gerador de Missões</h1>", unsafe_allow_html=True)
    st.markdown("**Produto → Design → Dev** · pipeline multiagente no Google ADK que transforma um one-pager em um **PRD padrão ouro** pronto para codificação.")
    st.markdown("---")

    # Mesmo motivo das seções de `render_pipeline_details`: com `st.tabs`, o editor de
    # prompts era montado a cada rerun mesmo fechado — e ele resolve includes, chegando a
    # ~380 KB de payload por interação.
    # Os prompts voltam à tela só para leitura (08/10/2026): eles vão dentro da imagem, e uma edição aqui valeria só
    # até o próximo deploy. O .zip baixa todos de uma vez.
    SECOES = ["💬 Pipeline", "📝 Prompts e referências"]
    secao = st.segmented_control("Seção", SECOES, default=SECOES[0], key="secao_principal", label_visibility="collapsed") or SECOES[0]

    if secao == SECOES[0]:
        for idx, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                st.markdown(sanear_para_streamlit(msg["content"]))
                if msg.get("pipeline_result"):
                    render_pipeline_details(msg["pipeline_result"], key_prefix=f"msg_{idx}")

        render_guia_de_uso()

        # Com uma sessão aberta, o campo de mensagem pede correções NELA: a esteira recomeça só
        # da etapa afetada, sobre o estado salvo. Com parecer humano, ele pergunta à etapa escolhida
        # na conversa, sem mudar nada. Missão do zero é pelo botão "➕ Nova Missão".
        modo_correcao = bool(st.session_state.get("current_session_id"))
        run_dir_aberto = get_settings().output_path / str(st.session_state.current_session_id) if modo_correcao else None
        com_fluxo = modo_correcao and render_passagem(run_dir_aberto, opts)
        etapa_da_conversa, em_andamento = (
            render_conversa_etapas(run_dir_aberto, passagem.ler_fluxo(run_dir_aberto) or passagem.novo_fluxo())
            if com_fluxo else (None, None))
        if modo_correcao and not com_fluxo and st.session_state.get("correcao_pendente"):
            _render_card_correcao(st.session_state.correcao_pendente, opts)

        doc_batch: Optional[DocumentBatch] = None
        rotulo_anexos = (
            "📎 Anexar material para a correção (PDF, Word, Markdown ou texto — até 60 arquivos / 25 MB)"
            if modo_correcao else
            "📎 Anexar one-pager / documentos de apoio (PDF, Word, Markdown ou texto — até 60 arquivos / 25 MB)"
        )
        # com fluxo, o material de uma refação vai no comentário do Refazer; anexo aqui não teria destino
        if not com_fluxo:
            with st.expander(rotulo_anexos, expanded=False):
                uploaded = st.file_uploader("Arquivos para os agentes:" if modo_correcao else "Arquivos para o agente P0 (one-pager):", type=list(EXTENSOES_ACEITAS), accept_multiple_files=True, key="docs")
                if uploaded:
                    batch, err = validate_and_process_batch(uploaded)
                    if err:
                        st.error(err)
                    elif batch:
                        doc_batch = batch
                        st.success(f"✅ {batch.files_count} arquivo(s) — {batch.total_mb:.2f} MB")

        sessao = sessao_atual()
        # missão nova começa pela etapa de produto: só quem responde por ela a cria
        sem_permissao_de_criar = not modo_correcao and not (sessao and passagem.pode_criar_missao(sessao.papel))
        placeholder = (
            "Pergunte qualquer coisa sobre esta missão: a resposta fica no histórico e não muda nada. "
            "Para mudar, use Refazer no cartão de passagem."
            if com_fluxo else
            f"Missão nova é criada por {passagem.rotulo_donos('produto')} (ou admin). Abra uma missão no histórico."
            if sem_permissao_de_criar else
            "Peça uma correção nesta missão (ex.: subir o teto de bio para 150; trocar a copy da tela 3; fixar o polling em 4 s)…"
            if modo_correcao else
            "Descreva a missão (ano, ambiente, descoberta central, decisão do estudante) ou envie o one-pager…"
        )
        # Com parecer humano, a correção livre pelo chat ficaria fora do fluxo (sem dono, sem
        # parecer, rodando as etapas seguintes sem ninguém ter liberado): o campo vira pergunta à
        # etapa escolhida na conversa, que não altera nada, e mudar continua sendo o Refazer do cartão.
        user_prompt = st.chat_input(placeholder, disabled=sem_permissao_de_criar,
                                    max_chars=conversa_etapas.TETO_PERGUNTA if com_fluxo else None)
        if user_prompt and com_fluxo:
            _perguntar_a_etapa(run_dir_aberto, etapa_da_conversa, user_prompt, em_andamento)
        elif user_prompt and modo_correcao:
            settings = get_settings()
            if not settings.is_gemini_configured():
                st.warning("⚠️ `GOOGLE_API_KEY` não configurada no `.env`.")
            _iniciar_correcao(user_prompt, doc_batch)
        elif user_prompt and opts.get("parecer_humano"):
            _iniciar_missao_com_parecer(user_prompt, doc_batch, opts)
        elif user_prompt:
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
                    st.markdown(sanear_para_streamlit(summary if len(summary) < 4000 else summary[:4000] + "\n\n…"))
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
