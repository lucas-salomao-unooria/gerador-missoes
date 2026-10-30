/**
 * O que a casca oferece às telas — CÓDIGO FIXO da esteira, o agente não edita.
 *
 * `ir(id, estado?)` leva à próxima tela do fluxo (sem estado, ao primeiro estado dela). `sessao` guarda
 * o que o estudante fez e que outra tela precisa ler (a escolha da Etapa 3 que a Etapa 4 mostra); some
 * ao recarregar a página ou no botão «Reiniciar sessão», como um mock de servidor.
 */
import React, { useContext } from "react";

export type Missao = {
  /** Vai para a tela `id`, no `estado` dado ou no primeiro estado dela. */
  ir: (id: string, estado?: string) => void;
  /** Dados da sessão simulada, compartilhados entre telas. */
  sessao: Record<string, any>;
  /** Grava um dado na sessão simulada. */
  definir: (chave: string, valor: any) => void;
  /** A tela e o estado em que a casca está. */
  atual: { id: string; estado: string };
};

export const MissaoContexto = React.createContext<Missao>({
  ir: () => undefined,
  sessao: {},
  definir: () => undefined,
  atual: { id: "", estado: "" },
});

export function useMissao(): Missao {
  return useContext(MissaoContexto);
}
