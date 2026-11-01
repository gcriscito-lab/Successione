"""Prova A03 lato server: processo MCP reale via stdio, stesso archivio del servizio (GUI)."""
import json
import sys
import anyio
import pytest
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters, stdio_client
from successioni.archivio import Archivio
from successioni.servizio import Servizio


def dati(res):
    if res.structured_content is not None:
        sc = res.structured_content
        return sc.get("result", sc) if isinstance(sc, dict) else sc
    return json.loads(res.content[0].text)


def test_mcp_stdio_stessa_pratica_della_gui(tmp_path):
    base = tmp_path / "dati"
    sv = Servizio(Archivio(base))            # "interfaccia"
    param = StdioServerParameters(command=sys.executable, args=["-m", "successioni.mcp_server"],
                                  env={"SUCCESSIONI_DATA": str(base), "PATH": "/usr/bin:/bin"})

    async def scenario():
        from mcp.client.session import ClientSession
        async with stdio_client(param) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                tools = {t.name for t in (await s.list_tools()).tools}
                assert {"aggiorna_pratica", "leggi_pratica", "verifica_pratica", "prepara_pdfa"} <= tools
                assert not any(x in tools for x in ("shell", "sql", "esegui"))
                c = dati(await s.call_tool("crea_pratica", {"titolo": "Rossi", "chiave_richiesta": "k1"}))
                pid = c["pratica_id"]
                op = [{"op": "upsert", "coll": "persone", "id": "p_aaaa1111",
                       "campi": {"cognome": "Rossi", "ruolo": "defunto"}}]
                r1 = dati(await s.call_tool("aggiorna_pratica", {"pratica_id": pid, "revisione_attesa": 1,
                                                                 "operazioni": op, "chiave_richiesta": "u1"}))
                assert r1["revisione"] == 2
                # la "GUI" vede subito la modifica nello stesso archivio
                assert sv.leggi(pid)["dati"]["persone"][0]["cognome"] == "Rossi"
                # modifica manuale, poi MCP con revisione obsoleta: errore leggibile, nessuna sovrascrittura
                sv.aggiorna(pid, 2, [{"op": "upsert", "coll": "persone", "id": "p_aaaa1111", "campi": {"cognome": "Bianchi"}}])
                res = await s.call_tool("aggiorna_pratica", {"pratica_id": pid, "revisione_attesa": 2,
                                        "operazioni": [{"op": "upsert", "coll": "persone", "id": "p_aaaa1111", "campi": {"cognome": "Verdi"}}],
                                        "chiave_richiesta": "u2"})
                assert res.is_error and "CONFLITTO_REVISIONE" in res.content[0].text
                assert sv.leggi(pid)["dati"]["persone"][0]["cognome"] == "Bianchi"
    anyio.run(scenario)
