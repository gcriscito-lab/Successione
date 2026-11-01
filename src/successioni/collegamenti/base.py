"""Tipi condivisi dei collegamenti ufficiali e persistenza dei tentativi sulla tabella `job`.

Regole di fondo (vedi docs/COLLEGAMENTI.md):
- `Esito` ha quattro sole parole: passato | fallito | da_collaudare | simulazione.
- Ogni tentativo e' una riga della tabella `job` (tipo, stato, input, risultato JSON): sopravvive alla
  chiusura del client e puo' essere ripreso da un altro processo (GUI, MCP, CLI) che apra lo stesso archivio.
- Nessuna credenziale, nessun segreto, nessun endpoint: questo modulo non conosce la rete.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from ..archivio import Archivio
from ..errori import ChiaveRiutilizzata, ErroreServizio, NonTrovato, ora


# --------------------------------------------------------------------------------------- esiti
class Esito(str, Enum):
    """Livello di evidenza del risultato di una chiamata a un adattatore (docs/COLLAUDO_CLOUD_WINDOWS.md)."""

    PASSATO = "passato"            # eseguito sul componente/servizio reale, input/output/ambiente documentati
    FALLITO = "fallito"            # eseguito sul componente/servizio reale, esito negativo con diagnosi
    DA_COLLAUDARE = "da_collaudare"  # componente/servizio reale non esercitato: stato persistito, prova da fare
    SIMULAZIONE = "simulazione"    # eseguito su trasporto/fixture simulati: NON prova l'interoperabilita'

    def __str__(self) -> str:  # pragma: no cover - comodita'
        return self.value


ESITI = tuple(e.value for e in Esito)


@dataclass
class RisultatoAdattatore:
    """Risultato uniforme di ogni chiamata agli adattatori (contratto: docs/CONTRATTI_MODULI.md, area 3).

    `dettaglio` e' sempre un dict serializzabile in JSON; contiene `job_id` e `stato` quando la chiamata
    ha creato o letto un tentativo persistente.
    """

    esito: Esito
    dettaglio: dict
    artefatti: list = field(default_factory=list)
    azione_richiesta: str | None = None

    def __post_init__(self):
        self.esito = Esito(self.esito)

    @property
    def job_id(self) -> str | None:
        return self.dettaglio.get("job_id")

    @property
    def stato(self) -> str | None:
        return self.dettaglio.get("stato")

    def asdict(self) -> dict:
        d = asdict(self)
        d["esito"] = self.esito.value
        return d


# --------------------------------------------------------------------------------------- errori
class TransizioneNonAmmessa(ErroreServizio):
    codice = "TRANSIZIONE_NON_AMMESSA"


class ReinvioNonAmmesso(ErroreServizio):
    codice = "REINVIO_NON_AMMESSO"


class ConfermaNonValida(ErroreServizio):
    codice = "CONFERMA_NON_VALIDA"


class ComponenteNonDisponibile(ErroreServizio):
    codice = "COMPONENTE_NON_DISPONIBILE"


# --------------------------------------------------------------------------------------- utilita'
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path | str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blocco in iter(lambda: f.read(1 << 20), b""):
            h.update(blocco)
    return h.hexdigest()


def impronta_json(obj: Any) -> str:
    """Impronta canonica (chiavi ordinate) di una struttura JSON."""
    return sha256_bytes(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                                   default=str).encode("utf-8"))


# ------------------------------------------------------------------------------- protocolli (interfacce)
@runtime_checkable
class ControlloUfficiale(Protocol):
    """Esegue (o prepara il passaggio manuale del) controllo ufficiale su un file XML."""

    def esegui(self, xml_path: Path | str, **kw) -> RisultatoAdattatore: ...


@runtime_checkable
class CatastoEntratel(Protocol):
    """Risultanze catastali via Entratel (NON SISTER). Macchina a stati persistente."""

    def avvia(self, pratica_id: str, ambito: dict, **kw) -> RisultatoAdattatore: ...

    def riprendi(self, job_id: str, **kw) -> RisultatoAdattatore: ...

    def leggi_risultati(self, job_id: str, **kw) -> RisultatoAdattatore: ...


@runtime_checkable
class InvioSUC13(Protocol):
    """Preparazione, conferma, trasmissione e riconciliazione. La trasmissione reale NON e' implementata qui."""

    def prepara(self, pratica_id: str, **kw) -> RisultatoAdattatore: ...

    def conferma(self, copia_id: str, **kw) -> RisultatoAdattatore: ...

    def trasmetti(self, copia_id: str, **kw) -> RisultatoAdattatore: ...

    def riconcilia(self, tentativo_id: str, **kw) -> RisultatoAdattatore: ...


