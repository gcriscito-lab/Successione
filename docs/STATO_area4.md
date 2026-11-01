# Stato area 4: installazione Windows, manuale breve, configurazione MCP

Ultimo aggiornamento: 2026-11-01 (ripresa dopo interruzione; il lavoro precedente dell'area 4 non era nel repository).

## Fatto

- Letti CLAUDE.md, prompt, specifica (§6, §11, §12), COLLAUDO_CLOUD_WINDOWS, CONTRATTI_MODULI, PDFA, COLLEGAMENTI,
  pyproject, cli, mcp_server, web, archivio, servizio, elaborati.
- Fonti scaricate in scratchpad (2026-11-01): code.claude.com/docs/en/mcp.md (sha256 725767f7...), mcp-quickstart.md,
  desktop.md, desktop-wsl.md; modelcontextprotocol.io connect-local-servers (sha256 856a0bca...); ghostscript Install;
  docs.verapdf.org/install; docs.python.org/3.13/using/windows.html (embeddable).
- Python embeddable 3.13.17 amd64 scaricato: sha256 9e35319b...86ddb38, uguale alla pagina di rilascio python.org.
- Difetti individuati (da provare/registrare in PROPOSTE_installazione.md):
  D1 backup senza `elaborati/` (XML esportati); D2 wheel senza app.css/app.js (package-data solo *.html);
  D3 `radice_fonti()` = parents[3] non funziona da site-packages; D4 percorsi relativi con `\` su Windows
  (allegati/elaborati: `str(relative_to)`); D5 pythonw: uvicorn usa `sys.stdout.isatty()` (da provare);
  D6 la GUI non ha comando di arresto; D7 nessun comando `ripristina`.
- pwsh per controllare la sintassi PowerShell: download negato dal classificatore; ps1 ridotti al minimo, logica in Python.

## In corso

- packaging/costruisci_pacchetto.py (build del pacchetto Windows anche da Linux).

## Da fare

1. scripts/windows/: avvio GUI (launcher), installazione + collegamento desktop, diagnosi, configura_mcp.
2. docs/INSTALLAZIONE_WINDOWS.md, docs/CONFIGURAZIONE_MCP.md, docs/MANUALE_BREVE.md, docs/PROPOSTE_installazione.md.
3. Prova A02 backup/ripristino su Linux; tests/test_installazione*.py; suite completa.

## Comandi

```bash
cd /home/user/Successione
python -m pytest -q                      # suite completa
python -m pytest -q tests/test_installazione*.py
```
