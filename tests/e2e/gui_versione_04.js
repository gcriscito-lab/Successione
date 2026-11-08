"use strict";
// Versione 0.4 «Strumenti di studio», dati SINTETICI: anteprima interna dei documenti, fascicolo per il cliente, Guida > Tabelle
// e fonti, preventivo e parcella, copia anonima, elenco delle pratiche in CSV.
// Uso: node gui_versione_04.js [url]  (server sintetico: tests/e2e/server.py, porta 8813)
const assert = require("node:assert/strict");
async function run(page, url = "http://127.0.0.1:8813/?t=t0k") {
  const errori = []; page.on("pageerror", e => errori.push(String(e)));
  page.on("dialog", d => d.accept());
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto(url);
  await page.waitForFunction(() => typeof S !== "undefined" && S.schema);
  // elenco in CSV dalla pagina iniziale
  await page.waitForSelector("#homeCsv");
  const [scarico] = await Promise.all([page.waitForEvent("download"), page.click("#homeCsv")]);
  assert.match(scarico.suggestedFilename(), /^elenco_pratiche_\d{4}-\d{2}-\d{2}\.csv$/);
  // Guida > Tabelle e fonti: valori letti dai moduli di calcolo, con la fonte
  await page.click("#bGuida");
  await page.click("#guidaTab_tabelle");
  await page.waitForSelector("#tab_aliquote table.tab-valori");
  const tab = await page.textContent("#guidaPannello");
  assert.match(tab, /4%/); assert.match(tab, /1\.000\.000 €/); assert.match(tab, /Fonte:/); assert.match(tab, /Usufrutto vitalizio/);
  await page.click("#dGuida .wiz-az .pil");
  // pratica con un defunto; File e invio > Strumenti di studio
  const pid = await page.evaluate(async () => (await post("/api/pratiche", { titolo: "Studio e2e VERDI", iniziali: [{ op: "upsert", coll: "persone",
    id: "p_" + Math.random().toString(36).slice(2, 12), campi: { ruolo: "defunto", cognome: "VERDI", nome: "LUIGI", codice_fiscale: "VRDLGU50A01H501X", data_decesso: "2025-06-10" } }] })).pratica_id);
  await page.evaluate(async id => { await caricaPratiche(); await apri(id, "FILE"); }, pid);
  await page.waitForSelector("#strumentiStudio");
  // fascicolo: si apre nell'anteprima interna, senza nuova scheda
  await page.click("#strumentiStudio a:has-text('Fascicolo per il cliente')");
  await page.waitForSelector("#dAnteprima[open] iframe.anteprima-doc");
  assert.match(await page.getAttribute("#dAnteprima iframe", "src"), /\/fascicolo\.pdf$/);
  await page.click("#dAnteprima button:has-text('Chiudi')");
  // preventivo: due voci, IVA 22%, anteprima con il totale
  await page.click("#bPreventivo");
  await page.waitForSelector("#dPreventivo[open]");
  await page.fill("#dPreventivo tbody tr:nth-child(1) td:nth-child(1) input", "Dichiarazione di successione");
  await page.fill("#dPreventivo tbody tr:nth-child(1) td:nth-child(2) input", "1.000,00");
  await page.click("#prevAggiungi");
  await page.fill("#dPreventivo tbody tr:nth-child(2) td:nth-child(1) input", "Volture");
  await page.fill("#dPreventivo tbody tr:nth-child(2) td:nth-child(2) input", "200");
  await page.fill("#prevIva", "22"); await page.fill("#prevNumero", "12/2026");
  await page.click("#prevVediParcella");
  await page.waitForSelector("#dAnteprima[open] iframe.anteprima-doc");
  const fr = page.frameLocator("#dAnteprima iframe");
  await fr.locator("h1").waitFor();
  assert.equal(await fr.locator("h1").textContent(), "Parcella n. 12/2026");
  assert.match(await fr.locator("body").textContent(), /1\.464,00 €/);
  await page.click("#dAnteprima button:has-text('Chiudi')");
  const salvato = await page.evaluate(() => S.P.dati.note.preventivo);
  assert.deepEqual(salvato.voci.map(v => v.importo), ["1000.00", "200"]);
  assert.equal(salvato.iva_pct, "22");
  // copia anonima: nuova pratica, l'originale resta aperta e invariata
  const n0 = await page.evaluate(() => S.pratiche.length);
  const rev0 = await page.evaluate(() => S.P.revisione);
  await page.click("#bCopiaAnonima");
  await page.waitForFunction(n => S.pratiche.length === n + 1, n0);
  assert.equal(await page.evaluate(() => S.P.revisione), rev0);
  assert.match(await page.textContent("#msg"), /Creata «Copia anonima/);
  const copia = await page.evaluate(async () => { const p = S.pratiche.find(x => x.titolo.startsWith("Copia anonima"));
    return (await api("/api/pratiche/" + p.id)).dati.persone[0]; });
  assert.equal(copia.cognome, "PERSONA"); assert.notEqual(copia.codice_fiscale, "VRDLGU50A01H501X");
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
