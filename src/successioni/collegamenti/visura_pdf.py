"""Lettore del PDF delle «Risultanze catastali» di Entratel (ricerca per soggetto, una provincia, fabbricati o terreni), salvato
dal browser con «Stampa > Salva come PDF». Converte la tabella nel formato interno di ``collegamenti.catasto``
(``successioni.catasto.v1``), che poi propone gli immobili alla pratica senza scrivere nulla da solo.

Impaginazione osservata il 14/11/2026 su due PDF del 06/11/2026 (fabbricati e terreni) forniti dal
professionista e letti solo in locale: testata con data, provincia, tipo soggetto, codice fiscale e catasto, poi una tabella
le cui intestazioni sono centrate sulle colonne. Il testo estratto da solo perde le colonne vuote (sezione, subalterno), per
questo ogni frammento si assegna alla colonna dalla sua posizione orizzontale (centro del frammento contro centro
dell'intestazione) e ogni riga si ricostruisce attorno al numero di foglio.

Nessun valore viene inventato: un dato non leggibile resta vuoto e la riga e' segnalata. Il codice catastale del comune si
ricava dal nome solo con le tabelle del componente ufficiale configurato (``codice_fiscale.cerca_codice_comune``).
"""
from __future__ import annotations

import io
import re
from fractions import Fraction

from ..errori import DatiNonValidi

FORMATO = "risultanze_entratel_pdf"

# intestazioni delle colonne (testo normalizzato -> chiave), per i due catasti
_COLONNE = {
    "titolarita": "titolarita", "comune": "comune", "foglio": "foglio", "particella": "particella", "sub": "subalterno",
    "indirizzo": "indirizzo", "zona e categoria": "zona_categoria", "classe": "classe", "consistenza": "consistenza",
    "rendita": "rendita", "qualita": "qualita", "ha - are - ca": "superficie", "reddito dominicale": "reddito_dominicale",
    "reddito agrario": "reddito_agrario", "altri dati": "altri_dati",
}
_FINE_TABELLA = ("torna ai soggetti", "i redditi contraddistinti", "nuova ricerca")


def _norm(t: str) -> str:
    t = (t or "").lower().replace("à", "a").replace("'", "").strip()
    return re.sub(r"\s+", " ", t)


def _frammenti(pdf: bytes) -> list[list[tuple[float, float, float, str]]]:
    """Per pagina: (y, x sinistra, x destra stimata, testo). La larghezza e' stimata dal corpo del carattere."""
    from pypdf import PdfReader
    try:
        lettore = PdfReader(io.BytesIO(pdf))
        pagine = []
        for p in lettore.pages:
            out: list[tuple[float, float, float, str]] = []

            def vis(t, cm, tm, fd, fs, out=out):
                s = (t or "").replace("\uf059", "").replace("\uf08e", "")
                if not s.strip():
                    return
                x = cm[4] + tm[4] * cm[0]
                y = cm[5] + tm[5] * cm[3]
                corpo = abs(fs * cm[3]) or abs(fs) or 6.0
                out.append((round(y, 1), x, x + len(s) * corpo * 0.5, s.strip()))
            p.extract_text(visitor_text=vis)
            pagine.append(out)
        return pagine
    except Exception as e:  # PDF danneggiato o cifrato
        raise DatiNonValidi("PDF non leggibile", dettaglio=f"{type(e).__name__}: {e}"[:200]) from None


def _testata(frammenti: list[tuple]) -> dict:
    """Voci della testata «Etichetta: valore» (data, provincia, codice fiscale, catasto, aggiornamento)."""
    righe: dict[float, list[tuple]] = {}
    for f in frammenti:
        righe.setdefault(f[0], []).append(f)
    voci = {}
    for _, fr in righe.items():
        testo = " ".join(t for _, _, _, t in sorted(fr, key=lambda z: z[1]))
        m = re.match(r"^(Data|Provincia|Tipo soggetto|Ult\.\s*Aggiornamento|Codice fiscale|Catasto)\s*:\s*(.+)$", testo)
        if m:
            chiave = {"ult aggiornamento": "ult_aggiornamento", "ult.aggiornamento": "ult_aggiornamento"}.get(
                _norm(m.group(1)), _norm(m.group(1)).replace(" ", "_"))
            voci[chiave] = m.group(2).strip()
    return voci


