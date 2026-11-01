# Stato area 4: installazione Windows, manuale breve, configurazione MCP

Ultimo aggiornamento: 2026-11-01 (ripresa dopo interruzione; il lavoro precedente dell'area 4 non è presente nel repository).

## Fatto

- (nulla ancora: avvio della ripresa)

## In corso

- Lettura di CLAUDE.md, prompt, specifica, contratti, PDFA, collegamenti, codice cli/mcp_server/web/archivio.

## Da fare

1. docs/INSTALLAZIONE_WINDOWS.md (scelta motivata dell'approccio).
2. scripts/windows/: build del pacchetto, collegamento desktop, avvio GUI, diagnosi prerequisiti.
3. docs/CONFIGURAZIONE_MCP.md (Claude Desktop e Claude Code su Windows, WSL, prova A03 riprendibile).
4. docs/MANUALE_BREVE.md.
5. Prova backup/ripristino su Linux (A02) e difetti in docs/PROPOSTE_installazione.md.
6. tests/test_installazione*.py e suite completa.

## Comandi

```bash
cd /home/user/Successione
python -m pytest -q                      # suite completa
python -m pytest -q tests/test_installazione*.py
```
