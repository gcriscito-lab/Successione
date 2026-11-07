"""Revisione 3 (7/11/2026 sera): archivio, server web e avvio (dati sintetici, archivi temporanei).

1. connessione di lettura riusata solo durante un'operazione: a riposo nessun file del database aperto (anche con un
   server MCP fermo), file principale autosufficiente dopo la chiusura, chiudi() da un altro thread;
2. endpoint web eseguiti in un thread: richieste lente in parallelo, «database is locked» e OSError come errori di servizio;
3. interfaccia e server MCP avviati dall'avviatore leggono lo stesso file di configurazione (due processi);
4. in sola lettura invio_stato/stato_elaborati non scrivono (consultazione annullata).
"""
import asyncio
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

import pytest
from mcp.client import Client
from starlette.testclient import TestClient

from successioni import impostazioni
from successioni.archivio import Archivio
from successioni.integrita import verifica_copia
from successioni.mcp_server import costruisci
from successioni.servizio import Servizio
from successioni.web import crea_app

RADICE = Path(__file__).resolve().parents[1]
WIN = RADICE / "scripts" / "windows"
SRC = RADICE / "src"


@pytest.fixture(autouse=True)
def _isola(monkeypatch, tmp_path):
    monkeypatch.delenv("SUCCESSIONI_MCP_SOLA_LETTURA", raising=False)
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(tmp_path / "cfg" / "configurazione.json"))
    monkeypatch.setenv("SUCCESSIONI_DATA", str(tmp_path / "dati"))


def _env_figlio(**extra) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("SUCCESSIONI_")}
    env["PYTHONPATH"] = str(SRC)
    env.update(extra)
    return env


def chiama(sv, nome, args=None):
    async def scenario():
        async with Client(costruisci(sv)) as c:
            return await c.call_tool("successioni_" + nome, args or {})
    return asyncio.run(scenario())


def dati(res):
    sc = res.structured_content
    if sc is not None:
        return sc.get("result", sc) if isinstance(sc, dict) else sc
    return json.loads(res.content[0].text)


def _con_pratiche(base: Path, n: int = 3) -> Servizio:
    sv = Servizio(Archivio(base))
    for i in range(n):
        sv.crea_pratica(f"Pratica {i}", iniziali=[{"op": "upsert", "coll": "persone", "id": "p_defunto1",
                                                   "campi": {"ruolo": "defunto", "cognome": f"Prova{i}",
                                                             "data_decesso": "2026-03-01"}}])
    return sv


def _rinomina_da_altro_processo(da: Path, a: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-c", "import os,sys; os.rename(sys.argv[1], sys.argv[2])", str(da), str(a)],
                          capture_output=True, text=True, timeout=30)


# ------------------------------------------------------------------------------------- 1. sessioni di lettura
def test_sessione_riusa_una_connessione_e_la_chiude_alla_fine(tmp_path):
    a = Archivio(tmp_path / "d")
    with a.sessione_letture():
        assert a._aperte == []                        # aperta solo alla prima lettura (richieste senza archivio)
        with a.lettura() as c1, a.lettura() as c2:
            assert c1 is c2
        with a.lettura() as c3:
            assert c3 is c1
        assert a._aperte == [c1]
    assert a._aperte == []
    with pytest.raises(sqlite3.ProgrammingError):
        c1.execute("SELECT 1")                        # chiusa a fine sessione
    with a.lettura() as c4:                           # fuori sessione: aperta e chiusa per l'occasione
        assert c4 is not c1
    assert a._aperte == []


