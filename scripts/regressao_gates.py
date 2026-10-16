#!/usr/bin/env python3
"""scripts/regressao_gates.py

Reaplica todos os gates determinísticos (sem chamadas de LLM) a cada estado.json
do acervo dourado e gera ou compara contra a linha de base (tests/acervo/linha-de-base.json).

Uso:
    python scripts/regressao_gates.py --gravar-linha-de-base
    python scripts/regressao_gates.py --comparar
    python scripts/regressao_gates.py [missao]

Em modo --comparar:
    Compara o resultado atual contra a linha de base congelada.
    Se algum veredito mudar (status ou códigos de achados), lista o diff detalhado
    e encerra com código de saída 1 (reprovando o CI).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Garantir imports do projeto
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# Garantir BASE_PLATAFORMA_DIR apontando para a base congelada de testes (fixtures/base-plataforma)
# para garantir reproduzibilidade idêntica no CI e entre CLI e pytest.
def _garantir_base_plataforma() -> None:
    if not os.environ.get("BASE_PLATAFORMA_DIR"):
        candidatos = [
            RAIZ / "fixtures" / "base-plataforma",
            RAIZ / "output" / "base-plataforma",
        ]
        for c in candidatos:
            if c.exists() and (c / "design-system" / "atual.json").exists():
                os.environ["BASE_PLATAFORMA_DIR"] = str(c)
                break

_garantir_base_plataforma()

from tools import (
    bncc, contrato_produto, evidencia, kpis, rastro, consistencia,
    conteudo, conteudo_aprovado, cobertura_design, prd_codavel,
    afirmacoes, telas, prototipo, mecanica, rastreabilidade, componentes_ds
)
from pipeline.artifacts import caminhos_de_artefato


def _extrair_status_e_codigos(res: Any) -> Dict[str, Any]:
    """Padroniza a resposta de um gate em {'status': str, 'codigos': List[str]}."""
    if not isinstance(res, dict):
        return {"status": "desconhecido", "codigos": []}
    st = res.get("status", "desconhecido")
    achados = res.get("achados", []) or []
    codigos = sorted({
        str(a.get("codigo") or a.get("tipo") or a.get("regra") or "?")
        for a in achados
        if isinstance(a, dict)
    })
    return {"status": st, "codigos": codigos}


def reavaliar_estado(state: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Calcula todos os gates determinísticos aplicáveis a um estado.json."""
    spec = str(state.get("spec_missao", "") or "")
    prd = str(state.get("prd_final", "") or "")
    handoff = str(state.get("handoff_dev", "") or "")
    one_pager = str(state.get("one_pager", "") or "")
    one_pager_po = str(state.get("one_pager_po", "") or "")
    one_pager_res = str(state.get("one_pager_resumido", "") or "")
    one_pager_ped = str(state.get("one_pager_pedagogico", "") or "")
    banco = str(state.get("banco_conteudo", "") or "")
    brief_assets = str(state.get("brief_assets", "") or "")
    briefing = str(state.get("briefing", "") or "")
    nucleo = str(state.get("nucleo_narrativo", "") or "")
    copy_rev = str(state.get("copy_strings_revisada", "") or "")
    caa = str(state.get("camada_caa", "") or "")
    proto_arq = str(state.get("prototipo_arquivo", "") or "")
    jornada = str(state.get("jornada_telas", "") or "")
    qa_rep = str(state.get("qa_entregaveis_report", "") or "")
    stitch_links = str(state.get("stitch_links", "") or "")

    gates: Dict[str, Dict[str, Any]] = {}

    # === PRODUTO ===
    if spec:
        gates["bncc_status"] = _extrair_status_e_codigos(bncc.validar_spec(spec))
        gates["manifesto_status"] = _extrair_status_e_codigos(
            rastro.validar_manifesto(spec, briefing=briefing, one_pager_po=one_pager_po)
        )
        gates["evidencia_status"] = _extrair_status_e_codigos(evidencia.validar(spec))
        gates["perguntas_status"] = _extrair_status_e_codigos(kpis.validar_9f(spec))
        spec_g0 = state.get("spec_missao_gate0") or spec
        gates["rastro_spec_status"] = _extrair_status_e_codigos(
            rastro.varrer_lacunas(rastro.FONTES_SPEC, {**state, "spec_missao": spec_g0}, etapa_corrente="produto")
        )
        r_cas = conteudo_aprovado.validar_spec(spec, one_pager)
        conflitos = consistencia.glossario_contra_o_aprovado(spec, one_pager)
        if conflitos:
            r_cas = {**r_cas, "status": "bloqueado", "achados": r_cas["achados"] + conflitos}
        gates["conteudo_aprovado_spec_status"] = _extrair_status_e_codigos(r_cas)

    if one_pager:
        gates["contrato_produto_status"] = _extrair_status_e_codigos(
            contrato_produto.validar_one_pager(one_pager, nucleo=nucleo, briefing=briefing, one_pager_po=one_pager_po)
        )
        # os comitês pedagógicos (15/10/2026): o §12a e a conta da virada conferidos sobre o one-pager
        gates["evidencia_one_pager_status"] = _extrair_status_e_codigos(evidencia.conferir_one_pager(one_pager))
        gates["mecanica_one_pager_status"] = _extrair_status_e_codigos(mecanica.validar(one_pager))
    if nucleo:
        gates["mecanica_status"] = _extrair_status_e_codigos(mecanica.validar(nucleo))
    if one_pager_res:
        gates["conteudo_aprovado_resumido_status"] = _extrair_status_e_codigos(
            conteudo_aprovado.validar_resumido(one_pager_res, spec, one_pager)
        )
    if one_pager_ped:
        gates["conteudo_aprovado_pedagogico_status"] = _extrair_status_e_codigos(
            conteudo_aprovado.validar_pedagogico(one_pager_ped, spec, one_pager, caminhos_de_artefato())
        )

    # === DESIGN ===
    if proto_arq or jornada:
        gates["rastro_design_status"] = _extrair_status_e_codigos(
            rastro.varrer_lacunas(rastro.FONTES_DESIGN, state, etapa_corrente="design")
        )
        r_cons = consistencia.validar_estado(state)
        r_cons["achados"] += conteudo_aprovado.validar_copy(copy_rev, one_pager)
        r_cons["achados"] += conteudo_aprovado.validar_literais_design(caa, proto_arq, one_pager)
        if any(a.get("severidade") == "bloqueio" for a in r_cons.get("achados", [])):
            r_cons["status"] = "bloqueado"
        elif r_cons.get("achados") and r_cons.get("status") == "aprovado":
            r_cons["status"] = "amarelo"
        gates["consistencia_status"] = _extrair_status_e_codigos(r_cons)

        decs = sorted(set(re.findall(r"\bE\d-(?:ALU|PROF|SIS)-\d{2}\b", jornada)))
        r_pl = prototipo.validar(proto_arq, decs)
        r_pl["achados"] += componentes_ds.validar(str(state.get("wireframes_cobertura", "") or ""), spec)
        if any(a.get("severidade") == "bloqueio" for a in r_pl.get("achados", [])):
            r_pl["status"] = "bloqueado"
        elif r_pl.get("achados") and r_pl.get("status") == "aprovado":
            r_pl["status"] = "amarelo"
        gates["prototipo_lint_status"] = _extrair_status_e_codigos(r_pl)

        gates["cobertura_telas_status"] = _extrair_status_e_codigos(telas.cobertura(state))
        if qa_rep:
            gates["qa_afirmacoes_status"] = _extrair_status_e_codigos(
                afirmacoes.conferir_qa(qa_rep, stitch_links, jornada, proto_arq)
            )
        gates["rastreabilidade_status"] = _extrair_status_e_codigos(rastreabilidade.matriz(state))

    # === DEV ===
    if prd or handoff:
        if handoff:
            gates["telemetria_status"] = _extrair_status_e_codigos(rastro.validar_telemetria(handoff))
        if banco:
            r_cnt = conteudo.validar(brief_assets, banco, spec)
            r_cnt["achados"] += consistencia.validar(
                spec, {"banco de conteúdo": banco}, exigir_glossario=False, etapa="dev", aprovado=one_pager
            )["achados"]
            r_cnt["achados"] += conteudo_aprovado.validar_banco(banco, one_pager)
            r_cnt["achados"] += [{**a, "etapa": "dev"} for a in prd_codavel.validar_intencoes(banco, spec)]
            if any(a.get("severidade") == "bloqueio" for a in r_cnt.get("achados", [])):
                r_cnt["status"] = "bloqueado"
            elif r_cnt.get("achados") and r_cnt.get("status") == "aprovado":
                r_cnt["status"] = "amarelo"
            gates["conteudo_status"] = _extrair_status_e_codigos(r_cnt)

        if prd:
            r_lac = rastro.varrer_lacunas(rastro.FONTES_DEV, state)
            r_c_prd = rastro.validar_prd(prd, spec=spec, banco=banco, aprovado=one_pager)
            r_cdz = cobertura_design.validar(prd, {**state, "spec_missao": spec})
            r_cod = prd_codavel.validar(prd, spec, banco, handoff=handoff)
            ordem = ("bloqueado", "amarelo", "aprovado")
            r_prd_tot = {
                "status": min((r_lac["status"], r_cdz["status"], r_c_prd["status"], r_cod["status"]), key=ordem.index),
                "achados": list(r_lac["achados"]) + list(r_cdz["achados"]) + list(r_c_prd["achados"]) + list(r_cod["achados"]),
            }
            gates["prd_status"] = _extrair_status_e_codigos(r_prd_tot)
            gates["kpis_status"] = _extrair_status_e_codigos(kpis.validar_kpis(prd, spec, one_pager=one_pager))
            gates["conteudo_aprovado_prd_status"] = _extrair_status_e_codigos(
                conteudo_aprovado.validar_prd(prd, spec, one_pager, caminhos_de_artefato())
            )

        gates["rastro_lacunas_status"] = _extrair_status_e_codigos(
            rastro.varrer_lacunas(rastro.FONTES_DEV, state, etapa_corrente="dev")
        )

    return gates


