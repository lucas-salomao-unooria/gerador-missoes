"""Persistência dos artefatos de uma execução em `output/<data>-<slug>/`, com suporte a ADK Artifacts."""

from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.callbacks import extrair_slug
from config import get_settings

logger = logging.getLogger("artifacts")

# Ordem e nome de arquivo por chave de estado
ARTIFACT_FILES = [
    ("nucleo_narrativo", "produto/00a-nucleo-narrativo.md"),
    ("micro_gate_report", "produto/00b-micro-gate.md"),
    ("one_pager", "produto/00-one-pager.md"),
    ("brief_escopo", "produto/00f-brief-escopo.md"),
    ("contrato_produto_report", "produto/00e-contrato-produto.md"),
    ("gate_estrutural_report", "produto/01-gate-estrutural.md"),
    ("avaliacao_pedagogica_report", "produto/02-avaliacao-pedagogica.md"),
    ("experiencia_aluno_report", "produto/03-experiencia-aluno.md"),
    ("adequacao_report", "produto/03b-adequacao-pedagogica.md"),
    ("gate_final_report", "produto/04-gate-final.md"),
    ("spec_missao", "produto/05-spec-missao.md"),
    ("one_pager_gate0", "produto/00c-one-pager-original.md"),
    ("spec_missao_gate0", "produto/05a-spec-missao-gate0.md"),
    ("bncc_report", "produto/05b-conformidade-bncc.md"),
    ("one_pager_resumido", "produto/00d-one-pager-resumido.md"),
    ("fechamento_lacunas", "design/00-fechamento-lacunas.md"),
    ("relatorio_lacunas", "design/00a-relatorio-lacunas.md"),
    ("ambiente_simulado", "design/00b-ambiente-simulado.md"),
    ("brief_oficio", "design/01-briefing-oficio.md"),
    ("jornada_telas", "design/02-jornada-telas.md"),
    ("fluxo_arestas", "design/03-fluxo-arestas.md"),
    ("copy_strings", "design/04-copy-strings.md"),
    ("camada_caa", "design/04b-camada-caa.md"),
    ("wireframes_cobertura", "design/05-wireframes-cobertura.md"),
    ("copy_strings_revisada", "design/06-copy-strings-revisada.md"),
    ("prototipo_relatorio", "design/08-prototipo.md"),
    ("prototipo_arquivo", "design/08-prototipo.html"),
    ("diagramas_html", "design/09-diagramas.html"),
    ("stitch_links", "design/10-stitch-telas.md"),
    ("miro_links", "design/11-miro-boards.md"),
    ("qa_entregaveis_report", "design/07-qa-entregaveis.md"),
    ("evidencia_report", "produto/05c-matriz-evidencia.md"),
    ("manifesto_report", "dev/00-ficha-manifesto.md"),
    ("handoff_dev", "dev/01-handoff-dev.md"),
    ("brief_assets", "dev/01b-brief-assets.md"),
    ("telemetria_report", "dev/01c-telemetria-check.md"),
    ("rastro_lacunas_report", "dev/01d-rastro-lacunas.md"),
    ("validacao_produto_narrativa", "dev/02a-banca-produto-narrativa.md"),
    ("validacao_design_imersao", "dev/02b-banca-design-imersao.md"),
    ("validacao_pedagogia_bncc", "dev/02c-banca-pedagogia-bncc.md"),
    ("validacao_dados_lgpd", "dev/02d-banca-dados-lgpd.md"),
    ("validacao_tecnica_arquitetura", "dev/02e-banca-tecnica-arquitetura.md"),
    ("validacao_dev_report", "dev/03-banca-consolidada.md"),
    ("prd_final", "PRD.md"),
    ("one_pager_pedagogico", "one-pager-pedagogico.md"),
    ("prd_check_report", "dev/04-pendencias-do-prd.md"),
    ("diagnostico_execucao", "diagnostico-execucao.md"),
    ("aprendizado_registro", "aprendizado.md"),
    ("ficha_catalogo", "catalogo-ficha.md"),
]

STAGE_NAMES = {
    "produto": "🧭 Produto",
    "design": "🎨 Design",
    "dev": "🛠️ Dev",
}



