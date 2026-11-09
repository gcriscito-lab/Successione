Novità del programma (le più recenti in alto)

8 novembre 2026 — versione 0.4.0
Contiene le versioni 0.3 e 0.4 e le correzioni della revisione completa dell'8 novembre. Imposte e file telematico non
cambiano. Cambiano due cose: il valore catastale proposto per alcune categorie di lusso (vedi sotto) e la citazione delle norme
nelle tabelle.

Strumenti di studio
- Anteprima interna: modello ministeriale, prospetti, brogliaccio, albero genealogico, istruzioni ufficiali, fascicolo e
  preventivo si aprono in una finestra del programma, con «Stampa» e «Apri in una nuova scheda».
- Fascicolo per il cliente (File e invio > Strumenti di studio): un solo PDF con copertina e indice, il modello stampato, i
  documenti del quadro EG nell'ordine dei righi (le immagini TIFF convertite) e le ricevute in PDF, con un segnalibro per
  documento. Ciò che manca è elencato in copertina con il motivo.
- Guida > Tabelle e fonti: aliquote e franchigie dell'imposta di successione, imposte ipotecaria e catastale, tasse e bolli,
  moltiplicatori catastali e coefficienti dell'usufrutto, ognuna con la fonte e le successioni a cui si applica. I valori sono
  letti dai moduli di calcolo: sono quelli che il programma applica davvero. Anche per Claude (strumento tabelle_calcolo).
- Copia anonima: crea una nuova pratica con nomi, codici fiscali, indirizzi, riferimenti catastali e contatti di fantasia, senza
  allegati né note; date, importi e quote restano per ripetere i calcoli. La pratica di partenza non cambia.
- Preventivo e parcella: voci, contributo cassa, IVA e ritenuta li scrivi tu (vuoti = 0), il programma fa solo le somme; si
  possono aggiungere a parte le imposte dell'ultimo file generato. Si salva nelle note interne. Non è una fattura.
- Pagina iniziale: «Elenco in CSV» scarica tutte le pratiche con termine, avanzamento e prossima azione, per Excel.

Densità e velocità di inserimento
Si attivano dalle Impostazioni: chi non le sceglie vede il programma come prima.
- Pannello della riga sotto la tabella, a tutta larghezza (Impostazioni > Pannello della riga selezionata > Sotto la
  tabella): la barra che lo separa dalla tabella si trascina o si regola con Freccia su e Freccia giù e la misura resta.
- Scheda compatta (Impostazioni > Densità > Compatta): etichette a sinistra su una riga, campi affiancati, gruppi in
  colonne; l'aiuto di un campo compare quando ci entri (un «?» accanto all'etichetta lo segnala). A 1366×768, con pannello
  sotto e scheda compatta, un fabbricato passa da 2.400 a 750 pixel di altezza: 23 campi su 28 visibili senza scorrere
  (prima 10); un erede da 1.420 a 590 pixel, tutti i campi visibili.
- Immobili in una tabella sola: linguette «Tutti gli immobili / Fabbricati / Terreni / tavolari» sopra i quadri EB, EC,
  EL, EM, con la sigla del quadro in prima colonna e il totale complessivo. Il file telematico non cambia.
- Pagina iniziale più chiara: un solo elenco delle pratiche, ordinato per urgenza, con termine, avanzamento in cinque tappe e
  prossima cosa da fare (cliccabile); in alto un riepilogo in una riga e filtri a pulsanti con i conteggi (da lavorare, in
  scadenza, termine superato, senza data, completate), ricerca e ordine. Prima le stesse pratiche comparivano tre volte e la
  scadenza era detta in due modi; ora la colonna dei quadri e i comandi della pratica compaiono solo aprendo una pratica.
- Tastiera: Alt+1 … Alt+9 portano alle voci dell'elenco dei quadri (l'indicazione è nel suggerimento di ogni voce); nella
  scheda Invio passa al campo successivo e, dopo l'ultimo, al pulsante Salva.
- Aspetto più uniforme (design system): spazi e arrotondamenti da una sola scala, bordi dei campi ben visibili (contrasto 3:1).

Correzioni dalla revisione completa dell'8 novembre
- Valore catastale proposto: le abitazioni di lusso (A/1, A/8, A/9) e i castelli (A/11) usano il moltiplicatore ordinario
  (120) anche con la prima casa, come già il calcolo della prima casa; prima il programma proponeva 110.
- Tabelle e fonti: per usufrutto e moltiplicatori si cita prima la norma in vigore al decesso, cioè il D.Lgs. 346/1990 come
  modificato dal D.Lgs. 139/2024 (con l'art. 52 del DPR 131/1986); i testi unici successivi restano come conferma.
- Copia anonima più completa: anche notaio, enti, estremi di atti e registrazioni, provenienze e nomi scritti dentro i testi
  diventano di fantasia.
- Pagina iniziale: le ricevute si leggono dalla copia trasmessa; pagamento negativo, volture parziali o negative ed esiti
  contraddittori tengono aperta la pratica, con la tappa «problema»; oltre le prime 12 pratiche niente più «Genera il file»
  quando il file non si può generare. Nel CSV i giorni al termine negativi restano numeri.
- Fascicolo: se il modello stampato non è più aggiornato, la copertina lo dice. Preventivo: avviso se le imposte vengono da una
  bozza o da un file incompleto.
- Invio: non si può creare una nuova copia mentre un invio è aperto, anche con due richieste contemporanee.
- Calcolatrice: se manca la categoria dell'immobile lo dice e invita a controllare la visura.
- Finestre: procedura guidata, preventivo, modifica di gruppo, incolla da Excel e «Azzera» chiedono conferma prima di perdere
  ciò che hai scritto; il pulsante evidenziato è l'azione («Salva», «Crea»), non «Chiudi». «Controlla» chiede prima di salvare
  le modifiche in sospeso.
- Messaggi: «Dichiarazione creata» solo se la pratica si apre; esito dell'importazione in italiano; nella calcolatrice i
  dettagli aperti restano aperti mentre scrivi.
- Accessibilità: i messaggi d'errore si leggono insieme al campo; tabella e menu «Operazioni» descritti correttamente ai
  lettori di schermo; la calcolatrice annuncia solo il totale.
- Velocità: selezionare una riga non ridisegna più tutta la pagina (con 150 righi da circa 90 ms a pochi ms).

Limiti aperti (da confermare con il professionista)
- Saggio legale per i decessi dal 2026: il programma usa il 2,5% e il prospetto in vigore, con un avviso; il decreto 2026 non è
  nelle fonti del programma.
- Pertinenze della prima casa (C/2, C/6, C/7 con codice X): dal 9/11/2026 moltiplicatore 110 come la prima casa (confermato
  dal professionista; prima 120).
- Preventivo e parcella: IVA su compensi più contributo cassa e ritenuta sui soli compensi; spese anticipate esenti e bollo
  non gestiti; nessuna dicitura per i regimi senza IVA; arrotondamento al centesimo voce per voce.
- Esiti delle ricevute che tengono aperta la pratica: oggi pagamento negativo, volture parziali o negative ed esiti
  contraddittori.

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
