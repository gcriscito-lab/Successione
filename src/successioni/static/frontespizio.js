"use strict";
/* Frontespizio, File e invio, documenti allegati. */
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
    griglia.append(h("div", { class: "rg", 'data-campo': c }, h("label", { title: lbl("persone", c) }, lbl("persone", c)), campoInput("persone", e && e.id, c, campi[c], cur, (campo, v) => {
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
    sez.append(h("div", { class: "rg" }, h("label", { for: id, title: etichetta }, etichetta), inp));
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
    sez.append(h("div", { class: "rg" + (sd.aiuto ? " con-aiuto" : "") }, h("label", { for: id, title: [sd.etichetta, sd.aiuto].filter(Boolean).join(". ") }, sd.etichetta), h("div", {}, inp, h("div", { class: "mut aiuto-voce" }, sd.aiuto), dett)));
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
    sez.append(h("div", { class: "rg" + (sd.aiuto ? " con-aiuto" : "") }, h("label", { for: id, title: [sd.etichetta, sd.aiuto].filter(Boolean).join(". ") }, sd.etichetta), h("div", {}, inp, h("div", { class: "mut aiuto-voce" }, sd.aiuto))));
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
      : h('p', { class: 'mut dentro-testo' }, 'Inserisci eredi e beni: l’elenco si compone da solo.'));   // 22/11/2026: tolta la nota sotto l'elenco (richiesta)
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
    sez.append(h("p", { class: "dentro-testo" }, h("a", { href: url, target: "_blank", rel: "noopener", id: "albero_apri",
      onclick: ev => { ev.preventDefault(); anteprima(url, "Albero genealogico — " + att.nome); } }, "Apri l'anteprima di " + att.nome)),
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
  const sez = zonaTrascina(h("section", { class: "grp allegati" }, h("h2", {}, "Aggiungi un documento"),
    h("p", { class: "mut dentro-testo" }, "Trascina qui un file oppure sceglilo; poi indica il rigo e conferma con il pulsante qui sotto.")));
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

