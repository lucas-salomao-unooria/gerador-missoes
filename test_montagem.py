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
    # o número sem origem é 🟡 desde a C7 (25/10/2026): dizer que ele é «de regra» é leitura de sentido
    r = montagem.validar_prd(_sintetico(one_pager=op, prd_final=prd, decisoes_do_po=recusado))
    assert r["status"] == "amarelo" and _codigos(r) == ["numero-sem-origem"]


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

    # a citação é da frase dela: o número da frase anterior não responde por ela (exp03ef1b, 28/10/2026)
    outra_frase = _prd({"cada ato em tela dura no máximo 8 minutos (§15 do one-pager)":
                        "o Canal B espera 30 segundos. Cada ato em tela dura no máximo 8 minutos (§15 do one-pager)"})
    r = montagem.validar_prd(_sintetico(prd_final=outra_frase))
    assert "origem-de-produto-falsa" not in _codigos(r)

    # nem o de uma citação anterior da mesma frase (PRD da exp09ef1b, 29/10/2026)
    outra_citacao = _prd({"cada ato em tela dura no máximo 8 minutos (§15 do one-pager)":
                          "o Canal B espera 30 segundos (produto/05-spec-missao.md › Bloco 13) e cada ato em tela dura "
                          "no máximo 8 minutos (§15 do one-pager)"})
    r = montagem.validar_prd(_sintetico(prd_final=outra_citacao))
    assert "origem-de-produto-falsa" not in _codigos(r)


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


# --------------------------------------------------------------------------- calibragem C1 (24/10/2026)
# Os gates de montagem deram 🔴 nas 7 execuções de dev que o PO viu, com acerto e ruído na mesma lista. Os casos reais
# estão no gabarito (`tests/gabarito_achados/`); aqui, as guardas sintéticas de cada calibragem.
GUARDRAIL = _prd({"- RNF-SYNC-001": "- Guardrail: abandono na Etapa 2 abaixo de 5% dos estudantes.\n- RNF-SYNC-001"})


def _pedido(texto: str, etapa: str = "dev") -> Dict[str, Any]:
    return {"origem": f"refazer {etapa} · {etapa} · 24/10/2026 10:00", "etapa": etapa, "texto": texto}


def _troca(de: str, para: str, documento: str = "prd_final") -> Dict[str, str]:
    return {"documento": documento, "de": de, "para": para, "motivo": "pedido do PO"}


def test_pedido_em_prosa_nao_e_origem_de_numero():
    """Terceira revisão do PR #77 (24/10/2026), decisão de desenho: ler intenção em linguagem natural por regex errava
    a cada ajuste — «Não aceito o limiar de 80%» fazia origem do 80% inventado, e «Trocar 80% por 70%» não dava o 70%.
    O pedido em prosa livre não é origem: nem o valor que o PO afirma, nem o que ele cita. O valor novo chega ao
    contrato pela triagem (produto o grava no one-pager e na spec), pelo de acordo (`decisoes_do_po`) ou pela troca da
    correção pontual."""
    for texto in ("O guardrail do PRD está com 7%, deve ser 5%.", "Deve ser 5%.", "Não aceito 5% no guardrail.",
                  "O teto pode ser até 5%.", "Ratifico: resumo de notícia com 5%; manchete com 5%."):
        for estado in ({"pedidos_do_po": [_pedido(texto)]},
                       {"pareceres_humanos": [{"etapa": "dev", "acao": "refazer", "comentario": texto}]}):
            r = montagem.validar_prd(_sintetico(prd_final=GUARDRAIL, **estado))
            assert _codigos(r) == ["numero-sem-origem"] and "5%" in r["achados"][0]["resumo"], texto
            assert "pedidos_do_po" not in montagem.contrato(estado)


