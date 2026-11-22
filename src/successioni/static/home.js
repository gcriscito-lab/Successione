"use strict";
/* Pagina iniziale: elenco delle pratiche, filtri, scadenze (parte di app.js fino al 21/11/2026). */
/* ---------- Pagina iniziale (revisione dell'08/11/2026) ----------
   Un solo elenco delle pratiche, ordinato per urgenza: per ogni pratica il defunto, il termine, l'avanzamento in cinque tappe e
   la prossima cosa da fare (server: cruscotto.py, ?tutte=1). Prima le stesse pratiche comparivano tre volte (colonna a
   sinistra, elenco, «Prossime azioni») con due modi diversi di dire la scadenza. */
const HOME = { filtro: "tutte", ordine: "urgenza", cerca: "" };
const FILTRI_HOME = { tutte: "Tutte", lavorare: "Da lavorare", vicine: "In scadenza (60 giorni)", superate: "Termine superato",
  senza_data: "Senza data del decesso", completate: "Completate" };
let CRUSCOTTO = null;   // ultimo stato delle pratiche calcolato dal server: { tappe, mappa: pratica_id -> stato }
function voceHome(p) {
  const st = CRUSCOTTO && CRUSCOTTO.mappa.get(p.id), tl = terminePresentazione(p.data_decesso);
  // il termine del server tiene conto della decorrenza indicata nel frontespizio; finche' non arriva vale quello dal decesso
  const termine = st && st.termine ? st.termine : tl ? { data: isoData(tl.data), giorni: tl.giorni, base: "decesso" } : null;
  return { ...p, termine, stato: st || null, completata: !!(st && st.completata) };
}
function filtraHome(voci, filtro, cerca) {
  const c = String(cerca || "").trim().toLowerCase();
  return voci.filter(v => {
    if (c && !String(v.titolo || "").toLowerCase().includes(c)) return false;
    const t = v.termine;
    return filtro === "lavorare" ? !!v.stato && !v.completata : filtro === "completate" ? v.completata
      : filtro === "vicine" ? !v.completata && !!t && t.giorni >= 0 && t.giorni <= 60
      : filtro === "superate" ? !v.completata && !!t && t.giorni < 0
      : filtro === "senza_data" ? !t : true;
  });
}
function ordinaHome(voci, ordine) {
  if (ordine === "recenti") return voci;   // ordine del server: ultima modifica prima
  if (ordine === "nome") return [...voci].sort((a, b) => String(a.titolo).localeCompare(String(b.titolo), "it"));
  // urgenza: prima da lavorare, poi completate; dentro, il termine piu' vicino (senza data in fondo)
  return [...voci].sort((a, b) => (a.completata - b.completata) || ((a.termine ? a.termine.giorni : 1e6) - (b.termine ? b.termine.giorni : 1e6)));
}
function riepilogoHome(voci) {
  const n = voci.length, parti = [n + (n === 1 ? " pratica" : " pratiche")];
  const conta = f => filtraHome(voci, f, "").length;
  if (CRUSCOTTO) { const l = conta("lavorare"); parti.push(l + " da lavorare"); }
  const vic = conta("vicine"), sup = conta("superate"), sd = conta("senza_data");
  if (vic) parti.push(vic + " in scadenza nei prossimi 60 giorni");
  if (sup) parti.push(sup + " con termine superato");
  if (sd) parti.push(sd + " senza data del decesso");
  return parti.join(" · ");
}
const titoloTermine = t => "Termine del " + dataIt(t.data) + (t.base === "decorrenza" ? ", dalla decorrenza del " + dataIt(t.dal) : ", dalla data del decesso");
function cellaTermine(v) {
  const t = v.termine;
  if (!t) return h("td", { class: "c-term" }, h("span", { class: "mut" }, "da indicare"));
  const gg = t.giorni, dec = t.base === "decorrenza" ? " dalla decorrenza" : "";
  const pill = v.completata ? null : gg < 0 ? h("span", { class: "pz er" }, "superato" + dec) : gg === 0 ? h("span", { class: "pz am" }, "oggi" + dec)
    : h("span", { class: "pz" + (gg <= 60 ? " am" : "") }, "tra " + gg + (gg === 1 ? " giorno" : " giorni") + dec);
  return h("td", { class: "c-term", title: titoloTermine(t) }, h("span", { class: "data-term" }, dataIt(t.data)), pill ? " " : null, pill);
}
function testoAzione(a) {
  if (!a) return "";
  const m = String((a.dove || {}).percorso || "").match(/^([a-z_]+)\[[^\]]+\]\.([a-z_]+)$/);
  const campo = m && S.schema.collezioni[m[1]] ? lbl(m[1], m[2], a.dove.sel) : null;
  return (campo ? campo.charAt(0).toUpperCase() + campo.slice(1) + ": " : "") + a.testo + (a.altri ? " (e altri " + a.altri + ")" : "");
}
function cellaAvanzamento(v) {
  if (!v.stato) return h("td", { class: "c-avanz mut" }, "…");
  const tappe = (CRUSCOTTO.tappe || []), stati = v.stato.tappe || {};
  const corrente = tappe.find(t => ["corrente", "problema"].includes(stati[t.id]));
  const descr = v.completata ? "Completata" : corrente ? corrente.nome : "";
  return h("td", { class: "c-avanz" },
    h("ol", { class: "tappe-mini", "aria-label": "Avanzamento: " + (v.completata ? "pratica completata" : "tappa " + descr) },
      tappe.map(t => h("li", { class: "tm " + (stati[t.id] || "da_fare"), title: t.nome + ": " + ({ fatto: "fatto", corrente: "in corso", problema: "da correggere" }[stati[t.id]] || "da fare") }))),
    h("span", { class: "tappa-nome" + (corrente && stati[corrente.id] === "problema" ? " er" : "") }, descr));
}
function cellaAzione(v) {
  if (!v.stato) return h("td", { class: "c-azione mut" }, "…");
  const a = v.stato.azione;
  if (!a || v.completata) return h("td", { class: "c-azione mut" }, v.completata ? "Nessuna" : "");
  return h("td", { class: "c-azione" }, h("button", { type: "button", class: "lk-azione" + (a.livello === "problema" ? " problema" : ""),
    onclick: ev => { ev.stopPropagation(); vaiAllAzione(v.stato); } },
    a.livello === "problema" ? h("span", { class: "segno-problema" }, "Da correggere") : null, h("span", { class: "testo-azione" }, testoAzione(a))));
}
function titoloHome(t) {
  const m = /^(.*\S)\s+[-–—]\s+([A-Z0-9]{16})$/i.exec(String(t || ""));
  return m ? [h("span", { class: "tit" }, m[1]), h("span", { class: "cf-tit" }, m[2].toUpperCase())] : [h("span", { class: "tit" }, t)];
}
function rigaHome(v) {
  const dec = v.data_decesso ? "Decesso " + dataIt(v.data_decesso) : "Data del decesso da indicare";
  return h("tr", { class: v.completata ? "completata" : null, "data-pratica": v.id },
    h("td", { class: "c-pratica" }, h("button", { type: "button", class: "apri-pratica", onclick: () => apri(v.id), title: "Apri la pratica" },
      ...titoloHome(v.titolo), h("span", { class: "dett" }, dec))),
    cellaTermine(v), cellaAvanzamento(v), cellaAzione(v));
}
function filtriHome(box) {
  let f = $("#homeFiltri");
  if (!f) {
    const chips = h("div", { class: "chips", role: "group", "aria-label": "Mostra" });
    const cerca = h("input", { type: "search", "aria-label": "Cerca nel titolo", placeholder: "Cerca una pratica", oninput: ev => { HOME.cerca = ev.target.value; renderHome(); } });
    const ordine = h("select", { "aria-label": "Ordina", onchange: ev => { HOME.ordine = ev.target.value; renderHome(); } },
      h("option", { value: "urgenza" }, "Ordina per urgenza"), h("option", { value: "recenti" }, "Ultime modificate"), h("option", { value: "nome" }, "Per nome"));
    f = h("div", { id: "homeFiltri", class: "filtri-home" }, chips, h("div", { class: "filtri-destra" }, cerca, ordine));
    box.before(f);
  }
  return f;
}
function renderHome() {
  const box = $("#elencoPratiche"); if (!box) return;
  document.body.classList.toggle("in-home", !S.P); if (window.compattaBarra) window.compattaBarra();   // anche all'avvio, prima del primo render()
  // con una pratica aperta l'elenco non serve (e le sue righe non devono confondersi con quelle dei quadri): si ricostruisce al ritorno
  if (S.P) { box.replaceChildren(); return; }
  const vuoto = !S.pratiche.length;
  $("#homeTitolo").textContent = vuoto ? "Prima dichiarazione" : "Pratiche";
  $("#percorso").hidden = !vuoto; box.hidden = vuoto; $("#homeNota").hidden = vuoto;
  const voci = S.pratiche.map(voceHome);
  $("#homeIntro").textContent = vuoto ? "L’archivio non contiene ancora pratiche. Crea la prima oppure importa un file telematico già preparato." : riepilogoHome(voci);
  const f = filtriHome(box); f.hidden = vuoto;
  if (vuoto) { box.replaceChildren(h("div", { class: "vuoto-illustrato vuoto-home" }, h("img", { src: "/static/vuoto_home.svg", alt: "", "aria-hidden": "true", class: "illustrazione" }))); statoHome(); return; }
  const chips = f.querySelector(".chips"); chips.replaceChildren();
  for (const [k, nome] of Object.entries(FILTRI_HOME)) {
    const n = filtraHome(voci, k, "").length;
    if (k !== "tutte" && k !== HOME.filtro && (!n || (["lavorare", "completate"].includes(k) && !CRUSCOTTO))) continue;   // solo i filtri utili
    chips.append(h("button", { type: "button", class: "chip", "aria-pressed": HOME.filtro === k ? "true" : "false",
      onclick: () => { HOME.filtro = k; renderHome(); } }, nome, h("span", { class: "n" }, String(n))));
  }
  const righe = ordinaHome(filtraHome(voci, HOME.filtro, HOME.cerca), HOME.ordine);
  box.replaceChildren(righe.length ? h("table", { class: "tab-pratiche" },
    h("colgroup", {}, h("col", { class: "k-pratica" }), h("col", { class: "k-termine" }), h("col", { class: "k-avanz" }), h("col", { class: "k-azione" })),
    h("thead", {}, h("tr", {}, h("th", { scope: "col" }, "Pratica"), h("th", { scope: "col", title: "Dodici mesi dal decesso o dalla decorrenza" }, "Termine"),
      h("th", { scope: "col" }, "Avanzamento"), h("th", { scope: "col" }, "Prossima azione"))),
    h("tbody", {}, righe.map(rigaHome))) : h("p", { class: "mut nessuna" }, "Nessuna pratica corrisponde al filtro."));
  statoHome();
  caricaCruscotto();
}
/* Stato delle pratiche dal server (cinque tappe e prossima azione): al massimo ogni 5 secondi e solo sulla pagina iniziale. */
let cruscottoGen = 0;
async function caricaCruscotto() {
  if (S.P || !S.pratiche.length) return;
  const firma = S.pratiche.map(p => p.id + ":" + p.revisione).join(",");
  if (firma === caricaCruscotto.firma && Date.now() - (caricaCruscotto.quando || 0) < 5000) return;
  caricaCruscotto.firma = firma; caricaCruscotto.quando = Date.now();
  const gen = ++cruscottoGen;
  let c;
  try { c = await api("/api/cruscotto?tutte=1"); } catch (e) { if (gen === cruscottoGen) msg("Stato delle pratiche non disponibile: " + e.message, "e"); return; }
  if (gen !== cruscottoGen || S.P) return;
  CRUSCOTTO = { tappe: c.tappe, mappa: new Map(c.pratiche.map(v => [v.pratica_id, v])) };
  renderHome();
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
/* filtro per termine sui dati dell'elenco (usato anche dalle prove dell'interfaccia) */
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
  S.fornitoreDirty = {}; S.griglia = null;
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
  mostraTerminePratica();
}
/* Scadenza dentro la pratica (15/11/2026, da DEAS): il termine lo calcola il server con la regola della pagina iniziale
   (cruscotto._termine: dal decesso, o dalla decorrenza del frontespizio se successiva), letto dai dati salvati dopo ogni
   ricaricamento. Senza data del decesso non si mostra nulla. */
