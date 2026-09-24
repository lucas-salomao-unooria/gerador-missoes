"""Área de PRODUTO — do briefing ao spec fechado da missão.

Ordem (SequentialAgent):
  p00c A00cMapaConceitual    → mapa_conceitual (conceito limiar, núcleo e apoio do material, com o
                                 trecho citado; as crenças de entrada que o bimestre derruba)
  p00d A00dIdeacaoMecanismos → ideacao_mecanismos (três mecanismos distintos, pontuados na
                                 rubrica de profundidade; o núcleo desenvolve o escolhido)
  ┌─ LoopAgent (≤ 2 rodadas) ─────────────────────────────────────────┐
  │ p0a A01NucleoNarrativo   → nucleo_narrativo                     │
  │ p0cc A01cCoberturaConceitual → cobertura_resultado (determinístico) │
  │ p0mg A02MicroGate        → micro_gate_report                    │
  │ p0jp A02bJuizProfundidade → profundidade_report (notas P1–P6)   │
  │ p0pc A03bProfundidadeCheck → profundidade_status (contado nas notas) │
  │ p0mgc A03MicroGateCheck       → micro_gate_status                    │
  │ p0nc A03cNucleoCheck     → sai quando micro-gate E profundidade passam │
  └───────────────────────────────────────────────────────────────────┘
  p0b A04SecoesApoio         → one_pager  (núcleo + seções 2, 5–18 + brief)
  ┌─ LoopAgent (≤ N rodadas) ─────────────────────────────────────────┐
  │ p0c A04bContratoProdutoCheck → contrato_produto_report (lint: canal │
  │      de sala, estado no servidor, SAEB, números sem origem)       │
  ┌─ LoopAgent (≤ N rodadas) ─────────────────────────────────────────┐
  │ p1  A05GateEstrutural    → gate_estrutural_report               │
  │ p1c A06GateEstruturalCheck    → gate_estrutural_status (escalate)    │
  │ p1b A07RevisorOnePager   → one_pager (corrigido)                │
  └───────────────────────────────────────────────────────────────────┘
  ┌─ ParallelAgent ──────────────────────────────────────────────────┐
  │ p2  A08AvaliacaoPedagogica → avaliacao_pedagogica_report       │
  │ p3  A09ExperienciaEstudante    → experiencia_aluno_report          │
  └───────────────────────────────────────────────────────────────────┘
  p4  A11GateFinalProduto    → gate_final_report
  p4c GateFinalCheck           → gate_final_status
  p5  A13SpecMissao          → spec_missao   (saída final de Produto)
  p5c A14BnccCheck                → bncc_status   (determinístico: bloco 11 × BNCC Computação oficial;
                                 não conforme bloqueia design e dev)
  p5d A15cPerguntasCheck     → perguntas_status (determinístico: as 5 perguntas do 9f, com decisão
                                 com limiar e ação que existe na tabela de eventos)
  p5e A15dJuizPerguntas      → juiz_perguntas_report (o que só se julga lendo: a pergunta muda
                                 uma decisão nossa e é sobre o produto, não sobre a criança)
  p6  A16bOnePagerResumido   → one_pager_resumido (o formato curto do time de produto para
                                 avaliação pedagógica, derivado do canônico e da spec conferida)
"""

from __future__ import annotations

import warnings
from typing import Optional

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.loop_agent import LoopAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.sequential_agent import SequentialAgent

from agents.base import create_llm_agent
from agents.juiz import get_juiz_de_achados
from agents.callbacks import marcar_heranca, preservar_one_pager
from agents.checkers import (
    SecaoSplitAgent,
    BnccCheckAgent,
    CoberturaConceitualAgent,
    EnvelopeGateAgent,
    ProfundidadeCheckAgent,
    RastroCheckAgent,
    SaidaDeLoopAgent,
    VizinhasCatalogoAgent,
)
from config import get_settings
from prompts import load_prompt

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
        name="A00cMapaConceitual",
        deterministico=True,  # extrai do material: mesma entrada, mesmo mapa
        description="Mapa conceitual do material do bimestre: conceito limiar, conceitos núcleo e de apoio com o trecho citado, crenças de entrada a derrubar e o vocabulário que o Explicar deve usar.",
        instruction=load_prompt("produto/00c_mapa_conceitual.md"),
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
        name="A00dIdeacaoMecanismos",
        description="Ideação: três mecanismos distintos para o conceito limiar do material, cada um com a anatomia do aha, pontuados na rubrica de profundidade; indica qual o núcleo deve desenvolver.",
        instruction=load_prompt("produto/00d_ideacao_mecanismos.md"),
        output_key="ideacao_mecanismos",
        **kw,
    )


