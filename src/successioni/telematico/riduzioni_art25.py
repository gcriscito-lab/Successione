"""Riduzioni dell'imposta di successione: art. 25 comma 1 (codici 1-5 con «Valore precedenti successioni») e codici di
agevolazione L, Q, R, F (art. 25 commi 2, 4-bis, 3, 4). Ogni regola cita la fonte; nessuna regola dalla memoria.
Dettaglio, formule e casi esclusi: ``docs/regole/riduzioni_art25.md``.

FONTI
- XSD ``fornituraSUC13_v1.xsd`` (SUC13_20250702): ``Riduzioni`` (CodiciRiduzioni25comma1_Type) e ``ValorePrecSucc`` nel rigo di
  ogni cespite; ``Agevolazioni`` della sezione devoluzione (annotazioni: quadri ammessi, gradi di parentela, esclusivita');
  ``QuadroEH/.../SezioneIV_AltreAgevRiduz``; ``QuadroEG/RiduzioniImposteSuccessione``.
- Fascicolo I (Succ_FASCICOLO_I_Nov_23.pdf) p. PDF 27 (Riduzioni art. 25 c. 1), 50 (righi EG10, EG11), 53 (Sezione IV),
  62-63 (quadro sinottico e descrizione dei codici).
- Guida al calcolo (All. Specifiche tecniche ...) pp. 5-7: formule r, Rid.agevL/Q/R/F, r25, Rid.art25.

PERIMETRO SUPPORTATO
- codici 1-5 con ``valore_prec_succ`` sul cespite (EB, EC, EL, EM, EN, EO, EP, EQ, ER esclusi i cespiti DN);
- L (EB, EC, EL, EM), Q (EB, EC, EL, EM, EN, EO), R (EB, EC, EL, EM), F (EC, EM); un solo codice per riga di devoluzione;
- richiesta del dichiarante: Sezione IV del quadro EH (dati in ``opzioni.telematico.dichiarazione.riduzioni_art25``); di un
  beneficiario diverso dal dichiarante: allegato al rigo EG11 (L, Q, 1-5) con documento d'identita' (EG7).

NON SUPPORTATI (blocco con motivo): combinazione fra codici 1-5 e agevolazioni sulla stessa riga; piu' righe R/F per lo stesso
beneficiario (la guida applica la soglia di 103.291 euro per riga, il Fascicolo p. 63 parla di «valore complessivo»); riduzioni
su cespiti DN; L in ER, EP, EQ; Q in EP, EQ; trust; beni esteri e imposta estera; agevolazioni A, C, D, E, G, M, N, H.
"""
from __future__ import annotations

from fractions import Fraction

from . import fonti as FO
from . import formati as F
from .. import valori as V
from . import supplemento as SUP

#: codici di agevolazione-riduzione gestiti qui
CODICI_AGEV = ("L", "Q", "R", "F")
CODICI_RID = ("1", "2", "3", "4", "5")

#: coefficienti di riduzione art. 25 c. 1 (guida p. 7: 1 anno 0,5; 2 anni 0,4; 3 anni 0,3; 4 anni 0,2; 5 anni 0,1;
#: Fascicolo I p. PDF 63: «dal 50% al 10%»)
COEFF_ART25 = {"1": Fraction(5, 10), "2": Fraction(4, 10), "3": Fraction(3, 10), "4": Fraction(2, 10), "5": Fraction(1, 10)}
#: coefficienti L, Q, R, F (guida p. 6)
COEFF_AGEV = {"L": Fraction(5, 10), "Q": Fraction(4, 10), "R": Fraction(4, 10), "F": Fraction(4, 10)}
#: soglia dei codici R ed F (guida p. 6; Fascicolo I p. PDF 62-63: «fino a valore di euro 103.291,00»)
SOGLIA_RF = Fraction(103291)

#: quadri in cui l'XSD ammette il codice (annotazione di Devoluzione/Agevolazioni: «F ... solo ... EC, EM»; «EN ... solo D, G, Q»;
#: «EO ... solo D, Q»; «ER ... solo A e L»; «C, D, E, M, N, F, R, G non ... EP, EQ e ER»)
QUADRI_XSD = {"L": ("EB", "EC", "EL", "EM", "EP", "EQ", "ER"),
              "Q": ("EB", "EC", "EL", "EM", "EN", "EO", "EP", "EQ"),
              "R": ("EB", "EC", "EL", "EM"),
              "F": ("EC", "EM")}
