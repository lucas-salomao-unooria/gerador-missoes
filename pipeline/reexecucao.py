"""Reexecução de uma etapa sobre o estado salvo de uma sessão.

Cada mensagem no chat do gerador é uma missão nova: sessão ADK vazia, pasta nova, tudo do zero.
Este módulo é o que permite **corrigir** uma missão existente: carrega o `estado.json` da pasta,
descarta o que a etapa pedida (e as seguintes) produziram — guardando cada documento autoral como
base em `anterior_<chave>`, para o autor editar em vez de reescrever —, injeta o pedido de correção
numa chave de estado que todo agente enxerga (`pedido_correcao`, ver `agents/base.py`) e deixa o
runner rodar só essas etapas na mesma pasta. Usado por `scripts/rerodar_etapa.py` (CLI) e pelo app.

Só a parte determinística vive aqui: o que apagar, como preservar a herança dos gates que não
foram refeitos, backup e merge do `conversa.json`. Nada de LLM.
"""

from __future__ import annotations

import asyncio
import json
import logging
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

logger = logging.getLogger(__name__)

#: Chave de estado lida por todos os agentes (rodapé injetado em `agents/base.py`).
KEY_PEDIDO_CORRECAO = "pedido_correcao"
#: Pareceres humanos das etapas já liberadas (`pipeline/passagem.py`), no mesmo rodapé.
KEY_NOTAS_DE_PASSAGEM = "notas_de_passagem"
#: Todos os pedidos de refazer do PO, de todas as etapas (`pipeline/passagem.py::pedidos_do_po`). É o
#: que o verificador de fidelidade confere; o `pedido_correcao` só traz o da execução corrente.
KEY_PEDIDOS_DO_PO = "pedidos_do_po"


def _pedidos_do_po(conversa: Dict[str, Any]) -> List[Dict[str, str]]:
    from pipeline.passagem import fluxo_de, pedidos_do_po

    return pedidos_do_po(fluxo_de(conversa or {}))

#: Etapas de onde uma correção pode recomeçar, na ordem da esteira. `transversal` refaz só
#: diagnóstico e aprendizado. `produto` entrou em 23/09/2026: sem ela, a triagem mandava para `spec`
#: pedidos de mecânica, etapas e narrativa — e a correção a partir da spec não refaz o one-pager nem
#: passa pelos gates de produto. A spec mudava, o one-pager do PO ficava como estava, e a mecânica
#: nova não era avaliada por ninguém.
ETAPAS = ("produto", "spec", "design", "dev", "transversal")

