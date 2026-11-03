"""Impostazioni: percorsi degli strumenti esterni, stato di rilevamento, salvataggio tutto-o-niente e compatibilita' con l'avviatore."""
import importlib
import json
import os
import sys
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from successioni import impostazioni as IM
from successioni.archivio import Archivio
from successioni.errori import DatiNonValidi
from successioni.servizio import Servizio
from successioni.web import crea_app

RADICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RADICE / "scripts" / "windows"))
A = importlib.import_module("avvia_successioni")

CHIAVI_MODIFICABILI = [v[0] for v in IM.VOCI if v[2] != "sola_lettura"]


@pytest.fixture
def conf(tmp_path, monkeypatch):
    f = tmp_path / "configurazione.json"
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(f))
    monkeypatch.setenv("SUCCESSIONI_DATA", str(tmp_path / "dati"))
    # `salva` scrive in os.environ: si salvano e ripristinano le variabili a mano (monkeypatch.delenv, chiamato dopo il
    # salvataggio, ripristinerebbe a fine test il valore appena impostato e lo farebbe trapelare nei test successivi)
    prima = {k: os.environ.pop(k, None) for k in CHIAVI_MODIFICABILI}
    yield f
    for k, v in prima.items():
        os.environ.pop(k, None)
        if v is not None:
            os.environ[k] = v


def _file(tmp_path, nome="strumento.exe"):
    p = tmp_path / nome
    p.write_bytes(b"")
    return str(p)


def _voce(s, chiave):
    return next(v for v in s["voci"] if v["chiave"] == chiave)


def test_stato_elenca_tutte_le_voci_e_la_cartella_dati_e_solo_lettura(conf, tmp_path):
    s = IM.stato()
    assert [v["chiave"] for v in s["voci"]] == [v[0] for v in IM.VOCI] and s["file"] == str(conf)
    dati = _voce(s, "SUCCESSIONI_DATA")
    assert dati["modificabile"] is False and dati["valore"] == str(tmp_path / "dati")
    assert all(v["modificabile"] for v in s["voci"] if v["chiave"] != "SUCCESSIONI_DATA")


def test_voce_non_impostata(conf):
    v = _voce(IM.stato(), "SUCCESSIONI_QPDF")
    assert v["valore"] is None and v["origine"] == "non impostato" and v["salvato"] is None


def test_salva_file_e_cartella_aggiorna_file_e_ambiente(conf, tmp_path, monkeypatch):
    exe = _file(tmp_path, "gswin64c.exe")
    cart = tmp_path / "jar"
    cart.mkdir()
    s = IM.salva({"SUCCESSIONI_GS": exe, "SUCCESSIONI_CONTROLLI_SUC13": str(cart)})
    assert json.loads(conf.read_text(encoding="utf-8")) == {"SUCCESSIONI_GS": exe, "SUCCESSIONI_CONTROLLI_SUC13": str(cart)}
    assert os.environ["SUCCESSIONI_GS"] == exe and os.environ["SUCCESSIONI_CONTROLLI_SUC13"] == str(cart)
    v = _voce(s, "SUCCESSIONI_GS")
    assert v["valore"] == exe and v["origine"] == "file di configurazione" and v["salvato"] == exe and v["a_posto"] is True
    assert s["avvisi"] == []


def test_chiavi_estranee_nel_file_si_conservano(conf, tmp_path, monkeypatch):
    conf.write_text(json.dumps({"ALTRO": "valore", "SUCCESSIONI_GS": "vecchio"}), encoding="utf-8")
    exe = _file(tmp_path, "qpdf.exe")
    IM.salva({"SUCCESSIONI_QPDF": exe})
    assert json.loads(conf.read_text(encoding="utf-8")) == {"ALTRO": "valore", "SUCCESSIONI_GS": "vecchio", "SUCCESSIONI_QPDF": exe}


def test_il_file_scritto_e_letto_dall_avviatore(conf, tmp_path, monkeypatch):
    exe = _file(tmp_path, "verapdf.bat")
    IM.salva({"SUCCESSIONI_VERAPDF": exe, "SUCCESSIONI_CONTROLLI_TIMEOUT": "900"})
    assert A.leggi_configurazione() == {"SUCCESSIONI_VERAPDF": exe, "SUCCESSIONI_CONTROLLI_TIMEOUT": "900"}


