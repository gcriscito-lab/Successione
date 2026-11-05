# Beta 1: da revisionare

Etichetta Git: `beta-1`, sul branch `claude/successioni-dichiarazioni-app-fhcwbe`. Congelata il 2026-11-01.
Stato: **beta tecnica per la revisione. Non è utilizzabile su una pratica reale e non trasmette nulla.**

Nota successiva al congelamento: il rapporto sul commit `2e2b503` e' in
`docs/REVISIONE_ESTERNA_CODEX.md`; le correzioni CE01-CE10 e le nuove prove Windows sono
in `docs/CORREZIONI_CODEX.md`. I risultati storici sotto non sono un collaudo della versione corretta.
Il successivo collaudo locale Windows con veraPDF e SUC13 e' in `docs/COLLAUDO_WINDOWS_CODEX_20261102.md`.

## In una riga
Archivio, interfaccia locale, MCP, PDF/A e file XML funzionano e sono provati nel cloud Linux. Un caso sintetico ha superato il controllo ufficiale SUC13 in locale, secondo la registrazione dell'agente (non ancora riprodotta da chi coordina). Mancano i collaudi su Windows, con veraPDF, con Entratel e con i servizi dell'Agenzia.

## Prove eseguite (comando e risultato reale)
| Prova | Comando | Esito |
|---|---|---|
| Suite intera | `python3 -m pytest -q` | 238 passati, 8 saltati, 0 falliti |
| Motivi dei saltati | `python3 -m pytest -q -rs` | tutti per componenti esterni non configurati: controllo ufficiale (`SUCCESSIONI_CONTROLLI_SUC13`), veraPDF, pacchetto Windows costruito |
| Interfaccia nel browser reale | `tests/e2e/gui_flusso.js` (metodo `webapp-testing`) | 15 verifiche positive, nessun errore JavaScript (eseguita prima dell'ultima serie di correzioni) |
| Server MCP | test su processo reale via stdio | stessa pratica da MCP e interfaccia, conflitto di revisione leggibile, nessun duplicato |
| XML del caso base | `xmllint --schema fornituraSUC13_v1.xsd` | valido (validatore indipendente da quello del programma) |
| Controllo ufficiale, riproduzione di chi coordina | componenti ufficiali eseguiti in locale, senza interfaccia | **riprodotto** sui file registrati dall'agente 3 (esiti identici byte per byte tranne i nomi dei file temporanei). Non riprodotto sul caso positivo dell'agente 1: l'esecuzione con un componente Java aggiuntivo è stata bloccata dai permessi |

## Parole d'esito (docs/COLLAUDO_CLOUD_WINDOWS.md)
- **controllo locale**: componenti ufficiali eseguiti qui su dati sintetici. Non è la verifica con i servizi dell'Agenzia né con Desktop Telematico.
- **simulazione**: catasto Entratel, invio, ricevute, riconciliazione. Solo logica e dati inventati.
- **da collaudare**: tutto ciò che richiede il PC Windows, le credenziali o i servizi reali.

## Cosa funziona
- Pratiche con revisioni, conflitti leggibili, idempotenza delle richieste, backup e ripristino (anche file elaborati).
- Interfaccia a quadri (stile Vetro + Grafite): procedura guidata, tabella, ispettore, cronologia, scheda File.
- MCP: 18 strumenti con prefisso `successioni_`, nessuna shell né SQL, lettura file solo dalla cartella d'ingresso.
- PDF/A: conversione con Ghostscript, suddivisione sotto 5 MB, verificatore strutturale indicativo. **Mai «conforme» senza veraPDF.**
- XML: busta, frontespizio, EA, EB, EC, ER, ED, EE, EF, EG, EH nel perimetro del caso base (vedi `docs/MATRICE_COPERTURA.md`).
- Stati separati (dati, file XML, schema, controllo ufficiale, trasmissione), invalidati solo se cambia il dichiarato.

## Cosa NON c'è o è limitato
- Quadri non coperti: EI, EL, EM, EN, EO, EP, EQ, agevolazioni e riduzioni, rinunce, legatari, testamento. Selezionarli blocca la finalizzazione.
- Dichiarazione sostitutiva: codici 1 e 2 gestiti (controllo ufficiale locale positivo su dati sintetici, 2026-11-05); codice 3, rimborsi e tardive con imposta aggiuntiva non finalizzabili.
- I dati richiesti dall'export (sesso, provincia, codici comune, stato civile…) si impostano solo da MCP o API, non dalla GUI (rilievo R20).
- Con Java 11 o successivi il controllo ufficiale si ferma se la fornitura ha allegati EG (manca una libreria di sistema): serve Java 8 o una libreria aggiuntiva (proposta P9 in `docs/PROPOSTE_telematico.md`). L'adattatore di oggi fallisce con Java 21 in quel caso.
- Il calcolo dell'imposta copre il perimetro dichiarato. Il dubbio 82,0875 contro 82,08 resta aperto (`docs/regole/dubbio_arrotondamento.md`).
- Documenti di installazione, manuale breve e configurazione MCP non sono stati scritti: il contenuto essenziale è in `docs/STATO_area4.md`.
- Nessun invio reale, nessun accesso autenticato, nessuna credenziale.

## Da collaudare su Windows o con servizi reali
Installazione e avvio (A01), MCP con il client Claude effettivo (A03), validazione PDF/A con veraPDF (A11), controllo con Desktop Telematico (A10 completo), risultanze catastali via Entratel (A13-A14), invio e ricevute (A17-A19). Procedure: `docs/COLLAUDO_RIPRENDIBILE.md`, `docs/PDFA.md`, `docs/STATO_area4.md`.

## Rilievi noti aperti
Elenco in `docs/RISPOSTA_ALLA_REVISIONE.md`. In particolare R12 (esito `.esi` negativo e rischio di doppio invio) va risolto prima di qualsiasi trasmissione.

## Provarla in cinque minuti
```bash
pip install -e ".[test]"
SUCCESSIONI_DATA=$(mktemp -d) python3 -m successioni.cli gui      # apre l'interfaccia locale con token
python3 -m pytest -q
```
Facoltativo, controllo ufficiale locale: scaricare i componenti dal JNLP ufficiale (`fonti/Programma e controlli/`), impostare `SUCCESSIONI_CONTROLLI_SUC13=<cartella dei jar>` e rilanciare `pytest`.

## Per i revisori
Ambito e formato: `docs/REVISIONE_ESTERNA_BRIEF.md`. Il rapporto del revisore interno su Opus è `docs/REVISIONE_INDIPENDENTE.md`: un revisore esterno non deve leggerlo prima di aver finito il suo.