CHAVES_DEV = frozenset({
    "manifesto_report", "manifesto_status", "manifesto_status_envelope",
    "handoff_dev", "brief_assets", "handoff_rodada",
    "banco_conteudo", "conteudo_report", "conteudo_status", "conteudo_status_envelope", "banco_rodada",
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
    # PRD e pedagógico × one-pager aprovado (06/10/2026)
    "conteudo_aprovado_prd_report", "conteudo_aprovado_prd_status", "conteudo_aprovado_prd_status_envelope",
    "conteudo_aprovado_pedagogico_report", "conteudo_aprovado_pedagogico_status",
    "conteudo_aprovado_pedagogico_status_envelope", "pedagogico_rodada",
    "juiz_telemetria_saida",
    # o refazer de dev conferido nos documentos de dev (07/10/2026)
    "fidelidade_dev_report", "fidelidade_dev_status", "fidelidade_dev_status_envelope", "juiz_fidelidade_dev_saida", "interpretacao_fidelidade_dev_saida",
    # a matriz final, com chave própria para entrar no semáforo de dev (07/10/2026)
    "rastreabilidade_dev_report", "rastreabilidade_dev_status", "rastreabilidade_dev_status_envelope",
    # o corpo do PRD × conteúdo aprovado, pelo juiz de contradições (08/10/2026)
    "coerencia_prd_report", "coerencia_prd_status", "coerencia_prd_status_envelope", "juiz_coerencia_prd_saida",
    "coerencia_pedagogico_report", "coerencia_pedagogico_status", "coerencia_pedagogico_status_envelope",
    "juiz_coerencia_pedagogico_saida",
    # a banca de entrada do dev, segunda verificação de produto e design (08/10/2026)
    "banca_entrada_narrativa", "banca_entrada_imersao", "banca_entrada_pedagogia",
    "banca_entrada_report", "banca_entrada_status", "banca_entrada_status_envelope",
})
#: `miro_board` fica de fora de propósito: o espelho atualiza o mesmo board em vez de abrir outro.
CHAVES_DESIGN = frozenset({
    "conteudo_aprovado",
    "fechamento_lacunas", "relatorio_lacunas", "lacunas_status", "lacunas_status_envelope",
    "ambiente_simulado", "ambiente_status", "ambiente_status_envelope", "base_preservada_spec_missao",
    "brief_oficio", "jornada_telas", "fluxo_arestas", "copy_strings", "camada_caa",
    "wireframes_cobertura", "copy_strings_revisada", "prototipo_html", "prototipo_arquivo",
    "prototipo_relatorio", "diagramas_html", "stitch_links", "miro_links",
    "qa_entregaveis_report", "design_status", "design_status_envelope", "qa_design_rodada",
    "prototipo_lint_report", "prototipo_lint_status", "prototipo_lint_status_envelope",
    "rastro_design_report", "rastro_design_status", "rastro_design_status_envelope",
    "consistencia_report", "consistencia_status", "consistencia_status_envelope",
    "cobertura_telas_report", "cobertura_telas_status", "cobertura_telas_status_envelope",
    "rastreabilidade_report", "rastreabilidade_status", "rastreabilidade_status_envelope",
    "stitch_status", "stitch_status_envelope",
    "qa_afirmacoes_report", "qa_afirmacoes_status", "qa_afirmacoes_status_envelope",
    # o refazer de design conferido nos documentos de design (07/10/2026)
    "fidelidade_design_report", "fidelidade_design_status", "fidelidade_design_status_envelope",
    "juiz_fidelidade_design_saida", "interpretacao_fidelidade_design_saida",
    # a spec consolidada pelo D0/D9 × one-pager aprovado (07/10/2026)
    "conteudo_aprovado_spec_design_report", "conteudo_aprovado_spec_design_status",
    "conteudo_aprovado_spec_design_status_envelope",
    # a banca no fim de design (08/10/2026)
    "banca_design_narrativa", "banca_design_imersao",
    "banca_design_report", "banca_design_status", "banca_design_status_envelope",
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
    # a fidelidade final roda também na correção a partir da spec
    "fidelidade_report", "fidelidade_status", "fidelidade_status_envelope", "juiz_fidelidade_saida",
    "interpretacao_fidelidade_saida",
    "juiz_perguntas_report", "juiz_perguntas_status", "juiz_perguntas_status_envelope",
    "juiz_perguntas_rodada", "juiz_evidencia_saida",
    "rastro_spec_report", "rastro_spec_status", "rastro_spec_status_envelope",
    "conteudo_aprovado_spec_report", "conteudo_aprovado_spec_status", "conteudo_aprovado_spec_status_envelope",
    # o resumido × canônico aprovado (07/10/2026): sem apagar, a correção começava com as rodadas esgotadas
    "conteudo_aprovado_resumido_report", "conteudo_aprovado_resumido_status",
    "conteudo_aprovado_resumido_status_envelope", "resumido_rodada",
    # a banca no fim de produto (08/10/2026)
    "banca_produto_narrativa", "banca_produto_pedagogia",
    "banca_produto_report", "banca_produto_status", "banca_produto_status_envelope",
}) | CHAVES_DESIGN
#: Tudo que a etapa de produto grava. Ficam de fora, de propósito, o que ela LÊ da geração original:
#: `briefing`, `perguntas_po` e `material_anexado` — refazer produto é refazê-lo sobre o mesmo pedido
#: e o mesmo material, mais o pedido de correção.
CHAVES_PRODUTO = frozenset({
    "nucleo_narrativo", "micro_gate_report", "micro_gate_status", "micro_gate_status_envelope", "micro_gate_rodada",
    # o mapa e a ideação são refeitos: o pedido de correção pode dizer qual é o conceito central
    "mapa_conceitual", "ideacao_mecanismos", "cobertura_report", "cobertura_resultado",
    "profundidade_report", "profundidade_status", "profundidade_status_envelope", "profundidade_rodada",
    "fidelidade_nucleo_report", "fidelidade_nucleo_status", "fidelidade_nucleo_status_envelope",
    "mecanica_report", "mecanica_status", "mecanica_status_envelope",
    "juiz_fidelidade_nucleo_saida", "interpretacao_fidelidade_nucleo_saida",
    "nucleo_rodada",
    "missoes_vizinhas", "catalogo_indice_status", "catalogo_indice_status_envelope",
    # `one_pager_gate0` só é gravado se não existe (`agents.callbacks.preservar_one_pager`): sem cair aqui, o
    # «one-pager original» de um refazer de produto continuava sendo o da missão anterior
    "one_pager", "one_pager_gate0", "brief_escopo", "brief_escopo_status", "brief_escopo_status_envelope",
    # a conferência do one-pager do PO (08/10/2026). O `one_pager_po` em si fica: é insumo, como o material
    "one_pager_po_report", "one_pager_po_status", "one_pager_po_status_envelope", "one_pager_po_rodada",
    "secoes_apoio_rodada",
    "contrato_produto_report", "contrato_produto_status", "contrato_produto_status_envelope",
    "gate_estrutural_report", "gate_estrutural_status", "gate_estrutural_status_envelope", "gate_estrutural_rodada",
    "avaliacao_pedagogica_report", "avaliacao_status", "avaliacao_status_envelope",
    "experiencia_aluno_report", "experiencia_status", "experiencia_status_envelope",
    "adequacao_report", "adequacao_status", "adequacao_status_envelope", "avaliacoes_rodada",
    "gate_final_report", "gate_final_status", "gate_final_status_envelope",
    "juiz_contrato_produto_saida",
    # os comitês pedagógicos (15/10/2026): sem apagar, um refazer começava com as rodadas esgotadas e o núcleo
    # pulado por um voto da execução anterior (`agents.callbacks.manter_nucleo_sem_achado_do_a004`)
    "evidencia_one_pager_report", "evidencia_one_pager_status", "evidencia_one_pager_status_envelope",
    "mecanica_one_pager_report", "mecanica_one_pager_status", "mecanica_one_pager_status_envelope",
    "comite_canal_a_curriculo", "comite_canal_a_medida", "comite_canal_a_vivencia",
    "comite_canal_b_curriculo", "comite_canal_b_medida", "comite_canal_b_experiencia",
    "comite_final_pedagogia", "comite_final_qualidade", "comite_final_imersao",
    "comite_canal_a_report", "comite_canal_a_status", "comite_canal_a_status_envelope", "comite_canal_a_rodada",
    "comite_canal_b_report", "comite_canal_b_status", "comite_canal_b_status_envelope", "comite_canal_b_rodada",
    "comite_final_report", "comite_final_status", "comite_final_status_envelope", "comite_final_rodada",
    "comite_canais_rodada", "comite_final_externo_rodada",
}) | CHAVES_SPEC
CHAVES_TRANSVERSAL = frozenset({
    "diagnostico_execucao", "diagnostico_status", "diagnostico_status_envelope", "aprendizado_registro",
    # a ficha do A129: sem cair, a ficha da execução anterior ficava no estado de uma correção que
    # não chega à transversal, e o runner a registraria de novo no catálogo
    "ficha_catalogo", "ficha_catalogo_dados",
})
#: Contadores da execução anterior. `reexecucoes` é o orçamento de retrabalho da banca: sem zerar,
#: uma sessão que já gastou o teto chega à correção sem direito a conserto.
#: `tickets_sem_rota` acumula: sem zerar, o dossiê da correção listaria pendências da execução velha.
#: `mudancas_no_aprovado` é recalculada no começo de design e de dev; em produto ela não vale. Os retratos que
#: a originam (`conteudo_aprovado_base_design`, `conteudo_aprovado_base_dev`) ficam de propósito fora de toda
#: lista: têm de sobreviver ao refazer de produto para dizer o que mudou nele.
CHAVES_EXECUCAO = frozenset({"reexecucoes", "tickets_retrabalho", "tickets_sem_rota", "juiz_achados_entrada",
                             "fidelidade_entrada", "fidelidade_documentos", "interpretacao_entrada", "mudancas_no_aprovado",
                             "etapa_da_correcao", "escopo_banca", KEY_AGENTES_DEGRADADOS,
                             "contradicoes_documento", "contradicoes_referencia",
                             # a versão da rodada anterior de cada loop: some ao sair do loop, e aqui se a execução caiu
                             *(f"rodada_anterior_{c}" for c in ("one_pager", "spec_missao", "one_pager_resumido", "handoff_dev",
                                                                "brief_assets", "prd_final", "one_pager_pedagogico"))})