def test_troca_da_correcao_pontual_e_origem_so_do_numero_que_ela_trouxe():
    """O lado «para» da troca que a correção pontual de design ou dev aplicou (`edicoes_pontuais`) é origem — só o
    número que o «de» não tinha, só na correção pontual em curso e nunca a troca de documento de produto (que já é o
    contrato, ou foi desfeita por outra correção de produto)."""
    def com(*trocas: Dict[str, str], modo: str = "pontual") -> Dict[str, Any]:
        return _sintetico(prd_final=GUARDRAIL, modo_correcao=modo, edicoes_pontuais=list(trocas))

    assert montagem.validar_prd(com(_troca("abaixo de 7%", "abaixo de 5%")))["status"] == "aprovado"
    assert montagem.contrato(com(_troca("abaixo de 7%", "abaixo de 5%")))["trocas_da_correcao"] == (
        "5% — troca da correção pontual")
    for estado in (com(_troca("abaixo de 7%", "abaixo de 5%"), modo=""),
                   com(_troca("abaixo de 5% (ex.)", "abaixo de 5%")),
                   com(_troca("abaixo de 5%", "abaixo de 7%")),
                   com(_troca("abaixo de 7%", "abaixo de 5%", documento="one_pager")),
                   com(_troca("abaixo de 7%", "abaixo de 5%", documento="spec_missao"))):
        r = montagem.validar_prd(estado)
        assert _codigos(r) == ["numero-sem-origem"] and "5%" in r["achados"][0]["resumo"], estado["edicoes_pontuais"]
    # a decisão do PO no de acordo continua origem
    decidido = _sintetico(prd_final=GUARDRAIL, decisoes_do_po=[{"resposta": "outro", "valor": "guardrail de 5%"}])
    assert montagem.validar_prd(decidido)["status"] == "aprovado"


def test_decisao_e_troca_nao_entram_na_mecanica_da_hipotese():
    """Pedido, decisão e troca não dizem que um número é parâmetro da mecânica: a porcentagem «marcada» como taxa
    continua meta se só eles a têm (revisão do PR #77 — «A H1 não pode ter 25%» tirava do gate a H1 30×25 da
    exp02ef1b)."""
    handoff = ("# Handoff\n\n## 6. Hipóteses de validação\n\n- **Hipótese 1 (Usabilidade):** a dupla ajusta a moldura "
               "em menos de 90 segundos.\n  - *Indica falha:* Se a taxa de 25% de desistência for atingida pelas "
               "duplas.\n\n## 7. Lacunas e pendências\n\n- Nenhuma.\n")
    for extra in ({}, {"pedidos_do_po": [_pedido("A H1 não pode ter 25%: o §17 diz 30%.")]},
                  {"decisoes_do_po": [{"resposta": "outro", "valor": "taxa de 25% de desistência"}]},
                  {"modo_correcao": "pontual", "edicoes_pontuais": [_troca("x", "taxa de 25%", "handoff_dev")]}):
        r = montagem.validar_handoff(_sintetico(handoff_dev=handoff, **extra))
        assert any(a["codigo"] == "hipotese-diverge" and "escreve 25%" in a["resumo"] for a in r["achados"]), extra


def test_numero_de_palavras_so_conta_quando_o_teto_o_rege():
    """«(teto da faixa: 20 palavras)» ao lado de «até 17 palavras» não faz do 17 um teto; «em até 17 palavras» faz."""
    assert montagem.numeros_de_regra("respeitando os tetos da faixa (fala de Bento com 21 palavras)") == []
    assert montagem.numeros_de_regra("frases com até 17 palavras (teto da faixa: 20 palavras)") == [("20", "palavras")]
    assert montagem.numeros_de_regra("Crachá exibe nome, selo e mandato em até 17 palavras.") == [("17", "palavras")]
    assert montagem.numeros_de_regra("bloqueia se o bastidor ultrapassar 40 palavras") == [("40", "palavras")]


