"""Tabelle usate dai calcoli con la fonte (versione 0.4): i valori mostrati sono letti dai moduli di calcolo, non riscritti.
Ogni riga deve coincidere con cio' che le funzioni di calcolo applicano."""
from fractions import Fraction

from starlette.testclient import TestClient

from successioni import valore_catastale as VC
from successioni.archivio import Archivio
from successioni.servizio import Servizio
from successioni.tabelle import tabelle
from successioni.telematico import calcolo as C
from successioni.telematico import quadri_efgh as EF
from successioni.telematico import usufrutto as U
from successioni.web import crea_app


def _per_id():
    return {t["id"]: t for t in tabelle()}


def test_ogni_tabella_ha_fonte_decorrenza_e_righe_coerenti():
    for t in tabelle():
        assert t["fonte"] and t["decorrenza"] and t["righe"], t["id"]
        assert all(len(r) == len(t["colonne"]) for r in t["righe"]), t["id"]


def test_aliquote_e_franchigie_come_il_calcolo():
    t = _per_id()
    al = {r[1]: r[0] for r in t["aliquote"]["righe"]}
    for grado in C.GRADI_4 | C.GRADI_6 | C.GRADI_8 | C.GRADI_ESENTI:
        a, _ = C.aliquota(grado)
        testo = f"{a * 100}".rstrip("0") + "%" if a else "0%"
        assert grado in al[testo.replace("/1", "")].split(", ")
    fr = [r[1] for r in t["franchigie"]["righe"]]
    assert fr == ["1.000.000 €", "100.000 €", "1.500.000 €"]
    assert C.franchigia("01", False)[0] == 1_000_000 and C.franchigia("10", False)[0] == 100_000
    assert C.franchigia("27", True)[0] == 1_500_000


def test_ipocatastali_catastale_usufrutto():
    t = _per_id()
    ef = {r[0]: r[1] for r in t["ipocatastali"]["righe"]}
    assert ef["Imposta ipotecaria proporzionale (EF1)"] == "2%" and ef["Imposta catastale proporzionale (EF9)"] == "1%"
    assert f"{EF.IMPOSTA_FISSA} €" in ef.values() and f"{EF.IMPOSTA_FISSA_2006_2013} €" in ef.values()
    cat = t["catastale"]["righe"]
    assert [r[2] for r in cat] == ["90", "168", "40,80", "60", "110", "120"]
    assert VC.moltiplicatore_fabbricato("A2", True)[0] == 110 and VC.moltiplicatore_fabbricato("A2", False)[0] == 120
    us = t["usufrutto"]["righe"]
    assert len(us) == len(U.PROSPETTO) and us[0] == ["0–20 anni", "38", "95%"]
    assert U.coefficiente(20) * U.SAGGIO == Fraction(95, 100)


def test_api_e_mcp(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    cl = TestClient(crea_app(sv, token="tok123", ammetti_host_di_prova=True), base_url="http://testserver")
    cl.get("/", params={"t": "tok123"})
    j = cl.get("/api/tabelle").json()
    assert j["nota"] and [t["id"] for t in j["tabelle"]] == ["aliquote", "franchigie", "ipocatastali", "catastale", "usufrutto"]
    from successioni.mcp_server import STRUMENTI_LETTURA
    assert "tabelle_calcolo" in STRUMENTI_LETTURA
