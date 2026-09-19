"""
teste_empirico_po_vs_original.py
================================
Teste empírico das ferramentas de validação do repositório (tools/rastro.py):
1. validar_manifesto() e validar_telemetria()
2. Comparação entre formato de Product Owner (PO) sem chave-valor/mídia/telemetria estrita
   versus formato original padronizado (conforme contrato de plataforma).
"""

import sys
import os
import json
from pathlib import Path

# Garante que o diretório raiz esteja no sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tools.rastro import (
    validar_manifesto,
    validar_telemetria,
    relatorio_manifesto,
    relatorio_telemetria,
)

# -----------------------------------------------------------------------------
# CASO 1: SPEC TÍPICA DO PO
# Características:
# - Bloco 0 em formato descritivo/bullets livres ("* **Slug:**", "* **Série(s):**")
# - Sem a seção explícita "Ficha do manifesto:" em pares chave-valor estritos
# - Ausência de campos de infraestrutura (produto, permissoes, capabilities, liberacao)
# - Bloco 9 sem governança de mídia (onde grava, quem lê, prazo de retenção)
# - Telemetria em prosa/sem tabela de contrato (sem colunas verbo/objeto/resultado/contexto,
#   uso de campo proibido "dados", WebSocket e papéis obsoletos).
# -----------------------------------------------------------------------------
SPEC_FORMATO_PO = """# Spec — Detetives da Ciência v1.0

**4º EF (Anos Iniciais) · YouTube (`unitube`) · Rubrica v1.17 · Gate final: 🟢 em 24/10/2023**

## 0. Identificação de plataforma
* **Slug:** `exp-XX-mais-curtido-confiavel` `[NN a definir]`
* **Nome que o estudante vê:** Detetives da Ciência: O Mistério do Céu Azul
* **Série(s):** `["4EF"]`
* **Unidade da trilha:** Entre Redes
* **Público:** estudante
* **Software clonado:** YouTube Desktop / Web
* **Seção do DS:** unitube (Storybook Unooria)
* **Viewport:** Desktop 1024x768 ou tela cheia para Chromebooks escolares

## 1. Descoberta central
Nem todo vídeo com muitas visualizações fala a verdade.

## 2. Mecanismo por etapa
O estudante investiga vídeos e grava reflexão por áudio com seu microfone.

## 9. Evidências e dados
- Registramos cliques e as escolhas dos alunos.
- Coletamos áudio dos estudantes para avaliação do professor.
- Guardamos os dados em um banco com campo `dados`: `{ "respostas": [1, 2] }`.
- A sincronização de sala utiliza WebSocket dedicado.
- Autenticação exige papel `admin-contrato`.
"""

# -----------------------------------------------------------------------------
# CASO 2: SPEC E HANDOFF CONFORME (FORMATO ORIGINAL PADRONIZADO)
# Características:
# - Bloco 0 com cabeçalho "Ficha do manifesto:" e 10 pares chave: valor exatos
# - Bloco 9 com governança de mídia estruturada (destino, leitor, retenção)
# - Telemetria com tabela estrita: verbo, objeto, resultado, contexto, caminho, leitura
# - Arquitetura de sala por polling HTTP em exp_NN_gates_turma e papéis ADR-80
# -----------------------------------------------------------------------------
SPEC_FORMATO_ORIGINAL = """# Spec — Detetives da Ciência v1.0

**4º EF (Anos Iniciais) · YouTube (`unitube`) · Rubrica v1.17 · Gate final: 🟢 em 2026-09-17**

## 0. Identificação de plataforma
Nome: Detetives da Ciência.

**Ficha do manifesto:**
- `id: exp-08-mais-curtido-confiavel`
- `produto: entre-redes`
- `series: ["4EF"]`
- `unidade: 2`
- `publico: estudante`
- `viewport: 375x812`
- `permissoes: [forms, microphone]`
- `capabilities: [telemetria, progresso]`
- `secao_ds: unitube`
- `liberacao: por-turma`

## 1. Descoberta central
Nem todo vídeo com muitas visualizações fala a verdade.

## 2. Mecanismo por etapa
O estudante investiga vídeos e grava reflexão por voz.

## 9. Evidências e dados
### Mídia capturada do estudante (`microphone`)
- **Onde é gravada:** Arquivo `.webm` na tabela `exp_08_reflexoes` e bucket `gs://unooria-midia-alunos`.
- **Quem lê:** Professor da turma autenticado.
- **Retenção:** 1 ano letivo, expurgada ao final do ciclo escolar.

### Graus de medida
| Medida | Classificação | Critério |
|---|---|---|
| `selecao_confiavel` | `scored` | Escolha de vídeos validados |
"""

HANDOFF_FORMATO_ORIGINAL = """# Handoff — Detetives da Ciência
## 3. Spec de interação e eventos
| Verbo | Objeto | Quando dispara | resultado | contexto | Caminho | Onde é lido |
|---|---|---|---|---|---|---|
| `interacted` | `video:escolha` | ao tocar card | {"escolhido": true} | {"etapa": 3} | analítico | exp_08_sessoes |

## 5. Telemetria e entidades
Tabelas: `exp_08_sessoes`, `exp_08_gates_turma` lidas por polling curto de 3s.
Sem uso de WebSocket (ADR-93/94). Papéis conforme ADR-80 (`estudante`, `professor`).
"""


