# Review del programma Successioni — 3 novembre 2026

## 1. Esito

**Non OK per l'uso professionale dei flussi esaminati.** Sono riprodotti sei difetti: perdita silenziosa di agevolazioni nell'importazione, errata gestione delle continuazioni, perdita di modifiche al frontespizio e tre problemi nel percorso di invio/ripresa. Non sono state applicate correzioni al programma né effettuati invii reali.

Esaminata la copia `Successione`, commit `538e1259aaf24bf4871c2840ca7117d06dd61439`, comprese le modifiche locali a `servizio.py`, `web.py`, `static/app.js`, `static/index.html` e i file nuovi `telematico/importa.py`, `tests/test_telematico_importa.py`. La copia `Successione-sorgenti-96d0051` e il bundle non sono l'oggetto della review. I precedenti rapporti di revisione non sono stati usati per ricavare i rilievi.

## 2. Quadrature eseguite

- `python scripts/verifica_materiali.py`: **passato**, 23 fonti integre (8 PDF, 13 XSD, 2 JNLP).
- Il Python di sistema non contiene pytest. Usato `.venv/Scripts/python.exe`, Python 3.14.4, pytest 9.2.0.
- Suite mirata: `.venv/Scripts/python.exe -m pytest -q --basetemp=build/review_domain tests/test_servizio.py tests/test_telematico_esporta.py tests/test_collegamenti_invio.py tests/test_matrice_coerenza.py tests/test_telematico_calcolo.py tests/test_quadri.py tests/test_telematico_nessuna_perdita.py tests/test_invio_stati_extra.py`: **72 passed in 68.17s**.
- Suite complessiva: `.venv/Scripts/python.exe -m pytest -q --basetemp=build/review_complete`, eseguita fuori dal sandbox: **566 passed, 1 failed, 28 skipped, 1 warning in 242.48s**. Non è una suite interamente verde.
- Unico fallimento: `tests/test_installazione.py:108`, `test_candidati_windows_cartelle_standard_versione_piu_recente`. Il test prepara Ghostscript 10.05.0 in una cartella temporanea e si aspetta quel percorso; la ricerca include anche `C:\gs`, trova l'installazione reale `C:\gs\gs10.08.0\bin\gswin64c.exe` e la restituisce. Il test non isola la macchina ospite (`scripts/windows/avvia_successioni.py:79-80`). È un problema di riproducibilità del test, non una prova di mancato avvio di Ghostscript o di errore fiscale; isolare la ricerca con un doppio di filesystem/glob o rendere tutte le radici iniettabili. I 28 test saltati restano non eseguiti. Warning: deprecazione `pypdf.add_js` nel generatore del corpus sintetico.
- Prime esecuzioni nel sandbox interrotte: il percorso temporaneo predefinito produceva errori di accesso; `test_agenti_gratuiti.py::test_elenco_modelli` non raggiungeva il server locale; TestClient restava bloccato nella creazione di `asyncio` dentro `socket._fallback_socketpair/accept`. Lo stack è stato acquisito con `-o faulthandler_timeout=15`. Questi esiti non sono trattati come bug applicativi; la suite complessiva è stata rilanciata fuori dal sandbox con temporanei sotto `build/`.
- Sei riproduzioni aggiuntive con dati sintetici, riportate sotto. Per i requisiti del controllo nell'adattatore di invio è stato utilizzato il doppio di test `controllo_finto` già presente nei test: **non è stato eseguito un controllo ufficiale positivo**.
- Verifica JavaScript tramite Node 24.16.0 e un DOM minimo in memoria: eseguite le funzioni reali di `app.js`; nessuna prova visuale nel browser.

## 3. Rilievi

### R01 — Alta / P1 — L'importazione elimina agevolazioni senza segnalarle e consente di riesportare un file completo

**Codice:** `src/successioni/telematico/importa.py:183-195`, funzione `devoluzioni_di`; inventario finale dei dati omessi a partire da riga 345.

