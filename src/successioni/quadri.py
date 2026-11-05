"""Registro dei quadri del modello SUC13 e loro stato nell'interfaccia.

Nomi e sigle seguono il compilatore/modello ufficiale (albero tree_mod.xml del pacchetto pubblico SUC13 e istruzioni).
La corrispondenza quadro -> collezioni del modello comune e' una scelta dell'applicazione: gli id interni restano stabili
anche se righe/moduli ministeriali cambiano. Quadri `supportato=False`: la bozza resta conservata ma la pratica non e'
finalizzabile finche' il quadro e' attivo (specifica §1).
"""
from __future__ import annotations

from .etichette import ordina
from .schema import Errore

# colonne = campi mostrati nella tabella del quadro (sottoinsieme dei campi dello schema)
QUADRI: list[dict] = [
    {"id": "AN", "titolo": "Dati generali", "gruppo": "frontespizio", "vista": "frontespizio", "supportato": True},
    {"id": "EA", "titolo": "Eredi, chiamati, legatari e altri soggetti", "gruppo": "quadri", "vista": "tabella",
     "coll": "persone", "preset": {"ruolo": "erede"},
     "colonne": ["cognome", "nome", "codice_fiscale", "data_nascita", "luogo_nascita", "provincia_nascita", "ruolo", "grado_parentela"],
     "supportato": True},
    {"id": "EB", "titolo": "Attivo ereditario catasto terreni", "gruppo": "quadri", "vista": "tabella", "coll": "beni",
     "preset": {"tipo": "terreno"},
     "colonne": ["comune", "sezione", "foglio", "particella", "subalterno", "diritto", "quota_defunto", "valore", "rendita", "provenienza"],
     "supportato": True},
    {"id": "EC", "titolo": "Attivo ereditario catasto fabbricati", "gruppo": "quadri", "vista": "tabella", "coll": "beni",
     "preset": {"tipo": "fabbricato"},
     "colonne": ["comune", "sezione", "foglio", "particella", "subalterno", "categoria", "diritto", "quota_defunto", "rendita", "valore", "provenienza"],
     "supportato": True},
    {"id": "ER", "titolo": "Rendite, crediti e altri beni", "gruppo": "quadri", "vista": "tabella", "coll": "beni",
     "preset": {"tipo": "disponibilita_finanziaria"},
     "colonne": ["tipo", "descrizione", "valore", "quota_defunto", "provenienza"], "supportato": True},
    {"id": "ED", "titolo": "Passività ed altri oneri", "gruppo": "quadri", "vista": "tabella", "coll": "passivita",
     "preset": {}, "colonne": ["descrizione", "importo", "persona_id"], "supportato": True},
    {"id": "EF", "titolo": "Liquidazione delle imposte e altri tributi", "gruppo": "quadri", "vista": "non_supportato",
     "supportato": False, "generato": True, "motivo": "quadro generato automaticamente dal programma: non si compila"},
    {"id": "EG", "titolo": "Elenco documenti, certificati e dichiarazioni sostitutive", "gruppo": "quadri",
     "vista": "documenti", "coll": "documenti_ref", "preset": {}, "colonne": ["allegato_id", "tipo_eg", "finalita", "persona_id"],
     "supportato": True},
    {"id": "EI", "titolo": "Dichiarazioni utili alla voltura catastale", "gruppo": "quadri", "vista": "derivato",
     "supportato": False, "generato": True, "motivo": "quadro generato automaticamente dal programma: non si compila",
     "nota": "Il quadro EI si genera da solo: nei beni dei quadri EB ed EC spunta «discordanza dati intestatario» o «passaggi senza atti legali» e, per la discordanza, indica gli estremi di trascrizione o registrazione degli atti (dati degli estremi: oggi da MCP o API)."},
    {"id": "EL", "titolo": "Attivo ereditario terreni sistema tavolare", "gruppo": "quadri", "vista": "tabella", "coll": "beni",
     "preset": {"tipo": "terreno", "provincia": "BZ"},
     "colonne": ["comune", "foglio", "particella", "partita_tavolare", "valore", "quota_defunto"], "supportato": True},
    {"id": "EM", "titolo": "Attivo ereditario fabbricati sistema tavolare", "gruppo": "quadri", "vista": "tabella", "coll": "beni",
     "preset": {"tipo": "fabbricato", "provincia": "BZ"},
     "colonne": ["comune", "foglio", "particella", "categoria", "valore", "quota_defunto"], "supportato": True},
    {"id": "EN", "titolo": "Aziende", "gruppo": "quadri", "vista": "tabella", "coll": "beni", "preset": {"tipo": "azienda"},
     "colonne": ["descrizione", "codice_fiscale_emittente", "valore", "quota_defunto"], "supportato": True},
    {"id": "EO", "titolo": "Azioni, Obbligazioni, Altri titoli, Quote sociali", "gruppo": "quadri", "vista": "tabella", "coll": "beni",
     "preset": {"tipo": "titolo"},
     "colonne": ["tipo_titolo", "descrizione", "quantita", "valore", "quota_defunto"], "supportato": True},
    {"id": "EP", "titolo": "Aeromobili", "gruppo": "quadri", "vista": "tabella", "coll": "beni", "preset": {"tipo": "aeromobile"},
     "colonne": ["marca_modello", "anno_costruzione", "valore", "quota_defunto"], "supportato": True},
    {"id": "EQ", "titolo": "Navi e Imbarcazioni", "gruppo": "quadri", "vista": "tabella", "coll": "beni", "preset": {"tipo": "nave"},
     "colonne": ["tipo_unita", "nazionalita", "numero_iscrizione", "valore", "quota_defunto"], "supportato": True},
    {"id": "EH", "titolo": "Dichiarazioni sostitutive, agevolazioni e riduzioni", "gruppo": "riepiloghi", "vista": "non_supportato",
     "supportato": False, "generato": True, "motivo": "quadro generato automaticamente dal programma: non si compila"},
    {"id": "EE", "titolo": "Prospetto riepilogativo asse ereditario", "gruppo": "riepiloghi", "vista": "non_supportato",
     "supportato": False, "generato": True, "motivo": "quadro generato automaticamente dal programma: non si compila"},
    {"id": "DV", "titolo": "Devoluzioni e quote", "gruppo": "lavoro", "vista": "tabella", "coll": "devoluzioni", "preset": {},
     "colonne": ["bene_id", "persona_id", "quota", "diritto"], "supportato": True,
     "nota": "Tabella di lavoro: collega ogni bene agli aventi diritto. Non è un quadro ministeriale."},
]
PER_ID = {q["id"]: q for q in QUADRI}
#: campi di un bene mostrati nell'ispettore per ciascun quadro (gli altri restano nel modello ma non si propongono; un campo
#: gia' valorizzato si mostra sempre)
_BASE = ["tipo", "descrizione", "valore", "diritto", "quota_defunto"]
_IMM = ["comune", "foglio", "particella", "subalterno", "provincia", "codice_comune", "comune_amministrativo",
        "codice_comune_amministrativo", "data_visura", "provenienza"]
