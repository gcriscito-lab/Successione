"""Copia anonima della pratica (versione 0.4): per studio, formazione o per chiedere un parere senza far circolare dati personali.

Crea una NUOVA pratica; l'originale non viene toccata. Si sostituiscono o si tolgono i dati che identificano persone e immobili:

- persone: cognome «PERSONA», nome in sequenza (ALFA, BETA, ...), codice fiscale ricostruito da questi nomi con il carattere di
  controllo corretto (stessi caratteri di data di nascita e sesso, comune di nascita H501), luogo di nascita ROMA (RM);
  lo stesso codice viene sostituito ovunque compaia (rappresentato, titolare del conto, presentatore);
- immobili: indirizzo, foglio, particella, subalterno e partita tavolare sostituiti con valori di fantasia; descrizioni dei beni
  generiche;
- di fantasia: telefono, posta elettronica, estremi di documenti, verbali e immatricolazioni (cosi' la copia resta generabile);
- tolti: IBAN, PEC, profilo del fornitore, note e appunti, documenti del quadro EG (gli allegati non vengono copiati).

Restano date, importi, quote, gradi di parentela, categorie e rendite: servono a ripetere i calcoli. La data di nascita e il
comune dell'immobile possono ancora concorrere a identificare qualcuno: la copia va trattata come dato riservato.
"""
from __future__ import annotations

import copy
from datetime import date

from .telematico.identificativi import carattere_controllo

NOMI = ("ALFA", "BETA", "GAMMA", "DELTA", "EPSILON", "ZETA", "ETA", "TETA", "IOTA", "KAPPA", "LAMBDA", "MU", "NU", "XI",
        "OMICRON", "PI", "RO", "SIGMA", "TAU", "UPSILON", "FI", "CHI", "PSI", "OMEGA")
COGNOME = "PERSONA"
COMUNE_NASCITA = ("ROMA", "RM", "H501")
#: chiavi tolte ovunque compaiano (dati di contatto e pagamento, estremi di documenti)
TOGLI = {"pec", "iban"}
#: chiavi sostituite con un valore di fantasia (restano compilate, cosi' la copia si puo' ancora generare e controllare)
SOSTITUISCI = {"indirizzo": "VIA DI FANTASIA 1", "localita_estero": "LOCALITA'", "stato_federato": "STATO",
               "comune_decesso": COMUNE_NASCITA[0], "provincia_decesso": COMUNE_NASCITA[1],
               "telefono": "0600000000", "email": "anonimo@example.com", "estremi_documento": "OMESSI",
               "certificatore_disabilita": "OMESSO", "numero_immatricolazione": "OMESSO", "numero_iscrizione": "1",
               "marca_modello": "OMESSO", "inventario": "OMESSO"}


def _lettere(s: str) -> tuple[str, str]:
    s = "".join(c for c in s.upper() if c.isalpha())
    return "".join(c for c in s if c not in "AEIOU"), "".join(c for c in s if c in "AEIOU")


def _parte_cognome(s: str) -> str:
    c, v = _lettere(s)
    return (c + v + "XXX")[:3]


def _parte_nome(s: str) -> str:
    c, v = _lettere(s)
    if len(c) >= 4:
        return c[0] + c[2] + c[3]
    return (c + v + "XXX")[:3]


def codice_fiscale(cognome: str, nome: str, originale: str | None) -> str:
    """Codice di fantasia con controllo corretto; data e sesso dall'originale (servono a eta' e usufrutto), se valido."""
    mezzo = originale[6:11] if originale and len(originale) == 16 else "70A01"
    primi = _parte_cognome(cognome) + _parte_nome(nome) + mezzo + COMUNE_NASCITA[2]
    return primi + carattere_controllo(primi)


def _sostituisci_valori(x, mappa: dict):
    """Sostituisce ricorsivamente i valori di testo presenti in `mappa` e applica TOGLI/SOSTITUISCI alle chiavi."""
    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            if k in TOGLI:
                continue
            if k in SOSTITUISCI and isinstance(v, str):
                out[k] = SOSTITUISCI[k]
                continue
            out[k] = _sostituisci_valori(v, mappa)
        return out
    if isinstance(x, list):
        return [_sostituisci_valori(v, mappa) for v in x]
    if isinstance(x, str) and x in mappa:
        return mappa[x]
    return x


