# Seconda review completa — 7/11/2026 sera

Cinque revisori indipendenti, in sola lettura, sul ramo stabile dopo l'unione serale (guida, aspetto premium, Prossime azioni, calcolatrice, archivio veloce e miglioramenti DEAS). Prove fatte su archivi temporanei e dati sintetici; i file inviati sono stati letti solo da copie temporanee, poi cancellate. «Controllo ufficiale» indica il componente SUC13 eseguito in locale.

Il risultato di ogni revisore è segnato **C** (confermato: riprodotto o verificato su fonte) oppure **P** (probabile, da lettura del codice). ✔ indica che ho riletto il codice di persona e confermo il punto.

Stato della suite: **1942 test passati**, 1 saltato. Sicurezza dell'interfaccia locale (token, Host/Origin, XSS, path traversal): **nessun difetto**.

## Priorità 1 — dichiarazione sbagliata, invio, dati o sicurezza

| # | Area | Problema | Dove | |
|---|---|---|---|---|
| 1 | Export | Usufrutto e nuda proprietà accettati anche con la **devoluzione per legge**: il file risulta completo, ma il controllo ufficiale lo scarta con 6 errori bloccanti | `esporta.py:1563` | C ✔ |
| 2 | Controllo | Nel controllo eseguito a mano, il `.dgn` di **un altro file** (rinominato o di una revisione precedente) viene accettato come «passato»: basta il codice fiscale del defunto, e l'identificativo vale sempre 00001. Sblocca la conferma dell'invio | `controllo.py:555` | C ✔ |
| 3 | Invio | Preparando una seconda copia, il **tentativo d'invio in corso sparisce** dall'interfaccia. La copia nuova non si può inviare e la vecchia non si riconcilia: rischio di doppio invio con Desktop Telematico | `invio.py:396`, `elaborati.py:413`, `app.js:1311` | C |
| 4 | Claude | **«Claude in sola lettura» non arriva al server MCP** avviato da Claude Desktop: l'avviatore indica il file delle impostazioni solo all'interfaccia. Lo stesso vale per il profilo dello studio e per l'opzione «visura bloccante» | `avvia_successioni.py:166, 235` | C ✔ |
| 5 | Interfaccia | **La modifica di gruppo svuota un campo** in tutte le righe, se lo spunti senza scegliere un valore | `app.js:891` | C ✔ |
| 6 | Archivio | Effetti della mia ottimizzazione di oggi: l'archivio non si regge più da solo perché i dati restano nel file WAL, che non si riduce mai; un processo fermo, come Claude Desktop aperto, **tiene bloccata la cartella dati** | `archivio.py:94, 120` | C |
| 7 | Server | Le richieste web girano tutte su un solo thread: Ghostscript, Java, backup e PDF/A **bloccano l'intera interfaccia**; un «database is locked» diventa errore 500 | `web.py:141` | C |
| 8 | Import | Il valore quota (QuotaValore) del file viene **ricalcolato senza confronto** con l'originale: valori trascritti e volturati diversi, senza avviso | `importa.py:1236` | C |
| 9 | Allegati | Eliminazione e conversione controllano i righi EG fuori dalla transazione; il collegamento di un rigo EG a un allegato (`allegato_id`) non viene validato (accetta allegati inesistenti o di un'altra pratica); due conversioni in parallelo creano due PDF/A | `allegati.py:193, 252`, `schema.py:65` | C |

## Priorità 2 — risultati fuorvianti o funzioni incomplete

### Prossime azioni (`cruscotto.py`)

- Prende le 12 pratiche modificate più di recente e solo dopo ordina per scadenza: **le pratiche urgenti ma ferme spariscono**. **C** ✔
- Ignora la data di decorrenza del termine. **C**
- Dice «Genera il file» anche quando il file non si può generare, senza il motivo. **C**
- Copia rifiutata o resa superata: suggerisce «conferma e invia». **C**
- Registrazione con esito negativo: la mostra come «attesa». **C**

### Interfaccia

Tutti i punti sono **C**.
- Il tasto Invio dentro le finestre Operazioni, Calcolatrice e Guida le chiude e perde i dati.
- Ctrl+S salva anche con una finestra aperta.
- Chiudendo le Impostazioni le modifiche si perdono senza avviso.
- Alcuni pulsanti non sono protetti dal doppio clic: ricevuta, PDF/A, suddividi.

### Calcolatrice

- Gli importi con i centesimi danno «non stimabile», con un messaggio tecnico. **C**
- La passività predefinita è il mutuo (tipo 3): senza immobili non si stima, con immobili il mutuo viene agganciato al primo bene. **C**
- Nessun limite al numero di passività: 2000 voci richiedono 54 secondi e bloccano il server. **C**

### Albero genealogico

- Con un riferimento circolare nella rappresentazione, alcuni eredi spariscono senza avviso. **C**
- Il figlio premorto finisce in «Altri beneficiari». **C**

### Calcolo

- Il valore catastale non vede la prima casa che nasce dal diritto di abitazione del coniuge (codici 1, 2, 5, 6): moltiplicatore 120 invece di 110, con avviso falso. **P**
- Imposta pagata all'estero con usufrutto e nuda proprietà: possibile doppia detrazione. **P**
- L'ordine degli eredi nel quadro EA cambia in silenzio tra importazione e riesportazione. **C**
- La separazione con colpa ignora la «legge estera». **P**

### Brogliaccio e avvisi di qualità

- Ignorano i dati salvati in `opzioni.telematico`: colonne vuote e avvisi mancanti. **C**
- Segnalano «manca 1/2» quando gli eredi hanno lo stesso diritto scritto in due modi («1» e «proprieta»), che l'export accetta. **C**
- Il CSV non neutralizza le formule. **P**

### Claude (MCP)

- `invio_stato` e `stato_elaborati` sono classificati in lettura ma possono cambiare lo stato di una copia. **C**

### Documenti

- La guida della prima pratica reale salta i passaggi Prepara, Conferma e «Istruzioni per l'invio»: dopo l'invio, la ricevuta e l'esito dell'invio (`.esi`) non si possono registrare né abbinare. **C**
- La guida e la matrice di copertura si contraddicono su successioni prima del 2025, rinunce, legatari ed estero. **C**

### Catasto

- Un file JSON inserito a mano con `"completo": true` chiude l'acquisizione come se fosse arrivata da Entratel. **C**

## Priorità 3 — accessibilità, impaginazione, prestazioni, pulizia

- **Accessibilità:**
  - nei campi il nome letto dai lettori di schermo è quello interno;
  - nel tema scuro le iniziali della pagina iniziale hanno contrasto 1,86:1;
  - il menu a cassetto non trattiene il focus;
  - i ruoli `menu`/`tab` sono dichiarati senza la navigazione con le frecce.
- **Impaginazione:**
  - a 390 px c'è uno scorrimento orizzontale (titoli lunghi, barra di stato);
  - a 1366×768 restano 8 righe visibili.
- **Prestazioni:**
  - ogni tasto ridisegna tutta la tabella: 46 ms con 150 righe;
  - ogni clic su un fabbricato ricalcola i valori catastali dell'intera pratica.
- **CSS:** regole ripetute dopo l'unione delle due sessioni (`.home-corpo` cinque volte).
- **Test che passano per il motivo sbagliato:**
  - conferma dell'invio da MCP;
  - pulizia all'avvio;
  - detrazione estera.
- **Test che dipendono da Java e dal controllo ufficiale installati:** su un altro PC circa 280 test si saltano in silenzio.
- **Codice morto e duplicati:**
  - import inutilizzati in `agevolazioni.py`;
  - due calcoli dell'età;
  - due letture della data del decesso;
  - `stati_pratica` usata solo dai test.

## Come accelerare la suite (oggi 32-47 minuti)

| Intervento | Guadagno stimato |
|---|---|
| Cache dei risultati del controllo ufficiale per impronta dell'XML e dei JAR | −15/20 min |
| `pytest-xdist -n 4`, con server di prova su porta libera | 2,5-3 volte più veloce |
| Marcatore `java`, per un giro rapido quotidiano e la suite completa prima di ogni consegna | giro rapido di 5-7 min |
| Una sola JVM per più file, oppure il rapporto `.wri` solo quando serve | −3/15 min |
| Test MCP di suddivisione (57 s) e `test_agenti_gratuiti` (risoluzione del nome lenta su Windows) | −1,5 min |

## Cosa regge

- **Calcolatrice:** gli importi coincidono con il motore di esportazione su 3 casi.
- **Quote di legge:** corrette su 9 combinazioni di eredi.
- **Usufrutto:** i casi misti e incrociati sono accettati dal controllo ufficiale.
- **File reali:** i 7 file reali tornano identici, con le eccezioni dichiarate.
- **Pagina iniziale:** con 50 pratiche il pannello Prossime azioni si calcola in 0,1-0,2 secondi.
- **Guida:** pagine citate corrette e solo file ufficiali con impronta verificata.
- **Sicurezza locale:** token, Host/Origin, XSS e path traversal sono a posto.
- **Concorrenza e idempotenza:** con 2 processi e 8 thread nessuna lettura di dati vecchi; idempotenza e avvio contemporaneo dell'archivio corretti.
