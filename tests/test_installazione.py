"""Area 4: avviatore, diagnosi, configurazione MCP e montaggio del pacchetto Windows.

Prove eseguite su Linux: verificano la logica e i processi reali (GUI su 127.0.0.1, server MCP su stdio) con i
file del pacchetto. Non provano l'avvio su Windows ne' il client Claude effettivo (da collaudare, vedi
docs/INSTALLAZIONE_WINDOWS.md e docs/CONFIGURAZIONE_MCP.md).
"""
import importlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
WIN = RADICE / "scripts" / "windows"
sys.path.insert(0, str(WIN))
sys.path.insert(0, str(RADICE / "packaging"))

A = importlib.import_module("avvia_successioni")
DIAG = importlib.import_module("diagnosi")
CFG = importlib.import_module("configura_mcp")
PKG = importlib.import_module("costruisci_pacchetto")

NOME_ITALIANO = "Studio Rossi è à ù/Dati pratiche"


def _ferma_avviatore(proc):
    """La venv Windows usa un launcher padre: chiude anche il server figlio del test."""
    if os.name == 'nt' and proc.poll() is None:
        subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True, timeout=15)
    elif proc.poll() is None:
        proc.terminate()
    proc.wait(timeout=10)


def _env(base: Path, **extra) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("SUCCESSIONI_")}
    env.update({"SUCCESSIONI_DATA": str(base), "SUCCESSIONI_CONFIG": str(base.parent / "configurazione.json")})
    env.update(extra)
    return env


def _get(url: str, host: str | None = None) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"Host": host} if host else {})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _attendi_sessione(base: Path, proc, secondi=20) -> dict:
    fine = time.time() + secondi
    while time.time() < fine:
        p = base / A.NOME_SESSIONE
        if p.exists():
            s = json.loads(p.read_text(encoding="utf-8"))
            try:
                if _get(f"http://127.0.0.1:{s['porta']}/api/info?t={s['token']}")[0] == 200:
                    return s
            except OSError:
                pass
        if proc.poll() is not None:
            raise AssertionError(f"avviatore terminato: {proc.stdout.read() if proc.stdout else ''}")
        time.sleep(0.2)
    raise AssertionError("interfaccia non avviata entro il tempo previsto")


# ------------------------------------------------------------------------------------------------ avviatore
def test_configurazione_solo_variabili_note_e_ambiente_prevale(tmp_path, monkeypatch):
    conf = tmp_path / "configurazione.json"
    conf.write_text(json.dumps({"SUCCESSIONI_GS": "C:/gs/gswin64c.exe", "SUCCESSIONI_DATA": "D:/dati",
                                "PATH": "x", "SUCCESSIONI_PASSWORD": "segreto", "SUCCESSIONI_JAVA": 3}),
                    encoding="utf-8")
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(conf))
    assert A.leggi_configurazione() == {"SUCCESSIONI_GS": "C:/gs/gswin64c.exe", "SUCCESSIONI_DATA": "D:/dati"}
    env = {"SUCCESSIONI_DATA": "E:/altro"}
    origini = A.prepara_ambiente(env, windows=False)
    assert env["SUCCESSIONI_DATA"] == "E:/altro" and env["SUCCESSIONI_GS"] == "C:/gs/gswin64c.exe"
    assert origini == {"SUCCESSIONI_GS": "configurazione.json"} and "PATH" not in env


def test_configurazione_illeggibile_ignorata(tmp_path, monkeypatch):
    conf = tmp_path / "configurazione.json"
    conf.write_text("{ non json", encoding="utf-8")
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(conf))
    assert A.leggi_configurazione() == {}


