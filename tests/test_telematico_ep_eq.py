"""Quadri EP (aeromobili) ed EQ (navi): XML completo, totali EE, righe di EH, regole delle annotazioni XSD, controllo SUC13 locale."""
from datetime import date

import pytest
from lxml import etree

from successioni.telematico.esporta import esporta_xml
from telematico_casi import caso_mezzi, contesto_caso_a10
from test_telematico_controllo import NS, _esegui, _motivo_salto

D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"
CTX = contesto_caso_a10(data_riferimento=date(2025, 9, 1))
EH = "/suc:QuadroEH/suc:PrimoModulo/suc:SezioneI_DichSost"


def _es(id_=None, **mod):
    d = caso_mezzi()
    if id_:
        b = next(x for x in d["beni"] if x["id"] == id_)
        for k, v in mod.items():
            if v is None:
                b.pop(k, None)
            else:
                b[k] = v
    return esporta_xml(d, CTX)


def _codici(es):
    return {(e.percorso, e.codice) for e in es.errori}


def test_xml_completo_con_aeromobile_e_nave():
    es = _es()
    assert es.errori == [] and es.non_supportato == [] and es.quadri_mancanti == [], (es.errori, es.non_supportato)
    doc = etree.fromstring(es.xml)
    t = lambda xp: doc.xpath(D + xp, namespaces=NS)
    assert t("/suc:QuadroEP/suc:Modulo/suc:Aeromobili/suc:Tipo/suc:MarcaModello/text()") == ["AEROMOBILE SINTETICO X1"]
    assert t("/suc:QuadroEQ/suc:Modulo/suc:Navi/suc:Tipo/suc:Dimensione/suc:Lunghezza/text()") == ["9"]
    assert t("/suc:QuadroEE/suc:TotaleValoreAereiNavi/text()") == ["42000"]
    assert t(EH + "/suc:Navi/suc:FlagNavi/text()") == ["1"]
    assert t(EH + "/suc:Navi/suc:NumeroIscrizione/text()") == ["98765"]
    assert t(EH + "/suc:Aeromobili/suc:FlagAeromobili/text()") == ["1"]
    assert t(EH + "/suc:Aeromobili/suc:NumeroImmatricolazione/text()") == ["123456"]


def test_anno_fuori_intervallo_e_dato_mancante():
    assert ("beni[b_aereo001].anno_costruzione", "VALORE_NON_VALIDO") in _codici(_es("b_aereo001", anno_costruzione="1750"))
    assert ("beni[b_aereo001].anno_costruzione", "VALORE_NON_VALIDO") in _codici(_es("b_aereo001", anno_costruzione="2099"))
    assert ("beni[b_aereo001].marca_modello", "DATO_MANCANTE") in _codici(_es("b_aereo001", marca_modello=None))


def test_lunghezza_e_stazza_sono_una_scelta_esclusiva():
    assert ("beni[b_barca001].lunghezza", "DATI_INCOERENTI") in _codici(_es("b_barca001", stazza="5"))
    assert ("beni[b_barca001].lunghezza", "DATI_INCOERENTI") in _codici(_es("b_barca001", lunghezza=None))
    es = _es("b_barca001", lunghezza=None, stazza="5")
    assert es.errori == [] and b"<suc:Stazza>5</suc:Stazza>" in es.xml


def test_tipo_unita_fuori_enumerazione_e_numeri_non_numerici():
    assert ("beni[b_barca001].tipo_unita", "VALORE_NON_VALIDO") in _codici(_es("b_barca001", tipo_unita="3"))
    assert ("beni[b_barca001].numero_iscrizione", "VALORE_NON_VALIDO") in _codici(_es("b_barca001", numero_iscrizione="12A"))
    assert ("beni[b_aereo001].numero_immatricolazione", "VALORE_NON_VALIDO") in _codici(
        _es("b_aereo001", numero_immatricolazione="12345678901"))


def test_piu_navi_non_supportate_in_eh():
    d = caso_mezzi()
    seconda = {**next(b for b in d["beni"] if b["id"] == "b_barca001"), "id": "b_barca002", "numero_iscrizione": "11111"}
    d["beni"].append(seconda)
    for pid in ("p_anna0001", "p_luca0001"):
        d["devoluzioni"].append({"id": f"d_barc2{pid[2:6]}", "_origine": {}, "bene_id": "b_barca002", "persona_id": pid,
                                 "quota": {"num": 1, "den": 2}, "diritto": "1"})
    es = esporta_xml(d, CTX)
    assert es.xml is None and any("navi nel quadro EQ" in s for s in es.non_supportato)


def test_senza_devoluzione_e_un_errore():
    d = caso_mezzi()
    d["devoluzioni"] = [x for x in d["devoluzioni"] if x["bene_id"] != "b_aereo001"]
    es = esporta_xml(d, CTX)
    assert es.xml is None and any(e.codice == "DEVOLUZIONE_MANCANTE" for e in es.errori)


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
def test_reale_controllo_ufficiale_locale_mezzi(tmp_path):
    stato, dgn, wri, dcm = _esegui(_es().xml, tmp_path)
    assert stato == "positivo", (stato, dgn["diagnostici"])
    assert sorted((d["codice"], d["gravita"]) for d in dgn["diagnostici"]) == [("3345", 4)], dgn["diagnostici"]
