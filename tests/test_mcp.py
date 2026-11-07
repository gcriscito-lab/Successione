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


def test_ce01_mcp_esporta_caso_completo_intermediario_con_allegati(tmp_path):
    from test_correzioni_codex import pratica_con_allegati
    from telematico_casi import CF_LUCA
    sv, pid = pratica_con_allegati(tmp_path)
    param = StdioServerParameters(command=sys.executable, args=['-m', 'successioni.mcp_server'],
                                  env={'SUCCESSIONI_DATA': str(sv.arch.base)})

    async def scenario():
        from mcp.client.session import ClientSession
        async with stdio_client(param) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                p = dati(await s.call_tool('successioni_leggi_pratica', {'pratica_id': pid}))
                aid = p['dati']['documenti_ref'][0]['allegato_id']
                aggiornamento = await s.call_tool('successioni_aggiorna_pratica', {
                    'pratica_id': pid, 'revisione_attesa': p['revisione'], 'chiave_richiesta': 'ce01-profilo',
                    'operazioni': [
                        {'op': 'set', 'sezione': 'opzioni', 'campi': {'fornitore': {
                            'cf': CF_LUCA, 'tipo': '10', 'impegno_codice': '2', 'data_impegno': '2026-10-30'}}},
                        {'op': 'upsert', 'coll': 'documenti_ref', 'id': 'dr_identita',
                         'campi': {'allegato_id': aid, 'tipo_eg': 'DocumentiIdentita'}}]})
                assert not aggiornamento.is_error
                risposta = await s.call_tool('successioni_esporta_xml', {'pratica_id': pid})
                assert not risposta.is_error
                es = dati(risposta)
                assert es['generato'] and es['completo'] and es['avvisi'], es
                assert b'ImpegnoATrasmettere' in (sv.arch.base / es['percorso']).read_bytes()
    anyio.run(scenario)
    assert sv.leggi(pid)['revisione'] == 3


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
                assert {"successioni_aggiorna_pratica", "successioni_leggi_pratica", "successioni_verifica_pratica", "successioni_prepara_pdfa"} <= tools
                assert not any(x in tools for x in ("shell", "sql", "esegui"))
                c = dati(await s.call_tool("successioni_crea_pratica", {"titolo": "Rossi", "chiave_richiesta": "k1"}))
                pid = c["pratica_id"]
                op = [{"op": "upsert", "coll": "persone", "id": "p_aaaa1111",
                       "campi": {"cognome": "Rossi", "ruolo": "defunto"}}]
                r1 = dati(await s.call_tool("successioni_aggiorna_pratica", {"pratica_id": pid, "revisione_attesa": 1,
                                                                 "operazioni": op, "chiave_richiesta": "u1"}))
                assert r1["revisione"] == 2
                # la "GUI" vede subito la modifica nello stesso archivio
                assert sv.leggi(pid)["dati"]["persone"][0]["cognome"] == "Rossi"
                # modifica manuale, poi MCP con revisione obsoleta: errore leggibile, nessuna sovrascrittura
                sv.aggiorna(pid, 2, [{"op": "upsert", "coll": "persone", "id": "p_aaaa1111", "campi": {"cognome": "Bianchi"}}])
                res = await s.call_tool("successioni_aggiorna_pratica", {"pratica_id": pid, "revisione_attesa": 2,
                                        "operazioni": [{"op": "upsert", "coll": "persone", "id": "p_aaaa1111", "campi": {"cognome": "Verdi"}}],
                                        "chiave_richiesta": "u2"})
                assert res.is_error and "CONFLITTO_REVISIONE" in res.content[0].text
                assert sv.leggi(pid)["dati"]["persone"][0]["cognome"] == "Bianchi"
    anyio.run(scenario)


