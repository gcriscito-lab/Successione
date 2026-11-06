"""Caselle e dati del frontespizio SUC13 oltre a quelli gia' gestiti da ``esporta.py``.

Fonti: XSD ``fornituraSUC13_v1.xsd`` (``FrontespizioSUC_Type``: ``TipoDichiarazione/Devoluzione/LeggeEstera``, ``EventiEccezionali``,
``DataOpzione``; ``Beneficiari/AccettazioneConBeneficioInventario``; ``DatiDefunto/UlterioriDati/ResidenzaEstera``;
``Presentatore/DecorrenzaTerminePresentazione``, ``ResidenteEstero``, ``CodiceFiscaleRappresentato``; ``CasiParticolari``) e Fascicolo I
pp. PDF 13-15 (eventi eccezionali, data opzione art. 24-bis TUIR, beneficiari, residenza estera del defunto, presentatore, casi particolari).

Dati in ``opzioni.telematico.dichiarazione``::

    legge_estera            bool    successione regolata da legge straniera (LeggeEstera)
    eventi_eccezionali      "1"     inagibilita' dell'immobile prima casa gia' agevolato (EventiEccezionali)
    data_opzione            data    decorrenza dell'opzione art. 24-bis TUIR (non inferiore al 2017-01-01, anteriore al decesso)
    beneficio_inventario    bool    accettazione con beneficio d'inventario (Beneficiari)
    residenza_estera_defunto "1"|"2" 1 = mai residente in Italia o residenza ignota; 2 = in parte in Italia e in parte all'estero
    casi_particolari        bool    «non voler dar corso alle volture catastali» (CasiParticolari)
    richiesta_attestazione  bool    richiesta dell'attestazione di avvenuta presentazione, copia conforme (CasiParticolari/CopiaConforme;
                                    Fascicolo I p. PDF 16; effetti sul quadro EF: righi EF16 col. 1 e 3, EF18, pp. PDF 45-46)
    presentatore.data_decorrenza     data    decorrenza del termine di presentazione (non inferiore al decesso)
    presentatore.rappresentato_cf    CF      soggetto rappresentato (cariche 3 e 4 obbligatorio)
    presentatore.residente_estero    {codice_stato, stato, stato_federato, localita, indirizzo}
"""
from __future__ import annotations

from datetime import date

from . import formati as F
from . import fonti as FO
from . import sostitutiva as SO
from . import supplemento as SUP

PERC = "opzioni.telematico.dichiarazione."
FONTE_FASC = "Succ_FASCICOLO_I_Nov_23.pdf pp. PDF 13-15"
CHIAVI_NUOVE = ("legge_estera", "eventi_eccezionali", "data_opzione", "beneficio_inventario", "residenza_estera_defunto",
                "casi_particolari", "richiesta_attestazione")
PRIMO_2017 = date(2017, 1, 1)


def _data(x, chiave: str, valore, fonte: str):
    try:
        return F.data_iso(valore)
    except (F.ValoreXml, ValueError, TypeError) as e:
        x.err("VALORE_NON_VALIDO", PERC + chiave, f"data non valida: {e}", fonte)
        return None


def _bool(x, chiave: str) -> bool | None:
    v = SUP.dich(x.d, chiave)
    if v in (None, False, ""):
        return None
    if v is True:
        return True
    x.err("VALORE_NON_VALIDO", PERC + chiave, "atteso vero o falso", FONTE_FASC)
    return None


