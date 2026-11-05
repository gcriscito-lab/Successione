# Piano dei prossimi passi e dei lavori per gli agenti gratuiti

Stato al 2026-11-03 sera: 17 quadri su 17 con almeno un caso sintetico che supera il controllo SUC13 locale; PDF/A con Ghostscript 10.08.0 e veraPDF 1.30.3;
pacchetto Windows costruito, installato e provato; 515 test passati, 0 saltati. **Non utilizzabile su una pratica reale**: mancano casi particolari
dei quadri, la stampa, la verifica con i servizi dell'Agenzia e l'invio reale. Stime e dettagli: `docs/MATRICE_COPERTURA.md`.

## 1. Cosa abbiamo imparato sugli agenti (da usare nel piano)

| Osservazione (2026-11-03) | Conseguenza |
|---|---|
| Resa migliore: `claude-sonnet-4-5`, poi `gpt-oss-120b`; `codestral` quasi mai | catena di modelli in quest'ordine |
| 30 lanci su 60 falliti per HTTP 429/502/503 del servizio, non per qualita' | al massimo 3 lanci in parallelo, pausa di 20 s, nuovo tentativo con un altro modello |
| Compiti con percorsi Windows (`C:\...`) falliti 14 volte su 14: le barre rovesciate rompono il JSON | cambiare il formato di risposta (vedi 3.0) |
| I revisori gratuiti hanno mancato una discrepanza reale (EO, codice fiscale dell'emittente) | niente revisioni di regole agli agenti, salvo la prova di calibrazione (3.3) |
| Test scritti da agenti: sempre incompleti alla prima mutazione (C12, C13, C23, C22) | la mutazione del codice resta obbligatoria prima di integrare |
| Documenti scritti da agenti: ripetono frasi superate della matrice | ogni documento passa da uno script di verifica e dalla correzione alla fonte |

## 2. Lavori del coordinatore (non delegabili), in ordine

Criterio: prima cio' che sblocca casi **frequenti** nelle pratiche vere, poi cio' che richiede letture lunghe delle fonti.

| # | Lavoro | Perche' | Note |
|---|---|---|---|
| C1 | **Agevolazione «prima casa»** (codici P, Z, X, Y; Sezione II di EH; diritto di abitazione) | e' presente in moltissime successioni con un fabbricato | leggere Allegato 2 e Fascicolo I; calcolo EF con ipocatastali ridotte; un caso per codice, SUC13 locale; **parziale 2026-11-03**: P, X, Z (EC) con EF4 ed EH Sez. II, controllo locale positivo; restano Y, Z senza P, EM, diritto di abitazione, requisiti esteri/forze armate (`docs/regole/prima_casa.md`) |
| C2 | **Riduzioni art. 25 / precedenti successioni** (`ValorePrecSucc`, `Riduzioni`) | compaiono in EB, EC, EN, EO, EP, EQ, ER | **fatto (controllo locale)** per i codici 1-5 e per L, Q, R, F nel perimetro di docs/regole/riduzioni_art25.md; restano non supportati i casi del §7 di quel file |
| C3 | **Titoli esenti** (EO tipo 3, `ValoreEsente`) | BOT, CCT, buoni postali sono molto comuni | cambia EE e il calcolo (valore esente fuori dalla base) |
| C4 | **Piu' comuni nello stesso quadro** (circoscrizioni EF15/EF16) | oggi blocca tutte le successioni con immobili in due comuni | la tabella delle conservatorie e' solo nel componente ufficiale: leggerla a runtime dal JAR configurato dall'utente, senza distribuirla, **da decidere insieme** |
| C5 | **Rappresentanti di legatari, esecutore testamentario, trustee** (cariche 3, 7, 9) e relative sezioni di EH | sblocca chi non e' erede | EH Sezioni II-IV |
| C6 | **Qualifiche multiple** (stesso soggetto erede e legatario, franchigia unica) | citato dalla guida pag. 3 | solo calcolo |
| C7 | **Maschere dell'interfaccia** per i dati strutturati: superficie, ripartizione, estremi di EI, dati dell'azienda | oggi solo da MCP o API | `app.js`, provato nel browser reale: lavoro mio |
| C8 | **Stampa** | prevista dalla specifica | prima capire il formato richiesto nelle fonti |
| C9 | Beni esteri, immobili aziendali, inventario, dichiarazione sostitutiva | meno frequenti | dopo C1-C6 |

Dopo ogni lavoro: caso sintetico in `tests/telematico_casi.py`, controllo SUC13 locale, test con mutazioni, estensione di `test_telematico_nessuna_perdita.py`, matrice, suite completa, un commit.

## 3. Lavori per gli agenti

### 3.0 Prima: migliorare il lanciatore (coordinatore, mezza giornata)
1. **Formato di risposta a blocchi di testo** invece di JSON: `=== FILE: percorso ===` seguito dal contenuto fino alla riga `=== FINE ===`. Elimina gli errori di escape (barre, virgolette, a capo): era la causa di almeno 14 fallimenti.
2. **Nuovo tentativo automatico** su 429/502/503 con attesa crescente e cambio modello, nel lanciatore stesso (oggi lo fa `catena2.sh`).
3. **Limite di concorrenza** (massimo 3) e pausa tra i lanci.
4. Esito in `CONSEGNA.md` con il motivo reale del fallimento (limite del servizio / formato / test che non passa).
Accettazione: rilanciare C22 e C24 (falliti oggi) e vederli riuscire senza intervento.

### 3.1 Batch A, test di caratterizzazione (a rischio basso)
| ID | Cosa | Verifica |
|---|---|---|
| A1 | Rotte web su errori: 401/403/422, corpo non valido, mai HTTP 500 (quadri, elaborati, allegati) | `pytest` + mutazione sul controllo del token |
| A2 | `integrita.py` e `blocchi.py`: casi limite di verifica e ripristino | `pytest` + mutazione |
| A3 | Funzioni pure di `quadri_efgh` (arrotondamenti, `_flag`, `_estremi_ei`) | `pytest` + mutazione |
| A4 | `archivio.py`: backup e ripristino con percorsi con spazi e accenti | `pytest` |
| A5 | `documenti/` (anteprima, tiff, dimensioni): casi limite senza strumenti esterni (simulati) | `pytest` |

### 3.2 Batch B, documenti verificati da script (rischio basso)
| ID | Cosa | Verifica automatica |
|---|---|---|
| B1 | **Dizionario dei codici di errore** dell'esportazione (`DATO_MANCANTE`, `REGOLA_*`, ...) con significato e come correggere | script: ogni codice del documento esiste in `src/`, ogni codice di `src/` e' nel documento |
| B2 | **Esempi eseguibili** per MCP e API (creare pratica, aggiungere un titolo, esportare) | script che esegue i blocchi di codice su un archivio temporaneo |
| B3 | **Guida al controllo SUC13**: come leggere i diagnostici piu' comuni (1013, 3076, 3345, ...) | script: ogni codice citato compare nelle risorse del componente o nei test |
| B4 | Manuale breve aggiornato con installazione, backup e disinstallazione | `verifica_doc_quadri.py` esteso |

### 3.3 Batch C, esperimento di calibrazione dei revisori (una sola volta)
Obiettivo: sapere se un modello gratuito possa fare da revisore. Metodo: inserire in una copia del codice **5 difetti noti** (condizione invertita, validazione tolta, campo non esportato, ordine sbagliato, regola dimenticata) e chiedere a ogni modello (`claude-opus-4-5`, `claude-sonnet-4-5`, `gpt-oss-120b`, `fusion`) di elencare le discrepanze con l'annotazione XSD. Misura: quanti difetti trova e quante false segnalazioni. Se nessuno trova almeno 4 su 5, le revisioni di regole restano al coordinatore per sempre.

### 3.4 Batch D, mutazioni (qualita' dei test)
D1 (coordinatore): `scripts/verifica_mutazioni.py`, che legge `tests/mutazioni.json` (file, testo vecchio, testo nuovo, test attesi) e verifica che **ogni** mutazione faccia fallire almeno un test e che il testo vecchio esista ancora.
D2 (agenti): scrivere le voci di `mutazioni.json` per un modulo alla volta (esportazione, supplemento, invio). Verifica: lo script del coordinatore. E' il modo di far lavorare gli agenti sulla qualita' dei test senza fidarsi delle loro asserzioni.

### 3.5 Cosa NON si affida mai agli agenti
Regole fiscali e loro lettura dalle fonti, calcolo, esportazione XML, sicurezza e conferma dell'invio, credenziali, installazione di software, interpretazione di annotazioni XSD, decisioni su quali dati escludere o bloccare.

## 4. Controlli del coordinatore (invariati)
1. Perimetro della patch; 2. riesecuzione del comando di verifica; 3. **mutazione** del codice coperto; 4. lettura; 5. per i documenti, script e controllo a campione contro la matrice;
6. suite completa con tutte le variabili (SUC13, Java 8, Ghostscript, veraPDF, pacchetto); 7. un commit per consegna, con il modello nel messaggio.
Scarto immediato: file fuori perimetro, `src/` toccato, nomi inventati, regole fiscali nel testo, test che sopravvivono alla mutazione.

## 5. Calendario proposto (senza durate: dipende dai tempi del servizio gratuito)

1. Lanciatore a blocchi di testo e nuovi tentativi (3.0).
2. In parallelo: lavori C1 e, sullo sfondo, Batch A e B (3.1, 3.2) con il nuovo lanciatore.
3. C2 e C3; Batch D (3.4) per misurare i test appena scritti.
4. Esperimento di calibrazione (3.3).
5. C4 (dopo la decisione sulla tabella delle conservatorie), C5, C6.
6. C7 (maschere) e C8 (stampa).
7. Collaudi non delegabili e che dipendono da te: `Disinstalla.cmd`, avvio dal collegamento del desktop, `Configura-MCP.cmd` con Claude Desktop, un secondo PC, SmartScreen e antivirus.
8. Solo dopo, e solo con una pratica verificata e la tua autorizzazione: Entratel, invio reale, ricevute.

## 6. Decisioni che servono da te
1. **Tabella delle conservatorie (C4)**: usare a runtime il file del componente ufficiale che hai gia' scaricato (senza copiarlo nel programma) oppure lasciare bloccate le pratiche con piu' comuni?
2. **`git push`** del branch `claude/successioni-dichiarazioni-app-fhcwbe`: oggi esiste solo in locale.
3. **Priorita' C1 (prima casa)**: confermi che sia la prima agevolazione da fare, o hai pratiche reali che richiedono altro (riduzioni, titoli esenti, piu' comuni)?
4. Chi esegue i collaudi del punto 7 e su quale altro PC.
