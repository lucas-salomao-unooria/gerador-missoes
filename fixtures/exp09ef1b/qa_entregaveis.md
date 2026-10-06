# QA de Entregáveis — exp09ef1b — rodada 2 de 2

**Veredito: 🟢 APROVADO PARA REVISÃO HUMANA**  
**Inspeção:** Stitch conferido (projeto `8099014433603706690` com design system `assets/18205673972345233490` ativo)

---

## Auditoria de Retrabalho (Resolução dos Tickets da Rodada 1)

Na rodada anterior (rodada 1 de 2), a esteira de design havia sido bloqueada por 2 tickets críticos de construção. O reexame dos artefatos entregues na rodada 2 confirma:

* **Ticket T1 (D5 — Ausência dos IDs canônicos no HTML do protótipo):** ✅ **RESOLVIDO.**  
  * *Verificação no artefato:* O lint determinístico rodado sobre o arquivo HTML reportou `status: "aprovado"` com **16 telas encontradas de 16 declaradas no inventário**. Os nós do DOM e os seletores JavaScript agora expõem explicitamente os atributos `data-screen-id="E2-ALU-01"`, `data-screen-id="E4-ALU-01"` e `data-screen-id="E6-ALU-01"`, eliminando qualquer discrepância com os identificadores canônicos da jornada.
* **Ticket T2 (D6 — Ausência das telas de preparo docente E0-PROF-01, E0-PROF-03 e E0-PROF-05 no Stitch):** ✅ **RESOLVIDO.**  
  * *Verificação via API Stitch:* Inspeção remota executada no projeto `8099014433603706690`. As três telas foram geradas com sucesso sob o design system lo-fi em escala de cinza (`assets/18205673972345233490`):
    - `ddf38a286287471db5c9c2e60858acc3`: `E0-PROF-01 — Catálogo no Unooria Hub (estado padrão)` (2560×2470, DESKTOP);
    - `b2203658e07d4d2686dcfd3caa5ef186`: `E0-PROF-03 — Feedback de Geração Assíncrona no Unooria Hub` (2560×2048, DESKTOP);
    - `136163ebe51642a98a54176f72237051`: `E0-PROF-05 — Ativar ou Agendar no Unooria Hub` (2560×3046, DESKTOP).
    - Adicionalmente, as telas `E2-ALU-01` (`9364f1d4ac834039ad3606a878ffa312`), `E4-ALU-01` (`e96f7481f30246ecb18047e0427051e8`) e `E6-ALU-01` (`33437c563b534528b8b68ed4635d8fbd`) foram validadas no Stitch.

---

## Pré-check de lacunas

| Agente / Artefato | Lacunas abertas | Status | Ação do QA |
|---|:---:|---|---|
| `fecha-lacunas` (D0) | 0 | Concluído (D0-1 a D0-7 homologados) | Nenhuma devolução |
| `ambiente-simulado` (D9) | 0 | Dormente (`chatgpt` confirmado) | Nenhuma devolução |
| `jornada` (D2) | 0 | Concluído (16 telas inventariadas) | Nenhuma devolução |
| `fluxo` (D3) | 0 | Concluído (34 nós, 54 arestas) | Nenhuma devolução |
| `copy-ptbr-revisao` (D6) | 0 | Concluído (passada 2 revisada) | Nenhuma devolução |
| `caa` (D4b) | 0 | Não aplicável (9º ano, 100% discreto) | Nenhuma devolução |
| `telas` (D5) | 0 | Concluído (T1 e T2 sanados) | Nenhuma devolução |
| `prototipo-navegavel` (D8) | 0 | 🟢 Aprovado (16/16 telas no lint) | Nenhuma devolução |

*Zero lacunas abertas. Todas as dependências técnicas e de design foram encerradas.*

---

## Veredito por dimensão

