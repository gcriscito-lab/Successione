# Collaudo locale Windows del 2 novembre 2026

Il collaudo usa soltanto dati sintetici, cartelle separate e componenti pubblici. Su richiesta del committente,
nessun accesso Entratel, nessuna credenziale, nessun invio e nessuna ricevuta reale.
Base di partenza: commit `31503df29ad60519fc1b3032f5271020d7d52c6b` sul branch di sviluppo.
Le correzioni descritte sotto sono successive a quella base. Il rapporto della beta 1 e' conservato invariato.

## Esiti misurati

| Prova | Esito e perimetro |
|---|---|
| A11, conversione e verifica indipendente | **passato** sul corpus sintetico Windows: Ghostscript 10.08.0 e veraPDF 1.30.3, profilo PDF/A-1b. 15 originali invariati, analisi attese rispettate; tutti i 9 derivati generati sono conformi secondo veraPDF. |
| A11, controprove | **passato**: ordinario non PDF/A, font non incorporati e falso PDF/A risultano non conformi prima della conversione; il gia' PDF/A e' conforme. Protetti, troncati, non PDF e TIFF sono classificati separatamente. La firma del corpus e' simulata, non e' una verifica crittografica. |
| Resa visiva | **passato** limitatamente alle tre pagine del documento sintetico ordinario: anteprima originale/derivato ispezionata, accenti, impaginazione e immagini conservati. Confronto a 100 dpi: differenza media 0,074-0,126/255 e pixel diversi al massimo 0,09%. Non sostituisce un corpus professionale reale. |
| A01, pacchetto autonomo | **passato** per costruzione offline, verifica del manifest, installazione in cartella isolata con spazi/accenti, dipendenze, SQLite WAL e avvio della GUI col Python incorporato 3.13.17. Firma di python.exe valida, Python Software Foundation; `win32api` importato realmente. Nessun Python di sviluppo necessario all'app installata. |
| A01, aggiornamento | **passato**: reinstallazione del pacchetto su una copia di prova, backup automatico prima della sostituzione, configurazione e dati preservati. Non sono stati creati collegamenti personali sul desktop. |
| A02 | **passato**: backup e ripristino dell'archivio del pacchetto; pratica, revisioni, allegati originali/derivati, XML e job identici. |
| A03, lato server | **passato**: processo MCP del Python incorporato, lettura della pratica creata via HTTP, modifica visibile dalla GUI, conflitto di revisione respinto, chiusura del processo. Il client effettivo Claude resta da collaudare. |
| Percorso integrato del pacchetto | **passato**: upload di PDF sintetici via API della GUI, conversione e verifica veraPDF, XML completo nel perimetro coperto con profilo intermediario, allegati convertiti e controllo ufficiale locale positivo. |
| A10, controllo ufficiale | **passato localmente** su Windows 11, Java 8u511, SUC13 2.3.1 del 11/03/2026. Positivo sintetico senza scarti, con avviso (*) sull'attestazione non richiesta; file DCM prodotto. Due negativi predisposti verificati dai test reali. Nessuna dimostrazione di accettazione telematica. |
| A15, recupero controllo locale | **passato** sul job reale rimasto interrotto nel primo collaudo DCM: nuovo adattatore, input congelato, stesso job, controllo positivo; seconda ripresa senza riesecuzione. Non prova la ripresa dei canali Entratel. |
| A13-A14, A17-A19 reali | **da_collaudare**: esclusi su richiesta del committente; gli adattatori simulati non diventano collegamenti reali per effetto di queste prove. |

Il corpus automatico lascia intenzionalmente `esito_collaudo_a11=da_esaminare`: il presente rapporto registra
l'esame degli esiti, degli hash e dell'anteprima. I rapporti XML originali di veraPDF e gli artefatti SUC13
sono conservati nelle evidenze, insieme ai log e al programma di collaudo del pacchetto.

## Difetti emersi e correzioni

1. **Ghostscript Windows e percorsi oltre 260 caratteri.** L'esecuzione sul deposito dell'app falliva con
   `/undefinedfilename`, mentre lo stesso PDF in un percorso breve veniva convertito. `converti_in_pdfa`
   prepara ora copie temporanee con nomi brevi, anche per il profilo ICC, mantiene `-dSAFER` e concede la lettura
   del solo profilo. Copia il derivato nella destinazione solo dopo successo e rifiuta destinazione uguale
   all'originale. I percorsi dell'utente non vengono interpolati nel programma PostScript. I test del servizio,
   gli originali firmati simulati e la suddivisione che prima fallivano sono stati ripetuti.