def test_candidati_windows_cartelle_standard_versione_piu_recente(tmp_path, monkeypatch):
    glob_reale = A.glob.glob
    monkeypatch.setattr(A.glob, "glob", lambda pattern: glob_reale(pattern) if str(pattern).startswith(str(tmp_path)) else [])
    pf = tmp_path / "Program Files"
    for v in ("gs10.02.1", "gs10.05.0", "gs9.56.1"):
        (pf / "gs" / v / "bin").mkdir(parents=True)
        (pf / "gs" / v / "bin" / "gswin64c.exe").write_bytes(b"")
    (pf / "Eclipse Adoptium" / "jre-21.0.5.11-hotspot" / "bin").mkdir(parents=True)
    (pf / "Eclipse Adoptium" / "jre-21.0.5.11-hotspot" / "bin" / "java.exe").write_bytes(b"")
    (pf / "veraPDF").mkdir()
    (pf / "veraPDF" / "verapdf.bat").write_bytes(b"")
    c = A.candidati_windows({"ProgramFiles": str(pf), "ProgramFiles(x86)": str(tmp_path / "nessuna")})
    assert c["SUCCESSIONI_GS"].endswith(str(Path("gs10.05.0") / "bin" / "gswin64c.exe"))
    assert c["SUCCESSIONI_JAVA"].endswith("java.exe") and c["SUCCESSIONI_VERAPDF"].endswith("verapdf.bat")
    assert "SUCCESSIONI_QPDF" not in c                              # solo file esistenti



def test_candidati_windows_ghostscript_in_cartella_c_gs():
    # installazione silenziosa con /D=C:\gs\gs10.08.0: cartella non standard, cercata dopo Program Files
    import glob
    if not glob.glob(r"C:\gs\gs*\bin\gswin64c.exe"):
        pytest.skip(r"Ghostscript non installato in C:\gs su questo PC")
    c = A.candidati_windows({"ProgramFiles": r"C:\nessuna1", "ProgramFiles(x86)": r"C:\nessuna2"})
    assert c["SUCCESSIONI_GS"].lower().startswith(r"c:\gs" + "\\") and c["SUCCESSIONI_GS"].endswith("gswin64c.exe")


