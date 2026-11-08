"""«Prossime azioni» della pagina iniziale: per ogni pratica le cinque tappe (dati, file, controllo, invio, ricevute), la
prossima cosa da fare con il punto dell'interfaccia in cui farla, e il termine di presentazione.

Usa solo gli stati gia' calcolati dal programma (verifica, elaborati, esportazione, invio, ricevute): nessuna regola nuova.
Il termine e' di dodici mesi dalla decorrenza indicata nel frontespizio (``presentatore.data_decorrenza``, se presente e non
anteriore al decesso) oppure, in mancanza, dalla data del decesso, come la pagina iniziale.

Lo stato si calcola per TUTTE le pratiche (operazione leggera) e solo dopo si scelgono le piu' urgenti da mostrare: una
pratica ferma da tempo ma vicina al termine non sparisce. Il motivo che impedisce di generare il file (operazione piu'
costosa: una generazione di prova senza salvare nulla) si calcola solo per le pratiche mostrate.
"""
from __future__ import annotations

import re
from datetime import date

TAPPE = ("dati", "file", "controllo", "invio", "ricevute")
NOMI = {"dati": "Dati", "file": "File", "controllo": "Controllo", "invio": "Invio", "ricevute": "Ricevute"}


def _data(v) -> date | None:
    try:
        return date.fromisoformat(v) if isinstance(v, str) and v else None
    except ValueError:
        return None


def _termine(decesso: str | None, oggi: date, decorrenza: str | None = None) -> dict | None:
    d, dec = _data(decesso), _data(decorrenza)
    base = "decesso"
    if dec is not None and (d is None or dec >= d):     # una decorrenza anteriore al decesso non vale (frontespizio.py)
        d, base = dec, "decorrenza"
    if d is None:
        return None
    try:
        t = d.replace(year=d.year + 1)
    except ValueError:              # 29 febbraio
        t = d.replace(year=d.year + 1, day=28)
    return {"data": t.isoformat(), "giorni": (t - oggi).days, "base": base, "dal": d.isoformat()}


def _decorrenza(dati: dict) -> str | None:
    from .telematico import supplemento as SUP
    v = SUP.presentatore_sup(dati).get("data_decorrenza")
    return v if isinstance(v, str) else None


def _dove(dati: dict, percorso: str | None) -> dict:
    """Punto dell'interfaccia per un percorso di errore dell'esportazione (``quadro[EG].X`` oppure un campo dei dati)."""
    if not percorso:
        return {"sel": "FILE"}
    m = re.match(r"^quadro\[([A-Z]{2})\]", percorso)
    if m:
        return {"sel": m.group(1)}
    if percorso.startswith("opzioni.fornitore"):
        return {"sel": "FILE"}
    from . import quadri as Q
    try:
        return {"sel": Q.quadro_per_percorso(dati, percorso) or "AN", "percorso": percorso}
    except Exception:
        return {"sel": "AN", "percorso": percorso}


def _motivi_export(ris: dict) -> list[dict]:
    """Motivi bloccanti di un risultato di esportazione (errori, quadri mancanti, parti non supportate), nell'ordine."""
    out = [{"messaggio": e.get("messaggio"), "percorso": e.get("percorso")} for e in ris.get("errori") or []]
    out += [{"messaggio": e.get("messaggio"), "percorso": e.get("percorso")} for e in ris.get("quadri_mancanti") or []]
    out += [{"messaggio": "parte non supportata dal programma: " + str(x), "percorso": None} for x in ris.get("non_supportato") or []]
    return [m for m in out if m["messaggio"]]


