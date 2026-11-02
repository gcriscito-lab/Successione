# Correzioni della revisione esterna Codex

Aggiornamento successivo: i collaudi locali Windows del 2 novembre, con veraPDF e SUC13 reali,
sono in `docs/COLLAUDO_WINDOWS_CODEX_20261102.md`. I risultati sotto descrivono la verifica del 1 novembre.

1 novembre 2026. Base: `2e2b503d1bb4a22c6ae499600846e2c70d5bdb56`, branch
`claude/successioni-dichiarazioni-app-fhcwbe`. Il rapporto originale
`REVISIONE_ESTERNA_CODEX.md` resta invariato e descrive quella beta, prima delle correzioni.
Questo documento registra l'implementazione e le prove dell'autore delle correzioni;
non costituisce una seconda revisione indipendente o un'approvazione per uso professionale.

## Interventi ed evidenze

| Rilievo | Correzione | Prova nuova e stato |
|---|---|---|
| CE01 | Il servizio passa al modulo XML gli allegati della stessa pratica, dopo verifica di percorso, dimensione e SHA-256, e i campi dell'impegno a trasmettere. Avvisi propagati a API/MCP/GUI. Profilo intermediario disponibile nella scheda File. | `test_ce01_*`, test MCP `test_ce01_mcp_esporta_caso_completo_intermediario_con_allegati`, GUI `runExport`: **passato** localmente. Provati dichiarante, intermediario, documento estraneo/alterato e avvisi visibili. |
| CE02 | Snapshot dei campi inviati, pulizia dei soli valori confermati; modifiche sopraggiunte conservate. ID stabili per righe nuove; eliminazione pulisce il relativo buffer dopo la conferma del server. Salvataggi concorrenti e cambio pratica durante il salvataggio bloccati; ripristino revisioni protetto dai buffer pendenti. | `tests/e2e/gui_regressioni.js`, funzione `run`: **passato** nel browser, con risposta ritardata, nuova riga, eliminazione e risposte 422/409. |
| CE03 | Le configurazioni non coperte dalla verifica delle quote di legge producono anche un blocco di completezza, oltre all'avviso. La bozza tecnica rimane esplicitamente incompleta. Non sono state inventate nuove regole per fratelli o parenti collaterali. | `test_ce03_quote_non_verificate_non_finalizzabili_ma_bozza_con_avviso`: **passato**, incluso germano/unilaterale del rilievo. |
| CE04 | Con imposta di successione dovuta, una presentazione oltre il termine ordinario non e' finalizzabile, con entrambi i codici di pagamento. Anche il termine per un decesso il 29 febbraio richiede verifica esplicita. Le tempestive conservano il calcolo e la distinzione fra pagamento differito e contestuale. | `test_ce04_*`: **passato**. Il caso con imposta 44.132 euro non puo' piu' essere finalizzato come tardiva. Nessun calcolo di ravvedimento introdotto. |
| CE05 | Verifica dei 5 MB prima del Base64 e della fornitura sull'XML effettivo con allegati, dopo lo schema e prima della pubblicazione. Superamento blocca completo e bozza. | `test_ce05_*`: **passato**. Test oltre 6 MB e prova con soglia fornitura ridotta, usando la misura reale; test dimensionali preesistenti conservati. |
| CE06 | Ripristino preceduto da controllo SQLite, riferimenti e impronte di allegati/elaborati dei job. Copia preparata e ricontrollata separatamente; pubblicazione solo su destinazione nuova, senza client aperti; errore di copia non popola il DB. Rifiuto se la destinazione contiene altri file. | `test_ce06_*`: **passato**, con originale mancante/alterato, XML del job assente, errore di copia, ripetizione riuscita e file estranei preservati. |
| CE07 | La route statica rifiuta separatori Windows, drive e percorsi che risolvono fuori dalla cartella statica. Autenticazione, Host e Origin restano attivi. | `test_ce07_static_non_legge_fuori_directory` e test web esistenti: **passato** su Windows. |
| CE08 | Lock del singolo job rilasciato dal sistema alla morte del processo. Input congelato prima dell'esecuzione. Recupero di un controllo locale interrotto, stesso job e hash; cartella di lavoro diversa per ogni tentativo, senza riusare output Java orfani. Nessuna modifica ai canali di invio. | `test_ce08_*`: **simulazione** del componente, con interruzione e concorrente ancora attivo. Il recupero e l'idempotenza passano nei test; controllo ufficiale reale **da_collaudare**. |
| CE09 | `.gitattributes` disabilita la conversione di testo per entrambe le cartelle di evidenze ufficiali. Ripristinati i byte originali dei blob Git, senza cambiare XML, diagnostici o manifest. | `test_ce09_*`, confronti A10 e manifest esistenti: **passato**. Anche un nuovo checkout dei 22 file delle due cartelle, con `core.autocrlf=true`, e' identico ai blob Git. Nessuna nuova esecuzione del controllo ufficiale. |
| CE10 | L'helper E2E usa assert; il runner chiude il browser nel finally e termina con codice non zero in caso di errore. | `test_ce10_assert_e2e_negativo_termina_con_errore`: **passato** su un processo Node reale. |

