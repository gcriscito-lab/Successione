"use strict";
// Revisione di usabilita' del 14/11/2026 (docs/revisione_usabilita_20261114/ELENCO_UNICO.md), dati SINTETICI.
// Il punto piu' grave: il programma diceva «Nessun rilievo» e poi «Genera file» si rifiutava. Ora cio' che blocca il file e' un
// solo elenco (Controlli, File e invio, EF), contato in «Controlla (n)» e nella barra in basso, con «Vai al dato».
// Piu' alcuni errori: Ctrl+S con il cursore nel campo (E1), data dal codice fiscale nella procedura guidata (E4), conteggio delle
// righe nuove (E9), «File XML» senza file (E2).
// Uso: node gui_per_il_file.js [url]  (server sintetico: tests/e2e/server.py, porta 8813)
const assert = require("node:assert/strict");
async function run(page, url = "http://127.0.0.1:8813/?t=t0k") {
  const errori = []; page.on("pageerror", e => errori.push(String(e)));
  page.on("dialog", d => d.accept().catch(() => {}));
  await page.setViewportSize({ width: 1910, height: 1000 });
  await page.goto(url);
  await page.waitForFunction(() => typeof S !== "undefined" && S.schema && S.pratiche.length);

  // una pratica con qualcosa che blocca il file (nelle fixture almeno una non ha il fornitore)
  const pid = await page.evaluate(async () => {
    for (const p of S.pratiche) { const id = p.pratica_id || p.id; const q = await api("/api/pratiche/" + id + "/quadri"); if ((q.per_il_file || []).length) return id; }
    return null;
  });
  assert.ok(pid, "almeno una pratica di prova con punti da sistemare per il file");
  await page.evaluate(id => apri(id, "AN"), pid);
  await page.waitForFunction(() => S.Q && Array.isArray(S.Q.per_il_file));
  const conti = await page.evaluate(() => ({ ril: S.Q.rilievi.length, pf: S.Q.per_il_file.length, bottone: $("#bControlla").textContent, barra: $("#sb").textContent }));
  assert.equal(conti.bottone, "Controlla (" + (conti.ril + conti.pf) + ")", "Controlla conta anche i punti che bloccano il file");
  assert.ok(!/Nessun rilievo/.test(conti.barra), "la barra non dice «Nessun rilievo» se il file e' bloccato: " + conti.barra);
  assert.match(conti.barra, /da sistemare per il file/);
  assert.ok(!/Controllo ufficiale: vedi/.test(conti.barra), "niente testo fisso sul controllo ufficiale nella barra");

  // scheda Controlli: lo stesso elenco con «Vai al dato», senza la nota fissa «file XML completo non generato»
  await page.click("#bControlla"); await page.waitForSelector("#ins .per-il-file-voci li");
  const ctl = await page.evaluate(() => ({ voci: document.querySelectorAll("#ins .per-il-file-voci > li").length,
    vai: document.querySelectorAll("#ins .per-il-file-voci .lk").length, testo: $("#ins").textContent }));
  assert.equal(ctl.voci, conti.pf); assert.equal(ctl.vai, conti.pf, "ogni voce ha il suo «Vai al dato»");
  assert.ok(!/file XML completo non e' stato generato/.test(ctl.testo));
  assert.ok(!/Nessun rilievo/.test(ctl.testo));

  // File e invio, passo 2: stesso elenco prima del pulsante; «File XML» non dice «aggiornato» senza file
  await page.click("#navFile"); await page.waitForSelector("#fileContenuto .per-il-file-voci li");
  assert.equal(await page.locator("#fileContenuto .per-il-file-voci > li").count(), conti.pf);
  const fileXml = await page.evaluate(() => { const r = [...document.querySelectorAll("#fileContenuto .rg-stato")].find(x => /File XML/.test(x.textContent)); return r && r.textContent; });
  if (/Nessun file generato/.test(fileXml)) assert.ok(!/aggiornato/.test(fileXml), "File XML: " + fileXml);

  // «Vai a File e invio» / «Vai al dato» dai Controlli porta al dato
  await page.evaluate(() => { S.sel = "AN"; S.tab = "controlli"; render(); });
  await page.waitForSelector("#ins .per-il-file-voci .lk");
  const primo = await page.evaluate(() => S.Q.per_il_file[0].quadro);
  await page.click("#ins .per-il-file-voci .lk >> nth=0"); await page.waitForTimeout(400);
  assert.equal(await page.evaluate(() => S.sel), primo, "«Vai al dato» apre il quadro giusto");

  // EF: lo stesso elenco
  await page.evaluate(() => scegliQuadro("EF")); await page.waitForSelector("#vista .per-il-file-voci li");

  // E9: riga nuova contata nell'intestazione
  await page.evaluate(() => scegliQuadro("EA")); await page.waitForSelector("#vista .sottotitolo");
  const prima = await page.textContent("#vista .sottotitolo");
  await page.keyboard.press("Alt+n"); await page.waitForFunction(() => /da salvare/.test($("#vista .sottotitolo").textContent));
  assert.notEqual(await page.textContent("#vista .sottotitolo"), prima);
  await page.evaluate(() => { S.nuove.clear(); S.riga = null; render(); });

  // E1: Ctrl+S con il cursore ancora nel campo salva e non lascia «modifiche non salvate»
  await page.evaluate(() => scegliQuadro("AN"));
  const tel = page.locator('.generali-griglia [data-campo="cognome"] input, #vista .rg[data-campo="cognome"] input').first();
  await tel.click(); await tel.fill("Rossiprova");
  const salvato = page.waitForResponse(r => r.url().includes("/aggiorna") && r.request().method() === "POST");
  await page.keyboard.press("Control+s"); await salvato; await page.waitForTimeout(500);
  assert.equal(await page.evaluate(() => nMod()), 0, "dopo Ctrl+S nessuna modifica in sospeso");
  assert.ok(!/non salvat/.test(await page.textContent("#sb")));

  // E4: nella procedura guidata la data presa dal codice fiscale e' GG/MM/AAAA
  await page.click("#bHome"); await page.waitForTimeout(300);
  await page.evaluate(() => wizApri()); await page.waitForSelector("#wiz[open] #w_codice_fiscale");
  await page.fill("#w_codice_fiscale", "RSSMRA40A01H501K"); await page.dispatchEvent("#w_codice_fiscale", "change");
  await page.waitForFunction(() => $("#w_data_nascita").value !== "", null, { timeout: 5000 });
  assert.match(await page.inputValue("#w_data_nascita"), /^\d{2}\/\d{2}\/\d{4}$/);
  await page.evaluate(() => { W.dati = {}; document.querySelector("#wiz").close(); });

  assert.deepEqual(errori, []);
  return { esito: "passato", ambito: "GUI locale, dati sintetici", punti_per_il_file: conti.pf };
}
module.exports = { run };
if (require.main === module) (async () => {
  const { chromium } = require("playwright");
  const browser = await chromium.launch({ headless: true });
  try { console.log(JSON.stringify(await run(await browser.newPage(), process.argv[2]))); }
  finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
