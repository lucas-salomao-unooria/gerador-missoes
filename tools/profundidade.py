"""Profundidade pedagógica conferível: o núcleo vive os conceitos do material, e o aha tem ápice.

O time pedagógico devolvia as missões por serem rasas: o material do bimestre chegava ao núcleo
narrativo, mas nenhuma regra pedia que a missão trabalhasse os conceitos dele, e nenhum gate
media isso — o único critério sobre o aha era "dá para resumir numa frase?" (2.4). Na
exp02ef1b de 23/09/2026, o material "Toda imagem tem um autor" trazia intenção de quem
fotografa, enquadramento, fotolegenda e imagem como documento; a missão viveu só o
enquadramento, e o aha era um zoom-out sem consequência nenhuma da escolha do estudante.

Duas perguntas de FATO, no molde de `tools/evidencia.py` (só se lê TABELA com cabeçalho
reconhecido; prosa é ignorada):

- **Cobertura** — todo conceito `limiar` e `núcleo` do mapa conceitual tem linha na tabela 1.1
  do núcleo, com etapa em tela ou com a justificativa de ficar de fora; o limiar vive no Decidir
  ou no Resultado/Aha; a anatomia do aha (1.2) tem os seis passos preenchidos; o trecho que o
  mapa cita existe no material anexado.
- **Veredito do juiz** — o status do juiz de profundidade é recontado a partir das notas que ele
  mesmo deu. Um juiz que escreve "aprovado" com o ápice em 2 não aprova: é a mesma lição da banca
  de dev (23/09/2026), onde o veredito passou a ser contado em código.

Julgar se a consequência é "sentida" ou se a virada contradiz a crença continua com o LLM.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from agents.callbacks import extrair_envelope
from tools.evidencia import _norm, _tabelas

AGENTE_COBERTURA = "cobertura-conceitual"
AGENTE_JUIZ = "juiz-profundidade"

#: As seis dimensões da rubrica (`references/criterios-profundidade.md`).
DIMENSOES: Tuple[str, ...] = ("P1", "P2", "P3", "P4", "P5", "P6")
NOME_DIMENSAO = {
    "P1": "Conceito do material vivido",
    "P2": "Aposta comprometida",
    "P3": "Ápice do aha",
    "P4": "Explicar depois de viver",
    "P5": "Conserto do objeto no Explicar",
    "P6": "Demanda à altura do ano e do material",
}
#: Sem estas três em 3 ou mais, não há aha — há informação revelada.
NUCLEO_DO_AHA: Tuple[str, ...] = ("P1", "P2", "P3")

#: Os seis passos da anatomia do aha, na ordem em que a tabela 1.2 os traz. Desde 29/10/2026 o sexto é o conserto — o
#: estudante aplica o conceito nomeado ao mesmo objeto da Etapa 3, ainda no Explicar —, e não mais a transferência a um
#: cenário novo no Refletir: a etapa 6 saiu da missão por decisão do PO.
PASSOS_DO_AHA: Tuple[Tuple[str, str], ...] = (
    ("crenca", "Crença de entrada"),
    ("aposta", "Aposta comprometida"),
    ("consequencia", "Consequência sentida"),
    ("virada", "Virada"),
    ("nomeacao", "Nomeação"),
    ("conserto", "Conserto"),
)
_RE_PASSO = {
    "crenca": re.compile(r"cren[cç]a", re.I),
    "aposta": re.compile(r"aposta|compromet|previs", re.I),
    "consequencia": re.compile(r"consequ", re.I),
    "virada": re.compile(r"virada|contradi", re.I),
    "nomeacao": re.compile(r"nomea", re.I),
    "conserto": re.compile(r"conserto|consert|recalibr|reconfigur", re.I),
}

_RE_ETAPA = re.compile(r"\b(desafiar|navegar|decidir|resultado|aha|explicar)\b", re.I)
_RE_ETAPA_DO_AHA = re.compile(r"\b(decidir|resultado|aha)\b", re.I)
_RE_FORA = re.compile(r"^\s*[`*_]*\s*(fora|deixad[oa] de fora|fora do escopo)\b", re.I)
_RE_ID_CONCEITO = re.compile(r"\bC\d{1,2}\b")
_RE_ID_CRENCA = re.compile(r"\bB\d{1,2}\b")
_RE_PLACEHOLDER = re.compile(r"<[^>]{2,}>|\[preencher|\[a definir", re.I)
_RE_CITACAO = re.compile(r"[\"“”«»]([^\"“”«»]{12,})[\"“”«»]")

#: Tamanho mínimo, em caracteres, do que justifica deixar um conceito de fora.
MIN_JUSTIFICATIVA = 40
#: Tamanho mínimo de cada passo da anatomia: menos do que isso é rótulo, não desenho.
MIN_PASSO = 25


def _achado(codigo: str, resumo: str, severidade: str = "bloqueio", dono: str = "produto") -> Dict[str, str]:
    return {"severidade": severidade, "codigo": codigo, "etapa": "produto",
            "agente_responsavel": dono, "resumo": resumo}


#: Aspas e apóstrofos de qualquer tipografia: o mapa cita o material entre aspas e troca as aspas internas dele.
_RE_ASPAS = re.compile(r"[\"'“”‘’«»‹›„‟`´]")
_TRACOS = str.maketrans({"—": "-", "–": "-", "‐": "-", "‑": "-", "−": "-", "\u00a0": " ", "\u202f": " ", "…": "..."})


def _plano(texto: str) -> str:
    """Texto normalizado para procurar uma citação: sem acento, sem markdown, sem aspas, espaço único.

    As aspas saem dos dois lados: na exp02em1b (60cfa7f4, 21/10/2026) o material diz «…mas o "engajamento". O
    algoritmo prioriza…» e o mapa, citando entre aspas, escreveu «mas o 'engajamento'» ou tirou as aspas internas
    («metadados, que são…» contra «coleta "metadados", que são…»): três `trecho-inexistente` falsos em todo refazer."""
    sem_md = re.sub(r"[*_#>|]", " ", _RE_ASPAS.sub("", (texto or "").translate(_TRACOS)))
    return re.sub(r"\s+", " ", _norm(sem_md)).strip()


_RE_MATERIAL_DO_PEDIDO = re.compile(r"^### Material anexado ao pedido\s*\n(.*?)(?=^### Como agir|\Z)", re.S | re.M)


def material_do_po(state: Dict[str, Any]) -> str:
    """O material que o PO trouxe depois da geração — colado no texto de um pedido ou parecer, ou anexado ao pedido de
    refazer —, que o mapa conceitual também pode citar.

    Até 24/10/2026 a cobertura comparava só com `material_anexado`. Na exp04ef1b (8ce9c32d, 25/09/2026) o PO colou o
    material do bimestre no parecer de refazer («Segue o material trabalhado no bimestre…»), o mapa citou cinco trechos
    dele, e os cinco saíram `trecho-inexistente` em todas as execuções seguintes. O anexo de um refazer também não entra
    em `material_anexado` quando a sessão já o tinha (`pipeline.reexecucao.material_para_refazer_produto`). Do pedido
    corrente entra só o que a pessoa escreveu e anexou — o cabeçalho da esteira não é material."""
    from pipeline.reexecucao import texto_do_pedido

    partes = [str(p.get("texto") or "") for p in state.get("pedidos_do_po") or [] if isinstance(p, dict)]
    partes += [str(p.get("comentario") or "") for p in state.get("pareceres_humanos") or [] if isinstance(p, dict)]
    # nas notas de passagem, o que está citado com «>» é a palavra do PO (pedidos e pareceres); o resto é da esteira
    partes.append("\n".join(re.sub(r"^>\s?", "", l) for l in str(state.get("notas_de_passagem") or "").splitlines()
                            if l.startswith(">")))
    pedido = str(state.get("pedido_correcao") or "")
    partes.append(texto_do_pedido(pedido))
    anexos = _RE_MATERIAL_DO_PEDIDO.search(pedido)
    if anexos:
        partes.append(anexos.group(1))
    return "\n\n".join(p for p in partes if p.strip())


def material_da_sessao(state: Dict[str, Any]) -> str:
    """O material anexado à geração mais o que o PO trouxe depois (`material_do_po`)."""
    return "\n\n".join(p for p in (str(state.get("material_anexado") or ""), material_do_po(state)) if p.strip())


def ler_mapa(mapa: str) -> Dict[str, Any]:
    """Conceitos e crenças do mapa conceitual, pelas tabelas; o envelope diz a fonte."""
    envelope = extrair_envelope(mapa or "") or {}
    conceitos: Dict[str, Dict[str, str]] = {}
    for tabela in _tabelas(mapa or "", {"id", "conceito", "papel"}):
        for linha in tabela:
            ident = _RE_ID_CONCEITO.search(linha.get("id", ""))
            if not ident:
                continue
            papel = _norm(linha.get("papel", ""))
            papel = "limiar" if "limiar" in papel else "nucleo" if "nucleo" in papel else "apoio"
            conceitos[ident.group(0)] = {"papel": papel, "conceito": linha.get("conceito", "").strip(),
                                         "trecho": linha.get("trecho do material", "").strip()}
    crencas: Dict[str, str] = {}
    for tabela in _tabelas(mapa or "", {"id", "crenca de entrada"}):
        for linha in tabela:
            ident = _RE_ID_CRENCA.search(linha.get("id", ""))
            if ident:
                crencas[ident.group(0)] = linha.get("crenca de entrada", "").strip()
    fonte = str(envelope.get("fonte") or "").strip().lower()
    return {"conceitos": conceitos, "crencas": crencas, "fonte": fonte}


def _tabela_cobertura(nucleo: str) -> List[Dict[str, str]]:
    return [l for t in _tabelas(nucleo or "", {"conceito", "etapa", "o que o estudante faz em tela"}) for l in t]


def _tabela_anatomia(nucleo: str) -> List[Dict[str, str]]:
    return [l for t in _tabelas(nucleo or "", {"passo", "nesta missao"}) for l in t]


def validar_cobertura(nucleo: str, mapa: str, material: str = "") -> Dict[str, Any]:
    """Confere o núcleo contra o mapa conceitual. `status`: aprovado | amarelo | bloqueado.

    Defeito do MAPA (sem limiar, citação que o material não tem) é ⚠️ e não bloqueia: o mapa roda
    fora do loop do núcleo, e devolver ao autor do núcleo um defeito que ele não pode consertar
    gastaria a rodada à toa. Defeito do NÚCLEO bloqueia e volta ao P0a.
    """
    achados: List[Dict[str, str]] = []
    dados = ler_mapa(mapa)
    conceitos, crencas = dados["conceitos"], dados["crencas"]

    if not (nucleo or "").strip():
        achados.append(_achado("nucleo-vazio", "O núcleo narrativo chegou vazio: não há cobertura a conferir."))
        return {"status": "bloqueado", "achados": achados, "conceitos": conceitos, "cobertos": []}

    # --- o mapa (⚠️, dono: o mapa conceitual)
    if not conceitos:
        achados.append(_achado(
            "mapa-ausente",
            "Sem mapa conceitual legível (tabela `| ID | Conceito | Papel | Trecho do material | … |`): a cobertura "
            "dos conceitos do material não foi conferida. A missão pode estar certa — mas ninguém mediu.",
            severidade="atencao"))
    else:
        limiares = [c for c, d in conceitos.items() if d["papel"] == "limiar"]
        if len(limiares) != 1:
            achados.append(_achado(
                "mapa-sem-limiar" if not limiares else "mapa-com-varios-limiares",
                f"O mapa conceitual declara {len(limiares)} conceito(s) limiar; é exatamente um — o que "
                "a virada da missão precisa mudar no estudante.", severidade="atencao"))
        material_plano = _plano(material)
        if material_plano and dados["fonte"] != "briefing":
            for ident, d in conceitos.items():
                citacoes = _RE_CITACAO.findall(d["trecho"])
                if not citacoes:
                    achados.append(_achado(
                        "trecho-sem-citacao",
                        f"`{ident}` ({d['conceito'][:60]}) não cita entre aspas o trecho do material de onde saiu: "
                        "conceito sem citação pode ser do modelo, não do bimestre.", severidade="atencao"))
                    continue
                # Uma citação existente basta: o mapa pode citar duas semanas e parafrasear uma.
                if not any(_plano(c)[:120] in material_plano for c in citacoes):
                    achados.append(_achado(
                        "trecho-inexistente",
                        f"`{ident}`: o trecho citado («{citacoes[0][:80]}») não está no material anexado. "
                        "O mapa inventou ou reescreveu o conceito — confira antes de aceitar a cobertura.",
                        severidade="atencao"))

    # --- a tabela 1.1 do núcleo
    linhas = _tabela_cobertura(nucleo)
    cobertos: List[str] = []
    if not linhas:
        achados.append(_achado(
            "cobertura-ausente",
            "O núcleo não traz a tabela 1.1 «Conceitos do material vividos em tela» com o cabeçalho "
            "`| Conceito | Etapa | O que o estudante faz em tela | Como o professor aprofunda |`. Sem ela não se sabe "
            "qual conceito do bimestre a missão trabalha — era exatamente a reclamação do time pedagógico."))
    por_id: Dict[str, Dict[str, str]] = {}
    for linha in linhas:
        for ident in _RE_ID_CONCEITO.findall(linha.get("conceito", "")):
            por_id.setdefault(ident, linha)
    for ident in por_id:
        if conceitos and ident not in conceitos:
            achados.append(_achado("conceito-desconhecido",
                                   f"A tabela 1.1 cita `{ident}`, que não existe no mapa conceitual.",
                                   severidade="atencao"))

    for ident, d in conceitos.items():
        if d["papel"] == "apoio":
            continue
        linha = por_id.get(ident)
        rotulo = f"`{ident}` ({d['conceito'][:70]})"
        if linha is None:
            achados.append(_achado(
                "conceito-sem-destino",
                f"{rotulo} é {'o limiar' if d['papel'] == 'limiar' else 'conceito núcleo'} do material e não aparece "
                "na tabela 1.1 — nem vivido em tela, nem deixado de fora com justificativa."))
            continue
        etapa = linha.get("etapa", "")
        faz = linha.get("o que o estudante faz em tela", "").strip()
        if _RE_FORA.search(etapa):
            if d["papel"] == "limiar":
                achados.append(_achado(
                    "limiar-fora",
                    f"{rotulo} é o conceito limiar do bimestre e o núcleo o deixou de fora. A virada da missão "
                    "tem de ser sobre ele — é o que o material existe para mudar no estudante."))
            elif len(faz) < MIN_JUSTIFICATIVA:
                achados.append(_achado(
                    "fora-sem-justificativa",
                    f"{rotulo} ficou de fora sem justificativa de ao menos {MIN_JUSTIFICATIVA} caracteres "
                    "(por que não cabe nesta missão e que semana do bimestre o cobre)."))
            continue
        if not _RE_ETAPA.search(etapa):
            achados.append(_achado("etapa-invalida",
                                   f"{rotulo}: a coluna Etapa não nomeia uma das cinco etapas nem diz «fora»."))
            continue
        if re.search(r"\brefletir\b|\betapa\s*6\b|\bE6\b", etapa, re.I):
            achados.append(_achado("etapa-6-removida",
                                   f"{rotulo}: a coluna Etapa cita a Etapa 6 / Refletir (`{etapa.strip()}`). "
                                   "A missão termina na Etapa 5 (Explicar), sem Etapa 6 de transferência."))
            continue
        if len(faz) < MIN_PASSO or _RE_PLACEHOLDER.search(faz):
            achados.append(_achado("acao-vazia",
                                   f"{rotulo}: a coluna «O que o estudante faz em tela» está vazia ou é um marcador."))
            continue
        if d["papel"] == "limiar" and not _RE_ETAPA_DO_AHA.search(etapa):
            achados.append(_achado(
                "limiar-fora-do-aha",
                f"{rotulo} é o limiar e vive só em «{etapa.strip()}». Ele precisa estar no Decidir ou no "
                "Resultado/Aha: é a escolha do estudante sobre ele que a virada desmonta."))
            continue
        cobertos.append(ident)

    # --- a anatomia do aha (1.2)
    anatomia = _tabela_anatomia(nucleo)
    if not anatomia:
        achados.append(_achado(
            "anatomia-ausente",
            "O núcleo não traz a tabela 1.2 «Anatomia do aha» (`| Passo | Nesta missão |`, seis linhas: "
            + " · ".join(r for _, r in PASSOS_DO_AHA) + ")."))
    else:
        for chave, rotulo in PASSOS_DO_AHA:
            linha = next((l for l in anatomia if _RE_PASSO[chave].search(l.get("passo", ""))), None)
            texto = (linha or {}).get("nesta missao", "").strip()
            if linha is None or len(texto) < MIN_PASSO or _RE_PLACEHOLDER.search(texto):
                achados.append(_achado(
                    "anatomia-incompleta",
                    f"Anatomia do aha sem o passo «{rotulo}» preenchido de verdade "
                    f"(ao menos {MIN_PASSO} caracteres, sem marcador)."))
            elif chave == "crenca" and crencas and not _RE_ID_CRENCA.search(texto):
                achados.append(_achado(
                    "crenca-sem-id",
                    "O passo «Crença de entrada» não aponta a crença do mapa (`B1`, `B2`…) que a missão derruba.",
                    severidade="atencao"))

    bloqueios = [a for a in achados if a["severidade"] == "bloqueio"]
    status = "bloqueado" if bloqueios else ("amarelo" if achados else "aprovado")
    return {"status": status, "achados": achados, "conceitos": conceitos, "cobertos": cobertos}


def relatorio_cobertura(resultado: Dict[str, Any], missao: str = "") -> str:
    icone = {"aprovado": "🟢 COBERTURA CONFERIDA", "amarelo": "🟡 COM RESSALVAS", "bloqueado": "🔴 BLOQUEADO"}[resultado["status"]]
    conceitos = resultado.get("conceitos") or {}
    linhas = [f"# Cobertura conceitual — {missao or 'missão'}", "", f"**Veredito: {icone}**", "",
              f"Conceitos no mapa: **{len(conceitos)}** · limiar e núcleo vividos em tela: "
              f"**{', '.join(f'`{c}`' for c in resultado.get('cobertos') or []) or 'nenhum'}**", ""]
    if resultado["achados"]:
        linhas += ["## Achados", ""]
        for a in resultado["achados"]:
            marca = "❌" if a["severidade"] == "bloqueio" else "⚠️"
            linhas.append(f"- {marca} **{a['codigo']}** — {a['resumo']}")
    else:
        linhas.append("Nenhum achado: o limiar e os conceitos núcleo têm destino, o limiar vive na decisão ou no aha, "
                      "e a anatomia do aha tem os seis passos.")
    linhas += ["", "```json", json.dumps(
        {"agente": AGENTE_COBERTURA, "missao": missao, "status": resultado["status"], "achados": resultado["achados"]},
        ensure_ascii=False, indent=2), "```"]
    return "\n".join(linhas)


# ------------------------------------------------------------------ veredito do juiz
def _nota(valor: Any) -> Optional[int]:
    if isinstance(valor, bool):
        return None
    try:
        n = int(float(str(valor).strip()))
    except (TypeError, ValueError):
        return None
    return n if 1 <= n <= 4 else None


def veredito_por_notas(notas: Any) -> Tuple[str, List[Dict[str, str]]]:
    """O status que as notas sustentam — `aprovado` | `amarelo` | `bloqueado` — e por quê.

    - 🔴 qualquer dimensão em 1, ou P1, P2 ou P3 abaixo de 3: sem conceito vivido, sem aposta ou
      sem ápice, o que sobra é informação revelada — o defeito que o time pedagógico devolvia;
    - 🟡 núcleo do aha em 3+ e alguma de P4–P6 em 2;
    - 🟢 as seis em 3 ou 4.
    Nota ausente ou fora de 1–4 é bloqueio: juiz que não pontuou não julgou.
    """
    achados: List[Dict[str, str]] = []
    lidas: Dict[str, Optional[int]] = {d: _nota((notas or {}).get(d)) if isinstance(notas, dict) else None
                                        for d in DIMENSOES}
    faltam = [d for d, n in lidas.items() if n is None]
    if faltam:
        achados.append(_achado("notas-ilegiveis",
                               f"O juiz de profundidade não deu nota de 1 a 4 em {', '.join(faltam)}: "
                               "sem nota, a dimensão não foi julgada."))
        return "bloqueado", achados
    baixas = [d for d in NUCLEO_DO_AHA if lidas[d] < 3]
    for d in baixas:
        achados.append(_achado(f"{d.lower()}-abaixo-do-corte",
                               f"{d} · {NOME_DIMENSAO[d]} em {lidas[d]}/4 — o núcleo do aha exige 3."))
    for d in (d for d in DIMENSOES if lidas[d] == 1 and d not in baixas):
        achados.append(_achado(f"{d.lower()}-ausente", f"{d} · {NOME_DIMENSAO[d]} em 1/4: a dimensão não existe na missão."))
    if achados:
        return "bloqueado", achados
    doises = [d for d in DIMENSOES if lidas[d] == 2]
    for d in doises:
        achados.append(_achado(f"{d.lower()}-fraca", f"{d} · {NOME_DIMENSAO[d]} em 2/4.", severidade="atencao"))
    return ("amarelo" if doises else "aprovado"), achados


_GRAVIDADE = {"aprovado": 0, "amarelo": 1, "bloqueado": 2}


def _status_do_juiz(envelope: Dict[str, Any]) -> str:
    bruto = str(envelope.get("status") or envelope.get("veredito") or "").strip().lower()
    if bruto in ("aprovado", "passa", "verde", "🟢"):
        return "aprovado"
    if bruto in ("aprovado_com_ressalvas", "ressalvas", "amarelo", "🟡"):
        return "amarelo"
    return "bloqueado"


def consolidar(relatorio_juiz: str, cobertura: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Veredito final de profundidade: o mais severo entre notas, juiz e cobertura determinística."""
    envelope = extrair_envelope(relatorio_juiz or "") or {}
    achados: List[Dict[str, str]] = []
    notas: Dict[str, Any] = {}
    if not envelope:
        achados.append(_achado("juiz-sem-veredito",
                               "O juiz de profundidade não devolveu envelope legível: resposta vazia, truncada ou "
                               "sem o bloco JSON. Não respondeu não é aprovou."))
        status = "bloqueado"
    else:
        notas = envelope.get("notas") if isinstance(envelope.get("notas"), dict) else {}
        pelas_notas, achados_notas = veredito_por_notas(notas)
        do_juiz = _status_do_juiz(envelope)
        for a in envelope.get("achados") or []:
            if isinstance(a, dict) and a.get("resumo"):
                achados.append({"severidade": str(a.get("severidade") or "atencao"),
                                "codigo": str(a.get("codigo") or "profundidade"),
                                "etapa": "produto", "agente_responsavel": str(a.get("agente_responsavel") or "produto"),
                                "resumo": str(a["resumo"])})
        # As notas mandam; o juiz pode ser MAIS severo (viu algo que a nota não diz), nunca menos.
        if _GRAVIDADE[do_juiz] < _GRAVIDADE[pelas_notas]:
            achados.append(_achado("veredito-incoerente",
                                   f"O juiz escreveu `{envelope.get('status')}`, mas as notas que ele deu sustentam "
                                   f"`{pelas_notas}`. Vale o que as notas dizem.", severidade="atencao"))
        achados += achados_notas
        status = max((pelas_notas, do_juiz), key=_GRAVIDADE.__getitem__)

    cob = cobertura or {}
    achados += [a for a in cob.get("achados") or [] if isinstance(a, dict)]
    status_cob = str(cob.get("status") or "aprovado")
    status = max((status, status_cob if status_cob in _GRAVIDADE else "bloqueado"), key=_GRAVIDADE.__getitem__)
    return {"status": status, "achados": achados,
            "notas": {d: _nota(notas.get(d)) for d in DIMENSOES} if notas else {},
            "aha_em_uma_frase": str(envelope.get("aha_em_uma_frase") or "").strip(),
            "ponto_mais_fraco": str(envelope.get("ponto_mais_fraco") or "").strip()}


def linha_de_notas(notas: Dict[str, Any]) -> str:
    """`P1 3 · P2 4 · …` para o cartão do parecer e o dossiê."""
    return " · ".join(f"{d} {notas.get(d) or '—'}" for d in DIMENSOES)