def anonimizza_dati(dati: dict) -> tuple[dict, list[str]]:
    """Dati anonimi e un elenco in parole di cio' che e' stato cambiato."""
    d = copy.deepcopy(dati)
    mappa: dict[str, str] = {}
    fatto = []
    persone = d.get("persone", [])
    for i, p in enumerate(persone):
        nome = NOMI[i % len(NOMI)] + ("" if i < len(NOMI) else str(i // len(NOMI)))
        cf_orig = p.get("codice_fiscale") if isinstance(p.get("codice_fiscale"), str) else None
        for k in ("cognome", "nome"):
            if isinstance(p.get(k), str) and p[k]:
                mappa.setdefault(p[k], COGNOME if k == "cognome" else nome)
        p["cognome"], p["nome"] = COGNOME, nome
        if cf_orig:
            nuovo = codice_fiscale(COGNOME, nome, cf_orig)
            mappa[cf_orig] = nuovo
            p["codice_fiscale"] = nuovo
        if p.get("luogo_nascita"):
            p["luogo_nascita"] = COMUNE_NASCITA[0]
        if p.get("provincia_nascita"):
            p["provincia_nascita"] = COMUNE_NASCITA[1]
    if persone:
        fatto.append(f"{len(persone)} persone: cognome, nome, codice fiscale e luogo di nascita di fantasia")
    for p in persone:   # codici di rappresentati non presenti fra le persone
        r = p.get("rappresentato_cf")
        if isinstance(r, str) and r and r not in mappa:
            mappa[r] = codice_fiscale("RAPPRESENTATO", "ANONIMO", r)
    beni = d.get("beni", [])
    for n, b in enumerate(beni, 1):
        if b.get("descrizione"):
            b["descrizione"] = f"Bene {n}"
        if b.get("foglio"):
            b["foglio"] = str(n)
        if b.get("particella"):
            b["particella"] = str(100 + n)
        if b.get("subalterno"):
            b["subalterno"] = "1"
        if b.get("partita_tavolare"):
            b["partita_tavolare"] = str(1000 + n)
        if isinstance(b.get("graffati"), list):
            for g in b["graffati"]:
                if isinstance(g, dict):
                    for k, val in (("foglio", str(n)), ("particella", str(500 + n)), ("subalterno", "2")):
                        if g.get(k):
                            g[k] = val
    if beni:
        fatto.append(f"{len(beni)} beni: descrizione (anche delle passivita'), indirizzo, foglio, particella, subalterno e partita tavolare di fantasia")
    for n, ps in enumerate(d.get("passivita", []), 1):
        if ps.get("descrizione"):
            ps["descrizione"] = f"Passivita' {n}"
    if d.get("documenti_ref"):
        fatto.append(f"{len(d['documenti_ref'])} documenti del quadro EG tolti (gli allegati non vengono copiati)")
    d["documenti_ref"] = []
    opz = d.get("opzioni") or {}
    if opz.pop("fornitore", None) is not None:
        fatto.append("profilo del fornitore tolto")
    d["opzioni"] = _sostituisci_valori(opz, mappa)
    for coll in ("persone", "beni", "devoluzioni", "passivita"):
        d[coll] = _sostituisci_valori(d.get(coll, []), mappa)
    if d.get("note"):
        fatto.append("note e appunti tolti")
    d["note"] = {}
    fatto.append("telefono, posta elettronica ed estremi di documenti di fantasia; IBAN tolto; restano date, importi, quote e categorie")
    return d, fatto


def operazioni(dati: dict) -> list[dict]:
    """Operazioni di creazione (upsert per riga, set per sezione) che riproducono `dati` in una pratica nuova."""
    ops = []
    for coll in ("persone", "beni", "devoluzioni", "passivita", "documenti_ref"):
        for r in dati.get(coll, []):
            ops.append({"op": "upsert", "coll": coll, "id": r["id"],
                        "campi": {k: v for k, v in r.items() if k != "id" and not k.startswith("_")}})
    if dati.get("opzioni"):
        ops.append({"op": "set", "sezione": "opzioni", "campi": dati["opzioni"]})
    return ops


def copia_anonima(sv, pid: str, *, canale: str = "gui", chiave: str | None = None) -> dict:
    p = sv.leggi(pid)
    dati, fatto = anonimizza_dati(p["dati"])
    titolo = f"Copia anonima del {date.today().strftime('%d/%m/%Y')}"
    r = sv.crea_pratica(titolo, canale=canale, chiave=chiave, iniziali=operazioni(dati), _operazione="copia_anonima")
    return {**r, "titolo": titolo, "modifiche": fatto}