_TAV = ["comune_catastale", "codice_comune_catastale", "partita_tavolare", "corpo_tavolare", "sistema_tavolare"]
CAMPI_BENI = {
    "EB": _BASE + _IMM + ["natura", "tipologia_terreno", "reddito_dominicale", "rendita", "discordanza_intestatario", "passaggi_senza_atti_legali"],
    "EC": _BASE + _IMM + ["sezione", "categoria", "rendita", "indirizzo", "classe", "zona_censuaria", "consistenza",
                          "discordanza_intestatario", "passaggi_senza_atti_legali"],
    "EL": _BASE + _IMM + ["natura", "tipologia_terreno", "reddito_dominicale", "rendita"] + _TAV,
    "EM": _BASE + _IMM + ["sezione", "categoria", "rendita", "indirizzo", "classe", "zona_censuaria", "consistenza",
                          "porzione_materiale"] + _TAV,
    "EN": _BASE + ["codice_fiscale_emittente", "inventario", "data_redazione_inventario"],
    "EO": _BASE + ["tipo_titolo", "quantita", "codice_titolo", "codice_fiscale_emittente", "tipo_documento", "data_documento"],
    "EP": _BASE + ["marca_modello", "anno_costruzione", "nazionalita", "anno_immatricolazione", "numero_immatricolazione"],
    "EQ": _BASE + ["tipo_unita", "nazionalita", "sigla_ufficio_iscrizione", "anno_iscrizione", "numero_iscrizione",
                   "anno_costruzione", "lunghezza", "stazza"],
    "ER": _BASE + ["tipo_cespite", "provenienza"],
}
for _q in QUADRI:
    if _q["id"] in CAMPI_BENI:
        _q["campi"] = CAMPI_BENI[_q["id"]]
    if _q.get("colonne"):   # colonne e campi nell'ordine dei moduli ufficiali (etichette.ORDINE)
        _q["colonne"] = ordina(_q["id"], _q["colonne"])
    if _q.get("campi"):
        _q["campi"] = ordina(_q["id"], _q["campi"])

