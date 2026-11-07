# Analisi di replica: DE.A.S. II rispetto alla nostra app (7 novembre 2026)

**Fase 1, sola lettura.** Questo file è l'unico creato nel repository; nessun altro file è stato modificato. Niente va
implementato prima dell'approvazione dell'elenco (§8).

## 1. Premesse

| Voce | Valore |
|---|---|
| App di riferimento | DE.A.S. II (Geo Network), demo installata in `C:\geonet`. Il prompt aveva il segnaposto `[INSERIRE URL O PERCORSO CARTELLA]` non compilato: ho usato l'app già in esame in questa sessione. **Da confermare.** |
| Licenza | **Proprietaria.** Nessun file LICENSE o EULA nella cartella di installazione; contratto di licenza non disponibile né verificato. Quindi **nessuna copia di codice**: si reimplementa dal comportamento osservato. |
| Nostra app | ramo `claude/successioni-dichiarazioni-app-fhcwbe` (ultimo commit `48336fa`), più modifiche non salvate in git presenti nel working tree e non mie (11 file, tra cui `quadri_efgh.py`, `allegati.py`, `catasto.py`). |
| Fonti lette | `CLAUDE.md`, `README.md`, `docs/STATO_LAVORI.md` (aggiornato al 2026-11-05, in parte superato da `MATRICE_COPERTURA.md`, `PIANO_MODULI_MANCANTI.md` e `REVIEW_COMPLETA_20261107.md`) |
| Skill usate | `replica-recon` e `replica-diff`. Le loro uscite (`recon.md`, `features.csv`, `parity.md`, schermate di riferimento) stanno nella cartella di lavoro della sessione e **non nel repository**, per rispettare la sola lettura. |

### Come sono state raccolte le informazioni su DEAS

- Manuale `help.chm` (132 pagine) e 137 schermate del manuale.
- Pratica di esempio `.DEASX` (archivio ZIP): nomi dei campi di 20 tabelle e il file `.suc` prodotto da DEAS.
- Tabelle di sistema: **solo i nomi dei campi**.
- Risorse dell'interfaccia dentro `deas2.exe`: nomi delle finestre, didascalie, testi dei messaggi.

**Avvertenza da conoscere.** La skill `replica-recon` vieta di decompilare il binario. Prima della ricognizione, in questa
sessione, è stato avviato Ghidra (tramite rea) su `deas2.exe`. **È stato interrotto senza produrre risultati e non è stato
letto codice.** Le risorse dell'interfaccia e i testi però sono stati estratti dall'eseguibile. In questo documento servono solo
come **elenco di funzioni e di controlli**: nessun testo, tabella o coefficiente di DEAS va copiato nella nostra app.

### Credenziali e dati personali trovati (segnalati, non spostati)

- **DEAS**: le tabelle `C:\geonet\DEAS2\SYSTEM\INTERMEDIARIOF24.DAT` (campi `ENTRATEL_USERNAME`, `ENTRATEL_PASSWORD`,
  `ENTRATEL_PINCODE`), `LOGIN.DAT` (`USERNAME`, `PASSWORD`) e `PARAPROXY.DAT` (`PROXYPASSWORD`) sono fatte per contenere
  credenziali. **I valori non sono stati letti.** Se in futuro installate DEAS con credenziali vere, sappiate che le conserva lì.
- **Pratica di esempio DEAS** (`DATA\*.DEASX`): nominativi e codici fiscali "Garibaldi/Rossi", forniti dal produttore come esempio
  e verosimilmente fittizi.
- **Nostra app**: nei file letti non ho visto credenziali. Non ho fatto una scansione completa del repository.
- **Archivio reale** `%USERPROFILE%\Successioni-reale`: non toccato. Le prove sono state fatte su archivi temporanei.

## 2. Esito di replica-diff

```
Parità funzionale: 28,9 / 100   (52 funzioni contate, 5 escluse con motivo)
Funzioni "must": 4 su 19 presenti, quindi non alla pari
Per area, dalla più debole:
  interfaccia 10,0 · studio 15,0 · ingresso 17,6 · calcoli 20,0 · stampe 42,9 · controlli 65,0 · export 75,0
Nostre, assenti in DEAS (non contate): revisioni e differenze della pratica; MCP con le stesse regole della GUI
```

