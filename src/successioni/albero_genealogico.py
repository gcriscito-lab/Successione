"""Albero genealogico (quadro EG, rigo EG6 «AlberoGenealogico») generato dai dati della pratica.

Fonti (docs/regole/albero_genealogico.md):
- Fascicolo I (Succ_FASCICOLO_I_Nov_23.pdf) p. PDF 6, «Quali documenti occorrono»: l'albero genealogico deve far risultare
  nome, cognome, luogo e data di nascita del coniuge e dei soggetti beneficiari legati al defunto da vincoli di parentela;
- Fascicolo I p. PDF 49, quadro EG: allegazione obbligatoria dell'albero (rigo EG6), formato PDF/A-1a, PDF/A-1b o TIF/TIFF;
- XSD SUC13 (QuadroEG/AlberoGenealogico, AlberoGenealogicoNum = 1) e tipi GradoParentela_Type / TipoSoggetto_Type per le
  descrizioni dei codici (lette dagli XSD, non scritte qui).

Il documento e' una rappresentazione dei dati inseriti: non aggiunge parentele, date o luoghi. Dove un dato manca lo scrive
(«non indicato nella pratica») e lo elenca fra i dati da completare. Va controllato dal professionista prima dell'invio.

Il PDF si crea con reportlab, si converte in PDF/A con lo stesso percorso degli altri allegati (``prepara_pdfa``) e si collega
all'unico rigo EG6. Un albero caricato a mano non viene mai scollegato senza ``sostituisci_manuale`` e non viene mai cancellato
(resta fra i file della pratica); gli alberi generati in precedenza, non piu' usati, si eliminano perche' rigenerabili.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
from datetime import date
from pathlib import Path

from . import pdfa
from . import valori as V
from .errori import DatiNonValidi

TIPO_EG = "AlberoGenealogico"
FINALITA = "Albero genealogico generato dai dati"
NOME_FILE = "albero_genealogico.pdf"
MARCATORE = "albero_genealogico"
FONTI = ["Fascicolo I (Nov. 2023) p. PDF 6, «Quali documenti occorrono»",
         "Fascicolo I p. PDF 49, quadro EG, rigo EG6",
         "XSD SUC13: QuadroEG/AlberoGenealogico; GradoParentela_Type, TipoSoggetto_Type"]
NON_INDICATO = "non indicato nella pratica"

# Rami dell'albero per codice del grado di parentela (GradoParentela_Type). Il raggruppamento e' solo di presentazione.
DISCENDENTI = ("02", "04", "06", "08")
ASCENDENTI = ("03", "5A", "5B", "7A", "7B", "9A", "9B")
COLLATERALI = ("10", "11", "15", "15A", "16", "20", "21", "22", "27", "28", "29", "30", "31", "32", "33", "34")
AFFINI = ("12", "13", "14", "17", "18", "19", "23", "24", "25", "26")
# gradi di chi succede per rappresentazione (annotazione XSD SuccessionePerRappresentazione) e loro rappresentati
GRADI_RAPPRESENTAZIONE = ("04", "06", "08", "15", "20", "27")
RAMI = [("discendenti", "Discendenti"), ("ascendenti", "Ascendenti"), ("collaterali", "Fratelli, sorelle e altri collaterali"),
        ("affini", "Affini (parenti del coniuge)"), ("altri", "Altri beneficiari")]


# ----------------------------------------------------------------------------------------------------------- lettura dati
def _val(dati: dict, p: dict, campo: str):
    """Valore del campo della persona (anche da opzioni.telematico.persone[id]); None se assente o da confermare."""
    from .telematico import supplemento as SUP
    v = SUP.attr(dati, "persone", p, campo)
    if V.e_stato(v) or v in ("", None):
        return None
    return v


def _testo(dati, p, campo) -> str | None:
    v = _val(dati, p, campo)
    return str(v).strip() if v is not None and str(v).strip() else None


def _data_it(iso: str | None) -> str | None:
    if not iso:
        return None
    try:
        a, m, g = str(iso)[:10].split("-")
        return f"{g}/{m}/{a}"
    except ValueError:
        return str(iso)


def _codice_grado(v) -> str | None:
    if v in (None, ""):
        return None
    s = str(v).strip().upper()
    return s.zfill(2) if s.isdigit() and len(s) == 1 else s


def etichette_codici(tipo_xsd: str) -> dict[str, str]:
    """Descrizioni ufficiali dei codici dagli XSD; {} senza fonti (si mostra allora solo il codice)."""
    from . import codici
    return {x["valore"]: x["etichetta"] for x in codici.voci(tipo_xsd)}


def _ramo(grado: str | None, rapp_grado: str | None) -> str:
    if grado == "01":
        return "coniuge"
    if grado in DISCENDENTI or (grado in GRADI_RAPPRESENTAZIONE and rapp_grado == "02"):
        return "discendenti"
    if grado in ASCENDENTI:
        return "ascendenti"
    if grado in COLLATERALI:
        return "collaterali"
    if grado in AFFINI:
        return "affini"
    return "altri"


def _nodo(dati: dict, p: dict, gradi: dict, tipi: dict, *, beneficiario: bool = True) -> dict:
    sesso = _testo(dati, p, "sesso")
    denominazione = _testo(dati, p, "denominazione")
    grado = _codice_grado(_val(dati, p, "grado_parentela"))
    tipo = _testo(dati, p, "tipo_soggetto")
    rinuncia = _val(dati, p, "rinuncia") is True or tipo == "4"
    n = {"id": p.get("id"), "cognome": _testo(dati, p, "cognome"), "nome": _testo(dati, p, "nome"),
         "denominazione": denominazione, "codice_fiscale": _testo(dati, p, "codice_fiscale"), "sesso": sesso,
         "luogo_nascita": _testo(dati, p, "luogo_nascita"), "provincia_nascita": _testo(dati, p, "provincia_nascita"),
         "data_nascita": _testo(dati, p, "data_nascita"), "data_decesso": _testo(dati, p, "data_decesso"),
         "grado": grado, "grado_descrizione": gradi.get(grado) if grado else None,
         "relazione": _testo(dati, p, "relazione_con_defunto"), "ruolo": p.get("ruolo"),
         "tipo_soggetto": tipo, "tipo_descrizione": tipi.get(tipo) if tipo else None, "rinunciatario": rinuncia,
         "rappresentato_cf": (_testo(dati, p, "rappresentato_cf") or "").upper() or None,
         "rappresentato_grado": _codice_grado(_val(dati, p, "rappresentato_grado")), "figli": [], "mancanti": []}
    if beneficiario:
        n["qualita"] = _qualita(n)
        if denominazione and not (n["cognome"] or n["nome"]):
            pass                                   # ente o trust: niente dati di nascita
        else:
            for campo, testo in (("cognome", "cognome"), ("nome", "nome"), ("luogo_nascita", "luogo di nascita"),
                                 ("data_nascita", "data di nascita")):
                if not n[campo]:
                    n["mancanti"].append(testo)
            if not grado and not n["relazione"]:
                n["mancanti"].append("grado di parentela")
    return n


def _qualita(n: dict) -> str:
    if n["tipo_soggetto"] == "4":
        return "coniuge superstite rinunciatario/a"
    if n["rinunciatario"]:
        return "rinunciatario/a all'eredita'"
    if n["tipo_soggetto"] == "2" or n["ruolo"] == "legatario":
        return "legatario/a"
    if n["tipo_soggetto"] == "3":
        return "chiamato/a all'eredita'"
    if n["tipo_soggetto"] == "1" or n["ruolo"] == "erede":
        return "erede"
    return n["tipo_descrizione"] or (n["ruolo"] or "beneficiario")


def _e_beneficiario(dati: dict, p: dict) -> bool:
    if p.get("ruolo") in ("erede", "legatario"):
        return True
    return _testo(dati, p, "tipo_soggetto") in ("1", "2", "3", "4", "5", "6") and p.get("ruolo") not in ("defunto", "presentatore")


def _dichiarante(dati: dict) -> dict | None:
    from .telematico import supplemento as SUP
    persone = dati.get("persone") or []
    rif = SUP.presentatore_sup(dati).get("persona_id")
    cand = [p for p in persone if rif and p.get("id") == rif] or [p for p in persone if p.get("ruolo") == "presentatore"]
    if not cand:
        return None
    p = cand[0]
    nome = " ".join(x for x in (_testo(dati, p, "cognome"), _testo(dati, p, "nome")) if x) or _testo(dati, p, "denominazione")
    return {"id": p.get("id"), "nominativo": nome, "codice_fiscale": _testo(dati, p, "codice_fiscale")}


def costruisci(dati: dict, *, oggi: date | None = None) -> dict:
    """Modello dell'albero (dizionario serializzabile) dai dati della pratica. Non scrive nulla."""
    gradi = etichette_codici("GradoParentela_Type")
    tipi = etichette_codici("TipoSoggetto_Type")
    persone = dati.get("persone") or []
    defunti = [p for p in persone if p.get("ruolo") == "defunto"]
    if not defunti:
        raise DatiNonValidi("albero genealogico: manca il defunto fra i soggetti della pratica")
    defunto = _nodo(dati, defunti[0], gradi, tipi, beneficiario=False)
    defunto["mancanti"] = [t for c, t in (("cognome", "cognome"), ("nome", "nome"), ("luogo_nascita", "luogo di nascita"),
                                          ("data_nascita", "data di nascita"), ("data_decesso", "data del decesso"))
                           if not defunto[c]]
    benef = [_nodo(dati, p, gradi, tipi) for p in persone if _e_beneficiario(dati, p)]
    per_cf = {(_testo(dati, p, "codice_fiscale") or "").upper(): p for p in persone if _testo(dati, p, "codice_fiscale")}
    benef_cf = {n["codice_fiscale"].upper(): n for n in benef if n["codice_fiscale"]}
    rami: dict[str, list] = {k: [] for k, _ in RAMI}
    coniugi: list[dict] = []
    rappresentati: dict[str, dict] = {}
    avvisi: list[str] = []
    for n in benef:
        rcf = n["rappresentato_cf"]
        if rcf:
            if rcf in benef_cf and benef_cf[rcf] is not n:
                capo = benef_cf[rcf]                     # rappresentato presente nel quadro EA (es. figlio rinunciatario)
                capo.setdefault("rappresentato", True)
            else:
                capo = rappresentati.get(rcf)
                if capo is None:
                    capo = _nodo_rappresentato(dati, rcf, per_cf.get(rcf), n["rappresentato_grado"], gradi, tipi, defunto)
                    rappresentati[rcf] = capo
                    rami[_ramo(n["rappresentato_grado"], None)].append(capo)
            n["per_rappresentazione_di"] = _nominativo(capo) or rcf
            capo["figli"].append(n)
            continue
        if n["grado"] in GRADI_RAPPRESENTAZIONE and n["grado"] in ("04", "15"):
            avvisi.append(f"{_nominativo(n) or n['id']}: grado {n['grado']} senza il rappresentato (codice fiscale e grado "
                          "del genitore premorto o rinunciatario): indicato senza collegamento al ramo")
        r = _ramo(n["grado"], n["rappresentato_grado"])
        (coniugi if r == "coniuge" else rami[r]).append(n)
    mancanti = []
    for n in [defunto] + _tutti(coniugi) + [x for k in rami for x in _tutti(rami[k])]:
        if n["mancanti"]:
            mancanti.append({"id": n.get("id"), "soggetto": _nominativo(n) or n.get("codice_fiscale") or n.get("id"),
                             "dati": list(n["mancanti"])})
    dich = _dichiarante(dati)
    if not benef:
        avvisi.append("nessun erede o legatario nella pratica: l'albero mostra solo il defunto")
    return {"defunto": defunto, "coniugi": coniugi, "rami": {k: v for k, v in rami.items() if v},
            "mancanti": mancanti, "avvisi": avvisi, "dichiarante": dich,
            "data_redazione": (oggi or date.today()).isoformat(), "fonti": FONTI,
            "codici_disponibili": bool(gradi)}


