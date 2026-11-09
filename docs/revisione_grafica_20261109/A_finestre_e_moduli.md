# Revisione grafica A: finestre e moduli

Data: 9/11/2026. Ambito: procedura «Nuova dichiarazione» (S30–S36), Impostazioni (S40–S46, S103), calcolatrice (S10–S12), Guida (S20), preventivo (S90), fascicolo (S91), incolla da Excel e modifica di gruppo (S57, più una cattura aggiuntiva della modifica di gruppo sul quadro DV con dati sintetici), Vai al quadro (S55), scorciatoie (S56).
Metodo: design-critique (prima impressione, gerarchia, coerenza, accessibilità) e linee guida «Forms & Feedback» di ui-ux-pro-max (`input-labels`, `input-helper-text`, `weight-hierarchy` con etichette a 500 e testo a 400, `whitespace-balance`, `touch-spacing` con almeno 8 px tra controlli).
Misure prese sull'istanza di prova 8833 (dati sintetici, base del carattere 16 px) con Playwright: stili calcolati e rettangoli.
Vincolo: solo rifinitura. Niente nuovo layout, niente sezioni spostate, niente componenti nuovi, testi invariati.

## Prima impressione (2 secondi)

Le finestre hanno una buona ossatura: titolo, corpo, piede fisso con l'azione primaria piena a destra. La procedura guidata, al passo 3, e la calcolatrice sono ordinate.
Il disordine che l'utente vede in **Operatività** viene quasi tutto da **una sola regola**, `.campo label` (app.css:204). La regola:
- vince sulla classe `.chk`, quindi le caselle perdono lo spazio dal loro testo;
- dà all'etichetta lo stesso colore (`--t2`) e la stessa dimensione (`--fs-m`) dell'aiuto.

Inoltre `.campo` non ha alcun margine, quindi le voci si toccano. Misura: il fondo dell'aiuto è a y=1742 e l'etichetta successiva inizia a y=1741.
Gli stessi difetti ritornano in Aspetto, Strumenti, Modifica di gruppo e Preventivo.

---

## Rilievi (dal più importante)

### A01. Caselle incollate al loro testo
- **Schermate:** S43_impostazioni_operativita_1440/1920, S42_impostazioni_aspetto_1440_p2/p3, S103_scuro_impostazioni_operativita_1440
- **Problema visto:** «☑Elimina automaticamente…», «☐EA», «☐EB»: il quadratino tocca la prima lettera. Lo stacco misurato è di 3 px, cioè il margine di serie del browser. Nella procedura guidata, passo 3 (S35), le stesse caselle hanno invece 8 px di stacco e sono allineate bene.
- **Causa:** `.campo label { display:block }` (app.css:204) ha specificità 0,1,1 e batte `.chk { display:flex; gap }` (app.css:166), che ha 0,1,0. Anche `#imp .chk` (app.css:285) non reimposta `display`. Valore calcolato: `display:block`, quindi il `gap: 8px` resta senza effetto.
- **Correzione minima:**
  ```css
  .campo label.chk { display:flex; align-items:flex-start; gap:var(--s-2); color:var(--t); }
  .campo label.chk input { margin:.2em 0 0; flex:none; }
  ```
- **Gravità:** alta
- **Finestre:** Impostazioni › Operatività (3 caselle), Impostazioni › Aspetto (15 caselle «Quadri proposti»)

### A02. Aiuto con lo stesso peso dell'etichetta
- **Schermate:** S43, S46_impostazioni_strumenti_1440_p1–p3, S45, S32_wizard_1_compilato (nota del codice fiscale)
- **Problema visto:** etichetta, testo della casella e aiuto sono tutti grigi (`rgb(85,97,95)`), a 14,86 px e con peso 400: misura identica sui tre elementi. L'occhio non distingue la voce dalla sua spiegazione. In Strumenti, sotto ogni percorso, la riga di stato («✓ in uso: …») e la nota hanno lo stesso aspetto, una di seguito all'altra.
- **Causa:**
  - `.campo label { font-size:var(--fs-m); color:var(--t2) }` (app.css:204);
  - l'aiuto usa `.mut.testo-m` (app.css:81 e 349), cioè la stessa misura `--fs-m` e lo stesso colore `--t2`.
