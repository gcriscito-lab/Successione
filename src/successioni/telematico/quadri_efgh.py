"""Quadri EF (liquidazione), EG (documenti e allegati) ed EH (dichiarazioni sostitutive) - perimetro di base.

Usato da ``esporta._Export`` (stessa istanza ``x``: errori, non supportati, mappa, dati gia' validati dei quadri
EA/EB/EC/ER/ED). Ogni regola cita la fonte: annotazione dell'elemento XSD (fornituraSUC13_v1.xsd, SUC13_20250702) o
istruzioni ``Succ_FASCICOLO_I_Nov_23.pdf`` (pagina PDF = pagina stampata). Nessuna regola dalla memoria.

PERIMETRO (il resto e' ``non_supportato`` oppure ``quadri_mancanti`` con il motivo):

- EF: successioni aperte dal 2025-01-01, prima dichiarazione, immobili in un solo comune, senza agevolazioni/riduzioni
  salvo la prima casa (codici P, X, Z: rigo EF4 e Sezione II di EH, vedi ``prima_casa.py``); Sezioni I (ipotecaria 2%), II (catastale 1%), III (tassa ipotecaria 120 euro per circoscrizione), IV (bollo
  85 euro per circoscrizione), V-bis (imposta di successione da ``calcolo.calcola_da_xml`` sul file dichiarato),
  totale EF19. Non coperti: agevolazioni (G, M, Y, Z senza P, trust), regola dei valori fiscali dei soli terreni
  (Fascicolo I p. 40), imposta proporzionale inferiore alla fissa (fonti non concordi, vedi sotto), piu' comuni
  (l'individuazione della conservatoria richiede l'elenco dell'Agenzia), attestazione/copia conforme, crediti
  d'imposta, sostitutive, sanzioni e interessi, rateazione.
- EG: righi EG1 DichSost, EG5 DocumentiPassivita, EG6 AlberoGenealogico, EG7 DocumentiIdentita, EG8 Altro; i
  contenuti vengono SOLO da ``documenti.base64.dati_file_attachment`` (nome maiuscolo/conforme a cm:DatoAN_Type).
- EH: Sezione I con dichiarante erede/chiamato (carica 1), defunto deceduto (non morte presunta), devoluzione per
  legge, nessun interdetto/disabile, nessuna rinuncia, stato civile diverso da 5 e 7. Sezione II (prima casa del
  dichiarante) coperta da ``prima_casa.sezione_eh``; Sezioni III-IV non coperte.
"""
from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import re

