"""Tipi condivisi dei collegamenti ufficiali e persistenza dei tentativi sulla tabella `job`.

Regole di fondo (vedi docs/COLLEGAMENTI.md):
- `Esito` ha quattro sole parole: passato | fallito | da_collaudare | simulazione (docs/COLLAUDO_CLOUD_WINDOWS.md).
  `passato`/`fallito` solo per prove eseguite sul componente o servizio reale con input/output/ambiente registrati;
  qualunque esecuzione su trasporto o componente simulato produce `simulazione`, anche se "positiva".
- Ogni tentativo e' una riga della tabella `job` (tipo, stato, input, risultato JSON): sopravvive alla chiusura del
  client e puo' essere ripreso da un altro processo (GUI, MCP, CLI) che apra lo stesso archivio.
- Nessuna credenziale, nessun segreto, nessun endpoint: questo modulo non conosce la rete e rifiuta di salvare
  chiavi che somigliano a segreti.
"""
from __future__ import annotations
from contextlib import nullcontext

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol, runtime_checkable

from ..archivio import Archivio
from ..errori import ChiaveRiutilizzata, DatiNonValidi, ErroreServizio, NonTrovato, ora


# --------------------------------------------------------------------------------------- esiti
class Esito(str, Enum):
    """Livello di evidenza del risultato di una chiamata a un adattatore."""

    PASSATO = "passato"              # eseguito sul componente/servizio reale; input/output/ambiente documentati
    FALLITO = "fallito"              # eseguito sul componente/servizio reale; esito negativo con diagnosi
    DA_COLLAUDARE = "da_collaudare"  # componente/servizio reale non esercitato: stato persistito, prova da fare
    SIMULAZIONE = "simulazione"      # trasporto/fixture simulati: NON prova l'interoperabilita'

    def __str__(self) -> str:  # pragma: no cover - comodita'
        return self.value


ESITI = tuple(e.value for e in Esito)

# Stato del controllo ufficiale come dimensione separata della pratica (specifica §10).
STATI_CONTROLLO = ("non_eseguito", "positivo", "negativo", "da_verificare", "non_verificabile")