#: quadri supportati da questa versione (il Fascicolo p. PDF 63 descrive L come «beni immobili culturali»). Q solo in EN ed EO:
#: il controllo ufficiale SUC13 2.3.1 (eseguito in locale, diagnostico 3333) scarta Q su terreni e fabbricati che non siano
#: beni aziendali, e il bene aziendale (BeneAziendale, ImmobiliAziendali) non e' supportato
QUADRI_SUPPORTATI = {"L": ("EB", "EC", "EL", "EM"), "Q": ("EN", "EO"),
                     "R": ("EB", "EC", "EL", "EM"), "F": ("EC", "EM")}
QUADRI_RID = ("EB", "EC", "EL", "EM", "EN", "EO", "EP", "EQ", "ER")
#: gradi di parentela ammessi (annotazione XSD di Devoluzione/Agevolazioni, righi «L'agevolazione R/F/Q non puo' essere
#: richiesta da soggetti con grado di parentela diverso da ...»)
GRADI = {"R": {"01", "02", "03", "04", "5A", "5B", "06", "7A", "7B", "08", "9A", "9B", "10", "11"},
         "F": {"01", "02", "03", "04", "5A", "5B", "06", "7A", "7B"},
         "Q": {"01", "02", "03", "04", "5A", "5B", "06", "7A", "7B", "10", "11", "15", "16"}}
#: codici che, per uno stesso bene, escludono ogni altra agevolazione (annotazione XSD: «soltanto una delle seguenti tipologie:
#: A, C, D, E, L, M, N, P, X e Y ... F, G, Q e R possono invece essere presenti in contemporanea»)
ESCLUSIVI = {"A", "C", "D", "E", "L", "M", "N", "P", "X", "Y"}

EL_AGEV = "QuadroEC/Modulo/Fabbricati/DevoluzioneEC/Devoluzione/Agevolazioni"
EL_RID = "QuadroEC/Modulo/Fabbricati/DevoluzioneEC/Devoluzione/Riduzioni"
EL_VPS = "QuadroEC/Modulo/Fabbricati/ValorePrecSucc"
EL_IV = "QuadroEH/PrimoModulo/SezioneIV_AltreAgevRiduz"
FONTE_SINOTTICO = FO.fonte_fasc1(62, "quadro sinottico delle riduzioni dell'imposta di successione") + "; " + \
    FO.fonte_fasc1(63, "descrizione dei codici 1-5, L, R, F, Q")
CHIAVI_RIDUZIONI = {"dichiara_requisiti", "l", "a", "successione_precedente", "donazione_precedente"}
CHIAVI_L = {"num_protocollo", "data"}
CHIAVI_SUCC = {"ufficio", "anno", "volume", "numero"}
CHIAVI_DON = {"ufficio", "serie", "numero", "sottonumero"}


def inizializza(x) -> None:
    x.rid_dev = {}        # id devoluzione -> codice 1-5
    x.ra_righe = []       # {"did", "bene_id", "persona_id", "quadro", "agev", "rid"}
    x.ra_vps = {}         # id bene -> valore precedenti successioni (int)
    x.ra_eh = set()       # sezioni EH richieste dal dichiarante: "L", "Q", "art25"
    x.ra_eg = False       # richiesta di un beneficiario diverso dal dichiarante (rigo EG11)
    x.ra_altro = False    # codice R: attestazione da allegare al quadro EG (rigo EG8)


def _attr(x, d: dict, campo: str):
    return SUP.attr(x.d, "devoluzioni", d, campo)


