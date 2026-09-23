"""Reexecução de uma etapa sobre o estado salvo de uma sessão.

Cada mensagem no chat do gerador é uma missão nova: sessão ADK vazia, pasta nova, tudo do zero.
Este módulo é o que permite **corrigir** uma missão existente: carrega o `estado.json` da pasta,
descarta o que a etapa pedida (e as seguintes) produziram, injeta o pedido de correção numa chave
de estado que todo agente enxerga (`pedido_correcao`, ver `agents/base.py`) e deixa o runner
rodar só essas etapas na mesma pasta. Usado por `scripts/rerodar_etapa.py` (CLI) e pelo app.

Só a parte determinística vive aqui: o que apagar, como preservar a herança dos gates que não
foram refeitos, backup e merge do `conversa.json`. Nada de LLM.
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import time
from types import SimpleNamespace
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Iterable, List, Optional, Sequence, Tuple

from agents.callbacks import (
    KEY_AGENTES_DEGRADADOS,
    KEY_DEGRADACOES,
    KEY_HERANCA,
    KEY_PIPELINE_BLOQUEADO,
    KEY_PIPELINE_MOTIVO,
    texto_de_heranca,
)
from pipeline.artifacts import ARTIFACT_FILES

#: Chave de estado lida por todos os agentes (rodapé injetado em `agents/base.py`).
KEY_PEDIDO_CORRECAO = "pedido_correcao"

#: Etapas de onde uma correção pode recomeçar, na ordem da esteira. `transversal` refaz só
#: diagnóstico e aprendizado. `produto` entrou em 23/09/2026: sem ela, a triagem mandava para `spec`
#: pedidos de mecânica, etapas e narrativa — e a correção a partir da spec não refaz o one-pager nem
#: passa pelos gates de produto. A spec mudava, o one-pager do PO ficava como estava, e a mecânica
#: nova não era avaliada por ninguém.
ETAPAS = ("produto", "spec", "design", "dev", "transversal")

CHAVES_DEV = frozenset({
    "manifesto_report", "manifesto_status", "manifesto_status_envelope",
    "handoff_dev", "brief_assets", "handoff_rodada",
    "telemetria_report", "telemetria_status", "telemetria_status_envelope",
    "rastro_lacunas_report", "rastro_lacunas_status", "rastro_lacunas_status_envelope",
    "validacao_produto_narrativa", "validacao_design_imersao", "validacao_pedagogia_bncc",
    "validacao_dados_lgpd", "validacao_tecnica_arquitetura", "validacao_dev_report",
    "dev_status", "dev_status_envelope", "banca_rodada",
    "prd_final", "prd_check_report", "prd_status", "prd_status_envelope", "prd_rodada",
    "one_pager_pedagogico",
    # gate de KPI do PRD (23/09/2026): sem apagar, uma correção que caísse antes dele deixava
    # no dossiê o veredito da execução anterior como se fosse desta
    "kpis_report", "kpis_status", "kpis_status_envelope",
    "juiz_telemetria_saida",
})
#: `miro_board` fica de fora de propósito: o espelho atualiza o mesmo board em vez de abrir outro.
CHAVES_DESIGN = frozenset({
    "fechamento_lacunas", "relatorio_lacunas", "lacunas_status", "lacunas_status_envelope",
    "ambiente_simulado", "ambiente_status", "ambiente_status_envelope",
    "brief_oficio", "jornada_telas", "fluxo_arestas", "copy_strings", "camada_caa",
    "wireframes_cobertura", "copy_strings_revisada", "prototipo_html", "prototipo_arquivo",
    "prototipo_relatorio", "diagramas_html", "stitch_links", "miro_links",
    "qa_entregaveis_report", "design_status", "design_status_envelope", "qa_design_rodada",
    "prototipo_lint_report", "prototipo_lint_status", "prototipo_lint_status_envelope",
}) | CHAVES_DEV
#: `spec_missao_gate0` tem de cair: o split do D0 só grava esse backup se ele não existir
#: (`agents/checkers.py`, SecaoSplitAgent) — senão a spec velha seria preservada como "original".
CHAVES_SPEC = frozenset({
    "spec_missao", "spec_missao_gate0", "spec_rodada",
    "bncc_report", "bncc_status", "bncc_status_envelope",
    "one_pager_resumido",
    # gates da spec criados em 22–23/09/2026. `juiz_perguntas_rodada` é o que doía: sem apagar,
    # a correção começava com as rodadas do juiz já esgotadas e não havia rodada de correção.
    "evidencia_report", "evidencia_status", "evidencia_status_envelope",
    "perguntas_report", "perguntas_status", "perguntas_status_envelope",
    "juiz_perguntas_report", "juiz_perguntas_status", "juiz_perguntas_status_envelope",
    "juiz_perguntas_rodada", "juiz_evidencia_saida",
}) | CHAVES_DESIGN
#: Tudo que a etapa de produto grava. Ficam de fora, de propósito, o que ela LÊ da geração original:
#: `briefing`, `perguntas_po` e `material_anexado` — refazer produto é refazê-lo sobre o mesmo pedido
#: e o mesmo material, mais o pedido de correção.
CHAVES_PRODUTO = frozenset({
    "nucleo_narrativo", "micro_gate_report", "micro_gate_status", "micro_gate_status_envelope", "micro_gate_rodada",
    "missoes_vizinhas", "catalogo_indice_status", "catalogo_indice_status_envelope",
    "one_pager", "brief_escopo", "brief_escopo_status", "brief_escopo_status_envelope",
    "contrato_produto_report", "contrato_produto_status", "contrato_produto_status_envelope",
    "gate_estrutural_report", "gate_estrutural_status", "gate_estrutural_status_envelope", "gate_estrutural_rodada",
    "avaliacao_pedagogica_report", "avaliacao_status", "avaliacao_status_envelope",
    "experiencia_aluno_report", "experiencia_status", "experiencia_status_envelope",
    "adequacao_report", "adequacao_status", "adequacao_status_envelope", "avaliacoes_rodada",
    "gate_final_report", "gate_final_status", "gate_final_status_envelope",
    "juiz_contrato_produto_saida",
}) | CHAVES_SPEC
CHAVES_TRANSVERSAL = frozenset({
    "diagnostico_execucao", "diagnostico_status", "diagnostico_status_envelope", "aprendizado_registro",
})
#: Contadores da execução anterior. `reexecucoes` é o orçamento de retrabalho da banca: sem zerar,
#: uma sessão que já gastou o teto chega à correção sem direito a conserto.
#: `tickets_sem_rota` acumula: sem zerar, o dossiê da correção listaria pendências da execução velha.
CHAVES_EXECUCAO = frozenset({"reexecucoes", "tickets_retrabalho", "tickets_sem_rota", "juiz_achados_entrada",
                             KEY_AGENTES_DEGRADADOS})

CHAVES_POR_ETAPA: Dict[str, frozenset] = {
    "produto": CHAVES_PRODUTO,
    "spec": CHAVES_SPEC,
    "design": CHAVES_DESIGN,
    "dev": CHAVES_DEV,
    "transversal": frozenset(),
}
#: Uma spec nova invalida design e dev; um design novo invalida dev.
#: `transversal` passa uma etapa que o orquestrador não monta: sobram só diagnóstico e
#: aprendizado. Lista vazia não serve — o orquestrador a trocaria pelas etapas padrão.
ETAPA_PARA_STAGES: Dict[str, List[str]] = {
    "produto": ["produto", "design", "dev"],
    "spec": ["spec", "design", "dev"],
    "design": ["design", "dev"],
    "dev": ["dev"],
    "transversal": ["transversal"],
}

#: Rótulo (`rotulo=`) de cada gate → etapa que o produz. Serve para a herança: uma correção de
#: dev preserva a reprovação de um gate de produto (a base continua como estava) e descarta a
#: dos gates de dev, que vão ser recomputados. Rótulo desconhecido é descartado.
ROTULOS_GATE_POR_ETAPA: Dict[str, str] = {
    "Micro-gate do núcleo": "produto",
    "Contrato de plataforma e origem dos parâmetros": "produto",
    "Gate estrutural": "produto",
    "Adequação pedagógica": "produto",
    "Avaliação pedagógica": "produto",
    "Experiência do estudante": "produto",
    "Gate final de produto": "produto",
    "Conformidade BNCC Computação": "spec",
    "Ficha do manifesto (produto)": "spec",
    "Matriz de evidência pedagógica": "spec",
    "Perguntas de produto (9f)": "spec",
    "Juiz das perguntas de produto": "spec",
    "Spec da missão": "spec",
    "Fechamento de lacunas (D0)": "design",
    "Ambiente simulado (D9)": "design",
    "QA de entregáveis (design)": "design",
    "Retrabalho de design": "design",
    "Ficha do manifesto": "dev",
    "Contrato de telemetria e arquitetura": "dev",
    "Handoff de dev": "dev",
    "Rastro de lacunas antes do PRD": "dev",
    "Banca de dev": "dev",
    "Retrabalho da banca": "dev",
    "Pendências e consistência do PRD": "dev",
    "Coerência KPI ↔ evento ↔ tela": "dev",
    "Consistência do PRD": "dev",
}
_ETAPAS_REFEITAS: Dict[str, frozenset] = {
    "produto": frozenset({"produto", "spec", "design", "dev"}),
    "spec": frozenset({"spec", "design", "dev"}),
    "design": frozenset({"design", "dev"}),
    "dev": frozenset({"dev"}),
    "transversal": frozenset(),
}

#: Arquivos da raiz copiados para o backup antes de qualquer sobrescrita.
ARQUIVOS_DE_BACKUP = (
    "estado.json", "conversa.json", "manifesto-artefatos.json",
    "diagnostico-execucao.md", "aprendizado.md",
)
PASTA_CORRECOES = ".correcoes"


# ------------------------------------------------------------------ pedido de correção
@dataclass
class PedidoCorrecao:
    """O que a pessoa pediu, mais o material que anexou, já em texto."""

    texto: str
    #: (nome do arquivo, conteúdo em markdown) — DOCX, MD, TXT e PDF com texto extraído.
    anexos: List[Tuple[str, str]] = field(default_factory=list)
    #: Anexos cujo texto não pôde ser extraído (PDF digitalizado, por exemplo).
    anexos_sem_texto: List[str] = field(default_factory=list)

    @classmethod
    def de_doc_batch(cls, texto: str, doc_batch: Any) -> "PedidoCorrecao":
        pedido = cls(texto=texto)
        for doc in (getattr(doc_batch, "documents", None) or []):
            conteudo = (getattr(doc, "markdown_text", None) or "").strip()
            if conteudo:
                pedido.anexos.append((doc.name, conteudo))
            else:
                pedido.anexos_sem_texto.append(doc.name)
        return pedido

    def como_material(self) -> str:
        """Os anexos do pedido no formato de `material_anexado` — para refazer produto numa sessão
        antiga, que não guardou o material da geração original."""
        blocos = [f"### 📄 Documento de apoio: {nome}\n\n{conteudo.strip()}" for nome, conteudo in self.anexos]
        blocos += [f"### 📄 {nome} — anexado, mas sem texto extraível; considere só o que o pedido diz sobre ele."
                   for nome in self.anexos_sem_texto]
        return "\n\n".join(blocos)

    def como_markdown(self, etapa: str) -> str:
        """Valor de `state["pedido_correcao"]`: pedido, anexos e como agir."""
        seguintes = {"produto": " (e a spec, o design e o dev, que derivam dele)",
                     "spec": " (e design e dev, que derivam dela)", "design": " (e dev, que deriva dele)"}.get(etapa, "")
        linhas = [
            f"Esta execução refaz a etapa `{etapa}`{seguintes} de uma missão já gerada, a pedido de uma pessoa. "
            "Os documentos das etapas anteriores foram preservados e são seus insumos; os da sua etapa foram "
            "descartados e você os escreve de novo.",
            "",
            "### Pedido, na íntegra",
            "",
        ]
        linhas += [f"> {l}" if l.strip() else ">" for l in self.texto.strip().splitlines()] or ["> (vazio)"]
        linhas += ["", "### Material anexado ao pedido", ""]
        if not self.anexos and not self.anexos_sem_texto:
            linhas.append("Nenhum.")
        for nome, conteudo in self.anexos:
            linhas += [f"#### 📄 {nome}", "", conteudo.strip(), ""]
        for nome in self.anexos_sem_texto:
            linhas.append(f"#### 📄 {nome} — anexado, mas sem texto extraível; considere só o que o pedido diz sobre ele.")
        linhas += [
            "",
            "### Como agir",
            "",
            "1. Aplique o pedido **no que é seu** — no documento que você produz. Se o pedido não toca o seu "
            "documento, refaça-o normalmente a partir dos insumos, que podem ter mudado.",
            "2. Não invente o resto nem amplie o escopo: o que não foi pedido continua como estava.",
            "3. Registre no seu documento, numa seção curta **\"O que mudou nesta versão\"** (ou no changelog, se o "
            "formato já tiver um), o que você alterou por causa do pedido — ou \"nada: o pedido não toca este documento\".",
        ]
        return "\n".join(linhas)


@dataclass
class RegistroCorrecao:
    """Uma entrada de `conversa.json["historico_correcoes"]`."""

    quando: str
    etapa: str
    stages: List[str]
    pedido: str
    status: str
    anexos: List[str] = field(default_factory=list)
    triagem: Dict[str, Any] = field(default_factory=dict)
    duracao_s: float = 0.0
    chaves_removidas: List[str] = field(default_factory=list)
    backup: str = ""
    #: O que a triagem sugeriu, para medir quantas vezes a pessoa troca a etapa.
    etapa_sugerida: str = ""
    #: Preenchido quando a correção foi desfeita (`desfazer_correcao`).
    desfeita_em: str = ""


# ------------------------------------------------------------------ estado
def material_para_refazer_produto(
    estado: Dict[str, Any], conversa: Dict[str, Any], pedido: Optional[PedidoCorrecao]
) -> Tuple[Optional[str], Optional[str]]:
    """`(material, recusa)` para refazer produto. Exatamente um dos dois vem preenchido.

    O núcleo narrativo é construído a partir dos anexos, e até 23/09/2026 a sessão guardava só os
    nomes deles. Refazer produto numa sessão dessas sem o material seria gerar outra missão, sem o
    material do Entre Redes que definiu esta — pior que não corrigir. Então: o material guardado
    vence; sem ele, vale o que o pedido anexou; sem nenhum dos dois, e se a geração original teve
    anexos, a correção é recusada com o que fazer.
    """
    salvo = str(estado.get("material_anexado") or "").strip()
    if salvo:
        return salvo, None
    if pedido and (pedido.anexos or pedido.anexos_sem_texto):
        return pedido.como_material(), None
    originais = [str(n) for n in (conversa.get("attached_files") or [])]
    if not originais:
        return "", None
    return None, (
        "esta missão foi gerada antes de a esteira guardar o conteúdo dos anexos, e refazer a etapa de "
        "produto sem eles geraria outra missão. Anexe de novo ao pedido o material original ("
        + ", ".join(f"`{n}`" for n in originais[:6]) + ("…" if len(originais) > 6 else "") + ") e reenvie."
    )


def _etapa_do_gate(rotulo: str) -> Optional[str]:
    return ROTULOS_GATE_POR_ETAPA.get(str(rotulo or "").strip())


def recalcular_heranca(estado: Dict[str, Any], etapa: str) -> Dict[str, Any]:
    """Mantém só as reprovações de gates que NÃO serão refeitos e reescreve as marcas derivadas.

    Apagar `degradacoes` inteira (o que o script fazia) escondia uma reprovação real de produto
    numa correção de dev: o dev construiria sobre base reprovada sem marcar `[PROVISÓRIO]`.
    """
    refeitas = _ETAPAS_REFEITAS.get(etapa, frozenset())
    anteriores = [d for d in (estado.get(KEY_DEGRADACOES) or []) if isinstance(d, dict)]
    restantes = [d for d in anteriores if (_etapa_do_gate(d.get("gate")) or "?") not in refeitas | {"?"}]
    novo = dict(estado)
    novo[KEY_DEGRADACOES] = restantes
    novo[KEY_HERANCA] = texto_de_heranca(restantes)
    novo[KEY_PIPELINE_BLOQUEADO] = bool(restantes)
    novo[KEY_PIPELINE_MOTIVO] = str(restantes[0].get("motivo") or "") if restantes else ""
    return novo


def preparar_estado(
    estado: Dict[str, Any], etapa: str, pedido_md: Optional[str] = None
) -> Tuple[Dict[str, Any], List[str]]:
    """Estado pronto para reexecutar `etapa`: sem o que ela produz, com herança recalculada e o pedido.

    Pura, sem I/O. Devolve `(estado_limpo, chaves_removidas)`.
    """
    if etapa not in CHAVES_POR_ETAPA:
        raise ValueError(f"etapa inválida: {etapa!r} (esperado uma de {ETAPAS})")
    remover = CHAVES_POR_ETAPA[etapa] | CHAVES_TRANSVERSAL | CHAVES_EXECUCAO | {KEY_PEDIDO_CORRECAO}
    removidas = sorted(k for k in estado if k in remover)
    limpo = {k: v for k, v in estado.items() if k not in remover and not str(k).startswith("temp:")}
    if etapa == "design" and limpo.get("spec_missao_gate0"):
        # o D0 consolida a spec por cima de `spec_missao`; para refazer o design, volta à do Gate 0
        limpo["spec_missao"] = limpo["spec_missao_gate0"]
    if etapa == "transversal":
        # só diagnóstico e aprendizado: a herança descreve a execução que está sendo diagnosticada
        pass
    else:
        limpo = recalcular_heranca(limpo, etapa)
    if pedido_md:
        limpo[KEY_PEDIDO_CORRECAO] = pedido_md
    return limpo, removidas


# ------------------------------------------------------------------ arquivos e backup
def arquivos_das_chaves(chaves: Iterable[str]) -> List[str]:
    """Caminhos relativos (na pasta da sessão) dos artefatos que essas chaves geram.

    Inclui os irmãos exportados com a marca (`.docx`/`.html` do mesmo nome), que não estão em
    `ARTIFACT_FILES` mas nascem da mesma chave.
    """
    chaves = set(chaves)
    caminhos: List[str] = []
    for chave, rel in ARTIFACT_FILES:
        if chave not in chaves:
            continue
        caminhos.append(rel)
        base = rel.rsplit(".", 1)[0]
        for ext in (".docx", ".html"):
            irmao = base + ext
            if irmao != rel and irmao not in caminhos:
                caminhos.append(irmao)
    return caminhos


def fazer_backup(run_dir: Path, etapa: str, removidas: Sequence[str]) -> Path:
    """Guarda em `.correcoes/<data>-<etapa>/` o que a reexecução vai sobrescrever ou descartar.

    Copia os arquivos da raiz e **move** os artefatos das chaves removidas — assim não sobra
    artefato órfão de uma versão anterior ao lado dos novos. Pasta oculta: fora do manifesto e do ZIP.
    """
    run_dir = Path(run_dir)
    destino = run_dir / PASTA_CORRECOES / f"{time.strftime('%Y%m%d-%H%M%S')}-{etapa}"
    destino.mkdir(parents=True, exist_ok=True)
    for nome in ARQUIVOS_DE_BACKUP:
        origem = run_dir / nome
        if origem.is_file():
            shutil.copy2(origem, destino / nome)
    for rel in arquivos_das_chaves(removidas):
        origem = run_dir / rel
        if origem.is_file():
            alvo = destino / rel
            alvo.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(origem), str(alvo))
    return destino


def restaurar_backup(run_dir: Path, backup: Path) -> List[str]:
    """Devolve à sessão tudo que está no backup (sobrescrevendo). Retorna os caminhos restaurados."""
    run_dir, backup = Path(run_dir), Path(backup)
    restaurados: List[str] = []
    for arquivo in sorted(p for p in backup.rglob("*") if p.is_file()):
        rel = arquivo.relative_to(backup)
        alvo = run_dir / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(arquivo, alvo)
        restaurados.append(rel.as_posix())
    return restaurados


def carregar_sessao(run_dir: Path) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    """`(estado, conversa, briefing)` lidos da pasta da sessão."""
    run_dir = Path(run_dir)
    estado = json.loads((run_dir / "estado.json").read_text(encoding="utf-8"))
    conversa: Dict[str, Any] = {}
    if (run_dir / "conversa.json").exists():
        conversa = json.loads((run_dir / "conversa.json").read_text(encoding="utf-8"))
    briefing = str(estado.get("briefing") or "")
    if not briefing and (run_dir / "briefing-original.md").exists():
        briefing = (run_dir / "briefing-original.md").read_text(encoding="utf-8")
    return estado, conversa, briefing


# ------------------------------------------------------------------ conversa
def historico_de(conversa: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Histórico de correções, aceitando o nome antigo (`reexecucoes`, lista) do script."""
    atual = conversa.get("historico_correcoes")
    if isinstance(atual, list):
        return list(atual)
    legado = conversa.get("reexecucoes")
    return list(legado) if isinstance(legado, list) else []


