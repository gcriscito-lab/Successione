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
import re
from datetime import date

from .telematico.identificativi import carattere_controllo

NOMI = ("ALFA", "BETA", "GAMMA", "DELTA", "EPSILON", "ZETA", "ETA", "TETA", "IOTA", "KAPPA", "LAMBDA", "MU", "NU", "XI",
        "OMICRON", "PI", "RO", "SIGMA", "TAU", "UPSILON", "FI", "CHI", "PSI", "OMEGA")
COGNOME = "PERSONA"
COMUNE_NASCITA = ("ROMA", "RM", "H501")
#: chiavi tolte ovunque compaiano (dati di contatto e pagamento)
TOGLI = {"pec", "iban"}
#: chiavi sostituite con un valore di fantasia (restano compilate, cosi' la copia si puo' ancora generare e controllare)
SOSTITUISCI = {"indirizzo": "VIA DI FANTASIA 1", "localita_estero": "LOCALITA'", "stato_federato": "STATO",
               "comune_decesso": COMUNE_NASCITA[0], "provincia_decesso": COMUNE_NASCITA[1],
               "telefono": "0600000000", "email": "anonimo@example.com", "estremi_documento": "OMESSI",
               "certificatore_disabilita": "OMESSO", "numero_immatricolazione": "OMESSO", "numero_iscrizione": "1",
               "marca_modello": "OMESSO", "inventario": "OMESSO",
               # testi liberi ed estremi di atti: possono contenere nomi di notai, parti, enti, numeri di repertorio
               "provenienza": "OMESSA", "denominazione": "ENTE ANONIMO",
               "rinuncia_estremi": "OMESSI", "estremi_trascrizione": "OMESSI", "estremi_registrazione": "OMESSI",
               "pubblico_ufficiale": "PUBBLICO UFFICIALE", "numero_registrazione": "1", "sottonumero_registrazione": "1",
               "corpo_tavolare": "1", "porzione_materiale": "1", "particella_denominatore": "1",
               "prima_volume": "1", "prima_numero": "1", "azienda_camera_commercio": "OMESSA"}
#: campi di testo delle entita' che restano come sono: codici, scelte da elenco, dati catastali non identificativi.
#: Ogni campo di testo dello schema e del supplemento deve stare qui, in SOSTITUISCI/TOGLI o in GESTITI (lo verifica un test).
CONSERVATI = {
    "persone": {"sesso", "ruolo", "relazione_con_defunto", "tipo_soggetto", "grado_parentela", "rappresentato_grado", "rinuncia", "residenza_estera",
                "portatore_handicap"},
    "beni": {"tipo", "comune", "sezione", "categoria", "diritto", "bene_estero", "codice_stato_estero", "stato_estero",
             "provincia", "codice_comune", "comune_amministrativo", "codice_comune_amministrativo", "natura",
             "tipologia_terreno", "classe", "zona_censuaria", "consistenza", "tipo_cespite", "tipo_titolo", "quantita",
             "codice_titolo", "codice_fiscale_emittente", "valore_esente", "tipo_documento", "anno_costruzione", "nazionalita",
             "anno_immatricolazione", "tipo_unita", "sigla_ufficio_iscrizione", "anno_iscrizione", "lunghezza", "stazza",
             "comune_catastale", "codice_comune_catastale", "sistema_tavolare", "discordanza_intestatario",
             "passaggi_senza_atti_legali", "rendita_proposta", "bene_aziendale", "diritto_abitazione", "superficie",
             "valore_prec_succ", "imposta_estera", "graffati", "immobili_aziendali", "reddito_dominicale"},
    "devoluzioni": {"diritto", "agevolazioni", "riduzioni"},
    "passivita": {"tipo", "possesso", "ripartizione", "bene_id", "data_documento"},
    "documenti_ref": {"allegato_id", "tipo_eg", "finalita"},
}
#: campi trattati a parte in anonimizza_dati (nomi, codici fiscali, luogo di nascita, descrizioni, dati catastali)
GESTITI = {
    "persone": {"cognome", "nome", "codice_fiscale", "luogo_nascita", "provincia_nascita", "rappresentato_cf"},
    "beni": {"descrizione", "foglio", "particella", "subalterno", "partita_tavolare"},
    "devoluzioni": set(),
    "passivita": {"descrizione"},
    "documenti_ref": set(),
}
# Il codice dell'emittente dei titoli identifica una societa' (di solito quotata), non una persona: resta, cosi' la copia
# si genera ancora. Un codice di persona fisica che compaia in qualunque altro testo viene comunque sostituito.
_CF_PERSONA = re.compile(r"(?<![A-Z0-9])[A-Z]{6}[0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{3}[A-Z](?![A-Z0-9])")


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


