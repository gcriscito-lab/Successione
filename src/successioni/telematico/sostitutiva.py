"""Dichiarazione sostitutiva (codici 1 e 2 della casella «dichiarazione sostitutiva» del frontespizio).

Fonti (nessuna regola ricavata dalla memoria):
- XSD ``fornituraSUC13_v1.xsd``: ``Frontespizio/TipoDichiarazione`` (scelta fra ``PrimaDichiarazione`` e
  ``DichiarazioneSostitutiva`` + ``EstremiPrimaDichiarazione``), tipo ``DichiarazioneSostitutiva`` (1, 2, 3),
  ``EstremiPrimaDichiarazione_Type`` (Anno non inferiore al 2014, Volume al massimo 5 cifre, Numero al massimo 6 cifre),
  annotazioni di ``DataDecesso`` (anno <= anno della prima dichiarazione), ``ImpostaIpotecariaVersata``,
  ``ImpostaCatastaleVersata``, ``ImpostaCalcolata/ImpostaVersata``, ``Circoscrizioni_Numero``.
- Fascicolo I (Nov 2023): p. PDF 11-12 (tipo di dichiarazione, codici 1/2/3, «sostituisce integralmente la precedente»),
  p. PDF 13 (estremi della prima dichiarazione), pp. PDF 42-47 (righi EF6, EF8, EF12, EF14, EF15, EF16, EF18bis col. 3).

Perimetro: codici 1 e 2. Il codice 3 (solo frontespizio ed EG) e' dichiarato NON supportato: nessun XML.
I dati specifici stanno in ``opzioni.telematico.dichiarazione``::

    codice_sostitutiva   "1" (nuova trascrizione e voltura) | "2" (senza nuova trascrizione) | "3" (non supportato)
    prima_anno, prima_volume, prima_numero          estremi di registrazione della dichiarazione sostituita
                         (volume: 88888 o 88889)
    ipotecaria_versata   EF6  (rigo EF8 della dichiarazione sostituita), euro interi
    catastale_versata    EF12 (rigo EF14 della dichiarazione sostituita), euro interi
    successione_versata  EF18bis col. 3 (imposta di successione gia' versata), euro interi
    circoscrizioni_nuove (facoltativo, solo codice 1) numero di circoscrizioni delle nuove trascrizioni; senza: tutte
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .. import valori as V
from . import supplemento as SUP

CHIAVI_SOSTITUTIVA = ("codice_sostitutiva", "prima_anno", "prima_volume", "prima_numero",
                      "ipotecaria_versata", "catastale_versata", "successione_versata", "circoscrizioni_nuove")
FONTE_TIPO = "fornituraSUC13_v1.xsd Frontespizio/TipoDichiarazione; Fascicolo I p. PDF 11-12"
FONTE_ESTREMI = "fornituraSUC13_v1.xsd EstremiPrimaDichiarazione_Type; Fascicolo I p. PDF 13"
FONTE_VERSATE = "Fascicolo I pp. PDF 42-47 (righi EF6, EF12, EF18bis col. 3); annotazioni XSD ...Versata"
VOLUMI_TELEMATICI = ("88888", "88889")
_PERC = "opzioni.telematico.dichiarazione."


@dataclass(frozen=True)
class Sostitutiva:
    codice: str                 # "1" | "2"
    anno: str
    volume: str
    numero: str
    ipotecaria_versata: int
    catastale_versata: int
    successione_versata: int
    circoscrizioni_nuove: int | None = None   # solo codice 1: circoscrizioni delle nuove trascrizioni (default: tutte)


def e_sostitutiva(dati: dict) -> bool:
    return ((dati.get("opzioni") or {}).get("tipo_dichiarazione") or "originaria") != "originaria"


def _intero(dati: dict, chiave: str, errori: list) -> int:
    v = SUP.dich(dati, chiave)
    if v in (None, ""):
        return 0
    try:
        d = V.parse_importo(v)
    except V.ValoreNonValido as e:
        errori.append(("VALORE_NON_VALIDO", _PERC + chiave, str(e), FONTE_VERSATE))
        return 0
    if d < 0 or d != d.to_integral_value():
        errori.append(("VALORE_NON_VALIDO", _PERC + chiave, f"{d}: indicare euro interi non negativi (tracciato DatoNP_Type)",
                       FONTE_VERSATE))
        return 0
    return int(d)


def leggi(dati: dict, data_decesso: date | None = None) -> tuple[Sostitutiva | None, list[tuple[str, str, str, str]]]:
    """(configurazione, errori). Errori come tuple (codice, percorso, messaggio, fonte). ``None`` se non e' una sostitutiva
    o se i dati sono inutilizzabili."""
    if not e_sostitutiva(dati):
        return None, []
    tipo = (dati.get("opzioni") or {}).get("tipo_dichiarazione")
    err: list[tuple[str, str, str, str]] = []
    if tipo != "sostitutiva":
        return None, [("VALORE_NON_VALIDO", "opzioni.tipo_dichiarazione", f"tipo di dichiarazione {tipo!r} non ammesso "
                       "(originaria | sostitutiva)", FONTE_TIPO)]
    cod = SUP.dich(dati, "codice_sostitutiva")
    if cod in (None, ""):
        return None, [("DATO_MANCANTE", _PERC + "codice_sostitutiva", "dichiarazione sostitutiva: indicare il codice 1 "
                       "(nuova trascrizione e voltura) o 2 (senza nuova trascrizione)", FONTE_TIPO)]
    cod = str(cod)
    if cod == "3":
        return None, [("SOSTITUTIVA_NON_SUPPORTATA", _PERC + "codice_sostitutiva", "codice 3 (integrativa con sola "
                       "documentazione: solo frontespizio ed EG) non ancora gestito: nessun XML", FONTE_TIPO)]
    if cod not in ("1", "2"):
        return None, [("VALORE_NON_VALIDO", _PERC + "codice_sostitutiva", f"codice {cod!r} non ammesso (1, 2 o 3)", FONTE_TIPO)]
    anno, vol, num = (str(SUP.dich(dati, k) or "").strip() for k in ("prima_anno", "prima_volume", "prima_numero"))
    for k, v in (("prima_anno", anno), ("prima_volume", vol), ("prima_numero", num)):
        if not v:
            err.append(("DATO_MANCANTE", _PERC + k, "dichiarazione sostitutiva: indicare anno, volume e numero della "
                        "dichiarazione che si sostituisce", FONTE_ESTREMI))
    if anno and (not re.fullmatch(r"(18|19|20)\d{2}", anno) or int(anno) < 2014):
        err.append(("VALORE_NON_VALIDO", _PERC + "prima_anno", f"anno {anno!r}: quattro cifre, non inferiore al 2014",
                    FONTE_ESTREMI))
    elif anno and data_decesso and data_decesso.year > int(anno):
        err.append(("VALORE_NON_VALIDO", _PERC + "prima_anno", f"l'anno del decesso ({data_decesso.year}) deve essere "
                    f"minore o uguale all'anno della prima dichiarazione ({anno})", "annotazione XSD DataDecesso"))
    if vol and vol not in VOLUMI_TELEMATICI:
        err.append(("VALORE_NON_VALIDO", _PERC + "prima_volume", f"volume {vol!r}: la sostitutiva riguarda una dichiarazione "
                    "inviata con il modello telematico, il cui volume e' 88888 o 88889 (annotazione XSD; il controllo "
                    "ufficiale locale 2.3.1 scarta ogni altro valore, prova del 2026-11-05)", FONTE_ESTREMI))
    if num and not re.fullmatch(r"[0-9]{1,6}", num):
        err.append(("VALORE_NON_VALIDO", _PERC + "prima_numero", f"numero {num!r}: solo cifre, al massimo 6 (DatoTL_Type)",
                    FONTE_ESTREMI))
    versate = [_intero(dati, k, err) for k in ("ipotecaria_versata", "catastale_versata", "successione_versata")]
    nuove = None
    if SUP.dich(dati, "circoscrizioni_nuove") not in (None, ""):
        nuove = _intero(dati, "circoscrizioni_nuove", err)
        if nuove < 1 or cod != "1":
            err.append(("VALORE_NON_VALIDO", _PERC + "circoscrizioni_nuove", "campo ammesso solo con il codice 1 e con valore "
                        "almeno 1 (Fascicolo I pp. PDF 45-46)", FONTE_VERSATE))
    if err:
        return None, err
    return Sostitutiva(cod, anno, vol, num, *versate, circoscrizioni_nuove=nuove), []


def tipo_dichiarazione_xml(s: Sostitutiva | None) -> dict:
    """Parte iniziale di ``Frontespizio/TipoDichiarazione`` (prima di ``Devoluzione``)."""
    if s is None:
        return {"PrimaDichiarazione": "1"}
    return {"DichiarazioneSostitutiva": s.codice,
            "EstremiPrimaDichiarazione": {"Anno": s.anno, "Volume": s.volume, "Numero": s.numero}}


def rilievi(dati: dict) -> list[tuple[str, str, str, str]]:
    """Controlli di coerenza dei dati inseriti (usati anche dalla verifica della pratica)."""
    dec = None
    for p in dati.get("persone", []):
        if p.get("ruolo") == "defunto" and isinstance(p.get("data_decesso"), str):
            try:
                dec = date.fromisoformat(p["data_decesso"])
            except ValueError:
                dec = None
    return leggi(dati, dec)[1]


def netto(dovuto: Decimal | int, versato: int) -> Decimal:
    """Differenza non negativa fra imposta dovuta e gia' versata (righi EF8/EF14: «non puo' essere negativo»)."""
    d = Decimal(dovuto) - Decimal(versato)
    return d if d > 0 else Decimal(0)
