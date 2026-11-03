# Interfaccia aggiornata

- **Impostazioni → Aspetto e leggibilità:** tema automatico, chiaro, scuro o seppia; sei famiglie di caratteri; dimensioni da 12 a 22 px; spaziatura compatta, normale o ampia. Anteprima immediata, Salva per conservare, Chiudi per annullare l'anteprima. I percorsi degli strumenti rimangono nella sezione espandibile dedicata.
- **File e invio:** pagina unica per pratica, dalla barra principale o dal menu a sinistra. Fornitore, impegno, generazione, controlli e ricevute non sono più ripetuti nell'ispettore di ogni quadro. Le modifiche al fornitore restano nel buffer passando tra quadri e si salvano con Salva o Ctrl+S.
- **Pannello dati:** trascinare il separatore alla sua sinistra. Da tastiera usare frecce sinistra/destra, Home o End. La larghezza si conserva alla riapertura ed è adattata allo spazio disponibile; sugli schermi stretti i pannelli si dispongono in verticale.
- **Dati generali:** defunto; successione e devoluzione; presentatore e contatti; pagamento; firme e documenti. Testamento, prima casa, aziende e selezione dei quadri hanno sezioni espandibili. Comune e provincia sono affiancati; le province sono presenti anche nella creazione guidata e nella tabella dei soggetti.
- **Pagina iniziale:** logo vettoriale Successioni e accessi per creare/importare una pratica. Il logo nella barra superiore riporta alla pagina iniziale, con avviso se ci sono modifiche non salvate.

Le preferenze sono salvate nella sezione `interfaccia` del file di configurazione esistente; i percorsi degli strumenti e le altre impostazioni vengono conservati. Nessuna modifica alle regole fiscali o ai documenti originali.

Verifiche: 98 test Python pertinenti passati; Chromium su aspetto/persistenza/tema automatico, trascinamento, tastiera, province e creazione guidata, schermata stretta, salvataggi durante HTTP, conflitti, cronologia e generazione XML completa con profilo intermediario sintetico. Screenshot di verifica in `build/aspetto_*.png`. Nessun invio reale. Riavviare il programma aggiornato per caricare il nuovo codice dell'interfaccia.
