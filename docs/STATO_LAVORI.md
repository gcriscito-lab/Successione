# Stato dei lavori (aggiornato 2026-11-01)

Nota per riprendere. Le decisioni sotto sono già prese; non vanno riaperte senza motivo.

## Decisioni di interfaccia
- Struttura **A** (come il compilatore dell'Agenzia): frontespizio, quadri EA…ER, riepiloghi, pannello controlli.
- Stile scelto: **combinazione di 1 (Vetro) e 2 (Grafite)**, con i **colori di 1**: veste chiara e smerigliata, blu di sistema,
  sigle dei quadri colorate per stato; struttura di Grafite: tabella fitta al centro, ispettore a destra con
  *Dati / Controlli / Cronologia*, barra di stato in basso (revisione, salvataggio, rilievi, controllo ufficiale).
- Proposte visionabili: https://claude.ai/artifact/A6CKL8HtA3sgG3smRMiamc (stili), https://claude.ai/artifact/PmvopkizoXjojMyoNywadt (strutture).

## Da fare subito: applicare lo stile all'interfaccia vera
- `docs/design/vetro-grafite/index.html` e `app.css` sono già scritti (nuovo layout a tre colonne, token chiaro/scuro).
  **Non sono attivi**: l'interfaccia in uso (`src/successioni/static/`) è ancora la versione precedente, che funziona e passa i test.
- Manca il nuovo `app.js`: tabella con selezione di riga, ispettore (Dati: form della riga selezionata; Controlli: elenco cliccabile;
  Cronologia: revisioni con ripristino), barra di stato, frontespizio a schede raggruppate, procedura guidata, salvataggio unico
  di tutte le modifiche in una sola operazione. Riutilizzare le funzioni del `app.js` attuale (valori, salvataggio, procedura guidata).
- Poi: prova con Playwright (`.claude/skills/webapp-testing`, vedi `CLAUDE.md`), sostituire i file in `static/` e committare.
- Il font di sistema Apple non c'è su Windows: lo stack ripiega su Segoe UI.

## Subagenti (avviati, risultati non ancora integrati)
Tre agenti lavorano su file distinti (contratti in `docs/CONTRATTI_MODULI.md`): telematico/XSD, documenti/PDF-A, collegamenti.
Il commit contiene i loro file in corso (etichettati WIP). Alla consegna: verificare direttamente, integrare, poi revisore indipendente.

## Limiti dichiarati
- Validazione PDF/A indipendente (veraPDF): **da collaudare** (l'esecuzione dell'installer scaricato è stata bloccata dai permessi).
- Controllo ufficiale SUC13, catasto Entratel, invio e ricevute, client Claude su Windows, installazione Windows: **da collaudare**.
- Calcolo imposte, XML SUC13 completo, stampa: non ancora disponibili. I quadri non supportati bloccano la finalizzazione.
- Skill di progetto in `.claude/skills/` (vedi `docs/SKILLS_SETUP.md`): risultano ora caricate.

## Verifiche eseguite
`python -m pytest -q` → 26 test verdi (archivio, MCP stdio reale, GUI, quadri, PDF/A con Ghostscript).