def test_valore_vuoto_rimuove_dal_file_e_dall_ambiente(conf, tmp_path, monkeypatch):
    exe = _file(tmp_path, "java.exe")
    IM.salva({"SUCCESSIONI_JAVA": exe})
    s = IM.salva({"SUCCESSIONI_JAVA": "  "})
    assert "SUCCESSIONI_JAVA" not in os.environ and json.loads(conf.read_text(encoding="utf-8")) == {}
    assert any("rimossa" in a for a in s["avvisi"])


def test_rimozione_di_una_voce_non_impostata_non_da_avviso(conf):
    assert IM.salva({"SUCCESSIONI_ICC": ""})["avvisi"] == []


@pytest.mark.parametrize("chiave", ["SUCCESSIONI_PASSWORD", "PATH", "password", "SUCCESSIONI_CONFIG", "SUCCESSIONI_TOKEN"])
def test_chiavi_non_elencate_rifiutate(conf, chiave):
    with pytest.raises(DatiNonValidi, match="sconosciuta"):
        IM.salva({chiave: "x"})
    assert not conf.exists()


def test_cartella_dati_non_modificabile(conf):
    with pytest.raises(DatiNonValidi, match="non modificabile"):
        IM.salva({"SUCCESSIONI_DATA": "C:/altro"})


@pytest.mark.parametrize("chiave,valore,frammento", [
    ("SUCCESSIONI_GS", "C:/non/esiste/gs.exe", "non trovato"),
    ("SUCCESSIONI_CONTROLLI_SUC13", "C:/non/esiste/cartella", "non trovato"),
    ("SUCCESSIONI_CONTROLLI_TIMEOUT", "abc", "numero intero"),
    ("SUCCESSIONI_CONTROLLI_TIMEOUT", "9", "da 10 a 7200"),
    ("SUCCESSIONI_CONTROLLI_TIMEOUT", "7201", "da 10 a 7200"),
    ("SUCCESSIONI_GS", 5, "atteso un testo"),
    ("SUCCESSIONI_GS", "a\nb", "caratteri non ammessi"),
])
def test_valori_non_validi(conf, chiave, valore, frammento):
    with pytest.raises(DatiNonValidi, match=frammento):
        IM.salva({chiave: valore})
    assert not conf.exists()


@pytest.mark.parametrize("valore", ["10", "7200", "600"])
def test_timeout_ai_limiti(conf, valore, monkeypatch):
    IM.salva({"SUCCESSIONI_CONTROLLI_TIMEOUT": valore})
    assert json.loads(conf.read_text(encoding="utf-8"))["SUCCESSIONI_CONTROLLI_TIMEOUT"] == valore


def test_tutto_o_niente(conf, tmp_path):
    exe = _file(tmp_path, "gswin64c.exe")
    with pytest.raises(DatiNonValidi):
        IM.salva({"SUCCESSIONI_GS": exe, "SUCCESSIONI_QPDF": "C:/non/esiste.exe"})
    assert not conf.exists() and "SUCCESSIONI_GS" not in os.environ


def test_nessuna_modifica_e_tipo_errato(conf):
    for m in ({}, None, [("SUCCESSIONI_GS", "x")]):
        with pytest.raises(DatiNonValidi, match="nessuna modifica"):
            IM.salva(m)


def test_virgolette_attorno_al_percorso_tolte(conf, tmp_path, monkeypatch):
    exe = _file(tmp_path, "qpdf.exe")
    IM.salva({"SUCCESSIONI_QPDF": f'"{exe}"'})
    assert json.loads(conf.read_text(encoding="utf-8"))["SUCCESSIONI_QPDF"] == exe


def test_scrittura_impossibile_e_segnalata_senza_cambiare_l_ambiente(tmp_path, monkeypatch, conf):
    un_file = tmp_path / "e_un_file"
    un_file.write_bytes(b"")
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(un_file / "configurazione.json"))     # la cartella madre e' un file: non si puo' creare
    with pytest.raises(DatiNonValidi, match="impossibile scrivere"):
        IM.salva({"SUCCESSIONI_QPDF": _file(tmp_path, "qpdf.exe")})
    assert "SUCCESSIONI_QPDF" not in os.environ


