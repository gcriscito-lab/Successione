# Diario del percorso completo (area D)

Pratica sintetica «Successione BIANCHI GIORGIO» (CF calcolati a mano con il carattere di controllo corretto; verificato sul CF di prova RSSMRA40A01H501K dei test).
Defunto BNCGRG45C15F839P (Napoli, 15/03/1945, morto il 20/02/2026), coniuge ESPOSITO LUCIA SPSLCU50H60F839E, figlio BIANCHI MARCO BNCMRC75R10F839Q.
Beni: fabbricato Napoli fg.10 p.200 sub.5 A/2 (rendita 800, quota 1/2), terreno Napoli fg.5 p.33 (RD 50, 1/1), conto corrente (1/2, 10.000), passività spese funerarie.
Schermo 1910x1000 (verifica a 1440x900 su EC). Solo clic e tastiera via Playwright. Contatori del driver: un clic per ogni clic o scelta da elenco, un campo per ogni campo scritto o scelto.

Nota: il percorso è stato interrotto a metà (limite d'uso). Il server era stato fermato e la pratica era persa, quindi l'ho ricreata con gli stessi passi. I contatori qui sotto sono quelli della seconda passata, che comprende anche la ricreazione.

| # | Schermata | Azione | Esito / osservazione | Schermata |
|---|---|---|---|---|
| 1 | Elenco pratiche | apertura | La colonna «Prossima azione» usa testi tecnici: «Serve esattamente un soggetto con ruolo 'defunto'», «L'allegato 'al_albero' non esiste (eliminato o identificativo errato)». Il percorso dell'archivio compare due volte (in pagina e nella barra in basso). | 01_home |
| 2 | Procedura guidata 1/4 | clic su «Nuova dichiarazione» | Cognome, Nome, Codice fiscale | 02_nuova |
| 3 | idem | scrivo cognome, Tab, nome, Tab, CF, Tab | Nascita, comune e provincia si compilano dal CF (bene). **La data di nascita compare come «1945-03-15»** (formato ISO) mentre il segnaposto dice GG/MM/AAAA. Il messaggio dice «Compilato ...Sesso», ma qui il campo Sesso non c'è. | 03_cf_defunto |
| 4 | idem | data del decesso, comune del decesso NAPOLI, Tab | **La provincia del decesso non si compila** (resta il segnaposto «RM», che sembra un valore già scritto). La scrivo io. | 04_comune_decesso |
| 5 | Procedura guidata 2/4 «Tipo» | Avanti | Una schermata intera per una scelta che resta quasi sempre «originaria» | 05_tipo |
| 6 | Procedura guidata 3/4 «Quadri» | Avanti | Quadri proposti già giusti (bene) | 06_quadri |
| 7 | Procedura guidata 4/4 | «Crea dichiarazione» | 7 clic e 6 campi in tutto | 07_conferma |
| 8 | Dati generali | stato civile, devoluzione per legge sì, testamento no | Schermata lunga; 5 campi «Presentatore residente all'estero» sempre aperti; tre pulsanti di salvataggio (Salva in alto, «Salva dati generali», «Salva dati della dichiarazione» nella sezione prima casa). | 08, 10, 11, 12 |
| 9 | idem | **dubbio:** il presentatore va scelto «tra i soggetti», ma gli eredi non esistono ancora. Rimando la scelta. | | |
| 10 | EA | «Aggiungi riga» | Il pannello laterale è largo 330-360 px su uno schermo da 1910 px; le etichette sono tagliate («Rappresentato: codice ...»). Il contatore resta su «0 righe» anche con una riga presente. | 14_EA_riga |
| 11 | EA | coniuge: cognome, nome, CF, Tab | I dati si compilano dal CF (bene). **Il CF nel pannello non si legge per intero** («SPSLCU50H60F»: 154 px visibili su 210). **Dopo il Tab il cursore si perde** (nessun campo attivo). | 15_EA_coniuge_cf |
| 12 | EA | Tipo di soggetto 1 e Grado 01 | **«Ruolo nella successione = Erede» e «Tipo di soggetto = 1 Erede» chiedono la stessa cosa due volte.** | |
| 13 | EA | Aggiungi riga (il cursore va su Cognome, bene), figlio, Ctrl+S | | 16, 17 |
| 14 | EA, scheda Controlli | | Il riquadro arancione «il file XML completo non è stato generato...» è lo stesso avviso della barra in basso | 18_EA_controlli |
| 15 | Dati generali | presentatore = ESPOSITO LUCIA | **Il codice carica non diventa 1 da solo**, anche se la persona è erede. Lo scelgo io. Telefono, email, firme, Ctrl+S. | 19, 20 |
| 16 | idem | Ctrl+S con il cursore ancora nel campo appena scritto | **ERRORE:** compare «Salvato (revisione N)», ma il pulsante resta «Salva (1)» e la barra mostra «1 modifica non salvata». Ricaricando, il browser chiede «Abbandonare il sito?». Il dato invece è salvato (verificato dopo la ricarica). | 20_AN_fondo |
| 17 | EC | Aggiungi riga, provincia, comune NAPOLI, Tab | Il codice catastale viene proposto in un riquadro con il pulsante «Usa», sotto il campo. Il Tab porta altrove, quindi da tastiera non lo vedi e resta vuoto. Il codice del comune amministrativo non viene proposto. | 21, 22 |
| 18 | EC | dati catastali, diritto, quota 1/2, abitazione del coniuge = P | **Il valore non si calcola dalla rendita** (rendita × 1,05 × 110 × quota). Lo calcolo a mano: 46.200. | 23 |
| 19 | | **dubbio:** provo la Calcolatrice per il valore | Si apre una calcolatrice separata che chiede di nuovo eredi e immobili (dati già inseriti). La chiudo. | 25_calcolatrice |
| 20 | EC, Controlli | | Lo stesso riquadro mostra un avviso (data della visura) e subito sotto «Nessun rilievo sui dati inseriti.». «Vai al dato» porta nel campo giusto (ottimo). | 26, 27 |
| 21 | DV | Aggiungi riga | **Il titolo del pannello è un identificativo interno** («d_38484fce3c3c»), ripetuto in fondo. **L'elenco «Erede o legatario» contiene anche il defunto.** Non esiste una ripartizione automatica «per legge». | 30, 31 |
| 22 | DV | 2 righe per il fabbricato (Alt+D duplica, bene) | La somma delle quote «1/1 · completa» è chiara (bene) | 31 |
| 23 | EB, ER, ED | terreno, conto corrente, spese funerarie 1.500 | Il terreno vuole codice comune e codice del comune amministrativo (lo stesso dato due volte). | 32-37 |
| 24 | barra in alto | «Controlla» | **Non succede nulla di visibile:** «Nessun rilievo», nessun elenco. Eppure terreno e conto non hanno ancora devoluzioni, EG è vuoto e la passività supera il limite. | 38_controlla |
| 25 | File e invio | apertura | **«Dati: senza rilievi · 0 rilievi · 0 avvisi».** La pagina usa circa il 60% della larghezza. | 39 |
| 26 | idem | Genera file | Il messaggio rosso compare in basso, lontano dal campo e solo per qualche secondo: «manca il codice fiscale del fornitore...». Il campo non viene evidenziato. | 40 |
| 27 | idem | CF fornitore, Salva profilo, Genera file | Nuovo messaggio rosso con 3 blocchi (EG6, EG5, EF). Nel riquadro di stato restano «Dati senza rilievi» e «File XML: **aggiornato**» (verde) accanto a «Nessun file generato». | 41 |
| 28 | EF | **qui non sapevo cosa fare:** apro EF per capire | L'elenco **completo** dei 9 blocchi si trova solo qui, come testo semplice senza «Vai al dato»: «dato obbligatorio per <CodiceComuneAmministrativo>» (tre volte, senza dire quale bene), «la sezione devoluzione deve essere compilata», «spese funerarie: importo massimo 1033», «la passività va attribuita a soggetti del quadro EA»... | 42_EF |
| 29 | EC, EB | aggiungo i codici comune F839 | | |
| 30 | DV | altre 4 righe (terreno e conto × 2 eredi) | 6 righe × 4 scelte = 24 operazioni per una divisione 1/2 e 1/2 di tutto | 43 |
| 31 | ED | persona collegata, importo 1.033 | | |
| 32 | EG | «Genera albero genealogico dai dati», carico il PDF della fattura su EG5 | Bene. Nel pannello compaiono di nuovo identificativi interni («dr_6923a74f7d7b», «Allegato: al_377959277a43»). Per qualche secondo compare «Da completare: Converti in PDF/A» mentre la conversione automatica è già in corso: se clicchi, il pulsante sparisce. Ci sono due modi per aggiungere (il pulsante «Aggiungi riga» e il riquadro «Aggiungi un documento»). | 44-47 |
| 33 | EF | ricontrollo | **Compare un nuovo blocco mai mostrato prima:** «...indicare le dichiarazioni della Sezione II del quadro EH (chiavi: altra_casa, dichiara_requisiti, ...)». Lo ha attivato la scelta «abitazione del coniuge = P» in EC. | 48 |
| 34 | Dati generali, sezione «Agevolazione prima casa» | 5 scelte | Il testo dice «Fonti: docs/regole/prima_casa.md» (un file interno) e indica DV come punto in cui si imposta P, ma qui P è venuto da EC. | 49 |
| 35 | EF | ricontrollo | **Terzo giro, nuovo blocco:** «totale da versare 774: indicare IBAN e codice fiscale del titolare». Resta anche con tempistica 1 (pagamento non contestuale). | 50, 51 |
| 36 | File e invio | Genera file / Genera bozza tecnica | **Anche la bozza tecnica si blocca per l'IBAN.** Non ho inserito l'IBAN: le regole di sicurezza vietano di scrivere coordinate bancarie, anche finte. **Percorso fermo qui:** file non generato, controllo ufficiale e stampa disattivati. | 52 |
| 37 | EE, EH | | EE: «Nessun totale calcolabile». EH mostra domande per lo stato civile 5 e 7 anche con stato civile 2. | 53, 54 |
| 38 | EC a 1440x900 | | Pannello di 360 px, tabella di 780 px; il messaggio rosso dell'IBAN resta a schermo anche dopo aver cambiato quadro | 55_EC_1440 |

## Totali (seconda passata, compresa la ricreazione della pratica)
- Clic: **116**. Campi scritti o scelti: **102**. Tasti speciali (Tab, Ctrl+S, Alt+D): **33**. Totale circa **250 operazioni**, file non ancora generato.
- Le prove diagnostiche (Ctrl+S nel campo, ricarica, Calcolatrice) valgono circa 10 operazioni.
- Giri «Genera / leggo l'errore / correggo»: **4** (fornitore, poi 9 blocchi, poi prima casa, poi IBAN).
- Dati chiesti due volte: ruolo e tipo di soggetto; codice comune e codice del comune amministrativo; nome del comune e codice catastale; CF del presentatore e CF del fornitore (quando presenta il dichiarante); calcolatrice e pratica; «conformità delle copie» in Dati generali ed EH (sincronizzati, ma in due punti).
- Messaggi che interrompono: «Leave site?» falso alla ricarica (punto 16); messaggi rossi temporanei in basso (punti 26, 27, 38).
