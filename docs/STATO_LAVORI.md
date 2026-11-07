# Stato dei lavori (aggiornato 2026-11-07)

## Miglioramenti dall'analisi di DE.A.S. II (2026-11-07, ramo `miglioramenti-replica`)
- Analisi e voci approvate: `docs/ANALISI_REPLICA_2026-11-07.md` (gruppi 1-4 del §8, approvati dal committente il 07/11/2026).
  Solo comportamento osservato: nessun codice, testo o tabella di DEAS (licenza proprietaria).
- Lavoro su un ramo nuovo creato da `50117d6`, in una copia separata (`.claude/worktrees/miglioramenti-replica`): il ramo
  `claude/successioni-dichiarazioni-app-fhcwbe` e l'archivio reale non sono stati toccati. Nel frattempo il ramo principale e'
  avanzato (`886ea2e`): prima dell'unione serve allineare.
- Fatte (commit `d490387`, `f1842cb`):
  - 19 rimedio («Come risolvere») per ogni rilievo e avviso di `verifica_pratica`/`stato_quadri` (`rimedi.py`);
  - 21 avvisi di qualita' non bloccanti (`qualita.py`): spazi doppi, CF duplicato, carattere di controllo errato, CF incoerente
    con sesso o nascita, nascita dopo il decesso, provincia diversa da quella del codice comune (solo con le tabelle SUC13);
  - 22 somma delle quote per bene e diritto nella scheda del bene, anche con righe DV non salvate;
  - 33 riepilogo del soggetto in EA (ruolo, parentela, dichiarante, beni e quote) e segno «dichiarante» in tabella;
  - 5 modifica di gruppo per beni e devoluzioni (modifiche da salvare: una revisione, annullabile dalla Cronologia);
  - 9 incolla da Excel/testo tabulato nelle tabelle;
  - 10 appunti per riga e stato di lavorazione del quadro nella sezione `note` (non dichiarati, impronta invariata);
  - 8 pagina iniziale: tutte le pratiche, ricerca, filtri per termine ordinario, ordine per scadenza;
  - 23 brogliaccio beni e quote: CSV per Excel, pagina stampabile, strumento MCP `brogliaccio` (sola lettura).
- Gia' fatte da un'altra sessione prima della fase 2 (commit `783b1f7`): 27, 28, 29, 24, 31, 34 (province).
- Non fatte, con motivo: 17 (imposte ipocatastali per erede: manca in `fonti/` la regola di ripartizione); 34 per la
  consistenza (campo di testo libero usato dall'export: cambiarne il formato tocca l'XML); 21 per zeri di foglio/particella e
  termine dei 5 anni prima casa (nessuna fonte).
