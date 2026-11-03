# Compiti per agenti gratuiti (FreeLLMAPI o simili)

Pacchetto di lavoro delimitato, pensato per modelli meno affidabili: compiti piccoli, file consentiti dichiarati, criteri di accettazione verificabili da un comando. Il coordinatore rivede ogni consegna prima di integrarla.

## Regole per chi esegue (valgono per ogni compito)
1. Lavora su una copia del repository, branch `claude/successioni-dichiarazioni-app-fhcwbe`, partendo dal commit indicato dal coordinatore.
2. Tocca **solo** i file elencati nel compito. Niente altri file, niente `fonti/`, niente `docs/regole/`.
3. Dati **solo sintetici**. Mai dati reali di persone, mai credenziali, chiavi o token nel codice, nei log o nei documenti.
4. Nessuna regola fiscale dalla memoria. Se un compito ne richiede una, fermati e annotala in `docs/DOMANDE_PER_IL_COORDINATORE.md`: non inventarla.
5. Non saltare né indebolire test per farli passare. Se un test è sbagliato, spiegalo.
6. Consegna una patch (`git format-patch`) con un file `CONSEGNA.md`: cosa hai fatto, file toccati, comandi eseguiti con esito reale, cosa non hai potuto verificare.
7. Non fare push. Un compito alla volta.

Verifica di base per tutti: `python3 -m pytest -q` deve restare verde (oggi 263 passati, 8 saltati per componenti esterni non configurati).

## Cosa NON affidare a questi agenti
Regole fiscali e calcoli, esportazione XML, logica di invio e riconciliazione, sicurezza dell'interfaccia e dell'MCP. Restano al coordinatore o a un revisore forte.

---

## C1. Maschera «Dati della dichiarazione» nel frontespizio
**Perché:** stato civile, codice carica, contatti e versamento oggi si impostano solo da MCP o API (rilievo R20 aperto).
**File consentiti:** `src/successioni/static/app.js`, `src/successioni/static/app.css`, `tests/e2e/gui_flusso.js` (solo per aggiungere verifiche).
**Cosa fare:** nella scheda «Dati generali» aggiungere una sezione «Dati della dichiarazione» con i campi di `opzioni.telematico.dichiarazione` elencati in `src/successioni/telematico/supplemento.py` (`stato_civile`, `devoluzione_per_legge`, `firma_dichiarante`, `presentatore.persona_id`, `presentatore.codice_carica`, `presentatore.telefono`, `presentatore.email`, `versamento.iban`, `versamento.cf_titolare`, `tempistica_pagamento`). Salvataggio con l'operazione `{op:"set", sezione:"opzioni", campi:{telematico:<oggetto completo aggiornato>}}`: **leggere l'oggetto corrente e modificare solo le chiavi toccate**, senza perdere `persone`, `beni`, `passivita`. I codici ammessi non vanno inventati: mostrare un campo di testo con il suggerimento «codice come da istruzioni del frontespizio».
**Accettazione:** `node --check src/successioni/static/app.js`; nel browser (metodo di `.claude/skills/webapp-testing`) il valore inserito sopravvive a ricaricamento pagina e alla modifica di una persona; una verifica nuova in `tests/e2e/gui_flusso.js`; nessun errore JavaScript.

## C2. Manuale breve per il professionista
**File:** `docs/MANUALE_BREVE.md` (nuovo).
**Cosa fare:** istruzioni in linguaggio semplice, senza tecnicismi: avvio, nuova dichiarazione guidata, quadri, controlli, scheda File («bozza tecnica» che cosa significa), allegati e PDF/A («non verificato» senza veraPDF), backup e ripristino (`successioni backup <cartella>` e `successioni ripristina <backup> --destinazione <cartella nuova>`), dove sono i dati, cosa il programma NON fa (nessun invio, quadri non supportati). Fonti dei fatti: `docs/BETA_DA_REVISIONARE.md`, `docs/STATO_area4.md`, `scripts/windows/LEGGIMI.txt`, `docs/COLLAUDO_WINDOWS_CODEX_20261102.md`.
**Accettazione:** nessuna funzione citata che non esista (ogni comando verificabile con `--help`); massimo 3 pagine; nessun elenco di sigle senza spiegazione.