2. **DCM e copia di lavoro consumata.** Il controllo ufficiale puo' rimuovere la copia dell'XML di lavoro quando
   produce il DCM. L'adattatore tentava di rileggerla e sollevava FileNotFoundError dopo un controllo riuscito.
   Ora registra esplicitamente il consumo e verifica l'originale congelato nel deposito. Assenza senza DCM,
   alterazione della copia o dell'originale non sono accettate come esito verificabile. Regressione
   `test_dcm_consumo_copia_lavoro_non_perde_input_originale`.
3. **Prerequisiti dei test.** Il test di estrazione usa pypdf quando Poppler e' assente, mantenendo le verifiche
   sulle stringhe e sugli accenti. Il test MCP di suddivisione passa esplicitamente i percorsi Ghostscript/ICC
   al processo figlio: l'SDK non eredita quelle variabili e il vecchio PATH era specifico Linux.
   Il test diretto SUC13 ammette la copia consumata solo se esiste il DCM.

La prima esecuzione PDF/A aveva 4 fallimenti, 45 passati e 1 salto; l'esecuzione completa successiva ha individuato
anche il prerequisito MCP (265 passati, 1 fallito, 1 saltato). Questi esiti non sono nascosti o qualificati come
successi. La suite conclusiva dopo tutte le correzioni ha dato **266 passati, 1 saltato, zero fallimenti**,
2 warning, in 243,65 secondi. Il salto riguarda solo pdftotext facoltativo; i warning riguardano
`add_js` deprecato nei generatori di PDF ostili sintetici. Il log completo e' nelle evidenze.

## Riproduzione e provenienza

Strumenti esterni installati/estratti soltanto in `work/collaudo_windows_20261102/`, senza modificare PATH di sistema,
configurazioni Claude, installazioni fiscali esistenti o cartella dati professionale. Installazione del pacchetto
con `installa.ps1 -Destinazione <cartella-di-prova> -SenzaCollegamenti`; aggiornamento testato sulla stessa copia.

Fonti dei download: [Ghostscript](https://www.ghostscript.com/releases/),
[veraPDF](https://docs.verapdf.org/install/), Python.org/PyPI secondo lock del progetto e JNLP in `fonti/` per i
15 JAR SUC13. Firma Authenticode Ghostscript valida (Artifex Software); firma GPG veraPDF verificata con impronta
`13DD102B4DD69354D12DE5A83184863278B17FE7`, coincidente con quella pubblicata dal produttore. I 15 JAR hanno le
stesse impronte del 1 novembre 2026. Nessun documento o XSD originale modificato.

Suite: `.venv/Scripts/python.exe -m pytest -q -rs --tb=short --basetemp=<nuova-cartella>`, con
`SUCCESSIONI_GS`, `SUCCESSIONI_ICC`, `SUCCESSIONI_VERAPDF`, `SUCCESSIONI_JAVA` (Java 8),
`SUCCESSIONI_CONTROLLI_SUC13`, `SUCCESSIONI_PACCHETTO_WIN` impostati sui percorsi di prova e `PYTHONUTF8=1`.
Corpus ripetibile: `python -m successioni.documenti.corpus_sintetico <cartella-nuova> --collaudo`.
Test del pacchetto: `collaudo_pacchetto.py` nelle evidenze; nessun accesso remoto viene eseguito da questo script.

## Limiti rimasti

Non sono collaudati: documenti professionali reali, CIVIS, accessi Entratel, acquisizione catastale reale,
invio/ricevute, confronto nell'interfaccia Desktop Telematico, client Claude effettivo, collegamenti desktop/menu,
SmartScreen/antivirus come matrice di compatibilita', disinstallazione del programma abituale, WSL.
Poppler/pdftotext non e' installato; il test che estrae indipendentemente le pagine delle specifiche resta saltato.
La diagnosi segnala qpdf come facoltativo assente; la suddivisione usa pypdf. Resta il perimetro fiscale parziale
e il dubbio sugli arrotondamenti gia' dichiarato. Questi esiti locali non autorizzano l'uso su una pratica reale.