- **Correzione minima:** l'etichetta diventa inchiostro a peso 500; l'aiuto scende di un passo e si stacca di 4 px dal campo.
  ```css
  .campo > label:not(.chk) { color:var(--t); font-weight:500; margin-bottom:var(--s-1); }
  .campo > .mut { font-size:var(--fs-s); line-height:1.45; margin-top:var(--s-1); max-width:72ch; }
  .campo > .mut + .mut { margin-top:var(--s-05); }
  ```
- **Gravità:** alta
- **Finestre:** Impostazioni (tutte le sezioni), procedura guidata passo 1, Vai al quadro, calcolatrice (etichetta «Data del decesso»)

### A03. Nessun ritmo tra le voci
- **Schermate:** S43, S103
- **Problema visto:** in Operatività ogni voce attacca la successiva. Lo stacco tra l'aiuto e l'etichetta seguente è di 0 px, quello tra l'etichetta e il suo campo di 2 px. Non si capisce dove finisce una voce e dove inizia l'altra.
- **Causa:**
  - `.campo` non ha margini: rettangolo misurato `marginTop:0` e `marginBottom:0`;
  - `#imp .imp-sezioni > section` (app.css:280) dà spazio solo alla sezione intera;
  - nelle griglie (Aspetto, procedura guidata) il ritmo lo dà il `gap`, ma qui la sezione non è una griglia.
- **Correzione minima:**
  ```css
  #imp .imp-sezioni > section > .campo { margin-bottom:var(--s-4); }
  #imp .imp-sezioni > section > .campo:last-child { margin-bottom:0; }
  ```
- **Gravità:** alta
- **Finestre:** Impostazioni › Operatività. Lo stesso principio vale per Diagnosi: `.diagnosi-voce` (app.css:292) ha oggi 6 px, servirebbero 12 px.

### A04. Campi numerici larghi come la finestra
- **Schermate:** S43 (24 e 90 in campi da 692 px), S46_p1 («Tempo massimo del controllo (secondi)», 692 px)
- **Problema visto:** un numero di 2 o 3 cifre sta in un campo largo come il paragrafo. La larghezza non suggerisce cosa scrivere e il numero resta lontano dalla sua unità.
- **Causa:** la regola generale `input, select, textarea { width:100% }` (app.css:85). Nessuna regola per `type=number` né per la voce del tempo massimo, che è un campo di testo.
- **Correzione minima:**
  ```css
  #imp input[type=number], #imp_SUCCESSIONI_CONTROLLI_TIMEOUT { width:8rem; text-align:right; font-variant-numeric:tabular-nums; }
  ```
- **Gravità:** alta
- **Finestre:** Impostazioni › Operatività, Impostazioni › Strumenti e percorsi

### A05. «Pulisci ora» attaccato al campo
- **Schermate:** S43, S103
- **Problema visto:** il pulsante parte esattamente dal bordo inferiore del campo «ore», con 0 px di stacco, e subito sotto ricomincia l'etichetta della visura. Sembra un'appendice del campo, non un comando.
- **Causa:** il pulsante è fratello della `.campo` nella sezione e non ha margini. In app.js:2564–2569 il pulsante viene aggiunto dopo `numero('pulizia_ore', …)`.
- **Correzione minima, solo CSS** (pulsante sotto il campo, con stacco e respiro):
  ```css
  /* selettore piu' specifico di quello di A03, altrimenti vince il margine da 16 px */
  #imp .imp-sezioni > section > .campo:has(+ button) { margin-bottom:var(--s-15); }
  #imp .imp-sezioni > section > .campo + button { margin-bottom:var(--s-4); }
  ```
  **Variante consigliata** (pulsante accanto al campo che governa, posizione nella pagina invariata): in app.js, `numero()` riceve il pulsante come quarto figlio e mette campo e pulsante in una riga. Basta una riga di JS più questa regola:
  ```css
  .campo-riga { display:flex; align-items:center; gap:var(--s-2); }
  ```
