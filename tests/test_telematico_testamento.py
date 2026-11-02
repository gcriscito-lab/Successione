"""Dati della sezione Testamento (frontespizio): validazione di formato e regole di data. L'esportazione con testamento resta bloccata."""
from telematico_casi import caso_completo
from test_telematico_esporta import _bozza

TEST_OK = {"pubblico_ufficiale": "Notaio Sintetico", "data_pubblicazione": "2025-04-01", "ufficio_registrazione": "AAAA",
           "serie": "1T", "numero_registrazione": "123", "data_registrazione": "2025-04-10"}


def _caso(flag=True, sez=None):
    d = caso_completo()
    dich = d["opzioni"]["telematico"]["dichiarazione"]
    if flag is not None:
        dich["devoluzione_per_testamento"] = flag
    if sez is not None:
        dich["testamento"] = sez
    return d


def _errori(d):
    return {(e.percorso, e.codice) for e in _bozza(d).errori}


def test_testamento_valido_resta_non_esportabile_ma_senza_errori_di_dato():
    es = _bozza(_caso(True, dict(TEST_OK)))
    assert es.xml is None
    assert any("devoluzione_per_testamento" in s for s in es.non_supportato)
    assert not [e for e in es.errori if "testamento" in e.percorso]


def test_sezione_senza_flag_e_incoerente():
    assert ("opzioni.telematico.dichiarazione.testamento", "DATI_INCOERENTI") in _errori(_caso(None, dict(TEST_OK)))


def test_flag_senza_sezione_manca_il_dato():
    assert ("opzioni.telematico.dichiarazione.testamento", "DATO_MANCANTE") in _errori(_caso(True, None))


def test_pubblicazione_prima_del_decesso():
    s = dict(TEST_OK, data_pubblicazione="2025-03-09", data_registrazione="2025-04-10")  # decesso 2025-03-10
    assert ("opzioni.telematico.dichiarazione.testamento.data_pubblicazione", "REGOLA_DATA_PUBBLICAZIONE") in _errori(_caso(True, s))


def test_registrazione_prima_della_pubblicazione():
    s = dict(TEST_OK, data_registrazione="2025-03-31")
    assert ("opzioni.telematico.dichiarazione.testamento.data_registrazione", "REGOLA_DATA_REGISTRAZIONE") in _errori(_caso(True, s))


def test_campi_obbligatori_e_lunghezze():
    s = dict(TEST_OK, pubblico_ufficiale="x" * 51, serie="ABC", numero_registrazione="1234567")
    del s["ufficio_registrazione"]
    e = _errori(_caso(True, s))
    p = "opzioni.telematico.dichiarazione.testamento."
    assert (p + "pubblico_ufficiale", "VALORE_NON_VALIDO") in e
    assert (p + "serie", "VALORE_NON_VALIDO") in e
    assert (p + "numero_registrazione", "VALORE_NON_VALIDO") in e
    assert (p + "ufficio_registrazione", "DATO_MANCANTE") in e


def test_data_non_valida_e_testamento_estero():
    assert ("opzioni.telematico.dichiarazione.testamento.data_pubblicazione", "VALORE_NON_VALIDO") in _errori(
        _caso(True, dict(TEST_OK, data_pubblicazione="2025-02-30")))
    es = _bozza(_caso(True, {"estero": True}))
    assert not [e for e in es.errori if "testamento" in e.percorso]


def test_chiave_ignota_nella_sezione_e_segnalata():
    es = _bozza(_caso(True, dict(TEST_OK, inventata=1)))
    assert any("testamento.inventata" in s for s in es.non_supportato)
