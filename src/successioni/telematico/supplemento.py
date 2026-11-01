"""Dati telematici NON ancora presenti nel modello comune (schema.py), letti da ``opzioni["telematico"]``.

``schema.py`` non prevede sesso, provincia di nascita, tipo soggetto, grado di parentela codificato, stato civile,
codice carica, dati catastali di luogo (provincia, codice comune), natura del terreno, tipo cespite, tipo passivita'...
Finche' il coordinatore non li promuove a campi (proposta in docs/PROPOSTE_telematico.md) si leggono dalla sezione libera
``opzioni.telematico`` (le sezioni ``opzioni`` sono gia' salvate, versionate e incluse nell'impronta dichiarativa).

Struttura::

    opzioni.telematico = {
      "dichiarazione": {"stato_civile", "devoluzione_per_legge", "firma_dichiarante",
                         "presentatore": {"persona_id", "codice_carica", "telefono", "email"}},
      "persone":   {<id>: {"sesso", "provincia_nascita", "tipo_soggetto", "grado_parentela", "portatore_handicap"}},
      "beni":      {<id>: {"provincia", "codice_comune", "comune_amministrativo", "codice_comune_amministrativo",
                           "indirizzo", "natura", "tipologia_terreno", "superficie", "reddito_dominicale", "classe",
                           "zona_censuaria", "consistenza", "tipo_cespite"}},
      "passivita": {<id>: {"tipo", "estremi_documento", "data_documento", "possesso", "bene_id"}},
    }

Qualsiasi altra chiave e' segnalata come non supportata (nessuna perdita silenziosa). Se in futuro un campo esiste
anche sull'entita' del modello comune, il valore dell'entita' ha la precedenza.
"""
from __future__ import annotations

from .. import valori as V

CHIAVI = {
    "persone": {"sesso", "provincia_nascita", "tipo_soggetto", "grado_parentela", "portatore_handicap"},
    "beni": {"provincia", "codice_comune", "comune_amministrativo", "codice_comune_amministrativo", "indirizzo",
             "natura", "tipologia_terreno", "superficie", "reddito_dominicale", "classe", "zona_censuaria",
             "consistenza", "tipo_cespite"},
    "passivita": {"tipo", "estremi_documento", "data_documento", "possesso", "bene_id"},
}
CHIAVI_DICHIARAZIONE = {"stato_civile", "devoluzione_per_legge", "firma_dichiarante", "presentatore"}
CHIAVI_PRESENTATORE = {"persona_id", "codice_carica", "telefono", "email"}
CHIAVI_SUPERFICIE = {"ettari", "are", "centiare"}
CHIAVI_TOP = set(CHIAVI) | {"dichiarazione"}


def sup(dati: dict) -> dict:
    t = (dati.get("opzioni") or {}).get("telematico")
    return t if isinstance(t, dict) else {}


def attr(dati: dict, coll: str, ent: dict, campo: str):
    """Valore del campo: prima sull'entita', poi in ``opzioni.telematico[coll][id]``.

    Restituisce ``None`` se assente o se lo stato del dato e' 'assente'/'non_applicabile'; uno stato
    'da_confermare' o 'zero' viene restituito cosi' com'e' (il chiamante decide se e' bloccante)."""
    v = ent.get(campo)
    if v is None:
        v = (sup(dati).get(coll) or {}).get(ent["id"], {}).get(campo)
    if V.e_stato(v) and v["stato"] in ("assente", "non_applicabile"):
        return None
    return v


def dich(dati: dict, campo: str, default=None):
    return (sup(dati).get("dichiarazione") or {}).get(campo, default)


def presentatore_sup(dati: dict) -> dict:
    p = dich(dati, "presentatore") or {}
    return p if isinstance(p, dict) else {}


def chiavi_non_gestite(dati: dict) -> list[str]:
    """Percorsi di chiavi di ``opzioni.telematico`` che questo modulo non serializza."""
    s = sup(dati)
    out = [f"opzioni.telematico.{k}" for k in s if k not in CHIAVI_TOP]
    for coll, ammesse in CHIAVI.items():
        ids = {e["id"] for e in dati.get(coll, [])}
        for i, d in (s.get(coll) or {}).items():
            if i not in ids:
                out.append(f"opzioni.telematico.{coll}[{i}]: riferimento a un elemento inesistente")
                continue
            out += [f"opzioni.telematico.{coll}[{i}].{k}" for k in (d or {}) if k not in ammesse]
    d = s.get("dichiarazione") or {}
    out += [f"opzioni.telematico.dichiarazione.{k}" for k in d if k not in CHIAVI_DICHIARAZIONE]
    out += [f"opzioni.telematico.dichiarazione.presentatore.{k}" for k in presentatore_sup(dati)
            if k not in CHIAVI_PRESENTATORE]
    return sorted(out)
