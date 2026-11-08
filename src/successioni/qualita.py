"""Controlli di qualita' dei dati anagrafici e catastali (voce 21 di docs/ANALISI_REPLICA_2026-11-07.md).

Sono **avvisi**: non bloccano la finalizzazione e non contengono regole fiscali. Segnalano dati probabilmente scritti male
(spazi doppi, codice fiscale duplicato o incoerente con i dati anagrafici, date in ordine impossibile, provincia diversa da
quella del codice comune). La decisione resta al professionista: un caso raro ma corretto (es. un concepito al momento del
decesso) produce l'avviso ma non impedisce nulla.

Escluse per mancanza di una fonte in ``fonti/``: zeri iniziali di foglio e particella, termine di cinque anni per la prima
casa. Il controllo della provincia usa le tabelle dei comuni del componente ufficiale SUC13, se configurato
(``codice_fiscale.cerca_comune``); altrimenti non produce avvisi.
"""
from __future__ import annotations

import re

from . import codice_fiscale as CF
from .schema import Errore
from .telematico import identificativi as ID
from .telematico import supplemento as SUP

_SPAZI = re.compile(r"^\s|\s$|\s{2,}")
_TESTI_PERSONA = ("cognome", "nome", "luogo_nascita", "comune_decesso")
_TESTI_BENE = ("comune", "indirizzo", "comune_amministrativo")


def _iso(v) -> str | None:
    return v if isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) else None


def _campo(dati: dict, coll: str, ent: dict, campo: str):
    """Valore sull'entita' oppure, se assente, in ``opzioni.telematico`` (sesso, provincia, codice comune, comune del
    decesso...): stessa lettura dell'esportazione (``telematico.supplemento.attr``)."""
    v = ent.get(campo)
    return v if v is not None else SUP.attr(dati, coll, ent, campo)


def _nome(p: dict) -> str:
    n = " ".join(str(p.get(k) or "").strip() for k in ("cognome", "nome")).strip()
    return n or p["id"]


def avvisi(dati: dict) -> list[Errore]:
    out: list[Errore] = []
    persone = dati.get("persone", [])
    defunto = next((p for p in persone if p.get("ruolo") == "defunto"), None)
    decesso = _iso(defunto.get("data_decesso")) if defunto else None

    for p in persone:
        base = f"persone[{p['id']}]"
        for c in _TESTI_PERSONA:
            v = _campo(dati, "persone", p, c)
            if isinstance(v, str) and _SPAZI.search(v):
                out.append(Errore("SPAZI_ANOMALI", f"{base}.{c}", f"«{v}»: spazi doppi, iniziali o finali"))
        cf = p.get("codice_fiscale")
        if isinstance(cf, str) and len(cf.strip()) == 16:
            d = CF.decodifica(cf, ruolo=p.get("ruolo"))
            if not ID.cf_persona_fisica_valido(cf.strip().upper()):
                out.append(Errore("CF_CONTROLLO_ERRATO", f"{base}.codice_fiscale",
                                  f"carattere di controllo errato (atteso {ID.carattere_controllo(cf.strip().upper()[:15])}): "
                                  "controllare il codice sul documento"))
            else:
                campi = d["campi"]
                sesso = _campo(dati, "persone", p, "sesso")
                if sesso in ("M", "F") and campi.get("sesso") and campi["sesso"] != sesso:
                    out.append(Errore("CF_INCOERENTE", f"{base}.sesso",
                                      f"il codice fiscale indica sesso {campi['sesso']}, nella scheda {sesso}"))
                nasc = _iso(p.get("data_nascita"))
                da_cf = campi.get("data_nascita")
                # confronto su giorno, mese e ultime due cifre dell'anno: il secolo non e' nel codice
                if nasc and da_cf and (nasc[2:4], nasc[5:]) != (da_cf[2:4], da_cf[5:]):
                    out.append(Errore("CF_INCOERENTE", f"{base}.data_nascita",
                                      f"il codice fiscale indica la nascita il {da_cf[8:]}/{da_cf[5:7]}/..{da_cf[2:4]}, "
                                      f"nella scheda {nasc[8:]}/{nasc[5:7]}/{nasc[:4]}"))
        nasc = _iso(p.get("data_nascita"))
        if p is defunto and nasc and decesso and nasc > decesso:
            out.append(Errore("DATE_INCOERENTI", f"{base}.data_nascita", "la data di nascita del defunto e' successiva a "
                                                                         "quella del decesso"))
        elif p is not defunto and nasc and decesso and nasc > decesso:
            out.append(Errore("NATO_DOPO_IL_DECESSO", f"{base}.data_nascita",
                              f"{_nome(p)} risulta nato dopo il decesso: verificare la data (o il caso del concepito)"))

    visti: dict[str, dict] = {}
    for p in persone:
        cf = p.get("codice_fiscale")
        if not isinstance(cf, str) or not cf.strip():
            continue
        k = cf.strip().upper()
        if k in visti:
            out.append(Errore("CF_DUPLICATO", f"persone[{p['id']}].codice_fiscale",
                              f"stesso codice fiscale di {_nome(visti[k])}: ogni soggetto va indicato una volta sola"))
        else:
            visti[k] = p

    for b in dati.get("beni", []):
        base = f"beni[{b['id']}]"
        for c in _TESTI_BENE:
            v = _campo(dati, "beni", b, c)
            if isinstance(v, str) and _SPAZI.search(v):
                out.append(Errore("SPAZI_ANOMALI", f"{base}.{c}", f"«{v}»: spazi doppi, iniziali o finali"))
        cod, prov = _campo(dati, "beni", b, "codice_comune"), _campo(dati, "beni", b, "provincia")
        if isinstance(cod, str) and isinstance(prov, str) and cod.strip() and prov.strip() and prov.strip().upper() != "EE":
            com = CF.cerca_comune(cod.strip().upper())
            if com and com.get("provincia") and com["provincia"].upper() != prov.strip().upper():
                out.append(Errore("PROVINCIA_INCOERENTE", f"{base}.provincia",
                                  f"il codice comune {cod.strip().upper()} ({com['nome']}) e' in provincia di "
                                  f"{com['provincia']}, nella scheda {prov.strip().upper()}"))
    return out
