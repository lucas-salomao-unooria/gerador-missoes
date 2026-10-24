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
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

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
#:
#: Desde o PR 9 do plano «Produto dono do contrato» (24/10/2026, D9) a conferência que vale é a de leitura item a item
#: (`itens_de_conferencia`): ela só aparece quando há marcador aberto, e estas duas perguntas seguem desligadas.
CONFERENCIA_DE_ACORDO: Dict[str, Tuple[Tuple[str, str], ...]] = {
    # "produto": (
    #     ("crenca", "Que crença do estudante cai no aha, e em que momento da tela ela cai?"),
    #     ("fora", "Que conceito do material do bimestre a missão deixa de fora, e por que isso está certo?"),
    # ),
}


#: Na última etapa o *de acordo* só encerra a missão: comentário longo ali é quase sempre ajuste.
#: O de 06/10/2026 na missão do 9º ano trazia as perguntas de Canal B reescritas (2.375 caracteres)
#: e nenhum agente o leu. Nas outras etapas o comentário segue para a próxima, então só recusa o que
#: tem cara de conteúdo para a etapa que está sendo liberada.
MAX_DE_ACORDO_ULTIMA_ETAPA = 400

#: Onde uma mudança de conteúdo vale, por etapa. Em design e dev, o *refazer* não muda o one-pager, e os gates
#: conferem design e dev contra ele: o Canal B reescrito num refazer de dev voltava ao texto antigo pelo gate do
#: pedagógico, e o anexo do PRD seguia com o §12a de antes (auditoria de 07/10/2026). O que o one-pager decide
#: muda em produto; o resto, na etapa. Desde o PR 5 do plano «Produto dono do contrato» (23/10/2026), o *refazer* de
#: design e de dev passa pela triagem item a item: o que é de produto vai antes ao one-pager e à spec do Gate 0.
COMO_MUDAR_CONTEUDO: Dict[str, str] = {
    "produto": ("Para a mudança valer, use **Refazer** com este mesmo texto — a etapa é refeita aplicando-o e volta "
                "ao seu parecer."),
    "design": ("Use **Refazer** com este mesmo texto: a triagem o divide item a item, e o que muda o one-pager aprovado "
               "(texto que a criança ou o professor lê, regra, número, habilidade, tempo) vai primeiro a Produto — o "
               "one-pager e a spec do Gate 0 mudam lá —, e o resto se aplica no design. Você vê a divisão antes de "
               "confirmar. Item que a triagem não sabe de quem é pede **Devolver** até Produto."),
    "dev": ("Use **Refazer** com este mesmo texto: a triagem o divide item a item, e o que muda o one-pager aprovado "
            "(texto que a criança ou o professor lê, regra, número, habilidade, tempo) vai primeiro a Produto, depois "
            "ao Design e só então ao dev. Você vê a divisão antes de confirmar. Item que a triagem não sabe de quem é "
            "pede **Devolver**."),
}
_RE_CONTEUDO = re.compile(r"\bPergunta\s+\d|\bAlternativas?\b|\bCen[áa]rio:|\bAJUSTE\s+\d|\bTRAVAS?\b", re.IGNORECASE)


def parece_ajuste(comentario: str, ultima_etapa: bool) -> str:
    """O motivo, se o comentário de um *de acordo* parece trazer mudança de conteúdo; senão, vazio."""
    m = _RE_CONTEUDO.search(comentario or "")
    if m:
        return f"traz «{m.group(0).strip()}»"
    if ultima_etapa and caracteres_uteis(comentario) > MAX_DE_ACORDO_ULTIMA_ETAPA:
        return f"tem mais de {MAX_DE_ACORDO_ULTIMA_ETAPA} letras na última etapa, que não tem etapa seguinte para lê-lo"
    return ""


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


def _estrito(estrito: Optional[bool]) -> bool:
    """ESTEIRA_ESTRITA, a menos que o chamador diga (os testes dizem)."""
    if estrito is not None:
        return estrito
    from config import get_settings

    return bool(get_settings().esteira_estrita)


def contrato_em_aberto(estado: Dict[str, Any]) -> list:
    """Os itens que o PO decide no de acordo de produto (`tools/fechar_contrato.py`)."""
    from tools.fechar_contrato import itens_em_aberto

    return itens_em_aberto(estado)


def contrato_pendente(estado: Dict[str, Any]) -> bool:
    """Há item do contrato sem fechar, ou decisão do PO que um refazer apagou do texto (`decisoes_perdidas`)."""
    from tools.fechar_contrato import decisoes_perdidas

    itens = contrato_em_aberto(estado)
    return bool(itens) or bool(decisoes_perdidas(estado, itens))


