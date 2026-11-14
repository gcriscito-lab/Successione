// Genera i PDF SINTETICI delle «Risultanze catastali» usati da tests/test_visura_pdf.py.
// Riproduce l'impaginazione della pagina di Entratel salvata dal browser (testata «Etichetta: valore», tabella con intestazioni
// centrate, titolarita' su due righe, zona e categoria impilate, esponente del m²), con dati INVENTATI: codice fiscale sintetico
// di tests/telematico_casi.py, comuni e identificativi di fantasia. Nessun dato di una visura reale.
// Uso (dalla cartella del repository):  NODE_PATH=$(npm root -g) node tests/fixture_catasto/genera_risultanze.js
const { chromium } = require('playwright');
const path = require('path');

const CF = 'RSSMRA40A01H501K';
const testata = (catasto) => `
<p class="nav">Ti trovi in:</p><h3>Riepilogo</h3>
<p>Data: 10/11/2026 10:15:21</p><p>Provincia: ROMA</p><p>Tipo soggetto: Persona fisica</p>
<p>Ult.Aggiornamento: 09/11/2026</p><p>Codice fiscale: ${CF}</p><p>Catasto: ${catasto}</p>
<p class="avv">Avvertenza: eventuali incongruenze o incompletezze dei risultati della ricerca possono essere segnalati presentando
istanze di rettifica/correzione dei dati catastali tramite il servizio "Istanza rettifica dati catastali".</p>`;
const stile = `<style>body{font:11px Arial,sans-serif;margin:30px 36px}p{margin:4px 0}h3{font-size:12px}
table{border-collapse:collapse;width:100%;font-size:8px;margin-top:14px}th,td{text-align:center;padding:5px 3px;border-bottom:1px solid #ccc}
.avv{font-size:9px}.fine{margin-top:30px;text-align:center}</style>`;

const fabbricati = [
  ["Proprieta' per<br>35/1000", "ROMA Sez.", "17", "41", "", "ROMA(RM) VIA DELLE PROVE n. 1 Piano T-1", "Cat.A/4", "02", "2,5 vani", "Euro: 61,30"],
  ["Proprieta' per 1/1", "ROMA Sez.", "28", "777", "12", "ROMA(RM) VICOLO ESEMPIO Piano S2", "Zona 1<br>Cat.C/6", "04", "18 m<sup>2</sup>", "Euro:<br>143,10"],
  ["Nuda proprieta' per 1/2", "TIVOLI Sez. A", "5", "210", "33", "TIVOLI(RM) CORSO FITTIZIO n. 14 Piano S1-4", "Cat.A/2", "04", "5 vani", "Euro: 1.512,40"],
  ["Usufrutto per 1/2", "TIVOLI Sez.", "6", "318", "2", "TIVOLI(RM) VIA INVENTATA Piano T", "Cat.C/6", "04", "14 m<sup>2</sup>", "Euro: 77,15"],
];
const terreni = [
  ["Proprieta' per 1/36", "ROMA Sez.", "12", "301", "", "CAST FRUTTO", "04", "740", "Euro: 0,31", "Euro: 0,52", ""],
  ["Proprieta' per 1/36", "ROMA Sez.", "14", "55", "", "PRATO", "04", "5120", "Euro: 8,12 (*)", "Euro: 17,60", ""],
  ["Proprieta' per 1/1", "TIVOLI Sez.", "16", "9", "", "PASC CESPUG", "U", "7310", "Euro: 2,95", "Euro: 1,40", ""],
];
const tabella = (intest, righe) => `<table><tr>${intest.map(h => `<th>${h}</th>`).join('')}</tr>` +
  righe.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join('')}</tr>`).join('') + '</table>';

(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  const p = await b.newPage();
  const casi = {
    'risultanze_fabbricati_sintetico.pdf': testata('Fabbricati') + tabella(
      ['Titolarità', 'Comune', 'Foglio', 'Particella', 'Sub', 'Indirizzo', 'Zona e<br>Categoria', 'Classe', 'Consistenza', 'Rendita'], fabbricati),
    'risultanze_terreni_sintetico.pdf': testata('Terreni') + tabella(
      ['Titolarità', 'Comune', 'Foglio', 'Particella', 'Sub', 'Qualità', 'Classe', 'ha - are - ca', 'Reddito dominicale', 'Reddito agrario', 'Altri Dati'], terreni)
      + '<p>I redditi contraddistinti da (*) indicano che il reddito dominicale è stato calcolato tenendo conto delle deduzioni.</p>',
  };
  for (const [nome, corpo] of Object.entries(casi)) {
    await p.setContent(`<!doctype html><html><head><meta charset="utf-8">${stile}</head><body>${corpo}
      <p class="fine">Torna ai soggetti &nbsp; Torna alle provincie &nbsp; Nuova ricerca</p></body></html>`);
    await p.pdf({ path: path.join(__dirname, nome), format: 'A4' });
  }
  await b.close();
})();
