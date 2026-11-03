from datetime import date
from decimal import Decimal
import pytest

from successioni import valori as V
from successioni.telematico.formati import (
    ValoreXml,
    an,
    cb,
    cf,
    data,
    data_iso,
    email,
    euro_centesimi,
    euro_intero,
    quota_grezza,
    telefono,
)


def test_an_valido_e_limiti():
    assert an("rossi mario") == "ROSSI MARIO"
    assert an("ABC", massimo=3) == "ABC"
    with pytest.raises(ValoreXml, match="4 caratteri, massimo 3"):
        an("ABCD", massimo=3)


def test_an_casi_negativi():
    with pytest.raises(ValoreXml, match="testo mancante"):
        an("")
    with pytest.raises(ValoreXml, match="testo mancante"):
        an("   ")
    with pytest.raises(ValoreXml, match="testo mancante"):
        an(None)
    with pytest.raises(ValoreXml, match="caratteri non ammessi"):
        an("_NOME")


def test_cf_validi_e_invalidi():
    assert cf("RSSMRA80A01H501U") == "RSSMRA80A01H501U"
    assert cf("12345678901") == "12345678901"
    with pytest.raises(ValoreXml, match="codice fiscale non conforme"):
        cf("")
    with pytest.raises(ValoreXml, match="codice fiscale non conforme"):
        cf("INVALIDO")


def test_data_iso_e_data():
    assert data_iso("2025-02-15") == date(2025, 2, 15)
    assert data("2025-02-15") == "15022025"

    # Data inesistente (29 febbraio anno non bisestile)
    with pytest.raises(ValoreXml, match="day 29 must be in range"):
        data_iso("2025-02-29")

    # Formato errato
    with pytest.raises(ValoreXml, match="data attesa AAAA-MM-GG"):
        data_iso("15-02-2025")

    # non_oltre superato
    with pytest.raises(ValoreXml, match="data successiva alla data di riferimento"):
        data("2025-02-15", non_oltre=date(2025, 2, 1))


def test_euro_intero():
    assert euro_intero(100) == "100"
    assert euro_intero("50") == "50"
    assert euro_intero(Decimal("10")) == "10"

    with pytest.raises(ValoreXml, match="il tracciato ammette solo euro interi"):
        euro_intero("10.50")

    with pytest.raises(ValoreXml, match="DatoNP_Type ammette solo interi >= 1"):
        euro_intero("0")

    with pytest.raises(ValoreXml, match="massimo 16 cifre"):
        euro_intero("10000000000000000")


def test_euro_centesimi():
    assert euro_centesimi("10.50") == "10,50"
    assert euro_centesimi(Decimal("0.00")) == "0,00"

    with pytest.raises(V.ValoreNonValido, match="separatore decimale ',' non ammesso"):
        euro_centesimi("10,50")

    with pytest.raises(ValoreXml, match="richiede un importo non negativo con al massimo due decimali"):
        euro_centesimi("10.505")

    with pytest.raises(ValoreXml, match="richiede un importo non negativo con al massimo due decimali"):
        euro_centesimi("-1.00")

    with pytest.raises(ValoreXml, match="massimo 16 caratteri"):
        euro_centesimi("123456789012345.67")


def test_quota_grezza():
    assert quota_grezza("1/2") == (1, 2)
    assert quota_grezza({"num": 100, "den": 100}) == (100, 100)

    with pytest.raises(ValoreXml, match="quota nulla"):
        quota_grezza("0/2")

    with pytest.raises(ValoreXml, match="quota nulla"):
        quota_grezza({"num": 0, "den": 2})

    with pytest.raises(V.ValoreNonValido):
        quota_grezza("abc")


def test_telefono_email_cb():
    assert telefono("0612345678") == "0612345678"
    assert telefono("06 123 456") == "06123456"
    with pytest.raises(ValoreXml, match="DatoTL_Type ammette solo cifre"):
        telefono("")
    with pytest.raises(ValoreXml, match="DatoTL_Type ammette solo cifre"):
        telefono("06abc")

    assert email("test@example.com") == "test@example.com"
    with pytest.raises(ValoreXml, match="indirizzo email non conforme"):
        email("invalido")

    assert cb(True) == "1"
    assert cb(1) == "1"
    assert cb("1") == "1"
    with pytest.raises(ValoreXml, match="casella attesa come true/1"):
        cb(False)
    with pytest.raises(ValoreXml, match="casella attesa come true/1"):
        cb(0)
