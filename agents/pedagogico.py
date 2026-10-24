"""Os passos determinísticos do one-pager pedagógico, que fecha o design desde o PR 10 (`tools/pedagogico.py`).

- `ContratoNoPedagogicoAgent` (A120b), no loop do pedagógico, logo depois do redator: monta por código o que o PO
  aprovou — habilidades, a pergunta do fim, os tempos, o podcast e o roteiro da conversa — e devolve ao texto aprovado a
  citação quase igual de um texto-chave. Roda também na correção pontual, em que o redator não roda, e registra o que
  mudou como troca: o documento continua sendo a versão anterior mais as trocas.
- `PedagogicoNoDevAgent` (A119b), no dev: o pedagógico aprovado no de acordo de design, conferido contra o retrato do
  design (e devolvido a ele se mudou), e as pendências do dev numa seção própria, guardada à parte.
- `pular_pedagogico_sem_documento_na_correcao_pontual`: na correção pontual de uma sessão desenhada antes do PR 10, sem
  pedagógico para travar, o loop não roda — o pedagógico nasce no próximo refazer de design, como o bloco 15 da
  completude nasce no próximo refazer de produto.
"""
from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, Optional

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types
from typing_extensions import override

from .callbacks import KEY_MODO_CORRECAO, extrair_envelope, extrair_slug

#: Rótulo do guarda do dev (A119b): é por ele que a degradação se registra e que a herança sabe de que etapa ela é.
ROTULO_NO_DEV = "Pedagógico aprovado, no dev"

#: O que o loop do pedagógico emite quando não roda na correção pontual de uma sessão sem pedagógico.
PEDAGOGICO_PULADO_NA_CORRECAO = (
    "⏭️ OnePagerPedagogicoLoop não executado — correção pontual de uma missão desenhada antes de 24/10/2026, sem "
    "one-pager pedagógico para travar: ele nasce no próximo refazer de design, que o monta sobre o contrato.")


def pular_pedagogico_sem_documento_na_correcao_pontual(callback_context: CallbackContext) -> Optional[types.Content]:
    """before_agent_callback do loop do pedagógico: na correção pontual sem pedagógico, o loop não roda.

    Na correção pontual os autores não escrevem nada além das trocas (`agents.callbacks.travar_documento_na_correcao_
    pontual`); o redator do pedagógico sem documento para travar escreveria um inteiro — conteúdo além do pedido. As
    três missões desenhadas antes do PR 10 que o usuário vai refazer (exp02em1b, exp01em1b e exp03em1b) não têm
    pedagógico: no refazer de design ele é gerado; na correção pontual, não."""
    from pipeline.artifacts import e_mensagem_de_pulo
    from tools.pedagogico import KEY

    state = callback_context.state
    if state.get(KEY_MODO_CORRECAO) != "pontual":
        return None
    documento = state.get(KEY)
    if isinstance(documento, str) and documento.strip() and not e_mensagem_de_pulo(documento):
        return None
    return types.Content(role="model", parts=[types.Part(text=PEDAGOGICO_PULADO_NA_CORRECAO)])


class ContratoNoPedagogicoAgent(BaseAgent):
    """Determinístico: o contrato no pedagógico, por código (`tools.pedagogico.montar`, PR 10).

    O redator escreve a narrativa de sala de aula; as habilidades com o texto oficial, a pergunta do fim e as alternativas,
    a tabela de tempos, o podcast e o roteiro da conversa entram aqui, copiados do one-pager aprovado, num subtítulo «Do
    one-pager aprovado — …» no fim da seção de cada um. Até o PR 10 o redator os escrevia: nas missões do bucket o Canal B
    saiu reescrito (exp09ef1b), o podcast sumiu (exp05ef1b, exp07ef1b) e o roteiro do debate foi parafraseado (exp01ef1b,
    exp07ef1b), e o time pedagógico aprovava uma terceira versão.
    """

    chave: str = "one_pager_pedagogico"

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from pipeline.artifacts import e_mensagem_de_pulo
        from tools import pedagogico as pg

        state = ctx.session.state
        documento = state.get(self.chave)
        delta: Dict[str, Any] = {}
        if not isinstance(documento, str) or not documento.strip() or e_mensagem_de_pulo(documento):
            msg = "⏭️ Contrato no pedagógico: sem documento para montar."
        else:
            estado = dict(state)
            novo = pg.montar(documento, estado)
            blocos = pg.blocos_do_contrato(estado)
            if novo != documento:
                delta[self.chave] = novo
                if state.get(KEY_MODO_CORRECAO) == "pontual":
                    # Na correção pontual o pedagógico é a versão anterior mais as trocas, e é isso que prova as ordens de
                    # não mexer (`edicao_pontual.reaplicar`, A094): o que a montagem mudou entra como troca, com o motivo —
                    # como a cópia dos textos-chave na copy (A078b, PR 7). Mudou porque o contrato mudou a montante (o
                    # passo de produto da cascata), ou porque a sessão é anterior ao PR 10 e não tinha os subtítulos.
                    from tools import edicao_pontual

                    trocas = edicao_pontual.trocas_por_linhas(self.chave, documento, novo, pg.MOTIVO_TROCA)
                    if trocas:
                        delta["edicoes_pontuais"] = (list(state.get("edicoes_pontuais") or [])
                                                     + edicao_pontual.como_dicts(trocas))
            msg = (f"📎 Contrato no pedagógico: {len(blocos)} subtítulo(s) «{pg.PREFIXO_BLOCO} …» montados por código "
                   f"({', '.join(nome for nome, _, _, _ in blocos) or 'nenhum'})"
                   + ("; o documento mudou." if novo != documento else "; nada mudou."))
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    content=types.Content(role="model", parts=[types.Part(text=msg)]),
                    actions=EventActions(state_delta=delta))


