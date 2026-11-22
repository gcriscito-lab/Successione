"use strict";
const $ = (s, r = document) => r.querySelector(s);
function h(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === false || v === null || v === undefined) continue;
    if (k === "class") e.className = v; else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (k === "value") e.value = v; else e.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat()) if (c !== null && c !== undefined && c !== false) e.append(c.nodeType ? c : document.createTextNode(String(c)));
  return e;
}
/* ---------- accenti (report grafica DE.A.S. 09/11/2026, punto 4) ----------
   Molti testi (etichette, messaggi del servizio, voci degli elenchi) scrivono l'accento con l'apostrofo («proprieta'», «e'»).
   Si correggono SOLO nella visualizzazione: i dati, i valori dei campi e il file XML non cambiano.
   Restano com'erano: le elisioni («dell'immobile»), gli apici di citazione ('defunto'), «po'», i testi in <code>/<pre>. */
function accento(parola) {
  const low = parola.toLowerCase(); if (low === "po") return parola + "'";
  const base = parola.slice(0, -1), v = parola.slice(-1), maiu = v === v.toUpperCase();
  const nuova = v.toLowerCase() === "e" ? (/ch$/i.test(base) || ["n", "s"].includes(base.toLowerCase()) ? "é" : "è")
    : ({ a: "à", i: "ì", o: "ò", u: "ù" })[v.toLowerCase()];
  return nuova ? base + (maiu ? nuova.toUpperCase() : nuova) : parola + "'";
}
function accenta(s) {
  if (!s || s.indexOf("'") < 0) return s;
  let aperte = 0;
  return s.replace(/(^|[\s(«"\[\/])'(?=\p{L})|(\p{L}+)'(?=$|[\s.,;:!?)»\]"…\/–—-])/gu, (m, pre, parola, off, str) => {
    if (parola === undefined) { aperte++; return m; }          // apice che apre una citazione
    if (aperte > 0) { aperte--; return m; }                    // ...e quello che la chiude
    if (!/[aeiou]$/i.test(parola)) return m;
    const prima = str[off - 1]; if (prima && /[\p{N}_]/u.test(prima)) return m;   // identificativi (al_albero')
    return accento(parola);
  });
}
const SALTA_ACCENTI = "code, pre, textarea, script, style, [data-grezzo]";
function accentaNodo(n) {
  if (n.nodeType === 3) { const p = n.parentElement; if (p && !p.closest(SALTA_ACCENTI)) { const v = accenta(n.nodeValue); if (v !== n.nodeValue) n.nodeValue = v; } return; }
  if (n.nodeType !== 1 || n.closest(SALTA_ACCENTI)) return;
  for (const el of [n, ...n.querySelectorAll("[title], [aria-label], [placeholder]")])
    for (const a of ["title", "aria-label", "placeholder"]) { const x = el.getAttribute(a); if (x && x.indexOf("'") >= 0) { const v = accenta(x); if (v !== x) el.setAttribute(a, v); } }
  const tw = document.createTreeWalker(n, NodeFilter.SHOW_TEXT); let t;
  while ((t = tw.nextNode())) accentaNodo(t);
}
function avviaAccenti() {
  accentaNodo(document.body);
  new MutationObserver(lista => { for (const m of lista) {
    if (m.type === "childList") m.addedNodes.forEach(accentaNodo);
    else if (m.type === "characterData") accentaNodo(m.target);
    else if (m.type === "attributes") { const x = m.target.getAttribute(m.attributeName); if (x && x.indexOf("'") >= 0 && !m.target.closest(SALTA_ACCENTI)) { const v = accenta(x); if (v !== x) m.target.setAttribute(m.attributeName, v); } }
  } }).observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ["title", "aria-label", "placeholder"] });
}
if (document.body) avviaAccenti(); else document.addEventListener("DOMContentLoaded", avviaAccenti);
const S = { schema: null, pratiche: [], P: null, Q: null, sel: "AN", riga: null, tab: "dati", dirty: new Map(), nuove: new Map(), salvata: null, writeBusy: false, gen: 0 };
const STUDIO = { profilo: {}, archivio: '', ultimoBackup: null };   // profilo dello studio, archivio in uso, ultimo backup
const STATI = { vuoto: "da compilare", compilato: "compilato", rilievi: "rilievi", non_supportato: "non supportato", inattivo: "non selezionato",
  calcolato: "calcolato dal programma" };