def _tutti(nodi: list[dict]) -> list[dict]:
    out = []
    for n in nodi:
        out.append(n)
        out += _tutti(n["figli"])
    return out


def _nodo_rappresentato(dati, cf, persona, grado, gradi, tipi, defunto) -> dict:
    """Il rappresentato (premorto o rinunciatario) non e' un soggetto del quadro EA: se la pratica contiene una persona con
    quel codice fiscale se ne usano i dati; altrimenti si mostra solo il codice fiscale."""
    if persona is not None:
        n = _nodo(dati, persona, gradi, tipi, beneficiario=False)
    else:
        n = {"id": None, "cognome": None, "nome": None, "denominazione": None, "codice_fiscale": cf, "sesso": None,
             "luogo_nascita": None, "provincia_nascita": None, "data_nascita": None, "data_decesso": None,
             "relazione": None, "ruolo": None, "rinunciatario": False, "figli": [], "mancanti": []}
    n["grado"] = n.get("grado") or grado
    n["grado_descrizione"] = gradi.get(n["grado"]) if n["grado"] else None
    n["rappresentato"] = True
    n["mancanti"] = []
    if n.get("data_decesso"):
        n["qualita"] = "premorto/a il " + _data_it(n["data_decesso"])
    elif n.get("rinunciatario"):
        n["qualita"] = "rinunciatario/a all'eredita'"
    else:
        n["qualita"] = "premorto/a o rinunciatario/a (non indicato nella pratica)"
    if persona is None:
        n["nota"] = "dati anagrafici del rappresentato non presenti nella pratica (solo il codice fiscale)"
    return n


