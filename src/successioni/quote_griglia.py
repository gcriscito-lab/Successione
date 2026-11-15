"""Quote in griglia e agevolazioni guidate (layout ripreso dal confronto con DEAS, 15/11/2026).

Griglia delle quote: le stesse righe del quadro «Devoluzioni e quote» (collezione ``devoluzioni``) viste come tabella, una
riga per bene e diritto, una colonna per erede o legatario. La somma di riga e' la somma delle quote degli eredi sullo
stesso diritto del defunto: e' completa a 1/1 (stesso controllo di ``schema.controlli_coerenza``, DEVOLUZIONI_INCOMPLETE
ed ECCEDENTI). Nessun calcolo d'imposta e nessuna regola nuova: si salvano solo righe di devoluzione.

Agevolazioni guidate: scelto un codice fra quelli che l'interfaccia gia' offre (``schema.STRUTTURATI['devoluzioni.
agevolazioni']``), poi i beni e i soggetti, il codice si scrive sulle righe di devoluzione esistenti (opzioni.telematico,
come il pannello della riga). I quadri in cui ciascun codice e' proposto sono quelli che l'esportazione supporta
(``telematico.prima_casa``, ``riduzioni_art25``, ``agevolazioni``): gli altri controlli restano all'esportazione.
"""
from __future__ import annotations

import copy
import re
from fractions import Fraction

from . import brogliaccio as BR
from . import quadri as Q
from . import schema as S
from . import valori as V
from .errori import ConflittoRevisione, DatiNonValidi
from .telematico import supplemento as SUP

MASSIMO_CELLE = 5000
RUOLI_COLONNA = ("erede", "legatario")


def _quadri_per_codice() -> dict[str, tuple[str, ...]]:
    """Quadri in cui l'esportazione supporta ciascun codice (nessuna tabella nuova: si leggono quelle dei moduli).
    P, X, Z: ``prima_casa.py`` tratta solo il quadro EC (docstring del modulo: «quadro EC (fabbricati non tavolari)»)."""
    from .telematico import agevolazioni as AG
    from .telematico import prima_casa as PC
    from .telematico import riduzioni_art25 as RID
    return {**{c: ("EC",) for c in PC.CODICI}, **RID.QUADRI_SUPPORTATI, **AG.QUADRI_SUPPORTATI}


def _testo_quota(v) -> str:
    q = BR._quota(v)
    if q is None:
        if isinstance(v, dict) and "stato" in v:
            return str(v["stato"])
        return "" if v is None else str(v)
    if isinstance(v, dict):
        return f"{v['num']}/{v['den']}"
    if isinstance(v, str):
        return re.sub(r"\s+", "", v)
    return f"{q.numerator}/{q.denominator}"


def _frazione(f: Fraction) -> str:
    return f"{f.numerator}/{f.denominator}"


def _colonne(dati: dict) -> list[dict]:
    usati = {d.get("persona_id") for d in dati.get("devoluzioni", [])}
    return [{"id": p["id"], "nome": BR._nome_persona(p), "ruolo": p.get("ruolo") or "",
             "codice_fiscale": p.get("codice_fiscale") or ""}
            for p in dati.get("persone", [])
            if p.get("ruolo") != "defunto" and (p.get("ruolo") in RUOLI_COLONNA or p["id"] in usati)]


def griglia(dati: dict) -> dict:
    """{'colonne': [...], 'righe': [...], 'fuori_griglia': [...]}: una riga per (bene, diritto), celle per persona."""
    colonne = _colonne(dati)
    ids_col = {c["id"] for c in colonne}
    beni = {b["id"]: b for b in dati.get("beni", [])}
    per_bene: dict[str, list[dict]] = {}
    fuori = []
    for d in dati.get("devoluzioni", []):
        if d.get("bene_id") not in beni:
            fuori.append({"devoluzione_id": d["id"], "motivo": "bene non indicato o inesistente"})
        elif d.get("persona_id") not in ids_col:
            fuori.append({"devoluzione_id": d["id"], "motivo": "soggetto non indicato o inesistente"})
        else:
            per_bene.setdefault(d["bene_id"], []).append(d)
    righe = []
    for b in dati.get("beni", []):
        devs = per_bene.get(b["id"], [])
        diritti: list[str] = []
        for d in devs:
            c = BR.codice_diritto(d.get("diritto"))
            if c not in diritti:
                diritti.append(c)
        if not diritti:
            diritti = [BR.codice_diritto(b.get("diritto"))]
        for dir_ in diritti:
            celle, doppie, somma, non_note = {}, [], Fraction(0), 0
            for d in devs:
                if BR.codice_diritto(d.get("diritto")) != dir_:
                    continue
                pid = d["persona_id"]
                if pid in celle:
                    doppie.append(pid)
                    continue
                q = BR._quota(d.get("quota"))
                if q is None:
                    non_note += 1
                else:
                    somma += q
                celle[pid] = {"quota": _testo_quota(d.get("quota")), "devoluzione_id": d["id"],
                              "agevolazione": SUP.attr(dati, "devoluzioni", d, "agevolazioni")}
            if not celle:
                esito = "vuota"
            elif doppie:
                esito = "righe_doppie"
            elif non_note:
                esito = "da_indicare"
            else:
                esito = "completa" if somma == 1 else "eccedente" if somma > 1 else "incompleta"
            righe.append({"bene_id": b["id"], "quadro": Q.quadro_di("beni", b) or "", "bene": BR._nome_bene(b),
                          "quota_defunto": _testo_quota(b.get("quota_defunto")), "diritto": dir_,
                          "diritto_testo": BR._diritto_breve(dir_) if dir_ else "",
                          "celle": celle, "somma": _frazione(somma), "esito": esito,
                          "manca": _frazione(1 - somma) if esito == "incompleta" else None,
                          "doppie": sorted(set(doppie))})
    return {"colonne": colonne, "righe": righe, "fuori_griglia": fuori}


