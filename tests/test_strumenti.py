"""Diagnosi, versione del componente di controllo e percorsi di Desktop Telematico / Entratel-Multifile (src/successioni/strumenti.py)."""
import asyncio
import json
import zipfile

import pytest
from starlette.testclient import TestClient

from successioni import impostazioni, strumenti
from successioni.archivio import Archivio
from successioni.errori import DatiNonValidi
from successioni.servizio import Servizio
from successioni.web import crea_app


@pytest.fixture(autouse=True)
def _ambiente(monkeypatch, tmp_path):
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(tmp_path / "cfg" / "configurazione.json"))
    for v in ("SUCCESSIONI_DESKTOP_TELEMATICO", "SUCCESSIONI_ENTRATEL_MULTIFILE", "SystemDrive", "ProgramFiles", "ProgramFiles(x86)",
              "USERPROFILE", "LOCALAPPDATA"):
        monkeypatch.delenv(v, raising=False)


def _jar_finto(cartella, versione=b"2.3.1", data=b"11/03/2026"):
    """JAR con una MSUC13.class sintetica: costanti UTF-8 come nel constant pool (tag 1, lunghezza, testo)."""
    def utf8(t: bytes):
        return b"\x01" + len(t).to_bytes(2, "big") + t
    classe = b"\xca\xfe\xba\xbe" + utf8(b"DATA") + utf8(data) + utf8(b"VERSIONE") + utf8(versione) + utf8(b"schemaComponent")
    cartella.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(cartella / "controlliXMLREG2013.jar", "w") as z:
        z.writestr("it/finanze/entrate/sco/main/MSUC13.class", classe)
    return cartella


def test_versione_letta_dalle_costanti_della_classe(tmp_path):
    assert strumenti.versione_controllo_installata(_jar_finto(tmp_path / "j")) == {"versione": "2.3.1", "data": "11/03/2026"}
    assert strumenti.versione_controllo_installata(tmp_path / "inesistente") is None
    assert strumenti.versione_controllo_installata(None) is None


def test_versione_del_componente_reale_se_configurato():
    import os
    cart = os.environ.get("SUCCESSIONI_CONTROLLI_SUC13")
    if not cart:
        pytest.skip("componente di controllo non configurato")
    assert strumenti.versione_controllo_installata(cart) == {"versione": "2.3.1", "data": "11/03/2026"}


@pytest.mark.parametrize("inst,stato", [
    ({"versione": "2.3.1", "data": "11/03/2026"}, "aggiornata"),
    ({"versione": "2.3.0", "data": "10/01/2026"}, "piu_vecchia"),
    ({"versione": "2.3.1", "data": "01/02/2026"}, "piu_vecchia"),       # stessa versione, data precedente
    ({"versione": "2.4.0", "data": "01/06/2026"}, "piu_recente"),
    ({"versione": "2.10.0", "data": None}, "piu_recente"),              # 2.10 > 2.3: confronto numerico, non testuale
    (None, "sconosciuta"),
])
def test_confronto_con_la_versione_provata(inst, stato):
    r = strumenti.confronta_versione(inst)
    assert r["stato"] == stato and r["messaggio"]
    if stato == "piu_vecchia":
        assert "aggiorna" in r["messaggio"].lower()


def test_desktop_telematico_da_impostazione_e_rilevamento(tmp_path, monkeypatch):
    assert strumenti.desktop_telematico()["cartella"] is None
    dt = tmp_path / "DesktopTelematico"
    dt.mkdir()
    (dt / "DesktopTelematico.exe").write_bytes(b"MZ")
    monkeypatch.setenv("SUCCESSIONI_DESKTOP_TELEMATICO", str(dt))
    r = strumenti.desktop_telematico()
    assert r["origine"] == "impostazione" and r["eseguibile"].endswith("DesktopTelematico.exe")
    monkeypatch.delenv("SUCCESSIONI_DESKTOP_TELEMATICO")
    monkeypatch.setenv("USERPROFILE", str(tmp_path))                    # posizione consueta: <profilo>/DesktopTelematico
    assert strumenti.desktop_telematico()["origine"] == "rilevato"


def test_multifile_richiede_la_cartella_prog(tmp_path, monkeypatch):
    mf = tmp_path / "Entratel-Multifile"
    (mf / "prog").mkdir(parents=True)
    monkeypatch.setenv("SUCCESSIONI_ENTRATEL_MULTIFILE", str(mf))
    assert strumenti.multifile()["origine"] == "impostazione"
    monkeypatch.setenv("SUCCESSIONI_ENTRATEL_MULTIFILE", str(tmp_path))
    assert strumenti.multifile()["cartella"] is None


