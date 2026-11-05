"""Agevolazione «prima casa» (codici P, X, Z dell'attributo Agevolazioni; Sezione II del quadro EH; rigo EF4 e collegati).

Ogni regola cita la fonte (annotazione XSD di ``fornituraSUC13_v1.xsd`` SUC13_20250702 oppure ``Succ_FASCICOLO_I_Nov_23.pdf``,
pagina PDF). Nessuna regola dalla memoria. Dettaglio e casi esclusi: ``docs/regole/prima_casa.md``.

PERIMETRO SUPPORTATO
- quadro EC (fabbricati non tavolari, Italia), un codice per riga di devoluzione, letto da
  ``opzioni.telematico.devoluzioni[<id>].agevolazioni`` ('P', 'X' o 'Z');
- P: abitazione con categoria A/2-A/7 (Fascicolo I p. PDF 60: categorie «diverse da A/1, A/8 e A/9»), un solo immobile per
  soggetto; X: pertinenza C/2, C/6 o C/7, una per categoria, solo se lo stesso soggetto ha P; Z: immobile contiguo, solo del
  dichiarante e solo se il dichiarante ha anche P (un solo Z);
- dichiarante (presentatore con carica 1 presente in EA): Sezione II del quadro EH con le dichiarazioni indicate in
  ``opzioni.telematico.dichiarazione.prima_casa``; altri beneficiari (P e X): richiesta allegata al rigo EG9 (PrimaCasa)
  con il documento d'identita' (EG7), altrimenti il quadro risulta incompleto;
- quadro EF: rigo EF4 (Numero, valore, imposta fissa), esclusione dei beni agevolati dai righi EF1 ed EF9.

NON SUPPORTATI (blocco con motivo, mai implementati per analogia): codice Y; codice Z senza P dello stesso soggetto o richiesto da
un soggetto diverso dal dichiarante; quadro EM; diritto di abitazione del coniuge (campo DirittoAbitazione, valori 1-8);
requisiti dei trasferiti all'estero, delle forze armate (Opzioni FlagTrasferitoEstero, FlagForzeArmate, ...); evento
eccezionale cod. 1; credito d'imposta (Sezione III); combinazioni con altre agevolazioni o con riduzioni.
"""
from __future__ import annotations

from . import fonti as FO
from . import formati as F
from .. import valori as V

#: codici implementati
CODICI = ("P", "X", "Z")
#: categorie ammesse per l'abitazione (P, Z): Fascicolo I p. PDF 60 «case di abitazione con categorie catastali diverse da
#: A/1, A/8 e A/9». Le altre categorie A (A/10, A/11) e B-F non sono classificate dalle fonti: non supportate.
CAT_ABITAZIONE = ("A2", "A3", "A4", "A5", "A6", "A7")
CAT_ESCLUSE = ("A1", "A8", "A9")
#: pertinenze: Fascicolo I p. PDF 26-27 («limitatamente a una per ciascuna categoria ... C/2, C/6 e C/7»)
CAT_PERTINENZA = ("C2", "C6", "C7")

EL_AGEV = "QuadroEC/Modulo/Fabbricati/DevoluzioneEC/Devoluzione/Agevolazioni"
FONTE_CAT = FO.fonte_fasc1(60, "Allegato 2, prima casa cod. P e Z: case di abitazione con categorie diverse da A/1, A/8 e A/9")
FONTE_PERT = FO.fonte_fasc1(26, "pertinenze C/2, C/6, C/7, una per categoria; fino a 3") + "; " + FO.fonte_fasc1(27, "cod. X e Y")
FONTE_SINOTTICO = FO.fonte_fasc1(57, "quadro sinottico: P, Z, X, Y = imposta ipotecaria e catastale fisse, nessun effetto "
                                 "sull'imposta di successione")

CHIAVI_PRIMA_CASA = {"requisito_comune", "nessuna_altra_casa_comune", "altra_casa", "impegno_unione_catastale",
                     "dichiara_requisiti"}
#: Opzioni (scelta a) del modello EH14: elemento XSD SezioneII_AgevPrimaCasa/Opzioni
REQUISITO_COMUNE = {"residenza": "FlagComuneResidenza", "attivita": "FlagComuneAttivita",
                    "stabilire_residenza": "FlagCambioResidenza"}
ALTRA_CASA = {"nessuna": "FlagNessunaAltraCasa", "vendita": "FlagVenditaAltraCasa"}