def _nominativo(n: dict) -> str | None:
    s = " ".join(x for x in (n.get("cognome"), n.get("nome")) if x)
    return s or n.get("denominazione")


def impronta(modello: dict) -> str:
    """Impronta dei soli dati rappresentati (esclusa la data di redazione): dice se l'albero va rigenerato."""
    m = {k: v for k, v in modello.items() if k != "data_redazione"}
    return hashlib.sha256(json.dumps(m, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


# ----------------------------------------------------------------------------------------------------------------- PDF
def _righe_nodo(n: dict, *, defunto: bool = False) -> list[tuple[str, str]]:
    """[(stile, testo)]: 'b' grassetto, 'n' normale, 'm' dato mancante."""
    nome = _nominativo(n)
    out = [("b", nome or ("[cognome e nome " + NON_INDICATO + "]"))]
    if n.get("denominazione") and not (n.get("cognome") or n.get("nome")) and not defunto:
        pass
    else:
        nato = {"M": "nato", "F": "nata"}.get(n.get("sesso") or "", "nato/a")
        luogo = n.get("luogo_nascita")
        if luogo and n.get("provincia_nascita"):
            luogo += f" ({n['provincia_nascita']})"
        data = _data_it(n.get("data_nascita"))
        if luogo or data:
            out.append(("n" if luogo and data else "m", f"{nato} a {luogo or '[luogo ' + NON_INDICATO + ']'} il {data or '[data ' + NON_INDICATO + ']'}"))
        elif not n.get("rappresentato") or n.get("id"):
            out.append(("m", f"luogo e data di nascita: {NON_INDICATO}"))
    if n.get("codice_fiscale"):
        out.append(("n", "codice fiscale " + n["codice_fiscale"]))
    if defunto:
        out.append(("n" if n.get("data_decesso") else "m",
                    "deceduto/a il " + (_data_it(n.get("data_decesso")) or NON_INDICATO)))
        return out
    if n.get("grado"):
        out.append(("n", "grado di parentela: " + n["grado"] + (" - " + n["grado_descrizione"] if n.get("grado_descrizione") else "")))
    elif n.get("relazione"):
        out.append(("n", "relazione con il defunto: " + n["relazione"] + " (codice del grado non indicato)"))
    elif not n.get("rappresentato"):
        out.append(("m", "grado di parentela: " + NON_INDICATO))
    if n.get("qualita"):
        out.append(("n", n["qualita"]))
    if n.get("per_rappresentazione_di"):
        out.append(("n", "succede per rappresentazione di " + n["per_rappresentazione_di"]))
    if n.get("nota"):
        out.append(("m", n["nota"]))
    return out


class _Pagina:
    """Disegno con impaginazione automatica (reportlab, A4 verticale)."""

    def __init__(self, percorso: Path, modello: dict):
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        self.W, self.H = A4
        self.M = 40
        self.c = canvas.Canvas(str(percorso), pagesize=A4)
        self.c.setTitle("Albero genealogico")
        self.c.setSubject("Allegato alla dichiarazione di successione - quadro EG, rigo EG6")
        self.c.setCreator("Successioni - albero genealogico generato dai dati della pratica")
        self.m = modello
        self.pagina = 1
        self.y = self.H - self.M
        self._piede()

    def _piede(self):
        c, m = self.c, self.m
        d = m.get("dichiarante")
        c.setFont("Helvetica", 7.5)
        c.setFillGray(0.3)
        testo = (f"Redatto il {_data_it(m['data_redazione'])} - dichiarante: "
                 + ((d["nominativo"] or NON_INDICATO) + (f" ({d['codice_fiscale']})" if d and d.get("codice_fiscale") else "")
                    if d else NON_INDICATO))
        c.drawString(self.M, 22, testo)
        c.drawRightString(self.W - self.M, 22, f"pagina {self.pagina}")
        c.setFillGray(0)

    def spazio(self, h: float):
        if self.y - h < 40:
            self.c.showPage()
            self.pagina += 1
            self.y = self.H - self.M
            self._piede()
            self.c.setFont("Helvetica-Oblique", 8)
            self.c.drawString(self.M, self.y - 8, "Albero genealogico (segue)")
            self.y -= 20
            return True
        return False

    def testo(self, s: str, font="Helvetica", size=9, dx=0.0, grigio=0.0):
        from reportlab.lib.utils import simpleSplit
        righe = simpleSplit(s, font, size, self.W - 2 * self.M - dx)
        for r in righe:
            self.spazio(size + 3)
            self.c.setFont(font, size)
            self.c.setFillGray(grigio)
            self.c.drawString(self.M + dx, self.y - size, r)
            self.y -= size + 3
        self.c.setFillGray(0)

    def riquadro(self, x: float, righe: list[tuple[str, str]], larghezza: float, *, spesso=False) -> tuple[float, float]:
        """Disegna un riquadro con le righe; restituisce (y alto, y centro della prima riga)."""
        from reportlab.lib.utils import simpleSplit
        fonti = {"b": ("Helvetica-Bold", 9.5), "n": ("Helvetica", 8.5), "m": ("Helvetica-Oblique", 8.5)}
        spezzate = []
        for stile, t in righe:
            f, s = fonti[stile]
            for r in simpleSplit(t, f, s, larghezza - 12):
                spezzate.append((stile, r))
        h = 8 + sum(fonti[st][1] + 2.5 for st, _ in spezzate)
        self.spazio(h + 6)
        c = self.c
        alto = self.y
        c.setLineWidth(1.4 if spesso else 0.7)
        c.rect(x, alto - h, larghezza, h)
        yy = alto - 4
        for st, r in spezzate:
            f, s = fonti[st]
            yy -= s + 1
            c.setFont(f, s)
            c.setFillColorRGB(0.6, 0, 0) if st == "m" else c.setFillGray(0)
            c.drawString(x + 6, yy, r)
            yy -= 1.5
        c.setFillGray(0)
        self.y = alto - h - 6
        return alto, alto - 10

    def chiudi(self):
        self.c.save()


def genera_pdf(modello: dict, percorso: Path | str) -> dict:
    """Scrive il PDF dell'albero; restituisce {pagine}."""
    p = _Pagina(Path(percorso), modello)
    c = p.c
    p.testo("Albero genealogico", "Helvetica-Bold", 16)
    p.testo("Allegato alla dichiarazione di successione - quadro EG, rigo EG6 (Fascicolo I, «Quali documenti occorrono»)",
            "Helvetica", 8.5, grigio=0.3)
    p.y -= 8
    d = modello["defunto"]
    larg = (p.W - 2 * p.M - 30) / 2
    righe_d = [("n", "DEFUNTO/A")] + _righe_nodo(d, defunto=True)
    coniugi = modello["coniugi"]
    if coniugi:
        # defunto e coniuge affiancati, collegati da una doppia linea
        y0 = p.y
        alto, _ = p.riquadro(p.M, righe_d, larg, spesso=True)
        y_fine_d = p.y
        p.y = y0 if alto == y0 else alto
        y_fine_c = y_fine_d
        for k, cg in enumerate(coniugi):
            _, ymid = p.riquadro(p.M + larg + 30, [("n", "CONIUGE / PARTE DELL'UNIONE CIVILE")] + _righe_nodo(cg), larg)
            if k == 0:
                c.setLineWidth(0.8)
                c.line(p.M + larg, ymid, p.M + larg + 30, ymid)
                c.line(p.M + larg, ymid - 3, p.M + larg + 30, ymid - 3)
            y_fine_c = p.y
        p.y = min(y_fine_d, y_fine_c)
    else:
        p.riquadro(p.M, righe_d, larg, spesso=True)
        p.testo("Coniuge: nessun coniuge o parte dell'unione civile fra i soggetti della pratica.", "Helvetica-Oblique", 8.5)
    p.y -= 6
    for chiave, titolo in RAMI:
        nodi = modello["rami"].get(chiave)
        if not nodi:
            continue
        p.spazio(40)
        p.testo(titolo, "Helvetica-Bold", 11)
        p.y -= 2
        _disegna_livello(p, nodi, p.M + 8, 0)
        p.y -= 4
    p.y -= 6
    if modello["mancanti"]:
        p.testo("Dati da completare", "Helvetica-Bold", 10.5)
        for m in modello["mancanti"]:
            p.testo(f"- {m['soggetto']}: " + ", ".join(m["dati"]), "Helvetica", 8.5, dx=6)
    else:
        p.testo("Dati anagrafici richiesti presenti per tutti i soggetti indicati.", "Helvetica", 8.5)
    for a in modello["avvisi"]:
        p.testo("Avviso: " + a, "Helvetica-Oblique", 8.5)
    p.y -= 6
    p.testo("Documento generato dai dati inseriti nella pratica: non aggiunge parentele ne' dati anagrafici. I dati "
            "mancanti sono indicati come tali. Verificare prima dell'invio.", "Helvetica-Oblique", 7.5, grigio=0.3)
    pagine = p.pagina
    p.chiudi()
    return {"pagine": pagine}


def _disegna_livello(p: _Pagina, nodi: list[dict], x: float, livello: int):
    larg = min(330.0, p.W - p.M - x)
    rientro = 26
    for n in nodi:
        alto, ymid = p.riquadro(x, _righe_nodo(n), larg)
        if n["figli"]:
            ax = x + 10
            y_attacco = p.y + 6                         # bordo inferiore del riquadro del genitore
            pagina = p.pagina
            for f in n["figli"]:
                f_alto, f_mid = p.riquadro(x + rientro, _righe_nodo(f), larg)
                if p.pagina != pagina:                   # il figlio e' andato a pagina nuova: il tratto riparte dall'alto
                    y_attacco, pagina = f_alto + 4, p.pagina
                p.c.setLineWidth(0.6)
                p.c.line(ax, y_attacco, ax, f_mid)
                p.c.line(ax, f_mid, x + rientro, f_mid)
                y_attacco = f_mid
                if f["figli"]:
                    _disegna_livello(p, f["figli"], x + 2 * rientro, livello + 2)


# -------------------------------------------------------------------------------------------------------------- servizio
class AlberoGenealogicoMixin:
    """Generazione, collegamento al rigo EG6 e stato dell'albero (unico livello per interfaccia e MCP)."""

    @staticmethod
    def _marcatore(riga) -> dict | None:
        try:
            an = json.loads(riga["analisi"]) if riga["analisi"] else {}
        except (TypeError, ValueError):
            return None
        g = an.get("generato") if isinstance(an, dict) else None
        return g if isinstance(g, dict) and g.get("modulo") == MARCATORE else None

    def _stato_albero(self, pratica_id: str, dati: dict) -> dict:
        righe = {r["id"]: r for r in self._righe_pratica(pratica_id)}
        refs = [r for r in dati.get("documenti_ref", []) if r.get("tipo_eg") == TIPO_EG]
        voci = []
        for r in refs:
            a = righe.get(r.get("allegato_id"))
            m = self._marcatore(a) if a is not None else None
            voci.append({"documento_id": r["id"], "allegato_id": r.get("allegato_id"), "nome": a["nome"] if a else None,
                         "generato": m is not None, "impronta": (m or {}).get("impronta"),
                         "ruolo": a["ruolo"] if a else None, "file_presente": a is not None})
        return {"righi_eg6": voci, "generati_non_usati": [i for i, a in righe.items() if self._marcatore(a)
                                                          and i not in {v["allegato_id"] for v in voci}]}

    def stato_albero_genealogico(self, pratica_id: str) -> dict:
        """Modello dell'albero dai dati correnti e confronto con l'albero collegato al rigo EG6 (sola lettura)."""
        p = self.leggi(pratica_id)
        modello = costruisci(p["dati"])
        imp = impronta(modello)
        st = self._stato_albero(pratica_id, p["dati"])
        gen = [v for v in st["righi_eg6"] if v["generato"]]
        return {"pratica_id": pratica_id, "revisione": p["revisione"], "modello": modello, "impronta": imp,
                "righi_eg6": st["righi_eg6"],
                "aggiornato": bool(gen) and len(st["righi_eg6"]) == 1 and gen[0]["impronta"] == imp,
                "manuale": any(not v["generato"] for v in st["righi_eg6"])}

    def genera_albero_genealogico(self, pratica_id: str, *, sostituisci_manuale: bool = False, forza: bool = False,
                                  canale: str = "gui", autore: str | None = None, oggi: date | None = None) -> dict:
        """Genera il PDF, lo converte in PDF/A (``prepara_pdfa``) e lo collega all'unico rigo EG6.

        - albero caricato a mano gia' collegato: senza ``sostituisci_manuale`` non si fa nulla (esito 'conferma_richiesta');
          con la conferma il rigo passa all'albero generato e il file manuale resta fra i file della pratica (non si cancella);
        - albero generato gia' collegato e dati invariati: nessuna nuova versione ('gia_aggiornato'), salvo ``forza``;
        - alberi generati in precedenza e non piu' collegati: eliminati (si rigenerano dai dati)."""
        autore = autore or ("assistente" if canale == "mcp" else "utente")
        p = self.leggi(pratica_id)
        dati, rev = p["dati"], p["revisione"]
        modello = costruisci(dati, oggi=oggi)
        imp = impronta(modello)
        st = self._stato_albero(pratica_id, dati)
        refs = st["righi_eg6"]
        manuali = [v for v in refs if not v["generato"]]
        if manuali and not sostituisci_manuale:
            return {"pratica_id": pratica_id, "esito": "conferma_richiesta", "generato": False,
                    "manuali": [{"allegato_id": v["allegato_id"], "nome": v["nome"]} for v in manuali],
                    "messaggio": "il rigo EG6 contiene gia' un albero genealogico caricato a mano: confermare la "
                                 "sostituzione (il file caricato resta fra i documenti della pratica)",
                    "mancanti": modello["mancanti"]}
        if (not forza and len(refs) == 1 and refs[0]["generato"] and refs[0]["impronta"] == imp
                and refs[0]["file_presente"]):
            return {"pratica_id": pratica_id, "esito": "gia_aggiornato", "generato": False,
                    "allegato_id": refs[0]["allegato_id"], "revisione": rev, "mancanti": modello["mancanti"],
                    "avvisi": modello["avvisi"]}
        marcatore = {"modulo": MARCATORE, "impronta": imp, "revisione_dati": rev, "data_redazione": modello["data_redazione"]}
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / NOME_FILE
            info = genera_pdf(modello, f)
            analisi = {**pdfa.analizza_pdf(f), "generato": marcatore}
            with self.arch.transazione() as c:
                orig = self._registra(c, pratica_id, NOME_FILE, f, "originale", None, TIPO_EG, FINALITA, None, analisi)
        nuovi = [orig["allegato_id"]]
        try:
            conv = self.prepara_pdfa(orig["allegato_id"], canale=canale)
            usare, avvisi_conv = orig["allegato_id"], list(conv.get("avvisi") or [])
            der = conv.get("derivato")
            if der:
                nuovi.append(der["allegato_id"])
                riga_d = self._riga_allegato(der["allegato_id"])
                an_d = {**(json.loads(riga_d["analisi"]) if riga_d["analisi"] else {}), "generato": marcatore}
                with self.arch.transazione() as c:
                    c.execute("UPDATE allegati SET analisi=?, nome=? WHERE id=?",
                              (json.dumps(an_d), "albero_genealogico_pdfa.pdf", der["allegato_id"]))
                rap = json.loads(riga_d["rapporto"]) if riga_d["rapporto"] else None
                if self.derivato_utilizzabile(rap):
                    usare = der["allegato_id"]
            elif conv.get("esito") != "conforme":
                avvisi_conv.append("PDF/A non creato (" + str(conv.get("esito")) + (": " + str(conv.get("dettaglio"))
                                   if conv.get("dettaglio") else "") + "): il rigo EG6 usa il PDF non convertito, da "
                                   "convertire prima dell'invio")
            if refs:
                primo = next((v for v in refs if v["generato"]), refs[0])
                ops = [{"op": "upsert", "coll": "documenti_ref", "id": primo["documento_id"],
                        "campi": {"allegato_id": usare, "tipo_eg": TIPO_EG, "finalita": FINALITA}}]
                ops += [{"op": "remove", "coll": "documenti_ref", "id": v["documento_id"]} for v in refs
                        if v["documento_id"] != primo["documento_id"]]
            else:
                import uuid
                ops = [{"op": "upsert", "coll": "documenti_ref", "id": "dr_" + uuid.uuid4().hex[:12],
                        "campi": {"allegato_id": usare, "tipo_eg": TIPO_EG, "finalita": FINALITA}}]
            agg = self.aggiorna(pratica_id, rev, ops, autore=autore, canale=canale, origine="calcolato")
        except Exception:
            for i in nuovi:                                # nessun file orfano se il collegamento non riesce
                try:
                    self._cancella_riga(self._riga_allegato(i))
                except Exception:
                    pass
            raise
        eliminati = []
        usati = {r.get("allegato_id") for r in self.leggi(pratica_id)["dati"].get("documenti_ref", [])}
        for r in self._righe_pratica(pratica_id):
            if r["id"] not in usati and self._marcatore(r) is not None:
                self._cancella_riga(r)                     # solo alberi GENERATI non piu' usati: mai un file caricato a mano
                eliminati.append(r["id"])
        val = (self.elenca_allegati_uno(usare) or {}).get("rapporto") or {}
        return {"pratica_id": pratica_id, "esito": "generato", "generato": True, "allegato_id": usare,
                "pdfa": usare != orig["allegato_id"] or conv.get("esito") == "conforme",
                "validazione": (val.get("validazione") or {}).get("esito") if isinstance(val, dict) else None,
                "pagine": info["pagine"], "revisione": agg["revisione"], "impronta": imp,
                "mancanti": modello["mancanti"], "avvisi": modello["avvisi"] + avvisi_conv,
                "manuali_scollegati": [{"allegato_id": v["allegato_id"], "nome": v["nome"]} for v in manuali],
                "eliminati": eliminati, "fonti": FONTI}

    def elenca_allegati_uno(self, allegato_id: str) -> dict | None:
        r = self._riga_allegato(allegato_id)
        return {"id": r["id"], "nome": r["nome"], "rapporto": json.loads(r["rapporto"]) if r["rapporto"] else None}

    def file_allegato(self, allegato_id: str) -> tuple[bytes, dict]:
        """Contenuto di un allegato (per l'anteprima nell'interfaccia) e la sua riga."""
        r = self._riga_allegato(allegato_id)
        f = self.arch.base / r["percorso"]
        if not f.is_file():
            from .errori import NonTrovato
            raise NonTrovato("file dell'allegato assente dal deposito", allegato_id=allegato_id)
        return f.read_bytes(), dict(r)
