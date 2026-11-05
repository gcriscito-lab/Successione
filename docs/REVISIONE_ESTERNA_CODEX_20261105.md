# Revisione esterna del programma Successioni — 5 novembre 2026

Commit esaminato: `b94bf9587767ffc8083da84d7455eef1fb958a0d`.

Ambiente: Windows, Python della `.venv` del progetto, Chromium tramite Playwright; archivio GUI sintetico separato in `build/review_20261105_gui`, porta locale 8813. Nessuna pratica reale, credenziale, sessione autenticata o trasmissione. Codice applicativo e test lasciati invariati. Il presente documento è l'esito della revisione; gli altri file prodotti dalle prove sono temporanei sotto `build/`.

## 1. Esito

**NON OK per l'obiettivo di un programma SUC13 completo e utilizzabile su tutte le casistiche previste dalla specifica.** La base applicativa è ampia e supera 1.018 test Python, ma ho riprodotto **quattro bug applicativi, due di gravità alta**, e rimangono funzioni essenziali incomplete.

I due problemi da correggere per primi sono la contaminazione anagrafica fra pratiche dovuta a risposte asincrone tardive e l'esportazione di una sostitutiva come prima dichiarazione. I test superati non coprono questi due percorsi.

Il giudizio non significa che ogni funzione sia difettosa: archivio transazionale, revisioni, allegati originali, verifica XSD, numerose regole numeriche, integrazione MCP locale e gran parte dell'interfaccia hanno riscontri positivi. Prima casa, titoli esenti e riduzioni art. 25/L/Q/R/F sono già presenti, entro un perimetro parziale: non vanno elencati come funzioni interamente assenti.

Non attribuisco una percentuale di completamento: il numero di quadri presenti e il numero di test non misurano la copertura delle casistiche fiscali o l'effettiva operatività dei collegamenti.

## 2. Quadrature eseguite

### Risultati effettivi

| Prova | Risultato | Significato e limite |
|---|---|---|
| `.venv\Scripts\python.exe -m pytest -q -rs --tb=short --basetemp=build/review_20261105` | **1.018 passati, 2 saltati**, 2 warning; 785,42 secondi | Suite corrente completa; nessun fallimento Python. Non prova casistiche prive di test. |
| `python scripts/verifica_materiali.py` | **Passato: 23 materiali integri** | 8 PDF, 13 XSD, 2 JNLP; prova delle impronte locali, non della disponibilità di aggiornamenti ministeriali successivi. |
| `tests/e2e/gui_regressioni.js` su Chromium | **Passato** | Risposta lenta al salvataggio, rifiuto del secondo salvataggio concorrente, eliminazione riga, nuova riga modificata durante HTTP, conservazione buffer su 422 e conflitto 409. |
| `tests/e2e/gui_layout_20261103.js` su Chromium | **Passato** | Trascinamento barra, persistenza larghezza, tastiera, label associate, assenza di ID duplicati, favicon e layout a 375/768/1024/1440 pixel. Adattati in memoria solo i percorsi degli screenshot da `C:/sx/` a `build/`; nessun file sorgente modificato. |
| `tests/e2e/gui_aspetto.js` senza adattamenti | **Fallito** | Timeout al selettore della provincia a riga 57: il test cerca il vecchio input, mentre il programma ora presenta un menu strutturato. Vedi R05. |
| Stesso test di aspetto con soli selettori provincia adattati in memoria e `selectOption` | **Passato** | Logo iniziale, font/dimensione/tema, tema di sistema, salvataggio, annullamento anteprima, provincia, ispettore ridimensionabile, area File unica, conservazione profilo e responsive. Questo risultato non rende verde lo script originale. |
| Quattro prove aggiuntive mirate | **Quattro difetti riprodotti** | R01–R04 sotto; archivi temporanei e dati sintetici. |
| `git diff --stat` sul codice alla conclusione delle prove | **Nessuna modifica applicativa** | Escluso questo rapporto aggiunto successivamente. HEAD invariato durante la revisione. |

I due test saltati sono:

- `tests/test_documenti_dimensioni.py:44`: `pdftotext` non disponibile.
- `tests/test_installazione.py:377`: non impostato `SUCCESSIONI_PACCHETTO_WIN` con la cartella del pacchetto costruito.

I due warning riguardano `pypdf.add_js` deprecato, usato per costruire PDF ostili sintetici nei test. Non sono un errore di calcolo né un fallimento della conversione.