@runtime_checkable
class Ricevute(Protocol):
    """Associa ricevute ed esiti (documenti distinti) a un protocollo e a una pratica."""

    def associa(self, **kw) -> RisultatoAdattatore: ...


# ------------------------------------------------------------------------------------ persistenza job
PREFISSI_JOB = {
    "controllo_ufficiale": "ctl",
    "catasto_entratel": "cat",
    "invio_copia": "cpc",
    "invio_tentativo": "inv",
    "ricevuta_suc13": "ric",
}


def _carica(testo: str | None, default):
    if not testo:
        return default
    try:
        return json.loads(testo)
    except ValueError:  # pragma: no cover - archivio manomesso
        return default


class RegistroJob:
    """Accesso tipizzato alla tabella `job` (nessuna nuova tabella).

    - `input` e' immutabile dopo la creazione (contiene i parametri della richiesta e la sua impronta);
    - `risultato` e' un dict che accumula lo stato di lavorazione e una `cronologia` append-only;
    - `transizione()` e' un compare-and-set sullo stato dentro una transazione IMMEDIATE: due processi che
      tentano la stessa transizione non possono riuscire entrambi (base della protezione dai doppi invii).
    """

    def __init__(self, archivio: Archivio):
        self.arch = archivio

    # -- lettura
    @staticmethod
    def _riga(r) -> dict:
        return {
            "job_id": r["id"], "tipo": r["tipo"], "pratica_id": r["pratica_id"], "stato": r["stato"],
            "input": _carica(r["input"], {}), "risultato": _carica(r["risultato"], {}),
            "errore": r["errore"], "creato": r["creato"], "aggiornato": r["aggiornato"],
        }

    def leggi(self, job_id: str) -> dict:
        with self.arch.lettura() as c:
            r = c.execute("SELECT * FROM job WHERE id=?", (job_id,)).fetchone()
        if not r:
            raise NonTrovato("tentativo inesistente", job_id=job_id)
        return self._riga(r)

    def elenca(self, tipo: str | None = None, pratica_id: str | None = None) -> list[dict]:
        sql, par = "SELECT * FROM job WHERE 1=1", []
        if tipo:
            sql += " AND tipo=?"
            par.append(tipo)
        if pratica_id:
            sql += " AND pratica_id=?"
            par.append(pratica_id)
        sql += " ORDER BY creato, rowid"
        with self.arch.lettura() as c:
            return [self._riga(r) for r in c.execute(sql, par)]

    # -- creazione idempotente
    @staticmethod
    def id_da_chiave(tipo: str, chiave: str) -> str:
        return f"{PREFISSI_JOB[tipo]}_{sha256_bytes((tipo + chr(0) + chiave).encode())[:24]}"

    def crea(self, tipo: str, pratica_id: str | None, input_: dict, *, stato: str, chiave: str | None = None,
             risultato: dict | None = None, nota: str = "creato") -> tuple[dict, bool]:
        """Crea un tentativo. Con `chiave` e' idempotente: stessa chiave e stesso input restituiscono il
        tentativo gia' esistente (creato=False); stessa chiave con input diverso e' un errore."""
        if tipo not in PREFISSI_JOB:
            raise ValueError(f"tipo di job sconosciuto: {tipo}")
        job_id = self.id_da_chiave(tipo, chiave) if chiave else f"{PREFISSI_JOB[tipo]}_{uuid.uuid4().hex[:24]}"
        impr = impronta_json(input_)
        corpo = {**input_, "_impronta": impr}
        if chiave:
            corpo["_chiave_richiesta"] = chiave
        t = ora()
        ris = dict(risultato or {})
        ris.setdefault("cronologia", []).append({"ts": t, "stato": stato, "nota": nota})
        with self.arch.transazione() as c:
            r = c.execute("SELECT * FROM job WHERE id=?", (job_id,)).fetchone()
            if r:
                esistente = self._riga(r)
                if esistente["input"].get("_impronta") != impr:
                    raise ChiaveRiutilizzata("chiave di richiesta gia' usata con un contenuto diverso",
                                             chiave=chiave, job_id=job_id)
                return esistente, False
            c.execute("INSERT INTO job(id,tipo,pratica_id,stato,input,risultato,errore,creato,aggiornato) "
                      "VALUES(?,?,?,?,?,?,?,?,?)",
                      (job_id, tipo, pratica_id, stato, json.dumps(corpo, ensure_ascii=False),
                       json.dumps(ris, ensure_ascii=False), None, t, t))
            r = c.execute("SELECT * FROM job WHERE id=?", (job_id,)).fetchone()
            return self._riga(r), True

    # -- aggiornamento
    def transizione(self, job_id: str, da: set[str] | tuple | list | None, a: str, *, patch: dict | None = None,
                    nota: str = "", errore: str | None = None) -> dict:
        """Passa a stato `a` solo se lo stato corrente e' in `da` (None = qualsiasi). `patch` viene fuso
        (merge di primo livello) in `risultato`; la cronologia e' sempre estesa, mai riscritta."""
        t = ora()
        with self.arch.transazione() as c:
            r = c.execute("SELECT * FROM job WHERE id=?", (job_id,)).fetchone()
            if not r:
                raise NonTrovato("tentativo inesistente", job_id=job_id)
            if da is not None and r["stato"] not in set(da):
                raise TransizioneNonAmmessa(
                    f"transizione {r['stato']} -> {a} non ammessa (ammesse da: {sorted(set(da))})",
                    job_id=job_id, stato=r["stato"], richiesto=a)
            ris = _carica(r["risultato"], {})
            for k, v in (patch or {}).items():
                if k != "cronologia":
                    ris[k] = v
            ris.setdefault("cronologia", []).append({"ts": t, "da": r["stato"], "stato": a, "nota": nota})
            c.execute("UPDATE job SET stato=?, risultato=?, errore=?, aggiornato=? WHERE id=?",
                      (a, json.dumps(ris, ensure_ascii=False), errore if errore is not None else r["errore"], t,
                       job_id))
            r = c.execute("SELECT * FROM job WHERE id=?", (job_id,)).fetchone()
            return self._riga(r)

    def annota(self, job_id: str, patch: dict, nota: str = "") -> dict:
        """Aggiorna `risultato` senza cambiare stato."""
        return self.transizione(job_id, None, self.leggi(job_id)["stato"], patch=patch, nota=nota)


