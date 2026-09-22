"""Acusa números e fundamentações que divergem da fonte única `literatura-cognitiva.md`.

Por que existe: a fonte única existe "porque números soltos em prompts divergem sem que ninguém
perceba" — e divergiram: `defaults-missao.md` carregou por semanas os tetos de duração revogados
(12/15/20 min) e "4–5 opções" no Médio; dois prompts citavam Piaget e "30 a 40 estudantes". Este
script faz para as referências e os prompts o que `tools/contrato_produto.py` faz para o one-pager:
lista número sem origem. Não decide nada; imprime arquivo:linha para alguém corrigir.

Uso:
  python scripts/conferir_referencias.py            # lista divergências; exit 1 se houver
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FONTE = RAIZ / "prompts" / "references" / "literatura-cognitiva.md"
ALVOS = sorted(
    list((RAIZ / "prompts" / "references").glob("*.md"))
    + list((RAIZ / "prompts" / "produto").glob("*.md"))
    + list((RAIZ / "prompts" / "design").glob("*.md"))
)
#: Arquivos que podem citar valores antigos como registro histórico.
ISENTOS = {"literatura-cognitiva.md", "literatura-cognitiva-resumo.md"}

#: Valores revogados pela fonte (§8 "O que mudou"), que não podem reaparecer como regra.
REVOGADOS = [
    (re.compile(r"≤\s*12\s*min\s+em\s+anos\s+iniciais"), "teto por ato de 12 min (revogado: 6–8 / 8–10)"),
    (re.compile(r"≤\s*15\s*min\s+em\s+anos\s+finais"), "teto por ato de 15 min (revogado: 10–12)"),
    (re.compile(r"≤\s*20\s*min\s+no\s+EM"), "teto por ato de 20 min (revogado: 12–15)"),
    (re.compile(r"\|\s*Ensino Médio\s*\|\s*≤\s*4[–-]5\s*\|"), "4–5 opções no EM (fonte: 4)"),
    (re.compile(r"\b30\s+a\s+40\s+estudantes\b"), "30 a 40 estudantes (fonte §6: 25 / 32)"),
    (re.compile(r"\bPiaget\b"), "Piaget como régua etária (registro negativo §7)"),
    (re.compile(r"\bchoice overload\b", re.I), "choice overload como fundamentação (registro negativo §7)"),
    (re.compile(r"\bdecision fatigue\b|\bfadiga decis"), "decision fatigue como fundamentação (registro negativo §7)"),
    (re.compile(r"\bdois testes do 3\.5\b"), "teste de volume do 3.5 como obrigatório (rebaixado a desejável, §2)"),
    (re.compile(r"\bdos 6\b|\b6 ambientes\b|\b6 suportados\b|Roblox, ChatGPT"), "lista fechada com 6 ambientes / Roblox (ambientes.md: 5)"),
]
#: Contexto que isenta a linha: está dizendo para NÃO usar, ou registrando o que mudou.
NEGACAO = re.compile(r"não use|nao use|virou desejável|rebaixad|não sobreviveu|registro negativo|revogad|refutad|não replic|antes\b.*agora|foi o que aconteceu|carregou por semanas|erro histórico|em vez de|fora da lista|saiu\b|não\s+(?:é|conta|cita)", re.I)


def main() -> int:
    if not FONTE.exists():
        print(f"❌ fonte não encontrada: {FONTE}"); return 2
    achados = []
    for alvo in ALVOS:
        if alvo.name in ISENTOS:
            continue
        for n, linha in enumerate(alvo.read_text(encoding="utf-8").splitlines(), 1):
            for padrao, motivo in REVOGADOS:
                if padrao.search(linha) and not NEGACAO.search(linha):
                    achados.append((alvo.relative_to(RAIZ), n, motivo, linha.strip()[:110]))
    if not achados:
        print("✅ nenhuma divergência com a fonte única."); return 0
    print(f"❌ {len(achados)} divergência(s) com `literatura-cognitiva.md`:")
    for arq, n, motivo, trecho in achados:
        print(f"  {arq}:{n} — {motivo}\n      {trecho}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
