"""Valori esatti: importi decimali, quote frazionarie, stato del dato.

Nessun float. Gli importi usano il punto decimale; la virgola viene rifiutata per
evitare ambiguita' di separatore (richiesta del progetto).
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from fractions import Fraction

STATI_DATO = ("assente", "zero", "non_applicabile", "da_confermare")
ORIGINI = ("inserito", "acquisito", "proposto_assistente", "calcolato", "confermato")


class ValoreNonValido(ValueError):
    pass


def e_stato(v) -> bool:
    return isinstance(v, dict) and set(v) == {"stato"} and v["stato"] in STATI_DATO


def parse_importo(v) -> Decimal:
    if isinstance(v, float):
        raise ValoreNonValido("importo float non ammesso: usare stringa decimale con punto")
    s = str(v).strip()
    if "," in s:
        raise ValoreNonValido("separatore decimale ',' non ammesso: usare '.'")
    if not re.fullmatch(r"-?\d+(\.\d+)?", s):
        raise ValoreNonValido(f"importo non valido: {v!r}")
    try:
        return Decimal(s)
    except InvalidOperation as e:  # pragma: no cover
        raise ValoreNonValido(str(e))


def parse_quota(v) -> Fraction:
    """Accetta {"num":int,"den":int} oppure 'a/b'. Il denominatore deve essere > 0."""
    if isinstance(v, dict) and {"num", "den"} <= set(v):
        n, d = v["num"], v["den"]
    elif isinstance(v, str) and re.fullmatch(r"\s*\d+\s*/\s*\d+\s*", v):
        n, d = (int(x) for x in v.split("/"))
    else:
        raise ValoreNonValido(f"quota non valida: {v!r} (usare num/den)")
    if not (isinstance(n, int) and isinstance(d, int)) or isinstance(n, bool) or isinstance(d, bool):
        raise ValoreNonValido("numeratore e denominatore devono essere interi")
    if d <= 0 or n < 0:
        raise ValoreNonValido("denominatore > 0 e numeratore >= 0")
    f = Fraction(n, d)
    if f > 1:
        raise ValoreNonValido("quota maggiore di 1")
    return f


def quota_json(f: Fraction) -> dict:
    return {"num": f.numerator, "den": f.denominator}
