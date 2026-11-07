"""Diritto di abitazione del coniuge superstite (art. 540 c.c., «legato ex lege»): casella ``DirittoAbitazione`` del quadro EC
(codici 1-8), effetti sul quadro EF e sulla Sezione II del quadro EH; diritto di abitazione (codice diritto 3) devoluto in una riga
della sezione devoluzione e suo valore. Scheda: ``docs/regole/diritto_abitazione.md``.

Fonti (lette il 2026-11-07; nessuna regola dalla memoria):
- Fascicolo I p. PDF 31-32 «Diritto di abitazione»: la casella si compila solo per l'immobile su cui con l'apertura della
  successione si costituisce il diritto di abitazione del coniuge (art. 540 c.c.); codici 1-4 (coniuge erede: 1 P, 2 Z, 3 X,
  4 senza prima casa), 5-8 (coniuge che ha rinunciato all'eredita' ma non al legato ex lege: 5 P, 6 Z, 7 X, 8 senza prima casa).
  N.B.: l'agevolazione si estende alle quote degli altri beneficiari della sezione devoluzione; il diritto indicato nella casella
  «viene riportato nella trascrizione ... e volturato al pari degli altri diritti presenti nella sezione devoluzione».
- Fascicolo I p. PDF 17: tipo soggetto 1 anche per il coniuge cui spetta il diritto di abitazione; tipo 4 per il coniuge
  rinunciatario all'eredita' che mantiene il legato ex lege (casella Rinuncia barrata).
- XSD fornituraSUC13_v1.xsd (SUC13_20250702), annotazioni di QuadroEC/Modulo/Fabbricati/DirittoAbitazione (presenza del coniuge,
  diritto del defunto 1 o 1S, niente trust ne' bene aziendale, codici 1-4 senza coniuge rinunciatario e 5-8 solo con il tipo
  soggetto 4, codici 1/2/3/5/6/7 solo per immobili italiani, agevolazioni delle righe coerenti con il codice), di Quota (valore
  quota = valore x quota se il diritto devoluto coincide con quello del defunto e non ci sono i diritti aggiuntivi superficie, uso e
  abitazione), di CodiceDiritto_Rip (abitazione 3 «in aggiunta» ai diritti scomponibili; per legge i codici coincidono con quello
  del defunto), del quadro EF (PrimaCasa, PrimaCasa_Numero, AgevolazionePX_Valore, ImpostaProporzionale), del quadro EG (PrimaCasa)
  e del quadro EH (SezioneII_AgevPrimaCasa, ImmobilePrincipale, ImmobileContiguo, Pertinenza);
  typesReg_v2.xsd, annotazione di DatiCatastaliFabbricati_Type/CategoriaCatastale (codici 1/2/5/6: categoria A escluse A1, A8, A9,
  A10 oppure F3; codici 3/7: C/2, C/6, C/7).
- Fascicolo I pp. PDF 24-25 e 30 (tabella «Usufrutto, uso e abitazione»: valore della piena proprieta' x saggio legale x
  coefficiente; «Proprieta' gravata da diritti reali di godimento»: piena proprieta' meno il diritto che la grava); coefficienti e
  saggio in ``usufrutto.py`` (allegato 4 al D.Lgs. 123/2025).

Non coperti (blocco con motivo): quadro EM (tavolari); codici 2/3/6/7 senza un immobile principale con codice 1 o 5; piu' immobili
principali o contigui; categorie A/11 e F/3; casella e riga di abitazione (codice 3) sullo stesso immobile; riga di abitazione con
diritti diversi dalla proprieta' (1) o con usufrutto/nuda proprieta' sullo stesso bene; abitazione su proprieta' superficiaria (3S).
"""
from __future__ import annotations

from fractions import Fraction

from . import fonti as FO
from . import prima_casa as PC
from . import supplemento as SUP
from . import usufrutto as USU

CODICI = ("1", "2", "3", "4", "5", "6", "7", "8")
#: codice -> agevolazione prima casa corrispondente (Fascicolo I pp. PDF 31-32); 4 e 8: senza prima casa
PRIMA_CASA = {"1": "P", "2": "Z", "3": "X", "5": "P", "6": "Z", "7": "X"}
RINUNCIATARIO = ("5", "6", "7", "8")
#: codice diritto devoluto «Abitazione» (Fascicolo I p. PDF 67, Allegato 4)
ABITAZIONE = "3"
EL = "QuadroEC/Modulo/Fabbricati/DirittoAbitazione"
FONTE = FO.fonte_annotazione(EL) + "; " + FO.fonte_fasc1(31, "Diritto di abitazione") + "; " + FO.fonte_fasc1(32, "codici 1-8")
FONTE_CAT = (f"typesReg_v2.xsd ({FO.VERSIONE_SPECIFICHE}), annotazione di DatiCatastaliFabbricati_Type/CategoriaCatastale")
FONTE_VALORE = (FO.fonte_fasc1(25, "tabella: usufrutto, uso e abitazione; proprieta' gravata") + "; "
                + FO.fonte_annotazione("QuadroEC/Modulo/Fabbricati/DevoluzioneEC/Devoluzione/CodiceDiritto_Rip") + "; " + USU.FONTE)