#: As redações do teto inventado de 40 palavras do handoff da exp06ef1b-53e011b6 que a main acusava e a segunda revisão
#: perdeu (o marcador só valia nos 40 caracteres antes do número, cortados em `,;|()`), mais o LaTeX do PRD da
#: exp02ef1b-4fd72a9a (terceira revisão do PR #77, 24/10/2026).
TETOS_ESCRITOS_DE_OUTRO_JEITO = (
    "- Teto de palavras do texto de bastidor de cada projeto: 40 palavras.",
    "- Teto de palavras por texto de bastidor do projeto: 40 palavras.",
    "- Texto de bastidor (teto): 40 palavras.",
    "- Texto de bastidor (máx.): 40 palavras.",
    "- O texto de bastidor tem 40 palavras, que é o teto.",
    "- 40 palavras é o teto do texto de bastidor.",
    "- O bastidor precisa caber em 40 palavras.",
    "- Teto de leitura de 60 palavras por legenda de estande e 40 palavras por texto de bastidor.",
    "- Teto estrito de $\\le 40$ palavras por texto de bastidor.",
    "- Strings do bastidor: $\\le 40$ palavras.",
    "- Strings do bastidor com no máximo $40$ palavras.",
    "- Teto do texto de bastidor (40 palavras).",
)


def test_teto_em_qualquer_ponto_da_oracao_e_em_latex():
    for linha in TETOS_ESCRITOS_DE_OUTRO_JEITO:
        assert ("40", "palavras") in montagem.numeros_de_regra(linha), linha
    # as medidas do diagnóstico continuam medidas, com o teto em qualquer ponto antes: o número seguido do teto com
    # outro número, a medida entre parênteses logo depois do identificador e a contagem «com exatamente N palavras»
    for linha in ("Teto da faixa respeitado: fala com exatamente 21 palavras (cumprindo teto ≤ 25).",
                  "Teto da faixa respeitado: fala de Bento com 21 palavras (cumpre teto ≤ 25) e suporte TTS.",
                  "Teto prático da faixa: a pergunta `e6.pergunta.em13co26` (21 palavras) vai em 2 blocos.",
                  "Teto prático da faixa: a pergunta e6.pergunta.em13co26 (21 palavras) vai em 2 blocos.",
                  "Respeitando o teto, o balão com exatamente 21 palavras.",
                  "Copy nos tetos da faixa (resumo de 25 a 35 palavras, fala de Bento com 21 palavras).",
                  "Teto estrito de 0 palavras visuais. Strings em caixa alta de 1 a 21 palavras."):
        assert ("21", "palavras") not in montagem.numeros_de_regra(linha), linha
    # «e o teto» depois do número é outro teto, não o deste
    assert montagem.numeros_de_regra("Bastidor com 21 palavras e o teto da legenda em 60.") == []
    # o parêntese fechado com número solto dentro é de outro número
    assert ("40", "palavras") not in montagem.numeros_de_regra("Legendas (teto: 60 palavras) e bastidor com 40 palavras.")
    # o piso seguido do teto com outro número é regra, não medida: só dentro do parêntese o teto depois faz medida
    assert montagem.numeros_de_regra("Validador exige piso de 15 caracteres e teto de 240 caracteres no campo.") == [
        ("15", "caracteres"), ("240", "caracteres")]


def test_fonte_externa_e_nota_de_acessibilidade_so_tiram_a_porcentagem():
    assert montagem.numeros_de_regra("Pesquisas do CETIC.br apontam que menos de 15% compreendem o feed.") == []
    assert montagem.numeros_de_regra("| Acessibilidade | Lighthouse Accessibility Score ≥ 98% |") == []
    assert montagem.numeros_de_regra("Exemplo no painel: índice da sala (ex.: 73%) e taxa de revisão.") == []
    # a duração da mecânica na mesma linha continua pedindo origem
    assert montagem.numeros_de_regra("Segundo o IBGE, 40% das escolas…; cada rodada dura 45 s.") == [("45", "s")]
    assert montagem.numeros_de_regra("Tempo de resposta de 45 s, ajustável (WCAG 2.2.1).") == [("45", "s")]


