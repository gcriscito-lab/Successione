"""Beni esteri, imposta versata all'estero, certificazione EG e detrazione DET.estero.

Fonti: XSD fornituraSUC13_v1.xsd (Luogo_Type con provincia EE, BeniEsteri_Type, CertificazioneImpostaVersataEstero, annotazioni di
QuadroEF/QuadroEE), Fascicolo I pp. PDF 22, 23, 29, 33, 34 e Allegato di calcolo pp. 7-8 (e = valore quota estero x ISL / QE;
IE = imposta estera x quota di devoluzione; DET.estero = min(e, IE)). Ogni XML valido e' stato accettato dal controllo ufficiale
SUC13 2.3.1 eseguito in locale su dati sintetici."""
import copy
from datetime import date
from fractions import Fraction

import pytest
from lxml import etree

from telematico_casi import ALLEGATI_A10, caso_a10, caso_azienda, caso_mezzi, caso_titoli, contesto
from successioni.telematico.calcolo import (calcola_da_xml, detrazione_estera_componente, detrazione_estera_esatta)
from successioni.telematico.esporta import esporta_xml
from test_telematico_controllo import _esegui, _motivo_salto

D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"
ALLEGATI = {**ALLEGATI_A10, "al_cert": ALLEGATI_A10["al_passiv"]}
FRANCIA = {"codice_stato_estero": "029", "stato_estero": "FRANCIA"}


def ctx(**kw):
    return contesto(allegati=ALLEGATI, **kw)


def dev_meta(d, bid, pid_quote=(("p_anna0001", 1, 2), ("p_luca0001", 1, 2))):
    for pid, n, den in pid_quote:
        d["devoluzioni"].append({"id": f"d_{bid[2:9]}{pid[2:6]}", "_origine": {}, "bene_id": bid, "persona_id": pid,
                                 "quota": {"num": n, "den": den}, "diritto": "1"})


def con_certificazione(d):
    d["documenti_ref"].append({"id": "dr_certes1", "_origine": {}, "allegato_id": "al_cert",
                               "tipo_eg": "CertificazioneImpostaVersataEstero", "finalita": "Certificazione imposta estera (sintetica)"})


def immobile_estero(d, quadro="EC", valore="60000", imposta=None, bid=None):
    bid = bid or ("b_estero01" if quadro == "EC" else "b_estero02")
    if quadro == "EC":
        d["beni"].append({"id": bid, "_origine": {}, "tipo": "fabbricato", "valore": valore, "diritto": "1",
                          "quota_defunto": "1/1", "provincia": "EE", "indirizzo": "RUE DE LA PAIX 1", "localita_estero": "PARIGI",
                          **FRANCIA, **({"imposta_estera": imposta} if imposta else {})})
    else:
        d["beni"].append({"id": bid, "_origine": {}, "tipo": "terreno", "valore": valore, "diritto": "1",
                          "quota_defunto": "1/1", "provincia": "EE", "indirizzo": "ROUTE DES CHAMPS",
                          **FRANCIA, **({"imposta_estera": imposta} if imposta else {})})
    dev_meta(d, bid)
    if imposta:
        con_certificazione(d)
    return bid


def esporta(d, **kw):
    return esporta_xml(d, ctx(**kw))


def ok(es):
    assert es.completo, [e.messaggio for e in es.errori] + es.non_supportato + [m.messaggio for m in es.quadri_mancanti]
    return es


def xp(es, path):
    doc = etree.fromstring(es.xml)
    return doc.xpath(f"{D}/{path}", namespaces={k: v for k, v in doc.nsmap.items() if k})