def executar_bateria():
    print("=" * 80)
    print("BATERIA DE TESTES EMPÍRICOS: tools/rastro.py")
    print("=" * 80)

    # ---------------------------------------------------------
    # TESTE 1: validar_manifesto()
    # ---------------------------------------------------------
    print("\n" + "#" * 80)
    print("PARTE 1: validar_manifesto()")
    print("#" * 80)

    print("\n--- [1.1] Testando FORMATO DO PO ---")
    res_m_po = validar_manifesto(SPEC_FORMATO_PO)
    print(f"STATUS OBTIDO: {res_m_po['status'].upper()}")
    print(f"Bloco 0 identificado: {res_m_po['bloco0_encontrado']}")
    print(f"Total de achados: {len(res_m_po['achados'])}")
    print("Detalhamento dos Erros:")
    for idx, achado in enumerate(res_m_po['achados'], 1):
        print(f"  {idx}. [{achado['severidade'].upper()}] Campo: '{achado['campo']}' (Etapa: {achado['etapa']})")
        print(f"     Mensagem: {achado['resumo']}")

    print("\n--- [1.2] Testando FORMATO ORIGINAL (CONFORME) ---")
    res_m_orig = validar_manifesto(SPEC_FORMATO_ORIGINAL)
    print(f"STATUS OBTIDO: {res_m_orig['status'].upper()}")
    print(f"Bloco 0 identificado: {res_m_orig['bloco0_encontrado']}")
    print(f"Total de achados: {len(res_m_orig['achados'])}")
    print("Detalhamento dos Avisos/Achados:")
    for idx, achado in enumerate(res_m_orig['achados'], 1):
        print(f"  {idx}. [{achado['severidade'].upper()}] Campo: '{achado['campo']}' (Etapa: {achado['etapa']})")
        print(f"     Mensagem: {achado['resumo']}")

    # ---------------------------------------------------------
    # TESTE 2: validar_telemetria()
    # ---------------------------------------------------------
    print("\n" + "#" * 80)
    print("PARTE 2: validar_telemetria()")
    print("#" * 80)

    print("\n--- [2.1] Testando FORMATO DO PO (na Spec/Handoff não-conforme) ---")
    res_t_po = validar_telemetria(SPEC_FORMATO_PO)
    print(f"STATUS OBTIDO: {res_t_po['status'].upper()}")
    print(f"Tabelas de eventos encontradas: {res_t_po['tabelas_eventos']}")
    print(f"Total de achados: {len(res_t_po['achados'])}")
    print("Detalhamento dos Erros:")
    for idx, achado in enumerate(res_t_po['achados'], 1):
        print(f"  {idx}. [{achado['severidade'].upper()}] Código: '{achado['codigo']}' (Etapa: {achado['etapa']})")
        print(f"     Mensagem: {achado['resumo']}")

    print("\n--- [2.2] Testando FORMATO ORIGINAL (HANDOFF CONFORME) ---")
    res_t_orig = validar_telemetria(HANDOFF_FORMATO_ORIGINAL)
    print(f"STATUS OBTIDO: {res_t_orig['status'].upper()}")
    print(f"Tabelas de eventos encontradas: {res_t_orig['tabelas_eventos']}")
    print(f"Total de achados: {len(res_t_orig['achados'])}")
    if not res_t_orig['achados']:
        print("  ✓ Nenhum achado. Telemetria em total conformidade!")

    # ---------------------------------------------------------
    # TESTE 3: SPEC REAL DO REPOSITÓRIO (Sessão Histórica de PO)
    # ---------------------------------------------------------
    caminho_po_real = Path("output/20260902-213819-session-e8be/produto/05-spec-missao.md")
    if caminho_po_real.exists():
        print("\n" + "#" * 80)
        print("PARTE 3: TESTE COM ARQUIVO REAL DO REPOSITÓRIO")
        print(f"Arquivo: {caminho_po_real}")
        print("#" * 80)
        conteudo_po_real = caminho_po_real.read_text(encoding="utf-8")
        
        m_real = validar_manifesto(conteudo_po_real)
        print(f"\nManifesto no arquivo real: {m_real['status'].upper()} ({len(m_real['achados'])} achados)")
        for a in m_real['achados'][:5]:
            print(f"  - [{a['severidade']}] {a['campo']}: {a['resumo']}")
        if len(m_real['achados']) > 5:
            print(f"  ... e mais {len(m_real['achados']) - 5} achados de bloqueio.")

        t_real = validar_telemetria(conteudo_po_real)
        print(f"\nTelemetria no arquivo real: {t_real['status'].upper()} ({len(t_real['achados'])} achados)")
        for a in t_real['achados']:
            print(f"  - [{a['severidade']}] {a['codigo']}: {a['resumo']}")

    print("\n" + "=" * 80)
    print("FIM DA BATERIA EMPÍRICA")
    print("=" * 80)


if __name__ == "__main__":
    executar_bateria()