- **Gravità:** alta
- **Finestre:** Impostazioni › Operatività. Stessa regola per «Crea backup ora» ed «Esegui diagnosi», che oggi hanno uno stacco variabile di 12–16 px dal paragrafo.

### A06. Modifica di gruppo: «svuota il campo» stretto nella colonna delle etichette
- **Schermate:** S57_operazione_modifica_gruppo_1440. La cattura mostra solo il messaggio d'errore; il problema si vede aprendo la finestra sul quadro DV con dati sintetici (`revA/gruppo_1440.png`).
- **Problema visto:** la scelta secondaria «svuota il campo in tutte le righe scelte» finisce sotto l'etichetta, nella colonna da 150 px: va a capo su 2 righe. È in grassetto e nero come l'etichetta del campo, quindi ha lo stesso peso visivo.
- **Causa:**
  - `.rg { grid-template-columns:150px 1fr }` (app.css:151) colloca il terzo figlio nella colonna 1;
  - `.dlg-op .rg > label { font-weight:600 }` (app.css:437 e 441) colpisce anche `.gruppo-svuota`;
  - `.rg > label { color:var(--t) }` (app.css:152) batte `.gruppo-svuota { color:var(--t2) }` (app.css:532).
- **Correzione minima:**
  ```css
  .dlg-op .rg > .gruppo-svuota { grid-column:2; display:flex; align-items:center; gap:var(--s-15); font-weight:400; color:var(--t2); margin-top:0; }
  ```
- **Gravità:** media
- **Finestre:** Modifica di gruppo (beni, devoluzioni)

### A07. Procedura guidata, passo 1: larghezze uguali per dati di lunghezza diversa
- **Schermate:** S30, S31, S32_wizard_1_*_1440/1920
- **Problema visto:**
  - le province («RM», 2 lettere) e le date («GG/MM/AAAA») occupano 290 px come cognome e comune;
  - il codice fiscale (216 px) finisce prima delle colonne, per cui il bordo destro non è allineato;
  - tra una riga e l'altra ci sono 8 px, tra l'etichetta e il suo campo 2 px: proporzione giusta ma serrata.
- **Causa:** `.griglia { grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:var(--s-2) var(--s-3) }` (app.css:205), più `width:100%` della regola generale (app.css:85).
- **Correzione minima:**
  ```css
  .griglia { row-gap:var(--s-3); }
  #w_provincia_nascita, #w_provincia_decesso { width:5rem; text-transform:uppercase; }
  #w_data_nascita, #w_data_decesso { width:9.5rem; font-variant-numeric:tabular-nums; }
  ```
- **Gravità:** media
- **Finestre:** Nuova dichiarazione, passo 1

### A08. Procedura guidata: la finestra cambia posizione a ogni passo
- **Schermate:** S30 → S33 → S35 → S36. Misura del pulsante «Avanti» a 1440×900: y = 696, 565, 725, 545.
- **Problema visto:** la finestra si ricentra a ogni passo. Titolo, passi e pulsante «Avanti» saltano su e giù di 130–180 px, e chi preme Avanti più volte deve inseguire il pulsante.
- **Causa:** `dialog` (app.css:195) è centrato dal browser con `margin:auto` e ha l'altezza del contenuto. `#wiz` non ha regole proprie.
- **Correzione minima:** l'alto della finestra resta fermo e il corpo riempie lo spazio, così il piede sta sempre allo stesso posto.
  ```css
  #wiz { margin-block:8vh auto; }
  #wiz form { display:flex; flex-direction:column; min-height:min(40rem, 84vh); }
  #wizCorpo { flex:1; }
  ```
- **Gravità:** media
- **Finestre:** Nuova dichiarazione

