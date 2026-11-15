"""Quadri EE ed EH letti dal file generato, con la struttura del modello ufficiale (revisione del 15/11/2026).

Nessun calcolo: si leggono gli elementi che l'esportazione ha scritto nell'XML e si danno loro i nomi del modello.
Fonti dei nomi e dell'ordine:
- EE: modello «Dichiarazione di successione», quadro EE (righi EE1-EE8) e XSD ``fornituraSUC13_v1.xsd`` (QuadroEE, annotazioni
  dei campi: quali quadri alimentano ciascun totale).
- EH: modello, quadro EH (righi EH1-EH18, sezioni I-IV), Fascicolo I pp. PDF 51-53 (lettere a-m della sezione I) e XSD
  (QuadroEH/PrimoModulo).
"""
from __future__ import annotations

#: rigo, elemento XSD, testo del modello, quadri che lo alimentano (annotazioni XSD di QuadroEE)
RIGHI_EE = (
    ("EE1", "TotaleValoreImmobili", "Totale valore immobili", ("EB", "EC", "EL", "EM")),
    ("EE2", "TotaleValoreAziende", "Totale valore aziende", ("EN",)),
    ("EE3", "TotaleValoreTitoli", "Totale valore azioni, obbligazioni, altri titoli e quote sociali", ("EO",)),
    ("EE4", "TotaleValoreAereiNavi", "Totale valore aeromobili, navi e imbarcazioni", ("EP", "EQ")),
    ("EE5", "TotaleValoreAltriBeni", "Totale valore altri beni", ("ER",)),
    ("EE6", "TotaleAttivo", "Totale (somma da EE1 a EE5)", ()),
    ("EE7", "TotalePassivo", "Totale passivo", ("ED",)),
    ("EE8", "TotaleValoreAsseEreditarioNetto", "Totale valore asse ereditario netto (differenza tra EE6 e EE7)", ()),
)


def righi_ee(ee: list[dict]) -> list[dict]:
    """Gli otto righi del quadro EE nell'ordine del modello; ``valore`` None se il rigo non e' nel file (vuoto)."""
    valori = {x["campo"]: x["valore"] for x in ee}
    return [{"rigo": r, "campo": c, "testo": t, "valore": valori.get(c), "quadri": list(q),
             "totale": r in ("EE6", "EE8")} for r, c, t, q in RIGHI_EE]


# ---------------------------------------------------------------------------------------------------------------- EH
#: nomi leggibili degli elementi foglia (testi del modello, quadro EH)
ETICHETTE = {
    "Cognome": "Cognome", "Nome": "Nome", "Sesso": "Sesso", "DataNascita": "Data di nascita", "ComuneNascita": "Comune di nascita",
    "ProvinciaNascita": "Provincia di nascita", "CodiceFiscale": "Codice fiscale", "CodiceCarica": "Codice carica",
    "CodiceFiscaleRappresentato": "Codice fiscale rappresentato", "DataDecesso": "Data del decesso", "Comune": "Comune",
    "Provincia": "Provincia", "Tribunale": "Tribunale", "DataDeposito": "Data di deposito", "Sentenza": "Numero della sentenza",
    "UfficioDiRegistrazione": "Ufficio", "Serie": "Serie", "NumeroRegistrazione": "Numero", "SottonumeroRegistrazione": "Sottonumero",
    "DataRegistrazione": "Data", "Rigo": "Rigo del quadro EA", "Modulo": "Modulo", "Certificatore": "Certificato da",
    "CameraCommercio": "Camera di commercio", "SiglaUfficioIscrizione": "Sigla ufficio di iscrizione",
    "AnnoIscrizione": "Anno di iscrizione", "NumeroIscrizione": "Numero di iscrizione", "Nazionalita": "Nazionalità",
    "AnnoImmatricolazione": "Anno di immatricolazione", "NumeroImmatricolazione": "Numero di immatricolazione",
    "CodiceComune": "Codice comune", "Indirizzo": "Indirizzo", "SezioneUrbana": "Sezione urbana", "Foglio": "Foglio",
    "Particella": "Particella", "Subalterno": "Subalterno", "TipologiaImposta": "Tipologia d'imposta", "Imposta": "Imposta",
    "NumProtocollo": "Numero di protocollo", "Data": "Data", "Anno": "Anno", "Volume": "Volume", "Numero": "Numero",
    "UfficioTerritoriale": "Ufficio territoriale", "GradoParentela": "Grado di parentela",
    # caselle (valore «barrata»)
    "FlagComuneResidenza": "a) l'immobile è nel comune in cui risiedo",
    "FlagComuneAttivita": "a) l'immobile è nel comune in cui svolgo la mia attività",
    "FlagCambioResidenza": "a) stabilirò la residenza nel comune entro 18 mesi",
    "FlagNessunaAltraCasaComune": "b) nessuna altra casa di abitazione nel comune",
    "FlagNessunaAltraCasa": "c) nessuna altra casa acquistata con le agevolazioni prima casa",
    "FlagVenditaAltraCasa": "d) mi impegno a trasferire l'altra casa entro due anni",
    "FlagTrasferitoEstero": "f) trasferito all'estero per motivi di lavoro",
    "FlagTrasferimentoPrima": "f) trasferimento avvenuto prima dell'acquisto",
    "FlagSedeLavoro": "f) immobile nel comune della sede del datore di lavoro",
    "FlagForzeArmate": "h) personale delle Forze armate o di polizia",
    "FlagContigui": "i) mi impegno a unire catastalmente gli immobili contigui",
    "FlagA": "A - beni culturali", "FlagL": "L - beni culturali (art. 25 c. 2)", "FlagC": "C - terreni agricoli in comunità montane",
    "FlagD": "D - aziende, quote sociali e azioni", "FlagE": "E - terreni agricoli in compendio unico",
    "FlagQ": "Q - aziende e quote di società di persone in comuni montani",
}
NON_MOSTRARE = {"FirmaDichiarante"}


