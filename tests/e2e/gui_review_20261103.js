"use strict";
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const fixture = JSON.parse(require('node:fs').readFileSync('build/gui_review_fixture.json', 'utf8'));

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    const errori = [];
    page.on('pageerror', e => errori.push(e.message));
    await page.goto('http://127.0.0.1:8813/?t=t0k');
    await page.waitForLoadState('networkidle');
    await page.waitForFunction(() => S.schema);
    await page.evaluate(async () => {
      const p = await post('/api/pratiche', { titolo: 'Frontespizio e superficie', iniziali: [
        { op: 'upsert', coll: 'persone', id: 'p_gui0001', campi: { ruolo: 'defunto', cognome: 'Sintetico' } },
        { op: 'upsert', coll: 'beni', id: 'b_terr0001', campi: { tipo: 'terreno', foglio: '1', particella: '2' } }] });
      await apri(p.pratica_id);
    });
    await page.getByLabel('Stato civile del defunto', { exact: true }).selectOption('2');
    await page.getByLabel('IBAN del versamento', { exact: true }).fill('IT60X0542811101000000123456');
    assert.equal(await page.evaluate(() => nMod()), 2);
    await page.evaluate(() => { S.sel = 'EA'; render(); S.sel = 'AN'; render(); });
    assert.equal(await page.getByLabel('Stato civile del defunto', { exact: true }).inputValue(), '2');
    await page.keyboard.press('Control+s');
    await page.waitForFunction(() => !S.writeBusy && nMod() === 0 && S.P.revisione === 2);
    assert.equal(await page.evaluate(() => S.P.dati.opzioni.telematico.dichiarazione.stato_civile), '2');

    // Digitazione durante il salvataggio: resta nel buffer e viene salvata una volta sola.
    let release, received;
    const gate = new Promise(r => release = r), risposta = new Promise(r => received = r);
    await page.route('**/aggiorna', async route => { const response = await route.fetch(); received(); await gate; await route.fulfill({ response }); });
    await page.getByLabel('Stato civile del defunto', { exact: true }).selectOption('3');
    await page.locator('#bSalva').click(); await risposta;
    await page.getByLabel('Stato civile del defunto', { exact: true }).selectOption('4');
    release(); await page.waitForFunction(() => !S.writeBusy && S.P.revisione === 3);
    assert.equal(await page.getByLabel('Stato civile del defunto', { exact: true }).inputValue(), '4');
    assert.equal(await page.evaluate(() => nMod()), 1);
    await page.unroute('**/aggiorna');
    await page.locator('#bSalva').click();
    await page.waitForFunction(() => !S.writeBusy && nMod() === 0);

    await page.evaluate(() => { S.sel = 'EB'; render(); });
    await page.locator('#vista tbody tr[data-key]').first().click();
    await page.getByLabel('superficie ettari').fill('2');
    await page.getByLabel('superficie are').fill('15');
    await page.locator('#bSalva').click();
    await page.waitForFunction(() => !S.writeBusy && nMod() === 0);
    assert.deepEqual(await page.evaluate(() => S.P.dati.opzioni.telematico.beni.b_terr0001.superficie), { ettari: 2, are: 15 });

    // La fixture manuale viene creata da Python nel solo archivio sintetico del server.
    await page.evaluate(async pid => {
      await apri(pid);
      vaiFile();
    }, fixture.manuale);
    await page.getByLabel("Protocollo dell'invio").waitFor();
    assert.equal(await page.getByText('Invio da eseguire con gli strumenti ufficiali', { exact: false }).count(), 1);
    await page.getByLabel("Protocollo dell'invio").fill('GUI-SINTETICO-0001');
    await page.getByLabel('Evidenza verificata').fill('Collaudo locale: nessun invio reale');
    await page.getByRole('button', { name: 'Registra protocollo', exact: true }).click();
    await page.getByLabel('Tipo di ricevuta').waitFor();
    assert.equal(await page.getByText('GUI-SINTETICO-0001', { exact: false }).count(), 1);
    await page.getByLabel('Tipo di ricevuta').selectOption('registrazione');
    await page.getByLabel('Esito della ricevuta').selectOption('registrata');
    await page.getByLabel('Documento ricevuto').setInputFiles({ name: 'ricevuta_sintetica.txt', mimeType: 'text/plain', buffer: Buffer.from('ORIGINALE SINTETICO') });
    await page.getByRole('button', { name: 'Acquisisci ricevuta', exact: true }).click();
    await page.getByRole('link', { name: 'ricevuta_sintetica.txt', exact: true }).waitFor();
    const download = page.waitForEvent('download');
    await page.getByRole('link', { name: 'ricevuta_sintetica.txt', exact: true }).click();
    const d = await download; const stream = await d.createReadStream(); const chunks = [];
    for await (const c of stream) chunks.push(c);
    assert.equal(Buffer.concat(chunks).toString(), 'ORIGINALE SINTETICO');

    await page.evaluate(async pid => { await apri(pid); vaiFile(); }, fixture.export);
    await page.getByRole('link', { name: 'Prospetto tecnico del file', exact: true }).waitFor();
    // versione 0.4: il prospetto si apre nell'anteprima interna
    await page.getByRole('link', { name: 'Prospetto tecnico del file', exact: true }).click();
    await page.waitForSelector('#dAnteprima[open] iframe.anteprima-doc');
    const stampa = page.frameLocator('#dAnteprima iframe');
    await stampa.locator('section').first().waitFor();
    assert.ok((await stampa.locator('body').innerText()).includes(fixture.sha256));
    assert.equal(await stampa.locator('section').count() > 5, true);
    await page.click("#dAnteprima button:has-text('Chiudi')");
    assert.deepEqual(errori, []);
    await page.screenshot({ path: 'build/gui_review_20261103.png', fullPage: true });
    console.log(JSON.stringify({ esito: 'passato', casi: ['frontespizio condiviso', 'cambio quadro', 'Ctrl+S', 'digitazione durante HTTP', 'superficie', 'istruzioni manuali', 'protocollo', 'ricevute', 'download originale', 'stampa stessa impronta XML'], errori }));
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
