## Citação em todo achado que bloqueia — o código confere

Cada achado que bloqueia (❌, severidade `bloqueio`, `NOK`) traz no envelope JSON o campo **`"citacao"`**: o trecho
do documento avaliado onde o problema está, **copiado letra a letra**, de 6 a 40 palavras. Achado de ausência ("falta
a tela de erro") cita o trecho de onde ela deveria estar — o título da seção e a primeira frase dela.

Um código confere cada citação no documento que você avaliou. A que não existe lá rebaixa o achado a atenção: inventar
ou parafrasear a citação não bloqueia nada, e o achado verdadeiro se perde. Atenção e sugestão não precisam de citação.