## C3. Guida all'installazione e configurazione MCP
**File:** `docs/INSTALLAZIONE_WINDOWS.md` (nuovo). `docs/CONFIGURAZIONE_MCP.md` esiste gia': non toccarlo.
**Contesto:** `scripts/windows/LEGGIMI.txt`, `docs/STATO_area4.md`, `docs/CONFIGURAZIONE_MCP.md`, `docs/COLLAUDO_WINDOWS_CODEX_20261102.md`.
**Cosa fare:** ricavare dal contenuto già scritto in `docs/STATO_area4.md`, `scripts/windows/` e `packaging/`. Per MCP: comando e variabili d'ambiente reali (`python -m successioni.mcp_server`, `SUCCESSIONI_DATA`), come verificare che gli strumenti con prefisso `successioni_` siano visibili, cosa succede se il client si chiude (lo stato è nei dati). Citare la documentazione ufficiale del client con URL e data solo se consultata davvero; altrimenti scrivere «da verificare».
**Accettazione:** ogni comando e percorso citato esiste nel repository; sezione finale «Da collaudare su Windows» coerente con `docs/COLLAUDO_WINDOWS_CODEX_20261102.md`.

## C4. Test aggiuntivi su valori, schema e servizio
**File:** `tests/test_valori_schema_extra.py` (nuovo).
**Contesto:** `src/successioni/valori.py`, `src/successioni/schema.py`.
**Cosa fare:** casi limite per `valori.py` e `schema.valida_campo`: quote con denominatore 0 o negative, importi con virgola, float, stringhe vuote; date 29 febbraio valide e non; stati del dato (`assente`, `zero`, `non_applicabile`, `da_confermare`); riferimenti inesistenti; `Servizio.aggiorna` con chiave di richiesta ripetuta e con contenuto diverso.
**Accettazione:** almeno 25 asserzioni significative, tutte verdi; nessun test che passi per il motivo sbagliato (ogni caso negativo verifica il **codice** dell'errore, non solo che ci sia un errore).

## C5. Insieme di domande di valutazione per l'MCP
**File:** `docs/valutazione_mcp.xml` (nuovo).
**Contesto:** `src/successioni/mcp_server.py`, `src/successioni/schema.py`, `docs/CONFIGURAZIONE_MCP.md`. Usare solo gli strumenti `successioni_*` e i campi dello schema reali; `id` delle righe assegnati dal sistema (non inventarli).
**Cosa fare:** 10 domande in stile `.claude/skills/mcp-builder/reference/evaluation.md` che un assistente deve risolvere usando gli strumenti `successioni_*` su dati sintetici (es. «quante persone con ruolo erede ha la pratica X», «quali quadri hanno rilievi», «la pratica è finalizzabile e perché»), con risposta attesa verificabile. Includere i dati di partenza come operazioni `aggiorna_pratica`.
**Accettazione:** ogni domanda ha una sola risposta corretta, indipendente dal tempo, verificabile con una query sull'archivio.

## C6. Verifica di accessibilità dell'interfaccia
**File:** `src/successioni/static/app.js`, `src/successioni/static/app.css`, `tests/e2e/accessibilita.js` (nuovo).
**Contesto:** `tests/e2e/gui_flusso.js`.
**Cosa fare:** uso completo da tastiera (albero dei quadri, tabella, ispettore, procedura guidata, finestra di dialogo con focus che rientra al chiudere), etichette associate ai campi, contrasti sufficienti in tema chiaro e scuro, ordine di tabulazione sensato. Un test Playwright che percorra il flusso solo con tastiera.
**Accettazione:** il test passa; nessuna regressione in `tests/e2e/gui_flusso.js`; elenco in `CONSEGNA.md` dei punti non risolti.

## C7. Estratti dalle fonti sui legatari (solo citazioni)
**Perche':** il coordinatore deve implementare il testamento con legatari e non puo' ricavare le regole dalla memoria.
**File:** `docs/regole/LEGATARI_estratti.md` (nuovo).
**Contesto:** `docs/regole/_estratto_fonti_legatari.txt` (pagine dei PDF ufficiali che contengono la parola «legatar», con intestazione `===== SIGLA pag. N =====`).
**Cosa fare:** per ciascuno dei sei argomenti (1 franchigie e aliquote per i legatari; 2 presunzione su denaro, gioielli e mobilia e legatari; 3 documenti da allegare per testamento e legatari; 4 codici carica 2, 3, 7, 9 del dichiarante; 5 quote e devoluzioni in presenza di testamento; 6 passivita' ED tipo 11, legati e oneri) elencare fino a 8 punti. Ogni punto ha: la citazione LETTERALE copiata dal testo (massimo 40 parole, tra virgolette), la sigla e il numero di pagina dell'intestazione sotto cui compare. NON riformulare, NON calcolare, NON dedurre: se un argomento non compare nel testo scrivere «non trovato nel contesto».
**Accettazione:** il coordinatore verifica con uno script che ogni citazione compaia alla lettera nella pagina indicata; le citazioni non trovate fanno scartare il punto.

## C8. Test di caratterizzazione del supplemento telematico
**File:** `tests/test_supplemento_extra.py` (nuovo).
**Contesto:** `src/successioni/telematico/supplemento.py`, `src/successioni/valori.py`.
**Cosa fare:** Casi limite di `attr` (valore sull'entita' che ha la precedenza, valore in `opzioni.telematico`, stati `assente`/`non_applicabile`/`da_confermare`/`zero`), `dich`, `presentatore_sup`, `chiavi_non_gestite` (chiavi sconosciute, riferimento a elemento inesistente, chiavi annidate di presentatore, versamento, testamento). Scrivere SOLO il file di test indicato: non modificare mai `src/`. I test descrivono il comportamento REALE del codice mostrato (non inventare funzioni, firme, codici o messaggi che non compaiono nel contesto). Import come negli altri test: `from successioni... import ...`. Almeno 15 asserzioni; ogni caso negativo verifica il tipo di eccezione e un frammento del messaggio; niente test che passino per il motivo sbagliato.
**Accettazione:** `python -m pytest -q tests/test_supplemento_extra.py` verde (lo esegue il lanciatore).

## C9. Test dei lettori di esiti e richieste dell'invio
**File:** `tests/test_invio_lettori_extra.py` (nuovo).
**Contesto:** `src/successioni/collegamenti/invio.py`.
**Cosa fare:** Solo le funzioni pure di lettura e costruzione: `leggi_esi`, `leggi_stato_invii`, `richiesta_download` (contenuti validi, vuoti, malformati, campi mancanti) e `TrasportoSimulato` da solo (protocolli progressivi, guasti `timeout_prima`, `timeout_dopo_ricezione`, `rifiuto`, consultazione per impronta). Non usare l'archivio ne' `InvioAdattatore`. Scrivere SOLO il file di test indicato: non modificare mai `src/`. I test descrivono il comportamento REALE del codice mostrato (non inventare funzioni, firme, codici o messaggi che non compaiono nel contesto). Import come negli altri test: `from successioni... import ...`. Almeno 15 asserzioni; ogni caso negativo verifica il tipo di eccezione e un frammento del messaggio; niente test che passino per il motivo sbagliato.
**Accettazione:** `python -m pytest -q tests/test_invio_lettori_extra.py` verde (lo esegue il lanciatore).

## C10. Test dei formattatori XML
**File:** `tests/test_formati_extra.py` (nuovo).
**Contesto:** `src/successioni/telematico/formati.py`, `src/successioni/valori.py`.
**Cosa fare:** Casi limite di `an`, `cf`, `data_iso`, `data`, `euro_intero`, `euro_centesimi`, `quota_grezza`, `telefono`, `email`, `cb`: valori validi, ai limiti di lunghezza, vuoti, di tipo sbagliato, date inesistenti (29 febbraio), importi con decimali o virgola. Scrivere SOLO il file di test indicato: non modificare mai `src/`. I test descrivono il comportamento REALE del codice mostrato (non inventare funzioni, firme, codici o messaggi che non compaiono nel contesto). Import come negli altri test: `from successioni... import ...`. Almeno 15 asserzioni; ogni caso negativo verifica il tipo di eccezione e un frammento del messaggio; niente test che passino per il motivo sbagliato.
**Accettazione:** `python -m pytest -q tests/test_formati_extra.py` verde (lo esegue il lanciatore).

## C11. Revisione indipendente del codice del quadro EO (solo segnalazioni)
**File:** `docs/regole/REVISIONE_EO.md` (nuovo).
**Contesto:** `docs/regole/_estratto_eo_per_revisione.txt` (codice `riga_eo` e annotazioni XSD del quadro EO).
**Cosa fare:** confrontare il codice con le annotazioni ufficiali e segnalare SOLO discrepanze concrete: obbligatorieta' non rispettate, condizioni invertite, campi non validati, elementi emessi in ordine diverso dallo schema, casi in cui il codice scarta dati senza errore. Per ogni segnalazione: la riga di codice (copiata alla lettera), la frase dell'annotazione XSD (copiata alla lettera) e perche' non coincidono. NON proporre modifiche fiscali, NON inventare regole che non compaiono nel testo, se non trovi discrepanze scrivi «nessuna discrepanza trovata».
**Accettazione:** il coordinatore verifica ogni segnalazione contro il testo; quelle non confermate vengono scartate.

## C12. Test di caratterizzazione di quadri.py e schema.py
**File:** `tests/test_quadri_schema_extra.py` (nuovo).
**Contesto:** `src/successioni/quadri.py`, `src/successioni/schema.py`, `src/successioni/valori.py`.
**Cosa fare:** casi limite di `quadro_di` (ogni tipo di bene verso il quadro atteso, province tavolari BZ/TN/GO/TS in maiuscolo e minuscolo, flag `sistema_tavolare`, persone defunto/presentatore/erede, collezioni passivita/documenti_ref/devoluzioni), di `attivi` (quadri_attivi assente o con sigle sconosciute, quadri sempre attivi) e di `schema.valida_campo` per i campi aggiunti di recente (`tipo_titolo`, `quantita`, `data_documento`, `anno_costruzione`, `partita_tavolare`). Scrivere SOLO il file di test indicato: non modificare mai `src/`. I test descrivono il comportamento REALE del codice mostrato (non inventare funzioni, firme, codici o messaggi). Almeno 20 asserzioni; ogni caso negativo verifica il tipo di errore.
**Accettazione:** `python -m pytest -q tests/test_quadri_schema_extra.py` verde (lo esegue il lanciatore).

## C13. Test delle rotte web e degli strumenti MCP dell'invio
**File:** `tests/test_invio_web_mcp.py` (nuovo).
**Contesto:** `src/successioni/web.py`, `src/successioni/invio_servizio.py`, `src/successioni/mcp_server.py`, `tests/test_correzioni_codex.py` (solo per vedere come si crea una pratica con `Servizio`, `crea_app` e `TestClient`).
**Cosa fare:** Con `starlette.testclient.TestClient` e `crea_app(servizio, token='sintetico', ammetti_host_di_prova=True)`: rotte `/api/pratiche/{pid}/invio` (lettura), `/api/pratiche/{pid}/invio/prepara` senza file completo (errore atteso), `/api/invio/{cid}/conferma` e `/trasmetti` con copia inesistente (errore leggibile, mai HTTP 500), richieste senza token (401). Per MCP: `mcp_server.costruisci(servizio)` e verifica per nome che esistano `successioni_invio_prepara` e `successioni_invio_stato` e che NON esistano strumenti di conferma o trasmissione. Scrivere SOLO il file indicato: non modificare mai `src/`. Descrivere il comportamento REALE del codice mostrato: non inventare funzioni, firme, campi, codici o messaggi. Almeno 15 asserzioni; ogni caso negativo verifica il tipo di errore e un frammento del messaggio.
**Accettazione:** `python -m pytest -q tests/test_invio_web_mcp.py` verde.

## C14. Test di caratterizzazione delle quote di legge
**File:** `tests/test_devoluzione_legge_extra.py` (nuovo).
**Contesto:** `src/successioni/telematico/devoluzione_legge.py`, `src/successioni/valori.py`.
**Cosa fare:** Casi di `quote_di_legge` e `descrivi` esattamente come il codice li gestisce oggi (configurazioni coperte e non coperte, input vuoti, gradi sconosciuti, tipi soggetto diversi da 1). NON stabilire quali quote siano giuste in base a norme: documentare cosa restituisce il codice, annotando in un commento `# caratterizzazione` ogni caso. Scrivere SOLO il file indicato: non modificare mai `src/`. Descrivere il comportamento REALE del codice mostrato: non inventare funzioni, firme, campi, codici o messaggi. Almeno 15 asserzioni; ogni caso negativo verifica il tipo di errore e un frammento del messaggio.
**Accettazione:** `python -m pytest -q tests/test_devoluzione_legge_extra.py` verde.

## C15. Test degli identificativi (CF, IBAN, partita IVA)
**File:** `tests/test_identificativi_extra.py` (nuovo).
**Contesto:** `src/successioni/telematico/identificativi.py`.
**Cosa fare:** Casi limite di `carattere_controllo`, `cf_persona_fisica_valido`, `genera_cf_sintetico`, `iban_modulo_97_valido`, `cifre_controllo_iban`, `piva_checksum_valida` (lunghezze errate, minuscole, caratteri non ammessi, omocodia se gestita, cifra di controllo corretta e sbagliata). Usare solo codici sintetici generati dalle funzioni stesse. Scrivere SOLO il file indicato: non modificare mai `src/`. Descrivere il comportamento REALE del codice mostrato: non inventare funzioni, firme, campi, codici o messaggi. Almeno 15 asserzioni; ogni caso negativo verifica il tipo di errore e un frammento del messaggio.
**Accettazione:** `python -m pytest -q tests/test_identificativi_extra.py` verde.

## C16. Guida alla compilazione dei quadri
**File:** `docs/GUIDA_QUADRI.md` (nuovo).
**Contesto:** `docs/MATRICE_COPERTURA.md`, `src/successioni/quadri.py`, `src/successioni/schema.py`, `tests/telematico_casi.py`.
**Cosa fare:** Per ogni quadro (EA, EB, EC, ED, EE, EF, EG, EH, EL, EM, EN, EO, EP, EQ, ER, EI): a cosa serve in due righe, quali campi del modello si compilano (nomi esatti come in `schema.py`, tra backtick), un esempio sintetico ricavato da `tests/telematico_casi.py`, cosa NON e' supportato (copiato dalla matrice, senza aggiungere nulla). Linguaggio semplice. NON riportare aliquote, franchigie o regole fiscali. Massimo 6 pagine.
**Accettazione:** `python scripts/verifica_doc_quadri.py docs/GUIDA_QUADRI.md` stampa «verifica documento: ok» (lo esegue il lanciatore).

## C18. Test dei quadri nuovi attraverso il servizio
**File:** `tests/test_quadri_nuovi_servizio.py` (nuovo).
**Contesto:** `src/successioni/servizio.py`, `src/successioni/quadri.py`, `src/successioni/schema.py`, `tests/telematico_casi.py`, `tests/test_elaborati.py` (per `ops_da_caso`).
**Cosa fare:** Con `Servizio(Archivio(tmp_path))` e `ops_da_caso`: crea pratiche dai casi `caso_titoli()`, `caso_mezzi()`, `caso_azienda()`, `caso_tavolare()` e verifica che `servizio.quadri(pid)` riporti per EO, EP, EQ, EN, EL, EM uno stato diverso da `non_supportato`, che `servizio.verifica(pid)` non produca rilievi `QUADRO_NON_SUPPORTATO` per essi, e che `EI` resti `non_supportato`. Aggiungere un test che una modifica di un bene `titolo` cambi la revisione e l'impronta dichiarativa. Scrivere SOLO il file indicato: non modificare mai `src/`. Descrivere il comportamento REALE del codice mostrato: non inventare funzioni, firme, campi, codici o messaggi. Almeno 15 asserzioni; ogni caso negativo verifica il tipo di errore e un frammento del messaggio.
**Accettazione:** `python -m pytest -q tests/test_quadri_nuovi_servizio.py` verde.

## C19. Test di coerenza tra matrice di copertura e codice
**File:** `tests/test_matrice_coerenza.py` (nuovo).
**Contesto:** `docs/MATRICE_COPERTURA.md`, `src/successioni/quadri.py`, `src/successioni/telematico/esporta.py` (costante `QUADRI_ESPORTABILI`).
**Cosa fare:** Test che leggono la matrice come testo: ogni quadro in `QUADRI_ESPORTABILI` e ogni quadro con `supportato=True` in `quadri.QUADRI` e' citato nella matrice nella tabella di sintesi; i quadri con `supportato=False` non risultano dichiarati «controllo locale». Messaggi di errore chiari che nominano il quadro. Scrivere SOLO il file indicato: non modificare mai `src/`. Descrivere il comportamento REALE del codice mostrato: non inventare funzioni, firme, campi, codici o messaggi. Almeno 15 asserzioni; ogni caso negativo verifica il tipo di errore e un frammento del messaggio.
**Accettazione:** `python -m pytest -q tests/test_matrice_coerenza.py` verde.

## C21. Sezione «Quadri disponibili» del manuale breve
**File:** `docs/QUADRI_DISPONIBILI.md` (nuovo).
**Contesto:** `docs/MATRICE_COPERTURA.md`, `docs/MANUALE_BREVE.md`.
**Cosa fare:** Una tabella per il professionista: quadro, cosa copre oggi in una riga, cosa non copre in una riga (dalla matrice, senza aggiungere nulla), con la distinzione fra «controllo locale» e «verifica ufficiale». Niente regole fiscali, niente promesse. Massimo 2 pagine.
**Accettazione:** `python scripts/verifica_doc_quadri.py docs/QUADRI_DISPONIBILI.md` stampa «verifica documento: ok».

---

## Come il coordinatore integra
Controllo dei file toccati rispetto all'elenco consentito, lettura della patch, applicazione su ramo temporaneo, `python3 -m pytest -q`, prova nel browser dove pertinente, poi avanzamento in avanti sul branch di sessione, senza forzature.


---

## Esecuzione sul PC con FreeLLMAPI locale (lanciatore)
FreeLLMAPI gira sul tuo PC (`http://127.0.0.1:31415/v1`): il cloud non lo raggiunge, quindi gli agenti vanno lanciati **da te**.
Il lanciatore `scripts/agenti_gratuiti/lancia.py` usa solo la libreria standard. Il modello non esegue comandi: restituisce modifiche in JSON,
che il lanciatore applica in una copia isolata (`git worktree`), rifiutando ogni file non elencato nel compito, e poi esegue le verifiche con i
propri comandi. La chiave si legge dall'ambiente e non viene mai scritta nei risultati. Serve `git`; per C1 e C6 anche `node`.

PowerShell, dalla cartella del repository (clone del branch `claude/successioni-dichiarazioni-app-fhcwbe`):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -e ".[test]"
$env:FREELLMAPI_BASE_URL = "http://127.0.0.1:31415/v1"
$env:FREELLMAPI_KEY = Read-Host "Chiave FreeLLMAPI"      # si digita nel terminale, mai in chat
python scripts\agenti_gratuiti\lancia.py --modelli       # elenca i modelli disponibili
$env:FREELLMAPI_MODEL = "<uno dei nomi elencati>"
python scripts\agenti_gratuiti\lancia.py C2 --dry-run    # mostra file consentiti e verifiche, senza chiamare il servizio
python scripts\agenti_gratuiti\lancia.py C2              # un compito alla volta (C1..C6)
```

Risultato in `build\agenti\<compito>-<data>\`: `consegna.patch` e `CONSEGNA.md` (con gli esiti **reali** delle verifiche; le note del modello sono
dichiarazioni non verificate). Per provare la patch: `git apply --check build\agenti\...\consegna.patch`. Poi mandala al coordinatore per la revisione.

Attenzione alla riservatezza: un servizio gratuito può inoltrare i prompt a fornitori esterni. Il repository contiene solo dati sintetici e documenti
pubblici; non usare il lanciatore su cartelle con dati reali. Il lanciatore è provato qui solo con un servizio finto in locale (`tests/test_agenti_gratuiti.py`):
la prova con FreeLLMAPI reale è **da fare sul tuo PC**.
