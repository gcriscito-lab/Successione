"""Pulizia dei file temporanei e di lavoro lasciati nella cartella dei dati.

Elimina SOLO, e solo se piu' vecchi dell'eta' indicata:
- le cartelle di lavoro dei controlli ufficiali (``lavoro/controlli/<job>-<id>``) e i relativi lock (``lavoro/lock/*.lock``);
- i file ``*.tmp`` lasciati da scritture interrotte sotto ``elaborati/`` e ``allegati/``.

Non tocca mai database, allegati ed elaborati definitivi, backup, configurazione. Ogni percorso viene risolto e deve restare dentro la
cartella dei dati; i collegamenti simbolici non si seguono ne' si eliminano. Un lock posseduto da un altro processo (controllo in
esecuzione) e la cartella di lavoro del suo job si saltano. Gli errori su singoli file (in uso su Windows) si ignorano.
"""
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from .blocchi import blocco_file


def _interno(base: Path, p: Path) -> bool:
    try:
        return p.resolve().is_relative_to(base)
    except OSError:
        return False


def _ultima_modifica(p: Path) -> float:
    """Istante della modifica piu' recente nell'albero (senza seguire collegamenti simbolici)."""
    try:
        massimo = p.lstat().st_mtime
    except OSError:
        return time.time()
    if p.is_dir() and not p.is_symlink():
        for radice, cartelle, files in os.walk(p, followlinks=False):
            cartelle[:] = [d for d in cartelle if not (Path(radice) / d).is_symlink()]
            for n in cartelle + files:
                try:
                    massimo = max(massimo, (Path(radice) / n).lstat().st_mtime)
                except OSError:
                    pass
    return massimo


def _dimensione(p: Path) -> int:
    if p.is_symlink():
        return 0
    if p.is_file():
        try:
            return p.stat().st_size
        except OSError:
            return 0
    totale = 0
    for radice, _c, files in os.walk(p, followlinks=False):
        _c[:] = [d for d in _c if not (Path(radice) / d).is_symlink()]
        for n in files:
            f = Path(radice) / n
            try:
                if not f.is_symlink():
                    totale += f.stat().st_size
            except OSError:
                pass
    return totale


def _lock_libero(lock: Path) -> bool:
    """Vero se nessun processo possiede il lock (o se il lock non esiste)."""
    if not lock.exists():
        return True
    try:
        with blocco_file(lock) as acquisito:
            return bool(acquisito)
    except OSError:
        return False


def _elimina(base: Path, p: Path, conto: dict) -> None:
    if p.is_symlink() or not _interno(base, p):
        return
    try:
        byte = _dimensione(p)
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
    except OSError:
        return      # file in uso o gia' sparito: si riprova alla prossima pulizia
    if not p.exists():
        conto["eliminati"] += 1
        conto["byte_liberati"] += byte


def pulisci(base: Path, eta_ore: float | None = None, *, forzata: bool = False) -> dict:
    """Pulizia dei temporanei sotto ``base``. ``forzata`` ignora la preferenza ``pulizia_automatica``."""
    from . import impostazioni
    base = Path(base).resolve()
    pref = impostazioni.preferenze(base)
    if not forzata and not pref["pulizia_automatica"]:
        return {"eliminati": 0, "byte_liberati": 0, "eseguita": False, "motivo": "pulizia automatica disattivata"}
    if not base.is_dir():
        return {"eliminati": 0, "byte_liberati": 0, "eseguita": False, "motivo": "cartella dei dati non trovata"}
    limite = time.time() - 3600 * (pref["pulizia_ore"] if eta_ore is None else eta_ore)
    conto = {"eliminati": 0, "byte_liberati": 0}

    controlli = base / "lavoro" / "controlli"
    if controlli.is_dir() and not controlli.is_symlink() and _interno(base, controlli):
        for d in sorted(controlli.iterdir()):
            if d.is_symlink() or _ultima_modifica(d) >= limite:
                continue
            job = d.name.rsplit("-", 1)[0]          # <job_id>-<12 esadecimali>
            if not _lock_libero(base / "lavoro" / "lock" / (job + ".lock")):
                continue                              # controllo ancora in esecuzione
            _elimina(base, d, conto)

    locks = base / "lavoro" / "lock"
    if locks.is_dir() and not locks.is_symlink() and _interno(base, locks):
        for f in sorted(locks.glob("*.lock")):
            if f.is_symlink() or not f.is_file():
                continue
            try:
                if f.lstat().st_mtime >= limite or not _lock_libero(f):
                    continue
            except OSError:
                continue
            _elimina(base, f, conto)

    for sotto in ("elaborati", "allegati"):
        radice = base / sotto
        if not radice.is_dir() or radice.is_symlink() or not _interno(base, radice):
            continue
        for cartella, _dirs, files in os.walk(radice, followlinks=False):
            # non si scende in collegamenti simbolici, giunzioni di Windows o cartelle che escono da base
            _dirs[:] = [d for d in _dirs if not (Path(cartella) / d).is_symlink() and _interno(base, Path(cartella) / d)]
            for n in files:
                if not n.endswith(".tmp"):
                    continue
                f = Path(cartella) / n
                try:
                    if f.is_symlink() or f.lstat().st_mtime >= limite:
                        continue
                except OSError:
                    continue
                _elimina(base, f, conto)
    return {**conto, "eseguita": True, "motivo": None}


def pulisci_silenziosa(base: Path) -> dict | None:
    """Pulizia automatica che non solleva mai: usata dopo controlli/stampe e all'avvio del server."""
    try:
        return pulisci(base)
    except Exception:       # la pulizia non deve mai far fallire un'operazione
        return None
