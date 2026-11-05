# Manuale breve

Stato: **beta tecnica**. Non è utilizzabile su una pratica reale e non trasmette nulla all'Agenzia delle Entrate.
Ogni comando qui sotto è stato verificato con `successioni --help`.

## Avvio
- `successioni gui` apre l'interfaccia nel browser, su un indirizzo locale con un codice (token) personale. Opzioni: `--porta`, `--no-browser`.
- `successioni mcp` avvia il collegamento per l'assistente Claude (vedi `docs/CONFIGURAZIONE_MCP.md`).

## Dove sono i dati
Nella cartella indicata dalla variabile `SUCCESSIONI_DATA`. Per provare il programma usa una cartella separata con **dati inventati**, mai dati reali dello studio.

## Lavorare nell'interfaccia
- Procedura guidata per una nuova pratica; i quadri (EA, EB, EC…) sono nella colonna a sinistra.
- Al centro la tabella dei dati, a destra l'ispettore con tre schede: *Dati*, *Controlli*, *Cronologia*.
- In basso la barra di stato: revisione, salvataggio, rilievi, stato del controllo ufficiale.
- Ogni modifica crea una nuova revisione. Se due persone (o l'assistente e tu) modificano la stessa pratica, la seconda modifica viene respinta con un conflitto e va riapplicata sulla revisione aggiornata.
- Le parole d'esito: **simulazione** (solo logica, dati inventati), **controllo locale** (componenti ufficiali eseguiti sul tuo PC), **verifica ufficiale** (servizi dell'Agenzia: non ancora disponibile).

## Allegati e PDF/A
- `successioni converti-pdfa` converte un PDF in PDF/A-1b e riporta l'esito. Serve Ghostscript.
- Senza veraPDF l'esito è sempre «non verificato», mai «conforme». Con Ghostscript 10.08.0 e veraPDF 1.30.3 (profilo PDF/A-1b) installati e configurati (`SUCCESSIONI_GS`, `SUCCESSIONI_VERAPDF`, `SUCCESSIONI_ICC`) il collaudo sul corpus sintetico passa; non è la verifica ufficiale (servizio CIVIS dell'Agenzia).
- Gli allegati oltre 5 MB si possono suddividere dalla scheda File.

## Invio (prova simulata)
Nella scheda File, sezione «Invio»:
1. **Prepara invio**: congela il file XML completo con il controllo ufficiale locale positivo (servono entrambi).
2. Controlla impronta, file e fornitore, spunta la verifica e **Conferma questa copia**. La conferma si dà solo nell'app, mai dall'assistente.
3. **Invia in PROVA (simulata)**: usa un servizio fittizio locale. Non trasmette nulla all'Agenzia delle Entrate e serve solo a provare il percorso (anche rete interrotta e riconciliazione).
4. **Istruzioni per l'invio reale**: il programma non trasmette. Invia il file con Desktop Telematico / Entratel (credenziali nello strumento ufficiale) e registra poi l'esito con la riconciliazione.
Un file non si invia due volte: dopo un tentativo, anche incerto, si riconcilia invece di reinviare. Se cambi i dati della pratica, la copia diventa obsoleta.

## Backup e ripristino
- `successioni backup <cartella>` copia database e allegati.
- `successioni ripristina <backup> --destinazione <cartella nuova>` ripristina solo in una cartella nuova: non sovrascrive mai dati esistenti.

