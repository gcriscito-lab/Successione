"use strict";
// Calendario accanto ai campi data (richiesta del 9/11/2026), dati SINTETICI: ogni campo data di testo (GG/MM/AAAA) ha un
// pulsante che apre il calendario del browser; la data scelta finisce nel campo come se fosse stata digitata e la pratica
// registra la modifica. Il campo resta di testo: digitare funziona come prima.
// Uso: node gui_calendario.js [url]  (server sintetico: tests/e2e/server.py, porta 8813)
const assert = require("node:assert/strict");
async function run(page, url = "http://127.0.0.1:8813/?t=t0k") {
  const errori = []; page.on("pageerror", e => errori.push(String(e)));
  page.on("dialog", d => d.dismiss().catch(() => {}));
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(url);
  await page.waitForFunction(() => typeof S !== "undefined" && S.schema && S.pratiche.length);
  // sceglie una data dal calendario nascosto del campo (come fa il browser quando si clicca un giorno)
  const scegli = (sel, iso) => page.evaluate(([sel, iso]) => {
    const inp = document.querySelector(sel), n = inp.parentElement.querySelector(".cal-nativo");
    n.value = iso; n.dispatchEvent(new Event("input", { bubbles: true })); n.dispatchEvent(new Event("change", { bubbles: true }));
    return inp.value;
  }, [sel, iso]);
  const stato = sel => page.evaluate(sel => {
    const inp = document.querySelector(sel), w = inp && inp.parentElement, b = w && w.querySelector(".cal-apri");
    if (!b) return null;
    const ri = inp.getBoundingClientRect(), rb = b.getBoundingClientRect(), rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
    return { involucro: w.classList.contains("con-calendario"), etichetta: b.getAttribute("aria-label"), titolo: b.title, tab: b.tabIndex,
      dentro: rb.right <= ri.right + 1 && rb.left >= ri.left && rb.top >= ri.top - 1 && rb.bottom <= ri.bottom + 1,
      larghezza: ri.width, rem, tipo: inp.type, spento: b.disabled };
  }, sel);
  const controlla = async (sel, dove) => {
    const s = await stato(sel);
    assert.ok(s && s.involucro, `pulsante del calendario accanto al campo data (${dove})`);
    assert.equal(s.etichetta, "Scegli la data dal calendario"); assert.equal(s.titolo, "Scegli la data dal calendario");
    assert.equal(s.tab, -1, "il pulsante non entra nel giro del Tab");
    assert.equal(s.tipo, "text", "il campo resta di testo");
    assert.ok(s.dentro, `pulsante dentro il campo (${dove})`);
    assert.ok(s.larghezza <= 11 * s.rem + 1, `campo data entro 11rem (${dove}: ${s.larghezza}px)`);
  };

  // procedura guidata
  await page.click("#homeNuova"); await page.waitForSelector("#wiz[open] #w_data_decesso");
  await controlla("#w_data_decesso", "procedura guidata"); await controlla("#w_data_nascita", "procedura guidata");
  assert.equal(await scegli("#w_data_decesso", "2025-03-10"), "10/03/2025");
  assert.equal(await page.evaluate(() => W.dati.data_decesso), "10/03/2025", "la procedura guidata registra la data scelta");
  await page.fill("#w_data_nascita", "01/02/1940");                              // digitare funziona come prima
  assert.equal(await page.evaluate(() => W.dati.data_nascita), "01/02/1940");
  // il calendario si apre sulla data gia' scritta
  await page.evaluate(() => { HTMLInputElement.prototype.showPicker = function () { window.__aperto = this.value; }; });
  await page.click("#w_data_nascita + .cal-apri");
  assert.equal(await page.evaluate(() => window.__aperto), "1940-02-01");
  await page.evaluate(() => document.querySelector("#wiz").close());

  // Dati generali (AN)
  const pid = await page.evaluate(() => S.pratiche[0].pratica_id || S.pratiche[0].id);
  await page.evaluate(id => apri(id, "AN"), pid);
  await page.waitForSelector('.generali-griglia input[placeholder="GG/MM/AAAA"]');
  const nAN = await page.evaluate(() => { const c = [...document.querySelectorAll('.generali-griglia input[placeholder="GG/MM/AAAA"]')];
    return { campi: c.length, pulsanti: c.filter(x => x.parentElement.querySelector(".cal-apri")).length }; });
  assert.ok(nAN.campi > 0 && nAN.campi === nAN.pulsanti, `AN: ${nAN.pulsanti} pulsanti su ${nAN.campi} campi data`);
  await page.evaluate(() => document.querySelector('.generali-griglia [data-campo="data_decesso"] input').setAttribute("data-prova", "decesso"));
  await controlla('[data-prova="decesso"]', "Dati generali");
  const prima = await page.evaluate(() => nMod());
  assert.equal(await scegli('[data-prova="decesso"]', "2025-04-11"), "11/04/2025");
  assert.ok(await page.evaluate(() => nMod()) > prima, "la pratica registra la modifica fatta dal calendario");

  // scheda della riga (fabbricati: data della visura)
  await page.click('#albero [data-q="EC"]');                               // le modifiche non salvate restano
  await page.waitForSelector("#vista tbody tr");
  await page.click("#vista tbody tr >> nth=0");
  await page.waitForSelector('#ins input[placeholder="GG/MM/AAAA"]');
  await page.evaluate(() => document.querySelector('#ins input[placeholder="GG/MM/AAAA"]').setAttribute("data-prova", "scheda"));
  await controlla('[data-prova="scheda"]', "scheda della riga");
  assert.equal(await scegli('[data-prova="scheda"]', "2026-01-15"), "15/01/2026");
  // il campo nascosto non entra nel giro di Invio fra i campi della scheda
  assert.equal(await page.evaluate(() => [...document.querySelectorAll("#ins .cal-nativo")].every(x => x.tabIndex === -1)), true);

  assert.deepEqual(errori, []);
  return { esito: "passato", ambito: "GUI locale, dati sintetici", campi_AN: nAN.campi };
}
module.exports = { run };
if (require.main === module) (async () => {
  const { chromium } = require("playwright");
  const browser = await chromium.launch({ headless: true });
  try { console.log(JSON.stringify(await run(await browser.newPage(), process.argv[2]))); }
  finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
