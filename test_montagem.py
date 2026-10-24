"""PR 4 do plano «Produto dono do contrato» (docs/planos/2026-10-23-produto-dono-do-contrato.md, D10): o PRD e o handoff
montam, não decidem.

A fonte da verdade para codar é a spec de produto mais o anexo de design; o PRD deriva delas, e divergência é defeito.
`tools/montagem.py` confere em código, sem modelo:

a) todo número de regra do corpo existe no contrato (one-pager, spec de produto, decisões D0 da lista branca, decisões
   do PO no de acordo), com exceção do que é de dono plataforma;
b) hipóteses e metas iguais às do §17 e do 9f, e os tetos do §15 presentes;
c) estados da §6 iguais aos do contrato;
d) nenhuma decisão de design citada como origem de produto.

Os dois casos reais do acervo têm de reprovar: a H1 25×30 da exp02ef1b-4fd72a9a (no corpo do PRD e no handoff) e as 35
palavras omitidas do PRD da exp06ef1b-53e011b6. Cada mutante abaixo conserta ou estraga um ponto só.
"""
from __future__ import annotations

import asyncio
import copy
import json
import re
import warnings
from pathlib import Path
from typing import Any, Dict, List

from google.adk.agents.loop_agent import LoopAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

from agents.checkers import RastroCheckAgent, SaidaDeLoopAgent
from tools import montagem

warnings.filterwarnings("ignore", category=DeprecationWarning)

ACERVO = Path(__file__).resolve().parent / "tests" / "acervo"


def _estado(missao: str) -> Dict[str, Any]:
    return json.loads((ACERVO / missao / "estado.json").read_text(encoding="utf-8"))


def _codigos(r: Dict[str, Any]) -> List[str]:
    return sorted({a["codigo"] for a in r["achados"]})


def _achado(r: Dict[str, Any], codigo: str) -> List[Dict[str, str]]:
    return [a for a in r["achados"] if a["codigo"] == codigo]


# --------------------------------------------------------------------------- os dois casos reais
def test_h1_25_contra_30_reprova_o_prd_da_exp02ef1b():
    """O PRD da exp02ef1b escreveu a Hipótese 1 com 25% (o limiar da PQ-01, então [PROPOSTA]); o §17 diz 30%. O A117
    deu 🟢. Aqui reprova. Os 25% eram proposta (D11): a linha da PQ-01 tem `[PROPOSTA]`, então não é divergência do
    contrato, e o redator não é mandado a produto por uma cópia errada."""
    estado = _estado("exp02ef1b-4fd72a9a")
    r = montagem.validar_prd(estado)
    assert r["status"] == "bloqueado"
    h = _achado(r, "hipotese-diverge")
    assert h and "30%" in h[0]["resumo"] and "25%" in h[0]["resumo"]
    assert "divergência é do próprio contrato" not in h[0]["resumo"]
    assert h[0]["agente_responsavel"] == "prd-writer"
    assert not montagem.divergencias_do_contrato(estado["one_pager"], montagem._spec_produto(estado))
    assert not _achado(r, "divergencia-do-contrato-sem-registro")

    # mutante da revisão de 23/10: o registro na §19 com 25% no corpo não salva o PRD
    registrado = copy.deepcopy(estado)
    titulo = "# 19. Decisões (ADR) e pendências"
    assert titulo in estado["prd_final"]
    registrado["prd_final"] = estado["prd_final"].replace(
        titulo, titulo + "\n\n- [ABERTO — dono: produto: o §17 diz 30% na H1 e o 9f diz 25% na PQ-01]\n", 1)
    r = montagem.validar_prd(registrado)
    assert r["status"] == "bloqueado" and _achado(r, "hipotese-diverge")
    assert not _achado(r, "divergencia-registrada")

    # mutante: o corpo com o número do §17 — a divergência some
    corrigido = copy.deepcopy(estado)
    corrigido["prd_final"] = estado["prd_final"].replace("Mais de 25% das duplas desistirem",
                                                         "Mais de 30% das duplas desistirem")
    assert not _achado(montagem.validar_prd(corrigido), "hipotese-diverge")


