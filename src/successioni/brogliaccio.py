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
from decimal import Decimal, InvalidOperation
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


#: colonne d'importo che nella stampa si leggono in euro all'italiana (126.000 / 1.000,50); il CSV resta con i valori inseriti
IMPORTI_STAMPA = {"rendita", "reddito_dominicale", "valore"}


def _importo_it(v: str) -> str:
    """«126000» -> «126.000», «1000.5» -> «1.000,50». Un testo che non e' un numero resta com'e'."""
    m = re.fullmatch(r"(-?)(\d+)(?:\.(\d{1,2}))?", (v or "").strip())
    if not m:
        return v
    intero = f"{int(m.group(2)):,}".replace(",", ".")
    return m.group(1) + intero + ("," + m.group(3).ljust(2, "0") if m.group(3) else "")


def _diritto_leggibile(v: str) -> str:
    """«1» o «proprieta» -> «1 - Proprieta'» (descrizione delle tabelle ufficiali dei codici); un valore non riconosciuto resta."""
    cod = codice_diritto(v)
    if not cod:
        return v
    from . import codici as C
    for tipo in ("CodiciDiritto_Type", "CodiciDirittoImmobili_Type", "CodiciDirittoNonImmobili"):
        try:
            voce = next((x for x in C.voci(tipo) if x["valore"] == cod), None)
        except Exception:
            voce = None
        if voce:
            return f"{cod} - {voce['etichetta']}"
    return v


def _per_stampa(righe_t: list[dict]) -> list[dict]:
    out = []
    for x in righe_t:
        y = dict(x)
        for c in IMPORTI_STAMPA & y.keys():
            y[c] = _importo_it(str(y[c]))
        if y.get("diritto"):
            y["diritto"] = _diritto_leggibile(str(y["diritto"]))
        out.append(y)
    return out


#: colonne della tabella dei beni nella stampa: (chiave, intestazione breve, nome intero nel suggerimento, numerica)
COLONNE_STAMPA = [("descrizione", "Bene", "Descrizione o indirizzo del bene", False),
                  ("comune", "Comune", "Comune (provincia) e codice comune", False),
                  ("sezione", "Sez.", "Sezione", False), ("foglio", "Fg.", "Foglio", False), ("particella", "Part.", "Particella", False),
                  ("subalterno", "Sub.", "Subalterno", False), ("categoria", "Cat.", "Categoria", False), ("classe", "Cl.", "Classe", False),
                  ("consistenza", "Cons.", "Consistenza", True),
                  ("rendita", "Rendita / R.D.", "Rendita catastale o reddito dominicale", True),
                  ("diritto", "Diritto", "Diritto del defunto", False), ("quota_defunto", "Quota", "Quota del defunto", True),
                  ("valore", "Valore", "Valore dichiarato (euro)", True), ("data_visura", "Visura", "Data della visura catastale", False)]


def _decimale(v: str):
    try:
        return Decimal(str(v).strip())
    except (InvalidOperation, ValueError):
        return None


def _data_it(v: str) -> str:
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", (v or "").strip())
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if m else (v or "")


def _numero_it(v: str) -> str:
    """«5.50» -> «5,50»: numero con la virgola decimale (consistenza); un testo che non e' un numero resta com'e'."""
    return v.replace(".", ",") if re.fullmatch(r"\d+\.\d+", (v or "").strip()) else (v or "")


def _diritto_breve(v: str) -> str:
    """Descrizione del diritto senza codice e con gli accenti: «1» -> «Proprietà»."""
    from . import carta_intestata as CI
    return CI.accenti(_diritto_leggibile(v).split(" - ", 1)[-1]) if v else ""