**Come leggere il numero.** Misura quante funzioni di DEAS facciamo anche noi, non la qualità di ciò che facciamo. Dove
coincidiamo (export SUC13, controllo ufficiale, PDF/A, stampa del modello) siamo verificati col controllo ufficiale locale.

**Limite.** Il confronto di layout (`imgdiff`) non è stato eseguito: le schermate di DEAS vengono dal manuale (600-800 px, dati
diversi) e DEAS non è stato avviato. Le differenze di interfaccia sono quindi qualitative (§7) e misurate solo sulla nostra
app (`Report_grafica_layout_20261107.md`).

## 3. Divergenze fiscali (segnalate, non corrette)

Regola applicata: nessuna regola di calcolo entra nell'app se non trova riscontro nel D.Lgs. 346/1990 come modificato dal
D.Lgs. 139/2024 e nelle specifiche SUC13 in `fonti/`. **In `fonti/` non c'è il testo del D.Lgs. 346/1990 né del D.Lgs.
139/2024**: ci sono Fascicoli I e II, l'allegato «passaggi di calcolo», le specifiche SUC13 e il Modulo 04. Le verifiche sotto sono
fatte su questi documenti.

| # | Regola osservata in DEAS | Riscontro in `fonti/` | Conseguenza |
|---|---|---|---|
| D1 | Valore degli immobili da rendita con moltiplicatori e rivalutazione per categoria e periodo | **Assente**: i Fascicoli parlano di "valore catastale" ma non riportano moltiplicatori né rivalutazione | Non implementabile finché in `fonti/` non entrano le norme (art. 34 c. 5 TUS e disposizioni richiamate). **Bloccante** per la funzione n. 1 |
| D1-bis | **Lavoro in corso trovato nel working tree** (non mio, non in git, file delle 11:33-11:34): `src/successioni/valore_catastale.py`, `docs/regole/valore_catastale.md`, `tests/test_valore_catastale.py`, `tests/e2e/gui_valore_catastale.js`. Propone il valore catastale come **avviso** (`VALORE_SOTTO_CATASTALE`), senza sostituire il valore dichiarato. Fonti citate: L. 662/1996 e D.Lgs. 141/2026 art. 309, lette su Normattiva | Le fonti citate **non sono in `fonti/`** e non sono il D.Lgs. 346/1990 / D.Lgs. 139/2024. Il documento dichiara anche "da collaudare" i moltiplicatori 60 e 40,80 | **Divergenza dal vincolo del prompt**: va deciso se quelle fonti sono ammesse, ed eventualmente aggiunte a `fonti/` con impronta nel `manifest.json`. Non ho toccato quei file |
| D2 | Coefficienti dell'usufrutto per età e per periodo | **Parziale**: formula "valore × tasso legale × coefficiente della tabella allegata al TUS" e tasso 2025 al 2,5% (Fascicolo I p. 30; Fascicolo II p. 7, con esempi a coefficienti 20, 36, 38). **La tabella completa non c'è** | Serve la tabella allegata al TUS in `fonti/` |
| D3 | Ravvedimento: sanzione base 30% ridotta a 0,1% al giorno fino al 15°, poi 1/10, 1/9, 1/8, 1/7, 1/6 (DEAS cita il D.Lgs. 178/2015) | **Assente**: il Fascicolo rinvia all'art. 13 D.Lgs. 472/1997 senza percentuali | Non implementare. La tabella del manuale DEAS è datata e il regime sanzionatorio va verificato su una fonte ufficiale aggiornata (non verificato qui) |
| D4 | "Il tasso legale non può essere inferiore al 2,5% (art. 17 c. 1-ter TU)" (avviso di DEAS) | **Non verificabile**: in `fonti/` c'è solo il 2,5% del 2025 negli esempi | Non implementare senza il testo del TUS |
| D5 | Rateizzazione: fino a 8 rate se l'importo da rateizzare è fino a 20.000 €, fino a 12 oltre; acconto minimo | **Presente** (Fascicolo I p. 48; specifiche: "tra 1 e 12") | La nostra `quadri_efgh.py:593-608` è già allineata: **nessuna divergenza** |
| D6 | Prima casa chiedibile solo dal dichiarante fra i primi 3 soggetti di EA ("bug del modulo di controllo SUC13") | **Assente** nelle fonti: è un comportamento del controllo, non una regola | Da **provare col controllo ufficiale locale** prima di introdurre un avviso |
| D7 | Rinunciatario da indicare come "chiamato" e non come "erede" (modulo AdE 1.1.1) | Da verificare sulle annotazioni XSD di `GradoParentela`/`TipoSoggetto` | Verifica prima di introdurre l'avviso |
| D8 | Tributi speciali: 30,99 € per conservatoria nel modello telematico (manuale DEAS, liquidazione) | Le fonti citano la Sezione V "tributi speciali" senza l'importo nelle parti lette | Non usare il valore di DEAS; il nostro EF va confrontato con le fonti a parte |