def test_h1_25_contra_30_reprova_o_handoff_da_exp02ef1b():
    """O handoff parafraseou a H1 inteira com 25% (handoff_dev:779), e a linha não casava por palavras com a do §17: a
    comparação é por hipótese, pelo número dela. A H2, que o §17 não quantifica, ganhou «menos de 70%»."""
    estado = _estado("exp02ef1b-4fd72a9a")
    r = montagem.validar_handoff(estado)
    resumos = " ".join(a["resumo"] for a in _achado(r, "hipotese-diverge"))
    assert r["status"] == "bloqueado"
    assert "30%" in resumos and "25%" in resumos
    assert "H2 do §17 do one-pager não tem número" in resumos and "70%" in resumos
    assert all(a["agente_responsavel"] == "handoff-dev" for a in r["achados"])

    remetido = copy.deepcopy(estado)
    i = remetido["handoff_dev"].index("## 6. Hipóteses de validação")
    j = remetido["handoff_dev"].index("## 7. Lacunas")
    remetido["handoff_dev"] = (remetido["handoff_dev"][:i] + "## 6. Hipóteses de validação\n\nAs do §17 do "
                               "one-pager · H1 a H3, sem reescrevê-las.\n\n" + remetido["handoff_dev"][j:])
    assert not _achado(montagem.validar_handoff(remetido), "hipotese-diverge")


def test_35_palavras_omitidas_reprovam_o_prd_da_exp06ef1b():
    """O teto de 35 palavras do §15 estava no one-pager, na spec, no D0 e no D9, e o PRD saiu sem ele."""
    estado = _estado("exp06ef1b-53e011b6")
    r = montagem.validar_prd(estado)
    teto = _achado(r, "teto-ausente")
    assert r["status"] == "bloqueado" and teto and "35 palavras" in teto[0]["resumo"]

    # mutante: o RNF com o teto — o achado some
    com_teto = copy.deepcopy(estado)
    com_teto["prd_final"] = estado["prd_final"].replace(
        "# 10.", "- RNF-USA-009: balão de notificação da comissão com até 35 palavras (§15 do one-pager).\n\n# 10.", 1)
    assert "35 palavras" in com_teto["prd_final"]
    assert not _achado(montagem.validar_prd(com_teto), "teto-ausente")


def test_estados_inventados_do_prd_da_exp02ef1b():
    """O PRD trocou os 15 estados do contrato por `desafiar`, `explicar_padroes`… e largou PROCESSANDO_RESPOSTA_VISITA."""
    r = montagem.validar_prd(_estado("exp02ef1b-4fd72a9a"))
    inventados = _achado(r, "estado-fora-do-contrato")[0]["resumo"]
    ausentes = _achado(r, "estado-do-contrato-ausente")[0]["resumo"]
    assert "`desafiar`" in inventados and "`explicar_padroes`" in inventados
    assert "PROCESSANDO_RESPOSTA_VISITA" in ausentes


def test_d0_contratual_no_prd_da_exp02ef1b():
    """«Teto … | Decisão contratual [D0-1]»: decisão do D0 apresentada como produto."""
    r = montagem.validar_prd(_estado("exp02ef1b-4fd72a9a"))
    assert "D0-1 apresentado como produto" in _achado(r, "origem-de-produto-falsa")[0]["resumo"]


# --------------------------------------------------------------------------- caso sintético
ONE_PAGER = """# One-pager — Missão de teste v1.0

## 4. As 6 etapas — mecanismo, não intenção

### Etapa 6: Refletir
- Pergunta na tela: "Para mostrar que duas crianças estudam juntas, o que precisa aparecer na foto?"

## 15. Tetos aplicados à faixa
- **Teto de palavras por string de interface:** no máximo 20 palavras por balão.
- **Duração por ato em tela:** no máximo 8 minutos contínuos.

## 17. Hipóteses de validação
- **Hipótese 1 (Usabilidade):** a dupla ajusta a moldura em menos de 90 segundos.
  - *Indica falha:* Mais de 30% das duplas confirmarem na posição default.
- **Hipótese 2 (Virada):** a criança reconhece que a foto não mostrou tudo.
  - *Indica falha:* A criança culpar a câmera.
"""

SPEC = """# Spec — teste

## 2. Mecânica

### Contrato de estados

| Estado inicial | Gatilho | Regra | Estado seguinte | Responsável |
|---|---|---|---|---|
| `INICIAL_DESAFIAR` | toque | — | `DECIDINDO_MOLDURA` | Estudante |
| `DECIDINDO_MOLDURA` | confirmar | área mínima | `CONCLUIDO` | Estudante |

## 9. Dados

### 9f. Perguntas de produto desta missão

| PQ | Pergunta | Decisão que dispara | Corte | Etapa | Ação (verbo:objeto) | Origem |
|---|---|---|---|---|---|---|
| PQ-01 | Quantas duplas confirmam sem mover a moldura? | >25% → animação demonstrativa | turma | E3 | `scored decisao:moldura` | PO |
"""

