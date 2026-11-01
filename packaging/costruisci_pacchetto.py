"""Costruisce il pacchetto Windows di Successioni (Python embeddable + wheel offline + codice + fonti).

Funziona su Linux e su Windows: il pacchetto e' una cartella "portabile" e uno zip, senza installer di sistema.
Nessuna dipendenza oltre alla libreria standard e a pip. Uso tipico (dalla radice del repository):

    python packaging/costruisci_pacchetto.py                    # usa packaging/requisiti-win64.lock
    python packaging/costruisci_pacchetto.py --aggiorna-lock    # risolve di nuovo le wheel e riscrive il lock
    python packaging/costruisci_pacchetto.py --verifica dist/Successioni-0.1.0-win64

Le prove sul pacchetto prodotto in Linux verificano contenuto e coerenza, NON l'avvio su Windows (da collaudare).
"""
from __future__ import annotations

import argparse
import email.parser
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
QUI = Path(__file__).resolve().parent
VERSIONI = QUI / "versioni.json"
LOCK = QUI / "requisiti-win64.lock"
WIN = RADICE / "scripts" / "windows"

#: script Python dell'avviatore, copiati in <pacchetto>/app
SCRIPT_APP = ("avvia_successioni.py", "diagnosi.py", "configura_mcp.py", "verifica_backup.py")
#: file per l'utente nella radice del pacchetto (convertiti in CRLF, solo ASCII)
FILE_RADICE = ("Successioni.cmd", "Diagnosi.cmd", "Configura-MCP.cmd", "Verifica-backup.cmd", "Installa.cmd", "installa.ps1",
               "Disinstalla.cmd", "disinstalla.ps1", "LEGGIMI.txt")
DOCUMENTI = ("INSTALLAZIONE_WINDOWS.md", "MANUALE_BREVE.md", "CONFIGURAZIONE_MCP.md")
#: moduli che devono esistere nel pacchetto (import di primo livello del programma)
MODULI_ATTESI = ("mcp", "lxml", "pypdf", "reportlab", "PIL", "starlette", "uvicorn", "pydantic", "pydantic_core",
                 "anyio", "win32api")
IGNORA = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", "*.egg-info")


# --------------------------------------------------------------------------------------------- utilita'
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def versione_progetto() -> str:
    testo = (RADICE / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', testo, re.M)
    return m.group(1) if m else "0.0.0"


def dipendenze_progetto() -> list[str]:
    """Dipendenze dichiarate in pyproject.toml ([project].dependencies)."""
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
        raise SystemExit("serve Python >= 3.11 per leggere pyproject.toml")
    with open(RADICE / "pyproject.toml", "rb") as f:
        return list(tomllib.load(f)["project"]["dependencies"])


def stato_git() -> dict:
    try:
        rev = subprocess.run(["git", "-C", str(RADICE), "rev-parse", "HEAD"], capture_output=True, text=True,
                             timeout=30).stdout.strip()
        sporco = subprocess.run(["git", "-C", str(RADICE), "status", "--porcelain"], capture_output=True, text=True,
                                timeout=30).stdout.strip()
        return {"commit": rev or None, "modifiche_non_registrate": bool(sporco)}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "modifiche_non_registrate": None}


def _marker_cls():
    try:
        from packaging.markers import Marker
        from packaging.requirements import Requirement
    except ModuleNotFoundError:  # pip contiene una copia di packaging
        from pip._vendor.packaging.markers import Marker  # type: ignore
        from pip._vendor.packaging.requirements import Requirement  # type: ignore
    return Marker, Requirement


def normalizza(nome: str) -> str:
    return re.sub(r"[-_.]+", "-", nome).lower()


def metadati_wheel(whl: Path) -> tuple[str, str, list[str]]:
    """(nome, versione, Requires-Dist) letti dal METADATA della wheel."""
    with zipfile.ZipFile(whl) as z:
        nome_meta = next(n for n in z.namelist() if n.endswith(".dist-info/METADATA"))
        msg = email.parser.Parser().parsestr(z.read(nome_meta).decode("utf-8"))
    return msg["Name"], msg["Version"], msg.get_all("Requires-Dist") or []


