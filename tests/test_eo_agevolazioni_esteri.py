"""Quadro EO: agevolazione D sui titoli, titoli esteri senza codice fiscale dell'emittente, ValoreEsente sui fondi comuni (tipo 4).

Fonti (citate anche nel codice):
- XSD fornituraSUC13_v1.xsd (SUC13_20250702), annotazione di DevoluzioneNonImmobili_Type/Devoluzione/Agevolazioni: «Per il quadro
  EO sono ammessi solo i codici agevolazione D, Q»; gradi ammessi per D: 01, 02, 04, 06, 08; annotazione di
  QuadroEH/.../SezioneIV_AltreAgevRiduz/Agevolazioni (FlagD: «agevolazioni = C o D o E o Q in almeno uno dei quadri ... EO ...»).
- Fascicolo I p. PDF 56 (Allegato 2, codice D), p. PDF 57 (quadro sinottico: D esente da I, C, S), p. PDF 58 (cod. D: «quote sociali
  e azioni»; richiesta del dichiarante nel quadro EH, degli altri con dichiarazione sostitutiva nel quadro EG).
- Guida di calcolo p. 1: la QE esclude i righi con D.
- XSD, annotazione di QuadroEO/Modulo/Titoli/CodiceFiscale: obbligatorio se TipoTitolo 1, «Non deve essere presente se e' barrata la
  casella Bene sito all'estero».
- XSD PossessoEO_Type/Valore e /ValoreEsente: si escludono; Valore obbligatorio per i tipi 1 e 2, ValoreEsente obbligatorio per il
  tipo 3 e vietato per i tipi 1 e 2; per il tipo 4 nessun vincolo.
Dati sintetici.
"""
import copy
from datetime import date

import pytest
from lxml import etree

from successioni.telematico.calcolo import calcola_da_xml
from successioni.telematico.esporta import esporta_xml
from successioni.telematico.importa import importa_xml
from successioni.telematico import xsd

from telematico_casi import _titolo, caso_titoli, contesto_caso_a10
from test_telematico_controllo import NS, _esegui, _motivo_salto

SALTO = _motivo_salto()
CTX = contesto_caso_a10(data_riferimento=date(2025, 9, 1))
D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"
T = D + "/suc:QuadroEO/suc:Modulo/suc:Titoli"
EH_FLAG = {"dichiara_requisiti": True}


def _bene(d, bid):
    return next(b for b in d["beni"] if b["id"] == bid)


def _agev(d, did, cod):
    d["opzioni"]["telematico"].setdefault("devoluzioni", {}).setdefault(did, {})["agevolazioni"] = cod


def caso(d_azioni_anna=False, estero=False, fondo_esente=False):
    """``caso_titoli`` (azioni tipo 2, fondo tipo 4; Anna e' la dichiarante) con le varianti di questo modulo."""
    d = copy.deepcopy(caso_titoli())
    if d_azioni_anna:
        _agev(d, "d_azionanna", "D")
        d["opzioni"]["telematico"]["dichiarazione"]["riduzioni_art25"] = EH_FLAG
    if estero:
        d["beni"].append(_titolo("b_estero01", "1", "Azioni quotate estere (sintetico)", "4000", bene_estero="si"))
        for pid in ("p_anna0001", "p_luca0001"):
            d["devoluzioni"].append({"id": f"d_ester{pid[2:6]}", "_origine": {}, "bene_id": "b_estero01", "persona_id": pid,
                                     "quota": {"num": 1, "den": 2}, "diritto": "1"})
    if fondo_esente:
        _bene(d, "b_fondo001")["valore_esente"] = "si"
    return d


def _es(d):
    return esporta_xml(d, CTX)


def _x(es, xp):
    return etree.fromstring(es.xml).xpath(xp, namespaces=NS)


def _codici(es):
    return {(e.codice, e.percorso) for e in es.errori}


