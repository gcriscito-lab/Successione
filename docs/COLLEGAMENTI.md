# Collegamenti ufficiali: stato, prove e fonti (area 3)

Aggiornato al 2026-11-01. Parole-esito come in `docs/COLLAUDO_CLOUD_WINDOWS.md`: **passato** / **fallito** (prova
eseguita sul componente o servizio reale, input/output/ambiente registrati), **da_collaudare** (prova non eseguibile
qui; procedura in `docs/COLLAUDO_RIPRENDIBILE.md`), **simulazione** (test locale dell'adattatore: non prova
l'interoperabilita' con l'Agenzia). Codice: `src/successioni/collegamenti/`; test: `tests/test_collegamenti_*.py`.

## Quadro sintetico

| Collegamento / capacita' | Esito | Evidenza |
|---|---|---|
| Invocazione del controllo ufficiale SUC13 dall'app, senza GUI (Linux, OpenJDK 21) | **passato** | 2026-11-01: componente 2.3.1 eseguito tramite `ControlloJar`, diagnostico originale conservato (§1) |
| Lettura del diagnostico originale (`.dgn`, `_logSchema.xml`, `.wri`) | **passato** | lettori provati su 2 registrazioni reali; `_logSchema.xml` valido su `esitoFornitura_v3.xsd` delle fonti |
| A10: diagnostico positivo + negativo predisposto, sul PC di destinazione | **da_collaudare** | negativi reali ottenuti; manca un caso positivo (serve un XML completo: EF/EG/EH non ancora esportati dall'area 1) e la prova su Windows |
| File controllato `.dcm` (terzo argomento) | **da_collaudare** | prodotto dal componente solo per forniture trasmissibili: non ancora osservato |
| Passaggio manuale tracciato del controllo | **da_collaudare** | implementato e provato con file reali registrati; uso sul PC Windows da provare |
| Risultanze catastali via Entratel (A13) | **da_collaudare** | nessuna interfaccia o formato documentato trovato; nessun endpoint inventato (§2) |
| Macchina a stati catasto, ripresa, duplicati, importazione selettiva (A14, A15) | **simulazione** | `tests/test_collegamenti_catasto.py` su fixture sintetiche |
| Trasmissione SUC13 (Desktop Telematico / Entratel-Multifile) | **da_collaudare** | il programma non trasmette: trasporto "manuale tracciato" + riconciliazione (§3) |
| Copia congelata, conferma, invalidazione (A16, A17) | **simulazione** | `tests/test_collegamenti_invio.py` |
| Invio incerto senza reinvio cieco (A18) | **simulazione** | rete interrotta prima/dopo la ricezione, processo interrotto, riconciliazione con `.esi` |
| Ricevute ed esiti separati (A19) | **simulazione** per l'associazione; **da_collaudare** per i canali reali | tipi dal Fascicolo I p. 5 (§4) |

## 1. Controllo ufficiale SUC13

**Modalita' provata.** I 15 JAR elencati in `fonti/Programma e controlli/ControlliSUC13.jnlp` (identico a quello
pubblicato) sono stati scaricati dal codebase `https://jws.agenziaentrate.it/jws/registro/2013/` il 2026-11-01:
impronte uguali a quelle di un download precedente della sessione, firme verificate con `jarsigner -verify`
("jar verified", certificato SOGEI SPA emesso da Sectigo). Impronte di riferimento in
`collegamenti/collaudo.py` (`IMPRONTE_20261101`).

L'avviatore AWT `it.finanze.entrate.sco.applet.AControlliSUC2013` (metodo `run`, ispezione `javap -c`) chiama per
riflessione `MSUC13.main` con `{input, uscita}` o `{input, uscita, dcm}` e poi `VisualXml.main({file.dgn, flag})`.
La stessa sequenza, eseguita direttamente, funziona senza interfaccia grafica:

```
java -Djava.awt.headless=true -Djava.io.tmpdir=<lavoro>/tmp -cp <15 JAR> it.finanze.entrate.sco.main.MSUC13 in/F.xml out/F.xml [out/F.dcm]
java -Djava.awt.headless=true -cp <15 JAR> it.finanze.entrate.sco.common2013.VisualXml out/F.dgn 1
```

Uscite: `F.dgn` (record di 105 caratteri + fine riga), `F_logSchema.xml` (`EsitoFornitura`, namespace
`...sco:common:v3`), `F.wri` (rapporto leggibile con legenda e riepilogo). Il flag `1` = elenco completo dei
diagnostici (`2` esclusi dall'assistenza 730, `3` solo scartate: caselle `check1..3` dell'avviatore).

**Prove eseguite (2026-11-01, container Linux x86_64, OpenJDK 21.0.12.1, controllo 2.3.1 dell'11/03/2026):**

| Input sintetico | SHA-256 input | Esito componente | Esito adattatore |
|---|---|---|---|
| `frontespizio.xml` (solo frontespizio, CF fittizi) | `02d93434bb40...a06d710` | schema valido; 1 dichiarazione scartata: 7 errori (***) (EG/EH/EA obbligatori, CF errati, telefono) e 1 (*) | **fallito**, stato `negativo` |
| `minimo.xml` (manca `TipoFornitore`) | vedi manifest | schema non valido, record (****) "scarto dell'intera fornitura" | **fallito**, stato `negativo` |
| export "bozza tecnica" dell'area 1 (`tests/telematico_casi.py`, caso completo) | `69de9992c59e...591e57` | scartata: EF/EG/EH obbligatori, CF con carattere di controllo errato, numero soggetti in devoluzione, quote ER incoerenti con la devoluzione per legge | **fallito** (prova d'integrazione, non registrata nel repository) |

Registrazioni (input, `.dgn`, `_logSchema.xml`, `.wri`, manifest con ambiente e impronte dei JAR):
`src/successioni/collegamenti/fixture/controllo_reale_20261101/`. Il componente non ha modificato l'input
(impronta uguale prima e dopo).

**Tracciato del `.dgn` (solo cio' che e' deducibile dal componente).** Classe
`it.finanze.entrate.sco.generale2013.Visual` di `controlliXMLREG2013.jar`, ispezione `javap -c -constants`:
- record `0`: intestazione (modello, versione `2.3.1`, data `11/03/2026`; secondo record = nome del file);
- record `1`: `[1:17]` soggetto (CF del defunto o `VALIDAZIONE...`), `[17:19]` gravita' -> `impostaAsterischi`:
  4=(*), 8=(**), 12=(**E) solo 730, 14=(***C), 15-23=(***), >=24=(****); `[19:23]` codice messaggio;
  `[23:39]` campo; `[39:55]`, `[55:71]`, `[71:84]`, `[84:100]` valori; `[100:105]` identificativo dichiarazione;
- record `9` (`coda`): elaborate `[1:7]`, senza segnalazioni `[7:13]`, con anomalia `[13:19]`, errori confermati
  `[19:25]`, escluse assistenza `[25:31]`, non rispondenza `[31:37]`, scartate per errori bloccanti `[37:43]`;
  `[85:86]=1` -> "trasmissibile esclusivamente con Entratel".
I testi dei messaggi non vengono ricostruiti (stanno nelle risorse del componente): fanno fede `.wri` e `.dgn`.

**Valutazione** (`controllo.valuta`): `positivo` solo se schema valido, almeno una dichiarazione elaborata, nessuna
scartata e nessun diagnostico di gravita' >= 14; altrimenti `negativo`; senza `.dgn` `non_verificabile`. Un
esecutore iniettato (test) produce sempre `simulazione`, anche con un diagnostico positivo.

**Avvertenze d'ambiente rilevate.** Con Java >= 11 l'inizializzazione del modulo di stampa (`PrintModel.init`,
Spring) fallisce per `javax/annotation/PostConstruct` assente; il controllo prosegue e conclude. Compare anche
"could not locate enum table ... ProvincieItaliane" (XMLBeans). L'equivalenza con l'esecuzione in Desktop
Telematico (JRE proprio) va provata sul PC (A10). Il JNLP dichiara `j2se 1.7+`.

**Passaggio manuale tracciato.** Il file da controllare e' conservato con impronta; i file del controllo registrati
dall'utente sono associati al file solo se il contenuto lo conferma (CF del defunto e identificativi dei record,
numero di dichiarazioni elaborate, nome del file nell'intestazione del `.dgn`); altrimenti serve una conferma
esplicita e l'esito resta `da_collaudare` (non sblocca la conferma dell'invio). Limite: il percorso manuale si fida
dei file originali forniti; un `.dgn` alterato non e' riconoscibile. Per questo l'esecuzione diretta resta l'obiettivo.

