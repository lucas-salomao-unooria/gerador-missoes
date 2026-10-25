"""Persistência dos artefatos de uma execução em `output/<data>-<slug>/`, com suporte a ADK Artifacts."""

from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import posixpath
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from agents.callbacks import extrair_slug
from config import get_settings

logger = logging.getLogger("artifacts")

# Ordem e nome de arquivo por chave de estado
ARTIFACT_FILES = [
    ("material_anexado", "produto/00-material-anexado.md"),
    ("mapa_conceitual", "produto/00g-mapa-conceitual.md"),
    ("ideacao_mecanismos", "produto/00h-ideacao-mecanismos.md"),
    ("nucleo_narrativo", "produto/00a-nucleo-narrativo.md"),
    ("cobertura_report", "produto/00i-cobertura-conceitual.md"),
    ("micro_gate_report", "produto/00b-micro-gate.md"),
    ("profundidade_report", "produto/00j-juiz-profundidade.md"),
    ("one_pager", "produto/00-one-pager.md"),
    ("evidencia_one_pager_report", "produto/00k-contrato-evidencia-12a.md"),
    ("comite_canal_a_report", "produto/00l-comite-canais-painel-a.md"),
    ("comite_canal_b_report", "produto/00m-comite-canais-painel-b.md"),
    ("brief_escopo", "produto/00f-brief-escopo.md"),
    ("contrato_produto_report", "produto/00e-contrato-produto.md"),
    ("gate_estrutural_report", "produto/01-gate-estrutural.md"),
    ("avaliacao_pedagogica_report", "produto/02-avaliacao-pedagogica.md"),
    ("experiencia_aluno_report", "produto/03-experiencia-aluno.md"),
    ("adequacao_report", "produto/03b-adequacao-pedagogica.md"),
    ("mecanica_one_pager_report", "produto/03c-conta-da-virada-one-pager.md"),
    ("comite_final_report", "produto/03d-comite-final.md"),
    ("gate_final_report", "produto/04-gate-final.md"),
    ("spec_missao", "produto/05-spec-missao.md"),
    ("one_pager_gate0", "produto/00c-one-pager-original.md"),
    ("spec_missao_gate0", "produto/05a-spec-missao-gate0.md"),
    ("bncc_report", "produto/05b-conformidade-bncc.md"),
    ("one_pager_resumido", "produto/00d-one-pager-resumido.md"),
    # os textos-chave com ID (PR 7): a tabela que o de acordo mostra e que design e dev recebem
    ("textos_chave_tabela", "produto/00n-textos-chave.md"),
    ("fechamento_lacunas", "design/00-fechamento-lacunas.md"),
    ("relatorio_lacunas", "design/00a-relatorio-lacunas.md"),
    # o anexo de design da spec (PR 6): blocos 13 (D0-UX) e 14 (D9), fora de `produto/05-spec-missao.md`
    ("anexo_design_spec", "design/00-anexo-design-spec.md"),
    ("ambiente_simulado", "design/00b-ambiente-simulado.md"),
    ("brief_oficio", "design/01-briefing-oficio.md"),
    ("jornada_telas", "design/02-jornada-telas.md"),
    ("fluxo_arestas", "design/03-fluxo-arestas.md"),
    ("arestas_report", "design/03b-fluxo-x-spec.md"),
    ("copy_strings", "design/04-copy-strings.md"),
    ("camada_caa", "design/04b-camada-caa.md"),
    ("wireframes_cobertura", "design/05-wireframes-cobertura.md"),
    ("copy_strings_revisada", "design/06-copy-strings-revisada.md"),
    ("prototipo_relatorio", "design/08-prototipo.md"),
    ("prototipo_arquivo", "design/08-prototipo.html"),
    ("diagramas_html", "design/09-diagramas.html"),
    ("stitch_links", "design/10-stitch-telas.md"),
    ("miro_links", "design/11-miro-boards.md"),
    ("prototipo_lint_report", "design/06b-lint-prototipo.md"),
    ("consistencia_report", "design/06c-coerencia-documentos.md"),
    ("textos_chave_report", "design/06d-textos-chave.md"),
    ("qa_entregaveis_report", "design/07-qa-entregaveis.md"),
    ("qa_afirmacoes_report", "design/07b-qa-afirmacoes.md"),
    ("rastro_design_report", "design/12-rastro-lacunas-design.md"),
    # o one-pager pedagógico fecha o design desde o PR 10 (24/10/2026): até lá ficava na raiz, saído do fim do dev
    ("one_pager_pedagogico", "design/14-one-pager-pedagogico.md"),
    ("conteudo_aprovado_pedagogico_report", "design/14a-conteudo-aprovado-pedagogico.md"),
    ("montagem_pedagogico_report", "design/14b-montagem-pedagogico.md"),
    ("coerencia_pedagogico_report", "design/14c-coerencia-pedagogico.md"),
    ("evidencia_report", "produto/05c-matriz-evidencia.md"),
    ("perguntas_report", "produto/05d-perguntas-de-produto.md"),
    ("juiz_perguntas_report", "produto/05e-juiz-perguntas-de-produto.md"),
    ("rastro_spec_report", "produto/05f-rastro-lacunas-spec.md"),
    ("conteudo_aprovado_spec_report", "produto/05g-conteudo-aprovado.md"),
    # o passo de completude da spec (PR 6): a resposta inteira e o relatório; o bloco 15 está na própria spec
    ("completude_spec", "produto/05h-completude-spec.md"),
    ("relatorio_completude", "produto/05i-relatorio-completude.md"),
    ("manifesto_report", "dev/00-ficha-manifesto.md"),
    ("handoff_dev", "dev/01-handoff-dev.md"),
    ("brief_assets", "dev/01b-brief-assets.md"),
    ("banco_conteudo", "dev/01e-banco-conteudo.md"),
    ("conteudo_report", "dev/01f-banco-conteudo-check.md"),
    ("telemetria_report", "dev/01c-telemetria-check.md"),
    ("montagem_handoff_report", "dev/01g-montagem-handoff.md"),
    ("rastro_lacunas_report", "dev/01d-rastro-lacunas.md"),
    ("validacao_produto_narrativa", "dev/02a-banca-produto-narrativa.md"),
    ("validacao_design_imersao", "dev/02b-banca-design-imersao.md"),
    ("validacao_pedagogia_bncc", "dev/02c-banca-pedagogia-bncc.md"),
    ("validacao_dados_lgpd", "dev/02d-banca-dados-lgpd.md"),
    ("validacao_tecnica_arquitetura", "dev/02e-banca-tecnica-arquitetura.md"),
    ("validacao_dev_report", "dev/03-banca-consolidada.md"),
    ("prd_final", "PRD.md"),
    # o dev só acrescenta ao pedagógico (PR 10): o guarda que confere o texto aprovado e a seção das pendências do dev
    ("pedagogico_dev_report", "dev/07-pedagogico-no-dev.md"),
    ("kpis_report", "dev/04b-kpis-check.md"),
    ("prd_check_report", "dev/04-pendencias-do-prd.md"),
    ("conteudo_aprovado_prd_report", "dev/04c-conteudo-aprovado-prd.md"),
    ("montagem_prd_report", "dev/04e-montagem-prd.md"),
    ("coerencia_prd_report", "dev/04d-coerencia-prd.md"),
    ("conteudo_aprovado_resumido_report", "produto/05h-conteudo-aprovado-resumido.md"),
    ("banca_produto_report", "produto/05i-banca-produto.md"),
    ("banca_design_report", "design/07c-banca-design.md"),
    ("banca_entrada_report", "dev/00b-banca-entrada.md"),
    ("conteudo_aprovado_spec_design_report", "design/00c-spec-consolidada-x-one-pager.md"),
    ("fidelidade_design_report", "design/13-fidelidade-refazer-design.md"),
    ("fidelidade_dev_report", "dev/06-fidelidade-refazer-dev.md"),
    ("rastreabilidade_report", "matriz-de-rastreabilidade.md"),
    # a final do dev, quando existe, substitui a do design no mesmo arquivo (o laço grava na ordem desta lista)
    ("rastreabilidade_dev_report", "matriz-de-rastreabilidade.md"),
    # a correção pontual: as trocas aplicadas e de onde veio cada bloqueio dos gates (`tools/linha_de_base.py`)
    ("linha_de_base_report", "linha-de-base-da-correcao.md"),
    ("diagnostico_execucao", "diagnostico-execucao.md"),
    ("aprendizado_registro", "aprendizado.md"),
    ("ficha_catalogo", "catalogo-ficha.md"),
]

