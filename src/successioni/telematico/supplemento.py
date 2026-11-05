"""Dati telematici NON ancora presenti nel modello comune (schema.py), letti da ``opzioni["telematico"]``.

``schema.py`` non prevede sesso, provincia di nascita, tipo soggetto, grado di parentela codificato, stato civile,
codice carica, dati catastali di luogo (provincia, codice comune), natura del terreno, tipo cespite, tipo passivita'...
Finche' il coordinatore non li promuove a campi (proposta in docs/PROPOSTE_telematico.md) si leggono dalla sezione libera
``opzioni.telematico`` (le sezioni ``opzioni`` sono gia' salvate, versionate e incluse nell'impronta dichiarativa).

Struttura::

    opzioni.telematico = {
      "dichiarazione": {"stato_civile", "devoluzione_per_legge", "firma_dichiarante",
                         "presentatore": {"persona_id", "codice_carica", "telefono", "email"},
                         "versamento": {"iban", "cf_titolare"},          # Frontespizio/Versamento (EF19 > 0)
                         "tempistica_pagamento",                        # EF18ter col. 1 (1 | 2)
                         "pagamento_rateale", "acconto",                # EF18ter col. 2-3: numero di rate (1-12) e acconto in euro
                         "dichiara_copie_conformi"},                    # EH FlagPassivita (lettera l)
      "persone":   {<id>: {"sesso", "provincia_nascita", "tipo_soggetto", "grado_parentela", "portatore_handicap",
                           "comune_decesso", "provincia_decesso"}},    # luogo del decesso: EH DatiDefunto/Decesso
      "beni":      {<id>: {"provincia", "codice_comune", "comune_amministrativo", "codice_comune_amministrativo",
                           "indirizzo", "natura", "tipologia_terreno", "superficie", "reddito_dominicale", "classe",
                           "zona_censuaria", "consistenza", "tipo_cespite"}},
      "passivita": {<id>: {"tipo", "estremi_documento", "data_documento", "possesso", "bene_id",
                           "ripartizione": [{"persona_id", "quota"}]}},   # in alternativa a persona_id
    }

Qualsiasi altra chiave e' segnalata come non supportata (nessuna perdita silenziosa). Se in futuro un campo esiste
anche sull'entita' del modello comune, il valore dell'entita' ha la precedenza.
"""
from __future__ import annotations

from .. import valori as V

CHIAVI = {
    "persone": {"sesso", "provincia_nascita", "tipo_soggetto", "grado_parentela", "portatore_handicap",
                "comune_decesso", "provincia_decesso", "rappresentato_cf", "rappresentato_grado", "rinuncia",
                "rinuncia_estremi", "residenza_estera", "denominazione", "certificatore_disabilita"},
    "beni": {"provincia", "codice_comune", "comune_amministrativo", "codice_comune_amministrativo", "indirizzo",
             "natura", "tipologia_terreno", "superficie", "reddito_dominicale", "classe", "zona_censuaria",
             "consistenza", "tipo_cespite", "estremi_trascrizione", "estremi_registrazione",
             "valore_prec_succ", "bene_estero", "imposta_estera", "codice_stato_estero", "stato_estero",
             "stato_federato", "localita_estero", "graffati", "immobili_aziendali"},
    "passivita": {"tipo", "estremi_documento", "data_documento", "possesso", "bene_id", "ripartizione"},
    # agevolazioni della sezione devoluzione (docs/regole/prima_casa.md): oggi solo i codici P, X, Z
    "devoluzioni": {"agevolazioni", "riduzioni"},
}
CHIAVI_DICHIARAZIONE = {"stato_civile", "devoluzione_per_legge", "firma_dichiarante", "presentatore", "versamento",
                        "tempistica_pagamento", "pagamento_rateale", "acconto", "dichiara_copie_conformi",
                        "devoluzione_per_testamento", "testamento", "azienda_data_deposito", "azienda_camera_commercio",
                        "prima_casa", "riduzioni_art25",
                        "codice_sostitutiva", "prima_anno", "prima_volume", "prima_numero", "ipotecaria_versata",
                        "catastale_versata", "successione_versata", "circoscrizioni_nuove",
                        "separazione_con_colpa", "no_scioglimento_unione_civile", "reintegro_1", "reintegro_2", "reintegro_3",
                        "legge_estera", "eventi_eccezionali", "data_opzione", "beneficio_inventario", "residenza_estera_defunto",
                        "casi_particolari", "morte_presunta"}
# Sezione Testamento del frontespizio (annotazioni XSD: Pubblicazione, Registrazione, TestamentoEstero)
CHIAVI_TESTAMENTO = {"estero", "pubblico_ufficiale", "data_pubblicazione", "ufficio_registrazione", "serie",
                     "numero_registrazione", "sottonumero_registrazione", "data_registrazione"}
CHIAVI_VERSAMENTO = {"iban", "cf_titolare"}
# Sezione II del quadro EH (agevolazione prima casa): vedi prima_casa.CHIAVI_PRIMA_CASA
CHIAVI_PRESENTATORE = {"persona_id", "codice_carica", "telefono", "email", "data_decorrenza", "rappresentato_cf", "residente_estero"}
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
    tst = d.get("testamento")
    if isinstance(tst, dict):
        out += [f"opzioni.telematico.dichiarazione.testamento.{k}" for k in tst if k not in CHIAVI_TESTAMENTO]
    for n in (1, 2, 3):
        r = d.get(f"reintegro_{n}")
        if isinstance(r, dict):
            out += [f"opzioni.telematico.dichiarazione.reintegro_{n}.{k}" for k in r if k not in CHIAVI_TESTAMENTO]
    pc = d.get("prima_casa")
    if pc is not None and not isinstance(pc, dict):
        out.append("opzioni.telematico.dichiarazione.prima_casa: attesa una struttura di chiavi")
    v = d.get("versamento")
    if isinstance(v, dict):
        out += [f"opzioni.telematico.dichiarazione.versamento.{k}" for k in v if k not in CHIAVI_VERSAMENTO]
    return sorted(out)
