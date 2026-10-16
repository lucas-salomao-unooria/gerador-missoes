"""Comitês pedagógicos da etapa de Produto — três juízes votam, o código conta, e quem escreve a missão corrige.

Dois comitês (decisão do PO de 15/10/2026):

- **dos canais** — logo depois de o A014 definir o §12a: o painel A julga a mecânica e a ação do Canal A de cada
  habilidade, o painel B julga a pergunta do Canal B; os dois votam na mesma rodada, cada um com a própria
  unanimidade, e o loop só sai quando os dois aprovam (até `COMITE_MAX_RODADAS`, padrão 5);
- **final** — sobre a missão completa, antes do gate final: pedagogia, qualidade de produto e imersão (até
  `COMITE_FINAL_MAX_RODADAS`, padrão 2).

O comitê não escreve. Reprovada, a missão volta a quem a escreve — o A004 (núcleo) e o A014 (seções de apoio) —, e a
reescrita passa de novo pelos gates do núcleo. Por isso o loop do comitê envolve os loops dos autores, isolados
(`agents.checkers.LoopIsolado`): sem isolar, a saída do loop do núcleo encerraria o do comitê. Esgotado o teto sem
unanimidade, a missão segue 🟡 com os votos vencidos no parecer do PO.
"""
from __future__ import annotations

from typing import Any, Dict, List

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.loop_agent import LoopAgent
from google.adk.agents.parallel_agent import ParallelAgent

from agents.base import create_llm_agent
from agents.callbacks import manter_nucleo_sem_achado_do_a004, marcar_heranca, pular_juiz_sem_canal_b
from agents.checkers import ComiteVotosAgent, MecanicaCheckAgent, RastroCheckAgent, SaidaDeLoopAgent, isolar
from config import get_settings
from prompts.loader import load_prompt

#: painel → juízes: (sufixo do nome, prompt, chave de saída, rótulo no relatório, descrição)
JUIZES: Dict[str, List[tuple]] = {
    "canal_a": [
        ("ComiteCanalACurriculo", "produto/comite_canal_a_curriculo.md", "comite_canal_a_curriculo", "A·1 Currículo",
         "Painel A: a ação do Canal A de cada habilidade é o verbo e o objeto do texto oficial, na decisão onde o limiar mora."),
        ("ComiteCanalAMedida", "produto/comite_canal_a_medida.md", "comite_canal_a_medida", "A·2 Medida",
         "Painel A: a regra ternária é alcançável, sem buraco, sem Atingiu por sorte e calculável pelo que o evento registra."),
        ("ComiteCanalAVivencia", "produto/comite_canal_a_vivencia.md", "comite_canal_a_vivencia", "A·3 Vivência e idade",
         "Painel A: a ação é verbo nativo, vivida na decisão e dentro dos tetos da faixa."),
    ],
    "canal_b": [
        ("ComiteCanalBCurriculo", "produto/comite_canal_b_curriculo.md", "comite_canal_b_curriculo", "B·1 Currículo",
         "Painel B: a pergunta mede a habilidade da linha, e o Atingiu é domínio pleno e autônomo."),
        ("ComiteCanalBMedida", "produto/comite_canal_b_medida.md", "comite_canal_b_medida", "B·2 Medida",
         "Painel B: as três alternativas discriminam os níveis e nenhuma se elimina pela linguagem."),
        ("ComiteCanalBExperiencia", "produto/comite_canal_b_experiencia.md", "comite_canal_b_experiencia", "B·3 Experiência",
         "Painel B: depois do Refletir sem repeti-lo, na língua do ambiente, sem vazar resultado e dentro do teto."),
    ],
    "final": [
        ("ComiteFinalPedagogia", "produto/comite_final_pedagogia.md", "comite_final_pedagogia", "F·1 Pedagogia",
         "Comitê final: limiar vivido, aha com os seis passos e canais ainda coerentes depois das revisões."),
        ("ComiteFinalQualidade", "produto/comite_final_qualidade.md", "comite_final_qualidade", "F·2 Qualidade de produto",
         "Comitê final: uma missão só, tempos e tetos que fecham, professor claro e construível sem inventar."),
        ("ComiteFinalImersao", "produto/comite_final_imersao.md", "comite_final_imersao", "F·3 Imersão",
         "Comitê final: porta, troca e chegada diegéticas, verbos nativos e virada mostrada pelo ambiente."),
    ],
}

