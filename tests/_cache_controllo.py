"""Cache dei risultati del controllo ufficiale SUC13 nei test (solo test: il programma non la usa mai).

Il componente Java dell'Agenzia (MSUC13 + VisualXml) costa 6-10 secondi per file e circa 280 test lo avviano, quasi
sempre sugli stessi XML. Qui le uscite del componente vengono conservate e riusate quando TUTTO cio' che le determina
e' identico:

- chiave = SHA-256 dell'XML (o del .dgn per il rapporto VisualXml) + impronta dei JAR del classpath (nome, dimensione,
  data di modifica) + versione di Java (``java -version``) + percorso di Java + opzioni della JVM + classe e forma degli
  argomenti (con o senza ``.dcm``) + versione del formato di questa cache;
- valore = ``.dgn``, ``_logSchema.xml``, ``.dcm`` (se prodotto), ``.wri`` (per VisualXml), stdout/stderr, codice di
  uscita, durata e destino della copia di lavoro (il componente puo' consumarla producendo il ``.dcm``).

Nel ripristino il nome del file (``in/<job>.xml``, presente nel .dgn e nel .wri) e' sostituito con quello della prova
corrente (stessa lunghezza: fa parte della chiave, cosi' i record a lunghezza fissa del .dgn restano allineati) e la
data del rapporto .wri («Data: G/M/AAAA») diventa quella di oggi, come in un'esecuzione reale.

Cartella: ``SUCCESSIONI_TEST_CACHE`` oppure ``%LOCALAPPDATA%\\Successioni-test-cache`` (fuori dal repository).
Disattivazione per la verifica completa prima di una consegna: ``SUCCESSIONI_TEST_SENZA_CACHE=1``.
Un'esecuzione che non produce il .dgn, scade o altera l'input non viene mai conservata; un test con un tempo massimo
inferiore alla durata registrata esegue sempre il componente reale.
"""
from __future__ import annotations

import functools
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import uuid
from datetime import date
from pathlib import Path
from typing import Callable

VERSIONE_FORMATO = "1"
CLASSE_CONTROLLO = "it.finanze.entrate.sco.main.MSUC13"
CLASSE_RAPPORTO = "it.finanze.entrate.sco.common2013.VisualXml"
ENV_SENZA_CACHE = "SUCCESSIONI_TEST_SENZA_CACHE"
ENV_CARTELLA = "SUCCESSIONI_TEST_CACHE"

statistiche = {"riusi": 0, "esecuzioni": 0, "conservate": 0}


def attiva() -> bool:
    return os.environ.get(ENV_SENZA_CACHE, "").strip().lower() not in ("1", "si", "sì", "true", "yes")


def cartella() -> Path:
    env = os.environ.get(ENV_CARTELLA)
    if env:
        return Path(env)
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".cache")
    return Path(base) / "Successioni-test-cache"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


@functools.lru_cache(maxsize=None)
def _versione_java(java: str) -> str:
    try:
        p = subprocess.run([java, "-version"], capture_output=True, timeout=60,
                           env={**os.environ, "JAVA_TOOL_OPTIONS": ""})
    except (OSError, subprocess.SubprocessError) as e:
        return f"non determinabile: {type(e).__name__}"
    righe = [r for r in (p.stderr + p.stdout).decode("utf-8", "replace").splitlines()
             if r.strip() and not r.startswith("Picked up")]
    return " | ".join(righe)


def _impronta_classpath(cp: str) -> list:
    voci = []
    for parte in cp.split(os.pathsep):
        if not parte:
            continue
        file = sorted(glob.glob(parte)) if "*" in parte else [parte]
        for f in file:
            try:
                st = os.stat(f)
                voci.append([os.path.basename(f), st.st_size, st.st_mtime_ns])
            except OSError:
                voci.append([os.path.basename(f), None, None])
    return sorted(voci)


def _scomponi(argv: list[str]) -> tuple[list[str], str, int] | None:
    """(opzioni JVM senza tmpdir/classpath, classpath, indice della classe) oppure None se non e' il componente."""
    for classe in (CLASSE_CONTROLLO, CLASSE_RAPPORTO):
        if classe in argv:
            i = argv.index(classe)
            break
    else:
        return None
    opzioni, cp, k = [], "", 1
    while k < i:
        a = argv[k]
        if a in ("-cp", "-classpath") and k + 1 < i:
            cp = argv[k + 1]
            k += 2
            continue
        if not a.startswith("-Djava.io.tmpdir="):
            opzioni.append(a)
        k += 1
    return opzioni, cp, i


def _nome(rel: str) -> str:
    return Path(rel).stem


def _sostituisci(b: bytes, vecchio: str, nuovo: str) -> bytes:
    return b if vecchio == nuovo else b.replace(vecchio.encode(), nuovo.encode())


def _data_odierna(wri: bytes) -> bytes:
    oggi = date.today()
    return re.sub(rb"(Data:\s*)\d{1,2}/\d{1,2}/\d{4}", rb"\g<1>" + f"{oggi.day}/{oggi.month}/{oggi.year}".encode(),
                  wri, count=1)


