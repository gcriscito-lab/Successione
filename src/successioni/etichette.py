"""Etichette italiane e ordine dei campi per l'interfaccia (e per ``/api/schema``).

Fonti: il modello SUC13 (Fascicolo I, descrizione dei quadri EA-ER e dei dati generali) e gli XSD SUC13_20250702
(``fonti/Specifiche tecniche``: nomi degli elementi, es. ``ComuneAmministrativo``, ``CodiceComune``, ``Quantita``,
``DataDocumento``). L'ORDINE dei campi segue la successione dei campi nel quadro del compilatore ufficiale, consultato in
locale solo per capire la sequenza (codice fiscale, tipo soggetto, ..., come nei moduli); le etichette qui sotto sono
scritte per questo programma, brevi, e non riproducono tabelle o testi del compilatore.

Nessuna regola fiscale e nessun codice sono definiti qui: i menu dei codici stanno in ``codici.py`` (dagli XSD).
La coerenza con ``schema.COLLEZIONI`` e con ``quadri.py`` e' verificata da ``tests/test_etichette.py``.
"""
from __future__ import annotations

# --- etichette dei campi per collezione (nome del campo del modello -> etichetta) ---------------------------------------
ETICHETTE: dict[str, dict[str, str]] = {
    "persone": {
        "cognome": "Cognome", "nome": "Nome", "codice_fiscale": "Codice fiscale",
        "data_nascita": "Data di nascita", "luogo_nascita": "Comune o Stato estero di nascita",
        "provincia_nascita": "Provincia di nascita", "sesso": "Sesso",
        "ruolo": "Ruolo nella successione", "tipo_soggetto": "Tipo di soggetto",
        "grado_parentela": "Grado di parentela", "relazione_con_defunto": "Relazione con il defunto",
        "data_decesso": "Data del decesso", "comune_decesso": "Comune del decesso",
        "provincia_decesso": "Provincia del decesso",
        "rappresentato_cf": "Rappresentato: codice fiscale", "rappresentato_grado": "Rappresentato: grado di parentela",
        "certificatore_disabilita": "Disabilità/interdizione: estremi del verbale o della sentenza",
    },
    "beni": {
        "tipo": "Tipo di bene", "descrizione": "Descrizione",
        "provincia": "Provincia", "comune": "Comune", "comune_amministrativo": "Comune amministrativo",
        "codice_comune": "Codice comune", "codice_comune_amministrativo": "Codice comune amministrativo",
        "indirizzo": "Indirizzo o localita'",
        "bene_estero": "Bene sito all'estero (1)", "imposta_estera": "Imposta versata all'estero (euro)",
        "codice_stato_estero": "Codice dello Stato estero", "stato_estero": "Stato estero",
        "stato_federato": "Stato federato, provincia o contea", "localita_estero": "Localita' estera",
        "sezione": "Sezione urbana", "foglio": "Foglio", "particella": "Particella",
        "particella_denominatore": "Denominatore della particella", "subalterno": "Subalterno",
        "zona_censuaria": "Zona censuaria", "categoria": "Categoria catastale", "classe": "Classe",
        "consistenza": "Consistenza (vani, mq, mc)", "rendita": "Rendita catastale",
        "natura": "Natura", "tipologia_terreno": "Tipologia del terreno", "reddito_dominicale": "Reddito dominicale",
        "diritto": "Diritto del defunto", "quota_defunto": "Quota del defunto", "valore": "Valore",
        "provenienza": "Provenienza", "data_visura": "Data della visura catastale",
        "discordanza_intestatario": "Discordanza dati intestatario", "passaggi_senza_atti_legali": "Passaggi senza atti legali",
        "comune_catastale": "Comune catastale", "codice_comune_catastale": "Codice comune catastale",
        "partita_tavolare": "Partita tavolare", "corpo_tavolare": "Corpo tavolare",
        "porzione_materiale": "Porzione materiale", "sistema_tavolare": "Sistema tavolare",
        "tipo_cespite": "Tipo di cespite",
        "tipo_titolo": "Tipo di titolo", "quantita": "Quantita'", "codice_titolo": "Codice titolo",
        "codice_fiscale_emittente": "Codice fiscale dell'emittente",
        "tipo_documento": "Tipo di documento", "data_documento": "Data del documento",
        "inventario": "Inventario", "data_redazione_inventario": "Data di redazione dell'inventario",
        "marca_modello": "Marca e modello", "anno_costruzione": "Anno di costruzione", "nazionalita": "Nazionalita'",
        "anno_immatricolazione": "Anno di immatricolazione", "numero_immatricolazione": "Numero di immatricolazione",
        "tipo_unita": "Tipo di unita'", "sigla_ufficio_iscrizione": "Sigla dell'ufficio di iscrizione",
        "anno_iscrizione": "Anno di iscrizione", "numero_iscrizione": "Numero di iscrizione",
        "lunghezza": "Lunghezza (in centimetri)", "stazza": "Stazza",
    },
    "devoluzioni": {
        "bene_id": "Bene", "persona_id": "Erede o legatario", "diritto": "Diritto dell'erede", "quota": "Quota dell'erede",
    },
    "passivita": {
        "tipo": "Tipo di passivita'", "descrizione": "Descrizione", "estremi_documento": "Estremi del documento",
        "data_documento": "Data del documento", "bene_id": "Bene collegato", "possesso": "Quota gravante sul defunto",
        "importo": "Importo", "persona_id": "Persona collegata",
    },
    "documenti_ref": {
        "allegato_id": "Allegato", "tipo_eg": "Tipo di documento (EG)", "finalita": "Finalita'",
        "persona_id": "Persona collegata",
    },
}
# Alcuni campi hanno nel modulo una dizione propria del quadro (per esempio il codice fiscale e' quello della societa' in EO).
ETICHETTE_QUADRO: dict[tuple[str, str], str] = {
    ("EN", "descrizione"): "Denominazione dell'azienda",
    ("EN", "codice_fiscale_emittente"): "Codice fiscale dell'azienda",
    ("EO", "codice_fiscale_emittente"): "Codice fiscale della societa'",
    ("EO", "descrizione"): "Descrizione del titolo",
    ("EO", "tipo_documento"): "Tipo di documento (azienda)",
    ("EB", "indirizzo"): "Via o localita'",
    ("EL", "indirizzo"): "Via o localita'",
    ("EM", "indirizzo"): "Via o localita'",
    ("ER", "valore"): "Valore",
    ("EL", "comune"): "Comune amministrativo",
    ("EM", "comune"): "Comune amministrativo",
}

