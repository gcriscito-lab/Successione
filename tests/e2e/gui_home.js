"use strict";
// Pagina iniziale con un solo elenco (revisione dell'08/11/2026), dati SINTETICI: riepilogo, filtri a pulsanti con i conteggi,
// ricerca, ordine per urgenza, avanzamento e prossima azione per ogni pratica; colonna dei quadri e comandi della pratica
// nascosti sulla pagina iniziale e di nuovo visibili aprendo una pratica.
// Uso: node gui_home.js [url]  (server sintetico: tests/e2e/server.py, porta 8813)
const assert = require("node:assert/strict");
async function run(page, url = "http://127.0.0.1:8813/?t=t0k") {
  const errori = []; page.on("pageerror", e => errori.push(String(e)));
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto(url);
  await page.waitForFunction(() => typeof S !== "undefined" && S.schema);
  const ids = await page.evaluate(async () => {
    const d = n => { const x = new Date(); x.setFullYear(x.getFullYear() - 1); x.setDate(x.getDate() + n); return x.toISOString().slice(0, 10); };
    const crea = async (titolo, dec) => (await post("/api/pratiche", { titolo, iniziali: [{ op: "upsert", coll: "persone",
      id: "p_" + Math.random().toString(36).slice(2, 12), campi: { ruolo: "defunto", cognome: "HOME", nome: titolo.split(" ").pop().toUpperCase(), ...(dec ? { data_decesso: dec } : {}) } }] })).pratica_id;
    const r = { vicina: await crea("Home e2e Vicina", d(10)), lontana: await crea("Home e2e Lontana", d(200)),
      superata: await crea("Home e2e Superata", d(-5)), senza: await crea("Home e2e Senzadata", null) };
    await caricaPratiche(); return r;
  });
  // colonna dei quadri e comandi della pratica nascosti sulla pagina iniziale
  const vis = sel => page.evaluate(s => { const e = document.querySelector(s); return !!e && e.getClientRects().length > 0; }, sel);
  assert.equal(await vis("#lat"), false, "colonna a sinistra nascosta"); assert.equal(await vis("#bSalva"), false); assert.equal(await vis("#bControlla"), false);
  await page.waitForSelector("#elencoPratiche .lk-azione");
  assert.match(await page.textContent("#homeIntro"), /\d+ pratiche · \d+ da lavorare/);
  // filtro «Termine superato» con il conteggio, poi ricerca
  await page.fill("#homeFiltri input[type=search]", "Home e2e");
  let righe = await page.$$eval("#elencoPratiche tbody tr", t => t.map(x => x.dataset.pratica));
  assert.deepEqual(righe, [ids.superata, ids.vicina, ids.lontana, ids.senza], "ordine per urgenza: superata, vicina, lontana, senza data");
  const chip = page.locator("#homeFiltri .chip", { hasText: "Termine superato" });
  assert.match(await chip.textContent(), /\d+$/);
  await chip.click();
  righe = await page.$$eval("#elencoPratiche tbody tr", t => t.map(x => x.dataset.pratica));
  assert.deepEqual(righe, [ids.superata]);
  assert.equal(await chip.getAttribute("aria-pressed"), "true");
  await page.locator("#homeFiltri .chip", { hasText: "Tutte" }).click();
  await page.selectOption("#homeFiltri select", "nome");
  righe = await page.$$eval("#elencoPratiche tbody tr", t => t.map(x => x.dataset.pratica));
  assert.deepEqual(righe, [ids.lontana, ids.senza, ids.superata, ids.vicina], "ordine per nome");
  // riga: termine, avanzamento in cinque tappe e prossima azione
  const riga = page.locator(`#elencoPratiche tr[data-pratica="${ids.vicina}"]`);
  assert.match(await riga.locator(".c-term").textContent(), /tra 10 giorni/);
  assert.equal(await riga.locator(".tappe-mini .tm").count(), 5);
  assert.equal(await page.locator(`#elencoPratiche tr[data-pratica="${ids.senza}"] .c-term`).textContent(), "da indicare");
  // la prossima azione apre la pratica nel punto indicato; la colonna dei quadri torna visibile
  await riga.locator(".lk-azione").click();
  await page.waitForFunction(id => S.P && S.P.pratica_id === id && !document.body.classList.contains("in-home"), ids.vicina);
  assert.equal(await vis("#lat"), true, "colonna a sinistra visibile con la pratica aperta"); assert.equal(await vis("#bSalva"), true);
  await page.click("#bHome");
  await page.waitForSelector("#elencoPratiche .apri-pratica");
  await page.fill("#homeFiltri input[type=search]", ""); await page.selectOption("#homeFiltri select", "urgenza");
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
