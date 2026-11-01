"""Quadri EF (liquidazione), EG (documenti e allegati) ed EH (dichiarazioni sostitutive) - perimetro di base.

Usato da ``esporta._Export`` (stessa istanza ``x``: errori, non supportati, mappa, dati gia' validati dei quadri
EA/EB/EC/ER/ED). Ogni regola cita la fonte: annotazione dell'elemento XSD (fornituraSUC13_v1.xsd, SUC13_20250702) o
istruzioni ``Succ_FASCICOLO_I_Nov_23.pdf`` (pagina PDF = pagina stampata). Nessuna regola dalla memoria.

PERIMETRO (il resto e' ``non_supportato`` oppure ``quadri_mancanti`` con il motivo):

- EF: successioni aperte dal 2025-01-01, prima dichiarazione, immobili senza agevolazioni/riduzioni in un solo
  comune; Sezioni I (ipotecaria 2%), II (catastale 1%), III (tassa ipotecaria 120 euro per circoscrizione), IV (bollo
  85 euro per circoscrizione), V-bis (imposta di successione da ``calcolo.calcola_da_xml`` sul file dichiarato),
  totale EF19. Non coperti: agevolazioni (G, M, P/X/Y/Z, trust), regola dei valori fiscali dei soli terreni
  (Fascicolo I p. 40), imposta proporzionale inferiore alla fissa (fonti non concordi, vedi sotto), piu' comuni
  (l'individuazione della conservatoria richiede l'elenco dell'Agenzia), attestazione/copia conforme, crediti
  d'imposta, sostitutive, sanzioni e interessi, rateazione.
- EG: righi EG1 DichSost, EG5 DocumentiPassivita, EG6 AlberoGenealogico, EG7 DocumentiIdentita, EG8 Altro; i
  contenuti vengono SOLO da ``documenti.base64.dati_file_attachment`` (nome maiuscolo/conforme a cm:DatoAN_Type).
- EH: Sezione I con dichiarante erede/chiamato (carica 1), defunto deceduto (non morte presunta), devoluzione per
  legge, nessun interdetto/disabile, nessuna rinuncia, stato civile diverso da 5 e 7. Sezioni II-IV non coperte.
"""
from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from ..schema import Errore
from . import fonti as FO
from . import formati as F
from . import supplemento as SUP

DEC_2025 = date(2025, 1, 1)
DEC_2014 = date(2014, 1, 1)
#: imposta fissa ipotecaria/catastale per successioni aperte dal 2014-01-01 (Fascicolo I p. 39; annotazioni EF)
IMPOSTA_FISSA = 200
#: aliquote attuali (Fascicolo I p. 40 rigo EF1 col. 2: 2 per cento; p. 43 rigo EF9 col. 2: 1 per cento)
ALIQUOTA_IPOTECARIA = Decimal("0.02")
ALIQUOTA_CATASTALE = Decimal("0.01")
#: tassa per i servizi ipotecari e catastali per circoscrizione (Fascicolo I p. 44 rigo EF15 col. 2; annotazione
#: SezioneIII_TassaIpotecaria/Circoscrizioni_Imposta)
TASSA_CIRCOSCRIZIONE = 120
#: imposta di bollo per circoscrizione (Fascicolo I p. 45-46 rigo EF16; annotazione SezioneIV/Circoscrizioni_Imposta)
BOLLO_CIRCOSCRIZIONE = 85

#: righi del quadro EG nell'ordine dello schema; il numero di rigo e' quello del modello (fonti/Modello, quadro EG:
#: EG1 ... EG11) e coincide con l'ordine degli elementi in QuadroEG
SEZIONI_EG = ("DichSost", "Testamento", "Inventario", "CertificazioneImpostaVersataEstero", "DocumentiPassivita",
              "AlberoGenealogico", "DocumentiIdentita", "Altro", "PrimaCasa", "AgevolazioniImposteIpocatastali",
              "RiduzioniImposteSuccessione")
