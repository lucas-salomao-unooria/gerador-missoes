#!/usr/bin/env python3
"""Reexecuta uma etapa da esteira sobre o estado salvo de uma sessão — a mesma lógica do modo
correção do app (`pipeline/reexecucao.py`), por linha de comando.

Uso:
  python scripts/rerodar_etapa.py gs://entre-redes-dev-adk-artifacts/20260921-183442-exp06ef1b --etapa dev
  python scripts/rerodar_etapa.py output/20260921-183442-exp06ef1b --etapa dev --sem-upload
  python scripts/rerodar_etapa.py output/<sessão> --etapa transversal          # só diagnóstico + aprendizado
  python scripts/rerodar_etapa.py output/<sessão> --etapa dev --pedido "trocar o teto de bio para 150"

O que faz: baixa (ou usa) a pasta da sessão; guarda em `.correcoes/<data>-<etapa>/` o que vai
ser sobrescrito; apaga do estado as chaves da etapa pedida e das seguintes, recalcula a herança
dos gates que ficam; roda o orquestrador só com essas etapas, gravando na MESMA pasta; regrava
`conversa.json` preservando data e histórico; sobe de volta ao bucket, salvo `--sem-upload`.

`--pedido` põe o texto em `pedido_correcao`, que todo agente lê; sem ele, a etapa só é refeita.
`--so-esta-etapa` roda apenas a etapa pedida (sem as seguintes), para depuração.
Precisa de GOOGLE_API_KEY no .env e, para o bucket, `gcloud` autenticado. Cuidado: passar `gs://`
baixa o estado do bucket por cima da pasta local.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from config import get_settings  # noqa: E402
from pipeline.reexecucao import ETAPAS, PedidoCorrecao, executar_correcao_sync  # noqa: E402
from pipeline.runner import STATUS_KEYS  # noqa: E402

ETAPAS_CLI = ETAPAS


def _gcloud(*args: str) -> None:
    cmd = ["gcloud", "storage", *args]
    print("   $", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pasta", help="pasta da sessão: caminho local ou gs://bucket/pasta")
    ap.add_argument("--etapa", choices=ETAPAS_CLI, default="dev")
    ap.add_argument("--pedido", default="", help="pedido de correção visível a todos os agentes")
    ap.add_argument("--so-esta-etapa", action="store_true", help="não reexecuta as etapas seguintes")
    ap.add_argument("--sem-upload", action="store_true", help="não sobe o resultado de volta ao bucket")
    args = ap.parse_args()

    settings = get_settings()
    if args.pasta.startswith("gs://"):
        destino = args.pasta.rstrip("/")
        local = settings.output_path / destino.rsplit("/", 1)[-1]
        local.mkdir(parents=True, exist_ok=True)
        print(f"⬇️  Baixando {destino} → {local}")
        _gcloud("rsync", "-r", destino, str(local))
    else:
        destino = None
        local = Path(args.pasta)
    if not (local / "estado.json").exists():
        print(f"❌ {local}/estado.json não existe.")
        return 1

    pedido = PedidoCorrecao(texto=args.pedido) if args.pedido.strip() else None
    print(f"▶️  Etapa `{args.etapa}`{' (só ela)' if args.so_esta_etapa else ''} em {local}"
          + (f" · pedido: {args.pedido[:80]!r}" if pedido else ""))
    result, registro = executar_correcao_sync(local, args.etapa, pedido, so_esta_etapa=args.so_esta_etapa)
    print(f"⏱️  {registro.get('duracao_s', 0):.0f}s · status: {registro.get('status')} · backup em {registro.get('backup')}")
    if result is None:
        print("❌ A correção falhou e a sessão foi restaurada do backup.")
        return 2

    print("\n📊 Gates após a reexecução:")
    for k in STATUS_KEYS:
        if k in result.state:
            print(f"   {k:28} {result.state[k]}")

    if destino and not args.sem_upload:
        print(f"\n⬆️  Subindo {local} → {destino}")
        _gcloud("rsync", "-r", "--exclude", r"^\.adk_artifacts", str(local), destino)
    elif destino:
        print(f"\n⏸️  Upload desligado. Para publicar: gcloud storage rsync -r {local} {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