#: Onde o artefato da chave ficava antes de mudar de pasta: a gravação apaga o de antes quando grava o novo, e o backup de
#: uma reexecução o leva junto (`pipeline.reexecucao.arquivos_das_chaves`). O pedagógico saiu da raiz no PR 10.
CAMINHOS_LEGADOS: Dict[str, Tuple[str, ...]] = {
    "one_pager_pedagogico": ("one-pager-pedagogico.md", "one-pager-pedagogico.docx", "one-pager-pedagogico.html"),
    "conteudo_aprovado_pedagogico_report": ("dev/05-conteudo-aprovado-pedagogico.md",),
}

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
    "A113PrdWriter não executado" — e a interface, que só testa se a chave existe,
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
        "design/14-one-pager-pedagogico",
        "One-pager pedagógico",
        "Para leitura e aprovação do time pedagógico",
    ),
]


def documento_para_gravar(state: Dict[str, Any], chave: str) -> Any:
    """O valor que vai para o arquivo da chave. O pedagógico sai como gente o lê: o texto aprovado no de acordo de design
    e, no fim, a seção que o dev acrescenta (`tools.pedagogico.completo`, PR 10) — guardada à parte no estado, para o
    texto aprovado não mudar."""
    if chave == "one_pager_pedagogico":
        from tools.pedagogico import completo

        return completo(state)
    return state.get(chave)


