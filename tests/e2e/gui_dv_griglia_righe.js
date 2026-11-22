"use strict";
// Quadro DV con la griglia aperta per prima (22/11/2026), dati SINTETICI. I comandi che puntano a una riga di devoluzione
// (Alt+N, «Vai al dato») aprono l'elenco con la riga visibile e il pannello, invece di lasciare la riga invisibile dietro la
// griglia. Eliminare un bene o un soggetto toglie anche le sue quote, con conferma.
// Uso: node gui_dv_griglia_righe.js [url]  (server sintetico: tests/e2e/server.py, porta 8813)
const assert = require("node:assert/strict");
async function run(page, url = "http://127.0.0.1:8813/?t=t0k") {
  const errori = []; page.on("pageerror", e => errori.push(String(e)));
  const conferme = []; page.on("dialog", d => { conferme.push(d.message()); d.accept().catch(() => {}); });
  await page.setViewportSize({ width: 1910, height: 1000 });
  await page.goto(url);
  await page.waitForFunction(() => typeof S !== "undefined" && S.schema);
  await page.evaluate(() => { try { localStorage.removeItem("successioni.vistaDV"); } catch (_) { /* facoltativo */ } });
  await page.reload();
  await page.waitForFunction(() => typeof S !== "undefined" && S.schema);
  const pid = await page.evaluate(async () => (await post("/api/pratiche", { titolo: "DV griglia e2e", iniziali: [
    { op: "upsert", coll: "persone", id: "p_defdvg001", campi: { ruolo: "defunto", cognome: "Rossi", nome: "Mario", codice_fiscale: "RSSMRA40A01H501K", data_decesso: "2025-03-10" } },
    { op: "upsert", coll: "persone", id: "p_eredvg001", campi: { ruolo: "erede", cognome: "Rossi", nome: "Anna" } },
    { op: "upsert", coll: "persone", id: "p_eredvg002", campi: { ruolo: "erede", cognome: "Rossi", nome: "Luca" } },
    { op: "upsert", coll: "beni", id: "b_casadvg01", campi: { tipo: "fabbricato", comune: "Roma", foglio: "1", particella: "2", diritto: "1", quota_defunto: "1/1", valore: "100000" } },
    { op: "upsert", coll: "beni", id: "b_terrdvg01", campi: { tipo: "terreno", comune: "Tivoli", foglio: "3", particella: "4", diritto: "1", quota_defunto: "1/1", valore: "8000" } },
    { op: "upsert", coll: "devoluzioni", id: "d_casadvga", campi: { bene_id: "b_casadvg01", persona_id: "p_eredvg001", diritto: "1", quota: "1/2" } },
    { op: "upsert", coll: "devoluzioni", id: "d_casadvgl", campi: { bene_id: "b_casadvg01", persona_id: "p_eredvg002", diritto: "1", quota: "1/2" } },
    { op: "upsert", coll: "devoluzioni", id: "d_terrdvga", campi: { bene_id: "b_terrdvg01", persona_id: "p_eredvg001", diritto: "1", quota: "1/2" } }] })).pratica_id);
  await page.evaluate(id => apri(id, "DV"), pid);
  const pannelloAperto = () => page.evaluate(() => { const i = document.getElementById("ins"); return !i.hidden && i.offsetWidth > 0; });

  // la griglia e' la vista predefinita del quadro DV
  await page.waitForSelector("#vista .tab-griglia");
  assert.equal(await page.evaluate(() => S.vistaDV), "griglia");

  // Alt+N con la griglia aperta: si passa all'elenco, la riga nuova si vede e il pannello e' aperto
  await page.click("#vista .testa-quadro h1");
  await page.keyboard.press("Alt+n");
  await page.waitForFunction(() => S.nuove.size === 1);
  await page.waitForSelector("#vista table:not(.tab-griglia) tbody tr[data-key]");
  assert.equal(await page.evaluate(() => S.vistaDV), "elenco");
  assert.ok(await page.evaluate(() => !!document.querySelector('#vista tr[data-key="' + CSS.escape(S.riga) + '"]')), "riga nuova visibile");
  assert.ok(await pannelloAperto(), "pannello della riga nuova aperto");
  assert.equal(await page.evaluate(() => localStorage.getItem("successioni.vistaDV")), null, "la scelta della griglia non viene sovrascritta");
  await page.evaluate(() => { S.nuove.clear(); S.riga = null; cambiaVistaDV("griglia"); });
  await page.waitForSelector("#vista .tab-griglia");

  // «Vai al dato» su un campo di una riga di devoluzione (come un errore di salvataggio o di esportazione) con la griglia aperta.
  // Il rilievo DEVOLUZIONI_INCOMPLETE ha invece il percorso «devoluzioni[bene=…,diritto=…]», che non indica una riga: non e'
  // coperto qui (segnalato a parte).
  await page.evaluate(() => vaiA({ quadro: "DV", percorso: "devoluzioni[d_terrdvga].quota", messaggio: "prova" }));
  await page.waitForSelector("#vista table:not(.tab-griglia) tbody tr[aria-selected=true]");
  const chiave = await page.evaluate(() => S.riga);
  assert.match(chiave, /^e:devoluzioni:/);
  assert.ok(await pannelloAperto(), "pannello della riga del rilievo aperto");
  assert.ok(await page.evaluate(k => document.querySelector("#vista tr[aria-selected=true]").dataset.key === k, chiave), "riga del rilievo selezionata");

  // eliminare un bene con quote: conferma che le nomina e le toglie nella stessa revisione
  const rev = await page.evaluate(() => S.P.revisione);
  await page.evaluate(() => { S.immobiliTutti = false; scegliQuadro("EB"); });
  await page.click('#vista tbody tr[data-key="e:beni:b_terrdvg01"]');
  conferme.length = 0;
  await page.evaluate(() => eliminaRigaSelezionata(quadro()));
  await page.waitForFunction(r => S.P.revisione === r + 1, rev);
  assert.match(conferme.join("\n"), /1 quota di devoluzione/);
  const dopoBene = await page.evaluate(() => ({ beni: S.P.dati.beni.map(b => b.id), dv: S.P.dati.devoluzioni.map(d => d.id) }));
  assert.deepEqual(dopoBene.beni, ["b_casadvg01"]);
  assert.deepEqual(dopoBene.dv.sort(), ["d_casadvga", "d_casadvgl"]);

  // eliminare un soggetto con quote: stesse regole
  await page.evaluate(() => scegliQuadro("EA"));
  await page.click('#vista tbody tr[data-key="e:persone:p_eredvg002"]');
  conferme.length = 0;
  await page.evaluate(() => eliminaRigaSelezionata(quadro()));
  await page.waitForFunction(r => S.P.revisione === r + 2, rev);
  assert.match(conferme.join("\n"), /1 quota di devoluzione/);
  assert.deepEqual(await page.evaluate(() => S.P.dati.devoluzioni.map(d => d.id)), ["d_casadvga"]);

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
