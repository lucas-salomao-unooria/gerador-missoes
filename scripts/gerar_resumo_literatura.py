"""Gera `prompts/references/literatura-cognitiva-resumo.md` a partir da fonte única.

Por que existe: a fonte única dos tetos por idade (`literatura-cognitiva.md`, 268 linhas e mais de
vinte citações) era incluída em um único prompt (P3). Quem desenha tela recebia os tetos de
densidade "a calibrar" da rubrica de ofício sem a explicação de quando não se aplicam — e a
distinção que mais importa para layout ("opção visível não é opção lembrada", +1) não chegava a quem
faz layout (achado A6 da auditoria de 20/09/2026). Incluir a fonte inteira em cinco prompts de design
custaria contexto; este resumo de uma página é gerado da fonte, no mesmo padrão em que
`gerar_bncc_referencia.py` gera a lista BNCC do JSON, para não divergir.

Uso:
  python scripts/gerar_resumo_literatura.py           # regenera o resumo
  python scripts/gerar_resumo_literatura.py --check   # falha (exit 1) se a fonte mudou e o resumo não
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FONTE = RAIZ / "prompts" / "references" / "literatura-cognitiva.md"
DESTINO = RAIZ / "prompts" / "references" / "literatura-cognitiva-resumo.md"

#: Seções da fonte que entram no resumo, na ordem, com o título que o resumo usa.
SECOES = [
    ("1.", "Opções comparadas ao mesmo tempo numa decisão"),
    ("3.", "Duração"),
    ("4.", "Abstração: as portas por idade"),
    ("5.", "Narração e redundância"),
    ("6.", "O cenário de piso da escola pública"),
    ("10.", "Que plataforma a criança usa, por idade"),
    ("7.", "O que NÃO sustenta a régua"),
]
#: Parágrafos (por prefixo em negrito) que entram além das tabelas, por seção.
PARAGRAFOS = {
    "1.": ["**Opção visível não é opção lembrada.**"],
    "3.": ["**Teto agregado da missão inteira"],
    "5.": ["**Narrar ajuda quando:**", "**Narrar atrapalha quando:**", "**Consequência prática:**"],
}
#: Linhas do registro negativo que entram (só o "não use", sem a justificativa longa).
NEGATIVO_MAX_LINHAS = 4


def _sha(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _secao(texto: str, numero: str) -> str:
    """Corpo da seção `## <numero> …` até o próximo `## `."""
    m = re.search(rf"^## {re.escape(numero)} .*?$", texto, re.M)
    if not m:
        raise SystemExit(f"Seção '## {numero}' não encontrada em {FONTE.name}")
    resto = texto[m.end():]
    fim = re.search(r"^## ", resto, re.M)
    return resto[: fim.start()] if fim else resto


def _tabelas(corpo: str) -> list[str]:
    """Blocos de tabela markdown (linhas consecutivas começando por |)."""
    blocos, atual = [], []
    for linha in corpo.splitlines():
        if linha.startswith("|"):
            atual.append(linha)
        elif atual:
            blocos.append("\n".join(atual)); atual = []
    if atual:
        blocos.append("\n".join(atual))
    return blocos


def _paragrafos(corpo: str, prefixos: list[str]) -> list[str]:
    saida = []
    for par in re.split(r"\n\s*\n", corpo):
        p = par.strip()
        if any(p.startswith(pref) for pref in prefixos):
            saida.append(re.sub(r"\s*\n\s*", " ", p))
    return saida


def gerar() -> str:
    fonte = FONTE.read_text(encoding="utf-8")
    partes = [
        "---",
        "name: literatura-cognitiva-resumo",
        "description: Resumo operacional da régua por idade — só as tabelas e as regras de aplicação da fonte única, para os agentes de design. Gerado; não edite à mão.",
        "sources: [literatura-cognitiva.md]",
        "---",
        "",
        "# Régua por idade — resumo operacional",
        "",
        f"> **Gerado automaticamente** de `literatura-cognitiva.md` por `scripts/gerar_resumo_literatura.py`. Não edite à mão: edite a fonte e regenere. "
        f"SHA-256 da fonte: `{_sha(fonte)}`.",
        "",
        "Esta é a **fonte única dos números** que a esteira usa para julgar se uma missão cabe na idade, em uma página. "
        "Todo número é **[DADO DIRETO]** (medido), **[EXTRAPOLAÇÃO]** (derivado de princípio) ou **[CONVENÇÃO]** (escolha da equipe); "
        "extrapolação justifica ⚠️ com mais frequência que ❌. A fundamentação e as citações estão na fonte — aqui só o que se aplica ao construir tela, copy e jornada.",
        "",
    ]
    for numero, titulo in SECOES:
        corpo = _secao(fonte, numero)
        partes += [f"## {titulo} (fonte §{numero.rstrip('.')})", ""]
        tabelas = _tabelas(corpo)
        if numero == "7.":
            # Registro negativo: só a coluna "não use", curta.
            linhas = [l for l in tabelas[0].splitlines()[2:]] if tabelas else []
            partes += ["Não use como fundamentação (refutado ou sem fonte primária):", ""]
            for l in linhas[:NEGATIVO_MAX_LINHAS]:
                celulas = [c.strip() for c in l.strip("|").split("|")]
                partes.append(f"- {celulas[0]}")
            partes.append("")
            continue
        for t in tabelas:
            partes += [t, ""]
        for p in _paragrafos(corpo, PARAGRAFOS.get(numero, [])):
            partes += [p, ""]
        if numero == "10.":
            # As regras (a)–(e) são bullets com continuação em linhas indentadas: junte cada item.
            bloco = next((par for par in re.split(r"\n\s*\n", corpo) if par.strip().startswith("- **(")), "")
            for item in re.split(r"\n(?=- )", bloco.strip()):
                partes.append(re.sub(r"\s*\n\s*", " ", item))
            partes.append("")
    partes += [
        "## Como usar",
        "",
        "- **Teto é sinal, não veredito:** nenhum número desta página foi medido com missões da Unooria (fonte §9). No limite, com desenho sólido, é ⚠️; claramente acima, ❌.",
        "- **Layout muda o teto:** se todas as opções ficam na tela enquanto o estudante decide, o teto de opções sobe +1 (§1). É a distinção que mais importa para quem desenha tela.",
        "- **Formato pesa mais que duração:** atividade individual ou em pequeno grupo sustenta atenção melhor que turma inteira (§3).",
        "- **Chrome nativo não conta** como elemento novo: ícone de coração e botão de play já estão automatizados (§5).",
        "",
    ]
    return "\n".join(partes)


def main(argv: list[str]) -> int:
    if "--check" in argv:
        if not DESTINO.exists():
            print(f"❌ {DESTINO.name} não existe — rode sem --check para gerar."); return 1
        atual = _sha(FONTE.read_text(encoding="utf-8"))
        m = re.search(r"SHA-256 da fonte: `([0-9a-f]{64})`", DESTINO.read_text(encoding="utf-8"))
        if not m or m.group(1) != atual:
            print(f"❌ {DESTINO.name} está defasado em relação a {FONTE.name} — regenere."); return 1
        print(f"✅ {DESTINO.name} confere com a fonte ({atual[:12]}…)."); return 0
    DESTINO.write_text(gerar(), encoding="utf-8")
    print(f"✅ gerado {DESTINO.relative_to(RAIZ)} ({DESTINO.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
