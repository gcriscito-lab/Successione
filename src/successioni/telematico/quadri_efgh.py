"""Quadri EF (liquidazione), EG (documenti e allegati) ed EH (dichiarazioni sostitutive) - perimetro di base.

Usato da ``esporta._Export`` (stessa istanza ``x``: errori, non supportati, mappa, dati gia' validati dei quadri
EA/EB/EC/ER/ED). Ogni regola cita la fonte: annotazione dell'elemento XSD (fornituraSUC13_v1.xsd, SUC13_20250702) o
istruzioni ``Succ_FASCICOLO_I_Nov_23.pdf`` (pagina PDF = pagina stampata). Nessuna regola dalla memoria.

PERIMETRO (il resto e' ``non_supportato`` oppure ``quadri_mancanti`` con il motivo):

- EF: successioni aperte dal 2006-10-03 (misura fissa 168 fino al 2013, 200 dal 2014; sezione V-bis solo dal 2025-01-01, vedi docs/regole/ef_successioni_storiche.md), prima dichiarazione o sostitutiva 1/2, immobili anche in piu' comuni (circoscrizioni da ``conservatorie.py``, col componente di controllo configurato), senza agevolazioni/riduzioni
  salvo la prima casa (codici P, X, Z: rigo EF4 e Sezione II di EH, vedi ``prima_casa.py``); Sezioni I (ipotecaria 2%), II (catastale 1%), III (tassa ipotecaria 120 euro per circoscrizione), IV (bollo
  85 euro per circoscrizione), V-bis (imposta di successione da ``calcolo.calcola_da_xml`` sul file dichiarato),
  totale EF19. Non coperti: agevolazioni (G, M, Y, Z senza P, trust), regola dei valori fiscali dei soli terreni
  (Fascicolo I p. 40), (imposta proporzionale inferiore alla fissa: ora coperta, vedi sotto),
  attestazione/copia conforme, crediti
  d'imposta, sostitutive con rimborso o tardive con imposta aggiuntiva, sanzioni e interessi, rateazione.
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

from .. import valori as V
from ..schema import Errore
from . import fonti as FO
from . import formati as F
from . import agevolazioni as AG
from . import prima_casa as PC
from . import riduzioni_art25 as RA
from . import conservatorie as CO
from . import pagamenti as PG
from . import sostitutiva as SO
from . import supplemento as SUP

DEC_2025 = date(2025, 1, 1)
DEC_2014 = date(2014, 1, 1)
DEC_2006 = date(2006, 10, 3)
#: imposta fissa ipotecaria/catastale per successioni aperte dal 2014-01-01 (Fascicolo I p. 39; annotazioni EF)
IMPOSTA_FISSA = AG.IMPOSTA_FISSA
#: gradi di parentela degli enti esclusi dalle basi EF1/EF9 e dai righi EF2/EF3 (annotazioni EF: «'Grado di parentela' uguale a
#: '36', '37', '38' o '39'»); 36 = Stato, 37 = regioni, province, comuni (Fascicolo I pp. 44-45)
GRADI_ENTI = ("36", "37", "38", "39")
#: per le successioni aperte tra il 2006-10-03 e il 2013-12-31 (Fascicolo I p. 39; annotazioni XSD «168 ... 200 dal 01/01/2014»)
IMPOSTA_FISSA_2006_2013 = 168


def imposta_fissa(data_decesso: date) -> int:
    """Misura fissa dell'imposta ipotecaria e catastale secondo la data di apertura della successione."""
    return IMPOSTA_FISSA if data_decesso >= DEC_2014 else IMPOSTA_FISSA_2006_2013
#: aliquote attuali (Fascicolo I p. 40 rigo EF1 col. 2: 2 per cento; p. 43 rigo EF9 col. 2: 1 per cento)
ALIQUOTA_IPOTECARIA = Decimal("0.02")
ALIQUOTA_CATASTALE = Decimal("0.01")
#: tassa per i servizi ipotecari e catastali per circoscrizione (Fascicolo I p. 44 rigo EF15 col. 2; annotazione
#: SezioneIII_TassaIpotecaria/Circoscrizioni_Imposta)
TASSA_CIRCOSCRIZIONE = 120
TASSA_CIRCOSCRIZIONE_SENZA_VOLTURE = 65   # Fascicolo I p. PDF 45, rigo EF15 col. 2 (casi particolari, cariche 5, 6, 9)
#: imposta di bollo per circoscrizione (Fascicolo I p. 45-46 rigo EF16; annotazione SezioneIV/Circoscrizioni_Imposta)
BOLLO_CIRCOSCRIZIONE = 85
#: attestazione di avvenuta presentazione (copia conforme) chiesta in dichiarazione: rigo EF16 col. 1, «32€ (16€ per la richiesta e
#: 16€ per una attestazione)», sommati anche in col. 3 (Fascicolo I pp. PDF 45-46; annotazioni ImpostaBollo_CopiaConforme e
#: Circoscrizioni_Imposta); rigo EF18, tributi speciali, «un importo di 16 euro» (p. PDF 46; annotazione CopiaConforme_Importo)
BOLLO_ATTESTAZIONE = 32
TRIBUTI_SPECIALI_ATTESTAZIONE = 16

#: righi del quadro EG nell'ordine dello schema; il numero di rigo e' quello del modello (fonti/Modello, quadro EG:
#: EG1 ... EG11) e coincide con l'ordine degli elementi in QuadroEG
SEZIONI_EG = ("DichSost", "Testamento", "Inventario", "CertificazioneImpostaVersataEstero", "DocumentiPassivita",
              "AlberoGenealogico", "DocumentiIdentita", "Altro", "PrimaCasa", "AgevolazioniImposteIpocatastali",
              "RiduzioniImposteSuccessione")
EG_SUPPORTATE = {"DichSost", "Testamento", "Inventario", "DocumentiPassivita", "AlberoGenealogico", "DocumentiIdentita", "Altro",
                 "PrimaCasa", "AgevolazioniImposteIpocatastali", "RiduzioniImposteSuccessione",
                 "CertificazioneImpostaVersataEstero"}


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


def _somma_in_euro(x, somma: Decimal, elemento: str, descrizione: str) -> Decimal:
    """Somma dei 'Valore quota' (QuotaValore, cm:DatoVP_Type al centesimo) riportata in un campo in euro interi
    (cm:DatoNP_Type) del quadro EF: arrotondata all'unita' di euro con la regola delle annotazioni EF («per difetto se la
    frazione e' inferiore a 50 centesimi e per eccesso se non inferiore»). I centesimi nascono solo dall'arrotondamento
    dei singoli valori quota (quote non esatte al centesimo), ammesso entro la tolleranza dell'annotazione QuotaValore
    (1% del valore del bene, al massimo 100 euro). Riscontri: file originale accettato dall'Agenzia (104.903,97 -> 104.904)
    e controllo ufficiale SUC13 2.3.1 locale (docs/regole/dubbio_arrotondamento.md §7)."""
    intero = Decimal(arrotonda_euro(somma))
    if intero != somma:
        x.avv("ARROTONDAMENTO_SOMMA_VALORI_QUOTA", "quadro[EF]",
              f"somma dei 'Valore quota' degli {descrizione} {F.euro_centesimi(somma)} arrotondata a {int(intero)} euro "
              "(campo in euro interi)", _fa(elemento) + "; " + _fa("QuadroEF/SezioneI_ImpostaIpotecaria/ImpostaProporzionale/"
                                                                   "ImpostaProporzionale_Imposta"))
    return intero


