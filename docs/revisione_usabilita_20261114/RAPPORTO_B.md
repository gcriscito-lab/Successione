# Revisione B: inserimento dei dati nei quadri

Server di prova sulla porta 8832, solo dati sintetici («ROSSI MARIO», «Pratica appena aperta»). Viewport 1910x1000 e 1440x900.
Codice: `src/successioni/static/app.js` (righe citate come app.js:N) e `app.css`. Repository non modificato.

## 1. Sintesi

1. **La scheda della riga è lunga e stretta.** Con le impostazioni predefinite (normale, pannello a destra) il pannello è largo 360 px anche su uno schermo da 1910. La scheda di un fabbricato è alta 2.557 px, cioè 2,8 schermate da scorrere, mentre al centro restano vuoti circa 1.200x700 px. La combinazione compatta + sotto mostra la stessa scheda in 909 px, ma non è quella predefinita. Inoltre il ripiego a 440 px pensato per gli schermi larghi non scatta mai (è un errore).
2. **Inserire un bene costa molti clic, soprattutto per le devoluzioni.** Un fabbricato completo richiede 17 clic, più 10 clic per ogni erede a cui va il bene: bisogna passare al quadro DV e scegliere di nuovo bene e diritto. Con 2 eredi si arriva a circa 39 clic. Il riquadro «Devoluzioni del bene» dice «aggiungila nel quadro DV» ma non offre un pulsante.
3. **Ci sono testi fissi che si ripetono dappertutto.** La riga di aiuto sotto ogni tabella, la legenda «In grassetto i dati richiesti», la nota sull'immobile estero, le fonti normative del valore catastale (6 righe), l'id tecnico in fondo a ogni scheda, la nota «Comprende righe non ancora salvate». Nella scheda EC normale ci sono 1.534 caratteri di testo per 29 campi.
4. **Le sezioni ripiegate non restano chiuse.** «Altri dati (7)» nei fabbricati e nei terreni è sempre aperto, perché contiene «Tipo di bene», che è sempre compilato. Accanto c'è una seconda sezione chiamata quasi uguale, «Altri dati del bene». In «Dati generali» (2.882 px, 138 campi) i 5 campi di «Presentatore residente all'estero» sono sempre visibili, e l'anagrafica del presentatore ripete un erede già inserito in EA.
5. **Alcuni campi traggono in inganno e c'è linguaggio da programmatore.**
   - Le quote vuote mostrano «1/2» come se fosse un valore.
   - Il codice fiscale nella scheda EA è tagliato (si vede «RSSNNA70A41H»).
   - Le passività e le devoluzioni hanno come titolo l'id tecnico «ps_medic01».
   - La cronologia mostra «gui · utente 2026-11-14T13:31:45+00:00».
   - Il rilievo di una pratica nuova dice «serve esattamente un soggetto con ruolo 'defunto'».

## 2. Tabella dei rilievi