def chiusura_windows(wheels: list[Path], radici: list[str], ambiente: dict) -> tuple[dict, set[str]]:
    """Valuta i marcatori come su Windows (pip li valuta sulla macchina che scarica, non sulla destinazione).

    Restituisce (wheel per nome normalizzato, nomi richiesti ma assenti tra le wheel)."""
    Marker, Requirement = _marker_cls()
    per_nome = {}
    for w in wheels:
        n, v, req = metadati_wheel(w)
        per_nome[normalizza(n)] = {"nome": n, "versione": v, "requisiti": req, "file": w}
    richiesti, mancanti, coda = set(), set(), [Requirement(r) for r in radici]
    while coda:
        r = coda.pop()
        env = dict(ambiente)
        if r.marker is not None and not r.marker.evaluate(env):
            continue
        n = normalizza(r.name)
        if n in richiesti:
            continue
        richiesti.add(n)
        if n not in per_nome:
            mancanti.add(r.name)
            continue
        if per_nome[n]["versione"] not in r.specifier and str(r.specifier):
            mancanti.add(f"{r.name}{r.specifier} (presente {per_nome[n]['versione']})")
        for sub in per_nome[n]["requisiti"]:
            sr = Requirement(sub)
            # gli extra non richiesti esplicitamente non si installano
            if sr.marker is not None and "extra" in str(sr.marker):
                estr = {e for rr in [r] for e in rr.extras}
                if not any(sr.marker.evaluate({**env, "extra": e}) for e in estr):
                    continue
                sr.marker = None
            coda.append(sr)
    return {k: v for k, v in per_nome.items() if k in richiesti}, mancanti


# ------------------------------------------------------------------------------------- download e lock
def scarica(url: str, dest: Path, sha_atteso: str | None) -> Path:
    if dest.exists() and sha_atteso and sha256_file(dest) == sha_atteso:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f)
    h = sha256_file(tmp)
    if sha_atteso and h != sha_atteso:
        tmp.unlink()
        raise SystemExit(f"impronta diversa per {url}: {h} invece di {sha_atteso}")
    tmp.replace(dest)
    return dest


def _pip_piattaforma(cfg: dict) -> list[str]:
    p = cfg["piattaforma_wheel"]
    return ["--only-binary=:all:", "--platform", p["platform"], "--python-version", p["python_version"],
            "--implementation", p["implementation"], "--abi", p["abi"]]


def aggiorna_lock(cfg: dict, cache_wheel: Path, lock: Path = LOCK) -> dict:
    """Risolve le dipendenze per Windows e scrive il lock con versioni e SHA-256 delle wheel."""
    cache_wheel.mkdir(parents=True, exist_ok=True)
    radici = dipendenze_progetto()
    cmd = [sys.executable, "-m", "pip", "download", "--dest", str(cache_wheel), *_pip_piattaforma(cfg), *radici]
    subprocess.run(cmd, check=True)
    for _ in range(5):   # completa con le dipendenze condizionate a Windows (es. pywin32 di mcp)
        scelte, mancanti = chiusura_windows(sorted(cache_wheel.glob("*.whl")), radici, cfg["ambiente_marcatori_windows"])
        if not mancanti:
            break
        nomi = [re.split(r"[ <>=!~(]", m)[0] for m in mancanti]
        subprocess.run([sys.executable, "-m", "pip", "download", "--dest", str(cache_wheel), *_pip_piattaforma(cfg),
                        *nomi], check=True)
    else:
        raise SystemExit(f"dipendenze non risolte per Windows: {sorted(mancanti)}")
    righe = ["# Wheel per Windows x64 / CPython 3.13: generato da packaging/costruisci_pacchetto.py --aggiorna-lock",
             f"# {time.strftime('%Y-%m-%d')}; dipendenze radice da pyproject.toml: {', '.join(radici)}",
             "# Marcatori valutati per Windows (packaging/versioni.json, ambiente_marcatori_windows)."]
    for k in sorted(scelte):
        s = scelte[k]
        righe.append(f"{s['nome']}=={s['versione']} --hash=sha256:{sha256_file(s['file'])}")
    lock.write_text("\n".join(righe) + "\n", encoding="utf-8")
    return scelte