## 4. Funzionalità che mancano a noi

Legenda. Valore: **A** quasi ogni pratica, **M** frequente, **B** occasionale. Complessità: **S** giorni, **M** 1-2 settimane,
**L** oltre. Rischio: **fiscale** (può cambiare importi o XML), **dati** (può perdere o alterare dati), **basso**.

| Funzionalità o miglioramento | Presente da noi | Valore | Complessità | Rischio | File che andrebbero toccati |
|---|---|---|---|---|---|
| 1. Valore immobile da rendita (moltiplicatori per categoria e periodo, prima casa, ricalcolo del quadro, avviso sotto il minimo) | no nel codice in git; **in corso** nel working tree (vedi D1-bis) | A | M | fiscale, **da decidere su D1/D1-bis** | `valori.py`, nuovo `telematico/valore_catastale.py`, `telematico/esporta.py` (EB/EC), `schema.py`, `static/app.js`, `docs/regole/valore_immobili.md`, nuovi test |
| 2. Usufrutto e nuda proprietà (età, anche dalla data di nascita, coefficienti) | no (blocca l'export) | A | M | fiscale, **bloccato da D2** | `telematico/esporta.py` (devoluzioni con diritto diverso), `telematico/calcolo.py`, `schema.py`, `static/app.js`, `docs/regole/usufrutto.md` |
| 3. Albero genealogico generato come EG6 in PDF/A (da EA, rinunciatari e premorti, genitore) | no | A | M | basso (allegato) | nuovo `documenti/albero.py`, `pdfa.py`, `allegati.py`, `telematico/quadri_efgh.py` (EG6), `static/app.js` |
| 4. Ravvedimento operoso calcolato (versamento e presentazione tardivi) | no (solo importi dichiarati) | M | M | fiscale, **bloccato da D3/D4** | `telematico/pagamenti.py`, `telematico/quadri_efgh.py` (Sez. VI), `docs/regole/ravvedimento.md` |
| 5. Modifica di gruppo degli immobili (quota, diritto, età) | no | A | S | dati (modifica massiva: serve revisione unica e annullabile) | `servizio.py`, `mcp_server.py`, `static/app.js` |
| 6. Pratica da visura catastale PDF e import nel quadro immobili | no (adattatore catasto pronto) | A | L | dati (lettura PDF) | nuovo `collegamenti/visura_pdf.py`, `collegamenti/catasto.py`, `servizio.py`, `mcp_server.py`, `static/app.js`; servono **visure campione anonimizzate** |
| 7. Import tollerante di `.suc` di altri software e versioni (vecchio `QuadroEI`, decessi prima del 2025, sostitutive) | parziale: il `.suc` di DEAS è rifiutato | M | M | dati | `telematico/importa.py`, `servizio.py`, test con XSD delle versioni precedenti |
| 8. Elenco pratiche per scadenza e stato (filtri, sospensione dei termini) | parziale (termine ordinario in pagina iniziale) | A | S | basso | `archivio.py`, `servizio.py`, `static/app.js` |
| 9. Incolla da Excel o da testo tabulato | no | M | S | dati (validazione) | `static/app.js`, `servizio.py` |
| 10. Appunti per bene e soggetto; stato per quadro (completato, da completare, da controllare) | no | M | S | basso | `schema.py`, `static/app.js`, `archivio.py` |
| 11. Calcolatrici a sé stanti (imposte rapide, quota di legittima e disponibile) | no | B | S | fiscale (riusano `calcolo.py`) | `telematico/calcolo.py`, `static/app.js` |
| 12. Diritto di abitazione del coniuge | parziale (bloccato con motivo) | M | M | fiscale | `telematico/esporta.py`, `docs/regole/immobili_particolari.md` |
| 13. Imposta di successione per decessi prima del 2025 | parziale (EF dal 2006) | B | L | fiscale, servono fonti dei periodi | `telematico/calcolo.py`, `telematico/fonti.py` |

**Esclusi, con motivo:** assistente AI integrato (scelta di progetto: AI esterna); Modello 4, volture 1.1/2.0 e cartacee,
INVIM (superati); import da prodotti Geo Network; multiutente su DBMS; invio e ricevute Entratel (servono credenziali e
collaudo, fuori dalla fase 1).

## 5. Differenze nel flusso di compilazione

| Funzionalità o miglioramento | Presente da noi | Valore | Complessità | Rischio | File che andrebbero toccati |
|---|---|---|---|---|---|
| 14. Ingresso da documenti: DEAS parte da visura, precompilata, `.SUC` o copia PDF; noi da zero o da XML | parziale | A | vedi 6-7 | dati | vedi 6-7 |
| 15. Procedura guidata agevolazioni: prima l'agevolazione, poi i cespiti e i soggetti (DEAS); noi riga per riga nella devoluzione | parziale | M | M | fiscale (stesse regole, nuovo ingresso) | `static/app.js`, `servizio.py`, `telematico/agevolazioni.py` (solo lettura delle regole) |
| 16. Quote: DEAS si ferma con "situazione ambigua" se mancano i genitori dei rappresentanti; noi blocchiamo le configurazioni non verificate | parziale | M | S | fiscale | `telematico/devoluzione_legge.py` (testo dell'avviso), `static/app.js` |
| 17. Liquidazione per erede e legatario (tutte le imposte) prima dell'invio | parziale (`prospetto_cliente.py`, imposta di successione per erede) | A | S | fiscale (solo esposizione) | `prospetto_cliente.py`, `static/app.js` |
| 18. Codice comune ricavato dal nome invece che digitato | parziale (la tabella dei comuni c'è nel componente di controllo) | M | S | dati | `codice_fiscale.py` (`_comuni`), `static/app.js` |

## 6. Controlli e validazioni

| Funzionalità o miglioramento | Presente da noi | Valore | Complessità | Rischio | File che andrebbero toccati |
|---|---|---|---|---|---|
| 19. Ogni errore di verifica con il **rimedio** (quale comando o campo correggere) | parziale (il rimedio c'è solo nella diagnosi dell'ambiente) | A | S | basso | `mcp_server.py` (`verifica_pratica`), `servizio.py`, `static/app.js:1575` (già mostra `rimedio`) |
| 20. Avvisi preventivi sui difetti noti del controllo AdE (D6, D7), solo dopo prova locale | parziale (dubbi in `docs/regole/`) | M | S | fiscale (solo avvisi) | `servizio.py`, `docs/regole/` |
| 21. Qualità anagrafica e catastale: doppi spazi in nome e cognome, zeri iniziali in foglio e particella, provincia incoerente col comune, codice fiscale duplicato fra soggetti, nato prima del defunto, caratteri non ammessi, termine di 5 anni per la prima casa | parziale: **da confrontare uno per uno** con i controlli esistenti | M | S | basso | `servizio.py`, `codice_fiscale.py`, test |
| 22. Somma delle quote per bene diversa da 1/1, visibile mentre si compila | parziale (blocca l'export) | A | S | basso | `static/app.js` |

## 7. Stampe ed export, interfaccia

### Stampe ed export

| Funzionalità o miglioramento | Presente da noi | Valore | Complessità | Rischio | File che andrebbero toccati |
|---|---|---|---|---|---|
| 23. Brogliaccio immobili e riepilogo quote per bene e per erede (PDF e CSV) | no | M | S | basso | `prospetto_cliente.py` o nuovo `stampe_studio.py`, `static/app.js` |
| 24. Documentazione necessaria **specifica della pratica** (non la lista generica) | parziale | M | S | basso | `static/index.html`, `static/app.js`, `servizio.py` |
| 25. Fascicolo unico per il cliente (dichiarazione, allegati, ricevute) | no | B | S | basso | `elaborati.py`, `pdfa.py` |
| 26. F24 compilato | no | B | M | fiscale (codici tributo da fonti) | nuovo modulo, fonti da aggiungere |

### Interfaccia (misure in `Report_grafica_layout_20261107.md`)

| Funzionalità o miglioramento | Presente da noi | Valore | Complessità | Rischio | File che andrebbero toccati |
|---|---|---|---|---|---|
| 27. Colonne chiave fisse (riconoscimento a sinistra, **Valore** a destra): a 1366 px oggi Valore e Quota sono fuori schermo | no | A | S | basso | `static/app.css`, `static/app.js` |
| 28. Ispettore chiuso senza selezione, oppure dettaglio sotto la tabella (master-detail) | no | A | S | basso | `static/app.css` (`.app.conIns`), `static/layout.js`, `static/app.js` |
| 29. Riga di totale sotto le tabelle con importi | no | A | S | basso | `static/app.js` |
| 30. Scheda dettaglio a gruppi su 2-3 colonne (oggi un immobile occupa 28 campi e 2,3 schermate) | no | M | M | basso | `static/app.css` (`.ins .rg`), `static/app.js` |
| 31. Campi obbligatori evidenziati e numero dei mancanti nell'elenco dei quadri | no | M | S | basso | `static/app.js`, `servizio.py` |
| 32. Menu "Operazioni" per quadro (ricalcola, modifica di gruppo, importa, duplica) | no | M | S | basso | `static/app.js` |
| 33. Riga di riassunto degli eredi (parentela, quota, dichiarante) al posto della tabella che scorre | no | M | S | basso | `static/app.js` |
| 34. Formati all'italiana ovunque (consistenza `5.50`, province `RM — RM`) | parziale | M | S | basso | `static/app.js` |
| 35. Scorciatoie da tastiera (nuova riga, duplica, quadro successivo, vai a quadro, `?`) | parziale | B | S | basso | `static/app.js` |

## 8. Proposta di elenco da approvare (fase 2)

Ordine proposto, dal più utile e meno rischioso:

1. **Interfaccia senza rischio fiscale**: 27, 28, 29, 22, 34, poi 31, 33.
2. **Controlli**: 19 (rimedio), 21 (qualità dati, dopo il confronto con i controlli esistenti).
3. **Produttività**: 5 (modifica di gruppo), 8 (scadenze), 10 (appunti e stato), 9 (incolla da Excel).
4. **Stampe**: 17, 23, 24.
5. **Albero genealogico** (3).
6. **Import tollerante** (7).
7. **Solo dopo aver aggiunto le fonti in `fonti/`** (D1-D4): 1, 2, 4. Nessun valore preso da DEAS.
8. **Visure PDF** (6), quando ci sono campioni anonimizzati.

Per approvare basta indicare i numeri. In fase 2: ramo nuovo `miglioramenti-replica` creato dal ramo attuale **dopo aver
deciso cosa fare delle modifiche non salvate nel working tree**, che non sono mie. Poi un miglioramento alla volta con test
prima e dopo, XML di prova validato con l'XSD in `fonti/` e aggiornamento di `docs/STATO_LAVORI.md`.

## 9. Esito della fase 1

- **Esito**: OK per la fase 1 (analisi). Nessuna implementazione.
- **Quadrature eseguite**:
  - punteggio `parity.py` (28,9; 4/19 must);
  - regole DEAS confrontate col testo estratto da tutti i PDF di `fonti/` (D1-D8);
  - rateizzazione confrontata con `quadri_efgh.py` (allineata);
  - import di prova del `.suc` di DEAS in un archivio temporaneo (rifiutato: `QuadroEI_new` assente).
- **Punti aperti**:
  - app di riferimento da confermare (segnaposto vuoto nel prompt);
  - fonti normative da aggiungere per D1-D4;
  - modifiche non salvate nel working tree da sistemare prima di creare il ramo, compreso il lavoro in corso sul valore
    catastale (D1-bis), che sembra di un'altra sessione;
  - `docs/STATO_LAVORI.md` fermo al 5/11.
- **Cosa non ho potuto verificare**:
  - contratto di licenza di DEAS;
  - DEAS in esecuzione: flussi e numero di clic stimati dal manuale;
  - confronto di layout con `imgdiff`;
  - regime sanzionatorio vigente per il ravvedimento;
  - controlli D6 e D7 col controllo ufficiale;
  - scansione completa del repository per credenziali.

### File creati o modificati

- Creato: `C:\Users\Giuseppe Criscito\Desktop\Successioni\Successione\docs\ANALISI_REPLICA_2026-11-07.md` (questo file).
- Fuori dal repository, nella cartella di lavoro della sessione `C:\Users\GIUSEP~1\AppData\Local\Temp\claude\2af9e9b0ea8fb616\45053d6c-0a54-4b58-9725-dbf17fa9f338\scratchpad\`:
  - `replica\recon.md`, `replica\features.csv`, `replica\parity.md`;
  - `replica\screens\` (10 schermate del manuale DEAS, solo riferimento);
  - `fonti_testo.txt` (testo estratto dai PDF di `fonti/`);
  - `archivio_prova\` e `gui_prova\` (archivi temporanei con dati sintetici).
- Creati prima, nella stessa sessione, fuori dal repository: `C:\Users\Giuseppe Criscito\Desktop\Successioni\Report_DEAS_II_20261107.md`
  e `C:\Users\Giuseppe Criscito\Desktop\Successioni\Report_grafica_layout_20261107.md`.

## 10. Fase 2: esito (07/11/2026)

Approvati dal committente i gruppi 1-4 del §8 (voci 27, 28, 29, 22, 34, 31, 33, 19, 21, 5, 8, 10, 9, 17, 23, 24). Lavoro sul
ramo `miglioramenti-replica` (da `50117d6`) in una copia separata; il ramo originale non e' stato modificato.

| Voce | Stato | Dove |
|---|---|---|
| 27 colonne fisse, 28 pannello che si chiude, 29 totali, 24 documenti per la pratica, 31 obbligatori e rilievi nell'elenco, 34 province | gia' fatte da un'altra sessione (commit `783b1f7`, prima della fase 2) | — |
| 19 rimedio per ogni rilievo e avviso | fatta | `rimedi.py`, `servizio.py`, `static/app.js` |
| 21 qualita' dei dati (avvisi non bloccanti) | fatta in parte: esclusi zeri di foglio/particella e 5 anni prima casa (nessuna fonte) | `qualita.py` |
| 22 somma delle quote nella scheda del bene | fatta | `static/app.js` |
| 33 riepilogo del soggetto in EA | fatta | `static/app.js` |
| 5 modifica di gruppo | fatta (beni: diritto, quota, data visura; devoluzioni: diritto, quota). L'eta' dell'usufruttuario non e' un campo del modello | `static/app.js` |
| 9 incolla da Excel | fatta | `static/app.js` |
| 10 appunti e stato del quadro | fatta, nella sezione `note` (non dichiarata) | `static/app.js` |
| 8 elenco per scadenza | fatta senza sospensione dei termini (regola non in `fonti/`) | `static/app.js` |
| 23 brogliaccio | fatta: CSV, pagina stampabile, MCP | `brogliaccio.py`, `web.py`, `mcp_server.py` |
| 17 tutte le imposte per erede | **non fatta**: la ripartizione delle ipotecarie e catastali fra gli eredi non ha riscontro in `fonti/` | — |
| 34 consistenza `5.50` | **non fatta**: campo di testo usato dall'export, cambiarlo tocca l'XML | — |

Nessuna regola di calcolo nuova: franchigie, aliquote, quote e imposte non sono state toccate. Il file XML della pratica di
prova (sintetica, con allegati) e' valido sull'XSD di `fonti/` e identico byte per byte a quello prodotto dal codice del ramo
principale (`886ea2e`).
