# Correzioni e funzioni mancanti — 3 novembre 2026

## Risultato

Corretti i sei difetti riprodotti nella review `REVISIONE_ESTERNA_CODEX_20261103.md`. Aggiunte funzioni per completare il percorso locale di lavoro. **Non è raggiunta la copertura del 100% delle successioni né il collaudo del percorso telematico reale.** I limiti sotto richiedono ulteriore sviluppo e prove: non si risolvono cambiando un'etichetta di stato.

I documenti ministeriali e le pratiche professionali non sono stati modificati. Le prove di questa consegna usano un archivio sintetico separato in `build/`. Nessun invio reale, accesso Entratel o credenziale.

## Sei difetti corretti

| Rilievo | Comportamento aggiornato | Prova |
|---|---|---|
| R01, perdita delle agevolazioni XML | I campi significativi non letti nei quadri dichiarati importabili causano un errore esplicito prima della creazione. Un XML con `Agevolazioni=P` non viene trasformato silenziosamente in una pratica senza agevolazione. **Questo non implementa il calcolo della prima casa.** | `test_nessuna_perdita_silenziosa_dei_campi_xml`, tre varianti |
| R02, continuazioni | Le devoluzioni dei righi successivi sono collegate allo stesso bene, anche attraverso il cambio di modulo; identificativi delle devoluzioni unici. Una continuazione troncata viene respinta. | andata/ritorno XML con quattro e sette figli e tre beni; test negativo |
| R03, frontespizio | Buffer condiviso con il salvataggio generale e Ctrl+S; cambio quadro e digitazione durante HTTP conservano i dati. | Chromium, modifica durante risposta lenta, rilettura del dato salvato |
| R04, prova che blocca il reale | Tentativi simulati e operativi distinti nel vincolo contro i duplicati; modalità persistita, verificata in ripetizione e riconciliazione. | simulazione seguita da percorso manuale sulla stessa pratica; rifiuto di modalità errata |
| R05, riconciliazione GUI | Il dettaglio del tentativo mostra istruzioni e stato reali; modulo per protocollo/evidenza e per assenza verificata dell'invio; riconciliazione simulata separata. La lista mostra prima la copia più recente. | test browser fino alla registrazione del protocollo sintetico |
| R06, due commit disallineati | Tentativo finale e copia sono aggiornati nella stessa transazione; recupero idempotente per archivi precedenti già disallineati. | guasto iniettato tra le due scritture, rollback, ripresa senza secondo invio; tre stati finali preesistenti |

Corretto anche il test Windows dipendente dalla presenza di Ghostscript sul PC: il filesystem di prova ora è isolato. Il fallimento precedente non dimostrava un errore fiscale.

## Funzioni locali aggiunte

- **Scarica XML:** restituisce una versione precisa del file con controllo dell'impronta e dell'appartenenza alla pratica.
- **Scarica copia congelata:** permette il passaggio manuale del file effettivamente confermato agli strumenti ufficiali.
- **Stampa prospetto:** pagina stampabile/salvabile in PDF dal browser, ricavata dagli stessi byte XML, con revisione e SHA-256. Include i dati dei quadri senza stampare il contenuto Base64. È un prospetto di controllo, **non il modello ministeriale per presentazione e sottoscrizione**.
- **Maschere strutturate:** superficie dei terreni, ripartizione delle passività, estremi di trascrizione/registrazione per EI; indicazione documentata dell'handicap. Dati aziendali di deposito e camera di commercio, conformità delle copie allegate e luogo del decesso accessibili dalla GUI.
- **Ricevute:** acquisizione manuale dell'originale, classificazione ed esito scelti dall'utente, associazione al tentativo/protocollo della pratica, download dell'originale con verifica dell'hash. Registrazione, pagamento e volture conservano stati separati: un pagamento negativo non cancella la registrazione. La raccolta autenticata automatica non è implementata.
- **Importazione:** riconoscimento del ruolo del legatario da `TipoSoggetto=2`, estremi del testamento dal frontespizio, conservazione del flag handicap; rifiuto DOCTYPE e numeri non finiti. File XML/SUC selezionabili dalla GUI. Nuovo strumento MCP per importare dalla sola cartella d'ingresso.
- **Stati:** riepilogo trasmissione collegato ai record persistenti; indicazione esplicita delle prove simulate; importo totale e CF del fornitore della copia congelata ricavati dall'XML.
- **Avvio sorgenti:** `Avvia-programma-aggiornato.cmd`, dalla radice di questo repository, usa `.venv` e l'avviatore esistente. Non installa dipendenze né aggiorna un eventuale pacchetto precedente.

