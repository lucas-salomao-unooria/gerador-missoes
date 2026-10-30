/**
 * A casca do hub, portada do código da plataforma — CÓDIGO FIXO da esteira, o agente não edita.
 *
 * Mesmas classes e mesmos componentes de `apps/hub/components/header-plataforma.tsx`,
 * `menu-da-conta.tsx` e `app/(plataforma)/professor/layout.tsx` (plataforma-unooria): o
 * Tailwind do hub é compilado no build e o `plataforma.css` vem da ponte `@edu/ui`. O que muda é só o
 * que depende de servidor: sessão (nome e papel chegam por prop), `Link` do Next (vira `<a>`) e o
 * seletor de escola. Se o header do hub mudar, este arquivo muda junto.
 */
import React from "react";
import { Breadcrumb, HeaderMenu, Icon, Logo } from "@edu/ui/ds";

/** Altura do header do hub: `h-16` (64 px) + a `border-b` de 1 px. */
export const ALTURA_HEADER = 65;

type Voltar = { rotulo: string; onClick?: () => void };

/** `HeaderPlataforma`: marca à esquerda, identidade e menu da conta à direita. Um só para todos os papéis. */
export function HeaderPlataforma({ nome, apoio, voltar }: { nome: string; apoio: string; voltar?: Voltar }) {
  return (
    <header className="hifi-hub border-b border-unooria-neutral-200 bg-unooria-neutral-50">
      <div className="flex h-16 w-full items-center justify-between gap-4 px-6">
        <div className="flex items-center gap-4">
          <a href="#" onClick={(e) => e.preventDefault()} className="flex items-center gap-3" aria-label="Plataforma Unooria — início">
            <Logo size="sm" color="navy" />
          </a>
          {voltar ? (
            <>
              <span aria-hidden className="h-6 w-px bg-unooria-neutral-200" />
              <a
                href="#"
                onClick={(e) => { e.preventDefault(); voltar.onClick?.(); }}
                className="flex items-center gap-1 text-[13px] font-semibold text-unooria-neutral-600 hover:text-unooria-neutral-950"
              >
                <Icon name="arrow_back" size="s" color="currentColor" aria-hidden />
                {voltar.rotulo}
              </a>
            </>
          ) : null}
        </div>
        <div className="flex items-center gap-3">
          <div className="hidden text-right sm:block">
            <p className="text-[13px] font-semibold text-unooria-neutral-950">{nome}</p>
            <p className="text-[12px] text-unooria-neutral-500">{apoio}</p>
          </div>
          <HeaderMenu items={[{ key: "sair", label: "Sair", icon: "logout" }]} avatarName={nome} triggerLabel={`Conta de ${nome}`} />
        </div>
      </div>
    </header>
  );
}

/**
 * A área do professor: header, trilha (breadcrumb do DS) e a coluna `max-w-5xl` com `px-6 py-8`.
 * `trilha` é o caminho de volta, do mais geral à página atual (a última é a atual).
 */
export function CascaProfessor({ trilha, children, nome = "Professor(a)" }: {
  trilha?: string[]; children: React.ReactNode; nome?: string;
}) {
  return (
    <div className="hifi-hub unooria-theme-light unooria-surface flex h-full flex-col">
      <HeaderPlataforma nome={nome} apoio="Professor" />
      <main className="plataforma-largura-cheia mx-auto w-full max-w-5xl flex-1 overflow-y-auto px-6 py-8">
        {trilha && trilha.length ? (
          <div className="mb-6">
            <Breadcrumb items={trilha.map((label, i) => ({ label, isCurrent: i === trilha.length - 1 }))} />
          </div>
        ) : null}
        {children}
      </main>
    </div>
  );
}

/**
 * O estudante dentro da missão (`/exp/[expId]`): o header do hub com «Missões» de volta e, abaixo, a área
 * que o hub reserva para o iframe da experiência. Nada da marca entra DENTRO dessa área.
 */
export function CascaEstudante({ children, nome = "Estudante", serie = "9º ano" }: {
  children: React.ReactNode; nome?: string; serie?: string;
}) {
  return (
    <div className="unooria-theme-light unooria-surface flex h-full flex-col">
      <HeaderPlataforma nome={nome} apoio={serie} voltar={{ rotulo: "Missões" }} />
      <div className="relative min-h-0 flex-1 overflow-hidden">{children}</div>
    </div>
  );
}