#: Em que etapa começou a correção desta execução (vazio sem pedido de correção).
KEY_ETAPA_DA_CORRECAO = "etapa_da_correcao"

#: Documentos escritos por um AUTOR (não por gate). Quando uma reexecução os apaga, a versão que
#: existia vai para `anterior_<chave>` e o autor a recebe no prompt (`agents/base.py`) como base.
#: Até 06/10/2026 o pedido dizia "o que não foi pedido continua como estava", mas o autor não via
#: como estava: apagado o documento, ele escrevia do zero, e a ideação sorteava outro mecanismo.
#: Acrescentar uma pergunta de evidência à spec devolvia outra missão inteira.
CHAVES_AUTORAIS = frozenset({
    "mapa_conceitual", "ideacao_mecanismos", "nucleo_narrativo", "one_pager", "spec_missao", "one_pager_resumido",
    "fechamento_lacunas", "ambiente_simulado", "brief_oficio", "jornada_telas", "fluxo_arestas", "copy_strings",
    "camada_caa", "wireframes_cobertura", "copy_strings_revisada", "prototipo_html",
    "handoff_dev", "brief_assets", "banco_conteudo", "prd_final", "one_pager_pedagogico",
})
PREFIXO_ANTERIOR = "anterior_"
#: `versao_anterior_<chave>`: o texto cru da versão de antes do refazer, sem as instruções de `anterior_<chave>`.
#: Fica até a próxima reexecução: é a prova das ordens de não mexer (`tools/fidelidade.aplicar(anteriores=…)`), e o
#: retrabalho dos loops não mexe nele (plano padrão ouro, 2.3).
PREFIXO_VERSAO_ANTERIOR = "versao_anterior_"

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
    "Contrato de evidência do one-pager (§12a)": "produto",
    # o one-pager do PO reescrito só se conserta refazendo o one-pager, não a spec
    "One-pager do PO preservado": "produto",
    "Conformidade BNCC Computação": "spec",
    "Ficha do manifesto (produto)": "spec",
    "Matriz de evidência pedagógica": "spec",
    "Perguntas de produto (9f)": "spec",
    "Juiz das perguntas de produto": "spec",
    "Rastro de lacunas da spec": "spec",
    "Spec × one-pager aprovado": "spec",
    "Spec da missão": "spec",
    # o resumido roda no fim da correção a partir da spec: refazer spec o refaz
    "Resumido × one-pager aprovado": "spec",
    "One-pager resumido": "spec",
    "Spec consolidada × one-pager aprovado": "design",
    "Banca de produto": "spec",
    "Banca de design": "design",
    "Banca de entrada do dev": "dev",
    "Coerência do PRD com o one-pager aprovado": "dev",
    "Coerência do pedagógico com o one-pager aprovado": "dev",
    "Fechamento de lacunas (D0)": "design",
    "Ambiente simulado (D9)": "design",
    "QA de entregáveis (design)": "design",
    "Retrabalho de design": "design",
    "Rastro de lacunas do design": "design",
    "Coerência entre documentos": "design",
    "Ficha do manifesto": "dev",
    "Contrato de telemetria e arquitetura": "dev",
    "Banco de conteúdo": "dev",
    "Handoff de dev": "dev",
    "Rastro de lacunas antes do PRD": "dev",
    "Banca de dev": "dev",
    "Retrabalho da banca": "dev",
    "Pendências e consistência do PRD": "dev",
    "Coerência KPI ↔ evento ↔ tela": "dev",
    "PRD × one-pager aprovado": "dev",
    "Pedagógico × one-pager aprovado": "dev",
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
            "Os documentos das etapas anteriores foram preservados e são seus insumos. Se você é autor de um "
            "documento desta etapa, a versão que existia vem na seção \"Sua versão anterior deste documento\": "
            "é dela que você parte, não de uma folha em branco.",
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
            "1. Aplique o pedido **no que é seu** — no documento que você produz, editando a versão anterior. Se o "
            "pedido não toca o seu documento, mantenha a versão anterior e ajuste só o que os insumos, se mudaram, "
            "obrigam a ajustar.",
            "2. Não invente o resto nem amplie o escopo: o que não foi pedido continua como estava — mesma mecânica, "
            "mesma narrativa, mesmos nomes, etapas, telas e números.",
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
    #: `pontual` (trocas do editor, autores travados) ou `refazer` (os autores reescrevem a etapa).
    modo: str = ""
    #: Por que não foi pontual: o editor classificou o pedido como estrutural, ou as trocas não se aplicaram.
    motivo_modo: str = ""
    #: As trocas aplicadas, na ordem (`tools/edicao_pontual.py`), e o que o editor deixou para o PO decidir.
    edicoes: List[Dict[str, str]] = field(default_factory=list)
    pendencias: List[str] = field(default_factory=list)
    #: Passadas dos gates (a segunda em diante consertou bloqueios que a correção causou).
    passadas: int = 0


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