def acoes_possiveis(fluxo: Dict[str, Any], papel: str, estado: Dict[str, Any],
                    estrito: Optional[bool] = None) -> List[str]:
    """O que `papel` pode fazer agora. O `admin` pode tudo o que o dono pode, mais a exceção."""
    etapa, situacao = fluxo["etapa"], fluxo["situacao"]
    if not pode_agir(papel, etapa):
        return []
    vermelho = "🔴" in semaforo_da_etapa(estado, etapa).values()
    acoes: List[str] = []
    if situacao in (AGUARDANDO, DEVOLVIDA):
        acoes.append(DE_ACORDO if not vermelho else "")
        acoes.append(REFAZER)
        # Com ESTEIRA_ESTRITA, produto não sai com [PARÂMETRO]/[PROPOSTA] sem resposta — salvo exceção do admin, que fica
        # registrada com o que ficou sem resposta (plano «Produto dono do contrato», D3)
        sem_resposta_possivel = (etapa == "produto" and papel == "admin" and not vermelho and _estrito(estrito)
                                 and contrato_pendente(estado))
        if (vermelho or sem_resposta_possivel) and papel == "admin":
            acoes.append(EXCECAO)
    if situacao in (AGUARDANDO, DEVOLVIDA) and etapa_anterior(etapa):
        # Quem gerou pode ver que o problema vem de antes. Também depois de receber uma devolução: o Dev
        # devolve ao Design, e o Design precisa poder repassar a Produto sem refazer o que não é dele.
        acoes.append(DEVOLVER)
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
    """O que precisa rodar depois da decisão. `tipo`: `iniciar` | `refazer` | `encerrar`.

    `divisao`: no *refazer* de design ou dev, o pedido dividido por dono (`tools/triagem_pedido.py`) — com item de
    produto, `pipeline/execucao_fundo.py` roda a cascata (`pipeline.reexecucao.executar_cascata_stream`)."""

    tipo: str
    etapa: str
    pedido: str = ""
    divisao: Optional[Dict[str, Any]] = field(default=None, compare=False, hash=False)


def perguntas_de_conferencia(etapa: str, acao: str) -> Tuple[Tuple[str, str], ...]:
    """As perguntas que a liberação desta etapa exige — vazio para as demais ações e etapas."""
    return CONFERENCIA_DE_ACORDO.get(etapa, ()) if acao in (DE_ACORDO, EXCECAO) else ()


# ------------------------------------------------------------------ governança da liberação de produto (D9)
def exige_justificativa(etapa: str, acao: str, estado: Dict[str, Any]) -> bool:
    """A exceção do admin que libera produto com gate 🔴 exige justificativa escrita (plano «Produto dono do contrato»,
    D9). Até 24/10/2026 bastava o comentário de toda ação: a de 23/10 15:57 na exp02ef1b dizia «aprovado com falso
    positivo», sem dizer qual gate nem por quê. Em design e dev, a exceção segue como antes."""
    return etapa == "produto" and acao == EXCECAO and "🔴" in semaforo_da_etapa(estado, etapa).values()


#: Marcador do contrato no resumo de um achado: o item já está na lista do de acordo (`tools/fechar_contrato.py`), e a
#: conferência não o pede duas vezes — o rastro da spec repete como decisão humana cada [ABERTO — dono: PO].
_RE_MARCADOR_DO_CONTRATO = re.compile(r"\[(?:PAR[ÂA]METRO|PROPOSTA)\b|\[ABERTO\s*[—–-]\s*dono:\s*(?:o\s+)?PO\b", re.I)
CONTRATO = "contrato"
PENDENCIA = "pendencia"


def itens_de_conferencia(estado: Dict[str, Any]) -> List[Dict[str, str]]:
    """O que o PO confirma ter lido ou decidido antes do de acordo de produto — vazio quando não há marcador aberto.

    A conferência de leitura do de acordo de produto foi desligada em 25/09/2026 (05feeaf): as duas perguntas fixas
    eram sentidas como mais um bloqueio. Ela volta só quando há o que decidir (plano «Produto dono do contrato», PR 9):
    os itens da lista do contrato (`[PARÂMETRO]`, `[PROPOSTA]`, `[ABERTO — dono: PO]`, mudança do design no Gate 0 e
    texto-chave acima do teto, PR 3 e PR 7) e as pendências 🟡 que pedem decisão do PO nos gates de produto — achado de
    severidade `decisao_humana` («F7 — propostas aguardando homologação do PO», «conflito-pedido-regra»). Sem nenhum
    deles, o de acordo segue como antes. Pura."""
    itens: List[Dict[str, str]] = [{"id": i.id, "origem": CONTRATO, "tipo": i.tipo, "assunto": i.assunto}
                                   for i in contrato_em_aberto(estado)]
    vistos = set()
    for chave, icone in semaforo_da_etapa(estado, "produto").items():
        envelope = estado.get(f"{chave}_envelope")
        if icone not in ("🟡", "🔴") or not isinstance(envelope, dict):
            continue
        for a in envelope.get("achados") or []:
            if not (isinstance(a, dict) and str(a.get("severidade")) == "decisao_humana"
                    and str(a.get("resumo") or "").strip()):
                continue
            resumo = " ".join(str(a["resumo"]).split())
            if _RE_MARCADOR_DO_CONTRATO.search(resumo):
                continue
            # o mesmo achado em dois gates é uma leitura só: na exp01em1b (e3980485) a fidelidade do núcleo e a do
            # one-pager citam os mesmos pedidos em conflito com regra, cada uma com a explicação dela — vale a citação
            citacao = re.search(r"«(.+?)»", resumo)
            chave_achado = (citacao.group(1) if citacao else resumo).lower()
            carga = f"{a.get('codigo') or ''}|{chave_achado}".encode("utf-8")
            ident = "pendencia-" + hashlib.sha1(carga).hexdigest()[:10]
            if ident in vistos:
                continue
            vistos.add(ident)
            itens.append({"id": ident, "origem": PENDENCIA, "tipo": str(a.get("codigo") or "decisao_humana"),
                          "assunto": resumo[:400], "gate": chave})
    return itens


