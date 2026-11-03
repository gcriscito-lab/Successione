"""Codici ufficiali dei campi a valori fissi: letti dagli XSD, coerenti con i campi della pratica e con l'esportazione."""
import copy
from datetime import date

import pytest
from starlette.testclient import TestClient

from successioni import codici as C
from successioni import schema as S
from successioni.archivio import Archivio
from successioni.servizio import Servizio
from successioni.telematico import supplemento as SUP
from successioni.telematico import xsd as X
from successioni.telematico.esporta import codice_enum, esporta_xml
from successioni.web import crea_app, strutturati_completi
from telematico_casi import caso_a10, caso_testamento_legatario, contesto_caso_a10

CTX = contesto_caso_a10(data_riferimento=date(2025, 9, 1))


def test_ogni_regola_ha_un_tipo_xsd_con_voci():
    for chiave, (tipo, etichetta) in C.REGOLE.items():
        v = C.voci(tipo)
        assert len(v) >= 2 and etichetta, (chiave, tipo)
        assert all(x["valore"] and x["etichetta"] for x in v)
        assert len({x["valore"] for x in v}) == len(v)


def test_le_chiavi_sono_campi_reali_della_pratica():
    for chiave in C.REGOLE:
        parti = chiave.split(".", 1)
        if parti[0] == "dichiarazione":
            assert parti[1].split(".")[0] in SUP.CHIAVI_DICHIARAZIONE, chiave
        else:
            campo = parti[1].split("@")[0]
            assert campo in S.COLLEZIONI[parti[0]], chiave
            assert S.COLLEZIONI[parti[0]][campo] in ("str", "cf"), chiave      # un testo, non un enum gia' a menu


@pytest.mark.parametrize("chiave", list(C.REGOLE))
def test_ogni_codice_proposto_e_accettato_dall_esportazione(chiave):
    tipo = C.REGOLE[chiave][0]
    for v in C.voci(tipo):
        assert codice_enum(v["valore"], tipo) == v["valore"]


def test_stato_civile_e_gli_altri_codici_noti():
    d = {v["valore"]: v["etichetta"] for v in C.voci("StatoCivile_Type")}
    assert d["1"] == "celibe/nubile" and d["4"] == "vedovo/a" and len(d) == 7
    g = {v["valore"]: v["etichetta"] for v in C.voci("GradoParentela_Type")}
    assert g["02"] == "Figlio/a" and g["03"] == "Genitore" and len(g) == 43
    cespiti = {v["valore"] for v in C.voci("TipoCespite_Type")}
    assert {"BI", "CR", "DN", "AB"} <= cespiti and len(cespiti) == 5


def test_ordine_naturale_dei_codici():
    assert [v["valore"] for v in C.voci("CodiciDirittoImmobili_Type")] == ["1", "1S", "1T", "2", "2S", "2T", "4", "5", "6", "10"]
    assert C._chiave_naturale("10") > C._chiave_naturale("2") and C._chiave_naturale("1S") > C._chiave_naturale("1")


def test_etichette_pulite_senza_cambiare_le_parole():
    assert C._etichetta("  Spese  mediche;  ") == "Spese mediche"
    assert C._etichetta("abitazione.") == "abitazione"
    assert C._etichetta("a;b") == "a;b"


@pytest.mark.parametrize("tipo,atteso", [("fabbricato", "immobile"), ("terreno", "immobile"), ("titolo", "altro"),
                                         ("disponibilita_finanziaria", "altro"), ("azienda", "altro"), (None, "altro"), ("", "altro")])
def test_contesto_del_bene(tipo, atteso):
    assert C.contesto_bene(tipo) == atteso


def test_senza_fonti_i_campi_restano_di_testo_libero(monkeypatch):
    def guasto(*a, **k):
        raise FileNotFoundError("fonti assenti")
    monkeypatch.setattr(X, "enumerazioni", guasto)
    assert C.voci("StatoCivile_Type") == [] and C.strutturati() == {}