def mensagem_de_correcao(registro: RegistroCorrecao) -> str:
    icone = {"success": "🟢", "bypassed": "🟡", "blocked": "🔴", "error": "❌"}.get(registro.status, "⚪")
    de_onde = "só diagnóstico e aprendizado" if registro.etapa == "transversal" else f"**{registro.etapa}**"
    motivo = registro.triagem.get("motivo") if isinstance(registro.triagem, dict) else ""
    return (
        f"🔧 **Correção aplicada em {registro.quando}** — a esteira recomeçou de {de_onde}"
        + (f" ({motivo})" if motivo else "")
        + f". Status: {icone} {registro.status}. "
        "Veja as abas abaixo; o que mudou está na seção \"O que mudou nesta versão\" de cada documento refeito."
    )


def mesclar_conversa(
    run_dir: Path,
    conversa_anterior: Dict[str, Any],
    result: Any,
    registro: RegistroCorrecao,
    mensagens_novas: Sequence[Dict[str, Any]],
) -> Path:
    """Regrava `conversa.json` preservando data, histórico e mensagens anteriores.

    O runner grava o arquivo do zero com duas mensagens; aqui ele é reescrito por cima com o que
    a correção não pode perder.
    """
    from pipeline.session_store import save_session_record

    mensagens = list(conversa_anterior.get("messages") or []) + list(mensagens_novas)
    return save_session_record(
        run_dir=Path(run_dir),
        session_id=str(conversa_anterior.get("session_id") or getattr(result, "session_id", "") or ""),
        user_id=str(conversa_anterior.get("user_id") or getattr(result, "user_id", "") or ""),
        prompt=str(conversa_anterior.get("prompt") or getattr(result, "prompt", "") or ""),
        result=result,
        messages=mensagens,
        attached_files=list(conversa_anterior.get("attached_files") or []),
        created_at=conversa_anterior.get("created_at"),
        historico_correcoes=historico_de(conversa_anterior) + [asdict(registro)],
    )


