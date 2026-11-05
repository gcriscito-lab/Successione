# Guida all'installazione e configurazione su Windows

## Prerequisiti e requisiti di sistema
- Windows 10 o 11 a 64 bit.
- Non sono richiesti diritti di amministratore per l'installazione dell'utente corrente.
- Dipendenze esterne opzionali (rilevate e verificate tramite `Diagnosi.cmd`):
  - Ghostscript (conversione ed elaborazione PDF/A)
  - veraPDF e Java (verifica della conformita PDF/A)
  - Java 8 (modulo di controllo ufficiale SUC13 dell'Agenzia delle Entrate)

## Procedura di installazione
1. Estrarre l'intero archivio ZIP del pacchetto in una cartella a scelta.
2. Fare doppio clic su `Installa.cmd`. Il programma viene copiato nella cartella `%LOCALAPPDATA%\Programs\Successioni` e viene creato il collegamento "Successioni" sul desktop (mediante `installa.ps1`).
3. Al termine dell'installazione viene eseguita automaticamente la diagnosi dei prerequisiti.
4. Se Windows mostra l'avviso SmartScreen ("PC protetto da Windows"), cliccare su "Ulteriori informazioni" e poi su "Esegui comunque".

Per disinstallare l'applicazione mantenendo inalterati i dati utente, eseguire `Disinstalla.cmd` (che richiama `disinstalla.ps1`).

## Avvio ed uso dell'applicazione
- Fare doppio clic sul collegamento "Successioni" sul desktop oppure eseguire `Successioni.cmd`.
- L'avviatore (`scripts/windows/avvia_successioni.py`) individua una porta libera tra 8765 e 8785 e apre l'interfaccia web nel browser predefinito all'indirizzo `http://127.0.0.1:<porta>/`.
- La finestra di console ridotta a icona e il processo dell'applicazione: la sua chiusura arresta il server (i dati sono gia salvati).
- I dati locali restano salvati in `%LOCALAPPDATA%\Successioni` (archivio SQLite e repository allegati).

## Strumenti di gestione e manutenzione
- `Diagnosi.cmd` (`scripts/windows/diagnosi.py`): verifica la presenza di Ghostscript, veraPDF e Java. Con l'opzione `--salva-configurazione` registra i percorsi trovati in `configurazione.json`.
- `Verifica-backup.cmd` (`scripts/windows/verifica_backup.py`): controlla l'integrita e la coerenza delle copie di backup.
- `Configura-MCP.cmd` (`scripts/windows/configura_mcp.py`): configura l'integrazione MCP per Claude.
- `packaging/costruisci_pacchetto.py`: script per la generazione del pacchetto standalone offline per Windows.

## Configurazione del server MCP (Model Context Protocol)

### Comando di avvio e variabili d'ambiente
Il server MCP integrato puo essere eseguito direttamente tramite Python:
```cmd
python -m successioni.mcp_server
```
oppure mediante l'avviatore Windows specificando la modalita `mcp`:
```cmd
python scripts\windows\avvia_successioni.py mcp
```

Variabili d'ambiente reali utilizzate dal server MCP:
- `SUCCESSIONI_DATA`: percorso completo della cartella dati dell'archivio (se non impostata, viene usata la cartella predefinita `%LOCALAPPDATA%\Successioni`).
- `SUCCESSIONI_FONTI`: percorso alternativo per i file XSD e le fonti ufficiali.

### Integrazione con i client Claude
- **Claude Desktop**: `Configura-MCP.cmd` oppure `python scripts\windows\configura_mcp.py` mostra la configurazione JSON da inserire nel file `%APPDATA%\Claude\claude_desktop_config.json`. Utilizzando l'opzione `--scrivi-claude-desktop`, lo script aggiorna direttamente la configurazione creando una copia di sicurezza del file preesistente. E necessario un riavvio completo di Claude Desktop.
- **Claude Code**: aggiungere il server con il comando CLI:
```powershell
claude mcp add successioni --transport stdio --scope user -e "SUCCESSIONI_DATA=<cartella_dati>" -- "<percorso_python>\python.exe" -s "<percorso_repo>\scripts\windows\avvia_successioni.py" mcp
```

### Verifica degli strumenti MCP
Il server MCP espone 20 strumenti con prefisso `successioni_`:
- `successioni_capacita`
- `successioni_schema_dati`
- `successioni_crea_pratica`
- `successioni_elenca_pratiche`
- `successioni_leggi_pratica`
- `successioni_aggiorna_pratica`
- `successioni_revisioni_pratica`
- `successioni_differenze_pratica`
- `successioni_verifica_pratica`
- `successioni_stato_quadri`
- `successioni_esporta_xml`
- `successioni_stato_elaborati`
- `successioni_controllo_ufficiale`
- `successioni_file_in_ingresso`
- `successioni_acquisisci_allegato`
- `successioni_prepara_pdfa`
- `successioni_suddividi_allegato`
- `successioni_elenca_allegati`
- `successioni_invio_prepara` (prepara la copia da inviare; non conferma e non trasmette)
- `successioni_invio_stato`

Per verificare la visibilita degli strumenti in Claude Code, eseguire `claude mcp list` e accertarsi che il server `successioni` risulti nello stato `Connected`. Tramite lo strumento `successioni_capacita` e possibile verificare la cartella dati effettivamente in uso (`SUCCESSIONI_DATA`).

### Persistenza dei dati e chiusura del client
- Se il client MCP o l'interfaccia assistente viene chiusa, nessun dato va perso: la pratica e la cronologia delle revisioni risiedono in modo permanente nel database SQLite situato nella cartella dati (`SUCCESSIONI_DATA`).
- La stessa pratica puo essere successivamente riaperta e modificata sia dall'interfaccia web (GUI) sia tramite nuove sessioni del client MCP.

## Fonti e riferimenti documentali consultati
- Documentazione Claude Code MCP: `https://code.claude.com/docs/en/mcp.md` (consultato il 2026-11-01).
- Documentazione Model Context Protocol (Local Servers): `https://modelcontextprotocol.io/docs/develop/connect-local-servers` (consultato il 2026-11-01).
- Documentazione Python 3.13 su Windows: `https://docs.python.org/3.13/using/windows.html` (consultato il 2026-11-01).

## Da collaudare su Windows
In coerenza con quanto riportato in `docs/archivio/COLLAUDO_WINDOWS_CODEX_20261102.md` e `docs/archivio/STATO_area4.md`, gli aspetti ancora da verificare sul sistema target sono:

1. **Client effettivo Claude Desktop**: collaudo del caricamento automatico di `claude_desktop_config.json` (generato con `--scrivi-claude-desktop`), riavvio dell'applicazione e verifica della visibilita dei 18 strumenti `successioni_*` nell'interfaccia grafica.
2. **Ambiente WSL**: verifica del comportamento in ambienti WSL (accertarsi che il server operi come processo Windows nativo per condividere lo stesso archivio dati con la GUI).
3. **Installazione su percorsi utente complessi**: esecuzione di `Installa.cmd` su account utente contenenti spazi o caratteri accentati nel percorso `%USERPROFILE%`, verifica dei collegamenti sul desktop e menu Start, ed esame di eventuali blocchi da parte di SmartScreen / antivirus di terze parti.
4. **Backup e ripristino su Windows**: esecuzione di `Verifica-backup.cmd` e prova di ripristino dell'archivio tramite `successioni ripristina` in una cartella di destinazione vuota.
