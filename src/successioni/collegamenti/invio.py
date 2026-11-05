"""Preparazione, conferma, trasmissione, riconciliazione e ricevute della dichiarazione SUC13.

Principi (specifica §9, §10, A17-A19):
- la COPIA CONGELATA (job `invio_copia`) conserva elaborati con impronta, revisione e impronta dichiarativa della
  pratica, importi e profilo; la conferma nell'app riguarda la sua `impronta_conferma` e decade se la pratica
  cambia nei dati dichiarativi (una nota interna non la invalida);
- ogni TENTATIVO (job `invio_tentativo`) ha una chiave di richiesta: la stessa richiesta ripetuta non genera un
  secondo invio nel NOSTRO sistema (nessuna garanzia equivalente dal servizio dell'Agenzia);
- lo stato `in_trasmissione` e' scritto PRIMA di chiamare il trasporto: se il processo cade o la rete si interrompe
  l'esito e' incerto e si passa SOLO dalla riconciliazione; mai reinvio automatico;
- un esito finale (trasmesso con protocollo, rifiutato con motivazione) non viene sovrascritto da errori successivi;
- ricevute ed esiti successivi sono documenti distinti, associati al protocollo, con tipo dichiarato (mai dedotto
  dall'ordine di arrivo); un pagamento negativo non cancella la registrazione.

NESSUNA TRASMISSIONE REALE: l'unico trasporto "reale" e' `TrasportoManualeTracciato`, che non invia nulla e
chiede all'utente di usare gli strumenti ufficiali (Desktop Telematico / Entratel-Multifile), poi riconcilia.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol, runtime_checkable

from .. import valori as V
from ..archivio import Archivio
from ..errori import ConflittoRevisione, DatiNonValidi, NonTrovato, ora
from .base import (ConfermaNonValida, DepositoArtefatti, Esito, RegistroJob, ReinvioNonAmmesso,
                   RisultatoAdattatore, TransizioneNonAmmessa, impronta_json, risultato_da_job, sha256_bytes)

TIPO_COPIA, TIPO_TENTATIVO, TIPO_RICEVUTA = "invio_copia", "invio_tentativo", "ricevuta_suc13"

# Stati della copia congelata
PREPARATA, CONFERMATA, IN_INVIO, TRASMESSA, RIFIUTATA, OBSOLETA = (
    "preparata", "confermata", "in_invio", "trasmessa", "rifiutata", "obsoleta")
# Stati del tentativo
CREATO, IN_TRASMISSIONE, ESITO_INCERTO, ATTESA_INVIO_MANUALE = (
    "creato", "in_trasmissione", "esito_incerto", "attesa_invio_manuale")
TRASMESSO, RIFIUTATO, NON_TRASMESSO, ANNULLATO = "trasmesso", "rifiutato", "non_trasmesso", "annullato"
DA_RICONCILIARE = (IN_TRASMISSIONE, ESITO_INCERTO, ATTESA_INVIO_MANUALE)
FINALI_TENTATIVO = (TRASMESSO, RIFIUTATO, NON_TRASMESSO, ANNULLATO)

FONTE_RICEVUTE = "Succ_FASCICOLO_I_Nov_23.pdf, p. PDF 5, 'RICEVUTE TELEMATICHE'"
# Documenti restituiti dopo l'invio (fonte: FONTE_RICEVUTE). Il tipo lo indica chi registra il documento.
TIPI_RICEVUTA = {
    "trasmissione": {"desc": "prima ricevuta: avvenuta trasmissione del file", "esiti": ()},
    "registrazione": {"desc": "seconda ricevuta: esito dei controlli formali, estremi di registrazione o motivi "
                              "dello scarto", "esiti": ("registrata", "scartata")},
    "pagamento": {"desc": "terza ricevuta (solo con addebito in conto): esito del pagamento",
                  "esiti": ("positivo", "negativo")},
    "copia_semplice": {"desc": "ulteriore ricevuta: copia semplice con estremi di registrazione (Ricerca documenti)",
                       "esiti": ()},
    "richiesta_regolarizzazione": {"desc": "richiesta di regolarizzazione dell'ufficio", "esiti": ()},
    "attestazione": {"desc": "attestazione di avvenuta presentazione (copia conforme), se richiesta in frontespizio",
                     "esiti": ()},
    "volture": {"desc": "quinta ricevuta: esito della domanda di volture", "esiti": ("complete", "parziali",
                                                                                      "negative")},
    "da_classificare": {"desc": "documento ricevuto di tipo non ancora indicato", "esiti": ()},
}

RUOLI_ELABORATO = ("telematico", "file_controllato", "stampa", "diagnostico", "altro")


# ------------------------------------------------------------------------------- Entratel-Multifile
# Ricognizione dal manuale ufficiale (v1.1.1 del 19/06/2018; prodotto corrente 1.7.6 del 01/10/2026): vedi
# docs/COLLEGAMENTI.md §4. Da confrontare con la versione installata: nulla qui viene eseguito.
MULTIFILE = {
    "fonte": "https://telematici.agenziaentrate.gov.it/pdf/Istruzioni_Entratel-Multifile.pdf (v1.1.1, 61 pp., "
             "scaricato 2026-11-01, sha256 cd11f3324a6cbe55adc2f619f34951adc6db144c6792643bb222dde9f83ef713)",
    "catena": ["XML SUC13 -> controllo SUC13 (file controllato .dcm)", "AUTENTICA (.dcm -> .ccf, certificati UTEF.P12/"
               "UTEC.P12 + password ambiente di sicurezza)", "INVIO (.ccf, utente/password/PIN Entratel) -> "
               "protocollo in .esi", "DOWNLOAD RICEVUTE (richiesta R01-R04 .json -> .zip con _stato.json e .rcc)",
               "APRI RICEVUTE (.rcc -> .rel/.rel.p7m)", "VISUALIZZA (.rel -> PDF)"],
    "comandi": {"autentica": "prog/runAutentica.bat|.sh", "firma": "prog/runFirma.bat|.sh",
                "invio": "prog/runInvio.bat|.sh", "download": "prog/runDownload.bat|.sh",
                "apri_ricevute": "prog/runRicevute.bat|.sh", "pdf_ricevute": "prog/runVisualizzaRicevute.bat|.sh"},
    "configurazioni": ["config/autenticaMF.cfg", "config/firmaMF.cfg", "config/invioMF.cfg",
                       "config/downloadMF.cfg", "config/apriMF.cfg", "config/visualizzaMF.cfg"],
    "cartelle": ["certificato_utente", "file_da_autenticare", "file_da_firmare", "file_da_inviare", "file_esiti",
                 "file_firmati", "file_inviati", "ricevute_da_elaborare", "ricevute_elaborate", "ricevute_pdf",
                 "richieste_download", "richieste_elaborate", "stato_invii"],
    "limiti": ["400 file per esecuzione (ARG5/ARG9 nei .cfg)", "50 richieste di download o esito al giorno per "
               "utente", "R02: intervallo massimo una settimana", "R04: massimo 200 ricevute per richiesta, 500 al "
               "giorno", "proxy con autenticazione non gestito"],
    "esiti_procedura": "file_esiti/esito_GGMMAAAA_hhmmss.esi: JSON con tipoOperazione, resultCode ('00' positivo), "
                       "startDate, endDate, fileName, versioneApplicazione, protocollo (INVIO)",
    "stato_invii": "R0x_<timestamp>_<id>_stato.json: ricevuteList[{codScartoFornitura?, tipoFornitura, nomeFile, "
                   "data, stato (Ricevuto|In elaborazione|Elaborato|Scartato), protocollo, idRichiesta}], "
                   "result{esito, resultCode 00..08|99}",
    "attenzione": "i file .cfg possono contenere dati di accesso: il programma non li legge, non li copia e non li "
                  "registra (da verificare sulla versione installata)",
}


def leggi_esi(testo: str) -> list[dict]:
    """Legge un file di esito Multifile (.esi): oggetti JSON, uno per flusso. Righe non JSON ignorate e contate."""
    out, dec, i = [], json.JSONDecoder(), 0
    t = testo.strip()
    while i < len(t):
        j = t.find("{", i)
        if j < 0:
            break
        try:
            obj, fine = dec.raw_decode(t, j)
        except ValueError:
            i = j + 1
            continue
        if isinstance(obj, dict):
            out.append({k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in obj.items()})
        i = fine
    return out


def leggi_stato_invii(testo: str) -> dict:
    """Legge `..._stato.json` (allegato 2 del manuale Multifile)."""
    d = json.loads(testo)
    if not isinstance(d, dict) or "result" not in d:
        raise DatiNonValidi("file di stato invii non riconosciuto (manca 'result')")
    return {"ricevute": list(d.get("ricevuteList") or []), "result": d["result"]}


def richiesta_download(tipo: str, nome_utente: str, *, protocollo: str = "", data_da: str = "", data_a: str = "",
                       cf_incaricante: str = "", sede_incaricante: str = "") -> dict:
    """Contenuto di una richiesta R01-R04 (allegato 1 del manuale). Non contiene credenziali: `nomeUtente` e'
    l'identificativo di accesso, la password la chiede Multifile."""
    if tipo not in ("R01", "R02", "R03", "R04"):
        raise DatiNonValidi("tipoRichiesta: R01, R02, R03 o R04")
    if tipo in ("R01", "R03") and not protocollo:
        raise DatiNonValidi("R01/R03 richiedono il numero di protocollo")
    if tipo in ("R02", "R04") and not (data_da and data_a):
        raise DatiNonValidi("R02/R04 richiedono data_da e data_a (GG/MM/AAAAThh:mm)")
    return {"tipoRichiesta": tipo, "nomeUtente": nome_utente, "codiceFiscaleIncaricante": cf_incaricante,
            "sedeIncaricante": sede_incaricante, "numeroProtocollo": protocollo, "data_da": data_da, "data_a": data_a}