from ..schema import Errore
from . import fonti as FO
from . import formati as F
from . import prima_casa as PC
from . import riduzioni_art25 as RA
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
EG_SUPPORTATE = {"DichSost", "Testamento", "DocumentiPassivita", "AlberoGenealogico", "DocumentiIdentita", "Altro",
                 "PrimaCasa", "RiduzioniImposteSuccessione"}


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
    immobili = [r for r in x.righe_dev.values() if r["quadro"] in ("EB", "EC", "EL", "EM")]
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
        # prima casa (docs/regole/prima_casa.md): i beni con P/X/Z escono dai righi EF1 ed EF9 (annotazioni
        # QuadroEF/SezioneI_ImpostaIpotecaria/ImpostaProporzionale e SezioneII_ImpostaCatastale/ImpostaProporzionale:
        # «l'agevolazione prima casa si estende a tutti i beneficiari ... in relazione a quel bene») ed entrano nel rigo EF4
        agevolati = [r for r in immobili if r["bene_id"] in x.pc_beni]
        immobili_prop = [r for r in immobili if r["bene_id"] not in x.pc_beni]
        imponibile = sum((r["quota_valore"] for r in immobili_prop), Decimal(0))
        valore_pc = sum((r["quota_valore"] for r in agevolati), Decimal(0))
        n_pc = x.pc_numero
        if agevolati and n_pc == 0:
            motivi.append("immobili con agevolazione prima casa senza alcun codice P: il numero di immobili del rigo EF4 "
                          "(solo P, o Z in assenza di P) non e' determinabile")
        if valore_pc != valore_pc.to_integral_value():
            motivi.append(f"somma dei 'Valore quota' degli immobili prima casa {valore_pc} non intera: l'arrotondamento "
                          "del rigo EF4 colonna 2 non e' indicato dalle fonti")
        if any(r["diritto"] == "10" for r in immobili):
            motivi.append("immobili gravati da oneri reali (codice diritto 10): esclusi dalle circoscrizioni "
                          "(Fascicolo I p. 44), caso non coperto")
        if not any(r["quadro"] in ("EC", "EM") for r in immobili):
            motivi.append("soli terreni senza fabbricati: confronto con i valori fiscali dei terreni (Fascicolo I "
                          "p. 40, rigo EF1; annotazione ImpostaProporzionale_Imposta) non coperto")
        if immobili_prop and imponibile != imponibile.to_integral_value():
            motivi.append(f"somma dei 'Valore quota' degli immobili {imponibile} non intera: l'arrotondamento "
                          "dell'imponibile EF1/EF9 (cm:DatoNP_Type) non e' indicato dalle fonti")
        # EF1: quadri EB, EC, EL, EM (Fascicolo I p. 40). EF9 (catastale): il testo (p. 43) non elenca i quadri; il controllo
        # ufficiale SUC13 2.3.1 eseguito in locale il 2026-11-03 esclude i terreni tavolari (EL) dalla base catastale.
        prop_cat = [r for r in immobili_prop if r["quadro"] != "EL"]
        imponibile_cat = sum((r["quota_valore"] for r in prop_cat), Decimal(0))
        ip = arrotonda_euro(imponibile * ALIQUOTA_IPOTECARIA)
        cat = arrotonda_euro(imponibile_cat * ALIQUOTA_CATASTALE)
        if (immobili_prop and ip < IMPOSTA_FISSA) or (prop_cat and cat < IMPOSTA_FISSA):
            motivi.append(f"imposta proporzionale ({ip} / {cat}) inferiore alla fissa: il Fascicolo I (p. 40 e 43) "
                          "chiede 200 nella colonna 2, l'annotazione XSD solo nel totale dovuto (EF5/EF11): fonti non "
                          "concordi, caso non coperto")
        # circoscrizioni (EF15, EF16): solo immobili del catasto ordinario; per i tavolari il controllo ufficiale SUC13 2.3.1
        # (locale, 2026-11-03) individua 0 circoscrizioni
        comuni = sorted({r["codice_comune"] for r in immobili if r["quadro"] in ("EB", "EC")})
        if len(comuni) > 1:
            motivi.append(f"immobili in piu' comuni {comuni}: la circoscrizione si individua dall'elenco delle "
                          "conservatorie (sito dell'Agenzia, Fascicolo I p. 44), non disponibile nelle fonti")
        if not motivi:
            imp = str(int(imponibile))
            fa1 = _fa(el + "/SezioneI_ImpostaIpotecaria/ImpostaProporzionale/ImpostaProporzionale_Imposta")
            # rigo EF4 (Fascicolo I p. PDF 41, annotazione PrimaCasa_Imposta): numero immobili x 200; EF5/EF11 = proporzionale + EF4
            fissa_pc = IMPOSTA_FISSA * n_pc
            ip = ip if immobili_prop else 0
            cat = cat if prop_cat else 0
            s1: dict = {}
            if immobili_prop:
                s1["ImpostaProporzionale"] = {"ImpostaProporzionale_Imponibile": imp,
                                              "ImpostaProporzionale_Imposta": str(ip)}
            if agevolati:
                s1["PrimaCasa"] = {"PrimaCasa_Numero": str(n_pc), "AgevolazionePX_Valore": str(int(valore_pc)),
                                   "PrimaCasa_Imposta": str(fissa_pc)}
            s1["ImpostaIpotecariaDovuta"] = str(ip + fissa_pc)
            s1["ImpostaIpotecariaDaVersare"] = str(ip + fissa_pc)
            ef["SezioneI_ImpostaIpotecaria"] = s1
            s2: dict = {}
            if prop_cat:
                s2["ImpostaProporzionale"] = {"ImpostaProporzionale_Imponibile": str(int(imponibile_cat)),
                                              "ImpostaProporzionale_Imposta": str(cat)}
            if agevolati:
                s2["ImpostaCatastaleFissa"] = str(fissa_pc)
            s2["ImpostaCatastaleDovuta"] = str(cat + fissa_pc)
            s2["ImpostaCatastaleDaVersare"] = str(cat + fissa_pc)
            ef["SezioneII_ImpostaCatastale"] = s2
            n = len(comuni)
            if n:
                ef["SezioneIII_TassaIpotecaria"] = {"Circoscrizioni_Numero": str(n),
                                                    "Circoscrizioni_Imposta": str(TASSA_CIRCOSCRIZIONE * n)}
                ef["SezioneIV_ImpostaBollo"] = {"Circoscrizioni_Numero": str(n),
                                               "Circoscrizioni_Imposta": str(BOLLO_CIRCOSCRIZIONE * n)}
            da_versare += ip + cat + 2 * fissa_pc + TASSA_CIRCOSCRIZIONE * n + BOLLO_CIRCOSCRIZIONE * n
            x.calcoli_ef = {
                "EF1": {"imponibile": imp, "imposta": ip, "fonte": fa1 + "; " + FO.fonte_fasc1(40, "rigo EF1")},
                "EF4": {"numero": n_pc, "valore": str(int(valore_pc)), "imposta": fissa_pc,
                        "fonte": FO.fonte_fasc1(41, "rigo EF4") + "; " + FO.fonte_fasc1(43, "rigo EF10") + "; " +
                        _fa(el + "/SezioneI_ImpostaIpotecaria/PrimaCasa") + "; " + PC.FONTE_SINOTTICO},
                "EF5/EF8": {"importo": ip + fissa_pc, "fonte": FO.fonte_fasc1(41, "rigo EF5") + "; " + FO.fonte_fasc1(42, "EF8")},
                "EF9": {"imponibile": str(int(imponibile_cat)), "imposta": cat, "fonte": FO.fonte_fasc1(43, "rigo EF9")},
                "EF11/EF14": {"importo": cat + fissa_pc, "fonte": FO.fonte_fasc1(44, "righi EF11, EF14")},
                "EF15": {"circoscrizioni": n, "imposta": TASSA_CIRCOSCRIZIONE * n,
                         "fonte": FO.fonte_fasc1(44, "rigo EF15: stesso codice comune -> 1 circoscrizione; 120 euro")},
                "EF16": {"circoscrizioni": n, "imposta": BOLLO_CIRCOSCRIZIONE * n,
                         "fonte": FO.fonte_fasc1(45, "rigo EF16: 85 euro") + "; " + FO.fonte_fasc1(46, "col. 3")},
            }
            if not agevolati:
                x.calcoli_ef.pop("EF4")
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
    # Fascicolo I p.6 (dodici mesi) e p.48 (tempistica 1/2). Le decorrenze particolari,
    # sospensioni e il ravvedimento non sono implementati: non finalizzare una tardiva
    # con imposta di successione dovuta, neppure cambiando semplicemente codice 1 in 2.
    try:
        termine_ordinario = x.data_decesso.replace(year=x.data_decesso.year + 1)
    except ValueError:  # 29 febbraio: nessuna regola di calendario fiscale indovinata
        return None, 0, ["termine di presentazione per decesso il 29 febbraio da verificare: caso non coperto "
                         "(Fascicolo I p.6, p.48)"]
    if x.oggi > termine_ordinario:
        return None, 0, ["dichiarazione tardiva rispetto al termine ordinario di dodici mesi: decorrenze "
                         "particolari, sanzioni/interessi e tempistica di pagamento non coperti; "
                         "non finalizzabile (Fascicolo I p.6 e p.48, EF18ter col.1)"]
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
        if sez == "Testamento" and SUP.dich(x.d, "devoluzione_per_testamento") is not True:
            x.err("DATI_INCOERENTI", perc + ".tipo_eg", "rigo EG2 (testamento) non ammesso senza devoluzione per testamento",
                  _fa(el + "/Testamento"))
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
            from ..documenti.limiti import LIMITE_ALLEGATO_DECIMALE, FONTE_ALLEGATO
            dim = Path(percorso).stat().st_size
            if dim > LIMITE_ALLEGATO_DECIMALE:
                x.err("ALLEGATO_OLTRE_LIMITE", perc, f"{dim} byte > {LIMITE_ALLEGATO_DECIMALE}: "
                      "ridurre o suddividere prima della codifica Base64", FONTE_ALLEGATO)
                continue
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
    testamento = SUP.dich(x.d, "devoluzione_per_testamento") is True
    if testamento and "Testamento" not in per_sez:
        x.mancanti.append(Errore("ALLEGATO_OBBLIGATORIO_MANCANTE", "quadro[EG].Testamento", "copia del testamento (rigo EG2) "
                                 "obbligatoria con la devoluzione per testamento", _fa(el + "/Testamento")))
    if x.valore_passivita and "DocumentiPassivita" not in per_sez:
        x.mancanti.append(Errore("ALLEGATO_OBBLIGATORIO_MANCANTE", "quadro[EG].DocumentiPassivita", "documenti "
                                 "comprovanti le passivita' (rigo EG5) obbligatori in presenza del quadro ED",
                                 _fa(el + "/DocumentiPassivita") + "; " + FO.fonte_fasc1(38, "passivita'")))
    if "DichSost" in per_sez and "DocumentiIdentita" not in per_sez:
        x.mancanti.append(Errore("ALLEGATO_OBBLIGATORIO_MANCANTE", "quadro[EG].DocumentiIdentita", "documento "
                                 "d'identita' (rigo EG7) obbligatorio in presenza del rigo EG1",
                                 _fa(el + "/DocumentiIdentita")))
    if x.pc_eg:
        # annotazione QuadroEG/PrimaCasa: obbligatorio con agevolazioni P/X/Y/Z per soggetti diversi dal dichiarante;
        # Fascicolo I p. PDF 7: copia del documento d'identita' di chi sottoscrive le sostitutive rese da beneficiari diversi
        if "PrimaCasa" not in per_sez:
            x.mancanti.append(Errore("ALLEGATO_OBBLIGATORIO_MANCANTE", "quadro[EG].PrimaCasa", "richiesta dell'agevolazione "
                                     "prima casa di un beneficiario diverso dal dichiarante: allegare la dichiarazione "
                                     "sostitutiva (rigo EG9)", _fa(el + "/PrimaCasa") + "; " +
                                     FO.fonte_fasc1(52, "Sezione II: richiesta da soggetto diverso dal dichiarante")))
        if "DocumentiIdentita" not in per_sez:
            x.mancanti.append(Errore("ALLEGATO_OBBLIGATORIO_MANCANTE", "quadro[EG].DocumentiIdentita", "documento d'identita' "
                                     "di chi sottoscrive la richiesta prima casa (rigo EG7)",
                                     FO.fonte_fasc1(7, "copia del documento d'identita' di chi sottoscrive le dichiarazioni "
                                                    "sostitutive rese da beneficiari diversi dal dichiarante")))
    if x.ra_eg:
        # annotazione QuadroEG/RiduzioniImposteSuccessione: obbligatorio con riduzioni L, Q, 1-5 per soggetti diversi dal
        # dichiarante; Fascicolo I p. PDF 50: rigo EG11 (L, Q, 1-5) e copia del documento d'identita' di chi sottoscrive
        if "RiduzioniImposteSuccessione" not in per_sez:
            x.mancanti.append(Errore("ALLEGATO_OBBLIGATORIO_MANCANTE", "quadro[EG].RiduzioniImposteSuccessione", "richiesta "
                                     "di riduzioni (L, Q, art. 25 c. 1) di un beneficiario diverso dal dichiarante: allegare "
                                     "la dichiarazione sostitutiva (rigo EG11)", _fa(el + "/RiduzioniImposteSuccessione") +
                                     "; " + FO.fonte_fasc1(50, "rigo EG11")))
        if "DocumentiIdentita" not in per_sez:
            x.mancanti.append(Errore("ALLEGATO_OBBLIGATORIO_MANCANTE", "quadro[EG].DocumentiIdentita", "documento d'identita' "
                                     "di chi sottoscrive la richiesta di riduzioni (rigo EG7)",
                                     FO.fonte_fasc1(50, "dichiarazioni sostitutive rese da soggetti diversi dal dichiarante")))
    if x.ra_altro and "Altro" not in per_sez:
        x.mancanti.append(Errore("ALLEGATO_OBBLIGATORIO_MANCANTE", "quadro[EG].Altro", "codice R (fondi rustici): "
                                 "l'attestazione dell'ufficio regionale va allegata alla dichiarazione nel quadro EG; la "
                                 "documentazione senza rigo specifico va nel rigo EG8 'Altro'",
                                 FO.fonte_fasc1(63, "codice R") + "; " + FO.fonte_fasc1(50, "rigo EG8")))
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


