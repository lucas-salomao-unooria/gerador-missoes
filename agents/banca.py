"""A banca de validação nas quatro posições da esteira (decisão do usuário, 08/10/2026).

Até 08/10/2026 a banca rodava uma vez, dentro do dev, depois do handoff, do brief e do banco — e reescrevia jornada,
fluxo, telas e copy depois do parecer de design. Agora, com os mesmos critérios e o mesmo modelo:

- **fim de produto** (dimensões A e C, dentro do loop da spec): o achado volta ao autor da spec antes do parecer;
- **fim de design** (A e B, dentro do loop do QA): o achado vira ticket para o dono refazer antes do parecer;
- **entrada do dev** (A, B e C, antes de qualquer agente de dev): segunda verificação, com a visão cruzada de produto e
  design. Não reescreve nada; se bloqueia, o resto do dev não roda — validar dev sobre o que vai mudar é desperdício;
- **dev** (D e E, depois do handoff): conserta só documento de dev.

O que muda entre as posições é o escopo (`tools/banca.ESCOPOS`), gravado no estado logo antes das dimensões.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.parallel_agent import ParallelAgent
from google.genai import types

from agents.base import create_llm_agent
from agents.callbacks import marcar_heranca
from agents.checkers import ConsolidacaoBancaAgent, EscopoBancaAgent
from prompts import load_prompt

#: Letra da dimensão → (sufixo do nome, prompt, sufixo da chave de saída).
DIMENSOES_LLM: Dict[str, tuple] = {
    "A": ("ProdutoNarrativa", "dev/39_validacao_produto_narrativa.md", "narrativa"),
    "B": ("DesignImersao", "dev/40_validacao_design_imersao.md", "imersao"),
    "C": ("PedagogiaBncc", "dev/41_validacao_pedagogia_bncc.md", "pedagogia"),
}


def chaves_de_saida(posicao: str, dimensoes: str) -> List[str]:
    return [f"banca_{posicao}_{DIMENSOES_LLM[d][2]}" for d in dimensoes]


def get_banca(posicao: str, dimensoes: str, prefixo: str, *, rotulo: str, titulo: str, report_key: str,
              status_key: str, comparar_com: Optional[Dict[str, str]] = None, **kw: Any) -> List[Any]:
    """`[escopo, dimensões em paralelo, consolidação]` para encaixar numa etapa. A consolidação grava o status."""
    juizes = [
        create_llm_agent(
            name=f"{prefixo}Banca{DIMENSOES_LLM[d][0]}",
            description=f"Banca ({posicao}): dimensão {d}, com o escopo desta posição.",
            instruction=load_prompt(DIMENSOES_LLM[d][1]),
            output_key=chave,
            before_agent_callback=marcar_heranca,
            deterministico=True,
            **kw,
        )
        for d, chave in zip(dimensoes, chaves_de_saida(posicao, dimensoes))
    ]
    return [
        EscopoBancaAgent(name=f"{prefixo}EscopoBanca", posicao=posicao,
                         description=f"Grava o escopo da banca na posição «{posicao}»."),
        ParallelAgent(name=f"{prefixo}Banca", description=f"Banca ({posicao}): dimensões {', '.join(dimensoes)} em paralelo.",
                      sub_agents=juizes, before_agent_callback=marcar_heranca),
        ConsolidacaoBancaAgent(
            name=f"{prefixo}BancaConsolidacao",
            description=f"{rotulo}: o veredito é o pior das dimensões, com os bloqueantes lidos dos arquivos de critério.",
            fontes=chaves_de_saida(posicao, dimensoes), report_key=report_key, status_key=status_key,
            rotulo=rotulo, titulo=titulo, gravar_status=True, comparar_com=dict(comparar_com or {}),
        ),
    ]


KEY_STATUS_ENTRADA = "banca_entrada_status"


def pular_se_banca_de_entrada_bloqueou(callback_context: CallbackContext) -> Optional[types.Content]:
    """Com a banca de entrada do dev 🔴, nenhum agente de dev roda: o que ele construiria sobre produto ou design que
    vão mudar seria refeito de qualquer jeito. `BANCA_ENTRADA_ESTRITA=false` deixa seguir (o 🔴 continua no semáforo).
    """
    from config import get_settings

    if callback_context.state.get(KEY_STATUS_ENTRADA) == "bloqueado" and get_settings().banca_entrada_estrita:
        return types.Content(role="model", parts=[types.Part(text=(
            "⛔ A banca de entrada do dev bloqueou produto ou design: o dev não rodou. Os bloqueios, por dono, estão em "
            "`dev/00b-banca-entrada.md`; quem conserta é a etapa dona, pela devolução."))])
    return marcar_heranca(callback_context)
