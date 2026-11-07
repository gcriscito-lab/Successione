"""Guida in linea (istruzioni ufficiali per argomento) e finestra Informazioni: src/successioni/guida.py e rotte web."""
import pytest
from pypdf import PdfReader
from io import BytesIO
from starlette.testclient import TestClient

from successioni import __version__, guida
from successioni.archivio import Archivio
from successioni.errori import NonTrovato
from successioni.servizio import Servizio
from successioni.versioni import VERSIONE_REGOLE
from successioni.web import crea_app


def test_documenti_e_argomenti_disponibili():
    g = guida.elenco()
    disp = {d["id"] for d in g["documenti"] if d["disponibile"]}
    assert {"fascicolo1", "fascicolo2", "specifiche"} <= disp
    quadri = {a["quadro"] for a in g["argomenti"]}
    assert {"EA", "EB", "EC", "ED", "EF", "EG", "EH", "EO"} <= quadri


def test_pagine_dentro_i_documenti_e_titoli_coerenti():
    """Ogni argomento punta a una pagina esistente che contiene il titolo del quadro (es. «QUADRO EC»)."""
    pagine = {}
    for a in guida.elenco()["argomenti"]:
        r = pagine.setdefault(a["documento"], PdfReader(BytesIO(guida.file_documento(a["documento"]))))
        assert 1 <= a["pagina"] <= len(r.pages), a
        if a["quadro"] and a["quadro"] not in ("AN", "DV"):
            testo = (r.pages[a["pagina"] - 1].extract_text() or "").replace("\n", " ")
            assert "QUADRO " + a["quadro"] in testo, a


def test_solo_documenti_del_manifest():
    assert guida.file_documento("fascicolo1")[:5] == b"%PDF-"
    for doc in ("../manifest", "fonti/manifest.json", "inesistente"):
        with pytest.raises(NonTrovato):
            guida.file_documento(doc)


def test_informazioni_versioni(tmp_path):
    i = guida.informazioni(Archivio(tmp_path / "d"))
    assert i["versione"] == __version__ and i["versioni"]["regole"] == VERSIONE_REGOLE
    assert i["archivio"] and "Novit" in i["novita"] and i["componenti"]


def test_rotte_web_con_token(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    c = TestClient(crea_app(sv, token="tk", porta=8765), base_url="http://127.0.0.1:8765", follow_redirects=False)
    assert c.get("/api/guida").status_code == 401
    c.get("/", params={"t": "tk"})
    assert c.get("/api/guida").json()["argomenti"]
    r = c.get("/api/guida/fascicolo1.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf" and r.content[:5] == b"%PDF-"
    assert c.get("/api/guida/inesistente.pdf").status_code == 404
    assert c.get("/api/informazioni").json()["versione"] == __version__
