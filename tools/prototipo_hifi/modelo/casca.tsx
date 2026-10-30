/**
 * Casca de revisão do protótipo em alta fidelidade — CÓDIGO FIXO da esteira, o agente não edita.
 *
 * Trilho por etapa, barra com ID e estado, palco com o quadro em escala, painel da etapa (texto do
 * one-pager) e rodapé com ação e resultado. Cada quadro é a função que o agente escreveu em
 * `telas/<ID>.tsx`, no objeto `estados`, sob o nome exato do estado do inventário. As telas são
 * interativas: chamam `ir()` (de `casca-api`) para seguir o fluxo, e a casca troca o quadro.
 *
 * Três modos pelo hash: normal (revisão humana e jogo), `#captura=<n>` (o quadro n no tamanho real, ainda
 * navegável: é o que a captura e o `interagir` abrem) e `#auditoria` (monta todos e escreve o resultado
 * em `<pre id="auditoria">`). O `<body>` leva `data-atual="<ID>|<estado>"` com o quadro na tela.
 */
import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "@unooria/design-system/unooria.css";
import "@unooria/design-system/unooriaai.css";
import "@unooria/design-system/fonts/unooria.css";
import "@unooria/design-system/fonts/unooriaai.css";
import missao from "./dados/missao.json";
import { telas } from "./gerado/registro";
import { MissaoContexto, type Missao } from "./casca-api";

type Quadro = {
  id: string; estado: string; etapa: string; ator: string; ambiente: string; proposito: string;
  acao: string; resultado: string; largura: number; altura: number;
};
const QUADROS: Quadro[] = (missao as any).quadros;
const ETAPAS: Record<string, { nome: string; texto: string; fonte: string }> = (missao as any).etapas;

function componente(q: Quadro): React.FC | null {
  const modulo: any = (telas as any)[q.id];
  return (modulo && modulo.estados && modulo.estados[q.estado]) || null;
}

function indiceDe(id: string, estado?: string): number {
  return QUADROS.findIndex((q) => q.id === id && (estado === undefined || q.estado === estado));
}

/** Posição atual, sessão simulada e o `ir()` que as telas chamam. */
function useNavegacao(inicio: number) {
  const [i, setI] = useState(inicio);
  const [sessao, setSessao] = useState<Record<string, any>>({});
  const ir = useCallback((id: string, estado?: string) => {
    const n = indiceDe(id, estado);
    if (n < 0) console.error(`[casca] ir("${id}"${estado ? `, "${estado}"` : ""}): tela ou estado fora do inventário`);
    else setI(n);
  }, []);
  const definir = useCallback((chave: string, valor: any) => setSessao((s) => ({ ...s, [chave]: valor })), []);
  const q = QUADROS[i];
  const api: Missao = useMemo(() => ({ ir, sessao, definir, atual: { id: q?.id, estado: q?.estado } }), [ir, sessao, definir, q]);
  useEffect(() => { if (q) document.body.dataset.atual = `${q.id}|${q.estado}`; }, [q]);
  return { i, setI, q, api, reiniciar: () => setSessao({}) };
}

class Limite extends React.Component<{ q: Quadro; children: React.ReactNode }, { erro: string | null }> {
  state = { erro: null as string | null };
  static getDerivedStateFromError(e: unknown) { return { erro: String((e as Error)?.message || e) }; }
  render() {
    if (this.state.erro) {
      return <div className="hifi-erro" data-erro={this.state.erro}>Erro ao montar {this.props.q.id} · {this.props.q.estado}: {this.state.erro}</div>;
    }
    return this.props.children;
  }
}

function Quadro({ q }: { q: Quadro }) {
  const C = componente(q);
  return (
    <div className="hifi-quadro" data-screen-id={q.id} data-estado={q.estado} data-faltando={C ? undefined : "sim"}
         data-uai-theme="light" style={{ width: q.largura, height: q.altura }}>
      {C ? <Limite q={q}><C /></Limite> : <div className="hifi-faltando">{q.id} · {q.estado}<br />tela ainda não gerada</div>}
    </div>
  );
}

function Palco({ q }: { q: Quadro }) {
  const caixa = useRef<HTMLDivElement>(null);
  const [escala, setEscala] = useState(1);
  useLayoutEffect(() => {
    const medir = () => {
      const el = caixa.current;
      if (!el) return;
      setEscala(Math.min(1, (el.clientWidth - 32) / q.largura, (el.clientHeight - 48) / q.altura));
    };
    medir();
    window.addEventListener("resize", medir);
    return () => window.removeEventListener("resize", medir);
  }, [q]);
  return (
    <div className="hifi-palco" ref={caixa}>
      <div style={{ width: q.largura * escala, height: q.altura * escala }}>
        <div style={{ transform: `scale(${escala})`, transformOrigin: "top left" }}><Quadro key={`${q.id}|${q.estado}`} q={q} /></div>
      </div>
      <div className="hifi-legenda">{q.ator === "PROF" ? "janela do hub" : "experiência no hub"}, {q.largura}×{q.altura} · as telas respondem a clique: jogue a missão</div>
    </div>
  );
}

