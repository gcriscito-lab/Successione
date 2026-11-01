# Contratti tra moduli (coordinatore)

Proprietà dei file. **Solo il coordinatore** modifica: `schema.py`, `servizio.py`, `archivio.py`, `errori.py`,
`valori.py`, `mcp_server.py`, `web.py`, `cli.py`, `pyproject.toml`, `CLAUDE.md`, questo file. Gli agenti scrivono solo
nei propri moduli e propongono modifiche comuni in `docs/PROPOSTE_<area>.md` (campo, motivo, fonte).
Nessun agente esegue `git commit/push`. Dipendenze nuove: proporle, non installarle nel prodotto.

## Modello dati comune (vedi `schema.py`)
`dati` di pratica = dict con collezioni `persone, beni, devoluzioni, passivita, documenti_ref` (liste di dict con `id`
stabile `xx_...` e `_origine`) e sezioni `opzioni`, `note`. Importi: stringhe decimali con punto. Quote: `{"num","den"}`.
Stato del dato: `{"stato": "assente|zero|non_applicabile|da_confermare"}`. Gli id interni non coincidono con righi/moduli
ministeriali: la mappatura id→modulo/rigo è prodotta dal modulo telematico e non salvata nel modello.

## Errore di controllo
`schema.Errore(codice, percorso, messaggio, fonte)` — `fonte` deve citare documento+pagina/elemento XSD+versione.

## Esiti (parole fisse, vedi docs/COLLAUDO_CLOUD_WINDOWS.md)
`passato | fallito | da_collaudare | simulazione`. Un esito reale richiede input/output/ambiente documentati.

## Area 1 — `successioni.telematico` (regole fiscali, XSD, calcoli)
- `esporta_xml(dati: dict, contesto: ContestoExport) -> EsitoExport` con `EsitoExport(xml: bytes|None, errori: list[Errore], non_supportato: list[str], mappa: dict[id_interno -> riferimento XML/quadro/rigo])`; mai XML parziale presentato come completo: se la pratica usa casi non supportati, `xml=None`/`non_supportato` valorizzato.
- `valida_xsd(xml: bytes) -> list[Errore]` (lxml, XSD da `fonti/`, sola lettura).
- `calcola(dati: dict) -> RisultatoCalcolo` (Decimal/Fraction, passaggi spiegabili con fonte/versione/decorrenza).
- `docs/MATRICE_COPERTURA.md` (campo/regola/caso/test, stato) è di proprietà dell'area 1.

## Area 2 — documenti e PDF/A (`pdfa.py`, `allegati.py`, `documenti/`)
- Mantiene le firme pubbliche già testate in `tests/test_pdfa.py`; estensioni in `successioni.documenti`:
  `riduci_o_suddividi(pdf, limite_byte) -> list[Path]`, `incorpora_base64(percorso) -> str`,
  `verifica_fornitura(manifest, limite_compresso) -> list[Errore]`.
- Nessun esito `conforme` senza validatore indipendente (veraPDF); l'esito corretto altrimenti è `non_verificato`.

## Area 3 — `successioni.collegamenti` (controllo ufficiale, catasto, invio)
- Ogni adattatore: classe con metodi che restituiscono `RisultatoAdattatore(esito, dettaglio, artefatti, azione_richiesta)`
  con `esito` ∈ {passato, fallito, da_collaudare, simulazione}. Interfacce (Protocol): `ControlloUfficiale.esegui(xml_path)`,
  `CatastoEntratel.avvia/riprendi/leggi_risultati`, `InvioSUC13.prepara/conferma/trasmetti/riconcilia`, `Ricevute.associa`.
- Stato persistente: usare la tabella `job` esistente (`tipo`, `stato`, `input`, `risultato` JSON). Nuove tabelle: proporle.
- Credenziali/certificati: mai in codice, log, repository; solo variabili d'ambiente/percorsi configurati dall'utente.
- Nessun invio reale né accesso autenticato; nessun endpoint inventato.

## Integrazione (coordinatore)
Servizio/MCP/GUI chiamano i moduli sopra; i test d'integrazione sono in `tests/test_integrazione_*.py` (coordinatore).
