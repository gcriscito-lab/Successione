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
from telematico_casi import caso_a10, caso_tavolare, caso_testamento, caso_testamento_legatario, contesto_caso_a10

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
            _chiave_annidata_esiste(parti[1])
        else:
            campo = parti[1].split("@")[0]
            assert campo in S.COLLEZIONI[parti[0]], chiave
            assert S.COLLEZIONI[parti[0]][campo] in ("str", "cf"), chiave      # un testo, non un enum gia' a menu


def _chiave_annidata_esiste(percorso):
    sez, _, foglia = percorso.partition(".")
    insiemi = {"presentatore": SUP.CHIAVI_PRESENTATORE, "testamento": SUP.CHIAVI_TESTAMENTO, "versamento": SUP.CHIAVI_VERSAMENTO}
    if foglia:
        assert foglia in insiemi[sez], percorso


def _accettato(valore, tipo):
    """Accettato dall'esportazione se lo e' da almeno uno dei tipi della regola (unione «A+B»)."""
    for t in C.tipi_xsd(tipo):
        try:
            if codice_enum(valore, t) == valore:
                return True
        except Exception:
            pass
    return False


@pytest.mark.parametrize("chiave", list(C.REGOLE) + list(C.SUGGERIMENTI))
def test_ogni_codice_proposto_e_accettato_dall_esportazione(chiave):
    tipo = (C.REGOLE.get(chiave) or C.SUGGERIMENTI[chiave])[0]
    assert C.voci(tipo)
    for v in C.voci(tipo):
        assert _accettato(v["valore"], tipo), (chiave, v["valore"])


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


# ------------------------------------------------------------------ province e liste lunghe (SOGLIA_MENU)
def test_suggerimenti_sono_campi_reali_e_oltre_la_soglia():
    for chiave, (tipo, etichetta) in C.SUGGERIMENTI.items():
        assert etichetta and len(C.voci(tipo)) > C.SOGLIA_MENU, chiave
        parti = chiave.split(".", 1)
        if parti[0] == "dichiarazione":
            assert parti[1].split(".")[0] in SUP.CHIAVI_DICHIARAZIONE
            _chiave_annidata_esiste(parti[1])
        else:
            assert S.COLLEZIONI[parti[0]][parti[1]] in ("str", "cf")
    assert not set(C.SUGGERIMENTI) & set(C.REGOLE)


def test_i_menu_restano_entro_la_soglia():
    for chiave, (tipo, _) in C.REGOLE.items():
        assert len(C.voci(tipo)) <= C.SOGLIA_MENU, chiave


def test_province_nei_menu():
    s = C.strutturati()
    nasc = {o["valore"] for o in s["persone.provincia_nascita"]["opzioni"]}
    assert len(nasc) == 115 and {"RM", "EE", "FU"} <= nasc
    assert {o["valore"] for o in s["persone.provincia_decesso"]["opzioni"]} == nasc
    imm = {o["valore"] for o in s["beni.provincia@immobile"]["opzioni"]}
    assert len(imm) == 112 and {"RM", "BZ", "TN", "GO", "TS", "BL"} <= imm and not {"FU", "PL", "ZA"} & imm
    assert "beni.provincia" not in s                     # gli altri beni non hanno provincia


def test_unione_dei_tipi_senza_duplicati_e_ordine_naturale(monkeypatch):
    monkeypatch.setattr(X, "enumerazioni", lambda t, namespace=None: {"A": "", "B": "x"} if t == "T1" else {"B": "y", "C": "z"})
    assert [(v["valore"], v["etichetta"]) for v in C.voci("T1+T2")] == [("A", "A"), ("B", "x"), ("C", "z")]
    assert C.tipi_xsd("T1+T2") == ["T1", "T2"] and C.tipi_xsd("T1") == ["T1"]


def test_suggerimenti_elenco_e_assenza_fonti(monkeypatch):
    sg = C.suggerimenti()
    assert len(sg["beni.codice_comune_catastale"]["valori"]) == 692 and "613" in sg["beni.codice_comune_catastale"]["valori"]
    assert len(sg["dichiarazione.testamento.ufficio_registrazione"]["valori"]) == 1261
    monkeypatch.setattr(X, "enumerazioni", lambda *a, **k: (_ for _ in ()).throw(KeyError("x")))
    assert C.suggerimenti() == {}


def test_esportazione_reale_con_province_e_codici_dei_menu():
    d = caso_a10()
    pers = d["opzioni"]["telematico"]["persone"]
    for p in d["persone"]:
        pers.setdefault(p["id"], {})["provincia_nascita"] = "FU" if p["ruolo"] == "defunto" else "MI"
        if p["ruolo"] == "defunto":
            p["data_decesso"] = "2025-03-10"
            pers[p["id"]]["provincia_decesso"] = "TN"
    for b in d["beni"]:
        if b["tipo"] in ("fabbricato", "terreno"):
            d["opzioni"]["telematico"]["beni"].setdefault(b["id"], {})["provincia"] = "MI"
    assert not [e for e in _errori(d) if e[1] == "VALORE_NON_VALIDO"], _errori(d)


def test_provincia_non_in_elenco_e_ancora_un_errore():
    d = caso_a10()
    d["opzioni"]["telematico"]["persone"][next(p["id"] for p in d["persone"] if p["ruolo"] == "defunto")]["provincia_nascita"] = "XX"
    assert any(p.endswith("provincia_nascita") or "Provincia" in p for p, c in _errori(d) if c == "VALORE_NON_VALIDO")


def test_tavolare_con_provincia_e_comune_catastale_dei_codici():
    d = caso_tavolare()
    for b in d["beni"]:
        if b["id"].endswith("tav1"):
            assert b["provincia"] in {v["valore"] for v in C.voci(C.REGOLE["beni.provincia@immobile"][0])}
            assert b["codice_comune_catastale"] in C.suggerimenti()["beni.codice_comune_catastale"]["valori"]
    assert not [e for e in _errori(d) if e[1] == "VALORE_NON_VALIDO"], _errori(d)
    d["beni"][-1]["codice_comune_catastale"] = "999"          # fuori elenco
    assert any(c == "VALORE_NON_VALIDO" for _, c in _errori(d))


def test_ufficio_registrazione_testamento_dai_suggerimenti():
    d = caso_testamento()
    ufficio = C.suggerimenti()["dichiarazione.testamento.ufficio_registrazione"]["valori"][5]
    d["opzioni"]["telematico"]["dichiarazione"]["testamento"]["ufficio_registrazione"] = ufficio
    assert not [e for e in _errori(d) if e[0].endswith("ufficio_registrazione")]
    d["opzioni"]["telematico"]["dichiarazione"]["testamento"]["ufficio_registrazione"] = "ZZZ"
    assert any(p.endswith("ufficio_registrazione") for p, _ in _errori(d))


def test_ordine_con_codici_numerici_e_alfanumerici_misti():
    v = [x["valore"] for x in C.voci("UfficioDiRegistrazione_Type")]
    assert v[0] == "795" or v[0].isdigit()
    primo_alfa = next(i for i, c in enumerate(v) if not c.isdigit())
    assert all(c.isdigit() for c in v[:primo_alfa]) and v[primo_alfa:] == sorted(v[primo_alfa:], key=C._chiave_naturale)
    assert C._chiave_naturale("795") < C._chiave_naturale("T57")


def test_etichette_dei_suggerimenti():
    assert C.SUGGERIMENTI["beni.codice_comune_catastale"][1] == "codice del comune catastale (TN e BZ)"
    assert C.suggerimenti()["beni.codice_comune_catastale"]["etichetta"].startswith("codice del comune")