def leggi_lock(lock: Path = LOCK) -> list[dict]:
    out = []
    for riga in lock.read_text(encoding="utf-8").splitlines():
        riga = riga.strip()
        if not riga or riga.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z0-9_.\-]+)==([^\s]+)\s+--hash=sha256:([0-9a-f]{64})$", riga)
        if not m:
            raise SystemExit(f"riga del lock non valida: {riga}")
        out.append({"nome": m.group(1), "versione": m.group(2), "sha256": m.group(3)})
    return out


def scarica_wheel_lock(cfg: dict, cache_wheel: Path, lock: Path = LOCK):
    subprocess.run([sys.executable, "-m", "pip", "download", "--dest", str(cache_wheel), "--no-deps",
                    "--require-hashes", *_pip_piattaforma(cfg), "-r", str(lock)], check=True)


# ---------------------------------------------------------------------------------------- assemblaggio
def _crlf_ascii(src: Path, dst: Path):
    testo = src.read_text(encoding="utf-8")
    if any(ord(c) > 127 for c in testo):
        raise SystemExit(f"{src.name}: solo caratteri ASCII nei file .cmd/.ps1/.txt per Windows")
    dst.write_bytes(testo.replace("\r\n", "\n").replace("\n", "\r\n").encode("ascii"))


def scrivi_pth(cartella_python: Path, nome_pth: str):
    """sys.path del Python incorporato: libreria standard, site-packages del pacchetto e codice del programma."""
    righe = ["python313.zip", ".", r"Lib\site-packages", r"..\app\src",
             "# site attivo: elabora i .pth delle dipendenze (es. pywin32)", "import site", ""]
    (cartella_python / nome_pth).write_bytes("\r\n".join(righe).encode("ascii"))