def motivi_file(sv, pid: str, dati: dict, export: dict) -> list[dict]:
    """Perche' il file telematico completo non si puo' generare ora; lista vuota se si puo'.

    Usa l'ultima esportazione se e' della versione corrente dei dati, altrimenti una generazione di prova identica a
    ``esporta`` (stessi allegati e fornitore) che non salva file ne' job."""
    forn = (dati.get("opzioni") or {}).get("fornitore") or {}
    cf = str(forn.get("cf") or "").strip().upper()
    if not cf:
        return [{"messaggio": "manca il codice fiscale del fornitore (intermediario o dichiarante): indicalo nel profilo",
                 "percorso": "opzioni.fornitore.cf"}]
    if export.get("stato") == "aggiornato":
        from .elaborati import TIPO_EXPORT
        j = sv._job_ultimo(TIPO_EXPORT, pid)
        if j and j["input"].get("scopo", "completo") == "completo":
            return _motivi_export(j["risultato"])
    from .telematico.esporta import ContestoExport, esporta_xml
    try:
        es = esporta_xml(dati, ContestoExport(cf_fornitore=cf, tipo_fornitore=str(forn.get("tipo") or "1"), scopo="completo",
                                              allegati=sv._allegati_export(pid, dati),
                                              impegno_codice=forn.get("impegno_codice"), data_impegno=forn.get("data_impegno")))
    except Exception as e:                  # es. allegato alterato: e' esso stesso il motivo
        return [{"messaggio": str(e), "percorso": None}]
    if es.xml is not None and es.completo:
        return []
    return _motivi_export({"errori": [e.asdict() for e in es.errori], "quadri_mancanti": [e.asdict() for e in es.quadri_mancanti],
                           "non_supportato": list(es.non_supportato)})


def _azione_file(sv, pid: str, dati: dict, ex: dict) -> dict:
    try:
        motivi = motivi_file(sv, pid, dati, ex)
    except Exception as e:
        motivi = [{"messaggio": f"stato del file non calcolabile: {e}", "percorso": None}]
    if motivi:
        m = motivi[0]
        return {"testo": "Il file non si può ancora generare: " + m["messaggio"], "altri": len(motivi) - 1,
                "livello": "problema", "dove": _dove(dati, m["percorso"])}
    return {"testo": "Dati cambiati: rigenera il file telematico" if ex.get("stato") == "obsoleto" else "Genera il file telematico",
            "dove": {"sel": "FILE"}}


def _azione_invio(tr: dict) -> dict:
    st = tr.get("stato")
    if st in ("non_preparata", None):
        testo, livello = "Prepara la copia e inviala con Desktop Telematico", None
    elif tr.get("modalita") == "simulata":
        testo, livello = "Solo prova simulata: prepara la copia reale e inviala con Desktop Telematico", None
    elif st == "preparata":
        testo, livello = "Copia preparata: conferma e invia", None
    elif st == "confermata":
        testo, livello = "Copia confermata: inviala con Desktop Telematico e registra l'esito", None
    elif st == "in_invio":
        testo, livello = "Invio in corso o in attesa: registra l'esito dell'invio", None
    elif st == "rifiutata":
        testo, livello = "Invio rifiutato: correggi i dati e prepara di nuovo la copia", "problema"
    elif st == "obsoleta":
        testo, livello = "Copia superata (dati cambiati o copia sostituita): prepara di nuovo la copia", "problema"
    else:
        testo, livello = "Controlla lo stato dell'invio", None
    a = {"testo": testo, "dove": {"sel": "FILE"}}
    if livello:
        a["livello"] = livello
    return a


def _azione_ricevute(ric: dict) -> dict:
    reg = str((ric or {}).get("registrazione") or "attesa")
    if reg.startswith("scartat"):
        return {"testo": "Dichiarazione scartata: leggi i motivi nella ricevuta, correggi e prepara di nuovo", "livello": "problema",
                "dove": {"sel": "FILE"}}
    if reg.startswith("contraddittorio"):
        return {"testo": "Ricevute di registrazione contraddittorie: controlla i documenti registrati", "livello": "problema",
                "dove": {"sel": "FILE"}}
    return {"testo": "Ricevuta di registrazione attesa", "dove": {"sel": "FILE"}}


