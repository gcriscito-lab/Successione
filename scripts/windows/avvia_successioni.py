"""Avviatore del pacchetto Successioni (collegamento sul desktop, server MCP per Claude, backup).

Uso (dal pacchetto installato, con il Python incorporato):
    python\\python.exe -s app\\avvia_successioni.py gui        interfaccia locale (solo 127.0.0.1) e browser
    python\\python.exe -s app\\avvia_successioni.py mcp        server MCP su stdio (per Claude Desktop / Claude Code)
    python\\python.exe -s app\\avvia_successioni.py backup <cartella>
    python\\python.exe -s app\\avvia_successioni.py info       percorsi e strumenti effettivi (JSON)

Cosa aggiunge al comando `successioni` (src/successioni/cli.py), senza modificarne il comportamento:
- legge `configurazione.json` accanto al programma (solo variabili SUCCESSIONI_* note; quelle gia' presenti
  nell'ambiente prevalgono) e cerca gli strumenti esterni nelle cartelle standard di Windows;
- in tutti i modi (anche `mcp`, avviato da Claude Desktop) indica a `successioni.impostazioni` lo STESSO file
  (SUCCESSIONI_CONFIG): preferenze come «Claude in sola lettura» e profilo dello studio valgono per interfaccia e Claude;
- con pythonw.exe (nessuna console) reindirizza stdout/stderr su un file di log: uvicorn altrimenti fallisce
  (`sys.stdout.isatty()` su None, provato il 2026-11-01);
- se l'interfaccia e' gia' aperta riapre il browser sulla stessa sessione invece di fallire per porta occupata;
  altrimenti usa la prima porta libera da 8765 a 8785.
In modalita' `mcp` non scrive nulla su stdout (riservato al protocollo).
"""
from __future__ import annotations

import glob
import json
import os
import re
import secrets
import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path

QUI = Path(__file__).resolve().parent
# Pacchetto: <radice>/app/avvia_successioni.py con il codice in app/src. Repository: scripts/windows/.
if (QUI / "src" / "successioni").is_dir():
    RADICE, SRC, FONTI = QUI.parent, QUI / "src", QUI / "fonti"
else:
    RADICE, SRC, FONTI = QUI.parents[1], QUI.parents[1] / "src", QUI.parents[1] / "fonti"

VARIABILI_NOTE = ("SUCCESSIONI_DATA", "SUCCESSIONI_GS", "SUCCESSIONI_ICC", "SUCCESSIONI_QPDF", "SUCCESSIONI_VERAPDF",
                  "SUCCESSIONI_JAVA", "SUCCESSIONI_CONTROLLI_SUC13", "SUCCESSIONI_CONTROLLI_TIMEOUT",
                  "SUCCESSIONI_FONTI")
PORTA_PREDEFINITA = 8765
PORTE = range(8765, 8786)
NOME_SESSIONE = "sessione_gui.json"


def file_configurazione() -> Path:
    return Path(os.environ.get("SUCCESSIONI_CONFIG") or (RADICE / "configurazione.json"))


def fissa_file_configurazione(env: dict | None = None) -> str:
    """Indica a ``successioni.impostazioni`` (variabile SUCCESSIONI_CONFIG) il file di configurazione dell'avviatore, in
    TUTTI i modi (gui, mcp, backup, info): l'interfaccia vi salva preferenze («Claude in sola lettura», visura bloccante),
    profilo dello studio e percorsi, e il server MCP avviato da Claude Desktop deve leggere lo stesso file. Senza, il server
    MCP leggerebbe ``configurazione.json`` nella cartella dei dati e ignorerebbe le scelte fatte nell'interfaccia. Un valore
    gia' presente nell'ambiente prevale."""
    env = os.environ if env is None else env
    env.setdefault("SUCCESSIONI_CONFIG", str(file_configurazione()))
    return env["SUCCESSIONI_CONFIG"]


