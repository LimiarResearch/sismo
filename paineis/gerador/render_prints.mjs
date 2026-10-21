// Renderiza cada tela de telas_html/ com Chromium (Playwright) no tamanho dela e grava o PNG.
// Uso: node render_prints.mjs <pasta telas_html> <pasta de saída>
import { chromium } from "playwright";
import path from "node:path";
const [src, out] = process.argv.slice(2);
const telas = [["01", "Capabilities-en", 1080], ["02", "Purpose-en", 1080], ["03", "Scorecard-en", 1080], ["04", "Results-en", 1920],
               ["05", "Recursos-pt", 1080], ["06", "Proposito-pt", 1080], ["07", "Placar-pt", 1080], ["08", "Resultados-pt", 1920]];
const b = await chromium.launch();
for (const [n, nome, w] of telas) {
  const p = await b.newPage({ viewport: { width: w, height: 1350 } });
  await p.goto("file://" + path.resolve(src, nome + ".html"));
  await p.waitForLoadState("networkidle"); await p.waitForTimeout(1500);
  await p.screenshot({ path: path.join(out, `${n}_${nome}.png`) }); await p.close();
}
await b.close();