def get_juiz_profundidade_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A02bJuizProfundidade",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Juiz de profundidade pedagógica: nota de 1 a 4 em seis dimensões (conceito do material vivido, aposta comprometida, ápice do aha, explicar depois de viver, transferência, demanda à altura do ano), com trecho citado e instrução de reescrita.",
        instruction=load_prompt("produto/02b_juiz_profundidade.md"),
        output_key="profundidade_report",
        **kw,
    )


def get_nucleo_narrativo_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A01NucleoNarrativo",
        description="Núcleo narrativo da missão (seções 0, 1, 3 e 4): descoberta central, gap de informação, escolha significativa e as 6 etapas.",
        instruction=load_prompt("produto/01_nucleo_narrativo.md"),
        output_key="nucleo_narrativo",
        include_contents="default",  # único agente que vê a mensagem original e os anexos
        **kw,
    )


#: O brief de escopo começa por esta linha, fixada em `04_secoes_apoio.md`.
#: Em negrito, como o prompt mostra, ou como heading — as duas rodadas de 23/09 escreveram
#: `# MISSÃO DIGITAL…`, e o brief nunca era separado. A linha inteira é consumida.
BRIEF_ESCOPO_INICIO = r"^(?:#{1,6}\s*|\*\*)\s*MISS[ÃA]O DIGITAL UNOORIA\s*·\s*BRIEFING DE ESCOPO[^\n]*"


def get_brief_escopo_split() -> SecaoSplitAgent:
    """Separa o brief de escopo do one-pager antes que o revisor o apague.

    O A04 entrega DOIS documentos — one-pager canônico e brief de escopo — na mesma
    `output_key` (`one_pager`). O A07, logo a seguir, é instruído a devolver "apenas o
    one-pager revisado" na mesma chave: o brief evaporava a cada execução, sem erro e sem
    artefato, e ninguém percebia porque ele nunca foi gravado em disco. É o documento que
    existe justamente para quem não vai auditar critério por critério.
    """
    return SecaoSplitAgent(
        name="A04bBriefEscopoSplit",
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
        name="A02MicroGate",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Micro-gate do núcleo: spoiler (4 padrões), gap de informação real, escolha significativa e job-to-be-done no Desafiar.",
        instruction=load_prompt("produto/02_micro_gate.md"),
        output_key="micro_gate_report",
        **kw,
    )


def get_secoes_apoio_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A04SecoesApoio",
        description="Seções de apoio (2 e 5–18) e brief de escopo sobre o núcleo aprovado: completa o one-pager canônico que o gate estrutural audita.",
        instruction=load_prompt("produto/04_secoes_apoio.md"),
        output_key="one_pager",
        after_agent_callback=preservar_one_pager,
        **kw,
    )


def get_gate_estrutural_agent(max_rodadas: Optional[int] = None, **kw) -> LlmAgent:
    # O teto de rodadas do loop é escrito dentro do prompt: sem isso, a regra de parada
    # do gate promete uma rodada que o LoopAgent nunca executa (e vice-versa).
    rodadas = max_rodadas or get_settings().gate_estrutural_max_rodadas
    return create_llm_agent(
        name="A05GateEstrutural",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Gate estrutural: completude, ambiente, verbos nativos, logística, evidências e fechamento de spec.",
        instruction=load_prompt("produto/05_gate_estrutural.md", gate_max_rodadas=rodadas),
        output_key="gate_estrutural_report",
        **kw,
    )