def leggi_configurazione(percorso: Path | None = None) -> dict:
    """Solo chiavi in VARIABILI_NOTE con valore stringa; il resto e' ignorato (e segnalato da `info`)."""
    p = percorso or file_configurazione()
    try:
        dati = json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    if not isinstance(dati, dict):
        return {}
    return {k: v for k, v in dati.items() if k in VARIABILI_NOTE and isinstance(v, str) and v.strip()}


def _primo(schemi: list[str]) -> str | None:
    trovati = []
    for s in schemi:
        trovati += glob.glob(s)
    # la versione piu' recente ha di solito il nome maggiore (gs10.05.0 > gs10.02.1)
    trovati = sorted({t for t in trovati if Path(t).is_file()}, key=lambda t: [int(x) if x.isdigit() else x
                                                                                for x in re.split(r"(\d+)", t)])
    return trovati[-1] if trovati else None


def candidati_windows(env: dict | None = None) -> dict:
    """Strumenti nelle cartelle standard di Windows (solo se il file esiste). Non usato su altri sistemi."""
    env = env if env is not None else os.environ
    pf = [env.get("ProgramFiles", r"C:\Program Files"), env.get("ProgramFiles(x86)", r"C:\Program Files (x86)")]
    la = env.get("LOCALAPPDATA", "")
    out = {}
    gs = _primo([str(Path(p) / "gs" / "gs*" / "bin" / "gswin64c.exe") for p in pf]
                 + [r"C:\gs\gs*\bin\gswin64c.exe"])   # installazione silenziosa con /D=C:\gs\gs<versione>
    if gs:
        out["SUCCESSIONI_GS"] = gs
    qpdf = _primo([str(Path(p) / "qpdf*" / "bin" / "qpdf.exe") for p in pf])
    if qpdf:
        out["SUCCESSIONI_QPDF"] = qpdf
    vera = _primo([r"C:\veraPDF\verapdf.bat"] + [str(Path(p) / "veraPDF" / "verapdf.bat") for p in pf]
                  + ([str(Path(la) / "veraPDF" / "verapdf.bat")] if la else []))
    if vera:
        out["SUCCESSIONI_VERAPDF"] = vera
    java = _primo([str(Path(p) / d / "*" / "bin" / "java.exe") for p in pf
                   for d in ("Eclipse Adoptium", "Java", "Microsoft", "Zulu", "Amazon Corretto")])
    if java:
        out["SUCCESSIONI_JAVA"] = java
    return out


def prepara_ambiente(env: dict | None = None, windows: bool | None = None) -> dict:
    """Completa `env` (predefinito: os.environ) senza sovrascrivere valori presenti. Restituisce le origini."""
    env = os.environ if env is None else env
    windows = (os.name == "nt") if windows is None else windows
    origini = {}
    for k, v in leggi_configurazione().items():
        if k not in env:
            env[k] = v
            origini[k] = "configurazione.json"
    if "SUCCESSIONI_FONTI" not in env and FONTI.is_dir() and (RADICE / "app").is_dir():
        env["SUCCESSIONI_FONTI"] = str(FONTI)
        origini["SUCCESSIONI_FONTI"] = "pacchetto"
    if windows:
        for k, v in candidati_windows(env).items():
            if k not in env:
                env[k] = v
                origini[k] = "rilevato"
    if str(SRC) not in sys.path:
        try:
            import successioni  # noqa: F401
        except ModuleNotFoundError:
            sys.path.insert(0, str(SRC))
    return origini


def cartella_dati() -> Path:
    from successioni.archivio import cartella_dati as cd
    return cd()


def proteggi_flussi(cartella_log: Path):
    """pythonw.exe: sys.stdout/sys.stderr valgono None. Li sostituisce con un file di log (max ~1 MB)."""
    if sys.stdout is not None and sys.stderr is not None:
        return None
    cartella_log.mkdir(parents=True, exist_ok=True)
    p = cartella_log / "avvio.log"
    if p.exists() and p.stat().st_size > 1_000_000:
        p.replace(p.with_suffix(".log.1"))
    f = open(p, "a", encoding="utf-8", buffering=1)
    if sys.stdout is None:
        sys.stdout = f
    if sys.stderr is None:
        sys.stderr = f
    return p