# ------------------------------------------------------------------------------------------------ struttura dell'XML
def test_immobile_estero_ec_senza_dati_catastali_e_fuori_da_ef():
    d = caso_a10()
    base = ok(esporta(caso_a10()))
    immobile_estero(d, "EC")
    es = ok(esporta(d))
    luogo = xp(es, "suc:QuadroEC//suc:Fabbricati/suc:Luogo[*[local-name()='Provincia']='EE']")[0]
    assert [c.tag.split("}")[1] for c in luogo] == ["Provincia", "Estero"]
    assert [c.text for c in luogo.iter() if len(c) == 0][0] == "EE"
    estero = {c.tag.split("}")[1]: c.text for c in luogo[1]}
    assert estero == {"CodiceStatoEstero": "029", "LocalitaEstero": "PARIGI", "IndirizzoEstero": "RUE DE LA PAIX 1",
                      "StatoEstero": "FRANCIA"}
    assert len(xp(es, "suc:QuadroEC//suc:Fabbricati/suc:DatiFabbricati")) == 1          # solo la casa italiana
    # il valore estero e' nel prospetto EE ma non nelle basi EF1/EF9, ne' nelle circoscrizioni
    assert xp(es, "suc:QuadroEE/suc:TotaleValoreImmobili/text()") == [str(141000 + 60000)]
    for sezione in ("SezioneI_ImpostaIpotecaria", "SezioneII_ImpostaCatastale"):
        assert xp(es, f"suc:QuadroEF/suc:{sezione}/suc:ImpostaProporzionale/*/text()") == \
            xp(base, f"suc:QuadroEF/suc:{sezione}/suc:ImpostaProporzionale/*/text()")
    assert xp(es, "suc:QuadroEF/suc:TotaleDaVersare/text()") == xp(base, "suc:QuadroEF/suc:TotaleDaVersare/text()")


def test_terreno_estero_eb_con_imposta_estera_e_certificazione():
    d = caso_a10()
    immobile_estero(d, "EB", valore="40000", imposta="3000")
    es = ok(esporta(d))
    riga = xp(es, "suc:QuadroEB//suc:Terreni[suc:Luogo/*[local-name()='Provincia']='EE']")[0]
    figli = {c.tag.split("}")[1]: c for c in riga}
    # il controllo ufficiale respinge TipologiaTerreno su un terreno estero (diagnostico 3072): non va indicata
    assert "DatiTerreni" not in figli and "TipologiaTerreno" not in figli and figli["ImpostaVersataEstero"].text == "3000"
    assert xp(es, "suc:QuadroEG/suc:CertificazioneImpostaVersataEstero/suc:CertificazioneImpostaVersataEsteroNum/text()") == ["1"]


def test_cespiti_esteri_er_en_eo_ep_eq():
    d = caso_a10()
    ER = next(b for b in d["beni"] if b["id"] == "b_conto001")
    ER["bene_estero"], ER["imposta_estera"] = "1", "400"
    con_certificazione(d)
    es = ok(esporta(d))
    assert xp(es, "suc:QuadroER/suc:Modulo/suc:Rendite[1]/suc:BeniEsteri/*/text()") == ["1", "400"]
    for caso, bene, quadro, riga in ((caso_azienda(), "b_azien001", "EN", "Aziende"), (caso_titoli(), "b_azioni01", "EO", "Titoli"),
                                     (caso_mezzi(), "b_aereo001", "EP", "Aeromobili"), (caso_mezzi(), "b_barca001", "EQ", "Navi")):
        b = next(x for x in caso["beni"] if x["id"] == bene)
        b["bene_estero"] = "1"
        if quadro == "EN":
            del b["codice_fiscale_emittente"]
        es = ok(esporta(caso))
        assert xp(es, f"suc:Quadro{quadro}//suc:BeniEsteri/suc:BeneSitoEstero/text()")