SEMPRE_ATTIVI = ("AN", "DV")
PREDEFINITI = ("EA", "EB", "EC", "ER", "ED", "EG")


#: province con catasto tavolare esclusivo (non compaiono in reg:PENonTavolare_Type): i loro immobili vanno in EL/EM
PROVINCE_TAVOLARI = ("BZ", "TN", "GO", "TS")


def quadro_di(coll: str, entita: dict) -> str | None:
    if coll == "persone":
        return "AN" if entita.get("ruolo") in ("defunto", "presentatore") else "EA"
    if coll == "beni":
        tavolare = (str(entita.get("provincia") or "").strip().upper() in PROVINCE_TAVOLARI
                    or str(entita.get("sistema_tavolare") or "").strip().lower() in ("1", "si", "true"))
        if tavolare and entita.get("tipo") in ("terreno", "fabbricato"):
            return "EL" if entita.get("tipo") == "terreno" else "EM"
        return {"terreno": "EB", "fabbricato": "EC", "titolo": "EO", "aeromobile": "EP", "nave": "EQ", "azienda": "EN"}.get(entita.get("tipo"), "ER")
    return {"passivita": "ED", "documenti_ref": "EG", "devoluzioni": "DV"}.get(coll)


def attivi(dati: dict) -> set[str]:
    sel = dati.get("opzioni", {}).get("quadri_attivi")
    base = set(PREDEFINITI) if sel is None else {x for x in sel if x in PER_ID}
    return base | set(SEMPRE_ATTIVI)


def _quadro_da_percorso(dati: dict, percorso: str) -> str | None:
    import re
    m = re.match(r"^([a-z_]+)\[(?:bene=)?([^\]\],]+)", percorso)
    if not m:
        return "AN" if percorso.startswith("persone") else None
    coll, eid = m.groups()
    if coll == "devoluzioni":
        return "DV"
    for e in dati.get(coll, []):
        if e["id"] == eid:
            return quadro_di(coll, e)
    return quadro_di(coll, {}) if coll in ("passivita", "documenti_ref") else None


FONTE_VISURA = ("Succ_FASCICOLO_I_Nov_23.pdf pp. PDF 20 e 28: i dati catastali si ricavano dalla visura catastale risalente a non "
                "piu' di tre mesi prima della data di presentazione della dichiarazione")