**Fatto verificato:** il parser legge soggetto, quota e diritto della devoluzione, ma non `Agevolazioni`. L'elenco `non_importato` identifica interi quadri esclusi e non segnala questo campo perso all'interno di EC.

**Riproduzione:** generato l'XML di `caso_a10()` con data di riferimento 2025-09-01; aggiunto `suc:Agevolazioni=P` alla prima devoluzione del fabbricato. `valida_xsd` restituisce **zero errori**. L'importazione restituisce `avvisi=[]`, non conserva l'agevolazione e non la cita in `non_importato`. Riassegnati i riferimenti agli allegati sintetici e `dichiara_copie_conformi=True`, la riesportazione restituisce `completo=True`, zero errori e un XML **identico al caso originario senza agevolazione**.

**Impatto:** la pratica importata può perdere un'informazione che incide sul trattamento del bene; una successiva esportazione completa non fa emergere la perdita. La validità XSD del caso predisposto non equivale alla validazione ufficiale o fiscale dell'XML modificato.

**Fonte:** XSD locale `fonti/Specifiche tecniche/SUC13_20250702/SUC/xsd/fornituraSUC13_v1.xsd`, tipo `DevoluzioneImmobili_Type`, elemento `Agevolazioni`; annotazioni delle sezioni EF collegate alle agevolazioni. Non è necessario stabilire qui un importo d'imposta per dimostrare la perdita.

**Correzione suggerita:** conservare i campi supportati e censire esplicitamente ogni elemento significativo non importato. Per un campo fiscale non rappresentabile, registrare l'omissione nella pratica e impedire la finalizzazione fino alla risoluzione, oppure rifiutare l'importazione. Il generico avviso che EE/EF saranno ricalcolati non descrive la perdita di un dato di ingresso.

### R02 — Alta / P1 — I righi di continuazione diventano beni autonomi

**Codice:** `src/successioni/telematico/importa.py:219-224`; stesso problema nel ciclo ER a partire da riga 268.

**Fatto verificato:** ogni rigo aumenta il contatore e riceve un nuovo identificativo di bene; il parser non interpreta il flag `Continuazione`.

**Riproduzione:** `_bozza(_quattro_figli())` da `tests/test_telematico_esporta.py` produce tre beni, ciascuno con quattro beneficiari e un rigo di continuazione. `importa_xml` e `Servizio.importa_xml_telematico` producono **sei beni**: due terreni, due fabbricati e due disponibilità finanziarie. `b_eb002`, `b_ec002`, `b_er002` sono privi di valore e dati identificativi. Gli avvisi sono vuoti. Le devoluzioni del quarto beneficiario sono associate a questi beni fittizi, anziché al bene del rigo precedente.

**Impatto:** il rapporto bene/beneficiari è alterato e la pratica non può essere ripresa fedelmente; occorre ricostruirla manualmente. Il difetto si verifica anche con XML prodotto dallo stesso programma.

**Fonte:** medesimo XSD, elemento `Continuazione` dei tipi di devoluzione: il rigo successivo contiene gli ulteriori soggetti senza ripetere i dati identificativi del bene. `esporta.py:986-1001` applica già tale struttura.

**Correzione suggerita:** mantenere il bene corrente finché la catena di continuazioni non termina, anche al cambio di modulo; aggiungere le devoluzioni a quel bene e preservare correttamente i riferimenti di posizione usati da ED. Testare almeno quattro e sette beneficiari, continuazioni tra moduli e cespiti successivi.

### R03 — Alta / P1 — Le modifiche ai dati della dichiarazione non sono rilevate dal salvataggio generale

**Codice:** `src/successioni/static/app.js:428-449`, funzione `sezioneDatiDichiarazione`; confronto con `nMod`, `salvaTutto`, `apri` e `beforeunload`.

**Fatto verificato:** i campi stato civile, devoluzione, firma, IBAN e testamento sono conservati soltanto negli elementi DOM; non hanno handler `input/change` che aggiornino il buffer `S.dirty`. Solo il pulsante locale «Salva dati della dichiarazione» li legge.