class PedagogicoNoDevAgent(BaseAgent):
    """Determinístico: o dev só acrescenta ao pedagógico (`tools.pedagogico.no_dev`, PR 10).

    O pedagógico é o que o time aprovou no de acordo de design. Aqui ele é conferido contra o retrato que o design gravou
    (`pedagogico_do_design`, A124): se algo no dev o mudou ou apagou, ele volta ao retrato e o gate fica 🔴 — mudar o
    pedagógico em dev é pedido no parecer (a triagem leva ao Design o que é do pedagógico) ou Devolver ao Design. As
    pendências da banca de dev e do rastro de lacunas do dev vão numa seção própria, guardada à parte
    (`pedagogico_pendencias_dev`), que a exportação junta no fim do documento: o texto aprovado não muda, nem a
    assinatura do design.
    """

    report_key: str = "pedagogico_dev_report"
    status_key: str = "pedagogico_dev_status"
    rotulo: str = ROTULO_NO_DEV
    estrito: bool = True

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from tools import pedagogico as pg

        from .checkers import limpar_degradacao, registrar_degradacao

        state = ctx.session.state
        resultado = pg.no_dev(dict(state))
        missao = extrair_slug(str(state.get("spec_missao") or state.get("one_pager") or "")) or ""
        relatorio = pg.relatorio_no_dev(resultado, missao)
        delta: Dict[str, Any] = {self.report_key: relatorio, self.status_key: resultado["status"],
                                 f"{self.status_key}_envelope": extrair_envelope(relatorio) or {},
                                 pg.KEY_SECAO_DEV: resultado["secao"]}
        if resultado["restaurar"] is not None:
            delta[pg.KEY] = resultado["restaurar"]
        if resultado["status"] == "bloqueado" and self.estrito:
            registrar_degradacao(state, delta, self.rotulo, f"{self.rotulo} reprovado: o pedagógico mudou no dev")
        elif resultado["status"] != "bloqueado":
            limpar_degradacao(state, delta, self.rotulo)
        marca = {"aprovado": "🟢", "amarelo": "🟡", "bloqueado": "🔴"}[resultado["status"]]
        msg = (f"{marca} {self.rotulo}: "
               + ("o texto aprovado no de acordo de design está como estava" if resultado["status"] == "aprovado" else
                  "; ".join(a["resumo"][:200] for a in resultado["achados"]))
               + (". Pendências do dev acrescentadas numa seção própria no fim." if resultado["secao"] else "."))
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    content=types.Content(role="model", parts=[types.Part(text=msg)]),
                    actions=EventActions(state_delta=delta))


#: Rótulo do gate de montagem do pedagógico (PR 10), como os do PR 4 em `agents/dev`.
ROTULO_MONTAGEM_PEDAGOGICO = "Pedagógico monta, não decide"


def get_one_pager_pedagogico_agent(**kw):
    """O redator do pedagógico (A120), que fecha o design desde o PR 10 (24/10/2026). Era o último passo do dev, e o time
    validava a missão pelos protótipos contra um one-pager de produto que não a descreve inteira."""
    from prompts import load_prompt

    from .base import create_llm_agent
    from .callbacks import copiar_textos_chave, desembrulhar_documento, marcar_heranca

    return create_llm_agent(
        name="A120OnePagerPedagogico",
        description="O fechamento do design e o documento do de acordo de design: a missão inteira em linguagem de sala de aula, com o papel do professor, os links do protótipo e as perguntas que só o time pedagógico responde. O LLM escreve a narrativa; o contrato entra por código (A120b).",
        instruction=load_prompt("dev/120_one_pager_pedagogico.md"),
        output_key="one_pager_pedagogico",
        before_agent_callback=marcar_heranca,
        after_agent_callback=[desembrulhar_documento("one_pager_pedagogico"), copiar_textos_chave("one_pager_pedagogico")],
        **kw,
    )


