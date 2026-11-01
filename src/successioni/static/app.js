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
const S = { schema: null, pratiche: [], P: null, Q: null, sel: "AN", riga: null, tab: "dati", dirty: new Map(), nuove: new Map(), salvata: null };
const STATI = { vuoto: "da compilare", compilato: "compilato", rilievi: "rilievi", non_supportato: "non supportato", inattivo: "non selezionato" };
const nMod = () => S.dirty.size + S.nuove.size;

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
async function init() {
  try {
    const i = await api("/api/info");
    $("#info").textContent = "Versione " + i.versione + ". Accesso solo da questo computer. PDF/A: Ghostscript " + (i.pdfa.ghostscript ? "presente" : "assente") + ", veraPDF " + (i.pdfa.veraPDF ? "presente" : "non configurato");
    S.schema = await api("/api/schema");
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
  if (nMod() && !confirm("Ci sono modifiche non salvate: continuare senza salvarle?")) return;
  S.dirty.clear(); S.nuove.clear(); S.riga = null; S.tab = "dati"; S.salvata = null;
  await ricarica(id);
  S.sel = sel || "AN"; render(); await caricaPratiche();
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
  $("#app").classList.toggle("conIns", aperta); $("#ins").hidden = !aperta;
  renderAlbero(); renderVista(); renderIns(); renderSb(); aggiornaBottoni();
}
function aggiornaBottoni() {
  const n = nMod();
  $("#bSalva").disabled = !n; $("#bSalva").textContent = n ? "Salva (" + n + ")" : "Salva";
  $("#bControlla").disabled = !S.P;
  $("#bControlla").textContent = S.Q && S.Q.rilievi.length ? "Controlla (" + S.Q.rilievi.length + ")" : "Controlla";
}
function renderSb() {
  const sb = $("#sb"); sb.replaceChildren();
  if (!S.P) { sb.append(h("span", {}, "Nessuna pratica aperta")); return; }
  const n = S.Q.rilievi.length;
  sb.append(...[h("span", {}, "Revisione " + S.P.revisione),
    S.salvata ? h("span", { class: "ok" }, "Salvata alle " + S.salvata) : null,
    nMod() ? h("span", { style: "color:var(--am)" }, nMod() + (nMod() === 1 ? " modifica non salvata" : " modifiche non salvate")) : null,
    n ? h("button", { onclick: () => { S.tab = "controlli"; renderIns(); } }, n + (n === 1 ? " rilievo" : " rilievi")) : h("span", {}, "Nessun rilievo"),
    h("span", {}, S.Q.finalizzabile ? "Finalizzabile nel perimetro supportato" : "Non finalizzabile"),
    h("span", {}, "Controllo ufficiale: non eseguito")].filter(Boolean));
}

/* ---------- albero dei quadri ---------- */
function renderAlbero() {
  const nav = $("#albero"); nav.replaceChildren();
  if (!S.Q) return;
  for (const [g, nome] of [["frontespizio", "Frontespizio"], ["quadri", "Quadri"], ["riepiloghi", "Riepiloghi"], ["lavoro", "Tabella di lavoro"]]) {
    nav.append(h("div", { class: "gruppo" }, nome));
    for (const q of S.Q.quadri.filter(x => x.gruppo === g)) {
      const st = q.stato;
      const testo = st === "rilievi" ? q.rilievi + (q.rilievi === 1 ? " rilievo" : " rilievi") : (q.righe && st === "compilato" ? q.righe + (q.righe === 1 ? " riga" : " righe") : STATI[st]);
      nav.append(h("button", { class: "voce", "data-stato": st, "data-q": q.id, "aria-current": S.sel === q.id ? "true" : "false", onclick: () => { S.sel = q.id; S.riga = null; render(); } },
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

/* ---------- vista centrale ---------- */
function appartiene(q, e) {
  if (q.coll === "persone") return !["defunto", "presentatore"].includes(e.ruolo);
  if (q.coll === "beni") { const t = e.tipo; return q.id === "EB" ? t === "terreno" : q.id === "EC" ? t === "fabbricato" : !["terreno", "fabbricato"].includes(t); }
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
  const q = quadro();
  if (!q) return;
  main.append(h("h1", {}, (q.id === "AN" || q.id === "DV" ? "" : q.id + " — ") + q.titolo));
  main.append(h("div", { class: "sottotitolo" }, q.nota || (q.vista === "tabella" || q.vista === "documenti" ? (q.righe + (q.righe === 1 ? " riga" : " righe")) : "")));
  if (!q.attivo && q.supportato) main.append(h("div", { class: "nota" }, "Questo quadro non è selezionato per la dichiarazione. ", h("button", { class: "lk", onclick: () => impostaQuadro(q.id, true) }, "Seleziona il quadro")));
  if (q.rilievi && q.vista !== "frontespizio") main.append(h("div", { class: "avv" }, h("b", {}, q.rilievi + (q.rilievi === 1 ? " rilievo" : " rilievi")), h("span", { style: "flex:1" }, rilievi().find(r => r.quadro === q.id).messaggio), h("button", { class: "gh", onclick: () => { S.tab = "controlli"; renderIns(); } }, "Vedi controlli")));
  if (q.vista === "frontespizio") renderFront(main);
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
  const key = "n:" + Date.now();
  S.nuove.set(key, { q: q.id, coll: q.coll, campi: { ...q.preset } });
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
  const nr = rilievi().length;
  const seg = h("div", { class: "seg", role: "tablist" }, [["dati", "Dati"], ["controlli", "Controlli" + (nr ? " (" + nr + ")" : "")], ["cronologia", "Cronologia"]].map(([k, n]) =>
    h("button", { role: "tab", "aria-selected": S.tab === k ? "true" : "false", onclick: () => { S.tab = k; renderIns(); } }, n)));
  ins.append(seg);
  if (S.tab === "dati") insDati(ins); else if (S.tab === "controlli") insControlli(ins); else insCronologia(ins);
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
  for (const [c, kind] of Object.entries(campi)) {
    ins.append(h("div", { class: "rg" }, h("label", {}, c.replaceAll("_", " ")), campoInput(q.coll, id, c, kind, valRiga(r, c), (campo, v) => {
      if (r.nuova) r.nuova.campi[campo] = v;
      else { const d = S.dirty.get(r.key) || { coll: q.coll, id, campi: {} }; d.campi[campo] = v; S.dirty.set(r.key, d); }
      renderVista(); aggiornaBottoni(); renderSb();
    })));
  }
  const az = h("div", { class: "az" }, h("button", { class: "pil", onclick: salvaTutto }, "Salva"));
  if (r.nuova || S.dirty.has(r.key)) az.append(h("button", { class: "gh", onclick: () => { r.nuova ? S.nuove.delete(r.key) : S.dirty.delete(r.key); if (r.nuova) S.riga = null; render(); } }, "Annulla modifiche"));
  if (r.e) az.append(h("button", { class: "lk", style: "color:var(--er)", onclick: async () => { if (confirm("Eliminare la riga?")) { S.riga = null; await salvaOps([{ op: "remove", coll: q.coll, id }]); } } }, "Elimina riga"));
  ins.append(az, h("p", { class: "mut mono", style: "margin-top:10px" }, r.e ? r.e.id : ""));
}
function insControlli(ins) {
  const q = S.Q;
  ins.append(h("p", { class: "mut" }, q.ambito + (q.finalizzabile ? ". Finalizzabile nel perimetro supportato." : ". Non finalizzabile.")));
  if (!q.rilievi.length) { ins.append(h("p", { class: "ok", style: "color:var(--ok);font-weight:600" }, "Nessun rilievo.")); return; }
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
      if (!confirm("Creare una nuova revisione con i dati della n. " + x.n + "?")) return;
      try { await post("/api/pratiche/" + S.P.pratica_id + "/ripristina", { revisione_attesa: S.P.revisione, a_revisione: x.n }); await ricarica(); render(); msg("Dati della revisione " + x.n + " ripristinati in una nuova revisione.", "o"); } catch (e) { msg(e.message, "e"); } } }, "Ripristina") : null;
    ins.append(h("div", { class: "rv" }, h("b", {}, "Revisione " + x.n), " · " + x.canale + " · " + x.autore, h("div", { class: "mut" }, x.ts), h("div", {}, x.sommario), b));
  }
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
  const e = persona(ruolo); const key = "f:" + ruolo; const campi = S.schema.collezioni.persone;
  const g = h("section", { class: "grp" }, h("h2", {}, titolo));
  for (const c of vis) {
    const cur = S.dirty.has(key) && c in S.dirty.get(key).campi ? S.dirty.get(key).campi[c] : (e ? e[c] : undefined);
    g.append(h("div", { class: "rg" }, h("label", {}, c.replaceAll("_", " ")), campoInput("persone", e && e.id, c, campi[c], cur, (campo, v) => {
      const d = S.dirty.get(key) || { coll: "persone", id: e ? e.id : null, campi: e ? {} : { ruolo } };
      d.campi[campo] = v; S.dirty.set(key, d); aggiornaBottoni(); renderSb();
    })));
  }
  return g;
}
function renderFront(main) {
  main.append(schedaPersona("Defunto", "defunto", ["cognome", "nome", "codice_fiscale", "data_nascita", "luogo_nascita", "data_decesso"]));
  main.append(schedaPersona("Presentatore della dichiarazione", "presentatore", ["cognome", "nome", "codice_fiscale", "data_nascita", "luogo_nascita", "relazione_con_defunto"]));
  const tipo = (S.P.dati.opzioni || {}).tipo_dichiarazione || "originaria";
  const sel = h("select", { "aria-label": "Tipo di dichiarazione" }, h("option", { value: "originaria" }, "Dichiarazione originaria"), h("option", { value: "sostitutiva" }, "Dichiarazione sostitutiva"));
  sel.value = tipo; sel.addEventListener("change", () => salvaOps([{ op: "set", sezione: "opzioni", campi: { tipo_dichiarazione: sel.value } }]));
  main.append(h("section", { class: "grp" }, h("h2", {}, "Tipo di dichiarazione"), h("div", { class: "rg" }, h("label", {}, "tipo"), sel),
    tipo === "sostitutiva" ? h("div", { class: "nota", style: "margin:8px 14px" }, "I dati della dichiarazione sostituita non sono ancora gestiti: la sostitutiva non è finalizzabile.") : null));
  const att = new Set(S.P.dati.opzioni.quadri_attivi || S.schema.predefiniti);
  const box = h("section", { class: "grp" }, h("h2", {}, "Quadri da compilare"));
  for (const q of S.schema.quadri.filter(x => x.gruppo !== "frontespizio" && x.id !== "DV")) {
    const cb = h("input", { type: "checkbox", id: "qa_" + q.id }); cb.checked = att.has(q.id);
    cb.addEventListener("change", () => impostaQuadro(q.id, cb.checked));
    box.append(h("label", { class: "chk", for: "qa_" + q.id }, cb, h("span", {}, q.id + " — " + q.titolo + (q.supportato ? "" : " (non ancora supportato)"))));
  }
  main.append(box);
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
async function salvaOps(ops) {
  try {
    const r = await post("/api/pratiche/" + S.P.pratica_id + "/aggiorna", { revisione_attesa: S.P.revisione, operazioni: ops, chiave: crypto.randomUUID() });
    const d = new Date(); S.salvata = String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
    msg("Salvato (revisione " + r.revisione + ").", "o");
    await ricarica(); render(); await caricaPratiche(); return true;
  } catch (e) {
    if (e.dati && e.dati.errori) msg(e.dati.errori.map(x => x.percorso + ": " + x.messaggio).join(" | "), "e");
    else if (e.stato === 409) { msg("La pratica è stata modificata altrove (" + e.message + "). Le tue modifiche non sono state applicate: controlla i dati aggiornati e salva di nuovo.", "e"); await ricarica(); render(); }
    else msg(e.message, "e");
    return false;
  }
}
async function salvaTutto() {
  if (!S.P) return;
  const ops = [];
  for (const d of S.dirty.values()) ops.push({ op: "upsert", coll: d.coll, ...(d.id ? { id: d.id } : {}), campi: { ...d.campi } });
  for (const n of S.nuove.values()) { const campi = Object.fromEntries(Object.entries(n.campi).filter(([, v]) => v !== null)); if (Object.keys(campi).length) ops.push({ op: "upsert", coll: n.coll, campi }); }
  if (!ops.length) { S.dirty.clear(); S.nuove.clear(); aggiornaBottoni(); return; }
  if (await salvaOps(ops)) { S.dirty.clear(); S.nuove.clear(); S.riga = null; render(); }
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
  const f = (k, label, ph) => h("div", { class: "campo" }, h("label", { for: "w_" + k }, label), h("input", { id: "w_" + k, value: d[k] || "", placeholder: ph || "", class: k === "codice_fiscale" ? "mono" : "", oninput: ev => { d[k] = ev.target.value; } }));
  if (W.passo === 0) c.append(h("p", { class: "mut" }, "Dati anagrafici del defunto. Potrai completarli o correggerli nel frontespizio."), h("div", { class: "griglia" }, f("cognome", "Cognome"), f("nome", "Nome"), f("codice_fiscale", "Codice fiscale"), f("data_nascita", "Data di nascita", "AAAA-MM-GG"), f("luogo_nascita", "Luogo di nascita"), f("data_decesso", "Data del decesso", "AAAA-MM-GG")));
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
function wizApri() { W.passo = 0; W.dati = {}; wizRender(); $("#wiz").showModal(); }
async function wizAvanti() {
  const d = W.dati;
  if (W.passo === 0 && !(d.cognome || "").trim()) { $("#wizErr").textContent = "Indica almeno il cognome del defunto."; return; }
  if (W.passo < PASSI.length - 1) { W.passo++; wizRender(); return; }
  const campi = {}; for (const k of ["cognome", "nome", "codice_fiscale", "data_nascita", "luogo_nascita", "data_decesso"]) if ((d[k] || "").trim()) campi[k] = k === "codice_fiscale" ? d[k].trim().toUpperCase() : d[k].trim();
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

$("#bNuova").onclick = wizApri;
$("#wAnnulla").onclick = () => $("#wiz").close();
$("#wIndietro").onclick = () => { W.passo--; wizRender(); };
$("#wAvanti").onclick = wizAvanti;
$("#bSalva").onclick = salvaTutto;
$("#bControlla").onclick = async () => { if (!S.P) return; if (nMod()) await salvaTutto(); S.Q = await api("/api/pratiche/" + S.P.pratica_id + "/quadri"); S.tab = "controlli"; render(); };
document.addEventListener("keydown", ev => { if ((ev.ctrlKey || ev.metaKey) && ev.key === "s") { ev.preventDefault(); salvaTutto(); } });
window.addEventListener("beforeunload", ev => { if (nMod()) { ev.preventDefault(); ev.returnValue = ""; } });
init();