## Cosa il programma NON fa
- Non invia nulla all'Agenzia e non usa credenziali: l'invio nell'app è una prova simulata, quello reale si fa con gli strumenti ufficiali.
- Quadri non coperti: EI, EL, EM, EN, EO, EP, EQ, agevolazioni e riduzioni, rinunce, rappresentanti di legatari, testamento estero. Testamento con eredi e legatari persone fisiche: supportato (controllo locale su dati sintetici). Selezionarli blocca la finalizzazione.
- La dichiarazione sostitutiva è gestita per i codici 1 e 2 (indica estremi della prima dichiarazione, con volume 88888 o 88889, e le imposte già versate); il codice 3 (solo documentazione) non è supportato. Restano esclusi rimborsi, tardive con imposta aggiuntiva e sanzioni.
- I dati strutturati hanno una maschera nell'interfaccia: superficie, ripartizione, estremi di trascrizione/registrazione nell'ispettore del bene o della passività; dati della dichiarazione (stato civile, presentatore, versamento, testamento) e «Agevolazione prima casa (Sezione II del quadro EH)» nel frontespizio; codice P/X/Z nell'ispettore della riga di devoluzione (scheda DV); tipo di titolo, con «esente» (valore in ValoreEsente), nell'ispettore del quadro EO. Gli aiuti e i valori ammessi stanno in `schema.STRUTTURATI` e riportano solo le fonti di `docs/regole/prima_casa.md` e dell'XSD. Resta solo da MCP o API la rateazione (`pagamento_rateale`, non supportata).
- Stampa del modello ministeriale: disponibile (pulsante «Stampa modello ministeriale» nella vista File) se Java e il componente di controllo sono configurati; è una prova locale con il codice di stampa dell'Agenzia, da controllare prima di usarla. Gli allegati EG compaiono come flag, non come pagine.
- Nessun esito locale autorizza l'uso su una pratica reale.

Fonti: `docs/BETA_DA_REVISIONARE.md`, `docs/RISPOSTA_ALLA_REVISIONE.md`, `docs/COLLAUDO_WINDOWS_CODEX_20261102.md`.

## Compilazione dal codice fiscale
Scrivendo un codice fiscale di persona fisica (16 caratteri) nella procedura guidata, nelle schede del defunto e del presentatore o nella riga di un erede, il programma compila **solo i campi ancora vuoti**: data di nascita, sesso, comune e provincia di nascita (il comune dalle tabelle del componente di controllo SUC13, se configurato; altrimenti resta il codice catastale e un avviso). Il secolo non è nel codice fiscale: viene dedotto e, se ambiguo, segnalato. È un suggerimento: verifica sempre i dati. Un carattere di controllo errato viene segnalato senza bloccare. Anche l'assistente può usarlo: strumento `successioni_decodifica_codice_fiscale`.

## Riprendere una successione da un file XML

Il pulsante **Importa XML** crea una nuova pratica da un file telematico SUC13 (`.xml`, `.suc` in formato XML), per esempio uno esportato da questo programma. Si importano frontespizio, eredi (EA), terreni (EB), fabbricati (EC), passività (ED) e disponibilità finanziarie (ER). Gli altri quadri sono elencati nel messaggio finale come da reinserire; EE ed EF si ricalcolano. Gli allegati (EG) vanno riacquisiti. I dati letti vanno verificati: l'importazione non è un controllo ufficiale.

I file `.diz` del compilatore ministeriale **non** sono importabili: contengono oggetti dell'interfaccia del compilatore e serve un campione sintetico prodotto dal compilatore per scrivere un lettore affidabile.

## Impostazioni

Il pulsante **Impostazioni** mostra i percorsi degli strumenti esterni e se sono stati trovati: Java e cartella del controllo SUC13 (per il controllo ufficiale locale), Ghostscript, veraPDF, qpdf e profilo colore (per i PDF/A), cartella delle fonti e tempo massimo del controllo. Per la cartella del controllo si vede quanti JAR richiesti mancano.

Il salvataggio è tutto o niente: se un percorso non esiste non si scrive nulla. Il valore vale subito e viene scritto nel file di configurazione indicato in cima alla finestra, lo stesso letto all'avvio dal lanciatore (una variabile d'ambiente esterna con lo stesso nome prevale sul file). Lasciando vuoto un campo l'impostazione si rimuove. La cartella dei dati si vede ma si cambia solo con la variabile `SUCCESSIONI_DATA`, per non nascondere le pratiche esistenti. Qui non si salvano password, certificati né credenziali.