def stato_pratica(sv, p: dict, oggi: date) -> dict:
    pid = p["id"]
    out = {"pratica_id": pid, "titolo": p["titolo"], "aggiornata": p.get("aggiornata"), "termine": _termine(p.get("data_decesso"), oggi),
           "tappe": {}, "azione": None, "errore": None}
    try:
        st = sv.stato_elaborati(pid)
        q = sv.quadri(pid)
        dati = sv.leggi(pid)["dati"]
    except Exception as e:                 # il cruscotto non deve mai bloccare la pagina iniziale
        out["errore"] = str(e)
        out["azione"] = {"testo": "Apri la pratica per verificarne lo stato", "dove": {"sel": "AN"}}
        return out
    try:
        out["termine"] = _termine(p.get("data_decesso"), oggi, _decorrenza(dati))
    except Exception:
        pass
    ex, ct, tr = st["export"], st["controllo_ufficiale"], st["trasmissione"]
    rilievi = q.get("rilievi") or []
    fatto = {
        "dati": not rilievi,
        "file": ex.get("stato") == "aggiornato" and bool(ex.get("completo")),
        "controllo": ct.get("stato") == "positivo",
        "invio": tr.get("stato") in ("trasmessa", "trasmesso") and tr.get("modalita") != "simulata",
        "ricevute": False,
    }
    ric = {}
    if fatto["invio"]:
        try:
            copia = sv.invio_stato(pid)["copie"][0]
            tid = (copia.get("dettaglio") or {}).get("tentativo_corrente")
            ric = sv.ricevute_stato(pid, tid) if tid else {}
            fatto["ricevute"] = str(ric.get("registrazione", "")).startswith(("ricevut", "positiv", "registrat"))
            out["ricevute"] = {k: ric.get(k) for k in ("registrazione", "pagamento", "volture")}
        except Exception:
            pass
    corrente = next((t for t in TAPPE if not fatto[t]), None)
    out["tappe"] = {t: ("fatto" if fatto[t] else "corrente" if t == corrente else "da_fare") for t in TAPPE}
    out["completata"] = corrente is None
    if corrente == "dati":
        r = rilievi[0]
        altri = len(rilievi) - 1
        out["azione"] = {"testo": r.get("messaggio", "Completa i dati"), "altri": altri, "codice": r.get("codice"),
                         "dove": {"sel": r.get("quadro") or "AN", "percorso": r.get("percorso")}}
    elif corrente == "file":
        # il motivo bloccante si calcola dopo, solo per le pratiche mostrate (cruscotto)
        out["azione"] = {"testo": "Genera il file telematico", "dove": {"sel": "FILE"}}
        out["_file"] = (dati, ex)
    elif corrente == "controllo":
        testo = ("Carica l'esito del controllo eseguito a mano" if ct.get("stato_job") == "attesa_diagnostico"
                 else "Controllo ufficiale con rilievi: correggi e ripeti" if ct.get("stato") == "negativo"
                 else "Esegui il controllo ufficiale")
        out["azione"] = {"testo": testo, "dove": {"sel": "FILE"}}
        if ct.get("stato") == "negativo":
            out["azione"]["livello"] = "problema"
    elif corrente == "invio":
        out["azione"] = _azione_invio(tr)
    elif corrente == "ricevute":
        out["azione"] = _azione_ricevute(ric)
    else:
        out["azione"] = {"testo": "Pratica completata", "dove": {"sel": "FILE"}}
    if (out["azione"] or {}).get("livello") == "problema":
        out["tappe"][corrente] = "problema"
    return out


def _completa_file(sv, v: dict) -> None:
    dati, ex = v.pop("_file", (None, None))
    if dati is not None:
        v["azione"] = _azione_file(sv, v["pratica_id"], dati, ex)
        if v["azione"].get("livello") == "problema":
            v["tappe"]["file"] = "problema"


def cruscotto(sv, limite: int = 12, oggi: date | None = None, tutte: bool = False) -> dict:
    """Stato delle pratiche, le piu' urgenti prima. ``tutte``: la pagina iniziale mostra ogni pratica in un solo elenco; il motivo
    preciso per cui il file non si genera (calcolo piu' costoso) resta solo per le prime ``limite``."""
    oggi = oggi or date.today()
    voci = [stato_pratica(sv, p, oggi) for p in sv.elenca()]
    # prima le pratiche da lavorare con il termine piu' vicino; in fondo quelle complete. La scelta avviene DOPO l'ordinamento
    voci.sort(key=lambda v: (bool(v.get("completata")), (v["termine"] or {}).get("giorni", 10**6)))
    mostrate, nascoste = voci[:limite], voci[limite:]
    for v in mostrate:
        _completa_file(sv, v)
    for v in nascoste:
        v.pop("_file", None)
    if tutte:
        mostrate, nascoste = voci, []
    return {"oggi": oggi.isoformat(), "tappe": [{"id": t, "nome": NOMI[t]} for t in TAPPE], "pratiche": mostrate,
            "totale": len(voci), "altre": len(nascoste),
            "altre_da_lavorare": sum(1 for v in nascoste if not v.get("completata")),
            "nota": "Termine: dodici mesi dalla decorrenza indicata nel frontespizio o, se manca, dalla data del decesso."}