# ============================================================================================== EI
def _flag(v) -> bool:
    return v is True or str(v).strip().lower() in ("1", "si", "true")


def _estremi_ei(x, b: dict, campo: str, voci, spec, base: str, fonte: str) -> list[dict]:
    """Estremi di trascrizione o registrazione di un immobile: ``spec`` = [(chiave, elemento XSD, tipo)], massimo 3."""
    from .esporta import codice_enum   # import locale: esporta importa questo modulo
    out = []
    if voci in (None, ""):
        return out
    if not isinstance(voci, list):
        x.err("VALORE_NON_VALIDO", f"{base}.{campo}", "attesa una lista di estremi", fonte)
        return out
    if len(voci) > 3:
        x.ns.append(f"{base}.{campo}: piu' di tre estremi (campo Continuazione, moduli successivi) non supportato")
        return out
    for i, v in enumerate(voci):
        perc = f"{base}.{campo}[{i}]"
        if not isinstance(v, dict) or set(v) - {k for k, _, _ in spec}:
            x.err("VALORE_NON_VALIDO", perc, f"attesi solo i campi {[k for k, _, _ in spec]}", fonte)
            continue
        riga, ok = {}, True
        for chiave, elemento, tipo in spec:
            val = v.get(chiave)
            try:
                if val in (None, ""):
                    raise F.ValoreXml("dato obbligatorio")
                if tipo.startswith("enum:"):
                    riga[elemento] = codice_enum(str(val), tipo[5:])
                elif tipo == "anno":
                    if not re.fullmatch(r"(18|19|20)[0-9]{2}", str(val)) or int(val) > x.oggi.year:
                        raise F.ValoreXml(f"{val!r}: anno aaaa tra 1800 e l'anno corrente")
                    riga[elemento] = str(val)
                else:   # numerico con massimo di cifre
                    massimo = int(tipo)
                    if not str(val).isdigit() or len(str(val)) > massimo:
                        raise F.ValoreXml(f"{val!r}: solo cifre, massimo {massimo}")
                    riga[elemento] = str(val)
            except F.ValoreXml as e:
                x.err("DATO_MANCANTE" if val in (None, "") else "VALORE_NON_VALIDO", f"{perc}.{chiave}", str(e), fonte)
                ok = False
        if ok:
            out.append(riga)
    return out


