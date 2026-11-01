# Successioni — prompt di sviluppo v1.1

**Revisione del 1° novembre 2026 per repository e sviluppo cloud.** Il repository contiene questo prompt, la specifica e le fonti. Leggi anche `CLAUDE.md` nella radice. Non serve alcun percorso sul PC del committente per iniziare.

---

## Obiettivo

Realizza per un professionista italiano un programma locale Windows per compilare dichiarazioni di successione e domande di volture catastali, utilizzabile a mano e da un assistente esterno tramite MCP.

L'obiettivo finale è la copertura funzionale del modello telematico SUC13 dell'Agenzia delle Entrate: quadri, dati, casistiche dichiarative, calcoli, stampa e file sottoponibile al controllo ufficiale. Mantieni riconoscibili nomi e riferimenti ministeriali e semplifica il lavoro su molte persone e immobili. Una schermata simile al modello non dimostra la compatibilità del programma.

**L'AI rimane esterna.** Il programma non contiene chat, LLM, estrazione AI, chiavi API AI o abbonamenti AI. Claude può leggere documenti, proporre dati e compilare attraverso MCP. L'app conserva, calcola, controlla e produce elaborati con logica verificabile. Tutte le funzioni dichiarative devono essere utilizzabili anche manualmente.

## Materiali e priorità

Leggi `docs/02_SPECIFICA_E_COLLAUDO.md`, documento operativo di questo progetto, e le fonti in `fonti/`. Le istruzioni si riferiscono alla radice del repository e funzionano anche in un container Linux.

La cartella comprende modello, istruzioni, specifiche, XSD e avviatori JNLP. Il manuale storico commerciale non è incluso né necessario per iniziare. Conserva queste copie di riferimento e sviluppa il codice fuori da `fonti/`. Verifica versioni, contenuto e decorrenze; ricava regole fiscali e tracciato dalle fonti ufficiali. I manuali commerciali forniscono spunti d'uso e le nostre note sono un orientamento, non sostituti delle fonti.

I quattro requisiti imprescindibili sono:

1. **MCP per la compilazione esterna**, con lo stesso archivio e gli stessi servizi utilizzati dall'interfaccia.
2. **Conversione locale PDF → PDF/A**, disponibile come utilità e integrata nel caricamento degli allegati, con verifica del profilo ottenuto.
3. **Acquisizione delle risultanze catastali via Entratel**, il servizio già usato dal committente, e importazione selettiva nei quadri terreni/fabbricati. Non assumere SISTER.
4. **Invio e recupero degli esiti dall'app**, attraverso un collegamento verificato agli strumenti/servizi ufficiali e al profilo dell'intermediario.

## Semplicità dell'architettura

Una sola applicazione locale, un solo motore delle regole, un solo archivio e adattatori distinti per i collegamenti esterni. Assumi inizialmente un PC Windows; multiutenza simultanea e cloud sono estensioni da concordare.

Lo sviluppo può svolgersi nel container Linux: il nucleo, il servizio locale, i parser, i calcoli, MCP, PDF/A, XSD e stampa possono essere sviluppati e collaudati qui. Le prove specifiche Windows e i collegamenti autenticati vanno registrati come da collaudare, senza bloccare il codice indipendente. Non assumere che tutti i componenti ufficiali richiedano Windows: verifica ciò che è eseguibile tramite Java nell’ambiente corrente. Scegli e motiva uno stack dopo le prime prove tecniche. Il professionista deve avviare il programma da un collegamento, senza terminali o installazioni manuali di pacchetti di sviluppo. Se usi un'interfaccia web locale, includila nell'installazione e limita l'accesso alla macchina. Prova MCP con il client Claude effettivo su Windows; chiarisci gli eventuali confini con WSL. La chiusura di Claude non deve corrompere dati o far sparire lo stato delle lavorazioni.

## Comportamento richiesto

**Pratica e compilazione.** Identificativi stabili per persone, beni e documenti, distinti da righi/moduli ministeriali. Quote del defunto e devoluzioni sono dati differenti. Usa decimali e frazioni esatte; distingui assente, zero, non applicabile e da confermare. Mostra errori collegati al campo e calcoli spiegabili, con fonti e versioni.

**MCP.** Esponi capacità e schemi, lettura/creazione della pratica, aggiornamenti strutturati e atomici, documenti, calcolo, verifiche, esportazione, preparazione dell'invio e consultazione dei job/esiti. Evita comandi generici di shell/SQL e modifiche dirette al database. Richieste ripetute non devono duplicare dati; una revisione obsoleta deve produrre un conflitto leggibile. L'assistente deve poter preparare la pratica senza clic manuali obbligatori per ogni campo.

