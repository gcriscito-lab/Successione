# Suite dei test: comandi, cache del controllo ufficiale, esecuzione in parallelo

Ambiente di sviluppo (Windows): `.venv\Scripts\python.exe`, con `PYTHONPATH=src` (lo imposta anche `pyproject.toml`).
Usare sempre una `--basetemp` esplicita senza «~», per esempio
`--basetemp="C:/Users/<utente>/AppData/Local/Temp/min_test1"`.

## Comandi

| Scopo | Comando | Note |
|---|---|---|
| Giro rapido quotidiano | `python -m pytest -m "not java" -n 4` | esclude i test che avviano il componente Java ufficiale |
| Suite completa (sviluppo) | `python -m pytest -n 4` | con la cache del controllo ufficiale |
| Suite completa seriale | `python -m pytest` | utile per leggere un errore senza l'output dei processi paralleli |
| **Verifica prima di una consegna** | `set SUCCESSIONI_TEST_SENZA_CACHE=1` poi `python -m pytest -n 4` | Java eseguito davvero per ogni test |
| Solo i test con Java | `python -m pytest -m java -n 4` | |

`-n 4` richiede `pytest-xdist` (extra `test` di `pyproject.toml`: `pip install -e .[test]` oppure
`pip install pytest-xdist`). Senza `-n` la suite gira in un solo processo.

## Marcatore `java`

`@pytest.mark.java` indica i test che avviano il componente Java dell'Agenzia (controllo SUC13 `MSUC13`, rapporto
`VisualXml`, modello di stampa, verifica dei componenti). `tests/conftest.py` controlla ogni avvio di `java`: se un test
avvia Java senza il marcatore, il riepilogo finale lo elenca nella sezione «test che avviano Java senza il marcatore
«java»» (va aggiunto il marcatore). La sola lettura di `java -version` non conta.

## Cache del controllo ufficiale (solo test)

`tests/_cache_controllo.py`, usata dall'helper `_esegui` di `tests/test_telematico_controllo.py` e, tramite
`tests/conftest.py`, dall'adattatore `collegamenti.controllo.ControlloJar` quando nessun esecutore e' iniettato (il job
resta un'esecuzione reale, non `simulazione`). Il programma non la usa mai.

- **Chiave**: SHA-256 dell'XML (per VisualXml: del `.dgn`), impronta dei JAR del classpath (nome, dimensione, data di
  modifica), versione di Java (`java -version`) e suo percorso, opzioni della JVM, classe e forma degli argomenti (con
  o senza `.dcm`), versione del formato della cache.
- **Valore**: `.dgn`, `_logSchema.xml`, `.dcm` (se prodotto), `.wri`, stdout/stderr, codice di uscita, durata, e se la
  copia di lavoro e' stata consumata dal componente.
- Nel ripristino il nome del job nel `.dgn`/`.wri` diventa quello corrente (stessa lunghezza) e la data del `.wri`
  quella di oggi. Non si conserva mai un'esecuzione scaduta, senza `.dgn` o che altera l'input; un test con tempo
  massimo inferiore alla durata registrata esegue sempre Java.
- **Cartella**: `%LOCALAPPDATA%\Successioni-test-cache` (fuori dal repository), oppure `SUCCESSIONI_TEST_CACHE`.
  Si puo' cancellare in qualunque momento.
- **Disattivazione**: `SUCCESSIONI_TEST_SENZA_CACHE=1` (obbligatoria per la verifica prima di una consegna, e dopo
  un aggiornamento dei JAR o di Java se si vuole la prova piena: in quel caso l'impronta cambia comunque e la cache
  si rigenera da sola).
- **Fedelta'**: `tests/test_cache_controllo.py::test_stesse_uscite_con_e_senza_cache` esegue il componente reale due
  volte sullo stesso XML (la seconda a cache disattivata) e una terza dalla cache: le uscite coincidono salvo il file
  temporaneo citato nel `_logSchema.xml` e la data del rapporto. Gli altri test del file provano la chiave, il
  ripristino del nome, la copia consumata, la disattivazione e il rispetto del tempo massimo, senza Java.