/* Quadri che il programma calcola dagli altri (EE, EF, EH): non si selezionano, quindi per il server risultano «inattivi»;
   nell'elenco si mostrano come calcolati, non spenti in grigio (richiesta del 9/11/2026: «il quadro EF sia visibile»). */
const statoInElenco = q => q.generato && ["EE", "EF", "EH"].includes(q.id) && q.stato === "inattivo" ? "calcolato" : q.stato;
S.dichDirty = new Map();
try { S.vistaDV = localStorage.getItem("successioni.vistaDV") === "elenco" ? "elenco" : "griglia"; } catch (_) { S.vistaDV = "griglia"; }   // 22/11/2026: griglia predefinita
S.supDirty = new Map();
S.fornitoreDirty = {};
const nMod = () => S.dirty.size + S.nuove.size + S.dichDirty.size + S.supDirty.size + (Object.keys(S.fornitoreDirty).length ? 1 : 0) + (S.griglia && S.griglia.mod.size ? 1 : 0);
const nuovoId = coll => ({ persone: "p", beni: "b", devoluzioni: "d", passivita: "ps", documenti_ref: "dr" }[coll]) + "_" + crypto.randomUUID().replaceAll("-", "").slice(0, 12);
const uguale = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const ASPETTO_DEFAULT = { tema: 'sistema', stile: 'moderno', font: 'sistema', dimensione: 16, interlinea: 'normale', larghezza_pannello: 360, larghezza_nav: 240,
  accento: 'predefinito', densita: 'normale', contrasto: 'normale', movimento: 'normale', avvio: 'elenco', nome_studio: '', quadri_predefiniti: [],
  disposizione: 'destra', altezza_pannello: 380 };
// colori in app.css (:root[data-accento=...], con la variante per il tema scuro)
const ACCENTI = ['blu', 'verde', 'viola', 'arancio', 'rosso', 'grafite'];
// «sistema»: il carattere di sistema nello stile moderno (Segoe UI Variable su Windows, SF su Mac), Atkinson nel classico
const FONT_SISTEMA = '"Segoe UI Variable Text", "Segoe UI Variable", -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", system-ui, sans-serif';
const FONT_UI = { atkinson: '"Atkinson Hyperlegible Next", "Segoe UI", system-ui, sans-serif', sistema: '"Atkinson Hyperlegible Next", "Segoe UI", system-ui, sans-serif', segoe: '"Segoe UI", system-ui, sans-serif',
  arial: 'Arial, sans-serif', verdana: 'Verdana, sans-serif', georgia: 'Georgia, serif', consolas: 'Consolas, monospace' };