def test_dopo_le_operazioni_il_file_principale_contiene_tutto(tmp_path):
    base = tmp_path / "d"
    sv = _con_pratiche(base, 4)
    with sv.arch.sessione_letture():
        assert len(sv.elenca()) == 4
    wal = base / "archivio.sqlite3-wal"
    assert not wal.exists() or wal.stat().st_size == 0, "il WAL deve essere svuotato alla chiusura"
    c = sqlite3.connect((base / "archivio.sqlite3").resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        assert c.execute("SELECT COUNT(*) FROM pratiche").fetchone()[0] == 4      # senza WAL: dati nel file principale
    finally:
        c.close()
    verifica_copia(base, 1)                                                      # integrita.py la accetta
    dest = Archivio(tmp_path / "nuova")
    dest.ripristina(base)                                                        # e si ripristina
    assert len(Servizio(dest).elenca()) == 4


def test_verifica_backup_su_cartella_chiusa_non_dice_in_uso(tmp_path):
    base = tmp_path / "d"
    _con_pratiche(base, 2)
    r = subprocess.run([sys.executable, str(WIN / "verifica_backup.py"), str(base)], capture_output=True, text=True,
                       timeout=60, env=_env_figlio())
    out = json.loads(r.stdout)
    assert not any("in uso" in p for p in out["problemi"]), out["problemi"]
    assert len(out["pratiche"]) == 2


def test_chiudi_da_un_altro_thread_chiude_davvero(tmp_path):
    a = Archivio(tmp_path / "d")
    pronta, fine = threading.Event(), threading.Event()
    conn = {}

    def lavoro():
        with a.sessione_letture():
            with a.lettura() as c:
                conn["c"] = c
            pronta.set()
            fine.wait(10)
            with a.lettura() as c:                     # dopo chiudi() la sessione riapre una connessione
                conn["dopo"] = c.execute("SELECT COUNT(*) FROM pratiche").fetchone()[0]

    t = threading.Thread(target=lavoro)
    t.start()
    pronta.wait(10)
    a.chiudi()                                         # dal thread principale
    with pytest.raises(sqlite3.ProgrammingError):
        conn["c"].execute("SELECT 1")
    fine.set()
    t.join(10)
    assert conn["dopo"] == 0
    assert a._aperte == []


def test_server_mcp_fermo_non_blocca_la_cartella_dati(tmp_path):
    """Claude Desktop aperto ma inattivo: dopo una chiamata nessun file del database resta aperto, la cartella si rinomina
    da un altro processo."""
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    base = tmp_path / "dati"
    _con_pratiche(base, 2)
    spostata = tmp_path / "dati-spostata"
    param = StdioServerParameters(command=sys.executable, args=["-m", "successioni.mcp_server"],
                                  env=_env_figlio(SUCCESSIONI_DATA=str(base),
                                                  SUCCESSIONI_CONFIG=str(tmp_path / "cfg" / "configurazione.json")))
    esiti = {}

    async def scenario():
        async with stdio_client(param) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                esiti["prima"] = dati(await s.call_tool("successioni_elenca_pratiche", {}))["totale"]
                await s.call_tool("successioni_crea_pratica", {"titolo": "Da MCP", "chiave_richiesta": "r3-1"})
                esiti["rinomina"] = _rinomina_da_altro_processo(base, spostata)
                if esiti["rinomina"].returncode == 0:
                    _rinomina_da_altro_processo(spostata, base)
                esiti["dopo"] = dati(await s.call_tool("successioni_elenca_pratiche", {}))["totale"]
    asyncio.run(scenario())
    assert esiti["prima"] == 2
    assert esiti["rinomina"].returncode == 0, esiti["rinomina"].stderr
    assert esiti["dopo"] == 3


def test_cruscotto_resta_veloce_in_una_sessione(tmp_path):
    from successioni import cruscotto
    sv = _con_pratiche(tmp_path / "d", 11)
    cruscotto.cruscotto(sv)                                    # riscaldamento (import, cache)
    t0 = time.perf_counter()
    with sv.arch.sessione_letture():                           # come la richiesta /api/cruscotto
        c = cruscotto.cruscotto(sv)
    durata = time.perf_counter() - t0
    assert len(c["pratiche"]) == 11
    assert durata < 0.6, durata                                # misura locale ~0,1-0,2 s; prima dell'ottimizzazione 1,3 s


# ------------------------------------------------------------------------------------- 2. server web
def _porta_libera() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_richieste_lente_in_parallelo_non_bloccano_l_interfaccia(tmp_path):
    import uvicorn
    sv = _con_pratiche(tmp_path / "d", 1)
    originale = sv.elenca

    def lenta():
        time.sleep(1.0)                                        # come Ghostscript/Java/backup: codice sincrono
        return originale()
    sv.elenca = lenta
    porta = _porta_libera()
    server = uvicorn.Server(uvicorn.Config(crea_app(sv, token="tk", porta=porta), host="127.0.0.1", port=porta,
                                           log_level="warning"))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    try:
        for _ in range(100):
            if server.started:
                break
            time.sleep(0.05)

        def get(percorso):
            req = urllib.request.Request(f"http://127.0.0.1:{porta}{percorso}", headers={"x-successioni-token": "tk"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read())
        risultati, durate = [], {}

        def lenta_get(i):
            risultati.append(get("/api/pratiche"))
        t0 = time.perf_counter()
        fili = [threading.Thread(target=lenta_get, args=(i,)) for i in range(3)]
        for f in fili:
            f.start()
        time.sleep(0.2)
        t1 = time.perf_counter()
        stato, info = get("/api/info")                          # l'interfaccia risponde mentre le 3 lente lavorano
        durate["info"] = time.perf_counter() - t1
        for f in fili:
            f.join(20)
        durate["tre_lente"] = time.perf_counter() - t0
    finally:
        server.should_exit = True
        t.join(10)
    assert stato == 200 and info["versione"]
    assert [r[0] for r in risultati] == [200, 200, 200] and all(len(r[1]) == 1 for r in risultati)
    assert durate["info"] < 0.5, durate                          # non aspetta le richieste lente
    assert durate["tre_lente"] < 2.5, durate                     # in parallelo (in serie sarebbero almeno 3 s)


def test_corpo_della_richiesta_e_limiti_funzionano_nel_thread(tmp_path):
    sv = _con_pratiche(tmp_path / "d", 0)
    cl = TestClient(crea_app(sv, token="tk", porta=8765), base_url="http://127.0.0.1:8765", headers={"x-successioni-token": "tk"})
    r = cl.post("/api/pratiche", json={"titolo": "Dal thread"})
    assert r.status_code == 200 and r.json()["pratica_id"]
    r = cl.post("/api/calcolatrice", content=b"x" * 200_001)
    assert r.status_code == 413
    r = cl.post("/api/allegati/xyz/pdfa", headers={"origin": "http://evil.example"})
    assert r.status_code == 403                                  # Origin ancora controllato prima del thread


def test_archivio_occupato_e_errori_di_file_sono_errori_di_servizio(tmp_path):
    sv = _con_pratiche(tmp_path / "d", 1)
    cl = TestClient(crea_app(sv, token="tk", porta=8765), base_url="http://127.0.0.1:8765", headers={"x-successioni-token": "tk"})

    def bloccato():
        raise sqlite3.OperationalError("database is locked")
    sv.elenca = bloccato
    r = cl.get("/api/pratiche")
    assert r.status_code == 503 and r.json()["codice"] == "ARCHIVIO_OCCUPATO" and "riprova" in r.json()["messaggio"].lower()
    assert r.headers.get("retry-after")

    def in_uso():
        raise PermissionError(13, "Accesso negato", "C:/dati/file.pdf")
    sv.elenca = in_uso
    r = cl.get("/api/pratiche")
    assert r.status_code == 409 and r.json()["codice"] == "FILE_IN_USO" and "file.pdf" in r.json()["messaggio"]

    def disco():
        raise OSError(28, "Spazio insufficiente sul disco")
    sv.elenca = disco
    r = cl.get("/api/pratiche")
    assert r.status_code == 503 and r.json()["codice"] == "ERRORE_FILE"


def test_blocco_reale_dell_archivio_diventa_503(tmp_path):
    sv = _con_pratiche(tmp_path / "d", 1)
    pid = sv.elenca()[0]["id"]
    rev = sv.leggi(pid)["revisione"]
    cl = TestClient(crea_app(sv, token="tk", porta=8765), base_url="http://127.0.0.1:8765", headers={"x-successioni-token": "tk"})
    blocco = sqlite3.connect(sv.arch.db_path, isolation_level=None)
    blocco.execute("BEGIN IMMEDIATE")                              # un altro processo tiene la scrittura
    originale = sv.arch._apri

    def apri_rapida(condivisa=False):
        c = originale(condivisa)
        c.execute("PRAGMA busy_timeout=200")
        return c
    sv.arch._apri = apri_rapida
    try:
        r = cl.post(f"/api/pratiche/{pid}/aggiorna", json={"revisione_attesa": rev, "operazioni": [
            {"op": "set", "sezione": "note", "campi": {"promemoria": "x"}}]})
    finally:
        blocco.execute("ROLLBACK")
        blocco.close()
    assert r.status_code == 503 and r.json()["codice"] == "ARCHIVIO_OCCUPATO"
    assert sv.leggi(pid)["revisione"] == rev


def test_mcp_archivio_occupato_messaggio_comprensibile(tmp_path):
    sv = _con_pratiche(tmp_path / "d", 1)

    def bloccato():
        raise sqlite3.OperationalError("database is locked")
    sv.elenca = bloccato
    r = chiama(sv, "elenca_pratiche")
    assert r.is_error and "ARCHIVIO_OCCUPATO" in r.content[0].text


# ------------------------------------------------------------------------------------- 3. stessa configurazione
def _pacchetto(tmp_path: Path) -> Path:
    """Struttura del pacchetto installato (<radice>/app/avvia_successioni.py, codice in app/src): la configurazione
    dell'avviatore finisce in <radice>/configurazione.json, dentro la cartella temporanea."""
    radice = tmp_path / "pacchetto"
    app = radice / "app"
    app.mkdir(parents=True)
    shutil.copy2(WIN / "avvia_successioni.py", app / "avvia_successioni.py")
    shutil.copytree(SRC / "successioni", app / "src" / "successioni", ignore=shutil.ignore_patterns("__pycache__"))
    return radice


def test_gui_e_mcp_leggono_lo_stesso_file_di_configurazione(tmp_path):
    radice = _pacchetto(tmp_path)
    base = tmp_path / "dati"
    env = {k: v for k, v in os.environ.items() if not k.startswith("SUCCESSIONI_") and k != "PYTHONPATH"}
    env["SUCCESSIONI_DATA"] = str(base)                       # come la voce di Claude Desktop: nessun SUCCESSIONI_CONFIG
    # processo 1 (interfaccia): l'avviatore prepara l'ambiente e le Impostazioni salvano «Claude in sola lettura»
    gui = ("import sys; sys.path.insert(0, sys.argv[1]); import avvia_successioni as A\n"
           "A.fissa_file_configurazione(); A.prepara_ambiente()\n"
           "from successioni import impostazioni\n"
           "impostazioni.salva({}, profilo={'cf': 'RSSMRA40A01H501K'}, preferenze_nuove={'mcp_sola_lettura': True})\n"
           "print(impostazioni.file_configurazione())")
    r = subprocess.run([sys.executable, "-s", "-c", gui, str(radice / "app")], env=env, capture_output=True, text=True,
                       timeout=60)
    assert r.returncode == 0, r.stderr
    assert Path(r.stdout.strip()) == radice / "configurazione.json"
    assert not (base / "configurazione.json").exists()
    # processo 2: server MCP avviato come da Claude Desktop (avvia_successioni.py mcp)
    p = subprocess.Popen([sys.executable, "-s", str(radice / "app" / "avvia_successioni.py"), "mcp"], env=env,
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def invia(o):
        p.stdin.write((json.dumps(o) + "\n").encode())
        p.stdin.flush()

    def risposta(i, nome, args):
        invia({"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": nome, "arguments": args}})
        m = json.loads(p.stdout.readline())
        assert m["id"] == i
        return m["result"]
    try:
        invia({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "prova-r3", "version": "0"}}})
        json.loads(p.stdout.readline())
        invia({"jsonrpc": "2.0", "method": "notifications/initialized"})
        cap = json.loads(risposta(2, "successioni_capacita", {})["content"][0]["text"])
        crea = risposta(3, "successioni_crea_pratica", {"titolo": "Non deve nascere", "chiave_richiesta": "r3-cfg"})
    finally:
        p.stdin.close()
        p.wait(timeout=15)
    assert cap["sola_lettura"] is True and "Impostazioni" in cap["motivo_sola_lettura"]
    assert crea["isError"] is True and "SOLA_LETTURA" in crea["content"][0]["text"]
    assert Servizio(Archivio(base)).elenca() == []
    # il profilo dello studio e' letto dallo stesso file
    assert json.loads((radice / "configurazione.json").read_text(encoding="utf-8"))["profilo"]["cf"] == "RSSMRA40A01H501K"


