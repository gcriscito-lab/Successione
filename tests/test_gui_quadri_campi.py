"""Interfaccia: campi mostrati per quadro coerenti con il modello e province tavolari esposte dallo schema."""
from starlette.testclient import TestClient

from successioni import quadri as Q
from successioni import schema as S
from successioni.archivio import Archivio
from successioni.servizio import Servizio
from successioni.web import crea_app


def test_i_campi_di_ogni_quadro_esistono_nel_modello():
    campi = set(S.COLLEZIONI["beni"])
    for q in Q.QUADRI:
        if "campi" in q:
            assert q["coll"] == "beni", q["id"]
            assert set(q["campi"]) <= campi, (q["id"], set(q["campi"]) - campi)
            assert "tipo" in q["campi"] and "valore" in q["campi"], q["id"]


def test_ogni_quadro_dei_beni_ha_i_suoi_campi():
    con_campi = {q["id"] for q in Q.QUADRI if "campi" in q}
    assert con_campi == {"EB", "EC", "EL", "EM", "EN", "EO", "EP", "EQ", "ER"}


def test_i_campi_specifici_sono_solo_nei_quadri_pertinenti():
    per = {q["id"]: set(q["campi"]) for q in Q.QUADRI if "campi" in q}
    assert "tipo_titolo" in per["EO"] and "tipo_titolo" not in per["ER"] and "tipo_titolo" not in per["EC"]
    assert "partita_tavolare" in per["EL"] and "partita_tavolare" in per["EM"] and "partita_tavolare" not in per["EB"]
    assert "marca_modello" in per["EP"] and "lunghezza" in per["EQ"] and "inventario" in per["EN"]


def test_lo_schema_espone_le_province_tavolari(tmp_path):
    with TestClient(crea_app(Servizio(Archivio(tmp_path / "d")), token="sintetico", ammetti_host_di_prova=True)) as cl:
        r = cl.get("/api/schema?t=sintetico")
    assert r.status_code == 200
    assert sorted(r.json()["province_tavolari"]) == ["BZ", "GO", "TN", "TS"]
    assert {q["id"]: q.get("campi") for q in r.json()["quadri"]}["EO"]