def quadro_ei(x, fr: dict) -> dict | None:
    """Quadro EI (dichiarazione sostitutiva per la voltura): generato dai beni EB/EC con «discordanza dati intestatario» o
    «passaggi senza atti legali» (Fascicolo I p. 54). Piu' di tre estremi per immobile (Continuazione): non supportato."""
    el = "QuadroEI_new/PrimoModulo"
    if not x.ei_beni or fr is None:
        return None
    pres_fr = fr.get("Presentatore") or {}
    pres = dict(pres_fr.get("DatiAnagrafici") or {})
    pres["CodiceFiscale"] = pres_fr.get("CodiceFiscale")
    pres["CodiceCarica"] = pres_fr.get("CodiceCarica")
    if pres_fr.get("CodiceFiscaleRappresentato"):
        pres["CodiceFiscaleRappresentato"] = pres_fr["CodiceFiscaleRappresentato"]
    primo: dict = {"Presentatore": pres}
    if any(e["passaggi"] for e in x.ei_beni):
        primo["SezioneI_AttiLegali"] = {"FlagAttiLegali": "1", "FirmaDichiarante": "1"}
    sezioni = []
    for e in sorted((e for e in x.ei_beni if e["discordanza"]), key=lambda e: e["id"]):
        b, base = e["bene"], f"beni[{e['id']}]"
        fonte = FO.fonte_annotazione(el + "/SezioneII_DatiIntestatario/EstremiTrascrizione") + "; " + FO.fonte_fasc1(54, "Sezione II")
        sup_tr = SUP.attr(x.d, "beni", b, "estremi_trascrizione")
        sup_rg = SUP.attr(x.d, "beni", b, "estremi_registrazione")
        x.usa(b, "estremi_trascrizione")
        x.usa(b, "estremi_registrazione")
        tr = _estremi_ei(x, b, "estremi_trascrizione", sup_tr, [
            ("ufficio", "UfficioTrascrizione", "enum:UfficioDiTrascrizione_Type"),
            ("registro_particolare", "RegistroParticolare", "6"), ("anno", "Anno", "anno")], base, fonte)
        rg = _estremi_ei(x, b, "estremi_registrazione", sup_rg, [
            ("ufficio", "UfficioTerritoriale", "enum:UfficioDiRegistrazione_Type"), ("anno", "Anno", "anno"),
            ("volume", "Volume", "5"), ("numero", "Numero", "6")], base, fonte)
        if sup_tr in (None, "", []) and sup_rg in (None, "", []):
            x.err("DATO_MANCANTE", base + ".estremi_trascrizione", "con la discordanza dati intestatario indicare almeno una "
                  "trascrizione o una registrazione", fonte)
        luogo = e["luogo"]
        it = luogo.get("Italia", luogo)
        imm = {"TipoCatasto": "T" if e["quadro"] == "EB" else "U",
               "Luogo": {"Provincia": luogo["Provincia"], "ComuneAmministrativo": it["ComuneAmministrativo"],
                         "CodiceComune": it["CodiceComune"], "CodiceComuneAmministrativo": it["CodiceComuneAmministrativo"]},
               "DatiCatastali": e["cat"]}
        if e["quadro"] == "EC" and e.get("sezione"):
            imm["SezioneUrbana"] = e["sezione"]
        sez = {"Immobile": imm}
        if tr:
            sez["EstremiTrascrizione"] = tr
        if rg:
            sez["EstremiRegistrazione"] = rg
        sez["FirmaDichiarante"] = "1"
        sezioni.append(sez)
    if sezioni:
        primo["SezioneII_DatiIntestatario"] = sezioni[0]
    out = {"PrimoModulo": primo}
    if len(sezioni) > 1:
        # nei moduli successivi al primo la sezione non prevede la firma (XSD: Modulo/SezioneII_DatiIntestatario)
        out["Modulo"] = [{"SezioneII_DatiIntestatario": {k: v for k, v in s.items() if k != "FirmaDichiarante"}} for s in sezioni[1:]]
    return out


