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
const S = { schema: null, pratiche: [], P: null, Q: null, sel: "AN", riga: null, tab: "dati", dirty: new Map(), nuove: new Map(), salvata: null, writeBusy: false };
const STATI = { vuoto: "da compilare", compilato: "compilato", rilievi: "rilievi", non_supportato: "non supportato", inattivo: "non selezionato" };
S.dichDirty = new Map();
S.supDirty = new Map();
S.fornitoreDirty = {};
const nMod = () => S.dirty.size + S.nuove.size + S.dichDirty.size + S.supDirty.size + (Object.keys(S.fornitoreDirty).length ? 1 : 0);
const nuovoId = coll => ({ persone: "p", beni: "b", devoluzioni: "d", passivita: "ps", documenti_ref: "dr" }[coll]) + "_" + crypto.randomUUID().replaceAll("-", "").slice(0, 12);
const uguale = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const ASPETTO_DEFAULT = { tema: 'sistema', font: 'sistema', dimensione: 14, interlinea: 'normale', larghezza_pannello: 360 };
const FONT_UI = { sistema: 'system-ui, "Segoe UI", sans-serif', segoe: '"Segoe UI", system-ui, sans-serif',
  arial: 'Arial, sans-serif', verdana: 'Verdana, sans-serif', georgia: 'Georgia, serif', consolas: 'Consolas, monospace' };
let preferenze = { ...ASPETTO_DEFAULT };
const sistemaScuro = window.matchMedia('(prefers-color-scheme: dark)');
function applicaAspetto(valori) {
  const p = { ...ASPETTO_DEFAULT, ...valori }, root = document.documentElement;
  root.dataset.tema = p.tema === 'sistema' ? (sistemaScuro.matches ? 'scuro' : 'chiaro') : p.tema;
  root.style.setProperty('--f-ui', FONT_UI[p.font] || FONT_UI.sistema);
  root.style.setProperty('--dimensione-base', Math.max(12, Math.min(22, Number(p.dimensione) || 14)) + 'px');
  root.style.setProperty('--interlinea', ({ compatta: 1.3, normale: 1.5, ampia: 1.8 })[p.interlinea] || 1.5);
  const limite = Math.max(280, Math.min(760, window.innerWidth - 580));
  root.style.setProperty('--larghezza-ins', Math.min(limite, Math.max(280, Number(p.larghezza_pannello) || 360)) + 'px');
  const separatore = $('#ridimensiona');
  if (separatore) separatore.setAttribute('aria-valuenow', String(Math.round(Math.min(limite, p.larghezza_pannello))));
}
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
function msg(t, tipo) { const m = $("#msg"); m.textContent = t || ""; m.className = tipo || ""; m.hidden = !t; }

/* ---------- valori ---------- */
function mostra(kind, v) {
  if (v === undefined || v === null) return "";
  if (typeof v === "object" && v.stato) return "[" + v.stato + "]";
  if (kind === "quota" && typeof v === "object") return v.num + "/" + v.den;
  return String(v);
}
function leggi(kind, t) {
  t = t.trim();
  if (t === "") return null;
  if (t === "?") return { stato: "da_confermare" };
  if (/^\[[a-z_]+\]$/.test(t)) return { stato: t.slice(1, -1) };
  if (kind === "quota") { const m = t.match(/^(\d+)\s*\/\s*(\d+)$/); return m ? { num: +m[1], den: +m[2] } : t; }
  return t;
}
function etichetta(coll, e) {
  if (coll === "persone") return [e.cognome, e.nome].filter(Boolean).join(" ") || e.id;
  if (coll === "beni") return [e.tipo, e.comune, e.foglio && "fg." + e.foglio, e.particella && "p." + e.particella, e.subalterno && "sub." + e.subalterno, e.descrizione].filter(Boolean).join(" ") || e.id;
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
    try { memorizzaAspetto((await api('/api/impostazioni')).interfaccia); } catch (_) { /* l'app resta utilizzabile */ }
    await caricaPratiche(); renderSb(); aggiornaBottoni();
  } catch (e) { msg("Avvio non riuscito: " + e.message, "e"); }
}
async function caricaPratiche() {
  S.pratiche = await api("/api/pratiche");
  const ul = $("#lista"); ul.replaceChildren();
  if (!S.pratiche.length) ul.append(h("li", { class: "mut" }, "Nessuna pratica."));
  for (const p of S.pratiche) ul.append(h("li", {}, h("button", { "aria-current": S.P && S.P.pratica_id === p.id ? "true" : "false", onclick: () => apri(p.id) }, h("span", {}, p.titolo), h("span", { class: "mut" }, "rev. " + p.revisione))));
}
async function apri(id, sel) {
  if (S.writeBusy) { msg("Salvataggio in corso: attendi prima di cambiare pratica.", "e"); return; }
  if (nMod() && !confirm("Ci sono modifiche non salvate: continuare senza salvarle?")) return;
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
  if (!S.P) { sb.append(h("span", {}, "Nessuna pratica aperta")); return; }
  const n = S.Q.rilievi.length;
  sb.append(...[h("span", {}, "Revisione " + S.P.revisione),
    S.salvata ? h("span", { class: "ok" }, "Salvata alle " + S.salvata) : null,
    nMod() ? h("span", { style: "color:var(--am)" }, nMod() + (nMod() === 1 ? " modifica non salvata" : " modifiche non salvate")) : null,
    n ? h("button", { onclick: () => { if (S.sel === 'FILE') S.sel = 'AN'; S.tab = "controlli"; render(); } }, n + (n === 1 ? " rilievo" : " rilievi")) : h("span", {}, "Nessun rilievo"),
    h("span", {}, S.Q.finalizzabile ? "Finalizzabile" : "Non finalizzabile" + ((S.Q.blocchi_finalizzazione || []).length ? ": file XML completo non generato" : "")),
    h("span", {}, "Controllo ufficiale: vedi File e invio")].filter(Boolean));
}
function vaiFile() { if (!S.P) return; S.sel = 'FILE'; S.riga = null; S.tab = 'dati'; $('#vista').scrollTop = 0; render(); }
function scegliQuadro(id) { S.sel = id; S.riga = null; S.tab = 'dati'; $('#vista').scrollTop = 0; render(); }

