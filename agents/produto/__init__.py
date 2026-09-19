"""Área de PRODUTO — do briefing ao spec fechado da missão.

Ordem (SequentialAgent):
  ┌─ LoopAgent (≤ 2 rodadas) ─────────────────────────────────────────┐
  │ p0a A01NucleoNarrativo   → nucleo_narrativo                     │
  │ p0mg A02MicroGate        → micro_gate_report                    │
  │ p0mgc A03MicroGateCheck       → micro_gate_status (escalate)         │
  └───────────────────────────────────────────────────────────────────┘
  p0b A04SecoesApoio         → one_pager  (núcleo + seções 2, 5–18 + brief)
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
"""

from __future__ import annotations

import warnings
from typing import Optional

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.loop_agent import LoopAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.sequential_agent import SequentialAgent

from agents.base import create_llm_agent
from agents.callbacks import marcar_heranca, preservar_one_pager
from agents.checkers import BnccCheckAgent, EnvelopeGateAgent, RastroCheckAgent, SaidaDeLoopAgent
from config import get_settings
from prompts import load_prompt

warnings.filterwarnings("ignore", category=DeprecationWarning, module="google.adk.agents")

# O prompt do micro-gate fixa o teto em 2 rodadas: na segunda reprovação o problema é de
# mecanismo, não de redação, e o relatório sai com `precisa_humano`.
MICRO_GATE_MAX_RODADAS = 2


def get_nucleo_narrativo_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A01NucleoNarrativo",
        description="Núcleo narrativo da missão (seções 0, 1, 3 e 4): descoberta central, gap de informação, escolha significativa e as 6 etapas.",
        instruction=load_prompt("produto/01_nucleo_narrativo.md"),
        output_key="nucleo_narrativo",
        include_contents="default",  # único agente que vê a mensagem original e os anexos
        **kw,
    )


def get_micro_gate_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A02MicroGate",
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
        description="Avaliação pedagógica: descoberta central, papel do professor, BNCC e guardrails éticos.",
        instruction=load_prompt("produto/08_avaliacao_pedagogica.md"),
        output_key="avaliacao_pedagogica_report",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_adequacao_pedagogica_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A10AdequacaoPedagogica",
        description="Parecer de adequação pedagógica em seis eixos: alinhamento curricular, demanda cognitiva, carga acidental, viabilidade na escola pública, evidência de aprendizagem e equidade.",
        instruction=load_prompt("produto/10_adequacao_pedagogica.md"),
        output_key="adequacao_report",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_experiencia_aluno_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A09ExperienciaEstudante",
        description="Experiência do aluno por faixa etária: carga decisória, linguagem, duração e complexidade.",
        instruction=load_prompt("produto/09_experiencia_estudante.md"),
        output_key="experiencia_aluno_report",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_gate_final_produto_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A11GateFinalProduto",
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