# ============================================================================================== EF
def quadro_ef(x, xml_pre: bytes | None) -> dict | None:
    """Quadro EF. ``xml_pre``: dichiarazione gia' serializzata senza EF (fonte dei dati per il calcolo V-bis)."""
    el = "QuadroEF"
    dd = x.data_decesso
    if dd is None:
        return None
    # gli immobili esteri (provincia EE) non entrano nelle basi EF1/EF9 ne' nelle circoscrizioni (annotazioni XSD di QuadroEF)
    tutti = [r for r in x.righe_dev.values() if r["quadro"] in ("EB", "EC", "EL", "EM") and not r.get("estero")]
    # «non deve essere indicato il valore delle quote relative agli immobili devoluti a uno dei soggetti 36-39» (EF1, EF9):
    # le righe degli enti non entrano nelle basi proporzionali. Le circoscrizioni hanno invece esclusioni proprie (EF15: solo
    # grado 36; EF16: gradi 36 e 37), calcolate sotto da ``tutti`` (annotazioni Circoscrizioni_Numero; Fascicolo I pp. 44-45)
    immobili = [r for r in tutti if x.grado_ea.get(r["persona_id"]) not in GRADI_ENTI]
    attestazione = bool(getattr(x, "richiesta_attestazione", None))
    # annotazione XSD di QuadroEF: obbligatorio con EA e almeno un rigo EB, EC, EL, EM, senza considerare i righi esteri, quelli
    # a soggetti con grado 36, quelli a soggetti 37, 38, 39 con sostitutiva = 2 e quelli con agevolazione C, D, E o H con
    # sostitutiva = 2. Con la copia conforme le sezioni IV e V sono obbligatorie (annotazioni di SezioneIV_ImpostaBollo e
    # SezioneV_TributiSpeciali: «obbligatorio in presenza del campo Copia conforme»)
    sost2 = bool(getattr(x, "sost", None)) and x.sost.codice == "2"
    rilevanti = [r for r in tutti if x.grado_ea.get(r["persona_id"]) != "36" and not (
        sost2 and (x.grado_ea.get(r["persona_id"]) in ("37", "38", "39") or r.get("agevolazione") in ("C", "D", "E", "H")))]
    obbligatorio = dd >= DEC_2025 or (bool(x.ea) and bool(rilevanti)) or attestazione
    if not obbligatorio:
        return None
    motivi: list[str] = []
    # Prima del 2025 il quadro EF resta (obbligatorio con EA e immobili) ma senza la sezione V-bis: l'imposta di successione e'
    # liquidata dall'ufficio (Fascicolo I pp. PDF 9 e 39; annotazioni XSD di SezioneVBis_ImpostaSuccessione).
    if dd < DEC_2006:
        motivi.append("successione aperta prima del 2006-10-03: misura fissa e regole ipocatastali non indicate dalle fonti "
                      "(Fascicolo I p. 39 distingue solo i periodi dal 2006-10-03 e dal 2014-01-01)")
    fissa = imposta_fissa(dd) if dd >= DEC_2006 else IMPOSTA_FISSA_2006_2013
    if dd < DEC_2025:
        # tempistica di pagamento e rateazione sono campi di ImpostaCalcolata (V-bis), assente prima del 2025: se indicati non
        # finiscono nel file, quindi lo si dice (nessuna perdita silenziosa)
        ignorati = [k for k in ("tempistica_pagamento", "pagamento_rateale", "acconto") if SUP.dich(x.d, k) not in (None, "", False)]
        if ignorati:
            x.avv("DATO_NON_APPLICABILE_PRIMA_DEL_2025", "opzioni.telematico.dichiarazione",
                  f"successione aperta prima del 2025-01-01: {', '.join(ignorati)} riguardano l'imposta di successione autoliquidata "
                  "(sezione V-bis, assente per queste successioni) e non vengono esportati",
                  _fa("QuadroEF/SezioneVBis_ImpostaSuccessione") + "; " + FO.fonte_fasc1(39, "quadro EF"))
    ef: dict = {}
    da_versare = Decimal(0)
    # circoscrizioni (EF15, EF16): solo immobili del catasto ordinario (quadri EB, EC), senza oneri reali (codice diritto 10,
    # che qui blocca comunque il quadro) e senza i beni con agevolazione H (annotazioni Circoscrizioni_Numero: «i beni in cui e'
    # presente l'agevolazione H»; Fascicolo I pp. 44-46); per i tavolari il controllo ufficiale SUC13 2.3.1 (locale, 2026-11-03)
    # individua 0 circoscrizioni.
    beni_h = {r["bene_id"] for r in tutti if r.get("agevolazione") == "H"}
    base_circ = [r for r in tutti if r["quadro"] in ("EB", "EC") and r["diritto"] != "10" and r["bene_id"] not in beni_h]
    # EF15 (Sezione III): righi con grado di parentela diverso da 36 (annotazione SezioneIII/Circoscrizioni_Numero; Fascicolo I
    # p. 44: «circoscrizioni in cui sono compresi solo ... immobili devoluti allo Stato, codice 36»)
    righe_ef15 = [r for r in base_circ if x.grado_ea.get(r["persona_id"]) != "36"]
    # EF16 (Sezione IV): grado diverso da 36 e 37 e agevolazioni diverse da C, M, G, E (annotazione SezioneIV/Circoscrizioni_Numero;
    # Fascicolo I pp. 45-46). Esclusione per rigo come nell'annotazione XSD.
    righe_ef16 = [r for r in base_circ if x.grado_ea.get(r["persona_id"]) not in ("36", "37")
                  and r.get("agevolazione") not in AG.FUORI_CIRCOSCRIZIONI_BOLLO]
    if (immobili or righe_ef15) and not motivi:
        # prima casa (docs/regole/prima_casa.md): i beni con P/X/Z escono dai righi EF1 ed EF9 (annotazioni
        # QuadroEF/SezioneI_ImpostaIpotecaria/ImpostaProporzionale e SezioneII_ImpostaCatastale/ImpostaProporzionale:
        # «l'agevolazione prima casa si estende a tutti i beneficiari ... in relazione a quel bene») ed entrano nel rigo EF4
        agevolati = [r for r in immobili if r["bene_id"] in x.pc_beni]
        # altre agevolazioni (agevolazioni.py; Fascicolo I p. PDF 57): C, D, E, H esenti da I e C; G ed M a imposta ipotecaria
        # fissa (EF2, EF3) e catastale esente; A ed N restano nella base proporzionale. M si estende a tutti i beneficiari del bene
        beni_m = AG.beni_con_m(x)
        fuori_ag = [r for r in immobili if r["bene_id"] not in x.pc_beni and
                    (r["bene_id"] in beni_m or r.get("agevolazione") in AG.FUORI_BASE_PROPORZIONALE)]
        immobili_prop = [r for r in immobili if r["bene_id"] not in x.pc_beni and r not in fuori_ag]
        riga_g = AG.sezione_g(x, immobili)
        righe_m = [r for r in immobili if r["bene_id"] in beni_m and r["bene_id"] not in x.pc_beni]
        valore_m = sum((r["quota_valore"] for r in righe_m), Decimal(0))
        if riga_g and Decimal(riga_g["valore"]) != Decimal(riga_g["valore"]).to_integral_value():
            motivi.append("somma dei 'Valore quota' degli immobili con agevolazione G non intera: arrotondamento non indicato dalle fonti")
        if valore_m != valore_m.to_integral_value():
            motivi.append(f"somma dei 'Valore quota' degli immobili con agevolazione M {valore_m} non intera: arrotondamento "
                          "non indicato dalle fonti")
        imponibile = sum((r["quota_valore"] for r in immobili_prop), Decimal(0))
        valore_pc = sum((r["quota_valore"] for r in agevolati), Decimal(0))
        n_pc = x.pc_numero
        if agevolati and n_pc == 0:
            motivi.append("immobili con agevolazione prima casa senza alcun codice P: il numero di immobili del rigo EF4 "
                          "(solo P, o Z in assenza di P) non e' determinabile")
        # somme dei 'Valore quota' (DatoVP, al centesimo) nei campi in euro interi (cm:DatoNP_Type) EF1/EF9 col. 1 ed EF4 col. 2:
        # arrotondate all'unita' di euro (docs/regole/dubbio_arrotondamento.md §7)
        valore_pc = _somma_in_euro(x, valore_pc, el + "/SezioneI_ImpostaIpotecaria/PrimaCasa/AgevolazionePX_Valore",
                                   "immobili prima casa (rigo EF4 col. 2)")
        if any(r["diritto"] == "10" for r in tutti):
            motivi.append("immobili gravati da oneri reali (codice diritto 10): esclusi dalle circoscrizioni "
                          "(Fascicolo I p. 44), caso non coperto")
        # soli terreni non edificabili, senza agevolazioni ne' riduzioni, senza fabbricati: regola dei valori fiscali
        # (annotazioni XSD ImpostaProporzionale_Imposta di EF1 ed EF9; Fascicolo I pp. PDF 40 e 43)
        solo_terreni = (bool(immobili) and not any(r["quadro"] in ("EC", "EM") for r in immobili)
                        and all(r["quadro"] == "EB" for r in immobili))
        vf = None
        if solo_terreni:
            beni_ids = sorted({r["bene_id"] for r in immobili})          # una riga di devoluzione per beneficiario: ogni bene una volta
            info = [x.terreni_vf.get(b) for b in beni_ids]
            non_edif = all(i and i["tip"] == "3" for i in info)
            liberi = all(not r.get("agevolazione") and not r.get("riduzione") for r in immobili)
            if non_edif and liberi:
                rd_mancanti = [b for b, i in zip(beni_ids, info) if i["rd"] is None]
                if rd_mancanti:
                    motivi.append(f"soli terreni non edificabili: reddito dominicale mancante per {sorted(set(rd_mancanti))}: "
                                  "il valore fiscale (reddito x quota del defunto x 112,5) non e' determinabile")
                else:
                    vf = sum((i["rd"] * Decimal(i["quota"].numerator) / Decimal(i["quota"].denominator) for i in info),
                             Decimal(0)) * Decimal("112.5")
            else:
                solo_terreni = False   # terreni edificabili o con agevolazioni: imposta proporzionale ordinaria
        if immobili_prop:
            imponibile = _somma_in_euro(x, imponibile, el + "/SezioneI_ImpostaIpotecaria/ImpostaProporzionale/"
                                        "ImpostaProporzionale_Imponibile", "immobili soggetti a imposta ipotecaria (rigo EF1 col. 1)")
        # EF1: quadri EB, EC, EL, EM (Fascicolo I p. 40). EF9 (catastale): il testo (p. 43) non elenca i quadri; il controllo
        # ufficiale SUC13 2.3.1 eseguito in locale il 2026-11-03 esclude i terreni tavolari (EL) dalla base catastale.
        prop_cat = [r for r in immobili_prop if r["quadro"] != "EL"]
        imponibile_cat = sum((r["quota_valore"] for r in prop_cat), Decimal(0))
        if prop_cat:
            imponibile_cat = _somma_in_euro(x, imponibile_cat, el + "/SezioneII_ImpostaCatastale/ImpostaProporzionale/"
                                            "ImpostaProporzionale_Imponibile", "immobili soggetti a imposta catastale (rigo EF9 col. 1)")
        # imposta = aliquota x «campo precedente» (annotazioni ImpostaProporzionale_Imposta di EF1 ed EF9): l'imponibile intero
        ip = arrotonda_euro(imponibile * ALIQUOTA_IPOTECARIA)
        cat = arrotonda_euro(imponibile_cat * ALIQUOTA_CATASTALE)
        # imposta proporzionale inferiore alla fissa: il Fascicolo I (pp. 40 e 43) parla di «indicare 200 euro» ma il controllo
        # ufficiale SUC13 2.3.1 (prova locale 2026-11-05) respinge 200 nella colonna 2 («valore corretto» = imposta calcolata) e
        # accetta l'annotazione XSD di ImpostaIpotecariaDovuta/ImpostaCatastaleDovuta: colonna 2 = imposta calcolata, minimo di
        # 200 euro solo nel totale dovuto in presenza dei righi EF1/EF9 (vedi sotto)
        # circoscrizioni: EF15 e EF16 con le rispettive esclusioni (righe_ef15, righe_ef16 sopra)
        circoscrizioni = _circoscrizioni(righe_ef15, motivi)
        circoscrizioni_bollo = _circoscrizioni(righe_ef16, motivi)
        if not motivi:
            imp = str(int(imponibile))
            fa1 = _fa(el + "/SezioneI_ImpostaIpotecaria/ImpostaProporzionale/ImpostaProporzionale_Imposta")
            # rigo EF4 (Fascicolo I p. PDF 41, annotazione PrimaCasa_Imposta): numero immobili x 200; EF5/EF11 = proporzionale + EF4
            fissa_pc = fissa * n_pc
            ip = ip if immobili_prop else 0
            cat = cat if prop_cat else 0
            if vf is not None:
                x.vf_terreni = vf
                if vf < ip + cat:
                    # il minore fra valori fiscali e imposte proporzionali: 2/3 all'ipotecaria, 1/3 alla catastale
                    ip, cat = arrotonda_euro(vf * 2 / 3), arrotonda_euro(vf / 3)
                else:
                    ip, cat = max(ip, fissa), max(cat, fissa)
            s1: dict = {}
            if immobili_prop:
                s1["ImpostaProporzionale"] = {"ImpostaProporzionale_Imponibile": imp,
                                              "ImpostaProporzionale_Imposta": str(ip)}
            # EF2/EF3: «168 (se la data di decesso e' ... dal 01/01/2014 ... 200)» (annotazioni AgevolazioneG_Imposta e
            # AgevolazioneM_Imposta; Fascicolo I p. 39): misura fissa per data di apertura
            fissa_g = fissa if riga_g else 0
            fissa_m = fissa if righe_m else 0
            if riga_g:
                s1["AgevolazioneG"] = {"AgevolazioneG_Valore": str(int(riga_g["valore"])), "AgevolazioneG_Imposta": str(fissa_g)}
            if righe_m:
                s1["AgevolazioneM"] = {"AgevolazioneM_Valore": str(int(valore_m)), "AgevolazioneM_Imposta": str(fissa_m)}
            if agevolati:
                s1["PrimaCasa"] = {"PrimaCasa_Numero": str(n_pc), "AgevolazionePX_Valore": str(int(valore_pc)),
                                   "PrimaCasa_Imposta": str(fissa_pc)}
            sost = x.sost
            cred = PG.crediti(x)
            dovuta_ip, dovuta_cat = ip + fissa_pc + fissa_g + fissa_m, cat + fissa_pc
            if immobili_prop and vf is None:
                dovuta_ip = max(dovuta_ip, fissa)      # annotazione XSD ImpostaIpotecariaDovuta
            if prop_cat and vf is None:
                dovuta_cat = max(dovuta_cat, fissa)    # annotazione XSD ImpostaCatastaleDovuta
            s1["ImpostaIpotecariaDovuta"] = str(dovuta_ip)
            # EF8 = EF5 - EF6 (gia' versata) - EF7 (credito), non negativo; EF14 = EF11 - EF12 - EF13 (Fascicolo I pp. PDF 42-44).
            # Con la sostitutiva codice 1 l'importo da versare, se dovuto, non puo' essere inferiore alla misura fissa.
            versata_ip = sost.ipotecaria_versata if sost else 0
            versata_cat = sost.catastale_versata if sost else 0
            cred_ip, cred_cat = (cred.ipotecaria, cred.catastale) if cred else (0, 0)
            for nome, dov, ver, rigo in (("ipotecaria", dovuta_ip, versata_ip, "EF6"), ("catastale", dovuta_cat, versata_cat, "EF12")):
                if ver > dov:
                    # l'eccedenza non si esporta (da versare = 0) e si chiede a rimborso con istanza all'ufficio (Fascicolo I p. PDF 44)
                    x.avv("ECCEDENZA_IMPOSTA_VERSATA_DA_RIMBORSARE", f"opzioni.telematico.dichiarazione.{nome}_versata",
                          f"imposta {nome} gia' versata ({ver}, {rigo}) superiore a quella dovuta ({dov}): eccedenza di {ver - dov} euro "
                          "da chiedere a rimborso all'ufficio (non si indica nel file)", FO.fonte_fasc1(44, "EF14, rimborso"))
            da_ip = int(SO.netto(dovuta_ip - versata_ip, cred_ip))
            # annotazione di EF13: «puo' essere valorizzato solo se EF5 - EF6 - EF7 = 0, non maggiore della differenza EF11 - EF12»
            if cred_cat and dovuta_ip - versata_ip - cred_ip > 0:
                x.err("DATI_INCOERENTI", "opzioni.telematico.dichiarazione.credito_catastale", "il credito per l'imposta catastale "
                      "(EF13) si puo' usare solo dopo aver azzerato l'imposta ipotecaria da versare (EF5 - EF6 - EF7 = 0)",
                      PG.FONTE_CREDITI)
            if cred_cat > dovuta_cat - versata_cat:
                x.err("DATI_INCOERENTI", "opzioni.telematico.dichiarazione.credito_catastale", f"il credito EF13 ({cred_cat}) non puo' "
                      f"superare la differenza EF11 - EF12 ({dovuta_cat - versata_cat})", PG.FONTE_CREDITI)
            da_cat = int(SO.netto(dovuta_cat - versata_cat, cred_cat))
            x._residuo_cat_dopo_crediti = dovuta_cat - versata_cat - cred_cat       # per EF18bis col. 4 (EF11 - EF12 - EF13 = 0)
            if sost and sost.codice == "1":
                da_ip, da_cat = max(da_ip, fissa), max(da_cat, fissa)
            if versata_ip:
                s1["ImpostaIpotecariaVersata"] = str(versata_ip)
            if cred_ip:
                s1["CreditoImposta"] = str(cred_ip)
            if da_ip:
                s1["ImpostaIpotecariaDaVersare"] = str(da_ip)
            if s1.keys() - {"ImpostaIpotecariaDovuta", "ImpostaIpotecariaDaVersare", "ImpostaIpotecariaVersata", "CreditoImposta"}:
                ef["SezioneI_ImpostaIpotecaria"] = s1
            else:
                da_ip = dovuta_ip = 0        # tutti gli immobili esenti (C, D, E, H): nessun rigo dell'imposta ipotecaria
            s2: dict = {}
            if prop_cat:
                s2["ImpostaProporzionale"] = {"ImpostaProporzionale_Imponibile": str(int(imponibile_cat)),
                                              "ImpostaProporzionale_Imposta": str(cat)}
            if agevolati:
                s2["ImpostaCatastaleFissa"] = str(fissa_pc)
            if s2:
                s2["ImpostaCatastaleDovuta"] = str(dovuta_cat)
                if sost and sost.catastale_versata:
                    s2["ImpostaCatastaleVersata"] = str(sost.catastale_versata)
                if cred_cat:
                    s2["CreditoImposta"] = str(cred_cat)
                if da_cat:
                    s2["ImpostaCatastaleDaVersare"] = str(da_cat)
                ef["SezioneII_ImpostaCatastale"] = s2
            else:
                da_cat = dovuta_cat = 0      # nessun immobile soggetto a imposta catastale
                x._residuo_cat_dopo_crediti = 0
                if cred_cat:
                    x.err("DATI_INCOERENTI", "opzioni.telematico.dichiarazione.credito_catastale", "credito EF13 senza imposta "
                          "catastale dovuta", PG.FONTE_CREDITI)
            # codice 2: «il campo non deve essere compilato» (Fascicolo I pp. PDF 45-46); codice 1: solo le circoscrizioni
            # delle nuove trascrizioni (qui un unico comune, quindi al piu' una)
            n = len(circoscrizioni) if circoscrizioni and (not sost or sost.codice == "1") else 0
            nb = len(circoscrizioni_bollo) if circoscrizioni_bollo and (not sost or sost.codice == "1") else 0
            if sost and sost.circoscrizioni_nuove:
                # codice 1: solo le circoscrizioni delle nuove trascrizioni (Fascicolo I pp. PDF 45-46)
                n, nb = min(n, sost.circoscrizioni_nuove), min(nb, sost.circoscrizioni_nuove)
            # «non voler dar corso alle volture» (casi particolari): 65 euro per circoscrizione invece di 120 (Fascicolo I p. PDF 45;
            # controllo ufficiale locale, diagnostico 3076 con 120)
            tassa = TASSA_CIRCOSCRIZIONE_SENZA_VOLTURE if getattr(x, "casi_particolari", None) else TASSA_CIRCOSCRIZIONE
            if n:
                ef["SezioneIII_TassaIpotecaria"] = {"Circoscrizioni_Numero": str(n),
                                                    "Circoscrizioni_Imposta": str(tassa * n)}
            if nb:
                ef["SezioneIV_ImpostaBollo"] = {"Circoscrizioni_Numero": str(nb),
                                               "Circoscrizioni_Imposta": str(BOLLO_CIRCOSCRIZIONE * nb)}
            da_versare += da_ip + da_cat + tassa * n + BOLLO_CIRCOSCRIZIONE * nb
            x._tributi_presenti = {"ipotecaria": bool(da_ip), "catastale": bool(da_cat), "tassa_ipotecaria": bool(n),
                                   "bollo": bool(nb)}
            x.calcoli_ef = {
                "EF1": {"imponibile": imp, "imposta": ip, "fonte": fa1 + "; " + FO.fonte_fasc1(40, "rigo EF1")},
                "EF4": {"numero": n_pc, "valore": str(int(valore_pc)), "imposta": fissa_pc,
                        "fonte": FO.fonte_fasc1(41, "rigo EF4") + "; " + FO.fonte_fasc1(43, "rigo EF10") + "; " +
                        _fa(el + "/SezioneI_ImpostaIpotecaria/PrimaCasa") + "; " + PC.FONTE_SINOTTICO},
                "EF5/EF8": {"importo": ip + fissa_pc, "fonte": FO.fonte_fasc1(41, "rigo EF5") + "; " + FO.fonte_fasc1(42, "EF8")},
                "EF9": {"imponibile": str(int(imponibile_cat)), "imposta": cat, "fonte": FO.fonte_fasc1(43, "rigo EF9")},
                "EF11/EF14": {"importo": cat + fissa_pc, "fonte": FO.fonte_fasc1(44, "righi EF11, EF14")},
                "EF15": {"circoscrizioni": n, "imposta": tassa * n,
                         "fonte": FO.fonte_fasc1(44, "rigo EF15: stesso codice comune -> 1 circoscrizione; 120 euro; escluso "
                                                 "solo il grado 36") + "; " +
                                  _fa(el + "/SezioneIII_TassaIpotecaria/Circoscrizioni_Numero")},
                "EF16": {"circoscrizioni": nb, "imposta": BOLLO_CIRCOSCRIZIONE * nb,
                         "fonte": FO.fonte_fasc1(45, "rigo EF16: 85 euro; esclusi gradi 36, 37 e agevolazioni C, E, M, G")
                         + "; " + FO.fonte_fasc1(46, "col. 3") + "; " + _fa(el + "/SezioneIV_ImpostaBollo/Circoscrizioni_Numero")},
            }
            if not agevolati:
                x.calcoli_ef.pop("EF4")
            if sost:
                x.calcoli_ef["EF6/EF8/EF12/EF14"] = {
                    "codice_sostitutiva": sost.codice, "ipotecaria": {"dovuta": dovuta_ip, "versata": sost.ipotecaria_versata,
                                                                       "da_versare": da_ip},
                    "catastale": {"dovuta": dovuta_cat, "versata": sost.catastale_versata, "da_versare": da_cat},
                    "fonte": SO.FONTE_VERSATE}
    if attestazione and not motivi:
        da_versare += _attestazione(x, ef, motivi)
    cred = PG.crediti(x)
    if cred and not motivi and not ef:
        if cred.ipotecaria or cred.catastale:
            x.err("DATI_INCOERENTI", "opzioni.telematico.dichiarazione.credito_ipotecaria", "credito d'imposta sulle imposte "
                  "ipotecaria/catastale (EF7, EF13) senza imposte ipocatastali dovute", PG.FONTE_CREDITI)
    if cred and dd < DEC_2025 and cred.successione:
        x.err("DATI_INCOERENTI", "opzioni.telematico.dichiarazione.credito_successione", "credito sull'imposta di successione (EF18bis "
              "col. 4): per le successioni aperte prima del 2025 la sezione V-bis non c'e' (imposta liquidata dall'ufficio)",
              PG.FONTE_CREDITI)
    vbis = None
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
    if da_versare and dd < DEC_2025:
        _avviso_tardiva(x, dd)
    if da_versare:
        ef["TotaleDaVersare"] = F.euro_centesimi(da_versare)
    # Sezione VI: sanzioni e interessi DICHIARATI dal professionista (non calcolati). EF19 resta la somma dei tributi; l'importo da
    # versare del frontespizio e' EF19 + EF24 colonne 1 e 2 (annotazione di ImportoDaVersare e componente ufficiale, messaggio 3376)
    presenti = dict(getattr(x, "_tributi_presenti", {}))
    ic = (vbis or {}).get("ImpostaCalcolata") or {}
    presenti["successione"] = bool(ic.get("ImpostaDaVersare")) and ic.get("TempisticaPagamento") == "2"
    if dd >= DEC_2025 and vbis is None:
        presenti["successione"] = True       # V-bis non generata (errore o blocco gia' segnalato): niente errore a cascata
    sez_vi, extra_vi = PG.sezione_vi(x, presenti)
    if sez_vi:
        ef["SezioneVI_SanzioniInteressi"] = sez_vi
    x.totale_da_versare = da_versare + extra_vi
    x.mappa["quadro:EF"] = {"coll": None, "quadro": "EF", "xpath": f"{x.XP_DICH}/suc:QuadroEF",
                            "totale_da_versare": str(da_versare), "calcoli": dict(getattr(x, "calcoli_ef", {}))}
    return ef or None


