"""Gera `prompts/references/bncc-computacao-letramento-digital.md` a partir de `bncc-computacao.json`.

A fonte única é o JSON (transcrito do anexo oficial do MEC). O markdown é o que os prompts
incluem; não edite o markdown à mão — edite o JSON e rode:

    python scripts/gerar_bncc_referencia.py
"""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = ROOT / "prompts" / "references" / "bncc-computacao.json"
MD_PATH = ROOT / "prompts" / "references" / "bncc-computacao-letramento-digital.md"

EIXO_NOME = {"PC": "Pensamento Computacional", "MD": "Mundo Digital", "CD": "Cultura Digital"}
GRUPOS_EF = OrderedDict(
    [
        ("1º ano", lambda h: h["anos"] == [1]),
        ("2º ano", lambda h: h["anos"] == [2]),
        ("3º ano", lambda h: h["anos"] == [3]),
        ("4º ano", lambda h: h["anos"] == [4]),
        ("5º ano", lambda h: h["anos"] == [5]),
        ("Integradas 1º–5º ano (EF15)", lambda h: h["anos"] == [1, 2, 3, 4, 5]),
        ("6º ano", lambda h: h["anos"] == [6]),
        ("7º ano", lambda h: h["anos"] == [7]),
        ("8º ano", lambda h: h["anos"] == [8]),
        ("9º ano", lambda h: h["anos"] == [9]),
        ("Integradas 6º–9º ano (EF69)", lambda h: h["anos"] == [6, 7, 8, 9]),
    ]
)


def _linha(h: dict) -> str:
    marca = "**letramento digital**" if h["letramento_digital"] else "—"
    return f"| {EIXO_NOME[h['eixo']]} | `{h['codigo']}` | {h['objeto']} | {h['habilidade']} | {marca} |"


