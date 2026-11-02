"""O protótipo em alta fidelidade dentro do gerador: gerar a partir da sessão, acompanhar e abrir.

O resultado é publicado em `<sessão>/design/hifi/` — no Cloud Run, `output/` é o bucket montado, então o
protótipo fica com os outros artefatos e sobrevive a deploy. O workspace de trabalho (DS e React por link,
referências da plataforma, builds de lote) fica FORA da sessão, numa pasta temporária: no bucket ele seria
lento e não serve a ninguém depois.

A geração roda em segundo plano: leva perto de uma hora, e a aba do Streamlit não pode ficar presa a ela. Na
máquina local é um processo separado (`scripts/prototipo_hifi.py`). No Cloud Run é o Job `gerador-missoes-hifi`
(Terraform na fundação, imagem `Dockerfile.prototipo-hifi`): o serviço do gerador tem uma instância só e perde
o processo num deploy, e a requisição tem teto de 60 min. O gerador dispara o Job pela API, com a identidade
dele, e o Job publica em `<sessão>/design/hifi` no bucket.
"""
from __future__ import annotations

import base64
import gzip
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional

RAIZ = Path(__file__).resolve().parents[2]
PASTA = Path("design") / "hifi"
#: O pacote do DS (com `dist/`, `src/` e `node_modules/`) e o monorepo da plataforma. Em máquina de
#: desenvolvimento, os repositórios vizinhos; no Job do Cloud Run, o preparo os põe nestes caminhos.
DS_PADRAO = os.getenv("PROTOTIPO_HIFI_DS", "/Volumes/Documentos/Unooria/storybook-unooria")
PLATAFORMA_PADRAO = os.getenv("PROTOTIPO_HIFI_PLATAFORMA", "/Volumes/Documentos/Unooria/plataforma-unooria")
PYTHON_MOTOR = RAIZ / ".venv-antigravity" / "bin" / "python"
MODELOS = ("gemini-4-argon", "gemini-3.8-flash")
#: O Job do Cloud Run que gera na nuvem: `projects/<p>/locations/<r>/jobs/<nome>`. No serviço do gerador
#: (`K_SERVICE`) ele é deduzido do projeto; fora dele, só com `PROTOTIPO_HIFI_JOB`.
REGIAO_JOB = "us-east1"
NOME_JOB = "gerador-missoes-hifi"


def job_na_nuvem() -> Optional[str]:
    explicito = os.getenv("PROTOTIPO_HIFI_JOB")
    if explicito:
        return explicito
    projeto = os.getenv("GOOGLE_CLOUD_PROJECT")
    if os.getenv("K_SERVICE") and projeto:
        return f"projects/{projeto}/locations/{REGIAO_JOB}/jobs/{NOME_JOB}"
    return None


def _api(metodo: str, caminho: str, corpo: Optional[dict] = None) -> dict:
    """Chamada à API do Cloud Run v2 com a identidade do ambiente (no Cloud Run, a conta do gerador)."""
    import google.auth
    from google.auth.transport.requests import AuthorizedSession

    credenciais, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    resposta = AuthorizedSession(credenciais).request(metodo, f"https://run.googleapis.com/v2/{caminho}",
                                                      json=corpo, timeout=60)
    resposta.raise_for_status()
    return resposta.json()
#: O `DEFAULT_MODEL` do google-antigravity 0.1.23, para relatórios que não gravaram o nome.
MODELO_PADRAO_SDK = "gemini-3.8-flash"


def pasta(sessao: str | Path) -> Path:
    return Path(sessao) / PASTA


def pronto(sessao: str | Path) -> bool:
    return (pasta(sessao) / "prototipo.html").exists()


def resumo(sessao: str | Path) -> Optional[Dict[str, Any]]:
    arq = pasta(sessao) / "final.json"
    return json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else None


def tem_insumos(sessao: str | Path) -> bool:
    """A etapa de design precisa ter rodado: o protótipo sai do inventário da jornada e do one-pager."""
    s = Path(sessao)
    return (s / "design" / "02-jornada-telas.md").exists() and (s / "produto" / "00-one-pager.md").exists()


def indisponivel() -> Optional[str]:
    """Por que a geração não pode rodar NESTE ambiente, ou None quando pode."""
    if job_na_nuvem():
        return None
    if not PYTHON_MOTOR.exists():
        return ("A venv do Antigravity SDK não está instalada neste ambiente (`.venv-antigravity`). No Cloud Run "
                "a geração vai rodar num Job próprio, ainda não publicado: por enquanto, gere na máquina local.")
    if not (Path(DS_PADRAO) / "dist").exists():
        return f"O pacote do Design System não foi encontrado em `{DS_PADRAO}` (PROTOTIPO_HIFI_DS)."
    if not shutil.which("node"):
        return "O Node não está instalado neste ambiente."
    return None


