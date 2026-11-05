"""Codici degli Stati esteri (CodiceStatoEstero, 3 caratteri) per la residenza estera dei soggetti EA.

Fonti: XSD ``Residenza_Estera_Type`` (CodiceStatoEstero lunghezza 3); Fascicolo I p. PDF 18 («la tabella con l'elenco dei codici degli
Stati esteri e' consultabile nell'Appendice del Modello Unico Persone fisiche»). La tabella non e' nelle fonti del repository: si legge a
runtime da ``stati_esteri_cod.res`` del componente di controllo SUC13 configurato (``SUCCESSIONI_CONTROLLI_SUC13``), senza copiarla.
Senza componente la tabella non e' disponibile e il codice si controlla solo nella forma (tre caratteri).
"""
from __future__ import annotations

import functools
import os
import re
import zipfile
from pathlib import Path

_RISORSA = "it/finanze/entrate/sco/resources/stati_esteri_cod.res"


def _jar() -> Path | None:
    cartella = os.environ.get("SUCCESSIONI_CONTROLLI_SUC13")
    if not cartella:
        return None
    p = Path(cartella) / "controlliXMLREG2013.jar"
    return p if p.is_file() else None


@functools.lru_cache(maxsize=4)
def _tabella(jar: str) -> dict[str, str]:
    out: dict[str, str] = {}
    with zipfile.ZipFile(jar) as z:
        for r in z.read(_RISORSA).decode("latin-1").splitlines():
            m = re.fullmatch(r"\s*(.*?)\*(\w{3})\s*", r)           # righe NOME*CODICE
            if m and not r.startswith("#"):
                out[m.group(2)] = m.group(1)
    return out


def tabella() -> dict[str, str] | None:
    """codice -> nome dello Stato, oppure ``None`` se il componente non e' disponibile."""
    jar = _jar()
    if jar is None:
        return None
    try:
        return _tabella(str(jar))
    except (OSError, KeyError, zipfile.BadZipFile):
        return None
