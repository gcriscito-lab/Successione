"""Versioni registrate con ogni esportazione, per ricostruire con quali regole e specifiche e' stato prodotto un file."""
from __future__ import annotations

from . import __version__

# Aggiornare a ogni modifica delle regole fiscali o del tracciato; la data e' quella dell'ultima modifica verificata.
VERSIONE_REGOLE = "2026-11-05"


def versioni() -> dict:
    from .telematico import fonti as FO
    return {"applicazione": __version__, "regole": VERSIONE_REGOLE, "specifiche_suc": FO.VERSIONE_SPECIFICHE,
            "modulo_esportazione": FO.VERSIONE_MODULO}
