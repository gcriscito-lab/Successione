"""Casi SINTETICI per i test del modulo telematico (dati inventati).

Non sono dichiarazioni reali e non vanno mai trasmesse. I codici fiscali sono generati da
``successioni.telematico.identificativi.genera_cf_sintetico`` (carattere di controllo verificato con i componenti
ufficiali checkCF_PIVA.jar: tests/fixture_telematico/cf_lotto_esito_componente.txt): sono formalmente validi ma non
attribuiti a persone reali (non verificati in Anagrafe tributaria).
"""
from __future__ import annotations

import copy
from datetime import date
from pathlib import Path

from successioni.telematico.esporta import ContestoExport

CF_DEFUNTO = "RSSMRA40A01H501K"   # genera_cf_sintetico("Rossi", "Mario", "M", "1940-01-01", "H501")
CF_ANNA = "RSSNNA70A41H501J"      # genera_cf_sintetico("Rossi", "Anna", "F", "1970-01-01", "H501")
CF_LUCA = "RSSLCU72B02H501O"      # genera_cf_sintetico("Rossi", "Luca", "M", "1972-02-02", "H501")
IBAN_SINTETICO = "IT57A0123456789000000001234"  # ABI/CAB/conto inventati
FIXTURE = Path(__file__).parent / "fixture_telematico"


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
                                               "telefono": "0612345678"},
                              # addebito delle imposte autoliquidate (EF19): IBAN SINTETICO, cifre di controllo
                              # modulo 97 corrette e accettato da CheckIBAN di controlliXMLREG2013.jar
                              # (tests/fixture_telematico/iban_esito_componente.txt); titolare = dichiarante
                              "versamento": {"iban": IBAN_SINTETICO, "cf_titolare": CF_ANNA}},
            "persone": {"p_defunto1": {"sesso": "M", "provincia_nascita": "RM", "comune_decesso": "Roma",
                                       "provincia_decesso": "RM"},
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


def caso_a10() -> dict:
    """Caso base per la prova A10 con il controllo ufficiale (eseguito in locale): come ``caso_completo`` ma con le
    quote di legge sul conto (due figli: 1/2 ciascuno; il controllo segnala (***) 'Dati di devoluzione non coerenti
    con quelli relativi agli Eredi' con 1/3 - 2/3) e con gli allegati del quadro EG (albero genealogico EG6 e
    documenti delle passivita' EG5, PDF sintetici in tests/fixture_telematico/allegati/)."""
    d = caso_completo()
    for dv in d["devoluzioni"]:
        if dv["bene_id"] == "b_conto001":
            dv["quota"] = {"num": 1, "den": 2}
    d["documenti_ref"] = [
        {"id": "dr_albero1", "_origine": {}, "allegato_id": "al_albero", "tipo_eg": "AlberoGenealogico",
         "finalita": "Albero genealogico (sintetico)"},
        {"id": "dr_passiv1", "_origine": {}, "allegato_id": "al_passiv", "tipo_eg": "DocumentiPassivita",
         "finalita": "Fatture spese mediche e contratto di mutuo (sintetici)"},
    ]
    d["opzioni"]["telematico"]["dichiarazione"]["dichiara_copie_conformi"] = True
    return d


ALLEGATI_A10 = {"al_albero": {"percorso": str(FIXTURE / "allegati" / "albero_genealogico.pdf"),
                              "nome": "albero_genealogico.pdf"},
                "al_passiv": {"percorso": str(FIXTURE / "allegati" / "documenti_passivita.pdf"),
                              "nome": "documenti_passivita.pdf"}}


def contesto_caso_a10(**kw) -> ContestoExport:
    return contesto(allegati=ALLEGATI_A10, **kw)


def contesto(**kw) -> ContestoExport:
    base = {"cf_fornitore": CF_ANNA, "tipo_fornitore": "1", "data_riferimento": date(2026, 11, 1)}
    base.update(kw)
    return ContestoExport(**base)


def copia(d: dict) -> dict:
    return copy.deepcopy(d)
