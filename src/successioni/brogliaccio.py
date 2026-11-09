"""Brogliaccio di lavoro: elenco dei beni con dati catastali, diritto, quota e valore, e riepilogo delle quote per bene e per
soggetto (voce 23 di docs/ANALISI_REPLICA_2026-11-07.md).

Legge i dati della pratica cosi' come sono inseriti: nessun calcolo d'imposta e nessuna ripartizione di valori. Le quote
sono sommate solo per mostrare se le devoluzioni di un bene arrivano a 1/1 (lo stesso confronto di
``schema.controlli_coerenza``). E' uno strumento interno dello studio: non sostituisce la dichiarazione ne' il prospetto per
il cliente, che legge il file telematico.
"""
from __future__ import annotations

import csv
import io
import re
from fractions import Fraction
from html import escape

from . import valori as V
from . import quadri as Q
from .telematico import supplemento as SUP

COLONNE_BENI = ["quadro", "bene", "tipo", "provincia", "comune", "codice_comune", "sezione", "foglio", "particella",
                "subalterno", "categoria", "classe", "consistenza", "rendita", "reddito_dominicale", "diritto",
                "quota_defunto", "valore", "data_visura"]
COLONNE_QUOTE = ["quadro", "bene", "soggetto", "codice_fiscale", "diritto", "quota", "somma_quote_bene_diritto", "esito"]


def _testo(v) -> str:
    if v is None:
        return ""
    if isinstance(v, dict):
        if "stato" in v:
            return "[" + str(v["stato"]).replace("_", " ") + "]"
        if "num" in v and "den" in v:
            return f"{v['num']}/{v['den']}"
    return str(v)


def _quota(v) -> Fraction | None:
    try:
        return V.parse_quota(v)
    except (V.ValoreNonValido, TypeError, ValueError, KeyError):
        return None


def _nome_bene(b: dict) -> str:
    parti = [b.get("comune"), b.get("foglio") and f"fg. {b['foglio']}", b.get("particella") and f"p. {b['particella']}",
             b.get("subalterno") and f"sub. {b['subalterno']}", b.get("descrizione")]
    return " ".join(str(x) for x in parti if x) or b["id"]


def _nome_persona(p: dict | None) -> str:
    if not p:
        return "soggetto non indicato"
    return " ".join(str(p.get(k) or "") for k in ("cognome", "nome")).strip() or p["id"]


def _campo(dati: dict, coll: str, ent: dict, campo: str):
    """Valore del campo sull'entita' oppure, se assente, in ``opzioni.telematico`` (provincia, codice comune, classe,
    consistenza...: ``telematico.supplemento.attr``, come l'esportazione e l'albero genealogico)."""
    v = ent.get(campo)
    return v if v is not None else SUP.attr(dati, coll, ent, campo)


def codice_diritto(v) -> str:
    """Codice diritto normalizzato come nell'esportazione (``codice_enum`` con ``alias_descrizione``: '1' e 'proprieta'
    sono lo stesso diritto). Un valore non riconosciuto resta com'e' (lo segnalano i controlli interni)."""
    if v is None or isinstance(v, dict):
        return ""
    from .telematico.esporta import codice_enum
    try:
        return codice_enum(v, "CodiciDiritto_Type", alias_descrizione=True)
    except Exception:
        return str(v).strip()


def righe(dati: dict) -> dict:
    """{'beni': [...], 'quote': [...], 'soggetti': [...]} con valori in testo, pronti per CSV o stampa."""
    persone = {p["id"]: p for p in dati.get("persone", [])}
    beni = []
    for b in dati.get("beni", []):
        r = {c: _testo(_campo(dati, "beni", b, c)) for c in COLONNE_BENI if c not in ("quadro", "bene")}
        beni.append({"quadro": Q.quadro_di("beni", b) or "", "bene": _nome_bene(b), **r, "_id": b["id"]})
    nomi_beni = {b["_id"]: (b["quadro"], b["bene"]) for b in beni}
    somme: dict[tuple[str, str], tuple[Fraction, int]] = {}

    def chiave(d):
        return (d.get("bene_id", "") or "", codice_diritto(d.get("diritto")))
    for d in dati.get("devoluzioni", []):
        k = chiave(d)
        s, n = somme.get(k, (Fraction(0), 0))
        q = _quota(d.get("quota"))
        somme[k] = (s + q, n) if q is not None else (s, n + 1)
    quote = []
    ordinate = sorted(dati.get("devoluzioni", []), key=chiave)
    for d in ordinate:
        k = chiave(d)
        s, non_note = somme[k]
        esito = (f"{non_note} {'quota' if non_note == 1 else 'quote'} da indicare" if non_note else "completa" if s == 1 else
                 "supera 1/1" if s > 1 else f"manca {1 - s}")
        p = persone.get(d.get("persona_id"))
        qd, nb = nomi_beni.get(d.get("bene_id"), ("", "bene non indicato"))
        quote.append({"quadro": qd, "bene": nb, "soggetto": _nome_persona(p), "codice_fiscale": _testo((p or {}).get("codice_fiscale")),
                      "diritto": _testo(d.get("diritto")), "quota": _testo(d.get("quota")),
                      "somma_quote_bene_diritto": f"{s.numerator}/{s.denominator}", "esito": esito})
    soggetti = []
    for p in dati.get("persone", []):
        if p.get("ruolo") == "defunto":
            continue
        ricevuti = [q for q, d in zip(quote, ordinate) if d.get("persona_id") == p["id"]]
        soggetti.append({"soggetto": _nome_persona(p), "codice_fiscale": _testo(p.get("codice_fiscale")),
                         "ruolo": _testo(p.get("ruolo")), "beni": len(ricevuti),
                         "dettaglio": "; ".join(f"{r['bene']} {r['quota']} ({r['diritto'] or 'diritto non indicato'})" for r in ricevuti)})
    for b in beni:
        b.pop("_id")
    return {"beni": beni, "quote": quote, "soggetti": soggetti}


