"""Callbacks e utilitários determinísticos do pipeline.

- Leitura do envelope JSON de roteamento (references/contrato-saida.md) que os gates
  devolvem ao final do relatório.
- `marcar_heranca`: before_agent_callback que pula um agente (ou um container inteiro)
  quando o pipeline foi bloqueado por um gate de produto em modo estrito.
- `limitar_resposta_de_ferramenta` / `barrar_ferramenta_sem_orcamento`: contenção do
  que as ferramentas MCP devolvem ao contexto do turno. Sem elas, um agente de design
  que pede telas ao Stitch acumula dezenas de respostas grandes, dumps de board e
  imagens de screenshot — tudo no MESMO turno, porque o
  histórico de chamada de ferramenta não é conversa e `include_contents="none"` não o
  descarta. Foi assim que o D2 estourou o teto de 1.048.576 tokens do Gemini com um
  prompt de 22 KB.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

from google.adk.agents.callback_context import CallbackContext
from google.genai import types

# Chaves de estado usadas pelo controle de fluxo
KEY_PIPELINE_BLOQUEADO = "pipeline_bloqueado"
KEY_PIPELINE_MOTIVO = "pipeline_bloqueio_motivo"
#: Todas as reprovações da execução, em ordem. `KEY_PIPELINE_MOTIVO` guarda só a primeira —
#: no modelo antigo as seguintes nem aconteciam, porque a esteira parava.
KEY_DEGRADACOES = "degradacoes"
#: Texto injetado nas instruções dos agentes a jusante de uma reprovação. É o que faz o
#: agente saber que constrói sobre base reprovada e marcar `[PROVISÓRIO]` o que derivar dali.
KEY_HERANCA = "heranca_degradada"
#: Agentes que rodaram sob herança degradada — alimenta a seção "o que saiu provisório"
#: do diagnóstico final.
KEY_AGENTES_DEGRADADOS = "agentes_degradados"

_JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)

STATUS_APROVADO = "aprovado"
STATUS_BLOQUEADO = "bloqueado"
STATUS_INDEFINIDO = "indefinido"

_APROVADO_TOKENS = ("🟢", "APROVADO", "LIBERADA PARA DESIGN/DEV", "APTO PARA CODIFICAR", "APROVADO PARA REVISÃO HUMANA")
#: "NÃO APROVADO" contém "APROVADO": sem o token próprio, o relatório sem envelope que reprovava era lido como
#: aprovado (auditoria de 08/10/2026).
_BLOQUEADO_TOKENS = ("🔴", "BLOQUEADO", "BLOQUEADA PARA DESIGN/DEV", "NÃO APTO", "IMPASSE", "NÃO APROVAD", "NAO APROVAD")


def extrair_envelope(texto: str) -> Optional[Dict[str, Any]]:
    """Retorna o último bloco ```json {...}``` do texto como dict (ou None)."""
    if not texto:
        return None
    matches = _JSON_BLOCK_RE.findall(texto)
    for raw in reversed(matches):
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and ("status" in data or "veredito" in data):
                return data
        except json.JSONDecodeError:
            continue
    return None


_ENVELOPE_BLOQUEADO = ("bloqueado", "bloqueada", "devolvido", "nao_apto", "não apto", "nao_passa", "não passa",
                       "vermelho", "🔴", "reprovado", "reprovada", "nao_aprovado", "não aprovado")


def inferir_status(texto: str, envelope: Optional[Dict[str, Any]] = None) -> str:
    """Normaliza o veredito de um relatório em aprovado | bloqueado | indefinido."""
    if envelope:
        # `status` e `veredito` juntos: o envelope {"status": "aprovado", "veredito": "vermelho"} era lido só pelo
        # primeiro campo preenchido e passava. Qualquer um dos dois reprovando, reprova.
        valores = [str(envelope.get(k) or "").strip().lower() for k in ("status", "veredito")]
        if any(v in _ENVELOPE_BLOQUEADO for v in valores):
            return STATUS_BLOQUEADO
        status = next((v for v in valores if v), "")
        if status in ("aprovado", "concluido", "concluído", "liberada", "apto", "passa", "verde", "🟢"):
            return STATUS_APROVADO
        # `aguarda_gate` é o D0 dizendo que a decisão cabe ao Gate 0 ou ao PO. Não existe loop
        # que devolva isso a um agente, então tratá-lo como bloqueio travava a esteira num
        # impasse insolúvel. É pendência humana: segue, e o dossiê registra como 🟡.
        if status == "aguarda_gate":
            return STATUS_APROVADO
        if status in ("aprovado_com_ressalvas", "apto_com_ressalvas", "ressalvas", "amarelo", "🟡"):
            return STATUS_APROVADO
        # D0 (fecha-lacunas): segue | segue_com_pendencias · D9 (ambiente-simulado): dormente | existente | novo
        if status in ("segue", "segue_com_pendencias", "dormente", "existente", "novo", "nao_aplicavel", "não aplicável"):
            return STATUS_APROVADO
    cabecalho = (texto or "")[:1500].upper()
    if any(tok in cabecalho for tok in _BLOQUEADO_TOKENS):
        return STATUS_BLOQUEADO
    if any(tok in cabecalho for tok in _APROVADO_TOKENS):
        return STATUS_APROVADO
    return STATUS_INDEFINIDO


def status_registrado(texto: str, envelope: Optional[Dict[str, Any]] = None) -> str:
    """O veredito COMO ELE FOI DADO — aprovado | amarelo | bloqueado | indefinido.

    `inferir_status` é binário de propósito: ela decide se a esteira segue, e para isso
    "aprovado com ressalvas" é seguir. Mas gravar esse mesmo valor no dossiê apagava a
    ressalva: em 14 execuções, nenhum gate de LLM apareceu como 🟡, embora os relatórios
    estivessem cheios de 🟡. O que o time lia era um verde que o juiz não deu.

    Os dois convivem: o roteamento usa `inferir_status`, o dossiê usa esta.
    """
    if envelope:
        if any(str(envelope.get(k) or "").strip().lower() in _ENVELOPE_BLOQUEADO for k in ("status", "veredito")):
            return STATUS_BLOQUEADO
        bruto = str(envelope.get("status") or envelope.get("veredito") or "").strip().lower()
        if bruto in ("aprovado_com_ressalvas", "apto_com_ressalvas", "ressalvas", "amarelo", "🟡",
                     "segue_com_pendencias", "parcial", "aprovado-com-pendencias-de-plataforma",
                     # o D0/D9 devolvendo a decisão ao Gate 0 ou ao PO: não é aprovação nem
                     # impedimento, é pendência humana — e era lida como bloqueio insolúvel,
                     # porque não existe loop que devolva a decisão a um agente.
                     "aguarda_gate"):
            return "amarelo"
    binario = inferir_status(texto, envelope)
    if binario == STATUS_APROVADO and envelope:
        achados = envelope.get("achados") or []
        if any(str(a.get("severidade", "")).lower() in ("atencao", "atenção", "oficio", "ofício",
                                                        "decisao_humana", "decisão humana")
               for a in achados if isinstance(a, dict)):
            return "amarelo"
    return binario


def marcar_heranca(callback_context: CallbackContext) -> Optional[types.Content]:
    """before_agent_callback: registra que este agente roda sobre uma base reprovada.

    **Nunca pula o agente.** Antes, quando um gate reprovava, este callback devolvia um
    `Content` — o ADK gravava esse texto no `output_key` e o agente não rodava. O efeito
    colateral era pior que o problema: sem PRD, sem one-pager e sem relatório, não sobrava
    nada para diagnosticar o que deu errado, e os artefatos tinham de ser lidos fora da
    ferramenta.

    Agora a esteira vai até o fim. O agente roda, enxerga `heranca_degradada` na própria
    instrução (injetada por `agents.base.create_llm_agent`) e marca `[PROVISÓRIO]` o que
    derivar da parte reprovada. Aqui só anotamos quem rodou assim, para o diagnóstico final.
    """
    if not callback_context.state.get(KEY_PIPELINE_BLOQUEADO):
        return None
    ja = callback_context.state.get(KEY_AGENTES_DEGRADADOS) or []
    if callback_context.agent_name not in ja:
        callback_context.state[KEY_AGENTES_DEGRADADOS] = [*ja, callback_context.agent_name]
    return None


def preservar_one_pager(callback_context: CallbackContext) -> None:
    """Guarda a primeira versão do one-pager antes de o revisor começar a sobrescrevê-la.

    `A028RevisorOnePager` grava na mesma chave que o autor (`one_pager`), de propósito —
    é assim que os 17 prompts a jusante leem sempre a versão corrente. O efeito colateral
    é que a versão original desaparecia: a spec tinha `spec_missao_gate0`, o one-pager não
    tinha equivalente. Sem ele, não há como mostrar o que mudou entre rodadas.
    """
    state = callback_context.state
    if state.get("one_pager") and not state.get("one_pager_gate0"):
        state["one_pager_gate0"] = state["one_pager"]


def texto_de_heranca(degradacoes: list) -> str:
    """Monta o aviso que vai para a instrução dos agentes a jusante."""
    if not degradacoes:
        return ""
    linhas = [
        "As etapas anteriores reprovaram nos gates abaixo. Construa assim mesmo, com o que existe,"
        " e marque `[PROVISÓRIO — depende de <gate>]` em tudo que derivar do que foi reprovado."
        " Não invente o que falta e não conserte o que não é seu: o diagnóstico final registra."
    ]
    for d in degradacoes:
        gate = d.get("gate", "?") if isinstance(d, dict) else str(d)
        motivo = d.get("motivo", "") if isinstance(d, dict) else ""
        linhas.append(f"- **{gate}** — {motivo}")
    return "\n".join(linhas)


def extrair_slug(one_pager: str) -> str:
    """Procura o identificador da missão no one-pager/spec; vazio se não houver."""
    if not one_pager:
        return ""
    # Novo formato primeiro (`exp05ef3b`), legado depois (`exp-NN-slug`, usado por missão
    # transversal e ferramenta de professor, que não têm ano nem bimestre).
    m = re.search(r"\bexp0[1-9](?:ef|em)[1-4]b\b", one_pager, re.IGNORECASE)
    if not m:
        m = re.search(r"\bexp-(?:\d{2,3}|xx)-[a-z0-9][a-z0-9-]*", one_pager, re.IGNORECASE)
    return m.group(0).lower() if m else ""


# --------------------------------------------------------------------- MCP: contenção
logger = logging.getLogger("callbacks")

#: Teto por STRING dentro da resposta de uma ferramenta.
MCP_STRING_MAX = 6_000
#: Teto para a resposta inteira de UMA chamada, já podada.
MCP_RESPOSTA_MAX = 24_000
#: Orçamento acumulado de resposta de ferramenta POR AGENTE. O Gemini aceita ~1M
#: tokens; isto reserva a maior parte para a instrução e para a saída.
MCP_ORCAMENTO_POR_AGENTE = 600_000

_BASE64_LONGO = re.compile(r"^[A-Za-z0-9+/=\s]{2000,}$")
_CHAVES_DE_MIDIA = ("inlinedata", "inline_data", "mimetype", "mime_type", "imagedata", "image_data", "base64")


def _chave_de_midia(chave: str) -> bool:
    return chave.lower().replace("-", "_") in _CHAVES_DE_MIDIA or "screenshot" in chave.lower()


def _podar(valor: Any, chave: str = "") -> Any:
    """Poda recursiva: imagem vira aviso, string longa é truncada, estrutura é preservada."""
    if isinstance(valor, str):
        if _BASE64_LONGO.match(valor) or (_chave_de_midia(chave) and len(valor) > 512):
            return (
                f"<captura de {len(valor)} caracteres removida do contexto. A chamada FUNCIONOU e o nó existe no "
                "arquivo — é isso que a captura prova. A imagem em si não é lida pelo modelo (chega como texto "
                "codificado), então a conferência VISUAL é do revisor humano: registre no relatório o que ele deve "
                "olhar, e não peça a captura de novo.>"
            )
        if len(valor) > MCP_STRING_MAX:
            return valor[:MCP_STRING_MAX] + f"\n…[cortado: mais {len(valor) - MCP_STRING_MAX} caracteres]"
        return valor
    if isinstance(valor, dict):
        return {k: _podar(v, str(k)) for k, v in valor.items()}
    if isinstance(valor, list):
        podada = [_podar(v, chave) for v in valor[:50]]
        if len(valor) > 50:
            podada.append(f"…[cortado: mais {len(valor) - 50} itens]")
        return podada
    return valor


def _tamanho(obj: Any) -> int:
    try:
        return len(json.dumps(obj, ensure_ascii=False, default=str))
    except Exception:
        return len(str(obj))


def _chave_do_orcamento(agent_name: str) -> str:
    # `temp:` não é persistido no estado da sessão nem salvo nos artefatos.
    return f"temp:mcp_gasto_{agent_name}"


def limitar_resposta_de_ferramenta(tool: Any, args: Dict[str, Any], tool_context: Any, tool_response: Any) -> Optional[Dict[str, Any]]:
    """after_tool_callback: poda a resposta e debita o orçamento do agente.

    Devolver um dict SUBSTITUI o que o modelo recebe. Imagem nunca volta ao contexto:
    o agente já a viu quando a pediu, e reenviá-la custa o turno inteiro.
    """
    bruto = _tamanho(tool_response)
    resposta = _podar(tool_response) if bruto > MCP_STRING_MAX else tool_response

    if _tamanho(resposta) > MCP_RESPOSTA_MAX:
        texto = json.dumps(resposta, ensure_ascii=False, default=str)[:MCP_RESPOSTA_MAX]
        resposta = {
            "resposta_truncada": True,
            "motivo": (
                f"A resposta de `{getattr(tool, 'name', 'ferramenta')}` tinha {bruto} caracteres e não cabe no contexto. "
                "Trabalhe com o trecho abaixo; não peça a mesma leitura de novo."
            ),
            "trecho": texto,
        }

    gasto = int(tool_context.state.get(_chave_do_orcamento(tool_context.agent_name), 0) or 0) + _tamanho(resposta)
    tool_context.state[_chave_do_orcamento(tool_context.agent_name)] = gasto
    if bruto > MCP_RESPOSTA_MAX:
        logger.info(
            "%s: resposta de %s podada de %d para %d caracteres (gasto acumulado: %d)",
            tool_context.agent_name, getattr(tool, "name", "?"), bruto, _tamanho(resposta), gasto,
        )
    return resposta if resposta is not tool_response else None


def barrar_ferramenta_sem_orcamento(tool: Any, args: Dict[str, Any], tool_context: Any) -> Optional[Dict[str, Any]]:
    """before_tool_callback: quando o orçamento do agente acaba, recusa e manda concluir.

    Devolver um dict PULA a ferramenta. É melhor o agente entregar o markdown com o
    board pela metade do que a execução inteira morrer com 400 do modelo.
    """
    gasto = int(tool_context.state.get(_chave_do_orcamento(tool_context.agent_name), 0) or 0)
    if gasto < MCP_ORCAMENTO_POR_AGENTE:
        return None
    logger.warning("%s: orçamento de MCP esgotado (%d caracteres) — recusando %s", tool_context.agent_name, gasto, getattr(tool, "name", "?"))
    return {
        "recusado": True,
        "motivo": (
            "Orçamento de contexto desta etapa esgotado: as respostas de ferramenta já somam "
            f"{gasto} caracteres. **Pare de chamar ferramentas agora** e entregue o documento "
            "em Markdown com o que já foi construído, declarando no relatório o que ficou por fazer "
            "no arquivo e por quê."
        ),
    }


#: O que a ideação grava quando o PO já trouxe o one-pager: o núcleo lê isto no lugar dos três candidatos.
IDEACAO_DISPENSADA = (
    "# Ideação de mecanismos — dispensada\n\n"
    "O PO anexou o one-pager da missão (`one_pager_po`): o mecanismo é o dele, já desenhado e aprovado. "
    "Não há candidato a comparar nem a escolher. O núcleo narrativo parte do one-pager do PO e só muda o que "
    "o pedido dele manda mudar."
)


def pular_juiz_sem_canal_b(chave: str):
    """before_agent_callback de um juiz do painel B: missão sem Canal B no §12a não tem pergunta a julgar.

    O juiz não roda e o voto dele é gravado como dispensado (aprova sem custo). O `Content` devolvido não vai sozinho
    para o `output_key` — só o que o callback põe no estado entra no evento —, por isso a gravação explícita.
    """
    def _callback(callback_context: CallbackContext) -> Optional[types.Content]:
        from tools.comite import envelope_dispensado
        from tools.evidencia import habilidades_com_canal_b

        com_b = habilidades_com_canal_b(str(callback_context.state.get("one_pager") or ""))
        if com_b is None or com_b:
            return None
        texto = envelope_dispensado("nenhuma habilidade do §12a tem Canal B: não há pergunta a julgar")
        callback_context.state[chave] = texto
        return types.Content(role="model", parts=[types.Part(text=texto)])

    return _callback


#: Os comitês cujo voto devolve a missão a quem a escreve (`agents/comite.py`).
STATUS_DOS_COMITES = ("comite_canal_a_status", "comite_canal_b_status", "comite_final_status")


def manter_nucleo_sem_achado_do_a004(callback_context: CallbackContext) -> Optional[types.Content]:
    """before_agent_callback do loop do núcleo dentro dos comitês: sem nada para o A004, o núcleo fica como está.

    Reprovada por um comitê, a missão volta ao núcleo e às seções de apoio. Quando nenhum comitê reprovado aponta
    achado para o A004 — nem achado sem autor — e o contrato do §12a está em forma, reescrever o núcleo só gastaria o
    autor, o micro-gate e o juiz de profundidade para devolver o mesmo texto. Na dúvida, o núcleo roda.
    """
    from tools import citacoes

    state = callback_context.state
    if not str(state.get("nucleo_narrativo") or "").strip():
        return None
    reprovados = [e for e in (state.get(f"{k}_envelope") for k in STATUS_DOS_COMITES)
                  if isinstance(e, dict) and str(e.get("status") or "") == "bloqueado"]
    evidencia_bloqueada = str(state.get("evidencia_one_pager_status") or "") == "bloqueado"
    if not reprovados and not evidencia_bloqueada:
        return None
    if any(str(a.get("autor") or "") in ("A004", "") for e in reprovados for a in e.get("achados") or []
           if isinstance(a, dict) and citacoes.bloqueante(a)):
        return None
    # O §12a reprovado só devolve o núcleo quando o achado é do contrato do foco primário, que o A004 escreve na seção 4.
    # Na 3ef2b (25/10/2026), com os dois painéis aprovados, o núcleo era reescrito a cada volta só porque o §12a do A014
    # vinha truncado — e a volta extra engordava o histórico do A004 até o 400 de 1 milhão de tokens (T23).
    if evidencia_bloqueada and _achado_do_12a_e_do_nucleo(state):
        return None
    return types.Content(role="model", parts=[types.Part(
        text="⏭️ Núcleo mantido: os comitês e o §12a não apontaram nada para o A004 nesta rodada; só as seções de apoio "
             "corrigem.")])


_RE_CODIGO_BNCC = re.compile(r"\bE[FMI]\d{2}[A-Z]{2}\d{2,3}\b")


def _achado_do_12a_e_do_nucleo(state: Any) -> bool:
    """Algum achado do §12a cita habilidade que o núcleo traz — o foco primário, cujo contrato é do A004. Sem envelope
    legível, ou achado sem código (o §12a ausente ou sem tabela, que o A014 monta), não é do núcleo; na dúvida sobre o
    envelope, o núcleo roda."""
    envelope = state.get("evidencia_one_pager_status_envelope")
    if not isinstance(envelope, dict):
        return True
    nucleo = str(state.get("nucleo_narrativo") or "")
    for achado in envelope.get("achados") or []:
        if not isinstance(achado, dict):
            continue
        if any(c in nucleo for c in _RE_CODIGO_BNCC.findall(str(achado.get("resumo") or ""))):
            return True
    return False


#: Modo da correção corrente (`pipeline/reexecucao.py`): `pontual` trava os autores; ausente na geração e no refazer.
KEY_MODO_CORRECAO = "modo_correcao"
#: Documentos cujo autor não roda na correção pontual: o texto deles é o que o editor deixou (`tools/edicao_pontual.py`).
KEY_DOCUMENTOS_TRAVADOS = "documentos_travados"


def travar_documento_na_correcao_pontual(chave: str):
    """before_agent_callback dos autores: na correção pontual, o documento já editado não é reescrito.

    O `Content` devolvido é o próprio documento — vai para o `output_key` sem mudar uma letra do que o editor deixou, e o
    agente não roda. Até 19/10/2026 a correção reexecutava cada autor sobre `anterior_<chave>`, e a troca de um número
    devolvia a spec com metade das linhas diferentes (exp03em1b, 13/10/2026). Fora da correção pontual, não faz nada.

    A única coisa que muda é o que a esteira escreve: no handoff e no PRD, as pendências de governança da liberação de
    produto, como estão agora (`documento_com_governanca`). O after_agent_callback do redator não roda com o agente
    travado, e nenhum passo determinístico reescreve o handoff depois do HandoffLoop (o PRD tem o A119): na correção
    pontual de dev da exp02ef1b — produto liberado pela conta design em 22/10/2026 15:27 —, o PRD saía com a pendência
    e o handoff sem ela (revisão do PR #75, 24/10/2026).
    """

    def _travar(callback_context: CallbackContext) -> Optional[types.Content]:
        state = callback_context.state
        if state.get(KEY_MODO_CORRECAO) != "pontual" or chave not in (state.get(KEY_DOCUMENTOS_TRAVADOS) or []):
            return None
        documento = str(state.get(chave) or "")
        if not documento.strip():
            return None
        documento = documento_com_governanca(state, chave, documento)
        return types.Content(role="model", parts=[types.Part(text=documento)])

    _travar.__name__ = f"travar_{chave}_na_correcao_pontual"
    return _travar


#: Trocas aplicadas por retrabalho nos loops: `[{chave, edicoes}]`, para o dossiê e a auditoria.
KEY_TROCAS_DE_RETRABALHO = "trocas_de_retrabalho"
#: Rodadas de retrabalho que voltaram ao autor (estrutural, ou trocas que não se aplicaram): `[{chave, motivo}]`.
KEY_RETRABALHO_AO_AUTOR = "retrabalho_ao_autor"
#: Troca o editor nos testes (mesma assinatura de `pipeline.reexecucao.propor_edicao`). None = o editor de verdade.
PROPONENTE_DE_RETRABALHO = None


def retrabalhar_por_trocas(chave: str):
    """before_agent_callback dos autores: na rodada de retrabalho de um loop, o documento é corrigido por trocas.

    Vale na geração e no refazer. Quando um gate reprovava, o autor reemitia o documento inteiro a partir da versão da
    rodada (`rodada_anterior_<chave>`), e o que já tinha passado podia mudar sem nenhum gate conferir de novo — a mesma
    deriva que fazia a correção de um número reescrever a spec. Aqui o editor (`tools/edicao_pontual.py`) recebe os
    relatórios dos gates reprovados (`retrabalho_<chave>`, gravado por `agents.checkers.SaidaDeLoopAgent`) e devolve
    trocas; o código as aplica e o autor não roda. Se o editor diz que é estrutural, ou as trocas não se aplicam, o
    autor reescreve como antes. Desligado por `RETRABALHO_POR_TROCAS=false`.
    """

    async def _retrabalhar(callback_context: CallbackContext) -> Optional[types.Content]:
        from config import get_settings

        state = callback_context.state
        motivos = str(state.get(f"retrabalho_{chave}") or "").strip()
        documento = str(state.get(chave) or "")
        if not motivos or not documento.strip() or not get_settings().retrabalho_por_trocas:
            return None
        if chave == "one_pager":
            from tools.one_pager_grande import por_trocas

            if por_trocas(state):
                # com o one-pager do PO grande, quem escreve o one-pager já trabalha por trocas e leva estes motivos
                # (`montar_one_pager_por_trocas`): um editor por rodada, e sem volta ao autor que reescreveria tudo
                return None
        from pipeline.reexecucao import editar, validador_do_po
        from tools import governanca
        from tools.edicao_pontual import como_dicts

        if chave in governanca.SECAO_DE_PENDENCIAS:
            # as pendências de governança são da esteira: o editor não as vê, e elas voltam abaixo como estão agora
            documento = governanca.sem_bloco(documento)
        # o voto do comitê pode mudar o texto do PO, mas só com a proposta ao lado ou o voto citado na tabela de
        # alterações: a troca que o apaga volta ao editor (`tools.one_pager_po.perdidos_pela_edicao`)
        resultado, proposta = await editar(motivos, "retrabalho", {chave: documento},
                                           proponente=PROPONENTE_DE_RETRABALHO,
                                           validador=validador_do_po(state.to_dict() if hasattr(state, "to_dict") else dict(state))
                                           if chave == "one_pager" else None)
        # consumido: o próximo autor da mesma chave nesta rodada (o revisor) não refaz a correção
        state[f"retrabalho_{chave}"] = ""
        if resultado is None or not resultado.aplicadas:
            motivo = getattr(proposta, "motivo", "") or "o editor não devolveu troca"
            logger.info("Retrabalho de %s volta ao autor: %s", chave, motivo)
            # à vista no estado: quantas rodadas o editor resolveu e quantas voltaram ao autor, e por quê
            state[KEY_RETRABALHO_AO_AUTOR] = list(state.get(KEY_RETRABALHO_AO_AUTOR) or []) + [
                {"chave": chave, "motivo": motivo[:400]}]
            return None
        state[KEY_TROCAS_DE_RETRABALHO] = list(state.get(KEY_TROCAS_DE_RETRABALHO) or []) + [
            {"chave": chave, "edicoes": como_dicts(resultado.aplicadas), "pendencias": list(proposta.pendencias)}]
        corrigido = documento_com_governanca(state, chave, resultado.documentos[chave])
        return types.Content(role="model", parts=[types.Part(text=corrigido)])

    _retrabalhar.__name__ = f"retrabalhar_{chave}_por_trocas"
    return _retrabalhar


#: Troca o editor do one-pager montado por trocas nos testes (mesma assinatura de `pipeline.reexecucao.propor_edicao`).
PROPONENTE_DO_ONE_PAGER_GRANDE = None


def montar_one_pager_por_trocas(papel: str):
    """before_agent_callback de quem escreve o `one_pager` (A014, A028, A034, A037): com o one-pager do PO grande demais
    para ser reescrito, o documento é montado por código e o modelo devolve só as trocas (`tools/one_pager_grande.py`).

    Na 3ef2b (e2e de 25/10/2026) o one-pager do PO tinha 360 mil caracteres; o A014 o reescrevia inteiro e era cortado
    perto de 218 mil, o A037 também, e o comitê dos canais rodava cinco vezes até o 400. Aqui: a base é montada por
    código (o one-pager do PO ou o da rodada, com o núcleo copiado); o editor recebe a tarefa do papel e os relatórios e
    devolve trocas; as que se aplicam e respeitam o one-pager do PO entram, as outras viram `[ABERTO — dono: PO: …]` no
    fim da seção 18. O `Content` devolvido vai para o `output_key`, e o autor não roda. Com o one-pager do PO que cabe,
    não faz nada — o autor escreve como sempre.
    """

    async def _montar(callback_context: CallbackContext) -> Optional[types.Content]:
        from tools import one_pager_grande as og

        state = callback_context.state
        if not og.por_trocas(state):
            return None
        from pipeline.reexecucao import propor_edicao, validador_do_po
        from tools.edicao_pontual import aplicar_parcial, como_dicts

        estado = state.to_dict() if hasattr(state, "to_dict") else dict(state)
        base = og.base_do_papel(estado, papel)
        motivos = str(state.get("retrabalho_one_pager") or "")
        proponente = PROPONENTE_DO_ONE_PAGER_GRANDE or propor_edicao
        proposta = await proponente(og.pedido(estado, papel, base, motivos), "produto", {"one_pager": base},
                                    erros="", achados="")
        # consumido: o retrabalho desta rodada foi ao editor junto com a tarefa do papel
        state["retrabalho_one_pager"] = ""
        edicoes = list(proposta.edicoes) if proposta.pontual else []
        resultado = aplicar_parcial({"one_pager": base}, edicoes, validador_do_po(estado, antes=base))
        nao_aplicadas = []
        for falha in resultado.falhas:
            m = re.match(r"edição (\d+)", falha)
            e = edicoes[int(m.group(1)) - 1] if m and 0 < int(m.group(1)) <= len(edicoes) else None
            if e is not None:
                nao_aplicadas.append({"papel": papel, "motivo": e.motivo, "de": e.de[:400], "para": e.para[:400],
                                      "falha": falha[:400]})
        if not proposta.pontual:
            # o editor não devolveu trocas: o documento fica como a base (o PO preservado), e o motivo fica à vista
            nao_aplicadas.append({"papel": papel, "motivo": "", "de": "", "para": "",
                                  "falha": (proposta.motivo or "o editor não devolveu trocas")[:400]})
            logger.warning("One-pager por trocas (%s): o editor não devolveu trocas — %s", papel, proposta.motivo)
        documento = og.com_pendencias(resultado.documentos["one_pager"], [
            og.linha_de_pendencia(papel, n["motivo"], n["de"], n["para"], n["falha"]) for n in nao_aplicadas if n["de"]]
            + [og.linha_do_editor(papel, p) for p in proposta.pendencias])
        if nao_aplicadas:
            state[og.KEY_TROCAS_NAO_APLICADAS] = list(state.get(og.KEY_TROCAS_NAO_APLICADAS) or []) + nao_aplicadas
        state[KEY_TROCAS_DE_RETRABALHO] = list(state.get(KEY_TROCAS_DE_RETRABALHO) or []) + [
            {"chave": "one_pager", "papel": papel, "edicoes": como_dicts(resultado.aplicadas),
             "pendencias": list(proposta.pendencias)}]
        cortes = state.get(KEY_CORTES_DO_MODELO) or {}
        if isinstance(cortes, dict) and any(isinstance(c, dict) and c.get("chave") == "one_pager" for c in cortes.values()):
            # o one-pager agora é montado inteiro por código: o corte de uma tentativa anterior não vale mais
            state[KEY_CORTES_DO_MODELO] = {k: c for k, c in cortes.items()
                                           if not (isinstance(c, dict) and c.get("chave") == "one_pager")}
        if not str(state.get("one_pager_gate0") or "").strip():
            state["one_pager_gate0"] = documento  # o que o `preservar_one_pager` do A014 faria, que não roda aqui
        logger.info("One-pager por trocas (%s): %d troca(s) aplicada(s), %d não aplicada(s)", papel,
                    len(resultado.aplicadas), len(nao_aplicadas))
        return types.Content(role="model", parts=[types.Part(text=documento)])

    _montar.__name__ = f"montar_one_pager_por_trocas_{papel}"
    return _montar


#: Marca, no estado, se o passo de completude chamou o modelo na volta corrente do `CompletudeLoop` (ou manteve a resposta).
KEY_COMPLETUDE_CHAMOU = "completude_chamou_o_modelo"
#: O que o passo de completude grava quando não roda na correção pontual de uma sessão que não o tinha
#: (`pipeline.artifacts.e_mensagem_de_pulo` o reconhece e não grava artefato).
COMPLETUDE_PULADA_NA_CORRECAO = (
    "⏭️ A045bCompletudeSpec não executado — correção pontual: a spec foi editada trecho a trecho e o passo de completude "
    "não acrescenta nada além das trocas pedidas. O bloco 15 nasce no próximo refazer de produto.")


def manter_completude_entre_rodadas(callback_context: CallbackContext) -> Optional[types.Content]:
    """before_agent_callback do passo de completude da spec (A045b, PR 6): roda uma vez por execução do SpecLoop.

    Roda na primeira rodada; de novo no loop dela (`CompletudeLoop`) quando o código a reprovou; e de novo quando o A045
    reescreveu a spec inteira e o bloco 15 sumiu. Nas outras rodadas do SpecLoop, a spec que volta ao A045 por um gate
    reprovado é corrigida por trocas (`retrabalhar_por_trocas`) e continua com o bloco 15: rodar a completude de novo seria
    uma chamada grande a mais por rodada, e o teto aprovado é uma a mais por refazer de produto (plano, D14). O `Content`
    devolvido é a resposta anterior com o bloco 15 trocado pelo que está na spec agora — o split monta o mesmo bloco, e a
    troca que o retrabalho fez nele fica.

    O `CompletudeLoop` roda isolado dentro do SpecLoop (`agents.checkers.LoopIsolado`), que zera `completude_rodada` a
    cada volta: `completude_rodada` 0 é a primeira passada da volta, e 1 é o refazer dela, que só existe quando o código a
    reprovou. O refazer chama o modelo só se a primeira passada da volta o chamou (`KEY_COMPLETUDE_CHAMOU`): a resposta
    mantida que segue reprovada já teve o refazer dela, e chamar de novo a cada rodada da spec passaria do teto (revisão
    do PR #73, 24/10/2026). Pelo mesmo teto, a resposta que veio sem o bloco 15 não é pedida de novo nas voltas seguintes:
    só o A045 que reescreveu a spec, com a resposta anterior trazendo o bloco, faz a completude rodar de novo.

    Na correção pontual não roda nunca, nem na sessão anterior ao PR 6, que não tem `completude_spec` para travar: o
    editor trocou a spec, e o bloco 15 novo sobre ela seria conteúdo além das trocas pedidas (exp02ef1b e exp02em1b, que o
    plano reconduz por produto pontual, D11/D12)."""
    state = callback_context.state
    if state.get(KEY_MODO_CORRECAO) == "pontual":
        anterior = str(state.get("completude_spec") or "")
        return types.Content(role="model", parts=[types.Part(text=anterior if anterior.strip()
                                                              else COMPLETUDE_PULADA_NA_CORRECAO)])
    refazer_da_volta = int(state.get("completude_rodada") or 0) >= 1
    if refazer_da_volta and str(state.get("completude_status") or "") == "bloqueado" and state.get(KEY_COMPLETUDE_CHAMOU):
        return None  # a segunda rodada do loop da completude: ela corrige o que o código acusou
    if not refazer_da_volta and not int(state.get("spec_rodada") or 0):
        state[KEY_COMPLETUDE_CHAMOU] = True
        return None
    anterior = str(state.get("completude_spec") or "")
    spec = str(state.get("spec_missao") or "")
    titulo = re.compile(r"^##\s*\**\s*15\b.*$", re.MULTILINE)

    def bloco(texto: str) -> str:
        m = titulo.search(texto or "")
        if not m:
            return ""
        fim = re.search(r"^## ", texto[m.end():], re.MULTILINE)
        return texto[m.start(): m.end() + fim.start() if fim else len(texto)]

    atual, velho = bloco(spec), bloco(anterior)
    mantida = anterior.replace(velho, atual.rstrip() + "\n\n", 1) if atual.strip() and velho.strip() else anterior
    if refazer_da_volta and not state.get(KEY_COMPLETUDE_CHAMOU):
        # a primeira passada da volta manteve a resposta sem chamar o modelo: o refazer também não chama
        return types.Content(role="model", parts=[types.Part(text=mantida)])
    if not velho.strip():
        # a resposta da completude veio sem o bloco 15, e o modelo já respondeu nesta execução (a volta 0 sempre o chama,
        # e a resposta mantida traz o bloco): chamar de novo a cada volta somaria 2 chamadas por rodada da spec só no
        # caminho de falha. O split segue reprovando, e o 🔴 fica à vista (revisão do PR #73, 24/10/2026)
        state[KEY_COMPLETUDE_CHAMOU] = False
        return types.Content(role="model", parts=[types.Part(text=anterior)])
    if not atual.strip():
        state[KEY_COMPLETUDE_CHAMOU] = True
        return None
    if not refazer_da_volta:
        state[KEY_COMPLETUDE_CHAMOU] = False
    return types.Content(role="model", parts=[types.Part(text=mantida)])


def dispensar_ideacao_com_one_pager_do_po(callback_context: CallbackContext) -> Optional[types.Content]:
    """before_agent_callback da ideação: com o one-pager do PO no estado, não se inventam três mecanismos.

    Na exp06ef1b (08/10/2026) o PO anexou o one-pager aprovado e pediu três correções; a ideação desenhou três
    mecanismos novos e o núcleo, instruído a "desenvolver o candidato escolhido", partiu deles. O `Content`
    devolvido vai para o `output_key` e o agente não roda.
    """
    if not str(callback_context.state.get("one_pager_po") or "").strip():
        return None
    return types.Content(role="model", parts=[types.Part(text=IDEACAO_DISPENSADA)])


def desembrulhar_documento(chave: str):
    """after_agent_callback: tira a cerca ```markdown que envolve o documento inteiro, logo que ele é gravado.

    Na exp09ef1b o redator embrulhou o PRD: a conferência PRD × aprovado (A116) não achava a §14 dentro da cerca e
    acusava habilidade sem KPI que estava lá, deixava passar o tempo de etapa divergente, e o anexo literal entrava
    depois da cerca — aí a gravação não reconhecia mais o invólucro e o `PRD.md` abria como bloco de código.
    """
    def _callback(callback_context: CallbackContext) -> None:
        from pipeline.artifacts import desembrulhar_cerca

        texto = callback_context.state.get(chave)
        if isinstance(texto, str) and texto:
            limpo = desembrulhar_cerca(texto)
            if limpo != texto:
                callback_context.state[chave] = limpo
        return None

    _callback.__name__ = f"desembrulhar_{chave}"
    return _callback


def tirar_envelope_do_documento(chave: str):
    """after_agent_callback: tira do documento que gente lê o envelope JSON que o autor pôs no fim, logo que ele é gravado
    (`pipeline.artifacts.sem_envelope_do_agente`). O resumido das 15 sessões do acervo de 24/10/2026 terminava no JSON, e
    o envelope dele não é lido por ninguém: nenhum gate o confere, e o `.md` é o que o time de produto lê."""
    def _callback(callback_context: CallbackContext) -> None:
        from pipeline.artifacts import sem_envelope_do_agente

        texto = callback_context.state.get(chave)
        if isinstance(texto, str) and texto:
            limpo = sem_envelope_do_agente(texto)
            if limpo != texto:
                callback_context.state[chave] = limpo
        return None

    _callback.__name__ = f"tirar_envelope_{chave}"
    return _callback


def copiar_textos_chave(chave: str):
    """after_agent_callback: os textos-chave do one-pager copiados por código para o documento que o autor acabou de
    gravar (PR 7 do plano «Produto dono do contrato», D1).

    Na copy (passada 1), a linha que traz o texto-chave recebe o texto aprovado, e a redação do autor vira proposta ao
    PO na seção da esteira (`tools.textos_chave.aplicar_na_copy`); a revisão da copy e o gate vêm depois, no
    `TextosChaveCopyAgent`. No handoff, no PRD e no pedagógico, a citação entre aspas que é reescrita quase igual de um
    texto-chave passa a ser o texto aprovado (`aplicar_em_documento`) — a reescrita mais distante fica com os gates
    (montagem, A116, A121). O LLM não reescreve o texto-chave: o código o copia.
    """
    def _callback(callback_context: CallbackContext) -> None:
        from pipeline.artifacts import e_mensagem_de_pulo
        from tools import textos_chave as tk

        state = callback_context.state
        texto = state.get(chave)
        if not isinstance(texto, str) or not texto.strip() or e_mensagem_de_pulo(texto):
            return None
        tcs = tk.da_sessao(state)
        if not tcs:
            return None
        if chave in ("copy_strings", "copy_strings_revisada"):
            # na correção pontual o autor não roda (e este callback também não); se rodar, não anota linha sem troca
            novo = tk.aplicar_na_copy(texto, tcs, anotar_sem_troca=state.get(KEY_MODO_CORRECAO) != "pontual")["texto"]
        else:
            # as propostas do design para os textos-chave, as que o A078b registrou na copy e as que ele registraria
            # (sessão anterior ao PR 7 refeita só no dev): a citação que é uma delas volta ao aprovado sem a régua
            copia = str(state.get("copy_strings_revisada") or state.get("copy_strings") or "")
            propostas = tk.aplicar_na_copy(copia, tcs)["propostas"] if copia.strip() else []
            novo, _ = tk.aplicar_em_documento(texto, tcs, propostas)
        if novo != texto:
            state[chave] = novo
        return None

    _callback.__name__ = f"copiar_textos_chave_{chave}"
    return _callback


def documento_com_governanca(state: Any, chave: str, texto: str) -> str:
    """O handoff ou o PRD com as pendências de governança da liberação de produto como estão agora
    (`tools.governanca.com_pendencias`, lidas de `governanca_produto`). Outro documento volta como veio.

    É o mesmo bloco em todo caminho que escreve o documento: o redator (`registrar_governanca`), o documento travado na
    correção pontual (`travar_documento_na_correcao_pontual`) e o retrabalho por trocas (`retrabalhar_por_trocas`) — nos
    dois últimos o agente não roda, e o after_agent_callback dele também não."""
    from tools import governanca

    if chave not in governanca.SECAO_DE_PENDENCIAS:
        return texto
    return governanca.com_pendencias(texto, governanca.da_sessao(state), chave)


def registrar_governanca(chave: str):
    """after_agent_callback do handoff e do PRD: as pendências de governança da liberação de produto entram por código
    na seção de pendências (§7 do handoff, §19 do PRD) — PR 9 do plano «Produto dono do contrato», D9.

    Lidas de `governanca_produto`, que a execução grava a partir dos pareceres: «liberado sem a conta produto» (as
    liberações em vigor da exp02em1b e da exp02ef1b, de 22 e 23/10/2026, são da conta design) e a exceção do admin com
    🔴 em produto. O redator não as escreve nem as tira: o bloco de uma rodada anterior é trocado, e sem pendência ele
    sai. Logo depois do autor, para os gates do loop lerem o mesmo texto que vai para quem codifica."""
    def _callback(callback_context: CallbackContext) -> None:
        from pipeline.artifacts import e_mensagem_de_pulo

        state = callback_context.state
        texto = state.get(chave)
        if not isinstance(texto, str) or not texto.strip() or e_mensagem_de_pulo(texto):
            return None
        novo = documento_com_governanca(state, chave, texto)
        if novo != texto:
            state[chave] = novo
        return None

    _callback.__name__ = f"registrar_governanca_{chave}"
    return _callback


#: Prefixo da chave em que fica o aviso de resposta cortada pelo modelo, por agente (`bloqueio_modelo_<nome>`).
PREFIXO_BLOQUEIO_MODELO = "bloqueio_modelo_"
_AVISOS_DE_CORTE = {
    "RECITATION": (
        "o filtro de recitação do modelo cortou a resposta inteira — ela reproduzia literalmente um texto publicado. "
        "Nesta tentativa, **não transcreva por extenso** texto de fonte publicada (texto oficial da BNCC, apostila, lei, "
        "notícia, letra de música): cite o código ou a fonte e resuma em uma linha com suas palavras. O conteúdo da "
        "missão (narrativa, telas, falas, decisões) segue como as regras mandam."),
    "MAX_TOKENS": (
        "a resposta passou do limite de tamanho e foi cortada antes de terminar. Nesta tentativa, seja mais enxuto no "
        "raciocínio e não repita trechos já escritos; o documento precisa sair inteiro."),
}


#: Respostas cortadas pelo limite de saída do modelo **com texto**, por agente: `{agente: {chave, caracteres, motivo,
#: vezes}}`. Sai do registro quando o mesmo agente termina inteiro. Lido pela saída dos loops (`SaidaDeLoopAgent`) e pelo
#: diagnóstico (`tools/diagnostico.py`).
KEY_CORTES_DO_MODELO = "cortes_do_modelo"


def _chave_de_saida(callback_context: Any) -> str:
    agente = getattr(getattr(callback_context, "_invocation_context", None), "agent", None)
    return str(getattr(agente, "output_key", "") or "")


def registrar_corte_do_modelo(callback_context: CallbackContext, llm_response: Any) -> None:
    """after_model_callback de todo agente: resposta cortada pelo modelo fica registrada — com ou sem texto.

    Na exp03ef1b (08/10/2026) o A014 terminou com `FinishReason.RECITATION` e nenhum texto, duas vezes: o filtro de
    recitação do Gemini corta a saída que reproduz texto publicado — e o one-pager transcreve o texto oficial da
    BNCC. A esteira não registrava o motivo, o loop chamava o agente de novo com a mesma instrução e o resultado era
    o mesmo. Aqui o motivo vai ao estado e a próxima instrução do mesmo agente o recebe (`agents.base`).

    O corte por `MAX_TOKENS` **com texto** também. Na 3ef2b (e2e de 25/10/2026) o A014 devolvia o one-pager do PO de 360
    mil caracteres cortado sempre perto de 218 mil (≈65 mil tokens, o limite de saída), e a resposta parcial era gravada
    como one-pager sem aviso nenhum: o loop reenviava a mesma instrução cinco vezes. Agora o corte vai a
    `cortes_do_modelo`, que a saída do loop trata como reprovação e o diagnóstico mostra ao PO (`documento-cortado-pelo-modelo`).
    """
    conteudo = getattr(llm_response, "content", None)
    partes = list(getattr(conteudo, "parts", None) or [])
    texto = "".join(p.text or "" for p in partes if getattr(p, "text", None) and not getattr(p, "thought", False))
    agente = callback_context.agent_name
    chave = f"{PREFIXO_BLOQUEIO_MODELO}{agente}"
    if getattr(llm_response, "partial", False):
        return None
    motivo = str(getattr(llm_response, "finish_reason", "") or getattr(llm_response, "error_code", "") or "")
    motivo = motivo.split(".")[-1].upper()
    state = callback_context.state
    cortes = state.get(KEY_CORTES_DO_MODELO) or {}
    if texto.strip() and motivo == "MAX_TOKENS":
        anterior = cortes.get(agente) if isinstance(cortes, dict) else None
        vezes = int((anterior or {}).get("vezes", 0) or 0) + 1
        state[KEY_CORTES_DO_MODELO] = {**(cortes if isinstance(cortes, dict) else {}), agente: {
            "agente": agente, "chave": _chave_de_saida(callback_context), "caracteres": len(texto),
            "motivo": motivo, "vezes": vezes}}
        state[chave] = ("## Sua tentativa anterior foi cortada pelo modelo\n\nNa tentativa anterior, a resposta passou do "
                        f"limite de tamanho do modelo e foi cortada em {len(texto)} caracteres, antes de terminar. Nesta "
                        "tentativa, seja mais enxuto no raciocínio e não repita trechos já escritos; o documento precisa "
                        "sair inteiro.")
        logging.getLogger(__name__).warning("Resposta de %s cortada pelo limite de saída do modelo em %d caracteres",
                                            agente, len(texto))
        return None
    if texto.strip() or getattr(llm_response, "turn_complete", None) is False:
        if state.get(chave):
            state[chave] = ""
        if texto.strip() and isinstance(cortes, dict) and agente in cortes:
            # terminou inteiro desta vez: o documento cortado foi substituído
            state[KEY_CORTES_DO_MODELO] = {k: v for k, v in cortes.items() if k != agente}
        return None
    if motivo and motivo not in ("STOP", "FINISH_REASON_UNSPECIFIED"):
        aviso = _AVISOS_DE_CORTE.get(motivo, f"o modelo devolveu a resposta vazia (motivo `{motivo}`). Escreva o documento inteiro.")
        state[chave] = f"## Sua tentativa anterior foi cortada pelo modelo\n\nNa tentativa anterior, {aviso}"
        logging.getLogger(__name__).warning("Resposta de %s cortada pelo modelo: %s", agente, motivo)
    return None


def cortes_dos_documentos(state: Any, chaves: Any) -> list:
    """Os cortes registrados (`KEY_CORTES_DO_MODELO`) cujo documento é uma das `chaves`."""
    cortes = state.get(KEY_CORTES_DO_MODELO) or {}
    if not isinstance(cortes, dict):
        return []
    return [c for c in cortes.values() if isinstance(c, dict) and c.get("chave") in set(chaves or ())]


# --------------------------------------------------------------------- contexto de cada chamada ao modelo
#: O que fica na mensagem do PO, para o A004, no lugar do one-pager dele — que já está inteiro na instrução.
PONTEIRO_PO_NA_MENSAGEM = ("(o texto integral deste anexo — o one-pager do PO — está na sua instrução, na seção «One-pager "
                           "do PO»; não é repetido aqui)")


def so_a_mensagem_do_po(callback_context: CallbackContext, llm_request: Any) -> None:
    """before_model_callback do A004: o histórico da conversa vira só a mensagem original do PO, com os anexos.

    O A004 é o único agente da esteira que vê a mensagem do PO (`include_contents="default"`), e o ADK manda junto
    **todo** o histórico da sessão: cada saída do A014, os núcleos anteriores, os juízes, rodada após rodada. Na 3ef2b
    (e2e de 25/10/2026) a 5ª volta do comitê dos canais passou de 1.048.576 tokens e a missão caiu com 400. O que o A004
    precisa de rodadas anteriores chega pelo estado, na instrução (`{nucleo_narrativo?}`, os relatórios dos comitês e dos
    gates). O one-pager do PO também ia duas vezes — no anexo da mensagem e na instrução (`one-pager-do-po.md`): na
    mensagem, ele vira um ponteiro.
    """
    original = getattr(callback_context, "user_content", None)
    po = str(callback_context.state.get("one_pager_po") or "")
    partes = []
    for parte in getattr(original, "parts", None) or []:
        texto = getattr(parte, "text", None)
        if texto and po.strip() and po in texto:
            parte = types.Part(text=texto.replace(po, PONTEIRO_PO_NA_MENSAGEM, 1))
        partes.append(parte)
    if not partes:
        partes = [types.Part(text="Siga a instrução do sistema.")]
    llm_request.contents = [types.Content(role="user", parts=partes)]
    return None


def orcamento_de_contexto(deterministico: bool):
    """before_model_callback de todo agente: cabe no modelo? (`tools/contexto.py`).

    Na ordem: o one-pager do PO grande vai para o começo da instrução (o prefixo comum é o que o cache implícito do
    Gemini reaproveita); o juiz (`deterministico`) perde o que é repetido e, acima do orçamento, o que é longo e não é
    contrato, com o corte registrado em `contexto_cortado_<agente>`; e a requisição que ainda passa do teto não sai —
    `ContextoGrandeDemais`, com o agente, o tamanho e as maiores chaves do estado, no lugar do 400 do modelo depois de
    uma hora e meia (3ef2b, 25/10/2026).
    """

    def _callback(callback_context: CallbackContext, llm_request: Any) -> None:
        from tools import contexto

        state = callback_context.state
        agente = callback_context.agent_name
        estado = state.to_dict() if hasattr(state, "to_dict") else dict(state)
        config = getattr(llm_request, "config", None)
        instrucao = contexto.instrucao_da_requisicao(llm_request)
        if config is not None and isinstance(getattr(config, "system_instruction", None), str) and instrucao:
            nova = instrucao
            if deterministico and agente not in contexto.SEM_ORCAMENTO:
                # o corte antes: o one-pager do PO que sai do juiz não vai para o começo da instrução
                nova, cortes = contexto.cortar_para_o_orcamento(nova, estado)
                chave = f"contexto_cortado_{agente}"
                if cortes:
                    state[chave] = cortes
                    logger.info("%s: contexto cortado para caber no orçamento — %s", agente, "; ".join(cortes))
                elif state.get(chave):
                    state[chave] = []  # a chamada desta rodada coube inteira
            nova = contexto.po_primeiro(nova, estado)
            if nova != instrucao:
                config.system_instruction = nova
        tokens_instrucao, tokens_historico = contexto.tokens_da_requisicao(llm_request)
        total = tokens_instrucao + tokens_historico
        if total > contexto.TETO_PREVOO:
            raise contexto.ContextoGrandeDemais(agente, total, tokens_historico, contexto.maiores_chaves(estado))
        return None

    _callback.__name__ = "orcamento_de_contexto_juiz" if deterministico else "orcamento_de_contexto"
    return _callback