def _safe(name: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-") or "missao"


# Só `markdown`/`md`: é assim que o agente embrulha o documento. Uma cerca externa de
# outra linguagem (```json, ```sql) é o conteúdo do arquivo, não um invólucro.
_CERCA_EXTERNA = re.compile(r"\A\s*```(?:markdown|md)\s*\n(.*)\n\s*```\s*\Z", re.DOTALL | re.IGNORECASE)


def desembrulhar_cerca(texto: str) -> str:
    """Tira a cerca de código que envolve o documento INTEIRO.

    O agente às vezes entrega o documento dentro de ```markdown para deixar claro onde
    ele começa e termina. Salvo como está, o `.md` abre como um bloco de código e o
    front matter do PRD deixa de ser front matter. Só remove quando a cerca abre na
    primeira linha e fecha na última: cerca no meio do texto é conteúdo.
    """
    if not isinstance(texto, str):
        return texto
    m = _CERCA_EXTERNA.match(texto)
    if not m:
        return texto
    miolo = m.group(1)
    # O documento pode ter blocos de código legítimos dentro (json, sql, mermaid). Eles
    # vêm aos pares, então um miolo com número PAR de cercas é conteúdo balanceado e o
    # invólucro externo é real. Ímpar é ambíguo — aí não se mexe.
    internas = len(re.findall(r"^\s*```", miolo, re.MULTILINE))
    return miolo if internas % 2 == 0 else texto


def e_mensagem_de_pulo(valor: Any) -> bool:
    """O ADK grava no `output_key` o texto do callback que pulou o agente.

    Sem este filtro, um pipeline bloqueado produz um `PRD.md` de 88 bytes dizendo
    "A47PrdWriter não executado" — e a interface, que só testa se a chave existe,
    anuncia "PRD gerado".
    """
    if not isinstance(valor, str):
        return False
    inicio = valor.strip()[:200]
    return inicio.startswith("⏭️") and "não executado" in inicio



def generate_artifact_manifest(run_dir: Path) -> List[Dict[str, Any]]:
    """Gera um manifesto descritivo de todos os artefatos salvos em `run_dir`."""
    manifest: List[Dict[str, Any]] = []

    for path in sorted(run_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(run_dir).as_posix()
        # `.correcoes/` (backups de correção) e `_reexecucoes/` (nome antigo) não são artefatos
        if rel.startswith(".") or rel.startswith("_reexecucoes/") or rel == "manifesto-artefatos.json":
            continue

        size = path.stat().st_size
        size_str = f"{size / 1024:.1f} KB" if size >= 1024 else f"{size} B"

        # Categoria
        parts = rel.split("/")
        category = "Raiz"
        if len(parts) > 1:
            category = STAGE_NAMES.get(parts[0], parts[0].capitalize())

        mime_type, _ = mimetypes.guess_type(path.name)
        if not mime_type:
            mime_type = "text/markdown" if path.suffix == ".md" else "application/json"
        if path.suffix == ".html":
            mime_type = "text/html"
        elif path.suffix == ".docx":
            mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        manifest.append(
            {
                "path": rel,
                "filename": path.name,
                "category": category,
                "size_bytes": size,
                "size_str": size_str,
                "mime_type": mime_type,
            }
        )

    return manifest


async def _save_adk_artifacts(
    run_dir: Path,
    app_name: str,
    user_id: str,
    session_id: str,
    artifact_service: Any,
) -> int:
    """Registra artefatos no FileArtifactService do Google ADK."""
    if not artifact_service:
        return 0

    from google.genai import types

    count = 0
    for path in run_dir.rglob("*"):
        if not path.is_file() or path.name.startswith("."):
            continue
        rel = path.relative_to(run_dir).as_posix()
        mime_type, _ = mimetypes.guess_type(path.name)
        mime_type = mime_type or ("text/markdown" if path.suffix == ".md" else "application/octet-stream")

        try:
            data = path.read_bytes()
            part = types.Part.from_bytes(data=data, mime_type=mime_type)
            await artifact_service.save_artifact(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                filename=rel,
                artifact=part,
            )
            count += 1
        except Exception as exc:
            logger.debug("Aviso ao registrar artefato ADK %s: %s", rel, exc)

    return count


# Os documentos que saem da esteira para gente ler, e a etiqueta com que cada um se
# apresenta na capa. O resto dos artefatos é insumo de trabalho e fica em Markdown.
ONE_PAGERS_COM_MARCA = [
    ("one_pager", "produto/00-one-pager", "One-pager de produto", "Documento de produto · Unooria"),
    (
        "one_pager_resumido",
        "produto/00d-one-pager-resumido",
        "One-pager resumido",
        "Para avaliação pedagógica · Unooria",
    ),
    (
        "one_pager_pedagogico",
        "one-pager-pedagogico",
        "One-pager pedagógico",
        "Para leitura e aprovação do time pedagógico",
    ),
]


def exportar_one_pagers(state: Dict[str, Any], run_dir: Path, slug: str) -> List[Path]:
    """Grava cada one-pager em `.docx` e `.html` com a identidade visual da Unooria.

    Dois formatos porque são dois usos: o `.docx` abre no Word e no Google Docs para o
    time comentar e editar; o `.html` abre no navegador e vira PDF pelo "Imprimir", que
    é como a missão é apresentada para fora. O Markdown continua salvo do lado, porque é
    dele que os dois saem e é ele que a esteira lê.

    Falha aqui não derruba a execução: o documento em Markdown já está no disco, e o que
    se perde é a formatação, não o conteúdo.
    """
    gerados: List[Path] = []
    for chave, base, etiqueta, subtitulo in ONE_PAGERS_COM_MARCA:
        documento = state.get(chave)
        if not documento or not isinstance(documento, str) or e_mensagem_de_pulo(documento):
            continue

        destino_docx = run_dir / f"{base}.docx"
        try:
            from tools.docx_export import markdown_para_docx

            if markdown_para_docx(
                documento, destino_docx, titulo_fallback=slug, etiqueta=etiqueta, subtitulo=subtitulo
            ):
                gerados.append(destino_docx)
        except Exception as exc:
            logger.warning("Não consegui gerar o .docx de %s: %s", base, exc)

        destino_html = run_dir / f"{base}.html"
        try:
            from tools.onepager_html import markdown_para_html

            pagina = markdown_para_html(
                documento, titulo_fallback=slug, etiqueta=etiqueta, subtitulo=subtitulo
            )
            destino_html.parent.mkdir(parents=True, exist_ok=True)
            destino_html.write_text(pagina, encoding="utf-8")
            gerados.append(destino_html)
        except Exception as exc:
            logger.warning("Não consegui gerar o .html de %s: %s", base, exc)

    return gerados


def save_run_artifacts(
    state: Dict[str, Any],
    session_id: str,
    prompt: str = "",
    artifact_service: Optional[Any] = None,
    app_name: str = "GeradorMissoesUnooria",
    user_id: str = "usuario",
    run_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Grava cada saída do pipeline como Markdown, mais o manifesto e o estado completo em JSON.

    `run_dir` fixa a pasta de destino — é como uma etapa reexecutada sobre o estado salvo
    (`scripts/rerodar_etapa.py`) sobrescreve a sessão original em vez de abrir outra.
    """
    settings = get_settings()
    base = settings.output_path
    slug = extrair_slug(str(state.get("spec_missao") or state.get("one_pager") or "")) or _safe(session_id[:12])
    if run_dir is None:
        run_dir = base / f"{time.strftime('%Y%m%d-%H%M%S')}-{_safe(slug)}"
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    for key, rel in ARTIFACT_FILES:
        value = state.get(key)
        if not value or e_mensagem_de_pulo(value):
            continue
        path = run_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        text = value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False)
        path.write_text(desembrulhar_cerca(text).strip() + "\n", encoding="utf-8")
        written += 1


    # Os one-pagers também com a marca: quem os lê não lê Markdown, e são eles que circulam
    # fora do time — a PM encaminha o de produto, o time de produto avalia pelo resumido e a
    # professora aprova o pedagógico.
    exportar_one_pagers(state, run_dir, slug)

    # Estado serializável
    serializable = {k: v for k, v in state.items() if not str(k).startswith("temp:")}
    (run_dir / "estado.json").write_text(
        json.dumps(serializable, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    if prompt:
        (run_dir / "briefing-original.md").write_text(prompt.strip() + "\n", encoding="utf-8")

    # Manifesto de artefatos
    manifest = generate_artifact_manifest(run_dir)
    (run_dir / "manifesto-artefatos.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Registro no FileArtifactService do ADK caso fornecido
    if artifact_service:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Agenda no loop corrente se async
                asyncio.create_task(
                    _save_adk_artifacts(run_dir, app_name, user_id, session_id, artifact_service)
                )
            else:
                loop.run_until_complete(
                    _save_adk_artifacts(run_dir, app_name, user_id, session_id, artifact_service)
                )
        except Exception as exc:
            logger.debug("Não foi possível registrar no serviço ADK de forma síncrona: %s", exc)

    return run_dir if written else run_dir
