"""Servizio applicativo: unico punto di accesso per GUI e MCP."""
from __future__ import annotations

import copy
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone

from . import quadri as Q
from . import schema as S
from . import valori as V
from .allegati import AllegatiMixin
from .elaborati import ElaboratiMixin
from .invio_servizio import InvioMixin
from .archivio import Archivio
from .errori import (ChiaveRiutilizzata, ConflittoRevisione, DatiNonValidi, ErroreServizio,  # noqa: F401
                     NonTrovato, ora)

from .versioni import VERSIONE_REGOLE  # noqa: E402,F401
CANALI = ("gui", "mcp", "cli")


def _impronta(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def nuovi_dati() -> dict:
    return {**{c: [] for c in S.COLLEZIONI}, "opzioni": {}, "note": {}}


def impronta_dichiarativa(dati: dict) -> str:
    """Impronta dei soli dati che incidono sul dichiarato.

    Esclude note interne e metadati di origine; ignora l'ordine delle righe. Serve a decidere
    se un esito (calcolo/controllo) resta valido dopo una modifica (prova A16).
    """
    out = {}
    for coll in S.COLLEZIONI:
        righe = []
        for e in dati.get(coll, []):
            righe.append({k: v for k, v in e.items() if k != "_origine"})
        out[coll] = sorted(righe, key=lambda r: r["id"])
    out["opzioni"] = dati.get("opzioni", {})
    return _impronta(out)


def diff_dati(a: dict, b: dict) -> list[str]:
    righe: list[str] = []
    for coll in S.COLLEZIONI:
        ea = {e["id"]: e for e in a.get(coll, [])}
        eb = {e["id"]: e for e in b.get(coll, [])}
        for i in eb.keys() - ea.keys():
            righe.append(f"+ {coll}[{i}]")
        for i in ea.keys() - eb.keys():
            righe.append(f"- {coll}[{i}]")
        for i in ea.keys() & eb.keys():
            for k in sorted((ea[i].keys() | eb[i].keys()) - {"_origine"}):
                if ea[i].get(k) != eb[i].get(k):
                    righe.append(f"~ {coll}[{i}].{k}: {ea[i].get(k)!r} -> {eb[i].get(k)!r}")
    for sez in ("opzioni", "note"):
        for k in sorted(a.get(sez, {}).keys() | b.get(sez, {}).keys()):
            if a.get(sez, {}).get(k) != b.get(sez, {}).get(k):
                righe.append(f"~ {sez}.{k}")
    return righe


ID_VALIDO = re.compile(r"^[a-z]{1,4}_[a-z0-9]{4,32}$")
PREFISSI = {"persone": "p", "beni": "b", "devoluzioni": "d", "passivita": "ps", "documenti_ref": "dr"}


class Servizio(AllegatiMixin, ElaboratiMixin, InvioMixin):
    def __init__(self, archivio: Archivio | None = None):
        self.arch = archivio or Archivio()

    # ---------------------------------------------------------------- pratiche
    def crea_pratica(self, titolo: str, *, chiave: str | None = None, autore="utente", canale="gui",
                     iniziali: list[dict] | None = None) -> dict:
        """Crea la pratica; con `iniziali` applica nella stessa transazione le operazioni di partenza (creazione guidata)."""
        self._canale(canale)
        impr = _impronta({"titolo": titolo, "iniziali": iniziali or []})
        with self.arch.transazione() as c:
            if chiave:
                prec = self._richiesta(c, chiave, "crea_pratica", impr)
                if prec is not None:
                    return {**prec, "ripetuta": True}
            pid = "pr_" + uuid.uuid4().hex[:12]
            dati = nuovi_dati()
            origine = "proposto_assistente" if canale == "mcp" else "inserito"
            for i, op in enumerate(iniziali or []):
                self._applica(dati, op, origine, canale, i)
            from . import impostazioni
            profilo = impostazioni.profilo_studio(self.arch.base)
            if profilo and not (dati.get("opzioni") or {}).get("fornitore"):
                dati.setdefault("opzioni", {})["fornitore"] = dict(profilo)      # predefinito dello studio, modificabile per pratica
            errori = S.valida_forma(dati)
            if errori:
                raise DatiNonValidi("dati iniziali non validi: pratica non creata", errori=[e.asdict() for e in errori])
            t = ora()
            c.execute("INSERT INTO pratiche VALUES(?,?,?,?,?,?)", (pid, titolo, t, t, 1, json.dumps(dati)))
            c.execute("INSERT INTO revisioni VALUES(?,?,?,?,?,?,?,?)",
                      (pid, 1, t, autore, canale, chiave, "pratica creata", json.dumps(dati)))
            risp = {"pratica_id": pid, "revisione": 1, "titolo": titolo}
            if chiave:
                c.execute("INSERT INTO richieste VALUES(?,?,?,?,?,?)",
                          (chiave, pid, "crea_pratica", impr, json.dumps(risp), t))
            return risp

    def importa_xml_telematico(self, xml: bytes, *, titolo: str | None = None, autore="utente", canale="gui") -> dict:
        """Crea una pratica a partire da un file telematico SUC13 (vedi `telematico/importa.py`): solo i dati che
        l'esportazione sa riprodurre; il resto e' nell'elenco `non_importato`. I dati restano da verificare."""
        from .telematico.importa import XmlNonImportabile, importa_xml
        try:
            letto = importa_xml(xml)
        except XmlNonImportabile as e:
            raise DatiNonValidi(f"file non importabile: {e}") from None
        r = self.crea_pratica(titolo or letto["titolo"], autore=autore, canale=canale, iniziali=letto["operazioni"])
        return {**r, "importato": letto["importato"], "non_importato": letto["non_importato"], "avvisi": letto["avvisi"]}

    def elenca(self) -> list[dict]:
        # data del decesso del defunto (se indicata): serve all'interfaccia per mostrare il termine di presentazione
        def decesso(dati: str):
            try:
                p = next((x for x in json.loads(dati).get("persone", []) if x.get("ruolo") == "defunto"), {})
            except (ValueError, AttributeError):
                return None
            v = p.get("data_decesso")
            return v if isinstance(v, str) else None
        with self.arch.lettura() as c:
            return [{**{k: r[k] for k in ("id", "titolo", "creata", "aggiornata", "revisione")}, "data_decesso": decesso(r["dati"])}
                    for r in c.execute("SELECT id, titolo, creata, aggiornata, revisione, dati FROM pratiche ORDER BY aggiornata DESC")]

    def leggi(self, pratica_id: str, revisione: int | None = None) -> dict:
        with self.arch.lettura() as c:
            p = c.execute("SELECT * FROM pratiche WHERE id=?", (pratica_id,)).fetchone()
            if not p:
                raise NonTrovato("pratica inesistente", pratica_id=pratica_id)
            if revisione is None or revisione == p["revisione"]:
                dati, rev = json.loads(p["dati"]), p["revisione"]
            else:
                r = c.execute("SELECT dati FROM revisioni WHERE pratica_id=? AND n=?", (pratica_id, revisione)).fetchone()
                if not r:
                    raise NonTrovato("revisione inesistente", pratica_id=pratica_id, revisione=revisione)
                dati, rev = json.loads(r["dati"]), revisione
            return {"pratica_id": pratica_id, "titolo": p["titolo"], "revisione": rev,
                    "revisione_corrente": p["revisione"], "dati": dati,
                    "impronta_dichiarativa": impronta_dichiarativa(dati)}

    def revisioni(self, pratica_id: str) -> list[dict]:
        with self.arch.lettura() as c:
            return [dict(r) for r in c.execute(
                "SELECT n, ts, autore, canale, chiave, sommario FROM revisioni WHERE pratica_id=? ORDER BY n",
                (pratica_id,))]

    def differenze(self, pratica_id: str, da: int, a: int) -> list[str]:
        return diff_dati(self.leggi(pratica_id, da)["dati"], self.leggi(pratica_id, a)["dati"])

    # --------------------------------------------------------------- scrittura
    def aggiorna(self, pratica_id: str, revisione_attesa: int, operazioni: list[dict], *,
                 chiave: str | None = None, autore="utente", canale="gui",
                 origine: str | None = None) -> dict:
        self._canale(canale)
        origine = origine or ("proposto_assistente" if canale == "mcp" else "inserito")
        if origine not in V.ORIGINI:
            raise DatiNonValidi("origine non ammessa", ammesse=list(V.ORIGINI))
        impr = _impronta({"p": pratica_id, "r": revisione_attesa, "o": operazioni})
        with self.arch.transazione() as c:
            if chiave:
                prec = self._richiesta(c, chiave, "aggiorna", impr)
                if prec is not None:
                    return {**prec, "ripetuta": True}
            p = c.execute("SELECT * FROM pratiche WHERE id=?", (pratica_id,)).fetchone()
            if not p:
                raise NonTrovato("pratica inesistente", pratica_id=pratica_id)
            if p["revisione"] != revisione_attesa:
                succ = [dict(r) for r in c.execute(
                    "SELECT n, ts, autore, canale, sommario FROM revisioni WHERE pratica_id=? AND n>? ORDER BY n",
                    (pratica_id, revisione_attesa))]
                raise ConflittoRevisione(
                    f"la pratica e' alla revisione {p['revisione']}, attesa {revisione_attesa}: rileggere e riapplicare",
                    revisione_corrente=p["revisione"], revisione_attesa=revisione_attesa, modifiche_successive=succ)
            vecchi = json.loads(p["dati"])
            nuovi = copy.deepcopy(vecchi)
            for i, op in enumerate(operazioni):
                self._applica(nuovi, op, origine, canale, i)
            errori = S.valida_forma(nuovi)
            if errori:
                raise DatiNonValidi("dati non validi: nessuna modifica applicata",
                                    errori=[e.asdict() for e in errori])
            n = p["revisione"] + 1
            t = ora()
            sommario = "; ".join(diff_dati(vecchi, nuovi)[:20]) or "nessuna variazione"
            c.execute("UPDATE pratiche SET dati=?, revisione=?, aggiornata=? WHERE id=?",
                      (json.dumps(nuovi), n, t, pratica_id))
            c.execute("INSERT INTO revisioni VALUES(?,?,?,?,?,?,?,?)",
                      (pratica_id, n, t, autore, canale, chiave, sommario, json.dumps(nuovi)))
            risp = {"pratica_id": pratica_id, "revisione": n, "sommario": sommario}
            if chiave:
                c.execute("INSERT INTO richieste VALUES(?,?,?,?,?,?)",
                          (chiave, pratica_id, "aggiorna", impr, json.dumps(risp), t))
            return risp

    def ripristina_revisione(self, pratica_id: str, revisione_attesa: int, a_revisione: int, *,
                             autore="utente", canale="gui") -> dict:
        """Ripristino non distruttivo: crea una nuova revisione con i dati di quella richiesta."""
        snap = self.leggi(pratica_id, a_revisione)["dati"]
        with self.arch.transazione() as c:
            p = c.execute("SELECT revisione FROM pratiche WHERE id=?", (pratica_id,)).fetchone()
            if p["revisione"] != revisione_attesa:
                raise ConflittoRevisione("revisione obsoleta", revisione_corrente=p["revisione"],
                                         revisione_attesa=revisione_attesa)
            n, t = p["revisione"] + 1, ora()
            c.execute("UPDATE pratiche SET dati=?, revisione=?, aggiornata=? WHERE id=?",
                      (json.dumps(snap), n, t, pratica_id))
            c.execute("INSERT INTO revisioni VALUES(?,?,?,?,?,?,?,?)",
                      (pratica_id, n, t, autore, canale, None, f"ripristino dei dati della revisione {a_revisione}",
                       json.dumps(snap)))
            return {"pratica_id": pratica_id, "revisione": n}

    # ----------------------------------------------------------------- verifica
    def verifica(self, pratica_id: str) -> dict:
        d = self.leggi(pratica_id)
        errori = S.valida_forma(d["dati"]) + S.controlli_coerenza(d["dati"]) + Q.rilievi_quadri(d["dati"])
        from . import impostazioni
        pref = impostazioni.preferenze(self.arch.base)
        visure = Q.rilievi_visure(d["dati"], pref["avviso_visura_giorni"])
        avvisi = []
        if pref["visura_blocca"]:
            errori = errori + visure          # visura vecchia o senza data: rilievo bloccante
        else:
            avvisi = [x.asdict() for x in visure]   # solo avviso: non impedisce la finalizzazione
        blocchi = []
        e = self._job_ultimo("esporta_xml", pratica_id)
        if not (e and e["input"].get("impronta_dichiarativa") == d["impronta_dichiarativa"] and e["risultato"].get("completo")):
            blocchi.append({"codice": "FILE_XML_COMPLETO_NON_DISPONIBILE",
                            "messaggio": "il file XML completo non e' stato generato per i dati attuali: mancano quadri o casi non supportati, "
                                         "oppure l'esportazione non e' stata eseguita dopo l'ultima modifica"})
        return {"pratica_id": pratica_id, "revisione": d["revisione"],
                "impronta_dichiarativa": d["impronta_dichiarativa"],
                "versione_regole": VERSIONE_REGOLE,
                "ambito": "controlli interni di forma e coerenza; NON e' il controllo ufficiale",
                "esito": "ok" if not errori else "rilievi", "finalizzabile": not errori and not blocchi,
                "blocchi_finalizzazione": blocchi, "rilievi": [x.asdict() for x in errori], "avvisi": avvisi}

    def quadri(self, pratica_id: str) -> dict:
        """Stato di ciascun quadro (vuoto/compilato/rilievi/non supportato/inattivo) e rilievi per il pannello controlli."""
        v = self.verifica(pratica_id)
        d = self.leggi(pratica_id)
        rilievi = [{**r, "quadro": Q.quadro_per_percorso(d["dati"], r["percorso"])} for r in v["rilievi"]]
        return {"pratica_id": pratica_id, "revisione": d["revisione"], "quadri": Q.stato_quadri(d["dati"], v["rilievi"]),
                "esito": v["esito"], "finalizzabile": v["finalizzabile"], "blocchi_finalizzazione": v["blocchi_finalizzazione"],
                "rilievi": rilievi, "avvisi": v["avvisi"],
                "ambito": v["ambito"]}

    # ------------------------------------------------------------------ interni
    @staticmethod
    def _canale(canale):
        if canale not in CANALI:
            raise DatiNonValidi("canale non ammesso", ammessi=list(CANALI))

    @staticmethod
    def _richiesta(c, chiave, operazione, impr):
        r = c.execute("SELECT * FROM richieste WHERE chiave=?", (chiave,)).fetchone()
        if not r:
            return None
        if r["operazione"] != operazione or r["impronta"] != impr:
            raise ChiaveRiutilizzata("chiave di richiesta gia' usata con un contenuto diverso", chiave=chiave)
        return json.loads(r["risposta"])

    @staticmethod
    def _applica(dati: dict, op: dict, origine: str, canale: str, i: int):
        tipo = op.get("op")
        if tipo in ("upsert", "remove"):
            coll = op.get("coll")
            if coll not in S.COLLEZIONI:
                raise DatiNonValidi(f"operazione {i}: collezione sconosciuta", ammesse=list(S.COLLEZIONI))
            righe = dati.setdefault(coll, [])
            eid = op.get("id")
            if tipo == "remove":
                if not any(e["id"] == eid for e in righe):
                    raise NonTrovato(f"operazione {i}: elemento inesistente", coll=coll, id=eid)
                dati[coll] = [e for e in righe if e["id"] != eid]
                supplementi = dati.get("opzioni", {}).get("telematico", {}).get(coll, {})
                if isinstance(supplementi, dict):
                    supplementi.pop(eid, None)
                return
            if eid is None:
                eid = f"{PREFISSI[coll]}_{uuid.uuid4().hex[:8]}"
            elif not ID_VALIDO.match(eid):
                raise DatiNonValidi(f"operazione {i}: identificativo {eid!r} non valido: formato atteso da 1 a 4 lettere minuscole, "
                                  "un trattino basso e da 4 a 32 caratteri tra lettere minuscole e cifre (esempio p_a1b2c3d4)", id=eid)
            elemento = next((e for e in righe if e["id"] == eid), None)
            if elemento is None:
                elemento = {"id": eid, "_origine": {}}
                righe.append(elemento)
            for k, v in (op.get("campi") or {}).items():
                if k == "id" or k.startswith("_"):
                    raise DatiNonValidi(f"operazione {i}: il campo '{k}' e' riservato e non modificabile (identificativo e metadati di origine)", campo=k)
                if canale == "mcp" and elemento["_origine"].get(k) == "calcolato":
                    raise DatiNonValidi(f"operazione {i}: campo calcolato non modificabile da MCP", campo=k)
                if v is None:
                    elemento.pop(k, None)
                    elemento["_origine"].pop(k, None)
                else:
                    elemento[k] = v
                    elemento["_origine"][k] = origine
        elif tipo == "set":
            sez = op.get("sezione")
            if sez not in S.SEZIONI:
                raise DatiNonValidi(f"operazione {i}: sezione sconosciuta", ammesse=list(S.SEZIONI))
            for k, v in (op.get("campi") or {}).items():
                if v is None:
                    dati.setdefault(sez, {}).pop(k, None)
                else:
                    dati.setdefault(sez, {})[k] = v
        else:
            raise DatiNonValidi(f"operazione {i}: 'op' deve essere upsert, remove o set")
