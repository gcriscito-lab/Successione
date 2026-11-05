"""Sostitutiva codici 1/2: sezione V-bis (imposta di successione, EF18bis col. 3). Dati sintetici."""
from datetime import date

import pytest
from lxml import etree

from successioni.telematico import fonti
from successioni.telematico.esporta import esporta_xml
from successioni.telematico.xsd import valida_xsd
from telematico_casi import caso_a10, contesto_caso_a10
from test_telematico_controllo import _esegui, _motivo_salto

NS = {"tm": fonti.NS_TM, "suc": fonti.NS_SUC, "reg": fonti.NS_REG}
D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"
IC = f"{D}/suc:QuadroEF/suc:SezioneVBis_ImpostaSuccessione/suc:ImpostaCalcolata"


def _t(doc, xp):
    return doc.xpath(xp, namespaces=NS)


def caso(codice="2", dovuta=True, **dich):
    d = caso_a10()
    if dovuta:
        d["beni"][2]["valore"] = "2400000"   # ciascun figlio oltre la franchigia
        d["opzioni"]["telematico"]["dichiarazione"]["tempistica_pagamento"] = "2"
    d["opzioni"]["tipo_dichiarazione"] = "sostitutiva"
    d["opzioni"]["telematico"]["dichiarazione"].update(
        codice_sostitutiva=codice, prima_anno="2026", prima_volume="88888", prima_numero="123", **dich)
    return d


def esporta(d):
    return esporta_xml(d, contesto_caso_a10(data_riferimento=date(2026, 3, 9)))


def valido(es):
    assert es.errori == [] and es.completo, (es.errori, es.quadri_mancanti, es.non_supportato)
    assert valida_xsd(es.xml) == []
    return etree.fromstring(es.xml)


def imposta(es):
    return int(es.mappa["calcolo:EF18bis"]["imposta"])


@pytest.mark.parametrize("codice", ["1", "2"])
def test_a_nessuna_imposta_versata(codice):
    es = esporta(caso(codice))
    doc = valido(es)
    imp = imposta(es)
    assert imp > 10
    assert _t(doc, f"{IC}/suc:Imposta/text()") == [str(imp)]
    assert not _t(doc, f"{IC}/suc:ImpostaVersata")
    assert _t(doc, f"{IC}/suc:ImpostaDaVersare/text()") == [str(imp)]
    assert _t(doc, f"{IC}/suc:TempisticaPagamento/text()") == ["2"]


def test_b_versata_parziale_totale_coerente():
    imp = imposta(esporta(caso("2")))
    versata = imp // 2
    es = esporta(caso("2", successione_versata=str(versata)))
    doc = valido(es)
    assert _t(doc, f"{IC}/suc:ImpostaVersata/text()") == [str(versata)]
    assert _t(doc, f"{IC}/suc:ImpostaDaVersare/text()") == [str(imp - versata)]
    # codice 2: ipocatastali 4435 meno le circoscrizioni (120 + 85) non dovute con il codice 2
    base = int(_t(doc, f"{D}/suc:QuadroEF/suc:TotaleDaVersare/text()")[0].split(",")[0]) - (imp - versata)
    assert base == 4435 - 205
    assert _t(doc, f"{D}/suc:Frontespizio/suc:ImportoDaVersare/text()") == _t(doc, f"{D}/suc:QuadroEF/suc:TotaleDaVersare/text()")


def test_b_residuo_fino_a_dieci_euro_omette_importo_da_versare():
    imp = imposta(esporta(caso("2")))
    es = esporta(caso("2", successione_versata=str(imp - 10)))
    doc = valido(es)
    assert _t(doc, f"{IC}/suc:ImpostaVersata/text()") == [str(imp - 10)]
    assert not _t(doc, f"{IC}/suc:ImpostaDaVersare")
    assert not _t(doc, f"{IC}/suc:TempisticaPagamento")
    assert _t(doc, f"{D}/suc:QuadroEF/suc:TotaleDaVersare/text()") == ["4230,00"]


def test_b_residuo_zero_non_richiede_tempistica():
    imp = imposta(esporta(caso("2")))
    d = caso("2", successione_versata=str(imp))
    del d["opzioni"]["telematico"]["dichiarazione"]["tempistica_pagamento"]
    doc = valido(esporta(d))
    assert not _t(doc, f"{IC}/suc:ImpostaDaVersare")


def test_c_versata_superiore_all_imposta_non_genera_xml():
    imp = imposta(esporta(caso("2")))
    es = esporta(caso("2", successione_versata=str(imp + 1)))
    assert es.xml is None and not es.completo
    testo = " ".join(e.messaggio for e in es.quadri_mancanti + es.errori)
    assert "superiore a quella riliquidata" in testo, testo


def test_d_imposta_non_dovuta_con_versata_da_rimborsare():
    es = esporta(caso("2", dovuta=False, successione_versata="500"))
    doc = valido(es)
    assert _t(doc, f"{D}/suc:QuadroEF/suc:SezioneVBis_ImpostaSuccessione/suc:ImpostaNonDovuta/text()") == ["1"]
    assert "IMPOSTA_VERSATA_DA_RIMBORSARE" in {a.codice for a in es.avvisi}


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
@pytest.mark.parametrize("versata", [None, "partial"])
def test_e_controllo_ufficiale_locale(tmp_path, versata):
    extra = {}
    if versata:
        extra["successione_versata"] = str(imposta(esporta(caso("2"))) // 2)
    es = esporta(caso("2", **extra))
    valido(es)
    stato, dgn, wri, dcm = _esegui(es.xml, tmp_path)
    assert stato == "positivo", (stato, dgn["diagnostici"], wri)
    assert dcm
