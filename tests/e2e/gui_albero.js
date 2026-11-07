"use strict";
// Albero genealogico generato dai dati (quadro EG, rigo EG6; docs/regole/albero_genealogico.md). Dati SINTETICI.
// Il pulsante del quadro EG genera il PDF, lo collega all'unico rigo EG6 e mostra l'anteprima; un albero caricato a mano non si
// sostituisce senza conferma e il file resta fra i documenti. Uso: node gui_albero.js [url]  (server tests/e2e/server.py, porta 8813)
const assert = require("node:assert/strict");
async function run(page, url = "http://127.0.0.1:8813/?t=t0k") {
  const errori = []; page.on("pageerror", e => errori.push(String(e)));
  await page.goto(url);
  await page.waitForFunction(() => typeof S !== "undefined" && S.schema);
  const pid = await page.evaluate(async () => {
    const P = (id, campi) => ({ op: "upsert", coll: "persone", id, campi });
    const r = await post("/api/pratiche", { titolo: "Albero genealogico e2e", iniziali: [
      P("p_def0001", { ruolo: "defunto", cognome: "Sintetico", nome: "Mario", luogo_nascita: "Roma", data_nascita: "1940-01-01", data_decesso: "2025-03-10" }),
      P("p_con0001", { ruolo: "erede", cognome: "Coniugata", nome: "Anna", luogo_nascita: "Milano", data_nascita: "1945-05-05", grado_parentela: "01", tipo_soggetto: "1" }),
      P("p_fig0001", { ruolo: "erede", cognome: "Sintetico", nome: "Luca", grado_parentela: "02", tipo_soggetto: "1" })] });
    await apri(r.pratica_id);
    return r.pratica_id;
  });
  await page.evaluate(() => scegliQuadro("EG"));
  await page.waitForSelector("#albero_genera");
  assert.match(await page.textContent("#albero_stato"), /Nessun albero/);
  assert.match(await page.textContent("#albero_mancanti"), /Sintetico Luca: luogo di nascita, data di nascita/);
  await page.click("#albero_genera");
  await page.waitForSelector("#albero_anteprima", { timeout: 60000 });
  assert.match(await page.textContent("#albero_stato"), /generato dai dati attuali/);
  const info = await page.evaluate(async id => {
    const p = await api("/api/pratiche/" + id);
    const refs = p.dati.documenti_ref.filter(r => r.tipo_eg === "AlberoGenealogico");
    const f = await fetch("/api/allegati/" + refs[0].allegato_id + "/file");
    const testa = new Uint8Array(await f.arrayBuffer()).slice(0, 5);
    return { n: refs.length, tipo: f.headers.get("content-type"), testa: String.fromCharCode(...testa),
             src: document.querySelector("#albero_anteprima").getAttribute("src"), aid: refs[0].allegato_id };
  }, pid);
  assert.equal(info.n, 1, "un solo rigo EG6");
  assert.equal(info.tipo, "application/pdf"); assert.equal(info.testa, "%PDF-");
  assert.equal(info.src, "/api/allegati/" + info.aid + "/file");
  // seconda pressione con dati invariati: nessuna nuova versione
  await page.click("#albero_genera");
  await page.waitForFunction(() => /già aggiornato/.test(document.querySelector("#msg").textContent));
  // albero caricato a mano sul rigo EG6: sostituisce quello generato (un solo rigo), poi la generazione chiede conferma
  await page.setInputFiles("#file", { name: "albero_studio.pdf", mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF") });
  await page.selectOption("#teg", "AlberoGenealogico");
  await page.click("text=Aggiungi al quadro EG");
  await page.waitForFunction(() => /caricato a mano/.test((document.querySelector("#albero_stato") || {}).textContent || ""), null, { timeout: 60000 });
  const dopoManuale = await page.evaluate(async id => (await api("/api/pratiche/" + id)).dati.documenti_ref.filter(r => r.tipo_eg === "AlberoGenealogico").length, pid);
  assert.equal(dopoManuale, 1, "il file caricato prende il posto dell'albero generato");
  let domanda = "";
  page.once("dialog", d => { domanda = d.message(); d.dismiss(); });
  await page.click("#albero_genera");
  await page.waitForFunction(() => !document.querySelector("#albero_genera").disabled);
  assert.match(domanda, /caricato a mano/);
  assert.match(await page.textContent("#albero_stato"), /caricato a mano/, "senza conferma resta l'albero manuale");
  page.once("dialog", d => d.accept());
  await page.click("#albero_genera");
  await page.waitForFunction(() => /generato dai dati attuali/.test((document.querySelector("#albero_stato") || {}).textContent || ""), null, { timeout: 60000 });
  const fine = await page.evaluate(async id => {
    const al = await api("/api/pratiche/" + id + "/allegati");
    return { manuale: al.some(a => a.nome.startsWith("albero_studio")),
             refs: (await api("/api/pratiche/" + id)).dati.documenti_ref.filter(r => r.tipo_eg === "AlberoGenealogico").length };
  }, pid);
  assert.equal(fine.refs, 1); assert.equal(fine.manuale, true, "il file caricato a mano resta fra i documenti");
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
