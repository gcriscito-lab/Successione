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
const S = { schema: null, pratiche: [], P: null, Q: null, sel: "AN", riga: null, tab: "dati", dirty: new Map(), nuove: new Map(), salvata: null, writeBusy: false, gen: 0 };
const STUDIO = { profilo: {}, archivio: '', ultimoBackup: null };   // profilo dello studio, archivio in uso, ultimo backup
const STATI = { vuoto: "da compilare", compilato: "compilato", rilievi: "rilievi", non_supportato: "non supportato", inattivo: "non selezionato" };
S.dichDirty = new Map();
S.supDirty = new Map();
S.fornitoreDirty = {};
const nMod = () => S.dirty.size + S.nuove.size + S.dichDirty.size + S.supDirty.size + (Object.keys(S.fornitoreDirty).length ? 1 : 0);
const nuovoId = coll => ({ persone: "p", beni: "b", devoluzioni: "d", passivita: "ps", documenti_ref: "dr" }[coll]) + "_" + crypto.randomUUID().replaceAll("-", "").slice(0, 12);
const uguale = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const ASPETTO_DEFAULT = { tema: 'sistema', font: 'sistema', dimensione: 14, interlinea: 'normale', larghezza_pannello: 360, larghezza_nav: 240,
  accento: 'predefinito', densita: 'normale', contrasto: 'normale', movimento: 'normale', avvio: 'elenco', nome_studio: '', quadri_predefiniti: [] };
const ACCENTI = { blu: ['#0a74ff', '#6cb0ff'], verde: ['#1e7a37', '#6fd18a'], viola: ['#6e3fd1', '#b79cff'], arancio: ['#b25e00', '#ffb454'], rosso: ['#c4001a', '#ff8a92'], grafite: ['#3a3f4a', '#c4c9d4'] };
const hexRgba = (hex, a) => { const n = parseInt(hex.slice(1), 16); return 'rgba(' + (n >> 16) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a + ')'; };
const FONT_UI = { sistema: '"Atkinson Hyperlegible Next", "Segoe UI", system-ui, sans-serif', segoe: '"Segoe UI", system-ui, sans-serif',
  arial: 'Arial, sans-serif', verdana: 'Verdana, sans-serif', georgia: 'Georgia, serif', consolas: 'Consolas, monospace' };
let preferenze = { ...ASPETTO_DEFAULT };
const sistemaScuro = window.matchMedia('(prefers-color-scheme: dark)');
function applicaAspetto(valori) {
  const p = { ...ASPETTO_DEFAULT, ...valori }, root = document.documentElement;
  root.dataset.tema = p.tema === 'sistema' ? (sistemaScuro.matches ? 'scuro' : 'chiaro') : p.tema;
  root.style.setProperty('--f-ui', FONT_UI[p.font] || FONT_UI.sistema);
  // personalizzazione: accento (con la variante adatta al tema scuro), densita', contrasto, movimento, nome dello studio
  const acc = ACCENTI[p.accento];
  if (acc) { const col = acc[root.dataset.tema === 'scuro' ? 1 : 0]; root.style.setProperty('--blu', col); root.style.setProperty('--blu-t', hexRgba(col, 0.14)); }
  else { root.style.removeProperty('--blu'); root.style.removeProperty('--blu-t'); }
  root.dataset.densita = p.densita; root.dataset.contrasto = p.contrasto; root.dataset.movimento = p.movimento;
  const sub = $('#bHome .marchio-sub'); if (sub) sub.textContent = p.nome_studio || 'Dichiarazioni telematiche';   // il nome dello studio sotto il marchio
  document.title = 'Successioni' + (p.nome_studio ? ' · ' + p.nome_studio : '');
  root.style.setProperty('--dimensione-base', Math.max(12, Math.min(22, Number(p.dimensione) || 14)) + 'px');
  root.style.setProperty('--interlinea', ({ compatta: 1.3, normale: 1.5, ampia: 1.8 })[p.interlinea] || 1.5);
  const nav = limiteNav() ? Math.min(limiteNav(), Math.max(180, Number(p.larghezza_nav) || 240)) : 240;
  root.style.setProperty('--larghezza-nav', nav + 'px');
  const limite = limitePannello(nav);
  root.style.setProperty('--larghezza-ins', Math.min(limite, Math.max(280, Number(p.larghezza_pannello) || 360)) + 'px');
  const separatore = $('#ridimensiona');
  if (separatore) separatore.setAttribute('aria-valuenow', String(Math.round(Math.min(limite, p.larghezza_pannello))));
  const sepNav = $('#ridimensionaNav');
  if (sepNav) { sepNav.setAttribute('aria-valuenow', String(nav)); sepNav.setAttribute('aria-valuemax', String(limiteNav() || 480)); }
}
/* Limiti delle larghezze: la vista centrale deve restare di almeno 340 px; il menu dei quadri puo' crescere fino a 480 px. */
function limiteNav() { return window.innerWidth <= 960 ? 0 : Math.max(180, Math.min(480, window.innerWidth - 340 - 280)); }
function limitePannello(nav) { return Math.max(280, Math.min(760, window.innerWidth - (nav || preferenze.larghezza_nav || 240) - 340)); }
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
/* Il messaggio e' un riquadro mobile in basso (non sposta il layout) con pulsante di chiusura. Stile aggiunto da qui. */
document.head.append(h("style", {}, `#msg{position:fixed;left:50%;bottom:44px;transform:translateX(-50%);z-index:60;margin:0;max-width:min(760px,calc(100vw - 24px));
  display:flex;gap:12px;align-items:flex-start;white-space:pre-line;overflow-wrap:anywhere;max-height:40vh;overflow:auto}
  #msg[hidden]{display:none} #msg .mt{flex:1} #msg .x{flex:none;border:0;background:transparent;color:inherit;cursor:pointer;font:inherit;line-height:1;padding:2px 6px}
  #msg .x::before{content:"\\00d7";font-size:1.3em}`));
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
  return e.id;
}
const rilievi = () => (S.Q ? S.Q.rilievi : []);
const quadro = () => S.Q && S.Q.quadri.find(x => x.id === S.sel);

/* ---------- caricamento ---------- */
const mostraInfo = i => { $("#info").textContent = "Versione " + i.versione + ". Accesso solo da questo computer. PDF/A: Ghostscript " + (i.pdfa.ghostscript ? "presente" : "assente") + ", veraPDF " + (i.pdfa.veraPDF ? "presente" : "non configurato"); };
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
  const t = new Date(+m[1] + 1, +m[2] - 1, +m[3]);
  const oggi = new Date(); oggi.setHours(0, 0, 0, 0);
  return { data: t, giorni: Math.round((t - oggi) / 86400000) };
}
const dataBreve = d => String(d.getDate()).padStart(2, "0") + "/" + String(d.getMonth() + 1).padStart(2, "0") + "/" + d.getFullYear();
function renderHome() {
  const ul = $("#recenti"); if (!ul) return;
  ul.replaceChildren();
  const vuoto = !S.pratiche.length;
  $("#homeTitolo").textContent = vuoto ? "Prima dichiarazione" : "Riprendi il lavoro";
  $("#homeIntro").textContent = vuoto ? "L’archivio non contiene ancora pratiche. Crea la prima oppure importa un file telematico già preparato."
    : "Apri una pratica recente oppure inizia una nuova dichiarazione di successione.";
  ul.hidden = vuoto; $("#homeElencoT").textContent = vuoto ? "Come si arriva all’invio" : "Pratiche recenti"; $("#percorso").hidden = !vuoto;
  if (vuoto) { $("#homeNota").hidden = true; const f = $("#homeFiltri"); if (f) f.remove(); return; }
  // voce 8 dell'analisi del 07/11/2026: tutte le pratiche, filtrabili per termine ordinario e ordinabili per scadenza
  const pratiche = praticheFiltrate(S.pratiche, HOME.filtro, HOME.ordine, HOME.cerca);
  $("#homeElencoT").textContent = S.pratiche.length > 8 || HOME.filtro !== "tutte" || HOME.cerca ? "Pratiche (" + pratiche.length + " di " + S.pratiche.length + ")" : "Pratiche recenti";
  filtriHome(ul);
  if (!pratiche.length) ul.append(h("li", { class: "mut" }, "Nessuna pratica corrisponde al filtro."));
  let conTermine = false;
  for (const p of pratiche.slice(0, HOME.tutte ? pratiche.length : 8)) {
    const t = terminePresentazione(p.data_decesso); conTermine = conTermine || !!t;
    const term = !t ? h("span", { class: "term mut" }, "Data del decesso da indicare")
      : t.giorni < 0 ? h("span", { class: "term scaduto" }, "Termine ordinario superato il " + dataBreve(t.data))
      : h("span", { class: "term" + (t.giorni <= 60 ? " vicino" : "") }, "Termine ordinario " + dataBreve(t.data) + (t.giorni <= 60 ? ", tra " + t.giorni + (t.giorni === 1 ? " giorno" : " giorni") : ""));
    // pagina iniziale «premium» (proposta Canva del 07/11/2026): iniziali della pratica in casella, stato del termine in chiaro, «Riprendi»
    const iniz = String(p.titolo || "?").replace(/^(successione|eredit[aà]|dichiarazione)\s+/i, "").split(/\s+/).filter(Boolean).slice(0, 2).map(x => x[0]).join("").toUpperCase() || "?";
    const badge = t && t.giorni < 0 ? h("span", { class: "badge er" }, "Termine superato") : t && t.giorni <= 60 ? h("span", { class: "badge am" }, "In scadenza") : null;
    ul.append(h("li", {}, h("button", { type: "button", onclick: () => apri(p.id), "aria-label": "Riprendi " + p.titolo },
      h("span", { class: "iniz", "aria-hidden": "true" }, iniz),
      h("span", { class: "tit" }, p.titolo, badge ? " " : null, badge),
      h("span", { class: "dett" }, "Aggiornata il " + dataIt(String(p.aggiornata || "").slice(0, 10)) + " · revisione " + p.revisione), term,
      h("span", { class: "riprendi", "aria-hidden": "true" }, "Riprendi"))));
  }
  if (pratiche.length > 8) ul.append(h("li", { class: "altre" }, h("button", { type: "button", class: "lk", onclick: () => { HOME.tutte = !HOME.tutte; renderHome(); } },
    HOME.tutte ? "Mostra solo le prime 8" : "Mostra tutte (" + pratiche.length + ")")));
  $("#homeNota").hidden = !conTermine;
  statoHome();
  renderProssime();
}
/* «Prossime azioni» (proposta Canva 07/11/2026; server: cruscotto.py): per ogni pratica le cinque tappe e la cosa da fare,
   che porta dritto al punto dell'interfaccia in cui farla. */
let prossimeGen = 0;
async function renderProssime() {
  const box = $("#prossime"); if (!box || S.P) return;   // si calcola solo sulla pagina iniziale, non durante il lavoro
  // i filtri dell'elenco ridisegnano la pagina a ogni tasto: lo stato delle pratiche si ricalcola al massimo ogni 5 secondi
  const firma = S.pratiche.map(p => p.id + ":" + p.revisione).join(",");
  if (firma === renderProssime.firma && Date.now() - (renderProssime.quando || 0) < 5000) return;
  renderProssime.firma = firma; renderProssime.quando = Date.now();
  const gen = ++prossimeGen;
  if (!S.pratiche.length) { box.replaceChildren(h("p", { class: "mut" }, "Qui compariranno, pratica per pratica, i passi che restano fino alle ricevute.")); return; }
  let c;
  try { c = await api("/api/cruscotto"); } catch (e) { if (gen === prossimeGen) box.replaceChildren(h("p", { class: "err" }, e.message)); return; }
  if (gen !== prossimeGen || S.P) return;
  // il termine conta dalla decorrenza indicata nel frontespizio, se c'e' (cruscotto.py): lo si dice nel testo
  const daDec = t => t.base === "decorrenza" ? " dalla decorrenza" : "";
  const titTermine = t => "Termine del " + dataIt(t.data) + (t.base === "decorrenza" ? ", dalla decorrenza del " + dataIt(t.dal) : ", dalla data del decesso");
  const termine = t => !t ? null : t.giorni < 0 ? h("span", { class: "scad er", title: titTermine(t) }, "superato" + daDec(t))
    : h("span", { class: "scad" + (t.giorni <= 60 ? " am" : ""), title: titTermine(t) },
      (t.giorni === 0 ? "oggi" : "tra " + t.giorni + (t.giorni === 1 ? " giorno" : " giorni")) + daDec(t));
  const testoAzione = a => {
    if (!a) return "";
    const m = String((a.dove || {}).percorso || "").match(/^([a-z_]+)\[[^\]]+\]\.([a-z_]+)$/);
    const campo = m && S.schema.collezioni[m[1]] ? lbl(m[1], m[2], a.dove.sel) : null;
    return (campo ? campo.charAt(0).toUpperCase() + campo.slice(1) + ": " : "") + a.testo + (a.altri ? " (e altri " + a.altri + ")" : "");
  };
  box.replaceChildren(...c.pratiche.map(v => {
    const tappe = h("ol", { class: "tappe", "aria-label": "Avanzamento della pratica" }, c.tappe.map(t => {
      const st = (v.tappe || {})[t.id] || "da_fare";
      return h("li", { class: "tappa " + st, "aria-current": st === "corrente" ? "step" : null },
        h("span", { class: "nodo", "aria-hidden": "true" }), h("span", { class: "nome-tappa" }, t.nome),
        h("span", { class: "vh" }, st === "fatto" ? " (fatto)" : st === "corrente" ? " (in corso)" : st === "problema" ? " (da correggere)" : " (da fare)"));
    }));
    return h("article", { class: "card-azione" + (v.completata ? " completata" : "") },
      h("button", { type: "button", class: "card-tit", onclick: () => apri(v.pratica_id) }, v.titolo),
      tappe,
      h("button", { type: "button", class: "azione" + ((v.azione || {}).livello === "problema" ? " problema" : ""), onclick: () => vaiAllAzione(v) },
        h("span", { class: "freccia", "aria-hidden": "true" }), h("span", { class: "testo-az" }, testoAzione(v.azione)), termine(v.termine)));
  }), ...(c.altre ? [h("p", { class: "mut prossime-altre" }, "Altre " + c.altre + (c.altre === 1 ? " pratica" : " pratiche") + " con termine più lontano"
    + (c.altre_da_lavorare ? " (" + c.altre_da_lavorare + " da lavorare)" : "") + ": sono nell'elenco delle pratiche.")] : []));
}
async function vaiAllAzione(v) {
  const dove = (v.azione || {}).dove || {};
  await apri(v.pratica_id, dove.sel === "FILE" ? "AN" : dove.sel || "AN");
  if (!S.P || S.P.pratica_id !== v.pratica_id) return;
  if (dove.sel === "FILE") return vaiFile();
  const m = String(dove.percorso || "").match(/^([a-z_]+)\[([^\]]+)\]/);
  if (m && S.schema.collezioni[m[1]]) { S.riga = "e:" + m[1] + ":" + m[2]; S.tab = "dati"; render(); }
  setTimeout(() => { const el = dove.percorso && document.querySelector('[data-path="' + CSS.escape(dove.percorso) + '"]');
    if (el) { el.scrollIntoView({ block: "center" }); el.focus(); } }, 50);
}
/* Striscia di stato della pagina iniziale: archivio, versione e componenti (una richiesta, solo quando serve). */
let statoHomeCaricato = false;
async function statoHome() {
  const el = $("#homeStato"); if (!el) return;
  const n = S.pratiche.length;
  const voce = (tit, val, cls) => h("div", { class: "stato-voce" }, h("span", { class: "stato-tit" }, tit), h("span", { class: "stato-val " + (cls || "") }, val));
  el.replaceChildren(voce("Archivio", n + (n === 1 ? " pratica" : " pratiche")), voce("Versione", "…"), voce("Controllo ufficiale", "…"));
  el.hidden = false;
  if (statoHomeCaricato && GUIDA.info) return disegnaStato();
  try { GUIDA.info = GUIDA.info || await api("/api/informazioni"); statoHomeCaricato = true; disegnaStato(); } catch (_) { /* resta il conteggio */ }
  function disegnaStato() {
    const i = GUIDA.info, ctl = (i.componenti || []).find(c => /controllo/i.test(c.nome || ""));
    const ok = ctl && ctl.esito === "ok";
    el.replaceChildren(voce("Archivio", n + (n === 1 ? " pratica" : " pratiche")),
      voce("Versione", i.versione + " · regole " + dataIt(i.versioni.regole)),
      voce("Controllo ufficiale", ctl ? (ok ? "Disponibile su questo computer" : "Da configurare (vedi Impostazioni)") : "Non verificato", ok ? "ok" : "am"));
  }
}
const HOME = { filtro: "tutte", ordine: "recenti", cerca: "", tutte: false };
const FILTRI_HOME = { tutte: "Tutte", vicine: "In scadenza (60 giorni)", superate: "Termine superato", senza_data: "Senza data del decesso" };
function praticheFiltrate(elenco, filtro, ordine, cerca) {
  const c = String(cerca || "").trim().toLowerCase();
  const out = elenco.filter(p => {
    if (c && !String(p.titolo || "").toLowerCase().includes(c)) return false;
    const t = terminePresentazione(p.data_decesso);
    return filtro === "vicine" ? !!t && t.giorni >= 0 && t.giorni <= 60 : filtro === "superate" ? !!t && t.giorni < 0
      : filtro === "senza_data" ? !t : true;
  });
  if (ordine === "scadenza") out.sort((a, b) => { const ta = terminePresentazione(a.data_decesso), tb = terminePresentazione(b.data_decesso);
    return (ta ? ta.data.getTime() : Infinity) - (tb ? tb.data.getTime() : Infinity); });
  return out;   // «recenti»: ordine del server (ultima modifica prima)
}
function filtriHome(ul) {
  let f = $("#homeFiltri");
  if (!f) {
    const cerca = h("input", { type: "search", "aria-label": "Cerca nel titolo", placeholder: "Cerca nel titolo", oninput: ev => { HOME.cerca = ev.target.value; renderHome(); } });
    const filtro = h("select", { "aria-label": "Filtra per termine", onchange: ev => { HOME.filtro = ev.target.value; renderHome(); } },
      Object.entries(FILTRI_HOME).map(([v, t]) => h("option", { value: v }, t)));
    const ordine = h("select", { "aria-label": "Ordina", onchange: ev => { HOME.ordine = ev.target.value; renderHome(); } },
      h("option", { value: "recenti" }, "Ultime modificate"), h("option", { value: "scadenza" }, "Per termine di presentazione"));
    f = h("div", { id: "homeFiltri", class: "filtri-home" }, cerca, filtro, ordine);
    ul.before(f);
  }
  f.hidden = S.pratiche.length < 2;
}
async function caricaPratiche() {
  S.pratiche = await api("/api/pratiche");
  renderHome();
  const ul = $("#lista"); ul.replaceChildren();
  if (!S.pratiche.length) ul.append(h("li", { class: "mut" }, "Nessuna pratica."));
  for (const p of S.pratiche) ul.append(h("li", {}, h("button", { title: p.titolo + " (rev. " + p.revisione + ")", "aria-current": S.P && S.P.pratica_id === p.id ? "true" : "false", onclick: () => apri(p.id) }, h("span", { class: "tit-pratica" }, p.titolo))));
}
async function apri(id, sel) {
  if (S.writeBusy) { msg("Salvataggio in corso: attendi prima di cambiare pratica.", "e"); return; }
  if (nMod() && !confirm("Ci sono modifiche non salvate: continuare senza salvarle?")) return;
  S.gen++;   // invalida le risposte asincrone (es. codice fiscale) richieste per la pratica precedente
  S.dirty.clear(); S.nuove.clear(); S.dichDirty.clear(); S.supDirty.clear(); S.riga = null; S.tab = "dati"; S.salvata = null; S.allegati = null;
  S.fornitoreDirty = {};
  try { await ricarica(id); }
  catch (e) { msg("Pratica non aperta. " + e.message, "e"); return; }
  try { localStorage.setItem('successioni.ultima', id); } catch (_) { /* facoltativo */ }   // solo dopo conferma e apertura riuscita
  S.sel = sel || "AN"; $('#vista').scrollTop = 0; render(); await caricaPratiche();
}
async function ricarica(id) {
  id = id || S.P.pratica_id;
  S.P = await api("/api/pratiche/" + id);
  S.Q = await api("/api/pratiche/" + id + "/quadri");
  $("#titolo").textContent = S.P.titolo;
}
function render() {
  const aperta = !!S.P;
  $("#vuoto") && ($("#vuoto").hidden = aperta);
  const q = aperta ? quadro() : null;
  // quadro con una sola riga: si apre gia' selezionata (report grafica 07/11/2026, punto 2)
  if (q && q.coll && !S.riga && S.tab === "dati" && S.chiuso !== q.id) { const rr = righeQuadro(q); if (rr.length === 1) S.riga = rr[0].key; }
  // il pannello di destra resta chiuso finche' non c'e' una riga selezionata (o una scheda Controlli/Cronologia aperta):
  // senza selezione occupava un quarto dello schermo per dire «Seleziona una riga»
  const conTabella = q && q.coll;
  const pannello = aperta && S.sel !== 'FILE' && (S.tab !== 'dati' || (conTabella && !!S.riga));
  $("#app").classList.toggle("conIns", pannello); $("#ins").hidden = !pannello; $('#ridimensiona').hidden = !pannello;
  renderAlbero(); renderVista(); renderIns(); renderSb(); aggiornaBottoni();
}
function aggiornaBottoni() {
  const n = nMod();
  $("#bSalva").className = n ? "pil" : "gh"; $("#bNuova").className = "gh";   // senza pratica aperta l'azione principale e' nella pagina iniziale
  $("#bSalva").disabled = !n || S.writeBusy; $("#bSalva").textContent = S.writeBusy ? "Salvataggio…" : n ? "Salva (" + n + ")" : "Salva";
  $("#bControlla").disabled = !S.P; $("#bGenera").disabled = !S.P; $("#bGenera").title = "Apri l'area unica File e invio della pratica";
  $('#bGenera').setAttribute('aria-pressed', String(S.sel === 'FILE'));
  $("#bControlla").textContent = S.Q && S.Q.rilievi.length ? "Controlla (" + S.Q.rilievi.length + ")" : "Controlla";
}
function renderSb() {
  const sb = $("#sb"); sb.replaceChildren();
  const arch = STUDIO.archivio ? h("span", { class: "arch", title: STUDIO.archivio }, "Archivio: " + STUDIO.archivio.split(/[\\/]/).filter(Boolean).pop()) : null;
  if (!S.P) { sb.append(...[arch, h("span", {}, "Nessuna pratica aperta")].filter(Boolean)); return; }
  const n = S.Q.rilievi.length;
  sb.append(...[arch, h("span", {}, "Revisione " + S.P.revisione),
    S.salvata ? h("span", { class: "ok" }, "Salvata alle " + S.salvata) : null,
    nMod() ? h("span", { class: "am" }, nMod() + (nMod() === 1 ? " modifica non salvata" : " modifiche non salvate")) : null,
    n ? h("button", { onclick: () => { if (S.sel === 'FILE') S.sel = 'AN'; S.tab = "controlli"; render(); } }, n + (n === 1 ? " rilievo" : " rilievi")) : h("span", {}, "Nessun rilievo"),
    (S.Q.avvisi || []).length ? h("button", { class: "am", onclick: () => { if (S.sel === 'FILE') S.sel = 'AN'; S.tab = "controlli"; render(); } }, S.Q.avvisi.length + (S.Q.avvisi.length === 1 ? " avviso" : " avvisi")) : null,
    h("span", {}, S.Q.finalizzabile ? "Finalizzabile" : "Non finalizzabile" + ((S.Q.blocchi_finalizzazione || []).length ? ": file XML completo non generato" : "")),
    h("span", {}, "Controllo ufficiale: vedi File e invio")].filter(Boolean));
}
function vaiFile() { if (!S.P) return; S.sel = 'FILE'; S.riga = null; S.tab = 'dati'; $('#vista').scrollTop = 0; render(); }
function scegliQuadro(id) { S.sel = id; S.riga = null; S.chiuso = null; S.tab = 'dati'; $('#vista').scrollTop = 0; render(); }
function chiudiPannello() { const q = quadro(); S.chiuso = q ? q.id : null; S.riga = null; S.tab = "dati"; render(); tornaTabella(); }

/* ---------- albero dei quadri ---------- */
/* Titoli brevi nell'elenco (report grafica 07/11/2026, punto 5): il titolo ufficiale resta nel suggerimento e in testa al quadro. */
const TITOLI_BREVI = { EA: "Eredi e altri soggetti", EB: "Terreni", EC: "Fabbricati", ER: "Rendite, crediti, altri beni", ED: "Passività",
  EF: "Liquidazione imposte", EG: "Documenti allegati", EI: "Dichiarazioni per la voltura", EL: "Terreni tavolari", EM: "Fabbricati tavolari",
  EO: "Titoli e quote sociali", EQ: "Navi e imbarcazioni", EH: "Dichiarazioni sostitutive", EE: "Riepilogo dell'asse" };
function renderAlbero() {
  const nav = $("#albero"); nav.replaceChildren();
  if (!S.Q) return;
  nav.append(h('button', { class: 'voce nav-file', id: 'navFile', title: 'File e invio', 'aria-current': S.sel === 'FILE' ? 'page' : 'false', onclick: vaiFile },
    h('span', { class: 'sigla' }, '↗'), h('span', {}, 'File e invio')));
  for (const [g, nome] of [["frontespizio", "Frontespizio"], ["quadri", "Quadri"], ["riepiloghi", "Riepiloghi"], ["lavoro", "Tabella di lavoro"]]) {
    nav.append(h("div", { class: "gruppo" }, nome));
    for (const q of S.Q.quadri.filter(x => x.gruppo === g)) {
      const st = q.stato;
      const lav = statoLavoro(q.id);   // stato di lavorazione scelto dallo studio (voce 10), dopo lo stato calcolato
      const testo = [st === "rilievi" ? q.rilievi + (q.rilievi === 1 ? " rilievo" : " rilievi") : (q.righe && st === "compilato" ? q.righe + (q.righe === 1 ? " riga" : " righe") : STATI[st]),
        lav && STATI_LAVORO[lav]].filter(Boolean).join(" · ");
      nav.append(h("button", { class: "voce", "data-stato": st, "data-lavoro": lav || null, "data-q": q.id, title: q.id + " — " + q.titolo + (testo ? " (" + testo + ")" : ""), "aria-current": S.sel === q.id ? "true" : "false", onclick: () => scegliQuadro(q.id) },
        h("span", { class: "sigla" }, q.id), h("span", { class: "testi" }, h("span", { class: "nome" }, TITOLI_BREVI[q.id] || q.titolo), h("span", { class: "st" }, testo))));
    }
  }
}

/* ---------- campi ---------- */
/* Menu dei codici ufficiali (generati dagli XSD, server: codici.py): chiave «coll.campo», o «coll.campo@immobile|altro» per i
   diritti, che dipendono dal tipo del bene. Restituisce la definizione o null (il campo resta di testo libero). */
