"""Codici ufficiali dei campi a valori fissi (stato civile, grado di parentela, categoria catastale, diritti, tipi di passivita'...).

Unica sorgente: le enumerazioni degli XSD SUC13 (``telematico/xsd.py``, cartella ``fonti/Specifiche tecniche``): nessun codice e'
scritto a mano in questo modulo. Qui si dice solo QUALE tipo XSD governa QUALE campo della pratica (le stesse scelte che fa
l'esportazione in ``telematico/esporta.py``: ``tests/test_codici.py`` verifica la corrispondenza) e si costruiscono i menu per
l'interfaccia nello stesso formato dei campi a scelta guidata di ``schema.STRUTTURATI``.

Il valore salvato nella pratica e' il CODICE dell'XSD (es. stato civile ``4``), che l'esportazione accetta cosi' com'e'.
Una voce scritta a mano in ``STRUTTURATI`` ha la precedenza su quella generata. Senza le fonti l'elenco e' vuoto e i campi
restano di testo libero (l'esportazione continua a validare il valore).
"""
from __future__ import annotations

import re

# chiave del campo -> (tipo XSD, etichetta). Chiavi: «coll.campo» (campo del modello), «coll.campo@contesto» (l'elenco dipende dal
# tipo del bene: «immobile» = fabbricato o terreno, «altro» = gli altri beni) e «dichiarazione.<chiave>» (opzioni.telematico).
REGOLE: dict[str, tuple[str, str]] = {
    "dichiarazione.stato_civile": ("StatoCivile_Type", "stato civile del defunto"),
    "dichiarazione.tempistica_pagamento": ("TempisticaPagamento_Type", "tempistica del pagamento"),
    "dichiarazione.presentatore.codice_carica": ("CodiciCarica_Type", "carica del presentatore"),
    "persone.grado_parentela": ("GradoParentela_Type", "grado di parentela"),
    "persone.tipo_soggetto": ("TipoSoggetto_Type", "tipo di soggetto"),
    "beni.categoria": ("CodiciCategoriaCatastale_Type", "categoria catastale"),
    "beni.natura": ("CodiciNatura_Type", "natura"),
    "beni.tipologia_terreno": ("TerrenoEdificabile_Type", "tipologia del terreno"),
    "beni.tipo_cespite": ("TipoCespite_Type", "tipo di cespite"),
    "beni.tipo_documento": ("TipoDocumento_Type", "tipo di documento dell'azienda"),
    "beni.tipo_unita": ("TipoUnita_Type", "tipo di unita'"),
    "beni.diritto@immobile": ("CodiciDirittoImmobili_Type", "diritto del defunto"),
    "beni.diritto@altro": ("CodiciDirittoNonImmobili", "diritto del defunto"),
    "devoluzioni.diritto@immobile": ("CodiciDiritto_Type", "diritto dell'erede"),
    "devoluzioni.diritto@altro": ("CodiciDirittoNonImmobiliDevoluzione", "diritto dell'erede"),
    "passivita.tipo": ("CodiciPassivita_Type", "tipo di passivita'"),
    # Province. Conferme nell'esportazione (esporta.py / quadri_efgh.py, sola lettura):
    #  - provincia di nascita: anagrafica(), «codice_enum(str(v).upper(), "PN_Type")» (esporta.py riga 211, ogni soggetto);
    #  - provincia di decesso: quadri_efgh._pn(), «codice_enum(..., "PN_Type")» (riga 569), usata alla riga 492 per
    #    provincia_decesso del defunto (EH, Decesso/Provincia);
    #  - provincia dell'immobile: luogo() accetta reg:PENonTavolare_Type (esporta.py riga 393) e luogo_tavolare()
    #    reg:PRTavolare_Type (riga 427): il menu e' l'unione dei due tipi (BL, BS, UD, VI stanno in entrambi; BZ, TN, GO, TS
    #    solo nel tavolare). Solo fabbricati e terreni hanno una provincia: contesto «immobile».
    "persone.provincia_nascita": ("PN_Type", "provincia di nascita"),
    "persone.provincia_decesso": ("PN_Type", "provincia di decesso"),
    "beni.provincia@immobile": ("PENonTavolare_Type+PRTavolare_Type", "provincia dell'immobile"),
}
# Criterio per le liste lunghe: fino a SOGLIA_MENU voci il campo e' un menu a tendina (REGOLE). Oltre, un menu di centinaia di
# righe senza descrizioni (negli XSD i comuni catastali e gli uffici hanno solo il codice) non si scorre: il campo resta di
# testo libero con suggerimenti dei soli codici ammessi (SUGGERIMENTI, da mostrare con un <datalist>). Le province (111-115
# sigle di due lettere, note a chi compila e raggiungibili digitando) restano nel menu.
SOGLIA_MENU = 150
# chiave del campo -> (tipo XSD, etichetta). Conferme nell'esportazione:
#  - beni.codice_comune_catastale: luogo_tavolare(), «codice_enum(str(v), "ComuniCatastaliTNBZ_Type")» (esporta.py riga 447);
#  - dichiarazione.testamento.ufficio_registrazione: valida_testamento(), «codice_enum(uff, "UfficioDiRegistrazione_Type")»
#    (esporta.py riga 1159).
SUGGERIMENTI: dict[str, tuple[str, str]] = {
    "beni.codice_comune_catastale": ("ComuniCatastaliTNBZ_Type", "codice del comune catastale (TN e BZ)"),
    "dichiarazione.testamento.ufficio_registrazione": ("UfficioDiRegistrazione_Type", "ufficio di registrazione del testamento"),
}
TIPI_IMMOBILE = ("fabbricato", "terreno")


