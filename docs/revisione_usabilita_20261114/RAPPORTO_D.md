# Revisione D: il percorso completo di una pratica nuova (dati sintetici)

Ho compilato una pratica nuova dall'inizio, usando solo clic e tastiera. Dati: defunto, coniuge e figlio, 1 fabbricato con devoluzioni, 1 terreno, 1 conto corrente, 1 passività, documenti EG, poi liquidazione e File e invio.
**Il file non è stato generato.** L'ultimo blocco chiede l'IBAN di addebito, che non ho inserito per regola (niente coordinate bancarie, neanche finte). Fino a lì: **116 clic, 102 campi, 33 tasti (circa 250 operazioni) e 4 giri «Genera → errore → correggo»**.
Il passo per passo è in `DIARIO.md`; gli screenshot sono in questa cartella.

## 1. Sintesi (5 righe)
1. **I controlli dicono «tutto bene» mentre il file è bloccato.** «Controlla», la scheda Controlli e il riquadro «Stato della dichiarazione» mostrano «0 rilievi · 0 avvisi». I 9 veri blocchi stanno solo nella pagina del quadro EF.
2. **Gli errori arrivano a rate.** Prima il fornitore, poi 9 blocchi, poi le dichiarazioni prima casa, poi l'IBAN. Ogni giro si scopre solo premendo «Genera file» e leggendo un messaggio rosso temporaneo.
3. **Linguaggio da programmatore nei messaggi**: «<CodiceComuneAmministrativo>», «chiavi: altra_casa, dichiara_requisiti…», «Fonti: docs/regole/prima_casa.md», identificativi come «d_38484fce3c3c» come titolo del pannello.
4. **Dati che il programma conosce ma lascia scrivere a mano**: codice catastale (solo proposto, con un clic in più), codice del comune amministrativo, provincia del decesso, codice carica 1, valore dalla rendita, ripartizione per legge (24 operazioni per dividere tutto 1/2 e 1/2).
5. **Pannello di destra troppo stretto** su uno schermo largo (330-360 px): CF tagliato ed etichette troncate, mentre la tabella ha spazio in avanzo.

