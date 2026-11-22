"use strict";
/* Pannello dati della riga selezionata (ispettore) e dati strutturati. */
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
/* Pannello del quadro: solo i dati della riga (14/11/2026). I controlli di tutta la pratica stanno in cima a «File e invio»
   (Controlla, barra in basso), la cronologia nel menu Operazioni. */
function renderIns() {
  const ins = $("#ins"); ins.replaceChildren();
  S.tab = "dati";
  if (!S.P || S.sel === 'FILE') return;
  if (S.riga) ins.append(h("button", { class: "lk solo-mobile", onclick: tornaTabella }, "↑ Torna alla tabella"));
  insDati(ins);
}
/* Controlla, barra in basso e avvisi del quadro portano qui: in cima a «File e invio», con «Vai al dato» per ogni voce. */
function vaiControlli() {
  if (!S.P) return;
  vaiFile();
  const vai = (n = 0) => { const el = document.getElementById("controlliFile"); if (el) { $("#vista").scrollTop = 0; document.scrollingElement.scrollTop = 0; const t = el.querySelector("h2"); if (t) { t.tabIndex = -1; t.focus({ preventScroll: true }); } } else if (n < 40) setTimeout(() => vai(n + 1), 50); };
  vai();
}
/* Cronologia delle modifiche in una finestra (menu Operazioni e File e invio). */
function apriCronologia() {
  if (!S.P) return;
  const corpo = h("div", { class: "cronologia-corpo" });
  const d = h("dialog", { id: "dCronologia", class: "guida", "aria-label": "Cronologia delle modifiche" },
    h("form", { method: "dialog" }, h("h2", {}, "Cronologia delle modifiche"), corpo,
      h("div", { class: "wiz-az" }, h("button", { class: "gh", value: "chiudi" }, "Chiudi"))));
  d.addEventListener("close", () => d.remove());
  document.body.append(d); d.showModal();
  insCronologia(corpo, () => d.isConnected);
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
  // stile moderno: le etichette sono tutte uguali e i dati richiesti hanno un pallino (il nome intero lo dice nel suggerimento)
  if ((OBBLIGATORI[q.id] || []).length && document.documentElement.dataset.stile === "classico") ins.append(h("p", { class: "legenda-obbl" }, "In grassetto i dati richiesti dal quadro."));
  const visibili = q.campi ? new Set(q.campi) : (((S.schema.ordine || {})[q.id]) ? new Set(S.schema.ordine[q.id]) : null);   // solo i campi pertinenti al quadro; uno gia' valorizzato resta visibile
  const ordine = ordinati(q.id, Object.keys(campi));
  const gruppi = q.coll === "beni" || q.id === "EA" ? GRUPPI_SCHEDA[q.id] : null, righeCampi = [];
  let lista = null;   // campi delle schede senza gruppi: un contenitore, impaginato su piu' colonne con il pannello sotto
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
    if (aiuto) {   // nella scheda compatta l'aiuto compare entrando nel campo; resta sempre la descrizione accessibile del campo
      const idA = "aiuto_" + q.coll + "_" + c;
      w.append(h("div", { class: "mut aiuto-voce", id: idA }, aiuto));
      const f = w.querySelector("input, select, textarea"); if (f) aggiungiDescrizione(f, idA);
    }
    const obbl = (OBBLIGATORI[q.id] || []).includes(c);
    // il suggerimento dell'etichetta riporta sempre il nome intero (nella scheda compatta l'etichetta si accorcia su una riga)
    const titoloEt = [lbl(q.coll, c, q.id), obbl ? "dato richiesto nel quadro " + q.id : "", aiuto || ""].filter(Boolean).join(". ");
    const breve = ETICHETTE_BREVI[c];
    const rg = h("div", { class: "rg" + (obbl ? " obbl" : "") + (aiuto ? " con-aiuto" : ""), "data-campo": c }, h("label", { title: titoloEt },
      breve ? [h("span", { class: "et-intera" }, lbl(q.coll, c, q.id)), h("span", { class: "et-breve", "aria-hidden": "true" }, breve)] : lbl(q.coll, c, q.id)), w);
    if (gruppi) righeCampi.push([c, rg, vuoto]);
    else { if (!lista) { lista = h("div", { class: "campi-lista" }); ins.append(lista); } lista.append(rg); }
  }
  if (gruppi) ins.append(h("div", { class: "gruppi-scheda" }, ...schedaAGruppi(gruppi, righeCampi)));   // con il pannello sotto: gruppi affiancati
  if (q.coll === "beni" && ["EB", "EC"].includes(q.id)) {   // codice comune calcolato dal nome (report grafico DEAS 08/11/2026, proposta 4)
    propostaCodiceComune(q, r, ins);
    for (const c of ["comune", "provincia"]) { const el = ins.querySelector('.rg[data-campo="' + c + '"] input, .rg[data-campo="' + c + '"] select');
      if (el) el.addEventListener("change", () => propostaCodiceComune(q, r, ins)); }
  }
  if (nascostiEstero) ins.append(h("p", { class: "mut nota-campi" }, "Per un immobile all'estero scegli la provincia EE: compaiono i campi dello Stato estero."));
  renderStrutturati(ins, q, r);
  // riquadri della riga: con il pannello sotto stanno affiancati invece che uno sotto l'altro (versione 0.3)
  const extra = h("div", { class: "extra-scheda" });
  if (q.coll === "beni" && r.e && ["fabbricato", "terreno"].includes(valRiga(r, "tipo"))) extra.append(boxValoreCatastale(q, r));
  if (q.coll === "beni" && r.e) extra.append(boxDevoluzioniBene(r));            // voce 22: somma delle quote del bene
  // voce 33 tolta il 14/11/2026 («che senso ha mettere sotto i dati dell'erede tutti i dati della successione?»): i beni per
  // erede si vedono nel quadro DV e nel brogliaccio; il ruolo e la parentela sono gia' nei campi della scheda
  if (r.e) extra.append(boxAppunti(q, r));                                        // voce 10: nota interna della riga
  if (extra.childElementCount) ins.append(extra);
  const az = h("div", { class: "az" }, h("button", { class: "pil", onclick: salvaTutto }, "Salva"));
  const supKey = q.coll + ':' + (r.e ? r.e.id : r.nuova.id);
  if (r.nuova || S.dirty.has(r.key) || S.supDirty.has(supKey)) az.append(h("button", { class: "gh", onclick: () => { r.nuova ? S.nuove.delete(r.key) : S.dirty.delete(r.key); S.supDirty.delete(supKey); if (r.nuova) S.riga = null; render(); } }, "Annulla modifiche"));
  if (r.e) az.append(h("button", { class: "lk pericolo", onclick: async () => {
    if (S.writeBusy) return msg("Salvataggio in corso: attendi prima di eliminare la riga.", "e");
    const nomeRiga = etichetta(q.coll, r.e), posRiga = righeQuadro(q).findIndex(x => x.key === r.key) + 1;
    const descr = nomeRiga && nomeRiga !== r.e.id ? "«" + nomeRiga + "»" : posRiga ? "n. " + posRiga : "selezionata";
    const el = opsEliminazione(q.coll, id);
    if (confirm("Eliminare la riga " + descr + " dal quadro " + q.id + (q.titolo ? " (" + q.titolo + ")" : "") + "?" + el.nota)) await salvaOps(el.ops, () => {
      S.dirty.delete(r.key); S.supDirty.delete(supKey); S.riga = null;
    });
  } }, "Elimina riga"));
  ins.append(az);   // 14/11/2026: niente identificativo tecnico della riga sotto Salva
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
    ins.append(h('h3', { class: 'con-aiuto', title: sd.aiuto || '' }, 'Agevolazione (prima casa, riduzioni)'));
    ins.append(campoStrutturato(sd, valore('agevolazioni'), v => { scrivi('agevolazioni', v); renderIns(); }, null));
    ins.append(h('div', { class: 'mut aiuto-voce' }, sd.aiuto));
    if (bene && ['P', 'X', 'Z'].includes(attuale) && quadroBene(bene) !== 'EC')
      ins.append(h('div', { class: 'nota stretta' }, 'Il bene collegato non è un fabbricato del quadro EC: i codici P, X, Z sono ammessi solo lì e l\'esportazione segnalerà un errore.'));
    const rd = (S.schema.strutturati || {})['devoluzioni.riduzioni'];
    ins.append(h('h3', { class: 'con-aiuto', title: rd.aiuto || '' }, 'Riduzione art. 25 comma 1'));
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
    altri.append(h('h3', {}, 'Precedenti successioni o donazioni'), h('div', { class: 'rg' + (vp.aiuto ? ' con-aiuto' : '') }, h('label', { for: 'vps_' + id, title: [vp.etichetta, vp.aiuto].filter(Boolean).join('. ') }, vp.etichetta), h('div', {}, inp, h('div', { class: 'mut aiuto-voce' }, vp.aiuto))));
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
  ins.append(h("p", { class: "mut" }, q.ambito + "."));
  const el = elencoPerIlFile();
  if (el) ins.append(h("section", { class: "per-il-file" }, h("h3", {}, "Per generare il file manca"), el));
  // avvisi che non impediscono la finalizzazione (es. visure catastali vecchie o senza data)
  // ogni rilievo e avviso con il rimedio: dove intervenire e con quale comando (docs/ANALISI_REPLICA_2026-11-07.md, voce 19)
  const rimedio = x => x.rimedio ? h("div", { class: "rimedio" }, h("b", {}, "Come risolvere: "), x.rimedio) : null;
  // avvisi dello stesso tipo in un solo riquadro, con l'elenco dei dati (report 09/11/2026, punto 5): non otto riquadri uguali
  const perTipo = new Map();
  for (const a of (q.avvisi || [])) { const k = a.codice || a.messaggio; if (!perTipo.has(k)) perTipo.set(k, []); perTipo.get(k).push(a); }
  for (const gruppo of perTipo.values()) {
    const a = gruppo[0];
    if (gruppo.length === 1) { ins.append(h("div", { class: "nota stretta", role: "status" }, h("b", {}, "Avviso: "), a.messaggio, rimedio(a),
      a.quadro && a.percorso ? h("button", { class: "lk", onclick: () => vaiA(a) }, "Vai al dato") : null)); continue; }
    const uguali = gruppo.every(x => x.messaggio === a.messaggio);
    // dati di quadri diversi (EB ed EC): il rimedio non nomina un quadro solo (revisione 14/11/2026, E7)
    const misti = new Set(gruppo.map(x => x.quadro)).size > 1;
    const rim = misti && a.rimedio ? { rimedio: a.rimedio.replace(/ \(quadro [A-Z]{2}\)/g, "") } : a;
    ins.append(h("div", { class: "nota stretta avvisi-gruppo", role: "status" }, h("b", {}, "Avviso, " + gruppo.length + " dati: "), uguali ? a.messaggio : null, rimedio(rim),
      h("ul", { class: "avvisi-elenco" }, gruppo.map(x => h("li", {}, h("span", {}, nomeDatoAvviso(x) + (uguali ? "" : ": " + x.messaggio)),
        x.quadro && x.percorso ? h("button", { class: "lk", onclick: () => vaiA(x) }, "Vai al dato") : null)))));
  }
  if (!q.rilievi.length) { if (!el) ins.append(h("p", { class: "ok esito-ok" }, "Nessun rilievo: il file si può generare.")); return; }
  const ul = h("ul", { class: "rl" });
  for (const r of q.rilievi) ul.append(h("li", {}, h("button", { onclick: () => vaiA(r) }, h("span", { class: "sigla" }, r.quadro), h("span", {}, h("div", {}, r.messaggio), rimedio(r), h("div", { class: "cod" }, r.codice + " · " + r.percorso)))));
  ins.append(ul);
}
/* Cio' che blocca «Genera file» (server: quadri().per_il_file, revisione di usabilita' del 14/11/2026): un solo elenco, uguale
   nei Controlli, in File e invio e nei quadri calcolati, ogni voce con «Vai al dato». */
