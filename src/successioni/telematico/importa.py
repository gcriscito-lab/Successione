"""Importazione di un file telematico SUC13 (XML) come nuova pratica: l'inverso, limitato, di ``esporta.py``.

Serve a riprendere e modificare successioni gia' predisposte. Si importano solo i dati che l'esportazione sa riprodurre e
che la prova di andata e ritorno (tests/test_telematico_importa.py) verifica: frontespizio, eredi (EA), terreni (EB),
fabbricati (EC), passivita' (ED) e disponibilita' finanziarie (ER). Tutto il resto e' elencato in ``non_importato`` e va
reinserito a mano; i quadri di calcolo (EE, EF) si ricalcolano. L'XML non e' validato qui: la validita' e' quella del
controllo ufficiale sul file ri-esportato.

Il risultato e' un elenco di operazioni per ``Servizio.crea_pratica(iniziali=...)``: nessun dato viene scritto da questo
modulo. Dati ricavati dal file, non verificati: l'utente li controlla.
"""
from __future__ import annotations

import re
from contextvars import ContextVar
from datetime import date
from decimal import Decimal, InvalidOperation

from lxml import etree

NS = {"suc": "urn:www.agenziaentrate.gov.it:specificheTecniche:sco:suc:v1",
      "reg": "urn:www.agenziaentrate.gov.it:specificheTecniche:sco:reg:v2",
      "tm": "www.agenziaentrate.gov.it:specificheTecniche:telent:v1"}
QUADRI_RICALCOLATI = {"QuadroEE": "totali ricalcolati dal programma", "QuadroEF": "imposte ricalcolate dal programma"}
QUADRI_NON_IMPORTATI = {
    "QuadroEG": "allegati: da riacquisire", "QuadroEH": "dichiarazioni e testamento: da reinserire",
    "QuadroEI_new": "voltura: da reinserire", "QuadroEL": "da reinserire", "QuadroEM": "da reinserire",
    "QuadroEN": "da reinserire", "QuadroEO": "da reinserire", "QuadroEP": "da reinserire", "QuadroEQ": "da reinserire",
}


class XmlNonImportabile(ValueError):
    pass

_letti = ContextVar("elementi_xml_importati", default=None)


def _t(el, percorso: str) -> str | None:
    r = el.xpath(percorso, namespaces=NS)
    if r and _letti.get() is not None:
        _letti.get().update(r)
    return (r[0].text or "").strip() if r else None


def _data(s: str | None) -> str | None:
    if not s:
        return None
    if not re.fullmatch(r"\d{8}", s):
        raise XmlNonImportabile(f"data non nel formato ggmmaaaa: {s!r}")
    try:
        return date(int(s[4:]), int(s[2:4]), int(s[:2])).isoformat()
    except ValueError as e:
        raise XmlNonImportabile(f"data inesistente: {s!r}") from e


def _dec(s: str | None) -> str | None:
    """Importo/numero con virgola decimale -> stringa con punto."""
    if s is None or s == "":
        return None
    t = s.replace(",", ".")
    try:
        if not Decimal(t).is_finite():
            raise InvalidOperation
    except InvalidOperation:
        raise XmlNonImportabile(f"numero non valido: {s!r}") from None
    return t


def _intero(s: str | None, cosa: str) -> int:
    d = Decimal(_dec(s) or "0")
    if d != d.to_integral_value():
        raise XmlNonImportabile(f"{cosa}: atteso un intero, trovato {s!r}")
    return int(d)


def _anagrafica(el, base: str) -> dict:
    out = {}
    for campo, tag in (("cognome", "Cognome"), ("nome", "Nome"), ("sesso", "Sesso"), ("luogo_nascita", "ComuneNascita"),
                       ("provincia_nascita", "ProvinciaNascita")):
        v = _t(el, f"{base}/reg:{tag}")
        if v:
            out[campo] = v
    d = _data(_t(el, f"{base}/reg:DataNascita"))
    if d:
        out["data_nascita"] = d
    return out


def _quota(el, percorso: str, cosa: str) -> dict | None:
    n = _t(el, percorso + "Numeratore")
    d = _t(el, percorso + "Denominatore")
    if n is None or d is None:
        return None
    return {"num": _intero(n, cosa), "den": _intero(d, cosa)}