function struttDi(coll, campo, tipoBene) {
  const s = S.schema.strutturati || {};
  const ctx = (coll === "beni" || coll === "devoluzioni") ? (["fabbricato", "terreno"].includes(tipoBene) ? "immobile" : "altro") : null;
  return (ctx && s[coll + "." + campo + "@" + ctx]) || s[coll + "." + campo] || null;
}
/* Elenchi lunghi di codici ammessi (server: codici.suggerimenti, chiave «coll.campo»): suggerimenti con <datalist>, il campo resta di testo. */
function listaSuggerimenti(chiave) {
  const s = ((S.schema || {}).suggerimenti || {})[chiave];
  if (!s) return null;
  const id = "dl_" + chiave.replace(/[^a-z0-9]+/gi, "_");
  if (!document.getElementById(id)) {
    const dl = h("datalist", { id });
    for (const v of s.valori) dl.append(h("option", { value: v }));
    document.body.append(dl);
  }
  return id;
}
const MAX_LUNGHEZZA = { "beni.nazionalita": 20 };   // XSD: Nazionalita, massimo 20 caratteri (nessun elenco ufficiale: resta testo)
function campoInput(coll, id, campo, kind, val, onMod, tipoBene) {
  const sd = kind === "str" || kind === "cf" ? struttDi(coll, campo, tipoBene) : null;
  if (sd && sd.opzioni) return campoStrutturato(sd, val, v => onMod(campo, v), id ? coll + "[" + id + "]." + campo : null);
  const path = id ? coll + "[" + id + "]." + campo : null;
  const err = path ? rilievi().filter(r => r.percorso === path) : [];
  let el;
  if (kind.startsWith("enum:")) {
    el = h("select", { name: campo, "aria-label": lbl(coll, campo) }, h("option", { value: "" }, ""), kind.slice(5).split("|").map(o => h("option", { value: o }, nomeVal(coll, campo, o))));
    el.value = val || "";
  } else if (kind.startsWith("ref:")) {
    const rc = kind.slice(4);
    el = h("select", { name: campo, "aria-label": lbl(coll, campo) }, h("option", { value: "" }, ""), (S.P.dati[rc] || []).map(e => h("option", { value: e.id }, etichetta(rc, e))));
    el.value = val || "";
  } else {
    const lista = listaSuggerimenti(coll + "." + campo);
    el = h("input", { name: campo, "aria-label": lbl(coll, campo), autocomplete: "off", list: lista, maxlength: MAX_LUNGHEZZA[coll + "." + campo], class: kind === "cf" ? "mono cf" : (kind === "importo" || kind === "quota" ? "num" : ""), placeholder: kind === "quota" ? "1/2" : kind === "data" ? "GG/MM/AAAA" : "" });
    el.value = mostra(kind, val);
  }
  if (path) el.dataset.path = path;
  if (err.length) el.classList.add("bad");
  // «change» puo' arrivare quando il campo con il focus viene tolto da un nuovo disegno (dopo Salva o cambiando pratica): il valore
  // e' gia' arrivato con «input», e la riga potrebbe non essere piu' quella mostrata. Un campo staccato dal documento non scrive.
  const f = () => { if (el.isConnected) onMod(campo, leggi(kind, el.value)); };
  el.addEventListener("input", f); el.addEventListener("change", f);
  return h("div", {}, el, err.map(r => h("div", { class: "e" }, r.messaggio)));
}

/* Valore gia' presente scritto in un altro modo ma equivalente per l'esportazione: «A/2» e «a2» valgono «A2»; per i diritti la
   descrizione («proprieta» per «1», regola di esporta.codice_enum con alias_descrizione, elenco in sd.alias dal server); «08» vale «8».
   Restituisce il codice della voce, oppure il valore cosi' com'e'. Il dato non cambia finche' l'utente non sceglie. */
const normAlias = x => String(x).toLowerCase().replace(/['’]/g, "").replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
function riconosciVoce(sd, attuale) {
  if (!attuale || sd.opzioni.some(o => o.valore === attuale)) return attuale;
  const norm = x => String(x).replace(/[\s\/]/g, "").toUpperCase();
  const gemella = sd.opzioni.find(o => norm(o.valore) === norm(attuale));
  if (gemella) return gemella.valore;
  const al = sd.alias || {};
  for (const k of [attuale, normAlias(attuale)]) if (Object.prototype.hasOwnProperty.call(al, k) && sd.opzioni.some(o => o.valore === al[k])) return al[k];
  if (/^\d+$/.test(attuale) && sd.opzioni.some(o => o.valore === attuale.replace(/^0+/, ""))) return attuale.replace(/^0+/, "");
  return attuale;
}
// «RM — RM»: quando l'etichetta ripete il codice si mostra una volta sola (report grafica 07/11/2026, punto 7)
const testoVoce = (sd, o) => sd.senza_codice || !o.etichetta ? (o.etichetta || o.valore)
  : String(o.etichetta).trim().toUpperCase() === String(o.valore).trim().toUpperCase() ? o.valore : o.valore + " — " + o.etichetta;

/* Campo a scelta guidata (S.schema.strutturati, definito in schema.py): menu con etichette e aiuto della voce scelta.
   Un valore gia' presente ma non nell'elenco (o uno stato come [da_confermare]) resta visibile e non viene perso.
   Il menu occupa la larghezza disponibile, il testo lungo si tronca con «...» e si legge per intero nel suggerimento (title). */
function campoStrutturato(sd, val, onMod, path) {
  const err = path ? rilievi().filter(r => r.percorso === path) : [];
  const grezzo = val === undefined || val === null ? "" : (typeof val === "object" && val.stato ? "[" + val.stato + "]" : String(val));
  const attuale = riconosciVoce(sd, grezzo);
  const el = h("select", { "aria-label": sd.etichetta },
    h("option", { value: "" }, "(non indicato)"),
    sd.opzioni.map(o => h("option", { value: o.valore, title: testoVoce(sd, o) }, testoVoce(sd, o))),
    attuale && !sd.opzioni.some(o => o.valore === attuale) ? h("option", { value: attuale },
      /^\[[a-z_]+\]$/.test(attuale) ? mostra("str", { stato: attuale.slice(1, -1) }) : attuale + " (valore non previsto)") : null);
  el.value = attuale;
  if (path) el.dataset.path = path;
  if (err.length) el.classList.add("bad");
  const dett = h("div", { class: "mut aiuto-voce" });
  const mostraAiuto = () => {
    const o = sd.opzioni.find(x => x.valore === el.value);
    dett.textContent = o ? o.aiuto : "";
    el.title = el.selectedOptions[0] ? el.selectedOptions[0].textContent : "";
  };
  const f = () => { mostraAiuto(); onMod(leggi("str", el.value)); };
  el.addEventListener("change", f);
  mostraAiuto();
  return h("div", {}, el, dett, err.map(r => h("div", { class: "e" }, r.messaggio)));
}

/* ---------- vista centrale ---------- */
/* Stesso instradamento di quadri.quadro_di (server): le province tavolari arrivano da /api/schema. */
function quadroBene(e) {
  const prov = String(e.provincia || "").trim().toUpperCase();
  const tav = (S.schema.province_tavolari || []).includes(prov) || ["1", "si", "true"].includes(String(e.sistema_tavolare || "").trim().toLowerCase());
  if (tav && (e.tipo === "terreno" || e.tipo === "fabbricato")) return e.tipo === "terreno" ? "EL" : "EM";
  return { terreno: "EB", fabbricato: "EC", titolo: "EO", aeromobile: "EP", nave: "EQ", azienda: "EN" }[e.tipo] || "ER";
}
function appartiene(q, e) {
  if (q.coll === "persone") return !["defunto", "presentatore"].includes(e.ruolo);
  if (q.coll === "beni") return quadroBene(e) === q.id;
  return true;
}
function righeQuadro(q) {
  const out = [];
  for (const e of S.P.dati[q.coll] || []) if (appartiene(q, e)) out.push({ key: "e:" + q.coll + ":" + e.id, e });
  for (const [k, n] of S.nuove) if (n.q === q.id) out.push({ key: k, nuova: n });
  return out;
}
const valRiga = (r, c) => { const d = S.dirty.get(r.key); if (d && c in d.campi) return d.campi[c]; return r.nuova ? r.nuova.campi[c] : r.e[c]; };

function renderVista() {
  const main = $("#vista"); const y = main.scrollTop;
  for (const el of [...main.children]) if (el.id !== "vuoto") el.remove();
  if (S.P && S.sel === 'FILE') {
    main.append(h('h1', {}, 'File e invio'), h('p', { class: 'generali-intro' }, 'Un solo spazio per il fornitore, il file telematico, i controlli e le ricevute di questa pratica.'));
    insFile(main); return;
  }
  const q = quadro();
  if (!q) return;
  const titoloQ = h("h1", {}, (q.id === "AN" || q.id === "DV" ? "" : q.id + " — ") + q.titolo);
  const arg = typeof argomentoDelQuadro === "function" ? argomentoDelQuadro(q.id) : null;
  const linkIstr = arg ? h("button", { class: "lk istr-quadro", title: "Apre le istruzioni ufficiali alla pagina " + arg.pagina, onclick: () => apriIstruzioni(arg.documento, arg.pagina) }, "Istruzioni del quadro") : null;
  main.append(h("div", { class: "testa-quadro" }, titoloQ, linkIstr, q.coll && (q.vista === "tabella" || q.vista === "documenti") && q.supportato ? menuOperazioni(q) : null));
  // stato di lavorazione del quadro (voce 10: nota interna) nella riga sotto il titolo, per non spostare il menu «Operazioni»
  main.append(h("div", { class: "sottotitolo" }, q.nota || (q.vista === "tabella" || q.vista === "documenti" ? (q.righe + (q.righe === 1 ? " riga" : " righe")) : ""), " ", selettoreStato(q)));
  if (!q.attivo && q.supportato) main.append(h("div", { class: "nota" }, "Questo quadro non è selezionato per la dichiarazione. ", h("button", { class: "lk", onclick: () => impostaQuadro(q.id, true) }, "Seleziona il quadro")));
  if (q.rilievi && q.vista !== "frontespizio") main.append(h("div", { class: "avv" }, h("b", {}, q.rilievi + (q.rilievi === 1 ? " rilievo" : " rilievi")), h("span", { class: "cresce" }, rilievi().find(r => r.quadro === q.id).messaggio), h("button", { class: "gh", onclick: () => { S.tab = "controlli"; renderIns(); } }, "Vedi controlli")));
  if (q.vista === "frontespizio") renderFront(main);
  else if (q.vista === "derivato") main.append(h("div", { class: "nota" }, q.nota || "Quadro generato automaticamente dal programma."));
  else if (q.generato && ["EE", "EF", "EH"].includes(q.id)) renderAnteprima(main, q);
  else if (q.vista === "non_supportato") renderNonSupp(main, q);
  else { renderTabella(main, q); if (q.vista === "documenti") renderAllegati(main); }
  main.scrollTop = y;
}
/* Quadri EE, EF, EH: calcolati dal programma come nel file (server: elaborati.anteprima_quadri), mostrati a video; nel quadro EH le
   caselle che dipendono da una scelta del dichiarante si modificano qui. */
const VOCI_EE = { TotaleValoreTerreni: "Terreni", TotaleValoreFabbricati: "Fabbricati", TotaleValoreImmobili: "Immobili (terreni e fabbricati)",
  TotaleValoreAziende: "Aziende", TotaleValoreTitoli: "Azioni, obbligazioni e altri titoli", TotaleValoreAeromobili: "Aeromobili",
  TotaleValoreNavi: "Navi e imbarcazioni", TotaleValoreAltriBeni: "Rendite, crediti e altri beni", TotaleAttivo: "Totale attivo",
  TotalePassivo: "Totale passività", TotaleValoreAsseEreditarioNetto: "Asse ereditario netto" };
const VOCI_EH = { FlagDeceduto: "Il defunto è deceduto (data e luogo del decesso)", PresenzaDichiarante: "Il dichiarante è tra gli eredi o legatari",
  FlagAssenzaDichiarante: "Il dichiarante non è tra gli eredi o legatari", FlagTestamento: "Presenza di testamento (estremi)",
  FlagAssenzaTestamento: "Assenza di testamento", FlagInterdetti: "Presenza di interdetti o inabilitati", FlagAssenzaInterdetti: "Assenza di interdetti o inabilitati",
  FlagRinuncia: "Presenza di rinunce all'eredità", FlagAssenzaRinuncia: "Assenza di rinunce all'eredità", FlagSeparazione: "Separazione con addebito al coniuge",
  FlagAssenzaSeparazione: "Assenza di separazione con addebito", FlagNoScioglimentoUnioneCivile: "Nessuna domanda di scioglimento dell'unione civile",
  FlagReintegro: "Accordi di reintegro dei diritti di legittima", FlagAzienda: "Bilanci di aziende o società (deposito)", FlagNavi: "Navi o imbarcazioni (estremi)",
  FlagAeromobili: "Aeromobili (estremi)", FlagPassivita: "Documenti delle passività: copie degli originali (lettera l)",
  FlagProspetto: "Inventari/prospetti delle attività e passività: copie degli originali (lettera l)", FlagInventari: "Inventari allegati tra gli altri documenti: copie degli originali (lettera l)",
  FlagAttiLegali: "Passaggi senza atti legali (quadro EI)" };
const euroIt = v => { const n = Number(v); return isNaN(n) ? String(v) : n.toLocaleString("it-IT", { minimumFractionDigits: String(v).includes(".") ? 2 : 0, maximumFractionDigits: 2 }) + " €"; };
async function renderAnteprima(main, q) {
  const pid = S.P.pratica_id;
  main.append(h("div", { class: "nota" }, "Il quadro " + q.id + " è calcolato dal programma con i dati salvati della pratica, come nel file della dichiarazione. " +
    (nMod() ? "Ci sono modifiche non salvate: salva per aggiornare questa vista." : "")));
  const box = h("div", {}, h("p", { class: "mut" }, "Calcolo in corso…")); main.append(box);
  let r;
  try { r = await api("/api/pratiche/" + pid + "/anteprima-quadri"); } catch (e) { box.replaceChildren(h("div", { class: "avv" }, e.message)); return; }
  if (!S.P || S.P.pratica_id !== pid || !quadro() || quadro().id !== q.id) return;
  box.replaceChildren();
  if (q.id === "EE") {
    if (!r.ee.length) box.append(h("p", { class: "mut" }, "Nessun totale calcolabile: vedi i motivi qui sotto."));
    else box.append(h("div", { class: "tab piatta" }, h("table", {}, h("tbody", {}, r.ee.map(x => h("tr", { class: ["TotaleAttivo", "TotaleValoreAsseEreditarioNetto"].includes(x.campo) ? "fisso forte" : "fisso" },
      h("td", {}, VOCI_EE[x.campo] || x.campo), h("td", { class: "n" }, euroIt(x.valore))))))));
  } else if (q.id === "EF") {
    if (!r.ef) box.append(h("p", { class: "mut" }, "Imposte non calcolabili finché non si risolvono i punti qui sotto."));
    else box.append(h("div", { class: "tab piatta" }, h("table", {}, h("tbody", {},
      r.ef.imposte.map(([k, v]) => h("tr", { class: "fisso" }, h("td", {}, k), h("td", { class: "n" }, isNaN(Number(v)) ? v : euroIt(v)))),
      h("tr", { class: "fisso forte" }, h("td", {}, "Totale da versare (EF19)"), h("td", { class: "n" }, r.ef.totale ? euroIt(r.ef.totale) : "—")),
      r.ef.importo_da_versare && r.ef.importo_da_versare !== r.ef.totale ? h("tr", { class: "fisso" }, h("td", {}, "Importo da versare (frontespizio, con sanzioni e interessi)"), h("td", { class: "n" }, euroIt(r.ef.importo_da_versare))) : null))));
  } else if (q.id === "EH") {
    const sez1 = r.eh.filter(x => x.sezione === "SezioneI_DichSost"), altre = r.eh.filter(x => x.sezione !== "SezioneI_DichSost");
    box.append(h("section", { class: "grp" }, h("h2", {}, "Sezione I - Dichiarazioni sostitutive: cosa risulta dai dati"),
      sez1.length ? h("ul", { class: "spunte-eh" }, sez1.map(x => h("li", {}, "☑ " + (VOCI_EH[x.campo] || x.campo)))) : h("p", { class: "mut" }, r.solo_ee || r.errori.length ? "Non calcolabile finché non si risolvono i punti qui sotto." : "Nessuna casella."),
      altre.length ? h("p", { class: "mut" }, "Altre sezioni: " + [...new Set(altre.map(x => x.sezione.replace(/_/g, " ")))].join(", ")) : null,
      h("p", { class: "mut dentro-testo" }, "Testamento, interdetti, rinunce, eredi e aziende derivano dai dati degli altri quadri. Qui sotto le caselle che dipendono da una dichiarazione esplicita.")));
    box.append(sezioneDatiDichiarazione(['dichiara_copie_conformi', 'flag_inventari', 'separazione_con_colpa', 'no_scioglimento_unione_civile'], 'Caselle del dichiarante (quadro EH, lettere h ed l)'));
  }
  const punti = [...r.errori.map(t => ["er", t]), ...r.mancanti.map(t => ["av", t])];
  if (punti.length) box.append(h("section", { class: "grp" }, h("h2", {}, "Da sistemare prima di generare il file"), h("ul", { class: "elenco-azioni" }, punti.map(([k, t]) => h("li", { class: k }, t)))));
}
function renderNonSupp(main, q) {
  if (q.generato) {   // EE, EF, EH, EI: li produce il programma alla generazione del file; non c'e' nulla da compilare ne' da selezionare
    main.append(h("div", { class: "nota" }, "Il quadro " + q.id + " viene generato dal programma a partire dai dati degli altri quadri: non si compila e non va selezionato."
      + (q.attivo ? " In questa pratica risulta selezionato (scelta precedente): finche' resta selezionato la dichiarazione non e' finalizzabile." : "")));
    if (q.attivo) main.append(h("div", { class: "barra" }, h("button", { class: "gh", onclick: () => impostaQuadro(q.id, false) }, "Deseleziona il quadro")));
    return;
  }
  main.append(h("div", { class: "nota" }, "Il quadro " + q.id + " non è ancora supportato (" + (q.motivo || "") + "). I dati già inseriti altrove restano conservati; finché il quadro è selezionato la dichiarazione non può essere finalizzata."));
  main.append(h("div", { class: "barra" }, h("button", { class: "gh", onclick: () => impostaQuadro(q.id, !q.attivo) }, q.attivo ? "Deseleziona il quadro" : "Seleziona il quadro (blocca la finalizzazione)")));
}
async function impostaQuadro(id, on) {
  const cur = new Set((S.P.dati.opzioni.quadri_attivi) || S.schema.predefiniti);
  on ? cur.add(id) : cur.delete(id);
  await salvaOps([{ op: "set", sezione: "opzioni", campi: { quadri_attivi: [...cur] } }]);
}

// colonne fisse: la prima (riconoscimento) a sinistra, valore/importo (ultima) a destra (report grafica 07/11/2026, punto 1)
function classeColonna(q) {
  const ultima = q.colonne.length - 1, fissaDx = ["valore", "importo"].includes(q.colonne[ultima]);
  return (c, j) => [["quota", "importo", "rendita", "valore", "reddito_dominicale"].includes(c) ? "n" : "",
    j === 0 ? "fissa-sx" : "", j === ultima && fissaDx ? "fissa-dx" : ""].filter(Boolean).join(" ");
}
function renderTabella(main, q) {
  const campi = S.schema.collezioni[q.coll];
  const righe = righeQuadro(q);
  const t = h("table", { role: "grid", "aria-label": q.titolo });
  const clsCol = classeColonna(q);
  t.append(h("thead", {}, h("tr", {}, q.colonne.map((c, j) => h("th", { class: clsCol(c, j) }, lbl(q.coll, c, q.id))))));
  const tb = h("tbody"); t.append(tb);
  righe.forEach((r, i) => tb.append(rigaTabella(q, r, (S.riga && righe.some(x => x.key === S.riga) ? S.riga === r.key : i === 0))));
  if (!righe.length) tb.append(h("tr", {}, h("td", { colspan: q.colonne.length, class: "mut" }, "Nessuna riga. Usa «Aggiungi riga».")));
  const piede = piedeTabella(q, righe); if (piede) t.append(piede);
  main.append(h("div", { class: "tab" }, t));
  main.append(h("div", { class: "barra" }, h("button", { class: "pil", onclick: () => aggiungiRiga(q) }, "Aggiungi riga"),

    h("span", { class: "mut" }, "Quote come 1/2, importi come 1.234,50. Per un dato non noto scrivi «?» (da confermare), «assente», «zero» o «non applicabile».")));
}
function rigaTabella(q, r, focalizzabile) {
  const campi = S.schema.collezioni[q.coll], clsCol = classeColonna(q);
  const id = r.e && r.e.id; const base = id ? q.coll + "[" + id + "]" : null;
  const rilRiga = base ? rilievi().filter(x => x.percorso === base || x.percorso.startsWith(base + ".")) : [];
  const tr = h("tr", { tabindex: focalizzabile ? "0" : "-1", "aria-selected": S.riga === r.key ? "true" : "false", class: (r.nuova || S.dirty.has(r.key)) ? "mod" : "", "data-key": r.key,
    onclick: () => selezionaRiga(r.key, "riga"),
    onkeydown: ev => tastiTabella(ev, tr, r.key) });
  q.colonne.forEach((c, j) => {
    const kind = campi[c]; const v = valRiga(r, c);
    let txt = kind.startsWith("enum:") && typeof v === "string" ? nomeVal(q.coll, c, v) : mostra(kind, v, true);
    if (c === "grado_parentela" && typeof v === "string" && v) {   // il grado si legge per nome (menu dei codici), non come codice
      const sdg = struttDi(q.coll, c, null), og = sdg && sdg.opzioni.find(x => x.valore === riconosciVoce(sdg, v));
      if (og) txt = og.etichetta;
    }
    if (kind.startsWith("ref:") && v) { const e = (S.P.dati[kind.slice(4)] || []).find(x => x.id === v); if (e) txt = etichetta(kind.slice(4), e); }
    if (q.coll === "documenti_ref" && c === "tipo_eg" && v) { const sd = struttDi(q.coll, c, null), o = sd && sd.opzioni.find(x => x.valore === v); if (o) txt = o.etichetta; }
    if (q.coll === "documenti_ref" && c === "allegato_id" && v) txt = descriviFileEG(v);
    const errCampo = base && rilievi().some(x => x.percorso === base + "." + c);
    const td = h("td", { class: [clsCol(c, j), kind === "cf" ? "cf" : ""].filter(Boolean).join(" "), title: txt, "data-allegato": q.coll === "documenti_ref" && c === "allegato_id" ? (v || "") : null }, j === 0 && rilRiga.length ? h("span", { class: "punto", title: rilRiga.map(x => x.messaggio).join("; ") }) : null, errCampo ? h("span", { class: "pz er" }, "da correggere") : txt,
      j === 0 && q.coll === "persone" && id && id === presentatoreId() ? h("span", { class: "pz ok badge-dich", title: "Presentatore della dichiarazione" }, "dichiarante") : null);   // voce 33
    tr.append(td);
  });
  return tr;
}
// riga dei totali per gli importi (report grafica 07/11/2026, punto 4): somma dei valori indicati, senza i dati non noti
function piedeTabella(q, righe) {
  const campi = S.schema.collezioni[q.coll], clsCol = classeColonna(q);
  const daSommare = q.colonne.filter(c => campi[c] === "importo" && ["valore", "importo"].includes(c));
  if (righe.length > 1 && daSommare.length) {
    const tot = {}, mancano = {};
    for (const c of daSommare) {
      let cent = 0, nonNoti = 0;
      for (const r of righe) { const v = valRiga(r, c); const m = typeof v === "string" && v.match(/^(-?)(\d+)(?:\.(\d{1,2}))?$/);
        if (m) cent += (m[1] ? -1 : 1) * (Number(m[2]) * 100 + Number((m[3] || "").padEnd(2, "0"))); else nonNoti++; }
      tot[c] = cent; mancano[c] = nonNoti;
    }
    return h("tfoot", {}, h("tr", {}, q.colonne.map((c, j) => h("td", { class: clsCol(c, j) },
      j === 0 ? "Totale (" + righe.length + " righe)" : c in tot ? (tot[c] / 100).toLocaleString("it-IT", { minimumFractionDigits: tot[c] % 100 ? 2 : 0, maximumFractionDigits: 2 }) + (mancano[c] ? " + " + mancano[c] + " da indicare" : "") : ""))));
  }
  return null;
}
/* Modifica di un campo nel pannello: si ridisegnano solo la riga della tabella e i totali, non tutta la vista (prima ~20-46 ms
   a tasto con 150 righe). Se la riga non c'e' (cambia quadro, vista diversa) si ridisegna la vista intera. */
function aggiornaRigaVista(key) {
  const q = quadro(), vecchia = rigaDaFocalizzare(key);
  const r = q && q.coll && vecchia ? righeQuadro(q).find(x => x.key === key) : null;
  if (!r) return renderVista();
  const nuova = rigaTabella(q, r, vecchia.tabIndex === 0);
  const aveFocus = document.activeElement === vecchia;
  vecchia.replaceWith(nuova); if (aveFocus) nuova.focus({ preventScroll: true });
  const t = nuova.closest("table"), piede = piedeTabella(q, righeQuadro(q)), vecchio = t.querySelector("tfoot");
  if (vecchio && piede) vecchio.replaceWith(piede); else if (vecchio) vecchio.remove(); else if (piede) t.append(piede);
}
/* Scheda dell'immobile a gruppi (report grafica 07/11/2026, punto 3): i campi collegati stanno vicini, su piu' colonne, e
   quelli meno usati restano ripiegati se vuoti. I campi non elencati finiscono in «Altri dati». */
const G_IDENT = ["provincia", "comune", "codice_comune", "comune_amministrativo", "codice_comune_amministrativo", "sezione", "foglio", "particella", "subalterno", "indirizzo"];
const G_TAV = ["comune_catastale", "codice_comune_catastale", "partita_tavolare", "corpo_tavolare", "porzione_materiale", "particella_denominatore", "sistema_tavolare"];
const GRUPPI_SCHEDA = {
  EC: [["Identificazione catastale", G_IDENT], ["Classamento", ["categoria", "classe", "zona_censuaria", "consistenza", "rendita", "rendita_proposta"]],
       ["Diritto e valore", ["diritto", "quota_defunto", "valore", "diritto_abitazione"]]],
  EB: [["Identificazione catastale", G_IDENT], ["Terreno", ["natura", "tipologia_terreno", "reddito_dominicale", "rendita"]],
       ["Diritto e valore", ["diritto", "quota_defunto", "valore"]]],
  EL: [["Identificazione tavolare", [...G_IDENT, ...G_TAV]], ["Terreno", ["natura", "tipologia_terreno", "reddito_dominicale", "rendita"]], ["Diritto e valore", ["diritto", "quota_defunto", "valore"]]],
  EM: [["Identificazione tavolare", [...G_IDENT, ...G_TAV]], ["Classamento", ["categoria", "classe", "zona_censuaria", "consistenza", "rendita", "rendita_proposta"]], ["Diritto e valore", ["diritto", "quota_defunto", "valore"]]],
};
/* Dati da riportare «con gli estremi presenti in catasto» (Fascicolo I p. PDF 20 per EB, p. PDF 28 per EC): etichetta in grassetto. */
const OBBLIGATORI = {
  EB: ["provincia", "comune", "codice_comune", "foglio", "particella", "reddito_dominicale", "quota_defunto", "diritto", "valore"],
  EC: ["provincia", "comune", "codice_comune", "foglio", "particella", "categoria", "rendita", "quota_defunto", "diritto", "valore"],
  EA: ["codice_fiscale", "cognome", "nome", "grado_parentela"],
};
function schedaAGruppi(gruppi, righe) {
  const usati = new Set(), out = [];
  for (const [titolo, campi] of gruppi) {
    const qui = righe.filter(([c]) => campi.includes(c)); if (!qui.length) continue;
    qui.forEach(([c]) => usati.add(c));
    out.push(h("section", { class: "gruppo-scheda" }, h("h4", {}, titolo), h("div", { class: "campi-scheda" }, qui.map(([, el]) => el))));
  }
  const resto = righe.filter(([c]) => !usati.has(c));
  if (resto.length) {
    const d = h("details", { class: "gruppo-scheda altri-dati" }, h("summary", {}, "Altri dati (" + resto.length + ")"), h("div", { class: "campi-scheda" }, resto.map(([, el]) => el)));
    if (resto.some(([, el, vuoto]) => !vuoto || el.querySelector(".bad, .e"))) d.open = true;
    out.push(d);
  }
  return out;
}
/* ---------- valore catastale (valore_catastale.py): il programma propone, il professionista decide e salva ---------- */
function euroIntero(v) { return Number(v).toLocaleString("it-IT") + " €"; }
function scriviValore(id, valore) {
  const key = "e:beni:" + id;   // stessa chiave di righeQuadro: la modifica resta da salvare come le altre
  const d = S.dirty.get(key) || { coll: "beni", id, campi: {} }; d.campi.valore = valore; S.dirty.set(key, d);
}
/* La risposta vale per la revisione salvata: si chiede di nuovo solo quando la pratica cambia (salvataggio o altra pratica). */
const VALORI_CAT = { chiave: null, promessa: null };
function valoriCatastali() {
  const chiave = S.P.pratica_id + "@" + S.P.revisione;
  if (VALORI_CAT.chiave !== chiave) {
    VALORI_CAT.chiave = chiave;
    VALORI_CAT.promessa = api("/api/pratiche/" + S.P.pratica_id + "/valori-catastali").catch(e => { if (VALORI_CAT.chiave === chiave) VALORI_CAT.chiave = null; throw e; });
  }
  return VALORI_CAT.promessa;
}
function boxValoreCatastale(q, r) {
  const box = h("div", { class: "vc", "aria-live": "polite" }, h("h4", {}, "Valore catastale"), h("p", { class: "mut" }, "Calcolo in corso…"));
  valoriCatastali().then(res => {
    const v = (res.beni || []).find(x => x.bene_id === r.e.id);
    box.replaceChildren(h("h4", {}, "Valore catastale"));
    if (!v) return box.append(h("p", { class: "mut" }, "Non disponibile per questa riga."));
    if (!v.calcolabile) return box.append(h("p", { class: "mut" }, "Non calcolato: " + v.motivo + "."));
    box.append(h("p", {}, h("strong", {}, euroIntero(v.valore)), " — minimo che l'ufficio non può rettificare."),
      h("p", { class: "mut" }, v.formula), h("p", { class: "mut fonte-vc" }, "Fonti: " + v.fonti.join("; ")));
    if (v.avviso) box.append(h("p", { class: "avv" }, v.avviso));
    if (S.dirty.has(r.key)) box.append(h("p", { class: "mut" }, "Il calcolo usa i dati salvati: salva le modifiche per aggiornarlo."));
    if (v.inferiore) box.append(h("p", { class: "avv" }, "Il valore dichiarato (" + euroIntero(v.dichiarato) + ") è inferiore."));
    if (v.dichiarato === null || v.inferiore || Number(v.dichiarato) !== Number(v.valore))
      box.append(h("button", { class: "gh", onclick: () => { scriviValore(r.e.id, v.valore); renderVista(); renderIns(); aggiornaBottoni(); renderSb();
        msg("Valore " + euroIntero(v.valore) + " inserito nella riga: premi «Salva» per confermarlo.", "o"); } }, "Usa il valore catastale"));
  }).catch(e => box.replaceChildren(h("h4", {}, "Valore catastale"), h("p", { class: "avv" }, "Valore catastale non calcolabile: " + e.message)));
  return box;
}
async function ricalcolaValori(q) {
  let res; try { res = await valoriCatastali(); } catch (e) { return msg(e.message, "e"); }
  const ids = new Set(righeQuadro(q).filter(x => x.e).map(x => x.e.id));
  const da = (res.beni || []).filter(v => ids.has(v.bene_id) && v.calcolabile && (v.dichiarato === null || v.inferiore));
  const non = (res.beni || []).filter(v => ids.has(v.bene_id) && !v.calcolabile).length;
  if (!da.length) return msg("Nessun valore da aggiornare: tutti i valori sono già pari o superiori al valore catastale" + (non ? " (" + non + " righe non calcolabili, vedi il pannello della riga)." : "."), "o");
  if (!confirm("Inserire il valore catastale in " + da.length + " righe senza valore o con valore inferiore? I valori più alti restano come sono. Potrai controllare e poi premere «Salva»."))
    return;
  da.forEach(v => scriviValore(v.bene_id, v.valore));
  renderVista(); renderIns(); aggiornaBottoni(); renderSb();
  msg(da.length + " valori inseriti" + (non ? "; " + non + " righe non calcolabili" : "") + ": premi «Salva» per confermarli.", "o");
}
function aggiungiRiga(q) {
  const key = "n:" + crypto.randomUUID();
  S.nuove.set(key, { q: q.id, coll: q.coll, id: nuovoId(q.coll), campi: { ...q.preset } });
  S.riga = key; S.tab = "dati"; render();
  if (!q.attivo && q.supportato) msg("Il quadro " + q.id + " non è selezionato: si seleziona da solo quando salvi la nuova riga.", "o");
  const primo = $("#ins .rg input, #ins .rg select"); if (primo) primo.focus();
}
function duplicaRiga(q) {
  const r = rigaSelezionata(); if (!q || !q.coll || !r) return msg("Seleziona prima la riga da duplicare.", "e");
  const campi = {};
  for (const c of Object.keys(S.schema.collezioni[q.coll])) { const v = valRiga(r, c); if (v !== undefined && v !== null && v !== "") campi[c] = JSON.parse(JSON.stringify(v)); }
  const key = "n:" + crypto.randomUUID();
  S.nuove.set(key, { q: q.id, coll: q.coll, id: nuovoId(q.coll), campi });
  S.riga = key; S.tab = "dati"; render();
  msg("Riga duplicata: modifica i dati diversi e premi «Salva»" + (q.coll === "beni" ? ". Le devoluzioni del bene non vengono copiate." : "."), "o");
}
async function eliminaRigaSelezionata(q) {
  const r = rigaSelezionata(); if (!q || !r) return msg("Seleziona prima la riga da eliminare.", "e");
  if (r.nuova) { S.nuove.delete(r.key); S.riga = null; return render(); }
  if (S.writeBusy) return msg("Salvataggio in corso: attendi prima di eliminare la riga.", "e");
  if (confirm("Eliminare dal quadro " + q.id + " la riga «" + etichetta(q.coll, r.e) + "»?")) await salvaOps([{ op: "remove", coll: q.coll, id: r.e.id }], () => {
    S.dirty.delete(r.key); S.riga = null; });
}
/* Menu «Operazioni» del quadro (report grafica 07/11/2026, punto 9): i comandi che valgono solo in questo quadro, con la scorciatoia. */
function menuOperazioni(q) {
  const voci = [["Aggiungi riga", "Alt+N", () => aggiungiRiga(q)], ["Duplica la riga selezionata", "Alt+D", () => duplicaRiga(q)]];
  if (q.coll === "beni" && ["EB", "EC"].includes(q.id)) voci.push(["Ricalcola valori catastali", "", () => ricalcolaValori(q)]);
  if (CAMPI_GRUPPO[q.coll]) voci.push(["Modifica di gruppo…", "", () => modificaDiGruppo(q)]);
  if (q.vista === "tabella" && colonneIncolla(q).length) voci.push(["Incolla da Excel…", "", () => incollaRighe(q)]);
  if (q.coll === "beni" || q.coll === "devoluzioni") voci.push(["Brogliaccio da stampare", "", () => window.open("/api/pratiche/" + S.P.pratica_id + "/brogliaccio", "_blank")],
    ["Brogliaccio in CSV", "", () => { const a = h("a", { href: "/api/pratiche/" + S.P.pratica_id + "/brogliaccio.csv", download: "" }); document.body.append(a); a.click(); a.remove(); }]);
  voci.push(["Elimina la riga selezionata", "", () => eliminaRigaSelezionata(q)]);
  const d = h("details", { class: "operazioni" }, h("summary", { class: "gh", "aria-haspopup": "menu" }, "Operazioni"));
  const voceMenu = n => { const v = [...d.querySelectorAll("[role=menuitem]")]; if (v.length) v[(n + v.length) % v.length].focus(); };
  d.addEventListener("toggle", () => { if (d.open && document.activeElement === d.querySelector("summary")) voceMenu(0); });
  d.addEventListener("keydown", ev => {
    const v = [...d.querySelectorAll("[role=menuitem]")], i = v.indexOf(document.activeElement);
    if (ev.target.tagName === "SUMMARY" && ev.key === "ArrowDown") { ev.preventDefault(); d.open = true; voceMenu(0); return; }
    if (i < 0) return;
    const n = { ArrowDown: i + 1, ArrowUp: i - 1, Home: 0, End: v.length - 1 }[ev.key];
    if (n !== undefined) { ev.preventDefault(); voceMenu(n); }
    else if (ev.key === "Tab") d.open = false;
  });
  d.append(h("div", { class: "menu-op", role: "menu", "aria-label": "Operazioni del quadro " + q.id }, voci.map(([t, k, f]) => h("button", { role: "menuitem", tabindex: "-1", onclick: () => { d.open = false; f(); } },
    h("span", {}, t), k ? h("kbd", {}, k) : null))));
  return d;
}
/* Tastiera nella tabella (roving tabindex: una sola tappa Tab per tabella). Frecce su/giu, Home e Fine spostano il focus tra le
   righe; Invio o Spazio aprono la riga e portano il focus al primo campo del pannello (Esc, gestito in layout.js, torna alla riga). */
function tastiTabella(ev, tr, key) {
  const righe = [...tr.parentElement.querySelectorAll("tr[data-key]")], i = righe.indexOf(tr);
  const vai = n => { const t = righe[Math.max(0, Math.min(righe.length - 1, n))]; if (!t) return; ev.preventDefault();
    righe.forEach(x => x.tabIndex = -1); t.tabIndex = 0; t.focus(); };
  if (ev.key === "ArrowDown") vai(i + 1); else if (ev.key === "ArrowUp") vai(i - 1);
  else if (ev.key === "Home") vai(0); else if (ev.key === "End") vai(righe.length - 1);
  else if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); selezionaRiga(key, "pannello"); }
}
function rigaDaFocalizzare(key) { return document.querySelector('tr[data-key="' + CSS.escape(key) + '"]'); }
function selezionaRiga(key, dove) {
  S.riga = key; S.tab = "dati"; render();
  if (dove === "pannello") { const primo = $("#ins .rg input, #ins .rg select, #ins .rg textarea"); if (primo) { primo.focus(); return; } }
  if (dove) { const tr = rigaDaFocalizzare(key); if (tr) tr.focus({ preventScroll: true }); }
  if (window.innerWidth <= 960) $("#ins").scrollIntoView({ block: "start" });   // su schermo stretto il pannello sta sotto la tabella
}
function tornaTabella() {
  const tr = S.riga && rigaDaFocalizzare(S.riga) || document.querySelector("#vista tbody tr[tabindex]");
  if (tr) { tr.focus({ preventScroll: true }); tr.scrollIntoView({ block: "center" }); }
}

