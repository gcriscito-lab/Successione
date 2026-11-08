"""Quadro EN (aziende): XML completo, totale EE, riga EH9, regole delle annotazioni XSD, controllo SUC13 locale (dati sintetici)."""
from datetime import date

import pytest
from lxml import etree

from successioni.telematico.esporta import esporta_xml
from telematico_casi import caso_azienda, contesto_caso_a10
from test_telematico_controllo import NS, _esegui, _motivo_salto

D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"
CTX = contesto_caso_a10(data_riferimento=date(2025, 9, 1))
P = "beni[b_azien001]."


def _es(bene=None, dich=None):
    d = caso_azienda()
    if bene:
        next(b for b in d["beni"] if b["id"] == "b_azien001").update(bene)
    if dich:
        d["opzioni"]["telematico"]["dichiarazione"].update(dich)
    return esporta_xml(d, CTX)


def _codici(es):
    return {(e.percorso, e.codice) for e in es.errori}


def test_xml_completo_con_azienda():
    es = _es()
    assert es.errori == [] and es.non_supportato == [] and es.quadri_mancanti == [], (es.errori, es.non_supportato)
    doc = etree.fromstring(es.xml)
    t = lambda xp: doc.xpath(D + xp, namespaces=NS)
    assert t("/suc:QuadroEN/suc:Modulo/suc:Aziende/suc:Descrizione/suc:CodiceFiscale/text()") == ["00000000018"]
    assert t("/suc:QuadroEN/suc:Modulo/suc:Aziende/suc:Valore/text()") == ["20000"]
    assert t("/suc:QuadroEE/suc:TotaleValoreAziende/text()") == ["20000"]
    assert t("/suc:QuadroEH/suc:PrimoModulo/suc:SezioneI_DichSost/suc:Aziende/suc:FlagAzienda/text()") == ["1"]
    assert t("/suc:QuadroEH/suc:PrimoModulo/suc:SezioneI_DichSost/suc:Aziende/suc:CameraCommercio/text()") == ["ROMA"]


def test_codice_fiscale_azienda_obbligatorio_e_con_cifra_di_controllo():
    assert (P + "codice_fiscale_emittente", "DATO_MANCANTE") in _codici(_es({"codice_fiscale_emittente": None}))
    assert (P + "codice_fiscale_emittente", "VALORE_NON_VALIDO") in _codici(_es({"codice_fiscale_emittente": "00000000019"}))


def test_diritto_ammesso_solo_1_o_2():
    es = _es({"diritto": "3"})
    assert es.xml is None and any(e.codice in ("REGOLA_DIRITTO_AZIENDA", "VALORE_NON_VALIDO") for e in es.errori)


def test_dati_del_rigo_eh9_obbligatori_con_il_quadro_en():
    es = _es(dich={"azienda_camera_commercio": ""})
    assert ("opzioni.telematico.dichiarazione.azienda_camera_commercio", "DATO_MANCANTE") in _codici(es)
    es = _es(dich={"azienda_data_deposito": "2030-01-01"})
    assert ("opzioni.telematico.dichiarazione.azienda_data_deposito", "VALORE_NON_VALIDO") in _codici(es)


def test_inventario_non_supportato_e_data_senza_inventario_incoerente():
    es = _es({"inventario": "1", "data_redazione_inventario": "2025-01-31"})
    assert es.xml is None and any("inventario" in s for s in es.non_supportato)
    assert (P + "data_redazione_inventario", "DATI_INCOERENTI") in _codici(_es({"data_redazione_inventario": "2025-01-31"}))


def test_azienda_senza_devoluzione_e_un_errore():
    d = caso_azienda()
    d["devoluzioni"] = [x for x in d["devoluzioni"] if x["bene_id"] != "b_azien001"]
    es = esporta_xml(d, CTX)
    assert es.xml is None and any(e.codice == "DEVOLUZIONE_MANCANTE" for e in es.errori)


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
@pytest.mark.java
def test_reale_controllo_ufficiale_locale_azienda(tmp_path):
    stato, dgn, wri, dcm = _esegui(_es().xml, tmp_path)
    assert stato == "positivo", (stato, dgn["diagnostici"])
    assert sorted((d["codice"], d["gravita"]) for d in dgn["diagnostici"]) == [("3345", 4)], dgn["diagnostici"]