**Riproduzione:** eseguita la funzione reale in Node con DOM minimo e stato civile salvato `1`. Modificato il controllo a `2`: `nMod()` resta **0** e gli eventi del controllo sono `[]`. Ricreata la sezione, il valore torna a **1**. Non occorre un errore di rete per perdere il dato.

**Impatto:** cambiare quadro, rigenerare la vista o chiudere la finestra può eliminare le modifiche senza l'avviso previsto per le altre schede. «Salva» e Ctrl+S non le includono. Il successivo export può usare i vecchi dati benché l'utente abbia premuto il salvataggio generale.

**Correzione suggerita:** integrare questi campi nel buffer condiviso e nel salvataggio generale, includendoli negli avvisi di uscita e nelle protezioni durante le richieste. Conservare anche le modifiche quando il salvataggio fallisce.

### R04 — Alta / P1 — Un invio simulato impedisce il successivo percorso reale manuale

**Codice:** `src/successioni/collegamenti/invio.py:418-422`, vincolo `nessun_altro_invio`.

**Fatto verificato:** il vincolo ricerca tutte le copie della pratica in stato `in_invio` o `trasmessa`, senza distinguere il trasporto simulato da quello reale manuale. Anche la simulazione porta la copia a `trasmessa`.

**Riproduzione:** creata e confermata una copia con il doppio di controllo dei test; eseguita `InvioAdattatore(..., TrasportoSimulato()).trasmetti(...)`. Preparata e confermata una nuova copia della medesima pratica con l'adattatore manuale; il tentativo manuale è respinto con `ReinvioNonAmmesso: la copia ... della stessa pratica e' gia' 'trasmessa': nessun secondo invio della stessa dichiarazione`.

**Impatto:** il pulsante «Invia in PROVA» contamina lo stato operativo della pratica e impedisce di avviare il passaggio manuale successivo, pur non avendo trasmesso nulla all'Agenzia. Non esiste nel percorso ordinario un reset di questa copia finale.

**Correzione suggerita:** separare persistentemente prove e tentativi operativi, applicando il vincolo contro i duplicati nell'ambito pertinente. Mantenere integralmente il divieto di reinvio per tentativi reali incerti o trasmessi.

### R05 — Media / P2 — La GUI perde il percorso di riconciliazione e le istruzioni dopo l'avvio manuale

**Codice:** `src/successioni/static/app.js:369-378`, `renderInvio`; `src/successioni/invio_servizio.py:82-90`; `src/successioni/collegamenti/invio.py:469-472`.

**Fatto verificato:** il tentativo manuale assume `attesa_invio_manuale`, mentre la copia resta `in_invio`. Le istruzioni sono nel risultato del tentativo; la risposta ordinaria `invio_stato` restituisce le copie con i soli identificativi dei tentativi. La GUI cerca gli stati di riconciliazione sulla **copia**, con i valori `esito_incerto/in_trasmissione`, e propone soltanto una riconciliazione simulata. Non presenta un modulo per protocollo/evidenze del tentativo manuale.

**Riproduzione:** dopo `InvioAdattatore(...).trasmetti(...)` in modalità manuale: `copia=in_invio`, `tentativo=attesa_invio_manuale`, `azione_copia=None`, istruzioni presenti sul tentativo. Il pulsante visibile fino a quel momento scompare; le condizioni di rendering della riconciliazione non corrispondono allo stato della copia. La stessa discrepanza riguarda il tentativo simulato incerto, la cui copia rimane `in_invio`.

**Impatto:** chi usa l'interfaccia non riesce a completare il flusso annunciato «invio manuale e registrazione dell'esito» né a riconciliare un tentativo incerto. L'API dispone di una funzione di riconciliazione, ma il percorso GUI non la rende utilizzabile per il caso reale manuale.