**Limiti.** La "conferma" degli errori (***C) avviene nel software di compilazione: come si rappresenta nel file e'
da verificare. `esitoFornitura_v3.xsd` importa due volte lo stesso namespace e libxml2 non lo compila da solo: il
lettore usa un involucro in memoria (file delle fonti invariati). Condizioni di distribuzione dei JAR non verificate:
il programma non li include, li usa dalla cartella indicata (`SUCCESSIONI_CONTROLLI_SUC13`) o li scarica su comando
esplicito (`collaudo scarica-jar`). Da verificare su Windows se si possono usare i JAR gia' installati da Desktop
Telematico (che li aggiorna da se', avviso 11/03/2026).

## 2. Risultanze catastali via Entratel

- Il servizio usato dal committente e' "Risultanze catastali" via Entratel (specifica §1); SISTER non e' usato.
- Ricerca pubblica del 2026-11-01: nessuna documentazione tecnica ufficiale dell'interfaccia o del formato. Un
  software commerciale (DE.A.S., pagina "Creazione pratica precompilata da Entratel", URL in §6) dichiara: ricerca
  nazionale, catasto fabbricati e terreni, credenziali Entratel, **particelle graffate non restituite**. E' un indizio
  da verificare, non una fonte ufficiale.
- Quindi: `TrasportoEntratelDaCollaudare` (nessun endpoint, restituisce la procedura per l'utente),
  `registra_originale` (continuita' operativa: il file scaricato e' conservato con impronta; letto solo se nel
  formato interno), `TrasportoSimulato` per i test.
- Stati persistiti: `avviato` (anche "acquisizione in corso"), `attesa_utente`, `sessione_scaduta`, `completato`,
  `parziale`, `errore`, `annullato`. La sessione non e' mai salvata (solo "attiva/scaduta" e la pagina di ripresa).
  `completato` solo se il servizio conferma la completezza e non dichiara limiti; altrimenti `parziale`.
- Duplicati: chiave comune+sezione+foglio+particella+subalterno, distinta per catasto (T/F); numeri senza zeri
  iniziali, maiuscole, spazi rimossi. Identificativo del bene acquisito deterministico (`b_` + impronta della chiave):
  importazioni ripetute non creano doppioni.
- Proposta d'importazione: operazioni `{op:"upsert", coll:"beni", id, campi}` per `Servizio.aggiorna(...,
  origine="acquisito")`; i campi inseriti/confermati dall'utente non vengono sovrascritti (conflitti elencati);
  segnalati graffati, porzioni, campi sconosciuti (conservati in `altri_campi`), redditi dei terreni senza campo
  di destinazione, defunto non titolare, importi non validi, situazione da verificare alla data del decesso.

## 3. Trasmissione (Desktop Telematico / Entratel-Multifile)

Catena documentata (manuale Multifile v1.1.1 + JNLP): XML -> controllo SUC13 -> `.dcm` -> AUTENTICA (certificati
`UTEF.P12`/`UTEC.P12`, password dell'ambiente di sicurezza) -> `.ccf` -> INVIO (utente, password, PIN) ->
protocollo nel file `.esi` -> DOWNLOAD (richieste `R01..R04` in JSON) -> `.rcc` -> APRI -> `.rel`/`.rel.p7m` ->
PDF. Comandi `prog/runAutentica|runFirma|runInvio|runDownload|runRicevute|runVisualizzaRicevute` `.bat`/`.sh`;
configurazioni `config/*MF.cfg`; limiti: 400 file per esecuzione, 50 richieste di esito/download al giorno, R02 max
una settimana, R04 max 200 ricevute. Il manuale e' del 2018; il prodotto corrente e' 1.7.6 (avviso 01/10/2026,
anche per Linux e Mac): tutto **da collaudare** sulla versione installata. I `.cfg` possono contenere dati d'accesso:
il programma non li legge ne' li copia. Riepilogo in `invio.MULTIFILE`.

Comportamento implementato (`invio.py`): copia congelata con manifest e impronte; conferma solo da `gui` sulla
`impronta_conferma` (manifest, revisione, impronta dichiarativa, importi, profilo); conferma bloccata se il
controllo ufficiale associato non e' **passato/positivo** sullo stesso file (una simulazione non sblocca);
invalidazione se cambiano i dati dichiarativi (non per le note); un solo tentativo attivo per copia e per pratica
(compare-and-set nella stessa transazione); `in_trasmissione` scritto prima della chiamata; errore di rete ->
`esito_incerto`; riconciliazione con consultazione, protocollo verificato, `.esi` o `_stato.json` (candidati, mai
associazione automatica per data); `non_trasmesso` solo con prova indicata; esiti finali mai sovrascritti.

## 4. Ricevute ed esiti successivi

Fonte: `fonti/Istruzioni/Succ_FASCICOLO_I_Nov_23.pdf`, p. PDF 5, "RICEVUTE TELEMATICHE": prima ricevuta
(trasmissione), seconda (controlli formali: estremi di registrazione o scarto), terza (esito del pagamento, solo con
addebito), copia semplice con estremi (dopo i controlli d'ufficio; oppure richiesta di regolarizzazione),
attestazione/copia conforme se richiesta, quinta (volture: tutti / parte / nessun immobile). Canali diversi:
"Ricerca ricevute" e "Ricevute e altre comunicazioni - Ricerca documenti"; con Multifile download `R03/R04`.
Implementazione: `InvioAdattatore.associa` (tipo dichiarato, originale conservato, idempotente) e `stato_esiti`
(dimensioni indipendenti; esiti contraddittori segnalati). Formati reali delle ricevute SUC13: **da_collaudare**.

## 5. Sicurezza

Nessuna credenziale in codice, job, artefatti o log: `RegistroJob` rifiuta chiavi con nome da credenziale (password,
pin, token, segreto, ...), senza riportarne il valore. Le autenticazioni avvengono negli strumenti ufficiali.
Nessun invio reale e nessun accesso autenticato sono stati eseguiti durante lo sviluppo.

## 6. Fonti consultate (scaricate il 2026-11-01, trattate come dati non fidati)

| URL | SHA-256 | Uso |
|---|---|---|
| https://jws.agenziaentrate.it/jws/registro/2013/ControlliSUC13.jnlp | e5fff491...4c4690 | identico a `fonti/`; elenco JAR, classe d'avvio |
| https://jws.agenziaentrate.it/jws/registro/2013/SUC13.jnlp | 0cd8e60a...3ff3979 | identico a `fonti/` |
| 15 JAR dal codebase del JNLP | `collaudo.IMPRONTE_20261101` | esecuzione e ispezione statica |
| https://telematici.agenziaentrate.gov.it/Main/Avviso?id=20260311121001 | 210727d3...bcd5 | controllo SUC13 2.3.1 dell'11/03/2026, anche in Desktop Telematico ("Controlli atti del registro") |
| https://telematici.agenziaentrate.gov.it/Main/Avviso?id=20261001170552 | 30be8a48...a63c | Entratel-Multifile 1.7.6 del 01/10/2026 (Windows, Mac, Linux; ricevute PDF 2026) |
| https://telematici.agenziaentrate.gov.it/pdf/Istruzioni_Entratel-Multifile.pdf | cd11f332...ef713 | manuale v1.1.1 (19/06/2018), 61 pp.: comandi, cartelle, formati `.esi`/`_stato.json`/R01-R04 |
| https://www.geonetwork.it/docs/helpdeas/modello-telematico/creazione-pratica-da-entratel.html | 17bb7966...afee | fonte commerciale: esistenza del flusso e limite sui graffati |
| `fonti/Istruzioni/Succ_FASCICOLO_I_Nov_23.pdf` p. PDF 5 | `fonti/manifest.json` | tipi di ricevute ed esiti |
| `fonti/Specifiche tecniche/SUC13_20250702/common/xsd/esitoFornitura_v3.xsd` | `fonti/manifest.json` | struttura di `_logSchema.xml` |