let preferenze = { ...ASPETTO_DEFAULT };
const sistemaScuro = window.matchMedia('(prefers-color-scheme: dark)');
function applicaAspetto(valori) {
  const p = { ...ASPETTO_DEFAULT, ...valori }, root = document.documentElement;
  root.dataset.tema = p.tema === 'sistema' ? (sistemaScuro.matches ? 'scuro' : 'chiaro') : p.tema;
  const moderno = p.stile !== 'classico';
  root.style.setProperty('--f-ui', p.font === 'sistema' || !FONT_UI[p.font] ? (moderno ? FONT_SISTEMA : FONT_UI.atkinson) : FONT_UI[p.font]);
  // personalizzazione: accento (con la variante adatta al tema scuro), densita', contrasto, movimento, nome dello studio
  root.dataset.accento = ACCENTI.includes(p.accento) ? p.accento : 'predefinito';
  root.dataset.densita = p.densita; root.dataset.contrasto = p.contrasto; root.dataset.movimento = p.movimento;
  root.dataset.stile = p.stile === 'classico' ? 'classico' : 'moderno';
  const sub = $('#bHome .marchio-sub'); if (sub) sub.textContent = p.nome_studio || 'Dichiarazioni telematiche';   // il nome dello studio sotto il marchio
  document.title = 'Successioni' + (p.nome_studio ? ' · ' + p.nome_studio : '');
  root.style.setProperty('--dimensione-base', Math.max(12, Math.min(22, Number(p.dimensione) || 16)) + 'px');
  root.style.setProperty('--interlinea', ({ compatta: 1.3, normale: 1.5, ampia: 1.8 })[p.interlinea] || 1.5);
  const nav = limiteNav() ? Math.min(limiteNav(), Math.max(180, Number(p.larghezza_nav) || 240)) : 240;
  root.style.setProperty('--larghezza-nav', nav + 'px');
  const limite = limitePannello(nav);
  root.style.setProperty('--larghezza-ins', Math.min(limite, Math.max(280, Number(p.larghezza_pannello) || (window.innerWidth >= 1680 ? 440 : 360))) + 'px');
  // versione 0.3: pannello della riga sotto l'elenco, a tutta larghezza (separatore orizzontale) oppure a destra
  const sotto = p.disposizione === 'sotto';
  root.dataset.disposizione = sotto ? 'sotto' : 'destra';
  const altezza = Math.min(limiteAltezza(), Math.max(200, Number(p.altezza_pannello) || 380));
  root.style.setProperty('--altezza-ins', altezza + 'px');
  const separatore = $('#ridimensiona');
  if (separatore) {
    separatore.setAttribute('aria-orientation', sotto ? 'horizontal' : 'vertical');
    separatore.setAttribute('aria-label', sotto ? 'Altezza pannello dati' : 'Larghezza pannello dati');
    separatore.setAttribute('aria-valuemin', sotto ? '200' : '280');
    separatore.setAttribute('aria-valuemax', String(sotto ? limiteAltezza() : 760));
    separatore.setAttribute('aria-valuenow', String(sotto ? altezza : Math.round(Math.min(limite, p.larghezza_pannello))));
  }
  const sepNav = $('#ridimensionaNav');
  if (sepNav) { sepNav.setAttribute('aria-valuenow', String(nav)); sepNav.setAttribute('aria-valuemax', String(limiteNav() || 480)); }
}
/* Limiti delle larghezze: la vista centrale deve restare di almeno 340 px; il menu dei quadri puo' crescere fino a 480 px. */
function limiteNav() { return window.innerWidth <= 960 ? 0 : Math.max(180, Math.min(480, window.innerWidth - 340 - 280)); }
function limitePannello(nav) { return Math.max(280, Math.min(760, window.innerWidth - (nav || preferenze.larghezza_nav || 240) - 340)); }
/* Pannello sotto: l'elenco sopra deve restare di almeno 200 px (titolo, linguette e qualche riga). */
function limiteAltezza() { return Math.max(200, Math.min(900, window.innerHeight - 140 - 200)); }
const quadriPredefiniti = () => (preferenze.quadri_predefiniti && preferenze.quadri_predefiniti.length ? ['AN', ...preferenze.quadri_predefiniti.filter(q => q !== 'AN')] : S.schema.predefiniti);
function memorizzaAspetto(p) {
  preferenze = { ...ASPETTO_DEFAULT, ...p }; applicaAspetto(preferenze);
  try { localStorage.setItem('successioni.aspetto', JSON.stringify(preferenze)); } catch (_) { /* il file sul PC resta la fonte */ }
}
try { applicaAspetto(JSON.parse(localStorage.getItem('successioni.aspetto') || '{}')); } catch (_) { applicaAspetto(preferenze); }
sistemaScuro.addEventListener('change', () => applicaAspetto($('#imp').open && IMP.aspetto ? IMP.aspetto : preferenze));
window.addEventListener('resize', () => applicaAspetto($('#imp').open && IMP.aspetto ? IMP.aspetto : preferenze));

/* Server spento o irraggiungibile: fetch rifiuta con un TypeError in inglese («Failed to fetch»). Si mostra un messaggio italiano
   che dice cosa fare (revisione 2, punto 5). */
const MSG_RETE = "Il programma non risponde: è stata chiusa la finestra del server? Riavvia con Avvia-pratica-reale.cmd";
async function rete(url, opt) {
  try { return await fetch(url, opt); }
  catch (e) { if (e && e.name === "AbortError") throw e; throw Object.assign(new Error(MSG_RETE), { rete: true, causa: e }); }
}
async function api(url, opt) {
  const r = await rete(url, opt);
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(j.messaggio || j.codice || (r.status === 401 ? "Sessione scaduta: riapri il programma con Avvia-pratica-reale.cmd" : r.statusText || ("errore " + r.status))), { dati: j, stato: r.status });
  return j;
}
/* Azioni che non mostrano da sole l'errore (apertura pratica, Controlla, allegati, cronologia...): un rifiuto non gestito
   diventa un messaggio leggibile invece di restare solo nella console. */
window.addEventListener("unhandledrejection", ev => {
  const e = ev.reason;
  ev.preventDefault();
  msg(e && e.message ? e.message : String(e || "Errore imprevisto"), "e");
});
/* Un'azione alla volta per pulsante (revisione 2, punto 2): finche' la richiesta non finisce il pulsante e' disabilitato
   e i clic successivi sono ignorati. Il nome identifica l'azione anche dopo un nuovo disegno della vista. */
