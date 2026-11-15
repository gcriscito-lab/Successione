"""Fascicolo unico per il cliente (versione 0.4). Dati SINTETICI.

Raccoglie in un PDF solo i documenti gia' presenti: copertina con indice, modello stampato (se c'e'), allegati del quadro EG
nell'ordine dei righi (TIFF convertiti), ricevute in PDF. Cio' che manca e' elencato in copertina, non blocca.
"""
import io

from PIL import Image
from pypdf import PdfReader
from starlette.testclient import TestClient

from successioni.archivio import Archivio
from successioni.errori import DatiNonValidi
from successioni.fascicolo import fascicolo
from successioni.servizio import Servizio
from successioni.web import crea_app
from test_pdfa import crea_pdf


def _tiff(pagine=2):
    out = io.BytesIO()
    imgs = [Image.new("RGB", (200, 280), (255, 255, 255)) for _ in range(pagine)]
    imgs[0].save(out, format="TIFF", save_all=True, append_images=imgs[1:])
    return out.getvalue()


def _pratica(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    pid = sv.crea_pratica("Eredita' PROVA")["pratica_id"]
    crea_pdf(sv.cartella_ingresso / "testamento.pdf", 3)
    (sv.cartella_ingresso / "visura.tif").write_bytes(_tiff(2))
    a1 = sv.acquisisci_da_ingresso(pid, "testamento.pdf", tipo_eg="Testamento")
    a2 = sv.acquisisci_da_ingresso(pid, "visura.tif", tipo_eg="DichSost")
    rev = sv.leggi(pid)["revisione"]
    sv.aggiorna(pid, rev, [
        {"op": "upsert", "coll": "documenti_ref", "id": "dr_test0001", "campi": {"allegato_id": a1["allegato_id"], "tipo_eg": "Testamento"}},
        {"op": "upsert", "coll": "documenti_ref", "id": "dr_visu0001", "campi": {"allegato_id": a2["allegato_id"], "tipo_eg": "DichSost"}}])
    return sv, pid


def _testo(pdf, pagina=0):
    return PdfReader(io.BytesIO(pdf)).pages[pagina].extract_text()


def test_senza_modello_stampato_lo_segnala_e_include_gli_allegati(tmp_path):
    sv, pid = _pratica(tmp_path)
    pdf, ind = fascicolo(sv, pid)
    r = PdfReader(io.BytesIO(pdf))
    assert len(r.pages) == 2 + 3 + 2          # copertina, indice, documenti
    assert [t for t, _ in ind["documenti"]][0].startswith("EG2 - Testamento")
    assert ind["documenti"][1][0].startswith("EG1") and "TIFF" in ind["documenti"][1][0]
    assert any(x.startswith("Modello ministeriale") for x in ind["non_inclusi"])
    cop, ind_p = _testo(pdf), _testo(pdf, 1)
    assert "Fascicolo per il cliente" in cop and "pag. 1 di 7" in cop
    assert "Contenuto" in ind_p and "Non inclusi" in ind_p and "pag. 3" in ind_p and "pag. 6" in ind_p and "pag. 2 di 7" in ind_p
    assert [o.title for o in r.outline] == ["Copertina e indice", ind["documenti"][0][0], ind["documenti"][1][0]]


def test_modello_stampato_va_subito_dopo_la_copertina(tmp_path, monkeypatch):
    sv, pid = _pratica(tmp_path)
    crea_pdf(tmp_path / "mod.pdf", 4)
    monkeypatch.setattr(sv, "file_stampa_modello", lambda p: ((tmp_path / "mod.pdf").read_bytes(), {"id": "x"}))
    pdf, ind = fascicolo(sv, pid)
    assert ind["documenti"][0] == ("Modello ministeriale (stampa del file telematico)", 4)
    assert len(PdfReader(io.BytesIO(pdf)).pages) == 2 + 4 + 3 + 2
    assert not ind["non_inclusi"]


def test_pdf_danneggiato_non_blocca(tmp_path, monkeypatch):
    sv, pid = _pratica(tmp_path)
    monkeypatch.setattr(sv, "file_stampa_modello", lambda p: (b"%PDF-1.4 rotto", {"id": "x"}))
    pdf, ind = fascicolo(sv, pid)
    assert any("non leggibile" in x for x in ind["non_inclusi"])
    assert len(ind["documenti"]) == 2


def test_pratica_vuota_e_api(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    pid = sv.crea_pratica("Vuota")["pratica_id"]
    pdf, ind = fascicolo(sv, pid)
    assert ind["documenti"] == [] and "Nessun documento" in _testo(pdf, 1)
    cl = TestClient(crea_app(sv, token="tok123", ammetti_host_di_prova=True), base_url="http://testserver")
    cl.get("/", params={"t": "tok123"})
    r = cl.get(f"/api/pratiche/{pid}/fascicolo.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"].startswith("inline") and r.content[:5] == b"%PDF-"
    assert r.headers["x-frame-options"] == "SAMEORIGIN"
    assert cl.get("/api/pratiche/inesistente/fascicolo.pdf").status_code == 404


def test_stampa_superata_dichiarata_in_copertina(tmp_path, monkeypatch):
    sv, pid = _pratica(tmp_path)
    crea_pdf(tmp_path / "mod.pdf", 4)
    monkeypatch.setattr(sv, "file_stampa_modello", lambda p: ((tmp_path / "mod.pdf").read_bytes(), {"id": "x"}))
    originale = sv.stato_elaborati
    monkeypatch.setattr(sv, "stato_elaborati", lambda p: {**originale(p), "stampa_modello": {"stato": "obsoleta"}})
    pdf, ind = fascicolo(sv, pid)
    assert "SUPERATO" in ind["documenti"][0][0]
    assert any(x.startswith("Modello ministeriale aggiornato") for x in ind["non_inclusi"])


def test_copertina_con_defunto_e_registrazione_e_indice_su_piu_pagine():
    from datetime import date
    from successioni.fascicolo import VOCI_PER_PAGINA, _copertina
    dati = {"persone": [{"ruolo": "defunto", "nome": "ANNA", "cognome": "VERDI", "codice_fiscale": "VRDNNA40A41H501X",
                         "data_decesso": "2025-03-10", "sesso": "F"}],
            "note": {"registrazione": {"data_presentazione": "02/07/2025", "volume": "88888", "numero": "1", "anno": "2025",
                                       "ufficio": "UFFICIO DI PROVA"}}}
    docs = [(f"Documento {i}", 2) for i in range(VOCI_PER_PAGINA + 3)]
    pdf = _copertina("Pratica", docs, ["Ricevuta: non disponibile"], ["Studio Prova", "Via Roma 1"], dati=dati,
                     oggi=date(2026, 11, 15))
    r = PdfReader(io.BytesIO(pdf))
    n = len(r.pages)
    assert n == 3                                            # copertina e indice su due pagine
    cop = r.pages[0].extract_text()
    assert "Successione di Anna Verdi" in cop and "deceduta il 10/03/2025" in cop and "volume 88888, numero 1" in cop
    assert "Preparato il 15/11/2026" in cop and f"pag. 1 di {n + 2 * len(docs)}" in cop
    tutto = " ".join(p.extract_text() for p in r.pages[1:])
    assert f"pag. {n + 1}" in tutto and "Contenuto (segue)" in tutto and "Non inclusi" in tutto
