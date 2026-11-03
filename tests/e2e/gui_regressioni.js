"use strict";
// Esecuzione con un server sintetico separato: node gui_regressioni.js [url].
// run(page) e' anche utilizzabile da un runner Playwright gia' avviato.
const assert = require("node:assert/strict");

async function run(page, url = "http://127.0.0.1:8813/?t=t0k") {
  await page.goto(url);
  await page.waitForLoadState("networkidle");
  await page.waitForFunction(() => typeof S !== "undefined" && S.schema);
  async function apriCaso(beni = []) {
    return page.evaluate(async beni => {
      const r = await post('/api/pratiche', { titolo: 'Regressione GUI sintetica', iniziali: [
        { op: 'upsert', coll: 'persone', id: 'p_gui0001', campi: { ruolo: 'defunto', cognome: 'Rossi', nome: 'Mario' } },
        ...beni.map(b => ({ op: 'upsert', coll: 'beni', id: b.id, campi: b.campi }))] });
      await apri(r.pratica_id); return r.pratica_id;
    }, beni);
  }
  let release;
  try {
    await apriCaso();
    let intercettata;
    const ricevuta = new Promise(r => intercettata = r);
    const gate = new Promise(r => release = r);
    await page.route('**/aggiorna', async route => {
      const response = await route.fetch(); intercettata(); await gate; await route.fulfill({ response });
    });
    await page.locator('#vista [aria-label="nome"]').first().fill('Primo salvataggio');
    await page.locator('#bSalva').click();
    await ricevuta;
    // Nessuna seconda richiesta mentre il salvataggio e' in attesa.
    assert.equal(await page.evaluate(() => salvaTutto()), false);
    await page.locator('#vista [aria-label="nome"]').first().fill('Modifica durante attesa');
    release();
    await page.waitForFunction(() => !S.writeBusy && S.P.revisione === 2);
    const dopo = await page.evaluate(() => ({ dirty: nMod(), nome: document.querySelector('#vista [aria-label="nome"]').value }));
    assert.deepEqual(dopo, { dirty: 1, nome: 'Modifica durante attesa' });
    await page.unroute('**/aggiorna');
    await page.locator('#bSalva').click();
    await page.waitForFunction(() => !S.writeBusy && S.P.revisione === 3 && nMod() === 0);
    assert.equal(await page.evaluate(() => S.P.dati.persone[0].nome), 'Modifica durante attesa');

    await apriCaso([{ id: 'b_gui0001', campi: { tipo: 'fabbricato', descrizione: 'Originale', comune: 'Roma', foglio: '1', particella: '2' } }]);
    await page.evaluate(() => { S.sel = 'EC'; render(); });
    await page.locator('#vista tbody tr[data-key]').first().click();
    await page.locator('#ins [aria-label="descrizione"]').fill('Modifica non salvata');
    // Conferma accettata dal test; evita che il runner interattivo sospenda il caso.
    await page.evaluate(() => { window.__confermaOriginale = window.confirm; window.confirm = () => true; });
    await page.getByRole('button', { name: 'Elimina riga', exact: true }).click();
    await page.waitForFunction(() => !S.writeBusy && S.P.revisione === 2);
    assert.equal(await page.evaluate(() => nMod()), 0);
    await page.evaluate(() => salvaTutto());
    assert.equal(await page.evaluate(() => S.P.dati.beni.length), 0);

    // Nuova riga modificata durante il primo salvataggio: un solo ID, nessun doppione.
    await page.getByRole('button', { name: 'Aggiungi riga', exact: true }).click();
    await page.locator('#ins [aria-label="comune"]').fill('Roma');
    const ricevuta2 = new Promise(r => intercettata = r);
    const gate2 = new Promise(r => release = r);
    await page.route('**/aggiorna', async route => { const response = await route.fetch(); intercettata(); await gate2; await route.fulfill({ response }); });
    await page.locator('#bSalva').click(); await ricevuta2;
    await page.locator('#ins [aria-label="comune"]').fill('Torino');
    release(); await page.waitForFunction(() => !S.writeBusy && S.P.revisione === 3);
    assert.equal(await page.locator('#vista tbody tr[data-key]').count(), 1);
    assert.equal(await page.evaluate(() => nMod()), 1);
    await page.unroute('**/aggiorna');
    await page.locator('#bSalva').click();
    await page.waitForFunction(() => !S.writeBusy && S.P.revisione === 4 && nMod() === 0);
    assert.deepEqual(await page.evaluate(() => S.P.dati.beni.map(b => b.comune)), ['Torino']);

    // Una risposta 422 non cancella il buffer.
    await page.evaluate(() => { S.sel = 'AN'; render(); });
    await page.locator('#vista [aria-label="codice_fiscale"]').first().fill('errato');
    await page.locator('#bSalva').click();
    await page.waitForFunction(() => !S.writeBusy && document.querySelector('#msg').className === 'e');
    assert.equal(await page.evaluate(() => nMod()), 1);
    await page.locator('#vista [aria-label="codice_fiscale"]').first().fill('');
    await page.locator('#bSalva').click();
    await page.waitForFunction(() => !S.writeBusy && nMod() === 0);

    // Conflitto 409: nessuna sovrascrittura automatica e buffer conservato.
    await page.locator('#vista [aria-label="nome"]').first().fill('Bozza locale');
    await page.evaluate(async () => {
      await post('/api/pratiche/' + S.P.pratica_id + '/aggiorna', { revisione_attesa: S.P.revisione,
        operazioni: [{ op: 'upsert', coll: 'persone', id: 'p_gui0001', campi: { nome: 'Modifica esterna' } }] });
    });
    await page.locator('#bSalva').click();
    await page.waitForFunction(() => !S.writeBusy && document.querySelector('#msg').textContent.includes('modificata altrove'));
    assert.equal(await page.evaluate(() => nMod()), 1);
    assert.equal(await page.evaluate(() => S.P.dati.persone[0].nome), 'Modifica esterna');
    assert.equal(await page.locator('#vista [aria-label="nome"]').first().inputValue(), 'Bozza locale');
    // La ripetizione e' una scelta esplicita, dopo il messaggio di conflitto.
    await page.locator('#bSalva').click();
    await page.waitForFunction(() => !S.writeBusy && nMod() === 0);
    return { esito: 'passato', ambito: 'GUI locale, dati sintetici', casi: ['risposta lenta', 'salvataggio concorrente rifiutato', 'riga eliminata', 'nuova riga durante HTTP', '422', '409'] };
  } finally {
    if (release) release();
    await page.unroute('**/aggiorna');
    await page.evaluate(() => { if (window.__confermaOriginale) window.confirm = window.__confermaOriginale; });
  }
}
// Richiede una pratica sintetica tempestiva con EG1/EG5/EG7 gia' acquisiti.
async function runExport(page, praticaId, url = "http://127.0.0.1:8813/?t=t0k") {
  await page.goto(url);
  await page.waitForFunction(() => typeof S !== 'undefined' && S.schema);
  await page.evaluate(pid => apri(pid), praticaId);
  await page.locator('#bGenera').click();
  await page.getByLabel('Codice fiscale del fornitore', { exact: true }).fill('RSSLCU72B02H501O');
  await page.getByLabel('Tipo fornitore', { exact: true }).selectOption('10');
  await page.getByLabel('Impegno a trasmettere', { exact: true }).selectOption('2');
  await page.getByLabel('Data impegno', { exact: true }).fill('2026-10-30');
  const risposta = page.waitForResponse(r => r.url().includes('/esporta') && r.request().method() === 'POST');
  await page.locator('#vista').getByRole('button', { name: 'Genera file', exact: true }).click();
  const esito = await (await risposta).json();
  assert.equal(esito.completo, true);
  assert.equal(esito.generato, true);
  assert.equal(esito.avvisi.length > 0, true);
  await page.waitForFunction(() => document.querySelector('#msg').textContent.includes('Avvertenze:'));
  assert.deepEqual(await page.evaluate(() => S.P.dati.opzioni.fornitore), {
    cf: 'RSSLCU72B02H501O', tipo: '10', impegno_codice: '2', data_impegno: '2026-10-30'
  });
  return { esito: 'passato', ambito: 'GUI locale, profilo intermediario sintetico, export con allegati',
    completo: esito.completo, avvisi_visibili: true };
}
module.exports = { run, runExport };
if (require.main === module) (async () => {
  const { chromium } = require('playwright');
  const browser = await chromium.launch({ headless: true });
  try { console.log(JSON.stringify(await run(await browser.newPage(), process.argv[2]))); }
  finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