EG_SUPPORTATE = {"DichSost", "DocumentiPassivita", "AlberoGenealogico", "DocumentiIdentita", "Altro"}


def _snake(nome: str) -> str:
    out = ""
    for c in nome:
        out += ("_" + c.lower()) if c.isupper() and out else c.lower()
    return out


#: alias accettati per ``documenti_ref.tipo_eg``: nome dell'elemento XSD, forma snake_case, numero di rigo (EG1..EG11)
ALIAS_EG = {}
for _i, _s in enumerate(SEZIONI_EG, 1):
    ALIAS_EG[_s.lower()] = _s
    ALIAS_EG[_snake(_s)] = _s
    ALIAS_EG[f"eg{_i}"] = _s


def sezione_eg(tipo) -> str | None:
    if not isinstance(tipo, str):
        return None
    return ALIAS_EG.get(tipo.strip().lower().replace("-", "_").replace(" ", "_"))


def arrotonda_euro(d: Decimal) -> int:
    """'arrotondato all'unita' di euro, per difetto se la frazione e' inferiore a 50 centesimi e per eccesso se non
    inferiore' (annotazioni EF ImpostaProporzionale_Imposta; Fascicolo I p. 40 rigo EF1 col. 2)."""
    return int(d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _fa(el: str) -> str:
    return FO.fonte_annotazione(el)


# ============================================================================================== EF
def quadro_ef(x, xml_pre: bytes | None) -> dict | None:
    """Quadro EF. ``xml_pre``: dichiarazione gia' serializzata senza EF (fonte dei dati per il calcolo V-bis)."""
    el = "QuadroEF"
    dd = x.data_decesso
    if dd is None:
        return None
    immobili = [r for r in x.righe_dev.values() if r["quadro"] in ("EB", "EC")]
    obbligatorio = dd >= DEC_2025 or (bool(x.ea) and bool(immobili))
    if not obbligatorio:
        return None
    motivi: list[str] = []
    if dd < DEC_2025:
        motivi.append("successione aperta prima del 2025-01-01: quadro EF (imposte ipocatastali liquidate senza "
                      "sezione V-bis) non coperto da questa versione")
    if dd < DEC_2014:
        motivi.append("imposta fissa di 168 euro (successioni 2006-2013, Fascicolo I p. 39) non coperta")
    ef: dict = {}
    da_versare = Decimal(0)
    if immobili and not motivi:
        imponibile = sum((r["quota_valore"] for r in immobili), Decimal(0))
        if any(r["diritto"] == "10" for r in immobili):
            motivi.append("immobili gravati da oneri reali (codice diritto 10): esclusi dalle circoscrizioni "
                          "(Fascicolo I p. 44), caso non coperto")
        if not any(r["quadro"] == "EC" for r in immobili):
            motivi.append("soli terreni senza fabbricati: confronto con i valori fiscali dei terreni (Fascicolo I "
                          "p. 40, rigo EF1; annotazione ImpostaProporzionale_Imposta) non coperto")
        if imponibile != imponibile.to_integral_value():
            motivi.append(f"somma dei 'Valore quota' degli immobili {imponibile} non intera: l'arrotondamento "
                          "dell'imponibile EF1/EF9 (cm:DatoNP_Type) non e' indicato dalle fonti")
        ip = arrotonda_euro(imponibile * ALIQUOTA_IPOTECARIA)
        cat = arrotonda_euro(imponibile * ALIQUOTA_CATASTALE)
        if ip < IMPOSTA_FISSA or cat < IMPOSTA_FISSA:
            motivi.append(f"imposta proporzionale ({ip} / {cat}) inferiore alla fissa: il Fascicolo I (p. 40 e 43) "
                          "chiede 200 nella colonna 2, l'annotazione XSD solo nel totale dovuto (EF5/EF11): fonti non "
                          "concordi, caso non coperto")
        comuni = sorted({r["codice_comune"] for r in immobili})
        if len(comuni) != 1:
            motivi.append(f"immobili in piu' comuni {comuni}: la circoscrizione si individua dall'elenco delle "
                          "conservatorie (sito dell'Agenzia, Fascicolo I p. 44), non disponibile nelle fonti")
        if not motivi:
            imp = str(int(imponibile))
            fa1 = _fa(el + "/SezioneI_ImpostaIpotecaria/ImpostaProporzionale/ImpostaProporzionale_Imposta")
            ef["SezioneI_ImpostaIpotecaria"] = {
                "ImpostaProporzionale": {"ImpostaProporzionale_Imponibile": imp,
                                         "ImpostaProporzionale_Imposta": str(ip)},
                "ImpostaIpotecariaDovuta": str(ip), "ImpostaIpotecariaDaVersare": str(ip)}
            ef["SezioneII_ImpostaCatastale"] = {
                "ImpostaProporzionale": {"ImpostaProporzionale_Imponibile": imp,
                                         "ImpostaProporzionale_Imposta": str(cat)},
                "ImpostaCatastaleDovuta": str(cat), "ImpostaCatastaleDaVersare": str(cat)}
            n = len(comuni)
            ef["SezioneIII_TassaIpotecaria"] = {"Circoscrizioni_Numero": str(n),
                                                "Circoscrizioni_Imposta": str(TASSA_CIRCOSCRIZIONE * n)}
            ef["SezioneIV_ImpostaBollo"] = {"Circoscrizioni_Numero": str(n),
                                           "Circoscrizioni_Imposta": str(BOLLO_CIRCOSCRIZIONE * n)}
            da_versare += ip + cat + TASSA_CIRCOSCRIZIONE * n + BOLLO_CIRCOSCRIZIONE * n
            x.calcoli_ef = {
                "EF1": {"imponibile": imp, "imposta": ip, "fonte": fa1 + "; " + FO.fonte_fasc1(40, "rigo EF1")},
                "EF5/EF8": {"importo": ip, "fonte": FO.fonte_fasc1(41, "rigo EF5") + "; " + FO.fonte_fasc1(42, "EF8")},
                "EF9": {"imponibile": imp, "imposta": cat, "fonte": FO.fonte_fasc1(43, "rigo EF9")},
                "EF11/EF14": {"importo": cat, "fonte": FO.fonte_fasc1(44, "righi EF11, EF14")},
                "EF15": {"circoscrizioni": n, "imposta": TASSA_CIRCOSCRIZIONE * n,
                         "fonte": FO.fonte_fasc1(44, "rigo EF15: stesso codice comune -> 1 circoscrizione; 120 euro")},
                "EF16": {"circoscrizioni": n, "imposta": BOLLO_CIRCOSCRIZIONE * n,
                         "fonte": FO.fonte_fasc1(45, "rigo EF16: 85 euro") + "; " + FO.fonte_fasc1(46, "col. 3")},
            }
    if dd >= DEC_2025 and not motivi:
        vbis, extra, m2 = _sezione_vbis(x, xml_pre)
        motivi += m2
        if vbis is not None:
            ef["SezioneVBis_ImpostaSuccessione"] = vbis
            da_versare += extra
    if motivi:
        x.mancanti.append(Errore("QUADRO_EF_NON_GENERATO", "quadro[EF]", "il quadro EF e' obbligatorio per questa "
                                 "pratica ma non e' generato: " + "; ".join(motivi),
                                 _fa(el) + "; " + FO.fonte_fasc1(39, "quadro EF")))
        return None
    if da_versare:
        ef["TotaleDaVersare"] = F.euro_centesimi(da_versare)
    x.totale_da_versare = da_versare
    x.mappa["quadro:EF"] = {"coll": None, "quadro": "EF", "xpath": f"{x.XP_DICH}/suc:QuadroEF",
                            "totale_da_versare": str(da_versare), "calcoli": dict(getattr(x, "calcoli_ef", {}))}
    return ef or None


def _sezione_vbis(x, xml_pre):
    """Sezione V-bis dall'esito del calcolo sul file dichiarato (``calcolo.calcola_da_xml``)."""
    from .calcolo import calcola_da_xml
    el = "QuadroEF/SezioneVBis_ImpostaSuccessione"
    if xml_pre is None:
        return None, 0, ["dichiarazione non serializzabile: calcolo dell'imposta di successione non eseguito"]
    r = calcola_da_xml(xml_pre)
    x.calcolo = r
    if r.stato != "completato" or r.imposta_ef18bis is None:
        mot = "; ".join(m.messaggio for m in r.motivi) or r.stato
        return None, 0, [f"imposta di successione (EF18bis) non determinata: stato del calcolo '{r.stato}' ({mot})"]
    imposta = r.imposta_ef18bis
    if imposta <= 10:
        # Fascicolo I p. 47 col. 1: casella barrata se non e' dovuta alcuna imposta (es. importo <= 10 euro);
        # annotazione ImpostaDaVersare: se il risultato e' minore o uguale a 10 euro deve essere uguale a zero
        x.mappa["calcolo:EF18bis"] = {"coll": None, "quadro": "EF", "imposta": imposta, "versione": r.versione,
                                      "xpath": f"{x.XP_DICH}/suc:QuadroEF/suc:SezioneVBis_ImpostaSuccessione"}
        return {"ImpostaNonDovuta": "1"}, 0, []
    temp = SUP.dich(x.d, "tempistica_pagamento")
    if SUP.dich(x.d, "pagamento_rateale") not in (None, False):
        return None, 0, ["pagamento rateale dell'imposta di successione (EF18ter col. 2-3) non coperto"]
    if temp not in ("1", "2"):
        x.err("DATO_MANCANTE", "opzioni.telematico.dichiarazione.tempistica_pagamento", "imposta di successione "
              f"dovuta ({imposta}): indicare la tempistica di pagamento 1 (entro 90 giorni) o 2 (contestuale)",
              _fa(el + "/ImpostaCalcolata/TempisticaPagamento") + "; " + FO.fonte_fasc1(48, "rigo EF18ter col. 1"))
        return None, 0, []
    ic = {"Imposta": str(imposta), "ImpostaDaVersare": str(imposta), "TempisticaPagamento": temp}
    x.mappa["calcolo:EF18bis"] = {"coll": None, "quadro": "EF", "imposta": imposta, "versione": r.versione,
                                  "xpath": f"{x.XP_DICH}/suc:QuadroEF/suc:SezioneVBis_ImpostaSuccessione"}
    # EF19: EF18bis col. 5 solo con pagamento contestuale (codice 2) (Fascicolo I p. 48)
    return {"ImpostaCalcolata": ic}, (imposta if temp == "2" else 0), []


# ============================================================================================== EG
def quadro_eg(x) -> dict | None:
    """Quadro EG dai ``documenti_ref`` e dai file indicati in ``contesto.allegati`` (allegato_id -> file)."""
    from ..documenti.base64 import dati_file_attachment
    el = "QuadroEG"
    docs = x.d.get("documenti_ref", [])
    per_sez: dict[str, list] = {}
    for dr in sorted(docs, key=lambda e: (str(e.get("tipo_eg") or ""), str(e.get("allegato_id") or ""), e["id"])):
        x.usa(dr, "allegato_id", "tipo_eg", "finalita", "persona_id")
        perc = f"documenti_ref[{dr['id']}]"
        sez = sezione_eg(dr.get("tipo_eg"))
        if sez is None:
            x.err("VALORE_NON_VALIDO", perc + ".tipo_eg", f"{dr.get('tipo_eg')!r}: indicare il rigo del quadro EG "
                  f"({', '.join(SEZIONI_EG)} oppure EG1..EG11)", FO.fonte_xsd(el))
            continue
        if sez not in EG_SUPPORTATE:
            x.ns.append(f"{perc}: rigo EG {sez} non supportato in questa versione (testamento, inventario, imposta "
                        "estera, agevolazioni e riduzioni)")
            continue
        if dr.get("persona_id") not in (None, "") and dr["persona_id"] not in {p["id"] for p in x.d.get("persone", [])}:
            x.err("RIFERIMENTO_INESISTENTE", perc + ".persona_id", "persona inesistente", "src/successioni/schema.py")
        aid = dr.get("allegato_id")
        sorgente = (x.ctx.allegati or {}).get(aid) if aid else None
        if sorgente is None:
            x.err("ALLEGATO_NON_DISPONIBILE", perc + ".allegato_id", f"file dell'allegato {aid!r} non fornito "
                  "all'esportazione (contesto.allegati): il contenuto va incorporato in ImageData",
                  FO.fonte_xsd(el + "/" + sez + "/" + sez + "All/ImageData"))
            continue
        if isinstance(sorgente, dict):
            percorso, nome = sorgente.get("percorso"), sorgente.get("nome")
        else:
            percorso, nome = sorgente, None
        try:
            fa = dati_file_attachment(Path(percorso), nome=nome or Path(percorso).name,
                                      descrizione=dr.get("finalita") or None)
        except (OSError, ValueError) as e:
            x.err("ALLEGATO_NON_VALIDO", perc, str(e), FO.fonte_xsd(el + "/" + sez + "/" + sez + "All") + "; " +
                  FO.fonte_fasc1(49, "formati PDF/A-1a, PDF/A-1b, TIF/TIFF"))
            continue
        per_sez.setdefault(sez, []).append((dr["id"], fa))
    # obbligatorieta' (annotazioni dei righi EG)
    if x.ea and "AlberoGenealogico" not in per_sez:
        x.mancanti.append(Errore("ALLEGATO_OBBLIGATORIO_MANCANTE", "quadro[EG].AlberoGenealogico", "albero "
                                 "genealogico (rigo EG6) obbligatorio in presenza del quadro EA",
                                 _fa(el + "/AlberoGenealogico") + "; " + FO.fonte_fasc1(49, "rigo EG6")))
    if "AlberoGenealogico" in per_sez and len(per_sez["AlberoGenealogico"]) != 1:
        x.err("REGOLA_EG_NUMERO", "documenti_ref", "AlberoGenealogicoNum deve assumere valore 1: indicare un solo "
              "documento per l'albero genealogico", _fa(el + "/AlberoGenealogico/AlberoGenealogicoNum"))
    if x.valore_passivita and "DocumentiPassivita" not in per_sez:
        x.mancanti.append(Errore("ALLEGATO_OBBLIGATORIO_MANCANTE", "quadro[EG].DocumentiPassivita", "documenti "
                                 "comprovanti le passivita' (rigo EG5) obbligatori in presenza del quadro ED",
                                 _fa(el + "/DocumentiPassivita") + "; " + FO.fonte_fasc1(38, "passivita'")))
    if "DichSost" in per_sez and "DocumentiIdentita" not in per_sez:
        x.mancanti.append(Errore("ALLEGATO_OBBLIGATORIO_MANCANTE", "quadro[EG].DocumentiIdentita", "documento "
                                 "d'identita' (rigo EG7) obbligatorio in presenza del rigo EG1",
                                 _fa(el + "/DocumentiIdentita")))
    if x.fornitore_diverso_da_dichiarante and "DocumentiIdentita" not in per_sez:
        x.mancanti.append(Errore("ALLEGATO_OBBLIGATORIO_MANCANTE", "quadro[EG].DocumentiIdentita", "il modello non e' "
                                 "trasmesso direttamente dal dichiarante: allegare la copia del suo documento "
                                 "d'identita' (rigo EG7)", FO.fonte_fasc1(51, "quadro EH, premessa")))
    if not per_sez:
        return None
    eg: dict = {}
    for sez in SEZIONI_EG:
        if sez not in per_sez:
            continue
        righe = per_sez[sez]
        eg[sez] = {f"{sez}Num": str(len(righe)), f"{sez}All": [fa for _, fa in righe]}
        for i, (did, _) in enumerate(righe, 1):
            x.mappa[did] = {"coll": "documenti_ref", "quadro": "EG", "rigo": f"EG{SEZIONI_EG.index(sez) + 1}",
                            "xpath": f"{x.XP_DICH}/suc:QuadroEG/suc:{sez}/suc:{sez}All[{i}]"}
    x.avv("PDFA_NON_VERIFICATO_DALL_EXPORT", "quadro[EG]", "l'esportazione incorpora i file cosi' come sono: la "
          "conformita' PDF/A-1a/1b (pena lo scarto) va verificata con un validatore indipendente (area documenti)",
          FO.fonte_fasc1(49, "formati ammessi"))
    return eg


# ============================================================================================== EH
def quadro_eh(x, fr: dict, eg: dict | None) -> dict | None:
    """Quadro EH, Sezione I (dichiarazioni sostitutive) nel caso di base."""
    el = "QuadroEH/PrimoModulo/SezioneI_DichSost"
    if x.codice_carica in ("5", "6", "7"):
        return None  # annotazione QuadroEH: non deve essere presente con codice carica 5, 6, 7
    if x.codice_carica != "1" or x.presentatore is None or x.defunto is None:
        return None  # carica diversa da 1 gia' segnalata come non supportata nel frontespizio
    pres_fr = fr.get("Presentatore") or {}
    ana_p = pres_fr.get("DatiAnagrafici") or {}
    pres = dict(ana_p)
    pres["CodiceFiscale"] = pres_fr.get("CodiceFiscale")
    pres["CodiceCarica"] = pres_fr.get("CodiceCarica")
    dft = x.defunto
    comune = x.val("persone", dft, "comune_decesso", lambda v: F.an(v, 50), elemento=el + "/DatiDefunto/Decesso/Comune")
    prov = x.val("persone", dft, "provincia_decesso", lambda v: _pn(v), elemento=el + "/DatiDefunto/Decesso/Provincia")
    ana_d = (fr.get("DatiDefunto") or {}).get("DatiAnagrafici")
    data_dec = ((fr.get("DatiDefunto") or {}).get("UlterioriDati") or {}).get("DataDecesso")
    stato_civile = (fr.get("DatiDefunto") or {}).get("UlterioriDati", {}).get("StatoCivile")
    if stato_civile == "5":
        x.ns.append("quadro EH: stato civile 5 (separato) richiede la dichiarazione sulla separazione (Separazione), "
                    "non supportata")
    if stato_civile == "7":
        x.ns.append("quadro EH: stato civile 7 richiede FlagNoScioglimentoUnioneCivile, non supportato")
    if any(x.handicap_ea.values()):
        x.ns.append("quadro EH: soggetti con disabilita' richiedono la sezione Interdetti (rigo/modulo e certificatore),"
                    " non supportata")
    eredi = []
    for p in x.ea:
        if x.tipo_ea.get(p["id"]) not in ("1", "2", "3", "4"):
            continue
        sogg = x.soggetti_ea.get(p["id"]) or {}
        eredi.append({"CodiceFiscale": sogg.get("CodiceFiscale"), "GradoParentela": sogg.get("GradoParentela"),
                      "DatiAnagrafici": sogg.get("DatiAnagrafici")})
    sez: dict = {
        "Presentatore": pres,
        "DatiDefunto": {"DatiAnagrafici": ana_d, "Decesso": {"FlagDeceduto": "1", "DataDecesso": data_dec,
                                                             "Comune": comune, "Provincia": prov}},
        "Dichiarante": {"PresenzaDichiarante": "1"},
        "Testamento": {"FlagAssenzaTestamento": "1"},
        "Interdetti": {"FlagAssenzaInterdetti": "1"},
        "Rinuncia": {"FlagAssenzaRinuncia": "1"},
        "FirmaDichiarante": "1",
    }
    if eredi:
        sez["Eredi"] = eredi[:3]
    if eg and "DocumentiPassivita" in eg:
        conf = SUP.dich(x.d, "dichiara_copie_conformi")
        if conf is not True:
            x.err("DATO_MANCANTE", "opzioni.telematico.dichiarazione.dichiara_copie_conformi", "con i documenti delle "
                  "passivita' (rigo EG5) il dichiarante deve attestare che sono copie degli originali (EH, lettera l): "
                  "confermare esplicitamente (true)",
                  _fa(el + "/FlagPassivita") + "; " + FO.fonte_fasc1(52, "lettera l"))
        sez["FlagPassivita"] = "1"
    eh: dict = {"PrimoModulo": {"SezioneI_DichSost": sez}}
    altri = [eredi[i:i + 3] for i in range(3, len(eredi), 3)]
    if altri:
        eh["Modulo"] = [{"SezioneI_DichSost": {"Eredi": blocco}} for blocco in altri]
    if None in (comune, prov):
        return None
    x.mappa["quadro:EH"] = {"coll": None, "quadro": "EH", "xpath": f"{x.XP_DICH}/suc:QuadroEH"}
    return eh


def _pn(v) -> str:
    from .esporta import codice_enum
    return codice_enum(str(v).strip().upper(), "PN_Type")


# ============================================================================================== frontespizio
def versamento(x, cf_presentatore: str | None) -> dict | None:
    """Frontespizio/Versamento (addebito su conto): obbligatorio con EF19 diverso da zero e senza F24 (annotazione
    Frontespizio/Versamento; F24 'solo per le dichiarazioni inviate tramite Ufficio')."""
    from .identificativi import iban_modulo_97_valido
    el = "Frontespizio/Versamento"
    v = SUP.dich(x.d, "versamento") or {}
    if not getattr(x, "totale_da_versare", 0):
        if v:
            x.err("REGOLA_VERSAMENTO", "opzioni.telematico.dichiarazione.versamento", "nessun importo da versare: la "
                  "sezione Versamento non va compilata", _fa(el))
        return None
    if not isinstance(v, dict) or not v.get("iban") or not v.get("cf_titolare"):
        x.err("DATO_MANCANTE", "opzioni.telematico.dichiarazione.versamento", "totale da versare "
              f"{x.totale_da_versare}: indicare IBAN e codice fiscale del titolare del conto di addebito",
              _fa(el) + "; " + _fa("Frontespizio"))
        return None
    iban = str(v["iban"]).replace(" ", "").upper()
    if not iban_modulo_97_valido(iban):
        x.err("VALORE_NON_VALIDO", "opzioni.telematico.dichiarazione.versamento.iban", "IBAN italiano di 27 caratteri "
              "con cifre di controllo (modulo 97) corrette", FO.fonte_xsd(el + "/IBAN") + "; IBANCheckDigit "
              "(controlliXMLREG2013.jar)")
        return None
    try:
        cft = F.cf(v["cf_titolare"])
    except F.ValoreXml as e:
        x.err("VALORE_NON_VALIDO", "opzioni.telematico.dichiarazione.versamento.cf_titolare", str(e),
              FO.fonte_xsd(el + "/CodiceFiscaleTitolareCC"))
        return None
    ammessi = {cf_presentatore} if x.ctx.tipo_fornitore == "1" else {cf_presentatore, x.ctx.cf_fornitore}
    if cft not in ammessi:
        x.err("REGOLA_VERSAMENTO", "opzioni.telematico.dichiarazione.versamento.cf_titolare", "con TipoFornitore "
              f"{x.ctx.tipo_fornitore} il titolare del conto deve essere il dichiarante" +
              (" o il fornitore" if x.ctx.tipo_fornitore == "10" else ""), _fa(el + "/CodiceFiscaleTitolareCC"))
        return None
    return {"IBAN": iban, "CodiceFiscaleTitolareCC": cft}


def chiavi_usate() -> None:  # pragma: no cover - documentazione
    """Chiavi di ``opzioni.telematico`` lette da questo modulo: persone[defunto].comune_decesso/provincia_decesso,
    dichiarazione.versamento {iban, cf_titolare}, dichiarazione.tempistica_pagamento, dichiarazione.pagamento_rateale,
    dichiarazione.dichiara_copie_conformi."""