def test_il_file_di_configurazione_e_una_cartella(tmp_path, monkeypatch, conf):
    cartella = tmp_path / "e_una_cartella"
    cartella.mkdir()
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(cartella))
    with pytest.raises(DatiNonValidi, match="non e' leggibile"):
        IM.salva({"SUCCESSIONI_QPDF": _file(tmp_path, "qpdf.exe")})
    assert "SUCCESSIONI_QPDF" not in os.environ


def test_senza_variabile_il_file_e_nella_cartella_dei_dati(tmp_path, monkeypatch):
    monkeypatch.delenv("SUCCESSIONI_CONFIG", raising=False)
    monkeypatch.setenv("SUCCESSIONI_DATA", str(tmp_path / "d"))
    assert IM.file_configurazione() == tmp_path / "d" / "configurazione.json"


def test_file_illeggibile_in_lettura_si_mostra_come_vuoto(conf):
    conf.write_text("{ non json", encoding="utf-8")
    assert _voce(IM.stato(), "SUCCESSIONI_GS")["salvato"] is None


def test_origine_ambiente_diversa_dal_file(conf, tmp_path, monkeypatch):
    exe, altro = _file(tmp_path, "gswin64c.exe"), _file(tmp_path, "gs.exe")
    conf.write_text(json.dumps({"SUCCESSIONI_GS": exe}), encoding="utf-8")
    monkeypatch.setenv("SUCCESSIONI_GS", altro)
    v = _voce(IM.stato(), "SUCCESSIONI_GS")
    assert v["origine"] == "ambiente o rilevamento automatico" and v["salvato"] == exe


def test_controllo_suc13_segnala_i_jar_mancanti(conf, tmp_path, monkeypatch):
    from successioni.collegamenti import controllo
    monkeypatch.setattr(controllo, "jar_richiesti", lambda *a, **k: ["a.jar", "b.jar", "c.jar", "d.jar", "e.jar", "f.jar"])
    cart = tmp_path / "jar"
    cart.mkdir()
    (cart / "a.jar").write_bytes(b"")
    s = IM.salva({"SUCCESSIONI_CONTROLLI_SUC13": str(cart)})
    v = _voce(s, "SUCCESSIONI_CONTROLLI_SUC13")
    assert v["a_posto"] is False and "mancano 5 di 6 JAR" in v["dettaglio"] and v["dettaglio"].endswith("...")
    (cart / "b.jar").write_bytes(b"")
    for n in "cdef":
        (cart / f"{n}.jar").write_bytes(b"")
    v = _voce(IM.stato(), "SUCCESSIONI_CONTROLLI_SUC13")
    assert v["a_posto"] is True and "presenti" in v["dettaglio"]


def test_controllo_senza_cartella_non_e_a_posto(conf):
    v = _voce(IM.stato(), "SUCCESSIONI_CONTROLLI_SUC13")
    assert v["a_posto"] is False and "non impostata" in v["dettaglio"]


# ------------------------------------------------------------------------------------------------------------ API
def _client(tmp_path):
    return TestClient(crea_app(Servizio(Archivio(tmp_path / "web")), token="sintetico", ammetti_host_di_prova=True))


def test_api_legge_e_salva(conf, tmp_path, monkeypatch):
    exe = _file(tmp_path, "qpdf.exe")
    with _client(tmp_path) as cl:
        r = cl.get("/api/impostazioni?t=sintetico")
        assert r.status_code == 200 and len(r.json()["voci"]) == len(IM.VOCI)
        r = cl.post("/api/impostazioni?t=sintetico", json={"modifiche": {"SUCCESSIONI_QPDF": exe}})
        assert r.status_code == 200 and _voce(r.json(), "SUCCESSIONI_QPDF")["valore"] == exe
        assert cl.get("/api/info?t=sintetico").status_code == 200


