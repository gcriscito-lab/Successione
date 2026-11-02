// Prova end-to-end dell interfaccia locale (Playwright per Node, metodo della skill webapp-testing).
// Uso (dalla radice): SUCCESSIONI_DATA=$(mktemp -d) NODE_PATH=$(npm root -g) python3 .claude/skills/webapp-testing/scripts/with_server.py \
//   --server "python3 tests/e2e/server.py" --port 8813 -- node tests/e2e/gui_flusso.js /tmp/gui.png
// Poi chiudere il server per PID: lo script di avvio puo lasciarlo attivo e falsare le prove successive.
const { chromium } = require('playwright');
const { ok } = require('./verifiche');
(async () => {
  const b = await chromium.launch(); const pg = await b.newPage({ viewport: { width: 1360, height: 820 } });
  try {
  const errs = []; pg.on('pageerror', e => errs.push(String(e))); pg.on('console', m => m.type() === 'error' && !m.text().includes('422') && errs.push(m.text()));
  await pg.goto('http://127.0.0.1:8813/?t=t0k'); await pg.waitForLoadState('networkidle');
  await pg.click('#bNuova'); await pg.fill('#w_cognome', 'Rossi'); await pg.fill('#w_nome', 'Mario'); await pg.fill('#w_codice_fiscale', 'rssmra50a01h501x'); await pg.fill('#w_data_decesso', '2026-03-14');
  for (let i = 0; i < 4; i++) await pg.click('#wAvanti');
  await pg.waitForSelector('.voce'); ok((await pg.textContent('#titolo')) === 'Successione Rossi Mario', 'pratica creata dalla procedura guidata');
  ok(await pg.locator('#ins').isVisible(), 'ispettore visibile');
  await pg.click('.voce[data-q=EC]'); await pg.getByRole('button', { name: 'Aggiungi riga' }).click();
  await pg.locator('#ins [aria-label=comune]').fill('Roma'); await pg.locator('#ins [aria-label=diritto]').fill('proprieta');
  ok((await pg.locator('#vista tbody tr').first().innerText()).includes('Roma'), 'la tabella mostra subito il valore digitato');
  ok((await pg.textContent('#bSalva')).includes('(1)'), 'contatore modifiche non salvate');
  await pg.click('#bSalva'); await pg.waitForFunction(() => document.querySelector('#msg').textContent.includes('Salvato (revisione 2)')); ok((await pg.textContent('#sb')).includes('Revisione 2'), 'salvato: revisione 2 nella barra di stato');
  await pg.click('#bControlla'); await pg.waitForSelector('#ins .rl li');
  ok((await pg.locator('#ins .rl li').count()) === 1, 'un rilievo nei controlli (foglio/particella)');
  await pg.locator('#ins .rl li button').first().click(); await pg.waitForTimeout(200);
  ok((await pg.locator('#vista tbody tr[aria-selected=true]').count()) === 1, 'il rilievo seleziona la riga');
  await pg.locator('#ins [aria-label=foglio]').fill('512'); await pg.locator('#ins [aria-label=particella]').fill('88'); await pg.locator('#ins [aria-label=quota_defunto]').fill('1/1');
  await pg.click('#ins .az .pil'); await pg.waitForFunction(() => document.querySelector('#msg').textContent.includes('Salvato (revisione 3)')); await pg.click('#bControlla'); await pg.waitForTimeout(300);
  ok((await pg.textContent('#ins')).includes('Nessun rilievo'), 'dopo la correzione nessun rilievo');
  await pg.click('#ins [role=tab]:nth-child(4)'); await pg.waitForSelector('#ins .rv'); ok((await pg.locator('#ins .rv').count()) >= 3, 'cronologia con le revisioni');
  await pg.click('#bGenera'); await pg.waitForSelector('#ins [aria-label="Codice fiscale del fornitore"]');
  await pg.fill('#ins [aria-label="Codice fiscale del fornitore"]', 'RSSNNA70A41H501X'); await pg.getByRole('button', { name: 'Genera file' }).last().click();
  await pg.waitForFunction(() => document.querySelector('#msg').textContent.includes('Nessun file parziale'));
  ok((await pg.textContent('#msg')).includes('File non generato'), 'Genera file: nessun XML parziale, motivi mostrati');
  ok((await pg.textContent('#ins')).includes('non eseguito'), 'scheda File con stati separati');
  await pg.click('.voce[data-q=EN]'); ok((await pg.textContent('#vista')).includes('non è ancora supportato'), 'quadro non supportato spiegato');
  const stati = await pg.evaluate(() => [...document.querySelectorAll('.voce')].map(v => v.dataset.q + ':' + v.dataset.stato).join(' ')); console.log(stati);
  await pg.click('.voce[data-q=EC]'); await pg.click('#vista tbody tr'); await pg.screenshot({ path: process.argv[2] });
  ok(!(await pg.textContent('#sb')).includes('null'), 'barra di stato senza la parola null'); ok((await pg.locator('#lista li').count()) === 1, 'una sola pratica nell elenco'); ok(errs.length === 0, 'nessun errore JS ' + JSON.stringify(errs));
  } finally { await b.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
