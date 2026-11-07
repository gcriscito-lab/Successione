"""Importazione di un file telematico SUC13 (XML) come nuova pratica: l'inverso, limitato, di ``esporta.py``.

Serve a riprendere e modificare successioni gia' predisposte. Si importano solo i dati che l'esportazione sa riprodurre e
che la prova di andata e ritorno (tests/test_telematico_importa.py, tests/test_telematico_importa_altri_beni.py) verifica:
frontespizio, eredi (EA), terreni (EB), fabbricati (EC), passivita' (ED), disponibilita' finanziarie (ER), terreni e
fabbricati tavolari (EL, EM), aziende (EN), titoli (EO), aeromobili (EP), navi (EQ) e voltura (EI, ricostruita dai flag
dei beni e dagli estremi di trascrizione/registrazione). Tutto il resto e' elencato in ``non_importato`` e va reinserito a
mano; i quadri di calcolo (EE, EF) si ricalcolano, tranne i dati di EF/EH dichiarati dal professionista (sanzioni e interessi
della Sezione VI, tempistica, rateazione e acconto, crediti d'imposta EF7/EF13/EF18bis ed EH Sezione III), che si importano. Dopo
l'importazione la pratica viene riesportata in prova: se il quadro EF o l'ImportoDaVersare ricalcolati differiscono dall'originale
c'e' un avviso con i due valori; i dati di EF non ricalcolati e non importati sono negli avvisi. L'XML non e' validato qui: la validita' e' quella del controllo
ufficiale sul file ri-esportato.

Regola generale: un elemento con testo che l'importazione non legge (e non e' un totale derivato) rende il file non
importabile con errore esplicito, oppure (quadri non gestiti, quadro EI del modello precedente, impegno a trasmettere) e'
elencato con il suo contenuto in ``non_importato``; mai scartato in silenzio. Commenti e istruzioni di elaborazione sono tolti
prima della lettura unendo il testo che separano (valore di un elemento secondo XML/XSD); il contenuto misto (testo fuori dagli
elementi) e' un errore. Dove l'esportazione ordina i righi con una chiave propria (EB, EC, EL, EM, EN, EO, EP, EQ, ER) un file
in ordine diverso si importa con un avviso esplicito: la riesportazione riscrive i righi nel proprio ordine.

Dichiarazione sostitutiva (codici 1, 2, 3): codice, estremi della prima dichiarazione e imposte gia' versate (EF6, EF12,
EF18bis col. 3) nelle chiavi lette da ``sostitutiva.py``; agevolazioni e riduzioni delle righe di devoluzione in
``opzioni.telematico.devoluzioni``; Sezioni II (prima casa) e IV (altre agevolazioni) del quadro EH nelle chiavi
``prima_casa`` e ``riduzioni_art25`` (gli immobili e le caselle derivate sono ricostruiti e confrontati con l'originale).

Il risultato e' un elenco di operazioni per ``Servizio.crea_pratica(iniziali=...)``: nessun dato viene scritto da questo
modulo. Dati ricavati dal file, non verificati: l'utente li controlla.
"""
from __future__ import annotations

import re
from contextvars import ContextVar
from datetime import date
from decimal import Decimal, InvalidOperation
from math import gcd

from lxml import etree

from ..quadri import PROVINCE_TAVOLARI
from . import prima_casa as PC
from .esporta import _chiave_immobile

NS ={"suc": "urn:www.agenziaentrate.gov.it:specificheTecniche:sco:suc:v1",
      "reg": "urn:www.agenziaentrate.gov.it:specificheTecniche:sco:reg:v2",
      "tm": "www.agenziaentrate.gov.it:specificheTecniche:telent:v1"}
QUADRI_RICALCOLATI = {"QuadroEE": "totali ricalcolati dal programma", "QuadroEF": "imposte ricalcolate dal programma"}
QUADRI_NON_IMPORTATI = {
    "QuadroEG": "allegati: da riacquisire", "QuadroEH": "dichiarazioni e testamento: da reinserire",
}
QUADRI_IMPORTATI = ("QuadroEA", "QuadroEB", "QuadroEC", "QuadroED", "QuadroEI_new", "QuadroEL", "QuadroEM", "QuadroEN",
                    "QuadroEO", "QuadroEP", "QuadroEQ", "QuadroER")
#: quadri attivi di una pratica nuova (src/successioni/quadri.py PREDEFINITI): i quadri importati in piu' vanno attivati
_ATTIVI_BASE = ["EA", "EB", "EC", "ER", "ED", "EG"]


class XmlNonImportabile(ValueError):
    pass

_letti = ContextVar("elementi_xml_importati", default=None)


def _analizza(xml: bytes | str):
    """Radice del documento, senza commenti ne' istruzioni di elaborazione: il testo che separano si unisce (il valore di un
    elemento e' la concatenazione dei suoi caratteri, come per la validazione XSD). Restituisce (radice, numero di nodi tolti)."""
    if isinstance(xml, str):
        if re.match(r"\s*<\?xml[^>]*encoding", xml):
            raise XmlNonImportabile("il contenuto e' testo gia' decodificato con una dichiarazione di codifica: passare i byte del "
                                    "file cosi' come sono")
        xml = xml.encode("utf-8")
    try:
        radice = etree.fromstring(xml, parser=etree.XMLParser(resolve_entities=False, no_network=True))
    except etree.XMLSyntaxError as e:
        raise XmlNonImportabile(f"non e' un XML valido: {e}") from None
    except (ValueError, TypeError) as e:
        raise XmlNonImportabile(f"contenuto non leggibile come XML: {e}") from None
    if radice.getroottree().docinfo.doctype:
        raise XmlNonImportabile("DOCTYPE non ammesso nei file telematici")
    nodi = [n for n in radice.iter(etree.Comment, etree.ProcessingInstruction) if n is not radice]
    for n in nodi:
        padre, coda = n.getparent(), n.tail or ""
        if padre is None:
            continue
        prec = n.getprevious()
        if prec is not None:
            prec.tail = (prec.tail or "") + coda
        else:
            padre.text = (padre.text or "") + coda
        n.tail = None
        padre.remove(n)
    return radice, len(nodi)


def _t(el, percorso: str) -> str | None:
    r = el.xpath(percorso, namespaces=NS)
    if len(r) > 1:
        raise XmlNonImportabile(f"elemento duplicato dove ne e' atteso uno solo: {percorso} ({len(r)} volte)")
    if r and len(r[0]):
        raise XmlNonImportabile(f"{percorso}: atteso un valore, trovato un elemento con sottoelementi")
    if r and _letti.get() is not None:
        _letti.get().update(r)
    return (r[0].text or "").strip() if r else None


def _casella(el, percorso: str, cosa: str, avvisi: list[str] | None = None) -> bool:
    """Casella (cm:DatoCB_Type, valori 0 e 1): True se barrata. «0» e' ammesso dall'XSD e vale non barrata (con avviso: la
    riesportazione omette l'elemento); ogni altro valore e' un errore esplicito, mai ignorato."""
    v = _t(el, percorso)
    if v is None:
        return False
    if v == "1":
        return True
    if v == "0":
        if avvisi is not None:
            avvisi.append(f"{cosa}: casella con valore 0 (non barrata): la riesportazione omette l'elemento")
        return False
    raise XmlNonImportabile(f"{cosa}: casella con valore {v!r}, ammessi solo 1 (barrata) o 0 (cm:DatoCB_Type)")


def _cf(v: str | None) -> str | None:
    """Codice fiscale normalizzato in maiuscolo (DatoCF_Type ammette solo lettere maiuscole)."""
    return v.upper() if v else v


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
    # i tipi numerici del tracciato (DatoNP, DatoN, DatoVP: typesDati_v2.xsd) sono solo cifre con l'eventuale virgola decimale:
    # niente segno, esponente, spazi o separatori delle migliaia
    if not re.fullmatch(r"[0-9]+([,.][0-9]+)?", s):
        raise XmlNonImportabile(f"numero non valido: {s!r} (ammesse solo cifre con l'eventuale virgola decimale)")
    t = s.replace(",", ".")
    try:
        Decimal(t)
    except InvalidOperation:
        raise XmlNonImportabile(f"numero non valido: {s!r}") from None
    return t


def _intero(s: str | None, cosa: str) -> int:
    d = Decimal(_dec(s) or "0")
    if d != d.to_integral_value():
        raise XmlNonImportabile(f"{cosa}: atteso un intero, trovato {s!r}")
    return int(d)


def _cifre(s: str | None, cosa: str) -> str | None:
    """Valore che nel tracciato e' solo numerico (anni, numeri di iscrizione, quantita'): una lettera e' un errore."""
    if s is not None and not re.fullmatch(r"\d+", s):
        raise XmlNonImportabile(f"{cosa}: attese solo cifre, trovato {s!r}")
    return s


def _segna(el) -> None:
    """Dichiara letti un elemento e tutti i suoi discendenti (verificati come derivati da altri dati)."""
    if _letti.get() is not None:
        _letti.get().update(el.iter())


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


