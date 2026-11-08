"use strict";
// Calcolatrice rapida: pulsante nella pagina iniziale, nella barra e nella Guida; stima aggiornata mentre si scrive (caso del
// confronto col compilatore ufficiale: due fratelli, fabbricato 300.000, decesso 10/03/2025); nessuna pratica creata dalla stima;
// «Crea una pratica da questi dati» compila la procedura guidata. Uso: node gui_calcolatrice.js [url] (server sintetico, porta 8813)
const assert = require("node:assert/strict");
async function run(page, url = "http://127.0.0.1:8813/?t=t0k") {
  const errori = []; page.on("pageerror", e => errori.push(String(e)));
  await page.goto(url);
  await page.waitForFunction(() => typeof S !== "undefined" && S.schema);
  const pratiche = async () => (await page.evaluate(async () => await api("/api/pratiche"))).length;
  const prima = await pratiche();
  assert.ok(await page.isVisible("#bCalc"), "pulsante Calcolatrice nella barra");
  await page.click("#homeCalc");
  await page.waitForSelector("#dCalc[open] #calcData");
  assert.match(await page.textContent("#calcRis"), /Stima: non sostituisce la dichiarazione né il controllo ufficiale/);
  await page.fill("#calcData", "2025-03-10");
  await page.selectOption(".calc-erede >> nth=0 >> select", "10");
  await page.click("#calcDati button:has-text('Aggiungi erede')");
  await page.selectOption(".calc-erede >> nth=1 >> select", "10");
  await page.click("#calcDati button:has-text('Aggiungi immobile')");
  await page.fill(".calc-immobile >> nth=0 >> input[aria-label=Valore]", "300.000");
  await page.waitForFunction(() => (document.querySelector("#calcTotale") || {}).textContent === "15.805 €", null, { timeout: 30000 });
  const ris = await page.textContent("#calcRis");
  for (const t of ["Imposta di successione", "6.600 €", "6.000 €", "3.000 €", "120 €", "85 €", "Franchigia 100.000 €", "aliquota 6%"])
    assert.ok(ris.includes(t), "risultato: " + t + " | " + ris);
  assert.match(ris, /Stima: non sostituisce la dichiarazione né il controllo ufficiale/);
  // la quota di legge e' proposta come segnaposto
  assert.equal(await page.getAttribute(".calc-erede >> nth=0 >> input.q", "placeholder"), "1/2");
  // il campo quota contiene per intero il segnaposto «di legge» (review del 07/11/2026 sera)
  assert.ok(await page.evaluate(() => {
    const el = document.querySelector(".calc-erede input.q"), c = document.createElement("canvas").getContext("2d");
    c.font = getComputedStyle(el).font; return c.measureText("di legge").width + 8 <= el.clientWidth;
  }), "campo quota abbastanza largo per «di legge»");
  // passivita': predefinita 12 (nessun bene di riferimento); il mutuo (3) chiede l'immobile; importi con i centesimi
  await page.click("#calcDati button:has-text('Aggiungi passività')");
  assert.equal(await page.inputValue(".calc-passivita >> nth=0 >> select"), "12");
  assert.equal(await page.locator(".calc-passivita select.calc-cespite").count(), 0);
  await page.fill(".calc-passivita >> nth=0 >> input[aria-label=Importo]", "1.234,56");
  await page.fill(".calc-immobile >> nth=0 >> input[aria-label=Valore]", "300.000,50");
  await page.waitForFunction(() => /Importi arrotondati/.test(document.querySelector("#calcRis").textContent), null, { timeout: 30000 });
  assert.doesNotMatch(await page.textContent("#calcRis"), /DatoNP|non stimabile/);
  await page.selectOption(".calc-passivita >> nth=0 >> select", "3");
  await page.waitForSelector(".calc-passivita select.calc-cespite");
  await page.waitForFunction(() => /immobile del mutuo/.test((document.querySelector("#calcErrore") || {}).textContent || ""), null, { timeout: 30000 });
  await page.selectOption(".calc-passivita select.calc-cespite", "i1");
  await page.waitForFunction(() => document.querySelector("#calcTotale") && /Importi arrotondati/.test(document.querySelector("#calcRis").textContent), null, { timeout: 30000 });
  await page.click(".calc-passivita >> nth=0 >> button.x");
  await page.fill(".calc-immobile >> nth=0 >> input[aria-label=Valore]", "300.000");
  await page.waitForFunction(() => (document.querySelector("#calcTotale") || {}).textContent === "15.805 €", null, { timeout: 30000 });
  // decesso prima del 2025: imposta di successione «non stimabile» con il motivo
  await page.fill("#calcData", "2024-05-01");
  await page.waitForFunction(() => /non stimabile: imposta di successione/.test(document.querySelector("#calcRis").textContent), null, { timeout: 30000 });
  assert.equal(await pratiche(), prima, "la stima non crea pratiche");
  // dalla Guida
  await page.click("#dCalc .wiz-az button:has-text('Chiudi')");
  await page.click("#bGuida");
  await page.click("#dGuida [role=tab]:has-text('Uso del programma')");
  await page.click("#guidaCalc");
  await page.waitForSelector("#dCalc[open]");
  assert.equal(await page.inputValue("#calcData"), "2024-05-01", "i dati restano finche' non si azzera");
  // crea la pratica dalla procedura guidata compilata
  await page.click("#calcCrea");
  await page.waitForSelector("#wiz[open]");
  assert.equal(await page.inputValue("#w_data_decesso"), "01/05/2024");
  await page.fill("#w_cognome", "Prova Calcolatrice");
  for (let i = 0; i < 3; i++) await page.click("#wAvanti");
  await page.click("#wAvanti");
  await page.waitForFunction(() => !document.querySelector("#wiz").open && S.P && S.P.dati, null, { timeout: 30000 });
  const eredi = await page.evaluate(() => S.P.dati.persone.filter(p => p.ruolo === "erede").map(p => p.grado_parentela));
  assert.deepEqual(eredi, ["10", "10"]);
  assert.equal(await pratiche(), prima + 1);
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
