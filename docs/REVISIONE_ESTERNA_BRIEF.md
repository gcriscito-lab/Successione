# Revisione esterna del codice: istruzioni per il revisore

Documento da consegnare a un revisore esterno (ad esempio Codex). Il revisore non ha partecipato allo sviluppo e deve cercare errori, non confermare il lavoro.

## Regole
- Lavora in sola lettura sul codice. L'unico file da creare è il rapporto `docs/REVISIONE_ESTERNA_<revisore>.md`.
- Non leggere `docs/REVISIONE_INDIPENDENTE.md` finché il tuo rapporto non è concluso: serve a confrontare due revisioni separate.
- Non usare dati reali. Il repository contiene solo dati sintetici e documenti pubblici dell'Agenzia delle Entrate. Nessun invio reale, nessuna credenziale.
- Le regole fiscali vengono dalle fonti in `fonti/` e dal sito ufficiale dell'Agenzia, non dalla memoria. Cita sempre documento e pagina, oppure elemento XSD, oppure URL.

## Come partire
```bash
git clone <repository> && cd Successione
git checkout claude/successioni-dichiarazioni-app-fhcwbe
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"
python3 -m pytest -q
```
Indica nel rapporto il commit esaminato (`git rev-parse HEAD`) e l'esito reale dei test. Alcuni test sono saltati se mancano Ghostscript, qpdf, Java o veraPDF: segnalalo, non considerarlo un errore.

## Da leggere prima
`CLAUDE.md`, `docs/02_SPECIFICA_E_COLLAUDO.md` (§6 MCP, §7 PDF/A, §8 calcoli e XML, §9 canali, §10 stati, §12 accettazione A01-A20), `docs/CONTRATTI_MODULI.md`, `docs/MATRICE_COPERTURA.md`, `docs/COLLEGAMENTI.md`, `docs/PDFA.md`.

## Ambito
Tutto in `src/successioni/` e `tests/`: archivio, servizio, schema, quadri, elaborati, interfaccia (`web.py`, `static/app.js`), MCP (`mcp_server.py`), PDF/A e allegati, esportazione XML e calcolo (`telematico/`), adattatori (`collegamenti/`).

## Cosa cercare
1. **Errori fiscali e normativi**: confronta calcolo, esportazione e codici con la guida di calcolo, le istruzioni e gli XSD. Segnala dove il codice afferma più di quanto le fonti sostengono.
2. **Perdite di dati e incoerenze**: transazioni, revisioni, idempotenza delle richieste, conflitti, backup e ripristino, allegati (l'originale non deve mai cambiare), identificativi stabili, invalidazione selettiva degli esiti.
3. **Sicurezza**: interfaccia locale (token, controllo di Host e Origin, upload), MCP (nessuna shell, SQL o lettura arbitraria; cartella d'ingresso; path traversal), segreti nei log, esecuzione di Java e Ghostscript con input non fidati, XML e PDF ostili (entità esterne, zip bomb).
4. **Affermazioni non supportate**: dove codice o documenti dicono «passato», «conforme» o «collaudato» senza prova. Usa le parole `passato`, `fallito`, `da_collaudare`, `simulazione` di `docs/COLLAUDO_CLOUD_WINDOWS.md`.
5. **Test deboli o mancanti**: test che passano per il motivo sbagliato, rami critici scoperti, stato reale di ciascuna prova A01-A20.
6. **Interfaccia**: perdita di modifiche non salvate, inserimento di HTML con dati dell'utente, gestione degli errori 409 e 422, uso da tastiera.

## Formato del rapporto
Struttura fissa, in italiano:
1. **Esito**: OK oppure non OK per l'uso previsto, con una riga di motivazione.
2. **Quadrature eseguite**: comandi lanciati e risultati reali.
3. **Rilievi**, ordinati per gravità (bloccante, alta, media, bassa). Per ciascuno: file e riga, evidenza o caso riproducibile, impatto concreto, correzione suggerita. Separa i fatti verificati dalle ipotesi. Distingui differenze di pochi centesimi da anomalie sostanziali.
4. **Punti aperti**.
5. **Cosa non ho potuto verificare**.

Se un'area è solida, scrivilo: non gonfiare i rilievi.

## Limiti noti (non sono rilievi nuovi)
- Validazione PDF/A con veraPDF, controllo con Desktop Telematico su Windows, catasto via Entratel, invio e ricevute, client MCP su Windows: da collaudare.
- Quadri non supportati: vedi `docs/MATRICE_COPERTURA.md`. La loro selezione blocca la finalizzazione, per progetto.
- Il dubbio sull'arrotondamento 82,0875 contro 82,08 è dichiarato aperto in `docs/regole/dubbio_arrotondamento.md`.
