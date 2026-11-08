/* Layout, tastiera e accessibilita' trasversali (nessuna logica di dominio).
   - schermo stretto (<= 960 px): menu dei quadri a cassetto (#bNav), azioni secondarie della barra alta in un menu (#bMenu);
   - Esc dal pannello dati riporta il focus alla riga selezionata della tabella;
   - ogni <label> senza `for` viene collegata al suo campo con un id univoco (osservatore del DOM: vale per schede,
     ispettore e finestre, anche per le parti costruite altrove). Gli aria-label dei campi non vengono toccati. */
(() => {
  "use strict";
  const stretto = () => window.innerWidth <= 960;
  const body = document.body;

  function apriNav(aperta) {
    body.classList.toggle("navAperta", aperta);
    document.getElementById("velo").hidden = !aperta;
    document.getElementById("bNav").setAttribute("aria-expanded", String(aperta));
    if (aperta) { const primo = document.querySelector("#lat button"); if (primo) primo.focus(); }
  }
  function apriAzioni(aperte) {
    body.classList.toggle("azioniAperte", aperte);
    document.getElementById("bMenu").setAttribute("aria-expanded", String(aperte));
  }
  document.getElementById("bNav").addEventListener("click", () => apriNav(!body.classList.contains("navAperta")));
  document.getElementById("velo").addEventListener("click", () => apriNav(false));
  document.getElementById("bMenu").addEventListener("click", () => apriAzioni(!body.classList.contains("azioniAperte")));
  document.getElementById("lat").addEventListener("click", ev => {
    if (stretto() && ev.target.closest("button")) setTimeout(() => apriNav(false), 0);
  });
  document.getElementById("azioni").addEventListener("click", ev => {
    const b = ev.target.closest("button");
    if (b && b.id !== "bMenu") apriAzioni(false);
  });
  window.addEventListener("resize", () => { if (!stretto()) { apriNav(false); apriAzioni(false); } });

  /* Cassetto aperto (schermo stretto): Tab e Maiusc+Tab restano dentro il menu, come in una finestra modale. */
  const FOCUSABILI = "button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex='-1'])";
  document.addEventListener("keydown", ev => {
    if (ev.key !== "Tab" || !body.classList.contains("navAperta")) return;
    const lat = document.getElementById("lat");
    const el = [...lat.querySelectorAll(FOCUSABILI)].filter(x => x.getClientRects().length);
    if (!el.length) return;
    const primo = el[0], ultimo = el[el.length - 1], dentro = lat.contains(document.activeElement);
    if (ev.shiftKey && (!dentro || document.activeElement === primo)) { ev.preventDefault(); ultimo.focus(); }
    else if (!ev.shiftKey && (!dentro || document.activeElement === ultimo)) { ev.preventDefault(); primo.focus(); }
  });

  /* Barra alta compatta: se le azioni non stanno su una riga (portatile 1366, carattere grande), i pulsanti secondari mostrano
     solo l'icona (il testo resta nel DOM con carattere a zero: nome accessibile invariato; il suggerimento title lo mostra); se non basta, anche Controlla e File e invio.
     --alto-barra serve all'altezza della tabella, cosi' le righe visibili crescono quando la barra e' bassa. */
  const tb = document.querySelector(".tb"), azioni = document.getElementById("azioni");
  function vaACapo() {
    const brand = document.getElementById("bHome"), primo = document.getElementById("bSalva");
    return azioni.offsetTop > brand.offsetTop + brand.offsetHeight / 2 || azioni.offsetHeight > primo.offsetHeight * 1.6;
  }
  function compattaBarra() {
    body.dataset.barra = "";
    if (!stretto()) {
      if (vaACapo()) body.dataset.barra = "icone";
      if (body.dataset.barra && vaACapo()) body.dataset.barra = "minima";
    }
    document.documentElement.style.setProperty("--alto-barra", Math.round(tb.getBoundingClientRect().height) + "px");
  }
  let attesa = false;
  const pianifica = () => { if (attesa) return; attesa = true; requestAnimationFrame(() => { attesa = false; compattaBarra(); }); };
  window.compattaBarra = pianifica;
  new ResizeObserver(pianifica).observe(tb);
  window.addEventListener("resize", pianifica);
  compattaBarra();

  document.addEventListener("keydown", ev => {
    if (ev.key !== "Escape" || ev.defaultPrevented) return;
    if (body.classList.contains("navAperta")) { apriNav(false); document.getElementById("bNav").focus(); return; }
    const ins = document.getElementById("ins");
    if (ins && !ins.hidden && ins.contains(ev.target) && typeof S !== "undefined" && S.riga) {
      const tr = document.querySelector('tr[data-key="' + CSS.escape(S.riga) + '"]');
      if (tr) { ev.preventDefault(); tr.focus(); }
    }
  });

  /* Collegamento label -> campo. */
  const CAMPO = "input:not([type=hidden]),select,textarea";
  let contatore = 0;
  function idUnivoco(el) {
    if (el.id) return el.id;
    const base = "f_" + String((el.dataset && el.dataset.path) || "c" + (++contatore)).replace(/[^A-Za-z0-9_-]+/g, "_");
    let id = base;
    while (document.getElementById(id)) id = base + "_" + (++contatore);
    el.id = id;
    return id;
  }
  function campoDi(label) {
    for (let n = label.nextElementSibling; n; n = n.nextElementSibling) {
      if (n.tagName === "LABEL") return null;
      if (n.matches(CAMPO)) return n;
      const dentro = n.querySelector(CAMPO);
      if (dentro) return dentro;
    }
    return null;
  }
  function collegaEtichette() {
    for (const l of document.querySelectorAll("label:not([for])")) {
      if (l.querySelector(CAMPO)) continue;            // etichetta che racchiude il campo: gia' associata
      const c = campoDi(l);
      if (c) l.htmlFor = idUnivoco(c);
    }
  }
  let programmata = false;
  new MutationObserver(() => {
    if (programmata) return;
    programmata = true;
    queueMicrotask(() => { programmata = false; collegaEtichette(); });
  }).observe(body, { childList: true, subtree: true });
  collegaEtichette();
})();