Ghostscript era disponibile in `C:\gs\gs10.08.0\bin\gswin64c.exe`, veraPDF in `C:\veraPDF\verapdf.bat`; i componenti SUC13 e Java risultavano configurati (`_motivo_salto()` del controllo ufficiale restituisce `None`). Pertanto i test del controllo ministeriale locale non sono stati saltati per assenza dei componenti. Queste prove restano controlli **locali su dati sintetici**, senza autenticazione o invio all'Agenzia.

### Aree con riscontri positivi

- **Archivio e servizio condiviso:** SQLite con transazioni, revisioni attese e chiavi per richieste ripetute; test di conflitto, persistenza e ripristino. Il ripristino controlla database, riferimenti, percorsi e impronte prima di sostituire una destinazione vuota (`archivio.py`, `integrita.py`).
- **Documenti:** conservazione di originali e derivati distinti, controlli di appartenenza e impronta degli allegati prima dell'export, conversione/validazione PDF/A e suddivisione nel perimetro dei test. Rimane da provare la fedeltà su un corpus operativo reale autorizzato.
- **XML e calcolo:** XSD locali, identificativi, quote esatte, continuazioni e totali; casi positivi e negativi del componente SUC13 locale. Non ho dimostrato un nuovo errore sostanziale negli importi del perimetro provato. Il problema R02 riguarda la natura della dichiarazione, anche quando gli importi sono coerenti.
- **Interfaccia:** le richieste su impostazioni, font, tema, logo, provincia, area File unica e larghezza dei pannelli risultano attuate nelle prove descritte. Le prove di layout non eliminano il difetto asincrono R01.
- **Sicurezza dei confini esaminati:** controlli Host/token/Origin dell'interfaccia locale, restrizioni dei file statici, parser XML con entità esterne disabilitate, delimitazione dell'ingresso MCP e divieto di conferma dell'invio da MCP. Non ho riprodotto un accesso arbitrario a file o una trasmissione non autorizzata. Questa revisione non costituisce una prova esaustiva di sicurezza.

## 3. Rilievi

Priorità: P1 = da correggere prima dell'uso operativo; P2 = errore funzionale da correggere; P3 = manutenzione e affidabilità delle evidenze. Nessun rilievo è classificato come perdita irreversibile già avvenuta su dati reali.

### R01 — P1, alta: una risposta del codice fiscale può scrivere nella pratica successiva

**File e righe:** `src/successioni/static/app.js:728`, `:1055–1061`; cambio pratica in `:135–147`.

**Fatto verificato.** `suggerisciDaCF` attende la risposta HTTP e poi usa le callback di scrittura senza verificare che siano ancora correnti pratica, persona e codice fiscale. La callback di `schedaPersona` scrive nella mappa globale `S.dirty`. Il cambio pratica svuota la mappa, ma non annulla le richieste già in corso.

**Riproduzione in Chromium con la risposta reale del decoder locale:**

1. Creare due pratiche sintetiche A e B, ciascuna con un defunto avente ID `p_defunto1`. L'identità dell'ID fra pratiche è ammessa ed è normale nelle importazioni XML.
2. In A inserire `RSSMRA40A01H501K`, togliere il focus dal campo e ritardare la risposta `/api/codice-fiscale` tramite Playwright, senza modificarne il contenuto.
3. Aprire B e accettare l'abbandono delle modifiche di A. Subito dopo l'apertura la mappa delle modifiche è vuota: `[]`.
4. Rilasciare la risposta di A. Nella pratica B compaiono modifiche anagrafiche estranee.
5. Premere Salva: il defunto B viene persistito con `data_nascita=1940-01-01`, `luogo_nascita=ROMA`, `sesso=M`, `provincia_nascita=RM`, derivati dal codice fiscale della pratica A. Nessun errore JavaScript.

**Impatto:** contaminazione dei dati fra pratiche al successivo salvataggio. Il controllo del checksum del codice fiscale non protegge da questo errore di associazione.

**Correzione suggerita:** associare ogni richiesta a pratica, soggetto, valore CF e generazione del caricamento; prima di applicare il risultato verificare tutti questi riferimenti. Annullare o scartare le risposte dopo cambio pratica, modifica del CF o chiusura della procedura guidata. Applicare lo stesso criterio ai caricamenti di pratica, quadri e pannelli: `ricarica` assegna separatamente lo stato globale dopo due `await`.

