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
const FONT_UI = { sistema: 'system-ui, "Segoe UI", sans-serif', segoe: '"Segoe UI", system-ui, sans-serif',
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
  const brand = $('#bHome'); if (brand) { brand.lastChild.textContent = 'Successioni' + (p.nome_studio ? ' · ' + p.nome_studio : ''); document.title = 'Successioni' + (p.nome_studio ? ' · ' + p.nome_studio : ''); }
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

async function api(url, opt) {
  const r = await fetch(url, opt);
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(j.messaggio || j.codice || r.statusText), { dati: j, stato: r.status });
  return j;
}
const post = (u, b) => api(u, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b) });
/* Il messaggio e' un riquadro mobile in basso (non sposta il layout) con pulsante di chiusura. Stile aggiunto da qui. */
document.head.append(h("style", {}, `#msg{position:fixed;left:50%;bottom:44px;transform:translateX(-50%);z-index:60;margin:0;max-width:min(760px,calc(100vw - 24px));
  display:flex;gap:12px;align-items:flex-start;white-space:pre-line;overflow-wrap:anywhere;max-height:40vh;overflow:auto}
  #msg[hidden]{display:none} #msg .mt{flex:1} #msg .x{flex:none;border:0;background:transparent;color:inherit;cursor:pointer;font:inherit;line-height:1;padding:2px 6px}
  #msg .x::before{content:"\\00d7";font-size:1.3em}`));
function msg(t, tipo) {
  const m = $("#msg"); m.className = tipo || ""; m.hidden = !t; m.replaceChildren();
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
function mostra(kind, v) {
  if (v === undefined || v === null) return "";
  if (typeof v === "object" && v.stato) return "[" + v.stato + "]";
  if (kind === "quota" && typeof v === "object") return v.num + "/" + v.den;
  if (kind === "data") return dataIt(String(v));
  return String(v);
}
function leggi(kind, t) {
  t = t.trim();
  if (t === "") return null;
  if (t === "?") return { stato: "da_confermare" };
  if (/^\[[a-z_]+\]$/.test(t)) return { stato: t.slice(1, -1) };
  if (kind === "quota") { const m = t.match(/^(\d+)\s*\/\s*(\d+)$/); return m ? { num: +m[1], den: +m[2] } : t; }
  if (kind === "data") return dataIso(t);
  if (kind === "importo" && /^-?\d+,\d+$/.test(t)) return t.replace(",", ".");   // 12,5 -> 12.5
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
    try { const imp = await api('/api/impostazioni'); memorizzaAspetto(imp.interfaccia); STUDIO.profilo = imp.profilo || {}; } catch (_) { /* l'app resta utilizzabile */ }
    STUDIO.archivio = i.archivio || '';
    await caricaPratiche(); renderSb(); aggiornaBottoni();
    try { const ultima = localStorage.getItem('successioni.ultima'); if (preferenze.avvio === 'ultima' && ultima && S.pratiche.some(p => p.id === ultima)) await apri(ultima); } catch (_) { /* resta l'elenco */ }
  } catch (e) { msg("Avvio non riuscito: " + e.message, "e"); }
}
async function caricaPratiche() {
  S.pratiche = await api("/api/pratiche");
  const ul = $("#lista"); ul.replaceChildren();
  if (!S.pratiche.length) ul.append(h("li", { class: "mut" }, "Nessuna pratica."));
  for (const p of S.pratiche) ul.append(h("li", {}, h("button", { title: p.titolo + " (rev. " + p.revisione + ")", "aria-current": S.P && S.P.pratica_id === p.id ? "true" : "false", onclick: () => apri(p.id) }, h("span", {}, p.titolo), h("span", { class: "mut" }, "rev. " + p.revisione))));
}
async function apri(id, sel) {
  try { localStorage.setItem('successioni.ultima', id); } catch (_) { /* facoltativo */ }
  if (S.writeBusy) { msg("Salvataggio in corso: attendi prima di cambiare pratica.", "e"); return; }
  if (nMod() && !confirm("Ci sono modifiche non salvate: continuare senza salvarle?")) return;
  S.gen++;   // invalida le risposte asincrone (es. codice fiscale) richieste per la pratica precedente
  S.dirty.clear(); S.nuove.clear(); S.dichDirty.clear(); S.supDirty.clear(); S.riga = null; S.tab = "dati"; S.salvata = null;
  S.fornitoreDirty = {};
  await ricarica(id);
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
  const pannello = aperta && S.sel !== 'FILE' && (S.sel !== 'AN' || S.tab !== 'dati');
  $("#app").classList.toggle("conIns", pannello); $("#ins").hidden = !pannello; $('#ridimensiona').hidden = !pannello;
  renderAlbero(); renderVista(); renderIns(); renderSb(); aggiornaBottoni();
}
function aggiornaBottoni() {
  const n = nMod();
  $("#bSalva").disabled = !n || S.writeBusy; $("#bSalva").textContent = S.writeBusy ? "Salvataggio…" : n ? "Salva (" + n + ")" : "Salva";
  $("#bControlla").disabled = !S.P; $("#bGenera").disabled = !S.P; $("#bGenera").title = "Apri l'area unica File e invio della pratica";
  $('#bGenera').setAttribute('aria-pressed', String(S.sel === 'FILE'));
  $("#bControlla").textContent = S.Q && S.Q.rilievi.length ? "Controlla (" + S.Q.rilievi.length + ")" : "Controlla";
}
function renderSb() {
  const sb = $("#sb"); sb.replaceChildren();
  const arch = STUDIO.archivio ? h("span", { class: "arch", title: STUDIO.archivio, style: "font-weight:600" }, "Archivio: " + STUDIO.archivio.split(/[\\/]/).filter(Boolean).pop()) : null;
  if (!S.P) { sb.append(...[arch, h("span", {}, "Nessuna pratica aperta")].filter(Boolean)); return; }
  const n = S.Q.rilievi.length;
  sb.append(...[arch, h("span", {}, "Revisione " + S.P.revisione),
    S.salvata ? h("span", { class: "ok" }, "Salvata alle " + S.salvata) : null,
    nMod() ? h("span", { style: "color:var(--am)" }, nMod() + (nMod() === 1 ? " modifica non salvata" : " modifiche non salvate")) : null,
    n ? h("button", { onclick: () => { if (S.sel === 'FILE') S.sel = 'AN'; S.tab = "controlli"; render(); } }, n + (n === 1 ? " rilievo" : " rilievi")) : h("span", {}, "Nessun rilievo"),
    (S.Q.avvisi || []).length ? h("button", { style: "color:var(--am)", onclick: () => { if (S.sel === 'FILE') S.sel = 'AN'; S.tab = "controlli"; render(); } }, S.Q.avvisi.length + (S.Q.avvisi.length === 1 ? " avviso" : " avvisi")) : null,
    h("span", {}, S.Q.finalizzabile ? "Finalizzabile" : "Non finalizzabile" + ((S.Q.blocchi_finalizzazione || []).length ? ": file XML completo non generato" : "")),
    h("span", {}, "Controllo ufficiale: vedi File e invio")].filter(Boolean));
}
function vaiFile() { if (!S.P) return; S.sel = 'FILE'; S.riga = null; S.tab = 'dati'; $('#vista').scrollTop = 0; render(); }
function scegliQuadro(id) { S.sel = id; S.riga = null; S.tab = 'dati'; $('#vista').scrollTop = 0; render(); }

