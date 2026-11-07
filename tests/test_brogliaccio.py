"""Voce 23 di docs/ANALISI_REPLICA_2026-11-07.md: brogliaccio dei beni e riepilogo delle quote (CSV e pagina stampabile).
Dati come inseriti, nessun calcolo d'imposta; la somma delle quote per bene usa lo stesso confronto dei controlli interni."""
import csv
import io

from starlette.testclient import TestClient

from successioni import brogliaccio as B
from telematico_casi import caso_completo, copia

T = "tok123"


def test_righe_beni_quote_e_soggetti():
    d = caso_completo()
    r = B.righe(d)
    assert len(r["beni"]) == len(d["beni"]) and len(r["quote"]) == len(d["devoluzioni"])
    assert all(q["esito"] == "completa" for q in r["quote"]), r["quote"]
    eredi = [p for p in d["persone"] if p["ruolo"] != "defunto"]
    assert len(r["soggetti"]) == len(eredi)
    assert sum(s["beni"] for s in r["soggetti"]) == len(d["devoluzioni"])


def test_quote_incomplete_ed_eccedenti():
    d = copia(caso_completo())
    dv = d["devoluzioni"][0]
    dv["quota"] = {"num": 1, "den": 10}
    esiti = {q["esito"] for q in B.righe(d)["quote"]}
    assert any(e.startswith("manca") for e in esiti) or len(d["devoluzioni"]) == 1
    dv["quota"] = {"stato": "da_confermare"}
    assert any("da indicare" in q["esito"] for q in B.righe(d)["quote"])
    dv["quota"] = {"num": 1, "den": 1}          # 1/1 + 1/2 dell'altro erede sullo stesso bene
    assert any(q["esito"] == "supera 1/1" for q in B.righe(d)["quote"])
    dv["quota"] = {"num": 3, "den": 1}          # non e' una quota: resta da indicare, come nei controlli interni
    assert any(q["esito"] == "1 quota da indicare" for q in B.righe(d)["quote"])


def test_csv_per_excel_italiano():
    t = B.csv_testo(caso_completo())
    assert t.startswith("﻿")
    righe = list(csv.reader(io.StringIO(t[1:]), delimiter=";"))
    assert righe[0] == ["BENI"] and righe[1] == B.COLONNE_BENI
    assert ["QUOTE PER BENE"] in righe and ["SOGGETTI"] in righe


def test_html_stampabile_e_escape():
    d = copia(caso_completo())
    d["beni"][0]["comune"] = "<script>x</script>"
    pag = B.html(d, titolo="Prova <b>", revisione=3)
    assert "<script>x" not in pag and "&lt;script&gt;" in pag and "revisione 3" in pag and "Prova &lt;b&gt;" in pag


def test_api_csv_html_e_mcp(tmp_path):
    from successioni.archivio import Archivio
    from successioni.servizio import Servizio
    from successioni.web import crea_app
    from test_elaborati import ops_da_caso
    sv = Servizio(Archivio(tmp_path / "d"))
    pid = sv.crea_pratica("Brogliaccio", iniziali=ops_da_caso(caso_completo()))["pratica_id"]
    assert sv.brogliaccio(pid)["quote"]
    c = TestClient(crea_app(sv, token=T, ammetti_host_di_prova=True), base_url="http://testserver")
    c.get("/", params={"t": T})
    r = c.get(f"/api/pratiche/{pid}/brogliaccio.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"] and r.content.startswith("﻿".encode("utf-8"))
    r = c.get(f"/api/pratiche/{pid}/brogliaccio")
    assert r.status_code == 200 and "Brogliaccio" in r.text
    assert c.get("/api/pratiche/inesistente/brogliaccio.csv").status_code == 404