def inizializza(x) -> None:
    """Stato per esportazione: righe con agevolazione, beni agevolati, richieste di soggetti diversi dal dichiarante."""
    x.agev_dev = {}          # id devoluzione -> codice
    x.agev_righe = []        # {"did", "bene_id", "persona_id", "codice", "quadro"}
    x.info_ec = {}           # id bene -> {"luogo", "cat", "sezione", "categoria"}
    x.pc_beni = set()        # beni con almeno una riga P/X/Z (l'agevolazione si estende a tutti i beneficiari del bene)
    x.pc_numero = 0          # EF4 col. 1
    x.pc_dichiarante = None  # {"P": bene, "Z": bene|None, "X": [beni]}
    x.pc_eg = False          # serve la richiesta al rigo EG9 (beneficiari diversi dal dichiarante)


def leggi_riga(x, d: dict, b: dict, quadro: str, perc: str) -> str | None:
    """Codice agevolazione della riga di devoluzione ``d`` (None se assente o se la riga va scartata)."""
    from .esporta import codice_enum
    v = _attr(x, d)
    if v is None or v == "":
        return None
    if V.e_stato(v):
        x.err("DATO_NON_DEFINITIVO", perc + ".agevolazioni", f"il dato e' in stato '{v['stato']}': non esportabile",
              FO.fonte_annotazione(EL_AGEV))
        return None
    try:
        codice = codice_enum(str(v).strip().upper(), "CodiciAgevolazioni_Type")
    except F.ValoreXml as e:
        x.err("VALORE_NON_VALIDO", perc + ".agevolazioni", str(e), FO.fonte_xsd(EL_AGEV))
        return None
    if codice in ("P", "X", "Y", "Z") and quadro not in ("EC", "EM"):
        # annotazione Agevolazioni: «I codici agevolazione P, Z, X e Y possono essere selezionati solo nella sezione
        # devoluzione dei quadri EC, EM»
        x.err("REGOLA_AGEVOLAZIONE_QUADRO", perc + ".agevolazioni", f"il codice {codice} e' ammesso solo nei quadri EC ed EM",
              FO.fonte_annotazione(EL_AGEV))
        return None
    if codice in ("L", "Q", "R", "F"):
        return None  # riduzioni dell'imposta di successione: gestite da riduzioni_art25.py
    from . import agevolazioni as AG
    if codice in AG.CODICI:
        return None  # A, C, D, E, G, H, M, N: gestite da agevolazioni.py
    if codice not in CODICI:
        x.ns.append(f"{perc}.agevolazioni={codice}: agevolazione non supportata in questa versione (supportati P, X, Z"
                    + ("; il codice Y richiede dichiarazione sostitutiva EG9 e regole non coperte dal perimetro" if codice == "Y" else "")
                    + ")")
        return None
    if quadro == "EM":
        x.ns.append(f"{perc}.agevolazioni={codice}: quadro EM (fabbricati tavolari) non supportato per la prima casa")
        return None
    return codice


def _attr(x, d: dict):
    from . import supplemento as SUP
    return SUP.attr(x.d, "devoluzioni", d, "agevolazioni")


def registra(x, did: str, bene_id: str, persona_id: str, codice: str, quadro: str) -> None:
    x.agev_dev[did] = codice
    x.agev_righe.append({"did": did, "bene_id": bene_id, "persona_id": persona_id, "codice": codice, "quadro": quadro})


def _id_dichiarante(x) -> str | None:
    """Soggetto EA corrispondente al presentatore: stesso codice fiscale (annotazione QuadroEG/PrimaCasa, «per dichiarante
    si intende il codice fiscale presente nella sezione Riservato a chi presenta il modello ... se presente nel quadro EA»)."""
    pres = x.presentatore
    if pres is None or not isinstance(pres.get("codice_fiscale"), str):
        return None
    cf = pres["codice_fiscale"].strip().upper()
    for p in x.ea:
        if isinstance(p.get("codice_fiscale"), str) and p["codice_fiscale"].strip().upper() == cf:
            return p["id"]
    return None


