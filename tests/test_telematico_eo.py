"""Quadro EO (titoli): XML completo, totali di EE, regole delle annotazioni XSD e controllo ufficiale SUC13 locale (dati sintetici)."""
from datetime import date

import pytest
from lxml import etree

from successioni.telematico.esporta import esporta_xml
from telematico_casi import caso_titoli, contesto_caso_a10
from test_telematico_controllo import NS, _esegui, _motivo_salto

D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"
CTX = contesto_caso_a10(data_riferimento=date(2025, 9, 1))
P = "beni[b_azioni01]."


def _es(mod=None, id_="b_azioni01"):
    d = caso_titoli()
    if mod:
        mod(next(b for b in d["beni"] if b["id"] == id_))
    return esporta_xml(d, CTX)


def _codici(es):
    return {(e.percorso, e.codice) for e in es.errori}


def test_xml_completo_con_titoli_e_totali_ee():
    es = _es()
    assert es.errori == [] and es.non_supportato == [] and es.quadri_mancanti == [], (es.errori, es.non_supportato)
    doc = etree.fromstring(es.xml)
    t = lambda xp: doc.xpath(D + xp, namespaces=NS)
    assert t("/suc:QuadroEO/suc:Modulo/suc:Titoli/suc:TipoTitolo/text()") == ["2", "4"]
    assert t("/suc:QuadroEO/suc:Modulo/suc:Titoli/suc:Possesso/suc:Valore/text()") == ["10000", "6000"]
    assert t("/suc:QuadroEE/suc:TotaleValoreTitoli/text()") == ["16000"]
    imm = int(t("/suc:QuadroEE/suc:TotaleValoreImmobili/text()")[0])
    altri = int((t("/suc:QuadroEE/suc:TotaleValoreAltriBeni/text()") or ["0"])[0])
    assert int(t("/suc:QuadroEE/suc:TotaleAttivo/text()")[0]) == imm + 16000 + altri
    assert t("/suc:Frontespizio/suc:Firma/suc:CasellaEO/text()") == ["1"] or t("//suc:CasellaEO/text()") == ["1"]


def test_titolo_esente_non_supportato():
    es = _es(lambda b: b.update(tipo_titolo="3"))
    assert es.xml is None and any("tipo_titolo=3" in s for s in es.non_supportato)


def test_quotato_richiede_codice_fiscale_emittente():
    es = _es(lambda b: b.update(tipo_titolo="1"))
    assert (P + "codice_fiscale_emittente", "DATO_MANCANTE") in _codici(es)


def test_codice_fiscale_emittente_con_cifra_di_controllo_errata():
    es = _es(lambda b: b.update(tipo_titolo="1", codice_fiscale_emittente="00000000019"))
    assert (P + "codice_fiscale_emittente", "VALORE_NON_VALIDO") in _codici(es)


def test_cf_emittente_diverso_da_defunto_ed_eredi():
    from telematico_casi import CF_ANNA
    for cf in (CF_ANNA, "RSSMRA40A01H501K"):   # erede del quadro EA; defunto
        es = _es(lambda b, cf=cf: b.update(tipo_titolo="2", codice_fiscale_emittente=cf))
        assert (P + "codice_fiscale_emittente", "REGOLA_CF_EMITTENTE") in _codici(es), cf


def test_codice_titolo_solo_per_quotati():
    es = _es(lambda b: b.update(codice_titolo="IT0000000019"))
    assert (P + "codice_titolo", "DATI_INCOERENTI") in _codici(es)


def test_bilancio_richiede_la_data_del_documento():
    es = _es(lambda b: b.update(tipo_documento="1"))
    assert (P + "data_documento", "DATO_MANCANTE") in _codici(es)
    es = _es(lambda b: b.update(tipo_documento="1", data_documento="2024-12-31"))
    assert es.errori == [] and es.xml is not None


def test_quantita_non_numerica_e_tipo_titolo_fuori_enumerazione():
    assert (P + "quantita", "VALORE_NON_VALIDO") in _codici(_es(lambda b: b.update(quantita="10,5")))
    assert (P + "tipo_titolo", "VALORE_NON_VALIDO") in _codici(_es(lambda b: b.update(tipo_titolo="9")))


def test_titolo_senza_devoluzione_e_un_errore():
    d = caso_titoli()
    d["devoluzioni"] = [x for x in d["devoluzioni"] if x["bene_id"] != "b_fondo001"]
    es = esporta_xml(d, CTX)
    assert es.xml is None and any(e.codice == "DEVOLUZIONE_MANCANTE" for e in es.errori)


def test_quadro_eo_non_attivo_e_un_errore():
    d = caso_titoli()
    d["opzioni"]["quadri_attivi"] = ["EA", "EB", "EC", "ER", "ED", "EG"]
    assert any(e.codice == "DATI_IN_QUADRO_NON_ATTIVO" for e in esporta_xml(d, CTX).errori)


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
def test_reale_controllo_ufficiale_locale_titoli(tmp_path):
    stato, dgn, wri, dcm = _esegui(_es().xml, tmp_path)
    assert stato == "positivo", (stato, dgn["diagnostici"])
    assert sorted((d["codice"], d["gravita"]) for d in dgn["diagnostici"]) == [("3345", 4)], dgn["diagnostici"]


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
def test_reale_controllo_ufficiale_locale_titolo_quotato(tmp_path):
    es = _es(lambda b: b.update(tipo_titolo="1", codice_fiscale_emittente="00000000018", codice_titolo="IT0000000019"))
    assert es.errori == [], es.errori
    stato, dgn, wri, dcm = _esegui(es.xml, tmp_path)
    assert stato == "positivo", (stato, dgn["diagnostici"])