### A09. Calcolatrice: data larga 600 px e importi allineati a sinistra
- **Schermate:** S10, S11_calcolatrice_compilata_1440_p1/1920_p1, S12
- **Problema visto:**
  - «Data del decesso» è larga quanto tutta la colonna dati (597 px misurati);
  - «300.000», «rendita» e i valori degli altri beni sono allineati a sinistra, mentre nel preventivo e nel prospetto gli importi sono a destra.
- **Causa:** `#calcData` prende `width:100%` (app.css:85). `.calc-riga input.n { width:7.5em }` (app.css:516) non ha `text-align`. La classe è `n`, non `num`, quindi la regola `input.num` (app.css:87) non si applica.
- **Correzione minima:**
  ```css
  #calcData { width:11.5rem; }
  .calc-riga input.n { text-align:right; font-variant-numeric:tabular-nums; }
  ```
- **Gravità:** media
- **Finestre:** Calcolatrice rapida

### A10. Guida › Tabelle e fonti: testo tagliato con i puntini
- **Schermate:** S20_guida_tabelle_1440_p1–p4, 1920_p1–p4
- **Problema visto:** la colonna «Fonte» finisce con «…passaggi calcolo imposta d…» e la colonna dei gradi con «10, 11, 12, …, 2…». In una tabella di consultazione si perde proprio l'informazione cercata.
- **Causa:** la regola generale `td { white-space:nowrap; max-width:240px; text-overflow:ellipsis }` (app.css:157). `table.tab-valori td` (app.css:651) non la annulla, come fanno invece `table.calc-imp td` (app.css:523) e `table.info-versione td` (app.css:466). Inoltre `border-bottom:1px solid var(--bd, #ddd)` (app.css:651) usa una variabile inesistente: nel tema scuro il bordo resta #ddd, molto chiaro.
- **Correzione minima:**
  ```css
  table.tab-valori td { white-space:normal; max-width:none; }
  table.tab-valori th, table.tab-valori td { border-bottom-color:var(--sep); }
  ```
- **Gravità:** media
- **Finestre:** Guida

### A11. Preventivo: larghezze invertite, «Togli» lontano, casella rientrata
- **Schermate:** S90_preventivo_1440/1920
- **Problema visto:**
  - «Numero» (pochi caratteri) è largo 232 px, mentre «Intestato a» taglia il proprio segnaposto («…codice fiscale del clien»);
  - «Data» è larga 210 px;
  - «Togli» sta 130 px a destra dell'importo, staccato dalla sua riga;
  - la casella «Aggiungi le imposte…» rientra di 16 px rispetto alle etichette e si porta dietro una riga di separazione che divide a metà il modulo.
- **Causa:**
  - `dialog.preventivo .prev-campi { grid-template-columns:max-content 1fr max-content 1fr }` (app.css:662);
  - nessuna larghezza per l'ultima colonna di `table.prev-voci` (app.css:657–661);
  - `.chk { padding:var(--s-1) var(--s-3); border-bottom:1px solid var(--sep) }` (app.css:166).
- **Correzione minima:**
  ```css
  dialog.preventivo .prev-campi { grid-template-columns:max-content 11rem max-content 1fr; }
  dialog.preventivo table.prev-voci td:last-child { width:1%; white-space:nowrap; }
  dialog.preventivo .chk { padding-left:0; padding-right:0; border-bottom:0; }
  ```
- **Gravità:** media
- **Finestre:** Preventivo e parcella

### A12. Caselle e pulsanti di scelta da 13 px, con stacchi diversi in ogni finestra
- **Schermate:** S43, S42_p2, S35, S34, S90, S10, modifica di gruppo
- **Problema visto:** con testo a 16 px la casella misura 13×13 px: piccola e difficile da centrare. Lo stacco dal testo cambia da finestra a finestra:

  | Finestra | Stacco casella–testo |
  |---|---|
  | Impostazioni | 3 px |
  | Calcolatrice | 4 px |
  | Procedura guidata | 8 px |
  | Modifica di gruppo | uno spazio di testo |