# ------------------------------------------------------------------------------------------------- 1. agevolazione D in EO
def test_d_su_azioni_del_dichiarante_esportata_con_flag_d():
    es = _es(caso(d_azioni_anna=True))
    assert es.completo, ([e.messaggio for e in es.errori], es.non_supportato, [m.messaggio for m in es.quadri_mancanti])
    assert xsd.valida_xsd(es.xml) == []
    assert _x(es, T + "[suc:TipoTitolo='2']/suc:DevoluzioneEO/suc:Devoluzione/suc:Agevolazioni/text()") == ["D"]
    assert _x(es, D + "/suc:QuadroEH//suc:SezioneIV_AltreAgevRiduz/suc:Agevolazioni/suc:FlagD/text()") == ["1"]
    # EE3 invariato: il titolo agevolato resta nell'attivo (l'annotazione di QuadroEE esclude solo A dagli immobili)
    assert _x(es, D + "/suc:QuadroEE/suc:TotaleValoreTitoli/text()") == ["16000"]


def test_d_esclude_la_quota_dalla_base_imponibile():
    def qe(d):
        r = calcola_da_xml(_es(d).xml)
        assert r.stato == "completato", r.motivi
        return [{p.sigla: p.valore for p in b.passaggi}["QE"] for b in r.beneficiari]
    senza, con = qe(caso()), qe(caso(d_azioni_anna=True))
    # Anna: meno la sua quota delle azioni (10000 x 1/2); Luca invariato
    assert int(senza[0]) - int(con[0]) == 5000 and senza[1] == con[1], (senza, con)


def test_d_di_un_altro_beneficiario_richiede_il_rigo_eg10():
    d = caso()
    _agev(d, "d_azionluca", "D")
    es = _es(d)
    assert any(m.percorso == "quadro[EG].AgevolazioniImposteIpocatastali" for m in es.quadri_mancanti), es.quadri_mancanti
    assert not es.non_supportato


def test_d_su_fondo_comune_e_un_avviso():
    d = caso()
    _agev(d, "d_fondoanna", "D")
    d["opzioni"]["telematico"]["dichiarazione"]["riduzioni_art25"] = EH_FLAG
    es = _es(d)
    assert es.completo and any(a.codice == "AGEVOLAZIONE_D_TIPO_TITOLO" for a in es.avvisi)


@pytest.mark.parametrize("cod", ["A", "C", "E", "G", "H", "M", "N"])
def test_altri_codici_non_ammessi_in_eo(cod):
    d = caso()
    _agev(d, "d_azionanna", cod)
    assert ("REGOLA_AGEVOLAZIONE_QUADRO", "devoluzioni[d_azionanna].agevolazioni") in _codici(_es(d))


def test_d_grado_non_ammesso():
    d = caso()
    for p in d["persone"]:
        if p["id"] in ("p_anna0001", "p_luca0001"):
            p["relazione_con_defunto"] = "10"
            d["opzioni"]["telematico"]["persone"][p["id"]]["grado_parentela"] = "10"
    _agev(d, "d_azionanna", "D")
    assert ("REGOLA_AGEVOLAZIONE_GRADO", "devoluzioni[d_azionanna].agevolazioni") in _codici(_es(d))


# --------------------------------------------------------------------------------- 2. titolo estero: niente CF emittente
def test_titolo_estero_quotato_senza_codice_fiscale():
    es = _es(caso(estero=True))
    assert es.completo, ([e.messaggio for e in es.errori], es.non_supportato)
    riga = _x(es, T + "[suc:TipoTitolo='1']")[0]
    assert riga.find("{*}CodiceFiscale") is None and riga.find("{*}BeniEsteri/{*}BeneSitoEstero").text == "1"


def test_titolo_estero_con_codice_fiscale_e_incoerente():
    d = caso(estero=True)
    _bene(d, "b_estero01")["codice_fiscale_emittente"] = "00000000018"
    assert ("DATI_INCOERENTI", "beni[b_estero01].codice_fiscale_emittente") in _codici(_es(d))


def test_titolo_italiano_quotato_richiede_ancora_il_codice_fiscale():
    d = caso(estero=True)
    _bene(d, "b_estero01")["bene_estero"] = "no"
    assert ("DATO_MANCANTE", "beni[b_estero01].codice_fiscale_emittente") in _codici(_es(d))


