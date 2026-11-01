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
const S = { schema: null, pratiche: [], P: null, Q: null, sel: "AN", dirty: new Map(), nuove: new Map(), aperto: false };
const STATI = { vuoto: "da compilare", compilato: "compilato", rilievi: "rilievi", non_supportato: "non supportato", inattivo: "non selezionato" };

async function api(url, opt) {
  const r = await fetch(url, opt);
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(j.messaggio || j.codice || r.statusText), { dati: j, stato: r.status });
  return j;
}
const post = (u, b) => api(u, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b) });
function msg(t, tipo) { const m = $("#msg"); m.textContent = t || ""; m.className = tipo || ""; m.hidden = !t; }

/* ---- valori ---- */
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
const entita = (coll, id) => (S.P.dati[coll] || []).find(e => e.id === id);
function etichetta(coll, e) {
  if (coll === "persone") return [e.cognome, e.nome].filter(Boolean).join(" ") || e.id;
  if (coll === "beni") return [e.tipo, e.comune, e.foglio && "fg." + e.foglio, e.particella && "p." + e.particella, e.subalterno && "sub." + e.subalterno, e.descrizione].filter(Boolean).join(" ") || e.id;
  return e.id;
}
function rilieviCampo(path) { return (S.Q ? S.Q.rilievi : []).filter(r => r.percorso === path); }

/* ---- caricamento ---- */
async function init() {
  try {
    const i = await api("/api/info");
    $("#info").textContent = "Versione " + i.versione + ". Accesso solo da questo computer. PDF/A: Ghostscript " + (i.pdfa.ghostscript ? "presente" : "assente") + ", veraPDF " + (i.pdfa.veraPDF ? "presente" : "non configurato");
    S.schema = await api("/api/schema");
    await caricaPratiche();
  } catch (e) { msg("Avvio non riuscito: " + e.message, "e"); }
}
async function caricaPratiche() {
  S.pratiche = await api("/api/pratiche");
  const ul = $("#lista"); ul.replaceChildren();
  if (!S.pratiche.length) ul.append(h("li", { class: "mut" }, "Nessuna pratica."));
  for (const p of S.pratiche) ul.append(h("li", {}, h("button", { "aria-current": S.P && S.P.pratica_id === p.id ? "true" : "false", onclick: () => apri(p.id) }, h("span", {}, p.titolo), h("span", { class: "mut" }, "rev. " + p.revisione))));
}
async function apri(id, sel) {
  if (S.dirty.size && !confirm("Ci sono modifiche non salvate: continuare senza salvarle?")) return;
  S.dirty.clear(); S.nuove.clear();
  await ricarica(id);
  S.sel = sel || "AN"; render(); await caricaPratiche();
}
async function ricarica(id) {
  id = id || S.P.pratica_id;
  S.P = await api("/api/pratiche/" + id);
  S.Q = await api("/api/pratiche/" + id + "/quadri");
  $("#titolo").textContent = S.P.titolo + " — revisione " + S.P.revisione;
  for (const b of ["#bControlla"]) $(b).disabled = false;
  $("#bSalva").disabled = !S.dirty.size && !S.nuove.size;
  aggiornaControlli();
}
function render() {
  $("#vuoto") && ($("#vuoto").hidden = true);
  renderAlbero(); renderVista();
}