PRD_BOM = """---
titulo: PRD
---

# 2. Objetivos e KPIs

| KPI | PQ | Pergunta | Decisão | Corte | Tela | Evento(s) | Como calcula | Baseline | Alvo | Prazo |
|---|---|---|---|---|---|---|---|---|---|---|
| KPI-01 | PQ-01 | Quantas duplas confirmam sem mover a moldura? | > 25% → animação | turma | `E3-ALU-01` | `EVT-002` | x / y | sem baseline — primeira medição | ≤ 25% (spec, bloco 9f) | piloto |

### Hipóteses de validação (§17 do one-pager)
- **Hipótese 1 (Usabilidade):** a dupla ajusta a moldura em menos de 90 segundos.
  - *Indica falha:* Mais de 30% das duplas confirmarem na posição default.
- **Hipótese 2 (Virada):** a criança reconhece que a foto não mostrou tudo.

# 6. Máquina de estados

| No design | Estado do contrato |
|---|---|
| Abertura | `INICIAL_DESAFIAR` |

| Estado inicial | Gatilho | Regra | Estado seguinte |
|---|---|---|---|
| `INICIAL_DESAFIAR` | toque | — | `DECIDINDO_MOLDURA` |
| `DECIDINDO_MOLDURA` | confirmar | área mínima | `CONCLUIDO` |

```mermaid
stateDiagram-v2
  [*] --> INICIAL_DESAFIAR
  INICIAL_DESAFIAR --> DECIDINDO_MOLDURA
  DECIDINDO_MOLDURA --> CONCLUIDO
```

# 9. Requisitos não funcionais
- RNF-USA-001: nenhuma string da casca passa de 20 palavras (§15 do one-pager).
- RNF-USA-002: cada ato em tela dura no máximo 8 minutos (§15 do one-pager).
- RNF-SYNC-001: o cliente consulta o gate da turma por polling a cada 3 s (ADR-93).
- A folha do Canal B cobre 75% da tela. O balão `e3.narrativa.convite` tem 13 palavras.

# 19. Pendências
- Nenhuma.
"""


def _sintetico(**sobre: str) -> Dict[str, Any]:
    estado = {"one_pager": ONE_PAGER, "spec_missao": SPEC, "spec_missao_gate0": SPEC, "prd_final": PRD_BOM,
              "fluxo_arestas": "", "jornada_telas": "", "wireframes_cobertura": ""}
    estado.update(sobre)
    return estado


def _prd(troca: Dict[str, str]) -> str:
    texto = PRD_BOM
    for de, para in troca.items():
        assert de in texto, de
        texto = texto.replace(de, para)
    return texto


def test_prd_que_deriva_do_contrato_passa():
    """Polling a 3 s (plataforma), a folha de 75% da tela (layout) e as 13 palavras de uma string (medida) não pedem
    origem no contrato."""
    r = montagem.validar_prd(_sintetico())
    assert r["status"] == "aprovado", r["achados"]


def test_numero_de_regra_sem_origem_e_a_proposta():
    ruim = _prd({"- RNF-SYNC-001": "- Guardrail: abandono na Etapa 2 abaixo de 5% dos estudantes.\n- RNF-SYNC-001"})
    r = montagem.validar_prd(_sintetico(prd_final=ruim))
    assert _codigos(r) == ["numero-sem-origem"] and "5%" in r["achados"][0]["resumo"]

    # marcado como proposta ao PO, não decide: passa (e vai para a 19.3 pelo gate de propostas)
    proposta = ruim.replace("abaixo de 5% dos estudantes.",
                            "abaixo de 5% dos estudantes [PROPOSTA — validar com PO: guardrail de 5%].")
    assert montagem.validar_prd(_sintetico(prd_final=proposta))["status"] == "aprovado"