function Revisao() {
  const { i, setI, q, api, reiniciar } = useNavegacao(0);
  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.closest?.(".hifi-quadro")) return;  // tecla dentro da tela é da tela
      if (e.key === "ArrowRight") setI((n) => Math.min(QUADROS.length - 1, n + 1));
      if (e.key === "ArrowLeft") setI((n) => Math.max(0, n - 1));
    };
    window.addEventListener("keydown", tecla);
    return () => window.removeEventListener("keydown", tecla);
  }, [setI]);
  const etapa = ETAPAS[q.etapa] || { nome: `Etapa ${q.etapa}`, texto: "", fonte: "" };
  let ultimaEtapa = "";
  return (
    <MissaoContexto.Provider value={api}>
      <div className="hifi-app">
        <nav className="hifi-trilho" aria-label="Telas">
          <div className="hifi-titulo">{(missao as any).titulo}<small>{(missao as any).missao}</small></div>
          {QUADROS.map((x, n) => {
            const cab = x.etapa !== ultimaEtapa ? <div className="hifi-etapa">{(ETAPAS[x.etapa] || { nome: `Etapa ${x.etapa}` }).nome}</div> : null;
            ultimaEtapa = x.etapa;
            return (
              <React.Fragment key={n}>
                {cab}
                <button className={n === i ? "ativo" : ""} onClick={() => setI(n)} aria-current={n === i}>
                  <b>{x.id}</b> <em>{x.ator}</em>{componente(x) ? "" : " ⚠"}<br /><span>{x.estado}</span>
                </button>
              </React.Fragment>
            );
          })}
        </nav>
        <header className="hifi-barra">
          <span className="hifi-chip">{etapa.nome}</span><code>{q.id} [{q.estado}]</code>
          <span className="hifi-esp" />
          <button onClick={reiniciar} title="Apaga as escolhas feitas nas telas">Reiniciar sessão</button>
          {i + 1} de {QUADROS.length}
          <button onClick={() => setI(Math.max(0, i - 1))} disabled={i === 0}>← Anterior</button>
          <button onClick={() => setI(Math.min(QUADROS.length - 1, i + 1))} disabled={i === QUADROS.length - 1}>Próximo →</button>
        </header>
        <Palco q={q} />
        <aside className="hifi-painel">
          <h2>Por que esta etapa existe</h2><h3>{etapa.nome}</h3>
          <p>{etapa.texto || "O one-pager não traz texto para esta etapa."}</p>
          <h2>Esta tela</h2><p>{q.proposito}</p>
          {Object.keys(api.sessao).length ? <><h2>Sessão simulada</h2><pre className="hifi-sessao">{JSON.stringify(api.sessao, null, 1)}</pre></> : null}
          {etapa.fonte ? <small>Fonte: {etapa.fonte}</small> : null}
        </aside>
        <footer className="hifi-rodape"><b>TELA</b> {q.id} ({q.estado}) <b>AÇÃO</b> {q.acao} <b>O QUE MUDA</b> {q.resultado}</footer>
      </div>
    </MissaoContexto.Provider>
  );
}

function Captura({ n }: { n: number }) {
  const { q, api } = useNavegacao(n);
  if (!q) return <div>quadro {n} inexistente</div>;
  return (
    <MissaoContexto.Provider value={api}>
      <div className="hifi-captura"><Quadro key={`${q.id}|${q.estado}`} q={q} /></div>
    </MissaoContexto.Provider>
  );
}

/** Monta todos os quadros fora da tela e escreve cobertura, erros e texto visível de cada um. */
function Auditoria() {
  const raiz = useRef<HTMLDivElement>(null);
  const [saida, setSaida] = useState("");
  useEffect(() => {
    const t = setTimeout(() => {
      const quadros = Array.from(raiz.current!.querySelectorAll<HTMLElement>(".hifi-quadro"));
      setSaida(JSON.stringify(quadros.map((el) => ({
        id: el.dataset.screenId, estado: el.dataset.estado,
        faltando: el.dataset.faltando === "sim",
        erro: el.querySelector<HTMLElement>(".hifi-erro")?.dataset.erro || null,
        texto: (el.innerText || "").split("\n").map((s) => s.trim()).filter(Boolean),
      }))));
    }, 1500);
    return () => clearTimeout(t);
  }, []);
  return <><div ref={raiz} className="hifi-auditoria">{QUADROS.map((q, n) => <Quadro key={n} q={q} />)}</div><pre id="auditoria">{saida}</pre></>;
}

const hash = decodeURIComponent(location.hash.slice(1));
const captura = /^captura=(\d+)$/.exec(hash);
createRoot(document.getElementById("raiz")!).render(
  captura ? <Captura n={Number(captura[1])} /> : hash === "auditoria" ? <Auditoria /> : <Revisao />,
);
