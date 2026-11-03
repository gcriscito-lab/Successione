"use strict";
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const URL = 'http://127.0.0.1:8813/?t=t0k';
const ok = m => console.log('OK   ' + m);
async function apriPratica(page, q) {
  await page.goto(URL); await page.waitForFunction(() => typeof S !== 'undefined' && S.schema && preferenze && S.pratiche);
  await page.evaluate(async () => {   // pratica sintetica propria: defunto, due eredi, un fabbricato
    const p = await post('/api/pratiche', { titolo: 'Prova layout', chiave: 'layout-' + Date.now(), iniziali: [
      { op: 'upsert', coll: 'persone', id: 'p_def0001', campi: { ruolo: 'defunto', cognome: 'Rossi', nome: 'Mario', luogo_nascita: 'Roma' } },
      { op: 'upsert', coll: 'persone', id: 'p_ere0001', campi: { ruolo: 'erede', cognome: 'Rossi', nome: 'Luca', luogo_nascita: 'Roma' } },
      { op: 'upsert', coll: 'persone', id: 'p_ere0002', campi: { ruolo: 'erede', cognome: 'Rossi', nome: 'Anna', luogo_nascita: 'Roma' } },
      { op: 'upsert', coll: 'persone', id: 'p_ere0003', campi: { ruolo: 'erede', cognome: 'Verdi', nome: 'Maria', luogo_nascita: 'Roma' } },
      { op: 'upsert', coll: 'beni', id: 'b_casa0001', campi: { tipo: 'fabbricato', comune: 'Roma', provincia: 'RM', foglio: '1', particella: '2' } }] });
    await apri(p.pratica_id);
  });
  await page.evaluate(id => scegliQuadro(id), q);
  await page.waitForSelector('#vista tbody tr');
}
(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.SX_BROWSER_CHANNEL ? { channel: process.env.SX_BROWSER_CHANNEL } : {}) });
  const errs = [], bad = [];
  const nuova = async (w, h) => {
    const ctx = await browser.newContext({ viewport: { width: w, height: h } });
    const page = await ctx.newPage();
    page.on('pageerror', e => errs.push(e.message));
    page.on('response', r => { if (r.status() >= 400 && !r.url().includes('/api/pratiche/') ) bad.push(r.status() + ' ' + r.url()); });
    return { ctx, page };
  };

  /* --- desktop 1440 --- */
  let { ctx, page } = await nuova(1440, 900);
  await apriPratica(page, 'EC');
  // n.12 favicon
  const fav = await page.evaluate(async () => (await fetch('/favicon.ico')).status);
  assert.equal(fav, 200); ok('favicon.ico servito (200)');
  assert.equal(await page.evaluate(() => document.querySelector('link[rel=icon]').getAttribute('href')), '/static/logo.svg'); ok('link rel=icon presente');
  // n.4 tooltip sulle voci e larghezza
  const senzaTitle = await page.evaluate(() => [...document.querySelectorAll('#albero .voce')].filter(v => !v.title).length);
  assert.equal(senzaTitle, 0); ok('tutte le voci della barra laterale hanno title');
  const w0 = await page.evaluate(() => document.querySelector('#lat').getBoundingClientRect().width);
  assert.ok(Math.abs(w0 - 240) < 2); ok('larghezza iniziale barra laterale 240');
  // trascinamento con il mouse
  const sep = await page.locator('#ridimensionaNav').boundingBox();
  const salvata = page.waitForResponse(r => r.url().includes('/api/impostazioni') && r.request().method() === 'POST');
  await page.mouse.move(sep.x + 5, sep.y + 200); await page.mouse.down(); await page.mouse.move(sep.x + 125, sep.y + 200, { steps: 6 }); await page.mouse.up();
  await salvata;
  const w1 = await page.evaluate(() => document.querySelector('#lat').getBoundingClientRect().width);
  assert.ok(Math.abs(w1 - 360) < 3, 'larghezza dopo trascinamento ' + w1); ok('trascinamento mouse: 240 -> ' + w1);
  assert.equal(await page.evaluate(() => preferenze.larghezza_nav), Math.round(w1));
  // memorizzata: ricarica
  await page.reload(); await page.waitForFunction(() => typeof S !== 'undefined' && S.schema);
  const w2 = await page.evaluate(() => document.querySelector('#lat').getBoundingClientRect().width);
  assert.ok(Math.abs(w2 - w1) < 2); ok('larghezza memorizzata dopo ricarica: ' + w2);
  const srv = await page.evaluate(async () => (await (await fetch('/api/impostazioni')).json()).interfaccia.larghezza_nav);
  assert.equal(srv, Math.round(w1)); ok('persistita nel file di configurazione (' + srv + ')');
  // tastiera sul separatore
  await page.locator('#ridimensionaNav').focus();
  await page.keyboard.press('Home'); await page.waitForFunction(() => preferenze.larghezza_nav === 180);
  await page.keyboard.press('ArrowRight'); await page.waitForFunction(() => preferenze.larghezza_nav === 196);
  await page.keyboard.press('End'); await page.waitForFunction(() => preferenze.larghezza_nav > 400);
  ok('separatore da tastiera: Home 180, Freccia +16, End ' + await page.evaluate(() => preferenze.larghezza_nav));
  await page.locator('#ridimensionaNav').dblclick(); await page.waitForFunction(() => preferenze.larghezza_nav === 240); ok('doppio clic: ripristino 240');
  // n.9 tastiera nella tabella
  await apriPratica(page, 'EA');
  const nr = await page.locator('#vista tbody tr').count();
  assert.ok(nr >= 3);
  const tabindex = await page.evaluate(() => [...document.querySelectorAll('#vista tbody tr')].map(t => t.getAttribute('tabindex')));
  assert.equal(tabindex.filter(x => x === '0').length, 1); ok('roving tabindex: una sola riga con tabindex 0 su ' + nr);
  await page.locator('#vista tbody tr').first().focus();
  await page.keyboard.press('ArrowDown'); await page.keyboard.press('ArrowDown');
  assert.equal(await page.evaluate(() => [...document.querySelectorAll('#vista tbody tr')].indexOf(document.activeElement)), 2); ok('frecce giu: focus alla terza riga');
  assert.equal(await page.evaluate(() => document.querySelectorAll('#vista tbody tr[tabindex="0"]').length), 1);
  await page.keyboard.press('ArrowUp');
  assert.equal(await page.evaluate(() => [...document.querySelectorAll('#vista tbody tr')].indexOf(document.activeElement)), 1); ok('freccia su');
  await page.keyboard.press('Tab');
  assert.equal(await page.evaluate(() => document.activeElement.textContent), 'Aggiungi riga'); ok('un solo Tab dalla riga porta fuori dalla tabella ("Aggiungi riga")');
  await page.keyboard.press('Shift+Tab');
  assert.equal(await page.evaluate(() => document.activeElement.tagName), 'TR');
  await page.keyboard.press('Enter');
  const inPannello = await page.evaluate(() => !!document.activeElement.closest('#ins') && /INPUT|SELECT/.test(document.activeElement.tagName));
  assert.ok(inPannello); ok('Invio: focus sul primo campo del pannello (' + await page.evaluate(() => document.activeElement.getAttribute('aria-label')) + ')');
  const sel = await page.evaluate(() => document.querySelectorAll('#vista tr[aria-selected=true]').length); assert.equal(sel, 1);
  await page.keyboard.press('Escape'); await page.waitForTimeout(300);
  assert.equal(await page.evaluate(() => document.activeElement.tagName + ':' + document.activeElement.getAttribute('aria-selected')), 'TR:true'); ok('Esc: focus torna sulla riga selezionata');
  // n.7 label
  await page.keyboard.press('Enter');
  await page.waitForTimeout(100);
  let lab = await page.evaluate(() => { const ls = [...document.querySelectorAll('#ins label')]; return { n: ls.length, senza: ls.filter(l => !(l.control)).length }; });
  assert.ok(lab.n > 5 && lab.senza === 0, JSON.stringify(lab)); ok('ispettore: ' + lab.n + ' label, tutte associate a un campo');
  const idDup = await page.evaluate(() => { const ids = [...document.querySelectorAll('[id]')].map(e => e.id); return ids.length - new Set(ids).size; });
  assert.equal(idDup, 0); ok('nessun id duplicato');
  const lbl = await page.evaluate(() => { const l = document.querySelector('#ins .rg > label'); const c = l.control; return { for: l.htmlFor, aria: c.getAttribute('aria-label') }; });
  assert.ok(lbl.for && lbl.aria); ok('aria-label invariati sui campi (' + lbl.aria + ')');
  // click sulla label porta il focus al campo
  await page.locator('#ins .rg > label').nth(1).click();
  assert.equal(await page.evaluate(() => document.activeElement.id), await page.evaluate(() => document.querySelectorAll('#ins .rg > label')[1].htmlFor)); ok('clic sulla label focalizza il campo');
  // schede AN (persona)
  await page.evaluate(() => scegliQuadro('AN')); await page.waitForTimeout(200);
  lab = await page.evaluate(() => { const ls = [...document.querySelectorAll('#vista label')].filter(l => !l.control); return ls.map(l => l.textContent.slice(0, 30)); });
  console.log('     AN label senza campo:', JSON.stringify(lab));
  assert.equal(lab.length, 0); ok('scheda Dati generali: ogni label associata');
  await page.evaluate(() => vaiFile()); await page.waitForTimeout(500);
  lab = await page.evaluate(() => [...document.querySelectorAll('label')].filter(l => !l.control).map(l => l.textContent.slice(0, 30)));
  console.log('     File e invio label senza campo:', JSON.stringify(lab));
  await page.evaluate(() => scegliQuadro('EC')); await page.waitForSelector('#vista tbody tr');
  await page.locator('#vista tbody tr').first().click();
  await page.waitForTimeout(100);
  lab = await page.evaluate(() => [...document.querySelectorAll('label')].filter(l => !l.control).map(l => l.textContent.slice(0, 30)));
  console.log('     EC label senza campo:', JSON.stringify(lab)); assert.equal(lab.length, 0);
  await ctx.close();

  /* --- mobile 375 --- */
  ({ ctx, page } = await nuova(375, 812));
  await apriPratica(page, 'EC');
  let m = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: innerWidth, h: document.querySelector('.tb').getBoundingClientRect().height, sb: document.querySelector('.sb').getBoundingClientRect().height,
    latVis: getComputedStyle(document.querySelector('#lat')).visibility, mainH: document.querySelector('main').getBoundingClientRect().height }));
  assert.equal(m.sw, m.iw); assert.ok(m.h < 60 && m.sb < 36, JSON.stringify(m)); assert.equal(m.latVis, 'hidden');
  ok('375: nessun overflow orizzontale, barra alta ' + Math.round(m.h) + ' px, barra di stato ' + Math.round(m.sb) + ' px (una riga), cassetto chiuso');
  const scr = await page.evaluate(() => [...document.querySelectorAll('*')].filter(e => { const c = getComputedStyle(e); return /(auto|scroll)/.test(c.overflowY) && e.scrollHeight > e.clientHeight + 1 && c.visibility !== 'hidden' && e.offsetParent !== null; }).map(e => e.tagName + '.' + e.className));
  assert.equal(scr.length, 0); ok('375: nessuno scroll verticale annidato');
  await page.screenshot({ path: 'C:/sx/g1_375_EC_dopo.png' });
  await page.locator('#bNav').click();
  assert.equal(await page.evaluate(() => getComputedStyle(document.querySelector('#lat')).visibility), 'visible');
  await page.waitForTimeout(300); await page.screenshot({ path: 'C:/sx/g1_375_nav.png' });
  assert.equal(await page.evaluate(() => document.querySelector('#bNav').getAttribute('aria-expanded')), 'true'); ok('375: cassetto si apre dal pulsante menu');
  await page.keyboard.press('Escape'); await page.waitForTimeout(300);
  assert.equal(await page.evaluate(() => getComputedStyle(document.querySelector('#lat')).visibility), 'hidden'); ok('Esc chiude il cassetto');
  await page.locator('#bNav').click(); await page.locator('#albero .voce[data-q=EA]').click();
  await page.waitForFunction(() => S.sel === 'EA'); await page.waitForTimeout(300);
  assert.equal(await page.evaluate(() => getComputedStyle(document.querySelector('#lat')).visibility), 'hidden'); ok('scelta di un quadro chiude il cassetto');
  await page.locator('#bMenu').click(); await page.waitForTimeout(100);
  const hm = await page.evaluate(() => document.querySelector('.tb').getBoundingClientRect().height);
  await page.screenshot({ path: 'C:/sx/g1_375_azioni.png' });
  assert.ok(await page.locator('#bImpost').isVisible()); ok('menu azioni (altezza barra aperta ' + Math.round(hm) + ' px)');
  await page.locator('#bMenu').click();
  await page.locator('#vista tbody tr').first().click(); await page.waitForTimeout(300);
  await page.screenshot({ path: 'C:/sx/g1_375_pannello.png' });
  m = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: innerWidth, insTop: document.querySelector('#ins').getBoundingClientRect().top }));
  assert.equal(m.sw, m.iw); ok('375: riga selezionata, pannello sotto (top ' + Math.round(m.insTop) + '), nessun overflow');
  await ctx.close();

  /* --- 768 e 1024 --- */
  for (const w of [768, 1024]) {
    ({ ctx, page } = await nuova(w, 900));
    await apriPratica(page, 'EC'); await page.locator('#vista tbody tr').first().click(); await page.waitForTimeout(200);
    const r = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: innerWidth, main: Math.round(document.querySelector('main').getBoundingClientRect().width), lat: Math.round(document.querySelector('#lat').getBoundingClientRect().width), ins: Math.round(document.querySelector('#ins').getBoundingClientRect().width) }));
    assert.equal(r.sw, r.iw); ok(w + ': nessun overflow orizzontale ' + JSON.stringify(r));
    await page.screenshot({ path: `C:/sx/g1_${w}_pannello.png` });
    await ctx.close();
  }
  assert.equal(errs.length, 0, errs.join('|')); ok('nessun errore JavaScript');
  assert.equal(bad.length, 0, bad.join('|')); ok('nessuna risposta HTTP >= 400 (favicon inclusa)');
  await browser.close();
})().catch(e => { console.error('FALLITO', e.message); process.exit(1); });

