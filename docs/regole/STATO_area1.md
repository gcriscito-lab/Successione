# Stato area 1 (telematico: regole, XSD, esportazione XML, calcolo)

Aggiornato man mano dall'agente area 1. Ultimo aggiornamento: 2026-11-01 (consegna del primo perimetro: codice, test e documentazione).

## Fatto (verificato con i comandi sotto)
- `telematico/xsd.py`: `valida_xsd(xml) -> list[Errore]` (lxml, XSD di fonti/), XPath con prefissi, messaggi in
  italiano anche per tipi union (valori ammessi letti dall'XSD), lunghezze; `enumerazioni(tipo)`.
- `telematico/formati.py`: tipi semplici (DatoAN/AN2/NP/NU/VP/CF/DT/TL/EM/CB), nessun arrotondamento silenzioso.
- `telematico/modello_xsd.py` (bozza predecessore, verificata dai test): serializzatore guidato dall'XSD (ordine e
  namespace dallo schema).
- `telematico/supplemento.py`: dati non ancora nel modello comune letti da `opzioni.telematico` (chiavi elencate).
- `telematico/esporta.py`: `esporta_xml(dati, ContestoExport) -> EsitoExport` sul perimetro dichiarato
  (frontespizio, EA, EB, EC, ER, ED, EE). EF/EG/EH obbligatori per le annotazioni ma fuori perimetro ->
  `quadri_mancanti`, `completo=False`, `xml=None` con `scopo='completo'`; XML valido allo schema con
  `scopo='bozza_tecnica'`. Mappa id interno -> quadro/modulo/rigo/XPath. Determinismo e stabilita' al riordino.
- `telematico/calcolo.py`: `calcola(dati)` / `calcola_da_xml(xml)` secondo la guida (QE...ISN), Fraction esatta,
  due candidati di arrotondamento (esatto / replica del componente ufficiale ispezionato), stati
  completato | divergenza_aperta | non_supportato | dati_incompleti; esito_collaudo sempre da_collaudare.
- `telematico/mappa.py` -> `docs/regole/mappa_xsd_albero.md` (generato dagli XSD; test di aggiornamento).
- Ispezione statica (javap, NON esecuzione) di `controlliXMLREG2013.jar`: arrotondamenti del calcolo ufficiale
  documentati in `docs/regole/dubbio_arrotondamento.md`.
- Test: `tests/test_telematico_xsd.py`, `tests/test_telematico_esporta.py`, `tests/test_telematico_calcolo.py`,
  casi sintetici in `tests/telematico_casi.py`.
- Documenti: `docs/regole/mappa_xsd.md`, `docs/regole/dubbio_arrotondamento.md`, `docs/MATRICE_COPERTURA.md`,
  `docs/PROPOSTE_telematico.md`.
- Verifica indipendente dello schema: `xmllint --schema fornituraSUC13_v1.xsd` sul file del caso sintetico -> validates.

## In corso
- Nulla in sospeso: il lavoro riparte dai "Da fare".

