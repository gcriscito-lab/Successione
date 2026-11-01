"""ImageData (xs:base64Binary) e FileName/FileType di reg:FileAttachment_Type, provati contro gli XSD in fonti/."""
import os
import random
from pathlib import Path

import pytest
from lxml import etree

from successioni.documenti import base64 as B
from successioni.documenti.corpus_sintetico import pdf_immagini_grandi, pdf_testo

XSD = Path(__file__).resolve().parents[1] / "fonti" / "Specifiche tecniche" / "SUC13_20250702"
REG = XSD / "registro" / "xsd" / "typesReg_v2.xsd"
DATI = XSD / "common" / "xsd" / "typesDati_v2.xsd"
NS_REG = "urn:www.agenziaentrate.gov.it:specificheTecniche:sco:reg:v2"
XS = "{http://www.w3.org/2001/XMLSchema}"


@pytest.fixture(scope="module")
def schema_allegato(tmp_path_factory):
    """Schema di prova che importa typesReg_v2.xsd (sola lettura) e dichiara un elemento FileAttachment_Type."""
    d = tmp_path_factory.mktemp("xsd")
    involucro = d / "prova.xsd"
    involucro.write_text(
        '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:reg="' + NS_REG + '" '
        'targetNamespace="urn:prova" elementFormDefault="qualified">'
        f'<xs:import namespace="{NS_REG}" schemaLocation="{REG.as_uri()}"/>'
        '<xs:element name="Allegato" type="reg:FileAttachment_Type"/></xs:schema>', encoding="utf-8")
    return etree.XMLSchema(etree.parse(str(involucro)))


def _istanza(campi: dict) -> etree._Element:
    radice = etree.Element("{urn:prova}Allegato", nsmap={"p": "urn:prova", "reg": NS_REG})
    for k in ("FileType", "FileName", "FileDescription", "ImageData"):
        if k in campi:
            etree.SubElement(radice, f"{{{NS_REG}}}{k}").text = campi[k]
    return radice


def test_tipo_xsd_letto_dalle_fonti():
    reg = etree.parse(str(REG))
    ct = reg.find(f".//{XS}complexType[@name='FileAttachment_Type']")
    figli = [e.get("name") for e in ct.iter(f"{XS}element")]
    assert figli == ["FileType", "FileName", "FileDescription", "ImageData"]
    image = ct.find(f".//{XS}element[@name='ImageData']")
    assert image.get("type") == "xs:base64Binary" and len(image) == 0          # nessuna faccetta
    nome = ct.find(f".//{XS}element[@name='FileName']")
    assert nome.find(f".//{XS}maxLength").get("value") == "100"
    assert nome.find(f".//{XS}restriction").get("base") == "cm:DatoAN_Type"
    enum = [e.get("value") for e in reg.find(f".//{XS}simpleType[@name='FileType_Type']").iter(f"{XS}enumeration")]
    assert tuple(enum) == B.L.TIPI_FILE_EG
    dati = etree.parse(str(DATI))
    patt = dati.find(f".//{XS}simpleType[@name='DatoAN_Type']//{XS}pattern").get("value")
    assert patt == B.PATTERN_DATO_AN_XSD


@pytest.mark.parametrize("n", list(range(0, 10)) + [1000, 65537])
def test_round_trip_bit_per_bit_lunghezze(n, tmp_path):
    dati = random.Random(n).randbytes(n)
    f = tmp_path / "x.bin"
    f.write_bytes(dati)
    t = B.incorpora_base64(f)
    assert len(t) == B.lunghezza_base64(n) and "\n" not in t and t.isascii()
    assert B.decodifica_base64(t) == dati


