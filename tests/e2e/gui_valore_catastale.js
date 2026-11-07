"use strict";
// Valore catastale (docs/regole/valore_catastale.md): il pannello della riga EC propone il valore con la formula, il pulsante
// lo inserisce come modifica da salvare (mai salvato da solo) e «Ricalcola valori catastali» riempie solo i valori mancanti o
// piu' bassi. Uso: node gui_valore_catastale.js [url]  (server sintetico: tests/e2e/server.py, porta 8813)
const assert = require("node:assert/strict");
async function run(page, url = "http://127.0.0.1:8813/?t=t0k") {
  const errori = []; page.on("pageerror", e => errori.push(String(e)));
  await page.goto(url);
  await page.waitForFunction(() => typeof S !== "undefined" && S.schema);
  const pid = await page.evaluate(async () => {
    const fab = (id, cat, valore) => ({ op: "upsert", coll: "beni", id, campi: { tipo: "fabbricato", comune: "Roma", foglio: "1",
      particella: id.slice(-1), categoria: cat, rendita: "1000.00", diritto: "1", quota_defunto: "1/1", ...(valore ? { valore } : {}) } });
    const r = await post("/api/pratiche", { titolo: "Valore catastale e2e", iniziali: [
      { op: "upsert", coll: "persone", id: "p_defunto1", campi: { ruolo: "defunto", cognome: "Prova", nome: "Catasto", data_decesso: "2025-03-10" } },
      fab("b_fab1", "A/2", "100000"), fab("b_fab2", "C/1", null), fab("b_fab3", "A/2", "300000")] });
    await apri(r.pratica_id);
    return r.pratica_id;
  });
  await page.evaluate(() => scegliQuadro("EC"));
  await page.waitForSelector("#vista tbody tr[data-key]");
  await page.click('#vista tr[data-key="e:beni:b_fab1"]');
  await page.waitForFunction(() => /126\.000/.test((document.querySelector("#ins .vc") || {}).textContent || ""), null, { timeout: 20000 });
  const testo = await page.textContent("#ins .vc");
  assert.match(testo, /1,05/); assert.match(testo, /lettera f/); assert.match(testo, /inferiore/);
  await page.click("#ins .vc button");
  assert.equal(await page.evaluate(() => S.dirty.get("e:beni:b_fab1").campi.valore), "126000");
  const salvato = await page.evaluate(async id => (await api("/api/pratiche/" + id)).dati.beni.find(b => b.id === "b_fab1").valore, pid);
  assert.equal(salvato, "100000", "il valore non deve essere salvato senza «Salva»");
  page.once("dialog", d => d.accept());
  await page.click(".operazioni > summary");
  await page.click("text=Ricalcola valori catastali");
  await page.waitForFunction(() => S.dirty.has("e:beni:b_fab2"));
  const campi = await page.evaluate(() => ({ b2: S.dirty.get("e:beni:b_fab2").campi.valore, b3: S.dirty.has("e:beni:b_fab3") }));
  assert.equal(campi.b2, "42840");          // C/1: 1000 x 1,05 x 40,80
  assert.equal(campi.b3, false, "un valore piu' alto del catastale resta com'e'");
  await page.evaluate(() => salvaTutto());
  await page.waitForFunction(() => S.dirty.size === 0, null, { timeout: 20000 });
  const dopo = await page.evaluate(async id => (await api("/api/pratiche/" + id)).dati.beni.map(b => [b.id, b.valore]), pid);
  assert.deepEqual(Object.fromEntries(dopo), { b_fab1: "126000", b_fab2: "42840", b_fab3: "300000" });
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