def _circoscrizioni(righe: list[dict], motivi: list[str]) -> set | None:
    """Circoscrizioni di pubblicita' immobiliare dei righi indicati, individuate dal codice del comune (Fascicolo I p. 44: stesso
    comune -> una circoscrizione; piu' comuni: elenco delle conservatorie, ``conservatorie.py``)."""
    comuni = sorted({r["codice_comune"] for r in righe})
    if len(comuni) <= 1:
        return set(comuni) or None
    circ, perche = CO.circoscrizioni(comuni)
    if circ is None:
        m = f"immobili in piu' comuni {comuni}: {perche} (Fascicolo I p. 44)"
        if m not in motivi:
            motivi.append(m)
    return circ


def _attestazione(x, ef: dict, motivi: list[str]) -> int:
    """Righi EF16 col. 1 e 3 ed EF18 per l'attestazione chiesta in dichiarazione; restituisce l'importo da aggiungere al totale EF19.

    Col. 1 vale zero con devoluzioni a soggetti con grado di parentela 36 (Stato) e nei casi di trust per persone con disabilita'
    grave (annotazione di ImpostaBollo_CopiaConforme; Fascicolo I p. PDF 45): il trust (codice carica 9) non e' coperto e blocca il
    quadro, invece di indicare un importo non verificato."""
    if getattr(x, "codice_carica", None) == "9":
        motivi.append("attestazione di avvenuta presentazione con trust (codice carica 9): l'esenzione dal bollo del rigo EF16 col. 1 "
                      "per i trust a favore di persone con disabilita' grave non e' coperta")
        return 0
    immobili = [r for r in x.righe_dev.values() if r["quadro"] in ("EB", "EC", "EL", "EM")]
    bollo = 0 if any(x.grado_ea.get(r["persona_id"]) == "36" for r in immobili) else BOLLO_ATTESTAZIONE
    s4 = ef.get("SezioneIV_ImpostaBollo") or {}
    circ = int(s4.get("Circoscrizioni_Imposta") or 0)
    nuovo = {"ImpostaBollo_CopiaConforme": str(bollo)}
    if s4.get("Circoscrizioni_Numero"):
        nuovo["Circoscrizioni_Numero"] = s4["Circoscrizioni_Numero"]
    nuovo["Circoscrizioni_Imposta"] = str(circ + bollo)          # col. 3 = 85 x circoscrizioni + col. 1
    ef["SezioneIV_ImpostaBollo"] = nuovo
    # CopiaConforme_Importo e' cm:DatoVP_Type (importo con centesimi, «16,00»), a differenza dei righi interi del quadro
    ef["SezioneV_TributiSpeciali"] = {"CopiaConforme": {"CopiaConforme_Importo": F.euro_centesimi(Decimal(TRIBUTI_SPECIALI_ATTESTAZIONE))}}
    if hasattr(x, "_tributi_presenti"):
        x._tributi_presenti["bollo"] = True
    else:
        x._tributi_presenti = {"ipotecaria": False, "catastale": False, "tassa_ipotecaria": False, "bollo": True}
    calc = getattr(x, "calcoli_ef", None)
    if calc is None:
        x.calcoli_ef = calc = {}
    calc["EF16 col. 1 / EF18 (attestazione)"] = {
        "bollo": bollo, "tributi_speciali": TRIBUTI_SPECIALI_ATTESTAZIONE,
        "fonte": FO.fonte_fasc1(45, "rigo EF16 col. 1: 32 euro") + "; " + FO.fonte_fasc1(46, "col. 3 e rigo EF18: 16 euro")}
    return bollo + TRIBUTI_SPECIALI_ATTESTAZIONE


