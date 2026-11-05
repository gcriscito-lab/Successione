"""Cariche 5 (curatore dell'eredita' giacente), 6 (amministratore dell'eredita'), 8 (possesso temporaneo dei beni dell'assente: morte
presunta) e tipo soggetto 6 «Altro». Fonti: XSD fornituraSUC13_v1.xsd (CodiceCarica, TipoSoggetto, CasiParticolari, QuadroEH/DatiDefunto/
MortePresunta, QuadroEG/DichSost), Fascicolo I pp. PDF 15, 17-18, 52-53. I casi positivi sono stati accettati dal controllo ufficiale
SUC13 2.3.1 eseguito in locale il 2026-11-06 (dati sintetici; non e' una verifica con l'Agenzia). Il trust e la carica 9 restano bloccati."""
import copy
import re
import tempfile
from pathlib import Path

import pytest

from telematico_casi import caso_a10, caso_testamento
from test_frontespizio import SALTA, con_doc, con_presentatore, controllo, dich, esporta, ok, x, D
from test_telematico_controllo import _esegui

CF_CURATELA = "00000000018"          # codice fiscale a 11 cifre valido (cifra di controllo corretta)


def carica_6(chiamati=True, casi=True, dsost=True):
    d = con_presentatore(copy.deepcopy(caso_a10()), "Franco", "Neri", "6")
    if chiamati:
        for pid in ("p_anna0001", "p_luca0001"):
            d["opzioni"]["telematico"]["persone"][pid]["tipo_soggetto"] = "3"
    if casi:
        dich(d)["casi_particolari"] = True
    if dsost:
        con_doc(d, "dr_dsost01", "DichSost")
    con_doc(d, "dr_ident01", "DocumentiIdentita")
    return d


def carica_5(casi=True, dsost=True, grado="35"):
    """Un solo soggetto EA, la curatela (tipo 6, denominazione), cui vanno tutti i beni: eredita' giacente da testamento."""
    d = con_presentatore(copy.deepcopy(caso_testamento()), "Franco", "Neri", "5")
    d["persone"] = [p for p in d["persone"] if p.get("ruolo") != "erede"]
    den = "CURATELA EREDITA GIACENTE ROSSI MARIO"
    d["persone"].append({"id": "p_curat001", "_origine": {}, "cognome": "", "nome": "", "codice_fiscale": CF_CURATELA,
                         "ruolo": "erede", "denominazione": den, "relazione_con_defunto": grado})
    tel = d["opzioni"]["telematico"]
    for k in ("p_anna0001", "p_luca0001"):
        tel["persone"].pop(k, None)
    tel["persone"]["p_curat001"] = {"tipo_soggetto": "6", "grado_parentela": grado, "denominazione": den}
    visti, nuove = set(), []
    for dv in d["devoluzioni"]:
        if dv["bene_id"] not in visti:
            visti.add(dv["bene_id"])
            dv.update(persona_id="p_curat001", quota="1/1")
            nuove.append(dv)
    d["devoluzioni"] = nuove
    for ps in d["passivita"]:
        if "persona_id" in ps:
            ps["persona_id"] = "p_curat001"
    for pas in tel["passivita"].values():
        if "ripartizione" in pas:
            pas["ripartizione"] = [{"persona_id": "p_curat001", "quota": "1/1"}]
    dich(d)["tempistica_pagamento"] = "1"
    if casi:
        dich(d)["casi_particolari"] = True
    if dsost:
        con_doc(d, "dr_dsost01", "DichSost")
    con_doc(d, "dr_ident01", "DocumentiIdentita")
    return d


MORTE = {"tribunale": "TRIBUNALE DI ROMA", "data_deposito": "2026-06-10", "sentenza": "SENT 123 2026"}


def carica_8(in_ea=True, testamento=False):
    """Persone immessa nel possesso temporaneo dei beni dell'assente: il dichiarante e' un erede del quadro EA (in_ea) oppure no."""
    if in_ea:
        d = copy.deepcopy(caso_testamento() if testamento else caso_a10())
        dich(d)["presentatore"]["codice_carica"] = "8"
    else:
        d = con_presentatore(copy.deepcopy(caso_testamento() if testamento else caso_a10()), "Franco", "Neri", "8")
    dich(d)["morte_presunta"] = dict(MORTE)
    return d