## Da fare (prossimi passi riprendibili)
- Quadri EF (incluso V-bis con l'imposta del calcolo), EG (allegati Base64: valori da `documenti/base64.py` area 2),
  EH: senza questi nessuna pratica reale e' `completo`.
- Devoluzione per testamento, legatari, rinunce, rappresentazione, diritti diversi da quello del defunto
  (valutazione usufrutto/nuda proprieta'), agevolazioni/riduzioni, beni esteri, tavolare (EL/EM), EN-EQ, EI.
- Prova del controllo ufficiale sul file `bozza_tecnica` (area 3, `collegamenti/controllo.py`): da_collaudare.
- Risolvere la divergenza di arrotondamento con un'esecuzione del software ufficiale (ALIS o compilatore 2.3.x).

## Comandi di verifica
```
python scripts/verifica_materiali.py
python3 -m pytest -q tests/test_telematico_xsd.py tests/test_telematico_esporta.py tests/test_telematico_calcolo.py
python3 -m pytest -q
PYTHONPATH=src python3 -m successioni.telematico.mappa > docs/regole/mappa_xsd_albero.md   # rigenera l'albero
```
Ultimo esito: test area 1 -> 31 passed; `python3 -m pytest -q` -> 186 passed, 2 skipped (skip di altre aree: JAR del controllo e veraPDF non configurati).

## Secondo giro (ripresa) - 2026-11-01

Obiettivo: caso sintetico A10 che il controllo ufficiale SUC13 2.3.1 (eseguito in locale, batch, senza GUI) non scarta
per errori bloccanti (***), piu' casi negativi con errore predisposto. Controllo LOCALE su dati sintetici: non e'
trasmissione ne' prova con i servizi dell'Agenzia.

### Fatto
- CF: `identificativi.py` verificato ESEGUENDO checkCF_PIVA.jar su 30 soggetti sintetici + 3 negativi
  (`tests/fixture_telematico/cf_lotto.tsv`, esito originale `cf_lotto_esito_componente.txt`): primi 15 caratteri
  uguali a `CodiceFiscale.getCodiceFiscale` (che accoda sempre 'A': il 16o carattere NON e' calcolato da quella
  classe) e `U1CheckDigit.controllaCheckDigit`=true. Aggiunta la tabella accenti di `noAccentate`.
  `VerificaComponenti.java` ha la modalita' `lotto`.
- `tests/telematico_casi.py`: CF sintetici validi (RSSMRA40A01H501K, RSSNNA70A41H501J, RSSLCU72B02H501O).
- Controllo ufficiale sulla bozza con i nuovi CF: spariti i (***) sui codici fiscali e sul numero di soggetti in
  devoluzione; restano EF/EG/EH obbligatori e quote ER 1/3-2/3 incoerenti con la devoluzione per legge (1/2).

- EF/EG/EH: `telematico/quadri_efgh.py` (nuovo), integrato in `esporta.py`; quote di legge (Allegato 5, sottoinsieme)
  in `telematico/devoluzione_legge.py`; ripartizione ED da `opzioni.telematico.passivita[id].ripartizione`;
  ImportoDaVersare e Versamento nel frontespizio.
- **Controllo ufficiale locale su `caso_a10` (2026-11-01): "La dichiarazione puo' essere trasmessa", 0 scartate,
  1 con segnalazione (*) attestazione non richiesta; prodotto il `.dcm`.** Serve `jaxb-api-2.3.1.jar` nel classpath
  con Java 21 (GestoreAllegatiXML usa javax.xml.bind.DatatypeConverter, assente da Java 11): vedi limiti.

- Registrazioni del controllo (Java 8 estratto in scratch; verifica con Java 21 + jaxb-api: .dgn identici) in
  `tests/fixture_telematico/controllo_20261101/` (+ manifest.json): a10_positivo (solo (*) 3345), neg_cf_defunto
  ((***) 1013 XXB02), neg_importo_da_versare ((***) 3376 XXB94). Suite completa: 192 passed, 3 skipped.

- Test: `tests/test_telematico_identificativi.py` (CF/IBAN contro le registrazioni del componente; prova reale con
  SUCCESSIONI_CONTROLLI_SUC13), `tests/test_telematico_controllo.py` (EF/EG/EH, file A10 identico a quello
  controllato, diagnostici registrati letti con `collegamenti.controllo`, prova reale facoltativa positivo + 2 negativi).
- Prova aggiuntiva (non registrata in fixture): caso A10 con conto 2.400.000 (imposta di successione 22.396 da
  `calcolo`, tempistica 1 e 2) -> controllo ufficiale: solo (*) 3345, nessuno scarto (EF18bis accettato dal componente).

### Esito reale dell'ultimo controllo ufficiale sul caso base (2026-11-01, 2.3.1, locale, Java 8 e Java 21+jaxb-api)
```
(*)
Dati del Frontespizio:
 - Campo "attestazione" del Frontespizio: Non e' stata richiesta l'attestazione
di avvenuta presentazione della dichiarazione, utile ad es. per lo sblocco di un
conto corrente (vedi istruzioni per la compilazione)

La dichiarazione puo' essere trasmessa.   (elaborate 1, scartate 0, con segnalazione di anomalia 1; .dcm prodotto)
```
Causa della (*): casella attestazione/copia conforme non richiesta (scelta del dichiarante, non un errore); richiederla
implica EF16 col. 1 e EF18 (non coperti).

### Non finito (stato al congelamento)
- EF: agevolazioni (G, M, P/X/Y/Z, trust), soli terreni (valori fiscali), proporzionale < fissa (fonti non concordi),
  piu' comuni (elenco conservatorie), attestazione/copia conforme, crediti, sostitutive, sanzioni, rateazione ->
  `quadri_mancanti` (EF) o `non_supportato` con motivo.
- EG: testamento, inventario, imposta estera, agevolazioni/riduzioni -> `non_supportato`. Conformita' PDF/A non
  verificata dall'export (avviso).
- EH: sezioni II-IV, separazione (stato civile 5), unione civile (7), interdetti/disabili, rinunce -> `non_supportato`.
- Quote di legge: coperti solo figli / coniuge / coniuge+figli; altrimenti avviso `QUOTE_DI_LEGGE_NON_VERIFICATE`.
- Servizio/GUI/MCP: passare `ContestoExport.allegati` (allegato_id -> file) dall'archivio (proposta P8).
- Controllo con Java >= 11 dall'adattatore area 3: serve jaxb-api nel classpath o Java 8 (proposta P9).
- Collaudo su Desktop Telematico (Windows) e con i servizi dell'Agenzia: da fare.

### Comandi di verifica (secondo giro)
```
python3 -m pytest -q                                   # 238 passed, 8 skipped (2026-11-01, chiusura)
SUCCESSIONI_CONTROLLI_SUC13=<jar> SUCCESSIONI_JAVA=<java 8>/bin/java python3 -m pytest -q tests/test_telematico_controllo.py tests/test_telematico_identificativi.py   # 19 passed
SUCCESSIONI_CONTROLLI_SUC13=<jar> SUCCESSIONI_CONTROLLI_CLASSPATH_EXTRA=<jaxb-api-2.3.1.jar> python3 -m pytest -q tests/test_telematico_controllo.py -k reale   # 3 passed
```
