"use strict";
// Review completa del 07/11/2026 (sera), difetti minori dell'interfaccia, dati SINTETICI: nome accessibile dei campi, cassetto con
// il focus trattenuto, frecce nel menu Operazioni e nelle schede, contrasto della pagina iniziale, nessuno scorrimento orizzontale
// a 390 px, barra alta compatta a 1366, ridisegno della sola riga modificata, valori catastali chiesti una volta per revisione,
// conferma alla chiusura delle Impostazioni, «successioni.ultima» dopo la conferma, Ctrl+G senza prompt(). Nessun invio.
// Uso: node gui_review4.js [url]  (server sintetico: tests/e2e/server.py, porta 8813)
const assert = require("node:assert/strict");

const CONTRASTO = `(sel => {
  const cv = document.createElement("canvas"); cv.width = cv.height = 1; const cx = cv.getContext("2d", { willReadFrequently: true });
  const par = s => { cx.clearRect(0, 0, 1, 1); cx.fillStyle = "rgba(0,0,0,0)"; cx.fillStyle = s; cx.fillRect(0, 0, 1, 1); const d = cx.getImageData(0, 0, 1, 1).data; return [d[0], d[1], d[2], d[3] / 255]; };
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const mix = (a, b) => [0, 1, 2].map(i => a[i] * a[3] + b[i] * (1 - a[3])).concat(1);
  const el = document.querySelector(sel); const strati = [];
  for (let n = el; n; n = n.parentElement) { const c = par(getComputedStyle(n).backgroundColor); if (c[3] > 0) strati.push(c); if (c[3] >= 1) break; }
  let bg = [255, 255, 255, 1]; for (let i = strati.length - 1; i >= 0; i--) bg = mix(strati[i], bg);
  let op = 1; for (let n = el; n; n = n.parentElement) op *= Number(getComputedStyle(n).opacity);
  const c = par(getComputedStyle(el).color); const fg = mix([c[0], c[1], c[2], c[3] * op], bg);
  const a = lum(fg), b = lum(bg); return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
})`;

