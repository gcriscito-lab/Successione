"use strict";
/* Procedura guidata di creazione della pratica e scorciatoie da tastiera. */
/* ---------- procedura guidata ---------- */
const W = { passo: 0, dati: {} };
const PASSI = ["Defunto", "Tipo", "Quadri", "Conferma"];
function titoloWiz() { return "Successione " + ([W.dati.cognome, W.dati.nome].filter(Boolean).join(" ").trim() || "nuova"); }
function wizRender() {
  $("#wizPassi").replaceChildren(...PASSI.map((p, i) => h("li", { "aria-current": i === W.passo ? "step" : "false" }, (i + 1) + ". " + p)));
  const c = $("#wizCorpo"); c.replaceChildren(); $("#wizErr").textContent = "";
  $("#wIndietro").hidden = W.passo === 0; $("#wAvanti").textContent = W.passo === PASSI.length - 1 ? "Crea dichiarazione" : "Avanti";
  const d = W.dati;
  const f = (k, label, ph) => h("div", { class: "campo" }, h("label", { for: "w_" + k }, label), h("input", { id: "w_" + k, value: d[k] || "", placeholder: ph || "", class: k === "codice_fiscale" ? "mono cf" : "", oninput: ev => { d[k] = ev.target.value; $("#wizErr").textContent = ""; if (k === "codice_fiscale") wizDaCF(ev.target.value); } }));
  if (W.passo === 0) c.append(h("p", { class: "mut" }, "Dati anagrafici del defunto. Potrai completarli o correggerli nei dati generali."), h("div", { class: "griglia" }, f("cognome", "Cognome"), f("nome", "Nome"), f("codice_fiscale", "Codice fiscale"), f("data_nascita", "Data di nascita", "GG/MM/AAAA"), f("luogo_nascita", "Comune di nascita"), f("provincia_nascita", "Provincia di nascita", "RM"), f("data_decesso", "Data del decesso", "GG/MM/AAAA"), f("comune_decesso", "Comune del decesso"), f("provincia_decesso", "Provincia del decesso", "RM")), h("div", { id: "w_cf_nota", class: "mut testo-m spazio-su", "aria-live": "polite" }));
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
  const { testo } = await suggerisciDaCF(valore, "defunto", c => d[c], (c, x) => { x = dataIt(x); d[c] = x; const el = $("#w_" + c); if (el) el.value = x; }, () => W.dati === d && String(d.codice_fiscale || "").trim().toUpperCase() === String(valore || "").trim().toUpperCase());
  const nota = $("#w_cf_nota"); if (nota) nota.textContent = testo;
}
/* Una chiave di richiesta per ogni apertura della procedura: un doppio clic o un nuovo tentativo dopo un errore di rete
   non crea due pratiche (revisione 2, punto 1). */
function wizApri() { if (S.writeBusy) return msg("Salvataggio in corso: attendi prima di creare una pratica.", "e"); W.passo = 0; W.dati = {}; W.extra = null; W.chiave = crypto.randomUUID(); W.busy = false; S.gen++; wizRender(); $("#wAvanti").disabled = false; $("#wiz").showModal(); }
/* Dati scritti nella procedura (anche quelli portati dalla calcolatrice): chiudere li perde, quindi si chiede conferma. */
function wizHaDati() {
  const d = W.dati;
  return ["cognome", "nome", "codice_fiscale", "data_nascita", "luogo_nascita", "provincia_nascita", "data_decesso", "comune_decesso", "provincia_decesso"]
    .some(k => String(d[k] || "").trim()) || (W.extra && W.extra.length > 0) || (d.tipo && d.tipo !== "originaria");
}
function wizChiudi() {
  if (W.busy) return;
  if (wizHaDati() && !confirm("Chiudere la procedura? I dati inseriti andranno persi.")) return;
  $("#wiz").close();
}
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
  $("#wiz").close(); await caricaPratiche(); await apri(r.pratica_id, "AN");
  msg(S.P && S.P.pratica_id === r.pratica_id ? "Dichiarazione creata." : "Dichiarazione «" + titoloWiz() + "» creata: la trovi nell'elenco delle pratiche.", "o");
}

