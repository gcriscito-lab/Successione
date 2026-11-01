# Stato dei lavori (aggiornato 2026-11-01)

Nota per riprendere. Le decisioni sotto sono già prese; non vanno riaperte senza motivo.

## Decisioni di interfaccia
- Struttura **A** (come il compilatore dell'Agenzia): frontespizio, quadri EA…ER, riepiloghi, pannello controlli.
- Stile scelto: **combinazione di 1 (Vetro) e 2 (Grafite)**, con i **colori di 1**: veste chiara e smerigliata, blu di sistema,
  sigle dei quadri colorate per stato; struttura di Grafite: tabella fitta al centro, ispettore a destra con
  *Dati / Controlli / Cronologia*, barra di stato in basso (revisione, salvataggio, rilievi, controllo ufficiale).
- Proposte visionabili: https://claude.ai/artifact/A6CKL8HtA3sgG3smRMiamc (stili), https://claude.ai/artifact/PmvopkizoXjojMyoNywadt (strutture).

## Interfaccia (fatto il 2026-11-01)
Applicato lo stile Vetro+Grafite (colori di Vetro) all'interfaccia vera: tabella fitta con selezione di riga, ispettore a destra
(Dati / Controlli / Cronologia), barra di stato, frontespizio a schede, procedura guidata. Provata in browser reale con
`tests/e2e/gui_flusso.js` (13 verifiche positive, nessun errore JS). Il vecchio `app.js` è in `docs/design/vetro-grafite/app_precedente.js`.
Avvertenza: `with_server.py` può lasciare il server attivo; chiudere per PID prima di rilanciare le prove.

## Consegne dei subagenti
- **Area 2 (documenti, PDF/A): consegnata e verificata il 2026-11-01.** Suite intera 179 passati, 2 saltati; vincolo sui nomi allegati (solo maiuscole, max 100)
  confermato nell'XSD (typesDati_v2.xsd riga 18, typesReg_v2.xsd riga 422). Integrate: strumento MCP e pulsante GUI "Suddividi", pillow dichiarato.
  Da integrare quando c'è l'XML: `verifica_fornitura` prima dell'invio, anteprima visiva, nomi EG con `dati_file_attachment` (area 1).
  Resta **da collaudare**: veraPDF (procedura in `docs/PDFA.md` par. 9), fedeltà visiva su documenti reali.
- Aree 1 (regole/XML) e 3 (collegamenti): ancora in corso.

## Subagenti (rilanciati su Opus)
Tre agenti lavorano su file distinti (contratti in `docs/CONTRATTI_MODULI.md`): regole/XSD/XML, documenti/PDF-A, collegamenti.
Ognuno tiene traccia in `docs/regole/STATO_area1.md`, `docs/STATO_area2.md`, `docs/STATO_area3.md`. Alla consegna: verificare direttamente,
integrare, poi revisore indipendente. I loro file nel repository sono bozze finché non consegnano.

## Limiti dichiarati
- Validazione PDF/A indipendente (veraPDF): **da collaudare** (l'esecuzione dell'installer scaricato è stata bloccata dai permessi).
- Controllo ufficiale SUC13, catasto Entratel, invio e ricevute, client Claude su Windows, installazione Windows: **da collaudare**.
- Calcolo imposte, XML SUC13 completo, stampa: non ancora disponibili. I quadri non supportati bloccano la finalizzazione.
- Skill di progetto in `.claude/skills/` (vedi `docs/SKILLS_SETUP.md`): risultano ora caricate.

## Verifiche eseguite
`python -m pytest -q` → 26 test verdi (archivio, MCP stdio reale, GUI, quadri, PDF/A con Ghostscript).