def avaliar_acervo(acervo_dir: Path) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Lê todas as pastas com estado.json em `acervo_dir` e calcula seus gates."""
    resultados: Dict[str, Dict[str, Dict[str, Any]]] = {}
    pastas = sorted([p for p in acervo_dir.iterdir() if p.is_dir() and (p / "estado.json").exists()])
    for pasta in pastas:
        slug = pasta.name
        arquivo = pasta / "estado.json"
        try:
            state = json.loads(arquivo.read_text(encoding="utf-8"))
            resultados[slug] = reavaliar_estado(state)
        except Exception as e:
            print(f"Erro ao processar {slug}: {e}", file=sys.stderr)
            raise
    return resultados


def comparar_linhas_de_base(
    base: Dict[str, Dict[str, Dict[str, Any]]],
    atual: Dict[str, Dict[str, Dict[str, Any]]]
) -> List[str]:
    """Compara dois conjuntos de resultados e retorna lista de discrepâncias encontradas."""
    diffs: List[str] = []

    missoes_todas = sorted(set(base.keys()) | set(atual.keys()))
    for missao in missoes_todas:
        if missao not in base:
            diffs.append(f"[{missao}] Missão nova presente no acervo atual, ausente na linha de base.")
            continue
        if missao not in atual:
            diffs.append(f"[{missao}] Missão ausente no acervo atual, presente na linha de base.")
            continue

        gates_todos = sorted(set(base[missao].keys()) | set(atual[missao].keys()))
        for gate in gates_todos:
            if gate not in base[missao]:
                diffs.append(f"[{missao}] Gate novo '{gate}' calculado (não estava na linha de base).")
                continue
            if gate not in atual[missao]:
                diffs.append(f"[{missao}] Gate '{gate}' não calculado na execução atual.")
                continue

            gb = base[missao][gate]
            ga = atual[missao][gate]
            st_b = gb.get("status")
            st_a = ga.get("status")
            cod_b = gb.get("codigos", [])
            cod_a = ga.get("codigos", [])

            if st_b != st_a:
                diffs.append(
                    f"[{missao}] {gate}: status mudou de '{st_b}' para '{st_a}' "
                    f"(códigos base: {cod_b} -> códigos atuais: {cod_a})"
                )
            elif cod_b != cod_a:
                diffs.append(
                    f"[{missao}] {gate}: códigos de achados mudaram "
                    f"(base: {cod_b} -> atual: {cod_a})"
                )

    return diffs


def main() -> int:
    parser = argparse.ArgumentParser(description="Regressão de gates determinísticos sobre o acervo dourado.")
    parser.add_argument("--acervo-dir", type=Path, default=RAIZ / "tests" / "acervo",
                        help="Diretório contendo as pastas das missões com estado.json")
    parser.add_argument("--linha-de-base", type=Path, default=RAIZ / "tests" / "acervo" / "linha-de-base.json",
                        help="Arquivo JSON da linha de base")
    parser.add_argument("--gravar-linha-de-base", action="store_true",
                        help="Grava o resultado atual como nova linha de base")
    parser.add_argument("--comparar", action="store_true",
                        help="Compara o resultado atual contra a linha de base gravada e falha se houver mudança")
    parser.add_argument("missao", nargs="?", default=None,
                        help="Filtrar por slug específico de missão")

    args = parser.parse_args()

    # Garantir BASE_PLATAFORMA_DIR apontando para base válida
    if not os.environ.get("BASE_PLATAFORMA_DIR"):
        candidatos = [
            RAIZ / "output" / "base-plataforma",
            RAIZ / "fixtures" / "base-plataforma",
        ]
        for c in candidatos:
            if c.exists() and (c / "design-system" / "atual.json").exists():
                os.environ["BASE_PLATAFORMA_DIR"] = str(c)
                break

    print(f"📂 Acervo: {args.acervo_dir}")
    print(f"🏛️ Base plataforma: {os.environ.get('BASE_PLATAFORMA_DIR', '(padrão do código)')}")

    atual = avaliar_acervo(args.acervo_dir)
    print(f"✅ {len(atual)} missões avaliadas com sucesso.")

    if args.missao:
        if args.missao not in atual:
            print(f"❌ Missão '{args.missao}' não encontrada no acervo.", file=sys.stderr)
            return 1
        print(f"\nResultados para {args.missao}:")
        for g, val in sorted(atual[args.missao].items()):
            print(f"  {g:<35}: {val['status']} {val['codigos']}")
        return 0

    if args.gravar_linha_de_base:
        args.linha_de_base.parent.mkdir(parents=True, exist_ok=True)
        args.linha_de_base.write_text(json.dumps(atual, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"💾 Linha de base gravada com sucesso em: {args.linha_de_base}")
        return 0

    # Modo comparar (padrão se a linha de base existir, ou explicitado com --comparar)
    if args.comparar or args.linha_de_base.exists():
        if not args.linha_de_base.exists():
            print(f"❌ Linha de base não encontrada em {args.linha_de_base}. Execute com --gravar-linha-de-base primeiro.", file=sys.stderr)
            return 1

        base = json.loads(args.linha_de_base.read_text(encoding="utf-8"))
        diffs = comparar_linhas_de_base(base, atual)
        if diffs:
            print(f"\n❌ REGRESSÃO DETECTADA! {len(diffs)} divergência(s) encontrada(s):")
            for d in diffs:
                print(f"  - {d}")
            print("\nSe as mudanças foram deliberadas e explicadas, atualize a linha de base com:")
            print("  python scripts/regressao_gates.py --gravar-linha-de-base")
            return 1
        else:
            print(f"🟢 NENHUMA REGRESSÃO DETECTADA: todos os vereditos e códigos são 100% idênticos à linha de base.")
            return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