def bloco_versao_anterior(chave: str, documento: str) -> str:
    """Valor de `anterior_<chave>`: a versão que existia, com o que o autor faz com ela."""
    return "\n".join([
        "## Sua versão anterior deste documento",
        "",
        "Esta etapa está sendo refeita sobre uma missão que já existia. Abaixo está o documento que ocupava o seu "
        "lugar na execução anterior — a versão que as pessoas já leram e revisaram.",
        "",
        "1. **Parta dela.** Mantenha mecânica, narrativa, nomes, personagens, etapas, telas, textos e números como "
        "estão — palavra por palavra quando nada obriga a mudar.",
        "2. **Mude só o que tem motivo:** o que o pedido de correção pede; o que os seus insumos (documentos das "
        "etapas anteriores, notas de passagem) mudaram e obrigam a acompanhar; o que um gate desta execução "
        "reprovou. O tamanho da mudança é o do motivo: se o pedido manda refazer uma parte inteira, refaça essa "
        "parte — e só ela.",
        "3. Se o documento já foi reescrito nesta execução (você é revisor, ou está numa rodada seguinte de um "
        "loop), trabalhe sobre a versão atual e use esta só para conferir que nada fora do motivo mudou.",
        "4. Não reescreva por estilo nem melhore o que ninguém pediu: cada mudança sem motivo é uma missão "
        "diferente da que foi aprovada, e alguém vai ter de revisá-la de novo.",
        "",
        f'<versao_anterior chave="{chave}">',
        documento.strip(),
        "</versao_anterior>",
    ])


def _guardar_versoes_anteriores(estado: Dict[str, Any], limpo: Dict[str, Any], remover: frozenset) -> None:
    """Grava em `limpo` a base de cada documento autoral que a reexecução vai reescrever.

    Documento que não vai ser reescrito perde a base velha. Documento já apagado por uma
    reexecução anterior (produto refeito apaga design e dev, que só rodam no próximo *iniciar*)
    conserva a base que aquela reexecução guardou — senão o design chegaria sem nada.
    """
    for chave in CHAVES_AUTORAIS:
        anterior = PREFIXO_ANTERIOR + chave
        if chave not in remover:
            limpo.pop(anterior, None)
            limpo.pop(PREFIXO_VERSAO_ANTERIOR + chave, None)
            continue
        # a spec que o autor escreveu é a do Gate 0; `spec_missao` pode já trazer a consolidação do D0
        atual = estado.get("spec_missao_gate0") if chave == "spec_missao" else None
        atual = str(atual or estado.get(chave) or "").strip()
        if chave in ("prd_final", "one_pager_pedagogico"):
            # o anexo é da esteira, não do autor: na base dele, viraria texto a reescrever e duplicaria
            from tools.conteudo_aprovado import remover_anexo

            atual = remover_anexo(atual).strip()
        if atual:
            limpo[anterior] = bloco_versao_anterior(chave, atual)
            limpo[PREFIXO_VERSAO_ANTERIOR + chave] = atual


def texto_do_pedido(pedido_md: str) -> str:
    """Só o que a pessoa escreveu, de dentro de `pedido_correcao` (`PedidoCorrecao.como_markdown`).

    O valor do estado leva um cabeçalho da esteira ("Esta execução refaz a etapa…"), os anexos e "Como agir". A
    fidelidade citava esse cabeçalho como se fosse o pedido do PO (exp06ef1b, 08/10/2026). Texto fora desse formato
    volta como está.
    """
    texto = pedido_md or ""
    m = re.search(r"^### Pedido, na íntegra\s*\n(.*?)(?=^### |\Z)", texto, re.S | re.M)
    if not m:
        return texto.strip()
    return "\n".join(re.sub(r"^>\s?", "", l) for l in m.group(1).strip().splitlines()).strip()


def preparar_estado(
    estado: Dict[str, Any], etapa: str, pedido_md: Optional[str] = None
) -> Tuple[Dict[str, Any], List[str]]:
    """Estado pronto para reexecutar `etapa`: sem o que ela produz, com herança recalculada e o pedido.

    O que ela produz sai, mas cada documento autoral fica como base em `anterior_<chave>`.
    Pura, sem I/O. Devolve `(estado_limpo, chaves_removidas)`.
    """
    if etapa not in CHAVES_POR_ETAPA:
        raise ValueError(f"etapa inválida: {etapa!r} (esperado uma de {ETAPAS})")
    remover = CHAVES_POR_ETAPA[etapa] | CHAVES_TRANSVERSAL | CHAVES_EXECUCAO | {KEY_PEDIDO_CORRECAO}
    removidas = sorted(k for k in estado if k in remover)
    limpo = {k: v for k, v in estado.items() if k not in remover and not str(k).startswith("temp:")}
    _guardar_versoes_anteriores(estado, limpo, remover)
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
        # a fidelidade de design e de dev confere o pedido corrente só quando a correção começou nelas
        limpo[KEY_ETAPA_DA_CORRECAO] = etapa
    return limpo, removidas