def valida(x) -> None:
    """Regole incrociate sulle righe con agevolazione P, X, Z (eseguita dopo la costruzione dei quadri dei beni)."""
    if not x.agev_righe:
        return
    righe = [r for r in x.agev_righe if r["bene_id"] not in x.scartati]
    dich = _id_dichiarante(x)
    per_sogg: dict[str, list[dict]] = {}
    for r in righe:
        per_sogg.setdefault(r["persona_id"], []).append(r)
    for r in righe:
        info = x.info_ec.get(r["bene_id"]) or {}
        categ = info.get("categoria")
        perc = f"devoluzioni[{r['did']}].agevolazioni"
        if r["codice"] in ("P", "Z"):
            if categ in CAT_ESCLUSE:
                x.err("REGOLA_PRIMA_CASA_CATEGORIA", perc, f"codice {r['codice']}: la categoria catastale {categ} (A/1, A/8, "
                      "A/9) esclude l'agevolazione prima casa", FONTE_CAT)
            elif categ not in CAT_ABITAZIONE:
                x.ns.append(f"{perc}: codice {r['codice']} su categoria catastale {categ}: le fonti ammettono la prima casa "
                            "per le case di abitazione diverse da A/1, A/8, A/9 ma non classificano questa categoria "
                            "(solo A/2-A/7 supportate)")
        else:  # X
            if categ not in CAT_PERTINENZA:
                x.err("REGOLA_PRIMA_CASA_CATEGORIA", perc, f"codice X: la pertinenza deve essere di categoria C/2, C/6 o C/7 "
                      f"(trovata {categ})", FONTE_PERT)
    for pid, rs in sorted(per_sogg.items()):
        P = [r for r in rs if r["codice"] == "P"]
        Z = [r for r in rs if r["codice"] == "Z"]
        X_ = [r for r in rs if r["codice"] == "X"]
        nome = f"persone[{pid}]"
        # annotazione Agevolazioni (EC): «P ... per uno stesso soggetto ... solo se relative allo stesso immobile»;
        # Fascicolo I p. PDF 26: «un solo immobile abitativo»
        if len({r["bene_id"] for r in P}) > 1:
            x.err("REGOLA_PRIMA_CASA_P_UNICO", nome, "l'agevolazione P puo' essere richiesta da un soggetto per un solo "
                  "immobile abitativo", FO.fonte_annotazione(EL_AGEV) + "; " + FO.fonte_fasc1(26, "cod. P"))
        if X_ and not P:
            x.err("REGOLA_PRIMA_CASA_X_SENZA_P", nome, "l'agevolazione X e' ammessa solo se lo stesso soggetto ha anche P",
                  FO.fonte_annotazione(EL_AGEV))
        cats = [(x.info_ec.get(r["bene_id"]) or {}).get("categoria") for r in X_]
        if len(set(cats)) != len(cats):
            x.err("REGOLA_PRIMA_CASA_X_CATEGORIA", nome, "una sola pertinenza X per ciascuna categoria C/2, C/6, C/7",
                  FO.fonte_annotazione(EL_AGEV) + "; " + FONTE_PERT)
        if Z:
            if not P:
                x.ns.append(f"{nome}: agevolazione Z senza P dello stesso soggetto (immobile contiguo a uno gia' acquisito "
                            "con la prima casa): richiede la dichiarazione sostitutiva EG9 e regole non coperte dal perimetro")
            elif pid != dich:
                x.ns.append(f"{nome}: agevolazione Z richiesta da un soggetto diverso dal dichiarante: non supportata")
            elif len({r["bene_id"] for r in Z}) > 1:
                x.ns.append(f"{nome}: piu' immobili con agevolazione Z: la Sezione II del quadro EH ne prevede uno solo")
    # beni agevolati: l'agevolazione si estende a tutti i beneficiari del bene (EF, annotazioni PrimaCasa/AgevolazionePX_Valore)
    x.pc_beni = {r["bene_id"] for r in righe}
    # EF4 col. 1: numero di immobili con P (Z solo in assenza di P, Y: non supportato); X non si conta
    # (annotazione QuadroEF/SezioneI_ImpostaIpotecaria/PrimaCasa/PrimaCasa_Numero; Fascicolo I p. PDF 41 rigo EF4)
    x.pc_numero = len({r["bene_id"] for r in righe if r["codice"] == "P"})
    x.pc_eg = any(r["persona_id"] != dich for r in righe)
    if dich is not None and dich in per_sogg:
        rs = per_sogg[dich]
        P = sorted({r["bene_id"] for r in rs if r["codice"] == "P"})
        Z = sorted({r["bene_id"] for r in rs if r["codice"] == "Z"})
        Xs = sorted({r["bene_id"] for r in rs if r["codice"] == "X"})
        if P:
            x.pc_dichiarante = {"P": P[0], "Z": Z[0] if Z else None, "X": Xs}


def _flag(v) -> bool | None:
    if v is True or str(v).strip().lower() in ("1", "si", "true"):
        return True
    if v is False or str(v).strip().lower() in ("0", "no", "false"):
        return False
    return None