def test_tempo_limite_da_mecanica_nao_e_plataforma():
    """«Tempo limite» só é plataforma com contexto técnico (HTTP, requisição, API, sessão/JWT, rede). Os 45 s da
    exp02ef1b para responder eram decisão de produto tomada pelo D0."""
    mecanica = _prd({"- RNF-SYNC-001": "- RF-MEC-004: tempo limite de 45 s para responder ao desafio.\n- RNF-SYNC-001"})
    r = montagem.validar_prd(_sintetico(prd_final=mecanica))
    assert _codigos(r) == ["numero-sem-origem"] and "45 s" in r["achados"][0]["resumo"]
    for linha in ("- RF-MEC-004: timeout de 45 s até a criança escolher a carta.",
                  "- RF-MEC-004: a cada 45 s a dica pisca na tela.",
                  "- RF-MEC-004: o lote de cartas some depois de 45 s.",
                  "- RF-MEC-004: a criança ganha um token a cada 45 segundos de foco."):
        r = montagem.validar_prd(_sintetico(prd_final=_prd({"- RNF-SYNC-001": linha + "\n- RNF-SYNC-001"})))
        assert _codigos(r) == ["numero-sem-origem"], linha
    for linha in ("- RNF-REDE-001: timeout de 45 s na requisição HTTP da geração.",
                  "- RNF-REDE-001: tempo limite de 45 s da API de IA.",
                  "- RNF-REDE-001: a sessão expira por tempo limite de 45 min (JWT).",
                  "- RNF-TEL-001: lote de 50 eventos a cada 10 s da SDK.",
                  "- RNF-IA-001: no máximo 45% da cota em tokens de IA por turma."):
        r = montagem.validar_prd(_sintetico(prd_final=_prd({"- RNF-SYNC-001": linha + "\n- RNF-SYNC-001"})))
        assert r["status"] == "aprovado", (linha, r["achados"])


def test_sugestao_de_parametro_aberto_nao_e_contrato_e_a_decisao_do_po_e():
    """A sugestão dentro de um [PARÂMETRO] aberto é do agente; vira contrato quando o PO a aceita no de acordo (PR 3)."""
    op = ONE_PAGER.replace("## 17.", "- Inatividade: [PARÂMETRO — a definir por produto: inatividade, sugestão: 45 s]\n\n## 17.")
    prd = _prd({"- RNF-SYNC-001": "- RNF-INAT-001: o balão de estímulo aparece depois de 45 segundos de inatividade.\n"
                                  "- RNF-SYNC-001"})
    r = montagem.validar_prd(_sintetico(one_pager=op, prd_final=prd))
    assert _codigos(r) == ["numero-sem-origem"] and "45 s" in r["achados"][0]["resumo"]
    decidido = [{"id": "x", "resposta": "aceitar", "gravado": "45 segundos — PO, parecer de 24/10/2026"}]
    assert montagem.validar_prd(_sintetico(one_pager=op, prd_final=prd, decisoes_do_po=decidido))["status"] == "aprovado"
    recusado = [{"id": "x", "resposta": "recusar", "gravado": "45 segundos"}]
    assert montagem.validar_prd(_sintetico(one_pager=op, prd_final=prd, decisoes_do_po=recusado))["status"] == "bloqueado"


def test_bloco_13_pela_lista_branca():
    """Número de uma decisão D0 de UX (lista branca) é contrato; o de uma D0 de classe de produto, não."""
    bloco = ("\n## 13. Decisões D0\n\n| Decisão | Célula preenchida | O que define | Base | Reversível |\n|---|---|---|---|---|\n"
             "| `[D0-1]` | `7.gestos` | Microdemonstração some depois de 4 segundos. | padrão | não precisa |\n")
    prd = _prd({"- RNF-SYNC-001": "- RNF-GES-001: a demonstração do gesto some depois de 4 segundos.\n- RNF-SYNC-001"})
    envelope = {"decisoes": [{"id": "D0-1", "classe": "acessibilidade", "cor": "verde", "campo": "7.gestos"}]}
    estado = _sintetico(spec_missao=SPEC + bloco, prd_final=prd, lacunas_status_envelope=envelope)
    assert montagem.validar_prd(estado)["status"] == "aprovado"
    estado["lacunas_status_envelope"] = {"decisoes": [{"id": "D0-1", "classe": "mecanica_param", "cor": "verde",
                                                       "campo": "7.gestos"}]}
    r = montagem.validar_prd(estado)
    assert _codigos(r) == ["numero-sem-origem"] and "4 s" in r["achados"][0]["resumo"]


#: A PQ-01 decidida a 25% e ligada à H1 (que o §17 diz 30%): o próprio contrato diverge, na origem certa.
SPEC_DIVERGENTE = SPEC.replace("| `scored decisao:moldura` | PO |", "| `scored decisao:moldura` | H1 · PO |")
REGISTRO = "- [ABERTO — dono: produto: o §17 diz 30% na H1 e o 9f diz 25% na PQ-01]"