/* ---------- miglioramenti dall'analisi del 07/11/2026 (docs/ANALISI_REPLICA_2026-11-07.md, voci 5, 9, 10, 22, 33) ---------- */
/* Voce 22: devoluzioni del bene e somma delle quote per diritto, visibili nella scheda del bene mentre si compila.
   Conta anche le righe DV non ancora salvate; il controllo che blocca resta quello del servizio (DEVOLUZIONI_*). */
const _mcd = (a, b) => { a = Math.abs(a); b = Math.abs(b); while (b) [a, b] = [b, a % b]; return a || 1; };
function quotaFrazione(v) {
  if (v && typeof v === "object" && Number.isInteger(v.num) && Number.isInteger(v.den) && v.den > 0) return [v.num, v.den];
  const m = typeof v === "string" && v.trim().match(/^(\d+)\s*\/\s*(\d+)$/);
  return m && +m[2] > 0 ? [+m[1], +m[2]] : null;
}
function sommaQuote(quote) {
  let n = 0, d = 1, nonNote = 0;
  for (const q of quote) { const f = quotaFrazione(q); if (!f) { nonNote++; continue; }
    n = n * f[1] + f[0] * d; d = d * f[1]; const g = _mcd(n, d); n /= g; d /= g; }
  return { n, d, nonNote };
}
const quadroDV = () => S.Q && S.Q.quadri.find(x => x.id === "DV");
function righeDV(filtro) { const q = quadroDV(); return q ? righeQuadro(q).filter(filtro) : []; }
function nomeDiritto(codice, tipoBene) {
  const sd = struttDi("devoluzioni", "diritto", tipoBene), o = sd && sd.opzioni && sd.opzioni.find(x => x.valore === codice);
  return o ? o.etichetta : (codice || "diritto non indicato");
}
function nomePersona(id) { const p = (S.P.dati.persone || []).find(x => x.id === id); return p ? etichetta("persone", p) : "soggetto non indicato"; }
function boxDevoluzioniBene(r) {
  const beneId = r.e.id, tipo = valRiga(r, "tipo");
  const devs = righeDV(x => valRiga(x, "bene_id") === beneId);
  const box = h("div", { class: "dv-bene" }, h("h4", {}, "Devoluzioni del bene"));
  if (!devs.length) { box.append(h("p", { class: "mut" }, "Nessuna devoluzione: aggiungila nel quadro DV.")); return box; }
  const perDiritto = new Map();
  for (const x of devs) { const k = valRiga(x, "diritto") || ""; if (!perDiritto.has(k)) perDiritto.set(k, []); perDiritto.get(k).push(x); }
  for (const [dir, righe] of perDiritto) {
    const s = sommaQuote(righe.map(x => valRiga(x, "quota")));
    const esito = s.nonNote ? ["am", s.nonNote + (s.nonNote === 1 ? " quota da indicare" : " quote da indicare")]
      : s.n === s.d ? ["ok", "completa"] : s.n > s.d ? ["er", "supera 1/1"] : ["am", "manca " + (s.d - s.n) + "/" + s.d];
    box.append(h("table", { class: "dv-somma" }, h("caption", {}, nomeDiritto(dir, tipo)),
      h("tbody", {}, righe.map(x => h("tr", { class: "fisso" + ((x.nuova || S.dirty.has(x.key)) ? " mod" : "") },
        h("td", {}, nomePersona(valRiga(x, "persona_id"))), h("td", { class: "n" }, mostra("quota", valRiga(x, "quota")))))),
      h("tfoot", {}, h("tr", {}, h("td", {}, "Somma"), h("td", { class: "n" }, h("span", { class: "pz " + esito[0] }, s.n + "/" + s.d + " · " + esito[1]))))));
  }
  if (devs.some(x => x.nuova || S.dirty.has(x.key))) box.append(h("p", { class: "mut" }, "Comprende righe non ancora salvate."));
  return box;
}
/* Voce 33: riepilogo del soggetto nel quadro EA (ruolo, parentela, dichiarante, beni ricevuti con la quota). */
function presentatoreId() {
  const dich = ((S.P.dati.opzioni.telematico || {}).dichiarazione || {});
  return (dich.presentatore || {}).persona_id || ((S.P.dati.persone || []).find(p => p.ruolo === "presentatore") || {}).id || null;
}
function boxRiepilogoSoggetto(r) {
  const pid = r.e.id, box = h("div", { class: "riepilogo-soggetto" }, h("h4", {}, "Nella successione"));
  const voci = [nomeVal("persone", "ruolo", valRiga(r, "ruolo"))];
  const sdg = struttDi("persone", "grado_parentela", null), g = valRiga(r, "grado_parentela");
  const og = g && sdg && sdg.opzioni && sdg.opzioni.find(x => x.valore === riconosciVoce(sdg, g));
  if (g) voci.push(og ? og.etichetta : g);
  if (presentatoreId() === pid) voci.push("dichiarante");
  if (valRiga(r, "rappresentato_cf")) voci.push("per rappresentazione");
  if (valRiga(r, "certificatore_disabilita")) voci.push("disabilità o interdizione");
  box.append(h("p", {}, voci.filter(Boolean).join(" · ")));
  const devs = righeDV(x => valRiga(x, "persona_id") === pid);
  if (!devs.length) { box.append(h("p", { class: "mut" }, "Nessun bene attribuito nel quadro DV.")); return box; }
  box.append(h("ul", { class: "beni-soggetto" }, devs.map(x => { const b = (S.P.dati.beni || []).find(y => y.id === valRiga(x, "bene_id"));
    return h("li", {}, (b ? etichetta("beni", b) : "bene non indicato") + " — " + mostra("quota", valRiga(x, "quota")) + " (" + nomeDiritto(valRiga(x, "diritto"), b && b.tipo) + ")"); })));
  return box;
}
/* Voce 5: modifica di gruppo (beni e devoluzioni). I valori scelti diventano modifiche da salvare sulle righe spuntate: con
   «Salva» si crea una sola revisione, annullabile dalla Cronologia. Nessun campo viene cambiato se non e' spuntato. */
const CAMPI_GRUPPO = { beni: ["diritto", "quota_defunto", "data_visura"], devoluzioni: ["diritto", "quota"] };
function dialogo(id, titolo, corpo, conferma, onConferma) {
  const vecchio = document.getElementById(id); if (vecchio) vecchio.remove();
  const err = h("p", { class: "e", role: "alert", hidden: true });
  const ok = h("button", { class: "pil", value: "ok", onclick: ev => { ev.preventDefault(); const e = onConferma(); if (e) { err.textContent = e; err.hidden = false; } else d.close(); } }, conferma);
  // Invio in un campo: il modulo lo tratterebbe come clic sul primo pulsante («Annulla») e chiuderebbe perdendo i dati;
  // qui applica l'azione principale (i campi che usano Invio per conto loro lo fermano prima con preventDefault)
  const invio = ev => { if (ev.key === "Enter" && !ev.defaultPrevented && !ev.isComposing && ev.target.tagName === "INPUT") { ev.preventDefault(); ok.click(); } };
  const d = h("dialog", { id, class: "dlg-op", "aria-labelledby": id + "T" }, h("form", { method: "dialog", onkeydown: invio }, h("h2", { id: id + "T" }, titolo), corpo, err,
    h("div", { class: "wiz-az" }, h("button", { class: "gh", value: "annulla" }, "Annulla"), h("span", { class: "sp" }), ok)));
  document.body.append(d); d.showModal(); return d;
}
function descriviRigaGruppo(q, r) {
  if (q.coll !== "devoluzioni") return etichetta(q.coll, r.e);
  const b = (S.P.dati.beni || []).find(x => x.id === valRiga(r, "bene_id"));
  return nomePersona(valRiga(r, "persona_id")) + " — " + (b ? etichetta("beni", b) : "bene non indicato");
}
function modificaDiGruppo(q) {
  const campi = (CAMPI_GRUPPO[q.coll] || []).filter(c => c in S.schema.collezioni[q.coll]);
  const righe = righeQuadro(q).filter(x => x.e);
  if (!campi.length) return msg("La modifica di gruppo non è disponibile in questo quadro.", "e");
  if (righe.length < 2) return msg("Servono almeno due righe salvate per la modifica di gruppo.", "e");
  const tipoBene = q.coll === "beni" ? valRiga(righe[0], "tipo") : null;
  const scelte = new Map(righe.map(r => [r.key, true])), valori = {}, attivi = new Set(), svuota = new Set();
  const elenco = h("fieldset", { class: "gruppo-righe" }, h("legend", {}, "Righe da modificare"), righe.map(r => h("label", { class: "riga-sc" },
    h("input", { type: "checkbox", checked: true, "data-key": r.key, onchange: ev => scelte.set(r.key, ev.target.checked) }), " " + descriviRigaGruppo(q, r))));
  const blocchi = campi.map(c => {
    const spunta = h("input", { type: "checkbox", "data-campo": c, onchange: ev => { if (ev.target.checked) attivi.add(c); else { attivi.delete(c); svuota.delete(c); vuotaSc.checked = false; } } });
    // svuotare un campo in tutte le righe e' una scelta esplicita, mai l'effetto di una spunta senza valore
    const vuotaSc = h("input", { type: "checkbox", "data-svuota": c, onchange: ev => { if (ev.target.checked) { svuota.add(c); attivi.add(c); spunta.checked = true; } else svuota.delete(c); } });
    const w = campoInput(q.coll, null, c, S.schema.collezioni[q.coll][c], null, (campo, v) => { valori[campo] = v; attivi.add(campo); spunta.checked = true; }, tipoBene);
    return h("div", { class: "rg", "data-gruppo": c }, h("label", {}, spunta, " " + lbl(q.coll, c, q.id)), w,
      h("label", { class: "gruppo-svuota" }, vuotaSc, " svuota il campo in tutte le righe scelte"));
  });
  const vuoto = v => v === undefined || v === null || v === "";
  dialogo("dGruppo", "Modifica di gruppo · quadro " + q.id, h("div", {}, h("p", { class: "mut" }, "Spunta i campi da cambiare e le righe interessate. Le modifiche restano da salvare: controlla e premi «Salva»."), ...blocchi, elenco),
    "Applica alle righe", () => {
      const sel = righe.filter(r => scelte.get(r.key)), usati = [...attivi];
      if (!usati.length) return "Spunta almeno un campo da cambiare.";
      if (!sel.length) return "Spunta almeno una riga.";
      const senza = usati.filter(c => !svuota.has(c) && vuoto(valori[c]));
      if (senza.length) return "Nessuna modifica applicata: scegli un valore per " + senza.map(c => "«" + lbl(q.coll, c, q.id) + "»").join(", ")
        + ", oppure togli la spunta o scegli «svuota il campo».";
      const doppi = usati.filter(c => svuota.has(c) && !vuoto(valori[c]));
      if (doppi.length) return "Per " + doppi.map(c => "«" + lbl(q.coll, c, q.id) + "»").join(", ") + " hai scelto sia un valore sia «svuota il campo»: tieni una sola delle due.";
      const daSvuotare = usati.filter(c => svuota.has(c));
      if (daSvuotare.length && !confirm("Svuotare " + daSvuotare.map(c => "«" + lbl(q.coll, c, q.id) + "»").join(", ") + " in " + sel.length
        + (sel.length === 1 ? " riga" : " righe") + "? Il valore attuale viene cancellato; potrai controllare e poi premere «Salva»."))
        return "Nessuna modifica applicata.";
      for (const r of sel) { const d = S.dirty.get(r.key) || { coll: q.coll, id: r.e.id, campi: {} };
        for (const c of usati) d.campi[c] = svuota.has(c) ? null : valori[c]; S.dirty.set(r.key, d); }
      render(); msg(usati.length + (usati.length === 1 ? " campo cambiato" : " campi cambiati") + " in " + sel.length + " righe: premi «Salva» per confermare (una sola revisione).", "o");
      return null;
    });
}
/* Voce 9: incolla righe da Excel o da testo tabulato. Le colonne sono quelle della tabella, nello stesso ordine (una riga di
   intestazione con gli stessi nomi viene saltata). Le righe diventano righe nuove da salvare: i controlli sono quelli di «Salva». */
function colonneIncolla(q) { return q.colonne.filter(c => !(S.schema.collezioni[q.coll][c] || "").startsWith("ref:")); }
function incollaRighe(q) {
  const cols = colonneIncolla(q);
  const ta = h("textarea", { rows: 8, class: "incolla", "aria-label": "Righe da incollare", placeholder: cols.map(c => lbl(q.coll, c, q.id)).join("\t") });
  dialogo("dIncolla", "Incolla righe · quadro " + q.id, h("div", {}, h("p", { class: "mut" }, "Copia le celle da Excel (o testo separato da tabulazioni o da «;») con le colonne in quest'ordine:"),
    h("p", { class: "cod" }, cols.map(c => lbl(q.coll, c, q.id)).join(" · ")), ta), "Aggiungi le righe", () => {
      const r = righeDaTesto(ta.value, q, cols);
      if (r.errore) return r.errore;
      for (const campi of r.righe) S.nuove.set("n:" + crypto.randomUUID(), { q: q.id, coll: q.coll, id: nuovoId(q.coll), campi: { ...q.preset, ...campi } });
      S.riga = null; render(); msg(r.righe.length + (r.righe.length === 1 ? " riga aggiunta" : " righe aggiunte") + ": controllale e premi «Salva».", "o");
      return null;
    });
}
function righeDaTesto(testo, q, cols) {
  const linee = String(testo || "").replace(/\r/g, "").split("\n").filter(x => x.trim());
  if (!linee.length) return { errore: "Nessuna riga da aggiungere." };
  const sep = linee.some(x => x.includes("\t")) ? "\t" : ";";
  const nomi = cols.map(c => lbl(q.coll, c, q.id).toLowerCase());
  if (linee[0].split(sep).some(x => nomi.includes(x.trim().toLowerCase()))) linee.shift();   // intestazione
  const out = [];
  for (const [i, l] of linee.entries()) {
    const celle = l.split(sep);
    if (celle.length > cols.length) return { errore: "Riga " + (i + 1) + ": " + celle.length + " colonne, al massimo " + cols.length + "." };
    const campi = {};
    celle.forEach((t, j) => { const v = leggi(S.schema.collezioni[q.coll][cols[j]], t); if (v !== null) campi[cols[j]] = v; });
    if (Object.keys(campi).length) out.push(campi);
  }
  return out.length ? { righe: out } : { errore: "Nessuna riga con dati." };
}
/* Voce 10: appunti per riga (soggetto, bene, devoluzione...) e stato di lavorazione del quadro. Stanno nella sezione «note»:
   non fanno parte del dichiarato, non entrano nel file telematico e non rendono obsoleti controlli ed esportazioni. */
const STATI_LAVORO = { "": "stato: nessuno", da_completare: "da completare", da_controllare: "da controllare", completato: "completato" };
const noteP = () => (S.P && S.P.dati.note) || {};
function boxAppunti(q, r) {
  const k = q.coll + ":" + r.e.id, attuale = ((noteP().appunti || {})[k]) || "";
  const ta = h("textarea", { rows: 3, class: "appunti", "aria-label": "Appunti sulla riga" }); ta.value = attuale;
  const bt = h("button", { class: "gh", onclick: () => {
    const app = { ...(noteP().appunti || {}) }, v = ta.value.trim();
    if (v) app[k] = v; else delete app[k];
    salvaOps([{ op: "set", sezione: "note", campi: { appunti: Object.keys(app).length ? app : null } }]);
  } }, "Salva appunti");
  return h("details", { class: "gruppo-opzionale appunti-riga", open: !!attuale }, h("summary", {}, "Appunti" + (attuale ? " · presenti" : "")),
    h("p", { class: "mut" }, "Nota interna dello studio: non entra nella dichiarazione."), ta, bt);
}
function statoLavoro(qid) { return ((noteP().stato_quadri || {})[qid]) || ""; }
function selettoreStato(q) {
  const s = h("select", { class: "stato-lavoro", "aria-label": "Stato di lavorazione del quadro " + q.id, onchange: ev => {
    const st = { ...(noteP().stato_quadri || {}) }; if (ev.target.value) st[q.id] = ev.target.value; else delete st[q.id];
    salvaOps([{ op: "set", sezione: "note", campi: { stato_quadri: Object.keys(st).length ? st : null } }]);
  } }, Object.entries(STATI_LAVORO).map(([v, t]) => h("option", { value: v }, t)));
  s.value = statoLavoro(q.id);
  return s;
}
/* ---------- ispettore ---------- */
/* Schede (role=tab): una sola tappa Tab sulla scheda attiva, frecce sinistra/destra, Home e Fine per cambiare scheda. Il
   contenitore viene ridisegnato al cambio: dopo il clic il focus torna sulla scheda attiva del nuovo elenco (dove()). */