def rilievi_visure(dati: dict, giorni: int = 90, oggi=None) -> list[Errore]:
    """Visure catastali mancanti di data o piu' vecchie di ``giorni`` (rispetto a ``oggi``) per i beni immobili dei quadri attivi.
    Non e' un controllo ufficiale: il termine decorre dalla presentazione, qui si usa la data odierna. Chi chiama decide se
    trattarli come avvisi o come rilievi bloccanti."""
    from datetime import date
    oggi = oggi or date.today()
    att = attivi(dati)
    out: list[Errore] = []
    for b in dati.get("beni", []):
        if b.get("tipo") not in ("fabbricato", "terreno") or quadro_di("beni", b) not in att:
            continue
        perc = f"beni[{b['id']}].data_visura"
        d = b.get("data_visura")
        if not d or not isinstance(d, str):
            out.append(Errore("VISURA_SENZA_DATA", perc, "indicare la data della visura catastale da cui derivano i dati "
                              f"dell'immobile (al massimo {giorni} giorni prima della presentazione)", FONTE_VISURA))
            continue
        try:
            eta = (oggi - date.fromisoformat(d)).days
        except ValueError:
            continue    # il formato errato lo segnala gia' la validazione di forma
        if eta > giorni:
            out.append(Errore("VISURA_VECCHIA", perc, f"la visura catastale ha {eta} giorni (limite {giorni}): serve una visura piu' "
                              "recente prima di presentare", FONTE_VISURA))
    return out


def quadro_per_percorso(dati: dict, percorso: str) -> str:
    if percorso.startswith("quadro["):
        return percorso[7:-1]
    return _quadro_da_percorso(dati, percorso) or "AN"


def rilievi_quadri(dati: dict) -> list[Errore]:
    """Un quadro attivo ma non supportato blocca la finalizzazione; dati in quadri inattivi vengono segnalati."""
    out = []
    att = attivi(dati)
    for q in QUADRI:
        if q["id"] in att and not q["supportato"]:
            out.append(Errore("QUADRO_NON_SUPPORTATO", f"quadro[{q['id']}]",
                              f"il quadro {q['id']} è selezionato ma non ancora supportato ({q.get('motivo', '')}): "
                              "la bozza è conservata, la pratica non è finalizzabile", "docs/MATRICE_COPERTURA.md"))
    from .telematico import sostitutiva as _sost   # import locale: il pacchetto telematico importa questo modulo
    for cod, perc, msg, fonte in _sost.rilievi(dati):
        out.append(Errore(cod, perc, msg + ": la pratica non e' finalizzabile", fonte))
    for coll in ("persone", "beni", "passivita", "documenti_ref"):
        for e in dati.get(coll, []):
            qid = quadro_di(coll, e)
            if qid and qid not in att:
                out.append(Errore("DATI_IN_QUADRO_NON_ATTIVO", f"{coll}[{e['id']}]",
                                  f"ci sono dati nel quadro {qid} ma il quadro non è selezionato"))
    return out


def stato_quadri(dati: dict, rilievi: list[dict]) -> list[dict]:
    att = attivi(dati)
    per_q: dict[str, list[dict]] = {}
    for r in rilievi:
        per_q.setdefault(quadro_per_percorso(dati, r["percorso"]), []).append(r)
    out = []
    for q in QUADRI:
        qid = q["id"]
        righe = 0
        if q.get("coll"):
            righe = sum(1 for e in dati.get(q["coll"], []) if quadro_di(q["coll"], e) == qid)
        elif qid == "AN":
            righe = sum(1 for e in dati.get("persone", []) if e.get("ruolo") in ("defunto", "presentatore"))
        n_ril = len(per_q.get(qid, []))
        if not q["supportato"]:
            stato = "non_supportato" if qid in att else "inattivo"
        elif qid not in att:
            stato = "inattivo"
        elif n_ril:
            stato = "rilievi"
        elif righe:
            stato = "compilato"
        else:
            stato = "vuoto"
        d = {k: v for k, v in q.items()}
        d.update({"stato": stato, "righe": righe, "rilievi": n_ril, "attivo": qid in att})
        out.append(d)
    return out