def _vivo(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def _execucao_na_nuvem(info: Dict[str, Any]) -> Dict[str, Any]:
    """`{rodando, falhou, mensagem}` da execução do Job, pela API. Erro de rede conta como «rodando» (tenta de novo)."""
    try:
        e = _api("GET", info["execucao"])
    except Exception as exc:  # a tela não pode quebrar porque a API piscou
        return {"rodando": True, "falhou": False, "mensagem": f"sem resposta da API do Cloud Run ({exc})"}
    if not e.get("completionTime"):
        return {"rodando": True, "falhou": False, "mensagem": ""}
    falhas = int(e.get("failedCount") or 0) + int(e.get("cancelledCount") or 0)
    condicao = next((c for c in e.get("conditions") or [] if c.get("type") == "Completed"), {})
    return {"rodando": False, "falhou": falhas > 0, "mensagem": condicao.get("message", "")}


def em_andamento(sessao: str | Path) -> Optional[Dict[str, Any]]:
    """A geração rodando agora para esta sessão: início, modelo e quantos lotes já fecharam."""
    arq = pasta(sessao) / "execucao.json"
    if not arq.exists():
        return None
    info = json.loads(arq.read_text(encoding="utf-8"))
    if info.get("execucao"):
        # no Job, os lotes moram no /tmp da tarefa: o andamento que dá para mostrar é o da execução
        return {**info, "lotes_prontos": "?"} if _execucao_na_nuvem(info)["rodando"] else None
    if not _vivo(int(info.get("pid", 0))):
        return None
    ws = Path(info["workspace"])
    feitos = len(list((ws / "relatorios").glob("*.json"))) if (ws / "relatorios").exists() else 0
    return {**info, "lotes_prontos": feitos}


def falhou(sessao: str | Path) -> Optional[str]:
    """O fim do log de uma geração que parou sem publicar, para mostrar no gerador."""
    arq = pasta(sessao) / "execucao.json"
    if not arq.exists() or pronto(sessao) or em_andamento(sessao):
        return None
    info = json.loads(arq.read_text(encoding="utf-8"))
    if info.get("execucao"):
        estado = _execucao_na_nuvem(info)
        if not estado["falhou"]:
            return None
        nome = info["execucao"].rsplit("/", 1)[-1]
        return (f"A execução `{nome}` do Job terminou com falha: {estado['mensagem'] or 'sem mensagem'}. Os logs estão "
                f"no Cloud Run → Jobs → {NOME_JOB} → execuções.")
    log = Path(info.get("log", ""))
    return log.read_text(encoding="utf-8", errors="ignore")[-1500:] if log.exists() else "a geração parou sem log"


def iniciar_na_nuvem(sessao: Path, modelo: str, job: str) -> Dict[str, Any]:
    """Dispara o Job do Cloud Run para a sessão. Ele lê e publica no bucket, que no serviço é o `output/` montado."""
    corpo = {"overrides": {"containerOverrides": [{"env": [{"name": "SESSAO", "value": sessao.name},
                                                           {"name": "MODELO", "value": modelo}]}]}}
    operacao = _api("POST", f"{job}:run", corpo)
    execucao = (operacao.get("metadata") or {}).get("name", "")
    info = {"execucao": execucao, "inicio": time.strftime("%Y-%m-%d %H:%M"), "modelo": modelo, "job": job}
    destino = pasta(sessao)
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "execucao.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    return info


def iniciar(sessao: str | Path, modelo: str = MODELOS[0]) -> Dict[str, Any]:
    """Dispara a geração em segundo plano e devolve o registro da execução."""
    sessao = Path(sessao).resolve()
    job = job_na_nuvem()
    if job:
        return iniciar_na_nuvem(sessao, modelo, job)
    destino = pasta(sessao)
    destino.mkdir(parents=True, exist_ok=True)
    ws = Path(tempfile.gettempdir()) / "prototipo-hifi" / f"{sessao.name}-{int(time.time())}"
    ws.mkdir(parents=True, exist_ok=True)
    log = ws / "geracao.log"
    cmd = [sys.executable, str(RAIZ / "scripts" / "prototipo_hifi.py"), "--sessao", str(sessao), "--destino", str(ws),
           "--ds", DS_PADRAO, "--plataforma", PLATAFORMA_PADRAO, "--modelo", modelo, "--publicar", str(destino)]
    with open(log, "w", encoding="utf-8") as saida:
        proc = subprocess.Popen(cmd, cwd=RAIZ, stdout=saida, stderr=subprocess.STDOUT, start_new_session=True)
    info = {"pid": proc.pid, "inicio": time.strftime("%Y-%m-%d %H:%M"), "modelo": modelo,
            "workspace": str(ws), "log": str(log)}
    (destino / "execucao.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    return info


def custo_da_geracao(relatorios: list) -> Dict[str, Any]:
    """Uma linha de `custo_missao` para a geração: tokens de cada lote pelo modelo dele, mais as imagens geradas.

    O relatório do lote guarda o uso do SDK (`prompt`, `cache`, `saida`, `pensamento`); `prompt` já inclui a parte
    em cache, como a `entrada` do `tools/custo`. O lote que rodou no modelo padrão grava «<modelo> (padrão do SDK)».
    """
    from tools.custo import PRECO_IMAGEM, cotacao_usd_brl, custo_da_execucao

    por_lote, modelos = {}, {}
    imagens = 0
    for r in relatorios:
        uso = r.get("uso") or {}
        # a correção roda com os mesmos nomes de lote da geração: sem o prefixo, uma linha apagaria a outra
        chave = f"hifi:{'correcao-' if r.get('correcao') else ''}{r.get('lote', '?')}"
        por_lote[chave] = {"entrada": uso.get("prompt", 0), "cache": uso.get("cache", 0), "saida": uso.get("saida", 0),
                           "pensamento": uso.get("pensamento", 0), "chamadas": len(r.get("chamadas") or [])}
        modelo = str(r.get("modelo") or "").split(" ")[0]
        # relatório anterior a 30/10/2026 gravava só «padrão do SDK»: o padrão do google-antigravity 0.1.23
        modelos[chave] = MODELO_PADRAO_SDK if modelo in ("", "padrão") else modelo
        imagens += len(r.get("imagens") or [])
    linha = custo_da_execucao(por_lote, next(iter(modelos.values()), ""), modelos, etapas=["prototipo-hifi"])
    usd_imagens = imagens * PRECO_IMAGEM["gemini-3.1-flash-lite-image"]
    cotacao = linha.get("cotacao") or cotacao_usd_brl()[0]
    linha["usd_imagens"] = round(usd_imagens, 6)
    linha["usd"] = round(linha["usd"] + usd_imagens, 4)
    linha["brl"] = round(linha["usd"] * cotacao, 2)
    linha["imagens"] = {"quantidade": imagens, "usd": round(usd_imagens, 4)}
    if isinstance(linha.get("por_etapa"), dict) and "prototipo-hifi" in linha["por_etapa"]:
        bloco_etapa = linha["por_etapa"]["prototipo-hifi"]
        bloco_etapa["usd_imagens"] = round(float(bloco_etapa.get("usd_imagens", 0.0) or 0.0) + usd_imagens, 6)
        bloco_etapa["usd"] = round(float(bloco_etapa.get("usd", 0.0) or 0.0) + usd_imagens, 4)
        bloco_etapa["brl"] = round(bloco_etapa["usd"] * cotacao, 2)
        bloco_etapa["imagens"] = {"quantidade": imagens, "usd": round(usd_imagens, 4)}
    return linha


def registrar_custo(sessao: str | Path, relatorios: list) -> Optional[Dict[str, Any]]:
    """Soma a geração ao `custo_missao` do `estado.json` da sessão, como mais uma execução (etapa `prototipo-hifi`)."""
    from tools.custo import KEY_CUSTO, acumular

    caminho = Path(sessao) / "estado.json"
    if not caminho.exists() or not relatorios:
        return None
    linha = custo_da_geracao(relatorios)
    estado = json.loads(caminho.read_text(encoding="utf-8"))
    estado[KEY_CUSTO] = acumular(estado.get(KEY_CUSTO), linha, ["prototipo-hifi"])
    caminho.write_text(json.dumps(estado, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return linha


def html_comprimido(sessao: str | Path) -> str:
    """O protótipo em gzip + base64, para o navegador abrir numa guia nova sem ir ao servidor de novo."""
    return base64.b64encode(gzip.compress((pasta(sessao) / "prototipo.html").read_bytes(), 6)).decode("ascii")


def zip_das_telas(sessao: str | Path) -> bytes:
    """O código das telas, o mock e o CSS da missão: o ponto de partida do dev."""
    base = pasta(sessao) / "codigo"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for arq in sorted(base.rglob("*")) if base.exists() else []:
            if arq.is_file():
                z.write(arq, arq.relative_to(base))
    return buf.getvalue()