def leggi(x, ddec: date | None) -> dict:
    """Legge e valida le caselle. Restituisce i frammenti da inserire nel frontespizio (chiavi: ``legge_estera``, ``eventi``,
    ``data_opzione``, ``beneficio``, ``res_defunto``, ``casi``). Ogni valore e' ``None`` se la casella non e' indicata."""
    el = "Frontespizio"
    out: dict = {"legge_estera": None, "eventi": None, "data_opzione": None, "beneficio": None, "res_defunto": None, "casi": None,
                 "attestazione": None}
    if _bool(x, "legge_estera"):
        out["legge_estera"] = "1"
    ev = SUP.dich(x.d, "eventi_eccezionali")
    if ev not in (None, "", False):
        if ev is not True and str(ev) != "1":
            x.err("VALORE_NON_VALIDO", PERC + "eventi_eccezionali", "l'unico codice previsto e' 1 (inagibilita' dell'immobile "
                  "prima casa gia' agevolato)", FO.fonte_xsd(el + "/TipoDichiarazione/EventiEccezionali"))
        else:
            out["eventi"] = "1"
            x.fr_altro = True      # il controllo ufficiale (3323) richiede il rigo EG8 «Altro»: certificazione di inagibilita'
    do = SUP.dich(x.d, "data_opzione")
    if do not in (None, ""):
        fonte = FO.fonte_annotazione(el + "/TipoDichiarazione/DataOpzione") + "; " + FONTE_FASC
        d = _data(x, "data_opzione", do, fonte)
        if d is not None:
            if d < PRIMO_2017 or (ddec is not None and d >= ddec):
                x.err("REGOLA_DATA_OPZIONE", PERC + "data_opzione", "la data dell'opzione art. 24-bis TUIR deve essere precedente "
                      "alla data del decesso e non inferiore al 1 gennaio 2017", fonte)
            else:
                out["data_opzione"] = F.data(str(do))
    if _bool(x, "beneficio_inventario"):
        out["beneficio"] = "1"
    rd = SUP.dich(x.d, "residenza_estera_defunto")
    if rd not in (None, ""):
        if str(rd) not in ("1", "2"):
            x.err("VALORE_NON_VALIDO", PERC + "residenza_estera_defunto", "codici ammessi: 1 (mai residente in Italia o residenza "
                  "ignota) o 2 (in parte in Italia e in parte all'estero)", FO.fonte_xsd(el + "/DatiDefunto/UlterioriDati/ResidenzaEstera"))
        else:
            out["res_defunto"] = str(rd)
    if _bool(x, "casi_particolari"):
        out["casi"] = "1"
    if _bool(x, "richiesta_attestazione"):
        # «Richiesta attestazione di avvenuta presentazione della dichiarazione di successione (copia conforme della dichiarazione
        # telematica)»: casella del frontespizio, una sola attestazione (Fascicolo I pp. PDF 5 e 16)
        out["attestazione"] = "1"
    return out


def decorrenza(x, ddec: date | None, psup: dict) -> str | None:
    """``Presentatore/DecorrenzaTerminePresentazione`` (non inferiore alla data del decesso)."""
    v = psup.get("data_decorrenza")
    if v in (None, ""):
        return None
    fonte = FO.fonte_annotazione("Frontespizio/Presentatore/DecorrenzaTerminePresentazione") + "; " + FONTE_FASC
    d = _data(x, "presentatore.data_decorrenza", v, fonte)
    if d is None:
        return None
    if ddec is not None and d < ddec:
        x.err("REGOLA_DECORRENZA_TERMINE", PERC + "presentatore.data_decorrenza", "la decorrenza del termine di presentazione non "
              "puo' essere anteriore alla data del decesso", fonte)
        return None
    return F.data(str(v))


def riduci_per_integrativa(x) -> dict:
    """Codice 3 (integrativa con sola documentazione): la dichiarazione contiene SOLO il frontespizio e il quadro EG (annotazioni XSD:
    gli altri quadri «non devono essere presenti se Dichiarazione sostitutiva = 3»; Fascicolo I p. PDF 12). Restituisce i dati
    ridotti a defunto, presentatore e documenti; il resto della pratica non e' esportato e il fatto viene segnalato con un avviso."""
    d = x.d
    pers = d.get("persone", [])
    psup = SUP.dich(d, "presentatore")
    rif = psup.get("persona_id") if isinstance(psup, dict) else None
    tengo = [p for p in pers if p.get("ruolo") in ("defunto", "presentatore") or p["id"] == rif]
    ids = {p["id"] for p in tengo}
    for p in tengo:        # un erede che presenta: i dati del quadro EA (grado, tipo...) non si esportano con il codice 3
        if p.get("ruolo") not in ("defunto", "presentatore") and p.get("relazione_con_defunto") not in (None, ""):
            x.usa(p, "relazione_con_defunto")
            x.interno(p, "relazione_con_defunto")
    scartati =[p["id"] for p in pers if p["id"] not in ids]
    n_beni, n_pass, n_dev = len(d.get("beni", [])), len(d.get("passivita", [])), len(d.get("devoluzioni", []))
    ridotti = dict(d)
    ridotti["persone"], ridotti["beni"], ridotti["passivita"], ridotti["devoluzioni"] = tengo, [], [], []
    tel = (d.get("opzioni") or {}).get("telematico")
    if isinstance(tel, dict):
        tel2 = dict(tel)
        if isinstance(tel.get("persone"), dict):
            tel2["persone"] = {k: v for k, v in tel["persone"].items() if k in ids}
        for coll in ("beni", "passivita", "devoluzioni"):
            if coll in tel2:
                tel2[coll] = {}
        opz = dict(d["opzioni"])
        opz["telematico"] = tel2
        ridotti["opzioni"] = opz
    if scartati or n_beni or n_pass or n_dev:
        x.avv("INTEGRATIVA_SOLO_FRONTESPIZIO_EG", "opzioni.tipo_dichiarazione",
              f"dichiarazione integrativa (codice 3): vengono esportati solo il frontespizio e il quadro EG; non sono esportati "
              f"{len(scartati)} soggetti, {n_beni} beni, {n_pass} passivita' e {n_dev} devoluzioni presenti nella pratica",
              "fornituraSUC13_v1.xsd (annotazioni: «non deve essere presente se Dichiarazione sostitutiva = 3»); " + FONTE_FASC)
    return ridotti


