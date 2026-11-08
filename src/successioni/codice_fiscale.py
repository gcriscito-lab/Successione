"""Dati ricavabili da un codice fiscale di persona fisica: sesso, data di nascita, luogo (codice catastale, comune, provincia).

Solo struttura del codice (16 caratteri, mese con lettera, giorno +40 per le donne, omocodia sulle cifre) e carattere di controllo,
verificato con l'implementazione del componente ufficiale (`telematico/identificativi.py`). Il nome del comune e la provincia si
leggono, se disponibili, dalle tabelle del componente di controllo SUC13 che l'utente ha configurato (`SUCCESSIONI_CONTROLLI_SUC13`):
non sono copiate nel programma. Senza quel componente restano il codice catastale e un avviso.

Il secolo non e' nel codice fiscale: si deduce (vedi `_anno`) e quando e' ambiguo lo si segnala. I dati ricavati sono un suggerimento
per l'utente, che resta responsabile della verifica.
"""
from __future__ import annotations

import functools
import os
import re
import zipfile
from datetime import date
from pathlib import Path

from .telematico import identificativi as ID

_MESE = {c: i + 1 for i, c in enumerate(ID.MESI)}
_DA_OMOCODIA = {lettera: str(cifra) for cifra, lettera in enumerate("LMNPQRSTUV")}
_POSIZIONI_OMOCODIA = (6, 7, 9, 10, 12, 13, 14)     # 0-based: cifre che l'omocodia puo' sostituire con lettere
_RE_16 = re.compile(r"[A-Z]{6}[0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{3}[A-Z]")
_RISORSE = "it/finanze/entrate/sco/resources/"


def _senza_omocodia(cf: str) -> tuple[str, bool]:
    s = list(cf)
    omocodia = False
    for p in _POSIZIONI_OMOCODIA:
        if not s[p].isdigit():
            s[p] = _DA_OMOCODIA[s[p]]
            omocodia = True
    return "".join(s), omocodia


def _anno(yy: int, mese: int, giorno: int, oggi: date, ruolo: str | None) -> tuple[int, bool]:
    """Secolo dedotto dalle due cifre dell'anno: il piu' recente non nel futuro, ma una persona non ha piu' di 110 anni.
    Ambiguo se entrambe le ipotesi sono plausibili (2000+yy non futuro e 1900+yy con eta' fino a 110 anni): per il defunto si
    sceglie il 1900, per gli altri soggetti il 2000."""
    def non_futuro(a: int) -> bool:
        try:
            return date(a, mese, giorno) <= oggi
        except ValueError:
            return False
    a2000, a1900 = 2000 + yy, 1900 + yy
    ok2000 = non_futuro(a2000)
    ok1900 = (oggi.year - a1900) <= 110
    if ok2000 and ok1900:
        return (a1900 if ruolo == "defunto" else a2000), True
    if ok2000:
        return a2000, False
    return a1900, False


# ---------------------------------------------------------------------------------------- tabelle del componente ufficiale
def _jar() -> Path | None:
    cartella = os.environ.get("SUCCESSIONI_CONTROLLI_SUC13")
    if not cartella:
        return None
    p = Path(cartella) / "controlliXMLREG2013.jar"
    return p if p.is_file() else None


@functools.lru_cache(maxsize=4)
def _comuni(jar: str) -> dict[str, tuple[str, str | None]]:
    """codice catastale -> (nome, provincia). Da `comuni_conservatorie.res` (NOME*CODICE*UFFICIO*PROVINCIA*...) e, per i comuni
    assenti, da `comuni_ccat_13.res` (NOME*CODICE*...) senza provincia."""
    out: dict[str, tuple[str, str | None]] = {}
    with zipfile.ZipFile(jar) as z:
        for nome_file, con_provincia in ((_RISORSE + "comuni_conservatorie.res", True), (_RISORSE + "comuni_ccat_13.res", False)):
            try:
                righe = z.read(nome_file).decode("latin-1").splitlines()
            except KeyError:
                continue
            for r in righe:
                if r.startswith("#") or "*" not in r:
                    continue
                parti = r.split("*")
                if len(parti) < 2 or not re.fullmatch(r"[A-Z][0-9]{3}[A-Z]?", parti[1].strip()):
                    continue
                codice = parti[1].strip()
                prov = parti[3].strip() if con_provincia and len(parti) > 3 and re.fullmatch(r"[A-Z]{2}", parti[3].strip()) else None
                if codice not in out or (prov and not out[codice][1]):
                    out[codice] = (parti[0].strip(), prov)
    return out


def cerca_comune(codice: str) -> dict | None:
    """Comune e provincia di un codice catastale, se il componente ufficiale e' configurato; altrimenti None."""
    jar = _jar()
    if jar is None:
        return None
    try:
        voce = _comuni(str(jar)).get(codice)
    except (OSError, zipfile.BadZipFile):
        return None
    return {"nome": voce[0], "provincia": voce[1]} if voce else None


def _norm_nome(s: str) -> str:
    """Nome del comune confrontabile: maiuscole, senza accenti, apostrofi e spazi ripetuti («Sant'Agata» = «SANT AGATA»)."""
    import unicodedata
    s = re.sub(r"[‘’‛´`']", " ", s or "")   # apostrofi tipografici: spazio, non cancellati
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]+", " ", s.upper()).strip()


