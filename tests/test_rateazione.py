"""Pagamento rateale dell'imposta di successione (EF18ter col. 2-3). Regole: annotazioni XSD PagamentoRateale/Acconto e
Fascicolo I p. PDF 48. Dati sintetici."""
import math
from datetime import date

import pytest
from lxml import etree

from telematico_casi import caso_a10, contesto_caso_a10
from successioni.telematico.esporta import esporta_xml
from test_telematico_controllo import _esegui, _motivo_salto

D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"
CTX = dict(data_riferimento=date(2026, 3, 9))


def caso(valore="2400000", tempistica="2", rate=None, acconto=None):
    d = caso_a10()
    d["beni"][2]["valore"] = valore
    dich = d["opzioni"]["telematico"]["dichiarazione"]
    dich["tempistica_pagamento"] = tempistica
    if rate is not None:
        dich["pagamento_rateale"] = rate
    if acconto is not None:
        dich["acconto"] = acconto
    return d


def esporta(d):
    return esporta_xml(d, contesto_caso_a10(**CTX))


def imposta(valore="2400000"):
    return esporta(caso(valore)).mappa["calcolo:EF18bis"]["imposta"]


def vals(es, xp):
    doc = etree.fromstring(es.xml)
    return doc.xpath(f"{D}/{xp}/text()", namespaces={k: v for k, v in doc.nsmap.items() if k})


def codici(es):
    return {(e.codice, e.percorso.rsplit(".", 1)[-1]) for e in es.errori}


VBIS = "suc:QuadroEF/suc:SezioneVBis_ImpostaSuccessione/suc:ImpostaCalcolata"


def test_senza_rateazione_invariato():
    es = esporta(caso())
    assert es.completo and not vals(es, f"{VBIS}/suc:PagamentoRateale")
    assert vals(es, "suc:QuadroEF/suc:TotaleDaVersare") == [f"{4435 + imposta()},00"]


@pytest.mark.parametrize("tempistica,aggiunto", [("2", 5000), ("1", 0)])
def test_rateale_totale_secondo_la_tempistica(tempistica, aggiunto):
    imp = imposta()                                   # 22396: residuo 17396 -> al massimo 8 rate
    es = esporta(caso(tempistica=tempistica, rate=8, acconto="5000"))
    assert es.completo, [e.messaggio for e in es.errori]
    assert vals(es, f"{VBIS}/suc:PagamentoRateale") == ["8"] and vals(es, f"{VBIS}/suc:Acconto") == ["5000"]
    assert vals(es, f"{VBIS}/suc:ImpostaDaVersare") == [str(imp)]
    # EF19: altre somme + acconto (tempistica 2) oppure solo le altre somme (tempistica 1), p. PDF 48
    assert vals(es, "suc:QuadroEF/suc:TotaleDaVersare") == [f"{4435 + aggiunto},00"]


def test_acconto_minimo_venti_per_cento():
    imp = imposta()
    minimo = math.ceil(imp / 5)
    assert esporta(caso(rate=8, acconto=str(minimo))).completo
    es = esporta(caso(rate=8, acconto=str(minimo - 1)))
    assert es.xml is None and ("VALORE_NON_VALIDO", "acconto") in codici(es)


@pytest.mark.parametrize("rate,acconto,atteso", [
    (9, "5000", ("VALORE_NON_VALIDO", "pagamento_rateale")),     # residuo <= 20.000: al massimo 8 rate
    (13, "5000", ("VALORE_NON_VALIDO", "pagamento_rateale")),
    (0, "5000", ("VALORE_NON_VALIDO", "pagamento_rateale")),
    (True, "5000", ("VALORE_NON_VALIDO", "pagamento_rateale")),  # il vecchio flag booleano non e' piu' un numero di rate
    (4, None, ("DATO_MANCANTE", "acconto")),
    (None, "5000", ("DATO_MANCANTE", "pagamento_rateale")),
    (4, "21500", ("VALORE_NON_VALIDO", "pagamento_rateale")),    # residuo 896 < 1.000
    (4, "99999999", ("VALORE_NON_VALIDO", "acconto")),           # oltre l'imposta da versare
    (4, "5000.5", ("VALORE_NON_VALIDO", "acconto")),
])
def test_dati_non_validi(rate, acconto, atteso):
    es = esporta(caso(rate=rate, acconto=acconto))
    assert es.xml is None and atteso in codici(es), codici(es)


def test_oltre_ventimila_di_residuo_fino_a_dodici_rate():
    valore = "3600000"
    imp = imposta(valore)
    acc = math.ceil(imp / 5)
    assert imp - acc > 20000, "il caso di prova deve avere un residuo oltre 20.000"
    es = esporta(caso(valore, rate=12, acconto=str(acc)))
    assert es.completo, [e.messaggio for e in es.errori]
    assert vals(es, f"{VBIS}/suc:PagamentoRateale") == ["12"]
    assert esporta(caso(valore, rate=13, acconto=str(acc))).xml is None


def test_rateale_senza_imposta_dovuta_e_respinto():
    d = caso_a10()
    d["opzioni"]["telematico"]["dichiarazione"].update(pagamento_rateale=4, acconto="5000")
    es = esporta_xml(d, contesto_caso_a10())
    assert es.xml is None and ("VALORE_NON_VALIDO", "pagamento_rateale") in codici(es)


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
@pytest.mark.parametrize("tempistica", ["1", "2"])
@pytest.mark.java
def test_controllo_ufficiale_locale(tmp_path, tempistica):
    es = esporta(caso(tempistica=tempistica, rate=8, acconto="5000"))
    assert es.completo
    stato, dgn, wri, _ = _esegui(es.xml, tmp_path)
    assert stato == "positivo", (dgn["diagnostici"], wri[:800])