def test_mcp_annotazioni_prefisso_e_paginazione(tmp_path):
    base = tmp_path / "dati"
    param = StdioServerParameters(command=sys.executable, args=["-m", "successioni.mcp_server"],
                                  env={"SUCCESSIONI_DATA": str(base), "PATH": "/usr/bin:/bin"})

    async def scenario():
        from mcp.client.session import ClientSession
        async with stdio_client(param) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                tools = {t.name: t for t in (await s.list_tools()).tools}
                assert all(n.startswith("successioni_") for n in tools)
                assert tools["successioni_leggi_pratica"].annotations.read_only_hint is True
                assert tools["successioni_aggiorna_pratica"].annotations.read_only_hint is False
                assert tools["successioni_aggiorna_pratica"].annotations.destructive_hint is True   # ammette «remove» (revisione 2); le revisioni restano
                for i in range(3):
                    await s.call_tool("successioni_crea_pratica", {"titolo": f"P{i}", "chiave_richiesta": f"k{i}"})
                pag = dati(await s.call_tool("successioni_elenca_pratiche", {"limit": 2}))
                assert pag["totale"] == 3 and len(pag["elementi"]) == 2 and pag["has_more"] and pag["next_offset"] == 2
    anyio.run(scenario)


def test_mcp_stato_quadri_e_blocco_non_supportati(tmp_path):
    base = tmp_path / "dati"
    param = StdioServerParameters(command=sys.executable, args=["-m", "successioni.mcp_server"],
                                  env={"SUCCESSIONI_DATA": str(base), "PATH": "/usr/bin:/bin"})

    async def scenario():
        from mcp.client.session import ClientSession
        async with stdio_client(param) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                pid = dati(await s.call_tool("successioni_crea_pratica", {"titolo": "X", "chiave_richiesta": "k"}))["pratica_id"]
                await s.call_tool("successioni_aggiorna_pratica", {"pratica_id": pid, "revisione_attesa": 1, "chiave_richiesta": "u",
                    "operazioni": [{"op": "set", "sezione": "opzioni", "campi": {"quadri_attivi": ["EA", "EI"]}}]})
                st = dati(await s.call_tool("successioni_stato_quadri", {"pratica_id": pid}))
                assert st["finalizzabile"] is False
                assert {q["id"]: q["stato"] for q in st["quadri"]}["EI"] == "non_supportato"
                assert any(x["codice"] == "QUADRO_NON_SUPPORTATO" and x["quadro"] == "EI" for x in st["rilievi"])
    anyio.run(scenario)


def test_mcp_suddividi_allegato_oltre_limite(tmp_path):
    """Un PDF grande viene ridotto/suddiviso sotto il limite; l'originale resta invariato (A12). Richiede Ghostscript."""
    from successioni import pdfa
    if not pdfa.trova_gs():
        import pytest
        pytest.skip("Ghostscript non disponibile")
    import os
    from reportlab.pdfgen import canvas
    base = tmp_path / "dati"
    ingresso = base / "ingresso"; ingresso.mkdir(parents=True)
    f = ingresso / "grande.pdf"
    c = canvas.Canvas(str(f))
    for i in range(6):
        c.drawString(72, 750, f"pagina {i + 1}")
        c.drawInlineImage(__import__("PIL.Image", fromlist=["x"]).frombytes("RGB", (1400, 1400), os.urandom(1400 * 1400 * 3)), 20, 20, 500, 500)
        c.showPage()
    c.save()
    assert f.stat().st_size > 5_000_000
    param = StdioServerParameters(command=sys.executable, args=["-m", "successioni.mcp_server"],
                                  env={"SUCCESSIONI_DATA": str(base), "PATH": os.environ.get('PATH', ''),
                                       "SUCCESSIONI_GS": pdfa.trova_gs(), "SUCCESSIONI_ICC": pdfa._icc()})

    async def scenario():
        from mcp.client.session import ClientSession
        async with stdio_client(param) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                pid = dati(await s.call_tool("successioni_crea_pratica", {"titolo": "X", "chiave_richiesta": "k"}))["pratica_id"]
                a = dati(await s.call_tool("successioni_acquisisci_allegato", {"pratica_id": pid, "nome_file": "grande.pdf"}))
                res = await s.call_tool("successioni_suddividi_allegato", {"allegato_id": a["allegato_id"]})
                assert not res.is_error, res.content[0].text[:300]
                lista = dati(await s.call_tool("successioni_elenca_allegati", {"pratica_id": pid}))
                derivati = [x for x in lista if x["ruolo"] == "derivato"]
                assert derivati and all(x["bytes"] <= 5_000_000 for x in derivati)
                orig = [x for x in lista if x["ruolo"] == "originale"][0]
                assert orig["bytes"] == f.stat().st_size
    anyio.run(scenario)