def contesto_bene(tipo_bene: str | None) -> str:
    return "immobile" if tipo_bene in TIPI_IMMOBILE else "altro"


def _chiave_naturale(codice: str):
    """Ordine dei codici: numeri in ordine numerico, poi lettere (es. 1, 1S, 2, 10 invece di 1, 10, 1S, 2)."""
    return [(0, int(p), "") if p.isdigit() else (1, 0, p) for p in re.split(r"(\d+)", codice) if p != ""]


def _etichetta(descrizione: str) -> str:
    """Pulizia di forma (spazi, ';' o '.' finali del testo ufficiale) senza cambiare le parole."""
    return " ".join(descrizione.split()).rstrip(";. ")


def tipi_xsd(tipo_xsd: str) -> list[str]:
    """Tipi XSD di una regola: «A+B» = unione delle enumerazioni di A e B (il campo e' validato dall'uno o dall'altro)."""
    return tipo_xsd.split("+")


def voci(tipo_xsd: str) -> list[dict]:
    """[{valore, etichetta, aiuto}] dalle enumerazioni del tipo XSD; [] se le fonti non sono disponibili."""
    from .telematico import xsd as X
    enum: dict[str, str] = {}
    try:
        for t in tipi_xsd(tipo_xsd):
            for k, d in X.enumerazioni(t).items():
                if not enum.get(k):
                    enum[k] = d
    except Exception:                    # fonti assenti o illeggibili: i campi restano di testo libero
        return []
    return [{"valore": k, "etichetta": _etichetta(d) or k, "aiuto": ""}
            for k, d in sorted(enum.items(), key=lambda kv: _chiave_naturale(kv[0]))]


def strutturati() -> dict[str, dict]:
    """Campi a scelta guidata generati dagli XSD, nel formato di ``schema.STRUTTURATI``."""
    out = {}
    for chiave, (tipo, etichetta) in REGOLE.items():
        opz = voci(tipo)
        if opz:
            out[chiave] = {"etichetta": etichetta, "tipo": "enum", "opzioni": opz, "xsd": tipo,
                           "aiuto": f"Codici ufficiali (XSD SUC13, tipo {tipo}). Si salva il codice."}
    return out


def suggerimenti() -> dict[str, dict]:
    """Campi di testo libero con un elenco lungo di codici ammessi, da mostrare come suggerimenti e non come menu:
    {chiave: {etichetta, xsd, valori: [codice, ...]}}. Vuoto senza le fonti."""
    out = {}
    for chiave, (tipo, etichetta) in SUGGERIMENTI.items():
        v = voci(tipo)
        if v:
            out[chiave] = {"etichetta": etichetta, "xsd": tipo, "valori": [x["valore"] for x in v]}
    return out
