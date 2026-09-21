#!/usr/bin/env python3
"""Reexecuta UMA etapa da esteira sobre o estado salvo de uma execução anterior.

Uso:
  python scripts/rerodar_etapa.py gs://entre-redes-dev-adk-artifacts/20260921-183442-exp06ef1b --etapa dev
  python scripts/rerodar_etapa.py output/20260921-183442-exp06ef1b --etapa dev --sem-upload
  python scripts/rerodar_etapa.py output/20260921-183442-exp06ef1b --etapa transversal   # só diagnóstico + aprendizado

O que faz:
  1. baixa (ou usa) a pasta da sessão e lê `estado.json` e `conversa.json`;
  2. guarda uma cópia do que vai ser sobrescrito em `_reexecucoes/<data>/`;
  3. apaga do estado as chaves que a etapa pedida (e as seguintes) produzem, mais as marcas
     de herança degradada (`degradacoes`, `heranca_degradada`, `pipeline_bloqueado`…) —
     produto (e design, se a etapa for dev) ficam exatamente como estavam;
  4. roda o orquestrador só com essa etapa (+ diagnóstico e aprendizado, que rodam sempre),
     gravando na MESMA pasta: arquivos da etapa, PRD, estado.json, conversa.json;
  5. sobe a pasta de volta ao bucket, a não ser com `--sem-upload`.

Por que existe: rodar a esteira inteira custa ~20 min e reescreve produto e design a cada vez,
então não dá para saber se um defeito é novo ou o mesmo sob outro texto. Aqui a entrada fica
fixa e a etapa roda em minutos. Precisa de GOOGLE_API_KEY no .env e, para o bucket, `gcloud`
autenticado no projeto.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from config import get_settings  # noqa: E402
from pipeline.runner import STATUS_KEYS, run_orchestrator_pipeline_sync  # noqa: E402

CHAVES_DEV = {
    "manifesto_report", "manifesto_status", "manifesto_status_envelope",
    "handoff_dev", "brief_assets", "handoff_rodada",
    "telemetria_report", "telemetria_status", "telemetria_status_envelope",
    "rastro_lacunas_report", "rastro_lacunas_status", "rastro_lacunas_status_envelope",
    "validacao_produto_narrativa", "validacao_design_imersao", "validacao_pedagogia_bncc",
    "validacao_dados_lgpd", "validacao_tecnica_arquitetura", "validacao_dev_report",
    "dev_status", "dev_status_envelope", "banca_rodada",
    "prd_final", "prd_check_report", "prd_status", "prd_status_envelope", "prd_rodada",
    "one_pager_pedagogico",
}
CHAVES_DESIGN = {
    "fechamento_lacunas", "relatorio_lacunas", "lacunas_status", "lacunas_status_envelope",
    "ambiente_simulado", "ambiente_status", "ambiente_status_envelope",
    "brief_oficio", "jornada_telas", "fluxo_arestas", "copy_strings", "camada_caa",
    "wireframes_cobertura", "copy_strings_revisada", "prototipo_html", "prototipo_arquivo",
    "prototipo_relatorio", "diagramas_html", "stitch_links", "miro_links", "miro_board",
    "qa_entregaveis_report", "design_status", "design_status_envelope", "qa_design_rodada",
} | CHAVES_DEV
#: Marcas que fazem tudo a jusante sair `[PROVISÓRIO]`. Elas descrevem a execução anterior;
#: a reexecução recomputa os gates e registra as suas próprias.
CHAVES_HERANCA = {"degradacoes", "heranca_degradada", "agentes_degradados", "pipeline_bloqueado", "pipeline_bloqueio_motivo"}
CHAVES_TRANSVERSAL = {"diagnostico_execucao", "diagnostico_status", "diagnostico_status_envelope", "aprendizado_registro"}
#: `transversal` refaz só diagnóstico e aprendizado (~1 min), sem tocar em nenhuma etapa nem nas
#: marcas de herança — serve quando o defeito estava no próprio diagnóstico.
CHAVES_POR_ETAPA = {"design": CHAVES_DESIGN, "dev": CHAVES_DEV, "transversal": set()}
ARQUIVOS_PARA_BACKUP = ("estado.json", "conversa.json", "diagnostico-execucao.md", "aprendizado.md", "PRD.md", "one-pager-pedagogico.md")


def _gcloud(*args: str) -> None:
    cmd = ["gcloud", "storage", *args]
    print("   $", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pasta", help="pasta da sessão: caminho local ou gs://bucket/pasta")
    ap.add_argument("--etapa", choices=sorted(CHAVES_POR_ETAPA), default="dev")
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

    estado = json.loads((local / "estado.json").read_text(encoding="utf-8"))
    conversa = json.loads((local / "conversa.json").read_text(encoding="utf-8")) if (local / "conversa.json").exists() else {}
    briefing = estado.get("briefing") or ((local / "briefing-original.md").read_text(encoding="utf-8") if (local / "briefing-original.md").exists() else "")

    # 2. backup do que vai ser sobrescrito
    backup = local / "_reexecucoes" / time.strftime("%Y%m%d-%H%M%S")
    backup.mkdir(parents=True, exist_ok=True)
    for nome in ARQUIVOS_PARA_BACKUP:
        if (local / nome).exists():
            shutil.copy2(local / nome, backup / nome)
    if (local / args.etapa).is_dir():
        shutil.copytree(local / args.etapa, backup / args.etapa)
    print(f"🗂️  Cópia do anterior em {backup}")

    # 3. limpa o que a etapa produz
    remover = CHAVES_POR_ETAPA[args.etapa] | CHAVES_TRANSVERSAL
    if args.etapa != "transversal":
        remover |= CHAVES_HERANCA
    removidas = sorted(k for k in estado if k in remover)
    estado_limpo = {k: v for k, v in estado.items() if k not in remover}
    if args.etapa == "design" and estado_limpo.get("spec_missao_gate0"):
        # o D0 consolida a spec por cima de `spec_missao`; para refazer o design, volta à do Gate 0
        estado_limpo["spec_missao"] = estado_limpo["spec_missao_gate0"]
    print(f"🧹 {len(removidas)} chaves removidas para a etapa `{args.etapa}`; {len(estado_limpo)} preservadas.")

    # 4. roda só a etapa, na mesma pasta
    print(f"▶️  Rodando etapa `{args.etapa}` (+ diagnóstico e aprendizado) em {local} …")
    inicio = time.time()
    result = run_orchestrator_pipeline_sync(
        prompt=briefing,
        user_id=conversa.get("user_id"),
        session_id=conversa.get("session_id"),
        stages=[args.etapa],
        initial_state=estado_limpo,
        run_dir=local,
    )
    print(f"⏱️  {time.time() - inicio:.0f}s · status da execução: {result.status}")
    if result.status == "error":
        print(f"❌ {result.error_message}")
        return 2

    # conversa.json: preserva a data original e registra a reexecução
    caminho_conversa = local / "conversa.json"
    if caminho_conversa.exists():
        nova = json.loads(caminho_conversa.read_text(encoding="utf-8"))
        if conversa.get("created_at"):
            nova["created_at"] = conversa["created_at"]
        # o runner regrava conversa.json do zero: o histórico de reexecuções anteriores vem do arquivo antigo
        nova["reexecucoes"] = list(conversa.get("reexecucoes") or []) + [{
            "etapa": args.etapa, "quando": time.strftime("%d/%m/%Y %H:%M:%S"), "status": result.status,
            "chaves_removidas": removidas,
        }]
        nova["messages"] = list(conversa.get("messages") or nova.get("messages") or []) + [{
            "role": "assistant",
            "content": f"🔁 **Etapa `{args.etapa}` reexecutada em {time.strftime('%d/%m/%Y %H:%M')}** sobre o estado salvo, "
                       + ("só diagnóstico e aprendizado, etapas inalteradas" if args.etapa == "transversal"
                          else f"com produto{' e design' if args.etapa == 'dev' else ''} inalterados")
                       + f". Status: {result.status}.",
        }]
        caminho_conversa.write_text(json.dumps(nova, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    print("\n📊 Gates após a reexecução:")
    for k in STATUS_KEYS:
        if k in result.state:
            print(f"   {k:28} {result.state[k]}")

    # 5. de volta ao bucket
    if destino and not args.sem_upload:
        print(f"\n⬆️  Subindo {local} → {destino}")
        _gcloud("rsync", "-r", "--exclude", r"^\.adk_artifacts", str(local), destino)
    elif destino:
        print(f"\n⏸️  Upload desligado. Para publicar: gcloud storage rsync -r {local} {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