# ------------------------------------------------------------------------------------------------ controllo ufficiale
@SALTA
@pytest.mark.parametrize("caso", [
    pytest.param(lambda: carica_6(True), id="6_chiamati"),
    pytest.param(lambda: carica_6(False), id="6_eredi"),
    pytest.param(lambda: con_presentatore_testamento_6(), id="6_testamento"),
    pytest.param(lambda: carica_5(), id="5_curatela_testamento"),
    pytest.param(lambda: carica_5_con_prima_casa_assente(), id="5_senza_passivita"),
    pytest.param(lambda: carica_8(True), id="8_dichiarante_in_ea"),
    pytest.param(lambda: carica_8(False), id="8_dichiarante_fuori_ea"),
    pytest.param(lambda: carica_8(True, testamento=True), id="8_testamento"),
])
def test_cariche_accettate_dal_controllo(caso, tmp_path):
    es = ok(esporta(caso()))
    controllo(es, tmp_path)


def con_presentatore_testamento_6():
    d = con_presentatore(copy.deepcopy(caso_testamento()), "Franco", "Neri", "6")
    for pid in ("p_anna0001", "p_luca0001"):
        d["opzioni"]["telematico"]["persone"][pid]["tipo_soggetto"] = "3"
    dich(d)["casi_particolari"] = True
    con_doc(d, "dr_dsost01", "DichSost")
    con_doc(d, "dr_ident01", "DocumentiIdentita")
    return d


def carica_5_con_prima_casa_assente():
    d = carica_5()
    d["passivita"] = [p for p in d["passivita"] if p["id"] == "ps_medic01"]
    tel = d["opzioni"]["telematico"]
    tel["passivita"] = {k: v for k, v in tel["passivita"].items() if k == "ps_medic01"}
    return d


# --------------------------------------------------------------------------------------------------------- struttura XML
def test_xml_carica_6():
    es = ok(esporta(carica_6()))
    assert x(es, f"{D}/suc:Frontespizio/suc:Presentatore/suc:CodiceCarica/text()") == ["6"]
    assert x(es, f"{D}/suc:Frontespizio/suc:CasiParticolari/suc:CasiParticolari/text()") == ["1"]
    assert not x(es, f"{D}/suc:QuadroEH")                       # annotazione: QuadroEH non presente con codice carica 5, 6, 7
    assert x(es, f"{D}/suc:QuadroEG//suc:DichSost")


def test_xml_carica_5_curatela():
    es = ok(esporta(carica_5()))
    assert x(es, f"{D}/suc:Frontespizio/suc:Presentatore/suc:CodiceCarica/text()") == ["5"]
    assert x(es, f"{D}/suc:QuadroEA//suc:Soggetto/suc:TipoSoggetto/text()") == ["6"]
    assert x(es, f"{D}/suc:QuadroEA//suc:Soggetto/suc:GradoParentela/text()") == ["35"]
    assert x(es, f"{D}/suc:QuadroEA//suc:Soggetto/suc:Denominazione/text()") == ["CURATELA EREDITA GIACENTE ROSSI MARIO"]
    assert not x(es, f"{D}/suc:QuadroEH") and x(es, f"{D}/suc:Frontespizio/suc:CasiParticolari/suc:CasiParticolari/text()") == ["1"]


def test_xml_carica_8_morte_presunta():
    es = ok(esporta(carica_8(True)))
    base = f"{D}/suc:QuadroEH/suc:PrimoModulo/suc:SezioneI_DichSost"
    assert x(es, f"{base}/suc:DatiDefunto/suc:MortePresunta/suc:Tribunale/text()") == ["TRIBUNALE DI ROMA"]
    assert x(es, f"{base}/suc:DatiDefunto/suc:MortePresunta/suc:DataDeposito/text()") == ["10062026"]
    assert not x(es, f"{base}/suc:DatiDefunto/suc:Decesso")
    assert x(es, f"{base}/suc:Dichiarante/suc:PresenzaDichiarante/text()") == ["1"]          # il dichiarante e' nel quadro EA
    es = ok(esporta(carica_8(False)))
    assert x(es, f"{base}/suc:Dichiarante/suc:FlagAssenzaDichiarante/text()") == ["1"]         # il dichiarante non e' nel quadro EA


# ------------------------------------------------------------------- regole applicate dall'esportazione (annotazioni XSD)
def codici(es):
    return {e.codice for e in es.errori}


def test_carica_6_richiede_casi_particolari_e_dichiarazione_sostitutiva():
    es = esporta(carica_6(casi=False))
    assert es.xml is None and "DATO_MANCANTE" in codici(es)
    es = esporta(carica_6(dsost=False))
    assert not es.completo and any(m.percorso == "quadro[EG].DichSost" for m in es.quadri_mancanti)


def test_carica_5_richiede_la_curatela_come_unico_soggetto_di_tipo_altro():
    d = copy.deepcopy(caso_testamento())
    d = con_presentatore(d, "Franco", "Neri", "5")
    dich(d)["casi_particolari"] = True
    con_doc(d, "dr_dsost01", "DichSost")
    con_doc(d, "dr_ident01", "DocumentiIdentita")
    es = esporta(d)                                              # eredi persone fisiche: nessun soggetto di tipo 6
    assert es.xml is None and "REGOLA_CARICA_CURATORE" in codici(es)


