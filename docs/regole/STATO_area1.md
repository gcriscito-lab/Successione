# Stato area 1 (telematico: regole, XSD, esportazione XML, calcolo)

Aggiornato man mano dall'agente area 1. Ultimo aggiornamento: 2026-11-01 (avvio).

## Fatto
- Letti CLAUDE.md, CONTRATTI_MODULI.md, specifica §8/§10/§12, schema.py/servizio.py/quadri.py.
- `python scripts/verifica_materiali.py` -> OK (23 fonti). Suite iniziale: 26 passed.

## In corso
- Verifica delle bozze del predecessore (fonti.py, formati.py, modello_xsd.py, supplemento.py, xsd.py).

## Da fare
- mappa_xsd.md, esporta.py, calcolo.py, dubbio_arrotondamento.md, MATRICE_COPERTURA.md, test.

## Comandi di verifica
```
python scripts/verifica_materiali.py
python3 -m pytest -q tests/test_telematico*.py
python3 -m pytest -q
```