def test_hipotese_trocada_bloqueia_mesmo_com_registro_na_19():
    """Sem divergência no contrato (a PQ-01 não cita a H1), o 25% no corpo é só cópia errada: bloqueia, sem mandar o
    redator a produto, e o registro na 19 não o salva."""
    trocado = _prd({"Mais de 30% das duplas": "Mais de 25% das duplas"})
    r = montagem.validar_prd(_sintetico(prd_final=trocado))
    assert _codigos(r) == ["hipotese-diverge"]
    assert "divergência é do próprio contrato" not in r["achados"][0]["resumo"]
    registrado = trocado.replace("- Nenhuma.", REGISTRO)
    r = montagem.validar_prd(_sintetico(prd_final=registrado))
    assert r["status"] == "bloqueado" and _codigos(r) == ["hipotese-diverge"]


def test_divergencia_do_contrato_exige_corpo_certo_e_registro_na_19():
    """A PQ-01 do 9f cita a H1 com 25%, e o §17 diz 30%: a divergência é do próprio contrato. O corpo segue o §17 e,
    além disso, a 19 a registra com dono produto e os dois valores — aí é pendência do PO (atenção, etapa produto),
    que o rastro conta. Cada metade sozinha bloqueia."""
    from tools import rastro

    div = montagem.divergencias_do_contrato(ONE_PAGER, SPEC_DIVERGENTE)
    assert [(d["contrato"], d["outro"], d["onde"]) for d in div] == [("30%", "25%", "o 9f da spec (PQ-01)")]

    # 30% no corpo + registro → amarelo, e o PRD não sai pronto até o PO decidir
    certo = PRD_BOM.replace("- Nenhuma.", REGISTRO)
    r = montagem.validar_prd(_sintetico(spec_missao=SPEC_DIVERGENTE, prd_final=certo))
    assert r["status"] == "amarelo" and _codigos(r) == ["divergencia-registrada"]
    assert r["achados"][0]["etapa"] == "produto" and r["achados"][0]["severidade"] == "atencao"
    lac = rastro.varrer_lacunas([{"chave": "prd_final", "rotulo": "PRD", "etapa_padrao": "dev"}], {"prd_final": certo})
    assert lac["status"] == "bloqueado"

    # mutante: 30% no corpo sem o registro → bloqueado
    r = montagem.validar_prd(_sintetico(spec_missao=SPEC_DIVERGENTE))
    assert r["status"] == "bloqueado" and _codigos(r) == ["divergencia-do-contrato-sem-registro"]
    assert "[ABERTO — dono: produto: o §17 diz 30% e o 9f da spec (PQ-01) diz 25%]" in r["achados"][0]["resumo"]

    # mutante: 25% no corpo + registro → bloqueado (o registro não substitui o corpo certo)
    errado = _prd({"Mais de 30% das duplas": "Mais de 25% das duplas"}).replace("- Nenhuma.", REGISTRO)
    r = montagem.validar_prd(_sintetico(spec_missao=SPEC_DIVERGENTE, prd_final=errado))
    assert r["status"] == "bloqueado" and "hipotese-diverge" in _codigos(r)
    assert "divergência é do próprio contrato" in _achado(r, "hipotese-diverge")[0]["resumo"]

    # registro com número que o contrato não tem não vale
    outro = PRD_BOM.replace("- Nenhuma.", "- [ABERTO — dono: produto: o §17 diz 30% e o 9f diz 22%]")
    assert montagem.validar_prd(_sintetico(spec_missao=SPEC_DIVERGENTE, prd_final=outro))["status"] == "bloqueado"

    # no handoff, o registro é na seção 7
    handoff = ("# Handoff para dev\n\n## 6. Hipóteses de validação\nAs do §17 do one-pager.\n\n"
               "## 7. Lacunas e pendências carregadas\n- Nenhuma.\n")
    r = montagem.validar_handoff(_sintetico(spec_missao=SPEC_DIVERGENTE, handoff_dev=handoff))
    assert _codigos(r) == ["divergencia-do-contrato-sem-registro"] and "seção 7" in r["achados"][0]["resumo"]
    r = montagem.validar_handoff(_sintetico(spec_missao=SPEC_DIVERGENTE, handoff_dev=handoff.replace("- Nenhuma.",
                                                                                                    REGISTRO)))
    assert r["status"] == "amarelo" and _codigos(r) == ["divergencia-registrada"]