def test_fissa_file_configurazione_rispetta_ambiente(monkeypatch, tmp_path):
    sys.path.insert(0, str(WIN))
    try:
        import avvia_successioni as A
    finally:
        sys.path.remove(str(WIN))
    env = {}
    assert A.fissa_file_configurazione(env) == env["SUCCESSIONI_CONFIG"]
    env = {"SUCCESSIONI_CONFIG": str(tmp_path / "mio.json")}
    assert A.fissa_file_configurazione(env) == str(tmp_path / "mio.json")


# ------------------------------------------------------------------------------------- 4. consultazione
def test_consultazione_annulla_le_scritture_ma_le_mostra(tmp_path):
    a = Archivio(tmp_path / "d")
    with a.sessione_letture(consultazione=True):
        with a.transazione() as c:
            c.execute("INSERT INTO job(id,tipo,stato,creato,aggiornato) VALUES('j1','prova','a','t','t')")
        with a.transazione() as c:
            c.execute("UPDATE job SET stato='b' WHERE id='j1'")
        with a.lettura() as c:
            assert c.execute("SELECT stato FROM job WHERE id='j1'").fetchone()[0] == "b"   # visibile nell'operazione
    with a.lettura() as c:
        assert c.execute("SELECT COUNT(*) FROM job").fetchone()[0] == 0                  # ma non confermata


