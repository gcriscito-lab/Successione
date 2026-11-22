"use strict";
/* Griglia delle quote e agevolazioni guidate. */
/* ---------- Griglia delle quote e agevolazioni guidate (15/11/2026, dal confronto con DEAS) ----------
   Griglia: una riga per bene e diritto, una colonna per soggetto; le quote si scrivono nelle celle e si salvano insieme in una
   sola revisione (server: quote_griglia.py, /quote-griglia). La somma di ogni riga deve fare 1/1: e' lo stesso controllo
   DEVOLUZIONI_INCOMPLETE/ECCEDENTI del quadro DV; la quota del defunto e' solo un'informazione.
   S.vistaDV: "elenco" | "griglia"; S.griglia: { pid, dati (risposta del server), mod: Map cella -> quota, sel: Set di righe } */
const chiaveCella = (riga, pid) => riga.bene_id + "|" + riga.diritto + "|" + pid;
const quotaServer = (riga, pid) => (riga.celle[pid] || {}).quota || "";
function quotaCella(G, riga, pid) { const k = chiaveCella(riga, pid); return G.mod.has(k) ? G.mod.get(k) : quotaServer(riga, pid); }
const QUOTA_CELLA = /^\s*(0|\d+\s*\/\s*[1-9]\d*)?\s*$/;   // vuota o 0 toglie il soggetto dalla riga
const quotaValida = (G, riga, pid) => { const v = quotaCella(G, riga, pid); return QUOTA_CELLA.test(v) || v === quotaServer(riga, pid); };
function esitoRigaGriglia(G, riga) {
  if (riga.esito === "righe_doppie") return { cls: "er", testo: "righe doppie nel quadro DV", somma: riga.somma };
  const valori = G.dati.colonne.map(c => [c.id, String(quotaCella(G, riga, c.id)).trim()]).filter(([, v]) => v && v !== "0");
  if (!valori.length) return { cls: "", testo: "nessuna quota", somma: "—" };
  if (valori.some(([pid]) => !quotaValida(G, riga, pid))) return { cls: "er", testo: "quota da correggere", somma: "—" };
  const s = sommaQuote(valori.map(([, v]) => v.replace(/\s+/g, "")));
  if (s.nonNote) return { cls: "am", testo: s.nonNote === 1 ? "1 quota da indicare" : s.nonNote + " quote da indicare", somma: "—" };
  const somma = s.n + "/" + s.d;
  return s.n === s.d ? { cls: "ok", testo: "completa", somma } : s.n > s.d ? { cls: "er", testo: "supera 1/1", somma }
    : { cls: "am", testo: "manca " + (s.d - s.n) + "/" + s.d, somma };
}
function selettoreVistaDV() {
  const v = S.vistaDV || "griglia";
  const b = (k, t) => h("button", { type: "button", role: "tab", "aria-selected": v === k ? "true" : "false", onclick: () => cambiaVistaDV(k) }, t);
  return h("div", { class: "seg seg-vista", role: "tablist", "aria-label": "Vista del quadro DV" }, b("elenco", "Elenco"), b("griglia", "Griglia delle quote"));
}
function cambiaVistaDV(k) {
  if ((S.vistaDV || "griglia") === k) return;
  S.vistaDV = k; S.riga = null; S.chiuso = "DV"; S.tab = "dati";
  try { localStorage.setItem("successioni.vistaDV", k); } catch (_) { /* facoltativo */ }
  render();
}
const grigliaAperta = q => !!(q && q.id === "DV" && S.vistaDV === "griglia");
async function renderGrigliaQuote(main) {
  const box = h("div", { class: "griglia-quote" }, h("p", { class: "mut" }, "Caricamento della griglia…")); main.append(box);
  const pid = S.P.pratica_id;
  let G = S.griglia;
  if (!G || G.pid !== pid || (!G.mod.size && G.dati.revisione !== S.P.revisione)) {
    let d;
    try { d = await api("/api/pratiche/" + pid + "/quote-griglia"); }
    catch (e) { if (box.isConnected) box.replaceChildren(h("div", { class: "avv" }, "Griglia non disponibile: " + e.message)); return; }
    if (!box.isConnected || !S.P || S.P.pratica_id !== pid) return;
    G = S.griglia = { pid, dati: d, mod: new Map(), sel: new Set() };
  }
  disegnaGriglia(box, G);
  fuocoGriglia(box, G);
}
/* «Vai al dato» da un rilievo sulla somma delle quote di un bene (ispettore.js, vaiA): riga evidenziata e cursore nella prima casella vuota. */
function fuocoGriglia(box, G) {
  const f = S.grigliaFuoco; if (!f) return; S.grigliaFuoco = null;
  const bene = (S.P.dati.beni || []).find(b => b.id === f.bene), sd = struttDi("devoluzioni", "diritto", bene && bene.tipo);
  const dir = sd ? riconosciVoce(sd, String(f.diritto || "")) : f.diritto;
  const righe = G.dati.righe.map((r, i) => [r, i]).filter(([r]) => r.bene_id === f.bene);
  const scelta = righe.find(([r]) => r.diritto === dir || r.diritto === f.diritto) || righe[0];
  if (!scelta) return;
  const celle = [...box.querySelectorAll('input.cella-quota[data-r="' + scelta[1] + '"]')];
  const tr = celle[0] && celle[0].closest("tr"); if (!tr) return;
  tr.classList.add("evidenziata"); tr.scrollIntoView({ block: "center" });
  const vuota = celle.find(x => !x.value.trim() && !x.disabled) || celle.find(x => !x.disabled);
  if (vuota) vuota.focus();
}
function disegnaGriglia(box, G) {
  box.replaceChildren();
  const { colonne, righe, fuori_griglia: fuori } = G.dati;
  const altre = nMod() - (G.mod.size ? 1 : 0) > 0;            // modifiche nell'elenco o in altri quadri, non ancora salvate
  const superata = G.dati.revisione !== S.P.revisione;          // la pratica e' cambiata dopo che la griglia e' stata letta
  const sola = altre || superata;
  if (altre) box.append(h("div", { class: "nota" }, "Ci sono modifiche non salvate fuori dalla griglia: salvale per vederle qui e scrivere le quote. ",
    h("button", { class: "gh", type: "button", onclick: () => salvaTutto() }, "Salva")));
  if (superata && !altre) box.append(h("div", { class: "nota" }, "La pratica è cambiata dopo l'apertura della griglia. ",
    h("button", { class: "gh", type: "button", onclick: () => { if (!G.mod.size || confirm("Le quote scritte nella griglia e non salvate andranno perse. Continuare?")) { S.griglia = null; render(); } } }, "Ricarica la griglia")));
  if (!righe.length) { box.append(h("p", { class: "mut" }, "Nessun bene nella pratica: la griglia mostra una riga per ogni bene dei quadri dei beni.")); return; }
  if (!colonne.length) { box.append(h("p", { class: "mut" }, "Nessun erede o legatario: aggiungili nel quadro EA, poi torna qui a ripartire i beni.")); return; }
  const nSel = () => [...G.sel].filter(i => righe[i] && righe[i].esito !== "righe_doppie").length;
  const bSalva = h("button", { class: "pil", type: "button", onclick: occupato("griglia-salva", () => salvaGriglia()) }, "Salva le quote");
  const bAnnulla = h("button", { class: "gh", type: "button", onclick: () => { if (confirm("Annullare le quote scritte nella griglia e non salvate?")) { G.mod.clear(); aggiornaBottoni(); renderSb(); disegnaGriglia(box, G); } } }, "Annulla le modifiche");
  const bRip = h("button", { class: "gh", type: "button", onclick: () => ripartizioneGriglia(G, box) }, "Stessa ripartizione sulle righe scelte…");
  const stato = h("span", { class: "mut", "aria-live": "polite" });
  const aggiornaBarra = () => {
    const n = G.mod.size, s = nSel();
    bSalva.disabled = sola || !n; bAnnulla.disabled = !n; bRip.disabled = sola || !s;
    stato.textContent = (n ? n + (n === 1 ? " quota da salvare" : " quote da salvare") : "Nessuna modifica") + (s ? " · " + s + (s === 1 ? " riga scelta" : " righe scelte") : "");
  };
  box.append(h("div", { class: "barra barra-griglia" }, bSalva, bAnnulla, bRip, stato));
  const tutte = h("input", { type: "checkbox", "aria-label": "Scegli tutte le righe", onchange: ev => {
    G.sel = ev.target.checked ? new Set(righe.map((r, i) => i).filter(i => righe[i].esito !== "righe_doppie")) : new Set();
    for (const c of tb.querySelectorAll("input.sc-riga")) c.checked = G.sel.has(+c.dataset.r);
    aggiornaBarra();
  } });
  const t = h("table", { class: "tab-griglia", "aria-label": "Griglia delle quote: beni per soggetto" });
  t.append(h("thead", {}, h("tr", {}, h("th", { class: "c-sc" }, tutte), h("th", { class: "fissa-sx" }, "Bene"), h("th", {}, "Diritto"),
    h("th", { class: "n", title: "Quota del bene posseduta dal defunto: solo un'informazione, la somma della riga deve fare 1/1" }, "Quota del defunto"),
    colonne.map(c => h("th", { class: "n c-sogg", title: [c.nome, c.ruolo, c.codice_fiscale].filter(Boolean).join(" · ") }, c.nome)),
    h("th", { class: "n" }, "Somma"), h("th", {}, "Esito"))));
  const tb = h("tbody"); t.append(tb);
  righe.forEach((riga, i) => {
    const doppia = riga.esito === "righe_doppie";
    const sSomma = h("td", { class: "n c-somma" }), sEsito = h("td", { class: "c-esito" });
    const aggiornaRiga = () => {
      const e = esitoRigaGriglia(G, riga);
      sSomma.textContent = e.somma;
      sEsito.replaceChildren(...[h("span", { class: "pz " + e.cls }, e.testo), doppia ? h("button", { class: "lk", type: "button", onclick: () => cambiaVistaDV("elenco") }, "Sistema nell'elenco") : null].filter(Boolean));   // append(null) scriverebbe «null»
    };
    const celle = colonne.map(c => {
      const cella = riga.celle[c.id], ag = cella && cella.agevolazione;
      const inp = h("input", { type: "text", class: "cella-quota", inputmode: "numeric", autocomplete: "off", value: quotaCella(G, riga, c.id),
        "data-r": i, "data-c": c.id, "aria-label": "Quota di " + c.nome + " su " + riga.bene + (riga.diritto_testo ? " (" + riga.diritto_testo + ")" : ""),
        readonly: doppia || sola ? true : null, placeholder: "—" });
      const td = h("td", { class: "n c-cella" + (G.mod.has(chiaveCella(riga, c.id)) ? " cambiata" : "") }, inp,
        h("span", { class: "ag-cella", title: ag ? "Agevolazione " + ag + " su questa riga di devoluzione" : null }, ag || ""));   // sempre presente: le caselle restano allineate
      const segna = () => { inp.setAttribute("aria-invalid", quotaValida(G, riga, c.id) ? "false" : "true"); };
      inp.addEventListener("input", () => {
        const k = chiaveCella(riga, c.id), v = inp.value;
        if (v.trim() === quotaServer(riga, c.id).trim() || (!v.trim() && !quotaServer(riga, c.id))) G.mod.delete(k); else G.mod.set(k, v);
        td.classList.toggle("cambiata", G.mod.has(k)); segna(); aggiornaRiga(); aggiornaBarra(); aggiornaBottoni(); renderSb();
      });
      inp.addEventListener("keydown", ev => {   // come un foglio di calcolo: Invio e frecce su/giu' nella stessa colonna
        const passo = ev.key === "ArrowDown" || (ev.key === "Enter" && !ev.shiftKey) ? 1 : ev.key === "ArrowUp" || (ev.key === "Enter" && ev.shiftKey) ? -1 : 0;
        if (!passo) return;
        const altro = tb.querySelector('input.cella-quota[data-r="' + (i + passo) + '"][data-c="' + CSS.escape(c.id) + '"]');
        ev.preventDefault(); if (altro) { altro.focus(); altro.select(); }
      });
      segna(); return td;
    });
    const sc = h("input", { type: "checkbox", class: "sc-riga", "data-r": i, "aria-label": "Scegli " + riga.bene, checked: G.sel.has(i), disabled: doppia || null,
      onchange: ev => { ev.target.checked ? G.sel.add(i) : G.sel.delete(i); aggiornaBarra(); } });
    tb.append(h("tr", { class: doppia ? "riga-doppia" : null }, h("td", { class: "c-sc" }, sc),
      h("td", { class: "fissa-sx c-bene", title: riga.bene }, riga.quadro ? h("span", { class: "sigla-riga" }, riga.quadro) : null, riga.bene),
      h("td", {}, riga.diritto_testo || "—"), h("td", { class: "n mut" }, riga.quota_defunto || "—"), celle, sSomma, sEsito));
    aggiornaRiga();
  });
  box.append(h("div", { class: "tab" }, t));
  if (fuori && fuori.length) box.append(h("p", { class: "nota" }, fuori.length + (fuori.length === 1 ? " riga del quadro DV non compare" : " righe del quadro DV non compaiono")
    + " nella griglia perché manca il bene o il soggetto: " + [...new Set(fuori.map(x => x.motivo))].join("; ") + ". ",
    h("button", { class: "lk", type: "button", onclick: () => cambiaVistaDV("elenco") }, "Apri l'elenco")));
  box.append(h("p", { class: "mut nota-griglia" }, "Scrivi le quote come frazioni (1/2, 1/3). Una casella vuota o 0 toglie il soggetto dal bene. Invio passa alla riga sotto."));
  aggiornaBarra();
}
async function salvaGriglia() {
  const G = S.griglia; if (!G || !G.mod.size) return true;
  const celle = [];
  for (const [k, v] of G.mod) {
    const [bene_id, diritto, persona_id] = k.split("|");
    if (!QUOTA_CELLA.test(v)) { msg("Quota non valida: «" + v + "». Scrivi una frazione come 1/2, oppure lascia vuoto per togliere il soggetto.", "e"); return false; }
    celle.push({ bene_id, persona_id, diritto, quota: v.replace(/\s+/g, "") });
  }
  if (S.writeBusy) { msg("Salvataggio già in corso. Le quote restano da salvare.", "e"); return false; }
  S.writeBusy = true; aggiornaBottoni();
  try {
    const r = await post("/api/pratiche/" + G.pid + "/quote-griglia", { revisione_attesa: G.dati.revisione, chiave: crypto.randomUUID(), celle });
    G.dati = { ...r.griglia, revisione: r.revisione }; G.mod.clear();
    await ricarica(); render();
    msg("Quote salvate (revisione " + r.revisione + ").", "o"); caricaPratiche(); return true;
  } catch (e) {
    if (e.stato === 409) msg("La pratica è stata modificata altrove: le quote non sono state salvate. Ricarica la griglia e scrivile di nuovo.", "e");
    else msg("Quote non salvate: " + e.message, "e");
    return false;
  } finally { S.writeBusy = false; aggiornaBottoni(); }
}
/* «Stessa ripartizione su piu' beni» (come in DEAS): le quote scritte una volta vanno su tutte le righe scelte; poi «Salva le quote». */
function ripartizioneGriglia(G, box) {
  const scelte = [...G.sel].map(i => G.dati.righe[i]).filter(r => r && r.esito !== "righe_doppie");
  if (!scelte.length) return msg("Scegli almeno una riga della griglia.", "e");
  const somma = h("span", { class: "pz" });
  const campi = G.dati.colonne.map(c => [c, h("input", { type: "text", class: "cella-quota", autocomplete: "off", value: quotaCella(G, scelte[0], c.id), placeholder: "—", "aria-label": "Quota di " + c.nome })]);
  const ricalcola = () => {
    const v = campi.map(([, i]) => i.value.trim()).filter(x => x && x !== "0");
    if (v.some(x => !QUOTA_CELLA.test(x))) { somma.className = "pz er"; somma.textContent = "quota da correggere"; return; }
    const s = sommaQuote(v.map(x => x.replace(/\s+/g, "")));
    somma.className = "pz " + (!v.length ? "" : s.n === s.d ? "ok" : s.n > s.d ? "er" : "am");
    somma.textContent = v.length ? "somma " + s.n + "/" + s.d : "nessuna quota";
  };
  campi.forEach(([, i]) => i.addEventListener("input", ricalcola)); ricalcola();
  const corpo = h("div", {}, h("p", { class: "mut" }, "Le quote scritte qui vanno su " + (scelte.length === 1 ? "la riga scelta" : "tutte le " + scelte.length + " righe scelte")
    + ". Una casella vuota toglie il soggetto da quelle righe. Poi premi «Salva le quote»."),
    h("div", { class: "rip-campi" }, campi.map(([c, i]) => h("label", { class: "rip-campo" }, h("span", {}, c.nome), i))), h("p", {}, somma),
    h("details", { class: "rip-righe" }, h("summary", {}, "Righe scelte (" + scelte.length + ")"), h("ul", {}, scelte.map(r => h("li", {}, (r.quadro ? r.quadro + " · " : "") + r.bene + (r.diritto_testo ? " — " + r.diritto_testo : ""))))));
  dialogo("dRipartizione", "Stessa ripartizione sulle righe scelte", corpo, "Applica alle righe", () => {
    const err = campi.find(([, i]) => !QUOTA_CELLA.test(i.value));
    if (err) return "Quota non valida per " + err[0].nome + ": scrivi una frazione come 1/2, oppure lascia vuoto.";
    for (const r of scelte) for (const [c, i] of campi) {
      const k = chiaveCella(r, c.id), v = i.value.trim();
      if (v === quotaServer(r, c.id).trim() || (!v && !quotaServer(r, c.id))) G.mod.delete(k); else G.mod.set(k, v);
    }
    disegnaGriglia(box, G); aggiornaBottoni(); renderSb();
    msg("Ripartizione applicata a " + scelte.length + (scelte.length === 1 ? " riga" : " righe") + ": controlla e premi «Salva le quote».", "o");
  });
}
/* Agevolazioni guidate (come in DEAS): codice → beni → soggetti → Fine. Il codice va sulle righe di devoluzione esistenti dei beni
   e dei soggetti scelti; i beni proposti sono solo quelli dei quadri in cui l'esportazione ammette il codice (server:
   /agevolazioni-guidate). Non crea righe di devoluzione: le coppie senza riga tornano come avviso. */
