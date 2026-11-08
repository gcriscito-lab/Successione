"use strict";
// Guida (F1): istruzioni ufficiali per argomento, uso del programma, Informazioni con la versione; nel quadro il collegamento
// «Istruzioni del quadro». Uso: node gui_guida.js [url]  (server sintetico: tests/e2e/server.py, porta 8813)
const assert = require("node:assert/strict");
async function run(page, url = "http://127.0.0.1:8813/?t=t0k") {
  const errori = []; page.on("pageerror", e => errori.push(String(e)));
  await page.goto(url);
  await page.waitForFunction(() => typeof S !== "undefined" && S.schema);
  await page.keyboard.press("F1");
  await page.waitForSelector("#dGuida[open] .guida-lista li");
  assert.match(await page.textContent("#dGuida"), /Quadro EC - Fabbricati/);
  await page.fill("#dGuida input[type=search]", "rateale");
  assert.equal(await page.locator("#dGuida .guida-lista").first().locator("li").count(), 1);
  await page.click("#dGuida [role=tab]:has-text('Informazioni')");
  await page.waitForFunction(() => /Regole fiscali/.test(document.querySelector("#dGuida").textContent), null, { timeout: 30000 });
  const info = await page.textContent("#dGuida");
  assert.match(info, /Successioni \d+\.\d+/); assert.match(info, /Novità/);
  const versione = await page.evaluate(async () => (await api("/api/info")).versione);
  assert.ok(info.includes(versione));
  await page.click("#dGuida .wiz-az .pil");
  const pid = await page.evaluate(async () => { const r = await post("/api/pratiche", { titolo: "Prova guida", iniziali: [] }); await apri(r.pratica_id); return r.pratica_id; });
  await page.evaluate(() => scegliQuadro("EC"));
  await page.waitForSelector(".istr-quadro");
  // versione 0.4: le istruzioni si aprono nell'anteprima interna, alla pagina del quadro
  await page.click(".istr-quadro");
  await page.waitForSelector("#dAnteprima[open] iframe.anteprima-doc");
  assert.equal(await page.getAttribute("#dAnteprima iframe", "src"), "/api/guida/fascicolo1.pdf#page=28");
  await page.click("#dAnteprima button:has-text('Chiudi')");
  const pdf = await page.evaluate(async () => { const r = await fetch("/api/guida/fascicolo1.pdf"); return [r.status, r.headers.get("content-type")]; });
  assert.deepEqual(pdf, [200, "application/pdf"]);
  assert.ok(pid);
  assert.deepEqual(errori, []);
  return { esito: "passato", ambito: "GUI locale, dati sintetici" };
}
module.exports = { run };
if (require.main === module) (async () => {
  const { chromium } = require("playwright");
  const browser = await chromium.launch({ headless: true });
  try { console.log(JSON.stringify(await run(await browser.newPage(), process.argv[2]))); }
  finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