def gerar() -> str:
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    fonte = data["fonte"]
    habs = data["habilidades"]
    ef = [h for h in habs if h["etapa"] == "EF"]
    em = [h for h in habs if h["etapa"] == "EM"]
    em_letramento = set(data["letramento_digital"]["em_proposta"])

    out: list[str] = []
    out.append("---")
    out.append("name: bncc-computacao-letramento-digital")
    out.append(
        "description: Todas as habilidades da BNCC Computação por ano (Resolução CNE/CEB 1/2022), com eixo e a marca de letramento digital. Fonte única: references/bncc-computacao.json (gerado por scripts/gerar_bncc_referencia.py). Lido pela avaliação pedagógica (5.1/5.2), pela spec (bloco 11) e pelo QA de entregáveis (D2); o gate determinístico BnccCheck usa o JSON."
    )
    out.append(f"sources: [{fonte['url']}]")
    out.append("---")
    out.append("")
    out.append("# BNCC Computação — habilidades por ano e o que é letramento digital")
    out.append("")
    out.append(
        f"> **Gerado automaticamente** de `bncc-computacao.json` por `scripts/gerar_bncc_referencia.py`. Não edite à mão. "
        f"Fonte: {fonte['titulo']} — [{fonte['url']}]({fonte['url']}) (SHA-256 `{fonte['sha256'][:12]}…`, conferido em {fonte['conferido_em']}). "
        f"{fonte['escopo']}"
    )
    out.append("")
    out.append("## As três regras que a esteira aplica")
    out.append("")
    out.append(
        "1. **Só existe o que está aqui.** Código de habilidade que não aparece nesta lista não existe. Spec, one-pager ou relatório que cite código fora da lista é ⛔ — não é ressalva, é bloqueio."
    )
    out.append(
        "2. **Ano bate com ano.** `EF0n` vale só para o n-º ano; `EF15` vale para qualquer ano do 1º ao 5º; `EF69` para qualquer ano do 6º ao 9º; `EM13` só para o Ensino Médio. Habilidade de outro ano na missão é ⛔."
    )
    out.append(
        "3. **Letramento digital é obrigatório no Fundamental.** Toda missão de 1º a 9º ano exercita pelo menos uma habilidade do eixo Cultura Digital (marcada **letramento digital** abaixo). Pensamento Computacional e Mundo Digital podem entrar como secundárias, nunca como o núcleo que justifica a missão. No Ensino Médio o anexo não tem eixo: a missão precisa citar pelo menos uma habilidade `EM13` (não todas), e a marca de letramento digital é leitura proposta que orienta a avaliação pedagógica sem bloquear."
    )
    out.append("")
    out.append(
        "Essas três regras são conferidas por um gate **determinístico** (`BnccCheck`, depois da spec) que trava a esteira quando falham, e são lidas pelos agentes LLM (avaliação pedagógica 5.1/5.2, spec bloco 11, QA de entregáveis D2) para julgar o que a máquina não julga: se a ação em tela exercita de fato a habilidade."
    )
    out.append("")
    out.append("---")
    out.append("")
    out.append("## Ensino Fundamental")
    out.append("")
    for titulo, filtro in GRUPOS_EF.items():
        grupo = [h for h in ef if filtro(h)]
        if not grupo:
            continue
        ld = [h["codigo"] for h in grupo if h["letramento_digital"]]
        out.append(f"### {titulo}")
        out.append("")
        out.append(f"{len(grupo)} habilidades · letramento digital: {', '.join(f'`{c}`' for c in ld)}")
        out.append("")
        out.append("| Eixo | Código | Objeto de conhecimento | Habilidade | Letramento digital |")
        out.append("|---|---|---|---|---|")
        for h in grupo:
            out.append(_linha(h))
        out.append("")
    out.append("---")
    out.append("")
    out.append("## Ensino Médio (EM13)")
    out.append("")
    out.append(
        "Páginas 61–70 do documento. O anexo organiza as habilidades do Médio por **competência específica**, numa tabela única, sem coluna de eixo e sem separação por série. "
        + data["letramento_digital"]["regra_em"]
    )
    out.append("")
    out.append(
        "**Letramento digital no EM (proposta Unooria):** " + " · ".join(f"`{c}`" for c in data["letramento_digital"]["em_proposta"])
    )
    out.append("")
    comps = data["competencias_em"]
    for num in sorted(comps, key=int):
        grupo = [h for h in em if h["competencia"] == int(num)]
        out.append(f"### Competência específica {num}")
        out.append("")
        out.append(f"> {comps[num]}")
        out.append("")
        out.append("| Código | Habilidade | Letramento digital |")
        out.append("|---|---|---|")
        for h in grupo:
            marca = "**letramento digital** (proposta)" if h["codigo"] in em_letramento else "—"
            out.append(f"| `{h['codigo']}` | {h['habilidade']} | {marca} |")
        out.append("")
    out.append("---")
    out.append("")
    out.append("## Falsos amigos")
    out.append("")
    out.append(
        "Segurança **técnica** é Mundo Digital, não letramento: `EF07CO07` (segurança cibernética e formas de proteção), `EF09CO04` (malwares) e `EF09CO05` (criptografia). "
        "Segurança do ponto de vista do **uso e da privacidade** é Cultura Digital: `EF01CO07`, `EF02CO06`, `EF03CO09`, `EF08CO08`, `EF08CO10`. "
        "E `EF09CO06` (problemas sociais a partir de ambientes digitais) é Cultura Digital, embora fique ao lado das habilidades de segurança cibernética no anexo."
    )
    out.append("")
    out.append("## Regra de manutenção")
    out.append("")
    out.append(
        "Este arquivo espelha o anexo oficial. Só muda se o documento mudar ou se o time pedagógico revisar a leitura do Ensino Médio — e a mudança é feita no JSON, seguida de `python scripts/gerar_bncc_referencia.py`. Descrição de habilidade é cópia literal; não parafraseie."
    )
    out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    MD_PATH.write_text(gerar(), encoding="utf-8")
    print(f"ok → {MD_PATH.relative_to(ROOT)}")