def test_linha_de_proposta_nao_e_divergencia_do_contrato():
    """A PQ-01 da exp02ef1b tinha «>25%» numa célula e `[PROPOSTA — validar com PO]` na última: a linha inteira é
    proposta, e não faz o 25% da H1 virar divergência do contrato (D11: os 25% eram proposta)."""
    proposta = SPEC_DIVERGENTE.replace("| H1 · PO |", "| H1 · `[PROPOSTA — validar com PO]` |")
    assert not montagem.divergencias_do_contrato(ONE_PAGER, proposta)
    assert montagem.validar_prd(_sintetico(spec_missao=proposta))["status"] == "aprovado"
    trocado = _prd({"Mais de 30% das duplas": "Mais de 25% das duplas"})
    r = montagem.validar_prd(_sintetico(spec_missao=proposta, prd_final=trocado))
    assert _codigos(r) == ["hipotese-diverge"]
    assert "divergência é do próprio contrato" not in r["achados"][0]["resumo"]


#: O item de lista da spec que corresponde à H1, com outro número (revisão do PR #71, 23/10/2026).
ITEM_25 = "\n## 7. Hipóteses\n- *Indica falha:* Mais de 25% das duplas confirmarem na posição default{}.\n"


def test_item_de_lista_com_proposta_nao_e_divergencia_do_contrato():
    """Fora de tabela, `[PROPOSTA]` faz do item inteiro proposta, e o `[PARÂMETRO]` só o valor dentro dele: nenhum dos
    dois é divergência do contrato. Só a linha de tabela saía, e o item virava divergência que o PRD só passava
    registrando `[ABERTO — dono: produto]` — que o rastro conta como bloqueio."""
    # mutante: sem marcador, o item firme com 25% é divergência do contrato na origem certa
    firme = SPEC + ITEM_25.format("")
    assert [(d["secao"], d["contrato"], d["outro"], d["onde"])
            for d in montagem.divergencias_do_contrato(ONE_PAGER, firme)] == [("§17", "30%", "25%", "a spec")]
    assert "divergencia-do-contrato-sem-registro" in _codigos(montagem.validar_prd(_sintetico(spec_missao=firme)))
    proposta = SPEC + ITEM_25.format(" `[PROPOSTA — validar com PO]`")
    parametro = SPEC + ITEM_25.format("").replace("Mais de 25%", "Mais de [PARÂMETRO — a definir: limiar, sugestão: 25%]")
    for spec in (proposta, parametro):
        assert not montagem.divergencias_do_contrato(ONE_PAGER, spec)
        assert montagem.validar_prd(_sintetico(spec_missao=spec))["status"] == "aprovado"
    # o `[PARÂMETRO]` não leva junto o número firme da mesma linha: 25% fora dos colchetes continua divergência
    misto = SPEC + ITEM_25.format(" `[PARÂMETRO — a definir: amostra mínima]`")
    assert [d["outro"] for d in montagem.divergencias_do_contrato(ONE_PAGER, misto)] == ["25%"]
    assert "Mais de 25% das duplas" not in montagem.sem_linhas_abertas(proposta)
    item = montagem.sem_linhas_abertas(parametro).splitlines()[-1]
    assert "Mais de" in item and "25%" not in item


def test_divergencia_do_contrato_pela_linha_da_spec_e_faixa_nao_diverge():
    """O §15 diz 20 palavras e a linha correspondente da spec, 15: divergência na origem certa. Já o «8 a 10 palavras»
    do one-pager com 8 na spec (exp03ef1b) é detalhe dentro da faixa."""
    spec = SPEC + "\n## 6. Tetos\n- **Teto de palavras por string de interface:** no máximo 15 palavras por balão.\n"
    div = montagem.divergencias_do_contrato(ONE_PAGER, spec)
    assert [(d["secao"], d["contrato"], d["outro"], d["onde"]) for d in div] == [("§15", "20 palavras", "15 palavras",
                                                                                  "a spec")]
    faixa = ONE_PAGER.replace("no máximo 20 palavras por balão", "no máximo de 8 a 10 palavras por balão")
    spec_faixa = SPEC + "\n## 6. Tetos\n- **Teto de palavras por string de interface:** no máximo 8 palavras por balão.\n"
    assert not montagem.divergencias_do_contrato(faixa, spec_faixa)


