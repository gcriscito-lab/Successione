"""Valore quota dei diritti distinti: usufrutto (08) e nuda proprieta' (02) devoluti su un bene che il defunto aveva in
piena proprieta' (01). Scheda: ``docs/regole/usufrutto.md``.

Fonti (lette il 2026-11-07):
- Fascicolo I p. PDF 24: «se un immobile e' ereditato da due soggetti, per cui il primo riceve l'intero usufrutto e il
  secondo l'intera nuda proprieta', indicare nella quota di devoluzione di ciascuno 1/1»; codici diritto 08 e 02; «Valore
  quota»: se il diritto trasferito e' diverso da quello del defunto il valore segue le regole di valutazione dei diritti.
- Fascicolo I p. PDF 25 (esempio 2025): usufrutto = valore x quota possesso x quota devoluzione x tasso legale (2,5%) x
  coefficiente per eta'; nuda proprieta' = valore x quota possesso x quota devoluzione - valore dell'usufrutto.
- D.Lgs. 1 agosto 2025 n. 123 (GU n. 186 del 12-8-2025, S.O. n. 29): art. 99 c. 1 lett. b-c (usufrutto: annualita' =
  piena proprieta' x saggio legale, valutata con l'art. 102); art. 102 c. 1 lett. c e c. 3 (coefficiente dell'allegato 4 in
  base all'eta'; saggio non inferiore al 2,5%); allegato 4 «Prospetto dei coefficienti», esteso alle successioni dal
  D.Lgs. 139/2024 art. 1 c. 1 lett. fff.

Ambito: decessi dal 2025-01-01 (prospetto esteso alle successioni dal D.Lgs. 139/2024, che ha effetto dal 2025). Per il
2026 il saggio del 2,5% vale se il tasso legale non lo supera (art. 102 c. 3): il decreto 2026 non e' stato letto e il
programma lo segnala. Il diritto di abitazione (codice 3) usa SAGGIO e coefficienti da diritto_abitazione.py. Uso, enfiteusi, usufrutto a termine o congiunto: non gestiti.
"""
from __future__ import annotations

from datetime import date
from fractions import Fraction

SAGGIO = Fraction(25, 1000)          # 2,5% (art. 102 c. 3; Fascicolo I p. PDF 25 per il 2025)
DECORRENZA = date(2025, 1, 1)
VERIFICATO_FINO = date(2025, 12, 31)  # tasso legale 2025 letto nel Fascicolo I; il 2026 va verificato
DIRITTO_PIENA = "1"
USUFRUTTO = "8"
NUDA = "2"
#: allegato 4 al D.Lgs. 123/2025: (eta' minima, eta' massima, coefficiente)
PROSPETTO = ((0, 20, 38), (21, 30, 36), (31, 40, 34), (41, 45, 32), (46, 50, 30), (51, 53, 28), (54, 56, 26),
             (57, 60, 24), (61, 63, 22), (64, 66, 20), (67, 69, 18), (70, 72, 16), (73, 75, 14), (76, 78, 12),
             (79, 82, 10), (83, 86, 8), (87, 92, 6), (93, 99, 4))
FONTE = ("D.Lgs. 123/2025 artt. 99 c. 1 lett. c e 102 c. 1 lett. c e c. 3, allegato 4 (GU 12-8-2025 S.O. 29); "
         "Succ_FASCICOLO_I_Nov_23.pdf pp. PDF 24-25")


def supportato(dir_defunto: str | None, dir_devoluto: str) -> bool:
    return dir_defunto == DIRITTO_PIENA and dir_devoluto in (USUFRUTTO, NUDA)


def eta(nascita: date, al: date) -> int:
    return al.year - nascita.year - ((al.month, al.day) < (nascita.month, nascita.day))


def coefficiente(anni: int) -> int | None:
    for lo, hi, c in PROSPETTO:
        if lo <= anni <= hi:
            return c
    return None      # oltre 99 anni il prospetto non da' un coefficiente


def valori(valore: int, righe: list[dict]) -> dict:
    """``righe``: [{"id", "diritto", "quota": Fraction, "coefficiente": int|None}]. Restituisce {"valori": {id: Fraction},
    "errori": [str]} con usufrutto = valore x quota x saggio x coefficiente e nuda proprieta' = valore x quota meno la
    parte proporzionale dell'usufrutto che la grava; le righe in piena proprieta' restano valore x quota."""
    err = []
    p = sum((r["quota"] for r in righe if r["diritto"] == DIRITTO_PIENA), Fraction(0))
    u = sum((r["quota"] for r in righe if r["diritto"] == USUFRUTTO), Fraction(0))
    n = sum((r["quota"] for r in righe if r["diritto"] == NUDA), Fraction(0))
    if p + u != 1 or p + n != 1:
        err.append(f"con usufrutto e nuda proprieta' le quote devono coprire il bene per ogni diritto: piena proprieta' "
                   f"{p} + usufrutto {u} e piena proprieta' {p} + nuda proprieta' {n} devono valere 1 (Fascicolo I p. PDF 24)")
        return {"valori": {}, "errori": err}
    out = {}
    tot_usu = Fraction(0)
    for r in righe:
        if r["diritto"] == USUFRUTTO:
            if r["coefficiente"] is None:
                err.append(f"{r['id']}: coefficiente dell'usufrutto non determinabile (eta' dell'usufruttuario)")
                continue
            out[r["id"]] = Fraction(valore) * r["quota"] * SAGGIO * r["coefficiente"]
            tot_usu += out[r["id"]]
        elif r["diritto"] == DIRITTO_PIENA:
            out[r["id"]] = Fraction(valore) * r["quota"]
    if err:
        return {"valori": {}, "errori": err}
    for r in righe:
        if r["diritto"] == NUDA:
            out[r["id"]] = Fraction(valore) * r["quota"] - tot_usu * (r["quota"] / n)
    return {"valori": out, "errori": err}
