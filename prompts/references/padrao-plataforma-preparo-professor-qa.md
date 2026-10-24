---
name: padrao-plataforma-preparo-professor-qa
description: O preparo do professor na conferência do QA de design — Stitch e protótipo, o segundo grafo e o caminho curto, o teste das três disciplinas e a simulação de preparo, com os donos dos tickets. Só o QA de design inclui; a definição das cinco telas está em padrao-plataforma-preparo-professor.md.
sources: [088_qa_entregaveis, padrao-plataforma-preparo-professor, criterios-gate-estrutural, literatura-cognitiva]
status: padrão da plataforma (D7 do plano «Produto dono do contrato», 23/10/2026)
---

# Preparo do professor — na conferência do QA de design

- **Construídas no Stitch e no protótipo** — as cinco telas, verificadas na folha `stitch_links` e no trilho do protótipo, não só na jornada: tela do professor ausente do Stitch é ⛔ com dono `telas`.
- **O fluxo do professor existe como segundo grafo** no documento de fluxo e aparece no board do Miro (folha `miro_links`): ausência é ticket com dono `fluxo`. Botão de ativação do banco curado padrão, e o **caminho curto** `E0-PROF-01 → 02 → 05` («usar banco padrão», pulando geração e curadoria) presente como aresta própria no segundo grafo: ausência é ticket com dono `fluxo`. Em missão de 1º–5º, o banco padrão é a primeira ação visível de `E0-PROF-02` (4.3, teste de posição), senão ticket com dono `telas`.
- **Teste das três disciplinas.** A tela de recorte (`E0-PROF-02`) e a de curadoria (`E0-PROF-04`) mostram uma aula de disciplina **diferente do banco default** (tabela «a mesma missão em três aulas» do bloco 8)? As três linhas da tabela cabem no formulário sem mudar a mecânica, as cardinalidades ou a descoberta central? Formulário que só aceita um tipo de conteúdo, ou tela preenchida só com o default, é ticket com dono `telas`; mecânica que só funciona com um tipo de conteúdo é ⛔ com dono `gate-estrutural`, salvo `[LIMITE DE TRANSVERSALIDADE]` declarado na spec.
- **Simulação de preparo em minutos (missão de 1º–5º ano).** Percorra `E0-PROF-01…05` como a professora da rede municipal que não fez formação em tecnologia e conte telas, toques e decisões até `ativado`, pelo caminho curto e pelo caminho com IA; a contagem vai no relatório e confere com a seção 9a da spec (contagem de preparo, `[CONVENÇÃO]` — acordo interno, não medida: `literatura-cognitiva.md` §6 registra o preparo docente sem tempo medido).
