"""File elaborati di una pratica: esportazione XML, validazione di schema, controllo ufficiale e loro stato.

Dimensioni separate (specifica §10): export, validazione di schema, controllo ufficiale. Ognuna conserva l'impronta dei dati
dichiarativi su cui e' stata calcolata: se cambia il dichiarato diventa 'obsoleta'; una nota interna non la invalida.
Nessuna trasmissione avviene qui.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

from .errori import DatiNonValidi, ErroreServizio, ora

TIPO_EXPORT = "esporta_xml"
TIPO_CONTROLLO = "controllo_pratica"
SCOPI = ("completo", "bozza_tecnica")


class ElaboratiMixin:
    def file_export(self, pratica_id: str, job_id: str | None = None) -> tuple[bytes, dict]:
        """Legge una versione precisa, verificandone appartenenza e integrita'."""
        self.leggi(pratica_id)
        if job_id:
            with self.arch.lettura() as c:
                r = c.execute("SELECT * FROM job WHERE id=? AND tipo=? AND pratica_id=?",
                              (job_id, TIPO_EXPORT, pratica_id)).fetchone()
            if not r:
                raise DatiNonValidi("esportazione non appartenente alla pratica")
            j = dict(r); j["risultato"] = json.loads(j["risultato"]); j["input"] = json.loads(j["input"])
        else:
            j = self._job_ultimo(TIPO_EXPORT, pratica_id)
        if not j or not j["risultato"].get("generato"):
            raise DatiNonValidi("nessun file XML disponibile: genera prima il file")
        r = j["risultato"]
        p = (self.arch.base / r["percorso"]).resolve()
        if not p.is_relative_to((self.arch.base / "elaborati").resolve()) or not p.is_file():
            raise DatiNonValidi("file XML non disponibile")
        xml = p.read_bytes()
        if hashlib.sha256(xml).hexdigest() != r["xml_sha256"]:
            raise DatiNonValidi("file XML alterato: rigenera l'esportazione")
        return xml, j

    # ------------------------------------------------------------------ persistenza (tabella job)
    def _job_scrivi(self, tipo: str, pratica_id: str, stato: str, inp: dict, ris: dict) -> str:
        jid = "jb_" + uuid.uuid4().hex[:12]
        t = ora()
        with self.arch.transazione() as c:
            c.execute("INSERT INTO job(id,tipo,pratica_id,stato,input,risultato,errore,creato,aggiornato) VALUES(?,?,?,?,?,?,?,?,?)",
                      (jid, tipo, pratica_id, stato, json.dumps(inp), json.dumps(ris), None, t, t))
        return jid

    def _job_ultimo(self, tipo: str, pratica_id: str) -> dict | None:
        with self.arch.lettura() as c:
            r = c.execute("SELECT * FROM job WHERE tipo=? AND pratica_id=? ORDER BY creato DESC, rowid DESC LIMIT 1",
                          (tipo, pratica_id)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["input"] = json.loads(d["input"] or "{}")
        d["risultato"] = json.loads(d["risultato"] or "{}")
        return d

    # ------------------------------------------------------------------ esportazione
    def esporta(self, pratica_id: str, *, cf_fornitore: str | None = None, tipo_fornitore: str | None = None,
                scopo: str = "completo") -> dict:
        """Genera l'XML dalla pratica, lo valida sullo schema e conserva il file. `completo` non produce mai un XML parziale."""
        from .telematico.esporta import ContestoExport, esporta_xml
        from .telematico.xsd import valida_xsd
        if scopo not in SCOPI:
            raise DatiNonValidi("scopo non ammesso", ammessi=list(SCOPI))
        d = self.leggi(pratica_id)
        forn = (d["dati"].get("opzioni", {}) or {}).get("fornitore", {}) or {}
        cf = (cf_fornitore or forn.get("cf") or "").strip().upper()
        if not cf:
            raise DatiNonValidi("manca il codice fiscale del fornitore (intermediario o dichiarante): indicalo nel profilo",
                                campo="opzioni.fornitore.cf")
        tipo = str(tipo_fornitore or forn.get("tipo") or "1")
        es = esporta_xml(d["dati"], ContestoExport(
            cf_fornitore=cf, tipo_fornitore=tipo, scopo=scopo,
            allegati=self._allegati_export(pratica_id, d["dati"]),
            impegno_codice=forn.get("impegno_codice"), data_impegno=forn.get("data_impegno")))
        xsd_errori = [e.asdict() for e in valida_xsd(es.xml)] if es.xml is not None else []
        percorso = sha = None
        if es.xml is not None:
            sha = hashlib.sha256(es.xml).hexdigest()
            cart = self.arch.base / "elaborati" / pratica_id
            cart.mkdir(parents=True, exist_ok=True)
            p = cart / f"{sha[:16]}.xml"
            if not p.exists():
                p.write_bytes(es.xml)
            percorso = p.relative_to(self.arch.base).as_posix()
        ris = {"generato": es.xml is not None, "completo": es.completo, "scopo": scopo, "xml_sha256": sha, "percorso": percorso,
               "errori": [e.asdict() for e in es.errori], "non_supportato": list(es.non_supportato),
               "avvisi": [e.asdict() for e in es.avvisi],
               "quadri_mancanti": [e.asdict() for e in es.quadri_mancanti], "xsd_errori": xsd_errori,
               "versione": es.versione, "ambito": es.ambito}
        inp = {"impronta_dichiarativa": d["impronta_dichiarativa"], "revisione": d["revisione"], "scopo": scopo,
               "cf_fornitore": cf, "tipo_fornitore": tipo}
        jid = self._job_scrivi(TIPO_EXPORT, pratica_id, "completato", inp, ris)
        return {"pratica_id": pratica_id, "job_id": jid, **ris,
                "avvertenza": (None if es.completo else
                               "Il file NON è una dichiarazione completa e non è trasmissibile: serve solo ai controlli tecnici.")
                if es.xml is not None else None}

    def _allegati_export(self, pratica_id: str, dati: dict) -> dict:
        """Solo documenti della pratica e byte integri del deposito, mai percorsi forniti dal client."""
        richiesti = {r.get("allegato_id") for r in dati.get("documenti_ref", [])}
        out = {}
        radice = (self.arch.base / "allegati").resolve()
        with self.arch.lettura() as c:
            righe = c.execute("SELECT * FROM allegati WHERE pratica_id=?", (pratica_id,)).fetchall()
        for r in righe:
            if r["id"] not in richiesti:
                continue
            p = (self.arch.base / r["percorso"]).resolve()
            if not p.is_relative_to(radice) or not p.is_file():
                # Il modulo restituisce ALLEGATO_NON_DISPONIBILE sul riferimento originale.
                continue
            if p.stat().st_size != r["bytes"] or hashlib.sha256(p.read_bytes()).hexdigest() != r["sha256"]:
                raise DatiNonValidi("allegato alterato: impronta o dimensione diversa dal file acquisito",
                                    allegato_id=r["id"])
            out[r["id"]] = {"percorso": p, "nome": r["nome"]}
        return out

    # ------------------------------------------------------------------ controllo ufficiale
    def controllo_ufficiale_pratica(self, pratica_id: str, *, chiave: str | None = None) -> dict:
        """Esegue il controllo ufficiale sul file esportato corrente (se Java e componenti sono configurati; altrimenti
        passaggio manuale tracciato). Un esito su file di bozza tecnica resta marcato come tale."""
        from .collegamenti.controllo import TIPO_JOB, controllo_ufficiale
        st = self.stato_elaborati(pratica_id)
        exp = st["export"]
        if exp["stato"] != "aggiornato" or not exp.get("percorso"):
            raise DatiNonValidi("genera prima il file aggiornato: i dati sono cambiati o il file non è stato generato",
                                stato_export=exp["stato"])
        j = self._job_ultimo(TIPO_EXPORT, pratica_id)
        xml_path = self.arch.base / exp["percorso"]
        adattatore = controllo_ufficiale(self.arch)
        r = adattatore.esegui(xml_path, chiave=chiave, pratica_id=pratica_id,
                             revisione=j["input"]["revisione"],
                             impronta_dichiarativa=j["input"]["impronta_dichiarativa"])
        det = r.dettaglio or {}
        reg = adattatore.job.leggi(r.job_id, TIPO_JOB)["risultato"] if r.job_id else {}   # dettagli registrati dall'adattatore
        ris = {"esito": r.esito.value, "stato_controllo": det.get("stato_controllo", "non_eseguito"),
               "versione_controllo": reg.get("versione_controllo"), "data_versione": reg.get("data_versione"),
               "job_adattatore": r.job_id, "azione_richiesta": r.azione_richiesta,
               "riepilogo": reg.get("riepilogo"), "motivi": reg.get("motivi"),
               "bozza_tecnica": exp.get("scopo") == "bozza_tecnica", "modalita": reg.get("modalita")}
        inp = {"xml_sha256": exp["xml_sha256"], "impronta_dichiarativa": j["input"]["impronta_dichiarativa"]}
        jid = self._job_scrivi(TIPO_CONTROLLO, pratica_id, "completato", inp, ris)
        return {"pratica_id": pratica_id, "job_id": jid, **ris}

    # ------------------------------------------------------------------ stato
    def stato_elaborati(self, pratica_id: str) -> dict:
        d = self.leggi(pratica_id)
        imp = d["impronta_dichiarativa"]
        e = self._job_ultimo(TIPO_EXPORT, pratica_id)
        if not e:
            export = {"stato": "non_eseguito"}
        else:
            r = e["risultato"]
            export = {"stato": "aggiornato" if e["input"].get("impronta_dichiarativa") == imp else "obsoleto",
                      "job_id": e["id"], "generato": r.get("generato"), "completo": r.get("completo"), "scopo": r.get("scopo"),
                      "xml_sha256": r.get("xml_sha256"), "percorso": r.get("percorso"), "revisione": e["input"].get("revisione"),
                      "n_errori": len(r.get("errori", [])), "non_supportato": r.get("non_supportato", []),
                      "quadri_mancanti": [x["percorso"] for x in r.get("quadri_mancanti", [])]}
        xsd = {"stato": "non_eseguito"}
        if e and e["risultato"].get("generato"):
            n = len(e["risultato"].get("xsd_errori", []))
            xsd = {"stato": ("obsoleto" if export["stato"] == "obsoleto" else ("valido" if n == 0 else "non_valido")), "n_errori": n}
        c = self._job_ultimo(TIPO_CONTROLLO, pratica_id)
        if not c:
            ctl = {"stato": "non_eseguito"}
        else:
            r = c["risultato"]
            corrente = (export.get("stato") == "aggiornato" and c["input"].get("xml_sha256") == export.get("xml_sha256"))
            ctl = {"stato": r.get("stato_controllo") if corrente else "obsoleto", "ultimo_esito_registrato": r.get("stato_controllo"),
                   "parola_esito": r.get("esito"), "versione_controllo": r.get("versione_controllo"),
                   "bozza_tecnica": r.get("bozza_tecnica"), "job_id": c["id"], "job_adattatore": r.get("job_adattatore"),
                   "azione_richiesta": r.get("azione_richiesta") if corrente else None}
        ver = self.verifica(pratica_id)
        invio = self.invio_stato(pratica_id)["copie"]
        trasmissione = {"stato": "non_preparata", "nota": "invio reale manuale con strumenti ufficiali"}
        if invio:
            copia = invio[0]
            trasmissione.update(stato=copia["stato"], modalita=copia["dettaglio"].get("modalita"))
            if trasmissione["modalita"] == "simulata":
                trasmissione["nota"] = "PROVA SIMULATA: nessun invio all'Agenzia"
        return {"pratica_id": pratica_id, "revisione": d["revisione"], "impronta_dichiarativa": imp,
                "dati": {"stato": "senza_rilievi" if ver["esito"] == "ok" else "con_rilievi", "rilievi": len(ver["rilievi"])},
                "export": export, "xsd": xsd, "controllo_ufficiale": ctl,
                "trasmissione": trasmissione,
                "ambito": "stati separati; il controllo ufficiale locale non sostituisce la verifica con i servizi dell'Agenzia"}
