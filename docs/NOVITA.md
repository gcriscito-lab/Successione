Novità del programma (le più recenti in alto)

In preparazione — versione 0.3: densità e velocità di inserimento (da provare su una pratica reale)
Si attivano dalle Impostazioni: chi non le sceglie vede il programma come prima. Nessuna regola di calcolo nuova.
- Pannello della riga sotto la tabella, a tutta larghezza (Impostazioni > Pannello della riga selezionata > Sotto la
  tabella): la barra che lo separa dalla tabella si trascina o si regola con Freccia su e Freccia giù e la misura resta.
- Scheda compatta (Impostazioni > Densità > Compatta): etichette a sinistra su una riga, campi affiancati, gruppi in
  colonne; l'aiuto di un campo compare quando ci entri (un «?» accanto all'etichetta lo segnala). A 1366×768, con pannello
  sotto e scheda compatta, un fabbricato passa da 2.400 a 750 pixel di altezza: 23 campi su 28 visibili senza scorrere
  (prima 10); un erede da 1.420 a 590 pixel, tutti i campi visibili.
- Immobili in una tabella sola: linguette «Tutti gli immobili / Fabbricati / Terreni / tavolari» sopra i quadri EB, EC,
  EL, EM, con la sigla del quadro in prima colonna e il totale complessivo. Il file telematico non cambia.
- Tastiera: Alt+1 … Alt+9 portano alle voci dell'elenco dei quadri (l'indicazione è nel suggerimento di ogni voce); nella
  scheda Invio passa al campo successivo e, dopo l'ultimo, al pulsante Salva.

8 novembre 2026 — versione 0.2.0
Nessuna regola di calcolo nuova: imposte, quote e file telematico restano quelli delle regole 2026-11-07.
- Valori calcolati dal programma riconoscibili: tinta propria e scritta «calcolato» per il valore catastale proposto, i quadri
  EE, EF, EH e le somme delle quote. Il professionista vede a colpo d'occhio cosa ha scritto e cosa propone il programma.
- Codice comune ricavato dal nome nella scheda di fabbricati e terreni, con il pulsante «Usa» (mai scritto da solo). Con più
  comuni dello stesso nome chiede la provincia; se esistono omonimi soppressi invita a controllare la visura. Serve il
  componente ufficiale SUC13 configurato. Anche per Claude (strumento codice_comune, sola lettura).
- Trascinamento dei file: documenti del quadro EG, esiti del controllo eseguito a mano (.dgn, _logSchema.xml, .wri nel campo
  giusto), file .esi e ricevute. Il file va nel campo; il caricamento resta al pulsante.
- Tabelle vuote con l'indicazione di cosa fare; titoli dei gruppi della scheda come barra leggera, alla dimensione del testo.
- Devoluzioni raggruppate per bene, con la somma delle quote sotto ogni bene e il diritto per nome («Proprietà» invece di «1»).
- Eredi (EA): cognome, nome, parentela e ruolo prima del codice fiscale; segno «dichiarante» sulla riga del presentatore e,
  nella scheda, il riepilogo dei beni ricevuti con le quote.
- Controlli: ogni rilievo e avviso ha «Come risolvere» (quadro e comando da usare) e «Vai al dato». Nuovi avvisi di qualità,
  che non bloccano: spazi doppi, codice fiscale duplicato, errato o diverso da sesso e data di nascita, nascita dopo il
  decesso, provincia diversa da quella del codice comune.
- Scheda del bene: le devoluzioni del bene con la somma delle quote per diritto (completa, manca, supera 1/1).
- Menu Operazioni: modifica di gruppo di beni e devoluzioni (una sola revisione, annullabile dalla Cronologia), incolla righe
  da Excel, brogliaccio dei beni e delle quote da stampare o in CSV (anche per Claude: strumento brogliaccio).
- Appunti per riga e stato di lavorazione del quadro (da completare, da controllare, completato): note interne, non entrano
  nella dichiarazione.
