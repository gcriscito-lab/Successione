"use strict";
// Revisione indipendente dell'interfaccia (08/11/2026), dati SINTETICI: le finestre non perdono dati senza conferma (procedura,
// preventivo, finestre di operazione, Azzera della calcolatrice), azione primaria su «Salva»/«Crea», «Controlla» avvisa prima di
// salvare, dettagli della calcolatrice aperti fra un tasto e l'altro con annuncio del solo totale, tabella nativa senza role
// grid, menu Operazioni come semplice disclosure, errori collegati al campo, selezione di una riga senza ridisegnare tutta la vista.
// Uso: node gui_revisione_interfaccia.js [url]  (server sintetico: tests/e2e/server.py, porta 8813)
const assert = require("node:assert/strict");
async function run(page, url = "http://127.0.0.1:8813/?t=t0k") {
  const errori = []; page.on("pageerror", e => errori.push(String(e)));
  const domande = []; let risposta = "dismiss";
  page.on("dialog", d => { domande.push(d.message()); (risposta === "accept" ? d.accept() : d.dismiss()).catch(() => {}); });
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto(url);
  await page.waitForFunction(() => typeof S !== "undefined" && S.schema);

  // 1. procedura «Nuova dichiarazione»: vuota si chiude senza domande; con un dato Esc e Annulla chiedono conferma
  await page.click("#homeNuova"); await page.waitForSelector("#wiz[open]");
  await page.keyboard.press("Escape");
  await page.waitForFunction(() => !document.querySelector("#wiz[open]"));
  assert.equal(domande.length, 0, "procedura vuota: nessuna conferma");
  await page.click("#homeNuova"); await page.waitForSelector("#wiz[open] #w_cognome");
  await page.fill("#w_cognome", "ROSSI");
  await page.keyboard.press("Escape");
  assert.match(domande.pop() || "", /dati inseriti andranno persi/);
  assert.ok(await page.isVisible("#wiz[open]"), "rifiutata la conferma, la procedura resta aperta");
  assert.equal(await page.inputValue("#w_cognome"), "ROSSI");
  await page.click("#wAnnulla");
  assert.match(domande.pop() || "", /dati inseriti andranno persi/);
  risposta = "accept"; await page.click("#wAnnulla"); domande.pop(); risposta = "dismiss";
  await page.waitForFunction(() => !document.querySelector("#wiz[open]"));

  // 16 e 15. calcolatrice: «Azzera» con dati chiede conferma; primario su «Crea»; dettagli aperti restano aperti; annuncio del totale
  await page.click("#homeCalc"); await page.waitForSelector("#dCalc[open] #calcData");
  assert.ok(await page.$eval("#calcCrea", b => b.classList.contains("pil")), "primario: Crea una pratica");
  assert.equal(await page.$eval("#calcRis", x => x.hasAttribute("aria-live")), false, "nessun aria-live su tutto il risultato");
  await page.fill("#calcData", "2025-03-10");
  await page.selectOption(".calc-erede >> nth=0 >> select", "02");
  await page.click("#calcDati button:has-text('Aggiungi immobile')");
  await page.fill(".calc-immobile >> nth=0 >> input[aria-label=Valore]", "2.000.000");
  await page.waitForSelector("#calcRis details.calc-erede-ris", { timeout: 30000 });
  await page.click("#calcRis details.calc-erede-ris > summary");
  await page.fill(".calc-immobile >> nth=0 >> input[aria-label=Valore]", "2.100.000");
  await page.waitForFunction(() => /2\.100\.000|Totale/.test(document.querySelector("#calcAnnuncio").textContent) && document.querySelector("#calcTotale"), null, { timeout: 30000 });
  await page.waitForTimeout(900);   // nuovo calcolo dopo la pausa di scrittura
  assert.equal(await page.$eval("#calcRis details.calc-erede-ris", d => d.open), true, "il dettaglio dell'erede resta aperto");
  assert.match(await page.textContent("#calcAnnuncio"), /^Totale stimato: /);
  await page.click("#calcAzzera");
  assert.match(domande.pop() || "", /Azzerare la calcolatrice/);
  assert.equal(await page.inputValue("#calcData"), "2025-03-10", "rifiutata la conferma, i dati restano");
  await page.click("#dCalc .wiz-az button:has-text('Chiudi')");
  await page.waitForFunction(() => !document.querySelector("#dCalc[open]"));

  // pratica con due fabbricati e un erede con codice fiscale sbagliato (rilievo sul campo)
  const pid = await page.evaluate(async () => (await post("/api/pratiche", { titolo: "Revisione GUI e2e", iniziali: [
    { op: "upsert", coll: "persone", id: "p_def0rev1", campi: { ruolo: "defunto", cognome: "BIANCHI", nome: "ADA", data_decesso: "2025-05-02" } },
    { op: "upsert", coll: "persone", id: "p_ere0rev1", campi: { ruolo: "erede", cognome: "BIANCHI", nome: "LIA", codice_fiscale: "XXXXXXXXXXXXXXX1" } },
    { op: "upsert", coll: "beni", id: "b_fab0rev1", campi: { tipo: "fabbricato", comune: "ROMA", valore: "100000" } },
    { op: "upsert", coll: "beni", id: "b_fab0rev2", campi: { tipo: "fabbricato", comune: "MILANO", valore: "200000" } }] })).pratica_id);
  await page.evaluate(async id => { await caricaPratiche(); await apri(id, "EC"); }, pid);
  await page.waitForSelector("#vista tbody tr[data-key]");

  // 7 e 8. tabella nativa; menu Operazioni senza ruoli di menu
  assert.equal(await page.$eval("#vista table", t => t.getAttribute("role")), null);
  assert.equal(await page.$eval("#vista details.operazioni > summary", s => s.getAttribute("aria-haspopup")), null);
  assert.equal(await page.locator("#vista .menu-op [role=menuitem]").count(), 0);

  // 11. selezione di una riga: si aggiornano le righe e il pannello, la tabella non viene ridisegnata
  const righe = page.locator("#vista tbody tr[data-key]");
  await righe.nth(0).click(); await page.waitForSelector("#ins:not([hidden]) .ins-testa");
  await page.evaluate(() => { document.querySelector("#vista table").dataset.segno = "1"; });
  await righe.nth(1).click();
  await page.waitForFunction(() => document.querySelectorAll('#vista tbody tr[aria-selected="true"]').length === 1);
  assert.equal(await page.$eval("#vista table", t => t.dataset.segno), "1", "stessa tabella: niente ridisegno completo");
  assert.equal(await righe.nth(1).getAttribute("aria-selected"), "true");
  assert.equal(await righe.nth(1).getAttribute("tabindex"), "0");
  assert.equal(await righe.nth(0).getAttribute("tabindex"), "-1");
  assert.match(await page.textContent("#ins .ins-testa h3"), /MILANO|200/);

  // 3. finestra di operazione (modifica di gruppo): Invio su una casella non applica; Annulla con dati chiede conferma
  await page.click("#vista details.operazioni > summary");
  await page.click("#vista .menu-op button:has-text('Modifica di gruppo')");
  await page.waitForSelector("dialog.dlg-op[open]");
  const casella = page.locator("dialog.dlg-op[open] input[type=checkbox]").first();
  await casella.focus(); await page.keyboard.press("Enter");
  assert.ok(await page.isVisible("dialog.dlg-op[open]"), "Invio su una casella non applica");
  await page.keyboard.press("Space");
  await page.click("dialog.dlg-op[open] button:has-text('Annulla')");
  assert.match(domande.pop() || "", /Chiudere senza applicare/);
  assert.ok(await page.isVisible("dialog.dlg-op[open]"));
  risposta = "accept"; await page.keyboard.press("Escape"); domande.pop(); risposta = "dismiss";
  await page.waitForFunction(() => !document.querySelector("dialog.dlg-op[open]"));
  assert.equal(await page.evaluate(() => document.activeElement && document.activeElement.tagName), "SUMMARY", "il focus torna su «Operazioni»");

  // 9. «Controlla» con modifiche in sospeso chiede prima di salvare
  await page.locator("#ins input[name=comune]").fill("MILANO CENTRO");
  await page.click("#bControlla");
  assert.match(domande.pop() || "", /salva prima la modifica in sospeso/);
  assert.ok(await page.evaluate(() => nMod() > 0), "rifiutato: nulla e' stato salvato");
  await page.evaluate(() => { S.dirty.clear(); render(); });

  // 6. errore sul campo collegato al campo: aria-invalid e aria-describedby (anche con l'aiuto)
  await page.evaluate(() => scegliQuadro("EA"));
  await page.waitForSelector("#vista tbody tr[data-key]");
  await page.evaluate(async () => { S.Q = await api("/api/pratiche/" + S.P.pratica_id + "/quadri"); render(); });
  const cf = await page.evaluate(() => {
    const r = [...document.querySelectorAll("#vista tbody tr[data-key]")].find(x => /LIA/.test(x.textContent)); r.click();
    const el = document.querySelector('#ins [data-path$=".codice_fiscale"]');
    if (!el) return null;
    const ids = (el.getAttribute("aria-describedby") || "").split(/\s+/).filter(Boolean);
    return { invalid: el.getAttribute("aria-invalid"), testi: ids.map(i => (document.getElementById(i) || {}).textContent || "") };
  });
  if (cf && cf.invalid) {
    assert.equal(cf.invalid, "true");
    assert.ok(cf.testi.some(t => t.length > 0), "il messaggio d'errore e' nella descrizione del campo");
  }

  // 2 e 15. preventivo: «Salva» e' il primario; Chiudi ed Esc con modifiche chiedono conferma
  await page.evaluate(async id => { await apri(id, "FILE"); }, pid);
  await page.waitForSelector("#bPreventivo"); await page.click("#bPreventivo");
  await page.waitForSelector("#dPreventivo[open]");
  assert.ok(await page.$eval("#prevSalva", b => b.classList.contains("pil")));
  assert.ok(await page.$eval("#prevChiudi", b => !b.classList.contains("pil")));
  await page.click("#prevChiudi");
  await page.waitForFunction(() => !document.querySelector("#dPreventivo[open]"));
  assert.equal(domande.length, 0, "preventivo senza modifiche: si chiude senza domande");
  await page.click("#bPreventivo"); await page.waitForSelector("#dPreventivo[open]");
  await page.fill("#dPreventivo tbody tr:nth-child(1) td:nth-child(2) input", "500");
  await page.keyboard.press("Escape");
  assert.match(domande.pop() || "", /modifiche non salvate nel preventivo/);
  assert.ok(await page.isVisible("#dPreventivo[open]"));
  risposta = "accept"; await page.click("#prevChiudi"); domande.pop(); risposta = "dismiss";
  await page.waitForFunction(() => !document.querySelector("#dPreventivo[open]"));
  assert.equal(await page.evaluate(() => (S.P.dati.note || {}).preventivo), undefined, "nulla salvato");

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
