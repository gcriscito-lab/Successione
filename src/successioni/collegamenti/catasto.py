"""Risultanze catastali via Entratel (NON SISTER): macchina a stati persistente e proposta d'importazione.

Stato delle conoscenze (docs/COLLEGAMENTI.md §2): il servizio usato dal committente e' "Risultanze catastali" tramite
Entratel. Non sono disponibili, nel repository o nelle pagine pubbliche consultate, ne' un'interfaccia documentata
ne' il formato dei risultati. Quindi:
- il trasporto reale e' un Protocol con una sola implementazione `TrasportoEntratelDaCollaudare`, che NON contatta
  alcun endpoint e restituisce l'azione da far svolgere all'utente (esito `da_collaudare`);
- `TrasportoSimulato` riproduce sequenze di risposte (autenticazione, pagine, sessione scaduta) su fixture sintetiche
  (esito `simulazione`);
- i risultati sono conservati come originali (artefatti con impronta) piu' una rappresentazione interna normalizzata
  (`FORMATO_INTERNO`), che NON e' il formato dell'Agenzia: il convertitore dal formato reale resta da collaudare.

Le credenziali e i cookie di sessione non entrano mai qui: l'autenticazione la svolge l'utente nello strumento
ufficiale; il job conserva solo lo stato della sessione (attiva/scaduta) e il punto di ripresa (pagina).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Protocol, runtime_checkable

from .. import valori as V
from ..archivio import Archivio
from ..errori import DatiNonValidi, ora
from .base import DepositoArtefatti, Esito, RegistroJob, RisultatoAdattatore, risultato_da_job

TIPO_JOB = "catasto_entratel"
FORMATO_INTERNO = "successioni.catasto.v1"
SERVIZIO = "Risultanze catastali (Entratel)"

# Stati della lavorazione (persistiti nella colonna job.stato)
AVVIATO, ATTESA_UTENTE, SESSIONE_SCADUTA = "avviato", "attesa_utente", "sessione_scaduta"
COMPLETATO, PARZIALE, ERRORE, ANNULLATO = "completato", "parziale", "errore", "annullato"
APERTI = (AVVIATO, ATTESA_UTENTE, SESSIONE_SCADUTA)
TERMINALI = (COMPLETATO, PARZIALE, ERRORE, ANNULLATO)

CAMPI_IDENTIFICATIVI = ("tipo", "comune", "sezione", "foglio", "particella", "subalterno")
CAMPI_NOTI = {"catasto", "comune", "codice_comune", "sezione", "foglio", "particella", "subalterno", "graffati",
              "porzione", "categoria", "classe", "consistenza", "superficie", "rendita", "reddito_dominicale",
              "reddito_agrario", "qualita", "indirizzo", "titolarita", "partita", "data_situazione"}


# --------------------------------------------------------------------------------------- trasporto
@dataclass
class RispostaCatasto:
    """Risposta di un trasporto. `tipo`: autenticazione_richiesta | sessione_scaduta | risultati | errore |
    non_disponibile. Con `risultati`, `originale` sono i byte ricevuti (conservati tal quali)."""

    tipo: str
    immobili: list[dict] = field(default_factory=list)
    originale: bytes | None = None
    formato: str | None = None
    completo: bool = False
    pagina_successiva: str | None = None
    limiti: list[str] = field(default_factory=list)  # es. "graffati non restituiti dal servizio"
    messaggio: str = ""
    provenienza: dict = field(default_factory=dict)


@runtime_checkable
class TrasportoCatasto(Protocol):
    reale: bool

    def interroga(self, ambito: dict, pagina: str | None, *, autenticazione_confermata: bool) -> RispostaCatasto: ...


ISTRUZIONI_ENTRATEL = (
    "Acquisizione delle risultanze catastali via Entratel — passaggio da collaudare con il committente:\n"
    "1. Accedere all'area riservata Entratel con le proprie credenziali (mai inserite in questo programma).\n"
    "2. Aprire il servizio di consultazione delle risultanze catastali usato dallo studio e impostare l'ambito "
    "indicato (soggetto, catasto, territorio).\n"
    "3. Salvare i risultati nel formato offerto dal servizio senza modificarli e registrarli nel programma "
    "(registra_originale): il file viene conservato con impronta.\n"
    "4. Annotare percorso del menu, filtri disponibili, formato e limiti (graffati, porzioni, paginazione) in "
    "docs/COLLAUDO_RIPRENDIBILE.md (A13): serviranno a scrivere il convertitore e, se esiste, il collegamento diretto."
)


class TrasportoEntratelDaCollaudare:
    """Trasporto reale non ancora disponibile: non contatta nulla e chiede il passaggio dell'utente."""

    reale = True

    def interroga(self, ambito: dict, pagina: str | None, *, autenticazione_confermata: bool) -> RispostaCatasto:
        return RispostaCatasto("non_disponibile", messaggio=ISTRUZIONI_ENTRATEL)


