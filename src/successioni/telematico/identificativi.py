"""Controlli formali di codice fiscale e IBAN; generatore di codici fiscali SINTETICI per i test.

Fonti (nessuna regola dalla memoria). Il decreto che definisce il codice fiscale non e' tra i materiali di ``fonti/``;
le tabelle e gli algoritmi qui sotto sono letti con ispezione statica (``javap -c -constants``) dei componenti
ufficiali scaricati il 2026-11-01 dal codebase di ``ControlliSUC13.jnlp`` (https://jws.agenziaentrate.it/jws/registro/
2013/) e VERIFICATI ESEGUENDO gli stessi componenti (``tests/fixture_telematico/VerificaComponenti.java``, test
``tests/test_telematico_identificativi.py``, attivo con ``SUCCESSIONI_CONTROLLI_SUC13``):

- ``checkCF_PIVA.jar`` (SHA-256 6069cee2...238be), classe ``finanze.pos.fileutility.U1CheckDigit``:
  ``creaCarattereDispari``/``creaNumeroDispari`` (valori dei caratteri in posizione dispari), ``creaCaratterePari``/
  ``creaNumeroPari`` (posizione pari), ``controllaCheckDigit`` (somma delle prime 15 posizioni modulo 26, confrontata
  con la posizione del 16o carattere nella tabella pari), ``creaMese`` (lettere dei mesi);
  classe ``finanze.pos.fileutility.CodiceFiscale`` (calcolo da cognome, nome, sesso, data e comune: usata solo come
  riferimento d'esecuzione per il generatore sintetico);
- ``controlliXMLREG2013.jar`` (SHA-256 0b42dfc3...6a10), classe
  ``it.finanze.entrate.sco.modSUC.validator.checkdigit.IBANCheckDigit`` (primi 4 caratteri spostati in coda, valore
  numerico di ogni carattere con ``Character.getNumericValue``, modulo 97 = 1) e ``generale2013/IBAN.properties``
  (``length.IT=27``, coerente con la lunghezza 27 dell'XSD ``reg:Versamento_Type/IBAN``).

Il controllo del CIN italiano (``CheckIBAN.isCorrect``) NON e' replicato: resta al controllo ufficiale.
I codici generati sono sintetici: formalmente validi, non attribuiti a persone (non verificati in Anagrafe tributaria).
"""
from __future__ import annotations

import re
from datetime import date

FONTE_CF = ("checkCF_PIVA.jar (ControlliSUC13.jnlp, scaricato il 2026-11-01), classe finanze.pos.fileutility."
            "U1CheckDigit: controllaCheckDigit, tabelle creaCarattereDispari/creaNumeroDispari/creaCaratterePari/"
            "creaNumeroPari (javap) ; verificato eseguendo il componente")
FONTE_IBAN = ("controlliXMLREG2013.jar, classe it.finanze.entrate.sco.modSUC.validator.checkdigit.IBANCheckDigit "
              "(modulo 97) e generale2013/IBAN.properties length.IT=27 (javap) ; verificato eseguendo il componente")

# U1CheckDigit.creaCarattereDispari: il valore e' l'indice nel vettore (indice 0 -> 'B', 1 -> 'A', ...)
_DISPARI_LETTERE = "BAKPLCQDREVOSFTGUHMINJWZYX"
# U1CheckDigit.creaNumeroDispari: indice -> cifra; le posizioni vuote del vettore sono stringhe vuote
_DISPARI_CIFRE = {"1": 0, "0": 1, "2": 5, "3": 7, "4": 9, "5": 13, "6": 15, "7": 17, "8": 19, "9": 21}
# U1CheckDigit.creaCaratterePari / creaNumeroPari: A..Z -> 0..25, 0..9 -> 0..9
_PARI_LETTERE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
# U1CheckDigit.creaMese
MESI = "ABCDEHLMPRST"
_CF16 = re.compile(r"[A-Z]{6}[0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{3}[A-Z]")


def _valore(c: str, pos0: int) -> int:
    """Valore del carattere in posizione ``pos0`` (0-based): pos0 pari = posizione dispari (1a, 3a, ...)."""
    if pos0 % 2 == 0:
        return _DISPARI_CIFRE[c] if c.isdigit() else _DISPARI_LETTERE.index(c)
    return int(c) if c.isdigit() else _PARI_LETTERE.index(c)