def test_incoerenze():
    d = caso_a10()                                                 # imposta estera su un bene italiano
    next(b for b in d["beni"] if b["id"] == "b_conto001")["imposta_estera"] = "100"
    es = esporta(d)
    assert es.xml is None and any(e.codice == "DATI_INCOERENTI" for e in es.errori)
    d = caso_a10()                                                 # imposta estera senza certificazione EG4
    immobile_estero(d, "EC", imposta="500")
    d["documenti_ref"] = [x for x in d["documenti_ref"] if x["tipo_eg"] != "CertificazioneImpostaVersataEstero"]
    es = esporta(d)
    assert es.xml is None and any("CertificazioneImpostaVersataEstero" in m.percorso for m in es.quadri_mancanti)
    d = caso_a10()                                                 # dati catastali su immobile estero / stato mancante
    bid = immobile_estero(d, "EC")
    bene = next(b for b in d["beni"] if b["id"] == bid)
    bene["foglio"] = "10"
    assert esporta(d).xml is None
    bene.pop("foglio")
    del bene["codice_stato_estero"]
    es = esporta(d)
    assert es.xml is None and any(e.codice == "DATO_MANCANTE" for e in es.errori)
    d = caso_a10()                                                 # agevolazioni su immobile estero
    bid = immobile_estero(d, "EC")
    d["opzioni"]["telematico"]["devoluzioni"] = {f"d_{bid[2:9]}anna": {"agevolazioni": "P"}}
    es = esporta(d)
    assert es.xml is None and any(e.codice == "REGOLA_AGEVOLAZIONE_ESTERO" for e in es.errori)


def test_titolo_estero_non_ammette_codice_fiscale_dell_emittente():
    d = caso_titoli()
    b = next(x for x in d["beni"] if x["id"] == "b_azioni01")
    b["bene_estero"], b["tipo_titolo"], b["codice_fiscale_emittente"] = "1", "1", "00000000018"
    assert esporta(d).xml is None


# ------------------------------------------------------------------------------------------------ detrazione DET.estero
def test_detrazione_esempio_della_guida():
    # guida p. 7-8: valore quota estero 2.500, ISL 6.567, QE 200.000 -> e = 82,0875; IE = 1.000 x 1/2 = 500 >= e -> DET = e
    riga = {"qv": Fraction(2500), "ie": 1000, "qn": 1, "qd": 2}
    e = Fraction(2500) * Fraction(6567) / Fraction(200000)
    assert detrazione_estera_esatta([riga], Fraction(6567), Fraction(200000)) == e
    assert float(e) == pytest.approx(82.0875)
    # componente (ispezione statica): e a 4 decimali = 82,0875 (la guida mostra 82,08: dubbio documentato, vedi
    # docs/regole/dubbio_arrotondamento.md); l'imposta estera ridotta alla quota resta quella piu' bassa
    assert detrazione_estera_componente([riga], Fraction(6567), Fraction(200000)) == Fraction(820875, 10000)
    piccola = {"qv": Fraction(2500), "ie": 100, "qn": 1, "qd": 2}          # IE = 50 < e: DET = IE
    assert detrazione_estera_esatta([piccola], Fraction(6567), Fraction(200000)) == 50
    assert detrazione_estera_componente([piccola], Fraction(6567), Fraction(200000)) == 50
    assert detrazione_estera_esatta([riga], Fraction(0), Fraction(200000)) == 0


def con_imposta_dovuta(valore_conto="2400000"):
    d = caso_a10()
    next(b for b in d["beni"] if b["id"] == "b_conto001")["valore"] = valore_conto
    d["opzioni"]["telematico"]["dichiarazione"]["tempistica_pagamento"] = "2"
    return d