| # | schermata | cosa si vede (fatto) | perché disturba | proposta minima | priorità | screenshot |
|---|---|---|---|---|---|---|
| 1 | Pannello a destra, tutti i quadri | A 1910 px il pannello è largo 360 px. La scheda EC normale è alta 2.557 px (914 visibili), EB 2.263, EA 1.533. Al centro, sotto la tabella, resta vuoto circa il 70% dell'area. Il ripiego «440 px se lo schermo è ≥1680» non scatta mai, perché `ASPETTO_DEFAULT.larghezza_pannello` vale già 360 (app.js:66 e app.js:89) | Si scorre di continuo e lo spazio grande resta inutilizzato | Togliere `larghezza_pannello: 360` dai predefiniti (così vale 440 sugli schermi larghi), oppure proporre «compatta + sotto» come predefinito sui PC larghi: EC passa da 2.557 a 909 px | Alta | 02_EC.png, 04_pannello_EC_normale.png, 03_EC_compatta_sotto.png |
| 2 | Scheda EB/EC, «Altri dati (7)» | La sezione è sempre aperta, perché contiene «Tipo di bene» (sempre «Fabbricato») e la regola apre la sezione se un campo è pieno (app.js:933). Su una riga nuova aggiunge 7 campi e Invio ci passa attraverso (27 tappe) | La sezione ripiegata non ripiega mai | Non mostrare «tipo» nei quadri dove lo decide il quadro (EB, EC, EL, EM, EO, EN, EP, EQ). In alternativa escluderlo dal calcolo «pieno» a app.js:933 | Alta | 04_pannello_EC_normale.png, 13_EC_nuova_gruppi.png |
| 3 | Scheda dei beni | Due sezioni ripiegabili quasi omonime: «Altri dati (7)» (app.js:932) e «Altri dati del bene» (app.js:1541) | Non si capisce dove sia un dato | Rinominare la seconda, per esempio «Precedenti successioni, graffati, trascrizione e registrazione» | Media | 04_pannello_EC_normale.png |
| 4 | Campi quota (EC, EB, ER, EO, ED, DV) | Il segnaposto «1/2» (app.js:624) è scuro (rgb 85,97,95 contro 31,42,42 del testo vero) e allineato a destra come un valore | Sembra una quota già inserita: rischio di non compilarla, o di credere che il defunto ne avesse metà | Togliere il segnaposto, oppure scrivere «es. 1/1» in corsivo chiaro | Alta | 10_EO_nuova.png, 14_ED_scheda.png |
| 5 | Scheda EA (normale, a destra) | Il codice fiscale è affiancato al Sesso: il campo è largo 158 px e il testo ne richiede 210, quindi si vede solo «RSSNNA70A41H» | Il dato più importante dell'erede non si rilegge per intero | In EA mettere il codice fiscale su una riga intera (app.js:912, gruppo «coppie»), oppure ridurre la spaziatura delle lettere del campo `.cf` nel pannello | Alta | 03_EA_normale_destra.png, 06_EA_nuovo_erede.png |
| 6 | Devoluzioni (EB/EC → DV) | Per ogni erede bisogna: aprire DV (1 clic), Aggiungi riga (1), Bene (2), Erede (2), Diritto (2), Quota (1), Salva (1), cioè 10 clic. Nel bene il riquadro dice solo «aggiungila nel quadro DV» (app.js:1094) | È la parte più costosa dell'inserimento e obbliga a lasciare il bene | Mettere nel riquadro «Devoluzioni del bene» un pulsante «Aggiungi devoluzione» che crea la riga DV con bene e diritto del bene già compilati: restano erede e quota (circa 5 clic in meno per erede) | Alta | 04_pannello_EC_normale.png, 08_DV_nuova.png |
| 7 | Nuova riga DV | Il diritto parte vuoto anche se il bene ha già «1 — Proprietà» | 2 clic ripetuti per ogni erede | Ricopiare il diritto del bene appena si sceglie il bene (lasciandolo modificabile) | Media | 08_DV_nuova.png |
| 8 | Valore catastale, fabbricato nuovo | Il riquadro compare solo per le righe salvate (app.js:1491, `r.e`). Quindi: Salva, poi «Usa il valore catastale», poi Salva di nuovo | Salvataggio doppio e passaggio poco intuitivo | Mostrare il riquadro anche sulla riga nuova con la scritta «salva per calcolare», oppure calcolare al primo salvataggio e proporre subito «Usa» | Media | 07_EC_dopo_salva.png |
| 9 | Riquadro «Valore catastale calcolato» | Mostra formula più 6 righe di «Fonti: L. 662/1996 … D.Lgs. 141/2026 …». Le fonti sono nascoste solo con la densità compatta (app.css:576) | Testo normativo lungo nel punto in cui si lavora | Nascondere `.fonte-vc` in tutte le densità (le fonti restano già nel suggerimento, app.js:961) | Media | 04_pannello_EC_normale.png |
| 10 | Sotto ogni tabella | «Quote come 1/2, importi come 1.234,50. Per un dato non noto scrivi «?» …» (app.js:817), anche in EA dove non ci sono né quote né importi | Rumore ripetuto in tutti i quadri | Mostrarla solo a tabella vuota, oppure spostarla nel suggerimento di «Aggiungi riga» | Media | 02_EA.png, 02_EC.png |
| 11 | Testa della scheda | «In grassetto i dati richiesti dal quadro.» su ogni scheda di EA, EB ed EC (app.js:1416) | Una riga fissa che si impara una volta | Toglierla (il grassetto si spiega da sé) o metterla nel suggerimento del titolo | Bassa | 04_pannello_EA_normale.png |
| 12 | Scheda EB/EC | Sempre presente: «Per un immobile all'estero scegli la provincia EE: compaiono i campi dello Stato estero.» (app.js:1487) | Caso raro, testo fisso | Spostarlo nel suggerimento («?») della Provincia | Bassa | 04_pannello_EC_normale.png |
| 13 | Piede della scheda | Id tecnico «b_casa0001» / «ps_medic01» sotto Salva (app.js:1507) | Dato da programmatore | Toglierlo, oppure metterlo nel suggerimento del titolo | Bassa | 14_ED_scheda.png |
| 14 | Scheda ED e DV | Il titolo della scheda è «ps_medic01». `etichetta()` restituisce l'id per passività, devoluzioni e documenti (app.js:274). Lo stesso id compare nella conferma «Elimina la riga selezionata» del menu Operazioni (app.js:1005) | Il professionista non sa quale riga sta modificando o eliminando | In `etichetta()`: passività → descrizione e importo; devoluzioni → «erede — bene» (come in `descriviRigaGruppo`, app.js:1278) | Alta | 14_ED_scheda.png |
| 15 | Dati generali (AN) | Pagina di 2.882 px con 138 campi. Nella sezione 3 i 5 campi «Presentatore residente all'estero: …» sono sempre aperti (app.js:2114) | Occupano 3 righe di griglia per un caso raro | Metterli in un `details` chiuso, «Residenza estera del presentatore», come già fatto per testamento e crediti | Media | 12_AN_intero.png |
| 16 | AN, «Anagrafica del presentatore» | Se il presentatore è «Rossi Anna · Erede» si ripetono 8 campi già presenti in EA (CF, cognome, nome, …), modificabili anche qui (app.js:2116) | Stesso dato in due posti; si rischia di modificarlo senza accorgersene | Se il presentatore è un soggetto di EA, mostrare una riga sola («Dati anagrafici nel quadro EA — Vai») e la scheda completa solo per un presentatore distinto | Media | 12_AN_intero.png |
| 17 | AN, pulsanti di salvataggio | Ci sono «Salva» nella barra alta, «Salva dati generali» in fondo (app.js:2148) e due «Salva dati della dichiarazione» dentro «Prima casa» e «Riduzioni» (app.js:2070, 2098). Fanno tutti la stessa cosa | Fanno pensare che ogni sezione si salvi a parte | Tenere solo «Salva» in alto (con Ctrl+S) e togliere i pulsanti interni | Bassa | 12_AN_intero.png |
| 18 | Barra laterale | 19 voci, di cui 7 non selezionate (EI, EL, EM, EN, EO, EP, EQ). A 1000 px DV e i riepiloghi richiedono lo scorrimento (1.276 px su 914). In fondo c'è «Versione 0.4.0. Accesso solo da questo computer. PDF/A: Ghostscript presente, veraPDF presente» (app.js:279). AN mostra «1 riga» | DV, che si usa spesso, è fuori vista; il resto è rumore | Raggruppare i quadri non selezionati in un «Altri quadri (7)» ripiegabile; spostare le informazioni di versione in Guida; per AN non mostrare «1 riga» (app.js:568) | Media | 02_EA.png, 03_EA_normale_destra.png |
| 19 | Linguetta Cronologia | «Revisione 1 · gui · utente», «2026-11-14T13:31:45+00:00» (ora UTC in formato ISO, app.js:1649) | Linguaggio tecnico e ora sbagliata di un'ora per l'Italia | Formato «14/11/2026 14:31» in ora locale; togliere canale e autore (o lasciarli nel suggerimento) | Media | 09_EC_cronologia.png |
| 20 | Linguetta Controlli | Prima riga «controlli interni di forma e coerenza; NON è il controllo ufficiale. Non finalizzabile.» più un riquadro sul file XML non generato. Le stesse cose sono già nella barra di stato («Non finalizzabile: …», «Controllo ufficiale: vedi File e invio»). Ogni rilievo mostra anche codice e percorso tecnico (app.js:1627) | Messaggi ripetuti e dettagli da programmatore | Una sola riga breve in testa; codice e percorso nel suggerimento invece che a vista | Bassa | 09_EC_controlli.png |
| 21 | Messaggio del rilievo (pratica nuova) | «serve esattamente un soggetto con ruolo 'defunto'» | Lessico interno («soggetto con ruolo») | «Manca il defunto: compila i suoi dati in Dati generali» | Bassa | 05_nuova_AN.png |
| 22 | Impostazioni > Aspetto | «Compatta (schede con etichette a sinistra, aiuto quando entri nel campo)» (app.js:2550). Dal 10/11 l'aiuto non compare più entrando nel campo (app.css:919). «Ampia» dà nel pannello misure identiche a «Normale» (EA 1.533 px in entrambe) | Descrizione non più vera; una scelta che non cambia nulla nella scheda | Correggere in «Compatta (etichette a sinistra, schede più corte)»; valutare se tenere «Ampia» | Bassa | 16_impostazioni_aspetto.png |
| 23 | Pannello sotto | Altezza fissa di 380 px anche quando la tabella ha 1 riga e sopra restano circa 300 px vuoti | Si scorre dentro il pannello pur avendo spazio libero | Con poche righe dare al pannello l'altezza disponibile (tabella ridotta al contenuto) | Bassa | 03_EC_compatta_sotto.png |
| 24 | Scheda EO, ED, ER, DV (normale) | Etichette a sinistra su 2-3 righe («Tipo di documento (azienda)»), mentre EA, EB ed EC hanno le etichette sopra e i gruppi. In EO il primo campo è «Tipo di bene: Titolo», già deciso dal quadro | Scheda lunga e disomogenea; un campo inutile in testa | Nascondere «tipo» in EO (vedi #2); per gli altri quadri usare la stessa impaginazione a gruppi | Bassa | 10_EO_nuova.png, 14_ER_scheda.png |
| 25 | Formati nella scheda | Tabella «126.000» e «1.000,00», scheda «126000» e «1000,00» | Rilettura più difficile (separatore delle migliaia) | Mostrare gli importi nella scheda con il punto delle migliaia (la lettura accetta già «1.234,50») | Bassa | 02_EC.png |
| 26 | Proposta codice comune | «calcolato dal nome: H501 (ROMA, RM) Usa» compila il codice, ma la Provincia resta «(non indicato)» | Un clic e un menu in più | Con «Usa» compilare anche la provincia, se è vuota | Bassa | 02_EC.png |
| 27 | Intestazione del quadro | Sotto il titolo il menu «stato: nessuno» su ogni quadro, e «0 righe» anche mentre si compila una riga nuova (app.js:720) | Piccolo rumore; conteggio fuorviante | Mostrare il menu dello stato più discreto; contare anche le righe nuove («1 riga, da salvare») | Bassa | 06_EA_nuovo_erede.png |

### Conteggio dei clic (mouse; il testo digitato non è contato)

- **Erede completo**: 8 clic.
  - Quadro EA (1), Aggiungi riga (1), cognome (1), nome (1), codice fiscale (1), grado (2), Salva (1).
  - Il ruolo «Erede» è già proposto; sesso, data, comune e provincia di nascita si compilano dal codice fiscale.
  - Per ogni bene ricevuto servono altri 10 clic nel quadro DV.
- **Fabbricato completo**: 17 clic.
  - Quadro EC (1), Aggiungi riga (1), Provincia (2), Comune (1), «Usa» codice comune (1), Foglio, Particella e Sub (3), Categoria (2), Classe, Consistenza e Rendita (3), Diritto (2), Quota (1), Salva (1).
  - Il valore catastale aggiunge «Usa» e un secondo Salva (+2).
  - Ogni erede aggiunge 10 clic in DV.
  - Totale con 2 eredi: circa 39 clic. Con le proposte #6 e #7: circa 29.
- **Da tastiera**: Alt+N e poi Invio passa da un campo al successivo (buono). In EC però le tappe sono 27, perché «Altri dati» resta aperto (#2).

### Spazio dei testi rispetto ai campi (pannello, densità normale, a destra)

| quadro | campi | caratteri di testo visibili | altezza contenuto / visibile |
|---|---|---|---|
| EC | 29 | 1.534 | 2.557 / 914 px |
| EB | 27 | 911 | 2.263 / 914 |
| EA | 28 | 1.057 | 1.533 / 914 |
| ER | 11 | 464 | 1.062 / 914 |
| ED | 9 | 220 | 914 / 914 |
| DV | 7 | 193 | 914 / 914 |

Con la densità compatta e il pannello sotto, EC scende a 909 px (2,4 volte più corta) e i caratteri a 986. Tra «normale» e «ampia» il pannello non cambia.

## 3. Errori funzionali

1. **Id tecnico come titolo della riga (ED, DV, EG).**
   - Passi: ROSSI MARIO > ED > clic su «Spese mediche ultimi sei mesi».
   - Il titolo della scheda è «ps_medic01». Da Operazioni > «Elimina la riga selezionata» la conferma dice «Eliminare dal quadro ED la riga «ps_medic01»?».
   - Causa: `etichetta()` a app.js:271-275.
2. **Larghezza del pannello sugli schermi larghi.**
   - Il codice prevede 440 px a ≥1680 px (app.js:89), ma il predefinito 360 (app.js:66) vince sempre: a 1910 il pannello è largo 360 px.
3. **Codice fiscale tagliato nella scheda EA.**
   - Densità normale, pannello a destra: il campo è largo 158 px e il testo ne richiede 210, quindi non si legge per intero. Vale sia a 1910 sia a 1440.
4. **Descrizione superata nelle Impostazioni.**
   - «aiuto quando entri nel campo» per la densità compatta: la regola CSS a app.css:919 nasconde l'aiuto sempre.
5. **«Altri dati (7)» non si chiude mai** nei quadri dei beni, perché «Tipo di bene» è sempre valorizzato (app.js:933).
6. **«0 righe» nell'intestazione** mentre si compila una riga nuova non ancora salvata (EA, EO).
7. **Valore catastale non disponibile sulla riga nuova:** il riquadro compare solo dopo il primo salvataggio.
8. **Ora della cronologia in UTC** e in formato ISO (alle 14:31 italiane mostra 13:31).
9. **Dato non ripreso dal codice fiscale (da approfondire).** Nella pratica «ROSSI MARIO» il sesso del defunto e quello di Rossi Anna sono vuoti, anche se il codice fiscale è presente. La compilazione dal codice fiscale scatta solo modificandolo.

Nessun errore JavaScript in console durante le prove.

## 4. Cose che vanno bene e non vanno toccate

- Compilazione dal codice fiscale: data, comune, provincia e sesso si riempiono da soli, con un messaggio chiaro e la richiesta di verificarli.
- Proposta del codice comune con «Usa»: il programma propone, non scrive da solo.
- Riquadro «Devoluzioni del bene» con la somma delle quote per diritto («1/1 · completa»).
- Ruolo «Erede» già proposto nella riga nuova; un quadro non selezionato si seleziona da solo al salvataggio, con il messaggio.
- Scheda a gruppi (Identificazione, Classamento, Diritto e valore) in compatta + sotto: è la vista più efficiente, con tutto un fabbricato in una schermata.
- Invio per passare al campo successivo; Alt+N; menu Operazioni con i comandi propri del quadro.
- Avvisi raggruppati per tipo con «Vai al dato» e «Come risolvere».
- Il quadro con una sola riga si apre già selezionato; il pannello resta chiuso finché non si sceglie una riga.
- Riga dei totali nelle tabelle (ED: «Totale (2 righe) 32.000»).

## 5. Cosa non ho potuto verificare

- Tema scuro, contrasto alto, dimensioni del carattere diverse da 16 px.
- Incolla da Excel, Modifica di gruppo, Brogliaccio, Ricalcola valori catastali su più righe.
- Quadri tavolari EL/EM, EN, EP, EQ (solo aperti, non compilati).
- Lettore di schermo; flusso completo solo da tastiera (provata solo la sequenza Alt+N / Invio).
- Valore catastale su un fabbricato nuovo: nella «Pratica appena aperta» manca la data del decesso, quindi il calcolo dice «Non calcolato».
- Trascinamento dei separatori per ridimensionare i pannelli.