/* Impostazioni: percorsi degli strumenti esterni (server: /api/impostazioni), con stato di rilevamento. */
const IMP = { voci: [], iniziali: {}, aspetto: null, profilo: {}, intestazione: {}, preferenze: {}, rubrica: [] };
const RUOLI_RUBRICA = [["intermediario", "Intermediario"], ["delegato", "Delegato"], ["presentatore", "Presentatore"], ["altro", "Altro"]];
let RUBRICA = null;   // voci della rubrica dello studio, lette alla prima necessita'
async function rubrica() { if (!RUBRICA) { try { RUBRICA = (await api("/api/rubrica")).voci || []; } catch (_) { RUBRICA = []; } } return RUBRICA; }
function impRubricaRender() {
  const box = $("#impRubrica"); if (!box) return;
  const riga = (v, i) => {
    const campo = (k, attr, el) => { el = el || h("input", { value: v[k] || "", ...attr }); el.addEventListener("input", () => { IMP.rubrica[i][k] = k === "codice_fiscale" ? el.value.trim().toUpperCase() : el.value; }); return el; };
    const ruolo = h("select", { "aria-label": "Ruolo" }, RUOLI_RUBRICA.map(([k, t]) => h("option", { value: k }, t))); ruolo.value = v.ruolo || "intermediario";
    ruolo.addEventListener("change", () => { IMP.rubrica[i].ruolo = ruolo.value; });
    return h("tr", {}, h("td", {}, campo("nome", { "aria-label": "Nome", maxlength: "120" })), h("td", {}, campo("codice_fiscale", { "aria-label": "Codice fiscale", maxlength: "16", class: "mono" })),
      h("td", {}, ruolo), h("td", {}, campo("note", { "aria-label": "Note", maxlength: "200" })),
      h("td", {}, h("button", { class: "lk", type: "button", onclick: () => { IMP.rubrica.splice(i, 1); impRubricaRender(); } }, "Togli")));
  };
  box.replaceChildren(h("h3", {}, "Rubrica"), h("p", { class: "mut" }, "Intermediari, delegati e presentatori ricorrenti: si scelgono dalla rubrica nel fornitore di File e invio."),
    IMP.rubrica.length ? h("div", { class: "tab piatta" }, h("table", { class: "tab-rubrica" }, h("thead", {}, h("tr", {}, ["Nome", "Codice fiscale", "Ruolo", "Note", ""].map(t => h("th", {}, t)))),
      h("tbody", {}, IMP.rubrica.map(riga)))) : null,
    h("div", { class: "az" }, h("button", { class: "gh", type: "button", onclick: () => { IMP.rubrica.push({ nome: "", codice_fiscale: "", ruolo: "intermediario", note: "" }); impRubricaRender(); } }, "Aggiungi alla rubrica")));
}
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
  scelte('stile', 'Stile grafico', [['moderno', 'Moderno (predefinito)'], ['classico', 'Classico (com’era fino al 14/11/2026)']]);
  scelte('font', 'Carattere', [['sistema', 'Del sistema (predefinito)'], ['atkinson', 'Atkinson Hyperlegible (molto leggibile)'], ['segoe', 'Segoe UI'], ['arial', 'Arial'], ['verdana', 'Verdana'], ['georgia', 'Georgia'], ['consolas', 'Consolas']]);
  scelte('dimensione', 'Dimensione del testo', Array.from({ length: 11 }, (_, i) => [String(i + 12), (i + 12) + ' px']));
  scelte('interlinea', 'Spaziatura delle righe', [['compatta', 'Compatta'], ['normale', 'Normale'], ['ampia', 'Ampia']]);
  scelte('accento', 'Colore di accento', [['predefinito', 'Verde modello (predefinito)'], ['blu', 'Blu'], ['verde', 'Verde'], ['viola', 'Viola'], ['arancio', 'Arancio'], ['rosso', 'Rosso'], ['grafite', 'Grafite']]);
  scelte('densita', 'Densità di tabelle e schede', [['compatta', 'Compatta (schede con etichette a sinistra)'], ['normale', 'Normale'], ['ampia', 'Ampia']]);
  scelte('disposizione', 'Pannello della riga selezionata', [['destra', 'A destra della tabella'], ['sotto', 'Sotto la tabella, a tutta larghezza']]);
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
const VOCI_INTESTAZIONE = [['nome', 'Nome dello studio', 60], ['indirizzo', 'Indirizzo', 100], ['cap_comune', 'CAP, comune e provincia', 80],
  ['telefono', 'Telefono', 40], ['email', 'Posta elettronica', 120], ['pec', 'PEC', 120], ['cf_piva', 'Codice fiscale o partita IVA', 16]];