## 2. I 10 punti di maggiore attrito
| # | Schermata | Cosa si vede (fatto) | Perché disturba | Proposta minima | Priorità | Screenshot |
|---|---|---|---|---|---|---|
| 1 | File e invio / Controlla / scheda Controlli | Riquadro «Dati: **senza rilievi** · 0 rilievi · 0 avvisi» e «Nessun rilievo sui dati inseriti», con 9 blocchi aperti (devoluzioni mancanti, codici comune, passività oltre il limite, EG5, EG6) | Il professionista crede di aver finito; «Controlla» sembra non fare nulla | In «Stato della dichiarazione» far contare e mostrare anche i blocchi del file (gli stessi di EF) come «N punti da sistemare». Far aprire a «Controlla» lo stesso elenco. `static/app.js:1671` (riga «Dati»), `static/app.js:1625` | Alta | 38_controlla, 39_file_invio_1, 42_EF |
| 2 | Quadro EF «Da sistemare prima di generare il file» | Elenco in testo semplice, senza «Vai al dato»; «dato obbligatorio per <CodiceComuneAmministrativo>» tre volte senza dire quale bene | Non si capisce dove andare. È l'unico punto con l'elenco completo, ma sta in un quadro «calcolato dal programma» che nessuno apre | Aggiungere «Vai al dato» a ogni voce (il meccanismo esiste già nella scheda Controlli, `app.js:1619`). Tradurre i nomi XML con le etichette del campo e il bene (`telematico/esporta.py:198`). Mostrare lo stesso elenco in File e invio, passo 2 | Alta | 42_EF |
| 3 | File e invio, «Genera file» | L'errore è un messaggio rosso in basso, temporaneo e lungo, con i punti separati da «|». Resta aperto anche dopo aver cambiato quadro | Si legge male e non si può tornarci | Mostrare l'esito sotto il pulsante «Genera file», in un riquadro fisso con elenco puntato e «Vai al dato». Evidenziare il campo «Codice fiscale del fornitore» quando manca | Alta | 40, 41, 55_EC_1440 |
| 4 | Errori «a rate» | Dopo aver corretto 9 punti ne compare uno nuovo (prima casa), poi un altro (IBAN) | Quattro giri di genera e correggi; frustrazione | Calcolare e mostrare subito tutti i blocchi noti, anche quelli che nascono da altri blocchi, quando si può. Almeno scrivere «dopo questi potrebbero comparire altri controlli sul pagamento» | Alta | 42, 48, 50 |
| 5 | Messaggi tecnici | «(chiavi: altra_casa, dichiara_requisiti, impegno_unione_catastale…)», «Fonti: docs/regole/prima_casa.md», «serve esattamente un soggetto con ruolo 'defunto'», «L'allegato 'al_albero' non esiste (eliminato o identificativo errato)» | Linguaggio del programmatore, non del professionista | Sostituire con «compila le 5 dichiarazioni prima casa in Dati generali → Agevolazione prima casa» e un link. Togliere «Fonti: …». `telematico/prima_casa.py:208`, `telematico/riduzioni_art25.py:266`, `static/app.js:2049` e `2079`, `schema.py:386`, `servizio.py:320` | Media | 48, 49, 01_home |
| 6 | Pannello laterale (EA, EC, DV, EG) | Titolo del pannello = identificativo interno («d_38484fce3c3c», «dr_6923a74f7d7b»), ripetuto in fondo; campo «Allegato: al_377959277a43» | Rumore senza significato | Per DV usare «Fabbricato NAPOLI… → ESPOSITO LUCIA» (la funzione c'è già, `app.js:1281`); per EG usare il nome del file. Nascondere la riga con l'identificativo in fondo. `static/app.js:1413` | Media | 31_DV_due_righe, 46 |
| 7 | EC/EB, codici comune | Il codice catastale viene proposto in un riquadro con il pulsante «Usa» (non visibile se si va avanti con il Tab); il codice del comune amministrativo va scritto a mano e poi diventa un blocco | Lo stesso dato chiesto 2-3 volte (nome, codice, codice amministrativo) | Se il codice è vuoto e il comune è trovato, scriverlo direttamente (il «Usa» resta per i casi diversi). Copiare lo stesso codice nel codice amministrativo se vuoto. `static/app.js:1180-1195` | Alta | 22_EC_comune, 55_EC_1440 |
| 8 | DV Devoluzioni | Per «per legge, tutto metà al coniuge e metà al figlio» servono 6 righe × 4 scelte | Lavoro ripetitivo per il caso più comune | Nel menu Operazioni aggiungere «Applica le stesse quote a tutti i beni» (copia le righe del primo bene sugli altri). Togliere il defunto dall'elenco «Erede o legatario» | Media | 43_DV_completa |
| 9 | Pannello laterale stretto | A 1910 px il pannello è largo circa 330 px e a 1440 px 360 px; il CF si vede per 154 px su 210 («SPSLCU50H60F»); etichette troncate | Non si rilegge il CF, cioè il dato più importante | Larghezza iniziale del pannello circa 480-520 px sugli schermi oltre 1600 px, oppure CF senza spaziatura tra le lettere nel pannello. La larghezza è già regolabile (`salvaLarghezza`, `app.js:2693`): cambiare solo il valore predefinito | Media | 15_EA_coniuge_cf, 55_EC_1440 |
| 10 | Salvataggio con Ctrl+S | Con il cursore ancora nel campo: «Salvato (revisione N)», ma il pulsante resta «Salva (1)», la barra dice «1 modifica non salvata» e alla ricarica compare «Abbandonare il sito?». Il dato è salvato | Messaggi contraddittori; il professionista non si fida del salvataggio | Prima di salvare, chiudere il campo attivo (blur) oppure, dopo il salvataggio, togliere dalle modifiche i valori uguali a quelli salvati. `static/app.js:2781` e `salvaTutto` `app.js:2370` | Alta (vedi §3) | 20_AN_fondo |

### Altri rilievi (minori)
| # | Schermata | Fatto | Proposta minima | Priorità | Screenshot |
|---|---|---|---|---|---|
| 11 | Procedura guidata | Data di nascita scritta «1945-03-15» dopo la compilazione dal CF; il segnaposto «RM» nelle province sembra un valore; la provincia del decesso non si compila dal comune; il messaggio cita «Sesso», campo che lì non c'è | Scrivere la data GG/MM/AAAA; togliere il segnaposto «RM»; compilare la provincia del decesso. `static/app.js:2472` | Bassa | 03, 04 |
| 12 | Procedura guidata, passo 2 «Tipo» | Una schermata intera per «originaria» (quasi sempre) | Mettere la scelta nel passo 4 «Conferma», come elenco già impostato. `app.js:2464` | Bassa | 05_tipo |
| 13 | EA | «Ruolo nella successione = Erede» più «Tipo di soggetto = 1 Erede» | Impostare il tipo 1 da solo quando il ruolo è Erede (e 2 per Legatario) | Media | 15 |
| 14 | Dati generali | Il codice carica resta «non indicato» anche se il presentatore scelto è un erede | Proporre 1 quando la persona è erede | Media | 19 |
| 15 | EC | Il valore non si calcola dalla rendita; la Calcolatrice è un altro strumento e chiede di nuovo eredi e beni | Mostrare sotto «Valore» un riquadro «calcolato: rendita × coefficiente × quota = …» con «Usa», come per il codice comune | Media | 23, 25 |
| 16 | Dati generali | 5 campi «Presentatore residente all'estero» sempre aperti; tre pulsanti di salvataggio diversi | Chiuderli in un riquadro «Residente all'estero» come «Testamento»; lasciare un solo pulsante (Salva in alto) | Bassa | 10, 11 |
| 17 | File e invio | «File XML: **aggiornato**» (verde) accanto a «Nessun file generato»; «Il profilo si compila una volta per questa pratica», anche se esiste il profilo di studio predefinito in Impostazioni | Con nessun file mostrare «non generato»; testo: «proposto dal profilo dello studio (Impostazioni)». `app.js:1672`, `app.js:1680` | Media | 41 |
| 18 | File e invio | «Genera bozza tecnica» si blocca per lo stesso IBAN | Se la bozza serve a vedere il file con i suoi limiti, non bloccarla per i dati del pagamento | Media | 52 |
| 19 | EG | Per qualche secondo «Da completare: Converti in PDF/A» mentre la conversione è già in corso; doppio ingresso (pulsante «Aggiungi riga» e riquadro «Aggiungi un documento») | Mostrare «conversione in corso…» senza pulsante; togliere «Aggiungi riga» in EG | Bassa | 46, 47 |
| 20 | EH | Domande per lo stato civile 5 e 7 anche con stato civile 2; «Conformità delle copie» c'è sia in Dati generali sia in EH | Nascondere le domande che non c'entrano con lo stato civile scelto | Bassa | 54 |
| 21 | Scheda Controlli | Ripete il riquadro arancione «il file XML completo non è stato generato…» (già nella barra in basso) e mostra «Nessun rilievo» subito sotto un «Avviso» | Togliere il riquadro ripetuto; con avvisi presenti scrivere «Nessun errore» invece di «Nessun rilievo». `app.js:1625` | Bassa | 18, 26 |
| 22 | EA dopo il Tab dal CF | Il cursore si perde: nessun campo resta attivo | Rimettere il cursore sul campo successivo dopo la compilazione dal CF | Bassa | 15 |

## 3. Errori funzionali trovati
1. **Lo stato «non salvato» resta acceso dopo Ctrl+S.** Passi: Dati generali → scrivere nel campo Telefono → senza uscire dal campo premere Ctrl+S → compare «Salvato (revisione N)», ma il pulsante resta «Salva (1)» e la barra mostra «1 modifica non salvata». Ricaricando la pagina il browser chiede di abbandonare, eppure il dato risulta salvato.
2. **«Stato della dichiarazione» dice «senza rilievi / 0 rilievi · 0 avvisi» mentre «Genera file» rifiuta con 9 blocchi** (EF li elenca). Anche «File XML: aggiornato» in verde accanto a «Nessun file generato».
3. **«Controlla» non ha effetto visibile** con blocchi aperti (resta «Nessun rilievo»).
4. **I blocchi compaiono a rate**: «prima casa (Sezione II EH)» compare solo dopo aver corretto i primi 9; l'IBAN solo dopo la prima casa.
5. **Il blocco IBAN resta anche con «Tempistica 1 — pagamento non contestuale»**. Da verificare se è corretto per le regole; per l'utente è inatteso.
6. **La bozza tecnica non si genera** per lo stesso motivo (IBAN), anche se è presentata come file «con evidenza dei limiti».
7. L'elenco «Erede o legatario» in DV e la «Persona collegata» in ED **comprendono il defunto**.
8. Data di nascita in formato ISO («1945-03-15») nella procedura guidata dopo la compilazione dal CF.
9. Il messaggio rosso dell'IBAN resta a schermo anche dopo aver cambiato quadro.
10. Una richiesta al server è stata rifiutata (422) durante il percorso. Probabilmente è il «Genera file» rifiutato, ma non ho verificato quale.

## 4. Cose che vanno BENE (da non toccare)
- La compilazione dal codice fiscale (nascita, comune, provincia, sesso) nella procedura guidata e in EA, con la nota «Verifica i dati».
- Il pulsante **«Vai al dato»** nella scheda Controlli: porta esattamente nel campo (data della visura).
- La riga «calcolato · Somma delle quote … 1/1 · completa» in DV: chiarissima.
- Alt+D per duplicare la riga e Alt+N, con il cursore che va subito su Cognome.
- La generazione dell'albero genealogico dai dati e la conversione PDF/A automatica dell'allegato.
- I quadri proposti nella procedura guidata già giusti; la barra laterale con lo stato di ogni quadro («2 righe», «da compilare»).
- I suggerimenti al passaggio del mouse sulle etichette (es. «Valore: della QUOTA DEL DEFUNTO…»), che non tolgono spazio ai campi.
- File e invio organizzato in 5 passi numerati con la spunta «fatto».

## 5. Cosa non ho potuto verificare
- **Generazione del file, controllo ufficiale, stampa del modello, prepara invio**: bloccati dall'IBAN, che non ho inserito per regola. Per chiudere il percorso serve un IBAN di prova accettato dal professionista, oppure un caso senza imposte da versare.
- La correttezza degli importi (774 euro da versare) e se l'IBAN sia davvero obbligatorio con la tempistica 1.
- Una pausa anomala di circa 10 minuti in un passo di DV (riempimento di 2 righe + Alt+D + Ctrl+S). Rifatto più volte dopo, ogni riga richiedeva circa 1,5 secondi: non riprodotta, forse dovuta all'ambiente di prova.
- L'agevolazione prima casa impostata sulla riga DV (codice P): l'ho fatta scattare solo da EC.
- Il trascinamento dei file nel riquadro EG (ho usato «Scegli file»).