def test_gui_localhost_token_host_e_seconda_apertura(tmp_path):
    base = tmp_path / NOME_ITALIANO
    env = _env(base)
    p = subprocess.Popen([sys.executable, "-s", str(WIN / "avvia_successioni.py"), "gui", "--no-browser"],
                         env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        s = _attendi_sessione(base, p)
        porta, tok = s["porta"], s["token"]
        assert porta in A.PORTE
        # Identita' del server che risponde, non del launcher della venv.
        assert json.loads(_get(f"http://127.0.0.1:{porta}/api/info?t={tok}")[1])['pid'] == s['pid']
        st, corpo = _get(f"http://127.0.0.1:{porta}/?t={tok}")
        assert st == 200 and b"<html" in corpo.lower()
        assert _get(f"http://127.0.0.1:{porta}/static/app.js?t={tok}")[0] == 200
        assert _get(f"http://127.0.0.1:{porta}/")[0] == 401                       # senza token
        assert _get(f"http://127.0.0.1:{porta}/?t={tok}", host=f"esempio.it:{porta}")[0] == 403  # Host estraneo
        # solo loopback: su un indirizzo non di loopback della macchina la porta non risponde
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except OSError:
            ip = "127.0.0.1"
        if not ip.startswith("127."):
            with socket.socket() as so:
                so.settimeout(2)
                assert so.connect_ex((ip, porta)) != 0
        # secondo doppio clic: nessun secondo server, riapre la sessione esistente
        t0 = time.time()
        r = subprocess.run([sys.executable, "-s", str(WIN / "avvia_successioni.py"), "gui", "--no-browser"],
                           env=env, capture_output=True, text=True, timeout=30)
        assert r.returncode == 0 and "gia' aperto" in r.stdout and f":{porta}/" in r.stdout
        assert time.time() - t0 < 20
        assert (base / "archivio.sqlite3").exists()
    finally:
        _ferma_avviatore(p)


def test_gui_senza_console_come_pythonw(tmp_path):
    """pythonw.exe: sys.stdout e sys.stderr valgono None. L'avviatore deve partire e scrivere un log."""
    base = tmp_path / "dati è"
    codice = ("import sys, runpy; sys.stdout = None; sys.stderr = None; "
              f"sys.argv = ['avvia_successioni.py', 'gui', '--no-browser']; "
              f"runpy.run_path({str(WIN / 'avvia_successioni.py')!r}, run_name='__main__')")
    p = subprocess.Popen([sys.executable, "-s", "-c", codice], env=_env(base))
    try:
        s = _attendi_sessione(base, p)
        assert _get(f"http://127.0.0.1:{s['porta']}/api/info?t={s['token']}")[0] == 200
        log = (base / "log" / "avvio.log").read_text(encoding="utf-8")
        assert f"127.0.0.1:{s['porta']}" in log
    finally:
        _ferma_avviatore(p)


def test_sessione_scaduta_non_blocca_un_nuovo_avvio(tmp_path):
    base = tmp_path / "dati"
    base.mkdir()
    (base / A.NOME_SESSIONE).write_text(json.dumps({"porta": 8799, "token": "vecchio", "pid": 1}), encoding="utf-8")
    assert A.sessione_attiva(base) is None


# ------------------------------------------------------------------------------------------ server MCP stdio
def test_mcp_stdio_tramite_avviatore_stesso_archivio_e_chiusura(tmp_path):
    from successioni.archivio import Archivio
    from successioni.servizio import Servizio
    base = tmp_path / NOME_ITALIANO
    p = subprocess.Popen([sys.executable, "-s", str(WIN / "avvia_successioni.py"), "mcp"], env=_env(base),
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    righe_stdout = []

    def invia(o):
        p.stdin.write((json.dumps(o) + "\n").encode())
        p.stdin.flush()

    def ricevi():
        riga = p.stdout.readline()
        righe_stdout.append(riga)
        return json.loads(riga)

    def chiama(i, nome, args):
        invia({"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": nome, "arguments": args}})
        r = ricevi()
        assert r["id"] == i
        return r["result"]

    try:
        invia({"jsonrpc": "2.0", "id": 1, "method": "initialize",
               "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                          "clientInfo": {"name": "prova-area4", "version": "0"}}})
        init = ricevi()["result"]
        assert init["serverInfo"]["name"] == "successioni"
        invia({"jsonrpc": "2.0", "method": "notifications/initialized"})
        invia({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        nomi = [t["name"] for t in ricevi()["result"]["tools"]]
        assert nomi and all(n.startswith("successioni_") for n in nomi)
        assert {"successioni_capacita", "successioni_crea_pratica", "successioni_aggiorna_pratica",
                "successioni_leggi_pratica"} <= set(nomi)
        cap = json.loads(chiama(3, "successioni_capacita", {})["content"][0]["text"])
        assert Path(cap["cartella_ingresso"]) == base / "ingresso"      # stesso archivio dell'interfaccia
        r = json.loads(chiama(4, "successioni_crea_pratica", {"titolo": "Prova A03", "chiave_richiesta": "a03-1"})
                       ["content"][0]["text"])
        pid = r["pratica_id"]
        # modifica "manuale" (canale gui) nello stesso archivio mentre il server MCP e' aperto
        sv = Servizio(Archivio(base))
        sv.aggiorna(pid, 1, [{"op": "set", "sezione": "note", "campi": {"promemoria": "da GUI"}}])
        letto = json.loads(chiama(5, "successioni_leggi_pratica", {"pratica_id": pid})["content"][0]["text"])
        assert letto["revisione"] == 2 and letto["dati"]["note"]["promemoria"] == "da GUI"
        conflitto = chiama(6, "successioni_aggiorna_pratica",
                           {"pratica_id": pid, "revisione_attesa": 1, "chiave_richiesta": "a03-2",
                            "operazioni": [{"op": "set", "sezione": "note", "campi": {"promemoria": "da MCP"}}]})
        assert conflitto["isError"] is True and "CONFLITTO_REVISIONE" in conflitto["content"][0]["text"]
    finally:
        t0 = time.time()
        p.stdin.close()                       # come Claude Code su Windows: chiude stdin, poi termina il processo
        rc = p.wait(timeout=10)
        durata = time.time() - t0
    assert rc == 0 and durata < 5
    assert all(json.loads(r) for r in righe_stdout)                         # stdout: solo JSON-RPC
    sv = Servizio(Archivio(base))
    assert sv.leggi(pid)["dati"]["note"]["promemoria"] == "da GUI"        # nessuna sovrascrittura
    assert [r["canale"] for r in sv.revisioni(pid)] == ["mcp", "gui"]     # lo stato e' nell'archivio


# --------------------------------------------------------------------------------------------------- diagnosi
def test_diagnosi_linux_avviabile_e_coerente_con_gli_strumenti(tmp_path, monkeypatch):
    base = tmp_path / "Dati è à"
    monkeypatch.setenv("SUCCESSIONI_DATA", str(base))
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(tmp_path / "configurazione.json"))
    r = DIAG.diagnosi(windows=False)
    voci = {v["nome"]: v for v in r["voci"]}
    assert r["esito"] == "avviabile" and r["bloccanti"] == []
    for n in ("sistema", "python_dipendenze", "cartella_dati", "sqlite_wal", "percorsi_italiani", "fonti",
              "ghostscript", "verapdf", "java", "porta_gui"):
        assert n in voci
    assert voci["sqlite_wal"]["stato"] == "ok" and voci["percorsi_italiani"]["stato"] == "ok"
    from successioni import pdfa
    assert (voci["ghostscript"]["stato"] == "ok") == bool(pdfa.trova_gs())
    assert (voci["verapdf"]["stato"] == "ok") == bool(pdfa.trova_verapdf())
    assert not (base / "archivio.sqlite3").exists()                       # la diagnosi non crea l'archivio
    assert [p.name for p in base.iterdir()] == []                         # e non lascia file di prova


def test_diagnosi_avvisa_cartella_sincronizzata(tmp_path, monkeypatch):
    base = tmp_path / "OneDrive - Studio" / "Successioni"
    monkeypatch.setenv("SUCCESSIONI_DATA", str(base))
    voce = next(v for v in DIAG.controlla_cartella_dati(base) if v["nome"] == "cartella_dati")
    assert voce["stato"] == "avviso" and "WAL" in voce["rimedio"]


def test_diagnosi_salva_configurazione_solo_strumenti_trovati(tmp_path, monkeypatch):
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(tmp_path / "configurazione.json"))
    r = {"voci": [{"nome": "ghostscript", "stato": "ok", "percorso": "C:/gs/bin/gswin64c.exe"},
                  {"nome": "verapdf", "stato": "avviso"}, {"nome": "java", "stato": "ok", "percorso": "C:/j/java.exe"}]}
    p = DIAG.salva_configurazione(r)
    assert json.loads(p.read_text(encoding="utf-8")) == {"SUCCESSIONI_GS": "C:/gs/bin/gswin64c.exe",
                                                         "SUCCESSIONI_JAVA": "C:/j/java.exe"}


# ----------------------------------------------------------------------------------------- configurazione MCP
def test_configura_claude_desktop_conserva_le_altre_voci_con_copia(tmp_path):
    f = tmp_path / "Claude è" / "claude_desktop_config.json"
    f.parent.mkdir()
    f.write_text(json.dumps({"mcpServers": {"altro": {"command": "x"}}, "globalShortcut": "Ctrl+Space"}),
                 encoding="utf-8-sig")
    voce = {"command": r"C:\Users\Niccolò Rossi\AppData\Local\Programs\Successioni\python\python.exe",
            "args": ["-s", r"C:\Users\Niccolò Rossi\AppData\Local\Programs\Successioni\app\avvia_successioni.py", "mcp"]}
    r = CFG.unisci_claude_desktop(f, voce)
    d = json.loads(f.read_text(encoding="utf-8"))
    assert r["modificato"] and Path(r["copia"]).exists()
    assert d["mcpServers"]["altro"] == {"command": "x"} and d["globalShortcut"] == "Ctrl+Space"
    assert d["mcpServers"]["successioni"] == voce
    assert CFG.unisci_claude_desktop(f, voce)["modificato"] is False      # idempotente, nessuna nuova copia
    assert len(list(f.parent.glob("*.bak-*"))) == 1


def test_configura_claude_desktop_non_tocca_un_file_non_valido(tmp_path):
    f = tmp_path / "claude_desktop_config.json"
    f.write_text('{"mcpServers": {"altro": {}},}', encoding="utf-8")
    prima = f.read_bytes()
    with pytest.raises(SystemExit):
        CFG.unisci_claude_desktop(f, {"command": "x", "args": []})
    assert f.read_bytes() == prima and not list(tmp_path.glob("*.bak-*"))


def test_comando_claude_code_con_percorsi_con_spazi():
    voce = {"command": r"C:\Users\Anna Maria\AppData\Local\Programs\Successioni\python\python.exe",
            "args": ["-s", r"C:\Users\Anna Maria\AppData\Local\Programs\Successioni\app\avvia_successioni.py", "mcp"],
            "env": {"SUCCESSIONI_DATA": r"D:\Studio Rossi\Successioni"}}
    c = CFG.comando_claude_code(voce)
    assert c.startswith("claude mcp add --env SUCCESSIONI_DATA=\"D:\\Studio Rossi\\Successioni\" --transport stdio "
                        "--scope user successioni -- ")
    assert c.endswith('"C:\\Users\\Anna Maria\\AppData\\Local\\Programs\\Successioni\\python\\python.exe" -s '
                      '"C:\\Users\\Anna Maria\\AppData\\Local\\Programs\\Successioni\\app\\avvia_successioni.py" mcp')


# ------------------------------------------------------------------------------------------------- pacchetto
def _embed_finto(tmp_path) -> Path:
    z = tmp_path / "python-embed-finto.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for n in ("python.exe", "pythonw.exe", "python313.dll", "python313.zip", "_sqlite3.pyd", "sqlite3.dll",
                  "vcruntime140.dll"):
            zf.writestr(n, b"finto")
        zf.writestr("python313._pth", "python313.zip\r\n.\r\n\r\n#import site\r\n")
    return z


def test_montaggio_pacchetto_offline_struttura_e_file_windows(tmp_path):
    cfg = json.loads(PKG.VERSIONI.read_text(encoding="utf-8"))
    out = tmp_path / "dist" / "Successioni-prova-win64"
    man = PKG.assembla(out, _embed_finto(tmp_path), cfg, None, None, con_wheel=False)
    assert PKG.verifica(out, con_wheel=False) == []
    pth = (out / "python" / "python313._pth").read_bytes().decode("ascii").split("\r\n")
    assert pth[:4] == ["python313.zip", ".", r"Lib\site-packages", r"..\app\src"] and "import site" in pth
    # codice nella stessa disposizione del repository: fonti.radice_fonti() = parents[3]/fonti = app/fonti
    assert (out / "app" / "src" / "successioni" / "telematico" / "fonti.py").exists()
    assert (out / "app" / "fonti" / "Specifiche tecniche" / "SUC13_20250702" / "SUC" / "xsd" /
            "fornituraSUC13_v1.xsd").exists()
    assert not list((out / "app" / "src").rglob("__pycache__"))
    for n in PKG.FILE_RADICE:
        b = (out / n).read_bytes()
        assert b.decode("ascii") and b"\n" not in b.replace(b"\r\n", b""), n
    assert {f["percorso"] for f in man["file"]} >= {"Successioni.cmd", "app/avvia_successioni.py",
                                                    "app/src/successioni/static/app.css"}
    # un file alterato dopo il montaggio viene rilevato
    (out / "app" / "avvia_successioni.py").write_text("# alterato\n", encoding="utf-8")
    assert any("impronta diversa" in p for p in PKG.verifica(out, con_wheel=False))


def test_cmd_e_ps1_solo_ascii_e_riferimenti_esistenti():
    for n in PKG.FILE_RADICE:
        testo = (WIN / n).read_text(encoding="utf-8")
        assert all(ord(c) < 128 for c in testo), n
    import re
    for n in ("Successioni.cmd", "Diagnosi.cmd", "Configura-MCP.cmd", "Verifica-backup.cmd"):
        testo = (WIN / n).read_text(encoding="ascii")
        m = re.search(r'"%BASE%python\\python\.exe" -s "%BASE%app\\([a-z_]+\.py)"', testo)
        assert m, n
        assert (WIN / m.group(1)).exists() and m.group(1) in PKG.SCRIPT_APP, n
    for n in ("installa.ps1", "disinstalla.ps1"):
        t = (WIN / n).read_text(encoding="ascii")
        assert t.count("{") == t.count("}") and t.count("(") == t.count(")"), n
        assert "Invoke-Expression" not in t and "iex " not in t


def test_lock_windows_coerente_con_pyproject():
    from packaging.requirements import Requirement
    lock = {PKG.normalizza(w["nome"]): w for w in PKG.leggi_lock()}
    for dip in PKG.dipendenze_progetto():
        r = Requirement(dip)
        assert PKG.normalizza(r.name) in lock, dip
        assert lock[PKG.normalizza(r.name)]["versione"] in r.specifier, dip
    assert "pywin32" in lock          # dipendenza di mcp solo su Windows: i marcatori sono valutati per win32


@pytest.mark.skipif(not os.environ.get("SUCCESSIONI_PACCHETTO_WIN"),
                    reason="impostare SUCCESSIONI_PACCHETTO_WIN con la cartella del pacchetto costruito")
def test_pacchetto_costruito_integro():
    assert PKG.verifica(Path(os.environ["SUCCESSIONI_PACCHETTO_WIN"])) == []