def _leggi_voce(chiave: str) -> tuple[Path, dict] | None:
    d = cartella() / "controllo" / f"v{VERSIONE_FORMATO}" / chiave
    try:
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return d, meta


def _scrivi_voce(chiave: str, meta: dict, file: dict[str, bytes]) -> None:
    radice = cartella() / "controllo" / f"v{VERSIONE_FORMATO}"
    tmp = radice / f".{chiave}.{uuid.uuid4().hex}"
    try:
        tmp.mkdir(parents=True)
        for n, b in file.items():
            (tmp / n).write_bytes(b)
        (tmp / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, radice / chiave)      # atomico: un altro processo vede la voce intera o non la vede
        statistiche["conservate"] += 1
    except OSError:                           # gia' scritta da un altro processo (xdist) o cartella non scrivibile
        pass
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def esegui(argv: list[str], cwd: Path, timeout: int, reale: Callable):
    """Come ``reale(argv, cwd, timeout)`` (che restituisce un ``Processo`` dell'adattatore), riusando le uscite gia'
    prodotte dal componente sullo stesso input. Comandi diversi dal componente passano direttamente a ``reale``."""
    from successioni.collegamenti.controllo import Processo
    sc = _scomponi(argv) if attiva() else None
    if sc is None:
        return reale(argv, cwd, timeout)
    opzioni, cp, i = sc
    cwd = Path(cwd)
    classe = argv[i]
    argomenti = argv[i + 1:]
    if classe == CLASSE_CONTROLLO:
        if len(argomenti) not in (2, 3):
            return reale(argv, cwd, timeout)
        sorgente = cwd / argomenti[0]
        nome = _nome(argomenti[0])
        uscite = {"dgn": f"{_nome(argomenti[1])}.dgn", "log": f"{_nome(argomenti[1])}_logSchema.xml"}
        if len(argomenti) == 3:
            uscite["dcm"] = Path(argomenti[2]).name
        cartella_out = cwd / Path(argomenti[1]).parent
    else:
        if len(argomenti) != 2:
            return reale(argv, cwd, timeout)
        sorgente = cwd / argomenti[0]
        nome = _nome(argomenti[0])
        uscite = {"wri": f"{nome}.wri"}
        cartella_out = sorgente.parent
    try:
        dati = sorgente.read_bytes()
    except OSError:
        return reale(argv, cwd, timeout)
    # Nomi lunghi (job dell'adattatore: prefisso + 24 cifre esadecimali) sono unici e si sostituiscono senza rischio;
    # un nome corto (``F`` dell'helper dei test) potrebbe comparire in altri testi: resta letterale nella chiave.
    segnaposto = "#" * len(nome) if len(nome) >= 12 else nome
    forma = [a.replace(nome, segnaposto) for a in argomenti]
    contenuto = dati if classe == CLASSE_CONTROLLO else _sostituisci(dati, nome, segnaposto)
    materiale = {"formato": VERSIONE_FORMATO, "java": argv[0], "versione_java": _versione_java(argv[0]),
                 "classpath": _impronta_classpath(cp), "opzioni": opzioni, "classe": classe, "argomenti": forma,
                 "input_sha256": _sha(contenuto)}
    chiave = _sha(json.dumps(materiale, sort_keys=True).encode())
    voce = _leggi_voce(chiave)
    if voce is not None and timeout >= voce[1].get("durata_s", 0):
        d, meta = voce
        cartella_out.mkdir(parents=True, exist_ok=True)
        for ruolo, n in uscite.items():
            if ruolo in meta["file"]:
                b = _sostituisci((d / meta["file"][ruolo]).read_bytes(), segnaposto, nome)
                (cartella_out / n).write_bytes(_data_odierna(b) if ruolo == "wri" else b)
        if meta.get("input_consumato"):
            sorgente.unlink(missing_ok=True)
        statistiche["riusi"] += 1
        return Processo(meta["codice_uscita"], _sostituisci(bytes.fromhex(meta["stdout"]), segnaposto, nome),
                        _sostituisci(bytes.fromhex(meta["stderr"]), segnaposto, nome), meta["durata_s"])
    p = reale(argv, cwd, timeout)
    statistiche["esecuzioni"] += 1
    prodotte = {r: cartella_out / n for r, n in uscite.items() if (cartella_out / n).is_file()}
    dopo = sorgente.read_bytes() if sorgente.exists() else None
    if p.scaduto or p.codice_uscita is None or (dopo is not None and dopo != dati):
        return p
    if classe == CLASSE_CONTROLLO and "dgn" not in prodotte or classe == CLASSE_RAPPORTO and "wri" not in prodotte:
        return p
    file = {f"{r}.bin": _sostituisci(pp.read_bytes(), nome, segnaposto) for r, pp in prodotte.items()}
    meta = {"materiale": materiale, "file": {r: f"{r}.bin" for r in prodotte}, "codice_uscita": p.codice_uscita,
            "durata_s": p.durata_s, "input_consumato": dopo is None,
            "stdout": _sostituisci(p.stdout, nome, segnaposto).hex(),
            "stderr": _sostituisci(p.stderr, nome, segnaposto).hex()}
    _scrivi_voce(chiave, meta, file)
    return p
