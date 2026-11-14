"""Riconoscimento dei documenti dell'Agenzia scaricati dopo l'invio della dichiarazione di successione (PDF), per conservarli nella
pratica giusta senza doverli scegliere a mano.

Riconosciuto oggi, sull'impaginazione osservata il 14/11/2026 in sei file reali «<codice fiscale>_SUC13_dcm_Attestazione.pdf»
letti solo in locale con il permesso del professionista:
- ``attestazione``: «ATTESTAZIONE DI AVVENUTA PRESENTAZIONE DELLA DICHIARAZIONE DI SUCCESSIONE TELEMATICA», con data di
  acquisizione, defunto (nome e codice fiscale), estremi di registrazione (volume, numero, anno), ufficio competente e codice di
  verifica. Dopo la prima pagina segue la copia della dichiarazione.

Un altro PDF dell'Agenzia che parla di una dichiarazione di successione e contiene un codice fiscale e' ``da_classificare``: si
conserva, ma il tipo lo indica il professionista. Ricevute di presentazione, di versamento ed esito delle volture saranno
riconosciute quando ci saranno esempi. Nessun dato viene inventato: cio' che non si legge resta vuoto.
"""
from __future__ import annotations

import io
import re

from ..errori import DatiNonValidi

_CF = r"[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]"


def _testo(pdf: bytes, pagine: int = 1) -> tuple[str, int]:
    from pypdf import PdfReader
    try:
        r = PdfReader(io.BytesIO(pdf))
        return "\n".join((r.pages[i].extract_text() or "") for i in range(min(pagine, len(r.pages)))), len(r.pages)
    except Exception as e:
        raise DatiNonValidi("PDF non leggibile", dettaglio=f"{type(e).__name__}: {e}"[:200]) from None


def _spazi(t: str) -> str:
    return re.sub(r"\s+", " ", t or "").strip()


def riconosci(pdf: bytes) -> dict:
    """``{"tipo": "attestazione" | "da_classificare" | None, "codice_fiscale_defunto", "dati": {...}, "pagine"}``. ``tipo`` None:
    non e' un documento dell'Agenzia sulla dichiarazione di successione (il file non va toccato)."""
    if pdf[:5] != b"%PDF-":
        return {"tipo": None, "codice_fiscale_defunto": None, "dati": {}, "pagine": 0}
    testo, pagine = _testo(pdf)
    t = _spazi(testo)
    su = t.upper()
    if "ATTESTAZIONE DI AVVENUTA PRESENTAZIONE" in su and "SUCCESSIONE" in su:
        dati: dict = {}
        m = re.search(r"in data (\d{2}/\d{2}/\d{4}) il sistema informativo", t)
        if m:
            dati["data_presentazione"] = m.group(1)
        m = re.search(r"del(?:la)? defunt[oa] (.+?)\s*, nat[oa] a (.+?), il (\d{2}/\d{2}/\d{4}), codice fiscale (" + _CF + ")", t)
        cf = None
        if m:
            dati.update({"defunto": m.group(1).strip(), "luogo_nascita": m.group(2).strip(), "data_nascita": m.group(3)})
            cf = m.group(4)
        m = re.search(r"registrata al volume (\d+), numero (\d+), anno (\d{4})", t)
        if m:
            dati["registrazione"] = {"volume": m.group(1), "numero": m.group(2), "anno": m.group(3)}
        m = re.search(r"\(Codice Ufficio (\w+)\)", t)
        if m:
            dati["codice_ufficio"] = m.group(1)
        m = re.search(r"competente alla lavorazione della dichiarazione [eè] l.\s*(.+?)(?= IL FUNZIONARIO| Firmato|$)", t)
        if m:
            dati["ufficio"] = m.group(1).strip()
        m = re.search(r"Codice di verifica:\s*(\w+)", t)
        if m:
            dati["codice_verifica"] = m.group(1)
        m = re.search(r"disponibile fino al (\d{2}/\d{2}/\d{4})", t)
        if m:
            dati["verificabile_fino_al"] = m.group(1)
        if not cf:
            m = re.search(r"codice fiscale (" + _CF + ")", t)
            cf = m.group(1) if m else None
        return {"tipo": "attestazione", "codice_fiscale_defunto": cf, "dati": dati, "pagine": pagine}
    if "AGENZIA" in su and "SUCCESSION" in su:
        m = re.search(_CF, t)
        if m:
            return {"tipo": "da_classificare", "codice_fiscale_defunto": m.group(0), "dati": {}, "pagine": pagine}
    return {"tipo": None, "codice_fiscale_defunto": None, "dati": {}, "pagine": pagine}


def candidato_per_nome(nome: str) -> bool:
    """Si aprono solo i PDF con un nome da documento dell'Agenzia sulla successione (es. «<CF>_SUC13_dcm_Attestazione.pdf»,
    «ricevuta…»): gli altri file della cartella non vengono letti."""
    n = (nome or "").upper()
    return n.endswith(".PDF") and ("SUC13" in n or "SUCCESSION" in n or "RICEVUT" in n or "ATTESTAZION" in n)