def _intestazioni(frammenti: list[tuple]) -> tuple[float, list[tuple[str, float]]] | None:
    """(y della riga di intestazione, [(chiave, centro)]). Le intestazioni su due righe («Zona e» / «Categoria») si uniscono."""
    tit = [f for f in frammenti if _norm(f[3]) == "titolarita"]
    if not tit:
        return None
    y0 = tit[0][0]
    vicini = sorted((f for f in frammenti if abs(f[0] - y0) <= 6), key=lambda f: (round((f[1] + f[2]) / 2 / 12), -f[0]))
    gruppi: list[list[tuple]] = []
    for f in sorted(vicini, key=lambda f: (f[1] + f[2]) / 2):
        c = (f[1] + f[2]) / 2
        if gruppi and abs(c - sum((g[1] + g[2]) / 2 for g in gruppi[-1]) / len(gruppi[-1])) < 14 and \
                not any(abs(g[0] - f[0]) < 1 for g in gruppi[-1]):
            gruppi[-1].append(f)
        else:
            gruppi.append([f])
    colonne = []
    for g in gruppi:
        nome = _norm(" ".join(t for _, _, _, t in sorted(g, key=lambda z: -z[0])))
        chiave = _COLONNE.get(nome)
        if chiave:
            colonne.append((chiave, sum((f[1] + f[2]) / 2 for f in g) / len(g)))
    return (y0, colonne) if any(k == "foglio" for k, _ in colonne) else None


def _importo(t: str) -> str | None:
    """«Euro: 1.234,56» -> «1234.56» (formato del modello: punto decimale). None se non e' un importo."""
    m = re.search(r"(\d[\d.]*,\d{1,2}|\d+)", (t or "").replace(" ", ""))
    if not m:
        return None
    return m.group(1).replace(".", "").replace(",", ".")


def _titolarita(t: str) -> tuple[str, dict | None]:
    """«Proprieta' per 55/2000» -> («Proprieta'», {num: 55, den: 2000}); senza quota leggibile la quota e' None."""
    m = re.match(r"^(.*?)\s+per\s+(\d+)\s*/\s*(\d+)\b", t or "")
    if not m:
        return (t or "").strip(), None
    try:
        f = Fraction(int(m.group(2)), int(m.group(3)))
    except ZeroDivisionError:
        return m.group(1).strip(), None
    return m.group(1).strip(), {"num": f.numerator, "den": f.denominator}


def _codice_diritto(testo: str) -> str | None:
    from ..telematico.esporta import codice_enum
    try:
        return codice_enum(testo.replace("'", "").strip(), "CodiciDiritto_Type", alias_descrizione=True)
    except Exception:
        return None


def leggi(pdf: bytes, *, cerca_comune=None) -> dict:
    """Legge il PDF e restituisce ``{"catasto": "F"|"T", "codice_fiscale", "provincia", "data", "aggiornamento",
    "immobili": [formato interno], "segnalazioni": [...], "limiti": [...]}``. Solleva ``DatiNonValidi`` se il PDF non e'
    una pagina di Risultanze catastali riconoscibile. ``cerca_comune(nome, sigla)`` restituisce il codice catastale o None
    (predefinito: tabelle del componente ufficiale)."""
    if not pdf[:5] == b"%PDF-":
        raise DatiNonValidi("il file non e' un PDF")
    if cerca_comune is None:
        cerca_comune = _cerca_comune_ufficiale
    pagine = _frammenti(pdf)
    testata: dict = {}
    for fr in pagine:
        testata = {**_testata(fr), **testata}
    catasto_testo = _norm(testata.get("catasto", ""))
    catasto = "F" if catasto_testo.startswith("fabbricat") else "T" if catasto_testo.startswith("terren") else None
    cf = (testata.get("codice_fiscale") or "").replace(" ", "").upper()
    segnalazioni: list[dict] = []
    immobili: list[dict] = []
    intest = None
    for n_pag, fr in enumerate(pagine, 1):
        trovata = _intestazioni(fr)
        if trovata:
            intest = trovata
        if not intest:
            continue
        y0, colonne = intest if trovata else (max(f[0] for f in fr) + 1, intest[1])
        fine = min((f[0] for f in fr if any(_norm(f[3]).startswith(x) for x in _FINE_TABELLA)), default=-1e9)
        corpo = [f for f in fr if fine < f[0] < y0 - 4 and not re.match(r"^\d\d/\d\d/\d\d, \d\d:\d\d$", f[3])
                 and not f[3].startswith("https://")]
        if not corpo:
            continue

        def colonna(f):
            c = (f[1] + f[2]) / 2
            return min(colonne, key=lambda kc: abs(kc[1] - c))[0]
        assegnati = [(colonna(f), f) for f in corpo]
        ancore = sorted({f[0] for k, f in assegnati if k == "foglio" and re.fullmatch(r"\d+", f[3])}, reverse=True)
        if not ancore:
            continue
        righe: list[dict[str, list[tuple]]] = [{} for _ in ancore]
        for k, f in assegnati:
            i = min(range(len(ancore)), key=lambda j: abs(ancore[j] - f[0]))
            if abs(ancore[i] - f[0]) <= 14:
                righe[i].setdefault(k, []).append(f)
        for i, cel in enumerate(righe, 1):
            def testo(k, cel=cel):
                return " ".join(t for _, _, _, t in sorted(cel.get(k, []), key=lambda z: (-z[0], z[1]))).strip()
            immobili.append(_immobile(catasto, cf, testo, segnalazioni, f"pagina {n_pag}, riga {i}", cerca_comune))
    if intest is None or not catasto:
        raise DatiNonValidi("PDF non riconosciuto: non e' una pagina di «Risultanze catastali» di Entratel (manca la tabella "
                            "con Titolarita', Comune, Foglio o la voce Catasto)")
    limiti = [f"catasto {'fabbricati' if catasto == 'F' else 'terreni'}: risultanze della sola provincia di "
              f"{testata.get('provincia', 'indicata nel PDF')}; gli immobili in altre province vanno cercati a parte"]
    if testata.get("ult_aggiornamento"):
        limiti.append(f"situazione catastale aggiornata al {testata['ult_aggiornamento']}, non alla data del decesso")
    return {"formato": FORMATO, "catasto": catasto, "codice_fiscale": cf, "provincia": testata.get("provincia"),
            "data": testata.get("data"), "aggiornamento": testata.get("ult_aggiornamento"), "immobili": immobili,
            "segnalazioni": segnalazioni, "limiti": limiti}


