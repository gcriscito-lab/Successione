"""Schema dei dati di pratica e controlli interni di coerenza.

I codici dei diritti/qualifiche sono PROVVISORI: vanno legati alle enumerazioni degli XSD
(fonti/Specifiche tecniche) nel passo di export telematico. Vedi docs/MATRICE_COPERTURA.md.
"""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, asdict
from fractions import Fraction

from . import valori as V

CODICE_FISCALE = re.compile(r"^[A-Z0-9]{16}$")
DATA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")

RUOLI_PERSONA = ("defunto", "erede", "legatario", "rappresentante", "presentatore", "altro")
TIPI_BENE = ("fabbricato", "terreno", "disponibilita_finanziaria", "titolo", "altro")

# kind: str | cf | data | quota | importo | enum:<a|b> | ref:<collezione>
COLLEZIONI: dict[str, dict[str, str]] = {
    "persone": {
        "cognome": "str", "nome": "str", "codice_fiscale": "cf", "data_nascita": "data",
        "luogo_nascita": "str", "ruolo": "enum:" + "|".join(RUOLI_PERSONA),
        "relazione_con_defunto": "str", "data_decesso": "data",
        # Dati richiesti dall'export XML (prima solo in opzioni.telematico): se presenti qui hanno la precedenza.
        "sesso": "enum:M|F", "provincia_nascita": "str", "tipo_soggetto": "str", "grado_parentela": "str",
        "comune_decesso": "str", "provincia_decesso": "str",
    },
    "beni": {
        "tipo": "enum:" + "|".join(TIPI_BENE), "descrizione": "str",
        "comune": "str", "sezione": "str", "foglio": "str", "particella": "str", "subalterno": "str",
        "categoria": "str", "rendita": "importo", "valore": "importo",
        "diritto": "str", "quota_defunto": "quota", "provenienza": "str",
        "provincia": "str", "codice_comune": "str", "comune_amministrativo": "str", "codice_comune_amministrativo": "str",
        "indirizzo": "str", "natura": "str", "tipologia_terreno": "str", "reddito_dominicale": "importo", "classe": "str",
        "zona_censuaria": "str", "consistenza": "str", "tipo_cespite": "str",
        "tipo_titolo": "str", "quantita": "str", "codice_titolo": "str", "codice_fiscale_emittente": "str",
        "tipo_documento": "str", "data_documento": "data",
    },
    "devoluzioni": {
        "bene_id": "ref:beni", "persona_id": "ref:persone", "quota": "quota", "diritto": "str",
    },
    "passivita": {"descrizione": "str", "importo": "importo", "persona_id": "ref:persone",
                  "tipo": "str", "estremi_documento": "str", "data_documento": "data", "possesso": "quota",
                  "bene_id": "ref:beni"},
    "documenti_ref": {"allegato_id": "str", "tipo_eg": "str", "finalita": "str", "persona_id": "ref:persone"},
}
# Aiuti contestuali mostrati nell'interfaccia e restituiti dall'MCP: spiegano campi che si prestano a errori di inserimento.
AIUTI: dict[str, str] = {
    "beni.valore": "Valore in euro interi della QUOTA DEL DEFUNTO (base imponibile), non dell'intero bene. "
                   "Esempio: immobile da 200.000 euro posseduto per 1/2: indicare 100.000. Indicare l'intero valore raddoppia attivo e imposta.",
    "beni.quota_defunto": "Frazione del bene posseduta dal defunto (es. 1/2). Non è la quota dell'erede.",
    "beni.rendita": "Rendita catastale in euro, con il punto decimale (es. 1240.50).",
    "devoluzioni.quota": "Quota dell'erede sul diritto del defunto (es. 1/3). È un dato diverso dalla quota del defunto sul bene.",
    "persone.sesso": "M o F, come richiesto dal file telematico.",
    "persone.grado_parentela": "Codice del grado di parentela con il defunto, come nelle istruzioni del quadro EA (es. 02).",
    "beni.codice_comune": "Codice catastale del comune (4 caratteri, es. H501).",
    "beni.natura": "Natura del terreno secondo le istruzioni del quadro EB (es. T).",
    "persone.codice_fiscale": "16 caratteri. Il carattere di controllo viene verificato in esportazione.",
    "passivita.importo": "Importo in euro, con il punto decimale. Indicare la parte di debito che grava sul defunto.",
}
SEZIONI = {"opzioni": None, "note": None}  # sezioni libere (dict), non esportate se interne