function impProfiloRender(p, intest) {
  IMP.profilo = { ...p }; IMP.intestazione = { ...(intest || {}) };
  const campo = (chiave, titolo, el) => { el.id = 'prof_' + chiave; el.setAttribute('aria-label', titolo); return h('div', { class: 'campo' }, h('label', { for: el.id }, titolo), el); };
  const cf = h('input', { class: 'mono cf', value: p.cf || '', placeholder: 'codice fiscale', oninput: e => { IMP.profilo.cf = e.target.value.trim().toUpperCase(); } });
  const tipo = h('select', {}, h('option', { value: '' }, 'Non indicato'), h('option', { value: '1' }, 'Dichiarante (1)'), h('option', { value: '10' }, 'Intermediario (10)'));
  tipo.value = p.tipo || ''; tipo.addEventListener('change', () => { IMP.profilo.tipo = tipo.value; });
  const imp = h('select', {}, h('option', { value: '' }, 'Non indicato'), h('option', { value: '1' }, 'Predisposta dal dichiarante (1)'), h('option', { value: '2' }, 'Predisposta dall’intermediario (2)'));
  imp.value = p.impegno_codice || ''; imp.addEventListener('change', () => { IMP.profilo.impegno_codice = imp.value; });
  $('#impProfilo').replaceChildren(h('h3', {}, 'Profilo dello studio'),
    h('p', { class: 'mut' }, 'Chi presenta il file. Viene proposto in ogni nuova pratica e si può cambiare pratica per pratica.'),
    h('div', { class: 'aspetto-griglia' }, campo('cf', 'Codice fiscale del fornitore', cf), campo('tipo', 'Tipo fornitore', tipo), campo('impegno', 'Impegno a trasmettere', imp)),
    // carta intestata delle stampe (prospetto per il cliente, preventivo, brogliaccio, fascicolo), 14/11/2026
    h('h3', {}, 'Intestazione delle stampe'),
    h('p', { class: 'mut' }, 'Compare in alto nelle stampe per il cliente. I campi vuoti non si stampano.'),
    h('div', { class: 'aspetto-griglia' }, VOCI_INTESTAZIONE.map(([k, titolo, max]) => campo('int_' + k, titolo,
      h('input', { value: IMP.intestazione[k] || '', maxlength: String(max), class: k === 'cf_piva' ? 'mono' : '', autocomplete: 'off',
        type: k === 'email' || k === 'pec' ? 'email' : k === 'telefono' ? 'tel' : 'text',
        oninput: e => { IMP.intestazione[k] = k === 'cf_piva' ? e.target.value.trim().toUpperCase() : e.target.value; } })))));
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
    return h('div', { class: 'campo casella' }, h('label', { class: 'chk', for: el.id }, el, h('span', {}, titolo)), h('div', { class: 'mut aiuto' }, nota));
  };
  const numero = (chiave, titolo, minimo, massimo, pulsante) => {
    const el = h('input', { type: 'number', id: 'pref_' + chiave, min: String(minimo), max: String(massimo), value: String(p[chiave]) });
    el.addEventListener('input', () => { const n = parseInt(el.value, 10); if (Number.isInteger(n)) IMP.preferenze[chiave] = n; });
    return h('div', { class: 'campo' }, h('label', { for: el.id }, titolo + ' (' + minimo + '–' + massimo + ')'), pulsante ? h('div', { class: 'in-linea' }, el, pulsante) : el);
  };
  $('#impPreferenze').replaceChildren(h('h3', {}, 'Operatività e sicurezza'),
    casella('pulizia_automatica', 'Elimina automaticamente i file temporanei e di lavoro', 'Copie di XML e uscite dei controlli lasciate nella cartella di lavoro. Non tocca pratiche, allegati, file generati né backup.'),
    numero('pulizia_ore', 'Elimina i temporanei più vecchi di (ore)', 1, 720, h('button', { type: 'button', class: 'gh', onclick: async ev => {
      ev.target.disabled = true;
      try { const r = await post('/api/pulizia', {}); msg('Pulizia eseguita: ' + r.eliminati + ' elementi, ' + r.byte_liberati + ' byte liberati.', 'o'); }
      catch (e) { msg('Pulizia non riuscita: ' + e.message, 'e'); }
      ev.target.disabled = false;
    } }, 'Pulisci ora')),
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
            v.rimedio && v.stato !== 'ok' ? h('div', { class: 'mut aiuto' }, v.rimedio) : null)));
      } catch (e) { risultato.replaceChildren(h('p', { class: 'err' }, 'Diagnosi non riuscita: ' + e.message)); }
      ev.target.disabled = false;
    } }, 'Esegui diagnosi'), risultato);
}
function impRender(s) {
  impDiagnosiRender(s.componente_controllo);
  impProfiloRender(s.profilo || {}, s.intestazione || {}); impRubricaRender(); impBackupRender(); impPreferenzeRender(s.preferenze || {});
  IMP.voci = s.voci; IMP.iniziali = Object.fromEntries(s.voci.map(v => [v.chiave, v.valore || ""]));
  impAspettoRender(s.interfaccia);
  $("#impFile").textContent = "File di configurazione: " + s.file;
  $("#impCorpo").replaceChildren(...s.voci.map(v => h("div", { class: "campo voce-imp" },
    h("label", { for: "imp_" + v.chiave }, v.etichetta),
    h("input", { id: "imp_" + v.chiave, class: "mono", value: v.valore || "", disabled: !v.modificabile, placeholder: v.modificabile ? "non impostato" : "" }),
    h("div", { class: "mut aiuto" }, (v.a_posto ? "✓ " : "✗ ") + v.dettaglio + (v.valore ? " · origine: " + v.origine : "")),
    h("div", { class: "mut aiuto" }, v.nota))));
}
/* Impronta di cio' che si puo' modificare nelle Impostazioni: se alla chiusura e' diversa, ci sono modifiche non salvate. */
function impFirma() {
  const voci = (IMP.voci || []).filter(v => v.modificabile).map(v => { const el = document.getElementById("imp_" + v.chiave); return el ? el.value.trim() : ""; });
  return JSON.stringify([IMP.aspetto, IMP.profilo, IMP.intestazione, IMP.preferenze, IMP.rubrica, voci]);
}
function impChiudi() {
  if (IMP.firma && impFirma() !== IMP.firma && !confirm("Ci sono modifiche non salvate nelle Impostazioni. Chiudere senza salvarle?")) return false;
  $("#imp").close(); return true;
}
async function impApri() {
  $("#impErr").textContent = "";
  try { IMP.rubrica = ((await api("/api/rubrica")).voci || []).map(v => ({ ...v })); impRender(await api("/api/impostazioni")); IMP.firma = impFirma(); $("#imp").showModal(); }
  catch (e) { msg("Impostazioni non disponibili: " + e.message, "e"); }
}
async function impSalva() {
  const modifiche = {};
  for (const v of IMP.voci) if (v.modificabile) { const x = $("#imp_" + v.chiave).value.trim(); if (x !== IMP.iniziali[v.chiave]) modifiche[v.chiave] = x; }
  try {
    const profilo = Object.fromEntries(Object.entries(IMP.profilo).filter(([, v]) => v));
    const intestazione = Object.fromEntries(Object.entries(IMP.intestazione).map(([k, v]) => [k, String(v || '').trim()]).filter(([, v]) => v));
    const voci = IMP.rubrica.filter(v => (v.nome || "").trim() || (v.codice_fiscale || "").trim()).map(v => ({ ...v, nome: (v.nome || "").trim(), note: (v.note || "").trim() }));
    IMP.rubrica = (await post("/api/rubrica", { voci })).voci || []; RUBRICA = IMP.rubrica.map(v => ({ ...v }));
    const s = await post("/api/impostazioni", { modifiche, interfaccia: IMP.aspetto, profilo, intestazione, preferenze: IMP.preferenze });
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
  } catch (e) { memorizzaAspetto(precedente); msg('Misura del pannello non salvata: ' + e.message, 'e'); }
}
/* Separatore ridimensionabile: cfg = { chiave, pannello (selettore), verso (+1 se il pannello e' a sinistra del separatore),
   min, max() }. Trascinamento con pointer capture, tastiera con frecce/Home/End, doppio clic per il valore predefinito. */