def html(dati: dict, *, titolo: str, revisione: int | None = None, studio: dict | str | None = None, oggi=None) -> str:
    """Pagina stampabile su carta intestata, A4 orizzontale (Stampa > Salva come PDF dal browser). Stessi dati di ``righe``:
    nessun calcolo d'imposta; i totali per quadro sono la somma dei valori inseriti, solo da leggere."""
    from . import carta_intestata as CI
    from .quadri import PER_ID
    e = escape
    st = studio if isinstance(studio, dict) else {"nome": studio or ""}
    r = righe(dati)
    n_col = len(COLONNE_STAMPA)

    # --- beni, raggruppati per quadro, con il totale dei valori inseriti
    gruppi: dict[str, list[tuple[dict, dict]]] = {}
    for riga, b in zip(r["beni"], dati.get("beni", [])):
        gruppi.setdefault(riga["quadro"] or "", []).append((riga, b))
    th = "".join(f'<th{" class=n" if num else ""} title="{e(lungo)}">{e(breve)}</th>' for _, breve, lungo, num in COLONNE_STAMPA)
    corpo_beni, totale, parziale = [], Decimal(0), False
    for qd, elenco in gruppi.items():
        nome_q = (PER_ID.get(qd) or {}).get("titolo", "")
        corpo_beni.append(f'<tr class="gruppo"><td colspan="{n_col}">{e(qd)} {e(nome_q)}</td></tr>')
        somma, incompleta = Decimal(0), False
        for riga, b in elenco:
            desc = _testo(_campo(dati, "beni", b, "descrizione")) or _testo(_campo(dati, "beni", b, "indirizzo"))
            if not desc:
                desc = riga["bene"] if not riga.get("foglio") else (riga.get("tipo") or "").capitalize()
            comune = e(riga.get("comune", "")) + (f" ({e(riga['provincia'])})" if riga.get("provincia") else "")
            if riga.get("codice_comune"):
                comune += f'<div class="dett mono">{e(riga["codice_comune"])}</div>'
            celle = {"descrizione": e(desc) or "&nbsp;", "comune": comune,
                     "consistenza": e(_numero_it(riga.get("consistenza", ""))),
                     "rendita": e(_importo_it(riga.get("rendita") or riga.get("reddito_dominicale") or "")),
                     "diritto": e(_diritto_breve(riga.get("diritto", ""))),
                     "valore": e(_importo_it(riga.get("valore", ""))),
                     "data_visura": e(_data_it(riga.get("data_visura", "")))}
            v = _decimale(riga.get("valore", ""))
            if v is None:
                incompleta = True
            else:
                somma += v
            tds = "".join(f'<td{" class=n" if num else ""}>{celle[k] if k in celle else e(str(riga.get(k, "")))}</td>'
                          for k, _, _, num in COLONNE_STAMPA)
            corpo_beni.append(f"<tr>{tds}</tr>")
        nota = " (alcuni valori non indicati)" if incompleta else ""
        corpo_beni.append(f'<tr class="subtot"><td colspan="{n_col - 2}">Totale {e(qd)}{nota}</td>'
                          f'<td class="n">{e(_importo_it(str(somma)))}</td><td></td></tr>')
        totale += somma
        parziale = parziale or incompleta
    if corpo_beni:
        corpo_beni.append(f'<tr class="tot"><td colspan="{n_col - 2}">Totale dei beni'
                          f'{" (alcuni valori non indicati)" if parziale else ""}</td>'
                          f'<td class="n">{e(_importo_it(str(totale)))}</td><td></td></tr>')
    tab_beni = (f'<table class="beni"><thead><tr>{th}</tr></thead><tbody>'
                + ("".join(corpo_beni) or f'<tr><td colspan="{n_col}">Nessun bene.</td></tr>') + "</tbody></table>")

    # --- quote, raggruppate per bene e diritto, con l'esito della somma
    righe_q, prec = [], None
    for q in r["quote"]:
        k = (q["quadro"], q["bene"], codice_diritto(q["diritto"]))
        if k != prec:
            prec = k
            ok = q["esito"] == "completa"
            dir_ = _diritto_breve(q["diritto"]) or "diritto non indicato"
            righe_q.append(f'<tr class="gruppo"><td colspan="2">{e(q["quadro"])} – {e(q["bene"])} – {e(dir_)}</td>'
                           f'<td class="n">somma {e(q["somma_quote_bene_diritto"])}</td>'
                           f'<td><span class="esito {"ok" if ok else "no"}">{e(q["esito"])}</span></td></tr>')
        righe_q.append(f'<tr><td>{e(q["soggetto"])}</td><td class="mono">{e(q["codice_fiscale"])}</td>'
                       f'<td class="n">{e(q["quota"])}</td><td></td></tr>')
    tab_quote = ('<table class="quote"><thead><tr><th>Soggetto</th><th>Codice fiscale</th><th class="n">Quota</th>'
                 '<th>Esito</th></tr></thead><tbody>' + ("".join(righe_q) or '<tr><td colspan="4">Nessuna devoluzione.</td></tr>')
                 + "</tbody></table>")

    # --- soggetti
    righe_s = "".join(f'<tr><td>{e(x["soggetto"])}</td><td class="mono">{e(x["codice_fiscale"])}</td><td>{e(x["ruolo"])}</td>'
                      f'<td class="n">{x["beni"]}</td><td class="dett">{e(CI.accenti(x["dettaglio"]))}</td></tr>'
                      for x in r["soggetti"])
    tab_sogg = ('<table class="sogg"><thead><tr><th>Soggetto</th><th>Codice fiscale</th><th>Ruolo</th><th class="n">Beni</th>'
                '<th>Dettaglio</th></tr></thead><tbody>' + (righe_s or '<tr><td colspan="5">Nessun soggetto.</td></tr>')
                + "</tbody></table>")

    css = (".beni{font-size:12.5px}.beni th,.beni td{padding:5px 6px}.beni td:first-child{width:26%}.beni td:nth-child(2){white-space:nowrap}"
           ".beni tr.subtot td{font-weight:700;color:var(--t2);border-bottom:1px solid var(--inchiostro)}"
           ".quote,.sogg{font-size:13px}.quote td,.sogg td{padding:5px 8px}.quote{width:auto;min-width:60%}.quote td:first-child,.sogg td:first-child{white-space:nowrap}.quote td:nth-child(2){padding-right:32px}"
           ".esito{display:inline-block;padding:0 8px;border-radius:10px;font-size:12px;font-weight:700}"
           ".esito.ok{background:var(--casella);color:var(--verde)}.esito.no{background:#FBECEB;color:var(--rosso)}"
           ".gruppo td{font-size:12.5px}")
    rif = ["Brogliaccio di lavoro", f"del {CI.data_it(oggi)}",
           titolo + (f", revisione {revisione}" if revisione is not None else "")]
    corpo = (f'<h1>{e(titolo)}</h1><p class="sotto">Dati come inseriti nella pratica, senza calcoli d’imposta. Documento di '
             "lavoro dello studio: non sostituisce la dichiarazione.</p>"
             f"<h2>Beni</h2>{tab_beni}<h2>Quote per bene</h2>{tab_quote}<h2>Soggetti</h2>{tab_sogg}")
    return CI.pagina(titolo_finestra=f"Brogliaccio - {titolo}", studio=st, riferimento=rif, corpo=corpo, orizzontale=True,
                     css_extra=css)