function schedeTastiera(lista, pannelloId, dove) {
  const schede = [...lista.querySelectorAll("[role=tab]")];
  for (const s of schede) { s.tabIndex = s.getAttribute("aria-selected") === "true" ? 0 : -1; s.setAttribute("aria-controls", pannelloId); }
  lista.addEventListener("keydown", ev => {
    const i = schede.indexOf(document.activeElement); if (i < 0) return;
    const n = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: schede.length - 1 }[ev.key]; if (n === undefined) return;
    ev.preventDefault(); schede[(n + schede.length) % schede.length].click();
    setTimeout(() => { const l = dove(); const s = l && l.querySelector("[role=tab][aria-selected=true]"); if (s) s.focus(); }, 0);
  });
}
function renderIns() {
  let ins = $("#ins"); ins.replaceChildren();
  if (!S.P) return;
  if (S.tab === 'file') { vaiFile(); return; } // compatibilita' con collegamenti precedenti
  if (S.sel === 'FILE') return;
  const nr = rilievi().length;
  const seg = h("div", { class: "seg", role: "tablist", "aria-label": "Schede del pannello" }, [["dati", "Dati"], ["controlli", "Controlli" + (nr ? " (" + nr + ")" : "")], ["cronologia", "Cronologia"]].map(([k, n]) =>
    h("button", { role: "tab", id: "insTab_" + k, "aria-selected": S.tab === k ? "true" : "false", onclick: () => { S.tab = k; render(); } }, n)));
  const pannello = h("div", { id: "insPannello", role: "tabpanel", "aria-labelledby": "insTab_" + S.tab });
  schedeTastiera(seg, "insPannello", () => $("#ins .seg"));
  ins.append(seg, pannello);
  ins = pannello;
  if (S.tab === "dati" && S.riga) ins.append(h("button", { class: "lk solo-mobile", onclick: tornaTabella }, "↑ Torna alla tabella"));
  if (S.tab === "dati") insDati(ins); else if (S.tab === "controlli") insControlli(ins); else if (S.tab === "file") insFile(ins); else insCronologia(ins);
}
const ESTERO_IMM = new Set(["codice_stato_estero", "stato_estero", "stato_federato", "localita_estero", "imposta_estera"]);   // etichette.py: _ESTERO_IMM
function rigaSelezionata() {
  const q = quadro(); if (!q || !q.coll || !S.riga) return null;
  return righeQuadro(q).find(r => r.key === S.riga) || null;
}
function insDati(ins) {
  const q = quadro(); const r = rigaSelezionata(), gen = S.gen;   // gen: un evento tardivo di un campo non scrive in un'altra pratica
  if (!q || !q.coll) { ins.append(h("p", { class: "mut" }, q && q.vista === "frontespizio" ? "I dati del frontespizio si modificano nelle schede al centro." : "Questo quadro non ha righe da modificare.")); return; }
  if (!r) { ins.append(h("p", { class: "mut" }, "Seleziona una riga della tabella oppure aggiungine una.")); return; }
  const campi = S.schema.collezioni[q.coll]; const id = r.e ? r.e.id : r.nuova.id;   // anche le righe nuove hanno data-path (per evidenziare l'errore al salvataggio)
  ins.append(h("div", { class: "ins-testa" }, h("h3", {}, r.nuova ? "Nuova riga" : etichetta(q.coll, r.e)),
    h("button", { class: "lk chiudi-ins", title: "Chiudi il pannello (Esc dalla tabella)", "aria-label": "Chiudi il pannello", onclick: chiudiPannello }, "Chiudi")));
  for (const x of rilievi().filter(x => id && x.percorso === q.coll + "[" + id + "]")) ins.append(h("div", { class: "e e-riga" }, x.messaggio));
  const visibili = q.campi ? new Set(q.campi) : (((S.schema.ordine || {})[q.id]) ? new Set(S.schema.ordine[q.id]) : null);   // solo i campi pertinenti al quadro; uno gia' valorizzato resta visibile
  const ordine = ordinati(q.id, Object.keys(campi));
  const gruppi = q.coll === "beni" ? GRUPPI_SCHEDA[q.id] : null, righeCampi = [];
  for (const [comune, provincia] of [['comune', 'provincia'], ['luogo_nascita', 'provincia_nascita']]) {
    void comune; void provincia;   // provincia e comune seguono gia' l'ordine ufficiale (provincia prima del comune)
  }
  // dati dell'immobile estero: solo con provincia EE (o se gia' compilati), come nelle istruzioni dei quadri EB ed EC
  const esteroNascosto = q.coll === "beni" && ["EB", "EC"].includes(q.id) && String(valRiga(r, "provincia") || "").trim().toUpperCase() !== "EE";
  let nascostiEstero = 0;
  for (const c of ordine) { const kind = campi[c];
    const vv = valRiga(r, c);
    const vuoto = vv === undefined || vv === null || vv === "";
    if (visibili && !visibili.has(c) && vuoto) continue;
    if (esteroNascosto && ESTERO_IMM.has(c) && vuoto) { nascostiEstero++; continue; }
    if (q.coll === "persone" && c === "relazione_con_defunto" && struttDi("persone", "grado_parentela")) {   // duplica il grado (menu): si nasconde se vuota o uguale
      const rel = String(vv || "").trim();
      if (!rel || rel === String(valRiga(r, "grado_parentela") || "").trim()) continue;
    }
    const tipoBene = q.coll === "beni" ? valRiga(r, "tipo")
      : q.coll === "devoluzioni" ? ((S.P.dati.beni || []).find(b => b.id === valRiga(r, "bene_id")) || {}).tipo : null;
    const sd = struttDi(q.coll, c, tipoBene);
    const modificaCampo = (campo, v) => {
      if (S.gen !== gen) return;
      const scrivi = (c2, x) => {
        if (r.nuova) r.nuova.campi[c2] = x;
        else {
          // valore uguale a quello salvato (anche l'evento «change» che arriva quando il pannello si ridisegna dopo «Salva»):
          // non e' una modifica, si toglie invece di lasciare «1 modifica non salvata»
          const salvato = (S.P.dati[q.coll] || []).find(e => e.id === id), d = S.dirty.get(r.key) || { coll: q.coll, id, campi: {} };
          if (salvato && uguale(salvato[c2] ?? null, x ?? null)) { delete d.campi[c2]; if (!Object.keys(d.campi).length) S.dirty.delete(r.key); }
          else { d.campi[c2] = x; S.dirty.set(r.key, d); }
        }
      };
      const gradoPrima = campo === "grado_parentela" ? String(valRiga(r, "grado_parentela") || "") : "";
      scrivi(campo, v);
      // il grado (menu dei codici) e la «relazione» dicono la stessa cosa e l'esportazione li confronta: la relazione resta una
      // nota interna allineata al grado (se vuota o uguale al grado precedente); il campo si vede solo se contiene altro
      if (q.coll === "persone" && campo === "grado_parentela") {
        const rel = String(valRiga(r, "relazione_con_defunto") || "").trim();
        if (!rel || rel === gradoPrima) scrivi("relazione_con_defunto", v || null);
      }
      aggiornaRigaVista(r.key); aggiornaBottoni(); renderSb();
      if ((q.coll === "beni" && (campo === "tipo" || campo === "provincia")) || (q.coll === "devoluzioni" && campo === "bene_id")) renderIns();   // cambiano i diritti o i campi esteri
      if (q.coll === "persone" && campo === "codice_fiscale")
        suggerisciDaCF(v, r.e ? r.e.ruolo : (r.nuova && r.nuova.campi.ruolo), c2 => valRiga(r, c2), scrivi, () => String(valRiga(r, "codice_fiscale") || "").trim().toUpperCase() === v.trim().toUpperCase()).then(res => {
          if (res.testo) msg(res.testo, res.riempiti.length ? "o" : "e");
          if (res.riempiti.length) { renderVista(); renderIns(); aggiornaBottoni(); renderSb(); }
        });
    };
    const w = sd && sd.opzioni ? campoStrutturato(sd, valRiga(r, c), v => modificaCampo(c, v), id ? q.coll + "[" + id + "]." + c : null)
      : campoInput(q.coll, id, c, kind, valRiga(r, c), modificaCampo);
    const aiuto = (S.schema.aiuti || {})[q.coll + "." + c];
    if (aiuto) w.append(h("div", { class: "mut aiuto-voce" }, aiuto));
    const obbl = (OBBLIGATORI[q.id] || []).includes(c);
    const rg = h("div", { class: "rg" + (obbl ? " obbl" : ""), "data-campo": c }, h("label", { title: obbl ? "Dato richiesto nel quadro " + q.id : null }, lbl(q.coll, c, q.id)), w);
    if (gruppi) righeCampi.push([c, rg, vuoto]); else ins.append(rg);
  }
  if (gruppi) ins.append(...schedaAGruppi(gruppi, righeCampi));
  if (nascostiEstero) ins.append(h("p", { class: "mut nota-campi" }, "Per un immobile all'estero scegli la provincia EE: compaiono i campi dello Stato estero."));
  renderStrutturati(ins, q, r);
  if (q.coll === "beni" && r.e && ["fabbricato", "terreno"].includes(valRiga(r, "tipo"))) ins.append(boxValoreCatastale(q, r));
  if (q.coll === "beni" && r.e) ins.append(boxDevoluzioniBene(r));            // voce 22: somma delle quote del bene
  if (q.coll === "persone" && r.e && valRiga(r, "ruolo") !== "defunto") ins.append(boxRiepilogoSoggetto(r));   // voce 33
  if (r.e) ins.append(boxAppunti(q, r));                                        // voce 10: nota interna della riga
  const az = h("div", { class: "az" }, h("button", { class: "pil", onclick: salvaTutto }, "Salva"));
  const supKey = q.coll + ':' + (r.e ? r.e.id : r.nuova.id);
  if (r.nuova || S.dirty.has(r.key) || S.supDirty.has(supKey)) az.append(h("button", { class: "gh", onclick: () => { r.nuova ? S.nuove.delete(r.key) : S.dirty.delete(r.key); S.supDirty.delete(supKey); if (r.nuova) S.riga = null; render(); } }, "Annulla modifiche"));
  if (r.e) az.append(h("button", { class: "lk pericolo", onclick: async () => {
    if (S.writeBusy) return msg("Salvataggio in corso: attendi prima di eliminare la riga.", "e");
    const nomeRiga = etichetta(q.coll, r.e), posRiga = righeQuadro(q).findIndex(x => x.key === r.key) + 1;
    const descr = nomeRiga && nomeRiga !== r.e.id ? "«" + nomeRiga + "»" : posRiga ? "n. " + posRiga : "selezionata";
    if (confirm("Eliminare la riga " + descr + " dal quadro " + q.id + (q.titolo ? " (" + q.titolo + ")" : "") + "?")) await salvaOps([{ op: "remove", coll: q.coll, id }], () => {
      S.dirty.delete(r.key); S.supDirty.delete(supKey); S.riga = null;
    });
  } }, "Elimina riga"));
  ins.append(az, h("p", { class: "mut mono id-riga" }, r.e ? r.e.id : ""));
}
function renderStrutturati(ins, q, r) {
  if (!['beni', 'passivita', 'persone', 'devoluzioni'].includes(q.coll)) return;
  const id = r.e ? r.e.id : r.nuova.id, key = q.coll + ':' + id;
  const base = (((S.P.dati.opzioni.telematico || {})[q.coll] || {})[id]) || {};
  const valore = c => S.supDirty.has(key) && c in S.supDirty.get(key).campi ? S.supDirty.get(key).campi[c] : base[c];
  const scrivi = (c, v) => {
    const d = S.supDirty.get(key) || { coll: q.coll, id, campi: {} };
    d.campi[c] = v; S.supDirty.set(key, d); aggiornaBottoni(); renderSb();
  };
  if (q.coll === 'devoluzioni') {
    const sd = (S.schema.strutturati || {})['devoluzioni.agevolazioni'];
    const bene = (S.P.dati.beni || []).find(b => b.id === valRiga(r, 'bene_id'));
    const attuale = String(valore('agevolazioni') || '').toUpperCase();
    ins.append(h('h3', {}, 'Agevolazione (prima casa, riduzioni)'));
    ins.append(campoStrutturato(sd, valore('agevolazioni'), v => { scrivi('agevolazioni', v); renderIns(); }, null));
    ins.append(h('div', { class: 'mut aiuto-voce' }, sd.aiuto));
    if (bene && ['P', 'X', 'Z'].includes(attuale) && quadroBene(bene) !== 'EC')
      ins.append(h('div', { class: 'nota stretta' }, 'Il bene collegato non è un fabbricato del quadro EC: i codici P, X, Z sono ammessi solo lì e l\'esportazione segnalerà un errore.'));
    const rd = (S.schema.strutturati || {})['devoluzioni.riduzioni'];
    ins.append(h('h3', {}, 'Riduzione art. 25 comma 1'));
    ins.append(campoStrutturato(rd, valore('riduzioni'), v => scrivi('riduzioni', v), null));
    ins.append(h('div', { class: 'mut aiuto-voce' }, rd.aiuto));
    if (valore('riduzioni') && bene)
      ins.append(h('div', { class: 'nota stretta' }, 'Indica anche il valore delle precedenti successioni nel pannello del bene collegato (' + etichetta('beni', bene) + ').'));
    return;
  }
  // dati meno frequenti del bene (precedenti successioni, graffati, trascrizione, registrazione): ripiegati finche' sono vuoti
  let altri = ins;
  if (q.coll === 'beni') {
    const pieno = ['valore_prec_succ', 'graffati', 'estremi_trascrizione', 'estremi_registrazione', 'immobili_aziendali']
      .some(c => { const v = valore(c); return v != null && v !== '' && !(Array.isArray(v) && !v.length); });
    altri = h('details', { class: 'altri', open: pieno || S.altriAperti ? '' : null, ontoggle: ev => { S.altriAperti = ev.target.open; } },
      h('summary', {}, 'Altri dati del bene'));
    const vp = (S.schema.strutturati || {})['beni.valore_prec_succ'];
    const inp = h('input', { id: 'vps_' + id, class: 'num', autocomplete: 'off', 'aria-label': vp.etichetta, value: mostra('importo', valore('valore_prec_succ')),
      oninput: ev => scrivi('valore_prec_succ', leggi('importo', ev.target.value)) });
    altri.append(h('h3', {}, 'Precedenti successioni o donazioni'), h('div', { class: 'rg' }, h('label', { for: 'vps_' + id }, vp.etichetta), h('div', {}, inp, h('div', { class: 'mut aiuto-voce' }, vp.aiuto))));
  }
  if (q.coll === 'persone') {
    const cb = h('input', { type: 'checkbox', 'aria-label': 'portatore handicap', onchange: ev => scrivi('portatore_handicap', ev.target.checked) });
    cb.checked = valore('portatore_handicap') === true;
    ins.append(h('label', { class: 'chk' }, cb, 'Portatore di handicap (come documentato)'));
    // dati meno frequenti del soggetto: ripiegati finche' sono vuoti
    const pienoP = ['rinuncia', 'denominazione', 'rinuncia_estremi', 'residenza_estera'].some(c => { const v = valore(c); return v != null && v !== '' && v !== false; });
    altri = h('details', { class: 'altri', open: pienoP || S.altriAperti ? '' : null, ontoggle: ev => { S.altriAperti = ev.target.open; } },
      h('summary', {}, 'Rinuncia, enti e residenza estera'));
    // rinunciatari, enti e residenza estera (docs/regole/soggetti_ea.md)
    const rin = h('input', { type: 'checkbox', 'aria-label': 'rinunciatario', onchange: ev => scrivi('rinuncia', ev.target.checked ? true : null) });
    rin.checked = valore('rinuncia') === true;
    altri.append(h('label', { class: 'chk' }, rin, 'Rinunciatario (la rinuncia e\' registrata: indica gli estremi dell\'atto)'));
    const den = h('input', { 'aria-label': 'denominazione', value: valore('denominazione') || '', oninput: ev => scrivi('denominazione', ev.target.value.trim() || null) });
    altri.append(h('label', {}, 'Denominazione (solo enti: gradi 35, 37, 38, 39)', den));
    const oggetto = (campo, titolo, campi) => {
      altri.append(h('h3', {}, titolo));
      for (const [c, et] of campi) {
        const el = h('input', { 'aria-label': titolo + ': ' + et, value: (valore(campo) || {})[c] ?? '', oninput: ev => {
          const o = { ...(valore(campo) || {}) }; const t = ev.target.value.trim(); if (!t) delete o[c]; else o[c] = t;
          scrivi(campo, Object.keys(o).length ? o : null); } });
        altri.append(h('label', {}, et, el));
      }
    };
    oggetto('rinuncia_estremi', 'Estremi dell\'atto di rinuncia', [['ufficio_registrazione', 'ufficio di registrazione'], ['serie', 'serie'],
      ['numero_registrazione', 'numero'], ['sottonumero_registrazione', 'sottonumero'], ['data_registrazione', 'data di registrazione (AAAA-MM-GG)']]);
    oggetto('residenza_estera', 'Residenza estera', [['codice_stato', 'codice Stato (3 caratteri)'], ['stato', 'Stato'], ['stato_federato', 'Stato federato'],
      ['localita', 'localita\''], ['indirizzo', 'indirizzo']]);
  }
  if (q.id === 'EB' || q.id === 'EL') {
    ins.append(h('h3', {}, 'Superficie'));
    for (const c of ['ettari', 'are', 'centiare']) {
      const el = h('input', { 'aria-label': 'superficie ' + c, value: (valore('superficie') || {})[c] ?? '',
        oninput: ev => { const s = { ...(valore('superficie') || {}) }; const t = ev.target.value.trim(); if (!t) delete s[c]; else s[c] = /^\d+$/.test(t) ? Number(t) : t; scrivi('superficie', Object.keys(s).length ? s : null); } });
      ins.append(h('label', {}, c, el));
    }
  }
  const tabella = (campo, titolo, campi, predefinito) => {
    const dest = q.coll === 'beni' ? altri : ins;
    dest.append(h('h3', {}, titolo));
    const righe = valore(campo) || [];
    righe.forEach((voce, i) => {
      const box = h('div', { class: 'grp sotto' });
      for (const [c, tipo] of campi) box.append(h('label', {}, lbl(q.coll, c), campoInput(q.coll, null, c, tipo, voce[c], (k, v) => {
        const nuove = structuredClone(valore(campo) || []); nuove[i][k] = v; scrivi(campo, nuove);
      })));
      box.append(h('button', { class: 'gh', onclick: () => { scrivi(campo, righe.filter((_, j) => j !== i)); renderIns(); } }, 'Rimuovi ' + titolo.toLowerCase()));
      dest.append(box);
    });
    dest.append(h('button', { class: 'gh', onclick: () => { scrivi(campo, [...righe, structuredClone(predefinito)]); if (q.coll === 'beni') S.altriAperti = true; renderIns(); } }, 'Aggiungi ' + titolo.toLowerCase()));
  };
  if (q.coll === 'passivita') tabella('ripartizione', 'Ripartizione', [['persona_id', 'ref:persone'], ['quota', 'quota']], { persona_id: '', quota: '1/1' });
  if (q.id === 'EN') tabella('immobili_aziendali', 'Immobile aziendale', [['bene_id', 'ref:beni']], { bene_id: '' });
  if (q.id === 'EC') tabella('graffati', 'Immobile graffato', [['sezione', 'str'], ['foglio', 'str'], ['particella', 'str'], ['subalterno', 'str']], {});
  if (q.id === 'EB' || q.id === 'EC') {
    tabella('estremi_trascrizione', 'Trascrizione', [['ufficio', 'str'], ['registro_particolare', 'str'], ['anno', 'str']], {});
    tabella('estremi_registrazione', 'Registrazione', [['ufficio', 'str'], ['anno', 'str'], ['volume', 'str'], ['numero', 'str']], {});
  }
  if (altri !== ins) ins.append(altri);
}
function insControlli(ins) {
  const q = S.Q;
  ins.append(h("p", { class: "mut" }, q.ambito + (q.finalizzabile ? ". Finalizzabile." : ". Non finalizzabile.")));
  for (const b of (q.blocchi_finalizzazione || [])) ins.append(h("div", { class: "nota stretta" }, b.messaggio));
  // avvisi che non impediscono la finalizzazione (es. visure catastali vecchie o senza data)
  // ogni rilievo e avviso con il rimedio: dove intervenire e con quale comando (docs/ANALISI_REPLICA_2026-11-07.md, voce 19)
  const rimedio = x => x.rimedio ? h("div", { class: "rimedio" }, h("b", {}, "Come risolvere: "), x.rimedio) : null;
  for (const a of (q.avvisi || [])) ins.append(h("div", { class: "nota stretta", role: "status" }, h("b", {}, "Avviso: "), a.messaggio, rimedio(a),
    a.quadro && a.percorso ? h("button", { class: "lk", onclick: () => vaiA(a) }, "Vai al dato") : null));
  if (!q.rilievi.length) { ins.append(h("p", { class: "ok esito-ok" }, "Nessun rilievo sui dati inseriti.")); return; }
  const ul = h("ul", { class: "rl" });
  for (const r of q.rilievi) ul.append(h("li", {}, h("button", { onclick: () => vaiA(r) }, h("span", { class: "sigla" }, r.quadro), h("span", {}, h("div", {}, r.messaggio), rimedio(r), h("div", { class: "cod" }, r.codice + " · " + r.percorso)))));
  ins.append(ul);
}
async function insCronologia(ins) {
  ins.append(h("p", { class: "mut" }, "Ogni salvataggio crea una revisione. Il ripristino non cancella la cronologia."));
  let lista;
  try { lista = await api("/api/pratiche/" + S.P.pratica_id + "/revisioni"); }
  catch (e) { if (S.tab === "cronologia") { ins.append(h("p", { class: "err" }, e.message)); msg(e.message, "e"); } return; }
  if (S.tab !== "cronologia") return;
  for (const x of lista.slice().reverse()) {
    const b = x.n !== S.P.revisione ? h("button", { class: "gh spazio-su", onclick: async () => {
      if (S.writeBusy || nMod()) return msg("Completa il salvataggio delle modifiche prima di ripristinare una revisione.", "e");
      if (!confirm("Creare una nuova revisione con i dati della n. " + x.n + "?")) return;
      S.writeBusy = true; aggiornaBottoni();
      try { await post("/api/pratiche/" + S.P.pratica_id + "/ripristina", { revisione_attesa: S.P.revisione, a_revisione: x.n }); await ricarica(); render(); msg("Dati della revisione " + x.n + " ripristinati in una nuova revisione.", "o"); } catch (e) { msg(e.message, "e"); }
      finally { S.writeBusy = false; aggiornaBottoni(); } } }, "Ripristina") : null;
    ins.append(h("div", { class: "rv" }, h("b", {}, "Revisione " + x.n), " · " + x.canale + " · " + x.autore, h("div", { class: "mut" }, x.ts), h("div", {}, x.sommario), b));
  }
}
const PILLOLE = { aggiornato: "ok", valido: "ok", positivo: "ok", senza_rilievi: "ok", negativo: "er", non_valido: "er", con_rilievi: "am", obsoleto: "am", non_eseguito: "", non_preparata: "" };
function riga_stato(nome, stato, extra) {
  return h("div", { class: "rg rg-stato" }, h("span", { class: "etichetta" }, nome), h("div", {}, h("span", { class: "pz " + (PILLOLE[stato] || "") }, String(stato).replaceAll("_", " ")), extra ? h("div", { class: "mut stato-extra" }, extra) : null));
}
async function insFile(dest) {
  const pid = S.P.pratica_id;
  const griglia = h('div', { class: 'file-griglia', id: 'fileContenuto' }); dest.append(griglia);
  let st;
  try { st = await api('/api/pratiche/' + pid + '/elaborati'); }
  catch (e) { if (griglia.isConnected) griglia.append(h('p', { class: 'err' }, e.message)); return; }
  if (S.sel !== 'FILE' || S.P.pratica_id !== pid || !griglia.isConnected) return;
  const ex = st.export, ct = st.controllo_ufficiale;
  // I passi sono una sequenza reale: fornitore, file, controllo ufficiale, stampa, invio. Ogni passo dice se e' fatto.
  const passo = (n, titolo, fatto, attrs) => h('section', { class: 'grp passo', ...(attrs || {}) },
    h('h2', {}, h('span', { class: 'n' + (fatto ? ' fatto' : ''), 'aria-hidden': 'true' }, fatto ? '✓' : String(n)),
      h('span', {}, h('span', { class: 'vh' }, 'Passo ' + n + ': '), titolo, fatto ? h('span', { class: 'vh' }, ' (fatto)') : null)));
  const fileOk = ex.generato && ex.completo && ex.stato === 'aggiornato';
  const stato = h('section', { class: 'grp riepilogo' }, h('h2', {}, 'Stato della dichiarazione'));
  stato.append(riga_stato('Dati', st.dati.stato, st.dati.rilievi + (st.dati.rilievi === 1 ? ' rilievo' : ' rilievi')),
    riga_stato('File XML', ex.stato, ex.generato ? (ex.completo ? 'Completo nel perimetro supportato' : 'Bozza tecnica: non trasmissibile') : 'Nessun file generato'),
    riga_stato('Struttura del file', st.xsd.stato), riga_stato('Controllo ufficiale', ct.stato, ct.versione_controllo),
    riga_stato('Trasmissione', st.trasmissione.stato, st.trasmissione.nota));
  if (ex.versioni) stato.append(h('p', { class: 'mut piccolo' }, 'Versioni del file: programma ' + ex.versioni.applicazione + ', regole ' + ex.versioni.regole +
    ', specifiche ' + ex.versioni.specifiche_suc + (ct.versione_controllo ? ', controllo ' + ct.versione_controllo : '') + '.'));
  const profiloSalvato = (S.P.dati.opzioni.fornitore || {}).cf;
  const fornitore = passo(1, 'Fornitore e impegno alla trasmissione', !!profiloSalvato, { id: 'fornitore' });
  fornitore.append(
    h('p', { class: 'mut' }, 'Chi presenta il file: dichiarante o intermediario. Il profilo si compila una volta per questa pratica.'));
  const profilo = { ...(S.P.dati.opzioni.fornitore || {}), ...S.fornitoreDirty };
  const modifica = (k, valore) => { S.fornitoreDirty[k] = valore; aggiornaBottoni(); renderSb(); };
  const cfIn = h('input', { 'aria-label': 'Codice fiscale del fornitore', class: 'mono cf', value: profilo.cf || '',
    oninput: e => modifica('cf', e.target.value.trim().toUpperCase()) });
  const tipoIn = h('select', { 'aria-label': 'Tipo fornitore' }, h('option', { value: '1' }, 'Dichiarante (1)'), h('option', { value: '10' }, 'Intermediario (10)'));
  tipoIn.value = profilo.tipo || '1';
  const impegnoIn = h('select', { 'aria-label': 'Impegno a trasmettere' }, h('option', { value: '' }, 'Non indicato'),
    h('option', { value: '1' }, 'Predisposta dal dichiarante (1)'), h('option', { value: '2' }, 'Predisposta dall’intermediario (2)'));
  impegnoIn.value = profilo.impegno_codice || '';
  const dataIn = h('input', { 'aria-label': 'Data impegno', placeholder: 'GG/MM/AAAA', value: dataIt(profilo.data_impegno || '') });
  const dettagli = h('div', {}, h('label', {}, 'Impegno a trasmettere', impegnoIn), h('label', {}, 'Data impegno', dataIn));
  dettagli.hidden = tipoIn.value !== '10';
  tipoIn.addEventListener('change', () => { modifica('tipo', tipoIn.value); dettagli.hidden = tipoIn.value !== '10'; });
  impegnoIn.addEventListener('change', () => modifica('impegno_codice', impegnoIn.value || null));
  dataIn.addEventListener('input', () => modifica('data_impegno', dataIso(dataIn.value) || null));
  fornitore.append(h('label', {}, 'Codice fiscale del fornitore', cfIn), h('label', {}, 'Tipo fornitore', tipoIn), dettagli,
    h('div', { class: 'az' }, h('button', { class: 'gh', onclick: salvaTutto }, 'Salva profilo'),
      STUDIO.profilo && STUDIO.profilo.cf ? h('button', { class: 'gh', type: 'button', onclick: () => {
        for (const [k, v] of Object.entries(STUDIO.profilo)) modifica(k, v);
        cfIn.value = STUDIO.profilo.cf || ''; tipoIn.value = STUDIO.profilo.tipo || tipoIn.value; impegnoIn.value = STUDIO.profilo.impegno_codice || '';
        dettagli.hidden = tipoIn.value !== '10'; msg('Profilo dello studio applicato: premi «Salva profilo» per confermarlo sulla pratica.', 'o');
      } }, 'Applica profilo dello studio') : null));
  const elaborati = passo(2, 'Genera il file telematico', fileOk);
  const esegui = scopo => occupato('esporta', async () => {
    if (S.writeBusy) return;
    try {
      if (nMod() && !(await salvaTutto())) return;
      const r = await post('/api/pratiche/' + pid + '/esporta', { scopo });
      const motivi = [...(r.quadri_mancanti || []), ...(r.non_supportato || []), ...(r.errori || [])].map(motivoLeggibile);
      if (!r.generato) msg('File non generato: ' + motivi.slice(0, 3).join(' | ') + '. Nessun file parziale è stato prodotto.', 'e');
      else msg((r.completo ? 'File generato e valido per lo schema.' : 'Bozza tecnica generata. ' + r.avvertenza)
        + ((r.avvisi || []).length ? ' Avvertenze: ' + r.avvisi.map(a => a.messaggio).join(' | ') : ''), r.completo ? 'o' : 'e');
      if (r.backup && r.backup.errore) msg('Attenzione: backup automatico non riuscito (' + r.backup.errore + ')', 'e');
      else if (r.backup && r.backup.eseguito) STUDIO.ultimoBackup = r.backup.nome;
      if (S.P && S.P.pratica_id === pid) { await ricarica(); render(); }
    } catch (e) { msg(e.message, 'e'); }
  });
  elaborati.append(h('p', { class: 'mut' }, 'Genera il file quando i dati sono pronti. La bozza tecnica conserva evidenza dei limiti e non è trasmissibile.'),
    h('div', { class: 'az' }, h('button', { class: 'pil', disabled: OCCUPATI.has('esporta'), onclick: esegui('completo') }, 'Genera file'),
      h('button', { class: 'gh', disabled: OCCUPATI.has('esporta'), onclick: esegui('bozza_tecnica') }, 'Genera bozza tecnica')));
  if (ex.generato) elaborati.append(h('div', { class: 'az' },
    h('a', { class: 'gh', href: '/api/pratiche/' + pid + '/file.xml?job=' + ex.job_id, download: '' }, 'Scarica XML')));
  const controllo = passo(3, 'Controllo ufficiale', ct.stato === 'positivo');
  controllo.append(h('p', { class: 'mut' }, 'Esegue sul file il componente di controllo SUC dell\'Agenzia installato su questo computer.'));
  if (ct.azione_richiesta) controllo.append(h('p', { class: 'nota pre' }, ct.azione_richiesta));
  controllo.append(h('div', { class: 'az' }, h('button', { class: 'pil', disabled: ex.stato !== 'aggiornato' || !ex.generato || OCCUPATI.has('controllo'), onclick: occupato('controllo', async () => {
    if (nMod()) return msg('Salva le modifiche e rigenera il file prima del controllo.', 'e');
    try { const r = await post('/api/pratiche/' + pid + '/controllo-ufficiale', {}); msg('Controllo ufficiale: ' + String(r.stato_controllo).replaceAll('_', ' ') + ' (' + r.esito + ').', r.stato_controllo === 'positivo' ? 'o' : 'e'); }
    catch (e) { msg(e.message, 'e'); }
    if (S.P && S.P.pratica_id === pid && S.sel === 'FILE') renderVista();
  }) }, 'Esegui controllo ufficiale'),
    ct.stato === 'positivo' && ct.job_adattatore ? h('a', { class: 'gh', href: '/api/pratiche/' + pid + '/file.dcm', download: '' }, 'Scarica file controllato (.dcm)') : null));
  // passaggio manuale: l'utente ha eseguito il controllo con il programma dell'Agenzia e carica qui gli esiti (revisione 2)
  if (ct.stato_job === 'attesa_diagnostico') {
    const fDgn = h('input', { type: 'file', accept: '.dgn', 'aria-label': 'File .dgn' }), fLog = h('input', { type: 'file', accept: '.xml', 'aria-label': 'File _logSchema.xml' });
    const fWri = h('input', { type: 'file', accept: '.wri', 'aria-label': 'File .wri (facoltativo)' }), conf = h('input', { type: 'checkbox', id: 'dgn_conf' });
    controllo.append(h('div', { class: 'sotto' }, h('h3', {}, 'Carica l’esito del controllo eseguito a mano'),
      h('label', {}, 'Diagnostico (.dgn)', fDgn), h('label', {}, 'Esito dello schema (_logSchema.xml)', fLog), h('label', {}, 'Avvisi (.wri, facoltativo)', fWri),
      h('label', { class: 'chk', for: 'dgn_conf' }, conf, h('span', {}, 'Confermo che questi esiti riguardano il file di questa pratica')),
      h('div', { class: 'az' }, h('button', { class: 'gh', disabled: OCCUPATI.has('diagnostico'), onclick: occupato('diagnostico', async () => {
        if (!fDgn.files[0] || !fLog.files[0]) return msg('Scegli il file .dgn e il file _logSchema.xml prodotti dal controllo.', 'e');
        const fd = new FormData(); fd.append('dgn', fDgn.files[0]); fd.append('log_schema', fLog.files[0]);
        if (fWri.files[0]) fd.append('wri', fWri.files[0]); if (conf.checked) fd.append('conferma_associazione', '1');
        try { const r = await api('/api/pratiche/' + pid + '/controllo-ufficiale/diagnostico', { method: 'POST', body: fd });
          msg('Esito registrato: controllo ' + String(r.stato).replaceAll('_', ' ') + '.', r.stato === 'positivo' ? 'o' : 'e'); }
        catch (e) { msg(e.message, 'e'); }
        if (S.P && S.P.pratica_id === pid && S.sel === 'FILE') renderVista();
      }) }, 'Registra esito'))));
  }
  const stampa = passo(4, 'Stampa e rileggi', (st.stampa_modello || {}).stato === 'aggiornata');
  stampa.append(h('p', { class: 'mut' }, 'Rileggi il modello stampato prima di inviare: confronta immobili, eredi, quote e imposte con i documenti.'),
    h('div', { class: 'az' }, h('button', { class: 'gh', disabled: !fileOk || OCCUPATI.has('stampa'), onclick: occupato('stampa', async () => {
      if (nMod()) return msg('Salva le modifiche e rigenera il file prima della stampa.', 'e');
      try { const r = await post('/api/pratiche/' + pid + '/stampa-modello', {}); msg('Modello ministeriale generato (' + r.pagine + ' pagine). Prova locale: controllane il contenuto prima di usarlo.', 'o'); window.open('/api/pratiche/' + pid + '/stampa-modello.pdf', '_blank', 'noopener'); }
      catch (e) { msg(e.message, 'e'); }
    }) }, 'Stampa modello ministeriale'),
      ex.generato ? h('a', { class: 'gh', href: '/api/pratiche/' + pid + '/prospetto-cliente', target: '_blank', rel: 'noopener',
        title: 'Riepilogo per gli eredi: beni, quote, passività e imposte, con gli stessi importi del file' }, 'Prospetto per il cliente') : null,
      ex.generato ? h('a', { class: 'gh', href: '/api/pratiche/' + pid + '/stampa?job=' + ex.job_id, target: '_blank', rel: 'noopener' }, 'Prospetto tecnico del file') : null));
  const invio = passo(5, 'Invio e ricevute', st.trasmissione.stato === 'trasmessa' && st.trasmissione.modalita !== 'simulata', { id: 'invioPratica' });
  griglia.append(stato, fornitore, elaborati, controllo, stampa, invio);
  await renderInvio(invio, ex, ct);
}
/* Profilo e importi della copia congelata in parole, non in JSON (revisione 2, punto 6). */
function descriviFornitore(p) {
  p = p || {};
  if (!p.cf) return "non indicato";
  const tipo = { "1": "dichiarante", "10": "intermediario" }[String(p.tipo || "")];
  const impegno = { "1": "predisposta dal dichiarante", "2": "predisposta dall'intermediario" }[String(p.impegno_codice || "")];
  return p.cf + (tipo ? " (" + tipo + ")" : "") + (impegno ? ", " + impegno : "") + (p.data_impegno ? ", impegno del " + dataIt(p.data_impegno) : "");
}
function descriviImporti(m) {
  const voci = Object.entries(m || {});
  if (!voci.length) return "nessuno";
  return voci.map(([k, v]) => k.replaceAll("_", " ") + " € " + importoIt(String(v), true)).join(", ");
}
/* Invio: copia congelata -> conferma -> trasmissione. La modalita' «prova» usa un servizio FITTIZIO locale: non invia nulla all'Agenzia. */
async function renderInvio(ins, ex, ct) {
  const pid = S.P.pratica_id; const base = "/api/pratiche/" + pid + "/invio";
  ins.append(h("div", { class: "nota stretta" }, "PROVA SIMULATA: il programma non trasmette nulla all'Agenzia delle Entrate. L'invio reale si esegue con gli strumenti ufficiali (modalità manuale) e si registra qui."));
  let copie = [], sti = {};
  try { sti = await api(base); copie = sti.copie || []; } catch (e) { ins.append(h("p", { class: "err" }, e.message)); return; }
  // invio in corso / da riconciliare o gia' trasmesso: nessuna nuova copia finche' l'esito non e' registrato (review 3)
  const bloccoPrep = sti.copia_attiva ? (sti.tentativo_aperto
    ? "C'è un invio in corso o da riconciliare: registra prima l'esito (protocollo, .esi o invio non avvenuto)."
    : "La dichiarazione risulta già trasmessa: non si prepara un'altra copia.") : "";
  const ricarica = () => { if (S.sel === "FILE") renderVista(); };
  // ogni azione e' «occupata» finche' la richiesta non finisce: un secondo clic non parte (revisione 2, punto 2)
  const chiama = (nome, url, corpo, ok) => occupato(nome, async () => { try { const r = await post(url, corpo); msg(ok(r), "o"); } catch (e) { msg(e.message, "e"); } ricarica(); });
  // stessa chiave finche' non cambiano revisione, file generato e controllo: ripetere «Prepara invio» restituisce la stessa copia
  const chiavePrep = ["prep", pid, "r" + S.P.revisione, ex.job_id || "", (ct || {}).job_adattatore || (ct || {}).stato || ""].join("-");
  ins.append(h("div", { class: "az" }, h("button", { class: "pil", disabled: ex.stato !== "aggiornato" || !ex.completo || !!bloccoPrep || OCCUPATI.has("prepara"), title: bloccoPrep || "Congela il file XML completo con il controllo ufficiale associato",
    onclick: chiama("prepara", base + "/prepara", { chiave_richiesta: chiavePrep }, r => "Copia preparata. " + (r.azione_richiesta || "")) }, "Prepara invio")));
  if (bloccoPrep) ins.append(h("div", { class: "nota stretta" }, bloccoPrep));
  // la copia mostrata e' quella con il tentativo aperto o trasmessa, non la piu' recente: il tentativo non sparisce mai
  const c = copie.find(x => x.job_id === sti.copia_attiva) || copie[0];
  if (!c) { ins.append(h("p", { class: "mut testo-m" }, "Nessuna copia preparata. Serve un file completo e un controllo ufficiale positivo.")); return; }
  const altre = (sti.elenco_copie || []).filter(x => x.copia_id !== c.job_id);
  if (altre.length) ins.append(h("details", {}, h("summary", {}, "Altre copie della pratica (" + altre.length + ")"),
    ...altre.map(x => h("div", { class: "mut testo-m" }, "Copia " + x.copia_id + " · rev. " + (x.revisione ?? "–") + " · " + String(x.stato).replaceAll("_", " ")
      + (x.stato_tentativo ? " · tentativo " + String(x.stato_tentativo).replaceAll("_", " ") : "") + (x.protocollo ? " · protocollo " + x.protocollo : "")))));
  const d = c.dettaglio || {};
  ins.append(h("a", { href: "/api/invio/" + c.job_id + "/file", download: "" }, "Scarica la copia congelata"));
  ins.append(h("p", { class: "mut" }, "Fornitore: " + descriviFornitore(d.profilo) + " · Importi: " + descriviImporti(d.importi)));
  const tentativo = (c.tentativi || []).find(t => t.dettaglio.job_id === d.tentativo_corrente);
  if (tentativo) {
    ins.append(riga_stato("Tentativo", tentativo.dettaglio.stato, tentativo.dettaglio.modalita + (tentativo.dettaglio.protocollo ? " · " + tentativo.dettaglio.protocollo : "")));
    if (tentativo.azione_richiesta) ins.append(h("div", { class: "nota pre" }, tentativo.azione_richiesta));
  }
  ins.append(riga_stato("Copia", c.stato, (d.manifest || []).map(m => m.nome + " · " + m.sha256.slice(0, 12)).join(", ")));
  if (c.azione_richiesta) ins.append(h("div", { class: "nota stretta pre" }, c.azione_richiesta));
  if (c.stato === "preparata") {
    const sp = h("input", { type: "checkbox", id: "inv_ok" });
    const bt = h("button", { class: "pil", disabled: true, onclick: chiama("conferma", "/api/invio/" + c.job_id + "/conferma", { impronta: d.impronta_conferma, utente: "professionista" }, () => "Copia confermata.") }, "Conferma questa copia");
    sp.addEventListener("change", () => { bt.disabled = !sp.checked; });
    ins.append(h("label", { class: "chk", for: "inv_ok" }, sp, h("span", {}, "Ho verificato il file (impronta " + (d.impronta_conferma || "").slice(0, 12) + "…), il fornitore e il controllo ufficiale")), h("div", { class: "az" }, bt));
  }
  if (c.stato === "confermata") {
    ins.append(h("div", { class: "az" },
      h("button", { class: "pil", disabled: OCCUPATI.has("trasmetti"), onclick: chiama("trasmetti", "/api/invio/" + c.job_id + "/trasmetti", { chiave_richiesta: "t-" + crypto.randomUUID(), modalita: "simulata" }, r => (r.avvertenza || "") + " Esito: " + String(r.stato).replaceAll("_", " ")) }, "Invia in PROVA (simulata)"),
      h("button", { class: "gh", disabled: OCCUPATI.has("trasmetti"), onclick: chiama("trasmetti", "/api/invio/" + c.job_id + "/trasmetti", { chiave_richiesta: "t-" + crypto.randomUUID(), modalita: "manuale" }, r => r.avvertenza) }, "Istruzioni per l'invio reale")));
  }
  if (tentativo && ["esito_incerto", "in_trasmissione", "attesa_invio_manuale"].includes(tentativo.dettaglio.stato)) {
    const url = "/api/invio/tentativi/" + d.tentativo_corrente + "/riconcilia";
    if (tentativo.dettaglio.modalita === "simulata")
      ins.append(h("button", { onclick: chiama("riconcilia", url, {}, r => "Riconciliazione: " + r.stato) }, "Riconcilia (prova)"));
    else {
      const protocollo = h("input", { "aria-label": "Protocollo dell'invio", placeholder: "Protocollo assegnato" });
      const fonte = h("input", { "aria-label": "Evidenza verificata", placeholder: "Dove hai verificato l'esito" });
      const registra = nonInviato => {
        if (!fonte.value.trim() || (!nonInviato && !protocollo.value.trim())) return msg("Indica il protocollo e dove hai verificato l'esito; per un invio non avvenuto indica l'evidenza.", "e");
        const evidenze = { verificato_su: fonte.value.trim(), ...(nonInviato ? { non_trasmesso: true } : { protocollo: protocollo.value.trim() }) };
        return chiama("riconcilia", url, { evidenze }, r => "Esito registrato: " + r.stato)();
      };
      // file .esi di Entratel-Multifile / Desktop Telematico: abbinato per nome del file e data, mai per ordine d'arrivo
      const esi = h("input", { type: "file", accept: ".esi,.json,.txt", "aria-label": "File .esi dell'invio" });
      const registraEsi = async () => {
        const f = esi.files && esi.files[0];
        if (!f) return msg("Scegli il file .esi prodotto dall'invio.", "e");
        if (f.size > 2000000) return msg("File .esi troppo grande.", "e");
        const testo = await f.text();
        return chiama("riconcilia", url, { evidenze: { esi: testo } }, r => "Esito dal file .esi: " + String(r.stato).replaceAll("_", " ")
          + (r.dettaglio && r.dettaglio.protocollo ? " · protocollo " + r.dettaglio.protocollo : "") + (r.azione_richiesta && r.stato !== "trasmesso" ? " — " + r.azione_richiesta : ""))();
      };
      ins.append(protocollo, fonte, h("div", { class: "az" },
        h("button", { onclick: () => registra(false) }, "Registra protocollo"),
        h("button", { onclick: () => { if (confirm("Hai verificato che questo invio non è avvenuto?")) registra(true); } }, "Registra invio non avvenuto")),
        h("div", { class: "az" }, esi, h("button", { class: "gh", disabled: OCCUPATI.has("riconcilia"), onclick: registraEsi }, "Registra file .esi")));
    }
  }
  // le prove simulate sono separate: non consumano la copia confermata (revisione 2)
  for (const p of c.prove || []) {
    const pd = p.dettaglio || p;
    ins.append(riga_stato("PROVA simulata", pd.stato, (pd.protocollo ? "protocollo fittizio " + pd.protocollo : "") + " · non è un invio all'Agenzia"));
    if (["esito_incerto", "in_trasmissione"].includes(pd.stato)) ins.append(h("button", { class: "gh", onclick: chiama("riconcilia", "/api/invio/tentativi/" + pd.job_id + "/riconcilia", {}, r => "Riconciliazione della prova: " + r.stato) }, "Riconcilia (prova)"));
  }
  if (tentativo && tentativo.dettaglio.protocollo) await renderRicevute(ins, pid, tentativo.dettaglio.job_id);
  for (const tid of d.tentativi || []) ins.append(h("div", { class: "mut testo-m" }, "Tentativo " + tid + (tid === d.tentativo_corrente ? " (corrente)" : "")));
}
async function renderRicevute(ins, pid, tid) {
  const url = '/api/pratiche/' + pid + '/ricevute/' + tid;
  const stato = await api(url);
  ins.append(h('h3', {}, 'Ricevute ed esiti successivi'));
  for (const k of ['registrazione', 'pagamento', 'volture', 'copia_semplice', 'attestazione']) ins.append(riga_stato(k, stato[k]));
  const tipi = S.schema.tipi_ricevuta;
  const tipo = h('select', { 'aria-label': 'Tipo di ricevuta' }, Object.keys(tipi).map(k => h('option', { value: k }, k.replaceAll('_', ' '))));
  const esito = h('select', { 'aria-label': 'Esito della ricevuta' });
  const aggiorna = () => esito.replaceChildren(h('option', { value: '' }, '(senza esito)'), ...tipi[tipo.value].esiti.map(k => h('option', { value: k }, k)));
  tipo.addEventListener('change', aggiorna); aggiorna();
  const file = h('input', { type: 'file', 'aria-label': 'Documento ricevuto' });
  ins.append(tipo, esito, file, h('button', { disabled: OCCUPATI.has('ricevuta'), onclick: occupato('ricevuta', async () => {
    const f = file.files[0]; if (!f) return msg('Scegli il documento ricevuto.', 'e');
    try {
      await api(url + '?' + new URLSearchParams({ tipo: tipo.value, esito: esito.value, nome: f.name }), { method: 'POST', body: await f.arrayBuffer() });
      msg('Ricevuta originale acquisita e associata al protocollo.', 'o'); renderVista();
    } catch (e) { msg(e.message, 'e'); }
  }) }, 'Acquisisci ricevuta'));
  for (const doc of stato.documenti) ins.append(h('p', { class: 'mut' }, h('a', { href: url + '/file/' + doc.job_id, download: '' }, doc.nome), ' · ' + doc.tipo + ' · ' + (doc.esito || '') + ' · SHA-256 ' + doc.sha256));
}
function vaiA(r) {
  S.sel = r.quadro;
  const m = r.percorso.match(/^([a-z_]+)\[([^\]]+)\]/);
  const q = quadro();
  S.riga = m && q && q.coll === m[1] ? "e:" + m[1] + ":" + m[2] : null;
  S.tab = "dati"; render();
  const el = document.querySelector('[data-path="' + CSS.escape(r.percorso) + '"]');
  if (el) { el.scrollIntoView({ block: "center" }); el.focus(); }
}

