"""Proposte piccole del report grafico DEAS dell'08/11/2026: codice comune ricavato dal nome (4), colore dei valori calcolati
(3) con contrasto sufficiente in ogni tema. Le parti nel browser sono in tests/e2e/gui_grafica_rapida.js."""
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from successioni import codice_fiscale as CF
from test_gui_layout import SOGLIA, colore, rapporto, sopra, temi

STATIC = Path(__file__).resolve().parents[1] / "src" / "successioni" / "static"
TABELLA = {"H501": ("ROMA", "RM"), "E623": ("LIVO", "CO"), "E624": ("LIVO", "TN"), "I199": ("SANT'AGATA DI MILITELLO", "ME"),
           "Z999": ("CASTELLO", "TO"), "Z998": ("CASTELLO", None), "Z997": ("CASTELLO", None)}


@pytest.fixture
def tabelle(monkeypatch):
    monkeypatch.setattr(CF, "_jar", lambda: Path("finto.jar"))
    monkeypatch.setattr(CF, "_comuni", lambda jar: TABELLA)


def test_trovato_anche_con_accenti_apostrofi_e_minuscole(tabelle):
    r = CF.cerca_codice_comune("roma")
    assert r["esito"] == "trovato" and (r["codice"], r["provincia"]) == ("H501", "RM") and r["omonimi_senza_provincia"] == 0
    assert CF.cerca_codice_comune("Sant’Agata di Militello")["codice"] == "I199"
    assert CF.cerca_codice_comune("  sant agata  di militello ")["codice"] == "I199"


def test_omonimi_ambigui_si_risolvono_con_la_provincia(tabelle):
    r = CF.cerca_codice_comune("Livo")
    assert r["esito"] == "ambiguo" and {c["codice"] for c in r["candidati"]} == {"E623", "E624"}
    assert CF.cerca_codice_comune("Livo", "tn")["codice"] == "E624"
    assert CF.cerca_codice_comune("Livo", "RM")["esito"] == "non_trovato"


def test_omonimi_senza_provincia_segnalati(tabelle):
    r = CF.cerca_codice_comune("Castello")
    assert r["esito"] == "trovato" and r["codice"] == "Z999" and r["omonimi_senza_provincia"] == 2


def test_senza_tabelle_nessuna_proposta(monkeypatch):
    monkeypatch.setattr(CF, "_jar", lambda: None)
    assert CF.cerca_codice_comune("Roma") == {"esito": "tabelle_assenti", "candidati": []}


def test_nome_vuoto_o_sconosciuto(tabelle):
    assert CF.cerca_codice_comune("")["esito"] == "non_trovato"
    assert CF.cerca_codice_comune("Atlantide")["esito"] == "non_trovato"


def test_api_codice_comune(tabelle, tmp_path):
    from successioni.archivio import Archivio
    from successioni.servizio import Servizio
    from successioni.web import crea_app
    c = TestClient(crea_app(Servizio(Archivio(tmp_path / "d")), token="tok123", ammetti_host_di_prova=True), base_url="http://testserver")
    c.get("/", params={"t": "tok123"})
    r = c.get("/api/codice-comune", params={"nome": "Livo", "provincia": "CO"})
    assert r.status_code == 200 and r.json()["codice"] == "E623"


@pytest.mark.parametrize("tema", ["chiaro", "scuro", "seppia"])
def test_colore_dei_valori_calcolati_leggibile(tema):
    t = temi((STATIC / "app.css").read_text(encoding="utf-8"))[tema]
    fondo = colore(t["--solido"], t)
    calc = sopra(colore(t["--calc"], t), fondo)
    for nome in ("--t", "--t2"):
        assert rapporto(colore(t[nome], t), calc) >= SOGLIA, f"{tema}: {nome} su --calc = {rapporto(colore(t[nome], t), calc):.2f}"
    assert rapporto(colore(t["--calc-b"], t), calc) >= SOGLIA, f"{tema}: etichetta «calcolato» = {rapporto(colore(t['--calc-b'], t), calc):.2f}"
    # distinto dai colori di selezione e di avviso
    assert t["--calc"] not in (t["--blu-t"], t["--am-t"])
