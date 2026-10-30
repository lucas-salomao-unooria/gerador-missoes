// Executa ações num quadro do protótipo, com Playwright e o Chrome do sistema — CÓDIGO FIXO da esteira.
//
// Entrada: um JSON em argv[2] com {html, n, largura, altura, chrome, png, acoes}. Cada ação é um objeto
// com uma chave só: {clicar: alvo}, {digitar: [alvo, texto]}, {arrastar: [origem, destino]},
// {tecla: "Enter"}, {esperar: ms}. O alvo é um seletor do Playwright: `text=Começar Análise`,
// `role=button[name="Registrar Decisão"]` ou CSS. Saída: JSON com a tela antes e depois, o resultado de
// cada passo, os erros da página e a captura final.
import { chromium } from "playwright-core";

const e = JSON.parse(process.argv[2]);
const navegador = await chromium.launch({ executablePath: e.chrome, headless: true });
const pagina = await navegador.newPage({ viewport: { width: e.largura, height: e.altura } });
const erros = [];
pagina.on("pageerror", (x) => erros.push(String(x)));
pagina.on("console", (m) => { if (m.type() === "error") erros.push(m.text()); });
await pagina.goto(`file://${e.html}#captura=${e.n}`);
await pagina.waitForTimeout(500);
const atual = () => pagina.evaluate(() => document.body.dataset.atual || "");
const antes = await atual();
const passos = [];
for (const acao of e.acoes || []) {
  const [tipo, arg] = Object.entries(acao)[0] || [];
  try {
    if (tipo === "clicar") await pagina.locator(arg).first().click({ timeout: 4000 });
    else if (tipo === "digitar") await pagina.locator(arg[0]).first().fill(arg[1], { timeout: 4000 });
    else if (tipo === "arrastar") await pagina.locator(arg[0]).first().dragTo(pagina.locator(arg[1]).first(), { timeout: 4000 });
    else if (tipo === "tecla") await pagina.keyboard.press(arg);
    else if (tipo === "esperar") await pagina.waitForTimeout(Math.min(Number(arg) || 0, 15000));
    else throw new Error(`ação desconhecida: ${tipo}`);
    await pagina.waitForTimeout(250);
    passos.push({ acao, ok: true, tela: await atual() });
  } catch (x) {
    passos.push({ acao, ok: false, erro: String(x.message || x).split("\n")[0] });
    break;
  }
}
await pagina.screenshot({ path: e.png });
console.log(JSON.stringify({ antes, depois: await atual(), passos, erros, png: e.png }));
await navegador.close();
