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
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from fractions import Fraction
from math import gcd

from . import valori as V
from .errori import DatiNonValidi as _DatiNonValidi

AVVERTENZA = "Stima: non sostituisce la dichiarazione né il controllo ufficiale."
#: limiti della calcolatrice (stima veloce): oltre questi numeri si usa la pratica completa. Senza limite 2000 passivita'
#: richiedevano quasi un minuto e bloccavano l'interfaccia (review del 07/11/2026 sera)
MAX_EREDI = 30
MAX_BENI = 50
MAX_PASSIVITA = 50
#: tipi di passivita' che richiedono il cespite di riferimento (annotazione XSD di QuadroED/Modulo/Passivita/
#: ProgressivoCespite); per il tipo 3 il cespite deve stare nei quadri EB, EC, EL, EM (qui: un immobile)
PASSIVITA_CON_CESPITE = {"3", "4", "5", "7"}
PASSIVITA_PREDEFINITA = "12"          # «Altre passivita'»: non richiede il cespite
FONTE_ARROTONDAMENTO = ("Fascicolo I, p. PDF 22 (valore dei beni: base imponibile «arrotondata all'unità di euro») e p. PDF 38 "
                        "(valore delle passività «arrotondato all'unità di euro»)")
_SI = {"true", "si", "sì", "1", "yes", "vero", "x"}
_NO = {"false", "no", "0", "", "falso"}
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
        raise DatiNonValidi(f"{cosa}: importo non valido ({v!r})") from None
    if d < 0:
        raise DatiNonValidi(f"{cosa}: importo negativo")
    return d


def _euro_intero(v, cosa: str, arrotondati: list) -> Decimal | None:
    """Valore di un bene o di una passivita' all'unita' di euro (il tracciato ammette solo euro interi, DatoNP_Type; le
    istruzioni chiedono il valore arrotondato all'euro: ``FONTE_ARROTONDAMENTO``). Mezzo euro per eccesso, come la regola
    di arrotondamento delle annotazioni XSD del quadro EF. Gli importi arrotondati finiscono in ``arrotondati``."""
    d = _importo(v, cosa)
    if d is None:
        return None
    n = d.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    if n != d:
        arrotondati.append(f"{cosa}: {_euro(d)} → {_euro(n)}")
    return n


def _booleano(v, cosa: str) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    if isinstance(v, (int, float)) and v in (0, 1):
        return bool(v)
    s = str(v).strip().lower()
    if s in _SI:
        return True
    if s in _NO:
        return False
    raise DatiNonValidi(f"{cosa}: valore non valido ({v!r}); indicare sì o no (true/false)")


def _elenco(r: dict, chiave: str, cosa: str, massimo: int) -> list[dict]:
    """Lista di oggetti della richiesta, con controllo del tipo e del numero (prima di qualsiasi elaborazione)."""
    v = r.get(chiave)
    if v in (None, ""):
        return []
    if not isinstance(v, list):
        raise DatiNonValidi(f"{chiave}: atteso un elenco di {cosa}")
    if len(v) > massimo:
        raise DatiNonValidi(f"al massimo {massimo} {cosa} nella calcolatrice (qui {len(v)}): per casi più grandi usare la "
                            "pratica completa")
    for i, x in enumerate(v, 1):
        if x is not None and not isinstance(x, dict):
            raise DatiNonValidi(f"{chiave}, voce {i}: dati non validi ({x!r}); atteso un oggetto con i campi "
                                "(es. {\"grado\": \"02\"} per un erede, {\"valore\": \"100000\"} per un bene)")
    return [x or {} for x in v]


def _indice(v, cosa: str, n: int) -> int | None:
    """Numero (da 1) di un elemento dell'elenco, restituito come indice da 0."""
    if v in (None, ""):
        return None
    try:
        i = int(str(v).strip())
    except ValueError:
        raise DatiNonValidi(f"{cosa}: numero non valido ({v!r})") from None
    if not 1 <= i <= n:
        raise DatiNonValidi(f"{cosa}: non esiste il numero {i}" + (f" (da 1 a {n})" if n else " (nessuno inserito)"))
    return i - 1