/* ---------- frontespizio ---------- */
const persona = ruolo => (S.P.dati.persone || []).find(p => p.ruolo === ruolo);
function schedaPersona(titolo, ruolo, vis) {
  const dichiarazione = ((S.P.dati.opzioni.telematico || {}).dichiarazione || {});
  const ref = S.dichDirty.has('presentatore.persona_id') ? S.dichDirty.get('presentatore.persona_id') : (dichiarazione.presentatore || {}).persona_id;
  const e = (ruolo === 'presentatore' && ref ? S.P.dati.persone.find(p => p.id === ref) : null) || persona(ruolo);
  const key = e ? 'e:persone:' + e.id : "f:" + ruolo; const campi = S.schema.collezioni.persone;
  const g = h("section", { class: "grp" }, h("h2", {}, titolo));
  const griglia = h('div', { class: 'persona-campi' }); g.append(griglia);
  for (const c of ordinati(ruolo === 'presentatore' ? 'AN.presentatore' : 'AN', vis)) {
    const cur = S.dirty.has(key) && c in S.dirty.get(key).campi ? S.dirty.get(key).campi[c] : (e ? e[c] : undefined);
    griglia.append(h("div", { class: "rg", 'data-campo': c }, h("label", {}, lbl("persone", c)), campoInput("persone", e && e.id, c, campi[c], cur, (campo, v) => {
      const scrivi = (c2, x) => { const d = S.dirty.get(key) || { coll: "persone", id: e ? e.id : null, campi: e ? {} : { ruolo } }; d.campi[c2] = x; S.dirty.set(key, d); };
      scrivi(campo, v); aggiornaBottoni(); renderSb();
      if (campo === "codice_fiscale")
        suggerisciDaCF(v, ruolo, c2 => { const dd = S.dirty.get(key); return dd && c2 in dd.campi ? dd.campi[c2] : (e ? e[c2] : undefined); }, scrivi, () => { const dd = S.dirty.get(key); return !!dd && String(dd.campi.codice_fiscale || "").trim().toUpperCase() === String(v || "").trim().toUpperCase(); }).then(res => {
          if (res.testo) msg(res.testo, res.riempiti.length ? "o" : "e");
          if (res.riempiti.length) { aggiornaBottoni(); renderSb(); render(); }
        });
    })));
  }
  return g;
}
/* Dati della dichiarazione: opzioni.telematico.dichiarazione. I codici ufficiali sono proposti come menu (server: codici.py, dagli XSD). */
const CAMPI_DICH = [   // [chiave, etichetta, tipo]: "bool" = si'/no (valore booleano nel modello), altrimenti testo
  ["stato_civile", "stato civile"], ["devoluzione_per_legge", "devoluzione per legge", "bool"], ["firma_dichiarante", "firma del dichiarante", "bool"],
  ["tempistica_pagamento", "tempistica del pagamento"], ["pagamento_rateale", "numero di rate trimestrali (1-12)"], ["acconto", "acconto dell'imposta di successione (euro, almeno il 20%)"],
  ["codice_sostitutiva", "tipo di sostitutiva (codice)"], ["prima_anno", "prima dichiarazione: anno"], ["prima_volume", "prima dichiarazione: volume"],
  ["prima_numero", "prima dichiarazione: numero"], ["ipotecaria_versata", "imposta ipotecaria già versata (EF6)"],
  ["catastale_versata", "imposta catastale già versata (EF12)"], ["successione_versata", "imposta di successione già versata (EF18bis col. 3)"], ["circoscrizioni_nuove", "circoscrizioni delle nuove trascrizioni (solo codice 1)"],
  ["dichiara_copie_conformi", "dichiarazione di conformità delle copie allegate", "bool"],
  ["flag_inventari", "inventari allegati tra gli altri documenti (EG8) come copie degli originali", "bool"],
  ["azienda_data_deposito", "azienda: data di deposito"],
  ["azienda_camera_commercio", "azienda: camera di commercio"],
  ["presentatore.persona_id", "Presentatore tra i soggetti della pratica"], ["presentatore.codice_carica", "presentatore: codice carica"],
  ["presentatore.telefono", "presentatore: telefono"], ["presentatore.email", "presentatore: email"],
  ["presentatore.data_decorrenza", "presentatore: decorrenza del termine di presentazione"], ["presentatore.rappresentato_cf", "presentatore: codice fiscale del rappresentato (cariche 3 e 4)"],
  ["presentatore.residente_estero.codice_stato", "presentatore residente all'estero: codice Stato"], ["presentatore.residente_estero.stato", "presentatore residente all'estero: Stato"],
  ["presentatore.residente_estero.stato_federato", "presentatore residente all'estero: Stato federato"], ["presentatore.residente_estero.localita", "presentatore residente all'estero: località"],
  ["presentatore.residente_estero.indirizzo", "presentatore residente all'estero: indirizzo"],
  ["legge_estera", "successione regolata da legge straniera", "bool"], ["eventi_eccezionali", "eventi eccezionali (inagibilità dell'immobile prima casa)", "bool"],
  ["data_opzione", "data opzione art. 24-bis TUIR"], ["beneficio_inventario", "accettazione con beneficio d'inventario", "bool"],
  ["residenza_estera_defunto", "residenza estera del defunto"], ["casi_particolari", "non dar corso alle volture catastali (casi particolari)", "bool"],
  ["richiesta_attestazione", "richiesta attestazione di avvenuta presentazione (copia conforme)", "bool"],
  ["morte_presunta.tribunale", "morte presunta: tribunale"], ["morte_presunta.data_deposito", "morte presunta: data di deposito"], ["morte_presunta.sentenza", "morte presunta: sentenza"],
  ["versamento.iban", "versamento: IBAN"], ["versamento.cf_titolare", "versamento: codice fiscale del titolare"],
  ["devoluzione_per_testamento", "devoluzione per testamento", "bool"],
  ["credito_ipotecaria", "credito d'imposta da utilizzare per l'imposta ipotecaria (EF7, euro)"],
  ["credito_catastale", "credito d'imposta da utilizzare per l'imposta catastale (EF13, euro)"],
  ["credito_successione", "credito d'imposta da utilizzare per l'imposta di successione (EF18bis col. 4, euro)"],
  ["credito_tipologia", "credito d'imposta: tipologia di imposta (registro, IVA, IVA Sostegni-bis)"],
  ["credito_imposta", "credito d'imposta maturato (euro; se vuoto, la somma dei crediti utilizzati)"],
  ["credito_acquisto.ufficio_registrazione", "credito d'imposta, registrazione acquisto: ufficio di registrazione"],
  ["credito_acquisto.serie", "credito d'imposta, registrazione acquisto: serie"],
  ["credito_acquisto.numero_registrazione", "credito d'imposta, registrazione acquisto: numero"],
  ["credito_acquisto.sottonumero_registrazione", "credito d'imposta, registrazione acquisto: sottonumero"],
  ["credito_acquisto.data_registrazione", "credito d'imposta, registrazione acquisto: data di registrazione"],
  ["credito_vendita.ufficio_registrazione", "credito d'imposta, registrazione vendita (facoltativa): ufficio di registrazione"],
  ["credito_vendita.serie", "credito d'imposta, registrazione vendita (facoltativa): serie"],
  ["credito_vendita.numero_registrazione", "credito d'imposta, registrazione vendita (facoltativa): numero"],
  ["credito_vendita.sottonumero_registrazione", "credito d'imposta, registrazione vendita (facoltativa): sottonumero"],
  ["credito_vendita.data_registrazione", "credito d'imposta, registrazione vendita (facoltativa): data di registrazione"],
  ["credito_tipologia_2", "credito d'imposta, secondo acquisto: tipologia di imposta (registro, IVA)"],
  ["credito_imposta_2", "credito d'imposta, secondo acquisto: imposta pagata (euro)"],
  ["credito_acquisto_2.ufficio_registrazione", "credito d'imposta, registrazione secondo acquisto: ufficio di registrazione"],
  ["credito_acquisto_2.serie", "credito d'imposta, registrazione secondo acquisto: serie"],
  ["credito_acquisto_2.numero_registrazione", "credito d'imposta, registrazione secondo acquisto: numero"],
  ["credito_acquisto_2.sottonumero_registrazione", "credito d'imposta, registrazione secondo acquisto: sottonumero"],
  ["credito_acquisto_2.data_registrazione", "credito d'imposta, registrazione secondo acquisto: data di registrazione"],
  ["credito_vendita_2.ufficio_registrazione", "credito d'imposta, registrazione vendita del secondo rigo (facoltativa): ufficio di registrazione"],
  ["credito_vendita_2.serie", "credito d'imposta, registrazione vendita del secondo rigo (facoltativa): serie"],
  ["credito_vendita_2.numero_registrazione", "credito d'imposta, registrazione vendita del secondo rigo (facoltativa): numero"],
  ["credito_vendita_2.sottonumero_registrazione", "credito d'imposta, registrazione vendita del secondo rigo (facoltativa): sottonumero"],
  ["credito_vendita_2.data_registrazione", "credito d'imposta, registrazione vendita del secondo rigo (facoltativa): data di registrazione"],
  ["sanzione_ipotecaria", "sanzioni indicate dal professionista: imposta ipotecaria (euro)"],
  ["interessi_ipotecaria", "interessi indicati dal professionista: imposta ipotecaria (euro)"],
  ["sanzione_catastale", "sanzioni indicate dal professionista: imposta catastale (euro)"],
  ["interessi_catastale", "interessi indicati dal professionista: imposta catastale (euro)"],
  ["sanzione_tassa_ipotecaria", "sanzioni indicate dal professionista: tassa ipotecaria (euro)"],
  ["interessi_tassa_ipotecaria", "interessi indicati dal professionista: tassa ipotecaria (euro)"],
  ["sanzione_bollo", "sanzioni indicate dal professionista: imposta di bollo (euro)"],
  ["interessi_bollo", "interessi indicati dal professionista: imposta di bollo (euro)"],
  ["sanzione_successione", "sanzioni indicate dal professionista: imposta di successione (euro)"],
  ["interessi_successione", "interessi indicati dal professionista: imposta di successione (euro)"], ["testamento.estero", "testamento estero", "bool"],
  ["testamento.pubblico_ufficiale", "testamento: pubblico ufficiale"], ["testamento.data_pubblicazione", "testamento: data pubblicazione"],
  ["testamento.ufficio_registrazione", "testamento: ufficio di registrazione"], ["testamento.serie", "testamento: serie"],
  ["testamento.numero_registrazione", "testamento: numero registrazione"], ["testamento.sottonumero_registrazione", "testamento: sottonumero"],
  ["testamento.data_registrazione", "testamento: data registrazione"],
  ["separazione_con_colpa", "separazione con colpa del coniuge superstite (stato civile 5)", "bool"],
  ["no_scioglimento_unione_civile", "nessuna domanda di scioglimento dell'unione civile (stato civile 7)", "bool"],
  ["reintegro_1.ufficio_registrazione", "reintegro dei diritti 1: ufficio di registrazione"],
  ["reintegro_1.serie", "reintegro dei diritti 1: serie"],
  ["reintegro_1.numero_registrazione", "reintegro dei diritti 1: numero"],
  ["reintegro_1.sottonumero_registrazione", "reintegro dei diritti 1: sottonumero"],
  ["reintegro_1.data_registrazione", "reintegro dei diritti 1: data di registrazione"],
  ["reintegro_2.ufficio_registrazione", "reintegro dei diritti 2: ufficio di registrazione"],
  ["reintegro_2.serie", "reintegro dei diritti 2: serie"],
  ["reintegro_2.numero_registrazione", "reintegro dei diritti 2: numero"],
  ["reintegro_2.sottonumero_registrazione", "reintegro dei diritti 2: sottonumero"],
  ["reintegro_2.data_registrazione", "reintegro dei diritti 2: data di registrazione"],
  ["reintegro_3.ufficio_registrazione", "reintegro dei diritti 3: ufficio di registrazione"],
  ["reintegro_3.serie", "reintegro dei diritti 3: serie"],
  ["reintegro_3.numero_registrazione", "reintegro dei diritti 3: numero"],
  ["reintegro_3.sottonumero_registrazione", "reintegro dei diritti 3: sottonumero"],
  ["reintegro_3.data_registrazione", "reintegro dei diritti 3: data di registrazione"],
];
function sezioneDatiDichiarazione(chiavi = null, titolo = 'Dati della dichiarazione') {
  const tel = (S.P.dati.opzioni || {}).telematico || {};
  const dich = tel.dichiarazione || {};
  const leggi = (chiave) => chiave.split(".").reduce((o, k) => (o == null ? undefined : o[k]), dich);
  const sez = h("section", { class: "grp" }, h("h2", {}, titolo));
  const inputs = {};
  const ordDich = (S.schema.ordine || {})['AN.dichiarazione'] || [];
  const posDich = k => { const i = ordDich.indexOf(k); return i < 0 ? ordDich.length : i; };
  for (const [chiave, etichetta0, tipo] of [...CAMPI_DICH].sort((a, b) => posDich(a[0]) - posDich(b[0]))) {
    const etichetta = lblDich(chiave, etichetta0);
    if (chiavi && !chiavi.includes(chiave)) continue;
    const v = S.dichDirty.has(chiave) ? S.dichDirty.get(chiave) : leggi(chiave); const id = "dd_" + chiave.replaceAll(".", "_");
    let inp;
    if (tipo === "bool") {
      inp = h("select", { id, "aria-label": etichetta }, h("option", { value: "" }, "(non indicato)"), h("option", { value: "si" }, "sì"), h("option", { value: "no" }, "no"));
      inp.value = v === true ? "si" : v === false ? "no" : "";
    } else if (chiave === 'presentatore.persona_id') {
      inp = h('select', { id, 'aria-label': etichetta }, h('option', { value: '' }, 'Presentatore distinto / non selezionato'),
        S.P.dati.persone.filter(p => p.ruolo !== 'defunto').map(p => h('option', { value: p.id }, etichettaPersona(p))));
      inp.value = v || '';
    } else if ((S.schema.strutturati || {})["dichiarazione." + chiave]) {
      const sd = S.schema.strutturati["dichiarazione." + chiave], attuale = v == null ? "" : String(v);
      inp = h("select", { id, "aria-label": etichetta }, h("option", { value: "" }, "(non indicato)"),
        sd.opzioni.map(o => h("option", { value: o.valore }, o.valore + " — " + o.etichetta)),
        attuale && !sd.opzioni.some(o => o.valore === attuale) ? h("option", { value: attuale },
      /^\[[a-z_]+\]$/.test(attuale) ? mostra("str", { stato: attuale.slice(1, -1) }) : attuale + " (valore non previsto)") : null);
      inp.value = attuale;
    } else inp = h("input", { id, "aria-label": etichetta, autocomplete: "off", list: listaSuggerimenti("dichiarazione." + chiave),
      placeholder: chiave.includes("data_") ? "GG/MM/AAAA" : "", value: v == null ? "" : chiave.includes("data_") ? dataIt(String(v)) : String(v) });
    const modifica = () => {
      const testo = inp.value.trim();
      S.dichDirty.set(chiave, testo === "" ? null : tipo === "bool" ? testo === "si" : chiave.includes("data_") ? dataIso(testo) : testo);
      aggiornaBottoni(); renderSb();
      if (chiave === 'presentatore.persona_id') renderVista();
    };
    inp.addEventListener("input", modifica); inp.addEventListener("change", modifica);
    inputs[chiave] = inp;
    sez.append(h("div", { class: "rg" }, h("label", { for: id }, etichetta), inp));
  }
  if (!chiavi) sez.append(h("div", { class: "barra dentro" }, h("button", { class: "pil", id: "dd_salva", onclick: async () => {
    // legge l'oggetto corrente e modifica solo le chiavi toccate: persone, beni e passivita' dell'oggetto restano intatti
    await salvaTutto();
  } }, "Salva dati della dichiarazione")));
  return sez;
}
const etichettaPersona = p => [p.cognome, p.nome].filter(Boolean).join(' ') + (p.ruolo ? ' · ' + nomeVal('persone', 'ruolo', p.ruolo) : '');
/* Agevolazione prima casa del dichiarante: opzioni.telematico.dichiarazione.prima_casa (elenco e aiuti: schema.STRUTTURATI). */
function sezionePrimaCasa() {
  const dich = ((S.P.dati.opzioni || {}).telematico || {}).dichiarazione || {};
  const defs = Object.entries(S.schema.strutturati || {}).filter(([k]) => k.startsWith("dichiarazione.prima_casa."));
  const sez = h("section", { class: "grp", id: "sezPrimaCasa" }, h("h2", {}, "Agevolazione prima casa (Sezione II del quadro EH)"),
    h("div", { class: "nota dentro" }, "Servono solo se il dichiarante chiede il codice P: il codice si imposta sulla riga di devoluzione (scheda DV, riquadro «Agevolazione prima casa»). Il dichiarante è il presentatore con carica 1 presente nel quadro EA. Fonti: docs/regole/prima_casa.md."));
  for (const [percorso, sd] of defs) {
    const chiave = percorso.slice("dichiarazione.".length);   // es. prima_casa.requisito_comune
    const corrente = S.dichDirty.has(chiave) ? S.dichDirty.get(chiave) : chiave.split(".").reduce((o, k) => (o == null ? undefined : o[k]), dich);
    const id = "pc_" + chiave.replaceAll(".", "_");
    const opzioni = sd.tipo === "bool" ? [{ valore: "si", etichetta: "sì" }, { valore: "no", etichetta: "no" }] : sd.opzioni;
    const attuale = sd.tipo === "bool" ? (corrente === true ? "si" : corrente === false ? "no" : "") : (corrente == null ? "" : String(corrente));
    const inp = h("select", { id, "aria-label": sd.etichetta }, h("option", { value: "" }, "(non indicato)"),
      opzioni.map(o => h("option", { value: o.valore }, sd.tipo === "bool" ? o.etichetta : o.valore + " — " + o.etichetta)),
      attuale && !opzioni.some(o => o.valore === attuale) ? h("option", { value: attuale }, attuale + " (valore non previsto)") : null);
    inp.value = attuale;
    const dett = h("div", { class: "mut aiuto-voce" });
    const mostraAiuto = () => { const o = sd.tipo === "enum" ? sd.opzioni.find(x => x.valore === inp.value) : null; dett.textContent = o ? o.aiuto : ""; };
    const modifica = () => {
      const t = inp.value;
      S.dichDirty.set(chiave, t === "" ? null : sd.tipo === "bool" ? t === "si" : t);
      mostraAiuto(); aggiornaBottoni(); renderSb();
    };
    inp.addEventListener("change", modifica); mostraAiuto();
    sez.append(h("div", { class: "rg" }, h("label", { for: id }, sd.etichetta), h("div", {}, inp, h("div", { class: "mut aiuto-voce" }, sd.aiuto), dett)));
  }
  sez.append(h("div", { class: "barra dentro" }, h("button", { class: "pil", id: "pc_salva", onclick: () => salvaTutto() }, "Salva dati della dichiarazione")));
  return sez;
}
/* Sezione IV del quadro EH per le riduzioni dell'art. 25 e i codici L, Q chiesti dal dichiarante:
   opzioni.telematico.dichiarazione.riduzioni_art25 (elenco, etichette e aiuti: schema.STRUTTURATI, regole: docs/regole/riduzioni_art25.md). */
