---
name: premissa-imersao
description: A premissa que governa toda tela, string e critério de imersão — a fidelidade ao ambiente real é o instrumento de medida, não ornamento. Meia página, lida por quem constrói e por quem julga tela.
sources: [criterios-dev/2-design-imersao (DES-03), auditoria de imersão 20/09/2026, Sundararajan & Adesope 2020, Hamari et al. 2016]
---

# Premissa: a imersão é o instrumento de medida

Na missão Unooria, a fidelidade ao ambiente real **não é ornamento: é a condição de validade do que se mede**. Um feed que se comporta como feed real é o que torna a decisão do estudante uma decisão sobre feeds reais. Isso tem quatro consequências, e toda tela, string e critério obedece a elas.

1. **Constitutivo ou sedutor.** Um elemento é *constitutivo* quando o estudante toma alguma decisão que depende dele, ou quando é chrome nativo que o ambiente real sempre tem. Fora disso, é *detalhe sedutor*: material interessante e irrelevante ao objetivo, cujo custo sobre a aprendizagem a literatura mede em g = −0,33 (meta-análise de 68 estudos). **Teste, por elemento:** "que decisão muda se eu tirar isto?" Nenhuma, e não é chrome → corta.

2. **Imersão se perde por barreira, não se ganha por enfeite.** As barreiras conhecidas são: erro que vaza da ficção (PROD-13); marca institucional dentro do disfarce (DES-13); estado vazio ou de espera que parece tela quebrada (DES-07, O5); voz que não se distingue (O2); spoiler (Regra Zero do P0a); entrada no ambiente sem porta diegética (2.3). Construir é remover barreiras.

3. **Fidelidade tem lista.** O que o ambiente real tem e a simulação **não** tem está em `ambientes.md` (por seção) e no bloco 5 da spec (por missão). Completar a interface "por realismo" é violar a lista — e é o achado mais comum de O3.

4. **Imersão não substitui desafio.** A evidência empírica associa aprendizagem a **desafio** e engajamento, não a imersão isolada (Hamari et al. 2016; Cheng, She & Annetta 2015 — estudantes de médio e superior, não letramento digital: transfere-se o princípio, não o número). O piso de desafio (critério 6.6) é a outra metade desta premissa: uma missão fiel e fácil mede pouco.

**Onde isto se aplica:** o P0a desenha contra ela; o brief de ofício decide o que sai de propósito por ela; jornada e telas cortam por ela; o QA de design e a banca de dev julgam por ela.
