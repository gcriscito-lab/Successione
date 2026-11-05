"""Backup dell'archivio (database, allegati, elaborati) con verifica di integrita' e potatura delle copie automatiche.

Cartella dei backup: ``SUCCESSIONI_BACKUP`` se impostata, altrimenti ``<cartella dati>/../Successioni-backup/<nome cartella dati>``.
Per proteggersi da un guasto del disco la cartella va impostata su un'altra unita' (impostazioni). Ogni copia e' una cartella
``AAAAMMGG-HHMMSS-<motivo>`` ripristinabile con ``successioni ripristina``; dopo la copia se ne verifica l'integrita'
(``integrita.verifica_copia``): una copia che non passa la verifica viene scartata e l'operazione fallisce.
"""
from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path

from .archivio import SCHEMA_VERSIONE, Archivio
from .errori import DatiNonValidi
from .integrita import verifica_copia

ENV_BACKUP = "SUCCESSIONI_BACKUP"
MAX_AUTOMATICI = 10
ETA_MINIMA_AUTOMATICO_S = 30 * 60


def cartella_backup(arch: Archivio) -> Path:
    env = os.environ.get(ENV_BACKUP)
    if env:
        return Path(env)
    return arch.base.resolve().parent / "Successioni-backup" / arch.base.resolve().name


def _dimensione(p: Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def elenco(arch: Archivio) -> list[dict]:
    radice = cartella_backup(arch)
    if not radice.is_dir():
        return []
    out = []
    for d in sorted((x for x in radice.iterdir() if x.is_dir() and (x / "archivio.sqlite3").is_file()), reverse=True):
        parti = d.name.split("-", 2)
        out.append({"nome": d.name, "percorso": str(d), "automatico": len(parti) > 2 and parti[2].startswith("auto"),
                    "creato": datetime.fromtimestamp(d.stat().st_mtime).isoformat(timespec="seconds"), "byte": _dimensione(d)})
    return out


def crea(arch: Archivio, motivo: str = "manuale", *, automatico: bool = False) -> dict:
    """Crea e verifica una copia. ``DatiNonValidi`` se non riesce (la copia parziale viene rimossa)."""
    etichetta = ("auto-" if automatico else "") + "".join(c for c in motivo if c.isalnum() or c in "-_")[:30]
    nome = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + (etichetta or "manuale")
    dest = cartella_backup(arch) / nome
    if dest.exists():
        raise DatiNonValidi("backup gia' esistente con lo stesso nome: riprova fra un secondo", percorso=str(dest))
    try:
        arch.backup(dest)
        verifica_copia(dest, SCHEMA_VERSIONE)
    except Exception as e:
        shutil.rmtree(dest, ignore_errors=True)
        raise DatiNonValidi(f"backup non riuscito: {e}", percorso=str(dest)) from None
    if automatico:
        _pota(arch)
    return {"nome": nome, "percorso": str(dest), "byte": _dimensione(dest), "verificato": True, "automatico": automatico}


def _pota(arch: Archivio) -> None:
    auto = [b for b in elenco(arch) if b["automatico"]]
    for vecchio in auto[MAX_AUTOMATICI:]:
        shutil.rmtree(vecchio["percorso"], ignore_errors=True)


def automatico_se_serve(arch: Archivio, motivo: str) -> dict:
    """Backup automatico, al massimo uno ogni 30 minuti. Non solleva: l'esito (anche l'errore) si restituisce."""
    try:
        recenti = [b for b in elenco(arch) if b["automatico"]]
        if recenti:
            ultimo = datetime.fromisoformat(recenti[0]["creato"])
            if (datetime.now() - ultimo).total_seconds() < ETA_MINIMA_AUTOMATICO_S:
                return {"eseguito": False, "motivo": "backup automatico recente", "ultimo": recenti[0]["nome"]}
        return {"eseguito": True, **crea(arch, motivo, automatico=True)}
    except Exception as e:  # il backup non deve bloccare il lavoro, ma l'esito va mostrato
        return {"eseguito": False, "errore": str(e)}