async function agevolazioniGuidate() {
  if (S.writeBusy || !(await primaSalva())) return;
  const pid = S.P.pratica_id;
  let d;
  try { d = await api("/api/pratiche/" + pid + "/agevolazioni-guidate"); } catch (e) { return msg(e.message, "e"); }
  if (!S.P || S.P.pratica_id !== pid) return;
  const W = { passo: 1, codice: null, beni: new Set(), persone: new Set() };
  const codice = () => d.codici.find(c => c.valore === W.codice);
  const beniAmmessi = () => d.beni.filter(b => W.codice === "" ? b.beneficiari.length : (codice() && codice().quadri.includes(b.quadro)));
  const soggetti = () => {
    const m = new Map();
    for (const b of d.beni.filter(x => W.beni.has(x.bene_id))) for (const x of b.beneficiari) if (!m.has(x.persona_id)) m.set(x.persona_id, { ...x, codici: new Set() });
    for (const b of d.beni.filter(x => W.beni.has(x.bene_id))) for (const x of b.beneficiari) if (x.agevolazione) m.get(x.persona_id).codici.add(x.agevolazione);
    return [...m.values()];
  };
  const err = h("p", { class: "err e", role: "alert", hidden: true });
  const corpo = h("div", { class: "agev-corpo" });
  const passi = h("ol", { class: "agev-passi", "aria-label": "Passi" });
  const bIndietro = h("button", { type: "button", class: "gh", onclick: () => { W.passo--; disegna(); } }, "Indietro");
  const bAvanti = h("button", { type: "button", class: "pil", onclick: () => avanti() }, "Avanti");
  const dlg = h("dialog", { id: "dAgevolazioni", class: "dlg-op dlg-agev", "aria-labelledby": "dAgevolazioniT" },
    h("form", { method: "dialog", onsubmit: ev => ev.preventDefault() }, h("h2", { id: "dAgevolazioniT" }, "Agevolazioni guidate"), passi, corpo, err,
      h("div", { class: "wiz-az" }, h("button", { type: "button", class: "gh", onclick: () => dlg.close() }, "Annulla"), h("span", { class: "sp" }), bIndietro, bAvanti)));
  dlg.addEventListener("close", () => dlg.remove());
  const spunta = (insieme, id, testo, extra, disab) => h("label", { class: "riga-sc" + (disab ? " mut" : "") },
    h("input", { type: "checkbox", checked: insieme.has(id), disabled: disab || null, onchange: ev => { ev.target.checked ? insieme.add(id) : insieme.delete(id); err.hidden = true; } }), " ", testo, extra ? h("span", { class: "mut" }, " " + extra) : null);
  const tutti = (insieme, ids) => h("div", { class: "agev-tutti" }, h("button", { type: "button", class: "lk", onclick: () => { ids.forEach(x => insieme.add(x)); disegna(); } }, "Scegli tutti"),
    " · ", h("button", { type: "button", class: "lk", onclick: () => { insieme.clear(); disegna(); } }, "Nessuno"));
  function disegna() {
    err.hidden = true;
    passi.replaceChildren(...["Codice", "Beni", "Soggetti"].map((t, i) => h("li", { class: i + 1 === W.passo ? "attivo" : i + 1 < W.passo ? "fatto" : null, "aria-current": i + 1 === W.passo ? "step" : null }, t)));
    bIndietro.hidden = W.passo === 1; bAvanti.textContent = W.passo === 3 ? "Fine" : "Avanti";
    corpo.replaceChildren();
    if (W.passo === 1) {
      // spiegazione completa nel suggerimento: a video solo i quadri in cui il codice vale (l'utente ha chiesto meno testo)
      const voce = (valore, titolo, aiuto, spiega) => h("label", { class: "agev-codice", title: spiega || null }, h("input", { type: "radio", name: "agevCodice", value: valore, checked: W.codice === valore,
        onchange: () => { W.codice = valore; W.beni.clear(); W.persone.clear(); err.hidden = true; } }), h("span", {}, h("b", {}, titolo), aiuto ? h("span", { class: "mut aiuto-codice" }, aiuto) : null));
      corpo.append(h("p", { class: "mut" }, "Scegli il codice da indicare sulle righe di devoluzione."),
        h("div", { class: "agev-codici", role: "radiogroup", "aria-label": "Codice di agevolazione" },
          d.codici.map(c => voce(c.valore, c.valore + " — " + c.etichetta, c.quadri.length ? "Quadri " + c.quadri.join(", ") : "", c.aiuto)),
          voce("", "Togli il codice", "Le righe scelte restano senza agevolazione.")));
    } else if (W.passo === 2) {
      const ammessi = beniAmmessi();
      corpo.append(h("p", { class: "mut" }, W.codice ? "Beni dei quadri in cui il codice " + W.codice + " è ammesso (" + codice().quadri.join(", ") + ")." : "Beni con righe di devoluzione."));
      if (!ammessi.length) corpo.append(h("p", { class: "nota" }, "Nessun bene della pratica è in questi quadri."));
      else corpo.append(tutti(W.beni, ammessi.filter(b => b.beneficiari.length).map(b => b.bene_id)), h("div", { class: "agev-elenco" }, ammessi.map(b => spunta(W.beni, b.bene_id,
        (b.quadro ? b.quadro + " · " : "") + b.bene, b.beneficiari.length ? "(" + b.beneficiari.length + (b.beneficiari.length === 1 ? " beneficiario)" : " beneficiari)") : "(nessuna devoluzione: assegna prima le quote)", !b.beneficiari.length))));
    } else {
      const ss = soggetti();
      corpo.append(h("p", { class: "mut" }, "Soggetti che ricevono i beni scelti."), tutti(W.persone, ss.map(x => x.persona_id)),
        h("div", { class: "agev-elenco" }, ss.map(x => spunta(W.persone, x.persona_id, x.nome, x.codici.size ? "(oggi: " + [...x.codici].join(", ") + ")" : null))));
    }
    if (dlg.open) { const primo = corpo.querySelector("input:checked:not(:disabled), input:not(:disabled)"); if (primo) primo.focus(); }
  }
  const mostra = t => { err.textContent = t; err.hidden = false; };
  async function avanti() {
    if (W.passo === 1) { if (W.codice === null) return mostra("Scegli un codice, oppure «Togli il codice»."); W.passo = 2; return disegna(); }
    if (W.passo === 2) {
      if (!W.beni.size) return mostra("Scegli almeno un bene.");
      if (!W.persone.size) soggetti().forEach(x => W.persone.add(x.persona_id));   // al primo passaggio tutti i beneficiari sono gia' scelti
      W.passo = 3; return disegna();
    }
    if (!W.persone.size) return mostra("Scegli almeno un soggetto.");
    bAvanti.disabled = true;
    try {
      const r = await post("/api/pratiche/" + pid + "/agevolazioni-guidate", { revisione_attesa: d.revisione, chiave: crypto.randomUUID(), codice: W.codice, beni: [...W.beni], persone: [...W.persone] });
      dlg.close();
      if (r.cambiate) { await ricarica(); render(); caricaPratiche(); }
      const senza = (r.senza_devoluzione || []).length;
      const testo = !r.cambiate ? "Nessuna modifica: le righe scelte avevano già " + (W.codice ? "il codice " + W.codice : "nessun codice") + "."
        : (W.codice ? "Codice " + W.codice + " indicato su " : "Codice tolto da ") + r.cambiate + (r.cambiate === 1 ? " riga di devoluzione" : " righe di devoluzione") + " (revisione " + r.revisione + ").";
      msg(testo + (senza ? " " + senza + (senza === 1 ? " coppia bene-soggetto non ha" : " coppie bene-soggetto non hanno") + " una riga di devoluzione e " + (senza === 1 ? "è rimasta" : "sono rimaste") + " senza codice." : ""), senza ? "e" : "o");
    } catch (e) {
      if (e.stato === 409) { dlg.close(); msg("La pratica è stata modificata altrove: riapri «Agevolazioni guidate».", "e"); await ricarica(); render(); }
      else mostra(e.message);
    } finally { bAvanti.disabled = false; }
  }
  document.body.append(dlg); disegna(); dlg.showModal(); disegna();   // il fuoco va sul primo campo, non sul riquadro
}
