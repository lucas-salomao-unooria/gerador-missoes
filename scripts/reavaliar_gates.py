#!/usr/bin/env python3
"""Recomputa os gates determinísticos sobre sessões já geradas, sem alterá-las.

Por que existe: `rerodar_etapa.py --etapa transversal` refaz o diagnóstico sobre os
`*_status` **já gravados** (`pipeline/reexecucao.py:243-245`) — ele não reexecuta os
validadores. Para medir o efeito de uma mudança em `tools/rastro.py` (ou em qualquer
validador) sobre as sessões do bucket é preciso recomputar do zero a partir dos
artefatos, e comparar o veredito antes × depois.

Garantia de segurança: o bucket é lido e **nunca** escrito. Uma sessão `gs://` é
copiada para o diretório de trabalho local (scratchpad por padrão) e todo o resto
acontece sobre essa cópia.

Uso:
    python scripts/reavaliar_gates.py gs://entre-redes-dev-adk-artifacts/20260922-181029-exp06ef1b
    python scripts/reavaliar_gates.py --todas gs://entre-redes-dev-adk-artifacts
    python scripts/reavaliar_gates.py output/20260922-144438-exp06ef1b --json matriz.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import bncc, contrato_produto, evidencia, kpis, rastro  # noqa: E402
from tools.diagnostico import GATES, coletar  # noqa: E402

#: As mesmas fontes que o A107 lê — a lista vive em `tools/rastro.py`, sem espelho aqui.
FONTES_LACUNAS: List[Dict[str, str]] = rastro.FONTES_DEV

ICONE = {"aprovado": "🟢", "amarelo": "🟡", "bloqueado": "🔴", "devolvido": "🔴", "—": "·"}


def _scratchpad() -> Path:
    """Diretório de trabalho: o scratchpad da sessão, senão um temporário do projeto."""
    for var in ("CLAUDE_SCRATCHPAD", "SCRATCHPAD"):
        if os.getenv(var):
            return Path(os.environ[var])
    return Path("/tmp") / "reavaliar-gates"


def baixar(origem: str, destino_base: Path) -> Path:
    """Copia uma sessão do bucket para o disco local. Só leitura do lado do bucket."""
    nome = origem.rstrip("/").rsplit("/", 1)[-1]
    destino = destino_base / nome
    destino.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["gcloud", "storage", "rsync", "-r", origem.rstrip("/"), str(destino)],
        check=True,
        capture_output=True,
    )
    return destino


def listar_sessoes(bucket: str) -> List[str]:
    saida = subprocess.run(
        ["gcloud", "storage", "ls", bucket.rstrip("/") + "/"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [
        linha.strip()
        for linha in saida.splitlines()
        if linha.strip().endswith("/") and "-exp" in linha.rsplit("/", 2)[-2]
    ]


def recomputar(state: Dict[str, Any]) -> Dict[str, Any]:
    """Roda os validadores determinísticos sobre os artefatos e devolve os status novos.

    Os gates de LLM não são reexecutados (exigiriam chamada de modelo); o status deles
    é preservado como está, para que a comparação isole o efeito dos determinísticos.
    """
    spec = state.get("spec_missao", "") or ""
    handoff = state.get("handoff_dev", "") or ""
    prd = state.get("prd_final", "") or ""
    one_pager = state.get("one_pager", "") or ""

    novos: Dict[str, Dict[str, Any]] = {}

    novos["manifesto_status"] = rastro.validar_manifesto(spec, briefing=state.get("briefing", "") or "")
    novos["telemetria_status"] = rastro.validar_telemetria(handoff)
    novos["bncc_status"] = bncc.validar_spec(spec)
    novos["rastro_lacunas_status"] = rastro.varrer_lacunas(FONTES_LACUNAS, state, etapa_corrente="dev")
    # O rastro de produto roda sobre a spec do Gate 0, que é a que existia no loop da spec: a
    # `spec_missao` de uma sessão que passou por design já traz o bloco 13 do fechamento de lacunas.
    spec_gate0 = state.get("spec_missao_gate0") or spec
    novos["rastro_spec_status"] = rastro.varrer_lacunas(rastro.FONTES_SPEC, {**state, "spec_missao": spec_gate0},
                                                         etapa_corrente="produto")
    novos["rastro_design_status"] = rastro.varrer_lacunas(rastro.FONTES_DESIGN, state, etapa_corrente="design")

    # `Pendências do PRD` é a pior das duas leituras: marcadores abertos + consistência.
    lac_prd = rastro.varrer_lacunas([{"chave": "prd_final", "rotulo": "PRD", "etapa_padrao": "dev"}], state)
    cons_prd = rastro.validar_prd(prd)
    pior = "bloqueado" if "bloqueado" in (lac_prd["status"], cons_prd["status"]) else (
        "amarelo" if "amarelo" in (lac_prd["status"], cons_prd["status"]) else "aprovado"
    )
    novos["prd_status"] = {
        "status": pior,
        "achados": lac_prd.get("achados", []) + cons_prd.get("achados", []),
    }

    # gates acrescentados pela auditoria de 23/09: coerência pedagógica e KPI ↔ evento ↔ tela
    novos["evidencia_status"] = evidencia.validar(spec)
    novos["kpis_status"] = kpis.validar_kpis(prd, spec)

    # PR 4 do plano «Produto dono do contrato»: handoff e PRD montam, não decidem
    from tools import montagem

    if handoff:
        novos["montagem_handoff_status"] = montagem.validar_handoff(state)
    if prd:
        novos["montagem_prd_status"] = montagem.validar_prd(state)
    # PR 10: o pedagógico fecha o design e monta sobre o contrato
    if state.get("one_pager_pedagogico"):
        from tools import pedagogico

        novos["montagem_pedagogico_status"] = pedagogico.validar(state)

    # PR 7: os textos-chave na copy e o fluxo × bloco 2 da spec
    from tools import arestas, textos_chave

    if state.get("copy_strings_revisada"):
        novos["textos_chave_status"] = textos_chave.conferir_copy(str(state["copy_strings_revisada"]),
                                                                  textos_chave.da_sessao(state))
    if state.get("fluxo_arestas"):
        novos["arestas_status"] = arestas.validar(state)

    novos["contrato_produto_status"] = contrato_produto.validar_one_pager(
        one_pager, state.get("nucleo_narrativo", "") or "", state.get("briefing", "") or "",
        decisoes_do_po=state.get("decisoes_do_po") or [],
    )
    return novos


def matriz_de(state: Dict[str, Any]) -> Dict[str, str]:
    return {g["status"]: state.get(g["status"], "—") for g in GATES}


def avaliar(pasta: Path) -> Optional[Dict[str, Any]]:
    caminho = pasta / "estado.json"
    if not caminho.exists():
        return None
    state = json.loads(caminho.read_text(encoding="utf-8"))

    antes = matriz_de(state)
    dossie_antes = coletar(state)

    copia = dict(state)
    novos = recomputar(state)
    for chave, resultado in novos.items():
        copia[chave] = resultado["status"]
        copia[f"{chave}_envelope"] = {"status": resultado["status"], "achados": resultado.get("achados", [])}
    depois = matriz_de(copia)
    dossie_depois = coletar(copia)

    achados_novos: List[Dict[str, Any]] = []
    for chave, resultado in novos.items():
        for achado in resultado.get("achados", []):
            # Achado de lacuna não tem `codigo` — identifica-se pelo tipo de marcador
            # e pela etapa do dono, que é o que decide se bloqueia.
            codigo = achado.get("codigo") or f"lacuna:{achado.get('tipo', '?')}:{achado.get('etapa', '?')}"
            achados_novos.append(
                {
                    "gate": chave,
                    "codigo": codigo,
                    "severidade": achado.get("severidade"),
                    "etapa": achado.get("etapa"),
                    "resumo": achado.get("resumo") or achado.get("trecho", "")[:120],
                }
            )

    return {
        "sessao": pasta.name,
        "missao": state.get("missao") or state.get("slug") or "",
        "antes": antes,
        "depois": depois,
        "veredito_antes": dossie_antes.get("veredito"),
        "veredito_depois": dossie_depois.get("veredito"),
        "achados_antes": len(dossie_antes.get("achados", [])),
        "achados_depois": len(achados_novos),
        "achados": achados_novos,
    }


def imprimir(resultados: List[Dict[str, Any]]) -> None:
    rotulos = {g["status"]: g["rotulo"] for g in GATES}
    chaves = [g["status"] for g in GATES]

    print("=" * 110)
    print("MATRIZ sessão × gate — antes → depois (só gates determinísticos recomputados)")
    print("=" * 110)
    larg = max(len(r["sessao"]) for r in resultados) if resultados else 30
    cab = "  ".join(f"{rotulos[c][:14]:<14}" for c in chaves)
    print(f"{'sessão':<{larg}}  {cab}  veredito")
    for r in resultados:
        celulas = []
        for c in chaves:
            a, d = r["antes"].get(c, "—"), r["depois"].get(c, "—")
            marca = f"{ICONE.get(a, '?')}→{ICONE.get(d, '?')}" if a != d else f"  {ICONE.get(a, '?')}   "
            celulas.append(f"{marca:<14}")
        v = f"{r['veredito_antes']} → {r['veredito_depois']}"
        print(f"{r['sessao']:<{larg}}  {'  '.join(celulas)}  {v}")

    print("-" * 110)
    mudancas = [
        (r["sessao"], rotulos[c], r["antes"][c], r["depois"][c])
        for r in resultados
        for c in chaves
        if r["antes"].get(c) != r["depois"].get(c)
    ]
    print(f"células alteradas: {len(mudancas)}")
    for sessao, gate, a, d in mudancas:
        print(f"   {sessao}  {gate}: {a} → {d}")

    por_codigo: Dict[str, int] = {}
    for r in resultados:
        for a in r["achados"]:
            por_codigo[a.get("codigo") or "—"] = por_codigo.get(a.get("codigo") or "—", 0) + 1
    print("-" * 110)
    total = sum(por_codigo.values())
    print(f"achados determinísticos recomputados: {total}")
    for codigo, n in sorted(por_codigo.items(), key=lambda kv: -kv[1]):
        print(f"   {n:>3}  {codigo}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("origem", help="pasta local, gs://…/<sessao> ou gs://<bucket> com --todas")
    p.add_argument("--todas", action="store_true", help="varre todas as sessões do bucket")
    p.add_argument("--trabalho", default=None, help="onde baixar (padrão: scratchpad)")
    p.add_argument("--json", default=None, help="grava o resultado bruto neste arquivo")
    args = p.parse_args()

    base = Path(args.trabalho) if args.trabalho else _scratchpad() / "reavaliar-gates"
    base.mkdir(parents=True, exist_ok=True)

    if args.todas:
        origens = listar_sessoes(args.origem)
        print(f"{len(origens)} sessões no bucket", file=sys.stderr)
    else:
        origens = [args.origem]

    resultados = []
    for origem in origens:
        pasta = baixar(origem, base) if origem.startswith("gs://") else Path(origem)
        r = avaliar(pasta)
        if r:
            resultados.append(r)
        else:
            print(f"   (sem estado.json: {pasta.name})", file=sys.stderr)

    resultados.sort(key=lambda r: r["sessao"])
    imprimir(resultados)

    if args.json:
        Path(args.json).write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nbruto em {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
