"""Armazenamento e gerenciamento persistente de sessões e histórico de conversas."""

from __future__ import annotations

import io
import json
import logging
import os
import re
import shutil
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import get_settings
from pipeline.artifacts import extrair_slug

logger = logging.getLogger("session_store")


def _safe_str(val: Any) -> str:
    return str(val) if val is not None else ""


def extrair_metadados_frontmatter(texto: str) -> Tuple[Dict[str, str], str]:
    """Separa o frontmatter YAML (se houver) do restante do documento Markdown.
    
    Retorna (metadados_dict, corpo_sem_frontmatter).
    """
    if not texto or not isinstance(texto, str):
        return {}, _safe_str(texto)

    m = re.match(r"^\s*---\s*\n(.*?)\n---\s*\n?(.*)$", texto, re.DOTALL)
    if not m:
        return {}, texto

    raw_frontmatter, body = m.groups()
    meta: Dict[str, str] = {}
    for line in raw_frontmatter.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(":", 1)
        if len(parts) == 2:
            k = parts[0].strip()
            v = parts[1].strip().strip("\"'")
            meta[k] = v

    return meta, body.strip()


def formatar_status_label(status: str) -> str:
    """Retorna um label formatado com emoji amigável para o status da missão."""
    s = (status or "").strip().lower()
    if s in ("aprovado", "success", "concluido", "concluído", "liberada", "apto", "verde", "🟢"):
        return "🟢 Aprovado"
    if s in ("em-revisao", "em_revisao", "em revisão", "revisao", "revisão"):
        return "🟡 Em revisão"
    if s in ("bypassed", "bypass", "amarelo", "🟡", "ressalvas", "ressalva", "alerta", "warning", "apto_com_ressalvas", "aprovado_com_ressalvas"):
        return "🟡 Aprovado com ressalvas"
    if s in ("bloqueado", "bloqueada", "blocked", "reprovado", "vermelho", "🔴", "nao_apto"):
        return "🔴 Bloqueado"
    if s in ("draft", "rascunho"):
        return "⚪ Rascunho"
    if s in ("em-implementacao", "em_implementacao", "em implementação"):
        return "🔵 Em implementação"
    if s in ("lancado", "lançado"):
        return "🟣 Lançado"
    return f"⚪ {status.capitalize()}" if status else "⚪ Indefinido"


def rotulo_serie_bimestre(state: Dict[str, Any]) -> str:
    """`2EF-1B` a partir do identificador da missão, ou vazio quando não dá para deduzir.

    O histórico ordenava por data, e duas missões do mesmo ano ficavam indistinguíveis na lista.
    Com ano e bimestre na frente, a lista se organiza sozinha pelo que o time procura.
    """
    from tools.rastro import decompor_id

    texto = " ".join(
        str(state.get(k) or "")[:4000]
        for k in ("spec_missao", "prd_final", "one_pager")
    )
    m = re.search(r"\bexp0[1-9](?:ef|em)[1-4]b\b", texto, re.IGNORECASE)
    if m:
        partes = decompor_id(m.group(0).lower())
        if partes:
            return f"{partes['serie']}-{partes['unidade']}B"

    # Legado e transversal: tenta série e unidade declaradas soltas no bloco 0.
    serie = re.search(r"\b([1-9])\s*(EF|EM)\b", texto, re.IGNORECASE)
    unidade = re.search(r"unidade:\s*`?([1-4])", texto, re.IGNORECASE)
    if serie and unidade:
        return f"{serie.group(1)}{serie.group(2).upper()}-{unidade.group(1)}B"
    return ""


def extrair_titulo_missao(state: Dict[str, Any], fallback: str = "Missão Sem Título") -> str:
    """Título amigável da missão, prefixado por ano e bimestre quando dedutíveis.

    Ex.: `2EF-1B · O Detalhe que Muda Tudo`. O prefixo vem do identificador da missão, que
    carrega ano e bimestre desde a revisão do esquema de código.
    """
    titulo = _titulo_bruto(state, fallback)
    prefixo = rotulo_serie_bimestre(state)
    if prefixo and not titulo.upper().startswith(prefixo):
        return f"{prefixo} · {titulo}"
    return titulo


