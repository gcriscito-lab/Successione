"""Conversione dei valori del modello interno nei tipi di dato degli XSD (DatoAN, DatoDT, DatoNP, DatoVP, ...).

Ogni funzione solleva ``ValoreXml`` con un messaggio leggibile; il chiamante lo trasforma in ``Errore`` con
percorso interno e fonte. Nessun arrotondamento silenzioso: gli importi con decimali dove l'XSD ammette solo
interi sono rifiutati.
"""
from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction

from .. import valori as V


class ValoreXml(ValueError):
    pass


# pattern copiati da typesDati_v2.xsd (DatoAN_Type) e typesReg_v2.xsd (DatoAN2_Type)
_AN = re.compile(r"""([0-9A-Z\-]|")([0-9A-Z&]|'|\-|\.|,|\s|/|°|\^|\(|\)|À|È|É|Ì|Ò|Ù|Ü|"|\\|\||\+)*""")
_AN2 = re.compile(r"""([0-9A-Z\-\.',]|")([0-9A-Z&]|'|\-|\.|,|\s|/|°|\^|\(|\)|À|È|É|Ì|Ò|Ù|Ü|"|\\|\||\+)*""")
_CF = re.compile(r"[0-9]{11}|[A-Z]{6}[0-9LMNPQRSTUV]{2}[A-Z]{1}[0-9LMNPQRSTUV]{2}[A-Z]{1}[0-9LMNPQRSTUV]{3}[A-Z]{1}")
_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def an(valore, massimo: int, *, nome_proprio: bool = False) -> str:
    """DatoAN_Type (o DatoAN2_Type per cognome/nome): maiuscolo, caratteri ammessi, lunghezza massima."""
    if not isinstance(valore, str) or not valore.strip():
        raise ValoreXml("testo mancante")
    s = " ".join(valore.split()).upper()
    if len(s) > massimo:
        raise ValoreXml(f"{len(s)} caratteri, massimo {massimo}")
    if not (_AN2 if nome_proprio else _AN).fullmatch(s):
        raise ValoreXml(f"{s!r} contiene caratteri non ammessi (ammessi: A-Z 0-9 e . , ' - / ° ^ ( ) & + \" | \\ "
                        "e maiuscole accentate À È É Ì Ò Ù Ü; il primo carattere deve essere alfanumerico)")
    return s


def cf(valore) -> str:
    s = (valore or "").strip().upper() if isinstance(valore, str) else ""
    if not _CF.fullmatch(s):
        raise ValoreXml(f"{valore!r}: codice fiscale non conforme a DatoCF_Type (11 cifre oppure 16 caratteri "
                        "nel formato ministeriale)")
    return s


def data(valore) -> str:
    """ISO AAAA-MM-GG -> ggmmaaaa (DatoDT_Type / DatoDN_Type)."""
    m = _ISO.match(valore) if isinstance(valore, str) else None
    if not m:
        raise ValoreXml(f"{valore!r}: data attesa AAAA-MM-GG")
    from datetime import date
    try:
        date(int(m[1]), int(m[2]), int(m[3]))
    except ValueError as e:
        raise ValoreXml(f"{valore!r}: {e}")
    return f"{m[3]}{m[2]}{m[1]}"


def data_iso(valore: str):
    from datetime import date
    m = _ISO.match(valore)
    return date(int(m[1]), int(m[2]), int(m[3]))


def euro_intero(valore, *, minimo: int = 1, cifre: int = 13) -> str:
    """DatoNP_Type: intero positivo senza zeri iniziali. Rifiuta decimali (nessun arrotondamento silenzioso)."""
    d = V.parse_importo(valore) if not isinstance(valore, Decimal) else valore
    if d != d.to_integral_value():
        raise ValoreXml(f"{d}: l'XSD ammette solo euro interi; indicare la base imponibile gia' arrotondata "
                        "all'unita' di euro (regola di arrotondamento da Fascicolo I, Quadro EB/EC 'Valore')")
    n = int(d)
    if n < minimo:
        raise ValoreXml(f"{n}: DatoNP_Type ammette solo interi >= 1 (un importo nullo si omette)")
    if len(str(n)) > cifre:
        raise ValoreXml(f"{n}: massimo {cifre} cifre")
    return str(n)


def euro_intero_con_segno(valore: Decimal) -> str:
    """DatoNU_Type: intero positivo o negativo, non nullo, max 16 cifre."""
    if valore != valore.to_integral_value() or valore == 0 or len(str(abs(int(valore)))) > 16:
        raise ValoreXml(f"{valore}: DatoNU_Type ammette interi non nulli di al massimo 16 cifre")
    return str(int(valore))


def euro_centesimi(valore) -> str:
    """DatoVP_Type: positivo con due decimali e virgola (es. 1234,50). Quantizza a 0,01 solo se gia' esatto."""
    d = V.parse_importo(valore) if not isinstance(valore, Decimal) else valore
    q = d.quantize(Decimal("0.01"))
    if q != d or d < 0:
        raise ValoreXml(f"{d}: DatoVP_Type richiede un importo non negativo con al massimo due decimali")
    return f"{q:f}".replace(".", ",")


def centesimi_arrotondati(d: Decimal) -> Decimal:
    """POLITICA valore quota: prodotto valore x quota arrotondato al centesimo ROUND_HALF_UP.

    Scelta di implementazione NON fissata dalle fonti (tolleranza ammessa dall'annotazione di QuotaValore:
    1% e comunque <= 100 euro). Vedi docs/regole/dubbio_arrotondamento.md.
    """
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def possesso(quota) -> tuple[str, str]:
    """Quota del defunto {num,den} -> (PossessoNumeratore DatoVP 'n,00', PossessoDenominatore NP max 6 cifre)."""
    f = V.parse_quota(quota)
    if f == 0:
        raise ValoreXml("quota di possesso nulla")
    raw = quota if isinstance(quota, dict) else None
    n, d = (raw["num"], raw["den"]) if raw else (f.numerator, f.denominator)
    if len(str(d)) > 6:
        raise ValoreXml(f"denominatore {d}: massimo 6 cifre (PossessoDenominatore)")
    return f"{n},00", str(d)


def quota_elementi(f: Fraction) -> tuple[str, str]:
    if f == 0:
        raise ValoreXml("quota nulla")
    return str(f.numerator), str(f.denominator)


def cb() -> str:
    return "1"
