"""Conversione dei valori del modello interno nei tipi semplici degli XSD SUC13.

Fonti dei formati (tutte in ``fonti/Specifiche tecniche/SUC13_20250702``):
- ``common/xsd/typesDati_v2.xsd``: DatoAN_Type, DatoNP_Type, DatoNU_Type, DatoVP_Type, DatoCF_Type, DatoCB_Type,
  DatoDT_Type, DatoTL_Type, DatoEM_Type (pattern e facet riportati nei commenti delle funzioni);
- ``registro/xsd/typesReg_v2.xsd``: DatoAN2_Type (cognome/nome), Particella_Type;
- Specifiche_SUC13_20250702.pdf, Tabella 3 (p. 11): descrizione dei tipi.

Ogni funzione solleva ``ValoreXml`` con un messaggio leggibile; il chiamante lo trasforma in ``Errore`` con percorso
interno e fonte. Nessun arrotondamento silenzioso: un importo con decimali dove l'XSD ammette solo interi e' rifiutato.
Le uniche trasformazioni applicate sono di forma e documentate: maiuscolo e spazi multipli ridotti (DatoAN richiede
maiuscole), data ISO -> ggmmaaaa, punto decimale -> virgola.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from fractions import Fraction

from .. import valori as V


class ValoreXml(ValueError):
    pass


# typesDati_v2.xsd DatoAN_Type (pattern copiato dall'XSD)
_AN = re.compile(r"""([0-9A-Z\-]|")([0-9A-Z&]|'|\-|\.|,|\s|/|°|\^|\(|\)|À|È|É|Ì|Ò|Ù|Ü|"|\\|\||\+)*""")
# typesReg_v2.xsd DatoAN2_Type
_AN2 = re.compile(r"""([0-9A-Z\-\.',]|")([0-9A-Z&]|'|\-|\.|,|\s|/|°|\^|\(|\)|À|È|É|Ì|Ò|Ù|Ü|"|\\|\||\+)*""")
# typesReg_v2.xsd Particella_Type
_PARTICELLA = re.compile(r"""([0-9A-Z\-\.]|")([0-9A-Z&]|'|\-|\.|,|\s|/|°|\^|\(|\)|À|È|É|Ì|Ò|Ù|Ü|"|\\|\||\+)*""")
# typesDati_v2.xsd DatoCF_Type
_CF = re.compile(r"[0-9]{11}|[A-Z]{6}[0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{3}[A-Z]")
_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_TL = re.compile(r"[0-9]*")  # DatoTL_Type
_EM = re.compile(r"""[a-zA-Z0-9._%\-'"?^~=]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}""")  # DatoEM_Type


def an(valore, massimo: int | None = None, *, tipo: str = "AN") -> str:
    """DatoAN_Type (``tipo='AN'``), DatoAN2_Type (``'AN2'``, cognome/nome) o Particella_Type (``'PART'``)."""
    if not isinstance(valore, str) or not valore.strip():
        raise ValoreXml("testo mancante")
    s = " ".join(valore.split()).upper()
    if massimo is not None and len(s) > massimo:
        raise ValoreXml(f"{len(s)} caratteri, massimo {massimo}")
    patt = {"AN": _AN, "AN2": _AN2, "PART": _PARTICELLA}[tipo]
    if not patt.fullmatch(s):
        raise ValoreXml(f"{s!r} contiene caratteri non ammessi (ammessi: A-Z 0-9 spazio e . , ' - / ° ^ ( ) & + \" | \\ "
                        "e maiuscole accentate À È É Ì Ò Ù Ü; il primo carattere deve essere una lettera o una cifra)")
    return s


def cf(valore) -> str:
    s = valore.strip().upper() if isinstance(valore, str) else ""
    if not _CF.fullmatch(s):
        raise ValoreXml(f"{valore!r}: codice fiscale non conforme a DatoCF_Type (11 cifre oppure 16 caratteri "
                        "nel formato ministeriale)")
    return s


def data_iso(valore) -> date:
    m = _ISO.match(valore) if isinstance(valore, str) else None
    if not m:
        raise ValoreXml(f"{valore!r}: data attesa AAAA-MM-GG")
    try:
        return date(int(m[1]), int(m[2]), int(m[3]))
    except ValueError as e:
        raise ValoreXml(f"{valore!r}: {e}") from None


def data(valore, *, non_oltre: date | None = None) -> str:
    """ISO AAAA-MM-GG -> ggmmaaaa (DatoDT_Type). ``non_oltre``: 'La data indicata non deve essere successiva alla
    data corrente' (documentazione di DatoDT_Type in typesDati_v2.xsd)."""
    d = data_iso(valore)
    if non_oltre is not None and d > non_oltre:
        raise ValoreXml(f"{valore}: data successiva alla data di riferimento {non_oltre.isoformat()} (DatoDT_Type)")
    return f"{d.day:02d}{d.month:02d}{d.year:04d}"


def euro_intero(valore) -> str:
    """DatoNP_Type (pattern ``[1-9]{1}[0-9]*``; 'al massimo 16 cifre', Tabella 3 p. 11).

    Accetta solo importi interi >= 1: un importo con decimali e' rifiutato (le istruzioni chiedono la base imponibile
    'arrotondata all'unita' di euro', Fascicolo I pp. PDF 22, 30, 34, 38: l'arrotondamento spetta a chi determina il
    valore, non all'esportazione)."""
    d = valore if isinstance(valore, Decimal) else V.parse_importo(valore)
    if d != d.to_integral_value():
        raise ValoreXml(f"{d}: il tracciato ammette solo euro interi (DatoNP_Type); indicare il valore gia' "
                        "arrotondato all'unita' di euro come chiedono le istruzioni")
    n = int(d)
    if n < 1:
        raise ValoreXml(f"{n}: DatoNP_Type ammette solo interi >= 1 (un importo nullo non si indica)")
    if len(str(n)) > 16:
        raise ValoreXml(f"{n}: massimo 16 cifre")
    return str(n)


def intero_con_segno(valore: int) -> str:
    """DatoNU_Type: intero non nullo, positivo o negativo, massimo 16 cifre (pattern ``(\\-[1-9]|[1-9])[0-9]*``)."""
    if valore == 0 or len(str(abs(valore))) > 16:
        raise ValoreXml(f"{valore}: DatoNU_Type ammette interi non nulli di al massimo 16 cifre")
    return str(valore)


def euro_centesimi(valore) -> str:
    """DatoVP_Type: pattern ``[0-9]+,[0-9]{2}`` (maxLength 16). Rifiuta importi con piu' di due decimali."""
    d = valore if isinstance(valore, Decimal) else V.parse_importo(valore)
    q = d.quantize(Decimal("0.01"))
    if q != d or d < 0:
        raise ValoreXml(f"{d}: DatoVP_Type richiede un importo non negativo con al massimo due decimali")
    s = f"{q:f}".replace(".", ",")
    if len(s) > 16:
        raise ValoreXml(f"{s}: massimo 16 caratteri (DatoVP_Type)")
    return s


def frazione_a_centesimi(f: Fraction) -> tuple[Decimal, bool]:
    """Valore esatto -> (importo al centesimo, esatto?). Se non e' esatto applica ROUND_HALF_UP.

    POLITICA (scelta implementativa, NON regola fiscale): usata solo per 'Valore quota' (QuotaValore, DatoVP), per il
    quale l'annotazione XSD di QuotaValore ammette uno scostamento della somma dal valore del bene fino all'1% e
    comunque non oltre 100 euro. Vedi docs/regole/dubbio_arrotondamento.md.
    """
    if f < 0:
        raise ValoreXml(f"{f}: importo negativo")
    cent = f * 100  # aritmetica esatta su Fraction, nessun contesto di precisione Decimal coinvolto
    intero, resto = divmod(cent.numerator, cent.denominator)
    if resto == 0:
        return (Decimal(intero) / 100).quantize(Decimal("0.01")), True
    arrot = intero + (1 if Fraction(resto, cent.denominator) >= Fraction(1, 2) else 0)
    return (Decimal(arrot) / 100).quantize(Decimal("0.01")), False


def numeratore_possesso(num: int) -> str:
    """PossessoNumeratore e' DatoVP_Type (due decimali con virgola): il numeratore intero diventa 'n,00'."""
    return euro_centesimi(Decimal(num))


def quota_grezza(q) -> tuple[int, int]:
    """Quota come inserita ({num,den} o 'a/b'), senza ridurla: il modello ammette 100/100, 1000/1000 (Fascicolo I
    p. PDF 24, 'Quota di devoluzione'). Valida con ``valori.parse_quota``."""
    V.parse_quota(q)
    if isinstance(q, dict):
        n, d = q["num"], q["den"]
    else:
        n, d = (int(x) for x in q.split("/"))
    if n == 0:
        raise ValoreXml("quota nulla")
    return n, d


def telefono(valore) -> str:
    s = str(valore).strip().replace(" ", "")
    if not s or not _TL.fullmatch(s):
        raise ValoreXml(f"{valore!r}: DatoTL_Type ammette solo cifre")
    return s


def email(valore) -> str:
    s = str(valore).strip()
    if not _EM.fullmatch(s):
        raise ValoreXml(f"{valore!r}: indirizzo email non conforme a DatoEM_Type")
    return s


def cb(valore) -> str:
    """DatoCB_Type: '1' per casella barrata. Accetta solo True/'1'/1 (le caselle non barrate si omettono)."""
    if valore in (True, 1, "1"):
        return "1"
    raise ValoreXml(f"{valore!r}: casella attesa come true/1 (le caselle non barrate non si indicano)")
