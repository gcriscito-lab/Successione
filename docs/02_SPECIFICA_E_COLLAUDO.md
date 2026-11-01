# Successioni — specifica e collaudo v1.1

**1° novembre 2026.** Documento operativo che accompagna `01_PROMPT_CLAUDE_CODE.md`. Consolida requisiti e riscontri precedenti senza richiedere la lettura dei vecchi prompt. Stato: progetto da sviluppare, non applicazione già realizzata o approvata per trasmettere.

## 1. Decisioni, assunzioni e perimetro

| Stato | Contenuto |
|---|---|
| Richiesto dall'utente | Funzioni dichiarative del programma dell'Agenzia con collegamento per compilazione AI esterna, convertitore PDF/A, acquisizione catastale e invio/ricevute dall'app |
| Confermato dall'utente | Nessuna AI interna; servizio catastale utilizzato: Risultanze catastali tramite Entratel |
| Proposta di architettura iniziale | App locale su un PC Windows, compilazione disponibile senza Internet, salvo aggiornamenti e collegamenti esterni; MCP locale |
| Proposta di funzionamento | Claude prepara; la conferma finale nell'app autorizza la specifica trasmissione e gli eventuali addebiti mostrati |
| Da concordare se necessario | Più operatori contemporanei, archivio in rete, Modello 4 completo, priorità delle estensioni |

Il risultato finale comprende **frontespizio e quadri EA, EB, EC, ED, EE, EF, EG, EH, EI, EL, EM, EN, EO, EP, EQ, ER**, con le casistiche pertinenti al modello vigente. Comprende i dati per la domanda di voltura prevista nella successione; la gestione di una voltura separata è un'estensione distinta.

Una prima consegna può coprire un sottoinsieme dichiarato per dimostrare il funzionamento, senza ridurre l'obiettivo finale. Le pratiche non supportate restano conservabili come bozze e non finalizzabili attraverso un percorso che perda dati o produca calcoli incompleti. Il percorso storico viene riconosciuto e segnalato; la produzione del Modello 4 non è automaticamente compresa nella parità SUC13.

## 2. Evidenze disponibili e limiti

La ricognizione precedente ha censito **24 file locali: 9 PDF, 13 XSD, 2 JNLP**, con 1.654 pagine PDF complessive. Sono stati estratti e indicizzati i testi e analizzati gli schemi, con approfondimento delle parti pertinenti alla progettazione; questo non equivale al collaudo di ogni regola.

L'ispezione statica di alcuni componenti pubblici ha rilevato:

- configurazione del compilatore dichiarata **2.3.1 dell'11 marzo 2026**;
- coincidenza dello schema principale locale con quello incorporato nel componente esaminato;
- una tabella comune più recente nel componente pubblico, con l'ufficio TJ4/Monte Porzio Catone e altre aggiunte condivise;
- risorse residue non necessariamente attive nel modello corrente.

I JNLP forniti sono avviatori che richiamano componenti remoti. Sono state lette risorse/configurazioni e confrontati file; **non sono stati eseguiti il programma Java, un controllo SUC13 o un accesso autenticato**. Anche REA e i prodotti commerciali sono stati valutati attraverso documentazione, senza installazione o collaudo. Nessun invio è stato effettuato.

| Punto aperto | Prova richiesta |
|---|---|
| Controllo ufficiale richiamabile dall'app | Invocazione effettiva, input/output e diagnostico riferiti allo stesso file |
| Catasto Entratel | Sessione autorizzata, ambito e completezza dei risultati, importazione ripetibile |
| Invio SUC13 | Sequenza concreta dei file e degli strumenti; collaudo operativo solo su pratica effettiva autorizzata |
| Copie, attestazioni e ricevute | Disponibilità nei canali reali e corretta associazione al protocollo |
| Compatibilità di archivi | Esempi dei formati supportati e riapertura senza perdita, senza assumere capacità d'importazione del compilatore ufficiale |
| Regole numeriche dubbie | Caso di riferimento, fonti e confronto ufficiale con versione registrata |

