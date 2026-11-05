# Piano: punti aperti affidati agli agenti gratuiti (con ricontrollo del coordinatore)

Stato al 2026-11-03. Servizio: FreeLLMAPI locale (`http://127.0.0.1:31415/v1`), chiave nelle variabili utente di Windows, mai in chat o nei file.
Compiti definiti in `docs/COMPITI_PER_AGENTI_GRATUITI.md`, lanciati con `scripts/agenti_gratuiti/lancia.py`.

## 1. Cosa si affida agli agenti e cosa no

Criterio unico: un compito si delega solo se **un comando lo verifica** e se un errore del modello **non puo' finire in un file inviato**.

| Delegabile (test, documenti, caratterizzazione) | Resta al coordinatore |
|---|---|
| Test di caratterizzazione di moduli esistenti | EI (voltura) e ogni nuovo quadro |
| Test di rotte web, strumenti MCP, servizio | Regole fiscali, quote, calcolo, aliquote |
| Test di coerenza matrice-codice | Esportazione XML e regole delle annotazioni XSD |
| Guide e manuali verificati da script | Sicurezza, conferma e trasmissione dell'invio |
| | Installazione di Ghostscript e veraPDF (rete, esecuzione di installer) |
| | Credenziali, Entratel, invio reale, catasto |
| | Tabella dei comuni tavolari, elenco delle conservatorie (non nelle fonti) |
| | Maschere grandi dell'interfaccia (`app.js`): gli agenti non hanno mai prodotto modifiche valide |
| | Revisione delle regole: i revisori gratuiti hanno mancato una discrepanza reale (EO, 2026-11-03) |

## 2. Compiti (7), file e verifica

| ID | Cosa produce | File | Verifica eseguita dal lanciatore |
|---|---|---|---|
| C13 | Test rotte web e strumenti MCP dell'invio (errori leggibili, mai HTTP 500, nessuno strumento di conferma/trasmissione in MCP) | `tests/test_invio_web_mcp.py` | `pytest` sul file |
| C14 | Caratterizzazione delle quote di legge (cosa restituisce oggi il codice) | `tests/test_devoluzione_legge_extra.py` | `pytest` sul file |
| C15 | Test di CF, IBAN, partita IVA | `tests/test_identificativi_extra.py` | `pytest` sul file |
| C16 | Guida alla compilazione dei quadri | `docs/GUIDA_QUADRI.md` | `scripts/verifica_doc_quadri.py`: ogni quadro citato, nessun identificativo inventato |
| C18 | Quadri nuovi attraverso il servizio (EO, EP, EQ, EN, EL, EM non piu' «non supportati», EI si') | `tests/test_quadri_nuovi_servizio.py` | `pytest` sul file |
| C19 | Coerenza tra matrice di copertura e codice | `tests/test_matrice_coerenza.py` | `pytest` sul file |
| C21 | Tabella «quadri disponibili» per il professionista | `docs/QUADRI_DISPONIBILI.md` | `scripts/verifica_doc_quadri.py` |

Gia' chiusi con gli agenti: C3, C4, C8, C9, C10, C12.

## 3. Esecuzione

Un lancio per compito e per modello, in parallelo e su file distinti (nessun conflitto: ogni agente lavora in una copia isolata).
Modelli, in ordine di resa osservata: `claude-sonnet-4-5`, `gpt-oss-120b`, `codestral`; di riserva `gemini-3.8-flash`, `mistral-large-3`, `deepseek-v4-pro`.
Gli errori 502 e 503 del servizio sono frequenti: se un lancio fallisce per quel motivo si rilancia sullo stesso compito con un altro modello (fino a 2 giri).

```powershell
# dalla radice, con FREELLMAPI_KEY gia' nelle variabili utente
$env:FREELLMAPI_BASE_URL = "http://127.0.0.1:31415/v1"
foreach ($c in "C13","C14","C15","C16","C18","C19","C21") {
  foreach ($m in "claude-sonnet-4-5","gpt-oss-120b","codestral") {
    $env:FREELLMAPI_MODEL = $m
    Start-Process -NoNewWindow .\.venv\Scripts\python.exe -ArgumentList "scripts\agenti_gratuiti\lancia.py",$c
    Start-Sleep 3
  }
}
```

## 4. Ricontrollo del coordinatore (obbligatorio, in questo ordine)

1. **Perimetro**: la patch tocca solo il file consentito (il lanciatore lo impone; si rilegge `CONSEGNA.md`).
2. **Verifica reale**: si riesegue il comando di verifica; il messaggio «verifiche passate» da solo non basta (nei compiti senza verifica automatica non prova nulla).
3. **Mutazione**: per ogni file di test si introduce a mano un difetto nel codice che il test dichiara di coprire e si verifica che fallisca; poi si ripristina il codice e `git status src` deve essere pulito. Un test che non rileva la mutazione non entra: si completa a mano (e' successo con C12: mancavano `GO` e `TS`).
4. **Lettura**: si legge la patch. Si scartano test con attese non motivate dal codice, asserzioni vuote, import fragili (`src.successioni`), a-capo CRLF, caratteri corrotti.
5. **Documenti**: lo script deve dare «ok» e inoltre si controllano a campione le frasi contro `docs/MATRICE_COPERTURA.md`; niente regole fiscali nei documenti degli agenti.
6. **Suite completa** con le variabili `SUCCESSIONI_CONTROLLI_SUC13` e `SUCCESSIONI_JAVA`: 0 falliti, saltati invariati.
7. **Commit** separato per consegna, con il modello nel messaggio.

Criteri di scarto immediato: file fuori perimetro; modifica di `src/`; invenzione di funzioni, campi o codici; regole fiscali nel testo; test che passano anche dopo la mutazione.

## 5. Cosa si sblocca e cosa resta aperto dopo

Si chiudono: copertura di test di rotte e strumenti dell'invio, degli identificativi, delle quote di legge (come caratterizzazione), dei quadri nuovi dal servizio, due documenti per il professionista e un controllo automatico che la matrice resti coerente con il codice.

Restano aperti e **non delegabili**: EI; Ghostscript e veraPDF; stampa; maschere GUI per i campi dei quadri nuovi; Entratel, invio reale e verifica ufficiale; mix di comuni (conservatorie); comuni tavolari di BL, UD, BS e VI; titoli esenti, riduzioni, agevolazioni, esteri; qualifiche multiple; rappresentanti di legatari, esecutore, trustee.

## 6. Rischi noti

- Un test di caratterizzazione fotografa il comportamento attuale: se il codice e' sbagliato nello stesso punto, il test lo conferma. Per C14 questo vale in modo particolare: le quote di legge vanno confrontate con l'Allegato 5 dal coordinatore, non dall'agente.
- Il servizio gratuito puo' fermarsi (e' successo il 2026-11-02): serve riavviare l'app FreeLLMAPI dal collegamento sul Desktop.
- I lanci scrivono in `build/agenti/` (non versionata) e usano worktree temporanei: per evitare l'errore «Filename too long» di Git su Windows impostare `TEMP` e `TMP` a una cartella corta (es. `C:\sx`).
