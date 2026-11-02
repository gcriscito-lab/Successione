"""Successione testamentaria con soli eredi: XML completo e controllo ufficiale SUC13 in locale (dati sintetici)."""
import pytest
from lxml import etree

from successioni.telematico import fonti
from successioni.telematico.esporta import esporta_xml
from datetime import date

from telematico_casi import caso_testamento, caso_testamento_legato, caso_testamento_legatario, contesto_caso_a10
from test_telematico_controllo import NS, _esegui, _motivo_salto

D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"


def _es():
    return esporta_xml(caso_testamento(), contesto_caso_a10())


def test_xml_completo_con_testamento():
    es = _es()
    assert es.errori == [] and es.non_supportato == [], (es.errori, es.non_supportato)
    assert es.xml is not None
    doc = etree.fromstring(es.xml)
    t = lambda xp: doc.xpath(D + xp, namespaces=NS)
    assert t("/suc:Frontespizio/suc:TipoDichiarazione/suc:Devoluzione/suc:DevoluzionePerTestamento/text()") == ["1"]
    assert t("/suc:Frontespizio/suc:TipoDichiarazione/suc:Devoluzione/suc:DevoluzionePerLegge") == []
    assert t("/suc:Frontespizio/suc:TipoDichiarazione/suc:Devoluzione/suc:Testamento/suc:Registrazione/reg:UfficioDiRegistrazione/text()") == ["795"]
    assert t("/suc:QuadroEG/suc:Testamento/suc:TestamentoNum/text()") == ["1"]
    assert t("/suc:QuadroEH/suc:PrimoModulo/suc:SezioneI_DichSost/suc:Testamento/suc:PresenzaTestamento/suc:FlagTestamento/text()") == ["1"]
    assert t("/suc:QuadroEH/suc:PrimoModulo/suc:SezioneI_DichSost/suc:Testamento/suc:FlagAssenzaTestamento") == []


def test_testamento_senza_allegato_eg2_non_e_completo():
    d = caso_testamento()
    d["documenti_ref"] = [x for x in d["documenti_ref"] if x["tipo_eg"] != "Testamento"]
    es = esporta_xml(d, contesto_caso_a10())
    assert es.xml is None
    assert any(m.codice == "ALLEGATO_OBBLIGATORIO_MANCANTE" and "Testamento" in m.percorso for m in es.quadri_mancanti)


def test_allegato_testamento_senza_devoluzione_per_testamento_e_incoerente():
    d = caso_testamento()
    d["opzioni"]["telematico"]["dichiarazione"]["devoluzione_per_testamento"] = False
    d["opzioni"]["telematico"]["dichiarazione"]["devoluzione_per_legge"] = True
    del d["opzioni"]["telematico"]["dichiarazione"]["testamento"]
    es = esporta_xml(d, contesto_caso_a10())
    assert es.xml is None and any(e.codice == "DATI_INCOERENTI" for e in es.errori)


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
def test_reale_controllo_ufficiale_locale_testamento(tmp_path):
    stato, dgn, wri, dcm = _esegui(_es().xml, tmp_path)
    # stesso esito del caso base A10: positivo, con la sola anomalia di entita' ridotta 3345 (gravita' 4)
    assert stato == "positivo", (stato, dgn["diagnostici"])
    assert sorted((d["codice"], d["gravita"]) for d in dgn["diagnostici"]) == [("3345", 4)], dgn["diagnostici"]


def _es_legatario():
    # entro i dodici mesi dal decesso: le tardive con imposta dovuta restano non finalizzabili
    return esporta_xml(caso_testamento_legatario(), contesto_caso_a10(data_riferimento=date(2025, 9, 1)))


def test_xml_completo_con_legatario():
    es = _es_legatario()
    assert es.errori == [] and es.non_supportato == [] and es.quadri_mancanti == [], (es.errori, es.non_supportato)
    doc = etree.fromstring(es.xml)
    t = lambda xp: doc.xpath(D + xp, namespaces=NS)
    assert t("/suc:Frontespizio/suc:Beneficiari/suc:NumeroLegatari/text()") == ["1"]
    assert t("/suc:Frontespizio/suc:Beneficiari/suc:NumeroEredi/text()") == ["2"]
    assert "2" in t("/suc:QuadroEA//suc:TipoSoggetto/text()")


def test_legatario_senza_testamento_e_incoerente():
    d = caso_testamento_legatario()
    dich = d["opzioni"]["telematico"]["dichiarazione"]
    dich["devoluzione_per_legge"], dich["devoluzione_per_testamento"] = True, False
    del dich["testamento"]
    d["documenti_ref"] = [x for x in d["documenti_ref"] if x["tipo_eg"] != "Testamento"]
    es = esporta_xml(d, contesto_caso_a10(data_riferimento=date(2025, 9, 1)))
    assert es.xml is None and any(e.codice == "DATI_INCOERENTI" and e.percorso.endswith(".ruolo") for e in es.errori)


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
def test_reale_controllo_ufficiale_locale_legatario(tmp_path):
    stato, dgn, wri, dcm = _esegui(_es_legatario().xml, tmp_path)
    assert stato == "positivo", (stato, dgn["diagnostici"])
    assert sorted((d["codice"], d["gravita"]) for d in dgn["diagnostici"]) == [("3345", 4)], dgn["diagnostici"]


def _es_legato():
    return esporta_xml(caso_testamento_legato(), contesto_caso_a10(data_riferimento=date(2025, 9, 1)))


def test_xml_completo_con_passivita_tipo_11():
    es = _es_legato()
    assert es.errori == [] and es.non_supportato == [] and es.quadri_mancanti == [], (es.errori, es.non_supportato)
    doc = etree.fromstring(es.xml)
    pas = doc.xpath(D + "/suc:QuadroED//suc:Passivita[suc:Tipo='11']", namespaces=NS)
    assert len(pas) == 1
    poss = pas[0].xpath("suc:Possesso/*", namespaces=NS)
    assert [etree.QName(x).localname for x in poss] == ["Valore"]  # nessun numeratore/denominatore (annotazione XSD)
    assert pas[0].xpath("suc:Possesso/suc:Valore/text()", namespaces=NS) == ["2000"]
    assert len(pas[0].xpath("suc:RipartizioneED/suc:Ripartizione", namespaces=NS)) == 2


def test_tipo_11_con_possesso_e_un_errore():
    d = caso_testamento_legato()
    d["opzioni"]["telematico"]["passivita"]["ps_legato1"]["possesso"] = "1/1"
    es = esporta_xml(d, contesto_caso_a10(data_riferimento=date(2025, 9, 1)))
    assert es.xml is None and any(e.codice == "REGOLA_POSSESSO_TIPO_11" for e in es.errori)


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
def test_reale_controllo_ufficiale_locale_legato(tmp_path):
    stato, dgn, wri, dcm = _esegui(_es_legato().xml, tmp_path)
    assert stato == "positivo", (stato, dgn["diagnostici"])
    assert sorted((d["codice"], d["gravita"]) for d in dgn["diagnostici"]) == [("3345", 4)], dgn["diagnostici"]