# ---------------------------------------------------------------------------------------------- codici carica del presentatore
CARICHE_SUPPORTATE = ("1", "2", "3", "4", "5", "6", "7", "8")
MOTIVO_CARICA = {
    "9": "trustee o suo rappresentante: BLOCCATO. Richiede insieme soggetti Trust (tipo 5) nel quadro EA con le sezioni Trust e il "
         "beneficiario finale, TrustDisab ed EF3-bis (imposta fissa), ImpostaCatastaleTrustDisab, l'atto istitutivo in EG «Altro», il "
         "pagamento anticipato EF18ter e l'esclusione di agevolazioni e riduzioni; il calcolo dell'imposta (modulo calcolo) non "
         "gestisce il trust e le fonti non ne danno una regola di importo completa da verificare col controllo ufficiale",
}
FONTE_CARICA = "fornituraSUC13_v1.xsd, annotazioni di Frontespizio/Presentatore/CodiceCarica e CodiceFiscaleRappresentato; " + FONTE_FASC


def regole_carica(x, carica: str | None, pres: dict, cfp, cfd, in_ea: list) -> None:
    """Coerenza fra codice carica, quadro EA e devoluzione (annotazioni di ``Presentatore/CodiceCarica`` e ``Devoluzione``)."""
    perc = f"persone[{pres['id']}]"
    tipo = x.tipo_ea.get(in_ea[0]["id"]) if in_ea else None
    testamento = SUP.dich(x.d, "devoluzione_per_testamento") is True
    if carica == "1" and in_ea and tipo not in ("1", "3"):
        x.err("REGOLA_PRESENTATORE", perc, "con codice carica 1 il dichiarante deve essere un erede o chiamato (tipo soggetto 1 o 3 "
              "nel quadro EA)", FONTE_CARICA)
    if carica == "2":
        if not in_ea:
            x.err("REGOLA_PRESENTATORE", perc, "con codice carica 2 il dichiarante deve essere presente nel quadro EA come legatario",
                  FONTE_CARICA)
        elif tipo != "2":
            x.err("REGOLA_PRESENTATORE", perc, "con codice carica 2 il tipo soggetto del dichiarante nel quadro EA deve essere 2 "
                  "(legatario)", FONTE_CARICA)
        if not testamento and SUP.dich(x.d, "legge_estera") is not True:
            x.err("REGOLA_CARICA_LEGATARIO", PERC + "devoluzione_per_testamento", "con codice carica 2 (legatario) la devoluzione per "
                  "testamento e' obbligatoria in assenza di legge estera", FONTE_CARICA)
    if carica in ("5", "6"):
        # annotazione di CasiParticolari: obbligatorio con le cariche 5, 6, 9 (controllo ufficiale 3250: «campo volture catastali
        # obbligatorio se codice carica 5 o 6 o 9»); Fascicolo I p. PDF 15: eredita' giacente/amministrata senza voltura automatica
        if SUP.dich(x.d, "casi_particolari") is not True:
            x.err("DATO_MANCANTE", PERC + "casi_particolari", f"con il codice carica {carica} la casella «non voler dar corso alle "
                  "volture catastali» e' obbligatoria (eredita' giacente o amministrata: voltura non automatizzabile)", FONTE_CARICA)
    if carica == "5" and not SO.e_sostitutiva(x.d):
        tipi = [x.tipo_ea.get(p["id"]) for p in x.ea]
        if len(x.ea) != 1 or tipi != ["6"]:
            x.err("REGOLA_CARICA_CURATORE", "quadro[EA]", "con il codice carica 5 (curatore dell'eredita' giacente) nel quadro EA deve "
                  "esserci un solo soggetto, la curatela, con tipo soggetto 6 (Altro) (annotazione XSD di CodiceCarica, prima "
                  "dichiarazione)", FONTE_CARICA)
    if carica == "7" and not testamento:
        x.err("REGOLA_CARICA_ESECUTORE", PERC + "devoluzione_per_testamento", "il codice carica 7 (esecutore testamentario) e' ammesso "
              "solo con la devoluzione per testamento", FONTE_CARICA)


