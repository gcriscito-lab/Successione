"use strict";
// Miglioramenti dall'analisi del 07/11/2026 (docs/ANALISI_REPLICA_2026-11-07.md), dati SINTETICI:
// 22 somma delle quote nella scheda del bene, 19 rimedio nei controlli, 5 modifica di gruppo (una sola revisione),
// 9 incolla da Excel, 33 riepilogo del soggetto, 10 appunti e stato del quadro (note interne: impronta invariata),
// 8 filtri della pagina iniziale. Uso: node gui_miglioramenti_replica.js [url]  (server sintetico: tests/e2e/server.py, porta 8813)
const assert = require("node:assert/strict");
async function run(page, url = "http://127.0.0.1:8813/?t=t0k") {
  const errori = []; page.on("pageerror", e => errori.push(String(e)));
  await page.goto(url);
  await page.waitForFunction(() => typeof S !== "undefined" && S.schema);
  const pid = await page.evaluate(async () => {
    const fab = (id, p) => ({ op: "upsert", coll: "beni", id, campi: { tipo: "fabbricato", comune: "Roma", foglio: "1", particella: p,
      categoria: "A/2", rendita: "500.00", diritto: "1", quota_defunto: "1/1", valore: "63000" } });
    const per = (id, cognome, nome) => ({ op: "upsert", coll: "persone", id, campi: { ruolo: "erede", cognome, nome } });
    const dv = (id, b, p, q) => ({ op: "upsert", coll: "devoluzioni", id, campi: { bene_id: b, persona_id: p, quota: q, diritto: "1" } });
    const r = await post("/api/pratiche", { titolo: "Miglioramenti replica e2e", iniziali: [
      { op: "upsert", coll: "persone", id: "p_defunto9", campi: { ruolo: "defunto", cognome: "Prova", nome: "Replica", data_decesso: "2025-05-10" } },
      per("p_annaa001", "BIANCHI", "ANNA"), per("p_lucaa001", "BIANCHI", "LUCA"),
      fab("b_casa0001", "11"), fab("b_casa0002", "12"),
      dv("d_uno00001", "b_casa0001", "p_annaa001", "1/2"), dv("d_due00001", "b_casa0001", "p_lucaa001", "1/2"),
      dv("d_tre00001", "b_casa0002", "p_annaa001", "1/2")] });
    await apri(r.pratica_id);
    return r.pratica_id;
  });
  const leggi = () => page.evaluate(async id => api("/api/pratiche/" + id), pid);

  // 22: somma delle quote nella scheda del bene
  await page.evaluate(() => scegliQuadro("EC"));
  await page.waitForSelector('#vista tr[data-key="e:beni:b_casa0002"]');
  await page.click('#vista tr[data-key="e:beni:b_casa0002"]');
  assert.match(await page.textContent("#ins .dv-bene"), /1\/2 · manca 1\/2/);
  await page.click('#vista tr[data-key="e:beni:b_casa0001"]');
  assert.match(await page.textContent("#ins .dv-bene"), /1\/1 · completa/);

  // 19: rimedio nei controlli
  await page.evaluate(() => { S.tab = "controlli"; renderIns(); });
  const controlli = await page.textContent("#ins");
  assert.match(controlli, /Come risolvere: Nel quadro DV aggiungi la riga/);
  await page.evaluate(() => { S.tab = "dati"; renderIns(); });

  // 5: modifica di gruppo, una sola revisione
  const prima = await leggi();
  await page.evaluate(() => modificaDiGruppo(quadro()));
  await page.fill('#dGruppo [data-gruppo="quota_defunto"] input:not([type=checkbox])', "1/2");
  await page.click("#dGruppo button.pil");
  const dirty = await page.evaluate(() => [...S.dirty.values()].map(d => [d.id, d.campi.quota_defunto]));
  assert.deepEqual(dirty.sort(), [["b_casa0001", { num: 1, den: 2 }], ["b_casa0002", { num: 1, den: 2 }]]);
  await page.evaluate(() => salvaTutto());
  await page.waitForFunction(() => S.dirty.size === 0, null, { timeout: 20000 });
  const dopo = await leggi();
  assert.equal(dopo.revisione, prima.revisione + 1, "la modifica di gruppo crea una sola revisione");
  const quota = v => typeof v === "string" ? v.replace(/\s/g, "") : v.num + "/" + v.den;
  assert.deepEqual(dopo.dati.beni.map(b => quota(b.quota_defunto)), ["1/2", "1/2"]);

  // 9: incolla da Excel nel quadro EA (righe nuove, non salvate)
  await page.evaluate(() => scegliQuadro("EA"));
  await page.waitForSelector('#vista tr[data-key="e:persone:p_annaa001"]');
  const testo = await page.evaluate(() => {   // righe costruite nell'ordine delle colonne della tabella, con l'intestazione
    const q = quadro(), cols = colonneIncolla(q), riga = v => cols.map(c => v[c] || "").join("\t");
    incollaRighe(q);
    return [cols.map(c => lbl(q.coll, c, q.id)).join("\t"), riga({ cognome: "VERDI", nome: "MARIA" }), riga({ cognome: "NERI", nome: "PAOLO" })].join("\n");
  });
  await page.fill("#dIncolla textarea", testo);
  await page.click("#dIncolla button.pil");
  const nuove = await page.evaluate(() => [...S.nuove.values()].map(n => [n.campi.cognome, n.campi.nome, n.campi.ruolo]));
  assert.deepEqual(nuove, [["VERDI", "MARIA", "erede"], ["NERI", "PAOLO", "erede"]]);
  await page.evaluate(() => { S.nuove.clear(); render(); });

  // 33: riepilogo del soggetto con i beni ricevuti
  await page.click('#vista tr[data-key="e:persone:p_annaa001"]');
  const riep = await page.textContent("#ins .riepilogo-soggetto");
  assert.match(riep, /fg\.1 p\.11/); assert.match(riep, /fg\.1 p\.12/);

  // 10: appunti e stato del quadro: note interne, impronta dichiarativa invariata
  const impronta = (await leggi()).impronta_dichiarativa;
  await page.click("#ins .appunti-riga summary");
  await page.fill("#ins textarea.appunti", "Chiedere copia del documento");
  await page.click("#ins .appunti-riga button");
  await page.waitForFunction(id => api("/api/pratiche/" + id).then(r => ((r.dati.note || {}).appunti || {})["persone:p_annaa001"]), pid, { timeout: 20000 });
  await page.waitForFunction(() => !S.writeBusy && document.querySelector(".sottotitolo .stato-lavoro"), null, { timeout: 20000 });
  await page.selectOption(".sottotitolo .stato-lavoro", "da_controllare");
  await page.waitForFunction(() => document.querySelector('.voce[data-q="EA"]') && document.querySelector('.voce[data-q="EA"]').dataset.lavoro === "da_controllare", null, { timeout: 20000 });
  const fine = await leggi();
  assert.equal(fine.dati.note.stato_quadri.EA, "da_controllare");
  assert.equal(fine.impronta_dichiarativa, impronta, "appunti e stato non cambiano il dichiarato");

  // 8: filtri della pagina iniziale (funzione pura, date relative a oggi)
  const filtri = await page.evaluate(() => {
    const g = n => { const d = new Date(); d.setFullYear(d.getFullYear() - 1); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };
    const el = [{ id: "a", titolo: "Alfa", data_decesso: g(30) }, { id: "b", titolo: "Beta", data_decesso: g(-10) }, { id: "c", titolo: "Gamma", data_decesso: null },
      { id: "d", titolo: "Delta", data_decesso: g(200) }];
    const ids = l => l.map(x => x.id).join("");
    return { vicine: ids(praticheFiltrate(el, "vicine", "recenti", "")), superate: ids(praticheFiltrate(el, "superate", "recenti", "")),
      senza: ids(praticheFiltrate(el, "senza_data", "recenti", "")), scad: ids(praticheFiltrate(el, "tutte", "scadenza", "")), cerca: ids(praticheFiltrate(el, "tutte", "recenti", "ELT")) };
  });
  assert.deepEqual(filtri, { vicine: "a", superate: "b", senza: "c", scad: "badc", cerca: "d" });
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