#: Onde a citação de cada bloqueio é conferida.
DOCUMENTOS = ["nucleo_narrativo", "one_pager", "brief_escopo"]


def rotulos(painel: str) -> Dict[str, str]:
    return {chave: rotulo for _, _, chave, rotulo, _ in JUIZES[painel]}


def _juizes(painel: str, numero: int, letras: str, **kw: Any) -> List[LlmAgent]:
    """Juízes novos a cada chamada: um agente ADK só tem um pai."""
    juizes = []
    for letra, (sufixo, prompt, chave, _, descricao) in zip(letras, JUIZES[painel]):
        callbacks = [marcar_heranca] + ([pular_juiz_sem_canal_b(chave)] if painel == "canal_b" else [])
        juizes.append(create_llm_agent(
            name=f"A{numero:03d}{letra}{sufixo}",
            description=descricao,
            instruction=load_prompt(prompt),
            output_key=chave,
            before_agent_callback=callbacks,
            deterministico=True,  # emite voto: mesmo artefato, mesma resposta
            **kw,
        ))
    return juizes


def _evidencia_one_pager(nome: str) -> RastroCheckAgent:
    return RastroCheckAgent(
        name=nome,
        description="§12a do one-pager: toda habilidade da seção 2 com linha, Canal A e regra ternária por extenso; Canal B "
                    "com o nível de cada alternativa. Forma antes de voto. Determinístico.",
        modo="evidencia_one_pager",
        rotulo="Contrato de evidência do one-pager (§12a)",
        report_key="evidencia_one_pager_report",
        status_key="evidencia_one_pager_status",
        agente="evidencia-one-pager",
        estrito=False,
    )


def build_comite_canais_loop(autores: List[BaseAgent], numero: int = 18, **kw: Any) -> LoopAgent:
    """Núcleo e seções de apoio (isolados) → forma do §12a → painéis A e B → votos → saída.

    `autores`: o loop do núcleo, o das seções de apoio e o que confere que o one-pager existe, nessa ordem. O do núcleo é
    pulado quando os comitês reprovados não têm nada para o A004 (`manter_nucleo_sem_achado_do_a004`).
    """
    settings = get_settings()
    rodadas = max(1, settings.comite_max_rodadas)
    nucleo, apoio, *resto = autores
    nucleo_isolado = isolar(nucleo)
    nucleo_isolado.before_agent_callback = manter_nucleo_sem_achado_do_a004
    return LoopAgent(
        name="ComiteCanaisLoop",
        description="Comitê dos canais: núcleo e seções de apoio ↔ painéis A (mecânica e Canal A) e B (Canal B), três "
                    "juízes cada, até os dois aprovarem por unanimidade ou esgotar as rodadas.",
        max_iterations=rodadas,
        before_agent_callback=marcar_heranca,
        sub_agents=[
            nucleo_isolado,
            isolar(apoio),
            *resto,
            _evidencia_one_pager(f"A{numero:03d}EvidenciaOnePager"),
            ParallelAgent(
                name=f"A{numero + 1:03d}ComiteCanais",
                description="Painéis A e B do comitê dos canais votam em paralelo sobre a mesma versão do one-pager.",
                sub_agents=_juizes("canal_a", numero + 1, "abc", **kw) + _juizes("canal_b", numero + 1, "def", **kw),
                before_agent_callback=marcar_heranca,
            ),
            ComiteVotosAgent(
                name=f"A{numero + 2:03d}VotosCanalA",
                description="Conta os votos do painel A: unanimidade aprova; sem ela, a missão volta ao A004 e ao A014.",
                fontes=rotulos("canal_a"), documentos=DOCUMENTOS,
                report_key="comite_canal_a_report", status_key="comite_canal_a_status",
                round_key="comite_canal_a_rodada", max_rounds=rodadas,
                rotulo="Comitê dos canais — painel A", titulo="Comitê dos canais — painel A (mecânica e Canal A)",
            ),
            ComiteVotosAgent(
                name=f"A{numero + 3:03d}VotosCanalB",
                description="Conta os votos do painel B: unanimidade aprova; sem ela, a missão volta ao A004 e ao A014.",
                fontes=rotulos("canal_b"), documentos=DOCUMENTOS,
                report_key="comite_canal_b_report", status_key="comite_canal_b_status",
                round_key="comite_canal_b_rodada", max_rounds=rodadas,
                rotulo="Comitê dos canais — painel B", titulo="Comitê dos canais — painel B (Canal B)",
            ),
            SaidaDeLoopAgent(
                name=f"A{numero + 4:03d}ComiteCanaisRodada",
                description="Os dois painéis unânimes e o §12a em forma encerram o loop; senão, a missão volta ao núcleo "
                            "e às seções de apoio com os relatórios.",
                rotulo="Comitê dos canais",
                status_keys=["comite_canal_a_status", "comite_canal_b_status", "evidencia_one_pager_status"],
                rodada_key="comite_canais_rodada",
                max_rounds=rodadas,
                autor_keys=["one_pager"],
            ),
        ],
    )


