# Collaudo della GUI web locale (sola lettura)

Data: 2026-11-03. Commit di partenza: 8321366 (fast-forward di `claude/successioni-dichiarazioni-app-fhcwbe`).
Nessun file sotto `src/`, `tests/`, `docs/` esistenti e' stato modificato. Dati solo sintetici.

## Metodo e limiti

- Server `tests/e2e/server.py` copiato in `C:/sx/server8870.py` (porta 8870), dati in `C:/sx/collaudo`.
- Pratica sintetica creata via API (`C:/sx/crea.py`, `C:/sx/crea2.py`, fuori dal repository): defunto, 3 eredi, fabbricato EC, terreno EB, conto, titolo, azienda, terreno e fabbricato tavolari, aeromobile, nave, passivita', 3 devoluzioni. Gli id seguono `^[a-z]{1,4}_[a-z0-9]{4,32}$` (un id come `p_def` viene rifiutato: vedi problema 3).
- Il pane del browser non salva gli screenshot su file: ho usato Chrome 156 headless pilotato via CDP (script in `C:/sx/*.js`, fuori dal repository). Viewport 1440x900, 1024x768, 375x812 (mobile). Gli screenshot sono in `build/collaudo_gui/` (cartella ignorata da git: aggiunti con `-f`).
- Non verificato: trascinamento con il mouse del separatore (provato solo da tastiera), importazione di un XML valido (provati solo file vuoto e non XML), invio/ricevute oltre "Prepara invio" (richiede controllo ufficiale), caricamento allegati/PDF-A, Firefox/Safari, tema seppia, 768px, lettore di schermo, confronto diretto con il compilatore ufficiale (JNLP non eseguito). Il contrasto e' calcolato in modo approssimato (sfondi con alfa non composti).
- Nessun errore JavaScript (`exceptionThrown`) in nessuna schermata. Console: solo i 422 attesi dalle validazioni e `GET /favicon.ico` 404.

Percorsi screenshot sono relativi a `build/collaudo_gui/`.

## Problemi, ordinati per gravita'

Gravita': B = blocca l'uso, C = confonde, E = estetico.

### 1. [B su telefono] Layout a 375 px quasi inutilizzabile
- Quadro: tutti. Passi: viewport 375x812, aprire la pratica, scegliere EC.
- Barra alta su 3 righe, barra di stato su 3 righe, elenco pratiche + sidebar + vista + pannello dati impilati con tre scroll annidati: del contenuto restano circa 150 px su 812 (`375_EC.png`, `375_AN.png`, `375_EA.png`). Nessun scroll orizzontale del documento (`scrollWidth` 375); le tabelle scorrono dentro `.tab`.
- Correzione: `static/app.css`, media query sotto 960 px: sidebar come cassetto apribile, pannello dati come foglio a tutto schermo con chiusura, barra di stato su una riga. Per un uso solo desktop scendere a "C".

### 2. [C alta] Riga aggiunta in un quadro "non selezionato": viene salvata ma il quadro non si attiva
- Quadri EL, EM, EN, EO, EP, EQ (e ogni quadro fuori da `quadri_attivi`). Passi: aprire EO, "Aggiungi riga", compilare, Salva. Esito: "Salvato", ma `stato` resta `inattivo` e compare il rilievo `DATI_IN_QUADRO_NON_ATTIVO` ("ci sono dati nel quadro EO ma il quadro non e' selezionato"). Il pulsante "Seleziona il quadro" esiste solo nella nota in cima (`EO_non_selezionato.png`); la casella "Quadri inclusi nella pratica" e' in fondo alla pagina Dati generali, chiusa. Anche i beni creati via API/MCP danno 6 rilievi.
- Correzione: `app.js` `aggiungiRiga()`/`salvaTutto()`: se `!q.attivo`, aggiungere l'operazione `set opzioni.quadri_attivi` (o chiedere conferma); in alternativa trasformare il rilievo in un link "Seleziona il quadro" (`insControlli`/`vaiA`).