**Documenti.** Tipo EG, beneficiario e finalità vengono indicati dall'utente o da Claude attraverso dati strutturati; il programma può verificare formato, integrità e condizioni documentate, senza fingere di interpretare il contenuto. Conserva originale e derivati, valida PDF/A e dimensioni e collega i documenti ai dati. Un PDF convertito non prova che sia firmato o documentalmente sufficiente.

**Catasto.** Verifica il percorso autenticato reale e i risultati disponibili. Registra provenienza, data e ambito della ricerca, confronta duplicati e proponi l'importazione. Segnala incompletezze, graffati/porzioni non acquisiti e dati da verificare al decesso. L'importazione manuale è una continuità operativa, non il completamento del collegamento richiesto.

**Telematico e invio.** Genera il file effettivo secondo gli XSD coerenti e gli allegati previsti; separa calcoli, validazione XSD, controllo ufficiale, preparazione, trasmissione e ricevute. Prova l'invocazione del controllo e il percorso SUC13 con gli strumenti ufficiali, compreso Entratel Multifile dove utilizzabile; non dedurre una modalità batch dal solo JNLP. Conserva diagnostici e file della versione controllata. Una modifica che cambia il dichiarato invalida gli esiti pertinenti; una nota interna non esportata non deve inutilmente riavviare tutto il flusso.

Credenziali e segreti vengono inseriti nelle impostazioni protette locali, senza attraversare MCP, log o repository. L'assistente prepara l'invio; come impostazione di progetto, la trasmissione effettiva richiede la conferma nell'app sul contenuto e sugli importi. Non eseguire invii reali durante lo sviluppo senza una pratica effettiva verificata e l'autorizzazione specifica del professionista. Dopo un timeout incerto consulta gli esiti prima di qualsiasi nuovo invio.

## Prime prove e sviluppo

**Prima verifica le dipendenze critiche disponibili nell'ambiente:** un documento convertito e validato, una modifica via MCP visibile nell'interfaccia, la modalità concreta di controllo ufficiale e il percorso possibile per catasto/invio. Le prove non disponibili non sono condizioni per iniziare il codice indipendente. Distingui chiaramente ciò che è dimostrato da ciò che richiede accesso autenticato. Se manca un accesso, prepara l'adattatore e il test riprendibile e continua le altre attività. Non inventare endpoint, risposte positive o ambienti di prova.

**Poi realizza un caso completo**, con dati sintetici locali: soggetti, bene immobile, disponibilità finanziaria, allegati, calcoli, stampa, esportazione, riapertura e controllo ufficiale. Deve essere gestibile sia a mano sia da Claude. La specifica stabilisce le evidenze necessarie e come trattare un requisito non ancora verificabile.

**Estendi quindi la copertura** a tutti i quadri/casi SUC13 del perimetro e completa i collegamenti. Tieni una matrice delle funzioni implementate e collaudate; blocca la finalizzazione delle casistiche non supportate senza perdere le bozze. Completa installazione, backup/ripristino e istruzioni essenziali prima di dichiarare il programma utilizzabile.

Albero genealogico, proposta delle quote legittime, importazione PDF di pratiche, modelli accessori e volture separate sono estensioni ordinate per utilità nella specifica. Non rendere il completamento di queste estensioni una condizione per dimostrare il nucleo e le quattro richieste.

REA resta facoltativo per domande tecniche circoscritte che le fonti o le prove ordinarie non risolvono. Verificane il supporto ai JAR desktop se necessario; non inserirlo nelle dipendenze del prodotto. L'indagine su un comportamento non sostituisce la validazione fiscale.

Procedi con le attività reversibili e già comprese nell'incarico senza chiedere conferma per ogni scelta ordinaria. Per decisioni che cambiano il perimetro presenta una proposta concreta e continua le attività indipendenti. A ogni consegna mostra software avviabile, risultati riproducibili e limiti residui. Il risultato atteso è una pratica verificabile e un programma mantenibile, con integrazioni provate e stato di copertura esplicito.


## Ripartenza nel cloud

Esegui `python scripts/verifica_materiali.py`. Poi leggi la specifica e inizia il primo caso completo locale. L’assenza di Windows, di credenziali o del collaudo ufficiale non richiede una nuova conferma per sviluppare le parti indipendenti. Consulta `docs/COLLAUDO_CLOUD_WINDOWS.md` per separare prove locali, simulazioni e prove operative. Non descrivere come integrato ciò che rimane da provare.
