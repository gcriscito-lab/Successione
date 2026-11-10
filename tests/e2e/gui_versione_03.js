"use strict";
// Versione 0.3 (report grafico DEAS 08/11/2026, proposte 1, 2, 5, 6), dati SINTETICI, finestra 1366x768:
// pannello sotto l'elenco con separatore orizzontale, scheda compatta, vista unica degli immobili, Alt+1…9, Invio al campo
// successivo. Le preferenze toccate tornano ai valori predefiniti alla fine.
// Uso: node gui_versione_03.js [url]  (server sintetico: tests/e2e/server.py, porta 8813)
const assert = require("node:assert/strict");
async function run(page, url = "http://127.0.0.1:8813/?t=t0k") {
  const errori = []; page.on("pageerror", e => errori.push(String(e)));
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto(url);
  await page.waitForFunction(() => typeof S !== "undefined" && S.schema);
  const pref = v => page.evaluate(async v => { const r = await post("/api/impostazioni", { interfaccia: v }); memorizzaAspetto(r.interfaccia); render(); }, v);
  await pref({ disposizione: "destra", densita: "normale" });
  const pid = await page.evaluate(async () => {
    const fab = (id, p) => ({ op: "upsert", coll: "beni", id, campi: { tipo: "fabbricato", comune: "Roma", foglio: "3", particella: p,
      categoria: "A/2", rendita: "300.00", diritto: "1", quota_defunto: "1/1", valore: "37800" } });
    const r = await post("/api/pratiche", { titolo: "Versione 0.3 e2e", iniziali: [
      { op: "upsert", coll: "persone", id: "p_defunto03", campi: { ruolo: "defunto", cognome: "Prova", nome: "Densita", data_decesso: "2025-07-01" } },
      { op: "upsert", coll: "persone", id: "p_erede0301", campi: { ruolo: "erede", cognome: "NERI", nome: "LUCIA" } },
      fab("b_fab030001", "31"), fab("b_fab030002", "32"),
      { op: "upsert", coll: "beni", id: "b_ter030001", campi: { tipo: "terreno", comune: "Roma", foglio: "9", particella: "77", reddito_dominicale: "12.50",
        diritto: "1", quota_defunto: "1/1", valore: "1350" } }] });
    await apri(r.pratica_id); return r.pratica_id;
  });
  const misura = () => page.evaluate(() => {
    const v = document.querySelector("#vista").getBoundingClientRect(), i = document.querySelector("#ins").getBoundingClientRect();
    return { vista: { x: Math.round(v.x), y: Math.round(v.y), w: Math.round(v.width), h: Math.round(v.height) },
      ins: { x: Math.round(i.x), y: Math.round(i.y), w: Math.round(i.width), h: Math.round(i.height) }, alto: document.querySelector("#ins").scrollHeight };
  });

  // 1. disposizione predefinita: pannello a destra; scheda dell'immobile alta (riferimento)
  await page.evaluate(() => scegliQuadro("EC"));
  await page.click('#vista tr[data-key="e:beni:b_fab030001"]');
  await page.waitForSelector("#ins .gruppi-scheda");
  const destra = await misura();
  assert.ok(destra.ins.x > destra.vista.x + destra.vista.w - 5, "pannello a destra: " + JSON.stringify(destra));

  // 2. pannello sotto + scheda compatta
  await pref({ disposizione: "sotto", densita: "compatta" });
  await page.waitForFunction(() => document.documentElement.dataset.disposizione === "sotto");
  const sotto = await misura();
  assert.ok(sotto.ins.y >= sotto.vista.y + sotto.vista.h - 2, "pannello sotto: " + JSON.stringify(sotto));
  assert.ok(Math.abs(sotto.ins.w - sotto.vista.w) < 4 && sotto.ins.w > 1000, "a tutta larghezza: " + JSON.stringify(sotto));
  assert.ok(sotto.alto < destra.alto * 0.6, `scheda piu' bassa: ${sotto.alto} contro ${destra.alto}`);
  const sep = await page.$eval("#ridimensiona", s => [s.getAttribute("aria-orientation"), s.getAttribute("aria-label")]);
  assert.deepEqual(sep, ["horizontal", "Altezza pannello dati"]);
  // aiuto (10/11/2026): mai sotto il campo, nemmeno entrandoci; il testo resta nel suggerimento dell'etichetta e nella
  // descrizione accessibile del campo
  const aiuto = await page.evaluate(() => { const rg = document.querySelector("#ins .rg.con-aiuto"); return rg && getComputedStyle(rg.querySelector(".aiuto-voce")).display; });
  assert.equal(aiuto, "none");
  await page.focus("#ins .rg.con-aiuto input, #ins .rg.con-aiuto select");
  const nelTitolo = await page.evaluate(() => { const rg = document.activeElement.closest(".rg"), a = rg.querySelector(".aiuto-voce");
    return { nascosto: getComputedStyle(a).display === "none", titolo: rg.querySelector("label").title.includes(a.textContent),
      descritto: (document.activeElement.getAttribute("aria-describedby") || "").split(/\s+/).includes(a.id) }; });
  assert.deepEqual(nelTitolo, { nascosto: true, titolo: true, descritto: true });
  // separatore da tastiera: Freccia su allarga il pannello (altezza salvata)
  const h0 = await page.evaluate(() => preferenze.altezza_pannello);
  const salvata = page.waitForResponse(r => r.url().includes("/api/impostazioni") && r.request().method() === "POST");
  await page.focus("#ridimensiona"); await page.keyboard.press("ArrowUp"); await salvata;
  assert.equal(await page.evaluate(() => preferenze.altezza_pannello), h0 + 16);

  // 3. vista unica degli immobili: EC ed EB insieme, la riga di un altro quadro porta il pannello su quel quadro
  await page.waitForSelector(".linguette-immobili");
  await page.click(".linguette-immobili button:first-child");
  await page.waitForSelector('#vista tr[data-key="e:beni:b_ter030001"]');
  const righe = await page.$$eval("#vista tbody tr[data-key]", trs => trs.map(t => [t.dataset.key.split(":").pop(), t.querySelector(".sigla-mini").textContent]));
  assert.deepEqual(righe, [["b_fab030001", "EC"], ["b_fab030002", "EC"], ["b_ter030001", "EB"]]);
  assert.match(await page.textContent("#vista tfoot"), /76\.950/);   // 37.800 + 37.800 + 1.350: totale di tutti gli immobili
  await page.click('#vista tr[data-key="e:beni:b_ter030001"]');
  assert.equal(await page.evaluate(() => S.sel), "EB");
  assert.ok(await page.evaluate(() => S.immobiliTutti), "la vista unica resta attiva");
  assert.match(await page.textContent("#ins"), /Terreno/);

  // 4. Invio passa al campo successivo nella scheda
  const primo = await page.evaluate(() => { const c = [...document.querySelectorAll("#ins .rg input:not([type=checkbox])")].filter(x => x.getClientRects().length); c[0].focus(); return c[0].dataset.path; });
  await page.keyboard.press("Enter");
  const dopo = await page.evaluate(() => document.activeElement.dataset.path || document.activeElement.tagName);
  assert.notEqual(dopo, primo, "Invio sposta il fuoco");
  assert.equal(await page.evaluate(() => S.dirty.size), 0, "Invio non modifica e non salva");

  // 5. Alt+2: seconda voce dell'elenco dei quadri
  await page.locator("#vista").click({ position: { x: 5, y: 5 } });
  const seconda = await page.evaluate(() => vociElenco()[1].id);
  await page.keyboard.press("Alt+2");
  await page.waitForFunction(id => S.sel === id, seconda);
  assert.match(await page.getAttribute('.voce[data-q="' + seconda + '"]', "title"), /Alt\+2/);

  await pref({ disposizione: "destra", densita: "normale", altezza_pannello: 380 });
  assert.deepEqual(errori, []);
  return { esito: "passato", ambito: "GUI locale, dati sintetici", misure: { destra: destra.alto, sotto_compatta: sotto.alto } };
}
module.exports = { run };
if (require.main === module) (async () => {
  const { chromium } = require("playwright");
  const browser = await chromium.launch({ headless: true });
  try { console.log(JSON.stringify(await run(await browser.newPage(), process.argv[2]))); }
  finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
