"""Achados 🟡 e 🔴 explicados para quem dá o parecer: título simples, o que aconteceu, por que importa, o que fazer e
quem resolve — sem jargão de esteira.

Pedido do usuário em 25/10/2026: «explicar bem os erros amarelos e vermelhos [no Streamlit]. Eu percebo que hoje eles
têm limites de caracteres e aparecem cortados e são bem confusos na real, até o PO fica confuso. Então tem que ser mais
didático e uma linguagem não técnica.» Quem lê o cartão é o PO e o time pedagógico e de design: não sabe o que é
«gate», «envelope», «A094», «numero-sem-origem», «§17», «spec» nem «handoff».

O catálogo é determinístico (sem LLM na hora de mostrar: estável e grátis). A chave é o código do achado; o gate entra
quando o código é de família (código BNCC, critério numerado de um juiz, `perdido-<o quê>-<onde>`) ou quando o juiz
escreve o código que quiser — aí a explicação é a do verificador, e o texto do juiz é o caso. Código sem entrada cai
num texto genérico honesto, com o detalhe original à vista: `codigos_sem_explicacao` os lista, e o teste exige que
nenhum código do acervo (as 15 missões e as sessões brutas de 24/10/2026) caia nele.

Nada aqui corta texto: o trecho da missão e o texto original do verificador saem inteiros. Puro, sem Streamlit.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

# ------------------------------------------------------------------ quem resolve
PO = "po"
DESIGN = "design"
DEV = "dev"
ESTEIRA = "esteira"
#: A ordem dos grupos no cartão: o que só o PO decide vem primeiro.
ORDEM_QUEM = (PO, DESIGN, DEV, ESTEIRA)
ROTULO_QUEM = {PO: "PO (produto)", DESIGN: "Design", DEV: "Dev", ESTEIRA: "A esteira (refazer a etapa)"}
TITULO_GRUPO = {
    PO: "🧑 Para o PO decidir",
    DESIGN: "🎨 Para o design",
    DEV: "🛠️ Para o dev",
    ESTEIRA: "⚙️ Para a esteira refazer",
}
EXPLICA_GRUPO = {
    PO: "Só o PO decide estes pontos: a esteira não escolhe no lugar dele.",
    DESIGN: "O time de design ajusta estes pontos — em geral com **Refazer** no parecer de design.",
    DEV: "O time de dev ajusta estes pontos — em geral com **Refazer** no parecer de dev.",
    ESTEIRA: "Falhas da própria esteira, não da missão. Quem está com a etapa pede **Refazer**; se voltar a "
             "acontecer, avise o time técnico.",
}

# ------------------------------------------------------------------ severidade em palavras
BLOQUEIO = "bloqueio"
DECISAO_HUMANA = "decisao_humana"
ATENCAO = "atencao"
#: `(ícone, o que significa)` de cada severidade de achado.
SEVERIDADE = {
    BLOQUEIO: ("🔴", "Impede seguir até ser resolvido"),
    DECISAO_HUMANA: ("🧑", "Precisa da decisão de uma pessoa — a esteira não decide sozinha"),
    ATENCAO: ("🟡", "Pode seguir, mas alguém precisa conferir"),
}
_ORDEM_SEVERIDADE = {BLOQUEIO: 0, DECISAO_HUMANA: 1, ATENCAO: 2}

#: O semáforo de cada verificador, em palavras. ⛔ é a marca dos relatórios para o item de bloqueio (`tools/*.py`
#: escrevem «⛔ se bloqueio, ⚠️ se não») e da execução que parou num verificador — o mesmo peso do 🔴.
SEMAFORO_EM_PALAVRAS = {
    "🔴": "impede seguir até ser resolvido (ou até uma liberação com exceção, que fica registrada)",
    "🟡": "pode seguir, mas alguém precisa conferir",
    "🟢": "nada a conferir",
    "⚪": "não rodou nesta execução",
    "⛔": "a esteira parou aqui: é um impedimento, como o 🔴 — nada segue até alguém resolver",
}
LEGENDA = ("🔴 impede seguir até ser resolvido · 🟡 pode seguir, mas alguém precisa conferir · "
           "🧑 pede a decisão de uma pessoa · 🟢 nada a conferir")


# ------------------------------------------------------------------ a explicação
@dataclass(frozen=True)
class Explicacao:
    titulo: str
    o_que_aconteceu: str
    por_que_importa: str
    o_que_fazer: str
    #: `PO`, `DESIGN`, `DEV`, `ESTEIRA` — ou `None`: decide quem escreveu o trecho (`agente_responsavel`) ou a etapa.
    quem: Optional[str] = None
    #: o texto do verificador é o próprio caso (um juiz que escreve em prosa): sai à vista, não só nos detalhes
    texto_e_o_caso: bool = False
    #: sem entrada no catálogo — o texto genérico honesto
    generica: bool = False


def _x(titulo: str, aconteceu: str, importa: str, fazer: str, quem: Optional[str] = None,
       caso: bool = False) -> Explicacao:
    return Explicacao(titulo, aconteceu, importa, fazer, quem, caso)


# Frases que se repetem nas entradas
_REFAZER_PRODUTO = "Use **Refazer** no parecer de produto, citando o ponto, ou siga com ele registrado."
_DECIDA_NA_LISTA = ("Responda o item na lista «Contrato de produto em aberto» do cartão (aceitar, outro valor ou "
                    "recusar). O que você decidir entra no texto com o seu nome e a data.")
_PLATAFORMA = "A plataforma é o sistema onde a missão roda na escola: o que ela não faz, a missão não pode prometer."
_DEV_LE = "O PRD é o documento que o dev usa para programar a missão."

CATALOGO: Dict[str, Explicacao] = {
    # ---------------------------------------------------------- decisões do PO e o contrato de produto
    # ⚠️: a sessão tem pedido ou parecer do PO (`tools/decisoes.py`); o ⛔ sem registro está em `_SE_BLOQUEIO`
    "decisao-atribuida-ao-po": _x(
        "Decisão escrita como se fosse do PO",
        "O texto diz que o PO decidiu algo. A sessão tem pedidos ou pareceres do PO, mas a esteira não sabe se algum "
        "deles diz isso.",
        "Se o PO não decidiu, a missão segue com uma escolha do agente disfarçada de decisão do PO, e ninguém volta "
        "para conferir.",
        "Leia cada frase abaixo. Se a decisão é sua, confirme no comentário do de acordo. Se não é, use **Refazer** "
        "pedindo que ela vire proposta para você validar.", PO),
    "propostas-a-revisar": _x(
        "Sugestões do agente esperando o PO",
        "O agente deixou propostas marcadas para o PO validar. Elas não travam a etapa, mas ainda não são decisão.",
        "Proposta não validada pode chegar ao design e ao dev como se fosse regra da missão.",
        _DECIDA_NA_LISTA, PO),
    "proposta": _x(
        "Proposta do agente ainda sem resposta do PO",
        "Há uma sugestão do agente no texto, marcada para o PO validar.",
        "Enquanto o PO não responde, ela é só sugestão — e o design e o dev não sabem se podem seguir com ela.",
        _DECIDA_NA_LISTA, PO),
    "parametro": _x(
        "Número que o PO ainda precisa definir",
        "O texto deixou um número (tempo, quantidade, limite) para o PO definir.",
        "Sem o número, quem desenha e quem programa escolhe um por conta própria.",
        _DECIDA_NA_LISTA, PO),
    "parametro-decidido": _x(
        "Número em aberto que apareceu como decidido",
        "O one-pager aprovado deixou um número para o PO definir, e a especificação o escreveu como se já estivesse "
        "decidido.",
        "O design e o dev vão tratar como decisão do PO um número que ninguém decidiu.",
        "Confira o número abaixo. Se ele vale, responda na lista do contrato; se não, use **Refazer** de produto "
        "pedindo que o número volte a ficar em aberto.", PO),
    "aberto": _x(
        "Pendência aberta no texto",
        "O texto tem um ponto marcado como «em aberto», com um dono para decidir.",
        "Ponto aberto que ninguém decide segue até o dev como dúvida, e alguém vai decidir sem saber.",
        "Veja quem é o dono do ponto (no trecho abaixo). Se é o PO, responda na lista do contrato ou registre no de "
        "acordo; se é outra equipe, avise quem cuida.", PO),
    "humano": _x(
        "Ponto que uma pessoa precisa decidir",
        "O texto marcou uma decisão que nenhum agente pode tomar — é de uma pessoa (PO, editorial, pedagogia).",
        "Sem essa decisão a missão segue com uma dúvida que vai aparecer no dev ou em sala.",
        "Leia o trecho e decida, ou passe para quem é o dono. Registre a decisão no comentário do de acordo.", PO),
    "produto": _x(
        "Pendência de produto aberta",
        "O texto marcou uma decisão de produto que ainda está em aberto.",
        "Decisão de produto em aberto chega ao design e ao dev como lacuna.",
        "Leia o trecho e decida. Se a decisão muda o texto, use **Refazer** de produto com ela.", PO),
    "editorial": _x(
        "Pendência para o editorial",
        "O texto marcou um ponto para a equipe editorial confirmar (por exemplo, um código da BNCC na grade).",
        "Sem a confirmação, a missão pode citar algo que a rede de ensino não reconhece.",
        "Encaminhe ao editorial e registre a resposta no comentário do de acordo.", PO),
    "externo": _x(
        "Ponto a confirmar fora da esteira",
        "O texto cita algo que depende de confirmação externa (outra disciplina, a rede de ensino, um documento oficial).",
        "Se a confirmação não vier, a missão promete algo que pode não valer na escola.",
        "Confirme com quem responde pelo assunto e registre no de acordo. Não trava a etapa.", PO),
    "a_validar": _x(
        "Afirmação plausível, ainda a confirmar",
        "O texto marcou uma afirmação como plausível, mas ainda sem confirmação formal.",
        "Se estiver errada, a missão ensina ou cita algo incorreto.",
        "Confirme a afirmação com a fonte e registre no de acordo. Não trava a etapa.", PO),
    "conflito-pedido-regra": _x(
        "Seu pedido esbarra numa regra da esteira",
        "Um pedido do PO contraria uma regra fixa da esteira. O agente não escolhe entre os dois: devolve a decisão "
        "ao PO.",
        "Se ninguém decidir, a missão sai ou sem o pedido ou contra a regra — e não se sabe qual.",
        "Leia o pedido e a regra no trecho. Decida: manter o pedido (registre por quê no de acordo) ou ajustá-lo "
        "com **Refazer**.", PO),
    "slug-colidido": _x(
        "O código da missão já é de outra missão",
        "O código curto da missão (ex.: exp01ef1b) já foi usado por outra missão gerada.",
        "Duas missões com o mesmo código se sobrescrevem na plataforma.",
        "Decida se esta missão substitui a anterior ou ganha outro código, e registre no de acordo.", PO),
    "missao-parecida": _x(
        "Missão muito parecida com outra já gerada",
        "A esteira comparou esta missão com as anteriores e achou uma muito parecida.",
        "Duas missões quase iguais gastam aula da criança com a mesma descoberta.",
        "Compare as duas e decida se esta segue como está ou muda o foco.", PO),
    "indice-defasado": _x(
        "Lista de missões para comparação desatualizada",
        "A lista que a esteira usa para comparar esta missão com as anteriores não tem as missões mais novas.",
        "A comparação pode deixar passar uma missão repetida.",
        "Não depende de você: avise o time técnico para atualizar a lista. Não trava a etapa.", ESTEIRA),
    "existente-sem-decisao": _x(
        "Esta missão já existe na plataforma, e falta a decisão do PO",
        "Já há uma missão publicada com este código, e o texto não registra se esta a substitui ou ganha outro código.",
        "Sem essa decisão, o dev não sabe se atualiza a missão que está no ar ou cria uma nova.",
        # sempre 🔴 (`tools/conferir_prd_plataforma.py`), no dev: o de acordo não aparece, e a decisão vale com a data
        # de um pedido do PO nesta sessão
        "Decida: substituir a existente ou dar outro código, e escreva a decisão no pedido de **Refazer** de dev: o PRD "
        "a registra com a data do seu pedido.", PO),
    "experiencia-ja-existe": _x(
        "Esta missão já existe na plataforma",
        "Já há uma missão publicada com este código; o documento para o dev a trata como nova.",
        "O dev pode criar uma segunda versão em vez de atualizar a que está no ar.",
        "Decida se esta missão atualiza a existente ou ganha outro código, e escreva a decisão no pedido de "
        "**Refazer** de dev.", PO),
    # ---------------------------------------------------------- pedido do PO aplicado ou não
    "nao-tratado": _x(
        "Pedido do PO sem sinal de que foi feito",
        "A esteira procurou no documento o que o PO pediu e não achou nada que mostre que o pedido foi aplicado.",
        "Pode ser que o pedido tenha ficado de fora — e o PO acha que a missão já está como ele pediu.",
        "Confira no documento se o pedido abaixo está lá. Se não está, use **Refazer** repetindo o pedido.", None),
    "nao-julgado": _x(
        "Pedido do PO que ninguém conferiu",
        "O revisor automático não deu parecer sobre este pedido do PO.",
        "Sem conferência, não dá para saber se o pedido entrou no documento.",
        "Confira no documento se o pedido abaixo está lá. Se não está, use **Refazer** repetindo o pedido.", None),
    "citou-o-pedido": _x(
        "O revisor «confirmou» copiando o próprio pedido",
        "Para dizer que o pedido foi aplicado, o revisor automático citou o texto do pedido, e não um trecho do "
        "documento.",
        "Não há prova de que o documento mudou.",
        "Confira no documento se o pedido abaixo está lá. Se não está, use **Refazer** repetindo o pedido.", None),
    "sem-prova": _x(
        "A prova de que o pedido foi feito não está no documento",
        "O revisor disse que o pedido foi atendido e citou um trecho, mas esse trecho não existe no documento.",
        "O pedido pode não ter sido aplicado.",
        "Confira no documento se o pedido abaixo está lá. Se não está, use **Refazer** repetindo o pedido.", None),
    "pedido-violado": _x(
        "O documento contraria o pedido do PO",
        "O revisor encontrou no documento o contrário do que o PO pediu.",
        "A missão segue fazendo o que o PO mandou não fazer.",
        "Leia o pedido e o trecho. Use **Refazer** repetindo o pedido, de preferência citando a frase que precisa "
        "mudar.", None),
    "preservacao-sem-prova": _x(
        "Pedido de «não mexer» sem como conferir",
        "O PO pediu para manter algo como estava, e nenhum verificador consegue provar que ficou igual.",
        "Se o trecho mudou, ninguém vai perceber.",
        "Confira você mesmo se o que pediu para manter continua igual no documento.", None),
    "preservacao-sem-citacao": _x(
        "Pedido de «não mexer» sem trecho para conferir",
        "O PO pediu para manter algo como estava, sem citar o trecho exato; a conferência fica com os outros "
        "verificadores.",
        "Se o trecho mudou, a esteira pode não perceber.",
        "Confira você mesmo se o que pediu para manter continua igual no documento.", None),
    "remocao-a-conferir": _x(
        "Pedido para tirar um trecho que ainda aparece",
        "O PO pediu para tirar um texto, e ele ainda aparece no documento — talvez em outro lugar.",
        "O texto que o PO mandou tirar pode continuar na missão.",
        "Confira onde o texto ainda aparece. Se deveria ter saído, use **Refazer** citando o lugar.", None),
    "exigencia-dispensada": _x(
        "Frase do pedido tratada como comentário",
        "O revisor tratou uma frase do pedido do PO como contexto, mas ela pede uma mudança.",
        "Essa parte do pedido pode ter ficado de fora.",
        "Confira se o que a frase pede está no documento. Se não está, use **Refazer** repetindo a frase.", None),
    "linha-trocada-a-pedido": _x(
        "Linha trocada a pedido do PO",
        "Uma linha do documento foi trocada para atender a um pedido do PO.",
        "É só um registro da troca, para conferência.",
        "Confira se a troca ficou como você pediu.", None),
    "alteracao-sem-pedido": _x(
        "Mudança que ninguém pediu",
        "O documento mudou num ponto que nenhum pedido citava.",
        "Uma correção pontual não deve mexer no que já estava aprovado.",
        "Confira a mudança. Se não devia ter acontecido, use **Refazer** pedindo para voltar ao texto anterior.", None),
    "trecho-do-po-perdido": _x(
        "Trecho escrito pelo PO sumiu",
        "Um trecho que o PO escreveu não está mais no documento.",
        "O que o PO aprovou não pode sumir sem ele pedir.",
        "Use **Refazer** pedindo que o trecho volte, citando-o.", None),
    # ---------------------------------------------------------- textos que o PO aprovou
    "texto-chave-acima-do-teto": _x(
        "Frase que a criança lê está longa demais",
        "Alguns textos que a criança lê passam do limite de palavras por frase da série.",
        "Frase longa demais cansa ou trava a leitura de quem ainda lê devagar.",
        "Para cada texto, decida na lista do contrato: manter assim ou trocar por uma versão mais curta.", PO),
    "texto-chave-divergente": _x(
        "Texto aprovado pelo PO chegou mudado às telas",
        "Textos que o PO aprovou palavra por palavra aparecem com outra redação nos textos das telas.",
        "A criança vai ler uma versão que o PO não aprovou.",
        "Peça ao design que use o texto aprovado (o original está no trecho). Se o design quer outra redação, ela vira "
        "proposta para o PO.", DESIGN),
    "texto-chave-sem-linha": _x(
        "Texto aprovado sem lugar nas telas",
        "Alguns textos aprovados pelo PO não têm a linha deles na tabela de textos das telas.",
        "Quem programa pode não saber em que tela o texto aparece.",
        "Peça ao design que inclua cada texto na tabela de textos das telas, com o código dele.", DESIGN),
    "texto-chave-reescrito": _x(
        "Texto aprovado pelo PO reescrito",
        "Textos que o PO aprovou palavra por palavra aparecem com outra redação neste documento.",
        "O documento passa uma versão que o PO não aprovou — e é ela que vai para a sala ou para o dev.",
        "Peça, com **Refazer** desta etapa, que o documento copie o texto aprovado (o original está no trecho).", None),
    "literal-parafraseado": _x(
        "Texto aprovado pelo PO reescrito no PRD",
        "Um texto que o PO aprovou palavra por palavra aparece no PRD com outra redação. " + _DEV_LE,
        "O dev vai programar a versão errada do texto.",
        "Peça, com **Refazer** de dev, que o PRD copie o texto aprovado.", DEV),
    "opcoes-divergentes": _x(
        "As opções de uma escolha mudaram",
        "Uma escolha que o PO aprovou tem opções a menos, a mais ou com outro nome nos textos das telas.",
        "O número e o texto das opções são decisão do PO: mudar isso muda o que a criança decide.",
        "Peça ao design que restaure as opções aprovadas. Se o design quer outra escolha, ela vira proposta para o PO.",
        DESIGN),
    "texto-de-tela-reescrito": _x(
        "Textos de tela aprovados não chegaram iguais às telas",
        "Textos que o one-pager aprovado põe na tela, entre aspas, não estão nos textos das telas (nem parecidos).",
        "A criança pode ler uma frase diferente da aprovada, ou nenhuma.",
        "Confira cada texto abaixo. Peça ao design que use a redação aprovada ou proponha outra ao PO.", DESIGN),
    "canal-b-reescrito": _x(
        "Perguntas do fim da missão reescritas",
        "As perguntas de múltipla escolha do fim (e as alternativas) aprovadas pelo PO não estão iguais neste "
        "documento.",
        "Essas perguntas medem a aprendizagem: mudar a redação muda o que é medido.",
        "Peça, com **Refazer** desta etapa, que o documento copie as perguntas aprovadas.", None),
    "roteiro-reescrito": _x(
        "Perguntas do debate reescritas",
        "As perguntas que o professor faz no debate, aprovadas pelo PO, não estão iguais neste documento.",
        "O professor vai conduzir a conversa com perguntas que o PO não aprovou.",
        "Peça, com **Refazer** desta etapa, que o documento copie as perguntas aprovadas.", None),
    "podcast-ausente": _x(
        "O podcast do professor sumiu",
        "O one-pager aprovado tem um podcast de recapitulação, e este documento não o menciona.",
        "Sem ele, o design e o dev esquecem ou reinventam o áudio.",
        "Peça, com **Refazer** desta etapa, que o documento traga o podcast como foi aprovado.", None),
    "podcast-reescrito": _x(
        "Falas do podcast reescritas",
        "As falas do podcast aprovado não estão iguais neste documento.",
        "O áudio gravado seria diferente do que o PO aprovou.",
        "Peça, com **Refazer** desta etapa, que o documento copie o roteiro aprovado.", None),
    "podcast-sem-requisito": _x(
        "O PRD não pede o podcast",
        "O one-pager aprovado tem podcast, e nenhum requisito do PRD o cita. " + _DEV_LE,
        "O dev não vai programar o áudio.",
        "Peça, com **Refazer** de dev, um requisito para o podcast (quem toca, em que tela, quando).", DEV),
    # ---------------------------------------------------------- BNCC, avaliação e evidência
    "codigo-fora-do-eixo": _x(
        "Habilidade da BNCC citada sem a etapa que a exercita",
        "O texto cita uma habilidade da BNCC, mas não diz em que momento da missão a criança a pratica.",
        "Habilidade citada e não praticada é promessa vazia para a escola.",
        "Peça, com **Refazer** de produto, a etapa que exercita a habilidade — ou que ela saia da lista.", PO),
    "saeb-ausente": _x(
        "Falta o descritor do SAEB",
        "A série é avaliada pelo SAEB, e o texto não diz qual descritor da prova a missão exercita.",
        "A escola usa essa ligação para planejar; sem ela, a missão perde valor para o professor.",
        "Indique o descritor (ou por que nenhum se aplica) com **Refazer** de produto.", PO),
    "saeb-fora-do-ano": _x(
        "Descritor do SAEB numa série que o SAEB não avalia",
        "O texto cita descritores do SAEB, mas o SAEB não avalia esta série.",
        "É uma informação errada para a escola.",
        "Peça, com **Refazer** de produto, que a linha diga «não se aplica — série não avaliada pelo SAEB».", PO),
    "12a-ausente": _x(
        "Falta dizer como a missão mede cada habilidade",
        "O one-pager não tem a parte que diz, para cada habilidade, de qual ação da criança sai o nível dela.",
        "Sem isso, ninguém sabe dizer se a criança aprendeu.",
        _REFAZER_PRODUTO, PO),
    "habilidade-sem-canal-a": _x(
        "Habilidade medida só por pergunta do fim",
        "Uma habilidade é medida só pela pergunta de múltipla escolha do fim, sem nenhuma ação da criança na tela.",
        "A missão existe para a criança fazer; uma pergunta no fim não mostra se ela soube fazer.",
        "Peça, com **Refazer** de produto, a ação em tela que exercita a habilidade — ou tire a habilidade.", PO),
    "habilidade-sem-matriz": _x(
        "Habilidade sem a regra que mede o nível",
        "Uma habilidade da lista não tem a linha que diz como o nível da criança é calculado.",
        "Sem a regra, o relatório do professor não consegue mostrar essa habilidade.",
        _REFAZER_PRODUTO, PO),
    "habilidade-sem-kpi": _x(
        "Nenhum indicador mede quantos alunos aprenderam",
        "Nenhum indicador do PRD conta quantos estudantes chegam a «Atingiu» nas habilidades. " + _DEV_LE,
        "É o número que a missão existe para mover.",
        "Peça, com **Refazer** de dev, o indicador de cada habilidade.", DEV),
    "gabarito-nao-declarado": _x(
        "Falta dizer que a resposta certa fica no servidor",
        "O texto não declara que o gabarito das escolhas fica guardado no servidor, longe do celular da criança.",
        "Gabarito no aparelho é gabarito entregue à criança.",
        _REFAZER_PRODUTO, PO),
    "gabarito-no-cliente": _x(
        "A resposta certa iria para o celular da criança",
        "O documento coloca o gabarito no aplicativo que roda no aparelho.",
        "Qualquer criança curiosa acharia a resposta certa.",
        "Peça, com **Refazer** desta etapa, que o gabarito fique no servidor.", None),
    "tabela-medidas-ausente": _x(
        "Falta a tabela do que é medido",
        "A especificação não traz a tabela que lista cada medida e os sinais que a compõem.",
        "Sem ela, um nível pode ser calculado com sinais de menos — e um adulto decide sobre a criança com um número "
        "inflado.",
        _REFAZER_PRODUTO, PO),
    "conta-ausente": _x(
        "Falta a conta da virada",
        "O núcleo da missão não mostra a conta (por exemplo, o ranking antes e depois) que faz a criança perceber a "
        "virada.",
        "Sem a conta, a descoberta central fica no ar.",
        _REFAZER_PRODUTO, PO),
    "trecho-inexistente": _x(
        "Citação que não está no material",
        "O mapa de conceitos citou um trecho que não existe no material anexado.",
        "O conceito pode ter sido inventado ou reescrito pelo agente.",
        "Confira o conceito no material antes de aceitar. Se estiver errado, use **Refazer** de produto.", PO),
    "eixo-no-em": _x(
        "Habilidade do Ensino Médio sem eixo oficial",
        "No Ensino Médio a BNCC não separa as habilidades de computação por eixo; a esteira usa uma leitura proposta.",
        "A classificação pode não ser a que a pedagogia adota.",
        "Valide com a pedagogia e registre no de acordo. Não trava a etapa.", PO),
    # `letramento` é o achado do recorte de letramento digital que falta (`tools/bncc.py`): no EM é 🟡 (a lista do EM é
    # proposta, a pedagogia decide); no EF é 🔴 — a variante está em `_SE_BLOQUEIO`. Até a revisão do PR #82 o texto
    # daqui era o da família EM13 «proposta» e terminava em «Não trava a etapa» também no 🔴 do EF.
    "letramento": _x(
        "Nenhuma habilidade da lista proposta de letramento digital do Ensino Médio",
        "Nenhuma das habilidades da BNCC declaradas está na lista proposta de letramento digital do Ensino Médio. No "
        "Médio a BNCC não separa as habilidades por eixo, então a lista é uma leitura proposta, não oficial.",
        "Letramento digital é o recorte da BNCC que a missão precisa cobrir; no Médio, quem decide se ela cobre é a "
        "avaliação pedagógica.",
        "Valide com a pedagogia e registre no de acordo. Não trava a etapa.", PO),
    "decisao-produto": _x(
        "Decisão de produto pendente sobre a BNCC",
        "Nenhuma habilidade de Cultura Digital da série descreve a ação da missão. É decisão do time: mudar a série "
        "ou a âncora curricular.",
        "Sem a decisão, a missão não tem habilidade da BNCC que a sustente.",
        "Decida a série ou a âncora curricular e use **Refazer** de produto com a decisão.", PO),
    # ---------------------------------------------------------- números e metas
    "numero-sem-origem": _x(
        "Número sem fonte",
        "O texto apresenta números (tempos, quantidades, limites) como decididos, sem que venham do one-pager, do "
        "briefing ou de uma decisão do PO.",
        "Número que ninguém decidiu vira regra da missão sem que o PO perceba.",
        "Confira cada número abaixo. Se ele vale, confirme na lista do contrato ou no de acordo; se não, use "
        "**Refazer** pedindo que ele vire «a definir por produto».", None),
    "kpi-alvo-inventado": _x(
        "Meta de indicador que ninguém decidiu",
        "Um indicador tem uma meta que não está no one-pager nem nas perguntas de produto.",
        "Meta é decisão do PO; inventada, ela orienta o produto para o lado errado.",
        "Decida a meta (ou «sem meta — primeira medição») e registre com **Refazer** de dev.", PO),
    "meta-diverge-9f": _x(
        "Meta de indicador diferente da aprovada",
        "Indicadores do PRD têm metas diferentes das que estão nas perguntas de produto aprovadas.",
        "Duas metas para a mesma pergunta: o time não sabe qual vale.",
        "Confirme qual número vale. Se é o aprovado, peça **Refazer** de dev; se é outro, decida como PO.", PO),
    "hipotese-diverge": _x(
        "A meta da hipótese mudou no caminho",
        "A hipótese do one-pager aparece neste documento com outro número (ou com um número que ela não tinha).",
        "Meta de hipótese é decisão do PO.",
        "Confirme o número certo. Se for o do one-pager, peça **Refazer** desta etapa para copiá-lo.", PO),
    "hipotese-a-conferir": _x(
        "Número da hipótese a conferir",
        "A hipótese do one-pager tem um número, e este documento usa outro que pode ser de outra coisa (o limiar de "
        "uma pergunta). É dúvida, não erro certo.",
        "Se forem a mesma coisa, há dois números para a mesma meta.",
        "Confira os dois números e registre no de acordo qual vale. Não trava a etapa.", PO),
    "teto-ausente": _x(
        "O limite de tempo aprovado não chegou ao PRD",
        "O one-pager aprovado define um teto (por exemplo, minutos seguidos de tela) e o PRD não o traz. " + _DEV_LE,
        "O dev pode programar telas mais longas do que a série aguenta.",
        "Peça, com **Refazer** de dev, que o PRD leve o teto às telas que ele limita.", DEV),
    "origem-de-produto-falsa": _x(
        "Decisão do design apresentada como do PO",
        "O PRD cita como decisão de produto algo que foi decidido no design.",
        "O dev acha que o PO decidiu, e ninguém mais confere.",
        "Peça, com **Refazer** de dev, que a citação aponte a origem certa.", DEV),
    "proposta-perdida": _x(
        "Proposta chegou ao PRD como se estivesse decidida",
        "Propostas do agente que o PO não validou aparecem no PRD sem a marca de proposta.",
        "O dev lê como decidido o que o PO não aprovou.",
        "Valide as propostas na lista do contrato, ou peça **Refazer** de dev para manter a marca.", PO),
    # ---------------------------------------------------------- limites da plataforma
    "websocket": _x(
        "Sincronização da turma que a plataforma não tem",
        "O texto propõe uma conexão em tempo real (WebSocket) para sincronizar a sala. " + _PLATAFORMA,
        "A plataforma sincroniza a turma por consultas curtas e repetidas; a missão não funcionaria como escrita.",
        _REFAZER_PRODUTO, PO),
    "websocket-mencao": _x(
        "Segunda forma de sincronizar a turma",
        "O texto menciona uma conexão em tempo real além da forma de sincronizar que a plataforma usa.",
        "Duas formas de sincronizar é uma a mais; pode ser só comparação, mas vale conferir.",
        "Confira se a menção é só comparação. Não trava a etapa.", None),
    "agendamento": _x(
        "Agendamento que a plataforma não tem",
        "O texto propõe agendar a missão. " + _PLATAFORMA + " Lá, o professor põe a atividade no ar e ela abre na hora.",
        "A missão prometeria algo que a escola não vai encontrar.",
        "Peça que o texto diga «pôr no ar», ou registre o agendamento como pendência de plataforma.", PO),
    "agendamento-inexistente": _x(
        "Agendamento que a plataforma não tem",
        "O documento conta com agendamento da missão. " + _PLATAFORMA,
        "O dev não tem como programar o que a plataforma não oferece.",
        "Peça, com **Refazer**, que o texto diga «pôr no ar» — ou registre o agendamento como pendência de plataforma.",
        None),
    "estado-cliente": _x(
        "Progresso guardado no celular",
        "O texto diz que o progresso da criança fica guardado no aparelho.",
        "Na plataforma o progresso fica no servidor: se a criança troca de aparelho, nada se perde.",
        "Peça que o texto diga o que se preserva, sem dizer onde. Não trava a etapa.", PO),
    "capacidade-inexistente": _x(
        "O PRD pede algo que a plataforma não faz",
        "O PRD exige um recurso (por exemplo, funcionar sem internet) que a plataforma não tem. " + _PLATAFORMA,
        "O dev não tem como entregar; a missão promete o impossível.",
        "Decida se o recurso sai da missão ou vira pendência de plataforma, e peça **Refazer** de dev.", DEV),
    "zerar-arquiva": _x(
        "«Zerar» que apaga em vez de abrir rodada nova",
        "O documento diz que zerar a missão arquiva as respostas. Na plataforma, zerar abre uma rodada nova sem "
        "apagar nada.",
        "O professor perderia o histórico da turma.",
        "Peça, com **Refazer**, que zerar abra uma rodada nova.", DEV),
    "evidencia-tabela-propria": _x(
        "Tabela própria para notas da missão",
        "O documento cria uma tabela só desta missão para guardar respostas ou notas.",
        "A plataforma já tem um lugar único para a evidência de aprendizagem; tabela própria não aparece no relatório "
        "do professor.",
        "Peça, com **Refazer**, que a evidência use o módulo da plataforma.", DEV),
    "ponte-legada": _x(
        "Visual de um app de terceiros que não se usa mais",
        "O documento usa a versão antiga do visual do app simulado (copiando a identidade de um app real).",
        "Missão nova usa o visual próprio da Unooria; a versão antiga só com decisão registrada do PO.",
        "Peça, com **Refazer**, a seção atual do design system — ou registre a decisão do PO.", DEV),
    "ds-versao-cravada": _x(
        "Versão fixa do design system",
        "O documento fixa um número de versão do design system.",
        "A plataforma segue sempre a última versão; um número fixo desatualiza.",
        "Peça que o número saia. Não trava a etapa.", DEV),
    "modelo-ia-divergente": _x(
        "Modelo de IA diferente do da plataforma",
        "O PRD nomeia um modelo de IA que não é o que a plataforma usa.",
        "Custo e limites de uso saem do modelo da plataforma; outro nome confunde quem programa.",
        "Peça, com **Refazer** de dev, que o PRD use a família de modelo da plataforma. Não trava a etapa.", DEV),
    "secao_ds": _x(
        "Seção nova do design system",
        "A missão pede uma seção do design system que ainda não existe.",
        "Alguém da plataforma precisa criá-la, com prazo; sem isso o dev fica parado.",
        "Combine com o time de plataforma quem cria a seção e quando. Não trava a etapa.", DEV),
    # ---------------------------------------------------------- design: nomes, textos e telas
    "rotulo-divergente": _x(
        "Mesmo botão com nomes diferentes",
        "Um botão (ou outro rótulo) aparece com um nome diferente do nome oficial definido no glossário da missão.",
        "A criança e o professor podem ver dois nomes para a mesma coisa; o dev não sabe qual programar.",
        "Peça que o documento use o nome oficial (está no trecho). Em geral é ajuste simples.", None),
    "glossario-ausente": _x(
        "Falta a lista oficial de nomes",
        "A especificação não traz o glossário com os nomes oficiais (personagens, botões, números).",
        "Sem ele, cada documento batiza as coisas de um jeito.",
        _REFAZER_PRODUTO, PO),
    "coluna-inexistente": _x(
        "Documento cita um dado que o modelo de dados não tem",
        "O documento cita um campo de dados que não está declarado no próprio modelo de dados.",
        "Quem programa vai procurar um campo que não existe.",
        "Peça, com **Refazer**, que o campo seja declarado ou saia do texto. Não trava a etapa.", None),
    "alterou-fora-do-proprio-bloco": _x(
        "O design tentou mudar uma parte que é de produto",
        "Um agente de design quis mudar um trecho que pertence a produto. A mudança foi descartada; o texto de produto "
        "ficou como estava.",
        "O que é decisão de produto só muda pelo PO. Se a mudança era boa, ela ainda não entrou.",
        "Se a mudança deveria entrar, use **Refazer** com ela: a triagem a leva a produto. Se não, nada a fazer.",
        DESIGN),
    "decisao-de-produto-pelo-agente": _x(
        "O design tentou decidir algo de produto",
        "Um agente de design escreveu numa parte de produto. A mudança não entrou.",
        "Só o PO decide produto.",
        "Se a mudança deveria entrar, use **Refazer** com ela: a triagem a leva a produto.", DESIGN),
    "linhas-perdidas": _x(
        "Linhas do documento sumiram ao ser reescrito",
        "Ao consolidar o documento, o agente apagou linhas que outro autor tinha escrito.",
        "O que foi escrito e aprovado antes não pode sumir sem pedido.",
        "Peça, com **Refazer**, que as linhas abaixo voltem no mesmo lugar.", None),
    "autor-instavel": _x(
        "Linhas mudaram desde a execução anterior",
        "O documento perdeu linhas que tinha na execução anterior.",
        "Pode ser o efeito esperado do pedido de refazer — ou uma perda sem querer.",
        "Confira se o motivo do refazer explica as linhas abaixo. Se não, peça que voltem.", None),
    "arquivo-inexistente": _x(
        "O relatório de QA cita um arquivo que não existe",
        "O relatório de QA do design cita um arquivo que a esteira não grava.",
        "O QA pode ter conferido algo que não existe — a conferência dele fica em dúvida.",
        "Peça **Refazer** de design para o QA conferir os arquivos reais.", DESIGN),
    "afirmacao-stitch": _x(
        "O QA contou mais telas no Stitch do que existem",
        "O relatório de QA afirma um número de telas no Stitch maior do que o projeto tem.",
        "Telas podem estar faltando, e o QA disse que estava tudo lá.",
        "Abra o Stitch e confira. Peça **Refazer** de design para gerar as que faltam.", DESIGN),
    "afirmacao-prototipo": _x(
        "O QA contou mais telas no protótipo do que existem",
        "O relatório de QA afirma um número de telas no protótipo maior do que o arquivo tem.",
        "Telas podem estar faltando, e o QA disse que estava tudo lá.",
        "Abra o protótipo e confira. Peça **Refazer** de design para completar.", DESIGN),
    "estados-fora-do-prototipo": _x(
        "Telas sem todos os estados desenhados",
        "Algumas telas têm menos versões no protótipo do que os estados que elas têm (por exemplo, vazio, carregando, "
        "erro).",
        "O dev vai inventar a aparência dos estados que faltam.",
        "Peça ao design os quadros que faltam (estão listados abaixo).", DESIGN),
    "prototipo-sem-quadros-marcados": _x(
        "Protótipo sem a marca de cada tela",
        "As telas do protótipo não estão marcadas com o código de cada uma.",
        "Sem a marca, não dá para conferir se cada tela do inventário foi desenhada.",
        "Peça **Refazer** de design com as telas marcadas.", DESIGN),
    "preparo-do-professor-ausente": _x(
        "Faltam as telas do professor",
        "O inventário não tem todas as cinco telas de preparo do professor (escolher a missão, recorte da aula, "
        "geração, curadoria, pôr no ar).",
        "Sem elas, o professor não consegue preparar a aula.",
        "Peça ao design as telas que faltam.", DESIGN),
    "componente-inexistente": _x(
        "Componente que o design system não tem",
        "O protótipo usa um componente que não existe no design system.",
        "O dev teria de criar um componente fora do padrão — ou trocá-lo sem o design saber.",
        "Peça ao design um componente do design system (há sugestão no detalhe).", DESIGN),
    "guarda-afrouxada": _x(
        "Caminho entre telas mais solto do que a regra",
        "Uma passagem entre telas deixa a criança avançar em mais situações do que a especificação permite.",
        "A criança pode pular uma etapa que a missão precisa.",
        "Decida: aceitar a passagem do design ou manter a regra da especificação. Registre no de acordo.", PO),
    "guarda-exige-acerto": _x(
        "Passagem que só aceita a resposta certa",
        "Uma passagem entre telas só deixa a criança seguir se acertar, e a especificação não pede acerto ali.",
        "A missão deixa de medir quem erra — e o erro é parte da descoberta.",
        "Decida: aceitar a trava do design ou deixar a criança seguir mesmo errando. Registre no de acordo.", PO),
    "miro-indisponivel": _x(
        "Os diagramas não foram para o Miro",
        "A esteira não conseguiu criar ou atualizar o quadro do Miro com os diagramas da missão.",
        "Quem consulta o Miro vê uma versão antiga, ou nenhuma. Os diagramas continuam no arquivo da missão.",
        "Não trava a etapa. Avise o time técnico se o Miro precisar estar em dia.", ESTEIRA),
    "miro-board-incompleto": _x(
        "Quadro do Miro incompleto",
        "O quadro do Miro saiu com diagramas faltando.",
        "Quem consulta o Miro não vê a missão inteira.",
        "Não trava a etapa. Avise o time técnico se o Miro precisar estar completo.", ESTEIRA),
    "conteudo-raso": _x(
        "Texto do banco de conteúdo curto demais",
        "Um texto que a criança vai ler (notícia, post, documento) tem só uma descrição, não o texto de verdade.",
        "Na tela a criança veria uma descrição em vez do conteúdo.",
        "Peça, com **Refazer** de dev, o texto completo.", DEV),
    # ---------------------------------------------------------- dev: o PRD
    "estado-da-spec-sem-mapa": _x(
        "Estados da missão que não chegaram ao PRD",
        "Alguns estados da missão (os momentos em que ela pode estar) não aparecem no PRD. " + _DEV_LE,
        "O dev programa uma missão com momentos a menos.",
        "Peça, com **Refazer** de dev, que o PRD traga todos os estados, com os mesmos nomes.", DEV),
    "estado-do-contrato-ausente": _x(
        "Estados da missão que não chegaram ao PRD",
        "Estados da missão definidos na especificação não estão no PRD. " + _DEV_LE,
        "O dev programa uma missão com momentos a menos.",
        "Peça, com **Refazer** de dev, que o PRD traga todos os estados, com os mesmos nomes.", DEV),
    "estado-fora-do-contrato": _x(
        "O PRD inventou estados",
        "O PRD tem estados da missão que não existem na especificação nem no fluxo do design.",
        "O PRD deve copiar, não criar: estado novo é decisão que ninguém tomou.",
        "Peça, com **Refazer** de dev, que o PRD use os nomes da especificação.", DEV),
    "evento-perdido": _x(
        "Ações da criança que o PRD não registra",
        "Ações que a especificação manda registrar não estão no PRD, ou estão com outro nome.",
        "Sem o registro, os indicadores e o relatório do professor ficam sem dado.",
        "Peça, com **Refazer** de dev, os registros que faltam.", DEV),
    "ausencia-perdida": _x(
        "O que o app simulado não tem sumiu do PRD",
        "A especificação diz o que o app simulado não oferece (por exemplo, sem botão de editar), e o PRD não repete.",
        "O dev pode programar o que a missão escolheu não ter.",
        "Peça, com **Refazer** de dev, que o PRD traga essas ausências. Não trava a etapa.", DEV),
    "asset-fora-do-inventario": _x(
        "Imagens e ícones que não chegaram ao PRD",
        "Imagens, ícones e animações listados pelo design não aparecem no PRD.",
        "O dev não sabe que precisa deles.",
        "Peça, com **Refazer** de dev, a lista completa de imagens no PRD.", DEV),
    "chave-de-copy-ausente": _x(
        "Textos das telas sem lugar no PRD",
        "Textos das telas não estão, pelo código, na descrição da tela delas no PRD.",
        "O dev não sabe em que tela vai cada texto.",
        "Peça, com **Refazer** de dev, que cada texto apareça na tela dele.", DEV),
    "chave-sem-onde-vive": _x(
        "Textos sem dizer onde aparecem",
        "Textos estão na descrição da tela sem dizer em que parte dela aparecem.",
        "O dev vai posicionar os textos por conta própria.",
        "Peça, com **Refazer** de dev, onde cada texto aparece.", DEV),
    "tela-sem-story": _x(
        "Tela sem descrição no PRD",
        "Uma tela do inventário não tem a descrição dela no PRD.",
        "O dev não vai programar essa tela.",
        "Peça, com **Refazer** de dev, a descrição da tela.", DEV),
    "rf-p0-sem-criterio": _x(
        "Requisitos sem como conferir se ficaram prontos",
        "Requisitos obrigatórios do PRD não dizem como verificar que estão prontos.",
        "Sem o critério, ninguém consegue dizer se o dev entregou o que foi pedido.",
        "Peça, com **Refazer** de dev, o critério de aceite de cada requisito.", DEV),
    "status-de-gate-no-corpo": _x(
        "O PRD escreve o resultado das verificações",
        "O PRD traz linhas com o resultado das verificações da esteira (🟢 🟡 🔴).",
        "Esse resultado é da esteira e muda a cada execução; no PRD ele fica velho e engana.",
        "Peça, com **Refazer** de dev, que essas linhas saiam.", DEV),
    "schema-indefinido": _x(
        "Formato de dados citado e não definido",
        "O PRD cita formatos de dados de uma rota sem defini-los.",
        "O dev vai inventar os campos.",
        "Peça, com **Refazer** de dev, a definição de cada formato.", DEV),
    "tarefa-nao-atomica": _x(
        "Tarefa grande demais",
        "Uma tarefa do plano cobre muitos requisitos de uma vez.",
        "Tarefa que implementa a missão inteira não se estima nem se confere.",
        "Peça, com **Refazer** de dev, a tarefa dividida por entrega. Não trava a etapa.", DEV),
    "sem-idempotencia": _x(
        "Falta dizer o que acontece no clique repetido",
        "O PRD não diz o que acontece se a criança tocar duas vezes no mesmo botão.",
        "Um toque duplo pode registrar a jogada duas vezes.",
        "Peça, com **Refazer** de dev, a regra do segundo toque. Não trava a etapa.", DEV),
    "sem-rate-limit": _x(
        "Falta limite de uso por pessoa",
        "O PRD não diz quantas vezes por minuto cada pessoa pode usar as rotas da missão.",
        "Sem limite, um erro no aparelho pode sobrecarregar o servidor.",
        "Peça, com **Refazer** de dev, o limite. Não trava a etapa.", DEV),
    "sem-grant": _x(
        "Falta liberar o acesso às tabelas novas",
        "O PRD cria tabelas e não dá ao sistema permissão de usá-las.",
        "A missão falharia ao gravar.",
        "Peça, com **Refazer** de dev, a permissão. Não trava a etapa.", DEV),
    "plano-sem-porta": _x(
        "Falta o endereço de teste da missão",
        "O plano não diz em que porta (endereço local) a missão roda durante o desenvolvimento.",
        "Quem programa escolhe uma, e ela pode ser de outra missão.",
        "Peça, com **Refazer** de dev, a porta. Não trava a etapa.", DEV),
    "porta-ocupada": _x(
        "Endereço de teste já usado por outra missão",
        "A porta escolhida para a missão já é de outra.",
        "As duas missões não rodam juntas no computador de quem programa.",
        "Peça, com **Refazer** de dev, a próxima porta livre (está no detalhe).", DEV),
    "tipo-divergente-registrado": _x(
        "Tipo de dado diferente entre PRD e especificação",
        "Um campo tem um tipo no PRD e outro na especificação. O PRD seguiu a plataforma e registrou a troca.",
        "Quem programa precisa saber qual vale.",
        "A especificação deve acompanhar o PRD: confira e registre. Não trava a etapa.", DEV),
    "tipo-divergente-da-plataforma": _x(
        "Tipo de dado diferente do da plataforma",
        "Campos do PRD têm um tipo diferente do que a plataforma usa.",
        "A missão não conversaria com o resto da plataforma.",
        "Peça, com **Refazer** de dev, os tipos da plataforma.", DEV),
    "coluna-da-spec-ausente": _x(
        "Campo previsto na especificação faltando no PRD",
        "Um campo de dados previsto na especificação não está no modelo de dados do PRD.",
        "O dado não seria guardado.",
        "Peça, com **Refazer** de dev, o campo. Não trava a etapa.", DEV),
    "sessao-sem-rodada": _x(
        "Registro da partida fora do molde da plataforma",
        "O PRD guarda a partida da criança sem a rodada e a atividade, como a plataforma exige.",
        "Ao zerar a missão, as respostas se misturariam.",
        "Peça, com **Refazer** de dev, o molde da plataforma.", DEV),
    "erros-sem-tabela": _x(
        "Falta a tabela de erros",
        "O PRD não lista os erros possíveis e o que a tela mostra em cada um.",
        "Quem programa inventa os erros, e a tela não sabe o que mostrar.",
        "Peça, com **Refazer** de dev, a tabela.", DEV),
    "ia-sem-tabela": _x(
        "Uso de IA sem a ficha técnica",
        "A missão gera conteúdo com IA, e o PRD não traz a ficha de cada chamada (entrada, saída, limite, plano B).",
        "Sem a ficha, o custo e a segurança da IA ficam sem controle.",
        "Peça, com **Refazer** de dev, a ficha.", DEV),
    "rota-do-molde-ausente": _x(
        "Faltam as rotas que toda missão tem",
        "O PRD não declara as rotas padrão (zerar, pacotes da turma, pôr no ar, material do professor).",
        "Quem programa decide sozinho o caminho de cada uma.",
        "Peça, com **Refazer** de dev, as rotas padrão.", DEV),
    "rotas-sem-id": _x(
        "Rotas sem código",
        "O PRD não tem a tabela de rotas com um código por rota.",
        "Testes e tarefas não têm como apontar para a rota.",
        "Peça, com **Refazer** de dev, a tabela de rotas.", DEV),
    "rota-do-handoff-mudou": _x(
        "Rotas mudaram entre a passagem ao dev e o PRD",
        "Rotas do documento de passagem ao dev não aparecem no PRD.",
        "Se o PRD trocou uma rota por outra, quem programa precisa saber qual vale.",
        "Peça que o PRD diga qual rota substitui qual. Não trava a etapa.", DEV),
    "rota-fora-do-modulo": _x(
        "Rota pendurada no lugar errado",
        "Uma rota da missão foi colocada num módulo geral da plataforma, e não no módulo próprio da missão.",
        "Mistura a missão com o resto da plataforma.",
        "Peça, com **Refazer** de dev, a rota no módulo da missão. Não trava a etapa.", DEV),
    "rota-verbo-errado": _x(
        "Rota existente usada do jeito errado",
        "O documento usa uma rota que já existe na plataforma, mas com outra operação.",
        "A chamada falharia.",
        "Peça, com **Refazer** de dev, a operação certa.", DEV),
    "rota-inexistente": _x(
        "Rota que a plataforma não tem",
        "O documento usa uma rota que não existe na plataforma.",
        "A chamada falharia.",
        "Peça, com **Refazer** de dev, uma rota existente — ou registre a nova como pendência de plataforma.", DEV),
    "adr-inexistente": _x(
        "Cita uma decisão técnica que não existe",
        "O documento cita uma decisão técnica registrada (ADR) com um número que não existe.",
        "Quem programa vai procurar a decisão e não vai achar.",
        "Peça, com **Refazer**, a citação certa — ou registre a decisão como proposta nova.", DEV),
    "adr-numero-errado": _x(
        "Decisão técnica nova com número já usado",
        "O documento numera uma decisão técnica nova com um número que já é de outra.",
        "Duas decisões com o mesmo número confundem quem programa.",
        "Peça, com **Refazer**, o próximo número livre (está no detalhe).", DEV),
    "adr-sem-proposta": _x(
        "Decisão técnica nova sem a marca de proposta",
        "O documento cita como existente uma decisão técnica que ainda não existe.",
        "Quem programa vai procurar a decisão e não vai achar.",
        "Peça, com **Refazer**, que ela apareça como proposta, com dono.", DEV),
    "adr-titulo-divergente": _x(
        "Decisão técnica citada com outro assunto",
        "O documento cita uma decisão técnica existente pelo número, mas com outro assunto.",
        "Duas decisões com o mesmo número confundem quem programa.",
        "Peça, com **Refazer**, o título certo — ou um número novo como proposta.", DEV),
    "artefato-inexistente": _x(
        "Documento cita arquivos que não existem",
        "O documento cita arquivos da missão com nomes que não existem na pasta.",
        "Quem lê vai procurar o arquivo e não vai achar.",
        "Peça, com **Refazer**, os caminhos certos (estão no detalhe).", None),
    "manifesto-ausente": _x(
        "Falta a ficha técnica da missão no PRD",
        "O PRD não traz a ficha que registra a missão na plataforma (nome, versão, série, permissões).",
        "Quem programa preencheria a ficha por conta própria.",
        "Peça, com **Refazer** de dev, a ficha completa.", DEV),
    "registro-da-plataforma-ausente": _x(
        "Falta o registro da missão nova na plataforma",
        "A missão é nova, e o PRD não diz onde registrá-la (guia da aula, ficha do professor).",
        "A missão não apareceria para o professor.",
        "Peça, com **Refazer** de dev, os registros.", DEV),
    "ficha-ausente": _x(
        "Falta a ficha de evidência no PRD",
        "O PRD não tem a ficha que diz como o servidor calcula o nível de cada habilidade.",
        "O servidor não saberia calcular o nível de ninguém.",
        "Peça, com **Refazer** de dev, a ficha.", DEV),
    "secao-11-ausente": _x(
        "Falta o modelo de dados no PRD", "O PRD não tem a seção do modelo de dados.",
        "Quem programa não sabe o que guardar.", "Peça, com **Refazer** de dev, a seção.", DEV),
    "secao-12-ausente": _x(
        "Faltam as rotas no PRD", "O PRD não tem a seção das rotas (como o aplicativo conversa com o servidor).",
        "Quem programa inventa as rotas, os dados e os erros.", "Peça, com **Refazer** de dev, a seção.", DEV),
    "secao-14-ausente": _x(
        "Falta a parte pedagógica do PRD", "O PRD não tem a seção de pedagogia, onde fica a matriz das habilidades.",
        "O dev não vê como cada habilidade é medida.", "Peça, com **Refazer** de dev, a seção.", DEV),
    "d0-orfao": _x(
        "Documento cita decisões do design que não estão registradas",
        "Um documento cita decisões do design pelo código, mas o bloco onde elas ficam não existe.",
        "Quem lê não acha a decisão citada.",
        "Peça, com **Refazer**, que a citação ou o bloco de decisões seja corrigido.", None),
    # ---------------------------------------------------------- indicadores e perguntas de produto
    "kpi-tela-divergente": _x(
        "Indicador medido na tela errada",
        "Um indicador diz medir uma tela, mas usa uma ação que acontece em outra.",
        "O número vai sair e não vai medir o que o indicador diz.",
        "Peça, com **Refazer** de dev, a ação certa (ou a tela certa) para o indicador.", DEV),
    "kpi-operacional-com-resultado": _x(
        "Indicador calculado com um dado que não existe",
        "Um indicador usa um registro que não guarda o resultado que ele quer contar.",
        "O número sairia sempre vazio ou errado.",
        "Peça, com **Refazer** de dev, o cálculo com o dado que a missão guarda. Não trava a etapa.", DEV),
    "kpi-herdada-reescrita": _x(
        "Pergunta padrão da plataforma reescrita",
        "Um indicador herda uma pergunta padrão da plataforma, mas a reescreve com outro sentido.",
        "As missões deixam de ser comparáveis entre si.",
        "Peça, com **Refazer** de dev, a pergunta padrão como é. Não trava a etapa.", DEV),
    "tabela-kpi-ausente": _x(
        "Falta a tabela de indicadores", "O PRD não traz a tabela de indicadores (KPIs) legível.",
        "Ninguém sabe o que a missão vai medir.", "Peça, com **Refazer** de dev, a tabela.", DEV),
    "pq-tabela-ausente": _x(
        "Faltam as perguntas de produto",
        "A especificação não traz a tabela de perguntas que o time quer responder com os dados da missão.",
        "Sem perguntas, os dados coletados não servem para decidir nada.",
        _REFAZER_PRODUTO, PO),
    "core-action-ausente": _x(
        "Falta dizer qual é a ação central",
        "A especificação não diz qual ação mostra que a criança passou pela decisão central da missão.",
        "Não dá para separar quem fez a missão de quem só a abriu.",
        _REFAZER_PRODUTO, PO),
    "declared-lessons-ausente": _x(
        "Falta dizer quantas aulas a missão tem",
        "A especificação não diz em quantas aulas a missão foi pensada.",
        "Uma missão de duas aulas apareceria como abandonada pela metade.",
        _REFAZER_PRODUTO, PO),
    "perguntas-herdadas-ausente": _x(
        "Faltam as perguntas padrão da plataforma",
        "A especificação não lista as perguntas padrão que toda missão do grupo herda.",
        "As missões deixam de ser comparáveis entre si.",
        _REFAZER_PRODUTO, PO),
    "sinal-universal-ausente": _x(
        "Falta um registro padrão de ação",
        "A tabela de registros não tem um sinal padrão que toda missão envia (por exemplo, o aviso de inatividade).",
        "Perguntas padrão da plataforma ficam sem resposta.",
        "Peça, com **Refazer**, a linha que falta (o detalhe diz qual).", None),
    # ---------------------------------------------------------- app simulado e mini-jogo (decisão do PO, D8)
    "ambiente-ausente-na-spec": _x(
        "Falta escolher o app simulado",
        "A especificação de produto não diz qual app a missão imita (Instagram, WhatsApp…) nem se é mini-jogo.",
        "Sem essa escolha, o design decide sozinho a cara da missão.",
        "Escolha o app na lista do contrato do de acordo de produto.", PO),
    "classe-ambiente-divergente": _x(
        "Tipo de missão e app simulado não combinam",
        "A especificação diz um tipo de missão (app simulado ou mini-jogo) e escolhe uma seção do design system do "
        "outro tipo.",
        "O design não sabe qual dos dois vale.",
        "Corrija um dos dois com **Refazer** de produto.", PO),
    "escolha-de-ambiente-com-o-po": _x(
        "App novo ou mini-jogo esperando o PO",
        "A missão propõe um app simulado novo ou um mini-jogo; essa escolha é do PO e está na lista do de acordo.",
        "Criar app novo custa caro para a plataforma; por isso só o PO decide.",
        _DECIDA_NA_LISTA, PO),
    "escolha-de-ambiente-recusada": _x(
        "O app que o PO recusou continua na especificação",
        "O PO recusou o app simulado ou o mini-jogo no de acordo, e a especificação ainda o usa.",
        "A missão segue com uma escolha que o PO recusou.",
        "Use **Refazer** de produto com um app existente (ou com o que o PO escreveu no lugar).", PO),
    "escolha-de-ambiente-sem-o-po": _x(
        "App novo ou mini-jogo escolhido sem o PO",
        "A especificação fixa um app simulado novo ou um mini-jogo sem decisão do PO.",
        "Criar app novo é decisão do PO; o agente não escolhe no lugar dele.",
        "Peça, com **Refazer** de produto, que a escolha vire proposta — ela aparece na lista para você decidir.", PO),
    "minijogo-fora-da-faixa": _x(
        "Mini-jogo numa série que não usa mini-jogo",
        "A missão é mini-jogo, e mini-jogo só vale do 1º ao 5º ano. Do 6º ano em diante, a missão imita um app.",
        "A missão sai fora do padrão da série.",
        "Use **Refazer** de produto com um app simulado da lista.", PO),
    "minijogo-regras-e-fases-com-o-po": _x(
        "Regras e fases do mini-jogo esperando o PO",
        "As regras e as fases do mini-jogo estão pendentes de decisão do PO no de acordo de produto.",
        "Sem regras e fases, o design não tem o que desenhar.",
        _DECIDA_NA_LISTA, PO),
    "fase-sem-tela": _x(
        "Fase da missão sem tela",
        "Fases da especificação não têm linha na jornada do design — e, portanto, nenhuma tela.",
        "A criança passaria por uma fase que ninguém desenhou.",
        "Peça ao design, com **Refazer**, a linha da fase na jornada.", DESIGN),
    "devolucao-a-produto": _x(
        "O design propôs mudar algo de produto",
        "Um agente de design propôs mudar o app simulado ou o tipo da missão — o que é decisão de produto.",
        "Só o PO decide; a proposta espera a resposta dele.",
        _DECIDA_NA_LISTA, PO),
    # ---------------------------------------------------------- quem fechou a decisão
    "decisao-do-po-pelo-agente": _x(
        "Ponto do PO fechado pelo agente",
        "Um número ou uma proposta que esperava o PO foi fechado por um agente, sem parecer do PO com data.",
        "A missão segue com uma decisão que o PO não tomou.",
        "Confira o valor. Se vale, confirme na lista do contrato; se não, use **Refazer** de produto.", PO),
    "decisao-do-po-pelo-parecer": _x(
        "Ponto do PO fechado a partir do parecer",
        "Um número ou uma proposta foi fechado com base num parecer do PO. A esteira não sabe se o parecer diz "
        "exatamente isso.",
        "Se o agente leu o parecer errado, a decisão não é a do PO.",
        "Confira se o valor é o que você decidiu. Não trava a etapa.", PO),
    "mecanica-pelo-parecer": _x(
        "Lacuna de produto fechada a partir do parecer",
        "Uma lacuna de produto (mecânica, currículo, número ou proposta) foi fechada com base num parecer do PO.",
        "Se o agente leu o parecer errado, a decisão não é a do PO.",
        "Confira se o que foi fechado é o que você decidiu. Não trava a etapa.", PO),
    "gate0-aplicado-a-montante": _x(
        "Documento usava a especificação de antes da correção",
        "Um documento trazia a parte de produto como estava antes da última correção do PO; a esteira trocou pela "
        "versão corrigida.",
        "É um registro: a correção do PO chegou ao documento.",
        "Nada a fazer; confira se quiser.", None),
    "glossario-proibe-o-aprovado": _x(
        "Lista de nomes proíbe um termo que o PO aprovou",
        "O glossário da missão proíbe um termo que o one-pager aprovado usa.",
        "Os documentos seguintes vão trocar um texto que o PO aprovou.",
        "Decida qual termo vale e corrija com **Refazer** de produto.", PO),
    "bloco-proprio-ausente": _x(
        "Um agente respondeu sem a parte que só ele escreve",
        "Um agente devolveu o documento sem o bloco pelo qual ele responde; o bloco ficou como estava.",
        "Quem cita uma decisão desse bloco mais adiante cita algo que não está lá.",
        "Peça **Refazer** da etapa. Se voltar a acontecer, avise o time técnico.", ESTEIRA),
    # ---------------------------------------------------------- BNCC (lado do código)
    "bloco-11": _x(
        "Não achou a parte do currículo",
        "A esteira não achou o bloco do currículo na especificação e leu os códigos da BNCC no texto inteiro.",
        "A conferência da BNCC pode ter pego códigos citados por outro motivo.",
        "Confira a lista de habilidades. Não trava a etapa.", ESTEIRA),
    "sem-codigo": _x(
        "Nenhuma habilidade da BNCC declarada",
        "A especificação não declara nenhuma habilidade de Computação da BNCC.",
        "A missão não diz o que ensina.",
        _REFAZER_PRODUTO, PO),
    "serie": _x(
        "Série da missão não identificada",
        "A esteira não achou a série (ano) da missão.",
        "Sem a série, não dá para conferir se as habilidades são do ano certo.",
        _REFAZER_PRODUTO, PO),
    "texto-divergente": _x(
        "Habilidade da BNCC citada com outro texto",
        "Uma habilidade aparece com um texto que não é o oficial da BNCC.",
        "A escola confere o texto oficial; outro texto parece outra habilidade.",
        "Peça, com **Refazer** de produto, o texto oficial (está no detalhe).", PO),
    # sempre 🔴 em `tools/bncc.py`: o eixo errado declara letramento digital que a habilidade não tem
    "eixo-divergente": _x(
        "Habilidade classificada no eixo errado",
        "A habilidade aparece num eixo da BNCC que não é o dela — ou, no Ensino Médio, aparece como Cultura Digital "
        "(letramento digital) sem estar na lista de letramento.",
        "O eixo decide o que a missão pode declarar como letramento digital: com o eixo errado, ela promete à escola um "
        "recorte que não cobre.",
        "Peça, com **Refazer** de produto, que a habilidade apareça com o eixo oficial (o trecho diz qual).", PO),
    # ---------------------------------------------------------- pedagógico e Stitch
    "pedagogico-ausente": _x(
        "Falta o one-pager pedagógico",
        "A missão não tem o one-pager pedagógico, que fecha o design e é o documento do de acordo de design.",
        "Sem ele, o time não tem a missão inteira em linguagem de sala de aula para aprovar.",
        "Peça **Refazer** de design.", DESIGN),
    "pedagogico-apagado-no-dev": _x(
        "O one-pager pedagógico sumiu no dev",
        "O pedagógico aprovado no de acordo de design sumiu durante o dev; a esteira o devolveu.",
        "O que o time aprovou não pode sumir.",
        "Confira se ele está como foi aprovado.", DEV),
    "pedagogico-reescrito-no-dev": _x(
        "O one-pager pedagógico mudou no dev",
        "O pedagógico aprovado no de acordo de design mudou durante o dev.",
        "O dev não muda o que o time aprovou no design.",
        "Confira a mudança; se não devia ter acontecido, use **Refazer** de dev.", DEV),
    "stitch-tela-sem-id": _x(
        "Telas com código fora do padrão não foram ao Stitch",
        "Algumas telas do inventário têm um código fora do padrão e não foram geradas no Stitch.",
        "Essas telas ficam sem desenho.",
        "Peça ao design, com **Refazer**, os códigos no padrão.", DESIGN),
    "sem-identificacao": _x(
        "Missão sem código nem nome",
        "A execução terminou sem o código curto e o nome da missão.",
        "A missão não entra na lista de missões geradas, e a comparação com as outras não a vê.",
        "Peça **Refazer** da etapa. Se voltar a acontecer, avise o time técnico.", ESTEIRA),
    "precisa-humano": _x(
        "O verificador pediu uma decisão sem dizer qual",
        "Um verificador pediu a decisão de uma pessoa, mas não disse qual.",
        "Algo ficou para decidir e não está à vista.",
        "Abra o relatório do verificador nos passos da esteira, ou pergunte à etapa pelo campo de mensagem.", None),
    "profundidade-nao-estrita": _x(
        "Profundidade reprovou, mas a esteira deixou seguir",
        "O revisor de profundidade reprovou a missão, e a configuração atual da esteira rebaixou o 🔴 para 🟡.",
        "A missão pode estar rasa; a esteira só não está travando por isso.",
        "Leia as notas de profundidade no cartão e decida se pede **Refazer** de produto.", PO),
    # ---------------------------------------------------------- falhas da própria esteira
    "secao-ausente": _x(
        "Parte do relatório não veio",
        "A esteira esperava uma parte do relatório de um agente e não a encontrou.",
        "O que essa parte traria ficou de fora desta execução.",
        "Peça **Refazer** da etapa. Se voltar a acontecer, avise o time técnico.", ESTEIRA),
}

# ------------------------------------------------------------------ códigos que o acervo ainda não mostrou
# Os verificadores determinísticos emitem estes códigos por `falha(…)`, `_achado(…)`, `bloqueio(…)` e `atencao(…)`, e
# não só em dicionário literal. A revisão do PR #82 (25/10/2026) achou 138 deles no texto genérico — `kpi-sem-evento`,
# `pq-faltando`, `prototipo-nao-abre`, vários 🔴 —, que o acervo de 15 missões ainda não tinha mostrado. O teste varre
# as chamadas e exige a entrada de cada um.
_REFAZER_DEV = "Peça, com **Refazer** de dev, "
_REFAZER_DESIGN = "Peça **Refazer** de design."
_REFAZER_DA_ETAPA = "Peça, com **Refazer** desta etapa, "
for _codigo_novo, _exp_nova in {
    # ---------------------------------------------------------- como cada habilidade é medida (spec e one-pager)
    "12a-sem-tabela": _x(
        "Falta a tabela de como cada habilidade é medida",
        "O one-pager não traz a tabela que diz, para cada habilidade, de qual ação da criança sai o nível dela.",
        "Sem ela, ninguém sabe como a missão mostra ao professor o que a criança aprendeu.",
        _REFAZER_PRODUTO, PO),
    "canal-b-vazio": _x(
        "Pergunta do fim prometida e não escrita",
        "A habilidade diz que também é medida por uma pergunta no fim da missão, mas a pergunta e as alternativas não "
        "estão lá.",
        "A habilidade fica sem a medida prometida.",
        "Peça, com **Refazer** de produto, a pergunta com as três alternativas — ou que a habilidade seja medida só "
        "pela ação na tela.", PO),
    "canal-b-sem-niveis": _x(
        "Pergunta do fim sem dizer o nível de cada resposta",
        "As alternativas da pergunta do fim não dizem a qual nível cada uma leva (Atingiu, Em processo, Não atingiu).",
        "O professor não teria como ler a resposta da criança.",
        _REFAZER_PRODUTO, PO),
    "grau-invalido": _x(
        "Medida sem dizer quão confiável é",
        "Uma medida não diz se é só um indício ou uma nota calculada.",
        "O relatório do professor misturaria medida forte com indício.",
        _REFAZER_PRODUTO, PO),
    "scored-1-sinal": _x(
        "Nota calculada com um sinal só",
        "Uma medida se apresenta como nota calculada, mas só tem um sinal do que a criança fez; a regra pede ao menos "
        "dois sinais independentes.",
        "Um sinal só é indício, não nota: o professor confiaria demais nele.",
        "Peça, com **Refazer** de produto, um segundo sinal — ou que a medida passe a ser só indício.", PO),
    "habilidade-sem-canal": _x(
        "Habilidade sem dizer como é medida",
        "A tabela não diz se a habilidade é medida pela ação na tela, por uma pergunta no fim ou pelos dois.",
        "Quem programa inventa a forma de medir.",
        _REFAZER_PRODUTO, PO),
    "habilidade-sem-contrato": _x(
        "Habilidade sem regra de medida",
        "Uma habilidade declarada não tem linha na tabela que diz como ela é medida.",
        "Habilidade que nada mede some do relatório do professor.",
        _REFAZER_PRODUTO, PO),
    "habilidade-sem-medida": _x(
        "Habilidade que nenhuma medida acompanha",
        "Nenhuma das medidas da missão está ligada a esta habilidade.",
        "Habilidade que nada mede é currículo só no papel: some do relatório do professor.",
        _REFAZER_PRODUTO, PO),
    "habilidade-sem-momento": _x(
        "Habilidade sem o momento em que é medida",
        "A tabela não aponta a etapa ou a tela em que a criança mostra a habilidade.",
        "Sem o momento, o design não sabe onde pôr a ação que mede.",
        _REFAZER_PRODUTO, PO),
    "regra-ternaria-ausente": _x(
        "Falta a regra dos três níveis",
        "A habilidade não diz, por extenso, o que separa Atingiu, Em processo e Não atingiu.",
        "Quem programa decidiria sozinho como classificar a criança.",
        _REFAZER_PRODUTO, PO),
    # ---------------------------------------------------------- profundidade pedagógica (núcleo)
    "anatomia-ausente": _x(
        "Falta o roteiro da descoberta («Anatomia do aha»)",
        "O núcleo não traz a tabela de seis passos que mostra como a criança chega à descoberta central.",
        "Sem o roteiro, ninguém confere se a missão tem uma descoberta ou só uma sequência de passos.",
        _REFAZER_PRODUTO, PO),
    "anatomia-incompleta": _x(
        "Roteiro da descoberta incompleto",
        "Um passo da «Anatomia do aha» está vazio, curto demais ou só com um marcador.",
        "O passo que falta é justamente onde a descoberta pode não acontecer.",
        _REFAZER_PRODUTO, PO),
    "cobertura-ausente": _x(
        "Falta a tabela dos conceitos do material vividos na tela",
        "O núcleo não diz, conceito a conceito do material do bimestre, o que a criança faz na tela e como o "
        "professor aprofunda.",
        "Não dá para saber se a missão cobre o material.",
        _REFAZER_PRODUTO, PO),
    "conceito-sem-destino": _x(
        "Conceito do material esquecido",
        "Um conceito central do material não aparece na missão nem foi deixado de fora com justificativa.",
        "O conceito pode ter sido esquecido sem ninguém decidir isso.",
        _REFAZER_PRODUTO, PO),
    "fora-sem-justificativa": _x(
        "Conceito deixado de fora sem dizer por quê",
        "Um conceito do material ficou de fora sem dizer por que não cabe nesta missão nem em que semana do bimestre "
        "ele é tratado.",
        "O professor não sabe onde a turma vê esse conceito.",
        _REFAZER_PRODUTO, PO),
    "limiar-fora": _x(
        "O conceito central do bimestre ficou de fora",
        "O conceito que o material existe para mudar no estudante (o conceito limiar) não está no núcleo da missão.",
        "A virada da missão precisa ser sobre ele; sem ele, a missão perde o propósito.",
        _REFAZER_PRODUTO, PO),
    "limiar-fora-do-aha": _x(
        "O conceito central não está na decisão nem na descoberta",
        "O conceito limiar aparece só numa etapa secundária; ele precisa estar no momento em que a criança decide ou "
        "no resultado, onde acontece a descoberta.",
        "É a escolha da criança sobre ele que a virada desmonta.",
        _REFAZER_PRODUTO, PO),
    "crenca-sem-id": _x(
        "A crença que a missão derruba não está identificada",
        "O passo «Crença de entrada» não aponta qual crença do mapa de conceitos a missão derruba.",
        "Fica difícil conferir se a virada mexe na crença certa.",
        _REFAZER_PRODUTO, PO),
    "mapa-ausente": _x(
        "Sem mapa de conceitos do material",
        "Não há mapa de conceitos legível: a esteira não conferiu se a missão cobre o material do bimestre.",
        "A missão pode estar certa — mas ninguém mediu.",
        "Se quiser a conferência, peça **Refazer** de produto; senão, siga e registre no de acordo.", PO),
    "trecho-sem-citacao": _x(
        "Conceito sem a citação do material",
        "Um conceito do mapa não cita entre aspas o trecho do material de onde saiu.",
        "Conceito sem citação pode ter sido inventado pelo agente, e não vir do bimestre.",
        "Confira o conceito no material. Se estiver errado, use **Refazer** de produto.", PO),
    # ---------------------------------------------------------- a conta da virada (tabela 1.3)
    "conta-nao-fecha": _x(
        "A conta da virada não fecha",
        "Com os critérios e os pesos da própria tabela, o vencedor calculado não é o que o texto declara.",
        "A criança que refizer a conta vê outro resultado: a descoberta desmorona.",
        _REFAZER_PRODUTO, PO),
    "empate": _x(
        "Empate na conta da virada",
        "Duas opções empatam na conta; a missão não teria o que recomendar.",
        "Sem um vencedor, não há virada para a criança perceber.",
        _REFAZER_PRODUTO, PO),
    "sem-virada": _x(
        "A conta não muda: não há virada",
        "Antes e depois do dado novo, o vencedor calculado é o mesmo.",
        "Sem mudança, a criança não vive a descoberta que a missão promete.",
        _REFAZER_PRODUTO, PO),
    "sentido-indefinido": _x(
        "Critério da conta sem dizer se vale mais ou menos",
        "Um critério da conta não diz se ganha o maior ou o menor valor.",
        "Sem isso, a conta não pode ser refeita nem conferida.",
        _REFAZER_PRODUTO, PO),
    "tabela-ilegivel": _x(
        "Tabela da conta da virada ilegível",
        "A tabela da conta existe, mas sem as colunas esperadas (Opção, Critério, Melhor quando, Peso, Antes, Depois) "
        "com números.",
        "A esteira não consegue refazer a conta para conferir a virada.",
        _REFAZER_PRODUTO, PO),
    "valor-sem-numero": _x(
        "Conta da virada com valores faltando",
        "Algumas linhas da tabela da conta não têm número em Antes ou em Depois.",
        "A conta não pode ser feita.",
        _REFAZER_PRODUTO, PO),
    "vencedor-nao-declarado": _x(
        "Conta sem o vencedor declarado",
        "A tabela da conta não declara qual opção vence antes (ou depois) do dado novo.",
        "Não dá para conferir se a virada acontece.",
        _REFAZER_PRODUTO, PO),
    "nao-se-aplica-sem-motivo": _x(
        "Conta da virada dispensada sem motivo",
        "A tabela da conta diz que não se aplica a esta missão, sem dizer por quê.",
        "A descoberta pode ficar sem a conta que a mostra.",
        "Confira se a missão dispensa mesmo a conta. Se não dispensa, use **Refazer** de produto.", PO),
    # ---------------------------------------------------------- briefing e one-pager
    "ancora-do-briefing-trocada": _x(
        "Habilidade principal diferente da do briefing",
        "O briefing marca uma habilidade como a principal, e o one-pager pôs outra como foco.",
        "A troca pode ser certa, mas é decisão do PO, não do agente.",
        "Confira a troca. Se ela vale, registre no de acordo; se não, use **Refazer** de produto pedindo a habilidade "
        "do briefing.", PO),
    "habilidade-do-briefing-sumiu": _x(
        "Habilidade do briefing sumiu do one-pager",
        "O briefing lista habilidades da BNCC que o one-pager não menciona.",
        "Cortar habilidade do briefing é decisão do PO, não do agente.",
        "Use **Refazer** de produto pedindo que a habilidade volte. Se você quer mesmo cortá-la, diga isso no pedido, "
        "para que o one-pager registre a decisão como sua.", PO),
    "habilidade-acrescentada": _x(
        "Habilidade que o aprovado não tem",
        "Uma habilidade da BNCC aparece neste documento e não está no material aprovado.",
        "A missão prometeria à escola algo que o PO não aprovou.",
        _REFAZER_DA_ETAPA + "que a habilidade saia. Se ela deve entrar, o pedido é a produto.", None),
    "habilidade-perdida": _x(
        "Habilidade aprovada que sumiu",
        "Uma habilidade do material aprovado sumiu deste documento.",
        "O que o PO aprovou se perde no caminho.",
        _REFAZER_DA_ETAPA + "que a habilidade volte.", None),
    "tempo-alterado": _x(
        "Tempo da missão diferente do aprovado",
        "O documento declara um tempo total na tela diferente do que o one-pager aprovado dá.",
        "A aula foi planejada com o tempo aprovado.",
        _REFAZER_DA_ETAPA + "o tempo aprovado. Se você quer outro tempo, o pedido é a produto.", None),
    "tempo-de-etapa-divergente": _x(
        "Tempo por etapa diferente do aprovado",
        "O tempo na tela de cada etapa não bate com a tabela de tempos do one-pager aprovado.",
        "A aula foi planejada com os tempos aprovados.",
        "Confira os tempos. Se a diferença não tem motivo, peça, com **Refazer** desta etapa, os tempos aprovados.",
        None),
    "divergencia-do-contrato-sem-registro": _x(
        "O próprio material aprovado se contradiz",
        "Duas partes do material aprovado (o one-pager e a especificação, por exemplo) dizem coisas diferentes sobre o "
        "mesmo ponto, e isso não está registrado como pendência.",
        "O documento não pode escolher sozinho qual vale: a escolha é do PO.",
        "Decida qual vale e peça a correção a produto (**Refazer** de produto, ou devolva a missão a produto).", PO),
    "divergencia-registrada": _x(
        "Contradição no aprovado, já registrada para o PO",
        "Duas partes do material aprovado divergem, e isso está registrado como pendência de produto.",
        "Até o PO decidir, o dev não sabe qual vale.",
        "Decida qual vale e registre no de acordo, ou use **Refazer** de produto.", PO),
    # ---------------------------------------------------------- perguntas de produto da especificação (bloco 9)
    "spec-sem-tabela-eventos": _x(
        "Especificação sem a tabela de ações registradas",
        "A esteira não achou, na especificação, a tabela das ações da criança que a missão registra.",
        "As perguntas de produto não podem ser conferidas com o que a missão de fato registra.",
        _REFAZER_PRODUTO, PO),
    "core-action-formato": _x(
        "Ação central da missão fora do formato",
        "A ação central da missão não está no formato «verbo objeto» que a plataforma registra.",
        "A decisão central da criança não seria registrada.",
        _REFAZER_PRODUTO, PO),
    "core-action-sem-evento": _x(
        "Ação central que nada registra",
        "A ação central da missão não está na tabela de ações registradas.",
        "A decisão central da criança não seria medida.",
        _REFAZER_PRODUTO, PO),
    "herdada-inexistente": _x(
        "Pergunta comum que não existe",
        "A missão herda uma pergunta comum a todas as missões (T1 a T21) que não existe.",
        "A pergunta não tem resposta nem comparação com as outras missões.",
        _REFAZER_PRODUTO, PO),
    "herdada-faltando": _x(
        "Faltam perguntas comuns que a missão deve herdar",
        "A missão deixa de fora perguntas comuns a todas as missões que cabem a ela responder.",
        "As missões deixam de ser comparáveis.",
        _REFAZER_PRODUTO, PO),
    "herdada-plataforma": _x(
        "Pergunta comum que só a plataforma responde",
        "A missão herda uma pergunta que só a plataforma consegue responder; a missão não tem esse dado.",
        "A pergunta ficaria sem resposta.",
        "Peça, com **Refazer** de produto, que ela saia da lista.", PO),
    "pq-faltando": _x(
        "Faltam perguntas de produto",
        "A especificação tem menos perguntas de produto do que a missão precisa.",
        "O que o time quer aprender com os dados da missão fica sem pergunta.",
        "Peça, com **Refazer** de produto, as perguntas que faltam: o agente pode propor, e você valida.", PO),
    "pq-excedente": _x(
        "Perguntas de produto demais",
        "A missão tem mais perguntas de produto do que o limite.",
        "Pergunta demais dilui as que mudam decisão.",
        "Escolha as que mudam decisão e peça, com **Refazer** de produto, que as outras saiam.", PO),
    "pq-sem-pergunta": _x(
        "Linha de pergunta de produto vazia",
        "Uma linha da tabela de perguntas de produto não tem a pergunta.",
        "Não há o que medir.",
        _REFAZER_PRODUTO, PO),
    "pq-nao-e-pergunta": _x(
        "Pergunta de produto que não é pergunta",
        "Uma «pergunta» de produto está escrita como afirmação.",
        "Sem pergunta, não há resposta que mude decisão.",
        _REFAZER_PRODUTO, PO),
    "pq-duplicada": _x(
        "Pergunta de produto repetida",
        "Duas linhas fazem a mesma pergunta de produto.",
        "Uma pergunta escrita duas vezes ocupa o lugar de outra.",
        _REFAZER_PRODUTO, PO),
    "pq-sem-decisao": _x(
        "Pergunta de produto sem a decisão que dispara",
        "A pergunta não diz o que o time decide com a resposta.",
        "Pergunta que não muda nada é curiosidade.",
        _REFAZER_PRODUTO, PO),
    "pq-decisao-sem-limiar": _x(
        "Decisão sem o número que a dispara",
        "A pergunta diz que decisão tomar, mas não a partir de quanto.",
        "Ninguém saberia quando agir.",
        _REFAZER_PRODUTO, PO),
    "pq-sem-corte": _x(
        "Pergunta sem dizer como a resposta é lida",
        "A pergunta não diz o recorte da resposta (por turma, por escola…).",
        "A resposta pode ser lida do jeito errado.",
        _REFAZER_PRODUTO, PO),
    "pq-corte-invalido": _x(
        "Pergunta com recorte desconhecido",
        "A pergunta usa um recorte (por turma, por escola…) fora da lista aceita.",
        "A plataforma não saberia separar a resposta assim.",
        _REFAZER_PRODUTO, PO),
    "pq-sem-acao": _x(
        "Pergunta sem a ação que a responde",
        "A pergunta não nomeia a ação da criança que a responde.",
        "Ninguém saberia de onde tirar a resposta.",
        _REFAZER_PRODUTO, PO),
    "pq-acao-sem-evento": _x(
        "Pergunta respondida por uma ação que nada registra",
        "A pergunta aponta uma ação que não está na tabela de ações registradas.",
        "Ninguém registra o que responderia a pergunta.",
        _REFAZER_PRODUTO, PO),
    "pq-evento-nao-mede": _x(
        "Pergunta que pede um número que ninguém registra",
        "A pergunta aponta uma ação registrada que só diz que aconteceu, não quanto.",
        "A pergunta pede um número que a missão não guarda.",
        _REFAZER_PRODUTO, PO),
    "pq-origem-invalida": _x(
        "Pergunta sem dizer de onde veio",
        "A pergunta não diz se veio do PO ou se é proposta do agente.",
        "Proposta do agente pode passar por decisão do PO.",
        _REFAZER_PRODUTO, PO),
    "pq-acoes-pouco-distintas": _x(
        "Perguntas de produto que medem a mesma coisa",
        "Várias perguntas se apoiam na mesma ação da criança: na prática, são uma pergunta só.",
        "O time aprende menos do que parece.",
        _REFAZER_PRODUTO, PO),
    # ---------------------------------------------------------- indicadores do PRD
    "kpi-sem-pergunta": _x(
        "Indicador sem a pergunta que responde",
        "Um indicador do PRD não diz que pergunta ele responde.",
        "Número sem pergunta não muda decisão.",
        _REFAZER_DEV + "a pergunta de cada indicador.", DEV),
    "kpi-sem-decisao": _x(
        "Indicador sem a decisão que dispara",
        "Um indicador não diz o que muda conforme o valor.",
        "Número que não muda decisão é enfeite.",
        _REFAZER_DEV + "a decisão de cada indicador.", DEV),
    "kpi-sem-evento": _x(
        "Indicador sem a ação que o alimenta",
        "Um indicador não diz de qual ação registrada da criança ele sai.",
        "Ninguém sabe de onde o número sai.",
        _REFAZER_DEV + "a ação que alimenta o indicador.", DEV),
    "kpi-evento-inexistente": _x(
        "Indicador usa uma ação que não existe",
        "Um indicador cita uma ação registrada que não está na tabela de ações.",
        "O número nunca seria calculado.",
        _REFAZER_DEV + "que o indicador use uma ação da tabela.", DEV),
    "kpi-aponta-tabela-ou-rota": _x(
        "Indicador alimentado pela coisa errada",
        "Um indicador diz que sai de uma tabela de dados ou de um endereço do sistema, e não de uma ação registrada da "
        "criança.",
        "Tabela guarda; o que se conta é a ação.",
        _REFAZER_DEV + "a ação que alimenta o indicador.", DEV),
    "kpi-herdada-inexistente": _x(
        "Indicador herda uma pergunta que não existe",
        "Um indicador cita uma pergunta comum (T1 a T21) que não existe.",
        "O indicador não tem pergunta de verdade.",
        _REFAZER_DEV + "a pergunta comum certa.", DEV),
    "kpi-herdada-evento": _x(
        "Indicador comum calculado com outra ação",
        "Um indicador herdado das perguntas comuns a todas as missões usa uma ação diferente da prevista.",
        "As missões deixam de ser comparáveis.",
        _REFAZER_DEV + "a ação prevista para a pergunta comum.", DEV),
    "kpi-herdada-plataforma": _x(
        "Indicador que só a plataforma calcula",
        "Um indicador herda uma pergunta que só a plataforma responde; a missão não tem o dado.",
        "O indicador ficaria sem número.",
        _REFAZER_DEV + "que o indicador saia e vire pendência de plataforma.", DEV),
    "kpi-pq-inexistente": _x(
        "Indicador para uma pergunta de produto que não existe",
        "O PRD cita uma pergunta de produto que a especificação não tem.",
        "Quem decide o que se quer saber é produto, com o PO — o PRD não inventa pergunta.",
        _REFAZER_DEV + "que o indicador saia, ou leve a pergunta a produto.", DEV),
    "pq-sem-kpi": _x(
        "Pergunta de produto sem indicador no PRD",
        "Uma pergunta de produto decidida na especificação não tem indicador no PRD.",
        "A pergunta se perde entre produto e dev.",
        _REFAZER_DEV + "o indicador da pergunta.", DEV),
    "corte-invalido": _x(
        "Indicador com recorte desconhecido",
        "Um indicador usa um recorte (por turma, por escola…) fora da lista aceita.",
        "A plataforma não saberia separar o número assim.",
        _REFAZER_DEV + "um recorte da lista.", DEV),
    "baseline-ausente": _x(
        "Indicador sem ponto de partida",
        "Um indicador não diz o valor de partida nem que ele ainda não existe.",
        "Sem ponto de partida, não dá para saber se a missão melhorou algo.",
        _REFAZER_DEV + "o valor com a fonte — ou a frase «sem baseline — primeira medição».", DEV),
    "baseline-zero": _x(
        "Ponto de partida «0%» que ninguém mediu",
        "Um indicador tem ponto de partida 0%, sem fonte.",
        "Zero inventado parece medição.",
        _REFAZER_DEV + "o valor com a fonte — ou a frase «sem baseline — primeira medição».", DEV),
    "baseline-sem-origem": _x(
        "Ponto de partida sem fonte",
        "Um indicador tem um valor de partida sem dizer de onde veio.",
        "Número sem fonte pode ter sido inventado.",
        "Confira de onde veio o número. Se não há fonte, peça, com **Refazer** de dev, que ele saia.", DEV),
    "payload-nao-computa": _x(
        "Indicador calculado com dado que ninguém registra",
        "Um indicador usa dados que nenhuma ação registrada carrega.",
        "O número não pode ser calculado.",
        _REFAZER_DEV + "que a ação registre o dado, ou outro cálculo.", DEV),
    "leitura-sem-leitor": _x(
        "Dado lido num lugar que ninguém lê",
        "Uma ação registrada diz que é lida num canal que a plataforma não tem.",
        "O dado é guardado e nunca chega ao painel.",
        _REFAZER_DEV + "o leitor certo (a tabela da missão).", DEV),
    "sinal-ia-sem-ia-ao-estudante": _x(
        "Registro de IA numa missão em que a IA não fala com o aluno",
        "O PRD registra ações de uma IA que responde ao estudante, mas nesta missão a IA não fala com o aluno.",
        "O indicador mediria algo que não acontece.",
        _REFAZER_DEV + "que esses registros saiam.", DEV),
    "sinal-universal-divergente": _x(
        "Ação comum a todas as missões registrada com outro nome",
        "Uma ação comum a todas as missões aparece com outro nome.",
        "As missões deixam de ser comparáveis.",
        _REFAZER_DEV + "o nome do catálogo.", DEV),
    "tabela-evt-ausente": _x(
        "Tabela de ações ilegível",
        "A esteira não achou a tabela de ações registradas (com a coluna «Quando dispara») para conferir os "
        "indicadores.",
        "Os indicadores ficaram sem conferência.",
        "Confira a tabela no PRD. Se ela falta, peça **Refazer** de dev.", DEV),
    # ---------------------------------------------------------- registro das ações e o PRD
    "tabela-eventos": _x(
        "Falta a tabela de ações registradas",
        "A passagem ao dev não tem a tabela das ações da criança que a missão registra.",
        "Sem ela, os indicadores não têm de onde sair.",
        _REFAZER_DEV + "a tabela de ações.", DEV),
    "resultado-contexto": _x(
        "Registro de ações sem os campos que a plataforma guarda",
        "A tabela de ações não tem as colunas «resultado» e «contexto», os únicos dados extras que a plataforma "
        "guarda.",
        "O que a criança fez seria registrado sem o detalhe.",
        _REFAZER_DEV + "as duas colunas.", DEV),
    "campo-dados": _x(
        "Registro de ação com um campo que a plataforma descarta",
        "Ações da criança são registradas com um campo «dados», que a plataforma não tem e descarta sem avisar.",
        "Esses dados se perderiam.",
        _REFAZER_DEV + "os campos «resultado» e «contexto».", DEV),
    "tabela-leitura": _x(
        "Falta a tabela de onde o professor lê os dados",
        "Nenhuma tabela própria da missão foi nomeada; é dela que saem as medidas que o professor vê.",
        "A medida não existiria.",
        _REFAZER_DEV + "a tabela da missão.", DEV),
    "prefixo-tabela": _x(
        "Nome de tabela fora do padrão",
        "Uma tabela de dados tem o nome fora do padrão da plataforma (o código da missão, sem separador no meio).",
        "Os nomes deixam de bater entre as partes do sistema.",
        _REFAZER_DEV + "o nome no padrão.", DEV),
    "papeis": _x(
        "Papéis de usuário antigos",
        "O documento usa papéis de usuário que a plataforma não tem mais; ela tem seis (estudante, professor, três "
        "níveis de gestor e administrador).",
        "Permissão com papel errado não funciona.",
        _REFAZER_DEV + "os papéis da plataforma.", DEV),
    "rota-motor": _x(
        "Registro numa rota de outra missão",
        "O documento grava ações numa rota de uma missão antiga, em vez da rota do próprio módulo.",
        "Os registros iriam para o lugar errado.",
        _REFAZER_DEV + "a rota do módulo da missão.", DEV),
    "quota-env": _x(
        "Limite de uso de IA no lugar antigo",
        "O documento põe o limite de uso de IA numa configuração que não existe mais; hoje ele é por perfil.",
        "O limite não funcionaria.",
        _REFAZER_DEV + "o limite por perfil.", DEV),
    "enum-estado": _x(
        "Estado guardado num formato que a plataforma não usa",
        "O documento guarda o estado da missão num formato que a plataforma não adota.",
        "Quem programa seguiria um molde diferente do da plataforma.",
        _REFAZER_DEV + "o formato da plataforma.", DEV),
    "evento-sem-leitor": _x(
        "Ação registrada que ninguém lê",
        "O PRD diz que uma ação da criança é lida por um canal que a plataforma não tem.",
        "O dado é registrado e nunca chega ao painel.",
        _REFAZER_DEV + "o leitor certo (a tabela da missão).", DEV),
    "rf-sem-rastro": _x(
        "Requisito obrigatório sem tarefa",
        "Um requisito obrigatório do PRD não está ligado a nenhuma tarefa do plano de implementação.",
        "Ele pode ficar sem ser programado.",
        _REFAZER_DEV + "a tarefa do requisito.", DEV),
    "identificador-invalido": _x(
        "Nome inválido no código",
        "Um nome do PRD tem hífen, o que não vale no código.",
        "Quem programa inventaria outro nome, e as partes deixariam de se encontrar.",
        _REFAZER_DEV + "um nome válido.", DEV),
    "caminho-divergente": _x(
        "Missão com duas pastas",
        "O PRD declara mais de uma pasta para a mesma missão.",
        "Quem programa não sabe onde criar os arquivos.",
        _REFAZER_DEV + "uma pasta só.", DEV),
    "tipo-divergente": _x(
        "Mesmo dado com dois tipos",
        "Um campo do modelo de dados aparece com dois tipos diferentes (texto num lugar e número no outro, por "
        "exemplo).",
        "Quem programa não sabe qual é o certo.",
        _REFAZER_DEV + "um tipo só.", DEV),
    "tipo-divergente-de-spec": _x(
        "Campo com tipo diferente do da especificação",
        "Um campo de dados tem um tipo no PRD e outro na especificação, sem registro da troca.",
        "Quem programa não sabe qual vale.",
        _REFAZER_DEV + "o tipo da especificação, ou a troca registrada.", DEV),
    # ---------------------------------------------------------- PRD pronto para programar
    "zerar-com-delete": _x(
        "«Zerar» apaga dados",
        "O PRD faz o «zerar» da missão apagando os dados; na plataforma, zerar abre uma rodada nova e guarda a "
        "anterior.",
        "Apagar perde o histórico da turma.",
        _REFAZER_DEV + "o zerar da plataforma.", DEV),
    "contrato-sem-zod": _x(
        "Comunicação com o servidor descrita só em texto",
        "O PRD descreve o que cada endereço do servidor recebe e devolve em prosa, sem o formato exato dos dados.",
        "Quem programa escolhe os campos, e os erros só aparecem na sala.",
        _REFAZER_DEV + "o formato exato.", DEV),
    "contrato-frouxo": _x(
        "Formato de dados que aceita qualquer coisa",
        "O PRD descreve dados com um tipo que aceita qualquer coisa, sem os campos.",
        "Quem programa escolhe os campos, e os erros só aparecem na sala.",
        _REFAZER_DEV + "os campos declarados.", DEV),
    "ia-sem-prompt": _x(
        "Falta o texto do que se pede à IA",
        "O PRD lista chamadas de IA sem o texto do pedido (o prompt) de cada uma.",
        "Quem programa escreveria o pedido sozinho — e é ele que decide o que a criança vê.",
        _REFAZER_DEV + "o texto de cada pedido à IA.", DEV),
    "ia-saida-sem-schema": _x(
        "Resposta da IA sem formato definido",
        "O PRD não define o formato exato do que a IA devolve.",
        "A missão aceitaria qualquer resposta da IA, inclusive uma quebrada.",
        _REFAZER_DEV + "o formato da resposta.", DEV),
    "modelo-sem-ddl": _x(
        "Modelo de dados só em texto",
        "O PRD não traz a definição exata das tabelas de dados (tipos, obrigatoriedade, ligações).",
        "Quem programa decidiria sozinho como guardar os dados da missão.",
        _REFAZER_DEV + "a definição das tabelas.", DEV),
    "nivel-em-tabela-da-missao": _x(
        "Nível da criança guardado no lugar errado",
        "O PRD guarda o nível da criança numa tabela da própria missão; na plataforma ele fica no registro comum de "
        "evidências.",
        "O painel do professor não acharia o nível.",
        _REFAZER_DEV + "o registro comum.", DEV),
    "sem-force-rls": _x(
        "Falta a proteção de dados por escola",
        "O modelo de dados do PRD não traz o bloco que garante que cada escola só veja os próprios dados.",
        "Sem ele, dados de uma escola poderiam aparecer para outra.",
        _REFAZER_DEV + "o bloco de proteção.", DEV),
    "ficha-tipo-invalido": _x(
        "Regra de nível com tipo desconhecido",
        "Uma linha da ficha de evidência tem um tipo que não existe (só vale ação ou múltipla escolha).",
        "O servidor não saberia calcular o nível.",
        _REFAZER_DEV + "o tipo certo.", DEV),
    "ficha-sem-habilidade": _x(
        "Habilidade sem regra de nível no PRD",
        "A ficha de evidência do PRD não tem linha para uma habilidade da missão.",
        "O painel do professor ficaria sem o nível dessa habilidade.",
        _REFAZER_DEV + "a linha da habilidade.", DEV),
    "regra-em-proposta": _x(
        "Regra de nível ainda em proposta",
        "A regra que calcula o nível de uma habilidade ainda é proposta, à espera do PO.",
        "Sem a decisão do PO, o servidor não sabe calcular o nível.",
        "Decida a regra e registre no de acordo, ou peça que produto a feche.", PO),
    "regra-sem-coluna": _x(
        "Regra de nível que não lê nenhum dado guardado",
        "A condição da regra de nível não usa nenhum dado que o modelo de dados declara.",
        "O servidor não tem como aplicar a regra.",
        _REFAZER_DEV + "a regra sobre um dado guardado.", DEV),
    "regra-sem-predicado": _x(
        "Regra de nível em palavras soltas",
        "A condição da regra de nível cita um dado, mas não diz a comparação (por exemplo, «tentativas = 1»).",
        "O servidor não saberia quando a criança atingiu o nível.",
        _REFAZER_DEV + "a comparação.", DEV),
    "regra-chave-jsonb-ausente": _x(
        "Regra de nível lê um dado que não é guardado",
        "A regra de nível de uma habilidade lê um dado que o modelo de dados não declara.",
        "Dado que não é guardado nunca existe: o nível nunca seria calculado.",
        _REFAZER_DEV + "o dado no modelo de dados.", DEV),
    "chat-sem-intencoes": _x(
        "Conversa simulada sem as respostas previstas",
        "A missão tem um chat com um personagem simulado, e o banco de conteúdo não traz a tabela do que ele responde "
        "a cada mensagem.",
        "Quem programa inventaria o que o personagem diz.",
        _REFAZER_DEV + "a tabela de respostas do chat.", DEV),
    "intencao-sem-gatilho": _x(
        "Resposta do chat sem o que a dispara",
        "Uma resposta prevista do chat não diz que mensagem da criança a dispara.",
        "A resposta nunca apareceria.",
        _REFAZER_DEV + "o gatilho de cada resposta.", DEV),
    "intencao-sem-fallback": _x(
        "Chat sem resposta para mensagem inesperada",
        "A tabela do chat não diz o que o personagem responde quando a mensagem da criança não casa com nada previsto.",
        "A criança pode ficar sem resposta.",
        _REFAZER_DEV + "a resposta padrão.", DEV),
    "prd-sem-intencoes": _x(
        "PRD não diz onde ficam as respostas do chat",
        "O PRD não aponta a tabela de respostas do chat nem onde a mensagem da criança é interpretada.",
        "Quem programa não sabe de onde tirar as respostas.",
        _REFAZER_DEV + "a referência à tabela do chat.", DEV),
    "tabela-do-handoff-perdida": _x(
        "Tabela da passagem ao dev que sumiu do PRD",
        "Tabelas de dados declaradas na passagem ao dev não estão no PRD, nem registradas como divergência.",
        "Quem programa não sabe se a tabela existe.",
        _REFAZER_DEV + "as tabelas, ou a troca registrada.", DEV),
    "evento-do-handoff-perdido": _x(
        "Ação registrada na passagem que sumiu do PRD",
        "Ações da criança que a passagem ao dev registra não estão no PRD, nem como divergência.",
        "O dado dessas ações não seria guardado, e os indicadores ficam sem ele.",
        _REFAZER_DEV + "as ações, ou a troca registrada.", DEV),
    "divergencia-do-handoff-registrada": _x(
        "O PRD mudou algo da passagem ao dev e registrou",
        "O PRD tira itens da passagem ao dev e só registra a troca na lista de divergências.",
        "A troca pode ter motivo, mas alguém precisa conferir.",
        "Confira se a troca tem motivo antes de liberar.", DEV),
    # ---------------------------------------------------------- a missão na plataforma
    "id-nao-derivado": _x(
        "Código da missão fora da regra da plataforma",
        "O código da missão no PRD não é o que a plataforma deriva da série e da unidade.",
        "A missão seria registrada com outro código, e a pasta e o endereço não bateriam.",
        _REFAZER_DEV + "o código derivado.", DEV),
    "manifesto-invalido": _x(
        "Ficha técnica que a plataforma recusaria",
        "A ficha técnica da missão não passa na conferência que a plataforma faz ao publicar.",
        "A missão não seria publicada.",
        _REFAZER_DEV + "a ficha corrigida.", DEV),
    "manifesto-chave-inexistente": _x(
        "Ficha técnica com campos desconhecidos",
        "A ficha técnica da missão traz campos que a plataforma não reconhece.",
        "A publicação da missão pode falhar.",
        _REFAZER_DEV + "só os campos da plataforma.", DEV),
    "manifesto-capability": _x(
        "Recurso que a plataforma não oferece",
        "A ficha técnica pede um recurso que a plataforma não tem.",
        "Até a plataforma oferecer, essa parte da missão não funciona.",
        "Combine com o time de plataforma, ou peça, com **Refazer** de dev, que o recurso saia.", DEV),
    "manifesto-permissao": _x(
        "Permissão que a plataforma não concede",
        "A ficha técnica pede uma permissão do navegador (câmera, microfone…) que a plataforma não concede.",
        "Essa parte da missão não funcionaria.",
        "Combine com o time de plataforma, ou peça, com **Refazer** de dev, que a permissão saia.", DEV),
    "ponte-inexistente": _x(
        "Pacote de componentes que não existe",
        "O PRD usa um pacote de componentes do design system que a plataforma não tem.",
        "O código não funcionaria.",
        _REFAZER_DEV + "um dos pacotes existentes (estão no detalhe).", DEV),
    # ---------------------------------------------------------- banco de conteúdo
    "conteudo-ausente": _x(
        "Textos da missão que faltam no banco de conteúdo",
        "Itens previstos não têm o texto inteiro no banco de conteúdo (notícias, posts, falas).",
        "A criança veria a tela vazia.",
        _REFAZER_DEV + "os textos que faltam.", DEV),
    "fala-ausente": _x(
        "Fala do personagem de IA faltando",
        "Em alguns momentos em que o personagem de IA deveria falar, o banco de conteúdo não tem a fala.",
        "A criança ficaria sem a resposta prevista.",
        _REFAZER_DEV + "as falas que faltam.", DEV),
    "status-humano": _x(
        "Texto marcado como aprovado pelo próprio agente",
        "O banco de conteúdo marca um texto como homologado ou aprovado; quem escreve o banco só pode marcar "
        "«escrito».",
        "Aprovar é da curadoria humana: a marca esconderia que ninguém revisou.",
        "Peça **Refazer** de dev.", DEV),
    # ---------------------------------------------------------- protótipo e pedagógico (design)
    "prototipo-nao-abre": _x(
        "O protótipo não abre no navegador",
        "O arquivo do protótipo não é uma página que o navegador abre.",
        "Ninguém consegue ver nem conferir as telas.",
        "Peça **Refazer** de design. Se voltar a acontecer, avise o time técnico.", DESIGN),
    "quadros-todos-visiveis": _x(
        "Todas as telas aparecem empilhadas",
        "No protótipo, as telas que deviam aparecer uma de cada vez ficam visíveis ao mesmo tempo.",
        "A navegação parece não funcionar, e o QA confere a coisa errada.",
        _REFAZER_DESIGN, DESIGN),
    "sem-id-de-tela": _x(
        "Telas do protótipo sem o código de tela",
        "Nenhuma tela do protótipo tem o código de tela (como E3-ALU-01).",
        "Sem o código, não dá para conferir se cada tela prevista foi construída.",
        _REFAZER_DESIGN, DESIGN),
    "telas-ausentes": _x(
        "Telas previstas que não estão no protótipo",
        "Algumas telas da lista de telas da missão não aparecem no protótipo.",
        "O QA confere o que está na tela, não o que o relatório promete.",
        "Peça, com **Refazer** de design, as telas que faltam (estão no trecho).", DESIGN),
    "telas-nao-declaradas": _x(
        "Tela no protótipo que a lista de telas não tem",
        "O protótipo tem uma tela que a lista de telas da missão não declara.",
        "Ou a lista está desatualizada, ou o protótipo inventou uma tela.",
        "Confira a tela. Se ela não devia existir, peça **Refazer** de design.", DESIGN),
    "marcador-de-rascunho": _x(
        "Marca de rascunho no protótipo",
        "O protótipo ainda tem marcas de rascunho (texto provisório ou lembretes).",
        "O QA confere o que a criança veria: rascunho na tela não é tela pronta.",
        _REFAZER_DESIGN, DESIGN),
    "afirmacao-inventario": _x(
        "O QA conta outro número de telas",
        "O relatório de QA afirma um número de telas diferente do que a lista de telas declara.",
        "O relatório pode estar conferindo outra coisa.",
        _REFAZER_DESIGN, DESIGN),
    "bloco-do-contrato-ausente": _x(
        "Parte do aprovado sumiu do pedagógico",
        "Partes que a esteira copia do one-pager aprovado não estão no one-pager pedagógico.",
        "O que o PO aprovou some do documento de sala de aula.",
        _REFAZER_DESIGN, DESIGN),
    "bloco-do-contrato-alterado": _x(
        "Parte copiada do aprovado mudou no pedagógico",
        "Partes que a esteira copia do one-pager aprovado aparecem diferentes no one-pager pedagógico.",
        "O texto aprovado pelo PO não muda no design.",
        "Peça **Refazer** de design. Se a mudança é sua, peça-a a produto, com **Refazer** de produto.", DESIGN),
    "texto-chave-proposta": _x(
        "O design propôs outra redação para um texto aprovado",
        "O design propôs outra redação para textos que o PO aprovou palavra por palavra; vale o aprovado até o PO "
        "decidir.",
        "Texto aprovado só muda pelo PO.",
        "Leia as propostas. Se quer alguma, peça a troca com **Refazer** de produto; se não, siga — vale o aprovado.",
        PO),
    "texto-chave-id-desconhecido": _x(
        "Texto das telas que o aprovado não tem mais",
        "Os textos das telas citam textos-chave que o one-pager aprovado não tem (mais).",
        "O texto pode ter saído num refazer de produto.",
        "Confira a linha. Se o texto saiu do aprovado, peça **Refazer** de design.", DESIGN),
    # ---------------------------------------------------------- mesmos nomes em todos os documentos
    "variante-proibida": _x(
        "Nome proibido para um personagem ou elemento",
        "Um documento usa uma forma de nome que a lista oficial de nomes proíbe; o nome oficial está no trecho.",
        "Dois nomes para a mesma coisa confundem a criança e quem programa.",
        _REFAZER_DA_ETAPA + "que o documento use o nome oficial.", None),
    "idade-divergente": _x(
        "Idade de personagem diferente da oficial",
        "Um documento dá a um personagem uma idade diferente da que a lista oficial fixa.",
        "A criança e o professor veriam dois dados para o mesmo personagem.",
        "Peça que o documento use a idade oficial (está no trecho). Em geral é ajuste simples.", None),
    "papel-divergente": _x(
        "Personagem com papel diferente do oficial",
        "Um personagem aparece coordenando ou respondendo por algo que não é o papel dele na lista oficial.",
        "A história fica incoerente entre os documentos.",
        "Peça que o documento use o papel oficial (está no trecho).", None),
    "numero-divergente": _x(
        "Número diferente do oficial",
        "Um documento usa um número diferente do que a lista oficial fixa (por exemplo, a quantidade de rodadas).",
        "Quem desenha e quem programa ficam sem saber qual vale.",
        "Peça que o documento use o número oficial (está no trecho).", None),
    "arquivo-divergente": _x(
        "Nome de arquivo diferente entre documentos",
        "Um documento cita um arquivo com um nome diferente do que foi de fato gerado.",
        "Quem procura o arquivo não o acha.",
        "Peça que o documento use o nome certo (está no trecho). Em geral é ajuste simples.", None),
    "glossario-vazio": _x(
        "Lista oficial de nomes vazia",
        "A especificação tem o título da lista oficial de nomes, mas nenhuma tabela legível dentro dele.",
        "Sem a lista, cada documento batiza as coisas de um jeito.",
        _REFAZER_PRODUTO, PO),
}.items():
    # entrada que já existe vence: estas cobrem só o que faltava
    CATALOGO.setdefault(_codigo_novo, _exp_nova)

#: Falhas da execução, não da missão: o texto é o mesmo para todas.
_FALHA_DA_ESTEIRA = _x(
    "Falha da esteira nesta execução",
    "Um passo da esteira não produziu o que devia (veio vazio, ilegível ou sem veredito).",
    "A verificação desse ponto ficou incompleta: não é um problema da missão, mas o ponto ficou sem conferência.",
    "Peça **Refazer** da etapa. Se voltar a acontecer, avise o time técnico.", ESTEIRA)
for _c in ("envelope-ilegivel", "juiz-sem-voto", "juiz-sem-veredito", "notas-ilegiveis", "insumo-ausente",
           "catalogo-indisponivel", "indice-ilegivel", "indice-cego", "prd-vazio", "one-pager-vazio", "copy-vazia",
           "nucleo-vazio", "banco-vazio", "fontes-vazias", "fonte-vazia", "veredito-incoerente",
           "voto-sem-achado-verificavel", "ticket-sem-rota", "dimensao-ausente", "gabarito-desconhecido",
           "conceito-desconhecido", "etapa-invalida", "acao-vazia", "tarefa-sem-conteudo", "stitch-sem-projeto",
           "stitch-recusou", "stitch-incompleto", "spec-vazia", "prototipo-vazio"):
    CATALOGO.setdefault(_c, _FALHA_DA_ESTEIRA)

#: Sinônimos: o rastro de lacunas grava o tipo do marcador; o diagnóstico, o dono.
CATALOGO.setdefault("pendencia-plataforma", _x(
    "Pendência da plataforma",
    "A missão precisa de algo que a plataforma ainda não tem; o texto marcou isso como pendência com dono.",
    "Até a plataforma entregar, essa parte da missão não funciona.",
    "Combine com o time de plataforma quem resolve e quando. Não trava a etapa.", DEV))
CATALOGO.setdefault("plataforma", CATALOGO["pendencia-plataforma"])

# ------------------------------------------------------------------ quando o achado impede seguir
#: O mesmo código sai 🟡 numa situação e 🔴 noutra: `letramento` no EM e no EF, `secao_ds` pendência de plataforma ou
#: seção legada, `decisao-atribuida-ao-po` com e sem registro do PO, `numero-sem-origem` no one-pager e no PRD, a escolha
#: do PO com ESTEIRA_ESTRITA. Com 🔴 o «De acordo» não aparece (`pipeline.passagem.acoes_possiveis`): a explicação não
#: manda registrar nele nem diz que não trava. Revisão do PR #82 (25/10/2026): o PO via «🔴 Impede seguir» e, logo
#: abaixo, «Não trava a etapa» — justamente no gate da BNCC, o único recorte bloqueante.
_SE_BLOQUEIO: Dict[str, Explicacao] = {
    "letramento": _x(
        "Falta habilidade de letramento digital da série",
        "Nenhuma das habilidades da BNCC declaradas é de letramento digital (o eixo Cultura Digital) e do ano da "
        "missão.",
        "No Ensino Fundamental, a missão precisa de ao menos uma habilidade de letramento digital do ano: é o recorte "
        "da BNCC que impede seguir quando falta.",
        "Use **Refazer** de produto pedindo uma habilidade de Cultura Digital do ano que descreva o que a criança faz. "
        "Se nenhuma descreve, o time decide mudar a série ou a âncora curricular — diga a decisão no pedido.", PO),
    "secao_ds": _x(
        "O ambiente da missão não pode seguir como está",
        "A seção do design system em que a missão acontece (o app simulado ou o mini-jogo) não pode ficar como a "
        "especificação diz: é uma seção antiga, que imita app de terceiro; repete uma coleção que o design system já "
        "tem; contraria o briefing; ou é um ambiente novo que o PO não escolheu ou recusou. O motivo exato está no "
        "trecho abaixo.",
        "O ambiente é decisão de produto e define o que o design desenha e o que a plataforma precisa ter: com o "
        "ambiente errado, a missão inteira vai para o lugar errado.",
        "Leia o motivo e use **Refazer** de produto com a seção certa. Se a escolha é sua (manter a seção antiga, por "
        "exemplo), diga isso no pedido de **Refazer**, para que a especificação a registre como decisão sua.", PO),
    "decisao-atribuida-ao-po": _x(
        "Decisão escrita como se fosse do PO",
        "O texto diz que o PO decidiu algo, e a sessão não tem nenhum pedido nem parecer do PO que diga isso.",
        "Se o PO não decidiu, a missão segue com uma escolha do agente disfarçada de decisão do PO, e ninguém volta "
        "para conferir.",
        # `decisoes.ha_registro_do_po`: o pedido de refazer é registro do PO, e com ele o achado cai para ⚠️
        "Leia cada frase abaixo. Se a decisão é sua, use **Refazer** dizendo isso: o pedido fica registrado e o ponto "
        "deixa de travar. Se não é, use **Refazer** pedindo que ela vire proposta para você validar.", PO),
    "numero-sem-origem": _x(
        "Número sem fonte",
        "O documento apresenta números (tempos, quantidades, limites) como decididos, sem que venham do material "
        "aprovado nem de uma decisão do PO.",
        "Número que ninguém decidiu vira regra da missão sem que o PO perceba.",
        "Confira cada número abaixo. Este documento só usa números que produto decidiu: peça, com **Refazer** desta "
        "etapa, que o número seja copiado do aprovado, saia ou vire proposta para o PO. Se o número deve valer, o "
        "pedido é a produto.", None),
    "ambiente-ausente-na-spec": _x(
        "Falta escolher o app simulado",
        "A especificação de produto não diz qual app a missão imita (Instagram, WhatsApp…) nem se é mini-jogo.",
        "Sem essa escolha, o design decidiria sozinho a cara da missão.",
        "Devolva a missão a produto dizendo qual app ela imita, ou se é mini-jogo: a escolha é sua e entra na "
        "especificação.", PO),
    "guarda-afrouxada": _x(
        "Caminho entre telas mais solto do que a regra",
        "Uma passagem entre telas deixa a criança avançar em mais situações do que a especificação permite.",
        "A criança pode pular uma etapa que a missão precisa.",
        "Peça, com **Refazer** de design, que a passagem siga a regra da especificação. Se você quer mudar a regra, o "
        "pedido é a produto.", PO),
    "guarda-exige-acerto": _x(
        "Passagem que só aceita a resposta certa",
        "Uma passagem entre telas só deixa a criança seguir se acertar, e a especificação não pede acerto ali.",
        "A missão deixa de medir quem erra — e o erro é parte da descoberta.",
        "Peça, com **Refazer** de design, que a criança possa seguir mesmo errando, como a especificação pede. Se você "
        "quer a trava, o pedido é a produto.", PO),
}

#: A família EM13 que conta como letramento pela leitura **proposta** do EM (`tools/bncc.py`, sempre 🟡). Até a revisão do
#: PR #82 ela usava a entrada `letramento`, que é outro achado.
_LETRAMENTO_PROPOSTO_EM = _x(
    "Habilidade do Ensino Médio lida como letramento digital",
    "A habilidade conta como letramento digital por uma leitura proposta do Ensino Médio, que não tem eixo oficial.",
    "A classificação pode não ser a que a pedagogia adota.",
    "Valide com a pedagogia e registre no de acordo. Não trava a etapa.", PO)

#: A ficha técnica (bloco 0 da spec, `rastro.validar_manifesto`) grava o nome do campo como código do achado: `produto`
#: ali é o campo «produto» da ficha, não uma pendência de produto.
_CAMPOS_DA_FICHA = {
    "id": "o código da missão", "series": "a série (ano) da missão", "unidade": "a unidade (bimestre)",
    "viewport": "o tamanho de tela", "publico": "o público (quem usa a missão)",
    "produto": "o produto da plataforma em que a missão entra", "liberacao": "a regra de liberação da missão",
    "capabilities": "os recursos da plataforma que a missão usa",
    "permissoes": "as permissões do navegador (câmera, microfone…)",
    "classe_ambiente": "o tipo de ambiente (app simulado ou mini-jogo)",
    "secoes_ds_extras": "as seções extras do design system",
}


def _campo_da_ficha(campo: str) -> Explicacao:
    nome = _CAMPOS_DA_FICHA[campo]
    return _x(f"Ficha técnica da missão: {nome}",
              f"A ficha técnica que registra a missão na plataforma (o começo da especificação) tem um problema em "
              f"{nome}. O motivo está abaixo.",
              "A plataforma usa a ficha para publicar e mostrar a missão: campo errado ou faltando impede publicar, ou "
              "leva a missão para o lugar errado.",
              "Leia o motivo e peça a correção com **Refazer** da etapa que escreveu a ficha (em geral, produto).",
              None, caso=True)


#: Frases que só valem quando o ponto não trava. Com 🔴, saem; a menção ao «De acordo» vira o caminho que existe.
_SO_SEM_TRAVA = (
    (re.compile(r"\s*Não trava a etapa\.?"), ""),
    (re.compile(r"\s*(?:,|—)?\s*ou siga com ele registrado"), ""),
    (re.compile(r"; senão, siga e registre no de acordo"), ""),
    (re.compile(r"; se não, siga e registre por quê(?: no comentário)?"),
     "; se não concorda, fale com o administrador: só ele libera com exceção, que fica registrada"),
)
#: O que dizer no lugar de «registre no de acordo» quando o ponto impede seguir.
NO_VERMELHO = ("Enquanto este ponto impedir seguir, o botão «De acordo» não aparece: o caminho é **Refazer** (o seu "
               "pedido fica registrado) ou a liberação com exceção pelo administrador.")


def o_que_fazer(explicacao: Explicacao, sev: str) -> str:
    """O «O que fazer» coerente com a severidade: com 🔴, sem «Não trava a etapa» e sem mandar registrar no de acordo,
    que não aparece. As entradas que mudam de sentido com o 🔴 têm texto próprio em `_SE_BLOQUEIO`; isto é a rede."""
    texto = explicacao.o_que_fazer
    if sev != BLOQUEIO:
        return texto
    for regra, troca in _SO_SEM_TRAVA:
        texto = regra.sub(troca, texto)
    frases = [f for f in re.split(r"(?<=[.!?])\s+", texto.strip()) if f.strip()]
    ficam = [f for f in frases if "de acordo" not in f]
    if len(ficam) < len(frases):
        ficam.append(NO_VERMELHO)
    return " ".join(ficam) or NO_VERMELHO


# ------------------------------------------------------------------ o que o padrão do juiz de adequação quer dizer
#: O juiz de adequação escreve o código que quiser (`demanda_cognitiva`, `2`, `E3`), mas o `padrao` é de uma lista
#: fechada (`prompts/produto/…adequacao…`): é por ele que a explicação sai.
PADROES: Dict[str, Explicacao] = {
    "tempo-insuficiente-etapa": _x(
        "Pouco tempo para a etapa",
        "O revisor achou que a criança da série não consegue fazer o que a etapa pede no tempo previsto.",
        "Etapa apertada vira pressa — e a descoberta se perde.",
        "Leia o ponto. Ajuste o tempo ou a tarefa com **Refazer** de produto, ou siga com ele registrado.", PO, True),
    "repertorio-nao-declarado": _x(
        "A missão supõe algo que a criança pode não saber",
        "O revisor achou que a missão conta com um conhecimento que a criança da série pode não ter.",
        "A criança trava num conceito que ninguém apresentou.",
        "Leia o ponto. Peça, com **Refazer** de produto, que a missão apresente o conceito — ou siga com ele "
        "registrado.", PO, True),
    "estrangeirismo-na-interface": _x(
        "Palavra em inglês sem necessidade",
        "O revisor achou palavras em inglês na tela que a criança pode não entender.",
        "Palavra desconhecida tira a atenção do que importa.",
        "Leia o ponto. Peça a troca por português com **Refazer**, ou siga com ele registrado.", PO, True),
    "termo-sem-ancoragem": _x(
        "Palavra sem explicação",
        "O revisor achou um termo que aparece sem ser apresentado à criança.",
        "A criança pode não entender a tela.",
        "Leia o ponto. Peça a explicação ou a troca com **Refazer**, ou siga com ele registrado.", PO, True),
    "habilidade-decorativa": _x(
        "Habilidade listada e não praticada",
        "O revisor achou habilidades declaradas que a missão não exercita nem mede.",
        "Promessa vazia para a escola.",
        "Leia o ponto. Tire a habilidade ou acrescente onde ela é praticada, com **Refazer** de produto.", PO, True),
    "verbo-desalinhado": _x(
        "Habilidade que não bate com a tarefa",
        "O revisor achou que a ação da criança não corresponde ao verbo da habilidade (por exemplo, a habilidade pede "
        "«criar» e a tarefa é «escolher»).",
        "A missão mede outra coisa, não a habilidade declarada.",
        "Leia o ponto e decida se troca a habilidade ou a tarefa, com **Refazer** de produto.", PO, True),
    "sem-artefato-observavel": _x(
        "Algo medido que a esteira não consegue ver",
        "O revisor achou uma regra de nível que depende de algo que acontece fora da tela (por exemplo, a fala na "
        "sala).",
        "O sistema não tem como registrar o que não acontece na tela.",
        "Leia o ponto. Ajuste a regra com **Refazer** de produto, ou siga com ele registrado.", PO, True),
}

# ------------------------------------------------------------------ o que cada verificador confere
#: `chave do status: (nome simples, o que ele confere, quem resolve por padrão, o juiz escreve o código que quiser)`.
#: Quando o juiz escreve o código livre (critério numerado, id do achado), a explicação é a do verificador e o texto do
#: juiz é o caso.
GATES: Dict[str, Tuple[str, str, str, bool]] = {
    "catalogo_indice_status": ("Lista de missões já geradas", "se a lista usada para comparar esta missão com as "
                               "anteriores está em dia", ESTEIRA, False),
    "catalogo_status": ("Missões repetidas", "se esta missão repete o código ou a descoberta de outra já gerada",
                        PO, False),
    "micro_gate_status": ("Revisão rápida do núcleo", "se o núcleo da missão (a história e a descoberta central) "
                          "está completo antes de seguir", PO, True),
    "profundidade_status": ("Profundidade pedagógica", "se a missão leva a criança a uma descoberta de verdade, e "
                            "não só a seguir passos", PO, True),
    "mecanica_status": ("Conta da virada (núcleo)", "se o núcleo mostra a conta que faz a criança perceber a virada",
                        PO, False),
    "mecanica_one_pager_status": ("Conta da virada (one-pager)", "se o one-pager mostra a conta que faz a criança "
                                  "perceber a virada", PO, False),
    "fidelidade_nucleo_status": ("Pedidos do PO no núcleo", "se cada pedido do PO foi aplicado no núcleo da missão",
                                 PO, False),
    "fidelidade_status": ("Pedidos do PO e o briefing", "se cada pedido do PO e o briefing foram respeitados nos "
                          "documentos de produto", PO, False),
    "fidelidade_design_status": ("Pedidos do PO no design", "se o pedido de refazer o design foi aplicado", DESIGN,
                                 False),
    "fidelidade_dev_status": ("Pedidos do PO no dev", "se o pedido de refazer o dev foi aplicado", DEV, False),
    "evidencia_one_pager_status": ("Como a missão mede cada habilidade (one-pager)", "se o one-pager diz, para cada "
                                   "habilidade, de qual ação da criança sai o nível dela", PO, False),
    "comite_canal_a_status": ("Comitê pedagógico — ações em tela", "se as ações da criança na tela medem as "
                              "habilidades declaradas", PO, True),
    "comite_canal_b_status": ("Comitê pedagógico — perguntas do fim", "se as perguntas de múltipla escolha do fim "
                              "medem o que dizem medir", PO, True),
    "comite_final_status": ("Comitê final", "uma última leitura de pedagogia, qualidade e fidelidade ao app "
                            "simulado", PO, True),
    "brief_escopo_status": ("Resumo de escopo", "se o resumo de escopo foi separado do one-pager", ESTEIRA, False),
    "gate_estrutural_status": ("Revisão estrutural do one-pager", "se o one-pager tem todas as partes que a "
                               "plataforma e a pedagogia exigem", PO, True),
    "avaliacao_status": ("Avaliação pedagógica", "se as habilidades, a avaliação e os tempos da aula fazem sentido",
                         PO, True),
    "experiencia_status": ("Experiência do estudante", "se a criança da série consegue ler, entender e usar a missão "
                           "no tempo da aula", PO, True),
    "adequacao_status": ("Adequação à série", "se a linguagem, a leitura e o que a missão supõe que a criança sabe "
                         "cabem na série", PO, True),
    "gate_final_status": ("Revisão final de produto", "o conjunto do one-pager antes de ir para o design", PO, True),
    "bncc_status": ("Habilidades da BNCC", "se os códigos da BNCC existem, são da série e foram citados com o texto "
                    "oficial", PO, False),
    "completude_status": ("Especificação completa", "se a especificação da missão tem todas as partes", ESTEIRA,
                          False),
    "manifesto_status": ("Ficha técnica da missão", "se a ficha que registra a missão na plataforma está certa "
                         "(seção do design system, componentes)", DEV, False),
    "evidencia_status": ("Matriz de evidência", "se cada habilidade tem a ação que a mede e a regra do nível", PO,
                         False),
    "perguntas_status": ("Perguntas de produto", "se a especificação traz as perguntas que o time quer responder com "
                         "os dados da missão", PO, False),
    "juiz_perguntas_status": ("Revisor das perguntas de produto", "se cada pergunta de produto leva a uma decisão e é "
                              "medida pela ação certa", PO, True),
    "rastro_spec_status": ("Pendências abertas na especificação", "os pontos marcados como em aberto, proposta ou "
                           "número a definir na especificação", PO, False),
    "conteudo_aprovado_spec_status": ("Especificação × one-pager aprovado", "se a especificação traz os textos "
                                      "aprovados pelo PO sem reescrever", PO, False),
    "contrato_produto_status": ("Limites da plataforma e origem dos números", "se o one-pager promete só o que a "
                                "plataforma faz e se cada número tem fonte", PO, False),
    "banca_produto_status": ("Banca de produto", "uma revisão independente do conjunto de produto, no fim da etapa",
                             PO, True),
    "conteudo_aprovado_resumido_status": ("One-pager resumido × aprovado", "se o one-pager resumido traz os textos "
                                          "aprovados sem reescrever", PO, False),
    "one_pager_po_status": ("One-pager do PO preservado", "se o que o PO escreveu no one-pager original continua lá",
                            PO, False),
    "lacunas_status": ("Fechamento de lacunas (design)", "se o design completou o que faltava na especificação sem "
                       "apagar o que já estava", DESIGN, False),
    "ambiente_status": ("App simulado", "se o design descreveu o app simulado sem mexer no que é decisão de produto",
                        DESIGN, False),
    "conteudo_aprovado_spec_design_status": ("Especificação × one-pager aprovado (design)", "se os textos aprovados "
                                             "continuam iguais na especificação depois do design", DESIGN, False),
    "prototipo_lint_status": ("Arquivo do protótipo", "se o protótipo usa os componentes do design system e marca "
                              "cada tela", DESIGN, False),
    "consistencia_status": ("Mesmos nomes em todos os documentos", "se botões, personagens, números e textos têm o "
                            "mesmo nome em todos os documentos", DESIGN, False),
    "stitch_status": ("Telas no Stitch", "se cada tela do inventário foi gerada no Stitch", DESIGN, False),
    "cobertura_telas_status": ("Todas as telas desenhadas", "se cada tela e cada estado do inventário aparece no "
                               "protótipo", DESIGN, False),
    "textos_chave_status": ("Textos aprovados nas telas", "se os textos que o PO aprovou palavra por palavra chegaram "
                            "iguais aos textos das telas", DESIGN, False),
    "arestas_status": ("Caminhos entre as telas", "se o fluxo entre as telas segue as regras da especificação "
                       "(quando a criança pode avançar)", DESIGN, False),
    "qa_afirmacoes_status": ("Conferência do relatório de QA", "se o que o QA do design afirma (telas, arquivos) é "
                             "verdade", DESIGN, False),
    "design_status": ("QA do design", "a revisão final dos entregáveis de design", DESIGN, True),
    "rastro_design_status": ("Pendências abertas no design", "os pontos marcados como em aberto ou proposta nos "
                             "documentos de design", DESIGN, False),
    "banca_design_status": ("Banca de design", "uma revisão independente do design, no fim da etapa", DESIGN, True),
    "miro_status": ("Diagramas no Miro", "se o quadro do Miro tem os diagramas da missão", ESTEIRA, False),
    "coerencia_pedagogico_status": ("One-pager pedagógico × aprovado", "se o one-pager pedagógico conta a missão "
                                    "como o PO aprovou", DESIGN, True),
    "conteudo_aprovado_pedagogico_status": ("Textos aprovados no pedagógico", "se o one-pager pedagógico traz os "
                                            "textos aprovados sem reescrever", DESIGN, False),
    "montagem_pedagogico_status": ("Pedagógico só junta o que foi decidido", "se o one-pager pedagógico não inventa "
                                   "números nem reescreve textos aprovados", DESIGN, False),
    "pedagogico_dev_status": ("Pedagógico aprovado, no dev", "se o dev manteve o one-pager pedagógico aprovado", DEV,
                              False),
    "rastreabilidade_status": ("O aprovado chegou ao design", "se cada texto, estado e tela que produto aprovou "
                               "chegou aos documentos de design", DESIGN, False),
    "rastreabilidade_dev_status": ("O aprovado chegou ao dev", "se cada texto, estado e tela que produto aprovou "
                                   "chegou aos documentos de dev", DEV, False),
    "banca_entrada_status": ("Banca de entrada do dev", "uma segunda leitura de produto e design antes do dev "
                             "começar", DEV, True),
    "conteudo_status": ("Banco de conteúdo", "se os textos que a criança lê (notícias, posts, falas) estão completos",
                        DEV, False),
    "telemetria_status": ("Registro das ações da criança", "se o documento de passagem ao dev registra as ações do "
                          "jeito que a plataforma aceita", DEV, False),
    "montagem_handoff_status": ("Passagem ao dev só junta o que foi decidido", "se o documento de passagem ao dev "
                                "não inventa números, metas ou estados", DEV, False),
    "rastro_lacunas_status": ("Pendências abertas (todas as etapas)", "os pontos ainda em aberto em todos os "
                              "documentos", DEV, False),
    "dev_status": ("Banca de dev", "uma revisão independente do dev, em cinco dimensões", DEV, True),
    "prd_status": ("PRD completo", "se o PRD (o documento que o dev usa para programar) está completo e coerente com "
                   "a plataforma", DEV, False),
    "kpis_status": ("Indicadores × ações × telas", "se cada indicador é calculado com a ação certa, na tela certa",
                    DEV, False),
    "conteudo_aprovado_prd_status": ("PRD × one-pager aprovado", "se o PRD traz o que o PO aprovou sem reescrever",
                                     DEV, False),
    "montagem_prd_status": ("PRD só junta o que foi decidido", "se o PRD não inventa números, metas ou estados", DEV,
                            False),
    "coerencia_prd_status": ("PRD × one-pager aprovado", "se o PRD conta a missão como o PO aprovou", DEV, True),
    "diagnostico_status": ("Diagnóstico da execução", "o resumo de tudo o que ficou pendente na execução", ESTEIRA,
                           True),
}

#: O agente que escreveu o trecho → quem resolve. Usado quando a entrada do catálogo não fixa o dono.
_DONO_DO_AGENTE = (
    (re.compile(r"humano|editorial|\bpo\b|produto|spec|gate-estrutural|secoes-apoio|one.?pager|nucleo|bncc", re.I), PO),
    (re.compile(r"jornada|fluxo|copy|prototipo|protótipo|ambiente|lacunas|design|stitch|caa|qa", re.I), DESIGN),
    (re.compile(r"handoff|prd|banco|dev|plataforma|kpi|telemetria", re.I), DEV),
)
_ETAPA_PARA_QUEM = {"produto": PO, "design": DESIGN, "dev": DEV}


# ------------------------------------------------------------------ famílias de código
_RE_BNCC = re.compile(r"^E[FIM]\d{2}[A-Z]{2}\d{2,3}$")
_RE_CRITERIO = re.compile(r"^\d+(\.\d+)*[a-z]?(\([a-z0-9]+\))?$", re.I)
_RE_ID_DE_JUIZ = re.compile(r"^[A-Z]{1,4}\d{0,2}[a-z]?(-[A-Z0-9]+)*$")
_RE_PERDIDO = re.compile(r"^perdido-([a-z_]+)-([a-z_]+)$")
_RE_PROFUNDIDADE = re.compile(r"^P\d+(-|$)")

_PERDIDO_O_QUE = {
    "texto_tela": "textos de tela aprovados", "canal_b": "perguntas do fim aprovadas (Canal B)",
    "podcast": "falas do podcast aprovado", "roteiro": "perguntas do debate aprovadas",
    "estado": "estados da missão (os momentos em que ela pode estar)", "proposta": "propostas a validar com o PO",
    "tela": "telas do inventário", "parametro": "números a definir pelo PO", "habilidade": "habilidades",
}
_PERDIDO_ONDE = {
    "copy": ("aos textos das telas", "nos textos das telas", DESIGN),
    "prototipo": ("ao protótipo", "no protótipo", DESIGN),
    "fluxo": ("ao fluxo das telas", "no fluxo das telas", DESIGN),
    "stitch": ("às telas do Stitch", "nas telas do Stitch", DESIGN),
    "jornada": ("à jornada", "na jornada", DESIGN),
    "pedagogico": ("ao one-pager pedagógico", "no one-pager pedagógico", DESIGN),
    "prd": ("ao PRD (o documento do dev)", "no PRD", DEV),
    "banco": ("ao banco de conteúdo", "no banco de conteúdo", DEV),
    "handoff": ("à passagem ao dev", "na passagem ao dev", DEV),
    "spec": ("à especificação", "na especificação", PO),
}


def _perdido(m: "re.Match[str]") -> Explicacao:
    o_que = _PERDIDO_O_QUE.get(m.group(1), m.group(1).replace("_", " "))
    chegou, aparece, quem = _PERDIDO_ONDE.get(m.group(2), (f"a «{m.group(2)}»", f"em «{m.group(2)}»", None))
    return _x(f"Nem tudo o que foi aprovado chegou {chegou}",
              f"Alguns itens ({o_que}) não aparecem {aparece}.",
              "O que produto aprovou se perde no caminho, e a missão sai diferente do aprovado.",
              "Confira os itens listados abaixo. Peça, com **Refazer** da etapa, que eles entrem como foram aprovados.",
              quem)


def _do_gate(gate: str) -> Optional[Explicacao]:
    """A explicação pelo verificador: o juiz escreve o código que quiser, e o texto dele é o caso."""
    if gate not in GATES:
        return None
    nome, confere, quem, _ = GATES[gate]
    return _x(f"{nome}: ponto apontado pelo revisor",
              f"O revisor automático «{nome}», que confere {confere}, apontou o ponto abaixo.",
              "É a leitura de um revisor: pode ser um problema real da missão ou um excesso de zelo — por isso vale "
              "uma leitura humana.",
              "Leia o ponto. Se concorda, peça o ajuste com **Refazer** desta etapa; se não, siga e registre por quê no "
              "comentário.", quem, caso=True)


def _familia(codigo: str, gate: str, achado: Mapping[str, Any]) -> Optional[Explicacao]:
    if _RE_BNCC.match(codigo):
        if gate == "bncc_status" and "proposta" in str(achado.get("resumo") or "").lower():
            return _LETRAMENTO_PROPOSTO_EM
        return _x("Habilidade da BNCC a conferir",
                  f"A habilidade {codigo} da BNCC foi apontada pelo verificador (o motivo está abaixo).",
                  "A habilidade é o que a missão promete ensinar à escola: citação errada é promessa errada.",
                  "Leia o ponto e valide com a pedagogia. Registre no de acordo ou peça **Refazer** de produto.", PO,
                  caso=True)
    m = _RE_PERDIDO.match(codigo)
    if m:
        return _perdido(m)
    if codigo == "F7":
        return _x("Propostas esperando a homologação do PO",
                  "A revisão final de produto lista propostas do agente que ainda esperam a decisão do PO.",
                  "Proposta não homologada chega ao design como se fosse decisão.",
                  _DECIDA_NA_LISTA, PO, caso=True)
    if _RE_PROFUNDIDADE.match(codigo) and gate in ("profundidade_status", "diagnostico_status", ""):
        return _x("Ponto fraco de profundidade pedagógica",
                  "O revisor de profundidade achou um ponto em que a missão fica rasa (o motivo está abaixo).",
                  "A missão pode virar «seguir passos», sem a descoberta que a justifica.",
                  "Leia o ponto. Se concorda, peça o ajuste com **Refazer** de produto; se não, siga e registre por "
                  "quê.", PO, caso=True)
    return None


# ------------------------------------------------------------------ a consulta
def _codigo(achado: Mapping[str, Any]) -> str:
    return str(achado.get("codigo") or "").strip()


def explicar(achado: Mapping[str, Any], gate: str = "", sev: Optional[str] = None) -> Explicacao:
    """A explicação de um achado: a variante de bloqueio, o campo da ficha técnica, o catálogo pelo código, a família do
    código, o padrão do juiz, o verificador — nessa ordem. Sem nenhum, a genérica. `sev` é a severidade já calculada
    (o item a tira também do ícone do verificador); sem ela, vale a do achado."""
    codigo = _codigo(achado)
    if (sev or severidade(achado)) == BLOQUEIO and codigo in _SE_BLOQUEIO:
        return _SE_BLOQUEIO[codigo]
    if gate == "manifesto_status" and codigo in _CAMPOS_DA_FICHA:
        return _campo_da_ficha(codigo)
    if codigo in CATALOGO:
        return CATALOGO[codigo]
    familia = _familia(codigo, gate, achado) if codigo else None
    if familia:
        return familia
    padrao = str(achado.get("padrao") or "").strip()
    if padrao in PADROES:
        return PADROES[padrao]
    classe = str(achado.get("classe") or "").strip()
    if classe in CATALOGO and gate.startswith("rastro"):
        # o rastro grava o dono no código e o tipo do marcador na classe
        return CATALOGO[classe]
    if gate in GATES and (GATES[gate][3] or not codigo or _RE_CRITERIO.match(codigo) or _RE_ID_DE_JUIZ.match(codigo)):
        return _do_gate(gate)  # type: ignore[return-value]
    return generica(gate)


def generica(gate: str = "") -> Explicacao:
    nome = GATES[gate][0] if gate in GATES else ""
    onde = f" (no verificador «{nome}»)" if nome else ""
    return Explicacao(
        "Ponto técnico apontado pela esteira",
        f"A esteira encontrou um ponto técnico{onde} que ainda não tem explicação em linguagem simples. O texto "
        "original está nos detalhes técnicos, logo abaixo.",
        "Pode afetar a missão; o texto original diz onde.",
        "Leia o detalhe. Se não ficar claro, pergunte à etapa (campo de mensagem) ou ao time técnico antes de liberar.",
        None, texto_e_o_caso=True, generica=True)


def tem_explicacao(codigo: str, gate: str = "", achado: Optional[Mapping[str, Any]] = None) -> bool:
    return not explicar({**(achado or {}), "codigo": codigo}, gate).generica


def codigos_sem_explicacao(pares: Iterable[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """`[(gate, código)]` que caem na explicação genérica — o teste exige que nenhum do acervo caia."""
    return sorted({(g, c) for g, c in pares if c and not tem_explicacao(c, g)})


def quem_resolve(achado: Mapping[str, Any], gate: str = "", explicacao: Optional[Explicacao] = None) -> str:
    """O dono fixo da entrada; senão o agente que escreveu o trecho; senão o verificador; senão a etapa."""
    explicacao = explicacao or explicar(achado, gate)
    if explicacao.quem:
        return explicacao.quem
    agente = str(achado.get("agente_responsavel") or achado.get("dono") or "").strip()
    if agente:
        for regra, quem in _DONO_DO_AGENTE:
            if regra.search(agente):
                return quem
    etapa = str(achado.get("etapa") or "").strip()
    if etapa in _ETAPA_PARA_QUEM:
        return _ETAPA_PARA_QUEM[etapa]
    if gate in GATES:
        return GATES[gate][2]
    return ESTEIRA


def severidade(achado: Mapping[str, Any], icone_do_gate: str = "") -> str:
    sev = str(achado.get("severidade") or "").strip().lower()
    if sev in SEVERIDADE:
        return sev
    if sev in ("bloqueado", "bloqueante", "vermelho"):
        return BLOQUEIO
    return BLOQUEIO if icone_do_gate == "🔴" and not sev else ATENCAO


def severidade_em_palavras(sev: str) -> Tuple[str, str]:
    return SEVERIDADE.get(sev, SEVERIDADE[ATENCAO])


def nome_do_gate(gate: str, rotulos: Optional[Mapping[str, str]] = None) -> str:
    if gate in GATES:
        return GATES[gate][0]
    return (rotulos or {}).get(gate) or gate


# ------------------------------------------------------------------ o trecho da missão, inteiro
_RE_PREFIXO_REBAIXADO = re.compile(r"^\s*\[não causado pela correção — ([^\]]+)\]\s*")
_RE_TRECHO_EM_CRASE = re.compile(r"Trecho(?: do QA)?:\s*`([^`]+)`")


def _entre(texto: str, abre: str, fecha: str) -> List[str]:
    """O que está entre `abre` e `fecha`, no nível de fora — «a «b» c» é um trecho só."""
    saida, nivel, inicio = [], 0, 0
    for i, ch in enumerate(texto):
        if ch == abre:
            if nivel == 0:
                inicio = i + 1
            nivel += 1
        elif ch == fecha and nivel:
            nivel -= 1
            if nivel == 0:
                saida.append(texto[inicio:i])
    return saida


def _limpo(t: str, item: bool = False) -> str:
    """Sem espaços nas pontas; num item de lista, sem o «- » do item e sem as aspas que o envolvem inteiro."""
    t = t.strip()
    if item and t.startswith("- "):
        t = t[2:].strip()
    if len(t) >= 2 and t[0] == "«" and t[-1] == "»" and not _entre(t[1:-1], "«", "»"):
        t = t[1:-1].strip()
    return t


def trechos(achado: Mapping[str, Any], do_texto: bool = True) -> List[str]:
    """Os trechos da missão que motivaram o achado, inteiros e sem repetir: os campos de citação, os itens da lista do
    texto (linhas recuadas) e o que vem entre «», “” ou depois de «Trecho:». O que o verificador cortou na origem
    (`tools/*.py`) não volta — e o texto original segue inteiro nos detalhes técnicos."""
    vistos: List[str] = []

    def junta(t: Any, item: bool = False) -> None:
        t = _limpo(str(t or ""), item)
        if len(t) >= 2 and t not in vistos:
            vistos.append(t)

    for campo in ("citacao", "trecho", "contexto"):
        if achado.get(campo):
            junta(achado[campo])
    faltando = [f for f in achado.get("faltando") or [] if isinstance(f, Mapping) and f.get("texto")]
    if faltando:
        # a matriz de rastreabilidade grava a lista inteira à parte: o resumo dela traz só 6 itens de 70 caracteres
        for f in faltando:
            junta(f"{f['texto']} ({f.get('id')})" if f.get("id") else f["texto"])
        return vistos
    if not do_texto:
        return vistos
    resumo = sem_prefixo(str(achado.get("resumo") or ""))
    linhas = resumo.split("\n")
    itens = [l for l in linhas[1:] if l.startswith("  ") and l.strip()]
    corpo = linhas[0] if itens else resumo
    for t in _RE_TRECHO_EM_CRASE.findall(corpo):
        junta(t)
    corpo = _RE_TRECHO_EM_CRASE.sub("", corpo)
    for t in _entre(corpo, "«", "»") + _entre(corpo, "“", "”"):
        junta(t)
    # linhas de diff («-» o texto que fica, «+» o que o agente quis pôr): ditas em palavras, não com o sinal cru
    diff = any(l.strip().startswith("+") for l in itens)
    for l in itens:
        t = l.strip()
        if diff and t.startswith(("+", "-")):
            junta(("Como o agente quis deixar: " if t[0] == "+" else "Como está: ") + t[1:].strip())
        else:
            junta(l, item=True)
    if not vistos and resumo.lstrip().startswith(("-", "|", "[", "`")):
        # o rastro de lacunas grava a própria linha do documento como texto do achado: ela é o trecho
        junta(_limpo(resumo, item=True).strip("` "))
    return vistos


def sem_prefixo(texto: str) -> str:
    """O texto do verificador sem a marca «[não causado pela correção — …]», que a nota de rebaixamento já diz."""
    return _RE_PREFIXO_REBAIXADO.sub("", str(texto or ""))


def nota_de_rebaixamento(achado: Mapping[str, Any]) -> str:
    """O achado que era 🔴 e a linha de base da correção pontual rebaixou: dito em palavras."""
    m = _RE_PREFIXO_REBAIXADO.match(str(achado.get("resumo") or ""))
    if not m and not achado.get("severidade_original"):
        return ""
    return ("Este ponto já existia antes da última correção, que não o causou: por isso ele não impede seguir. "
            "Vale conferir mesmo assim.")


# ------------------------------------------------------------------ itens do cartão
@dataclass
class Item:
    gate: str
    icone_gate: str
    achado: Dict[str, Any]
    explicacao: Explicacao
    quem: str
    severidade: str
    trechos: List[str]
    tambem_em: List[str] = field(default_factory=list)

    @property
    def texto_original(self) -> str:
        return str(self.achado.get("resumo") or "")

    @property
    def o_que_fazer(self) -> str:
        """O que fazer, coerente com a severidade deste item — é o que o cartão mostra."""
        return o_que_fazer(self.explicacao, self.severidade)


def item(achado: Mapping[str, Any], gate: str = "", icone_gate: str = "") -> Item:
    sev = severidade(achado, icone_gate)
    exp = explicar(achado, gate, sev)
    return Item(gate=gate, icone_gate=icone_gate, achado=dict(achado), explicacao=exp,
                quem=quem_resolve(achado, gate, exp), severidade=sev,
                # quando o texto do juiz é o caso, ele já sai inteiro: os trechos são só os campos de citação
                trechos=trechos(achado, do_texto=not exp.texto_e_o_caso))


def _sem_detalhe(gate: str, icone: str) -> Item:
    nome = GATES[gate][0] if gate in GATES else gate
    exp = _x(f"{nome}: ficou {icone} sem dizer por quê",
             f"O verificador «{nome}» ficou {icone} e não detalhou o motivo aqui.",
             SEMAFORO_EM_PALAVRAS.get(icone, "").capitalize() + ".",
             "Abra o relatório dele nos passos da esteira (aba da etapa) ou pergunte à etapa pelo campo de mensagem.",
             GATES[gate][2] if gate in GATES else ESTEIRA)
    return Item(gate, icone, {}, exp, exp.quem or ESTEIRA, BLOQUEIO if icone == "🔴" else ATENCAO, [])


def itens_do_semaforo(estado: Mapping[str, Any], semaforo: Mapping[str, str]) -> List[Item]:
    """Os achados dos verificadores 🔴 e 🟡 da etapa, explicados, sem repetir o mesmo achado de dois verificadores.

    Ordem: o que impede seguir, depois o que pede decisão, depois o que é para conferir. Verificador 🔴 ou 🟡 sem
    achado vira um item que diz isso — antes, o cartão mostrava «0 achado(s)» e nada mais."""
    saida: List[Item] = []
    por_chave: Dict[Tuple[str, str], Item] = {}
    for gate, icone in semaforo.items():
        if icone not in ("🔴", "🟡"):
            continue
        envelope = estado.get(f"{gate}_envelope")
        achados = [a for a in ((envelope.get("achados") if isinstance(envelope, Mapping) else None) or [])
                   if isinstance(a, Mapping) and str(a.get("resumo") or "").strip()]
        if not achados:
            saida.append(_sem_detalhe(gate, icone))
            continue
        for a in achados:
            chave = (_codigo(a), " ".join(str(a.get("resumo")).split()))
            if chave in por_chave:
                por_chave[chave].tambem_em.append(gate)
                continue
            novo = item(a, gate, icone)
            por_chave[chave] = novo
            saida.append(novo)
    saida.sort(key=lambda i: _ORDEM_SEVERIDADE.get(i.severidade, 3))
    return saida


def agrupar_por_quem(itens: Sequence[Item]) -> List[Tuple[str, List[Item]]]:
    grupos: Dict[str, List[Item]] = {q: [] for q in ORDEM_QUEM}
    for i in itens:
        grupos.setdefault(i.quem, []).append(i)
    return [(q, lista) for q, lista in grupos.items() if lista]


def contagem(itens: Sequence[Item]) -> str:
    """«2 impedem seguir · 1 pede decisão · 3 para conferir»."""
    n = {s: sum(1 for i in itens if i.severidade == s) for s in SEVERIDADE}
    partes = []
    if n[BLOQUEIO]:
        partes.append(f"{n[BLOQUEIO]} {'impede' if n[BLOQUEIO] == 1 else 'impedem'} seguir")
    if n[DECISAO_HUMANA]:
        partes.append(f"{n[DECISAO_HUMANA]} {'pede' if n[DECISAO_HUMANA] == 1 else 'pedem'} decisão")
    if n[ATENCAO]:
        partes.append(f"{n[ATENCAO]} para conferir")
    return " · ".join(partes)


def explicacao_de_pendencia(pendencia: Mapping[str, Any]) -> Item:
    """Uma pendência da conferência de leitura (`pipeline.passagem.pendencias_de_conferencia`) como item."""
    achado = {"codigo": pendencia.get("tipo") or "", "resumo": pendencia.get("assunto") or "",
              "severidade": DECISAO_HUMANA}
    return item(achado, str(pendencia.get("gate") or ""), "🟡")