**Test necessario:** risposta tardiva dopo cambio pratica con ID uguale; risposta del CF A dopo sostituzione con CF B; nuova apertura della procedura guidata mentre una risposta precedente è pendente. I primi passi sopra sono riprodotti; gli ultimi scenari sono regressioni da aggiungere, non ulteriori bug conteggiati separatamente.

### R02 — P1, alta: la sostitutiva viene generata come prima dichiarazione e marcata completa

**File e righe:** `src/successioni/telematico/esporta.py:1435`; ingresso servizio `src/successioni/elaborati.py:66–84`; rilievo già previsto in `src/successioni/quadri.py:148–150`; preparazione in `src/successioni/invio_servizio.py:37–60`.

**Fatto verificato.** La GUI permette di scegliere `opzioni.tipo_dichiarazione="sostitutiva"`. I controlli la dichiarano non supportata, ma l'esportatore imposta sempre `PrimaDichiarazione=1`; né il servizio di export né quello di preparazione applicano quel blocco preliminare.

**Riproduzione:** partire dalla pratica sintetica completa costruita da `tests/test_correzioni_codex.py::pratica_con_allegati`, impostare il tipo sostitutiva, quindi chiamare `s.esporta(pid)` e `s.invio_prepara(pid)`.

Risultato effettivo:

```json
{
  "generato": true,
  "completo": true,
  "finalizzabile": false,
  "rilievi": ["SOSTITUTIVA_NON_SUPPORTATA"],
  "prima_dichiarazione": true,
  "copia_preparata": "preparata"
}
```

**Impatto:** si scarica un file completo che rappresenta un'operazione diversa da quella scelta. Il file può essere usato fuori dall'applicazione. Il fatto che l'app richieda successivamente il controllo ufficiale per la conferma non corregge il tipo errato serializzato. La prova non ha trasmesso o confermato nulla e non dimostra un aggiramento dei requisiti di trasmissione.

**Correzione suggerita:** rifiutare il tipo non supportato direttamente nell'esportatore e nel servizio comune a GUI/MCP. Anche la preparazione deve rispettare i blocchi applicativi pertinenti. Separare i controlli preliminari da quelli che dipendono dall'esistenza dell'export, per evitare una dipendenza circolare da `finalizzabile`.

**Test necessario:** tipo sostitutiva con tutti gli altri dati validi: nessun XML completo e nessuna preparazione. Verificare GUI, MCP e chiamata diretta dell'esportatore. L'implementazione fiscale della sostitutiva resta una funzione mancante distinta dal bug di conversione silenziosa in originaria.

### R03 — P2, media: una nota interna blocca la preparazione di un XML ancora aggiornato

**File e righe:** `src/successioni/invio_servizio.py:60`; `src/successioni/collegamenti/invio.py:272–275`; esclusione intenzionale delle note in `src/successioni/servizio.py:33–47`.

**Fatto verificato.** L'impronta dichiarativa esclude correttamente le note interne, quindi l'export resta aggiornato quando cambia soltanto una nota. La preparazione passa però la vecchia revisione dell'export all'adattatore, che confronta il numero di revisione invece della rilevanza dichiarativa della modifica.

**Riproduzione:** creare la pratica sintetica completa, esportarla, aggiornare soltanto `note.interna`, chiamare `invio_prepara`.

```text
stato_elaborati(pid)["export"]["stato"] = "aggiornato"
ConflittoRevisione: la pratica e' cambiata: rigenerare gli elaborati
```

**Impatto:** percorso operativo contraddittorio; obbliga a rigenerare il file dopo una modifica irrilevante, contro il requisito A16 di invalidazione selettiva. Non è una perdita di dati.

**Correzione suggerita:** verificare l'impronta dichiarativa dell'export contro la pratica corrente nel momento del congelamento, conservando la revisione per tracciabilità. Evitare di eliminare indiscriminatamente il controllo di concorrenza: una vera modifica dichiarativa deve continuare a bloccare.

**Test necessario:** nota interna dopo export e dopo controllo ufficiale; preparazione consentita a parità di dichiarato. Variazione di importo, beneficiario o allegato: preparazione rifiutata o copia invalidata.

### R04 — P2, media: la rigenerazione non ripara un XML alterato sul disco

**File e righe:** `src/successioni/elaborati.py:85–99`; rilevamento dell'alterazione in `:40–42`.

**Fatto verificato.** Il nome dell'XML deriva dall'hash dei byte corretti rigenerati. Quando il percorso esiste, `esporta` salta la scrittura senza confrontarne il contenuto. Registra ugualmente un nuovo successo. `file_export` rileva poi l'impronta errata e invita nuovamente a rigenerare.