def _avviso_tardiva(x, dd) -> None:
    """Dichiarazione oltre i dodici mesi dal decesso con imposte ipocatastali da versare: la Sezione VI (sanzioni e interessi del
    ravvedimento) e' facoltativa («puo' essere utilizzata», Fascicolo I p. PDF 49) e non si calcola qui (il tasso legale per anno
    non e' nelle fonti): l'XML non e' bloccato ma l'utente va avvisato."""
    try:
        termine = dd.replace(year=dd.year + 1)
    except ValueError:
        return
    if x.oggi > termine and not PG.sanzioni(x):
        x.avv("EF_TARDIVA_SANZIONI_NON_CALCOLATE", "quadro[EF]",
              f"dichiarazione presentata oltre il termine di dodici mesi dal decesso ({termine.isoformat()}): per le imposte "
              "ipotecarie, catastali e gli altri tributi autoliquidati versati in ritardo possono essere dovuti sanzioni e interessi "
              "(Sezione VI, ravvedimento operoso) che questo programma non calcola: valutarli a parte",
              FO.fonte_fasc1(49, "Sezione VI - sanzioni e interessi"))


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
    sost = x.sost
    versata = sost.successione_versata if sost else 0
    if imposta <= 10:
        if versata:
            x.avv("IMPOSTA_VERSATA_DA_RIMBORSARE", "opzioni.telematico.dichiarazione.successione_versata",
                  f"imposta di successione gia' versata ({versata}) con imposta riliquidata non dovuta: l'eventuale "
                  "rimborso si chiede all'ufficio (Fascicolo I p. PDF 47, col. 3)", SO.FONTE_VERSATE)
        # Fascicolo I p. 47 col. 1: casella barrata se non e' dovuta alcuna imposta (es. importo <= 10 euro);
        # annotazione ImpostaDaVersare: se il risultato e' minore o uguale a 10 euro deve essere uguale a zero
        x.mappa["calcolo:EF18bis"] = {"coll": None, "quadro": "EF", "imposta": imposta, "versione": r.versione,
                                      "xpath": f"{x.XP_DICH}/suc:QuadroEF/suc:SezioneVBis_ImpostaSuccessione"}
        _rateale_senza_importo(x)
        cred0 = PG.crediti(x)
        if cred0 and cred0.successione:
            x.err("DATI_INCOERENTI", "opzioni.telematico.dichiarazione.credito_successione", "credito sull'imposta di successione "
                  "indicato ma imposta non dovuta", PG.FONTE_CREDITI)
        return {"ImpostaNonDovuta": "1"}, 0, []
    # Fascicolo I p.6 (dodici mesi) e p.48 (tempistica 1/2). Le decorrenze particolari,
    # sospensioni e il ravvedimento non sono implementati: non finalizzare una tardiva
    # con imposta di successione dovuta, neppure cambiando semplicemente codice 1 in 2.
    if versata > imposta:
        # il tracciato ammette ImpostaVersata solo fino all'imposta calcolata (annotazione XSD): l'eccedenza non si esporta e si
        # chiede a rimborso con istanza all'ufficio (Fascicolo I p. PDF 47, col. 3; lo scomputo fra tributi non e' definito dallo schema)
        x.avv("ECCEDENZA_IMPOSTA_VERSATA_DA_RIMBORSARE", "opzioni.telematico.dichiarazione.successione_versata",
              f"imposta di successione gia' versata ({versata}) superiore a quella riliquidata ({imposta}): nel file si indica "
              f"{imposta}; l'eccedenza di {versata - imposta} euro va chiesta a rimborso all'ufficio", SO.FONTE_VERSATE)
        versata = imposta
    cred = PG.crediti(x)
    credito = cred.successione if cred else 0
    residuo = imposta - versata
    if credito:
        # annotazioni di EF18bis col. 4: «puo' essere valorizzato solo se EF11 - EF12 - EF13 = 0; non maggiore di EF18bis imposta -
        # imposta gia' versata»
        if getattr(x, "_residuo_cat_dopo_crediti", 0) > 0:
            x.err("DATI_INCOERENTI", "opzioni.telematico.dichiarazione.credito_successione", "il credito sull'imposta di successione "
                  "(EF18bis col. 4) si usa solo dopo aver azzerato l'imposta catastale da versare (EF11 - EF12 - EF13 = 0)",
                  PG.FONTE_CREDITI)
        if credito > residuo:
            x.err("DATI_INCOERENTI", "opzioni.telematico.dichiarazione.credito_successione", f"il credito ({credito}) non puo' "
                  f"superare l'imposta di successione al netto del gia' versato ({residuo})", PG.FONTE_CREDITI)
            credito = residuo
        residuo -= credito
    da_versare_imp = residuo if residuo > 10 else 0   # annotazione ImpostaDaVersare: <= 10 euro -> zero
    if sost and da_versare_imp == 0:
        # nessuna somma ulteriore: niente tardivita', tempistica o sanzioni da valutare
        ic = {"Imposta": str(imposta)}
        if versata:
            ic["ImpostaVersata"] = str(versata)
        if credito:
            ic["CreditoImposta"] = str(credito)
        x.mappa["calcolo:EF18bis"] = {"coll": None, "quadro": "EF", "imposta": imposta, "versione": r.versione,
                                      "xpath": f"{x.XP_DICH}/suc:QuadroEF/suc:SezioneVBis_ImpostaSuccessione"}
        _rateale_senza_importo(x)
        return {"ImpostaCalcolata": ic}, 0, []
    try:
        termine_ordinario = x.data_decesso.replace(year=x.data_decesso.year + 1)
    except ValueError:  # 29 febbraio: nessuna regola di calendario fiscale indovinata
        return None, 0, ["termine di presentazione per decesso il 29 febbraio da verificare: caso non coperto "
                         "(Fascicolo I p.6, p.48)"]
    temp = SUP.dich(x.d, "tempistica_pagamento")
    if x.oggi > termine_ordinario:
        # tardiva: Fascicolo I p. PDF 48 (codice 1 ammesso se si presenta entro i 90 giorni previsti per il pagamento; oltre, codice 2)
        # e p. PDF 49 (sanzioni e interessi del ravvedimento, Sezione VI). Il tasso legale non e' nelle fonti: gli importi li indica il
        # professionista. Senza importi dichiarati per l'imposta di successione la tardiva resta bloccata.
        from datetime import timedelta
        entro_pagamento = x.oggi <= termine_ordinario + timedelta(days=90)
        dichiarate = PG.sanzioni(x).get("successione")
        if temp == "1" and entro_pagamento:
            pass     # pagamento nei termini: nessuna sanzione dovuta sull'imposta di successione
        elif dichiarate is None:
            return None, 0, [f"dichiarazione tardiva (oltre {termine_ordinario.isoformat()}, termine di dodici mesi dal decesso) con imposta "
                             "di successione dovuta: indicare le sanzioni e gli interessi del ravvedimento calcolati dal professionista "
                             "(sanzione_successione / interessi_successione; con importo 0 se non dovuti), oppure presentare entro 90 "
                             "giorni dal termine con tempistica 1 (Fascicolo I pp. PDF 48-49; il tasso legale non e' nelle fonti)"]
        elif temp != "2":
            x.err("DATI_INCOERENTI", "opzioni.telematico.dichiarazione.tempistica_pagamento", "dichiarazione presentata oltre i 90 "
                  "giorni dal termine di presentazione: il pagamento e' contestuale (tempistica 2); le sanzioni sull'imposta di "
                  "successione si indicano solo con la tempistica 2 (annotazione XSD di ImpostaSuccessione)",
                  FO.fonte_fasc1(48, "rigo EF18ter col. 1") + "; " + PG.FONTE_SANZIONI)
            return None, 0, []
    if temp not in ("1", "2"):
        x.err("DATO_MANCANTE", "opzioni.telematico.dichiarazione.tempistica_pagamento", "imposta di successione "
              f"dovuta ({imposta}): indicare la tempistica di pagamento 1 (entro 90 giorni) o 2 (contestuale)",
              _fa(el + "/ImpostaCalcolata/TempisticaPagamento") + "; " + FO.fonte_fasc1(48, "rigo EF18ter col. 1"))
        return None, 0, []
    ic = {"Imposta": str(imposta)}
    if versata:
        ic["ImpostaVersata"] = str(versata)
    if credito:
        ic["CreditoImposta"] = str(credito)
    ic.update({"ImpostaDaVersare": str(da_versare_imp), "TempisticaPagamento": temp})
    acconto = _rateazione(x, da_versare_imp, ic)
    if acconto is None:
        return None, 0, []
    x.mappa["calcolo:EF18bis"] = {"coll": None, "quadro": "EF", "imposta": imposta, "versione": r.versione,
                                  "xpath": f"{x.XP_DICH}/suc:QuadroEF/suc:SezioneVBis_ImpostaSuccessione"}
    # EF19: EF18bis col. 5 solo con pagamento contestuale (codice 2) (Fascicolo I p. 48)
    dovuto_ora = (acconto if "PagamentoRateale" in ic else da_versare_imp) if temp == "2" else 0
    return {"ImpostaCalcolata": ic}, dovuto_ora, []


