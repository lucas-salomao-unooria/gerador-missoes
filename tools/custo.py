"""Custo de uma missão em tokens, dólares e reais, somando todas as execuções dela e detalhando por etapa e agente.

O runner já contava os tokens por agente (`state["execucao"]`), mas cada execução sobrescrevia a anterior: depois de
um refazer, ninguém sabia quanto a missão tinha custado no total. `state["custo_missao"]` guarda uma linha por
execução (nova, iniciar etapa, refazer, edição pontual, triagem, conversa, protótipo hi-fi), o consolidado por etapa
(`por_etapa`), o consolidado por agente (`por_agente`), o consolidado por modelo (`por_modelo`) e o total da missão,
e não sai do estado numa reexecução.

Preço: tabela Standard da API do Gemini (https://ai.google.dev/gemini-api/docs/pricing, consultada em 12/10/2026),
em dólares por 1 milhão de tokens. A saída inclui os tokens de pensamento. A entrada que veio do cache implícito
ou explícito custa a tarifa de cache, não a cheia — e a economia proporcionada pelo cache é calculada separadamente.

O real usa a cotação do momento da execução, nesta ordem: `COTACAO_USD_BRL` no ambiente (para fixar um valor); a PTAX
de venda mais recente do Banco Central (API pública Olinda, sem chave); o padrão, se a API não responder. A linha da
execução guarda a cotação e a fonte dela.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.request
from datetime import date, timedelta
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

KEY_CUSTO = "custo_missao"
#: Acumulador transitório de chamadas LLM feitas fora do loop principal do ADK (editor pontual, retrabalho por trocas,
#: triagem de pedido) durante uma execução: o runner recolhe, incorpora em `tokens_por_agente` e limpa ao fechar.
KEY_USO_EXTERNO = "_uso_llm_externo"

#: `modelo → [(vale até, entrada, saída, entrada em cache)]`, em US$ por 1M de tokens. `None` = sem data final.
PRECOS: Dict[str, List[Tuple[Optional[date], float, float, float]]] = {
    "gemini-3.8-flash": [(date(2026, 12, 31), 0.75, 3.75, 0.075), (None, 1.50, 7.50, 0.15)],
    "gemini-3.6-flash": [(date(2026, 12, 31), 0.75, 3.75, 0.075), (None, 1.50, 7.50, 0.15)],
    "gemini-3.5-flash-lite": [(None, 0.25, 1.50, 0.025)],
    "gemini-3.1-flash-lite": [(None, 0.25, 1.50, 0.025)],
    "gemini-3.1-flash-lite-preview": [(None, 0.25, 1.50, 0.025)],
    "gemini-2.5-flash-lite": [(None, 0.10, 0.40, 0.01)],
    "gemini-3-flash-preview": [(None, 0.50, 3.00, 0.05)],
    # o modelo do agente de código do protótipo hi-fi (tools/prototipo_hifi); tabela consultada em 30/10/2026
    "gemini-4-argon": [(date(2026, 11, 30), 2.00, 10.00, 0.10), (None, 4.00, 20.00, 0.20)],
}

#: US$ por imagem gerada, na resolução 1K (as do protótipo hi-fi são reduzidas depois, mas saem do modelo em 1K).
PRECO_IMAGEM: Dict[str, float] = {"gemini-3.1-flash-lite-image": 0.0336}

#: Ordem canônica das etapas para exibição e agrupamento de custos.
ORDEM_ETAPAS_CUSTO: Tuple[str, ...] = (
    "produto",
    "design",
    "dev",
    "transversal",
    "prototipo-hifi",
    "edicao_pontual",
    "triagem",
    "conversa",
)

#: Etapas principais da esteira (sempre listadas no resumo por etapa de uma missão).
ETAPAS_PRINCIPAIS: Tuple[str, ...] = ("produto", "design", "dev", "transversal")

ROTULOS_ETAPA_CUSTO: Dict[str, str] = {
    "produto": "🧭 Produto",
    "spec": "🧭 Produto (Spec)",
    "design": "🎨 Design",
    "dev": "⚙️ Dev",
    "transversal": "📚 Transversal",
    "prototipo-hifi": "✨ Protótipo Hi-Fi",
    "edicao_pontual": "✏️ Edição pontual",
    "triagem": "🔎 Triagem de pedido",
    "conversa": "💬 Conversa da etapa",
}

ROTULOS_AGENTES_ESPECIAIS: Dict[str, str] = {
    "ClassificadorDeSentido": "Classificador semântico dos gates (C7)",
    "A000EditorPontual": "Editor de correção pontual por trocas",
    "A000TriagemCorrecao": "Triagem semântica do pedido de correção",
    "A000ConversaEtapa": "Assistente de conversa da etapa",
}

#: Aliases de conveniência para importadores da interface e testes.
ORDEM_ETAPAS = ORDEM_ETAPAS_CUSTO
ROTULOS_ETAPAS = ROTULOS_ETAPA_CUSTO
TABELA_PRECOS = PRECOS

_RE_AGENTE_PASSO = re.compile(r"^A(\d{3})([a-z]?)")

logger = logging.getLogger(__name__)

#: Cotação de último recurso: sem `COTACAO_USD_BRL` e sem resposta da PTAX.
COTACAO_PADRAO = 5.50

_PTAX = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo("
         "dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?@dataInicial='{ini}'&@dataFinalCotacao='{fim}'"
         "&$top=100&$format=json&$select=cotacaoVenda,dataHoraCotacao")
#: `{dia: (cotação, fonte)}`: uma consulta por dia e por processo.
_CACHE_PTAX: Dict[date, Tuple[float, str]] = {}


def ptax_venda(hoje: Optional[date] = None, timeout: float = 5.0) -> Optional[Tuple[float, str]]:
    """`(cotação, "PTAX dd/mm/aaaa")` do último dia útil dos 10 anteriores; `None` se a API falhar."""
    hoje = hoje or date.today()
    if hoje in _CACHE_PTAX:
        return _CACHE_PTAX[hoje]
    url = _PTAX.format(ini=(hoje - timedelta(days=10)).strftime("%m-%d-%Y"), fim=hoje.strftime("%m-%d-%Y"))
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            valores = json.loads(resp.read().decode("utf-8")).get("value") or []
        ultimo = valores[-1]
        dia = ultimo["dataHoraCotacao"][:10].split("-")
        resultado = (float(ultimo["cotacaoVenda"]), f"PTAX {dia[2]}/{dia[1]}/{dia[0]}")
    except Exception as exc:  # sem rede ou API fora: o custo não pode derrubar a execução
        logger.warning("PTAX indisponível (%s); a cotação cai no padrão", exc)
        return None
    _CACHE_PTAX[hoje] = resultado
    return resultado


def cotacao_usd_brl() -> Tuple[float, str]:
    """`(cotação, fonte)`: o `.env` vence, depois a PTAX, depois o padrão."""
    fixa = os.getenv("COTACAO_USD_BRL", "").strip()
    if fixa:
        try:
            return float(fixa.replace(",", ".")), "COTACAO_USD_BRL"
        except ValueError:
            logger.warning("COTACAO_USD_BRL inválida: %r", fixa)
    return ptax_venda() or (COTACAO_PADRAO, "padrão (PTAX indisponível)")


def preco(modelo: str, dia: Optional[date] = None) -> Optional[Tuple[float, float, float]]:
    """`(entrada, saída, cache)` em US$/1M do modelo no dia; `None` se o modelo não está na tabela."""
    nome = (modelo or "").strip().lower().split(" ")[0]
    faixas = PRECOS.get(nome)
    if not faixas:
        return None
    dia = dia or date.today()
    for ate, entrada, saida, cache in faixas:
        if ate is None or dia <= ate:
            return entrada, saida, cache
    return faixas[-1][1:]


def rotulo_etapa(etapa: str) -> str:
    """Nome amigável com ícone para uma etapa de custo."""
    e = (etapa or "").strip().lower()
    return ROTULOS_ETAPA_CUSTO.get(e, e.capitalize() if e else "Outros")


@lru_cache(maxsize=1)
def _mapa_metadados_agentes() -> Dict[str, Dict[str, str]]:
    """`{agent_id: {"etapa": stage, "rotulo": name}}` e `{"#NNN": {"etapa": stage, "rotulo": name}}`."""
    por_id: Dict[str, Dict[str, str]] = {}
    try:
        from pipeline.orchestrator import get_pipeline_agents_metadata

        for meta in get_pipeline_agents_metadata(active_only=False):
            aid = str(meta.get("id") or "")
            etapa = str(meta.get("stage") or "")
            nome = str(meta.get("name") or aid)
            if aid:
                por_id[aid] = {"etapa": etapa, "rotulo": nome}
            m = _RE_AGENTE_PASSO.match(aid)
            if m:
                chave_num = f"#{int(m.group(1)):03d}{m.group(2)}"
                por_id.setdefault(chave_num, {"etapa": etapa, "rotulo": nome})
                por_id.setdefault(f"#{int(m.group(1)):03d}", {"etapa": etapa, "rotulo": nome})
    except Exception:
        pass
    return por_id


def normalizar_etapa(etapa: str) -> str:
    """Normaliza `spec` para `produto` (na esteira de 4 etapas a spec é a segunda metade de produto)."""
    e = (etapa or "").strip().lower()
    if e == "spec":
        return "produto"
    return e


def etapa_do_agente(agente: str, etapas_execucao: Optional[Sequence[str]] = None) -> str:
    """Determina a qual etapa (`produto`, `design`, `dev`, `transversal`, `prototipo-hifi`, etc.) pertence o agente."""
    nome = (agente or "").strip()
    if not nome:
        return normalizar_etapa(etapas_execucao[0]) if etapas_execucao else "produto"

    if nome.startswith("hifi:"):
        return "prototipo-hifi"

    # Agente qualificado com sufixo `:<etapa>` (ex.: `A000EditorPontual:design`, `ClassificadorDeSentido:produto`)
    if ":" in nome:
        base, sufixo = nome.split(":", 1)
        sufixo_norm = normalizar_etapa(sufixo)
        if sufixo_norm in ORDEM_ETAPAS_CUSTO:
            return sufixo_norm
        nome = base

    # Consulta direta aos metadados da árvore do orquestrador
    mapa = _mapa_metadados_agentes()
    if nome in mapa and mapa[nome].get("etapa"):
        return normalizar_etapa(mapa[nome]["etapa"])

    # Pelo número `A<NNN>` (cobre retrabalhos, juízes internos, intérpretes e agentes legados)
    m = _RE_AGENTE_PASSO.match(nome)
    if m:
        num = int(m.group(1))
        letra = m.group(2)
        for ch in (f"#{num:03d}{letra}", f"#{num:03d}"):
            if ch in mapa and mapa[ch].get("etapa"):
                return normalizar_etapa(mapa[ch]["etapa"])
        if num == 0:
            pass
        elif 1 <= num <= 63:
            return "produto"
        elif (64 <= num <= 94) or (120 <= num <= 124):
            return "design"
        elif (95 <= num <= 119) or (125 <= num <= 126):
            return "dev"
        elif 127 <= num <= 129:
            return "transversal"

    etapas_limpas = [normalizar_etapa(e) for e in (etapas_execucao or []) if e]
    etapas_principais_exec = [
        e for e in etapas_limpas if e in ("produto", "design", "dev", "transversal", "prototipo-hifi")
    ]

    if nome.startswith("A000EditorPontual"):
        return etapas_principais_exec[0] if len(etapas_principais_exec) == 1 else "edicao_pontual"
    if nome.startswith("A000TriagemCorrecao"):
        return etapas_principais_exec[0] if len(etapas_principais_exec) == 1 else "triagem"
    if nome.startswith("A000ConversaEtapa"):
        return etapas_principais_exec[0] if len(etapas_principais_exec) == 1 else "conversa"
    if nome.startswith("ClassificadorDeSentido"):
        return etapas_principais_exec[0] if len(etapas_principais_exec) == 1 else "produto"

    if etapas_principais_exec:
        return etapas_principais_exec[0]
    if etapas_limpas:
        return etapas_limpas[0]
    return "produto"


def rotulo_do_agente(agente: str) -> str:
    """Descrição amigável do agente para tabelas de custo."""
    nome = (agente or "").strip()
    if not nome:
        return "Desconhecido"
    if nome.startswith("hifi:"):
        lote = nome.split(":", 1)[1]
        if lote.startswith("correcao-"):
            return f"Protótipo Hi-Fi · Correção ({lote.removeprefix('correcao-')})"
        return f"Protótipo Hi-Fi · Lote {lote}"
    sufixo = ""
    base = nome
    if ":" in nome:
        base, sufixo = nome.split(":", 1)
    if base in ROTULOS_AGENTES_ESPECIAIS:
        rot = ROTULOS_AGENTES_ESPECIAIS[base]
        return f"{rot} ({rotulo_etapa(sufixo)})" if sufixo else rot
    mapa = _mapa_metadados_agentes()
    if base in mapa:
        rot = mapa[base]["rotulo"]
        return f"{rot} ({sufixo})" if sufixo else rot
    m = _RE_AGENTE_PASSO.match(base)
    if m:
        num, letra = int(m.group(1)), m.group(2)
        info = mapa.get(f"#{num:03d}{letra}") or mapa.get(f"#{num:03d}")
        if info:
            rot = info["rotulo"]
            if base.endswith("Retrabalho"):
                rot += " · Retrabalho"
            elif base.endswith("Interprete"):
                rot += " · Intérprete"
            elif base.endswith("Juiz") and "Juiz" not in rot:
                rot += " · Juiz"
            return rot
    return nome


def enriquecer_tokens(tokens: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Completa um dicionário de tokens com todos os campos derivados (`entrada_sem_cache`, `saida_total`,
    `total_tokens`, `taxa_cache_pct`, `taxa_pensamento_pct`, `ferramentas_entrada`, `maior_entrada`, `do_cache`)."""
    t = tokens or {}
    entrada = max(0, int(t.get("entrada", 0) or 0))
    cache = min(max(0, int(t.get("cache", 0) or 0)), entrada)
    entrada_sem_cache = max(0, entrada - cache)
    ferramentas_entrada = max(0, int(t.get("ferramentas_entrada", 0) or 0))
    saida = max(0, int(t.get("saida", 0) or 0))
    pensamento = max(0, int(t.get("pensamento", 0) or 0))
    saida_total = saida + pensamento
    total_tokens = entrada + saida_total
    chamadas = max(0, int(t.get("chamadas", 0) or 0))
    maior_entrada = max(0, int(t.get("maior_entrada", 0) or 0))
    if maior_entrada == 0 and entrada > 0:
        maior_entrada = entrada if chamadas <= 1 else round(entrada / chamadas)
    do_cache = max(0, int(t.get("do_cache", 0) or 0))
    taxa_cache_pct = round((cache / entrada) * 100.0, 1) if entrada > 0 else 0.0
    taxa_pensamento_pct = round((pensamento / saida_total) * 100.0, 1) if saida_total > 0 else 0.0
    return {
        "entrada": entrada,
        "entrada_sem_cache": entrada_sem_cache,
        "cache": cache,
        "taxa_cache_pct": taxa_cache_pct,
        "ferramentas_entrada": ferramentas_entrada,
        "saida": saida,
        "pensamento": pensamento,
        "saida_total": saida_total,
        "taxa_pensamento_pct": taxa_pensamento_pct,
        "total_tokens": total_tokens,
        "maior_entrada": maior_entrada,
        "chamadas": chamadas,
        "do_cache": do_cache,
    }


