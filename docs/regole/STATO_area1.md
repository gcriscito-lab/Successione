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