def test_recorte_da_aula_so_os_limites_da_plataforma():
    """tema ≤ 60, assuntos ≤ 600 e contexto ≤ 120 caracteres são o contrato de customização da plataforma; outro teto
    para o mesmo campo é decisão e pede origem."""
    assert montagem.numeros_de_regra(
        "O professor digita o tema (máx. 60 caracteres) e os tópicos (máx. 600 caracteres).") == []
    assert montagem.numeros_de_regra("Campo de tema com no máximo 80 caracteres.") == [("80", "caracteres")]
    assert montagem.numeros_de_regra("Resposta aberta com piso de 15 caracteres.") == [("15", "caracteres")]


def test_payload_da_spec_e_o_teto_da_faixa_sao_origem():
    """`{"segundos_sem_acao": 90}` na tabela de eventos da spec é a origem dos «90s sem ação»; o teto da faixa da missão
    (references/teto-palavras-por-faixa.md) é padrão da plataforma — só o da faixa dela."""
    assert montagem.tem_numero(montagem.texto_do_contrato({"spec": '| `EVT-U04` | `{"segundos_sem_acao": 90}` |'}),
                               ("90", "s"))
    assert "20 palavras" in montagem.contrato({"one_pager": "# One-pager — exp06ef1b"})["teto_da_faixa"]
    assert "10 palavras" in montagem.contrato({"one_pager": "# One-pager — exp02ef1b"})["teto_da_faixa"]
    assert "20 palavras" not in montagem.contrato({"one_pager": "# One-pager — exp02ef1b"})["teto_da_faixa"]


ONE_PAGER_H1_85 = ONE_PAGER.replace(
    "- **Hipótese 1 (Usabilidade):** a dupla ajusta a moldura em menos de 90 segundos.\n"
    "  - *Indica falha:* Mais de 30% das duplas confirmarem na posição default.\n",
    "- **Hipótese 1 (Moldura):** pelo menos 85% das duplas ajustam a moldura antes de confirmar a fotografia.\n")
SPEC_PQ01_80 = SPEC.replace("| >25% → animação demonstrativa |", "| <80% → animação demonstrativa |")


def _handoff_h1(linha: str) -> Dict[str, Any]:
    handoff = "# Handoff\n\n## 6. Hipóteses de validação\n\n" + linha + "\n\n## 7. Lacunas e pendências\n\n- Nenhuma.\n"
    return _sintetico(one_pager=ONE_PAGER_H1_85, spec_missao=SPEC_PQ01_80, spec_missao_gate0=SPEC_PQ01_80,
                      handoff_dev=handoff)


def test_limiar_da_pq_citada_e_duvida_so_quando_o_corpo_nao_reproduz_a_frase_do_17():
    """O corpo escreve o limiar da PQ-01 (80%, linha firme do 9f) que a hipótese cita no lugar da meta do §17 (85%).
    Com outro comparativo e outro predicado — a pergunta da PQ, não a frase da meta — é dúvida, atenção. Reproduzir a
    frase do §17 com o número trocado é divergência certa, mesmo com a PQ firme no outro número (terceira revisão do PR
    #77: a H1 30×25 da exp02ef1b, que o PO acusou em 23/10, viraria dúvida com a PQ-01 homologada a 25%). A hipótese
    trocada (outra coisa, mesmo citando a PQ-01 com 80%) continua bloqueando."""
    r = montagem.validar_handoff(_handoff_h1("- **Hipótese 1 (Moldura, PQ-01):** as duplas ajustam a moldura antes de "
                                             "confirmar a fotografia; falha se menos de 80% das duplas tocarem nas "
                                             "alças."))
    assert _codigos(r) == ["hipotese-a-conferir"] and r["status"] == "amarelo"
    assert r["achados"][0]["resumo"].startswith("Dúvida, não divergência certa: a H1 do §17 do one-pager tem 85%")
    assert "limiar da PQ-01" in r["achados"][0]["resumo"]

    for linha in ("- **Hipótese 1 (Moldura, PQ-01):** pelo menos 80% das duplas ajustam a moldura antes de confirmar a "
                  "fotografia.",
                  "- **Hipótese 1 (Moldura, PQ-01):** a meta é que pelo menos 80% das duplas ajustem a moldura antes de "
                  "confirmar."):
        copiada = montagem.validar_handoff(_handoff_h1(linha))
        assert _codigos(copiada) == ["hipotese-diverge"] and copiada["status"] == "bloqueado", linha
        assert "escreve 80%" in copiada["achados"][0]["resumo"]

    trocada = montagem.validar_handoff(_handoff_h1(
        "- **Hipótese 1 (Busca ativa, PQ-01):** pelo menos 80% dos estudantes pesquisam hashtags fora do feed."))
    assert _codigos(trocada) == ["hipotese-diverge"] and trocada["status"] == "bloqueado"

    # sem meta no §17, o limiar da PQ não vira dúvida: continua meta acrescentada
    sem_meta = _handoff_h1("- **Hipótese 2 (Virada, PQ-01):** pelo menos 80% das crianças reconhecem que a foto não "
                           "mostrou tudo.")
    sem_meta["one_pager"] = ONE_PAGER
    assert _codigos(montagem.validar_handoff(sem_meta)) == ["hipotese-diverge"]