def test_api_errori_e_token(conf, tmp_path):
    with _client(tmp_path) as cl:
        assert cl.get("/api/impostazioni").status_code == 401
        assert cl.post("/api/impostazioni", json={"modifiche": {"SUCCESSIONI_QPDF": "x"}}).status_code == 401
        r = cl.post("/api/impostazioni?t=sintetico", json={"modifiche": {"SUCCESSIONI_PASSWORD": "x"}})
        assert r.status_code == 422 and r.json()["codice"] == "DATI_NON_VALIDI"
        assert cl.post("/api/impostazioni?t=sintetico", json={}).status_code == 422
    assert not conf.exists()


@pytest.mark.parametrize("contenuto", ["[1, 2]", '"testo"', "123", "null", '{"SUCCESSIONI_GS": "x",}', "{ non json"])
def test_file_illeggibile_o_non_oggetto_non_si_sovrascrive(conf, tmp_path, contenuto):
    conf.write_text(contenuto, encoding="utf-8")
    assert IM.stato()["voci"][1]["salvato"] is None
    with pytest.raises(DatiNonValidi, match="non e' leggibile|non contiene un oggetto"):
        IM.salva({"SUCCESSIONI_QPDF": _file(tmp_path, "qpdf.exe")})
    assert conf.read_text(encoding="utf-8") == contenuto and "SUCCESSIONI_QPDF" not in os.environ


@pytest.mark.parametrize("chiave,nome", [("SUCCESSIONI_JAVA", "cmd.exe"), ("SUCCESSIONI_JAVA", "calc.exe"),
                                         ("SUCCESSIONI_GS", "powershell.exe"), ("SUCCESSIONI_VERAPDF", "verapdf.exe.txt"),
                                         ("SUCCESSIONI_QPDF", "qpdf2.exe"), ("SUCCESSIONI_ICC", "profilo.exe")])
def test_il_nome_del_file_deve_essere_quello_dello_strumento(conf, tmp_path, chiave, nome):
    with pytest.raises(DatiNonValidi, match="nome dello strumento"):
        IM.salva({chiave: _file(tmp_path, nome)})
    assert not conf.exists()


@pytest.mark.parametrize("chiave,nome", [("SUCCESSIONI_JAVA", "java.exe"), ("SUCCESSIONI_JAVA", "javaw.exe"), ("SUCCESSIONI_JAVA", "JAVA.EXE"),
                                         ("SUCCESSIONI_GS", "gswin64c.exe"), ("SUCCESSIONI_GS", "gs"), ("SUCCESSIONI_GS", "gswin32c.exe"),
                                         ("SUCCESSIONI_VERAPDF", "verapdf.bat"), ("SUCCESSIONI_VERAPDF", "verapdf"),
                                         ("SUCCESSIONI_QPDF", "qpdf.exe"), ("SUCCESSIONI_ICC", "srgb.icc"), ("SUCCESSIONI_ICC", "x.ICM")])
def test_nomi_ammessi_per_ogni_strumento(conf, tmp_path, chiave, nome):
    IM.salva({chiave: _file(tmp_path, nome)})
    assert chiave in json.loads(conf.read_text(encoding="utf-8"))


def test_nome_di_comando_nel_path_e_accettato_per_gli_strumenti(conf, monkeypatch):
    monkeypatch.setattr(IM.shutil, "which", lambda n: "C:/bin/gs.exe" if n == "gs" else None)
    IM.salva({"SUCCESSIONI_GS": "gs"})
    with pytest.raises(DatiNonValidi, match="non trovato"):
        IM.salva({"SUCCESSIONI_QPDF": "qpdf-inesistente"})
    with pytest.raises(DatiNonValidi, match="non trovato"):
        IM.salva({"SUCCESSIONI_CONTROLLI_SUC13": "gs"})        # una cartella deve esistere davvero: il PATH non conta


@pytest.mark.parametrize("carattere", ["\n", "\r", "\x00"])
def test_caratteri_di_controllo_rifiutati_anche_se_il_percorso_esiste(conf, tmp_path, carattere, monkeypatch):
    monkeypatch.setattr(IM.shutil, "which", lambda n: "C:/bin/x.exe")
    with pytest.raises(DatiNonValidi, match="caratteri non ammessi"):
        IM.salva({"SUCCESSIONI_GS": "gs" + carattere + "x"})