def leggi_riga(x, d: dict, b: dict, quadro: str, perc: str, pid: str) -> None:
    """Legge ``agevolazioni`` (solo L, Q, R, F; gli altri codici sono di ``prima_casa``) e ``riduzioni`` della riga di
    devoluzione ``d``. Registra lo stato in ``x`` (``agev_dev``, ``rid_dev``, ``ra_righe``)."""
    from .esporta import codice_enum
    x.usa(d, "riduzioni")
    agev = _attr(x, d, "agevolazioni")
    agev = None if agev in (None, "") or V.e_stato(agev) else str(agev).strip().upper()
    if agev not in CODICI_AGEV:
        agev = None
    rid = _attr(x, d, "riduzioni")
    if rid in (None, ""):
        rid = None
    elif V.e_stato(rid):
        x.err("DATO_NON_DEFINITIVO", perc + ".riduzioni", f"il dato e' in stato '{rid['stato']}': non esportabile",
              FO.fonte_annotazione(EL_RID))
        return
    else:
        try:
            rid = codice_enum(str(rid).strip(), "CodiciRiduzioni25comma1_Type")
        except F.ValoreXml as e:
            x.err("VALORE_NON_VALIDO", perc + ".riduzioni", str(e), FO.fonte_xsd(EL_RID))
            return
    if agev is None and rid is None:
        return
    fonte_q = FO.fonte_annotazione(EL_AGEV)
    if x.tipo_ea.get(pid) == "5":
        x.err("REGOLA_RIDUZIONE_TRUST", perc, "agevolazioni e riduzioni non possono essere presenti in presenza di "
              "devoluzione a soggetti di tipo 5 (trust)", fonte_q + "; " + FO.fonte_annotazione(EL_RID))
        return
    if agev and rid:
        x.ns.append(f"{perc}: agevolazione {agev} e riduzione art. 25 c. 1 ({rid}) sulla stessa riga: combinazione non "
                    "coperta dalle fonti")
        return
    if agev:
        if quadro not in QUADRI_XSD[agev]:
            x.err("REGOLA_AGEVOLAZIONE_QUADRO", perc + ".agevolazioni", f"il codice {agev} non e' ammesso nel quadro "
                  f"{quadro} (ammessi: {', '.join(QUADRI_XSD[agev])})", fonte_q)
            return
        if quadro not in QUADRI_SUPPORTATI[agev]:
            x.ns.append(f"{perc}.agevolazioni={agev} nel quadro {quadro}: non supportato in questa versione "
                        f"(supportati: {', '.join(QUADRI_SUPPORTATI[agev])}; " + FO.fonte_fasc1(63, "codici L, Q, R, F") + ")")
            return
        grado = (x.soggetti_ea.get(pid) or {}).get("GradoParentela")
        if agev in GRADI and grado not in GRADI[agev]:
            x.err("REGOLA_AGEVOLAZIONE_GRADO", perc + ".agevolazioni", f"l'agevolazione {agev} non puo' essere richiesta da "
                  f"un soggetto con grado di parentela {grado} (ammessi: {', '.join(sorted(GRADI[agev]))})", fonte_q)
            return
        x.agev_dev[d["id"]] = agev
    if rid:
        if quadro not in QUADRI_RID:
            x.err("REGOLA_RIDUZIONE_QUADRO", perc + ".riduzioni", f"quadro {quadro} senza riduzioni art. 25", FO.fonte_xsd(EL_RID))
            return
        if x.tipo_cespite.get(b["id"]) == "DN" or SUP.attr(x.d, "beni", b, "tipo_cespite") == "DN":
            x.ns.append(f"{perc}.riduzioni: riduzione su cespite DN (denaro, gioielli, mobilia): trattamento nella QDN non "
                        "coperto dalle fonti")
            return
        x.rid_dev[d["id"]] = rid
    x.ra_righe.append({"did": d["id"], "bene_id": b["id"], "persona_id": pid, "quadro": quadro, "agev": agev, "rid": rid})