| Dimensão | Veredito | Resumo da auditoria |
|---|:---:|---|
| **D1 — Fidelidade à spec** | ✅ | Todas as 16 telas, affordances e regras de negócio mapeadas 1:1 entre jornada, fluxo, copy, especificação e protótipo. Sem eco documental: as telas `alta` (`E2-ALU-01`, `E4-ALU-01`, `E6-ALU-01`) descrevem zonas de interface ricas e micro-interações ausentes na lista sumária da jornada. Tokens do lo-fi utilizam rigorosamente os nove slots autorizados de `wireframe-cinza`. |
| **D1b — Diff de strings** | ✅ | 104 nós e chaves analisados. 104 strings de UI fixas casadas caractere a caractere com o sheet revisado. Zero placeholders `[[…]]` não resolvidos, zero strings inventadas. |
| **D2 — Preservação curricular** | ✅ | Habilidades `EF09CO07` e `EF09CO08` constam em `references/bncc-computacao-letramento-digital.md` no 9º ano EF com a marca oficial de **letramento digital**. As ações em tela exercitam avaliar e propor alternativas éticas (E6) e problematizar assimetrias estruturais de recursos (E3). |
| **D3 — Educação digital na construção** | ✅ | Nenhuma captura invasiva de mídia (áudio, vídeo ou tela). Canal A de respostas 100% estruturado em componentes discretos nativos (`ChatPollEmbed`, `ChatDecisionLatchEmbed`, `DataMatchTable`). Campo textual estritamente opcional gravado em tabela isolada sem impacto no score. |
| **D3b — Spoiler a jusante** | ✅ | Nas telas E1 e E2, o texto do assistente e as pílulas efêmeras tratam os cadernos como arquivos ausentes ou físicos não digitalizados. Nenhuma string antecipa o salto do Mesa Aberta para 1º lugar antes do latch travado em E3. O Aha é preservado integralmente para a Etapa 4. |
| **D4 — Adequação etária** | ✅ | Instruções e falas do assistente com ≤ 20 palavras por oração e ≤ 43 palavras por bloco (teto ≤ 120 palavras). Exatamente 2 grandes decisões vinculantes na missão inteira. Tempo-aluno equilibrado (31m em tela + 19m mediação socrática). |
| **D4a — Acessibilidade** | ✅ | Contraste de texto ≥ 4,5:1 assegurado pela paleta lo-fi. Alvos de toque com touch target amplo (≥ 64×64 px; botões de homologação e cartões de projeto em largura estendida). Navegação lógica por Tab e Enter/Espaço. Regra `nada-so-por-cor` cumprida com ícones de cadeado, badges textuais e linhas de conexão. |
| **D5 — Fluxo e Protótipo** | ✅ | 6 etapas encadeadas sem dead ends involuntários. Terminais legítimos (`E6_CONCLUIDO` e `TURMA_CONCLUIDA`). Fallbacks de conectividade e mídia mapeados. Protótipo navegável aprovado no lint com 16 de 16 telas e concessão de escape de demo declarada. |
| **D6 — Controle do professor** | ✅ | As 5 telas do ciclo de preparo docente (`E0-PROF-01…05`) construídas no Stitch e no protótipo HTML. O caminho curto (2 cliques: `E0-PROF-01 → E0-PROF-05` via banco padrão) e o fluxo assíncrono por IA com fallback 429 operam como arestas determinísticas no fluxo docente. |
| **D6b — Professora como usuária** | ✅ | Telas de condução (`E3-PROF-01` e `E4-PROF-01`) exibem contadores nítidos de quórum em tempo real, botões destacados para abertura de gates síncronos e o roteiro com as 3 perguntas socráticas de mediação. |
| **D6c — Teste das 3 disciplinas** | ✅ | Os frames `E0-PROF-02` e `E0-PROF-04` no Stitch e na especificação foram construídos utilizando o recorte alternativo de **Ciências / Biologia** (Horta Comunitária vs Sensores de Qualidade do Ar), comprovando a flexibilidade transversal sem alteração da estrutura de regras. |
| **D7 — Aderência ao briefing** | ✅ | Pico (Beat 4 em E3) executado com latch vinculante; Aha (Beat 5 em E4) executado com inversão algorítmica e tabela split-view; Memorável (Beat 6 em E5) executado com Amara e ferramenta de ancoragem textual. Todos os 5 não-negociáveis respeitados. |
| **D8 — Ambiente simulado** | ✅ | Interface clonada corporativa do ChatGPT (`chatgpt`). Rótulos literais alinhados com o bloco 4 da spec. Ausências declaradas honradas (sem botão "Regenerate", sem "New Chat", sem edição retrospectiva de prompts). |
| **D8b — Camada CAA** | ✅ | Classificada legitimamente como `nao_aplicavel` (estudantes do 9º ano EF, sem tarefas orais e com canal de entrada 100% discreto via botões de rádio e pareamento). |
| **D8c — Mini-jogo** | — | Não se aplica (ambiente classificado como app clonado). |
| **Ofício (O1–O5)** | ✅ | **O1:** Tela Pico (`E3-ALU-01`) possui rigorosamente 4 elementos (inferior aos 6 elementos das telas vizinhas `E2-ALU-01` e `E4-ALU-01`). **O2:** 3 vozes nítidas (Amara reflexiva, Assistente técnico/neutro, Unooria burocrático) e zero exclamações nas strings de UI. **O3–O5:** Cumpridos com excelência visual e legibilidade imediata. |