def _rateazione(x, da_versare: int, ic: dict) -> int | None:
    """Rigo EF18ter col. 2-3 (PagamentoRateale, Acconto). Restituisce l'acconto (0 senza rateazione) oppure ``None`` se i dati
    non sono validi (errori registrati). Regole: annotazioni XSD ``ImpostaCalcolata/PagamentoRateale`` e ``Acconto``; Fascicolo I
    p. PDF 48 (acconto non inferiore al 20% dell'imposta da versare; residuo non inferiore a 1.000 euro; fino a 8 rate
    trimestrali se il residuo non supera 20.000 euro, fino a 12 oltre)."""
    el = "QuadroEF/SezioneVBis_ImpostaSuccessione/ImpostaCalcolata"
    perc = "opzioni.telematico.dichiarazione."
    fonte = _fa(el + "/PagamentoRateale") + "; " + _fa(el + "/Acconto") + "; " + FO.fonte_fasc1(48, "rigo EF18ter col. 2-3")
    rate_in, acc_in = SUP.dich(x.d, "pagamento_rateale"), SUP.dich(x.d, "acconto")
    assente = lambda v: v is None or v is False or v == ""   # 0 non e' «assente»: e' un numero di rate non valido
    if assente(rate_in) and assente(acc_in):
        return 0
    if assente(rate_in):
        x.err("DATO_MANCANTE", perc + "pagamento_rateale", "indicato l'acconto senza il numero di rate: l'acconto "
              "esiste solo con il pagamento rateale", fonte)
        return None
    try:
        rate = int(str(rate_in))
        if isinstance(rate_in, bool) or str(rate) != str(rate_in).strip() or not 1 <= rate <= 12:
            raise ValueError
    except ValueError:
        x.err("VALORE_NON_VALIDO", perc + "pagamento_rateale", f"{rate_in!r}: indicare il numero di rate trimestrali (1-12)", fonte)
        return None
    if acc_in in (None, ""):
        x.err("DATO_MANCANTE", perc + "acconto", "pagamento rateale: l'acconto (almeno il 20% dell'imposta da versare) "
              "e' obbligatorio", fonte)
        return None
    try:
        acc = V.parse_importo(acc_in)
    except V.ValoreNonValido as e:
        x.err("VALORE_NON_VALIDO", perc + "acconto", str(e), fonte)
        return None
    if acc != acc.to_integral_value():
        x.err("VALORE_NON_VALIDO", perc + "acconto", f"{acc}: euro interi (DatoNP_Type)", fonte)
        return None
    acc = int(acc)
    if acc * 5 < da_versare or acc > da_versare:
        x.err("VALORE_NON_VALIDO", perc + "acconto", f"acconto {acc}: deve essere compreso fra il 20% ({da_versare / 5:g}) e "
              f"l'intera imposta da versare ({da_versare})", fonte)
        return None
    residuo = da_versare - acc
    if residuo < 1000:
        x.err("VALORE_NON_VALIDO", perc + "pagamento_rateale", f"il residuo da rateizzare ({residuo}) e' inferiore a 1.000 euro: "
              "rateazione non ammessa", fonte)
        return None
    if residuo <= 20000 and rate > 8:
        x.err("VALORE_NON_VALIDO", perc + "pagamento_rateale", f"con un residuo di {residuo} euro (fino a 20.000) le rate sono al "
              "massimo 8", fonte)
        return None
    ic["PagamentoRateale"], ic["Acconto"] = str(rate), str(acc)
    return acc