class TrasportoSimulato:
    """Sequenza scriptata di risposte su fixture sintetiche. Ogni chiamata consuma il passo successivo.

    `passi`: lista di dict {"tipo": ..., "immobili": [...], "completo": bool, "limiti": [...]}; il passo
    `autenticazione_richiesta` viene superato solo con `autenticazione_confermata=True`. Lo stato vive nel
    processo: dopo un riavvio la sessione e' persa (come un cookie reale) e va riconfermata.
    """

    reale = False

    def __init__(self, passi: list[dict]):
        self.passi = list(passi)
        self.i = 0
        self.chiamate: list[dict] = []

    def interroga(self, ambito: dict, pagina: str | None, *, autenticazione_confermata: bool) -> RispostaCatasto:
        self.chiamate.append({"pagina": pagina, "autenticazione_confermata": autenticazione_confermata})
        if self.i >= len(self.passi):
            return RispostaCatasto("errore", messaggio="simulazione: nessun passo residuo")
        p = self.passi[self.i]
        if p["tipo"] == "autenticazione_richiesta":
            if not autenticazione_confermata:
                return RispostaCatasto("autenticazione_richiesta", messaggio="simulazione: autenticarsi")
            self.i += 1
            if self.i >= len(self.passi):  # pragma: no cover - scenario mal scritto
                return RispostaCatasto("errore", messaggio="simulazione: nessun passo dopo l'autenticazione")
            p = self.passi[self.i]
        self.i += 1
        if p["tipo"] != "risultati":
            return RispostaCatasto(p["tipo"], messaggio=p.get("messaggio", "simulazione"))
        corpo = {"formato": FORMATO_INTERNO, "_nota": "SIMULAZIONE: dati sintetici", "immobili": p["immobili"]}
        return RispostaCatasto("risultati", immobili=p["immobili"], formato=FORMATO_INTERNO,
                               originale=json.dumps(corpo, ensure_ascii=False, sort_keys=True).encode(),
                               completo=bool(p.get("completo")), pagina_successiva=p.get("pagina_successiva"),
                               limiti=list(p.get("limiti", [])),
                               provenienza={"servizio": "simulazione", "data_estrazione": p.get("data", ora())})


# ----------------------------------------------------------------------------------- normalizzazione
def _norm_id(v) -> str:
    """Identificativo catastale normalizzato per il confronto: maiuscolo, senza spazi, numeri senza zeri iniziali."""
    if v is None:
        return ""
    s = re.sub(r"\s+", "", str(v)).upper()
    return str(int(s)) if s.isdigit() else s


def chiave_immobile(tipo: str | None, comune, sezione, foglio, particella, subalterno) -> str:
    """Chiave di confronto dei duplicati: comune+sezione+foglio+particella+subalterno, distinta per catasto
    (terreni/fabbricati), perche' gli stessi foglio e particella possono comparire in entrambi."""
    t = {"T": "terreno", "F": "fabbricato"}.get(str(tipo or "").upper(), tipo or "")
    return "|".join([t, _norm_id(comune), _norm_id(sezione), _norm_id(foglio), _norm_id(particella),
                     _norm_id(subalterno)])


def chiave_da_bene(b: dict) -> str:
    return chiave_immobile(b.get("tipo"), b.get("comune"), b.get("sezione"), b.get("foglio"), b.get("particella"),
                           b.get("subalterno"))


def chiave_da_immobile(im: dict) -> str:
    return chiave_immobile(im.get("catasto"), im.get("codice_comune") or im.get("comune"), im.get("sezione"),
                           im.get("foglio"), im.get("particella"), im.get("subalterno"))


def id_bene(chiave: str) -> str:
    """Identificativo stabile del bene acquisito (stessa chiave -> stesso id: nessun doppione fra importazioni)."""
    return "b_" + hashlib.sha256(("catasto|" + chiave).encode()).hexdigest()[:12]


