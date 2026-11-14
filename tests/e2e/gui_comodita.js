"use strict";
// Piccole comodita' (15/11/2026), dati SINTETICI: carica visura (PDF sintetico in tests/fixture_catasto), ordina e sposta gli
// immobili, cerca immobile, duplica la pratica, rubrica dello studio con la scelta nel fornitore, ricerca delle ricevute nei
// download (su una cartella di prova vuota, mai quella vera), illustrazioni degli stati vuoti.
// Uso: node gui_comodita.js [url]  (server sintetico: tests/e2e/server.py, porta 8813)
const assert = require("node:assert/strict");
const path = require("node:path"), fs = require("node:fs"), os = require("node:os");
async function run(page, url = "http://127.0.0.1:8813/?t=t0k") {
  const errori = []; page.on("pageerror", e => errori.push(String(e)));
  page.on("dialog", d => d.accept().catch(() => {}));
  const vuota = fs.mkdtempSync(path.join(os.tmpdir(), "ricevute-e2e-"));
  await page.route("**/api/ricevute-cartella*", r => r.continue({ url: new URL(url).origin + "/api/ricevute-cartella?cartella=" + encodeURIComponent(vuota) }));
  await page.setViewportSize({ width: 1910, height: 1000 });
  await page.goto(url);
  await page.waitForFunction(() => typeof S !== "undefined" && S.schema);
  const pid = await page.evaluate(async () => (await post("/api/pratiche", { titolo: "Comodita e2e", iniziali: [
    { op: "upsert", coll: "persone", id: "p_defcom001", campi: { ruolo: "defunto", cognome: "Rossi", nome: "Mario", codice_fiscale: "RSSMRA40A01H501K", data_decesso: "2025-03-10" } },
    { op: "upsert", coll: "persone", id: "p_erecom001", campi: { ruolo: "erede", cognome: "Rossi", nome: "Anna" } }] })).pratica_id);
  await page.evaluate(id => apri(id, "EC"), pid);
  await page.waitForSelector("#vista .vuoto-illustrato img[src$='vuoto_beni.svg']");

  // visura: dall'illustrazione del quadro vuoto
  await page.click("#vista .vuoto-illustrato button"); await page.waitForSelector("#dVisura");
  await page.waitForSelector("#dVisura img[src$='vuoto_visura.svg']");   // illustrazione prima del caricamento
  await page.setInputFiles("#visuraFile", path.join(__dirname, "..", "fixture_catasto", "risultanze_fabbricati_sintetico.pdf"));
  await page.waitForSelector("#dVisura tbody tr");
  const avvisi = await page.$$eval("#dVisura .visura-avvisi li", l => l.map(x => x.textContent));
  assert.equal(new Set(avvisi).size, avvisi.length, "avvisi della visura senza doppioni");
  const scelte = await page.$$eval("#dVisura tbody input[type=checkbox]:checked", l => l.length);
  assert.ok(scelte >= 1, "gli immobili nuovi sono gia' spuntati");
  await page.click("#dVisura >> text=Aggiungi gli immobili scelti");
  await page.waitForFunction(() => !document.getElementById("dVisura"));
  await page.waitForFunction(n => document.querySelectorAll("#vista tbody tr[data-key]").length === n, scelte);

  // ordina e cerca
  await page.evaluate(() => ordinaBeni(quadro()));
  await page.waitForFunction(() => /ordinati/.test(document.querySelector("#msg").textContent));
  const comuni = await page.$$eval("#vista tbody tr[data-key] td:first-child", l => l.map(x => x.textContent.trim().toUpperCase()));
  assert.deepEqual(comuni, [...comuni].sort(), "ordinati per comune");
  await page.fill(".cerca-beni", "tivoli");
  const vis = await page.$$eval("#vista tbody tr[data-key]", l => l.filter(x => !x.hidden).map(x => x.textContent.toUpperCase()));
  assert.ok(vis.length > 0 && vis.every(t => t.includes("TIVOLI")), "la ricerca filtra le righe");
  await page.fill(".cerca-beni", ""); await page.evaluate(() => { S.cercaBeni = ""; });

  // sposta su con Alt+freccia
  await page.click("#vista tbody tr[data-key] >> nth=1");
  const chiave = await page.evaluate(() => S.riga);
  await page.evaluate(() => document.querySelector("#vista tbody tr[aria-selected=true]").focus());
  await page.keyboard.press("Alt+ArrowUp");
  await page.waitForFunction(k => document.querySelector("#vista tbody tr[data-key]").dataset.key === k, chiave);

  // rubrica e scelta nel fornitore
  await page.evaluate(() => impApri()); await page.waitForSelector("#impRubrica");
  await page.click("#impRubrica >> text=Aggiungi alla rubrica");
  await page.fill('#impRubrica tbody tr:last-child input[aria-label="Nome"]', "Intermediario di prova");
  await page.fill('#impRubrica tbody tr:last-child input[aria-label="Codice fiscale"]', "12345678901");
  await page.click("#iSalva"); await page.waitForFunction(() => /salvate/.test(document.querySelector("#msg").textContent));
  await page.evaluate(() => $("#imp").close());
  await page.click("#navFile"); await page.waitForSelector(".da-rubrica option:nth-child(2)", { state: "attached" });
  await page.selectOption(".da-rubrica", { index: 1 });
  assert.equal(await page.inputValue('[aria-label="Codice fiscale del fornitore"]'), "12345678901");
  assert.equal(await page.inputValue('[aria-label="Tipo fornitore"]'), "10");

  // ricevute nei download (cartella di prova vuota): illustrazione e nessun elenco
  await page.click("text=Cerca nei download");
  await page.waitForSelector(".ricevute-download img[src$='vuoto_ricevute.svg']");

  // duplica la pratica (le modifiche al fornitore si salvano prima, con conferma)
  await page.evaluate(() => duplicaPratica()); await page.waitForSelector("#dDuplica");
  await page.click("#dDuplica .pil");
  await page.waitForFunction(p => S.P && S.P.pratica_id !== p, pid, { timeout: 15000 });
  assert.match(await page.evaluate(() => S.P.titolo), /^Copia di Comodita e2e/);

  assert.deepEqual(errori, []);
  fs.rmSync(vuota, { recursive: true, force: true });
  return { esito: "passato", ambito: "GUI locale, dati sintetici", immobili_da_visura: scelte };
}
module.exports = { run };
if (require.main === module) (async () => {
  const { chromium } = require("playwright");
  const browser = await chromium.launch({ headless: true });
  try { console.log(JSON.stringify(await run(await browser.newPage(), process.argv[2]))); }
  finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