async function mostraTerminePratica() {
  const el = $("#terminePratica"); if (!el || !S.P) return;
  const pid = S.P.pratica_id, rev = S.P.revisione;
  let t = null;
  try { t = (await api("/api/pratiche/" + pid + "/termine")).termine; } catch (_) { t = null; }
  if (!S.P || S.P.pratica_id !== pid || S.P.revisione !== rev) return;   // risposta superata da un altro caricamento
  el.hidden = !t; if (!t) return;
  const gg = t.giorni, gi = n => n + (n === 1 ? " giorno" : " giorni");
  el.className = "termine-pratica pz" + (gg < 0 ? " er" : gg <= 60 ? " am" : "");
  el.title = titoloTermine(t);
  el.textContent = "Presentare entro " + dataIt(t.data) + " · " + (gg < 0 ? "scaduto da " + gi(-gg) : gg === 0 ? "scade oggi" : "tra " + gi(gg));
  if (window.compattaBarra) window.compattaBarra();
}
function render() {
  const aperta = !!S.P;
  $("#vuoto") && ($("#vuoto").hidden = aperta);
  // pagina iniziale: niente colonna dei quadri e niente comandi della pratica (sarebbero spenti); tornano aprendo una pratica
  document.body.classList.toggle("in-home", !aperta); if (window.compattaBarra) window.compattaBarra();
  if (aperta) { const e = $("#elencoPratiche"); if (e) e.replaceChildren(); }   // righe della pagina iniziale fuori dal DOM
  const q = aperta ? quadro() : null;
  // 22/11/2026 (revisione dell'altra chat): con la griglia predefinita un comando che punta a una riga (Aggiungi, Duplica, Incolla,
  // «Vai al dato», salto al primo errore) apre l'elenco, altrimenti la riga resterebbe invisibile; solo per la sessione
  if (q && grigliaAperta(q) && S.riga) S.vistaDV = "elenco";
  // quadro con una sola riga: si apre gia' selezionata (report grafica 07/11/2026, punto 2)
  if (q && q.coll && !grigliaAperta(q) && !S.riga && S.tab === "dati" && S.chiuso !== q.id) { const rr = righeQuadro(q); if (rr.length === 1) S.riga = rr[0].key; }
  // il pannello di destra resta chiuso finche' non c'e' una riga selezionata (o una scheda Controlli/Cronologia aperta):
  // senza selezione occupava un quarto dello schermo per dire «Seleziona una riga»
  const conTabella = q && q.coll && !grigliaAperta(q);   // nella griglia delle quote niente pannello della riga
  // sempre booleano: con undefined (quadri senza tabella, es. AN) classList.toggle invertiva la classe a ogni ridisegno e
  // lasciava una colonna vuota di 360-400 px a destra
  const pannello = !!(aperta && S.sel !== 'FILE' && (S.tab !== 'dati' || (conTabella && !!S.riga)));
  $("#app").classList.toggle("conIns", pannello); $("#ins").hidden = !pannello; $('#ridimensiona').hidden = !pannello;
  renderAlbero(); renderVista(); renderIns(); renderSb(); aggiornaBottoni();
}
function aggiornaBottoni() {
  const n = nMod();
  $("#bSalva").className = n ? "pil" : "gh"; $("#bNuova").className = "gh";   // senza pratica aperta l'azione principale e' nella pagina iniziale
  $("#bSalva").disabled = !n || S.writeBusy; $("#bSalva").textContent = S.writeBusy ? "Salvataggio…" : n ? "Salva (" + n + ")" : "Salva";
  $("#bControlla").disabled = !S.P; $("#bGenera").disabled = !S.P; $("#bGenera").title = "Apri l'area unica File e invio della pratica";
  $('#bGenera').setAttribute('aria-pressed', String(S.sel === 'FILE'));
  const nDaSist = S.Q ? S.Q.rilievi.length + perIlFile().length : 0;
  $("#bControlla").textContent = nDaSist ? "Controlla (" + nDaSist + ")" : "Controlla";
}
function renderSb() {
  const sb = $("#sb"); sb.replaceChildren();
  const arch = STUDIO.archivio ? h("span", { class: "arch", title: STUDIO.archivio }, "Archivio: " + STUDIO.archivio.split(/[\\/]/).filter(Boolean).pop()) : null;
  if (!S.P) { sb.append(...[arch, h("span", {}, "Nessuna pratica aperta")].filter(Boolean)); return; }
  const n = S.Q.rilievi.length, pf = perIlFile().length;
  const aiControlli = vaiControlli;
  sb.append(...[arch, h("span", {}, "Revisione " + S.P.revisione),
    S.salvata ? h("span", { class: "ok" }, "Salvata alle " + S.salvata) : null,
    nMod() ? h("span", { class: "am" }, nMod() + (nMod() === 1 ? " modifica non salvata" : " modifiche non salvate")) : null,
    n ? h("button", { onclick: aiControlli }, n + (n === 1 ? " rilievo" : " rilievi")) : null,
    pf ? h("button", { class: "am", onclick: aiControlli, title: "Cose da sistemare prima di generare il file" }, pf + (pf === 1 ? " punto" : " punti") + " da sistemare per il file") : null,
    !n && !pf ? h("span", {}, "Nessun rilievo") : null,
    (S.Q.avvisi || []).length ? h("button", { class: "am", onclick: vaiControlli }, S.Q.avvisi.length + (S.Q.avvisi.length === 1 ? " avviso" : " avvisi")) : null,
    h("span", {}, S.Q.finalizzabile ? "File generato e aggiornato" : (S.Q.blocchi_finalizzazione || []).length ? "File da generare" : "Non finalizzabile")].filter(Boolean));
}
function chiudiErroreVecchio() { const m = $("#msg"); if (m && !m.hidden && m.className === "e") msg(""); }
function vaiFile() { if (!S.P) return; chiudiErroreVecchio(); S.sel = 'FILE'; S.riga = null; S.tab = 'dati'; $('#vista').scrollTop = 0; render(); }
function scegliQuadro(id, tuttiImmobili = false) { chiudiErroreVecchio(); S.sel = id; S.riga = null; S.chiuso = null; S.tab = 'dati'; S.immobiliTutti = tuttiImmobili; $('#vista').scrollTop = 0; render(); }
function chiudiPannello() { const q = quadro(); S.chiuso = q ? q.id : null; S.riga = null; S.tab = "dati"; render(); tornaTabella(); }

