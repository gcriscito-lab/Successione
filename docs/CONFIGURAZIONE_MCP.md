# Configurazione del server MCP

## Claude Code (provato il 2026-11-02 su Windows)
```powershell
claude mcp add successioni --transport stdio --scope user -e "SUCCESSIONI_DATA=<cartella dati di prova>" -- "<repo>\.venv\Scripts\python.exe" -s "<repo>\scripts\windows\avvia_successioni.py" mcp
claude mcp list        # deve mostrare: successioni ... Connected
```
Il nome va messo **prima** delle opzioni `-e`/`--env`, che altrimenti lo assorbono. Un server aggiunto a sessione avviata compare solo in una **sessione nuova**.

## Claude Desktop (da collaudare)
`python scripts\windows\configura_mcp.py` stampa la voce da inserire in `claude_desktop_config.json`; con `--scrivi-claude-desktop` la scrive (copia di sicurezza del file precedente). Poi riavvio completo dell'app. Non ancora provato.

## Verifica
Gli strumenti hanno prefisso `successioni_` (20): capacita, schema_dati, crea_pratica, elenca_pratiche, leggi_pratica, aggiorna_pratica, revisioni_pratica, differenze_pratica, verifica_pratica, stato_quadri, esporta_xml, stato_elaborati, controllo_ufficiale, file_in_ingresso, acquisisci_allegato, prepara_pdfa, suddividi_allegato, elenca_allegati, invio_prepara, invio_stato (l'MCP non conferma né trasmette: solo l'app).
Si legge sempre la pratica prima di modificarla: `aggiorna_pratica` richiede `revisione_attesa` e una `chiave_richiesta` univoca. Gli id delle righe non si scelgono: li assegna il sistema.

## Claude in sola lettura
Impostazioni → Operatività e sicurezza → «Claude (MCP) in sola lettura» (oppure `SUCCESSIONI_MCP_SOLA_LETTURA=1` nell'ambiente del server). La preferenza si
rilegge a ogni chiamata: vale subito, senza riavviare. In sola lettura Claude puo' leggere pratiche, revisioni, differenze, verifiche, stato dei quadri e dei file,
allegati e codici fiscali, ma gli strumenti che modificano o producono qualcosa (`crea_pratica`, `aggiorna_pratica`, `acquisisci_allegato`, `prepara_pdfa`,
`suddividi_allegato`, `importa_xml_telematico`, `esporta_xml`, `controllo_ufficiale`, `stampa_modello`, `backup_archivio`, `invio_prepara`) rispondono con l'errore
`SOLA_LETTURA` senza eseguire nulla. `successioni_capacita` riporta `sola_lettura: true/false`. La classificazione e' in `STRUMENTI_LETTURA`/`STRUMENTI_SCRITTURA`
(`mcp_server.py`): uno strumento non elencato come lettura e' trattato come scrittura (fail-closed) e un test impedisce strumenti non classificati.
`invio_stato` e `stato_elaborati` possono allineare lo stato di una copia d'invio (copia resa obsoleta da una modifica, esito finale di un tentativo):
in sola lettura girano in consultazione, il risultato mostra lo stato aggiornato ma la modifica viene annullata e l'archivio non cambia.
Interfaccia e server MCP avviati dall'avviatore leggono lo stesso `configurazione.json` accanto al programma (vedi `INSTALLAZIONE_WINDOWS.md`).

## Se il client si chiude
Lo stato è nella cartella dati: la stessa pratica si riapre da GUI o da MCP.

## Esito della prova A03 (Claude Code, dati sintetici)
Modifica da MCP visibile nella GUI e conflitto `CONFLITTO_REVISIONE` con revisione vecchia: passati. Claude Desktop: da collaudare. Questa non è una verifica ufficiale dell'Agenzia.
