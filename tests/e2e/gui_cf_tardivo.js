"use strict";
// R01 (revisione 2026-11-05): una risposta /api/codice-fiscale tardiva non deve scrivere nella pratica aperta dopo.
// Uso: node gui_cf_tardivo.js [url]  (server sintetico: tests/e2e/server.py, porta 8813)
const assert = require("node:assert/strict");
async function run(page, url = "http://127.0.0.1:8813/?t=t0k") {
  await page.goto(url);
  await page.waitForFunction(() => typeof S !== "undefined" && S.schema);
  const ids = await page.evaluate(async () => {
    const out = [];
    for (const t of ["CF tardivo A", "CF tardivo B"]) {
      const r = await post("/api/pratiche", { titolo: t, iniziali: [
        { op: "upsert", coll: "persone", id: "p_defunto1", campi: { ruolo: "defunto", cognome: t, nome: "Prova" } }] });
      out.push(r.pratica_id);
    }
    return out;
  });
  await page.evaluate(id => apri(id), ids[0]);
  let release; const gate = new Promise(r => release = r);
  let intercettata; const ricevuta = new Promise(r => intercettata = r);
  await page.route("**/api/codice-fiscale**", async route => { const response = await route.fetch(); intercettata(); await gate; await route.fulfill({ response }); });
  const cf = page.locator('#vista [aria-label="codice_fiscale"]').first();
  await cf.fill("RSSMRA40A01H501K"); await cf.blur();
  await ricevuta;
  page.once("dialog", d => d.accept());
  await page.evaluate(id => apri(id), ids[1]);
  assert.equal(await page.evaluate(() => nMod()), 0);
  release();
  await page.waitForTimeout(500);
  assert.equal(await page.evaluate(() => nMod()), 0, "la risposta tardiva ha sporcato la pratica B");
  await page.unroute("**/api/codice-fiscale**");
  return { esito: "passato", ambito: "GUI locale, dati sintetici" };
}
module.exports = { run };
if (require.main === module) (async () => {
  const { chromium } = require("playwright");
  const browser = await chromium.launch({ headless: true });
  try { console.log(JSON.stringify(await run(await browser.newPage(), process.argv[2]))); }
  finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
