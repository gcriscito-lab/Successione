# Risposta ai rilievi della revisione indipendente

Rapporto: `docs/REVISIONE_INDIPENDENTE.md` (commit esaminato `08c3587`). Stato al momento della scrittura; ogni correzione ha un test di
regressione in `tests/test_correzioni_revisione.py`. «Corretto» significa corretto e provato con test locali.

| Rilievo | Gravità | Esito | Dove |
|---|---|---|---|
| R1 «finalizzabile» incoerente con l'export | alta | **corretto**: finalizzabile richiede un file XML completo generato sui dati attuali; il motivo è mostrato (`blocchi_finalizzazione`) | `servizio.py` verifica/quadri, GUI barra di stato |
| R2 dichiarazione sostitutiva ignorata | alta | **corretto lato verifica**: la pratica non è finalizzabile. Resta da correggere l'XML (`PrimaDichiarazione` fisso, area 1) | `quadri.py` |
| R3 protezione dei campi calcolati aggirabile | alta | **corretto**: i campi che iniziano con `_` e `id` sono riservati | `servizio.py` `_applica` |
| R4 id modificabili tramite `campi` | alta | **corretto**; i vecchi test usavano proprio la falla | `servizio.py`, `tests/test_servizio.py` |
| R6 backup incompleto, nessun ripristino | alta | **corretto**: il backup include `elaborati/`; nuovi `Archivio.ripristina` e `successioni ripristina` (solo su archivio vuoto) | `archivio.py`, `cli.py` |
| R20 campi dell'export non compilabili da GUI | alta | **corretto in parte (2026-11-02)**: sesso, provincia di nascita, grado di parentela, tipo soggetto, comune e provincia del decesso (persone), codici comune, indirizzo, natura, classe, consistenza, tipo cespite, reddito dominicale ecc. (beni) e tipo, estremi, data, possesso, bene collegato (passività) sono ora campi del modello, visibili nell'ispettore e nell'MCP; il valore dell'entità ha la precedenza su `opzioni.telematico`. **Restano in `opzioni.telematico`** e senza maschera nella GUI i dati a livello di dichiarazione (stato civile, codice carica, contatti, versamento) e quelli strutturati (superficie, ripartizione) | `schema.py` |
| R8 date impossibili | media | **corretto** (data reale); resta il controllo del carattere finale del codice fiscale (generatore verificato in `telematico/identificativi.py`, da collegare) | `schema.py` |
| R9 HTTP 500 e host di prova ammesso | media | **corretto**: 422 `RICHIESTA_NON_VALIDA`; l'host `testserver` solo con `ammetti_host_di_prova` | `web.py` |
| R7 devoluzioni raggruppate per diritto grezzo | media | **aperto** (dipende dalla sostituzione dei codici di diritto con quelli XSD, P1) | — |
| R10 quote con devoluzione per legge | media | **aperto** (area 1; prova da rieseguire con il controllo ufficiale) | — |
| R11 passaggio manuale non completabile dall'app | media | **aperto** | — |
| R12 `.esi` con resultCode diverso da 00 | media | **corretto (2026-11-02)**: un esito negativo di Multifile non prova più il mancato ricevimento; l'esito resta incerto e solo il protocollo o la dichiarazione esplicita «non trasmesso» con il luogo della verifica permettono un nuovo tentativo. Test `test_r12_*` | `collegamenti/invio.py` |
| R13 «valore» è la quota del defunto, non spiegato | media | **corretto (2026-11-02)**: aiuto contestuale nell'ispettore, in `/api/schema` e nello schema MCP (`aiuti_campi`) | `schema.py` `AIUTI` |
| R17 doppia arrotondatura (fino a 1 euro) | bassa | **aperto**, collegato al dubbio 82,0875 / 82,08 | `telematico/calcolo.py` |

I rilievi non elencati (bassi) restano nel rapporto. Nessun rilievo è stato chiuso senza test.

Altri rilievi chiusi da Codex (CE01-CE10) e integrati il 2026-11-02: vedi `docs/CORREZIONI_CODEX.md`.
Correzione dell'interfaccia del 2026-11-02: il messaggio «Salvato» ora compare dopo il ricaricamento dello stato, non prima.