def valore_prec_succ(x, b: dict, riga: dict, quadro: str) -> None:
    """Aggiunge ``ValorePrecSucc`` al rigo del cespite se ``opzioni.telematico.beni[<id>].valore_prec_succ`` e' presente."""
    v = SUP.attr(x.d, "beni", b, "valore_prec_succ")
    x.usa(b, "valore_prec_succ")
    if v in (None, ""):
        return
    perc = f"beni[{b['id']}].valore_prec_succ"
    fonte = FO.fonte_annotazione(EL_VPS) + "; " + FO.fonte_fasc1(23, "Valore precedenti successioni/donazioni")
    if V.e_stato(v):
        x.err("DATO_NON_DEFINITIVO", perc, f"il dato e' in stato '{v['stato']}': non esportabile", fonte)
        return
    if quadro not in QUADRI_RID:
        x.err("REGOLA_RIDUZIONE_QUADRO", perc, f"quadro {quadro} senza ValorePrecSucc", fonte)
        return
    try:
        s = F.euro_intero(v)
    except F.ValoreXml as e:
        x.err("VALORE_NON_VALIDO", perc, str(e), fonte)
        return
    if len(s) > 13 or int(s) <= 0:
        x.err("VALORE_NON_VALIDO", perc, f"{s}: importo positivo di massimo 13 cifre", fonte)
        return
    contenitore = riga["Possesso"] if quadro == "EO" else riga
    if "ValoreEsente" in contenitore:
        x.ns.append(f"{perc}: valore precedenti successioni su titolo esente: non coperto")
        return
    valore = contenitore.get("Valore")
    if valore is None or int(s) > int(valore):
        x.err("REGOLA_VALORE_PREC_SUCC", perc, f"il valore precedenti successioni ({s}) non puo' essere superiore al "
              f"campo valore ({valore})", fonte)
        return
    contenitore["ValorePrecSucc"] = s
    x.ra_vps[b["id"]] = int(s)


def valida(x) -> None:
    """Regole incrociate (eseguita dopo la costruzione dei quadri dei beni, prima del calcolo)."""
    from . import prima_casa as PC
    righe = [r for r in x.ra_righe if r["bene_id"] not in x.scartati]
    dich = PC._id_dichiarante(x)
    per_bene: dict[str, list[str]] = {}
    for did, rg in x.righe_dev.items():
        per_bene.setdefault(rg["bene_id"], []).append(did)
    for bid in sorted(set(x.ra_vps) | {r["bene_id"] for r in righe if r["rid"]}):
        if bid in x.scartati:
            continue
        codici = [x.rid_dev.get(did) for did in per_bene.get(bid, [])]
        fonte = FO.fonte_annotazione(EL_RID) + "; " + FO.fonte_annotazione(EL_VPS)
        if bid in x.ra_vps:
            if None in codici or len(set(codici)) != 1:
                x.err("REGOLA_RIDUZIONI_ART25", f"beni[{bid}]", "con il valore precedenti successioni il campo Riduzioni e' "
                      "obbligatorio e deve assumere lo stesso valore in tutti i righi della devoluzione del bene", fonte)
        elif any(codici):
            x.err("REGOLA_RIDUZIONI_ART25", f"beni[{bid}]", "la riduzione art. 25 c. 1 richiede il valore precedenti "
                  "successioni del cespite (opzioni.telematico.beni[<id>].valore_prec_succ)", fonte)
    # esclusivita' per bene (annotazione XSD): L, P, X, ... non convivono con altre agevolazioni dello stesso bene
    codici_bene: dict[str, set] = {}
    for r in x.agev_righe:
        codici_bene.setdefault(r["bene_id"], set()).add(r["codice"])
    for r in righe:
        if r["agev"]:
            codici_bene.setdefault(r["bene_id"], set()).add(r["agev"])
    for bid, cod in sorted(codici_bene.items()):
        if bid in x.scartati:
            continue
        for c in sorted(cod & ESCLUSIVI):
            if cod - {c}:
                x.err("REGOLA_AGEVOLAZIONE_ESCLUSIVA", f"beni[{bid}]", f"per uno stesso bene l'agevolazione {c} esclude ogni "
                      f"altra agevolazione (trovate: {', '.join(sorted(cod))})", FO.fonte_annotazione(EL_AGEV))
                break
    # codici R ed F: soglia per riga nella guida, «valore complessivo» nel Fascicolo
    for cod in ("R", "F"):
        conta: dict[str, int] = {}
        for r in righe:
            if r["agev"] == cod:
                conta[r["persona_id"]] = conta.get(r["persona_id"], 0) + 1
        for pid, n in sorted(conta.items()):
            if n > 1:
                x.ns.append(f"persone[{pid}]: {n} righe con codice {cod}: la guida applica la soglia di 103.291 euro per "
                            "riga, il Fascicolo I (p. PDF 63) la riferisce al valore complessivo: caso non coperto")
    for r in righe:
        if r["rid"] and r["did"] in {a["did"] for a in x.agev_righe}:
            x.ns.append(f"devoluzioni[{r['did']}]: riduzione art. 25 insieme all'agevolazione prima casa: non coperto")
        persona_dich = r["persona_id"] == dich
        # richiesta del dichiarante: Sezione IV del quadro EH; di altri: allegato EG11 (Fascicolo I p. PDF 50, 53;
        # annotazione di QuadroEG/RiduzioniImposteSuccessione)
        if r["agev"] == "L" or r["agev"] == "Q" or r["rid"]:
            if persona_dich:
                x.ra_eh.add("L" if r["agev"] == "L" else "Q" if r["agev"] == "Q" else "art25")
            else:
                x.ra_eg = True
        if r["agev"] == "R":
            x.ra_altro = True