# ------------------------------------------------------------------------------------- trasporto
@dataclass
class RispostaInvio:
    """`tipo`: accettato (protocollo assegnato) | rifiutato (esito finale negativo con motivo) | incerto |
    non_trasmesso (prova che il file non e' stato ricevuto) | non_disponibile (nessun invio eseguito) |
    sconosciuto (la consultazione non permette di concludere)."""

    tipo: str
    protocollo: str | None = None
    motivo: str = ""
    originale: bytes | None = None
    data: str | None = None
    candidati: list[dict] = field(default_factory=list)


@runtime_checkable
class TrasportoInvio(Protocol):
    reale: bool       # False = simulazione
    automatico: bool  # False = l'invio lo esegue l'utente con gli strumenti ufficiali

    def trasmetti(self, file: bytes, nome: str, metadati: dict) -> RispostaInvio: ...

    def consulta(self, riferimento: dict) -> RispostaInvio: ...


ISTRUZIONI_INVIO_MANUALE = (
    "Invio da eseguire con gli strumenti ufficiali (questo programma NON trasmette):\n"
    "1. Esportare il file indicato (impronta SHA-256 riportata) senza modificarlo.\n"
    "2. Con Desktop Telematico (Entratel) o Entratel-Multifile: controllo SUC13 -> file controllato (.dcm) -> "
    "Autentica (.ccf) -> Invia. Le credenziali restano nello strumento ufficiale.\n"
    "3. Registrare l'esito nel programma con 'riconcilia': protocollo assegnato, oppure il file .esi di Multifile, "
    "oppure la dichiarazione verificata che l'invio non e' avvenuto.\n"
    "Finche' l'esito non e' riconciliato non e' possibile avviare un altro tentativo per questa copia."
)