def test_detrazione_nel_calcolo_dell_imposta_di_successione():
    senza = con_imposta_dovuta()
    es0 = ok(esporta(senza, data_riferimento=date(2026, 3, 9)))
    imposta0 = es0.mappa["calcolo:EF18bis"]["imposta"]
    d = con_imposta_dovuta()
    immobile_estero(d, "EC", valore="400000", imposta="3000")
    es = ok(esporta(d, data_riferimento=date(2026, 3, 9)))
    r = calcola_da_xml(es.xml)
    assert r.stato == "completato", [m.messaggio for m in r.motivi]
    passi = {p.sigla: p for b in r.beneficiari for p in b.passaggi if p.sigla == "DET"}
    assert passi and all(b.passaggi[-2].sigla == "DET" and float(b.passaggi[-2].valore) > 0 for b in r.beneficiari)
    # il valore estero entra nell'asse (QE) e quindi nell'imposta lorda; la detrazione la riduce
    assert es.mappa["calcolo:EF18bis"]["imposta"] != imposta0


# ------------------------------------------------------------------------------------------------ controllo ufficiale
def _dati(caso):
    d = {"immobile": lambda: _imm(), "terreno": lambda: _terr()}
    return d[caso]()


def _imm():
    d = caso_a10()
    immobile_estero(d, "EC")
    return d


def _terr():
    d = caso_a10()
    immobile_estero(d, "EB", valore="40000", imposta="3000")
    return d


def _conto():
    d = caso_a10()
    b = next(x for x in d["beni"] if x["id"] == "b_conto001")
    b["bene_estero"], b["imposta_estera"] = "1", "400"
    con_certificazione(d)
    return d


def _conto_senza_imposta():
    d = caso_a10()
    next(x for x in d["beni"] if x["id"] == "b_conto001")["bene_estero"] = "1"
    return d


def _titolo():
    d = caso_titoli()
    next(x for x in d["beni"] if x["id"] == "b_azioni01")["bene_estero"] = "1"
    return d


def _azienda():
    d = caso_azienda()
    b = next(x for x in d["beni"] if x["id"] == "b_azien001")
    b["bene_estero"] = "1"
    del b["codice_fiscale_emittente"]
    return d


def _mezzi():
    d = caso_mezzi()
    for bid in ("b_aereo001", "b_barca001"):
        next(x for x in d["beni"] if x["id"] == bid)["bene_estero"] = "1"
    return d


def _mix_con_det():
    d = con_imposta_dovuta()
    immobile_estero(d, "EC", valore="400000", imposta="3000")
    return d


def _mix_det_totale():
    d = con_imposta_dovuta()
    immobile_estero(d, "EB", valore="100000", imposta="9000")      # imposta estera alta: DET limitata da e
    return d


CASI = {"immobile_estero_senza_imposta": _imm, "terreno_estero_con_imposta": _terr, "conto_estero_con_imposta": _conto,
        "conto_estero_senza_imposta": _conto_senza_imposta, "titolo_estero": _titolo, "azienda_estera": _azienda,
        "aereo_e_nave_esteri": _mezzi, "mix_con_detrazione": _mix_con_det, "mix_detrazione_limitata": _mix_det_totale}


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
@pytest.mark.parametrize("nome", sorted(CASI))
@pytest.mark.java
def test_controllo_ufficiale_locale(tmp_path, nome):
    es = ok(esporta(CASI[nome](), data_riferimento=date(2026, 3, 9)))
    stato, dgn, wri, _ = _esegui(es.xml, tmp_path)
    assert stato == "positivo", (nome, dgn["diagnostici"], wri[:1500])


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
@pytest.mark.java
def test_controllo_ufficiale_respinge_una_detrazione_sbagliata(tmp_path):
    """Il controllo ricalcola l'imposta (EF18bis) con la detrazione: una imposta senza detrazione viene respinta."""
    es = ok(esporta(_mix_con_det(), data_riferimento=date(2026, 3, 9)))
    imposta = str(es.mappa["calcolo:EF18bis"]["imposta"]).encode()
    alterata = es.xml.replace(b">" + imposta + b"<", b">" + str(int(imposta) + 500).encode() + b"<")
    assert alterata != es.xml
    stato, dgn, _, _ = _esegui(alterata, tmp_path, rapporto=False)
    assert stato == "negativo", dgn["diagnostici"]
