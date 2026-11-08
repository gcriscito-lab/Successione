# Stato dei lavori (aggiornato 2026-11-08)

## Versione 0.4.0 (2026-11-08, ramo `rilascio-0.4.0`, etichetta `v0.4.0`)
- Contiene 0.3 (densita', pannello sotto, vista unica immobili; opzioni, predefiniti invariati), 0.4 (strumenti di studio),
  design system (token di spazi e raggi, bordi a 3:1), correzioni della revisione completa (`docs/REVIEW_COMPLETA_20261108.md`)
  e i 16 rilievi sull'interfaccia (ramo `revisione-gui`, commit `2d02167`).
- Novita' per lo studio e limiti aperti in `docs/NOVITA.md`; decisioni da confermare con il professionista: saggio legale dal
  2026, pertinenze della prima casa, basi del preventivo, esiti delle ricevute che tengono aperta la pratica.
- Verifiche e pacchetto: vedi il commit dell'etichetta `v0.4.0`.

## Versione 0.4 «Strumenti di studio» (2026-11-08, ramo `versione-0.4`)
- Anteprima interna (`anteprima()` in app.js) per modello, prospetti, brogliaccio, albero, istruzioni, fascicolo e preventivo;
  intestazioni `X-Frame-Options: SAMEORIGIN` e `frame-ancestors 'self'` (middleware `IntestazioniSicurezza` in web.py).
- `fascicolo.py` + `GET /api/pratiche/{pid}/fascicolo.pdf`: copertina con indice, modello stampato, allegati EG nell'ordine
  dei righi (TIFF convertiti), ricevute PDF del tentativo con protocollo della copia attiva; segnalibri; mancanti in copertina.
- `tabelle.py` + `GET /api/tabelle` + strumento MCP di lettura `tabelle_calcolo`: tabelle lette dalle costanti e funzioni di
  calcolo (nessun numero nuovo), Guida > Tabelle e fonti.
- `anonimizza.py` + `POST /api/pratiche/{pid}/copia-anonima`: nuova pratica con dati di fantasia (CF con controllo corretto,
  stessi caratteri di data e sesso), senza allegati, note, IBAN, fornitore; originale invariata; idempotente con `chiave`.
- `preventivo.py` + `GET /api/pratiche/{pid}/preventivo?tipo=preventivo|parcella`: dati in `note.preventivo`; percentuali
  del professionista (vuote = 0); somme: IVA su compensi + contributo, ritenuta sui compensi (**scelta da confermare**).
- `cruscotto.csv_elenco` + `GET /api/pratiche.csv` (stesso ordine della pagina iniziale, celle protette dalle formule).
- **Divergenze segnalate, non corrette**: moltiplicatori catastali citano il D.Lgs. 141/2026 e l'usufrutto il D.Lgs. 123/2025
  invece del D.Lgs. 346/1990 come modificato dal D.Lgs. 139/2024; saggio dell'usufrutto verificato solo fino al 31/12/2025.
  `cruscotto.stato_pratica` legge le ricevute dalla copia piu' recente (`copie[0]`), non dalla copia attiva (da verificare).
- Rinviati, da discutere: protezione con password, aiuto guidato per le agevolazioni.
- Verifiche: suite Python 2080 passati e 1 saltato (pacchetto); interfaccia 18/18 con `tests/e2e/gui_versione_04.js`
  (aggiornate `gui_guida.js` e `gui_review_20261103.js`: i documenti si aprono nell'anteprima). Nuovi test:
  `test_fascicolo.py`, `test_tabelle.py`, `test_strumenti_studio.py`.

## Pagina iniziale ridisegnata (2026-11-08, ramo `home-chiara`)
- Un solo elenco delle pratiche (tabella) al posto di colonna a sinistra + elenco a schede + «Prossime azioni»: per ogni pratica
  termine (con la decorrenza, da `cruscotto.py`), cinque tappe in piccolo e prossima azione; filtri a pulsanti con i conteggi,
  ricerca e ordine (urgenza, ultime modificate, nome). `GET /api/cruscotto?tutte=1` restituisce tutte le pratiche; senza
  parametro il comportamento resta quello di prima (12 piu' urgenti).
- Sulla pagina iniziale sono nascosti la colonna dei quadri e i comandi della pratica (Salva, Controlla, File e invio).
- Prove aggiornate alla struttura nuova mantenendo cio' che verificano (contrasto nei temi, decorrenza, tappa da correggere):
  `gui_review3.js`, `gui_review4.js`, `gui_grafica_rapida.js`, `gui_layout_20261103.js`; nuove `gui_home.js`,
  `tests/test_home_elenco.py`. Suite Python 2066 passati e 1 saltato; interfaccia 17/17.

## Versione 0.3 in prova: densita' e velocita' di inserimento (ramo `versione-0.3`)
- Proposte 1, 2, 5, 6 del report grafico DEAS (`Report_grafica_DEAS_rea_20261108.md`). Predefiniti invariati: si attivano con
  le preferenze `disposizione` (`destra`/`sotto`, con `altezza_pannello` 200-900) e `densita` = `compatta`.
- Misure a 1366x768 (dati sintetici, `scratchpad/e2e_porta/foto4.js`): fabbricato 2402 px -> 753 px con pannello sotto e scheda
  compatta (campi visibili senza scorrere 10/28 -> 23/28); erede 1418 -> 589 px (13/13). Solo pannello sotto: 1229 px; solo
  compatta a destra: 1499 px.
- Vista unica degli immobili (EB, EC, EL, EM) solo nell'interfaccia; Alt+1…9 sulle voci dell'elenco (Alt+lettera scartato:
  Alt+D/E/F del browser, Alt+Maiusc cambia lingua della tastiera su Windows); Invio al campo successivo nella scheda.
- Verifiche: suite Python 2064 passati e 1 saltato (pacchetto); prove interfaccia 16/16 con `tests/e2e/gui_versione_03.js`.
- **Da fare prima di rilasciarla**: prova del professionista su una pratica reale con pannello sotto e scheda compatta; poi
  decidere se diventano i predefiniti, versione 0.3.0 e pacchetto.

## Versione 0.2.0 (2026-11-08, commit `e3c2d6c`, etichetta `v0.2.0`)
- Novita' per lo studio in `docs/NOVITA.md`; nessuna regola di calcolo nuova (regole 2026-11-07).
- Verifiche: suite Python 2060 passati e 1 saltato; con il pacchetto costruito `tests/test_installazione.py` 18/18 (anche il
  test del pacchetto); prove interfaccia 15/15; XML SUC13 di prova valido sull'XSD di `fonti/`.
- Pacchetto Windows: `dist/Successioni-0.2.0-win64` (106 MB) e zip da 51.588.292 byte, SHA-256
  `d39bf1f73dfe1bdd673c8db6700e1988dd2ce842a39293ed0cecd96291ab0771`; `costruisci_pacchetto.py --verifica` senza problemi.
  Python 3.13.17 embeddable e wheel del lock scaricati con impronta verificata.
- Avvio dal pacchetto provato su questo PC (Python del pacchetto, archivio temporaneo): interfaccia attiva, versione 0.2.0,
  codice comune dalle tabelle SUC13. **Da collaudare** l'installazione su un altro PC Windows e la pratica reale con la 0.2.0.

## Grafica dal confronto con DE.A.S. II (2026-11-08, ramo `grafica-rapida`, unito con avanzamento diretto)
- Analisi: `Report_grafica_DEAS_rea_20261108.md` (cartella `Successioni` del Desktop, fuori dal repository): 255 maschere DFM
  di DEAS lette dall'eseguibile, solo come idee di layout; nessun codice, icona o testo di DEAS nel programma.
- Fatte: «Dati generali» senza colonna vuota (classList.toggle con undefined), tabella eredi con cognome e nome per primi,
  devoluzioni per bene con la somma delle quote e il diritto per nome, filtri della pagina iniziale su una riga, titolo del
  quadro su una riga (`4288c80`, `871f873`); proposte 3, 4, 7, 11 del report (`c98a048`): tinta e scritta «calcolato» per i
  valori calcolati (token `--calc`), codice comune ricavato dal nome con «Usa» (tabelle del componente SUC13, API
  `/api/codice-comune`, MCP `codice_comune`), stati vuoti con istruzione e trascinamento dei file, titoli di gruppo come barra.
- Verifiche: suite Python 2060 passati e 1 saltato; prove interfaccia 15/15 (porta 8823). Dopo l'unione 15/15 anche nella
  cartella principale.
- Da fare (report, proposte 1-2, 5, 6, 8-10): scheda compatta con etichette a sinistra e dettaglio sotto l'elenco, da provare
  con il professionista su una pratica reale; vista unica degli immobili; Alt+lettera per i quadri; elenco pratiche a tabella;
  anteprima interna; consultazione delle tabelle di `fonti/`.

## Correzioni dalla seconda review completa del 07/11/2026 sera (`docs/archivio/REVIEW_COMPLETA_20261107_SERA.md`)
Priorita' 1, tutte affrontate (commit su `moduli/integr4`):
- 1 usufrutto/nuda proprieta' con devoluzione per legge bloccati (`REGOLA_CODICE_DIRITTO`); 8 QuotaValore del file confrontato
  con la riesportazione e avviso sull'ordine del quadro EA; valore catastale con la prima casa dal diritto di abitazione
  (codici 1, 2, 5, 6) — `6e10873`.
- 2 `.dgn` del controllo manuale non piu' accettato per il solo CF; 3 nessuna nuova copia con un tentativo aperto, copia
  attiva in interfaccia, `.esi` dalla GUI, `stati_pratica` rimossa; catasto manuale «completo» -> `caricato_manualmente`;
  guida della prima pratica (passi 9-12) e matrice allineate — `8b58f96`.
- 4 `SUCCESSIONI_CONFIG` in tutti i modi dell'avviatore; 6 archivio senza connessioni a riposo, WAL svuotato;
  7 richieste web in un thread di lavoro, «database is locked» -> 503 — `7a2bcdc`; impostazioni salvate una alla volta — `64f717d`.
- 5 modifica di gruppo, tasto Invio, Ctrl+S, Prossime azioni (5 punti del cruscotto) — `306f82d`.
- 9 righi EG ricontrollati nella transazione che cancella, `allegato_id` validato, PDF/A idempotente, albero genealogico con
  revisione riletta — `d69b2d8`.
Pulizia (ramo `worktree-agent-a1c72ea2a83cb926f`):
- import inutilizzati tolti da `telematico/agevolazioni.py` (analisi statica con `ast` su `telematico/` e moduli vicini;
  fuori da quest'area restano `cli.py` Servizio, `elaborati.py` Path, `servizio.py` datetime/timezone/ErroreServizio);
- eta' calcolata solo da `usufrutto.eta`; data del decesso letta solo da `formati.data_decesso_defunto` (export e valore
  catastale);
- separazione con colpa: annotazione XSD di FlagSeparazione applicata alla lettera (divieto del grado 01 solo nella sezione
  devoluzione dei quadri, non con «legge estera»); il controllo ufficiale SUC13 2.3.1 non applica questa annotazione (prova
  locale in `tests/test_eg_eh.py`), il blocco resta dell'export;
- spostamento dei righi EG sul PDF/A (`riordina_allegati`, `_dopo_conversione`) con revisione riletta e nuovi tentativi
  (`tests/test_allegati_conflitto_revisione.py`);
- importazione: avviso per testi con spazi ripetuti o a capo (DatoAN_Type li ammette, `formati.an` li riduce);
- docstring di `calcolo.py`, `quadri_efgh.py`, `sostitutiva.py` riallineati al perimetro reale; riferimenti a `stati_pratica`
  aggiornati in `docs/PROPOSTE_collegamenti.md` e `docs/COMPITI_PER_AGENTI_GRATUITI.md`.
Da riscontrare punto per punto: le voci di priorita' 2 e 3 non citate sopra (per esempio brogliaccio e `opzioni.telematico`,
calcolatrice, accessibilita', prestazioni, test dipendenti da Java, accelerazione della suite), su cui lavorano altre sessioni.

## Miglioramenti dall'analisi di DE.A.S. II (2026-11-07, ramo `miglioramenti-replica`)
- Analisi e voci approvate: `docs/ANALISI_REPLICA_2026-11-07.md` (gruppi 1-4 del §8, approvati dal committente il 07/11/2026).
  Solo comportamento osservato: nessun codice, testo o tabella di DEAS (licenza proprietaria).
- Lavoro su un ramo nuovo creato da `50117d6`, in una copia separata (`.claude/worktrees/miglioramenti-replica`): il ramo
  `claude/successioni-dichiarazioni-app-fhcwbe` e l'archivio reale non sono stati toccati. Nel frattempo il ramo principale e'
  avanzato (`886ea2e`). Unito nel ramo principale il 07/11/2026 su richiesta del committente (commit `9c1aff6`; unico
  conflitto l'elenco delle prove in `tests/e2e/esegui_tutti.py`, tenute entrambe). Alle 18:50 un'altra sessione ha unito sopra
  guida, calcolatrice e Prossime azioni (`96ae8c7`). Verifiche su `95b99fc` (stato con entrambe le unioni): 1942 passati e
  1 saltato; prove interfaccia 12/12; XML di prova valido sull'XSD.
- Da guardare (non legato a queste modifiche): due allegati dello stesso rigo EG acquisiti nello stesso istante possono uscire
  in ordine diverso fra due esportazioni (visto una volta su quattro con la fixture sintetica: stesso rigo, stesso contenuto).
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

## Sintesi corrente (2026-11-05, dopo la revisione esterna `docs/archivio/REVISIONE_ESTERNA_CODEX_20261105.md`)
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
Ognuno tiene traccia in `docs/archivio/STATO_area1.md`, `docs/archivio/STATO_area2.md`, `docs/archivio/STATO_area3.md`. Alla consegna: verificare direttamente,
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