def test_impostazioni_validano_il_contenuto_delle_cartelle(tmp_path):
    vuota = tmp_path / "vuota"
    vuota.mkdir()
    with pytest.raises(DatiNonValidi, match="DesktopTelematico.exe"):
        impostazioni.salva({"SUCCESSIONI_DESKTOP_TELEMATICO": str(vuota)})
    with pytest.raises(DatiNonValidi, match="prog"):
        impostazioni.salva({"SUCCESSIONI_ENTRATEL_MULTIFILE": str(vuota)})
    dt = tmp_path / "dt"
    dt.mkdir()
    (dt / "DesktopTelematico.exe").write_bytes(b"MZ")
    s = impostazioni.salva({"SUCCESSIONI_DESKTOP_TELEMATICO": str(dt)})
    v = next(x for x in s["voci"] if x["chiave"] == "SUCCESSIONI_DESKTOP_TELEMATICO")
    assert v["valore"] == str(dt) and v["a_posto"]


def test_istruzioni_di_invio_con_i_percorsi(tmp_path, monkeypatch):
    dt = tmp_path / "dt"
    dt.mkdir()
    (dt / "DesktopTelematico.exe").write_bytes(b"MZ")
    mf = tmp_path / "mf"
    (mf / "prog").mkdir(parents=True)
    monkeypatch.setenv("SUCCESSIONI_DESKTOP_TELEMATICO", str(dt))
    monkeypatch.setenv("SUCCESSIONI_ENTRATEL_MULTIFILE", str(mf))
    t = strumenti.istruzioni_invio("successione.xml", "abc123", percorso_dcm=str(tmp_path / "x.dcm"))
    assert str(dt / "DesktopTelematico.exe") in t and str(mf / "file_da_autenticare") in t and "runAutentica.bat" in t
    assert "NON trasmette" in t and "abc123" in t and "x.dcm" in t
    assert "password" not in t.lower().replace("credenziali", "")          # nessun dato di accesso


def test_istruzioni_senza_strumenti_indicano_dove_configurare():
    t = strumenti.istruzioni_invio("f.xml")
    assert "non rilevato" in t and "Impostazioni" in t


def test_diagnosi_struttura_e_esito(tmp_path):
    s = Servizio(Archivio(tmp_path / "dati"))
    d = strumenti.diagnosi(s.arch)
    assert d["esito"] in ("ok", "avvisi", "non_utilizzabile") and d["riepilogo"]
    nomi = {v["nome"] for v in d["voci"]}
    assert {"Sistema", "Cartella dei dati", "Versione del controllo SUC13", "Desktop Telematico", "Entratel-Multifile", "Backup"} <= nomi
    assert all(v["stato"] in ("ok", "avviso", "errore", "info") for v in d["voci"])
    backup = next(v for v in d["voci"] if v["nome"] == "Backup")
    assert backup["stato"] == "avviso" and "nessun backup" in backup["dettaglio"]       # nessun backup ancora
    s.backup_archivio("prova")
    assert next(v for v in strumenti.diagnosi(s.arch)["voci"] if v["nome"] == "Backup")["stato"] == "ok"


def test_diagnosi_segnala_il_controllo_vecchio(tmp_path, monkeypatch):
    monkeypatch.setenv("SUCCESSIONI_CONTROLLI_SUC13", str(_jar_finto(tmp_path / "j", b"2.2.0", b"01/01/2026")))
    voce = next(v for v in strumenti.diagnosi()["voci"] if v["nome"] == "Versione del controllo SUC13")
    assert voce["stato"] == "avviso" and "piu' vecchio" in voce["dettaglio"]


def test_api_diagnosi_e_stato_delle_impostazioni(tmp_path):
    s = Servizio(Archivio(tmp_path / "dati"))
    with TestClient(crea_app(s, token="t", ammetti_host_di_prova=True)) as cl:
        r = cl.post("/api/diagnosi?t=t", json={})
        assert r.status_code == 200 and r.json()["voci"]
        imp = cl.get("/api/impostazioni?t=t").json()
        assert "componente_controllo" in imp and "stato" in imp["componente_controllo"]


def test_mcp_diagnosi_disponibile_anche_in_sola_lettura(tmp_path):
    from mcp.client import Client
    from successioni.mcp_server import STRUMENTI_LETTURA, costruisci
    assert "diagnosi" in STRUMENTI_LETTURA
    impostazioni.salva({}, preferenze_nuove={"mcp_sola_lettura": True})
    s = Servizio(Archivio(tmp_path / "dati"))

    async def scenario():
        async with Client(costruisci(s)) as c:
            return await c.call_tool("successioni_diagnosi", {})
    res = asyncio.run(scenario())
    sc = res.structured_content
    dati = sc.get("result", sc) if isinstance(sc, dict) else json.loads(res.content[0].text)
    assert dati["voci"] and dati["esito"] in ("ok", "avvisi", "non_utilizzabile")
