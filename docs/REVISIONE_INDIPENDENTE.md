# Revisione indipendente (ripresa)

- Revisore: agente indipendente, non partecipante allo sviluppo; sola lettura su codice, test e documenti altrui.
- Commit esaminato: `08c358792d7b81d91a51b91a353d25e157105ee5` (HEAD all'avvio; snapshot WIP dichiarato "non ancora verificato né integrato"). Durante la revisione il coordinatore ha creato `a3d22666dfd94b379478b63241e26999911e8df1`, che modifica solo documenti (`docs/REVISIONE_INDIPENDENTE.md`, `docs/STATO_area4.md`, `docs/regole/STATO_area1.md`): il codice in `src/` e `tests/` esaminato è identico nei due commit. Il lavoro non ancora committato di altri agenti (es. `telematico/quadri_efgh.py`, modifiche a `telematico/supplemento.py`, `packaging/`, `scripts/windows/`) è escluso salvo dove indicato.
- Data: 2026-11-01.
- Ambiente: container Linux, Python 3.13.
- Stato del documento: IN CORSO (compilato man mano; se la sessione si interrompe, i rilievi già scritti restano validi).

Legenda gravità: bloccante / alta / media / bassa. Legenda esiti (da `docs/COLLAUDO_CLOUD_WINDOWS.md`): passato, fallito, da_collaudare, simulazione.

## Esito

(da completare a fine revisione)

## Quadrature e verifiche eseguite

- `python scripts/verifica_materiali.py` → `OK: 23 fonti verificate (8 PDF, 13 XSD, 2 JNLP)`.
- `python3 -m pytest -q` (intera suite, commit sopra) → **192 passati, 3 saltati** in 81 s. Saltati: `test_collegamenti_controllo.py:213` e `test_elaborati.py:90` (JAR del controllo SUC13 non configurati, `SUCCESSIONI_CONTROLLI_SUC13`), `test_documenti_corpus.py:177` (veraPDF assente). Strumenti presenti nel container: Ghostscript 10.02.1, qpdf, Java 21, pdftotext; veraPDF assente.
- Script di riproduzione del revisore (fuori dal repository): `/tmp/claude-0/-home-user-Successione/45d852c4-b150-580d-8ea9-929683237c63/scratchpad/riproduci1.py` (archivio temporaneo, dati sintetici di `tests/telematico_casi.py`).

## Rilievi

Ordinati per gravità all'interno di ciascun blocco; i rilievi sono stati aggiunti man mano (la numerazione R* è quella di lavoro).

### Alta

**R4 — Un'operazione `upsert` può cambiare l'`id` di un elemento, creare id duplicati e riassegnare in silenzio le devoluzioni a un'altra persona.** (fatto verificato)
- Evidenza: `src/successioni/servizio.py:254-262` copia ogni chiave di `campi` nell'elemento, compresa `id`; `ID_VALIDO` (riga 248) è controllato solo sull'`id` dell'operazione, non su `campi["id"]`; `schema.valida_forma` (`schema.py:88-90`) salta `id` e non controlla l'unicità.
- Riproduzione (`riproduci1.py`, R4): crea `p_zzzz0001` (ruolo `altro`), poi `upsert id=p_zzzz0001 campi={"id":"p_anna0001"}` → accettato, revisione 5, id persone `['p_defunto1','p_anna0001','p_luca0001','p_anna0001']`; poi `upsert id=p_anna0001 campi={"id":"QUALSIASI COSA!"}` (canale gui) → accettato: la vera Anna diventa `QUALSIASI COSA!` e le devoluzioni `persona_id=p_anna0001` puntano ora alla persona «Z» con ruolo `altro`. La verifica interna segnala solo `CF_MANCANTE`.
- Impatto: rompe la garanzia di identificativi stabili (spec. §5, A05) e può attribuire beni a un soggetto diverso senza alcun errore; raggiungibile da MCP (`aggiorna_pratica`) e dall'API della GUI.
- Correzione: rifiutare `id` e `_origine` dentro `campi` (DatiNonValidi), e in `valida_forma` verificare formato e unicità degli id per collezione.

**R3 — La protezione dei campi «calcolato» contro le modifiche via MCP è aggirabile passando `_origine` in `campi`; un `_origine` non dizionario provoca un'eccezione non gestita.** (fatto verificato)
- Evidenza: `servizio.py:254-262`: il controllo `elemento["_origine"].get(k) == "calcolato"` avviene campo per campo; la chiave `_origine` non è esclusa, quindi `campi={"_origine": {}, "valore": "1"}` azzera le marcature e la modifica successiva passa. Con `campi={"_origine":"x"}` → `TypeError: 'str' object does not support item assignment` (non è un `ErroreServizio`: nella GUI diventa 500, in MCP un errore generico).
- Riproduzione (`riproduci1.py`, R3/R5): modifica diretta respinta (`DATI_NON_VALIDI ... campo calcolato non modificabile da MCP`); con `_origine:{}` accettata, `valore` = `1`, `_origine` = `{'_origine': 'proposto_assistente', 'valore': 'proposto_assistente'}`.
- Impatto: oggi nessun codice marca campi come `calcolato`, quindi l'effetto è latente; ma la regola della spec. §8 («i valori derivati non possono essere sovrascritti attraverso MCP») non è garantita, e la provenienza può essere falsificata.
- Correzione: come R4 (chiavi riservate vietate in `campi`), test dedicato.

**R1 — «Finalizzabile nel perimetro supportato» è mostrato per pratiche che l'esportazione dichiara incomplete (EF, EG, EH obbligatori e non generati).** (fatto verificato)
- Evidenza: `servizio.verifica` (`servizio.py:198-206`) calcola `finalizzabile = not errori` usando solo forma, coerenza e `quadri.rilievi_quadri`; `quadri.PREDEFINITI` (`quadri.py:184`) non comprende EF/EH, e un quadro non selezionato non genera rilievi. `esporta.quadri_obbligatori` (`telematico/esporta.py`, metodo `quadri_obbligatori`) invece rende EF/EG/EH obbligatori. La GUI mostra la frase in barra di stato (`static/app.js:96`) e nel pannello controlli (`app.js:249`).
- Riproduzione (`riproduci1.py`, R1) sul caso sintetico `caso_completo()`: `verifica.esito ok finalizzabile True rilievi []` mentre `esporta` → `completo False generato False quadri_mancanti ['quadro[EF]','quadro[EG]','quadro[EH]']`.
- Impatto: l'utente e l'AI (strumento MCP `stato_quadri`) leggono «finalizzabile» per una dichiarazione che non può essere prodotta; contraddice A20 («casi mancanti bloccati alla finalizzazione») e §1.
- Correzione: far dipendere `finalizzabile` anche dai quadri obbligatori per le annotazioni XSD (stessa funzione dell'export) e dall'esito di `esporta_xml` (errori/non_supportato), oppure rinominare l'indicatore in «nessun rilievo interno».

**R2 — La scelta «Dichiarazione sostitutiva» è ignorata: non blocca la finalizzazione, l'XML dichiara `PrimaDichiarazione` e il calcolo la tratta come prima dichiarazione.** (fatto verificato)
- Evidenza: la GUI salva `opzioni.tipo_dichiarazione` (`app.js` `renderFront` e procedura guidata) e scrive «la sostitutiva non è finalizzabile»; ma nessun controllo legge `tipo_dichiarazione` (`grep` in `servizio.py`, `schema.py`, `quadri.py`, `telematico/`), il frontespizio esportato scrive sempre `PrimaDichiarazione=1` (`esporta.py`, `frontespizio`), e `supplemento.chiavi_non_gestite` controlla solo `opzioni.telematico`, quindi la chiave non finisce nemmeno in `non_supportato`.
- Riproduzione (`riproduci1.py`, R2): con `tipo_dichiarazione=sostitutiva` → `verifica finalizzabile True []`; bozza tecnica generata con `PrimaDichiarazione`, `non_supportato: []`; `calcola` → `completato 0`.
- Impatto: un dato dichiarativo scelto dall'utente si perde in silenzio nel file; l'affermazione dell'interfaccia è falsa; contraddice la regola «nessuna perdita silenziosa» dichiarata in `esporta.campi_non_esportati`.
- Correzione: rilievo bloccante in `verifica` e `non_supportato` in `esporta_xml` per `tipo_dichiarazione != originaria`; più in generale segnalare ogni chiave di `opzioni` non gestita dall'export (oggi solo `opzioni.telematico` è sorvegliata).

**R6 — Il backup non comprende i file elaborati (XML esportati): dopo il ripristino lo stato dice «aggiornato» ma il file non esiste; non esiste un comando di ripristino.** (fatto verificato)
- Evidenza: `archivio.py:106-121` copia solo `archivio.sqlite3` e `allegati/`; `elaborati.py:62-67` scrive l'XML in `elaborati/<pratica>/<sha>.xml` (fuori da `allegati/`) e il job registra quel percorso. `cli.py` offre `backup` ma nessun `ripristina`; il test A02 (`tests/test_servizio.py:101-108`) confronta solo dati e revisioni, non allegati né elaborati.
- Riproduzione (`riproduci2.py`): export bozza → `elaborati/pr_…/3d14….xml`; backup → contenuto `['allegati','archivio.sqlite3']`; sull'archivio di backup `stato_elaborati` → `export aggiornato`, `file esiste: False`; `controllo_ufficiale_pratica` → `NON_TROVATO file da controllare inesistente`. Gli allegati invece sono copiati (1 allegato, file presente).
- Impatto: A02 («pratica e allegati identici dopo riavvio e ripristino») non è dimostrata; lo stato degli elaborati dopo un ripristino è falso. Gli artefatti dei collegamenti sono invece nel deposito `allegati/` (`collegamenti/base.py:336-347`) e quindi inclusi.
- Correzione: salvare gli XML nel deposito content-addressed (come `DepositoArtefatti`) o includere `elaborati/` nel backup; far verificare a `stato_elaborati` l'esistenza e l'impronta del file; aggiungere `ripristina` con verifica d'integrità (impronte di tutti gli allegati) e un test A02 che copra allegati, elaborati e job.

### Media

**R7 — Il controllo interno delle devoluzioni raggruppa per diritto «grezzo» e contraddice l'esportazione.** (fatto verificato)
- Evidenza: `schema.controlli_coerenza` (`schema.py:107-122`) somma le quote per `(bene_id, diritto)` come stringa; l'export normalizza il codice (`esporta.codice_enum(..., alias_descrizione=True)`), quindi `"1"` e `"proprieta"` sono lo stesso diritto per l'export ma due gruppi per il controllo interno. Il controllo interno non confronta neppure il diritto devoluto con quello del defunto.
- Riproduzione (`riproduci2.py`, R7): casa devoluta 1/2 con diritto `"1"` e 1/2 con `"proprieta"` → `verifica`: due `DEVOLUZIONI_INCOMPLETE` (1/2 < 1), non finalizzabile; `esporta` bozza → generato, nessun errore.
- Impatto: rilievi spuri (o mancati) diversi tra GUI/MCP e file; due implementazioni della stessa regola.
- Correzione: un'unica funzione di normalizzazione dei codici diritto usata da schema e export (o validare il campo `diritto` sull'enumerazione XSD già al salvataggio).

**R8 — La validazione al salvataggio accetta date impossibili e la verifica interna le dichiara senza rilievi.** (fatto verificato)
- Evidenza: `schema.py:15` `DATA_ISO = ^\d{4}-\d{2}-\d{2}$` (solo forma). Il controllo vero è solo nell'export (`formati.data_iso`).
- Riproduzione (`riproduci2.py`, R8): `data_decesso="2025-02-30"` → `verifica: ok True []`; export → `VALORE_NON_VALIDO … day is out of range for month`.
- Impatto: la data del decesso decide decorrenza, quadri obbligatori e calcolo; una data invalida passa i controlli mostrati all'utente e all'AI (aggrava R1). Analogo per il codice fiscale (`schema.py:14`, solo `[A-Z0-9]{16}`, nessun carattere di controllo né 11 cifre per gli enti).
- Correzione: validare le date con `date.fromisoformat` e il CF con il pattern XSD (`formati._CF`) e, se si vuole, il carattere di controllo (già in `telematico/identificativi.py`).

**R9 — API della GUI: input malformati producono HTTP 500 invece di 422; l'host `testserver` è ammesso anche in produzione.** (fatto verificato)
- Evidenza: `web.py:38-49` intercetta solo `ErroreServizio`; `web.py:86, 96, 106, 111` usano `b["..."]`/`int(...)` senza gestione; `servizio._applica` (`servizio.py:233-273`) assume che ogni operazione sia un dizionario. `web.py:25`: `host_ok` contiene `"testserver"` (valore del client di test di Starlette) in ogni avvio.
- Riproduzione (`riproduci3.py`, client Starlette su `127.0.0.1:8765`): JSON malformato, `revisione_attesa` mancante, `revisione=abc`, operazione `"x"`, `_origine` stringa → tutti `HTTP 500 'Internal Server Error'`; `Host: testserver` → `200`.
- Impatto: messaggi d'errore inutilizzabili per l'utente e per i client (la spec. §6 chiede codice, campo e percorso); il nome host di test allarga senza motivo la difesa contro DNS rebinding (rischio basso: un nome a etichetta singola è difficilmente risolvibile da un attaccante, e serve comunque il token).
- Correzione: validare il corpo delle richieste (schema) e convertire `KeyError/ValueError/TypeError` in 422 con codice; rendere `testserver` un parametro dei soli test.

**R10 — Con «devoluzione per legge» (unico caso supportato) l'export accetta quote qualsiasi; il controllo ufficiale, secondo l'area 3, scarta il file per quote incoerenti con la successione legittima.** (fatto dichiarato in `docs/COLLEGAMENTI.md` §1, tabella delle prove; non ho potuto rieseguire il controllo, vedi «Cosa non ho potuto verificare»)
- Evidenza: `docs/COLLEGAMENTI.md` §1 riporta per la bozza tecnica del caso completo: «scartata: … numero soggetti in devoluzione, quote ER incoerenti con la devoluzione per legge» (prova «non registrata nel repository»). Il caso sintetico `tests/telematico_casi.py` devolve il conto 1/3–2/3 a due figli per legge; anche i test del calcolo (`tests/test_telematico_calcolo.py:72-100`) usano 1/3–2/3 fra cugini per legge. `docs/MATRICE_COPERTURA.md` marca «quote di legge dell'Allegato 5» come `non coperto (non verificate)` ma, contrariamente alla definizione della stessa matrice («non coperto: … l'XML non viene prodotto»), l'export viene prodotto e la verifica interna dichiara la pratica finalizzabile.
- Impatto: il perimetro dichiarato (solo devoluzione per legge) non controlla proprio la regola che lo caratterizza; il test di divergenza degli arrotondamenti e l'esempio «figli» si basano su ripartizioni che il controllo ufficiale scarterebbe. Il rilievo «numero soggetti in devoluzione» non risulta né spiegato né tracciato in matrice.
- Correzione: implementare la tabella dell'Allegato 5 (Fascicolo I) o, finché manca, rendere `non_supportato` ogni devoluzione per legge con quote diverse da quelle derivabili; registrare nel repository il diagnostico di quella prova (input, `.dgn`, `.wri`) e tradurre ciascun diagnostico in un caso di test.

