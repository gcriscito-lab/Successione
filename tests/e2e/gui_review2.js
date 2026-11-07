"use strict";
/* Revisione 2 dell'interfaccia (dati SINTETICI, server tests/e2e/server.py sulla porta 8813):
   token tolto dall'indirizzo, doppio clic su «Crea dichiarazione» e sulle azioni di File e invio, chiave stabile di «Prepara invio»,
   messaggio italiano con server irraggiungibile, conferma di eliminazione con riga e quadro, motivi leggibili, messaggi positivi
   che spariscono da soli. Nessun controllo ufficiale o invio reale. */
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const fixture = JSON.parse(require('node:fs').readFileSync('build/gui_review_fixture.json', 'utf8'));
const URL = 'http://127.0.0.1:8813/?t=t0k';

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    const errori = [];
    page.on('pageerror', e => errori.push(e.message));
    await page.goto(URL);
    await page.waitForFunction(() => typeof S !== 'undefined' && S.schema);
    // punto 4: il token non resta nella barra degli indirizzi
    assert.equal(page.url(), 'http://127.0.0.1:8813/');
    const cookie = (await page.context().cookies()).find(c => c.name === 'successioni_8813');
    assert.ok(cookie && cookie.httpOnly && cookie.sameSite === 'Strict', 'cookie per porta, HttpOnly e SameSite=Strict');
    await page.reload(); await page.waitForFunction(() => typeof S !== 'undefined' && S.schema);   // il cookie basta

    // punto 1: doppio clic su «Crea dichiarazione» -> una sola richiesta e una sola pratica
    const prima = await page.evaluate(async () => (await api('/api/pratiche')).length);
    let rilascia; const cancello = new Promise(r => rilascia = r); let creazioni = 0; const chiavi = [];
    await page.route('**/api/pratiche', async route => {
      if (route.request().method() !== 'POST') return route.continue();
      creazioni++; chiavi.push(JSON.parse(route.request().postData()).chiave);
      const response = await route.fetch(); await cancello; await route.fulfill({ response });
    });
    await page.evaluate(() => wizApri());
    await page.locator('#w_cognome').fill('Doppioclic');
    await page.evaluate(() => { W.passo = PASSI.length - 1; wizRender(); });
    assert.equal(await page.locator('#wAvanti').textContent(), 'Crea dichiarazione');
    await page.locator('#wAvanti').dblclick();
    await page.locator('#wAvanti').click({ force: true }).catch(() => {});
    assert.equal(await page.locator('#wAvanti').isDisabled(), true, 'pulsante disabilitato durante la richiesta');
    rilascia();
    await page.waitForFunction(() => S.P && S.P.titolo.includes('Doppioclic'));
    await page.unroute('**/api/pratiche');
    assert.equal(creazioni, 1, 'una sola richiesta di creazione');
    assert.equal(await page.evaluate(async () => (await api('/api/pratiche')).length), prima + 1);
    const pidNuova = await page.evaluate(() => S.P.pratica_id);

    // punto 9: l'esito positivo sparisce da solo, l'errore resta
    await page.evaluate(() => msg('Esito positivo di prova', 'o'));
    await page.waitForFunction(() => document.querySelector('#msg').hidden, null, { timeout: 12000 });
    await page.evaluate(() => msg('Errore di prova', 'e'));
    await page.waitForTimeout(8800);
    assert.equal(await page.evaluate(() => document.querySelector('#msg').hidden), false, 'gli errori restano');
    await page.locator('#msg .x').click();

    // punto 8: la conferma dice quale riga e in quale quadro
    let testoConferma = '';
    page.once('dialog', d => { testoConferma = d.message(); d.dismiss(); });
    await page.evaluate(async () => {
      await post('/api/pratiche/' + S.P.pratica_id + '/aggiorna', { revisione_attesa: S.P.revisione, chiave: crypto.randomUUID(), operazioni: [
        { op: 'upsert', coll: 'persone', id: 'p_erede0001', campi: { ruolo: 'erede', cognome: 'Erede', nome: 'Prova' } }] });
      await ricarica(); scegliQuadro('EA');
      S.riga = righeQuadro(quadro()).find(r => r.e && r.e.id === 'p_erede0001').key; render();
    });
    await page.locator('#ins').getByRole('button', { name: 'Elimina riga' }).click();
    assert.match(testoConferma, /Erede Prova/); assert.match(testoConferma, /quadro EA/);

    // punto 6: i percorsi interni diventano quadro, riga e campo
    const leggibile = await page.evaluate(() => {
      const id = S.P.dati.persone[0].id;
      return [motivoLeggibile({ percorso: 'persone[' + id + '].codice_fiscale', messaggio: 'dato mancante' }),
        motivoLeggibile('persone[' + id + '].sesso: valore non ammesso'),
        descriviFornitore({ cf: 'RSSLCU72B02H501O', tipo: '10', impegno_codice: '2', data_impegno: '2026-10-30' }),
        descriviImporti({ totale_da_versare: '1234.50' })];
    });
    assert.ok(leggibile.slice(0, 2).every(t => t.includes('Quadro AN') && !t.includes('persone[')), leggibile.join(' / '));
    assert.equal(leggibile[2], 'RSSLCU72B02H501O (intermediario), predisposta dall\'intermediario, impegno del 30/10/2026');
    assert.equal(leggibile[3], 'totale da versare € 1.234,50');

    // punto 2: doppio clic su «Genera bozza tecnica» -> una sola esportazione, pulsanti disabilitati durante la richiesta
    await page.evaluate(() => vaiFile());
    const bozza = page.locator('#vista').getByRole('button', { name: 'Genera bozza tecnica', exact: true });
    await bozza.waitFor();
    let rilascia2; const cancello2 = new Promise(r => rilascia2 = r); let esportazioni = 0;
    await page.route('**/esporta', async route => { esportazioni++; const response = await route.fetch(); await cancello2; await route.fulfill({ response }); });
    await bozza.dblclick();
    await page.waitForTimeout(300);
    assert.equal(await bozza.isDisabled(), true);
    await page.locator('#vista').getByRole('button', { name: 'Genera file', exact: true }).click({ force: true }).catch(() => {});
    rilascia2();
    await page.waitForFunction(() => !OCCUPATI.has('esporta'));
    await page.unroute('**/esporta');
    assert.equal(esportazioni, 1, 'una sola esportazione');

    // punto 2: «Prepara invio» usa la stessa chiave finche' i dati non cambiano (pratica della fixture con file completo)
    await page.evaluate(pid => apri(pid), fixture.export);
    await page.evaluate(() => vaiFile());
    const genera = page.locator('#vista').getByRole('button', { name: 'Genera file', exact: true });
    await genera.waitFor();
    const r = page.waitForResponse(x => x.url().includes('/esporta') && x.request().method() === 'POST');
    await genera.click();
    const esito = await (await r).json();
    await page.waitForFunction(() => !OCCUPATI.has('esporta')); await page.waitForLoadState('networkidle'); await page.waitForTimeout(300);
    let prepara = 'non provato (file non completo)';
    if (esito.completo) {
      const corpi = [];
      await page.route('**/invio/prepara', async route => { corpi.push(JSON.parse(route.request().postData())); await route.continue(); });
      for (let i = 0; i < 2; i++) {
        const b = page.locator('#vista').getByRole('button', { name: 'Prepara invio', exact: true });
        await page.waitForFunction(() => { const x = [...document.querySelectorAll('#vista button')].find(b => b.textContent === 'Prepara invio'); return x && !x.disabled; });
        const risp = page.waitForResponse(x => x.url().includes('/invio/prepara'));
        await b.click(); await risp;
        await page.waitForFunction(() => !OCCUPATI.has('prepara'));
        await page.waitForLoadState('networkidle'); await page.waitForTimeout(300);
      }
      await page.unroute('**/invio/prepara');
      assert.equal(corpi.length, 2); assert.equal(corpi[0].chiave_richiesta, corpi[1].chiave_richiesta);
      prepara = 'stessa chiave su due clic';
    }
    assert.equal(await page.locator('#vista').getByText(/Fornitore: \{/).count(), 0, 'nessun JSON per fornitore/importi');

    // punto 5: server irraggiungibile -> messaggio italiano, niente «Failed to fetch»
    await page.route('**/api/**', route => route.abort('connectionrefused'));
    await page.evaluate(() => msg('Salvato (revisione 9).', 'o'));
    await page.locator('#bControlla').click();
    await page.waitForFunction(() => document.querySelector('#msg').textContent.includes('Il programma non risponde'));
    assert.equal(await page.evaluate(() => document.querySelector('#msg').className), 'e');
    await page.evaluate(pid => apri(pid), pidNuova);
    await page.waitForFunction(() => document.querySelector('#msg').textContent.includes('Il programma non risponde'));
    await page.evaluate(() => { caricaPratiche(); });                       // promessa non gestita: diventa messaggio
    await page.waitForTimeout(300);
    const testo = await page.evaluate(() => document.querySelector('#msg').textContent);
    assert.ok(testo.includes('Avvia-pratica-reale.cmd') && !/Failed to fetch/i.test(testo), testo);
    await page.unroute('**/api/**');

    assert.deepEqual(errori, []);
    console.log(JSON.stringify({ esito: 'passato', prepara, ambito: 'GUI locale, dati sintetici' }));
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