def inizializza(x) -> None:
    x.da_beni = {}        # id bene -> codice della casella DirittoAbitazione (solo righe esportate)
    x.da_righe3 = set()   # beni con una riga di devoluzione con codice diritto 3 (abitazione)


def leggi(x, b: dict, tavolare: bool, estero: bool) -> str | None:
    """Codice della casella ``DirittoAbitazione`` del fabbricato ``b`` (None se assente o non esportabile)."""
    x.usa(b, "diritto_abitazione")
    v = SUP.attr(x.d, "beni", b, "diritto_abitazione")
    if v in (None, ""):
        return None
    perc = f"beni[{b['id']}].diritto_abitazione"
    if isinstance(v, dict):
        x.err("DATO_NON_DEFINITIVO", perc, f"il dato e' in stato '{v.get('stato')}': non esportabile", FONTE)
        return None
    codice = str(v).strip()
    if codice not in CODICI:
        x.err("VALORE_NON_VALIDO", perc, f"{v!r}: codici ammessi 1-8 (DirittoAbitazione_Type)", FO.fonte_xsd(EL))
        return None
    if tavolare:
        x.ns.append(f"{perc}={codice}: diritto di abitazione nei fabbricati tavolari (quadro EM) non supportato")
        return None
    if estero and codice in PRIMA_CASA:
        x.err("REGOLA_DIRITTO_ABITAZIONE", perc, f"codice {codice}: i codici 1, 2, 3, 5, 6 e 7 (prima casa) sono ammessi solo per "
              "immobili italiani (provincia diversa da EE)", FONTE)
        return None
    return codice      # registrato in x.da_beni da esporta.py solo se il rigo del bene viene esportato


def _coniuge(x) -> str | None:
    return next((pid for pid, g in x.grado_ea.items() if g == "01"), None)


def valida(x) -> None:
    """Regole incrociate della casella (dopo la costruzione dei quadri dei beni e di PC.valida) ed effetti prima casa: i beni con
    codice 1/2/3/5/6/7 entrano fra i beni agevolati (EF), il codice 1/5 conta nel rigo EF4 col. 1 e, se il coniuge e' il
    dichiarante, determina gli immobili della Sezione II del quadro EH; altrimenti serve la richiesta al rigo EG9."""
    beni = dict(x.da_beni)
    if not beni:
        return
    coniuge = _coniuge(x)
    tipo4 = any(t == "4" for t in x.tipo_ea.values())
    for bid, codice in sorted(beni.items()):
        perc = f"beni[{bid}].diritto_abitazione"
        if coniuge is None:
            x.err("REGOLA_DIRITTO_ABITAZIONE", perc, "la casella richiede nel quadro EA il coniuge o la parte dell'unione civile "
                  "superstite (grado di parentela 01)", FONTE)
        if str(x.diritto_bene.get(bid) or "").upper() not in ("1", "1S"):
            x.err("REGOLA_DIRITTO_ABITAZIONE", perc, "la casella e' ammessa solo se il diritto del defunto e' la proprieta' (1) o la "
                  f"proprieta' superficiaria (1S); trovato {x.diritto_bene.get(bid)}", FONTE)
        if bid in x.immobili_az:
            x.err("REGOLA_DIRITTO_ABITAZIONE", perc, "la casella non e' ammessa per un bene aziendale", FONTE)
        righe = [r for r in x.righe_dev.values() if r["bene_id"] == bid]
        if any(x.tipo_ea.get(r["persona_id"]) == "5" for r in righe):
            x.err("REGOLA_DIRITTO_ABITAZIONE", perc, "la casella non e' ammessa con righe di devoluzione a un trust (tipo 5)", FONTE)
        if codice in RINUNCIATARIO and not tipo4:
            x.err("REGOLA_DIRITTO_ABITAZIONE", perc, f"codice {codice}: i codici 5-8 richiedono nel quadro EA il coniuge superstite "
                  "rinunciatario all'eredita' che mantiene il legato ex lege (tipo soggetto 4)", FONTE + "; " +
                  FO.fonte_fasc1(17, "Tipo soggetto, codice 4"))
        if codice not in RINUNCIATARIO and (tipo4 or (coniuge is not None and coniuge in x.rinunce)):
            x.err("REGOLA_DIRITTO_ABITAZIONE", perc, f"codice {codice}: con il coniuge rinunciatario (tipo soggetto 4) vanno usati i "
                  "codici 5-8", FONTE)
        if bid in x.da_righe3:
            x.ns.append(f"{perc}={codice}: casella del diritto di abitazione e riga di devoluzione con il diritto di abitazione "
                        "(codice 3) sullo stesso immobile: combinazione non descritta dalle fonti, non supportata")
        agev = PRIMA_CASA.get(codice)
        ammesse = {agev} if agev else None
        for r in righe:
            a = r.get("agevolazione")
            if ammesse is not None and a not in (None, "") and a not in ammesse:
                x.err("REGOLA_DIRITTO_ABITAZIONE", perc, f"codice {codice}: nella sezione devoluzione sono ammesse solo righe con "
                      f"agevolazione {agev} (trovata {a})", FONTE)
        categ = (x.info_ec.get(bid) or {}).get("categoria")
        if agev in ("P", "Z"):
            if categ in PC.CAT_ESCLUSE or categ == "A10" or (categ and categ[0] not in "AF"):
                x.err("REGOLA_DIRITTO_ABITAZIONE", perc, f"codice {codice}: categoria catastale {categ} non ammessa (categoria A "
                      "escluse A1, A8, A9 e A10, oppure F3)", FONTE_CAT)
            elif categ not in PC.CAT_ABITAZIONE:
                x.ns.append(f"{perc}={codice}: categoria catastale {categ}: solo A/2-A/7 supportate per la prima casa")
        elif agev == "X" and categ not in PC.CAT_PERTINENZA:
            x.err("REGOLA_DIRITTO_ABITAZIONE", perc, f"codice {codice}: la pertinenza deve essere di categoria C/2, C/6 o C/7 "
                  f"(trovata {categ})", FONTE_CAT)
    _prima_casa(x, beni, coniuge)


