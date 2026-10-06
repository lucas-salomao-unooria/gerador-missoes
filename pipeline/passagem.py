"""Parecer humano entre as etapas da esteira: quem pode o quê, e o que acontece depois.

Cada etapa (produto → design → dev) tem um dono. Quando ela termina de gerar, o dono dá o
**parecer**: *de acordo* (libera para a próxima, com um comentário que registra as contribuições
dele) ou *refazer* (o comentário vira o pedido de correção e a etapa é refeita na mesma sessão). O
dono da etapa seguinte faz o **recebimento**: *iniciar* a etapa dele ou *devolver* à anterior. A
devolução não refaz nada sozinha: reabre o parecer do dono anterior, que decide.

O semáforo automático (🟢🟡🔴) continua valendo: com um gate da etapa em 🔴, *de acordo* é
recusado, e só o `admin` pode liberar com exceção, que fica registrada.

Tudo aqui é determinístico e sem Streamlit. `aplicar` é pura: recebe o fluxo e devolve o fluxo
novo mais o **efeito** que alguém precisa executar (rodar a etapa, refazê-la, encerrar a missão).
Quem executa é `pipeline/execucao_fundo.py`; quem desenha os botões é o `app.py`.

O fluxo vive em `conversa.json["fluxo"]`:

    {"etapa": "design", "situacao": "liberada", "versao": 3, "atualizado_em": "23/09/2026 14:02:11",
     "pareceres": [{"etapa": "produto", "acao": "de_acordo", "autor": "produto", "como": "produto",
                    "comentario": "…", "quando": "…", "rodada": 1, "assinatura": "…",
                    "valido": true, "gates": {"gate_final_status": "🟢"}, "excecao": false}]}
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ORDEM: Tuple[str, ...] = ("produto", "design", "dev")
ROTULO_ETAPA = {"produto": "Produto", "design": "Design", "dev": "Dev"}

#: Quem responde por cada etapa, além do `admin`. O design também gera e dá parecer em produto
#: (decisão de 24/09/2026): ele costuma abrir a missão e seguir até o fim do design. O dev só age no dev.
PAPEIS_DA_ETAPA: Dict[str, Tuple[str, ...]] = {"produto": ("produto", "design"), "design": ("design",), "dev": ("dev",)}
#: Quem cria missão nova — é a etapa de produto que ela começa.
PAPEIS_QUE_CRIAM: Tuple[str, ...] = PAPEIS_DA_ETAPA["produto"] + ("admin",)

GERANDO = "gerando"
AGUARDANDO = "aguardando_parecer"
REFAZENDO = "refazendo"
LIBERADA = "liberada"
DEVOLVIDA = "devolvida"
ENCERRANDO = "encerrando"
ENTREGUE = "entregue"
FALHOU = "falhou"
EM_EXECUCAO = (GERANDO, REFAZENDO, ENCERRANDO)

DE_ACORDO = "de_acordo"
REFAZER = "refazer"
INICIAR = "iniciar"
DEVOLVER = "devolver"
EXCECAO = "excecao"

#: Letras e dígitos, sem espaços nem pontuação: "ok, de acordo!!!" não passa.
MIN_CARACTERES_COMENTARIO = 20

#: O *de acordo* de produto pede duas respostas que só quem leu a missão consegue dar. Em
#: 24/09/2026 o time pedagógico devolvia missões rasas que o PO liberava confiando no semáforo —
#: e o semáforo não media profundidade. O comentário livre aceitava "conferi, está ok"; estas
#: perguntas não se respondem sem abrir o núcleo. A resposta segue para os agentes de design
#: junto com o comentário. Não é conferida contra a missão: o objetivo é que a leitura aconteça.
#:
#: **Desligada em 25/09/2026:** o time sentiu as duas perguntas como mais um bloqueio para liberar
#: produto. O mecanismo fica: `perguntas_de_conferencia`, `aplicar` e o cartão do app leem este
#: dicionário, e vazio não pede nada. Para religar, descomente a entrada de produto.
CONFERENCIA_DE_ACORDO: Dict[str, Tuple[Tuple[str, str], ...]] = {
    # "produto": (
    #     ("crenca", "Que crença do estudante cai no aha, e em que momento da tela ela cai?"),
    #     ("fora", "Que conceito do material do bimestre a missão deixa de fora, e por que isso está certo?"),
    # ),
}


class DecisaoInvalida(ValueError):
    """A ação não cabe nesta situação, para este papel, ou veio sem comentário suficiente."""


class ConflitoDeVersao(RuntimeError):
    """O fluxo mudou entre a leitura e a gravação: outra pessoa decidiu antes."""


# ------------------------------------------------------------------ utilidades
def proxima_etapa(etapa: str) -> Optional[str]:
    i = ORDEM.index(etapa)
    return ORDEM[i + 1] if i + 1 < len(ORDEM) else None


def etapa_anterior(etapa: str) -> Optional[str]:
    i = ORDEM.index(etapa)
    return ORDEM[i - 1] if i > 0 else None


def _agora() -> str:
    return time.strftime("%d/%m/%Y %H:%M:%S")


def caracteres_uteis(texto: str) -> int:
    return len(re.sub(r"[\W_]", "", texto or ""))


def chaves_da_etapa(etapa: str) -> frozenset:
    """O que a etapa produz, sem o que as seguintes produzem. Reaproveita os conjuntos da correção."""
    from pipeline.reexecucao import CHAVES_DESIGN, CHAVES_DEV, CHAVES_PRODUTO

    return {"produto": CHAVES_PRODUTO - CHAVES_DESIGN, "design": CHAVES_DESIGN - CHAVES_DEV,
            "dev": CHAVES_DEV}[etapa]


def assinatura_da_etapa(estado: Dict[str, Any], etapa: str) -> str:
    """Hash do que a etapa gerou. Um parecer vale para esta versão, não para uma refeita depois."""
    chaves = sorted(k for k in chaves_da_etapa(etapa) if k in estado)
    carga = json.dumps({k: estado[k] for k in chaves}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(carga.encode("utf-8")).hexdigest()[:16]


def _icone(valor: Any) -> str:
    v = str(valor or "").strip().lower()
    if v in ("aprovado", "success", "apto", "verde", "🟢"):
        return "🟢"
    if v in ("bloqueado", "blocked", "reprovado", "vermelho", "🔴"):
        return "🔴"
    if v in ("amarelo", "🟡", "bypassed", "ressalvas", "apto_com_ressalvas"):
        return "🟡"
    return "⚪"


def semaforo_da_etapa(estado: Dict[str, Any], etapa: str) -> Dict[str, str]:
    """`{chave_de_status: ícone}` dos gates que a etapa produz, na ordem alfabética."""
    return {k: _icone(estado[k]) for k in sorted(chaves_da_etapa(etapa))
            if k.endswith("_status") and k in estado}


# ------------------------------------------------------------------ fluxo
def novo_fluxo() -> Dict[str, Any]:
    """Missão nova: produto começa a gerar."""
    return {"etapa": "produto", "situacao": GERANDO, "versao": 0, "atualizado_em": _agora(), "pareceres": []}


def fluxo_de(conversa: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """O fluxo da sessão, ou `None` para uma sessão anterior ao parecer humano."""
    fluxo = conversa.get("fluxo")
    return fluxo if isinstance(fluxo, dict) and fluxo.get("etapa") in ORDEM else None


def pode_agir(papel: str, etapa: str) -> bool:
    return papel == "admin" or papel in PAPEIS_DA_ETAPA.get(etapa, ())


def pode_criar_missao(papel: str) -> bool:
    return papel in PAPEIS_QUE_CRIAM


def rotulo_donos(etapa: str) -> str:
    """"Produto ou Design", "Dev" — para dizer a quem a missão está esperando."""
    return " ou ".join(ROTULO_ETAPA.get(p, p) for p in PAPEIS_DA_ETAPA.get(etapa, (etapa,)))


def dono_da_vez(fluxo: Dict[str, Any]) -> Optional[str]:
    """O papel de quem a missão está esperando, ou `None` se ninguém (executando ou entregue)."""
    if fluxo.get("situacao") in (AGUARDANDO, LIBERADA, DEVOLVIDA, FALHOU):
        return fluxo["etapa"]
    return None


def acoes_possiveis(fluxo: Dict[str, Any], papel: str, estado: Dict[str, Any]) -> List[str]:
    """O que `papel` pode fazer agora. O `admin` pode tudo o que o dono pode, mais a exceção."""
    etapa, situacao = fluxo["etapa"], fluxo["situacao"]
    if not pode_agir(papel, etapa):
        return []
    vermelho = "🔴" in semaforo_da_etapa(estado, etapa).values()
    acoes: List[str] = []
    if situacao in (AGUARDANDO, DEVOLVIDA):
        acoes.append(DE_ACORDO if not vermelho else "")
        acoes.append(REFAZER)
        if vermelho and papel == "admin":
            acoes.append(EXCECAO)
    if situacao == AGUARDANDO and etapa_anterior(etapa):
        acoes.append(DEVOLVER)  # quem gerou pode ver que o problema vem de antes
    if situacao == ENTREGUE and etapa_anterior(etapa):
        # Dev aprovou e entregou, e depois viu que o design precisa mudar. Antes não havia ação:
        # reabrir era editar o conversa.json no bucket à mão. Volta só um passo, como a devolução
        # comum; de Design para Produto segue o caminho de sempre.
        acoes.append(DEVOLVER)
    if situacao == LIBERADA:
        acoes += [INICIAR, DEVOLVER]
    if situacao == FALHOU:
        acoes += [INICIAR] if not fluxo.get("falhou_refazendo") else [REFAZER]
    return [a for a in acoes if a]


def _invalidar_a_partir_de(pareceres: List[Dict[str, Any]], etapa: str) -> None:
    corte = ORDEM.index(etapa)
    for p in pareceres:
        if p.get("etapa") in ORDEM and ORDEM.index(p["etapa"]) >= corte and p.get("acao") in (DE_ACORDO, EXCECAO):
            p["valido"] = False


@dataclass(frozen=True)
class Efeito:
    """O que precisa rodar depois da decisão. `tipo`: `iniciar` | `refazer` | `encerrar`."""

    tipo: str
    etapa: str
    pedido: str = ""


def perguntas_de_conferencia(etapa: str, acao: str) -> Tuple[Tuple[str, str], ...]:
    """As perguntas que a liberação desta etapa exige — vazio para as demais ações e etapas."""
    return CONFERENCIA_DE_ACORDO.get(etapa, ()) if acao in (DE_ACORDO, EXCECAO) else ()


def aplicar(fluxo: Dict[str, Any], acao: str, sessao: Any, comentario: str,
            estado: Dict[str, Any], conferencia: Optional[Dict[str, str]] = None,
            ) -> Tuple[Dict[str, Any], Optional[Efeito]]:
    """Aplica a decisão e devolve `(fluxo_novo, efeito)`. Pura: não toca disco.

    `sessao` é um `tools.auth.Sessao` (usa `.papel` e `.assinatura_de`). `conferencia` traz as
    respostas às `CONFERENCIA_DE_ACORDO` da etapa, quando a ação a libera. Levanta
    `DecisaoInvalida` com a razão para a tela mostrar.
    """
    etapa = fluxo["etapa"]
    if acao not in acoes_possiveis(fluxo, sessao.papel, estado):
        raise DecisaoInvalida(
            f"{ROTULO_ETAPA.get(etapa, etapa)} está em '{fluxo['situacao']}': "
            f"a ação '{acao}' não cabe ao papel {sessao.papel}.")
    comentario = (comentario or "").strip()
    if acao != INICIAR and caracteres_uteis(comentario) < MIN_CARACTERES_COMENTARIO:
        raise DecisaoInvalida(f"O comentário é obrigatório e precisa de ao menos {MIN_CARACTERES_COMENTARIO} "
                              "letras ou números: registre o que você viu e o que decidiu.")
    respostas: Dict[str, str] = {}
    for chave, pergunta in perguntas_de_conferencia(etapa, acao):
        resposta = str((conferencia or {}).get(chave) or "").strip()
        if caracteres_uteis(resposta) < MIN_CARACTERES_COMENTARIO:
            raise DecisaoInvalida(f"Para liberar {ROTULO_ETAPA.get(etapa, etapa)}, responda «{pergunta}» com ao menos "
                                  f"{MIN_CARACTERES_COMENTARIO} letras ou números. A resposta está no núcleo "
                                  "narrativo (1.1 e 1.2) — é a leitura que o de acordo registra.")
        respostas[chave] = resposta
    if respostas:
        # No texto também: é o comentário que chega aos agentes de design, à trilha e ao dossiê.
        comentario += "\n\n" + "\n".join(f"- **{pergunta}** {respostas[chave]}"
                                         for chave, pergunta in perguntas_de_conferencia(etapa, acao))

    novo = json.loads(json.dumps(fluxo))  # cópia funda: o chamador pode comparar antes/depois
    pareceres: List[Dict[str, Any]] = novo.setdefault("pareceres", [])
    alvo = etapa_anterior(etapa) if acao == DEVOLVER else etapa
    rodada = 1 + sum(1 for p in pareceres if p.get("etapa") == alvo and p.get("acao") in (REFAZER, DEVOLVER))
    registro = {
        "etapa": alvo, "acao": acao, "autor": sessao.papel, "como": sessao.assinatura_de(etapa),
        "comentario": comentario, "quando": _agora(), "rodada": rodada,
        "assinatura": assinatura_da_etapa(estado, alvo), "valido": True,
        "gates": semaforo_da_etapa(estado, alvo), "excecao": acao == EXCECAO,
    }
    if respostas:
        registro["conferencia"] = respostas
    efeito: Optional[Efeito] = None

    if acao in (DE_ACORDO, EXCECAO):
        seguinte = proxima_etapa(etapa)
        if seguinte:
            novo.update(etapa=seguinte, situacao=LIBERADA)
        else:
            novo["situacao"] = ENCERRANDO
            efeito = Efeito("encerrar", etapa)
    elif acao == REFAZER:
        _invalidar_a_partir_de(pareceres, etapa)
        devolutiva = ultima_devolutiva(novo, etapa)
        pedido = comentario if not devolutiva else (
            f"{comentario}\n\nDevolutiva que motivou o retrabalho ({devolutiva['como']}, {devolutiva['quando']}):\n"
            f"{devolutiva['comentario']}")
        novo["situacao"] = REFAZENDO
        efeito = Efeito("refazer", etapa, pedido)
    elif acao == INICIAR:
        novo["situacao"] = GERANDO
        efeito = Efeito("iniciar", etapa)
    elif acao == DEVOLVER:
        _invalidar_a_partir_de(pareceres, alvo)
        novo.update(etapa=alvo, situacao=DEVOLVIDA)

    if acao != INICIAR:
        pareceres.append(registro)
    novo.pop("falhou_refazendo", None)
    novo["atualizado_em"] = _agora()
    return novo, efeito


def concluir_execucao(fluxo: Dict[str, Any], ok: bool) -> Dict[str, Any]:
    """Depois que o efeito rodou: a etapa volta ao parecer do dono, ou a missão é entregue."""
    novo = json.loads(json.dumps(fluxo))
    situacao = novo.get("situacao")
    if not ok:
        novo["falhou_refazendo"] = situacao == REFAZENDO
        novo["situacao"] = FALHOU if situacao != ENCERRANDO else AGUARDANDO
    elif situacao == ENCERRANDO:
        novo["situacao"] = ENTREGUE
    else:
        novo["situacao"] = AGUARDANDO
    novo["atualizado_em"] = _agora()
    return novo


def ultima_devolutiva(fluxo: Dict[str, Any], etapa: str) -> Optional[Dict[str, Any]]:
    """A devolução mais recente para `etapa`, se não houve *de acordo* nem *refazer* depois dela."""
    for p in reversed(fluxo.get("pareceres") or []):
        if p.get("etapa") != etapa:
            continue
        return p if p.get("acao") == DEVOLVER else None
    return None


def notas_de_passagem(fluxo: Optional[Dict[str, Any]]) -> str:
    """Markdown dos pareceres *de acordo* válidos, para o estado (`{notas_de_passagem?}`)."""
    if not fluxo:
        return ""
    validos = [p for p in fluxo.get("pareceres") or []
               if p.get("acao") in (DE_ACORDO, EXCECAO) and p.get("valido", True)]
    if not validos:
        return ""
    linhas = ["Pareceres humanos das etapas já liberadas. São decisão de quem responde pela etapa: aplique-os. "
              "Se um deles contrariar um gate ou a plataforma, registre o conflito no seu documento em vez de "
              "escolher em silêncio.", ""]
    for p in validos:
        marca = " — **liberada com exceção** (havia gate 🔴)" if p.get("excecao") else ""
        linhas.append(f"### {ROTULO_ETAPA.get(p['etapa'], p['etapa'])} · {p['como']} · {p['quando']}{marca}")
        linhas += [""] + [f"> {l}" if l.strip() else ">" for l in p["comentario"].splitlines()] + [""]
    return "\n".join(linhas).rstrip() + "\n"


# ------------------------------------------------------------------ disco
def ler_fluxo(run_dir: Path) -> Optional[Dict[str, Any]]:
    caminho = Path(run_dir) / "conversa.json"
    try:
        return fluxo_de(json.loads(caminho.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return None


def registrar_fluxo(run_dir: Path, fluxo: Dict[str, Any], versao_lida: Optional[int]) -> Dict[str, Any]:
    """Grava o fluxo em `conversa.json` se ninguém gravou desde `versao_lida`. Devolve o gravado.

    `versao_lida=None` pula a conferência — só para quem é dono exclusivo do momento (a execução
    em segundo plano, que roda com a trava de `execucao.json`).
    """
    caminho = Path(run_dir) / "conversa.json"
    conversa = json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else {}
    atual = fluxo_de(conversa)
    if versao_lida is not None and atual and int(atual.get("versao", 0)) != int(versao_lida):
        raise ConflitoDeVersao("Outra pessoa registrou uma decisão nesta missão enquanto você a via. "
                               "Recarregue a missão para ver o estado atual.")
    gravado = dict(fluxo)
    gravado["versao"] = int((atual or {}).get("versao", 0)) + 1
    conversa["fluxo"] = gravado
    caminho.write_text(json.dumps(conversa, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return gravado


def quem_age(fluxo: Optional[Dict[str, Any]]) -> str:
    """Frase curta para a lista de missões e o cartão: "aguardando parecer de Design"."""
    if not fluxo:
        return ""
    etapa, situacao = ROTULO_ETAPA.get(fluxo["etapa"], fluxo["etapa"]), fluxo.get("situacao")
    return {
        GERANDO: f"{etapa} gerando",
        REFAZENDO: f"{etapa} refazendo",
        ENCERRANDO: "fechando o dossiê",
        AGUARDANDO: f"aguardando parecer de {etapa}",
        DEVOLVIDA: f"devolvida a {etapa}",
        LIBERADA: f"liberada para {etapa} iniciar",
        FALHOU: f"{etapa} falhou — rodar de novo",
        ENTREGUE: "entregue",
    }.get(situacao, situacao or "")