/* ---- albero dei quadri ---- */
function renderAlbero() {
  const nav = $("#albero"); nav.replaceChildren();
  if (!S.Q) return;
  const gruppi = [["frontespizio", "Frontespizio"], ["quadri", "Quadri"], ["riepiloghi", "Riepiloghi"], ["lavoro", "Tabella di lavoro"]];
  for (const [g, nome] of gruppi) {
    nav.append(h("div", { class: "gruppo" }, nome));
    for (const q of S.Q.quadri.filter(x => x.gruppo === g)) {
      const st = q.stato;
      const testo = st === "rilievi" ? q.rilievi + (q.rilievi === 1 ? " rilievo" : " rilievi") : (q.righe && st === "compilato" ? q.righe + (q.righe === 1 ? " riga" : " righe") : STATI[st]);
      nav.append(h("button", { class: "voce" + (st === "inattivo" ? " inattivo" : ""), "data-stato": st, "data-q": q.id, "aria-current": S.sel === q.id ? "true" : "false", onclick: () => { S.sel = q.id; render(); } },
        h("span", { class: "sigla" }, q.id), h("span", { class: "nome" }, q.titolo), h("span", { class: "st" }, testo)));
    }
  }
}

/* ---- vista ---- */
function renderVista() {
  const main = $("#vista"); main.replaceChildren();
  const q = S.Q.quadri.find(x => x.id === S.sel);
  if (!q) return;
  main.append(h("h1", {}, (q.id === "AN" || q.id === "DV" ? "" : q.id + " — ") + q.titolo));
  if (q.nota) main.append(h("p", { class: "sottotitolo" }, q.nota));
  if (!q.attivo && q.supportato) main.append(h("div", { class: "nota" }, "Questo quadro non è selezionato per la dichiarazione. Selezionalo nel frontespizio per compilarlo.", " ", h("button", { onclick: () => impostaQuadro(q.id, true) }, "Seleziona il quadro")));
  if (q.vista === "frontespizio") renderFront(main);
  else if (q.vista === "non_supportato") renderNonSupp(main, q);
  else { renderTabella(main, q); if (q.vista === "documenti") renderAllegati(main); }
}
function renderNonSupp(main, q) {
  main.append(h("div", { class: "nota" }, "Il quadro " + q.id + " non è ancora supportato (" + (q.motivo || "") + "). I dati già inseriti altrove restano conservati; finché il quadro è selezionato la dichiarazione non può essere finalizzata."));
  const att = q.attivo;
  main.append(h("div", { class: "barra" }, h("button", { onclick: () => impostaQuadro(q.id, !att) }, att ? "Deseleziona il quadro" : "Seleziona il quadro (blocca la finalizzazione)")));
}
async function impostaQuadro(id, on) {
  const cur = new Set((S.P.dati.opzioni.quadri_attivi) || S.schema.predefiniti);
  on ? cur.add(id) : cur.delete(id);
  await salvaOps([{ op: "set", sezione: "opzioni", campi: { quadri_attivi: [...cur] } }]);
}

/* ---- campi ---- */
function campoInput(coll, id, rowKey, campo, kind, val, onMod) {
  const path = id ? coll + "[" + id + "]." + campo : null;
  const err = path ? rilieviCampo(path) : [];
  let el;
  if (kind.startsWith("enum:")) {
    el = h("select", { "aria-label": campo }, h("option", { value: "" }, ""), kind.slice(5).split("|").map(o => h("option", { value: o }, o)));
    el.value = val || "";
  } else if (kind.startsWith("ref:")) {
    const rc = kind.slice(4);
    el = h("select", { "aria-label": campo }, h("option", { value: "" }, ""), (S.P.dati[rc] || []).map(e => h("option", { value: e.id }, etichetta(rc, e))));
    el.value = val || "";
  } else {
    el = h("input", { "aria-label": campo, class: (kind === "cf" ? "mono" : kind === "importo" || kind === "quota" ? "num" : ""), placeholder: kind === "quota" ? "1/2" : kind === "data" ? "AAAA-MM-GG" : "" });
    el.value = mostra(kind, val);
  }
  if (path) el.dataset.path = path;
  if (err.length) el.classList.add("bad");
  el.addEventListener("input", () => onMod(campo, leggi(kind, el.value)));
  el.addEventListener("change", () => onMod(campo, leggi(kind, el.value)));
  return h("div", {}, el, err.map(r => h("div", { class: "e" }, r.messaggio)));
}
function segnaModifica() { $("#bSalva").disabled = !S.dirty.size && !S.nuove.size; $("#bSalva").textContent = (S.dirty.size + S.nuove.size) ? "Salva modifiche (" + (S.dirty.size + S.nuove.size) + ")" : "Salva modifiche"; }