def test_sola_lettura_invio_stato_e_stato_elaborati_non_scrivono(tmp_path):
    sv = _con_pratiche(tmp_path / "d", 1)
    pid = sv.elenca()[0]["id"]
    chiamate = []

    def con_scrittura(nome, originale):
        def f(pratica_id):
            # come verifica_validita/_recupera_finale: allinea uno stato con una transazione, poi rilegge
            with sv.arch.transazione() as c:
                c.execute("INSERT INTO job(id,tipo,pratica_id,stato,creato,aggiornato) VALUES(?,?,?,?,?,?)",
                          (f"j-{nome}", "prova", pratica_id, "obsoleta", "t", "t"))
            with sv.arch.lettura() as c:
                visto = c.execute("SELECT stato FROM job WHERE id=?", (f"j-{nome}",)).fetchone()[0]
            chiamate.append((nome, visto))
            return {"visto": visto}
        return f
    sv.invio_stato = con_scrittura("invio", sv.invio_stato)
    sv.stato_elaborati = con_scrittura("elaborati", sv.stato_elaborati)
    impostazioni.salva({}, preferenze_nuove={"mcp_sola_lettura": True})
    for nome in ("invio_stato", "stato_elaborati"):
        r = chiama(sv, nome, {"pratica_id": pid})
        assert not r.is_error and dati(r)["visto"] == "obsoleta"
    with sv.arch.lettura() as c:
        assert c.execute("SELECT COUNT(*) FROM job WHERE tipo='prova'").fetchone()[0] == 0
    impostazioni.salva({}, preferenze_nuove={"mcp_sola_lettura": False})       # fuori dalla sola lettura si conferma
    assert not chiama(sv, "invio_stato", {"pratica_id": pid}).is_error
    with sv.arch.lettura() as c:
        assert c.execute("SELECT COUNT(*) FROM job WHERE tipo='prova'").fetchone()[0] == 1
