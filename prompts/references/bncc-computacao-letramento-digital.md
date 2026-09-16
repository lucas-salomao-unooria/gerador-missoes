---
name: bncc-computacao-letramento-digital
description: Todas as habilidades da BNCC Computação por ano (Resolução CNE/CEB 1/2022), com eixo e a marca de letramento digital. Fonte única: references/bncc-computacao.json (gerado por scripts/gerar_bncc_referencia.py). Lido pela avaliação pedagógica (5.1/5.2), pela spec (bloco 11) e pelo QA de entregáveis (D2); o gate determinístico BnccCheck usa o JSON.
sources: [https://www.gov.br/mec/pt-br/escolas-conectadas/arquivos/BNCCComputaoCompletodiagramado.pdf]
---

# BNCC Computação — habilidades por ano e o que é letramento digital

> **Gerado automaticamente** de `bncc-computacao.json` por `scripts/gerar_bncc_referencia.py`. Não edite à mão. Fonte: BNCC Computação — Complemento à BNCC (Resolução CNE/CEB nº 1, de 4 de outubro de 2022; Parecer CNE/CEB nº 2/2022) — [https://www.gov.br/mec/pt-br/escolas-conectadas/arquivos/BNCCComputaoCompletodiagramado.pdf](https://www.gov.br/mec/pt-br/escolas-conectadas/arquivos/BNCCComputaoCompletodiagramado.pdf) (SHA-256 `60aab0b192ac…`, conferido em 2026-09-16). Ensino Fundamental (EF01–EF09, EF15, EF69; páginas 12–58 do documento) e Ensino Médio (EM13CO01–26; páginas 61–70 do documento, tabela única por competência específica, sem separação por série). Educação Infantil (EI03CO01–11) fora do escopo das missões.

## As três regras que a esteira aplica

1. **Só existe o que está aqui.** Código de habilidade que não aparece nesta lista não existe. Spec, one-pager ou relatório que cite código fora da lista é ⛔ — não é ressalva, é bloqueio.
2. **Ano bate com ano.** `EF0n` vale só para o n-º ano; `EF15` vale para qualquer ano do 1º ao 5º; `EF69` para qualquer ano do 6º ao 9º; `EM13` só para o Ensino Médio. Habilidade de outro ano na missão é ⛔.
3. **Letramento digital é obrigatório no Fundamental.** Toda missão de 1º a 9º ano exercita pelo menos uma habilidade do eixo Cultura Digital (marcada **letramento digital** abaixo). Pensamento Computacional e Mundo Digital podem entrar como secundárias, nunca como o núcleo que justifica a missão. No Ensino Médio o anexo não tem eixo: a missão precisa citar pelo menos uma habilidade `EM13` (não todas), e a marca de letramento digital é leitura proposta que orienta a avaliação pedagógica sem bloquear.

Essas três regras são conferidas por um gate **determinístico** (`BnccCheck`, depois da spec) que trava a esteira quando falham, e são lidas pelos agentes LLM (avaliação pedagógica 5.1/5.2, spec bloco 11, QA de entregáveis D2) para julgar o que a máquina não julga: se a ação em tela exercita de fato a habilidade.

---

## Ensino Fundamental

### 1º ano

7 habilidades · letramento digital: `EF01CO06`, `EF01CO07`

| Eixo | Código | Objeto de conhecimento | Habilidade | Letramento digital |
|---|---|---|---|---|
| Pensamento Computacional | `EF01CO01` | Organização de objetos | Organizar objetos físicos ou digitais considerando diferentes características para esta organização, explicitando semelhanças (padrões) e diferenças. | — |
| Pensamento Computacional | `EF01CO02` | Conceituação de Algoritmos | Identificar e seguir sequências de passos aplicados no dia a dia para resolver problemas. | — |
| Pensamento Computacional | `EF01CO03` | Conceituação de Algoritmos | Reorganizar e criar sequências de passos em meios físicos ou digitais, relacionando essas sequências à palavra ‘Algoritmos’. | — |
| Mundo Digital | `EF01CO04` | Codificação da informação | Reconhecer o que é a informação, que ela pode ser armazenada, transmitida como mensagem por diversos meios e descrita em várias linguagens. | — |
| Mundo Digital | `EF01CO05` | Codificação da informação | Representar informação usando diferentes codificações. | — |
| Cultura Digital | `EF01CO06` | Uso de artefatos computacionais | Reconhecer e explorar artefatos computacionais voltados a atender necessidades pessoais ou coletivas. | **letramento digital** |
| Cultura Digital | `EF01CO07` | Segurança e responsabilidade no uso de tecnologia computacional | Conhecer as possibilidades de uso seguro das tecnologias computacionais para proteção dos dados pessoais e para garantir a própria segurança. | **letramento digital** |

### 2º ano

6 habilidades · letramento digital: `EF02CO05`, `EF02CO06`

| Eixo | Código | Objeto de conhecimento | Habilidade | Letramento digital |
|---|---|---|---|---|
| Pensamento Computacional | `EF02CO01` | Modelagem de objetos | Criar e comparar modelos (representações) de objetos, identificando padrões e atributos essenciais. | — |
| Pensamento Computacional | `EF02CO02` | Algoritmos com repetições simples | Criar e simular algoritmos representados em linguagem oral, escrita ou pictográfica, construídos como sequências com repetições simples (iterações definidas) com base em instruções preestabelecidas ou criadas, analisando como a precisão da instrução impacta na execução do algoritmo. | — |
| Mundo Digital | `EF02CO03` | Instrução de máquina | Identificar que máquinas diferentes executam conjuntos próprios de instruções e que podem ser usadas para definir algoritmos. | — |
| Mundo Digital | `EF02CO04` | Hardware e software | Diferenciar componentes físicos (hardware) e programas que fornecem as instruções (software) para o hardware. | — |
| Cultura Digital | `EF02CO05` | Uso de artefatos computacionais | Reconhecer as características e usos das tecnologias computacionais no cotidiano dentro e fora da escola. | **letramento digital** |
| Cultura Digital | `EF02CO06` | Segurança e responsabilidade no uso de tecnologia computacional | Reconhecer os cuidados com a segurança no uso de dispositivos computacionais. | **letramento digital** |

### 3º ano

9 habilidades · letramento digital: `EF03CO07`, `EF03CO08`, `EF03CO09`

| Eixo | Código | Objeto de conhecimento | Habilidade | Letramento digital |
|---|---|---|---|---|
| Pensamento Computacional | `EF03CO01` | Lógica computacional | Associar os valores 'verdadeiro' e 'falso' a sentenças lógicas que dizem respeito a situações do dia a dia, fazendo uso de termos que indicam negação. | — |
| Pensamento Computacional | `EF03CO02` | Algoritmos com repetições condicionais simples | Criar e simular algoritmos representados em linguagem oral, escrita ou pictográfica, que incluam sequências e repetições simples com condição (iterações indefinidas), para resolver problemas de forma independente e em colaboração. | — |
| Pensamento Computacional | `EF03CO03` | Decomposição | Aplicar a estratégia de decomposição para resolver problemas complexos, dividindo esse problema em partes menores, resolvendo-as e combinando suas soluções. | — |
| Mundo Digital | `EF03CO04` | Codificação da informação | Relacionar o conceito de informação com o de dado. | — |
| Mundo Digital | `EF03CO05` | Codificação da informação | Compreender que dados são estruturados em formatos específicos dependendo da informação armazenada. | — |
| Mundo Digital | `EF03CO06` | Interface física | Reconhecer que, para um computador realizar tarefas, ele se comunica com o mundo exterior com o uso de interfaces físicas (dispositivos de entrada e saída). | — |
| Cultura Digital | `EF03CO07` | Uso de tecnologias computacionais | Utilizar diferentes navegadores e ferramentas de busca para pesquisar e acessar informações. | **letramento digital** |
| Cultura Digital | `EF03CO08` | Uso de tecnologias computacionais | Usar ferramentas computacionais em situações didáticas para se expressar em diferentes formatos digitais. | **letramento digital** |
| Cultura Digital | `EF03CO09` | Segurança e responsabilidade no uso da tecnologia | Reconhecer o potencial impacto do compartilhamento de informações pessoais ou de seus pares em meio digital. | **letramento digital** |

### 4º ano

8 habilidades · letramento digital: `EF04CO06`, `EF04CO07`, `EF04CO08`

| Eixo | Código | Objeto de conhecimento | Habilidade | Letramento digital |
|---|---|---|---|---|
| Pensamento Computacional | `EF04CO01` | Matrizes e registros | Reconhecer objetos do mundo real e/ou digital que podem ser representados através de matrizes que estabelecem uma organização na qual cada componente está em uma posição definida por coordenadas, fazendo manipulações simples sobre estas representações. | — |
| Pensamento Computacional | `EF04CO02` | Matrizes e registros | Reconhecer objetos do mundo real e/ou digital que podem ser representados através de registros que estabelecem uma organização na qual cada componente é identificado por um nome, fazendo manipulações sobre estas representações. | — |
| Pensamento Computacional | `EF04CO03` | Algoritmos com repetições simples e aninhadas | Criar e simular algoritmos representados em linguagem oral, escrita ou pictográfica, que incluam sequências e repetições simples e aninhadas (iterações definidas e indefinidas), para resolver problemas de forma independente e em colaboração. | — |
| Mundo Digital | `EF04CO04` | Codificação da informação | Entender que para guardar, manipular e transmitir dados deve-se codificá-los de alguma forma que seja compreendida pela máquina (formato digital). | — |
| Mundo Digital | `EF04CO05` | Codificação da informação | Codificar diferentes informações para representação em computador (binária, ASCII, atributos de pixel, como RGB etc.). | — |
| Cultura Digital | `EF04CO06` | Uso de tecnologias computacionais | Usar diferentes ferramentas computacionais para criação de conteúdo (textos, apresentações, vídeos etc.). | **letramento digital** |
| Cultura Digital | `EF04CO07` | Segurança e responsabilidade no uso da tecnologia | Demonstrar postura ética nas atividades de coleta, transferência, guarda e uso de dados. | **letramento digital** |
| Cultura Digital | `EF04CO08` | Segurança e responsabilidade no uso da tecnologia | Reconhecer a importância de verificar a confiabilidade das fontes de informações obtidas na Internet. | **letramento digital** |

### 5º ano

11 habilidades · letramento digital: `EF05CO08`, `EF05CO09`, `EF05CO10`, `EF05CO11`

| Eixo | Código | Objeto de conhecimento | Habilidade | Letramento digital |
|---|---|---|---|---|
| Pensamento Computacional | `EF05CO01` | Listas e grafos | Reconhecer objetos do mundo real e/ou digital que podem ser representados através de listas que estabelecem uma organização na qual há um número variável de itens dispostos em sequência, fazendo manipulações simples sobre estas representações. | — |
| Pensamento Computacional | `EF05CO02` | Listas e grafos | Reconhecer objetos do mundo real e digital que podem ser representados através de grafos que estabelecem uma organização com uma quantidade variável de vértices conectados por arestas, fazendo manipulações simples sobre estas representações. | — |
| Pensamento Computacional | `EF05CO03` | Lógica computacional | Realizar operações de negação, conjunção e disjunção sobre sentenças lógicas e valores 'verdadeiro' e 'falso'. | — |
| Pensamento Computacional | `EF05CO04` | Algoritmos com seleção condicional | Criar e simular algoritmos representados em linguagem oral, escrita ou pictográfica, que incluam sequências, repetições e seleções condicionais para resolver problemas de forma independente e em colaboração. | — |
| Mundo Digital | `EF05CO05` | Arquitetura de computadores | Identificar os componentes principais de um computador (dispositivos de entrada/saída, processadores e armazenamento). | — |
| Mundo Digital | `EF05CO06` | Armazenamento de dados | Reconhecer que os dados podem ser armazenados em um dispositivo local ou remoto. | — |
| Mundo Digital | `EF05CO07` | Sistema operacional | Reconhecer a necessidade de um sistema operacional para a execução de programas e gerenciamento do hardware. | — |
| Cultura Digital | `EF05CO08` | Segurança e responsabilidade no uso da tecnologia | Acessar as informações na Internet de forma crítica para distinguir os conteúdos confiáveis de não confiáveis. | **letramento digital** |
| Cultura Digital | `EF05CO09` | Segurança e responsabilidade no uso da tecnologia | Usar informações considerando aplicações e limites dos direitos autorais em diferentes mídias digitais. | **letramento digital** |
| Cultura Digital | `EF05CO10` | Uso de tecnologias computacionais | Expressar-se crítica e criativamente na compreensão das mudanças tecnológicas no mundo do trabalho e sobre a evolução da sociedade. | **letramento digital** |
| Cultura Digital | `EF05CO11` | Uso de tecnologias computacionais | Identificar a adequação de diferentes tecnologias computacionais na resolução de problemas. | **letramento digital** |

### Integradas 1º–5º ano (EF15)

9 habilidades · letramento digital: `EF15CO08`, `EF15CO09`

| Eixo | Código | Objeto de conhecimento | Habilidade | Letramento digital |
|---|---|---|---|---|
| Pensamento Computacional | `EF15CO01` | Organização e representação da informação | Identificar as principais formas de organizar e representar a informação de maneira estruturada (matrizes, registros, listas e grafos) ou não estruturada (números, palavras, valores verdade). | — |
| Pensamento Computacional | `EF15CO02` | Algoritmos | Construir e simular algoritmos, de forma independente ou em colaboração, que resolvam problemas simples e do cotidiano com uso de sequências, seleções condicionais e repetições de instruções. | — |
| Pensamento Computacional | `EF15CO03` | Lógica computacional | Realizar operações de negação, conjunção e disjunção sobre sentenças lógicas e valores 'verdadeiro' e 'falso'. | — |
| Pensamento Computacional | `EF15CO04` | Decomposição | Aplicar a estratégia de decomposição para resolver problemas complexos, dividindo esse problema em partes menores, resolvendo-as e combinando suas soluções. | — |
| Mundo Digital | `EF15CO05` | Codificação da informação | Codificar a informação de diferentes formas, entendendo a importância desta codificação para o armazenamento, manipulação e transmissão em dispositivos computacionais. | — |
| Mundo Digital | `EF15CO06` | Funcionamento de dispositivos computacionais | Conhecer os componentes básicos de dispositivos computacionais, entendendo os princípios de seu funcionamento. | — |
| Mundo Digital | `EF15CO07` | Sistema Operacional | Conhecer o conceito de Sistema Operacional e sua importância na integração entre software e hardware. | — |
| Cultura Digital | `EF15CO08` | Uso de artefatos computacionais | Reconhecer e utilizar tecnologias computacionais para pesquisar e acessar informações, expressar-se crítica e criativamente e resolver problemas. | **letramento digital** |
| Cultura Digital | `EF15CO09` | Segurança e responsabilidade no uso de tecnologia computacional | Entender que as tecnologias devem ser utilizadas de maneira segura, ética e responsável, respeitando direitos autorais, de imagem e as leis vigentes. | **letramento digital** |

### 6º ano

10 habilidades · letramento digital: `EF06CO09`, `EF06CO10`

| Eixo | Código | Objeto de conhecimento | Habilidade | Letramento digital |
|---|---|---|---|---|
| Pensamento Computacional | `EF06CO01` | Programação · Tipos de dados | Classificar informações, agrupando-as em coleções (conjuntos) e associando cada coleção a um ‘tipo de dados’ | — |
| Pensamento Computacional | `EF06CO02` | Programação · Linguagem de programação | Elaborar algoritmos que envolvam instruções sequenciais, de repetição e de seleção usando uma linguagem de programação. | — |
| Pensamento Computacional | `EF06CO03` | Programação · Linguagem de programação | Descrever com precisão a solução de um problema, construindo o programa que implementa a solução descrita. | — |
| Pensamento Computacional | `EF06CO04` | Estratégias de solução de problemas · Decomposição | Construir soluções de problemas usando a técnica de decomposição e automatizar tais soluções usando uma linguagem de programação. | — |
| Pensamento Computacional | `EF06CO05` | Estratégias de solução de problemas · Generalização | Identificar os recursos ou insumos necessários (entradas) para a resolução de problemas, bem como os resultados esperados (saídas), determinando os respectivos tipos de dados, e estabelecendo a definição de problema como uma relação entre entrada e saída. | — |
| Pensamento Computacional | `EF06CO06` | Estratégias de solução de problemas · Generalização | Comparar diferentes casos particulares (instâncias) de um mesmo problema, identificando as semelhanças e diferenças entre eles, e criar um algoritmo para resolver todos, fazendo uso de variáveis (parâmetros) para permitir o tratamento de todos os casos de forma genérica. | — |
| Mundo Digital | `EF06CO07` | Armazenamento e Transmissão de dados · Fundamentos de transmissão de dados | Entender o processo de transmissão de dados, como a informação é quebrada em pedaços, transmitida em pacotes através de múltiplos equipamentos, e reconstruída no destino. | — |
| Mundo Digital | `EF06CO08` | Armazenamento e Transmissão de dados · Gestão de dados | Compreender e utilizar diferentes formas de armazenar, manipular, compactar e recuperar arquivos, documentos e metadados. | — |
| Cultura Digital | `EF06CO09` | Segurança e responsabilidade no uso da tecnologia · Tecnologia digital e sociedade | Apresentar conduta e linguagem apropriadas ao se comunicar em ambiente digital, considerando a ética e o respeito. | **letramento digital** |
| Cultura Digital | `EF06CO10` | Uso de tecnologias computacionais · Tecnologia digital e sustentabilidade | Analisar o consumo de tecnologia na sociedade, compreendendo criticamente o caminho da produção dos recursos bem como aspectos ligados à obsolescência e a sustentabilidade. | **letramento digital** |

### 7º ano

11 habilidades · letramento digital: `EF07CO08`, `EF07CO09`, `EF07CO10`, `EF07CO11`

| Eixo | Código | Objeto de conhecimento | Habilidade | Letramento digital |
|---|---|---|---|---|
| Pensamento Computacional | `EF07CO01` | Programação · Programação usando registros e matrizes | Criar soluções de problemas para os quais seja adequado o uso de registros e matrizes unidimensionais para descrever suas informações e automatizá-las usando uma linguagem de programação. | — |
| Pensamento Computacional | `EF07CO02` | Programação · Análise de programas | Analisar programas para detectar e remover erros, ampliando a confiança na sua correção. | — |
| Pensamento Computacional | `EF07CO03` | Programação · Projetos com programação | Construir soluções computacionais de problemas de diferentes áreas do conhecimento, de forma individual e colaborativa, selecionando as estruturas de dados e técnicas adequadas, aperfeiçoando e articulando saberes escolares. | — |
| Pensamento Computacional | `EF07CO04` | Programação · Propriedades de grafos | Explorar propriedades básicas de grafos. | — |
| Pensamento Computacional | `EF07CO05` | Estratégias de solução de problemas · Reúso | Criar algoritmos fazendo uso da decomposição e do reúso no processo de solução de forma colaborativa e cooperativa e automatizá-los usando uma linguagem de programação. | — |
| Mundo Digital | `EF07CO06` | Armazenamento e Transmissão de dados · Protocolos de comunicação em redes | Compreender o papel de protocolos para a transmissão de dados. | — |
| Mundo Digital | `EF07CO07` | Armazenamento e Transmissão de dados · Fundamentos de Segurança Cibernética | Identificar problemas de segurança cibernética e experimentar formas de proteção. | — |
| Cultura Digital | `EF07CO08` | Segurança e responsabilidade no uso da tecnologia · Cyberbullying | Demonstrar empatia sobre opiniões divergentes na web. | **letramento digital** |
| Cultura Digital | `EF07CO09` | Segurança e responsabilidade no uso da tecnologia · Cyberbullying | Reconhecer e debater sobre cyberbullying. | **letramento digital** |
| Cultura Digital | `EF07CO10` | Uso de tecnologias computacionais · Impactos da tecnologia digital | Identificar os impactos ambientais do descarte de peças de computadores e eletrônicos, bem como sua relação com a sustentabilidade. | **letramento digital** |
| Cultura Digital | `EF07CO11` | Uso de tecnologias computacionais · Produção Digital | Criar, documentar e publicar, de forma individual ou colaborativa, produtos (vídeos, podcasts, web sites) usando recursos de tecnologia. | **letramento digital** |

### 8º ano

11 habilidades · letramento digital: `EF08CO07`, `EF08CO08`, `EF08CO09`, `EF08CO10`, `EF08CO11`

| Eixo | Código | Objeto de conhecimento | Habilidade | Letramento digital |
|---|---|---|---|---|
| Pensamento Computacional | `EF08CO01` | Programação · Programação com listas e recursão | Construir soluções de problemas usando a técnica de recursão e automatizar tais soluções usando uma linguagem de programação. | — |
| Pensamento Computacional | `EF08CO02` | Programação · Programação com listas e recursão | Criar soluções de problemas para os quais seja adequado o uso de listas para descrever suas informações e automatizá-las usando uma linguagem de programação, empregando ou não a recursão como uma técnica de resolver o problema. | — |
| Pensamento Computacional | `EF08CO03` | Programação · Algoritmos clássicos | Utilizar algoritmos clássicos de manipulação sobre listas. | — |
| Pensamento Computacional | `EF08CO04` | Programação · Projetos com programação | Construir soluções computacionais de problemas de diferentes áreas do conhecimento, de forma individual e colaborativa, selecionando as estruturas de dados e técnicas adequadas, aperfeiçoando e articulando saberes escolares. | — |
| Mundo Digital | `EF08CO05` | Sistemas distribuídos e internet · Fundamentos de sistemas distribuídos | Compreender os conceitos de paralelismo, concorrência e armazenamento/processamento distribuídos. | — |
| Mundo Digital | `EF08CO06` | Sistemas distribuídos e internet · Internet | Entender como é a estrutura e funcionamento da internet. | — |
| Cultura Digital | `EF08CO07` | Segurança e responsabilidade no uso da tecnologia · Redes sociais e segurança da informação | Compartilhar informações por meio de redes sociais, compreendendo a sua dinâmica de funcionamento, de forma responsável e avaliando sua confiabilidade, considerando o respeito e a ética. | **letramento digital** |
| Cultura Digital | `EF08CO08` | Segurança e responsabilidade no uso da tecnologia · Redes sociais e segurança da informação | Distinguir os tipos de dados pessoais que são solicitados em espaços digitais e os riscos associados. | **letramento digital** |
| Cultura Digital | `EF08CO09` | Segurança e responsabilidade no uso da tecnologia · Redes sociais e segurança da informação | Analisar criticamente as políticas de termos de uso das redes sociais e demais plataformas. | **letramento digital** |
| Cultura Digital | `EF08CO10` | Segurança e responsabilidade no uso da tecnologia · Segurança em ambientes virtuais | Discutir questões sobre segurança e privacidade relacionadas ao uso dos ambientes virtuais. | **letramento digital** |
| Cultura Digital | `EF08CO11` | Uso de tecnologias computacionais · Uso crítico das mídias digitais | Avaliar a precisão, relevância, adequação, abrangência e vieses que ocorrem em fontes de informação eletrônica. | **letramento digital** |

### 9º ano

10 habilidades · letramento digital: `EF09CO06`, `EF09CO07`, `EF09CO08`, `EF09CO09`, `EF09CO10`

| Eixo | Código | Objeto de conhecimento | Habilidade | Letramento digital |
|---|---|---|---|---|
| Pensamento Computacional | `EF09CO01` | Programação · Programação usando grafos e árvores | Criar soluções de problemas para os quais seja adequado o uso de árvores e grafos para descrever suas informações e automatizá-las usando uma linguagem de programação. | — |
| Pensamento Computacional | `EF09CO02` | Programação · Projetos com programação | Construir soluções computacionais de problemas de diferentes áreas do conhecimento, de forma individual e colaborativa, selecionando as estruturas de dados e técnicas adequadas, aperfeiçoando e articulando saberes escolares. | — |
| Pensamento Computacional | `EF09CO03` | Programação · Autômatos e linguagens baseadas em eventos | Usar autômatos para descrever comportamentos de forma abstrata automatizando-os através de uma linguagem de programação baseada em eventos. | — |
| Mundo Digital | `EF09CO04` | Sistemas distribuídos e internet · Segurança cibernética | Compreender o funcionamento de malwares e outros ataques cibernéticos. | — |
| Mundo Digital | `EF09CO05` | Sistemas distribuídos e internet · Segurança cibernética | Analisar técnicas de criptografia para armazenamento e transmissão de dados. | — |
| Cultura Digital | `EF09CO06` | Segurança e responsabilidade no uso da tecnologia · Tecnologia digital e sociedade | Analisar problemas sociais de sua cidade e estado a partir de ambientes digitais, propondo soluções. | **letramento digital** |
| Cultura Digital | `EF09CO07` | Segurança e responsabilidade no uso da tecnologia · Tecnologia digital e sociedade | Avaliar aplicações e implicações políticas, socioambientais e culturais das tecnologias digitais para propor alternativas aos desafios do mundo contemporâneo, incluindo aqueles relativos ao mundo do trabalho. | **letramento digital** |
| Cultura Digital | `EF09CO08` | Segurança e responsabilidade no uso da tecnologia · Tecnologia digital e sociedade | Discutir como a distribuição desigual de recursos de computação em uma economia global levanta questões de equidade, acesso e poder. | **letramento digital** |
| Cultura Digital | `EF09CO09` | Segurança e responsabilidade no uso da tecnologia · Autoria em meio digital | Criar ou utilizar conteúdo em meio digital, compreendendo questões éticas relacionadas a direitos autorais e de uso de imagem. | **letramento digital** |
| Cultura Digital | `EF09CO10` | Uso de tecnologias computacionais · Qualidade da informação | Avaliar a veracidade, credibilidade e relevância da informação em seus diferentes formatos, sendo capaz de identificar o propósito pelo qual foi disseminada. | **letramento digital** |

### Integradas 6º–9º ano (EF69)

12 habilidades · letramento digital: `EF69CO11`, `EF69CO12`

| Eixo | Código | Objeto de conhecimento | Habilidade | Letramento digital |
|---|---|---|---|---|
| Pensamento Computacional | `EF69CO01` | Programação · Tipos de dados | Classificar informações, agrupando-as em coleções (conjuntos) e associando cada coleção a um ‘tipo de dado’. | — |
| Pensamento Computacional | `EF69CO02` | Programação · Linguagem de programação | Elaborar algoritmos que envolvam instruções sequenciais, de repetição e de seleção usando uma linguagem de programação. | — |
| Pensamento Computacional | `EF69CO03` | Programação · Linguagem de programação | Descrever com precisão a solução de um problema, construindo o programa que implementa a solução descrita. | — |
| Pensamento Computacional | `EF69CO04` | Estratégias de solução de problemas · Decomposição | Construir soluções de problemas usando a técnica de decomposição e automatizar tais soluções usando uma linguagem de programação. | — |
| Pensamento Computacional | `EF69CO05` | Estratégias de solução de problemas · Generalização | Identificar os recursos ou insumos necessários (entradas) para a resolução de problemas, bem como os resultados esperados (saídas), determinando os respectivos tipos de dados, e estabelecendo a definição de problema como uma relação entre entrada e saída. | — |
| Pensamento Computacional | `EF69CO06` | Estratégias de solução de problemas · Generalização | Comparar diferentes casos particulares (instâncias) de um mesmo problema, identificando as semelhanças e diferenças entre eles, e criar um algoritmo para resolver todos, fazendo uso de variáveis (parâmetros) para permitir o tratamento de todos os casos de forma genérica. | — |
| Mundo Digital | `EF69CO07` | Armazenamento e Transmissão de dados · Fundamentos de transmissão de dados | Entender o processo de transmissão de dados, como a informação é quebrada em pedaços, transmitida em pacotes através de múltiplos equipamentos, e reconstruída no destino. | — |
| Mundo Digital | `EF69CO08` | Armazenamento e Transmissão de dados · Gestão de dados | Compreender e utilizar diferentes formas de armazenar, manipular, compactar e recuperar arquivos, documentos e metadados. | — |
| Mundo Digital | `EF69CO09` | Sistemas distribuídos e internet · Fundamentos de sistemas distribuídos | Compreender os conceitos de paralelismo, concorrência e armazenamento/processamento distribuídos. | — |
| Mundo Digital | `EF69CO10` | Sistemas distribuídos e internet · Internet | Entender como é a estrutura e funcionamento da internet. | — |
| Cultura Digital | `EF69CO11` | Segurança e responsabilidade no uso da tecnologia · Tecnologia digital e sociedade | Apresentar conduta e linguagem apropriadas ao se comunicar em ambiente digital, considerando a ética e o respeito. | **letramento digital** |
| Cultura Digital | `EF69CO12` | Uso de tecnologias computacionais · Tecnologia digital e sustentabilidade | Analisar o consumo de tecnologia na sociedade, compreendendo criticamente o caminho da produção dos recursos bem como aspectos ligados à obsolescência e a sustentabilidade. | **letramento digital** |

---

## Ensino Médio (EM13)

Páginas 61–70 do documento. O anexo organiza as habilidades do Médio por **competência específica**, numa tabela única, sem coluna de eixo e sem separação por série. O Ensino Médio não separa por série nem por eixo: as 26 habilidades EM13 valem para qualquer série (1ª–3ª) e estão organizadas por competência específica. A missão de EM precisa citar pelo menos uma habilidade EM13 existente — não todas. A marca de letramento digital no EM é uma leitura proposta pela Unooria (sem eixo oficial): orienta a avaliação pedagógica, mas não bloqueia a esteira.

**Letramento digital no EM (proposta Unooria):** `EM13CO08` · `EM13CO09` · `EM13CO10` · `EM13CO14` · `EM13CO15` · `EM13CO17` · `EM13CO19` · `EM13CO20` · `EM13CO21` · `EM13CO22` · `EM13CO23` · `EM13CO24` · `EM13CO25` · `EM13CO26`

### Competência específica 1

> Compreender as possibilidades e os limites da Computação para resolver problemas, tanto em termos de viabilidade quanto de eficiência, propondo e analisando soluções computacionais para diversos domínios do conhecimento, considerando diferentes aspectos.

| Código | Habilidade | Letramento digital |
|---|---|---|
| `EM13CO01` | Explorar e construir a solução de problemas por meio da reutilização de partes de soluções existentes. | — |
| `EM13CO02` | Explorar e construir a solução de problemas por meio de refinamentos, utilizando diversos níveis de abstração desde a especificação até a implementação. | — |
| `EM13CO03` | Identificar o comportamento dos algoritmos no que diz respeito ao consumo de recursos como tempo de execução, espaço de memória e energia, entre outros. | — |
| `EM13CO04` | Reconhecer o conceito de metaprogramação como uma forma de generalização na construção de programas, permitindo que algoritmos sejam entrada ou saída para outros algoritmos. | — |
| `EM13CO05` | Identificar os limites da Computação para diferenciar o que pode ou não ser automatizado, buscando uma compreensão mais ampla dos limites dos processos mentais envolvidos na resolução de problemas. | — |
| `EM13CO06` | Avaliar software levando em consideração diferentes características e métricas associadas. | — |

### Competência específica 2

> Analisar criticamente artefatos computacionais, sendo capaz de identificar as vulnerabilidades dos ambientes e das soluções computacionais buscando garantir a integridade, privacidade, sigilo e segurança das informações.

| Código | Habilidade | Letramento digital |
|---|---|---|
| `EM13CO07` | Compreender as diferentes tecnologias, bem como equipamentos, protocolos e serviços envolvidos no funcionamento de redes de computadores, identificando suas possibilidades de escala e confiabilidade. | — |
| `EM13CO08` | Entender como mudanças na tecnologia afetam a segurança, incluindo novas maneiras de preservar sua privacidade e dados pessoais on-line, reportando suspeitas e buscando ajuda em situações de risco. | **letramento digital** (proposta) |

### Competência específica 3

> Analisar situações do mundo contemporâneo, selecionando técnicas computacionais apropriadas para a solução de problemas.

| Código | Habilidade | Letramento digital |
|---|---|---|
| `EM13CO09` | Identificar tecnologias digitais, sua presença e formas de uso, nas diferentes atividades no mundo do trabalho. | **letramento digital** (proposta) |
| `EM13CO10` | Conhecer os fundamentos da Inteligência Artificial, comparando-a com a inteligência humana, analisando suas potencialidades, riscos e limites. | **letramento digital** (proposta) |
| `EM13CO11` | Criar e explorar modelos computacionais simples para simular e fazer previsões, identificando sua importância no desenvolvimento científico. | — |

### Competência específica 4

> Construir conhecimento usando técnicas e tecnologias computacionais, produzindo conteúdos e artefatos de forma criativa, com respeito às questões éticas e legais, que proporcionem experiências para si e os demais.

| Código | Habilidade | Letramento digital |
|---|---|---|
| `EM13CO12` | Produzir, analisar, gerir e compartilhar informações a partir de dados, utilizando princípios de ciência de dados. | — |
| `EM13CO13` | Analisar e utilizar as diferentes formas de representação e consulta a dados em formato digital para pesquisas científicas. | — |
| `EM13CO14` | Avaliar a confiabilidade das informações encontradas em meio digital, investigando seus modos de construção e considerando a autoria, a estrutura e o propósito da mensagem. | **letramento digital** (proposta) |
| `EM13CO15` | Analisar a interação entre usuários e artefatos computacionais, abordando aspectos da experiência do usuário e promovendo reflexão sobre a qualidade do uso dos artefatos nas esferas do trabalho, do lazer e do estudo. | **letramento digital** (proposta) |
| `EM13CO16` | Desenvolver projetos com robótica, utilizando artefatos físicos ou simuladores. | — |

### Competência específica 5

> Desenvolver projetos para investigar desafios do mundo contemporâneo, construir soluções e tomar decisões éticas, democráticas e socialmente responsáveis, articulando conceitos, procedimentos e linguagens próprias da Computação preferencialmente de maneira colaborativa.

| Código | Habilidade | Letramento digital |
|---|---|---|
| `EM13CO17` | Construir redes virtuais de interação e colaboração, favorecendo o desenvolvimento de projetos de forma segura, legal e ética. | **letramento digital** (proposta) |
| `EM13CO18` | Planejar e gerenciar projetos integrados às áreas de conhecimento de forma colaborativa, solucionando problemas, usando diversos artefatos computacionais. | — |

### Competência específica 6

> Expressar e partilhar informações, ideias, sentimentos e soluções computacionais utilizando diferentes plataformas, ferramentas, linguagens e tecnologias da Computação de forma fluente, criativa, crítica, significativa, reflexiva e ética.

| Código | Habilidade | Letramento digital |
|---|---|---|
| `EM13CO19` | Expor, argumentar e negociar propostas, produtos e serviços, utilizando diferentes mídias e ferramentas digitais. | **letramento digital** (proposta) |
| `EM13CO20` | Criar conteúdos, disponibilizando-os em ambientes virtuais para publicação e compartilhamento, avaliando a confiabilidade e as consequências da disseminação dessas informações. | **letramento digital** (proposta) |
| `EM13CO21` | Comunicar ideias complexas de forma clara por meio de objetos digitais como mapas conceituais, infográficos, hipertextos e outros. | **letramento digital** (proposta) |
| `EM13CO22` | Produzir e publicar conteúdo como textos, imagens, áudios, vídeos e suas associações, bem como ferramentas para sua integração, organização e apresentação, utilizando diferentes mídias digitais. | **letramento digital** (proposta) |

### Competência específica 7

> Agir pessoal e coletivamente com respeito, autonomia, responsabilidade, flexibilidade, resiliência e determinação, identificando e reconhecendo seus direitos e deveres, recorrendo aos conhecimentos da Computação e suas tecnologias frente às questões de diferentes naturezas.

| Código | Habilidade | Letramento digital |
|---|---|---|
| `EM13CO23` | Analisar criticamente as experiências em comunidades virtuais e as relações advindas da interação e comunicação com outras pessoas, bem como seus impactos na sociedade. | **letramento digital** (proposta) |
| `EM13CO24` | Identificar e reconhecer como as redes sociais e artefatos computacionais em geral interferem na saúde física e mental de seus usuários. | **letramento digital** (proposta) |
| `EM13CO25` | Dialogar em ambientes virtuais com segurança e respeito às diferenças culturais e pessoais, reconhecendo e denunciando atitudes abusivas. | **letramento digital** (proposta) |
| `EM13CO26` | Aplicar os conceitos e pressupostos do direito digital em sua conduta e experiências com o cotidiano da cultura digital, bem como na produção e uso de artefatos computacionais. | **letramento digital** (proposta) |

---

## Falsos amigos

Segurança **técnica** é Mundo Digital, não letramento: `EF07CO07` (segurança cibernética e formas de proteção), `EF09CO04` (malwares) e `EF09CO05` (criptografia). Segurança do ponto de vista do **uso e da privacidade** é Cultura Digital: `EF01CO07`, `EF02CO06`, `EF03CO09`, `EF08CO08`, `EF08CO10`. E `EF09CO06` (problemas sociais a partir de ambientes digitais) é Cultura Digital, embora fique ao lado das habilidades de segurança cibernética no anexo.

## Regra de manutenção

Este arquivo espelha o anexo oficial. Só muda se o documento mudar ou se o time pedagógico revisar a leitura do Ensino Médio — e a mudança é feita no JSON, seguida de `python scripts/gerar_bncc_referencia.py`. Descrição de habilidade é cópia literal; não parafraseie.