- Verifiche: suite Python prima 1840 passati e 1 saltato, dopo 1857 passati e 1 saltato (17 test nuovi in
  `tests/test_rimedi_qualita.py` e `tests/test_brogliaccio.py`); prove interfaccia 8/8 prima e 9/9 dopo (porta 8823, per non
  scontrarsi con il server di prova di un'altra sessione sulla 8813). XML SUC13 completo di una pratica sintetica con allegati
  valido sull'XSD `fonti/Specifiche tecniche/SUC13_20250702/SUC/xsd/fornituraSUC13_v1.xsd` e identico byte per byte a quello
  del ramo principale (sha256 `d332eb88…`). Controllo ufficiale non rieseguito su questo file.

## Sintesi corrente (2026-11-05, dopo la revisione esterna `docs/REVISIONE_ESTERNA_CODEX_20261105.md`)
- Corretti R01 (risposte CF tardive tra pratiche: contatore `S.gen` e verifica di coerenza in `suggerisciDaCF`), R02 (tipo
  dichiarazione non gestito: nessun XML, quindi nessuna preparazione), R03 (preparazione dopo modifica non dichiarativa) e
  R04 (rigenerazione ripara l'XML alterato). Regressioni Python in `tests/test_correzioni_codex.py`; R01 verificato nel browser
  integrato con risposta ritardata (riprodotto sul codice precedente), non ancora con Playwright: non installato qui.
- R05: `gui_aspetto.js` usa `selectOption` per la provincia; matrice riallineata su Frontespizio/EG/EH. Restano da fare le
  altre voci della revisione (sezione 4): sostitutive, devoluzione legittima, pluricomune, collegamenti reali, stampa ministeriale.
- Sostitutive codici 1 e 2 implementate (`telematico/sostitutiva.py`, `tests/test_sostitutiva.py`, `docs/regole/sostitutiva.md`); controllo ufficiale SUC13 2.3.1 locale positivo il 2026-11-05 su dati sintetici. Codice 3 non supportato.
- Le sezioni seguenti sono cronologia storica: possono descrivere come assenti funzioni poi realizzate.


Nota per riprendere. Le decisioni sotto sono già prese; non vanno riaperte senza motivo.

## Decisioni di interfaccia
- Struttura **A** (come il compilatore dell'Agenzia): frontespizio, quadri EA…ER, riepiloghi, pannello controlli.
- Stile scelto: **combinazione di 1 (Vetro) e 2 (Grafite)**, con i **colori di 1**: veste chiara e smerigliata, blu di sistema,
  sigle dei quadri colorate per stato; struttura di Grafite: tabella fitta al centro, ispettore a destra con
  *Dati / Controlli / Cronologia*, barra di stato in basso (revisione, salvataggio, rilievi, controllo ufficiale).
- Proposte visionabili: https://claude.ai/artifact/A6CKL8HtA3sgG3smRMiamc (stili), https://claude.ai/artifact/PmvopkizoXjojMyoNywadt (strutture).

## Interfaccia (fatto il 2026-11-01)
Applicato lo stile Vetro+Grafite (colori di Vetro) all'interfaccia vera: tabella fitta con selezione di riga, ispettore a destra
(Dati / Controlli / Cronologia), barra di stato, frontespizio a schede, procedura guidata. Provata in browser reale con
`tests/e2e/gui_flusso.js` (13 verifiche positive, nessun errore JS). Il vecchio `app.js` è in `docs/design/vetro-grafite/app_precedente.js`.
Avvertenza: `with_server.py` può lasciare il server attivo; chiudere per PID prima di rilanciare le prove.

## Consegne dei subagenti
- **Area 2 (documenti, PDF/A): consegnata e verificata il 2026-11-01.** Suite intera 179 passati, 2 saltati; vincolo sui nomi allegati (solo maiuscole, max 100)
  confermato nell'XSD (typesDati_v2.xsd riga 18, typesReg_v2.xsd riga 422). Integrate: strumento MCP e pulsante GUI "Suddividi", pillow dichiarato.
  Da integrare quando c'è l'XML: `verifica_fornitura` prima dell'invio, anteprima visiva, nomi EG con `dati_file_attachment` (area 1).
  Resta **da collaudare**: veraPDF (procedura in `docs/PDFA.md` par. 9), fedeltà visiva su documenti reali.
- Aree 1 (regole/XML) e 3 (collegamenti): ancora in corso.

## Subagenti (rilanciati su Opus)
Tre agenti lavorano su file distinti (contratti in `docs/CONTRATTI_MODULI.md`): regole/XSD/XML, documenti/PDF-A, collegamenti.
Ognuno tiene traccia in `docs/regole/STATO_area1.md`, `docs/archivio/STATO_area2.md`, `docs/archivio/STATO_area3.md`. Alla consegna: verificare direttamente,
integrare, poi revisore indipendente. I loro file nel repository sono bozze finché non consegnano.

## Limiti dichiarati
- Validazione PDF/A indipendente (veraPDF): **da collaudare** (l'esecuzione dell'installer scaricato è stata bloccata dai permessi).
- Controllo ufficiale SUC13, catasto Entratel, invio e ricevute, client Claude su Windows, installazione Windows: **da collaudare**.
- Calcolo imposte, XML SUC13 completo, stampa: non ancora disponibili. I quadri non supportati bloccano la finalizzazione.
- Skill di progetto in `.claude/skills/` (vedi `docs/SKILLS_SETUP.md`): risultano ora caricate.

## Verifiche eseguite
`python -m pytest -q` → 26 test verdi (archivio, MCP stdio reale, GUI, quadri, PDF/A con Ghostscript).


## Integrazione degli aggiornamenti di Codex (2026-11-02)
Applicati due commit di Codex (`0aebdce` correzioni CE01-CE10, `1206a30` collaudo Windows) sulla beta `2e2b503`, senza conflitti e senza forzature.
Verifica di chi coordina, in questo container Linux: la patch si applica pulita, ho letto le parti sensibili (ripristino con verifica di integrità,
protezione dei percorsi dei file statici, lock di processo, adattatore del controllo) e la suite intera dà **259 passati, 8 saltati, 0 falliti**
(i saltati richiedono componenti esterni non configurati qui). Le prove su Windows (veraPDF 1.30.3, Ghostscript 10.08.0, pacchetto autonomo, controllo
SUC13 con Java 8, ripresa del job) sono **riportate da Codex** in `docs/archivio/COLLAUDO_WINDOWS_CODEX_20261102.md` e NON sono state riprodotte da me.
Restano da collaudare: Entratel, catasto reale, invio e ricevute, client Claude effettivo, SmartScreen e antivirus, disinstallazione, WSL.
