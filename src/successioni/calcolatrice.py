"""Calcolatrice rapida delle imposte di successione: STIMA da pochi dati, senza pratica in archivio.

Nessuna regola fiscale nuova. La funzione costruisce in memoria una pratica SINTETICA (nomi e codici fiscali inventati,
generati da ``telematico.identificativi.genera_cf_sintetico``; IBAN inventato con cifre di controllo calcolate) e la passa ai
motori gia' verificati:

- ``telematico.esporta.esporta_xml`` in scopo ``bozza_tecnica``: quadro EF (imposte ipotecaria, catastale, tassa ipotecaria,
  bollo, prima casa) e sezione V-bis (imposta di successione), con le regole e le fonti di ``telematico.quadri_efgh``;
- ``telematico.calcolo.calcola_da_xml`` sul file prodotto: passaggi della guida per ogni erede (franchigia, aliquota);
- ``prospetto_cliente.leggi`` per leggere dal file gli importi dichiarati;
- ``valore_catastale.calcola`` per proporre il valore catastale da rendita e categoria;
- ``telematico.devoluzione_legge.quote_di_legge`` per proporre le quote di legge.

Nulla viene salvato: niente archivio, niente file su disco (gli allegati del quadro EG non servono alla bozza tecnica). Ogni
caso che i motori non coprono resta «non stimabile» con il motivo restituito dal motore stesso.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from fractions import Fraction

from . import valori as V
from .errori import DatiNonValidi as _DatiNonValidi

AVVERTENZA = "Stima: non sostituisce la dichiarazione né il controllo ufficiale."
MAX_EREDI = 20
MAX_BENI = 30
_NOMI = [("Anna", "F"), ("Luca", "M"), ("Marta", "F"), ("Paolo", "M"), ("Sara", "F"), ("Ugo", "M"), ("Elena", "F"),
         ("Marco", "M"), ("Giulia", "F"), ("Piero", "M")]
_ASCENDENTI = {"03", "5A", "5B", "7A", "7B", "9A", "9B"}
#: tipi cespite del quadro ER offerti per gli «altri beni» (codici XSD TipoCespite_Type)
TIPI_ALTRI_BENI = {"CR": "Conti correnti, depositi e crediti", "AB": "Titoli e altri beni", "DN": "Denaro, gioielli e mobilia"}
_IBAN_BBAN = "A0123456789000000001234"   # ABI/CAB/conto inventati: solo per completare la bozza tecnica


class DatiNonValidi(_DatiNonValidi):
    """Dati della calcolatrice non validi (HTTP 422 nell'interfaccia, errore dello strumento MCP)."""


def _importo(v, cosa: str) -> Decimal | None:
    if v in (None, ""):
        return None
    s = str(v).strip().replace(" ", "").replace("€", "")
    # importi all'italiana, come nella maschera dell'interfaccia (app.js, leggi «importo»): 1.234,50 / 150.000 / 12,5
    if re.fullmatch(r"\d{1,3}(\.\d{3})+,\d+", s):
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    elif re.fullmatch(r"\d+,\d+", s):
        s = s.replace(",", ".")
    if s == "":
        return None
    try:
        d = V.parse_importo(s)
    except (V.ValoreNonValido, InvalidOperation, ValueError):
        raise DatiNonValidi(f"{cosa}: importo non valido ({v!r})")
    if d < 0:
        raise DatiNonValidi(f"{cosa}: importo negativo")
    return d


def _quota(v, cosa: str) -> Fraction | None:
    if v in (None, ""):
        return None
    if str(v).strip() == "1":
        return Fraction(1)
    try:
        q = V.parse_quota(v)
    except (V.ValoreNonValido, ValueError):
        raise DatiNonValidi(f"{cosa}: quota non valida ({v!r}); scrivere ad esempio 1/2")
    if not 0 < q <= 1:
        raise DatiNonValidi(f"{cosa}: la quota deve essere maggiore di zero e al massimo 1")
    return q


def _euro(d) -> str:
    """Importo per l'interfaccia, all'italiana (1.234,56)."""
    if d is None:
        return ""
    d = Decimal(str(d))
    intero = d == d.to_integral_value()
    s = f"{d:,.0f}" if intero else f"{d:,.2f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".") + " €"


def _frazione_esatta(s: str) -> Decimal:
    if "/" in s:
        n, d = s.split("/")
        return (Decimal(n) / Decimal(d)).quantize(Decimal("0.01"))
    return Decimal(s)


def _gradi() -> dict[str, str]:
    from .codici import strutturati
    return {o["valore"]: o["etichetta"] for o in strutturati()["persone.grado_parentela"]["opzioni"]}


def _cf(cognome: str, nome: str, sesso: str, nascita: date) -> str:
    from .telematico.identificativi import genera_cf_sintetico
    return genera_cf_sintetico(cognome, nome, sesso, nascita, "H501")


def _iban() -> str:
    from .telematico.identificativi import cifre_controllo_iban
    return "IT" + cifre_controllo_iban("IT", _IBAN_BBAN) + _IBAN_BBAN


def leggi_richiesta(r: dict) -> dict:
    """Controlla e normalizza i dati della calcolatrice. Solleva ``DatiNonValidi`` con un messaggio leggibile."""
    if not isinstance(r, dict):
        raise DatiNonValidi("richiesta non valida")
    try:
        dd = date.fromisoformat(str(r.get("data_decesso") or ""))
    except ValueError:
        raise DatiNonValidi("indicare la data del decesso (AAAA-MM-GG)")
    if dd > date.today():
        raise DatiNonValidi("la data del decesso è nel futuro")
    gradi = _gradi()
    eredi = []
    for i, e in enumerate(r.get("eredi") or [], 1):
        g = str((e or {}).get("grado") or "").strip().upper()
        g = {"5A": "5A", "5B": "5B"}.get(g, g)
        if g not in gradi:
            raise DatiNonValidi(f"erede {i}: scegliere il grado di parentela dal menu")
        eredi.append({"grado": g, "quota": _quota(e.get("quota"), f"erede {i}"), "disabile": e.get("disabile") is True,
                      "nome": str(e.get("nome") or "").strip()[:60]})
    if not eredi:
        raise DatiNonValidi("aggiungere almeno un erede")
    if len(eredi) > MAX_EREDI:
        raise DatiNonValidi(f"al massimo {MAX_EREDI} eredi")
    immobili = []
    for i, b in enumerate(r.get("immobili") or [], 1):
        b = b or {}
        tipo = "terreno" if b.get("tipo") == "terreno" else "fabbricato"
        immobili.append({"tipo": tipo, "valore": _importo(b.get("valore"), f"immobile {i}"),
                         "rendita": _importo(b.get("rendita"), f"immobile {i}, rendita"),
                         "reddito_dominicale": _importo(b.get("reddito_dominicale"), f"immobile {i}, reddito dominicale"),
                         "categoria": str(b.get("categoria") or "A/2").strip().upper()[:5],
                         "prima_casa": b.get("prima_casa") is True and tipo == "fabbricato",
                         "quota_defunto": _quota(b.get("quota_defunto"), f"immobile {i}, quota del defunto") or Fraction(1)})
    altri = []
    for i, b in enumerate(r.get("altri_beni") or [], 1):
        b = b or {}
        tc = str(b.get("tipo") or "CR").upper()
        if tc not in TIPI_ALTRI_BENI:
            raise DatiNonValidi(f"altro bene {i}: tipo non previsto")
        v = _importo(b.get("valore"), f"altro bene {i}")
        if v:
            altri.append({"tipo": tc, "valore": v, "descrizione": str(b.get("descrizione") or "").strip()[:80]})
    passivita = []
    for i, p in enumerate(r.get("passivita") or [], 1):
        p = p or {}
        v = _importo(p.get("importo"), f"passività {i}")
        if v:
            passivita.append({"tipo": str(p.get("tipo") or "12"), "importo": v,
                              "descrizione": str(p.get("descrizione") or "").strip()[:80]})
    if len(immobili) + len(altri) > MAX_BENI:
        raise DatiNonValidi(f"al massimo {MAX_BENI} beni")
    try:
        circ = int(r.get("circoscrizioni") or 1)
    except (TypeError, ValueError):
        raise DatiNonValidi("numero di circoscrizioni non valido")
    if not 1 <= circ <= 50:
        raise DatiNonValidi("numero di circoscrizioni fra 1 e 50")
    return {"data_decesso": dd, "eredi": eredi, "immobili": immobili, "altri_beni": altri, "passivita": passivita,
            "circoscrizioni": circ}


def quote_legge(eredi: list[dict]) -> dict[int, Fraction] | None:
    """Quote di legge per indice dell'erede (motore ``devoluzione_legge``), ``None`` se la configurazione non e' coperta."""
    from .telematico.devoluzione_legge import quote_di_legge
    q = quote_di_legge({f"e{i:02d}": e["grado"] for i, e in enumerate(eredi)}, {f"e{i:02d}": "1" for i in range(len(eredi))})
    return None if q is None else {int(k[1:]): v for k, v in q.items()}


def _pratica(c: dict, quote: list[Fraction]) -> dict:
    """Pratica sintetica in memoria (mai salvata)."""
    dd = c["data_decesso"]
    defunto = {"id": "p_defunto1", "_origine": {}, "cognome": "Stima", "nome": "Defunto", "ruolo": "defunto",
               "codice_fiscale": _cf("Stima", "Defunto", "M", date(1940, 1, 1)), "data_nascita": "1940-01-01",
               "luogo_nascita": "Roma", "data_decesso": dd.isoformat()}
    persone, op_persone = [defunto], {"p_defunto1": {"sesso": "M", "provincia_nascita": "RM", "comune_decesso": "Roma",
                                                      "provincia_decesso": "RM"}}
    pids = []
    for i, e in enumerate(c["eredi"]):
        nome, sesso = _NOMI[i % len(_NOMI)]
        anno = (1915 if e["grado"] in _ASCENDENTI else 1965) + i // len(_NOMI)
        nascita = date(anno, 1, 1) + timedelta(days=i)
        pid = f"p_erede{i:03d}"
        pids.append(pid)
        persone.append({"id": pid, "_origine": {}, "cognome": "Erede", "nome": nome, "ruolo": "erede",
                        "codice_fiscale": _cf("Erede", nome, sesso, nascita), "data_nascita": nascita.isoformat(),
                        "luogo_nascita": "Roma", "relazione_con_defunto": e["grado"]})
        op_persone[pid] = {"sesso": sesso, "provincia_nascita": "RM", "grado_parentela": e["grado"],
                           **({"portatore_handicap": True, "certificatore_disabilita": "VERBALE STIMA"} if e["disabile"] else {})}
    beni, op_beni, devs, op_devs = [], {}, [], {}
    prima_casa = False

    def devolvi(bid: str, agev_primo: str | None = None):
        for j, (pid, q) in enumerate(zip(pids, quote)):
            did = f"d_{bid[2:]}_{j:03d}"
            devs.append({"id": did, "_origine": {}, "bene_id": bid, "persona_id": pid,
                         "quota": {"num": q.numerator, "den": q.denominator}, "diritto": "1"})
            if agev_primo and j == 0:
                op_devs[did] = {"agevolazioni": agev_primo}

    for k, im in enumerate(c["immobili"]):
        bid = f"b_imm{k:03d}"
        qd = im["quota_defunto"]
        b = {"id": bid, "_origine": {}, "tipo": im["tipo"], "comune": "Roma", "foglio": "100", "particella": str(200 + k),
             "valore": str(im["valore"]), "diritto": "proprieta", "quota_defunto": {"num": qd.numerator, "den": qd.denominator}}
        ob = {"provincia": "RM", "codice_comune": "H501", "codice_comune_amministrativo": "H501"}
        if im["tipo"] == "fabbricato":
            b.update(subalterno=str(k + 1), categoria=im["categoria"])
            # la rendita e' obbligatoria nel quadro EC ma non entra nelle imposte (calcolate sul valore): senza rendita si usa un
            # segnaposto, che resta nella pratica sintetica
            b["rendita"] = str(im["rendita"]) if im["rendita"] is not None else "1.00"
            ob.update(indirizzo="Via Esempio 1", classe="1", consistenza="1")
        else:
            ob.update(natura="T", tipologia_terreno="3", superficie={"ettari": 0, "are": 10, "centiare": 0})
            if im["reddito_dominicale"] is not None:
                ob["reddito_dominicale"] = str(im["reddito_dominicale"])
        beni.append(b)
        op_beni[bid] = ob
        devolvi(bid, "P" if im["prima_casa"] else None)
        prima_casa = prima_casa or im["prima_casa"]
    for k, ab in enumerate(c["altri_beni"]):
        bid = f"b_alt{k:03d}"
        beni.append({"id": bid, "_origine": {}, "tipo": "disponibilita_finanziaria",
                     "descrizione": ab["descrizione"] or TIPI_ALTRI_BENI[ab["tipo"]], "valore": str(ab["valore"]),
                     "diritto": "1", "quota_defunto": "1/1"})
        op_beni[bid] = {"tipo_cespite": ab["tipo"]}
        devolvi(bid)
    passivita, op_pass = [], {}
    for k, p in enumerate(c["passivita"]):
        psid = f"ps_pas{k:03d}"
        passivita.append({"id": psid, "_origine": {}, "descrizione": p["descrizione"] or "Passività (stima)",
                          "importo": str(p["importo"])})
        op = {"tipo": p["tipo"], "estremi_documento": "Documento (stima)", "data_documento": dd.isoformat(), "possesso": "1/1",
              "ripartizione": [{"persona_id": pid, "quota": f"{q.numerator}/{q.denominator}"} for pid, q in zip(pids, quote)]}
        if p["tipo"] == "3" and beni and beni[0]["tipo"] in ("fabbricato", "terreno"):
            op["bene_id"] = beni[0]["id"]
        op_pass[psid] = op
    gradi = [e["grado"] for e in c["eredi"]]
    stato_civile = "2" if "01" in gradi else ("4" if "02" in gradi else "1")
    dich = {"stato_civile": stato_civile, "devoluzione_per_legge": True, "firma_dichiarante": True,
            "tempistica_pagamento": "1",
            "presentatore": {"persona_id": pids[0], "codice_carica": "1", "telefono": "0600000000"},
            "versamento": {"iban": _iban(), "cf_titolare": persone[1]["codice_fiscale"]}}
    if prima_casa:
        dich["prima_casa"] = {"dichiara_requisiti": True, "requisito_comune": "residenza", "nessuna_altra_casa_comune": True,
                              "altra_casa": "nessuna"}
    tel = {"dichiarazione": dich, "persone": op_persone, "beni": op_beni}
    if op_devs:
        tel["devoluzioni"] = op_devs
    if op_pass:
        tel["passivita"] = op_pass
    return {"persone": persone, "beni": beni, "devoluzioni": devs, "passivita": passivita, "documenti_ref": [],
            "opzioni": {"telematico": tel}}


def _data_riferimento(dd: date, oggi: date) -> date:
    """Data della dichiarazione assunta per la stima: entro i dodici mesi dal decesso (le sanzioni non si stimano)."""
    try:
        termine = dd.replace(year=dd.year + 1) - timedelta(days=1)
    except ValueError:
        termine = dd + timedelta(days=364)
    return max(dd, min(oggi, termine))


_SIGLE = {
    "QE": "Valore dei beni ricevuti",
    "QDN": "di cui denaro, gioielli e mobilia",
    "QP": "Passività a suo carico",
    "AN": "Valore netto ricevuto (beni meno passività)",
    "FR": "Franchigia",
    "QN": "Valore tassabile dopo la franchigia",
    "PR": "Presunzione del 10% per denaro, gioielli e mobilia",
    "QTI": "Base imponibile",
    "AL": "Aliquota",
    "ISL": "Imposta lorda (base × aliquota)",
    "RID": "Riduzioni",
    "DET": "Detrazione imposta estera",
    "ISN": "Imposta di successione dovuta",
}


def _passaggi_erede(b) -> list[dict]:
    out = []
    for p in b.passaggi:
        if p.sigla not in _SIGLE:
            continue
        v = _frazione_esatta(p.valore)
        if p.sigla in ("QDN", "PR", "RID", "DET") and v == 0:
            continue
        testo = f"{float(v) * 100:g}%".replace(".", ",") if p.sigla == "AL" else _euro(v)
        out.append({"sigla": p.sigla, "voce": _SIGLE[p.sigla], "valore": testo, "fonte": p.fonte})
    return out


def stima(richiesta: dict, oggi: date | None = None) -> dict:
    """Stima delle imposte. Restituisce un dizionario pronto per l'interfaccia e per lo strumento MCP ``stima_imposte``."""
    from . import prospetto_cliente as P
    from . import valore_catastale as VC
    from .telematico import quadri_efgh as QE
    from .telematico.calcolo import aliquota, calcola_da_xml, franchigia
    from .telematico.esporta import ContestoExport, esporta_xml

    oggi = oggi or date.today()
    c = leggi_richiesta(richiesta)
    gradi = _gradi()
    out: dict = {"avvertenza": AVVERTENZA, "stato": "stimato", "non_stimabile": [], "note": [], "passaggi": [],
                 "eredi": [], "imposte": [], "valori_catastali": [], "quote_di_legge": None}
    legge = quote_legge(c["eredi"])
    if legge is not None:
        out["quote_di_legge"] = [f"{legge[i].numerator}/{legge[i].denominator}" for i in range(len(c["eredi"]))]
    if all(e["quota"] is None for e in c["eredi"]):
        if legge is None:
            out["stato"] = "non_stimabile"
            out["non_stimabile"].append("quote degli eredi: la combinazione di gradi di parentela non è coperta dalle quote di "
                                        "legge del programma (Allegato 5 del Fascicolo I); indicare le quote")
            return out
        quote = [legge[i] for i in range(len(c["eredi"]))]
        out["note"].append("Quote non indicate: usate le quote di legge (" +
                           ", ".join(f"erede {i + 1} {q.numerator}/{q.denominator}" for i, q in enumerate(quote)) + ").")
    else:
        if any(e["quota"] is None for e in c["eredi"]):
            raise DatiNonValidi("indicare la quota di tutti gli eredi, oppure di nessuno (si usano le quote di legge)")
        quote = [e["quota"] for e in c["eredi"]]
        if sum(quote) != 1:
            raise DatiNonValidi(f"la somma delle quote degli eredi è {sum(quote)}: deve essere 1")
        if legge is not None and quote != [legge[i] for i in range(len(quote))]:
            out["note"].append("Le quote indicate sono diverse da quelle di legge: la stima segue i motori della devoluzione per "
                               "legge, che possono rifiutarle (testamento o accordi non sono gestiti dalla calcolatrice).")
    # valori catastali proposti (motore valore_catastale) per gli immobili senza valore
    for k, im in enumerate(c["immobili"]):
        prov = {"persone": [{"ruolo": "defunto", "data_decesso": c["data_decesso"].isoformat()}],
                "devoluzioni": [{"id": "d", "bene_id": "b", "agevolazioni": "P"}] if im["prima_casa"] else []}
        b = {"id": "b", "tipo": im["tipo"], "categoria": im["categoria"], "diritto": "1",
             "quota_defunto": {"num": im["quota_defunto"].numerator, "den": im["quota_defunto"].denominator},
             "valore": str(im["valore"]) if im["valore"] is not None else None,
             "rendita": str(im["rendita"]) if im["rendita"] is not None else None,
             "reddito_dominicale": str(im["reddito_dominicale"]) if im["reddito_dominicale"] is not None else None,
             "natura": "T", "tipologia_terreno": "3"}
        if im["prima_casa"]:
            prov["opzioni"] = {"telematico": {"devoluzioni": {"d": {"agevolazioni": "P"}}}}
        vc = VC.calcola(prov, b) if (im["rendita"] is not None or im["reddito_dominicale"] is not None) else None
        voce = {"immobile": k + 1, "valore_catastale": vc["valore"] if vc and vc["calcolabile"] else None,
                "formula": vc["formula"] if vc else None, "motivo": vc["motivo"] if vc else None,
                "fonti": vc["fonti"] if vc else []}
        out["valori_catastali"].append(voce)
        if im["valore"] is None:
            if voce["valore_catastale"] is None:
                out["stato"] = "non_stimabile"
                out["non_stimabile"].append(f"immobile {k + 1}: indicare il valore" +
                                            (f" (valore catastale non calcolabile: {vc['motivo']})" if vc else
                                             " oppure la rendita (fabbricati) o il reddito dominicale (terreni)"))
                continue
            im["valore"] = Decimal(voce["valore_catastale"])
            out["note"].append(f"Immobile {k + 1}: usato il valore catastale proposto, {_euro(im['valore'])} ({vc['formula']}).")
        elif vc and vc["inferiore"]:
            out["note"].append(f"Immobile {k + 1}: il valore indicato è inferiore al valore catastale ({_euro(vc['valore'])}): "
                               "l'ufficio potrebbe rettificarlo.")
    if out["stato"] == "non_stimabile":
        return out
    if not c["immobili"] and not c["altri_beni"]:
        raise DatiNonValidi("aggiungere almeno un bene")

    dati = _pratica(c, quote)
    rif = _data_riferimento(c["data_decesso"], oggi)
    if rif < oggi and oggi > c["data_decesso"] + timedelta(days=366):
        out["note"].append("Sono passati più di dodici mesi dal decesso: sanzioni e interessi non stimabili (la stima assume la "
                           "presentazione nei termini).")
    ctx = ContestoExport(cf_fornitore=dati["persone"][1]["codice_fiscale"], tipo_fornitore="1", data_riferimento=rif,
                         scopo="bozza_tecnica")
    es = esporta_xml(dati, ctx)
    if es.xml is None and any(e.percorso.startswith("opzioni.telematico.dichiarazione.versamento") for e in es.errori):
        # nessun importo da versare con la dichiarazione: la sezione Versamento non va compilata (regola dell'esportazione)
        dati["opzioni"]["telematico"]["dichiarazione"].pop("versamento", None)
        es = esporta_xml(dati, ctx)
    if es.xml is None:
        out["stato"] = "non_stimabile"
        msg = [e.messaggio for e in es.errori] + list(es.non_supportato)
        out["non_stimabile"] += [m for m in dict.fromkeys(msg)] or ["dati non elaborabili dai motori di calcolo"]
        return out
    ef_mancante = next((e.messaggio for e in es.quadri_mancanti if e.percorso == "quadro[EF]"), None)
    if ef_mancante:
        out["non_stimabile"].append("imposte ipotecaria, catastale, tassa ipotecaria e bollo: " + ef_mancante)
    pr = P.leggi(es.xml)
    imp = {k: v for k, v in pr["imposte"]}
    calc_ef = (es.mappa.get("quadro:EF") or {}).get("calcoli") or {}
    tot = Decimal(0)
    n = c["circoscrizioni"]
    for etich, chiave in (("Imposta ipotecaria", "Imposta ipotecaria"), ("Imposta catastale", "Imposta catastale"),
                          ("Tassa ipotecaria", "Tassa ipotecaria"), ("Imposta di bollo", "Imposta di bollo")):
        if ef_mancante:
            continue
        v = imp.get(chiave)
        v = Decimal(v) if isinstance(v, Decimal) else Decimal(0)
        if n > 1 and chiave == "Tassa ipotecaria" and v:
            v = Decimal(QE.TASSA_CIRCOSCRIZIONE * n)
        if n > 1 and chiave == "Imposta di bollo" and v:
            v = Decimal(QE.BOLLO_CIRCOSCRIZIONE * n)
        out["imposte"].append({"voce": etich, "importo": str(v), "testo": _euro(v)})
        tot += v
    # passaggi delle imposte ipocatastali (dal quadro EF generato)
    if not ef_mancante and c["immobili"]:
        e1, e9 = calc_ef.get("EF1") or {}, calc_ef.get("EF9") or {}
        if e1.get("imponibile") not in (None, "0"):
            out["passaggi"].append(f"Imposta ipotecaria: 2% del valore degli immobili ({_euro(e1['imponibile'])}) = "
                                   f"{_euro(e1['imposta'])}; si paga almeno l'imposta fissa di {QE.imposta_fissa(c['data_decesso'])} €.")
        if e9.get("imponibile") not in (None, "0"):
            out["passaggi"].append(f"Imposta catastale: 1% del valore degli immobili ({_euro(e9['imponibile'])}) = "
                                   f"{_euro(e9['imposta'])}; si paga almeno l'imposta fissa di {QE.imposta_fissa(c['data_decesso'])} €.")
        e4 = calc_ef.get("EF4")
        if e4:
            out["passaggi"].append(f"Prima casa: {e4['numero']} immobile/i a imposta fissa ({_euro(e4['imposta'])} ipotecaria e "
                                   f"altrettanto catastale), esclusi dal 2% e dall'1%.")
        out["passaggi"].append(f"Tassa ipotecaria: {QE.TASSA_CIRCOSCRIZIONE} € e imposta di bollo: {QE.BOLLO_CIRCOSCRIZIONE} € per "
                               f"ogni circoscrizione immobiliare (qui {n}).")
        if n > 1:
            out["note"].append(f"Con {n} circoscrizioni la tassa ipotecaria e il bollo sono moltiplicati per {n}; la verifica "
                               "delle circoscrizioni reali spetta alla pratica.")
    if not c["immobili"]:
        out["passaggi"].append("Nessun immobile: niente imposte ipotecaria e catastale, tassa ipotecaria e bollo.")
    # imposta di successione (V-bis, dal 2025)
    r = calcola_da_xml(es.xml)
    cf_idx = {p["codice_fiscale"]: i for i, p in enumerate(dati["persone"][1:])}
    if r.stato == "completato":
        isn = r.imposta_ef18bis
        out["imposte"].insert(0, {"voce": "Imposta di successione", "importo": str(isn), "testo": _euro(isn)})
        tot += Decimal(isn)
        for b in r.beneficiari:
            i = cf_idx.get(b.codice_fiscale)
            e = c["eredi"][i]
            fr, _ = franchigia(e["grado"], e["disabile"])
            al, _ = aliquota(e["grado"])
            out["eredi"].append({
                "erede": i + 1, "nome": e["nome"] or f"Erede {i + 1}", "grado": e["grado"], "grado_testo": gradi.get(e["grado"]),
                "quota": f"{quote[i].numerator}/{quote[i].denominator}", "disabile": e["disabile"],
                "franchigia": _euro(fr), "aliquota": f"{float(al) * 100:g}%".replace(".", ","),
                "imposta": _euro(_frazione_esatta(b.isn_esatta)), "passaggi": _passaggi_erede(b)})
        out["eredi"].sort(key=lambda x: x["erede"])
        out["passaggi"].insert(0, "Imposta di successione: per ogni erede si toglie dal valore ricevuto (al netto delle "
                                  "passività) la franchigia del suo grado di parentela, poi si applica l'aliquota; la somma "
                                  "degli eredi, arrotondata all'euro, è l'imposta.")
        out["note"] += r.note[:1] if r.note and "<= 10" in r.note[0] else []
    else:
        out["non_stimabile"].append("imposta di successione: " + "; ".join(m.messaggio for m in r.motivi))
    for k, v in pr["imposte"]:
        if k.startswith("di cui") and isinstance(v, Decimal):
            out["note"].append(f"Imposta di successione: {_euro(v)} {k.removeprefix('di cui ')}.")
    out["totale"] = str(tot)
    out["totale_testo"] = _euro(tot)
    if out["non_stimabile"] and not out["imposte"]:
        out["stato"] = "non_stimabile"
    elif out["non_stimabile"]:
        out["stato"] = "parziale"
    out["assunzioni"] = [
        "Dichiarazione presentata nei termini, devoluzione per legge, eredi persone fisiche che accettano.",
        "Beni in piena proprietà; " + ("prima casa: requisiti assunti come presenti per il primo erede. " if any(
            i["prima_casa"] for i in c["immobili"]) else "") + "nessuna altra agevolazione o riduzione.",
        "Titoli di Stato e altri beni esenti, legati, testamento, rinunce, trust, crediti d'imposta: non gestiti dalla "
        "calcolatrice (non stimabili qui; usare la pratica completa).",
    ]
    return out


def pratica_iniziale(richiesta: dict) -> dict:
    """Dati per «Crea una pratica da questi dati»: data del decesso per la procedura guidata e operazioni iniziali che creano gli
    eredi (grado di parentela, nome se indicato). Nessun dato inventato: cognomi, codici fiscali e beni si completano nei quadri.
    Non scrive nulla: le operazioni le applica la creazione della pratica (POST /api/pratiche, campo «iniziali»)."""
    c = leggi_richiesta(richiesta)
    ops = []
    for e in c["eredi"]:
        campi = {"ruolo": "erede", "grado_parentela": e["grado"], "relazione_con_defunto": e["grado"]}
        if e["nome"]:
            campi["nome"] = e["nome"]
        ops.append({"op": "upsert", "coll": "persone", "campi": campi})
    return {"data_decesso": c["data_decesso"].isoformat(), "operazioni": ops,
            "da_completare": "cognome, nome e codice fiscale di defunto ed eredi, beni, passività" +
                             (", disabilità grave (quadro EA)" if any(e["disabile"] for e in c["eredi"]) else "")}