const OCCUPATI = new Set();
function occupato(nome, fn) {
  return async ev => {
    if (OCCUPATI.has(nome)) return;
    OCCUPATI.add(nome);
    const b = ev && ev.currentTarget instanceof HTMLElement ? ev.currentTarget : null, prima = b ? b.disabled : false;
    if (b) { b.disabled = true; b.setAttribute("aria-busy", "true"); }
    try { return await fn(ev); }
    finally { OCCUPATI.delete(nome); if (b) { b.disabled = prima; b.removeAttribute("aria-busy"); } }
  };
}
const post = (u, b) => api(u, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b) });
/* Il messaggio e' un riquadro mobile in basso (non sposta il layout) con pulsante di chiusura: stile in app.css (#msg). */
/* Gli esiti positivi (classe "o") spariscono da soli dopo 8 secondi: a 375 px il riquadro copriva i campi. Gli errori restano
   finche' non si chiudono (revisione 2, punto 9). */
let msgTimer = null;
function msg(t, tipo) {
  const m = $("#msg"); m.className = tipo || ""; m.hidden = !t; m.replaceChildren();
  clearTimeout(msgTimer); msgTimer = null;
  if (t && tipo === "o") { const mio = m; msgTimer = setTimeout(() => { if (mio.className === "o") msg(""); }, 8000); }
  if (t) m.append(h("span", { class: "mt" }, t), h("button", { class: "x", "aria-label": "Chiudi il messaggio", title: "Chiudi", onclick: () => msg("") }));
}

/* ---------- valori ---------- */
/* Date: all'utente GG/MM/AAAA, nella pratica AAAA-MM-GG (convertite PRIMA dell'invio). Un testo non riconoscibile resta com'e'
   e il server risponde con il formato atteso. */
function dataIt(v) { const m = typeof v === "string" && v.match(/^(\d{4})-(\d{2})-(\d{2})$/); return m ? m[3] + "/" + m[2] + "/" + m[1] : v; }
function dataIso(t) {
  t = String(t).trim();
  let m = t.match(/^(\d{1,2})[\/.\-](\d{1,2})[\/.\-](\d{4})$/);
  if (m) return m[3] + "-" + m[2].padStart(2, "0") + "-" + m[1].padStart(2, "0");
  m = t.match(/^(\d{4})[\/.\-](\d{1,2})[\/.\-](\d{1,2})$/);
  return m ? m[1] + "-" + m[2].padStart(2, "0") + "-" + m[3].padStart(2, "0") : t;
}
/* Calendario accanto ai campi data (richiesta del 9/11/2026). Il campo resta di testo (GG/MM/AAAA, come prima); un pulsante
   apre il calendario del browser e la data scelta viene scritta nel campo come se fosse stata digitata (eventi input e change).
   Un solo aggancio per tutti i campi, anche quelli creati dopo (scheda della riga, finestre, passi della procedura guidata):
   si riconoscono dal segnaposto «GG/MM/AAAA». I campi data nativi (preventivo, calcolatrice) restano come sono. */