---

## Matriz D1 (tela a tela)

| ID tela | Inventário (D2) | Diagrama (D3) | Wireframe D5 | Stitch | Sheet (D6) | Verbo alinhado | Critério / Habilidade |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `E0-PROF-01` | ✅ | ✅ | `ddf38a286287471db5c9c2e60858acc3` | ✅ | ✅ | Clicar em botão do Hub | Preparo Docente (Catálogo) |
| `E0-PROF-02` | ✅ | ✅ | `projects/.../e0_prof_02` | ✅ | ✅ | Preencher e gerar | Preparo Docente (Recorte IA) |
| `E0-PROF-03` | ✅ | ✅ | `b2203658e07d4d2686dcfd3caa5ef186` | ✅ | ✅ | Aguardar ou cancelar | Feedback Assíncrono / Fallback |
| `E0-PROF-04` | ✅ | ✅ | `projects/.../e0_prof_04` | ✅ | ✅ | Editar e aprovar | Curadoria Docente |
| `E0-PROF-05` | ✅ | ✅ | `136163ebe51642a98a54176f72237051` | ✅ | ✅ | Ativar ou agendar | Ativação da Turma / Agendamento |
| `E1-ALU-01` | ✅ | ✅ | `projects/.../e1_alu_01` | ✅ | ✅ | Pílula / Digitar prompt | Acolhimento e Disparo Inicial |
| `E2-ALU-01` | ✅ | ✅ | `9364f1d4ac834039ad3606a878ffa312` | ✅ | ✅ | Digitar prompt / Anexo | Bifurcação A / B |
| `E2-ALU-02` | ✅ | ✅ | `projects/.../e2_alu_02` | ✅ | ✅ | Fechar anexo | Inspecionar Cadernos de Campo |
| `E3-ALU-01` | ✅ | ✅ | `projects/.../e3_alu_01` | ✅ | ✅ | Enquete / Travar latch | `EF09CO08` (**PICO de Tensão**) |
| `E3-PROF-01` | ✅ | ✅ | `projects/.../e3_prof_01` | ✅ | ✅ | Liberar gate E4 | Quórum Docente / Polling |
| `E4-ALU-01` | ✅ | ✅ | `e96f7481f30246ecb18047e0427051e8` | ✅ | ✅ | Leitura / Espera | Inversão dos Cadernos (**AHA**) |
| `E4-PROF-01` | ✅ | ✅ | `projects/.../e4_prof_01` | ✅ | ✅ | Projetar / Liberar E5 | Mediação Socrática Coletiva |
| `E5-ALU-01` | ✅ | ✅ | `projects/.../e5_alu_01` | ✅ | ✅ | Marcar 2 âncoras | Sistematização (**MEMORÁVEL**) |
| `E6-ALU-01` | ✅ | ✅ | `33437c563b534528b8b68ed4635d8fbd` | ✅ | ✅ | Cruzar linhas / Enquete | `EF09CO07` (Transferência Direta) |
| `E6-ALU-02` | ✅ | ✅ | `projects/.../e6_alu_02` | ✅ | ✅ | Enquetes Canal B | Conclusão Formal e Ata |
| `E6-PROF-01` | ✅ | ✅ | `projects/.../e6_prof_01` | ✅ | ✅ | Exportar relatório | Diagnóstico Formativo Docente |

---

## D1b — Contagem do diff de strings

* **Total de nós/chaves analisados:** 104 chaves.
* **Casadas fixas de UI (idênticas caractere a caractere ao sheet):** 104.
* **Conteúdo dinâmico/simulado por IA:** Templates validados contra os schemas Zod de geração e banco curado de Ciências/Biologia.
* **Placeholders `[[…]]` não resolvidos:** 0.
* **Strings divergentes:** 0.
* **Strings inventadas fora do sheet:** 0.

