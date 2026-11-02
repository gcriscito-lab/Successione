import pytest
from starlette.testclient import TestClient
from successioni.archivio import Archivio
from successioni.servizio import Servizio
from successioni.web import crea_app

T = "tok123"


@pytest.fixture
def ctx(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    c = TestClient(crea_app(sv, token=T, ammetti_host_di_prova=True), base_url="http://testserver")
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


def test_api_elaborati_stati_e_nessun_xml_parziale(ctx):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from test_elaborati import ops_da_caso, CF_FORN
    from telematico_casi import caso_completo
    sv, c = ctx
    pid = sv.crea_pratica("Caso", iniziali=ops_da_caso(caso_completo()))["pratica_id"]
    r = c.post(f"/api/pratiche/{pid}/esporta", json={"cf_fornitore": CF_FORN}, params={"t": T})
    assert r.status_code == 200 and r.json()["generato"] is False                    # completo: nessun file parziale
    r = c.post(f"/api/pratiche/{pid}/esporta", json={"cf_fornitore": CF_FORN, "scopo": "bozza_tecnica"}, params={"t": T})
    assert r.json()["generato"] is True and "NON è una dichiarazione completa" in r.json()["avvertenza"]
    st = c.get(f"/api/pratiche/{pid}/elaborati", params={"t": T}).json()
    assert st["export"]["stato"] == "aggiornato" and st["xsd"]["stato"] == "valido" and st["trasmissione"]["stato"] == "non_preparata"
    assert c.post(f"/api/pratiche/{pid}/esporta", json={"scopo": "x"}, params={"t": T}).status_code == 422


def test_r13_aiuti_sul_valore_della_quota_del_defunto(ctx):
    _, c = ctx
    a = c.get("/api/schema", params={"t": T}).json()["aiuti"]
    assert "QUOTA DEL DEFUNTO" in a["beni.valore"] and "intero" in a["beni.valore"]