# ============================================================================================== EH
def _eh_testamento(x) -> dict:
    """EH, rigo testamento: assenza oppure presenza con gli estremi di registrazione (EH4 = frontespizio)."""
    if SUP.dich(x.d, "devoluzione_per_testamento") is not True:
        return {"FlagAssenzaTestamento": "1"}
    pres = {"FlagTestamento": "1"}
    if x.test_reg:
        pres["RegistrazioneTestamento"] = [dict(x.test_reg)]
    return {"PresenzaTestamento": pres}


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
        "Testamento": _eh_testamento(x),
        "Interdetti": {"FlagAssenzaInterdetti": "1"},
        "Rinuncia": {"FlagAssenzaRinuncia": "1"},
        "FirmaDichiarante": "1",
    }
    for chiave, elenco, flag in (("Navi", x.eh_navi, "FlagNavi"), ("Aeromobili", x.eh_aeromobili, "FlagAeromobili")):
        if len(elenco) > 1:
            x.ns.append(f"quadro EH: {len(elenco)} {chiave.lower()} nel quadro {'EQ' if chiave == 'Navi' else 'EP'}: la sezione "
                        f"{chiave} del quadro EH ne ammette una sola nel primo modulo, il secondo modulo non e' supportato")
        elif elenco:
            sez[chiave] = {flag: "1", **elenco[0]}
    if x.quadro_bene and "EN" in set(x.quadro_bene.values()):
        dd, cc = SUP.dich(x.d, "azienda_data_deposito"), SUP.dich(x.d, "azienda_camera_commercio")
        az = {"FlagAzienda": "1"}
        fonte = FO.fonte_annotazione("QuadroEH/PrimoModulo/SezioneI_DichSost/Aziende")
        for chiave, val, conv in (("DataDeposito", dd, lambda v: F.data(v, non_oltre=x.oggi)), ("CameraCommercio", cc, lambda v: F.an(v, 35))):
            nome = "azienda_data_deposito" if chiave == "DataDeposito" else "azienda_camera_commercio"
            if val in (None, ""):
                x.err("DATO_MANCANTE", "opzioni.telematico.dichiarazione." + nome, "dato obbligatorio con il quadro EN (rigo EH9)", fonte)
                continue
            try:
                az[chiave] = conv(val)
            except F.ValoreXml as e:
                x.err("VALORE_NON_VALIDO", "opzioni.telematico.dichiarazione." + nome, str(e), fonte)
        sez["Aziende"] = az
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
    sez2 = PC.sezione_eh(x)
    if sez2:
        eh["PrimoModulo"]["SezioneII_AgevPrimaCasa"] = sez2
    elif x.pc_dichiarante is None and SUP.dich(x.d, "prima_casa") is not None:
        x.err("DATI_INCOERENTI", "opzioni.telematico.dichiarazione.prima_casa", "la Sezione II del quadro EH puo' essere "
              "compilata solo con l'agevolazione P richiesta dal dichiarante", _fa("QuadroEH/PrimoModulo/SezioneII_AgevPrimaCasa"))
    sez4 = RA.sezione_eh(x)
    if sez4:
        eh["PrimoModulo"]["SezioneIV_AltreAgevRiduz"] = sez4
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

