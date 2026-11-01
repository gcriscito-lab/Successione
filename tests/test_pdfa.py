import shutil
import subprocess
import pytest
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter
from successioni import pdfa

gs_ok = pytest.mark.skipif(not pdfa.trova_gs() or not pdfa._icc(), reason="Ghostscript non disponibile")


def crea_pdf(p, pagine=3):
    c = canvas.Canvas(str(p))
    for i in range(pagine):
        c.setFont("Helvetica", 14)       # carattere NON incorporato: caso tipico non conforme
        c.drawString(72, 750, f"Certificato di prova pagina {i+1} - è così àèìòù")
        c.showPage()
    c.save()


def estrai_testo(p):
    return subprocess.run(["pdftotext", str(p), "-"], capture_output=True, text=True).stdout


def test_non_pdf_e_danneggiato_e_protetto(tmp_path):
    f = tmp_path / "x.pdf"; f.write_bytes(b"MZ not a pdf")
    assert pdfa.analizza_pdf(f)["esito"] == "non_pdf"
    g = tmp_path / "ok.pdf"; crea_pdf(g)
    h = tmp_path / "rotto.pdf"; h.write_bytes(g.read_bytes()[:400])
    assert pdfa.analizza_pdf(h)["esito"] == "danneggiato"
    w = PdfWriter(clone_from=str(g)); w.encrypt("segreto")
    e = tmp_path / "enc.pdf"; w.write(str(e))
    assert pdfa.analizza_pdf(e)["esito"] == "protetto"


def test_analisi_pdf_ordinario(tmp_path):
    g = tmp_path / "ok.pdf"; crea_pdf(g, 3)
    a = pdfa.analizza_pdf(g)
    assert a["esito"] == "leggibile" and a["pagine"] == 3 and a["dichiara_pdfa"] is None


@gs_ok
def test_a11_conversione_conserva_pagine_e_testo_e_non_dichiara_conformita(tmp_path):
    src, dst = tmp_path / "in.pdf", tmp_path / "out.pdf"
    crea_pdf(src, 3)
    r = pdfa.converti_in_pdfa(src, dst)
    assert r["comando_ok"], r["stderr"]
    a = pdfa.analizza_pdf(dst)
    assert a["pagine"] == 3                                    # nessuna pagina persa
    assert a["dichiara_pdfa"] == "1b"                          # metadati presenti ...
    assert "pagina 2" in estrai_testo(dst) and "è così" in estrai_testo(dst)  # ... testo leggibile
    # ... ma senza validatore indipendente la conformita' NON e' dimostrata
    if not pdfa.trova_verapdf():
        v = pdfa.valida_pdfa(dst)
        assert v["esito"] == "non_verificato" and "non dimostrata" in v["motivo"]


@gs_ok
def test_font_incorporati_dopo_conversione(tmp_path):
    src, dst = tmp_path / "in.pdf", tmp_path / "out.pdf"
    crea_pdf(src, 1)
    pdfa.converti_in_pdfa(src, dst)
    r = PdfReader(str(dst))
    fonts = r.pages[0]["/Resources"]["/Font"]
    for _, f in fonts.items():
        d = f.get_object()
        desc = d.get("/DescendantFonts")
        fd = (desc[0].get_object() if desc else d)["/FontDescriptor"].get_object()
        assert any(k in fd for k in ("/FontFile", "/FontFile2", "/FontFile3"))


def test_pdfa_1a_non_prodotto():
    with pytest.raises(NotImplementedError):
        pdfa.converti_in_pdfa("a", "b", "1a")


def test_servizio_allegati_originale_derivato_collegati(tmp_path):
    from successioni.archivio import Archivio
    from successioni.servizio import Servizio, DatiNonValidi
    sv = Servizio(Archivio(tmp_path / "dati"))
    pid = sv.crea_pratica("X")["pratica_id"]
    f = sv.cartella_ingresso / "cert.pdf"; crea_pdf(f, 2)
    a = sv.acquisisci_da_ingresso(pid, "cert.pdf", tipo_eg="certificato", finalita="prova")
    assert a["ruolo"] == "originale" and a["analisi"]["pagine"] == 2
    with pytest.raises(DatiNonValidi):                      # nessuna lettura fuori dalla cartella d'ingresso
        sv.acquisisci_da_ingresso(pid, "../archivio.sqlite3")
    if pdfa.trova_gs():
        r = sv.prepara_pdfa(a["allegato_id"])
        assert r["derivato"]["ruolo"] == "derivato"
        assert r["esito"] in ("conforme", "non_verificato")   # mai "conforme" senza validatore
        if not pdfa.trova_verapdf():
            assert r["esito"] == "non_verificato"
        lista = sv.elenca_allegati(pid)
        assert [x["ruolo"] for x in lista] == ["originale", "derivato"]
        assert lista[1]["origine_id"] == a["allegato_id"]
        assert (sv.arch.base / lista[0]["percorso"]).read_bytes() == f.read_bytes()  # originale intatto
