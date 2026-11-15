"use strict";
// Quadri EE ed EH come nel modello (15/11/2026), dati SINTETICI (pratica esportabile delle fixture: build/gui_review_fixture.json).
// EE: otto righi numerati, vuoti con «—», totali EE6 ed EE8 in grassetto. EH: sezioni I-IV con lettere, frasi barrate ed eredi
// in tabella, niente nomi tecnici; caselle di separazione e unione civile solo con lo stato civile giusto (5, 7).
// Uso: node gui_quadri_ee_eh.js [url]  (server sintetico: tests/e2e/server.py, porta 8813)
const assert = require("node:assert/strict");
const path = require("node:path"), fs = require("node:fs");
async function run(page, url = "http://127.0.0.1:8813/?t=t0k") {
  const errori = []; page.on("pageerror", e => errori.push(String(e)));
  page.on("dialog", d => d.accept().catch(() => {}));
  const fix = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "..", "build", "gui_review_fixture.json"), "utf8"));
  await page.setViewportSize({ width: 1910, height: 1000 });
  await page.goto(url);
  await page.waitForFunction(() => typeof S !== "undefined" && S.schema && S.pratiche.length);

  // EE
  await page.evaluate(id => apri(id, "EE"), fix.export);
  await page.waitForSelector("#vista .prospetto-ee tbody tr");
  const righi = await page.$$eval("#vista .prospetto-ee tbody tr", l => l.map(r => ({ rigo: r.cells[0].textContent, forte: r.classList.contains("forte"), valore: r.cells[2].textContent })));
  assert.deepEqual(righi.map(r => r.rigo), ["EE1", "EE2", "EE3", "EE4", "EE5", "EE6", "EE7", "EE8"]);
  assert.deepEqual(righi.filter(r => r.forte).map(r => r.rigo), ["EE6", "EE8"]);
  assert.ok(righi.every(r => r.valore === "—" || /^[\d.]+ €$/.test(r.valore)), "euro interi o «—»: " + JSON.stringify(righi));
  assert.ok(!(await page.textContent("#vista")).includes("TotaleValore"), "nessun nome tecnico nel quadro EE");

  // EH
  await page.evaluate(() => scegliQuadro("EH"));
  await page.waitForSelector("#vista .eh-sezione");
  const testo = await page.textContent("#vista");
  assert.match(testo, /Sezione I - Dichiarazioni sostitutive/);
  assert.ok(!/Sezione(I|II|III|IV)_/.test(testo), "nessun nome tecnico delle sezioni");
  const lettere = await page.$$eval("#vista .eh-lettera", l => l.map(x => x.textContent));
  assert.ok(lettere.length && lettere[0] === "a)", "sezione I per lettera: " + lettere.join(" "));
  assert.equal(await page.locator("#vista details.eh-sezione.assente").count() + await page.locator("#vista section.eh-sezione").count(), 4, "quattro sezioni");
  // il collegamento porta al quadro in cui si modifica
  const vai = page.locator("#vista .eh-vai").first();
  const dest = (await vai.textContent()).match(/Modifica in ([A-Z]{2})/)[1];
  await vai.click(); await page.waitForFunction(q => S.sel === q, dest);

  // caselle del dichiarante secondo lo stato civile (modifica non salvata, poi annullata)
  const caselle = async sc => {
    await page.evaluate(sc => { S.dichDirty.set("stato_civile", sc); scegliQuadro("EH"); }, sc);
    await page.waitForSelector("#vista .eh-sezione");
    return page.evaluate(() => [!!document.getElementById("dd_separazione_con_colpa"), !!document.getElementById("dd_no_scioglimento_unione_civile")]);
  };
  assert.deepEqual(await caselle("5"), [true, false], "stato civile 5: solo separazione");
  assert.deepEqual(await caselle("7"), [false, true], "stato civile 7: solo unione civile");
  assert.match(await page.textContent("#vista"), /Con stato civile 7 la casella sullo scioglimento/);
  assert.deepEqual(await caselle("1"), [false, false], "altri stati civili: nessuna delle due");
  await page.evaluate(() => { S.dichDirty.clear(); render(); });

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