def test_complemento_so_com_outro_predicado_ou_o_mesmo_negado():
    """100 − x com o comparativo invertido é dúvida só se o predicado também muda; o mesmo predicado com o critério
    invertido é divergência certa (terceira revisão do PR #77: «Se menos de 70% das duplas desistirem» contra «Mais de
    30% das duplas desistirem» saía 🟡)."""
    def situacao(falha: str) -> List[str]:
        corpo = ("## 6. Hipóteses de validação\n\n- **Hipótese 1 (Usabilidade):** a dupla ajusta a moldura em menos de "
                 "90 segundos.\n  - *Indica falha:* " + falha + "\n")
        return [i["situacao"] for i in montagem.hipoteses_e_tetos(ONE_PAGER, corpo, exigir_tetos=False, spec=SPEC,
                                                                   contrato_texto="") if i["secao"] == "§17"]

    assert situacao("Se menos de 70% das duplas confirmarem na posição default.") == ["trocado"]
    assert situacao("Se menos de 70% das duplas ajustarem a moldura antes de confirmar.") == ["complemento"]
    assert situacao("Se menos de 70% das duplas não confirmarem na posição default.") == ["complemento"]
# --------------------------------------------------------------------------- revisão do PR #77 (24/10/2026)
def test_toda_porcentagem_da_hipotese_e_meta_menos_a_marcada_como_mecanica():
    """A leitura pedia comparativo de lista curta ou população, e «superar 25%», «25% ou mais», «maior que 25%»,
    «taxa de desistência de 25%» sumiam em silêncio. Só sai a porcentagem marcada como mecânica, sem comparativo."""
    for linha in ("Se a desistência das duplas superar 25%.", "Se 25% ou mais das duplas desistirem.",
                  "Se a taxa de desistência for maior que 25%.", "Se a desistência passar de 25%.",
                  "Se a desistência ultrapassar 25%.", "Se a desistência exceder 25%.", "Se mais que 25% desistirem.",
                  "Se a taxa de desistência de 25% for atingida.", "A partir de 25% das duplas.",
                  "Igual ou superior a 25%.", "Menor do que 25% das duplas."):
        assert montagem._metas_do_corpo(linha) == [("25", "%")], linha
    # a mecânica dos 12 de 16 projetos ocultos, que o one-pager da exp06ef1b tem fora do §17 e do 9f
    mecanica = montagem._contrato_da_mecanica(
        "## 4. Etapas\n- A taxa de invisibilidade de cada jurado será de 60% a 75%.\n"
        "## 17. Hipóteses de validação\n- H1: mais de 25% das duplas desistem.\n"
        "## 18. Decisões\n| PQ-01 | Quantas duplas desistem? | >25% → animação |\n")
    for linha in ("o grid com 12 projetos ocultos (taxa real de ~75% de invisibilidade)",
                  "o confronto entre a projeção da sala e a taxa de 75% da Galeria Oculta"):
        assert montagem._metas_do_corpo(linha, mecanica) == [], linha
        # sem o contrato, a marca não basta
        assert montagem._metas_do_corpo(linha) == [("75", "%")], linha
    # a marca de mecânica não vale contra comparativo nem população, e o «~» solto não marca nada
    assert montagem._metas_do_corpo("taxa de 75% das duplas", mecanica) == [("75", "%")]
    assert montagem._metas_do_corpo("mais de ~75% acertam", mecanica) == [("75", "%")]
    assert montagem._metas_do_corpo("a galeria esconde ~75% dos projetos", mecanica) == [("75", "%")]
    # revisão do PR #77 (24/10/2026): a porcentagem que o contrato só tem no §17 ou no limiar de uma PQ do 9f é meta,
    # mesmo marcada como taxa — os 25% da H1 da exp02ef1b
    assert "25%" not in mecanica
    for linha in ("Se a desistência chegar a ~25%, ou", "Se ~25% desistirem, ou",
                  "Se a taxa de 25% de desistência for atingida pelas duplas, ou",
                  "A taxa de 25% de desistência na moldura for atingida (alimenta PQ-01).",
                  "Desistência na moldura em ~25% (alimenta PQ-01)."):
        assert montagem._metas_do_corpo(linha, mecanica) == [("25", "%")], linha


