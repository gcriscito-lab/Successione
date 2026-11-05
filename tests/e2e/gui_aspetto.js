"use strict";
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1500, height: 980 } });
    const errori = [];
    page.on('pageerror', e => errori.push(e.message));
    await page.goto('http://127.0.0.1:8813/?t=t0k');
    await page.waitForLoadState('networkidle');
    await page.waitForFunction(() => S.schema && preferenze);
    assert.equal(await page.getByAltText('Logo Successioni').isVisible(), true);
    await page.screenshot({ path: 'build/aspetto_home.png', fullPage: true });

    await page.locator('#bImpost').click();
    await page.getByLabel('Tema', { exact: true }).selectOption('sistema');
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.waitForFunction(() => document.documentElement.dataset.tema === 'scuro');
    await page.emulateMedia({ colorScheme: 'light' });
    await page.waitForFunction(() => document.documentElement.dataset.tema === 'chiaro');
    await page.getByLabel('Tema', { exact: true }).selectOption('scuro');
    await page.getByLabel('Carattere', { exact: true }).selectOption('verdana');
    await page.getByLabel('Dimensione del testo').selectOption('18');
    await page.getByLabel('Spaziatura delle righe').selectOption('ampia');
    assert.equal(await page.evaluate(() => document.documentElement.dataset.tema), 'scuro');
    assert.equal(await page.evaluate(() => getComputedStyle(document.body).fontSize), '18px');
    assert.ok((await page.evaluate(() => getComputedStyle(document.body).fontFamily)).includes('Verdana'));
    await page.screenshot({ path: 'build/aspetto_impostazioni.png', fullPage: true });
    const salvato = page.waitForResponse(r => r.url().includes('/api/impostazioni') && r.request().method() === 'POST');
    await page.locator('#iSalva').click(); assert.equal((await salvato).status(), 200);
    await page.locator('#iChiudi').click();
    await page.reload(); await page.waitForLoadState('networkidle');
    assert.equal(await page.evaluate(() => preferenze.dimensione), 18);
    assert.equal(await page.evaluate(() => document.documentElement.dataset.tema), 'scuro');
    await page.locator('#bImpost').click();
    await page.getByLabel('Tema', { exact: true }).selectOption('seppia');
    await page.locator('#iChiudi').click();
    await page.waitForFunction(() => document.documentElement.dataset.tema === 'scuro');
    assert.equal(await page.evaluate(() => document.documentElement.dataset.tema), 'scuro');
    // Salvataggio tema chiaro, taglia normale per la verifica dei campi.
    await page.locator('#bImpost').click();
    await page.getByLabel('Tema', { exact: true }).selectOption('chiaro');
    await page.getByLabel('Dimensione del testo').selectOption('14');
    await page.getByLabel('Carattere', { exact: true }).selectOption('sistema');
    await page.getByLabel('Spaziatura delle righe').selectOption('normale');
    const normale = page.waitForResponse(r => r.url().includes('/api/impostazioni') && r.request().method() === 'POST');
    await page.locator('#iSalva').click(); await normale; await page.locator('#iChiudi').click();
    const pid = await page.evaluate(async () => {
      const p = await post('/api/pratiche', { titolo: 'Prova nuovo spazio di lavoro', iniziali: [
        { op: 'upsert', coll: 'persone', id: 'p_def0001', campi: { ruolo: 'defunto', cognome: 'Rossi', nome: 'Mario', luogo_nascita: 'Roma', provincia_nascita: 'RM' } },
        { op: 'upsert', coll: 'beni', id: 'b_casa0001', campi: { tipo: 'fabbricato', comune: 'Roma', provincia: 'RM', foglio: '1', particella: '2' } }] });
      await apri(p.pratica_id); return p.pratica_id;
    });
    assert.equal(await page.getByRole('heading', { name: '1. Defunto', exact: true }).count(), 1);
    await page.locator('#vista [aria-label="provincia_nascita"]').first().selectOption('TO');
    await page.locator('#bSalva').click(); await page.waitForFunction(() => !S.writeBusy && nMod() === 0);
    assert.equal(await page.evaluate(() => S.P.dati.persone[0].provincia_nascita), 'TO');
    await page.screenshot({ path: 'build/aspetto_generali.png', fullPage: true });
    await page.locator('[data-q="EC"]').click();
    await page.locator('#vista tbody tr[data-key]').click();
    assert.equal(await page.locator('#ins [aria-label="provincia"]').isVisible(), true);
    assert.equal(await page.getByRole('tab', { name: 'File', exact: true }).count(), 0);
    const minimaSalvata = page.waitForResponse(r => r.url().includes('/api/impostazioni') && r.request().method() === 'POST');
    await page.locator('#ridimensiona').focus(); await page.keyboard.press('Home'); await minimaSalvata;
    const precedente = await page.locator('#ins').boundingBox();
    const bordo = await page.locator('#ridimensiona').boundingBox();
    const larghezzaSalvata = page.waitForResponse(r => r.url().includes('/api/impostazioni') && r.request().method() === 'POST');
    await page.mouse.move(bordo.x + bordo.width / 2, bordo.y + 100);
    await page.mouse.down(); await page.mouse.move(bordo.x - 120, bordo.y + 100, { steps: 12 }); await page.mouse.up();
    await larghezzaSalvata;
    const nuova = await page.locator('#ins').boundingBox(); assert.ok(nuova.width > precedente.width + 100);
    await page.locator('#bGenera').click(); await page.getByRole('heading', { name: 'Fornitore e impegno alla trasmissione' }).waitFor();
    assert.equal(await page.locator('#ins').isVisible(), false);
    await page.getByLabel('Codice fiscale del fornitore', { exact: true }).fill('RSSMRA40A01H501K');
    await page.locator('[data-q="EA"]').click();
    assert.equal(await page.getByLabel('Codice fiscale del fornitore', { exact: true }).count(), 0);
    await page.locator('#navFile').click();
    assert.equal(await page.getByLabel('Codice fiscale del fornitore', { exact: true }).inputValue(), 'RSSMRA40A01H501K');
    await page.locator('#bSalva').click(); await page.waitForFunction(() => !S.writeBusy && nMod() === 0);
    await page.screenshot({ path: 'build/aspetto_file.png', fullPage: true });
    const desiderata = await page.evaluate(() => preferenze.larghezza_pannello);
    await page.reload(); await page.waitForLoadState('networkidle');
    await page.evaluate(async id => { await apri(id); scegliQuadro('EC'); }, pid);
    assert.equal(await page.evaluate(() => preferenze.larghezza_pannello), desiderata);
    assert.ok(Math.abs((await page.locator('#ins').boundingBox()).width - desiderata) < 2);
    await page.locator('#bNuova').click();
    await page.locator('#w_cognome').fill('Provincia sintetica');
    await page.locator('#w_luogo_nascita').fill('Roma');
    await page.locator('#w_provincia_nascita').fill('rm');
    await page.locator('#w_comune_decesso').fill('Torino');
    await page.locator('#w_provincia_decesso').fill('to');
    for (let i = 0; i < 4; i++) await page.locator('#wAvanti').click();
    await page.waitForFunction(() => S.P.titolo.includes('Provincia sintetica'));
    const defunto = await page.evaluate(() => S.P.dati.persone.find(p => p.ruolo === 'defunto'));
    assert.equal(defunto.provincia_nascita, 'RM'); assert.equal(defunto.provincia_decesso, 'TO');
    // Schermo stretto: niente separatore e niente contenuto fuori viewport.
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.locator('#ridimensiona').isVisible(), false);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    assert.deepEqual(errori, []);
    console.log(JSON.stringify({ esito: 'passato', casi: ['logo iniziale', 'font/dimensione/tema', 'persistenza', 'annulla anteprima', 'provincia', 'pannello mouse', 'file unico', 'profilo conservato', 'responsive'], errori }));
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
