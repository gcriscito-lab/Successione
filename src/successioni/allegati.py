"""Allegati: originale e derivati conservati insieme, con analisi e rapporto di validazione.

Flusso (specifica par. 7): acquisisci originale -> rileva formato, firme, protezioni -> conserva se gia' conforme
(solo con validatore indipendente) oppure crea il derivato PDF/A -> valida -> controlla pagine, testo, dimensioni ->
riduci o suddividi se oltre il limite. L'originale non viene mai modificato.
"""
from __future__ import annotations

import hashlib
import json
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
        if not dest.exists():
            shutil.copyfile(percorso_tmp, dest)
        aid = "al_" + uuid.uuid4().hex[:12]
        c.execute("INSERT INTO allegati VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (aid, pratica_id, nome, h, dest.stat().st_size, dest.relative_to(self.arch.base).as_posix(), ruolo,
                   origine_id, tipo_eg, finalita, persona_id, json.dumps(analisi),
                   json.dumps(rapporto) if rapporto else None, ora()))
        return {"allegato_id": aid, "nome": nome, "sha256": h, "bytes": dest.stat().st_size, "ruolo": ruolo,
                "analisi": analisi, "rapporto": rapporto}

    def acquisisci_file(self, pratica_id: str, percorso: Path | str, *, tipo_eg: str | None = None,
                        finalita: str | None = None, persona_id: str | None = None, nome: str | None = None) -> dict:
        """Acquisisce un file come ORIGINALE (mai modificato). Tipo/finalita' li indica chi chiama."""
        self.leggi(pratica_id)  # esistenza
        p = Path(percorso)
        if not p.is_file():
            raise NonTrovato("file inesistente", percorso=str(p))
        analisi = pdfa.analizza_pdf(p)
        with self.arch.transazione() as c:
            return self._registra(c, pratica_id, nome or p.name, p, "originale", None, tipo_eg, finalita,
                                  persona_id, analisi)

    def acquisisci_da_ingresso(self, pratica_id: str, nome_file: str, **kw) -> dict:
        """Per il canale MCP: solo file nella cartella d'ingresso dell'app (nessuna lettura arbitraria)."""
        base = self.cartella_ingresso.resolve()
        p = (base / nome_file).resolve()
        if base not in p.parents:
            raise DatiNonValidi("il file deve trovarsi nella cartella d'ingresso", cartella=str(base))
        return self.acquisisci_file(pratica_id, p, nome=Path(nome_file).name, **kw)

    def elenca_allegati(self, pratica_id: str) -> list[dict]:
        with self.arch.lettura() as c:
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

    def _derivato_esistente(self, allegato_id: str):
        """Ultimo derivato di conversione (non di suddivisione) gia' registrato per l'originale."""
        with self.arch.lettura() as c:
            righe = c.execute("SELECT * FROM allegati WHERE origine_id=? AND ruolo='derivato' ORDER BY ts DESC",
                              (allegato_id,)).fetchall()
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

    def _cancella_riga(self, r) -> None:
        with self.arch.transazione() as c:
            c.execute("DELETE FROM allegati WHERE id=?", (r["id"],))
            altri = c.execute("SELECT COUNT(*) FROM allegati WHERE sha256=?", (r["sha256"],)).fetchone()[0]
        if not altri:          # lo stesso contenuto puo' servire ad altri allegati (deposito per impronta)
            p = self.arch.base / r["percorso"]
            if p.is_file():
                p.unlink()

    def elimina_allegato(self, allegato_id: str, *, canale: str = "gui") -> dict:
        """Elimina un allegato della pratica. Rifiutato se un rigo del quadro EG lo usa ancora."""
        r = self._riga_allegato(allegato_id)
        refs = self._riferimenti(r["pratica_id"], allegato_id)
        if refs:
            raise DatiNonValidi("l'allegato e' usato nel quadro EG: togli prima il rigo o sostituisci il file",
                                righi=[x["id"] for x in refs])
        self._cancella_riga(r)
        return {"allegato_id": allegato_id, "eliminato": True}

    def riordina_allegati(self, pratica_id: str, *, canale: str = "gui") -> dict:
        """Toglie i doppioni: per ogni originale convertito resta una sola versione PDF/A (quella usata nel quadro EG, o la
        piu' recente); i righi EG che puntano all'originale passano al PDF/A e l'originale convertito viene rimosso."""
        tutti = [dict(x) for x in self._righe_pratica(pratica_id)]
        usati = {r.get("allegato_id") for r in self.leggi(pratica_id)["dati"].get("documenti_ref", [])}
        rimossi, spostati = [], 0
        for o in [x for x in tutti if x["ruolo"] == "originale"]:
            conv = [x for x in tutti if x["origine_id"] == o["id"] and x["ruolo"] == "derivato"
                    and "conversione" in (json.loads(x["rapporto"]) if x["rapporto"] else {})]
            if not conv:
                continue
            tenere = next((x for x in conv if x["id"] in usati), None) or max(conv, key=lambda x: x["ts"])
            for x in conv:
                if x["id"] != tenere["id"] and x["id"] not in usati:
                    self._cancella_riga(x)
                    rimossi.append(x["id"])
            spostati += self._sposta_riferimenti(pratica_id, o["id"], tenere["id"], canale)
            if not self._riferimenti(pratica_id, o["id"]):
                self._cancella_riga(o)
                rimossi.append(o["id"])
        return {"pratica_id": pratica_id, "rimossi": rimossi, "righi_eg_aggiornati": spostati}

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
            val = rap_gia.get("validazione") or {}
            esito = {"allegato_id": allegato_id, "esito": val.get("esito"), "gia_convertito": True,
                     "derivato": {"allegato_id": gia["id"], "nome": gia["nome"], "sha256": gia["sha256"], "bytes": gia["bytes"]},
                     "avvisi": list(rap_gia.get("avvisi") or [])}
            if sostituisci_originale:
                esito.update(self._dopo_conversione(r, gia["id"], esito["avvisi"], canale))
            return esito
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
                d = self._registra(c, r["pratica_id"], Path(r["nome"]).stem + "_pdfa.pdf", out, "derivato", allegato_id,
                                   r["tipo_eg"], r["finalita"], r["persona_id"], an_d, rapporto)
        esito = val["esito"]  # conforme / non_conforme / non_verificato
        out = {"allegato_id": allegato_id, "derivato": d, "esito": esito, "avvisi": avvisi,
               "verifica_indicativa": (val.get("verifica_indicativa") or {}).get("esito"),
               "azione_richiesta": azione_richiesta}
        if sostituisci_originale and esito != "non_conforme":
            out.update(self._dopo_conversione(r, d["allegato_id"], avvisi, canale))
        return out

    #: avvisi della conversione per cui l'originale resta (da confrontare a vista o perche' perde la firma)
    _RISCHI = ("firmato", "testo divergente", "differenze visive")

    def _dopo_conversione(self, originale, derivato_id: str, avvisi: list[str], canale: str) -> dict:
        rischi = [a for a in avvisi if any(k in a for k in self._RISCHI)]
        spostati = self._sposta_riferimenti(originale["pratica_id"], originale["id"], derivato_id, canale)
        if rischi:
            return {"originale_rimosso": False, "righi_eg_aggiornati": spostati,
                    "motivo_originale_conservato": "controllare il PDF/A prima di eliminare l'originale: " + "; ".join(rischi)}
        self._cancella_riga(originale)
        return {"originale_rimosso": True, "righi_eg_aggiornati": spostati}

    def suddividi_allegato(self, allegato_id: str, limite_byte: int | None = None, livello: str = "1b",
                           **opzioni) -> dict:
        """Riduce o suddivide un allegato oltre il limite; registra ogni parte come derivato collegato.

        Le parti sono rivalidate e il rapporto (hash, pagine per parte, verifica testo) e' conservato con ciascuna."""
        from .documenti.dimensioni import riduci_o_suddividi
        r = self._riga_allegato(allegato_id)
        src = self.arch.base / r["percorso"]
        limite = int(limite_byte or pdfa.LIMITE_ALLEGATO_BYTE)
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