def rappresentato(x, carica: str | None, psup: dict, cfp, cfd) -> str | None:
    """``Presentatore/CodiceFiscaleRappresentato``: obbligatorio con le cariche 3 e 4; vietato con 1, 2, 5, 6, 7; diverso dal defunto
    e dal presentatore."""
    v = psup.get("rappresentato_cf")
    perc = PERC + "presentatore.rappresentato_cf"
    if v in (None, ""):
        if carica in ("3", "4"):
            x.err("DATO_MANCANTE", perc, f"con codice carica {carica} il codice fiscale del soggetto rappresentato e' obbligatorio",
                  FONTE_CARICA)
        return None
    if carica in ("1", "2", "5", "6", "7", "8"):
        x.err("DATI_INCOERENTI", perc, f"con codice carica {carica} il codice fiscale del rappresentato non va indicato", FONTE_CARICA)
        return None
    try:
        cf = F.cf(v)
    except F.ValoreXml as e:
        x.err("VALORE_NON_VALIDO", perc, str(e), FONTE_CARICA)
        return None
    if cf == cfd or cf == cfp:
        x.err("REGOLA_RAPPRESENTATO", perc, "il rappresentato deve essere diverso dal defunto e dal soggetto che presenta il modello",
              FONTE_CARICA)
        return None
    if not any(isinstance(p.get("codice_fiscale"), str) and p["codice_fiscale"].strip().upper() == cf for p in x.ea):
        x.avv("RAPPRESENTATO_NON_IN_EA", perc, "il soggetto rappresentato non risulta nel quadro EA (erede, chiamato o legatario): "
              "verificare il codice fiscale", FONTE_CARICA)
    return cf


def residente_estero(x, psup: dict) -> dict | None:
    """``Presentatore/ResidenteEstero`` (Fascicolo I p. PDF 15): stessi campi della residenza estera dei soggetti EA."""
    v = psup.get("residente_estero")
    if v in (None, "", {}):
        return None
    pseudo = {"id": "presentatore", "residenza_estera": v}
    return x.residenza_estera(pseudo, "presentatore", "Frontespizio/Presentatore")


# ------------------------------------------------------------------------------------------- soggetto «Altro» (tipo soggetto 6)
FONTE_ALTRO = ("fornituraSUC13_v1.xsd, annotazioni di QuadroEA/Modulo/Soggetto/TipoSoggetto («se e' presente il valore 6 (Altro) non possono "
               "essere presenti altri soggetti nel quadro»), GradoParentela e CodiceFiscale; Fascicolo I p. PDF 17")