def _quota(el, percorso: str, cosa: str, avvisi: list[str] | None = None) -> dict | None:
    """Quota {num, den}. Con ``avvisi`` (quote di possesso, PossessoNumeratore cm:DatoVP_Type con due decimali) il numeratore
    decimale si converte esattamente in frazione intera (20,66/100 -> 2066/10000) e l'avviso dice come la riesportazione lo
    riscrive; altrove (cm:DatoNP_Type) e' un errore."""
    n = _t(el, percorso + "Numeratore")
    d = _t(el, percorso + "Denominatore")
    if n is None and d is None:
        return None
    if n is None or d is None:
        raise XmlNonImportabile(f"{cosa}: quota incompleta, manca {'il numeratore' if n is None else 'il denominatore'}")
    den = _intero(d, cosa)
    if avvisi is None:
        num, den_q = _intero(n, cosa), den
    else:
        dn = Decimal(_dec(n) or "0")
        if dn == dn.to_integral_value():
            num, den_q = int(dn), den
        else:
            cifre = -dn.normalize().as_tuple().exponent
            num, den_q = int(dn.scaleb(cifre)), den * 10 ** cifre
            if len(str(den_q)) > 6:                       # PossessoDenominatore: al massimo 6 cifre
                g = gcd(num, den_q)
                num, den_q = num // g, den_q // g
            if len(str(den_q)) > 6:
                raise XmlNonImportabile(f"{cosa}: quota {n}/{d} non rappresentabile con numeratore intero e denominatore di "
                                        "al massimo 6 cifre (PossessoDenominatore)")
    if den_q == 0:
        raise XmlNonImportabile(f"{cosa}: quota {n}/{d} con denominatore zero")
    if num == 0:
        raise XmlNonImportabile(f"{cosa}: quota {n}/{d} nulla")
    if num > den_q:
        raise XmlNonImportabile(f"{cosa}: quota {n}/{d} con numeratore maggiore del denominatore")
    if avvisi is not None and (num, den_q) != (_intero_o_none(n), den):
        avvisi.append(f"{cosa}: quota di possesso {n}/{d} con numeratore decimale importata come {num}/{den_q} (stesso valore); "
                      f"la riesportazione la scrive {num},00/{den_q}, testo diverso dall'originale")
    return {"num": num, "den": den_q}


def _intero_o_none(s: str) -> int | None:
    d = Decimal(_dec(s) or "0")
    return int(d) if d == d.to_integral_value() else None


def _beni_esteri(b, ctx: str) -> dict:
    """``BeniEsteri`` dei quadri EN, EO, EP, EQ, ER -> chiavi ``bene_estero`` e ``imposta_estera`` (esporta.beni_esteri)."""
    out: dict = {}
    if _casella(b, "suc:BeniEsteri/suc:BeneSitoEstero", f"{ctx} BeneSitoEstero"):
        out["bene_estero"] = True
    ie = _dec(_t(b, "suc:BeniEsteri/suc:ImpostaVersataEstero"))
    if ie:
        out["imposta_estera"] = ie
    return out


def _estero(nodo, base: str) -> dict:
    """Residenza estera (Residenza_Estera_Type, figli nel namespace dei dati comuni) -> {codice_stato, stato_federato, localita,
    indirizzo, stato} come la legge l'esportazione (esporta.residenza_estera, frontespizio.residente_estero)."""
    out = {}
    for k, tag in (("codice_stato", "CodiceStatoEstero"), ("stato_federato", "StatoFederato"), ("localita", "LocalitaEstero"),
                   ("indirizzo", "IndirizzoEstero"), ("stato", "StatoEstero")):
        v = _t(nodo, f"{base}/*[local-name()='{tag}']")
        if v:
            out[k] = v
    return out


def _upsert(coll: str, eid: str, campi: dict) -> dict:
    return {"op": "upsert", "coll": coll, "id": eid, "campi": campi}


# ---- quadri EF ed EH: dati DICHIARATI dal professionista (non ricalcolati), letti nelle chiavi che l'esportazione usa
# (quadri_efgh.py, pagamenti.py; supplemento.CHIAVI_DICHIARAZIONE). Tutto il resto del quadro EF e' ricalcolato e confrontato
# con l'originale dopo l'importazione (_confronta_ef).
_SEZ_VI = {"ImpostaIpotecaria": "ipotecaria", "ImpostaCatastale": "catastale", "TassaIpotecaria": "tassa_ipotecaria",
           "ImpostaBollo": "bollo", "ImpostaSuccessione": "successione"}        # pagamenti.TRIBUTI
_CREDITI_EF = (("suc:SezioneI_ImpostaIpotecaria/suc:CreditoImposta", "credito_ipotecaria"),             # EF7
               ("suc:SezioneII_ImpostaCatastale/suc:CreditoImposta", "credito_catastale"),              # EF13
               ("suc:SezioneVBis_ImpostaSuccessione/suc:ImpostaCalcolata/suc:CreditoImposta", "credito_successione"))  # EF18bis c. 4
#: foglie del quadro EF che l'esportazione ricalcola dagli altri dati della pratica (quadri_efgh.quadro_ef, pagamenti.sezione_vi)
_EF_RICALCOLATI = {"ImpostaProporzionale_Imponibile", "ImpostaProporzionale_Imposta", "AgevolazioneG_Valore", "AgevolazioneG_Imposta",
                   "AgevolazioneM_Valore", "AgevolazioneM_Imposta", "PrimaCasa_Numero", "AgevolazionePX_Valore", "PrimaCasa_Imposta",
                   "ImpostaIpotecariaDovuta", "ImpostaIpotecariaDaVersare", "ImpostaCatastaleFissa", "ImpostaCatastaleDovuta",
                   "ImpostaCatastaleDaVersare", "Circoscrizioni_Numero", "Circoscrizioni_Imposta", "ImpostaBollo_CopiaConforme",
                   "CopiaConforme_Importo", "Imposta", "ImpostaDaVersare", "ImpostaNonDovuta", "TotaleDaVersare",
                   "TotaleDaVersare_Sanzioni", "TotaleDaVersare_Interessi"}
_VERSATE_EF = (("suc:SezioneI_ImpostaIpotecaria/suc:ImpostaIpotecariaVersata", "ipotecaria_versata"),          # EF6
               ("suc:SezioneII_ImpostaCatastale/suc:ImpostaCatastaleVersata", "catastale_versata"),            # EF12
               ("suc:SezioneVBis_ImpostaSuccessione/suc:ImpostaCalcolata/suc:ImpostaVersata", "successione_versata"))  # EF18bis c. 3
_EH_SEZIONI_NOTE = {"SezioneI_DichSost"}        # coperta dalla voce generale «dichiarazioni e testamento: da reinserire»
#: sezioni del quadro EH lette nelle chiavi dell'esportazione (prima_casa.sezione_eh, riduzioni_art25.sezione_eh): dopo
#: l'importazione si confrontano con la riesportazione (_confronta_ef)
_EH_SEZIONI_LETTE = ("SezioneII_AgevPrimaCasa", "SezioneIV_AltreAgevRiduz")


def _estremi_reg(el, base: str) -> dict | None:
    """reg:EstremiRegistrazione_Type -> chiavi di ``esporta.estremi_registrazione`` (come per il testamento)."""
    if not el.xpath(base, namespaces=NS):
        return None
    out = {}
    for campo, tag in (("ufficio_registrazione", "UfficioDiRegistrazione"), ("serie", "Serie"),
                       ("numero_registrazione", "NumeroRegistrazione"), ("sottonumero_registrazione", "SottonumeroRegistrazione"),
                       ("data_registrazione", "DataRegistrazione")):
        v = _t(el, f"{base}/reg:{tag}")
        if v:
            out[campo] = _data(v) if campo == "data_registrazione" else v
    return out


def _percorso_relativo(e, sopra) -> str:
    parti = []
    while e is not None and e is not sopra:
        parti.append(etree.QName(e).localname)
        e = e.getparent()
    return "/".join(reversed(parti))