Ulteriore correzione di test: l'avviatore della venv Windows puo' avere un PID diverso dal server figlio.
Il test confronta il PID registrato con quello del server che risponde a `/api/info`; la chiusura
ferma l'albero del processo creato dal test. Non e' una prova del pacchetto autonomo distribuito.

## Fonti e scelte di copertura

- CE01: `fornituraSUC13_v1.xsd`, elementi `QuadroEG/AlberoGenealogico` e
  `Frontespizio/ImpegnoATrasmettere`; istruzioni Fascicolo I, pp.49 e 51.
- CE03: Fascicolo I, p.69, Allegato 5; annotazioni `Devoluzione/Quota` nei quadri EB/EC/ER.
  La verifica automatica resta limitata a figli, coniuge, coniuge e figli.
- CE04: Fascicolo I p.6, termine ordinario di dodici mesi; p.48, EF18ter colonna 1 e inclusione in EF19.
  Il blocco e' prudenziale per le tardive **con imposta di successione dovuta**; non implementa sospensioni,
  decorrenze particolari, sanzioni o interessi. Non dichiara verificate le tardive con imposta non dovuta.
- CE05: `Specifiche_SUC13_20250702.pdf`, p.7 §2.3 (5 MB per allegato), p.3 §1
  (40 MB compressi per fornitura). MB decimali e DEFLATE sono scelte esplicite gia' documentate
  in `documenti/dimensioni.py`: l'algoritmo/contenitore del canale reale resta da collaudare e viene
  segnalato negli avvisi. Non si attesta l'accettazione dimensionale da Entratel.

Le fonti originali in `fonti/` e i dati delle registrazioni ufficiali restano invariati.
Non e' stato risolto il dubbio noto 82,0875/82,08 e non sono stati aggiunti quadri esclusi.

## Verifiche eseguite

Ambiente: Windows, PowerShell, Python 3.14.4 nella venv del repository, Node e browser Playwright.
Archivi sintetici separati. Nessuna credenziale, trasmissione o sessione autenticata dell'Agenzia.

Comandi dalla radice del repository:

```powershell
.\.venv\Scripts\python.exe scripts/verifica_materiali.py --check-xsd
.\.venv\Scripts\python.exe -m pytest -q -rs --basetemp=../pytest_codex_correzioni_finale_20261101_2205
node --check src/successioni/static/app.js
node --check tests/e2e/gui_flusso.js
node --check tests/e2e/gui_regressioni.js
git diff --cached --check -- . ':(exclude)docs/REVISIONE_ESTERNA_CODEX.md'
```

Risultati: **232 passati, 34 saltati, zero fallimenti**, 1 warning, in 70,19 secondi.
I 34 salti dipendono da Ghostscript (25), pdftotext (1), controllo/componenti ufficiali (6),
veraPDF insieme a Ghostscript (1) e pacchetto Windows costruito (1). Il warning riguarda
`PdfWriter.add_js` deprecato nel generatore del corpus PDF ostile sintetico, non il prodotto.
23 fonti integre (8 PDF, 13 XSD, 2 JNLP), schema e dipendenze compilati;
verifiche sintattiche JavaScript e whitespace passate.
Il controllo whitespace esclude il rapporto storico, conservato byte per byte con la sua riga vuota finale.
Un tentativo con la directory temporanea predefinita di Windows non ha potuto preparare i test
per `PermissionError` sulla cartella `pytest-of-Giuseppe Criscito`: ripetuto su un percorso nuovo nel workspace.

Browser: server locale `127.0.0.1:8827`, archivio sintetico dedicato, funzioni `run` e `runExport`
del file `tests/e2e/gui_regressioni.js` eseguite tramite il runner Playwright disponibile.
Il runner non offre `require`: il corpo delle funzioni e' stato eseguito con assert equivalenti per
i tipi verificati (stringhe, booleani, array e oggetti semplici). Il percorso CLI Node di questo file
non e' stato eseguito. L'helper assert negativo CE10 e' invece stato provato in un vero processo Node.
L'export da GUI ha restituito `generato=True`, `completo=True`, profilo intermediario salvato e avvisi visibili.

## Limiti residui

Rimangono **da_collaudare**: veraPDF/PDF-A, componenti ufficiali e Desktop Telematico,
pacchetto Windows autonomo, client Claude effettivo, catasto Entratel, invio e ricevute.
I test con esecutore finto restano **simulazione**. Il ripristino richiede una destinazione nuova
senza altri client: non e' una sostituzione a caldo di un archivio in uso e non simula un arresto
del sistema durante lo scambio finale delle cartelle. Nessun esito locale e' qualificato come
dichiarazione pronta, approvata o trasmessa. La matrice aggiornata distingue integrazione,
regole parziali, registrazioni storiche e verifica ufficiale.
