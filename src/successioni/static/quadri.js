"use strict";
/* Elenco dei quadri, campi, vista centrale (tabelle), valore catastale, piccole comodita' e miglioramenti del 07/11. */
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
      const st = statoInElenco(q);
      const lav = statoLavoro(q.id);   // stato di lavorazione scelto dallo studio (voce 10), dopo lo stato calcolato
      const testo = [st === "rilievi" ? q.rilievi + (q.rilievi === 1 ? " rilievo" : " rilievi") : (q.righe && st === "compilato" ? q.righe + (q.righe === 1 ? " riga" : " righe") : STATI[st]),
        lav && STATI_LAVORO[lav]].filter(Boolean).join(" · ");
      nav.append(h("button", { class: "voce", "data-stato": st, "data-lavoro": lav || null, "data-q": q.id, title: q.id + " — " + q.titolo + (testo ? " (" + testo + ")" : "") + tastoVoce(q.id), "aria-current": S.sel === q.id ? "true" : "false", onclick: () => scegliQuadro(q.id) },
        h("span", { class: "sigla" }, q.id), h("span", { class: "testi" }, h("span", { class: "nome" }, TITOLI_BREVI[q.id] || q.titolo), st === "inattivo" && !lav ? null : h("span", { class: "st" }, testo))));
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
/* Errori di un campo: ogni messaggio ha un id ed e' aggiunto alla descrizione accessibile del campo (senza togliere l'aiuto),
   e il campo e' marcato come non valido: lo sente anche chi usa un lettore di schermo. */
let _nErr = 0;
function aggiungiDescrizione(el, id) {
  const ids = (el.getAttribute("aria-describedby") || "").split(/\s+/).filter(Boolean);
  if (!ids.includes(id)) el.setAttribute("aria-describedby", [...ids, id].join(" "));
}
function erroriCampo(el, err) {
  if (!err.length) return [];
  el.setAttribute("aria-invalid", "true");
  return err.map(r => { const id = "err_" + (++_nErr); aggiungiDescrizione(el, id); return h("div", { class: "e", id }, r.messaggio); });
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
    el = h("select", { name: campo, "aria-label": lbl(coll, campo) }, h("option", { value: "" }, ""), (S.P.dati[rc] || []).filter(e => !(coll === "devoluzioni" && rc === "persone" && e.ruolo === "defunto" && e.id !== val))   // il defunto non riceve (E6)
      .map(e => h("option", { value: e.id }, etichetta(rc, e))));
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
  return h("div", {}, el, erroriCampo(el, err));
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
    el.title = (el.selectedOptions[0] ? el.selectedOptions[0].textContent : "") + (o && o.aiuto ? " — " + o.aiuto : "");
  };
  const f = () => { mostraAiuto(); onMod(leggi("str", el.value)); };
  el.addEventListener("change", f);
  mostraAiuto();
  return h("div", {}, el, dett, erroriCampo(el, err));
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
  const testoTitolo = (q.id === "AN" || q.id === "DV" ? "" : q.id + " — ") + q.titolo;
  const conSigla = !(q.id === "AN" || q.id === "DV");
  const titoloQ = h("h1", { title: testoTitolo, class: conSigla ? "con-sigla" : null },
    conSigla ? h("span", { class: "sigla-titolo", "aria-hidden": "true" }, q.id) : null,
    conSigla ? h("span", { class: "vh" }, q.id + " — ") : null, h("span", { class: "testo-titolo" }, q.titolo));   // se non sta su una riga si accorcia: il testo intero resta nel suggerimento
  const arg = typeof argomentoDelQuadro === "function" ? argomentoDelQuadro(q.id) : null;
  const linkIstr = arg ? h("button", { class: "lk istr-quadro", title: "Apre le istruzioni ufficiali alla pagina " + arg.pagina, onclick: () => apriIstruzioni(arg.documento, arg.pagina) }, "Istruzioni del quadro") : null;
  main.append(h("div", { class: "testa-quadro" }, titoloQ, linkIstr, q.coll && (q.vista === "tabella" || q.vista === "documenti") && q.supportato ? menuOperazioni(q) : null));
  // stato di lavorazione del quadro (voce 10: nota interna) nella riga sotto il titolo, per non spostare il menu «Operazioni»
  main.append(h("div", { class: "sottotitolo" }, q.nota || (q.vista === "tabella" || q.vista === "documenti" ? contaRighe(q) : ""), " ", selettoreStato(q)));
  if (!q.attivo && q.supportato) main.append(h("div", { class: "nota" }, "Questo quadro non è selezionato per la dichiarazione. ", h("button", { class: "lk", onclick: () => impostaQuadro(q.id, true) }, "Seleziona il quadro")));
  if (q.rilievi && q.vista !== "frontespizio") main.append(h("div", { class: "avv" }, h("b", {}, q.rilievi + (q.rilievi === 1 ? " rilievo" : " rilievi")), h("span", { class: "cresce" }, rilievi().find(r => r.quadro === q.id).messaggio), h("button", { class: "gh", onclick: vaiControlli }, "Vedi controlli")));
  if (q.vista === "frontespizio") renderFront(main);
  else if (q.vista === "derivato") main.append(h("div", { class: "nota" }, q.nota || "Quadro generato automaticamente dal programma."));
  else if (q.generato && ["EE", "EF", "EH"].includes(q.id)) renderAnteprima(main, q);
  else if (q.vista === "non_supportato") renderNonSupp(main, q);
  else if (grigliaAperta(q)) { main.append(selettoreVistaDV()); renderGrigliaQuote(main); }
  else { if (q.id === "DV") main.append(selettoreVistaDV()); renderTabella(main, q); if (q.vista === "documenti") renderAllegati(main); }
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
// «2.820 €» anche sotto i 10.000 (in italiano il separatore delle migliaia di norma si omette a quattro cifre: negli importi no)
const euroIt = (v, dec) => { const n = Number(v); return isNaN(n) ? String(v) : n.toLocaleString("it-IT", { minimumFractionDigits: dec ?? (String(v).includes(".") ? 2 : 0), maximumFractionDigits: 2, useGrouping: "always" }) + " €"; };
async function renderAnteprima(main, q) {
  const pid = S.P.pratica_id;
  main.append(h("div", { class: "calcolato riquadro-calc" }, h("span", { class: "etich-calc" }, "calcolato"), " Il quadro " + q.id + " è calcolato dal programma con i dati salvati della pratica, come nel file della dichiarazione. " +
    (nMod() ? "Ci sono modifiche non salvate: salva per aggiornare questa vista." : "")));
  const box = h("div", { class: q.id === "EH" ? "anteprima-eh" : null }, h("p", { class: "mut" }, "Calcolo in corso…")); main.append(box);
  let r;
  try { r = await api("/api/pratiche/" + pid + "/anteprima-quadri"); } catch (e) { box.replaceChildren(h("div", { class: "avv" }, e.message)); return; }
  if (!S.P || S.P.pratica_id !== pid || !quadro() || quadro().id !== q.id) return;
  box.replaceChildren();
  if (q.id === "EE") {
    if (!r.ee.length) box.append(h("p", { class: "mut" }, "Nessun totale calcolabile: vedi i motivi qui sotto."));
    else if (r.ee_righi) box.append(prospettoEE(r.ee_righi));
    else box.append(h("div", { class: "tab piatta" }, h("table", {}, h("tbody", {}, r.ee.map(x => h("tr", { class: ["TotaleAttivo", "TotaleValoreAsseEreditarioNetto"].includes(x.campo) ? "fisso forte" : "fisso" },
      h("td", {}, VOCI_EE[x.campo] || x.campo), h("td", { class: "n" }, euroIt(x.valore, 2))))))));
  } else if (q.id === "EF") {
    if (!r.ef) box.append(h("p", { class: "mut" }, "Imposte non calcolabili finché non si risolvono i punti qui sotto."));
    else box.append(h("div", { class: "tab piatta prospetto-ef" }, h("table", { "aria-label": "Liquidazione delle imposte (quadro EF)" }, h("tbody", {},
      r.ef.imposte.map(([k, v]) => h("tr", { class: "fisso" }, h("td", {}, k), h("td", { class: "n" }, isNaN(Number(v)) ? v : euroIt(v, 2)))),
      h("tr", { class: "fisso forte" }, h("td", {}, "Totale da versare (EF19)"), h("td", { class: "n" }, r.ef.totale ? euroIt(r.ef.totale, 2) : "—")),
      r.ef.importo_da_versare && r.ef.importo_da_versare !== r.ef.totale ? h("tr", { class: "fisso" }, h("td", {}, "Importo da versare (frontespizio, con sanzioni e interessi)"), h("td", { class: "n" }, euroIt(r.ef.importo_da_versare, 2))) : null))));
  } else if (q.id === "EH") {
    if (r.eh_dettaglio) box.append(...dettaglioEH(r.eh_dettaglio));
    else {
    const sez1 = r.eh.filter(x => x.sezione === "SezioneI_DichSost"), altre = r.eh.filter(x => x.sezione !== "SezioneI_DichSost");
    box.append(h("section", { class: "grp" }, h("h2", {}, "Sezione I - Dichiarazioni sostitutive: cosa risulta dai dati"),
      sez1.length ? h("ul", { class: "spunte-eh" }, sez1.map(x => h("li", {}, "☑ " + (VOCI_EH[x.campo] || x.campo)))) : h("p", { class: "mut" }, r.solo_ee || r.errori.length ? "Non calcolabile finché non si risolvono i punti qui sotto." : "Nessuna casella."),
      altre.length ? h("p", { class: "mut" }, "Altre sezioni: " + [...new Set(altre.map(x => x.sezione.replace(/_/g, " ")))].join(", ")) : null,
      h("p", { class: "mut dentro-testo" }, "Testamento, interdetti, rinunce, eredi e aziende derivano dai dati degli altri quadri. Qui sotto le caselle che dipendono da una dichiarazione esplicita.")));
    }
    box.append(caselleDichiaranteEH());
  }
  const el = elencoPerIlFile();
  if (el) box.append(h("section", { class: "grp" }, h("h2", {}, "Da sistemare prima di generare il file"), el));
}
/* Quadro EE come nel modello (revisione del 15/11/2026): sempre gli otto righi EE1-EE8 con il numero di rigo, vuoti con «—»;
   EE6 ed EE8 (totali) in grassetto; accanto alla descrizione i quadri da cui viene il valore, per andarci. */
