"""Percorso di invio della pratica: copia congelata, conferma nell'app, trasmissione, riconciliazione.

Due modalita', mai una trasmissione reale dal programma:
- ``simulata``: servizio fittizio locale (``TrasportoSimulato``) per PROVARE il percorso completo (anche rete interrotta e
  riconciliazione). L'esito e' sempre ``simulazione``: non dimostra nulla sull'Agenzia.
- ``manuale``: il programma non invia; restituisce le istruzioni per l'invio con gli strumenti ufficiali (Desktop Telematico /
  Entratel) e registra poi il protocollo con la riconciliazione. L'esito resta ``da_collaudare``.

La conferma della trasmissione si da' solo dall'interfaccia (canale ``gui``), mai da MCP: l'adattatore lo impone.
Credenziali e certificati non passano di qui.
"""
from __future__ import annotations

from .errori import ConflittoRevisione, DatiNonValidi

MODALITA = ("simulata", "manuale")


class InvioMixin:
    def _adattatore_invio(self, modalita: str):
        from .collegamenti.invio import InvioAdattatore, TrasportoSimulato
        if modalita not in MODALITA:
            raise DatiNonValidi("modalita' non ammessa", ammesse=list(MODALITA))
        if modalita == "simulata":
            if getattr(self, "_trasporto_simulato", None) is None:   # lato 'server' fittizio: vive quanto il servizio
                self._trasporto_simulato = TrasportoSimulato()
            return InvioAdattatore(self.arch, self._trasporto_simulato)
        return InvioAdattatore(self.arch)

    @staticmethod
    def _copia_json(r) -> dict:
        d = r.asdict()
        d["artefatti"] = [{k: a.get(k) for k in ("ruolo", "nome", "sha256", "bytes")} for a in d.get("artefatti", [])]
        d["job_id"], d["stato"] = d["dettaglio"].get("job_id"), d["dettaglio"].get("stato")
        return d

    def invio_prepara(self, pratica_id: str, *, chiave: str | None = None) -> dict:
        """Congela il file XML completo e aggiornato con il controllo ufficiale associato. Non trasmette nulla."""
        from .elaborati import TIPO_CONTROLLO
        st = self.stato_elaborati(pratica_id)
        exp = st["export"]
        if exp.get("stato") != "aggiornato" or not exp.get("generato") or not exp.get("completo") or not exp.get("percorso"):
            raise DatiNonValidi("serve un file XML completo e aggiornato: genera il file (scopo completo) prima di preparare "
                                "l'invio", stato_export=exp.get("stato"), completo=exp.get("completo"))
        c = self._job_ultimo(TIPO_CONTROLLO, pratica_id)
        controllo = None
        if c and c["input"].get("xml_sha256") == exp.get("xml_sha256"):
            controllo = c["risultato"].get("job_adattatore")
        d = self.leggi(pratica_id)
        if d["impronta_dichiarativa"] != st["impronta_dichiarativa"]:
            raise ConflittoRevisione("la pratica e' cambiata: rigenerare gli elaborati")
        forn = (d["dati"].get("opzioni", {}) or {}).get("fornitore", {}) or {}
        profilo = {k: forn[k] for k in ("cf", "tipo", "impegno_codice", "data_impegno") if forn.get(k)}
        from lxml import etree
        from .telematico.fonti import NS_SUC, NS_TM
        xml, _ = self.file_export(pratica_id, exp["job_id"])
        root = etree.fromstring(xml, etree.XMLParser(resolve_entities=False, no_network=True))
        importi = {"totale_da_versare": root.findtext(f'.//{{{NS_SUC}}}Frontespizio/{{{NS_SUC}}}ImportoDaVersare', '0').replace(',', '.')}
        profilo["cf"] = root.findtext(f'.//{{{NS_TM}}}CodiceFiscaleFornitore')
        r = self._adattatore_invio("manuale").prepara(
            pratica_id, elaborati=[{"percorso": str(self.arch.base / exp["percorso"]), "ruolo": "telematico"}],
            importi=importi, profilo=profilo, controllo_job_id=controllo, revisione=d["revisione"], chiave=chiave,
            aspettative={"addebito": bool(root.find(f'.//{{{NS_SUC}}}Versamento') is not None)})
        return self._copia_json(r)

    def invio_copia(self, copia_id: str) -> dict:
        return self._copia_json(self._adattatore_invio("manuale").verifica_validita(copia_id))

    def invio_conferma(self, copia_id: str, impronta_mostrata: str, *, utente: str = "utente", canale: str = "gui") -> dict:
        """Conferma della specifica copia: ammessa solo dal canale 'gui'."""
        return self._copia_json(self._adattatore_invio("manuale").conferma(
            copia_id, impronta_mostrata=impronta_mostrata, utente=utente, canale=canale))

    def invio_trasmetti(self, copia_id: str, chiave_richiesta: str, *, modalita: str = "simulata", canale: str = "gui") -> dict:
        """Trasmette la copia confermata: ``simulata`` (servizio fittizio) o ``manuale`` (istruzioni, nessun invio)."""
        r = self._adattatore_invio(modalita).trasmetti(copia_id, chiave_richiesta=chiave_richiesta, canale=canale)
        out = r.asdict()
        out["job_id"], out["stato"] = out["dettaglio"].get("job_id"), out["dettaglio"].get("stato")
        out["modalita"] = modalita
        out["avvertenza"] = ("PROVA SIMULATA: nessun file e' stato inviato all'Agenzia delle Entrate." if modalita == "simulata"
                             else "Il programma NON ha trasmesso nulla: segui le istruzioni, poi registra l'esito con la riconciliazione.")
        return out

    def invio_riconcilia(self, tentativo_id: str, evidenze: dict | None = None, *, modalita: str | None = None) -> dict:
        ad = self._adattatore_invio("manuale")
        t = ad.job.leggi(tentativo_id, "invio_tentativo")
        registrata = ad._modalita_tentativo(t)
        if modalita is not None and modalita != registrata:
            raise DatiNonValidi("modalita' diversa da quella del tentativo")
        modalita = registrata
        r = self._adattatore_invio(modalita).riconcilia(tentativo_id, evidenze=evidenze)
        out = r.asdict()
        out["job_id"], out["stato"] = out["dettaglio"].get("job_id"), out["dettaglio"].get("stato")
        out["modalita"] = modalita
        return out

    def invio_stato(self, pratica_id: str) -> dict:
        """Copie congelate della pratica con i tentativi (dal piu' recente)."""
        from .collegamenti.invio import TIPO_COPIA
        ad = self._adattatore_invio("manuale")
        copie = []
        for j in reversed(ad.job.elenca(TIPO_COPIA, pratica_id)):
            for tid in j["risultato"].get("tentativi", []):
                ad._recupera_finale(ad.job.leggi(tid, "invio_tentativo"))
            copia = self._copia_json(ad.verifica_validita(j["job_id"]))
            copia["tentativi"] = [ad.leggi_tentativo(tid).asdict() for tid in copia["dettaglio"].get("tentativi", [])]
            copie.append(copia)
        return {"pratica_id": pratica_id, "copie": copie}

    def ricevuta_acquisisci(self, pratica_id: str, tentativo_id: str, contenuto: bytes, *, nome: str,
                           tipo: str, esito: str | None = None) -> dict:
        """Conserva l'originale associandolo al protocollo preciso, mai per ordine d'arrivo."""
        self.leggi(pratica_id)
        ad = self._adattatore_invio("manuale")
        t = ad.job.leggi(tentativo_id, "invio_tentativo")
        if t["pratica_id"] != pratica_id or t["stato"] != "trasmesso" or not t["risultato"].get("protocollo"):
            raise DatiNonValidi("serve un tentativo trasmesso della stessa pratica con protocollo registrato")
        if not contenuto or len(contenuto) > 20_000_000:
            raise DatiNonValidi("ricevuta vuota o oltre 20 MB")
        ad = self._adattatore_invio(ad._modalita_tentativo(t))
        return ad.associa(protocollo=t["risultato"]["protocollo"], tipo=tipo, contenuto=contenuto,
                          nome=nome, esito=esito, pratica_id=pratica_id).asdict()

    def ricevute_stato(self, pratica_id: str, tentativo_id: str) -> dict:
        ad = self._adattatore_invio("manuale")
        t = ad.job.leggi(tentativo_id, "invio_tentativo")
        if t["pratica_id"] != pratica_id or not t["risultato"].get("protocollo"):
            raise DatiNonValidi("tentativo senza protocollo o appartenente a un'altra pratica")
        ad = self._adattatore_invio(ad._modalita_tentativo(t))
        return ad.stato_esiti(t["risultato"]["protocollo"], pratica_id=pratica_id)
