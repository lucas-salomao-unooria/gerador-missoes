"""Execução das etapas em segundo plano, para a aba do navegador não precisar ficar aberta.

Cada etapa leva de 7 a 30 minutos. Rodando dentro do rerun do Streamlit, fechar a aba (ou
recarregar, que agora também pede o cookie de login) interrompia a execução — e, com três pessoas
revezando, ninguém deve ficar olhando a tela esperando. Aqui a etapa roda numa `threading.Thread`
com loop asyncio próprio.

**Onde fica o estado da execução — e por que em dois lugares.** O progresso (agente atual, gates,
batimento) muda a cada evento e é lido pela tela a cada 5 s: ele vive no **disco local** da
instância (`<tmp>/gerador-execucoes/<sessão>.json`). No bucket, `run_dir/execucao.json` só é gravado
três vezes — no início, quando o backup nasce e no fim. Em 24/09/2026 o progresso inteiro ia para o
bucket (montado por gcsfuse), com `.tmp` + rename a cada evento e a cada 30 s: foi o dia em que o
gcsfuse do Cloud Run passou a entrar em pânico (`convertInMessage: Corrupt OpLookup`) no meio da
etapa, derrubando a instância cinco vezes — nenhuma nos sete dias anteriores. E cada falha momentânea
do volume (`Stale file handle`, `Transport endpoint is not connected`) matava a thread do batimento.

    {"situacao": "executando", "tipo": "iniciar", "etapa": "design", "agente_atual": "D2Jornada",
     "gates": {"design_status": "aprovado"}, "iniciado_em": 1790000000.0,
     "batimento": 1790000030.0, "backup": ".correcoes/20260923-140211-passagem-design", "erro": ""}

**Uma execução por sessão, e como se sabe que ela morreu.** O serviço roda com uma instância só
(`--max-instances 1`), então "está rodando" é "há uma thread viva *neste processo*". Se o bucket diz
`executando` e nenhuma thread daqui roda a etapa, a instância que a rodava morreu (reinício, deploy,
pânico do volume): `conferir_execucao_morta` restaura o backup e devolve a missão ao dono. Logo depois
de o processo subir há uma folga, porque numa troca de revisão a instância anterior pode estar
terminando.

No Cloud Run isto exige `--no-cpu-throttling` (CPU fora de requisição) e `--min-instances 1` (o
container não pode ser desligado no meio de uma etapa) — ver `.github/workflows/deploy.yml` e o
Terraform do gerador.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Dict, Optional

from pipeline import passagem

logger = logging.getLogger(__name__)

ARQUIVO = "execucao.json"
BATIMENTO_S = 30
MORTA_APOS_S = 120
#: Numa troca de revisão, a instância anterior ainda pode estar fechando a etapa dela.
FOLGA_AO_SUBIR_S = 45
TENTATIVAS = 3

_INICIO_PROCESSO = time.time()
_threads: Dict[str, threading.Thread] = {}
_lock = threading.Lock()


class ExecucaoEmAndamento(RuntimeError):
    """Já existe uma etapa rodando nesta missão."""


# ------------------------------------------------------------------ estado em disco
def _dir_local() -> Path:
    return Path(os.getenv("EXECUCAO_LOCAL_DIR") or tempfile.gettempdir()) / "gerador-execucoes"


def _caminho_local(run_dir: Path) -> Path:
    return _dir_local() / f"{Path(run_dir).name}.json"


def _caminho_bucket(run_dir: Path) -> Path:
    return Path(run_dir) / ARQUIVO


def _tentar(descricao: str, fn: Callable[[], Any]) -> Any:
    """Repete uma operação de disco que o volume do bucket pode recusar por um instante.

    Nunca levanta: uma gravação de estado que falha não pode derrubar a etapa que ela descreve.
    """
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            return fn()
        except OSError as exc:
            if tentativa == TENTATIVAS:
                logger.warning("%s falhou após %d tentativas: %s", descricao, TENTATIVAS, exc)
                return None
            time.sleep(0.5 * tentativa)
    return None


def _ler(caminho: Path) -> Optional[Dict[str, Any]]:
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        return dados if isinstance(dados, dict) else None
    except (OSError, ValueError):
        return None


def _gravar_local(run_dir: Path, dados: Dict[str, Any]) -> None:
    def gravar() -> None:
        caminho = _caminho_local(run_dir)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = caminho.with_suffix(".tmp")
        temporario.write_text(json.dumps(dados, ensure_ascii=False, default=str), encoding="utf-8")
        temporario.replace(caminho)  # rename é atômico no disco local; no gcsfuse, não

    _tentar("gravar o progresso local", gravar)


def _gravar(run_dir: Path, dados: Dict[str, Any]) -> None:
    """Grava no bucket: escrita direta, sem `.tmp` + rename, que no gcsfuse vira cópia e remoção."""
    _tentar(f"gravar {ARQUIVO} de {Path(run_dir).name}",
            lambda: _caminho_bucket(run_dir).write_text(json.dumps(dados, ensure_ascii=False, default=str),
                                                        encoding="utf-8"))


def ler_execucao(run_dir: Path) -> Optional[Dict[str, Any]]:
    """O progresso local, se esta instância rodou a etapa; senão, o que o bucket guardou."""
    return _ler(_caminho_local(run_dir)) or _ler(_caminho_bucket(run_dir))


def _thread_viva(run_dir: Path) -> bool:
    with _lock:
        t = _threads.get(str(Path(run_dir).resolve()))
        return bool(t and t.is_alive())


def em_execucao(run_dir: Path, agora: Optional[float] = None) -> bool:
    """Há uma etapa rodando nesta instância. Não lê o bucket: com uma instância só, basta o processo."""
    if _thread_viva(run_dir):
        return True
    local = _ler(_caminho_local(run_dir))
    agora = time.time() if agora is None else agora
    return bool(local and local.get("situacao") == "executando"
                and agora - float(local.get("batimento") or 0) < MORTA_APOS_S)


def conferir_execucao_morta(run_dir: Path, agora: Optional[float] = None) -> bool:
    """Se o bucket diz que a etapa roda e nenhuma thread daqui a roda, restaura o backup e a devolve."""
    agora = time.time() if agora is None else agora
    if em_execucao(run_dir, agora) or agora - _INICIO_PROCESSO < FOLGA_AO_SUBIR_S:
        return False
    dados = _ler(_caminho_bucket(run_dir))
    if not dados or dados.get("situacao") != "executando":
        return False
    local = _ler(_caminho_local(run_dir))
    if local and local.get("situacao") == "executando":
        dados = {**dados, **local}  # a thread morreu neste processo: o local sabe mais
    if dados.get("backup"):
        from pipeline.reexecucao import restaurar_backup

        _tentar(f"restaurar o backup de {Path(run_dir).name}",
                lambda: restaurar_backup(Path(run_dir), Path(run_dir) / dados["backup"],
                                         (dados.get("custo") or {}).get("execucao"), [dados.get("etapa", "")]))
    _fechar(Path(run_dir), dados, ok=False,
            erro="a instância que rodava a etapa parou no meio (reinício, deploy ou falha do volume)")
    return True


def _fechar(run_dir: Path, dados: Dict[str, Any], ok: bool, erro: str = "") -> None:
    """Grava o fim da execução e devolve a missão ao dono da etapa."""
    dados = {**dados, "situacao": "concluida" if ok else "falhou", "erro": erro, "terminou_em": time.time(),
             "batimento": time.time()}
    _gravar_local(run_dir, dados)
    _gravar(run_dir, dados)
    fluxo = passagem.ler_fluxo(run_dir)
    if fluxo:
        _tentar(f"atualizar o fluxo de {run_dir.name}",
                lambda: passagem.registrar_fluxo(run_dir, passagem.concluir_execucao(fluxo, ok), None))
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
                # o que já rodou nesta execução, para a animação da esteira (`pipeline/esteira_visual.py`)
                if dados["agente_atual"] and dados["agente_atual"] not in dados.setdefault("vistos", []):
                    dados["vistos"].append(dados["agente_atual"])
                mudou = True
            elif tipo == "gate_status":
                dados["gates"] = evento.get("status") or {}
                mudou = True
            elif tipo == "custo_parcial":
                # o custo ao vivo (`tools/custo.py`): só no disco local, como o resto do progresso
                dados["custo"] = {"execucao": evento.get("custo") or {}, "missao_antes": evento.get("missao_antes") or {}}
                mudou = True
            elif tipo in ("etapa_started", "correcao_started") and evento.get("backup"):
                dados["backup"] = evento["backup"]
                # o backup vai ao bucket: é o que permite desfazer a etapa se esta instância morrer
                _gravar(run_dir, dados)
                mudou = True
            elif tipo in _FIM_OK or (nova and tipo == "pipeline_completed"):
                resultado = evento.get("result")
                ok = getattr(resultado, "status", "") != "error"
                erro = "" if ok else str(getattr(resultado, "error_message", "") or "erro no runner")
            elif tipo in _FIM_ERRO:
                ok, erro = False, str(evento.get("error") or "erro no runner")
            if mudou:
                dados["batimento"] = time.time()
                _gravar_local(run_dir, dados)
    except Exception as exc:  # a thread não pode morrer calada: o fluxo ficaria "gerando" para sempre
        logger.exception("Execução em segundo plano falhou em %s", run_dir)
        ok, erro = False, str(exc)
    _fechar(run_dir, dados, ok, erro)


def _disparar(run_dir: Path, dados: Dict[str, Any], fabrica_stream, nova: bool = False) -> None:
    run_dir = Path(run_dir)
    chave = str(run_dir.resolve())
    if em_execucao(run_dir):
        raise ExecucaoEmAndamento("Esta missão já tem uma etapa rodando.")
    agora = time.time()
    dados = {"situacao": "executando", "agente_atual": "", "vistos": [], "gates": {}, "iniciado_em": agora,
             "batimento": agora, "backup": "", "erro": "", **dados}
    _gravar_local(run_dir, dados)
    _gravar(run_dir, dados)
    parar = threading.Event()

    def batimento() -> None:
        # só no disco local: é o que a tela lê a cada 5 s, e o bucket não precisa saber disso
        while not parar.wait(BATIMENTO_S):
            atual = _ler(_caminho_local(run_dir)) or dados
            if atual.get("situacao") != "executando":
                return
            _gravar_local(run_dir, {**atual, "batimento": time.time()})

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
        if (vivo := _threads.get(chave)) and vivo.is_alive():
            raise ExecucaoEmAndamento("Esta missão já tem uma etapa rodando.")
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
