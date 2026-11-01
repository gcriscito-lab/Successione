# Proposte dell'area 3 (collegamenti) per il coordinatore

Modifiche a file di proprieta' del coordinatore, necessarie per integrare `successioni.collegamenti`. Nessuna e'
stata applicata dall'area 3.

## 1. Modello dati (`schema.py`)

| Campo proposto | Collezione | Motivo | Fonte |
|---|---|---|---|
| `acquisizione_ref` (str: `job_id` + chiave catastale) | beni | collegare il bene all'acquisizione catastale e ai suoi originali; oggi il legame e' solo nel job | specifica §5, §9 ("conserva risultati originali o rappresentazione tracciabile") |
| `reddito_dominicale`, `reddito_agrario` (importo), `qualita`, `classe`, `superficie` (str) | beni (terreni) | restituiti dalle risultanze ma senza destinazione: oggi segnalati `CAMPI_SENZA_DESTINAZIONE` | quadro EB; nomi da allineare agli XSD con l'area 1 |
| `classe`, `consistenza`, `indirizzo` (str) | beni (fabbricati) | come sopra | quadro EC; allineare agli XSD |
| `graffati` (lista di {foglio, particella, subalterno}) | beni | i graffati vanno segnalati e, se il modello li prevede, dichiarati; oggi solo segnalazione | specifica §9; XSD da verificare (area 1) |

Fino ad allora `catasto.proponi_importazione` propone solo campi gia' presenti in `schema.COLLEZIONI["beni"]`.

## 2. Servizio / MCP (`servizio.py`, `mcp_server.py`)

Strumenti delimitati (nessuno trasmette):

- `successioni_controllo_ufficiale(pratica_id, chiave_richiesta)`: esporta l'XML (area 1), chiama
  `controllo.controllo_ufficiale(arch).esegui(xml, pratica_id=..., revisione=..., impronta_dichiarativa=...)`,
  restituisce `job_id`, `esito`, `stato_controllo`, `azione_richiesta`. Passare SEMPRE `impronta_dichiarativa`:
  serve a `stati_pratica` per marcare obsoleto il controllo quando cambia il dichiarato (A16).
- `successioni_controllo_registra_diagnostico(job_id, file_dgn, file_log, file_wri?)`: file presi solo dalla
  cartella d'ingresso dell'app (come gli allegati).
- `successioni_catasto_avvia(pratica_id, ambito, chiave_richiesta)`, `successioni_catasto_riprendi(job_id)`,
  `successioni_catasto_risultati(job_id)`, `successioni_catasto_proponi(job_id, selezione?)`; l'applicazione della
  proposta passa da `aggiorna_pratica` con `origine="acquisito"` (esporre il parametro `origine` nello strumento
  MCP di aggiornamento, oggi fissato a `proposto_assistente` per il canale mcp).
- `successioni_invio_prepara(pratica_id, ...)`, `successioni_invio_stato(pratica_id)` (= `invio.stati_pratica`),
  `successioni_esiti(protocollo)` (= `stato_esiti`), `successioni_ricevuta_registra(protocollo, tipo, esito, file)`.
- **Solo nell'interfaccia, non via MCP:** `conferma` (gia' rifiutata da `canale != "gui"`), `trasmetti` e la
  riconciliazione `non_trasmesso` (abilita un nuovo invio). Motivo: "la conferma finale nell'app autorizza la
  specifica trasmissione" (specifica §1).
- `successioni_job(job_id)`: lettura generica di un job (stato, esito, azione richiesta) per la ripresa (A15).

## 3. Interfaccia (`web.py`, `static/`)

Area "Invio ed esiti": copia congelata (elenco elaborati con impronta, importi, profilo, revisione) e pulsante di
conferma che invia `impronta_conferma` mostrata; stato del tentativo con `azione_richiesta`; modulo di
riconciliazione (protocollo + "verificato su", file `.esi`); registrazione delle ricevute con tipo scelto
dall'utente. Barra di stato: "controllo ufficiale" da `stati_pratica` (positivo/negativo/obsoleto/non eseguito).
Impostazioni: percorso di Java e cartella dei JAR (`SUCCESSIONI_JAVA`, `SUCCESSIONI_CONTROLLI_SUC13`), non segreti.

## 4. Archivio (`archivio.py`)

Nessuna nuova tabella: tutto sta in `job` (tipi `controllo_ufficiale`, `catasto_entratel`, `invio_copia`,
`invio_tentativo`, `ricevuta_suc13`) e nel deposito `allegati/` (artefatti content-addressed, inclusi nel backup).
Facoltativo in una migrazione futura: `CREATE INDEX job_tipo_pratica ON job(tipo, pratica_id)`. Nota: gli
artefatti dei collegamenti sono file in `allegati/` senza riga nella tabella `allegati`; un'eventuale pulizia degli
orfani deve escludere i file referenziati da `job.risultato` (`artefatti[].sha256`).

## 5. Repository

- `.gitattributes`: aggiungere `src/successioni/collegamenti/fixture/** -text`, perche' le uscite registrate del
  componente ufficiale mantengano i byte esatti (impronte nel `manifest.json`) anche su checkout Windows.
- `pyproject.toml`: nessuna dipendenza nuova. I fixture servono solo ai test; se si vogliono nel pacchetto
  installato, aggiungere `collegamenti/fixture/*` a `package-data`.

## 6. Riscontri per l'area 1 (dal controllo ufficiale reale, 2026-11-01)

Export "bozza tecnica" di `tests/telematico_casi.py::caso_completo` controllato con il componente 2.3.1
(SHA-256 input `69de9992c59ee0b8a6dc2066fcbcef48ba638fbd5b4101c6497e459577591e57`): dichiarazione scartata con
(***) quadri EF, EG, EH obbligatori; "Codice Fiscale errato" per defunto, presentatore ed eredi (carattere di
controllo non valido nei casi sintetici); "Numero di soggetti presenti nella sezione devoluzione diverso da quello
degli Eredi aventi diritto" (dichiarato 1, atteso 2); quadro ER "Dati di devoluzione non coerenti con quelli
relativi agli Eredi" (quote 1/3 e 2/3 contro 1/2 attesa con devoluzione per legge). Sono riscontri applicativi del
componente, da confrontare con le fonti prima di diventare regole (specifica §3).