async function run(page, url = "http://127.0.0.1:8813/?t=t0k") {
  const errori = []; page.on("pageerror", e => errori.push(String(e)));
  await page.setViewportSize({ width: 1366, height: 657 });
  await page.goto(url);
  await page.waitForFunction(() => typeof S !== "undefined" && S.schema);
  const pid = await page.evaluate(async () => {
    const ini = [{ op: "upsert", coll: "persone", id: "p_defunto4", campi: { ruolo: "defunto", cognome: "Prova", nome: "Review", data_decesso: "2026-01-10" } }];
    for (let i = 0; i < 40; i++) ini.push({ op: "upsert", coll: "beni", id: "b_rev4" + String(i).padStart(6, "0"), campi: { tipo: "fabbricato", provincia: "RM",
      comune: "Roma", foglio: String(i + 1), particella: String(10 + i), categoria: "A/2", rendita: "500.00", diritto: "1", quota_defunto: "1/1", valore: "63000" } });
    const r = await post("/api/pratiche", { titolo: "REVIEW4_SUCCESSIONE_CON_UN_TITOLO_LUNGHISSIMO_SENZA_SPAZI_E2E", iniziali: ini });
    return r.pratica_id;
  });

  // 1. contrasto della pagina iniziale (iniziali e «Riprendi») nei temi chiaro, scuro, seppia e con contrasto alto
  await page.evaluate(() => caricaPratiche());
  // pagina iniziale ridisegnata l'08/11/2026: un solo elenco; si attende anche lo stato dal server (prossima azione)
  await page.waitForSelector("#elencoPratiche .apri-pratica"); await page.waitForSelector("#elencoPratiche .lk-azione");
  for (const asp of [{ tema: "chiaro" }, { tema: "scuro" }, { tema: "seppia" }, { tema: "chiaro", contrasto: "alto" }, { tema: "scuro", contrasto: "alto" }]) {
    await page.evaluate(a => applicaAspetto({ ...preferenze, ...a }), asp);
    await page.waitForTimeout(250);   // i pulsanti cambiano colore con una transizione di 120 ms: si misura a transizione finita
    for (const sel of ["#elencoPratiche .apri-pratica .tit", "#elencoPratiche .apri-pratica .dett", "#elencoPratiche .lk-azione",
                       "#elencoPratiche th", "#homeFiltri .chip[aria-pressed=true]", "#homeIntro"]) {
      const c = await page.evaluate(CONTRASTO + "(" + JSON.stringify(sel) + ")");
      assert.ok(c >= 4.5, sel + " " + JSON.stringify(asp) + ": contrasto " + c.toFixed(2));
    }
  }
  await page.evaluate(() => applicaAspetto(preferenze));

  // 2. barra alta compatta a 1366 con una pratica aperta (sulla pagina iniziale i comandi della pratica non ci sono):
  //    una sola riga, pulsanti secondari a icona con il nome accessibile intatto
  await page.evaluate(id => apri(id), pid); await page.waitForFunction(() => S.P);
  const alta = await page.evaluate(() => Math.round(document.querySelector(".tb").getBoundingClientRect().height));
  assert.ok(alta <= 64, "barra alta su una riga a 1366 px: " + alta + " px");
  assert.equal(await page.getAttribute("body", "data-barra"), "icone");
  assert.equal(await page.getByRole("button", { name: "Impostazioni", exact: true }).count(), 1, "nome accessibile del pulsante a icona");
  assert.ok(await page.getAttribute("#bImpost", "title"));
  await page.setViewportSize({ width: 1920, height: 900 });
  await page.waitForFunction(() => document.body.dataset.barra === "");
  await page.setViewportSize({ width: 1366, height: 657 });
  await page.waitForFunction(() => document.body.dataset.barra === "icone");

  // 3. Ctrl+G: finestra con la sigla (nessun prompt del browser); un quadro inesistente lo dice e la finestra resta aperta
  let nativo = false; const suPrompt = d => { if (d.type() === "prompt") { nativo = true; d.dismiss().catch(() => {}); } }; page.on("dialog", suPrompt);
  await page.evaluate(id => apri(id), pid);
  await page.waitForFunction(() => S.P && document.querySelector(".voce[data-q=EC]"));
  await page.keyboard.press("Control+g");
  await page.waitForSelector("#dVai[open] #vaiSigla");
  await page.fill("#vaiSigla", "ZZ"); await page.press("#vaiSigla", "Enter");
  assert.match(await page.textContent("#dVai p.e"), /Quadro ZZ non trovato/);
  await page.fill("#vaiSigla", "ec"); await page.press("#vaiSigla", "Enter");
  await page.waitForFunction(() => S.sel === "EC" && !document.querySelector("#dVai[open]"));
  assert.equal(nativo, false, "nessun prompt() nativo"); page.off("dialog", suPrompt);

  // 4. campi del pannello: il nome letto e' l'etichetta, non il nome interno
  await page.click('#vista tbody tr[data-key="e:beni:b_rev4000000"]');
  await page.waitForSelector('#ins [name="foglio"]');
  assert.equal(await page.getByRole("textbox", { name: "foglio", exact: true }).count(), 0);
  const nomeFoglio = await page.evaluate(() => document.querySelector('#ins [name="foglio"]').getAttribute("aria-label"));
  assert.equal(nomeFoglio, await page.evaluate(() => lbl("beni", "foglio")));
  assert.ok(!/_/.test(await page.evaluate(() => document.querySelector('#ins [name="quota_defunto"]').getAttribute("aria-label"))), "quota senza nome interno");

  // 5. un tasto nel pannello ridisegna solo la riga (segno «modificato» e totale aggiornati), non la tabella
  await page.evaluate(() => { window.__vista = 0; const orig = renderVista; window.renderVista = (...a) => { window.__vista++; return orig(...a); }; });
  const altra = await page.evaluate(() => document.querySelector('#vista tbody tr[data-key="e:beni:b_rev4000005"]') !== null && (window.__altra = document.querySelector('#vista tbody tr[data-key="e:beni:b_rev4000005"]'), true));
  assert.ok(altra);
  await page.fill('#ins [name="valore"]', "70.000");
  await page.fill('#ins [name="foglio"]', "19");
  const dopo = await page.evaluate(() => ({ vista: window.__vista, stessa: window.__altra.isConnected, mod: document.querySelector('#vista tr[data-key="e:beni:b_rev4000000"]').classList.contains("mod"),
    foglio: document.querySelector('#vista tr[data-key="e:beni:b_rev4000000"]').textContent, totale: document.querySelector("#vista tfoot").textContent,
    focus: document.activeElement.getAttribute("name") }));
  assert.equal(dopo.vista, 0, "nessun ridisegno dell'intera vista mentre si scrive");
  assert.equal(dopo.stessa, true, "le altre righe non vengono ricreate");
  assert.equal(dopo.mod, true, "segno «modificato» sulla riga");
  assert.match(dopo.foglio, /19/);
  assert.match(dopo.totale, /2\.527\.000/, "totale aggiornato");
  assert.equal(dopo.focus, "foglio", "il focus resta nel campo");
  await page.evaluate(() => { S.dirty.clear(); render(); });

  // 6. valori catastali: una richiesta per revisione, non a ogni riga selezionata
  let richieste = 0; const conta = r => { if (r.url().includes("/valori-catastali")) richieste++; }; page.on("request", conta);
  await page.evaluate(() => { VALORI_CAT.chiave = null; });
  for (const n of [1, 2, 3, 4]) { await page.click(`#vista tbody tr[data-key="e:beni:b_rev400000${n}"]`); await page.waitForSelector("#ins .vc strong"); }
  assert.equal(richieste, 1, "una sola richiesta per 4 righe");
  await page.fill('#ins [name="particella"]', "999");
  const salvato = await page.evaluate(async () => { const ok = await salvaTutto(); return { ok, n: nMod(), msg: document.querySelector("#msg").textContent, d: [...S.dirty.keys()] }; });
  assert.equal(salvato.n, 0, "salvataggio: " + JSON.stringify(salvato));
  await page.click('#vista tbody tr[data-key="e:beni:b_rev4000002"]'); await page.waitForSelector("#ins .vc strong");
  assert.equal(richieste, 2, "nuova revisione: nuova richiesta");
  page.off("request", conta);

  // 7. schede Dati/Controlli/Cronologia con le frecce; tabindex mobile e aria-controls
  await page.focus('#ins [role=tab][aria-selected=true]');
  assert.equal(await page.getAttribute('#ins [role=tab][aria-selected=true]', "aria-controls"), "insPannello");
  assert.equal(await page.locator('#ins [role=tab][tabindex="0"]').count(), 1);
  await page.keyboard.press("ArrowRight");
  await page.waitForFunction(() => S.tab === "controlli" && document.activeElement.getAttribute("role") === "tab" && document.activeElement.id === "insTab_controlli");
  await page.keyboard.press("End");
  await page.waitForFunction(() => S.tab === "cronologia" && document.activeElement.id === "insTab_cronologia");
  await page.keyboard.press("ArrowRight");
  await page.waitForFunction(() => S.tab === "dati" && document.activeElement.id === "insTab_dati");

  // 8. menu Operazioni: frecce, Home/Fine, Esc torna al pulsante
  await page.focus("#vista details.operazioni > summary");
  await page.keyboard.press("ArrowDown");
  await page.waitForFunction(() => document.activeElement.getAttribute("role") === "menuitem");
  const primaVoce = await page.evaluate(() => document.activeElement.textContent);
  await page.keyboard.press("ArrowDown");
  assert.notEqual(await page.evaluate(() => document.activeElement.textContent), primaVoce);
  await page.keyboard.press("End");
  assert.match(await page.evaluate(() => document.activeElement.textContent), /Elimina la riga selezionata/);
  await page.keyboard.press("ArrowDown");
  assert.equal(await page.evaluate(() => document.activeElement.textContent), primaVoce, "dall'ultima voce si torna alla prima");
  await page.keyboard.press("Escape");
  assert.equal(await page.evaluate(() => document.activeElement.tagName + ":" + document.querySelector("details.operazioni").open), "SUMMARY:false");

  // 9. Impostazioni: Chiudi ed Esc con modifiche non salvate chiedono conferma
  await page.click("#bImpost"); await page.waitForSelector("#imp[open] #aspetto_nome_studio");
  await page.click("#iChiudi"); await page.waitForFunction(() => !document.querySelector("#imp[open]"));   // nessuna modifica: chiude senza domande
  await page.click("#bImpost"); await page.waitForSelector("#imp[open] #aspetto_nome_studio");
  await page.fill("#aspetto_nome_studio", "Studio di prova e2e");
  let domanda = "";
  page.once("dialog", d => { domanda = d.message(); d.dismiss(); });
  await page.click("#iChiudi");
  assert.match(domanda, /modifiche non salvate nelle Impostazioni/);
  assert.equal(await page.isVisible("#imp[open]"), true, "annullando resta aperta");
  page.once("dialog", d => d.dismiss());
  await page.keyboard.press("Escape");
  await page.waitForTimeout(200);
  assert.equal(await page.isVisible("#imp[open]"), true, "Esc annullato: resta aperta");
  page.once("dialog", d => d.accept());
  await page.click("#iChiudi");
  await page.waitForFunction(() => !document.querySelector("#imp[open]"));
  assert.notEqual(await page.evaluate(() => document.title), "Successioni · Studio di prova e2e", "modifica scartata");

  // 10. apri(): con modifiche non salvate e conferma annullata la pratica «ultima» non cambia
  const altraPid = await page.evaluate(async () => (await post("/api/pratiche", { titolo: "Review4 seconda e2e" })).pratica_id);
  await page.evaluate(() => scegliQuadro("EC"));
  await page.click('#vista tbody tr[data-key="e:beni:b_rev4000003"]');
  await page.fill('#ins [name="particella"]', "77");
  page.once("dialog", d => d.dismiss());
  await page.evaluate(id => apri(id), altraPid);
  assert.equal(await page.evaluate(() => localStorage.getItem("successioni.ultima")), pid, "ultima invariata se l'apertura e' annullata");
  await page.evaluate(() => { S.dirty.clear(); });
  await page.evaluate(id => apri(id), altraPid);
  assert.equal(await page.evaluate(() => localStorage.getItem("successioni.ultima")), altraPid);
  assert.equal(await page.evaluate(() => nMod()), 0, "un evento tardivo del campo non porta modifiche nella pratica appena aperta");

  // 11. 390 px: nessuno scorrimento orizzontale (titolo lungo, barra di stato); cassetto con il focus trattenuto
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(id => apri(id), pid);
  const largo = () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  assert.equal(await largo(), 0, "pratica a 390 px senza scorrimento orizzontale");
  await page.click("#bHome"); await page.waitForSelector("#elencoPratiche .apri-pratica .tit");
  await page.waitForTimeout(300);
  assert.equal(await largo(), 0, "pagina iniziale a 390 px senza scorrimento orizzontale");
  await page.evaluate(id => apri(id), pid);
  await page.click("#bNav");
  await page.waitForFunction(() => document.body.classList.contains("navAperta") && document.getElementById("lat").contains(document.activeElement));
  for (let i = 0; i < 80; i++) {
    await page.keyboard.press("Tab");
    assert.equal(await page.evaluate(() => document.getElementById("lat").contains(document.activeElement)), true, "Tab resta nel cassetto (" + i + ")");
  }
  await page.keyboard.press("Shift+Tab");
  assert.equal(await page.evaluate(() => document.getElementById("lat").contains(document.activeElement)), true);
  await page.keyboard.press("Escape");
  assert.equal(await page.evaluate(() => document.activeElement.id), "bNav");
  await page.setViewportSize({ width: 1366, height: 657 });

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
