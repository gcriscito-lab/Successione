# Revisione grafica del 9/11/2026: elenco unico delle correzioni

Fonti, tutte nella cartella `docs/` del repository:
- **CSS**: analisi del codice, in `REVISIONE_GRAFICA_20261109_css.md`;
- **A**: finestre e moduli, in `A_finestre_e_moduli.md`;
- **B**: pagina iniziale e quadri, in `B_home_e_quadri.md`;
- **C**: leggibilità e temi, con contrasti misurati, in `C_leggibilita_e_temi.md`.

Le misure sono state prese con Playwright sull'istanza di prova 127.0.0.1:8833, con dati sintetici. Le 411 schermate del «prima» sono nella cartella temporanea della sessione di coordinamento.

Ogni rilievo indica il selettore con il numero di riga e la correzione minima. Qui sotto c'è solo l'ordine di applicazione e le decisioni prese nei punti in cui le fonti divergono.

**Vincolo del professionista:** niente stravolgimenti. Restano uguali la struttura, le sezioni, la posizione delle cose e i testi. Si toccano solo allineamenti, spazi, larghezze, gerarchia dei testi, contrasto e coerenza.

## Decisioni sulle divergenze

1. **Modello di riga del modulo.** Si usa quello dell'analisi CSS: `.modulo > .campo`, con `.campo.casella`, `.in-linea`, `.aiuto` e i token `--l-*`. Nella regola si integrano le misure di A (schema finale di A_finestre).
   - Peso dell'etichetta: **500**, non 600. Così resta un gradino sotto i titoli di sezione, che sono a 700 (ui-ux-pro-max, `weight-hierarchy`).
   - Campo numerico: **8rem** invece di 7rem, per lasciare spazio alle frecce del campo `number`.
   - Data **11rem**, sigla di provincia **5rem**, codice fiscale con la sua larghezza a 16 caselle, percorsi a riga intera.
   - Il ritmo è 4 / 4 / 16 px (etichetta → campo → aiuto → voce successiva). Il pulsante legato al campo sta a 8 px di lato.
2. **«Pulisci ora».** Va **sulla stessa riga** del campo delle ore, con `.in-linea`. È la variante consigliata sia da A05 sia dall'analisi CSS. La posizione nella pagina resta la stessa.
3. **Errori.** C'è una sola classe, `.err`; `.e` diventa un sinonimo (CSS, punto 8).
4. **`width:100%` generale (app.css:85).** Resta. I limiti di larghezza valgono solo dentro `.modulo` e nei casi elencati nel lotto 3.
5. **B03 e B06.** Toccano gli stessi blocchi di EH: si applica prima B06, poi si controlla se B03 serve ancora per EH.

## Lotti, in ordine

### Lotto 1: difetti che sembrano errori (prima di tutto)
- **B01 = C01.** La barra «Dati / Controlli / Cronologia» è trasparente e il testo le scorre sotto; a 1440 è anche tagliata di 4 px. Va resa opaca con `top` corretto e `.ins { scroll-padding-top:3.5rem }`. Riguarda anche il focus coperto (WCAG 2.4.11).
- **B05.** La riga nuova vuota compare come una striscia di 12 px. Correzione: `tbody td:empty::before{content:"\00a0"}`.
- **A13.** La pillola «info» è rossa come un errore (app.js:2976) e deve diventare neutra.
- **A18.** L'errore della procedura guidata resta visibile dopo la correzione (app.js:2423).

### Lotto 2: riga di modulo comune in tutte le finestre (la segnalazione del professionista)
- Applicare il modello (decisione 1) a: Impostazioni (tutte le sezioni), Nuova dichiarazione, finestre `dialogo()` / `.dlg-op`, Preventivo, Calcolatrice, Vai al quadro, Guida.
- Questo copre:
  - **CSS** 1–9;
  - **A** 01, 02, 03, 04, 05, 12, 14, 17, 19, 24, 25;
  - **C** 05, 07.
- Nello stesso lotto, le larghezze dentro le finestre: **A** 07, 09, 11, 15, 21, 22 e **A06**, cioè «svuota il campo» in colonna 2.
- **A20.** L'elenco delle colonne di Incolla righe va in stile codice.
- **A16.** Le 15 caselle dei quadri proposti vanno in una griglia più stretta.
- **A10 = C09.** Nelle Tabelle della Guida si toglie il taglio con i puntini e `var(--bd)` diventa `var(--sep)`.
- Il codice HTML delle sezioni non si tocca: in JS cambiano solo le classi.

