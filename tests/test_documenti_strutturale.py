"""Verificatore strutturale PDF/A-1 (indicativo): una regola per prova, con regressione sul difetto dei booleani."""
import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (ArrayObject, BooleanObject, DecodedStreamObject, DictionaryObject, FloatObject,
                           NameObject, NumberObject)

from successioni import pdfa
from successioni.documenti.corpus_sintetico import pdf_testo
from successioni.documenti.pdfa_strutturale import verifica_strutturale_pdfa as V

gs_ok = pytest.mark.skipif(not pdfa.trova_gs() or not pdfa._icc(), reason="Ghostscript non disponibile")


def codici(p, livello="1b"):
    r = V(p, livello)
    assert r["esito"] in ("indicativo_ok", "indicativo_ko") and "veraPDF" in r["dichiarazione"]
    return {m["codice"] for m in r["motivi"]}


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    d = tmp_path_factory.mktemp("strutt")
    src = pdf_testo(d / "src.pdf", 2)
    if not (pdfa.trova_gs() and pdfa._icc()):
        pytest.skip("Ghostscript non disponibile")
    assert pdfa.converti_in_pdfa(src, d / "pdfa.pdf")["comando_ok"]
    return d / "pdfa.pdf"


def _muta(base, dst, funzione):
    w = PdfWriter(clone_from=str(base))
    funzione(w)
    w._ID = PdfReader(str(base)).trailer["/ID"]
    with open(dst, "wb") as f:
        w.write(f)
    return dst


def test_base_pdfa_pulita_e_clonazione_neutra(base, tmp_path):
    assert codici(base) == set()
    assert codici(_muta(base, tmp_path / "c.pdf", lambda w: None)) == set()


def test_need_appearances_vero_rilevato(base, tmp_path):
    """Regressione: BooleanObject(True) 'is True' e' falso; il controllo deve usare il valore."""
    def f(w):
        w._root_object[NameObject("/AcroForm")] = DictionaryObject(
            {NameObject("/Fields"): ArrayObject(), NameObject("/NeedAppearances"): BooleanObject(True)})
    assert "PDFA_FORM" in codici(_muta(base, tmp_path / "na.pdf", f))


def test_interpolate_e_bpc_immagine(base, tmp_path):
    def f(w):
        img = DecodedStreamObject()
        img.set_data(b"\x00" * 4)
        img.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Image"),
                    NameObject("/Width"): NumberObject(2), NameObject("/Height"): NumberObject(1),
                    NameObject("/ColorSpace"): NameObject("/DeviceGray"), NameObject("/BitsPerComponent"):
                    NumberObject(16), NameObject("/Interpolate"): BooleanObject(True)})
        res = w.pages[0]["/Resources"]
        res[NameObject("/XObject")] = DictionaryObject({NameObject("/ImX"): w._add_object(img)})
    r = V(_muta(base, tmp_path / "im.pdf", f))
    messaggi = " ".join(m["messaggio"] for m in r["motivi"] if m["codice"] == "PDFA_IMMAGINI")
    assert "Interpolate" in messaggi and "BitsPerComponent 16" in messaggi


def test_extgstate_tr_intento_e_trasparenza(base, tmp_path):
    def f(w):
        gs = DictionaryObject({NameObject("/Type"): NameObject("/ExtGState"), NameObject("/TR"): NameObject("/Identity"),
                               NameObject("/RI"): NameObject("/Inventato"), NameObject("/ca"): FloatObject(0.5)})
        w.pages[0]["/Resources"][NameObject("/ExtGState")] = DictionaryObject({NameObject("/GX"): w._add_object(gs)})
    assert {"PDFA_EXTGSTATE", "PDFA_INTENTO", "PDFA_TRASPARENZA"} <= codici(_muta(base, tmp_path / "g.pdf", f))


def test_catalogo_oc_embedded_js_aa(base, tmp_path):
    def f(w):
        w._root_object[NameObject("/OCProperties")] = DictionaryObject()
        w._root_object[NameObject("/AA")] = DictionaryObject()
        w.add_js("app.alert(1)")
    assert {"PDFA_OPTIONAL_CONTENT", "PDFA_AZIONI", "PDFA_JAVASCRIPT"} <= codici(_muta(base, tmp_path / "o.pdf", f))


def test_sintassi_grezza_dopo_eof_e_intestazione(base, tmp_path):
    dati = base.read_bytes()
    (tmp_path / "eof.pdf").write_bytes(dati + b"spazzatura\n")
    assert "PDFA_DOPO_EOF" in codici(tmp_path / "eof.pdf")
    i = dati.index(b"\n") + 1
    assert dati[i:i + 1] == b"%"
    (tmp_path / "bin.pdf").write_bytes(dati[:i + 1] + b"abcd" + dati[i + 5:])
    assert codici(tmp_path / "bin.pdf") == {"PDFA_HEADER_BINARIO"}


def test_livello_1a_richiede_struttura_e_tounicode(base):
    c = codici(base, "1a")
    assert {"PDFA_1A_STRUTTURA", "PDFA_XMP_PDFAID"} <= c
    with pytest.raises(ValueError):
        V(base, "2b")


def test_limiti_implementazione_oggetti(base, tmp_path):
    def f(w):
        w._root_object[NameObject("/Grande")] = ArrayObject([NumberObject(1)] * 8192)
        w._root_object[NameObject("/Reale")] = FloatObject(40000.5)
    c = V(_muta(base, tmp_path / "lim.pdf", f))
    msg = " ".join(m["messaggio"] for m in c["motivi"] if m["codice"] == "PDFA_LIMITI")
    assert "8192" in msg and "6.1.12-2" in msg