def _prima_casa(x, beni: dict, coniuge: str | None) -> None:
    pc = {bid: PRIMA_CASA[c] for bid, c in beni.items() if c in PRIMA_CASA}
    if not pc:
        return
    principali = sorted(b for b, a in pc.items() if a == "P")
    contigui = sorted(b for b, a in pc.items() if a == "Z")
    pertinenze = sorted(b for b, a in pc.items() if a == "X")
    fonte_pc = FONTE + "; " + FO.fonte_fasc1(26, "cod. P: un solo immobile abitativo")
    if len(principali) > 1:
        x.err("REGOLA_PRIMA_CASA_P_UNICO", "beni", "diritto di abitazione con prima casa sull'immobile principale (codice 1 o 5) "
              f"indicato su piu' immobili ({', '.join(principali)}): ammesso un solo immobile abitativo", fonte_pc)
    if (contigui or pertinenze) and not principali:
        x.ns.append("beni: diritto di abitazione con prima casa sull'immobile contiguo o sulla pertinenza (codici 2, 3, 6, 7) senza "
                    "l'immobile principale (codice 1 o 5): non supportato")
    if len(contigui) > 1:
        x.ns.append("beni: diritto di abitazione con prima casa su piu' immobili contigui (codice 2 o 6): non supportato")
    cats = [(x.info_ec.get(b) or {}).get("categoria") for b in pertinenze]
    if len(set(cats)) != len(cats):
        x.err("REGOLA_PRIMA_CASA_X_CATEGORIA", "beni", "una sola pertinenza (codice 3 o 7) per ciascuna categoria C/2, C/6, C/7",
              FO.fonte_fasc1(26, "pertinenze C/2, C/6, C/7, una per categoria"))
    if coniuge is not None:
        p_righe = {r["bene_id"] for r in x.agev_righe if r["persona_id"] == coniuge and r["codice"] == "P"
                   and r["bene_id"] not in x.scartati}
        if principali and p_righe - set(principali):
            x.err("REGOLA_PRIMA_CASA_P_UNICO", f"persone[{coniuge}]", "il coniuge chiede la prima casa (P) su un immobile diverso "
                  "da quello del diritto di abitazione con codice 1 o 5: ammesso un solo immobile abitativo", fonte_pc)
    # EF: l'agevolazione si estende a tutti i beneficiari del bene (annotazioni ImpostaProporzionale e AgevolazionePX_Valore);
    # EF4 col. 1: immobili con P o con il codice 1 o 5 (annotazione PrimaCasa_Numero; i codici 2 e 6 contano solo senza 1 e 5,
    # caso non supportato sopra)
    x.pc_beni = set(x.pc_beni) | set(pc)
    con_p = {r["bene_id"] for r in x.agev_righe if r["codice"] == "P" and r["bene_id"] not in x.scartati}
    x.pc_numero = len(con_p | set(principali))
    dich = PC._id_dichiarante(x)
    if coniuge is None:
        return
    if coniuge != dich or coniuge in x.rinunce:
        # annotazione QuadroEG/PrimaCasa: obbligatorio con il diritto di abitazione 1/2/3/5/6/7 per soggetti diversi dal dichiarante
        x.pc_eg = True
        return
    if not principali:
        return
    # Sezione II del quadro EH: immobile principale = codice 1/5, contiguo = 2/6, pertinenze = 3/7 (annotazioni ImmobilePrincipale,
    # ImmobileContiguo, Pertinenza: «se il dichiarante ha Grado di parentela = '01'»), uniti a quelli delle righe P/Z/X del coniuge
    prec = x.pc_dichiarante or {"P": principali[0], "Z": None, "X": []}
    z = prec.get("Z") or (contigui[0] if contigui else None)
    if prec.get("Z") and contigui and contigui[0] != prec["Z"]:
        x.ns.append(f"persone[{coniuge}]: immobile contiguo indicato sia con l'agevolazione Z sia con il codice 2/6 del diritto di "
                    "abitazione su immobili diversi: non supportato")
    x.pc_dichiarante = {"P": principali[0], "Z": z, "X": sorted(set(prec.get("X") or []) | set(pertinenze))}


