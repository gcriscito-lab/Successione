"""«Prossime azioni» della pagina iniziale (src/successioni/cruscotto.py): tappe, azione e termine, dati SINTETICI."""
from datetime import date

from starlette.testclient import TestClient

from successioni import cruscotto as C
from successioni.archivio import Archivio
from successioni.servizio import Servizio
from successioni.web import crea_app
from test_correzioni_codex import pratica_con_allegati


def test_pratica_nuova_si_ferma_ai_dati_con_il_campo(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    sv.crea_pratica("Successione Prova", iniziali=[{"op": "upsert", "coll": "persone", "id": "p_defunto1",
                                                   "campi": {"ruolo": "defunto", "cognome": "Prova", "data_decesso": "2025-12-01"}}])
    c = C.cruscotto(sv, oggi=date(2026, 11, 7))
    v = c["pratiche"][0]
    assert v["tappe"] == {"dati": "corrente", "file": "da_fare", "controllo": "da_fare", "invio": "da_fare", "ricevute": "da_fare"}
    assert v["azione"]["testo"] and v["azione"]["dove"]["sel"]
    assert v["termine"] == {"data": "2026-12-01", "giorni": 24}
    assert [t["nome"] for t in c["tappe"]] == ["Dati", "File", "Controllo", "Invio", "Ricevute"]


def test_pratica_completa_passa_al_file_e_poi_al_controllo(tmp_path):
    sv, pid = pratica_con_allegati(tmp_path)
    v = next(x for x in C.cruscotto(sv)["pratiche"] if x["pratica_id"] == pid)
    assert v["tappe"]["dati"] == "fatto" and v["tappe"]["file"] == "corrente" and v["azione"]["dove"] == {"sel": "FILE"}
    assert sv.esporta(pid)["completo"]
    v = next(x for x in C.cruscotto(sv)["pratiche"] if x["pratica_id"] == pid)
    assert v["tappe"]["file"] == "fatto" and v["tappe"]["controllo"] == "corrente" and "controllo" in v["azione"]["testo"].lower()


def test_ordine_per_termine_e_termine_superato(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    for t, dd in (("Lontana", "2026-10-01"), ("Superata", "2025-06-01"), ("Vicina", "2025-12-01")):
        sv.crea_pratica(t, iniziali=[{"op": "upsert", "coll": "persone", "id": "p_defunto1",
                                      "campi": {"ruolo": "defunto", "cognome": t, "data_decesso": dd}}])
    c = C.cruscotto(sv, oggi=date(2026, 11, 7))
    assert [v["titolo"] for v in c["pratiche"]] == ["Superata", "Vicina", "Lontana"]
    assert c["pratiche"][0]["termine"]["giorni"] < 0


def test_rotta_web(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    sv.crea_pratica("Una")
    cl = TestClient(crea_app(sv, token="tk", porta=8765), base_url="http://127.0.0.1:8765", follow_redirects=False)
    assert cl.get("/api/cruscotto").status_code == 401
    cl.get("/", params={"t": "tk"})
    r = cl.get("/api/cruscotto")
    assert r.status_code == 200 and r.json()["pratiche"][0]["titolo"] == "Una"