function prospettoEE(righi) {
  const navigabile = id => quadriNavigabili().some(x => x.id === id && (x.righe || 0) > 0);   // solo i quadri con righe
  return h("div", { class: "tab piatta prospetto-ee" }, h("table", { "aria-label": "Riepilogo dell'asse ereditario (quadro EE)" },
    h("thead", {}, h("tr", {}, h("th", { class: "c-rigo" }, "Rigo"), h("th", {}, "Descrizione"), h("th", { class: "n" }, "Valore"))),
    h("tbody", {}, righi.map(x => {
      const da = x.valore != null ? x.quadri.filter(navigabile) : [];
      return h("tr", { class: "fisso" + (x.totale ? " forte" : "") + (x.valore == null ? " vuoto-ee" : "") },
        h("td", { class: "c-rigo" }, x.rigo),
        h("td", {}, x.testo, da.length ? h("span", { class: "da-quadri" }, da.map(id => h("button", { type: "button", class: "lk", title: "Vai al quadro " + id, onclick: () => scegliQuadro(id) }, id))) : null),
        h("td", { class: "n" }, x.valore == null ? h("span", { class: "mut" }, "—") : euroIt(x.valore, 0)));
    }))));
}
/* Quadro EH come nel modello: sezione I per lettera (a-m, Fascicolo I pp. 51-52) con la frase barrata e i dati che la
   sostengono, gli eredi in tabella (righi EH1-EH3); le sezioni II-IV non compilate restano chiuse con il motivo. Ogni voce
   rimanda al quadro in cui si modifica: la pagina mostra, non calcola. */
const NOMI_DOVE = { AN: "Dati generali", EH: "caselle qui sotto" };
function voceEH(v) {
  const coppie = l => h("div", { class: "eh-dati" }, l.map(([k, val]) => h("span", { class: "eh-dato" }, h("span", { class: "mut" }, k + ": "), val == null || val === "" ? "—" : String(val))));
  const vai = v.dove && v.dove !== "EH" && quadriNavigabili().some(x => x.id === v.dove)
    ? h("button", { type: "button", class: "lk eh-vai", onclick: () => scegliQuadro(v.dove) }, "Modifica in " + v.dove + (NOMI_DOVE[v.dove] ? " (" + NOMI_DOVE[v.dove] + ")" : "")) : null;
  return h("li", { class: "eh-voce" },
    h("div", { class: "eh-testa" }, h("span", { class: "eh-titolo" }, v.lettera ? h("span", { class: "eh-lettera" }, v.lettera + ")") : null, v.titolo), vai),
    v.scelta ? h("div", { class: "eh-scelta" }, h("span", { class: "eh-casella", "aria-hidden": "true" }, "☑"), " ", v.scelta) : null,
    v.dati && v.dati.length ? coppie(v.dati) : null,
    v.tabella && v.tabella.righe.length ? h("div", { class: "tab piatta eh-tabella" }, h("table", { "aria-label": v.titolo },
      h("thead", {}, h("tr", {}, v.tabella.colonne.map(c => h("th", {}, c)))),
      h("tbody", {}, v.tabella.righe.map(rr => h("tr", { class: "fisso" }, rr.map(c => h("td", {}, c == null || c === "" ? "—" : String(c)))))))) : null,
    ...(v.registrazioni || []).map(reg => coppie(reg)),
    ...(v.soggetti || []).map(sg => coppie(sg)),
    v.elenco && v.elenco.length ? h("ul", { class: "eh-elenco" }, v.elenco.map(t => h("li", {}, "☑ " + t))) : null);
}
function dettaglioEH(d) {
  const out = [];
  const di = d.dichiarante;
  if (di) out.push(h("p", { class: "eh-dichiarante" }, "Dichiarante: ", h("b", {}, di.nome || "—"),
    di.codice_fiscale ? " · " + di.codice_fiscale : "", di.codice_carica ? " · codice carica " + di.codice_carica : ""));
  for (const sz of d.sezioni) {
    if (sz.presente) out.push(h("section", { class: "grp eh-sezione" }, h("h2", {}, sz.titolo),
      sz.voci.length ? h("ol", { class: "eh-voci" }, sz.voci.map(voceEH)) : h("p", { class: "mut" }, "Nessuna voce.")));
    else out.push(h("details", { class: "eh-sezione assente" }, h("summary", {}, sz.titolo, h("span", { class: "mut" }, " · non si compila")),
      sz.nota ? h("p", { class: "mut" }, sz.nota) : null));
  }
  return out;
}
/* Caselle del dichiarante (lettere h ed l). Separazione con addebito solo con stato civile 5, nessuno scioglimento dell'unione
   civile solo (e obbligatoria) con stato civile 7: XSD QuadroEH. Una casella gia' compilata con un altro stato civile resta
   visibile, con l'avviso, per poterla togliere. */
