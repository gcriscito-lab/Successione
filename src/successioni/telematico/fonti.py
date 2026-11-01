"""Percorsi e riferimenti delle fonti ufficiali usate dal modulo telematico.

Tutti i percorsi sono relativi al repository (cartella ``fonti/``); nessun percorso Windows.
La radice puo' essere sostituita con la variabile d'ambiente ``SUCCESSIONI_FONTI`` (cartella ``fonti``)
per installazioni in cui i materiali ministeriali non stanno accanto al codice.
"""
from __future__ import annotations

import os
from pathlib import Path

#: versione dei materiali tecnici (nome della cartella ministeriale in fonti/Specifiche tecniche)
VERSIONE_SPECIFICHE = "SUC13_20250702"
NOME_XSD = "fornituraSUC13_v1.xsd"

NS_TM = "www.agenziaentrate.gov.it:specificheTecniche:telent:v1"
NS_CM = "urn:www.agenziaentrate.gov.it:specificheTecniche:common:v2"
NS_SC = "urn:www.agenziaentrate.gov.it:specificheTecniche:sco:common:v3"
NS_REG = "urn:www.agenziaentrate.gov.it:specificheTecniche:sco:reg:v2"
NS_SUC = "urn:www.agenziaentrate.gov.it:specificheTecniche:sco:suc:v1"

#: citazioni brevi dei documenti (usate nel campo ``fonte`` degli errori)
DOC_SPEC = "Specifiche_SUC13_20250702.pdf"
DOC_GUIDA = "All. Specifiche tecniche (passaggi calcolo imposta di successione).pdf"
DOC_FASC1 = "Succ_FASCICOLO_I_Nov_23.pdf (istruzioni, aggiornamenti 2025)"
FONTE_XSD = f"{NOME_XSD} ({VERSIONE_SPECIFICHE})"


def radice_fonti() -> Path:
    env = os.environ.get("SUCCESSIONI_FONTI")
    if env:
        return Path(env)
    # src/successioni/telematico/fonti.py -> radice repository = parents[3]
    return Path(__file__).resolve().parents[3] / "fonti"


def cartella_xsd() -> Path:
    return radice_fonti() / "Specifiche tecniche" / VERSIONE_SPECIFICHE


def xsd_principale() -> Path:
    return cartella_xsd() / "SUC" / "xsd" / NOME_XSD


def fonte_xsd(elemento: str | None = None) -> str:
    return FONTE_XSD + (f", elemento {elemento}" if elemento else "")