### 3. [C] Errori di salvataggio: percorsi interni, gergo, nessun campo evidenziato
- Quadri EA, EO e tutti. Passi: EA, riga ROSSI LUCA, codice fiscale `ABC123` e data `10/02/1970`, Salva (`EA_errore_cf_data.png`); EO, valore `12,5` e quota `abc` (`EO_errore_valori.png`).
- Messaggi: `persone[p_erede01].codice_fiscale: codice fiscale di 16 caratteri alfanumerici`, `beni[b_e1afbd972a4f].valore: separatore decimale ',' non ammesso: usare '.'`, `quota non valida: 'abc' (usare num/den)`. Il percorso e' un id interno, "num/den" e' gergo (l'interfaccia chiede 1/2). Nessun campo e' marcato `.bad` e il focus non si sposta (`#ins .e` vuoto); il banner rosso in alto sposta tutto il layout di circa 44 px e non ha pulsante di chiusura. L'app accetta "10/02/1970" in digitazione e lo rifiuta solo al salvataggio; nessun selettore di data.
- Correzione: `app.js` `salvaOps()` (ramo `e.dati.errori`): tradurre `percorso` in etichetta (usando `etichetta()` e il nome del campo), marcare `[data-path=...]` con `.bad`, mettere il focus sul primo; `servizio.py`/`schema.py` messaggi senza `num/den`; per le date `<input type=date>` oppure accettare GG/MM/AAAA e convertire in `campoInput`. Il virgola decimale potrebbe essere convertito in `leggi()` invece di rifiutato.

### 4. [C] Sidebar sinistra a larghezza fissa (240 px), non ridimensionabile
- Tutti i quadri. 17 voci su 18 hanno il nome troncato e nessun attributo `title` (`EB`, `EC`, `EL`, `EM` leggibili solo come "Attivo e..."). Con testo a 22 px diventa "Dati gen...", "L non selezionato" (`1440_EC_testo22.png`); nel pannello i menu sono tagliati ("fabbricatc").
- Solo il pannello destro ha il separatore (`#ridimensiona`); `.lat` ha `resize:none` e nessun separatore.
- Correzione: `app.css` `.lat` con larghezza variabile e secondo separatore (stesso codice di `separatoreDati`); `app.js` `renderAlbero()`: `title: q.titolo`, nome su due righe.

### 5. [C] Valori esistenti non riconosciuti dai menu e menu troncati
- EC, EB, EL, EM, DV (campo `diritto`). Passi: EC, riga con `diritto = "proprieta"`: il menu mostra "proprieta (valore non previsto)" invece di "1 — Proprieta'" (`1440_EC.png`). Il menu "categoria" mostra "A2 — Abitazione di tipo c" tagliato (larghezza del select 194 px). I dati inseriti da MCP/API/vecchie pratiche usano spesso parole, non codici.
- Correzione: `app.js` `campoStrutturato()`: oltre a `norm()` provare un confronto con l'etichetta (`proprieta'`, `proprieta`) e mostrare la voce corrispondente; `title` su ogni `<option>`; `app.css` `.rg select{min-width:0;text-overflow:ellipsis}` e pannello piu' largo di default.

### 6. [C] Campi che dovrebbero essere menu (o scelta guidata) ma sono testo libero
Verificato nel pannello (`campi` di `audit1`), in parte possibile gia' in corso.
- EA: `relazione con defunto` (testo libero, duplica `grado parentela` che e' menu; allineata solo se vuota), `provincia nascita`, `provincia decesso`.
- EB/EC/EL/EM: `provincia`, `sezione`, `codice comune`, `codice comune amministrativo`, `comune amministrativo`, `provenienza`, `discordanza intestatario` e `passaggi senza atti legali` (nel XSD sono `DatoCB`, cioe' si/no), `sistema tavolare` (si/no); `classe`, `zona censuaria`.
- EO: `quantita`; EN: `codice fiscale emittente` (nome fuorviante per un'azienda); EP/EQ: `nazionalita`, `tipo unita` e' menu ma `nazionalita` no.
- ED: `possesso` (quota, ok ma senza placeholder), `estremi documento` libero.
- AN: tutte le date `AAAA-MM-GG` sono testo; `telefono`, `email`, IBAN solo testo senza controllo in digitazione.
- Il campo `tipo` (preimpostato dal quadro e quasi mai da cambiare) e' il primo campo del pannello con 9 voci grezze.
- Correzione: `schema.py` `STRUTTURATI`/`codici.py` per i codici dagli XSD (province: `typesProvincie_v2.xsd`); flag come `bool` (come in `CAMPI_DICH`); `codice comune` da un endpoint comuni (esiste `codice_fiscale.cerca_comune`, non esposto da `web.py`).

### 7. [C] Etichette grezze e non accessibili
- Tabelle: intestazioni minuscole da `replaceAll("_"," ")` (`quota defunto`, `luogo nascita`, `persona id`, `bene id`, `allegato id`, `tipo eg`, `PDF/A`). Pannello: `tipo cespite`, `particella denominatore`, `codice fiscale emittente`. Valori enum grezzi: `disponibilita_finanziaria`, `erede`, `altro`. AN: etichette in minuscolo (`cognome`, `nome`...) ripetute identiche per Defunto e Presentatore.
- Accessibilita': i `<label>` del pannello non hanno `for` (0 su 23 associati: cliccare l'etichetta non porta al campo); i campi di testo hanno `aria-label` con identificatori interni (`quota_defunto`, `codice_comune`, `discordanza_intestatario`), i menu strutturati un'etichetta diversa dalla visibile (`diritto del defunto` vs `diritto`).
- Correzione: `app.js` `insDati()` (label con `for` e `id` sul campo; `aria-label` = testo visibile), `renderTabella()` intestazioni da un dizionario di etichette (condiviso con `nomi` di `schedaPersona`), `campoInput()` per enum con etichetta. Probabilmente in corso (altro agente su app.js/etichette).

### 8. [C] Ordine dei campi diverso dal flusso del modulo/XSD
Probabilmente in corso. Il pannello segue l'ordine di `schema.COLLEZIONI`, non quello di `fornituraSUC13_v1.xsd` (Luogo -> dati catastali -> Possesso -> flag -> dati specifici):
- EA: dopo `ruolo`/`relazione` compaiono `data decesso`, poi `sesso`, `tipo soggetto`, `grado parentela`, `comune decesso`, `provincia decesso` (campi del defunto inseriti in mezzo a quelli dell'erede; `1440_EA.png`).
- EB/EC: `rendita` e `valore` prima di `diritto` e `quota defunto`; `codice comune`, `comune amministrativo` dopo `provenienza`; `natura`, `tipologia terreno`, `reddito dominicale` e i flag in fondo (`EB_pannello_fondo.png`); poi Superficie, Trascrizione, Registrazione.
- EO: valore/diritto/quota prima di `tipo titolo` e `quantita`. EN: `codice fiscale emittente` dopo la quota.
- Il quadro non mostra `sezione` in EB ma lo mostra in EC/EM; la colonna `provenienza` e' tagliata nella tabella EC (`1440_EC.png`).
- Correzione: `quadri.py` (aggiungere un ordine `campi` per quadro, gia' usato come filtro in `insDati`) e `insDati()` per usarlo come ordine.

### 9. [C] Tastiera e focus
- Ogni riga e' una tappa Tab; dopo l'ultima riga il Tab va a "Aggiungi riga", al separatore e alle schede, mai ai campi della riga selezionata; Invio seleziona ma non porta il focus al pannello (`audit3.json`, `tab_seq`). Il focus e' visibile (outline 2px). Con molte righe raggiungere il pannello richiede molti Tab.
- Correzione: `renderTabella()` roving tabindex (una tappa sola per tabella, frecce per le righe); `selezionaRiga()` con Invio sposta il focus sul primo campo.

### 10. [C] Quadri EE/EF/EH/EI: messaggi contraddittori
- Pagina EE (`1440_EE.png`): "non e' ancora supportato (quadro generato automaticamente dal programma: non si compila)" ma sotto "Seleziona il quadro (blocca la finalizzazione)". Nel wizard (`1440_WIZ3.png`, `375_WIZ3.png`) EF/EI hanno "(non ancora supportato: blocca la finalizzazione)" e controlli resi con cerchi anziche' caselle. Per l'utente non e' chiaro se serva selezionarli.
- Correzione: `app.js` `renderNonSupp()` e `wizRender()`: testo distinto per quadri generati (nessuna azione) e quadri davvero non gestiti.

### 11. [E] Contrasto
- Tema chiaro: testo secondario `#6e6e73` sulla sidebar (etichette, "non selezionato", titoli gruppo) circa 4,4:1, sotto 4,5:1 (calcolo approssimato). Tema scuro: 5,6:1, ok. Tema chiaro: voci inattive in grigio chiaro con sigla su fondo grigio (`1440_EC.png`).
- Correzione: `app.css` variabile del grigio secondario.

### 12. [E] Varie
- `GET /favicon.ico` 404 a ogni caricamento (`index.html`: aggiungere `<link rel="icon" href="/static/logo.svg">`).
- Id di pratica: `p_def` o `b_fab` danno "identificativo non valido" senza indicare il formato richiesto (`servizio.py` `_applica`): messaggio da API/MCP da migliorare (`ID_VALIDO`).
- Dialoghi (Impostazioni, wizard) a 375 px: ok, senza overflow (`375_IMPOST.png`). Pannello a 760 px lascia alla tabella 430 px (`1440_EC_pannello_max.png`); a 1024 px: vista 494, pannello 280.
- Il separatore da tastiera (Home/End/frecce) funziona e persiste (280-760 verificato, salvato su `/api/impostazioni`).

## (g) Funzioni dell'app dell'Agenzia che mancano (solo quelle motivabili)

1. Totali e riepilogo dell'asse ereditario (EE) e liquidazione (EF): l'XSD prevede `TotaleValoreImmobili`, `TotaleValoreAziende`, `TotaleValoreTitoli`, `TotaleValoreAereiNavi`, `TotaleValoreAltriBeni`, `TotaleAttivo`, `TotalePassivo`, `TotaleValoreAsseEreditarioNetto` (`fornituraSUC13_v1.xsd`, circa righe 599-640) e la fonte `All. Specifiche tecniche (passaggi calcolo imposta)...pdf` descrive il calcolo; `telematico/esporta.py` li produce, ma la GUI non mostra nessun totale prima della generazione del file (EE/EF/EH sono solo pagine di avviso).
2. Gestione delle pratiche: nessuna eliminazione, duplicazione, rinomina o archiviazione (barra in alto e `web.py` non espongono tali rotte; il titolo si fissa alla creazione).
3. Ricerca/autocompletamento di comune, provincia e codice catastale: l'XSD distingue i campi del luogo (`reg:Luogo_Type`) e il backend ha `cerca_comune`, ma la GUI usa testo libero (problema 6).
4. Stampa/anteprima del modello compilato quadro per quadro: esiste solo "Stampa prospetto" dopo la generazione del file (`File e invio`).
5. Indicazione di obbligatorieta' e avanzamento per campo: lo stato dei quadri e' solo "da compilare/compilato/rilievi".

## Cosa ha funzionato
Menu dei codici ufficiali per stato civile, tipo soggetto, grado, categoria (53 voci), natura, tipologia, tipo cespite, tipo titolo, diritti per tipo di bene; DV e ED mostrano nomi (non id) per bene e persona; il colore, i temi chiaro/scuro e il pannello ridimensionabile da tastiera; nessun overflow orizzontale del documento a 375/1024/1440; File e invio, Impostazioni e wizard senza errori JS; messaggio chiaro "manca il codice fiscale del fornitore" alla generazione; messaggi di importazione "file non importabile: non e' un XML valido" e "file vuoto" (ma con il codice `RICHIESTA_NON_VALIDA` esposto all'utente solo via fetch diretto).