def conferir_leitura(itens: List[Dict[str, str]], decisoes: Optional[Dict[str, Dict[str, Any]]],
                     leitura: Optional[Any]) -> List[Dict[str, str]]:
    """O registro da conferência: cada item como «decidido» (respondido na lista do contrato) ou «lido» (confirmado no
    cartão). Levanta `DecisaoInvalida` com os que faltam. Item do contrato com «lido» na resposta conta como lido."""
    lidos = {str(i) for i in (leitura or ())}
    registro: List[Dict[str, str]] = []
    faltam: List[Dict[str, str]] = []
    for item in itens:
        resposta = (decisoes or {}).get(item["id"]) or {}
        if item["origem"] == CONTRATO and str(resposta.get("resposta") or "").strip():
            como = "decidido"
        elif item["id"] in lidos or (item["origem"] == CONTRATO and resposta.get("lido")):
            como = "lido"
        else:
            faltam.append(item)
            continue
        registro.append({"id": item["id"], "origem": item["origem"], "tipo": item["tipo"],
                         "assunto": item["assunto"][:200], "como": como})
    if faltam:
        nomes = "; ".join(f"«{f['assunto'][:70]}»" for f in faltam[:5])
        mais = f" e mais {len(faltam) - 5}" if len(faltam) > 5 else ""
        raise DecisaoInvalida(
            f"Há {len(itens)} marcador(es) aberto(s) em produto, e {len(faltam)} ainda sem leitura confirmada: "
            f"{nomes}{mais}. Antes de liberar, responda cada item na lista do contrato ou marque «Li» nele, e confirme "
            "cada pendência 🟡 da conferência de leitura do cartão.")
    return registro


