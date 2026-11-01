# Istruzioni operative del progetto

## Fonti presenti e percorsi

Lavora dalla radice di questo repository. I materiali sono in `fonti/`; la specifica è `docs/02_SPECIFICA_E_COLLAUDO.md`. Non cercare una cartella sul Desktop Windows o allegati esterni: i percorsi validi sono relativi al repository.

Esegui subito `python scripts/verifica_materiali.py`, poi leggi `docs/01_PROMPT_CLAUDE_CODE.md` e la specifica. La verifica di base usa soltanto la libreria standard; `--check-xsd` esegue anche la compilazione dello schema se `lxml` è installato.

## Ambito già autorizzato

Il committente ha chiesto lo sviluppo. Procedi con creazione del codice, struttura, dipendenze pertinenti, test, documentazione e commit sul branch di lavoro. Non chiedere un nuovo consenso per iniziare lo scheletro o per ogni scelta ordinaria e reversibile.

Mantieni intatti i documenti sotto `fonti/`. Scegli uno stack proporzionato dopo le prime prove e registra le decisioni. Un solo modello dati e livello applicativo per interfaccia e MCP. L'AI rimane esterna all'app.

## Ambiente di sviluppo e prodotto finale

Puoi sviluppare e verificare nel container Linux anche se il programma finale è destinato a Windows. Lavora subito su archivio, regole, XML/XSD, stampa, PDF/A e server MCP. Testare il server MCP nel cloud è possibile; dimostrare il client effettivo sulla postazione Windows è una prova successiva, da indicare separatamente.

Non classificare tutti i componenti ufficiali come Windows-only senza verifica: il materiale fornito è Java/JNLP. Esamina le modalità realmente utilizzabili e documenta limiti e dipendenze del controllo. L'esistenza di Java da sola non prova che il controllo funzioni.

Le prove Windows e i servizi autenticati non bloccano le attività indipendenti. Prepara adattatori e test riprendibili; marca i requisiti come `da collaudare` quando manca una prova reale. Le simulazioni servono ai test e non dimostrano interoperabilità con l'Agenzia.

## Primo risultato atteso

1. Verifica i materiali e registra versioni/fonti e incognite concrete.
2. Scegli la base tecnica e crea un primo percorso completo con dati sintetici locali.
3. Dimostra creazione/salvataggio/riapertura della stessa pratica da interfaccia e MCP, allegati, calcolo documentato ed esportazione verificata secondo la copertura realizzata.
4. Esegui le prove disponibili, registra gli esiti e continua l'estensione prevista dalla specifica.

Non limitarti a un altro piano generale e non concludere che mancano tutti i materiali senza leggere il repository. Non dichiarare passati i controlli ufficiali se non eseguiti. Non ricavare regole fiscali dalla memoria o da risposte simulate.

## Credenziali e invii

Nessun invio reale né dichiarazione sintetica ai servizi di produzione durante lo sviluppo. Il successivo collaudo operativo riguarda una pratica effettiva verificata e autorizzata dal professionista. Credenziali e certificati vengono configurati sulla postazione appropriata, senza inserirli in chat, codice, log o repository.

## Documenti di riferimento

- `docs/01_PROMPT_CLAUDE_CODE.md`: obiettivo e percorso di sviluppo.
- `docs/02_SPECIFICA_E_COLLAUDO.md`: requisiti, priorità e accettazione.
- `docs/COLLAUDO_CLOUD_WINDOWS.md`: distinzione fra prove disponibili e prove operative successive.
- `fonti/manifest.json`: file di riferimento e impronte.

In caso di differenza tra un precedente messaggio e queste istruzioni, usa i percorsi di questo repository e l'esplicita separazione fra sviluppo cloud e collaudo finale Windows. Le quattro funzioni richieste restano l'obiettivo finale.