def carattere_controllo(primi15: str) -> str:
    """Carattere di controllo (16o) di un codice fiscale di persona fisica dai primi 15 caratteri."""
    s = primi15.strip().upper()
    if len(s) != 15 or not all(c.isdigit() or "A" <= c <= "Z" for c in s):
        raise ValueError(f"{primi15!r}: attesi 15 caratteri A-Z/0-9")
    return _PARI_LETTERE[sum(_valore(c, i) for i, c in enumerate(s)) % 26]


def cf_persona_fisica_valido(cf: str) -> bool:
    """Formato DatoCF a 16 caratteri e carattere di controllo corretto (``U1CheckDigit.controllaCheckDigit``)."""
    s = cf.strip().upper() if isinstance(cf, str) else ""
    return bool(_CF16.fullmatch(s)) and carattere_controllo(s[:15]) == s[15]


# ------------------------------------------------------------------------------------------- generatore sintetico
# CodiceFiscale.noAccentate: "ÀÈÉÌÒÙàèéìòù" -> "AEEIOUAEEIOU" (javap -constants, costanti #94/#96)
_ACCENTATE = str.maketrans("ÀÈÉÌÒÙàèéìòù", "AEEIOUAEEIOU")
# CodiceFiscale(): costanti #25 'AEIOU' (vocali) e #29 'BCDFGHJKLMNPQRSTVWXYZ' (consonanti); gli altri caratteri
# (spazi, apostrofi, trattini) non contano
_VOCALI, _CONSONANTI = "AEIOU", "BCDFGHJKLMNPQRSTVWXYZ"


def _lettere(s: str) -> str:
    t = s.translate(_ACCENTATE).upper()
    altri = sorted({c for c in t if c.isalpha() and not "A" <= c <= "Z"})
    if altri:
        raise ValueError(f"{s!r}: lettere {''.join(altri)!r} non gestite dal generatore sintetico")
    return "".join(c for c in t if "A" <= c <= "Z")


def _consonanti(s: str) -> str:
    return "".join(c for c in _lettere(s) if c in _CONSONANTI)


def _vocali(s: str) -> str:
    return "".join(c for c in _lettere(s) if c in _VOCALI)


def _parte_cognome(cognome: str) -> str:
    return (_consonanti(cognome) + _vocali(cognome) + "XXX")[:3]


def _parte_nome(nome: str) -> str:
    c = _consonanti(nome)
    if len(c) >= 4:
        return c[0] + c[2] + c[3]
    return (c + _vocali(nome) + "XXX")[:3]


def genera_cf_sintetico(cognome: str, nome: str, sesso: str, nascita: date | str, codice_comune: str) -> str:
    """Codice fiscale SINTETICO formalmente valido, coerente con i dati anagrafici indicati.

    Solo per dati di prova: nessuna gestione dell'omocodia, nessuna verifica in Anagrafe tributaria. L'esito e'
    confrontato nei test con ``finanze.pos.fileutility.CodiceFiscale.getCodiceFiscale`` del componente ufficiale."""
    d = date.fromisoformat(nascita) if isinstance(nascita, str) else nascita
    if sesso not in ("M", "F"):
        raise ValueError("sesso atteso M o F")
    comune = codice_comune.strip().upper()
    if not re.fullmatch(r"[A-Z][0-9]{3}", comune):
        raise ValueError(f"{codice_comune!r}: codice catastale atteso (lettera + 3 cifre)")
    giorno = d.day + (40 if sesso == "F" else 0)
    primi = f"{_parte_cognome(cognome)}{_parte_nome(nome)}{d.year % 100:02d}{MESI[d.month - 1]}{giorno:02d}{comune}"
    return primi + carattere_controllo(primi)


# ------------------------------------------------------------------------------------------- IBAN
def iban_modulo_97_valido(iban: str) -> bool:
    """IBAN italiano di 27 caratteri con cifre di controllo corrette (modulo 97). Il CIN non e' verificato."""
    s = iban.replace(" ", "").upper() if isinstance(iban, str) else ""
    if not re.fullmatch(r"IT[0-9]{2}[A-Z][0-9]{10}[0-9A-Z]{12}", s):
        return False
    return _mod97(s[4:] + s[:4]) == 1


def _mod97(s: str) -> int:
    n = 0
    for c in s:
        v = int(c) if c.isdigit() else ord(c) - ord("A") + 10
        n = (n * (100 if v > 9 else 10) + v) % 97
    return n


def cifre_controllo_iban(paese: str, bban: str) -> str:
    """Cifre di controllo IBAN (98 - modulo 97 con cifre '00'), come ``IBANCheckDigit.calculate``."""
    return f"{98 - _mod97(bban.upper() + paese.upper() + '00'):02d}"