def _sostituisci_testo(x: str, mappa: dict, nomi: re.Pattern | None) -> str:
    """Valore intero gia' noto; poi nomi e codici fiscali anche dentro testi piu' lunghi («atto notaio ... a favore di ROSSI»)."""
    if x in mappa:
        return mappa[x]
    if nomi is not None:
        x = nomi.sub(lambda m: mappa.get(m.group(0).upper(), "OMESSO"), x)
    nuovi = set(mappa.values())      # codici gia' di fantasia: restano

    def cf(m):
        v = m.group(0)
        return v if v in nuovi else mappa.setdefault(v, codice_fiscale("ANONIMO", "ANONIMO", v))
    return _CF_PERSONA.sub(cf, x)


def _sostituisci_valori(x, mappa: dict, nomi: re.Pattern | None = None):
    """Sostituisce ricorsivamente i valori di testo e applica TOGLI/SOSTITUISCI alle chiavi."""
    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            if k in TOGLI:
                continue
            if k in SOSTITUISCI and isinstance(v, str):
                out[k] = SOSTITUISCI[k] if v else v
                continue
            out[k] = _sostituisci_valori(v, mappa, nomi)
        return out
    if isinstance(x, list):
        return [_sostituisci_valori(v, mappa, nomi) for v in x]
    if isinstance(x, str):
        return _sostituisci_testo(x, mappa, nomi)
    return x


def _espressione_nomi(mappa: dict) -> re.Pattern | None:
    """Trova i nomi originali (almeno 3 caratteri) come parole intere, senza badare alle maiuscole."""
    parole = sorted({k for k in mappa if len(k) >= 3 and not _CF_PERSONA.fullmatch(k)}, key=len, reverse=True)
    if not parole:
        return None
    return re.compile(r"(?<!\w)(?:" + "|".join(re.escape(p) for p in parole) + r")(?!\w)", re.IGNORECASE)


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
            if isinstance(p.get(k), str) and p[k].strip():
                mappa.setdefault(p[k].strip().upper(), COGNOME if k == "cognome" else nome)
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
    # denominazioni di enti e societa', sull'entita' o nel supplemento (opzioni.telematico.persone.<id>)
    supp = ((opz.get("telematico") or {}).get("persone") or {})
    for x in [*persone, *(v for v in supp.values() if isinstance(v, dict))]:
        if isinstance(x.get("denominazione"), str) and x["denominazione"].strip():
            mappa.setdefault(x["denominazione"].strip().upper(), "ENTE ANONIMO")
    nomi = _espressione_nomi(mappa)
    d["opzioni"] = _sostituisci_valori(opz, mappa, nomi)
    for coll in ("persone", "beni", "devoluzioni", "passivita"):
        d[coll] = _sostituisci_valori(d.get(coll, []), mappa, nomi)
    if d.get("note"):
        fatto.append("note e appunti tolti")
    d["note"] = {}
    fatto.append("telefono, posta elettronica, estremi di atti e documenti, provenienza e denominazioni di fantasia; "
                 "nomi e codici fiscali sostituiti anche dentro i testi; IBAN tolto; restano date, importi, quote e categorie")
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