#: Onde a prosa começa depois do nome. O gabarito do bloco 0 (`references/formato-spec.md:17`)
#: pede "Nome que o estudante vê · software clonado · por que este viewport", e o agente entrega
#: tudo isso numa linha só. O nome é o que vem antes do primeiro separador ou do primeiro ponto
#: final de frase.
_CORTE_PROSA = re.compile(
    r"\s+[·—–|]\s+"                        # separadores do gabarito
    r"|(?<=[a-zà-ÿ0-9\)\"'])\.(?:\s+|$)"     # fim de frase: ponto após letra/dígito
)
_LIMITE_TITULO = 70


def _encurtar_titulo(bruto: str) -> str:
    """Reduz o título ao nome da missão, sem o resumo que costuma vir grudado.

    `O algoritmo que me formou. Software clonado: Instagram (`instanooria`). Viewport: 375x812…`
    vira `O algoritmo que me formou`. O corte é no primeiro separador do gabarito ou no primeiro
    fim de frase — `375x812` e `v1.0` não são fim de frase porque o ponto não é seguido de espaço.
    """
    texto = " ".join((bruto or "").split()).strip().strip("*_`\"'")
    if not texto:
        return ""
    m = _CORTE_PROSA.search(texto)
    if m:
        texto = texto[: m.start()].strip()
    texto = texto.strip().strip("*_`\"'").rstrip(".,;:·—–|").strip()
    if len(texto) > _LIMITE_TITULO:
        corte = texto.rfind(" ", 0, _LIMITE_TITULO)
        texto = texto[: corte if corte > 0 else _LIMITE_TITULO].rstrip(" ,;:.") + "…"
    return texto


def _titulo_bruto(state: Dict[str, Any], fallback: str = "Missão Sem Título") -> str:
    """Extrai o título amigável da missão a partir do prd_final, spec_missao, one_pager ou fallback."""
    fontes = [
        state.get("prd_final"),
        state.get("spec_missao"),
        state.get("one_pager"),
    ]
    # O núcleo narrativo e o one-pager trazem o nome como item de lista
    # (`* **Nome que o estudante vê:** O algoritmo que me formou`); a spec o entrega em prosa,
    # junto do software clonado e do viewport, porque o bloco 0 é um parágrafo corrido. Ler os
    # documentos limpos primeiro evita depender só do corte.
    fontes_nome = [
        state.get("nucleo_narrativo"),
        state.get("one_pager"),
        state.get("prd_final"),
        state.get("spec_missao"),
    ]

    # Prioridade 1: 'Nome que o estudante vê: ...' nos documentos onde o nome vem limpo
    for fonte in fontes_nome:
        txt = _safe_str(fonte).strip()
        if not txt:
            continue
        m_nome = re.search(r"\*?\*?Nome que o estudante vê:\*?\*?\s*([^\n\r]+)", txt, re.IGNORECASE)
        if m_nome:
            clean = _encurtar_titulo(m_nome.group(1))
            if clean:
                return clean

    # Prioridade 2: Frontmatter YAML 'titulo: ...'
    for fonte in fontes:
        txt = _safe_str(fonte).strip()
        if not txt:
            continue
        meta, _ = extrair_metadados_frontmatter(txt)
        if meta.get("titulo"):
            clean = _encurtar_titulo(meta["titulo"])
            if clean:
                return clean
        m_tit = re.search(r"^\s*titulo:\s*[\"']?([^\"'\n\r]+)[\"']?", txt, re.MULTILINE | re.IGNORECASE)
        if m_tit:
            clean = _encurtar_titulo(m_tit.group(1))
            if clean:
                return clean

    # Prioridade 3: '# One-pager — ...' ou '# Spec — ...' ou '# PRD — ...'
    for fonte in fontes:
        txt = _safe_str(fonte).strip()
        if not txt:
            continue
        m_header = re.search(r"^#\s+(?:One-pager|Spec|PRD|0\.\s+Resumo executivo)\s+[—-]\s+([^\n\r]+)", txt, re.MULTILINE | re.IGNORECASE)
        if m_header:
            clean = re.sub(r"\s+v\d+(?:\.\d+)?.*$", "", m_header.group(1).strip()).strip()
            clean = _encurtar_titulo(clean)
            if clean:
                return clean

    # Prioridade 4: Fallback se contiver metadados
    fallback_str = _safe_str(fallback).strip()
    if fallback_str:
        m_nome = re.search(r"\*?\*?Nome que o estudante vê:\*?\*?\s*([^\n\r]+)", fallback_str, re.IGNORECASE)
        if m_nome:
            clean = _encurtar_titulo(m_nome.group(1))
            if clean:
                return clean

        meta, _ = extrair_metadados_frontmatter(fallback_str)
        if meta.get("titulo"):
            return _encurtar_titulo(meta["titulo"])

        m_tit = re.search(r"^\s*titulo:\s*[\"']?([^\"'\n\r]+)[\"']?", fallback_str, re.MULTILINE | re.IGNORECASE)
        if m_tit:
            return _encurtar_titulo(m_tit.group(1))

        m_header = re.search(r"^#\s+(?:One-pager|Spec|PRD|0\.\s+Resumo executivo)\s+[—-]\s+([^\n\r]+)", fallback_str, re.MULTILINE | re.IGNORECASE)
        if m_header:
            clean = re.sub(r"\s+v\d+(?:\.\d+)?.*$", "", m_header.group(1).strip()).strip()
            clean = _encurtar_titulo(clean)
            if clean:
                return clean

        if "prd_id:" not in fallback_str and "\n" not in fallback_str:
            return _encurtar_titulo(fallback_str) or fallback_str[:60]

    # Prioridade 5: Slug
    for fonte in fontes:
        slug = extrair_slug(_safe_str(fonte))
        if slug:
            return slug

    return "Missão Sem Título"


