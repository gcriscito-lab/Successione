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


def test_dati_in_opzioni_telematico():
    # review del 07/11/2026 sera: provincia, codice comune, classe e consistenza salvati in opzioni.telematico (come nel
    # caso di riferimento) devono comparire nel brogliaccio, letti come fanno esportazione e albero
    d = caso_completo()
    casa = next(r for r in B.righe(d)["beni"] if r["particella"] == "200")
    assert (casa["provincia"], casa["codice_comune"], casa["classe"], casa["consistenza"]) == ("RM", "H501", "3", "5.5")
    terreno = next(r for r in B.righe(d)["beni"] if r["particella"] == "20")
    assert terreno["reddito_dominicale"] == "12.34"
    # il valore sull'entita' ha la precedenza
    d = copia(d)
    d["beni"][0]["provincia"] = "LT"
    assert B.righe(d)["beni"][0]["provincia"] == "LT"


def test_diritti_equivalenti_non_segnalano_manca():
    # lo stesso diritto scritto «1» e «proprieta» (l'esportazione li accetta entrambi, codice_enum con alias_descrizione)
    d = copia(caso_completo())
    d["devoluzioni"][0]["diritto"], d["devoluzioni"][1]["diritto"] = "1", "proprieta"
    q = [r for r in B.righe(d)["quote"] if r["bene"].startswith("Roma fg. 100")]
    assert len(q) == 2 and all(r["esito"] == "completa" and r["somma_quote_bene_diritto"] == "1/1" for r in q), q
    assert {r["diritto"] for r in q} == {"1", "proprieta"}          # il testo resta quello inserito
    assert B.codice_diritto("nuda proprieta") == "2" and B.codice_diritto("usufrutto") == "8"
    assert B.codice_diritto("xyz") == "xyz"
    # diritti diversi restano separati
    d["devoluzioni"][1]["diritto"] = "8"
    assert {r["esito"] for r in B.righe(d)["quote"] if r["bene"].startswith("Roma fg. 100")} == {"manca 1/2"}


def test_csv_neutralizza_le_formule_ma_non_i_numeri():
    d = copia(caso_completo())
    b = d["beni"][0]
    b["comune"], b["foglio"], b["valore"], b["rendita"] = '=HYPERLINK("x")', "-1+1", "-12", "+3,50"
    b["categoria"] = "@A2"
    next(x for x in d["persone"] if x["ruolo"] != "defunto")["cognome"] = "-SOMMA(A1)"
    righe = list(csv.reader(io.StringIO(B.csv_testo(d)[1:]), delimiter=";"))
    col = {c: i for i, c in enumerate(B.COLONNE_BENI)}
    r = righe[2]
    assert r[col["comune"]] == "'=HYPERLINK(\"x\")" and r[col["foglio"]] == "'-1+1" and r[col["categoria"]] == "'@A2"
    assert r[col["bene"]].startswith("'=")
    assert r[col["valore"]] == "-12" and r[col["rendita"]] == "+3,50"      # numeri veri delle colonne numeriche
    celle = [c for riga in righe for c in riga]
    assert any(c.startswith("'-SOMMA") for c in celle)
    assert not [c for c in celle if c[:1] in ("=", "+", "-", "@") and c not in ("-12", "+3,50")]
    assert B._cella("foglio", "-12") == "'-12" and B._cella("valore", "-12x") == "'-12x" and B._cella("valore", "12") == "12"
