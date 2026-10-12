"""Conversa com as etapas de uma missão: perguntas sobre produto, design ou dev, sem alterar nada.

Com o parecer humano, o campo de mensagem deixou de pedir correção (ela rodaria etapas sem dono e
sem parecer) e ficou travado: não havia como perguntar "por que o gate BNCC ficou vermelho?" sem
refazer a etapa. Esta conversa responde com os documentos da etapa como contexto e **não muda a
missão**. Para mudar, o caminho continua sendo o Refazer do cartão de passagem, e o rascunho do
comentário dele pode sair daqui.

A conversa fica em `.conversa-etapas.json`, na pasta da missão (decisão de 24/09/2026):
- no histórico da missão, e todo mundo que abre a missão vê e pode perguntar;
- fora dos artefatos: o ponto no nome a tira dos downloads, do manifesto e da assinatura da pasta,
  como `.correcoes/`;
- fora do `conversa.json`, que o runner regrava do zero ao fim de cada etapa preservando só o
  `fluxo`: uma pergunta feita com a etapa rodando se perderia ali.

Sem Streamlit. O app desenha; aqui moram o arquivo, o recorte do contexto e a chamada ao modelo.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pipeline import passagem

logger = logging.getLogger(__name__)

ARQUIVO = ".conversa-etapas.json"

#: A conversa única (12/10/2026): uma pergunta sobre a missão inteira, com os documentos das três etapas no
#: contexto. As perguntas antigas, gravadas com a etapa delas, continuam no histórico.
MISSAO = "missao"
ROTULO_MISSAO = "toda a missão"

#: Teto do contexto por pergunta, em caracteres (~90 mil tokens). O estado de uma missão com PRD
#: passa de 1,1 milhão de caracteres; só o design tem 590 mil.
ORCAMENTO_CONTEXTO = 350_000
#: Um documento que não coube inteiro entra cortado só se sobrar pelo menos isto; senão, fica de fora.
MINIMO_PARA_CORTAR = 20_000
#: Trocas anteriores da mesma etapa que o modelo vê, e o teto de cada mensagem nelas.
TROCAS_NO_HISTORICO = 6
TETO_MENSAGEM_NO_HISTORICO = 2_500
TETO_PERGUNTA = 4_000

#: A mensagem que pede o rascunho do comentário do parecer. O prompt a reconhece literalmente.
PEDIDO_RASCUNHO = "[rascunho do comentário do parecer]"

#: Documentos lidos primeiro, nesta ordem. O resto da etapa entra depois, relatórios antes.
PRIORIDADE: Dict[str, Tuple[str, ...]] = {
    "produto": ("one_pager", "spec_missao", "nucleo_narrativo", "one_pager_resumido", "gate_final_report"),
    "design": ("jornada_telas", "fluxo_arestas", "copy_strings_revisada", "wireframes_cobertura", "camada_caa",
               "brief_oficio", "ambiente_simulado", "fechamento_lacunas", "qa_entregaveis_report"),
    "dev": ("prd_final", "handoff_dev", "brief_assets", "validacao_dev_report", "one_pager_pedagogico"),
}
# na conversa única, o principal de cada etapa antes de qualquer relatório
PRIORIDADE[MISSAO] = ("one_pager", "spec_missao", "jornada_telas", "fluxo_arestas", "copy_strings_revisada",
                      "prd_final", "one_pager_resumido", "handoff_dev", "brief_assets", "one_pager_pedagogico",
                      "gate_final_report", "qa_entregaveis_report", "validacao_dev_report", "nucleo_narrativo",
                      "wireframes_cobertura", "camada_caa", "brief_oficio", "ambiente_simulado", "fechamento_lacunas")
#: O que a etapa recebe da anterior e costuma entrar na pergunta ("o design seguiu a spec?").
A_MONTANTE: Dict[str, Tuple[str, ...]] = {"produto": (), "design": ("spec_missao",), "dev": ("spec_missao",), MISSAO: ()}
#: HTML do protótipo e dos diagramas: ~240 mil caracteres de marcação que não respondem nada que a
#: jornada, o fluxo e a copy não respondam.
FORA_DO_CONTEXTO = frozenset({"prototipo_html", "prototipo_arquivo", "diagramas_html"})
#: Veredito vai no semáforo; envelope repete o relatório; `_rodada` é contador; `_gate0` é a versão
#: anterior à revisão do gate.
SUFIXOS_FORA = ("_status", "_status_envelope", "_rodada", "_gate0")

ROTULO_ACAO = {
    passagem.DE_ACORDO: "de acordo", passagem.REFAZER: "refazer", passagem.INICIAR: "iniciar",
    passagem.DEVOLVER: "devolver", passagem.EXCECAO: "liberada com exceção",
}

_TRAVA = threading.Lock()


# ------------------------------------------------------------------ arquivo
def _agora() -> str:
    return time.strftime("%d/%m/%Y %H:%M:%S")


def ler(run_dir: Path) -> List[Dict[str, Any]]:
    """As mensagens da missão, em ordem. Arquivo ausente ou ilegível é conversa vazia."""
    caminho = Path(run_dir) / ARQUIVO
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as exc:
        logger.warning("Conversa das etapas ilegível em %s: %s", caminho, exc)
        return []
    return [m for m in (dados.get("mensagens") or []) if isinstance(m, dict)]


def registrar(run_dir: Path, *novas: Dict[str, Any]) -> None:
    """Acrescenta mensagens à conversa da missão.

    O app roda numa instância só, então a trava do processo basta para duas pessoas perguntando ao
    mesmo tempo não apagarem a pergunta uma da outra. Um arquivo ilegível é posto de lado com outro
    nome, em vez de sobrescrito: a conversa recomeça sem apagar o que havia.
    """
    caminho = Path(run_dir) / ARQUIVO
    with _TRAVA:
        mensagens: List[Dict[str, Any]] = []
        if caminho.exists():
            try:
                mensagens = [m for m in (json.loads(caminho.read_text(encoding="utf-8")).get("mensagens") or [])
                             if isinstance(m, dict)]
            except (OSError, ValueError) as exc:
                lado = caminho.with_name(f"{ARQUIVO}.ilegivel-{time.strftime('%Y%m%d-%H%M%S')}")
                logger.warning("Conversa das etapas ilegível em %s (%s); guardada em %s", caminho, exc, lado.name)
                caminho.rename(lado)
        mensagens.extend(novas)
        caminho.write_text(json.dumps({"mensagens": mensagens}, indent=2, ensure_ascii=False, default=str),
                           encoding="utf-8")


def rotulo(etapa: str) -> str:
    return ROTULO_MISSAO if etapa == MISSAO else passagem.ROTULO_ETAPA[etapa]


def _etapas(etapa: str) -> Tuple[str, ...]:
    return passagem.ORDEM if etapa == MISSAO else (etapa,)


def assinatura(estado: Dict[str, Any], etapa: str) -> str:
    """A da etapa; na conversa única, a das três juntas (qualquer etapa refeita muda a versão)."""
    return "-".join(passagem.assinatura_da_etapa(estado, e) for e in _etapas(etapa))


def pergunta(etapa: str, texto: str, usuario: str, papel: str) -> Dict[str, Any]:
    return {"id": uuid.uuid4().hex[:12], "etapa": etapa, "role": "user", "autor": usuario, "como": papel,
            "quando": _agora(), "texto": texto}


def resposta(etapa: str, texto: str, a_pergunta: Dict[str, Any], estado: Dict[str, Any]) -> Dict[str, Any]:
    """A resposta guarda a assinatura da etapa: se ela for refeita, a resposta passa a ser de outra versão."""
    return {"id": uuid.uuid4().hex[:12], "etapa": etapa, "role": "assistant", "responde_a": a_pergunta["id"],
            "quando": _agora(), "assinatura": assinatura(estado, etapa), "texto": texto}


def da_etapa(mensagens: Sequence[Dict[str, Any]], etapa: str) -> List[Dict[str, Any]]:
    return [m for m in mensagens if m.get("etapa") == etapa]


def de_outra_versao(mensagem: Dict[str, Any], assinatura_atual: str) -> bool:
    """Resposta dada sobre uma versão da etapa que já foi refeita."""
    return bool(mensagem.get("role") == "assistant" and mensagem.get("assinatura")
                and mensagem["assinatura"] != assinatura_atual)


# ------------------------------------------------------------------ contexto
@lru_cache(maxsize=1)
def _nomes_dos_documentos() -> Dict[str, str]:
    """`output_key` → nome do agente que o escreve, como aparece nas abas ("13 · Spec da missão")."""
    from pipeline.orchestrator import STAGES

    nomes: Dict[str, str] = {}
    for stage in STAGES:
        for agente in stage["agents"]:
            if agente.get("output_key"):
                nomes.setdefault(agente["output_key"], agente["name"])
    # quatro agentes escrevem o one-pager; o primeiro nome ("04 · Seções de apoio") engana
    nomes["one_pager"] = "One-pager"
    return nomes


def _tem_conteudo(estado: Dict[str, Any], chave: str) -> bool:
    from pipeline.artifacts import e_mensagem_de_pulo

    valor = estado.get(chave)
    return valor not in (None, "", [], {}) and not e_mensagem_de_pulo(valor)


def documentos_da_etapa(estado: Dict[str, Any], etapa: str) -> List[str]:
    """As chaves que a conversa lê para a etapa, na ordem de leitura."""
    proprias = frozenset().union(*(passagem.chaves_da_etapa(e) for e in _etapas(etapa)))

    def serve(chave: str) -> bool:
        if chave in FORA_DO_CONTEXTO or chave.endswith(SUFIXOS_FORA) or not _tem_conteudo(estado, chave):
            return False
        # a passada 2 da copy substitui a 1
        return not (chave == "copy_strings" and _tem_conteudo(estado, "copy_strings_revisada"))

    primeiro = [k for k in PRIORIDADE[etapa] if k in proprias]
    resto = sorted((k for k in proprias if k not in primeiro), key=lambda k: (not k.endswith("_report"), k))
    ordem = list(dict.fromkeys(primeiro + list(A_MONTANTE[etapa]) + resto))
    return [k for k in ordem if serve(k)]


def _como_texto(valor: Any) -> str:
    return valor if isinstance(valor, str) else json.dumps(valor, indent=1, ensure_ascii=False, default=str)


def _situacao(fluxo: Optional[Dict[str, Any]], etapa: str, execucao: Optional[Dict[str, Any]]) -> str:
    if not fluxo:
        return "missão sem parecer humano entre etapas"
    atual, situacao = fluxo["etapa"], fluxo.get("situacao")
    if etapa == MISSAO:
        if situacao == passagem.ENTREGUE:
            return "missão entregue: as três etapas foram liberadas"
        texto = f"a missão está em {passagem.ROTULO_ETAPA[atual]}: {passagem.quem_age(fluxo)}"
        if situacao in passagem.EM_EXECUCAO:
            agente = (execucao or {}).get("agente_atual")
            texto += (f" (agente atual: {agente})" if agente else "") + (
                ". Etapas seguintes ainda não têm documento; os abaixo são os gravados quando a pergunta foi feita.")
        return texto
    i, j = passagem.ORDEM.index(etapa), passagem.ORDEM.index(atual)
    if situacao == passagem.ENTREGUE or i < j:
        return "etapa já liberada: a missão passou dela"
    if i > j or situacao == passagem.LIBERADA:
        return "etapa ainda não começou: não há documento dela, só o das etapas anteriores"
    texto = passagem.quem_age(fluxo)
    if situacao in passagem.EM_EXECUCAO:
        agente = (execucao or {}).get("agente_atual")
        texto += (f" agora (agente atual: {agente})" if agente else " agora") + (
            ". Os documentos abaixo são os que estavam gravados quando a pergunta foi feita.")
    return texto


def _pareceres(fluxo: Optional[Dict[str, Any]]) -> str:
    linhas: List[str] = []
    for p in (fluxo or {}).get("pareceres") or []:
        substituido = "" if p.get("valido", True) else " · substituído por uma versão refeita"
        linhas.append(f"- **{passagem.ROTULO_ETAPA.get(p.get('etapa'), p.get('etapa'))} · "
                      f"{ROTULO_ACAO.get(p.get('acao'), p.get('acao'))}** · {p.get('como')} · {p.get('quando')}"
                      f" (rodada {p.get('rodada', 1)}){substituido}")
        linhas += [f"  > {l}" for l in str(p.get("comentario") or "").splitlines() if l.strip()]
        for chave, texto in (p.get("conferencia") or {}).items():
            linhas.append(f"  > Conferência ({chave}): {texto}")
    return "\n".join(linhas)


def montar_contexto(estado: Dict[str, Any], fluxo: Optional[Dict[str, Any]], etapa: str,
                    execucao: Optional[Dict[str, Any]] = None, orcamento: int = ORCAMENTO_CONTEXTO) -> str:
    """O que o modelo lê para responder sobre a etapa, dentro do orçamento de caracteres."""
    from pipeline.reexecucao import montar_mapa_da_missao

    partes = [f"### Missão\n\n{montar_mapa_da_missao(estado)}",
              f"### Situação de {rotulo(etapa)}\n\n{_situacao(fluxo, etapa, execucao)}"]
    semaforo = {k: v for e in _etapas(etapa) for k, v in passagem.semaforo_da_etapa(estado, e).items()}
    if semaforo:
        partes.append("### Semáforo dos gates desta etapa\n\n"
                      + "\n".join(f"- {icone} `{k}` = {estado[k]}" for k, icone in semaforo.items()))
    pareceres = _pareceres(fluxo)
    if pareceres:
        partes.append(f"### Pareceres humanos desta missão\n\n{pareceres}")

    nomes = _nomes_dos_documentos()
    documentos, fora, resta = [], [], orcamento
    for chave in documentos_da_etapa(estado, etapa):
        texto = _como_texto(estado[chave])
        origem = ' origem="etapa anterior"' if chave in A_MONTANTE[etapa] else ""
        abre = f'<documento chave="{chave}" nome="{nomes.get(chave, chave)}"{origem}'
        if len(texto) <= resta:
            documentos.append(f"{abre}>\n{texto}\n</documento>")
            resta -= len(texto)
        elif resta >= MINIMO_PARA_CORTAR:
            documentos.append(f'{abre} cortado="só os primeiros {resta} de {len(texto)} caracteres">\n'
                              f"{texto[:resta]}\n[… o resto deste documento não coube no contexto]\n</documento>")
            resta = 0
        else:
            fora.append(chave)
    if documentos:
        partes.append("### Documentos da etapa\n\n" + "\n\n".join(documentos))
    else:
        partes.append("### Documentos da etapa\n\nNenhum documento desta etapa foi gravado ainda.")
    if fora:
        partes.append("### Fora do contexto por tamanho\n\n"
                      + ", ".join(f"{nomes.get(k, k)} (`{k}`)" for k in fora))
    return "\n\n".join(partes)


def historico_para_modelo(mensagens: Sequence[Dict[str, Any]]) -> str:
    """As últimas trocas da etapa, com quem perguntou e quando."""
    linhas = []
    for m in list(mensagens)[-2 * TROCAS_NO_HISTORICO:]:
        texto = str(m.get("texto") or "")
        if len(texto) > TETO_MENSAGEM_NO_HISTORICO:
            texto = texto[:TETO_MENSAGEM_NO_HISTORICO] + " […]"
        if m.get("role") == "user":
            linhas.append(f"**Pergunta de {m.get('como')}, {m.get('quando')}:** {texto}")
        else:
            linhas.append(f"**Sua resposta:** {texto}")
    return "\n\n".join(linhas)


def estado_da_conversa(etapa: str, estado: Dict[str, Any], fluxo: Optional[Dict[str, Any]],
                       anteriores: Sequence[Dict[str, Any]], execucao: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """O estado da sessão do ADK que o prompt interpola."""
    return {
        "etapa_da_conversa": rotulo(etapa),
        "etapa_do_parecer": passagem.ROTULO_ETAPA.get((fluxo or {}).get("etapa"), rotulo(etapa)),
        "contexto_da_etapa": montar_contexto(estado, fluxo, etapa, execucao),
        "conversa_anterior": historico_para_modelo(anteriores) or "(é a primeira pergunta desta conversa)",
    }


# ------------------------------------------------------------------ modelo
async def responder(texto: str, etapa: str, estado: Dict[str, Any], fluxo: Optional[Dict[str, Any]],
                    anteriores: Sequence[Dict[str, Any]], execucao: Optional[Dict[str, Any]] = None) -> str:
    """Roda o agente de conversa num runner mínimo, fora da esteira. Falha sobe para quem chamou."""
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    from agents.transversal import get_conversa_etapa_agent

    app = "ConversaEtapa"
    runner = InMemoryRunner(agent=get_conversa_etapa_agent(), app_name=app)
    sessao = await runner.session_service.create_session(
        app_name=app, user_id="conversa", state=estado_da_conversa(etapa, estado, fluxo, anteriores, execucao))
    mensagem = types.Content(role="user", parts=[types.Part.from_text(text=texto)])
    async for _ in runner.run_async(user_id="conversa", session_id=sessao.id, new_message=mensagem):
        pass
    final = await runner.session_service.get_session(app_name=app, user_id="conversa", session_id=sessao.id)
    saida = str((final.state if final else {}).get("resposta_conversa") or "").strip()
    if not saida:
        raise RuntimeError("o modelo não devolveu resposta")
    return saida


async def rascunhar_comentario(etapa: str, estado: Dict[str, Any], fluxo: Optional[Dict[str, Any]],
                               anteriores: Sequence[Dict[str, Any]]) -> str:
    """O comentário do parecer que a conversa sustenta, para quem decide revisar antes de enviar."""
    return await responder(PEDIDO_RASCUNHO, etapa, estado, fluxo, anteriores)