/* ---------- albero dei quadri ---------- */
function renderAlbero() {
  const nav = $("#albero"); nav.replaceChildren();
  if (!S.Q) return;
  nav.append(h('button', { class: 'voce nav-file', id: 'navFile', 'aria-current': S.sel === 'FILE' ? 'page' : 'false', onclick: vaiFile },
    h('span', { class: 'sigla' }, '↗'), h('span', {}, 'File e invio')));
  for (const [g, nome] of [["frontespizio", "Frontespizio"], ["quadri", "Quadri"], ["riepiloghi", "Riepiloghi"], ["lavoro", "Tabella di lavoro"]]) {
    nav.append(h("div", { class: "gruppo" }, nome));
    for (const q of S.Q.quadri.filter(x => x.gruppo === g)) {
      const st = q.stato;
      const testo = st === "rilievi" ? q.rilievi + (q.rilievi === 1 ? " rilievo" : " rilievi") : (q.righe && st === "compilato" ? q.righe + (q.righe === 1 ? " riga" : " righe") : STATI[st]);
      nav.append(h("button", { class: "voce", "data-stato": st, "data-q": q.id, "aria-current": S.sel === q.id ? "true" : "false", onclick: () => scegliQuadro(q.id) },
        h("span", { class: "sigla" }, q.id), h("span", { class: "nome" }, q.titolo), h("span", { class: "st" }, testo)));
    }
  }
}

/* ---------- campi ---------- */
function campoInput(coll, id, campo, kind, val, onMod) {
  const path = id ? coll + "[" + id + "]." + campo : null;
  const err = path ? rilievi().filter(r => r.percorso === path) : [];
  let el;
  if (kind.startsWith("enum:")) {
    el = h("select", { "aria-label": campo }, h("option", { value: "" }, ""), kind.slice(5).split("|").map(o => h("option", { value: o }, o)));
    el.value = val || "";
  } else if (kind.startsWith("ref:")) {
    const rc = kind.slice(4);
    el = h("select", { "aria-label": campo }, h("option", { value: "" }, ""), (S.P.dati[rc] || []).map(e => h("option", { value: e.id }, etichetta(rc, e))));
    el.value = val || "";
  } else {
    el = h("input", { "aria-label": campo, autocomplete: "off", class: kind === "cf" ? "mono" : (kind === "importo" || kind === "quota" ? "num" : ""), placeholder: kind === "quota" ? "1/2" : kind === "data" ? "AAAA-MM-GG" : "" });
    el.value = mostra(kind, val);
  }
  if (path) el.dataset.path = path;
  if (err.length) el.classList.add("bad");
  const f = () => onMod(campo, leggi(kind, el.value));
  el.addEventListener("input", f); el.addEventListener("change", f);
  return h("div", {}, el, err.map(r => h("div", { class: "e" }, r.messaggio)));
}