class TrasportoManualeTracciato:
    """Trasporto reale disponibile oggi: nessun invio; l'utente invia con gli strumenti ufficiali e riconcilia."""

    reale = True
    automatico = False

    def trasmetti(self, file: bytes, nome: str, metadati: dict) -> RispostaInvio:
        try:
            from .. import strumenti
            sha = (metadati or {}).get("sha256") or (metadati or {}).get("xml_sha256")
            return RispostaInvio("non_disponibile", motivo=strumenti.istruzioni_invio(nome, sha))
        except Exception:   # le istruzioni dinamiche sono un aiuto: in caso di problema vale il testo generale
            return RispostaInvio("non_disponibile", motivo=ISTRUZIONI_INVIO_MANUALE)

    def consulta(self, riferimento: dict) -> RispostaInvio:
        return RispostaInvio("sconosciuto", motivo="consultazione automatica non disponibile: fornire evidenze "
                                                   "(protocollo, .esi, _stato.json)")


class TrasportoSimulato:
    """Servizio fittizio con memoria propria (lato 'server') per provare rete interrotta e riconciliazione.

    `guasto`: None | "timeout_dopo_ricezione" (il server registra il file e assegna il protocollo, ma la risposta
    si perde) | "timeout_prima" (la richiesta non arriva) | "rifiuto" (scarto immediato con motivo).
    """

    reale = False
    automatico = True

    def __init__(self, guasto: str | None = None, motivo_rifiuto: str = "file non conforme (simulazione)"):
        self.guasto = guasto
        self.motivo_rifiuto = motivo_rifiuto
        self.ricevuti: dict[str, dict] = {}  # sha256 -> {protocollo, nome}
        self.chiamate_trasmetti = 0
        self.consultazione_guasta = False

    def trasmetti(self, file: bytes, nome: str, metadati: dict) -> RispostaInvio:
        self.chiamate_trasmetti += 1
        if self.guasto == "timeout_prima":
            raise TimeoutError("simulazione: connessione interrotta prima della ricezione")
        if self.guasto == "rifiuto":
            return RispostaInvio("rifiutato", motivo=self.motivo_rifiuto)
        prot = f"SIM{len(self.ricevuti) + 1:014d}"
        self.ricevuti[sha256_bytes(file)] = {"protocollo": prot, "nome": nome}
        if self.guasto == "timeout_dopo_ricezione":
            raise TimeoutError("simulazione: risposta persa dopo la ricezione")
        return RispostaInvio("accettato", protocollo=prot, originale=b"SIMULAZIONE prima ricevuta " + prot.encode())

    def consulta(self, riferimento: dict) -> RispostaInvio:
        if self.consultazione_guasta:
            raise ConnectionError("simulazione: consultazione non raggiungibile")
        r = self.ricevuti.get(riferimento.get("sha256", ""))
        if r:
            return RispostaInvio("accettato", protocollo=r["protocollo"])
        return RispostaInvio("sconosciuto", motivo="simulazione: nessun file con questa impronta")


# ------------------------------------------------------------------------------------------ servizio
LettorePratica = Callable[[str], dict]


def _lettore_predefinito(archivio: Archivio) -> LettorePratica:
    def leggi(pratica_id: str) -> dict:
        from ..servizio import Servizio  # import locale: il servizio e' del coordinatore
        d = Servizio(archivio).leggi(pratica_id)
        return {"revisione": d["revisione"], "impronta_dichiarativa": d["impronta_dichiarativa"]}
    return leggi


