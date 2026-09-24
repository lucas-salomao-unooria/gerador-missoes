"""Execução das etapas em segundo plano, para a aba do navegador não precisar ficar aberta.

Cada etapa leva de 7 a 30 minutos. Rodando dentro do rerun do Streamlit, fechar a aba (ou
recarregar, que agora também pede o cookie de login) interrompia a execução — e, com três pessoas
revezando, ninguém deve ficar olhando a tela esperando. Aqui a etapa roda numa `threading.Thread`
com loop asyncio próprio, e o progresso vai para `run_dir/execucao.json`, que a tela lê a cada 5 s:

    {"situacao": "executando", "tipo": "iniciar", "etapa": "design", "agente_atual": "D2Jornada",
     "gates": {"design_status": "aprovado"}, "iniciado_em": 1790000000.0,
     "batimento": 1790000030.0, "backup": ".correcoes/20260923-140211-passagem-design", "erro": ""}

Uma execução por sessão: `em_execucao` é a trava. O batimento é gravado a cada 30 s por uma thread
à parte, porque uma chamada longa ao modelo pode ficar minutos sem emitir evento. Batimento com
mais de 2 min e nenhuma thread viva neste processo = a execução morreu (reinício do container,
deploy no meio): `conferir_execucao_morta` restaura o backup e devolve a missão ao dono.

No Cloud Run isto exige `--no-cpu-throttling` (CPU fora de requisição) e `--min-instances 1` (o
container não pode ser desligado no meio de uma etapa) — ver `.github/workflows/deploy.yml` e o
Terraform do gerador.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Optional

from pipeline import passagem

logger = logging.getLogger(__name__)

ARQUIVO = "execucao.json"
BATIMENTO_S = 30
MORTA_APOS_S = 120

_threads: Dict[str, threading.Thread] = {}
_lock = threading.Lock()


class ExecucaoEmAndamento(RuntimeError):
    """Já existe uma etapa rodando nesta missão."""


# ------------------------------------------------------------------ estado em disco
def _caminho(run_dir: Path) -> Path:
    return Path(run_dir) / ARQUIVO


def ler_execucao(run_dir: Path) -> Optional[Dict[str, Any]]:
    try:
        dados = json.loads(_caminho(run_dir).read_text(encoding="utf-8"))
        return dados if isinstance(dados, dict) else None
    except (OSError, ValueError):
        return None


def _gravar(run_dir: Path, dados: Dict[str, Any]) -> None:
    caminho = _caminho(run_dir)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix(".tmp")
    temporario.write_text(json.dumps(dados, ensure_ascii=False, default=str), encoding="utf-8")
    temporario.replace(caminho)


def _thread_viva(run_dir: Path) -> bool:
    with _lock:
        t = _threads.get(str(Path(run_dir).resolve()))
        return bool(t and t.is_alive())


def em_execucao(run_dir: Path, agora: Optional[float] = None) -> bool:
    if _thread_viva(run_dir):
        return True
    dados = ler_execucao(run_dir)
    agora = time.time() if agora is None else agora
    return bool(dados and dados.get("situacao") == "executando"
                and agora - float(dados.get("batimento") or 0) < MORTA_APOS_S)


def conferir_execucao_morta(run_dir: Path, agora: Optional[float] = None) -> bool:
    """Se a execução registrada morreu sem avisar, restaura o backup e marca o fluxo como falho."""
    dados = ler_execucao(run_dir)
    agora = time.time() if agora is None else agora
    if not dados or dados.get("situacao") != "executando" or _thread_viva(run_dir):
        return False
    if agora - float(dados.get("batimento") or 0) < MORTA_APOS_S:
        return False
    if dados.get("backup"):
        from pipeline.reexecucao import restaurar_backup

        try:
            restaurar_backup(Path(run_dir), Path(run_dir) / dados["backup"])
        except OSError as exc:  # pragma: no cover - disco
            logger.warning("Backup de %s não restaurado: %s", run_dir, exc)
    _fechar(Path(run_dir), dados, ok=False, erro="a execução foi interrompida (reinício do servidor?)")
    return True


def _fechar(run_dir: Path, dados: Dict[str, Any], ok: bool, erro: str = "") -> None:
    """Grava o fim da execução e devolve a missão ao dono da etapa."""
    dados = {**dados, "situacao": "concluida" if ok else "falhou", "erro": erro, "terminou_em": time.time(),
             "batimento": time.time()}
    _gravar(run_dir, dados)
    fluxo = passagem.ler_fluxo(run_dir)
    if fluxo:
        try:
            passagem.registrar_fluxo(run_dir, passagem.concluir_execucao(fluxo, ok), None)
        except OSError as exc:  # pragma: no cover - disco
            logger.warning("Fluxo de %s não atualizado: %s", run_dir, exc)
    notificar({"tipo": "execucao_terminou", "run_dir": str(run_dir), "ok": ok, "etapa": dados.get("etapa"),
               "erro": erro})


# ------------------------------------------------------------------ avisos
def notificar(evento: Dict[str, Any]) -> None:
    """Gancho para avisar fora do app (Slack, e-mail). Hoje só registra: não há provedor ligado.

    A fila "Aguardando você" da barra lateral é o aviso de verdade — ela lê o `fluxo` de cada missão.
    """
    logger.info("passagem: %s", evento)


# ------------------------------------------------------------------ execução
def _stream_do_efeito(run_dir: Path, efeito: passagem.Efeito, notas: str,
                      opcoes: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
    from pipeline.reexecucao import PedidoCorrecao, executar_correcao_stream, iniciar_etapa_stream

    if efeito.tipo == "iniciar":
        return iniciar_etapa_stream(run_dir, efeito.etapa, notas, **opcoes)
    if efeito.tipo == "encerrar":
        return iniciar_etapa_stream(run_dir, "transversal", notas, **opcoes)
    if efeito.tipo == "refazer":
        # só esta etapa: a seguinte espera o parecer, e roda quando o dono dela iniciar
        return executar_correcao_stream(run_dir, efeito.etapa, PedidoCorrecao(texto=efeito.pedido), None,
                                        so_esta_etapa=True, notas_de_passagem=notas,
                                        com_transversal=False, **opcoes)
    raise ValueError(f"efeito desconhecido: {efeito.tipo!r}")


_FIM_OK = {"etapa_completed", "correcao_completed"}
_FIM_ERRO = {"etapa_error", "correcao_error", "pipeline_error"}


async def _consumir(run_dir: Path, stream: AsyncGenerator[Dict[str, Any], None], dados: Dict[str, Any],
                    nova: bool) -> None:
    ok, erro = False, ""
    try:
        async for evento in stream:
            tipo = evento.get("type")
            mudou = False
            if tipo == "agent_started":
                dados["agente_atual"] = evento.get("agent_name", "")
                mudou = True
            elif tipo == "gate_status":
                dados["gates"] = evento.get("status") or {}
                mudou = True
            elif tipo in ("etapa_started", "correcao_started") and evento.get("backup"):
                dados["backup"] = evento["backup"]
                mudou = True
            elif tipo in _FIM_OK or (nova and tipo == "pipeline_completed"):
                resultado = evento.get("result")
                ok = getattr(resultado, "status", "") != "error"
                erro = "" if ok else str(getattr(resultado, "error_message", "") or "erro no runner")
            elif tipo in _FIM_ERRO:
                ok, erro = False, str(evento.get("error") or "erro no runner")
            if mudou:
                dados["batimento"] = time.time()
                _gravar(run_dir, dados)
    except Exception as exc:  # a thread não pode morrer calada: o fluxo ficaria "gerando" para sempre
        logger.exception("Execução em segundo plano falhou em %s", run_dir)
        ok, erro = False, str(exc)
    _fechar(run_dir, dados, ok, erro)


def _disparar(run_dir: Path, dados: Dict[str, Any], fabrica_stream, nova: bool = False) -> None:
    run_dir = Path(run_dir)
    chave = str(run_dir.resolve())
    with _lock:
        vivo = _threads.get(chave)
        if vivo and vivo.is_alive():
            raise ExecucaoEmAndamento("Esta missão já tem uma etapa rodando.")
    if em_execucao(run_dir):
        raise ExecucaoEmAndamento("Esta missão já tem uma etapa rodando.")
    agora = time.time()
    dados = {"situacao": "executando", "agente_atual": "", "gates": {}, "iniciado_em": agora,
             "batimento": agora, "backup": "", "erro": "", **dados}
    _gravar(run_dir, dados)
    parar = threading.Event()

    def batimento() -> None:
        while not parar.wait(BATIMENTO_S):
            atual = ler_execucao(run_dir) or dados
            if atual.get("situacao") != "executando":
                return
            _gravar(run_dir, {**atual, "batimento": time.time()})

    def alvo() -> None:
        pulso = threading.Thread(target=batimento, name=f"batimento-{run_dir.name}", daemon=True)
        pulso.start()
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_consumir(run_dir, fabrica_stream(), dados, nova))
        finally:
            parar.set()
            loop.close()

    t = threading.Thread(target=alvo, name=f"etapa-{run_dir.name}", daemon=True)
    with _lock:
        _threads[chave] = t
    t.start()


def executar_efeito(run_dir: Path, efeito: passagem.Efeito, notas: str, **opcoes: Any) -> None:
    """Dispara o efeito de uma decisão (`passagem.aplicar`) em segundo plano. Volta na hora."""
    _disparar(run_dir, {"tipo": efeito.tipo, "etapa": efeito.etapa},
              lambda: _stream_do_efeito(Path(run_dir), efeito, notas, opcoes))


def iniciar_nova(run_dir: Path, prompt: str, user_id: str, session_id: str, doc_batch: Any,
                 **opcoes: Any) -> None:
    """Missão nova com parecer humano: roda só produto, na pasta já criada, em segundo plano."""
    from pipeline.runner import run_orchestrator_pipeline_stream

    _disparar(run_dir, {"tipo": "nova", "etapa": "produto"},
              lambda: run_orchestrator_pipeline_stream(
                  prompt=prompt, user_id=user_id, session_id=session_id, stages=["produto"],
                  doc_batch=doc_batch, run_dir=Path(run_dir), com_transversal=False, **opcoes),
              nova=True)


def aguardar(run_dir: Path, timeout: float = 5.0) -> None:
    """Espera a thread da missão terminar (para testes e para a linha de comando)."""
    with _lock:
        t = _threads.get(str(Path(run_dir).resolve()))
    if t:
        t.join(timeout)