# ----------------------------------------------------------------------------------- 3. ValoreEsente sul fondo (tipo 4)
def test_fondo_con_valore_esente():
    es = _es(caso(fondo_esente=True))
    assert es.completo, ([e.messaggio for e in es.errori], es.non_supportato)
    assert _x(es, T + "[suc:TipoTitolo='4']/suc:Possesso/suc:ValoreEsente/text()") == ["6000"]
    assert _x(es, T + "[suc:TipoTitolo='4']/suc:Possesso/suc:Valore") == []
    assert _x(es, D + "/suc:QuadroEE/suc:TotaleValoreTitoli/text()") == ["16000"]      # Valore + ValoreEsente


def test_fondo_esente_fuori_dalla_base_imponibile():
    def qe(d):
        r = calcola_da_xml(_es(d).xml)
        return [{p.sigla: p.valore for p in b.passaggi}["QE"] for b in r.beneficiari]
    a, b = qe(caso()), qe(caso(fondo_esente=True))
    assert [int(x) - int(y) for x, y in zip(a, b)] == [3000, 3000], (a, b)


def test_valore_esente_incoerente_col_tipo():
    d = caso()
    _bene(d, "b_azioni01")["valore_esente"] = "si"          # tipo 2: ValoreEsente vietato
    assert ("DATI_INCOERENTI", "beni[b_azioni01].valore_esente") in _codici(_es(d))
    d = caso()
    d["beni"].append(_titolo("b_bot00001", "3", "BOT sintetico", "800", valore_esente="no"))
    assert ("DATI_INCOERENTI", "beni[b_bot00001].valore_esente") in _codici(_es(d))


def test_importazione_del_valore_esente_sul_tipo_4_e_riesportazione_identica():
    xml = _es(caso(fondo_esente=True)).xml
    r = importa_xml(xml)
    testo = repr(r["operazioni"])
    assert "'valore_esente': 'si'" in testo
    assert not any("ValoreEsente" in a for a in r["avvisi"])


def test_valore_esente_su_tipo_2_importato_resta_esente_e_blocca():
    """File esterno non conforme (ValoreEsente su un tipo 2): l'import non lo trasforma in imponibile."""
    xml = _es(caso()).xml
    doc = etree.fromstring(xml)
    v = doc.xpath(T + "[suc:TipoTitolo='2']/suc:Possesso/suc:Valore", namespaces=NS)[0]
    v.tag = v.tag.replace("Valore", "ValoreEsente")
    r = importa_xml(etree.tostring(doc, xml_declaration=True, encoding="UTF-8"))
    assert "'valore_esente': 'si'" in repr(r["operazioni"])
    assert any("ValoreEsente" in a and "'2'" in a for a in r["avvisi"])


# --------------------------------------------------------------------------------------------- controllo ufficiale locale
@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
@pytest.mark.java
def test_reale_controllo_ufficiale_positivo(tmp_path):
    es = _es(caso(d_azioni_anna=True, estero=True, fondo_esente=True))
    assert es.completo, ([e.messaggio for e in es.errori], es.non_supportato)
    stato, dgn, wri, _ = _esegui(es.xml, tmp_path)
    assert stato == "positivo", (dgn["diagnostici"], wri[:900])
    assert sorted(x["codice"] for x in dgn["diagnostici"]) == ["3345"], dgn["diagnostici"]


def _senza_flag_d(doc):
    s = doc.xpath(D + "/suc:QuadroEH//suc:SezioneIV_AltreAgevRiduz", namespaces=NS)[0]
    s.getparent().remove(s)


def _cf_su_estero(doc):
    riga = doc.xpath(T + "[suc:TipoTitolo='1']", namespaces=NS)[0]
    cf = etree.Element(riga.find("{*}TipoTitolo").tag.replace("TipoTitolo", "CodiceFiscale"))
    cf.text = "00000000018"
    riga.find("{*}TipoTitolo").addnext(cf)


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
@pytest.mark.parametrize("mut", [_senza_flag_d, _cf_su_estero])
@pytest.mark.java
def test_reale_controllo_ufficiale_negativi(mut, tmp_path):
    doc = etree.fromstring(_es(caso(d_azioni_anna=True, estero=True, fondo_esente=True)).xml)
    mut(doc)
    stato, dgn, _, _ = _esegui(etree.tostring(doc, xml_declaration=True, encoding="UTF-8"), tmp_path, rapporto=False)
    assert stato != "positivo", (mut.__name__, dgn["diagnostici"])