class InvioAdattatore:
    """Implementa i Protocol `InvioSUC13` e `Ricevute` sulla tabella job."""

    def __init__(self, archivio: Archivio, trasporto: TrasportoInvio | None = None,
                 lettore: LettorePratica | None = None):
        self.arch = archivio
        self.job = RegistroJob(archivio)
        self.deposito = DepositoArtefatti(archivio)
        self.trasporto = trasporto or TrasportoManualeTracciato()
        self.lettore = lettore or _lettore_predefinito(archivio)

    # ---------------------------------------------------------------- esiti
    def _esito_operazione(self) -> Esito:
        return Esito.DA_COLLAUDARE if self.trasporto.reale else Esito.SIMULAZIONE

    def _esito_tentativo(self, stato: str) -> Esito:
        """Livello di evidenza del COLLEGAMENTO: simulato -> simulazione; manuale (l'utente invia con gli strumenti
        ufficiali e registra il protocollo) -> da_collaudare anche se il tentativo risulta trasmesso; solo un
        trasporto reale automatico, oggi inesistente, potrebbe dare passato/fallito."""
        if not self.trasporto.reale:
            return Esito.SIMULAZIONE
        if not getattr(self.trasporto, "automatico", False):
            return Esito.DA_COLLAUDARE
        if stato == TRASMESSO:
            return Esito.PASSATO
        if stato == RIFIUTATO:
            return Esito.FALLITO
        return Esito.DA_COLLAUDARE

    # ---------------------------------------------------------------- copia congelata
    def prepara(self, pratica_id: str, *, elaborati: list[dict], importi: dict, profilo: dict,
                controllo_job_id: str | None = None, aspettative: dict | None = None, chiave: str | None = None,
                revisione: int | None = None, **kw) -> RisultatoAdattatore:
        """Congela gli elaborati. `elaborati`: [{"percorso", "ruolo"}] con un solo ruolo 'telematico'.
        `importi`: {nome: decimale con punto}; `profilo`: dati dell'intermediario senza segreti;
        `aspettative`: {"addebito", "voltura_automatica", "attestazione_richiesta"} (bool) per gli esiti attesi."""
        attuale = self.lettore(pratica_id)
        if revisione is not None and revisione != attuale["revisione"]:
            raise ConflittoRevisione("la pratica e' cambiata: rigenerare gli elaborati",
                                     revisione_attesa=revisione, revisione_corrente=attuale["revisione"])
        for k, v in (importi or {}).items():
            try:
                V.parse_importo(v)
            except V.ValoreNonValido as e:
                raise DatiNonValidi(f"importo {k}: {e}") from None
        manifest, artefatti = [], []
        for el in elaborati:
            ruolo = el.get("ruolo")
            if ruolo not in RUOLI_ELABORATO:
                raise DatiNonValidi("ruolo dell'elaborato non ammesso", ammessi=list(RUOLI_ELABORATO))
            p = Path(el["percorso"])
            if not p.is_file():
                raise NonTrovato("elaborato inesistente", percorso=str(p))
            a = self.deposito.salva_file(p, ruolo=f"elaborato_{ruolo}")
            artefatti.append(a)
            manifest.append({"ruolo": ruolo, "nome": a["nome"], "sha256": a["sha256"], "bytes": a["bytes"]})
        if [m["ruolo"] for m in manifest].count("telematico") != 1:
            raise DatiNonValidi("serve esattamente un elaborato con ruolo 'telematico'")
        tel = next(m for m in manifest if m["ruolo"] == "telematico")
        requisiti = self._requisiti_controllo(controllo_job_id, tel["sha256"], attuale["impronta_dichiarativa"])
        base_conf = {"pratica_id": pratica_id, "revisione": attuale["revisione"],
                     "impronta_dichiarativa": attuale["impronta_dichiarativa"], "manifest": manifest,
                     "importi": dict(importi or {}), "profilo": dict(profilo or {})}
        inp = {**base_conf, "controllo_job_id": controllo_job_id, "aspettative": dict(aspettative or {}),
               "impronta_conferma": impronta_json(base_conf), "impronta_manifest": impronta_json(manifest)}
        j, nuovo = self.job.crea(TIPO_COPIA, pratica_id, inp, stato=PREPARATA, chiave=chiave,
                                 risultato={"artefatti": artefatti, "requisiti_mancanti": requisiti,
                                            "conferma": None, "tentativi": []})
        if nuovo:  # le copie precedenti non ancora inviate della stessa pratica sono sostituite
            for vecchia in self.job.elenca(TIPO_COPIA, pratica_id, stati=[PREPARATA, CONFERMATA]):
                if vecchia["job_id"] != j["job_id"]:
                    try:
                        self.job.transizione(vecchia["job_id"], [PREPARATA, CONFERMATA], OBSOLETA, patch={
                            "motivo_obsoleta": f"sostituita dalla copia {j['job_id']}",
                            "conferma_invalidata": vecchia["risultato"].get("conferma")}, nota="sostituita")
                    except TransizioneNonAmmessa:  # pragma: no cover - cambiata nel frattempo
                        pass
        return self.leggi_copia(j["job_id"])

    def _requisiti_controllo(self, controllo_job_id, sha_tel: str, impronta: str) -> list[str]:
        if not controllo_job_id:
            return ["controllo ufficiale non associato alla copia"]
        try:
            c = self.job.leggi(controllo_job_id, "controllo_ufficiale")
        except NonTrovato:
            return [f"controllo ufficiale {controllo_job_id} inesistente"]
        out = []
        r = c["risultato"]
        if r.get("stato_controllo") != "positivo" or r.get("esito") != Esito.PASSATO.value:
            out.append(f"controllo ufficiale non positivo (stato {r.get('stato_controllo')}, esito {r.get('esito')})")
        if c["input"].get("xml_sha256") != sha_tel:
            out.append("il controllo ufficiale riguarda un file diverso dall'elaborato telematico congelato")
        if c["input"].get("impronta_dichiarativa") not in (None, impronta):
            out.append("il controllo ufficiale e' stato eseguito su dati dichiarativi precedenti")
        return out

    def verifica_validita(self, copia_id: str) -> RisultatoAdattatore:
        """Invalida la copia (e la sua conferma) se la pratica e' cambiata nei dati dichiarativi."""
        j = self.job.leggi(copia_id, TIPO_COPIA)
        if j["stato"] in (PREPARATA, CONFERMATA):
            attuale = self.lettore(j["pratica_id"])
            if attuale["impronta_dichiarativa"] != j["input"]["impronta_dichiarativa"]:
                self.job.transizione(copia_id, [PREPARATA, CONFERMATA], OBSOLETA, patch={
                    "motivo_obsoleta": "dati dichiarativi della pratica modificati dopo la preparazione",
                    "revisione_corrente": attuale["revisione"],
                    "conferma_invalidata": j["risultato"].get("conferma")}, nota="copia obsoleta")
        return self.leggi_copia(copia_id)

    def conferma(self, copia_id: str, *, impronta_mostrata: str, utente: str, canale: str = "gui",
                 **kw) -> RisultatoAdattatore:
        """Conferma dall'app (non via MCP) della specifica copia: contenuto, importi e profilo mostrati."""
        if canale != "gui":
            raise ConfermaNonValida("la conferma della trasmissione si da' nell'app, non da " + canale)
        j = self.job.leggi(copia_id, TIPO_COPIA)
        if j["stato"] == CONFERMATA and j["risultato"]["conferma"]["impronta"] == impronta_mostrata:
            return self.verifica_validita(copia_id)
        if j["stato"] != PREPARATA:
            raise ConfermaNonValida(f"copia in stato '{j['stato']}': conferma non ammessa", copia_id=copia_id)
        if impronta_mostrata != j["input"]["impronta_conferma"]:
            raise ConfermaNonValida("la conferma riguarda un contenuto diverso da quello congelato",
                                    attesa=j["input"]["impronta_conferma"])
        if j["risultato"].get("requisiti_mancanti"):
            raise ConfermaNonValida("requisiti mancanti", requisiti=j["risultato"]["requisiti_mancanti"])
        for a in j["risultato"]["artefatti"]:
            self.deposito.leggi(a)  # integrita' degli elaborati congelati
        if self.verifica_validita(copia_id).stato == OBSOLETA:
            raise ConfermaNonValida("la pratica e' cambiata: copia obsoleta, prepararne una nuova")
        self.job.transizione(copia_id, [PREPARATA], CONFERMATA, patch={"conferma": {
            "utente": utente, "canale": canale, "ts": ora(), "impronta": impronta_mostrata}}, nota="confermata")
        return self.leggi_copia(copia_id)

    def leggi_copia(self, copia_id: str) -> RisultatoAdattatore:
        j = self.job.leggi(copia_id, TIPO_COPIA)
        r = j["risultato"]
        tentativo = self.job.leggi(r["tentativo_corrente"], TIPO_TENTATIVO) if r.get("tentativo_corrente") else None
        az = None
        if r.get("requisiti_mancanti"):
            az = "Requisiti per la conferma: " + "; ".join(r["requisiti_mancanti"])
        elif j["stato"] == PREPARATA:
            az = "Verificare elaborati, importi e profilo e confermare nell'app."
        elif j["stato"] == OBSOLETA:
            az = "Pratica modificata: rigenerare elaborati, ricontrollare e preparare una nuova copia."
        modalita = self._modalita_tentativo(tentativo) if tentativo else None
        return risultato_da_job(j, Esito.SIMULAZIONE if modalita == "simulata" else self._esito_operazione(),
                                artefatti=r.get("artefatti", []), azione_richiesta=az,
                                impronta_conferma=j["input"]["impronta_conferma"], manifest=j["input"]["manifest"],
                                importi=j["input"]["importi"], profilo=j["input"]["profilo"],
                                revisione=j["input"]["revisione"], conferma=r.get("conferma"),
                                modalita=modalita, tentativo_corrente=r.get("tentativo_corrente"), tentativi=r.get("tentativi", []))

    @staticmethod
    def _modalita_tentativo(t: dict) -> str:
        return t["input"].get("modalita") or ("simulata" if t["input"].get("trasporto") == "TrasportoSimulato" else "manuale")

    # ---------------------------------------------------------------- trasmissione
    def trasmetti(self, copia_id: str, *, chiave_richiesta: str, canale: str = "gui", **kw) -> RisultatoAdattatore:
        if not chiave_richiesta:
            raise DatiNonValidi("chiave_richiesta obbligatoria per la trasmissione")
        copia = self.job.leggi(copia_id, TIPO_COPIA)
        tid = self.job.id_da_chiave(TIPO_TENTATIVO, chiave_richiesta)
        try:
            gia = self.job.leggi(tid, TIPO_TENTATIVO)
        except NonTrovato:
            gia = None
        if gia is not None:  # stessa richiesta ripetuta: nessuna nuova trasmissione
            if self._modalita_tentativo(gia) != ("manuale" if self.trasporto.reale else "simulata"):
                raise DatiNonValidi("la chiave appartiene a una diversa modalita' di invio")
            if gia["input"]["copia_id"] != copia_id:
                raise DatiNonValidi("chiave di richiesta gia' usata per un'altra copia")
            if gia["stato"] != CREATO:
                return self.leggi_tentativo(tid)
            # CREATO: il trasporto non e' mai stato chiamato (IN_TRASMISSIONE si scrive prima): si puo' proseguire
        if self.verifica_validita(copia_id).stato == OBSOLETA:
            raise ConfermaNonValida("la pratica e' cambiata dopo la conferma: trasmissione bloccata")
        copia = self.job.leggi(copia_id, TIPO_COPIA)
        ripresa = copia["stato"] == IN_INVIO and copia["risultato"].get("tentativo_corrente") == tid
        if copia["stato"] != CONFERMATA and not ripresa:
            blocco = copia["risultato"].get("tentativo_corrente")
            if copia["stato"] in (IN_INVIO, TRASMESSA):
                raise ReinvioNonAmmesso("esiste gia' un tentativo per questa copia: riconciliare, non reinviare",
                                        tentativo=blocco, stato_copia=copia["stato"])
            raise ConfermaNonValida(f"copia in stato '{copia['stato']}': serve la conferma nell'app")
        tel = next(a for a, m in zip(copia["risultato"]["artefatti"], copia["input"]["manifest"])
                   if m["ruolo"] == "telematico")
        contenuto = self.deposito.leggi(tel)
        if gia is None:
            self.job.crea(TIPO_TENTATIVO, copia["pratica_id"], {
                "copia_id": copia_id, "sha256": tel["sha256"], "nome": tel["nome"], "canale": canale,
                "impronta_conferma": copia["input"]["impronta_conferma"], "trasporto": type(self.trasporto).__name__,
                "modalita": "manuale" if self.trasporto.reale else "simulata",
                "precedenti": len(copia["risultato"].get("tentativi", []))}, stato=CREATO, chiave=chiave_richiesta)

        def nessun_altro_invio(elenca) -> str | None:
            for altra in elenca(TIPO_COPIA, copia["pratica_id"]):
                if altra["job_id"] != copia_id and altra["stato"] in (IN_INVIO, TRASMESSA):
                    vecchio_id = altra["risultato"].get("tentativo_corrente")
                    # Le prove fittizie non costituiscono un invio operativo, e viceversa.
                    if vecchio_id:
                        precedente = elenca(TIPO_TENTATIVO, copia["pratica_id"])
                        precedente = next((x for x in precedente if x["job_id"] == vecchio_id), None)
                        if precedente and self._modalita_tentativo(precedente) != ("manuale" if self.trasporto.reale else "simulata"):
                            continue
                    return (f"la copia {altra['job_id']} della stessa pratica e' gia' '{altra['stato']}': "
                            "nessun secondo invio della stessa dichiarazione")
            return None

        if not ripresa:
            try:  # prenotazione atomica: un solo tentativo attivo per copia e per pratica, anche fra processi
                self.job.transizione(copia_id, [CONFERMATA], IN_INVIO, patch={
                    "tentativo_corrente": tid, "tentativi": copia["risultato"].get("tentativi", []) + [tid]},
                    nota=f"tentativo {tid}", vincolo=nessun_altro_invio)
            except TransizioneNonAmmessa as e:
                self.job.transizione(tid, [CREATO], ANNULLATO, patch={"motivo": e.messaggio}, nota="non avviato")
                raise ReinvioNonAmmesso(e.messaggio, copia_id=copia_id) from None
        self.job.transizione(tid, [CREATO], IN_TRASMISSIONE, patch={"avviato": ora()},
                             nota="registrato prima della chiamata al trasporto")
        try:
            resp = self.trasporto.trasmetti(contenuto, tel["nome"], {"copia_id": copia_id, "tentativo_id": tid})
        except (TimeoutError, ConnectionError, OSError) as e:
            resp = RispostaInvio("incerto", motivo=f"{type(e).__name__}: {e}")
        self._applica_risposta(tid, resp, da=[IN_TRASMISSIONE])
        return self.leggi_tentativo(tid)

    def _applica_risposta(self, tid: str, resp: RispostaInvio, *, da, prova: dict | None = None) -> None:
        t = self.job.leggi(tid, TIPO_TENTATIVO)
        copia_id = t["input"]["copia_id"]
        patch: dict = {"ultima_risposta": {"tipo": resp.tipo, "motivo": resp.motivo, "ts": ora()}}
        if prova:
            patch["prova"] = prova
        if resp.originale:
            a = self.deposito.salva_bytes(resp.originale, f"risposta_{tid}", "risposta_trasporto")
            patch["artefatti"] = t["risultato"].get("artefatti", []) + [a]
        if resp.tipo == "accettato" and resp.protocollo:
            patch.update({"protocollo": resp.protocollo, "data_protocollo": resp.data or ora(), "azione_richiesta":
                          None})
            self._concludi(tid, da, TRASMESSO, patch, TRASMESSA, {"protocollo": resp.protocollo})
        elif resp.tipo == "rifiutato":
            patch.update({"motivazione": resp.motivo, "azione_richiesta": "Esito negativo definitivo: correggere e "
                          "preparare una nuova copia."})
            self._concludi(tid, da, RIFIUTATO, patch, RIFIUTATA, {"motivazione": resp.motivo}, resp.motivo)
        elif resp.tipo == "non_trasmesso":
            patch.update({"motivazione": resp.motivo, "azione_richiesta": "Invio non avvenuto (provato): e' possibile "
                          "un nuovo tentativo esplicito con una nuova chiave di richiesta."})
            self._concludi(tid, da, NON_TRASMESSO, patch, CONFERMATA, {"tentativo_corrente": None})
        elif resp.tipo == "non_disponibile":
            patch.update({"azione_richiesta": resp.motivo, "file_da_inviare": {"nome": t["input"]["nome"],
                                                                               "sha256": t["input"]["sha256"]}})
            self.job.transizione(tid, da, ATTESA_INVIO_MANUALE, patch=patch, nota="invio manuale tracciato")
        else:  # incerto / sconosciuto
            patch.update({"errore_rete": resp.motivo if resp.tipo == "incerto" else t["risultato"].get("errore_rete"),
                          "candidati": resp.candidati,
                          "azione_richiesta": "Esito incerto: NON reinviare. "
                                              + (resp.motivo + " " if resp.tipo == "sconosciuto" and resp.motivo else "")
                                              + "Riconciliare consultando protocolli ed "
                                              "esiti (Ricerca ricevute, Multifile R01/R02, file .esi)."})
            nuovo = ESITO_INCERTO if t["stato"] == IN_TRASMISSIONE else None
            self.job.transizione(tid, da, nuovo, patch=patch, nota=f"esito {resp.tipo}")

    def _concludi(self, tid, da, stato, patch, stato_copia, patch_copia, errore=None):
        t = self.job.leggi(tid, TIPO_TENTATIVO)
        self.job.transizioni([
            {"job_id": tid, "da": da, "a": stato, "patch": patch, "nota": stato, "errore": errore},
            {"job_id": t["input"]["copia_id"], "da": [IN_INVIO], "a": stato_copia,
             "patch": patch_copia, "nota": stato_copia}])

    def _recupera_finale(self, t):
        """Ripara archivi precedenti con tentativo finale e copia non allineata."""
        c = self.job.leggi(t["input"]["copia_id"], TIPO_COPIA)
        if c["stato"] != IN_INVIO or c["risultato"].get("tentativo_corrente") != t["job_id"]:
            return
        destinazioni = {TRASMESSO: (TRASMESSA, {"protocollo": t["risultato"].get("protocollo")}),
                        RIFIUTATO: (RIFIUTATA, {"motivazione": t["risultato"].get("motivazione")}),
                        NON_TRASMESSO: (CONFERMATA, {"tentativo_corrente": None})}
        if t["stato"] in destinazioni:
            stato, patch = destinazioni[t["stato"]]
            self.job.transizione(c["job_id"], [IN_INVIO], stato, patch=patch, nota="recupero esito finale")

    def leggi_tentativo(self, tentativo_id: str) -> RisultatoAdattatore:
        t = self.job.leggi(tentativo_id, TIPO_TENTATIVO)
        r = t["risultato"]
        modalita = self._modalita_tentativo(t)
        return risultato_da_job(t, Esito.SIMULAZIONE if modalita == "simulata" else self._esito_tentativo(t["stato"]),
                                artefatti=r.get("artefatti", []), modalita=modalita,
                                azione_richiesta=r.get("azione_richiesta"), copia_id=t["input"]["copia_id"],
                                protocollo=r.get("protocollo"), motivazione=r.get("motivazione"),
                                errore_rete=r.get("errore_rete"), prova=r.get("prova"),
                                candidati=r.get("candidati", []))

    # ---------------------------------------------------------------- riconciliazione
    def riconcilia(self, tentativo_id: str, *, evidenze: dict | None = None, **kw) -> RisultatoAdattatore:
        """Determina l'esito di un tentativo incerto senza mai reinviare.

        `evidenze` (facoltative, anche combinate): {"esi": testo del file .esi di Multifile},
        {"stato_invii": testo di ..._stato.json}, {"protocollo": "...", "verificato_su": "..."},
        {"non_trasmesso": True, "verificato_su": "..."}. Senza evidenze si interroga il trasporto."""
        t = self.job.leggi(tentativo_id, TIPO_TENTATIVO)
        if t["stato"] in FINALI_TENTATIVO:
            self._recupera_finale(t)
            return self.leggi_tentativo(tentativo_id)  # un esito finale non si riapre
        if self._modalita_tentativo(t) != ("manuale" if self.trasporto.reale else "simulata"):
            raise DatiNonValidi("modalita' diversa dal tentativo da riconciliare")
        if t["stato"] not in DA_RICONCILIARE:
            raise TransizioneNonAmmessa(f"tentativo in stato '{t['stato']}': niente da riconciliare")
        resp, prova = self._valuta_evidenze(t, evidenze or {})
        if resp is None:
            try:
                resp = self.trasporto.consulta({"sha256": t["input"]["sha256"], "nome": t["input"]["nome"],
                                                "tentativo_id": tentativo_id})
                prova = {"metodo": "consultazione del trasporto", "ts": ora()}
            except (TimeoutError, ConnectionError, OSError) as e:
                resp, prova = RispostaInvio("sconosciuto", motivo=f"consultazione fallita: {e}"), None
        self._applica_risposta(tentativo_id, resp, da=DA_RICONCILIARE, prova=prova)
        return self.leggi_tentativo(tentativo_id)

    @staticmethod
    def _valuta_evidenze(t: dict, ev: dict) -> tuple[RispostaInvio | None, dict | None]:
        nome = t["input"]["nome"]
        base = nome.rsplit(".", 1)[0]
        if ev.get("protocollo"):
            return (RispostaInvio("accettato", protocollo=str(ev["protocollo"])),
                    {"metodo": "protocollo indicato dall'utente", "verificato_su": ev.get("verificato_su"),
                     "ts": ora()})
        if ev.get("esi"):
            righe = [r for r in leggi_esi(ev["esi"]) if str(r.get("tipoOperazione", "")).upper() == "INVIO"
                     and str(r.get("fileName", "")).rsplit(".", 1)[0] == base]
            if righe:
                r = righe[-1]
                prova = {"metodo": "file .esi di Entratel-Multifile", "riga": r, "ts": ora()}
                if r.get("resultCode") == "00" and r.get("protocollo"):
                    return RispostaInvio("accettato", protocollo=r["protocollo"]), prova
                if r.get("resultCode") and r.get("resultCode") != "00":
                    # Un esito negativo di Multifile NON prova che il file non sia stato ricevuto (puo' essere stato ricevuto e
                    # scartato): resta incerto, niente nuovo tentativo senza una verifica esplicita dell'utente.
                    return (RispostaInvio("sconosciuto", motivo=(
                        f"Multifile ha registrato un esito negativo per l'INVIO (resultCode {r['resultCode']}), che non prova "
                        "che il file non sia stato ricevuto: verificare nelle ricevute e nello stato degli invii, poi riconciliare "
                        "con {'protocollo': ...} oppure, solo dopo la verifica, con {'non_trasmesso': True, 'verificato_su': '...'}")),
                            prova)
        if ev.get("stato_invii"):
            st = leggi_stato_invii(ev["stato_invii"])
            cand = [{k: x.get(k) for k in ("protocollo", "tipoFornitura", "data", "stato", "nomeFile",
                                           "codScartoFornitura")} for x in st["ricevute"]]
            return (RispostaInvio("sconosciuto", motivo="scegliere il protocollo tra i candidati e riconciliare con "
                                  "{'protocollo': ...}: l'associazione automatica per data non e' sicura",
                                  candidati=cand), {"metodo": "stato invii Multifile", "result": st["result"]})
        if ev.get("non_trasmesso") is True:
            if not ev.get("verificato_su"):
                raise DatiNonValidi("indicare dove e' stata verificata l'assenza dell'invio (verificato_su)")
            return (RispostaInvio("non_trasmesso", motivo="assenza dell'invio verificata dall'utente"),
                    {"metodo": "dichiarazione dell'utente", "verificato_su": ev["verificato_su"], "ts": ora()})
        return None, None

    # ---------------------------------------------------------------- ricevute ed esiti successivi
    def associa(self, *, protocollo: str, tipo: str, contenuto: bytes, nome: str, esito: str | None = None,
                data_documento: str | None = None, pratica_id: str | None = None, dettagli: dict | None = None,
                **kw) -> RisultatoAdattatore:
        """Registra un documento ricevuto (originale conservato) e lo associa a protocollo/tentativo/pratica."""
        if tipo not in TIPI_RICEVUTA:
            raise DatiNonValidi("tipo di documento non ammesso", ammessi=list(TIPI_RICEVUTA))
        ammessi = TIPI_RICEVUTA[tipo]["esiti"]
        if esito is not None and esito not in ammessi:
            raise DatiNonValidi(f"esito non ammesso per {tipo}", ammessi=list(ammessi))
        if ammessi and esito is None:
            raise DatiNonValidi(f"per {tipo} indicare l'esito riportato nel documento", ammessi=list(ammessi))
        modalita = "manuale" if self.trasporto.reale else "simulata"
        tent = [t for t in self.job.elenca(TIPO_TENTATIVO) if t["risultato"].get("protocollo") == protocollo
                and self._modalita_tentativo(t) == modalita and (pratica_id is None or t["pratica_id"] == pratica_id)]
        pid = tent[0]["pratica_id"] if tent else pratica_id
        h = sha256_bytes(contenuto)
        inp = {"protocollo": protocollo, "tipo": tipo, "esito": esito, "sha256": h, "nome": nome,
               "data_documento": data_documento, "dettagli": dettagli or {}, "fonte_tipi": FONTE_RICEVUTE, "modalita": modalita}
        j, nuovo = self.job.crea(TIPO_RICEVUTA, pid, inp, stato="acquisita", chiave=f"{modalita}|{pid}|{protocollo}|{tipo}|{h}",
                                 risultato={"tentativo_id": tent[0]["job_id"] if tent else None})
        if nuovo:
            a = self.deposito.salva_bytes(contenuto, nome, f"ricevuta_{tipo}")
            self.job.annota(j["job_id"], {"artefatti": [a], "associazione": "tentativo" if tent else
                                          "solo protocollo (nessun tentativo con questo protocollo)"})
        j = self.job.leggi(j["job_id"])
        return risultato_da_job(j, self._esito_operazione(), artefatti=j["risultato"].get("artefatti", []),
                                protocollo=protocollo, tipo_documento=tipo, esito_documento=esito,
                                ripetuta=not nuovo)

    def stato_esiti(self, protocollo: str, pratica_id: str | None = None) -> dict:
        """Dimensioni separate degli esiti successivi (specifica §10). Non lineare: ogni dimensione e' indipendente."""
        modalita = "manuale" if self.trasporto.reale else "simulata"
        docs = [d for d in self.job.elenca(TIPO_RICEVUTA, pratica_id) if d["input"]["protocollo"] == protocollo
                and d["input"].get("modalita", modalita) == modalita]
        tent = [t for t in self.job.elenca(TIPO_TENTATIVO, pratica_id) if t["risultato"].get("protocollo") == protocollo
                and self._modalita_tentativo(t) == modalita]
        asp = {}
        if tent:
            asp = self.job.leggi(tent[0]["input"]["copia_id"], TIPO_COPIA)["input"].get("aspettative", {})

        def per_tipo(t):
            return [d for d in docs if d["input"]["tipo"] == t]

        def esito_di(t, atteso):
            ds = per_tipo(t)
            es = sorted({d["input"]["esito"] for d in ds})
            if len(es) > 1:
                return "contraddittorio: " + ", ".join(es)
            return es[0] if es else atteso

        def atteso(flag, si, no="non_applicabile"):
            return si if flag is True else no if flag is False else "da_determinare"

        return {
            "protocollo": protocollo, "fonte": FONTE_RICEVUTE,
            "trasmissione": "trasmessa_con_riscontro" if tent or per_tipo("trasmissione") else "non_riscontrata",
            "registrazione": esito_di("registrazione", "attesa"),
            "pagamento": esito_di("pagamento", atteso(asp.get("addebito"), "atteso")),
            "volture": esito_di("volture", atteso(asp.get("voltura_automatica"), "attese")),
            "copia_semplice": "acquisita" if per_tipo("copia_semplice") else "attesa",
            "regolarizzazione": "richiesta" if per_tipo("richiesta_regolarizzazione") else "nessuna",
            "attestazione": "acquisita" if per_tipo("attestazione") else atteso(asp.get("attestazione_richiesta"),
                                                                                  "attesa"),
            "da_classificare": len(per_tipo("da_classificare")),
            "documenti": [{"job_id": d["job_id"], "tipo": d["input"]["tipo"], "esito": d["input"]["esito"],
                           "nome": d["input"]["nome"], "sha256": d["input"]["sha256"]} for d in docs],
        }


