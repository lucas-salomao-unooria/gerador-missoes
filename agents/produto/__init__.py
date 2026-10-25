"""Área de PRODUTO — do briefing ao spec fechado da missão.

Ordem (SequentialAgent):
  p00c A002MapaConceitual    → mapa_conceitual (conceito limiar, núcleo e apoio do material, com o
                                 trecho citado; as crenças de entrada que o bimestre derruba)
  p00d A003IdeacaoMecanismos → ideacao_mecanismos (três mecanismos distintos, pontuados na
                                 rubrica de profundidade; o núcleo desenvolve o escolhido)
  ┌─ ComiteFinalLoop (≤ COMITE_FINAL_MAX_RODADAS, padrão 2) ──────────────────┐
  │ ┌─ ComiteCanaisLoop (≤ COMITE_MAX_RODADAS, padrão 5) ───────────────────┐ │
  │ │ [isolado] NucleoNarrativoLoop (≤ 2): A004 núcleo → A005–A012 → A013    │ │
  │ │           (pulado quando nenhum comitê reprovado aponta para o A004)  │ │
  │ │ [isolado] SecoesApoioLoop (≤ 2): A014 seções de apoio → A015 → A016    │ │
  │ │ A017 one-pager existe                                                 │ │
  │ │ A018 contrato de evidência do §12a (determinístico: Canal A em toda   │ │
  │ │      habilidade, regra ternária, níveis do Canal B)                   │ │
  │ │ A019a–f painéis A (mecânica e Canal A) e B (Canal B), 3 juízes cada   │ │
  │ │ A020/A021 votos (unanimidade, citação conferida) → A022 saída: volta  │ │
  │ │      ao A004 e ao A014 com os relatórios; esgotado, segue 🟡           │ │
  │ └───────────────────────────────────────────────────────────────────────┘ │
  │ [isolado] GateEstruturalLoop (≤ N): A023 brief → A024–A025 contrato →      │
  │           A026 gate estrutural → A027 veredito → A028 revisor             │
  │ [isolado] AvaliacoesLoop (≤ 2): A029a–c avaliações (sem julgar canal) →    │
  │           A030–A033 vereditos → A034 revisor movido pelo parecer          │
  │ [isolado] OnePagerPoLoop (≤ 2): A035–A036 conferência do PO → A037        │
  │ A038 §12a de novo · A039 conta da virada sobre o one-pager                │
  │ A040a–c comitê final (pedagogia, qualidade, imersão) → A041 votos →       │
  │ A042 saída: reprovado, a cadeia roda de novo a partir do núcleo           │
  └───────────────────────────────────────────────────────────────────────────┘
  p4  A043GateFinalProduto    → gate_final_report
  p4c GateFinalCheck           → gate_final_status
  p4d A044bTextosChave         → textos_chave (registro de IDs) · textos_chave_tabela (determinístico, PR 7: os
                                 textos-chave do one-pager — aspas do §4, Canal B, opções, roteiro, podcast — com
                                 ID estável; roda também na correção pontual de produto)
  p5  A045SpecMissao          → spec_missao   (saída final de Produto)
  p5a A045bCompletudeSpec     → completude_spec (o que o D0 fechava no design e é de produto: estado, handoff,
                                 evidência, dados e retenção, duração e tetos, painel, PQ e KPI, texto do
                                 professor, revezamento; o que é do PO vira marcador e vai ao de acordo)
  p5b A045cCompletudeSpecSplit → spec_missao com o bloco 15 montado em código · relatorio_completude ·
                                 completude_status   (A045b e A045c num loop de até 2 rodadas: a segunda só
                                 quando o código reprova a completude, e só ela refaz)
  p5c A046BnccCheck                → bncc_status   (determinístico: bloco 11 × BNCC Computação oficial;
                                 não conforme bloqueia design e dev)
  p5d A050PerguntasCheck     → perguntas_status (determinístico: as 5 perguntas do 9f, com decisão
                                 com limiar e ação que existe na tabela de eventos)
  p5e A051JuizPerguntas      → juiz_perguntas_report (o que só se julga lendo: a pergunta muda
                                 uma decisão nossa e é sobre o produto, não sobre a criança)
  p5f A053RastroSpec         → rastro_spec_status (determinístico: marcador de lacuna na spec;
                                 o de produto volta para a spec, o do PO fica 🟡 no parecer)
  p5g A054ConteudoAprovadoSpec → conteudo_aprovado_spec_status (determinístico: habilidades,
                                 tempo em tela e podcast iguais aos do one-pager aprovado)
  ┌── OnePagerResumidoLoop (até SPEC_MAX_RODADAS) ─────────────────────────┐
  │ p6  A061OnePagerResumido   → one_pager_resumido (o formato curto do time de produto para │
  │                              avaliação pedagógica, derivado do canônico e da spec conferida) │
  │ p6b A062ConteudoAprovadoResumido → habilidades, tempo e Canal B × canônico aprovado │
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
from agents.comite import build_comite_canais_loop, build_comite_final_loop
from agents.juiz import get_fidelidade_check, get_juiz_de_achados
from agents.callbacks import (dispensar_ideacao_com_one_pager_do_po, manter_completude_entre_rodadas, marcar_heranca,
                              preservar_one_pager)
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
    TextosChaveAgent,
    VizinhasCatalogoAgent,
    isolar,
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
        name="A023BriefEscopoSplit",
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
        name="A026GateEstrutural",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Gate estrutural: completude, ambiente, verbos nativos, logística, evidências e fechamento de spec.",
        instruction=load_prompt("produto/026_gate_estrutural.md", gate_max_rodadas=rodadas),
        output_key="gate_estrutural_report",
        **kw,
    )


def get_revisor_one_pager_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A028RevisorOnePager",
        description="Aplica ao one-pager as correções prontas do gate estrutural, sem inventar decisões de produto.",
        instruction=load_prompt("produto/revisor_one_pager.md"),
        output_key="one_pager",
        **kw,
    )


def get_restaurador_one_pager_po_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A037RestaurarOnePagerPo",
        description="Devolve ao one-pager os trechos do one-pager do PO que a esteira reescreveu sem pedido; o que um gate ou parecer pedia vira proposta ao PO.",
        instruction=load_prompt("produto/037_restaurar_one_pager_po.md"),
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
        name="A029aAvaliacaoPedagogica",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Avaliação pedagógica: descoberta central, papel do professor, BNCC e guardrails éticos.",
        instruction=load_prompt("produto/029a_avaliacao_pedagogica.md"),
        output_key="avaliacao_pedagogica_report",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_adequacao_pedagogica_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A029cAdequacaoPedagogica",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Parecer de adequação pedagógica em seis eixos: alinhamento curricular, demanda cognitiva, carga acidental, viabilidade na escola pública, evidência de aprendizagem e equidade.",
        instruction=load_prompt("produto/029c_adequacao_pedagogica.md"),
        output_key="adequacao_report",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_experiencia_aluno_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A029bExperienciaEstudante",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Experiência do aluno por faixa etária: carga decisória, linguagem, duração e complexidade.",
        instruction=load_prompt("produto/029b_experiencia_estudante.md"),
        output_key="experiencia_aluno_report",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_gate_final_produto_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A043GateFinalProduto",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Gate final de produto: coerência entre missão e vereditos; libera ou bloqueia para design/dev.",
        instruction=load_prompt("produto/043_gate_final.md"),
        output_key="gate_final_report",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_spec_missao_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A045SpecMissao",
        description="Traduz o one-pager aprovado na especificação de missão (12 blocos) — o contrato da construção.",
        instruction=load_prompt("produto/045_spec_missao.md"),
        output_key="spec_missao",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_completude_spec_agent(**kw) -> LlmAgent:
    """O que o D0 fechava no design e é de produto, agora em produto, antes da banca e do parecer (PR 6, decisão D2).

    O D0 tomou 34 decisões em 5 sessões; 9 criavam produto (15 palavras, 10% e 45 s na exp02ef1b; retenção, 6 métricas do
    painel e revezamento de 4 na exp03em1b) e 2 aplicavam decisão do PO que nunca foi gravada (90 s e 45 palavras na
    exp02em1b). Aqui elas nascem onde o PO as vê: o que é derivável da missão ou de padrão da plataforma entra no bloco 15
    da spec; o que é decisão do PO vira [PARÂMETRO]/[PROPOSTA]/[ABERTO — dono: PO] e cai na lista do de acordo."""
    return create_llm_agent(
        name="A045bCompletudeSpec",
        description="Completude da spec em produto: varredura das células de produto que a esteira consome, decisões [CP-n] com base declarada (padrão da plataforma, one-pager, catálogo), e o que é do PO como marcador para o de acordo — no bloco 15 da spec.",
        instruction=load_prompt("produto/046_completude_spec.md"),
        output_key="completude_spec",
        # nas rodadas seguintes do SpecLoop, só roda de novo se a spec perdeu o bloco 15: é uma chamada a mais por
        # refazer de produto, não por rodada (teto do plano, D14)
        before_agent_callback=[marcar_heranca, manter_completude_entre_rodadas],
        **kw,
    )


def get_completude_spec_split() -> SecaoSplitAgent:
    """Monta em código a spec com o bloco 15 da completude, sem tocar o que o A045 escreveu (como o D0 desde o PR 2)."""
    return SecaoSplitAgent(
        name="A045cCompletudeSpecSplit",
        description="Monta em código a spec de produto — a do A045 com o bloco 15 da completude no lugar —, separa o relatório de completude e registra `completude_status`. [PARÂMETRO]/[PROPOSTA] fechado sem parecer datado do PO bloqueia.",
        rotulo="Completude da spec (produto)",
        source_key="completude_spec",
        status_key="completude_status",
        estrito=get_settings().esteira_estrita,
        # na correção pontual o editor já trocou a spec montada (bloco 15 inclusive); montar de novo a desfaria
        pular_na_correcao_pontual=True,
        # o que o código acusou na resposta, para a completude corrigir na segunda rodada do loop dela
        relatorio_key="completude_report",
        extracoes=[
            {
                "chave": "spec_missao",
                "inicio": COMPLETUDE_INICIO,
                "fim": COMPLETUDE_FIM,
                "exigir": r"^##\s*15\b",
                "minimo_chars": 120,
                "bloco_proprio": r"^##\s*15\b.*$",
                "bloco_obrigatorio": True,
                "autor": "Completude (045b)",
                "etapa": "produto",
            },
            {
                "chave": "relatorio_completude",
                "inicio": COMPLETUDE_FIM,
                "fim": COMPLETUDE_RELATORIO_FIM,
                "minimo_chars": 80,
            },
        ],
    )


#: Rodadas da completude quando o próprio split a reprova (decidiu no lugar do PO, ou veio sem o bloco 15).
COMPLETUDE_MAX_RODADAS = 2


def _completude_loop(**kw) -> LoopAgent:
    """Completude ↔ o split que a confere, até passar ou esgotar 2 rodadas — só a completude refaz.

    Um 🔴 da completude deixaria a etapa de produto sem *de acordo* (só com exceção) até um refazer de produto inteiro.
    Devolvê-lo ao A045 pelo SpecLoop faria o autor da spec reescrevê-la por um achado que não é dele. Aqui a segunda
    rodada é só da completude, com o que o código acusou (`completude_report`): a chamada a mais existe só quando ela
    falha (teto do plano, D14)."""
    return LoopAgent(
        name="CompletudeLoop",
        description="Completude da spec ↔ conferência em código do bloco 15, até passar ou esgotar 2 rodadas.",
        max_iterations=COMPLETUDE_MAX_RODADAS,
        sub_agents=[
            get_completude_spec_agent(**kw),
            get_completude_spec_split(),
            SaidaDeLoopAgent(
                name="A045dCompletudeRodada",
                description="Completude conferida encerra o loop; reprovada pelo código (decidiu no lugar do PO, ou veio sem o bloco 15) volta a ela com os achados.",
                rotulo="Completude da spec",
                status_keys=["completude_status"],
                rodada_key="completude_rodada",
                max_rounds=COMPLETUDE_MAX_RODADAS,
                # na correção pontual o split não roda (a spec veio editada) e o status fica ausente: não é reprovação
                aceitos=["aprovado", "amarelo", ""],
            ),
        ],
    )


#: Headings da «Saída obrigatória» do prompt 046, como os do D0 (`agents/design`): o bloco 15 vem no Passo 4.
_H = r"^#{2,3}\s*"
COMPLETUDE_INICIO = _H + r"Passo 4\b.*$"     # "## Passo 4 — Bloco 15 (...)"
COMPLETUDE_FIM = _H + r"Passo 5\b.*$"        # "## Passo 5 — Relatório de completude"
COMPLETUDE_RELATORIO_FIM = _H + r"Passo 6\b.*$"  # "## Passo 6 — Testes"


def get_one_pager_resumido_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A061OnePagerResumido",
        description="One-pager resumido para avaliação pedagógica, no formato do time de produto: ficha, ideia em prosa, componente curricular, socioemocionais, 6 etapas, professor, contrato de evidência ternário por habilidade e takeaway. Condensa o canônico e a spec aprovados; não decide nada novo.",
        instruction=load_prompt("produto/061_one_pager_resumido.md"),
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
                name="A062ConteudoAprovadoResumido",
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
                name="A063ResumidoRodada",
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
        name="A051JuizPerguntas",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Juiz das cinco perguntas de produto do 9f: cada uma muda uma decisão nossa, é sobre o produto e não sobre a criança, e a ação nomeada a responde.",
        instruction=load_prompt("produto/051_juiz_perguntas.md"),
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
            # PR 6: o que o D0 fechava no design e é de produto fecha aqui, antes dos gates, da banca e do parecer — os
            # gates conferem a spec completa, e o PO vê no de acordo o que ficou para ele. Isolado: o LoopAgent do ADK
            # encerra no primeiro `escalate` de qualquer subagente, e a saída da completude encerraria o SpecLoop sem o
            # BNCC, os gates, a banca e o A059 (revisão do PR #73, 24/10/2026)
            isolar(_completude_loop(**kw)),
            BnccCheckAgent(
                name="A046BnccCheck",
                description="Confere o bloco 11 da spec contra a lista oficial da BNCC Computação: código existe, é do ano da missão e há letramento digital.",
                estrito=settings.bncc_check_estrito,
                before_agent_callback=marcar_heranca,
            ),
            RastroCheckAgent(
                name="A047ManifestoCheckProduto",
                description="Ficha do manifesto no bloco 0 da spec, conferida ainda em Produto: campo fora do vocabulário fechado volta para quem escreveu a spec.",
                modo="manifesto",
                rotulo="Ficha do manifesto (produto)",
                report_key="manifesto_report",
                status_key="manifesto_status",
                estrito=settings.esteira_estrita,
                before_agent_callback=marcar_heranca,
            ),
            RastroCheckAgent(
                name="A048EvidenciaCheck",
                description="Matriz de evidência pedagógica: grau `scored` com dois sinais, toda habilidade do bloco 11 com momento em tela e medida do bloco 9, gabarito declarado no servidor.",
                modo="evidencia",
                rotulo="Matriz de evidência pedagógica",
                report_key="evidencia_report",
                status_key="evidencia_status",
                estrito=settings.esteira_estrita,
                before_agent_callback=marcar_heranca,
            ),
            get_juiz_de_achados("A049JuizEvidencia", status_key="evidencia_status", report_key="evidencia_report",
                                fonte_key="spec_missao", gate_rotulo="Matriz de evidência pedagógica", **kw),
            RastroCheckAgent(
                name="A050PerguntasCheck",
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
                name="A052JuizPerguntasCheck",
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
                name="A053RastroSpec",
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
                name="A054ConteudoAprovadoSpec",
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
            *get_banca("produto", "AC", 55, rotulo="Banca de produto",
                       titulo="Banca de validação — fim de produto",
                       report_key="banca_produto_report", status_key="banca_produto_status", **kw),
            SaidaDeLoopAgent(
                name="A059SpecCheck",
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
            # duas etapas depois (A101) ou nunca. O lint não bloqueia sozinho — o gate aplica.
            RastroCheckAgent(
                name="A024ContratoProdutoCheck",
                description="Contrato de plataforma e origem dos parâmetros no one-pager: canal de sala por polling, estado no servidor, SAEB só nos anos avaliados, número com origem ou marcador. Alimenta o gate estrutural.",
                modo="one_pager",
                rotulo="Contrato de plataforma e origem dos parâmetros",
                report_key="contrato_produto_report",
                status_key="contrato_produto_status",
                estrito=False,
            ),
            get_juiz_de_achados("A025JuizContratoProduto", status_key="contrato_produto_status",
                                report_key="contrato_produto_report", fonte_key="one_pager",
                                gate_rotulo="Contrato de plataforma e origem dos parâmetros", **kw),
            get_gate_estrutural_agent(max_rodadas=rodadas, **kw),
            EnvelopeGateAgent(
                name="A027GateEstruturalCheck",
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
    revisor_pos_parecer.name = "A034RevisorOnePagerParecer"
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
            # `A033AdequacaoCheck` consultava nunca era escrito por agente nenhum — o loop
            # encerrava com aprovação sobre uma chave inexistente. Em 14 execuções, o parecer
            # de adequação emitiu 40 achados de conteúdo real e nenhum foi fechado.
            EnvelopeGateAgent(
                name="A030AvaliacaoCheck",
                documentos=["one_pager", "brief_escopo", "material_anexado"],  # citação dos bloqueios conferida em código (`tools/citacoes.py`)
                description="Lê o veredito da avaliação pedagógica (critérios 4.x, 5.1/5.2, 8.x).",
                rotulo="Avaliação pedagógica",
                report_key="avaliacao_pedagogica_report",
                status_key="avaliacao_status",
                block_pipeline_on_fail=estrito,
                # o 4.1 da exp06ef1b repetia os 29 min que o PO aceitou no Pedido 13 (08/10/2026)
                recontar_decisoes_do_po=True,
            ),
            EnvelopeGateAgent(
                name="A031ExperienciaCheck",
                documentos=["one_pager", "brief_escopo"],  # citação dos bloqueios conferida em código (`tools/citacoes.py`)
                description="Lê o veredito da experiência do estudante (3.x, 6.x). Sinaliza, não trava: os tetos desta dimensão são [EXTRAPOLAÇÃO], não medida.",
                rotulo="Experiência do estudante",
                report_key="experiencia_aluno_report",
                status_key="experiencia_status",
                block_pipeline_on_fail=False,
                # o 6.2 da exp06ef1b repetia os 29 min que o PO aceitou no Pedido 13 (08/10/2026)
                recontar_decisoes_do_po=True,
            ),
            EnvelopeGateAgent(
                name="A032AdequacaoCheck",
                documentos=["one_pager", "brief_escopo", "material_anexado"],  # citação dos bloqueios conferida em código (`tools/citacoes.py`)
                description="Lê o veredito do parecer de adequação pedagógica.",
                rotulo="Adequação pedagógica",
                report_key="adequacao_report",
                status_key="adequacao_status",
                block_pipeline_on_fail=False,
            ),
            SaidaDeLoopAgent(
                name="A033AdequacaoCheck",
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
            get_one_pager_po_check("A035OnePagerPoCheck", estrito=settings.esteira_estrita),
            SaidaDeLoopAgent(
                name="A036OnePagerPoRodada",
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
            # Os comitês só julgam; reprovada, a missão volta a quem a escreve (A004 e A014) e passa de novo pelos
            # gates do núcleo — por isso o loop do comitê envolve os loops dos autores (`agents/comite.py`).
            build_comite_final_loop([
                build_comite_canais_loop([
                    nucleo_loop,
                    secoes_apoio_loop,
                    DocumentoObrigatorioAgent(name="A017OnePagerExiste", chave="one_pager", autor="A014SecoesApoio",
                                              description="Sem one-pager depois de duas tentativas do A014, a etapa para com mensagem legível."),
                ], **kw),
                gate_loop,
                avaliacoes_loop,
                one_pager_po_loop,
            ], **kw),
            get_gate_final_produto_agent(**kw),
            EnvelopeGateAgent(
                name="A044GateFinalProdutoCheck",
                documentos=["one_pager", "brief_escopo", "gate_estrutural_report", "avaliacao_pedagogica_report", "experiencia_aluno_report", "adequacao_report"],  # citação dos bloqueios conferida em código (`tools/citacoes.py`)
                description="Lê o veredito do gate final de produto (🟢 liberada / 🔴 bloqueada).",
                rotulo="Gate final de produto",
                report_key="gate_final_report",
                status_key="gate_final_status",
                block_pipeline_on_fail=estrito,
                # 🟡 em 15 de 15 sessões por construção (levantamento de 24/10/2026): a proposta aberta vai à lista do de
                # acordo (PR 3), e a decisão que o PO já registrou não é ressalva (`tools/juizes_produto.py`)
                recontar_decisoes_do_po=True,
                contrato_no_de_acordo=True,
            ),
            # O one-pager está fechado: os textos-chave ganham ID antes da spec, que os cita, e do de acordo, que mostra a
            # tabela (PR 7, D1). Na correção pontual roda também — o texto que o editor trocou guarda o ID.
            TextosChaveAgent(
                name="A044bTextosChave",
                description="Tabela de textos-chave com ID estável, montada por código do one-pager aprovado (§4, §12a, §9, §11): o texto igual ou trocado no mesmo lugar guarda o ID, o novo ganha o próximo número.",
            ),
            spec_loop,
            _fidelidade_de_produto(kw),
            # Depois da spec, de propósito: o bloco 11 já passou pelo A046, então o resumido
            # copia códigos conferidos em vez dos que a seção 2 do canônico ainda podia trocar.
            _resumido_loop(kw, settings),
        ],
    )


def _fidelidade_de_produto(kw: Dict[str, Any]):
    """A conferência final: núcleo, one-pager e spec contra todos os pedidos do PO e o briefing.
    Com 🔴 aqui, o *de acordo* de produto é recusado (`pipeline/passagem.py`)."""
    return get_fidelidade_check("A060FidelidadeProduto", status_key="fidelidade_status", report_key="fidelidade_report",
                                documentos=["nucleo_narrativo", "one_pager", "spec_missao"],
                                onde="fim de produto", etapas_pedido=list(ETAPAS_DO_PEDIDO_DE_PRODUTO), **kw)


#: Os pedidos de refazer que produto confere: os de produto e os registros antigos, sem etapa. O pedido feito a
#: design ou a dev é conferido no fim daquela etapa (A094, A51): aqui ele reprovava o núcleo por um botão de tela.
ETAPAS_DO_PEDIDO_DE_PRODUTO = ("produto", "")


#: Agentes do estágio parcial "spec" (correção a partir da spec), na ordem em que rodam.
SPEC_AGENT_IDS = ["A045SpecMissao", "A045bCompletudeSpec", "A045cCompletudeSpecSplit", "A045dCompletudeRodada",
                  "A046BnccCheck", "A047ManifestoCheckProduto", "A048EvidenciaCheck",
                  "A050PerguntasCheck", "A051JuizPerguntas", "A052JuizPerguntasCheck",
                  "A054ConteudoAprovadoSpec", "A057aBancaProdutoNarrativa", "A057bBancaPedagogiaBncc",
                  "A058BancaConsolidacao", "A059SpecCheck", "A060FidelidadeProduto", "A061OnePagerResumido",
                  "A062ConteudoAprovadoResumido", "A063ResumidoRodada"]

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
    {"id": "A018EvidenciaOnePager", "name": "018 · Contrato de evidência do one-pager (determinístico)", "icon": "🔬", "output_key": "evidencia_one_pager_report", "prompt_file": None, "description": "O §12a onde ele nasce: toda habilidade da seção 2 com linha, Canal A e regra ternária por extenso, e Canal B com o nível de cada alternativa. Forma antes de voto: o que falha aqui volta ao autor sem gastar o comitê."},
    {"id": "A019aComiteCanalACurriculo", "name": "019a · Comitê dos canais: A·1 Currículo", "icon": "🧑‍⚖️", "output_key": "comite_canal_a_curriculo", "prompt_file": "produto/comite_canal_a_curriculo.md", "description": "Painel A: a ação do Canal A de cada habilidade é o verbo e o objeto do texto oficial, na decisão onde o limiar mora."},
    {"id": "A019bComiteCanalAMedida", "name": "019b · Comitê dos canais: A·2 Medida", "icon": "🧑‍⚖️", "output_key": "comite_canal_a_medida", "prompt_file": "produto/comite_canal_a_medida.md", "description": "Painel A: a regra ternária é alcançável, sem buraco, sem Atingiu por sorte e calculável pelo que o evento registra."},
    {"id": "A019cComiteCanalAVivencia", "name": "019c · Comitê dos canais: A·3 Vivência e idade", "icon": "🧑‍⚖️", "output_key": "comite_canal_a_vivencia", "prompt_file": "produto/comite_canal_a_vivencia.md", "description": "Painel A: a ação é verbo nativo, vivida na decisão e dentro dos tetos da faixa."},
    {"id": "A019dComiteCanalBCurriculo", "name": "019d · Comitê dos canais: B·1 Currículo", "icon": "🧑‍⚖️", "output_key": "comite_canal_b_curriculo", "prompt_file": "produto/comite_canal_b_curriculo.md", "description": "Painel B: a pergunta mede a habilidade da linha, e o Atingiu é domínio pleno e autônomo."},
    {"id": "A019eComiteCanalBMedida", "name": "019e · Comitê dos canais: B·2 Medida", "icon": "🧑‍⚖️", "output_key": "comite_canal_b_medida", "prompt_file": "produto/comite_canal_b_medida.md", "description": "Painel B: as três alternativas discriminam os níveis e nenhuma se elimina pela linguagem."},
    {"id": "A019fComiteCanalBExperiencia", "name": "019f · Comitê dos canais: B·3 Experiência", "icon": "🧑‍⚖️", "output_key": "comite_canal_b_experiencia", "prompt_file": "produto/comite_canal_b_experiencia.md", "description": "Painel B: depois do Refletir sem repeti-lo, na língua do ambiente, sem vazar resultado e dentro do teto."},
    {"id": "A020VotosCanalA", "name": "020 · Votos do painel A (determinístico)", "icon": "🗳️", "output_key": "comite_canal_a_report", "prompt_file": None, "description": "Conta os três votos do painel A (mecânica e Canal A) com as citações conferidas: unanimidade aprova; sem ela, a missão volta ao núcleo (A004) e às seções de apoio (A014)."},
    {"id": "A021VotosCanalB", "name": "021 · Votos do painel B (determinístico)", "icon": "🗳️", "output_key": "comite_canal_b_report", "prompt_file": None, "description": "Conta os três votos do painel B (Canal B): unanimidade aprova; sem ela, a missão volta a quem a escreve. Sem Canal B na missão, os juízes são dispensados sem custo."},
    {"id": "A022ComiteCanaisRodada", "name": "022 · Saída do comitê dos canais (determinístico)", "icon": "🔁", "output_key": "comite_canais_rodada", "prompt_file": None, "description": "Os dois painéis unânimes e o §12a em forma encerram o loop; senão, núcleo e seções de apoio reescrevem com os relatórios, até COMITE_MAX_RODADAS (padrão 5). Esgotado, segue 🟡 com os votos vencidos no parecer."},
    {"id": "A023BriefEscopoSplit", "name": "023 · Brief de escopo separado (determinístico)", "icon": "🔀", "output_key": "brief_escopo_status", "prompt_file": None, "description": "Separa o brief de escopo do one-pager canônico para `brief_escopo`, antes do revisor."},
    {"id": "A024ContratoProdutoCheck", "name": "024 · Contrato de plataforma e origem dos parâmetros (determinístico)", "icon": "📡", "output_key": "contrato_produto_report", "prompt_file": None, "description": "Lint do one-pager a cada rodada do gate: canal de sala por polling (nunca WebSocket), estado no servidor (sem localStorage/IndexedDB), SAEB só nos anos avaliados, número com origem ou marcador. O gate aplica; o revisor corrige."},
    {"id": "A025JuizContratoProduto", "name": "025 · Juiz do contrato de produto", "icon": "⚖️", "output_key": "contrato_produto_status", "prompt_file": None, "description": "Juiz de achados sobre `Contrato de plataforma e origem dos parâmetros`: retira o achado de uso vedado quando o texto só cita para vedar — com citação literal conferida."},
    {"id": "A026GateEstrutural", "name": "026 · Gate estrutural", "icon": "🚧", "output_key": "gate_estrutural_report", "prompt_file": "produto/026_gate_estrutural.md", "description": "critérios: estrutura, ambiente, logística, evidências, viabilidade e infraestrutura."},
    {"id": "A027GateEstruturalCheck", "name": "027 · Veredito do gate (determinístico)", "icon": "🔀", "output_key": "gate_estrutural_status", "prompt_file": None, "description": "Lê o envelope JSON e decide repetir, seguir ou bloquear."},
    {"id": "A028RevisorOnePager", "name": "028 · Revisor do one-pager", "icon": "🩹", "output_key": "one_pager", "prompt_file": "produto/revisor_one_pager.md", "description": "Aplica o complemento pronto-pra-colar do gate; não inventa decisão de produto."},
    {"id": "A029aAvaliacaoPedagogica", "name": "029a · Avaliação pedagógica", "icon": "🎓", "output_key": "avaliacao_pedagogica_report", "prompt_file": "produto/029a_avaliacao_pedagogica.md", "description": "BNCC, professor, guardrails e affordance × guardrail (paralelo com P3)."},
    {"id": "A029bExperienciaEstudante", "name": "029b · Experiência do estudante", "icon": "🧒", "output_key": "experiencia_aluno_report", "prompt_file": "produto/029b_experiencia_estudante.md", "description": "Carga cognitiva, faixa etária e agência (paralelo com P2)."},
    {"id": "A029cAdequacaoPedagogica", "name": "029c · Adequação pedagógica", "icon": "⚖️", "output_key": "adequacao_report", "prompt_file": "produto/029c_adequacao_pedagogica.md", "description": "Seis eixos com parecer e ajustes acionáveis: currículo, demanda cognitiva, carga acidental, viabilidade na escola pública, evidência de aprendizagem e equidade. Parecer entra como ressalva, não bloqueia."},
    {"id": "A030AvaliacaoCheck", "name": "030 · Veredito da avaliação pedagógica (determinístico)", "icon": "🔀", "output_key": "avaliacao_status", "prompt_file": None, "description": "Lê o veredito da avaliação pedagógica (critérios 4.x, 5.1/5.2, 8.x)."},
    {"id": "A031ExperienciaCheck", "name": "031 · Veredito da experiência do estudante (determinístico)", "icon": "🔀", "output_key": "experiencia_status", "prompt_file": None, "description": "Lê o veredito da experiência do estudante (3.x, 6.x). Sinaliza, não trava: os tetos desta dimensão são [EXTRAPOLAÇÃO], não medida."},
    {"id": "A032AdequacaoCheck", "name": "032 · Veredito da adequação pedagógica (determinístico)", "icon": "🔀", "output_key": "adequacao_status", "prompt_file": None, "description": "Lê o veredito do parecer de adequação pedagógica."},
    {"id": "A033AdequacaoCheck", "name": "033 · Veredito do parecer (determinístico)", "icon": "🔀", "output_key": "avaliacoes_rodada", "prompt_file": None, "description": "Parecer sem ajuste exigido encerra o ciclo das avaliações; com ajuste, devolve ao revisor do one-pager."},
    {"id": "A034RevisorOnePagerParecer", "name": "034 · Revisor movido pelo parecer", "icon": "🩹", "output_key": "one_pager", "prompt_file": "produto/revisor_one_pager.md", "description": "Aplica ao one-pager os ajustes exigidos pelo parecer de adequação (padrão: 2 rodadas; AVALIACOES_MAX_RODADAS=1 desliga)."},
    {"id": "A035OnePagerPoCheck", "name": "035 · One-pager do PO preservado, depois dos pareceres (determinístico)", "icon": "📌", "output_key": "one_pager_po_report", "prompt_file": None, "description": "A conferência final, depois do gate estrutural, dos pareceres e dos revisores: trecho do one-pager do PO perdido sem pedido deixa produto 🔴 e vai ao restaurador."},
    {"id": "A036OnePagerPoRodada", "name": "036 · Saída da conferência do one-pager do PO (determinístico)", "icon": "🔀", "output_key": "one_pager_po_rodada", "prompt_file": None, "description": "Preservado segue para o gate final; perdido vai ao restaurador uma vez."},
    {"id": "A037RestaurarOnePagerPo", "name": "037 · Restaurador do one-pager do PO", "icon": "🧷", "output_key": "one_pager", "prompt_file": "produto/037_restaurar_one_pager_po.md", "description": "Devolve ao one-pager, literalmente, os trechos do PO que a esteira reescreveu; o que um gate ou parecer pedia vira [PROPOSTA — validar com PO]."},
    {"id": "A038EvidenciaOnePagerFinal", "name": "038 · Contrato de evidência, antes do comitê final (determinístico)", "icon": "🔬", "output_key": "evidencia_one_pager_report", "prompt_file": None, "description": "O §12a de novo, sobre o one-pager depois do gate estrutural, dos pareceres e dos revisores."},
    {"id": "A039ContaDaViradaOnePager", "name": "039 · Conta da virada no one-pager (determinístico)", "icon": "🧮", "output_key": "mecanica_one_pager_report", "prompt_file": None, "description": "Refaz o ranking da tabela 1.3 sobre o one-pager de agora: os revisores podem ter mudado a mecânica depois do núcleo."},
    {"id": "A040aComiteFinalPedagogia", "name": "040a · Comitê final: F·1 Pedagogia", "icon": "🧑‍⚖️", "output_key": "comite_final_pedagogia", "prompt_file": "produto/comite_final_pedagogia.md", "description": "Comitê final: limiar vivido, aha com os seis passos e canais ainda coerentes depois das revisões."},
    {"id": "A040bComiteFinalQualidade", "name": "040b · Comitê final: F·2 Qualidade de produto", "icon": "🧑‍⚖️", "output_key": "comite_final_qualidade", "prompt_file": "produto/comite_final_qualidade.md", "description": "Comitê final: uma missão só, tempos e tetos que fecham, professor claro e construível sem inventar."},
    {"id": "A040cComiteFinalImersao", "name": "040c · Comitê final: F·3 Imersão", "icon": "🧑‍⚖️", "output_key": "comite_final_imersao", "prompt_file": "produto/comite_final_imersao.md", "description": "Comitê final: porta, troca e chegada diegéticas, verbos nativos e virada mostrada pelo ambiente."},
    {"id": "A041VotosFinal", "name": "041 · Votos do comitê final (determinístico)", "icon": "🗳️", "output_key": "comite_final_report", "prompt_file": None, "description": "Conta os votos de pedagogia, qualidade e imersão com as citações conferidas: unanimidade aprova; sem ela, a missão volta ao A004 e ao A014."},
    {"id": "A042ComiteFinalRodada", "name": "042 · Saída do comitê final (determinístico)", "icon": "🔁", "output_key": "comite_final_externo_rodada", "prompt_file": None, "description": "Os três de acordo, o §12a em forma e a conta da virada fechando encerram o loop; senão, a cadeia de produto roda de novo a partir do núcleo, até COMITE_FINAL_MAX_RODADAS (padrão 2). Esgotado, segue 🟡."},
    {"id": "A043GateFinalProduto", "name": "043 · Gate final de produto", "icon": "🏁", "output_key": "gate_final_report", "prompt_file": "produto/043_gate_final.md", "description": "Coerência entre missão e vereditos; libera ou bloqueia para design/dev."},
    {"id": "A044GateFinalProdutoCheck", "name": "044 · Veredito final (determinístico)", "icon": "🔀", "output_key": "gate_final_status", "prompt_file": None, "description": "Lê o envelope do gate final."},
    {"id": "A044bTextosChave", "name": "044b · Textos-chave com ID (determinístico)", "icon": "🔑", "output_key": "textos_chave_tabela", "prompt_file": None, "description": "Os textos-chave do one-pager aprovado — aspas do §4, pergunta e alternativas do Canal B (§12a), opções de cada escolha com o nº de opções, roteiro do professor (§9), podcast (§11) — numa tabela com ID estável (`TC-07`, a opção `TC-12.2`), montada por código. O cartão do de acordo a mostra; design e dev a recebem no conteúdo aprovado, e o código copia cada texto até a copy (PR 7)."},
    {"id": "A045SpecMissao", "name": "045 · Spec da missão", "icon": "📜", "output_key": "spec_missao", "prompt_file": "produto/045_spec_missao.md", "description": "Os 12 blocos da spec — contrato contra o qual design e dev constroem."},
    {"id": "A045bCompletudeSpec", "name": "045b · Completude da spec", "icon": "🧩", "output_key": "completude_spec", "prompt_file": "produto/046_completude_spec.md", "description": "O que o D0 fechava no design e é de produto (estado, handoff, evidência, dados e retenção, duração e tetos, painel docente, PQ e KPI, texto do professor, revezamento), em produto: decisões [CP-n] com base declarada no bloco 15 da spec, padrões da plataforma aplicados e listados no de acordo, e o que é do PO como [PARÂMETRO]/[PROPOSTA]/[ABERTO — dono: PO] na lista do de acordo. Nas rodadas seguintes do loop só roda se a spec perdeu o bloco 15; na correção pontual não roda."},
    {"id": "A045cCompletudeSpecSplit", "name": "045c · Spec com o bloco 15 (determinístico)", "icon": "✂️", "output_key": "relatorio_completude", "prompt_file": None, "description": "Monta em código a spec de produto — a do A045 com o bloco 15 da completude no lugar, o resto descartado —, separa o relatório de completude e registra `completude_status`. [PARÂMETRO]/[PROPOSTA] fechado pela completude sem parecer datado do PO bloqueia."},
    {"id": "A045dCompletudeRodada", "name": "045d · Saída da completude (determinístico)", "icon": "🔀", "output_key": "completude_rodada", "prompt_file": None, "description": "Completude conferida encerra o loop dela; reprovada pelo código (decidiu no lugar do PO, ou veio sem o bloco 15) volta só a ela, uma vez, com os achados — o autor da spec não reescreve por isso."},
    {"id": "A046BnccCheck", "name": "046 · Conformidade BNCC Computação (determinístico)", "icon": "📚", "output_key": "bncc_report", "prompt_file": None, "description": "Bloco 11 × lista oficial do MEC: código existe, é do ano da missão e inclui letramento digital. Não conforme bloqueia design e dev."},
    {"id": "A047ManifestoCheckProduto", "name": "047 · Ficha do manifesto (determinístico)", "icon": "🪪", "output_key": "manifesto_report", "prompt_file": None, "description": "Bloco 0 da spec × listas fechadas da plataforma, conferido ainda em Produto: campo errado volta para quem escreveu a spec, em vez de custar o design inteiro."},
    {"id": "A048EvidenciaCheck", "name": "048 · Matriz de evidência pedagógica (determinístico)", "icon": "🔬", "output_key": "evidencia_report", "prompt_file": None, "description": "Bloco 9 × bloco 11: grau `scored` com dois sinais nomeados, toda habilidade com momento em tela e medida ligada, gabarito declarado no servidor."},
    {"id": "A049JuizEvidencia", "name": "049 · Juiz da matriz de evidência", "icon": "⚖️", "output_key": "evidencia_status", "prompt_file": None, "description": "Juiz de achados sobre `Matriz de evidência pedagógica`: retira o achado de uso vedado quando o texto só cita para vedar — com citação literal conferida."},
    {"id": "A050PerguntasCheck", "name": "050 · Perguntas de produto, sub-bloco 9f (determinístico)", "icon": "❓", "output_key": "perguntas_report", "prompt_file": None, "description": "As cinco perguntas de produto: quantidade fechada, decisão com limiar, corte do vocabulário, e a ação que responde cada uma declarada na tabela de eventos do bloco 9 com payload que mede."},
    {"id": "A051JuizPerguntas", "name": "051 · Juiz das perguntas de produto", "icon": "⚖️", "output_key": "juiz_perguntas_report", "prompt_file": "produto/051_juiz_perguntas.md", "description": "O que não se confere por regex: a pergunta muda uma decisão nossa, é sobre o produto e não sobre a criança, a ação nomeada a responde, e ela não é uma transversal repintada."},
    {"id": "A052JuizPerguntasCheck", "name": "052 · Veredito do juiz das perguntas (determinístico)", "icon": "🔀", "output_key": "juiz_perguntas_status", "prompt_file": None, "description": "Lê o envelope do juiz: ❌ em pergunta declarada pelo PO bloqueia; ❌ só em proposta segue como ressalva para o PO decidir."},
    {"id": "A053RastroSpec", "name": "053 · Rastro de lacunas da spec (determinístico)", "icon": "🧭", "output_key": "rastro_spec_report", "prompt_file": None, "description": "Marcadores de lacuna na spec, por dono: o de produto ou de insumo volta para quem escreveu a spec; a decisão do PO fica 🟡 no semáforo do parecer; o de design e o de dev ficam para a etapa delas."},
    {"id": "A054ConteudoAprovadoSpec", "name": "054 · Spec × one-pager aprovado (determinístico)", "icon": "📎", "output_key": "conteudo_aprovado_spec_report", "prompt_file": None, "description": "A spec traduz o one-pager que o PO aprovou: mesmas habilidades do contrato de evidência (§12a), mesmo tempo total em tela (§10) e o podcast (§11) declarado. Ressalva de parecer que o PO não incorporou não muda a spec."},
    {"id": "A055ConteudoAprovado", "name": "055 · Conteúdo aprovado para a banca de produto (determinístico)", "icon": "🔀", "output_key": None, "prompt_file": None, "description": "Grava as seções literais do one-pager para a banca do fim de produto."},
    {"id": "A056EscopoBanca", "name": "056 · Escopo da banca de produto (determinístico)", "icon": "🔀", "output_key": None, "prompt_file": None, "description": "Grava o escopo da banca na posição «produto»."},
    {"id": "A057aBancaProdutoNarrativa", "name": "057a · Banca no fim de produto: produto e narrativa", "icon": "🅰️", "output_key": "banca_produto_narrativa", "prompt_file": "dev/validacao_produto_narrativa.md", "description": "Os critérios PROD da banca que a spec decide, antes do parecer do PO. O achado volta ao autor da spec na próxima rodada."},
    {"id": "A057bBancaPedagogiaBncc", "name": "057b · Banca no fim de produto: pedagogia e BNCC", "icon": "🅲", "output_key": "banca_produto_pedagogia", "prompt_file": "dev/validacao_pedagogia_bncc.md", "description": "Os critérios PED da banca sobre a spec, antes do parecer do PO."},
    {"id": "A058BancaConsolidacao", "name": "058 · Banca de produto (determinístico)", "icon": "⚖️", "output_key": "banca_produto_report", "prompt_file": None, "description": "Veredito da banca no fim de produto: o pior das dimensões, com os bloqueantes lidos dos arquivos de critério. 🔴 devolve a spec ao autor e, esgotadas as rodadas, recusa o de acordo."},
    {"id": "A059SpecCheck", "name": "059 · Veredito da spec (determinístico)", "icon": "🔀", "output_key": "spec_rodada", "prompt_file": None, "description": "Currículo e manifesto conformes encerram o loop da spec; reprovados devolvem ao autor com os dois relatórios."},
    {"id": "A060FidelidadeProduto", "name": "060 · Fidelidade ao pedido do PO e ao briefing", "icon": "📌", "output_key": "fidelidade_report", "prompt_file": None, "description": "Núcleo, one-pager e spec contra todos os pedidos do PO e o briefing. Pedido sem prova é 🔴 e recusa o de acordo de produto; conflito com regra da esteira vira decisão do PO."},
    {"id": "A061OnePagerResumido", "name": "061 · One-pager resumido", "icon": "🗂️", "output_key": "one_pager_resumido", "prompt_file": "produto/061_one_pager_resumido.md", "description": "O one-pager no formato do time de produto para avaliação pedagógica: ficha, ideia, componente curricular, socioemocionais, 6 etapas, professor, contrato de evidência ternário e takeaway. Sai em .md, .docx e .html."},
    {"id": "A062ConteudoAprovadoResumido", "name": "062 · Resumido × one-pager aprovado (determinístico)", "icon": "📎", "output_key": "conteudo_aprovado_resumido_report", "prompt_file": None, "description": "As habilidades do bloco 11, o tempo em tela do §10 e o Canal B com o texto do §12a no resumido que o time lê para aprovar. Divergência volta ao autor do resumido."},
    {"id": "A063ResumidoRodada", "name": "063 · Veredito do resumido (determinístico)", "icon": "🔁", "output_key": "resumido_rodada", "prompt_file": None, "description": "Resumido fiel encerra o loop; divergente volta ao autor com o relatório, até o teto de rodadas."},
]

PRODUTO_METADATA_SPEC = [m for m in PRODUTO_METADATA if m["id"] in SPEC_AGENT_IDS]