def aplicar(fluxo: Dict[str, Any], acao: str, sessao: Any, comentario: str,
            estado: Dict[str, Any], conferencia: Optional[Dict[str, str]] = None,
            decisoes: Optional[Dict[str, Dict[str, str]]] = None, estrito: Optional[bool] = None,
            divisao: Optional[Dict[str, Any]] = None, leitura: Optional[Any] = None, justificativa: str = "",
            ) -> Tuple[Dict[str, Any], Optional[Efeito]]:
    """Aplica a decisão e devolve `(fluxo_novo, efeito)`. Pura: não toca disco.

    `sessao` é um `tools.auth.Sessao` (usa `.papel` e `.assinatura_de`). `conferencia` traz as
    respostas às `CONFERENCIA_DE_ACORDO` da etapa, quando a ação a libera. `decisoes` traz as
    respostas do PO à lista do contrato aberto (`{id do item: {resposta, valor}}`), no de acordo de
    produto: o registro leva as decisões e as trocas que `tools.fechar_contrato.gravar` grava no
    one-pager e na spec do Gate 0. `divisao` é o *refazer* de design ou dev dividido pela triagem
    (`tools.triagem_pedido.Divisao.como_dict`), que o PO viu e confirmou: item sem dono recusa o refazer (D4, B), e o
    registro e o efeito levam a divisão. `leitura` são os ids de `itens_de_conferencia` que quem libera produto marcou
    como lidos, e `justificativa`, o texto da exceção do admin com 🔴 em produto (D9). Levanta `DecisaoInvalida` com a
    razão para a tela mostrar.
    """
    from tools import governanca as gov

    etapa = fluxo["etapa"]
    if acao not in acoes_possiveis(fluxo, sessao.papel, estado, estrito):
        raise DecisaoInvalida(
            f"{ROTULO_ETAPA.get(etapa, etapa)} está em '{fluxo['situacao']}': "
            f"a ação '{acao}' não cabe ao papel {sessao.papel}.")
    comentario = (comentario or "").strip()
    if acao != INICIAR and caracteres_uteis(comentario) < MIN_CARACTERES_COMENTARIO:
        raise DecisaoInvalida(f"O comentário é obrigatório e precisa de ao menos {MIN_CARACTERES_COMENTARIO} "
                              "letras ou números: registre o que você viu e o que decidiu.")
    justificativa = (justificativa or "").strip()
    if exige_justificativa(etapa, acao, estado) and not gov.justificativa_valida(justificativa):
        raise DecisaoInvalida(
            "A exceção que libera produto com gate 🔴 exige justificativa escrita: por que liberar assim, apesar de "
            "quais gates, e quem resolve o que ficou. Ela fica no parecer, no estado da missão e no dossiê, com o seu "
            "nome e a data. Só espaços ou pontuação não contam.")
    if acao == DE_ACORDO:
        motivo = parece_ajuste(comentario, ultima_etapa=proxima_etapa(etapa) is None)
        if motivo:
            raise DecisaoInvalida(
                f"Este comentário parece trazer mudança de conteúdo ({motivo}). Pelo *de acordo* ela não entra em "
                "documento nenhum: ele só registra que a etapa está pronta como está. " + COMO_MUDAR_CONTEUDO[etapa])
    if acao == REFAZER and divisao is not None and etapa in ("design", "dev"):
        from tools.triagem_pedido import Divisao, ROTULO_DONO

        lida = Divisao.de_dict(divisao)
        if lida is None:
            raise DecisaoInvalida("A divisão do pedido pela triagem veio ilegível. Peça a triagem de novo.")
        if lida.indefinidos:
            # D4, opção B: sem saber o dono, o item não vai a design (o one-pager ficaria dizendo outra coisa) nem a
            # produto por conta da esteira — quem decide é o PO, em produto
            nomes = "; ".join(f"{i.n}. «{i.rotulo(60)}»" for i in lida.indefinidos[:5])
            raise DecisaoInvalida(
                f"A triagem não soube o dono de {len(lida.indefinidos)} item(ns) do pedido: {nomes}. Mande cada um a "
                f"Produto na divisão, ou use **Devolver** até Produto com o pedido — {ROTULO_DONO.get(etapa, etapa)} "
                "não aplica item que pode mudar o one-pager aprovado.")
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
    if acao == REFAZER and divisao is not None and etapa in ("design", "dev"):
        registro["divisao"] = dict(divisao)
    if etapa == "produto" and acao in (DE_ACORDO, EXCECAO):
        registro.update(_fechar_contrato(estado, acao, decisoes, registro["quando"], registro["como"], estrito))
        # depois do contrato: com ESTEIRA_ESTRITA, o item sem resposta é recusado lá com a mensagem do contrato
        itens = itens_de_conferencia(estado)
        if itens:
            registro["conferencia_de_leitura"] = conferir_leitura(itens, decisoes, leitura)
        if gov.liberou_sem_conta_produto(registro):
            # quem liberou, com papel e data, fica no registro (autor, como, quando) e na marca que cartão, catálogo,
            # dossiê e as pendências do handoff e do PRD leem (`tools/governanca.py`)
            registro["liberado_sem_conta_produto"] = True
        if acao == EXCECAO and justificativa:
            registro["justificativa_excecao"] = {
                "texto": justificativa, "autor": sessao.papel, "como": registro["como"], "quando": registro["quando"],
                "gates_vermelhos": gov.gates_vermelhos(registro)}
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
        pedido = comentario
        for devolutiva in devolutivas_em_cadeia(novo, etapa):
            pedido += (f"\n\nDevolutiva que motivou o retrabalho ({devolutiva['como']}, {devolutiva['quando']}):\n"
                       f"{devolutiva['comentario']}")
        novo["situacao"] = REFAZENDO
        efeito = Efeito("refazer", etapa, pedido, registro.get("divisao"))
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