#: `[texto](alvo)`: o link do Markdown, como `tools.markdown_blocos` o lê.
_RE_LINK_MD = re.compile(r"\[([^\]\n]+)\]\(([^)\s]+)\)")
#: Alvo que não é caminho a partir da raiz da sessão: com esquema (`https:`, `mailto:`), âncora, absoluto ou já relativo
#: à pasta de cima.
_RE_ALVO_FORA_DA_SESSAO = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|#|/|\.\./)")


def links_relativos_a_pasta(documento: str, base: str) -> str:
    """O documento com cada link para um artefato da sessão relativo à pasta do arquivo exportado (`base`).

    O redator cita os artefatos pelo caminho a partir da raiz da sessão (`design/08-prototipo.html`), e é contra a raiz
    que o A121 os confere (`caminhos_de_artefato`). Exportado em `design/14-one-pager-pedagogico.{html,docx}` (PR 10), o
    mesmo link abria `design/design/08-prototipo.html` — justamente o protótipo com que o time valida a missão (exp05ef1b;
    revisão do PR #79, 24/10/2026). Só o `.docx` e o `.html` mudam: o `.md` é o texto da esteira, e fica como está.
    Link que não aponta para artefato da sessão fica como está."""
    pasta = posixpath.dirname(base)
    if not pasta:
        return documento
    da_sessao = set(caminhos_de_artefato())
    pastas = {c.split("/", 1)[0] for c in da_sessao if "/" in c}

    def trocar(m: "re.Match[str]") -> str:
        alvo = m.group(2)
        if _RE_ALVO_FORA_DA_SESSAO.match(alvo):
            return m.group(0)
        caminho, sep, ancora = alvo.partition("#")
        caminho = posixpath.normpath(caminho) if caminho else caminho
        if not caminho or (caminho not in da_sessao and caminho.split("/", 1)[0] not in pastas):
            return m.group(0)
        return f"[{m.group(1)}]({posixpath.relpath(caminho, pasta)}{sep}{ancora})"

    return _RE_LINK_MD.sub(trocar, documento or "")


