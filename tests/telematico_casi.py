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
            # devoluzione per legge, due figli: 1/2 ciascuno (Fascicolo I p. 69, Allegato 5)
            {"id": "d_contanna", "_origine": {}, "bene_id": "b_conto001", "persona_id": "p_anna0001",
             "quota": {"num": 1, "den": 2}, "diritto": "1"},
            {"id": "d_contluca", "_origine": {}, "bene_id": "b_conto001", "persona_id": "p_luca0001",
             "quota": {"num": 1, "den": 2}, "diritto": "1"},
        ],
        "passivita": [
            {"id": "ps_medic01", "_origine": {}, "descrizione": "Spese mediche ultimi sei mesi", "importo": "2000",
             "persona_id": "p_anna0001"},
            # mutuo (tipo 3): ripartito per quote di legge (annotazione RipartizioneED/Ripartizione/Quota), vedi
            # opzioni.telematico.passivita.ps_mutuo01.ripartizione
            {"id": "ps_mutuo01", "_origine": {}, "descrizione": "Mutuo ipotecario residuo", "importo": "30000"},
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
                                         "data_documento": "2010-05-05", "possesso": "1/1", "bene_id": "b_casa0001",
                                         "ripartizione": [{"persona_id": "p_anna0001", "quota": "1/2"},
                                                          {"persona_id": "p_luca0001", "quota": "1/2"}]}},
        }},
        "note": {"promemoria": "nota interna non esportata"},
    }


def caso_a10() -> dict:
    """Caso base per la prova A10 con il controllo ufficiale (eseguito in locale): ``caso_completo`` con gli allegati
    del quadro EG (albero genealogico EG6 e documenti delle passivita' EG5, PDF/A-1b SINTETICI in
    tests/fixture_telematico/allegati/) e l'attestazione del dichiarante sulle copie (EH, FlagPassivita)."""
    d = caso_completo()
    d["documenti_ref"] = [
        {"id": "dr_albero1", "_origine": {}, "allegato_id": "al_albero", "tipo_eg": "AlberoGenealogico",
         "finalita": "Albero genealogico (sintetico)"},
        {"id": "dr_passiv1", "_origine": {}, "allegato_id": "al_passiv", "tipo_eg": "DocumentiPassivita",
         "finalita": "Fatture spese mediche e contratto di mutuo (sintetici)"},
    ]
    d["opzioni"]["telematico"]["dichiarazione"]["dichiara_copie_conformi"] = True
    return d


def caso_testamento() -> dict:
    """Successione testamentaria con soli eredi: ``caso_a10`` con devoluzione per testamento (sezione Testamento ed EG2)."""
    d = caso_a10()
    dich = d["opzioni"]["telematico"]["dichiarazione"]
    dich.pop("devoluzione_per_legge", None)
    dich["devoluzione_per_testamento"] = True
    dich["testamento"] = {"pubblico_ufficiale": "Notaio Sintetico", "data_pubblicazione": "2025-04-01",
                          "ufficio_registrazione": "795", "serie": "1T", "numero_registrazione": "123",
                          "data_registrazione": "2025-04-10"}
    d["documenti_ref"].append({"id": "dr_testam1", "_origine": {}, "allegato_id": "al_testam", "tipo_eg": "Testamento",
                               "finalita": "Testamento (sintetico)"})
    return d


def caso_testamento_legatario() -> dict:
    """``caso_testamento`` con un legatario estraneo (grado 35) cui va per intero un terreno in piena proprieta'."""
    d = caso_testamento()
    d["persone"].append({"id": "p_paolo001", "_origine": {}, "cognome": "Verdi", "nome": "Paolo",
                         "codice_fiscale": "VRDPLA80C03H501A", "data_nascita": "1980-03-03", "luogo_nascita": "Roma",
                         "ruolo": "legatario", "relazione_con_defunto": "estraneo"})
    d["beni"].append({"id": "b_terr0002", "_origine": {}, "tipo": "terreno", "comune": "Roma", "foglio": "11",
                      "particella": "21", "valore": "10000", "diritto": "1", "quota_defunto": "1/1"})
    d["devoluzioni"].append({"id": "d_terrpaol", "_origine": {}, "bene_id": "b_terr0002", "persona_id": "p_paolo001",
                             "quota": "1/1", "diritto": "1"})
    tel = d["opzioni"]["telematico"]
    tel["dichiarazione"]["tempistica_pagamento"] = "1"
    tel["persone"]["p_paolo001"] = {"sesso": "M", "provincia_nascita": "RM", "grado_parentela": "35"}
    tel["beni"]["b_terr0002"] = {"provincia": "RM", "codice_comune": "H501", "codice_comune_amministrativo": "H501",
                                 "natura": "T", "tipologia_terreno": "3", "reddito_dominicale": "5.00",
                                 "superficie": {"ettari": 0, "are": 50, "centiare": 0}}
    return d


def caso_testamento_legato() -> dict:
    """``caso_testamento_legatario`` con un legato (passivita' tipo 11, 2.000 euro) a carico dei due figli eredi, 1/2 ciascuno."""
    d = caso_testamento_legatario()
    d["passivita"].append({"id": "ps_legato1", "_origine": {}, "descrizione": "Legato di somma di denaro (sintetico)",
                           "importo": "2000"})
    d["opzioni"]["telematico"]["passivita"]["ps_legato1"] = {
        "tipo": "11", "estremi_documento": "Testamento olografo (sintetico)", "data_documento": "2024-06-01",
        "ripartizione": [{"persona_id": "p_anna0001", "quota": "1/2"}, {"persona_id": "p_luca0001", "quota": "1/2"}]}
    return d


ALLEGATI_A10 = {"al_albero": {"percorso": str(FIXTURE / "allegati" / "albero_genealogico.pdf"),
                              "nome": "albero_genealogico.pdf"},
                "al_passiv": {"percorso": str(FIXTURE / "allegati" / "documenti_passivita.pdf"),
                              "nome": "documenti_passivita.pdf"},
                "al_testam": {"percorso": str(FIXTURE / "allegati" / "testamento.pdf"), "nome": "testamento.pdf"}}


def contesto_caso_a10(**kw) -> ContestoExport:
    return contesto(allegati=ALLEGATI_A10, **kw)


def contesto(**kw) -> ContestoExport:
    base = {"cf_fornitore": CF_ANNA, "tipo_fornitore": "1", "data_riferimento": date(2026, 11, 1)}
    base.update(kw)
    return ContestoExport(**base)


def copia(d: dict) -> dict:
    return copy.deepcopy(d)