def _loc(e) -> str:
    from lxml import etree
    return etree.QName(e).localname if isinstance(e.tag, str) else ""


def _valore(nome: str, testo: str) -> str:
    t = (testo or "").strip()
    if (nome.startswith("Data") or nome == "Data") and len(t) == 8 and t.isdigit():
        return f"{t[:2]}/{t[2:4]}/{t[4:]}"
    if nome.startswith("Flag") or nome.startswith("Presenza"):
        return "sì" if t == "1" else t
    return t


def _figlio(e, nome):
    return next((c for c in e if _loc(c) == nome), None)


def _dati(e, salta=()) -> list[list[str]]:
    """Foglie dell'elemento come [etichetta, valore], in ordine di documento (esclusi i nomi in ``salta``)."""
    out = []
    for c in e.iter():
        n = _loc(c)
        if len(c) or n in NON_MOSTRARE or n in salta or not (c.text or "").strip():
            continue
        out.append([ETICHETTE.get(n, n), _valore(n, c.text)])
    return out


def _nome(e) -> str:
    da = _figlio(e, "DatiAnagrafici") if _figlio(e, "DatiAnagrafici") is not None else e
    parti = [(_figlio(da, k).text or "").strip() for k in ("Cognome", "Nome") if _figlio(da, k) is not None]
    den = _figlio(da, "Denominazione")
    return " ".join(p for p in parti if p) or ((den.text or "").strip() if den is not None else "")


def _registrazioni(e, nome: str) -> list[list[list[str]]]:
    return [_dati(r) for r in e.iter() if _loc(r) == nome]