def _soma(blocos: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Soma uma lista de blocos de tokens preservando todos os contadores e calculando taxas e `maior_entrada`."""
    lista = [enriquecer_tokens(b) for b in blocos if b]
    if not lista:
        return enriquecer_tokens({})
    bruto = {
        "entrada": sum(b["entrada"] for b in lista),
        "cache": sum(b["cache"] for b in lista),
        "ferramentas_entrada": sum(b["ferramentas_entrada"] for b in lista),
        "saida": sum(b["saida"] for b in lista),
        "pensamento": sum(b["pensamento"] for b in lista),
        "chamadas": sum(b["chamadas"] for b in lista),
        "do_cache": sum(b["do_cache"] for b in lista),
        "maior_entrada": max((b["maior_entrada"] for b in lista), default=0),
    }
    return enriquecer_tokens(bruto)


def detalhar_custo_usd(
    tokens: Dict[str, Any],
    modelo: str,
    dia: Optional[date] = None,
    cotacao: Optional[float] = None,
) -> Optional[Dict[str, float]]:
    """Decompõe o custo de um bloco de tokens em: entrada sem cache, entrada em cache, saída, pensamento e
    economia proporcionada pelo cache (em US$ e, se `cotacao` informada, também em R$)."""
    p = preco(modelo, dia)
    if p is None:
        return None
    tarifa_entrada, tarifa_saida, tarifa_cache = p
    t = enriquecer_tokens(tokens)
    usd_entrada_sem_cache = (t["entrada_sem_cache"] * tarifa_entrada) / 1_000_000
    usd_cache = (t["cache"] * tarifa_cache) / 1_000_000
    usd_entrada = usd_entrada_sem_cache + usd_cache
    usd_saida = (t["saida"] * tarifa_saida) / 1_000_000
    usd_pensamento = (t["pensamento"] * tarifa_saida) / 1_000_000
    usd_saida_total = usd_saida + usd_pensamento
    usd_total = usd_entrada + usd_saida_total
    economia_cache_usd = max(0.0, (t["cache"] * (tarifa_entrada - tarifa_cache)) / 1_000_000)

    res: Dict[str, float] = {
        "usd_entrada_sem_cache": round(usd_entrada_sem_cache, 6),
        "usd_cache": round(usd_cache, 6),
        "usd_entrada": round(usd_entrada, 6),
        "usd_saida": round(usd_saida, 6),
        "usd_pensamento": round(usd_pensamento, 6),
        "usd_saida_total": round(usd_saida_total, 6),
        "economia_cache_usd": round(economia_cache_usd, 6),
        "usd": round(usd_total, 6),
    }
    if cotacao is not None:
        c = float(cotacao)
        res.update({
            "brl_entrada_sem_cache": round(usd_entrada_sem_cache * c, 4),
            "brl_cache": round(usd_cache * c, 4),
            "brl_entrada": round(usd_entrada * c, 4),
            "brl_saida": round(usd_saida * c, 4),
            "brl_pensamento": round(usd_pensamento * c, 4),
            "brl_saida_total": round(usd_saida_total * c, 4),
            "economia_cache_brl": round(economia_cache_usd * c, 4),
            "brl": round(usd_total * c, 4),
        })
    return res


def custo_usd(tokens: Dict[str, int], modelo: str, dia: Optional[date] = None) -> Optional[float]:
    """Dólares de um bloco `{entrada, saida, pensamento, cache}`. `entrada` já inclui a parte em cache."""
    p = preco(modelo, dia)
    if p is None:
        return None
    entrada, saida, cache = p
    em_cache = min(int(tokens.get("cache", 0) or 0), int(tokens.get("entrada", 0) or 0))
    cheia = int(tokens.get("entrada", 0) or 0) - em_cache
    gerada = int(tokens.get("saida", 0) or 0) + int(tokens.get("pensamento", 0) or 0)
    return (cheia * entrada + em_cache * cache + gerada * saida) / 1_000_000


def registrar_uso_externo(
    estado: Optional[Dict[str, Any]],
    agente: str,
    tokens: Dict[str, Any],
    modelo: str = "",
    etapa: str = "",
) -> None:
    """Acumula em `estado[KEY_USO_EXTERNO]` o uso de uma chamada LLM feita fora do loop de eventos do ADK
    (ex.: `A000EditorPontual` durante `retrabalhar_por_trocas`, `montar_one_pager_por_trocas` ou `propor_edicao`)."""
    if estado is None or not hasattr(estado, "get"):
        return
    chave_agente = f"{agente}:{normalizar_etapa(etapa)}" if etapa and ":" not in agente else agente
    externo = dict(estado.get(KEY_USO_EXTERNO) or {})
    por_agente = dict(externo.get("tokens_por_agente") or {})
    modelos = dict(externo.get("modelo_por_agente") or {})
    anterior = por_agente.get(chave_agente) or {}
    novo = _soma([anterior, tokens])
    por_agente[chave_agente] = novo
    if modelo:
        modelos[chave_agente] = modelo
    externo["tokens_por_agente"] = por_agente
    externo["modelo_por_agente"] = modelos
    estado[KEY_USO_EXTERNO] = externo


def consumir_uso_externo(
    estado: Optional[Dict[str, Any]],
    tokens_por_agente: Optional[Dict[str, Dict[str, Any]]] = None,
    modelo_por_agente: Optional[Dict[str, str]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    """Incorpora em `tokens_por_agente` (e `modelo_por_agente`) tudo o que foi registrado em `KEY_USO_EXTERNO`
    e remove a chave temporária do estado. Retorna `(tokens_por_agente, modelo_por_agente)`."""
    tpa = tokens_por_agente if tokens_por_agente is not None else {}
    mpa = modelo_por_agente if modelo_por_agente is not None else {}
    if estado is None or not hasattr(estado, "get"):
        return tpa, mpa
    externo = estado.get(KEY_USO_EXTERNO)
    try:
        estado.pop(KEY_USO_EXTERNO, None)
    except Exception:
        estado[KEY_USO_EXTERNO] = {}
    if not isinstance(externo, dict) or not externo:
        return tpa, mpa
    for ag, tok in (externo.get("tokens_por_agente") or {}).items():
        tpa[ag] = _soma([tpa.get(ag) or {}, tok])
    for ag, mod in (externo.get("modelo_por_agente") or {}).items():
        if mod:
            mpa.setdefault(ag, mod)
    return tpa, mpa


#: Agentes de Camada 1 (micro-classificadores semânticos, juiz de achados, intérprete de pedido e triagem).
AGENTES_CAMADA_CLASSIFICADOR: Tuple[str, ...] = (
    "ClassificadorDeSentido",
    "A000TriagemCorrecao",
    "A025JuizContratoProdutoLlm",
    "A049JuizEvidenciaLlm",
    "A102JuizTelemetriaLlm",
    "A010FidelidadeNucleoInterprete",
    "A060FidelidadeProdutoInterprete",
    "A094FidelidadeDesignInterprete",
    "A126FidelidadeDevInterprete",
)

#: Agentes de Camada 2 (pareceres consultivos, juiz de perguntas 9f e síntese de aprendizado).
AGENTES_CAMADA_PARECER: Tuple[str, ...] = (
    "A029aAvaliacaoPedagogica",
    "A029bExperienciaEstudante",
    "A029cAdequacaoPedagogica",
    "A051JuizPerguntas",
    "A128Aprendizado",
)


def modelos_dos_agentes(settings: Any = None) -> Dict[str, str]:
    """Mapa `{agente: modelo}` com os modelos configurados para PRD, Camada 1 (classificador) e Camada 2 (parecer)."""
    if settings is None:
        from config import get_settings

        settings = get_settings()
    mod_cls = getattr(settings, "gemini_model_classificador", "") or getattr(settings, "gemini_model", "gemini-3.8-flash")
    mod_par = getattr(settings, "gemini_model_parecer", "") or getattr(settings, "gemini_model", "gemini-3.8-flash")
    mod_prd = getattr(settings, "gemini_model_prd", "") or getattr(settings, "gemini_model", "gemini-3.8-flash")
    mapa: Dict[str, str] = {"A113PrdWriter": mod_prd}
    for ag in AGENTES_CAMADA_CLASSIFICADOR:
        mapa[ag] = mod_cls
    for ag in AGENTES_CAMADA_PARECER:
        mapa[ag] = mod_par
    return mapa


def _modelo_do_agente(agente: str, modelo_padrao: str, modelo_por_agente: Optional[Dict[str, str]]) -> str:
    """Resolve o modelo de `agente` aceitando chave exata, prefixo antes de `:<etapa>` ou sufixos de subagentes de Camada 1."""
    mpa = modelo_por_agente or {}
    if agente in mpa and mpa[agente]:
        return mpa[agente]
    base = str(agente or "").split(":", 1)[0].strip()
    if base in mpa and mpa[base]:
        return mpa[base]
    if base.endswith(("FidelidadeNucleoInterprete", "FidelidadeProdutoInterprete", "FidelidadeDesignInterprete", "FidelidadeDevInterprete", "Interprete")) or (
        base.endswith("Llm") and "Juiz" in base
    ):
        if "ClassificadorDeSentido" in mpa and mpa["ClassificadorDeSentido"]:
            return mpa["ClassificadorDeSentido"]
    return modelo_padrao


def custo_da_execucao(
    tokens_por_agente: Dict[str, Dict[str, int]],
    modelo: str,
    modelo_por_agente: Dict[str, str],
    dia: Optional[date] = None,
    etapas: Optional[Sequence[str]] = None,
    cotacao_fixa: Optional[Tuple[float, str]] = None,
    duracao_s: Optional[float] = None,
) -> Dict[str, Any]:
    """Tokens e custo de uma execução, cada agente pelo modelo e pela etapa dele."""
    cotacao, fonte = cotacao_fixa or cotacao_usd_brl()
    usd = 0.0
    usd_entrada_sem_cache = 0.0
    usd_cache = 0.0
    usd_saida = 0.0
    usd_pensamento = 0.0
    economia_cache_usd = 0.0
    sem_preco = set()

    agentes_detalhados: Dict[str, Dict[str, Any]] = {}
    blocos_por_etapa: Dict[str, List[Dict[str, Any]]] = {}
    custos_por_etapa: Dict[str, Dict[str, float]] = {}
    agentes_por_etapa: Dict[str, List[str]] = {}

    for agente, tokens_brutos in tokens_por_agente.items():
        tok = enriquecer_tokens(tokens_brutos)
        m = _modelo_do_agente(agente, modelo, modelo_por_agente)
        etapa = etapa_do_agente(agente, etapas)
        det = detalhar_custo_usd(tok, m, dia, cotacao=cotacao)
        if det is None:
            if m:
                sem_preco.add(m)
            c_usd = 0.0
            det_zeros = {
                "usd_entrada_sem_cache": 0.0,
                "usd_cache": 0.0,
                "usd_entrada": 0.0,
                "usd_saida": 0.0,
                "usd_pensamento": 0.0,
                "usd_saida_total": 0.0,
                "economia_cache_usd": 0.0,
                "usd": 0.0,
                "brl_entrada_sem_cache": 0.0,
                "brl_cache": 0.0,
                "brl_entrada": 0.0,
                "brl_saida": 0.0,
                "brl_pensamento": 0.0,
                "brl_saida_total": 0.0,
                "economia_cache_brl": 0.0,
                "brl": 0.0,
            }
            det = det_zeros
        else:
            c_usd = det["usd"]
            usd += c_usd
            usd_entrada_sem_cache += det["usd_entrada_sem_cache"]
            usd_cache += det["usd_cache"]
            usd_saida += det["usd_saida"]
            usd_pensamento += det["usd_pensamento"]
            economia_cache_usd += det["economia_cache_usd"]

        agentes_detalhados[agente] = {
            **tok,
            "modelo": m,
            "etapa": etapa,
            "usd": round(c_usd, 6),
            "brl": round(c_usd * cotacao, 4),
            "usd_entrada_sem_cache": det["usd_entrada_sem_cache"],
            "usd_cache": det["usd_cache"],
            "usd_saida": det["usd_saida"],
            "usd_pensamento": det["usd_pensamento"],
            "economia_cache_usd": det["economia_cache_usd"],
            "economia_cache_brl": det["economia_cache_brl"],
        }

        blocos_por_etapa.setdefault(etapa, []).append(tok)
        agentes_por_etapa.setdefault(etapa, []).append(agente)
        ce = custos_por_etapa.setdefault(etapa, {
            "usd": 0.0,
            "usd_entrada_sem_cache": 0.0,
            "usd_cache": 0.0,
            "usd_saida": 0.0,
            "usd_pensamento": 0.0,
            "economia_cache_usd": 0.0,
        })
        ce["usd"] += c_usd
        ce["usd_entrada_sem_cache"] += det["usd_entrada_sem_cache"]
        ce["usd_cache"] += det["usd_cache"]
        ce["usd_saida"] += det["usd_saida"]
        ce["usd_pensamento"] += det["usd_pensamento"]
        ce["economia_cache_usd"] += det["economia_cache_usd"]

    por_etapa_exec: Dict[str, Dict[str, Any]] = {}
    for etapa, blocos in blocos_por_etapa.items():
        ce = custos_por_etapa[etapa]
        por_etapa_exec[etapa] = {
            "etapa": etapa,
            "rotulo": rotulo_etapa(etapa),
            "tokens": _soma(blocos),
            "usd": round(ce["usd"], 4),
            "brl": round(ce["usd"] * cotacao, 2),
            "usd_entrada_sem_cache": round(ce["usd_entrada_sem_cache"], 4),
            "usd_cache": round(ce["usd_cache"], 4),
            "usd_saida": round(ce["usd_saida"], 4),
            "usd_pensamento": round(ce["usd_pensamento"], 4),
            "economia_cache_usd": round(ce["economia_cache_usd"], 4),
            "economia_cache_brl": round(ce["economia_cache_usd"] * cotacao, 2),
            "agentes": sorted(agentes_por_etapa.get(etapa) or []),
        }

    tokens_totais = _soma(list(agentes_detalhados.values()))
    por_modelo_exec: Dict[str, Dict[str, Any]] = {}
    for ag_d in agentes_detalhados.values():
        mod_k = str(ag_d.get("modelo") or modelo)
        bm = por_modelo_exec.setdefault(mod_k, {
            "modelo": mod_k,
            "tokens": enriquecer_tokens({}),
            "usd": 0.0,
            "brl": 0.0,
            "usd_entrada_sem_cache": 0.0,
            "usd_cache": 0.0,
            "usd_saida": 0.0,
            "usd_pensamento": 0.0,
            "economia_cache_usd": 0.0,
            "economia_cache_brl": 0.0,
        })
        bm["tokens"] = _soma([bm["tokens"], ag_d])
        bm["usd"] = round(bm["usd"] + float(ag_d.get("usd") or 0.0), 4)
        bm["brl"] = round(bm["brl"] + float(ag_d.get("brl") or 0.0), 2)
        bm["usd_entrada_sem_cache"] = round(bm["usd_entrada_sem_cache"] + float(ag_d.get("usd_entrada_sem_cache") or 0.0), 4)
        bm["usd_cache"] = round(bm["usd_cache"] + float(ag_d.get("usd_cache") or 0.0), 4)
        bm["usd_saida"] = round(bm["usd_saida"] + float(ag_d.get("usd_saida") or 0.0), 4)
        bm["usd_pensamento"] = round(bm["usd_pensamento"] + float(ag_d.get("usd_pensamento") or 0.0), 4)
        bm["economia_cache_usd"] = round(bm["economia_cache_usd"] + float(ag_d.get("economia_cache_usd") or 0.0), 4)
        bm["economia_cache_brl"] = round(bm["economia_cache_brl"] + float(ag_d.get("economia_cache_brl") or 0.0), 2)

    res_exec: Dict[str, Any] = {
        "modelo": modelo,
        "tokens": tokens_totais,
        "usd": round(usd, 4),
        "brl": round(usd * cotacao, 2),
        "cotacao": cotacao,
        "fonte_cotacao": fonte,
        "economia_cache_usd": round(economia_cache_usd, 4),
        "economia_cache_brl": round(economia_cache_usd * cotacao, 2),
        "detalhe_custos": {
            "usd_entrada_sem_cache": round(usd_entrada_sem_cache, 4),
            "usd_cache": round(usd_cache, 4),
            "usd_saida": round(usd_saida, 4),
            "usd_pensamento": round(usd_pensamento, 4),
            "usd_imagens": 0.0,
            "economia_cache_usd": round(economia_cache_usd, 4),
            "brl_entrada_sem_cache": round(usd_entrada_sem_cache * cotacao, 2),
            "brl_cache": round(usd_cache * cotacao, 2),
            "brl_saida": round(usd_saida * cotacao, 2),
            "brl_pensamento": round(usd_pensamento * cotacao, 2),
            "brl_imagens": 0.0,
            "economia_cache_brl": round(economia_cache_usd * cotacao, 2),
        },
        "modelos_sem_preco": sorted(sem_preco),
        "tokens_por_agente": agentes_detalhados,
        "por_etapa": por_etapa_exec,
        "por_modelo": por_modelo_exec,
    }
    if duracao_s is not None:
        res_exec["duracao_s"] = round(float(duracao_s), 1)
    return res_exec


def acumular(
    anterior: Optional[Dict[str, Any]],
    execucao: Dict[str, Any],
    etapas: List[str],
    quando: Optional[float] = None,
    tipo: str = "",
    duracao_s: Optional[float] = None,
) -> Dict[str, Any]:
    """`custo_missao` com a execução nova somada às anteriores, incluindo `por_etapa`, `por_agente` e `por_modelo`."""
    linhas = list((anterior or {}).get("execucoes") or [])
    item: Dict[str, Any] = {
        "quando": time.strftime("%d/%m/%Y %H:%M", time.localtime(quando or time.time())),
        "etapas": list(etapas),
        **execucao,
    }
    if tipo and "tipo" not in item:
        item["tipo"] = tipo
    if duracao_s is not None and "duracao_s" not in item:
        item["duracao_s"] = round(float(duracao_s), 1)
    linhas.append(item)

    resumo = detalhar_missao({"execucoes": linhas})
    return {
        "execucoes": linhas,
        "total": resumo["total"],
        "por_etapa": resumo["por_etapa"],
        "por_agente": resumo["por_agente"],
        "por_modelo": resumo["por_modelo"],
    }


def _normalizar_execucao_legada(
    linha: Dict[str, Any],
    idx: int,
    total_linhas: int,
    estado: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Garante que qualquer linha de `custo_missao.execucoes` (inclusive de sessões antigas sem `tokens_por_agente`
    ou sem `por_etapa`) tenha `tokens` enriquecido, `detalhe_custos`, `tokens_por_agente` e `por_etapa`."""
    cotacao = float(linha.get("cotacao") or COTACAO_PADRAO)
    etapas_raw = [normalizar_etapa(e) for e in (linha.get("etapas") or []) if e]
    etapas = list(dict.fromkeys(etapas_raw)) or ["produto"]
    modelo_padrao = str(linha.get("modelo") or (estado or {}).get("execucao", {}).get("modelo") or "gemini-3.8-flash")
    modelo_prd = str((estado or {}).get("execucao", {}).get("modelo_prd") or modelo_padrao)

    tpa = dict(linha.get("tokens_por_agente") or {})
    # Se for a última execução de uma sessão antiga e `estado["execucao"]["tokens_por_agente"]` tiver os agentes
    if not tpa and idx == total_linhas - 1 and isinstance(estado, dict):
        ex_est = estado.get("execucao")
        if isinstance(ex_est, dict) and ex_est.get("tokens_por_agente"):
            tpa_est = ex_est.get("tokens_por_agente") or {}
            soma_est = sum(int((v or {}).get("entrada", 0) or 0) for v in tpa_est.values())
            ent_linha = int((linha.get("tokens") or {}).get("entrada", 0) or 0)
            if soma_est == ent_linha and soma_est > 0:
                tpa = dict(tpa_est)

    imagens_info = linha.get("imagens") or {}
    qtd_imagens = int(imagens_info.get("quantidade", 0) or 0) if isinstance(imagens_info, dict) else 0
    usd_imagens = float(imagens_info.get("usd", 0.0) or 0.0) if isinstance(imagens_info, dict) else 0.0
    brl_imagens = round(usd_imagens * cotacao, 2)

    agentes_enriquecidos: Dict[str, Dict[str, Any]] = {}
    blocos_por_etapa: Dict[str, List[Dict[str, Any]]] = {}
    custos_por_etapa: Dict[str, Dict[str, float]] = {}
    agentes_por_etapa: Dict[str, List[str]] = {}

    usd_ent_sc_total = 0.0
    usd_cache_total = 0.0
    usd_saida_total = 0.0
    usd_pens_total = 0.0
    econ_usd_total = 0.0

    if tpa:
        for ag, tok_raw in tpa.items():
            tok = enriquecer_tokens(tok_raw)
            mod = str((tok_raw or {}).get("modelo") or (modelo_prd if ag == "A113PrdWriter" else modelo_padrao))
            if ag.startswith("hifi:") and not (tok_raw or {}).get("modelo"):
                mod = "gemini-4-argon"
            etapa = str((tok_raw or {}).get("etapa") or etapa_do_agente(ag, etapas))
            etapa = normalizar_etapa(etapa)
            det = detalhar_custo_usd(tok, mod, cotacao=cotacao)
            if det is None:
                c_usd = float((tok_raw or {}).get("usd", 0.0) or 0.0)
                det = {
                    "usd_entrada_sem_cache": 0.0,
                    "usd_cache": 0.0,
                    "usd_saida": c_usd,
                    "usd_pensamento": 0.0,
                    "economia_cache_usd": 0.0,
                    "usd": c_usd,
                    "economia_cache_brl": 0.0,
                }
            c_usd = det["usd"]
            usd_ent_sc_total += det["usd_entrada_sem_cache"]
            usd_cache_total += det["usd_cache"]
            usd_saida_total += det["usd_saida"]
            usd_pens_total += det["usd_pensamento"]
            econ_usd_total += det["economia_cache_usd"]

            agentes_enriquecidos[ag] = {
                **tok,
                "modelo": mod,
                "etapa": etapa,
                "rotulo": rotulo_do_agente(ag),
                "usd": round(c_usd, 6),
                "brl": round(c_usd * cotacao, 4),
                "usd_entrada_sem_cache": det["usd_entrada_sem_cache"],
                "usd_cache": det["usd_cache"],
                "usd_saida": det["usd_saida"],
                "usd_pensamento": det["usd_pensamento"],
                "economia_cache_usd": det["economia_cache_usd"],
                "economia_cache_brl": round(det["economia_cache_usd"] * cotacao, 4),
            }
            blocos_por_etapa.setdefault(etapa, []).append(tok)
            agentes_por_etapa.setdefault(etapa, []).append(ag)
            ce = custos_por_etapa.setdefault(etapa, {
                "usd": 0.0,
                "usd_entrada_sem_cache": 0.0,
                "usd_cache": 0.0,
                "usd_saida": 0.0,
                "usd_pensamento": 0.0,
                "usd_imagens": 0.0,
                "economia_cache_usd": 0.0,
            })
            ce["usd"] += c_usd
            ce["usd_entrada_sem_cache"] += det["usd_entrada_sem_cache"]
            ce["usd_cache"] += det["usd_cache"]
            ce["usd_saida"] += det["usd_saida"]
            ce["usd_pensamento"] += det["usd_pensamento"]
            ce["economia_cache_usd"] += det["economia_cache_usd"]
    else:
        # Execução legada sem `tokens_por_agente`: atribui à(s) etapa(s) registrada(s) na linha
        tok_linha = enriquecer_tokens(linha.get("tokens") or {})
        det = detalhar_custo_usd(tok_linha, modelo_padrao, cotacao=cotacao)
        usd_linha_sem_img = max(0.0, float(linha.get("usd", 0.0) or 0.0) - usd_imagens)
        if det is None:
            det = {
                "usd_entrada_sem_cache": 0.0,
                "usd_cache": 0.0,
                "usd_saida": usd_linha_sem_img,
                "usd_pensamento": 0.0,
                "economia_cache_usd": 0.0,
                "usd": usd_linha_sem_img,
            }
        usd_ent_sc_total = det["usd_entrada_sem_cache"]
        usd_cache_total = det["usd_cache"]
        usd_saida_total = det["usd_saida"]
        usd_pens_total = det["usd_pensamento"]
        econ_usd_total = det["economia_cache_usd"]

        etapa_alvo = etapas[0] if len(etapas) == 1 else ("produto" if "produto" in etapas else etapas[0])
        blocos_por_etapa[etapa_alvo] = [tok_linha]
        custos_por_etapa[etapa_alvo] = {
            "usd": usd_linha_sem_img,
            "usd_entrada_sem_cache": det["usd_entrada_sem_cache"],
            "usd_cache": det["usd_cache"],
            "usd_saida": det["usd_saida"],
            "usd_pensamento": det["usd_pensamento"],
            "usd_imagens": 0.0,
            "economia_cache_usd": det["economia_cache_usd"],
        }

    if usd_imagens > 0:
        etapa_img = "prototipo-hifi" if "prototipo-hifi" in etapas or "prototipo-hifi" in custos_por_etapa else etapas[0]
        blocos_por_etapa.setdefault(etapa_img, [])
        ce_img = custos_por_etapa.setdefault(etapa_img, {
            "usd": 0.0,
            "usd_entrada_sem_cache": 0.0,
            "usd_cache": 0.0,
            "usd_saida": 0.0,
            "usd_pensamento": 0.0,
            "usd_imagens": 0.0,
            "economia_cache_usd": 0.0,
        })
        ce_img["usd"] += usd_imagens
        ce_img["usd_imagens"] += usd_imagens

    por_etapa_exec: Dict[str, Dict[str, Any]] = {}
    for etapa, blocos in blocos_por_etapa.items():
        ce = custos_por_etapa[etapa]
        por_etapa_exec[etapa] = {
            "etapa": etapa,
            "rotulo": rotulo_etapa(etapa),
            "tokens": _soma(blocos),
            "usd": round(ce["usd"], 4),
            "brl": round(ce["usd"] * cotacao, 2),
            "usd_entrada_sem_cache": round(ce["usd_entrada_sem_cache"], 4),
            "usd_cache": round(ce["usd_cache"], 4),
            "usd_saida": round(ce["usd_saida"], 4),
            "usd_pensamento": round(ce["usd_pensamento"], 4),
            "usd_imagens": round(ce.get("usd_imagens", 0.0), 4),
            "economia_cache_usd": round(ce["economia_cache_usd"], 4),
            "economia_cache_brl": round(ce["economia_cache_usd"] * cotacao, 2),
            "agentes": sorted(agentes_por_etapa.get(etapa) or []),
        }

    tokens_exec = enriquecer_tokens(linha.get("tokens") or _soma(list(agentes_enriquecidos.values())))
    # Se `maior_entrada` não estava salvo no topo da execução, pega o máximo entre os agentes
    if tokens_exec["maior_entrada"] == 0 and agentes_enriquecidos:
        tokens_exec["maior_entrada"] = max((a["maior_entrada"] for a in agentes_enriquecidos.values()), default=0)

    usd_exec = round(
        float(linha.get("usd") or (usd_ent_sc_total + usd_cache_total + usd_saida_total + usd_pens_total + usd_imagens)),
        4,
    )
    brl_exec = round(float(linha.get("brl") or (usd_exec * cotacao)), 2)

    return {
        **linha,
        "indice": idx + 1,
        "etapas": etapas,
        "modelo": modelo_padrao,
        "tokens": tokens_exec,
        "usd": usd_exec,
        "brl": brl_exec,
        "cotacao": cotacao,
        "fonte_cotacao": str(linha.get("fonte_cotacao") or ""),
        "imagens": {"quantidade": qtd_imagens, "usd": round(usd_imagens, 4), "brl": brl_imagens},
        "detalhe_custos": {
            "usd_entrada_sem_cache": round(usd_ent_sc_total, 4),
            "usd_cache": round(usd_cache_total, 4),
            "usd_saida": round(usd_saida_total, 4),
            "usd_pensamento": round(usd_pens_total, 4),
            "usd_imagens": round(usd_imagens, 4),
            "economia_cache_usd": round(econ_usd_total, 4),
            "brl_entrada_sem_cache": round(usd_ent_sc_total * cotacao, 2),
            "brl_cache": round(usd_cache_total * cotacao, 2),
            "brl_saida": round(usd_saida_total * cotacao, 2),
            "brl_pensamento": round(usd_pens_total * cotacao, 2),
            "brl_imagens": brl_imagens,
            "economia_cache_brl": round(econ_usd_total * cotacao, 2),
        },
        "tokens_por_agente": agentes_enriquecidos,
        "por_etapa": por_etapa_exec,
    }


def detalhar_missao(
    custo_missao: Optional[Dict[str, Any]],
    estado: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Reconstrói e enriquece todo o histórico de custo e tokens de uma missão:
    totais globais, quebra por etapa (`por_etapa`), quebra por agente (`por_agente`),
    quebra por modelo (`por_modelo`), execuções detalhadas (`execucoes`) e classificador semântico.
    Aceita tanto `custo_missao` quanto o dicionário `estado` completo no primeiro argumento."""
    cm = custo_missao if isinstance(custo_missao, dict) else {}
    if cm and "execucoes" not in cm and (KEY_CUSTO in cm or "execucao" in cm or "one_pager" in cm or "spec_missao" in cm):
        if estado is None:
            estado = cm
        cm = cm.get(KEY_CUSTO) if isinstance(cm.get(KEY_CUSTO), dict) else {}
    if not cm and isinstance(estado, dict):
        cm = estado.get(KEY_CUSTO) if isinstance(estado.get(KEY_CUSTO), dict) else {}

    linhas_brutas = list(cm.get("execucoes") or [])
    # Fallback para sessões muito antigas que só tinham `estado["execucao"]`
    if not linhas_brutas and isinstance(estado, dict) and isinstance(estado.get("execucao"), dict):
        ex = estado["execucao"]
        c_ex = ex.get("custo") or {}
        if c_ex or ex.get("tokens"):
            linhas_brutas = [{
                "quando": "execução única",
                "etapas": ["produto", "design", "dev", "transversal"],
                "modelo": ex.get("modelo") or "gemini-3.8-flash",
                "duracao_s": ex.get("duracao_s"),
                "tokens": ex.get("tokens") or c_ex.get("tokens") or {},
                "usd": c_ex.get("usd", 0.0),
                "brl": c_ex.get("brl", 0.0),
                "cotacao": c_ex.get("cotacao", COTACAO_PADRAO),
                "fonte_cotacao": c_ex.get("fonte_cotacao", ""),
                "tokens_por_agente": ex.get("tokens_por_agente") or c_ex.get("tokens_por_agente") or {},
            }]

    execucoes = [
        _normalizar_execucao_legada(l, idx, len(linhas_brutas), estado=estado)
        for idx, l in enumerate(linhas_brutas)
    ]

    tokens_total = _soma([e["tokens"] for e in execucoes])
    usd_total = round(sum(float(e["usd"] or 0.0) for e in execucoes), 4)
    brl_total = round(sum(float(e["brl"] or 0.0) for e in execucoes), 2)

    det_chaves = (
        "usd_entrada_sem_cache", "usd_cache", "usd_saida", "usd_pensamento", "usd_imagens", "economia_cache_usd",
        "brl_entrada_sem_cache", "brl_cache", "brl_saida", "brl_pensamento", "brl_imagens", "economia_cache_brl",
    )
    det_totais = {
        k: round(
            sum(float((e.get("detalhe_custos") or {}).get(k, 0.0) or 0.0) for e in execucoes),
            4 if k.startswith("usd") or "usd" in k else 2,
        )
        for k in det_chaves
    }
    qtd_imagens_total = sum(int((e.get("imagens") or {}).get("quantidade", 0) or 0) for e in execucoes)
    duracao_total_s = round(sum(float(e.get("duracao_s", 0.0) or 0.0) for e in execucoes), 1)
    execucoes_falhas = sum(1 for e in execucoes if e.get("falhou"))

    # Agrupamento por agente em toda a missão
    agentes_acum: Dict[str, Dict[str, Any]] = {}
    modelos_acum: Dict[str, Dict[str, Any]] = {}

    for e in execucoes:
        for ag, dados_ag in (e.get("tokens_por_agente") or {}).items():
            etapa_ag = dados_ag.get("etapa") or etapa_do_agente(ag, e.get("etapas"))
            mod_ag = dados_ag.get("modelo") or e.get("modelo") or "gemini-3.8-flash"
            atual = agentes_acum.get(ag)
            if atual is None:
                agentes_acum[ag] = {
                    "agente": ag,
                    "rotulo": rotulo_do_agente(ag),
                    "etapa": etapa_ag,
                    "rotulo_etapa": rotulo_etapa(etapa_ag),
                    "modelo": mod_ag,
                    "execucoes_count": 1,
                    "tokens": enriquecer_tokens(dados_ag),
                    "usd": float(dados_ag.get("usd", 0.0) or 0.0),
                    "brl": float(dados_ag.get("brl", 0.0) or 0.0),
                    "usd_entrada_sem_cache": float(dados_ag.get("usd_entrada_sem_cache", 0.0) or 0.0),
                    "usd_cache": float(dados_ag.get("usd_cache", 0.0) or 0.0),
                    "usd_saida": float(dados_ag.get("usd_saida", 0.0) or 0.0),
                    "usd_pensamento": float(dados_ag.get("usd_pensamento", 0.0) or 0.0),
                    "economia_cache_usd": float(dados_ag.get("economia_cache_usd", 0.0) or 0.0),
                    "economia_cache_brl": float(dados_ag.get("economia_cache_brl", 0.0) or 0.0),
                }
            else:
                atual["execucoes_count"] += 1
                atual["tokens"] = _soma([atual["tokens"], dados_ag])
                atual["usd"] += float(dados_ag.get("usd", 0.0) or 0.0)
                atual["brl"] += float(dados_ag.get("brl", 0.0) or 0.0)
                atual["usd_entrada_sem_cache"] += float(dados_ag.get("usd_entrada_sem_cache", 0.0) or 0.0)
                atual["usd_cache"] += float(dados_ag.get("usd_cache", 0.0) or 0.0)
                atual["usd_saida"] += float(dados_ag.get("usd_saida", 0.0) or 0.0)
                atual["usd_pensamento"] += float(dados_ag.get("usd_pensamento", 0.0) or 0.0)
                atual["economia_cache_usd"] += float(dados_ag.get("economia_cache_usd", 0.0) or 0.0)
                atual["economia_cache_brl"] += float(dados_ag.get("economia_cache_brl", 0.0) or 0.0)

            # Acumula por modelo
            m_entry = modelos_acum.setdefault(mod_ag, {
                "modelo": mod_ag,
                "tokens": enriquecer_tokens({}),
                "usd": 0.0,
                "brl": 0.0,
                "usd_entrada_sem_cache": 0.0,
                "usd_cache": 0.0,
                "usd_saida": 0.0,
                "usd_pensamento": 0.0,
                "economia_cache_usd": 0.0,
                "economia_cache_brl": 0.0,
                "imagens": 0,
            })
            m_entry["tokens"] = _soma([m_entry["tokens"], dados_ag])
            m_entry["usd"] += float(dados_ag.get("usd", 0.0) or 0.0)
            m_entry["brl"] += float(dados_ag.get("brl", 0.0) or 0.0)
            m_entry["usd_entrada_sem_cache"] += float(dados_ag.get("usd_entrada_sem_cache", 0.0) or 0.0)
            m_entry["usd_cache"] += float(dados_ag.get("usd_cache", 0.0) or 0.0)
            m_entry["usd_saida"] += float(dados_ag.get("usd_saida", 0.0) or 0.0)
            m_entry["usd_pensamento"] += float(dados_ag.get("usd_pensamento", 0.0) or 0.0)
            m_entry["economia_cache_usd"] += float(dados_ag.get("economia_cache_usd", 0.0) or 0.0)
            m_entry["economia_cache_brl"] += float(dados_ag.get("economia_cache_brl", 0.0) or 0.0)

        if (e.get("imagens") or {}).get("quantidade", 0) > 0:
            im = e["imagens"]
            m_img = modelos_acum.setdefault("gemini-3.1-flash-lite-image", {
                "modelo": "gemini-3.1-flash-lite-image",
                "tokens": enriquecer_tokens({}),
                "usd": 0.0,
                "brl": 0.0,
                "economia_cache_usd": 0.0,
                "economia_cache_brl": 0.0,
                "imagens": 0,
            })
            m_img["imagens"] += int(im.get("quantidade", 0) or 0)
            m_img["usd"] += float(im.get("usd", 0.0) or 0.0)
            m_img["brl"] += float(im.get("brl", 0.0) or 0.0)

    por_agente_lista: List[Dict[str, Any]] = []
    for ag, d in sorted(agentes_acum.items(), key=lambda kv: (-kv[1]["usd"], -kv[1]["tokens"]["total_tokens"])):
        pct = round((d["usd"] / usd_total) * 100.0, 1) if usd_total > 0 else 0.0
        por_agente_lista.append({
            **d,
            "usd": round(d["usd"], 4),
            "brl": round(d["brl"], 2),
            "usd_entrada_sem_cache": round(d["usd_entrada_sem_cache"], 4),
            "usd_cache": round(d["usd_cache"], 4),
            "usd_saida": round(d["usd_saida"], 4),
            "usd_pensamento": round(d["usd_pensamento"], 4),
            "economia_cache_usd": round(d["economia_cache_usd"], 4),
            "economia_cache_brl": round(d["economia_cache_brl"], 2),
            "pct_missao": pct,
        })

    # Agrupamento por etapa em toda a missão
    etapas_vistas: List[str] = list(ETAPAS_PRINCIPAIS)
    for e in execucoes:
        for et in (e.get("por_etapa") or {}).keys():
            if et not in etapas_vistas:
                etapas_vistas.append(et)
    etapas_ordenadas = sorted(
        etapas_vistas,
        key=lambda x: ORDEM_ETAPAS_CUSTO.index(x) if x in ORDEM_ETAPAS_CUSTO else 99,
    )

    por_etapa: Dict[str, Dict[str, Any]] = {}
    for et in etapas_ordenadas:
        blocos_et: List[Dict[str, Any]] = []
        execucoes_et: List[Dict[str, Any]] = []
        usd_et = 0.0
        brl_et = 0.0
        usd_ent_sc_et = 0.0
        usd_cache_et = 0.0
        usd_saida_et = 0.0
        usd_pens_et = 0.0
        usd_img_et = 0.0
        econ_usd_et = 0.0
        econ_brl_et = 0.0
        imgs_qtd_et = 0

        for e in execucoes:
            pe = (e.get("por_etapa") or {}).get(et)
            if not pe:
                continue
            blocos_et.append(pe.get("tokens") or {})
            usd_et += float(pe.get("usd", 0.0) or 0.0)
            brl_et += float(pe.get("brl", 0.0) or 0.0)
            usd_ent_sc_et += float(pe.get("usd_entrada_sem_cache", 0.0) or 0.0)
            usd_cache_et += float(pe.get("usd_cache", 0.0) or 0.0)
            usd_saida_et += float(pe.get("usd_saida", 0.0) or 0.0)
            usd_pens_et += float(pe.get("usd_pensamento", 0.0) or 0.0)
            usd_img_et += float(pe.get("usd_imagens", 0.0) or 0.0)
            econ_usd_et += float(pe.get("economia_cache_usd", 0.0) or 0.0)
            econ_brl_et += float(pe.get("economia_cache_brl", 0.0) or 0.0)
            if et == "prototipo-hifi":
                imgs_qtd_et += int((e.get("imagens") or {}).get("quantidade", 0) or 0)
            execucoes_et.append({
                "indice": e.get("indice"),
                "quando": e.get("quando", ""),
                "tipo": e.get("tipo", ""),
                "falhou": bool(e.get("falhou")),
                "tokens": pe.get("tokens") or enriquecer_tokens({}),
                "usd": round(float(pe.get("usd", 0.0) or 0.0), 4),
                "brl": round(float(pe.get("brl", 0.0) or 0.0), 2),
                "economia_cache_brl": round(float(pe.get("economia_cache_brl", 0.0) or 0.0), 2),
                "agentes_count": len(pe.get("agentes") or []),
            })

        agentes_da_etapa = [a for a in por_agente_lista if a["etapa"] == et]
        for a in agentes_da_etapa:
            a["pct_etapa"] = round((a["usd"] / usd_et) * 100.0, 1) if usd_et > 0 else 0.0

        tok_et = _soma(blocos_et)
        pct_custo = round((usd_et / usd_total) * 100.0, 1) if usd_total > 0 else 0.0
        por_etapa[et] = {
            "etapa": et,
            "rotulo": rotulo_etapa(et),
            "tokens": tok_et,
            "usd": round(usd_et, 4),
            "brl": round(brl_et, 2),
            "pct_custo": pct_custo,
            "usd_entrada_sem_cache": round(usd_ent_sc_et, 4),
            "usd_cache": round(usd_cache_et, 4),
            "usd_saida": round(usd_saida_et, 4),
            "usd_pensamento": round(usd_pens_et, 4),
            "usd_imagens": round(usd_img_et, 4),
            "economia_cache_usd": round(econ_usd_et, 4),
            "economia_cache_brl": round(econ_brl_et, 2),
            "imagens_quantidade": imgs_qtd_et,
            "execucoes_count": len(execucoes_et),
            "execucoes": execucoes_et,
            "agentes": agentes_da_etapa,
        }

    por_modelo: Dict[str, Dict[str, Any]] = {}
    for mod, m_d in sorted(modelos_acum.items(), key=lambda kv: -kv[1]["usd"]):
        por_modelo[mod] = {
            **m_d,
            "usd": round(m_d["usd"], 4),
            "brl": round(m_d["brl"], 2),
            "usd_entrada_sem_cache": round(m_d.get("usd_entrada_sem_cache", 0.0), 4),
            "usd_cache": round(m_d.get("usd_cache", 0.0), 4),
            "usd_saida": round(m_d.get("usd_saida", 0.0), 4),
            "usd_pensamento": round(m_d.get("usd_pensamento", 0.0), 4),
            "economia_cache_usd": round(m_d["economia_cache_usd"], 4),
            "economia_cache_brl": round(m_d["economia_cache_brl"], 2),
            "pct_custo": round((m_d["usd"] / usd_total) * 100.0, 1) if usd_total > 0 else 0.0,
        }

    # Dados do classificador semântico (se `estado` fornecido)
    cls_info: Dict[str, Any] = {}
    if isinstance(estado, dict):
        cls_reg = (
            (estado.get("classificador_sentido") or {}).get("custo")
            if isinstance(estado.get("classificador_sentido"), dict)
            else None
        )
        if isinstance(cls_reg, dict) and cls_reg:
            cls_info = {
                "chamadas": int(cls_reg.get("chamadas", 0) or 0),
                "tokens": enriquecer_tokens(cls_reg.get("tokens") or {}),
                "usd": round(float(cls_reg.get("usd", 0.0) or 0.0), 4),
                "por_gate": dict(cls_reg.get("por_gate") or {}),
            }

    tem_dados = bool(tokens_total["total_tokens"] > 0 or usd_total > 0 or len(execucoes) > 0)
    modelos_sem_preco_missao = sorted({m for e in execucoes for m in (e.get("modelos_sem_preco") or [])})

    total_bloco = {
        "tokens": tokens_total,
        "usd": usd_total,
        "brl": brl_total,
        **det_totais,
        "imagens": {
            "quantidade": qtd_imagens_total,
            "usd": det_totais["usd_imagens"],
            "brl": det_totais["brl_imagens"],
        },
        "execucoes_count": len(execucoes),
        "execucoes_falhas": execucoes_falhas,
        "duracao_total_s": duracao_total_s,
    }

    return {
        "tem_dados": tem_dados,
        "num_execucoes": len(execucoes),
        "tokens": tokens_total,
        "usd": usd_total,
        "brl": brl_total,
        **det_totais,
        "modelos_sem_preco": modelos_sem_preco_missao,
        "total": total_bloco,
        "por_etapa": por_etapa,
        "por_agente": por_agente_lista,
        "por_modelo": por_modelo,
        "execucoes": execucoes,
        "classificador": cls_info,
    }


def resumo_indexado(custo_missao: Optional[Dict[str, Any]], estado: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Resumo leve de `custo_missao` para guardar em `conversa.json` e carregar rapidamente na listagem de sessões."""
    det = detalhar_missao(custo_missao, estado=estado)
    tot = det["total"]
    por_etapa_resumo = {
        et: {
            "usd": dados["usd"],
            "brl": dados["brl"],
            "tokens": dados["tokens"],
            "economia_cache_brl": dados["economia_cache_brl"],
            "execucoes_count": dados["execucoes_count"],
        }
        for et, dados in (det.get("por_etapa") or {}).items()
        if dados["tokens"]["total_tokens"] > 0 or dados["usd"] > 0
    }
    return {
        "usd": tot["usd"],
        "brl": tot["brl"],
        "economia_cache_usd": tot["economia_cache_usd"],
        "economia_cache_brl": tot["economia_cache_brl"],
        "usd_entrada_sem_cache": tot["usd_entrada_sem_cache"],
        "usd_cache": tot["usd_cache"],
        "usd_saida": tot["usd_saida"],
        "usd_pensamento": tot["usd_pensamento"],
        "usd_imagens": tot["usd_imagens"],
        "imagens_quantidade": tot["imagens"]["quantidade"],
        "execucoes_count": tot["execucoes_count"],
        "execucoes_falhas": tot["execucoes_falhas"],
        "duracao_total_s": tot["duracao_total_s"],
        "tokens": tot["tokens"],
        "por_etapa": por_etapa_resumo,
    }


def consolidar_missoes(sessoes: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Consolida os custos e tokens de todas as missões para o painel administrativo (`sessao.papel == 'admin'`).

    Cada item de `sessoes` pode conter `custo_missao`, `estado` ou `custo_resumo`, além dos metadados da sessão
    (`dir_name`, `slug`, `prompt`, `created_display`, `created_at`, `user_id`, `status`, `fluxo`).
    """
    missoes_detalhadas: List[Dict[str, Any]] = []
    blocos_tokens_global: List[Dict[str, Any]] = []

    usd_global = 0.0
    brl_global = 0.0
    econ_usd_global = 0.0
    econ_brl_global = 0.0
    usd_ent_sc_global = 0.0
    usd_cache_global = 0.0
    usd_saida_global = 0.0
    usd_pens_global = 0.0
    usd_img_global = 0.0
    imgs_qtd_global = 0
    execucoes_global = 0
    falhas_global = 0
    duracao_global_s = 0.0

    etapas_global: Dict[str, Dict[str, Any]] = {}
    modelos_global: Dict[str, Dict[str, Any]] = {}
    agentes_global: Dict[str, Dict[str, Any]] = {}

    for s in sessoes:
        estado = s.get("estado") if isinstance(s.get("estado"), dict) else None
        cm = s.get("custo_missao") if isinstance(s.get("custo_missao"), dict) else None
        det = detalhar_missao(cm, estado=estado)
        tot = det["total"]
        tok = tot["tokens"]

        tem_uso = tok["total_tokens"] > 0 or tot["usd"] > 0 or tot["execucoes_count"] > 0
        if tem_uso:
            blocos_tokens_global.append(tok)
            usd_global += tot["usd"]
            brl_global += tot["brl"]
            econ_usd_global += tot["economia_cache_usd"]
            econ_brl_global += tot["economia_cache_brl"]
            usd_ent_sc_global += tot["usd_entrada_sem_cache"]
            usd_cache_global += tot["usd_cache"]
            usd_saida_global += tot["usd_saida"]
            usd_pens_global += tot["usd_pensamento"]
            usd_img_global += tot["usd_imagens"]
            imgs_qtd_global += tot["imagens"]["quantidade"]
            execucoes_global += tot["execucoes_count"]
            falhas_global += tot["execucoes_falhas"]
            duracao_global_s += tot["duracao_total_s"]

        # Acumula por etapa
        for et, pe in (det.get("por_etapa") or {}).items():
            if pe["tokens"]["total_tokens"] == 0 and pe["usd"] == 0:
                continue
            eg = etapas_global.setdefault(et, {
                "etapa": et,
                "rotulo": rotulo_etapa(et),
                "missoes_count": 0,
                "execucoes_count": 0,
                "tokens": enriquecer_tokens({}),
                "usd": 0.0,
                "brl": 0.0,
                "usd_entrada_sem_cache": 0.0,
                "usd_cache": 0.0,
                "usd_saida": 0.0,
                "usd_pensamento": 0.0,
                "usd_imagens": 0.0,
                "economia_cache_usd": 0.0,
                "economia_cache_brl": 0.0,
                "imagens_quantidade": 0,
            })
            eg["missoes_count"] += 1
            eg["execucoes_count"] += pe["execucoes_count"]
            eg["tokens"] = _soma([eg["tokens"], pe["tokens"]])
            eg["usd"] += pe["usd"]
            eg["brl"] += pe["brl"]
            eg["usd_entrada_sem_cache"] += pe["usd_entrada_sem_cache"]
            eg["usd_cache"] += pe["usd_cache"]
            eg["usd_saida"] += pe["usd_saida"]
            eg["usd_pensamento"] += pe["usd_pensamento"]
            eg["usd_imagens"] += pe["usd_imagens"]
            eg["economia_cache_usd"] += pe["economia_cache_usd"]
            eg["economia_cache_brl"] += pe["economia_cache_brl"]
            eg["imagens_quantidade"] += pe.get("imagens_quantidade", 0)

        # Acumula por modelo
        for mod, pm in (det.get("por_modelo") or {}).items():
            mg = modelos_global.setdefault(mod, {
                "modelo": mod,
                "missoes_count": 0,
                "tokens": enriquecer_tokens({}),
                "usd": 0.0,
                "brl": 0.0,
                "usd_entrada_sem_cache": 0.0,
                "usd_cache": 0.0,
                "usd_saida": 0.0,
                "usd_pensamento": 0.0,
                "economia_cache_usd": 0.0,
                "economia_cache_brl": 0.0,
                "imagens": 0,
            })
            mg["missoes_count"] += 1
            mg["tokens"] = _soma([mg["tokens"], pm["tokens"]])
            mg["usd"] += pm["usd"]
            mg["brl"] += pm["brl"]
            mg["usd_entrada_sem_cache"] += float(pm.get("usd_entrada_sem_cache", 0.0) or 0.0)
            mg["usd_cache"] += float(pm.get("usd_cache", 0.0) or 0.0)
            mg["usd_saida"] += float(pm.get("usd_saida", 0.0) or 0.0)
            mg["usd_pensamento"] += float(pm.get("usd_pensamento", 0.0) or 0.0)
            mg["economia_cache_usd"] += pm["economia_cache_usd"]
            mg["economia_cache_brl"] += pm["economia_cache_brl"]
            mg["imagens"] += pm.get("imagens", 0)

        # Acumula por agente
        for pa in det.get("por_agente") or []:
            ag = pa["agente"]
            ag_g = agentes_global.setdefault(ag, {
                "agente": ag,
                "rotulo": pa["rotulo"],
                "etapa": pa["etapa"],
                "rotulo_etapa": pa["rotulo_etapa"],
                "modelo": pa["modelo"],
                "missoes_count": 0,
                "execucoes_count": 0,
                "tokens": enriquecer_tokens({}),
                "usd": 0.0,
                "brl": 0.0,
                "economia_cache_usd": 0.0,
                "economia_cache_brl": 0.0,
            })
            ag_g["missoes_count"] += 1
            ag_g["execucoes_count"] += pa["execucoes_count"]
            ag_g["tokens"] = _soma([ag_g["tokens"], pa["tokens"]])
            ag_g["usd"] += pa["usd"]
            ag_g["brl"] += pa["brl"]
            ag_g["economia_cache_usd"] += pa["economia_cache_usd"]
            ag_g["economia_cache_brl"] += pa["economia_cache_brl"]

        pe_map = det.get("por_etapa") or {}
        missoes_detalhadas.append({
            "dir_name": s.get("dir_name", ""),
            "session_id": s.get("session_id", ""),
            "title": s.get("title") or s.get("slug") or s.get("dir_name", "Missão"),
            "slug": s.get("slug") or s.get("dir_name", ""),
            "prompt": s.get("prompt", ""),
            "created_display": s.get("created_display", ""),
            "created_at": s.get("created_at", ""),
            "user_id": s.get("user_id", ""),
            "status": s.get("status", ""),
            "status_label": s.get("status_label") or s.get("status", ""),
            "status_icon": s.get("status_icon", ""),
            "excluida": bool(s.get("excluida")),
            "excluida_em": str(s.get("excluida_em") or ""),
            "prd_gerado": bool(s.get("prd_gerado") or s.get("has_prd")),
            "tem_custo": tem_uso,
            "tem_dados": tem_uso,
            "num_execucoes": tot["execucoes_count"],
            "execucoes_count": tot["execucoes_count"],
            "execucoes_falhas": tot["execucoes_falhas"],
            "duracao_total_s": tot["duracao_total_s"],
            "usd": tot["usd"],
            "brl": tot["brl"],
            "economia_cache_usd": tot["economia_cache_usd"],
            "economia_cache_brl": tot["economia_cache_brl"],
            "imagens_quantidade": tot["imagens"]["quantidade"],
            "tokens": tok,
            "por_etapa": pe_map,
            "execucoes": det.get("execucoes") or [],
            "custo_produto_brl": (pe_map.get("produto") or {}).get("brl", 0.0),
            "custo_design_brl": (pe_map.get("design") or {}).get("brl", 0.0),
            "custo_dev_brl": (pe_map.get("dev") or {}).get("brl", 0.0),
            "custo_transversal_brl": (pe_map.get("transversal") or {}).get("brl", 0.0),
            "custo_hifi_brl": (pe_map.get("prototipo-hifi") or {}).get("brl", 0.0),
            "custo_outros_brl": round(sum(
                v.get("brl", 0.0) for k, v in pe_map.items()
                if k not in ("produto", "design", "dev", "transversal", "prototipo-hifi")
            ), 2),
            "custo_produto_usd": (pe_map.get("produto") or {}).get("usd", 0.0),
            "custo_design_usd": (pe_map.get("design") or {}).get("usd", 0.0),
            "custo_dev_usd": (pe_map.get("dev") or {}).get("usd", 0.0),
            "custo_transversal_usd": (pe_map.get("transversal") or {}).get("usd", 0.0),
            "custo_hifi_usd": (pe_map.get("prototipo-hifi") or {}).get("usd", 0.0),
            "detalhe": det,
        })

    tokens_global = _soma(blocos_tokens_global)
    missoes_com_custo = sum(1 for m in missoes_detalhadas if m["tem_custo"])

    por_etapa_global: Dict[str, Dict[str, Any]] = {}
    for et in sorted(etapas_global.keys(), key=lambda x: ORDEM_ETAPAS_CUSTO.index(x) if x in ORDEM_ETAPAS_CUSTO else 99):
        eg = etapas_global[et]
        mc = max(1, eg["missoes_count"])
        pct_g = round((eg["usd"] / usd_global) * 100.0, 1) if usd_global > 0 else 0.0
        media_brl = round(eg["brl"] / mc, 2)
        por_etapa_global[et] = {
            **eg,
            "missoes_com_etapa": eg["missoes_count"],
            "usd": round(eg["usd"], 4),
            "brl": round(eg["brl"], 2),
            "usd_entrada_sem_cache": round(eg["usd_entrada_sem_cache"], 4),
            "usd_cache": round(eg["usd_cache"], 4),
            "usd_saida": round(eg["usd_saida"], 4),
            "usd_pensamento": round(eg["usd_pensamento"], 4),
            "usd_imagens": round(eg["usd_imagens"], 4),
            "economia_cache_usd": round(eg["economia_cache_usd"], 4),
            "economia_cache_brl": round(eg["economia_cache_brl"], 2),
            "media_brl": media_brl,
            "media_brl_por_missao": media_brl,
            "media_usd_por_missao": round(eg["usd"] / mc, 4),
            "pct_custo": pct_g,
            "pct_custo_global": pct_g,
        }

    por_modelo_global: Dict[str, Dict[str, Any]] = {}
    for mod, mg in sorted(modelos_global.items(), key=lambda kv: -kv[1]["usd"]):
        pct_m = round((mg["usd"] / usd_global) * 100.0, 1) if usd_global > 0 else 0.0
        por_modelo_global[mod] = {
            **mg,
            "usd": round(mg["usd"], 4),
            "brl": round(mg["brl"], 2),
            "usd_entrada_sem_cache": round(mg.get("usd_entrada_sem_cache", 0.0), 4),
            "usd_cache": round(mg.get("usd_cache", 0.0), 4),
            "usd_saida": round(mg.get("usd_saida", 0.0), 4),
            "usd_pensamento": round(mg.get("usd_pensamento", 0.0), 4),
            "economia_cache_usd": round(mg["economia_cache_usd"], 4),
            "economia_cache_brl": round(mg["economia_cache_brl"], 2),
            "pct_custo": pct_m,
            "pct_custo_global": pct_m,
        }

    por_agente_global: List[Dict[str, Any]] = []
    for ag, ag_g in sorted(agentes_global.items(), key=lambda kv: (-kv[1]["usd"], -kv[1]["tokens"]["total_tokens"])):
        pct_a = round((ag_g["usd"] / usd_global) * 100.0, 1) if usd_global > 0 else 0.0
        por_agente_global.append({
            **ag_g,
            "missoes": ag_g["missoes_count"],
            "usd": round(ag_g["usd"], 4),
            "brl": round(ag_g["brl"], 2),
            "economia_cache_usd": round(ag_g["economia_cache_usd"], 4),
            "economia_cache_brl": round(ag_g["economia_cache_brl"], 2),
            "pct_custo": pct_a,
            "pct_custo_global": pct_a,
        })

    divisor_missoes = max(1, missoes_com_custo)
    totais_globais = {
        "num_missoes": len(missoes_detalhadas),
        "missoes_total": len(missoes_detalhadas),
        "missoes_com_custo": missoes_com_custo,
        "num_execucoes": execucoes_global,
        "execucoes_total": execucoes_global,
        "execucoes_falhas": falhas_global,
        "duracao_total_s": round(duracao_global_s, 1),
        "usd": round(usd_global, 4),
        "brl": round(brl_global, 2),
        "media_usd_por_missao": round(usd_global / divisor_missoes, 4) if missoes_com_custo else 0.0,
        "media_brl_por_missao": round(brl_global / divisor_missoes, 2) if missoes_com_custo else 0.0,
        "economia_cache_usd": round(econ_usd_global, 4),
        "economia_cache_brl": round(econ_brl_global, 2),
        "usd_entrada_sem_cache": round(usd_ent_sc_global, 4),
        "usd_cache": round(usd_cache_global, 4),
        "usd_saida": round(usd_saida_global, 4),
        "usd_pensamento": round(usd_pens_global, 4),
        "usd_imagens": round(usd_img_global, 4),
        "imagens_quantidade": imgs_qtd_global,
        "tokens": tokens_global,
    }

    return {
        **totais_globais,
        "totais": totais_globais,
        "por_etapa": por_etapa_global,
        "por_modelo": por_modelo_global,
        "por_agente": por_agente_global,
        "missoes": missoes_detalhadas,
    }


def brl(valor: float) -> str:
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def usd_fmt(valor: float, casas: int = 2) -> str:
    return f"US$ {valor:,.{casas}f}"


def milhares(n: int) -> str:
    return f"{int(n or 0):,}".replace(",", ".")


def texto_ao_vivo(execucao: Optional[Dict[str, Any]], missao_antes: Optional[Dict[str, Any]]) -> str:
    """`💰 R$ 3,42 nesta execução · R$ 18,90 na missão · 1.234.567 de entrada (62% cache) · 85.432 de saída`."""
    if not execucao:
        return ""
    t = enriquecer_tokens(execucao.get("tokens") or {})
    agora = float(execucao.get("brl") or 0)
    total = agora + float((missao_antes or {}).get("brl") or 0)
    info_cache = f" ({t['taxa_cache_pct']:.0f}% cache)" if t["cache"] > 0 else ""
    info_pens = f" ({milhares(t['pensamento'])} pens.)" if t["pensamento"] > 0 else ""
    return (
        f"💰 {brl(agora)} nesta execução · {brl(total)} na missão · "
        f"{milhares(t['entrada'])} de entrada{info_cache} · "
        f"{milhares(t['saida_total'])} de saída{info_pens}"
    )
