# Stato area 2 (documenti, allegati, PDF/A)

Aggiornato: 2026-11-01 (agente area 2). Documento tecnico: `docs/PDFA.md`. Proposte comuni: `docs/PROPOSTE_documenti.md`.

## Fatto
- Fonti rilette e citate: Specifiche_SUC13_20250702.pdf p.3, p.7 par. 2.3, p.263-281, p.794-796, p.902; Fascicolo I
  p.49; XSD typesReg_v2 / typesDati_v2 / fornituraSUC13_v1 (letti dai test). Sito Agenzia: URL provati -> 404.
- `documenti/pdfa_strutturale.py`: corretti 2 difetti (BooleanObject `is True`; messaggi persi a parità di codice),
  intestazione binaria e %%EOF secondo veraPDF; nuove regole (TR/TR2, intento, BPC, C/IC, 6.1.12 sugli oggetti,
  ToUnicode 1a). Mai "conforme".
- `documenti/dimensioni.py`: `riduci_o_suddividi` (Ghostscript, poi qpdf/pypdf, parti rivalidate, rapporto JSON),
  `verifica_fornitura` / `misura_fornitura` (unità e punto di misura come parametri dichiarati).
- `documenti/base64.py`: `incorpora_base64`, `decodifica_base64`, nomi EG (cm:DatoAN_Type), `dati_file_attachment`.
- `documenti/tiff.py`: verifica requisiti p.7 e conversione `tiffg4`. `documenti/anteprima.py`: confronto visivo.
- `documenti/corpus_sintetico.py`: corpus (firma simulata) + `collaudo_a11` (evidenza JSON riprendibile).
- `allegati.py`: originale già conforme (solo veraPDF) conservato; pagine diverse = derivato scartato; avvisi su
  testo/visivo/dimensione; `suddividi_allegato`. `pdfa.py`: analisi TIFF con verifica.
- Test: `tests/test_documenti_{corpus,dimensioni,base64,tiff,strutturale}.py`.

## Esito reale delle prove (2026-11-01, Linux, GS 10.02.1, qpdf 11.9.0, veraPDF assente)
- `python3 -m pytest -q` -> 179 passati, 2 saltati (intera suite, ultima esecuzione).
- `python3 -m pytest -q tests/test_pdfa.py tests/test_documenti_*.py` -> 87 passati, 1 saltato (collaudo veraPDF reale).

## Da collaudare (non bloccano il resto)
- A11 con veraPDF sul PC del professionista: procedura `docs/PDFA.md` par. 9.
- Fedeltà visiva su insieme rappresentativo reale; accettazione CIVIS/Agenzia; TIFF multipagina.

## Da fare / possibili estensioni
- Integrazioni GUI/MCP/servizio proposte in `docs/PROPOSTE_documenti.md` (coordinatore).
- Ripetere il corpus con Ghostscript >= 10.05 (limite ToUnicode).

## Comandi di verifica
- `python3 -m pytest -q`
- `PYTHONPATH=src python3 -m successioni.documenti.corpus_sintetico /tmp/corpus --collaudo`
