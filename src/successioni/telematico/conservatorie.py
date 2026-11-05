"""Circoscrizioni di pubblicita' immobiliare (conservatorie) dei comuni catastali, per i righi EF15 ed EF16.

Fonti: XSD ``fornituraSUC13_v1.xsd`` (annotazione ``SezioneIII_TassaIpotecaria/Circoscrizioni_Numero``: «numero di
circoscrizioni immobiliari, individuate in base al codice del comune ... L'elenco delle conservatorie e' presente sul sito
internet dell'Agenzia delle Entrate»); Fascicolo I p. PDF 44 (stesso comune -> una circoscrizione).

L'elenco non e' nelle fonti del repository. Si legge a runtime dalla tabella ``comuni_conservatorie.res`` del componente di
controllo SUC13 che l'utente ha configurato (``SUCCESSIONI_CONTROLLI_SUC13``), come gia' fa ``codice_fiscale.py`` per i comuni:
la tabella non e' copiata nel programma. Righe: ``NOME*CODICE_CATASTALE*UFFICIO*PROVINCIA*CIRCOSCRIZIONE`` (il valore ``-`` indica
i comuni a sistema tavolare, senza circoscrizione). Senza componente il chiamante deve trattare il caso come non determinabile.
"""
from __future__ import annotations

import functools
import os
import re
import zipfile
from pathlib import Path

_RISORSA = "it/finanze/entrate/sco/resources/comuni_conservatorie.res"
FONTE = ("fornituraSUC13_v1.xsd, annotazione Circoscrizioni_Numero; Fascicolo I p. PDF 44; tabella comuni_conservatorie.res "
         "del componente di controllo SUC13 2.3.1")


def _jar() -> Path | None:
    cartella = os.environ.get("SUCCESSIONI_CONTROLLI_SUC13")
    if not cartella:
        return None
    p = Path(cartella) / "controlliXMLREG2013.jar"
    return p if p.is_file() else None


@functools.lru_cache(maxsize=4)
def _tabella(jar: str) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    with zipfile.ZipFile(jar) as z:
        for r in z.read(_RISORSA).decode("latin-1").splitlines():
            parti = r.split("*")
            if r.startswith("#") or len(parti) < 5 or not re.fullmatch(r"[A-Z][0-9]{3}[A-Z]?", parti[1].strip()):
                continue
            circ = parti[4].strip()
            out[parti[1].strip()] = circ if re.fullmatch(r"[A-Z]{2}[0-9]{2}", circ) else None
    return out


def tabella() -> dict[str, str | None] | None:
    """codice catastale -> codice della circoscrizione (``None`` per i comuni tavolari); ``None`` se non disponibile."""
    jar = _jar()
    if jar is None:
        return None
    try:
        return _tabella(str(jar))
    except (OSError, KeyError, zipfile.BadZipFile):
        return None


def circoscrizioni(codici_comune: list[str]) -> tuple[set[str] | None, str]:
    """(insieme delle circoscrizioni, motivo). Insieme ``None`` e motivo non vuoto se non determinabile."""
    t = tabella()
    if t is None:
        return None, ("elenco delle conservatorie non disponibile: configurare il componente di controllo SUC13 "
                      "(SUCCESSIONI_CONTROLLI_SUC13) o indicare un solo comune")
    sconosciuti = sorted(c for c in codici_comune if c not in t)
    if sconosciuti:
        return None, f"comuni {sconosciuti} assenti dall'elenco delle conservatorie"
    senza = sorted(c for c in codici_comune if t[c] is None)
    if senza:
        return None, f"comuni {senza} senza circoscrizione nell'elenco (sistema tavolare): caso non coperto in EB/EC"
    return {t[c] for c in codici_comune}, ""