**Correzione suggerita:** restituire e mostrare il dettaglio del tentativo corrente, le istruzioni e il protocollo; abilitare i comandi dagli stati del tentativo e chiedere le evidenze previste dall'API, usando la modalità del tentativo persistita. Verificare sia attesa manuale sia timeout simulato.

### R06 — Media / P2 — Un'interruzione tra due commit lascia la copia bloccata anche dopo la riconciliazione

**Codice:** `src/successioni/collegamenti/invio.py:454-456` e rami analoghi a righe 460-467; uscita anticipata in `riconcilia:499-501`.

**Fatto verificato:** il risultato finale del tentativo e lo stato della copia sono registrati con due transazioni distinte. Se il processo si interrompe tra le due, il tentativo è finale ma la copia rimane `in_invio`. La riconciliazione ritorna subito per i tentativi finali, senza riallineare la copia.

**Riproduzione:** sul trasporto simulato, inserita in memoria un'eccezione `OSError` immediatamente prima della transizione della copia a `trasmessa`, dopo il commit del tentativo. Output prima e dopo `riconcilia(tid)`: **`trasmesso in_invio`** in entrambi i casi. Si è iniettato un guasto per provare il punto di interruzione; non si afferma che un crash reale sia stato osservato.

**Impatto:** stato operativo incoerente e mancata ripresa automatica dopo un'interruzione. Nel ramo `non_trasmesso` lo stesso disegno può lasciare la pratica bloccata anche quando è stata registrata la prova dell'assenza dell'invio.

**Correzione suggerita:** rendere atomico l'aggiornamento delle due righe dopo la chiamata esterna oppure prevedere un recupero idempotente che ricostruisca lo stato della copia dal tentativo finale. La ripresa non deve richiamare il trasporto per trasmettere di nuovo.

## 4. Punti aperti

- Aggiungere regressioni sui sei casi, perché i casi positivi esistenti non verificano questi confini. Il test attuale di importazione usa principalmente il caso base con due eredi, che non esercita le continuazioni.
- Estendere l'inventario dei campi XML importati e omessi: l'agevolazione è una perdita dimostrata, non un censimento esaustivo di tutte le possibili omissioni. L'importazione di interi quadri dichiarati non gestiti rimane un limite esplicito distinto dai rilievi nuovi.
- Allineare i testi di stato della GUI: la barra di stato riporta sempre «Controllo ufficiale: non eseguito» (`app.js:100`) e `stato_elaborati` presenta la trasmissione come non disponibile benché esista il percorso in `InvioMixin`. Sono incongruenze informative ulteriori, senza una prova qui di trasmissione reale erroneamente attestata.
- Aspetti positivi verificati: transazioni del servizio, rifiuto dei riferimenti pendenti, idempotenza di base, conflitti di revisione, ripristino non distruttivo e precisione delle quote/importi sono coperti dalla suite mirata passata. Il deposito degli artefatti usa la stessa cartella `allegati`, inclusa dal backup: non è emersa una perdita generalizzata di tali file nel backup.

## 5. Cosa non ho potuto verificare

- Nessun invio reale, accesso autenticato al catasto o acquisizione di ricevute reali; nessuna credenziale utilizzata.
- Nessuna attestazione sulla correttezza fiscale complessiva, sulle regole aggiornate al 2026 o sulla conformità professionale di ogni casistica. Le prove fiscali predisposte sono state eseguite come test software; per le due anomalie XML si è fatto riferimento allo schema locale.
- Nessun nuovo collaudo visuale nel browser o di installazione Windows; la verifica JavaScript descritta usa un DOM minimo, non Playwright.
- Non è stato condotto un audit di sicurezza esaustivo né un censimento completo di ogni quadro e campo SUC13. Sono stati letti i percorsi principali di archivio, servizio, export/import, GUI e invio, con prove mirate sui difetti descritti.
- I documenti del progetto riportano prove precedenti su PDF/A e componenti ufficiali; non sono attribuite a questa review né sostituiscono una nuova esecuzione.