- **Causa:** nessuna regola di dimensione per le caselle. Ci sono solo `margin-top` e `accent-color` in `.chk input` (app.css:167), `.radio input` (app.css:203) e `.dlg-op input[type=checkbox]` (app.css:440).
- **Correzione minima** (limitata alle finestre, la tabella principale non cambia):
  ```css
  dialog input[type=checkbox], dialog input[type=radio] { width:1rem; height:1rem; flex:none; accent-color:var(--blu); }
  .calc-riga .chk { gap:var(--s-15); }
  ```
- **Gravità:** media
- **Finestre:** tutte quelle con caselle

### A13. «info» mostrato in rosso come un errore
- **Schermate:** S20_guida_info_1920_p1 (qpdf, Entratel-Multifile)
- **Problema visto:** le voci solo informative hanno la pillola rossa, come i guasti. Un componente facoltativo non rilevato sembra un errore.
- **Causa:** app.js:2976 mappa `ok → ok`, `avviso → am` e tutto il resto, `info` compreso, a `er`. Le classi `.pz.er` e `.pz.am` sono definite in app.css:163.
- **Correzione minima:** in app.js, `c.esito === "info" ? "" : …`, cioè pillola neutra con `.pz` (app.css:162). Nessun CSS nuovo.
- **Gravità:** media
- **Finestre:** Guida › Informazioni (ed eventuale elenco della diagnosi)

### A14. Segnaposto in carattere monospaziato e codice fiscale attaccato al bordo
- **Schermate:** S46_p1–p3 («non impostato» spaziato), S55 («es. EC»), S41 e S32 (codice fiscale)
- **Problema visto:**
  - i segnaposto dei percorsi e della sigla sono nel carattere a spaziatura fissa e sembrano valori veri;
  - nel codice fiscale il primo carattere, o il segnaposto «codice fiscale», tocca il bordo sinistro: il margine interno misurato è di 1,9 px.
- **Causa:**
  - `input.mono, .mono { font-family:var(--f-mono) }` (app.css:86) vale anche per `::placeholder`. Solo `input.cf::placeholder` (app.css:96) torna al carattere normale;
  - `input.cf { padding:4px calc(var(--l) / 2) }` (app.css:92).
- **Correzione minima:**
  ```css
  input.mono::placeholder { font-family:var(--f-ui); letter-spacing:normal; }
  input.cf { padding-inline:calc(var(--l) / 2 + 4px); width:calc(16 * var(--cella) + var(--l) + 10px); }
  ```
  La griglia delle caselle resta allineata perché usa `background-origin:content-box`.
- **Gravità:** media
- **Finestre:** Impostazioni › Strumenti e Studio, Vai al quadro, procedura guidata

### A15. Vai al quadro: campo da 4 caratteri largo 590 px
- **Schermate:** S55_vai_al_quadro_1440/1920
- **Problema visto:** la sigla («EC») si scrive in un campo largo quanto tutta la finestra (640 px), e la finestra è quasi vuota.
- **Causa:** `dialog { width:min(640px,94vw) }` (app.css:195) e `width:100%` (app.css:85).
- **Correzione minima:**
  ```css
  #dVai { width:min(420px,94vw); }
  #vaiSigla { width:8rem; text-transform:uppercase; }
  ```
- **Gravità:** bassa
- **Finestre:** Vai al quadro

### A16. Aspetto: 15 caselle su 7 righe con 48 px di passo
- **Schermate:** S42_impostazioni_aspetto_1440_p2/p3
- **Problema visto:** le sigle dei quadri (EA…EQ) stanno su due colonne da 340 px, con 16 px di spazio tra le righe. Il gruppo occupa 370 px in altezza per 15 etichette di 2 lettere.
- **Causa:** il gruppo riusa `.aspetto-griglia { grid-template-columns:repeat(2,…); gap:var(--s-4) }` (app.css:288).
- **Correzione minima:** stessa griglia, colonne più strette.
  ```css
  .aspetto-griglia[role=group] { grid-template-columns:repeat(auto-fill,minmax(5.5rem,1fr)); gap:var(--s-1) var(--s-3); }
  ```