function caselleDichiaranteEH() {
  const dich = (((S.P.dati.opzioni || {}).telematico || {}).dichiarazione) || {};
  const val = k => S.dichDirty.has(k) ? S.dichDirty.get(k) : dich[k];
  const sc = String(val("stato_civile") || "").trim();
  const chiavi = ["dichiara_copie_conformi", "flag_inventari"], note = [];
  const regola = [["separazione_con_colpa", "5", "separazione con addebito"], ["no_scioglimento_unione_civile", "7", "scioglimento dell'unione civile"]];
  for (const [k, cod, nome] of regola) {
    const compilata = val(k) != null && val(k) !== "";
    if (sc === cod) chiavi.push(k);
    else if (compilata) { chiavi.push(k); note.push("La casella sul" + (k.startsWith("sep") ? "la " : "lo ") + nome + " vale solo con stato civile " + cod + " (nel frontespizio è " + (sc || "non indicato") + "): togli il valore."); }
  }
  const sez = sezioneDatiDichiarazione(chiavi, "Caselle del dichiarante (quadro EH, lettere h ed l)");
  for (const t of note) sez.append(h("p", { class: "nota stretta" }, t));
  if (sc === "7" && (val("no_scioglimento_unione_civile") == null || val("no_scioglimento_unione_civile") === ""))
    sez.append(h("p", { class: "nota stretta" }, "Con stato civile 7 la casella sullo scioglimento dell'unione civile va indicata."));
  return sez;
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
// righe salvate piu' quelle nuove non ancora salvate (revisione 14/11/2026, E9: non «0 righe» mentre se ne compila una)
function contaRighe(q) {
  const nuove = [...S.nuove.values()].filter(n => n.q === q.id).length, n = q.righe + nuove;
  return n + (n === 1 ? " riga" : " righe") + (nuove ? " (" + nuove + " da salvare)" : "");
}
function classeColonna(q) {
  const col = colonneVista(q), ultima = col.length - 1, fissaDx = ["valore", "importo"].includes(col[ultima]);
  return (c, j) => [["quota", "quota_defunto", "importo", "rendita", "valore", "reddito_dominicale"].includes(c) ? "n" : "",
    j === 0 ? "fissa-sx" : "", j === ultima && fissaDx ? "fissa-dx" : ""].filter(Boolean).join(" ");
}
function renderTabella(main, q) {
  const campi = S.schema.collezioni[q.coll];
  const colonne = colonneVista(q);                    // solo l'ordine di visualizzazione: dati e colonne del quadro non cambiano
  const righe = ordinaRigheVista(q, righeQuadro(q));
  const t = h("table", { "aria-label": q.titolo });
  const clsCol = classeColonna(q);
  t.append(h("thead", {}, h("tr", {}, colonne.map((c, j) => { const t = LBL_VISTA[c] || lbl(q.coll, c, q.id); return h("th", { class: clsCol(c, j), title: t }, SIGLE_COLONNA[c] || t); }))));
  const lg = linguetteImmobili(q); if (lg) main.append(lg);
  const tb = h("tbody"); t.append(tb);
  const indice = indiceRilievi();
  const vere = righe.filter(r => !r.subtotale);   // le righe di somma delle devoluzioni non sono righe di dati
  righe.forEach(r => tb.append(r.subtotale ? rigaSubtotaleDV(r, colonne)
    : rigaTabella(q, r, (S.riga && vere.some(x => x.key === S.riga) ? S.riga === r.key : r === vere[0]), indice)));
  if (!righe.length) tb.append(h("tr", { class: "vuota" }, h("td", { colspan: colonne.length, class: "mut" },
    q.coll === "beni" ? h("div", { class: "vuoto-illustrato" }, h("img", { src: "/static/vuoto_beni.svg", alt: "", "aria-hidden": "true", class: "illustrazione" }),
      h("div", {}, testoVuoto(q), ["EB", "EC"].includes(q.id) ? h("div", { class: "az" }, h("button", { class: "gh", type: "button", onclick: () => caricaVisura(q) }, "Carica visura catastale (PDF)")) : null))
      : testoVuoto(q))));
  const piede = piedeTabella(q, vere); if (piede) t.append(piede);
  if (q.coll === "beni" && vere.length > 3) main.append(cercaImmobile(tb));
  main.append(h("div", { class: "tab" }, t));
  if (q.coll === "beni" && S.cercaBeni) filtraRigheBeni(tb, S.cercaBeni);
  main.append(h("div", { class: "barra" }, h("button", { class: "pil", onclick: () => aggiungiRiga(q) }, vistaImmobili(q) ? "Aggiungi riga in " + q.id : "Aggiungi riga"),

    h("span", { class: "mut" }, "Quote come 1/2, importi come 1.234,50. Per un dato non noto scrivi «?» (da confermare), «assente», «zero» o «non applicabile».")));
}
/* Rilievi per riga («coll[id]») e per campo (percorso completo): costruito una volta per disegno, non per ogni cella. */
function indiceRilievi() {
  const riga = new Map(), campo = new Set();
  for (const x of rilievi()) {
    const p = x.percorso || "", m = p.match(/^[a-z_]+\[[^\]]+\]/);
    if (!m) continue;
    if (!riga.has(m[0])) riga.set(m[0], []);
    riga.get(m[0]).push(x); campo.add(p);
  }
  return { riga, campo };
}
function rigaTabella(q, r, focalizzabile, indice) {
  const campi = S.schema.collezioni[q.coll], clsCol = classeColonna(q);
  const id = r.e && r.e.id; const base = id ? q.coll + "[" + id + "]" : null;
  indice = indice || indiceRilievi();
  const rilRiga = base ? (indice.riga.get(base) || []) : [];
  const tr = h("tr", { tabindex: focalizzabile ? "0" : "-1", "aria-selected": S.riga === r.key ? "true" : "false", class: (r.nuova || S.dirty.has(r.key)) ? "mod" : "", "data-key": r.key,
    onclick: () => selezionaRiga(r.key, "riga"),
    onkeydown: ev => tastiTabella(ev, tr, r.key) });
  colonneVista(q).forEach((c, j) => {
    if (c === "_quadro") {   // vista unica degli immobili: sigla del quadro della riga
      const qid = r.quadroId || q.id;
      tr.append(h("td", { class: clsCol(c, j), title: NOMI_IMMOBILI[qid] || qid }, rilRiga.length ? h("span", { class: "punto", title: rilRiga.map(x => x.messaggio).join("; ") }) : null, h("span", { class: "sigla-mini" }, qid)));
      return;
    }
    if (c === "_rendita") {   // fabbricati: rendita; terreni: reddito dominicale
      const v = valRiga(r, "rendita") ?? valRiga(r, "reddito_dominicale"), txt = mostra("importo", v, true);
      tr.append(h("td", { class: "n", title: txt }, txt)); return;
    }
    const kind = campi[c]; const v = valRiga(r, c);
    let txt = kind.startsWith("enum:") && typeof v === "string" ? nomeVal(q.coll, c, v) : mostra(kind, v, true);
    if (q.coll === "devoluzioni" && c === "diritto" && typeof v === "string" && v) {   // il diritto per nome («Proprieta'»), non il codice
      const b = (S.P.dati.beni || []).find(x => x.id === valRiga(r, "bene_id")); txt = nomeDiritto(v, b && b.tipo);
    }
    if (q.coll === "beni" && c === "diritto" && typeof v === "string" && v) {   // anche nei quadri dei beni il diritto per nome (elenco ufficiale), non «proprieta»
      const sdd = struttDi("beni", "diritto", valRiga(r, "tipo")), od = sdd && sdd.opzioni && sdd.opzioni.find(x => x.valore === riconosciVoce(sdd, v));
      if (od) txt = od.etichetta;
    }
    if (c === "grado_parentela" && typeof v === "string" && v) {   // il grado si legge per nome (menu dei codici), non come codice
      const sdg = struttDi(q.coll, c, null), og = sdg && sdg.opzioni.find(x => x.valore === riconosciVoce(sdg, v));
      if (og) txt = og.etichetta;
    }
    if (kind.startsWith("ref:") && v) { const e = (S.P.dati[kind.slice(4)] || []).find(x => x.id === v); if (e) txt = etichetta(kind.slice(4), e); }
    if (q.coll === "documenti_ref" && c === "tipo_eg" && v) { const sd = struttDi(q.coll, c, null), o = sd && sd.opzioni.find(x => x.valore === v); if (o) txt = o.etichetta; }
    if (q.coll === "documenti_ref" && c === "allegato_id" && v) txt = descriviFileEG(v);
    const errCampo = base && indice.campo.has(base + "." + c);
    const td = h("td", { class: [clsCol(c, j), kind === "cf" ? "cf" : ""].filter(Boolean).join(" "), title: txt, "data-allegato": q.coll === "documenti_ref" && c === "allegato_id" ? (v || "") : null }, j === 0 && rilRiga.length ? h("span", { class: "punto", title: rilRiga.map(x => x.messaggio).join("; ") }) : null, errCampo ? h("span", { class: "pz er" }, "da correggere") : txt,
      j === 0 && q.coll === "persone" && id && id === presentatoreId() ? h("span", { class: "pz ok badge-dich", title: "Presentatore della dichiarazione" }, "dichiarante") : null);   // voce 33
    tr.append(td);
  });
  return tr;
}
// riga dei totali per gli importi (report grafica 07/11/2026, punto 4): somma dei valori indicati, senza i dati non noti
function piedeTabella(q, righe) {
  const campi = S.schema.collezioni[q.coll], clsCol = classeColonna(q), colonne = colonneVista(q);
  const daSommare = colonne.filter(c => campi[c] === "importo" && ["valore", "importo"].includes(c));
  if (righe.length > 1 && daSommare.length) {
    const tot = {}, mancano = {};
    for (const c of daSommare) {
      let cent = 0, nonNoti = 0;
      for (const r of righe) { const v = valRiga(r, c); const m = typeof v === "string" && v.match(/^(-?)(\d+)(?:\.(\d{1,2}))?$/);
        if (m) cent += (m[1] ? -1 : 1) * (Number(m[2]) * 100 + Number((m[3] || "").padEnd(2, "0"))); else nonNoti++; }
      tot[c] = cent; mancano[c] = nonNoti;
    }
    return h("tfoot", {}, h("tr", {}, colonne.map((c, j) => h("td", { class: clsCol(c, j) },
      j === 0 ? "Totale (" + righe.length + " righe)" : c in tot ? (tot[c] / 100).toLocaleString("it-IT", { minimumFractionDigits: tot[c] % 100 ? 2 : 0, maximumFractionDigits: 2 }) + (mancano[c] ? " + " + mancano[c] + " da indicare" : "") : ""))));
  }
  return null;
}
/* Modifica di un campo nel pannello: si ridisegnano solo la riga della tabella e i totali, non tutta la vista (prima ~20-46 ms
   a tasto con 150 righe). Se la riga non c'e' (cambia quadro, vista diversa) si ridisegna la vista intera. */