# ----------------------------------------------------------------------------- riga di devoluzione con il diritto di abitazione (3)
def riga_supportata(dir_defunto: str | None, dir_devoluto: str, quadro: str) -> bool:
    """Riga con il diritto di abitazione (3) su un fabbricato EC in proprieta' (1) del defunto."""
    return quadro == "EC" and dir_defunto == USU.DIRITTO_PIENA and dir_devoluto == ABITAZIONE


def valori(valore: int, righe: list[dict]) -> dict:
    """``righe``: [{"id", "diritto", "quota": Fraction, "coefficiente": int|None}] con diritti 1 (proprieta', gravata dal diritto di
    abitazione) e 3 (abitazione). Abitazione = valore x quota x saggio x coefficiente (tabella «Usufrutto, uso e abitazione»);
    proprieta' gravata = valore x quota meno la parte proporzionale del diritto di abitazione che la grava (Fascicolo I p. PDF 25).
    Restituisce {"valori": {id: Fraction}, "errori": [str]}."""
    altri = sorted({r["diritto"] for r in righe} - {USU.DIRITTO_PIENA, ABITAZIONE})
    if altri:
        return {"valori": {}, "errori": [], "non_supportato": f"diritto di abitazione (3) insieme ai diritti {', '.join(altri)}: "
                                                               "solo la proprieta' (1) gravata e' supportata"}
    p = sum((r["quota"] for r in righe if r["diritto"] == USU.DIRITTO_PIENA), Fraction(0))
    a = sum((r["quota"] for r in righe if r["diritto"] == ABITAZIONE), Fraction(0))
    if p != 1 or a != 1:
        return {"valori": {}, "errori": [f"con il diritto di abitazione (3) le quote devono coprire il bene per ciascun diritto: "
                                         f"proprieta' {p} e abitazione {a} devono valere 1 (Fascicolo I p. PDF 24: quota 1/1 per "
                                         "ciascun diritto)"]}
    out, err, tot = {}, [], Fraction(0)
    for r in righe:
        if r["diritto"] == ABITAZIONE:
            if r["coefficiente"] is None:
                err.append(f"{r['id']}: coefficiente del diritto di abitazione non determinabile (eta' del titolare)")
                continue
            out[r["id"]] = Fraction(valore) * r["quota"] * USU.SAGGIO * r["coefficiente"]
            tot += out[r["id"]]
    if err:
        return {"valori": {}, "errori": err}
    for r in righe:
        if r["diritto"] == USU.DIRITTO_PIENA:
            out[r["id"]] = Fraction(valore) * r["quota"] - tot * r["quota"]
    return {"valori": out, "errori": []}


def ammessa_per_legge(x) -> bool:
    """Riga con codice diritto diverso da quello del defunto: ammessa solo con devoluzione per testamento o legge estera
    (annotazione di CodiceDiritto_Rip: per legge i codici devono coincidere con quello del defunto)."""
    return SUP.dich(x.d, "devoluzione_per_testamento") is True or SUP.dich(x.d, "legge_estera") is True
