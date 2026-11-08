"""Pagina iniziale con un solo elenco (08/11/2026): il cruscotto puo' restituire tutte le pratiche (?tutte=1); senza l'opzione resta
il comportamento precedente (le 12 piu' urgenti e il conteggio delle altre). Le parti nel browser: tests/e2e/gui_home.js."""
from datetime import date

from starlette.testclient import TestClient

from successioni import cruscotto as CR
from successioni.archivio import Archivio
from successioni.servizio import Servizio
from successioni.web import crea_app


def _servizio(tmp_path, n):
    sv = Servizio(Archivio(tmp_path / "d"))
    for i in range(n):
        sv.crea_pratica(f"Pratica {i:02d}", iniziali=[{"op": "upsert", "coll": "persone", "id": f"p_def{i:05d}",
                                                      "campi": {"ruolo": "defunto", "cognome": "PROVA", "data_decesso": f"2025-{1 + i % 12:02d}-10"}}])
    return sv


def test_predefinito_invariato_e_tutte(tmp_path):
    sv = _servizio(tmp_path, 14)
    c = CR.cruscotto(sv, oggi=date(2026, 1, 15))
    assert len(c["pratiche"]) == 12 and c["altre"] == 2 and c["totale"] == 14
    t = CR.cruscotto(sv, oggi=date(2026, 1, 15), tutte=True)
    assert len(t["pratiche"]) == 14 and t["altre"] == 0 and t["totale"] == 14
    # stesso ordine (urgenza): le prime 12 coincidono
    assert [v["pratica_id"] for v in t["pratiche"][:12]] == [v["pratica_id"] for v in c["pratiche"]]
    assert all(v["tappe"] and v["azione"] for v in t["pratiche"])


def test_api_tutte(tmp_path):
    sv = _servizio(tmp_path, 13)
    cl = TestClient(crea_app(sv, token="tok123", ammetti_host_di_prova=True), base_url="http://testserver")
    cl.get("/", params={"t": "tok123"})
    assert len(cl.get("/api/cruscotto").json()["pratiche"]) == 12
    assert len(cl.get("/api/cruscotto", params={"tutte": "1"}).json()["pratiche"]) == 13