def _fechar_contrato(estado: Dict[str, Any], acao: str, decisoes: Optional[Dict[str, Dict[str, str]]],
                     quando: str, como: str, estrito: Optional[bool]) -> Dict[str, Any]:
    """As respostas do PO à lista do contrato aberto, conferidas, e as trocas que o de acordo grava.

    Só a lista responde: «Tudo de acordo» no comentário não aprova [PROPOSTA] — foi assim que o D0-4 da exp02ef1b tornou
    PQ-01..05 «contratuais» (22/10/2026). Com ESTEIRA_ESTRITA, o de acordo não sai com item sem resposta; a exceção do
    admin sai, e o registro diz o que ficou sem resposta (D3)."""
    from tools import fechar_contrato as fc

    itens = fc.itens_em_aberto(estado)
    perdidas = fc.decisoes_perdidas(estado, itens)
    if not itens and not perdidas:
        return {}
    try:
        decisao = fc.decidir(itens, decisoes, quando, como)
    except fc.RespostaInvalida as exc:
        raise DecisaoInvalida(str(exc)) from exc
    _, falhas = fc.aplicar_edicoes(estado, decisao.edicoes)
    if falhas:
        raise DecisaoInvalida("As respostas não puderam ser gravadas — " + "; ".join(falhas[:3])
                              + ". Recarregue a missão: o texto mudou desde que a lista foi montada. Se é uma mudança do "
                              "design no Gate 0, use Refazer com ela.")
    if decisao.sem_resposta and acao == DE_ACORDO and _estrito(estrito):
        nomes = "; ".join(f"«{s['assunto'][:70]}»" for s in decisao.sem_resposta[:5])
        mais = f" e mais {len(decisao.sem_resposta) - 5}" if len(decisao.sem_resposta) > 5 else ""
        raise DecisaoInvalida(
            f"O contrato de produto tem {len(decisao.sem_resposta)} item(ns) sem resposta: {nomes}{mais}. Com "
            "ESTEIRA_ESTRITA, o de acordo de produto não sai com [PARÂMETRO] ou [PROPOSTA] aberto: responda cada item na "
            "lista do cartão (ou «Aceitar as sugestões»), ou peça ao admin a liberação com exceção. «Tudo de acordo» no "
            "comentário não aprova proposta.")
    if perdidas and acao == DE_ACORDO and _estrito(estrito):
        # O refazer apagou do texto a decisão, e o marcador não voltou: o design não a aplica (065, D3), e ela sumiria a
        # jusante. Com ESTEIRA_ESTRITA, produto a repõe (Refazer) antes do de acordo — ou o admin libera com exceção
        nomes = "; ".join(f"«{str(d.get('assunto') or '')[:70]}»" for d in perdidas[:5])
        raise DecisaoInvalida(
            f"{len(perdidas)} decisão(ões) do PO no contrato não está(ão) mais no one-pager nem na spec do Gate 0 — um "
            f"refazer de produto reescreveu o trecho: {nomes}. Com ESTEIRA_ESTRITA, o de acordo de produto não sai assim: "
            "use Refazer citando cada decisão, para ela voltar ao texto, ou peça ao admin a liberação com exceção.")
    saida = {"decisoes_contrato": decisao.decisoes, "sem_resposta": decisao.sem_resposta,
             "edicoes_contrato": decisao.edicoes, "itens_no_cartao": len(itens)}
    if perdidas:
        saida["decisoes_fora_do_texto"] = [{k: d.get(k) for k in ("id", "tipo", "assunto", "resposta", "valor", "quando", "como")}
                                           for d in perdidas]
    return saida


def concluir_execucao(fluxo: Dict[str, Any], ok: bool, estado: Optional[Dict[str, Any]] = None,
                      pede_devolver: bool = False) -> Dict[str, Any]:
    """Depois que o efeito rodou: a etapa volta ao parecer do dono, ou a missão é entregue.

    Ticket do QA ou da banca com dono `gate-estrutural` é devolução a produto (`devolucoes_a_produto`, gravado por
    `agents.checkers.DespachoTicketsAgent`): a missão volta ao parecer de Produto com os tickets como devolutiva, como
    se o dono da etapa tivesse devolvido. Até o PR 5 do plano «Produto dono do contrato» (23/10/2026) o ticket era
    `RETRABALHO_EXTERNO`: ficava numa mensagem, não rodava nada, e o design construía sobre o defeito de produto.

    `pede_devolver`: o *refazer* triado não aplicou nada e pede **Devolver** a Produto (D4, opção B). A etapa volta ao
    parecer do dono, como estava antes do pedido — em «falhou», a única ação seria refazer de novo. O parecer desse
    refazer fica marcado `nao_aplicado`: os itens de outro dono não viram «aplicado a montante» (`pedidos_do_po`)."""
    novo = json.loads(json.dumps(fluxo))
    situacao = novo.get("situacao")
    if not ok and pede_devolver and situacao == REFAZENDO:
        novo["situacao"] = AGUARDANDO
        # Sem a marca, o refazer não aplicado seguia nas notas como «já aplicado no one-pager e na spec do Gate 0», e o
        # A094/A126 das execuções seguintes o davam por aplicado a montante (revisão do PR 5, 24/10)
        refazer = next((p for p in reversed(novo.get("pareceres") or [])
                        if p.get("etapa") == novo.get("etapa") and p.get("acao") == REFAZER), None)
        if refazer is not None:
            refazer["nao_aplicado"] = True
    elif not ok:
        novo["falhou_refazendo"] = situacao == REFAZENDO
        novo["situacao"] = FALHOU if situacao != ENCERRANDO else AGUARDANDO
    elif situacao == ENCERRANDO:
        novo["situacao"] = ENTREGUE
    else:
        novo["situacao"] = AGUARDANDO
        tickets = devolucoes_a_produto(estado or {})
        if tickets and novo.get("etapa") in ("design", "dev") and situacao in (GERANDO, REFAZENDO):
            _devolver_a_produto(novo, tickets)
    novo["atualizado_em"] = _agora()
    return novo


