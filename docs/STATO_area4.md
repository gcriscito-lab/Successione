# Stato area 4: installazione Windows, manuale breve, configurazione MCP

Ultimo aggiornamento: 2026-11-01 21:20 circa (ripresa dopo interruzione).

## Fatto

- Letture: CLAUDE.md, prompt, specifica (§6, §11, §12), COLLAUDO_CLOUD_WINDOWS, CONTRATTI_MODULI, PDFA, COLLEGAMENTI,
  codice cli/mcp_server/web/archivio/servizio/elaborati.
- Fonti consultate 2026-11-01 (copie in scratchpad): code.claude.com/docs/en/mcp.md (sha256 725767f7...),
  mcp-quickstart.md, desktop.md, desktop-wsl.md; modelcontextprotocol.io connect-local-servers (856a0bca...);
  ghostscript Install; docs.verapdf.org/install; docs.python.org/3.13/using/windows.html.
- Python embeddable 3.13.17 amd64: sha256 9e35319b...86ddb38 = pagina di rilascio python.org.
- `packaging/costruisci_pacchetto.py` + `packaging/versioni.json` + `packaging/requisiti-win64.lock` (34 wheel,
  marcatori valutati per Windows: compare pywin32 richiesto da mcp). Build reale su Linux riuscita (cartella 110 MB,
  zip 51 MB); `verifica` ok dopo correzione del controllo win32api.
- `scripts/windows/`: avvia_successioni.py (gui/mcp/backup/info), diagnosi.py, configura_mcp.py, verifica_backup.py,
  Successioni.cmd, Diagnosi.cmd, Configura-MCP.cmd, Verifica-backup.cmd, Installa.cmd + installa.ps1,
  Disinstalla.cmd + disinstalla.ps1, LEGGIMI.txt.
- Prove reali su Linux: GUI via avviatore con pythonw simulato (stdout=None) -> HTTP 200; cli diretto -> errore
  uvicorn isatty (D5). Handshake MCP stdio grezzo: 18 strumenti successioni_*, chiusura stdin -> uscita 0 in 0,21 s.
- Suite completa con le versioni del lock (venv in scratchpad, Linux): 215 passati, 1 fallito (mio test, corretto), 4 saltati.
- Il coordinatore ha corretto D1 (backup con elaborati/) e aggiunto `successioni ripristina` (commit 36e36a1):
  test A02 aggiornati (copia + comando ripristina), 23 passati + 1 saltato.

## In corso

- Ricostruzione del pacchetto con i file nuovi; documenti INSTALLAZIONE_WINDOWS, CONFIGURAZIONE_MCP, MANUALE_BREVE,
  PROPOSTE_installazione.

## Da fare

1. Documenti (4) con fonti e procedure riprendibili.
2. Suite completa finale (ambiente di sviluppo) e aggiornamento di questo file.

## Comandi

```bash
cd /home/user/Successione
python -m pytest -q tests/test_installazione*.py
python -m pytest -q
python packaging/costruisci_pacchetto.py --uscita <dir> --cache <dir>        # build (rete: python.org, PyPI)
python packaging/costruisci_pacchetto.py --verifica <dir>/Successioni-0.1.0-win64
SUCCESSIONI_PACCHETTO_WIN=<dir>/Successioni-0.1.0-win64 python -m pytest -q tests/test_installazione.py
```