/* ---- tabella di quadro ---- */
function appartiene(q, e) {
  if (q.coll === "persone") return !["defunto", "presentatore"].includes(e.ruolo);
  if (q.coll === "beni") { const t = e.tipo; return q.id === "EB" ? t === "terreno" : q.id === "EC" ? t === "fabbricato" : !["terreno", "fabbricato"].includes(t); }
  return true;
}
function renderTabella(main, q) {
  const campi = S.schema.collezioni[q.coll];
  const righe = (S.P.dati[q.coll] || []).filter(e => appartiene(q, e));
  const t = h("table");
  t.append(h("thead", {}, h("tr", {}, q.colonne.map(c => h("th", {}, c.replaceAll("_", " "))), h("th", {}))));
  const tb = h("tbody"); t.append(tb);
  for (const e of righe) tb.append(riga(q, campi, e, "e:" + q.coll + ":" + e.id));
  for (const [k, n] of S.nuove) if (n.q === q.id) tb.append(riga(q, campi, null, k));
  if (!righe.length && ![...S.nuove.values()].some(n => n.q === q.id)) tb.append(h("tr", {}, h("td", { colspan: q.colonne.length + 1, class: "mut" }, "Nessuna riga. Usa «Aggiungi riga».")));
  main.append(h("div", { class: "tab" }, t));
  main.append(h("p", { class: "mut" }, "Quote: 1/2 · importi con il punto: 1234.50 · dato non noto: ? oppure [assente], [zero], [non_applicabile]."));
  main.append(h("div", { class: "barra" }, h("button", { class: "p", onclick: () => { S.nuove.set("n:" + Date.now(), { q: q.id, coll: q.coll, campi: { ...q.preset } }); segnaModifica(); renderVista(); } }, "Aggiungi riga")));
}
function riga(q, campi, e, key) {
  const nuova = !e; const stato = nuova ? S.nuove.get(key) : null;
  const tr = h("tr", { class: (nuova || S.dirty.has(key)) ? "mod" : "" });
  for (const c of q.colonne) {
    const val = nuova ? stato.campi[c] : (S.dirty.has(key) && c in S.dirty.get(key).campi ? S.dirty.get(key).campi[c] : e[c]);
    tr.append(h("td", {}, campoInput(q.coll, e && e.id, key, c, campi[c], val, (campo, v) => {
      if (nuova) { stato.campi[campo] = v; }
      else { const d = S.dirty.get(key) || { coll: q.coll, id: e.id, campi: {} }; d.campi[campo] = v; S.dirty.set(key, d); tr.className = "mod"; }
      segnaModifica();
    })));
  }
  const az = h("td", { class: "az" });
  if (nuova) az.append(h("button", { class: "l", onclick: () => { S.nuove.delete(key); segnaModifica(); renderVista(); } }, "Annulla"));
  else {
    if (S.dirty.has(key)) az.append(h("button", { class: "l", onclick: () => { S.dirty.delete(key); segnaModifica(); renderVista(); } }, "Annulla"));
    az.append(h("button", { class: "l", onclick: async () => { if (confirm("Eliminare la riga?")) await salvaOps([{ op: "remove", coll: q.coll, id: e.id }]); } }, "Elimina"));
    az.append(h("div", { class: "mut mono", style: "font-size:11px" }, e.id));
  }
  tr.append(az); return tr;
}

