import pytest
from successioni.collegamenti.base import sha256_bytes
from successioni.collegamenti.invio import (
    TrasportoSimulato,
    leggi_esi,
    leggi_stato_invii,
    richiesta_download,
)
from successioni.errori import DatiNonValidi


def test_leggi_esi_valido_e_rumore():
    testo = """
    Intestazione con testo non JSON
    {"tipoOperazione": "INVIO ", "resultCode": "00 ", "protocollo": "12345 "}
    Qualche riga spuria
    {"tipoOperazione": "RICEVUTA", "resultCode": "01"}
    """
    res = leggi_esi(testo)
    assert len(res) == 2
    assert res[0]["tipoOperazione"] == "INVIO"
    assert res[0]["resultCode"] == "00"
    assert res[0]["protocollo"] == "12345"
    assert res[1]["tipoOperazione"] == "RICEVUTA"


def test_leggi_esi_vuoto_e_malformato():
    assert leggi_esi("") == []
    assert leggi_esi("nessun json qui") == []
    testo_malformato = 'riga 1\n{json corrotto\n{"tipoOperazione": "INVIO"}'
    res = leggi_esi(testo_malformato)
    assert len(res) == 1
    assert res[0]["tipoOperazione"] == "INVIO"


def test_leggi_stato_invii_valido():
    testo = '{"result": {"esito": "OK", "resultCode": "00"}, "ricevuteList": [{"nomeFile": "test.ccf", "stato": "Ricevuto"}]}'
    st = leggi_stato_invii(testo)
    assert st["result"]["resultCode"] == "00"
    assert len(st["ricevute"]) == 1
    assert st["ricevute"][0]["nomeFile"] == "test.ccf"


def test_leggi_stato_invii_senza_result():
    testo = '{"ricevuteList": []}'
    with pytest.raises(DatiNonValidi) as exc_info:
        leggi_stato_invii(testo)
    assert "manca 'result'" in str(exc_info.value)


def test_richiesta_download_r01_r03_valida_e_errori():
    req = richiesta_download("R01", "utente1", protocollo="PROT123")
    assert req["tipoRichiesta"] == "R01"
    assert req["nomeUtente"] == "utente1"
    assert req["numeroProtocollo"] == "PROT123"

    with pytest.raises(DatiNonValidi) as exc_info:
        richiesta_download("R01", "utente1")
    assert "R01/R03 richiedono il numero di protocollo" in str(exc_info.value)

    with pytest.raises(DatiNonValidi) as exc_info:
        richiesta_download("R03", "utente1", protocollo="")
    assert "R01/R03 richiedono il numero di protocollo" in str(exc_info.value)


def test_richiesta_download_r02_r04_valida_e_errori():
    req = richiesta_download("R02", "utente1", data_da="01/01/2026T00:00", data_a="07/01/2026T23:59")
    assert req["tipoRichiesta"] == "R02"
    assert req["data_da"] == "01/01/2026T00:00"

    with pytest.raises(DatiNonValidi) as exc_info:
        richiesta_download("R02", "utente1", data_da="01/01/2026T00:00")
    assert "R02/R04 richiedono data_da e data_a" in str(exc_info.value)

    with pytest.raises(DatiNonValidi) as exc_info:
        richiesta_download("R04", "utente1")
    assert "R02/R04 richiedono data_da e data_a" in str(exc_info.value)


def test_richiesta_download_tipo_invalido():
    with pytest.raises(DatiNonValidi) as exc_info:
        richiesta_download("INVALID", "utente1")
    assert "tipoRichiesta: R01, R02, R03 o R04" in str(exc_info.value)


def test_trasporto_simulato_progressivo():
    t = TrasportoSimulato()
    assert t.reale is False
    assert t.automatico is True

    f1 = b"contenuto1"
    f2 = b"contenuto2"
    r1 = t.trasmetti(f1, "file1.dcm", {})
    r2 = t.trasmetti(f2, "file2.dcm", {})

    assert r1.tipo == "accettato"
    assert r1.protocollo == "SIM00000000000001"
    assert r2.protocollo == "SIM00000000000002"
    assert t.chiamate_trasmetti == 2


def test_trasporto_simulato_guasto_timeout_prima():
    t = TrasportoSimulato(guasto="timeout_prima")
    with pytest.raises(TimeoutError) as exc_info:
        t.trasmetti(b"data", "file.dcm", {})
    assert "connessione interrotta prima della ricezione" in str(exc_info.value)
    assert t.chiamate_trasmetti == 1


def test_trasporto_simulato_guasto_timeout_dopo_ricezione():
    t = TrasportoSimulato(guasto="timeout_dopo_ricezione")
    f = b"dati_ricevuti_ma_timeout"
    with pytest.raises(TimeoutError) as exc_info:
        t.trasmetti(f, "file.dcm", {})
    assert "risposta persa dopo la ricezione" in str(exc_info.value)

    h = sha256_bytes(f)
    resp = t.consulta({"sha256": h})
    assert resp.tipo == "accettato"
    assert resp.protocollo == "SIM00000000000001"


def test_trasporto_simulato_guasto_rifiuto():
    t = TrasportoSimulato(guasto="rifiuto", motivo_rifiuto="scarto formale")
    res = t.trasmetti(b"data", "file.dcm", {})
    assert res.tipo == "rifiutato"
    assert res.motivo == "scarto formale"


def test_trasporto_simulato_consulta_esito_e_guasto():
    t = TrasportoSimulato()
    res = t.consulta({"sha256": "non_esistente"})
    assert res.tipo == "sconosciuto"
    assert "nessun file con questa impronta" in res.motivo

    t.consultazione_guasta = True
    with pytest.raises(ConnectionError) as exc_info:
        t.consulta({"sha256": "non_esistente"})
    assert "consultazione non raggiungibile" in str(exc_info.value)
