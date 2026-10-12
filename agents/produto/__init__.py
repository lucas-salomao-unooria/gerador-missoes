"""Área de PRODUTO — do briefing ao spec fechado da missão.

Ordem (SequentialAgent):
  p00c A002MapaConceitual    → mapa_conceitual (conceito limiar, núcleo e apoio do material, com o
                                 trecho citado; as crenças de entrada que o bimestre derruba)
  p00d A003IdeacaoMecanismos → ideacao_mecanismos (três mecanismos distintos, pontuados na
                                 rubrica de profundidade; o núcleo desenvolve o escolhido)
  ┌─ LoopAgent (≤ 2 rodadas) ─────────────────────────────────────────┐
  │ p0a A004NucleoNarrativo   → nucleo_narrativo                     │
  │ p0cc A006CoberturaConceitual → cobertura_resultado (determinístico) │
  │ p0mg A007MicroGate        → micro_gate_report                    │
  │ p0jp A008JuizProfundidade → profundidade_report (notas P1–P6)   │
  │ p0pc A011ProfundidadeCheck → profundidade_status (contado nas notas) │
  │ p0mgc A012MicroGateCheck       → micro_gate_status                    │
  │ p0nc A013NucleoCheck     → sai quando micro-gate E profundidade passam │
  └───────────────────────────────────────────────────────────────────┘
  p0b A014SecoesApoio         → one_pager  (núcleo + seções 2, 5–18 + brief)
  ┌─ LoopAgent (≤ N rodadas) ─────────────────────────────────────────┐
  │ p0c A019ContratoProdutoCheck → contrato_produto_report (lint: canal │
  │      de sala, estado no servidor, SAEB, números sem origem)       │
  ┌─ LoopAgent (≤ N rodadas) ─────────────────────────────────────────┐
  │ p1  A021GateEstrutural    → gate_estrutural_report               │
  │ p1c A022GateEstruturalCheck    → gate_estrutural_status (escalate)    │
  │ p1b A023RevisorOnePager   → one_pager (corrigido)                │
  └───────────────────────────────────────────────────────────────────┘
  ┌─ ParallelAgent ──────────────────────────────────────────────────┐
  │ p2  A024aAvaliacaoPedagogica → avaliacao_pedagogica_report       │
  │ p3  A024bExperienciaEstudante    → experiencia_aluno_report          │
  └───────────────────────────────────────────────────────────────────┘
  p4  A033GateFinalProduto    → gate_final_report
  p4c GateFinalCheck           → gate_final_status
  p5  A035SpecMissao          → spec_missao   (saída final de Produto)
  p5c A036BnccCheck                → bncc_status   (determinístico: bloco 11 × BNCC Computação oficial;
                                 não conforme bloqueia design e dev)
  p5d A040PerguntasCheck     → perguntas_status (determinístico: as 5 perguntas do 9f, com decisão
                                 com limiar e ação que existe na tabela de eventos)
  p5e A041JuizPerguntas      → juiz_perguntas_report (o que só se julga lendo: a pergunta muda
                                 uma decisão nossa e é sobre o produto, não sobre a criança)
  p5f A043RastroSpec         → rastro_spec_status (determinístico: marcador de lacuna na spec;
                                 o de produto volta para a spec, o do PO fica 🟡 no parecer)
  p5g A044ConteudoAprovadoSpec → conteudo_aprovado_spec_status (determinístico: habilidades,
                                 tempo em tela e podcast iguais aos do one-pager aprovado)
  ┌── OnePagerResumidoLoop (até SPEC_MAX_RODADAS) ─────────────────────────┐
  │ p6  A051OnePagerResumido   → one_pager_resumido (o formato curto do time de produto para │
  │                              avaliação pedagógica, derivado do canônico e da spec conferida) │
  │ p6b A052ConteudoAprovadoResumido → habilidades, tempo e Canal B × canônico aprovado │
  └────────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, Optional

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.loop_agent import LoopAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.sequential_agent import SequentialAgent

from agents.base import create_llm_agent
from agents.banca import get_banca
from agents.juiz import get_fidelidade_check, get_juiz_de_achados
from agents.callbacks import dispensar_ideacao_com_one_pager_do_po, marcar_heranca, preservar_one_pager
from agents.checkers import (
    DocumentoObrigatorioAgent,
    SecaoSplitAgent,
    BnccCheckAgent,
    CoberturaConceitualAgent,
    EnvelopeGateAgent,
    MecanicaCheckAgent,
    ProfundidadeCheckAgent,
    RastroCheckAgent,
    SaidaDeLoopAgent,
    VizinhasCatalogoAgent,
)
from config import get_settings
from prompts import load_prompt
from tools.rastro import FONTES_SPEC

warnings.filterwarnings("ignore", category=DeprecationWarning, module="google.adk.agents")

# O prompt do micro-gate fixa o teto em 2 rodadas: na segunda reprovação o problema é de
# mecanismo, não de redação, e o relatório sai com `precisa_humano`.
MICRO_GATE_MAX_RODADAS = 2


def get_mapa_conceitual_agent(**kw) -> LlmAgent:
    """Lê o material do bimestre ANTES de alguém inventar a missão.

    Até 24/09/2026 o material chegava ao núcleo narrativo e nenhuma regra pedia que a missão
    trabalhasse os conceitos dele: o núcleo pegava o tema gerador e ignorava o resto. O mapa
    separa o conceito limiar (o que a virada precisa mudar no estudante) dos conceitos de apoio,
    e cita o trecho do material de onde cada um saiu — a citação é conferida em código.
    """
    return create_llm_agent(
        name="A002MapaConceitual",
        deterministico=True,  # extrai do material: mesma entrada, mesmo mapa
        description="Mapa conceitual do material do bimestre: conceito limiar, conceitos núcleo e de apoio com o trecho citado, crenças de entrada a derrubar e o vocabulário que o Explicar deve usar.",
        instruction=load_prompt("produto/002_mapa_conceitual.md"),
        output_key="mapa_conceitual",
        **kw,
    )


def get_ideacao_mecanismos_agent(**kw) -> LlmAgent:
    """Três mecanismos candidatos antes do núcleo: a primeira ideia de um modelo é a mais provável.

    Uma geração única devolve o esqueleto modal — escolher, comparar com colegas, revelar o
    escondido —, e o próprio one-pager v5 do 6º ano admitiu ter repetido o de "A Seleção". Aqui
    nascem três desenhos que diferem na decisão e na virada, pontuados na rubrica de profundidade.
    """
    return create_llm_agent(
        name="A003IdeacaoMecanismos",
        description="Ideação: três mecanismos distintos para o conceito limiar do material, cada um com a anatomia do aha, pontuados na rubrica de profundidade; indica qual o núcleo deve desenvolver.",
        instruction=load_prompt("produto/003_ideacao_mecanismos.md"),
        output_key="ideacao_mecanismos",
        # com o one-pager do PO anexado, o mecanismo é o dele: três candidatos novos puxavam o núcleo para longe
        before_agent_callback=dispensar_ideacao_com_one_pager_do_po,
        **kw,
    )


def get_juiz_profundidade_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A008JuizProfundidade",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Juiz de profundidade pedagógica: nota de 1 a 4 em seis dimensões (conceito do material vivido, aposta comprometida, ápice do aha, explicar depois de viver, transferência, demanda à altura do ano), com trecho citado e instrução de reescrita.",
        instruction=load_prompt("produto/008_juiz_profundidade.md"),
        output_key="profundidade_report",
        **kw,
    )


def get_nucleo_narrativo_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A004NucleoNarrativo",
        description="Núcleo narrativo da missão (seções 0, 1, 3 e 4): descoberta central, gap de informação, escolha significativa e as 6 etapas.",
        instruction=load_prompt("produto/004_nucleo_narrativo.md"),
        output_key="nucleo_narrativo",
        include_contents="default",  # único agente que vê a mensagem original e os anexos
        **kw,
    )


#: O brief de escopo começa por esta linha, fixada em `014_secoes_apoio.md`.
#: Em negrito, como o prompt mostra, ou como heading — as duas rodadas de 23/09 escreveram
#: `# MISSÃO DIGITAL…`, e o brief nunca era separado. A linha inteira é consumida.
BRIEF_ESCOPO_INICIO = r"^(?:#{1,6}\s*|\*\*)\s*MISS[ÃA]O DIGITAL UNOORIA\s*·\s*BRIEFING DE ESCOPO[^\n]*"


def get_brief_escopo_split() -> SecaoSplitAgent:
    """Separa o brief de escopo do one-pager antes que o revisor o apague.

    O A014 entrega DOIS documentos — one-pager canônico e brief de escopo — na mesma
    `output_key` (`one_pager`). O A07, logo a seguir, é instruído a devolver "apenas o
    one-pager revisado" na mesma chave: o brief evaporava a cada execução, sem erro e sem
    artefato, e ninguém percebia porque ele nunca foi gravado em disco. É o documento que
    existe justamente para quem não vai auditar critério por critério.
    """
    return SecaoSplitAgent(
        name="A018BriefEscopoSplit",
        description="Separa o brief de escopo do one-pager canônico para `brief_escopo`, antes do revisor.",
        rotulo="Brief de escopo",
        source_key="one_pager",
        status_key="brief_escopo_status",
        fonte_sem_veredito=True,
        extracoes=[
            {"chave": "brief_escopo", "inicio": BRIEF_ESCOPO_INICIO, "minimo_chars": 200,
             # sem brief a missão ainda se constrói, mas quem não audita critério por critério
             # fica sem o documento dele: ressalva visível, não bloqueio
             "ausencia_vira_ressalva": True},
        ],
    )


def get_micro_gate_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A007MicroGate",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Micro-gate do núcleo: spoiler (4 padrões), gap de informação real, escolha significativa e job-to-be-done no Desafiar.",
        instruction=load_prompt("produto/007_micro_gate.md"),
        output_key="micro_gate_report",
        **kw,
    )


def get_secoes_apoio_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A014SecoesApoio",
        description="Seções de apoio (2 e 5–18) e brief de escopo sobre o núcleo aprovado: completa o one-pager canônico que o gate estrutural audita.",
        instruction=load_prompt("produto/014_secoes_apoio.md"),
        output_key="one_pager",
        after_agent_callback=preservar_one_pager,
        **kw,
    )


def get_gate_estrutural_agent(max_rodadas: Optional[int] = None, **kw) -> LlmAgent:
    # O teto de rodadas do loop é escrito dentro do prompt: sem isso, a regra de parada
    # do gate promete uma rodada que o LoopAgent nunca executa (e vice-versa).
    rodadas = max_rodadas or get_settings().gate_estrutural_max_rodadas
    return create_llm_agent(
        name="A021GateEstrutural",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Gate estrutural: completude, ambiente, verbos nativos, logística, evidências e fechamento de spec.",
        instruction=load_prompt("produto/021_gate_estrutural.md", gate_max_rodadas=rodadas),
        output_key="gate_estrutural_report",
        **kw,
    )


def get_revisor_one_pager_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A023RevisorOnePager",
        description="Aplica ao one-pager as correções prontas do gate estrutural, sem inventar decisões de produto.",
        instruction=load_prompt("produto/revisor_one_pager.md"),
        output_key="one_pager",
        **kw,
    )


def get_restaurador_one_pager_po_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A032RestaurarOnePagerPo",
        description="Devolve ao one-pager os trechos do one-pager do PO que a esteira reescreveu sem pedido; o que um gate ou parecer pedia vira proposta ao PO.",
        instruction=load_prompt("produto/032_restaurar_one_pager_po.md"),
        output_key="one_pager",
        **kw,
    )


def get_one_pager_po_check(nome: str, estrito: bool) -> RastroCheckAgent:
    """One-pager do PO × one-pager gerado, trecho a trecho (`tools/one_pager_po.py`). Sem anexo, aprova sem custo."""
    return RastroCheckAgent(
        name=nome,
        description="Cada trecho do one-pager que o PO anexou está no one-pager gerado, ou saiu porque o pedido mandou (código removido ou alteração com o pedido citado).",
        modo="one_pager_po",
        rotulo="One-pager do PO preservado",
        report_key="one_pager_po_report",
        status_key="one_pager_po_status",
        agente="one-pager-do-po",
        estrito=estrito,
    )


#: Rodadas da conferência do one-pager do PO: a das seções de apoio e a final (uma restauração em cada uma).
ONE_PAGER_PO_RODADAS = 2


def get_avaliacao_pedagogica_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A024aAvaliacaoPedagogica",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Avaliação pedagógica: descoberta central, papel do professor, BNCC e guardrails éticos.",
        instruction=load_prompt("produto/024a_avaliacao_pedagogica.md"),
        output_key="avaliacao_pedagogica_report",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_adequacao_pedagogica_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A024cAdequacaoPedagogica",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Parecer de adequação pedagógica em seis eixos: alinhamento curricular, demanda cognitiva, carga acidental, viabilidade na escola pública, evidência de aprendizagem e equidade.",
        instruction=load_prompt("produto/024c_adequacao_pedagogica.md"),
        output_key="adequacao_report",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_experiencia_aluno_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A024bExperienciaEstudante",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Experiência do aluno por faixa etária: carga decisória, linguagem, duração e complexidade.",
        instruction=load_prompt("produto/024b_experiencia_estudante.md"),
        output_key="experiencia_aluno_report",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_gate_final_produto_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A033GateFinalProduto",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Gate final de produto: coerência entre missão e vereditos; libera ou bloqueia para design/dev.",
        instruction=load_prompt("produto/033_gate_final.md"),
        output_key="gate_final_report",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_spec_missao_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A035SpecMissao",
        description="Traduz o one-pager aprovado na especificação de missão (12 blocos) — o contrato da construção.",
        instruction=load_prompt("produto/035_spec_missao.md"),
        output_key="spec_missao",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_one_pager_resumido_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A051OnePagerResumido",
        description="One-pager resumido para avaliação pedagógica, no formato do time de produto: ficha, ideia em prosa, componente curricular, socioemocionais, 6 etapas, professor, contrato de evidência ternário por habilidade e takeaway. Condensa o canônico e a spec aprovados; não decide nada novo.",
        instruction=load_prompt("produto/051_one_pager_resumido.md"),
        output_key="one_pager_resumido",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def _resumido_loop(kw: dict, settings) -> LoopAgent:
    """O resumido ↔ conferência contra o canônico aprovado.

    O resumido é o que o time de produto lê para aprovar a missão; o canônico é o que segue para design e dev.
    Até 07/10/2026 nada os comparava: em 7 das 15 sessões do bucket o resumido não trazia o Canal B com o texto
    aprovado, e numa delas declarava outro tempo em tela.
    """
    rodadas = max(1, settings.spec_max_rodadas)
    return LoopAgent(
        name="OnePagerResumidoLoop",
        description="One-pager resumido ↔ conferência contra o one-pager canônico aprovado, até bater ou esgotar as rodadas.",
        max_iterations=rodadas,
        before_agent_callback=marcar_heranca,
        sub_agents=[
            get_one_pager_resumido_agent(**kw),
            RastroCheckAgent(
                name="A052ConteudoAprovadoResumido",
                description="One-pager resumido × canônico aprovado e spec: as habilidades do bloco 11, o tempo em tela do §10 e o Canal B com o texto do §12a. Divergência volta ao autor do resumido.",
                modo="aprovado_resumido",
                rotulo="Resumido × one-pager aprovado",
                report_key="conteudo_aprovado_resumido_report",
                status_key="conteudo_aprovado_resumido_status",
                agente="conteudo-aprovado",
                estrito=settings.esteira_estrita,
                before_agent_callback=marcar_heranca,
            ),
            SaidaDeLoopAgent(
                name="A053ResumidoRodada",
                description="Resumido fiel ao canônico encerra o loop; divergente volta ao autor com o relatório.",
                rotulo="One-pager resumido",
                status_keys=["conteudo_aprovado_resumido_status"],
                rodada_key="resumido_rodada",
                max_rounds=rodadas,
                autor_keys=["one_pager_resumido"],
            ),
        ],
    )


def get_vizinhas_catalogo_agent(nome: str) -> VizinhasCatalogoAgent:
    """Missões já geradas mais próximas desta. Roda em duas posições: antes do núcleo (filtrando
    pelo briefing) e depois dele, dentro do loop (filtrando pelo que a missão é) — só a segunda
    serve à verificação V5 do micro-gate."""
    return VizinhasCatalogoAgent(
        name=nome,
        description="Recupera do índice as missões já geradas mais próximas desta, para o autor do núcleo não repetir e o micro-gate julgar. Determinístico.",
    )


def get_juiz_perguntas_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A041JuizPerguntas",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Juiz das cinco perguntas de produto do 9f: cada uma muda uma decisão nossa, é sobre o produto e não sobre a criança, e a ação nomeada a responde.",
        instruction=load_prompt("produto/041_juiz_perguntas.md"),
        output_key="juiz_perguntas_report",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def _build_spec_loop(kw: dict, settings, rodadas_spec: int) -> LoopAgent:
    """Spec da missão ↔ BNCC e ficha do manifesto. Usado pela etapa inteira e pela correção a partir da spec."""
    return LoopAgent(
        name="SpecLoop",
        description="Spec da missão ↔ conformidade curricular e ficha do manifesto, até passar ou esgotar as rodadas.",
        max_iterations=rodadas_spec,
        sub_agents=[
            get_spec_missao_agent(**kw),
            BnccCheckAgent(
                name="A036BnccCheck",
                description="Confere o bloco 11 da spec contra a lista oficial da BNCC Computação: código existe, é do ano da missão e há letramento digital.",
                estrito=settings.bncc_check_estrito,
                before_agent_callback=marcar_heranca,
            ),
            RastroCheckAgent(
                name="A037ManifestoCheckProduto",
                description="Ficha do manifesto no bloco 0 da spec, conferida ainda em Produto: campo fora do vocabulário fechado volta para quem escreveu a spec.",
                modo="manifesto",
                rotulo="Ficha do manifesto (produto)",
                report_key="manifesto_report",
                status_key="manifesto_status",
                estrito=settings.esteira_estrita,
                before_agent_callback=marcar_heranca,
            ),
            RastroCheckAgent(
                name="A038EvidenciaCheck",
                description="Matriz de evidência pedagógica: grau `scored` com dois sinais, toda habilidade do bloco 11 com momento em tela e medida do bloco 9, gabarito declarado no servidor.",
                modo="evidencia",
                rotulo="Matriz de evidência pedagógica",
                report_key="evidencia_report",
                status_key="evidencia_status",
                estrito=settings.esteira_estrita,
                before_agent_callback=marcar_heranca,
            ),
            get_juiz_de_achados("A039JuizEvidencia", status_key="evidencia_status", report_key="evidencia_report",
                                fonte_key="spec_missao", gate_rotulo="Matriz de evidência pedagógica", **kw),
            RastroCheckAgent(
                name="A040PerguntasCheck",
                description="Sub-bloco 9f: cinco perguntas de produto, cada uma com decisão que tem limiar, corte válido e uma ação declarada na tabela de eventos que a responde com número.",
                modo="perguntas",
                rotulo="Perguntas de produto (9f)",
                report_key="perguntas_report",
                status_key="perguntas_status",
                estrito=settings.esteira_estrita,
                before_agent_callback=marcar_heranca,
            ),
            get_juiz_perguntas_agent(**kw),
            EnvelopeGateAgent(
                name="A042JuizPerguntasCheck",
                documentos=["spec_missao", "perguntas_po"],  # citação dos bloqueios conferida em código (`tools/citacoes.py`)
                report_key="juiz_perguntas_report",
                status_key="juiz_perguntas_status",
                rotulo="Juiz das perguntas de produto",
                round_key="juiz_perguntas_rodada",
                max_rounds=rodadas_spec,
                block_pipeline_on_fail=settings.esteira_estrita,
            ),
            # O rastro de lacunas só rodava em dev, e uma pendência de produto que a spec deixou
            # barrava o PRD numa etapa que não reescreve a spec (exp04ef1b, 25/09/2026). Aqui ela
            # volta para quem a escreveu, e a decisão do PO aparece no semáforo do parecer.
            RastroCheckAgent(
                name="A043RastroSpec",
                description="Marcadores de lacuna na spec: pendência de produto ou de insumo volta para quem escreveu a spec; decisão do PO fica 🟡 no parecer; a de design e a de dev ficam para a etapa delas.",
                modo="lacunas",
                rotulo="Rastro de lacunas da spec",
                report_key="rastro_spec_report",
                status_key="rastro_spec_status",
                fontes=FONTES_SPEC,
                etapa="produto",
                agente="rastro-lacunas-spec",
                estrito=settings.esteira_estrita,
                before_agent_callback=marcar_heranca,
            ),
            # A spec traduz o one-pager aprovado. Até 06/10/2026 ela aplicava as ressalvas dos pareceres
            # que o PO não tinha incorporado — a exp06ef1b perdeu a EF06CO07 e foi de 29 para 24 min em
            # tela —, e tudo a jusante seguia a spec sem nenhum gate ver.
            RastroCheckAgent(
                name="A044ConteudoAprovadoSpec",
                description="Spec × one-pager aprovado: as habilidades do contrato de evidência (§12a), o tempo total em tela (§10) e o podcast (§11). Divergência volta ao autor da spec.",
                modo="aprovado_spec",
                rotulo="Spec × one-pager aprovado",
                report_key="conteudo_aprovado_spec_report",
                status_key="conteudo_aprovado_spec_status",
                agente="conteudo-aprovado",
                estrito=settings.esteira_estrita,
                before_agent_callback=marcar_heranca,
            ),
            # A banca no fim de produto (dimensões de produto e pedagogia), antes do parecer do PO: o achado volta ao
            # autor da spec na próxima rodada. A mesma banca roda de novo na entrada do dev (decisão de 08/10/2026).
            *get_banca("produto", "AC", 45, rotulo="Banca de produto",
                       titulo="Banca de validação — fim de produto",
                       report_key="banca_produto_report", status_key="banca_produto_status", **kw),
            SaidaDeLoopAgent(
                name="A049SpecCheck",
                description="Currículo, manifesto, matriz de evidência, perguntas de produto, lacunas e fidelidade ao one-pager aprovado conformes encerram o loop; reprovados devolvem a spec ao autor com os relatórios.",
                rotulo="Spec da missão",
                status_keys=["bncc_status", "manifesto_status", "evidencia_status",
                             "perguntas_status", "juiz_perguntas_status", "rastro_spec_status",
                             "conteudo_aprovado_spec_status", "banca_produto_status"],
                rodada_key="spec_rodada",
                max_rounds=rodadas_spec,
                autor_keys=["spec_missao"],
            ),
        ],
    )


def build_produto_stage(
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
    modo_estrito: Optional[bool] = None,
    max_rodadas: Optional[int] = None,
    a_partir_de: Optional[str] = None,
) -> SequentialAgent:
    """Monta a etapa de Produto como SequentialAgent aninhado.

    `a_partir_de="spec"` monta só o fim da etapa — SpecLoop e one-pager resumido — para o modo
    correção: núcleo, one-pager e gates da execução anterior ficam como estão no estado.
    """
    settings = get_settings()
    estrito = settings.produto_modo_estrito if modo_estrito is None else modo_estrito
    rodadas = max(1, max_rodadas or settings.gate_estrutural_max_rodadas)
    rodadas_spec = max(1, settings.spec_max_rodadas)
    rodadas_avaliacoes = max(1, settings.avaliacoes_max_rodadas)
    kw = {"thinking_budget": thinking_budget, "include_thoughts": include_thoughts}

    if a_partir_de is not None:
        if a_partir_de != "spec":
            raise ValueError(f"a_partir_de inválido: {a_partir_de!r} (só 'spec' é suportado)")
        return SequentialAgent(
            name="ProdutoStage",
            description="Área de Produto — correção a partir da spec: spec ↔ currículo e manifesto → one-pager resumido (núcleo, one-pager e gates preservados da execução anterior).",
            sub_agents=[_build_spec_loop(kw, settings, rodadas_spec), _fidelidade_de_produto(kw),
                        _resumido_loop(kw, settings)],
        )

    nucleo_loop = LoopAgent(
        name="NucleoNarrativoLoop",
        description="Núcleo narrativo ↔ micro-gate de spoiler/gap e juiz de profundidade até os dois passarem ou esgotar as rodadas.",
        max_iterations=MICRO_GATE_MAX_RODADAS,
        sub_agents=[
            get_nucleo_narrativo_agent(**kw),
            # Depois do núcleo: refiltra o índice pelo que a missão de fato é (ambiente, eixo,
            # descoberta). É esta lista que a verificação V5 do micro-gate julga, e é ela que o
            # autor relê na segunda rodada quando V5 reprova.
            get_vizinhas_catalogo_agent("A005VizinhasCatalogo"),
            CoberturaConceitualAgent(
                name="A006CoberturaConceitual",
                description="Núcleo × mapa conceitual: o limiar vive no Decidir ou no aha, todo conceito núcleo tem destino, a anatomia do aha tem os seis passos e a citação do mapa existe no material. Determinístico.",
            ),
            get_micro_gate_agent(**kw),
            get_juiz_profundidade_agent(**kw),
            # Antes do veredito do micro-gate, de propósito: esgotada a última rodada, o
            # `A012MicroGateCheck` encerra o loop, e a profundidade da rodada ficaria sem status.
            # O núcleo é onde a missão do 9º ano trocou A e B e cortou a frase do PO (30/09/2026):
            # conferido aqui, a cada rodada, o autor recebe o relatório e reescreve antes de seguir.
            MecanicaCheckAgent(
                name="A009ContaDaVirada",
                description="Refaz em código o ranking da tabela 1.3 (antes e depois do dado que faltava): o vencedor calculado tem de ser o declarado, e os dois têm de ser diferentes.",
            ),
            get_fidelidade_check("A010FidelidadeNucleo", status_key="fidelidade_nucleo_status",
                                 report_key="fidelidade_nucleo_report", documentos=["nucleo_narrativo"],
                                 onde="núcleo", etapas_pedido=list(ETAPAS_DO_PEDIDO_DE_PRODUTO), parcial=True, **kw),
            ProfundidadeCheckAgent(
                name="A011ProfundidadeCheck",
                max_rounds=MICRO_GATE_MAX_RODADAS,
                description="Conta o veredito de profundidade nas notas do juiz e funde a cobertura conceitual: 🔴 com P1, P2 ou P3 abaixo de 3 ou qualquer dimensão em 1.",
            ),
            EnvelopeGateAgent(
                name="A012MicroGateCheck",
                documentos=["nucleo_narrativo"],  # citação dos bloqueios conferida em código (`tools/citacoes.py`)
                description="Lê o envelope do micro-gate: aprovado segue para as seções de apoio, reprovado devolve o núcleo ao P0a.",
                rotulo="Micro-gate do núcleo",
                report_key="micro_gate_report",
                status_key="micro_gate_status",
                round_key="micro_gate_rodada",
                max_rounds=MICRO_GATE_MAX_RODADAS,
                # Quem encerra o loop é o `A013NucleoCheck`: spoiler resolvido com missão rasa
                # não é núcleo pronto.
                escalate_on_approve=False,
                # Quem bloqueia a missão é o gate estrutural (P1). O micro-gate esgotado
                # segue adiante com o achado registrado — o problema é de mecanismo e o P1 o audita.
                block_pipeline_on_fail=False,
            ),
            SaidaDeLoopAgent(
                name="A013NucleoCheck",
                description="Micro-gate e profundidade aprovados encerram o loop; qualquer um reprovado devolve o núcleo ao P0a com os dois relatórios.",
                rotulo="Núcleo narrativo",
                status_keys=["micro_gate_status", "profundidade_status", "fidelidade_nucleo_status", "mecanica_status"],
                rodada_key="nucleo_rodada",
                max_rounds=MICRO_GATE_MAX_RODADAS,
            ),
        ],
    )

    gate_loop = LoopAgent(
        name="GateEstruturalLoop",
        description="Gate estrutural ↔ revisor do one-pager até aprovar ou esgotar as rodadas.",
        max_iterations=rodadas,
        sub_agents=[
            # O brief de escopo sai do `one_pager` ANTES do gate e do revisor: o A014 entrega os
            # dois documentos na mesma chave e o A07 devolve só o one-pager revisado, então o
            # brief evaporava a cada execução — sem erro, sem artefato, sem ninguém notar.
            get_brief_escopo_split(),
            # Antes do gate, a cada rodada: WebSocket como canal de sala, estado em
            # `localStorage`, SAEB fora do ano e número sem origem nasciam aqui e só eram pegos
            # duas etapas depois (A091) ou nunca. O lint não bloqueia sozinho — o gate aplica.
            RastroCheckAgent(
                name="A019ContratoProdutoCheck",
                description="Contrato de plataforma e origem dos parâmetros no one-pager: canal de sala por polling, estado no servidor, SAEB só nos anos avaliados, número com origem ou marcador. Alimenta o gate estrutural.",
                modo="one_pager",
                rotulo="Contrato de plataforma e origem dos parâmetros",
                report_key="contrato_produto_report",
                status_key="contrato_produto_status",
                estrito=False,
            ),
            get_juiz_de_achados("A020JuizContratoProduto", status_key="contrato_produto_status",
                                report_key="contrato_produto_report", fonte_key="one_pager",
                                gate_rotulo="Contrato de plataforma e origem dos parâmetros", **kw),
            get_gate_estrutural_agent(max_rodadas=rodadas, **kw),
            EnvelopeGateAgent(
                name="A022GateEstruturalCheck",
                documentos=["one_pager", "brief_escopo", "briefing"],  # citação dos bloqueios conferida em código (`tools/citacoes.py`)
                description="Lê o envelope do gate estrutural e decide repetir, seguir ou bloquear.",
                rotulo="Gate estrutural",
                report_key="gate_estrutural_report",
                status_key="gate_estrutural_status",
                round_key="gate_estrutural_rodada",
                max_rounds=rodadas,
                escalate_on_approve=True,
                block_pipeline_on_fail=estrito,
            ),
            get_revisor_one_pager_agent(**kw),
        ],
    )

    # O revisor do one-pager vive no loop do gate estrutural, que fecha ANTES das avaliações —
    # então o parecer de adequação chegaria a ele com o one-pager já congelado. Este segundo
    # ciclo resolve: avalia, e se o parecer pede ajuste, o revisor aplica e as avaliações
    # refazem sobre a versão nova. Ligado por padrão (teto 2) desde 07/10/2026: com teto 1 o ajuste
    # exigido nunca era aplicado e o gate final reprovava a missão por ele (exp03ef1b). Custa
    # reexecutar os três avaliadores só quando o parecer exige ajuste.
    revisor_pos_parecer = get_revisor_one_pager_agent(**kw)
    revisor_pos_parecer.name = "A029RevisorOnePagerParecer"
    revisor_pos_parecer.description = (
        f"{revisor_pos_parecer.description} (rodada movida pelo parecer de adequação pedagógica)"
    )

    avaliacoes = ParallelAgent(
        name="AvaliacoesParalelas",
        description="Avaliação pedagógica, experiência do estudante e adequação pedagógica rodam em paralelo sobre a mesma versão da missão.",
        sub_agents=[
            get_avaliacao_pedagogica_agent(**kw),
            get_experiencia_aluno_agent(**kw),
            get_adequacao_pedagogica_agent(**kw),
        ],
        before_agent_callback=marcar_heranca,
    )

    # A spec é o contrato que design e dev consomem, e os dois gates que a auditam são
    # determinísticos e baratos: currículo (BNCC) e ficha do manifesto. Antes, o manifesto
    # só era conferido no começo do dev — duas etapas depois de quem o escreveu, quando o
    # conserto já custava descartar o design inteiro. Aqui o autor da spec reescreve na hora.
    spec_loop = _build_spec_loop(kw, settings, rodadas_spec)

    avaliacoes_loop = LoopAgent(
        name="AvaliacoesLoop",
        description="Avaliações em paralelo ↔ revisor do one-pager, quando o parecer de adequação pede ajuste.",
        max_iterations=rodadas_avaliacoes,
        before_agent_callback=marcar_heranca,
        sub_agents=[
            avaliacoes,
            # Os três relatórios pedagógicos produziam veredito e NINGUÉM o lia: não havia
            # `*_status` para eles em `tools/diagnostico.py`, e o `adequacao_status` que o
            # `A028AdequacaoCheck` consultava nunca era escrito por agente nenhum — o loop
            # encerrava com aprovação sobre uma chave inexistente. Em 14 execuções, o parecer
            # de adequação emitiu 40 achados de conteúdo real e nenhum foi fechado.
            EnvelopeGateAgent(
                name="A025AvaliacaoCheck",
                documentos=["one_pager", "brief_escopo", "material_anexado"],  # citação dos bloqueios conferida em código (`tools/citacoes.py`)
                description="Lê o veredito da avaliação pedagógica (critérios 4.x, 5.1/5.2, 8.x).",
                rotulo="Avaliação pedagógica",
                report_key="avaliacao_pedagogica_report",
                status_key="avaliacao_status",
                block_pipeline_on_fail=estrito,
            ),
            EnvelopeGateAgent(
                name="A026ExperienciaCheck",
                documentos=["one_pager", "brief_escopo"],  # citação dos bloqueios conferida em código (`tools/citacoes.py`)
                description="Lê o veredito da experiência do estudante (3.x, 6.x). Sinaliza, não trava: os tetos desta dimensão são [EXTRAPOLAÇÃO], não medida.",
                rotulo="Experiência do estudante",
                report_key="experiencia_aluno_report",
                status_key="experiencia_status",
                block_pipeline_on_fail=False,
            ),
            EnvelopeGateAgent(
                name="A027AdequacaoCheck",
                documentos=["one_pager", "brief_escopo", "material_anexado"],  # citação dos bloqueios conferida em código (`tools/citacoes.py`)
                description="Lê o veredito do parecer de adequação pedagógica.",
                rotulo="Adequação pedagógica",
                report_key="adequacao_report",
                status_key="adequacao_status",
                block_pipeline_on_fail=False,
            ),
            SaidaDeLoopAgent(
                name="A028AdequacaoCheck",
                description="Parecer sem ajuste exigido encerra o loop; com ajuste, o revisor aplica e as avaliações refazem.",
                rotulo="Adequação pedagógica",
                status_keys=["adequacao_status", "avaliacao_status"],
                rodada_key="avaliacoes_rodada",
                max_rounds=rodadas_avaliacoes,
                # `""` saiu da lista: era o que fazia a chave nunca escrita valer aprovação.
                aceitos=["aprovado", "aprovado_com_ressalvas", "amarelo"],
                # com ressalvas, mas com ajuste exigido, o revisor aplica antes do gate final
                envelope_exige={"adequacao_status": "ajustes_exigidos"},
            ),
            revisor_pos_parecer,
        ],
    )

    # O one-pager que o PO anexou é a missão: o A014 parte dele e a conferência devolve ao A014 o que ele reescreveu.
    # Sem anexo, a conferência aprova e o loop sai na primeira rodada, sem custo.
    secoes_apoio_loop = LoopAgent(
        name="SecoesApoioLoop",
        description="Seções de apoio ↔ conferência do one-pager do PO, quando ele anexou um.",
        max_iterations=ONE_PAGER_PO_RODADAS,
        sub_agents=[
            get_secoes_apoio_agent(**kw),
            # dentro do loop não bloqueia: quem registra o 🔴 é a conferência final, depois de revisores e pareceres
            get_one_pager_po_check("A015OnePagerPoCheck", estrito=False),
            SaidaDeLoopAgent(
                name="A016SecoesApoioRodada",
                description="One-pager do PO preservado encerra o loop; trecho perdido volta ao A014 com a lista.",
                rotulo="Seções de apoio × one-pager do PO",
                status_keys=["one_pager_po_status"],
                rodada_key="secoes_apoio_rodada",
                max_rounds=ONE_PAGER_PO_RODADAS,
                autor_keys=["one_pager"],
            ),
        ],
    )

    # Depois de gate estrutural, pareceres e revisores — os que reescreviam o one-pager do PO na exp06ef1b
    # (08/10/2026). Trecho perdido vai ao restaurador; o que um parecer pedia vira proposta ao PO.
    one_pager_po_loop = LoopAgent(
        name="OnePagerPoLoop",
        description="Conferência final do one-pager do PO ↔ restaurador, antes do gate final.",
        max_iterations=ONE_PAGER_PO_RODADAS,
        sub_agents=[
            get_one_pager_po_check("A030OnePagerPoCheck", estrito=settings.esteira_estrita),
            SaidaDeLoopAgent(
                name="A031OnePagerPoRodada",
                description="One-pager do PO preservado segue para o gate final; trecho perdido vai ao restaurador.",
                rotulo="One-pager do PO",
                status_keys=["one_pager_po_status"],
                rodada_key="one_pager_po_rodada",
                max_rounds=ONE_PAGER_PO_RODADAS,
                autor_keys=["one_pager"],
            ),
            get_restaurador_one_pager_po_agent(**kw),
        ],
    )

    return SequentialAgent(
        name="ProdutoStage",
        description="Área de Produto: núcleo narrativo ↔ micro-gate → seções de apoio → gate estrutural → avaliações → gate final → spec da missão ↔ currículo e manifesto → one-pager resumido.",
        sub_agents=[
            # Antes de inventar: o que já existe no ano, lido do índice pelo briefing. Sem isto, a
            # primeira geração nasce cega e a repetição só apareceria na segunda rodada do loop.
            get_vizinhas_catalogo_agent("A001VizinhasCatalogo"),
            # Antes de inventar, também: o que o material do bimestre ensina, e três desenhos
            # candidatos para o conceito central dele. O núcleo desenvolve um, não improvisa.
            get_mapa_conceitual_agent(**kw),
            get_ideacao_mecanismos_agent(**kw),
            nucleo_loop,
            secoes_apoio_loop,
            DocumentoObrigatorioAgent(name="A017OnePagerExiste", chave="one_pager", autor="A014SecoesApoio",
                                      description="Sem one-pager depois de duas tentativas do A014, a etapa para com mensagem legível."),
            gate_loop,
            avaliacoes_loop,
            one_pager_po_loop,
            get_gate_final_produto_agent(**kw),
            EnvelopeGateAgent(
                name="A034GateFinalProdutoCheck",
                documentos=["one_pager", "brief_escopo", "gate_estrutural_report", "avaliacao_pedagogica_report", "experiencia_aluno_report", "adequacao_report"],  # citação dos bloqueios conferida em código (`tools/citacoes.py`)
                description="Lê o veredito do gate final de produto (🟢 liberada / 🔴 bloqueada).",
                rotulo="Gate final de produto",
                report_key="gate_final_report",
                status_key="gate_final_status",
                block_pipeline_on_fail=estrito,
            ),
            spec_loop,
            _fidelidade_de_produto(kw),
            # Depois da spec, de propósito: o bloco 11 já passou pelo A036, então o resumido
            # copia códigos conferidos em vez dos que a seção 2 do canônico ainda podia trocar.
            _resumido_loop(kw, settings),
        ],
    )


def _fidelidade_de_produto(kw: Dict[str, Any]):
    """A conferência final: núcleo, one-pager e spec contra todos os pedidos do PO e o briefing.
    Com 🔴 aqui, o *de acordo* de produto é recusado (`pipeline/passagem.py`)."""
    return get_fidelidade_check("A050FidelidadeProduto", status_key="fidelidade_status", report_key="fidelidade_report",
                                documentos=["nucleo_narrativo", "one_pager", "spec_missao"],
                                onde="fim de produto", etapas_pedido=list(ETAPAS_DO_PEDIDO_DE_PRODUTO), **kw)


#: Os pedidos de refazer que produto confere: os de produto e os registros antigos, sem etapa. O pedido feito a
#: design ou a dev é conferido no fim daquela etapa (A084, A51): aqui ele reprovava o núcleo por um botão de tela.
ETAPAS_DO_PEDIDO_DE_PRODUTO = ("produto", "")


#: Agentes do estágio parcial "spec" (correção a partir da spec), na ordem em que rodam.
SPEC_AGENT_IDS = ["A035SpecMissao", "A036BnccCheck", "A037ManifestoCheckProduto", "A038EvidenciaCheck",
                  "A040PerguntasCheck", "A041JuizPerguntas", "A042JuizPerguntasCheck",
                  "A044ConteudoAprovadoSpec", "A047aBancaProdutoNarrativa", "A047bBancaPedagogiaBncc",
                  "A048BancaConsolidacao", "A049SpecCheck", "A050FidelidadeProduto", "A051OnePagerResumido",
                  "A052ConteudoAprovadoResumido", "A053ResumidoRodada"]

PRODUTO_METADATA = [
    {"id": "A001VizinhasCatalogo", "name": "001 · Missões já geradas (determinístico)", "icon": "🗂️", "output_key": "missoes_vizinhas", "prompt_file": None, "description": "Lê o índice de missões e entrega ao núcleo as mais próximas do ano do briefing, para a missão nova não repetir uma anterior."},
    {"id": "A002MapaConceitual", "name": "002 · Mapa conceitual do material", "icon": "🧭", "output_key": "mapa_conceitual", "prompt_file": "produto/002_mapa_conceitual.md", "description": "Lê o material do bimestre antes de inventar: um conceito limiar, os conceitos núcleo e de apoio com o trecho citado, as crenças de entrada que o bimestre derruba e o vocabulário do Explicar."},
    {"id": "A003IdeacaoMecanismos", "name": "003 · Ideação de mecanismos", "icon": "💡", "output_key": "ideacao_mecanismos", "prompt_file": "produto/003_ideacao_mecanismos.md", "description": "Três mecanismos distintos para o conceito limiar, cada um com a anatomia do aha, pontuados na rubrica de profundidade. O núcleo desenvolve o escolhido."},
    {"id": "A004NucleoNarrativo", "name": "004 · Núcleo narrativo", "icon": "🎬", "output_key": "nucleo_narrativo", "prompt_file": "produto/004_nucleo_narrativo.md", "description": "Seções 0, 1, 3 e 4 a partir do briefing, dos anexos, do mapa conceitual e do mecanismo escolhido: descoberta, conceitos vividos em tela, anatomia do aha, narrativa e as 6 etapas."},
    {"id": "A005VizinhasCatalogo", "name": "005 · Missões já geradas, pelo núcleo (determinístico)", "icon": "🗂️", "output_key": "missoes_vizinhas", "prompt_file": None, "description": "Refiltra o índice pelo ambiente, eixo e descoberta do núcleo recém-escrito. É esta lista que a verificação V5 do micro-gate julga."},
    {"id": "A006CoberturaConceitual", "name": "006 · Cobertura conceitual (determinístico)", "icon": "🧩", "output_key": "cobertura_report", "prompt_file": None, "description": "Núcleo × mapa: o limiar vive no Decidir ou no aha, todo conceito núcleo tem destino, a anatomia do aha tem os seis passos e o trecho citado pelo mapa existe no material."},
    {"id": "A007MicroGate", "name": "007 · Micro-gate do núcleo", "icon": "🕵️", "output_key": "micro_gate_report", "prompt_file": "produto/007_micro_gate.md", "description": "Spoiler, gap de informação, escolha significativa e job-to-be-done — binário, até 2 rodadas."},
    {"id": "A008JuizProfundidade", "name": "008 · Juiz de profundidade", "icon": "🎯", "output_key": "profundidade_report", "prompt_file": "produto/008_juiz_profundidade.md", "description": "Nota de 1 a 4 em seis dimensões — conceito do material vivido, aposta comprometida, ápice do aha, explicar depois de viver, transferência e demanda à altura do ano —, com trecho citado e instrução de reescrita."},
    {"id": "A009ContaDaVirada", "name": "009 · Conta da virada (determinístico)", "icon": "🧮", "output_key": "mecanica_report", "prompt_file": None, "description": "Refaz o ranking da tabela 1.3 do núcleo: normaliza cada critério, aplica os pesos e confere que o vencedor antes e o depois são os declarados — e diferentes. Pega a virada que não fecha (o custo por vaga da exp09ef1b)."},
    {"id": "A010FidelidadeNucleo", "name": "010 · Fidelidade ao pedido do PO (núcleo)", "icon": "📌", "output_key": "fidelidade_nucleo_report", "prompt_file": None, "description": "O núcleo contra todos os pedidos de refazer do PO (TRAVAS, AJUSTES, VALIDAÇÃO, frases entre aspas) e o briefing: o juiz cita, o código confere. Parcial: o núcleo não tem as outras seções, então item sem prova é 🟡 e só o pedido violado (🔴) devolve o núcleo ao autor; a prova é cobrada no 16c."},
    {"id": "A011ProfundidadeCheck", "name": "011 · Veredito de profundidade (determinístico)", "icon": "🔀", "output_key": "profundidade_status", "prompt_file": None, "description": "Conta o veredito nas notas do juiz, não no que ele escreveu: P1, P2 ou P3 abaixo de 3 é 🔴. Funde a cobertura conceitual."},
    {"id": "A012MicroGateCheck", "name": "012 · Veredito do micro-gate (determinístico)", "icon": "🔀", "output_key": "micro_gate_status", "prompt_file": None, "description": "Lê o envelope do micro-gate e registra se o núcleo passou em spoiler, gap, escolha e job."},
    {"id": "A013NucleoCheck", "name": "013 · Saída do loop do núcleo (determinístico)", "icon": "🔀", "output_key": "nucleo_rodada", "prompt_file": None, "description": "Micro-gate e profundidade aprovados encerram o loop; qualquer um reprovado devolve o núcleo ao P0a com os dois relatórios."},
    {"id": "A014SecoesApoio", "name": "014 · Seções de apoio e brief", "icon": "📝", "output_key": "one_pager", "prompt_file": "produto/014_secoes_apoio.md", "description": "Completa o one-pager canônico (seções 2 e 5–18) e o brief de escopo sobre o núcleo aprovado."},
    {"id": "A015OnePagerPoCheck", "name": "015 · One-pager do PO preservado (determinístico)", "icon": "📌", "output_key": "one_pager_po_report", "prompt_file": None, "description": "Quando o PO anexou o one-pager: cada trecho dele (linha e célula de tabela) está no one-pager das seções de apoio, ou saiu porque o pedido mandou. Trecho perdido volta ao A014 com a lista. Sem anexo, não se aplica."},
    {"id": "A016SecoesApoioRodada", "name": "016 · Saída das seções de apoio (determinístico)", "icon": "🔀", "output_key": "secoes_apoio_rodada", "prompt_file": None, "description": "One-pager do PO preservado encerra o loop das seções de apoio; trecho perdido devolve ao A014."},
    {"id": "A017OnePagerExiste", "name": "017 · One-pager existe (determinístico)", "icon": "🧱", "output_key": None, "prompt_file": None, "description": "Se o A014 terminou sem texto nas duas tentativas, a etapa para aqui com uma mensagem que diz quem ficou mudo — antes, o gate estrutural quebrava com «Context variable not found»."},
    {"id": "A018BriefEscopoSplit", "name": "018 · Brief de escopo separado (determinístico)", "icon": "🔀", "output_key": "brief_escopo_status", "prompt_file": None, "description": "Separa o brief de escopo do one-pager canônico para `brief_escopo`, antes do revisor."},
    {"id": "A019ContratoProdutoCheck", "name": "019 · Contrato de plataforma e origem dos parâmetros (determinístico)", "icon": "📡", "output_key": "contrato_produto_report", "prompt_file": None, "description": "Lint do one-pager a cada rodada do gate: canal de sala por polling (nunca WebSocket), estado no servidor (sem localStorage/IndexedDB), SAEB só nos anos avaliados, número com origem ou marcador. O gate aplica; o revisor corrige."},
    {"id": "A020JuizContratoProduto", "name": "020 · Juiz do contrato de produto", "icon": "⚖️", "output_key": "contrato_produto_status", "prompt_file": None, "description": "Juiz de achados sobre `Contrato de plataforma e origem dos parâmetros`: retira o achado de uso vedado quando o texto só cita para vedar — com citação literal conferida."},
    {"id": "A021GateEstrutural", "name": "021 · Gate estrutural", "icon": "🚧", "output_key": "gate_estrutural_report", "prompt_file": "produto/021_gate_estrutural.md", "description": "critérios: estrutura, ambiente, logística, evidências, viabilidade e infraestrutura."},
    {"id": "A022GateEstruturalCheck", "name": "022 · Veredito do gate (determinístico)", "icon": "🔀", "output_key": "gate_estrutural_status", "prompt_file": None, "description": "Lê o envelope JSON e decide repetir, seguir ou bloquear."},
    {"id": "A023RevisorOnePager", "name": "023 · Revisor do one-pager", "icon": "🩹", "output_key": "one_pager", "prompt_file": "produto/revisor_one_pager.md", "description": "Aplica o complemento pronto-pra-colar do gate; não inventa decisão de produto."},
    {"id": "A024aAvaliacaoPedagogica", "name": "024a · Avaliação pedagógica", "icon": "🎓", "output_key": "avaliacao_pedagogica_report", "prompt_file": "produto/024a_avaliacao_pedagogica.md", "description": "BNCC, professor, guardrails e affordance × guardrail (paralelo com P3)."},
    {"id": "A024bExperienciaEstudante", "name": "024b · Experiência do estudante", "icon": "🧒", "output_key": "experiencia_aluno_report", "prompt_file": "produto/024b_experiencia_estudante.md", "description": "Carga cognitiva, faixa etária e agência (paralelo com P2)."},
    {"id": "A024cAdequacaoPedagogica", "name": "024c · Adequação pedagógica", "icon": "⚖️", "output_key": "adequacao_report", "prompt_file": "produto/024c_adequacao_pedagogica.md", "description": "Seis eixos com parecer e ajustes acionáveis: currículo, demanda cognitiva, carga acidental, viabilidade na escola pública, evidência de aprendizagem e equidade. Parecer entra como ressalva, não bloqueia."},
    {"id": "A025AvaliacaoCheck", "name": "025 · Veredito da avaliação pedagógica (determinístico)", "icon": "🔀", "output_key": "avaliacao_status", "prompt_file": None, "description": "Lê o veredito da avaliação pedagógica (critérios 4.x, 5.1/5.2, 8.x)."},
    {"id": "A026ExperienciaCheck", "name": "026 · Veredito da experiência do estudante (determinístico)", "icon": "🔀", "output_key": "experiencia_status", "prompt_file": None, "description": "Lê o veredito da experiência do estudante (3.x, 6.x). Sinaliza, não trava: os tetos desta dimensão são [EXTRAPOLAÇÃO], não medida."},
    {"id": "A027AdequacaoCheck", "name": "027 · Veredito da adequação pedagógica (determinístico)", "icon": "🔀", "output_key": "adequacao_status", "prompt_file": None, "description": "Lê o veredito do parecer de adequação pedagógica."},
    {"id": "A028AdequacaoCheck", "name": "028 · Veredito do parecer (determinístico)", "icon": "🔀", "output_key": "avaliacoes_rodada", "prompt_file": None, "description": "Parecer sem ajuste exigido encerra o ciclo das avaliações; com ajuste, devolve ao revisor do one-pager."},
    {"id": "A029RevisorOnePagerParecer", "name": "029 · Revisor movido pelo parecer", "icon": "🩹", "output_key": "one_pager", "prompt_file": "produto/revisor_one_pager.md", "description": "Aplica ao one-pager os ajustes exigidos pelo parecer de adequação (padrão: 2 rodadas; AVALIACOES_MAX_RODADAS=1 desliga)."},
    {"id": "A030OnePagerPoCheck", "name": "030 · One-pager do PO preservado, depois dos pareceres (determinístico)", "icon": "📌", "output_key": "one_pager_po_report", "prompt_file": None, "description": "A conferência final, depois do gate estrutural, dos pareceres e dos revisores: trecho do one-pager do PO perdido sem pedido deixa produto 🔴 e vai ao restaurador."},
    {"id": "A031OnePagerPoRodada", "name": "031 · Saída da conferência do one-pager do PO (determinístico)", "icon": "🔀", "output_key": "one_pager_po_rodada", "prompt_file": None, "description": "Preservado segue para o gate final; perdido vai ao restaurador uma vez."},
    {"id": "A032RestaurarOnePagerPo", "name": "032 · Restaurador do one-pager do PO", "icon": "🧷", "output_key": "one_pager", "prompt_file": "produto/032_restaurar_one_pager_po.md", "description": "Devolve ao one-pager, literalmente, os trechos do PO que a esteira reescreveu; o que um gate ou parecer pedia vira [PROPOSTA — validar com PO]."},
    {"id": "A033GateFinalProduto", "name": "033 · Gate final de produto", "icon": "🏁", "output_key": "gate_final_report", "prompt_file": "produto/033_gate_final.md", "description": "Coerência entre missão e vereditos; libera ou bloqueia para design/dev."},
    {"id": "A034GateFinalProdutoCheck", "name": "034 · Veredito final (determinístico)", "icon": "🔀", "output_key": "gate_final_status", "prompt_file": None, "description": "Lê o envelope do gate final."},
    {"id": "A035SpecMissao", "name": "035 · Spec da missão", "icon": "📜", "output_key": "spec_missao", "prompt_file": "produto/035_spec_missao.md", "description": "Os 12 blocos da spec — contrato contra o qual design e dev constroem."},
    {"id": "A036BnccCheck", "name": "036 · Conformidade BNCC Computação (determinístico)", "icon": "📚", "output_key": "bncc_report", "prompt_file": None, "description": "Bloco 11 × lista oficial do MEC: código existe, é do ano da missão e inclui letramento digital. Não conforme bloqueia design e dev."},
    {"id": "A037ManifestoCheckProduto", "name": "037 · Ficha do manifesto (determinístico)", "icon": "🪪", "output_key": "manifesto_report", "prompt_file": None, "description": "Bloco 0 da spec × listas fechadas da plataforma, conferido ainda em Produto: campo errado volta para quem escreveu a spec, em vez de custar o design inteiro."},
    {"id": "A038EvidenciaCheck", "name": "038 · Matriz de evidência pedagógica (determinístico)", "icon": "🔬", "output_key": "evidencia_report", "prompt_file": None, "description": "Bloco 9 × bloco 11: grau `scored` com dois sinais nomeados, toda habilidade com momento em tela e medida ligada, gabarito declarado no servidor."},
    {"id": "A039JuizEvidencia", "name": "039 · Juiz da matriz de evidência", "icon": "⚖️", "output_key": "evidencia_status", "prompt_file": None, "description": "Juiz de achados sobre `Matriz de evidência pedagógica`: retira o achado de uso vedado quando o texto só cita para vedar — com citação literal conferida."},
    {"id": "A040PerguntasCheck", "name": "040 · Perguntas de produto, sub-bloco 9f (determinístico)", "icon": "❓", "output_key": "perguntas_report", "prompt_file": None, "description": "As cinco perguntas de produto: quantidade fechada, decisão com limiar, corte do vocabulário, e a ação que responde cada uma declarada na tabela de eventos do bloco 9 com payload que mede."},
    {"id": "A041JuizPerguntas", "name": "041 · Juiz das perguntas de produto", "icon": "⚖️", "output_key": "juiz_perguntas_report", "prompt_file": "produto/041_juiz_perguntas.md", "description": "O que não se confere por regex: a pergunta muda uma decisão nossa, é sobre o produto e não sobre a criança, a ação nomeada a responde, e ela não é uma transversal repintada."},
    {"id": "A042JuizPerguntasCheck", "name": "042 · Veredito do juiz das perguntas (determinístico)", "icon": "🔀", "output_key": "juiz_perguntas_status", "prompt_file": None, "description": "Lê o envelope do juiz: ❌ em pergunta declarada pelo PO bloqueia; ❌ só em proposta segue como ressalva para o PO decidir."},
    {"id": "A043RastroSpec", "name": "043 · Rastro de lacunas da spec (determinístico)", "icon": "🧭", "output_key": "rastro_spec_report", "prompt_file": None, "description": "Marcadores de lacuna na spec, por dono: o de produto ou de insumo volta para quem escreveu a spec; a decisão do PO fica 🟡 no semáforo do parecer; o de design e o de dev ficam para a etapa delas."},
    {"id": "A044ConteudoAprovadoSpec", "name": "044 · Spec × one-pager aprovado (determinístico)", "icon": "📎", "output_key": "conteudo_aprovado_spec_report", "prompt_file": None, "description": "A spec traduz o one-pager que o PO aprovou: mesmas habilidades do contrato de evidência (§12a), mesmo tempo total em tela (§10) e o podcast (§11) declarado. Ressalva de parecer que o PO não incorporou não muda a spec."},
    {"id": "A045ConteudoAprovado", "name": "045 · Conteúdo aprovado para a banca de produto (determinístico)", "icon": "🔀", "output_key": None, "prompt_file": None, "description": "Grava as seções literais do one-pager para a banca do fim de produto."},
    {"id": "A046EscopoBanca", "name": "046 · Escopo da banca de produto (determinístico)", "icon": "🔀", "output_key": None, "prompt_file": None, "description": "Grava o escopo da banca na posição «produto»."},
    {"id": "A047aBancaProdutoNarrativa", "name": "047a · Banca no fim de produto: produto e narrativa", "icon": "🅰️", "output_key": "banca_produto_narrativa", "prompt_file": None, "description": "Os critérios PROD da banca que a spec decide, antes do parecer do PO. O achado volta ao autor da spec na próxima rodada."},
    {"id": "A047bBancaPedagogiaBncc", "name": "047b · Banca no fim de produto: pedagogia e BNCC", "icon": "🅲", "output_key": "banca_produto_pedagogia", "prompt_file": None, "description": "Os critérios PED da banca sobre a spec, antes do parecer do PO."},
    {"id": "A048BancaConsolidacao", "name": "048 · Banca de produto (determinístico)", "icon": "⚖️", "output_key": "banca_produto_report", "prompt_file": None, "description": "Veredito da banca no fim de produto: o pior das dimensões, com os bloqueantes lidos dos arquivos de critério. 🔴 devolve a spec ao autor e, esgotadas as rodadas, recusa o de acordo."},
    {"id": "A049SpecCheck", "name": "049 · Veredito da spec (determinístico)", "icon": "🔀", "output_key": "spec_rodada", "prompt_file": None, "description": "Currículo e manifesto conformes encerram o loop da spec; reprovados devolvem ao autor com os dois relatórios."},
    {"id": "A050FidelidadeProduto", "name": "050 · Fidelidade ao pedido do PO e ao briefing", "icon": "📌", "output_key": "fidelidade_report", "prompt_file": None, "description": "Núcleo, one-pager e spec contra todos os pedidos do PO e o briefing. Pedido sem prova é 🔴 e recusa o de acordo de produto; conflito com regra da esteira vira decisão do PO."},
    {"id": "A051OnePagerResumido", "name": "051 · One-pager resumido", "icon": "🗂️", "output_key": "one_pager_resumido", "prompt_file": "produto/051_one_pager_resumido.md", "description": "O one-pager no formato do time de produto para avaliação pedagógica: ficha, ideia, componente curricular, socioemocionais, 6 etapas, professor, contrato de evidência ternário e takeaway. Sai em .md, .docx e .html."},
    {"id": "A052ConteudoAprovadoResumido", "name": "052 · Resumido × one-pager aprovado (determinístico)", "icon": "📎", "output_key": "conteudo_aprovado_resumido_report", "prompt_file": None, "description": "As habilidades do bloco 11, o tempo em tela do §10 e o Canal B com o texto do §12a no resumido que o time lê para aprovar. Divergência volta ao autor do resumido."},
    {"id": "A053ResumidoRodada", "name": "053 · Veredito do resumido (determinístico)", "icon": "🔁", "output_key": "resumido_rodada", "prompt_file": None, "description": "Resumido fiel encerra o loop; divergente volta ao autor com o relatório, até o teto de rodadas."},
]

PRODUTO_METADATA_SPEC = [m for m in PRODUTO_METADATA if m["id"] in SPEC_AGENT_IDS]