#: Onde `agents.checkers.DespachoTicketsAgent` grava os tickets endereçados a produto, por gate.
KEY_DEVOLUCOES_A_PRODUTO = "devolucoes_a_produto"


def devolucoes_a_produto(estado: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Os tickets com dono `gate-estrutural` da última rodada de cada gate, sem repetir."""
    vistos, saida = set(), []
    por_gate = estado.get(KEY_DEVOLUCOES_A_PRODUTO)
    for gate, tickets in (por_gate.items() if isinstance(por_gate, dict) else []):
        for t in tickets or []:
            if not isinstance(t, dict):
                continue
            chave = (gate, str(t.get("id") or ""), str(t.get("resumo") or "")[:120])
            if chave not in vistos:
                vistos.add(chave)
                saida.append({**t, "gate": gate})
    return saida


def _devolver_a_produto(fluxo: Dict[str, Any], tickets: List[Dict[str, Any]]) -> None:
    """Registra a devolução da esteira a produto, com os tickets como comentário, e reabre o parecer de produto."""
    etapa = fluxo.get("etapa")
    pareceres: List[Dict[str, Any]] = fluxo.setdefault("pareceres", [])
    rodada = 1 + sum(1 for p in pareceres if p.get("etapa") == "produto" and p.get("acao") in (REFAZER, DEVOLVER))
    comentario = "\n".join(
        [f"O QA de {ROTULO_ETAPA.get(etapa, etapa)} endereçou a produto (dono `gate-estrutural`) {len(tickets)} "
         "ticket(s) que o design não pode consertar — a decisão é do PO, no one-pager e na spec:", ""]
        + [f"- `{t.get('id') or t.get('codigo') or '—'}` ({t.get('gate', '')}) — {str(t.get('resumo') or '')[:400]}"
           for t in tickets[:12]]
        + ([f"- … e mais {len(tickets) - 12}"] if len(tickets) > 12 else []))
    _invalidar_a_partir_de(pareceres, "produto")
    pareceres.append({"etapa": "produto", "acao": DEVOLVER, "autor": "esteira",
                      "como": f"QA de {ROTULO_ETAPA.get(etapa, etapa)} (devolução automática)", "comentario": comentario,
                      "quando": _agora(), "rodada": rodada, "assinatura": "", "valido": True, "gates": {},
                      "excecao": False, "automatica": True, "tickets": tickets})
    fluxo.update(etapa="produto", situacao=DEVOLVIDA)


def ultima_devolutiva(fluxo: Dict[str, Any], etapa: str) -> Optional[Dict[str, Any]]:
    """A devolução mais recente para `etapa`, se não houve *de acordo* nem *refazer* depois dela."""
    for p in reversed(fluxo.get("pareceres") or []):
        if p.get("etapa") != etapa:
            continue
        return p if p.get("acao") == DEVOLVER else None
    return None


def devolutivas_em_cadeia(fluxo: Dict[str, Any], etapa: str) -> List[Dict[str, Any]]:
    """A devolução pendente para `etapa` e as que ainda estão pendentes nas etapas seguintes, da que achou o
    problema à mais recente.

    O Dev devolve ao Design («29 × 24 min, falta EF06CO07»), o Design repassa a Produto («a causa é a mecânica do
    one-pager») — e, até 07/10/2026, o refazer de Produto levava só o repasse: o detalhe de quem achou o problema
    ficava na trilha, que agente nenhum lê. Devolução que já teve *refazer* ou *de acordo* depois não conta.
    """
    return [d for e in reversed(ORDEM[ORDEM.index(etapa):]) if (d := ultima_devolutiva(fluxo, e))]


def pedidos_do_po(fluxo: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Todos os pedidos de *refazer*, de todas as etapas, do mais antigo ao mais novo.

    Até 06/10/2026 só o último pedido chegava aos agentes: o refazer seguinte apagava o anterior
    (`pedido_correcao` é uma chave só), e design e dev não recebiam nenhum. Na missão do 9º ano o
    primeiro pedido trazia a definição dos caminhos A/B e a frase da descoberta inteira; o segundo o
    apagou, e a missão saiu com A/B trocados. Um pedido não deixa de valer porque veio outro.
    """
    if not fluxo:
        return []
    saida: List[Dict[str, str]] = []
    for p in fluxo.get("pareceres") or []:
        if p.get("acao") != REFAZER or not str(p.get("comentario") or "").strip():
            continue
        origem = f"refazer {ROTULO_ETAPA.get(p.get('etapa'), p.get('etapa'))} · {p.get('como', '')} · {p.get('quando', '')}"
        saida += _pedido_por_dono(origem, str(p.get("etapa") or ""), str(p.get("comentario") or ""), p.get("divisao"),
                                  nao_aplicado=bool(p.get("nao_aplicado")))
    return saida


def _pedido_por_dono(origem: str, etapa: str, texto: str, divisao: Any,
                     nao_aplicado: bool = False) -> List[Dict[str, str]]:
    """O pedido de refazer como os agentes o recebem: inteiro, ou — quando a triagem o dividiu e algum item não é da
    etapa — um pedido por dono. O de produto vale em produto (a fidelidade de produto o confere, inclusive num refazer
    de produto seguinte) e diz de onde veio (`a_montante_de`); o da etapa leva os itens dela e o contexto. Até o PR 5
    (23/10/2026) o pedido inteiro era da etapa, e o A094 cobrava em design o botão que a spec do Gate 0 nomeia.

    `nao_aplicado`: a cascata desse refazer não aplicou nada (`concluir_execucao` com `pede_devolver`). Os itens de
    outro dono não levam `a_montante_de` — não foram aplicados a montante — e levam `pendente_em`, com a origem dizendo
    que esperam a decisão do PO."""
    from tools.triagem_pedido import DESIGN, DEV, PRODUTO, ROTULO_DONO, Divisao

    d = Divisao.de_dict(divisao) if isinstance(divisao, dict) else None
    if d is None or all(i.dono == etapa for i in d.itens):
        return [{"origem": origem, "etapa": etapa, "texto": texto}]
    saida: List[Dict[str, str]] = []
    for dono in (PRODUTO, DESIGN, DEV):
        if dono not in (PRODUTO, etapa) and not (dono == DESIGN and etapa == DEV):
            continue
        itens = d.texto_de(dono, com_contexto=dono == etapa)
        if not d.de(dono) or not itens.strip():
            continue
        entrada = {"origem": f"{origem} · itens de {ROTULO_DONO[dono].lower()} (triagem)", "etapa": dono,
                   "texto": itens}
        if dono != etapa and nao_aplicado:
            entrada["origem"] += (f" · NÃO APLICADOS: o refazer voltou ao PO para Devolver até "
                                  f"{ROTULO_DONO[dono]}")
            entrada["pendente_em"] = dono
        elif dono != etapa:
            entrada["a_montante_de"] = etapa
        saida.append(entrada)
    return saida


def notas_de_passagem(fluxo: Optional[Dict[str, Any]]) -> str:
    """Markdown dos pedidos de refazer e dos pareceres *de acordo* válidos (`{notas_de_passagem?}`)."""
    if not fluxo:
        return ""
    from tools.fechar_contrato import notas as notas_do_contrato

    validos = [p for p in fluxo.get("pareceres") or []
               if p.get("acao") in (DE_ACORDO, EXCECAO) and p.get("valido", True)]
    pedidos = pedidos_do_po(fluxo)
    # As decisões do PO no contrato valem também depois de um refazer, que invalida o de acordo: na exp02em1b o de
    # acordo de 21/10/2026 15:43 (90 s, 45 palavras, StoryPoll recusado) sumiu das notas no refazer de 23/10
    contrato = notas_do_contrato(fluxo)
    if not validos and not pedidos and not contrato:
        return ""
    linhas: List[str] = []
    if contrato:
        linhas += [contrato.rstrip(), ""]
    if pedidos:
        linhas += ["## Pedidos de refazer do PO, em vigor", "",
                   "Todos continuam valendo, do mais antigo ao mais novo — um pedido não apaga o anterior. Onde dois "
                   "se contradizem, vale o mais novo. Aplique as TRAVAS e os AJUSTES no que é seu, e responda às "
                   "perguntas de VALIDAÇÃO que o PO escreveu: a fidelidade a eles é conferida depois. O pedido feito a "
                   "design ou a dev passa pela triagem item a item: o que é de produto aparece aqui como «itens de "
                   "produto (triagem)» e já foi aplicado no one-pager e na spec do Gate 0 — acompanhe-o onde o texto "
                   "aparece no seu documento, sem decidir de novo. O marcado «NÃO APLICADOS» não chegou ao one-pager "
                   "nem à spec: não o dê por aplicado nem o aplique na sua etapa — quem decide é o PO, na etapa dona do item; se "
                   "o seu documento depende dele, registre `[CONFLITO — pedido do PO × one-pager aprovado: …]`. "
                   "Pedido sem essa divisão (anterior a 23/10/2026) não "
                   "muda o one-pager aprovado: se ele muda o que o one-pager decide — habilidade, tempo, texto que a "
                   "criança ou o professor lê, número, regra de mecânica —, aplique o que é da sua etapa e registre o "
                   "resto como `[CONFLITO — pedido do PO × one-pager aprovado: …]`. Essa mudança se faz em produto.", ""]
        for i, p in enumerate(pedidos, 1):
            linhas.append(f"### Pedido {i} · {p['origem']}")
            linhas += [""] + [f"> {l}" if l.strip() else ">" for l in p["texto"].splitlines()] + [""]
    if validos:
        linhas += ["## Pareceres de quem liberou as etapas", "",
                   "Pareceres humanos das etapas já liberadas. São decisão de quem responde pela etapa: aplique-os. "
                   "Se um deles contrariar um gate ou a plataforma, registre o conflito no seu documento em vez de "
                   "escolher em silêncio. Parecer não muda o one-pager aprovado: se um comentário contradiz o que o "
                   "one-pager decide — habilidade, tempo, texto que a criança ou o professor lê, número, regra de "
                   "mecânica —, não aplique; registre `[CONFLITO — parecer × one-pager aprovado: …]` para o PO "
                   "decidir em produto.", ""]
        for p in validos:
            marca = " — **liberada com exceção** (havia gate 🔴)" if p.get("excecao") else ""
            if p.get("excecao") and p.get("sem_resposta") and "🔴" not in (p.get("gates") or {}).values():
                marca = (f" — **liberada com exceção** ({len(p['sem_resposta'])} item(ns) do contrato de produto sem "
                         "resposta do PO: seguem como `[PARÂMETRO]`/`[PROPOSTA]`, e não são do design decidir)")
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


def registrar_decisao(run_dir: Path, fluxo_lido: Dict[str, Any], novo: Dict[str, Any], acao: str) -> Dict[str, Any]:
    """Grava a decisão: no de acordo de produto, primeiro as respostas do contrato no one-pager e na spec do Gate 0
    (`tools.fechar_contrato.gravar`), depois o fluxo. Se o fluxo não pode ser gravado (outra pessoa decidiu antes), o
    `estado.json` volta como estava. Devolve o fluxo gravado.

    A ordem garante que o design só fica liberado com as respostas já no texto que ele vai ler (plano, PR 3). Gravado o
    fluxo, o `.docx` e o `.html` do one-pager são regerados com as respostas."""
    from tools import fechar_contrato

    anterior: Optional[Dict[str, str]] = None
    registro = (novo.get("pareceres") or [{}])[-1]
    if (fluxo_lido.get("etapa") == "produto" and acao in (DE_ACORDO, EXCECAO)
            and (registro.get("edicoes_contrato") or registro.get("decisoes_contrato"))):
        anterior = fechar_contrato.gravar(run_dir, registro)
    try:
        gravado = registrar_fluxo(run_dir, novo, fluxo_lido.get("versao", 0))
    except Exception:
        # conflito de versão ou falha de disco: sem o fluxo, as respostas não valem, e o texto volta como estava
        if anterior:
            fechar_contrato.desfazer(run_dir, anterior)
        raise
    if anterior and any(e.get("documento") == fechar_contrato.DOC_ONE_PAGER
                        for e in registro.get("edicoes_contrato") or []):
        try:
            fechar_contrato.exportar_one_pager(run_dir)
        except Exception as exc:  # o export é para gente ler; a decisão já está gravada
            logger.warning("O .docx/.html do one-pager não foi regerado depois do de acordo: %s", exc)
    gravar_governanca(run_dir, gravado)
    return gravado


def governanca(fluxo: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """A governança da liberação de produto deste fluxo (`tools.governanca.de_produto`)."""
    from tools import governanca as gov

    return gov.de_produto((fluxo or {}).get("pareceres") or [])


def gravar_governanca(run_dir: Path, fluxo: Dict[str, Any]) -> bool:
    """Grava no `estado.json` quem liberou produto, com papel e data, quando a decisão a mudou (`governanca_produto`).

    Depois do fluxo: a fonte da verdade são os pareceres, e cada etapa que começa recalcula a chave a partir deles;
    aqui ela fica certa já entre a decisão e a próxima execução (o catálogo `reconstruir` lê o `estado.json`). Falha de
    disco não desfaz a decisão gravada. Devolve se gravou."""
    from tools.governanca import KEY_GOVERNANCA

    caminho = Path(run_dir) / "estado.json"
    try:
        estado = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    nova = governanca(fluxo)
    if estado.get(KEY_GOVERNANCA) == nova or (not nova["historico"] and KEY_GOVERNANCA not in estado):
        return False
    estado[KEY_GOVERNANCA] = nova
    try:
        caminho.write_text(json.dumps(estado, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    except OSError as exc:
        logger.warning("A governança da liberação de produto não foi gravada no estado.json: %s", exc)
        return False
    return True


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
