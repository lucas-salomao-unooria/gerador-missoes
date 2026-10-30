/**
 * Casca de revisão do protótipo em alta fidelidade — CÓDIGO FIXO da esteira, o agente não edita.
 *
 * Trilho por etapa, barra com ID e estado, palco com o quadro em escala, painel da etapa (texto do
 * one-pager) e rodapé com ação e resultado. Cada quadro é a função que o agente escreveu em
 * `telas/<ID>.tsx`, no objeto `estados`, sob o nome exato do estado do inventário.
 *
 * Três modos pelo hash: normal (revisão humana), `#captura=<n>` (só o quadro n, no tamanho real, para
 * a captura de tela) e `#auditoria` (renderiza todos e escreve o resultado em `<pre id="auditoria">`).
 */
import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "@unooria/design-system/unooria.css";
import "@unooria/design-system/unooriaai.css";
import "@unooria/design-system/fonts/unooria.css";
import "@unooria/design-system/fonts/unooriaai.css";
import missao from "./dados/missao.json";
import { telas } from "./gerado/registro";

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
      <div className="hifi-legenda">{q.ator === "PROF" ? "janela do hub" : "experiência no hub"}, {q.largura}×{q.altura}</div>
    </div>
  );
}

function Revisao() {
  const [i, setI] = useState(0);
  const q = QUADROS[i];
  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === "ArrowDown") setI((n) => Math.min(QUADROS.length - 1, n + 1));
      if (e.key === "ArrowLeft" || e.key === "ArrowUp") setI((n) => Math.max(0, n - 1));
    };
    window.addEventListener("keydown", tecla);
    return () => window.removeEventListener("keydown", tecla);
  }, []);
  const etapa = ETAPAS[q.etapa] || { nome: `Etapa ${q.etapa}`, texto: "", fonte: "" };
  let ultimaEtapa = "";
  return (
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
        <span className="hifi-esp" />{i + 1} de {QUADROS.length}
        <button onClick={() => setI(Math.max(0, i - 1))} disabled={i === 0}>← Anterior</button>
        <button onClick={() => setI(Math.min(QUADROS.length - 1, i + 1))} disabled={i === QUADROS.length - 1}>Próximo →</button>
      </header>
      <Palco q={q} />
      <aside className="hifi-painel">
        <h2>Por que esta etapa existe</h2><h3>{etapa.nome}</h3>
        <p>{etapa.texto || "O one-pager não traz texto para esta etapa."}</p>
        <h2>Esta tela</h2><p>{q.proposito}</p>
        {etapa.fonte ? <small>Fonte: {etapa.fonte}</small> : null}
      </aside>
      <footer className="hifi-rodape"><b>TELA</b> {q.id} ({q.estado}) <b>AÇÃO</b> {q.acao} <b>O QUE MUDA</b> {q.resultado}</footer>
    </div>
  );
}

function Captura({ n }: { n: number }) {
  const q = QUADROS[n];
  return q ? <div className="hifi-captura"><Quadro q={q} /></div> : <div>quadro {n} inexistente</div>;
}

/** Renderiza todos os quadros fora da tela e escreve cobertura, erros e texto visível de cada um. */
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