def _ef_eh_dichiarati(d, dichiarazione: dict, avvisi: list[str], non_importato: list[str]) -> None:
    """Sanzioni e interessi (EF Sezione VI), tempistica, rateazione e acconto (EF18ter), crediti d'imposta (EF7, EF13, EF18bis
    col. 4 ed EH Sezione III). Le foglie di EF non lette e non ricalcolate finiscono negli avvisi; le sezioni di EH diverse dalla
    I e dalla III (lette qui) in ``non_importato``."""
    ef = d.xpath("suc:QuadroEF", namespaces=NS)
    if ef:
        ef = ef[0]
        for elem, trib in _SEZ_VI.items():
            for tipo, suff in (("sanzione", "Sanzioni"), ("interessi", "Interessi")):
                v = _dec(_t(ef, f"suc:SezioneVI_SanzioniInteressi/suc:{elem}/suc:{elem}_{suff}"))
                if v is not None:
                    dichiarazione[f"{tipo}_{trib}"] = v
        ic = "suc:SezioneVBis_ImpostaSuccessione/suc:ImpostaCalcolata/suc:"
        tp = _t(ef, ic + "TempisticaPagamento")
        if tp:
            dichiarazione["tempistica_pagamento"] = tp
        pr = _t(ef, ic + "PagamentoRateale")
        if pr:
            dichiarazione["pagamento_rateale"] = _intero(pr, "QuadroEF PagamentoRateale")
        ac = _dec(_t(ef, ic + "Acconto"))
        if ac is not None:
            dichiarazione["acconto"] = ac
        for percorso, chiave in _CREDITI_EF:
            v = _dec(_t(ef, percorso))
            if v is not None:
                dichiarazione[chiave] = v
        # imposte gia' versate con la dichiarazione sostituita (EF6, EF12, EF18bis col. 3): sostitutiva.py
        for percorso, chiave in _VERSATE_EF:
            v = _dec(_t(ef, percorso))
            if v is not None:
                dichiarazione[chiave] = v
                if "codice_sostitutiva" not in dichiarazione:
                    avvisi.append(f"QuadroEF: {percorso.replace('suc:', '')} = {v} in una prima dichiarazione: importato in "
                                  f"{chiave}, ma la riesportazione lo scrive solo per una dichiarazione sostitutiva")
        letti = _letti.get() or set()
        for e in ef.iter():
            if not isinstance(e.tag, str) or len(e) or not (e.text or "").strip() or e in letti:
                continue
            if etree.QName(e).localname not in _EF_RICALCOLATI:
                avvisi.append(f"QuadroEF: {_percorso_relativo(e, ef)} = {(e.text or '').strip()} non importato (dato non "
                              "ricalcolato dal programma): da reinserire, la riesportazione non lo riproduce")
    eh = d.xpath("suc:QuadroEH", namespaces=NS)
    if not eh:
        return
    eh = eh[0]
    righe = [("", s) for s in eh.xpath("suc:PrimoModulo/suc:SezioneIII_CreditoImposta", namespaces=NS)]
    righe += [("_2", s) for s in eh.xpath("suc:Modulo[1]/suc:SezioneIII_CreditoImposta", namespaces=NS)]
    for suff, s in righe:
        for campo, tag in (("credito_tipologia", "TipologiaImposta"), ("credito_imposta", "Imposta")):
            v = _t(s, "suc:" + tag)
            if v:
                dichiarazione[campo + suff] = _dec(v) if campo == "credito_imposta" else v
        for campo, tag in (("credito_acquisto", "RegistrazioneAcquisto"), ("credito_vendita", "RegistrazioneVendita")):
            reg = _estremi_reg(s, "suc:" + tag)
            if reg is not None:
                dichiarazione[campo + suff] = reg
        _casella(s, "suc:FirmaDichiarante", "QuadroEH sezione III FirmaDichiarante", avvisi)   # riscritta dall'esportazione
    for sz in eh.xpath("suc:PrimoModulo/suc:SezioneII_AgevPrimaCasa", namespaces=NS):
        _eh_prima_casa(sz, dichiarazione, avvisi)
    for sz in eh.xpath("suc:PrimoModulo/suc:SezioneIV_AltreAgevRiduz", namespaces=NS):
        _eh_altre_agevolazioni(sz, dichiarazione, avvisi)
    letti = _letti.get() or set()
    for sz in eh.xpath("suc:PrimoModulo/*", namespaces=NS):
        if etree.QName(sz).localname not in _EH_SEZIONI_LETTE:
            continue
        resto = [f"{_percorso_relativo(e, eh)} = {(e.text or '').strip()}" for e in sz.iter()
                 if isinstance(e.tag, str) and not len(e) and (e.text or "").strip() and e not in letti]
        if resto:
            non_importato.append(f"QuadroEH {etree.QName(sz).localname}: campi non importati, da reinserire: " + "; ".join(resto))
    for suff, s in righe:
        resto = [_percorso_relativo(e, eh) for e in s.iter() if isinstance(e.tag, str) and not len(e)
                 and (e.text or "").strip() and e not in letti]
        if resto:
            non_importato.append("QuadroEH sezione III (credito d'imposta): campi non importati, da reinserire: " + "; ".join(resto))
    altri_moduli = eh.xpath("suc:Modulo[position() > 1]/suc:SezioneIII_CreditoImposta", namespaces=NS)
    if altri_moduli:
        non_importato.append(f"QuadroEH sezione III: {len(altri_moduli)} righi di credito oltre il secondo non importati: da reinserire")
    lette_primo = {etree.QName(sz).localname for sz in eh.xpath("suc:PrimoModulo/*", namespaces=NS)} & set(_EH_SEZIONI_LETTE)
    sezioni = sorted({etree.QName(sz).localname for m in eh for sz in m if isinstance(sz.tag, str)}
                     - _EH_SEZIONI_NOTE - {"SezioneIII_CreditoImposta"} - lette_primo)
    for nome in sezioni:
        non_importato.append(f"QuadroEH {nome}: non importata, da reinserire")
    for nome in sorted({etree.QName(sz).localname for sz in eh.xpath("suc:Modulo/*", namespaces=NS)} & lette_primo):
        non_importato.append(f"QuadroEH {nome} nei moduli successivi al primo: non importata, da reinserire")


def _eh_prima_casa(sz, dichiarazione: dict, avvisi: list[str]) -> None:
    """Sezione II del quadro EH (prima casa) -> ``dichiarazione.prima_casa`` (chiavi di prima_casa.CHIAVI_PRIMA_CASA). Gli
    immobili della sezione si ricostruiscono dai beni con codice P, Z, X e si confrontano con l'originale dopo l'importazione."""
    pc: dict = {}
    ctx = "QuadroEH SezioneII_AgevPrimaCasa"
    for chiave, gruppo, voci in (("requisito_comune", "Opzioni", PC.REQUISITO_COMUNE),
                                 ("altra_casa", "AltraCasa", PC.ALTRA_CASA)):
        scelte = [k for k, flag in voci.items() if _casella(sz, f"suc:{gruppo}/suc:{flag}", f"{ctx} {gruppo}/{flag}", avvisi)]
        if len(scelte) > 1:
            raise XmlNonImportabile(f"{ctx}: {gruppo} con piu' caselle barrate ({', '.join(scelte)})")
        if scelte:
            pc[chiave] = scelte[0]
    for chiave, tag in (("nessuna_altra_casa_comune", "FlagNessunaAltraCasaComune"), ("impegno_unione_catastale", "FlagContigui"),
                        ("dichiara_requisiti", "FirmaDichiarante")):
        if _casella(sz, "suc:" + tag, f"{ctx} {tag}", avvisi):
            pc[chiave] = True
    for nodo in sz.xpath("suc:ImmobilePrincipale|suc:ImmobileContiguo|suc:Pertinenza", namespaces=NS):
        _segna(nodo)          # ricostruiti dai beni con agevolazione P/Z/X: confronto con la riesportazione in _confronta_ef
    dichiarazione["prima_casa"] = pc


def _eh_altre_agevolazioni(sz, dichiarazione: dict, avvisi: list[str]) -> None:
    """Sezione IV del quadro EH -> ``dichiarazione.riduzioni_art25`` (riduzioni_art25.CHIAVI_RIDUZIONI): firma, estremi delle
    esenzioni A ed L. Le caselle FlagC/D/E/Q derivano dai codici delle devoluzioni (confronto con la riesportazione); la parte
    Riduzioni (precedente successione o donazione) non e' letta e resta in ``non_importato``."""
    ra: dict = {}
    ctx = "QuadroEH SezioneIV_AltreAgevRiduz"
    for flag in ("FlagC", "FlagD", "FlagE", "FlagQ"):
        _casella(sz, "suc:Agevolazioni/suc:" + flag, f"{ctx} {flag}", avvisi)
    firme = [_casella(sz, p + "/suc:FirmaDichiarante", f"{ctx} FirmaDichiarante", avvisi)
             for p in ("suc:Agevolazioni", "suc:EsenzioneImpostaSuccessione")]
    for chiave, tipo, flag in (("a", "AgevolazTipoA", "FlagA"), ("l", "AgevolazTipoL", "FlagL")):
        base = f"suc:EsenzioneImpostaSuccessione/suc:{tipo}"
        if not sz.xpath(base, namespaces=NS):
            continue
        _casella(sz, f"{base}/suc:{flag}", f"{ctx} {tipo}/{flag}", avvisi)
        voce = {}
        np_ = _t(sz, base + "/suc:NumProtocollo")
        if np_:
            voce["num_protocollo"] = np_
        dt = _data(_t(sz, base + "/suc:Data"))
        if dt:
            voce["data"] = dt
        ra[chiave] = voce
    if any(firme):
        ra["dichiara_requisiti"] = True
    dichiarazione["riduzioni_art25"] = ra


def _foglie(el) -> dict[str, str]:
    """percorso (relativo, con indici) -> testo delle foglie valorizzate."""
    out = {}
    if el is None:
        return out

    def visita(nodo, percorso):
        figli = [f for f in nodo if isinstance(f.tag, str)]
        if not figli:
            if (nodo.text or "").strip():
                out[percorso] = (nodo.text or "").strip()
            return
        visti: dict[str, int] = {}
        for f in figli:
            nome = etree.QName(f).localname       # nomi locali: il prefisso dei namespace dipende dal software produttore
            visti[nome] = visti.get(nome, 0) + 1
            n = sum(1 for g in figli if etree.QName(g).localname == nome)
            visita(f, f"{percorso}/{nome}" + (f"[{visti[nome]}]" if n > 1 else "") if percorso else
                   nome + (f"[{visti[nome]}]" if n > 1 else ""))
    visita(el, "")
    return out


def _importo(s: str | None) -> Decimal | None:
    return Decimal(s.replace(",", ".")) if s else None


