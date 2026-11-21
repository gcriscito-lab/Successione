"use strict";
/* Salvataggio delle modifiche e compilazione dal codice fiscale. */
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
    if (!(el.parentElement && el.parentElement.querySelector(".e.sv"))) { const id = "err_" + (++_nErr); el.after(h("div", { class: "e sv", id }, x.x.messaggio)); aggiungiDescrizione(el, id); }
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
  // quote scritte nella griglia: si salvano per prime, in una revisione loro (server: /quote-griglia)
  if (S.griglia && S.griglia.mod.size) { if (!(await salvaGriglia())) return false; if (!nMod()) return true; }
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