function sezioneRiduzioni() {
  const dich = ((S.P.dati.opzioni || {}).telematico || {}).dichiarazione || {};
  const defs = Object.entries(S.schema.strutturati || {}).filter(([k]) => k.startsWith("dichiarazione.riduzioni_art25."));
  const sez = h("section", { class: "grp", id: "sezRiduzioni" }, h("h2", {}, "Riduzioni dell'art. 25 e codici L, Q (Sezione IV del quadro EH)"),
    h("div", { class: "nota dentro" }, "Servono solo se il dichiarante chiede una riduzione 1-5 oppure L o Q: i codici si impostano sulle righe di devoluzione (scheda DV) e il valore delle precedenti successioni sul bene. Indica la successione precedente OPPURE la donazione precedente. Fonti: docs/regole/riduzioni_art25.md."));
  for (const [percorso, sd] of defs) {
    const chiave = percorso.slice("dichiarazione.".length);   // es. riduzioni_art25.l.data
    const corrente = S.dichDirty.has(chiave) ? S.dichDirty.get(chiave) : chiave.split(".").reduce((o, k) => (o == null ? undefined : o[k]), dich);
    const id = "ra_" + chiave.replaceAll(".", "_"), isData = sd.formato === "data";
    let inp;
    if (sd.tipo === "bool") {
      inp = h("select", { id, "aria-label": sd.etichetta }, h("option", { value: "" }, "(non indicato)"), h("option", { value: "si" }, "sì"), h("option", { value: "no" }, "no"));
      inp.value = corrente === true ? "si" : corrente === false ? "no" : "";
    } else inp = h("input", { id, "aria-label": sd.etichetta, autocomplete: "off", list: sd.suggerimenti ? listaSuggerimenti(sd.suggerimenti) : null,
      placeholder: isData ? "GG/MM/AAAA" : "", value: corrente == null ? "" : isData ? dataIt(String(corrente)) : String(corrente) });
    const modifica = () => {
      const t = inp.value.trim();
      S.dichDirty.set(chiave, t === "" ? null : sd.tipo === "bool" ? t === "si" : isData ? dataIso(t) : t);
      aggiornaBottoni(); renderSb();
    };
    inp.addEventListener("input", modifica); inp.addEventListener("change", modifica);
    sez.append(h("div", { class: "rg" }, h("label", { for: id }, sd.etichetta), h("div", {}, inp, h("div", { class: "mut aiuto-voce" }, sd.aiuto))));
  }
  sez.append(h("div", { class: "barra dentro" }, h("button", { class: "pil", id: "ra_salva", onclick: () => salvaTutto() }, "Salva dati della dichiarazione")));
  return sez;
}
function renderFront(main) {
  main.append(h('p', { class: 'generali-intro' }, 'Compila i dati nell’ordine indicato. Le modifiche si salvano insieme con Salva o Ctrl+S.'));
  const grid = h('div', { class: 'generali-griglia' }); main.append(grid);
  grid.append(schedaPersona('1. Defunto', 'defunto', ['cognome', 'nome', 'codice_fiscale', 'sesso', 'data_nascita', 'luogo_nascita', 'provincia_nascita', 'data_decesso', 'comune_decesso', 'provincia_decesso']));
  const tipo = (S.P.dati.opzioni || {}).tipo_dichiarazione || 'originaria';
  const successione = sezioneDatiDichiarazione(['stato_civile', 'devoluzione_per_legge', 'devoluzione_per_testamento'], '2. Successione e devoluzione');
  const sel = h('select', { 'aria-label': 'Tipo di dichiarazione' }, h('option', { value: 'originaria' }, 'Dichiarazione originaria'), h('option', { value: 'sostitutiva' }, 'Dichiarazione sostitutiva'));
  sel.value = tipo;
  sel.addEventListener('change', () => salvaOps([{ op: 'set', sezione: 'opzioni', campi: { tipo_dichiarazione: sel.value } }]));
  successione.insertBefore(h('div', { class: 'rg' }, h('label', {}, 'Tipo di dichiarazione'), sel), successione.children[1] || null);
  if (tipo === 'sostitutiva') successione.append(h('p', { class: 'nota' }, 'Sostitutiva: sono gestiti i codici 1 e 2 (il codice 3, solo documentazione, no). Compila gli estremi della prima dichiarazione e le imposte già versate; la sostitutiva deve contenere tutti i quadri, non solo le modifiche.'));
  grid.append(successione);
  if (tipo === 'sostitutiva') grid.append(sezioneDatiDichiarazione(['codice_sostitutiva', 'prima_anno', 'prima_volume', 'prima_numero', 'ipotecaria_versata', 'catastale_versata', 'successione_versata', 'circoscrizioni_nuove'], 'Dichiarazione sostituita e imposte già versate'));
  const presentatore = sezioneDatiDichiarazione(CAMPI_DICH.filter(([k]) => k.startsWith('presentatore.')).map(([k]) => k), '3. Presentatore e contatti');
  presentatore.classList.add('intera');
  presentatore.append(schedaPersona('Anagrafica del presentatore', 'presentatore', ['cognome', 'nome', 'codice_fiscale', 'sesso', 'data_nascita', 'luogo_nascita', 'provincia_nascita', 'relazione_con_defunto']));
  grid.append(presentatore,
    sezioneDatiDichiarazione(['tempistica_pagamento', 'pagamento_rateale', 'acconto', 'versamento.iban', 'versamento.cf_titolare'], '4. Pagamento'),
    sezioneDatiDichiarazione(['firma_dichiarante', 'dichiara_copie_conformi', 'richiesta_attestazione', 'casi_particolari'], '5. Firme, attestazione e volture'));
  const dich = ((S.P.dati.opzioni.telematico || {}).dichiarazione || {});
  const testamento = h('details', { class: 'gruppo-opzionale', open: dich.devoluzione_per_testamento === true || !!dich.testamento }, h('summary', {}, 'Testamento · dati da compilare se presente'),
    sezioneDatiDichiarazione(CAMPI_DICH.filter(([k]) => k.startsWith('testamento.')).map(([k]) => k), 'Estremi del testamento'));
  const chiaviReintegro = CAMPI_DICH.filter(([k]) => k.startsWith('reintegro_')).map(([k]) => k);
  const stato = h('details', { class: 'gruppo-opzionale', open: dich.separazione_con_colpa != null || dich.no_scioglimento_unione_civile != null || chiaviReintegro.some(k => k.split('.').reduce((o, c) => (o == null ? undefined : o[c]), dich) != null) },
    h('summary', {}, 'Separazione, unione civile e reintegro dei diritti · quadro EH'),
    sezioneDatiDichiarazione(['separazione_con_colpa', 'no_scioglimento_unione_civile', ...chiaviReintegro], 'Dichiarazioni sullo stato civile e sugli accordi di reintegro'));
  const chiaviCrediti = CAMPI_DICH.filter(([k]) => k.startsWith('credito_')).map(([k]) => k);
  const chiaviSanzioni = CAMPI_DICH.filter(([k]) => /^(sanzione|interessi)_/.test(k)).map(([k]) => k);
  const valorizzata = k => k.split('.').reduce((o, c) => (o == null ? undefined : o[c]), dich) != null;
  const pagamenti = h('details', { class: 'gruppo-opzionale', open: chiaviCrediti.some(valorizzata) || chiaviSanzioni.some(valorizzata) },
    h('summary', {}, 'Crediti d\'imposta, sanzioni e interessi · quadri EF ed EH'),
    sezioneDatiDichiarazione(chiaviCrediti, 'Crediti d\'imposta (Legge 448/1998 art. 7 c. 2; DL 73/2021 art. 64 c. 7)'),
    sezioneDatiDichiarazione(chiaviSanzioni, 'Sanzioni e interessi del ravvedimento (importi calcolati dal professionista)'));
  const morte = h('details', { class: 'gruppo-opzionale', open: !!dich.morte_presunta }, h('summary', {}, 'Possesso temporaneo dei beni dell\'assente (carica 8) · morte presunta'),
    sezioneDatiDichiarazione(['morte_presunta.tribunale', 'morte_presunta.data_deposito', 'morte_presunta.sentenza'], 'Sentenza di morte presunta'));
  const primaCasa = h('details', { class: 'gruppo-opzionale', open: !!dich.prima_casa }, h('summary', {}, 'Agevolazione prima casa'), sezionePrimaCasa());
  const riduzioni = h('details', { class: 'gruppo-opzionale', open: !!dich.riduzioni_art25 }, h('summary', {}, 'Riduzioni art. 25 e codici L, Q'), sezioneRiduzioni());
  const aziende = h('details', { class: 'gruppo-opzionale', open: S.P.dati.beni.some(b => b.tipo === 'azienda') }, h('summary', {}, 'Dati delle aziende · se presenti'),
    sezioneDatiDichiarazione(['azienda_data_deposito', 'azienda_camera_commercio'], 'Deposito e camera di commercio'));
  main.append(testamento, stato, pagamenti, morte, primaCasa, riduzioni, aziende);
  const att = new Set(S.P.dati.opzioni.quadri_attivi || S.schema.predefiniti);
  const box = h('details', { class: 'gruppo-opzionale' }, h('summary', {}, 'Quadri inclusi nella pratica · ' + att.size + ' selezionati'));
  for (const q of S.schema.quadri.filter(x => x.gruppo !== 'frontespizio' && x.id !== 'DV' && (!x.generato || att.has(x.id)))) {
    const cb = h('input', { type: 'checkbox', id: 'qa_' + q.id }); cb.checked = att.has(q.id);
    cb.addEventListener('change', () => impostaQuadro(q.id, cb.checked));
    box.append(h('label', { class: 'chk', for: 'qa_' + q.id }, cb, h('span', {}, q.id + ' — ' + q.titolo + (q.supportato ? '' : q.generato ? ' (generato dal programma: scelta precedente da togliere)' : ' (copertura limitata: blocca la finalizzazione)'))));
  }
  main.append(box, documentiPratica(), h('div', { class: 'barra' }, h('button', { class: 'pil', id: 'dd_salva', onclick: salvaTutto }, 'Salva dati generali')));
}
/* Documenti da preparare per QUESTA pratica (report grafica 07/11/2026, punto 12): voci dedotte dai dati gia' inseriti, ciascuna
   col riferimento del Fascicolo I (p. PDF 6 «Quali documenti occorrono», quadri EB/EC p. 20 e 28 per le visure). */
function documentiPratica() {
  const d = S.P.dati, dich = ((d.opzioni || {}).telematico || {}).dichiarazione || {};
  const beni = d.beni || [], persone = (d.persone || []).filter(p => !['defunto', 'presentatore'].includes(p.ruolo));
  const voci = [];
  if (persone.length) voci.push("Albero genealogico in PDF (quadro EG, rigo EG6)");
  if (beni.some(b => ['fabbricato', 'terreno'].includes(b.tipo))) voci.push("Visure catastali di non più di tre mesi per " + beni.filter(b => ['fabbricato', 'terreno'].includes(b.tipo)).length + " immobili");
  if (dich.devoluzione_per_testamento || dich.testamento) voci.push("Copia del testamento pubblicato (rigo EG2)");
  if ((d.passivita || []).length) voci.push("Documenti delle " + d.passivita.length + " passività (rigo EG5)");
  if (beni.some(b => ['disponibilita_finanziaria', 'credito', 'altro'].includes(b.tipo) || quadroBene(b) === 'ER')) voci.push("Saldi di conti e crediti alla data del decesso");
  if (beni.some(b => b.tipo === 'titolo')) voci.push("Estratti dei titoli con il valore alla data del decesso");
  if (beni.some(b => b.tipo === 'azienda')) voci.push("Ultimo bilancio o inventario dell'azienda");
  if (beni.some(b => b.imposta_estera)) voci.push("Certificazione dell'imposta pagata all'estero (rigo EG4)");
  if ((d.devoluzioni || []).some(x => ['P', 'X', 'Z', 'Y'].includes(String(x.agevolazioni || '').toUpperCase())) || dich.prima_casa) voci.push("Dichiarazione sostitutiva per la prima casa (rigo EG9)");
  if (persone.some(p => p.ruolo === 'rinunciatario')) voci.push("Atti di rinuncia all'eredità");
  if (beni.some(b => String(b.rendita_proposta || '').toLowerCase().startsWith('s'))) voci.push("Dichiarazione per la rendita proposta DOCFA (rigo EG8)");
  return h('section', { class: 'grp documenti-pratica' }, h('h2', {}, 'Documenti da avere per questa pratica'),
    voci.length ? h('ul', { class: 'spunte dentro-testo' }, voci.map(v => h('li', {}, v)))
      : h('p', { class: 'mut dentro-testo' }, 'Inserisci eredi e beni: l’elenco si compone da solo.'),
    h('p', { class: 'mut dentro-testo piccolo' }, 'Elenco ricavato dai dati inseriti (Fascicolo I, «Quali documenti occorrono»): non sostituisce il controllo del professionista.'));
}

/* ---------- documenti ---------- */
/* Quadro EG: un rigo per documento. Il file caricato diventa subito un rigo EG e, se e' un PDF leggibile, viene convertito in PDF/A;
   a conversione riuscita senza avvisi di rischio il rigo passa al PDF/A e l'originale viene tolto (server: allegati.prepara_pdfa). */
function statoFile(x) {
  if (!x) return { testo: "file non trovato", tipo: "er" };
  const an = x.analisi || {}, rap = x.rapporto || {}, val = rap.validazione || {};
  if (x.ruolo === "derivato") return { testo: "PDF/A" + (val.esito === "conforme" ? " conforme" : val.esito === "non_conforme" ? " NON conforme" : " (da validare con veraPDF)"), tipo: val.esito === "non_conforme" ? "er" : "ok" };
  if (rap.conservato_senza_riscrittura) return { testo: "PDF/A conforme (originale)", tipo: "ok" };
  if (["leggibile", "firmato"].includes(an.esito)) return { testo: "da convertire in PDF/A", tipo: "av", convertibile: true };
  return { testo: "non convertibile: " + (an.esito || "formato non riconosciuto"), tipo: "er" };
}
function descriviFileEG(aid) {
  const x = (S.allegati || []).find(a => a.id === aid);
  if (!S.allegati) return "…";
  return x ? x.nome + " — " + statoFile(x).testo : "file non trovato (" + aid + ")";
}
async function convertiAllegato(id) {
  const r = await api("/api/allegati/" + id + "/pdfa", { method: "POST" });
  if (!r.derivato && r.esito !== "conforme") throw new Error("Conversione non riuscita: " + (r.dettaglio || r.motivo || r.esito));
  return r;
}
/* Albero genealogico generato dai dati (server: albero_genealogico.py; Fascicolo I p. PDF 6). Un albero caricato a mano non si
   sostituisce senza conferma e non si cancella. */
