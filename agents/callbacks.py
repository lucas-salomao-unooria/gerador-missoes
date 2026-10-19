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
    if not reprovados or str(state.get("evidencia_one_pager_status") or "") == "bloqueado":
        return None
    if any(str(a.get("autor") or "") in ("A004", "") for e in reprovados for a in e.get("achados") or []
           if isinstance(a, dict) and citacoes.bloqueante(a)):
        return None
    return types.Content(role="model", parts=[types.Part(
        text="⏭️ Núcleo mantido: os comitês não apontaram nada para o A004 nesta rodada; só as seções de apoio corrigem.")])


#: Modo da correção corrente (`pipeline/reexecucao.py`): `pontual` trava os autores; ausente na geração e no refazer.
KEY_MODO_CORRECAO = "modo_correcao"
#: Documentos cujo autor não roda na correção pontual: o texto deles é o que o editor deixou (`tools/edicao_pontual.py`).
KEY_DOCUMENTOS_TRAVADOS = "documentos_travados"


def travar_documento_na_correcao_pontual(chave: str):
    """before_agent_callback dos autores: na correção pontual, o documento já editado não é reescrito.

    O `Content` devolvido é o próprio documento — vai para o `output_key` sem mudar uma letra, e o agente não roda.
    Até 19/10/2026 a correção reexecutava cada autor sobre `anterior_<chave>`, e a troca de um número devolvia a spec
    com metade das linhas diferentes (exp03em1b, 13/10/2026). Fora da correção pontual, não faz nada.
    """

    def _travar(callback_context: CallbackContext) -> Optional[types.Content]:
        state = callback_context.state
        if state.get(KEY_MODO_CORRECAO) != "pontual" or chave not in (state.get(KEY_DOCUMENTOS_TRAVADOS) or []):
            return None
        documento = str(state.get(chave) or "")
        if not documento.strip():
            return None
        return types.Content(role="model", parts=[types.Part(text=documento)])

    _travar.__name__ = f"travar_{chave}_na_correcao_pontual"
    return _travar


#: Trocas aplicadas por retrabalho nos loops: `[{chave, edicoes}]`, para o dossiê e a auditoria.
KEY_TROCAS_DE_RETRABALHO = "trocas_de_retrabalho"
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
        from pipeline.reexecucao import editar
        from tools.edicao_pontual import como_dicts

        resultado, proposta = await editar(motivos, "retrabalho", {chave: documento},
                                           proponente=PROPONENTE_DE_RETRABALHO)
        # consumido: o próximo autor da mesma chave nesta rodada (o revisor) não refaz a correção
        state[f"retrabalho_{chave}"] = ""
        if resultado is None or not resultado.aplicadas:
            logger.info("Retrabalho de %s volta ao autor: %s", chave, getattr(proposta, "motivo", ""))
            return None
        state[KEY_TROCAS_DE_RETRABALHO] = list(state.get(KEY_TROCAS_DE_RETRABALHO) or []) + [
            {"chave": chave, "edicoes": como_dicts(resultado.aplicadas), "pendencias": list(proposta.pendencias)}]
        return types.Content(role="model", parts=[types.Part(text=resultado.documentos[chave])])

    _retrabalhar.__name__ = f"retrabalhar_{chave}_por_trocas"
    return _retrabalhar


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


def registrar_corte_do_modelo(callback_context: CallbackContext, llm_response: Any) -> None:
    """after_model_callback de todo agente: resposta sem texto cortada pelo modelo fica registrada para a tentativa seguinte.

    Na exp03ef1b (08/10/2026) o A014 terminou com `FinishReason.RECITATION` e nenhum texto, duas vezes: o filtro de
    recitação do Gemini corta a saída que reproduz texto publicado — e o one-pager transcreve o texto oficial da
    BNCC. A esteira não registrava o motivo, o loop chamava o agente de novo com a mesma instrução e o resultado era
    o mesmo. Aqui o motivo vai ao estado e a próxima instrução do mesmo agente o recebe (`agents.base`).
    """
    conteudo = getattr(llm_response, "content", None)
    partes = list(getattr(conteudo, "parts", None) or [])
    texto = "".join(p.text or "" for p in partes if getattr(p, "text", None) and not getattr(p, "thought", False))
    chave = f"{PREFIXO_BLOQUEIO_MODELO}{callback_context.agent_name}"
    if getattr(llm_response, "partial", False):
        return None
    motivo = str(getattr(llm_response, "finish_reason", "") or getattr(llm_response, "error_code", "") or "")
    motivo = motivo.split(".")[-1].upper()
    if texto.strip() or getattr(llm_response, "turn_complete", None) is False:
        if callback_context.state.get(chave):
            callback_context.state[chave] = ""
        return None
    if motivo and motivo not in ("STOP", "FINISH_REASON_UNSPECIFIED"):
        aviso = _AVISOS_DE_CORTE.get(motivo, f"o modelo devolveu a resposta vazia (motivo `{motivo}`). Escreva o documento inteiro.")
        callback_context.state[chave] = f"## Sua tentativa anterior foi cortada pelo modelo\n\nNa tentativa anterior, {aviso}"
        logging.getLogger(__name__).warning("Resposta de %s cortada pelo modelo: %s", callback_context.agent_name, motivo)
    return None