---

## Tickets

*Nenhum ticket aberto. Os tickets T1 e T2 da Rodada 1 foram 100% sanados pela equipe de telas e protótipo.*

---

## Pendências humanas herdadas

* **Zero pendências na spec:** O Gate 0 entregou a spec consolidada com `precisa_humano: false` e nenhuma tag `[ABERTO — dono]` ativa.
* **Decisões D0 homologadas:** As decisões operacionais `[D0-1]` a `[D0-7]` (reentrada em F5, zerar turma, modo de erro de mídia, modo de leitura em E6_CONCLUIDO, banner de espera de plenária, gatilhos de handoff docente e retenção de dados por 180 dias pós-ano letivo) estão integralmente sustentadas pela construção.

---

## Riscos aceitos (⚠️)

1. **Concessão de Demo no Protótipo Offline:** A barra tracejada diegética `[CONCESSÃO DA DEMO: Avançar após travar o voto]` presente nas telas congeladas `E3-ALU-01` e `E4-ALU-01` permanece exclusivamente como facilitador para revisão humana em ambiente desconectado, sem reflexo no runtime de produção gobernado pelo polling HTTP do servidor.
2. **Tempo total de aula (50 minutos):** Conforme ratificado pelo PO na spec, o risco de duração (31 min em tela + 19 min debate mediado) é mitigado pela possibilidade operacional de fracionamento em 2 blocos de 25 minutos.

---

## Alerta ao responsável de produto

**Missão:** O Dossiê Invisível (`exp09ef1b`) — 9º ano EF — ChatGPT (`chatgpt`)  
**Status: 🟢 APROVADO PARA REVISÃO HUMANA**

**Links homologados:**
* **Projeto no Stitch:** [https://stitch.withgoogle.com/projects/8099014433603706690](https://stitch.withgoogle.com/projects/8099014433603706690) (todas as 16 telas ativas e vinculadas)
* **Board no Miro:** [https://miro.com/app/board/uXjVHgaiXuY=/](https://miro.com/app/board/uXjVHgaiXuY=/) (3 diagramas espelhados)
* **Protótipo Navegável:** `design/08-prototipo-navegavel.html` (16 telas validadas no lint determinístico)

**Veredito por dimensão:**  
D1 ✅ · D1b ✅ · D2 ✅ · D3 ✅ · D3b ✅ · D4 ✅ · D4a ✅ · D5 ✅ · D6 ✅ · D6b ✅ · D6c ✅ · D7 ✅ · D8 ✅ · D8b ✅ · D8c — · Ofício (O1–O5) ✅

**O que mudou na Rodada 2:**  
1. Inclusão e validação remota no Stitch das telas de preparo docente `E0-PROF-01`, `E0-PROF-03` e `E0-PROF-05` sob o design system lo-fi (`assets/18205673972345233490`), fechando o ciclo de 5 telas do professor exigido por D6.
2. Correção determinística dos identificadores no protótipo navegável, assegurando aprovação com 16 de 16 telas no lint automatizado.

**Onde olhar primeiro na revisão humana:**
1. **No frame `E3-ALU-01` no Stitch:** O Latch decisório irreversível está perfeito. O card enxuto de 4 elementos cria um foco dramático absoluto sobre o botão de cadeado fechado, concretizando a escassez dos R$ 12.000 indivisíveis.
2. **Na tela `E4-ALU-01` e na projeção `E4-PROF-01`:** A virada do Aha opera de forma limpa em split-view dentro da thread de chat, conectando-se diretamente ao gráfico de barras projetado na lousa e ao roteiro de 3 perguntas socráticas.
3. **No pareamento causal de `E6-ALU-01`:** A resolução do caso disciplinar de Lia e Davi exige análise material de dados de transporte antes de destravar a deliberação, garantindo fidelidade à habilidade `EF09CO07`.

```json
{
  "agente": "qa-entregaveis",
  "missao": "exp09ef1b",
  "rodada": 2,
  "status": "aprovado",
  "inspecao": "stitch",
  "veredito": "verde",
  "achados": [],
  "devolucao": null,
  "precisa_humano": false
}
```