def test_tipo_altro_regole():
    d = carica_5(grado="37")
    es = esporta(d)
    assert es.xml is None and "REGOLA_TIPO_ALTRO" in codici(es)            # grado diverso da 35: non provato
    d = carica_5()
    del d["opzioni"]["telematico"]["persone"]["p_curat001"]["denominazione"]
    d["persone"][-1].pop("denominazione")
    es = esporta(d)
    assert es.xml is None and "DATO_MANCANTE" in codici(es)               # la curatela non e' una persona fisica
    d = carica_5()
    d["persone"].append({"id": "p_altro0001", "_origine": {}, "cognome": "Rossi", "nome": "Anna", "codice_fiscale": "RSSNNA70A41H501J",
                         "data_nascita": "1970-01-01", "luogo_nascita": "Roma", "ruolo": "erede", "relazione_con_defunto": "02"})
    d["opzioni"]["telematico"]["persone"]["p_altro0001"] = {"sesso": "F", "provincia_nascita": "RM", "grado_parentela": "02"}
    es = esporta(d)
    assert es.xml is None and "REGOLA_TIPO_ALTRO" in codici(es)           # con il tipo 6 non possono esserci altri soggetti


def test_morte_presunta_regole():
    d = carica_8()
    del dich(d)["morte_presunta"]
    es = esporta(d)
    assert es.xml is None and "DATO_MANCANTE" in codici(es)
    d = carica_8()
    dich(d)["morte_presunta"]["data_deposito"] = "2025-03-10"             # uguale alla data del decesso (2025-03-10)
    es = esporta(d)
    assert es.xml is None and "REGOLA_MORTE_PRESUNTA" in codici(es)
    d = caso_a10()
    dich(d)["morte_presunta"] = dict(MORTE)                              # con la carica 1 la morte presunta non si indica
    es = esporta(d)
    assert es.xml is None and "DATI_INCOERENTI" in codici(es)
    d = carica_8()
    dich(d)["morte_presunta"]["extra"] = "x"
    assert "VALORE_NON_VALIDO" in codici(esporta(d))


def test_rappresentato_non_ammesso_con_le_cariche_5_6_8():
    for carica in ("5", "6", "8"):
        d = {"5": carica_5, "6": carica_6, "8": carica_8}[carica]()
        dich(d)["presentatore"]["rappresentato_cf"] = "RSSNNA70A41H501J"
        assert "DATI_INCOERENTI" in codici(esporta(d))


def test_carica_9_e_trust_restano_bloccati():
    d = copy.deepcopy(caso_testamento())
    dich(d)["presentatore"]["codice_carica"] = "9"
    es = esporta(d)
    assert es.xml is None and any("codice_carica=9" in m for m in es.non_supportato)
    d = copy.deepcopy(caso_testamento())
    d["opzioni"]["telematico"]["persone"]["p_anna0001"]["tipo_soggetto"] = "5"
    es = esporta(d)
    assert es.xml is None and any("tipo soggetto 5 (trust)" in m for m in es.non_supportato)


# ------------------------------------- negativi del controllo ufficiale (XML alterato: prova che la regola viene dal controllo)
def respinto(es, tmp_path, xml, codice):
    stato, dgn, wri, _ = _esegui(xml, tmp_path)
    assert stato == "negativo" and codice in [d["codice"] for d in dgn["diagnostici"]], (stato, dgn["diagnostici"])


@SALTA
def test_negativo_carica_6_senza_casi_particolari(tmp_path):
    es = ok(esporta(carica_6()))
    xml = re.sub(rb"<(\w+:)?CasiParticolari>1</(\w+:)?CasiParticolari>", b"", es.xml)    # solo la casella interna
    assert xml != es.xml
    respinto(es, tmp_path, xml, "3250")


@SALTA
def test_negativo_carica_5_senza_dichiarazione_sostitutiva(tmp_path):
    es = ok(esporta(carica_5()))
    # carica 5 senza dichiarazione sostitutiva EG1: l'esportazione la richiede; per provare il controllo si toglie il blocco DichSost
    xml = re.sub(rb"<(\w+:)?DichSost>.*?</(\w+:)?DichSost>", b"", es.xml, flags=re.S)
    assert xml != es.xml
    respinto(es, tmp_path, xml, "3328")


@SALTA
def test_negativo_carica_8_assenza_con_dichiarante_in_ea(tmp_path):
    es = ok(esporta(carica_8(True)))
    xml = es.xml.replace(b"PresenzaDichiarante", b"FlagAssenzaDichiarante")          # apertura e chiusura dell'elemento
    assert xml != es.xml
    respinto(es, tmp_path, xml, "3213")
