"""Allegati: originale e derivati conservati insieme, con analisi e rapporto di validazione.

Flusso (specifica par. 7): acquisisci originale -> rileva formato, firme, protezioni -> conserva se gia' conforme
(solo con validatore indipendente) oppure crea il derivato PDF/A -> valida -> controlla pagine, testo, dimensioni ->
riduci o suddividi se oltre il limite. L'originale non viene mai modificato.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path

from . import pdfa
from .errori import DatiNonValidi, NonTrovato, ora


class AllegatiMixin:
    @property
    def cartella_ingresso(self) -> Path:
        d = self.arch.base / "ingresso"
        d.mkdir(exist_ok=True)
        return d

    def _registra(self, c, pratica_id, nome, percorso_tmp: Path, ruolo, origine_id, tipo_eg, finalita, persona_id,
                  analisi, rapporto=None) -> dict:
        h = hashlib.sha256(percorso_tmp.read_bytes()).hexdigest()
        dest = self.arch.percorso_allegato(h)
        self._scrivi_nel_deposito(percorso_tmp, dest, h)
        aid = "al_" + uuid.uuid4().hex[:12]
        c.execute("INSERT INTO allegati VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (aid, pratica_id, nome, h, dest.stat().st_size, dest.relative_to(self.arch.base).as_posix(), ruolo,
                   origine_id, tipo_eg, finalita, persona_id, json.dumps(analisi),
                   json.dumps(rapporto) if rapporto else None, ora()))
        return {"allegato_id": aid, "nome": nome, "sha256": h, "bytes": dest.stat().st_size, "ruolo": ruolo,
                "analisi": analisi, "rapporto": rapporto}

    @staticmethod
    def _sha_file(p: Path) -> str:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for blocco in iter(lambda: f.read(1 << 20), b""):
                h.update(blocco)
        return h.hexdigest()

    def _scrivi_nel_deposito(self, sorgente: Path, dest: Path, h: str) -> None:
        """Copia atomica nel deposito per impronta (.tmp + os.replace). Un file gia' presente viene ricontrollato: se
        l'impronta non coincide (troncato, alterato) viene riscritto dalla sorgente."""
        if dest.is_file() and self._sha_file(dest) == h:
            return
        tmp = dest.with_name(f"{dest.name}.{uuid.uuid4().hex[:8]}.tmp")
        try:
            shutil.copyfile(sorgente, tmp)
            if self._sha_file(tmp) != h:
                raise DatiNonValidi("il file e' cambiato durante l'acquisizione: riprovare", percorso=str(sorgente))
            os.replace(tmp, dest)
        finally:
            if tmp.exists():
                tmp.unlink()

    def acquisisci_file(self, pratica_id: str, percorso: Path | str, *, tipo_eg: str | None = None,
                        finalita: str | None = None, persona_id: str | None = None, nome: str | None = None,
                        chiave: str | None = None, riusa_identico: bool = False) -> dict:
        """Acquisisce un file come ORIGINALE (mai modificato). Tipo/finalita' li indica chi chiama.

        ``chiave``: idempotenza come per ``crea_pratica`` (tabella richieste): la ripetizione restituisce la stessa risposta
        con ``ripetuta``; la stessa chiave con un altro file o altri argomenti e' ``ChiaveRiutilizzata``.
        ``riusa_identico`` (canale MCP): se la pratica ha gia' un originale con stessa impronta, nome, tipo, finalita' e
        persona e il file nel deposito e' integro, si restituisce quello (``gia_presente``) invece di crearne un doppione."""
        self.leggi(pratica_id)  # esistenza
        p = Path(percorso)
        if not p.is_file():
            raise NonTrovato("file inesistente", percorso=str(p))
        nome = nome or p.name
        h = self._sha_file(p)
        impr = hashlib.sha256(json.dumps({"p": pratica_id, "sha256": h, "nome": nome, "tipo_eg": tipo_eg,
                                          "finalita": finalita, "persona_id": persona_id},
                                         sort_keys=True).encode()).hexdigest()
        analisi = pdfa.analizza_pdf(p)
        with self.arch.transazione() as c:
            if chiave:
                prec = self._richiesta(c, chiave, "acquisisci_allegato", impr)
                if prec is not None:
                    return {**prec, "ripetuta": True}
            risp = None
            if riusa_identico:
                for r in c.execute("SELECT * FROM allegati WHERE pratica_id=? AND sha256=? AND ruolo='originale' AND nome=? "
                                   "AND tipo_eg IS ? AND finalita IS ? AND persona_id IS ? ORDER BY ts",
                                   (pratica_id, h, nome, tipo_eg, finalita, persona_id)):
                    dep = self.arch.base / r["percorso"]
                    if dep.is_file() and self._sha_file(dep) == h:
                        risp = {"allegato_id": r["id"], "nome": r["nome"], "sha256": h, "bytes": r["bytes"],
                                "ruolo": r["ruolo"], "analisi": json.loads(r["analisi"]) if r["analisi"] else None,
                                "rapporto": json.loads(r["rapporto"]) if r["rapporto"] else None, "gia_presente": True}
                        break
            if risp is None:
                risp = self._registra(c, pratica_id, nome, p, "originale", None, tipo_eg, finalita, persona_id, analisi)
            if chiave:
                c.execute("INSERT INTO richieste VALUES(?,?,?,?,?,?)",
                          (chiave, pratica_id, "acquisisci_allegato", impr, json.dumps(risp), ora()))
            return risp

    def acquisisci_da_ingresso(self, pratica_id: str, nome_file: str, **kw) -> dict:
        """Per il canale MCP: solo file nella cartella d'ingresso dell'app (nessuna lettura arbitraria)."""
        base = self.cartella_ingresso.resolve()
        p = (base / nome_file).resolve()
        if base not in p.parents:
            raise DatiNonValidi("il file deve trovarsi nella cartella d'ingresso", cartella=str(base))
        return self.acquisisci_file(pratica_id, p, nome=Path(nome_file).name, **kw)

    def elenca_allegati(self, pratica_id: str) -> list[dict]:
        with self.arch.lettura() as c:
            if not c.execute("SELECT 1 FROM pratiche WHERE id=?", (pratica_id,)).fetchone():
                raise NonTrovato("pratica inesistente", pratica_id=pratica_id)
            righe = c.execute("SELECT * FROM allegati WHERE pratica_id=? ORDER BY ts", (pratica_id,)).fetchall()
        out = []
        for r in righe:
            d = dict(r)
            d["analisi"] = json.loads(d["analisi"]) if d["analisi"] else None
            rap = json.loads(d["rapporto"]) if d["rapporto"] else None
            if rap:
                rap.pop("rapporto_xml", None)
                if isinstance(rap.get("validazione"), dict):
                    rap["validazione"].pop("rapporto_xml", None)
            d["rapporto"] = rap
            out.append(d)
        return out

    def _riga_allegato(self, allegato_id: str):
        with self.arch.lettura() as c:
            r = c.execute("SELECT * FROM allegati WHERE id=?", (allegato_id,)).fetchone()
        if not r:
            raise NonTrovato("allegato inesistente", allegato_id=allegato_id)
        return r

    def _derivato_esistente(self, allegato_id: str, c=None):
        """Ultimo derivato di conversione (non di suddivisione) gia' registrato per l'originale. Con ``c`` la lettura
        avviene nella transazione di chi chiama (controllo e registrazione atomici)."""
        sql = "SELECT * FROM allegati WHERE origine_id=? AND ruolo='derivato' ORDER BY ts DESC"
        if c is not None:
            righe = c.execute(sql, (allegato_id,)).fetchall()
        else:
            with self.arch.lettura() as cl:
                righe = cl.execute(sql, (allegato_id,)).fetchall()
        for d in righe:
            rap = json.loads(d["rapporto"]) if d["rapporto"] else {}
            if "conversione" in rap:
                return d, rap
        return None, None

    def _riferimenti(self, pratica_id: str, allegato_id: str) -> list[dict]:
        return [r for r in self.leggi(pratica_id)["dati"].get("documenti_ref", []) if r.get("allegato_id") == allegato_id]

    def _sposta_riferimenti(self, pratica_id: str, da: str, a: str, canale: str) -> int:
        """I righi del quadro EG che puntano a ``da`` passano ad ``a`` (nuova revisione della pratica)."""
        refs = self._riferimenti(pratica_id, da)
        if not refs:
            return 0
        rev = self.leggi(pratica_id)["revisione"]
        self.aggiorna(pratica_id, rev, [{"op": "upsert", "coll": "documenti_ref", "id": r["id"], "campi": {"allegato_id": a}}
                                        for r in refs], autore="programma", canale=canale)
        return len(refs)

    @staticmethod
    def _usi_in(c, allegato_id: str, pratica_id: str | None) -> list[dict]:
        """Righi ``documenti_ref`` (di qualunque pratica) che puntano all'allegato, letti con la connessione ``c``.

        La pratica proprietaria si legge per intero; le altre solo se il loro JSON contiene l'identificativo (dati
        anteriori alla validazione del collegamento potevano puntare all'allegato di un'altra pratica)."""
        righe = []
        if pratica_id:
            righe += c.execute("SELECT id, dati FROM pratiche WHERE id=?", (pratica_id,)).fetchall()
        righe += c.execute("SELECT id, dati FROM pratiche WHERE id IS NOT ? AND dati LIKE ?",
                           (pratica_id, f"%{allegato_id}%")).fetchall()
        out = []
        for p in righe:
            try:
                refs = json.loads(p["dati"]).get("documenti_ref") or []
            except (TypeError, ValueError, AttributeError):
                continue
            out += [{"pratica_id": p["id"], "id": x.get("id")} for x in refs
                    if isinstance(x, dict) and x.get("allegato_id") == allegato_id]
        return out

    def _usi_altre_pratiche(self, c, allegato_id: str, pratica_id: str) -> bool:
        return any(u["pratica_id"] != pratica_id for u in self._usi_in(c, allegato_id, pratica_id))

    def _cancella_in(self, c, r) -> None:
        """Cancellazione della riga e (se l'impronta non serve piu') del file, dentro la transazione ``c``."""
        c.execute("DELETE FROM allegati WHERE id=?", (r["id"],))
        if self._impronta_in_uso(c, r["sha256"]):
            return
        p = self.arch.base / r["percorso"]
        if p.is_file() and p.name == r["sha256"]:
            p.unlink()

    def _cancella_riga(self, r, *, se_non_usato: bool = False) -> None:
        """Toglie la riga; il file del deposito si cancella solo se l'impronta non serve piu' a nessuno.

        Con ``se_non_usato`` i righi EG che usano l'allegato si ricontrollano DENTRO la transazione che cancella: un
        aggiornamento concorrente (GUI e MCP) che collega l'allegato a un rigo EG o viene prima, e la cancellazione e'
        rifiutata (``DatiNonValidi`` con i righi), o viene dopo e trova l'allegato gia' cancellato (rifiutato da
        ``aggiorna``). Nessun rigo puo' restare collegato a un allegato inesistente.

        Il deposito per impronta e' condiviso con ``DepositoArtefatti`` (ricevute, copie congelate, diagnostici), i cui
        descrittori stanno nel JSON di ``job.input``/``job.risultato``: se l'impronta compare li' (o in caso di dubbio)
        il file resta. Controllo e cancellazione avvengono sotto lo stesso lock di scrittura (BEGIN IMMEDIATE): un
        allegato con lo stesso contenuto, che scrive il file dentro la propria transazione, non puo' restare senza file."""
        with self.arch.transazione() as c:
            if se_non_usato:
                usi = self._usi_in(c, r["id"], r["pratica_id"])
                if usi:
                    raise DatiNonValidi("l'allegato e' usato nel quadro EG: togli prima il rigo o sostituisci il file",
                                        allegato_id=r["id"], righi=[u["id"] for u in usi],
                                        pratiche=sorted({u["pratica_id"] for u in usi}))
            self._cancella_in(c, r)

    @staticmethod
    def _impronta_in_uso(c, h: str) -> bool:
        if not h or len(h) != 64:
            return True                                  # in dubbio non si cancella
        try:
            if c.execute("SELECT 1 FROM allegati WHERE sha256=? LIMIT 1", (h,)).fetchone():
                return True
            like = f"%{h}%"
            return c.execute("SELECT 1 FROM job WHERE input LIKE ? OR risultato LIKE ? OR errore LIKE ? LIMIT 1",
                             (like, like, like)).fetchone() is not None
        except Exception:
            return True

    def elimina_allegato(self, allegato_id: str, *, canale: str = "gui") -> dict:
        """Elimina un allegato della pratica. Rifiutato se un rigo del quadro EG lo usa ancora."""
        r = self._riga_allegato(allegato_id)
        self._cancella_riga(r, se_non_usato=True)      # controllo dei righi EG e cancellazione nella stessa transazione
        return {"allegato_id": allegato_id, "eliminato": True}

    def riordina_allegati(self, pratica_id: str, *, canale: str = "gui") -> dict:
        """Toglie i doppioni: per ogni originale convertito resta una sola versione PDF/A (quella usata nel quadro EG, o la
        piu' recente). Se il PDF/A puo' sostituire l'originale (stessa regola di ``prepara_pdfa``: ``originale_sostituibile``)
        i righi EG passano al PDF/A e l'originale viene rimosso; altrimenti originale e righi restano e il motivo e'
        riportato in ``originali_conservati``."""
        tutti = [dict(x) for x in self._righe_pratica(pratica_id)]
        usati = {r.get("allegato_id") for r in self.leggi(pratica_id)["dati"].get("documenti_ref", [])}
        rimossi, spostati, conservati = [], 0, []
        for o in [x for x in tutti if x["ruolo"] == "originale"]:
            conv = [x for x in tutti if x["origine_id"] == o["id"] and x["ruolo"] == "derivato"
                    and "conversione" in (json.loads(x["rapporto"]) if x["rapporto"] else {})]
            if not conv:
                continue
            tenere = next((x for x in conv if x["id"] in usati), None) or max(conv, key=lambda x: x["ts"])
            for x in conv:
                if x["id"] != tenere["id"] and x["id"] not in usati:
                    try:
                        self._cancella_riga(x, se_non_usato=True)
                    except DatiNonValidi:
                        continue                     # collegato nel frattempo a un rigo EG: resta
                    rimossi.append(x["id"])
            ok, motivo = self.originale_sostituibile(json.loads(tenere["rapporto"]) if tenere["rapporto"] else None)
            if not ok:
                conservati.append({"allegato_id": o["id"], "nome": o["nome"], "derivato_id": tenere["id"],
                                   "motivo": motivo})
                if self.derivato_utilizzabile(json.loads(tenere["rapporto"]) if tenere["rapporto"] else None):
                    spostati += self._sposta_riferimenti(pratica_id, o["id"], tenere["id"], canale)
                continue
            spostati += self._sposta_riferimenti(pratica_id, o["id"], tenere["id"], canale)
            try:
                self._cancella_riga(o, se_non_usato=True)
            except DatiNonValidi:
                continue                             # ancora (o di nuovo) usato da un rigo EG: l'originale resta
            rimossi.append(o["id"])
        return {"pratica_id": pratica_id, "rimossi": rimossi, "righi_eg_aggiornati": spostati,
                "originali_conservati": conservati}

    def _righe_pratica(self, pratica_id: str):
        with self.arch.lettura() as c:
            return c.execute("SELECT * FROM allegati WHERE pratica_id=? ORDER BY ts", (pratica_id,)).fetchall()

    def prepara_pdfa(self, allegato_id: str, livello: str = "1b", *, sostituisci_originale: bool = False,
                     canale: str = "gui") -> dict:
        """Crea il derivato PDF/A di un originale, lo analizza e lo valida; conserva tutto collegato.

        Se l'originale dichiara gia' PDF/A-1 e veraPDF lo giudica conforme, l'originale e' conservato senza riscrittura
        (la firma digitale, se presente, resta integra). Senza veraPDF si crea sempre il derivato (esito
        'non_verificato'). Un derivato con un numero di pagine diverso NON viene registrato.

        Una seconda richiesta sullo stesso originale restituisce il derivato gia' creato (nessun doppione).
        Con ``sostituisci_originale`` (interfaccia e MCP) una conversione senza avvisi di rischio sposta i righi EG sul PDF/A e
        rimuove l'originale; con firma digitale, testo o aspetto divergenti l'originale resta e lo si dice."""
        from .documenti.dimensioni import confronta_testo, testo_pagine
        r = self._riga_allegato(allegato_id)
        if r["ruolo"] != "originale":
            raise DatiNonValidi("la conversione parte da un originale")
        gia, rap_gia = self._derivato_esistente(allegato_id)
        if gia is not None:
            return self._esito_gia_convertito(r, gia, rap_gia, sostituisci_originale, canale)
        src = self.arch.base / r["percorso"]
        an = json.loads(r["analisi"])
        if an.get("esito") not in ("leggibile", "firmato"):
            return {"allegato_id": allegato_id, "esito": an.get("esito"), "derivato": None,
                    "motivo": an.get("dettaglio") or "il file non e' un PDF convertibile",
                    "verifica_tiff": an.get("verifica_tiff")}
        avvisi: list[str] = []
        if an.get("dichiara_pdfa") in ("1a", "1b") and (livello == "1b" or an["dichiara_pdfa"] == "1a"):
            val0 = pdfa.valida_pdfa(src, an["dichiara_pdfa"])
            if val0["esito"] == "conforme":
                rapporto0 = {"validazione": val0, "livello": an["dichiara_pdfa"], "conservato_senza_riscrittura": True}
                with self.arch.transazione() as c:
                    c.execute("UPDATE allegati SET rapporto=? WHERE id=?", (json.dumps(rapporto0), allegato_id))
                return {"allegato_id": allegato_id, "derivato": None, "esito": "conforme", "conservato": "originale",
                        "avvisi": ["l'originale e' gia' PDF/A conforme secondo veraPDF: conservato senza riscrittura"]}
            avvisi.append(f"l'originale dichiara PDF/A-{an['dichiara_pdfa']} ma la conformita' non e' dimostrata "
                          f"({val0['esito']}): creato il derivato")
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "derivato.pdf"
            conv = pdfa.converti_in_pdfa(src, out, livello)
            if not conv["comando_ok"]:
                return {"allegato_id": allegato_id, "esito": "conversione_fallita", "derivato": None,
                        "dettaglio": conv.get("errore") or conv["stderr"]}
            an_d = pdfa.analizza_pdf(out)
            if an_d.get("pagine") != an.get("pagine"):
                return {"allegato_id": allegato_id, "esito": "conversione_fallita", "derivato": None,
                        "dettaglio": f"pagine diverse: originale {an.get('pagine')}, derivato {an_d.get('pagine')}; "
                                     "derivato scartato (nessuna pagina deve andare persa)"}
            val = pdfa.valida_pdfa(out, livello)
            avvisi += list(an_d.get("avvisi", []))
            if an.get("firme_digitali"):
                avvisi.append("l'originale era firmato: il derivato NON conserva la firma")
            testo = confronta_testo(testo_pagine(src), testo_pagine(out))
            if testo["divergenti"]:
                avvisi.append("testo divergente sulle pagine " + ", ".join(str(d["pagina"]) for d in
                                                                        testo["divergenti"][:20]))
            elif testo["differenze"]:
                avvisi.append("testo estratto con differenze minori (es. lettere accentate non piu' ricercabili) "
                              "sulle pagine " + ", ".join(str(d["pagina"]) for d in testo["differenze"][:20])
                              + ": controllare l'anteprima")
            try:
                from .documenti.anteprima import confronta_visivo
                visivo = confronta_visivo(src, out)
                if visivo["esito"] != "simili":
                    avvisi.append(f"differenze visive da controllare alle pagine {visivo['pagine_da_controllare']}")
            except Exception as e:          # l'anteprima e' un indicatore: la sua assenza non blocca
                visivo = {"esito": "non_eseguito", "motivo": str(e)[:200]}
            azione_richiesta = None
            if out.stat().st_size > pdfa.LIMITE_ALLEGATO_BYTE:
                azione_richiesta = "suddividi_allegato"
                avvisi.append(f"il derivato ({out.stat().st_size} byte) supera il limite per allegato "
                              f"({pdfa.LIMITE_ALLEGATO_BYTE} byte): ridurre o suddividere")
            rapporto = {"conversione": conv, "validazione": val, "avvisi": avvisi, "livello": livello,
                        "verifica_testo": testo, "confronto_visivo": visivo}
            with self.arch.transazione() as c:
                # idempotenza sotto il lock di scrittura: due conversioni contemporanee (GUI e MCP) dello stesso
                # originale registrano un solo derivato; la seconda scarta il proprio e restituisce quello esistente
                if not c.execute("SELECT 1 FROM allegati WHERE id=?", (allegato_id,)).fetchone():
                    raise NonTrovato("allegato inesistente (eliminato durante la conversione)", allegato_id=allegato_id)
                gia, rap_gia = self._derivato_esistente(allegato_id, c)
                d = None if gia is not None else self._registra(
                    c, r["pratica_id"], Path(r["nome"]).stem + "_pdfa.pdf", out, "derivato", allegato_id,
                    r["tipo_eg"], r["finalita"], r["persona_id"], an_d, rapporto)
        if gia is not None:
            return self._esito_gia_convertito(r, gia, rap_gia, sostituisci_originale, canale)
        esito = val["esito"]  # conforme / non_conforme / non_verificato
        out = {"allegato_id": allegato_id, "derivato": d, "esito": esito, "avvisi": avvisi,
               "verifica_indicativa": (val.get("verifica_indicativa") or {}).get("esito"),
               "azione_richiesta": azione_richiesta}
        if sostituisci_originale:
            out.update(self._dopo_conversione(r, d["allegato_id"], rapporto, canale))
        return out

    def _esito_gia_convertito(self, r, gia, rap_gia: dict, sostituisci_originale: bool, canale: str) -> dict:
        val = rap_gia.get("validazione") or {}
        esito = {"allegato_id": r["id"], "esito": val.get("esito"), "gia_convertito": True,
                 "derivato": {"allegato_id": gia["id"], "nome": gia["nome"], "sha256": gia["sha256"], "bytes": gia["bytes"]},
                 "avvisi": list(rap_gia.get("avvisi") or [])}
        if sostituisci_originale:
            esito.update(self._dopo_conversione(r, gia["id"], rap_gia, canale))
        return esito

    #: avvisi della conversione per cui l'originale resta (da confrontare a vista o perche' perde la firma)
    _RISCHI = ("firmato", "testo divergente", "differenze visive")

    @classmethod
    def originale_sostituibile(cls, rapporto_derivato: dict | None) -> tuple[bool, str | None]:
        """Regola unica (prepara_pdfa, anche col derivato gia' esistente, e riordina_allegati): il PDF/A prende il posto
        dell'originale solo se la validazione non e' 'non_conforme' e non ci sono avvisi di rischio (_RISCHI)."""
        if not rapporto_derivato:
            return False, "rapporto di conversione assente: l'originale resta"
        val = rapporto_derivato.get("validazione")
        esito = val.get("esito") if isinstance(val, dict) else None
        if esito == "non_conforme":
            return False, "il PDF/A non e' conforme secondo il validatore: l'originale resta"
        rischi = [str(a) for a in (rapporto_derivato.get("avvisi") or []) if any(k in str(a) for k in cls._RISCHI)]
        if rischi:
            return False, "controllare il PDF/A prima di eliminare l'originale: " + "; ".join(rischi)
        return True, None

    @staticmethod
    def derivato_utilizzabile(rapporto_derivato: dict | None) -> bool:
        """Il PDF/A puo' prendere il posto dell'originale nel quadro EG (anche se l'originale resta per un confronto):
        serve un rapporto di conversione e un esito diverso da 'non_conforme'."""
        if not rapporto_derivato:
            return False
        val = rapporto_derivato.get("validazione")
        return (val.get("esito") if isinstance(val, dict) else None) != "non_conforme"

    def _dopo_conversione(self, originale, derivato_id: str, rapporto_derivato: dict | None, canale: str) -> dict:
        ok, motivo = self.originale_sostituibile(rapporto_derivato)
        if not ok:
            # l'originale resta sempre; i righi EG passano comunque al PDF/A se e' utilizzabile (e' quello da inviare),
            # cosi' l'originale compare fra i file non usati e il professionista decide se eliminarlo dopo il confronto
            spostati = (self._sposta_riferimenti(originale["pratica_id"], originale["id"], derivato_id, canale)
                        if self.derivato_utilizzabile(rapporto_derivato) else 0)
            return {"originale_rimosso": False, "righi_eg_aggiornati": spostati, "motivo_originale_conservato": motivo}
        spostati = self._sposta_riferimenti(originale["pratica_id"], originale["id"], derivato_id, canale)
        try:
            # ricontrollo dei righi EG nella stessa transazione della cancellazione (aggiornamenti concorrenti)
            self._cancella_riga(originale, se_non_usato=True)
        except DatiNonValidi as e:
            return {"originale_rimosso": False, "righi_eg_aggiornati": spostati,
                    "motivo_originale_conservato": "l'originale e' stato collegato a un rigo EG durante la conversione: "
                    "resta (righi " + ", ".join(str(x) for x in e.dettagli.get("righi", [])) + ")"}
        return {"originale_rimosso": True, "righi_eg_aggiornati": spostati}

    def suddividi_allegato(self, allegato_id: str, limite_byte: int | None = None, livello: str = "1b",
                           **opzioni) -> dict:
        """Riduce o suddivide un allegato oltre il limite; registra ogni parte come derivato collegato.

        Le parti sono rivalidate e il rapporto (hash, pagine per parte, verifica testo) e' conservato con ciascuna."""
        from .documenti.dimensioni import riduci_o_suddividi
        r = self._riga_allegato(allegato_id)
        src = self.arch.base / r["percorso"]
        if limite_byte is None:
            limite = pdfa.LIMITE_ALLEGATO_BYTE
        elif isinstance(limite_byte, bool) or not isinstance(limite_byte, int) or limite_byte <= 0:
            raise DatiNonValidi("limite_byte: indicare un numero intero di byte maggiore di zero (o ometterlo per il "
                                f"limite delle specifiche, {pdfa.LIMITE_ALLEGATO_BYTE} byte)", limite_byte=limite_byte)
        else:
            limite = limite_byte
        with tempfile.TemporaryDirectory() as t:
            parti = riduci_o_suddividi(src, limite, cartella_uscita=t, livello=livello, **opzioni)
            rap = parti.rapporto
            sintesi = {k: rap.get(k) for k in ("azione", "limite_byte", "limite", "assunzioni", "fonte", "tentativi",
                                               "verifica_pagine", "verifica_testo", "originale_invariato", "avvisi")}
            if rap["azione"] == "nessuna":
                return {"allegato_id": allegato_id, "azione": "nessuna", "parti": [], "rapporto": sintesi}
            registrate = []
            with self.arch.transazione() as c:
                for voce, p in zip(rap["parti"], parti):
                    k = voce["di"]
                    suffisso = "_pdfa.pdf" if rap["azione"] == "conversione" else "_ridotto.pdf"
                    nome = Path(r["nome"]).stem + (f"_parte{voce['parte']:02d}di{k:02d}.pdf" if k > 1 else suffisso)
                    rapporto = {"suddivisione": {**sintesi, "parte": voce}, "validazione": voce.get("validazione"),
                                "livello": livello}
                    registrate.append(self._registra(c, r["pratica_id"], nome, Path(p), "derivato", allegato_id,
                                                     r["tipo_eg"], r["finalita"], r["persona_id"],
                                                     pdfa.analizza_pdf(p), rapporto))
        return {"allegato_id": allegato_id, "azione": rap["azione"], "parti": registrate, "rapporto": sintesi}