def cerca_codice_comune(nome: str, provincia: str | None = None) -> dict:
    """Codice catastale di un comune dal nome (ed eventualmente dalla provincia), dalle stesse tabelle del componente ufficiale
    SUC13 usate per il codice fiscale. Nessuna tabella nel programma: senza componente configurato l'esito e'
    ``tabelle_assenti`` e il codice resta da scrivere a mano.

    ``esito``: ``trovato`` (un solo comune: ``codice``, ``nome``, ``provincia``), ``ambiguo`` (piu' comuni con quel nome:
    ``candidati``, si sceglie con la provincia), ``non_trovato`` o ``tabelle_assenti``."""
    jar = _jar()
    if jar is None:
        return {"esito": "tabelle_assenti", "candidati": []}
    chiave = _norm_nome(nome)
    if not chiave:
        return {"esito": "non_trovato", "candidati": []}
    try:
        tab = _comuni(str(jar))
    except (OSError, zipfile.BadZipFile):
        return {"esito": "tabelle_assenti", "candidati": []}
    cand = [{"codice": c, "nome": n, "provincia": p} for c, (n, p) in tab.items() if _norm_nome(n) == chiave]
    prov = (provincia or "").strip().upper()
    if prov and prov != "EE":
        cand = [x for x in cand if x["provincia"] == prov] or [x for x in cand if x["provincia"] is None]
    esclusi = 0
    if len(cand) > 1:
        # comuni con provincia (elenco delle conservatorie) prima di quelli dell'altro elenco, che non la riporta e contiene
        # anche comuni soppressi: se ne resta uno solo si propone quello, segnalando gli omonimi esclusi
        attuali = [x for x in cand if x["provincia"]]
        if len(attuali) == 1:
            esclusi, cand = len(cand) - 1, attuali
    cand.sort(key=lambda x: (x["provincia"] or "ZZ", x["codice"]))
    if len(cand) == 1:
        return {"esito": "trovato", **cand[0], "candidati": cand, "omonimi_senza_provincia": esclusi}
    return {"esito": "ambiguo" if cand else "non_trovato", "candidati": cand[:20], "omonimi_senza_provincia": 0}


# ---------------------------------------------------------------------------------------------------------- decodifica
def decodifica(codice_fiscale: str, *, oggi: date | None = None, ruolo: str | None = None) -> dict:
    """Ricava i dati anagrafici dal codice fiscale.

    Restituisce ``{"valido": bool, "motivi": [...], "avvisi": [...], "campi": {...}, "dettaglio": {...}}``: ``campi`` ha le chiavi
    del modello (``sesso``, ``data_nascita``, ``luogo_nascita``, ``provincia_nascita``) solo se ricavate; ``valido`` e' vero se la
    struttura e il carattere di controllo sono corretti (la data puo' comunque non essere ricostruibile)."""
    oggi = oggi or date.today()
    cf = (codice_fiscale or "").strip().upper()
    out = {"valido": False, "motivi": [], "avvisi": [], "campi": {}, "dettaglio": {"codice_fiscale": cf}}
    if re.fullmatch(r"[0-9]{11}", cf):
        out["motivi"].append("codice a 11 cifre (persona non fisica): non contiene dati anagrafici")
        return out
    if len(cf) != 16 or not _RE_16.fullmatch(cf):
        out["motivi"].append("il codice fiscale di una persona fisica ha 16 caratteri nel formato ministeriale")
        return out
    controllo = ID.cf_persona_fisica_valido(cf)
    if not controllo:
        out["motivi"].append(f"carattere di controllo errato (atteso {ID.carattere_controllo(cf[:15])})")
    base, omocodia = _senza_omocodia(cf)
    out["dettaglio"]["omocodia"] = omocodia
    if omocodia:
        out["avvisi"].append("codice con omocodia: i dati sono ricavati sostituendo le lettere con le cifre corrispondenti")
    giorno_cf = int(base[9:11])
    sesso = "F" if giorno_cf > 40 else "M"
    giorno = giorno_cf - 40 if giorno_cf > 40 else giorno_cf
    out["campi"]["sesso"] = sesso
    mese = _MESE.get(base[8])
    if mese is None:
        out["motivi"].append(f"lettera del mese {base[8]!r} non valida")
    else:
        anno, ambiguo = _anno(int(base[6:8]), mese, giorno, oggi, ruolo)
        try:
            out["campi"]["data_nascita"] = date(anno, mese, giorno).isoformat()
            if ambiguo:
                out["avvisi"].append(f"secolo non determinabile dal codice: assunto {anno}; verificare la data di nascita")
        except ValueError:
            out["motivi"].append(f"data di nascita impossibile: giorno {giorno}, mese {mese}")
    codice = base[11:15]
    out["dettaglio"]["codice_catastale"] = codice
    if codice.startswith("Z"):
        out["campi"]["provincia_nascita"] = "EE"
        out["avvisi"].append(f"nato all'estero (codice {codice}): indicare lo Stato di nascita")
    else:
        comune = cerca_comune(codice)
        if comune:
            out["campi"]["luogo_nascita"] = comune["nome"]
            if comune["provincia"]:
                out["campi"]["provincia_nascita"] = comune["provincia"]
        else:
            out["avvisi"].append(f"comune con codice catastale {codice} non trovato: indicarlo a mano" if _jar()
                                 else f"codice catastale {codice}: tabelle dei comuni non disponibili (componente SUC13 non configurato), indicare il comune")
    out["valido"] = controllo and not out["motivi"]
    return out