@dataclass
class RisultatoAdattatore:
    """Risultato uniforme di ogni chiamata agli adattatori (contratto: docs/CONTRATTI_MODULI.md, area 3).

    `dettaglio` e' sempre un dict serializzabile in JSON; contiene `job_id` e `stato` quando la chiamata
    ha creato o letto un tentativo persistente. `artefatti` sono descrittori di `DepositoArtefatti`.
    `azione_richiesta` e' il testo per l'utente quando serve un suo intervento (autenticazione, passaggio
    manuale, riconciliazione); None se non serve nulla.
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


class SegretoRifiutato(DatiNonValidi):
    codice = "SEGRETO_NON_AMMESSO"


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


# Chiavi che non devono mai finire in job/artefatti/log (le credenziali restano nel deposito protetto del sistema).
_PAROLE_SEGRETE = ("password", "passwd", "pwd", "pin", "puk", "segreto", "secret", "token", "credenzial",
                   "chiave_privata", "private_key", "p12_password")


def verifica_assenza_segreti(obj: Any, percorso: str = "") -> None:
    """Solleva `SegretoRifiutato` se una chiave di dict somiglia a una credenziale.

    Difesa in profondita': gli adattatori non ricevono segreti; se un chiamante li passa per errore non vengono
    persistiti. Controlla solo i nomi delle chiavi (i valori non vengono mai letti o riportati nell'errore).
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            nome = str(k).lower()
            if any(p == nome or nome.startswith(p + "_") or nome.endswith("_" + p) or (len(p) > 4 and p in nome)
                   for p in _PAROLE_SEGRETE):
                raise SegretoRifiutato("dato con nome da credenziale: non viene salvato (usare il deposito protetto "
                                       "del sistema)", campo=f"{percorso}.{k}".lstrip("."))
            verifica_assenza_segreti(v, f"{percorso}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            verifica_assenza_segreti(v, f"{percorso}[{i}]")


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

    def leggi(self, job_id: str, tipo: str | None = None) -> dict:
        with self.arch.lettura() as c:
            r = c.execute("SELECT * FROM job WHERE id=?", (job_id,)).fetchone()
        if not r or (tipo and r["tipo"] != tipo):
            raise NonTrovato("tentativo inesistente", job_id=job_id, tipo=tipo)
        return self._riga(r)

    def elenca(self, tipo: str | None = None, pratica_id: str | None = None,
               stati: Iterable[str] | None = None) -> list[dict]:
        sql, par = "SELECT * FROM job WHERE 1=1", []
        if tipo:
            sql += " AND tipo=?"
            par.append(tipo)
        if pratica_id:
            sql += " AND pratica_id=?"
            par.append(pratica_id)
        stati = list(stati or [])
        if stati:
            sql += f" AND stato IN ({','.join('?' * len(stati))})"
            par.extend(stati)
        sql += " ORDER BY creato, rowid"
        with self.arch.lettura() as c:
            return [self._riga(r) for r in c.execute(sql, par)]

    # -- creazione idempotente
    @staticmethod
    def id_da_chiave(tipo: str, chiave: str) -> str:
        return f"{PREFISSI_JOB[tipo]}_{sha256_bytes((tipo + chr(0) + chiave).encode())[:24]}"

    def crea(self, tipo: str, pratica_id: str | None, input_: dict, *, stato: str, chiave: str | None = None,
             risultato: dict | None = None, nota: str = "creato", vincolo=None) -> tuple[dict, bool]:
        """Crea un tentativo. Con `chiave` e' idempotente: stessa chiave e stesso input restituiscono il
        tentativo gia' esistente (creato=False); stessa chiave con input diverso e' un errore. `vincolo(c)`, se indicato,
        gira nella stessa transazione subito prima dell'inserimento (puo' sollevare un errore che annulla tutto)."""
        if tipo not in PREFISSI_JOB:
            raise ValueError(f"tipo di job sconosciuto: {tipo}")
        verifica_assenza_segreti(input_, "input")
        verifica_assenza_segreti(risultato or {}, "risultato")
        job_id = self.id_da_chiave(tipo, chiave) if chiave else f"{PREFISSI_JOB[tipo]}_{uuid.uuid4().hex[:24]}"
        impr = impronta_json(input_)
        corpo = {**input_, "_impronta": impr}
        if chiave:
            corpo["_chiave_richiesta"] = chiave
        t = ora()
        ris = dict(risultato or {})
        ris["cronologia"] = [{"ts": t, "stato": stato, "nota": nota}]
        with self.arch.transazione() as c:
            r = c.execute("SELECT * FROM job WHERE id=?", (job_id,)).fetchone()
            if r:
                esistente = self._riga(r)
                if esistente["input"].get("_impronta") != impr:
                    raise ChiaveRiutilizzata("chiave di richiesta gia' usata con un contenuto diverso",
                                             chiave=chiave, job_id=job_id)
                return esistente, False
            if vincolo is not None:
                vincolo(c)
            c.execute("INSERT INTO job(id,tipo,pratica_id,stato,input,risultato,errore,creato,aggiornato) "
                      "VALUES(?,?,?,?,?,?,?,?,?)",
                      (job_id, tipo, pratica_id, stato, json.dumps(corpo, ensure_ascii=False),
                       json.dumps(ris, ensure_ascii=False), None, t, t))
            r = c.execute("SELECT * FROM job WHERE id=?", (job_id,)).fetchone()
            return self._riga(r), True

    # -- aggiornamento
    def transizione(self, job_id: str, da: Iterable[str] | None, a: str | None, *, patch: dict | None = None,
                    nota: str = "", errore: str | None = None,
                    vincolo: Callable[[Callable[..., list[dict]]], str | None] | None = None, _conn=None) -> dict:
        """Passa allo stato `a` solo se lo stato corrente e' in `da` (None = qualsiasi); `a=None` mantiene lo
        stato corrente (annotazione). `patch` viene fuso (primo livello) in `risultato`; la cronologia e' sempre
        estesa, mai riscritta. Tutto avviene in un'unica transazione IMMEDIATE (compare-and-set).

        `vincolo(elenca)` viene valutato DENTRO la stessa transazione: riceve una funzione
        `elenca(tipo, pratica_id)` sulle righe correnti e restituisce un messaggio per rifiutare la transizione
        (es. un'altra copia della stessa pratica gia' in invio)."""
        verifica_assenza_segreti(patch or {}, "risultato")
        t = ora()
        with (nullcontext(_conn) if _conn is not None else self.arch.transazione()) as c:
            r = c.execute("SELECT * FROM job WHERE id=?", (job_id,)).fetchone()
            if not r:
                raise NonTrovato("tentativo inesistente", job_id=job_id)
            ammessi = None if da is None else set(da)
            if ammessi is not None and r["stato"] not in ammessi:
                raise TransizioneNonAmmessa(
                    f"transizione {r['stato']} -> {a or r['stato']} non ammessa (ammesse da: {sorted(ammessi)})",
                    job_id=job_id, stato=r["stato"], richiesto=a)
            if vincolo is not None:
                def elenca(tipo: str, pratica_id: str | None) -> list[dict]:
                    return [self._riga(x) for x in c.execute(
                        "SELECT * FROM job WHERE tipo=? AND pratica_id IS ? ORDER BY creato, rowid", (tipo, pratica_id))]
                msg = vincolo(elenca)
                if msg:
                    raise TransizioneNonAmmessa(msg, job_id=job_id, stato=r["stato"], richiesto=a)
            nuovo = a or r["stato"]
            ris = _carica(r["risultato"], {})
            for k, v in (patch or {}).items():
                if k != "cronologia":
                    ris[k] = v
            ris.setdefault("cronologia", []).append({"ts": t, "da": r["stato"], "stato": nuovo, "nota": nota})
            c.execute("UPDATE job SET stato=?, risultato=?, errore=?, aggiornato=? WHERE id=?",
                      (nuovo, json.dumps(ris, ensure_ascii=False), errore if errore is not None else r["errore"],
                       t, job_id))
            r = c.execute("SELECT * FROM job WHERE id=?", (job_id,)).fetchone()
            return self._riga(r)

    def annota(self, job_id: str, patch: dict, nota: str = "") -> dict:
        """Aggiorna `risultato` senza cambiare stato (atomico: non puo' annullare una transizione concorrente)."""
        return self.transizione(job_id, None, None, patch=patch, nota=nota)

    def transizioni(self, operazioni: list[dict]) -> None:
        """Aggiorna piu' job insieme: un errore annulla tutte le transizioni."""
        with self.arch.transazione() as c:
            for op in operazioni:
                self.transizione(**op, _conn=c)


def risultato_da_job(job: dict, esito: Esito | str, *, artefatti: list | None = None,
                     azione_richiesta: str | None = None, **extra) -> RisultatoAdattatore:
    """Costruisce il RisultatoAdattatore standard a partire da una riga di job."""
    det = {"job_id": job["job_id"], "tipo": job["tipo"], "stato": job["stato"], "pratica_id": job["pratica_id"],
           "aggiornato": job["aggiornato"], **extra}
    return RisultatoAdattatore(esito=esito, dettaglio=det, artefatti=list(artefatti or []),
                               azione_richiesta=azione_richiesta)


# ------------------------------------------------------------------------------- deposito artefatti
class DepositoArtefatti:
    """Conserva gli artefatti dei tentativi (diagnostici, copie congelate, risposte) nello stesso deposito
    content-addressed degli allegati (`Archivio.percorso_allegato`), cosi' che il backup coerente di
    database + allegati li comprenda. Il file non viene mai riscritto se esiste gia' (immutabile)."""

    def __init__(self, archivio: Archivio):
        self.arch = archivio

    def salva_bytes(self, contenuto: bytes, nome: str, ruolo: str, **extra) -> dict:
        verifica_assenza_segreti(extra, "artefatto")
        h = sha256_bytes(contenuto)
        dest = self.arch.percorso_allegato(h)
        if not dest.exists():
            tmp = dest.with_name(f"{dest.name}.{uuid.uuid4().hex[:8]}.tmp")
            tmp.write_bytes(contenuto)
            tmp.replace(dest)
        return {"nome": nome, "ruolo": ruolo, "sha256": h, "bytes": len(contenuto),
                "percorso": dest.relative_to(self.arch.base).as_posix(), **extra}

    def salva_file(self, percorso: Path | str, nome: str | None = None, ruolo: str = "file", **extra) -> dict:
        p = Path(percorso)
        return self.salva_bytes(p.read_bytes(), nome or p.name, ruolo, **extra)

    def leggi(self, descrittore: dict) -> bytes:
        p = self.arch.base / descrittore["percorso"]
        if not p.exists():
            raise NonTrovato("artefatto mancante nel deposito", nome=descrittore.get("nome"),
                             sha256=descrittore.get("sha256"))
        dati = p.read_bytes()
        if sha256_bytes(dati) != descrittore["sha256"]:
            raise ErroreServizio("artefatto alterato: impronta diversa da quella registrata",
                                 nome=descrittore.get("nome"))
        return dati

    def esporta(self, descrittore: dict, cartella: Path | str, nome: str | None = None) -> Path:
        """Scrive una copia verificata dell'artefatto (per il passaggio a un componente esterno)."""
        dest = Path(cartella) / (nome or descrittore["nome"])
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self.leggi(descrittore))
        return dest