## Cosa manca per un prodotto completo

Inventario ricavato dal codice e da `MATRICE_COPERTURA.md`, `02_SPECIFICA_E_COLLAUDO.md` e `PIANO_PROSSIMI_PASSI.md`. La presenza di un quadro non significa copertura di tutti i suoi campi e casi.

| Priorità | Area da completare | Criterio concreto per chiuderla |
|---|---|---|
| Alta | Prima casa: P/Z/X/Y, diritto di abitazione, dichiarazioni EH e imposte EF collegate | Casi distinti dalle fonti locali, dati conservati in GUI/import/export, calcolo verificato indipendentemente e controllo SUC13 locale su positivi e negativi |
| Alta | Titoli esenti EO tipo 3, componenti esenti e relativi totali/base | Nessuna inclusione impropria nel patrimonio imponibile; prove per tipi esenti e non esenti |
| Alta | Più comuni/circoscrizioni, EF15/EF16, casi immobiliari non coperti | Fonte tracciabile per l'associazione comune/conservatoria, conteggi verificati su comuni nella stessa e in diverse circoscrizioni; niente tabella inventata |
| Alta | Riduzioni art. 25, precedenti successioni, estero e detrazioni | Valori intermedi e arrotondamenti confrontati con fonti e componente; soluzione documentata del dubbio 82,0875/82,08 |
| Alta | Sostitutive, precedenti versamenti, crediti, rateazione, tardive e relativi accessori | Riferimenti alla precedente dichiarazione, corretta differenza da versare, versioni e decorrenze, test del controllo sui casi supportati |
| Alta | Qualifiche multiple, rappresentanti/cariche diverse da 1, rappresentazione, trust, enti, rinunce, EH II-IV | Anagrafiche e rapporti completi, franchigie/attribuzioni coerenti, firme/documenti richiesti, moduli e continuazioni verificati |
| Media | Casi residui dei beni | Immobili aziendali e inventario, graffati e rendita proposta, beni/territori esteri, più mezzi e più moduli EH; tutti con regole e test dedicati |
| Media | Importazione di tutti i quadri e formati | Attualmente si importano EA/EB/EC/ED/ER e parte del frontespizio; altri quadri sono dichiarati omessi. Servono import completo, conservazione degli allegati EG ed eventuale compatibilità `.diz` dimostrata. Un `.suc` selezionabile non dimostra supporto a formati proprietari diversi dall'XML |
| Alta | Stampa ministeriale | Modello ufficiale completo con ripetizioni, allegati, firme e controlli di impaginazione, dalla stessa versione dell'XML. Il nuovo prospetto non chiude questo requisito |
| Alta | Acquisizione catastale Entratel | Collegamento autenticato documentato e autorizzato, risultati originali tracciati, selezione/confronto duplicati e stato al decesso; oggi resta l'adattatore simulato |
| Alta | Controllo/preparazione telematica end-to-end | Configurazione locale dei componenti, DCM/autenticazione ufficiale dove necessari, prova sul PC di destinazione della versione corretta. I doppi usati nei test di invio non attestano questo requisito |
| Alta | Invio e raccolta autenticata delle ricevute | Integrazione con strumenti ufficiali e ambiente di sicurezza, pratica reale verificata e autorizzata, riscontri originali, pagamento e volture separati. Oggi funziona il percorso manuale tracciato; non è un invio automatico |
| Media | Distribuzione aggiornata e collaudo operativo | Ricostruire il pacchetto autonomo includendo queste modifiche, installazione/aggiornamento e recupero su secondo PC, client MCP effettivo, antivirus/SmartScreen; corpus documentale professionale autorizzato |