def _quota(v, cosa: str) -> Fraction | None:
    if v in (None, ""):
        return None
    if str(v).strip() == "1":
        return Fraction(1)
    try:
        q = V.parse_quota(v)
    except (V.ValoreNonValido, ValueError):
        raise DatiNonValidi(f"{cosa}: quota non valida ({v!r}); scrivere ad esempio 1/2") from None
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


def leggi_richiesta(r: dict, oggi: date | None = None) -> dict:
    """Controlla e normalizza i dati della calcolatrice. Solleva ``DatiNonValidi`` con un messaggio leggibile."""
    if not isinstance(r, dict):
        raise DatiNonValidi("dati della calcolatrice non validi: atteso un oggetto con data_decesso, eredi, immobili, "
                            "altri_beni, passivita")
    oggi = oggi or date.today()
    try:
        dd = date.fromisoformat(str(r.get("data_decesso") or ""))
    except ValueError:
        raise DatiNonValidi("indicare la data del decesso (AAAA-MM-GG)") from None
    if dd > oggi:
        raise DatiNonValidi("la data del decesso è nel futuro")
    # numero e tipo degli elenchi controllati prima di ogni elaborazione
    eredi_in = _elenco(r, "eredi", "eredi", MAX_EREDI)
    immobili_in = _elenco(r, "immobili", "immobili", MAX_BENI)
    altri_in = _elenco(r, "altri_beni", "altri beni", MAX_BENI)
    passivita_in = _elenco(r, "passivita", "passività", MAX_PASSIVITA)
    if len(immobili_in) + len(altri_in) > MAX_BENI:
        raise DatiNonValidi(f"al massimo {MAX_BENI} beni nella calcolatrice (immobili e altri beni insieme, qui "
                            f"{len(immobili_in) + len(altri_in)}): per casi più grandi usare la pratica completa")
    gradi = _gradi()
    arrotondati: list[str] = []
    ignorati: list[str] = []
    eredi = []
    for i, e in enumerate(eredi_in, 1):
        g = str(e.get("grado") or "").strip().upper()
        if g not in gradi:
            raise DatiNonValidi(f"erede {i}: scegliere il grado di parentela dal menu")
        eredi.append({"grado": g, "quota": _quota(e.get("quota"), f"erede {i}"),
                      "disabile": _booleano(e.get("disabile"), f"erede {i}, disabilità grave"),
                      "nome": str(e.get("nome") or "").strip()[:60]})
    if not eredi:
        raise DatiNonValidi("aggiungere almeno un erede")
    immobili = []
    for i, b in enumerate(immobili_in, 1):
        tipo = "terreno" if b.get("tipo") == "terreno" else "fabbricato"
        valore = _euro_intero(b.get("valore"), f"immobile {i}", arrotondati)
        if valore is not None and valore < 1:
            raise DatiNonValidi(f"immobile {i}: il valore deve essere di almeno 1 euro; lasciarlo vuoto per usare il valore "
                                "catastale proposto dalla rendita o dal reddito dominicale")
        immobili.append({"tipo": tipo, "valore": valore,
                         "rendita": _importo(b.get("rendita"), f"immobile {i}, rendita"),
                         "reddito_dominicale": _importo(b.get("reddito_dominicale"), f"immobile {i}, reddito dominicale"),
                         "categoria": str(b.get("categoria") or "A/2").strip().upper()[:5],
                         "categoria_ipotizzata": not str(b.get("categoria") or "").strip() and tipo == "fabbricato",
                         "prima_casa": _booleano(b.get("prima_casa"), f"immobile {i}, prima casa") and tipo == "fabbricato",
                         "quota_defunto": _quota(b.get("quota_defunto"), f"immobile {i}, quota del defunto") or Fraction(1)})
    altri, pos_altri = [], {}
    for i, b in enumerate(altri_in, 1):
        tc = str(b.get("tipo") or "CR").upper()
        if tc not in TIPI_ALTRI_BENI:
            raise DatiNonValidi(f"altro bene {i}: tipo non previsto")
        v = _euro_intero(b.get("valore"), f"altro bene {i}", arrotondati)
        if v is not None and v < 1:
            ignorati.append(f"altro bene {i} (valore zero)")
        elif v:
            pos_altri[i - 1] = len(altri)
            altri.append({"tipo": tc, "valore": v, "descrizione": str(b.get("descrizione") or "").strip()[:80]})
    from .telematico.xsd import enumerazioni
    tipi_pass = enumerazioni("CodiciPassivita_Type")
    passivita = []
    for i, p in enumerate(passivita_in, 1):
        cosa = f"passività {i}"
        tipo = str(p.get("tipo") or PASSIVITA_PREDEFINITA).strip()
        tipo = tipo.lstrip("0") or tipo
        if tipo not in tipi_pass:
            raise DatiNonValidi(f"{cosa}: tipo non previsto ({tipo!r}); scegliere il tipo dal menu (codici 1-12)")
        v = _euro_intero(p.get("importo"), cosa, arrotondati)
        if v is not None and v < 1:
            ignorati.append(f"{cosa} (importo zero)")
            continue
        if not v:
            continue
        voce = {"n": i, "tipo": tipo, "importo": v, "descrizione": str(p.get("descrizione") or "").strip()[:80]}
        if tipo in PASSIVITA_CON_CESPITE:
            im = _indice(p.get("immobile"), f"{cosa}, immobile di riferimento", len(immobili))
            ab = None if tipo == "3" else _indice(p.get("altro_bene"), f"{cosa}, bene di riferimento", len(altri_in))
            if im is None and ab is None:
                raise DatiNonValidi(
                    f"{cosa}: il tipo {tipo} ({tipi_pass[tipo].rstrip(';.')}) richiede il bene a cui si riferisce: " +
                    ("scegliere l'immobile del mutuo" + ("" if immobili else " (aggiungere prima l'immobile)") if tipo == "3"
                     else "scegliere l'immobile o l'altro bene") +
                    f", oppure usare il tipo {PASSIVITA_PREDEFINITA} (altre passività)")
            if ab is not None and ab not in pos_altri:
                raise DatiNonValidi(f"{cosa}: l'altro bene {ab + 1} non ha un valore")
            voce["cespite"] = ("immobile", im) if im is not None else ("altro", pos_altri[ab])
        passivita.append(voce)
    try:
        circ = int(r.get("circoscrizioni") or 1)
    except (TypeError, ValueError):
        raise DatiNonValidi("numero di circoscrizioni non valido") from None
    if not 1 <= circ <= 50:
        raise DatiNonValidi("numero di circoscrizioni fra 1 e 50")
    return {"data_decesso": dd, "eredi": eredi, "immobili": immobili, "altri_beni": altri, "passivita": passivita,
            "circoscrizioni": circ, "arrotondati": arrotondati, "ignorati": ignorati}


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
            ob.update(indirizzo="Via Esempio 1", classe="1")
            if im["categoria"][:1] in "ABC":      # la consistenza si indica solo per i gruppi A, B, C (esporta: REGOLA_CONSISTENZA)
                ob["consistenza"] = "1"
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
        if "cespite" in p:          # tipi 3, 4, 5, 7: il bene scelto (annotazione XSD di ProgressivoCespite)
            genere, j = p["cespite"]
            op["bene_id"] = f"b_imm{j:03d}" if genere == "immobile" else f"b_alt{j:03d}"
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