- **Gravità:** bassa
- **Finestre:** Impostazioni › Aspetto

### A17. Procedura guidata, passo 2: la descrizione della scelta è grande come il titolo
- **Schermate:** S33, S34_wizard_2_*
- **Problema visto:** «Prima dichiarazione per questa successione.» ha la stessa dimensione del titolo «Dichiarazione originaria». È lo stesso difetto di A02 nella forma a pulsanti di scelta.
- **Causa:** `.radio` (app.css:203): la `.mut` interna eredita la dimensione piena.
- **Correzione minima:**
  ```css
  .radio .mut { font-size:var(--fs-m); margin-top:var(--s-05); }
  .radio { padding:var(--s-2) 0; }
  ```
- **Gravità:** bassa
- **Finestre:** Nuova dichiarazione, passo 2

### A18. Procedura guidata: l'errore resta dopo la correzione
- **Schermate:** S32_wizard_1_compilato_1440. Con il cognome già scritto si legge ancora «Indica almeno il cognome del defunto.».
- **Problema visto:** il messaggio rosso resta sotto i campi compilati e sembra ancora valido.
- **Causa:** comportamento, non CSS. `#wizErr` viene svuotato solo in `wizRender()` (app.js:2421).
- **Correzione minima:** in `f()` (app.js:2423), aggiungere `$("#wizErr").textContent = ""` all'`oninput` del cognome. Lo stile `.err` (app.css:81) va bene.
- **Gravità:** bassa
- **Finestre:** Nuova dichiarazione

### A19. Indice delle Impostazioni: «Strumenti e percorsi» va a capo
- **Schermate:** S46_impostazioni_strumenti_1440_p1–p3
- **Problema visto:** quando la voce è attiva e in grassetto va su due righe. La pillola verde diventa alta il doppio delle altre.
- **Causa:** `#imp .imp-corpo { grid-template-columns:180px … }` (app.css:275).
- **Correzione minima:**
  ```css
  #imp .imp-corpo { grid-template-columns:200px minmax(0,1fr); }
  ```
- **Gravità:** bassa
- **Finestre:** Impostazioni

### A20. Incolla righe: l'elenco delle colonne sembra un altro paragrafo
- **Schermate:** S57_operazione_incolla_da_excel_1440/1920
- **Problema visto:** «Codice fiscale · Ruolo nella successione · …» è in testo normale e nero, più evidente della spiegazione che lo introduce. Non si capisce che è l'intestazione da rispettare.
- **Causa:** il paragrafo ha classe `cod`, ma `.cod` esiste solo come `.ins .cod` (app.css:181), quindi nella finestra non ha stile.
- **Correzione minima:**
  ```css
  .dlg-op .cod { font-family:var(--f-mono); font-size:var(--fs-s); color:var(--t2); background:var(--grigio); border-radius:var(--r1); padding:var(--s-15) var(--s-2); }
  ```
- **Gravità:** bassa
- **Finestre:** Incolla righe

### A21. Modifica di gruppo: righe su due linee e campo quota troppo largo
- **Schermate:** modifica di gruppo sul quadro DV (cattura aggiuntiva)
- **Problema visto:**
  - nelle righe da modificare che vanno su due linee la casella si centra in verticale invece di stare sulla prima linea;
  - la quota («1/2») sta in un campo da 410 px.
- **Causa:** `.gruppo-righe .riga-sc { align-items:center }` (app.css:439); `width:100%` (app.css:85).
- **Correzione minima:**
  ```css
  .gruppo-righe .riga-sc { align-items:flex-start; }
  .gruppo-righe .riga-sc input { margin-top:.2em; }
  .dlg-op .rg[data-gruppo^=quota] input { width:8rem; }
  ```
- **Gravità:** bassa
- **Finestre:** Modifica di gruppo

### A22. Guida: campo di ricerca largo 830 px
- **Schermate:** S20_guida_istruzioni_1440_p1
- **Problema visto:** il campo «Cerca un argomento» è largo quanto la finestra, molto più di qualsiasi termine cercato.
- **Causa:** `.guida-corpo input[type=search]` (app.css:463) non ha larghezza propria.
- **Correzione minima:**
  ```css
  .guida-corpo input[type=search] { max-width:32rem; }
  ```