const SEL_CAMPO_DATA = 'input[placeholder="GG/MM/AAAA"]';
function dataEsiste(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso); if (!m) return false;
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  return d.getUTCFullYear() === +m[1] && d.getUTCMonth() === +m[2] - 1 && d.getUTCDate() === +m[3];
}
function agganciaCalendario(inp) {
  if (inp.closest(".con-calendario") || inp.classList.contains("cal-nativo")) return;
  const nativo = h("input", { type: "date", class: "cal-nativo", tabindex: "-1", "aria-hidden": "true" });
  const b = h("button", { type: "button", class: "cal-apri", "data-ic": "calendario", tabindex: "-1",
    "aria-label": "Scegli la data dal calendario", title: "Scegli la data dal calendario" });
  const fermo = () => inp.disabled || inp.readOnly;
  b.disabled = fermo();
  b.addEventListener("click", () => {
    if (fermo()) { b.disabled = true; return; }
    const iso = dataIso(inp.value);
    nativo.value = dataEsiste(iso) ? iso : "";       // con una data valida il calendario si apre su quella
    try { nativo.showPicker(); } catch (_) { nativo.focus(); nativo.click(); }
  });
  // gli eventi del campo nascosto non devono arrivare ai moduli: conta solo il campo di testo
  nativo.addEventListener("input", ev => ev.stopPropagation());
  nativo.addEventListener("change", ev => {
    ev.stopPropagation();
    if (!nativo.value || fermo()) return;
    inp.value = dataIt(nativo.value);
    inp.dispatchEvent(new Event("input", { bubbles: true })); inp.dispatchEvent(new Event("change", { bubbles: true }));
    inp.focus();
  });
  const attivo = document.activeElement === inp;
  const involucro = h("span", { class: "con-calendario" });
  inp.replaceWith(involucro); involucro.append(inp, b, nativo);
  if (attivo) inp.focus();                            // spostare il campo nel DOM gli toglie il fuoco
}
function agganciaCalendari(nodo) {
  if (!nodo || nodo.nodeType !== 1) return;
  if (nodo.matches(SEL_CAMPO_DATA)) agganciaCalendario(nodo);
  else for (const x of nodo.querySelectorAll(SEL_CAMPO_DATA)) agganciaCalendario(x);
}
function avviaCalendari() {
  agganciaCalendari(document.body);
  new MutationObserver(lista => { for (const m of lista) m.addedNodes.forEach(agganciaCalendari); })
    .observe(document.body, { childList: true, subtree: true });
}
if (document.body) avviaCalendari(); else document.addEventListener("DOMContentLoaded", avviaCalendari);
/* Dato non noto: nella pratica {stato: ...}, all'utente in parole. Si possono scrivere le parole, «?» o la forma [stato]. */
const STATI_DATO = { da_confermare: "da confermare", assente: "assente", zero: "zero", non_applicabile: "non applicabile" };
/* Importi: nella pratica col punto decimale (1234.50), all'utente con la virgola; in tabella anche col punto delle migliaia. */
function importoIt(v, migliaia) {
  const m = String(v).match(/^(-?)(\d+)(?:\.(\d+))?$/);
  if (!m) return String(v);
  return m[1] + (migliaia ? m[2].replace(/\B(?=(\d{3})+(?!\d))/g, ".") : m[2]) + (m[3] !== undefined ? "," + m[3] : "");
}
function mostra(kind, v, inTabella) {
  if (v === undefined || v === null) return "";
  if (typeof v === "object" && v.stato) return STATI_DATO[v.stato] || String(v.stato).replaceAll("_", " ");
  if (kind === "quota" && typeof v === "object") return v.num + "/" + v.den;
  if (kind === "data") return dataIt(String(v));
  if (kind === "importo") return importoIt(v, inTabella);
  return String(v);
}
function leggi(kind, t) {
  t = t.trim();
  if (t === "") return null;
  if (t === "?") return { stato: "da_confermare" };
  if (/^\[[a-z_]+\]$/.test(t)) return { stato: t.slice(1, -1) };
  const st = Object.keys(STATI_DATO).find(k => STATI_DATO[k] === t.toLowerCase());
  if (st) return { stato: st };
  if (kind === "quota") { const m = t.match(/^(\d+)\s*\/\s*(\d+)$/); return m ? { num: +m[1], den: +m[2] } : t; }
  if (kind === "data") return dataIso(t);
  if (kind === "importo") {
    if (/^-?\d{1,3}(\.\d{3})+,\d+$/.test(t)) return t.replaceAll(".", "").replace(",", ".");   // 1.234,50 -> 1234.50
    // 150.000 / 1.234.567 -> 150000 / 1234567: nella maschera il punto seguito da gruppi di tre cifre e' il separatore
    // delle migliaia (come suggerisce «1.234,50»); prima un solo gruppo restava "150.000" = 150 euro
    if (/^-?\d{1,3}(\.\d{3})+$/.test(t)) return t.replaceAll(".", "");
    if (/^-?\d+,\d+$/.test(t)) return t.replace(",", ".");                                    // 12,5 -> 12.5
  }
  return t;
}
/* Etichette e ordine dei campi: arrivano da /api/schema (server: etichette.py). Mai il nome interno con i trattini bassi. */
function lbl(coll, campo, quadro) {
  const E = (S.schema && S.schema.etichette) || {};
  return (quadro && (E.quadro || {})[quadro + "." + campo]) || ((E.campi || {})[coll] || {})[campo] || String(campo).replaceAll("_", " ");
}
function nomeVal(coll, campo, v) { return ((((S.schema || {}).etichette || {}).valori || {})[coll + "." + campo] || {})[v] || v; }
function lblDich(chiave, fallback) { return ((((S.schema || {}).etichette || {}).dichiarazione || {})[chiave]) || fallback || chiave.replaceAll("_", " ").replaceAll(".", ": "); }
/* campi nell'ordine del quadro; quelli non previsti vanno in coda */
function ordinati(chiaveOrdine, campi) {
  const o = ((S.schema || {}).ordine || {})[chiaveOrdine] || [];
  const pos = c => { const i = o.indexOf(c); return i < 0 ? o.length : i; };
  return [...campi].sort((a, b) => pos(a) - pos(b));
}
function etichetta(coll, e) {
  if (coll === "persone") return [e.cognome, e.nome].filter(Boolean).join(" ") || e.id;
  if (coll === "beni") return [nomeVal("beni", "tipo", e.tipo), e.comune, e.foglio && "fg." + e.foglio, e.particella && "p." + e.particella, e.subalterno && "sub." + e.subalterno, e.descrizione].filter(Boolean).join(" ") || e.id;
  if (coll === "devoluzioni") {   // 22/11/2026: «Rossi Anna – Fabbricato Roma fg.100…» invece di «d_casaanna»
    const p = (S.P && S.P.dati.persone || []).find(x => x.id === e.persona_id), b = (S.P && S.P.dati.beni || []).find(x => x.id === e.bene_id);
    const t = [p && etichetta("persone", p), b && etichetta("beni", b)].filter(Boolean).join(" – ");
    return t || "Nuova riga di devoluzione";
  }
  if (coll === "passivita" && e.descrizione) return e.descrizione;
  return e.id;
}
const rilievi = () => (S.Q ? S.Q.rilievi : []);
const quadro = () => S.Q && S.Q.quadri.find(x => x.id === S.sel);

