"use strict";
// Griglia delle quote, agevolazioni guidate e scadenza nella pratica (15/11/2026, layout ripreso da DEAS), dati SINTETICI.
// Uso: node gui_griglia_quote.js [url]  (server sintetico: tests/e2e/server.py, porta 8813)
const assert = require("node:assert/strict");
async function run(page, url = "http://127.0.0.1:8813/?t=t0k") {
  const errori = []; page.on("pageerror", e => errori.push(String(e)));
  page.on("dialog", d => d.accept().catch(() => {}));
  await page.setViewportSize({ width: 1910, height: 1000 });
  await page.goto(url);
  await page.waitForFunction(() => typeof S !== "undefined" && S.schema);
  const decesso = await page.evaluate(() => { const d = new Date(); d.setMonth(d.getMonth() - 2); return isoData(d); });
  const pid = await page.evaluate(async dd => (await post("/api/pratiche", { titolo: "Griglia e2e", iniziali: [
    { op: "upsert", coll: "persone", id: "p_defgri001", campi: { ruolo: "defunto", cognome: "Rossi", nome: "Mario", codice_fiscale: "RSSMRA40A01H501K", data_decesso: dd } },
    { op: "upsert", coll: "persone", id: "p_eregri001", campi: { ruolo: "erede", cognome: "Rossi", nome: "Anna" } },
    { op: "upsert", coll: "persone", id: "p_eregri002", campi: { ruolo: "erede", cognome: "Rossi", nome: "Luca" } },
    { op: "upsert", coll: "beni", id: "b_casagri01", campi: { tipo: "fabbricato", comune: "Roma", foglio: "1", particella: "2", diritto: "1", quota_defunto: "1/1", valore: "100000" } },
    { op: "upsert", coll: "beni", id: "b_terrgri01", campi: { tipo: "terreno", comune: "Tivoli", foglio: "3", particella: "4", diritto: "1", quota_defunto: "1/2", valore: "8000" } },
    { op: "upsert", coll: "devoluzioni", id: "d_usufgri01", campi: { bene_id: "b_casagri01", persona_id: "p_eregri001", diritto: "8", quota: "1/1" } },
    { op: "upsert", coll: "devoluzioni", id: "d_nudagri01", campi: { bene_id: "b_casagri01", persona_id: "p_eregri002", diritto: "2", quota: "1/1" } }] })).pratica_id, decesso);
  await page.evaluate(id => apri(id, "DV"), pid);

  // scadenza accanto al titolo: dal server (/termine), circa dieci mesi dopo
  await page.waitForFunction(() => !document.getElementById("terminePratica").hidden);
  assert.match(await page.textContent("#terminePratica"), /^Presentare entro \d\d\/\d\d\/\d{4} · tra \d+ giorni$/);

  // griglia: usufrutto e nuda proprieta' della casa su due righe, il terreno senza devoluzioni una volta
  await page.click(".seg-vista >> text=Griglia delle quote");
  await page.waitForSelector(".tab-griglia tbody tr");
  assert.equal(await page.locator(".tab-griglia tbody tr").count(), 3);
  assert.equal(await page.evaluate(() => S.vistaDV), "griglia");
  assert.ok(await page.$("#ins[hidden]") || !(await page.isVisible("#ins")), "nessun pannello della riga accanto alla griglia");
  const esiti = await page.$$eval(".tab-griglia .c-esito", l => l.map(x => x.textContent.trim()));
  assert.deepEqual(esiti, ["completa", "completa", "nessuna quota"]);

  // quote del terreno: somma ed esito si aggiornano mentre si scrive; una quota sbagliata si segnala
  const cella = (r, p) => `.tab-griglia input.cella-quota[data-r="${r}"][data-c="${p}"]`;
  await page.fill(cella(2, "p_eregri001"), "1/2");
  assert.equal(await page.textContent(".tab-griglia tbody tr:nth-child(3) .c-esito"), "manca 1/2");
  await page.fill(cella(2, "p_eregri002"), "abc");
  assert.equal(await page.getAttribute(cella(2, "p_eregri002"), "aria-invalid"), "true");
  await page.fill(cella(2, "p_eregri002"), "1/2");
  assert.equal(await page.textContent(".tab-griglia tbody tr:nth-child(3) .c-esito"), "completa");
  assert.equal(await page.isDisabled("#bSalva"), false, "le quote della griglia contano come modifiche da salvare");
  await page.click("text=Salva le quote");
  await page.waitForFunction(() => /Quote salvate/.test(document.querySelector("#msg").textContent));
  const devs = await page.evaluate(() => S.P.dati.devoluzioni.filter(d => d.bene_id === "b_terrgri01").length);
  assert.equal(devs, 2, "due righe di devoluzione create per il terreno");

  // stessa ripartizione su piu' righe: scelgo le due righe della casa e tolgo Luca da entrambe (poi annullo)
  await page.waitForSelector(".tab-griglia tbody tr:nth-child(3) input.sc-riga");
  await page.check(".tab-griglia tbody tr:nth-child(1) input.sc-riga"); await page.check(".tab-griglia tbody tr:nth-child(3) input.sc-riga");
  await page.click("text=Stessa ripartizione sulle righe scelte…"); await page.waitForSelector("#dRipartizione");
  await page.fill('#dRipartizione input[aria-label="Quota di Rossi Anna"]', "1/1");
  await page.fill('#dRipartizione input[aria-label="Quota di Rossi Luca"]', "");
  await page.click("#dRipartizione >> text=Applica alle righe");
  await page.waitForFunction(() => !document.getElementById("dRipartizione") || !document.getElementById("dRipartizione").open);
  assert.equal(await page.inputValue(cella(2, "p_eregri001")), "1/1");
  assert.equal(await page.inputValue(cella(2, "p_eregri002")), "");
  await page.click("text=Annulla le modifiche");
  assert.equal(await page.inputValue(cella(2, "p_eregri002")), "1/2");

  // agevolazioni guidate: P solo per i fabbricati (EC); i beneficiari della casa sono gia' scelti
  await page.click("#vista details.operazioni > summary"); await page.click("text=Agevolazioni guidate…");
  await page.waitForSelector("#dAgevolazioni");
  await page.check('#dAgevolazioni input[value="P"]'); await page.click("#dAgevolazioni >> text=Avanti");
  const beni = await page.$$eval("#dAgevolazioni .agev-elenco label", l => l.map(x => x.textContent.trim()));
  assert.equal(beni.length, 1); assert.match(beni[0], /^EC · /);
  await page.check("#dAgevolazioni .agev-elenco input"); await page.click("#dAgevolazioni >> text=Avanti");
  assert.equal(await page.locator("#dAgevolazioni .agev-elenco input:checked").count(), 2);
  await page.click("#dAgevolazioni >> text=Fine");
  await page.waitForFunction(() => /Codice P indicato su 2 righe/.test(document.querySelector("#msg").textContent));
  await page.waitForSelector(".tab-griglia .ag-cella");

  // ritorno all'elenco
  await page.click(".seg-vista >> text=Elenco");
  await page.waitForSelector("#vista table:not(.tab-griglia) tbody tr[data-key]");
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