def migrar_caminhos_legados(run_dir: Path, gravados: List[str]) -> List[str]:
    """Apaga o arquivo de antes da mudança de pasta de cada chave cujo arquivo novo foi gravado agora — o conteúdo é o
    mesmo, da mesma chave. Devolve os caminhos apagados."""
    apagados: List[str] = []
    for chave, legados in CAMINHOS_LEGADOS.items():
        if chave not in gravados:
            continue
        for rel in legados:
            caminho = Path(run_dir) / rel
            if caminho.is_file():
                caminho.unlink()
                apagados.append(rel)
    return apagados


def caminhos_de_artefato() -> List[str]:
    """Todo caminho que uma sessão pode ter: o mapa acima e as exportações `.docx`/`.html` dos one-pagers.

    É contra esta lista que o PRD e o pedagógico conferem os caminhos que citam — os das 11 missões do
    bucket apontavam `spec/<slug>-spec.md` e `design/08-prototipo-navegavel.html`, que nunca existiram.
    """
    caminhos = [arquivo for _, arquivo in ARTIFACT_FILES]
    caminhos += [f"{base}{ext}" for _, base, _, _ in ONE_PAGERS_COM_MARCA for ext in (".docx", ".html")]
    return sorted(set(caminhos))


def exportar_one_pagers(state: Dict[str, Any], run_dir: Path, slug: str) -> List[Path]:
    """Grava cada one-pager em `.docx` e `.html` com a identidade visual da Unooria.

    Dois formatos porque são dois usos: o `.docx` abre no Word e no Google Docs para o
    time comentar e editar; o `.html` abre no navegador e vira PDF pelo "Imprimir", que
    é como a missão é apresentada para fora. O Markdown continua salvo do lado, porque é
    dele que os dois saem e é ele que a esteira lê.

    Falha aqui não derruba a execução: o documento em Markdown já está no disco, e o que
    se perde é a formatação, não o conteúdo.

    O pedagógico sai com imagens: a tela do Stitch debaixo de cada passo («Telas deste passo») e
    o desenho da jornada e do fluxo no fim do passo a passo (`tools.ilustracoes`). As imagens
    baixadas ficam em `.cache-imagens/`, na pasta da sessão — fora do manifesto —, e imagem que
    não vem vira legenda com o link: nunca derruba a exportação.
    """
    gerados: List[Path] = []
    for chave, base, etiqueta, subtitulo in ONE_PAGERS_COM_MARCA:
        documento = documento_para_gravar(state, chave)
        if not documento or not isinstance(documento, str) or e_mensagem_de_pulo(documento):
            continue

        # o .docx e o .html ficam na pasta de `base`; os links do texto são a partir da raiz da sessão
        exportado = links_relativos_a_pasta(documento, base)
        ilustracoes = None
        if chave == "one_pager_pedagogico":
            try:
                from tools.ilustracoes import PASTA_CACHE, montar_ilustracoes

                ilustracoes = montar_ilustracoes(state, documento, run_dir / PASTA_CACHE)
            except Exception as exc:
                logger.warning("O pedagógico sai sem as imagens das telas: %s", exc)

        destino_docx = run_dir / f"{base}.docx"
        try:
            from tools.docx_export import markdown_para_docx

            if markdown_para_docx(
                exportado, destino_docx, titulo_fallback=slug, etiqueta=etiqueta, subtitulo=subtitulo,
                ilustracoes=ilustracoes,
            ):
                gerados.append(destino_docx)
        except Exception as exc:
            logger.warning("Não consegui gerar o .docx de %s: %s", base, exc)

        destino_html = run_dir / f"{base}.html"
        try:
            from tools.onepager_html import markdown_para_html

            pagina = markdown_para_html(
                exportado, titulo_fallback=slug, etiqueta=etiqueta, subtitulo=subtitulo, ilustracoes=ilustracoes
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
    gravadas: List[str] = []
    for key, rel in ARTIFACT_FILES:
        value = documento_para_gravar(state, key)
        if not value or e_mensagem_de_pulo(value):
            continue
        path = run_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        text = value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False)
        path.write_text(desembrulhar_cerca(text).strip() + "\n", encoding="utf-8")
        written += 1
        gravadas.append(key)
    # a sessão gravada antes do PR 10 tinha o pedagógico na raiz: o de lá sai, para não ficar um de cada versão
    migrar_caminhos_legados(run_dir, gravadas)


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
