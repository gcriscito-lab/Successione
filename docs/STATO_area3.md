# Stato area 3 — collegamenti ufficiali (controllo SUC13, catasto Entratel, invio e ricevute)

Aggiornato 2026-11-01 dall'agente area 3. File di proprieta': `src/successioni/collegamenti/**`,
`tests/test_collegamenti*.py`, `docs/COLLEGAMENTI.md`, `docs/COLLAUDO_RIPRENDIBILE.md`,
`docs/PROPOSTE_collegamenti.md`, questo file. Dettagli e fonti: `docs/COLLEGAMENTI.md`.

## Fatto
- `base.py` (bozza del predecessore corretta): `annota` atomico (prima poteva annullare una transizione
  concorrente), `transizione(..., vincolo=)` valutato nella stessa transazione, file temporaneo univoco nel deposito,
  rifiuto delle chiavi con nome da credenziale, `risultato_da_job`, `DepositoArtefatti.esporta`.
- `controllo.py`: `ControlloJar` (esecuzione reale del JAR, ambiente/impronte/stdout/stderr registrati, cartella di
  lavoro rimossa), `ControlloManuale` (passaggio manuale tracciato, verifica dell'associazione), lettori
  `.dgn`/`_logSchema.xml`/`.wri`, `valuta`, `diagnostica_ambiente`. Modalita' batch PROVATA nel container
  (MSUC13 + VisualXml, headless, OpenJDK 21): 2 negativi reali registrati in `fixture/controllo_reale_20261101/`;
  controllato anche l'export "bozza tecnica" dell'area 1 (negativo, rilievi in PROPOSTE §6).
- `catasto.py`: macchina a stati persistente, trasporto reale `da_collaudare` (nessun endpoint), simulato,
  normalizzazione/duplicati, proposta d'importazione per `Servizio.aggiorna(origine="acquisito")`.
- `invio.py`: copia congelata, conferma solo da GUI, invalidazione, tentativi con chiave, esito incerto e
  riconciliazione (consultazione, protocollo, `.esi`, `_stato.json`), ricevute con tipi dal Fascicolo I p. 5,
  ricognizione Multifile (`MULTIFILE`, lettori `.esi`/`_stato.json`, richieste R01-R04). Nessuna trasmissione.
- `collaudo.py`: comandi JSON riprendibili per il PC Windows (ambiente, scarica-jar, controllo, registra-diagnostico,
  catasto-avvia/registra, riconcilia, ricevuta, stato).
- Documenti: COLLEGAMENTI.md, COLLAUDO_RIPRENDIBILE.md, PROPOSTE_collegamenti.md.

## Da fare / aperto
- A10 positivo: serve un XML completo (EF/EG/EH dall'area 1) o un file di pratica effettiva; prova su Windows.
- `.dcm` mai osservato (solo con fornitura trasmissibile).
- A13/A14 reali: formato e accesso del servizio "Risultanze catastali" da rilevare con il committente; convertitore.
- A18/A19 reali: solo con pratica effettiva autorizzata; integrazione GUI della conferma (coordinatore).
- Integrazione MCP/GUI/schema: vedi `docs/PROPOSTE_collegamenti.md`.

## Comandi di verifica
```
python scripts/verifica_materiali.py
python3 -m pytest -q tests/test_collegamenti_*.py          # 47 test, 1 saltato senza JAR
SUCCESSIONI_CONTROLLI_SUC13=<cartella 15 JAR> python3 -m pytest -q tests/test_collegamenti_*.py   # anche il reale
python3 -m pytest -q                                       # intera suite: 184 passati, 2 saltati (2026-11-01)
python -m successioni.collegamenti.collaudo ambiente
```
JAR usati nelle prove: scratchpad della sessione `a3/jar_controlli` (scaricabili con `collaudo scarica-jar`).
