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

# O classificador de sentido (C7), como na regressão: lê o cache da própria sessão (`classificador_sentido` no estado,
# gravado pela esteira) e o versionado de teste, sem chamar o modelo. Fora deles, «nao_sei» — o gate de hipótese fica
# só com a prova em código (`tools/montagem._leitura_sem_classificador`). `CLASSIFICADOR_SENTIDO=ligado` chama o Gemini;
# o custo não é gravado, porque o script nunca escreve na sessão. Revisão do PR #85 (25/10/2026): sem isto, cada
# validador chamava o modelo ao vivo, sem sessão, sem cache e sem limite por gate.
os.environ.setdefault("CLASSIFICADOR_SENTIDO", "so_cache")
os.environ.setdefault("CLASSIFICADOR_CACHE_FIXO",
                      str(Path(__file__).resolve().parent.parent / "fixtures" / "classificador-cache.json"))

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

    novos["manifesto_status"] = rastro.validar_manifesto(spec, briefing=state.get("briefing", "") or "",
                                                         one_pager_po=state.get("one_pager_po", "") or "",
                                                         one_pager=one_pager,
                                                         decisoes_do_po=state.get("decisoes_do_po") or [])
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
    cons_prd = rastro.validar_prd(prd, spec=spec, banco=state.get("banco_conteudo", "") or "", aprovado=one_pager)
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

        ped_remontado = pedagogico.montar(str(state["one_pager_pedagogico"]), state)
        state = {**state, "one_pager_pedagogico": ped_remontado}
        novos["montagem_pedagogico_status"] = pedagogico.validar(state)

    # PR 7: os textos-chave na copy e o fluxo × bloco 2 da spec
    from tools import afirmacoes, arestas, consistencia, conteudo_aprovado, rastreabilidade, telas, textos_chave
    from pipeline.artifacts import caminhos_de_artefato

    spec_c = state.get("spec_missao_consolidada") or spec
    if spec_gate0 and one_pager:
        r_cas = conteudo_aprovado.validar_spec(spec_gate0, one_pager)
        conflitos = consistencia.glossario_contra_o_aprovado(spec_gate0, one_pager)
        if conflitos:
            r_cas = {**r_cas, "status": "bloqueado", "achados": list(r_cas.get("achados", [])) + conflitos}
        novos["conteudo_aprovado_spec_status"] = r_cas
    if spec_c and one_pager and state.get("spec_missao_consolidada"):
        novos["conteudo_aprovado_spec_design_status"] = conteudo_aprovado.validar_spec(spec_c, one_pager)
    if state.get("one_pager_resumido") and one_pager:
        novos["conteudo_aprovado_resumido_status"] = conteudo_aprovado.validar_resumido(
            str(state["one_pager_resumido"]), spec_gate0, one_pager
        )
    if state.get("one_pager_pedagogico") and one_pager:
        novos["conteudo_aprovado_pedagogico_status"] = conteudo_aprovado.validar_pedagogico(
            str(state["one_pager_pedagogico"]), spec_c, one_pager, caminhos_de_artefato()
        )
    if prd and one_pager:
        novos["conteudo_aprovado_prd_status"] = conteudo_aprovado.validar_prd(
            prd, spec_c, one_pager, caminhos_de_artefato()
        )
    if state.get("prototipo_html_arquivo") or state.get("jornada_telas"):
        r_cons = consistencia.validar_estado(state)
        r_cons["achados"] = list(r_cons.get("achados", [])) + conteudo_aprovado.validar_copy(
            str(state.get("copy_strings_revisada") or ""), one_pager
        ) + conteudo_aprovado.validar_literais_design(
            str(state.get("camada_caa") or ""), str(state.get("prototipo_html_arquivo") or ""), one_pager
        )
        if any(a.get("severidade") == "bloqueio" for a in r_cons["achados"]):
            r_cons["status"] = "bloqueado"
        elif r_cons["achados"] and r_cons.get("status") == "aprovado":
            r_cons["status"] = "amarelo"
        novos["consistencia_status"] = r_cons
        novos["cobertura_telas_status"] = telas.cobertura(state)
        novos["rastreabilidade_status"] = rastreabilidade.matriz(
            state, colunas_veredito=("spec", "jornada", "fluxo", "copy", "telas", "prototipo", "stitch")
        )
    if handoff or prd or state.get("banco_conteudo"):
        novos["rastreabilidade_dev_status"] = rastreabilidade.matriz(state, colunas_veredito=("handoff", "banco", "prd"))
    qa_texto = str(state.get("qa_design_report") or state.get("qa_entregaveis_report") or "")
    if qa_texto:
        qa_base = qa_texto.split("\n\n## Afirmações conferidas em código (A089)")[0]
        novos["qa_afirmacoes_status"] = afirmacoes.conferir_qa(
            qa_base,
            str(state.get("stitch_links") or ""),
            str(state.get("jornada_telas") or ""),
            str(state.get("prototipo_html_arquivo") or ""),
        )

    if state.get("copy_strings_revisada"):
        novos["textos_chave_status"] = textos_chave.conferir_copy(str(state["copy_strings_revisada"]),
                                                                  textos_chave.da_sessao(state))
    if state.get("fluxo_arestas") or state.get("jornada_telas"):
        novos["arestas_status"] = arestas.validar(state)
    # PR 8: o split do D9 refeito sobre a resposta gravada — bloco 14 × bloco 0, jogo na ficha, texto fora do bloco 14
    if state.get("ambiente_simulado"):
        from tools import ambiente

        novos["ambiente_status"] = ambiente.reavaliar_d9(state)

    from tools.decisoes import ha_registro_do_po

    novos["contrato_produto_status"] = contrato_produto.validar_one_pager(
        one_pager, state.get("nucleo_narrativo", "") or "", state.get("briefing", "") or "",
        one_pager_po=state.get("one_pager_po", "") or "",
        decisoes_do_po=state.get("decisoes_do_po") or [],
        registro_do_po=ha_registro_do_po(state),
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
    from tools import classificador

    # uma sessão para a recomputação inteira: o cache da sessão gravada responde; com `ligado`, o limite de chamadas
    # (`classificador.LIMITE_POR_GATE`) vale para a soma dos validadores
    with classificador.sessao(state, "reavaliar_gates"):
        novos = recomputar(state)
    for chave, resultado in novos.items():
        copia[chave] = resultado["status"]
        copia[f"{chave}_envelope"] = {"status": resultado["status"], "achados": resultado.get("achados", [])}
    if "contrato_produto_status" in novos:
        copia["contrato_produto_report"] = contrato_produto.relatorio_markdown(
            novos["contrato_produto_status"],
            str(state.get("slug_missao") or ""),
        )
    # Se qa_afirmacoes_status e rastro_design_status deixaram de bloquear e design_status só carregava achados deles
    if (copia.get("qa_afirmacoes_status") != "bloqueado"
            and copia.get("rastro_design_status") != "bloqueado"
            and copia.get("design_status") == "bloqueado"):
        env_d = copia.get("design_status_envelope") or {}
        ach_d = [a for a in env_d.get("achados") or [] if a.get("codigo") not in ("arquivo-inexistente", "d0-orfao")]
        if not ach_d:
            copia["design_status"] = "aprovado"
            copia["design_status_envelope"] = {"status": "aprovado", "achados": []}
    # Se nenhum portão continua bloqueado/devolvido após a recomputação, limpa degradacoes herdadas de gates agora verdes/amarelos
    if not any(copia.get(g["status"]) in ("bloqueado", "devolvido") for g in GATES):
        copia["degradacoes"] = []
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
