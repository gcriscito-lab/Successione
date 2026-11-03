"""Test delle rotte web di invio e degli strumenti MCP associati."""
import asyncio
import pytest
from starlette.testclient import TestClient

from successioni.archivio import Archivio
from successioni import mcp_server
from successioni.servizio import Servizio
from successioni.web import crea_app


@pytest.fixture
def servizio(tmp_path):
    return Servizio(Archivio(tmp_path / "dati"))


@pytest.fixture
def client(servizio):
    app = crea_app(servizio, token="sintetico", ammetti_host_di_prova=True)
    return TestClient(app)


def _estrai_nomi_strumenti(mcp_app) -> list[str]:
    if hasattr(mcp_app, "_tool_manager") and hasattr(mcp_app._tool_manager, "_tools"):
        return list(mcp_app._tool_manager._tools.keys())
    if hasattr(mcp_app, "_tools"):
        return list(mcp_app._tools.keys())
    if hasattr(mcp_app, "list_tools"):
        res = asyncio.run(mcp_app.list_tools())
        if hasattr(res, "tools"):
            return [t.name for t in res.tools]
        if isinstance(res, list):
            return [getattr(t, "name", str(t)) for t in res]
    if hasattr(mcp_app, "_tool_manager") and hasattr(mcp_app._tool_manager, "list_tools"):
        res = asyncio.run(mcp_app._tool_manager.list_tools())
        if hasattr(res, "tools"):
            return [t.name for t in res.tools]
    raise RuntimeError("Impossibile recuperare i nomi dei tool da MCPServer")


def test_richieste_senza_token_ritornano_401(client, servizio):
    p = servizio.crea_pratica("Pratica Senza Token")
    pid = p["pratica_id"]

    res_get = client.get(f"/api/pratiche/{pid}/invio")
    assert res_get.status_code == 401
    d_get = res_get.json()
    assert d_get["codice"] == "NON_AUTORIZZATO"

    res_post = client.post(f"/api/pratiche/{pid}/invio/prepara", json={})
    assert res_post.status_code == 401
    d_post = res_post.json()
    assert d_post["codice"] == "NON_AUTORIZZATO"


def test_invio_stato_lettura_pratica_esistente(client, servizio):
    p = servizio.crea_pratica("Pratica Test Stato Invio")
    pid = p["pratica_id"]

    res = client.get(f"/api/pratiche/{pid}/invio?t=sintetico")
    assert res.status_code == 200
    d = res.json()
    assert d["pratica_id"] == pid
    assert isinstance(d["copie"], list)
    assert len(d["copie"]) == 0


def test_invio_prepara_senza_export_completo_ritorna_errore(client, servizio):
    p = servizio.crea_pratica("Pratica Senza Export")
    pid = p["pratica_id"]

    res = client.post(f"/api/pratiche/{pid}/invio/prepara?t=sintetico", json={"chiave_richiesta": "k1"})
    assert res.status_code == 422
    d = res.json()
    assert d["codice"] == "DATI_NON_VALIDI"
    assert "file XML completo e aggiornato" in d["messaggio"]


def test_invio_prepara_pratica_inesistente(client):
    res = client.post("/api/pratiche/pratica_fantasma/invio/prepara?t=sintetico", json={})
    assert res.status_code == 404
    d = res.json()
    assert d["codice"] == "NON_TROVATO"
    assert "pratica inesistente" in d["messaggio"].lower()


def test_invio_conferma_copia_inesistente_non_da_500(client):
    res = client.post("/api/invio/copia_fantasma/conferma?t=sintetico", json={"impronta": "123456"})
    assert res.status_code != 500
    assert res.status_code in (404, 422)
    d = res.json()
    assert d["codice"] in ("NON_TROVATO", "DATI_NON_VALIDI")
    assert "tentativo inesistente" in d["messaggio"].lower()


def test_invio_trasmetti_copia_inesistente_non_da_500(client):
    res = client.post("/api/invio/copia_fantasma/trasmetti?t=sintetico", json={"chiave_richiesta": "k2"})
    assert res.status_code != 500
    assert res.status_code in (404, 422)
    d = res.json()
    assert d["codice"] in ("NON_TROVATO", "DATI_NON_VALIDI")
    assert "tentativo inesistente" in d["messaggio"].lower()


def test_mcp_strumenti_invio(servizio):
    srv = mcp_server.costruisci(servizio)
    nomi = _estrai_nomi_strumenti(srv)

    assert "successioni_invio_prepara" in nomi
    assert "successioni_invio_stato" in nomi
    assert "successioni_invio_conferma" not in nomi
    assert "successioni_invio_trasmetti" not in nomi
    assert not any("conferma" in n for n in nomi)
    assert not any("trasmetti" in n for n in nomi)
