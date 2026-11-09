// Genera successioni.ico dalle due SVG (variante piccola fino a 32 px, grande da 48 px).
// Uso, dalla radice: NODE_PATH=$(npm root -g) node scripts/windows/icona/genera_icona.js
// poi:               .venv\Scripts\python.exe scripts/windows/icona/componi_ico.py
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const dir = __dirname;
(async () => {
  const b = await chromium.launch();
  for (const s of [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]) {
    const svg = fs.readFileSync(path.join(dir, s <= 32 ? 'successioni-piccola.svg' : 'successioni.svg'), 'utf8');
    const p = await b.newPage({ viewport: { width: s, height: s }, deviceScaleFactor: 1 });
    await p.setContent(`<html><body style="margin:0;background:transparent">${svg.replace('<svg ', `<svg width="${s}" height="${s}" `)}</body></html>`);
    await p.screenshot({ path: path.join(dir, 'png', `${s}.png`), omitBackground: true, clip: { x: 0, y: 0, width: s, height: s } });
    await p.close();
  }
  await b.close();
  console.log('png pronti');
})();