/* ---- frontespizio ---- */
function persona(ruolo) { return (S.P.dati.persone || []).find(p => p.ruolo === ruolo); }
function schedaPersona(titolo, ruolo, campiVis) {
  const e = persona(ruolo); const key = "f:" + ruolo;
  const campi = S.schema.collezioni.persone;
  const sc = h("section", { class: "scheda" }, h("h2", {}, titolo));
  const g = h("div", { class: "griglia" });
  for (const c of campiVis) {
    const cur = S.dirty.has(key) && c in S.dirty.get(key).campi ? S.dirty.get(key).campi[c] : (e ? e[c] : undefined);
    g.append(h("div", { class: "campo" }, h("label", {}, c.replaceAll("_", " ")), campoInput("persone", e && e.id, key, c, campi[c], cur, (campo, v) => {
      const d = S.dirty.get(key) || { coll: "persone", id: e ? e.id : null, campi: e ? {} : { ruolo }, nuovo: !e };
      d.campi[campo] = v; S.dirty.set(key, d); segnaModifica();
    })));
  }
  sc.append(g); return sc;
}
function renderFront(main) {
  main.append(h("p", { class: "sottotitolo" }, "Dati del defunto e del presentatore, tipo di dichiarazione e quadri da compilare."));
  main.append(schedaPersona("Defunto", "defunto", ["cognome", "nome", "codice_fiscale", "data_nascita", "luogo_nascita", "data_decesso"]));
  main.append(schedaPersona("Presentatore della dichiarazione", "presentatore", ["cognome", "nome", "codice_fiscale", "data_nascita", "luogo_nascita", "relazione_con_defunto"]));
  const tipo = (S.P.dati.opzioni || {}).tipo_dichiarazione || "originaria";
  const sel = h("select", { "aria-label": "Tipo di dichiarazione" }, h("option", { value: "originaria" }, "Dichiarazione originaria"), h("option", { value: "sostitutiva" }, "Dichiarazione sostitutiva"));
  sel.value = tipo; sel.addEventListener("change", () => salvaOps([{ op: "set", sezione: "opzioni", campi: { tipo_dichiarazione: sel.value } }]));
  main.append(h("section", { class: "scheda" }, h("h2", {}, "Tipo di dichiarazione"), h("div", { class: "campo", style: "max-width:320px" }, sel),
    tipo === "sostitutiva" ? h("p", { class: "nota" }, "I dati della dichiarazione sostituita non sono ancora gestiti: la sostitutiva non è finalizzabile.") : null));
  const att = new Set(S.P.dati.opzioni.quadri_attivi || S.schema.predefiniti);
  const box = h("section", { class: "scheda" }, h("h2", {}, "Quadri da compilare"));
  for (const q of S.schema.quadri.filter(x => x.gruppo !== "frontespizio" && x.id !== "DV")) {
    const cb = h("input", { type: "checkbox", id: "qa_" + q.id }); cb.checked = att.has(q.id);
    cb.addEventListener("change", () => impostaQuadro(q.id, cb.checked));
    box.append(h("label", { class: "chk", for: "qa_" + q.id }, cb, h("span", {}, q.id + " — " + q.titolo, q.supportato ? "" : "  (non ancora supportato)")));
  }
  main.append(box);
}