def preparar_estado_pontual(
    estado: Dict[str, Any], etapa: str, pedido_md: Optional[str], documentos: Dict[str, str],
    edicoes: Sequence[Dict[str, Any]],
) -> Tuple[Dict[str, Any], List[str]]:
    """Estado para a correção pontual: o de `preparar_estado`, com os documentos da etapa já editados e travados.

    Os gates da etapa caem, como num refazer, e são julgados de novo; os autores não rodam
    (`agents.callbacks.travar_documento_na_correcao_pontual`). `versao_anterior_<chave>` fica com a versão de antes —
    a fidelidade prova com ela que nada além das trocas mudou. A linha de base guarda o veredito de cada gate antes da
    correção (`tools/linha_de_base.py`). Pura, sem I/O.
    """
    from agents.callbacks import KEY_DOCUMENTOS_TRAVADOS, KEY_MODO_CORRECAO
    from tools import edicao_pontual, linha_de_base

    limpo, removidas = preparar_estado(estado, etapa, pedido_md)
    travados: List[str] = []
    for chave in edicao_pontual.travados(etapa):
        texto = documentos.get(chave) if chave in documentos else estado.get(chave)
        if not str(texto or "").strip():
            continue
        limpo[chave] = texto
        # o autor não roda: a instrução de "parta da versão anterior" não tem leitor
        limpo.pop(PREFIXO_ANTERIOR + chave, None)
        travados.append(chave)
    if etapa == "produto" and limpo.get("one_pager"):
        # `agents.callbacks.preservar_one_pager` roda depois do autor, que não roda: o original desta versão é o editado
        limpo["one_pager_gate0"] = limpo["one_pager"]
    if limpo.get(KEY_PEDIDO_CORRECAO):
        # quem lê o pedido aqui são os gates e juízes: os autores desta etapa não rodam
        limpo[KEY_PEDIDO_CORRECAO] += (
            "\n\n### Modo desta correção: edição pontual\n\nO pedido foi aplicado como trocas trecho a trecho, listadas "
            "abaixo; os documentos diferem da versão anterior só por elas, e nenhum autor reescreveu nada. Ao julgar, "
            "confira se as trocas atendem ao pedido e se quebraram algo.\n\n" + edicao_pontual.resumo(edicoes))
    limpo[KEY_MODO_CORRECAO] = edicao_pontual.MODO_PONTUAL
    limpo[KEY_DOCUMENTOS_TRAVADOS] = travados
    limpo["edicoes_pontuais"] = [dict(e) for e in edicoes]
    limpo[linha_de_base.KEY_LINHA_DE_BASE] = linha_de_base.capturar(
        estado, sorted(k for k in CHAVES_POR_ETAPA.get(etapa, ()) if k.endswith("_status")))
    return limpo, removidas


def validador_do_po(estado: Dict[str, Any], pedido_extra: str = ""):
    """Recusa a troca que faz o one-pager do PO perder texto (`tools.one_pager_po.perdidos_pela_edicao`). None sem PO."""
    po = str(estado.get("one_pager_po") or "")
    if not po.strip():
        return None
    from tools.comite import texto_votos
    from tools.one_pager_po import perdidos_pela_edicao

    pedidos = "\n".join(str(p.get("texto") or "") for p in (estado.get(KEY_PEDIDOS_DO_PO) or []) if isinstance(p, dict))
    brief = str(estado.get("brief_escopo") or "")

    def validar(documentos: Dict[str, str]) -> List[str]:
        if "one_pager" not in documentos:
            return []
        return perdidos_pela_edicao(po, str(estado.get("one_pager") or "") + "\n\n" + brief,
                                    documentos["one_pager"] + "\n\n" + brief, str(estado.get("briefing") or ""),
                                    pedidos + "\n" + pedido_extra, texto_votos(estado))

    return validar


#: Tentativas do editor quando alguma troca não se aplica (trecho que não existe ou que se repete).
TENTATIVAS_DO_EDITOR = 3


def texto_para_o_editor(pedido: "PedidoCorrecao") -> str:
    """O pedido como o PO escreveu, com o texto dos anexos — sem o cabeçalho da esteira."""
    partes = [pedido.texto.strip() or "(sem texto)"]
    for nome, conteudo in pedido.anexos:
        partes += ["", f"### Anexo: {nome}", "", conteudo.strip()]
    for nome in pedido.anexos_sem_texto:
        partes.append(f"\n### Anexo: {nome} — sem texto extraível; considere só o que o pedido diz sobre ele.")
    return "\n".join(partes)


def achados_para_o_editor(linhas: Sequence[Dict[str, Any]], estado: Dict[str, Any]) -> str:
    """Os bloqueios que a correção pode ter causado, para o editor consertar com novas trocas."""
    if not linhas:
        return ""
    blocos = ["## Bloqueios que os gates acusaram depois das suas trocas", "",
              "As trocas abaixo já estão aplicadas nos documentos que você recebeu. Os gates julgaram a missão "
              "corrigida e acusaram estes bloqueios, que citam o texto que você pôs ou não citam trecho. Acrescente "
              "trocas que os resolvam **sem desfazer o pedido do PO**. Se um bloqueio não é consequência das suas "
              "trocas nem do pedido, não mexa: devolva `edicoes` vazia e explique em `pendencias`.", ""]
    for l in linhas:
        blocos.append(f"- `{l['gate']}` — {l.get('codigo') or 'achado'}: {l.get('resumo') or ''}")
    relatorios = []
    for gate in dict.fromkeys(l["gate"] for l in linhas):
        texto = str(estado.get(gate[: -len("_status")] + "_report") or "").strip()
        if texto:
            relatorios.append(f"### Relatório de `{gate}`\n\n{texto[:6000]}")
    return "\n".join(blocos + ([""] + relatorios if relatorios else []))


async def propor_edicao(
    pedido_texto: str, etapa: str, documentos: Dict[str, str], *, erros: str = "", achados: str = "",
    thinking_budget: Optional[int] = 4096,
) -> Any:
    """Roda o editor num runner mínimo, fora da esteira. Falha de rede ou modelo vira proposta estrutural."""
    from tools.edicao_pontual import MODO_ESTRUTURAL, Proposta, ler_proposta, renderizar

    try:
        from google.adk.runners import InMemoryRunner

        from agents.transversal import get_editor_pontual_agent
        from pipeline.runner import build_user_message

        app = "EditorPontual"
        runner = InMemoryRunner(agent=get_editor_pontual_agent(thinking_budget=thinking_budget), app_name=app)
        sessao = await runner.session_service.create_session(app_name=app, user_id="editor", state={
            "pedido_pontual": pedido_texto, "etapa_da_correcao": etapa,
            "documentos_pontuais": renderizar(documentos),
            "erros_da_edicao": erros, "achados_da_edicao": achados,
        })
        async for _ in runner.run_async(user_id="editor", session_id=sessao.id,
                                        new_message=build_user_message("Aplique o pedido como trocas.", None)):
            pass
        final = await runner.session_service.get_session(app_name=app, user_id="editor", session_id=sessao.id)
        return ler_proposta(str((final.state if final else {}).get("edicao_pontual") or ""))
    except Exception as exc:  # pragma: no cover - rede/modelo
        logger.warning("Editor pontual falhou: %s", exc)
        return Proposta(modo=MODO_ESTRUTURAL, motivo=f"falha no editor: {exc}")