**Riproduzione su archivio temporaneo:** esportare una pratica completa; sostituire il contenuto del file esportato con `ALTERAZIONE SINTETICA`; riesportare senza modificare la pratica; tentare di scaricare il file.

```text
secondo export: generato=True, completo=True, stato=aggiornato
file sul disco: ALTERAZIONE SINTETICA
download: file XML alterato: rigenera l'esportazione
```

**Impatto:** procedura di recupero inefficace e falso esito positivo della rigenerazione. Il controllo di integrità evita correttamente di restituire i byte alterati: non ho osservato un'accettazione del file corrotto al download.

**Correzione suggerita:** verificare l'impronta del file preesistente; se diversa, ripristinare atomicamente i byte appena generati oppure segnalare un errore esplicito senza registrare successo. Applicare una politica chiara di conservazione dell'evidenza del file alterato.

**Test necessario:** corruzione e rigenerazione, successivo download corretto, controllo e preparazione sulla stessa impronta. Verificare anche un file esistente integro, che deve restare riutilizzabile.

### R05 — P3, bassa: test browser e documentazione di copertura non allineati al programma

**File e righe:** `tests/e2e/gui_aspetto.js:57`, `:63`; `docs/MATRICE_COPERTURA.md:24`, `:28`, `:31–32`, `:73–74`; intestazione e prime sezioni di `docs/STATO_LAVORI.md`.

**Fatti verificati:**

- Il test di aspetto cerca `aria-label="provincia_nascita"` e usa `fill`; il campo corrente è un menu strutturato con etichetta italiana. Il test originale fallisce prima di completare le verifiche successive. Adattando esclusivamente questi selettori e il tipo d'interazione, il flusso passa.
- La matrice indica fra i campi non coperti del frontespizio `Versamento` e `ImportoDaVersare`, mentre la riga EF li descrive supportati e i test ne verificano il contenuto.
- La riga EG elenca il testamento fra i non coperti, ma l'export e i test testamentari lo gestiscono. La riga EH elenca le sezioni II–IV fra i non coperti pur descrivendo già la II e, nella riga art. 25, una parte della IV.
- Le sezioni iniziali di `STATO_LAVORI.md` descrivono calcoli/XML/stampa come ancora assenti e conteggi di test storici, poi sono seguite da aggiornamenti successivi: manca una sintesi corrente univoca.

**Impatto:** verifiche manuali non ripetibili senza adattamenti e difficoltà nel capire quali casi siano davvero utilizzabili. Le discrepanze documentali non dimostrano da sole un errore fiscale.

**Correzione suggerita:** aggiornare i test browser ai controlli attuali e includerli in una procedura di verifica ripetibile. Riscrivere la matrice sintetica sulla base del codice e dei casi attesi; tenere la cronologia in una sezione separata. Registrare commit, componenti e casi di riferimento per ciascun esito.

## 4. Punti aperti e funzioni mancanti

### Copertura necessaria per l'obiettivo della specifica

La specifica `docs/02_SPECIFICA_E_COLLAUDO.md`, sezioni 1 e 4, richiede tutti i quadri/casi pertinenti, stampa, collegamenti reali, portabilità e conservazione. La disponibilità di una maschera per un quadro non prova che tutti i suoi casi siano esportabili.

