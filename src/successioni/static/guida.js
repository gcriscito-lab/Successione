"use strict";
/* Menu Operazioni (chiusura), Guida, Informazioni e calcolatrice rapida. */
/* il menu Operazioni si chiude cliccando fuori o con Esc */
document.addEventListener("click", ev => { for (const d of document.querySelectorAll("details.operazioni[open]")) if (!d.contains(ev.target)) d.open = false; });
document.addEventListener("keydown", ev => { if (ev.key === "Escape") for (const d of document.querySelectorAll("details.operazioni[open]")) { d.open = false; d.querySelector("summary").focus(); } });

/* ---------- Guida e Informazioni (come in ogni programma) ----------
   Istruzioni ufficiali dell'Agenzia (copie in fonti/, server: guida.py) aperte alla pagina dell'argomento; uso del programma;
   versione, componenti e novita'. Si apre con il pulsante «Guida» o con F1. */
const GUIDA = { dati: null, info: null };
async function datiGuida() { if (!GUIDA.dati) GUIDA.dati = await api("/api/guida"); return GUIDA.dati; }
function apriIstruzioni(doc, pagina) { anteprima("/api/guida/" + doc + ".pdf#page=" + pagina, "Istruzioni ufficiali — pagina " + pagina); }
/* Versione 0.4: anteprima interna dei documenti (modello, prospetti, brogliaccio, albero, istruzioni): si legge senza cambiare
   scheda del browser. «Apri in una nuova scheda» resta disponibile; «Stampa» per le pagine HTML (i PDF hanno i loro comandi). */