def test_direcao_do_comparativo_antes_e_depois_da_porcentagem():
    for texto, direcao in (("superar 25%", "mais"), ("ultrapassarem 25%", "mais"), ("passar de 25%", "mais"),
                           ("maior do que 25%", "mais"), ("a partir de 25%", "mais"), ("25% ou mais", "mais"),
                           ("igual ou superior a 25%", "mais"), ("pelo menos 25%", "mais"),
                           ("menor que 25%", "menos"), ("menos que 25%", "menos"), ("25% ou menos", "menos"),
                           ("igual ou inferior a 25%", "menos"), ("no máximo 25%", "menos"), ("taxa de 25%", "")):
        assert montagem._direcao(texto, ("25", "%")) == direcao, texto


def test_teto_posposto_separado_por_virgula_ou_na_celula_anterior():
    """Só o marcador logo antes do número contava: o teto novo escrito depois dele, separado por vírgula ou na célula
    vizinha da tabela deixava de pedir origem. A medida seguida do teto com outro número continua sendo medida."""
    for linha, numero in (("Balões de notificação com 35 palavras no máximo.", "35"),
                          ("RNF: balões com, no máximo, 35 palavras.", "35"),
                          ("| Balão da comissão | Teto | 35 palavras |", "35"),
                          ("| Balão da comissão | 35 palavras (teto) |", "35"),
                          ("Resumo entre 25 e 35 palavras (teto do D0-09).", "35"),
                          ("Balão de notificação: 35 palavras (teto do §15).", "35"),
                          ("Balão de notificação: 40 palavras (teto do § 15).", "40"),
                          ("Manchetes de 8 a 10 palavras, sem exceder o teto.", "10"),
                          ("Legenda de 35 palavras ou menos.", "35"),
                          ("Balão com 35 palavras (máx. 2 linhas).", "35")):
        assert montagem.numeros_de_regra(linha) == [(numero, "palavras")], linha
    for linha in ("legendas com 39 a 46 palavras (teto: 60)", "`e6.pergunta.em13co26` (49 palavras)",
                  "| Fala de Bento | 21 palavras | teto da faixa |", "| Teto da faixa: 20 | Fala com 21 palavras |",
                  "Fala de Bento com 21 palavras, teto da faixa: 20 palavras."):
        assert ("21", "palavras") not in montagem.numeros_de_regra(linha) and (
            "46", "palavras") not in montagem.numeros_de_regra(linha) and (
            "49", "palavras") not in montagem.numeros_de_regra(linha), linha