# ------------------------------------------------------------------------------- deposito artefatti
class DepositoArtefatti:
    """Conserva gli artefatti dei tentativi (diagnostici, copie congelate, risposte) nello stesso deposito
    content-addressed degli allegati (`Archivio.percorso_allegato`), cosi' che il backup coerente di
    database + allegati li comprenda. Il file non viene mai riscritto se esiste gia' (immutabile)."""

    def __init__(self, archivio: Archivio):
        self.arch = archivio

    def salva_bytes(self, contenuto: bytes, nome: str, ruolo: str, **extra) -> dict:
        h = sha256_bytes(contenuto)
        dest = self.arch.percorso_allegato(h)
        if not dest.exists():
            tmp = dest.with_name(dest.name + ".tmp")
            tmp.write_bytes(contenuto)
            tmp.replace(dest)
        return {"nome": nome, "ruolo": ruolo, "sha256": h, "bytes": len(contenuto),
                "percorso": str(dest.relative_to(self.arch.base)), **extra}

    def salva_file(self, percorso: Path | str, nome: str | None = None, ruolo: str = "file", **extra) -> dict:
        p = Path(percorso)
        return self.salva_bytes(p.read_bytes(), nome or p.name, ruolo, **extra)

    def leggi(self, descrittore: dict) -> bytes:
        p = self.arch.base / descrittore["percorso"]
        dati = p.read_bytes()
        if sha256_bytes(dati) != descrittore["sha256"]:
            raise ErroreServizio("artefatto alterato: impronta diversa da quella registrata",
                                 nome=descrittore.get("nome"))
        return dati