### Lotto 3: campi larghi quanto la scheda nelle schermate della pratica
- **B02.** Dati generali: date, provincia, sesso, relazione, tendine.
- **B12.** Acconto e rate allineati a destra; consistenza EC a destra.
- **B18.** File e invio: colonna delle etichette di stato e tendina del fornitore.
- **B04.** Etichette della scheda riga su una riga sola, come nella vista compatta.
- **B03.** Etichette di 150 px nelle sezioni facoltative di AN (per EH vale la decisione 5).

### Lotto 4: coerenza fra schede e quadri
- **B06.** Stessa larghezza (44rem) per i tre blocchi di EE, EF ed EH.
- **B07.** Elenchi puntati dentro il riquadro.
- **B08.** Un solo stile per i titoli di scheda.
- **B10.** Niente doppio bordo per la scheda dentro la scheda in AN.
- **B11.** Nota sotto «Aggiungi riga» ed aiuti di EG a `--fs-s`.
- **B16.** I titoli di gruppo nella scheda DV hanno lo stesso aspetto di `.gruppo-scheda > h4`.
- **B13.** Spazio dopo le colonne numeriche e «Quota» allineata in EB, EC ed ER: va aggiunta la classe `n` in app.js.
- **B23.** Intestazioni delle tabelle dei quadri a `--fs-m` in `--t`, densità invariata.
- **B09.** Sezioni facoltative chiuse meno distanziate.
- **B14.** Menu Operazioni: la scorciatoia non si deve stirare.
- **B15.** Con la disposizione «sotto», il pannello va allineato al quadro.

### Lotto 5: leggibilità (solo valori dei token)
- **C02.** `::placeholder { color:var(--t2); opacity:1 }`. Nel tema scuro oggi il contrasto è 3,83:1.
- **C03.** Numero del chip attivo: `color-mix` dal 22% al 12%.
- **C04.** Soglie minime: `--fs-s:max(.857rem,12px)` e `--fs-m:max(.929rem,13px)`.
- **C06.** Opacità dei pulsanti disabilitati a .6.
- **C08.** Alfa di `--sep-f` per tema: chiaro .60, scuro .48, seppia .72.
- **C10.** Barra di stato a `--fs-m`.
- **C11.** `.lat { scroll-padding-block:var(--s-2) }`.

### Lotto 6: rifiniture minori e schermi larghi (il programma si usa solo da PC)
- **A08.** Nella procedura guidata l'alto della finestra resta fermo e «Avanti» non salta.
- **A23.** Impostazioni e Guida larghe 1040 px oltre i 1600 px.
- **B17.** Pannello predefinito di 440 px oltre i 1680 px, solo se l'utente non ha scelto una larghezza.
- **B21.** Pagina iniziale fino a 100rem oltre i 1800 px.
- **B19.** Stato «nessuna pratica» in un riquadro.
- **B20.** Chip alti quanto i campi.
- **B22.** Pulsante del selettore di file con lo stile dei pulsanti `.gh`.
- **B25.** Maniglia di ridimensionamento più tenue e voci «non selezionato» più basse.
- **B24.** Decimali coerenti nel prospetto EF (app.js:698) e numeri a destra nel brogliaccio (brogliaccio.py:155–161).

## Verifica (per ogni lotto)
- Nuova prova e2e `gui_moduli.js`, come proposta nell'analisi CSS, a 1440×900 e 1920×1080. Si aggiungono questi controlli:
  - con B01, la barra delle linguette è opaca;
  - con B05, l'altezza di una riga vuota è almeno quella di una riga piena;
  - con A04 e B02, i campi numerici e le date non superano la loro larghezza;
  - con C02, il contrasto dei segnaposto nel tema scuro è almeno 4,5.
- Suite e2e completa (`tests/e2e/esegui_tutti.py`), `tests/test_design_system.py` e pytest.
- Schermate «prima e dopo» almeno di:
  - S43 Impostazioni › Operatività;
  - S30 procedura guidata;
  - S51 AN;
  - S51 EC con una riga aperta;
  - S51 EF;
  - S01 home;
  - S106 EC nel tema scuro.

  Così il professionista vede l'effetto prima del commit finale.
