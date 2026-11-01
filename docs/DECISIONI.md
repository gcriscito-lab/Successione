# Decisioni di progetto

| Data | Decisione | Motivo / stato |
|---|---|---|
| 2026-11-01 | Python 3.13 (>=3.11), SQLite WAL, lxml, SDK `mcp` 2.x (`MCPServer`), Starlette/uvicorn per la GUI locale | Provato nel container: archivio, MCP stdio reale e Ghostscript funzionano. Impacchettamento Windows (eseguibile autonomo + collegamento): **da collaudare** |
| 2026-11-01 | Un solo `Servizio` per GUI e MCP; stato nel file di archivio, non nel processo | Requisito A15: chiusura del client senza perdita |
| 2026-11-01 | PDF/A: conversione Ghostscript, validazione solo con veraPDF | L'esecuzione dell'installer veraPDF scaricato è stata bloccata dai permessi del container: validazione indipendente **da collaudare** |
| 2026-11-01 | MCP legge solo dalla cartella d'ingresso dell'app | Nessuna lettura arbitraria del PC |
| 2026-11-01 | Nessun calcolo fiscale dalla memoria | Solo da fonti in `fonti/`, con riferimento e versione |