async function sezioneAlbero(pid) {
  const sez = h("section", { class: "grp albero-gen", id: "albero_gen" }, h("h2", {}, "Albero genealogico (rigo EG6)"));
  let st;
  try { st = await api("/api/pratiche/" + pid + "/albero-genealogico"); }
  catch (e) { sez.append(h("p", { class: "mut dentro-testo" }, "Albero non generabile: " + e.message)); return sez; }
  const r6 = st.righi_eg6 || [];
  const stato = !r6.length ? "Nessun albero genealogico nel quadro EG."
    : st.manuale ? "Nel rigo EG6 c'è un albero caricato a mano (" + (r6.find(x => !x.generato) || {}).nome + ")."
    : st.aggiornato ? "Albero generato dai dati attuali della pratica."
    : "I dati sono cambiati dopo l'ultima generazione: rigenera l'albero.";
  sez.append(h("p", { class: "dentro-testo", id: "albero_stato" }, stato));
  const genera = h("button", { class: "pil", id: "albero_genera", onclick: async ev => {
    if (nMod()) return msg("Salva prima le altre modifiche in corso.", "e");
    ev.target.disabled = true;
    try {
      let r = await post("/api/pratiche/" + pid + "/albero-genealogico", {});
      if (r.esito === "conferma_richiesta") {
        if (!confirm("Il rigo EG6 contiene un albero caricato a mano (" + r.manuali.map(x => x.nome).join(", ") + "). Sostituirlo con l'albero generato dai dati? Il file caricato resta fra i documenti della pratica.")) return;
        r = await post("/api/pratiche/" + pid + "/albero-genealogico", { sostituisci_manuale: true });
      }
      await ricarica(); render();
      const manc = (r.mancanti || []).length;
      msg(r.esito === "gia_aggiornato" ? "L'albero genealogico è già aggiornato ai dati della pratica."
        : "Albero genealogico generato" + (r.pdfa ? " e convertito in PDF/A" : " (PDF/A non creato: convertilo prima dell'invio)") + (manc ? ". Dati da completare per " + manc + " soggetti." : "."), manc || !r.pdfa ? "e" : "o");
    } catch (e) { msg(e.message, "e"); } finally { ev.target.disabled = false; }
  } }, r6.length && !st.manuale ? "Rigenera albero genealogico dai dati" : "Genera albero genealogico dai dati");
  sez.append(h("div", { class: "barra dentro" }, genera));
  const manc = (st.modello || {}).mancanti || [];
  if (manc.length) sez.append(h("p", { class: "mut dentro-testo" }, "Dati da completare: "), h("ul", { class: "elenco-azioni", id: "albero_mancanti" }, manc.map(m => h("li", { class: "er" }, m.soggetto + ": " + m.dati.join(", ")))));
  const att = r6.find(x => x.file_presente);
  if (att) {
    const url = "/api/allegati/" + att.allegato_id + "/file";
    sez.append(h("p", { class: "dentro-testo" }, h("a", { href: url, target: "_blank", rel: "noopener", id: "albero_apri" }, "Apri l'anteprima di " + att.nome)),
      h("iframe", { src: url, title: "Anteprima dell'albero genealogico", id: "albero_anteprima", class: "anteprima-albero" }));
  }
  sez.append(h("p", { class: "mut dentro-testo piccolo" }, "L'albero riporta solo i dati inseriti (Fascicolo I, «Quali documenti occorrono»: nome, cognome, luogo e data di nascita del coniuge e dei beneficiari parenti). Puoi sostituirlo caricando un file sul rigo EG6."));
  return sez;
}
async function renderAllegati(main) {
  const pid = S.P.pratica_id;
  let a;
  try { a = await api("/api/pratiche/" + pid + "/allegati"); }
  catch (e) { msg("Elenco dei documenti non disponibile. " + e.message, "e"); return; }
  if (!S.P || S.P.pratica_id !== pid || (quadro() && quadro().id !== "EG")) return;
  S.allegati = a;
  for (const td of document.querySelectorAll("#vista td[data-allegato]")) { const v = td.dataset.allegato; if (v) { td.textContent = descriviFileEG(v); td.title = td.textContent; } }
  const refs = S.P.dati.documenti_ref || [];
  const usati = new Set(refs.map(r => r.allegato_id));
  const sd = struttDi("documenti_ref", "tipo_eg", null);
  const sez = h("section", { class: "grp allegati" }, h("h2", {}, "Aggiungi un documento"));
  const selTipo = h("select", { id: "teg", "aria-label": "Rigo del quadro EG" }, h("option", { value: "" }, "Rigo del quadro EG…"), sd.opzioni.map(o => h("option", { value: o.valore, title: o.aiuto }, o.etichetta)));
  sez.append(h("div", { class: "barra dentro" }, h("input", { type: "file", id: "file", "aria-label": "File da caricare" }), selTipo,
    h("input", { id: "fin", placeholder: "Descrizione (es. carta d'identità di …)", "aria-label": "Descrizione del documento" }),
    h("button", { class: "pil", onclick: async ev => {
      const file = $("#file").files[0]; if (!file) return msg("Scegli un file.", "e");
      if (!selTipo.value) return msg("Scegli il rigo del quadro EG.", "e");
      if (nMod()) return msg("Salva prima le altre modifiche in corso.", "e");
      // rigo EG6: un solo albero. Il file caricato prende il posto di quello presente (generato: senza chiedere; caricato a mano: con conferma)
      const eg6 = selTipo.value === "AlberoGenealogico" ? refs.find(r => r.tipo_eg === "AlberoGenealogico") : null;
      const prec = eg6 ? a.find(y => y.id === eg6.allegato_id) : null, precGenerato = !!(prec && (prec.analisi || {}).generato);
      if (eg6 && !precGenerato && !confirm("Il rigo EG6 contiene già un albero caricato a mano. Sostituirlo con il nuovo file? Il file precedente resta fra i documenti della pratica.")) return;
      ev.target.disabled = true;
      try {
        const fd = new FormData(); fd.append("file", file); fd.append("tipo_eg", selTipo.value); fd.append("finalita", $("#fin").value);
        const al = await api("/api/pratiche/" + pid + "/allegati", { method: "POST", body: fd });
        const ok = await salvaOps([{ op: "upsert", coll: "documenti_ref", id: eg6 ? eg6.id : nuovoId("documenti_ref"), campi: { allegato_id: al.allegato_id, tipo_eg: selTipo.value, finalita: $("#fin").value || null } }]);
        if (!ok) return;
        if (precGenerato) { try { await api("/api/allegati/" + prec.id + "/elimina", { method: "POST" }); } catch (e) { /* resta fra i file non usati */ } }
        if (["leggibile", "firmato"].includes((al.analisi || {}).esito)) {
          const r = await convertiAllegato(al.allegato_id); await ricarica(); render();
          msg("Documento aggiunto e convertito in PDF/A" + (r.originale_rimosso ? ": resta solo il PDF/A." : ". " + (r.motivo_originale_conservato || "")), r.originale_rimosso ? "o" : "e");
        } else msg("Documento aggiunto. Non è un PDF convertibile: " + ((al.analisi || {}).esito || "") + ".", "e");
      } catch (e) { msg(e.message, "e"); } finally { ev.target.disabled = false; }
    } }, "Aggiungi al quadro EG")));
  sez.append(h("p", { class: "mut dentro-testo" }, "Il file viene convertito in PDF/A e nel quadro EG resta una sola versione. Se la conversione cambia il testo o l'aspetto, o il PDF era firmato, l'originale resta finché non lo controlli. La conformità PDF/A è attestata solo da un validatore indipendente (veraPDF)."));
  // azioni sui documenti del quadro: da convertire, oltre 5 MB
  const daFare = [];
  for (const r of refs) {
    const x = a.find(y => y.id === r.allegato_id), st = statoFile(x);
    if (st.convertibile) daFare.push(h("li", {}, (x.nome) + " — da convertire ", h("button", { class: "gh", disabled: OCCUPATI.has("converti_" + x.id), onclick: occupato("converti_" + x.id, async () => { try { const z = await convertiAllegato(x.id); await ricarica(); render(); msg("Convertito in PDF/A" + (z.originale_rimosso ? ": resta solo il PDF/A." : ". " + (z.motivo_originale_conservato || "")), z.originale_rimosso ? "o" : "e"); } catch (e) { msg(e.message, "e"); } }) }, "Converti in PDF/A")));
    if (x && x.bytes > 5000000) daFare.push(h("li", {}, x.nome + " supera 5 MB ", h("button", { class: "gh", disabled: OCCUPATI.has("suddividi_" + x.id), onclick: occupato("suddividi_" + x.id, async () => { try { const z = await api("/api/allegati/" + x.id + "/suddividi", { method: "POST" }); msg("Ridotto o suddiviso in " + ((z.parti || []).length || 1) + " file: collega le parti ai righi EG.", "o"); renderVista(); } catch (e) { msg(e.message, "e"); } }) }, "Riduci o suddividi")));
  }
  if (daFare.length) main.append(h("section", { class: "grp" }, h("h2", {}, "Da completare"), h("ul", { class: "elenco-azioni" }, daFare)));
  main.append(sez);
  const albero = await sezioneAlbero(pid);
  if (!S.P || S.P.pratica_id !== pid || (quadro() && quadro().id !== "EG")) return;
  main.append(albero);
  // file caricati non collegati a un rigo EG (vecchie conversioni, doppioni, originali gia' convertiti)
  const liberi = a.filter(x => !usati.has(x.id));
  if (liberi.length) {
    const doppi = liberi.some(x => x.ruolo === "derivato" || a.some(y => y.origine_id === x.id));
    const ul = h("ul", { class: "elenco-azioni" }, liberi.map(x => h("li", {}, x.nome + " — " + (x.ruolo === "originale" ? (a.some(y => y.origine_id === x.id) ? "originale già convertito" : "originale non usato") : "copia PDF/A non usata") + " ",
      h("button", { class: "gh", onclick: async () => { if (!confirm("Eliminare il file «" + x.nome + "» dall'archivio della pratica?")) return; try { await api("/api/allegati/" + x.id + "/elimina", { method: "POST" }); msg("File eliminato.", "o"); renderVista(); } catch (e) { msg(e.message, "e"); } } }, "Elimina"))));
    main.append(h("section", { class: "grp" }, h("h2", {}, "File non usati nel quadro EG (" + liberi.length + ")"),
      doppi ? h("div", { class: "barra dentro" }, h("button", { class: "pil", onclick: async () => {
        if (!confirm("Tenere una sola versione PDF/A per documento ed eliminare doppioni e originali già convertiti?")) return;
        try { const r = await post("/api/pratiche/" + pid + "/allegati/riordina", {}); await ricarica(); render(); msg("Eliminati " + r.rimossi.length + " file doppi o già convertiti.", "o"); } catch (e) { msg(e.message, "e"); } } }, "Rimuovi doppioni")) : null,
      ul));
  }
}

/* ---------- salvataggio ---------- */
/* Un errore del server ha un percorso interno (beni[b_e1afbd972a4f].valore): lo si traduce in quadro, riga e campo leggibili,
   si evidenzia il campo e ci si porta il focus. */
function quadroDiEntita(coll, e) {
  if (coll === "persone") return ["defunto", "presentatore"].includes(e.ruolo) ? "AN" : "EA";
  if (coll === "beni") return quadroBene(e);
  return { passivita: "ED", documenti_ref: "EG", devoluzioni: "DV" }[coll] || null;
}
function descriviErrore(x) {
  const m = String(x.percorso || "").match(/^([a-z_]+)\[([^\]]+)\](?:\.([a-z_]+))?$/);
  if (!m || !S.schema.collezioni[m[1]]) return { testo: x.messaggio, x };
  const [, coll, eid, campo] = m;
  const nuova = [...S.nuove.values()].find(n => n.id === eid), esistente = (S.P.dati[coll] || []).find(e => e.id === eid);
  const sporca = [...S.dirty.values()].find(d => d.id === eid);
  const entita = nuova ? { ...nuova.campi } : { ...(esistente || {}), ...(sporca ? sporca.campi : {}) };
  const quadroId = nuova ? nuova.q : quadroDiEntita(coll, entita);
  const chiave = nuova ? [...S.nuove].find(([, n]) => n.id === eid)[0] : "e:" + coll + ":" + eid;
  let riga = nuova ? "nuova riga" : esistente ? etichetta(coll, esistente) : "";
  if (!riga || riga === eid) riga = "riga senza descrizione";
  const nomeCampo = campo ? lbl(coll, campo, quadroId) : null;
  const dove = (quadroId ? "Quadro " + quadroId + ", " : "") + riga;
  return { testo: dove + (nomeCampo ? " — " + nomeCampo : "") + ": " + x.messaggio, x, coll, eid, campo, quadroId, chiave,
           path: campo ? coll + "[" + eid + "]." + campo : null };
}
/* Motivo di un export non riuscito: oggetto {percorso, messaggio} o testo «beni[b_...].campo: spiegazione».
   Il percorso interno diventa quadro, riga e campo (revisione 2, punto 6). */
function motivoLeggibile(x) {
  if (typeof x === "string") {
    const m = x.match(/^((?:opzioni\.telematico\.)?[a-z_]+\[[^\]]+\](?:\.[a-z_]+)?):\s*(.*)$/s);
    if (!m) return x;
    x = { percorso: m[1], messaggio: m[2] };
  }
  if (!x || typeof x !== "object") return String(x);
  const percorso = String(x.percorso || "").replace(/^opzioni\.telematico\./, "");
  try { return descriviErrore({ ...x, percorso }).testo || String(x.messaggio || ""); }
  catch (_) { return String(x.messaggio || x.percorso || ""); }
}
function mostraErroriSalvataggio(errori) {
  const d = errori.map(descriviErrore);
  const righe = d.slice(0, 5).map(x => x.testo);
  if (d.length > 5) righe.push("... e altri " + (d.length - 5) + " errori.");
  msg("Non salvato: correggi i dati indicati.\n" + righe.join("\n"), "e");
  const primo = d.find(x => x.chiave && x.quadroId);
  if (!primo) return;
  if (primo.quadroId !== S.sel || S.riga !== primo.chiave || S.tab !== "dati") { S.sel = primo.quadroId; S.riga = primo.chiave; S.tab = "dati"; render(); }
  let focalizzato = false;
  for (const x of d) {
    if (!x.path) continue;
    const el = document.querySelector('[data-path="' + CSS.escape(x.path) + '"]');
    if (!el) continue;
    el.classList.add("bad"); el.setAttribute("aria-invalid", "true");
    if (!(el.parentElement && el.parentElement.querySelector(".e.sv"))) el.after(h("div", { class: "e sv" }, x.x.messaggio));
    if (!focalizzato) { focalizzato = true; el.scrollIntoView({ block: "center" }); el.focus(); }
  }
}
async function salvaOps(ops, confermate) {
  if (S.writeBusy) { msg("Salvataggio già in corso. Le modifiche restano da salvare.", "e"); return false; }
  S.writeBusy = true; aggiornaBottoni();
  try {
    const r = await post("/api/pratiche/" + S.P.pratica_id + "/aggiorna", { revisione_attesa: S.P.revisione, operazioni: ops, chiave: crypto.randomUUID() });
    const d = new Date(); S.salvata = String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
    await ricarica(); if (confermate) confermate(); render();
    msg("Salvato (revisione " + r.revisione + ").", "o");   // dopo il ricaricamento: il messaggio non anticipa lo stato mostrato
    await caricaPratiche(); return true;
  } catch (e) {
    if (e.dati && e.dati.errori) mostraErroriSalvataggio(e.dati.errori);
    else if (e.stato === 409) { msg("La pratica è stata modificata altrove (" + e.message + "). Le tue modifiche non sono state applicate: controlla i dati aggiornati e salva di nuovo.", "e"); await ricarica(); render(); }
    else msg(e.message, "e");
    return false;
  } finally { S.writeBusy = false; aggiornaBottoni(); }
}
async function salvaTutto() {
  if (!S.P || S.writeBusy) return false;
  // Snapshot indipendente: la digitazione durante l'HTTP rimane nel buffer vivo.
  for (const d of S.dirty.values()) if (!d.id) d.id = nuovoId(d.coll);
  const dirty = structuredClone(S.dirty), nuove = structuredClone(S.nuove), dichiarazione = structuredClone(S.dichDirty), supplementi = structuredClone(S.supDirty), fornitore = structuredClone(S.fornitoreDirty);
  const ops = [];
  if (Object.keys(fornitore).length) {
    const f = { ...(S.P.dati.opzioni.fornitore || {}), ...fornitore };
    f.tipo = f.tipo || '1';
    if (f.tipo === '1') { delete f.impegno_codice; delete f.data_impegno; }
    ops.push({ op: 'set', sezione: 'opzioni', campi: { fornitore: f } });
  }
  if (dichiarazione.size || supplementi.size) {
    const tel = structuredClone(S.P.dati.opzioni.telematico || {});
    const d = tel.dichiarazione = tel.dichiarazione || {};
    for (const [path, val] of dichiarazione) {
      const parti = path.split('.'); let o = d;
      for (const p of parti.slice(0, -1)) o = o[p] = o[p] || {};
      if (val === null) delete o[parti.at(-1)]; else o[parti.at(-1)] = val;
    }
    const pota = o => { for (const k of Object.keys(o)) if (o[k] && typeof o[k] === 'object' && !Array.isArray(o[k])) { pota(o[k]); if (!Object.keys(o[k]).length) delete o[k]; } };
    pota(d);   // oggetti annidati rimasti vuoti (presentatore, versamento, testamento, prima_casa, riduzioni_art25...)
    for (const { coll, id, campi } of supplementi.values()) {
      const ent = (tel[coll] = tel[coll] || {})[id] = ((tel[coll] || {})[id] || {});
      for (const [k, v] of Object.entries(campi)) { if (v === null) delete ent[k]; else ent[k] = v; }
      if (!Object.keys(ent).length) delete tel[coll][id];
    }
    ops.push({ op: 'set', sezione: 'opzioni', campi: { telematico: tel } });
  }
  // Una riga aggiunta in un quadro non selezionato lo seleziona (altrimenti resta il rilievo «dati in quadro non attivo»)
  const daAttivare = new Set();
  for (const n of nuove.values()) {
    if (!Object.values(n.campi).some(v => v !== null)) continue;
    const idq = n.coll === "beni" ? quadroBene(n.campi) : n.q, qd = S.Q.quadri.find(x => x.id === idq);
    if (qd && qd.supportato && !qd.attivo) daAttivare.add(idq);
  }
  if (daAttivare.size) ops.unshift({ op: "set", sezione: "opzioni", campi: { quadri_attivi: [...new Set([...(S.P.dati.opzioni.quadri_attivi || S.schema.predefiniti), ...daAttivare])] } });
  for (const d of dirty.values()) ops.push({ op: "upsert", coll: d.coll, id: d.id, campi: { ...d.campi } });
  for (const n of nuove.values()) { const campi = Object.fromEntries(Object.entries(n.campi).filter(([, v]) => v !== null)); if (Object.keys(campi).length) ops.push({ op: "upsert", coll: n.coll, id: n.id, campi }); }
  if (!ops.length) return true;
  return salvaOps(ops, () => {
    for (const [k, v] of Object.entries(fornitore)) if (uguale(S.fornitoreDirty[k], v)) delete S.fornitoreDirty[k];
    for (const [k, v] of dichiarazione) if (uguale(S.dichDirty.get(k), v)) S.dichDirty.delete(k);
    for (const [key, inviato] of supplementi) {
      const vivo = S.supDirty.get(key); if (!vivo) continue;
      for (const [k, v] of Object.entries(inviato.campi)) if (uguale(vivo.campi[k], v)) delete vivo.campi[k];
      if (!Object.keys(vivo.campi).length) S.supDirty.delete(key);
    }
    for (const [k, inviato] of dirty) {
      const vivo = S.dirty.get(k); if (!vivo) continue;
      for (const [c, v] of Object.entries(inviato.campi)) if (uguale(vivo.campi[c], v)) delete vivo.campi[c];
      if (!Object.keys(vivo.campi).length) S.dirty.delete(k);
    }
    for (const [k, inviato] of nuove) {
      const vivo = S.nuove.get(k); if (!vivo) continue;
      const restanti = Object.fromEntries(Object.entries(vivo.campi).filter(([c, v]) => !uguale(v, inviato.campi[c])));
      const stabile = "e:" + inviato.coll + ":" + inviato.id;
      if (Object.keys(restanti).length) S.dirty.set(stabile, { coll: inviato.coll, id: inviato.id, campi: restanti });
      S.nuove.delete(k); if (S.riga === k) S.riga = stabile;
    }
  });
}

/* ---------- compilazione dal codice fiscale ---------- */
/* Dal codice fiscale si ricavano sesso, data di nascita, comune e provincia (server: /api/codice-fiscale). E' un suggerimento:
   riempie solo i campi ancora vuoti e dice cosa ha compilato, l'utente verifica. */
const DA_CF = ["data_nascita", "luogo_nascita", "sesso", "provincia_nascita"];
const _cacheCF = new Map();
async function decodificaCF(cf, ruolo) {
  const k = cf + "|" + (ruolo || "");
  if (!_cacheCF.has(k)) _cacheCF.set(k, await api("/api/codice-fiscale?cf=" + encodeURIComponent(cf) + (ruolo ? "&ruolo=" + encodeURIComponent(ruolo) : "")));
  return _cacheCF.get(k);
}
function testoCF(r, riempiti) {
  const parti = [];
  if (!r.valido) parti.push("Codice fiscale non valido: " + r.motivi.join("; ") + ".");
  if (riempiti.length) parti.push("Compilato dal codice fiscale: " + riempiti.map(c => lbl("persone", c)).join(", ") + ". Verifica i dati.");
  if (r.avvisi.length) parti.push(r.avvisi.join(" "));
  return parti.join(" ");
}
async function suggerisciDaCF(cf, ruolo, leggiCampo, scriviCampo, ancoraValida) {
  const v = String(cf || "").trim().toUpperCase();
  if (v.length !== 16) return { riempiti: [], testo: "" };
  const gen = S.gen, pid = S.P && S.P.pratica_id;
  let r; try { r = await decodificaCF(v, ruolo); } catch (e) { return { riempiti: [], testo: "" }; }
  // risposta tardiva: pratica cambiata/chiusa, procedura guidata riaperta o codice fiscale nel frattempo modificato
  if (gen !== S.gen || pid !== (S.P && S.P.pratica_id) || (ancoraValida && !ancoraValida())) return { riempiti: [], testo: "" };
  const riempiti = [];
  for (const c of DA_CF) { const x = r.campi[c]; if (x && !String(leggiCampo(c) || "").trim()) { scriviCampo(c, x); riempiti.push(c); } }
  return { riempiti, testo: testoCF(r, riempiti) };
}

/* ---------- procedura guidata ---------- */
const W = { passo: 0, dati: {} };
const PASSI = ["Defunto", "Tipo", "Quadri", "Conferma"];
function titoloWiz() { return "Successione " + ([W.dati.cognome, W.dati.nome].filter(Boolean).join(" ").trim() || "nuova"); }
function wizRender() {
  $("#wizPassi").replaceChildren(...PASSI.map((p, i) => h("li", { "aria-current": i === W.passo ? "step" : "false" }, (i + 1) + ". " + p)));
  const c = $("#wizCorpo"); c.replaceChildren(); $("#wizErr").textContent = "";
  $("#wIndietro").hidden = W.passo === 0; $("#wAvanti").textContent = W.passo === PASSI.length - 1 ? "Crea dichiarazione" : "Avanti";
  const d = W.dati;
  const f = (k, label, ph) => h("div", { class: "campo" }, h("label", { for: "w_" + k }, label), h("input", { id: "w_" + k, value: d[k] || "", placeholder: ph || "", class: k === "codice_fiscale" ? "mono cf" : "", oninput: ev => { d[k] = ev.target.value; if (k === "codice_fiscale") wizDaCF(ev.target.value); } }));
  if (W.passo === 0) c.append(h("p", { class: "mut" }, "Dati anagrafici del defunto. Potrai completarli o correggerli nei dati generali."), h("div", { class: "griglia" }, f("cognome", "Cognome"), f("nome", "Nome"), f("codice_fiscale", "Codice fiscale"), f("data_nascita", "Data di nascita", "GG/MM/AAAA"), f("luogo_nascita", "Comune di nascita"), f("provincia_nascita", "Provincia di nascita", "RM"), f("data_decesso", "Data del decesso", "GG/MM/AAAA"), f("comune_decesso", "Comune del decesso"), f("provincia_decesso", "Provincia del decesso", "RM")), h("div", { id: "w_cf_nota", class: "mut", class: "testo-m spazio-su", "aria-live": "polite" }));
  if (W.passo === 1) {
    d.tipo = d.tipo || "originaria";
    for (const [v, t, s] of [["originaria", "Dichiarazione originaria", "Prima dichiarazione per questa successione."], ["sostitutiva", "Dichiarazione sostitutiva", "Sostituisce una dichiarazione già presentata. La gestione dei dati della precedente non è ancora disponibile."]]) {
      const r = h("input", { type: "radio", name: "tipo", id: "t_" + v, value: v, onchange: () => { d.tipo = v; } }); r.checked = d.tipo === v;
      c.append(h("label", { class: "radio", for: "t_" + v }, r, h("span", {}, h("strong", {}, t), h("div", { class: "mut" }, s))));
    }
  }
  if (W.passo === 2) {
    d.quadri = d.quadri || [...quadriPredefiniti()];
    c.append(h("p", { class: "mut" }, "Seleziona i quadri da compilare. Potrai cambiare scelta nel frontespizio. I quadri EE, EF, EH ed EI non compaiono: li genera il programma."));
    for (const q of S.schema.quadri.filter(x => x.gruppo !== "frontespizio" && x.id !== "DV" && !x.generato)) {
      const cb = h("input", { type: "checkbox", id: "wq_" + q.id }); cb.checked = d.quadri.includes(q.id);
      cb.addEventListener("change", () => { d.quadri = cb.checked ? [...new Set([...d.quadri, q.id])] : d.quadri.filter(x => x !== q.id); });
      c.append(h("label", { class: "chk", for: "wq_" + q.id }, cb, h("span", {}, q.id + " — " + q.titolo + (q.supportato ? "" : " (copertura limitata: blocca la finalizzazione)"))));
    }
  }
  if (W.passo === 3) c.append(h("p", {}, "Verrà creata la dichiarazione «" + titoloWiz() + "» con " + (d.quadri || quadriPredefiniti()).length + " quadri selezionati, tipo " + (d.tipo || "originaria") + "."), h("p", { class: "mut" }, "Potrai completare ogni dato nei quadri; i controlli ti mostreranno cosa manca."));
}
async function wizDaCF(valore) {
  const d = W.dati;
  const { testo } = await suggerisciDaCF(valore, "defunto", c => d[c], (c, x) => { d[c] = x; const el = $("#w_" + c); if (el) el.value = x; }, () => W.dati === d && String(d.codice_fiscale || "").trim().toUpperCase() === String(valore || "").trim().toUpperCase());
  const nota = $("#w_cf_nota"); if (nota) nota.textContent = testo;
}
/* Una chiave di richiesta per ogni apertura della procedura: un doppio clic o un nuovo tentativo dopo un errore di rete
   non crea due pratiche (revisione 2, punto 1). */
function wizApri() { if (S.writeBusy) return msg("Salvataggio in corso: attendi prima di creare una pratica.", "e"); W.passo = 0; W.dati = {}; W.extra = null; W.chiave = crypto.randomUUID(); W.busy = false; S.gen++; wizRender(); $("#wAvanti").disabled = false; $("#wiz").showModal(); }
async function wizAvanti() {
  if (W.busy) return;
  const d = W.dati;
  if (W.passo === 0 && !(d.cognome || "").trim()) { $("#wizErr").textContent = "Indica almeno il cognome del defunto."; return; }
  if (W.passo < PASSI.length - 1) { W.passo++; wizRender(); return; }
  const campi = {}; for (const k of ["cognome", "nome", "codice_fiscale", "data_nascita", "luogo_nascita", "sesso", "provincia_nascita", "data_decesso", "comune_decesso", "provincia_decesso"]) if ((d[k] || "").trim()) campi[k] = (k === "codice_fiscale" || k.startsWith('provincia')) ? d[k].trim().toUpperCase() : (k.startsWith("data_") ? dataIso(d[k]) : d[k].trim());
  campi.ruolo = "defunto";
  const iniziali = [{ op: "upsert", coll: "persone", campi }, { op: "set", sezione: "opzioni", campi: { tipo_dichiarazione: d.tipo || "originaria", quadri_attivi: d.quadri || S.schema.predefiniti } }, ...(W.extra || [])];
  W.busy = true; const bt = $("#wAvanti"); bt.disabled = true; bt.setAttribute("aria-busy", "true"); $("#wizErr").textContent = "";
  let r;
  try {
    r = await post("/api/pratiche", { titolo: titoloWiz(), chiave: W.chiave, iniziali });
  } catch (e) {
    const t = e.dati && e.dati.errori ? e.dati.errori.map(x => x.messaggio).join(" | ") : e.message;
    if (e.stato === 422) W.chiave = crypto.randomUUID();   // rifiutata dal server: nessuna pratica creata, i dati corretti sono una nuova richiesta
    if (e.dati && e.dati.errori) { W.passo = 0; wizRender(); }
    $("#wizErr").textContent = t;
    return;
  } finally { W.busy = false; bt.disabled = false; bt.removeAttribute("aria-busy"); }
  $("#wiz").close(); await caricaPratiche(); await apri(r.pratica_id, "AN"); msg("Dichiarazione creata.", "o");
}