/* Campo a scelta guidata (S.schema.strutturati, definito in schema.py): menu con etichette e aiuto della voce scelta.
   Un valore gia' presente ma non nell'elenco (o uno stato come [da_confermare]) resta visibile e non viene perso. */
function campoStrutturato(sd, val, onMod, path) {
  const err = path ? rilievi().filter(r => r.percorso === path) : [];
  const attuale = val === undefined || val === null ? "" : (typeof val === "object" && val.stato ? "[" + val.stato + "]" : String(val));
  const el = h("select", { "aria-label": sd.etichetta },
    h("option", { value: "" }, "(non indicato)"),
    sd.opzioni.map(o => h("option", { value: o.valore }, o.valore + " — " + o.etichetta)),
    attuale && !sd.opzioni.some(o => o.valore === attuale) ? h("option", { value: attuale }, attuale + " (valore non previsto)") : null);
  el.value = attuale;
  if (path) el.dataset.path = path;
  if (err.length) el.classList.add("bad");
  const dett = h("div", { class: "mut aiuto-voce", style: "font-size:0.8846rem;margin-top:2px" });
  const mostraAiuto = () => { const o = sd.opzioni.find(x => x.valore === el.value); dett.textContent = o ? o.aiuto : ""; };
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
  t.append(h("thead", {}, h("tr", {}, q.colonne.map(c => h("th", { class: ["quota", "importo", "rendita", "valore"].includes(c) ? "n" : "" }, c.replaceAll("_", " "))))));
  const tb = h("tbody"); t.append(tb);
  righe.forEach((r, i) => {
    const id = r.e && r.e.id; const base = id ? q.coll + "[" + id + "]" : null;
    const rilRiga = base ? rilievi().filter(x => x.percorso === base || x.percorso.startsWith(base + ".")) : [];
    const tr = h("tr", { tabindex: "0", "aria-selected": S.riga === r.key ? "true" : "false", class: (r.nuova || S.dirty.has(r.key)) ? "mod" : "", "data-key": r.key,
      onclick: () => selezionaRiga(r.key),
      onkeydown: ev => { if (ev.key === "ArrowDown" && righe[i + 1]) { ev.preventDefault(); selezionaRiga(righe[i + 1].key, true); } else if (ev.key === "ArrowUp" && righe[i - 1]) { ev.preventDefault(); selezionaRiga(righe[i - 1].key, true); } else if (ev.key === "Enter") selezionaRiga(r.key); } });
    q.colonne.forEach((c, j) => {
      const kind = campi[c]; const v = valRiga(r, c);
      let txt = mostra(kind, v);
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
  const primo = $("#ins .rg input, #ins .rg select"); if (primo) primo.focus();
}
function selezionaRiga(key, focusRiga) {
  S.riga = key; S.tab = "dati"; renderVista(); renderIns();
  if (focusRiga) { const tr = document.querySelector('tr[data-key="' + CSS.escape(key) + '"]'); if (tr) tr.focus(); }
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
  const campi = S.schema.collezioni[q.coll]; const id = r.e && r.e.id;
  ins.append(h("h3", {}, r.nuova ? "Nuova riga" : etichetta(q.coll, r.e)));
  for (const x of rilievi().filter(x => id && x.percorso === q.coll + "[" + id + "]")) ins.append(h("div", { class: "e", style: "color:var(--er);margin:0 0 6px" }, x.messaggio));
  const visibili = q.campi ? new Set(q.campi) : null;   // solo i campi pertinenti al quadro; uno gia' valorizzato resta visibile
  const ordine = Object.keys(campi);
  for (const [comune, provincia] of [['comune', 'provincia'], ['luogo_nascita', 'provincia_nascita']]) {
    if (ordine.includes(comune) && ordine.includes(provincia)) { ordine.splice(ordine.indexOf(provincia), 1); ordine.splice(ordine.indexOf(comune) + 1, 0, provincia); }
  }
  for (const c of ordine) { const kind = campi[c];
    const vv = valRiga(r, c);
    if (visibili && !visibili.has(c) && (vv === undefined || vv === null || vv === "")) continue;
    const sd = (S.schema.strutturati || {})[q.coll + "." + c];
    const modificaCampo = (campo, v) => {
      const scrivi = (c2, x) => {
        if (r.nuova) r.nuova.campi[c2] = x;
        else { const d = S.dirty.get(r.key) || { coll: q.coll, id, campi: {} }; d.campi[c2] = x; S.dirty.set(r.key, d); }
      };
      scrivi(campo, v);
      renderVista(); aggiornaBottoni(); renderSb();
      if (q.coll === "persone" && campo === "codice_fiscale")
        suggerisciDaCF(v, r.e ? r.e.ruolo : (r.nuova && r.nuova.campi.ruolo), c2 => valRiga(r, c2), scrivi).then(res => {
          if (res.testo) msg(res.testo, res.riempiti.length ? "o" : "e");
          if (res.riempiti.length) { renderVista(); renderIns(); aggiornaBottoni(); renderSb(); }
        });
    };
    const w = sd && sd.opzioni ? campoStrutturato(sd, valRiga(r, c), v => modificaCampo(c, v), id ? q.coll + "[" + id + "]." + c : null)
      : campoInput(q.coll, id, c, kind, valRiga(r, c), modificaCampo);
    const aiuto = (S.schema.aiuti || {})[q.coll + "." + c];
    if (aiuto) w.append(h("div", { class: "mut", style: "font-size:0.8846rem;margin-top:2px" }, aiuto));
    ins.append(h("div", { class: "rg" }, h("label", {}, c.replaceAll("_", " ")), w));
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
    ins.append(h('h3', {}, 'Agevolazione prima casa'));
    ins.append(campoStrutturato(sd, valore('agevolazioni'), v => scrivi('agevolazioni', v), null));
    ins.append(h('div', { class: 'mut', style: 'font-size:0.8846rem;margin-top:4px' }, sd.aiuto));
    if (bene && quadroBene(bene) !== 'EC')
      ins.append(h('div', { class: 'nota', style: 'margin:6px 0' }, 'Il bene collegato non è un fabbricato del quadro EC: i codici P, X, Z sono ammessi solo lì e l\'esportazione segnalerà un errore.'));
    return;
  }
  if (q.coll === 'persone') {
    const cb = h('input', { type: 'checkbox', 'aria-label': 'portatore handicap', onchange: ev => scrivi('portatore_handicap', ev.target.checked) });
    cb.checked = valore('portatore_handicap') === true;
    ins.append(h('label', { class: 'chk' }, cb, 'Portatore di handicap (come documentato)'));
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
      for (const [c, tipo] of campi) box.append(h('label', {}, c.replaceAll('_', ' '), campoInput(q.coll, null, c, tipo, voce[c], (k, v) => {
        const nuove = structuredClone(valore(campo) || []); nuove[i][k] = v; scrivi(campo, nuove);
      })));
      box.append(h('button', { onclick: () => { scrivi(campo, righe.filter((_, j) => j !== i)); renderIns(); } }, 'Rimuovi ' + titolo.toLowerCase()));
      ins.append(box);
    });
    ins.append(h('button', { onclick: () => { scrivi(campo, [...righe, structuredClone(predefinito)]); renderIns(); } }, 'Aggiungi ' + titolo.toLowerCase()));
  };
  if (q.coll === 'passivita') tabella('ripartizione', 'Ripartizione', [['persona_id', 'ref:persone'], ['quota', 'quota']], { persona_id: '', quota: '1/1' });
  if (q.id === 'EB' || q.id === 'EC') {
    tabella('estremi_trascrizione', 'Trascrizione', [['ufficio', 'str'], ['registro_particolare', 'str'], ['anno', 'str']], {});
    tabella('estremi_registrazione', 'Registrazione', [['ufficio', 'str'], ['anno', 'str'], ['volume', 'str'], ['numero', 'str']], {});
  }
}
function insControlli(ins) {
  const q = S.Q;
  ins.append(h("p", { class: "mut" }, q.ambito + (q.finalizzabile ? ". Finalizzabile." : ". Non finalizzabile.")));
  for (const b of (q.blocchi_finalizzazione || [])) ins.append(h("div", { class: "nota", style: "margin:0 0 8px" }, b.messaggio));
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
  return h("div", { class: "rg", style: "grid-template-columns:120px 1fr" }, h("label", {}, nome), h("div", {}, h("span", { class: "pz " + (PILLOLE[stato] || "") , style: PILLOLE[stato] ? "" : "background:var(--grigio)" }, String(stato).replaceAll("_", " ")), extra ? h("div", { class: "mut", style: "font-size:0.9231rem;margin-top:3px" }, extra) : null));
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
  const dataIn = h('input', { 'aria-label': 'Data impegno', placeholder: 'AAAA-MM-GG', value: profilo.data_impegno || '' });
  const dettagli = h('div', {}, h('label', {}, 'Impegno a trasmettere', impegnoIn), h('label', {}, 'Data impegno', dataIn));
  dettagli.hidden = tipoIn.value !== '10';
  tipoIn.addEventListener('change', () => { modifica('tipo', tipoIn.value); dettagli.hidden = tipoIn.value !== '10'; });
  impegnoIn.addEventListener('change', () => modifica('impegno_codice', impegnoIn.value || null));
  dataIn.addEventListener('input', () => modifica('data_impegno', dataIn.value.trim() || null));
  fornitore.append(h('label', {}, 'Codice fiscale del fornitore', cfIn), h('label', {}, 'Tipo fornitore', tipoIn), dettagli,
    h('div', { class: 'az' }, h('button', { class: 'gh', onclick: salvaTutto }, 'Salva profilo')));
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
      if (S.P.pratica_id === pid) { await ricarica(); render(); }
    } catch (e) { msg(e.message, 'e'); }
  };
  elaborati.append(h('p', { class: 'mut' }, 'Genera il file quando i dati sono pronti. La bozza tecnica conserva evidenza dei limiti e non è trasmissibile.'),
    h('div', { class: 'az' }, h('button', { class: 'pil', onclick: () => esegui('completo') }, 'Genera file'),
      h('button', { class: 'gh', onclick: () => esegui('bozza_tecnica') }, 'Genera bozza tecnica')));
  if (ex.generato) elaborati.append(h('div', { class: 'az' },
    h('a', { href: '/api/pratiche/' + pid + '/file.xml?job=' + ex.job_id, download: '' }, 'Scarica XML'),
    h('a', { href: '/api/pratiche/' + pid + '/stampa?job=' + ex.job_id, target: '_blank', rel: 'noopener' }, 'Stampa prospetto')));
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
  for (const c of vis) {
    const cur = S.dirty.has(key) && c in S.dirty.get(key).campi ? S.dirty.get(key).campi[c] : (e ? e[c] : undefined);
    const nomi = { luogo_nascita: 'Comune di nascita', provincia_nascita: 'Provincia di nascita', comune_decesso: 'Comune del decesso', provincia_decesso: 'Provincia del decesso' };
    griglia.append(h("div", { class: "rg", 'data-campo': c }, h("label", {}, nomi[c] || c.replaceAll("_", " ")), campoInput("persone", e && e.id, c, campi[c], cur, (campo, v) => {
      const scrivi = (c2, x) => { const d = S.dirty.get(key) || { coll: "persone", id: e ? e.id : null, campi: e ? {} : { ruolo } }; d.campi[c2] = x; S.dirty.set(key, d); };
      scrivi(campo, v); aggiornaBottoni(); renderSb();
      if (campo === "codice_fiscale")
        suggerisciDaCF(v, ruolo, c2 => { const dd = S.dirty.get(key); return dd && c2 in dd.campi ? dd.campi[c2] : (e ? e[c2] : undefined); }, scrivi).then(res => {
          if (res.testo) msg(res.testo, res.riempiti.length ? "o" : "e");
          if (res.riempiti.length) { aggiornaBottoni(); renderSb(); render(); }
        });
    })));
  }
  return g;
}
/* Dati della dichiarazione: opzioni.telematico.dichiarazione. I codici non sono proposti dal programma: vanno presi dalle istruzioni del frontespizio. */
const CAMPI_DICH = [   // [chiave, etichetta, tipo]: "bool" = si'/no (valore booleano nel modello), altrimenti testo
  ["stato_civile", "stato civile"], ["devoluzione_per_legge", "devoluzione per legge", "bool"], ["firma_dichiarante", "firma del dichiarante", "bool"],
  ["tempistica_pagamento", "tempistica del pagamento"],
  ["dichiara_copie_conformi", "dichiarazione di conformità delle copie allegate", "bool"],
  ["azienda_data_deposito", "azienda: data di deposito (AAAA-MM-GG)"],
  ["azienda_camera_commercio", "azienda: camera di commercio"],
  ["presentatore.persona_id", "Presentatore tra i soggetti della pratica"], ["presentatore.codice_carica", "presentatore: codice carica"],
  ["presentatore.telefono", "presentatore: telefono"], ["presentatore.email", "presentatore: email"],
  ["versamento.iban", "versamento: IBAN"], ["versamento.cf_titolare", "versamento: codice fiscale del titolare"],
  ["devoluzione_per_testamento", "devoluzione per testamento", "bool"], ["testamento.estero", "testamento estero", "bool"],
  ["testamento.pubblico_ufficiale", "testamento: pubblico ufficiale"], ["testamento.data_pubblicazione", "testamento: data pubblicazione (AAAA-MM-GG)"],
  ["testamento.ufficio_registrazione", "testamento: ufficio di registrazione"], ["testamento.serie", "testamento: serie"],
  ["testamento.numero_registrazione", "testamento: numero registrazione"], ["testamento.sottonumero_registrazione", "testamento: sottonumero"],
  ["testamento.data_registrazione", "testamento: data registrazione (AAAA-MM-GG)"],
];
function sezioneDatiDichiarazione(chiavi = null, titolo = 'Dati della dichiarazione') {
  const tel = (S.P.dati.opzioni || {}).telematico || {};
  const dich = tel.dichiarazione || {};
  const leggi = (chiave) => chiave.split(".").reduce((o, k) => (o == null ? undefined : o[k]), dich);
  const sez = h("section", { class: "grp" }, h("h2", {}, titolo));
  const inputs = {};
  for (const [chiave, etichetta, tipo] of CAMPI_DICH) {
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
    } else inp = h("input", { id, "aria-label": etichetta, value: v == null ? "" : String(v) });
    const modifica = () => {
      const testo = inp.value.trim();
      S.dichDirty.set(chiave, testo === "" ? null : tipo === "bool" ? testo === "si" : testo);
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
const etichettaPersona = p => [p.cognome, p.nome].filter(Boolean).join(' ') + (p.ruolo ? ' · ' + p.ruolo : '');
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
  if (tipo === 'sostitutiva') successione.append(h('p', { class: 'nota' }, 'La gestione della dichiarazione precedente non è completa: la sostitutiva resta non finalizzabile.'));
  grid.append(successione);
  const presentatore = sezioneDatiDichiarazione(CAMPI_DICH.filter(([k]) => k.startsWith('presentatore.')).map(([k]) => k), '3. Presentatore e contatti');
  presentatore.classList.add('intera');
  presentatore.append(schedaPersona('Anagrafica del presentatore', 'presentatore', ['cognome', 'nome', 'codice_fiscale', 'sesso', 'data_nascita', 'luogo_nascita', 'provincia_nascita', 'relazione_con_defunto']));
  grid.append(presentatore,
    sezioneDatiDichiarazione(['tempistica_pagamento', 'versamento.iban', 'versamento.cf_titolare'], '4. Pagamento'),
    sezioneDatiDichiarazione(['firma_dichiarante', 'dichiara_copie_conformi'], '5. Firme e documenti'));
  const dich = ((S.P.dati.opzioni.telematico || {}).dichiarazione || {});
  const testamento = h('details', { class: 'gruppo-opzionale', open: dich.devoluzione_per_testamento === true || !!dich.testamento }, h('summary', {}, 'Testamento · dati da compilare se presente'),
    sezioneDatiDichiarazione(CAMPI_DICH.filter(([k]) => k.startsWith('testamento.')).map(([k]) => k), 'Estremi del testamento'));
  const primaCasa = h('details', { class: 'gruppo-opzionale', open: !!dich.prima_casa }, h('summary', {}, 'Agevolazione prima casa'), sezionePrimaCasa());
  const aziende = h('details', { class: 'gruppo-opzionale', open: S.P.dati.beni.some(b => b.tipo === 'azienda') }, h('summary', {}, 'Dati delle aziende · se presenti'),
    sezioneDatiDichiarazione(['azienda_data_deposito', 'azienda_camera_commercio'], 'Deposito e camera di commercio'));
  main.append(testamento, primaCasa, aziende);
  const att = new Set(S.P.dati.opzioni.quadri_attivi || S.schema.predefiniti);
  const box = h('details', { class: 'gruppo-opzionale' }, h('summary', {}, 'Quadri inclusi nella pratica · ' + att.size + ' selezionati'));
  for (const q of S.schema.quadri.filter(x => x.gruppo !== 'frontespizio' && x.id !== 'DV')) {
    const cb = h('input', { type: 'checkbox', id: 'qa_' + q.id }); cb.checked = att.has(q.id);
    cb.addEventListener('change', () => impostaQuadro(q.id, cb.checked));
    box.append(h('label', { class: 'chk', for: 'qa_' + q.id }, cb, h('span', {}, q.id + ' — ' + q.titolo + (q.supportato ? '' : ' (generato / copertura limitata)'))));
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
    if (e.dati && e.dati.errori) msg(e.dati.errori.map(x => x.percorso + ": " + x.messaggio).join(" | "), "e");
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
    for (const k of ['presentatore', 'versamento', 'testamento', 'prima_casa']) if (d[k] && !Object.keys(d[k]).length) delete d[k];
    for (const { coll, id, campi } of supplementi.values()) {
      const ent = (tel[coll] = tel[coll] || {})[id] = ((tel[coll] || {})[id] || {});
      for (const [k, v] of Object.entries(campi)) { if (v === null) delete ent[k]; else ent[k] = v; }
      if (!Object.keys(ent).length) delete tel[coll][id];
    }
    ops.push({ op: 'set', sezione: 'opzioni', campi: { telematico: tel } });
  }
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
  if (riempiti.length) parti.push("Compilato dal codice fiscale: " + riempiti.map(c => c.replaceAll("_", " ")).join(", ") + ". Verifica i dati.");
  if (r.avvisi.length) parti.push(r.avvisi.join(" "));
  return parti.join(" ");
}
async function suggerisciDaCF(cf, ruolo, leggiCampo, scriviCampo) {
  const v = String(cf || "").trim().toUpperCase();
  if (v.length !== 16) return { riempiti: [], testo: "" };
  let r; try { r = await decodificaCF(v, ruolo); } catch (e) { return { riempiti: [], testo: "" }; }
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
  if (W.passo === 0) c.append(h("p", { class: "mut" }, "Dati anagrafici del defunto. Potrai completarli o correggerli nei dati generali."), h("div", { class: "griglia" }, f("cognome", "Cognome"), f("nome", "Nome"), f("codice_fiscale", "Codice fiscale"), f("data_nascita", "Data di nascita", "AAAA-MM-GG"), f("luogo_nascita", "Comune di nascita"), f("provincia_nascita", "Provincia di nascita", "RM"), f("data_decesso", "Data del decesso", "AAAA-MM-GG"), f("comune_decesso", "Comune del decesso"), f("provincia_decesso", "Provincia del decesso", "RM")), h("div", { id: "w_cf_nota", class: "mut", style: "font-size:0.9231rem;margin-top:8px", "aria-live": "polite" }));
  if (W.passo === 1) {
    d.tipo = d.tipo || "originaria";
    for (const [v, t, s] of [["originaria", "Dichiarazione originaria", "Prima dichiarazione per questa successione."], ["sostitutiva", "Dichiarazione sostitutiva", "Sostituisce una dichiarazione già presentata. La gestione dei dati della precedente non è ancora disponibile."]]) {
      const r = h("input", { type: "radio", name: "tipo", id: "t_" + v, value: v, onchange: () => { d.tipo = v; } }); r.checked = d.tipo === v;
      c.append(h("label", { class: "radio", for: "t_" + v }, r, h("span", {}, h("strong", {}, t), h("div", { class: "mut" }, s))));
    }
  }
  if (W.passo === 2) {
    d.quadri = d.quadri || [...S.schema.predefiniti];
    c.append(h("p", { class: "mut" }, "Seleziona i quadri da compilare. Potrai cambiare scelta nel frontespizio."));
    for (const q of S.schema.quadri.filter(x => x.gruppo !== "frontespizio" && x.id !== "DV")) {
      const cb = h("input", { type: "checkbox", id: "wq_" + q.id }); cb.checked = d.quadri.includes(q.id);
      cb.addEventListener("change", () => { d.quadri = cb.checked ? [...new Set([...d.quadri, q.id])] : d.quadri.filter(x => x !== q.id); });
      c.append(h("label", { class: "chk", for: "wq_" + q.id }, cb, h("span", {}, q.id + " — " + q.titolo + (q.supportato ? "" : " (non ancora supportato: blocca la finalizzazione)"))));
    }
  }
  if (W.passo === 3) c.append(h("p", {}, "Verrà creata la dichiarazione «" + titoloWiz() + "» con " + (d.quadri || S.schema.predefiniti).length + " quadri selezionati, tipo " + (d.tipo || "originaria") + "."), h("p", { class: "mut" }, "Potrai completare ogni dato nei quadri; i controlli ti mostreranno cosa manca."));
}
async function wizDaCF(valore) {
  const d = W.dati;
  const { testo } = await suggerisciDaCF(valore, "defunto", c => d[c], (c, x) => { d[c] = x; const el = $("#w_" + c); if (el) el.value = x; });
  const nota = $("#w_cf_nota"); if (nota) nota.textContent = testo;
}
function wizApri() { if (S.writeBusy) return msg("Salvataggio in corso: attendi prima di creare una pratica.", "e"); W.passo = 0; W.dati = {}; wizRender(); $("#wiz").showModal(); }
async function wizAvanti() {
  const d = W.dati;
  if (W.passo === 0 && !(d.cognome || "").trim()) { $("#wizErr").textContent = "Indica almeno il cognome del defunto."; return; }
  if (W.passo < PASSI.length - 1) { W.passo++; wizRender(); return; }
  const campi = {}; for (const k of ["cognome", "nome", "codice_fiscale", "data_nascita", "luogo_nascita", "sesso", "provincia_nascita", "data_decesso", "comune_decesso", "provincia_decesso"]) if ((d[k] || "").trim()) campi[k] = (k === "codice_fiscale" || k.startsWith('provincia')) ? d[k].trim().toUpperCase() : d[k].trim();
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
const IMP = { voci: [], iniziali: {}, aspetto: null };
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
  $('#impAspetto').replaceChildren(h('h3', {}, 'Aspetto e leggibilità'), grid,
    h('div', { class: 'aspetto-anteprima' }, h('strong', {}, 'Anteprima del carattere'), h('p', {}, 'Dichiarazione di successione · Roma (RM) · € 1.234,56')),
    h('p', { class: 'mut' }, 'Trascina il separatore accanto ai dati per allargare o restringere il pannello. La larghezza viene ricordata.'),
    h('button', { type: 'button', class: 'gh', onclick: () => { impAspettoRender(ASPETTO_DEFAULT); applicaAspetto(IMP.aspetto); } }, 'Ripristina aspetto predefinito'));
}
function impRender(s) {
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
    const s = await post("/api/impostazioni", { modifiche, interfaccia: IMP.aspetto });
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
async function salvaLarghezza(larghezza) {
  const precedente = { ...preferenze };
  memorizzaAspetto({ ...preferenze, larghezza_pannello: larghezza });
  try {
    const r = await post('/api/impostazioni', { interfaccia: { larghezza_pannello: larghezza } });
    memorizzaAspetto(r.interfaccia);
  } catch (e) { memorizzaAspetto(precedente); msg('Larghezza non salvata: ' + e.message, 'e'); }
}
const separatoreDati = $('#ridimensiona');
let trascinamento = null;
separatoreDati.addEventListener('pointerdown', ev => {
  if (ev.button !== 0 || window.innerWidth <= 960) return;
  trascinamento = { id: ev.pointerId, x: ev.clientX, larghezza: $('#ins').getBoundingClientRect().width, nuova: preferenze.larghezza_pannello };
  separatoreDati.setPointerCapture(ev.pointerId); document.body.classList.add('ridimensionando'); ev.preventDefault();
});
separatoreDati.addEventListener('pointermove', ev => {
  if (!trascinamento || ev.pointerId !== trascinamento.id) return;
  trascinamento.nuova = Math.round(Math.max(280, Math.min(760, window.innerWidth - 580, trascinamento.larghezza + trascinamento.x - ev.clientX)));
  applicaAspetto({ ...preferenze, larghezza_pannello: trascinamento.nuova });
});
const terminaTrascinamento = ev => {
  if (!trascinamento || ev.pointerId !== trascinamento.id) return;
  const larghezza = trascinamento.nuova; trascinamento = null; document.body.classList.remove('ridimensionando');
  if (separatoreDati.hasPointerCapture(ev.pointerId)) separatoreDati.releasePointerCapture(ev.pointerId);
  if (ev.type === 'pointercancel') applicaAspetto(preferenze); else salvaLarghezza(larghezza);
};
separatoreDati.addEventListener('pointerup', terminaTrascinamento);
separatoreDati.addEventListener('pointercancel', terminaTrascinamento);
separatoreDati.addEventListener('keydown', ev => {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(ev.key)) return;
  ev.preventDefault();
  const l = ev.key === 'Home' ? 280 : ev.key === 'End' ? 760 : preferenze.larghezza_pannello + (ev.key === 'ArrowLeft' ? 16 : -16);
  salvaLarghezza(Math.max(280, Math.min(760, l)));
});

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
  S.P = null; S.Q = null; S.dirty.clear(); S.nuove.clear(); S.dichDirty.clear(); S.supDirty.clear(); S.fornitoreDirty = {};
  S.sel = 'AN'; S.tab = 'dati'; $('#vista').scrollTop = 0; $('#titolo').textContent = 'Nessuna pratica aperta'; render(); caricaPratiche();
};
document.addEventListener("keydown", ev => { if ((ev.ctrlKey || ev.metaKey) && ev.key === "s") { ev.preventDefault(); salvaTutto(); } });
window.addEventListener("beforeunload", ev => { if (nMod()) { ev.preventDefault(); ev.returnValue = ""; } });
init();