function collegaSeparatore(sep, base) {
  // cfg puo' dipendere dalla disposizione (pannello a destra: larghezza sull'asse x; pannello sotto: altezza sull'asse y)
  const conf = () => (typeof base === 'function' ? base() : base);
  let tr = null;
  sep.addEventListener('pointerdown', ev => {
    if (ev.button !== 0 || window.innerWidth <= 960) return;
    const cfg = conf(), r = $(cfg.pannello).getBoundingClientRect();
    tr = { cfg, id: ev.pointerId, p: cfg.asse === 'y' ? ev.clientY : ev.clientX, misura: cfg.asse === 'y' ? r.height : r.width, nuova: preferenze[cfg.chiave] };
    sep.setPointerCapture(ev.pointerId); document.body.classList.add('ridimensionando'); ev.preventDefault();
  });
  sep.addEventListener('pointermove', ev => {
    if (!tr || ev.pointerId !== tr.id) return;
    const cfg = tr.cfg, p = cfg.asse === 'y' ? ev.clientY : ev.clientX;
    tr.nuova = Math.round(Math.max(cfg.min, Math.min(cfg.max(), tr.misura + cfg.verso * (p - tr.p))));
    applicaAspetto({ ...preferenze, [cfg.chiave]: tr.nuova });
  });
  const fine = ev => {
    if (!tr || ev.pointerId !== tr.id) return;
    const valore = tr.nuova, chiave = tr.cfg.chiave; tr = null; document.body.classList.remove('ridimensionando');
    if (sep.hasPointerCapture(ev.pointerId)) sep.releasePointerCapture(ev.pointerId);
    if (ev.type === 'pointercancel') applicaAspetto(preferenze); else salvaLarghezza(valore, chiave);
  };
  sep.addEventListener('pointerup', fine); sep.addEventListener('pointercancel', fine);
  sep.addEventListener('keydown', ev => {
    const cfg = conf(), tasti = cfg.asse === 'y' ? ['ArrowUp', 'ArrowDown'] : ['ArrowLeft', 'ArrowRight'];
    if (![...tasti, 'Home', 'End'].includes(ev.key)) return;
    ev.preventDefault();
    const piu = cfg.verso > 0 ? tasti[1] : tasti[0];
    const l = ev.key === 'Home' ? cfg.min : ev.key === 'End' ? cfg.max() : preferenze[cfg.chiave] + (ev.key === piu ? 16 : -16);
    salvaLarghezza(Math.max(cfg.min, Math.min(cfg.max(), l)), cfg.chiave);
  });
  sep.addEventListener('dblclick', () => { const cfg = conf(); salvaLarghezza(ASPETTO_DEFAULT[cfg.chiave], cfg.chiave); });
}
collegaSeparatore($('#ridimensiona'), () => preferenze.disposizione === 'sotto'
  ? { chiave: 'altezza_pannello', pannello: '#ins', asse: 'y', verso: -1, min: 200, max: () => limiteAltezza() }
  : { chiave: 'larghezza_pannello', pannello: '#ins', asse: 'x', verso: -1, min: 280, max: () => limitePannello() });