@dataclass
class Errore:
    codice: str
    percorso: str
    messaggio: str
    fonte: str = "controllo interno"

    def asdict(self):
        return asdict(self)


def valida_campo(kind: str, valore, percorso: str, riferimenti: dict[str, set[str]]) -> list[Errore]:
    if V.e_stato(valore):
        return []
    try:
        if kind == "str":
            if not isinstance(valore, str):
                raise V.ValoreNonValido("atteso testo")
        elif kind == "cf":
            if not (isinstance(valore, str) and CODICE_FISCALE.match(valore.upper())):
                raise V.ValoreNonValido("codice fiscale di 16 caratteri alfanumerici")
        elif kind == "data":
            if not (isinstance(valore, str) and DATA_ISO.match(valore)):
                raise V.ValoreNonValido("data in formato AAAA-MM-GG")
            try:
                datetime.date.fromisoformat(valore)
            except ValueError:
                raise V.ValoreNonValido("data inesistente nel calendario")
        elif kind == "quota":
            V.parse_quota(valore)
        elif kind == "importo":
            V.parse_importo(valore)
        elif kind.startswith("enum:"):
            if valore not in kind[5:].split("|"):
                raise V.ValoreNonValido("valore ammesso: " + ", ".join(kind[5:].split("|")))
        elif kind.startswith("ref:"):
            if valore not in riferimenti.get(kind[4:], set()):
                raise V.ValoreNonValido(f"riferimento inesistente in {kind[4:]}")
    except V.ValoreNonValido as e:
        return [Errore("VALORE_NON_VALIDO", percorso, str(e))]
    return []


def valida_forma(dati: dict) -> list[Errore]:
    """Validazione strutturale (usata a ogni scrittura): campi noti, tipi, riferimenti."""
    err: list[Errore] = []
    rif = {c: {e["id"] for e in dati.get(c, [])} for c in COLLEZIONI}
    for coll, campi in COLLEZIONI.items():
        for e in dati.get(coll, []):
            base = f"{coll}[{e['id']}]"
            for k, v in e.items():
                if k in ("id", "_origine"):
                    continue
                if k not in campi:
                    err.append(Errore("CAMPO_SCONOSCIUTO", f"{base}.{k}", "campo non previsto dallo schema"))
                    continue
                err += valida_campo(campi[k], v, f"{base}.{k}", rif)
    return err


def controlli_coerenza(dati: dict) -> list[Errore]:
    """Controlli di merito interni (non sono il controllo ufficiale dell'Agenzia)."""
    err: list[Errore] = []
    persone = dati.get("persone", [])
    if sum(1 for p in persone if p.get("ruolo") == "defunto") != 1:
        err.append(Errore("DEFUNTO_NON_UNICO", "persone", "serve esattamente un soggetto con ruolo 'defunto'"))
    for p in persone:
        if not p.get("codice_fiscale"):
            err.append(Errore("CF_MANCANTE", f"persone[{p['id']}].codice_fiscale", "dato mancante"))
    # somma delle devoluzioni per (bene, diritto) <= 1: quote del defunto e devoluzioni sono dati distinti
    somme: dict[tuple[str, str], Fraction] = {}
    for d in dati.get("devoluzioni", []):
        try:
            q = V.parse_quota(d["quota"])
        except (KeyError, V.ValoreNonValido):
            continue
        k = (d.get("bene_id", ""), d.get("diritto", ""))
        somme[k] = somme.get(k, Fraction(0)) + q
    for (bene, diritto), s in somme.items():
        if s > 1:
            err.append(Errore("DEVOLUZIONI_ECCEDENTI", f"devoluzioni[bene={bene},diritto={diritto}]",
                              f"somma quote {s.numerator}/{s.denominator} > 1"))
        elif s < 1:
            err.append(Errore("DEVOLUZIONI_INCOMPLETE", f"devoluzioni[bene={bene},diritto={diritto}]",
                              f"somma quote {s.numerator}/{s.denominator} < 1 (da confermare)"))
    for b in dati.get("beni", []):
        if b.get("tipo") in ("fabbricato", "terreno") and not (b.get("foglio") and b.get("particella")):
            err.append(Errore("IDENTIFICATIVI_CATASTALI_INCOMPLETI", f"beni[{b['id']}]", "foglio/particella mancanti"))
    return err
