# Stato area 3 — collegamenti ufficiali (controllo SUC13, catasto Entratel, invio e ricevute)

Aggiornato man mano dall'agente area 3. File di proprietà: `src/successioni/collegamenti/**`, `tests/test_collegamenti*.py`,
`docs/COLLEGAMENTI.md`, `docs/COLLAUDO_RIPRENDIBILE.md`, `docs/PROPOSTE_collegamenti.md`, questo file.

## Fatto
- Lettura di CLAUDE.md, CONTRATTI_MODULI, specifica (§2, §9, §10, §12), COLLAUDO_CLOUD_WINDOWS, archivio.py, errori.py.
- Linea di base: `python scripts/verifica_materiali.py` OK (23 fonti); `python3 -m pytest -q` → 26 passati.

## In corso
- Verifica e test di `collegamenti/base.py` (bozza del predecessore).

## Da fare
- controllo.py, catasto.py, invio.py, test, COLLEGAMENTI.md, COLLAUDO_RIPRENDIBILE.md, PROPOSTE_collegamenti.md.

## Comandi di verifica
```
python scripts/verifica_materiali.py
python3 -m pytest -q tests/test_collegamenti*.py
python3 -m pytest -q
```