# ------------------------------------------------------------------ execução
def _stages_de(etapa: str, so_esta_etapa: bool) -> List[str]:
    if etapa == "transversal":
        return ETAPA_PARA_STAGES["transversal"]
    return [etapa] if so_esta_etapa else list(ETAPA_PARA_STAGES[etapa])


def _triagem_como_dict(triagem: Any) -> Dict[str, Any]:
    if triagem is None:
        return {}
    if isinstance(triagem, dict):
        return dict(triagem)
    try:
        return asdict(triagem)
    except TypeError:
        return {"bruto": str(triagem)}


async def executar_correcao_stream(
    run_dir: Path,
    etapa: str,
    pedido: Optional[PedidoCorrecao] = None,
    triagem: Any = None,
    *,
    so_esta_etapa: bool = False,
    **opcoes_runner: Any,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Reexecuta `etapa` (e as seguintes) sobre a sessão em `run_dir`, gravando na mesma pasta.

    Emite `correcao_started`, repassa os eventos do runner e fecha com `correcao_completed`
    (`result` + `registro`) ou `correcao_error` (backup restaurado). `opcoes_runner` vai para
    `run_orchestrator_pipeline_stream` (thinking_budget, include_thoughts, modo_estrito…).
    """
    from pipeline.runner import run_orchestrator_pipeline_stream

    run_dir = Path(run_dir)
    estado, conversa, briefing = carregar_sessao(run_dir)
    if etapa == "produto":
        material, recusa = material_para_refazer_produto(estado, conversa, pedido)
        if recusa:
            # nada foi tocado ainda: sem backup, sem estado limpo, sem registro de correção
            yield {"type": "correcao_error", "error": recusa, "registro": None, "restaurados": [], "timestamp": time.time()}
            return
        estado = {**estado, "material_anexado": material}
    tem_pedido = bool(pedido and (pedido.texto.strip() or pedido.anexos or pedido.anexos_sem_texto))
    pedido_md = pedido.como_markdown(etapa) if tem_pedido else None
    limpo, removidas = preparar_estado(estado, etapa, pedido_md)
    backup = fazer_backup(run_dir, etapa, removidas)
    stages = _stages_de(etapa, so_esta_etapa)
    inicio = time.time()
    quando = time.strftime("%d/%m/%Y %H:%M:%S")
    yield {
        "type": "correcao_started", "etapa": etapa, "stages": stages,
        "backup": backup.relative_to(run_dir).as_posix(), "chaves_removidas": removidas, "timestamp": inicio,
    }

    result: Any = None
    erro: Optional[Dict[str, Any]] = None
    async for evento in run_orchestrator_pipeline_stream(
        prompt=briefing,
        user_id=conversa.get("user_id"),
        session_id=conversa.get("session_id"),
        stages=stages,
        initial_state=limpo,
        run_dir=run_dir,
        registrar_conversa=False,
        **opcoes_runner,
    ):
        tipo = evento.get("type")
        if tipo == "pipeline_completed":
            result = evento.get("result")
        elif tipo == "pipeline_error":
            erro = evento
        yield evento

    registro = RegistroCorrecao(
        quando=quando,
        etapa=etapa,
        stages=stages,
        pedido=pedido.texto if pedido else "",
        status=str(getattr(result, "status", "") or "error"),
        anexos=([n for n, _ in pedido.anexos] + list(pedido.anexos_sem_texto)) if pedido else [],
        triagem=_triagem_como_dict(triagem),
        duracao_s=round(time.time() - inicio, 1),
        chaves_removidas=removidas,
        backup=backup.relative_to(run_dir).as_posix(),
        etapa_sugerida=str(_triagem_como_dict(triagem).get("etapa") or ""),
    )
    mensagens: List[Dict[str, Any]] = []
    if tem_pedido and pedido and pedido.texto.strip():
        mensagens.append({"role": "user", "content": pedido.texto.strip()})

    if result is None:
        restaurados = restaurar_backup(run_dir, backup)
        registro.status = "error"
        detalhe = (erro or {}).get("error") or "o runner terminou sem resultado"
        mensagens.append({"role": "assistant", "content": f"❌ **Correção não aplicada:** {detalhe}. A sessão voltou ao estado anterior."})
        falso_result = SimpleNamespace(status="error", state={}, gates={}, duration_seconds=registro.duracao_s,
                                       attached_files=[], step_thoughts={}, session_id=conversa.get("session_id", ""),
                                       user_id=conversa.get("user_id", ""), prompt=briefing)
        mesclar_conversa(run_dir, conversa, falso_result, registro, mensagens)
        yield {"type": "correcao_error", "error": detalhe, "registro": asdict(registro), "restaurados": restaurados, "timestamp": time.time()}
        return

    mensagens.append({"role": "assistant", "content": mensagem_de_correcao(registro), "pipeline_result": result})
    mesclar_conversa(run_dir, conversa, result, registro, mensagens)
    yield {"type": "correcao_completed", "result": result, "registro": asdict(registro), "timestamp": time.time()}


def executar_correcao_sync(run_dir: Path, etapa: str, pedido: Optional[PedidoCorrecao] = None,
                           triagem: Any = None, **kwargs: Any) -> Tuple[Any, Dict[str, Any]]:
    """`(result | None, registro)` — para a linha de comando."""

    async def _rodar() -> Tuple[Any, Dict[str, Any]]:
        result, registro = None, {}
        async for evento in executar_correcao_stream(run_dir, etapa, pedido, triagem, **kwargs):
            if evento["type"] == "correcao_completed":
                result, registro = evento["result"], evento["registro"]
            elif evento["type"] == "correcao_error":
                registro = evento["registro"]
        return result, registro

    return asyncio.run(_rodar())


# ------------------------------------------------------------------ triagem
ETAPAS_DE_TRIAGEM = ("produto", "spec", "design", "dev", "nenhuma")


@dataclass
class Triagem:
    """Decisão do agente de triagem sobre um pedido de correção."""

    etapa: str                      # spec | design | dev | nenhuma | indefinida
    motivo: str = ""
    resumo_pedido: str = ""
    resumo_anexos: str = ""
    confianca: str = ""
    bruto: str = ""

    @property
    def confiavel(self) -> bool:
        return self.etapa in ETAPAS_DE_TRIAGEM

    @property
    def reexecuta(self) -> bool:
        return self.etapa in ETAPA_PARA_STAGES and self.etapa != "transversal"

    @classmethod
    def de_texto(cls, texto: str) -> "Triagem":
        """Lê o último bloco ```json``` da resposta; sem `etapa` válida, `etapa="indefinida"`.

        Não passa por `extrair_envelope`: aquele exige `status`/`veredito`, vocabulário de gate,
        e a triagem não é gate — ela não aprova nem reprova nada.
        """
        from agents.callbacks import _JSON_BLOCK_RE

        envelope: Dict[str, Any] = {}
        for bruto in reversed(_JSON_BLOCK_RE.findall(texto or "")):
            try:
                dados = json.loads(bruto)
            except json.JSONDecodeError:
                continue
            if isinstance(dados, dict) and "etapa" in dados:
                envelope = dados
                break
        etapa = str(envelope.get("etapa") or "").strip().lower()
        if etapa not in ETAPAS_DE_TRIAGEM:
            return cls(etapa="indefinida", motivo="a triagem não devolveu uma etapa válida", bruto=texto or "")
        return cls(
            etapa=etapa,
            motivo=str(envelope.get("motivo") or "").strip(),
            resumo_pedido=str(envelope.get("resumo_pedido") or "").strip(),
            resumo_anexos=str(envelope.get("resumo_anexos") or "").strip(),
            confianca=str(envelope.get("confianca") or "").strip().lower(),
            bruto=texto or "",
        )


def montar_mapa_da_missao(estado: Dict[str, Any]) -> str:
    """O que a triagem precisa saber da missão sem ler os documentos inteiros."""
    from pipeline.artifacts import extrair_slug
    from pipeline.runner import STATUS_KEYS

    spec = str(estado.get("spec_missao") or "")
    linhas = [f"- **Missão:** `{extrair_slug(spec or str(estado.get('one_pager') or '')) or '?'}`"]
    etapas = []
    if estado.get("one_pager"):
        etapas.append("produto (one-pager)")
    if spec:
        etapas.append("spec")
    if estado.get("jornada_telas") or estado.get("wireframes_cobertura"):
        etapas.append("design")
    if estado.get("handoff_dev") or estado.get("prd_final"):
        etapas.append("dev" + (" (com PRD)" if estado.get("prd_final") else ""))
    linhas.append(f"- **Etapas existentes:** {', '.join(etapas) or 'nenhuma'}")
    gates = [f"{k.replace('_status', '')}={estado[k]}" for k in STATUS_KEYS if k in estado and str(k).endswith("_status")]
    if gates:
        linhas.append(f"- **Gates:** {' · '.join(gates)}")
    cabecalhos = re.findall(r"^#{1,3}\s+(.+)$", spec, flags=re.MULTILINE)[:40]
    if cabecalhos:
        linhas.append("- **Estrutura da spec:** " + " · ".join(c.strip() for c in cabecalhos))
    docs_design = [k for k in ("brief_oficio", "jornada_telas", "fluxo_arestas", "copy_strings_revisada", "wireframes_cobertura", "prototipo_html", "camada_caa") if estado.get(k)]
    if docs_design:
        linhas.append("- **Documentos de design:** " + ", ".join(docs_design))
    docs_dev = [k for k in ("handoff_dev", "brief_assets", "validacao_dev_report", "prd_final", "one_pager_pedagogico") if estado.get(k)]
    if docs_dev:
        linhas.append("- **Documentos de dev:** " + ", ".join(docs_dev))
    return "\n".join(linhas)


async def triar_pedido(
    pedido: PedidoCorrecao, doc_batch: Any, estado: Dict[str, Any], *, thinking_budget: Optional[int] = 1024
) -> Triagem:
    """Roda o agente de triagem num runner mínimo, fora da esteira. Falha vira `indefinida`."""
    try:
        from google.adk.runners import InMemoryRunner

        from agents.transversal import get_triagem_correcao_agent
        from pipeline.runner import build_user_message

        app = "TriagemCorrecao"
        runner = InMemoryRunner(agent=get_triagem_correcao_agent(thinking_budget=thinking_budget), app_name=app)
        sessao = await runner.session_service.create_session(
            app_name=app, user_id="triagem",
            state={"briefing": str(estado.get("briefing") or ""), "mapa_da_missao": montar_mapa_da_missao(estado)},
        )
        async for _ in runner.run_async(user_id="triagem", session_id=sessao.id, new_message=build_user_message(pedido.texto, doc_batch)):
            pass
        final = await runner.session_service.get_session(app_name=app, user_id="triagem", session_id=sessao.id)
        return Triagem.de_texto(str((final.state if final else {}).get("triagem_correcao") or ""))
    except Exception as exc:  # pragma: no cover - rede/modelo
        return Triagem(etapa="indefinida", motivo=f"falha na triagem: {exc}")


def triar_pedido_sync(pedido: PedidoCorrecao, doc_batch: Any, estado: Dict[str, Any], **kwargs: Any) -> Triagem:
    return asyncio.run(triar_pedido(pedido, doc_batch, estado, **kwargs))


# ------------------------------------------------------------------ desfazer
def correcao_desfazivel(conversa: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """A última correção, se ainda pode ser desfeita: tem backup e não foi desfeita."""
    historico = historico_de(conversa)
    if not historico:
        return None
    ultima = historico[-1]
    if ultima.get("status") == "desfeita" or ultima.get("desfeita_em") or not ultima.get("backup"):
        return None
    return ultima


def desfazer_correcao(run_dir: Path) -> Optional[Dict[str, Any]]:
    """Devolve a sessão ao estado anterior à última correção e registra o desfazer.

    Restaura tudo que está em `.correcoes/<backup>/` — inclusive o `conversa.json` daquela hora,
    que já traz o histórico e as mensagens de antes — e acrescenta por cima a mensagem e a
    entrada de histórico do desfazer. Devolve a entrada desfeita, ou None se não havia o quê.
    """
    run_dir = Path(run_dir)
    if not (run_dir / "conversa.json").exists():
        return None
    conversa = json.loads((run_dir / "conversa.json").read_text(encoding="utf-8"))
    ultima = correcao_desfazivel(conversa)
    if not ultima:
        return None
    backup = run_dir / str(ultima["backup"])
    if not backup.is_dir():
        return None
    restaurar_backup(run_dir, backup)

    restaurada = json.loads((run_dir / "conversa.json").read_text(encoding="utf-8")) if (run_dir / "conversa.json").exists() else {}
    estado = json.loads((run_dir / "estado.json").read_text(encoding="utf-8")) if (run_dir / "estado.json").exists() else {}
    agora = time.strftime("%d/%m/%Y %H:%M:%S")
    registro = dict(ultima)
    registro.update({"status": "desfeita", "desfeita_em": agora})
    mensagem = (
        f"↩️ **Correção de {ultima.get('quando', '?')} desfeita em {agora}** — a sessão voltou ao estado "
        f"anterior (recomeço de `{ultima.get('etapa', '?')}`" + (f", pedido: {ultima['pedido']}" if ultima.get("pedido") else "") + ")."
    )
    falso_result = SimpleNamespace(
        status=str(restaurada.get("status") or "success"), state=estado, gates=restaurada.get("gates") or {},
        duration_seconds=restaurada.get("duration_seconds", 0.0), attached_files=restaurada.get("attached_files") or [],
        step_thoughts=restaurada.get("step_thoughts") or {}, session_id=restaurada.get("session_id", ""),
        user_id=restaurada.get("user_id", ""), prompt=restaurada.get("prompt", ""),
    )
    from pipeline.session_store import save_session_record

    save_session_record(
        run_dir=run_dir,
        session_id=str(restaurada.get("session_id") or conversa.get("session_id") or ""),
        user_id=str(restaurada.get("user_id") or conversa.get("user_id") or ""),
        prompt=str(restaurada.get("prompt") or conversa.get("prompt") or ""),
        result=falso_result,
        messages=list(restaurada.get("messages") or []) + [{"role": "assistant", "content": mensagem}],
        attached_files=list(restaurada.get("attached_files") or []),
        created_at=restaurada.get("created_at") or conversa.get("created_at"),
        historico_correcoes=historico_de(restaurada) + [registro],
    )
    return registro