def stati_pratica(archivio: Archivio, pratica_id: str, impronta_dichiarativa_corrente: str | None = None) -> dict:
    """Riepilogo per pratica delle dimensioni gestite dai collegamenti: controllo ufficiale e trasmissione.
    Un controllo eseguito su dati precedenti resta registrato ma per la versione corrente e' 'obsoleto'."""
    reg = RegistroJob(archivio)
    ctl = [c for c in reg.elenca("controllo_ufficiale", pratica_id) if c["stato"] in ("completato",
                                                                                      "errore_esecuzione")]
    controllo = {"stato": "non_eseguito"}
    if ctl:
        c = ctl[-1]
        obs = (impronta_dichiarativa_corrente is not None and c["input"].get("impronta_dichiarativa") not in
               (None, impronta_dichiarativa_corrente))
        controllo = {"stato": c["risultato"].get("stato_controllo"), "esito": c["risultato"].get("esito"),
                     "job_id": c["job_id"], "data": c["aggiornato"], "obsoleto": obs}
    copie = reg.elenca(TIPO_COPIA, pratica_id)
    trasmissione = {"stato": "non_preparata"}
    if copie:
        cp = copie[-1]
        trasmissione = {"stato": cp["stato"], "copia_id": cp["job_id"],
                        "tentativo": cp["risultato"].get("tentativo_corrente")}
        tid = cp["risultato"].get("tentativo_corrente")
        if tid:
            t = reg.leggi(tid)
            trasmissione["tentativo_stato"] = t["stato"]
            trasmissione["protocollo"] = t["risultato"].get("protocollo")
    return {"pratica_id": pratica_id, "controllo_ufficiale": controllo, "trasmissione": trasmissione}
