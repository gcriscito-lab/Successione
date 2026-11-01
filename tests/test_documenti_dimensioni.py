"""Riduzione/suddivisione (A12) e verifica dimensionale della fornitura, con soglie e unita' esplicite."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from successioni import pdfa
from successioni.documenti import dimensioni as D
from successioni.documenti import limiti as L
from successioni.documenti.corpus_sintetico import pdf_cifrato, pdf_immagini_grandi, pdf_testo
from successioni.errori import DatiNonValidi

gs_ok = pytest.mark.skipif(not pdfa.trova_gs() or not pdfa._icc(), reason="Ghostscript non disponibile")
SPEC = Path(__file__).resolve().parents[1] / "fonti" / "Specifiche tecniche" / "Specifiche_SUC13_20250702.pdf"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def multipagina(tmp_path_factory):
    return pdf_testo(tmp_path_factory.mktemp("mp") / "multipagina.pdf", 40, righe=55, seme=3)


def _verifica_senza_perdita(src: Path, parti, limite: int):
    rap = parti.rapporto
    assert all(Path(p).stat().st_size <= limite for p in parti)
    assert sum(len(D.PdfReader(str(p)).pages) for p in parti) == len(D.PdfReader(str(src)).pages)
    intervalli = [v["pagine_sorgente"] for v in rap["parti"]]
    assert intervalli[0][0] == 1 and intervalli[-1][1] == rap["sorgente"]["pagine"]
    assert all(b[0] == a[1] + 1 for a, b in zip(intervalli, intervalli[1:]))          # contigui, in ordine
    for v, p in zip(rap["parti"], parti):
        assert v["sha256"] == sha(p) and v["bytes"] == Path(p).stat().st_size
    assert rap["verifica_pagine"]["esito"] == "passato" and rap["originale_invariato"] is True
    assert json.loads(Path(rap["file_rapporto"]).read_text(encoding="utf-8"))["azione"] == rap["azione"]


def test_fonti_dei_limiti_citate_correttamente():
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext non disponibile")
    p3 = subprocess.run(["pdftotext", "-f", "3", "-l", "3", str(SPEC), "-"], capture_output=True, text=True).stdout
    p7 = subprocess.run(["pdftotext", "-f", "7", "-l", "7", str(SPEC), "-"], capture_output=True, text=True).stdout
    assert "40 MB compressi" in " ".join(p3.split()) and "una sola dichiarazione" in " ".join(p3.split())
    t7 = " ".join(p7.split())
    assert "dimensione massima di 5 MB" in t7 and "suddividerlo in più file" in t7
    assert "PDF/A-1a o PDF/A-1b" in t7 and "non superiore a 300 DPI" in t7 and "CCITT Group IV" in t7
    assert (L.LIMITE_ALLEGATO_MB, L.LIMITE_FORNITURA_MB) == (5, 40)
    assert L.limite_byte(5) == 5_000_000 and L.limite_byte(5, "binaria") == 5_242_880
    assert pdfa.LIMITE_ALLEGATO_BYTE == 5_000_000                # predefinito: unita' decimale, piu' severa


def test_suddivisione_senza_perdita_qpdf(multipagina, tmp_path):
    h0 = sha(multipagina)
    parti = D.riduci_o_suddividi(multipagina, 60_000, cartella_uscita=tmp_path, tentativi=(), forza_pdfa=False,
                                 valida=False)
    assert parti.rapporto["azione"] == "suddivisione" and len(parti) >= 3
    assert parti.rapporto["strumento_suddivisione"] == ("qpdf" if D.trova_qpdf() else "pypdf")
    _verifica_senza_perdita(multipagina, parti, 60_000)
    # testo identico pagina per pagina (pdftotext): nessuna pagina persa ne' scambiata
    testo = [t for p in parti for t in D.testo_pagine(p)]
    assert [D._norm(t) for t in testo] == [D._norm(t) for t in D.testo_pagine(multipagina)]
    assert all(f"Pagina {i} di 40" in t for i, t in enumerate(testo, 1))
    assert sha(multipagina) == h0


def test_suddivisione_fallback_pypdf(multipagina, tmp_path, monkeypatch):
    monkeypatch.setattr(D, "trova_qpdf", lambda: None)
    parti = D.riduci_o_suddividi(multipagina, 60_000, cartella_uscita=tmp_path, tentativi=(), forza_pdfa=False,
                                 valida=False)
    assert parti.rapporto["strumento_suddivisione"] == "pypdf"
    _verifica_senza_perdita(multipagina, parti, 60_000)
    assert parti.rapporto["verifica_testo"]["differenze"] == []


def test_soglia_esatta_in_byte(multipagina, tmp_path):
    n = multipagina.stat().st_size
    uguale = D.riduci_o_suddividi(multipagina, n, cartella_uscita=tmp_path / "a", forza_pdfa=False, valida=False)
    assert uguale.rapporto["azione"] == "nessuna" and list(uguale) == [multipagina]
    sopra = D.riduci_o_suddividi(multipagina, n - 1, cartella_uscita=tmp_path / "b", tentativi=(), forza_pdfa=False,
                                 valida=False)
    assert sopra.rapporto["azione"] == "suddivisione" and len(sopra) == 2
    _verifica_senza_perdita(multipagina, sopra, n - 1)


def test_pagina_singola_oltre_limite_respinta(multipagina, tmp_path):
    with pytest.raises(D.LimiteNonRaggiungibile) as e:
        D.riduci_o_suddividi(multipagina, 3_000, cartella_uscita=tmp_path, tentativi=(), forza_pdfa=False)
    assert e.value.codice == "LIMITE_NON_RAGGIUNGIBILE" and e.value.dettagli["pagina"] == 1


def test_input_non_elaborabili_respinti(multipagina, tmp_path):
    cif = pdf_cifrato(multipagina, tmp_path / "c.pdf")
    tr = tmp_path / "t.pdf"
    tr.write_bytes(multipagina.read_bytes()[:5000])
    np_ = tmp_path / "n.pdf"
    np_.write_bytes(b"PK\x03\x04 non e' un pdf")
    for f, esito in ((cif, "protetto"), (tr, "danneggiato"), (np_, "non_pdf")):
        with pytest.raises(DatiNonValidi) as e:
            D.riduci_o_suddividi(f, 1_000_000, cartella_uscita=tmp_path)
        assert e.value.dettagli["esito"] == esito


@gs_ok
def test_riduzione_immagini_grandi_limite_reale_5mb(tmp_path, monkeypatch):
    monkeypatch.setattr(pdfa, "trova_verapdf", lambda: None)
    src = pdf_immagini_grandi(tmp_path / "scansione.pdf")
    assert src.stat().st_size > L.LIMITE_ALLEGATO_BINARIO
    h0 = sha(src)
    parti = D.riduci_o_suddividi(src, cartella_uscita=tmp_path / "out")          # limite predefinito: 5 000 000
    rap = parti.rapporto
    assert rap["limite_byte"] == 5_000_000 and rap["azione"] == "riduzione" and len(parti) == 1
    assert parti[0].stat().st_size <= 5_000_000
    assert rap["tentativi"][0]["dpi"] == 200
    _verifica_senza_perdita(src, parti, 5_000_000)
    v = rap["parti"][0]["validazione"]
    assert v["esito"] == "non_verificato" and v["indicativo"] == "indicativo_ok"      # mai "conforme" senza veraPDF
    assert "Pagina 1 di 1" in D.testo_pagine(parti[0])[0] and sha(src) == h0


@gs_ok
def test_riduzione_insufficiente_poi_suddivisione_parti_rivalidate(multipagina, tmp_path, monkeypatch):
    monkeypatch.setattr(pdfa, "trova_verapdf", lambda: None)
    parti = D.riduci_o_suddividi(multipagina, 60_000, cartella_uscita=tmp_path)
    rap = parti.rapporto
    assert rap["azione"] == "riduzione+suddivisione" and len(rap["tentativi"]) == 2
    _verifica_senza_perdita(multipagina, parti, 60_000)
    for v in rap["parti"]:
        assert v["validazione"]["esito"] == "non_verificato"
        assert v["validazione"]["indicativo"] == "indicativo_ok", v["validazione"]["motivi_indicativi"]
        assert pdfa.analizza_pdf(v["percorso"])["dichiara_pdfa"] == "1b"
    assert rap["verifica_testo"]["divergenti"] == []


# ------------------------------------------------------------------------------------------- fornitura

def _pdf_finto(p: Path, n: int) -> Path:
    p.write_bytes(b"%PDF-1.4\n" + b"0" * (n - 9))
    return p


def test_fornitura_limite_allegato_soglie_e_unita(tmp_path):
    esatto = _pdf_finto(tmp_path / "a.pdf", 5_000_000)
    oltre = _pdf_finto(tmp_path / "b.pdf", 5_000_001)
    medio = _pdf_finto(tmp_path / "c.pdf", 5_100_000)          # oltre 5 MB decimali, sotto 5 MiB
    m = {"allegati": [{"percorso": str(esatto), "id": "a"}]}
    assert D.verifica_fornitura(m) == []
    e = D.verifica_fornitura({"allegati": [{"percorso": str(oltre), "id": "b"}]})
    assert [x.codice for x in e] == ["ALLEGATO_OLTRE_LIMITE"]
    assert "5000001 byte" in e[0].messaggio and "prima della codifica Base64" in e[0].messaggio
    assert "p.7" in e[0].fonte
    m = {"allegati": [{"percorso": str(medio), "id": "c"}]}
    assert [x.codice for x in D.verifica_fornitura(m)] == ["ALLEGATO_OLTRE_LIMITE"]
    assert D.verifica_fornitura(m, limite_allegato=L.limite_byte(5, "binaria")) == []


def test_fornitura_punto_di_misura_e_limite_compresso(tmp_path):
    a = _pdf_finto(tmp_path / "a.pdf", 300_000)
    xml = b"<Fornitura>" + b"<ImageData>" + b"QUJD" * 200_000 + b"</ImageData></Fornitura>"
    man = {"xml": xml, "allegati": [{"percorso": str(a)}]}
    compresso = D.misura_fornitura(man)
    grezzo = D.misura_fornitura(man, "xml_non_compresso")
    assert compresso["completa"] and compresso["punto_misura"] == "xml_deflate"
    assert grezzo["bytes"] == len(xml) > compresso["bytes"]
    assert D.verifica_fornitura(man, limite_compresso=compresso["bytes"]) == []
    e = D.verifica_fornitura(man, limite_compresso=compresso["bytes"] - 1)
    assert [x.codice for x in e] == ["FORNITURA_OLTRE_LIMITE"]
    assert "xml_deflate" in e[0].messaggio and "ASSUNZIONE" in e[0].messaggio and "p.3" in e[0].fonte
    assert D.verifica_fornitura(man, limite_compresso=len(xml) - 1, punto_misura="xml_non_compresso")
    # senza XML: misura sugli allegati, dichiarata come limite inferiore
    solo = D.misura_fornitura({"allegati": [{"percorso": str(a)}]})
    assert solo["punto_misura"] == "allegati_base64_deflate" and solo["completa"] is False
    assert [x.codice for x in D.verifica_fornitura({"allegati": []}, richiedi_xml=True)] == ["FORNITURA_XML_ASSENTE"]
    with pytest.raises(ValueError):
        D.misura_fornitura(man, "a_occhio")


def test_fornitura_controlli_formali(tmp_path):
    pdf = _pdf_finto(tmp_path / "a.pdf", 1000)
    png = tmp_path / "x.pdf"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 100)
    man = {"dichiarazioni": 2, "allegati": [
        {"id": "1", "percorso": str(pdf), "file_type": "image/tiff", "nome_eg": "certificato_morte.pdf"},
        {"id": "2", "percorso": str(png), "file_type": "image/png"},
        {"id": "3", "percorso": str(tmp_path / "manca.pdf")},
        {"id": "4", "percorso": str(pdf), "nome_eg": "CERTIFICATO MORTE.PDF", "esito_validazione": "non_verificato"},
    ]}
    codici = sorted(x.codice for x in D.verifica_fornitura(man))
    assert codici == sorted(["FORNITURA_PIU_DICHIARAZIONI", "ALLEGATO_TIPO_INCOERENTE", "ALLEGATO_NOME_NON_VALIDO",
                             "ALLEGATO_FORMATO_NON_AMMESSO", "ALLEGATO_TIPO_NON_AMMESSO", "ALLEGATO_MANCANTE",
                             "ALLEGATO_CONFORMITA_NON_DIMOSTRATA"])
    for e in D.verifica_fornitura(man):
        assert e.fonte and e.percorso.startswith("fornitura")


@gs_ok
def test_fallback_pypdf_parti_pdfa_strutturalmente_pulite(multipagina, tmp_path, monkeypatch):
    monkeypatch.setattr(pdfa, "trova_verapdf", lambda: None)
    monkeypatch.setattr(D, "trova_qpdf", lambda: None)
    parti = D.riduci_o_suddividi(multipagina, 60_000, cartella_uscita=tmp_path, tentativi=((200, 0.4),))
    assert parti.rapporto["strumento_suddivisione"] == "pypdf"
    _verifica_senza_perdita(multipagina, parti, 60_000)
    assert all(v["validazione"]["indicativo"] == "indicativo_ok" for v in parti.rapporto["parti"]), \
        [v["validazione"]["motivi_indicativi"] for v in parti.rapporto["parti"]]
