"""Errori applicativi con codice stabile (usati da GUI e MCP)."""
from datetime import datetime, timezone


def ora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ErroreServizio(Exception):
    codice = "ERRORE"

    def __init__(self, messaggio: str, **dettagli):
        super().__init__(messaggio)
        self.messaggio = messaggio
        self.dettagli = dettagli

    def asdict(self):
        return {"codice": self.codice, "messaggio": self.messaggio, **self.dettagli}


class NonTrovato(ErroreServizio):
    codice = "NON_TROVATO"


class ConflittoRevisione(ErroreServizio):
    codice = "CONFLITTO_REVISIONE"


class DatiNonValidi(ErroreServizio):
    codice = "DATI_NON_VALIDI"


class ChiaveRiutilizzata(ErroreServizio):
    codice = "CHIAVE_RICHIESTA_RIUTILIZZATA"


class RipristinoNonAmmesso(ErroreServizio):
    codice = "RIPRISTINO_NON_AMMESSO"