def _sezione_i(s) -> list[dict]:
    voci = []
    dd = _figlio(s, "DatiDefunto")
    if dd is not None:
        dec, mp = _figlio(dd, "Decesso"), _figlio(dd, "MortePresunta")
        if mp is not None:
            voci.append({"lettera": "a", "titolo": "Decesso", "scelta": "È stata dichiarata l'assenza o la morte presunta",
                         "dati": _dati(mp, ("FlagAssenza",)), "dove": "AN"})
        elif dec is not None:
            luogo = " ".join(x for x in ((_figlio(dec, "Comune").text if _figlio(dec, "Comune") is not None else ""),
                                         f"({_figlio(dec, 'Provincia').text})" if _figlio(dec, "Provincia") is not None else "") if x)
            voci.append({"lettera": "a", "titolo": "Decesso", "scelta": f"{_nome(dd)} è deceduto/a",
                         "dati": [x for x in [["Data del decesso", _valore("DataDecesso", _figlio(dec, "DataDecesso").text)]
                                              if _figlio(dec, "DataDecesso") is not None else None,
                                              ["Luogo del decesso", luogo] if luogo else None] if x], "dove": "AN"})
    eredi = [x for x in s if _loc(x) == "Eredi"]
    dich = _figlio(s, "Dichiarante")
    scelta = None
    if dich is not None:
        scelta = ("Eredi, chiamati e legatari: incluso me dichiarante" if _figlio(dich, "PresenzaDichiarante") is not None
                  else "Eredi, chiamati e legatari: escluso me dichiarante")
    if eredi or scelta:
        righe = []
        for i, e in enumerate(eredi, 1):
            da = _figlio(e, "DatiAnagrafici")
            g = lambda n: _valore(n, (_figlio(da, n).text if da is not None and _figlio(da, n) is not None else ""))  # noqa: E731
            righe.append([f"EH{i}" if i <= 3 else f"EH{(i - 1) % 3 + 1} (mod. {(i - 1) // 3 + 1})", _nome(e),
                          (_figlio(e, "CodiceFiscale").text or "") if _figlio(e, "CodiceFiscale") is not None else "",
                          g("DataNascita"), " ".join(x for x in (g("ComuneNascita"), f"({g('ProvinciaNascita')})" if g("ProvinciaNascita") else "") if x),
                          (_figlio(e, "GradoParentela").text or "") if _figlio(e, "GradoParentela") is not None else ""])
        voci.append({"lettera": "b", "titolo": "Eredi, chiamati all'eredità e legatari (righi EH1-EH3)", "scelta": scelta,
                     "tabella": {"colonne": ["Rigo", "Cognome e nome", "Codice fiscale", "Data di nascita", "Luogo di nascita",
                                             "Grado di parentela"], "righe": righe}, "dove": "EA"})
    t = _figlio(s, "Testamento")
    if t is not None:
        if _figlio(t, "FlagAssenzaTestamento") is not None:
            voci.append({"lettera": "c", "titolo": "Testamento (righi EH4-EH5)", "scelta": "Non esiste testamento", "dove": "AN"})
        else:
            regs = _registrazioni(t, "RegistrazioneTestamento")
            voci.append({"lettera": "c", "titolo": "Testamento (righi EH4-EH5)",
                         "scelta": "Esistono uno o più testamenti validi e non impugnati" + ("" if regs else " (testamento estero: estremi non richiesti)"),
                         "registrazioni": regs, "dove": "AN"})
    r = _figlio(s, "ReintegroDiritti")
    if r is not None:
        voci.append({"lettera": "d", "titolo": "Reintegro dei diritti di legittima",
                     "scelta": "Tra gli eredi è stato stipulato un accordo di reintegro",
                     "registrazioni": _registrazioni(r, "RegistrazioneReintegroDiritti"), "dove": "AN"})
    i = _figlio(s, "Interdetti")
    if i is not None:
        if _figlio(i, "FlagAssenzaInterdetti") is not None:
            voci.append({"lettera": "e", "titolo": "Incapaci, interdetti o persone con disabilità grave",
                         "scelta": "Non esistono incapaci o interdetti", "dove": "EA"})
        else:
            sog = [_dati(x) for x in i.iter() if _loc(x) == "IdentificazioneSoggetto"]
            cert = [(_figlio(x, "Certificatore").text or "") for x in i.iter() if _loc(x) == "PresenzaInterdetti" and _figlio(x, "Certificatore") is not None]
            voci.append({"lettera": "e", "titolo": "Incapaci, interdetti o persone con disabilità grave",
                         "scelta": "Gli eredi o legatari indicati sono incapaci, interdetti o con disabilità grave",
                         "soggetti": sog, "dati": [["Certificato da", c] for c in cert if c], "dove": "EA"})
    rn = _figlio(s, "Rinuncia")
    if rn is not None:
        if _figlio(rn, "FlagAssenzaRinuncia") is not None:
            voci.append({"lettera": "f", "titolo": "Rinunce all'eredità", "scelta": "Nessuno ha rinunciato all'eredità", "dove": "EA"})
        else:
            voci.append({"lettera": "f", "titolo": "Rinunce all'eredità", "scelta": "Gli eredi indicati hanno rinunciato",
                         "soggetti": [_dati(x) for x in rn.iter() if _loc(x) == "IdentificazioneSoggetto"],
                         "registrazioni": _registrazioni(rn, "RegistrazioneRinuncia"), "dove": "EA"})
    sp = _figlio(s, "Separazione")
    if sp is not None:
        voci.append({"lettera": "g", "titolo": "Separazione personale",
                     "scelta": ("È stata pronunciata sentenza di separazione per colpa del coniuge superstite o di entrambi"
                                if _figlio(sp, "FlagSeparazione") is not None else
                                "Non è stata pronunciata sentenza di separazione per colpa del coniuge superstite"), "dove": "EH"})
    if _figlio(s, "FlagNoScioglimentoUnioneCivile") is not None:
        voci.append({"lettera": "h", "titolo": "Unione civile", "scelta": "Non è stata presentata domanda di scioglimento",
                     "dove": "EH"})
    az = _figlio(s, "Aziende")
    if az is not None:
        voci.append({"lettera": "i", "titolo": "Bilancio di aziende o società", "scelta": "Il bilancio è stato depositato",
                     "dati": _dati(az, ("FlagAzienda",)), "dove": "EN"})
    copie = [t for n, t in (("FlagProspetto", "l'inventario o il prospetto delle attività e passività"),
                            ("FlagInventari", "gli inventari richiesti dalla legge"),
                            ("FlagPassivita", "i documenti di prova delle passività")) if _figlio(s, n) is not None]
    if copie:
        voci.append({"lettera": "l", "titolo": "Copie degli originali",
                     "scelta": "Costituiscono copie degli originali: " + "; ".join(copie), "dove": "EH"})
    for nome, titolo, q in (("Navi", "Navi e imbarcazioni", "EQ"), ("Aeromobili", "Aeromobili", "EP")):
        for x in (y for y in s if _loc(y) == nome):
            voci.append({"lettera": "m", "titolo": titolo, "scelta": f"Il defunto è proprietario di {titolo.lower()} (pubblici registri)",
                         "dati": _dati(x, ("FlagNavi", "FlagAeromobili")), "dove": q})
    return voci


