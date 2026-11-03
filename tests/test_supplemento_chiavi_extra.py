import importlib
import pytest

from successioni.telematico.supplemento import chiavi_non_gestite, attr
from telematico_casi import (
    caso_completo,
    caso_azienda,
    caso_voltura,
    caso_tavolare,
    caso_testamento,
    copia,
)


def test_chiavi_non_gestite_allowed_azienda_keys():
    d = copia(caso_azienda())
    ng = chiavi_non_gestite(d)
    assert "opzioni.telematico.dichiarazione.azienda_data_deposito" not in ng
    assert "opzioni.telematico.dichiarazione.azienda_camera_commercio" not in ng


def test_chiavi_non_gestite_allowed_voltura_keys():
    d = copia(caso_voltura())
    ng = chiavi_non_gestite(d)
    # le chiavi di estremi di trascrizione e registrazione sono ammesse
    assert "opzioni.telematico.beni[b_casa0001].estremi_trascrizione" not in ng
    assert "opzioni.telematico.beni[b_casa0001].estremi_registrazione" not in ng


def test_chiavi_non_gestite_allowed_tavolare_key():
    d = copia(caso_tavolare())
    ng = chiavi_non_gestite(d)
    # la chiave superficie è ammessa per i terreni tavolari
    assert "opzioni.telematico.beni[b_terrtav1].superficie" not in ng


def test_chiavi_non_gestite_unknown_declaration_key():
    d = copia(caso_completo())
    d["opzioni"]["telematico"]["dichiarazione"]["foo"] = "bar"
    ng = chiavi_non_gestite(d)
    assert "opzioni.telematico.dichiarazione.foo" in ng


def test_chiavi_non_gestite_unknown_presentatore_key():
    d = copia(caso_completo())
    d["opzioni"]["telematico"]["dichiarazione"]["presentatore"]["fax"] = "123"
    ng = chiavi_non_gestite(d)
    assert "opzioni.telematico.dichiarazione.presentatore.fax" in ng


def test_chiavi_non_gestite_unknown_testamento_key():
    d = copia(caso_testamento())
    d["opzioni"]["telematico"]["dichiarazione"]["testamento"]["extra"] = "val"
    ng = chiavi_non_gestite(d)
    assert "opzioni.telematico.dichiarazione.testamento.extra" in ng


def test_chiavi_non_gestite_unknown_versamento_key():
    d = copia(caso_completo())
    d["opzioni"]["telematico"]["dichiarazione"]["versamento"]["extra_vers"] = "x"
    ng = chiavi_non_gestite(d)
    assert "opzioni.telematico.dichiarazione.versamento.extra_vers" in ng


def test_chiavi_non_gestite_unknown_bene_key():
    d = copia(caso_completo())
    d["opzioni"]["telematico"]["beni"]["b_casa0001"]["unknown"] = 1
    ng = chiavi_non_gestite(d)
    assert "opzioni.telematico.beni[b_casa0001].unknown" in ng


def test_chiavi_non_gestite_reference_to_nonexistent_bene():
    d = copia(caso_completo())
    # aggiungo un bene telematico che non esiste nella lista dei beni
    d["opzioni"]["telematico"]["beni"]["b_fake"] = {"provincia": "XX"}
    ng = chiavi_non_gestite(d)
    assert "opzioni.telematico.beni[b_fake]: riferimento a un elemento inesistente" in ng


def test_attr_entity_precedence(monkeypatch):
    dati = {"opzioni": {"telematico": {"persone": {"p_test": {"custom": "tel"}}}}}
    ent = {"id": "p_test", "custom": "ent"}
    assert attr(dati, "persone", ent, "custom") == "ent"


def test_attr_telematic_fallback(monkeypatch):
    dati = {"opzioni": {"telematico": {"persone": {"p_test": {"custom": "tel"}}}}}
    ent = {"id": "p_test"}
    assert attr(dati, "persone", ent, "custom") == "tel"


def test_attr_none_when_absent(monkeypatch):
    dati = {"opzioni": {"telematico": {"persone": {}}}}
    ent = {"id": "p_test"}
    assert attr(dati, "persone", ent, "custom") is None


def test_attr_assente_state(monkeypatch):
    sup_mod = importlib.import_module("successioni.telematico.supplemento")
    # forziamo V.e_stato a riconoscere i dict con chiave 'stato'
    monkeypatch.setattr(sup_mod.V, "e_stato", lambda v: isinstance(v, dict) and "stato" in v)
    dati = {
        "opzioni": {
            "telematico": {
                "persone": {"p_test": {"custom": {"stato": "assente", "val": 1}}}
            }
        }
    }
    ent = {"id": "p_test"}
    assert attr(dati, "persone", ent, "custom") is None


def test_attr_da_confermare_state(monkeypatch):
    sup_mod = importlib.import_module("successioni.telematico.supplemento")
    monkeypatch.setattr(sup_mod.V, "e_stato", lambda v: isinstance(v, dict) and "stato" in v)
    dati = {
        "opzioni": {
            "telematico": {
                "persone": {"p_test": {"custom": {"stato": "da_confermare", "val": 1}}}
            }
        }
    }
    ent = {"id": "p_test"}
    result = attr(dati, "persone", ent, "custom")
    assert isinstance(result, dict)
    assert result["stato"] == "da_confermare"


def test_tutte_le_sottochiavi_del_testamento_sono_note_e_le_altre_segnalate():
    from successioni.telematico.supplemento import CHIAVI_TESTAMENTO, chiavi_non_gestite
    attese = {"estero", "pubblico_ufficiale", "data_pubblicazione", "ufficio_registrazione", "serie",
              "numero_registrazione", "sottonumero_registrazione", "data_registrazione"}
    assert CHIAVI_TESTAMENTO == attese
    dati = {"persone": [], "beni": [], "passivita": [], "opzioni": {"telematico": {"dichiarazione": {
        "testamento": {**{k: "x" for k in attese}, "inventata": 1}}}}}
    assert chiavi_non_gestite(dati) == ["opzioni.telematico.dichiarazione.testamento.inventata"]
