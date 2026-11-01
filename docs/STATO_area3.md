# Stato area 3 — collegamenti ufficiali (controllo SUC13, catasto Entratel, invio e ricevute)

Aggiornato man mano dall'agente area 3. File di proprietà: `src/successioni/collegamenti/**`, `tests/test_collegamenti*.py`,
`docs/COLLEGAMENTI.md`, `docs/COLLAUDO_RIPRENDIBILE.md`, `docs/PROPOSTE_collegamenti.md`, questo file.

## Fatto
- Lettura di CLAUDE.md, CONTRATTI_MODULI, specifica (§2, §9, §10, §12), COLLAUDO_CLOUD_WINDOWS, archivio.py, errori.py.
- Linea di base: `python scripts/verifica_materiali.py` OK (23 fonti); `python3 -m pytest -q` → 26 passati.

- Esecuzione REALE del controllo ufficiale SUC13 2.3.1 in modalita' batch, senza GUI, nel container:
  `java -Djava.awt.headless=true -cp <15 jar di ControlliSUC13.jnlp> it.finanze.entrate.sco.main.MSUC13 in/X.xml out/X.xml`
  → `out/X.dgn`, `out/X_logSchema.xml` (EsitoFornitura, esitoFornitura_v3.xsd); `VisualXml [dgn, "1"]` → `.wri`.
  JAR scaricati di nuovo dal codebase del JNLP (hash identici a quelli del predecessore, firmati SOGEI, jarsigner "verified").
  Cartella: scratchpad `a3/jar_controlli`, `a3/run_manuale1`.
- Formato `.dgn` dedotto da `controlliXMLREG2013.jar` classe `generale2013.Visual` (javap): record 106 car.,
  gravita' [17:19] (4=(*), 8=(**), 14=(***C), 15-23=(***), >=24=(****)), codice [19:23], campo [23:39], valori [39:55]...;
  record 9: elaborate [1:7], senza segnalazioni [7:13], anomalia [13:19], confermati [19:25], non rispondenza [31:37], bloccanti [37:43].
- Manuale Entratel-Multifile (v1.1.1) e avvisi scaricati in scratchpad `a3/dl_docs` (INDICE.txt con URL, hash, data).
- Fascicolo I istruzioni p. 5 "RICEVUTE TELEMATICHE": cinque ricevute + attestazione (fonte per ricevute ed esiti).

- `collegamenti/base.py` riscritto: `annota` atomico (prima poteva annullare una transizione concorrente),
  file temporaneo univoco nel deposito, rifiuto di chiavi con nome da credenziale, `risultato_da_job`, `esporta`.
- `collegamenti/controllo.py`: `ControlloJar` (esecuzione reale, artefatti con impronta, ambiente registrato),
  `ControlloManuale` (passaggio manuale tracciato), lettori `.dgn`/`_logSchema.xml`/`.wri`, `valuta`.
  Provato col componente reale tramite l'adattatore: 2 casi negativi (frontespizio incompleto; schema non valido).
  Registrazioni in `collegamenti/fixture/controllo_reale_20261101/` (manifest con hash di input, JAR, Java).
  `esitoFornitura_v3.xsd` non compila in libxml2 (doppio import dello stesso namespace): involucro in memoria.

- Test: `tests/test_collegamenti_base.py` (8), `tests/test_collegamenti_controllo.py` (14, di cui 1 reale
  che si esegue solo con `SUCCESSIONI_CONTROLLI_SUC13=<cartella JAR>`): verdi; il reale verde con i JAR.
- `catasto.py` e `invio.py` scritti (vedi docstring); fixture `fixture/catasto_simulazione_v1.json` (simulazione).

- Test catasto (8) e invio (13) verdi; intera suite: 178 passati, 2 saltati (uno e' il reale del controllo).

## In corso
- `collegamenti/collaudo.py` (comandi riprendibili per il PC Windows), documenti COLLEGAMENTI /
  COLLAUDO_RIPRENDIBILE / PROPOSTE_collegamenti.

## Da fare
- controllo.py, catasto.py, invio.py, test, COLLEGAMENTI.md, COLLAUDO_RIPRENDIBILE.md, PROPOSTE_collegamenti.md.

## Comandi di verifica
```
python scripts/verifica_materiali.py
python3 -m pytest -q tests/test_collegamenti*.py
python3 -m pytest -q
```
