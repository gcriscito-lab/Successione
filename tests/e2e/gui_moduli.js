"use strict";
// Revisione grafica del 9/11/2026, lotti 1 e 2 (docs/revisione_grafica_20261109/ELENCO_UNICO.md), dati SINTETICI.
// Riga di modulo comune nelle finestre: campi numerici stretti, «Pulisci ora» accanto al campo delle ore, 16 px tra le voci,
// aiuto piu' piccolo dell'etichetta e allineato al testo della casella; linguette del pannello opache; riga vuota alta come le altre.
// Uso: node gui_moduli.js [url]  (server sintetico: tests/e2e/server.py, porta 8813)
const assert = require("node:assert/strict");
async function run(page, url = "http://127.0.0.1:8813/?t=t0k") {
  const errori = []; page.on("pageerror", e => errori.push(String(e)));
  page.on("dialog", d => d.dismiss().catch(() => {}));
  const esiti = {};
  for (const [w, hh] of [[1440, 900], [1920, 1080]]) {
    await page.setViewportSize({ width: w, height: hh });
    await page.goto(url);
    await page.waitForFunction(() => typeof S !== "undefined" && S.schema && S.pratiche.length);
    await page.evaluate(() => impApri());
    await page.waitForSelector("#pref_pulizia_ore");
    const m = await page.evaluate(() => {
      const r = el => el.getBoundingClientRect();
      const rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
      const numeri = [...document.querySelectorAll("#imp input[type=number], #imp_SUCCESSIONI_CONTROLLI_TIMEOUT")].map(e => r(e).width);
      const ore = document.querySelector("#pref_pulizia_ore");
      const pulisci = [...document.querySelectorAll("#impPreferenze button")].find(b => /Pulisci ora/.test(b.textContent));
      const campi = [...document.querySelectorAll("#impPreferenze > .campo")];
      const distanze = campi.slice(1).map((c, i) => Math.round(r(c).top - r(campi[i]).bottom));
      const cas = document.querySelector("#impPreferenze .campo.casella");
      const testo = cas.querySelector("label.chk span"), aiuto = cas.querySelector(".mut");
      const etichetta = document.querySelector("#impPreferenze .campo > label:not(.chk)");
      const sez = document.querySelector("#imp .imp-sezioni");
      return { rem, numeri, oreTop: r(ore).top, pulTop: r(pulisci).top, stacco: r(pulisci).left - r(ore).right, distanze,
        fsAiuto: parseFloat(getComputedStyle(aiuto).fontSize), fsEtichetta: parseFloat(getComputedStyle(etichetta).fontSize),
        pesoEtichetta: getComputedStyle(etichetta).fontWeight, sxAiuto: r(aiuto).left, sxTesto: r(testo).left,
        trabocca: sez.scrollWidth > sez.clientWidth };
    });
    for (const x of m.numeri) assert.ok(x <= 8 * m.rem + 1, `campo numerico largo ${x}px (max 8rem) a ${w}`);
    assert.ok(Math.abs(m.pulTop - m.oreTop) <= 4 + 0.6 * m.rem, `«Pulisci ora» sulla riga del campo ore a ${w}`);
    assert.ok(m.stacco >= 8, `«Pulisci ora» staccato di almeno 8 px (${m.stacco}) a ${w}`);
    for (const d of m.distanze) assert.ok(d >= 14 && d <= 18, `distanza tra voci ${d}px (16±2) a ${w}`);
    assert.ok(m.fsAiuto < m.fsEtichetta, "aiuto piu' piccolo dell'etichetta");
    assert.equal(m.pesoEtichetta, "500");
    assert.ok(Math.abs(m.sxAiuto - m.sxTesto) <= 2, `aiuto allineato al testo della casella (${m.sxAiuto} vs ${m.sxTesto})`);
    assert.equal(m.trabocca, false, "nessun campo esce dalle Impostazioni");
    await page.evaluate(() => $("#imp").close());
    esiti[w] = { distanze: m.distanze, numeri: m.numeri.map(Math.round) };
  }

  // B05: una riga con le celle vuote e' alta come una riga con testo
  const alt = await page.evaluate(() => {
    const t = document.createElement("table"); t.className = "tab";
    t.innerHTML = "<tbody><tr><td>ROMA</td></tr><tr><td></td></tr></tbody>"; document.querySelector("main").append(t);
    const [a, b] = [...t.querySelectorAll("tr")].map(x => x.getBoundingClientRect().height); t.remove(); return { a, b };
  });
  assert.ok(alt.b >= alt.a - 0.5, `riga vuota alta ${alt.b} contro ${alt.a}`);

  // B01: linguette Dati/Controlli/Cronologia opache (lo sfondo copre cio' che scorre sotto)
  const pid = await page.evaluate(() => S.pratiche[0].pratica_id || S.pratiche[0].id);
  await page.evaluate(id => apri(id, "EA"), pid);
  await page.waitForSelector(".ins > .seg");
  const sfondo = await page.evaluate(() => getComputedStyle(document.querySelector(".ins > .seg")).backgroundImage);
  assert.match(sfondo, /linear-gradient/, "sfondo delle linguette con il fondo pieno del pannello");

  assert.deepEqual(errori, []);
  return { esito: "passato", ambito: "GUI locale, dati sintetici", esiti };
}
module.exports = { run };
if (require.main === module) (async () => {
  const { chromium } = require("playwright");
  const browser = await chromium.launch({ headless: true });
  try { console.log(JSON.stringify(await run(await browser.newPage(), process.argv[2]))); }
  finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
