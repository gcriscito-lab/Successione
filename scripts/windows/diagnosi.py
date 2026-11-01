"""Diagnosi dei prerequisiti di Successioni sulla postazione (Windows; funziona anche su Linux per le prove).

    python\\python.exe -s app\\diagnosi.py                 rapporto leggibile + JSON nella cartella dati\\log
    python\\python.exe -s app\\diagnosi.py --json FILE     scrive il JSON anche in FILE
    python\\python.exe -s app\\diagnosi.py --salva-configurazione
                                       registra in configurazione.json i percorsi degli strumenti trovati

Solo lettura, salvo: file di prova temporanei nella cartella dati (rimossi), il rapporto in <dati>\\log e, se
richiesto, configurazione.json. Non legge credenziali; dei file di configurazione di Claude riporta solo se esiste
una voce "successioni". Esiti: ok | avviso | mancante | errore. Codice di uscita 1 se manca un requisito
indispensabile (programma, cartella dati, SQLite, fonti), altrimenti 0.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import avvia_successioni as A  # noqa: E402

INDISPENSABILI = {"python_dipendenze", "cartella_dati", "sqlite_wal", "percorsi_italiani", "fonti"}
CONSIGLIO_GS = ("Installare Ghostscript per Windows a 64 bit (installer gs#####w64.exe, "
                "https://ghostscript.readthedocs.io/en/latest/Install.html), poi rieseguire la diagnosi con "
                "--salva-configurazione oppure impostare SUCCESSIONI_GS con il percorso di gswin64c.exe")


def voce(nome, stato, dettaglio, rimedio=None, **extra) -> dict:
    return {"nome": nome, "stato": stato, "dettaglio": dettaglio, "rimedio": rimedio, **extra}


def esegui(cmd: list[str], timeout=30) -> tuple[int | None, str]:
    try:
        pr = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, errors="replace")
        return pr.returncode, ((pr.stdout or "") + (pr.stderr or "")).strip()
    except (OSError, subprocess.SubprocessError) as e:
        return None, f"{type(e).__name__}: {e}"


def controlla_dipendenze() -> dict:
    mancanti, versioni = [], {}
    for mod, dist in (("mcp", "mcp"), ("lxml", "lxml"), ("pypdf", "pypdf"), ("reportlab", "reportlab"),
                      ("PIL", "pillow"), ("starlette", "starlette"), ("uvicorn", "uvicorn")):
        try:
            __import__(mod)
            from importlib.metadata import version
            versioni[dist] = version(dist)
        except Exception as e:  # noqa: BLE001 - qualsiasi errore d'importazione e' un esito
            mancanti.append(f"{dist} ({type(e).__name__}: {e})")
    try:
        import successioni
        versioni["successioni"] = successioni.__version__
    except Exception as e:  # noqa: BLE001
        mancanti.append(f"successioni ({e})")
    if mancanti:
        return voce("python_dipendenze", "errore", f"moduli non importabili: {mancanti}",
                    "Pacchetto incompleto: reinstallare Successioni dallo zip originale.", versioni=versioni)
    return voce("python_dipendenze", "ok", f"Python {platform.python_version()} ({sys.executable})", versioni=versioni)


def controlla_cartella_dati(base: Path) -> list[dict]:
    out = []
    try:
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=base, prefix=".diagnosi-", delete=True) as f:
            f.write(b"ok")
        libero = shutil.disk_usage(base).free
        note = []
        s = str(base)
        if " " in s:
            note.append("contiene spazi")
        if any(ord(c) > 127 for c in s):
            note.append("contiene caratteri non ASCII")
        stato = "ok"
        rimedio = None
        if "onedrive" in s.lower() or s.startswith("\\\\") or s.lower().startswith("//"):
            stato = "avviso"
            rimedio = ("La cartella dati e' in rete o sincronizzata (OneDrive): SQLite in modalita' WAL richiede un "
                       "disco locale. Usare la cartella predefinita %LOCALAPPDATA%\\Successioni e fare i backup a parte.")
        if libero < 1_000_000_000:
            stato = "avviso"
            rimedio = (rimedio or "") + " Spazio libero inferiore a 1 GB."
        out.append(voce("cartella_dati", stato, f"{base} scrivibile; spazio libero {libero // 1_000_000} MB"
                        + (f"; {', '.join(note)}" if note else ""), rimedio, percorso=s))
    except OSError as e:
        out.append(voce("cartella_dati", "errore", f"{base}: {e}",
                        "Scegliere una cartella scrivibile impostando SUCCESSIONI_DATA in configurazione.json."))
        return out
    db = base / "archivio.sqlite3"
    if db.exists():
        try:
            c = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True, timeout=5)
            v = c.execute("PRAGMA user_version").fetchone()[0]
            n = c.execute("SELECT COUNT(*) FROM pratiche").fetchone()[0]
            c.close()
            out.append(voce("archivio", "ok", f"archivio presente: schema {v}, {n} pratiche"))
        except sqlite3.Error as e:
            out.append(voce("archivio", "errore", f"archivio non leggibile: {e}",
                            "Non cancellare nulla: conservare la cartella e ripristinare l'ultimo backup "
                            "(docs/MANUALE_BREVE.md, Backup e ripristino)."))
    else:
        out.append(voce("archivio", "ok", "archivio non ancora creato (verra' creato al primo avvio)"))
    return out


def controlla_sqlite_e_percorsi(base: Path) -> list[dict]:
    """WAL e percorsi con spazi/caratteri italiani in una sottocartella temporanea della cartella dati."""
    out = []
    try:
        with tempfile.TemporaryDirectory(dir=base, prefix=".diagnosi ") as t:
            d = Path(t) / "Pratica di prova è à ù ò"
            d.mkdir()
            f = d / "allegato con spazi è.txt"
            f.write_text("verifica àèìòù", encoding="utf-8")
            ok_file = f.read_text(encoding="utf-8") == "verifica àèìòù"
            c = sqlite3.connect(d / "prova è.sqlite3")
            modo = c.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            c.execute("CREATE TABLE t(x TEXT)")
            c.execute("INSERT INTO t VALUES ('àèìòù')")
            c.commit()
            letto = c.execute("SELECT x FROM t").fetchone()[0]
            c.close()
            out.append(voce("sqlite_wal", "ok" if modo == "wal" else "errore",
                            f"SQLite {sqlite3.sqlite_version}, journal_mode={modo}",
                            None if modo == "wal" else "Cartella dati su un disco che non supporta WAL: usare un disco locale."))
            out.append(voce("percorsi_italiani", "ok" if ok_file and letto == "àèìòù" else "errore",
                            f"cartella e file con spazi e lettere accentate: {'scrittura/lettura riuscite' if ok_file else 'errore'}"))
    except (OSError, sqlite3.Error) as e:
        out.append(voce("sqlite_wal", "errore", str(e), "Verificare permessi e tipo di disco della cartella dati."))
    return out


def controlla_fonti() -> dict:
    try:
        from successioni.telematico.fonti import radice_fonti, xsd_principale
        x = xsd_principale()
        if x.exists():
            return voce("fonti", "ok", f"XSD principale presente: {x}", radice=str(radice_fonti()))
        return voce("fonti", "errore", f"XSD non trovato: {x}",
                    "Reinstallare il pacchetto (cartella app\\fonti) o impostare SUCCESSIONI_FONTI.")
    except Exception as e:  # noqa: BLE001
        return voce("fonti", "errore", f"{type(e).__name__}: {e}")


def controlla_strumenti(windows: bool) -> list[dict]:
    out = []
    try:
        from successioni import pdfa
        gs = pdfa.trova_gs()
        icc = pdfa._icc()  # noqa: SLF001 - stessa ricerca usata dal programma
        vp = pdfa.trova_verapdf()
    except Exception as e:  # noqa: BLE001
        return [voce("strumenti_pdf", "errore", f"modulo pdfa non importabile: {e}")]
    cand = A.candidati_windows() if windows else {}
    if gs:
        rc, txt = esegui([gs, "--version"])
        out.append(voce("ghostscript", "ok" if rc == 0 else "errore", f"{gs} versione {txt[:40]}",
                        percorso=gs))
        if not icc:
            out.append(voce("profilo_icc", "avviso", "profilo sRGB non trovato: la conversione PDF/A non parte",
                            "Impostare SUCCESSIONI_ICC con il percorso di srgb.icc (cartella iccprofiles di Ghostscript)."))
    else:
        extra = f" Trovato ma non configurato: {cand['SUCCESSIONI_GS']}." if cand.get("SUCCESSIONI_GS") else ""
        out.append(voce("ghostscript", "mancante", "Ghostscript non trovato: la conversione PDF/A non e' disponibile."
                        + extra, CONSIGLIO_GS))
    if vp:
        rc, txt = esegui([vp, "--version"], timeout=90)
        out.append(voce("verapdf", "ok" if rc == 0 else "errore", f"{vp}: {txt[:80]}", percorso=vp))
    else:
        out.append(voce("verapdf", "avviso",
                        "veraPDF non trovato: i PDF/A risultano 'non verificato' (mai 'conforme').",
                        "Facoltativo ma consigliato: installare veraPDF (https://docs.verapdf.org/install/, componente "
                        "'veraPDF CLI', es. in C:\\veraPDF) e poi --salva-configurazione. Richiede Java."))
    try:
        from successioni.documenti.dimensioni import trova_qpdf
        q = trova_qpdf()
    except Exception:  # noqa: BLE001
        q = shutil.which("qpdf")
    out.append(voce("qpdf", "ok" if q else "avviso", q or "qpdf non trovato (facoltativo: la suddivisione usa pypdf)"))
    pt = shutil.which("pdftotext")
    out.append(voce("pdftotext", "ok" if pt else "avviso",
                    pt or "pdftotext non trovato (facoltativo: il confronto del testo usa pypdf)"))
    java = os.environ.get("SUCCESSIONI_JAVA") or shutil.which("java")
    if java:
        rc, txt = esegui([java, "-version"])
        righe = [r for r in txt.splitlines() if "version" in r.lower() and "JAVA_TOOL_OPTIONS" not in r]
        out.append(voce("java", "ok" if rc == 0 else "errore", f"{java}: {righe[0] if righe else txt[:80]}",
                        percorso=java))
    else:
        out.append(voce("java", "avviso", "Java non trovato: controllo ufficiale SUC13 solo come passaggio manuale; "
                        "veraPDF non utilizzabile.",
                        "Installare un Java Runtime a 64 bit e rieseguire la diagnosi con --salva-configurazione."))
    jar = os.environ.get("SUCCESSIONI_CONTROLLI_SUC13")
    if jar:
        n = len(list(Path(jar).glob("*.jar"))) if Path(jar).is_dir() else 0
        out.append(voce("controlli_suc13", "ok" if n else "avviso", f"{jar}: {n} file .jar"))
    else:
        out.append(voce("controlli_suc13", "avviso", "SUCCESSIONI_CONTROLLI_SUC13 non impostata",
                        "Vedi docs/COLLEGAMENTI.md par. 1 e docs/COLLAUDO_RIPRENDIBILE.md (componenti del controllo)."))
    return out


def controlla_porta() -> dict:
    libere = [p for p in A.PORTE if A.porta_libera(p)]
    if A.PORTA_PREDEFINITA in libere:
        return voce("porta_gui", "ok", "porta 8765 libera su 127.0.0.1")
    if libere:
        return voce("porta_gui", "avviso", f"porta 8765 occupata (forse Successioni e' gia' aperto); sara' usata {libere[0]}")
    return voce("porta_gui", "errore", "nessuna porta libera tra 8765 e 8785", "Chiudere le copie aperte del programma.")


def controlla_claude(windows: bool) -> list[dict]:
    out = []
    cand = []
    if windows and os.environ.get("APPDATA"):
        cand.append(("claude_desktop", Path(os.environ["APPDATA"]) / "Claude" / "claude_desktop_config.json"))
    cand.append(("claude_code", Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home()) / ".claude.json"))
    for nome, p in cand:
        if not p.exists():
            out.append(voce(nome, "avviso", f"{p} non presente",
                            "Vedi docs/CONFIGURAZIONE_MCP.md (Configura-MCP.cmd stampa la configurazione)."))
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as e:
            out.append(voce(nome, "errore", f"{p}: JSON non leggibile ({type(e).__name__})",
                            "Correggere il file (una virgola o una parentesi mancante impedisce l'avvio dei server)."))
            continue
        voci = set((d.get("mcpServers") or {}).keys())
        for prj in (d.get("projects") or {}).values():
            if isinstance(prj, dict):
                voci |= set((prj.get("mcpServers") or {}).keys())
        presente = "successioni" in voci
        out.append(voce(nome, "ok" if presente else "avviso",
                        f"{p}: voce 'successioni' {'presente' if presente else 'assente'}"))
    return out


def controlla_sistema(windows: bool) -> dict:
    info = {"sistema": platform.platform(), "macchina": platform.machine(), "python": platform.python_version()}
    wsl_dentro = False
    try:
        wsl_dentro = "microsoft" in Path("/proc/version").read_text().lower()
    except OSError:
        pass
    info["dentro_wsl"] = wsl_dentro
    info["wsl_exe"] = bool(windows and shutil.which("wsl"))
    stato, rimedio = "ok", None
    if wsl_dentro:
        stato = "avviso"
        rimedio = ("Questo processo gira dentro WSL: l'archivio di Windows NON e' quello che vede questo processo. "
                   "Usare il programma Windows (vedi docs/CONFIGURAZIONE_MCP.md, WSL).")
    if windows and platform.machine().upper() not in ("AMD64", "X86_64"):
        stato, rimedio = "avviso", "Il pacchetto e' per Windows x64."
    if windows:
        ucrt = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "ucrtbase.dll"
        info["ucrtbase"] = ucrt.exists()
        if not ucrt.exists():
            stato, rimedio = "errore", "Manca il Universal C Runtime (ucrtbase.dll): aggiornare Windows."
    return voce("sistema", stato, json.dumps(info, ensure_ascii=False), rimedio, **info)


def diagnosi(windows: bool | None = None) -> dict:
    windows = (os.name == "nt") if windows is None else windows
    origini = A.prepara_ambiente(windows=windows)
    voci = [controlla_sistema(windows), controlla_dipendenze()]
    base = A.cartella_dati()
    voci += controlla_cartella_dati(base)
    voci += controlla_sqlite_e_percorsi(base)
    voci.append(controlla_fonti())
    voci += controlla_strumenti(windows)
    voci.append(controlla_porta())
    voci += controlla_claude(windows)
    bloccanti = [v["nome"] for v in voci if v["nome"] in INDISPENSABILI and v["stato"] == "errore"]
    return {"data": time.strftime("%Y-%m-%dT%H:%M:%S"), "programma": str(A.RADICE), "cartella_dati": str(base),
            "origine_variabili": origini, "voci": voci, "bloccanti": bloccanti,
            "esito": "non_avviabile" if bloccanti else "avviabile"}


def salva_configurazione(rapporto: dict) -> Path:
    p = A.file_configurazione()
    try:
        attuale = json.loads(p.read_text(encoding="utf-8-sig"))
        if not isinstance(attuale, dict):
            attuale = {}
    except (OSError, ValueError):
        attuale = {}
    mappa = {"ghostscript": "SUCCESSIONI_GS", "verapdf": "SUCCESSIONI_VERAPDF", "java": "SUCCESSIONI_JAVA"}
    for v in rapporto["voci"]:
        k = mappa.get(v["nome"])
        if k and v["stato"] == "ok" and v.get("percorso"):
            attuale[k] = v["percorso"]
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(attuale, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)
    return p


def stampa(rapporto: dict):
    simboli = {"ok": "[OK]      ", "avviso": "[AVVISO]  ", "mancante": "[MANCANTE]", "errore": "[ERRORE]  "}
    print(f"Diagnosi Successioni - {rapporto['data']}")
    print(f"Programma: {rapporto['programma']}")
    print(f"Cartella dati: {rapporto['cartella_dati']}")
    for v in rapporto["voci"]:
        print(f"{simboli.get(v['stato'], v['stato'])} {v['nome']}: {v['dettaglio']}")
        if v.get("rimedio") and v["stato"] != "ok":
            print(f"            -> {v['rimedio']}")
    print("Esito:", "il programma si puo' avviare" if rapporto["esito"] == "avviabile"
          else f"mancano requisiti indispensabili: {', '.join(rapporto['bloccanti'])}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="diagnosi")
    ap.add_argument("--json", help="scrive anche il rapporto JSON in questo file")
    ap.add_argument("--salva-configurazione", action="store_true")
    ap.add_argument("--silenzioso", action="store_true", help="niente rapporto a video")
    a = ap.parse_args(argv)
    r = diagnosi()
    try:
        log = Path(r["cartella_dati"]) / "log"
        log.mkdir(parents=True, exist_ok=True)
        (log / f"diagnosi-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(
            json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    if a.json:
        Path(a.json).write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
    if a.salva_configurazione:
        print(f"Configurazione aggiornata: {salva_configurazione(r)}")
    if not a.silenzioso:
        stampa(r)
    return 1 if r["bloccanti"] else 0


if __name__ == "__main__":
    sys.exit(main())