def _rateale_senza_importo(x) -> None:
    r, a = SUP.dich(x.d, "pagamento_rateale"), SUP.dich(x.d, "acconto")
    if not ((r is None or r is False or r == "") and a in (None, "")):
        x.err("VALORE_NON_VALIDO", "opzioni.telematico.dichiarazione.pagamento_rateale", "pagamento rateale indicato ma "
              "nessuna imposta di successione da versare", FO.fonte_fasc1(48, "rigo EF18ter"))


# ============================================================================================== EG
def _conformita_allegato(x, perc: str, percorso, sorgente: dict) -> None:
    """Formati ammessi per gli allegati EG: PDF/A-1a, PDF/A-1b, TIF/TIFF (Specifiche_SUC13_20250702 p. 7 par. 2.3; Fascicolo I
    p. PDF 49). Un allegato non conforme (rapporto 'non_conforme', PDF senza PDF/A-1, TIFF fuori specifica) rende il file non
    completo: resta generabile solo come bozza tecnica. Conformita' non accertata da un validatore indipendente: avviso.
    ``sorgente`` puo' portare il rapporto dell'archivio (``rapporto`` con ``validazione.esito``) o ``esito_validazione``."""
    from ..documenti.dimensioni import valuta_conformita_eg
    try:
        c = valuta_conformita_eg(Path(percorso), sorgente.get("rapporto"), sorgente.get("esito_validazione"))
    except Exception as e:          # file illeggibile per la verifica: conformita' non dimostrata, non un falso positivo
        c = {"esito": "non_conforme", "motivo": f"verifica di conformita' non eseguibile: {str(e)[:150]}", "fonte": ""}
    fonte = (c.get("fonte") or "") + "; " + FO.fonte_fasc1(49, "formati PDF/A-1a, PDF/A-1b, TIF/TIFF")
    if c["esito"] == "non_conforme":
        x.mancanti.append(Errore("ALLEGATO_NON_CONFORME", perc, f"allegato non conforme ai formati ammessi: {c['motivo']}. "
                                 "Allegati non conformi causano lo scarto della dichiarazione: file non completo", fonte))
    elif c["esito"] != "conforme":
        x.avv("ALLEGATO_CONFORMITA_NON_DIMOSTRATA", perc, c["motivo"], fonte)


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
            x.ns.append(f"{perc}: rigo EG {sez} non supportato in questa versione")
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
        _conformita_allegato(x, perc, percorso, sorgente if isinstance(sorgente, dict) else {})
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
    if getattr(x, "imposta_estera", None) and "CertificazioneImpostaVersataEstero" not in per_sez:
        # annotazione CertificazioneImpostaVersataEstero: obbligatorio in presenza di imposta versata all'estero in almeno un
        # quadro EB, EC, EO, EP, EQ, ER (e annotazione di ImpostaVersataEstero: «deve essere presente il campo EG4»)
        x.mancanti.append(Errore("ALLEGATO_OBBLIGATORIO_MANCANTE", "quadro[EG].CertificazioneImpostaVersataEstero",
                                 "imposta versata all'estero: allegare la certificazione (rigo EG4)",
                                 _fa(el + "/CertificazioneImpostaVersataEstero") + "; " +
                                 FO.fonte_fasc1(23, "Imposta versata all'estero: certificazione nel rigo EG")))
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
    if getattr(x, "ag_eg10", False):
        # annotazione QuadroEG/AgevolazioniImposteIpocatastali: obbligatorio con C, D, E per soggetti diversi dal dichiarante;
        # Fascicolo I p. PDF 50: rigo EG10 e copia del documento d'identita' di chi sottoscrive
        if "AgevolazioniImposteIpocatastali" not in per_sez:
            x.mancanti.append(Errore("ALLEGATO_OBBLIGATORIO_MANCANTE", "quadro[EG].AgevolazioniImposteIpocatastali",
                                     "richiesta delle agevolazioni C, D o E di un beneficiario diverso dal dichiarante: "
                                     "allegare la dichiarazione sostitutiva (rigo EG10)",
                                     _fa(el + "/AgevolazioniImposteIpocatastali") + "; " + FO.fonte_fasc1(50, "rigo EG10")))
        if "DocumentiIdentita" not in per_sez:
            x.mancanti.append(Errore("ALLEGATO_OBBLIGATORIO_MANCANTE", "quadro[EG].DocumentiIdentita", "documento d'identita' "
                                     "di chi sottoscrive la richiesta di agevolazioni (rigo EG7)",
                                     FO.fonte_fasc1(50, "dichiarazioni sostitutive rese da soggetti diversi dal dichiarante")))
    if getattr(x, "rp_altro", False) and "Altro" not in per_sez:
        x.mancanti.append(Errore("ALLEGATO_OBBLIGATORIO_MANCANTE", "quadro[EG].Altro", "rendita proposta (DOCFA): la volonta' di "
                                 "avvalersene va manifestata con una dichiarazione sostitutiva allegata nel quadro EG, rigo 'Altro'",
                                 _fa(el + "/Altro") + "; " + FO.fonte_fasc1(30, "Determinazione rendita")))
    if PG.crediti(x) and "Altro" not in per_sez:
        x.mancanti.append(Errore("ALLEGATO_OBBLIGATORIO_MANCANTE", "quadro[EG].Altro", "credito d'imposta (Legge 448/1998 art. 7 c. 2, "
                                 "DL 73/2021 art. 64 c. 7): occorre allegare nel quadro EG, rigo EG8 'Altro', la dichiarazione sostitutiva "
                                 "di atto notorio con i requisiti del credito", _fa(el + "/Altro") + "; " + FO.fonte_fasc1(42, "EF7")))
    if getattr(x, "ag_altro", False) and "Altro" not in per_sez:
        x.mancanti.append(Errore("ALLEGATO_OBBLIGATORIO_MANCANTE", "quadro[EG].Altro", "agevolazione H (immobili demoliti o "
                                 "inagibili): la documentazione va allegata nel quadro EG, rigo EG8 'Altro'",
                                 _fa(el + "/Altro") + "; " + FO.fonte_fasc1(50, "dichiarazione sostitutiva per l'agevolazione H")))
    if x.codice_carica in ("5", "6", "7") and "DichSost" not in per_sez:
        x.mancanti.append(Errore("ALLEGATO_OBBLIGATORIO_MANCANTE", "quadro[EG].DichSost", f"codice carica {x.codice_carica} "
                                 "(curatore, amministratore o esecutore testamentario): la dichiarazione sostitutiva di atto notorio "
                                 "sullo stato di famiglia e' obbligatoria (rigo EG1; annotazione XSD «obbligatorio se codice carica = 5 "
                                 "o 6 o 7»; controllo ufficiale 3328)",
                                 _fa(el + "/DichSost") + "; " + FO.fonte_fasc1(49, "dichiarazione sostitutiva stato di famiglia")))
    if getattr(x, "fr_altro", False) and "Altro" not in per_sez:
        x.mancanti.append(Errore("ALLEGATO_OBBLIGATORIO_MANCANTE", "quadro[EG].Altro", "eventi eccezionali (inagibilita' dell'immobile "
                                 "prima casa gia' agevolato): la certificazione e la dichiarazione sostitutiva vanno allegate nel "
                                 "quadro EG, rigo EG8 'Altro' (controllo ufficiale 3323)",
                                 FO.fonte_fasc1(13, "Eventi eccezionali") + "; " + FO.fonte_fasc1(50, "rigo EG8")))
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
    """Estremi di trascrizione o registrazione di un immobile: ``spec`` = [(chiave, elemento XSD, tipo)]. Piu' di tre estremi sono
    ammessi: il chiamante li distribuisce su moduli successivi (campo Continuazione, annotazione XSD di QuadroEI_new)."""
    from .esporta import codice_enum   # import locale: esporta importa questo modulo
    out = []
    if voci in (None, ""):
        return out
    if not isinstance(voci, list):
        x.err("VALORE_NON_VALIDO", f"{base}.{campo}", "attesa una lista di estremi", fonte)
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
    «passaggi senza atti legali» (Fascicolo I p. 54). Piu' di tre estremi per immobile: Continuazione e moduli successivi."""
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
        # fino a tre estremi per tipo in ogni modulo; oltre, «Continuazione» e un modulo successivo con gli ulteriori estremi e SENZA i
        # dati dell'immobile (annotazioni XSD di EstremiTrascrizione, EstremiRegistrazione e Continuazione)
        n_moduli = max(1, -(-max(len(tr), len(rg)) // 3))
        # il controllo ufficiale SUC13 2.3.1 (prova locale 2026-11-05) scarta la continuazione se in un modulo entrambe le liste sono
        # piene e il modulo successivo non contiene almeno un estremo di ciascun tipo (diagnostici 3413/3414): XSD e controllo
        # discordano, vince il controllo
        for k in range(n_moduli - 1):
            piene = len(tr[3 * k:3 * k + 3]) == 3 and len(rg[3 * k:3 * k + 3]) == 3
            if piene and not (tr[3 * k + 3:3 * k + 6] and rg[3 * k + 3:3 * k + 6]):
                x.ns.append(f"{base}: {len(tr)} estremi di trascrizione e {len(rg)} di registrazione: con entrambe le liste piene il "
                            "modulo di continuazione deve contenere almeno un estremo di ciascun tipo (il controllo ufficiale lo "
                            "richiede): caso non esprimibile")
                break
        for k in range(n_moduli):
            sez = {"Immobile": imm} if k == 0 else {}
            if tr[3 * k:3 * k + 3]:
                sez["EstremiTrascrizione"] = tr[3 * k:3 * k + 3]
            if rg[3 * k:3 * k + 3]:
                sez["EstremiRegistrazione"] = rg[3 * k:3 * k + 3]
            if k < n_moduli - 1:
                sez["Continuazione"] = "1"
            if k == 0:
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


def _presentatore_in_ea(x, pres: dict) -> bool:
    cf = pres.get("CodiceFiscale")
    return any((x.soggetti_ea.get(p["id"]) or {}).get("CodiceFiscale") == cf for p in x.ea)


def quadro_eh(x, fr: dict, eg: dict | None) -> dict | None:
    """Quadro EH, Sezione I (dichiarazioni sostitutive) nel caso di base."""
    el = "QuadroEH/PrimoModulo/SezioneI_DichSost"
    if x.codice_carica in ("5", "6", "7"):
        return None  # annotazione QuadroEH: non deve essere presente con codice carica 5, 6, 7
    if x.codice_carica not in ("1", "2", "3", "4", "8") or x.presentatore is None or x.defunto is None:
        return None  # cariche non supportate gia' segnalate nel frontespizio
    pres_fr = fr.get("Presentatore") or {}
    ana_p = pres_fr.get("DatiAnagrafici") or {}
    pres = dict(ana_p)
    pres["CodiceFiscale"] = pres_fr.get("CodiceFiscale")
    pres["CodiceCarica"] = pres_fr.get("CodiceCarica")
    if pres_fr.get("CodiceFiscaleRappresentato"):      # cariche 3 e 4: stesso dato del frontespizio (controllo ufficiale 3214)
        pres["CodiceFiscaleRappresentato"] = pres_fr["CodiceFiscaleRappresentato"]
    dft = x.defunto
    morte = x.codice_carica == "8"
    comune = prov = None
    if not morte:
        comune = x.val("persone", dft, "comune_decesso", lambda v: F.an(v, 50), elemento=el + "/DatiDefunto/Decesso/Comune")
        prov = x.val("persone", dft, "provincia_decesso", lambda v: _pn(v), elemento=el + "/DatiDefunto/Decesso/Provincia")
    elif x.morte_presunta is None:
        return None             # errori gia' segnalati da frontespizio.morte_presunta
    ana_d = (fr.get("DatiDefunto") or {}).get("DatiAnagrafici")
    data_dec = ((fr.get("DatiDefunto") or {}).get("UlterioriDati") or {}).get("DataDecesso")
    stato_civile = (fr.get("DatiDefunto") or {}).get("UlterioriDati", {}).get("StatoCivile")
    sep_unione = _eh_separazione_unione(x, stato_civile)
    interdetti = _eh_interdetti(x)
    reintegri = _eh_reintegri(x)
    eredi, visti = [], set()
    for p in x.ea:
        if x.tipo_ea.get(p["id"]) not in ("1", "2", "3", "4"):
            continue
        sogg = x.soggetti_ea.get(p["id"]) or {}
        if sogg.get("CodiceFiscale") in visti:      # soggetto su piu' righi del quadro EA: un solo rigo nell'elenco EH (controllo 2092)
            continue
        visti.add(sogg.get("CodiceFiscale"))
        voce = {"CodiceFiscale": sogg.get("CodiceFiscale"), "GradoParentela": sogg.get("GradoParentela")}
        voce.update({"Denominazione": sogg["Denominazione"]} if "Denominazione" in sogg else {"DatiAnagrafici": sogg.get("DatiAnagrafici")})
        eredi.append(voce)
    sez: dict = {
        "Presentatore": pres,
        "DatiDefunto": {"DatiAnagrafici": ana_d,
                        **({"MortePresunta": x.morte_presunta} if morte else
                           {"Decesso": {"FlagDeceduto": "1", "DataDecesso": data_dec, "Comune": comune, "Provincia": prov}})},
        # cariche 1 e 2: il dichiarante e' nel quadro EA; cariche 3 e 4 (rappresentante): assenza del dichiarante (controllo 3008)
        # carica 8 (possesso temporaneo dei beni dell'assente): presenza se il dichiarante e' nel quadro EA, assenza altrimenti
        # (controllo ufficiale 3213 con l'assenza di un dichiarante che e' nel quadro EA, 3214 con la presenza di uno che non c'e')
        "Dichiarante": ({"PresenzaDichiarante": "1"} if (x.codice_carica in ("1", "2") or (morte and _presentatore_in_ea(x, pres)))
                        else {"FlagAssenzaDichiarante": "1"}),
        "Testamento": _eh_testamento(x),
        "Interdetti": ({"PresenzaInterdetti": {"FlagInterdetti": "1", **interdetti[0]}} if interdetti
                       else {"FlagAssenzaInterdetti": "1"}),
        "Rinuncia": _eh_rinuncia(x, 0),
        "FirmaDichiarante": "1",
    }
    sez.update(sep_unione)
    if reintegri:
        sez["ReintegroDiritti"] = {"FlagReintegro": "1", "RegistrazioneReintegroDiritti": reintegri[0]}
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
    if eg and ("DocumentiPassivita" in eg or "Inventario" in eg):
        conf = SUP.dich(x.d, "dichiara_copie_conformi")
        if conf is not True:
            x.err("DATO_MANCANTE", "opzioni.telematico.dichiarazione.dichiara_copie_conformi", "con i documenti delle "
                  "passivita' (rigo EG5) o con l'inventario/prospetto (rigo EG3) il dichiarante deve attestare che sono copie "
                  "degli originali (EH, lettera l): confermare esplicitamente (true)",
                  _fa(el + "/FlagPassivita") + "; " + _fa(el + "/FlagProspetto") + "; " + FO.fonte_fasc1(52, "lettera l"))
        if "DocumentiPassivita" in eg:
            sez["FlagPassivita"] = "1"
        if "Inventario" in eg:
            sez["FlagProspetto"] = "1"             # annotazione: obbligatorio in presenza del rigo EG3
    if SUP.dich(x.d, "flag_inventari") is True:
        # lettera l (Fascicolo I p. PDF 52): inventari allegati come copie degli originali; annotazione XSD di FlagInventari:
        # «non deve essere barrata in assenza del rigo EG8» (Altro). Casella del dichiarante, non derivata.
        if eg and "Altro" in eg:
            sez["FlagInventari"] = "1"
        else:
            x.err("DATI_INCOERENTI", "opzioni.telematico.dichiarazione.flag_inventari", "la casella degli inventari (quadro EH) "
                  "richiede almeno un documento nel rigo EG8 «Altro»", _fa(el + "/FlagInventari") + "; " +
                  FO.fonte_fasc1(52, "lettera l"))
    eh: dict = {"PrimoModulo": {"SezioneI_DichSost": sez}}
    sez2 = PC.sezione_eh(x)
    if sez2:
        eh["PrimoModulo"]["SezioneII_AgevPrimaCasa"] = sez2
    elif x.pc_dichiarante is None and SUP.dich(x.d, "prima_casa") is not None:
        x.err("DATI_INCOERENTI", "opzioni.telematico.dichiarazione.prima_casa", "la Sezione II del quadro EH puo' essere "
              "compilata solo con l'agevolazione P richiesta dal dichiarante", _fa("QuadroEH/PrimoModulo/SezioneII_AgevPrimaCasa"))
    sez3, sez3b = PG.sezioni_eh(x)
    if sez3:
        eh["PrimoModulo"]["SezioneIII_CreditoImposta"] = sez3
    sez4 = RA.sezione_eh(x)
    if sez4:
        eh["PrimoModulo"]["SezioneIV_AltreAgevRiduz"] = sez4
    altri = [eredi[i:i + 3] for i in range(3, len(eredi), 3)]
    if altri:
        eh["Modulo"] = [{"SezioneI_DichSost": {"Eredi": blocco}} for blocco in altri]
    if sez3b:
        # secondo rigo di acquisti (tipologia 1 o 2): primo ``Modulo`` successivo, Sezione III (annotazione XSD: almeno 2 righi)
        moduli = eh.setdefault("Modulo", [])
        if not moduli:
            moduli.append({})
        moduli[0]["SezioneIII_CreditoImposta"] = sez3b
    _eh_rinunce_ulteriori(x, eh)
    _eh_moduli_ulteriori(eh, "PresenzaInterdetti", interdetti[1:])
    _eh_moduli_ulteriori(eh, "ReintegroDiritti", reintegri[1:])
    if not morte and None in (comune, prov):
        return None
    x.mappa["quadro:EH"] = {"coll": None, "quadro": "EH", "xpath": f"{x.XP_DICH}/suc:QuadroEH"}
    return eh


def _eh_moduli_ulteriori(eh: dict, chiave: str, elementi: list) -> None:
    """Dal secondo elemento in poi un rigo per modulo (``Modulo/SezioneI_DichSost/<chiave>``, «puo' essere presente solo se nel
    modulo precedente e' presente il rigo corrispondente»): il k-esimo elemento ulteriore va nel k-esimo modulo successivo."""
    for k, el in enumerate(elementi):
        moduli = eh.setdefault("Modulo", [])
        while len(moduli) <= k:
            moduli.append({"SezioneI_DichSost": {}})
        moduli[k]["SezioneI_DichSost"][chiave] = el


def _eh_separazione_unione(x, stato_civile) -> dict:
    """Separazione (lettera g) e unione civile (lettera h) della Sezione I (annotazioni XSD di Separazione e
    FlagNoScioglimentoUnioneCivile; Fascicolo I pp. PDF 18 e 51). Dati: ``separazione_con_colpa`` (stato civile 5) e
    ``no_scioglimento_unione_civile`` (stato civile 7)."""
    el = "QuadroEH/PrimoModulo/SezioneI_DichSost"
    perc = "opzioni.telematico.dichiarazione."
    sep, nus = SUP.dich(x.d, "separazione_con_colpa"), SUP.dich(x.d, "no_scioglimento_unione_civile")
    out: dict = {}
    legge = SUP.dich(x.d, "devoluzione_per_testamento") is not True
    if stato_civile == "5":
        if sep not in (True, False):
            x.err("DATO_MANCANTE", perc + "separazione_con_colpa", "stato civile 5 (separato/a): indicare se e' stata pronunciata "
                  "una sentenza di separazione passata in giudicato per colpa del coniuge superstite o di entrambi (si/no)",
                  _fa(el + "/Separazione") + "; " + FO.fonte_fasc1(51, "lettera g"))
        elif sep:
            out["Separazione"] = {"FlagSeparazione": "1"}
            if legge and any(g == "01" for g in x.grado_ea.values()):
                x.err("REGOLA_SEPARAZIONE", perc + "separazione_con_colpa", "separazione con addebito: con la devoluzione per legge "
                      "il coniuge (grado 01) non puo' essere beneficiario (annotazione XSD di FlagSeparazione; Fascicolo I p. PDF 18)",
                      _fa(el + "/Separazione/FlagSeparazione"))
        else:
            out["Separazione"] = {"FlagAssenzaSeparazione": "1"}
    elif sep not in (None, False):
        x.err("DATI_INCOERENTI", perc + "separazione_con_colpa", "la separazione con colpa si indica solo con stato civile 5 "
              "(separato/a)", _fa(el + "/Separazione/FlagSeparazione"))
    if stato_civile == "7":
        if nus is True:
            out["FlagNoScioglimentoUnioneCivile"] = "1"
        else:
            x.err("DATO_MANCANTE", perc + "no_scioglimento_unione_civile", "stato civile 7 (parte dell'unione civile): confermare "
                  "esplicitamente (true) che non e' stata presentata domanda di scioglimento dell'unione civile",
                  _fa(el + "/FlagNoScioglimentoUnioneCivile") + "; " + FO.fonte_fasc1(51, "lettera h"))
    elif nus not in (None, False):
        x.err("DATI_INCOERENTI", perc + "no_scioglimento_unione_civile", "la dichiarazione sull'unione civile si indica solo con "
              "stato civile 7", _fa(el + "/FlagNoScioglimentoUnioneCivile"))
    return out


def _eh_interdetti(x) -> list[dict]:
    """Soggetti con disabilita' grave o interdetti (lettera e): un rigo EH7 per soggetto con il numero di rigo e di modulo del
    quadro EA e gli estremi del verbale o della sentenza (``certificatore_disabilita``, al massimo 35 caratteri)."""
    el = "QuadroEH/PrimoModulo/SezioneI_DichSost/Interdetti/PresenzaInterdetti"
    out = []
    for p in sorted((p for p in x.ea if x.handicap_ea.get(p["id"])), key=lambda p: x.pos_ea[p["id"]]):
        perc = f"persone[{p['id']}].certificatore_disabilita"
        x.usa(p, "certificatore_disabilita")
        v = SUP.attr(x.d, "persone", p, "certificatore_disabilita")
        if v in (None, ""):
            x.err("DATO_MANCANTE", perc, "persona con disabilita' grave o interdetta: indicare gli estremi del verbale della "
                  "commissione (L. 104/1992 art. 4) o della sentenza di interdizione/inabilitazione (al massimo 35 caratteri)",
                  _fa(el + "/Certificatore") + "; " + FO.fonte_fasc1(51, "lettera e"))
            continue
        try:
            cert = F.an(v, 35)
        except F.ValoreXml as e:
            x.err("VALORE_NON_VALIDO", perc, str(e), _fa(el + "/Certificatore"))
            continue
        m, r = x.pos_ea[p["id"]]
        out.append({"IdentificazioneSoggetto": {"Rigo": str(r), "Modulo": str(m)}, "Certificatore": cert})
    return out


def _eh_reintegri(x) -> list[dict]:
    """Accordi di reintegrazione dei diritti di legittima lesi (lettera d): fino a tre accordi (``reintegro_1`` .. ``reintegro_3``,
    ciascuno con gli estremi di registrazione: ufficio, serie, numero, sottonumero, data)."""
    el = "QuadroEH/PrimoModulo/SezioneI_DichSost/ReintegroDiritti"
    out = []
    for n in (1, 2, 3):
        sez = SUP.dich(x.d, f"reintegro_{n}")
        if sez in (None, ""):
            continue
        reg = x.estremi_registrazione(sez, f"opzioni.telematico.dichiarazione.reintegro_{n}",
                                      _fa(el + "/RegistrazioneReintegroDiritti") + "; " + FO.fonte_fasc1(51, "lettera d"))
        if reg is not None:
            if any(reg == o for o in out):
                x.err("DATI_INCOERENTI", f"opzioni.telematico.dichiarazione.reintegro_{n}", "estremi di registrazione duplicati "
                      "(annotazione XSD: non possono essere presenti righe duplicate)", _fa(el + "/RegistrazioneReintegroDiritti"))
            else:
                out.append(reg)
    return out


def _rinunciatari_ordinati(x) -> list[tuple[str, dict]]:
    """Rinunciatari del quadro EA con i loro estremi, nell'ordine del quadro (modulo, rigo)."""
    return sorted(((pid, reg) for pid, reg in x.rinunce.items()), key=lambda t: x.pos_ea[t[0]])


def _presenza_rinuncia(x, pid: str, reg: dict | None) -> dict | None:
    if reg is None:
        return None                                    # estremi non validi: errore gia' registrato
    m, r = x.pos_ea[pid]
    return {"IdentificazioneSoggetto": {"Rigo": str(r), "Modulo": str(m)}, "RegistrazioneRinuncia": reg}


def _eh_rinuncia(x, indice: int) -> dict:
    """Sezione Rinuncia del primo modulo EH: assenza o prima rinuncia (annotazioni XSD di QuadroEH/.../Rinuncia). Le rinunce
    ulteriori vanno nei moduli successivi (``_eh_rinunce_ulteriori``)."""
    elenco = _rinunciatari_ordinati(x)
    if not elenco:
        return {"FlagAssenzaRinuncia": "1"}
    pres = _presenza_rinuncia(x, *elenco[0])
    return {"PresenzaRinuncia": {"FlagRinuncia": "1", **pres}} if pres else {"FlagAssenzaRinuncia": "1"}


def _eh_rinunce_ulteriori(x, eh: dict) -> None:
    """Dalla seconda rinuncia in poi: un rigo EH8 per modulo (``Modulo/SezioneI_DichSost/PresenzaRinuncia``, che «puo' essere
    presente solo se nel modulo precedente e' presente il rigo relativo alla rinuncia»)."""
    for k, (pid, reg) in enumerate(_rinunciatari_ordinati(x)[1:]):
        pres = _presenza_rinuncia(x, pid, reg)
        if pres is None:
            continue
        moduli = eh.setdefault("Modulo", [])
        while len(moduli) <= k:
            moduli.append({"SezioneI_DichSost": {}})
        moduli[k]["SezioneI_DichSost"]["PresenzaRinuncia"] = pres


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