def get_revisor_one_pager_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A07RevisorOnePager",
        description="Aplica ao one-pager as correções prontas do gate estrutural, sem inventar decisões de produto.",
        instruction=load_prompt("produto/07_revisor_one_pager.md"),
        output_key="one_pager",
        **kw,
    )


def get_avaliacao_pedagogica_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A08AvaliacaoPedagogica",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Avaliação pedagógica: descoberta central, papel do professor, BNCC e guardrails éticos.",
        instruction=load_prompt("produto/08_avaliacao_pedagogica.md"),
        output_key="avaliacao_pedagogica_report",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_adequacao_pedagogica_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A10AdequacaoPedagogica",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Parecer de adequação pedagógica em seis eixos: alinhamento curricular, demanda cognitiva, carga acidental, viabilidade na escola pública, evidência de aprendizagem e equidade.",
        instruction=load_prompt("produto/10_adequacao_pedagogica.md"),
        output_key="adequacao_report",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_experiencia_aluno_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A09ExperienciaEstudante",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Experiência do aluno por faixa etária: carga decisória, linguagem, duração e complexidade.",
        instruction=load_prompt("produto/09_experiencia_estudante.md"),
        output_key="experiencia_aluno_report",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_gate_final_produto_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A11GateFinalProduto",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Gate final de produto: coerência entre missão e vereditos; libera ou bloqueia para design/dev.",
        instruction=load_prompt("produto/11_gate_final.md"),
        output_key="gate_final_report",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_spec_missao_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A13SpecMissao",
        description="Traduz o one-pager aprovado na especificação de missão (12 blocos) — o contrato da construção.",
        instruction=load_prompt("produto/13_spec_missao.md"),
        output_key="spec_missao",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_one_pager_resumido_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A16bOnePagerResumido",
        description="One-pager resumido para avaliação pedagógica, no formato do time de produto: ficha, ideia em prosa, componente curricular, socioemocionais, 6 etapas, professor, contrato de evidência ternário por habilidade e takeaway. Condensa o canônico e a spec aprovados; não decide nada novo.",
        instruction=load_prompt("produto/16b_one_pager_resumido.md"),
        output_key="one_pager_resumido",
        before_agent_callback=marcar_heranca,
        **kw,
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
        name="A15dJuizPerguntas",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Juiz das cinco perguntas de produto do 9f: cada uma muda uma decisão nossa, é sobre o produto e não sobre a criança, e a ação nomeada a responde.",
        instruction=load_prompt("produto/15_juiz_perguntas.md"),
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
                name="A14BnccCheck",
                description="Confere o bloco 11 da spec contra a lista oficial da BNCC Computação: código existe, é do ano da missão e há letramento digital.",
                estrito=settings.bncc_check_estrito,
                before_agent_callback=marcar_heranca,
            ),
            RastroCheckAgent(
                name="A15ManifestoCheckProduto",
                description="Ficha do manifesto no bloco 0 da spec, conferida ainda em Produto: campo fora do vocabulário fechado volta para quem escreveu a spec.",
                modo="manifesto",
                rotulo="Ficha do manifesto (produto)",
                report_key="manifesto_report",
                status_key="manifesto_status",
                estrito=settings.esteira_estrita,
                before_agent_callback=marcar_heranca,
            ),
            RastroCheckAgent(
                name="A15bEvidenciaCheck",
                description="Matriz de evidência pedagógica: grau `scored` com dois sinais, toda habilidade do bloco 11 com momento em tela e medida do bloco 9, gabarito declarado no servidor.",
                modo="evidencia",
                rotulo="Matriz de evidência pedagógica",
                report_key="evidencia_report",
                status_key="evidencia_status",
                estrito=settings.esteira_estrita,
                before_agent_callback=marcar_heranca,
            ),
            get_juiz_de_achados("A15bbJuizEvidencia", status_key="evidencia_status", report_key="evidencia_report",
                                fonte_key="spec_missao", gate_rotulo="Matriz de evidência pedagógica", **kw),
            RastroCheckAgent(
                name="A15cPerguntasCheck",
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
                name="A15eJuizPerguntasCheck",
                report_key="juiz_perguntas_report",
                status_key="juiz_perguntas_status",
                rotulo="Juiz das perguntas de produto",
                round_key="juiz_perguntas_rodada",
                max_rounds=rodadas_spec,
                block_pipeline_on_fail=settings.esteira_estrita,
            ),
            SaidaDeLoopAgent(
                name="A16SpecCheck",
                description="Currículo, manifesto, matriz de evidência e perguntas de produto conformes encerram o loop; reprovados devolvem a spec ao autor com os relatórios.",
                rotulo="Spec da missão",
                status_keys=["bncc_status", "manifesto_status", "evidencia_status",
                             "perguntas_status", "juiz_perguntas_status"],
                rodada_key="spec_rodada",
                max_rounds=rodadas_spec,
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
            sub_agents=[_build_spec_loop(kw, settings, rodadas_spec), get_one_pager_resumido_agent(**kw)],
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
            get_vizinhas_catalogo_agent("A01bVizinhasCatalogo"),
            CoberturaConceitualAgent(
                name="A01cCoberturaConceitual",
                description="Núcleo × mapa conceitual: o limiar vive no Decidir ou no aha, todo conceito núcleo tem destino, a anatomia do aha tem os seis passos e a citação do mapa existe no material. Determinístico.",
            ),
            get_micro_gate_agent(**kw),
            get_juiz_profundidade_agent(**kw),
            # Antes do veredito do micro-gate, de propósito: esgotada a última rodada, o
            # `A03MicroGateCheck` encerra o loop, e a profundidade da rodada ficaria sem status.
            ProfundidadeCheckAgent(
                name="A03bProfundidadeCheck",
                max_rounds=MICRO_GATE_MAX_RODADAS,
                description="Conta o veredito de profundidade nas notas do juiz e funde a cobertura conceitual: 🔴 com P1, P2 ou P3 abaixo de 3 ou qualquer dimensão em 1.",
            ),
            EnvelopeGateAgent(
                name="A03MicroGateCheck",
                description="Lê o envelope do micro-gate: aprovado segue para as seções de apoio, reprovado devolve o núcleo ao P0a.",
                rotulo="Micro-gate do núcleo",
                report_key="micro_gate_report",
                status_key="micro_gate_status",
                round_key="micro_gate_rodada",
                max_rounds=MICRO_GATE_MAX_RODADAS,
                # Quem encerra o loop é o `A03cNucleoCheck`: spoiler resolvido com missão rasa
                # não é núcleo pronto.
                escalate_on_approve=False,
                # Quem bloqueia a missão é o gate estrutural (P1). O micro-gate esgotado
                # segue adiante com o achado registrado — o problema é de mecanismo e o P1 o audita.
                block_pipeline_on_fail=False,
            ),
            SaidaDeLoopAgent(
                name="A03cNucleoCheck",
                description="Micro-gate e profundidade aprovados encerram o loop; qualquer um reprovado devolve o núcleo ao P0a com os dois relatórios.",
                rotulo="Núcleo narrativo",
                status_keys=["micro_gate_status", "profundidade_status"],
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
            # O brief de escopo sai do `one_pager` ANTES do gate e do revisor: o A04 entrega os
            # dois documentos na mesma chave e o A07 devolve só o one-pager revisado, então o
            # brief evaporava a cada execução — sem erro, sem artefato, sem ninguém notar.
            get_brief_escopo_split(),
            # Antes do gate, a cada rodada: WebSocket como canal de sala, estado em
            # `localStorage`, SAEB fora do ano e número sem origem nasciam aqui e só eram pegos
            # duas etapas depois (A36) ou nunca. O lint não bloqueia sozinho — o gate aplica.
            RastroCheckAgent(
                name="A04bContratoProdutoCheck",
                description="Contrato de plataforma e origem dos parâmetros no one-pager: canal de sala por polling, estado no servidor, SAEB só nos anos avaliados, número com origem ou marcador. Alimenta o gate estrutural.",
                modo="one_pager",
                rotulo="Contrato de plataforma e origem dos parâmetros",
                report_key="contrato_produto_report",
                status_key="contrato_produto_status",
                estrito=False,
            ),
            get_juiz_de_achados("A04cJuizContratoProduto", status_key="contrato_produto_status",
                                report_key="contrato_produto_report", fonte_key="one_pager",
                                gate_rotulo="Contrato de plataforma e origem dos parâmetros", **kw),
            get_gate_estrutural_agent(max_rodadas=rodadas, **kw),
            EnvelopeGateAgent(
                name="A06GateEstruturalCheck",
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
    # refazem sobre a versão nova. Desligado por padrão (teto 1), porque ligar custa
    # reexecutar os três avaliadores; suba `AVALIACOES_MAX_RODADAS` para ativar.
    revisor_pos_parecer = get_revisor_one_pager_agent(**kw)
    revisor_pos_parecer.name = "A07RevisorOnePagerParecer"
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
            # `A10bAdequacaoCheck` consultava nunca era escrito por agente nenhum — o loop
            # encerrava com aprovação sobre uma chave inexistente. Em 14 execuções, o parecer
            # de adequação emitiu 40 achados de conteúdo real e nenhum foi fechado.
            EnvelopeGateAgent(
                name="A08bAvaliacaoCheck",
                description="Lê o veredito da avaliação pedagógica (critérios 4.x, 5.1/5.2, 8.x).",
                rotulo="Avaliação pedagógica",
                report_key="avaliacao_pedagogica_report",
                status_key="avaliacao_status",
                block_pipeline_on_fail=estrito,
            ),
            EnvelopeGateAgent(
                name="A09bExperienciaCheck",
                description="Lê o veredito da experiência do estudante (3.x, 6.x). Sinaliza, não trava: os tetos desta dimensão são [EXTRAPOLAÇÃO], não medida.",
                rotulo="Experiência do estudante",
                report_key="experiencia_aluno_report",
                status_key="experiencia_status",
                block_pipeline_on_fail=False,
            ),
            EnvelopeGateAgent(
                name="A10aAdequacaoCheck",
                description="Lê o veredito do parecer de adequação pedagógica.",
                rotulo="Adequação pedagógica",
                report_key="adequacao_report",
                status_key="adequacao_status",
                block_pipeline_on_fail=False,
            ),
            SaidaDeLoopAgent(
                name="A10bAdequacaoCheck",
                description="Parecer sem ajuste exigido encerra o loop; com ajuste, o revisor aplica e as avaliações refazem.",
                rotulo="Adequação pedagógica",
                status_keys=["adequacao_status", "avaliacao_status"],
                rodada_key="avaliacoes_rodada",
                max_rounds=rodadas_avaliacoes,
                # `""` saiu da lista: era o que fazia a chave nunca escrita valer aprovação.
                aceitos=["aprovado", "aprovado_com_ressalvas", "amarelo"],
            ),
            revisor_pos_parecer,
        ],
    )

    return SequentialAgent(
        name="ProdutoStage",
        description="Área de Produto: núcleo narrativo ↔ micro-gate → seções de apoio → gate estrutural → avaliações → gate final → spec da missão ↔ currículo e manifesto → one-pager resumido.",
        sub_agents=[
            # Antes de inventar: o que já existe no ano, lido do índice pelo briefing. Sem isto, a
            # primeira geração nasce cega e a repetição só apareceria na segunda rodada do loop.
            get_vizinhas_catalogo_agent("A00bVizinhasCatalogo"),
            # Antes de inventar, também: o que o material do bimestre ensina, e três desenhos
            # candidatos para o conceito central dele. O núcleo desenvolve um, não improvisa.
            get_mapa_conceitual_agent(**kw),
            get_ideacao_mecanismos_agent(**kw),
            nucleo_loop,
            get_secoes_apoio_agent(**kw),
            gate_loop,
            avaliacoes_loop,
            get_gate_final_produto_agent(**kw),
            EnvelopeGateAgent(
                name="A12GateFinalProdutoCheck",
                description="Lê o veredito do gate final de produto (🟢 liberada / 🔴 bloqueada).",
                rotulo="Gate final de produto",
                report_key="gate_final_report",
                status_key="gate_final_status",
                block_pipeline_on_fail=estrito,
            ),
            spec_loop,
            # Depois da spec, de propósito: o bloco 11 já passou pelo A14, então o resumido
            # copia códigos conferidos em vez dos que a seção 2 do canônico ainda podia trocar.
            get_one_pager_resumido_agent(**kw),
        ],
    )


#: Agentes do estágio parcial "spec" (correção a partir da spec), na ordem em que rodam.
SPEC_AGENT_IDS = ["A13SpecMissao", "A14BnccCheck", "A15ManifestoCheckProduto", "A15bEvidenciaCheck",
                  "A15cPerguntasCheck", "A15dJuizPerguntas", "A15eJuizPerguntasCheck",
                  "A16SpecCheck", "A16bOnePagerResumido"]

PRODUTO_METADATA = [
    {"id": "A00bVizinhasCatalogo", "name": "00b · Missões já geradas (determinístico)", "icon": "🗂️", "output_key": "missoes_vizinhas", "prompt_file": None, "description": "Lê o índice de missões e entrega ao núcleo as mais próximas do ano do briefing, para a missão nova não repetir uma anterior."},
    {"id": "A00cMapaConceitual", "name": "00c · Mapa conceitual do material", "icon": "🧭", "output_key": "mapa_conceitual", "prompt_file": "produto/00c_mapa_conceitual.md", "description": "Lê o material do bimestre antes de inventar: um conceito limiar, os conceitos núcleo e de apoio com o trecho citado, as crenças de entrada que o bimestre derruba e o vocabulário do Explicar."},
    {"id": "A00dIdeacaoMecanismos", "name": "00d · Ideação de mecanismos", "icon": "💡", "output_key": "ideacao_mecanismos", "prompt_file": "produto/00d_ideacao_mecanismos.md", "description": "Três mecanismos distintos para o conceito limiar, cada um com a anatomia do aha, pontuados na rubrica de profundidade. O núcleo desenvolve o escolhido."},
    {"id": "A01NucleoNarrativo", "name": "01 · Núcleo narrativo", "icon": "🎬", "output_key": "nucleo_narrativo", "prompt_file": "produto/01_nucleo_narrativo.md", "description": "Seções 0, 1, 3 e 4 a partir do briefing, dos anexos, do mapa conceitual e do mecanismo escolhido: descoberta, conceitos vividos em tela, anatomia do aha, narrativa e as 6 etapas."},
    {"id": "A01bVizinhasCatalogo", "name": "01b · Missões já geradas, pelo núcleo (determinístico)", "icon": "🗂️", "output_key": "missoes_vizinhas", "prompt_file": None, "description": "Refiltra o índice pelo ambiente, eixo e descoberta do núcleo recém-escrito. É esta lista que a verificação V5 do micro-gate julga."},
    {"id": "A01cCoberturaConceitual", "name": "01c · Cobertura conceitual (determinístico)", "icon": "🧩", "output_key": "cobertura_report", "prompt_file": None, "description": "Núcleo × mapa: o limiar vive no Decidir ou no aha, todo conceito núcleo tem destino, a anatomia do aha tem os seis passos e o trecho citado pelo mapa existe no material."},
    {"id": "A02MicroGate", "name": "02 · Micro-gate do núcleo", "icon": "🕵️", "output_key": "micro_gate_report", "prompt_file": "produto/02_micro_gate.md", "description": "Spoiler, gap de informação, escolha significativa e job-to-be-done — binário, até 2 rodadas."},
    {"id": "A02bJuizProfundidade", "name": "02b · Juiz de profundidade", "icon": "🎯", "output_key": "profundidade_report", "prompt_file": "produto/02b_juiz_profundidade.md", "description": "Nota de 1 a 4 em seis dimensões — conceito do material vivido, aposta comprometida, ápice do aha, explicar depois de viver, transferência e demanda à altura do ano —, com trecho citado e instrução de reescrita."},
    {"id": "A03bProfundidadeCheck", "name": "03b · Veredito de profundidade (determinístico)", "icon": "🔀", "output_key": "profundidade_status", "prompt_file": None, "description": "Conta o veredito nas notas do juiz, não no que ele escreveu: P1, P2 ou P3 abaixo de 3 é 🔴. Funde a cobertura conceitual."},
    {"id": "A03MicroGateCheck", "name": "03 · Veredito do micro-gate (determinístico)", "icon": "🔀", "output_key": "micro_gate_status", "prompt_file": None, "description": "Lê o envelope do micro-gate e registra se o núcleo passou em spoiler, gap, escolha e job."},
    {"id": "A03cNucleoCheck", "name": "03c · Saída do loop do núcleo (determinístico)", "icon": "🔀", "output_key": "nucleo_rodada", "prompt_file": None, "description": "Micro-gate e profundidade aprovados encerram o loop; qualquer um reprovado devolve o núcleo ao P0a com os dois relatórios."},
    {"id": "A04SecoesApoio", "name": "04 · Seções de apoio e brief", "icon": "📝", "output_key": "one_pager", "prompt_file": "produto/04_secoes_apoio.md", "description": "Completa o one-pager canônico (seções 2 e 5–18) e o brief de escopo sobre o núcleo aprovado."},
    {"id": "A04bContratoProdutoCheck", "name": "04b · Contrato de plataforma e origem dos parâmetros (determinístico)", "icon": "📡", "output_key": "contrato_produto_report", "prompt_file": None, "description": "Lint do one-pager a cada rodada do gate: canal de sala por polling (nunca WebSocket), estado no servidor (sem localStorage/IndexedDB), SAEB só nos anos avaliados, número com origem ou marcador. O gate aplica; o revisor corrige."},
    {"id": "A05GateEstrutural", "name": "05 · Gate estrutural", "icon": "🚧", "output_key": "gate_estrutural_report", "prompt_file": "produto/05_gate_estrutural.md", "description": "critérios: estrutura, ambiente, logística, evidências, viabilidade e infraestrutura."},
    {"id": "A06GateEstruturalCheck", "name": "06 · Veredito do gate (determinístico)", "icon": "🔀", "output_key": "gate_estrutural_status", "prompt_file": None, "description": "Lê o envelope JSON e decide repetir, seguir ou bloquear."},
    {"id": "A07RevisorOnePager", "name": "07 · Revisor do one-pager", "icon": "🩹", "output_key": "one_pager", "prompt_file": "produto/07_revisor_one_pager.md", "description": "Aplica o complemento pronto-pra-colar do gate; não inventa decisão de produto."},
    {"id": "A08AvaliacaoPedagogica", "name": "08 · Avaliação pedagógica", "icon": "🎓", "output_key": "avaliacao_pedagogica_report", "prompt_file": "produto/08_avaliacao_pedagogica.md", "description": "BNCC, professor, guardrails e affordance × guardrail (paralelo com P3)."},
    {"id": "A09ExperienciaEstudante", "name": "09 · Experiência do estudante", "icon": "🧒", "output_key": "experiencia_aluno_report", "prompt_file": "produto/09_experiencia_estudante.md", "description": "Carga cognitiva, faixa etária e agência (paralelo com P2)."},
    {"id": "A10AdequacaoPedagogica", "name": "10 · Adequação pedagógica", "icon": "⚖️", "output_key": "adequacao_report", "prompt_file": "produto/10_adequacao_pedagogica.md", "description": "Seis eixos com parecer e ajustes acionáveis: currículo, demanda cognitiva, carga acidental, viabilidade na escola pública, evidência de aprendizagem e equidade. Parecer entra como ressalva, não bloqueia."},
    {"id": "A10bAdequacaoCheck", "name": "10b · Veredito do parecer (determinístico)", "icon": "🔀", "output_key": "avaliacoes_rodada", "prompt_file": None, "description": "Parecer sem ajuste exigido encerra o ciclo das avaliações; com ajuste, devolve ao revisor do one-pager."},
    {"id": "A07RevisorOnePagerParecer", "name": "10c · Revisor movido pelo parecer", "icon": "🩹", "output_key": "one_pager", "prompt_file": "produto/07_revisor_one_pager.md", "description": "Aplica ao one-pager os ajustes exigidos pelo parecer de adequação. Só roda com AVALIACOES_MAX_RODADAS > 1."},
    {"id": "A11GateFinalProduto", "name": "11 · Gate final de produto", "icon": "🏁", "output_key": "gate_final_report", "prompt_file": "produto/11_gate_final.md", "description": "Coerência entre missão e vereditos; libera ou bloqueia para design/dev."},
    {"id": "A12GateFinalProdutoCheck", "name": "12 · Veredito final (determinístico)", "icon": "🔀", "output_key": "gate_final_status", "prompt_file": None, "description": "Lê o envelope do gate final."},
    {"id": "A13SpecMissao", "name": "13 · Spec da missão", "icon": "📜", "output_key": "spec_missao", "prompt_file": "produto/13_spec_missao.md", "description": "Os 12 blocos da spec — contrato contra o qual design e dev constroem."},
    {"id": "A14BnccCheck", "name": "14 · Conformidade BNCC Computação (determinístico)", "icon": "📚", "output_key": "bncc_report", "prompt_file": None, "description": "Bloco 11 × lista oficial do MEC: código existe, é do ano da missão e inclui letramento digital. Não conforme bloqueia design e dev."},
    {"id": "A15ManifestoCheckProduto", "name": "15 · Ficha do manifesto (determinístico)", "icon": "🪪", "output_key": "manifesto_report", "prompt_file": None, "description": "Bloco 0 da spec × listas fechadas da plataforma, conferido ainda em Produto: campo errado volta para quem escreveu a spec, em vez de custar o design inteiro."},
    {"id": "A15bEvidenciaCheck", "name": "15b · Matriz de evidência pedagógica (determinístico)", "icon": "🔬", "output_key": "evidencia_report", "prompt_file": None, "description": "Bloco 9 × bloco 11: grau `scored` com dois sinais nomeados, toda habilidade com momento em tela e medida ligada, gabarito declarado no servidor."},
    {"id": "A15cPerguntasCheck", "name": "15c · Perguntas de produto, sub-bloco 9f (determinístico)", "icon": "❓", "output_key": "perguntas_report", "prompt_file": None, "description": "As cinco perguntas de produto: quantidade fechada, decisão com limiar, corte do vocabulário, e a ação que responde cada uma declarada na tabela de eventos do bloco 9 com payload que mede."},
    {"id": "A15dJuizPerguntas", "name": "15d · Juiz das perguntas de produto", "icon": "⚖️", "output_key": "juiz_perguntas_report", "prompt_file": "produto/15_juiz_perguntas.md", "description": "O que não se confere por regex: a pergunta muda uma decisão nossa, é sobre o produto e não sobre a criança, a ação nomeada a responde, e ela não é uma transversal repintada."},
    {"id": "A15eJuizPerguntasCheck", "name": "15e · Veredito do juiz das perguntas (determinístico)", "icon": "🔀", "output_key": "juiz_perguntas_status", "prompt_file": None, "description": "Lê o envelope do juiz: ❌ em pergunta declarada pelo PO bloqueia; ❌ só em proposta segue como ressalva para o PO decidir."},
    {"id": "A16SpecCheck", "name": "16 · Veredito da spec (determinístico)", "icon": "🔀", "output_key": "spec_rodada", "prompt_file": None, "description": "Currículo e manifesto conformes encerram o loop da spec; reprovados devolvem ao autor com os dois relatórios."},
    {"id": "A16bOnePagerResumido", "name": "16b · One-pager resumido", "icon": "🗂️", "output_key": "one_pager_resumido", "prompt_file": "produto/16b_one_pager_resumido.md", "description": "O one-pager no formato do time de produto para avaliação pedagógica: ficha, ideia, componente curricular, socioemocionais, 6 etapas, professor, contrato de evidência ternário e takeaway. Sai em .md, .docx e .html."},
]

PRODUTO_METADATA_SPEC = [m for m in PRODUTO_METADATA if m["id"] in SPEC_AGENT_IDS]