def termine_ordinario(dd: date) -> date:
    """Termine ordinario di presentazione: dodici mesi dalla data del decesso (Fascicolo I, p. PDF 6, «Termini di
    presentazione»). Stesso calcolo di ``cruscotto._termine`` (Prossime azioni): stessa data dell'anno dopo, 28 febbraio per
    chi e' deceduto il 29 febbraio. Le decorrenze diverse (curatore, rinuncia...) non sono gestite dalla calcolatrice."""
    try:
        return dd.replace(year=dd.year + 1)
    except ValueError:              # 29 febbraio
        return dd.replace(year=dd.year + 1, day=28)


def _data_riferimento(dd: date, oggi: date) -> date:
    """Data della dichiarazione assunta per la stima: entro il termine ordinario (le sanzioni non si stimano)."""
    return max(dd, min(oggi, termine_ordinario(dd)))


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
    c = leggi_richiesta(richiesta, oggi)
    gradi = _gradi()
    out: dict = {"avvertenza": AVVERTENZA, "stato": "stimato", "non_stimabile": [], "note": [], "passaggi": [],
                 "eredi": [], "imposte": [], "valori_catastali": [], "quote_di_legge": None}
    if c["arrotondati"]:
        out["note"].append("Importi arrotondati all'unità di euro, come chiedono le istruzioni: " + "; ".join(c["arrotondati"])
                           + ".")
    if c["ignorati"]:
        out["note"].append("Non considerati perché pari a zero: " + ", ".join(c["ignorati"]) + ".")
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
            out["note"].append(f"Immobile {k + 1}: usato il valore catastale proposto, {_euro(im['valore'])} ({vc['formula']})."
                               + (" Categoria non indicata: calcolato come abitazione A/2, verificare la categoria nella visura."
                                  if im.get("categoria_ipotizzata") else ""))
        elif vc and vc["inferiore"]:
            out["note"].append(f"Immobile {k + 1}: il valore indicato è inferiore al valore catastale ({_euro(vc['valore'])}): "
                               "l'ufficio potrebbe rettificarlo.")
    if out["stato"] == "non_stimabile":
        return out
    if not c["immobili"] and not c["altri_beni"]:
        raise DatiNonValidi("aggiungere almeno un bene")

    # valore quota della ripartizione delle passivita' (Fascicolo I p. PDF 38: «arrotondato all'unità di euro», senza criterio
    # per il resto): l'esportazione rifiuta le quote non intere, quindi per la SOLA stima l'importo e' portato al multiplo piu'
    # vicino del denominatore comune delle quote (a parita', per difetto: meno passivita' dedotte, stima prudente)
    mcm = 1
    for q in quote:
        mcm = mcm * q.denominator // gcd(mcm, q.denominator)
    adattati = []
    for k, p in enumerate(c["passivita"]):
        v = int(p["importo"])
        if mcm > 1 and v % mcm:
            giu = v - v % mcm
            nuovo = giu + mcm if v - giu > mcm - (v - giu) else giu
            if nuovo < mcm:
                nuovo = mcm
            adattati.append(f"passività {p['n']}: {_euro(v)} → {_euro(nuovo)}")
            p["importo"] = Decimal(nuovo)
    if adattati:
        out["note"].append("Per ripartire le passività fra gli eredi in euro interi, la stima usa importi multipli di "
                           f"{mcm}: " + "; ".join(adattati) + ". Nella pratica la ripartizione si indica nel quadro ED.")
    dati = _pratica(c, quote)
    rif = _data_riferimento(c["data_decesso"], oggi)
    termine = termine_ordinario(c["data_decesso"])
    if oggi > termine:
        out["note"].append(f"Il termine ordinario di presentazione (dodici mesi dal decesso) è scaduto il "
                           f"{termine.strftime('%d/%m/%Y')}: sanzioni e interessi non stimabili (la stima assume la "
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
        "Valori dei beni e delle passività arrotondati all'unità di euro (" + FONTE_ARROTONDAMENTO + "); le istruzioni non "
        "indicano il verso per questi valori: la calcolatrice arrotonda per eccesso da 50 centesimi, come prescrivono le "
        "annotazioni XSD per le imposte del quadro EF.",
    ]
    if c["passivita"]:
        out["assunzioni"].append("Passività dedotte per intero dal defunto (quota 1/1), ripartite fra gli eredi secondo le quote "
                                 "di eredità, con data del documento pari alla data del decesso. Il valore della quota di "
                                 "ciascun erede va in euro interi (Fascicolo I, p. PDF 38) ma le istruzioni non dicono come "
                                 "ripartire il resto: per la sola stima l'importo è portato al multiplo più vicino del "
                                 "denominatore comune delle quote (a parità, per difetto).")
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