- **Gravità:** bassa
- **Finestre:** Guida

### A23. Schermi larghi: finestre di consultazione strette
- **Schermate:** S43_1920, S46_1920, S20_guida_info_1920_p1
- **Problema visto:** a 1920 px le Impostazioni restano larghe 920 px e la Guida 880 px. I percorsi sono tagliati nel campo, e i percorsi lunghi della Guida vanno a capo su 3 righe, mentre ai lati restano 500 px vuoti. Per i moduli brevi (procedura guidata, Vai al quadro) la larghezza attuale è giusta e non va toccata.
- **Causa:** `#imp { width:min(920px,96vw) }` (app.css:272), `dialog.guida { width:min(880px,96vw) }` (app.css:460).
- **Correzione minima:**
  ```css
  @media (min-width:1600px) { #imp { width:1040px; } dialog.guida { width:1040px; } }
  ```
- **Gravità:** bassa
- **Finestre:** Impostazioni, Guida

### A24. Distanza tra titolo e sottotitolo diversa da finestra a finestra
- **Schermate:** S40 (44 px tra titolo e sottotitolo), S10 (52 px), S30 (24 px), S90 (circa 30 px)
- **Problema visto:** il sottotitolo grigio sta vicino al titolo in una finestra e lontano in un'altra.
- **Causa:** `dialog h2 { margin:0 0 var(--s-2) }` (app.css:197) più il margine di serie del paragrafo (1em). In Impostazioni si aggiunge `#imp .imp-testa` (app.css:274).
- **Correzione minima:**
  ```css
  dialog h2 + p { margin-top:0; }
  #imp .imp-testa p { margin:0 0 var(--s-2); }
  ```
- **Gravità:** bassa
- **Finestre:** tutte

### A25. Diagnosi e Backup: pulsante a distanza variabile dal testo
- **Schermate:** S44_impostazioni_backup_1440, S45_impostazioni_diagnosi_1440
- **Problema visto:** «Crea backup ora» ed «Esegui diagnosi» stanno a 16 px dal paragrafo per il margine di serie di `<p>`. Dopo la diagnosi le voci del risultato hanno 6 px di stacco l'una dall'altra e la riga di rimedio ha lo stesso peso della voce.
- **Causa:** il margine di serie di `<p>`, `.diagnosi-voce { margin-bottom:var(--s-15) }` (app.css:292) e `.diagnosi-voce .mut { font-size:var(--fs-m) }` (app.css:292).
- **Correzione minima:**
  ```css
  #imp .imp-sezioni > section > p.mut { margin:0 0 var(--s-2); max-width:72ch; }
  .diagnosi-voce { margin-bottom:var(--s-3); }
  .diagnosi-voce .mut { font-size:var(--fs-s); margin-top:var(--s-05); }
  ```
- **Gravità:** bassa
- **Finestre:** Impostazioni › Backup e Diagnosi

---

## Cosa funziona già e va lasciato com'è

- Il piede delle finestre: azione secondaria a sinistra, primaria piena a destra, sempre attaccato in basso con il filo di separazione. Le finestre con il solo «Chiudi» (Guida, Scorciatoie) usano coerentemente il pulsante pieno a destra.
- Il passo 3 della procedura guidata (S35): casella da 8 px, filo tra le voci, ritmo regolare. È il modello per tutte le caselle.
- La calcolatrice: campo e pulsante sulla stessa riga («Circoscrizioni … [1]»), colonna dei risultati ancorata.
- La nota di avviso ocra (`.calc-avv`) e il riquadro dei valori calcolati.

---

## Schema comune della «riga di modulo» (proposta CSS)

Si appoggia solo su classi già esistenti (`.campo`, `.chk`, `.mut`, `.gh`) e su token esistenti. Si può aggiungere in coda ad app.css, limitato a `dialog`, così il pannello principale non cambia.
Unica classe in più, facoltativa: `.campo-riga`, se si sceglie la variante di A05.

