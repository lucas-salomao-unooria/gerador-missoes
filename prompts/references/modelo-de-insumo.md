# Modelo de insumo — especificação de missão imersiva

Entregue este documento preenchido (PO + Designer, juntos) para a banca de
validação (`/validar-missao`). Cada seção espelha os critérios que serão
avaliados; seção vazia = NOK na validação. Onde houver dúvida, escreva a
dúvida — dúvida declarada é melhor que lacuna silenciosa.

## 1. Identificação
- **Slug**: `expNNefNb`
- **Nome da missão** (título que o estudante vê):
- **Série(s)**: `["4EF"]` / `["2EM"]` / `[]` (transversal)
- **Produto** (manifesto, ADR-87): `entre-redes` / `plano-de-aula` / `plano-de-ensino` / `bem-estar`
- **Unidade da trilha** (manifesto `unidade` 1–4, ordena a grade da sala — ADR-69):
- **Público**: `estudante` / `professor`
- **Liberação**: por turma (ADR-69) — como a professora libera e o que o estudante vê bloqueado
- **Software clonado** (ou "mundo próprio"):
- **Seção do design system**: existente (`instanooria`/`unitube`/`chatgpt`/
  `whatsappmobile`/`tiktooria`) ou nova (listar componentes a criar no
  storybook-unooria, com responsável e prazo)

## 2. Premissa e objetivos
- **Premissa em UMA frase**:
- **Objetivo do estudante DENTRO da ficção**:
- **Objetivo pedagógico** (o que de fato se quer que aconteça):

## 3. Habilidades e evidências (a matriz)
| Habilidade BNCC (código) | Evidência observável | Interação que a captura | Dado gravado (evento/tabela) |
|---|---|---|---|

- **O que é medida e o que é cosmético** (item a item):
- **Gabarito**: fonte da verdade, e a declaração de que vive **exclusivamente no servidor**:
- **Nota/score**: existe? qual, em que escala? Se não existe, por quê:
- **Graus de medida**: o que conta como scored / indicative / zero / none:

## 4. Fluxo da missão
- **Estados nomeados, em ordem** (entrada → … → conclusão → pós):
- **Reentrada**: F5 no meio / voltar noutro dia / reiniciar:
- **Estados latch** (o que nunca regride) e **o que congela** após o score:
- **Conclusão**: quem fecha, como, o que reporta:
- **Segunda aplicação**: o que re-sorteia, o que preserva, o que "zerar turma"
  apaga:
- **Dependências de outras missões** + comportamento sem elas:

## 5. Revelação (escolher UMA)
- [ ] **No software** — roteiro tela a tela em anexo, com as variações por
      situação real do estudante (a revelação não pode mentir)
- [ ] **No debate do professor** — roteiro do debate em anexo (perguntas, o que
      projetar, tempo)
- [ ] **Híbrida** — descrever

## 6. Papel do professor
- **Preparo e parametrização** (tela `E0-PROF-01`): inputs do professor (tema/contexto local, palavras-chave, restrições e nível de desafio), geração de pacote de conteúdo imersivo via IA com curadoria humana (aprovar / regenerar / editar posts e personas), ativação do banco curado padrão (`default_fallback`):
- **Largada/relógio coletivo e ritmo** (se síncrona): ações, controle de liberação de etapas/checkpoints e efeitos:
- **Acompanhamento ao vivo**: o que vê, controle de pausas/congelamento de tela e O QUE PEDE AÇÃO:
- **Leitura individual** (por criança) vs **visão de turma** vs **gestor (só
  agregado)**:
- **Ações destrutivas** (zerar turma: apaga o quê, preserva o quê):

## 7. Design
- **Referências visuais do clone** e o que deliberadamente difere:
- **Mapa "quem está falando"** por tela (clone × plataforma):
- **Viewport**: casca de aparelho 375×812 ou desktop, e por quê:
- **Permissões de iframe** (`forms`? `pointer-lock`? `downloads`?), derivadas das interações (a rota do hub precisa repassar ao `ExpFrame`, ADR-76):
- **Estados de cada tela**: vazio / carregando / erro / ponto cego ("não
  sabemos", nunca "0"):
- **Copy final** (não placeholder), com tom para a série:
- **Assets**: inventário com pesos (>2MB → bucket):
- **Interações instrumentadas** (as que viram dado — não mudar sem avisar):

## 8. Dados
- **Vocabulário de telemetria** (`verbo` / `objeto` em `namespace:slug` / `resultado` / `contexto` / significado — **não existe campo `dados`**) e **onde cada medida é lida** (tabela `expNNefNb_*` + rota do professor):
- **Caminho de cada dado**: operacional (rota do próprio módulo → `expNNefNb_sessoes`) × analítico (`track` → Pub/Sub) × erro × vital × trace:
- **Relógio coletivo** (largada, pausa, virada): existe? → `expNNefNb_gates_turma` por polling curto (ADR-93/94), etapas e quem transiciona:
- **Entidades a persistir** (tabelas `expNNefNb_*` com PK, `turma_id` denormalizado, `versao_instrumento`, `tentativa`; `expNNefNb_conteudo_turma` quando há preparação docente; exceções de RLS justificadas):
- **Lista do que NUNCA vai ao bundle** (gabarito, parâmetros, calibragem,
  prompts de geração) — será verificada por grep no dist/:
- **Payload bruto + versão do instrumento** (reprocessamento):
- **Texto livre de menor**: existe? por quê? quem lê?:
- **Dado sensível (art. 11)?** Se sim, regras de acesso:
- **Retenção** por tabela (ou lacuna assumida por escrito):

## 9. IA e Geração de Conteúdo
- **Onde a IA entra**: geração de conteúdo e postagens na preparação docente (`POST /<slug>/preparar/gerar-conteudo`), com curadoria humana antes da aula (nunca durante a execução do aluno sem supervisão); motor determinístico em sala:
- **Contrato de geração**: prompt de sistema, schema Zod de saída validado estritamente, variáveis injetadas:
- **O que a IA NUNCA decide**: avaliação formal do aluno, pontuação/score, verdades curriculares determinísticas:
- **Comportamento sem IA e Fallback**: ativação automática ou manual do banco curado padrão (`banco_default`), garantindo execução 100% offline ou sem quota:
- **Estimativa de tokens por turma/sessão de preparação** e **perfil de quota consumido** (`ia_quotas` por perfil, editável só pelo `admin` — ADR-105); o que acontece sem saldo (429):

## 10. Modos de erro
- O que o estudante vê quando: a rede cai / a IA falha / a quota acaba —
  sempre na voz da ficção:

## 11. Conteúdo autoral
- **Inventário** (quantos vídeos/fontes/mensagens/personas), quem produz,
  critério de revisão:

## 12. Validação pedagógica
- **Plano de playtest** (papel/piloto), critérios de sucesso:

## 13. Anexos
- Roteiro da revelação OU do debate
- Wireframes/protótipo
- Conteúdo autoral (rascunho)