def test_round_trip_pdf_grandi_e_a_capo(tmp_path):
    for p in (pdf_testo(tmp_path / "t.pdf", 2), pdf_immagini_grandi(tmp_path / "g.pdf", lato_px=800)):
        orig = p.read_bytes()
        t = B.incorpora_base64(p)
        assert B.decodifica_base64(t) == orig
        a_capo = "\r\n".join(t[i:i + 76] for i in range(0, len(t), 76))     # forma RFC 2045: spazi XML ammessi
        assert B.decodifica_base64(a_capo) == orig
        (tmp_path / "rt.pdf").write_bytes(B.decodifica_base64(t))
        assert (tmp_path / "rt.pdf").read_bytes() == orig


@pytest.mark.parametrize("cattivo", ["QUJD!", "QUJ", "QU=D", "QUJDè", "QUJD=QUJD"])
def test_decodifica_rigorosa(cattivo):
    with pytest.raises(ValueError):
        B.decodifica_base64(cattivo)


NOMI = ["CERTIFICATO.PDF", "certificato.pdf", "CERTIFICATO_MORTE.PDF", "CERT MORTE (COPIA) 1/2.PDF", "-A.PDF",
        ".PDF", "À.PDF", "ATTO È.PDF", "\"X\".PDF", "A+B|C\\D.PDF", "A" * 100, "A" * 101, "ATTO N°1^2.PDF", "",
        "ATTO X.PDF", "ATTO\tX.PDF"]


@pytest.mark.parametrize("nome", NOMI)
def test_nome_file_equivalente_all_xsd(nome, schema_allegato):
    """La traduzione Python del pattern XSD da' lo stesso verdetto del validatore lxml sullo schema ufficiale."""
    xsd_ok = schema_allegato.validate(_istanza({"FileType": "application/pdf", "FileName": nome, "ImageData": "QUJD"}))
    assert xsd_ok == (B.valida_nome_file_eg(nome) == []), (nome, schema_allegato.error_log)
    normalizzato = B.normalizza_nome_file_eg(nome or "x")
    assert B.valida_nome_file_eg(normalizzato) == []
    assert schema_allegato.validate(_istanza({"FileType": "application/pdf", "FileName": normalizzato,
                                              "ImageData": "QUJD"}))


def test_dati_file_attachment_validi_secondo_xsd(tmp_path, schema_allegato):
    p = pdf_testo(tmp_path / "certificato di morte_2024.pdf", 1)
    campi = B.dati_file_attachment(p, descrizione="Certificato di morte - copia conforme")
    assert campi["FileType"] == "application/pdf" and campi["FileName"] == "CERTIFICATO DI MORTE-2024.PDF"
    el = _istanza(campi)
    assert schema_allegato.validate(el), schema_allegato.error_log
    testo = etree.tostring(el)
    ripreso = etree.fromstring(testo).find(f"{{{NS_REG}}}ImageData").text
    assert B.decodifica_base64(ripreso) == p.read_bytes()
    with pytest.raises(ValueError):
        B.dati_file_attachment(p, file_type="image/tiff")             # incoerente col contenuto
    with pytest.raises(ValueError):
        B.dati_file_attachment(p, file_type="image/png")              # fuori enumerazione XSD
    finto = tmp_path / "foto.pdf"
    finto.write_bytes(b"\x89PNG\r\n\x1a\n")
    with pytest.raises(ValueError):
        B.dati_file_attachment(finto)


def test_tipo_file_da_contenuto(tmp_path):
    assert B.tipo_file_eg(b"%PDF-1.4") == "application/pdf"
    assert B.tipo_file_eg(b"II*\x00....") == "image/tiff" and B.tipo_file_eg(b"MM\x00*") == "image/tiff"
    assert B.tipo_file_eg(b"GIF89a") is None
    assert B.ELEMENTI_EG_ALLEGATO[0] == "DichSostAll" and len(B.ELEMENTI_EG_ALLEGATO) == 11


def test_elementi_eg_dall_xsd_della_fornitura():
    f = etree.parse(str(XSD / "SUC" / "xsd" / "fornituraSUC13_v1.xsd"))
    nomi = tuple(e.get("name") for e in f.iter(f"{XS}element") if e.get("type") == "reg:FileAttachment_Type")
    assert nomi == B.ELEMENTI_EG_ALLEGATO