/* ---------- caricamento ---------- */
// solo la versione (richiesta del 14/11/2026); gli strumenti PDF/A restano nella Diagnosi e nel suggerimento
const mostraInfo = i => { const el = $("#info"); el.textContent = "Versione " + i.versione;
  el.title = "Accesso solo da questo computer. PDF/A: Ghostscript " + (i.pdfa.ghostscript ? "presente" : "assente") + ", veraPDF " + (i.pdfa.veraPDF ? "presente" : "non configurato"); };
async function init() {
  try {
    const i = await api("/api/info");
    mostraInfo(i);
    S.schema = await api("/api/schema");
    try { const imp = await api('/api/impostazioni'); memorizzaAspetto(imp.interfaccia); STUDIO.profilo = imp.profilo || {};
      if (imp.problema_configurazione) msg("Il file delle impostazioni non è valido: Claude resta in sola lettura finché non lo correggi o lo salvi di nuovo dalle Impostazioni. Motivo: " + imp.problema_configurazione, "e"); } catch (_) { /* l'app resta utilizzabile */ }
    STUDIO.archivio = i.archivio || '';
    if (i.archivio) { const a = $("#homeArchivio"); a.replaceChildren("Archivio aperto: ", h("code", {}, i.archivio)); a.hidden = false; }
    await caricaPratiche(); renderSb(); aggiornaBottoni();
    try { const ultima = localStorage.getItem('successioni.ultima'); if (preferenze.avvio === 'ultima' && ultima && S.pratiche.some(p => p.id === ultima)) await apri(ultima); } catch (_) { /* resta l'elenco */ }
  } catch (e) { msg("Avvio non riuscito: " + e.message, "e"); }
}
/* Pagina iniziale: le pratiche piu' recenti con il termine ordinario di presentazione (dodici mesi dal decesso:
   docs/regole/pagamenti_crediti.md e istruzioni del modello, che prevedono anche decorrenze diverse). */
function terminePresentazione(decesso) {
  const m = typeof decesso === "string" && decesso.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return null;
  // stessa regola di cruscotto._termine e della calcolatrice: stesso giorno dell'anno dopo, 28 febbraio per un decesso il 29
  const t = new Date(+m[1] + 1, +m[2] - 1, +m[2] === 2 && +m[3] === 29 ? 28 : +m[3]);
  const oggi = new Date(); oggi.setHours(0, 0, 0, 0);
  return { data: t, giorni: Math.round((t - oggi) / 86400000) };
}
const dataBreve = d => String(d.getDate()).padStart(2, "0") + "/" + String(d.getMonth() + 1).padStart(2, "0") + "/" + d.getFullYear();
const isoData = d => d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