def test_hipotese_sem_numero_que_ganhou_meta():
    ruim = _prd({"- **Hipótese 2 (Virada):** a criança reconhece que a foto não mostrou tudo.":
                 "- **Hipótese 2 (Virada):** pelo menos 70% das crianças reconhecem que a foto não mostrou tudo."})
    r = montagem.validar_prd(_sintetico(prd_final=ruim))
    assert "hipotese-diverge" in _codigos(r)
    assert "H2 do §17 do one-pager não tem número" in _achado(r, "hipotese-diverge")[0]["resumo"]


def test_meta_do_kpi_igual_a_da_pq_no_9f():
    ruim = _prd({"≤ 25% (spec, bloco 9f)": "≤ 30% (spec, bloco 9f)"})
    r = montagem.validar_prd(_sintetico(prd_final=ruim))
    assert "meta-diverge-9f" in _codigos(r)
    assert "KPI-01 (PQ-01, alvo): 30% — no 9f, 25%" in _achado(r, "meta-diverge-9f")[0]["resumo"]
    # e o 30% citado como «spec, bloco 9f» não está lá: origem falsa
    assert "origem-de-produto-falsa" in _codigos(r)


def test_teto_do_15_ausente_e_trocado():
    sem = _prd({"- RNF-USA-001: nenhuma string da casca passa de 20 palavras (§15 do one-pager).\n": ""})
    assert _codigos(montagem.validar_prd(_sintetico(prd_final=sem))) == ["teto-ausente"]
    trocado = _prd({"- RNF-USA-001: nenhuma string da casca passa de 20 palavras (§15 do one-pager).":
                    "- **Teto de palavras por string de interface:** no máximo 15 palavras por balão."})
    r = montagem.validar_prd(_sintetico(prd_final=trocado))
    assert "teto-diverge" in _codigos(r) and "20 palavras" in _achado(r, "teto-diverge")[0]["resumo"]
    # e o 15 que o contrato não tem também é número sem origem
    assert "15 palavras" in _achado(r, "numero-sem-origem")[0]["resumo"]


def test_estados_da_secao_6():
    ruim = PRD_BOM.replace("| `DECIDINDO_MOLDURA` | confirmar | área mínima | `CONCLUIDO` |",
                           "| `decidir` | confirmar | área mínima | `CONCLUIDO` |")
    r = montagem.validar_prd(_sintetico(prd_final=ruim.replace("DECIDINDO_MOLDURA --> CONCLUIDO", "decidir --> CONCLUIDO")))
    assert "estado-fora-do-contrato" in _codigos(r) and "`decidir`" in _achado(r, "estado-fora-do-contrato")[0]["resumo"]

    # sem o estado do contrato em lugar nenhum da §6
    sem = PRD_BOM.replace("`DECIDINDO_MOLDURA`", "`INICIAL_DESAFIAR`").replace("DECIDINDO_MOLDURA", "INICIAL_DESAFIAR")
    r = montagem.validar_prd(_sintetico(prd_final=sem))
    assert "DECIDINDO_MOLDURA" in _achado(r, "estado-do-contrato-ausente")[0]["resumo"]

    # estado de decomposição que o fluxo do design nomeia não é invenção (D7)
    decomposto = PRD_BOM.replace("  DECIDINDO_MOLDURA --> CONCLUIDO",
                                 "  DECIDINDO_MOLDURA --> AJUSTANDO_ALCAS\n  AJUSTANDO_ALCAS --> CONCLUIDO")
    assert "estado-fora-do-contrato" in _codigos(montagem.validar_prd(_sintetico(prd_final=decomposto)))
    estado = _sintetico(prd_final=decomposto, fluxo_arestas="| `AJUSTANDO_ALCAS` | arrastar | — |")
    assert montagem.validar_prd(estado)["status"] == "aprovado"


def test_decisao_do_d0_citada_como_produto():
    ruim = _prd({"(§15 do one-pager).\n- RNF-USA-002": "(Decisão contratual [D0-1]).\n- RNF-USA-002"})
    r = montagem.validar_prd(_sintetico(prd_final=ruim))
    assert "origem-de-produto-falsa" in _codigos(r)
    # até o PR 6 o bloco 13 mora em produto/05-spec-missao.md: citá-lo assim é legítimo
    certo = _prd({"(§15 do one-pager).\n- RNF-USA-002": "(§15 do one-pager; `produto/05-spec-missao.md` › Bloco 13, "
                                                         "[D0-1]).\n- RNF-USA-002"})
    assert "origem-de-produto-falsa" not in _codigos(montagem.validar_prd(_sintetico(prd_final=certo)))