def _tipo_ufficio(x, v, perc, fonte, nome):
    from .esporta import codice_enum
    try:
        return codice_enum(str(v), "UfficioDiRegistrazione_Type")
    except F.ValoreXml as e:
        x.err("VALORE_NON_VALIDO", f"{perc}.{nome}", str(e), fonte)
        return None


def sezione_eh(x) -> dict | None:
    """Sezione IV del quadro EH (``SezioneIV_AltreAgevRiduz``) per le richieste del dichiarante."""
    base = "opzioni.telematico.dichiarazione.riduzioni_art25"
    dati = SUP.dich(x.d, "riduzioni_art25")
    fonte = FO.fonte_annotazione(EL_IV) + "; " + FO.fonte_fasc1(53, "Sezione IV altre agevolazioni e riduzioni")
    if not x.ra_eh:
        if dati is not None:
            x.err("DATI_INCOERENTI", base, "la Sezione IV del quadro EH puo' essere compilata solo con A, C, D, E, L, Q o "
                  "riduzioni art. 25 c. 1 richieste dal dichiarante", fonte)
        return None
    if not isinstance(dati, dict):
        x.err("DATO_MANCANTE", base, "con riduzioni richieste dal dichiarante indicare i dati della Sezione IV del quadro EH "
              f"(chiavi: {', '.join(sorted(CHIAVI_RIDUZIONI))})", fonte)
        return None
    for k in dati:
        if k not in CHIAVI_RIDUZIONI:
            x.ns.append(f"{base}.{k}: chiave non gestita")
    ok = True
    if dati.get("dichiara_requisiti") is not True:
        x.err("DATO_MANCANTE", base + ".dichiara_requisiti", "la Sezione IV attesta, con la firma, il possesso dei requisiti: "
              "confermare esplicitamente (true)", fonte)
        ok = False
    sez: dict = {}
    esenz: dict = {}
    for cod, chiave, tipo_xml, flag in (("A", "a", "AgevolazTipoA", "FlagA"), ("L", "l", "AgevolazTipoL", "FlagL")):
        if cod not in x.ra_eh:
            continue
        l = dati.get(chiave)
        el = EL_IV + "/EsenzioneImpostaSuccessione/" + tipo_xml
        if not isinstance(l, dict) or set(l) - CHIAVI_L or not l.get("num_protocollo") or not l.get("data"):
            x.err("DATO_MANCANTE", base + "." + chiave, f"con il codice {cod} richiesto dal dichiarante indicare "
                  "{num_protocollo, data} (estremi della richiesta/attestazione dei beni culturali)",
                  FO.fonte_annotazione(el) + "; " + FO.fonte_fasc1(53, "N.B. richiesta di attestazione"))
            ok = False
        else:
            if not 7 <= len(str(l["num_protocollo"])) <= 16:
                x.err("VALORE_NON_VALIDO", base + f".{chiave}.num_protocollo", f"il numero protocollo {cod} deve avere da 7 a 16 "
                      "caratteri", "controllo ufficiale SUC13 2.3.1 eseguito in locale, diagnostico 3128 ('Numero protocollo "
                      "L'); non e' scritto negli XSD")
                ok = False
            try:
                esenz[tipo_xml] = {flag: "1", "NumProtocollo": F.an(l["num_protocollo"], 35),
                                   "Data": F.data(l["data"], non_oltre=x.oggi)}
            except F.ValoreXml as e:
                x.err("VALORE_NON_VALIDO", base + "." + chiave, str(e), FO.fonte_annotazione(el))
                ok = False
    if esenz:
        sez["EsenzioneImpostaSuccessione"] = {**esenz, "FirmaDichiarante": "1"}
    from . import agevolazioni as AG
    flag_agev = AG.flags_agevolazioni_eh(x)          # FlagC, FlagD, FlagE (modello EH, sezione Agevolazioni)
    if "Q" in x.ra_eh:
        flag_agev["FlagQ"] = "1"
    if flag_agev:
        sez["Agevolazioni"] = {**flag_agev, "FirmaDichiarante": "1"}
    if "art25" in x.ra_eh:
        r = _riduzioni_art25_eh(x, dati, base, fonte)
        if r is None:
            ok = False
        else:
            sez["Riduzioni"] = r
    if not ok:
        return None
    x.mappa["quadro:EH:SezioneIV"] = {"coll": None, "quadro": "EH", "xpath": f"{x.XP_DICH}/suc:QuadroEH/suc:PrimoModulo/"
                                                                             "suc:SezioneIV_AltreAgevRiduz"}
    return sez


