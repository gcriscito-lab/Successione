"use strict";
// Quadro EF visibile (richiesta del 09/11/2026), dati SINTETICI: nell'elenco dei quadri EF non compare spento («non selezionato»)
// ma come quadro calcolato dal programma; aprendolo si vede il prospetto delle imposte in sola lettura (nessun campo da compilare).
// Uso: node gui_quadro_ef.js [url]  (server sintetico: tests/e2e/server.py, porta 8813)
const assert = require("node:assert/strict");
async function run(page, url = "http://127.0.0.1:8813/?t=t0k") {
  const errori = []; page.on("pageerror", e => errori.push(String(e)));
  page.on("dialog", d => d.dismiss().catch(() => {}));
  await page.setViewportSize({ width: 1910, height: 960 });
  await page.goto(url);
  await page.waitForFunction(() => typeof S !== "undefined" && S.schema && S.pratiche.length);
  const pid = await page.evaluate(() => S.pratiche[0].pratica_id || S.pratiche[0].id);
  await page.evaluate(id => apri(id, "AN"), pid);
  await page.waitForSelector('#albero [data-q="EF"]');

  const voce = await page.evaluate(() => { const v = document.querySelector('#albero [data-q="EF"]');
    return { stato: v.dataset.stato, testo: v.querySelector(".st").textContent, grigio: getComputedStyle(v.querySelector(".nome")).color }; });
  assert.equal(voce.stato, "calcolato", "EF nell'elenco: calcolato, non spento");
  assert.equal(voce.testo, "calcolato dal programma");
  assert.equal(await page.evaluate(() => document.querySelector('#albero [data-q="EE"]').dataset.stato), "calcolato", "anche EE");

  await page.click('#albero [data-q="EF"]');
  await page.waitForFunction(() => /calcolato dal programma/.test(document.querySelector("#vista").textContent)
    && !/Calcolo in corso/.test(document.querySelector("#vista").textContent));
  const vista = await page.evaluate(() => ({
    prospetto: !!document.querySelector("#vista .prospetto-ef"),
    motivo: /non calcolabili/.test(document.querySelector("#vista").textContent),
    campi: [...document.querySelectorAll("#vista input, #vista select:not(.stato-lavoro), #vista textarea")].filter(e => e.offsetParent).map(e => e.outerHTML.slice(0, 160)),   // visibili (i filtri della pagina iniziale restano nascosti)
    nonSelez: /non è selezionato/.test(document.querySelector("#vista").textContent) }));
  assert.ok(vista.prospetto || vista.motivo, "prospetto delle imposte, o il motivo per cui non e' calcolabile");
  assert.deepEqual(vista.campi, [], "sola lettura: nessun campo da compilare");
  assert.equal(vista.nonSelez, false, "nessun invito a selezionare il quadro");
  if (vista.prospetto) {
    const totale = await page.evaluate(() => [...document.querySelectorAll("#vista .prospetto-ef tr")].map(t => t.textContent).find(t => /Totale da versare/.test(t)));
    assert.ok(totale, "riga del totale (EF19)");
  }
  assert.equal(await page.evaluate(() => euroIt("2820")), "2.820 €", "migliaia separate anche a quattro cifre");

  assert.deepEqual(errori, []);
  return { esito: "passato", ambito: "GUI locale, dati sintetici", prospetto: vista.prospetto };
}
module.exports = { run };
if (require.main === module) (async () => {
  const { chromium } = require("playwright");
  const browser = await chromium.launch({ headless: true });
  try { console.log(JSON.stringify(await run(await browser.newPage(), process.argv[2]))); }
  finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
