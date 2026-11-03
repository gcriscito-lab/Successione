import pytest

from successioni.telematico.supplemento import (
    attr,
    chiavi_non_gestite,
    dich,
    presentatore_sup,
    sup,
)
from successioni.valori import ValoreNonValido, parse_importo, parse_quota


def test_sup_gestione_struttura():
    assert sup({}) == {}
    assert sup({"opzioni": None}) == {}
    assert sup({"opzioni": {"telematico": "non_un_dict"}}) == {}
    dati = {"opzioni": {"telematico": {"dichiarazione": {"stato_civile": "CONIUGATO"}}}}
    assert sup(dati) == {"dichiarazione": {"stato_civile": "CONIUGATO"}}


def test_attr_precedenza_entita():
    dati = {
        "opzioni": {
            "telematico": {
                "persone": {
                    "P1": {"sesso": "F", "provincia_nascita": "RM"}
                }
            }
        }
    }
    # Il valore presente sull'entita' ha precedenza su opzioni.telematico
    entita = {"id": "P1", "sesso": "M"}
    assert attr(dati, "persone", entita, "sesso") == "M"

    # Se il valore e' assente sull'entita', si recupera da telematico
    assert attr(dati, "persone", entita, "provincia_nascita") == "RM"


def test_attr_stati_dato():
    dati = {
        "opzioni": {
            "telematico": {
                "persone": {
                    "P1": {
                        "sesso": {"stato": "assente"},
                        "provincia_nascita": {"stato": "non_applicabile"},
                        "tipo_soggetto": {"stato": "da_confermare"},
                        "grado_parentela": {"stato": "zero"},
                    }
                }
            }
        }
    }
    ent = {"id": "P1"}
    # assente e non_applicabile restituiscono None
    assert attr(dati, "persone", ent, "sesso") is None
    assert attr(dati, "persone", ent, "provincia_nascita") is None

    # da_confermare e zero restituiscono il dizionario dello stato
    assert attr(dati, "persone", ent, "tipo_soggetto") == {"stato": "da_confermare"}
    assert attr(dati, "persone", ent, "grado_parentela") == {"stato": "zero"}

    # Verifico lo stesso comportamento con stati presenti direttamente sull'entita'
    assert attr(dati, "persone", {"id": "P1", "sesso": {"stato": "assente"}}, "sesso") is None
    assert attr(dati, "persone", {"id": "P1", "provincia_nascita": {"stato": "non_applicabile"}}, "provincia_nascita") is None
    assert attr(dati, "persone", {"id": "P1", "tipo_soggetto": {"stato": "da_confermare"}}, "tipo_soggetto") == {"stato": "da_confermare"}


def test_dich_e_presentatore_sup():
    dati = {
        "opzioni": {
            "telematico": {
                "dichiarazione": {
                    "stato_civile": "NUBILE",
                    "presentatore": {
                        "persona_id": "P1",
                        "codice_carica": "1",
                    },
                }
            }
        }
    }
    assert dich(dati, "stato_civile") == "NUBILE"
    assert dich(dati, "campo_inesistente") is None
    assert dich(dati, "campo_inesistente", default="VALORE_DEFAULT") == "VALORE_DEFAULT"

    pres = presentatore_sup(dati)
    assert pres == {"persona_id": "P1", "codice_carica": "1"}

    # Presentatore non valido (non dict) restituisce dict vuoto
    dati_invalid_pres = {"opzioni": {"telematico": {"dichiarazione": {"presentatore": "stringa"}}}}
    assert presentatore_sup(dati_invalid_pres) == {}


def test_chiavi_non_gestite_completo():
    dati = {
        "persone": [{"id": "P1"}],
        "beni": [{"id": "B1"}],
        "opzioni": {
            "telematico": {
                "sezione_sconosciuta": 123,
                "persone": {
                    "P1": {"sesso": "M", "campo_sconosciuto_p": True},
                    "P_INESISTENTE": {"sesso": "F"},
                },
                "beni": {
                    "B1": {"campo_sconosciuto_b": "val"}
                },
                "dichiarazione": {
                    "chiave_dich_extra": "abc",
                    "presentatore": {
                        "persona_id": "P1",
                        "extra_presentatore": 1,
                    },
                    "versamento": {
                        "iban": "IT123",
                        "extra_versamento": "err",
                    },
                    "testamento": {
                        "estero": False,
                        "extra_testamento": "err",
                    },
                },
            }
        },
    }

    esiti = chiavi_non_gestite(dati)
    assert "opzioni.telematico.sezione_sconosciuta" in esiti
    assert "opzioni.telematico.persone[P1].campo_sconosciuto_p" in esiti
    assert "opzioni.telematico.persone[P_INESISTENTE]: riferimento a un elemento inesistente" in esiti
    assert "opzioni.telematico.beni[B1].campo_sconosciuto_b" in esiti
    assert "opzioni.telematico.dichiarazione.chiave_dich_extra" in esiti
    assert "opzioni.telematico.dichiarazione.presentatore.extra_presentatore" in esiti
    assert "opzioni.telematico.dichiarazione.versamento.extra_versamento" in esiti
    assert "opzioni.telematico.dichiarazione.testamento.extra_testamento" in esiti
    assert esiti == sorted(esiti)


def test_casi_negativi_ed_eccezioni():
    # 1. attr con entita senza 'id' e valore mancante solleva KeyError per 'id'
    entita_senza_id = {"nome": "Mario"}
    dati = {"opzioni": {"telematico": {"persone": {}}}}
    with pytest.raises(KeyError) as exc_info:
        attr(dati, "persone", entita_senza_id, "sesso")
    assert "id" in str(exc_info.value)

    # 2. parse_importo rifiuta virgole
    with pytest.raises(ValoreNonValido, match="separatore decimale ',' non ammesso"):
        parse_importo("100,50")

    # 3. parse_importo rifiuta float
    with pytest.raises(ValoreNonValido, match="importo float non ammesso"):
        parse_importo(100.5)

    # 4. parse_quota rifiuta quota > 1
    with pytest.raises(ValoreNonValido, match="quota maggiore di 1"):
        parse_quota("3/2")