def build_comite_final_loop(cadeia: List[BaseAgent], numero: int = 38, **kw: Any) -> LoopAgent:
    """A cadeia de produto até a conferência do PO (loops isolados) → forma do §12a → conta da virada → painel final.

    `cadeia`: comitê dos canais, gate estrutural, avaliações e conferência do one-pager do PO — os loops, ainda não
    isolados. Reprovado, a próxima volta recomeça no núcleo: quem escreve a missão corrige, e tudo é conferido de novo.
    """
    settings = get_settings()
    rodadas = max(1, settings.comite_final_max_rodadas)
    return LoopAgent(
        name="ComiteFinalLoop",
        description="Comitê final: a cadeia de produto ↔ pedagogia, qualidade e imersão sobre a missão completa, até "
                    "os três aprovarem ou esgotar as rodadas.",
        max_iterations=rodadas,
        before_agent_callback=marcar_heranca,
        sub_agents=[
            *[isolar(loop) if isinstance(loop, LoopAgent) else loop for loop in cadeia],
            _evidencia_one_pager(f"A{numero:03d}EvidenciaOnePagerFinal"),
            MecanicaCheckAgent(
                name=f"A{numero + 1:03d}ContaDaViradaOnePager",
                description="Refaz a conta da tabela 1.3 sobre o one-pager de agora: o gate estrutural e os revisores "
                            "podem ter mudado a mecânica depois do núcleo. Determinístico.",
                chave="one_pager", report_key="mecanica_one_pager_report", status_key="mecanica_one_pager_status",
            ),
            ParallelAgent(
                name=f"A{numero + 2:03d}ComiteFinal",
                description="Pedagogia, qualidade de produto e imersão votam em paralelo sobre a missão completa.",
                sub_agents=_juizes("final", numero + 2, "abc", **kw),
                before_agent_callback=marcar_heranca,
            ),
            ComiteVotosAgent(
                name=f"A{numero + 3:03d}VotosFinal",
                description="Conta os votos do comitê final: unanimidade aprova; sem ela, a missão volta ao A004 e ao A014.",
                fontes=rotulos("final"), documentos=DOCUMENTOS,
                report_key="comite_final_report", status_key="comite_final_status",
                round_key="comite_final_rodada", max_rounds=rodadas,
                rotulo="Comitê final", titulo="Comitê final — pedagogia, qualidade e imersão",
            ),
            SaidaDeLoopAgent(
                name=f"A{numero + 4:03d}ComiteFinalRodada",
                description="Os três juízes de acordo, o §12a em forma e a conta da virada fechando encerram o loop; "
                            "senão, a missão volta ao núcleo e às seções de apoio, e a cadeia roda de novo.",
                rotulo="Comitê final",
                status_keys=["comite_final_status", "evidencia_one_pager_status", "mecanica_one_pager_status"],
                rodada_key="comite_final_externo_rodada",
                max_rounds=rodadas,
                autor_keys=["one_pager"],
            ),
        ],
    )
