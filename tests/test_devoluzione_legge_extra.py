import pytest
from fractions import Fraction
from successioni.telematico.devoluzione_legge import quote_di_legge, descrivi


# caratterizzazione: caso vuoto (gradi assente) -> None
def test_quote_vuoto_gradi():
    assert quote_di_legge({}, {"A": "1"}) is None


# caratterizzazione: chiavi non corrispondenti tra gradi e tipi -> None
def test_quote_chiavi_non_corrispondenti():
    gradi = {"A": "01"}
    tipi = {"B": "1"}
    assert quote_di_legge(gradi, tipi) is None


# caratterizzazione: tipi soggetto misti (non tutti '1' né tutti '3') -> None
def test_quote_tipi_misti():
    gradi = {"A": "01"}
    tipi = {"A": "2"}
    assert quote_di_legge(gradi, tipi) is None


# caratterizzazione: più di un coniuge -> None
def test_quote_piu_coniugi():
    gradi = {"A": "01", "B": "01"}
    tipi = {"A": "1", "B": "1"}
    assert quote_di_legge(gradi, tipi) is None


# caratterizzazione: coniuge + figlio ma chiave extra non riconosciuta -> None
def test_quote_extra_id_non_coperto():
    gradi = {"A": "01", "B": "02", "C": "03"}
    tipi = {"A": "1", "B": "1", "C": "1"}
    assert quote_di_legge(gradi, tipi) is None


# caratterizzazione: solo coniuge (grado 01) -> quota intera al coniuge
def test_quote_solo_coniuge():
    gradi = {"M": "01"}
    tipi = {"M": "1"}
    result = quote_di_legge(gradi, tipi)
    assert result == {"M": Fraction(1)}


# caratterizzazione: solo un figlio (grado 02) -> quota intera al figlio
def test_quote_solo_figlio_unico():
    gradi = {"F": "02"}
    tipi = {"F": "1"}
    result = quote_di_legge(gradi, tipi)
    assert result == {"F": Fraction(1)}


# caratterizzazione: più figli senza coniuge -> quote uguali 1/len(figli)
def test_quote_solo_figli_multipli():
    gradi = {"F1": "02", "F2": "02", "F3": "02"}
    tipi = {"F1": "1", "F2": "1", "F3": "1"}
    result = quote_di_legge(gradi, tipi)
    expected = {"F1": Fraction(1, 3), "F2": Fraction(1, 3), "F3": Fraction(1, 3)}
    assert result == expected


# caratterizzazione: coniuge + un figlio -> 1/2 ciascuno
def test_quote_coniuge_un_figlio():
    gradi = {"C": "01", "F": "02"}
    tipi = {"C": "1", "F": "1"}
    result = quote_di_legge(gradi, tipi)
    assert result == {"C": Fraction(1, 2), "F": Fraction(1, 2)}


# caratterizzazione: coniuge + due figli -> coniuge 1/3, ogni figlio 1/3
def test_quote_coniuge_due_figli():
    gradi = {"C": "01", "F1": "02", "F2": "02"}
    tipi = {"C": "1", "F1": "1", "F2": "1"}
    result = quote_di_legge(gradi, tipi)
    expected = {"C": Fraction(1, 3), "F1": Fraction(1, 3), "F2": Fraction(1, 3)}
    assert result == expected


# caratterizzazione: coniuge + tre figli -> coniuge 1/3, ogni figlio 2/9
def test_quote_coniuge_tre_figli():
    gradi = {"C": "01", "F1": "02", "F2": "02", "F3": "02"}
    tipi = {"C": "1", "F1": "1", "F2": "1", "F3": "1"}
    result = quote_di_legge(gradi, tipi)
    expected = {
        "C": Fraction(1, 3),
        "F1": Fraction(2, 9),
        "F2": Fraction(2, 9),
        "F3": Fraction(2, 9),
    }
    assert result == expected


# caratterizzazione: descrivi con un solo soggetto
def test_descrivi_unico():
    quote = {"A": Fraction(1, 2)}
    assert descrivi(quote) == "A 1/2"


# caratterizzazione: descrivi con più soggetti, ordinati alfabeticamente
def test_descrivi_multipli_ordinati():
    quote = {"B": Fraction(1, 3), "A": Fraction(2, 3)}
    assert descrivi(quote) == "A 2/3, B 1/3"


# caratterizzazione: descrivi con dizionario vuoto -> stringa vuota
def test_descrivi_vuoto():
    assert descrivi({}) == ""


# caratterizzazione: tipi soggetto tutti '3' (chiamati) -> comportamento identico a '1'
def test_quote_tipi_tutti_chiamati():
    gradi = {"C": "01", "F": "02"}
    tipi = {"C": "3", "F": "3"}
    result = quote_di_legge(gradi, tipi)
    assert result == {"C": Fraction(1, 2), "F": Fraction(1, 2)}


# genitore unico: senza discendenti ne' fratelli succede il genitore che sopravvive (Allegato 5, p. 69); un grado fuori
# dalle tabelle (nonno del coniuge) resta non coperto
def test_quote_genitore_unico_e_grado_non_coperto():
    assert quote_di_legge({"A": "03"}, {"A": "1"}) == {"A": Fraction(1)}
    assert quote_di_legge({"A": "14"}, {"A": "1"}) is None