| Priorità di completamento | Capacità | Stato riscontrato e lavoro residuo | Riferimento tecnico |
|---|---|---|---|
| Alta | Sostitutive/integrative | Mancano gestione della dichiarazione precedente e relativi dati/calcoli; correggere subito R02 prima di estendere il supporto. | `quadri.py:148`; `calcolo.py:189`; `esporta.py:1435` |
| Alta | Devoluzione legittima più ampia | Verifica automatica limitata a soli figli, solo coniuge, coniuge e figli. Ascendenti, fratelli/unilaterali, rappresentazione e altri assetti bloccano il completo se non coperti. Servono regole, fonti e casi indipendenti. | `telematico/devoluzione_legge.py:17–18`; `esporta.py:1584` |
| Alta | Immobili in più comuni e liquidazione EF completa | L'export blocca più comuni perché manca la determinazione delle conservatorie. Restano fuori anche i casi dei soli terreni e alcune relazioni fra imposta proporzionale e fissa. | `telematico/quadri_efgh.py:91–148` |
| Alta | Pagamenti e decorrenze | Supporto parziale alla tempistica ordinaria; fuori rateazione prevista nel modello, tardive con imposta dovuta, decorrenze particolari, sanzioni/interessi, crediti e casi storici. Distinguere i campi necessari SUC13 dallo scadenzario/F24 accessorio. | `quadri_efgh.py:234–258`; `calcolo.py:26–30` |
| Alta | Catasto Entratel effettivo | Adattatore, normalizzazione e importazioni sintetiche presenti; il trasporto predefinito restituisce sempre `non_disponibile`. Non è completata l'acquisizione autenticata richiesta dalla specifica. | `collegamenti/catasto.py:87–88` |
| Alta | Invio e acquisizione automatica ricevute | Presenti copia congelata, conferma, simulazione, istruzioni manuali e registrazione dei documenti. Il trasporto manuale non trasmette; mancano il collegamento reale e il download autenticato delle ricevute. | `invio_servizio.py:1–10`; `collegamenti/invio.py:178–181` |
| Alta | Stampa del modello ministeriale | Esiste un prospetto HTML dei dati XML, correttamente etichettato come non ministeriale. Manca la stampa del modello da presentare/sottoscrivere e il relativo collaudo visivo. | `stampa.py:7`; `mcp_server.py:21` |
| Media | Prima casa completa | Già implementati P/X/Z nel perimetro descritto e testato. Restano Y, Z senza P, fabbricati tavolari EM, diritto di abitazione, requisiti esteri/forze armate e credito d'imposta. | `telematico/prima_casa.py:1–20`, `:86–91`, `:163–168` |
| Media | Altre agevolazioni/riduzioni | Già presenti art. 25 codici 1–5 e L/Q/R/F per i quadri ammessi. Mancano A/C/D/E/G/H/M/N, combinazioni agevolazione più riduzione sulla stessa riga, DN/titoli esenti, alcune combinazioni e più righe R/F dello stesso beneficiario. | `telematico/calcolo.py:26–30`, `:166–178`; `riduzioni_art25.py` |
| Media | Estero e soggetti particolari | Non completati beni/imposte estere e relativa detrazione, enti/trust, rappresentanti/cariche ulteriori, rinunce, più qualifiche della stessa persona e ulteriori dichiarazioni EH. | `calcolo.py:26–30`, `:344–353`; controlli in `esporta.py` e `quadri_efgh.py` |
| Media | Casi immobiliari e continuazioni residue | Mancano immobili graffati/aziendali e altre casistiche fuori perimetro, rendita proposta, più di tre destinatari ED, continuazioni EI oltre il limite supportato e più mezzi nella relativa dichiarazione EH. | `esporta.py`, `quadri_efgh.py`; matrice da riallineare con R05 |
| Media | Importazione senza reinserimenti | L'importatore ora comprende EA/EB/EC/ED/EI/EL/EM/EN/EO/EP/EQ/ER. EG e EH non vengono ricostruiti; agevolazioni/riduzioni e altri campi non letti vengono rifiutati esplicitamente. Non si riapre integralmente ogni file prodotto dal programma, ad esempio con prima casa. | `telematico/importa.py:35–39`, `:663–684`; `tests/test_review_20261103.py:19` |
| Media | Portabilità della singola pratica | Esistono backup/ripristino complessivi e import XML parziale. Manca un flusso utente completo di esportazione/reimportazione della singola pratica con dati di lavoro, allegati originali, provenienza e controlli, distinto dall'XML telematico. | API di `servizio.py`; comandi di `cli.py:18–21` |
| Media | Versionamento delle regole e rilascio | Regole identificate come `0.1-bozza`; serve una gestione operativa verificata degli aggiornamenti di regole/tabelle/componenti e della ricostruzione dei risultati delle pratiche già lavorate. Non basta cambiare il numero di versione. | `servizio.py:21`; specifica §3 e A20 |
| Successiva | Assistenze di compilazione | Calcolo del valore catastale dalla rendita, proposta completa delle quote, generazione dell'albero genealogico e documenti accessori possono ridurre il lavoro manuale; non sono tutti indispensabili per ogni pratica già coperta. | matrice, righe EB/EC; specifica §4 |

L'elenco distingue limiti di progetto già dichiarati da nuovi difetti. L'assenza di un collegamento reale non va corretta sostituendo uno stato simulato con «passato». Occorrono implementazione, ambiente autorizzato e prove con evidenze.

### Stato ragionato dei requisiti A01–A20

