"""Dati telematici NON ancora presenti nel modello comune (schema.py): lettura da ``opzioni["telematico"]``.

``schema.py`` non prevede sesso, province, codici catastali, grado di parentela codificato, stato civile ecc.
Finche' il coordinatore non li promuove a campi (vedi docs/PROPOSTE_telematico.md) li leggiamo dalla sezione
libera ``opzioni.telematico``; se un campo esiste gia' sull'entita' ha la precedenza. Le chiavi ammesse sono
elencate qui: qualsiasi altra chiave viene segnalata come non supportata (nessuna perdita silenziosa).
"""
from __future__ import annotations

from .. import valori as V

CHIAVI_PERSONA = {"sesso", "provincia_nascita", "tipo_soggetto", "grado_parentela", "portatore_handicap",
                  "denominazione", "qualifiche"}
CHIAVI_BENE = {"provincia", "comune_amministrativo", "codice_comune", "codice_comune_amministrativo", "indirizzo",
               "natura", "tipologia_terreno", "classe", "zona_censuaria", "consistenza", "superficie",
               "reddito_dominicale", "tipo_cespite"}
CHIAVI_DICHIARAZIONE = {"stato_civile", "presentatore", "luogo_decesso", "eh", "firma_dichiarante",
                        "devoluzione_per_legge", "devoluzione_per_testamento", "legge_estera",
                        "circoscrizioni_numero"}
CHIAVI_PRESENTATORE = {"persona_id", "codice_carica", "telefono", "email"}
CHIAVI_EH = {"assenza_testamento", "assenza_interdetti", "assenza_rinuncia", "assenza_separazione", "firma"}
CHIAVI_TOP = {"persone", "beni", "dichiarazione"}


def sup(dati: dict) -> dict:
    t = (dati.get("opzioni") or {}).get("telematico")
    return t if isinstance(t, dict) else {}


def attr(dati: dict, coll: str, ent: dict, campo: str):
    """Valore del campo: prima sull'entita', poi in ``opzioni.telematico[coll][id]``. ``None`` se assente."""
    if campo in ent and not V.e_stato(ent[campo]):
        return ent[campo]
    return (sup(dati).get(coll) or {}).get(ent["id"], {}).get(campo)


def dich(dati: dict, campo: str, default=None):
    return (sup(dati).get("dichiarazione") or {}).get(campo, default)


def chiavi_non_gestite(dati: dict) -> list[str]:
    """Percorsi di chiavi presenti in ``opzioni.telematico`` che questo modulo non serializza."""
    s = sup(dati)
    out = [f"opzioni.telematico.{k}" for k in s if k not in CHIAVI_TOP]
    for coll, ammesse in (("persone", CHIAVI_PERSONA), ("beni", CHIAVI_BENE)):
        for i, d in (s.get(coll) or {}).items():
            out += [f"opzioni.telematico.{coll}[{i}].{k}" for k in d if k not in ammesse]
    d = s.get("dichiarazione") or {}
    out += [f"opzioni.telematico.dichiarazione.{k}" for k in d if k not in CHIAVI_DICHIARAZIONE]
    out += [f"opzioni.telematico.dichiarazione.presentatore.{k}" for k in (d.get("presentatore") or {})
            if k not in CHIAVI_PRESENTATORE]
    out += [f"opzioni.telematico.dichiarazione.eh.{k}" for k in (d.get("eh") or {}) if k not in CHIAVI_EH]
    return out
