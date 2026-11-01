"""TIFF: requisiti di Specifiche p.7 (<=300 DPI, B/N, CCITT Group IV). Esito indicativo; CIVIS da collaudare."""
import pytest
from PIL import Image

from successioni import pdfa
from successioni.documenti import tiff as T
from successioni.documenti.corpus_sintetico import pdf_testo

gs_ok = pytest.mark.skipif(not pdfa.trova_gs(), reason="Ghostscript non disponibile")


def _bn(p, dpi, compressione="group4"):
    Image.new("1", (200, 100), 1).save(p, compression=compressione, dpi=dpi)
    return p


@pytest.mark.parametrize("dpi,esito", [((300, 300), "indicativo_ok"), ((200, 200), "indicativo_ok"),
                                       ((301, 300), "indicativo_ko"), ((300, 600), "indicativo_ko")])
def test_soglia_300_dpi(tmp_path, dpi, esito):
    v = T.verifica_tiff(_bn(tmp_path / "a.tif", dpi))
    assert v["esito"] == esito and v["pagine"] == 1
    assert v["esito"] != "conforme" and "CIVIS" in v["dichiarazione"]


def test_compressione_e_colore(tmp_path):
    v = T.verifica_tiff(_bn(tmp_path / "lzw.tif", (200, 200), "tiff_lzw"))
    assert [m["codice"] for m in v["motivi"]] == ["TIFF_COMPRESSIONE"]
    Image.new("L", (50, 50), 128).save(tmp_path / "grigi.tif", compression="tiff_lzw", dpi=(200, 200))
    codici = {m["codice"] for m in T.verifica_tiff(tmp_path / "grigi.tif")["motivi"]}
    assert codici == {"TIFF_COMPRESSIONE", "TIFF_NON_BN"}
    Image.new("1", (50, 50), 1).save(tmp_path / "senza_dpi.tif", compression="group4")
    assert {m["codice"] for m in T.verifica_tiff(tmp_path / "senza_dpi.tif")["motivi"]} == {"TIFF_RISOLUZIONE"}


def test_troncato_e_non_tiff(tmp_path):
    p = _bn(tmp_path / "a.tif", (200, 200))
    dati = p.read_bytes()
    (tmp_path / "t.tif").write_bytes(dati[:40])
    assert T.verifica_tiff(tmp_path / "t.tif")["motivi"][0]["codice"] == "TIFF_ILLEGGIBILE"
    (tmp_path / "x.tif").write_bytes(b"%PDF-1.4")
    assert T.verifica_tiff(tmp_path / "x.tif")["esito"] == "indicativo_ko"


@gs_ok
def test_conversione_pdf_tiff_g4_multipagina(tmp_path):
    src = pdf_testo(tmp_path / "doc.pdf", 3)
    r = T.converti_in_tiff_g4(src, tmp_path / "doc.tif", dpi=200)
    assert r["comando_ok"] and r["verifica"]["esito"] == "indicativo_ok" and r["verifica"]["pagine"] == 3
    assert all(p["dpi"] == [200.0, 200.0] and p["compressione"] == 4 for p in r["verifica"]["dettaglio_pagine"])
    a = pdfa.analizza_pdf(tmp_path / "doc.tif")
    assert a["formato"] == "tiff" and a["pagine"] == 3 and a["verifica_tiff"]["esito"] == "indicativo_ok"
    with pytest.raises(ValueError):
        T.converti_in_tiff_g4(src, tmp_path / "x.tif", dpi=400)