#: colonne con importi o numeri, dove un segno meno iniziale seguito da sole cifre e' un numero negativo vero
COLONNE_NUMERICHE = {"rendita", "reddito_dominicale", "valore", "classe", "consistenza", "beni"}
_INIZIO_FORMULA = ("=", "+", "-", "@", "\t", "\r")
_NUMERO = re.compile(r"[+-]?\d+(?:[.,]\d+)*")


def _cella(colonna: str, v) -> str:
    """Testo della cella neutralizzato contro le formule (CSV injection): una cella che inizia con =, +, -, @, tabulazione o
    ritorno a capo e' preceduta da un apostrofo, che Excel mostra come testo. I numeri veri delle colonne numeriche (es.
    -12,50) restano invariati."""
    s = "" if v is None else str(v)
    if s.startswith(_INIZIO_FORMULA) and not (colonna in COLONNE_NUMERICHE and _NUMERO.fullmatch(s)):
        return "'" + s
    return s


def csv_testo(dati: dict) -> str:
    """CSV per Excel in italiano: separatore «;», tre sezioni separate da una riga vuota."""
    r = righe(dati)
    out = io.StringIO()
    w = csv.writer(out, delimiter=";", lineterminator="\r\n")
    for titolo, colonne, dati_sez in (("BENI", COLONNE_BENI, r["beni"]), ("QUOTE PER BENE", COLONNE_QUOTE, r["quote"]),
                                      ("SOGGETTI", ["soggetto", "codice_fiscale", "ruolo", "beni", "dettaglio"], r["soggetti"])):
        w.writerow([titolo])
        w.writerow(colonne)
        for x in dati_sez:
            w.writerow([_cella(c, x.get(c, "")) for c in colonne])
        w.writerow([])
    return "﻿" + out.getvalue()      # BOM: Excel riconosce l'UTF-8 (lettere accentate)


def html(dati: dict, *, titolo: str, revisione: int | None = None) -> str:
    """Pagina stampabile (Stampa > Salva come PDF dal browser)."""
    r = righe(dati)

    def tabella(intest: list[str], righe_t: list[dict]) -> str:
        th = "".join(f"<th>{escape(c.replace('_', ' '))}</th>" for c in intest)
        trs = "".join("<tr>" + "".join(f"<td{' class=n' if c in COLONNE_NUMERICHE else ''}>{escape(str(x.get(c, '')))}</td>"
                                       for c in intest) + "</tr>" for x in righe_t)
        return f"<table><thead><tr>{th}</tr></thead><tbody>{trs or '<tr><td colspan=99>nessuna riga</td></tr>'}</tbody></table>"

    sotto = f" · revisione {revisione}" if revisione is not None else ""
    return ("<!doctype html><html lang=it><head><meta charset=utf-8><title>Brogliaccio · " + escape(titolo) + "</title><style>"
            "body{font:12px/1.4 system-ui,sans-serif;margin:16px;color:#111}h1{font-size:18px}h2{font-size:14px;margin-top:18px}"
            "table{border-collapse:collapse;width:100%}th,td{border:1px solid #999;padding:2px 4px;text-align:left;vertical-align:top}"
            "td.n{text-align:right;font-variant-numeric:tabular-nums}"
            "th{background:#eee}@media print{h2{break-after:avoid}tr{break-inside:avoid}}</style></head><body>"
            f"<h1>Brogliaccio · {escape(titolo)}</h1><p>Documento di lavoro dello studio{escape(sotto)}: dati come inseriti nella "
            "pratica, senza calcoli d'imposta. Non sostituisce la dichiarazione.</p>"
            "<h2>Beni</h2>" + tabella([c for c in COLONNE_BENI if c != "tipo"], r["beni"])
            + "<h2>Quote per bene</h2>" + tabella(COLONNE_QUOTE, r["quote"])
            + "<h2>Soggetti</h2>" + tabella(["soggetto", "codice_fiscale", "ruolo", "beni", "dettaglio"], r["soggetti"])
            + "</body></html>")
