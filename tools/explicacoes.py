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
    "decisao-atribuida-ao-po": _x(
        "Decisão escrita como se fosse do PO",
        "O texto diz que o PO decidiu algo, mas a esteira não acha essa decisão nos pareceres nem nos pedidos do PO.",
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
        "Decida: substituir a existente ou dar outro código. Registre no de acordo.", PO),
    "experiencia-ja-existe": _x(
        "Esta missão já existe na plataforma",
        "Já há uma missão publicada com este código; o documento para o dev a trata como nova.",
        "O dev pode criar uma segunda versão em vez de atualizar a que está no ar.",
        "Decida se esta missão atualiza a existente ou ganha outro código, e registre no de acordo.", PO),
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
    "letramento": _x(
        "Habilidade do Ensino Médio lida como letramento digital",
        "A habilidade conta como letramento digital por uma leitura proposta do Ensino Médio, que não tem eixo "
        "oficial.",
        "A classificação pode não ser a que a pedagogia adota.",
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
    "eixo-divergente": _x(
        "Habilidade classificada no eixo errado",
        "A habilidade aparece num eixo da BNCC que não é o dela.",
        "A classificação errada confunde a leitura curricular da missão.",
        "Peça a correção com **Refazer** de produto. Não trava a etapa.", PO),
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
           "stitch-recusou", "stitch-incompleto"):
    CATALOGO.setdefault(_c, _FALHA_DA_ESTEIRA)

#: Sinônimos: o rastro de lacunas grava o tipo do marcador; o diagnóstico, o dono.
CATALOGO.setdefault("pendencia-plataforma", _x(
    "Pendência da plataforma",
    "A missão precisa de algo que a plataforma ainda não tem; o texto marcou isso como pendência com dono.",
    "Até a plataforma entregar, essa parte da missão não funciona.",
    "Combine com o time de plataforma quem resolve e quando. Não trava a etapa.", DEV))
CATALOGO.setdefault("plataforma", CATALOGO["pendencia-plataforma"])

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
            return CATALOGO["letramento"]
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


def explicar(achado: Mapping[str, Any], gate: str = "") -> Explicacao:
    """A explicação de um achado: catálogo pelo código, família do código, padrão do juiz, verificador — nessa ordem.
    Sem nenhum, a genérica."""
    codigo = _codigo(achado)
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


def item(achado: Mapping[str, Any], gate: str = "", icone_gate: str = "") -> Item:
    exp = explicar(achado, gate)
    return Item(gate=gate, icone_gate=icone_gate, achado=dict(achado), explicacao=exp,
                quem=quem_resolve(achado, gate, exp), severidade=severidade(achado, icone_gate),
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