def test_barra_de_progresso_so_e_plataforma_na_espera_do_carregamento():
    """A barra que mostra o tempo da rodada é a mecânica (decisão de produto, como os 45 s da exp02ef1b); a da espera
    da geração por IA é a casca (handoff da exp06ef1b-727a3c2d)."""
    assert montagem.numeros_de_regra("Barra de progresso do tempo da rodada: 45 s para responder.") == [("45", "s")]
    assert montagem.numeros_de_regra("Indicador de progresso da rodada com 30 s.") == [("30", "s")]
    assert montagem.numeros_de_regra("Barra de progresso contínua com estimativa tranquilizadora de 10 a 20 segundos "
                                     "da geração por IA.") == []
    assert montagem.numeros_de_regra("Indicador de progresso durante o carregamento de 3 s.") == []
    assert montagem.numeros_de_regra("Spinner por 3 s enquanto a IA gera.") == []
    # sai só a duração da espera, na oração dela: a regra ao lado continua pedindo origem (terceira revisão do PR #77 —
    # spinner, skeleton e barra de progresso tiravam a linha inteira)
    assert montagem.numeros_de_regra(
        "Pausa 1: o cliente envia os Stories e aguarda; o painel plota a barra de progresso em tempo real e, ao atingir "
        "≥ 60% de submissões, habilita o mural.") == [("60", "%")]
    assert montagem.numeros_de_regra("Barra de progresso da rodada: a IA avalia a resposta, e o estudante tem 25 "
                                     "segundos para responder.") == [("25", "s")]
    assert montagem.numeros_de_regra("Skeleton da galeria; a dica aparece após 25 segundos sem toque.") == [("25", "s")]


def test_origem_dos_numeros_no_15_e_alternativa_considerada_na_hipotese():
    """A tabela «Origem dos números» na §15 traz a coluna «Alternativa considerada» e recapitula itens do §17 (exp03ef1b):
    nem a alternativa descartada vira `teto-ausente`, nem citá-la entre parênteses na hipótese vira `hipotese-diverge`."""
    one_pager = (
        "## 15. Tetos aplicados à faixa (3º ano EF)\n"
        "- Legenda de foto com até 8 palavras.\n\n"
        "### Origem dos números\n"
        "| Número | Onde aparece | Origem | Alternativa considerada |\n"
        "|---|---|---|---|\n"
        "| Legenda de foto até 8 palavras | itens 3 e 15 | decisão de produto | teto único de 5 palavras |\n"
        "| H2 (Etapa 4): pelo menos 60% das equipes põem o Pátio em Onde | item 17 | decisão de produto | 50% |\n"
        "| H3: pelo menos 70% das equipes completam a montagem com até 10 recusas | item 17 | decisão de produto | 60% |\n\n"
        "## 17. Hipóteses de validação\n"
        "- **H2**: Pelo menos 60% das equipes põem o Pátio em Onde na primeira tentativa. Falha: mais de 30% erram.\n"
        "- **H3**: Pelo menos 70% das equipes completam a montagem com até 10 recusas.\n"
    )
    corpo = (
        "## Hipóteses de validação (§17 do one-pager aprovado)\n"
        "- **H2**: Pelo menos 60% das equipes põem o Pátio em Onde na primeira tentativa "
        "(origem: one-pager §17; alternativa considerada: 50%). Falha: mais de 30% erram.\n"
        "- **H3**: Pelo menos 70% das equipes completam a montagem com até 10 recusas "
        "(origem: one-pager §17; alternativa considerada: 60%).\n\n"
        "## Requisitos não funcionais\n"
        "- Legenda de foto com até 8 palavras.\n"
    )
    assert montagem.hipoteses_e_tetos(one_pager, corpo, exigir_tetos=True) == []