def _upsert(coll: str, eid: str, campi: dict) -> dict:
    return {"op": "upsert", "coll": coll, "id": eid, "campi": campi}


def importa_xml(xml: bytes) -> dict:
    token = _letti.set(set())
    try:
        return _importa_xml(xml)
    finally:
        _letti.reset(token)


def _importa_xml(xml: bytes) -> dict:
    """Legge un file telematico SUC13. Restituisce ``{"operazioni", "titolo", "importato", "non_importato", "avvisi"}``."""
    try:
        radice = etree.fromstring(xml, parser=etree.XMLParser(resolve_entities=False, no_network=True))
    except etree.XMLSyntaxError as e:
        raise XmlNonImportabile(f"non e' un XML valido: {e}") from None
    if radice.getroottree().docinfo.doctype:
        raise XmlNonImportabile("DOCTYPE non ammesso nei file telematici")
    dich = radice.xpath("//suc:Fornitura/suc:Dichiarazione", namespaces=NS)
    if not dich:
        raise XmlNonImportabile("nessuna dichiarazione SUC13 nel file (manca suc:Fornitura/suc:Dichiarazione)")
    if len(dich) > 1:
        raise XmlNonImportabile(f"il file contiene {len(dich)} dichiarazioni: se ne importa una per volta")
    d = dich[0]
    fr = d.xpath("suc:Frontespizio", namespaces=NS)
    if not fr:
        raise XmlNonImportabile("frontespizio assente")
    fr = fr[0]
    ops: list[dict] = []
    avvisi: list[str] = []
    importato: dict[str, int] = {}

    # ---- defunto
    cf_def = _t(fr, "suc:CodiceFiscaleDefunto")
    if not cf_def:
        raise XmlNonImportabile("codice fiscale del defunto assente")
    defunto = {"ruolo": "defunto", "codice_fiscale": cf_def, **_anagrafica(fr, "suc:DatiDefunto/suc:DatiAnagrafici")}
    dd = _data(_t(fr, "suc:DatiDefunto/suc:UlterioriDati/suc:DataDecesso"))
    if dd:
        defunto["data_decesso"] = dd
    # il luogo del decesso e' nel quadro EH (primo modulo, sezione I)
    for campo, tag in (("comune_decesso", "Comune"), ("provincia_decesso", "Provincia")):
        v = _t(d, f"suc:QuadroEH/suc:PrimoModulo/suc:SezioneI_DichSost/suc:DatiDefunto/suc:Decesso/suc:{tag}")
        if v:
            defunto[campo] = v
    ops.append(_upsert("persone", "p_defunto1", defunto))

    dichiarazione: dict = {}
    sc = _t(fr, "suc:DatiDefunto/suc:UlterioriDati/suc:StatoCivile")
    if sc:
        dichiarazione["stato_civile"] = sc
    if _t(fr, "suc:TipoDichiarazione/suc:Devoluzione/suc:DevoluzionePerLegge") == "1":
        dichiarazione["devoluzione_per_legge"] = True
    if _t(fr, "suc:TipoDichiarazione/suc:Devoluzione/suc:DevoluzionePerTestamento") == "1":
        avvisi.append("devoluzione per testamento: estremi importati dal frontespizio; verificare dichiarazioni EH e riacquisire il testamento")
        dichiarazione["devoluzione_per_testamento"] = True
        base_test = "suc:TipoDichiarazione/suc:Devoluzione/suc:Testamento"
        testamento = {}
        if _t(fr, base_test + "/suc:TestamentoEstero") == "1":
            testamento["estero"] = True
        for campo, path in (("pubblico_ufficiale", "suc:Pubblicazione/suc:PubblicoUfficiale"),
                            ("data_pubblicazione", "suc:Pubblicazione/suc:DataPubblicazioneTestamento"),
                            ("ufficio_registrazione", "suc:Registrazione/reg:UfficioDiRegistrazione"),
                            ("serie", "suc:Registrazione/reg:Serie"),
                            ("numero_registrazione", "suc:Registrazione/reg:NumeroRegistrazione"),
                            ("sottonumero_registrazione", "suc:Registrazione/reg:SottonumeroRegistrazione"),
                            ("data_registrazione", "suc:Registrazione/reg:DataRegistrazione")):
            v = _t(fr, base_test + "/" + path)
            if v:
                testamento[campo] = _data(v) if campo.startswith("data_") else v
        dichiarazione["testamento"] = testamento
    if _t(fr, "suc:FirmaModello/suc:FirmaDichiarante") == "1":
        dichiarazione["firma_dichiarante"] = True
    iban = _t(fr, "suc:Versamento/reg:IBAN")
    if iban:
        dichiarazione["versamento"] = {"iban": iban, "cf_titolare": _t(fr, "suc:Versamento/reg:CodiceFiscaleTitolareCC")}

    # ---- eredi (EA): l'ordine del file e' quello dei riferimenti Rigo/Modulo
    persona_di_rigo: dict[tuple[int, int], str] = {}
    persona_di_cf: dict[str, str] = {}
    tel_persone: dict[str, dict] = {}
    n = 0
    for m, mod in enumerate(d.xpath("suc:QuadroEA/suc:Modulo", namespaces=NS), 1):
        for r, s in enumerate(mod.xpath("suc:Soggetto", namespaces=NS), 1):
            n += 1
            cf = _t(s, "suc:CodiceFiscale")
            pid = f"p_erede{n:03d}"
            ts, gp = _t(s, "suc:TipoSoggetto"), _t(s, "suc:GradoParentela")
            campi = {"ruolo": "legatario" if ts == "2" else "erede", "codice_fiscale": cf,
                     **_anagrafica(s, "suc:DatiAnagrafici")}
            if ts:
                campi["tipo_soggetto"] = ts
            handicap = _t(s, "suc:PortatoreHandicap")
            if handicap:
                if handicap != "1":
                    raise XmlNonImportabile("PortatoreHandicap: atteso 1")
                tel_persone[pid] = {"portatore_handicap": True}
            if gp:
                campi["grado_parentela"] = gp
                campi["relazione_con_defunto"] = gp
                if gp == "35" and ts != "2":
                    avvisi.append(f"{cf}: grado 35 (estraneo), importato come erede; se e' un legatario cambiarne il ruolo")
            ops.append(_upsert("persone", pid, campi))
            persona_di_rigo[(m, r)] = pid
            persona_di_cf[cf] = pid
    importato["eredi"] = n

    # ---- presentatore
    pres = fr.xpath("suc:Presentatore", namespaces=NS)
    if pres:
        p = pres[0]
        cf = _t(p, "suc:CodiceFiscale")
        anagrafica_pres = _anagrafica(p, "suc:DatiAnagrafici")
        dichiarazione["presentatore"] = {"codice_carica": _t(p, "suc:CodiceCarica"), "telefono": _t(p, "suc:Telefono")}
        if cf in persona_di_cf:
            dichiarazione["presentatore"]["persona_id"] = persona_di_cf[cf]
            erede = next(o["campi"] for o in ops if o.get("id") == persona_di_cf[cf])
            if any(erede.get(k) != v for k, v in anagrafica_pres.items()):
                raise XmlNonImportabile("anagrafica del presentatore diversa dal soggetto EA con lo stesso codice fiscale")
        else:                           # estraneo agli eredi: persona con ruolo presentatore (e senza riferimento, che sarebbe ambiguo)
            ops.append(_upsert("persone", "p_present1", {"ruolo": "presentatore", "codice_fiscale": cf,
                                                         **anagrafica_pres}))
        dichiarazione["presentatore"] = {k: v for k, v in dichiarazione["presentatore"].items() if v}

    # ---- beni
    tel_beni: dict[str, dict] = {}
    posizione_bene: dict[tuple[str, int, int], str] = {}      # (quadro, modulo, rigo) -> id bene
    devoluzioni: list[dict] = []

    def devoluzioni_di(bid: str, nodo, tag: str, elemento: str, ctx: str):
        for k, dv in enumerate(nodo.xpath(f"suc:{tag}/suc:{elemento}", namespaces=NS), 1):
            rigo = _intero(_t(dv, "suc:IdentificazioneSoggetto/suc:Rigo"), ctx)
            mod = _intero(_t(dv, "suc:IdentificazioneSoggetto/suc:Modulo"), ctx)
            pid = persona_di_rigo.get((mod, rigo))
            if pid is None:
                raise XmlNonImportabile(f"{ctx}: la devoluzione {k} rimanda a un erede inesistente (modulo {mod}, rigo {rigo})")
            q = _quota(dv, "suc:Quota/suc:QuotaElementi/suc:Quota", ctx)
            campi = {"bene_id": bid, "persona_id": pid, "quota": q}
            dr = _t(dv, "suc:CodiceDiritto_Rip")
            if dr:
                campi["diritto"] = dr
            devoluzioni.append(_upsert("devoluzioni", f"d_import{len(devoluzioni)+1:06d}", campi))

    def continuazione(b, tag, corrente, attesa, ctx):
        if attesa:
            if any(etree.QName(e).localname != tag for e in b):
                raise XmlNonImportabile(f"{ctx}: rigo di continuazione con dati di un nuovo bene")
            if not b.xpath(f"suc:{tag}/suc:Devoluzione", namespaces=NS):
                raise XmlNonImportabile(f"{ctx}: continuazione senza beneficiari")
            devoluzioni_di(corrente, b, tag, "Devoluzione", ctx)
        return _t(b, f"suc:{tag}/suc:Continuazione") == "1"

    def luogo(nodo, campi: dict):
        for campo, tag in (("provincia", "reg:Provincia"), ("comune", "reg:Italia/reg:ComuneAmministrativo"),
                           ("codice_comune", "reg:Italia/reg:CodiceComune"), ("indirizzo", "reg:Italia/reg:Indirizzo"),
                           ("codice_comune_amministrativo", "reg:Italia/reg:CodiceComuneAmministrativo")):
            v = _t(nodo, "suc:Luogo/" + tag)
            if v:
                campi[campo] = v

    def possesso(nodo, campi: dict, ctx: str):
        q = _quota(nodo, "suc:Possesso/suc:Possesso", ctx)
        if q:
            campi["quota_defunto"] = q
        dr = _t(nodo, "suc:CodiceDiritto_P")
        if dr:
            campi["diritto"] = dr
        v = _t(nodo, "suc:Valore")
        if v:
            campi["valore"] = _dec(v)

    for quadro, tipo, elem, dati_tag, dev_tag, sigla in (("QuadroEB", "terreno", "Terreni", "DatiTerreni", "DevoluzioneEB", "eb"),
                                                       ("QuadroEC", "fabbricato", "Fabbricati", "DatiFabbricati", "DevoluzioneEC", "ec")):
        k = 0
        attesa, bid = False, None
        for m, mod in enumerate(d.xpath(f"suc:{quadro}/suc:Modulo", namespaces=NS), 1):
            for r, b in enumerate(mod.xpath(f"suc:{elem}", namespaces=NS), 1):
                ctx = f"{quadro} modulo {m} rigo {r}"
                precedente = attesa
                attesa = continuazione(b, dev_tag, bid, attesa, ctx)
                if precedente:
                    posizione_bene[(quadro[-2:], m, r)] = bid
                    continue
                k += 1
                bid = f"b_{sigla}{k:03d}"
                ctx = f"{quadro} modulo {m} rigo {r}"
                campi: dict = {"tipo": tipo}
                tel: dict = {}
                luogo(b, campi)
                cat = f"suc:{dati_tag}/reg:DatiCatastali"
                for campo, tag in (("sezione", "Sezione"), ("foglio", "Foglio"), ("particella", "Particella"),
                                   ("subalterno", "Subalterno")):
                    v = _t(b, f"{cat}/reg:{tag}")
                    if v:
                        campi[campo] = v
                dati = f"suc:{dati_tag}/reg:{dati_tag}"
                if tipo == "terreno":
                    for campo, tag in (("natura", "Natura"),):
                        v = _t(b, f"{dati}/reg:{tag}")
                        if v:
                            campi[campo] = v
                    v = _dec(_t(b, f"{dati}/reg:RedditoDominicale"))
                    if v:
                        campi["reddito_dominicale"] = v
                    sup = {"ettari": _t(b, f"{dati}/reg:Superficie/reg:SuperficieEttari"),
                           "are": _t(b, f"{dati}/reg:Superficie/reg:SuperficieAre"),
                           "centiare": _t(b, f"{dati}/reg:Superficie/reg:SuperficieCentiare")}
                    if any(sup.values()):
                        tel["superficie"] = {c: _intero(v, ctx) for c, v in sup.items() if v}
                    v = _t(b, "suc:TipologiaTerreno")
                    if v:
                        campi["tipologia_terreno"] = v
                else:
                    for campo, tag in (("categoria", "CategoriaCatastale"), ("classe", "Classe")):
                        v = _t(b, f"{dati}/reg:{tag}")
                        if v:
                            campi[campo] = v
                    for campo, tag in (("consistenza", "Consistenza"), ("rendita", "RenditaCatastale")):
                        v = _dec(_t(b, f"{dati}/reg:{tag}"))
                        if v:
                            campi[campo] = v
                possesso(b, campi, ctx)
                ops.append(_upsert("beni", bid, campi))
                if tel:
                    tel_beni[bid] = tel
                posizione_bene[(quadro[-2:], m, r)] = bid
                devoluzioni_di(bid, b, dev_tag, "Devoluzione", ctx)
        if attesa:
            raise XmlNonImportabile(f"{quadro}: manca il rigo di continuazione")
        importato["terreni" if tipo == "terreno" else "fabbricati"] = k

    k = 0
    attesa, bid = False, None
    for m, mod in enumerate(d.xpath("suc:QuadroER/suc:Modulo", namespaces=NS), 1):
        for r, b in enumerate(mod.xpath("suc:Rendite", namespaces=NS), 1):
            ctx = f"QuadroER modulo {m} rigo {r}"
            precedente = attesa
            attesa = continuazione(b, "DevoluzioneER", bid, attesa, ctx)
            if precedente:
                posizione_bene[("ER", m, r)] = bid
                continue
            k += 1
            bid = f"b_er{k:03d}"
            ctx = f"QuadroER modulo {m} rigo {r}"
            campi = {"tipo": "disponibilita_finanziaria"}
            tc = _t(b, "suc:TipoCespite")
            tel = {"tipo_cespite": tc} if tc else {}
            ds = _t(b, "suc:Descrizione")
            if ds:
                campi["descrizione"] = ds
            possesso(b, campi, ctx)
            ops.append(_upsert("beni", bid, campi))
            if tel:
                tel_beni[bid] = tel
            posizione_bene[("ER", m, r)] = bid
            devoluzioni_di(bid, b, "DevoluzioneER", "Devoluzione", ctx)
    if attesa:
        raise XmlNonImportabile("QuadroER: manca il rigo di continuazione")
    importato["disponibilita_finanziarie"] = k

    # ---- passivita' (ED)
    tel_pass: dict[str, dict] = {}
    k = 0
    for m, mod in enumerate(d.xpath("suc:QuadroED/suc:Modulo", namespaces=NS), 1):
        for r, ps in enumerate(mod.xpath("suc:Passivita", namespaces=NS), 1):
            k += 1
            pid = f"ps_ed{k:03d}"
            ctx = f"QuadroED modulo {m} rigo {r}"
            campi = {}
            ds = _t(ps, "suc:Descrizione")
            if ds:
                campi["descrizione"] = ds
            v = _dec(_t(ps, "suc:Possesso/suc:Valore"))
            if v:
                campi["importo"] = v
            tel = {}
            for campo, tag in (("tipo", "Tipo"), ("estremi_documento", "EstremiDocumento")):
                v = _t(ps, "suc:" + tag)
                if v:
                    tel[campo] = v
            dt = _data(_t(ps, "suc:DataDocumento"))
            if dt:
                tel["data_documento"] = dt
            q = _quota(ps, "suc:Possesso/suc:Possesso", ctx)
            if q:
                tel["possesso"] = q
            pc = ps.xpath("suc:ProgressivoCespite", namespaces=NS)
            if pc:
                chiave = (_t(pc[0], "suc:Quadro"), _intero(_t(pc[0], "suc:Mod"), ctx), _intero(_t(pc[0], "suc:Rigo"), ctx))
                bid = posizione_bene.get((chiave[0], chiave[1], chiave[2]))
                if bid:
                    tel["bene_id"] = bid
                else:
                    avvisi.append(f"{ctx}: il cespite collegato ({chiave[0]} modulo {chiave[1]} rigo {chiave[2]}) non e' stato importato")
            rip = []
            for rp in ps.xpath("suc:RipartizioneED/suc:Ripartizione", namespaces=NS):
                rigo = _intero(_t(rp, "suc:IdentificazioneSoggetto/suc:Rigo"), ctx)
                mm = _intero(_t(rp, "suc:IdentificazioneSoggetto/suc:Modulo"), ctx)
                pers = persona_di_rigo.get((mm, rigo))
                if pers is None:
                    raise XmlNonImportabile(f"{ctx}: la ripartizione rimanda a un erede inesistente (modulo {mm}, rigo {rigo})")
                rip.append({"persona_id": pers, "quota": _quota(rp, "suc:Quota/suc:QuotaElementi/suc:Quota", ctx)})
            if len(rip) == 1 and rip[0]["quota"] == {"num": 1, "den": 1}:
                campi["persona_id"] = rip[0]["persona_id"]       # un solo erede per l'intero: forma semplice del modello
            elif rip:
                tel["ripartizione"] = rip
            ops.append(_upsert("passivita", pid, campi))
            tel_pass[pid] = tel
    importato["passivita"] = k

    ops.extend(devoluzioni)
    telematico: dict = {"dichiarazione": dichiarazione}
    if tel_persone:
        telematico["persone"] = tel_persone
    if tel_beni:
        telematico["beni"] = tel_beni
    if tel_pass:
        telematico["passivita"] = tel_pass
    ops.append({"op": "set", "sezione": "opzioni", "campi": {"telematico": telematico}})

    # Nessun campo significativo dei quadri dichiarati importabili puo' sparire.
    # I totali e le caselle derivate sono ricostruiti dall'export; gli altri campi
    # non letti rendono esplicito il limite PRIMA di creare la pratica.
    derivati = {"NumeroBeneficiari", "NumeroImmobili", "NumeroEredi", "NumeroLegatari", "NumeroChiamati",
                "ImportoDaVersare", "QuotaValore"}
    ignora = {"FirmaModello", "ImpegnoATrasmettere"}
    mancanti = []
    _t(fr, "suc:TipoDichiarazione/suc:PrimaDichiarazione")
    for sezione in d:
        if etree.QName(sezione).localname not in {"Frontespizio", "QuadroEA", "QuadroEB", "QuadroEC", "QuadroED", "QuadroER"}:
            continue
        for e in sezione.iter():
            if not isinstance(e.tag, str) or len(e) or not (e.text or "").strip() or e in _letti.get():
                continue
            nome = etree.QName(e).localname
            antenati = {etree.QName(a).localname for a in e.iterancestors()}
            if nome in derivati or antenati & ignora:
                continue
            mancanti.append(radice.getroottree().getpath(e))
    if mancanti:
        raise XmlNonImportabile("campi non supportati dall'importazione (nessun dato salvato): " + "; ".join(mancanti))
    non_importato = []
    presenti = {etree.QName(e).localname for e in d}
    for q in sorted(presenti):
        if q in QUADRI_RICALCOLATI:
            non_importato.append(f"{q}: {QUADRI_RICALCOLATI[q]}")
        elif q in QUADRI_NON_IMPORTATI:
            non_importato.append(f"{q}: {QUADRI_NON_IMPORTATI[q]}")
        elif q.startswith("Quadro") and q not in ("QuadroEA", "QuadroEB", "QuadroEC", "QuadroED", "QuadroER"):
            non_importato.append(f"{q}: non gestito dall'importazione")
    cognome = defunto.get("cognome", "")
    titolo = f"Importata: {cognome} {defunto.get('nome', '')}".strip()
    return {"operazioni": ops, "titolo": titolo, "importato": importato, "non_importato": non_importato, "avvisi": avvisi}