def _sezione_ii(s) -> list[dict]:
    voci = []
    for nome, titolo in (("ImmobilePrincipale", "Immobile principale"), ("Pertinenza", "Pertinenza"),
                         ("ImmobileContiguo", "Immobile contiguo")):
        for x in (y for y in s if _loc(y) == nome):
            voci.append({"titolo": titolo, "dati": _dati(x), "dove": "EC"})
    dich = [ETICHETTE.get(_loc(c), _loc(c)) for c in s.iter() if _loc(c).startswith("Flag") and (c.text or "").strip() == "1"]
    if dich:
        voci.append({"titolo": "Dichiaro", "elenco": dich, "dove": "AN"})
    return voci


def _generica(s) -> list[dict]:
    voci = []
    for x in s:
        if _loc(x) in NON_MOSTRARE:
            continue
        if len(x):
            caselle = [ETICHETTE.get(_loc(c), _loc(c)) for c in x.iter() if _loc(c).startswith("Flag") and (c.text or "").strip() == "1"]
            voci.append({"titolo": _loc(x), "elenco": caselle, "dati": _dati(x, tuple(_loc(c) for c in x.iter() if _loc(c).startswith("Flag")))})
        elif (x.text or "").strip():
            voci.append({"titolo": ETICHETTE.get(_loc(x), _loc(x)), "dati": [[ETICHETTE.get(_loc(x), _loc(x)), _valore(_loc(x), x.text)]]})
    return voci


TITOLI_IV = {"EsenzioneImpostaSuccessione": "Esenzione dall'imposta di successione (A, L)",
             "Agevolazioni": "Agevolazioni (C, D, E, Q)", "Riduzioni": "Riduzioni per precedenti successioni o donazioni (1-5)"}
SEZIONI = (
    ("SezioneI_DichSost", "I", "Dichiarazioni sostitutive", "Sempre presente quando il quadro EH è compilato."),
    ("SezioneII_AgevPrimaCasa", "II", "Agevolazione prima casa (righi EH14-EH18)",
     "Si compila solo se il dichiarante chiede la prima casa (codici P, X, Y, Z sulle sue righe di devoluzione) o ha il diritto di abitazione."),
    ("SezioneIII_CreditoImposta", "III", "Richiesta di utilizzo del credito d'imposta",
     "Si compila solo se c'è il credito d'imposta del rigo EF7 (riacquisto prima casa)."),
    ("SezioneIV_AltreAgevRiduz", "IV", "Altre agevolazioni e riduzioni",
     "Si compila solo se il dichiarante chiede le agevolazioni A, L, C, D, E, Q o le riduzioni 1-5."),
)


def sezioni_eh(quadro_eh) -> dict:
    """{'dichiarante': {...}, 'sezioni': [...]} dal nodo QuadroEH del file (None: quadro assente)."""
    if quadro_eh is None:
        return {"dichiarante": None, "sezioni": []}
    pm = next((x for x in quadro_eh.iter() if _loc(x) == "PrimoModulo"), quadro_eh)
    s1 = _figlio(pm, "SezioneI_DichSost")
    pres = _figlio(s1, "Presentatore") if s1 is not None else None
    dichiarante = None
    if pres is not None:
        dichiarante = {"nome": _nome(pres), "codice_fiscale": (_figlio(pres, "CodiceFiscale").text or "") if _figlio(pres, "CodiceFiscale") is not None else "",
                       "codice_carica": (_figlio(pres, "CodiceCarica").text or "") if _figlio(pres, "CodiceCarica") is not None else ""}
    out = []
    for el, num, titolo, nota in SEZIONI:
        nodo = _figlio(pm, el)
        if nodo is None:
            voci = []
        elif el == "SezioneI_DichSost":
            voci = _sezione_i(nodo)
        elif el == "SezioneII_AgevPrimaCasa":
            voci = _sezione_ii(nodo)
        else:
            voci = _generica(nodo)
            for v in voci:
                v["titolo"] = TITOLI_IV.get(v["titolo"], v["titolo"])
        out.append({"sezione": num, "titolo": f"Sezione {num} - {titolo}", "presente": nodo is not None,
                    "nota": None if nodo is not None else nota, "voci": voci})
    return {"dichiarante": dichiarante, "sezioni": out}