def regole_tipo_altro(x, base: str, p: dict) -> None:
    """Tipo soggetto 6 (Altro: la curatela dell'eredita' giacente o amministrata). Unico soggetto del quadro EA, con denominazione
    (soggetto diverso da persona fisica); grado 35 (Estraneo/a), unico caso provato col controllo ufficiale locale."""
    if len(x.ea) != 1:
        x.err("REGOLA_TIPO_ALTRO", base + ".tipo_soggetto", "con il tipo soggetto 6 (Altro) non possono esserci altri soggetti nel quadro "
              "EA", FONTE_ALTRO)
    den = SUP.attr(x.d, "persone", p, "denominazione")
    if den in (None, ""):
        x.err("DATO_MANCANTE", f"opzioni.telematico.persone[{p['id']}].denominazione", "con il tipo soggetto 6 (Altro) la denominazione "
              "(della curatela) e' obbligatoria: il soggetto non e' una persona fisica", FONTE_ALTRO)
    if SUP.attr(x.d, "persone", p, "rinuncia") not in (None, False):
        x.err("REGOLA_TIPO_ALTRO", f"opzioni.telematico.persone[{p['id']}].rinuncia", "la rinuncia non e' prevista per il tipo soggetto 6",
              FONTE_ALTRO)


def grado_tipo_altro(x, base: str, grado) -> None:
    if grado is not None and grado != "35":
        x.err("REGOLA_TIPO_ALTRO", base + ".grado_parentela", f"con il tipo soggetto 6 (Altro) e la denominazione e' provato solo il grado 35 "
              f"(Estraneo/a), non {grado}: gli altri gradi di soggetti non persone fisiche (36-39) hanno regole proprie", FONTE_ALTRO)


# ------------------------------------------------------------------------------------- morte presunta (codice carica 8)
FONTE_MORTE_PRESUNTA = ("fornituraSUC13_v1.xsd, annotazioni di QuadroEH/.../DatiDefunto/MortePresunta (obbligatoria se codice carica = 8) e "
                        "DataDeposito (successiva alla data del decesso del frontespizio); Fascicolo I pp. PDF 15 e 52-53")


def morte_presunta(x, ddec: date | None) -> dict | None:
    """Sezione ``MortePresunta`` del quadro EH (``opzioni.telematico.dichiarazione.morte_presunta {tribunale, data_deposito, sentenza}``):
    obbligatoria con il codice carica 8 (persona immessa nel possesso temporaneo dei beni dell'assente), non ammessa con gli altri."""
    v = SUP.dich(x.d, "morte_presunta")
    carica = x.codice_carica
    if v in (None, "", {}):
        if carica == "8":
            x.err("DATO_MANCANTE", PERC + "morte_presunta", "con il codice carica 8 (possesso temporaneo dei beni dell'assente) servono "
                  "tribunale, data di deposito e sentenza di morte presunta", FONTE_MORTE_PRESUNTA)
        return None
    if carica != "8":
        x.err("DATI_INCOERENTI", PERC + "morte_presunta", "la morte presunta si indica solo con il codice carica 8", FONTE_MORTE_PRESUNTA)
        return None
    if not isinstance(v, dict) or set(v) - {"tribunale", "data_deposito", "sentenza"}:
        x.err("VALORE_NON_VALIDO", PERC + "morte_presunta", "atteso {tribunale, data_deposito, sentenza}", FONTE_MORTE_PRESUNTA)
        return None
    out: dict = {"FlagAssenza": "1"}
    for chiave, nome in (("tribunale", "Tribunale"), ("sentenza", "Sentenza")):
        if v.get(chiave) in (None, ""):
            x.err("DATO_MANCANTE", PERC + "morte_presunta." + chiave, f"{chiave} obbligatorio", FONTE_MORTE_PRESUNTA)
            continue
        try:
            out[nome] = F.an(str(v[chiave]), 50)
        except F.ValoreXml as e:
            x.err("VALORE_NON_VALIDO", PERC + "morte_presunta." + chiave, str(e), FONTE_MORTE_PRESUNTA)
    dd = v.get("data_deposito")
    if dd in (None, ""):
        x.err("DATO_MANCANTE", PERC + "morte_presunta.data_deposito", "data di deposito obbligatoria", FONTE_MORTE_PRESUNTA)
    else:
        d = _data(x, "morte_presunta.data_deposito", dd, FONTE_MORTE_PRESUNTA)
        if d is not None:
            if ddec is not None and d <= ddec:
                x.err("REGOLA_MORTE_PRESUNTA", PERC + "morte_presunta.data_deposito", "la data di deposito deve essere successiva alla "
                      "data del decesso", FONTE_MORTE_PRESUNTA)
            else:
                out["DataDeposito"] = F.data(str(dd))
    return out if len(out) == 4 else None
