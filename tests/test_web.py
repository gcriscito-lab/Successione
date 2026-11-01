import pytest
from starlette.testclient import TestClient
from successioni.archivio import Archivio
from successioni.servizio import Servizio
from successioni.web import crea_app

T = "tok123"


@pytest.fixture
def ctx(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    c = TestClient(crea_app(sv, token=T), base_url="http://testserver")
    return sv, c


def test_senza_token_non_autorizzato(ctx):
    _, c = ctx
    assert c.get("/api/pratiche").status_code == 401
    assert c.get("/api/pratiche", params={"t": T}).status_code == 200


def test_host_diverso_rifiutato(ctx):
    _, c = ctx
    r = c.get("/api/pratiche", params={"t": T}, headers={"host": "evil.example"})
    assert r.status_code == 403


def test_origine_esterna_rifiutata_su_scrittura(ctx):
    _, c = ctx
    c.get("/", params={"t": T})
    r = c.post("/api/pratiche", json={"titolo": "x"}, headers={"origin": "http://evil.example"})
    assert r.status_code == 403


def test_flusso_gui_e_conflitto_con_servizio(ctx):
    sv, c = ctx
    assert "Successioni" in c.get("/", params={"t": T}).text
    pid = c.post("/api/pratiche", json={"titolo": "Rossi", "chiave": "a"}).json()["pratica_id"]
    op = [{"op": "upsert", "coll": "persone", "id": "p_aaaa1111", "campi": {"cognome": "Rossi", "ruolo": "defunto"}}]
    r = c.post(f"/api/pratiche/{pid}/aggiorna", json={"revisione_attesa": 1, "operazioni": op})
    assert r.status_code == 200 and r.json()["revisione"] == 2
    # una modifica da MCP/servizio nel frattempo: la GUI con revisione vecchia riceve 409 leggibile
    sv.aggiorna(pid, 2, [{"op": "upsert", "coll": "persone", "id": "p_aaaa1111", "campi": {"nome": "M"}}], canale="mcp")
    r = c.post(f"/api/pratiche/{pid}/aggiorna", json={"revisione_attesa": 2, "operazioni": op})
    assert r.status_code == 409 and r.json()["modifiche_successive"][0]["canale"] == "mcp"
    bad = c.post(f"/api/pratiche/{pid}/aggiorna", json={"revisione_attesa": 3, "operazioni": [
        {"op": "upsert", "coll": "persone", "id": "p_bbbb2222", "campi": {"codice_fiscale": "x"}}]})
    assert bad.status_code == 422 and bad.json()["errori"][0]["percorso"] == "persone[p_bbbb2222].codice_fiscale"
    assert c.get(f"/api/pratiche/{pid}/verifica").json()["esito"] == "rilievi"