def normalizza(immobili: list[dict]) -> tuple[list[dict], list[dict]]:
    """Restituisce (immobili normalizzati e deduplicati, segnalazioni). I campi sconosciuti sono conservati in
    `altri_campi`; nessun valore viene inventato o derivato."""
    out: dict[str, dict] = {}
    segn: list[dict] = []
    for i, im in enumerate(immobili):
        noti = {k: v for k, v in im.items() if k in CAMPI_NOTI}
        altri = {k: v for k, v in im.items() if k not in CAMPI_NOTI}
        if not (noti.get("foglio") and noti.get("particella")) or str(noti.get("catasto", "")).upper() not in ("T", "F"):
            segn.append({"codice": "IMMOBILE_INCOMPLETO", "indice": i,
                         "messaggio": "catasto/foglio/particella mancanti: non importabile, conservato nell'originale"})
            continue
        k = chiave_da_immobile(noti)
        rec = {**noti, "catasto": str(noti["catasto"]).upper(), "chiave": k, "altri_campi": altri}
        if k in out:
            if out[k] != rec:
                segn.append({"codice": "DUPLICATO_DIVERSO", "chiave": k,
                             "messaggio": "stesso identificativo restituito due volte con dati diversi: "
                                          "conservata la prima occorrenza, verificare"})
            continue
        out[k] = rec
        if altri:
            segn.append({"codice": "CAMPI_NON_RICONOSCIUTI", "chiave": k, "campi": sorted(altri),
                         "messaggio": "campi conservati ma non importati"})
        if im.get("graffati"):
            segn.append({"codice": "GRAFFATI", "chiave": k, "graffati": im["graffati"],
                         "messaggio": "particelle graffate: verificarne l'inserimento (non importate come beni)"})
        if im.get("porzione"):
            segn.append({"codice": "PORZIONE", "chiave": k, "porzione": im["porzione"],
                         "messaggio": "porzione di particella: verificare l'identificazione"})
    return list(out.values()), segn


def _quota_defunto(im: dict, cf_defunto: str | None) -> tuple[dict | None, str | None, list[dict]]:
    segn = []
    tit = [t for t in im.get("titolarita") or [] if cf_defunto and str(t.get("cf", "")).upper() == cf_defunto.upper()]
    if not tit:
        segn.append({"codice": "DEFUNTO_NON_TITOLARE", "chiave": im["chiave"],
                     "messaggio": "il defunto non compare tra i titolari restituiti: diritto e quota non proposti"})
        return None, None, segn
    if len(tit) > 1:
        segn.append({"codice": "TITOLARITA_MULTIPLE", "chiave": im["chiave"],
                     "messaggio": "piu' titolarita' del defunto sullo stesso immobile: diritto e quota da inserire"})
        return None, None, segn
    t = tit[0]
    q = t.get("quota")
    quota = None
    try:
        if isinstance(q, dict):
            f = Fraction(int(q["num"]), int(q["den"]))
            quota = {"num": f.numerator, "den": f.denominator} if 0 <= f <= 1 else None
    except (KeyError, ValueError, ZeroDivisionError, TypeError):
        quota = None
    if quota is None:
        segn.append({"codice": "QUOTA_NON_LEGGIBILE", "chiave": im["chiave"], "messaggio": "quota non proposta"})
    return quota, t.get("diritto"), segn