def test_le_voci_scritte_a_mano_hanno_la_precedenza(monkeypatch):
    monkeypatch.setattr(C, "REGOLE", {**C.REGOLE, "beni.tipo_titolo": ("Titoli_Type", "tipo titolo generato")})
    s = strutturati_completi()
    assert s["beni.tipo_titolo"] is S.STRUTTURATI["beni.tipo_titolo"]
    assert s["dichiarazione.stato_civile"]["xsd"] == "StatoCivile_Type"


def test_diritti_distinti_per_immobili_e_altri_beni():
    s = C.strutturati()
    imm = {o["valore"] for o in s["beni.diritto@immobile"]["opzioni"]}
    altro = {o["valore"] for o in s["beni.diritto@altro"]["opzioni"]}
    assert {"1", "1S", "10"} <= imm and altro == {"1", "2"}
    assert {o["valore"] for o in s["devoluzioni.diritto@altro"]["opzioni"]} == {"1", "2", "7", "8"}
    assert len(s["devoluzioni.diritto@immobile"]["opzioni"]) == 17


# ----------------------------------------------------------------------- i codici scelti dai menu producono un XML senza errori
def _errori(d):
    return {(e.percorso, e.codice) for e in esporta_xml(d, CTX).errori}


def test_codici_del_menu_nella_pratica_esportano_senza_errori_di_valore():
    d = caso_a10()
    d["persone"][0]["data_decesso"] = "2025-03-10"
    for p in d["persone"]:
        if p["ruolo"] == "erede":
            p["grado_parentela"] = "02"
            p["tipo_soggetto"] = "1"
    d["opzioni"]["telematico"]["dichiarazione"]["stato_civile"] = "2"
    d["opzioni"]["telematico"]["dichiarazione"]["tempistica_pagamento"] = "2"
    casa = next(b for b in d["beni"] if b["tipo"] == "fabbricato")
    casa["categoria"] = "A3"
    casa["diritto"] = "1"
    errori = _errori(d)
    assert not [e for e in errori if e[1] == "VALORE_NON_VALIDO"], errori


def test_un_codice_fuori_elenco_resta_un_errore_dell_esportazione():
    d = caso_a10()
    d["opzioni"]["telematico"]["dichiarazione"]["stato_civile"] = "9"
    assert any(p.endswith("stato_civile") or "stato" in p for p, c in _errori(d) if c == "VALORE_NON_VALIDO")


def test_tempistica_fuori_elenco_con_imposta_dovuta():
    d = caso_testamento_legatario()
    assert not [e for e in _errori(d) if e[0].endswith("tempistica_pagamento")]
    d["opzioni"]["telematico"]["dichiarazione"]["tempistica_pagamento"] = "7"
    assert any(p.endswith("tempistica_pagamento") for p, _ in _errori(d))


# ------------------------------------------------------------------------------------------------------------ API
def test_api_schema_espone_i_codici(tmp_path):
    with TestClient(crea_app(Servizio(Archivio(tmp_path / "d")), token="sintetico", ammetti_host_di_prova=True)) as cl:
        j = cl.get("/api/schema?t=sintetico").json()
    st = j["strutturati"]
    assert st["dichiarazione.stato_civile"]["opzioni"][3] == {"valore": "4", "etichetta": "vedovo/a", "aiuto": ""}
    assert "beni.tipo_titolo" in st and "persone.grado_parentela" in st and "passivita.tipo" in st


def test_voci_puliscono_le_etichette_e_ripiegano_sul_codice(monkeypatch):
    monkeypatch.setattr(X, "enumerazioni", lambda tipo, namespace=None: {"2": "", "1": "  Uno  due;", "10": "Dieci."})
    assert C.voci("Qualsiasi") == [{"valore": "1", "etichetta": "Uno due", "aiuto": ""},
                                   {"valore": "2", "etichetta": "2", "aiuto": ""},
                                   {"valore": "10", "etichetta": "Dieci", "aiuto": ""}]


def test_strutturati_generati_sono_menu_a_scelta():
    s = C.strutturati()
    assert all(v["tipo"] == "enum" and v["opzioni"] and v["xsd"] and "Si salva il codice" in v["aiuto"] for v in s.values())
    assert set(s) == set(C.REGOLE)
