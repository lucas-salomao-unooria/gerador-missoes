"""Consolidação determinística da banca de dev — o veredito vira contagem, não redação.

O consolidador era um `LlmAgent` cuja própria descrição prometia "veredito determinístico
🟢/🟡/🔴". Em 14 execuções ele leu 122 achados e aprovou 14 vezes — e a lista de bloqueantes
que ele carregava no prompt omitia `DES-14` (visão do professor), que os arquivos de critério
declaram bloqueante desde 22/09/2026. Ou seja: a visão do professor podia faltar inteira e a
banca liberava, porque o juiz não sabia que aquele critério travava.

Aqui a lista de bloqueantes é lida dos **próprios arquivos de critérios**, que são a fonte da
verdade. Não há segunda cópia para divergir.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from prompts import REFERENCES_DIR

AGENTE = "banca-consolidada"

#: `## DAD-07 [BLOQUEANTE] — Título` · o `[BLOQUEANTE para X]` do PED-01 também conta.
_RE_BLOQUEANTE = re.compile(r"^##\s+([A-Z]{3,4}-\d{2})\s*\[BLOQUEANTE", re.MULTILINE)
_RE_CRITERIO = re.compile(r"^##\s+([A-Z]{3,4}-\d{2})\b", re.MULTILINE)

#: Achados que a esteira não pode fechar porque pedem ato no monorepo da plataforma. Continuam
#: no relatório como pendência declarada, mas não rebaixam o veredito: o PRD que os nomeia é o
#: entregável, e cobrar deles a execução é cobrar de quem não tem o repositório.
FORA_DA_ESTEIRA = frozenset({"TEC-07", "TEC-08", "TEC-09", "TEC-10", "TEC-11", "DES-06"})

#: Critérios que a banca não cobra numa posição porque os modelos dos autores dela não os pedem — continuam cobrados nas
#: posições seguintes, onde o documento que os traz existe. No fim de produto, `014`, `045` e `046` não pedem a leitura
#: do gestor (PED-12), o plano de playtest (PED-15) nem a classificação medida × cosmético item a item (PED-03): no
#: levantamento de 24/10/2026 a banca de produto os cobrou em 5, 4 e 3 sessões, o autor da spec não tinha como atender,
#: e na 317df247 o PO copiou os três num refazer. A entrada do dev e o dev os avaliam sobre o handoff, o banco e o PRD.
FORA_DA_POSICAO: Dict[str, frozenset] = {"produto": frozenset({"PED-03", "PED-12", "PED-15"})}

_ORDEM = {"bloqueado": 0, "amarelo": 1, "aprovado": 2}

#: Onde a banca roda e o que ela pode fazer ali (decisão do usuário, 08/10/2026). Os mesmos critérios e o mesmo
#: modelo nas quatro posições; muda o escopo, que um agente determinístico grava em `escopo_banca` logo antes:
#: - fim de produto e fim de design: antes do parecer, e o achado volta ao autor da própria etapa;
#: - entrada do dev: segunda verificação de produto e design já aprovados, com a visão cruzada que nenhuma etapa
#:   tem sozinha. Não reescreve nada: bloqueio para o dev antes de qualquer agente de dev rodar;
#: - dev: dados/LGPD e técnica, depois do handoff, consertando só documento de dev.
KEY_ESCOPO = "escopo_banca"
ESCOPOS: Dict[str, str] = {
    "produto": (
        "Você avalia no **fim da etapa de produto**, antes do parecer do PO. O insumo que existe é a **spec**, e o "
        "**conteúdo aprovado** traz as seções literais do one-pager: o achado que mais importa aqui é a spec dizendo "
        "outra coisa que o one-pager. Jornada, fluxo, copy, telas, handoff, brief e banco **ainda não existem**: "
        "vêm vazios, e isso **não é falha** — não acuse ausência deles. Avalie os critérios que a spec decide; o que só "
        "se julga em tela ou no handoff é ➖ N/A (avaliado no design ou no dev). Os modelos de produto não pedem a "
        "leitura do gestor (PED-12), o plano de validação pedagógica com playtest (PED-15) nem a classificação medida × "
        "cosmético item a item (PED-03): aqui eles são ➖ N/A, avaliados na entrada do dev e no dev. Todo achado volta "
        "ao autor da spec, que corrige na próxima rodada: `agente_responsavel` é `spec-missao` — ou `produto`, quando a "
        "falha está numa decisão do one-pager que a spec só traduziu."
    ),
    "design": (
        "Você avalia no **fim da etapa de design**, antes do parecer de design. Existem a spec consolidada e os "
        "documentos de design (jornada, fluxo, copy revisada, CAA, telas, protótipo). Handoff, brief de assets e "
        "banco **ainda não existem**: vêm vazios, e isso **não é falha**. Se você é a dimensão de produto, avalie só "
        "o que se realiza em tela — PROD-04 (o fluxo realiza o contrato de estados), PROD-07 (o momento de conclusão "
        "tem tela), PROD-12 (a condução do debate está nas telas e na copy do professor), PROD-13 (cada modo de erro "
        "tem tela, na ficção) — e marque os demais ➖ N/A (avaliados no fim de produto). DES-10: o inventário de "
        "assets é o da jornada e das telas. Todo achado vira ticket para o dono refazer antes do parecer: além dos "
        "nomes da lista, `agente_responsavel` aceita aqui `caa`, `prototipo`, `brief-oficio`, `fecha-lacunas` e "
        "`ambiente-simulado`."
    ),
    "entrada": (
        "Você avalia na **entrada do dev**, antes de qualquer agente de dev: é a **segunda verificação** de produto e "
        "design, já aprovados nas etapas deles. Handoff, brief e banco **ainda não existem** (vêm vazios; não é "
        "falha). Avalie todos os seus critérios sobre a spec e o design aprovados e, além deles, **confira produto e "
        "design juntos** — o que nenhuma etapa vê sozinha: cada estado do contrato da spec tem tela e aresta no fluxo; "
        "o momento de conclusão e a revelação que a spec decide aparecem numa tela; o papel do professor do conteúdo "
        "aprovado tem as telas dele (`E0-PROF-…`) e as strings dele; os textos literais do conteúdo aprovado (Canal B, "
        "debate, aposta) estão na copy como foram aprovados; o que a spec declara ausente não aparece no design. "
        "**Você não manda reescrever nada**: todo bloqueio para o dev e vai, com o dono, para a etapa que o conserta. "
        "Quando reprovar algo que a etapa aprovou, diga no resumo: «passou na etapa, reprova aqui»."
    ),
    "dev": (
        "Você avalia **dentro do dev**, depois do handoff, do brief de assets e do banco de conteúdo. Produto e design "
        "já passaram pela segunda verificação na entrada do dev. Achado seu sobre documento de dev (`handoff-dev`, "
        "`brief-assets`, `banco-conteudo`) é refeito aqui com o seu ticket; achado sobre spec ou design vira pendência "
        "nomeada para a etapa dona — o dev não reescreve produto nem design."
    ),
}

#: Saída de cada dimensão em cada posição → rótulo no relatório.
DIMENSOES: Dict[str, str] = {
    "validacao_produto_narrativa": "A — Produto e narrativa",
    "validacao_design_imersao": "B — Design e imersão",
    "validacao_pedagogia_bncc": "C — Pedagogia e BNCC",
    "validacao_dados_lgpd": "D — Dados, telemetria e LGPD",
    "validacao_tecnica_arquitetura": "E — Técnica e arquitetura",
    "banca_produto_narrativa": "A — Produto e narrativa (fim de produto)",
    "banca_produto_pedagogia": "C — Pedagogia e BNCC (fim de produto)",
    "banca_design_narrativa": "A — Produto realizado em tela (fim de design)",
    "banca_design_imersao": "B — Design e imersão (fim de design)",
    "banca_entrada_narrativa": "A — Produto e narrativa (entrada do dev)",
    "banca_entrada_imersao": "B — Design e imersão (entrada do dev)",
    "banca_entrada_pedagogia": "C — Pedagogia e BNCC (entrada do dev)",
}


def _ids_bloqueio(achados: List[Dict[str, Any]]) -> List[str]:
    saida: List[str] = []
    for a in achados or []:
        if str(a.get("severidade", "")).lower() not in ("bloqueio", "nok", "❌"):
            continue
        m = re.search(r"[A-Z]{3,4}-\d{2}", str(a.get("codigo") or a.get("id") or "").upper())
        if m and m.group(0) not in saida:
            saida.append(m.group(0))
    return saida


def divergencias_com_etapas(resultado: Dict[str, Any], etapas: Dict[str, Optional[Dict[str, Any]]]) -> List[str]:
    """Critérios que bloqueiam na entrada do dev e que nenhuma etapa bloqueou.

    É o sinal que a segunda verificação existe para dar: a correção pedida na etapa não pegou, ou o juiz da etapa
    foi enganado. `etapas` = nome da etapa → envelope da banca dela (ausente quando a etapa não rodou a banca).
    O critério que a etapa também bloqueou não é divergência: a etapa foi liberada por exceção, e já se sabia.

    A etapa que não cobra o critério (`FORA_DA_POSICAO`) não o deixou passar — não o avaliou: o PED-12 que reprova na
    entrada do dev saía «passou no fim de produto», como se o juiz de produto tivesse sido enganado (revisão do PR #80,
    24/10/2026). Ela sai da frase, com a nota de que ali o critério não é avaliado; sem etapa que o avalie, não há o
    que comparar.
    """
    rodaram = {nome: env for nome, env in etapas.items() if env}
    if not rodaram:
        return []
    bloqueados_nas_etapas = {i for env in rodaram.values() for i in _ids_bloqueio(env.get("achados") or [])}
    saida: List[str] = []
    for c in _ids_bloqueio(resultado.get("achados") or []):
        if c in bloqueados_nas_etapas:
            continue
        avaliaram = [nome for nome in rodaram if c not in FORA_DA_POSICAO.get(nome, frozenset())]
        if not avaliaram:
            continue
        nao = [nome for nome in rodaram if nome not in avaliaram]
        saida.append(f"`{c}` passou no fim de {' e de '.join(avaliaram)} e reprova aqui."
                     + (f" No fim de {' e de '.join(nao)} ele não é avaliado." if nao else ""))
    return saida


def bloqueantes() -> Dict[str, List[str]]:
    """IDs bloqueantes por arquivo de dimensão, lidos da fonte."""
    fora: Dict[str, List[str]] = {}
    for caminho in sorted((REFERENCES_DIR / "criterios-dev").glob("*.md")):
        fora[caminho.stem] = _RE_BLOQUEANTE.findall(caminho.read_text(encoding="utf-8"))
    return fora


def todos_bloqueantes() -> frozenset:
    return frozenset(i for ids in bloqueantes().values() for i in ids)


def _id(a: Dict[str, Any]) -> str:
    bruto = str(a.get("codigo") or a.get("id") or a.get("criterio") or "")
    m = re.search(r"[A-Z]{3,4}-\d{2}", bruto.upper())
    return m.group(0) if m else ""


#: O tema de cada critério de `FORA_DA_POSICAO`: o achado só sai da posição quando fala dele. Na exp01em1b (e89e91b3) o
#: juiz rotulou de PED-12 um achado sobre o DDL da missão (colunas `score_coXX` fora do módulo de evidências), que não é
#: a leitura do gestor e continua contando.
TEMA_DO_CRITERIO: Dict[str, "re.Pattern[str]"] = {
    "PED-03": re.compile(r"cosm[ée]tic|gabarito|medida|num[ée]ric", re.IGNORECASE),
    "PED-12": re.compile(r"gestor|gest[ãa]o|agregad|adulto", re.IGNORECASE),
    "PED-15": re.compile(r"playtest|piloto|valida[çc][ãa]o pedag[óo]gica|usabilidade|em papel", re.IGNORECASE),
}


def _de_outra_posicao(achado: Dict[str, Any], fora: frozenset) -> bool:
    """O critério do achado não é cobrado nesta posição, e o achado é mesmo sobre ele."""
    ident = _id(achado)
    tema = TEMA_DO_CRITERIO.get(ident)
    return ident in fora and (tema is None or bool(tema.search(str(achado.get("resumo") or ""))))


def _posicao(chave: str) -> str:
    """A posição da banca pela chave de saída da dimensão (`banca_produto_pedagogia` → `produto`); a do dev não tem
    prefixo (`validacao_*`)."""
    m = re.match(r"banca_(produto|design|entrada)_", chave or "")
    return m.group(1) if m else "dev"


def _status_da_dimensao(envelope: Optional[Dict[str, Any]], travam: frozenset,
                        fora_da_posicao: frozenset = frozenset()) -> tuple:
    """(status, achados relevantes) de uma dimensão. Sem envelope legível = bloqueado.

    O achado de critério que esta posição não cobra (`FORA_DA_POSICAO`) fica no relatório e não conta no status — nem
    na contagem de NOK que o juiz declarou."""
    if not envelope:
        return "bloqueado", [{
            "severidade": "bloqueio", "codigo": "dimensao-ausente",
            "resumo": "A dimensão não devolveu envelope legível: uma resposta que não chegou não é aprovação.",
        }]
    achados = [a for a in (envelope.get("achados") or []) if isinstance(a, dict)]
    contagem = envelope.get("contagem") or {}
    contam = [a for a in achados if not _de_outra_posicao(a, fora_da_posicao)]

    nok = [a for a in achados if str(a.get("severidade", "")).lower() in ("bloqueio", "nok", "❌")]
    nok_travam = [a for a in nok if _id(a) in travam and a in contam]
    nok_fora = [a for a in nok if _id(a) in FORA_DA_ESTEIRA or a not in contam]
    nok_bloqueantes_fora = sum(1 for a in nok if _id(a) in travam and a not in contam)

    if nok_travam or int(contagem.get("nok_bloqueantes", 0) or 0) > nok_bloqueantes_fora:
        return "bloqueado", achados
    if [a for a in nok if a not in nok_fora] or int(contagem.get("nok", 0) or 0) > len(nok_fora):
        return "amarelo", achados
    if any(str(a.get("severidade", "")).lower() in ("atencao", "atenção", "ressalva") for a in contam):
        return "amarelo", achados
    return "aprovado", achados


#: O que a banca avalia, nas quatro posições: a citação de cada NOK é conferida nestes documentos.
DOCUMENTOS_DA_BANCA = ("spec_missao", "anexo_design_spec", "conteudo_aprovado", "jornada_telas", "fluxo_arestas", "copy_strings_revisada",
                       "wireframes_cobertura", "brief_oficio", "camada_caa", "stitch_links", "prototipo_relatorio",
                       "handoff_dev", "brief_assets", "banco_conteudo")


def consolidar(envelopes: Dict[str, Optional[Dict[str, Any]]], documentos: str = "") -> Dict[str, Any]:
    """Veredito global = o pior das cinco dimensões. Dimensão ausente bloqueia.

    Com `documentos`, a citação de cada NOK é conferida (`tools/citacoes.py`): a que não existe rebaixa o achado, e a
    contagem que o juiz declarou deixa de valer para aquela dimensão — o veredito sai dos achados que sobraram.
    """
    travam = todos_bloqueantes()
    por_dimensao: Dict[str, Dict[str, Any]] = {}
    todos: List[Dict[str, Any]] = []

    if documentos:
        from tools import citacoes

        for chave, envelope in list(envelopes.items()):
            if envelope and isinstance(envelope.get("achados"), list) and citacoes.conferir(envelope["achados"], documentos):
                envelopes[chave] = {**envelope, "contagem": {}}

    outra_posicao: List[Dict[str, Any]] = []
    for chave, envelope in envelopes.items():
        fora = FORA_DA_POSICAO.get(_posicao(chave), frozenset())
        status, achados = _status_da_dimensao(envelope, travam, fora)
        por_dimensao[chave] = {"status": status, "achados": [a for a in achados if not _de_outra_posicao(a, fora)]}
        for a in achados:
            bruto = str(a.get("codigo") or a.get("id") or "").upper()
            m = re.search(r"[A-Z]{3,4}-\d{2}", bruto)
            ident = m.group(0) if m else ""
            copia = dict(a)
            copia["dimensao"] = chave
            if _de_outra_posicao(a, fora):
                # não some: o relatório o lista como avaliado em outra posição
                outra_posicao.append(copia)
                continue
            if ident in FORA_DA_ESTEIRA:
                copia["severidade"] = "atencao"
                copia["classe"] = "pendencia-plataforma"
            todos.append(copia)

    global_ = min((d["status"] for d in por_dimensao.values()), key=lambda s: _ORDEM[s]) if por_dimensao else "bloqueado"
    return {
        "status": global_,
        "por_dimensao": por_dimensao,
        "achados": todos,
        "outra_posicao": outra_posicao,
        "bloqueantes_conhecidos": sorted(travam),
    }


def relatorio(resultado: Dict[str, Any], missao: str = "", titulo: str = "Validação de insumos",
              divergencias: Optional[List[str]] = None) -> str:
    icone = {"aprovado": "🟢 APTO PARA CODIFICAR", "amarelo": "🟡 APTO COM RESSALVAS",
             "bloqueado": "🔴 NÃO APTO PARA CODIFICAR"}[resultado["status"]]
    linhas = [f"# {titulo} — {missao or 'missão'}", "",
              f"**Veredito: {icone}**", "",
              "| Dimensão | Veredito | Achados |", "|---|---|---|"]
    marca = {"aprovado": "🟢", "amarelo": "🟡", "bloqueado": "🔴"}
    for chave, dados in resultado["por_dimensao"].items():
        linhas.append(f"| {DIMENSOES.get(chave, chave)} | {marca[dados['status']]} | {len(dados['achados'])} |")
    if divergencias:
        linhas += ["", "## Passou na etapa, reprova aqui", "",
                   "A segunda verificação discorda da banca da etapa. É o sinal de que a correção pedida lá não pegou, "
                   "ou de que o juiz da etapa foi enganado:", ""] + [f"- {d}" for d in divergencias]

    impedem = [a for a in resultado["achados"] if str(a.get("severidade", "")).lower() in ("bloqueio", "nok", "❌")]
    plataforma = [a for a in resultado["achados"] if a.get("classe") == "pendencia-plataforma"]
    if impedem:
        linhas += ["", "## O que impede a codificação", ""]
        for a in impedem:
            linhas.append(f"- **{a.get('codigo') or a.get('id') or '—'}** ({a.get('dimensao', '—')}): {a.get('resumo', '')}")
    if plataforma:
        linhas += ["", "## Pendências de plataforma (declaradas, não impedem)", "",
                   "Pedem ato no monorepo — porta de dev, versão em três lugares, suíte E2E, "
                   "invariantes, publicação no Storybook, tema. O PRD que as nomeia é o entregável.", ""]
        for a in plataforma:
            linhas.append(f"- {a.get('codigo') or '—'}: {a.get('resumo', '')}")
    if resultado.get("outra_posicao"):
        linhas += ["", "## Avaliados em outra posição (não contam aqui)", "",
                   "Os modelos dos autores desta etapa não pedem estes critérios; a entrada do dev e o dev os cobram "
                   "sobre o documento que os traz (`tools/banca.FORA_DA_POSICAO`).", ""]
        for a in resultado["outra_posicao"]:
            linhas.append(f"- {a.get('codigo') or a.get('id') or '—'} ({a.get('dimensao', '—')}): {a.get('resumo', '')}")

    linhas += ["", "```json", _envelope_json(resultado, missao), "```"]
    return "\n".join(linhas)


def _envelope_json(resultado: Dict[str, Any], missao: str) -> str:
    import json
    return json.dumps({
        "agente": AGENTE, "missao": missao, "status": resultado["status"],
        "veredito": {"aprovado": "verde", "amarelo": "amarelo", "bloqueado": "vermelho"}[resultado["status"]],
        "por_dimensao": {k: v["status"] for k, v in resultado["por_dimensao"].items()},
        "achados": [
            # `id` e `agente_responsavel` precisam chegar ao despacho: sem eles, de 22 a
            # 23/09/2026 todo ticket da banca foi descartado — o retrabalho não consertava nada.
            {k: a.get(k) for k in ("id", "codigo", "severidade", "agente_responsavel", "dimensao", "classe", "resumo")
             if a.get(k)}
            for a in resultado["achados"]
        ],
        "precisa_humano": any(a.get("classe") == "pendencia-plataforma" for a in resultado["achados"]),
    }, ensure_ascii=False, indent=2)