def _riduzioni_art25_eh(x, dati: dict, base: str, fonte: str) -> dict | None:
    el = EL_IV + "/Riduzioni"
    succ, don = dati.get("successione_precedente"), dati.get("donazione_precedente")
    if (succ is None) == (don is None):
        x.err("DATO_MANCANTE", base, "con le riduzioni art. 25 c. 1 richieste dal dichiarante indicare "
              "successione_precedente {ufficio, anno, volume, numero} oppure donazione_precedente {ufficio, serie, numero, "
              "sottonumero}", FO.fonte_annotazione(el))
        return None
    out: dict = {}
    if succ is not None:
        p = base + ".successione_precedente"
        if not isinstance(succ, dict) or set(succ) - CHIAVI_SUCC or any(succ.get(k) in (None, "") for k in CHIAVI_SUCC):
            x.err("DATO_MANCANTE", p, "indicare {ufficio, anno, volume, numero}", FO.fonte_annotazione(el))
            return None
        uff = _tipo_ufficio(x, succ["ufficio"], p, FO.fonte_annotazione(el), "ufficio")
        anno, vol, num = str(succ["anno"]), str(succ["volume"]), str(succ["numero"])
        if not (anno.isdigit() and len(anno) == 4 and 1800 <= int(anno) <= x.oggi.year and vol.isdigit() and len(vol) <= 5
                and num.isdigit() and len(num) <= 6):
            x.err("VALORE_NON_VALIDO", p, "anno aaaa, volume fino a 5 cifre, numero fino a 6 cifre", FO.fonte_annotazione(el))
            return None
        if uff is None:
            return None
        out["UfficioTerritoriale"] = uff
        out["EstremiDichiarazionePrecedente"] = {"Anno": anno, "Volume": vol, "Numero": num}
    else:
        p = base + ".donazione_precedente"
        if not isinstance(don, dict) or set(don) - CHIAVI_DON or any(don.get(k) in (None, "") for k in ("ufficio", "serie", "numero")):
            x.err("DATO_MANCANTE", p, "indicare {ufficio, serie, numero[, sottonumero]}", FO.fonte_annotazione(el))
            return None
        uff = _tipo_ufficio(x, don["ufficio"], p, FO.fonte_annotazione(el), "ufficio")
        import re
        serie, num, sub = str(don["serie"]).upper(), str(don["numero"]), don.get("sottonumero")
        if not (re.fullmatch(r"[1-4][A-Z]?", serie) and num.isdigit() and len(num) <= 6
                and (sub in (None, "") or (str(sub).isdigit() and len(str(sub)) <= 3))):
            x.err("VALORE_NON_VALIDO", p, "serie [1-4] con lettera facoltativa, numero fino a 6 cifre, sottonumero fino a 3 "
                  "cifre (Serie_Type, XSD)", FO.fonte_annotazione(el))
            return None
        if uff is None:
            return None
        e = {"UfficioDiRegistrazione": uff, "Serie": serie, "NumeroRegistrazione": num}
        if sub not in (None, ""):
            e["SottonumeroRegistrazione"] = str(sub)
        out["EstremiDonazionePrecedente"] = e
    out["FirmaDichiarante"] = "1"
    return out