# --- nomi leggibili dei valori ammessi dallo schema (enum) --------------------------------------------------------------
NOMI_VALORI: dict[str, dict[str, str]] = {
    "persone.ruolo": {
        "defunto": "Defunto", "erede": "Erede", "legatario": "Legatario", "rappresentante": "Rappresentante",
        "presentatore": "Presentatore", "altro": "Altro soggetto",
    },
    "persone.sesso": {"M": "Maschio", "F": "Femmina"},
    "beni.tipo": {
        "fabbricato": "Fabbricato", "terreno": "Terreno", "disponibilita_finanziaria": "Disponibilità finanziaria",
        "titolo": "Titolo (azioni, obbligazioni, quote)", "aeromobile": "Aeromobile", "nave": "Nave o imbarcazione",
        "azienda": "Azienda", "altro": "Altro bene",
    },
}

# --- dati della dichiarazione (opzioni.telematico.dichiarazione): chiave -> etichetta ------------------------------------
ETICHETTE_DICHIARAZIONE: dict[str, str] = {
    "stato_civile": "Stato civile del defunto",
    "devoluzione_per_legge": "Devoluzione per legge",
    "devoluzione_per_testamento": "Devoluzione per testamento",
    "testamento.estero": "Testamento estero",
    "testamento.pubblico_ufficiale": "Pubblico ufficiale",
    "testamento.data_pubblicazione": "Pubblicato il",
    "testamento.ufficio_registrazione": "Ufficio di registrazione",
    "testamento.serie": "Serie",
    "testamento.numero_registrazione": "Numero di registrazione",
    "testamento.sottonumero_registrazione": "Sottonumero",
    "testamento.data_registrazione": "Registrato il",
    "presentatore.persona_id": "Presentatore tra i soggetti della pratica",
    "presentatore.codice_carica": "Codice carica",
    "presentatore.telefono": "Telefono",
    "presentatore.email": "Indirizzo di posta elettronica",
    "tempistica_pagamento": "Tempistica del pagamento",
    "pagamento_rateale": "Numero di rate trimestrali (1-12)",
    "acconto": "Acconto dell'imposta di successione (euro, almeno il 20%)",
    "versamento.iban": "IBAN del versamento",
    "versamento.cf_titolare": "Codice fiscale del titolare del conto",
    "firma_dichiarante": "Firma del dichiarante",
    "dichiara_copie_conformi": "Dichiarazione di conformità delle copie allegate",
    "separazione_con_colpa": "Separazione con colpa del coniuge superstite (stato civile 5)",
    "no_scioglimento_unione_civile": "Nessuna domanda di scioglimento dell'unione civile (stato civile 7)",
    "reintegro_1.ufficio_registrazione": "Reintegro dei diritti di legittima 1: ufficio di registrazione",
    "reintegro_1.serie": "Reintegro dei diritti di legittima 1: serie",
    "reintegro_1.numero_registrazione": "Reintegro dei diritti di legittima 1: numero",
    "reintegro_1.sottonumero_registrazione": "Reintegro dei diritti di legittima 1: sottonumero",
    "reintegro_1.data_registrazione": "Reintegro dei diritti di legittima 1: data di registrazione",
    "reintegro_2.ufficio_registrazione": "Reintegro dei diritti di legittima 2: ufficio di registrazione",
    "reintegro_2.serie": "Reintegro dei diritti di legittima 2: serie",
    "reintegro_2.numero_registrazione": "Reintegro dei diritti di legittima 2: numero",
    "reintegro_2.sottonumero_registrazione": "Reintegro dei diritti di legittima 2: sottonumero",
    "reintegro_2.data_registrazione": "Reintegro dei diritti di legittima 2: data di registrazione",
    "reintegro_3.ufficio_registrazione": "Reintegro dei diritti di legittima 3: ufficio di registrazione",
    "reintegro_3.serie": "Reintegro dei diritti di legittima 3: serie",
    "reintegro_3.numero_registrazione": "Reintegro dei diritti di legittima 3: numero",
    "reintegro_3.sottonumero_registrazione": "Reintegro dei diritti di legittima 3: sottonumero",
    "reintegro_3.data_registrazione": "Reintegro dei diritti di legittima 3: data di registrazione",
    "codice_sostitutiva": "Tipo di sostitutiva (codice)",
    "prima_anno": "Prima dichiarazione: anno",
    "prima_volume": "Prima dichiarazione: volume",
    "prima_numero": "Prima dichiarazione: numero",
    "ipotecaria_versata": "Imposta ipotecaria già versata (EF6)",
    "catastale_versata": "Imposta catastale già versata (EF12)",
    "successione_versata": "Imposta di successione già versata (EF18bis col. 3)",
    "circoscrizioni_nuove": "Circoscrizioni delle nuove trascrizioni (solo codice 1)",
    "azienda_data_deposito": "Azienda: data di deposito",
    "azienda_camera_commercio": "Azienda: camera di commercio",
}