def _quota_da_salvare(v, i: int):
    """None = togli la riga; altrimenti la quota come {num, den} (numeri scritti dall'utente, senza semplificare)."""
    if v is None or (isinstance(v, str) and v.strip() in ("", "0", "0/1")) or v == 0:
        return None
    try:
        f = V.parse_quota(v)
    except V.ValoreNonValido as e:
        raise DatiNonValidi(f"cella {i}: {e}") from None
    if f == 0:
        return None
    if isinstance(v, dict):
        return {"num": v["num"], "den": v["den"]}
    n, d = (int(x) for x in v.split("/"))
    return {"num": n, "den": d}


class QuoteGrigliaMixin:
    def quote_griglia(self, pratica_id: str) -> dict:
        p = self.leggi(pratica_id)
        return {"revisione": p["revisione"], **griglia(p["dati"])}

    def quote_salva(self, pratica_id: str, revisione_attesa: int, celle: list, *, chiave: str | None = None,
                    autore: str = "utente", canale: str = "gui") -> dict:
        """Scrive le celle della griglia: {bene_id, persona_id, diritto, quota}. Quota vuota o 0 toglie la riga di
        devoluzione; una cella nuova crea la riga; una cella uguale non cambia nulla. Una sola revisione per tutte."""
        if not isinstance(celle, list) or not celle:
            raise DatiNonValidi("'celle' deve essere una lista non vuota di {bene_id, persona_id, diritto, quota}")
        if len(celle) > MASSIMO_CELLE:
            raise DatiNonValidi(f"al massimo {MASSIMO_CELLE} celle per salvataggio")
        dati = self.leggi(pratica_id)["dati"]
        beni = {b["id"] for b in dati.get("beni", [])}
        persone = {p["id"]: p for p in dati.get("persone", [])}
        devs = dati.get("devoluzioni", [])
        ops, viste = [], set()
        for i, c in enumerate(celle):
            if not isinstance(c, dict):
                raise DatiNonValidi(f"cella {i}: attesa un oggetto {{bene_id, persona_id, diritto, quota}}")
            bid, pid = c.get("bene_id"), c.get("persona_id")
            if bid not in beni:
                raise DatiNonValidi(f"cella {i}: bene inesistente", bene_id=bid)
            if pid not in persone or persone[pid].get("ruolo") == "defunto":
                raise DatiNonValidi(f"cella {i}: soggetto inesistente o defunto", persona_id=pid)
            dir_ = BR.codice_diritto(c.get("diritto"))
            if not dir_:
                raise DatiNonValidi(f"cella {i}: diritto mancante (es. 1 per la proprieta')")
            k = (bid, pid, dir_)
            if k in viste:
                raise DatiNonValidi(f"cella {i}: la stessa cella (bene, soggetto, diritto) compare due volte")
            viste.add(k)
            quota = _quota_da_salvare(c.get("quota"), i)
            trovate = [d for d in devs if d.get("bene_id") == bid and d.get("persona_id") == pid
                       and BR.codice_diritto(d.get("diritto")) == dir_]
            if len(trovate) > 1:
                raise DatiNonValidi(f"cella {i}: nel quadro DV ci sono {len(trovate)} righe per lo stesso bene, soggetto e "
                                    "diritto; correggile li' prima di usare la griglia",
                                    devoluzioni=[d["id"] for d in trovate])
            if trovate:
                d = trovate[0]
                if quota is None:
                    ops.append({"op": "remove", "coll": "devoluzioni", "id": d["id"]})
                elif BR._quota(d.get("quota")) != Fraction(quota["num"], quota["den"]):
                    ops.append({"op": "upsert", "coll": "devoluzioni", "id": d["id"], "campi": {"quota": quota}})
            elif quota is not None:
                ops.append({"op": "upsert", "coll": "devoluzioni",
                            "campi": {"bene_id": bid, "persona_id": pid, "diritto": dir_, "quota": quota}})
        if not ops:
            p = self.leggi(pratica_id)
            if p["revisione"] != revisione_attesa:
                raise ConflittoRevisione("revisione obsoleta", revisione_corrente=p["revisione"])
            return {"revisione": p["revisione"], "modifiche": 0, "griglia": griglia(p["dati"])}
        r = self.aggiorna(pratica_id, revisione_attesa, ops, chiave=chiave, autore=autore, canale=canale)
        return {**r, "modifiche": len(ops), "griglia": griglia(self.leggi(pratica_id)["dati"])}

    def agevolazioni_guidate(self, pratica_id: str) -> dict:
        """Dati per la procedura guidata: codici con i quadri in cui sono proposti, beni con i beneficiari (righe di
        devoluzione) e il codice gia' indicato su ciascuna riga."""
        p = self.leggi(pratica_id)
        dati = p["dati"]
        quadri = _quadri_per_codice()
        sd = S.STRUTTURATI["devoluzioni.agevolazioni"]
        codici = [{"valore": o["valore"], "etichetta": o["etichetta"], "aiuto": o["aiuto"],
                   "quadri": list(quadri.get(o["valore"], ()))} for o in sd["opzioni"]]
        persone = {x["id"]: x for x in dati.get("persone", [])}
        beni = []
        for b in dati.get("beni", []):
            benef = [{"persona_id": d.get("persona_id"), "nome": BR._nome_persona(persone.get(d.get("persona_id"))),
                      "devoluzione_id": d["id"], "diritto": BR.codice_diritto(d.get("diritto")),
                      "quota": _testo_quota(d.get("quota")),
                      "agevolazione": SUP.attr(dati, "devoluzioni", d, "agevolazioni")}
                     for d in dati.get("devoluzioni", []) if d.get("bene_id") == b["id"]]
            beni.append({"bene_id": b["id"], "quadro": Q.quadro_di("beni", b) or "", "bene": BR._nome_bene(b),
                         "beneficiari": benef})
        return {"revisione": p["revisione"], "codici": codici, "beni": beni, "colonne": _colonne(dati)}

    def agevolazione_applica(self, pratica_id: str, revisione_attesa: int, codice: str | None, beni: list,
                             persone: list, *, chiave: str | None = None, autore: str = "utente",
                             canale: str = "gui") -> dict:
        """Scrive (o toglie, con codice vuoto) l'agevolazione sulle righe di devoluzione dei beni e dei soggetti scelti.
        Le coppie bene-soggetto senza riga di devoluzione non si creano: tornano in 'senza_devoluzione'."""
        dati = self.leggi(pratica_id)["dati"]
        cod = str(codice or "").strip().upper() or None
        ammessi = [o["valore"] for o in S.STRUTTURATI["devoluzioni.agevolazioni"]["opzioni"]]
        if cod is not None and cod not in ammessi:
            raise DatiNonValidi("codice di agevolazione non proposto dal programma", ammessi=ammessi)
        if not isinstance(beni, list) or not beni or not isinstance(persone, list) or not persone:
            raise DatiNonValidi("scegli almeno un bene e un soggetto")
        per_id = {b["id"]: b for b in dati.get("beni", [])}
        ids_p = {x["id"] for x in dati.get("persone", []) if x.get("ruolo") != "defunto"}
        if set(beni) - set(per_id):
            raise DatiNonValidi("beni inesistenti", beni=sorted(set(beni) - set(per_id)))
        if set(persone) - ids_p:
            raise DatiNonValidi("soggetti inesistenti", persone=sorted(set(persone) - ids_p))
        if cod is not None:
            quadri = _quadri_per_codice().get(cod, ())
            fuori = [b for b in beni if Q.quadro_di("beni", per_id[b]) not in quadri]
            if fuori:
                raise DatiNonValidi(f"il codice {cod} e' proposto solo nei quadri {', '.join(quadri)}", beni=fuori,
                                    quadri=list(quadri))
        righe = [d for d in dati.get("devoluzioni", []) if d.get("bene_id") in beni and d.get("persona_id") in persone]
        coperte = {(d["bene_id"], d["persona_id"]) for d in righe}
        senza = [{"bene_id": b, "persona_id": x} for b in beni for x in persone if (b, x) not in coperte]
        if not righe:
            raise DatiNonValidi("nessuna riga di devoluzione per i beni e i soggetti scelti: assegna prima le quote",
                                senza_devoluzione=senza)
        tel = copy.deepcopy((dati.get("opzioni") or {}).get("telematico") or {})
        sup = tel.setdefault("devoluzioni", {})
        cambiate = 0
        for d in righe:
            ent = sup.setdefault(d["id"], {})
            prima = ent.get("agevolazioni")
            if cod is None:
                ent.pop("agevolazioni", None)
            else:
                ent["agevolazioni"] = cod
            cambiate += ent.get("agevolazioni") != prima
            if not ent:
                del sup[d["id"]]
        if not sup:
            del tel["devoluzioni"]
        base = {"applicate": len(righe), "cambiate": cambiate, "senza_devoluzione": senza}
        if not cambiate:
            return {"revisione": self.leggi(pratica_id)["revisione"], **base}
        r = self.aggiorna(pratica_id, revisione_attesa, [{"op": "set", "sezione": "opzioni", "campi": {"telematico": tel}}],
                          chiave=chiave, autore=autore, canale=canale)
        return {**r, **base}