async def editar(
    pedido_texto: str, etapa: str, documentos: Dict[str, str], *, achados: str = "",
    proponente: Any = None, validador: Any = None,
) -> Tuple[Any, Any]:
    """`(resultado | None, proposta)`: as trocas aplicadas aos documentos, ou None se o pedido não cabe numa edição.

    O editor tem `TENTATIVAS_DO_EDITOR` chances: troca que não se aplica volta a ele com o motivo, e também a que o
    `validador` recusa (`validador(documentos_novos) -> [falhas]`, ex.: texto do one-pager do PO apagado).
    `proponente` troca o editor nos testes (mesma assinatura de `propor_edicao`).
    """
    from tools.edicao_pontual import MODO_ESTRUTURAL, Proposta, aplicar

    proponente = proponente or propor_edicao
    erros = ""
    proposta = Proposta(modo=MODO_ESTRUTURAL)
    for _ in range(TENTATIVAS_DO_EDITOR):
        proposta = await proponente(pedido_texto, etapa, documentos, erros=erros, achados=achados)
        if not proposta.pontual:
            return None, proposta
        resultado = aplicar(documentos, proposta.edicoes)
        if resultado.ok and validador is not None:
            recusas = list(validador(resultado.documentos) or [])
            if recusas:
                from tools.one_pager_po import COMO_RESPEITAR_O_PO

                erros = ("## Suas trocas da tentativa anterior foram recusadas\n\nNenhuma foi aplicada. "
                         + COMO_RESPEITAR_O_PO + " Refaça a lista inteira corrigindo isto:\n\n"
                         + "\n".join(f"- {r}" for r in recusas))
                continue
        if resultado.ok:
            return resultado, proposta
        erros = ("## Suas trocas da tentativa anterior não se aplicaram\n\nNenhuma foi aplicada. Refaça a lista "
                 "inteira corrigindo estas:\n\n" + "\n".join(f"- {f}" for f in resultado.falhas))
    proposta.motivo = (f"as trocas não se aplicaram em {TENTATIVAS_DO_EDITOR} tentativas — "
                       + (erros.splitlines()[-1][2:] if erros else "sem detalhe"))
    proposta.modo = MODO_ESTRUTURAL
    return None, proposta


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