function aggiornaRigaVista(key) {
  const q = quadro(), vecchia = rigaDaFocalizzare(key);
  const r = q && q.coll && vecchia ? righeQuadro(q).find(x => x.key === key) : null;
  if (!r || q.coll === "devoluzioni" || vistaImmobili(q)) return renderVista();   // somme per bene / totale di tutti gli immobili   // DV: le righe di somma per bene cambiano con la riga
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
  // erede: coppie che si leggono insieme sulla stessa riga (Cognome | Nome, Codice fiscale | Sesso), report 09/11/2026 punto 2
  EA: [["Anagrafica", ["cognome", "nome", "codice_fiscale", "sesso", "data_nascita", "provincia_nascita", "luogo_nascita"], "coppie"],
       ["Nella successione", ["ruolo", "tipo_soggetto", "grado_parentela", "relazione_con_defunto"], "coppie"],
       ["Rappresentazione", ["rappresentato_cf", "rappresentato_grado"], "coppie"], ["Disabilità", ["certificatore_disabilita"], "coppie"]],
};
/* Dati da riportare «con gli estremi presenti in catasto» (Fascicolo I p. PDF 20 per EB, p. PDF 28 per EC): etichetta in grassetto. */
const OBBLIGATORI = {
  EB: ["provincia", "comune", "codice_comune", "foglio", "particella", "reddito_dominicale", "quota_defunto", "diritto", "valore"],
  EC: ["provincia", "comune", "codice_comune", "foglio", "particella", "categoria", "rendita", "quota_defunto", "diritto", "valore"],
  EA: ["codice_fiscale", "cognome", "nome", "grado_parentela"],
};
function schedaAGruppi(gruppi, righe) {
  const usati = new Set(), out = [];
  for (const [titolo, campi, tipo] of gruppi) {
    const qui = righe.filter(([c]) => campi.includes(c)); if (!qui.length) continue;
    if (tipo === "coppie") qui.sort((a, b) => campi.indexOf(a[0]) - campi.indexOf(b[0]));   // l'ordine del gruppo, non quello del modello
    qui.forEach(([c]) => usati.add(c));
    out.push(h("section", { class: "gruppo-scheda" }, h("h4", {}, titolo), h("div", { class: "campi-scheda" + (tipo === "coppie" ? " coppie" : "") }, qui.map(([, el]) => el))));
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
  const box = h("div", { class: "vc", "aria-live": "polite" }, h("h4", {}, "Valore catastale ", h("span", { class: "etich-calc" }, "calcolato")), h("p", { class: "mut" }, "Calcolo in corso…"));
  valoriCatastali().then(res => {
    const v = (res.beni || []).find(x => x.bene_id === r.e.id);
    box.replaceChildren(h("h4", {}, "Valore catastale ", h("span", { class: "etich-calc" }, "calcolato")));
    if (!v) return box.append(h("p", { class: "mut" }, "Non disponibile per questa riga."));
    if (!v.calcolabile) return box.append(h("p", { class: "mut" }, "Non calcolato: " + v.motivo + "."));
    // 14/11/2026 («a cosa serve scrivere tutta questa roba?»): a vista solo il valore e il calcolo; le norme restano nei dati e
    // si leggono da «Fonti» (suggerimento al passaggio del mouse, testo intero al clic)
    const fonti = "Fonti: " + v.fonti.join("; ");
    const dett = h("details", { class: "fonte-vc-det" }, h("summary", { title: fonti }, "Fonti"), h("p", { class: "mut fonte-vc" }, fonti));
    box.append(h("p", {}, h("strong", {}, euroIntero(v.valore)), " — minimo che l'ufficio non può rettificare."),
      h("p", { class: "mut" }, v.formula), dett);
    if (v.avviso) box.append(h("p", { class: "avv" }, v.avviso));
    if (S.dirty.has(r.key)) box.append(h("p", { class: "mut" }, "Il calcolo usa i dati salvati: salva le modifiche per aggiornarlo."));
    if (v.inferiore) box.append(h("p", { class: "avv" }, "Il valore dichiarato (" + euroIntero(v.dichiarato) + ") è inferiore."));
    if (v.dichiarato === null || v.inferiore || Number(v.dichiarato) !== Number(v.valore))
      box.append(h("button", { class: "gh", onclick: () => { scriviValore(r.e.id, v.valore); renderVista(); renderIns(); aggiornaBottoni(); renderSb();
        msg("Valore " + euroIntero(v.valore) + " inserito nella riga: premi «Salva» per confermarlo.", "o"); } }, "Usa il valore catastale"));
  }).catch(e => box.replaceChildren(h("h4", {}, "Valore catastale ", h("span", { class: "etich-calc" }, "calcolato")), h("p", { class: "avv" }, "Valore catastale non calcolabile: " + e.message)));
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
/* ==== Piccole comodita' (15/11/2026, con il lavoro della sessione «GitHub installation» sul server) ==== */
/* Cerca immobile: filtra le righe gia' disegnate mentre si scrive (comune, foglio, particella, indirizzo...): il campo non
   perde il fuoco e i dati non cambiano. */
function cercaImmobile(tb) {
  const inp = h("input", { type: "search", class: "cerca-beni", placeholder: "Cerca immobile: comune, foglio, particella, indirizzo", "aria-label": "Cerca immobile",
    value: S.cercaBeni || "", oninput: e => { S.cercaBeni = e.target.value; filtraRigheBeni(tb, S.cercaBeni); } });
  return h("div", { class: "barra-cerca" }, inp);
}
function filtraRigheBeni(tb, testo) {
  const parole = String(testo || "").toLowerCase().split(/\s+/).filter(Boolean);
  for (const tr of tb.querySelectorAll("tr[data-key]")) {
    const t = tr.textContent.toLowerCase();
    tr.hidden = parole.length > 0 && !parole.every(w => t.includes(w));
  }
}
/* Prima di un'operazione che riscrive la pratica sul server: le modifiche in sospeso vanno salvate. */
async function primaSalva() {
  if (!nMod()) return true;
  if (!confirm("Ci sono modifiche non salvate: il programma le salva prima di continuare. Continuare?")) return false;
  return await salvaTutto();
}
/* Ordina gli immobili del quadro per comune, sezione, foglio, particella e subalterno (server: ordina-beni). */
async function ordinaBeni(q) {
  if (S.writeBusy || !(await primaSalva())) return;
  try { await post("/api/pratiche/" + S.P.pratica_id + "/ordina-beni", { revisione_attesa: S.P.revisione, quadro: q.id, chiave: crypto.randomUUID() });
    await ricarica(); render(); msg("Immobili del quadro " + q.id + " ordinati per comune, foglio e particella.", "o"); }
  catch (e) { msg(e.message, "e"); }
}
/* Sposta su/giu' la riga selezionata fra le righe di questo quadro (le righe degli altri quadri della stessa raccolta restano dove
   sono): nuova permutazione degli identificativi con l'operazione «ordina». */
async function spostaRiga(q, verso) {
  const r = rigaSelezionata();
  if (!r || !r.e) return msg("Seleziona prima una riga salvata da spostare.", "e");
  if (S.writeBusy || !(await primaSalva())) return;
  const visibili = righeQuadro(q).filter(x => x.e).map(x => x.e.id), i = visibili.indexOf(r.e.id), j = i + verso;
  if (i < 0 || j < 0 || j >= visibili.length) return msg(verso < 0 ? "La riga è già la prima." : "La riga è già l'ultima.", "o");
  const tutti = (S.P.dati[q.coll] || []).map(x => x.id), a = tutti.indexOf(visibili[i]), b = tutti.indexOf(visibili[j]);
  [tutti[a], tutti[b]] = [tutti[b], tutti[a]];
  const chiave = r.key;
  await salvaOps([{ op: "ordina", coll: q.coll, ids: tutti }], () => { S.riga = chiave; });
  const tr = document.querySelector('#vista tbody tr[data-key="' + CSS.escape(chiave) + '"]'); if (tr) tr.focus({ preventScroll: false });
}
/* Duplica la pratica: dati copiati, allegati e invii no (il server elenca cosa non copia). */
function duplicaPratica() {
  if (!S.P) return;
  const titolo = h("input", { id: "dupTitolo", value: "Copia di " + (S.P.titolo || ""), maxlength: "200" });
  dialogo("dDuplica", "Duplica la pratica", h("div", {}, h("p", { class: "mut" }, "Si crea una nuova pratica con gli stessi dati. Allegati, file generati e invii non vengono copiati."),
    h("div", { class: "campo" }, h("label", { for: "dupTitolo" }, "Titolo della nuova pratica"), titolo)), "Duplica", () => {
    if (!titolo.value.trim()) return "Scrivi il titolo della nuova pratica.";
    const pid = S.P.pratica_id, t = titolo.value.trim();
    setTimeout(async () => {
      if (!(await primaSalva())) return;
      try { const r = await post("/api/pratiche/" + pid + "/duplica", { titolo: t, chiave: crypto.randomUUID() });
        await caricaPratiche(); await apri(r.pratica_id, "AN");
        msg("Pratica duplicata: «" + r.titolo + "»." + ((r.non_copiati || []).length ? " Non copiati: " + r.non_copiati.join("; ") + "." : ""), "o"); }
      catch (e) { msg(e.message, "e"); }
    }, 0);
    return null;
  });
  titolo.select();
}
/* Carica visura: il PDF «Risultanze catastali» scaricato da Entratel; si scelgono gli immobili da aggiungere. */
function caricaVisura(q) {
  if (!S.P) return;
  const pid = S.P.pratica_id, base = "/api/pratiche/" + pid + "/visure";
  const corpo = h("div", { class: "visura-corpo" }), err = h("p", { class: "err e", role: "alert", hidden: true });
  const file = h("input", { type: "file", accept: ".pdf,application/pdf", multiple: true, id: "visuraFile", hidden: true });
  const scegli = h("button", { class: "gh", type: "button", onclick: () => file.click() }, "Scegli il PDF della visura…");
  const applica = h("button", { class: "pil", type: "button", disabled: true }, "Aggiungi gli immobili scelti");
  const d = h("dialog", { id: "dVisura", class: "guida dlg-visura", "aria-labelledby": "dVisuraT" },
    h("form", { method: "dialog" }, h("h2", { id: "dVisuraT" }, "Carica visura catastale"),
      h("p", { class: "mut" }, "Scegli il PDF «Risultanze catastali» scaricato dai servizi dell'Agenzia. Gli immobili letti si aggiungono solo se li scegli; i dati già inseriti non vengono sovrascritti."),
      h("div", { class: "az" }, scegli, file), err, corpo,
      h("div", { class: "wiz-az" }, h("button", { class: "gh", value: "chiudi" }, "Chiudi"), h("span", { class: "sp" }), applica)));
  d.addEventListener("close", () => d.remove());
  document.body.append(d); d.showModal();
  const errore = t => { err.textContent = t || ""; err.hidden = !t; };
  const mostra = st => {
    corpo.replaceChildren();
    const imm = st.immobili || [];
    // segnalazioni di una riga (con «chiave»): accanto alla riga; le altre in cima
    const segn = (st.proposta || {}).segnalazioni || [], perRiga = {};
    // lo stesso avviso su tutte le righe (per esempio «titolarita' da verificare alla data del decesso") si scrive una volta in cima
    const nImm = (st.immobili || []).length, conta = {};
    for (const x of segn) if (x && typeof x === "object" && x.chiave) conta[x.messaggio] = (conta[x.messaggio] || 0) + 1;
    const comune = m => nImm > 1 && conta[m] >= nImm;
    for (const x of segn) if (x && typeof x === "object" && x.chiave && !comune(x.messaggio)) (perRiga[x.chiave] = perRiga[x.chiave] || []).push(x);
    const avvisi = [...new Set([...(st.avvisi || []), ...(st.limiti || []), ...segn.filter(x => !(x && x.chiave) || comune(x.messaggio)).map(x => typeof x === "string" ? x : x.messaggio || "")].filter(Boolean))];
    if (avvisi.length) corpo.append(h("ul", { class: "nota stretta visura-avvisi" }, avvisi.map(t => h("li", {}, t))));
    if (!imm.length) { corpo.append(h("div", { class: "vuoto-illustrato" }, h("img", { src: "/static/vuoto_visura.svg", alt: "", "aria-hidden": "true", class: "illustrazione" }),
      h("p", { class: "mut" }, "Nessun immobile letto finora."))); applica.disabled = true; return; }
    const ESITI = { nuovi: "nuovo", aggiornati: "da aggiornare", invariati: "già presente", conflitti: "in conflitto" };
    const righe = imm.map(x => {
      const c = h("input", { type: "checkbox", value: x.chiave, checked: x.esito === "nuovi", disabled: x.esito === "invariati" });
      const estremi = [x.comune, x.sezione ? "sez. " + x.sezione : "", "fg. " + x.foglio, "part. " + x.particella, x.subalterno ? "sub. " + x.subalterno : ""].filter(Boolean).join(" ");
      const note = (perRiga[x.chiave] || []).map(y => y.codice === "DIRITTO_NON_AMMESSO_PER_IMMOBILI"
        ? "Il diritto del defunto (" + y.diritto + ") non si può indicare per un immobile: si aggiunge senza diritto e quota, da verificare." : y.messaggio);
      return h("tr", {}, h("td", {}, c), h("td", {}, x.catasto === "T" ? "Terreno" : "Fabbricato"), h("td", {}, estremi, note.map(t => h("div", { class: "nota-riga am" }, t))),
        h("td", {}, x.categoria || x.qualita || ""), h("td", { class: "n" }, x.rendita ? importoIt(String(x.rendita), true) : x.reddito_dominicale ? importoIt(String(x.reddito_dominicale), true) : ""),
        h("td", {}, (x.titolarita || []).join("; ")), h("td", {}, h("span", { class: "pz " + (x.esito === "conflitti" ? "am" : x.esito === "nuovi" ? "ok" : "") }, ESITI[x.esito] || x.esito)));
    });
    corpo.append(h("div", { class: "tab" }, h("table", { "aria-label": "Immobili letti dalla visura" },
      h("thead", {}, h("tr", {}, ["", "Catasto", "Estremi", "Categoria", "Rendita / reddito", "Titolarità", "Esito"].map(t => h("th", {}, t)))), h("tbody", {}, righe))));
    applica.disabled = false;
  };
  const aggiorna = async () => { try { mostra(await api(base)); } catch (e) { errore(e.message); } };
  file.addEventListener("change", async () => {
    errore("");
    for (const f of [...file.files]) {
      try { const r = await rete(base + "?nome=" + encodeURIComponent(f.name), { method: "POST", body: await f.arrayBuffer(), headers: { "Content-Type": "application/pdf" } });
        const j = await r.json().catch(() => ({})); if (!r.ok) { errore(f.name + ": " + (j.messaggio || j.codice || r.status)); break; } }
      catch (e) { errore(e.message); break; }
    }
    file.value = ""; await aggiorna();
  });
  applica.addEventListener("click", async () => {
    const scelti = [...corpo.querySelectorAll("tbody input[type=checkbox]:checked")].map(c => c.value);
    if (!scelti.length) return errore("Scegli almeno un immobile.");
    if (!(await primaSalva())) return;
    try { const r = await post(base + "/applica", { revisione_attesa: S.P.revisione, selezione: scelti, chiave: crypto.randomUUID() });
      d.close(); await ricarica(); render(); msg("Immobili aggiunti dalla visura: " + scelti.length + ". Controlla diritto, quota e valore.", "o"); return r; }
    catch (e) { errore(e.message); }
  });
  aggiorna();
}
/* Ricevute dalla cartella dei download: il programma non entra nei servizi dell'Agenzia; i PDF scaricati dal professionista si
   riconoscono e si conservano nella pratica. */
async function cercaRicevute(box, pid) {
  box.replaceChildren(h("p", { class: "mut" }, "Ricerca nella cartella dei download…"));
  let r;
  try { r = await api("/api/ricevute-cartella"); } catch (e) { box.replaceChildren(h("p", { class: "err" }, e.message)); return; }
  const miei = (r.documenti || []).filter(x => (x.pratiche || []).some(p => p.pratica_id === pid) && x.conservato_in !== pid);
  if (!miei.length) { box.replaceChildren(h("div", { class: "vuoto-illustrato" }, h("img", { src: "/static/vuoto_ricevute.svg", alt: "", "aria-hidden": "true", class: "illustrazione" }),
    h("p", { class: "mut" }, "Nessun documento nuovo per questa pratica in " + (r.cartella || "Download") + "."))); return; }
  box.replaceChildren(h("ul", { class: "ricevute-trovate" }, miei.map(x => {
    const dt = x.dati || {}, reg = dt.registrazione || {};
    const descr = (x.tipo === "attestazione" ? "Attestazione di avvenuta presentazione" : "Documento da classificare") +
      (dt.data_presentazione ? " del " + dataIt(dt.data_presentazione) : "") + (reg.volume ? " · registrazione " + reg.volume + "/" + reg.numero + "/" + reg.anno : "");
    const b = h("button", { class: "gh", type: "button", onclick: async () => {
      b.disabled = true;
      try { await post("/api/pratiche/" + pid + "/ricevute/da-cartella", { file: x.file, cartella: r.cartella, tipo: x.tipo === "attestazione" ? undefined : null });
        await ricarica(); msg("Documento conservato nella pratica: " + x.file + ".", "o"); if (S.sel === "FILE") renderVista(); }
      catch (e) { b.disabled = false; msg(e.message, "e"); }
    } }, "Conserva");
    return h("li", {}, h("div", {}, h("b", {}, x.file), h("div", { class: "mut" }, descr)), b);
  })));
}
/* Menu «Operazioni» del quadro (report grafica 07/11/2026, punto 9): i comandi che valgono solo in questo quadro, con la scorciatoia. */
function menuOperazioni(q) {
  const voci = [["Aggiungi riga", "Alt+N", () => aggiungiRiga(q)], ["Duplica la riga selezionata", "Alt+D", () => duplicaRiga(q)]];
  if (q.coll === "beni" && ["EB", "EC"].includes(q.id)) voci.push(["Ricalcola valori catastali", "", () => ricalcolaValori(q)]);
  if (CAMPI_GRUPPO[q.coll]) voci.push(["Modifica di gruppo…", "", () => modificaDiGruppo(q)]);
  if (q.vista === "tabella" && colonneIncolla(q).length) voci.push(["Incolla da Excel…", "", () => incollaRighe(q)]);
  if (q.coll === "beni" || q.coll === "devoluzioni") voci.push(["Brogliaccio da stampare", "", () => anteprima("/api/pratiche/" + S.P.pratica_id + "/brogliaccio", "Brogliaccio beni e quote")],
    ["Brogliaccio in CSV", "", () => { const a = h("a", { href: "/api/pratiche/" + S.P.pratica_id + "/brogliaccio.csv", download: "" }); document.body.append(a); a.click(); a.remove(); }]);
  if (q.coll === "beni" && ["EB", "EC"].includes(q.id)) voci.push(["Carica visura catastale (PDF)…", "", () => caricaVisura(q)]);
  if (q.coll === "beni") voci.push(["Ordina per comune, foglio e particella", "", () => ordinaBeni(q)]);
  if (q.vista === "tabella") voci.push(["Sposta su la riga selezionata", "Alt+↑", () => spostaRiga(q, -1)], ["Sposta giù la riga selezionata", "Alt+↓", () => spostaRiga(q, 1)]);
  if (q.coll === "beni" || q.coll === "devoluzioni") voci.push(["Agevolazioni guidate…", "", agevolazioniGuidate]);
  voci.push(["Cronologia delle modifiche", "", apriCronologia], ["Duplica la pratica…", "", duplicaPratica]);
  voci.push(["Elimina la riga selezionata", "", () => eliminaRigaSelezionata(q)]);
  const d = h("details", { class: "operazioni" }, h("summary", { class: "gh" }, "Operazioni"));
  const voceMenu = n => { const v = [...d.querySelectorAll(".menu-op button")]; if (v.length) v[(n + v.length) % v.length].focus(); };
  d.addEventListener("toggle", () => { if (d.open && document.activeElement === d.querySelector("summary")) voceMenu(0); });
  d.addEventListener("keydown", ev => {
    const v = [...d.querySelectorAll(".menu-op button")], i = v.indexOf(document.activeElement);
    if (ev.target.tagName === "SUMMARY" && ev.key === "ArrowDown") { ev.preventDefault(); d.open = true; voceMenu(0); return; }
    if (i < 0) return;
    const n = { ArrowDown: i + 1, ArrowUp: i - 1, Home: 0, End: v.length - 1 }[ev.key];
    if (n !== undefined) { ev.preventDefault(); voceMenu(n); }
    else if (ev.key === "Tab") d.open = false;
  });
  // il focus torna su «Operazioni» prima del comando: una finestra aperta dal comando lo restituisce li' alla chiusura
  d.append(h("div", { class: "menu-op", role: "group", "aria-label": "Operazioni del quadro " + q.id }, voci.map(([t, k, f]) => h("button", { type: "button", onclick: () => { d.open = false; d.querySelector("summary").focus(); f(); } },
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
  // vista unica degli immobili: la riga puo' appartenere a un altro quadro (EB, EC, EL, EM): il pannello segue quel quadro
  const prima = { sel: S.sel, riga: S.riga, tab: S.tab };
  if (S.immobiliTutti) { const qr = quadroDellaRiga(key); if (qr && qr !== S.sel) S.sel = qr; }
  S.riga = key; S.tab = "dati";
  const nuova = rigaDaFocalizzare(key);
  // stesso quadro, pannello gia' aperto sulla scheda Dati: basta spostare la selezione e ridisegnare il pannello (91 ms -> pochi ms
  // con 150 righi). Negli altri casi (quadro cambiato, pannello da aprire) serve il disegno completo.
  if (prima.sel === S.sel && prima.tab === "dati" && prima.riga && nuova && !$("#ins").hidden) {
    const vecchia = rigaDaFocalizzare(prima.riga);
    if (vecchia && vecchia !== nuova) { vecchia.setAttribute("aria-selected", "false"); vecchia.tabIndex = -1; }
    for (const x of document.querySelectorAll('#vista tbody tr[tabindex="0"]')) if (x !== nuova) x.tabIndex = -1;
    nuova.setAttribute("aria-selected", "true"); nuova.tabIndex = 0;
    renderIns();
  } else render();
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
/* Ordine di visualizzazione delle tabelle (confronto grafico con DEAS II, 08/11/2026). Cambia solo la vista:
   - EA: prima chi e' (cognome, nome, parentela, ruolo), poi codice fiscale e nascita;
   - DV: righe raggruppate per bene, con sotto ogni bene la somma delle quote per diritto. */
const PRIMA_EA = ["cognome", "nome", "grado_parentela", "ruolo"];
/* Versione 0.3 (report grafico DEAS, proposta 5): vista unica degli immobili. I quadri EB, EC, EL, EM restano distinti nei
   dati e nel file telematico; qui si guardano insieme, con la sigla del quadro come prima colonna. */
const IMMOBILI = ["EC", "EB", "EM", "EL"];
const NOMI_IMMOBILI = { EC: "Fabbricati", EB: "Terreni", EM: "Fabbricati tavolari", EL: "Terreni tavolari" };
const COLONNE_IMMOBILI = ["_quadro", "comune", "foglio", "particella", "subalterno", "categoria", "_rendita", "diritto", "quota_defunto", "valore"];
const LBL_VISTA = { _quadro: "Quadro", _rendita: "Rendita / reddito dom." };
/* Intestazioni brevi, come nei modelli e in DE.A.S. (report 09/11/2026, punto 3): il nome intero resta nel suggerimento. */
const SIGLE_COLONNA = { foglio: "Fg.", particella: "Part.", subalterno: "Sub.", categoria: "Cat.", rendita: "Rendita", reddito_dominicale: "Reddito dom.",
  diritto: "Diritto", quota_defunto: "Quota", data_nascita: "Nascita", grado_parentela: "Grado", partita_tavolare: "Partita tav.",
  codice_fiscale_emittente: "CF emittente", _rendita: "Rendita / R.D." };
/* Etichette brevi della scheda compatta (punto 1): si vedono solo con la densita' compatta; il nome intero e' nel suggerimento. */
const ETICHETTE_BREVI = { grado_parentela: "Grado", ruolo: "Ruolo", tipo_soggetto: "Tipo soggetto", relazione_con_defunto: "Relazione",
  luogo_nascita: "Comune nascita", provincia_nascita: "Prov. nascita", data_nascita: "Data nascita", rappresentato_cf: "CF rappr.",
  rappresentato_grado: "Grado rappr.", certificatore_disabilita: "Verbale", categoria: "Categoria", quota_defunto: "Quota",
  diritto: "Diritto", comune_amministrativo: "Comune amm.", codice_comune: "Cod. comune", codice_comune_amministrativo: "Cod. amm.",
  indirizzo: "Indirizzo", zona_censuaria: "Zona cens.", consistenza: "Consistenza", rendita: "Rendita", rendita_proposta: "Rendita DOCFA",
  reddito_dominicale: "Reddito dom.", tipologia_terreno: "Tipologia", particella_denominatore: "Denominatore", sezione: "Sezione",
  data_visura: "Data visura", diritto_abitazione: "Abit. coniuge", codice_stato_estero: "Cod. Stato", stato_federato: "Stato federato",
  localita_estero: "Località estera", imposta_estera: "Imposta estera", bene_estero: "Bene estero", discordanza_intestatario: "Discordanza",
  passaggi_senza_atti_legali: "Passaggi s. atti", codice_comune_catastale: "Cod. com. catastale", comune_catastale: "Comune catastale" };
const vistaImmobili = q => !!(S.immobiliTutti && q && IMMOBILI.includes(q.id));
function quadriImmobili() { return IMMOBILI.map(id => S.Q && S.Q.quadri.find(x => x.id === id)).filter(x => x && x.supportato && (x.attivo || righeQuadro(x).length)); }
function quadroDellaRiga(key) { for (const q of quadriImmobili()) if (righeQuadro(q).some(r => r.key === key)) return q.id; return null; }
function colonneVista(q) {
  if (vistaImmobili(q)) return COLONNE_IMMOBILI.filter(c => c.startsWith("_") || c in S.schema.collezioni.beni);
  if (q.id !== "EA") return q.colonne;
  return [...PRIMA_EA.filter(c => q.colonne.includes(c)), ...q.colonne.filter(c => !PRIMA_EA.includes(c))];
}
function linguetteImmobili(q) {
  const qs = quadriImmobili(); if (!IMMOBILI.includes(q.id) || qs.length < 1) return null;
  const n = qq => righeQuadro(qq).length, tot = qs.reduce((s, qq) => s + n(qq), 0);
  const tab = (testo, attiva, f, titolo) => h("button", { type: "button", role: "tab", "aria-selected": attiva ? "true" : "false", title: titolo || null, onclick: f }, testo);
  return h("div", { class: "linguette-immobili", role: "tablist", "aria-label": "Immobili" },
    tab("Tutti gli immobili (" + tot + ")", !!S.immobiliTutti, () => scegliQuadro(S.sel, true), "Fabbricati e terreni di tutti i quadri in una tabella"),
    qs.map(qq => tab(NOMI_IMMOBILI[qq.id] + " " + qq.id + " (" + n(qq) + ")", !S.immobiliTutti && S.sel === qq.id, () => scegliQuadro(qq.id), qq.titolo)));
}
function ordinaRigheVista(q, righe) {
  if (vistaImmobili(q)) return quadriImmobili().flatMap(qq => righeQuadro(qq).map(r => ({ ...r, quadroId: qq.id })));
  if (q.coll !== "devoluzioni" || righe.length < 2) return righe;
  const ordineBeni = new Map((S.P.dati.beni || []).map((b, i) => [b.id, i]));
  const pos = r => { const b = valRiga(r, "bene_id"); return ordineBeni.has(b) ? ordineBeni.get(b) : 1e9; };
  const ordinate = righe.map((r, i) => [r, i]).sort((a, b) => pos(a[0]) - pos(b[0]) || a[1] - b[1]).map(x => x[0]);
  const out = [];
  ordinate.forEach((r, i) => {
    out.push(r);
    const b = valRiga(r, "bene_id"), dopo = ordinate[i + 1];
    if (b && (!dopo || valRiga(dopo, "bene_id") !== b)) out.push({ subtotale: true, bene_id: b, righe: ordinate.filter(x => valRiga(x, "bene_id") === b) });
  });
  return out;
}
function rigaSubtotaleDV(r, colonne) {
  const bene = (S.P.dati.beni || []).find(x => x.id === r.bene_id);
  const perDiritto = new Map();
  for (const x of r.righe) { const k = valRiga(x, "diritto") || ""; if (!perDiritto.has(k)) perDiritto.set(k, []); perDiritto.get(k).push(valRiga(x, "quota")); }
  const esiti = [...perDiritto].map(([dir, quote]) => {
    const s = sommaQuote(quote);
    const [cls, t] = s.nonNote ? ["am", s.nonNote === 1 ? "1 quota da indicare" : s.nonNote + " quote da indicare"]
      : s.n === s.d ? ["ok", "completa"] : s.n > s.d ? ["er", "supera 1/1"] : ["am", "manca " + (s.d - s.n) + "/" + s.d];
    return h("span", { class: "pz " + cls, title: nomeDiritto(dir, bene && bene.tipo) }, (perDiritto.size > 1 ? nomeDiritto(dir, bene && bene.tipo) + ": " : "") + s.n + "/" + s.d + " · " + t);
  });
  return h("tr", { class: "subtot", "aria-hidden": "true" }, h("td", { colspan: colonne.length }, h("span", { class: "etich-calc" }, "calcolato"), " Somma delle quote" + (bene ? " di " + etichetta("beni", bene) : ""), " ", esiti));
}
/* Report grafico DEAS dell'08/11/2026, proposta 4: codice catastale ricavato dal nome del comune, dalle tabelle del componente
   SUC13 configurato (server: codice_fiscale.cerca_codice_comune). E' un valore calcolato: si propone con «Usa», non si scrive
   mai da solo; con omonimi soppressi si chiede di controllare la visura. Solo EB ed EC (i tavolari hanno il comune catastale). */
function propostaCodiceComune(q, r, ins) {
  if (q.coll !== "beni" || !["EB", "EC"].includes(q.id)) return;
  const rg = ins.querySelector('.rg[data-campo="codice_comune"]'); if (!rg) return;
  const vecchia = rg.querySelector(".proposta-comune"); if (vecchia) vecchia.remove();
  const nome = String(valRiga(r, "comune") || "").trim(), prov = String(valRiga(r, "provincia") || "").trim().toUpperCase();
  if (!nome || prov === "EE") return;
  const box = h("div", { class: "calcolato proposta-comune", "aria-live": "polite" }); rg.append(box);
  const attuale = String(valRiga(r, "codice_comune") || "").trim().toUpperCase();
  const descr = c => c.codice + " (" + c.nome + (c.provincia ? ", " + c.provincia : "") + ")";
  api("/api/codice-comune?nome=" + encodeURIComponent(nome) + (prov ? "&provincia=" + encodeURIComponent(prov) : "")).then(res => {
    if (!box.isConnected) return;
    const etich = h("span", { class: "etich-calc" }, "calcolato");
    if (res.esito === "trovato") {
      if (attuale === res.codice) box.append(etich, " dal nome: " + descr(res) + " — coincide");
      else box.append(...[etich, " dal nome: ", h("strong", {}, res.codice), " (" + res.nome + (res.provincia ? ", " + res.provincia : "") + ") ",
        attuale ? h("span", { class: "pz am" }, "diverso da " + attuale) : null, " "].filter(x => x !== null),   // Element.append scriverebbe «null»
        h("button", { type: "button", class: "gh", onclick: () => {
          if (r.nuova) r.nuova.campi.codice_comune = res.codice;
          else { const d = S.dirty.get(r.key) || { coll: q.coll, id: r.e.id, campi: {} }; d.campi.codice_comune = res.codice; S.dirty.set(r.key, d); }
          renderVista(); renderIns(); aggiornaBottoni(); renderSb();
          msg("Codice comune " + res.codice + " inserito nella riga: premi «Salva» per confermarlo.", "o");
        } }, "Usa"));
      if (res.omonimi_senza_provincia) box.append(h("div", {}, "Con lo stesso nome ci sono anche " + res.omonimi_senza_provincia +
        (res.omonimi_senza_provincia === 1 ? " comune" : " comuni") + " senza provincia nelle tabelle (anche soppressi): controlla il codice sulla visura."));
    } else if (res.esito === "ambiguo") box.append(etich, " Più comuni con questo nome: indica la provincia. " + res.candidati.map(descr).join(", "));
    else if (res.esito === "non_trovato") box.append(etich, " Nessun comune con questo nome nelle tabelle ufficiali: controlla il nome o scrivi il codice dalla visura.");
    else box.remove();   // tabelle del componente non configurate: nessuna proposta, il codice si scrive a mano
  }).catch(() => box.remove());
}
/* Proposta 7: trascinamento dei file. Un file lasciato sul riquadro va nel campo file con l'estensione ammessa (o nel primo);
   poi si conferma con il pulsante di sempre: nulla viene caricato da solo. */
function zonaTrascina(zona) {
  const avvia = ev => { if ([...(ev.dataTransfer || {}).types || []].includes("Files")) { ev.preventDefault(); zona.classList.add("trascina-sopra"); } };
  zona.addEventListener("dragenter", avvia); zona.addEventListener("dragover", avvia);
  zona.addEventListener("dragleave", ev => { if (!zona.contains(ev.relatedTarget)) zona.classList.remove("trascina-sopra"); });
  zona.addEventListener("drop", ev => {
    zona.classList.remove("trascina-sopra");
    const files = [...((ev.dataTransfer || {}).files || [])]; if (!files.length) return;
    ev.preventDefault();
    const campi = [...zona.querySelectorAll('input[type="file"]')];
    const ammette = (inp, f) => { const acc = (inp.getAttribute("accept") || "").split(",").map(x => x.trim().toLowerCase()).filter(Boolean);
      return !acc.length || acc.some(a => f.name.toLowerCase().endsWith(a)); };
    const messi = [];
    for (const f of files) {
      const inp = campi.find(i => !messi.includes(i) && ammette(i, f)); if (!inp) continue;
      const dt = new DataTransfer(); dt.items.add(f); inp.files = dt.files; inp.dispatchEvent(new Event("change", { bubbles: true })); messi.push(inp);
    }
    msg(messi.length ? (messi.length === 1 ? "File pronto: " + files[0].name + ". Completa i dati e conferma con il pulsante." : messi.length + " file pronti: conferma con il pulsante.")
      : "Nessun campo di questo riquadro accetta il file trascinato.", messi.length ? "o" : "e");
  });
  zona.classList.add("zona-trascina");
  return zona;
}
function testoVuoto(q) {
  if (q.id === "EG") return "Nessun documento collegato. Trascina un PDF nel riquadro «Aggiungi un documento» qui sotto, oppure sceglilo da lì.";
  const incolla = q.vista === "tabella" && colonneIncolla(q).length ? " oppure «Incolla da Excel» nel menu Operazioni" : "";
  return "Nessuna riga in questo quadro. Usa «Aggiungi riga» (Alt+N)" + incolla + ".";
}
/* Voce 33: riepilogo del soggetto nel quadro EA (ruolo, parentela, dichiarante, beni ricevuti con la quota). */
function presentatoreId() {
  const dich = ((S.P.dati.opzioni.telematico || {}).dichiarazione || {});
  return (dich.presentatore || {}).persona_id || ((S.P.dati.persone || []).find(p => p.ruolo === "presentatore") || {}).id || null;
}
/* Voce 5: modifica di gruppo (beni e devoluzioni). I valori scelti diventano modifiche da salvare sulle righe spuntate: con
   «Salva» si crea una sola revisione, annullabile dalla Cronologia. Nessun campo viene cambiato se non e' spuntato. */
const CAMPI_GRUPPO = { beni: ["diritto", "quota_defunto", "data_visura"], devoluzioni: ["diritto", "quota"] };
function dialogo(id, titolo, corpo, conferma, onConferma) {
  const vecchio = document.getElementById(id); if (vecchio) vecchio.remove();
  const err = h("p", { class: "err e", role: "alert", hidden: true });
  const ok = h("button", { class: "pil", value: "ok", onclick: ev => { ev.preventDefault(); const e = onConferma(); if (e) { err.textContent = e; err.hidden = false; } else d.close(); } }, conferma);
  // Invio in un campo: il modulo lo tratterebbe come clic sul primo pulsante («Annulla») e chiuderebbe perdendo i dati;
  // qui applica l'azione principale (i campi che usano Invio per conto loro lo fermano prima con preventDefault)
  // (casella e scelta: Invio non applica, si cambiano con Spazio)
  const invio = ev => { if (ev.key === "Enter" && !ev.defaultPrevented && !ev.isComposing && ev.target.tagName === "INPUT" && !["checkbox", "radio"].includes(ev.target.type)) { ev.preventDefault(); ok.click(); } };
  const annulla = () => { if (firmaModulo(d) !== iniziale && !confirm("Chiudere senza applicare? I dati inseriti nella finestra andranno persi.")) return; d.close(); };
  const d = h("dialog", { id, class: "dlg-op", "aria-labelledby": id + "T" }, h("form", { method: "dialog", onkeydown: invio }, h("h2", { id: id + "T" }, titolo), corpo, err,
    h("div", { class: "wiz-az" }, h("button", { type: "button", class: "gh", value: "annulla", onclick: annulla }, "Annulla"), h("span", { class: "sp" }), ok)));
  d.addEventListener("cancel", ev => { ev.preventDefault(); annulla(); });   // Esc: stessa conferma di «Annulla»
  document.body.append(d); const iniziale = firmaModulo(d); d.showModal(); return d;
}
/* Impronta dei campi di una finestra: serve a chiedere conferma prima di chiudere perdendo cio' che si e' scritto. */
function firmaModulo(el) {
  return JSON.stringify([...el.querySelectorAll("input:not(.cal-nativo), select, textarea")].map(x => x.type === "checkbox" || x.type === "radio" ? x.checked : x.value));
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