def build_produto_stage(
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
    modo_estrito: Optional[bool] = None,
    max_rodadas: Optional[int] = None,
) -> SequentialAgent:
    """Monta a etapa de Produto como SequentialAgent aninhado."""
    settings = get_settings()
    estrito = settings.produto_modo_estrito if modo_estrito is None else modo_estrito
    rodadas = max(1, max_rodadas or settings.gate_estrutural_max_rodadas)
    rodadas_spec = max(1, settings.spec_max_rodadas)
    rodadas_avaliacoes = max(1, settings.avaliacoes_max_rodadas)
    kw = {"thinking_budget": thinking_budget, "include_thoughts": include_thoughts}

    nucleo_loop = LoopAgent(
        name="NucleoNarrativoLoop",
        description="Núcleo narrativo ↔ micro-gate de spoiler/gap até passar ou esgotar as rodadas.",
        max_iterations=MICRO_GATE_MAX_RODADAS,
        sub_agents=[
            get_nucleo_narrativo_agent(**kw),
            get_micro_gate_agent(**kw),
            EnvelopeGateAgent(
                name="A03MicroGateCheck",
                description="Lê o envelope do micro-gate: aprovado segue para as seções de apoio, reprovado devolve o núcleo ao P0a.",
                rotulo="Micro-gate do núcleo",
                report_key="micro_gate_report",
                status_key="micro_gate_status",
                round_key="micro_gate_rodada",
                max_rounds=MICRO_GATE_MAX_RODADAS,
                escalate_on_approve=True,
                # Quem bloqueia a missão é o gate estrutural (P1). O micro-gate esgotado
                # segue adiante com o achado registrado — o problema é de mecanismo e o P1 o audita.
                block_pipeline_on_fail=False,
            ),
        ],
    )

    gate_loop = LoopAgent(
        name="GateEstruturalLoop",
        description="Gate estrutural ↔ revisor do one-pager até aprovar ou esgotar as rodadas.",
        max_iterations=rodadas,
        sub_agents=[
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
    spec_loop = LoopAgent(
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
            SaidaDeLoopAgent(
                name="A16SpecCheck",
                description="Currículo e manifesto conformes encerram o loop; reprovados devolvem a spec ao autor com os dois relatórios.",
                rotulo="Spec da missão",
                status_keys=["bncc_status", "manifesto_status"],
                rodada_key="spec_rodada",
                max_rounds=rodadas_spec,
            ),
        ],
    )

    avaliacoes_loop = LoopAgent(
        name="AvaliacoesLoop",
        description="Avaliações em paralelo ↔ revisor do one-pager, quando o parecer de adequação pede ajuste.",
        max_iterations=rodadas_avaliacoes,
        before_agent_callback=marcar_heranca,
        sub_agents=[
            avaliacoes,
            SaidaDeLoopAgent(
                name="A10bAdequacaoCheck",
                description="Parecer sem ajuste exigido encerra o loop; com ajuste, o revisor aplica e as avaliações refazem.",
                rotulo="Adequação pedagógica",
                status_keys=["adequacao_status"],
                rodada_key="avaliacoes_rodada",
                max_rounds=rodadas_avaliacoes,
                # o parecer é consultivo: `aprovado_com_ressalvas` não obriga nova rodada
                aceitos=["aprovado", "aprovado_com_ressalvas", "amarelo", ""],
            ),
            revisor_pos_parecer,
        ],
    )

    return SequentialAgent(
        name="ProdutoStage",
        description="Área de Produto: núcleo narrativo ↔ micro-gate → seções de apoio → gate estrutural → avaliações → gate final → spec da missão ↔ currículo e manifesto.",
        sub_agents=[
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
        ],
    )


PRODUTO_METADATA = [
    {"id": "A01NucleoNarrativo", "name": "01 · Núcleo narrativo", "icon": "🎬", "output_key": "nucleo_narrativo", "prompt_file": "produto/01_nucleo_narrativo.md", "description": "Seções 0, 1, 3 e 4 a partir do briefing e dos anexos: descoberta, narrativa e as 6 etapas."},
    {"id": "A02MicroGate", "name": "02 · Micro-gate do núcleo", "icon": "🕵️", "output_key": "micro_gate_report", "prompt_file": "produto/02_micro_gate.md", "description": "Spoiler, gap de informação, escolha significativa e job-to-be-done — binário, até 2 rodadas."},
    {"id": "A03MicroGateCheck", "name": "03 · Veredito do micro-gate (determinístico)", "icon": "🔀", "output_key": "micro_gate_status", "prompt_file": None, "description": "Lê o envelope do micro-gate e decide se o núcleo volta ao P0a ou segue."},
    {"id": "A04SecoesApoio", "name": "04 · Seções de apoio e brief", "icon": "📝", "output_key": "one_pager", "prompt_file": "produto/04_secoes_apoio.md", "description": "Completa o one-pager canônico (seções 2 e 5–18) e o brief de escopo sobre o núcleo aprovado."},
    {"id": "A05GateEstrutural", "name": "05 · Gate estrutural", "icon": "🚧", "output_key": "gate_estrutural_report", "prompt_file": "produto/05_gate_estrutural.md", "description": "23 critérios: estrutura, ambiente, logística, evidências, viabilidade e infraestrutura."},
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
    {"id": "A16SpecCheck", "name": "16 · Veredito da spec (determinístico)", "icon": "🔀", "output_key": "spec_rodada", "prompt_file": None, "description": "Currículo e manifesto conformes encerram o loop da spec; reprovados devolvem ao autor com os dois relatórios."},
]
