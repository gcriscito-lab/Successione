"use strict";
// Review completa del 07/11/2026 (sera), interfaccia, dati SINTETICI: modifica di gruppo che non svuota per errore, tasto
// Invio nelle finestre Operazioni / Calcolatrice / Guida, Ctrl+S con una finestra aperta, «Prossime azioni» (decorrenza,
// passo da correggere, pratiche non mostrate). Nessun controllo ufficiale o invio.
// Uso: node gui_review3.js [url]  (server sintetico: tests/e2e/server.py, porta 8813)
const assert = require("node:assert/strict");
async function run(page, url = "http://127.0.0.1:8813/?t=t0k") {
  const errori = []; page.on("pageerror", e => errori.push(String(e)));
  await page.goto(url);
  await page.waitForFunction(() => typeof S !== "undefined" && S.schema);
  const pid = await page.evaluate(async () => {
    const fab = (id, p) => ({ op: "upsert", coll: "beni", id, campi: { tipo: "fabbricato", comune: "Roma", foglio: "1", particella: p,
      categoria: "A/2", rendita: "500.00", diritto: "1", quota_defunto: "1/1", valore: "63000" } });
    const r = await post("/api/pratiche", { titolo: "Review3 decorrenza e2e", iniziali: [
      { op: "upsert", coll: "persone", id: "p_defunto9", campi: { ruolo: "defunto", cognome: "Prova", nome: "Review", data_decesso: "2025-12-01" } },
      fab("b_casa0001", "11"), fab("b_casa0002", "12")] });
    await post("/api/pratiche", { titolo: "Review3 altra e2e" });
    const p = await api("/api/pratiche/" + r.pratica_id);
    await post("/api/pratiche/" + r.pratica_id + "/aggiorna", { revisione_attesa: p.revisione, chiave: crypto.randomUUID(), operazioni: [
      { op: "set", sezione: "opzioni", campi: { telematico: { dichiarazione: { presentatore: { data_decorrenza: "2026-03-01" } } } } }] });
    await apri(r.pratica_id);
    return r.pratica_id;
  });
  const leggi = () => page.evaluate(async id => api("/api/pratiche/" + id), pid);
  await page.evaluate(() => scegliQuadro("EC"));
  await page.waitForSelector('#vista tr[data-key="e:beni:b_casa0002"]');
  const sporchi = () => page.evaluate(() => [...S.dirty.values()].map(d => [d.id, d.campi.quota_defunto === undefined ? "assente" : d.campi.quota_defunto]).sort());

  // 1. campo spuntato senza valore: nessuna modifica, il dialogo lo dice e resta aperto
  await page.evaluate(() => modificaDiGruppo(quadro()));
  await page.check('#dGruppo input[data-campo="quota_defunto"]');
  await page.click("#dGruppo button.pil");
  assert.equal(await page.isVisible("#dGruppo[open]"), true, "il dialogo resta aperto");
  assert.match(await page.textContent("#dGruppo p.e"), /Nessuna modifica applicata: scegli un valore/);
  assert.deepEqual(await sporchi(), [], "nessun campo svuotato");
  // svuotare richiede la scelta esplicita e una conferma che dice quante righe; annullando non cambia nulla
  await page.check('#dGruppo input[data-svuota="quota_defunto"]');
  let domanda = "";
  page.once("dialog", d => { domanda = d.message(); d.dismiss(); });
  await page.click("#dGruppo button.pil");
  assert.match(domanda, /^Svuotare «.+» in 2 righe\?/);
  assert.deepEqual(await sporchi(), [], "conferma annullata: nessuna modifica");
  page.once("dialog", d => d.accept());
  await page.click("#dGruppo button.pil");
  await page.waitForFunction(() => !document.querySelector("#dGruppo[open]"));
  assert.deepEqual(await sporchi(), [["b_casa0001", null], ["b_casa0002", null]], "svuotato solo dopo la conferma");
  await page.evaluate(() => { S.dirty.clear(); render(); });

  // 2. Invio in un campo delle Operazioni applica l'azione principale (non «Annulla»)
  await page.evaluate(() => modificaDiGruppo(quadro()));
  const campoQuota = '#dGruppo [data-gruppo="quota_defunto"] input:not([type=checkbox])';
  await page.fill(campoQuota, "1/2");
  await page.press(campoQuota, "Enter");
  await page.waitForFunction(() => !document.querySelector("#dGruppo[open]"));
  assert.deepEqual(await sporchi(), [["b_casa0001", { num: 1, den: 2 }], ["b_casa0002", { num: 1, den: 2 }]], "Invio = Applica");

  // 3. Ctrl+S con una finestra aperta non salva; chiusa la finestra, salva
  const rev = (await leggi()).revisione;
  await page.evaluate(() => modificaDiGruppo(quadro()));
  await page.focus(campoQuota);
  await page.keyboard.press("Control+s");
  await page.waitForTimeout(600);
  assert.equal((await leggi()).revisione, rev, "nessun salvataggio con il dialogo aperto");
  assert.equal(await page.evaluate(() => S.dirty.size), 2, "le modifiche restano da salvare");
  await page.click('#dGruppo button[value="annulla"]');
  await page.waitForFunction(() => !document.querySelector("dialog[open]"));
  await page.keyboard.press("Control+s");
  await page.waitForFunction(() => S.dirty.size === 0, null, { timeout: 20000 });
  assert.equal((await leggi()).revisione, rev + 1, "Ctrl+S senza finestre salva");

  // 4. Invio nella Calcolatrice e nella ricerca della Guida non chiude la finestra
  await page.evaluate(() => apriCalcolatrice());
  await page.waitForSelector("#dCalc[open] #calcData");
  await page.fill(".calc-erede >> nth=0 >> input.nome", "Mario");
  await page.press(".calc-erede >> nth=0 >> input.nome", "Enter");
  await page.waitForTimeout(200);
  assert.equal(await page.isVisible("#dCalc[open]"), true, "Calcolatrice ancora aperta");
  assert.equal(await page.inputValue(".calc-erede >> nth=0 >> input.nome"), "Mario");
  await page.click("#dCalc button.pil");
  await page.waitForFunction(() => !document.querySelector("#dCalc[open]"));
  await page.evaluate(() => apriGuida());
  const cerca = '#dGuida[open] input[type=search]';
  await page.waitForSelector(cerca);
  await page.fill(cerca, "prima casa");
  await page.press(cerca, "Enter");
  await page.waitForTimeout(200);
  assert.equal(await page.isVisible("#dGuida[open]"), true, "Guida ancora aperta");
  assert.equal(await page.inputValue(cerca), "prima casa");
  await page.click("#dGuida button.pil");
  await page.waitForFunction(() => !document.querySelector("#dGuida[open]"));

  // 5. Pagina iniziale (un solo elenco dall'08/11/2026): termine dalla decorrenza, passo da correggere, tutte le pratiche elencate
  await page.route("**/api/cruscotto*", async route => {
    const response = await route.fetch(); const c = await response.json();
    const v = c.pratiche.find(x => x.pratica_id !== pid);
    if (v) { v.azione = { testo: "Invio rifiutato: correggi i dati e prepara di nuovo la copia", livello: "problema", dove: { sel: "FILE" } };
      v.tappe = { ...v.tappe, invio: "problema" }; }
    await route.fulfill({ response, json: c });
  });
  await page.click("#bHome");
  // l'elenco si completa quando arriva lo stato (in parte simulato) delle pratiche
  await page.waitForFunction(() => /dalla decorrenza/.test((document.querySelector("#elencoPratiche") || {}).textContent || "")
    && document.querySelector("#elencoPratiche .lk-azione.problema"), null, { timeout: 20000 });
  const riga = page.locator("#elencoPratiche tr", { hasText: "Review3 decorrenza e2e" });
  assert.match(await riga.locator(".c-term .pz").textContent(), /dalla decorrenza$/);
  assert.match(await riga.locator(".c-term").getAttribute("title"), /Termine del 01\/03\/2027, dalla decorrenza del 01\/03\/2026/);
  assert.match(await page.textContent("#elencoPratiche .lk-azione.problema"), /correggi/);
  assert.ok(await page.locator("#elencoPratiche .tm.problema").count() >= 1, "tappa da correggere evidenziata");
  assert.equal(await page.locator("#elencoPratiche tbody tr").count(), await page.evaluate(() => S.pratiche.length), "tutte le pratiche nell'elenco");
  await page.unroute("**/api/cruscotto*");
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
