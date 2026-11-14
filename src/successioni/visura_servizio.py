"""Immobili dalla visura: il professionista carica il PDF delle «Risultanze catastali» scaricato da Entratel, il programma
propone gli immobili e li scrive nella pratica solo quelli scelti, con origine «acquisito».

Usa la lavorazione del catasto (``collegamenti.catasto``, tipo ``catasto_entratel``) in modalita' manuale: nessun accesso a
Entratel dal programma. Il PDF resta conservato tal quale fra gli originali della lavorazione. Interfaccia e MCP chiamano gli
stessi metodi.
"""
from __future__ import annotations

from .errori import DatiNonValidi

LIMITE_VISURA = 20 * 1024 * 1024


class VisuraMixin:
    def _adattatore_catasto(self):
        from .collegamenti.catasto import CatastoEntratelAdattatore
        return CatastoEntratelAdattatore(self.arch)

    @staticmethod
    def _cf_defunto(dati: dict) -> str:
        return next((str(p.get("codice_fiscale") or "").strip().upper() for p in dati.get("persone", [])
                     if p.get("ruolo") == "defunto"), "")

    def _job_visura(self, pratica_id: str, cf: str, *, crea: bool) -> str | None:
        from .collegamenti import catasto as K
        ad = self._adattatore_catasto()
        aperti = [j for j in ad.job.elenca(K.TIPO_JOB, pratica_id)
                  if j["stato"] in (K.ATTESA_UTENTE, K.AVVIATO, K.PARZIALE, K.CARICATO_MANUALMENTE)]
        if aperti:
            return aperti[-1]["job_id"]
        if not crea:
            return None
        return ad.avvia(pratica_id, {"soggetto_cf": cf, "catasto": "entrambi",
                                     "note": "visure caricate a mano dal professionista"}).job_id

    def visura_carica(self, pratica_id: str, contenuto: bytes, *, nome: str = "visura.pdf") -> dict:
        """Conserva il PDF e ne legge gli immobili (si sommano a quelli dei PDF gia' caricati nella stessa pratica)."""
        dati = self.leggi(pratica_id)["dati"]
        cf = self._cf_defunto(dati)
        if not cf:
            raise DatiNonValidi("indica prima il codice fiscale del defunto nei dati generali: serve a riconoscere le sue "
                                "quote nella visura")
        if not contenuto or len(contenuto) > LIMITE_VISURA:
            raise DatiNonValidi("visura vuota o oltre 20 MB")
        if contenuto[:5] != b"%PDF-":
            raise DatiNonValidi("la visura deve essere il PDF delle «Risultanze catastali» salvato da Entratel")
        job = self._job_visura(pratica_id, cf, crea=True)
        self._adattatore_catasto().registra_originale(job, contenuto, formato="pdf", fonte=nome)
        return self.visura_stato(pratica_id)

    def visura_stato(self, pratica_id: str, *, selezione: list[str] | None = None) -> dict:
        """Immobili letti dalle visure caricate e proposta per la pratica (nessuna scrittura)."""
        dati = self.leggi(pratica_id)["dati"]
        cf = self._cf_defunto(dati)
        job = self._job_visura(pratica_id, cf, crea=False)
        if job is None:
            return {"job_id": None, "immobili": [], "proposta": None, "file": [], "avvisi": []}
        ad = self._adattatore_catasto()
        ris = ad.leggi_risultati(job)
        prop = ad.proponi(job, dati, selezione=selezione, cf_defunto=cf).dettaglio["proposta"]
        j = ad.job.leggi(job)
        avvisi = []
        cf_letti = {p.get("codice_fiscale") for p in [j["risultato"].get("provenienza") or {}] if p.get("codice_fiscale")}
        if cf and cf_letti and cf not in cf_letti:
            avvisi.append("la visura e' intestata a un codice fiscale diverso da quello del defunto: quote e diritti non "
                          "vengono proposti")
        stato_per_chiave = {k: s for s in ("nuovi", "aggiornati", "invariati") for k in prop[s]}
        stato_per_chiave.update({c["chiave"]: "conflitti" for c in prop["conflitti"]})
        immobili = [{**{k: v for k, v in im.items() if k not in ("altri_campi", "titolarita")},
                     "titolarita": [t.get("descrizione") or t.get("diritto") for t in im.get("titolarita") or []],
                     "esito": stato_per_chiave.get(im["chiave"], "escluso")}
                    for im in ris.dettaglio.get("immobili", [])]
        file = [{"nome": a.get("fonte") or a.get("nome"), "sha256": a.get("sha256")} for a in j["risultato"].get("originali", [])]
        return {"job_id": job, "immobili": immobili, "proposta": prop, "file": file, "avvisi": avvisi,
                "limiti": ris.dettaglio.get("limiti", [])}

    def visura_applica(self, pratica_id: str, revisione_attesa: int, selezione: list[str], *, chiave: str | None = None,
                       canale: str = "gui") -> dict:
        """Scrive nella pratica gli immobili scelti (``selezione`` = chiavi degli immobili), con origine «acquisito». I campi
        gia' inseriti o confermati dall'utente non vengono sovrascritti (restano nei conflitti)."""
        if not isinstance(selezione, list) or not selezione:
            raise DatiNonValidi("scegli almeno un immobile da aggiungere")
        st = self.visura_stato(pratica_id, selezione=selezione)
        if not st["job_id"]:
            raise DatiNonValidi("nessuna visura caricata per questa pratica")
        ops = st["proposta"]["operazioni"]
        if not ops:
            return {"applicate": 0, "revisione": revisione_attesa, "conflitti": st["proposta"]["conflitti"]}
        r = self.aggiorna(pratica_id, revisione_attesa, ops, chiave=chiave, canale=canale, origine="acquisito")
        return {"applicate": len(ops), "revisione": r.get("revisione"), "conflitti": st["proposta"]["conflitti"],
                "nuovi": st["proposta"]["nuovi"], "aggiornati": st["proposta"]["aggiornati"]}