/* ---- documenti ---- */
async function renderAllegati(main) {
  const a = await api("/api/pratiche/" + S.P.pratica_id + "/allegati");
  const info = h("section", { class: "scheda" }, h("h2", {}, "Allegati e conversione in PDF/A"));
  const f = h("div", { class: "barra" }, h("input", { type: "file", id: "file", "aria-label": "File da caricare", style: "max-width:260px" }),
    h("input", { id: "teg", placeholder: "Tipo documento EG", "aria-label": "Tipo documento EG", style: "max-width:200px" }),
    h("input", { id: "fin", placeholder: "Finalità o beneficiario", "aria-label": "Finalità", style: "max-width:240px" }),
    h("button", { class: "p", onclick: async () => {
      const file = $("#file").files[0]; if (!file) return msg("Scegli un file.", "e");
      const fd = new FormData(); fd.append("file", file); fd.append("tipo_eg", $("#teg").value); fd.append("finalita", $("#fin").value);
      try { await api("/api/pratiche/" + S.P.pratica_id + "/allegati", { method: "POST", body: fd }); msg("Allegato acquisito (originale conservato).", "o"); renderVista(); } catch (e) { msg(e.message, "e"); }
    } }, "Carica"));
  info.append(f);
  const t = h("table", {}, h("thead", {}, h("tr", {}, ["nome", "ruolo", "byte", "analisi", "PDF/A", ""].map(x => h("th", {}, x)))));
  const tb = h("tbody"); t.append(tb);
  for (const x of a) {
    const an = x.analisi || {}; const rap = x.rapporto;
    const pdfa = rap ? ((rap.validazione || {}).esito || "") + (((rap.validazione || {}).verifica_indicativa) ? " (indicativo: " + rap.validazione.verifica_indicativa.esito + ")" : "") + ((rap.avvisi || []).length ? " — " + rap.avvisi.join("; ") : "") : (an.dichiara_pdfa ? "dichiara " + an.dichiara_pdfa + " (non verificato)" : "");
    tb.append(h("tr", {}, h("td", {}, x.nome), h("td", {}, x.ruolo), h("td", { class: "num" }, x.bytes), h("td", {}, (an.esito || "") + ((an.avvisi || []).length ? " — " + an.avvisi.join("; ") : "")), h("td", {}, pdfa),
      h("td", {}, x.ruolo === "originale" && ["leggibile", "firmato"].includes(an.esito) ? h("button", { onclick: async () => { try { const r = await api("/api/allegati/" + x.id + "/pdfa", { method: "POST" }); msg("Conversione eseguita. Esito validazione: " + r.esito + (r.esito === "non_verificato" ? " (serve veraPDF per attestare la conformità)." : "."), r.esito === "conforme" ? "o" : "e"); renderVista(); } catch (e) { msg(e.message, "e"); } } }, "Converti in PDF/A") : null)));
  }
  if (!a.length) tb.append(h("tr", {}, h("td", { colspan: 6, class: "mut" }, "Nessun allegato.")));
  info.append(h("div", { class: "tab" }, t));
  info.append(h("p", { class: "mut" }, "Un PDF convertito non prova che il documento sia firmato o sufficiente. La conformità PDF/A è attestata solo da un validatore indipendente."));
  main.append(info);
}

/* ---- salvataggio ---- */
async function salvaOps(ops) {
  try {
    const r = await post("/api/pratiche/" + S.P.pratica_id + "/aggiorna", { revisione_attesa: S.P.revisione, operazioni: ops, chiave: crypto.randomUUID() });
    msg("Salvato (revisione " + r.revisione + ").", "o");
    await ricarica(); render(); await caricaPratiche(); return true;
  } catch (e) {
    if (e.dati && e.dati.errori) { msg(e.dati.errori.map(x => x.percorso + ": " + x.messaggio).join(" | "), "e"); }
    else if (e.stato === 409) { msg("La pratica è stata modificata altrove (" + e.message + "). Le tue modifiche non sono state applicate: controlla i dati aggiornati e salva di nuovo.", "e"); await ricarica(); render(); }
    else msg(e.message, "e");
    return false;
  }
}
async function salvaTutto() {
  const ops = [];
  for (const d of S.dirty.values()) {
    const campi = Object.fromEntries(Object.entries(d.campi));
    ops.push({ op: "upsert", coll: d.coll, ...(d.id ? { id: d.id } : {}), campi });
  }
  for (const n of S.nuove.values()) {
    const campi = Object.fromEntries(Object.entries(n.campi).filter(([, v]) => v !== null));
    if (Object.keys(campi).length) ops.push({ op: "upsert", coll: n.coll, campi });
  }
  if (!ops.length) { S.dirty.clear(); S.nuove.clear(); segnaModifica(); return; }
  if (await salvaOps(ops)) { S.dirty.clear(); S.nuove.clear(); segnaModifica(); renderVista(); }
}