/* Impostazioni: percorsi degli strumenti esterni (server: /api/impostazioni), con stato di rilevamento. */
const IMP = { voci: [], iniziali: {}, aspetto: null, profilo: {}, preferenze: {} };
function impAspettoRender(p) {
  IMP.aspetto = { ...preferenze, ...p };
  const grid = h('div', { class: 'aspetto-griglia' });
  const scelte = (chiave, titolo, opzioni) => {
    const id = 'aspetto_' + chiave;
    const el = h('select', { id, 'aria-label': titolo }, opzioni.map(([v, t]) => h('option', { value: v }, t)));
    el.value = String(IMP.aspetto[chiave]);
    el.addEventListener('change', () => { IMP.aspetto[chiave] = chiave === 'dimensione' ? Number(el.value) : el.value; applicaAspetto(IMP.aspetto); });
    grid.append(h('div', { class: 'campo' }, h('label', { for: id }, titolo), el));
  };
  scelte('tema', 'Tema', [['sistema', 'Come il sistema'], ['chiaro', 'Chiaro'], ['scuro', 'Scuro'], ['seppia', 'Seppia']]);
  scelte('font', 'Carattere', [['sistema', 'Atkinson Hyperlegible (predefinito)'], ['segoe', 'Segoe UI'], ['arial', 'Arial'], ['verdana', 'Verdana'], ['georgia', 'Georgia'], ['consolas', 'Consolas']]);
  scelte('dimensione', 'Dimensione del testo', Array.from({ length: 11 }, (_, i) => [String(i + 12), (i + 12) + ' px']));
  scelte('interlinea', 'Spaziatura delle righe', [['compatta', 'Compatta'], ['normale', 'Normale'], ['ampia', 'Ampia']]);
  scelte('accento', 'Colore di accento', [['predefinito', 'Verde modello (predefinito)'], ['blu', 'Blu'], ['verde', 'Verde'], ['viola', 'Viola'], ['arancio', 'Arancio'], ['rosso', 'Rosso'], ['grafite', 'Grafite']]);
  scelte('densita', 'Densità delle tabelle', [['compatta', 'Compatta'], ['normale', 'Normale'], ['ampia', 'Ampia']]);
  scelte('contrasto', 'Contrasto', [['normale', 'Normale'], ['alto', 'Alto (bordi e testi più marcati)']]);
  scelte('movimento', 'Animazioni', [['normale', 'Normali'], ['ridotto', 'Ridotte']]);
  scelte('avvio', 'All’avvio', [['elenco', 'Mostra l’elenco delle pratiche'], ['ultima', 'Riapri l’ultima pratica']]);
  const nome = h('input', { id: 'aspetto_nome_studio', maxlength: '60', value: IMP.aspetto.nome_studio || '', placeholder: 'es. Studio Rossi' });
  nome.addEventListener('input', () => { IMP.aspetto.nome_studio = nome.value; applicaAspetto(IMP.aspetto); });
  grid.append(h('div', { class: 'campo' }, h('label', { for: 'aspetto_nome_studio' }, 'Nome dello studio (in intestazione)'), nome));
  const quadriGrid = h('div', { class: 'aspetto-griglia', role: 'group', 'aria-label': 'Quadri proposti nelle nuove pratiche' },
    ['EA', 'EB', 'EC', 'ER', 'ED', 'EF', 'EG', 'EH', 'EI', 'EL', 'EM', 'EN', 'EO', 'EP', 'EQ'].map(q => {
      const el = h('input', { type: 'checkbox', id: 'qp_' + q, checked: (IMP.aspetto.quadri_predefiniti || []).includes(q) });
      el.addEventListener('change', () => { const s = new Set(IMP.aspetto.quadri_predefiniti || []); el.checked ? s.add(q) : s.delete(q); IMP.aspetto.quadri_predefiniti = [...s]; });
      return h('label', { class: 'chk', for: 'qp_' + q }, el, h('span', {}, q));
    }));
  grid.append(h('div', { class: 'campo intera' }, h('label', {}, 'Quadri proposti nelle nuove pratiche (vuoto = quelli standard)'), quadriGrid));
  $('#impAspetto').replaceChildren(h('h3', {}, 'Aspetto e leggibilità'), grid,
    h('div', { class: 'aspetto-anteprima' }, h('strong', {}, 'Anteprima del carattere'), h('p', {}, 'Dichiarazione di successione, Roma (RM), € 1.234,56'), h('p', { class: 'mono' }, 'RSSMRA50A01H501U  0 O 1 l I')),
    h('p', { class: 'mut' }, 'Trascina il separatore accanto ai dati per allargare o restringere il pannello. La larghezza viene ricordata.'),
    h('button', { type: 'button', class: 'gh', onclick: () => { impAspettoRender(ASPETTO_DEFAULT); applicaAspetto(IMP.aspetto); } }, 'Ripristina aspetto predefinito'));
}
function impProfiloRender(p) {
  IMP.profilo = { ...p };
  const campo = (chiave, titolo, el) => { el.id = 'prof_' + chiave; el.setAttribute('aria-label', titolo); return h('div', { class: 'campo' }, h('label', { for: el.id }, titolo), el); };
  const cf = h('input', { class: 'mono cf', value: p.cf || '', placeholder: 'codice fiscale', oninput: e => { IMP.profilo.cf = e.target.value.trim().toUpperCase(); } });
  const tipo = h('select', {}, h('option', { value: '' }, 'Non indicato'), h('option', { value: '1' }, 'Dichiarante (1)'), h('option', { value: '10' }, 'Intermediario (10)'));
  tipo.value = p.tipo || ''; tipo.addEventListener('change', () => { IMP.profilo.tipo = tipo.value; });
  const imp = h('select', {}, h('option', { value: '' }, 'Non indicato'), h('option', { value: '1' }, 'Predisposta dal dichiarante (1)'), h('option', { value: '2' }, 'Predisposta dall’intermediario (2)'));
  imp.value = p.impegno_codice || ''; imp.addEventListener('change', () => { IMP.profilo.impegno_codice = imp.value; });
  $('#impProfilo').replaceChildren(h('h3', {}, 'Profilo dello studio'),
    h('p', { class: 'mut' }, 'Chi presenta il file. Viene proposto in ogni nuova pratica e si può cambiare pratica per pratica.'),
    h('div', { class: 'aspetto-griglia' }, campo('cf', 'Codice fiscale del fornitore', cf), campo('tipo', 'Tipo fornitore', tipo), campo('impegno', 'Impegno a trasmettere', imp)));
}
async function impBackupRender() {
  const box = $('#impBackup');
  let b = { cartella: '', backup: [] };
  try { b = await api('/api/backup'); } catch (_) { /* elenco non disponibile: il pulsante resta */ }
  const ultimo = b.backup[0];
  box.replaceChildren(h('h3', {}, 'Backup'),
    h('p', { class: 'mut' }, 'Cartella: ' + (b.cartella || '—') + (ultimo ? ' · ultimo: ' + ultimo.creato.replace('T', ' ') : ' · nessun backup ancora') +
      '. Prima di generare un file si fa una copia automatica (al massimo una ogni 30 minuti). Per proteggerti da un guasto del disco imposta una cartella su un\'altra unità (Strumenti e percorsi).'),
    h('button', { type: 'button', class: 'gh', onclick: async ev => {
      ev.target.disabled = true;
      try { const r = await post('/api/backup', {}); msg('Backup creato e verificato: ' + r.nome, 'o'); STUDIO.ultimoBackup = r.nome; renderSb(); }
      catch (e) { msg('Backup non riuscito: ' + e.message, 'e'); }
      ev.target.disabled = false; impBackupRender();
    } }, 'Crea backup ora'));
}
function impPreferenzeRender(p) {
  IMP.preferenze = { ...p };
  const casella = (chiave, titolo, nota) => {
    const el = h('input', { type: 'checkbox', id: 'pref_' + chiave, checked: !!p[chiave] });
    el.addEventListener('change', () => { IMP.preferenze[chiave] = el.checked; });
    return h('div', { class: 'campo' }, h('label', { class: 'chk', for: el.id }, el, h('span', {}, titolo)), h('div', { class: 'mut testo-m' }, nota));
  };
  const numero = (chiave, titolo, minimo, massimo) => {
    const el = h('input', { type: 'number', id: 'pref_' + chiave, min: String(minimo), max: String(massimo), value: String(p[chiave]) });
    el.addEventListener('input', () => { const n = parseInt(el.value, 10); if (Number.isInteger(n)) IMP.preferenze[chiave] = n; });
    return h('div', { class: 'campo' }, h('label', { for: el.id }, titolo + ' (' + minimo + '–' + massimo + ')'), el);
  };
  $('#impPreferenze').replaceChildren(h('h3', {}, 'Operatività e sicurezza'),
    casella('pulizia_automatica', 'Elimina automaticamente i file temporanei e di lavoro', 'Copie di XML e uscite dei controlli lasciate nella cartella di lavoro. Non tocca pratiche, allegati, file generati né backup.'),
    numero('pulizia_ore', 'Elimina i temporanei più vecchi di (ore)', 1, 720),
    h('button', { type: 'button', class: 'gh', onclick: async ev => {
      ev.target.disabled = true;
      try { const r = await post('/api/pulizia', {}); msg('Pulizia eseguita: ' + r.eliminati + ' elementi, ' + r.byte_liberati + ' byte liberati.', 'o'); }
      catch (e) { msg('Pulizia non riuscita: ' + e.message, 'e'); }
      ev.target.disabled = false;
    } }, 'Pulisci ora'),
    numero('avviso_visura_giorni', 'Avvisa se la visura catastale ha più di (giorni)', 30, 365),
    casella('visura_blocca', 'Una visura vecchia o senza data blocca la finalizzazione', 'Il Fascicolo chiede visure di non più di tre mesi prima della presentazione. Se non spunti, è solo un avviso.'),
    casella('mcp_sola_lettura', 'Claude (MCP) in sola lettura', 'Claude può leggere pratiche e controlli ma non modificare pratiche, generare file, allegare o fare backup. Vale subito, senza riavvio.'));
}
function impDiagnosiRender(componente) {
  const box = $('#impDiagnosi');
  const nota = componente && componente.messaggio ? h('p', { class: componente.stato === 'aggiornata' ? 'mut' : 'nota', role: 'status' }, componente.messaggio) : null;
  const risultato = h('div', { id: 'impDiagnosiRis', 'aria-live': 'polite' });
  box.replaceChildren(h('h3', {}, 'Diagnosi'),
    h('p', { class: 'mut' }, 'Controlla Java, il componente di controllo SUC13 (e la sua versione), Ghostscript, veraPDF, Desktop Telematico, Entratel-Multifile, i backup e il collegamento di Claude. Non esegue nulla dell\'Agenzia.'),
    nota,
    h('button', { type: 'button', class: 'gh', onclick: async ev => {
      ev.target.disabled = true; risultato.replaceChildren(h('p', { class: 'mut' }, 'Controllo in corso…'));
      try {
        const r = await post('/api/diagnosi', {});
        const icona = { ok: '✓', avviso: '⚠', errore: '✗', info: 'ℹ' };
        risultato.replaceChildren(h('p', { class: 'forte' }, r.riepilogo),
          ...r.voci.map(v => h('div', { class: 'campo diagnosi-voce' }, h('div', {}, (icona[v.stato] || '·') + ' ' + v.nome + ' — ' + v.dettaglio),
            v.rimedio && v.stato !== 'ok' ? h('div', { class: 'mut testo-m' }, v.rimedio) : null)));
      } catch (e) { risultato.replaceChildren(h('p', { class: 'err' }, 'Diagnosi non riuscita: ' + e.message)); }
      ev.target.disabled = false;
    } }, 'Esegui diagnosi'), risultato);
}
function impRender(s) {
  impDiagnosiRender(s.componente_controllo);
  impProfiloRender(s.profilo || {}); impBackupRender(); impPreferenzeRender(s.preferenze || {});
  IMP.voci = s.voci; IMP.iniziali = Object.fromEntries(s.voci.map(v => [v.chiave, v.valore || ""]));
  impAspettoRender(s.interfaccia);
  $("#impFile").textContent = "File di configurazione: " + s.file;
  $("#impCorpo").replaceChildren(...s.voci.map(v => h("div", { class: "campo voce-imp" },
    h("label", { for: "imp_" + v.chiave }, v.etichetta),
    h("input", { id: "imp_" + v.chiave, class: "mono", value: v.valore || "", disabled: !v.modificabile, placeholder: v.modificabile ? "non impostato" : "" }),
    h("div", { class: "mut testo-m" }, (v.a_posto ? "✓ " : "✗ ") + v.dettaglio + (v.valore ? " · origine: " + v.origine : "")),
    h("div", { class: "mut testo-m" }, v.nota))));
}
/* Impronta di cio' che si puo' modificare nelle Impostazioni: se alla chiusura e' diversa, ci sono modifiche non salvate. */
function impFirma() {
  const voci = (IMP.voci || []).filter(v => v.modificabile).map(v => { const el = document.getElementById("imp_" + v.chiave); return el ? el.value.trim() : ""; });
  return JSON.stringify([IMP.aspetto, IMP.profilo, IMP.preferenze, voci]);
}
function impChiudi() {
  if (IMP.firma && impFirma() !== IMP.firma && !confirm("Ci sono modifiche non salvate nelle Impostazioni. Chiudere senza salvarle?")) return false;
  $("#imp").close(); return true;
}
async function impApri() {
  $("#impErr").textContent = "";
  try { impRender(await api("/api/impostazioni")); IMP.firma = impFirma(); $("#imp").showModal(); }
  catch (e) { msg("Impostazioni non disponibili: " + e.message, "e"); }
}
async function impSalva() {
  const modifiche = {};
  for (const v of IMP.voci) if (v.modificabile) { const x = $("#imp_" + v.chiave).value.trim(); if (x !== IMP.iniziali[v.chiave]) modifiche[v.chiave] = x; }
  try {
    const profilo = Object.fromEntries(Object.entries(IMP.profilo).filter(([, v]) => v));
    const s = await post("/api/impostazioni", { modifiche, interfaccia: IMP.aspetto, profilo, preferenze: IMP.preferenze });
    STUDIO.profilo = s.profilo || {};
    memorizzaAspetto(s.interfaccia);
    impRender(s); IMP.firma = impFirma(); $("#impErr").textContent = "";
    msg("Impostazioni salvate." + (s.avvisi.length ? " " + s.avvisi.join(" ") : ""), "o");
    try { mostraInfo(await api("/api/info")); } catch (_) { /* riga informativa: aggiornata al prossimo caricamento */ }
  } catch (e) { $("#impErr").textContent = e.message; }
}
$("#bImpost").onclick = impApri;
/* Indice delle Impostazioni: porta alla sezione senza cambiare l'indirizzo della pagina. */
$("#impIndice").addEventListener("click", ev => {
  const a = ev.target.closest("a"); if (!a) return;
  ev.preventDefault();
  const dest = $(a.getAttribute("href")); if (dest) dest.scrollIntoView({ block: "start" });
  for (const x of $("#impIndice").querySelectorAll("a")) x.setAttribute("aria-current", String(x === a));
});
$("#iChiudi").onclick = impChiudi;
$("#imp").addEventListener("cancel", ev => { ev.preventDefault(); impChiudi(); });   // Esc: stessa conferma di «Chiudi»
$("#iSalva").onclick = impSalva;
$('#imp').addEventListener('close', () => applicaAspetto(preferenze));

/* Separatore del pannello: pointer capture evita salti quando il mouse esce dal bordo. */
async function salvaLarghezza(larghezza, chiave = 'larghezza_pannello') {
  const precedente = { ...preferenze };
  memorizzaAspetto({ ...preferenze, [chiave]: larghezza });
  try {
    const r = await post('/api/impostazioni', { interfaccia: { [chiave]: larghezza } });
    memorizzaAspetto(r.interfaccia);
  } catch (e) { memorizzaAspetto(precedente); msg('Larghezza non salvata: ' + e.message, 'e'); }
}
/* Separatore ridimensionabile: cfg = { chiave, pannello (selettore), verso (+1 se il pannello e' a sinistra del separatore),
   min, max() }. Trascinamento con pointer capture, tastiera con frecce/Home/End, doppio clic per il valore predefinito. */
function collegaSeparatore(sep, cfg) {
  let tr = null;
  sep.addEventListener('pointerdown', ev => {
    if (ev.button !== 0 || window.innerWidth <= 960) return;
    tr = { id: ev.pointerId, x: ev.clientX, larghezza: $(cfg.pannello).getBoundingClientRect().width, nuova: preferenze[cfg.chiave] };
    sep.setPointerCapture(ev.pointerId); document.body.classList.add('ridimensionando'); ev.preventDefault();
  });
  sep.addEventListener('pointermove', ev => {
    if (!tr || ev.pointerId !== tr.id) return;
    tr.nuova = Math.round(Math.max(cfg.min, Math.min(cfg.max(), tr.larghezza + cfg.verso * (ev.clientX - tr.x))));
    applicaAspetto({ ...preferenze, [cfg.chiave]: tr.nuova });
  });
  const fine = ev => {
    if (!tr || ev.pointerId !== tr.id) return;
    const larghezza = tr.nuova; tr = null; document.body.classList.remove('ridimensionando');
    if (sep.hasPointerCapture(ev.pointerId)) sep.releasePointerCapture(ev.pointerId);
    if (ev.type === 'pointercancel') applicaAspetto(preferenze); else salvaLarghezza(larghezza, cfg.chiave);
  };
  sep.addEventListener('pointerup', fine); sep.addEventListener('pointercancel', fine);
  sep.addEventListener('keydown', ev => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(ev.key)) return;
    ev.preventDefault();
    const piu = cfg.verso > 0 ? 'ArrowRight' : 'ArrowLeft';
    const l = ev.key === 'Home' ? cfg.min : ev.key === 'End' ? cfg.max() : preferenze[cfg.chiave] + (ev.key === piu ? 16 : -16);
    salvaLarghezza(Math.max(cfg.min, Math.min(cfg.max(), l)), cfg.chiave);
  });
  sep.addEventListener('dblclick', () => salvaLarghezza(ASPETTO_DEFAULT[cfg.chiave], cfg.chiave));
}
collegaSeparatore($('#ridimensiona'), { chiave: 'larghezza_pannello', pannello: '#ins', verso: -1, min: 280, max: () => limitePannello() });
collegaSeparatore($('#ridimensionaNav'), { chiave: 'larghezza_nav', pannello: '#lat', verso: 1, min: 180, max: () => limiteNav() || 480 });

/* Importa un file telematico SUC13 (XML) come nuova pratica: importa solo cio' che il programma sa riprodurre e dice il resto. */
async function importaXml(file) {
  if (S.writeBusy) return msg("Salvataggio in corso: attendi prima di importare.", "e");
  try {
    const r = await rete("/api/importa", { method: "POST", body: await file.arrayBuffer(), headers: { "Content-Type": "application/xml" } });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) return msg("Importazione non riuscita: " + (j.messaggio || j.codice || r.status), "e");
    await caricaPratiche(); await apri(j.pratica_id, "AN");
    const n = Object.entries(j.importato).map(([k, v]) => v + " " + k.replaceAll("_", " ")).join(", ");
    const resto = j.non_importato.concat(j.avvisi);
    msg("Importata: " + n + ". Verifica i dati." + (resto.length ? " Da reinserire o controllare: " + resto.join("; ") + "." : ""), resto.length ? "e" : "o");
  } catch (e) { msg("Importazione non riuscita: " + e.message, "e"); }
}
$("#bImporta").onclick = () => $("#fImporta").click();
$("#fImporta").onchange = ev => { const f = ev.target.files[0]; ev.target.value = ""; if (f) importaXml(f); };
$("#bNuova").onclick = wizApri;
$("#wAnnulla").onclick = () => $("#wiz").close();
$("#wIndietro").onclick = () => { W.passo--; wizRender(); };
$("#wAvanti").onclick = wizAvanti;
$("#bSalva").onclick = salvaTutto;
$("#bGenera").onclick = vaiFile;
$("#bControlla").onclick = async () => {
  if (!S.P) return; if (nMod() && !(await salvaTutto())) return;
  try { S.Q = await api("/api/pratiche/" + S.P.pratica_id + "/quadri"); } catch (e) { msg("Controllo non eseguito. " + e.message, "e"); return; }
  if (S.sel === 'FILE') S.sel = 'AN'; S.tab = "controlli"; render();
};
$('#homeNuova').onclick = wizApri;
$('#homeImporta').onclick = () => $('#fImporta').click();
$('#bHome').onclick = () => {
  if (S.writeBusy || (nMod() && !confirm('Ci sono modifiche non salvate. Tornare alla pagina iniziale senza salvarle?'))) return;
  S.gen++; S.P = null; S.Q = null; S.dirty.clear(); S.nuove.clear(); S.dichDirty.clear(); S.supDirty.clear(); S.fornitoreDirty = {};
  S.sel = 'AN'; S.tab = 'dati'; $('#vista').scrollTop = 0; $('#titolo').textContent = 'Nessuna pratica aperta'; render(); caricaPratiche();
};
// con una finestra aperta (Operazioni, procedura guidata, Calcolatrice, Guida...) Ctrl+S non salva la pratica: la finestra ha i suoi pulsanti
document.addEventListener("keydown", ev => { if ((ev.ctrlKey || ev.metaKey) && (ev.key === "s" || ev.key === "S")) { ev.preventDefault(); if (document.querySelector("dialog[open]")) return; salvaTutto(); } });
/* Scorciatoie per chi inserisce dati tutto il giorno (report grafica 07/11/2026, punto 10). «?» mostra l'elenco. */
const SCORCIATOIE = [["Ctrl+S", "Salva le modifiche"], ["Alt+N", "Nuova riga nel quadro"], ["Alt+D", "Duplica la riga selezionata"],
  ["Alt+PagGiù / Alt+PagSu", "Quadro successivo / precedente"], ["Ctrl+G", "Vai a un quadro (scrivi la sigla, es. EC)"],
  ["Alt+C", "Controlla la pratica"], ["Frecce, Home, Fine", "Righe della tabella"], ["Invio", "Apri la riga nel pannello"], ["Esc", "Dal pannello torna alla tabella"], ["F1", "Guida e istruzioni ufficiali"], ["?", "Questo elenco"]];
function mostraScorciatoie() {
  let d = $("#dScorciatoie");
  if (!d) { d = h("dialog", { id: "dScorciatoie", "aria-labelledby": "dScT" }, h("form", { method: "dialog" }, h("h2", { id: "dScT" }, "Scorciatoie da tastiera"),
    h("table", { class: "scorciatoie" }, h("tbody", {}, SCORCIATOIE.map(([k, t]) => h("tr", { class: "fisso" }, h("td", {}, h("kbd", {}, k)), h("td", {}, t))))),
    h("div", { class: "wiz-az" }, h("span", { class: "sp" }), h("button", { class: "pil" }, "Chiudi")))); document.body.append(d); }
  d.showModal();
}
function vaiAlQuadro() {
  const inp = h("input", { id: "vaiSigla", autocomplete: "off", list: "vaiQuadri", placeholder: "es. EC", class: "mono", maxlength: "4" });
  const dl = h("datalist", { id: "vaiQuadri" }, S.Q.quadri.map(x => h("option", { value: x.id }, x.titolo)));
  dialogo("dVai", "Vai al quadro", h("div", { class: "campo" }, h("label", { for: "vaiSigla" }, "Sigla del quadro"), inp, dl), "Vai", () => {
    const sigla = inp.value.trim().toUpperCase();
    if (!sigla) return "Scrivi la sigla del quadro, per esempio EC.";
    if (!S.Q.quadri.some(x => x.id === sigla)) return "Quadro " + sigla + " non trovato.";
    setTimeout(() => scegliQuadro(sigla), 0);
    return null;
  });
  inp.focus();
}
function quadriNavigabili() { return S.Q ? S.Q.quadri.filter(x => x.gruppo !== "lavoro" || x.id === "DV") : []; }
document.addEventListener("keydown", ev => {
  const inCampo = ev.target.closest && ev.target.closest("input, select, textarea, [contenteditable]");
  if (document.querySelector("dialog[open]")) return;
  if (ev.key === "?" && !inCampo && !ev.ctrlKey && !ev.altKey) { ev.preventDefault(); return mostraScorciatoie(); }
  if (!S.P) return;
  const q = quadro();
  if (ev.altKey && !ev.ctrlKey && (ev.key === "n" || ev.key === "N")) { if (q && q.coll && q.supportato) { ev.preventDefault(); aggiungiRiga(q); } return; }
  if (ev.altKey && !ev.ctrlKey && (ev.key === "d" || ev.key === "D")) { if (q && q.coll) { ev.preventDefault(); duplicaRiga(q); } return; }
  if (ev.altKey && !ev.ctrlKey && (ev.key === "c" || ev.key === "C")) { ev.preventDefault(); $("#bControlla").click(); return; }
  if (ev.altKey && (ev.key === "PageDown" || ev.key === "PageUp")) {
    const l = quadriNavigabili(), i = l.findIndex(x => x.id === S.sel); if (!l.length) return;
    ev.preventDefault(); scegliQuadro(l[(Math.max(0, i) + (ev.key === "PageDown" ? 1 : l.length - 1)) % l.length].id); return;
  }
  if ((ev.ctrlKey || ev.metaKey) && (ev.key === "g" || ev.key === "G")) {
    ev.preventDefault(); vaiAlQuadro();
  }
});
window.addEventListener("beforeunload", ev => { if (nMod()) { ev.preventDefault(); ev.returnValue = ""; } });
init();
/* il menu Operazioni si chiude cliccando fuori o con Esc */
document.addEventListener("click", ev => { for (const d of document.querySelectorAll("details.operazioni[open]")) if (!d.contains(ev.target)) d.open = false; });
document.addEventListener("keydown", ev => { if (ev.key === "Escape") for (const d of document.querySelectorAll("details.operazioni[open]")) { d.open = false; d.querySelector("summary").focus(); } });

/* ---------- Guida e Informazioni (come in ogni programma) ----------
   Istruzioni ufficiali dell'Agenzia (copie in fonti/, server: guida.py) aperte alla pagina dell'argomento; uso del programma;
   versione, componenti e novita'. Si apre con il pulsante «Guida» o con F1. */
const GUIDA = { dati: null, info: null };
async function datiGuida() { if (!GUIDA.dati) GUIDA.dati = await api("/api/guida"); return GUIDA.dati; }
function apriIstruzioni(doc, pagina) { window.open("/api/guida/" + doc + ".pdf#page=" + pagina, "_blank", "noopener"); }
function argomentoDelQuadro(id) { return GUIDA.dati && GUIDA.dati.argomenti.find(a => a.quadro === id); }
// Invio in un campo di Guida o Calcolatrice: il modulo lo tratterebbe come «Chiudi» e la finestra si chiuderebbe; qui non fa nulla
function invioNonChiude(ev) { if (ev.key === "Enter" && ev.target.tagName === "INPUT" && !ev.isComposing) ev.preventDefault(); }
async function apriGuida(scheda) {
  let d = $("#dGuida");
  if (!d) { d = h("dialog", { id: "dGuida", class: "guida", "aria-labelledby": "dGuidaT" }); document.body.append(d); }
  const schede = [["istruzioni", "Istruzioni ufficiali"], ["uso", "Uso del programma"], ["info", "Informazioni"]];
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
          h("span", { class: "pz " + (c.esito === "ok" ? "ok" : c.esito === "avviso" ? "am" : "er") }, c.esito || "?"), " ", h("b", {}, c.nome),
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
  catch (e) { if (mio !== CALC.seq) return; ris.removeAttribute("aria-busy"); calcMostraErrore(e.message); return; }
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
function calcMostraErrore(t) {
  CALC.ultimo = null;
  $("#calcRis").replaceChildren(h("p", { class: "calc-avv" }, "Stima: non sostituisce la dichiarazione né il controllo ufficiale."), h("p", { class: "err", id: "calcErrore" }, t));
}
function calcMostra(r) {
  const lista = (cls, voci) => voci && voci.length ? h("ul", { class: cls }, voci.map(v => h("li", {}, v))) : null;
  const imp = r.imposte || [];
  $("#calcRis").replaceChildren(...[
    h("p", { class: "calc-avv", id: "calcAvv" }, r.avvertenza),
    imp.length ? h("table", { class: "calc-imp", id: "calcImposte" }, h("tbody", {},
      imp.map(x => h("tr", { class: "fisso" }, h("td", {}, x.voce), h("td", { class: "n" }, x.testo))),
      h("tr", { class: "fisso tot" }, h("td", {}, "Totale stimato"), h("td", { class: "n", id: "calcTotale" }, r.totale_testo || "")))) : null,
    r.non_stimabile && r.non_stimabile.length ? [h("h3", {}, "Non stimabile"), lista("calc-ns", r.non_stimabile.map(m => "non stimabile: " + m))] : null,
    r.eredi && r.eredi.length ? [h("h3", {}, "Imposta di successione per erede"), ...r.eredi.map(e => h("details", { class: "calc-erede-ris" },
      h("summary", {}, e.nome + " (" + (e.grado_testo || e.grado) + ", quota " + e.quota + "): " + e.imposta),
      h("p", { class: "mut" }, "Franchigia " + e.franchigia + (e.disabile ? " (disabilità grave)" : "") + ", aliquota " + e.aliquota + "."),
      h("ol", {}, e.passaggi.map(p => h("li", {}, p.voce + ": " + p.valore)))))] : null,
    r.passaggi && r.passaggi.length ? [h("h3", {}, "Come si arriva al risultato"), lista("", r.passaggi)] : null,
    r.note && r.note.length ? [h("h3", {}, "Note"), lista("", r.note)] : null,
    r.assunzioni ? h("details", {}, h("summary", {}, "Ipotesi della stima"), lista("", r.assunzioni)) : null].flat().filter(Boolean));
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
  msg("Procedura guidata compilata con la data del decesso e " + r.operazioni.length + " eredi. Da completare: " + r.da_completare + ".", "o");
}
function apriCalcolatrice() {
  let d = $("#dCalc");
  if (!d) {
    d = h("dialog", { id: "dCalc", class: "calc", "aria-labelledby": "dCalcT" }, h("form", { method: "dialog", onkeydown: invioNonChiude },
      h("h2", { id: "dCalcT" }, "Calcolatrice rapida"),
      h("p", { class: "mut" }, "Stima delle imposte di successione con i motori di calcolo del programma. Non crea e non salva pratiche."),
      h("div", { class: "calc-corpo" }, h("div", { class: "calc-dati", id: "calcDati" }), h("div", { class: "calc-ris", id: "calcRis", "aria-live": "polite" })),
      h("div", { class: "wiz-az" },
        h("button", { type: "button", class: "gh", id: "calcAzzera", onclick: () => { CALC.dati = calcNuovi(); CALC.ultimo = null; calcDisegnaDati(); calcEsegui(); } }, "Azzera"),
        h("span", { class: "sp" }),
        h("button", { type: "button", class: "gh", id: "calcCrea", onclick: occupato("calcCrea", calcCreaPratica) }, "Crea una pratica da questi dati"),
        h("button", { class: "pil" }, "Chiudi"))));
    document.body.append(d);
  }
  if (!CALC.dati) CALC.dati = calcNuovi();
  calcDisegnaDati(); calcEsegui();
  if (!d.open) d.showModal();
  $("#calcData").focus();
}
$("#bCalc").onclick = () => apriCalcolatrice();
$("#homeCalc").onclick = () => apriCalcolatrice();