- Pagina iniziale: tutte le pratiche con ricerca, filtri per termine (in scadenza, superato, senza data) e ordine per
  scadenza; «Prossime azioni» con le cinque tappe; calcolatrice rapida delle imposte senza creare una pratica.
- Correzioni: in «Dati generali» non resta più una colonna vuota a destra; ricerca, filtro e ordinamento della pagina
  iniziale su una riga; il titolo lungo di un quadro non va più a capo.

7 novembre 2026 (sera) — correzioni dalla seconda revisione completa
- Usufrutto e nuda proprietà con la devoluzione per legge: il file non si genera più (il controllo ufficiale lo scartava).
- Controllo eseguito a mano: un rapporto .dgn di un altro file non vale più come «passato».
- Invio: non si prepara una nuova copia mentre un tentativo d'invio è in corso; si vede sempre la copia attiva; il file
  dell'esito (.esi) si registra anche dall'interfaccia.
- Claude in sola lettura, profilo dello studio e «visura bloccante» valgono anche per Claude Desktop.
- Archivio: a programma fermo la cartella dati non resta bloccata e i dati stanno tutti nel file principale; le operazioni
  lunghe (PDF/A, controllo, backup) non bloccano più l'interfaccia; «archivio occupato» invece di un errore generico.
- Interfaccia: la modifica di gruppo non svuota più i campi per sbaglio; il tasto Invio e Ctrl+S non chiudono né salvano con
  una finestra aperta; Prossime azioni mostra prima le pratiche urgenti, anche se ferme, con il motivo che blocca il file.
- Importazione dei file .suc: avviso se il valore quota del file è diverso da quello ricalcolato, se l'ordine degli eredi
  cambia e se una descrizione contiene spazi ripetuti (la riesportazione li riduce a uno).
- Valore catastale: la prima casa che nasce dal diritto di abitazione del coniuge (codici 1, 2, 5, 6) usa il moltiplicatore 110.
- Separazione con colpa: il coniuge resta bloccato solo se compare fra i beneficiari delle quote e mai con la legge estera
  (prima bastava che fosse nel quadro EA).
- Allegati: eliminazione, riordino e PDF/A sicuri anche con interfaccia e Claude al lavoro insieme; il collegamento di un rigo
  EG accetta solo allegati della stessa pratica.
- Guida della prima pratica reale completata con i passi Prepara, Conferma, Istruzioni per l'invio ed esito.

7 novembre 2026 — regole 2026-11-07
- Guida in linea con le istruzioni ufficiali aperte alla pagina del quadro e finestra Informazioni con le versioni.
- Diritto di abitazione del coniuge (casella codici 1-8 nel quadro EC, prima casa estesa agli altri beneficiari).
- Quadro EO: agevolazione D sui titoli, titoli esteri senza codice fiscale dell'emittente, valore esente dei fondi.
- Quadro EF: somme dei valori quota con centesimi arrotondate all'euro (come accetta il controllo ufficiale).
- Albero genealogico (rigo EG6) generato dai dati del quadro EA, in PDF/A.
- Importazione dei file .suc: sostitutive, quote decimali, righi in ordine diverso, agevolazioni, vecchio quadro EI.
- Usufrutto e nuda proprietà nelle devoluzioni con i coefficienti per età.
- Valore catastale proposto per fabbricati e terreni, con avviso se il valore dichiarato è inferiore.
- Nuova impaginazione: valore sempre visibile, totali, scheda dell'immobile a gruppi, menu Operazioni, scorciatoie.
- Correzioni: doppio clic, due finestre aperte insieme, messaggi con programma chiuso, prova di invio separata
  dall'invio vero, controllo interrotto, sola lettura di Claude con impostazioni non valide, allegati e backup.

6 novembre 2026
- Attestazione di avvenuta presentazione (copia conforme), quadri EE, EF, EH visibili, quadro EG senza doppioni.
- Confronto con il compilatore ufficiale SuccessioniOnLine 2.3.1: imposte uguali sul caso di prova.