# --- ordine dei campi per quadro (come nel modulo: identificazione, ubicazione, dati catastali, diritto, valori) ----------
# Chiavi: id del quadro; «AN» = anagrafica del defunto, «AN.presentatore» = anagrafica del presentatore,
# «AN.dichiarazione» = dati della dichiarazione (chiavi di ETICHETTE_DICHIARAZIONE).
_UBIC = ["provincia", "comune", "comune_amministrativo", "codice_comune", "codice_comune_amministrativo", "indirizzo"]
_ESTERO_IMM = ["codice_stato_estero", "stato_estero", "stato_federato", "localita_estero", "imposta_estera"]
_TAVOLARE = ["comune_catastale", "codice_comune_catastale", "partita_tavolare", "corpo_tavolare", "sistema_tavolare"]
_DIRITTO_VALORE = ["diritto", "quota_defunto", "valore"]
ORDINE: dict[str, list[str]] = {
    "AN": ["codice_fiscale", "cognome", "nome", "sesso", "data_nascita", "provincia_nascita", "luogo_nascita",
           "data_decesso", "provincia_decesso", "comune_decesso"],
    "AN.presentatore": ["codice_fiscale", "cognome", "nome", "sesso", "data_nascita", "provincia_nascita", "luogo_nascita",
                        "relazione_con_defunto"],
    "AN.dichiarazione": list(ETICHETTE_DICHIARAZIONE),
    "EA": ["codice_fiscale", "ruolo", "tipo_soggetto", "grado_parentela", "relazione_con_defunto", "cognome", "nome",
           "provincia_nascita", "luogo_nascita", "data_nascita", "sesso", "rappresentato_cf", "rappresentato_grado"],
    "EB": ["tipo", "descrizione"] + _UBIC + _ESTERO_IMM + ["sezione", "foglio", "particella", "subalterno", "natura", "tipologia_terreno",
           "reddito_dominicale", "rendita"] + _DIRITTO_VALORE + ["data_visura", "provenienza", "discordanza_intestatario",
           "passaggi_senza_atti_legali"],
    "EC": ["tipo", "descrizione"] + _UBIC + _ESTERO_IMM + ["sezione", "foglio", "particella", "subalterno", "zona_censuaria", "categoria",
           "classe", "consistenza", "rendita"] + _DIRITTO_VALORE + ["data_visura", "provenienza", "discordanza_intestatario",
           "passaggi_senza_atti_legali"],
    "ED": ["tipo", "descrizione", "estremi_documento", "data_documento", "bene_id", "possesso", "importo", "persona_id"],
    "EG": ["allegato_id", "tipo_eg", "finalita", "persona_id"],
    "EL": ["tipo", "descrizione"] + _UBIC + _TAVOLARE[:2] + ["foglio", "particella", "particella_denominatore", "subalterno", "natura",
           "tipologia_terreno", "reddito_dominicale", "rendita"] + _DIRITTO_VALORE + ["partita_tavolare", "corpo_tavolare",
           "sistema_tavolare", "data_visura", "provenienza"],
    "EM": ["tipo", "descrizione"] + _UBIC + _TAVOLARE[:2] + ["partita_tavolare", "corpo_tavolare", "porzione_materiale",
           "sezione", "foglio", "particella", "particella_denominatore", "subalterno", "zona_censuaria", "categoria", "classe", "consistenza", "rendita"]
          + _DIRITTO_VALORE + ["sistema_tavolare", "data_visura", "provenienza"],
    "EN": ["tipo", "descrizione", "codice_fiscale_emittente", "inventario", "data_redazione_inventario"] + _DIRITTO_VALORE
          + ["bene_estero", "imposta_estera"],
    "EO": ["tipo", "tipo_titolo", "codice_fiscale_emittente", "quantita", "codice_titolo", "descrizione", "tipo_documento",
           "data_documento"] + _DIRITTO_VALORE + ["bene_estero", "imposta_estera"],
    "EP": ["tipo", "marca_modello", "anno_costruzione", "nazionalita", "anno_immatricolazione", "numero_immatricolazione",
           "descrizione"] + _DIRITTO_VALORE + ["bene_estero", "imposta_estera"],
    "EQ": ["tipo", "tipo_unita", "nazionalita", "sigla_ufficio_iscrizione", "anno_iscrizione", "numero_iscrizione",
           "anno_costruzione", "lunghezza", "stazza", "descrizione"] + _DIRITTO_VALORE + ["bene_estero", "imposta_estera"],
    "ER": ["tipo", "tipo_cespite", "descrizione"] + _DIRITTO_VALORE + ["bene_estero", "imposta_estera", "provenienza"],
    "DV": ["bene_id", "persona_id", "diritto", "quota"],
}
# Collezione dei campi elencati da ciascun quadro (per i controlli di coerenza e per l'interfaccia).
COLLEZIONE_QUADRO: dict[str, str] = {
    "AN": "persone", "AN.presentatore": "persone", "EA": "persone", "ED": "passivita", "EG": "documenti_ref",
    "DV": "devoluzioni", **{q: "beni" for q in ("EB", "EC", "EL", "EM", "EN", "EO", "EP", "EQ", "ER")},
}


