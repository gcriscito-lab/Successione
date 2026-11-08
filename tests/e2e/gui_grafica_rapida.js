"use strict";
// Correzioni grafiche dal confronto con DEAS II (08/11/2026), dati SINTETICI, finestra 1366x768:
// - «Dati generali» senza la colonna vuota del pannello (classList.toggle con undefined la invertiva a ogni ridisegno);
// - EA: cognome, nome, parentela e ruolo prima del codice fiscale;
// - DV: diritto per nome, righe raggruppate per bene con la somma delle quote;
// - pagina iniziale: ricerca, filtro e ordinamento sulla stessa riga; titolo del quadro su una riga.
// Uso: node gui_grafica_rapida.js [url]  (server sintetico: tests/e2e/server.py, porta 8813)
const assert = require("node:assert/strict");
async function run(page, url = "http://127.0.0.1:8813/?t=t0k") {
  const errori = []; page.on("pageerror", e => errori.push(String(e)));
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto(url);
  await page.waitForFunction(() => typeof S !== "undefined" && S.schema);
  await page.evaluate(async () => {
    const fab = (id, p) => ({ op: "upsert", coll: "beni", id, campi: { tipo: "fabbricato", comune: "Roma", foglio: "2", particella: p,
      categoria: "A/2", rendita: "400.00", diritto: "1", quota_defunto: "1/1", valore: "50400" } });
    const per = (id, cognome, nome) => ({ op: "upsert", coll: "persone", id, campi: { ruolo: "erede", cognome, nome } });
    const dv = (id, b, p, q) => ({ op: "upsert", coll: "devoluzioni", id, campi: { bene_id: b, persona_id: p, quota: q, diritto: "1" } });
    await post("/api/pratiche", { titolo: "Grafica rapida e2e", iniziali: [
      { op: "upsert", coll: "persone", id: "p_defuntog1", campi: { ruolo: "defunto", cognome: "Prova", nome: "Grafica", data_decesso: "2025-06-01" } },
      per("p_saraa0001", "VERDI", "SARA"), per("p_marcoo001", "VERDI", "MARCO"),
      fab("b_villa0001", "21"), fab("b_villa0002", "22"),
      // ordine misto apposta: la vista deve raggruppare per bene
      dv("d_g10000001", "b_villa0001", "p_saraa0001", "1/2"), dv("d_g20000001", "b_villa0002", "p_saraa0001", "1/2"),
      dv("d_g30000001", "b_villa0001", "p_marcoo001", "1/2")] });
    await caricaPratiche(); renderHome();
  });

  // pagina iniziale: ricerca, filtro e ordinamento su una riga
  const alti = await page.evaluate(() => [...document.querySelectorAll("#homeFiltri > *")].map(e => Math.round(e.getBoundingClientRect().top)));
  assert.equal(alti.length, 3); assert.ok(Math.max(...alti) - Math.min(...alti) < 12, "filtri su una riga: " + alti);   // input e select differiscono di 1-2 px

  const pid = await page.evaluate(() => S.pratiche.find(p => p.titolo === "Grafica rapida e2e").id);
  await page.evaluate(id => apri(id), pid);
  await page.waitForFunction(() => S.P && S.Q);

  // «Dati generali»: nessuna colonna del pannello, anche dopo piu' ridisegni
  for (let i = 0; i < 3; i++) {
    await page.evaluate(() => render());
    const st = await page.evaluate(() => ({ cls: document.querySelector("#app").classList.contains("conIns"), w: Math.round(document.querySelector("#vista").getBoundingClientRect().width) }));
    assert.equal(st.cls, false, "ridisegno " + i + ": colonna del pannello presente in Dati generali");
    assert.ok(st.w > 1000, "Dati generali usa la larghezza: " + st.w);
  }

  // EA: chi e' prima del codice fiscale
  await page.evaluate(() => scegliQuadro("EA"));
  await page.waitForSelector('#vista tr[data-key="e:persone:p_saraa0001"]');
  const intest = await page.$$eval("#vista thead th", ths => ths.map(t => t.textContent.trim()));
  assert.deepEqual(intest.slice(0, 2), ["Cognome", "Nome"]);
  assert.ok(intest.indexOf("Codice fiscale") > intest.indexOf("Nome"));

  // DV: diritto per nome, gruppi per bene con la somma
  await page.evaluate(() => scegliQuadro("DV"));
  await page.waitForSelector('#vista tr[data-key="e:devoluzioni:d_g10000001"]');
  const dv = await page.evaluate(() => [...document.querySelectorAll("#vista tbody tr")].map(tr => tr.classList.contains("subtot") ? "S:" + tr.textContent : tr.dataset.key));
  assert.deepEqual(dv.map(x => x.startsWith("S:") ? "S" : x.split(":").pop()), ["d_g10000001", "d_g30000001", "S", "d_g20000001", "S"]);
  assert.match(dv[2], /1\/1 · completa/); assert.match(dv[4], /1\/2 · manca 1\/2/);
  const diritto = await page.$eval('#vista tr[data-key="e:devoluzioni:d_g10000001"]', tr => tr.textContent);
  assert.ok(!/(^|\s)1(\s|$)/.test(diritto.replace(/1\/2/g, "")) && /propriet/i.test(diritto), "diritto per nome: " + diritto);
  // la tastiera salta le righe di somma
  await page.focus('#vista tr[data-key="e:devoluzioni:d_g30000001"]');
  await page.keyboard.press("ArrowDown");
  assert.equal(await page.evaluate(() => document.activeElement.dataset.key), "e:devoluzioni:d_g20000001");

  // titolo del quadro su una riga con il pannello aperto
  await page.evaluate(() => scegliQuadro("EC"));
  await page.click('#vista tr[data-key="e:beni:b_villa0001"]');
  const h1 = await page.$eval(".testa-quadro h1", e => ({ h: e.getBoundingClientRect().height, lh: parseFloat(getComputedStyle(e).lineHeight) || 0, title: e.title }));
  assert.ok(h1.h < 50, "titolo su una riga: " + JSON.stringify(h1)); assert.match(h1.title, /EC — /);
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