/* ---- controlli ---- */
function aggiornaControlli() {
  const q = S.Q; if (!q) return;
  const n = q.rilievi.length;
  $("#bControlla").textContent = n ? "Controlla (" + n + ")" : "Controlla";
  if (!$("#controlli").hidden) renderControlli();
}
function renderControlli() {
  const q = S.Q; $("#controlli").hidden = false;
  $("#cTitolo").textContent = q.rilievi.length ? q.rilievi.length + " rilievi" : "Nessun rilievo";
  $("#cAmbito").textContent = q.ambito + (q.finalizzabile ? " — finalizzabile nel perimetro supportato" : " — non finalizzabile");
  const ul = $("#cLista"); ul.replaceChildren();
  for (const r of q.rilievi) ul.append(h("li", {}, h("button", { onclick: () => vaiA(r) }, h("span", { class: "sigla" }, r.quadro), h("span", {}, h("div", {}, r.messaggio), h("div", { class: "cod" }, r.codice + " · " + r.percorso)))));
}
function vaiA(r) {
  S.sel = r.quadro; render();
  const el = document.querySelector('[data-path="' + CSS.escape(r.percorso) + '"]');
  if (el) { el.scrollIntoView({ block: "center" }); el.focus(); }
}

/* ---- procedura guidata ---- */
const W = { passo: 0, dati: {} };
const PASSI = ["Defunto", "Tipo", "Quadri", "Conferma"];
function wizRender() {
  const ol = $("#wizPassi"); ol.replaceChildren(...PASSI.map((p, i) => h("li", { "aria-current": i === W.passo ? "step" : "false" }, (i + 1) + ". " + p)));
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
      c.append(h("label", { class: "chk", for: "wq_" + q.id }, cb, h("span", {}, q.id + " — " + q.titolo, q.supportato ? "" : "  (non ancora supportato: blocca la finalizzazione)")));
    }
  }
  if (W.passo === 3) c.append(h("p", {}, "Verrà creata la dichiarazione «" + titoloWiz() + "» con " + (d.quadri || S.schema.predefiniti).length + " quadri selezionati, tipo " + (d.tipo || "originaria") + "."), h("p", { class: "mut" }, "Potrai completare ogni dato nei quadri; i controlli ti mostreranno cosa manca."));
}
const titoloWiz = () => "Successione " + [W.dati.cognome, W.dati.nome].filter(Boolean).join(" ").trim() || "Nuova dichiarazione";
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
  } catch (e) { $("#wizErr").textContent = e.dati && e.dati.errori ? e.dati.errori.map(x => x.messaggio).join(" | ") : e.message; if (e.dati && e.dati.errori) { W.passo = 0; wizRender(); $("#wizErr").textContent = e.dati.errori.map(x => x.messaggio).join(" | "); } }
}

$("#bNuova").onclick = wizApri;
$("#wAnnulla").onclick = () => $("#wiz").close();
$("#wIndietro").onclick = () => { W.passo--; wizRender(); };
$("#wAvanti").onclick = wizAvanti;
$("#bSalva").onclick = salvaTutto;
$("#bControlla").onclick = async () => { if (!S.P) return; if (S.dirty.size || S.nuove.size) await salvaTutto(); S.Q = await api("/api/pratiche/" + S.P.pratica_id + "/quadri"); renderControlli(); renderAlbero(); };
$("#cChiudi").onclick = () => { $("#controlli").hidden = true; };
document.addEventListener("keydown", ev => { if ((ev.ctrlKey || ev.metaKey) && ev.key === "s") { ev.preventDefault(); if (S.P) salvaTutto(); } });
window.addEventListener("beforeunload", ev => { if (S.dirty.size || S.nuove.size) { ev.preventDefault(); ev.returnValue = ""; } });
init();