def build_fechamento_pedagogico(**kw) -> list:
    """O loop do pedagógico e o anexo literal, no fim do design: depois da banca, do QA e do rastro de lacunas de design
    (as pendências que ele lê), antes do parecer de design (PR 10). Os mesmos passos que rodavam no fim do dev — o redator
    A120 com a cópia dos textos-chave (PR 7), o A121, o juiz A122 e o anexo A124 —, mais a montagem do contrato por código
    (A120b) e o gate dela (A121b). Chamadas de modelo: as mesmas do dev (o redator e o juiz, por rodada); os passos novos
    são código."""
    from google.adk.agents.loop_agent import LoopAgent

    from config import get_settings
    from tools.conteudo_aprovado import SECOES_PEDAGOGICO
    from tools.pedagogico import KEY_RETRATO

    from .callbacks import marcar_heranca
    from .checkers import AnexoAprovadoAgent, RastroCheckAgent, SaidaDeLoopAgent
    from .juiz import get_juiz_de_contradicoes

    rodadas = max(1, get_settings().prd_max_rodadas)
    estrito = get_settings().esteira_estrita
    return [
        LoopAgent(
            name="OnePagerPedagogicoLoop",
            description="One-pager pedagógico ↔ contrato e conferência contra o one-pager aprovado, até bater ou esgotar as rodadas.",
            max_iterations=rodadas,
            # na correção pontual de uma missão desenhada antes do PR 10 não há pedagógico para travar: o loop não roda
            before_agent_callback=[pular_pedagogico_sem_documento_na_correcao_pontual, marcar_heranca],
            sub_agents=[
                get_one_pager_pedagogico_agent(**kw),
                ContratoNoPedagogicoAgent(
                    name="A120bContratoNoPedagogico",
                    description="Monta por código o que o PO aprovou num subtítulo «Do one-pager aprovado — …» no fim de cinco seções — as habilidades com o texto oficial, a pergunta do fim e as alternativas, a tabela de tempos, o podcast e o roteiro da conversa — e devolve ao texto aprovado a citação quase igual de um texto-chave.",
                    before_agent_callback=marcar_heranca,
                ),
                RastroCheckAgent(
                    name="A121ConteudoAprovadoPedagogico",
                    description="One-pager pedagógico × one-pager aprovado e spec: as habilidades do bloco 11, o tempo em tela do §10, o podcast do §11 e só caminhos de artefato que a sessão tem.",
                    modo="aprovado_pedagogico",
                    rotulo="Pedagógico × one-pager aprovado",
                    report_key="conteudo_aprovado_pedagogico_report",
                    status_key="conteudo_aprovado_pedagogico_status",
                    agente="conteudo-aprovado",
                    estrito=estrito,
                    before_agent_callback=marcar_heranca,
                ),
                # O pedagógico monta, não decide (PR 10), no molde do gate do PRD (PR 4): a narrativa contra o contrato.
                RastroCheckAgent(
                    name="A121bMontagemPedagogico",
                    description="A narrativa do pedagógico contra o contrato: número de regra sem origem, hipótese do §17 ou teto do §15 com outro número, texto-chave reescrito, origem de produto falsa e tempo de etapa fora do §10; e os subtítulos da esteira iguais ao contrato de agora.",
                    modo="montagem_pedagogico",
                    rotulo=ROTULO_MONTAGEM_PEDAGOGICO,
                    report_key="montagem_pedagogico_report",
                    status_key="montagem_pedagogico_status",
                    agente="montagem-pedagogico",
                    estrito=estrito,
                    before_agent_callback=marcar_heranca,
                ),
                # O documento que o time pedagógico aprova também não pode afirmar o contrário do aprovado — e era o único
                # sem juiz de contradições (auditoria do padrão ouro, 08/10/2026).
                get_juiz_de_contradicoes("A122CoerenciaPedagogico", documento_key="one_pager_pedagogico",
                                         referencia_key="conteudo_aprovado", report_key="coerencia_pedagogico_report",
                                         status_key="coerencia_pedagogico_status", dono="one-pager-pedagogico",
                                         rotulo="Coerência do pedagógico com o one-pager aprovado", etapa="design", **kw),
                SaidaDeLoopAgent(
                    name="A123PedagogicoRodada",
                    description="Pedagógico fiel e montado sobre o contrato encerra o loop; divergente volta ao redator com os relatórios.",
                    rotulo="One-pager pedagógico",
                    status_keys=["conteudo_aprovado_pedagogico_status", "montagem_pedagogico_status",
                                 "coerencia_pedagogico_status"],
                    rodada_key="pedagogico_rodada",
                    max_rounds=rodadas,
                    autor_keys=["one_pager_pedagogico"],
                ),
            ],
        ),
        AnexoAprovadoAgent(
            name="A124AnexoPedagogico",
            description="Cola no fim do pedagógico os tempos e cenários de aula, o podcast com o roteiro e o contrato de evidência do one-pager aprovado, literais, e grava o retrato do documento: o texto sobre o qual o de acordo de design é dado, que o dev confere.",
            chave="one_pager_pedagogico",
            secoes=list(SECOES_PEDAGOGICO),
            rotulo="Anexo do pedagógico",
            retrato_key=KEY_RETRATO,
            before_agent_callback=marcar_heranca,
        ),
    ]