function anteprima(url, titolo) {
  const vecchio = document.getElementById("dAnteprima"); if (vecchio) vecchio.remove();
  const pdf = /\.pdf(\b|#|\?|$)/i.test(url);
  const fr = h("iframe", { src: url, title: titolo, class: "anteprima-doc" });
  const d = h("dialog", { id: "dAnteprima", class: "anteprima", "aria-label": "Anteprima: " + titolo },
    h("div", { class: "anteprima-barra" }, h("h2", {}, titolo), h("span", { class: "sp" }),
      h("a", { class: "gh", href: url, target: "_blank", rel: "noopener" }, "Apri in una nuova scheda"),
      pdf ? null : h("button", { type: "button", class: "gh", onclick: () => { try { fr.contentWindow.focus(); fr.contentWindow.print(); } catch (_) { window.open(url, "_blank", "noopener"); } } }, "Stampa"),
      h("button", { type: "button", class: "pil", onclick: () => d.close() }, "Chiudi")),
    fr);
  d.addEventListener("close", () => d.remove());
  document.body.append(d); d.showModal();
  return d;
}
function linkAnteprima(url, testo, titolo) {
  return h("a", { class: "gh", href: url, title: titolo || null, onclick: ev => { ev.preventDefault(); anteprima(url, testo); } }, testo);
}
/* Versione 0.4: strumenti di studio della pratica (fascicolo per il cliente, copia anonima, preventivo e parcella). */
function strumentiStudio(pid) {
  return h('section', { class: 'grp strumenti-studio', id: 'strumentiStudio' }, h('h2', {}, 'Strumenti di studio'),
    h('p', { class: 'mut' }, 'Documenti per il cliente e per lo studio: non cambiano la dichiarazione.'),
    h('div', { class: 'az' },
      linkAnteprima('/api/pratiche/' + pid + '/fascicolo.pdf', 'Fascicolo per il cliente',
        'Un solo PDF con indice: modello stampato, documenti del quadro EG e ricevute presenti nella pratica'),
      h('button', { type: 'button', class: 'gh', id: 'bPreventivo', onclick: () => apriPreventivo() }, 'Preventivo e parcella'),
      h('button', { type: 'button', class: 'gh', id: 'bCopiaAnonima', disabled: OCCUPATI.has('anonima'), onclick: occupato('anonima', () => copiaAnonima(pid)) }, 'Copia anonima')));
}
async function copiaAnonima(pid) {
  if (nMod()) return msg('Salva prima le modifiche: la copia parte dai dati salvati.', 'e');
  if (!confirm('Creare una NUOVA pratica con nomi, codici fiscali, indirizzi e riferimenti catastali di fantasia? Questa pratica non cambia; gli allegati non vengono copiati.')) return;
  try {
    const r = await post('/api/pratiche/' + pid + '/copia-anonima', { chiave: crypto.randomUUID() });
    await caricaPratiche();
    msg('Creata «' + r.titolo + '»: ' + r.modifiche.join('; ') + '. Date e importi restano: trattala comunque come dato riservato.', 'o');
  } catch (e) { msg(e.message, 'e'); }
}
function apriPreventivo() {
  if (!S.P) return;
  let d = $('#dPreventivo');
  if (!d) { d = h('dialog', { id: 'dPreventivo', class: 'preventivo', 'aria-labelledby': 'dPreventivoT' }); document.body.append(d); }
  const prev = structuredClone(noteP().preventivo || {});
  const voci = (prev.voci && prev.voci.length ? prev.voci : [{ descrizione: '', importo: '' }]).map(v => ({ ...v }));
  const corpoVoci = h('tbody');
  const campo = (id, et, val, attrs) => { const i = h('input', { id, ...(attrs || {}) }); i.value = val == null ? '' : String(val); return [h('label', { for: id }, et), i]; };
  const disegna = () => corpoVoci.replaceChildren(...voci.map((v, i) => {
    const de = h('input', { 'aria-label': 'Descrizione della voce ' + (i + 1), placeholder: 'es. Predisposizione e invio della dichiarazione' }); de.value = v.descrizione || '';
    const im = h('input', { 'aria-label': 'Importo della voce ' + (i + 1), inputmode: 'decimal', class: 'num', placeholder: '0,00' }); im.value = v.importo == null ? '' : String(v.importo).replace('.', ',');
    de.oninput = () => { v.descrizione = de.value; }; im.oninput = () => { v.importo = im.value; };
    return h('tr', { class: 'fisso' }, h('td', {}, de), h('td', {}, im),
      h('td', {}, h('button', { type: 'button', class: 'lk', 'aria-label': 'Togli la voce ' + (i + 1), onclick: () => { voci.splice(i, 1); if (!voci.length) voci.push({ descrizione: '', importo: '' }); disegna(); } }, 'Togli')));
  }));
  disegna();
  const [lNum, iNum] = campo('prevNumero', 'Numero', prev.numero);
  const [lData, iData] = campo('prevData', 'Data', prev.data || new Date().toISOString().slice(0, 10), { type: 'date' });
  const [lInt, iInt] = campo('prevIntestatario', 'Intestato a', prev.intestatario, { placeholder: 'nome e codice fiscale del cliente' });
  const pct = (id, et, k) => campo(id, et, prev[k] == null ? '' : String(prev[k]).replace('.', ','), { inputmode: 'decimal', class: 'num', placeholder: '0' });
  const [lCassa, iCassa] = pct('prevCassa', 'Contributo cassa %', 'cassa_pct');
  const [lIva, iIva] = pct('prevIva', 'IVA %', 'iva_pct');
  const [lRit, iRit] = pct('prevRit', "Ritenuta d'acconto %", 'ritenuta_pct');
  const imp = h('input', { type: 'checkbox', id: 'prevImposte' }); imp.checked = !!prev.includi_imposte;
  const nota = h('textarea', { id: 'prevNota', rows: 2 }); nota.value = prev.nota || '';
  // importi all'italiana: 1.234,50 -> 1234.50; un solo separatore «.» con 1-2 decimali resta decimale (12.5)
  const num = x => { const t = String(x || '').trim(); if (!t) return ''; return t.includes(',') ? t.replace(/\./g, '').replace(',', '.') : (/^\d+\.\d{1,2}$/.test(t) ? t : t.replace(/\./g, '')); };
  const raccogli = () => ({ voci: voci.filter(v => (v.descrizione || '').trim() || String(v.importo || '').trim()).map(v => ({ descrizione: (v.descrizione || '').trim(), importo: num(v.importo) })),
    numero: iNum.value.trim(), data: iData.value, intestatario: iInt.value.trim(), cassa_pct: num(iCassa.value), iva_pct: num(iIva.value),
    ritenuta_pct: num(iRit.value), includi_imposte: imp.checked, nota: nota.value.trim() });
  const salva = async () => {
    if (S.writeBusy) { msg('Salvataggio in corso: riprova tra un momento.', 'e'); return false; }
    return salvaOps([{ op: 'set', sezione: 'note', campi: { preventivo: raccogli() } }]);
  };
  let firma = null;
  const chiudi = () => { if (JSON.stringify(raccogli()) !== firma && !confirm("Ci sono modifiche non salvate nel preventivo. Chiudere senza salvarle?")) return; d.close(); };
  d.oncancel = ev => { ev.preventDefault(); chiudi(); };   // Esc: stessa conferma di «Chiudi»
  const vedi = tipo => async () => { if (await salva()) { d.close(); anteprima('/api/pratiche/' + S.P.pratica_id + '/preventivo?tipo=' + tipo, tipo === 'parcella' ? 'Parcella' : 'Preventivo'); } };
  d.replaceChildren(h('form', { method: 'dialog', onkeydown: invioNonChiude },
    h('h2', { id: 'dPreventivoT' }, 'Preventivo e parcella'),
    h('p', { class: 'mut' }, 'Voci e percentuali le decidi tu (vuote = 0): il programma fa solo le somme. Si salva nelle note interne della pratica, non nel file telematico. Non è una fattura.'),
    h('table', { class: 'prev-voci' }, h('thead', {}, h('tr', { class: 'fisso' }, h('th', {}, 'Voce'), h('th', {}, 'Importo (€)'), h('th', {}, h('span', { class: 'vh' }, 'Azioni')))), corpoVoci),
    h('div', { class: 'az' }, h('button', { type: 'button', class: 'gh', id: 'prevAggiungi', onclick: () => { voci.push({ descrizione: '', importo: '' }); disegna(); const x = corpoVoci.querySelectorAll('input'); if (x.length) x[x.length - 2].focus(); } }, 'Aggiungi voce')),
    h('div', { class: 'prev-campi' }, lCassa, iCassa, lIva, iIva, lRit, iRit, lNum, iNum, lData, iData, lInt, iInt),
    h('label', { class: 'chk', for: 'prevImposte' }, imp, h('span', {}, "Aggiungi le imposte della dichiarazione (dall'ultimo file generato), sommate a parte")),
    h('label', { for: 'prevNota' }, 'Nota in fondo al documento'), nota,
    h('div', { class: 'wiz-az' }, h('button', { type: 'button', class: 'gh', id: 'prevChiudi', onclick: chiudi }, 'Chiudi'),
      h('span', { class: 'sp' }),
      h('button', { type: 'button', class: 'gh', id: 'prevVediPreventivo', onclick: vedi('preventivo') }, 'Salva e vedi preventivo'),
      h('button', { type: 'button', class: 'gh', id: 'prevVediParcella', onclick: vedi('parcella') }, 'Salva e vedi parcella'),
      h('button', { type: 'button', class: 'pil', id: 'prevSalva', onclick: async () => { if (await salva()) d.close(); } }, 'Salva'))));
  firma = JSON.stringify(raccogli());
  if (!d.open) d.showModal();
  const primo = corpoVoci.querySelector('input'); if (primo) primo.focus();
}
function argomentoDelQuadro(id) { return GUIDA.dati && GUIDA.dati.argomenti.find(a => a.quadro === id); }
// Invio in un campo di Guida o Calcolatrice: il modulo lo tratterebbe come «Chiudi» e la finestra si chiuderebbe; qui non fa nulla
function invioNonChiude(ev) { if (ev.key === "Enter" && ev.target.tagName === "INPUT" && !ev.isComposing) ev.preventDefault(); }
async function apriGuida(scheda) {
  let d = $("#dGuida");
  if (!d) { d = h("dialog", { id: "dGuida", class: "guida", "aria-labelledby": "dGuidaT" }); document.body.append(d); }
  const schede = [["istruzioni", "Istruzioni ufficiali"], ["uso", "Uso del programma"], ["tabelle", "Tabelle e fonti"], ["info", "Informazioni"]];
  const att = scheda || "istruzioni";
  const corpo = h("div", { class: "guida-corpo", id: "guidaPannello", role: "tabpanel", "aria-labelledby": "guidaTab_" + att }, h("p", { class: "mut" }, "Caricamento…"));
  const seg = h("div", { class: "seg", role: "tablist", "aria-label": "Sezioni della guida" }, schede.map(([k, n]) => h("button", { type: "button", role: "tab", id: "guidaTab_" + k, "aria-selected": att === k ? "true" : "false", onclick: () => apriGuida(k) }, n)));
  schedeTastiera(seg, "guidaPannello", () => $("#dGuida .seg"));
  d.replaceChildren(h("form", { method: "dialog", onkeydown: invioNonChiude }, h("h2", { id: "dGuidaT" }, "Guida"), seg, corpo,
    h("div", { class: "wiz-az" }, h("span", { class: "sp" }), h("button", { class: "pil" }, "Chiudi"))));
  if (!d.open) d.showModal();
  try {
    if (att === "istruzioni") {
      const g = await datiGuida();
      const cerca = h("input", { type: "search", placeholder: "Cerca un argomento (es. prima casa, EF, rateale)", "aria-label": "Cerca nelle istruzioni" });
      const lista = h("ul", { class: "guida-lista" });
      const nomeDoc = id => (g.documenti.find(x => x.id === id) || {}).titolo || id;
      const disegna = () => {
        const q = cerca.value.trim().toLowerCase();
        lista.replaceChildren(...g.argomenti.filter(a => !q || a.titolo.toLowerCase().includes(q) || (a.quadro || "").toLowerCase() === q)
          .map(a => h("li", {}, h("button", { type: "button", class: "lk", onclick: () => apriIstruzioni(a.documento, a.pagina) }, a.titolo),
            h("span", { class: "mut" }, " — " + nomeDoc(a.documento) + ", pagina " + a.pagina))));
      };
      cerca.addEventListener("input", disegna); disegna();
      corpo.replaceChildren(cerca, lista, h("h3", {}, "Documenti completi"),
        h("ul", { class: "guida-lista" }, g.documenti.map(x => h("li", {}, x.disponibile
          ? h("button", { type: "button", class: "lk", onclick: () => apriIstruzioni(x.id, 1) }, x.titolo)
          : h("span", { class: "mut" }, x.titolo + " (non presente)"), h("span", { class: "mut" }, " — " + x.descrizione)))),
        h("p", { class: "mut piccolo" }, g.nota));
      cerca.focus();
    } else if (att === "uso") {
      corpo.replaceChildren(h("ol", { class: "guida-lista" },
        h("li", {}, h("b", {}, "Crea la pratica: "), "«Nuova dichiarazione» chiede defunto e quadri; «Importa XML» riprende un file .suc già inviato."),
        h("li", {}, h("b", {}, "Compila i quadri: "), "eredi in EA, terreni in EB, fabbricati in EC, passività in ED, gli altri beni negli altri quadri. «Controlla» dice cosa manca; il valore catastale è proposto nella scheda dell'immobile."),
        h("li", {}, h("b", {}, "Allegati: "), "nel quadro EG carichi i documenti (convertiti in PDF/A) e generi l'albero genealogico dai dati."),
        h("li", {}, h("b", {}, "File e invio: "), "genera il file, esegui il controllo ufficiale sul tuo computer, stampa e rileggi, prepara la copia da inviare con Desktop Telematico, poi registra protocollo e ricevute."),
        h("li", {}, h("b", {}, "Stima veloce: "), h("button", { type: "button", class: "lk", id: "guidaCalc", onclick: () => { $("#dGuida").close(); apriCalcolatrice(); } }, "Calcolatrice"), " stima le imposte da pochi dati (eredi, beni, passività) senza creare una pratica.")),
        h("h3", {}, "Scorciatoie da tastiera"),
        h("table", { class: "scorciatoie" }, h("tbody", {}, SCORCIATOIE.map(([k, t]) => h("tr", { class: "fisso" }, h("td", {}, h("kbd", {}, k)), h("td", {}, t))))),
        h("p", { class: "mut piccolo" }, "Dati non noti: scrivi «?» (da confermare), «assente», «zero» o «non applicabile». Importi all'italiana: 150.000 oppure 1.234,50."));
    } else if (att === "tabelle") {
      if (!GUIDA.tabelle) GUIDA.tabelle = await api("/api/tabelle");
      const T = GUIDA.tabelle;
      corpo.replaceChildren(h("p", { class: "mut" }, T.nota),
        h("nav", { class: "tab-indice", "aria-label": "Tabelle" }, T.tabelle.map(t => h("a", { href: "#tab_" + t.id, class: "lk",
          onclick: ev => { ev.preventDefault(); const x = document.getElementById("tab_" + t.id); if (x) x.scrollIntoView({ block: "start" }); } }, t.titolo))),
        ...T.tabelle.map(t => h("section", { class: "tab-fonte", id: "tab_" + t.id },
          h("h3", {}, t.titolo), h("p", { class: "mut piccolo" }, "Si applica a: " + t.decorrenza),
          h("table", { class: "tab-valori" }, h("thead", {}, h("tr", { class: "fisso" }, t.colonne.map(c => h("th", {}, c)))),
            h("tbody", {}, t.righe.map(r => h("tr", { class: "fisso" }, r.map(c => h("td", {}, c)))))),
          h("p", { class: "mut piccolo" }, h("b", {}, "Fonte: "), t.fonte), t.nota ? h("p", { class: "mut piccolo" }, t.nota) : null)));
    } else {
      if (!GUIDA.info) GUIDA.info = await api("/api/informazioni");
      const i = GUIDA.info, v = i.versioni || {};
      const riga = (k, x) => h("tr", { class: "fisso" }, h("td", {}, k), h("td", {}, x || "—"));
      corpo.replaceChildren(h("table", { class: "info-versione" }, h("tbody", {},
        riga("Programma", i.programma + " " + i.versione + (i.build ? " (build " + i.build.commit + " del " + dataIt(i.build.data) + ")" : "")),
        riga("Regole fiscali aggiornate al", v.regole ? dataIt(v.regole) : null), riga("Specifiche del file telematico", v.specifiche_suc),
        riga("Modulo di esportazione", v.modulo_esportazione), riga("Archivio in uso", i.archivio), riga("Sistema", i.sistema + " · Python " + i.python))),
        h("h3", {}, "Componenti"),
        h("ul", { class: "guida-lista" }, (i.componenti || []).map(c => h("li", {},
          h("span", { class: "pz " + (c.esito === "ok" ? "ok" : c.esito === "avviso" ? "am" : c.esito === "info" ? "" : "er") }, c.esito || "?"), " ", h("b", {}, c.nome),
          h("span", { class: "mut" }, " — " + (c.dettaglio || ""))))),
        h("h3", {}, "Novità"), h("pre", { class: "novita" }, i.novita || "—"),
        h("p", { class: "mut piccolo" }, i.avvertenza));
    }
  } catch (e) { corpo.replaceChildren(h("p", { class: "err" }, e.message)); }
}
$("#bGuida").onclick = () => apriGuida();
document.addEventListener("keydown", ev => { if (ev.key === "F1") { ev.preventDefault(); apriGuida(); } });
datiGuida().then(() => { if (S.P && S.sel !== "FILE") renderVista(); }).catch(() => { /* la guida resta raggiungibile dal pulsante */ });

/* ---------- Calcolatrice rapida ----------
   Stima delle imposte da pochi dati: il server (calcolatrice.py, POST /api/calcolatrice) costruisce una pratica sintetica IN
   MEMORIA e usa gli stessi motori della dichiarazione. Nulla viene salvato nell'archivio. Risultato aggiornato mentre si scrive. */
const CALC = { dati: null, seq: 0, timer: null, ultimo: null };
const CALC_ALTRI = [["CR", "Conti, depositi, crediti"], ["AB", "Titoli e altri beni"], ["DN", "Denaro, gioielli, mobilia"]];
function calcNuovi() {
  return { data_decesso: "", eredi: [{ grado: "02", quota: "", disabile: false, nome: "" }], immobili: [], altri_beni: [], passivita: [], circoscrizioni: 1 };
}
function calcOpzioni(chiave) { return ((S.schema && S.schema.strutturati[chiave]) || { opzioni: [] }).opzioni; }
function calcSelect(valore, opzioni, onchange, etichetta) {
  const s = h("select", { "aria-label": etichetta, onchange: ev => onchange(ev.target.value) }, opzioni.map(([v, t]) => h("option", { value: v }, t)));
  s.value = valore; return s;
}
function calcInput(o, k, attrs) { return h("input", { ...attrs, value: o[k] == null ? "" : String(o[k]), oninput: ev => { o[k] = ev.target.value; calcPianifica(); } }); }
function calcCheck(o, k, testo) {
  const cb = h("input", { type: "checkbox", onchange: ev => { o[k] = ev.target.checked; calcPianifica(); } }); cb.checked = !!o[k];
  return h("label", { class: "chk" }, cb, testo);
}
function calcTogli(lista, i) { return h("button", { type: "button", class: "gh x", "aria-label": "Togli la riga", title: "Togli", onclick: () => { lista.splice(i, 1); calcDisegnaDati(); calcPianifica(); } }, "×"); }
function calcDisegnaDati() {
  const d = CALC.dati, box = $("#calcDati"), sugg = (CALC.ultimo && CALC.ultimo.valori_catastali) || [];
  const gradi = calcOpzioni("persone.grado_parentela").map(o => [o.valore, o.valore + " — " + o.etichetta]);
  const tipiPass = calcOpzioni("passivita.tipo").map(o => [o.valore, o.valore + " — " + o.etichetta]);
  const legge = (CALC.ultimo && CALC.ultimo.quote_di_legge) || [];
  const dataD = h("input", { type: "date", id: "calcData", "aria-label": "Data del decesso", value: d.data_decesso, oninput: ev => { d.data_decesso = ev.target.value; calcPianifica(); } });
  const sez = (titolo, lista, nuovo, riga, testoAgg) => [h("h3", {}, titolo), ...lista.map((o, i) => riga(o, i)),
    h("button", { type: "button", class: "gh", onclick: () => { lista.push(nuovo()); calcDisegnaDati(); calcPianifica(); } }, testoAgg)];
  box.replaceChildren(...[
    h("div", { class: "campo" }, h("label", { for: "calcData" }, "Data del decesso"), dataD),
    ...sez("Eredi", d.eredi, () => ({ grado: "02", quota: "", disabile: false, nome: "" }), (o, i) => h("div", { class: "calc-riga calc-erede" },
      calcInput(o, "nome", { class: "nome", placeholder: "Erede " + (i + 1), "aria-label": "Nome (facoltativo)" }),
      calcSelect(o.grado, gradi, v => { o.grado = v; calcPianifica(); }, "Grado di parentela"),
      calcInput(o, "quota", { class: "q", placeholder: legge[i] || "di legge", "aria-label": "Quota (es. 1/2)", title: "Quota dell'eredità, es. 1/2. Vuota per tutti: quote di legge" }),
      calcCheck(o, "disabile", "disabilità grave"), d.eredi.length > 1 ? calcTogli(d.eredi, i) : null), "+ Aggiungi erede"),
    ...sez("Immobili", d.immobili, () => ({ tipo: "fabbricato", valore: "", rendita: "", categoria: "A/2", prima_casa: false }), (o, i) => {
      const s = sugg[i] || {};
      return h("div", { class: "calc-riga calc-immobile" },
        calcSelect(o.tipo, [["fabbricato", "Fabbricato"], ["terreno", "Terreno"]], v => { o.tipo = v; calcDisegnaDati(); calcPianifica(); }, "Tipo di immobile"),
        calcInput(o, "valore", { class: "n", placeholder: "valore €", "aria-label": "Valore", inputmode: "decimal" }),
        o.tipo === "terreno" ? calcInput(o, "reddito_dominicale", { class: "n", placeholder: "reddito dominicale", "aria-label": "Reddito dominicale", inputmode: "decimal" })
          : [calcInput(o, "rendita", { class: "n", placeholder: "rendita", "aria-label": "Rendita catastale", inputmode: "decimal" }),
             calcInput(o, "categoria", { class: "c", placeholder: "A/2", "aria-label": "Categoria catastale" }), calcCheck(o, "prima_casa", "prima casa")],
        calcTogli(d.immobili, i),
        s.valore_catastale ? h("span", { class: "calc-sugg" }, "Valore catastale proposto: " + Number(s.valore_catastale).toLocaleString("it-IT") + " € (" + s.formula + ")" + (o.valore ? "" : " — usato nella stima"))
          : s.motivo ? h("span", { class: "calc-sugg" }, "Valore catastale non calcolabile: " + s.motivo) : null);
    }, "+ Aggiungi immobile"),
    d.immobili.length ? h("div", { class: "calc-riga" }, h("label", { for: "calcCirc" }, "Circoscrizioni immobiliari (conservatorie) diverse"),
      calcInput(d, "circoscrizioni", { id: "calcCirc", class: "c", type: "number", min: "1", max: "50" })) : null,
    ...sez("Altri beni", d.altri_beni, () => ({ tipo: "CR", valore: "" }), (o, i) => h("div", { class: "calc-riga calc-altro" },
      calcSelect(o.tipo, CALC_ALTRI, v => { o.tipo = v; calcPianifica(); }, "Tipo di bene"),
      calcInput(o, "valore", { class: "n", placeholder: "valore €", "aria-label": "Valore", inputmode: "decimal" }), calcTogli(d.altri_beni, i)), "+ Aggiungi conto, titolo o altro bene"),
    // predefinita «12 — Altre passività», che non richiede il bene di riferimento; per i tipi 3, 4, 5, 7 si sceglie il bene
    // (annotazione XSD di ProgressivoCespite: per il mutuo, tipo 3, solo un immobile)
    ...sez("Passività", d.passivita, () => ({ tipo: "12", importo: "" }), (o, i) => h("div", { class: "calc-riga calc-passivita" },
      calcSelect(o.tipo, tipiPass, v => { o.tipo = v; calcDisegnaDati(); calcPianifica(); }, "Tipo di passività"),
      calcInput(o, "importo", { class: "n", placeholder: "importo €", "aria-label": "Importo", inputmode: "decimal" }),
      calcCespite(o, d), calcTogli(d.passivita, i)), "+ Aggiungi passività")].filter(Boolean));
}
const CALC_CON_CESPITE = ["3", "4", "5", "7"];
function calcCespite(o, d) {
  if (!CALC_CON_CESPITE.includes(String(o.tipo))) { delete o.immobile; delete o.altro_bene; return null; }
  const voci = [["", o.tipo === "3" ? "immobile del mutuo…" : "bene di riferimento…"],
    ...d.immobili.map((b, k) => ["i" + (k + 1), "Immobile " + (k + 1) + " (" + (b.tipo === "terreno" ? "terreno" : "fabbricato") + ")"]),
    ...(o.tipo === "3" ? [] : d.altri_beni.map((b, k) => ["a" + (k + 1), "Altro bene " + (k + 1)]))];
  const att = o.immobile ? "i" + o.immobile : (o.altro_bene && o.tipo !== "3") ? "a" + o.altro_bene : "";
  if (att && !voci.some(v => v[0] === att)) { delete o.immobile; delete o.altro_bene; }   // bene tolto nel frattempo
  const s = calcSelect(voci.some(v => v[0] === att) ? att : "", voci, v => {
    delete o.immobile; delete o.altro_bene;
    if (v[0] === "i") o.immobile = +v.slice(1); else if (v[0] === "a") o.altro_bene = +v.slice(1);
    calcPianifica();
  }, o.tipo === "3" ? "Immobile a cui si riferisce il mutuo" : "Bene a cui si riferisce la passività");
  s.classList.add("calc-cespite");
  return s;
}
function calcPianifica() { clearTimeout(CALC.timer); CALC.timer = setTimeout(calcEsegui, 450); }
async function calcEsegui() {
  const d = CALC.dati, ris = $("#calcRis"), mio = ++CALC.seq;
  if (!d.data_decesso) { ris.replaceChildren(h("p", { class: "calc-avv" }, "Stima: non sostituisce la dichiarazione né il controllo ufficiale."), h("p", { class: "mut" }, "Indica la data del decesso, gli eredi e almeno un bene: il risultato compare qui mentre scrivi.")); return; }
  ris.setAttribute("aria-busy", "true");
  let r;
  try { r = await post("/api/calcolatrice", d); }
  catch (e) {
    if (mio !== CALC.seq) return; ris.removeAttribute("aria-busy");
    // ancora nessun bene: non e' un errore, si sta compilando (revisione 14/11/2026, E12)
    if (/almeno un bene/.test(e.message)) { ris.replaceChildren(h("p", { class: "calc-avv" }, "Stima: non sostituisce la dichiarazione né il controllo ufficiale."), h("p", { class: "mut" }, "Aggiungi almeno un bene: il risultato compare qui mentre scrivi.")); return; }
    calcMostraErrore(e.message); return;
  }
  if (mio !== CALC.seq) return;            // risposta superata da una modifica successiva
  ris.removeAttribute("aria-busy");
  const primaSugg = JSON.stringify((CALC.ultimo || {}).valori_catastali || []) + JSON.stringify((CALC.ultimo || {}).quote_di_legge);
  CALC.ultimo = r;
  calcMostra(r);
  if (primaSugg !== JSON.stringify(r.valori_catastali || []) + JSON.stringify(r.quote_di_legge)) {
    const att = document.activeElement, idx = att && [...$("#calcDati").querySelectorAll("input,select")].indexOf(att), pos = att && att.selectionStart;
    calcDisegnaDati();
    if (idx >= 0) { const el = [...$("#calcDati").querySelectorAll("input,select")][idx]; if (el) { el.focus(); try { if (pos != null) el.setSelectionRange(pos, pos); } catch (_) { /* campi senza selezione */ } } }
  }
}
function calcAnnuncia(t) { const a = $("#calcAnnuncio"); if (a && a.textContent !== t) a.textContent = t; }
function calcMostraErrore(t) {
  CALC.ultimo = null; calcAnnuncia(t);
  $("#calcRis").replaceChildren(h("p", { class: "calc-avv" }, "Stima: non sostituisce la dichiarazione né il controllo ufficiale."), h("p", { class: "err", id: "calcErrore" }, t));
}
function calcMostra(r) {
  const lista = (cls, voci) => voci && voci.length ? h("ul", { class: cls }, voci.map(v => h("li", {}, v))) : null;
  const imp = r.imposte || [];
  // ridisegno a ogni tasto: i dettagli aperti (erede, ipotesi) restano aperti
  const aperti = new Set([...$("#calcRis").querySelectorAll("details[open]")].map(x => x.dataset.k));
  const det = (k, ...figli) => { const x = h("details", { "data-k": k, class: k.startsWith("erede") ? "calc-erede-ris" : null }, ...figli); if (aperti.has(k)) x.open = true; return x; };
  calcAnnuncia(imp.length ? "Totale stimato: " + (r.totale_testo || "") : (r.non_stimabile || []).length ? "Stima non disponibile per alcuni dati" : "");
  $("#calcRis").replaceChildren(...[
    h("p", { class: "calc-avv", id: "calcAvv" }, r.avvertenza),
    imp.length ? h("table", { class: "calc-imp", id: "calcImposte" }, h("tbody", {},
      imp.map(x => h("tr", { class: "fisso" }, h("td", {}, x.voce), h("td", { class: "n" }, x.testo))),
      h("tr", { class: "fisso tot" }, h("td", {}, "Totale stimato"), h("td", { class: "n", id: "calcTotale" }, r.totale_testo || "")))) : null,
    r.non_stimabile && r.non_stimabile.length ? [h("h3", {}, "Non stimabile"), lista("calc-ns", r.non_stimabile.map(m => "non stimabile: " + m))] : null,
    r.eredi && r.eredi.length ? [h("h3", {}, "Imposta di successione per erede"), ...r.eredi.map((e, i) => det("erede" + i,
      h("summary", {}, e.nome + " (" + (e.grado_testo || e.grado) + ", quota " + e.quota + "): " + e.imposta),
      h("p", { class: "mut" }, "Franchigia " + e.franchigia + (e.disabile ? " (disabilità grave)" : "") + ", aliquota " + e.aliquota + "."),
      h("ol", {}, e.passaggi.map(p => h("li", {}, p.voce + ": " + p.valore)))))] : null,
    r.passaggi && r.passaggi.length ? [h("h3", {}, "Come si arriva al risultato"), lista("", r.passaggi)] : null,
    r.note && r.note.length ? [h("h3", {}, "Note"), lista("", r.note)] : null,
    r.assunzioni ? det("ipotesi", h("summary", {}, "Ipotesi della stima"), lista("", r.assunzioni)) : null].flat().filter(Boolean));
}
async function calcCreaPratica() {
  if (!CALC.dati.data_decesso) return calcMostraErrore("Indica almeno la data del decesso e gli eredi.");
  let r;
  try { r = await post("/api/calcolatrice", { ...CALC.dati, azione: "pratica_iniziale" }); } catch (e) { return calcMostraErrore(e.message); }
  $("#dCalc").close();
  wizApri();
  if (!$("#wiz").open) return;
  W.dati.data_decesso = dataIt(r.data_decesso); W.extra = r.operazioni;
  wizRender();
  const nEredi = r.operazioni.filter(o => o.coll === "persone" && o.op === "upsert").length;
  msg("Procedura guidata compilata con la data del decesso e " + nEredi + (nEredi === 1 ? " erede" : " eredi") + ". Da completare: " + r.da_completare + ".", "o");
}
function apriCalcolatrice() {
  let d = $("#dCalc");
  if (!d) {
    d = h("dialog", { id: "dCalc", class: "calc", "aria-labelledby": "dCalcT" }, h("form", { method: "dialog", onkeydown: invioNonChiude },
      h("h2", { id: "dCalcT" }, "Calcolatrice rapida"),
      h("p", { class: "mut" }, "Stima delle imposte di successione con i motori di calcolo del programma. Non crea e non salva pratiche."),
      h("div", { class: "calc-corpo" }, h("div", { class: "calc-dati", id: "calcDati" }), h("div", { class: "calc-ris", id: "calcRis" })),
      h("p", { class: "vh", id: "calcAnnuncio", "aria-live": "polite" }),
      h("div", { class: "wiz-az" },
        h("button", { type: "button", class: "gh", id: "calcAzzera", onclick: () => {
          if (!uguale(CALC.dati, calcNuovi()) && !confirm("Azzerare la calcolatrice? I dati inseriti andranno persi.")) return;
          CALC.dati = calcNuovi(); CALC.ultimo = null; calcDisegnaDati(); calcEsegui(); } }, "Azzera"),
        h("span", { class: "sp" }),
        h("button", { class: "gh" }, "Chiudi"),
        h("button", { type: "button", class: "pil", id: "calcCrea", onclick: occupato("calcCrea", calcCreaPratica) }, "Crea una pratica da questi dati"))));
    document.body.append(d);
  }
  if (!CALC.dati) CALC.dati = calcNuovi();
  calcDisegnaDati(); calcEsegui();
  if (!d.open) d.showModal();
  $("#calcData").focus();
}
$("#bCalc").onclick = () => apriCalcolatrice();
$("#homeCalc").onclick = () => apriCalcolatrice();