- Il riepilogo finale indica quanti risultati sono stati riusati e quante esecuzioni reali di Java ci sono state (in un
  processo seriale; con `-n` ogni processo tiene i propri conteggi).

## Test saltati: il motivo resta visibile

`pyproject.toml` aggiunge `-rs`: ogni test saltato compare nel riepilogo con il motivo. Se mancano Java 8 o i JAR
(`SUCCESSIONI_JAVA`, `SUCCESSIONI_CONTROLLI_SUC13`), oltre all'elenco compare la sezione
«controllo ufficiale SUC13 NON eseguito» con il numero di test saltati per motivo: in quel caso una suite verde **non**
prova il controllo ufficiale. Su un PC nuovo: installare Java 8, impostare `SUCCESSIONI_JAVA` (es.
`C:\Program Files\Java\jre1.8.0_xxx\bin\java.exe`) e `SUCCESSIONI_CONTROLLI_SUC13` (cartella dei 15 JAR del JNLP),
poi rieseguire.

## Esecuzione in parallelo (pytest-xdist)

Ogni processo ha le proprie cartelle temporanee (`tmp_path` sotto `--basetemp`), i server di prova usano porte libere
(`HTTPServer(("127.0.0.1", 0))`, `TestClient` senza socket reali) e la cache scrive ogni voce in modo atomico
(cartella temporanea poi rinomina), quindi due processi sullo stesso XML non si ostacolano.

## Tempi misurati

Misure del 2026-11-07 (Windows 11, Java 8, PC condiviso con altri processi: valori indicativi).

| Giro | Esito | Durata |
|---|---|---|
| Prima (commit 64f717d), seriale | 2013 passati, 1 saltato | 32 min 05 s |
| Dopo, `-n 4`, cache disattivata (`SUCCESSIONI_TEST_SENZA_CACHE=1`) | 2020 passati, 1 saltato | 11 min 51 s |
| Dopo, seriale, cache vuota all'avvio (si popola nel giro: 244 riusi, 341 esecuzioni di Java) | 2020 passati, 1 saltato | 26 min 31 s |
| Dopo, seriale, cache calda (576 riusi, 9 esecuzioni) | 2020 passati, 1 saltato | 11 min 56 s |
| Dopo, `-n 4`, cache calda | 2020 passati, 1 saltato | 5 min 10 s |

Il test saltato e' `test_installazione.py:381` (richiede `SUCCESSIONI_PACCHETTO_WIN`). Test con il marcatore `java`:
263 su 2021 (il giro `-m "not java"` ne esegue 1758). Nessun errore sotto `-n 4`.

## Altri interventi sulla durata

- `tests/test_mcp.py::test_mcp_suddividi_allegato_oltre_limite`: 3 pagine 600x600 e limite passato allo strumento MCP
  (prima 6 pagine 1400x1400 oltre 5 MB, ~57 s). Il limite predefinito di 5 MB resta provato in
  `tests/test_documenti_dimensioni.py`.
- `tests/test_agenti_gratuiti.py`: la lentezza non era `socket.getfqdn` (0,08 s) ma `git worktree add` (6-7 s per
  test). La prima copia isolata e' creata davvero; le successive riusano la stessa copia riportata allo stato del commit
  (`git reset --hard`, `git clean -fdx`) e spostata con `git worktree move`.
- `tests/test_backup_profilo_versioni.py::test_potatura_dei_backup_automatici`: orologio iniettato al posto di
  `time.sleep(1.05)` x 4.
- `_motivo_salto()`/`_java_major()` memorizzati: prima `java -version` veniva lanciato due volte per ogni decoratore
  `skipif` alla raccolta.
- Rapporto `.wri` (VisualXml, una JVM in piu') solo nei test che lo leggono: `_esegui(..., rapporto=False)` negli altri.