collegaSeparatore($('#ridimensionaNav'), { chiave: 'larghezza_nav', pannello: '#lat', verso: 1, min: 180, max: () => limiteNav() || 480 });

/* Importa un file telematico SUC13 (XML) come nuova pratica: importa solo cio' che il programma sa riprodurre e dice il resto. */
const ETICHETTE_IMPORTATO = { eredi: "soggetti del quadro EA", terreni: "terreni", fabbricati: "fabbricati",
  disponibilita_finanziarie: "conti, crediti e altri beni", passivita: "passività", voltura: "sezioni di voltura" };
async function importaXml(file) {
  if (S.writeBusy) return msg("Salvataggio in corso: attendi prima di importare.", "e");
  try {
    const r = await rete("/api/importa", { method: "POST", body: await file.arrayBuffer(), headers: { "Content-Type": "application/xml" } });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) return msg("Importazione non riuscita: " + (j.messaggio || j.codice || r.status), "e");
    await caricaPratiche(); await apri(j.pratica_id, "AN");
    const n = Object.entries(j.importato).filter(([, v]) => v).map(([k, v]) => v + " " + (ETICHETTE_IMPORTATO[k] || k.replaceAll("_", " "))).join(", ");
    // EE ed EF li ricalcola il programma: e' una nota, non un problema (revisione 14/11/2026, E5)
    const ricalcolati = /^Quadro(EE|EF): .*ricalcolat/;
    const leggibile = t => String(t).replace(/Quadro([A-Z]{2})/g, "Quadro $1");
    const resto = j.non_importato.concat(j.avvisi).filter(t => !ricalcolati.test(t)).map(leggibile);
    const nota = j.non_importato.some(t => ricalcolati.test(t)) ? " Totali e imposte (quadri EE ed EF) li ricalcola il programma." : "";
    msg("Importata: " + n + ". Verifica i dati." + nota + (resto.length ? " Da reinserire o controllare: " + resto.join("; ") + "." : ""), resto.length ? "e" : "o");
  } catch (e) { msg("Importazione non riuscita: " + e.message, "e"); }
}
$("#bImporta").onclick = () => $("#fImporta").click();
$("#fImporta").onchange = ev => { const f = ev.target.files[0]; ev.target.value = ""; if (f) importaXml(f); };
$("#bNuova").onclick = wizApri;
$("#wAnnulla").onclick = wizChiudi;
$("#wiz").addEventListener("cancel", ev => { ev.preventDefault(); wizChiudi(); });   // Esc: stessa conferma di «Annulla»
$("#wIndietro").onclick = () => { W.passo--; wizRender(); };
$("#wAvanti").onclick = wizAvanti;
$("#bSalva").onclick = salvaTutto;
$("#bGenera").onclick = vaiFile;
$("#bControlla").onclick = async () => {
  if (!S.P) return;
  const n = nMod();
  if (n && !confirm("Per controllare, il programma salva prima " + (n === 1 ? "la modifica in sospeso" : "le " + n + " modifiche in sospeso") + ". Continuare?")) return;
  if (n && !(await salvaTutto())) return;
  try { S.Q = await api("/api/pratiche/" + S.P.pratica_id + "/quadri"); } catch (e) { msg("Controllo non eseguito. " + e.message, "e"); return; }
  vaiControlli();
};
$('#homeNuova').onclick = wizApri;
$('#homeImporta').onclick = () => $('#fImporta').click();
$('#bHome').onclick = () => {
  if (S.writeBusy || (nMod() && !confirm('Ci sono modifiche non salvate. Tornare alla pagina iniziale senza salvarle?'))) return;
  S.gen++; S.P = null; S.Q = null; S.dirty.clear(); S.nuove.clear(); S.dichDirty.clear(); S.supDirty.clear(); S.fornitoreDirty = {};
  S.sel = 'AN'; S.tab = 'dati'; $('#vista').scrollTop = 0; $('#titolo').textContent = 'Nessuna pratica aperta'; $('#terminePratica').hidden = true; S.griglia = null; render(); caricaPratiche();
};
// con una finestra aperta (Operazioni, procedura guidata, Calcolatrice, Guida...) Ctrl+S non salva la pratica: la finestra ha i suoi pulsanti
document.addEventListener("keydown", ev => { if ((ev.ctrlKey || ev.metaKey) && (ev.key === "s" || ev.key === "S")) { ev.preventDefault(); if (document.querySelector("dialog[open]")) return;
  // il campo in cui si sta scrivendo registra il valore all'uscita (change): prima lo si chiude, poi si salva (revisione 14/11/2026, E1)
  const a = document.activeElement;
  if (a && a.matches("input, select, textarea")) { a.blur(); a.focus({ preventScroll: true }); }
  salvaTutto(); } });