| Requisiti | Valutazione dopo questa revisione |
|---|---|
| A01 installazione | Avvio sorgente provato; collaudo del pacchetto corrente non eseguito, relativo test saltato. |
| A02 salvataggio/ripristino | Prove locali positive; nessuna nuova perdita d'archivio riprodotta. |
| A03 GUI/MCP | Servizio comune e test del protocollo presenti; client Claude effettivo e ciclo operativo completo non provati in questa revisione. |
| A04 concorrenza/idempotenza | Test del servizio e dei salvataggi GUI positivi; non coprono le risposte anagrafiche tardive di R01. |
| A05 quote/continuazioni | Positivo nel sottoinsieme testato; diritti distinti e continuazioni residue impediscono la copertura generale. |
| A06–A08 casistiche/calcoli | Numerosi test, prima casa e art. 25 compresi; inventario, qualifiche multiple, estero, storico e combinazioni restano parziali. |
| A09 XML/stampa | XML locale testato; R02 e R04 da correggere, stampa ministeriale mancante. |
| A10 controllo ufficiale | Prove del componente locale eseguite nella suite; non equivalgono a un invio o a un collaudo autenticato. |
| A11–A12 PDF/A/documenti | Conversione e validazione locali disponibili e testate; confronto testuale della suddivisione saltato per assenza di `pdftotext`; documenti reali non esaminati. |
| A13 catasto | Acquisizione autenticata non disponibile. |
| A14–A15 import/ripresa | Test locali e simulazioni degli adattatori; sessione reale non provata. |
| A16 invalidazione selettiva | R03 dimostra un difetto nella preparazione dopo una nota interna. |
| A17 preparazione/conferma | Meccanismi implementati e testati, con R02–R03 ancora da risolvere. |
| A18 invio incerto | Gestione locale simulata testata; nessuna prova di trasporto reale. |
| A19 ricevute | Associazione e stati locali testati; non prova download autenticato, contenuto o autenticità di ricevute effettive. |
| A20 copertura/aggiornamento | Parziale; R02 viola il blocco dei casi non supportati, R05 rende incoerente la matrice sintetica. |

### Ordine proposto degli interventi

1. Correggere R01 e R02, aggiungendo le rispettive regressioni a livello browser e servizio/esportatore.
2. Correggere R03 e R04; riallineare test e matrice con R05.
3. Completare le casistiche operative più frequenti oggi bloccate: assetti successori, più comuni/conservatorie, prima casa residua, pagamenti e sostitutive.
4. Realizzare stampa ministeriale e portabilità integrale della pratica.
5. Implementare e collaudare i collegamenti reali previsti; verificare il pacchetto Windows dello stesso commit e il client MCP effettivo.

L'accettazione deve basarsi su casi positivi, negativi, salvataggio/riapertura, export/import e confronto con componenti ufficiali, con input e versioni registrati. Un test che verifica solo che compaia un codice o che esista un pulsante non dimostra il risultato operativo.

## 5. Cosa non ho potuto verificare

- Installazione pulita, aggiornamento e ripristino del pacchetto Windows corrente: il percorso richiesto dal test non era configurato. Non deduco dal funzionamento della `.venv` che un eseguibile distribuito contenga questo commit.
- Accesso Entratel/catasto, autenticazione/autentica del file, trasmissione effettiva e download delle ricevute: non eseguiti e, nei trasporti predefiniti esaminati, non disponibili come automazione reale.
- Uso con il client Claude effettivo e ciclo di vita completo di quel client; la suite del server MCP non sostituisce tale prova.
- Correttezza documentale e fiscale di una pratica reale, visure effettive, documenti sottoscritti e fedeltà visiva di tutte le conversioni: usati soltanto dati sintetici.
- Aggiornamenti delle fonti ministeriali successivi ai materiali locali: verificata l'integrità delle copie presenti, senza una nuova ricerca normativa o aggiornamento remoto. Il rapporto descrive il software e i suoi limiti; non certifica la vigenza universale delle regole fiscali.
- Assenza assoluta di ulteriori bug o vulnerabilità: lettura del codice, test e riproduzioni forniscono evidenze nei percorsi esaminati. I quattro difetti sopra sono verificati; gli altri limiti sono indicati come capacità residue o collaudi mancanti.

Il codice non è stato corretto in questa revisione. Non ho consultato `docs/archivio/REVISIONE_INDIPENDENTE.md`, per mantenere indipendente il giudizio come richiesto dal brief.