def sezione_eh(x) -> dict | None:
    """Sezione II (SezioneII_AgevPrimaCasa) del quadro EH per l'agevolazione richiesta dal dichiarante."""
    from . import supplemento as SUP
    pc = x.pc_dichiarante
    if pc is None:
        return None
    el = "QuadroEH/PrimoModulo/SezioneII_AgevPrimaCasa"
    base = "opzioni.telematico.dichiarazione.prima_casa"
    fonte = FO.fonte_annotazione(el) + "; " + FO.fonte_fasc1(52, "Sezione II agevolazione prima casa") + "; modello EH14-EH18"
    dati = SUP.dich(x.d, "prima_casa")
    if not isinstance(dati, dict):
        x.err("DATO_MANCANTE", base, "con l'agevolazione prima casa richiesta dal dichiarante indicare le dichiarazioni della "
              f"Sezione II del quadro EH (chiavi: {', '.join(sorted(CHIAVI_PRIMA_CASA))})", fonte)
        return None
    ok = True
    if dati.get("dichiara_requisiti") is not True:
        x.err("DATO_MANCANTE", base + ".dichiara_requisiti", "la Sezione II attesta, con la firma, il possesso dei requisiti: "
              "confermare esplicitamente (true)", fonte)
        ok = False
    req = dati.get("requisito_comune")
    if req not in REQUISITO_COMUNE:
        x.err("DATO_MANCANTE" if req in (None, "") else "VALORE_NON_VALIDO", base + ".requisito_comune",
              f"indicare uno tra {sorted(REQUISITO_COMUNE)} (dichiarazione a del modello EH14: comune di residenza, comune "
              "dell'attivita', intenzione di stabilire la residenza entro 18 mesi; altri requisiti non supportati)", fonte)
        ok = False
    nac = _flag(dati.get("nessuna_altra_casa_comune"))
    if nac is None:
        x.err("DATO_MANCANTE", base + ".nessuna_altra_casa_comune", "dichiarazione b del modello EH14 (nessuna altra casa nel "
              "comune): indicare true", fonte)
        ok = False
    elif nac is False:
        x.err("REGOLA_PRIMA_CASA_REQUISITO", base + ".nessuna_altra_casa_comune", "il requisito b (non titolare di altra casa "
              "di abitazione nel comune) e' condizione dell'agevolazione: con false l'agevolazione non spetta",
              FO.fonte_fasc1(60, "Allegato 2: requisiti del beneficiario") + "; " + fonte)
        ok = False
    ac = dati.get("altra_casa")
    if ac not in ALTRA_CASA:
        x.err("DATO_MANCANTE" if ac in (None, "") else "VALORE_NON_VALIDO", base + ".altra_casa",
              f"indicare uno tra {sorted(ALTRA_CASA)} (dichiarazione c: nessuna altra casa acquistata con le agevolazioni; "
              "dichiarazione d: impegno a trasferirla entro due anni dal decesso)", fonte)
        ok = False
    if pc["Z"] is not None and _flag(dati.get("impegno_unione_catastale")) is not True:
        x.err("DATO_MANCANTE", base + ".impegno_unione_catastale", "con l'agevolazione Z indicare true (dichiarazione i: impegno "
              "a unire catastalmente gli immobili contigui entro tre anni; FlagContigui obbligatorio)",
              FO.fonte_annotazione(el + "/FlagContigui") + "; " + fonte)
        ok = False
    for k in dati:
        if k not in CHIAVI_PRIMA_CASA:
            x.ns.append(f"{base}.{k}: chiave non gestita")
    if not ok:
        return None

    def immobile(bid: str) -> dict:
        i = x.info_ec[bid]
        it = i["luogo"]["Italia"]
        luogo = {"Provincia": i["luogo"]["Provincia"], "Comune": it["ComuneAmministrativo"],
                 "CodiceComune": it["CodiceComune"]}
        if it.get("Indirizzo"):
            luogo["Indirizzo"] = it["Indirizzo"]
        r = {"Luogo": luogo}
        if i.get("sezione"):
            r["SezioneUrbana"] = i["sezione"]
        r["DatiCatastali"] = i["cat"]
        return r

    sez: dict = {"ImmobilePrincipale": immobile(pc["P"])}
    if pc["Z"] is not None:
        sez["ImmobileContiguo"] = immobile(pc["Z"])
    pert = sorted(pc["X"], key=lambda b: ((x.info_ec[b].get("categoria") or ""), b))
    if pert:
        sez["Pertinenza"] = [immobile(b) for b in pert]
    sez["Opzioni"] = {REQUISITO_COMUNE[req]: "1"}
    sez["FlagNessunaAltraCasaComune"] = "1"
    sez["AltraCasa"] = {ALTRA_CASA[ac]: "1"}
    if pc["Z"] is not None:
        sez["FlagContigui"] = "1"
    sez["FirmaDichiarante"] = "1"
    x.mappa["quadro:EH:SezioneII"] = {"coll": None, "quadro": "EH", "xpath": f"{x.XP_DICH}/suc:QuadroEH/suc:PrimoModulo/"
                                                                             "suc:SezioneII_AgevPrimaCasa"}
    return sez