def etichetta(coll: str, campo: str, quadro: str | None = None) -> str:
    """Etichetta italiana di un campo; se manca, il nome del campo con gli spazi (mai con il trattino basso)."""
    if quadro and (quadro, campo) in ETICHETTE_QUADRO:
        return ETICHETTE_QUADRO[(quadro, campo)]
    return ETICHETTE.get(coll, {}).get(campo) or campo.replace("_", " ").capitalize()


def nome_valore(coll: str, campo: str, valore: str) -> str:
    """Nome leggibile di un valore enum (es. beni.tipo ``disponibilita_finanziaria`` -> «Disponibilità finanziaria»)."""
    return NOMI_VALORI.get(f"{coll}.{campo}", {}).get(valore) or valore


def ordina(quadro: str, campi) -> list[str]:
    """I campi dati, nell'ordine del quadro; quelli non previsti dall'ordine vanno in coda, nell'ordine di arrivo."""
    ordine = ORDINE.get(quadro, [])
    campi = list(campi)
    return sorted(campi, key=lambda c: (ordine.index(c) if c in ordine else len(ordine)))


def per_api() -> dict:
    """Struttura esposta da ``/api/schema`` nelle chiavi ``etichette`` e ``ordine``."""
    return {
        "etichette": {
            "campi": ETICHETTE,
            "quadro": {f"{q}.{c}": t for (q, c), t in ETICHETTE_QUADRO.items()},
            "dichiarazione": ETICHETTE_DICHIARAZIONE,
            "valori": NOMI_VALORI,
        },
        "ordine": ORDINE,
    }