/* Scorciatoie per chi inserisce dati tutto il giorno (report grafica 07/11/2026, punto 10). «?» mostra l'elenco. */
const SCORCIATOIE = [["Ctrl+S", "Salva le modifiche"], ["Alt+N", "Nuova riga nel quadro"], ["Alt+D", "Duplica la riga selezionata"],
  ["Alt+PagGiù / Alt+PagSu", "Quadro successivo / precedente"], ["Ctrl+G", "Vai a un quadro (scrivi la sigla, es. EC)"],
  ["Alt+1 … Alt+9", "Vai alla 1ª … 9ª voce dell'elenco dei quadri (Dati generali, Eredi, …)"],
  ["Alt+C", "Controlla la pratica"], ["Frecce, Home, Fine", "Righe della tabella"], ["Invio", "Apri la riga nel pannello"],
  ["Invio (nella scheda)", "Campo successivo; dopo l'ultimo campo porta a «Salva»"], ["Esc", "Dal pannello torna alla tabella"], ["F1", "Guida e istruzioni ufficiali"], ["?", "Questo elenco"]];
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
/* Versione 0.3: le voci nell'ordine dell'elenco a sinistra (Alt+1 … Alt+9). Stesso ordine di renderAlbero. */
const GRUPPI_ELENCO = ["frontespizio", "quadri", "riepiloghi", "lavoro"];
function vociElenco() { return S.Q ? GRUPPI_ELENCO.flatMap(g => S.Q.quadri.filter(x => x.gruppo === g)) : []; }
function tastoVoce(id) { const i = vociElenco().findIndex(x => x.id === id); return i >= 0 && i < 9 ? " · Alt+" + (i + 1) : ""; }
/* Invio in un campo della scheda: passa al campo successivo (come nei programmi da tavolo); dopo l'ultimo, al pulsante Salva.
   Non vale per aree di testo, caselle, pulsanti e finestre aperte (lì Invio conserva il suo significato). */
