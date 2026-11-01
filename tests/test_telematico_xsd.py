"""Validazione XSD SUC13 (lxml sugli XSD di fonti/) e formati dei tipi semplici.

Esito di queste prove: controllo locale di schema. NON e' il controllo ufficiale dell'Agenzia.
"""
from __future__ import annotations

from decimal import Decimal
from fractions import Fraction

import pytest

from successioni.telematico import formati as F
from successioni.telematico import fonti, xsd
from successioni.telematico.esporta import codice_enum, esporta_xml

from telematico_casi import caso_completo, contesto


@pytest.fixture(scope="module")
def xml_valido() -> bytes:
    es = esporta_xml(caso_completo(), contesto(scopo="bozza_tecnica"))
    assert es.xml is not None, (es.errori, es.non_supportato)
    return es.xml


def test_xsd_dalle_fonti_compila():
    assert fonti.xsd_principale().is_file()
    assert "fonti/Specifiche tecniche/SUC13_20250702" in fonti.xsd_principale().as_posix()
    assert xsd.schema() is not None


def test_xml_sintetico_valido(xml_valido):
    assert xsd.valida_xsd(xml_valido) == []
    assert xml_valido.startswith(b'<?xml version="1.0" encoding="UTF-8"?>')
    xml_valido.decode("utf-8")  # UTF-8 valido


def test_errore_predisposto_formato_rifiutato_con_xpath_e_fonte(xml_valido):
    rotto = xml_valido.replace(b"<suc:Valore>126000</suc:Valore>", b"<suc:Valore>126000,50</suc:Valore>")
    assert rotto != xml_valido
    err = xsd.valida_xsd(rotto)
    assert err, "un importo con decimali in un DatoNP deve essere rifiutato"
    e = err[0]
    assert e.codice == "XSD_FORMATO"
    assert "126000,50" in e.messaggio and "Valore" in e.messaggio
    assert e.percorso.startswith("/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione/suc:QuadroEC")
    assert e.percorso.endswith("suc:Valore")
    assert "fornituraSUC13_v1.xsd" in e.fonte and "SUC13_20250702" in e.fonte


def test_errore_predisposto_enumerazione(xml_valido):
    rotto = xml_valido.replace(b"<suc:CodiceDiritto_P>1</suc:CodiceDiritto_P>", b"<suc:CodiceDiritto_P>99</suc:CodiceDiritto_P>", 1)
    err = xsd.valida_xsd(rotto)
    assert len(err) == 1, err
    e = err[0]
    assert e.codice == "XSD_VALORE_NON_AMMESSO" and "<CodiceDiritto_P>" in e.messaggio, e
    assert "CodiciDirittoImmobili_Type" in e.messaggio and "1S" in e.messaggio  # elenco dei valori dallo schema


def test_errore_predisposto_ordine_sequenza(xml_valido):
    a = b"<suc:TipoSoggetto>1</suc:TipoSoggetto>"
    b = b"<suc:GradoParentela>02</suc:GradoParentela>"
    rotto = xml_valido.replace(a + b"\n              " + b, b + b"\n              " + a, 1)
    assert rotto != xml_valido
    err = xsd.valida_xsd(rotto)
    assert any(e.codice == "XSD_ELEMENTO_NON_ATTESO" and "GradoParentela" in e.messaggio for e in err), err


def test_elemento_obbligatorio_mancante(xml_valido):
    rotto = xml_valido.replace(b"<suc:CodiceFiscaleDefunto>RSSMRA40A01H501K</suc:CodiceFiscaleDefunto>", b"")
    err = xsd.valida_xsd(rotto)
    assert any("CodiceFiscaleDefunto" in e.messaggio for e in err), err


def test_xml_non_ben_formato():
    err = xsd.valida_xsd(b"<tm:Messaggio")
    assert err and err[0].codice == "XML_NON_BEN_FORMATO"


def test_enumerazioni_lette_dagli_xsd():
    imm = xsd.enumerazioni("CodiciDirittoImmobili_Type")
    assert set(imm) == {"10", "1", "1S", "1T", "2", "2S", "2T", "4", "5", "6"}
    assert set(xsd.enumerazioni("CodiciDirittoNonImmobiliDevoluzione")) == {"1", "2", "7", "8"}
    assert xsd.enumerazioni("TipoSoggetto_Type")["3"].startswith("Chiamato")
    assert "5A" in xsd.enumerazioni("GradoParentela_Type")
    assert set(xsd.enumerazioni("TipoCespite_Type")) == {"BI", "CR", "DN", "AB", "GD"}


def test_codici_diritto_alias_documentati():
    assert codice_enum("proprieta", "CodiciDirittoImmobili_Type", alias_descrizione=True) == "1"
    assert codice_enum("nuda_proprieta", "CodiciDiritto_Type", alias_descrizione=True) == "2"
    assert codice_enum("08", "CodiciDiritto_Type", alias_descrizione=True) == "8"
    assert codice_enum("usufrutto", "CodiciDiritto_Type", alias_descrizione=True) == "8"
    with pytest.raises(F.ValoreXml):
        codice_enum("usufrutto", "CodiciDirittoImmobili_Type", alias_descrizione=True)  # il defunto non ha 8 in EB/EC
    with pytest.raises(F.ValoreXml):
        codice_enum("proprieta", "CodiciDirittoImmobili_Type")  # alias solo se richiesto


def test_formati():
    assert F.data("2025-03-10") == "10032025"
    with pytest.raises(F.ValoreXml):
        F.data("2025-02-30")
    assert F.euro_intero("126000") == "126000"
    with pytest.raises(F.ValoreXml):
        F.euro_intero("126000.50")  # nessun arrotondamento silenzioso
    with pytest.raises(F.ValoreXml):
        F.euro_intero("0")
    assert F.euro_centesimi("5.5") == "5,50"
    assert F.numeratore_possesso(1) == "1,00"
    assert F.an("Via  del Corso 1") == "VIA DEL CORSO 1"
    with pytest.raises(F.ValoreXml):
        F.an("ça va")
    assert F.frazione_a_centesimi(Fraction(15000, 2)) == (Decimal("7500.00"), True)
    assert F.frazione_a_centesimi(Fraction(20000, 3)) == (Decimal("6666.67"), False)
    assert F.frazione_a_centesimi(Fraction(40000, 3)) == (Decimal("13333.33"), False)
    assert F.frazione_a_centesimi(Fraction(1, 200)) == (Decimal("0.01"), False)  # meta' centesimo: HALF_UP
    assert F.quota_grezza({"num": 100, "den": 100}) == (100, 100)  # non ridotta


def test_mappa_generata_aggiornata():
    """docs/regole/mappa_xsd_albero.md deve coincidere con quanto rigenerato dagli XSD in fonti/."""
    from pathlib import Path

    from successioni.telematico.mappa import genera
    file = Path(__file__).resolve().parents[1] / "docs" / "regole" / "mappa_xsd_albero.md"
    assert file.read_text(encoding="utf-8") == genera(), \
        "rigenerare con: PYTHONPATH=src python3 -m successioni.telematico.mappa > docs/regole/mappa_xsd_albero.md"