def test_numero_com_origem_citada_que_nao_a_tem():
    ruim = _prd({"cada ato em tela dura no máximo 8 minutos (§15 do one-pager)":
                 "cada ato em tela dura no máximo 8 minutos (§15 do one-pager) e o Canal B em 30 segundos (§17 do "
                 "one-pager)"})
    r = montagem.validar_prd(_sintetico(prd_final=ruim))
    assert "origem-de-produto-falsa" in _codigos(r)
    assert "30 s citado como «§17 do one-pager»" in _achado(r, "origem-de-produto-falsa")[0]["resumo"]


def test_handoff_nao_precisa_repetir_teto_mas_nao_reescreve_texto_chave():
    handoff = ("# Handoff para dev\n\n## 3. Spec de interação\n- Polling a cada 3 s.\n\n## 6. Hipóteses de validação\n"
               "As do §17 do one-pager.\n\n## 7. Lacunas e pendências carregadas\n- Nenhuma.\n")
    assert montagem.validar_handoff(_sintetico(handoff_dev=handoff))["status"] == "aprovado"
    reescrito = handoff.replace("- Polling a cada 3 s.", '- Pergunta do Canal B: "Para mostrar que duas crianças '
                                                         'estudam juntas, o que deve aparecer na foto?"')
    r = montagem.validar_handoff(_sintetico(handoff_dev=reescrito))
    assert _codigos(r) == ["texto-chave-reescrito"]


# --------------------------------------------------------------------------- na esteira
async def _rodar(raiz, estado):
    runner = InMemoryRunner(agent=raiz, app_name="teste")
    await runner.session_service.create_session(app_name="teste", user_id="u", session_id="s", state=estado)
    async for _ in runner.run_async(user_id="u", session_id="s",
                                    new_message=types.Content(role="user", parts=[types.Part(text="go")])):
        pass
    final = await runner.session_service.get_session(app_name="teste", user_id="u", session_id="s")
    return dict(final.state)


def test_gate_no_loop_do_prd_devolve_ao_redator():
    loop = LoopAgent(name="PrdLoop", max_iterations=1, sub_agents=[
        RastroCheckAgent(name="A116bMontagemPrd", modo="montagem_prd", rotulo="PRD monta, não decide",
                         report_key="montagem_prd_report", status_key="montagem_prd_status", agente="montagem-dev",
                         estrito=False),
        SaidaDeLoopAgent(name="A118PrdRodada", rotulo="PRD", status_keys=["montagem_prd_status"],
                         rodada_key="prd_rodada", max_rounds=1),
    ])
    estado = asyncio.run(_rodar(loop, _sintetico(prd_final=_prd({"Mais de 30% das duplas": "Mais de 25% das duplas"}))))
    assert estado["montagem_prd_status"] == "bloqueado"
    assert "`hipotese-diverge`" in estado["montagem_prd_report"]
    envelope = json.loads(re.findall(r"```json\n(.*?)\n```", estado["montagem_prd_report"], re.S)[-1])
    assert envelope["agente"] == "montagem-dev" and envelope["achados"][0]["agente_responsavel"] == "prd-writer"


def test_gates_ligados_aos_loops_e_aos_prompts():
    from agents.dev import POSFIXO_BANCA, agentes_em_ordem, build_dev_stage
    from prompts import load_prompt

    ordem = agentes_em_ordem(build_dev_stage())
    handoff = next(a for a in ordem if a.name == "HandoffLoop")
    nomes = [a.name for a in handoff.sub_agents]
    assert nomes.index("A101bMontagemHandoff") < nomes.index("A103HandoffCheck")
    saida = next(a for a in handoff.sub_agents if a.name == "A103HandoffCheck")
    assert "montagem_handoff_status" in saida.status_keys
    prd = next(a for a in ordem if a.name == "PrdLoop")
    nomes = [a.name for a in prd.sub_agents]
    assert nomes.index("A116bMontagemPrd") < nomes.index("A118PrdRodada")
    assert "montagem_prd_status" in next(a for a in prd.sub_agents if a.name == "A118PrdRodada").status_keys
    assert "A101bMontagemHandoffRetrabalhoBanca" in POSFIXO_BANCA["handoff-dev"]

    assert "{montagem_handoff_report?}" in load_prompt("dev/100a_handoff_dev.md")
    redator = load_prompt("dev/113_prd_writer.md")
    assert "{montagem_prd_report?}" in redator and "[ABERTO — dono: produto:" in redator
