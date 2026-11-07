"""File elaborati di una pratica: esportazione XML, validazione di schema, controllo ufficiale e loro stato.

Dimensioni separate (specifica §10): export, validazione di schema, controllo ufficiale. Ognuna conserva l'impronta dei dati
dichiarativi su cui e' stata calcolata: se cambia il dichiarato diventa 'obsoleta'; una nota interna non la invalida.
Nessuna trasmissione avviene qui.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid

from .errori import DatiNonValidi, ErroreServizio, ora

TIPO_EXPORT = "esporta_xml"
TIPO_CONTROLLO = "controllo_pratica"
TIPO_STAMPA = "stampa_modello"
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
        from . import backup_archivio as BK
        from .versioni import versioni
        backup = BK.automatico_se_serve(self.arch, "prima-export")   # copia di sicurezza prima di generare (max una ogni 30 min)
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
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != sha:
                # assente o alterato: ripristina atomicamente i byte generati (nome temporaneo univoco: due esportazioni
                # contemporanee GUI e MCP dello stesso contenuto non scrivono sullo stesso file temporaneo)
                tmp = p.with_name(f"{p.name}.{uuid.uuid4().hex}.tmp")
                try:
                    tmp.write_bytes(es.xml)
                    for prova in range(20):      # Windows: sostituzione contemporanea dello stesso file -> accesso negato
                        try:
                            os.replace(tmp, p)
                            break
                        except PermissionError:
                            if prova == 19:
                                raise
                            import time
                            time.sleep(0.05)
                finally:
                    tmp.unlink(missing_ok=True)
            percorso = p.relative_to(self.arch.base).as_posix()
        ris = {"generato": es.xml is not None, "completo": es.completo, "scopo": scopo, "xml_sha256": sha, "percorso": percorso,
               "errori": [e.asdict() for e in es.errori], "non_supportato": list(es.non_supportato),
               "avvisi": [e.asdict() for e in es.avvisi],
               "quadri_mancanti": [e.asdict() for e in es.quadri_mancanti], "xsd_errori": xsd_errori,
               "versione": es.versione, "ambito": es.ambito, "versioni": versioni()}
        inp = {"impronta_dichiarativa": d["impronta_dichiarativa"], "revisione": d["revisione"], "scopo": scopo,
               "cf_fornitore": cf, "tipo_fornitore": tipo}
        jid = self._job_scrivi(TIPO_EXPORT, pratica_id, "completato", inp, ris)
        return {"pratica_id": pratica_id, "job_id": jid, **ris, "backup": backup,
                "avvertenza": (None if es.completo else
                               "Il file NON è una dichiarazione completa e non è trasmissibile: serve solo ai controlli tecnici.")
                if es.xml is not None else None}

    def anteprima_quadri(self, pratica_id: str) -> dict:
        """Quadri EE, EF ed EH come li scriverebbe la generazione del file, per vederli a video (nessun file salvato, nessun job).
        Fornitore: quello del profilo; se manca, il presentatore (tipo 1). Con l'intermediario senza impegno si usa un impegno
        provvisorio solo per l'anteprima."""
        from datetime import date
        from lxml import etree
        from . import prospetto_cliente as PC
        from .telematico.esporta import ContestoExport, esporta_xml
        d = self.leggi(pratica_id)
        dati = d["dati"]
        forn = (dati.get("opzioni", {}) or {}).get("fornitore", {}) or {}
        pres_id = (((dati.get("opzioni") or {}).get("telematico") or {}).get("dichiarazione") or {}).get("presentatore", {}).get("persona_id")
        persone = {p.get("id"): p for p in dati.get("persone", [])}
        cf_pres = (persone.get(pres_id) or next((p for p in dati.get("persone", []) if p.get("ruolo") == "presentatore"), {})).get("codice_fiscale")
        cf = (forn.get("cf") or cf_pres or next((p.get("codice_fiscale") for p in dati.get("persone", []) if p.get("ruolo") == "defunto"), "")
              or "").strip().upper()
        tipo = str(forn.get("tipo") or "1") if forn.get("cf") else "1"
        imp, dimp = forn.get("impegno_codice"), forn.get("data_impegno")
        if tipo == "10" and not (imp and dimp):
            imp, dimp = "1", date.today().isoformat()
        out: dict = {"pratica_id": pratica_id, "revisione": d["revisione"], "ee": [], "ef": None, "eh": [], "eg": [],
                     "errori": [], "mancanti": [], "avvisi": []}
        if not cf:
            out["errori"].append("manca un codice fiscale (fornitore, presentatore o defunto) per calcolare l'anteprima")
            return out
        try:
            es = esporta_xml(dati, ContestoExport(cf_fornitore=cf, tipo_fornitore=tipo, scopo="bozza_tecnica",
                                                  allegati=self._allegati_export(pratica_id, dati),
                                                  impegno_codice=imp if tipo == "10" else None,
                                                  data_impegno=dimp if tipo == "10" else None))
        except Exception as e:          # l'anteprima non deve mai impedire il lavoro: si mostra il motivo
            out["errori"].append(f"anteprima non calcolabile: {e}")
            return out
        out["errori"] = [e.messaggio for e in es.errori] + list(es.non_supportato)
        out["mancanti"] = [m.messaggio for m in es.quadri_mancanti]
        out["avvisi"] = [a.messaggio for a in es.avvisi]
        if es.xml is None:
            # i quadri EF/EG/EH bloccati (es. IBAN mancante) non devono nascondere il riepilogo EE: secondo calcolo senza di essi
            try:
                es = esporta_xml(dati, ContestoExport(cf_fornitore=cf, tipo_fornitore=tipo, scopo="bozza_tecnica",
                                                      quadri_liquidazione=False,
                                                      impegno_codice=imp if tipo == "10" else None,
                                                      data_impegno=dimp if tipo == "10" else None))
            except Exception:
                return out
            if es.xml is None:
                return out
            out["solo_ee"] = True
        root = etree.fromstring(es.xml, etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True))
        loc = lambda e: etree.QName(e).localname if isinstance(e.tag, str) else ""    # noqa: E731
        for q in root.iter():
            if loc(q) == "QuadroEE":
                out["ee"] = [{"campo": loc(e), "valore": e.text.strip()} for e in q.iter() if len(e) == 0 and (e.text or "").strip()]
            elif loc(q) == "QuadroEH":
                for e in q.iter():
                    if len(e) == 0 and (e.text or "").strip() and loc(e).startswith(("Flag", "Presenza")):
                        sez = next((loc(a) for a in e.iterancestors() if loc(a).startswith("Sezione")), "")
                        out["eh"].append({"sezione": sez, "campo": loc(e), "gruppo": loc(e.getparent())})
            elif loc(q) == "QuadroEG":
                for g in q:
                    nomi = [c.text.strip() for a in g if loc(a).endswith("All") for c in a
                            if loc(c) == "FileName" and (c.text or "").strip()]
                    out["eg"].append({"rigo": loc(g), "file": nomi})
        if out.get("solo_ee"):
            return out
        lettura = PC.leggi(es.xml)
        out["ef"] = {"imposte": [[k, str(v)] for k, v in lettura["imposte"]], "totale": str(lettura["totale_ef"] or ""),
                     "importo_da_versare": str(lettura["importo_da_versare"] or "")}
        return out

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
            # il rapporto salvato (esito veraPDF) arriva all'export: un PDF/A non conforme blocca il file completo
            out[r["id"]] = {"percorso": p, "nome": r["nome"], "rapporto": r["rapporto"]}
        return out

    # ------------------------------------------------------------------ backup
    def backup_archivio(self, motivo: str = "manuale") -> dict:
        """Copia verificata di database, allegati ed elaborati nella cartella dei backup."""
        from . import backup_archivio as BK
        return BK.crea(self.arch, motivo)

    def elenco_backup(self) -> dict:
        from . import backup_archivio as BK
        return {"cartella": str(BK.cartella_backup(self.arch)), "backup": BK.elenco(self.arch)}

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
        from .collegamenti.controllo import ControlloJar
        # Con il componente reale si chiede sempre il file controllato (.dcm): senza, il componente cancella la copia di lavoro
        # anche a controllo positivo (prova generale del 2026-11-05) e il risultato sembrerebbe un'alterazione dell'input.
        extra = {"produci_dcm": True} if isinstance(adattatore, ControlloJar) else {}
        inp = {"xml_sha256": exp["xml_sha256"], "impronta_dichiarativa": j["input"]["impronta_dichiarativa"]}
        bozza = exp.get("scopo") == "bozza_tecnica"
        try:
            r = adattatore.esegui(xml_path, chiave=chiave, pratica_id=pratica_id,
                                 revisione=j["input"]["revisione"],
                                 impronta_dichiarativa=j["input"]["impronta_dichiarativa"], **extra)
        except Exception as e:
            # Il record della pratica si scrive sempre: lo stato mostra un controllo non concluso, non quello precedente.
            motivo = str(getattr(e, "messaggio", None) or f"{type(e).__name__}: {e}")[:300]
            ris = {"esito": "fallito" if isinstance(adattatore, ControlloJar) else "da_collaudare",
                   "stato_controllo": "non_verificabile", "versione_controllo": None, "data_versione": None,
                   "job_adattatore": None, "azione_richiesta": "Controllo ufficiale non concluso: " + motivo
                   + ". Rieseguire il controllo.", "riepilogo": None, "motivi": [motivo],
                   "bozza_tecnica": bozza, "modalita": None, "errore": motivo}
            self._job_scrivi(TIPO_CONTROLLO, pratica_id, "errore", inp, ris)
            raise ErroreServizio("controllo ufficiale non concluso: " + motivo) from None
        ris = self._ris_controllo(r.job_id, r.esito.value, (r.dettaglio or {}).get("stato_controllo", "non_eseguito"),
                                  r.azione_richiesta, bozza)
        prec = self._job_ultimo(TIPO_CONTROLLO, pratica_id)
        if (prec and r.job_id and prec["risultato"].get("job_adattatore") == r.job_id
                and prec["input"].get("xml_sha256") == inp["xml_sha256"]):
            jid = prec["id"]     # stesso passaggio manuale ancora aperto: nessun record duplicato
        else:
            jid = self._job_scrivi(TIPO_CONTROLLO, pratica_id, "completato", inp, ris)
        from .pulizia import pulisci_silenziosa
        pulisci_silenziosa(self.arch.base)           # temporanei vecchi: mai causa di fallimento del controllo
        return {"pratica_id": pratica_id, "job_id": jid, **ris}

    def _ris_controllo(self, job_adattatore: str | None, esito: str, stato: str, azione: str | None, bozza) -> dict:
        from .collegamenti.base import RegistroJob
        from .collegamenti.controllo import TIPO_JOB
        reg = RegistroJob(self.arch).leggi(job_adattatore, TIPO_JOB)["risultato"] if job_adattatore else {}
        return {"esito": esito, "stato_controllo": stato,
                "versione_controllo": reg.get("versione_controllo"), "data_versione": reg.get("data_versione"),
                "job_adattatore": job_adattatore, "azione_richiesta": azione,
                "riepilogo": reg.get("riepilogo"), "motivi": reg.get("motivi"),
                "bozza_tecnica": bozza, "modalita": reg.get("modalita")}

    def registra_diagnostico_controllo(self, pratica_id: str, *, dgn: bytes, log_schema: bytes, wri: bytes | None = None,
                                       ambiente_dichiarato: dict | None = None, conferma_associazione: bool = False,
                                       job_adattatore: str | None = None) -> dict:
        """Chiude il passaggio manuale del controllo ufficiale con i file ORIGINALI prodotti dall'utente (Desktop Telematico
        o ControlliSUC13): `.dgn` e `_logSchema.xml` obbligatori, `.wri` facoltativo. Il diagnostico e' accettato solo se
        riferibile al file controllato; un nome che indica un altro file o un'altra revisione, o un rapporto .wri datato
        prima della prima esportazione di questi byte, e' rifiutato. Codice fiscale e identificativo non bastano: se il nome
        nel .dgn non e' fra quelli noti serve `conferma_associazione` (dichiarazione dell'utente); senza alcun riscontro nel
        contenuto l'esito resta 'da_collaudare' e non sblocca l'invio."""
        from .collegamenti.base import RegistroJob
        from .collegamenti.controllo import TIPO_JOB, ControlloManuale
        st = self.stato_elaborati(pratica_id)
        ctl, exp = st["controllo_ufficiale"], st["export"]
        jid = job_adattatore or ctl.get("job_adattatore")
        if not jid:
            raise DatiNonValidi("nessun controllo ufficiale in attesa del diagnostico: avvia prima il controllo")
        for nome, b in (("dgn", dgn), ("_logSchema.xml", log_schema), ("wri", wri)):
            if b is not None and len(b) > 20_000_000:
                raise DatiNonValidi(f"file {nome} oltre 20 MB")
        j = RegistroJob(self.arch).leggi(jid, TIPO_JOB)
        if j["pratica_id"] != pratica_id:
            raise DatiNonValidi("il controllo indicato appartiene a un'altra pratica")
        if exp.get("stato") != "aggiornato" or j["input"].get("xml_sha256") != exp.get("xml_sha256"):
            raise DatiNonValidi("il controllo in attesa riguarda un file non piu' corrente: rigenera il file e riavvia il "
                                "controllo", stato_export=exp.get("stato"))
        if j["stato"] != "attesa_diagnostico":
            raise DatiNonValidi(f"il controllo {jid} non e' in attesa del diagnostico (stato {j['stato']})")
        ControlloManuale(self.arch).registra_diagnostico(
            jid, dgn=dgn, log_schema=log_schema, wri=wri, ambiente_dichiarato=ambiente_dichiarato,
            conferma_associazione=conferma_associazione,
            non_prima_di=self._prima_esportazione(pratica_id, exp.get("xml_sha256")) or j.get("creato"))
        return {"pratica_id": pratica_id, **self.stato_elaborati(pratica_id)["controllo_ufficiale"]}

    def _prima_esportazione(self, pratica_id: str, sha: str | None) -> str | None:
        """Istante della prima esportazione che ha prodotto esattamente questi byte (stessa impronta)."""
        if not sha:
            return None
        with self.arch.lettura() as c:
            righe = c.execute("SELECT creato, risultato FROM job WHERE tipo=? AND pratica_id=?",
                              (TIPO_EXPORT, pratica_id)).fetchall()
        date = [r["creato"] for r in righe if json.loads(r["risultato"] or "{}").get("xml_sha256") == sha]
        return min(date) if date else None

    def file_controllato_dcm(self, pratica_id: str) -> tuple[bytes, dict]:
        """File controllato (.dcm) prodotto dal componente ufficiale per l'export corrente, se il controllo e' positivo."""
        from .collegamenti.base import DepositoArtefatti
        from .collegamenti.controllo import TIPO_JOB, controllo_ufficiale
        st = self.stato_elaborati(pratica_id)
        ctl = st["controllo_ufficiale"]
        if ctl.get("stato") != "positivo" or not ctl.get("job_adattatore"):
            raise DatiNonValidi("nessun file controllato disponibile: serve un controllo ufficiale positivo sul file aggiornato",
                                stato_controllo=ctl.get("stato"))
        ad = controllo_ufficiale(self.arch)
        reg = ad.job.leggi(ctl["job_adattatore"], TIPO_JOB)["risultato"]
        art = next((a for a in reg.get("artefatti", []) if a.get("ruolo") == "file_controllato_dcm"), None)
        if art is None:
            raise DatiNonValidi("il controllo non ha prodotto il file controllato (.dcm): riesegui il controllo ufficiale")
        return DepositoArtefatti(self.arch).leggi(art), {"job": ctl["job_adattatore"], "nome": art.get("nome")}

    # ------------------------------------------------------------------ stampa del modello ministeriale
    def stampa_modello(self, pratica_id: str) -> dict:
        """PDF del modello ministeriale compilato dallo STESSO XML del file telematico completo e aggiornato (codice di stampa
        del componente ufficiale, locale). Non e' una verifica con l'Agenzia ne' una firma."""
        from .collegamenti import stampa as ST
        exp = self.stato_elaborati(pratica_id)["export"]
        if exp.get("stato") != "aggiornato" or not exp.get("generato") or not exp.get("completo"):
            raise DatiNonValidi("la stampa del modello richiede un file XML completo e aggiornato: genera prima il file",
                                stato_export=exp.get("stato"), completo=exp.get("completo"))
        xml, _ = self.file_export(pratica_id, exp["job_id"])
        r = ST.genera(xml)
        sha = hashlib.sha256(r.pdf).hexdigest()
        cart = self.arch.base / "elaborati" / pratica_id
        cart.mkdir(parents=True, exist_ok=True)
        p = cart / f"modello_{sha[:16]}.pdf"
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != sha:
            tmp = p.with_name(f"{p.name}.{uuid.uuid4().hex}.tmp")   # nome univoco (stampe contemporanee)
            try:
                tmp.write_bytes(r.pdf)
                for prova in range(20):          # Windows: sostituzione contemporanea dello stesso file -> accesso negato
                    try:
                        os.replace(tmp, p)
                        break
                    except PermissionError:
                        if prova == 19:
                            raise
                        import time
                        time.sleep(0.05)
            finally:
                tmp.unlink(missing_ok=True)
        ris = {"generato": True, "pdf_sha256": sha, "percorso": p.relative_to(self.arch.base).as_posix(), "pagine": r.pagine,
               "fonte": ST.FONTE,
               "ambito": "prova locale con il codice di stampa del componente ufficiale; non e' una verifica con l'Agenzia, "
                         "la fedelta' visiva va controllata per i quadri usati; gli allegati EG compaiono come flag"}
        inp = {"xml_sha256": exp["xml_sha256"], "impronta_dichiarativa": self.leggi(pratica_id)["impronta_dichiarativa"]}
        jid = self._job_scrivi(TIPO_STAMPA, pratica_id, "completato", inp, ris)
        from .pulizia import pulisci_silenziosa
        pulisci_silenziosa(self.arch.base)
        return {"pratica_id": pratica_id, "job_id": jid, **ris}

    def file_stampa_modello(self, pratica_id: str) -> tuple[bytes, dict]:
        self.leggi(pratica_id)
        j = self._job_ultimo(TIPO_STAMPA, pratica_id)
        if not j or not j["risultato"].get("generato"):
            raise DatiNonValidi("nessuna stampa del modello disponibile: generala prima")
        r = j["risultato"]
        p = (self.arch.base / r["percorso"]).resolve()
        if not p.is_relative_to((self.arch.base / "elaborati").resolve()) or not p.is_file():
            raise DatiNonValidi("file della stampa non disponibile")
        pdf = p.read_bytes()
        if hashlib.sha256(pdf).hexdigest() != r["pdf_sha256"]:
            raise DatiNonValidi("file della stampa alterato: rigenera la stampa")
        return pdf, j

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
                      "versioni": r.get("versioni"),
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
            r = dict(c["risultato"])
            if r.get("job_adattatore"):   # stato ATTUALE del job dell'adattatore (es. diagnostico registrato dopo)
                from .collegamenti.base import RegistroJob
                from .collegamenti.controllo import TIPO_JOB
                try:
                    ja = RegistroJob(self.arch).leggi(r["job_adattatore"], TIPO_JOB)
                except ErroreServizio:
                    ja = None
                if ja is not None:
                    ra = ja["risultato"]
                    r.update(stato_controllo=ra.get("stato_controllo", r.get("stato_controllo")),
                             esito=ra.get("esito", r.get("esito")), azione_richiesta=ra.get("azione_richiesta"),
                             versione_controllo=ra.get("versione_controllo") or r.get("versione_controllo"),
                             stato_job=ja["stato"], modalita=ra.get("modalita") or r.get("modalita"))
            corrente = (export.get("stato") == "aggiornato" and c["input"].get("xml_sha256") == export.get("xml_sha256"))
            ctl = {"stato_job": r.get("stato_job"), "modalita": r.get("modalita"), "stato": r.get("stato_controllo") if corrente else "obsoleto", "ultimo_esito_registrato": r.get("stato_controllo"),
                   "parola_esito": r.get("esito"), "versione_controllo": r.get("versione_controllo"),
                   "bozza_tecnica": r.get("bozza_tecnica"), "job_id": c["id"], "job_adattatore": r.get("job_adattatore"),
                   "azione_richiesta": r.get("azione_richiesta") if corrente else None}
        s = self._job_ultimo(TIPO_STAMPA, pratica_id)
        if not s:
            stampa = {"stato": "non_eseguita"}
        else:
            corrente = export.get("stato") == "aggiornato" and s["input"].get("xml_sha256") == export.get("xml_sha256")
            stampa = {"stato": "aggiornata" if corrente else "obsoleta", "job_id": s["id"], "pagine": s["risultato"].get("pagine"),
                      "pdf_sha256": s["risultato"].get("pdf_sha256")}
        ver = self.verifica(pratica_id)
        stato_invio = self.invio_stato(pratica_id)
        invio = stato_invio["copie"]
        trasmissione = {"stato": "non_preparata", "nota": "invio reale manuale con strumenti ufficiali"}
        if invio:
            # La copia da mostrare e' quella con un invio aperto o gia' trasmesso (anche se non e' la piu' recente):
            # un tentativo in corso non deve mai sparire dalla vista.
            copia = next((x for x in invio if x["job_id"] == stato_invio.get("copia_attiva")), invio[0])
            trasmissione.update(stato=copia["stato"], modalita=copia["dettaglio"].get("modalita"),
                                copia_id=copia["job_id"], copie=len(invio),
                                tentativo_aperto=stato_invio.get("tentativo_aperto"))
            corr = next((t for t in copia.get("tentativi", [])
                         if t["dettaglio"].get("job_id") == copia["dettaglio"].get("tentativo_corrente")), None)
            if corr is not None:
                trasmissione.update(tentativo=corr["dettaglio"].get("job_id"), tentativo_stato=corr["dettaglio"].get("stato"),
                                    protocollo=corr["dettaglio"].get("protocollo"))
            if stato_invio.get("tentativo_aperto"):
                ta = stato_invio["tentativo_aperto"]
                trasmissione["nota"] = (f"invio da riconciliare (tentativo {ta['job_id']}, stato {ta['stato']}): "
                                        "registra l'esito prima di qualunque altra copia")
            if trasmissione["modalita"] == "simulata":
                trasmissione["nota"] = "PROVA SIMULATA: nessun invio all'Agenzia"
            if copia.get("prove"):   # prove simulate sulla copia reale: separate, non cambiano lo stato della copia
                u = copia["prove"][-1]["dettaglio"]
                trasmissione["prova_simulata"] = {
                    "tentativo": u.get("job_id"), "stato": u.get("stato"), "protocollo_fittizio": u.get("protocollo"),
                    "numero": len(copia["prove"]), "esito": "simulazione",
                    "nota": "PROVA SIMULATA: nessun invio all'Agenzia; la copia reale resta da inviare"}
        return {"pratica_id": pratica_id, "revisione": d["revisione"], "impronta_dichiarativa": imp,
                "dati": {"stato": "senza_rilievi" if ver["esito"] == "ok" else "con_rilievi", "rilievi": len(ver["rilievi"])},
                "export": export, "xsd": xsd, "controllo_ufficiale": ctl, "stampa_modello": stampa,
                "trasmissione": trasmissione,
                "ambito": "stati separati; il controllo ufficiale locale non sostituisce la verifica con i servizi dell'Agenzia"}