def proponi_importazione(immobili: list[dict], dati_pratica: dict, *, cf_defunto: str | None = None,
                         selezione: list[str] | None = None) -> dict:
    """Confronta gli immobili acquisiti con i beni della pratica e propone operazioni per `Servizio.aggiorna`
    (`{op, coll, id, campi}`, da applicare con origine='acquisito'). Non sovrascrive campi inseriti o confermati
    dall'utente: li elenca come conflitti. `selezione` = chiavi da importare (None = tutte)."""
    beni = {chiave_da_bene(b): b for b in dati_pratica.get("beni", [])}
    if cf_defunto is None:
        cf_defunto = next((p.get("codice_fiscale") for p in dati_pratica.get("persone", [])
                           if p.get("ruolo") == "defunto"), None)
    operazioni, conflitti, invariati, nuovi, aggiornati, segnalazioni = [], [], [], [], [], []
    for im in immobili:
        k = im["chiave"]
        if selezione is not None and k not in selezione:
            continue
        campi = {"tipo": "terreno" if im["catasto"] == "T" else "fabbricato",
                 "comune": im.get("codice_comune") or im.get("comune"), "sezione": im.get("sezione"),
                 "foglio": im.get("foglio"), "particella": im.get("particella"), "subalterno": im.get("subalterno"),
                 "categoria": im.get("categoria") if im["catasto"] == "F" else None,
                 "rendita": im.get("rendita") if im["catasto"] == "F" else None}
        quota, diritto, s = _quota_defunto(im, cf_defunto)
        segnalazioni += s
        campi["quota_defunto"], campi["diritto"] = quota, diritto
        campi = {c: (str(v) if not isinstance(v, dict) else v) for c, v in campi.items() if v not in (None, "")}
        if "rendita" in campi:
            try:
                V.parse_importo(campi["rendita"])
            except V.ValoreNonValido:
                segnalazioni.append({"codice": "IMPORTO_NON_VALIDO", "chiave": k, "valore": campi.pop("rendita"),
                                     "messaggio": "rendita non in formato decimale con punto: non proposta"})
        segnalazioni.append({"codice": "SITUAZIONE_AL_DECESSO", "chiave": k,
                             "messaggio": "titolarita' catastale da verificare alla data del decesso; "
                                          "l'acquisizione non prova la proprieta' ne' agevolazioni"})
        non_mappati = sorted(c for c in ("reddito_dominicale", "reddito_agrario", "classe", "consistenza",
                                         "superficie", "qualita", "indirizzo", "partita") if im.get(c))
        if non_mappati:
            segnalazioni.append({"codice": "CAMPI_SENZA_DESTINAZIONE", "chiave": k, "campi": non_mappati,
                                 "messaggio": "dati restituiti senza campo corrispondente nel modello: conservati "
                                              "nell'acquisizione (vedi docs/PROPOSTE_collegamenti.md)"})
        esistente = beni.get(k)
        if esistente is None:
            operazioni.append({"op": "upsert", "coll": "beni", "id": id_bene(k), "campi": campi})
            nuovi.append(k)
            continue
        origini = esistente.get("_origine", {})
        diff, conf = {}, []
        for c, v in campi.items():
            if esistente.get(c) == v or (c in CAMPI_IDENTIFICATIVI and esistente.get(c)):
                continue  # identificativi gia' uguali a meno della normalizzazione (es. zeri iniziali)
            if c in esistente and origini.get(c) in ("inserito", "confermato", "proposto_assistente"):
                conf.append({"campo": c, "attuale": esistente.get(c), "acquisito": v, "origine": origini.get(c)})
            else:
                diff[c] = v
        if conf:
            conflitti.append({"chiave": k, "bene_id": esistente["id"], "campi": conf})
        if diff:
            operazioni.append({"op": "upsert", "coll": "beni", "id": esistente["id"], "campi": diff})
            aggiornati.append(k)
        elif not conf:
            invariati.append(k)
    return {"operazioni": operazioni, "origine": "acquisito", "nuovi": nuovi, "aggiornati": aggiornati,
            "invariati": invariati, "conflitti": conflitti, "segnalazioni": segnalazioni,
            "nota": "proposta: applicarla con Servizio.aggiorna(pratica_id, revisione, operazioni, origine='acquisito')"}