function campoSuccessivo(ev) {
  if (ev.key !== "Enter" || ev.ctrlKey || ev.altKey || ev.shiftKey || ev.metaKey || ev.isComposing || ev.defaultPrevented) return;
  const ins = $("#ins"), t = ev.target;
  if (!ins || !ins.contains(t) || document.querySelector("dialog[open]")) return;
  if (!(t.tagName === "SELECT" || (t.tagName === "INPUT" && !["checkbox", "radio", "file", "button", "submit", "reset"].includes(t.type)))) return;
  const campi = [...ins.querySelectorAll('input:not([type=hidden]):not([type=file]):not([disabled]):not([readonly]):not(.cal-nativo), select:not([disabled]), textarea:not([disabled])')]
    .filter(x => x.getClientRects().length && !x.closest("details:not([open]) > :not(summary)"));
  const i = campi.indexOf(t); if (i < 0) return;
  ev.preventDefault();
  const dopo = campi[i + 1];
  if (dopo) { dopo.focus(); if (dopo.tagName === "INPUT" && dopo.select) dopo.select(); }
  else { const salva = ins.querySelector(".az .pil"); if (salva) salva.focus(); }
}
document.addEventListener("keydown", campoSuccessivo);
document.addEventListener("keydown", ev => {
  const inCampo = ev.target.closest && ev.target.closest("input, select, textarea, [contenteditable]");
  if (document.querySelector("dialog[open]")) return;
  if (ev.key === "?" && !inCampo && !ev.ctrlKey && !ev.altKey) { ev.preventDefault(); return mostraScorciatoie(); }
  if (!S.P) return;
  const q = quadro();
  if (ev.altKey && !ev.ctrlKey && (ev.key === "n" || ev.key === "N")) { if (q && q.coll && q.supportato) { ev.preventDefault(); aggiungiRiga(q); } return; }
  if (ev.altKey && !ev.ctrlKey && (ev.key === "d" || ev.key === "D")) { if (q && q.coll) { ev.preventDefault(); duplicaRiga(q); } return; }
  if (ev.altKey && !ev.ctrlKey && (ev.key === "c" || ev.key === "C")) { ev.preventDefault(); $("#bControlla").click(); return; }
  if (ev.altKey && !ev.ctrlKey && !inCampo && (ev.key === "ArrowUp" || ev.key === "ArrowDown")) { if (q && q.vista === "tabella" && q.coll) { ev.preventDefault(); spostaRiga(q, ev.key === "ArrowUp" ? -1 : 1); } return; }
  // Alt+1 … Alt+9: voce dell'elenco dei quadri (ev.code: indipendente dalla tastiera italiana o da Maiusc)
  const cifra = /^Digit([1-9])$/.exec(ev.code || "");
  if (ev.altKey && !ev.ctrlKey && !ev.metaKey && cifra) {
    const v = vociElenco()[Number(cifra[1]) - 1]; if (!v) return;
    ev.preventDefault(); scegliQuadro(v.id);
    // il fuoco va dove si lavora: la prima riga della tabella, altrimenti la voce dell'elenco
    const dove = document.querySelector('#vista tbody tr[tabindex="0"]') || document.querySelector('.voce[data-q="' + v.id + '"]');
    if (dove) dove.focus({ preventScroll: true }); return;
  }
  if (ev.altKey && (ev.key === "PageDown" || ev.key === "PageUp")) {
    const l = quadriNavigabili(), i = l.findIndex(x => x.id === S.sel); if (!l.length) return;
    ev.preventDefault(); scegliQuadro(l[(Math.max(0, i) + (ev.key === "PageDown" ? 1 : l.length - 1)) % l.length].id); return;
  }
  if ((ev.ctrlKey || ev.metaKey) && (ev.key === "g" || ev.key === "G")) {
    ev.preventDefault(); vaiAlQuadro();
  }
});
window.addEventListener("beforeunload", ev => { if (nMod()) { ev.preventDefault(); ev.returnValue = ""; } });