def list_saved_sessions() -> List[Dict[str, Any]]:
    """Lista todas as sessões salvas em `output/`, ordenadas pela mais recente."""
    settings = get_settings()
    base_dir = settings.output_path

    if not base_dir.exists():
        return []

    sessions: List[Dict[str, Any]] = []

    for entry in base_dir.iterdir():
        if not entry.is_dir() or entry.name.startswith("."):
            continue

        estado_file = entry / "estado.json"
        conversa_file = entry / "conversa.json"
        prd_file = entry / "PRD.md"

        conversa_data: Dict[str, Any] = {}
        if conversa_file.exists():
            try:
                conversa_data = json.loads(conversa_file.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("Falha ao ler %s: %s", conversa_file, exc)

        # `estado.json` tem ~1 MB por missão e o PRD.md, 60–90 KB. Antes ambos eram lidos
        # para *toda* sessão em *todo* rerun do Streamlit, o que fazia a listagem crescer
        # linearmente com o histórico (e, no Cloud Run com GCS-FUSE, virar segundos).
        # Agora só são lidos quando o `conversa.json` não traz a informação — o caso das
        # sessões gravadas antes de `save_session_record` passar a registrar esses campos.
        _cache: Dict[str, Any] = {}

        def carregar_state() -> Dict[str, Any]:
            if "state" not in _cache:
                state: Dict[str, Any] = {}
                if estado_file.exists():
                    try:
                        state = json.loads(estado_file.read_text(encoding="utf-8"))
                    except Exception as exc:
                        logger.warning("Falha ao ler %s: %s", estado_file, exc)
                if prd_file.exists() and not state.get("prd_final"):
                    try:
                        state["prd_final"] = prd_file.read_text(encoding="utf-8")
                    except Exception:
                        pass
                _cache["state"] = state
            return _cache["state"]

        def carregar_prd_meta() -> Dict[str, Any]:
            if "prd_meta" not in _cache:
                meta, _ = extrair_metadados_frontmatter(carregar_state().get("prd_final") or "")
                _cache["prd_meta"] = meta
            return _cache["prd_meta"]

        # Determina o título limpo
        title = conversa_data.get("title")
        if not title or "prd_id:" in str(title) or "titulo:" in str(title) or "\n" in str(title):
            title = carregar_prd_meta().get("titulo") or extrair_titulo_missao(carregar_state(), fallback=entry.name)

        slug = conversa_data.get("slug")
        if not slug:
            state = carregar_state()
            slug = carregar_prd_meta().get("slug_experiencia") or extrair_slug(str(state.get("spec_missao") or state.get("one_pager") or state.get("prd_final") or "")) or entry.name

        # Timestamp de criação
        timestamp_str = conversa_data.get("created_at")
        if not timestamp_str:
            # Tenta extrair da pasta YYYYMMDD-HHMMSS
            m_time = re.match(r"^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})", entry.name)
            if m_time:
                y, m, d, h, mi, s = m_time.groups()
                timestamp_str = f"{d}/{m}/{y} {h}:{mi}"
            else:
                mtime = entry.stat().st_mtime
                timestamp_str = time.strftime("%d/%m/%Y %H:%M", time.localtime(mtime))

        # Gates conhecidos. O `conversa.json` já grava `gates`; o estado só é consultado
        # para sessões antigas, que não têm esse campo.
        gates = dict(conversa_data.get("gates") or {})
        if not gates:
            state = carregar_state()
            for k in ("micro_gate_status", "gate_estrutural_status", "gate_final_status", "bncc_status", "lacunas_status", "ambiente_status", "design_status", "manifesto_status", "telemetria_status", "rastro_lacunas_status", "dev_status", "prd_status"):
                if k in state:
                    gates[k] = state[k]

        has_blocked_gate = any(
            str(v).strip().lower() in ("bloqueado", "blocked", "reprovado", "vermelho", "🔴")
            for v in gates.values()
        )
        if "pipeline_bloqueado" in conversa_data:
            is_pipeline_blocked = bool(conversa_data.get("pipeline_bloqueado"))
        else:
            is_pipeline_blocked = bool(carregar_state().get("pipeline_bloqueado"))

        if prd_file.exists():
            has_prd = True
        elif "has_prd" in conversa_data:
            has_prd = bool(conversa_data["has_prd"])
        else:
            has_prd = bool(carregar_state().get("prd_final"))

        # Status: determinado pelo veredito dos gates e pela geração do PRD
        if is_pipeline_blocked:
            status = "bloqueado"
        elif has_prd and has_blocked_gate:
            status = "bypassed"
        elif has_prd or conversa_data.get("status") in ("success", "aprovado"):
            status = "aprovado"
        elif (entry / "produto/04-gate-final.md").exists() or has_blocked_gate:
            status = "bloqueado"
        else:
            status = conversa_data.get("status") or carregar_prd_meta().get("status") or "indefinido"

        if status in ("bypassed", "bypass", "warning", "ressalvas"):
            status_icon = "🟡"
        elif status in ("aprovado", "success"):
            status_icon = "🟢"
        elif status in ("bloqueado", "blocked"):
            status_icon = "🔴"
        elif status in ("em-revisao", "em_revisao", "em revisão"):
            status_icon = "🟡"
        elif status in ("em-implementacao", "em_implementacao"):
            status_icon = "🔵"
        else:
            status_icon = "⚪"

        status_label = formatar_status_label(status)

        # Prompt original
        prompt = conversa_data.get("prompt") or ""
        if not prompt and (entry / "briefing-original.md").exists():
            try:
                prompt = (entry / "briefing-original.md").read_text(encoding="utf-8").strip()
            except Exception:
                prompt = ""

        # Contagem de arquivos úteis. O `glob("**/*.md")` recursivo só roda para sessões
        # antigas, que não gravaram `files_count` no conversa.json.
        files_count = conversa_data.get("files_count")
        if files_count is None:
            files_count = len(list(entry.glob("**/*.md")))

        # Parecer humano (`pipeline/passagem.py`): a fila "Aguardando você" sai daqui, sem abrir
        # mais nenhum arquivo. Sessões anteriores ao parecer não têm `fluxo` e ficam de fora da fila.
        fluxo = conversa_data.get("fluxo") if isinstance(conversa_data.get("fluxo"), dict) else {}

        sessions.append(
            {
                "dir_name": entry.name,
                "path": str(entry),
                "title": title,
                "slug": slug,
                "session_id": conversa_data.get("session_id") or entry.name,
                "created_at": timestamp_str,
                "status": status,
                "status_label": status_label,
                "status_icon": status_icon,
                "has_prd": prd_file.exists(),
                "prompt": prompt,
                "files_count": files_count,
                "mtime": entry.stat().st_mtime,
                "fluxo_etapa": fluxo.get("etapa"),
                "fluxo_situacao": fluxo.get("situacao"),
                "fluxo_atualizado_em": fluxo.get("atualizado_em"),
            }
        )

    # Ordena decrescente pelo tempo de modificação
    sessions.sort(key=lambda s: s["mtime"], reverse=True)
    return sessions


def load_saved_session(dir_name_or_id: str) -> Optional[Tuple[List[Dict[str, Any]], Any, Dict[str, Any]]]:
    """Carrega uma sessão salva do disco.
    
    Retorna uma tupla (messages, pipeline_result, metadata) ou None se não encontrada.
    """
    settings = get_settings()
    base_dir = settings.output_path

    target_dir = base_dir / dir_name_or_id
    if not target_dir.exists():
        # Busca por session_id
        for d in base_dir.iterdir():
            if d.is_dir() and dir_name_or_id in d.name:
                target_dir = d
                break

    if not target_dir.exists() or not target_dir.is_dir():
        return None

    state: Dict[str, Any] = {}
    estado_file = target_dir / "estado.json"
    if estado_file.exists():
        try:
            state = json.loads(estado_file.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Falha ao carregar estado de %s: %s", estado_file, exc)

    conversa_data: Dict[str, Any] = {}
    conversa_file = target_dir / "conversa.json"
    if conversa_file.exists():
        try:
            conversa_data = json.loads(conversa_file.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Falha ao carregar conversa de %s: %s", conversa_file, exc)

    prompt = conversa_data.get("prompt") or ""
    if not prompt and (target_dir / "briefing-original.md").exists():
        try:
            prompt = (target_dir / "briefing-original.md").read_text(encoding="utf-8").strip()
        except Exception:
            prompt = ""

    # `step_outputs` vem do conversa.json quando existe. Não é reconstruído a partir do
    # disco: em execução ele é indexado pelo id do agente (ver `runner.py`), enquanto
    # ARTIFACT_FILES usa `output_key` — as chaves nunca batiam com o único consumidor
    # (`app.py`), e a reconstrução custava 43 leituras de arquivo por clique no histórico
    # (no Cloud Run, 43 RPCs no GCS-FUSE). O render lê tudo de `result.state`.
    step_outputs = conversa_data.get("step_outputs", {})

    # Importa PipelineExecutionResult tardiamente para evitar imports circulares
    from pipeline.runner import PipelineExecutionResult

    gates = dict(conversa_data.get("gates") or {})
    for k in ("micro_gate_status", "gate_estrutural_status", "gate_final_status", "bncc_status", "lacunas_status", "ambiente_status", "design_status", "manifesto_status", "telemetria_status", "rastro_lacunas_status", "dev_status", "prd_status"):
        if k in state and k not in gates:
            gates[k] = state[k]

    has_blocked_gate = any(
        str(v).strip().lower() in ("bloqueado", "blocked", "reprovado", "vermelho", "🔴")
        for v in gates.values()
    )
    is_pipeline_blocked = bool(state.get("pipeline_bloqueado"))
    has_prd = (target_dir / "PRD.md").exists() or bool(state.get("prd_final"))

    final_output = state.get("prd_final") or state.get("spec_missao") or state.get("gate_final_report") or ""
    saved_status = conversa_data.get("status")
    prd_raw = state.get("prd_final")
    if not prd_raw and (target_dir / "PRD.md").exists():
        try:
            prd_raw = (target_dir / "PRD.md").read_text(encoding="utf-8")
        except Exception:
            prd_raw = ""
    prd_meta, _ = extrair_metadados_frontmatter(str(prd_raw or ""))
    prd_status = prd_meta.get("status")

    if is_pipeline_blocked:
        status = "bloqueado"
    elif has_prd and has_blocked_gate:
        status = "bypassed"
    elif has_prd or saved_status in ("success", "aprovado"):
        status = "success"
    elif (target_dir / "produto/04-gate-final.md").exists() or has_blocked_gate:
        status = "blocked"
    else:
        status = saved_status or prd_status or "indefinido"

    result = PipelineExecutionResult(
        session_id=conversa_data.get("session_id") or target_dir.name,
        user_id=conversa_data.get("user_id") or "saved_user",
        prompt=prompt,
        final_output=final_output,
        step_outputs=step_outputs,
        step_thoughts=conversa_data.get("step_thoughts", {}),
        attached_files=conversa_data.get("attached_files", []),
        state=state,
        duration_seconds=conversa_data.get("duration_seconds", 0.0),
        status=status,
        output_dir=str(target_dir),
    )

    # Reconstrói messages limpando mensagens de boas-vindas e evitando duplicações
    raw_messages = conversa_data.get("messages") or []
    cleaned_messages: List[Dict[str, Any]] = []

    for m in raw_messages:
        content = str(m.get("content") or "").strip()
        if content.startswith("👋 Olá!") or "Gerador de Missões Unooria" in content:
            continue
        cleaned_messages.append({
            "role": m.get("role", "user"),
            "content": content,
        })

    messages: List[Dict[str, Any]] = []
    if cleaned_messages:
        # Encontra o índice da ÚLTIMA mensagem do assistente para anexar o pipeline_result
        last_assistant_idx = -1
        for i, m in enumerate(cleaned_messages):
            if m.get("role") == "assistant":
                last_assistant_idx = i

        for i, m in enumerate(cleaned_messages):
            is_target_assistant = (i == last_assistant_idx)
            messages.append({
                "role": m["role"],
                "content": m["content"],
                "pipeline_result": result if is_target_assistant else None,
            })
    else:
        # Se não havia mensagens salvas válidas, reconstrói o par [user, assistant] padrão
        if prompt:
            messages.append({"role": "user", "content": prompt})
        if state.get("prd_final"):
            summary = (
                "🟡 **PRD gerado com ressalvas (gates bypassados).** Veja as abas abaixo."
                if (status == "bypassed" or (has_blocked_gate and not is_pipeline_blocked))
                else "📘 **PRD gerado.** Veja as abas abaixo."
            )
        else:
            summary = final_output
        messages.append({
            "role": "assistant",
            "content": summary if len(summary) < 4000 else "Resultado do pipeline:",
            "pipeline_result": result,
        })

    # Garante que o título e slug sejam limpos
    title = conversa_data.get("title")
    if not title or "prd_id:" in str(title) or "titulo:" in str(title) or "\n" in str(title):
        title = extrair_titulo_missao(state, target_dir.name)

    metadata = {
        "dir_name": target_dir.name,
        "path": str(target_dir),
        "title": title,
        "slug": conversa_data.get("slug") or extrair_slug(str(state.get("spec_missao") or "")),
        "session_id": result.session_id,
        "status": status,
        "status_label": formatar_status_label(status),
        "created_at": conversa_data.get("created_at"),
        "historico_correcoes": (
            conversa_data.get("historico_correcoes")
            if isinstance(conversa_data.get("historico_correcoes"), list)
            else conversa_data.get("reexecucoes") if isinstance(conversa_data.get("reexecucoes"), list) else []
        ),
    }

    return messages, result, metadata


def save_session_record(
    run_dir: Path,
    session_id: str,
    user_id: str,
    prompt: str,
    result: Any,
    messages: List[Dict[str, Any]],
    attached_files: Optional[List[str]] = None,
    created_at: Optional[str] = None,
    historico_correcoes: Optional[List[Dict[str, Any]]] = None,
    fluxo: Optional[Dict[str, Any]] = None,
) -> Path:
    """Grava `conversa.json`.

    O `fluxo` do parecer humano (`pipeline/passagem.py`) é preservado do arquivo em disco quando
    não vem explícito: este arquivo é regravado do zero pelo runner e pela correção, e perder o
    fluxo apagaria os pareceres de quem já deu *de acordo*.

    `created_at` e `historico_correcoes` existem para a correção de uma sessão
    (`pipeline/reexecucao.py`): a data de criação é a original, e o histórico acumula.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    state = getattr(result, "state", {}) or {}
    if not state and (run_dir / "estado.json").exists():
        try:
            state = json.loads((run_dir / "estado.json").read_text(encoding="utf-8"))
        except Exception:
            state = {}

    title = extrair_titulo_missao(state, fallback=prompt[:60].strip() or "Missão")
    if "prd_id:" in title or "titulo:" in title or "\n" in title:
        title = extrair_titulo_missao({"prd_final": title}, fallback="Missão")

    slug = extrair_slug(str(state.get("spec_missao") or state.get("one_pager") or state.get("prd_final") or "")) or session_id[:12]

    # Serializa mensagens sem o pipeline_result interno e excluindo mensagens de boas-vindas
    serializable_messages = []
    for m in messages:
        content = str(m.get("content") or "").strip()
        if content.startswith("👋 Olá!") or "Gerador de Missões Unooria" in content:
            continue
        serializable_messages.append({
            "role": m.get("role", "user"),
            "content": content,
        })

    if not serializable_messages:
        if prompt:
            serializable_messages.append({"role": "user", "content": prompt})
        serializable_messages.append({
            "role": "assistant",
            "content": "📘 **PRD gerado.** Veja as abas abaixo." if getattr(result, "state", {}).get("prd_final") else "Resultado do pipeline:",
        })

    data = {
        "session_id": session_id,
        "user_id": user_id,
        "title": title,
        "slug": slug,
        "created_at": created_at or time.strftime("%d/%m/%Y %H:%M:%S"),
        "prompt": prompt,
        "attached_files": attached_files or getattr(result, "attached_files", []),
        "status": getattr(result, "status", "success"),
        "duration_seconds": getattr(result, "duration_seconds", 0.0),
        "gates": getattr(result, "gates", {}),
        "messages": serializable_messages,
        "step_thoughts": getattr(result, "step_thoughts", {}),
        # Campos de índice: permitem que `list_saved_sessions` monte a sidebar lendo só
        # este arquivo (~2 KB), sem abrir o `estado.json` de ~1 MB a cada rerun.
        "pipeline_bloqueado": bool(state.get("pipeline_bloqueado")),
        "has_prd": bool(state.get("prd_final")) or (run_dir / "PRD.md").exists(),
        "files_count": sum(1 for p in list_session_files(run_dir) if p.suffix == ".md"),
    }
    if historico_correcoes:
        data["historico_correcoes"] = historico_correcoes

    conversa_path = run_dir / "conversa.json"
    if fluxo is None and conversa_path.exists():
        try:
            fluxo = json.loads(conversa_path.read_text(encoding="utf-8")).get("fluxo")
        except (OSError, ValueError):
            fluxo = None
    if isinstance(fluxo, dict):
        data["fluxo"] = fluxo

    conversa_path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return conversa_path


def delete_saved_session(dir_name_or_id: str) -> bool:
    """Remove o diretório de uma sessão salva."""
    settings = get_settings()
    base_dir = settings.output_path

    target_dir = base_dir / dir_name_or_id
    if not target_dir.exists():
        for d in base_dir.iterdir():
            if d.is_dir() and dir_name_or_id in d.name:
                target_dir = d
                break

    if target_dir.exists() and target_dir.is_dir():
        try:
            shutil.rmtree(target_dir)
            return True
        except Exception as exc:
            logger.error("Erro ao deletar sessão %s: %s", target_dir, exc)
            return False
    return False




def resolve_session_dir(dir_or_path: str | Path | None) -> Optional[Path]:
    """Resolve o diretório real de uma sessão, tolerando caminhos obsoletos.

    O caminho gravado em `PipelineExecutionResult.output_dir` é absoluto e pode ter sido
    produzido com outro `OUTPUT_DIR` (por exemplo, execução local versus `/app/output`
    montado do Cloud Storage). Nesse caso, procura o mesmo nome de pasta dentro do
    `output_path` configurado no momento da chamada.
    """
    if not dir_or_path:
        return None

    candidate = Path(dir_or_path)
    try:
        if candidate.is_dir():
            return candidate
    except OSError as exc:
        logger.warning("Falha ao verificar %s: %s", candidate, exc)

    base = get_settings().output_path
    try:
        fallback = base / candidate.name
        if fallback.is_dir():
            logger.info("Diretório %s não existe; usando %s", candidate, fallback)
            return fallback
    except OSError as exc:
        logger.warning("Falha ao verificar %s: %s", base, exc)

    return None


#: Pastas que guardam versões anteriores de uma sessão corrigida: `.correcoes/` (atual) e
#: `_reexecucoes/` (nome antigo do script). Não são artefatos: ficam fora do manifesto e do ZIP.
PASTAS_DE_BACKUP = ("_reexecucoes",)


def _oculto(rel: Path) -> bool:
    """Caminho relativo com algum componente oculto (`.algo`) ou de backup."""
    return any(parte.startswith(".") or parte in PASTAS_DE_BACKUP for parte in rel.parts)


def list_session_files(run_dir: Path) -> List[Path]:
    """Lista, em ordem estável, todos os arquivos visíveis de uma sessão.

    Entradas que desaparecem ou falham no `stat` durante a varredura (comum em
    sistemas de arquivos montados via FUSE) são ignoradas em vez de abortar a listagem.
    """
    files: List[Path] = []
    for path in run_dir.rglob("*"):
        if _oculto(path.relative_to(run_dir)):
            continue
        try:
            if path.is_file():
                files.append(path)
        except OSError as exc:
            logger.warning("Ignorando %s ao listar a sessão: %s", path, exc)
    files.sort(key=lambda p: p.relative_to(run_dir).as_posix())
    return files


def session_dir_signature(run_dir: Path) -> str:
    """Impressão digital do conteúdo da pasta, usada como chave de cache."""
    parts: List[str] = []
    for path in list_session_files(run_dir):
        try:
            stat = path.stat()
            parts.append(f"{path.relative_to(run_dir).as_posix()}:{stat.st_size}:{int(stat.st_mtime)}")
        except OSError:
            continue
    return "|".join(parts)


def _zip_timestamp(path: Path) -> Tuple[int, int, int, int, int, int]:
    """Data/hora do arquivo no formato do ZIP, limitada ao mínimo aceito (1980)."""
    try:
        mtime = time.localtime(path.stat().st_mtime)
    except OSError:
        mtime = time.localtime()
    if mtime.tm_year < 1980:
        return (1980, 1, 1, 0, 0, 0)
    return (mtime.tm_year, mtime.tm_mon, mtime.tm_mday, mtime.tm_hour, mtime.tm_min, mtime.tm_sec)


def nome_do_zip_de_artefatos(state: Dict[str, Any], session_id: str) -> str:
    """`artefatos_<slug>.zip` — `artefatos_exp09ef1b.zip`, ano e bimestre da missão.

    O slug sai da spec, do one-pager ou do PRD, nessa ordem. Missão que ainda não tem nenhum
    deles (produto gerando) cai no id da sessão, como era antes de 06/10/2026.
    """
    for chave in ("spec_missao", "one_pager", "prd_final"):
        slug = extrair_slug(_safe_str((state or {}).get(chave)))
        if slug:
            return f"artefatos_{slug}.zip"
    return f"artefatos_{(session_id or 'session')[:12]}.zip"


def create_session_zip(run_dir_path: str | Path) -> bytes:
    """Gera um arquivo ZIP em memória com todos os artefatos da missão.

    Lê o conteúdo de cada arquivo explicitamente (em vez de delegar a leitura ao
    `zipfile`), de modo que um arquivo ilegível seja pulado com aviso em vez de
    derrubar o pacote inteiro. A ordem das entradas e os carimbos de tempo são
    estáveis, então chamadas repetidas com o mesmo conteúdo produzem bytes idênticos.

    Levanta `FileNotFoundError` se o diretório não for encontrado ou estiver vazio.
    """
    run_dir = resolve_session_dir(run_dir_path)
    if run_dir is None:
        raise FileNotFoundError(
            f"Diretório da sessão não encontrado: {run_dir_path} "
            f"(OUTPUT_DIR atual: {get_settings().output_path})"
        )

    files = list_session_files(run_dir)
    if not files:
        raise FileNotFoundError(f"Nenhum artefato legível em {run_dir}")

    skipped: List[str] = []
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:
            rel_path = file_path.relative_to(run_dir).as_posix()
            try:
                data = file_path.read_bytes()
            except OSError as exc:
                logger.warning("Não foi possível ler %s para o ZIP: %s", file_path, exc)
                skipped.append(rel_path)
                continue

            info = zipfile.ZipInfo(rel_path, date_time=_zip_timestamp(file_path))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, data)

        if skipped:
            zf.writestr(
                "ARQUIVOS-NAO-INCLUIDOS.txt",
                "Os arquivos abaixo estavam no diretório da missão mas não puderam ser lidos:\n\n"
                + "\n".join(f"- {p}" for p in skipped)
                + "\n",
            )

    if len(skipped) == len(files):
        raise FileNotFoundError(f"Nenhum artefato pôde ser lido em {run_dir}")

    return buffer.getvalue()
