"""Percorsi e citazioni delle fonti ufficiali usate dal modulo telematico.

Tutti i percorsi sono relativi al repository (cartella ``fonti/``, sola lettura); nessun percorso Windows.
La radice puo' essere sostituita con la variabile d'ambiente ``SUCCESSIONI_FONTI`` (cartella ``fonti``)
per installazioni in cui i materiali ministeriali non stanno accanto al codice.

Le pagine citate sono pagine del file PDF (``pdftotext -f N -l N``); dove la numerazione stampata differisce lo si
indica come "p. PDF".
"""
from __future__ import annotations

import os
from pathlib import Path

#: versione dei materiali tecnici (nome della cartella ministeriale in fonti/Specifiche tecniche)
VERSIONE_SPECIFICHE = "SUC13_20250702"
NOME_XSD = "fornituraSUC13_v1.xsd"
#: versione delle regole di esportazione/calcolo di questo modulo (cambia quando cambia il comportamento)
VERSIONE_MODULO = "telematico-0.2 (" + VERSIONE_SPECIFICHE + ")"

# Namespace come dichiarati negli XSD (targetNamespace). Nota: per tm il PDF (Tabella 1, p. 9) riporta
# 'urn:www.agenziaentrate.gov.it:specificheTecniche:telent:v1', mentre telematico_v1.xsd dichiara
# 'www.agenziaentrate.gov.it:specificheTecniche:telent:v1' (senza 'urn:'): vale lo schema, che e' quello validato.
NS_TM = "www.agenziaentrate.gov.it:specificheTecniche:telent:v1"
NS_CM = "urn:www.agenziaentrate.gov.it:specificheTecniche:common:v2"
NS_SC = "urn:www.agenziaentrate.gov.it:specificheTecniche:sco:common:v3"
NS_REG = "urn:www.agenziaentrate.gov.it:specificheTecniche:sco:reg:v2"
NS_SUC = "urn:www.agenziaentrate.gov.it:specificheTecniche:sco:suc:v1"
NSMAP = {"tm": NS_TM, "suc": NS_SUC, "reg": NS_REG, "sc": NS_SC, "cm": NS_CM}

#: citazioni brevi dei documenti (usate nel campo ``fonte`` degli errori)
DOC_SPEC = "Specifiche_SUC13_20250702.pdf"
DOC_GUIDA = "All. Specifiche tecniche (passaggi calcolo imposta di successione).pdf"
DOC_FASC1 = "Succ_FASCICOLO_I_Nov_23.pdf"
FONTE_XSD = f"{NOME_XSD} ({VERSIONE_SPECIFICHE})"

#: componente ufficiale ispezionato staticamente (NON eseguito) per il comportamento di calcolo
COMPONENTE_CALCOLO = ("controlliXMLREG2013.jar (https://jws.agenziaentrate.it/jws/registro/2013/, scaricato il "
                      "2026-11-01, SHA-256 0b42dfc37e673a4cee65f696bbf84612fee0c898a7a3b0456b661d17dece6a10), "
                      "classi it.finanze.entrate.sco.modSUC2013.CalcolaImpostaSuccessione/ImpostaSuccessione")


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


def fonte_annotazione(elemento: str) -> str:
    """Regola applicativa contenuta nella documentazione (xs:annotation) di un elemento XSD."""
    return f"{FONTE_XSD}, annotazione dell'elemento {elemento}"


def fonte_spec(pagina: int, sezione: str = "") -> str:
    return f"{DOC_SPEC} p. {pagina}" + (f" {sezione}" if sezione else "")


def fonte_fasc1(pagina_pdf: int, voce: str = "") -> str:
    return f"{DOC_FASC1} p. PDF {pagina_pdf}" + (f" ({voce})" if voce else "")


def fonte_guida(pagina: int, voce: str = "") -> str:
    return f"{DOC_GUIDA} p. {pagina}" + (f" ({voce})" if voce else "") + "; decorrenza: successioni aperte dal 2025-01-01"