def _confronta_ef(radice, ops: list[dict], data_riferimento: date | None) -> list[str]:
    """Riesporta la pratica che si sta per creare e confronta il quadro EF e l'ImportoDaVersare con l'originale: ogni differenza
    e' un avviso esplicito con i due valori (mai una variazione silenziosa degli importi da versare)."""
    from ..servizio import Servizio, nuovi_dati
    from .esporta import ContestoExport, esporta_xml
    orig_d = radice.xpath("//suc:Fornitura/suc:Dichiarazione", namespaces=NS)[0]
    orig_ef = orig_d.find(f"{{{NS['suc']}}}QuadroEF")
    orig_imp = orig_d.xpath("suc:Frontespizio/suc:ImportoDaVersare/text()", namespaces=NS)
    orig_imp = orig_imp[0].strip() if orig_imp else None
    if orig_ef is None and orig_imp is None:
        return []
    dati = nuovi_dati()
    try:
        for i, op in enumerate(ops):
            Servizio._applica(dati, op, "inserito", "gui", i)
        cf_forn = radice.xpath("//tm:Intestazione/tm:CodiceFiscaleFornitore/text()", namespaces=NS)
        es = esporta_xml(dati, ContestoExport(cf_fornitore=cf_forn[0].strip() if cf_forn else "", data_riferimento=data_riferimento,
                                              scopo="bozza_tecnica"))
    except Exception as e:  # noqa: BLE001 - il confronto non deve impedire l'importazione, ma l'esito va detto
        return [f"QuadroEF: confronto con l'originale non eseguito ({type(e).__name__}): verificare a mano ImportoDaVersare "
                f"({orig_imp or 'assente'}) e totali del quadro EF dopo la riesportazione"]
    if es.xml is None:
        tot_orig = orig_ef.findtext(f"{{{NS['suc']}}}TotaleDaVersare") if orig_ef is not None else None
        ef_map = es.mappa.get("quadro:EF") or {}
        tot_nuovo = ef_map.get("totale_da_versare")
        motivo = "; ".join(sorted({f"{e.codice} {e.percorso}" for e in es.errori})[:5]) or "file non generato"
        msg = (f"QuadroEF: riesportazione non completa senza i dati da reinserire ({motivo}); ImportoDaVersare originale "
               f"{orig_imp or 'assente'} non confrontabile")
        if (_importo(tot_orig) or Decimal(0)) != (_importo(tot_nuovo) or Decimal(0)):
            msg += f"; TotaleDaVersare (EF19) originale {tot_orig or 'assente'}, ricalcolato {tot_nuovo or 'non determinato'}"
        return [msg]
    nuovo = etree.fromstring(es.xml)
    nuovo_d = nuovo.xpath("//suc:Fornitura/suc:Dichiarazione", namespaces=NS)[0]
    nuovo_imp = nuovo_d.xpath("suc:Frontespizio/suc:ImportoDaVersare/text()", namespaces=NS)
    nuovo_imp = nuovo_imp[0].strip() if nuovo_imp else None
    nuovo_ef = nuovo_d.find(f"{{{NS['suc']}}}QuadroEF")
    out_eh = []
    for nome in _EH_SEZIONI_LETTE:
        # sezioni del quadro EH importate: immobili e caselle derivate sono ricostruiti, ogni differenza e' un avviso
        xp = f"suc:QuadroEH/suc:PrimoModulo/suc:{nome}"
        o, n_ = orig_d.xpath(xp, namespaces=NS), nuovo_d.xpath(xp, namespaces=NS)
        if not o:
            continue
        a, b = _foglie(o[0]), _foglie(n_[0] if n_ else None)
        diff = [f"{k}: originale {a.get(k, 'assente')}, riesportato {b.get(k, 'assente')}" for k in sorted(a.keys() | b.keys())
                if a.get(k) != b.get(k)]
        if diff:
            out_eh.append(f"QuadroEH {nome} riesportata diversa dall'originale: " + "; ".join(diff))
    if orig_ef is not None and nuovo_ef is None:
        motivi = "; ".join(m.messaggio for m in es.quadri_mancanti if m.percorso == "quadro[EF]") or "non generato"
        tot_orig = orig_ef.findtext(f"{{{NS['suc']}}}TotaleDaVersare") or "assente"
        return [f"QuadroEF non ricalcolabile con i dati importati ({motivi}): originale ImportoDaVersare {orig_imp or 'assente'}, "
                f"TotaleDaVersare {tot_orig}; ricalcolato ImportoDaVersare {nuovo_imp or 'assente'}"] + out_eh
    a, b = _foglie(orig_ef), _foglie(nuovo_ef)
    diff =[f"{k}: originale {a.get(k, 'assente')}, ricalcolato {b.get(k, 'assente')}" for k in sorted(a.keys() | b.keys())
            if a.get(k) != b.get(k)]
    if orig_imp == nuovo_imp and not diff:
        return out_eh
    out = out_eh
    if orig_imp != nuovo_imp:
        out.append(f"ImportoDaVersare ricalcolato diverso dall'originale: originale {orig_imp or 'assente'}, ricalcolato "
                   f"{nuovo_imp or 'assente'}: verificare i dati prima di riesportare")
    if diff:
        out.append("QuadroEF ricalcolato diverso dall'originale: " + "; ".join(diff))
    return out


def importa_xml(xml: bytes, *, data_riferimento: date | None = None) -> dict:
    """``data_riferimento``: data della riesportazione di confronto del quadro EF (None = oggi, come la riesportazione reale)."""
    radice, tolti = _analizza(xml)
    token = _letti.set(set())
    try:
        r = _importa_xml(radice)
    finally:
        _letti.reset(token)
    if tolti:
        r["avvisi"].insert(0, f"{tolti} commenti o istruzioni di elaborazione tolti dal file: il testo che separavano e' stato "
                              "unito al valore dell'elemento; la riesportazione non li riproduce")
    r["avvisi"] += _confronta_ef(radice, r["operazioni"], data_riferimento)
    return r


def _elenco_foglie(el, sopra) -> str:
    """«percorso = valore» di tutte le foglie valorizzate di ``el`` (per ``non_importato``: nulla si perde in silenzio)."""
    voci = [f"{_percorso_relativo(e, sopra)} = {(e.text or '').strip()}" for e in el.iter()
            if isinstance(e.tag, str) and not len(e) and (e.text or "").strip()]
    return "; ".join(voci) if voci else "nessun campo valorizzato"


