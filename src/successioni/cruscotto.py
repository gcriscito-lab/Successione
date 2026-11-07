"""«Prossime azioni» della pagina iniziale: per ogni pratica le cinque tappe (dati, file, controllo, invio, ricevute), la
prossima cosa da fare con il punto dell'interfaccia in cui farla, e il termine ordinario di presentazione.

Usa solo gli stati gia' calcolati dal programma (verifica, elaborati, invio, ricevute): nessuna regola nuova. Il termine e'
quello ordinario di dodici mesi dal decesso (come la pagina iniziale; le istruzioni prevedono decorrenze diverse).
"""
from __future__ import annotations

from datetime import date

TAPPE = ("dati", "file", "controllo", "invio", "ricevute")
NOMI = {"dati": "Dati", "file": "File", "controllo": "Controllo", "invio": "Invio", "ricevute": "Ricevute"}


def _termine(decesso: str | None, oggi: date) -> dict | None:
    try:
        d = date.fromisoformat(decesso) if isinstance(decesso, str) else None
    except ValueError:
        d = None
    if d is None:
        return None
    try:
        t = d.replace(year=d.year + 1)
    except ValueError:              # 29 febbraio
        t = d.replace(year=d.year + 1, day=28)
    return {"data": t.isoformat(), "giorni": (t - oggi).days}


def stato_pratica(sv, p: dict, oggi: date) -> dict:
    pid = p["id"]
    out = {"pratica_id": pid, "titolo": p["titolo"], "aggiornata": p.get("aggiornata"), "termine": _termine(p.get("data_decesso"), oggi),
           "tappe": {}, "azione": None, "errore": None}
    try:
        st = sv.stato_elaborati(pid)
        q = sv.quadri(pid)
    except Exception as e:                 # il cruscotto non deve mai bloccare la pagina iniziale
        out["errore"] = str(e)
        out["azione"] = {"testo": "Apri la pratica per verificarne lo stato", "dove": {"sel": "AN"}}
        return out
    ex, ct, tr = st["export"], st["controllo_ufficiale"], st["trasmissione"]
    rilievi = q.get("rilievi") or []
    fatto = {
        "dati": not rilievi,
        "file": ex.get("stato") == "aggiornato" and bool(ex.get("completo")),
        "controllo": ct.get("stato") == "positivo",
        "invio": tr.get("stato") in ("trasmessa", "trasmesso") and tr.get("modalita") != "simulata",
        "ricevute": False,
    }
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
        out["azione"] = {"testo": "Genera il file telematico" if ex.get("stato") != "obsoleto" else "Dati cambiati: rigenera il file",
                         "dove": {"sel": "FILE"}}
    elif corrente == "controllo":
        testo = ("Carica l'esito del controllo eseguito a mano" if ct.get("stato_job") == "attesa_diagnostico"
                 else "Controllo ufficiale con rilievi: correggi e ripeti" if ct.get("stato") == "negativo"
                 else "Esegui il controllo ufficiale")
        out["azione"] = {"testo": testo, "dove": {"sel": "FILE"}}
    elif corrente == "invio":
        out["azione"] = {"testo": "Prepara la copia e inviala con Desktop Telematico" if tr.get("stato") in ("non_preparata", None)
                         else "Copia preparata: conferma e invia", "dove": {"sel": "FILE"}}
    elif corrente == "ricevute":
        out["azione"] = {"testo": "Ricevuta di registrazione attesa", "dove": {"sel": "FILE"}}
    else:
        out["azione"] = {"testo": "Pratica completata", "dove": {"sel": "FILE"}}
    return out


def cruscotto(sv, limite: int = 12, oggi: date | None = None) -> dict:
    oggi = oggi or date.today()
    pratiche = sv.elenca()[:limite]
    voci = [stato_pratica(sv, p, oggi) for p in pratiche]
    # prima le pratiche da lavorare con il termine piu' vicino; in fondo quelle complete
    voci.sort(key=lambda v: (bool(v.get("completata")), (v["termine"] or {}).get("giorni", 10**6)))
    return {"oggi": oggi.isoformat(), "tappe": [{"id": t, "nome": NOMI[t]} for t in TAPPE], "pratiche": voci,
            "nota": "Termine ordinario: dodici mesi dal decesso. Le istruzioni prevedono decorrenze diverse in alcuni casi."}