/* ---------- albero dei quadri ---------- */
function renderAlbero() {
  const nav = $("#albero"); nav.replaceChildren();
  if (!S.Q) return;
  nav.append(h('button', { class: 'voce nav-file', id: 'navFile', title: 'File e invio', 'aria-current': S.sel === 'FILE' ? 'page' : 'false', onclick: vaiFile },
    h('span', { class: 'sigla' }, '↗'), h('span', {}, 'File e invio')));
  for (const [g, nome] of [["frontespizio", "Frontespizio"], ["quadri", "Quadri"], ["riepiloghi", "Riepiloghi"], ["lavoro", "Tabella di lavoro"]]) {
    nav.append(h("div", { class: "gruppo" }, nome));
    for (const q of S.Q.quadri.filter(x => x.gruppo === g)) {
      const st = q.stato;
      const testo = st === "rilievi" ? q.rilievi + (q.rilievi === 1 ? " rilievo" : " rilievi") : (q.righe && st === "compilato" ? q.righe + (q.righe === 1 ? " riga" : " righe") : STATI[st]);
      nav.append(h("button", { class: "voce", "data-stato": st, "data-q": q.id, title: q.id + " — " + q.titolo + (testo ? " (" + testo + ")" : ""), "aria-current": S.sel === q.id ? "true" : "false", onclick: () => scegliQuadro(q.id) },
        h("span", { class: "sigla" }, q.id), h("span", { class: "testi" }, h("span", { class: "nome" }, q.titolo), h("span", { class: "st" }, testo))));
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
    el = h("select", { "aria-label": campo }, h("option", { value: "" }, ""), kind.slice(5).split("|").map(o => h("option", { value: o }, nomeVal(coll, campo, o))));
    el.value = val || "";
  } else if (kind.startsWith("ref:")) {
    const rc = kind.slice(4);
    el = h("select", { "aria-label": campo }, h("option", { value: "" }, ""), (S.P.dati[rc] || []).map(e => h("option", { value: e.id }, etichetta(rc, e))));
    el.value = val || "";
  } else {
    const lista = listaSuggerimenti(coll + "." + campo);
    el = h("input", { "aria-label": campo, autocomplete: "off", list: lista, maxlength: MAX_LUNGHEZZA[coll + "." + campo], class: kind === "cf" ? "mono" : (kind === "importo" || kind === "quota" ? "num" : ""), placeholder: kind === "quota" ? "1/2" : kind === "data" ? "GG/MM/AAAA" : "" });
    el.value = mostra(kind, val);
  }
  if (path) el.dataset.path = path;
  if (err.length) el.classList.add("bad");
  const f = () => onMod(campo, leggi(kind, el.value));
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
const testoVoce = (sd, o) => sd.senza_codice ? o.etichetta : o.valore + " — " + o.etichetta;

/* Campo a scelta guidata (S.schema.strutturati, definito in schema.py): menu con etichette e aiuto della voce scelta.
   Un valore gia' presente ma non nell'elenco (o uno stato come [da_confermare]) resta visibile e non viene perso.
   Il menu occupa la larghezza disponibile, il testo lungo si tronca con «...» e si legge per intero nel suggerimento (title). */
function campoStrutturato(sd, val, onMod, path) {
  const err = path ? rilievi().filter(r => r.percorso === path) : [];
  const grezzo = val === undefined || val === null ? "" : (typeof val === "object" && val.stato ? "[" + val.stato + "]" : String(val));
  const attuale = riconosciVoce(sd, grezzo);
  const el = h("select", { "aria-label": sd.etichetta, style: "width:100%;min-width:0;max-width:100%;text-overflow:ellipsis" },
    h("option", { value: "" }, "(non indicato)"),
    sd.opzioni.map(o => h("option", { value: o.valore, title: testoVoce(sd, o) }, testoVoce(sd, o))),
    attuale && !sd.opzioni.some(o => o.valore === attuale) ? h("option", { value: attuale }, attuale + " (valore non previsto)") : null);
  el.value = attuale;
  if (path) el.dataset.path = path;
  if (err.length) el.classList.add("bad");
  const dett = h("div", { class: "mut aiuto-voce", style: "font-size:0.8846rem;margin-top:2px" });
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
  main.append(h("h1", {}, (q.id === "AN" || q.id === "DV" ? "" : q.id + " — ") + q.titolo));
  main.append(h("div", { class: "sottotitolo" }, q.nota || (q.vista === "tabella" || q.vista === "documenti" ? (q.righe + (q.righe === 1 ? " riga" : " righe")) : "")));
  if (!q.attivo && q.supportato) main.append(h("div", { class: "nota" }, "Questo quadro non è selezionato per la dichiarazione. ", h("button", { class: "lk", onclick: () => impostaQuadro(q.id, true) }, "Seleziona il quadro")));
  if (q.rilievi && q.vista !== "frontespizio") main.append(h("div", { class: "avv" }, h("b", {}, q.rilievi + (q.rilievi === 1 ? " rilievo" : " rilievi")), h("span", { style: "flex:1" }, rilievi().find(r => r.quadro === q.id).messaggio), h("button", { class: "gh", onclick: () => { S.tab = "controlli"; renderIns(); } }, "Vedi controlli")));
  if (q.vista === "frontespizio") renderFront(main);
  else if (q.vista === "derivato") main.append(h("div", { class: "nota" }, q.nota || "Quadro generato automaticamente dal programma."));
  else if (q.vista === "non_supportato") renderNonSupp(main, q);
  else { renderTabella(main, q); if (q.vista === "documenti") renderAllegati(main); }
  main.scrollTop = y;
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

function renderTabella(main, q) {
  const campi = S.schema.collezioni[q.coll];
  const righe = righeQuadro(q);
  const t = h("table", { role: "grid", "aria-label": q.titolo });
  t.append(h("thead", {}, h("tr", {}, q.colonne.map(c => h("th", { class: ["quota", "importo", "rendita", "valore"].includes(c) ? "n" : "" }, lbl(q.coll, c, q.id))))));
  const tb = h("tbody"); t.append(tb);
  righe.forEach((r, i) => {
    const id = r.e && r.e.id; const base = id ? q.coll + "[" + id + "]" : null;
    const rilRiga = base ? rilievi().filter(x => x.percorso === base || x.percorso.startsWith(base + ".")) : [];
    const tr = h("tr", { tabindex: (S.riga && righe.some(x => x.key === S.riga) ? S.riga === r.key : i === 0) ? "0" : "-1", "aria-selected": S.riga === r.key ? "true" : "false", class: (r.nuova || S.dirty.has(r.key)) ? "mod" : "", "data-key": r.key,
      onclick: () => selezionaRiga(r.key, "riga"),
      onkeydown: ev => tastiTabella(ev, tr, r.key) });
    q.colonne.forEach((c, j) => {
      const kind = campi[c]; const v = valRiga(r, c);
      let txt = kind.startsWith("enum:") && typeof v === "string" ? nomeVal(q.coll, c, v) : mostra(kind, v);
      if (c === "grado_parentela" && typeof v === "string" && v) {   // il grado si legge per nome (menu dei codici), non come codice
        const sdg = struttDi(q.coll, c, null), og = sdg && sdg.opzioni.find(x => x.valore === riconosciVoce(sdg, v));
        if (og) txt = og.etichetta;
      }
      if (kind.startsWith("ref:") && v) { const e = (S.P.dati[kind.slice(4)] || []).find(x => x.id === v); if (e) txt = etichetta(kind.slice(4), e); }
      const errCampo = base && rilievi().some(x => x.percorso === base + "." + c);
      const td = h("td", { class: ["quota", "importo", "rendita", "valore"].includes(c) ? "n" : "", title: txt }, j === 0 && rilRiga.length ? h("span", { class: "punto", title: rilRiga.map(x => x.messaggio).join("; ") }) : null, errCampo ? h("span", { class: "pz er" }, "da correggere") : txt);
      tr.append(td);
    });
    tb.append(tr);
  });
  if (!righe.length) tb.append(h("tr", {}, h("td", { colspan: q.colonne.length, class: "mut" }, "Nessuna riga. Usa «Aggiungi riga».")));
  main.append(h("div", { class: "tab" }, t));
  main.append(h("div", { class: "barra" }, h("button", { class: "pil", onclick: () => aggiungiRiga(q) }, "Aggiungi riga"),
    h("span", { class: "mut" }, "Quote 1/2 · importi con il punto (1234.50) · dato non noto: ? oppure [assente], [zero], [non_applicabile]")));
}
function aggiungiRiga(q) {
  const key = "n:" + crypto.randomUUID();
  S.nuove.set(key, { q: q.id, coll: q.coll, id: nuovoId(q.coll), campi: { ...q.preset } });
  S.riga = key; S.tab = "dati"; renderVista(); renderIns(); aggiornaBottoni(); renderSb();
  if (!q.attivo && q.supportato) msg("Il quadro " + q.id + " non è selezionato: si seleziona da solo quando salvi la nuova riga.", "o");
  const primo = $("#ins .rg input, #ins .rg select"); if (primo) primo.focus();
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
  S.riga = key; S.tab = "dati"; renderVista(); renderIns();
  if (dove === "pannello") { const primo = $("#ins .rg input, #ins .rg select, #ins .rg textarea"); if (primo) { primo.focus(); return; } }
  if (dove) { const tr = rigaDaFocalizzare(key); if (tr) tr.focus({ preventScroll: true }); }
  if (window.innerWidth <= 960) $("#ins").scrollIntoView({ block: "start" });   // su schermo stretto il pannello sta sotto la tabella
}
function tornaTabella() {
  const tr = S.riga && rigaDaFocalizzare(S.riga) || document.querySelector("#vista tbody tr[tabindex]");
  if (tr) { tr.focus({ preventScroll: true }); tr.scrollIntoView({ block: "center" }); }
}

/* ---------- ispettore ---------- */
function renderIns() {
  const ins = $("#ins"); ins.replaceChildren();
  if (!S.P) return;
  if (S.tab === 'file') { vaiFile(); return; } // compatibilita' con collegamenti precedenti
  if (S.sel === 'FILE') return;
  const nr = rilievi().length;
  const seg = h("div", { class: "seg", role: "tablist" }, [["dati", "Dati"], ["controlli", "Controlli" + (nr ? " (" + nr + ")" : "")], ["cronologia", "Cronologia"]].map(([k, n]) =>
    h("button", { role: "tab", "aria-selected": S.tab === k ? "true" : "false", onclick: () => { S.tab = k; render(); } }, n)));
  ins.append(seg);
  if (S.tab === "dati" && S.riga) ins.append(h("button", { class: "lk solo-mobile", onclick: tornaTabella }, "↑ Torna alla tabella"));
  if (S.tab === "dati") insDati(ins); else if (S.tab === "controlli") insControlli(ins); else if (S.tab === "file") insFile(ins); else insCronologia(ins);
}
function rigaSelezionata() {
  const q = quadro(); if (!q || !q.coll || !S.riga) return null;
  return righeQuadro(q).find(r => r.key === S.riga) || null;
}
function insDati(ins) {
  const q = quadro(); const r = rigaSelezionata();
  if (!q || !q.coll) { ins.append(h("p", { class: "mut" }, q && q.vista === "frontespizio" ? "I dati del frontespizio si modificano nelle schede al centro." : "Questo quadro non ha righe da modificare.")); return; }
  if (!r) { ins.append(h("p", { class: "mut" }, "Seleziona una riga della tabella oppure aggiungine una.")); return; }
  const campi = S.schema.collezioni[q.coll]; const id = r.e ? r.e.id : r.nuova.id;   // anche le righe nuove hanno data-path (per evidenziare l'errore al salvataggio)
  ins.append(h("h3", {}, r.nuova ? "Nuova riga" : etichetta(q.coll, r.e)));
  for (const x of rilievi().filter(x => id && x.percorso === q.coll + "[" + id + "]")) ins.append(h("div", { class: "e", style: "color:var(--er);margin:0 0 6px" }, x.messaggio));
  const visibili = q.campi ? new Set(q.campi) : (((S.schema.ordine || {})[q.id]) ? new Set(S.schema.ordine[q.id]) : null);   // solo i campi pertinenti al quadro; uno gia' valorizzato resta visibile
  const ordine = ordinati(q.id, Object.keys(campi));
  for (const [comune, provincia] of [['comune', 'provincia'], ['luogo_nascita', 'provincia_nascita']]) {
    void comune; void provincia;   // provincia e comune seguono gia' l'ordine ufficiale (provincia prima del comune)
  }
  for (const c of ordine) { const kind = campi[c];
    const vv = valRiga(r, c);
    if (visibili && !visibili.has(c) && (vv === undefined || vv === null || vv === "")) continue;
    if (q.coll === "persone" && c === "relazione_con_defunto" && struttDi("persone", "grado_parentela")) {   // duplica il grado (menu): si nasconde se vuota o uguale
      const rel = String(vv || "").trim();
      if (!rel || rel === String(valRiga(r, "grado_parentela") || "").trim()) continue;
    }
    const tipoBene = q.coll === "beni" ? valRiga(r, "tipo")
      : q.coll === "devoluzioni" ? ((S.P.dati.beni || []).find(b => b.id === valRiga(r, "bene_id")) || {}).tipo : null;
    const sd = struttDi(q.coll, c, tipoBene);
    const modificaCampo = (campo, v) => {
      const scrivi = (c2, x) => {
        if (r.nuova) r.nuova.campi[c2] = x;
        else { const d = S.dirty.get(r.key) || { coll: q.coll, id, campi: {} }; d.campi[c2] = x; S.dirty.set(r.key, d); }
      };
      const gradoPrima = campo === "grado_parentela" ? String(valRiga(r, "grado_parentela") || "") : "";
      scrivi(campo, v);
      // il grado (menu dei codici) e la «relazione» dicono la stessa cosa e l'esportazione li confronta: la relazione resta una
      // nota interna allineata al grado (se vuota o uguale al grado precedente); il campo si vede solo se contiene altro
      if (q.coll === "persone" && campo === "grado_parentela") {
        const rel = String(valRiga(r, "relazione_con_defunto") || "").trim();
        if (!rel || rel === gradoPrima) scrivi("relazione_con_defunto", v || null);
      }
      renderVista(); aggiornaBottoni(); renderSb();
      if ((q.coll === "beni" && campo === "tipo") || (q.coll === "devoluzioni" && campo === "bene_id")) renderIns();   // cambia l'elenco dei diritti
      if (q.coll === "persone" && campo === "codice_fiscale")
        suggerisciDaCF(v, r.e ? r.e.ruolo : (r.nuova && r.nuova.campi.ruolo), c2 => valRiga(r, c2), scrivi, () => String(valRiga(r, "codice_fiscale") || "").trim().toUpperCase() === v.trim().toUpperCase()).then(res => {
          if (res.testo) msg(res.testo, res.riempiti.length ? "o" : "e");
          if (res.riempiti.length) { renderVista(); renderIns(); aggiornaBottoni(); renderSb(); }
        });
    };
    const w = sd && sd.opzioni ? campoStrutturato(sd, valRiga(r, c), v => modificaCampo(c, v), id ? q.coll + "[" + id + "]." + c : null)
      : campoInput(q.coll, id, c, kind, valRiga(r, c), modificaCampo);
    const aiuto = (S.schema.aiuti || {})[q.coll + "." + c];
    if (aiuto) w.append(h("div", { class: "mut", style: "font-size:0.8846rem;margin-top:2px" }, aiuto));
    ins.append(h("div", { class: "rg" }, h("label", {}, lbl(q.coll, c, q.id)), w));
  }
  renderStrutturati(ins, q, r);
  const az = h("div", { class: "az" }, h("button", { class: "pil", onclick: salvaTutto }, "Salva"));
  const supKey = q.coll + ':' + (r.e ? r.e.id : r.nuova.id);
  if (r.nuova || S.dirty.has(r.key) || S.supDirty.has(supKey)) az.append(h("button", { class: "gh", onclick: () => { r.nuova ? S.nuove.delete(r.key) : S.dirty.delete(r.key); S.supDirty.delete(supKey); if (r.nuova) S.riga = null; render(); } }, "Annulla modifiche"));
  if (r.e) az.append(h("button", { class: "lk", style: "color:var(--er)", onclick: async () => {
    if (S.writeBusy) return msg("Salvataggio in corso: attendi prima di eliminare la riga.", "e");
    if (confirm("Eliminare la riga?")) await salvaOps([{ op: "remove", coll: q.coll, id }], () => {
      S.dirty.delete(r.key); S.supDirty.delete(supKey); S.riga = null;
    });
  } }, "Elimina riga"));
  ins.append(az, h("p", { class: "mut mono", style: "margin-top:10px" }, r.e ? r.e.id : ""));
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
    ins.append(h('div', { class: 'mut', style: 'font-size:0.8846rem;margin-top:4px' }, sd.aiuto));
    if (bene && ['P', 'X', 'Z'].includes(attuale) && quadroBene(bene) !== 'EC')
      ins.append(h('div', { class: 'nota', style: 'margin:6px 0' }, 'Il bene collegato non è un fabbricato del quadro EC: i codici P, X, Z sono ammessi solo lì e l\'esportazione segnalerà un errore.'));
    const rd = (S.schema.strutturati || {})['devoluzioni.riduzioni'];
    ins.append(h('h3', {}, 'Riduzione art. 25 comma 1'));
    ins.append(campoStrutturato(rd, valore('riduzioni'), v => scrivi('riduzioni', v), null));
    ins.append(h('div', { class: 'mut', style: 'font-size:0.8846rem;margin-top:4px' }, rd.aiuto));
    if (valore('riduzioni') && bene)
      ins.append(h('div', { class: 'nota', style: 'margin:6px 0' }, 'Indica anche il valore delle precedenti successioni nel pannello del bene collegato (' + etichetta('beni', bene) + ').'));
    return;
  }
  if (q.coll === 'beni') {
    const vp = (S.schema.strutturati || {})['beni.valore_prec_succ'];
    const inp = h('input', { id: 'vps_' + id, class: 'num', autocomplete: 'off', 'aria-label': vp.etichetta, value: valore('valore_prec_succ') == null ? '' : String(valore('valore_prec_succ')),
      oninput: ev => scrivi('valore_prec_succ', leggi('importo', ev.target.value)) });
    ins.append(h('h3', {}, 'Precedenti successioni o donazioni'), h('div', { class: 'rg' }, h('label', { for: 'vps_' + id }, vp.etichetta), h('div', {}, inp, h('div', { class: 'mut', style: 'font-size:0.8846rem;margin-top:2px' }, vp.aiuto))));
  }
  if (q.coll === 'persone') {
    const cb = h('input', { type: 'checkbox', 'aria-label': 'portatore handicap', onchange: ev => scrivi('portatore_handicap', ev.target.checked) });
    cb.checked = valore('portatore_handicap') === true;
    ins.append(h('label', { class: 'chk' }, cb, 'Portatore di handicap (come documentato)'));
    // rinunciatari, enti e residenza estera (docs/regole/soggetti_ea.md)
    const rin = h('input', { type: 'checkbox', 'aria-label': 'rinunciatario', onchange: ev => scrivi('rinuncia', ev.target.checked ? true : null) });
    rin.checked = valore('rinuncia') === true;
    ins.append(h('label', { class: 'chk' }, rin, 'Rinunciatario (la rinuncia e\' registrata: indica gli estremi dell\'atto)'));
    const den = h('input', { 'aria-label': 'denominazione', value: valore('denominazione') || '', oninput: ev => scrivi('denominazione', ev.target.value.trim() || null) });
    ins.append(h('label', {}, 'Denominazione (solo enti: gradi 35, 37, 38, 39)', den));
    const oggetto = (campo, titolo, campi) => {
      ins.append(h('h3', {}, titolo));
      for (const [c, et] of campi) {
        const el = h('input', { 'aria-label': titolo + ': ' + et, value: (valore(campo) || {})[c] ?? '', oninput: ev => {
          const o = { ...(valore(campo) || {}) }; const t = ev.target.value.trim(); if (!t) delete o[c]; else o[c] = t;
          scrivi(campo, Object.keys(o).length ? o : null); } });
        ins.append(h('label', {}, et, el));
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
    ins.append(h('h3', {}, titolo));
    const righe = valore(campo) || [];
    righe.forEach((voce, i) => {
      const box = h('div', { class: 'grp', style: 'padding:8px;margin:6px 0' });
      for (const [c, tipo] of campi) box.append(h('label', {}, lbl(q.coll, c), campoInput(q.coll, null, c, tipo, voce[c], (k, v) => {
        const nuove = structuredClone(valore(campo) || []); nuove[i][k] = v; scrivi(campo, nuove);
      })));
      box.append(h('button', { onclick: () => { scrivi(campo, righe.filter((_, j) => j !== i)); renderIns(); } }, 'Rimuovi ' + titolo.toLowerCase()));
      ins.append(box);
    });
    ins.append(h('button', { onclick: () => { scrivi(campo, [...righe, structuredClone(predefinito)]); renderIns(); } }, 'Aggiungi ' + titolo.toLowerCase()));
  };
  if (q.coll === 'passivita') tabella('ripartizione', 'Ripartizione', [['persona_id', 'ref:persone'], ['quota', 'quota']], { persona_id: '', quota: '1/1' });
  if (q.id === 'EN') tabella('immobili_aziendali', 'Immobile aziendale', [['bene_id', 'ref:beni']], { bene_id: '' });
  if (q.id === 'EC') tabella('graffati', 'Immobile graffato', [['sezione', 'str'], ['foglio', 'str'], ['particella', 'str'], ['subalterno', 'str']], {});
  if (q.id === 'EB' || q.id === 'EC') {
    tabella('estremi_trascrizione', 'Trascrizione', [['ufficio', 'str'], ['registro_particolare', 'str'], ['anno', 'str']], {});
    tabella('estremi_registrazione', 'Registrazione', [['ufficio', 'str'], ['anno', 'str'], ['volume', 'str'], ['numero', 'str']], {});
  }
}
function insControlli(ins) {
  const q = S.Q;
  ins.append(h("p", { class: "mut" }, q.ambito + (q.finalizzabile ? ". Finalizzabile." : ". Non finalizzabile.")));
  for (const b of (q.blocchi_finalizzazione || [])) ins.append(h("div", { class: "nota", style: "margin:0 0 8px" }, b.messaggio));
  // avvisi che non impediscono la finalizzazione (es. visure catastali vecchie o senza data)
  for (const a of (q.avvisi || [])) ins.append(h("div", { class: "nota", style: "margin:0 0 8px", role: "status" }, h("b", {}, "Avviso: "), a.messaggio));
  if (!q.rilievi.length) { ins.append(h("p", { class: "ok", style: "color:var(--ok);font-weight:600" }, "Nessun rilievo sui dati inseriti.")); return; }
  const ul = h("ul", { class: "rl" });
  for (const r of q.rilievi) ul.append(h("li", {}, h("button", { onclick: () => vaiA(r) }, h("span", { class: "sigla", style: "background:var(--er-b)" }, r.quadro), h("span", {}, h("div", {}, r.messaggio), h("div", { class: "cod" }, r.codice + " · " + r.percorso)))));
  ins.append(ul);
}
async function insCronologia(ins) {
  ins.append(h("p", { class: "mut" }, "Ogni salvataggio crea una revisione. Il ripristino non cancella la cronologia."));
  const lista = await api("/api/pratiche/" + S.P.pratica_id + "/revisioni");
  if (S.tab !== "cronologia") return;
  for (const x of lista.slice().reverse()) {
    const b = x.n !== S.P.revisione ? h("button", { class: "gh", style: "margin-top:4px", onclick: async () => {
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
  return h("div", { class: "rg", style: "grid-template-columns:120px 1fr" }, h("span", { class: "etichetta" }, nome), h("div", {}, h("span", { class: "pz " + (PILLOLE[stato] || "") , style: PILLOLE[stato] ? "" : "background:var(--grigio)" }, String(stato).replaceAll("_", " ")), extra ? h("div", { class: "mut", style: "font-size:0.9231rem;margin-top:3px" }, extra) : null));
}
async function insFile(dest) {
  const pid = S.P.pratica_id;
  const griglia = h('div', { class: 'file-griglia', id: 'fileContenuto' }); dest.append(griglia);
  let st;
  try { st = await api('/api/pratiche/' + pid + '/elaborati'); }
  catch (e) { if (griglia.isConnected) griglia.append(h('p', { class: 'err' }, e.message)); return; }
  if (S.sel !== 'FILE' || S.P.pratica_id !== pid || !griglia.isConnected) return;
  const ex = st.export, ct = st.controllo_ufficiale;
  const stato = h('section', { class: 'grp' }, h('h2', {}, 'Stato della dichiarazione'));
  stato.append(riga_stato('Dati', st.dati.stato, st.dati.rilievi + ' rilievi'),
    riga_stato('File XML', ex.stato, ex.generato ? (ex.completo ? 'Completo nel perimetro supportato' : 'Bozza tecnica: non trasmissibile') : 'Nessun file generato'),
    riga_stato('Schema XSD', st.xsd.stato), riga_stato('Controllo ufficiale', ct.stato, ct.versione_controllo),
    riga_stato('Trasmissione', st.trasmissione.stato, st.trasmissione.nota));
  if (ex.versioni) stato.append(h('p', { class: 'mut', style: 'font-size:0.9231rem' }, 'Versioni del file: programma ' + ex.versioni.applicazione + ' · regole ' + ex.versioni.regole +
    ' · specifiche ' + ex.versioni.specifiche_suc + (ct.versione_controllo ? ' · controllo ' + ct.versione_controllo : '')));
  if (ct.azione_richiesta) stato.append(h('p', { class: 'nota', style: 'white-space:pre-wrap' }, ct.azione_richiesta));
  const fornitore = h('section', { class: 'grp', id: 'fornitore' }, h('h2', {}, 'Fornitore e impegno alla trasmissione'),
    h('p', { class: 'mut' }, 'Chi presenta il file: dichiarante o intermediario. Il profilo si compila una volta per questa pratica.'));
  const profilo = { ...(S.P.dati.opzioni.fornitore || {}), ...S.fornitoreDirty };
  const modifica = (k, valore) => { S.fornitoreDirty[k] = valore; aggiornaBottoni(); renderSb(); };
  const cfIn = h('input', { 'aria-label': 'Codice fiscale del fornitore', class: 'mono', value: profilo.cf || '',
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
  const elaborati = h('section', { class: 'grp' }, h('h2', {}, 'Generazione e controllo'));
  const esegui = async scopo => {
    if (S.writeBusy) return;
    try {
      if (nMod() && !(await salvaTutto())) return;
      const r = await post('/api/pratiche/' + pid + '/esporta', { scopo });
      const motivi = [...(r.quadri_mancanti || []).map(x => x.messaggio), ...(r.non_supportato || []), ...(r.errori || []).map(x => x.messaggio)];
      if (!r.generato) msg('File non generato: ' + motivi.slice(0, 3).join(' | ') + '. Nessun file parziale è stato prodotto.', 'e');
      else msg((r.completo ? 'File generato e valido per lo schema.' : 'Bozza tecnica generata. ' + r.avvertenza)
        + ((r.avvisi || []).length ? ' Avvertenze: ' + r.avvisi.map(a => a.messaggio).join(' | ') : ''), r.completo ? 'o' : 'e');
      if (r.backup && r.backup.errore) msg('Attenzione: backup automatico non riuscito (' + r.backup.errore + ')', 'e');
      else if (r.backup && r.backup.eseguito) STUDIO.ultimoBackup = r.backup.nome;
      if (S.P.pratica_id === pid) { await ricarica(); render(); }
    } catch (e) { msg(e.message, 'e'); }
  };
  elaborati.append(h('p', { class: 'mut' }, 'Genera il file quando i dati sono pronti. La bozza tecnica conserva evidenza dei limiti e non è trasmissibile.'),
    h('div', { class: 'az' }, h('button', { class: 'pil', onclick: () => esegui('completo') }, 'Genera file'),
      h('button', { class: 'gh', onclick: () => esegui('bozza_tecnica') }, 'Genera bozza tecnica')));
  if (ex.generato) elaborati.append(h('div', { class: 'az' },
    h('a', { href: '/api/pratiche/' + pid + '/file.xml?job=' + ex.job_id, download: '' }, 'Scarica XML'),
    h('a', { href: '/api/pratiche/' + pid + '/stampa?job=' + ex.job_id, target: '_blank', rel: 'noopener' }, 'Stampa prospetto')));
  elaborati.append(h('div', { class: 'az' }, h('button', { class: 'gh', disabled: ex.stato !== 'aggiornato' || !ex.generato || !ex.completo, onclick: async () => {
    if (nMod()) return msg('Salva le modifiche e rigenera il file prima della stampa.', 'e');
    try { const r = await post('/api/pratiche/' + pid + '/stampa-modello', {}); msg('Modello ministeriale generato (' + r.pagine + ' pagine). Prova locale: controllane il contenuto prima di usarlo.', 'o'); window.open('/api/pratiche/' + pid + '/stampa-modello.pdf', '_blank', 'noopener'); }
    catch (e) { msg(e.message, 'e'); }
  } }, 'Stampa modello ministeriale')));
  if (ct.stato === 'positivo' && ct.job_adattatore) elaborati.append(h('div', { class: 'az' },
    h('a', { href: '/api/pratiche/' + pid + '/file.dcm', download: '' }, 'Scarica file controllato (.dcm)')));
  elaborati.append(h('div', { class: 'az' }, h('button', { class: 'gh', disabled: ex.stato !== 'aggiornato' || !ex.generato, onclick: async () => {
    if (nMod()) return msg('Salva le modifiche e rigenera il file prima del controllo.', 'e');
    try { const r = await post('/api/pratiche/' + pid + '/controllo-ufficiale', {}); msg('Controllo ufficiale: ' + r.stato_controllo + ' (' + r.esito + ').', r.stato_controllo === 'positivo' ? 'o' : 'e'); }
    catch (e) { msg(e.message, 'e'); }
    if (S.P.pratica_id === pid && S.sel === 'FILE') renderVista();
  } }, 'Esegui controllo ufficiale')));
  const invio = h('section', { class: 'grp intera', id: 'invioPratica' }, h('h2', {}, 'Invio e ricevute'));
  griglia.append(stato, fornitore, elaborati, invio);
  await renderInvio(invio, ex);
}
/* Invio: copia congelata -> conferma -> trasmissione. La modalita' «prova» usa un servizio FITTIZIO locale: non invia nulla all'Agenzia. */
async function renderInvio(ins, ex) {
  const pid = S.P.pratica_id; const base = "/api/pratiche/" + pid + "/invio";
  ins.append(h("h3", { style: "margin-top:14px" }, "Invio"),
    h("div", { class: "nota", style: "margin:4px 0" }, "PROVA SIMULATA: il programma non trasmette nulla all'Agenzia delle Entrate. L'invio reale si esegue con gli strumenti ufficiali (modalità manuale) e si registra qui."));
  let copie = [];
  try { copie = (await api(base)).copie; } catch (e) { ins.append(h("p", { class: "err" }, e.message)); return; }
  const ricarica = () => { if (S.sel === "FILE") renderVista(); };
  const chiama = async (url, corpo, ok) => { try { const r = await post(url, corpo); msg(ok(r), "o"); } catch (e) { msg(e.message, "e"); } ricarica(); };
  ins.append(h("div", { class: "az" }, h("button", { class: "pil", disabled: ex.stato !== "aggiornato" || !ex.completo, title: "Congela il file XML completo con il controllo ufficiale associato",
    onclick: () => chiama(base + "/prepara", { chiave_richiesta: "prep-" + crypto.randomUUID() }, r => "Copia preparata. " + (r.azione_richiesta || "")) }, "Prepara invio")));
  const c = copie[0];
  if (!c) { ins.append(h("p", { class: "mut", style: "font-size:0.9231rem" }, "Nessuna copia preparata. Serve un file completo e un controllo ufficiale positivo.")); return; }
  const d = c.dettaglio || {};
  ins.append(h("a", { href: "/api/invio/" + c.job_id + "/file", download: "" }, "Scarica la copia congelata"));
  ins.append(h("p", { class: "mut" }, "Fornitore: " + JSON.stringify(d.profilo || {}) + " · Importi: " + JSON.stringify(d.importi || {})));
  const tentativo = (c.tentativi || []).find(t => t.dettaglio.job_id === d.tentativo_corrente);
  if (tentativo) {
    ins.append(riga_stato("Tentativo", tentativo.dettaglio.stato, tentativo.dettaglio.modalita + (tentativo.dettaglio.protocollo ? " · " + tentativo.dettaglio.protocollo : "")));
    if (tentativo.azione_richiesta) ins.append(h("div", { class: "nota", style: "white-space:pre-wrap" }, tentativo.azione_richiesta));
  }
  ins.append(riga_stato("Copia", c.stato, (d.manifest || []).map(m => m.nome + " · " + m.sha256.slice(0, 12)).join(", ")));
  if (c.azione_richiesta) ins.append(h("div", { class: "nota", style: "margin:6px 0;white-space:pre-wrap" }, c.azione_richiesta));
  if (c.stato === "preparata") {
    const sp = h("input", { type: "checkbox", id: "inv_ok" });
    const bt = h("button", { class: "pil", disabled: true, onclick: () => chiama("/api/invio/" + c.job_id + "/conferma", { impronta: d.impronta_conferma, utente: "professionista" }, () => "Copia confermata.") }, "Conferma questa copia");
    sp.addEventListener("change", () => { bt.disabled = !sp.checked; });
    ins.append(h("label", { class: "chk", for: "inv_ok" }, sp, h("span", {}, "Ho verificato il file (impronta " + (d.impronta_conferma || "").slice(0, 12) + "…), il fornitore e il controllo ufficiale")), h("div", { class: "az" }, bt));
  }
  if (c.stato === "confermata") {
    ins.append(h("div", { class: "az" },
      h("button", { class: "pil", onclick: () => chiama("/api/invio/" + c.job_id + "/trasmetti", { chiave_richiesta: "t-" + crypto.randomUUID(), modalita: "simulata" }, r => (r.avvertenza || "") + " Esito: " + String(r.stato).replaceAll("_", " ")) }, "Invia in PROVA (simulata)"),
      h("button", { class: "gh", onclick: () => chiama("/api/invio/" + c.job_id + "/trasmetti", { chiave_richiesta: "t-" + crypto.randomUUID(), modalita: "manuale" }, r => r.avvertenza) }, "Istruzioni per l'invio reale")));
  }
  if (tentativo && ["esito_incerto", "in_trasmissione", "attesa_invio_manuale"].includes(tentativo.dettaglio.stato)) {
    const url = "/api/invio/tentativi/" + d.tentativo_corrente + "/riconcilia";
    if (tentativo.dettaglio.modalita === "simulata")
      ins.append(h("button", { onclick: () => chiama(url, {}, r => "Riconciliazione: " + r.stato) }, "Riconcilia (prova)"));
    else {
      const protocollo = h("input", { "aria-label": "Protocollo dell'invio", placeholder: "Protocollo assegnato" });
      const fonte = h("input", { "aria-label": "Evidenza verificata", placeholder: "Dove hai verificato l'esito" });
      const registra = nonInviato => {
        if (!fonte.value.trim() || (!nonInviato && !protocollo.value.trim())) return msg("Indica il protocollo e dove hai verificato l'esito; per un invio non avvenuto indica l'evidenza.", "e");
        const evidenze = { verificato_su: fonte.value.trim(), ...(nonInviato ? { non_trasmesso: true } : { protocollo: protocollo.value.trim() }) };
        return chiama(url, { evidenze }, r => "Esito registrato: " + r.stato);
      };
      ins.append(protocollo, fonte, h("div", { class: "az" },
        h("button", { onclick: () => registra(false) }, "Registra protocollo"),
        h("button", { onclick: () => { if (confirm("Hai verificato che questo invio non è avvenuto?")) registra(true); } }, "Registra invio non avvenuto")));
    }
  }
  if (tentativo && tentativo.dettaglio.protocollo) await renderRicevute(ins, pid, tentativo.dettaglio.job_id);
  for (const tid of d.tentativi || []) ins.append(h("div", { class: "mut", style: "font-size:0.9231rem" }, "Tentativo " + tid + (tid === d.tentativo_corrente ? " (corrente)" : "")));
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
  ins.append(tipo, esito, file, h('button', { onclick: async () => {
    const f = file.files[0]; if (!f) return msg('Scegli il documento ricevuto.', 'e');
    try {
      await api(url + '?' + new URLSearchParams({ tipo: tipo.value, esito: esito.value, nome: f.name }), { method: 'POST', body: await f.arrayBuffer() });
      msg('Ricevuta originale acquisita e associata al protocollo.', 'o'); renderVista();
    } catch (e) { msg(e.message, 'e'); }
  } }, 'Acquisisci ricevuta'));
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
      inp = h("select", { id, "aria-label": etichetta }, h("option", { value: "" }, "(non indicato)"), h("option", { value: "si" }, "si'"), h("option", { value: "no" }, "no"));
      inp.value = v === true ? "si" : v === false ? "no" : "";
    } else if (chiave === 'presentatore.persona_id') {
      inp = h('select', { id, 'aria-label': etichetta }, h('option', { value: '' }, 'Presentatore distinto / non selezionato'),
        S.P.dati.persone.filter(p => p.ruolo !== 'defunto').map(p => h('option', { value: p.id }, etichettaPersona(p))));
      inp.value = v || '';
    } else if ((S.schema.strutturati || {})["dichiarazione." + chiave]) {
      const sd = S.schema.strutturati["dichiarazione." + chiave], attuale = v == null ? "" : String(v);
      inp = h("select", { id, "aria-label": etichetta }, h("option", { value: "" }, "(non indicato)"),
        sd.opzioni.map(o => h("option", { value: o.valore }, o.valore + " — " + o.etichetta)),
        attuale && !sd.opzioni.some(o => o.valore === attuale) ? h("option", { value: attuale }, attuale + " (valore non previsto)") : null);
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
  if (!chiavi) sez.append(h("div", { class: "barra", style: "padding:6px 14px" }, h("button", { class: "pil", id: "dd_salva", onclick: async () => {
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
    h("div", { class: "nota", style: "margin:8px 14px" }, "Servono solo se il dichiarante chiede il codice P: il codice si imposta sulla riga di devoluzione (scheda DV, riquadro «Agevolazione prima casa»). Il dichiarante è il presentatore con carica 1 presente nel quadro EA. Fonti: docs/regole/prima_casa.md."));
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
    const dett = h("div", { class: "mut", style: "font-size:0.8846rem;margin-top:2px" });
    const mostraAiuto = () => { const o = sd.tipo === "enum" ? sd.opzioni.find(x => x.valore === inp.value) : null; dett.textContent = o ? o.aiuto : ""; };
    const modifica = () => {
      const t = inp.value;
      S.dichDirty.set(chiave, t === "" ? null : sd.tipo === "bool" ? t === "si" : t);
      mostraAiuto(); aggiornaBottoni(); renderSb();
    };
    inp.addEventListener("change", modifica); mostraAiuto();
    sez.append(h("div", { class: "rg" }, h("label", { for: id }, sd.etichetta), h("div", {}, inp, h("div", { class: "mut", style: "font-size:0.8846rem;margin-top:2px" }, sd.aiuto), dett)));
  }
  sez.append(h("div", { class: "barra", style: "padding:6px 14px" }, h("button", { class: "pil", id: "pc_salva", onclick: () => salvaTutto() }, "Salva dati della dichiarazione")));
  return sez;
}
/* Sezione IV del quadro EH per le riduzioni dell'art. 25 e i codici L, Q chiesti dal dichiarante:
   opzioni.telematico.dichiarazione.riduzioni_art25 (elenco, etichette e aiuti: schema.STRUTTURATI, regole: docs/regole/riduzioni_art25.md). */
function sezioneRiduzioni() {
  const dich = ((S.P.dati.opzioni || {}).telematico || {}).dichiarazione || {};
  const defs = Object.entries(S.schema.strutturati || {}).filter(([k]) => k.startsWith("dichiarazione.riduzioni_art25."));
  const sez = h("section", { class: "grp", id: "sezRiduzioni" }, h("h2", {}, "Riduzioni dell'art. 25 e codici L, Q (Sezione IV del quadro EH)"),
    h("div", { class: "nota", style: "margin:8px 14px" }, "Servono solo se il dichiarante chiede una riduzione 1-5 oppure L o Q: i codici si impostano sulle righe di devoluzione (scheda DV) e il valore delle precedenti successioni sul bene. Indica la successione precedente OPPURE la donazione precedente. Fonti: docs/regole/riduzioni_art25.md."));
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
    sez.append(h("div", { class: "rg" }, h("label", { for: id }, sd.etichetta), h("div", {}, inp, h("div", { class: "mut", style: "font-size:0.8846rem;margin-top:2px" }, sd.aiuto))));
  }
  sez.append(h("div", { class: "barra", style: "padding:6px 14px" }, h("button", { class: "pil", id: "ra_salva", onclick: () => salvaTutto() }, "Salva dati della dichiarazione")));
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
    sezioneDatiDichiarazione(['firma_dichiarante', 'dichiara_copie_conformi'], '5. Firme e documenti'));
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
  main.append(box, h('div', { class: 'barra' }, h('button', { class: 'pil', id: 'dd_salva', onclick: salvaTutto }, 'Salva dati generali')));
}

/* ---------- documenti ---------- */
async function renderAllegati(main) {
  const a = await api("/api/pratiche/" + S.P.pratica_id + "/allegati");
  if (quadro() && quadro().id !== "EG") return;
  const sez = h("section", { class: "grp", style: "padding-bottom:10px" }, h("h2", {}, "Allegati e conversione in PDF/A"));
  sez.append(h("div", { class: "barra", style: "padding:6px 14px 0" }, h("input", { type: "file", id: "file", "aria-label": "File da caricare", style: "max-width:250px" }),
    h("input", { id: "teg", placeholder: "Tipo documento EG", "aria-label": "Tipo documento EG", style: "max-width:190px" }),
    h("input", { id: "fin", placeholder: "Finalità o beneficiario", "aria-label": "Finalità", style: "max-width:230px" }),
    h("button", { class: "pil", onclick: async () => {
      const file = $("#file").files[0]; if (!file) return msg("Scegli un file.", "e");
      const fd = new FormData(); fd.append("file", file); fd.append("tipo_eg", $("#teg").value); fd.append("finalita", $("#fin").value);
      try { await api("/api/pratiche/" + S.P.pratica_id + "/allegati", { method: "POST", body: fd }); msg("Allegato acquisito: l'originale è conservato.", "o"); renderVista(); } catch (e) { msg(e.message, "e"); }
    } }, "Carica")));
  const t = h("table", {}, h("thead", {}, h("tr", {}, ["nome", "ruolo", "byte", "analisi", "PDF/A", ""].map(x => h("th", {}, x)))));
  const tb = h("tbody"); t.append(tb);
  for (const x of a) {
    const an = x.analisi || {}; const rap = x.rapporto; const val = rap && rap.validazione;
    const pdfa = rap ? (val ? val.esito : "") + (val && val.verifica_indicativa ? " (indicativo: " + (val.verifica_indicativa.esito || "") + ")" : "") + ((rap.avvisi || []).length ? " — " + rap.avvisi.join("; ") : "") : (an.dichiara_pdfa ? "dichiara " + an.dichiara_pdfa + " (non verificato)" : "");
    tb.append(h("tr", { style: "cursor:default" }, h("td", {}, x.nome), h("td", {}, x.ruolo), h("td", { class: "n" }, x.bytes), h("td", {}, (an.esito || "") + ((an.avvisi || []).length ? " — " + an.avvisi.join("; ") : "")), h("td", {}, pdfa),
      h("td", {}, x.bytes > 5000000 && ["leggibile", "firmato"].includes(an.esito) ? h("button", { class: "gh", style: "margin-right:6px", title: "Il file supera il limite di 5 MB per allegato", onclick: async () => { try { const r = await api("/api/allegati/" + x.id + "/suddividi", { method: "POST" }); msg("Allegato ridotto o suddiviso: " + ((r.parti || []).length || 1) + " file collegati all'originale, che resta invariato.", "o"); renderVista(); } catch (e) { msg(e.message, "e"); } } }, "Suddividi") : null, x.ruolo === "originale" && ["leggibile", "firmato"].includes(an.esito) ? h("button", { class: "gh", onclick: async () => { try { const r = await api("/api/allegati/" + x.id + "/pdfa", { method: "POST" }); msg("Conversione eseguita. Esito validazione: " + r.esito + (r.esito === "non_verificato" ? " (serve veraPDF per attestare la conformità)." : "."), r.esito === "conforme" ? "o" : "e"); renderVista(); } catch (e) { msg(e.message, "e"); } } }, "Converti in PDF/A") : null)));
  }
  if (!a.length) tb.append(h("tr", { style: "cursor:default" }, h("td", { colspan: 6, class: "mut" }, "Nessun allegato.")));
  sez.append(h("div", { class: "tab", style: "box-shadow:none;border-radius:0;max-height:none" }, t));
  sez.append(h("p", { class: "mut", style: "margin:8px 14px 0" }, "Un PDF convertito non prova che il documento sia firmato o sufficiente. La conformità PDF/A è attestata solo da un validatore indipendente."));
  main.append(sez);
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
  const f = (k, label, ph) => h("div", { class: "campo" }, h("label", { for: "w_" + k }, label), h("input", { id: "w_" + k, value: d[k] || "", placeholder: ph || "", class: k === "codice_fiscale" ? "mono" : "", oninput: ev => { d[k] = ev.target.value; if (k === "codice_fiscale") wizDaCF(ev.target.value); } }));
  if (W.passo === 0) c.append(h("p", { class: "mut" }, "Dati anagrafici del defunto. Potrai completarli o correggerli nei dati generali."), h("div", { class: "griglia" }, f("cognome", "Cognome"), f("nome", "Nome"), f("codice_fiscale", "Codice fiscale"), f("data_nascita", "Data di nascita", "GG/MM/AAAA"), f("luogo_nascita", "Comune di nascita"), f("provincia_nascita", "Provincia di nascita", "RM"), f("data_decesso", "Data del decesso", "GG/MM/AAAA"), f("comune_decesso", "Comune del decesso"), f("provincia_decesso", "Provincia del decesso", "RM")), h("div", { id: "w_cf_nota", class: "mut", style: "font-size:0.9231rem;margin-top:8px", "aria-live": "polite" }));
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
function wizApri() { if (S.writeBusy) return msg("Salvataggio in corso: attendi prima di creare una pratica.", "e"); W.passo = 0; W.dati = {}; S.gen++; wizRender(); $("#wiz").showModal(); }
async function wizAvanti() {
  const d = W.dati;
  if (W.passo === 0 && !(d.cognome || "").trim()) { $("#wizErr").textContent = "Indica almeno il cognome del defunto."; return; }
  if (W.passo < PASSI.length - 1) { W.passo++; wizRender(); return; }
  const campi = {}; for (const k of ["cognome", "nome", "codice_fiscale", "data_nascita", "luogo_nascita", "sesso", "provincia_nascita", "data_decesso", "comune_decesso", "provincia_decesso"]) if ((d[k] || "").trim()) campi[k] = (k === "codice_fiscale" || k.startsWith('provincia')) ? d[k].trim().toUpperCase() : (k.startsWith("data_") ? dataIso(d[k]) : d[k].trim());
  campi.ruolo = "defunto";
  const iniziali = [{ op: "upsert", coll: "persone", campi }, { op: "set", sezione: "opzioni", campi: { tipo_dichiarazione: d.tipo || "originaria", quadri_attivi: d.quadri || S.schema.predefiniti } }];
  try {
    const r = await post("/api/pratiche", { titolo: titoloWiz(), chiave: crypto.randomUUID(), iniziali });
    $("#wiz").close(); await caricaPratiche(); await apri(r.pratica_id, "AN"); msg("Dichiarazione creata.", "o");
  } catch (e) {
    const t = e.dati && e.dati.errori ? e.dati.errori.map(x => x.messaggio).join(" | ") : e.message;
    if (e.dati && e.dati.errori) { W.passo = 0; wizRender(); }
    $("#wizErr").textContent = t;
  }
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
  scelte('font', 'Carattere', [['sistema', 'Carattere del sistema'], ['segoe', 'Segoe UI'], ['arial', 'Arial'], ['verdana', 'Verdana'], ['georgia', 'Georgia'], ['consolas', 'Consolas']]);
  scelte('dimensione', 'Dimensione del testo', Array.from({ length: 11 }, (_, i) => [String(i + 12), (i + 12) + ' px']));
  scelte('interlinea', 'Spaziatura delle righe', [['compatta', 'Compatta'], ['normale', 'Normale'], ['ampia', 'Ampia']]);
  scelte('accento', 'Colore di accento', [['predefinito', 'Predefinito del tema'], ['blu', 'Blu'], ['verde', 'Verde'], ['viola', 'Viola'], ['arancio', 'Arancio'], ['rosso', 'Rosso'], ['grafite', 'Grafite']]);
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
  grid.append(h('div', { class: 'campo', style: 'grid-column:1/-1' }, h('label', {}, 'Quadri proposti nelle nuove pratiche (vuoto = quelli standard)'), quadriGrid));
  $('#impAspetto').replaceChildren(h('h3', {}, 'Aspetto e leggibilità'), grid,
    h('div', { class: 'aspetto-anteprima' }, h('strong', {}, 'Anteprima del carattere'), h('p', {}, 'Dichiarazione di successione · Roma (RM) · € 1.234,56')),
    h('p', { class: 'mut' }, 'Trascina il separatore accanto ai dati per allargare o restringere il pannello. La larghezza viene ricordata.'),
    h('button', { type: 'button', class: 'gh', onclick: () => { impAspettoRender(ASPETTO_DEFAULT); applicaAspetto(IMP.aspetto); } }, 'Ripristina aspetto predefinito'));
}
function impProfiloRender(p) {
  IMP.profilo = { ...p };
  const campo = (chiave, titolo, el) => { el.id = 'prof_' + chiave; el.setAttribute('aria-label', titolo); return h('div', { class: 'campo' }, h('label', { for: el.id }, titolo), el); };
  const cf = h('input', { class: 'mono', value: p.cf || '', placeholder: 'codice fiscale', oninput: e => { IMP.profilo.cf = e.target.value.trim().toUpperCase(); } });
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
    return h('div', { class: 'campo' }, h('label', { class: 'chk', for: el.id }, el, h('span', {}, titolo)), h('div', { class: 'mut', style: 'font-size:0.9231rem' }, nota));
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
        risultato.replaceChildren(h('p', { style: 'font-weight:600' }, r.riepilogo),
          ...r.voci.map(v => h('div', { class: 'campo', style: 'margin-bottom:6px' }, h('div', {}, (icona[v.stato] || '·') + ' ' + v.nome + ' — ' + v.dettaglio),
            v.rimedio && v.stato !== 'ok' ? h('div', { class: 'mut', style: 'font-size:0.9231rem' }, v.rimedio) : null)));
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
  $("#impCorpo").replaceChildren(...s.voci.map(v => h("div", { class: "campo", style: "margin-bottom:12px" },
    h("label", { for: "imp_" + v.chiave }, v.etichetta),
    h("input", { id: "imp_" + v.chiave, class: "mono", value: v.valore || "", disabled: !v.modificabile, placeholder: v.modificabile ? "non impostato" : "" }),
    h("div", { class: "mut", style: "font-size:0.9231rem" }, (v.a_posto ? "✓ " : "✗ ") + v.dettaglio + (v.valore ? " · origine: " + v.origine : "")),
    h("div", { class: "mut", style: "font-size:0.9231rem" }, v.nota))));
}
async function impApri() {
  $("#impErr").textContent = "";
  try { impRender(await api("/api/impostazioni")); $("#imp").showModal(); }
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
    impRender(s); $("#impErr").textContent = "";
    msg("Impostazioni salvate." + (s.avvisi.length ? " " + s.avvisi.join(" ") : ""), "o");
    try { mostraInfo(await api("/api/info")); } catch (_) { /* riga informativa: aggiornata al prossimo caricamento */ }
  } catch (e) { $("#impErr").textContent = e.message; }
}
$("#bImpost").onclick = impApri;
$("#iChiudi").onclick = () => $("#imp").close();
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
    const r = await fetch("/api/importa", { method: "POST", body: await file.arrayBuffer(), headers: { "Content-Type": "application/xml" } });
    const j = await r.json();
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
$("#bControlla").onclick = async () => { if (!S.P) return; if (nMod() && !(await salvaTutto())) return; S.Q = await api("/api/pratiche/" + S.P.pratica_id + "/quadri"); if (S.sel === 'FILE') S.sel = 'AN'; S.tab = "controlli"; render(); };
$('#homeNuova').onclick = wizApri;
$('#homeImporta').onclick = () => $('#fImporta').click();
$('#bHome').onclick = () => {
  if (S.writeBusy || (nMod() && !confirm('Ci sono modifiche non salvate. Tornare alla pagina iniziale senza salvarle?'))) return;
  S.gen++; S.P = null; S.Q = null; S.dirty.clear(); S.nuove.clear(); S.dichDirty.clear(); S.supDirty.clear(); S.fornitoreDirty = {};
  S.sel = 'AN'; S.tab = 'dati'; $('#vista').scrollTop = 0; $('#titolo').textContent = 'Nessuna pratica aperta'; render(); caricaPratiche();
};
document.addEventListener("keydown", ev => { if ((ev.ctrlKey || ev.metaKey) && ev.key === "s") { ev.preventDefault(); salvaTutto(); } });
window.addEventListener("beforeunload", ev => { if (nMod()) { ev.preventDefault(); ev.returnValue = ""; } });
init();