def assembla(uscita: Path, embed_zip: Path, cfg: dict, cache_wheel: Path | None, lock: Path | None,
             con_wheel: bool = True) -> dict:
    if uscita.exists():
        shutil.rmtree(uscita)
    py = uscita / "python"
    py.mkdir(parents=True)
    with zipfile.ZipFile(embed_zip) as z:
        z.extractall(py)
    scrivi_pth(py, cfg["python"]["pth"])
    sp = py / "Lib" / "site-packages"
    sp.mkdir(parents=True, exist_ok=True)
    pacchetti = leggi_lock(lock) if (lock and con_wheel) else []
    if con_wheel and pacchetti:
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-index", "--find-links", str(cache_wheel),
                        "--target", str(sp), "--no-deps", "--no-compile", *_pip_piattaforma(cfg), "-r", str(lock)],
                       check=True)
        for estraneo in ("bin",):   # script generati per la macchina che costruisce, inutili su Windows
            if (sp / estraneo).exists():
                shutil.rmtree(sp / estraneo)
    app = uscita / "app"
    shutil.copytree(RADICE / "src" / "successioni", app / "src" / "successioni", ignore=IGNORA)
    shutil.copytree(RADICE / "fonti", app / "fonti")
    for n in SCRIPT_APP:
        shutil.copy2(WIN / n, app / n)
    for n in FILE_RADICE:
        _crlf_ascii(WIN / n, uscita / n)
    (uscita / "docs").mkdir()
    for n in DOCUMENTI:
        if (RADICE / "docs" / n).exists():
            shutil.copy2(RADICE / "docs" / n, uscita / "docs" / n)
    manifest = {
        "prodotto": "Successioni", "versione": versione_progetto(), "costruito": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "costruito_su": sys.platform, "git": stato_git(),
        "python": {k: cfg["python"][k] for k in ("versione", "url", "sha256")},
        "wheel": pacchetti,
        "avvertenza": "pacchetto costruito e verificato nel contenuto; avvio su Windows da collaudare (A01)",
    }
    file_elenco = []
    for p in sorted(uscita.rglob("*")):
        if p.is_file():
            file_elenco.append({"percorso": p.relative_to(uscita).as_posix(), "bytes": p.stat().st_size,
                                "sha256": sha256_file(p)})
    manifest["file"] = file_elenco
    manifest["bytes_totali"] = sum(f["bytes"] for f in file_elenco)
    (uscita / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    return manifest


def comprimi(cartella: Path) -> Path:
    dest = cartella.parent / (cartella.name + ".zip")
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(cartella.rglob("*")):
            if p.is_file():
                z.write(p, Path(cartella.name) / p.relative_to(cartella))
    return dest


# -------------------------------------------------------------------------------------------- verifica
def verifica(cartella: Path, con_wheel: bool = True) -> list[str]:
    """Controlli statici sul pacchetto: struttura, impronte, binari solo Windows, moduli, fonti invariate."""
    problemi = []
    man_p = cartella / "MANIFEST.json"
    if not man_p.exists():
        return ["MANIFEST.json assente"]
    man = json.loads(man_p.read_text(encoding="utf-8"))
    for f in man["file"]:
        p = cartella / f["percorso"]
        if not p.exists():
            problemi.append(f"file mancante: {f['percorso']}")
        elif sha256_file(p) != f["sha256"]:
            problemi.append(f"impronta diversa: {f['percorso']}")
    py = cartella / "python"
    for n in ("python.exe", "pythonw.exe", "python313.dll", "python313.zip", "python313._pth", "_sqlite3.pyd",
              "sqlite3.dll", "vcruntime140.dll"):
        if not (py / n).exists():
            problemi.append(f"python incorporato incompleto: manca {n}")
    pth = (py / "python313._pth").read_bytes().decode("ascii", "replace") if (py / "python313._pth").exists() else ""
    for riga in (r"Lib\site-packages", r"..\app\src", "import site"):
        if riga not in pth.splitlines() and riga not in pth.replace("\r", "").split("\n"):
            problemi.append(f"python313._pth senza la riga {riga!r}")
    sp = py / "Lib" / "site-packages"
    estranei = [p.relative_to(cartella).as_posix() for p in sp.rglob("*.so")] + \
               [p.relative_to(cartella).as_posix() for p in sp.rglob("*.so.*")]
    if estranei:
        problemi.append(f"binari non Windows nel pacchetto: {estranei[:5]}")
    pyd = [p.name for p in sp.rglob("*.pyd")]
    if con_wheel:
        if any("cp313-win_amd64" not in n and not re.match(r"^[A-Za-z0-9_]+\.pyd$", n) for n in pyd):
            problemi.append("estensioni .pyd non per cp313-win_amd64")
        for m in MODULI_ATTESI:
            if not ((sp / m).is_dir() or (sp / f"{m}.py").exists() or any(sp.glob(f"{m}.*.pyd"))
                    or any(sp.glob(f"win32/{m}*.pyd"))):
                problemi.append(f"modulo assente nel pacchetto: {m}")
        installati = {normalizza(d.name.split("-")[0]) for d in sp.glob("*.dist-info")}
        for w in man.get("wheel", []):
            if normalizza(w["nome"]) not in installati:
                problemi.append(f"wheel del lock non installata: {w['nome']}")
    app = cartella / "app"
    for n in ("src/successioni/cli.py", "src/successioni/mcp_server.py", "src/successioni/static/index.html",
              "src/successioni/static/app.js", "src/successioni/static/app.css", *SCRIPT_APP):
        if not (app / n).exists():
            problemi.append(f"programma incompleto: manca app/{n}")
    manifest_fonti = RADICE / "fonti" / "manifest.json"
    if manifest_fonti.exists() and (app / "fonti").exists():
        mf = json.loads(manifest_fonti.read_text(encoding="utf-8"))
        voci = mf.get("files") or mf.get("file") or []
        for v in voci if isinstance(voci, list) else []:
            rel, h = v.get("path") or v.get("percorso"), v.get("sha256")
            if rel and h:
                p = app / rel if rel.startswith("fonti/") else app / "fonti" / rel
                if not p.exists() or sha256_file(p) != h:
                    problemi.append(f"fonte mancante o alterata nel pacchetto: {rel}")
    for n in FILE_RADICE:
        p = cartella / n
        if not p.exists():
            problemi.append(f"manca {n}")
            continue
        b = p.read_bytes()
        if b"\n" in b.replace(b"\r\n", b""):
            problemi.append(f"{n}: righe non CRLF")
    return problemi


# ------------------------------------------------------------------------------------------------ main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--uscita", default=str(RADICE / "dist"), help="cartella di destinazione (predefinita: dist/)")
    ap.add_argument("--cache", default=str(RADICE / "build" / "cache-pacchetto"),
                    help="cache dei download (predefinita: build/cache-pacchetto, esclusa da git)")
    ap.add_argument("--embed-zip", help="zip del Python embeddable gia' scaricato (impronta verificata)")
    ap.add_argument("--lock", default=str(LOCK))
    ap.add_argument("--aggiorna-lock", action="store_true", help="risolve di nuovo le wheel e riscrive il lock")
    ap.add_argument("--senza-wheel", action="store_true", help="solo struttura (prove offline del montaggio)")
    ap.add_argument("--senza-zip", action="store_true")
    ap.add_argument("--verifica", metavar="CARTELLA", help="verifica un pacchetto gia' costruito ed esce")
    a = ap.parse_args(argv)
    if a.verifica:
        problemi = verifica(Path(a.verifica), con_wheel=not a.senza_wheel)
        print(json.dumps({"cartella": a.verifica, "problemi": problemi}, indent=1, ensure_ascii=False))
        return 1 if problemi else 0
    cfg = json.loads(VERSIONI.read_text(encoding="utf-8"))
    cache = Path(a.cache)
    cache_wheel = cache / "wheel"
    if a.embed_zip:
        embed = Path(a.embed_zip)
        if sha256_file(embed) != cfg["python"]["sha256"] and not a.senza_wheel:
            raise SystemExit("lo zip indicato non ha l'impronta attesa (packaging/versioni.json)")
    else:
        embed = scarica(cfg["python"]["url"], cache / Path(cfg["python"]["url"]).name, cfg["python"]["sha256"])
    lock = Path(a.lock)
    if not a.senza_wheel:
        if a.aggiorna_lock or not lock.exists():
            aggiorna_lock(cfg, cache_wheel, lock)
        scarica_wheel_lock(cfg, cache_wheel, lock)
    nome = f"Successioni-{versione_progetto()}-win64"
    uscita = Path(a.uscita) / nome
    man = assembla(uscita, embed, cfg, cache_wheel, lock, con_wheel=not a.senza_wheel)
    problemi = verifica(uscita, con_wheel=not a.senza_wheel)
    zip_p = None if a.senza_zip else comprimi(uscita)
    print(json.dumps({"cartella": str(uscita), "zip": str(zip_p) if zip_p else None,
                      "bytes_cartella": man["bytes_totali"], "bytes_zip": zip_p.stat().st_size if zip_p else None,
                      "wheel": [f"{w['nome']}=={w['versione']}" for w in man["wheel"]], "problemi": problemi},
                     indent=1, ensure_ascii=False))
    return 1 if problemi else 0


if __name__ == "__main__":
    sys.exit(main())