# ------------------------------------------------------------------------------------- adattatore
class CatastoEntratelAdattatore:
    """Implementa il Protocol `CatastoEntratel` sulla tabella job. Riprendibile da qualunque processo."""

    def __init__(self, archivio: Archivio, trasporto: TrasportoCatasto | None = None):
        self.arch = archivio
        self.job = RegistroJob(archivio)
        self.deposito = DepositoArtefatti(archivio)
        self.trasporto = trasporto or TrasportoEntratelDaCollaudare()

    @property
    def _esito_base(self) -> Esito:
        return Esito.DA_COLLAUDARE if self.trasporto.reale else Esito.SIMULAZIONE

    @staticmethod
    def _ambito(ambito: dict) -> dict:
        if not isinstance(ambito, dict) or not ambito.get("soggetto_cf"):
            raise DatiNonValidi("ambito della ricerca: serve almeno soggetto_cf (codice fiscale del soggetto)")
        cat = ambito.get("catasto", "entrambi")
        if cat not in ("T", "F", "entrambi"):
            raise DatiNonValidi("ambito.catasto: T, F o entrambi")
        return {"soggetto_cf": str(ambito["soggetto_cf"]).upper(), "catasto": cat,
                "territorio": ambito.get("territorio", "nazionale"), "note": ambito.get("note")}

    def avvia(self, pratica_id: str, ambito: dict, *, chiave: str | None = None, **kw) -> RisultatoAdattatore:
        amb = self._ambito(ambito)
        j, nuovo = self.job.crea(TIPO_JOB, pratica_id, {"ambito": amb, "servizio": SERVIZIO,
                                                        "trasporto": type(self.trasporto).__name__},
                                 stato=AVVIATO, chiave=chiave,
                                 risultato={"immobili": [], "originali": [], "pagina": None, "pagine": 0,
                                            "limiti": [], "sessione": "assente"})
        if not nuovo and j["stato"] != AVVIATO:
            return self.leggi(j["job_id"])
        return self._avanza(j["job_id"], autenticazione_confermata=False)

    def riprendi(self, job_id: str, *, autenticazione_confermata: bool = False, **kw) -> RisultatoAdattatore:
        """Riprende dopo l'azione dell'utente, una sessione scaduta o la chiusura del client. Nulla viene
        ripetuto: le pagine gia' acquisite restano, si riparte dalla pagina registrata."""
        j = self.job.leggi(job_id, TIPO_JOB)
        if j["stato"] in TERMINALI:
            return self.leggi(job_id)
        return self._avanza(job_id, autenticazione_confermata=autenticazione_confermata)

    def chiudi_parziale(self, job_id: str, motivo: str) -> RisultatoAdattatore:
        """L'utente interrompe: i risultati acquisiti restano, marcati come parziali."""
        self.job.transizione(job_id, APERTI, PARZIALE, patch={"completezza": {"completo": False, "motivo": motivo}},
                             nota="chiuso come parziale dall'utente")
        return self.leggi(job_id)

    def _avanza(self, job_id: str, *, autenticazione_confermata: bool) -> RisultatoAdattatore:
        for _ in range(1000):  # limite di sicurezza sulle pagine per chiamata
            j = self.job.leggi(job_id, TIPO_JOB)
            r = j["risultato"]
            amb = j["input"]["ambito"]
            resp = self.trasporto.interroga(amb, r.get("pagina"), autenticazione_confermata=autenticazione_confermata)
            if resp.tipo == "autenticazione_richiesta":
                self.job.transizione(job_id, APERTI, ATTESA_UTENTE, patch={
                    "sessione": "assente", "azione_richiesta": "Autenticarsi in Entratel nello strumento ufficiale, "
                    "poi riprendere la lavorazione (le credenziali non passano da questo programma)."},
                    nota="autenticazione richiesta")
                break
            if resp.tipo == "sessione_scaduta":
                self.job.transizione(job_id, APERTI, SESSIONE_SCADUTA, patch={
                    "sessione": "scaduta", "azione_richiesta": "Sessione scaduta: autenticarsi di nuovo e riprendere; "
                    f"le {r.get('pagine', 0)} pagine gia' acquisite sono conservate."}, nota="sessione scaduta")
                break
            if resp.tipo == "non_disponibile":
                self.job.transizione(job_id, APERTI, ATTESA_UTENTE, patch={
                    "sessione": "assente", "azione_richiesta": resp.messaggio, "modalita": "da_collaudare"},
                    nota="collegamento reale non disponibile")
                break
            if resp.tipo == "errore":
                self.job.transizione(job_id, APERTI, ERRORE, patch={"azione_richiesta": None,
                                                                     "errore_servizio": resp.messaggio},
                                     nota="errore del servizio", errore=resp.messaggio)
                break
            self._registra_pagina(job_id, resp)
            autenticazione_confermata = True  # la sessione resta valida per le pagine successive
            if not resp.pagina_successiva:
                break
        return self.leggi(job_id)

    def _registra_pagina(self, job_id: str, resp: RispostaCatasto, *, modalita: str = "trasporto") -> None:
        j = self.job.leggi(job_id, TIPO_JOB)
        r = j["risultato"]
        art = self.deposito.salva_bytes(resp.originale or b"", f"risultanze_p{r.get('pagine', 0) + 1}.json",
                                        "risultanze_originali", formato=resp.formato or "sconosciuto")
        grezzi = list(r.get("grezzi", [])) + list(resp.immobili)
        imm, segn = normalizza(grezzi)
        limiti = sorted(set(r.get("limiti", [])) | set(resp.limiti))
        fine = not resp.pagina_successiva
        completo = fine and resp.completo and not limiti
        stato = (COMPLETATO if completo else PARZIALE) if fine else AVVIATO  # avviato = acquisizione in corso
        prov = {"servizio": SERVIZIO if self.trasporto.reale else "simulazione", "modalita": modalita,
                "acquisito_il": ora(), **resp.provenienza}
        patch = {"immobili": imm, "grezzi": grezzi, "segnalazioni_normalizzazione": segn, "originali": r.get("originali", []) + [art],
                 "pagina": resp.pagina_successiva, "pagine": r.get("pagine", 0) + 1, "limiti": limiti,
                 "sessione": "attiva", "provenienza": prov, "azione_richiesta": None,
                 "completezza": {"completo": completo, "motivo": None if completo else
                                 ("in corso" if not fine else "; ".join(limiti) or "il servizio non conferma la "
                                  "completezza dei risultati")}}
        self.job.transizione(job_id, APERTI, stato, patch=patch, nota=f"pagina {patch['pagine']} acquisita")

    def registra_originale(self, job_id: str, contenuto: bytes, *, formato: str, fonte: str) -> RisultatoAdattatore:
        """Continuita' operativa: l'utente registra il file scaricato da Entratel. Viene sempre conservato; e' letto
        solo se nel formato interno (il convertitore del formato reale e' da collaudare)."""
        j = self.job.leggi(job_id, TIPO_JOB)
        if formato != FORMATO_INTERNO:
            art = self.deposito.salva_bytes(contenuto, "risultanze_originali", "risultanze_originali",
                                            formato=formato, fonte=fonte)
            self.job.transizione(job_id, None, None, patch={
                "originali": j["risultato"].get("originali", []) + [art],
                "azione_richiesta": f"File conservato (sha256 {art['sha256']}); formato '{formato}' non ancora "
                                    "convertibile: fornire un esempio per scrivere il convertitore (A13)."},
                nota="originale conservato, formato non supportato")
            return self.leggi(job_id)
        corpo = json.loads(contenuto.decode("utf-8"))
        resp = RispostaCatasto("risultati", immobili=corpo.get("immobili", []), originale=contenuto,
                               formato=formato, completo=bool(corpo.get("completo")), limiti=corpo.get("limiti", []),
                               provenienza={"fonte": fonte})
        self._registra_pagina(job_id, resp, modalita="registrazione_manuale")
        return self.leggi(job_id)

    def leggi(self, job_id: str) -> RisultatoAdattatore:
        j = self.job.leggi(job_id, TIPO_JOB)
        r = j["risultato"]
        return risultato_da_job(j, self._esito_base, artefatti=r.get("originali", []),
                                azione_richiesta=r.get("azione_richiesta"), ambito=j["input"]["ambito"],
                                pagine=r.get("pagine", 0), immobili=len(r.get("immobili", [])),
                                completezza=r.get("completezza"), sessione=r.get("sessione"))

    def leggi_risultati(self, job_id: str, **kw) -> RisultatoAdattatore:
        j = self.job.leggi(job_id, TIPO_JOB)
        r = j["risultato"]
        res = self.leggi(job_id)
        res.dettaglio.update({"immobili": r.get("immobili", []), "provenienza": r.get("provenienza"),
                              "segnalazioni": r.get("segnalazioni_normalizzazione", []), "limiti": r.get("limiti", [])})
        return res

    def proponi(self, job_id: str, dati_pratica: dict, *, selezione: list[str] | None = None,
                cf_defunto: str | None = None) -> RisultatoAdattatore:
        """Proposta di importazione selettiva per la pratica (nessuna scrittura sulla pratica)."""
        j = self.job.leggi(job_id, TIPO_JOB)
        prop = proponi_importazione(j["risultato"].get("immobili", []), dati_pratica, cf_defunto=cf_defunto,
                                    selezione=selezione)
        if j["stato"] != COMPLETATO:
            prop["segnalazioni"].insert(0, {"codice": "ACQUISIZIONE_NON_COMPLETA", "messaggio":
                                            f"lavorazione in stato '{j['stato']}': i risultati possono essere "
                                            "incompleti"})
        prop["segnalazioni"] = j["risultato"].get("segnalazioni_normalizzazione", []) + prop["segnalazioni"]
        for lim in j["risultato"].get("limiti", []):
            prop["segnalazioni"].insert(0, {"codice": "LIMITE_DEL_SERVIZIO", "messaggio": lim})
        res = self.leggi(job_id)
        res.dettaglio["proposta"] = prop
        return res