function perIlFile() { return (S.Q && S.Q.per_il_file) || []; }
function elencoPerIlFile() {
  const voci = perIlFile(); if (!voci.length) return null;
  return h("ul", { class: "elenco-azioni per-il-file-voci" }, voci.map(x => h("li", { class: "er" },
    h("span", {}, testoPerIlFile(x)), x.rimedio ? h("div", { class: "rimedio" }, x.rimedio) : null,
    x.quadro ? h("button", { class: "lk", onclick: () => vaiA(x) }, "Vai al dato") : null)));
}
function testoPerIlFile(x) {
  try { const d = descriviErrore(x); if (d.coll) return d.testo; } catch (_) { /* testo semplice */ }
  const t = String(x.messaggio || ""); return (x.quadro && x.quadro !== "FILE" ? "Quadro " + x.quadro + ": " : "") + t.charAt(0).toUpperCase() + t.slice(1);
}
/* «Fabbricato Roma fg.100 p.200 sub.3 (EC)»: la riga a cui si riferisce l'avviso, dal percorso «coll[id].campo». */
function nomeDatoAvviso(x) {
  const m = String(x.percorso || "").match(/^([a-z_]+)\[([^\]]+)\]/);
  const e = m && (S.P.dati[m[1]] || []).find(y => y.id === m[2]);
  return (e ? etichetta(m[1], e) : (x.percorso || "dato")) + (x.quadro ? " (" + x.quadro + ")" : "");
}
async function insCronologia(ins, attiva = () => true) {
  ins.append(h("p", { class: "mut" }, "Ogni salvataggio crea una revisione. Il ripristino non cancella la cronologia."));
  let lista;
  try { lista = await api("/api/pratiche/" + S.P.pratica_id + "/revisioni"); }
  catch (e) { if (attiva()) { ins.append(h("p", { class: "err" }, e.message)); msg(e.message, "e"); } return; }
  if (!attiva()) return;
  for (const x of lista.slice().reverse()) {
    const b = x.n !== S.P.revisione ? h("button", { class: "gh spazio-su", onclick: async () => {
      if (S.writeBusy || nMod()) return msg("Completa il salvataggio delle modifiche prima di ripristinare una revisione.", "e");
      if (!confirm("Creare una nuova revisione con i dati della n. " + x.n + "?")) return;
      S.writeBusy = true; aggiornaBottoni();
      try { await post("/api/pratiche/" + S.P.pratica_id + "/ripristina", { revisione_attesa: S.P.revisione, a_revisione: x.n }); const dc = document.getElementById("dCronologia"); if (dc) dc.close(); await ricarica(); render(); msg("Dati della revisione " + x.n + " ripristinati in una nuova revisione.", "o"); } catch (e) { msg(e.message, "e"); }
      finally { S.writeBusy = false; aggiornaBottoni(); } } }, "Ripristina") : null;
    ins.append(h("div", { class: "rv" }, h("b", {}, "Revisione " + x.n), " · " + x.canale + " · " + x.autore, h("div", { class: "mut" }, x.ts), h("div", {}, x.sommario), b));
  }
}
const PILLOLE = { registrata: "ok", da_sistemare: "am", non_generato: "", aggiornato: "ok", valido: "ok", positivo: "ok", senza_rilievi: "ok", negativo: "er", non_valido: "er", con_rilievi: "am", obsoleto: "am", non_eseguito: "", non_preparata: "" };
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
  const controlli = h('section', { class: 'grp controlli-file', id: 'controlliFile' }, h('h2', {}, 'Controlli della pratica'));
  insControlli(controlli);
  controlli.append(h('div', { class: 'az' }, h('button', { class: 'gh', type: 'button', onclick: apriCronologia }, 'Cronologia delle modifiche')));
  const stato = h('section', { class: 'grp riepilogo' }, h('h2', {}, 'Stato della dichiarazione'));
  const nAvv = ((S.Q && S.Q.avvisi) || []).length;   // come nella barra in basso: rilievi e avvisi insieme (report 09/11/2026, punto 7)
  const nPf = perIlFile().length;
  stato.append(riga_stato('Dati', nPf && st.dati.stato === 'senza_rilievi' ? 'da_sistemare' : st.dati.stato, st.dati.rilievi + (st.dati.rilievi === 1 ? ' rilievo' : ' rilievi') + ' · ' + nAvv + (nAvv === 1 ? ' avviso' : ' avvisi')
      + (nPf ? ' · ' + nPf + (nPf === 1 ? ' punto' : ' punti') + ' da sistemare per il file' : '')),
    riga_stato('File XML', ex.generato ? ex.stato : 'non_generato', ex.generato ? (ex.completo ? 'Completo nel perimetro supportato' : 'Bozza tecnica: non trasmissibile') : 'Nessun file generato'),
    riga_stato('Struttura del file', st.xsd.stato), riga_stato('Controllo ufficiale', ct.stato, ct.versione_controllo),
    riga_stato('Trasmissione', st.trasmissione.stato, st.trasmissione.nota));
  const reg = (S.P.dati.note || {}).registrazione;   // estremi dall'attestazione conservata (ricevute dai download)
  if (reg && reg.volume) stato.append(riga_stato('Registrazione', 'registrata', 'Volume ' + reg.volume + ' n. ' + reg.numero + '/' + reg.anno +
    (reg.ufficio ? ', ' + reg.ufficio : '') + (reg.data_presentazione ? ', presentata il ' + dataIt(reg.data_presentazione) : '')));
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
  const daRubrica = h('select', { 'aria-label': 'Scegli dalla rubrica', class: 'da-rubrica' }, h('option', { value: '' }, 'Scegli dalla rubrica…'));
  rubrica().then(voci => { for (const v of voci) daRubrica.append(h('option', { value: v.id }, v.nome + ' · ' + v.codice_fiscale)); daRubrica.hidden = !voci.length; });
  daRubrica.addEventListener('change', () => { const v = (RUBRICA || []).find(x => x.id === daRubrica.value); if (!v) return;
    cfIn.value = v.codice_fiscale; modifica('cf', v.codice_fiscale);
    if (v.ruolo === 'intermediario') { tipoIn.value = '10'; modifica('tipo', '10'); dettagli.hidden = false; }
    daRubrica.value = ''; msg('Fornitore preso dalla rubrica: ' + v.nome + '. Premi «Salva profilo» per confermarlo.', 'o'); });
  fornitore.append(h('label', {}, 'Codice fiscale del fornitore', cfIn), daRubrica, h('label', {}, 'Tipo fornitore', tipoIn), dettagli,
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
      // l'esito resta scritto nel passo 2 (non un messaggio che sparisce); le avvertenze tecniche restano nel registro del file
      S.esitoFile = { pid, rev: S.P && S.P.revisione, ok: !!r.generato, testo: r.generato ? (r.completo ? 'File generato e valido per lo schema.' : 'Bozza tecnica generata. ' + r.avvertenza)
        : 'File non generato: nessun file parziale è stato prodotto.', motivi: r.generato ? [] : motivi,
        // avvertenze utili al professionista; quelle interne (mappa dei campi, compressione) restano nel registro del file
        avvisi: (r.avvisi || []).map(a => a.messaggio).filter(t => !/docs\/|DEFLATE|campo di lavoro interno/.test(t)) };
      if (!r.generato) msg('File non generato: i motivi sono elencati nel passo 2.', 'e');
      else msg(S.esitoFile.testo, r.completo ? 'o' : 'e');
      if (r.backup && r.backup.errore) msg('Attenzione: backup automatico non riuscito (' + r.backup.errore + ')', 'e');
      else if (r.backup && r.backup.eseguito) STUDIO.ultimoBackup = r.backup.nome;
      if (S.P && S.P.pratica_id === pid) { await ricarica(); render(); }
    } catch (e) { msg(e.message, 'e'); }
  });
  if (perIlFile().length) elaborati.append(h('p', { class: 'nota stretta' }, 'Prima di generare il file sistema i punti elencati in «Controlli della pratica», in cima alla pagina.'));
  elaborati.append(h('p', { class: 'mut' }, 'Genera il file quando i dati sono pronti. La bozza tecnica conserva evidenza dei limiti e non è trasmissibile.'),
    h('div', { class: 'az' }, h('button', { class: 'pil', disabled: OCCUPATI.has('esporta'), onclick: esegui('completo') }, 'Genera file'),
      h('button', { class: 'gh', disabled: OCCUPATI.has('esporta'), onclick: esegui('bozza_tecnica') }, 'Genera bozza tecnica')));
  const esito = S.esitoFile && S.esitoFile.pid === pid && S.esitoFile.rev === S.P.revisione ? S.esitoFile : null;
  if (esito && (!esito.ok || esito.avvisi.length)) elaborati.append(h('div', { class: 'esito-file' + (esito.ok ? ' ok' : ' er'), role: 'status' }, h('b', {}, esito.testo),
    esito.motivi.length ? h('ul', {}, esito.motivi.map(t => h('li', {}, t))) : null,
    esito.avvisi.length ? [h('div', {}, 'Avvertenze:'), h('ul', {}, esito.avvisi.map(t => h('li', {}, t)))] : null));
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
    controllo.append(zonaTrascina(h('div', { class: 'sotto' }, h('h3', {}, 'Carica l’esito del controllo eseguito a mano'),
      h('p', { class: 'mut' }, 'Puoi trascinare qui insieme i file .dgn, _logSchema.xml e .wri: ognuno va nel suo campo.'),
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
      }) }, 'Registra esito')))));
  }
  const stampa = passo(4, 'Stampa e rileggi', (st.stampa_modello || {}).stato === 'aggiornata');
  stampa.append(h('p', { class: 'mut' }, 'Rileggi il modello stampato prima di inviare: confronta immobili, eredi, quote e imposte con i documenti.'),
    h('div', { class: 'az' }, h('button', { class: 'gh', disabled: !fileOk || OCCUPATI.has('stampa'), onclick: occupato('stampa', async () => {
      if (nMod()) return msg('Salva le modifiche e rigenera il file prima della stampa.', 'e');
      try { const r = await post('/api/pratiche/' + pid + '/stampa-modello', {}); msg('Modello ministeriale generato (' + r.pagine + ' pagine). Prova locale: controllane il contenuto prima di usarlo.', 'o'); anteprima('/api/pratiche/' + pid + '/stampa-modello.pdf', 'Modello ministeriale'); }
      catch (e) { msg(e.message, 'e'); }
    }) }, 'Stampa modello ministeriale'),
      ex.generato ? linkAnteprima('/api/pratiche/' + pid + '/prospetto-cliente', 'Prospetto per il cliente',
        'Riepilogo per gli eredi: beni, quote, passività e imposte, con gli stessi importi del file') : null,
      ex.generato ? linkAnteprima('/api/pratiche/' + pid + '/stampa?job=' + ex.job_id, 'Prospetto tecnico del file') : null));
  const invio = passo(5, 'Invio e ricevute', st.trasmissione.stato === 'trasmessa' && st.trasmissione.modalita !== 'simulata', { id: 'invioPratica' });
  griglia.append(controlli, stato, fornitore, elaborati, controllo, stampa, invio, strumentiStudio(pid));
  await renderInvio(invio, ex, ct);
  // ricevute scaricate dal professionista: si cercano nella cartella dei download (15/11/2026)
  const trovate = h("div", { class: "ricevute-download" });
  invio.append(h("h3", {}, "Ricevute scaricate"),
    h("p", { class: "mut" }, "Scarica le ricevute dall'area riservata dell'Agenzia con il tuo browser, poi cercale qui: il programma le riconosce e le conserva nella pratica."),
    h("div", { class: "az" }, h("button", { class: "gh", type: "button", onclick: () => cercaRicevute(trovate, pid) }, "Cerca nei download"),
      h("a", { class: "lk", href: "https://telematici.agenziaentrate.gov.it", target: "_blank", rel: "noopener noreferrer" }, "Apri l'area riservata dell'Agenzia")), trovate);
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
        zonaTrascina(h("div", { class: "az" }, esi, h("button", { class: "gh", disabled: OCCUPATI.has("riconcilia"), onclick: registraEsi }, "Registra file .esi"))));
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
  ins.append(zonaTrascina(h('div', { class: 'ricevuta-nuova' }, h('p', { class: 'mut' }, 'Scegli o trascina qui il documento ricevuto, poi indica tipo ed esito.'),
    tipo, esito, file, h('button', { disabled: OCCUPATI.has('ricevuta'), onclick: occupato('ricevuta', async () => {
    const f = file.files[0]; if (!f) return msg('Scegli il documento ricevuto.', 'e');
    try {
      await api(url + '?' + new URLSearchParams({ tipo: tipo.value, esito: esito.value, nome: f.name }), { method: 'POST', body: await f.arrayBuffer() });
      msg('Ricevuta originale acquisita e associata al protocollo.', 'o'); renderVista();
    } catch (e) { msg(e.message, 'e'); }
  }) }, 'Acquisisci ricevuta'))));
  for (const doc of stato.documenti) ins.append(h('p', { class: 'mut' }, h('a', { href: url + '/file/' + doc.job_id, download: '' }, doc.nome), ' · ' + doc.tipo + ' · ' + (doc.esito || '') + ' · SHA-256 ' + doc.sha256));
}
function vaiA(r) {
  if (r.quadro === "FILE") { vaiFile(); setTimeout(() => { const f = document.querySelector("#fornitore input"); if (f) { f.scrollIntoView({ block: "center" }); f.focus(); } }, 300); return; }
  S.sel = r.quadro;
  const m = r.percorso.match(/^([a-z_]+)\[([^\]]+)\]/);
  const q = quadro();
  S.riga = m && q && q.coll === m[1] ? "e:" + m[1] + ":" + m[2] : null;
  S.tab = "dati"; render();
  const el = document.querySelector('[data-path="' + CSS.escape(r.percorso) + '"]');
  if (el) { el.scrollIntoView({ block: "center" }); el.focus(); }
}