def _importa_xml(radice) -> dict:
    """Legge un file telematico SUC13. Restituisce ``{"operazioni", "titolo", "importato", "non_importato", "avvisi"}``."""
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
    cf_def = _cf(_t(fr, "suc:CodiceFiscaleDefunto"))
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
    # tipo di dichiarazione (scelta XSD fra PrimaDichiarazione e DichiarazioneSostitutiva + EstremiPrimaDichiarazione):
    # chiavi di sostitutiva.py, come le scrive l'esportazione (opzioni.tipo_dichiarazione e dichiarazione.codice_sostitutiva...)
    td = "suc:TipoDichiarazione/"
    tipo_dichiarazione = None
    prima = _casella(fr, td + "suc:PrimaDichiarazione", "frontespizio PrimaDichiarazione")
    cod_sost = _t(fr, td + "suc:DichiarazioneSostitutiva")
    if cod_sost is not None:
        if prima:
            raise XmlNonImportabile("frontespizio: PrimaDichiarazione e DichiarazioneSostitutiva entrambe presenti")
        if cod_sost not in ("1", "2", "3"):
            raise XmlNonImportabile(f"frontespizio DichiarazioneSostitutiva: codice {cod_sost!r} non ammesso (1, 2 o 3)")
        tipo_dichiarazione = "sostitutiva"
        dichiarazione["codice_sostitutiva"] = cod_sost
        for chiave, tag in (("prima_anno", "Anno"), ("prima_volume", "Volume"), ("prima_numero", "Numero")):
            v = _t(fr, td + "suc:EstremiPrimaDichiarazione/suc:" + tag)
            if v:
                dichiarazione[chiave] = v
        avvisi.append(f"dichiarazione sostitutiva (codice {cod_sost}): importati codice, estremi della prima dichiarazione e "
                      "imposte gia' versate (EF6, EF12, EF18bis col. 3)" + ("; il codice 3 non e' riesportabile da questa "
                                                                             "versione" if cod_sost == "3" else ""))
    elif not prima:
        raise XmlNonImportabile("frontespizio: tipo di dichiarazione assente (PrimaDichiarazione o DichiarazioneSostitutiva)")
    elif fr.xpath(td + "suc:EstremiPrimaDichiarazione", namespaces=NS):
        raise XmlNonImportabile("frontespizio: EstremiPrimaDichiarazione in una prima dichiarazione")
    dev = td + "suc:Devoluzione/suc:"
    if _casella(fr, dev + "DevoluzionePerLegge", "frontespizio DevoluzionePerLegge", avvisi):
        dichiarazione["devoluzione_per_legge"] = True
    # altre caselle del frontespizio (frontespizio.py: legge estera, eventi eccezionali, opzione art. 24-bis, inventario,
    # residenza estera del defunto)
    if _casella(fr, dev + "LeggeEstera", "frontespizio LeggeEstera", avvisi):
        dichiarazione["legge_estera"] = True
    ev = _t(fr, td + "suc:EventiEccezionali")
    if ev:
        dichiarazione["eventi_eccezionali"] = ev
    do = _data(_t(fr, td + "suc:DataOpzione"))
    if do:
        dichiarazione["data_opzione"] = do
    if _casella(fr, "suc:Beneficiari/suc:AccettazioneConBeneficioInventario", "frontespizio AccettazioneConBeneficioInventario",
                avvisi):
        dichiarazione["beneficio_inventario"] = True
    rd = _t(fr, "suc:DatiDefunto/suc:UlterioriDati/suc:ResidenzaEstera")
    if rd:
        dichiarazione["residenza_estera_defunto"] = rd
    if _casella(fr, dev + "DevoluzionePerTestamento", "frontespizio DevoluzionePerTestamento", avvisi):
        avvisi.append("devoluzione per testamento: estremi importati dal frontespizio; verificare dichiarazioni EH e riacquisire il testamento")
        dichiarazione["devoluzione_per_testamento"] = True
        base_test = "suc:TipoDichiarazione/suc:Devoluzione/suc:Testamento"
        testamento = {}
        if _casella(fr, base_test + "/suc:TestamentoEstero", "frontespizio TestamentoEstero", avvisi):
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
    if _casella(fr, "suc:FirmaModello/suc:FirmaDichiarante", "frontespizio FirmaModello/FirmaDichiarante", avvisi):
        dichiarazione["firma_dichiarante"] = True
    iban = _t(fr, "suc:Versamento/reg:IBAN")
    if iban:
        dichiarazione["versamento"] = {"iban": iban, "cf_titolare": _cf(_t(fr, "suc:Versamento/reg:CodiceFiscaleTitolareCC"))}

    # ---- eredi (EA): l'ordine del file e' quello dei riferimenti Rigo/Modulo
    persona_di_rigo: dict[tuple[int, int], str] = {}
    persona_di_cf: dict[str, str] = {}
    tel_persone: dict[str, dict] = {}
    cf_tipo_visti: dict[tuple, str] = {}
    n = 0
    for m, mod in enumerate(d.xpath("suc:QuadroEA/suc:Modulo", namespaces=NS), 1):
        for r, s in enumerate(mod.xpath("suc:Soggetto", namespaces=NS), 1):
            n += 1
            cf = _cf(_t(s, "suc:CodiceFiscale"))
            pid = f"p_erede{n:03d}"
            ts, gp = _t(s, "suc:TipoSoggetto"), _t(s, "suc:GradoParentela")
            # lo stesso soggetto puo' stare su piu' righi solo con tipi soggetto diversi (annotazioni XSD di CodiceFiscale e
            # TipoSoggetto, es. erede e legatario): un rigo ripetuto con lo stesso tipo e' un errore, non si fonde
            if (cf, ts) in cf_tipo_visti:
                raise XmlNonImportabile(f"QuadroEA modulo {m} rigo {r}: codice fiscale gia' presente nel quadro EA con lo stesso tipo "
                                        f"soggetto ({cf_tipo_visti[(cf, ts)]})")
            cf_tipo_visti[(cf, ts)] = f"modulo {m} rigo {r}"
            campi = {"ruolo": "legatario" if ts == "2" else "erede", "codice_fiscale": cf,
                     **_anagrafica(s, "suc:DatiAnagrafici")}
            if ts:
                campi["tipo_soggetto"] = ts
            tp: dict = {}
            if _casella(s, "suc:PortatoreHandicap", f"QuadroEA modulo {m} rigo {r} PortatoreHandicap", avvisi):
                tp["portatore_handicap"] = True
            # successione per rappresentazione e residenza estera (esporta.rappresentazione, esporta.residenza_estera)
            rc = _cf(_t(s, "suc:SuccessionePerRappresentazione/suc:CodiceFiscaleSoggettoRappresentato"))
            rg = _t(s, "suc:SuccessionePerRappresentazione/suc:GradoParentela")
            if rc:
                tp["rappresentato_cf"] = rc
            if rg:
                tp["rappresentato_grado"] = rg
            if s.xpath("suc:ResidenzaEstera", namespaces=NS):
                tp["residenza_estera"] = _estero(s, "suc:ResidenzaEstera")
            if tp:
                tel_persone[pid] = tp
            if gp:
                campi["grado_parentela"] = gp
                campi["relazione_con_defunto"] = gp
                if gp == "35" and ts != "2":
                    avvisi.append(f"{cf}: grado 35 (estraneo), importato come erede; se e' un legatario cambiarne il ruolo")
            ops.append(_upsert("persone", pid, campi))
            persona_di_rigo[(m, r)] = pid
            persona_di_cf.setdefault(cf, pid)
    importato["eredi"] = n

    # ---- presentatore
    pres = fr.xpath("suc:Presentatore", namespaces=NS)
    if pres:
        p = pres[0]
        cf = _cf(_t(p, "suc:CodiceFiscale"))
        anagrafica_pres = _anagrafica(p, "suc:DatiAnagrafici")
        dichiarazione["presentatore"] = {"codice_carica": _t(p, "suc:CodiceCarica"), "telefono": _t(p, "suc:Telefono"),
                                         "email": _t(p, "suc:Email"),
                                         "data_decorrenza": _data(_t(p, "suc:DecorrenzaTerminePresentazione")),
                                         "rappresentato_cf": _cf(_t(p, "suc:CodiceFiscaleRappresentato"))}
        if p.xpath("suc:ResidenteEstero", namespaces=NS):
            dichiarazione["presentatore"]["residente_estero"] = _estero(p, "suc:ResidenteEstero")
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
    campi_beni: dict[str, dict] = {}                          # id bene -> campi importati (per la ricostruzione del quadro EI)
    posizione_bene: dict[tuple[str, int, int], str] = {}      # (quadro, modulo, rigo) -> id bene
    devoluzioni: list[dict] = []
    tel_dev: dict[str, dict] = {}

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
            did = f"d_import{len(devoluzioni)+1:06d}"
            # agevolazioni (P, X, Y, Z, A, C, D, E, G, H, M, N, L, Q, R, F) e riduzioni art. 25 c. 1 (1-5) della riga: chiavi
            # lette dall'esportazione (supplemento.CHIAVI["devoluzioni"]; prima_casa, agevolazioni, riduzioni_art25)
            extra = {}
            for chiave, el_ in (("agevolazioni", "Agevolazioni"), ("riduzioni", "Riduzioni")):
                v = _t(dv, "suc:" + el_)
                if v:
                    extra[chiave] = v
            if extra:
                tel_dev[did] = extra
            devoluzioni.append(_upsert("devoluzioni", did, campi))

    def continuazione(b, tag, corrente, attesa, ctx):
        if attesa:
            if any(etree.QName(e).localname != tag for e in b):
                raise XmlNonImportabile(f"{ctx}: rigo di continuazione con dati di un nuovo bene")
            if not b.xpath(f"suc:{tag}/suc:Devoluzione", namespaces=NS):
                raise XmlNonImportabile(f"{ctx}: continuazione senza beneficiari")
            devoluzioni_di(corrente, b, tag, "Devoluzione", ctx)
        return _casella(b, f"suc:{tag}/suc:Continuazione", f"{ctx} Continuazione", avvisi)

    def luogo(nodo, campi: dict, tavolare: bool = False):
        if tavolare:
            voci = (("provincia", "Provincia"), ("comune", "ComuneAmministrativo"), ("codice_comune", "CodiceComune"),
                    ("indirizzo", "Indirizzo"), ("codice_comune_amministrativo", "CodiceComuneAmministrativo"),
                    ("comune_catastale", "ComuneCatastale"), ("codice_comune_catastale", "CodiceComuneCatastale"))
            percorsi = [(campo, f"suc:LuogoTavolare/reg:{tag}") for campo, tag in voci]
        else:
            percorsi = [(campo, "suc:Luogo/" + tag) for campo, tag in (
                ("provincia", "reg:Provincia"), ("comune", "reg:Italia/reg:ComuneAmministrativo"),
                ("codice_comune", "reg:Italia/reg:CodiceComune"), ("indirizzo", "reg:Italia/reg:Indirizzo"),
                ("codice_comune_amministrativo", "reg:Italia/reg:CodiceComuneAmministrativo"))]
        for campo, percorso in percorsi:
            v = _t(nodo, percorso)
            if v:
                campi[campo] = v
        if tavolare and campi.get("provincia") not in PROVINCE_TAVOLARI:
            # le altre province del catasto tavolare (BL, UD, BS, VI) richiedono il flag sistema_tavolare, che
            # l'esportazione non serializza: il file non sarebbe ricreato
            raise XmlNonImportabile(f"provincia {campi.get('provincia')!r} dei quadri EL/EM: l'importazione ricrea solo "
                                    f"le province {', '.join(PROVINCE_TAVOLARI)}")

    def possesso(nodo, campi: dict, ctx: str):
        q = _quota(nodo, "suc:Possesso/suc:Possesso", ctx, avvisi)
        if q:
            campi["quota_defunto"] = q
        dr = _t(nodo, "suc:CodiceDiritto_P")
        if dr:
            campi["diritto"] = dr
        v = _t(nodo, "suc:Valore")
        if v:
            campi["valore"] = _dec(v)

    def scorri(quadro: str, elem: str, sigla: str, costruisci, chiave=None, descr_ordine: str = "") -> int:
        """Righi di un quadro di beni, con le continuazioni delle devoluzioni; ``costruisci(rigo, ctx)`` -> (campi, tel).
        ``chiave(campi, tel, id)`` e' la chiave con cui l'esportazione ordina i righi: se il file ha un ordine diverso si importa
        comunque, con un avviso (la riesportazione riscrive i righi nel proprio ordine, con nuovi riferimenti modulo/rigo)."""
        k = 0
        attesa, bid = False, None
        chiavi = []
        for m, mod in enumerate(d.xpath(f"suc:Quadro{quadro}/suc:Modulo", namespaces=NS), 1):
            for r, b in enumerate(mod.xpath(f"suc:{elem}", namespaces=NS), 1):
                ctx = f"Quadro{quadro} modulo {m} rigo {r}"
                precedente = attesa
                attesa = continuazione(b, f"Devoluzione{quadro}", bid, attesa, ctx)
                if precedente:
                    posizione_bene[(quadro, m, r)] = bid
                    continue
                k += 1
                bid = f"b_{sigla}{k:03d}"
                campi, tel = costruisci(b, ctx)
                ops.append(_upsert("beni", bid, campi))
                campi_beni[bid] = campi
                if tel:
                    tel_beni[bid] = tel
                posizione_bene[(quadro, m, r)] = bid
                devoluzioni_di(bid, b, f"Devoluzione{quadro}", "Devoluzione", ctx)
                if chiave:
                    chiavi.append(chiave(campi, tel or {}, bid))
        if attesa:
            raise XmlNonImportabile(f"Quadro{quadro}: manca il rigo di continuazione")
        if chiavi != sorted(chiavi):
            spostati = sum(1 for a, b in zip(chiavi, sorted(chiavi)) if a != b)
            avvisi.append(f"Quadro{quadro}: i righi del file non sono nell'ordine con cui la riesportazione li riscrive "
                          f"({descr_ordine}): {spostati} beni su {len(chiavi)} cambiano posizione e riferimenti modulo/rigo "
                          "(anche quelli richiamati nel quadro ED); i dati non cambiano")
        return k

    def immobile(tipo: str, tavolare: bool):
        terreno = tipo == "terreno"

        def costruisci(b, ctx):
            campi: dict = {"tipo": tipo}
            tel: dict = {}
            luogo(b, campi, tavolare)
            nodo = ("DatiTerreni" if terreno else "DatiFabbricati") + ("Tavolare" if tavolare else "")
            for campo, tag in (("sezione", "Sezione"), ("foglio", "Foglio"), ("particella", "Particella"),
                               ("subalterno", "Subalterno")):
                v = _t(b, f"suc:{nodo}/reg:DatiCatastali/reg:{tag}")
                if v:
                    campi[campo] = v
            dati = f"suc:{nodo}/reg:{'DatiTerreni' if terreno else 'DatiFabbricati'}"
            if terreno:
                v = _t(b, f"{dati}/reg:Natura")
                if v:
                    campi["natura"] = v
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
                for campo, tag in (("categoria", "CategoriaCatastale"), ("classe", "Classe"),
                                   ("sezione", "SezioneUrbana"), ("zona_censuaria", "ZonaCensuaria")):
                    v = _t(b, f"{dati}/reg:{tag}")
                    if v:
                        campi[campo] = v
                for campo, tag in (("consistenza", "Consistenza"), ("rendita", "RenditaCatastale")):
                    v = _dec(_t(b, f"{dati}/reg:{tag}"))
                    if v:
                        campi[campo] = v
                if not tavolare:
                    # diritto di abitazione del coniuge superstite (codici 1-8): campo del modello comune; l'esportazione
                    # non lo supporta ancora e lo dichiara (non_supportato), quindi la riesportazione completa si blocca
                    da = _t(b, "suc:DirittoAbitazione")
                    if da:
                        campi["diritto_abitazione"] = da
                        avvisi.append(f"{ctx}: diritto di abitazione del coniuge superstite (codice {da}) importato; la "
                                      "riesportazione non lo supporta ancora e non genera il file finche' non e' gestito")
                    # immobili graffati (fino a 4 per rigo; l'esportazione non scrive ContinuazioneGraffati)
                    if b.xpath("suc:Graffati/suc:ContinuazioneGraffati", namespaces=NS):
                        raise XmlNonImportabile(f"{ctx}: piu' di quattro immobili graffati (ContinuazioneGraffati) non supportato")
                    voci = []
                    for g in b.xpath("suc:Graffati/suc:ImmobiliGraffati", namespaces=NS):
                        v = {}
                        for campo, tag in (("sezione", "SezioneUrbana"), ("foglio", "Foglio"), ("particella", "Particella"),
                                           ("subalterno", "Subalterno")):
                            t = g.xpath(f"*[local-name()='DatiCatastali']/*[local-name()='{tag}']")
                            if t and (t[0].text or "").strip():
                                v[campo] = t[0].text.strip()
                                _segna(t[0])
                        voci.append(v)
                    if voci:
                        tel["graffati"] = voci
            if tavolare:
                voci = [("partita_tavolare", "PartitaTavolare"), ("corpo_tavolare", "CorpoTavolare")]
                if not terreno:
                    voci.append(("porzione_materiale", "PorzioneMateriale"))
                for campo, tag in voci:
                    v = _t(b, f"{dati}/reg:{tag}")
                    if v:
                        campi[campo] = v
            else:        # caselle che generano il quadro EI (non previste dai quadri tavolari)
                for campo, tag in (("discordanza_intestatario", "DiscordanzaDatiIntestatario"),
                                   ("passaggi_senza_atti_legali", "PassaggiSenzaAttiLegali")):
                    v = _t(b, "suc:" + tag)
                    if v:
                        if v != "1":
                            raise XmlNonImportabile(f"{ctx}: {tag}: atteso 1, trovato {v!r}")
                        campi[campo] = "si"
            possesso(b, campi, ctx)
            return campi, tel
        return costruisci

    def disponibilita(b, ctx):
        campi = {"tipo": "disponibilita_finanziaria"}
        tc = _t(b, "suc:TipoCespite")
        ds = _t(b, "suc:Descrizione")
        if ds:
            campi["descrizione"] = ds
        possesso(b, campi, ctx)
        return campi, {**({"tipo_cespite": tc} if tc else {}), **_beni_esteri(b, ctx)}

    def azienda(b, ctx):
        campi = {"tipo": "azienda"}
        for campo, tag in (("descrizione", "Denominazione"), ("codice_fiscale_emittente", "CodiceFiscale")):
            v = _t(b, f"suc:Descrizione/suc:{tag}")
            if v:
                campi[campo] = _cf(v) if campo == "codice_fiscale_emittente" else v
        possesso(b, campi, ctx)
        if "quota_defunto" not in campi:
            campi["quota_defunto"] = {"num": 1, "den": 1}
            avvisi.append(f"{ctx}: il quadro EN non riporta la quota di possesso del defunto: assunta 1/1, da verificare")
        return campi, _beni_esteri(b, ctx)

    def titolo_eo(b, ctx):
        campi = {"tipo": "titolo"}
        for campo, tag in (("tipo_titolo", "TipoTitolo"), ("codice_fiscale_emittente", "CodiceFiscale"),
                           ("quantita", "Quantita"), ("codice_titolo", "CodiceTitolo"), ("descrizione", "Descrizione"),
                           ("tipo_documento", "TipoDocumento")):
            v = _t(b, "suc:" + tag)
            if v:
                campi[campo] = v
        _cifre(campi.get("quantita"), f"{ctx}: Quantita")
        if campi.get("codice_fiscale_emittente"):
            campi["codice_fiscale_emittente"] = _cf(campi["codice_fiscale_emittente"])
        dt = _data(_t(b, "suc:DataDocumento"))
        if dt:
            campi["data_documento"] = dt
        q = _quota(b, "suc:Possesso/suc:Possesso", ctx, avvisi)
        if q:
            campi["quota_defunto"] = q
        v = _dec(_t(b, "suc:Possesso/suc:Valore"))
        ve = _dec(_t(b, "suc:Possesso/suc:ValoreEsente"))
        if v and ve:
            raise XmlNonImportabile(f"{ctx}: Valore e ValoreEsente insieme (l'uno esclude l'altro, PossessoEO_Type)")
        if v:
            campi["valore"] = v
        if ve:
            # l'esportazione scrive ValoreEsente per il tipo 3 (sempre) e per il tipo 4 con la casella «valore esente»
            # (XSD PossessoEO_Type: ValoreEsente vietato solo per i tipi 1 e 2)
            campi["valore"] = ve
            if campi.get("tipo_titolo") != "3":
                campi["valore_esente"] = "si"
            if campi.get("tipo_titolo") not in ("3", "4"):
                # il valore resta esente: la riesportazione segnala l'incoerenza invece di trasformarlo in imponibile
                avvisi.append(f"{ctx}: ValoreEsente {ve} con tipo titolo {campi.get('tipo_titolo')!r}: per i tipi 1 e 2 il "
                              "valore esente non e' ammesso (XSD PossessoEO_Type): importato come esente, la riesportazione "
                              "lo segnala; verificare il tipo titolo")
        dr = _t(b, "suc:CodiceDiritto_C")
        if dr:
            campi["diritto"] = dr
        return campi, _beni_esteri(b, ctx)

    def mezzo(tipo: str, voci: tuple):
        def costruisci(b, ctx):
            campi = {"tipo": tipo}
            for campo, percorso, numerico in voci:
                v = _t(b, "suc:Tipo/suc:" + percorso)
                if v:
                    campi[campo] = _cifre(v, f"{ctx}: {percorso}") if numerico else v
            possesso(b, campi, ctx)
            return campi, _beni_esteri(b, ctx)
        return costruisci

    aeromobile = mezzo("aeromobile", (
        ("marca_modello", "MarcaModello", False), ("anno_costruzione", "AnnoCostruzione", True),
        ("nazionalita", "Nazionalita", False), ("anno_immatricolazione", "AnnoImmatricolazione", True),
        ("numero_immatricolazione", "NumeroImmatricolazione", True)))
    nave = mezzo("nave", (
        ("tipo_unita", "TipoUnita", False), ("nazionalita", "Nazionalita", False),
        ("sigla_ufficio_iscrizione", "SiglaUfficioIscrizione", False), ("anno_iscrizione", "AnnoIscrizione", True),
        ("numero_iscrizione", "NumeroIscrizione", True), ("anno_costruzione", "AnnoCostruzione", True),
        ("lunghezza", "Dimensione/suc:Lunghezza", True), ("stazza", "Dimensione/suc:Stazza", True)))

    # chiavi di ordinamento dei righi dell'esportazione (esporta.py, costruzione dei quadri dei beni)
    def k_imm(c, t, bid):
        return _chiave_immobile({**c, "id": bid})
    o_imm = "comune, sezione, foglio, particella, subalterno"
    importato["terreni"] = scorri("EB", "Terreni", "eb", immobile("terreno", False), k_imm, o_imm)
    importato["fabbricati"] = scorri("EC", "Fabbricati", "ec", immobile("fabbricato", False), k_imm, o_imm)
    importato["disponibilita_finanziarie"] = scorri(
        "ER", "Rendite", "er", disponibilita,
        lambda c, t, bid: (str(t.get("tipo_cespite") or ""), str(c.get("descrizione") or ""), bid), "tipo cespite, descrizione")
    altri = (("terreni_tavolari", scorri("EL", "TerreniTavolare", "el", immobile("terreno", True), k_imm, o_imm)),
             ("fabbricati_tavolari", scorri("EM", "FabbricatiTavolare", "em", immobile("fabbricato", True), k_imm, o_imm)),
             ("aziende", scorri("EN", "Aziende", "en", azienda,
                                lambda c, t, bid: (str(c.get("descrizione") or ""), bid), "denominazione")),
             ("titoli", scorri("EO", "Titoli", "eo", titolo_eo,
                               lambda c, t, bid: (str(c.get("tipo_titolo") or ""), str(c.get("descrizione") or ""), bid),
                               "tipo titolo, descrizione")),
             ("aeromobili", scorri("EP", "Aeromobili", "ep", aeromobile,
                                   lambda c, t, bid: (str(c.get("marca_modello") or ""), bid), "marca e modello")),
             ("navi", scorri("EQ", "Navi", "eq", nave,
                             lambda c, t, bid: (str(c.get("numero_iscrizione") or ""), bid), "numero di iscrizione")))
    quadri_extra = [q for q, (_, n) in zip(("EL", "EM", "EN", "EO", "EP", "EQ"), altri) if n]
    importato.update({nome: n for nome, n in altri if n})

    # ---- voltura (EI): ricostruita dall'esportazione dai flag dei beni; qui si leggono gli estremi e si verifica la coerenza
    flaggati = [bid for bid, c in campi_beni.items() if c.get("discordanza_intestatario") or c.get("passaggi_senza_atti_legali")]
    ei = d.xpath("suc:QuadroEI_new", namespaces=NS)
    ei_vecchio = d.xpath("suc:QuadroEI", namespaces=NS)
    for q in ei_vecchio:
        # quadro EI del modello precedente (file di altri programmi o di versioni passate): l'XSD SUC13 vigente prevede solo
        # QuadroEI_new. Gli altri quadri si importano; il contenuto di questo resta elencato per il reinserimento
        avvisi.append("QuadroEI del modello precedente (l'XSD vigente prevede solo QuadroEI_new): non importato; i suoi dati "
                      "sono elencati fra i non importati e vanno reinseriti nella voltura (estremi di trascrizione/registrazione "
                      "dei beni)")
        _segna(q)
    if ei and not flaggati:
        raise XmlNonImportabile("QuadroEI_new senza immobili con discordanza dati intestatario o passaggi senza atti legali: "
                                "il quadro si ricostruisce da quelle caselle e non sarebbe riprodotto")
    if flaggati and not ei and ei_vecchio:
        avvisi.append(f"{len(flaggati)} immobili con discordanza dati intestatario o passaggi senza atti legali: la voltura (QuadroEI_new) "
                      "va completata con gli estremi del quadro EI precedente prima di riesportare")
    elif flaggati and not ei:
        raise XmlNonImportabile("immobili con discordanza dati intestatario o passaggi senza atti legali ma quadro "
                                "QuadroEI_new assente: la riesportazione lo aggiungerebbe")
    if ei:
        ei = ei[0]
        con_discordanza = [bid for bid in flaggati if campi_beni[bid].get("discordanza_intestatario")]
        nel_primo = ei.xpath("suc:PrimoModulo", namespaces=NS)
        if len(nel_primo) != 1:
            raise XmlNonImportabile("QuadroEI_new: PrimoModulo assente")
        primo = nel_primo[0]
        anag = ("Cognome", "Nome", "Sesso", "DataNascita", "ComuneNascita", "ProvinciaNascita")
        fr_pres = fr.xpath("suc:Presentatore", namespaces=NS)
        if not fr_pres or not primo.xpath("suc:Presentatore", namespaces=NS):
            raise XmlNonImportabile("QuadroEI_new: presentatore assente")

        def firmatario(nodo, annidato: str):
            return [_t(nodo, annidato + "reg:" + t) for t in anag] + [_cf(_t(nodo, "suc:CodiceFiscale")), _t(nodo, "suc:CodiceCarica")]
        if firmatario(primo.xpath("suc:Presentatore", namespaces=NS)[0], "") != firmatario(fr_pres[0], "suc:DatiAnagrafici/"):
            raise XmlNonImportabile("QuadroEI_new: il presentatore e' diverso da quello del frontespizio")
        passaggi = any(campi_beni[bid].get("passaggi_senza_atti_legali") for bid in flaggati)
        atti = primo.xpath("suc:SezioneI_AttiLegali", namespaces=NS)
        if bool(atti) != passaggi:
            raise XmlNonImportabile("QuadroEI_new: la sezione I (atti legali) non corrisponde alle caselle 'passaggi senza "
                                    "atti legali' degli immobili")
        if atti and (_t(atti[0], "suc:FlagAttiLegali") != "1" or _t(atti[0], "suc:FirmaDichiarante") != "1"):
            raise XmlNonImportabile("QuadroEI_new: sezione I (atti legali) senza flag e firma")
        sezioni = primo.xpath("suc:SezioneII_DatiIntestatario", namespaces=NS) + ei.xpath(
            "suc:Modulo/suc:SezioneII_DatiIntestatario", namespaces=NS)
        if len(sezioni) != len(con_discordanza):
            raise XmlNonImportabile(f"QuadroEI_new: {len(sezioni)} sezioni II per {len(con_discordanza)} immobili con "
                                    "discordanza dati intestatario")
        trovati: list[str] = []
        for i, s in enumerate(sezioni, 1):
            ctx = f"QuadroEI_new sezione II n. {i}"
            imm = [_t(s, "suc:Immobile/" + p) for p in (
                "suc:TipoCatasto", "suc:Luogo/suc:Provincia", "suc:Luogo/suc:ComuneAmministrativo",
                "suc:Luogo/suc:CodiceComune", "suc:Luogo/suc:CodiceComuneAmministrativo", "suc:DatiCatastali/reg:Foglio",
                "suc:DatiCatastali/reg:Particella", "suc:DatiCatastali/reg:Subalterno", "suc:SezioneUrbana")]
            candidati = []
            for bid in con_discordanza:
                c = campi_beni[bid]
                terreno = c["tipo"] == "terreno"
                chiave = ["T" if terreno else "U", c.get("provincia"), c.get("comune"), c.get("codice_comune"),
                          c.get("codice_comune_amministrativo"), c.get("foglio"), c.get("particella"), c.get("subalterno"),
                          None if terreno else c.get("sezione")]
                if chiave == imm and bid not in trovati:
                    candidati.append(bid)
            if len(candidati) != 1:
                raise XmlNonImportabile(f"{ctx}: l'immobile indicato corrisponde a {len(candidati)} beni con discordanza "
                                        "dati intestatario (atteso esattamente uno)")
            bid = candidati[0]
            trovati.append(bid)
            if i == 1 and _t(s, "suc:FirmaDichiarante") != "1":
                raise XmlNonImportabile(f"{ctx}: firma del dichiarante assente")
            estremi = {}
            for campo, nodo, voci in (
                    ("estremi_trascrizione", "EstremiTrascrizione", (("ufficio", "UfficioTrascrizione", False),
                                                                    ("registro_particolare", "RegistroParticolare", True),
                                                                    ("anno", "Anno", True))),
                    ("estremi_registrazione", "EstremiRegistrazione", (("ufficio", "UfficioTerritoriale", False),
                                                                      ("anno", "Anno", True), ("volume", "Volume", True),
                                                                      ("numero", "Numero", True)))):
                elenco = []
                for e in s.xpath(f"suc:{nodo}", namespaces=NS):
                    voce = {}
                    for chiave_voce, tag, numerico in voci:
                        v = _t(e, "suc:" + tag)
                        if not v:
                            raise XmlNonImportabile(f"{ctx}: {nodo}/{tag} assente")
                        voce[chiave_voce] = _cifre(v, f"{ctx}: {tag}") if numerico else v
                    elenco.append(voce)
                if elenco:
                    estremi[campo] = elenco
            if not estremi:
                raise XmlNonImportabile(f"{ctx}: nessun estremo di trascrizione o registrazione")
            tel_beni.setdefault(bid, {}).update(estremi)
        if trovati != sorted(trovati):
            avvisi.append("QuadroEI_new: le sezioni II non sono nell'ordine dei beni con cui la riesportazione le riscrive: "
                          "cambia solo l'ordine delle sezioni, non i dati")
        importato["voltura"] = len(sezioni)

    # dati dell'azienda nel quadro EH (rigo EH9), necessari alla riesportazione del quadro EN
    base_az = "suc:QuadroEH/suc:PrimoModulo/suc:SezioneI_DichSost/suc:Aziende/suc:"
    dd = _data(_t(d, base_az + "DataDeposito"))
    if dd:
        dichiarazione["azienda_data_deposito"] = dd
    cc = _t(d, base_az + "CameraCommercio")
    if cc:
        dichiarazione["azienda_camera_commercio"] = cc

    # ---- passivita' (ED)
    tel_pass: dict[str, dict] = {}
    k = 0
    corrente: dict | None = None          # passivita' in costruzione: i righi di continuazione ne completano la ripartizione
    continua = False                      # il rigo precedente aveva «Continuazione» (Fascicolo I p. PDF 38)

    def ripartizione_di(ps, ctx):
        rip_ = []
        for rp in ps.xpath("suc:RipartizioneED/suc:Ripartizione", namespaces=NS):
            rigo = _intero(_t(rp, "suc:IdentificazioneSoggetto/suc:Rigo"), ctx)
            mm = _intero(_t(rp, "suc:IdentificazioneSoggetto/suc:Modulo"), ctx)
            pers = persona_di_rigo.get((mm, rigo))
            if pers is None:
                raise XmlNonImportabile(f"{ctx}: la ripartizione rimanda a un erede inesistente (modulo {mm}, rigo {rigo})")
            rip_.append({"persona_id": pers, "quota": _quota(rp, "suc:Quota/suc:QuotaElementi/suc:Quota", ctx)})
        return rip_

    def chiudi(c):
        rip_ = c["rip"]
        if len(rip_) == 1 and rip_[0]["quota"] == {"num": 1, "den": 1}:
            c["campi"]["persona_id"] = rip_[0]["persona_id"]       # un solo erede per l'intero: forma semplice del modello
        elif rip_:
            c["tel"]["ripartizione"] = rip_
        ops.append(_upsert("passivita", c["pid"], c["campi"]))
        tel_pass[c["pid"]] = c["tel"]

    for m, mod in enumerate(d.xpath("suc:QuadroED/suc:Modulo", namespaces=NS), 1):
        for r, ps in enumerate(mod.xpath("suc:Passivita", namespaces=NS), 1):
            ctx = f"QuadroED modulo {m} rigo {r}"
            if continua:
                # rigo di continuazione: solo gli ulteriori soggetti della ripartizione, senza i dati della passivita'
                if corrente is None or any(etree.QName(e).localname != "RipartizioneED" for e in ps):
                    raise XmlNonImportabile(f"{ctx}: rigo di continuazione con dati di una nuova passivita'")
                if not ps.xpath("suc:RipartizioneED/suc:Ripartizione", namespaces=NS):
                    raise XmlNonImportabile(f"{ctx}: continuazione senza soggetti")
                corrente["rip"].extend(ripartizione_di(ps, ctx))
                continua = _casella(ps, "suc:RipartizioneED/suc:Continuazione", f"{ctx} Continuazione", avvisi)
                continue
            if corrente is not None:
                chiudi(corrente)
            k += 1
            pid = f"ps_ed{k:03d}"
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
            corrente = {"pid": pid, "campi": campi, "tel": tel, "rip": ripartizione_di(ps, ctx)}
            continua = _casella(ps, "suc:RipartizioneED/suc:Continuazione", f"{ctx} Continuazione", avvisi)
    if continua:
        raise XmlNonImportabile("QuadroED: «Continuazione» barrata sull'ultimo rigo, senza il rigo che segue")
    if corrente is not None:
        chiudi(corrente)
    importato["passivita"] = k

    # ---- quadri EF ed EH: scelte del professionista che l'esportazione riproduce (sanzioni, tempistica, rateazione, crediti)
    non_importato_eh: list[str] = []
    _ef_eh_dichiarati(d, dichiarazione, avvisi, non_importato_eh)

    ops.extend(devoluzioni)
    telematico: dict = {"dichiarazione": dichiarazione}
    if tel_persone:
        telematico["persone"] = tel_persone
    if tel_beni:
        telematico["beni"] = tel_beni
    if tel_pass:
        telematico["passivita"] = tel_pass
    if tel_dev:
        telematico["devoluzioni"] = tel_dev
    opzioni: dict = {"telematico": telematico}
    if tipo_dichiarazione:
        opzioni["tipo_dichiarazione"] = tipo_dichiarazione
    if quadri_extra:
        opzioni["quadri_attivi"] = _ATTIVI_BASE + quadri_extra
    ops.append({"op": "set", "sezione": "opzioni", "campi": opzioni})

    # Casi particolari: «non dar corso alle volture» (derivata con soli EL/EM, altrimenti scelta del dichiarante) e richiesta
    # dell'attestazione di avvenuta presentazione (copia conforme, Fascicolo I p. PDF 16)
    casi = fr.xpath("suc:CasiParticolari", namespaces=NS)
    if casi:
        solo_tavolari = (importato.get("terreni_tavolari") or importato.get("fabbricati_tavolari")) and not (
            importato["terreni"] or importato["fabbricati"])
        figli = {etree.QName(e).localname: (e.text or "").strip() for e in casi[0]}
        if figli.get("FirmaDichiarante") != "1" or set(figli) - {"CasiParticolari", "CopiaConforme", "FirmaDichiarante"} or \
                any(v != "1" for v in figli.values()):
            raise XmlNonImportabile("frontespizio: CasiParticolari con valori non previsti: la riesportazione non lo riprodurrebbe")
        if "CasiParticolari" in figli and not solo_tavolari:
            dichiarazione["casi_particolari"] = True
        if "CopiaConforme" in figli:
            dichiarazione["richiesta_attestazione"] = True
        _segna(casi[0])

    # Nessun campo significativo dei quadri dichiarati importabili puo' sparire.
    # I totali e le caselle derivate sono ricostruiti dall'export; gli altri campi
    # non letti rendono esplicito il limite PRIMA di creare la pratica.
    derivati = {"NumeroBeneficiari", "NumeroImmobili", "NumeroEredi", "NumeroLegatari", "NumeroChiamati",
                "ImportoDaVersare", "QuotaValore",
                "IdentificativoProdSoftware"}     # identificativo del software che ha prodotto il file: non e' un dato dichiarato
    # firma del modello e impegno a trasmettere: alla riesportazione valgono le impostazioni locali (caselle dei quadri
    # ricalcolate dai quadri presenti, intermediario e data dell'impegno del contesto di esportazione)
    non_importato = []
    # (le caselle CasellaEA... della firma sono derivate dai quadri presenti e non si elencano)
    for nome_sez, motivo in (("FirmaModello", "alla riesportazione valgono le impostazioni locali"),
                             ("ImpegnoATrasmettere", "alla riesportazione valgono le impostazioni locali dell'intermediario "
                                                     "(codice fiscale, impegno, data)")):
        for sez in fr.xpath("suc:" + nome_sez, namespaces=NS):
            resto = [e for e in sez.iter() if isinstance(e.tag, str) and not len(e) and (e.text or "").strip()
                     and e not in _letti.get() and not etree.QName(e).localname.startswith("Casella")]
            if resto:
                non_importato.append(f"Frontespizio {nome_sez}: non importato, {motivo}; nel file: "
                                     + "; ".join(f"{_percorso_relativo(e, sez)} = {e.text.strip()}" for e in resto))
            _segna(sez)
    # contenuto misto: testo fuori dagli elementi foglia non e' un valore del tracciato e non si puo' attribuire a un campo
    for e in d.iter():
        if not isinstance(e.tag, str):
            continue
        if (len(e) and (e.text or "").strip()) or (e is not d and (e.tail or "").strip()):
            raise XmlNonImportabile(f"contenuto misto in {radice.getroottree().getpath(e)}: testo fuori dai campi, non attribuibile "
                                    "a un dato del tracciato (nessun dato salvato)")
    mancanti = []
    for sezione in d:
        if etree.QName(sezione).localname not in {"Frontespizio", "QuadroED", *QUADRI_IMPORTATI}:
            continue
        for e in sezione.iter():
            if not isinstance(e.tag, str) or len(e) or not (e.text or "").strip() or e in _letti.get():
                continue
            if etree.QName(e).localname in derivati:
                continue
            mancanti.append(radice.getroottree().getpath(e))
    if mancanti:
        raise XmlNonImportabile("campi non supportati dall'importazione (nessun dato salvato): " + "; ".join(mancanti))
    presenti = [etree.QName(e).localname for e in d if isinstance(e.tag, str)]
    for q in sorted(set(presenti)):
        nodi = [e for e in d if isinstance(e.tag, str) and etree.QName(e).localname == q]
        if q in QUADRI_RICALCOLATI:
            non_importato.append(f"{q}: {QUADRI_RICALCOLATI[q]}")
        elif q in QUADRI_NON_IMPORTATI:
            non_importato.append(f"{q}: {QUADRI_NON_IMPORTATI[q]}")
        elif q == "QuadroEI":
            non_importato.append("QuadroEI (modello precedente, non previsto dall'XSD SUC13 vigente): non importato, da reinserire "
                                 "nella voltura; contenuto: " + " | ".join(_elenco_foglie(n_, d) for n_ in nodi))
        elif q == "Frontespizio" or q in QUADRI_IMPORTATI:
            continue
        else:
            # quadro o elemento non gestito (o non previsto dall'XSD): elencato con tutto il suo contenuto
            tipo = "quadro non gestito dall'importazione" if q.startswith("Quadro") else "elemento non previsto nella dichiarazione"
            non_importato.append(f"{q}: {tipo}, non importato; contenuto: " + " | ".join(_elenco_foglie(n_, d) for n_ in nodi))
    non_importato += non_importato_eh
    cognome = defunto.get("cognome", "")
    titolo = f"Importata: {cognome} {defunto.get('nome', '')}".strip()
    return {"operazioni": ops, "titolo": titolo, "importato": importato, "non_importato": non_importato, "avvisi": avvisi}