```css
/* ---- Riga di modulo nelle finestre (revisione A, 9/11/2026) ---- */

/* 1. Voce: blocco con ritmo verticale fisso. 16 px tra voci, 4 px tra le parti interne. */
dialog .campo { margin:0 0 var(--s-4); }
dialog .campo:last-child { margin-bottom:0; }
dialog :is(.griglia, .aspetto-griglia) > .campo { margin-bottom:0; }   /* nelle griglie il ritmo lo dà il gap */
dialog .griglia { row-gap:var(--s-3); }

/* 2. Etichetta: inchiostro, peso 500, 4 px dal campo. */
dialog .campo > label:not(.chk) { display:block; color:var(--t); font-weight:500; font-size:var(--fs-m); margin-bottom:var(--s-1); }

/* 3. Controllo: larghezza secondo il dato, non secondo la finestra. */
dialog .campo > :is(input, select, textarea) { width:100%; }          /* testo libero, nomi, comuni */
dialog input[type=number],
dialog input.num                    { width:8rem;  text-align:right; font-variant-numeric:tabular-nums; }  /* numeri, ore, giorni, % */
dialog input[type=date],
#w_data_nascita, #w_data_decesso    { width:11.5rem; }                 /* date */
#w_provincia_nascita, #w_provincia_decesso { width:5rem; }             /* sigle di 2-4 caratteri */
dialog input.cf                     { /* larghezza propria, 16 caselle (app.css:92) */ }
dialog .calc-riga input.n           { text-align:right; }              /* importi */
dialog input.mono:not(.cf)          { width:100%; }                    /* percorsi: tutta la riga */
dialog input.mono::placeholder      { font-family:var(--f-ui); letter-spacing:normal; }
dialog select                       { max-width:28rem; }               /* scelte: non oltre il testo più lungo */

/* 4. Aiuto: un passo sotto, grigio, staccato dal campo, larghezza di lettura. */
dialog .campo > .mut { font-size:var(--fs-s); line-height:1.45; color:var(--t2); margin-top:var(--s-1); max-width:72ch; }
dialog .campo > .mut + .mut { margin-top:var(--s-05); }

/* 5. Casella con il suo aiuto: casella da 16 px sulla prima riga, testo a 8 px, aiuto rientrato sotto il testo. */
dialog input[type=checkbox], dialog input[type=radio] { width:1rem; height:1rem; flex:none; margin:.2em 0 0; accent-color:var(--blu); }
dialog .campo > label.chk { display:flex; align-items:flex-start; gap:var(--s-2); padding:0; border:0; color:var(--t); font-weight:400; font-size:var(--fs-base); }
dialog .campo > label.chk + .mut { margin-left:calc(1rem + var(--s-2)); }

/* 6. Pulsante legato a un campo: accanto (variante A05) o subito sotto, mai attaccato. */
dialog .campo-riga { display:flex; align-items:center; gap:var(--s-2); }
dialog .campo:has(+ button.gh) { margin-bottom:var(--s-15); }   /* i margini verticali si fondono: senza questa riga resterebbero 16 px */
dialog .campo + button.gh,
dialog p.mut + button.gh { margin:var(--s-15) 0 var(--s-4); }

/* 7. Sezioni e intestazioni: stessi stacchi in tutte le finestre. */
dialog h2 + p { margin-top:0; }
dialog section > h3 { margin:0 0 var(--s-3); }
```

Ritmo verticale risultante, uguale in tutte le finestre:

| Passaggio | Stacco |
|---|---|
| Etichetta → campo | 4 px |
| Campo → aiuto | 4 px |
| Aiuto → aiuto | 2 px |
| Voce → voce | 16 px |
| Titolo di sezione → prima voce | 12 px |
| Sezione → sezione | 12 + 16 px con filo (già oggi, app.css:280) |
| Campo → pulsante legato | 6 px sotto, oppure 8 px accanto |