def _cerca_comune_ufficiale(nome: str, sigla: str | None) -> tuple[str | None, str | None]:
    from ..codice_fiscale import cerca_codice_comune
    r = cerca_codice_comune(nome, sigla)
    if r.get("esito") == "trovato":
        return r.get("codice"), r.get("provincia")
    return None, None


def _immobile(catasto: str, cf: str, testo, segnalazioni: list, dove: str, cerca_comune) -> dict:
    tit = testo("titolarita")
    diritto_testo, quota = _titolarita(tit)
    comune_cella = testo("comune")
    m = re.match(r"^(.*?)\s*Sez\.\s*(.*)$", comune_cella)
    comune, sezione = (m.group(1).strip(), m.group(2).strip()) if m else (comune_cella, "")
    im: dict = {"catasto": catasto, "comune": comune, "foglio": testo("foglio"), "particella": testo("particella")}
    if sezione:
        im["sezione"] = sezione
    if testo("subalterno"):
        im["subalterno"] = testo("subalterno")
    sigla = None
    if catasto == "F":
        ind = testo("indirizzo")
        ms = re.search(r"\(([A-Z]{2})\)", ind)
        sigla = ms.group(1) if ms else None
        if ind:
            im["indirizzo"] = re.sub(r"^\S+\([A-Z]{2}\)\s*", "", ind).strip() or ind
        zc = testo("zona_categoria")
        mz, mc = re.search(r"Zona\s*(\S+?)(?=Cat\.|\s|$)", zc), re.search(r"Cat\.\s*([A-Z]\s*/?\s*\d+)", zc)
        if mz:
            im["zona"] = mz.group(1)
        if mc:
            im["categoria"] = mc.group(1).replace(" ", "")
        if testo("classe"):
            im["classe"] = testo("classe")
        # «18 m» con l'esponente «2» stampato piu' in alto (m²): si cerca il numero seguito dall'unita', non il primo numero
        cons = testo("consistenza")
        mcons = (re.search(r"(\d+(?:,\d+)?)\s*(vani|mq|m2|m²|m)\b", cons)
                 or re.match(r"^(\d+(?:,\d+)?)()$", cons.strip()))
        if mcons:
            im["consistenza"] = mcons.group(1).replace(",", ".")
            if mcons.group(2):
                im["unita_consistenza"] = "vani" if mcons.group(2) == "vani" else "m²"
        r = _importo(testo("rendita"))
        if r:
            im["rendita"] = r
    else:
        for k in ("qualita", "classe", "superficie", "altri_dati"):
            if testo(k):
                im[k] = testo(k)
        rd = testo("reddito_dominicale")
        if _importo(rd):
            im["reddito_dominicale"] = _importo(rd)
            if "*" in rd:
                im["reddito_dominicale_con_deduzioni"] = True
        if _importo(testo("reddito_agrario")):
            im["reddito_agrario"] = _importo(testo("reddito_agrario"))
    codice, prov = cerca_comune(comune, sigla) if comune else (None, None)
    if codice:
        im["codice_comune"] = codice
    if prov or sigla:
        im["provincia"] = prov or sigla
    im["titolarita"] = [{"cf": cf, "quota": quota, "diritto": _codice_diritto(diritto_testo) or diritto_testo,
                         "descrizione": tit}]
    if quota is None:
        segnalazioni.append({"codice": "QUOTA_NON_LETTA", "dove": dove, "messaggio": f"titolarita' «{tit}»: quota non letta"})
    if not (im["foglio"] and im["particella"]):
        segnalazioni.append({"codice": "IDENTIFICATIVI_NON_LETTI", "dove": dove,
                             "messaggio": "foglio o particella non letti: riga da inserire a mano"})
    return im
