"""Casi SINTETICI per i test del modulo telematico (dati inventati, codici fiscali solo formalmente plausibili).

Non sono dichiarazioni reali e non vanno mai trasmesse. Il codice fiscale rispetta il pattern di DatoCF_Type ma il
carattere di controllo non e' verificato: il controllo ufficiale e l'Anagrafe tributaria lo rifiuterebbero.
"""
from __future__ import annotations

import copy
from datetime import date

from successioni.telematico.esporta import ContestoExport

CF_DEFUNTO = "RSSMRA40A01H501W"
CF_ANNA = "RSSNNA70A41H501X"
CF_LUCA = "RSSLCU72B02H501Y"


def caso_completo() -> dict:
    """Defunto vedovo, due figli eredi per legge, un fabbricato, un terreno, un conto corrente, due passivita'."""
    return {
        "persone": [
            {"id": "p_defunto1", "_origine": {}, "cognome": "Rossi", "nome": "Mario", "codice_fiscale": CF_DEFUNTO,
             "data_nascita": "1940-01-01", "luogo_nascita": "Roma", "ruolo": "defunto", "data_decesso": "2025-03-10"},
            {"id": "p_anna0001", "_origine": {}, "cognome": "Rossi", "nome": "Anna", "codice_fiscale": CF_ANNA,
             "data_nascita": "1970-01-01", "luogo_nascita": "Roma", "ruolo": "erede", "relazione_con_defunto": "figlia"},
            {"id": "p_luca0001", "_origine": {}, "cognome": "Rossi", "nome": "Luca", "codice_fiscale": CF_LUCA,
             "data_nascita": "1972-02-02", "luogo_nascita": "Roma", "ruolo": "erede", "relazione_con_defunto": "02"},
        ],
        "beni": [
            {"id": "b_casa0001", "_origine": {}, "tipo": "fabbricato", "comune": "Roma", "foglio": "100",
             "particella": "200", "subalterno": "3", "categoria": "A/2", "rendita": "1000.00", "valore": "126000",
             "diritto": "proprieta", "quota_defunto": {"num": 1, "den": 1}, "provenienza": "atto 1990 (nota interna)"},
            {"id": "b_terr0001", "_origine": {}, "tipo": "terreno", "comune": "Roma", "foglio": "10", "particella": "20",
             "valore": "15000", "diritto": "1", "quota_defunto": {"num": 1, "den": 2}},
            {"id": "b_conto001", "_origine": {}, "tipo": "disponibilita_finanziaria",
             "descrizione": "Conto corrente n. 123 c/o Banca Esempio, saldo alla data del decesso",
             "valore": "20000", "diritto": "1", "quota_defunto": "1/1"},
        ],
        "devoluzioni": [
            {"id": "d_casaanna", "_origine": {}, "bene_id": "b_casa0001", "persona_id": "p_anna0001",
             "quota": {"num": 1, "den": 2}, "diritto": "1"},
            {"id": "d_casaluca", "_origine": {}, "bene_id": "b_casa0001", "persona_id": "p_luca0001",
             "quota": {"num": 1, "den": 2}, "diritto": "1"},
            {"id": "d_terranna", "_origine": {}, "bene_id": "b_terr0001", "persona_id": "p_anna0001", "quota": "1/2",
             "diritto": "proprieta"},
            {"id": "d_terrluca", "_origine": {}, "bene_id": "b_terr0001", "persona_id": "p_luca0001", "quota": "1/2",
             "diritto": "proprieta"},
            {"id": "d_contanna", "_origine": {}, "bene_id": "b_conto001", "persona_id": "p_anna0001",
             "quota": {"num": 1, "den": 3}, "diritto": "1"},
            {"id": "d_contluca", "_origine": {}, "bene_id": "b_conto001", "persona_id": "p_luca0001",
             "quota": {"num": 2, "den": 3}, "diritto": "1"},
        ],
        "passivita": [
            {"id": "ps_medic01", "_origine": {}, "descrizione": "Spese mediche ultimi sei mesi", "importo": "2000",
             "persona_id": "p_anna0001"},
            {"id": "ps_mutuo01", "_origine": {}, "descrizione": "Mutuo ipotecario residuo", "importo": "30000",
             "persona_id": "p_luca0001"},
        ],
        "documenti_ref": [],
        "opzioni": {"telematico": {
            "dichiarazione": {"stato_civile": "4", "devoluzione_per_legge": True, "firma_dichiarante": True,
                              "presentatore": {"persona_id": "p_anna0001", "codice_carica": "1",
                                               "telefono": "0612345678"}},
            "persone": {"p_defunto1": {"sesso": "M", "provincia_nascita": "RM"},
                        "p_anna0001": {"sesso": "F", "provincia_nascita": "RM", "grado_parentela": "02"},
                        "p_luca0001": {"sesso": "M", "provincia_nascita": "RM"}},
            "beni": {"b_casa0001": {"provincia": "RM", "codice_comune": "H501", "codice_comune_amministrativo": "H501",
                                    "indirizzo": "Via Esempio 1", "classe": "3", "consistenza": "5.5"},
                     "b_terr0001": {"provincia": "RM", "codice_comune": "H501", "codice_comune_amministrativo": "H501",
                                    "natura": "T", "tipologia_terreno": "3", "reddito_dominicale": "12.34",
                                    "superficie": {"ettari": 1, "are": 20, "centiare": 0}},
                     "b_conto001": {"tipo_cespite": "CR"}},
            "passivita": {"ps_medic01": {"tipo": "1", "estremi_documento": "Fatture 1-5/2025",
                                         "data_documento": "2025-02-28", "possesso": {"num": 1, "den": 1}},
                          "ps_mutuo01": {"tipo": "3", "estremi_documento": "Contratto mutuo rep. 123",
                                         "data_documento": "2010-05-05", "possesso": "1/1", "bene_id": "b_casa0001"}},
        }},
        "note": {"promemoria": "nota interna non esportata"},
    }


def contesto(**kw) -> ContestoExport:
    base = {"cf_fornitore": CF_ANNA, "tipo_fornitore": "1", "data_riferimento": date(2026, 11, 1)}
    base.update(kw)
    return ContestoExport(**base)


def copia(d: dict) -> dict:
    return copy.deepcopy(d)