def restaurar_backup(run_dir: Path, backup: Path, custo_parcial: Optional[Dict[str, Any]] = None,
                     etapas: Optional[List[str]] = None) -> List[str]:
    """Devolve à sessão tudo que está no backup (sobrescrevendo). Retorna os caminhos restaurados.

    O custo não volta com o backup: o que foi gasto foi gasto. O `custo_missao` mais completo (o de agora ou o do
    backup) fica no estado restaurado, e `custo_parcial` — o que a execução que falhou consumiu até cair — entra
    como uma linha marcada `falhou` (`tools/custo.py`).
    """
    from tools.custo import KEY_CUSTO, acumular

    run_dir, backup = Path(run_dir), Path(backup)
    caminho_estado = run_dir / "estado.json"

    def custo_em(caminho: Path) -> Dict[str, Any]:
        try:
            return json.loads(caminho.read_text(encoding="utf-8")).get(KEY_CUSTO) or {}
        except (OSError, ValueError):
            return {}

    custo_antes = custo_em(caminho_estado)
    restaurados: List[str] = []
    for arquivo in sorted(p for p in backup.rglob("*") if p.is_file()):
        rel = arquivo.relative_to(backup)
        alvo = run_dir / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(arquivo, alvo)
        restaurados.append(rel.as_posix())

    if caminho_estado.exists():
        custo = max((custo_antes, custo_em(caminho_estado)), key=lambda c: len(c.get("execucoes") or []))
        if custo_parcial and (custo_parcial.get("tokens") or {}).get("chamadas"):
            custo = acumular(custo, {**custo_parcial, "falhou": True}, list(etapas or []))
        if custo and custo != custo_em(caminho_estado):
            try:
                estado = json.loads(caminho_estado.read_text(encoding="utf-8"))
                estado[KEY_CUSTO] = custo
                caminho_estado.write_text(json.dumps(estado, indent=2, ensure_ascii=False, default=str),
                                          encoding="utf-8")
            except (OSError, ValueError) as exc:
                logger.warning("Não consegui devolver o custo ao estado restaurado de %s: %s", run_dir.name, exc)
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
    if registro.modo == "pontual":
        from tools.edicao_pontual import resumo

        docs = sorted({e.get("documento", "") for e in registro.edicoes})
        return (
            f"🔧 **Correção pontual aplicada em {registro.quando}** — {len(registro.edicoes)} troca(s) em "
            f"{', '.join(f'`{d}`' for d in docs) or 'nenhum documento'}; o resto ficou idêntico. Os gates de "
            f"**{registro.etapa}** julgaram a missão corrigida ({registro.passadas} passada(s)). Status: {icone} "
            f"{registro.status}.\n\n{resumo(registro.edicoes)}"
            + ("\n\n**Para o PO decidir:**\n" + "\n".join(f"- {p}" for p in registro.pendencias)
               if registro.pendencias else "")
            + "\n\nDe onde veio cada bloqueio está em `linha-de-base-da-correcao.md`."
        )
    if registro.motivo_modo:
        motivo = f"refeita pelos autores: {registro.motivo_modo}"
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
    notas_de_passagem: Optional[str] = None,
    proponente: Any = None,
    **opcoes_runner: Any,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Reexecuta `etapa` (e as seguintes) sobre a sessão em `run_dir`, gravando na mesma pasta.

    Com pedido, a correção é **pontual** primeiro (`tools/edicao_pontual.py`): o editor transforma o pedido em trocas,
    o código as aplica, os autores não rodam e os gates julgam a missão corrigida; a linha de base separa o bloqueio que
    a correção causou do que ela não tocou, e o causado volta ao editor (até `correcao_pontual_passadas`). Só quando o
    editor diz que o pedido é estrutural — ou as trocas não se aplicam — a etapa é refeita pelos autores, como era.
    `proponente` troca o editor nos testes.

    `notas_de_passagem`, quando vem, substitui a do estado salvo: é o *refazer* do parecer humano,
    e uma refação invalida os pareceres da própria etapa — o texto velho não pode seguir aos agentes.

    Emite `correcao_started`, repassa os eventos do runner e fecha com `correcao_completed`
    (`result` + `registro`) ou `correcao_error` (backup restaurado). `opcoes_runner` vai para
    `run_orchestrator_pipeline_stream` (thinking_budget, include_thoughts, modo_estrito…).
    """
    from pipeline.runner import run_orchestrator_pipeline_stream

    run_dir = Path(run_dir)
    estado, conversa, briefing = carregar_sessao(run_dir)
    recusa = None
    if etapa == "produto":
        material, recusa = material_para_refazer_produto(estado, conversa, pedido)
        if not recusa:
            estado = {**estado, "material_anexado": material}
    from config import get_settings
    from tools import edicao_pontual, linha_de_base
    from tools.custo import KEY_CUSTO

    tem_pedido = bool(pedido and (pedido.texto.strip() or pedido.anexos or pedido.anexos_sem_texto))
    pedido_md = pedido.como_markdown(etapa) if tem_pedido else None
    settings = get_settings()
    inicio = time.time()
    documentos = edicao_pontual.documentos_da_etapa(estado, etapa)
    edicoes: List[Dict[str, Any]] = []
    pendencias: List[str] = []
    modo, motivo_modo = "refazer", ""
    if settings.correcao_pontual and tem_pedido and pedido and documentos:
        yield {"type": "edicao_started", "etapa": etapa, "passada": 1, "timestamp": time.time()}
        # o texto do one-pager do PO só sai pelo pedido dele: a troca que o apaga sem isso volta ao editor
        guarda = validador_do_po({**estado, KEY_PEDIDOS_DO_PO: _pedidos_do_po(conversa)}, texto_para_o_editor(pedido))
        resultado, proposta = await editar(texto_para_o_editor(pedido), etapa, documentos, proponente=proponente,
                                           validador=guarda)
        if resultado is not None:
            modo, documentos = edicao_pontual.MODO_PONTUAL, resultado.documentos
            edicoes, pendencias = edicao_pontual.como_dicts(resultado.aplicadas), list(proposta.pendencias)
        else:
            motivo_modo = proposta.motivo or "o editor classificou o pedido como estrutural"
        yield {"type": "edicao_completed", "etapa": etapa, "modo": modo, "motivo": proposta.motivo,
               "edicoes": edicoes, "pendencias": pendencias, "timestamp": time.time()}
    pontual = modo == edicao_pontual.MODO_PONTUAL
    if recusa and not pontual:
        # sem o material, só a edição pontual cabe: refazer o núcleo sem ele geraria outra missão. Nada foi tocado ainda:
        # sem backup, sem estado limpo, sem registro de correção
        yield {"type": "correcao_error", "error": recusa, "registro": None, "restaurados": [], "timestamp": time.time()}
        return

    def estado_inicial() -> Tuple[Dict[str, Any], List[str]]:
        if pontual:
            novo, chaves = preparar_estado_pontual(estado, etapa, pedido_md, documentos, edicoes)
        else:
            novo, chaves = preparar_estado(estado, etapa, pedido_md)
        if notas_de_passagem is not None:
            novo[KEY_NOTAS_DE_PASSAGEM] = notas_de_passagem
        novo[KEY_PEDIDOS_DO_PO] = _pedidos_do_po(conversa)
        return novo, chaves

    limpo, removidas = estado_inicial()
    backup = fazer_backup(run_dir, etapa, removidas)
    stages = _stages_de(etapa, so_esta_etapa)
    quando = time.strftime("%d/%m/%Y %H:%M:%S")
    yield {
        "type": "correcao_started", "etapa": etapa, "stages": stages, "modo": modo,
        "backup": backup.relative_to(run_dir).as_posix(), "chaves_removidas": removidas, "timestamp": inicio,
    }

    result: Any = None
    erro: Optional[Dict[str, Any]] = None
    custo_parcial: Optional[Dict[str, Any]] = None
    passadas_max = max(1, int(settings.correcao_pontual_passadas)) if pontual else 1
    passada = 0
    while passada < passadas_max:
        passada += 1
        result, erro = None, None
        async for evento in run_orchestrator_pipeline_stream(
            prompt=briefing,
            user_id=conversa.get("user_id"),
            session_id=conversa.get("session_id"),
            stages=stages,
            initial_state=limpo,
            run_dir=run_dir,
            registrar_conversa=False,
            modo_pontual=pontual,
            **opcoes_runner,
        ):
            tipo = evento.get("type")
            if tipo == "pipeline_completed":
                result = evento.get("result")
            elif tipo == "pipeline_error":
                erro = evento
            elif tipo == "custo_parcial":
                custo_parcial = evento.get("custo")
            yield evento
        if result is None or not pontual or passada >= passadas_max:
            break
        # O que a correção causou volta ao editor, com os relatórios: ele acrescenta trocas, e os gates julgam de novo
        final = dict(getattr(result, "state", None) or {})
        linhas = final.get("linha_de_base_linhas") or []
        novos = linha_de_base.bloqueios_novos(linhas)
        if not novos:
            if any(l.get("origem") == linha_de_base.FALHA_DE_EXECUCAO for l in linhas):
                # um juiz não respondeu: não há o que editar, mas há o que julgar de novo
                yield {"type": "edicao_completed", "etapa": etapa, "modo": "rejulgar", "motivo": "juiz sem resposta",
                       "edicoes": [], "pendencias": pendencias, "timestamp": time.time()}
                limpo, _ = estado_inicial()
                if final.get(KEY_CUSTO):
                    limpo[KEY_CUSTO] = final[KEY_CUSTO]
                continue
            break
        yield {"type": "edicao_started", "etapa": etapa, "passada": passada + 1, "bloqueios": len(novos),
               "timestamp": time.time()}
        conserto, proposta = await editar(texto_para_o_editor(pedido), etapa, documentos,
                                          achados=achados_para_o_editor(novos, final), proponente=proponente,
                                          validador=validador_do_po({**final, "one_pager": documentos.get("one_pager", "")},
                                                                    texto_para_o_editor(pedido)))
        if conserto is None or not conserto.aplicadas:
            pendencias += [p for p in getattr(proposta, "pendencias", []) if p not in pendencias]
            yield {"type": "edicao_completed", "etapa": etapa, "modo": "sem-conserto", "motivo": proposta.motivo,
                   "edicoes": [], "pendencias": pendencias, "timestamp": time.time()}
            break
        documentos = conserto.documentos
        edicoes += edicao_pontual.como_dicts(conserto.aplicadas)
        pendencias += [p for p in proposta.pendencias if p not in pendencias]
        yield {"type": "edicao_completed", "etapa": etapa, "modo": modo, "motivo": proposta.motivo,
               "edicoes": edicao_pontual.como_dicts(conserto.aplicadas), "pendencias": pendencias,
               "timestamp": time.time()}
        limpo, _ = estado_inicial()
        # o custo da passada anterior já foi gasto: a seguinte acumula sobre ele
        if final.get(KEY_CUSTO):
            limpo[KEY_CUSTO] = final[KEY_CUSTO]

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
        modo=modo if tem_pedido else "",
        motivo_modo=motivo_modo,
        edicoes=edicoes,
        pendencias=pendencias,
        passadas=passada,
    )
    mensagens: List[Dict[str, Any]] = []
    if tem_pedido and pedido and pedido.texto.strip():
        mensagens.append({"role": "user", "content": pedido.texto.strip()})

    if result is None:
        restaurados = restaurar_backup(run_dir, backup, custo_parcial, stages)
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


async def iniciar_etapa_stream(
    run_dir: Path,
    etapa: str,
    notas_de_passagem: str = "",
    **opcoes_runner: Any,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Roda a próxima etapa de uma missão com parecer humano, sobre o estado salvo, na mesma pasta.

    É o esqueleto de `executar_correcao_stream` sem pedido de correção: não é conserto, é a esteira
    andando. `preparar_estado` ainda apaga o que a etapa (e as seguintes) já tinham produzido — há
    produto numa etapa *devolvida* e depois liberada de novo — e recalcula a herança. `etapa=
    "transversal"` fecha a missão (diagnóstico → aprendizado → catálogo).

    Emite os eventos do runner e fecha com `etapa_completed` (`result`) ou `etapa_error` (backup
    restaurado). Não entra em `historico_correcoes`: a linha do tempo das passagens é o `fluxo`.
    """
    from pipeline.runner import run_orchestrator_pipeline_stream

    run_dir = Path(run_dir)
    estado, conversa, briefing = carregar_sessao(run_dir)
    if etapa == "transversal":
        limpo = {k: v for k, v in estado.items() if k not in CHAVES_TRANSVERSAL | {KEY_PEDIDO_CORRECAO}}
        removidas = sorted(k for k in estado if k not in limpo)
        stages, com_transversal = ETAPA_PARA_STAGES["transversal"], True
        # o dossiê (A50) ganha a seção "Passagens" a partir daqui: o fluxo vive no conversa.json,
        # fora do estado que os agentes enxergam
        fluxo = (conversa.get("fluxo") or {}) if isinstance(conversa.get("fluxo"), dict) else {}
        limpo["pareceres_humanos"] = list(fluxo.get("pareceres") or [])
    else:
        limpo, removidas = preparar_estado(estado, etapa)
        stages, com_transversal = [etapa], False
    limpo[KEY_NOTAS_DE_PASSAGEM] = notas_de_passagem
    limpo[KEY_PEDIDOS_DO_PO] = _pedidos_do_po(conversa)
    backup = fazer_backup(run_dir, f"passagem-{etapa}", removidas)
    inicio = time.time()
    yield {"type": "etapa_started", "etapa": etapa, "stages": stages, "timestamp": inicio,
           "backup": backup.relative_to(run_dir).as_posix()}

    result: Any = None
    erro: Optional[Dict[str, Any]] = None
    custo_parcial: Optional[Dict[str, Any]] = None
    async for evento in run_orchestrator_pipeline_stream(
        prompt=briefing,
        user_id=conversa.get("user_id"),
        session_id=conversa.get("session_id"),
        stages=stages,
        initial_state=limpo,
        run_dir=run_dir,
        registrar_conversa=False,
        com_transversal=com_transversal,
        **opcoes_runner,
    ):
        tipo = evento.get("type")
        if tipo == "pipeline_completed":
            result = evento.get("result")
        elif tipo == "pipeline_error":
            erro = evento
        elif tipo == "custo_parcial":
            custo_parcial = evento.get("custo")
        yield evento

    if result is None or getattr(result, "status", "") == "error":
        restaurados = restaurar_backup(run_dir, backup, custo_parcial, stages)
        detalhe = (erro or {}).get("error") or getattr(result, "error_message", None) or "o runner terminou sem resultado"
        yield {"type": "etapa_error", "etapa": etapa, "error": detalhe, "restaurados": restaurados,
               "timestamp": time.time()}
        return

    from pipeline.session_store import save_session_record

    nome = {"transversal": "o dossiê final"}.get(etapa, f"a etapa **{etapa}**")
    mensagens = list(conversa.get("messages") or []) + [
        {"role": "assistant", "content": f"▶️ {time.strftime('%d/%m/%Y %H:%M')} — terminou {nome} "
                                         f"({round(time.time() - inicio)} s). Status: {getattr(result, 'status', '')}."}]
    save_session_record(
        run_dir=run_dir,
        session_id=str(conversa.get("session_id") or result.session_id),
        user_id=str(conversa.get("user_id") or result.user_id),
        prompt=str(conversa.get("prompt") or briefing),
        result=result,
        messages=mensagens,
        attached_files=list(conversa.get("attached_files") or []),
        created_at=conversa.get("created_at"),
        historico_correcoes=historico_de(conversa) or None,
    )
    yield {"type": "etapa_completed", "etapa": etapa, "result": result, "timestamp": time.time()}


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
