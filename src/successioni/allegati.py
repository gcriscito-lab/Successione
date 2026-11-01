"""Allegati: originale e derivati conservati insieme, con analisi e rapporto di validazione."""
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
                  (aid, pratica_id, nome, h, dest.stat().st_size, str(dest.relative_to(self.arch.base)), ruolo,
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
            d["rapporto"] = rap
            out.append(d)
        return out

    def prepara_pdfa(self, allegato_id: str, livello: str = "1b") -> dict:
        """Crea il derivato PDF/A di un originale, lo analizza e lo valida; conserva tutto collegato."""
        with self.arch.lettura() as c:
            r = c.execute("SELECT * FROM allegati WHERE id=?", (allegato_id,)).fetchone()
        if not r:
            raise NonTrovato("allegato inesistente", allegato_id=allegato_id)
        if r["ruolo"] != "originale":
            raise DatiNonValidi("la conversione parte da un originale")
        src = self.arch.base / r["percorso"]
        an = json.loads(r["analisi"])
        if an.get("esito") not in ("leggibile", "firmato"):
            return {"allegato_id": allegato_id, "esito": an.get("esito"), "derivato": None,
                    "motivo": an.get("dettaglio") or "il file non e' un PDF convertibile"}
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "derivato.pdf"
            conv = pdfa.converti_in_pdfa(src, out, livello)
            if not conv["comando_ok"]:
                return {"allegato_id": allegato_id, "esito": "conversione_fallita", "derivato": None,
                        "dettaglio": conv["stderr"]}
            an_d = pdfa.analizza_pdf(out)
            val = pdfa.valida_pdfa(out, livello)
            avvisi = list(an_d.get("avvisi", []))
            if an.get("firme_digitali"):
                avvisi.append("l'originale era firmato: il derivato NON conserva la firma")
            if an_d.get("pagine") != an.get("pagine"):
                avvisi.append(f"pagine diverse: originale {an.get('pagine')}, derivato {an_d.get('pagine')}")
            rapporto = {"conversione": conv, "validazione": val, "avvisi": avvisi, "livello": livello}
            with self.arch.transazione() as c:
                d = self._registra(c, r["pratica_id"], Path(r["nome"]).stem + "_pdfa.pdf", out, "derivato", allegato_id,
                                   r["tipo_eg"], r["finalita"], r["persona_id"], an_d, rapporto)
        esito = val["esito"]  # conforme / non_conforme / non_verificato
        return {"allegato_id": allegato_id, "derivato": d, "esito": esito, "avvisi": avvisi}