Non viene assegnata una percentuale di conformità: non esiste qui un denominatore verificato di tutti i casi fiscali e operativi. I casi fuori perimetro devono continuare a bloccare l'esportazione completa.

## Verifica e riproduzione

Test Python: `.venv/Scripts/python.exe -m pytest -q -rs --tb=short --basetemp=build/fix_final`.

Test browser: avviare il server `tests/e2e/server.py` con `SUCCESSIONI_DATA` uguale al percorso assoluto `build/gui_fix_data`, poi eseguire:

```
.venv/Scripts/python.exe tests/e2e/prepara_review.py
node tests/e2e/gui_review_20261103.js
node tests/e2e/gui_regressioni.js
```

Serve Playwright/Chromium disponibile al runner Node; nella sessione è stata usata l'installazione già presente sul PC, senza aggiungere dipendenze al prodotto. `prepara_review.py` crea soltanto fixture sintetiche e un doppio di controllo: non effettua un controllo ufficiale o un invio reale. Screenshot in `build/gui_review_20261103.png` e `build/stampa_review_20261103.png`.

Esiti della verifica:

- Suite completa finale: **580 passati, zero fallimenti, 28 saltati**, 1 warning, 251,67 secondi. I salti riguardano Ghostscript/veraPDF non impostati nel processo pytest, `pdftotext` e il pacchetto autonomo non presente in questa copia. Il warning riguarda `pypdf.add_js` nel corpus sintetico ostile.
- Entrambi i runner Chromium sono passati: il precedente (concorrenza, risposta lenta, eliminazione, 422/409) e il nuovo (frontespizio, cambio quadro, Ctrl+S, digitazione durante HTTP, superficie, istruzioni, protocollo, acquisizione/scaricamento ricevuta originale e prospetto con lo stesso SHA-256). Nessun errore JavaScript osservato. Nel nuovo runner è stato corretto anche il popolamento delle opzioni degli esiti delle ricevute emerso durante il primo collaudo.
- `git diff --check`, controllo sintattico di `app.js` e verifica delle 23 fonti: passati. Il percorso dell'avviatore e l'import Python puntano a questi sorgenti aggiornati.
- Screenshot del prospetto esaminato: intestazione, valori, quote, quadri e testi lunghi leggibili, contenuto Base64 sostituito da un richiamo all'allegato. Non è una verifica della stampa ministeriale.

Verifiche aggiuntive con gli strumenti già installati, impostati esplicitamente solo nel processo di test:

- Ghostscript 10.08.0 e profilo `srgb.icc`: **53 passati, zero fallimenti, 2 saltati**, 120,11 secondi, nei moduli corpus, dimensioni, verifiche strutturali, TIFF, PDF/A e MCP. I due salti di questa esecuzione sono veraPDF non ancora impostato e `pdftotext`.
- VeraPDF (`C:\veraPDF\verapdf.bat`) e Java/SUC13 configurati: **4 passati, zero salti o fallimenti**, 36,97 secondi. Comprendono `test_a11_collaudo_reale_verapdf` e tre esecuzioni del componente ufficiale SUC13 locale (positivo sintetico e due negativi predisposti). Sono controlli locali, non invii o accettazioni telematiche.
- Delle 28 prove inizialmente saltate sono state recuperate **26**; restano non eseguiti il controllo del pacchetto autonomo da ricostruire e la prova con `pdftotext` non disponibile. I conteggi delle esecuzioni aggiuntive si sovrappongono alla suite completa e non vanno sommati come test distinti.

Il server browser di collaudo viene arrestato a fine verifica. Per usare la versione aggiornata aprire `Avvia-programma-aggiornato.cmd`; una finestra dell'app o un'installazione precedente già aperta deve essere riavviata per caricare il codice nuovo.