## 3. Fonti e loro uso

Fonti del repository: `fonti/`; file e impronte in `fonti/manifest.json`. Il pacchetto operativo contiene 23 file ministeriali: 8 PDF, 13 XSD e 2 JNLP. Il manuale SEAC 2021, storico e commerciale, non è incluso né necessario per iniziare. Il conteggio di 24 file e 1.654 pagine riportato nella ricognizione storica comprendeva anche quel manuale; non descrive il contenuto attuale di `fonti/`. I fascicoli con `Nov_23` nel nome non vanno datati dal solo nome: il fascicolo 1 contiene aggiornamenti del 2025.

Per ogni regola registra fonte, riferimento/pagina o elemento, versione, data di acquisizione, decorrenza e casi coperti. La norma e gli atti ufficiali stabiliscono la disciplina; modello/istruzioni e specifiche stabiliscono la compilazione e il contratto tecnico. L'esito del controllo e il comportamento del programma sono riscontri applicativi. Se divergono, documenta il conflitto e sospendi la finalizzazione della casistica interessata, senza trasformare un possibile errore del software in una regola fiscale.

Riferimenti pubblici da verificare all'avvio dello sviluppo:

- [Avviatore compilatore](https://jws.agenziaentrate.it/jws/registro/2013/SUC13.jnlp) e [avviatore controlli](https://jws.agenziaentrate.it/jws/registro/2013/ControlliSUC13.jnlp).
- [Avviso controllo SUC13 2.3.1](https://telematici.agenziaentrate.gov.it/Main/Avviso?id=20260311121001): aggiornamento degli uffici.
- [Manuale Entratel Multifile](https://telematici.agenziaentrate.gov.it/pdf/Istruzioni_Entratel-Multifile.pdf): descrive operazioni batch; è un manuale storico e va confrontato con il prodotto installato. [Avviso 1.7.6 del 1° ottobre 2026](https://telematici.agenziaentrate.gov.it/Main/Avviso?id=20261001170552).
- [Documentazione Claude Code/MCP](https://code.claude.com/docs/en/mcp): configurazione e prova del client effettivo.
- [Ghostscript PDF/A](https://ghostscript.readthedocs.io/en/latest/VectorDevices.html) e [veraPDF](https://docs.verapdf.org/cli/validation/): candidati per conversione e validazione, con condizioni di distribuzione da verificare.
- [REA ufficiale](https://github.com/morluto/rea): strumento facoltativo per un'indagine circoscritta; disponibilità e supporto ai JAR da dimostrare, senza renderlo una dipendenza dell'app.

Nessun URL stabile garantisce contenuti o componenti immutati. Usa pacchetti coerenti di schema, tabelle e regole; conserva versione e impronte. Un aggiornamento va provato su casi di riferimento prima di diventare attivo. Le pratiche storiche devono restare ricostruibili con la versione usata, senza ricalcoli silenziosi.

## 4. Priorità: essenziali ed estensioni

| Priorità | Funzione | Confine |
|---|---|---|
| Essenziale | Pratiche, tutti i dati/quadri del perimetro, calcoli, stampa e telematico | Copertura finale SUC13 completa e dichiarata |
| Essenziale | MCP | Gestione della preparazione su dati reali dell'app, senza simulazione di clic |
| Essenziale | PDF/A | Utilità autonoma e conversione/verifica nel flusso EG |
| Essenziale | Catasto Entratel | Acquisizione effettiva e importazione selettiva; un caricamento manuale non completa il requisito |
| Essenziale | Invio, ricevute e documenti pertinenti | Collegamenti reali verificati, con esiti distinti |
| Essenziale | Salvataggio, import/export aperto della pratica, backup/ripristino | Conservazione dei dati e possibilità di uscire dal programma |
| Utile, successiva al primo caso completo | Import di file `.suc` esistenti | Portabilità con provenienza e rapporti di compatibilità |
| Utile, successiva al primo caso completo | Albero genealogico generato e proposta di quote legittime | Regole autonome da verificare; all'inizio è possibile inserire quote e allegare il documento esterno |
| Utile | Elenco dei documenti e modelli accessori | Condizioni ufficiali e modelli semplici, senza editor complesso |
| Estensione | Import PDF/XML di visure, `.diz`, copia PDF di dichiarazione | Parser con formati/casi dichiarati; nessun dato indovinato |
| Estensione | Rateazione/F24 e ripartizioni aggiuntive oltre i dati necessari al modello | Prospetti autonomi con regole e collaudi dedicati |
| Da concordare | Modello 4 completo, volture separate, multiutenza | Progetto aggiuntivo, distinto dal primo rilascio |

Le scelte di pagamento previste dal modello e i relativi campi restano parte essenziale; l'estensione riguarda l'eventuale gestione successiva di scadenziari/prospetti/F24. Nessuna AI interna, contabilità di studio, portale clienti o progetto di divisione nella prima versione.

## 5. Esperienza d'uso e modello dei dati

Cinque aree principali: **Pratiche, Compilazione, Documenti, Controlli, Invio ed esiti**. La compilazione conserva l'accesso ai quadri ministeriali e affianca una tabella di persone/beni/devoluzioni. Errori e richieste documentali aprono il dato interessato. Mostra solo i campi pertinenti mantenendo recuperabili gli altri dati già inseriti.

Il modello deve distinguere:

- pratica, revisione dichiarativa, copie congelate ed eventuale precedente dichiarazione;
- persona/ente, ruolo dichiarativo, qualifica di beneficiario e relazioni familiari;
- bene, identificativi e dati originali, diritto e possesso del defunto, devoluzioni;
- passività, beneficiari/ripartizione e documenti di supporto;
- opzioni fiscali, documenti EG, dichiarazioni EH/EI e dettagli di pagamento;
- risultati di calcolo, controlli, tentativi di trasmissione e documenti ricevuti.

Gli identificativi interni non cambiano quando il compilatore riordina righe/moduli. Un beneficiario su più qualifiche non diventa più persone. Le continuazioni del modello non diventano nuovi beni duplicati. Calcola e controlla le quote secondo diritto, massa e regola pertinente: non sommare indiscriminatamente proprietà, nuda proprietà e usufrutto come se fossero lo stesso diritto.

Per i dati rilevanti conserva origine e stato: inserito, acquisito, proposto dall'assistente, calcolato o confermato; documento/riferimento di supporto se disponibile. Una provenienza documentale non prova automaticamente il contenuto fiscale. In caso di import, confronta prima e applica le modifiche in una transazione, conservando ciò che non è stato riconosciuto.

Le modifiche autorizzate a una bozza possono essere effettuate da Claude senza richiedere un clic per ogni campo. Deve essere possibile vedere le modifiche e recuperare la revisione precedente. Il database e gli allegati formano un unico archivio logico da salvare e ripristinare insieme.

## 6. MCP: contratto minimo

| Gruppo | Funzioni necessarie |
|---|---|
| Capacità e struttura | Versione applicativa, funzionalità disponibili, schema dei campi/codici, dati mancanti e casi non coperti |
| Pratica | Elencare, creare, leggere e aggiornare soggetti/beni/passività/devoluzioni/opzioni; leggere differenze e revisioni |
| Documenti | Acquisire file autorizzati o riferimenti, assegnare tipo/finalità, convertire/verificare e collegare evidenze |
| Elaborati | Calcolare, verificare internamente, eseguire controllo ufficiale, anteprima, esportazione, preparazione dell'invio |
| Collegamenti | Avviare acquisizione catastale, leggere job e risultati, importare selezione; consultare esiti e scaricare documenti |

Sono gruppi di capacità, non un obbligo di usare esattamente cinque strumenti generici. Preferisci strumenti con schemi chiari e operazioni delimitate a un solo comando che esegua qualsiasi azione.

Ogni modifica include identificativo pratica, revisione attesa e chiave di richiesta quando serve a evitare duplicazioni. Gli importi sono valori decimali senza ambiguità di separatore e le quote hanno numeratore/denominatore. Restituisci errori con codice, campo/percorso interno, quadro/rigo quando applicabile, fonte della regola e indicazione del dato mancante. Un conflitto di revisione non deve sovrascrivere silenziosamente una modifica manuale.

Le elaborazioni lunghe restituiscono un job persistente con stato, risultato, eventuale azione richiesta e possibilità di ripresa. La disconnessione MCP non cancella una lavorazione né prova che sia fallita. Gli aggiornamenti del client non cambiano il risultato di una richiesta già eseguita.

Limita l'accesso alle pratiche e ai documenti autorizzati. I segreti del collegamento rimangono nel servizio locale. Nessuna shell, SQL o lettura arbitraria del PC come scorciatoia. Verifica configurazione e ciclo di vita nel client Claude reale: un test del solo server non prova che Claude possa usarlo. Le API pubbliche del programma devono consentire futuri client compatibili senza sviluppare altri connettori adesso.

## 7. Documenti e PDF/A

Il programma riceve il **tipo di documento e la destinazione** dall'utente o dal client esterno. Riconoscere formato e dimensione è deterministico; capire che un documento prova un requisito richiede una verifica distinta. L'eventuale elenco dei documenti mancanti deriva da regole sulle scelte della pratica, non da supposizioni sul testo del PDF.

Flusso: acquisisci originale → assegna categoria/finalità → rileva formato e firme/protezioni → conserva se già conforme oppure crea derivato → valida il profilo → controlla dimensioni/pagine → collega a EG. Rendere disponibile anche «Converti PDF in PDF/A» con selezione dell'output.

Nei materiali forniti sono indicati **PDF/A-1a o PDF/A-1b**, massimo **5 MB per allegato** e **40 MB compressi per fornitura**. Riferimenti: specifiche locali, pagine 7 e 3. Verifica l'applicabilità delle specifiche aggiornate, l'unità effettiva in byte e il punto della catena su cui misurare la fornitura. Per TIFF applica i requisiti ufficiali se ne implementi il supporto.

Un convertitore con uscita positiva o metadati PDF/A non prova la conformità. Leggi l'esito di un validatore indipendente sul profilo richiesto e conserva il rapporto. Dopo separazione/riduzione ricontrolla i derivati; nessuna pagina persa. La fedeltà visiva e la leggibilità richiedono prove su un insieme rappresentativo e anteprima dell'output, anche quando il formato è conforme.

File protetti, danneggiati o firmati hanno un esito esplicito; non descrivere come conservata la firma dell'originale se il PDF è stato riscritto. Mantieni originali, derivati e rapporto collegati. La verifica di formato e la verifica della firma/sottoscrizione non sono intercambiabili.

## 8. Calcoli, XML e stampa

Organizza regole e tabelle per versione e decorrenza. Usa decimali/frazioni e una politica esplicita per ogni arrotondamento, con i passaggi ricostruibili. Distingui applicazione della disciplina, correttezza dei dati documentati e superamento dei controlli. I valori derivati non possono essere sovrascritti attraverso MCP per forzare una quadratura; eventuali campi ufficialmente modificabili seguono una regola esplicita.

Casi da coprire: diverse decorrenze; plurime qualifiche e franchigie; eredi/legatari; DN/BI e inventario; agevolazioni e riduzioni art. 25; detrazioni estere; prima casa e diritti reali; particolari terreni; immobili esteri/tavolare; trust; sostitutive; pagamenti e precedenti versamenti. La completezza si dimostra con una matrice campo/regola/caso/test, non con il solo numero di schermate.

**Dubbio documentato da risolvere:** nell'allegato locale al calcolo, pagine 7-8, `2.500 × 6.567 / 200.000 = 82,0875`, mentre l'esempio espone 82,08. Non fissare quel centesimo come risultato di riferimento già validato: prova il comportamento ufficiale e chiarisci il criterio. La divergenza interessa quella regola/casistica, non impedisce tutte le attività indipendenti.

Serializza XML UTF-8 con namespace, ordine, busta e tipi ricavati dagli XSD effettivi. Una dichiarazione per fornitura; allegati nei nodi EG previsti con dati e contenuto Base64. Rispetta importi/codici ammessi, continuazioni e riferimenti. Le annotazioni XSD contengono anche regole da implementare separatamente dalla validazione dello schema.

La stampa è prodotta dai medesimi dati/versione del file telematico; verifica campi, ripetizioni, allegati e assenza di tagli. Non esporre «conforme» se la verifica ha riguardato soltanto la grafica.

Import/export della pratica interna, telematico `.suc`, archivio di lavoro `.diz` e file successivi del controllo/autenticazione sono oggetti diversi. Individua la catena effettiva. **Non imporre come criterio generale l'importazione di un `.suc` nel compilatore ministeriale se quella funzione non è supportata:** la prova del controllo ufficiale e la riapertura nel nostro programma sono verifiche distinte. Per `.diz`, se implementato, serve invece la prova di compatibilità del formato di lavoro.

## 9. Catasto e canali telematici

### Risultanze catastali

Prova il servizio autorizzato del committente; identifica il profilo, i filtri e l'ambito. Prediligi un'interfaccia documentata quando disponibile; un eventuale browser assistito deve rispettare autenticazione e passaggi interattivi e poter riprendere una sessione interrotta. Non basare il progetto su endpoint inventati o su risposte memorizzate presentate come correnti.

Conserva risultati originali o una rappresentazione tracciabile, identificativi, diritti/quote e rendite/redditi effettivamente restituiti. I risultati possono non essere una visura PDF. Confronta duplicati, graffati, porzioni e dati mancanti; non attribuire proprietà o agevolazioni solo dall'acquisizione. Gestisci visure/atti ulteriori per la situazione al decesso quando necessarie.

### Controllo, preparazione e invio

Dimostra come richiamare il controllo ufficiale; il solo nome di una classe Java non documenta una CLI. Se inizialmente occorre un passaggio manuale, rendilo tracciabile e registra il requisito di automazione come ancora aperto.

Per Entratel Multifile verifica comandi/configurazioni della versione installata, file intermedi, profili e ambiente di sicurezza. Non reinventare firma e cifratura. L'integrazione deve consentire di lavorare dalla pratica, anche quando dietro utilizza componenti ufficiali separati. Ricevute e altri documenti possono richiedere canali differenti: verifica l'intera raccolta richiesta.

Ogni tentativo è un record persistente legato alla copia congelata della dichiarazione. La chiave di richiesta previene duplicati nel nostro sistema; **non garantisce che il servizio dell'Agenzia offra un meccanismo equivalente**. Una risposta incerta richiede riconciliazione dei protocolli/esiti e non un reinvio automatico. Un esito finale negativo va conservato con la motivazione e non sovrascritto da un generico «errore di rete».

## 10. Stati e invalidazione dei controlli

Usa stati separati, con evidenze e data, per queste dimensioni:

| Dimensione | Esempi |
|---|---|
| Dati e documenti | incompleti, da verificare, verificati per il perimetro indicato |
| Calcoli | non eseguiti, da ricalcolare, completati, divergenza aperta |
| Controllo ufficiale | non eseguito, positivo, negativo, non verificabile |
| Trasmissione | preparata, confermata, avviata, esito incerto, trasmessa con riscontro |
| Esiti successivi | registrata/scartata; pagamento atteso/positivo/negativo; volture complete/parziali/negative; documenti attesi/acquisiti |

Non è un unico elenco lineare: alcuni esiti possono arrivare separatamente o non essere applicabili. Un errore nel pagamento non cancella la ricevuta di registrazione. Una prima ricevuta non prova che le volture siano concluse. Non dedurre codici documentali dall'ordine di arrivo.

Ricalcola e ricontrolla quando cambia un dato esportato, allegato effettivo, opzione o regola rilevante. Conserva il precedente esito sul suo input; per la versione corrente diventa obsoleto. Mantieni validi i risultati che non dipendono dalla modifica. Una nota interna o un ordinamento solo visivo non annullano il controllo se non cambiano i dati/file dichiarativi. La conferma dell'invio riguarda manifest degli elaborati, revisione, importi e profilo; una modifica materiale la invalida.

## 11. Architettura, manutenzione e dipendenze

Un servizio applicativo possiede archivio e regole. GUI e MCP sono accessi agli stessi servizi; gli adattatori esterni non replicano il motore fiscale. Il trasporto MCP può essere stdio; il processo del client non deve essere l'unico luogo in cui esistono dati o stato dei job. Se serve un servizio locale persistente, definirne chiaramente avvio/arresto e responsabilità.

Rileva Windows/client reale e gli eventuali confini WSL, percorsi con spazi e caratteri italiani. Non assumere che un comando eseguito su un altro ambiente abbia accesso all'archivio del programma. Le dipendenze normali dell'app vengono incluse o installate con procedura guidata; strumenti ufficiali e componenti terzi vanno distribuiti secondo le condizioni applicabili, con rilevamento e diagnostica chiari.

Segreti nel deposito protetto del sistema, dati in percorsi applicativi dell'utente e documenti nel perimetro scelto. Backup coerente di database/allegati e prova di ripristino. Aggiornamenti con versione fissata, migrazioni recuperabili e regressione sui casi di riferimento. Non introdurre servizi cloud o gestione di licenze del nostro prodotto per l'uso locale iniziale.

## 12. Matrice minima di accettazione

Le prove sotto non sostituiscono la copertura campo per campo. Un test non eseguibile resta tale; nessun risultato simulato viene registrato come controllo o servizio reale superato.

| ID | Prova | Evidenza per considerarla riuscita |
|---|---|---|
| A01 | Installazione e avvio su Windows | Programma avviabile senza ambiente di sviluppo e guida dei prerequisiti mancanti |
| A02 | Salvataggio/ripristino | Pratica e allegati identici dopo riavvio e ripristino di un backup |
| A03 | Stessa pratica da GUI e MCP | Modifica visibile, risultato coerente e revisione comune nel client Claude effettivo |
| A04 | Doppia richiesta e conflitto | Nessun duplicato; modifica manuale recente non sovrascritta |
| A05 | Quote e continuazioni | Numeratori/denominatori esatti, più beneficiari/moduli, diritti distinti e riferimenti coerenti |
| A06 | Franchigie e DN/BI | Casi verificati per qualifiche multiple, inventario ed eredi/legatari |
| A07 | Decorrenze e casi fiscali | Risultati attesi indipendenti per regole storiche/vigenti e casistiche della matrice |
| A08 | Riduzioni/estero/arrotondamenti | Fonti e valori intermedi conservati; dubbio sui centesimi risolto o caso dichiarato non finalizzabile |
| A09 | XML e stampa | Schema valido, allegati corretti, dati/versione coerenti e stampa controllata visivamente |
| A10 | Controllo ufficiale | Diagnostico originale positivo su un caso e negativo su un errore applicativo predisposto; hash dell'input e versione |
| A11 | PDF/A | Documento ordinario convertito e validato; un file non conforme correttamente respinto; pagine leggibili |
| A12 | Allegati difficili e dimensioni | Firmato/protetto/danneggiato gestiti esplicitamente; suddivisione e soglie provate senza perdita |
| A13 | Acquisizione catastale | Prova autenticata autorizzata, risultati con ambito/provenienza, controllo di completezza |
| A14 | Import catastale ripetuto | Aggiornamenti confrontabili, nessun doppione e campi ignoti conservati/segnalati |
| A15 | Ripresa di una lavorazione | Sessione scaduta o client chiuso; stato persistente e ripresa senza risultati inventati |
| A16 | Invalidazione selettiva | Modifica dichiarativa invalida il controllo pertinente; nota interna irrilevante non lo invalida |
| A17 | Preparazione e conferma | Elaborati congelati, importi/profilo visibili, modifica materiale invalida la conferma |
| A18 | Invio incerto | Simulazione locale di rete interrotta e prova dell'assenza di reinvii ciechi; collaudo reale solo quando autorizzato |
| A19 | Ricevute ed esiti separati | Associazione a protocollo/pratica, scarto e voltura parziale conservati con originali; documenti attesi riconoscibili |
| A20 | Copertura e aggiornamento | Matrice dei quadri/regole, casi mancanti bloccati alla finalizzazione, aggiornamento provato su casi di riferimento |

Test locali e fixture autorizzate verificano il comportamento dell'adattatore; l'effettiva interoperabilità con un servizio richiede anche un riscontro reale. Nessuna dichiarazione inventata va trasmessa al servizio di produzione. Il collaudo finale dell'invio avviene su una pratica effettiva e verificata con autorizzazione specifica; finché manca, il requisito operativo rimane da collaudare.

## 13. Ordine di esecuzione e consegne

| Passaggio | Risultato atteso |
|---|---|
| Ricognizione e prove critiche | Fonti/versioni e matrice iniziale; PDF/A reale; MCP reale; modalità di controllo provata; piano concreto e riprendibile per i collegamenti autenticati |
| Caso completo | Preparazione da GUI e da MCP fino a elaborati, riapertura e controllo, con i limiti espliciti del primo caso |
| Estensione | Copertura SUC13 progressiva, casistiche particolari e collegamenti; requisiti ancora aperti tracciati |
| Consegna utilizzabile | Installazione, manuale breve, configurazione MCP, backup/ripristino, rapporti di collaudo e matrice di copertura |

Se un'integrazione richiede il committente, prepara tutto il necessario prima della richiesta: punto di accesso, dati di prova appropriati, risultato atteso e modalità di acquisizione dell'esito. Continua il lavoro indipendente. Non usare la fase preliminare per rinviare indefinitamente il primo caso funzionante.

## 14. Confronto di mercato e cambiamenti della revisione

Il confronto pubblico ha suggerito funzioni, non dimostrato integrazioni o accuratezza fiscale dei concorrenti:

| Fonte | Spunto mantenuto |
|---|---|
| [DE.A.S. — acquisizione Entratel](https://www.geonetwork.it/docs/helpdeas/modello-telematico/creazione-pratica-da-entratel.html) | Esistenza documentata di un flusso simile e limite dichiarato sui graffati, da provare sul nostro servizio attuale |
| [DE.A.S. — allegati](https://www.geonetwork.it/docs/helpdeas/modello-telematico/allegati.html) | PDF/A nel flusso di caricamento |
| [Eredito — caratteristiche](https://www.gecsoftware.it/software-successioni-e-volture-p4309/caratteristiche/) | Relazioni familiari e prospetti per soggetto/bene |
| [SuccessOne — funzioni](https://www.blumatica.it/software-successioni-legittime-testamentarie-e-miste/) | Diritti reali, quadratura e prospetti analitici |

Questa revisione introduce un solo prompt operativo con una specifica autonoma; distingue le quattro richieste dalle estensioni; rende esplicita la classificazione dei documenti da parte dell'utente/client esterno; separa i formati di lavoro dal telematico; precisa la prova del client MCP Windows; distingue stati e invalidazioni; conserva il dubbio sugli arrotondamenti e richiede evidenze concrete per i collegamenti. Nessuna installazione, sviluppo dell'app o trasmissione è stata eseguita durante questa revisione.


## 15. Sviluppo cloud e destinazione Windows

La destinazione Windows del prodotto non implica che tutto lo sviluppo debba avvenire su Windows. In Linux sviluppa nucleo, archivio, regole, XML, stampa, MCP e conversione PDF/A con gli strumenti disponibili. Verifica concretamente la possibilità di eseguire componenti ufficiali Java: se non dimostrabile, registra il limite soltanto sul relativo controllo. Prove del client Claude su Windows, installazione/vault del sistema e servizi autenticati restano da collaudare sulla postazione reale. Mantieni adattatori con esiti espliciti e test locali, senza falsi positivi. La mancanza di una prova operativa non blocca il primo caso locale né richiede un nuovo consenso a creare il codice. Vedi `docs/COLLAUDO_CLOUD_WINDOWS.md`.
