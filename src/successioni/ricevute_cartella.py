"""Ricevute e attestazioni prese dalla cartella dei download: il professionista scarica i documenti dall'area riservata
dell'Agenzia (con le sue credenziali, nel suo browser), il programma li trova, riconosce a quale pratica appartengono dal codice
fiscale del defunto e li conserva nella pratica. Il programma non accede a Entratel e non conserva credenziali.

Si leggono solo i PDF con un nome da documento della successione (``ricevute_pdf.candidato_per_nome``): gli altri file della
cartella non vengono aperti. Solo dall'interfaccia: MCP non ha accesso alla cartella dei download.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from .errori import DatiNonValidi

LIMITE_FILE = 20 * 1024 * 1024


def cartella_predefinita() -> Path:
    return Path.home() / "Downloads"


class RicevuteCartellaMixin:
    def _cartella_ricevute(self, cartella: str | Path | None) -> Path:
        c = Path(cartella) if cartella else cartella_predefinita()
        if not c.is_dir():
            raise DatiNonValidi(f"cartella non trovata: {c}")
        return c

    def _ricevute_gia_conservate(self) -> dict[str, str]:
        """impronta -> pratica dei documenti gia' conservati (per non ricaricarli)."""
        from .collegamenti.invio import TIPO_RICEVUTA, InvioAdattatore
        ad = InvioAdattatore(self.arch)
        return {j["input"].get("sha256"): j["pratica_id"] for j in ad.job.elenca(TIPO_RICEVUTA) if j["input"].get("sha256")}

    def ricevute_cerca(self, cartella: str | Path | None = None) -> dict:
        """Documenti della successione trovati nella cartella, con la pratica a cui appartengono (per codice fiscale del
        defunto) e se sono gia' conservati. Nessuna scrittura."""
        from .collegamenti.ricevute_pdf import candidato_per_nome, riconosci
        c = self._cartella_ricevute(cartella)
        per_cf: dict[str, list[dict]] = {}
        for p in self.elenca():
            dati = self.leggi(p["id"])["dati"]
            cf = next((str(x.get("codice_fiscale") or "").upper() for x in dati.get("persone", []) if x.get("ruolo") == "defunto"), "")
            if cf:
                per_cf.setdefault(cf, []).append({"pratica_id": p["id"], "titolo": p.get("titolo")})
        gia = self._ricevute_gia_conservate()
        trovati = []
        for f in sorted(c.iterdir(), key=lambda x: x.name.lower()):
            if not f.is_file() or not candidato_per_nome(f.name) or f.stat().st_size > LIMITE_FILE:
                continue
            contenuto = f.read_bytes()
            try:
                r = riconosci(contenuto)
            except DatiNonValidi:
                continue
            if not r["tipo"]:
                continue
            h = hashlib.sha256(contenuto).hexdigest()
            pratiche = per_cf.get(r["codice_fiscale_defunto"] or "", [])
            trovati.append({"file": f.name, "tipo": r["tipo"], "codice_fiscale_defunto": r["codice_fiscale_defunto"],
                            "dati": r["dati"], "pagine": r["pagine"], "sha256": h, "pratiche": pratiche,
                            "conservato_in": gia.get(h)})
        return {"cartella": str(c), "documenti": trovati}

    def ricevuta_da_cartella(self, pratica_id: str, file: str, *, cartella: str | Path | None = None,
                             tipo: str | None = None) -> dict:
        """Conserva nella pratica un documento della cartella (originale tal quale). Il tipo riconosciuto si puo' correggere
        con ``tipo``. Con l'attestazione, gli estremi di registrazione si annotano nelle note interne della pratica."""
        from .collegamenti.invio import TIPI_RICEVUTA, TIPO_TENTATIVO, InvioAdattatore
        from .collegamenti.ricevute_pdf import candidato_per_nome, riconosci
        c = self._cartella_ricevute(cartella)
        p = (c / file).resolve()
        if not p.is_relative_to(c.resolve()) or not p.is_file() or not candidato_per_nome(p.name):
            raise DatiNonValidi("file non disponibile nella cartella o non e' un documento della successione")
        if p.stat().st_size > LIMITE_FILE:
            raise DatiNonValidi("file oltre 20 MB")
        contenuto = p.read_bytes()
        r = riconosci(contenuto)
        pr = self.leggi(pratica_id)
        cf = next((str(x.get("codice_fiscale") or "").upper() for x in pr["dati"].get("persone", []) if x.get("ruolo") == "defunto"), "")
        if r["codice_fiscale_defunto"] and cf and r["codice_fiscale_defunto"] != cf:
            raise DatiNonValidi("il documento riguarda un altro defunto (codice fiscale diverso da quello della pratica)")
        tipo = tipo or r["tipo"] or "da_classificare"
        if tipo not in TIPI_RICEVUTA:
            raise DatiNonValidi("tipo di documento non ammesso", ammessi=list(TIPI_RICEVUTA))
        ad = InvioAdattatore(self.arch)
        trasmessi = [t for t in ad.job.elenca(TIPO_TENTATIVO, pratica_id) if t["risultato"].get("protocollo")]
        reg = r["dati"].get("registrazione") or {}
        protocollo = (trasmessi[-1]["risultato"]["protocollo"] if trasmessi else
                      f"registrazione {reg['volume']}/{reg['numero']}/{reg['anno']}" if reg else "non indicato")
        esito = "registrata" if tipo == "registrazione" and reg else None
        res = ad.associa(protocollo=protocollo, tipo=tipo, contenuto=contenuto, nome=p.name, esito=esito,
                         data_documento=r["dati"].get("data_presentazione"), pratica_id=pratica_id,
                         dettagli={**r["dati"], "riconosciuto": r["tipo"], "cartella": str(c)}).asdict()
        if reg and not res.get("dettaglio", {}).get("ripetuta"):
            note = dict((pr["dati"].get("note") or {}).get("registrazione") or {})
            nuovo = {**reg, "data_presentazione": r["dati"].get("data_presentazione"), "ufficio": r["dati"].get("ufficio"),
                     "codice_ufficio": r["dati"].get("codice_ufficio"), "fonte": f"attestazione «{p.name}»"}
            if note != nuovo:
                self.aggiorna(pratica_id, pr["revisione"], [{"op": "set", "sezione": "note", "campi": {"registrazione": nuovo}}],
                              origine="acquisito")
        return {"tipo": tipo, "protocollo": protocollo, "dati": r["dati"], "ripetuta": bool(res.get("dettaglio", {}).get("ripetuta")),
                "job_id": res.get("job_id") or res.get("dettaglio", {}).get("job_id")}
