# Stato area 4: installazione Windows, manuale breve, configurazione MCP

Ultimo aggiornamento: 2026-11-01, chiusura richiesta dal coordinatore (beta congelata).
Suite completa `python3 -m pytest -q`: **238 passati, 8 saltati** (ambiente di sviluppo, Linux, Python 3.13.18).

## Fatto (prove reali su Linux; NON collaudo su Windows)

- `packaging/costruisci_pacchetto.py`, `packaging/versioni.json`, `packaging/requisiti-win64.lock`: pacchetto
  portabile = Python embeddable 3.13.17 amd64 (sha256 9e35319b...86ddb38, uguale alla pagina di rilascio python.org)
  + 34 wheel win_amd64/cp313 installate offline con `pip install --target` + codice in `app/src` + `app/fonti`.
  I marcatori sono valutati per Windows (pip li valuta sulla macchina che scarica): cosi' entra pywin32, richiesto
  da mcp su win32. Build reale su Linux: cartella 110 MB, zip 51 MB, `--verifica` senza problemi.
- Suite completa eseguita anche con le versioni del lock (venv in scratchpad, wheel Linux delle stesse versioni):
  215 passati, 4 saltati, 1 fallito = mio test con errore di stringa, poi corretto.
- `scripts/windows/`: `avvia_successioni.py` (gui/mcp/backup/info; configurazione.json; ricerca strumenti in
  Program Files; riapre la sessione gia' aperta; porta libera 8765-8785; log se senza console),
  `diagnosi.py`, `configura_mcp.py` (stampa JSON Claude Desktop e comando `claude mcp add`; unione con copia di
  sicurezza), `verifica_backup.py`, `Successioni.cmd`, `Diagnosi.cmd`, `Configura-MCP.cmd`, `Verifica-backup.cmd`,
  `Installa.cmd`+`installa.ps1` (utente corrente, backup prima di aggiornare, collegamenti desktop/Start),
  `Disinstalla.cmd`+`disinstalla.ps1`, `LEGGIMI.txt`. File .cmd/.ps1 solo ASCII, CRLF nel pacchetto.
- Test: `tests/test_installazione.py` (16 + 1 saltato senza pacchetto), `tests/test_installazione_backup.py` (7).
  Coprono: GUI reale su 127.0.0.1 con token/Host, seconda apertura, pythonw simulato; MCP stdio reale tramite
  avviatore (18 strumenti `successioni_*`, stesso archivio della GUI, conflitto di revisione, chiusura stdin ->
  uscita 0 entro 5 s; misurata 0,21 s); diagnosi; configurazione MCP; montaggio offline; lock coerente con pyproject.
- A02 su Linux: pratica (caso sintetico completo) + modifica MCP + PDF di 3 pagine + derivato PDF/A + XML bozza
  tecnica -> `successioni backup` -> ripristino per copia e con `successioni ripristina --destinazione` ->
  pratica, revisioni, allegati, pagine, hash ed XML identici; ripristino su archivio in uso rifiutato.

## Difetti trovati (da riportare in docs/PROPOSTE_installazione.md, non scritto per la chiusura)

- D1 backup senza `elaborati/`: **corretto dal coordinatore** (commit 36e36a1), test di regressione presente.
- D2 la wheel del progetto contiene solo `static/index.html`: `app.js`/`app.css` danno 404 se installato con pip
  (provato: wheel costruita fuori dal repository). Correzione: `successioni = ["static/*"]` in pyproject.
- D3 `telematico/fonti.radice_fonti()` = `parents[3]/fonti`: da site-packages punta a una cartella inesistente
  (provato, XSD non trovato). Il pacchetto Windows lo evita con la disposizione `app/src` + `app/fonti` e
  `SUCCESSIONI_FONTI` impostata dall'avviatore.
- D4 percorsi relativi salvati con `str(relative_to)` (allegati.py, elaborati.py): su Windows con `\`; archivio non
  portabile tra sistemi. Proposta: `.as_posix()`. `verifica_backup.py` accetta entrambi.
- D5 `successioni gui` con pythonw.exe fallisce (uvicorn `sys.stdout.isatty()` su None, provato con stdout=None):
  l'avviatore lo evita; proposta `use_colors=False` in `web.avvia`.
- D6 la GUI non ha un comando di arresto: si chiude chiudendo la finestra della console (documentato nel LEGGIMI).
- D8 GUI/`/api/info` non mostrano la cartella dati: utile per verificare che GUI e MCP usino lo stesso archivio
  (MCP la rivela tramite `cartella_ingresso` di `successioni_capacita`).

## Da collaudare su Windows (procedura riprendibile)

1. A01: estrarre lo zip prodotto da `costruisci_pacchetto.py`, `Installa.cmd` (senza amministratore), verificare
   collegamento desktop, apertura del browser su 127.0.0.1, `Diagnosi.cmd` con/ senza Ghostscript, Java, veraPDF;
   utente con spazi/accenti nel nome; firma Authenticode di python.exe (`Get-AuthenticodeSignature`); SmartScreen/
   antivirus; caricamento di pywin32 senza post-install; aggiornamento con backup automatico; disinstallazione.
2. A03 con il client effettivo: `Configura-MCP.cmd --scrivi-claude-desktop` (oppure Impostazioni > Sviluppatore >
   Modifica config), riavvio completo di Claude Desktop, strumenti `successioni_*` visibili; crea pratica da Claude ->
   visibile nella GUI; modifica dalla GUI -> aggiornamento da Claude con revisione vecchia = CONFLITTO_REVISIONE;
   chiusura di Claude durante il lavoro -> riapertura con stessa revisione. Claude Code nativo:
   `claude mcp add --transport stdio --scope user successioni -- "<...>\python\python.exe" -s "<...>\app\avvia_successioni.py" mcp`.
3. WSL: il server deve restare il processo Windows (stesso archivio); un processo Linux dentro WSL userebbe un altro
   archivio. Avvio dell'exe Windows tramite interop da WSL: non provato.
4. A02 su Windows: `Successioni.cmd` aperto + backup, `Verifica-backup.cmd`, `successioni ripristina` in cartella nuova.

## Non completato per la chiusura

- docs/INSTALLAZIONE_WINDOWS.md, docs/CONFIGURAZIONE_MCP.md, docs/MANUALE_BREVE.md, docs/PROPOSTE_installazione.md
  non scritti (il contenuto essenziale e' in questo file e nei commenti degli script).
- `scripts/windows/costruisci_pacchetto.cmd` (involucro batch della build) non creato: su Windows usare
  `py -3.13 packaging\costruisci_pacchetto.py`.

## Fonti (consultate il 2026-11-01)

- https://code.claude.com/docs/en/mcp.md (sha256 725767f7...): `claude mcp add ... -- <comando>`, `--env`, scope,
  arresto stdio su Windows (chiude stdin, poi termina dopo 300 ms); desktop.md: Claude Desktop carica
  `claude_desktop_config.json` anche nelle sessioni Code locali, la CLI no.
- https://modelcontextprotocol.io/docs/develop/connect-local-servers (sha256 856a0bca...): `%APPDATA%\Claude\claude_desktop_config.json`,
  Settings > Developer > Edit Config, riavvio completo, log `%APPDATA%\Claude\logs\mcp-server-NOME.log`.
- https://docs.python.org/3.13/using/windows.html (par. 4.4 embeddable, file ._pth).
- https://ghostscript.readthedocs.io/en/latest/Install.html (gswin64c.exe in gs#.##\bin, licenza AGPL/commerciale).
- https://docs.verapdf.org/install/ (installer zip, vera-install.bat, installazione automatica).

## Comandi

```bash
cd /home/user/Successione
python3 -m pytest -q                                   # suite completa
python3 -m pytest -q tests/test_installazione*.py
python3 packaging/costruisci_pacchetto.py --uscita <dir> --cache <dir>    # rete: python.org, PyPI
python3 packaging/costruisci_pacchetto.py --verifica <dir>/Successioni-0.1.0-win64
SUCCESSIONI_PACCHETTO_WIN=<dir>/Successioni-0.1.0-win64 python3 -m pytest -q tests/test_installazione.py
```