**R11 — Il «passaggio manuale tracciato» del controllo ufficiale non si può completare dall'applicazione.** (fatto verificato)
- Evidenza: `collegamenti/controllo.py` `_BaseControllo.registra_diagnostico` registra `.dgn`/`_logSchema.xml`/`.wri` forniti dall'utente, ma non è richiamato da `servizio.py`, `elaborati.py`, `web.py`, `mcp_server.py` né `static/app.js` (`grep registra_diagnostico` → solo `controllo.py` e test). Il testo mostrato all'utente (`ISTRUZIONI_MANUALI`, punto 3: «Registrare nel programma i file prodotti dal controllo») chiede un'azione che l'interfaccia non offre. Inoltre `elaborati.controllo_ufficiale_pratica` (`elaborati.py:81-103`) fotografa l'esito al momento della chiamata in un proprio job: un diagnostico registrato in seguito non aggiornerebbe lo stato mostrato in «File».
- Impatto: senza Java/JAR configurati (situazione attesa su molte postazioni) lo stato del controllo resta «non eseguito» per sempre; `docs/COLLEGAMENTI.md` lo descrive come «implementato e provato con file reali registrati».
- Correzione: esporre la registrazione del diagnostico (GUI e, se si vuole, MCP con file della cartella d'ingresso) e derivare lo stato del controllo dal job dell'adattatore, non da una copia.

**R12 — Riconciliazione dell'invio: un `.esi` di Multifile con `resultCode` diverso da `00` è trattato come prova che il file non è stato trasmesso, e sblocca un nuovo tentativo.** (fatto verificato sul codice; semantica dei codici da collaudare)
- Evidenza: `collegamenti/invio.py`, `_valuta_evidenze`: `if r.get("resultCode") and r.get("resultCode") != "00": return RispostaInvio("non_trasmesso", …)`; `_applica_risposta` riporta allora la copia a `confermata` («nuovo tentativo possibile»). Il manuale Multifile (v1.1.1, p. 58, scaricato in scratch, SHA-256 `cd11f332…ef713`, uguale a quello citato) dice solo «"00" per esito positivo, altro per esito negativo»: un esito negativo dell'operazione non prova che il server non abbia ricevuto il file. `docs/COLLEGAMENTI.md` §3 afferma invece «`non_trasmesso` solo con prova indicata».
- Impatto: rischio di doppia trasmissione della stessa dichiarazione dopo un errore ambiguo (oggi solo potenziale: il modulo invio non è collegato a servizio/GUI/MCP e il trasporto è manuale).
- Correzione: con `resultCode != 00` passare a `esito_incerto` con candidati e chiedere la verifica su «Ricerca ricevute»/R02 prima di ammettere un nuovo tentativo.

**R13 — Semantica del campo `valore` dei beni non comunicata all'utente né al client MCP.** (fatto verificato)
- Evidenza: Fascicolo I p. 22 e p. 24 (testo estratto, «valore quota = valore quota defunto x quota di devoluzione») e `esporta.valore_bene`: il `valore` è la base imponibile della **quota del defunto**, già arrotondata all'euro. `schema.COLLEZIONI` (`schema.py:27-31`) lo dichiara solo come `importo`; lo strumento MCP `schema_dati` e l'interfaccia (`app.js` `renderTabella`, intestazione «valore») non lo spiegano.
- Impatto: inserire il valore dell'intero immobile con `quota_defunto` 1/2 raddoppia QE, l'asse (EE) e l'imposta calcolata, senza alcun rilievo. È l'errore d'uso con maggiore effetto fiscale e non è intercettato.
- Correzione: descrizione dei campi nello schema esposto (GUI/MCP), etichetta esplicita («valore della quota del defunto») e, se utile, un avviso quando `valore` coincide con un valore di mercato pieno dichiarato altrove.

### Bassa

**R14 — Barra di stato: «Controllo ufficiale: non eseguito» è un testo fisso.** `static/app.js:97` scrive sempre quel testo, anche dopo un controllo eseguito o obsoleto (lo stato vero è solo nella scheda «File»). Correzione: leggere `controllo_ufficiale.stato` da `/elaborati`.

**R15 — Capacità MCP incoerenti.** `mcp_server.py:19-22` elenca fra i «non disponibili» «controllo ufficiale» ed «export XML SUC13 completo», ma il server espone `successioni_controllo_ufficiale` e `successioni_esporta_xml` (righe 122-135); `funzioni` (righe 66-67) non li cita. Un client AI che legge `capacita` riceve informazioni contrarie agli strumenti presenti.

**R16 — `opzioni.quadri_attivi` non è validato.** Una stringa (es. `"EF"`) viene iterata carattere per carattere (`quadri.py:196-198`): riproduzione `riproduci3.py` → quadri attivi `['AN','DV']`, nessun errore al salvataggio. Correzione: validare la sezione `opzioni` (tipo lista, valori in `PER_ID`).

**R17 — Doppia arrotondatura nel candidato «esatta» del calcolo.** `telematico/calcolo.py:289-290` arrotonda il totale prima al centesimo e poi all'euro (HALF_UP due volte), mentre il docstring (righe 14-16) la presenta come «nessun arrotondamento intermedio». Per totali esatti con frazione in [0,495; 0,5) il candidato dà l'euro superiore (es. 100,495 → 100,50 → 101, contro 100 applicando una sola volta la regola «per difetto se inferiore a 50 centesimi»). Effetto: al massimo 1 euro e solo in casi limite; poiché anche il candidato del componente arrotonda al centesimo, i due candidati possono concordare e il caso risultare `completato` invece che `divergenza_aperta`. Correzione: arrotondare l'esatto direttamente all'euro, o dichiarare la doppia arrotondatura come parte dell'ipotesi.

**R18 — `ripristina_revisione` senza chiave di richiesta e senza controllo del canale.** `servizio.py:180-195`: un doppio clic su «Ripristina» crea due revisioni identiche; `canale` non passa da `_canale`. Effetto solo sulla cronologia (nessuna perdita di dati).

**R19 — Documenti di stato non aggiornati.** `docs/STATO_LAVORI.md` dichiara ancora «Calcolo imposte, XML SUC13 completo, stampa: non ancora disponibili» e «26 test verdi», mentre esistono calcolo ed export (bozza tecnica) e la suite conta 192 test; `docs/PDFA.md:11` usa «controllo locale passato» per un caso con «firma simulata» (secondo `docs/COLLAUDO_CLOUD_WINDOWS.md` una prova su firma simulata è `simulazione`).

## Punti aperti

(in compilazione)

## Cosa non ho potuto verificare

(in compilazione)