def porta_libera(porta: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", porta))
            return True
        except OSError:
            return False


def sessione_attiva(base: Path) -> dict | None:
    p = base / NOME_SESSIONE
    try:
        s = json.loads(p.read_text(encoding="utf-8"))
        url = f"http://127.0.0.1:{int(s['porta'])}/api/info?t={s['token']}"
        with urllib.request.urlopen(url, timeout=2) as r:
            if r.status == 200:
                return s
    except (OSError, ValueError, KeyError):
        pass
    return None


def avvia_gui(porta: int | None, apri_browser: bool) -> int:
    os.environ.setdefault("SUCCESSIONI_CONFIG", str(file_configurazione()))   # la schermata Impostazioni scrive qui
    base = cartella_dati()
    base.mkdir(parents=True, exist_ok=True)
    proteggi_flussi(base / "log")
    attiva = sessione_attiva(base)
    if attiva and porta in (None, attiva["porta"]):
        url = f"http://127.0.0.1:{attiva['porta']}/?t={attiva['token']}"
        print(f"Successioni e' gia' aperto: {url}")
        if apri_browser:
            import webbrowser
            webbrowser.open(url)
        return 0
    if porta is None:
        porta = next((p for p in PORTE if porta_libera(p)), None)
        if porta is None:
            print("Nessuna porta libera tra 8765 e 8785: chiudere altre copie di Successioni e riprovare.")
            return 2
    elif not porta_libera(porta):
        print(f"La porta {porta} e' occupata.")
        return 2
    import uvicorn
    from successioni.web import crea_app
    token = secrets.token_urlsafe(24)
    app = crea_app(token=token, porta=porta)
    url = f"http://127.0.0.1:{porta}/?t={token}"
    sess = base / NOME_SESSIONE
    sess.write_text(json.dumps({"porta": porta, "token": token, "pid": os.getpid(),
                                "avviata": time.strftime("%Y-%m-%dT%H:%M:%S")}), encoding="utf-8")
    print(f"Successioni: {url}")
    print(f"Archivio: {base}")
    print("Lasciare aperta questa finestra durante il lavoro; chiuderla termina il programma (i dati sono gia' salvati).")
    if apri_browser:
        import webbrowser
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        uvicorn.run(app, host="127.0.0.1", port=porta, log_level="warning", use_colors=False)
    finally:
        try:
            if json.loads(sess.read_text(encoding="utf-8")).get("pid") == os.getpid():
                sess.unlink()
        except (OSError, ValueError):
            pass
    return 0


def info(origini: dict) -> dict:
    from successioni import __version__
    out = {"versione": __version__, "radice_programma": str(RADICE), "codice": str(SRC),
           "python": sys.executable, "configurazione": str(file_configurazione()),
           "cartella_dati": str(cartella_dati()),
           "variabili": {k: os.environ.get(k) for k in VARIABILI_NOTE if os.environ.get(k)},
           "origine_variabili": origini}
    return out


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="avvia_successioni")
    sub = ap.add_subparsers(dest="cmd")
    g = sub.add_parser("gui")
    g.add_argument("--porta", type=int, default=None)
    g.add_argument("--no-browser", action="store_true")
    sub.add_parser("mcp")
    b = sub.add_parser("backup")
    b.add_argument("destinazione")
    sub.add_parser("info")
    a = ap.parse_args(argv)
    fissa_file_configurazione()
    origini = prepara_ambiente()
    cmd = a.cmd or "gui"
    if cmd == "mcp":
        from successioni.mcp_server import main as m
        m()
        return 0
    if cmd == "backup":
        from successioni.cli import main as cli
        return cli(["backup", a.destinazione]) or 0
    if cmd == "info":
        print(json.dumps(info(origini), indent=1, ensure_ascii=False))
        return 0
    return avvia_gui(getattr(a, "porta", None), not getattr(a, "no_browser", False))


if __name__ == "__main__":
    sys.exit(main())
