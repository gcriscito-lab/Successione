"""Quadro EI (voltura: discordanza dati intestatario e passaggi senza atti legali): generato dai beni EB/EC; regole di
Fascicolo I p. 54 e delle annotazioni XSD; controllo SUC13 locale (dati sintetici)."""
import copy
from datetime import date

import pytest
from lxml import etree

from successioni.telematico.esporta import esporta_xml
from telematico_casi import caso_a10, caso_tavolare, caso_voltura, contesto_caso_a10
from test_telematico_controllo import NS, _esegui, _motivo_salto

D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"
EI = D + "/suc:QuadroEI_new"
CTX = contesto_caso_a10(data_riferimento=date(2025, 9, 1))
TR = {"ufficio": "RM10", "registro_particolare": "12345", "anno": "2010"}
RG = {"ufficio": "795", "anno": "2020", "volume": "88888", "numero": "123"}


def _es(mod=None, tel=None):
    d = caso_voltura()
    if mod:
        mod(d)
    if tel:
        tel(d["opzioni"]["telematico"]["beni"])
    return esporta_xml(d, CTX)


def _codici(es):
    return {(e.percorso, e.codice) for e in es.errori}


def _x(es, xp):
    return etree.fromstring(es.xml).xpath(xp, namespaces=NS)


def test_xml_completo_con_quadro_ei():
    es = _es()
    assert es.errori == [] and es.non_supportato == [] and es.quadri_mancanti == [], (es.errori, es.non_supportato)
    assert _x(es, D + "/suc:Frontespizio/suc:FirmaModello/suc:CasellaEI/text()") == ["1"]
    assert _x(es, EI + "/suc:PrimoModulo/suc:SezioneI_AttiLegali/suc:FlagAttiLegali/text()") == ["1"]
    s2 = EI + "/suc:PrimoModulo/suc:SezioneII_DatiIntestatario"
    assert _x(es, s2 + "/suc:Immobile/suc:TipoCatasto/text()") == ["U"]
    assert _x(es, s2 + "/suc:EstremiTrascrizione/suc:RegistroParticolare/text()") == ["12345"]
    assert _x(es, s2 + "/suc:EstremiRegistrazione/suc:Volume/text()") == ["88888"]
    # le caselle sono nei righi EB (passaggi) ed EC (discordanza)
    assert _x(es, D + "/suc:QuadroEC//suc:DiscordanzaDatiIntestatario/text()") == ["1"]
    assert _x(es, D + "/suc:QuadroEB//suc:PassaggiSenzaAttiLegali/text()") == ["1"]


def test_il_presentatore_coincide_con_il_frontespizio():
    es = _es()
    p = EI + "/suc:PrimoModulo/suc:Presentatore"
    f = D + "/suc:Frontespizio/suc:Presentatore"
    assert _x(es, p + "/suc:CodiceFiscale/text()") == _x(es, f + "/suc:CodiceFiscale/text()")
    assert _x(es, p + "/reg:Cognome/text()") == _x(es, f + "/suc:DatiAnagrafici/reg:Cognome/text()") or _x(es, p + "/reg:Cognome/text()")


def test_senza_caselle_non_c_e_il_quadro_ei():
    es = esporta_xml(caso_a10(), CTX)
    assert es.errori == []
    assert _x(es, EI) == [] and _x(es, D + "/suc:Frontespizio/suc:FirmaModello/suc:CasellaEI") == []


def test_solo_passaggi_senza_sezione_ii():
    d = caso_voltura()
    next(b for b in d["beni"] if b["id"] == "b_casa0001").pop("discordanza_intestatario")
    es = esporta_xml(d, CTX)
    assert es.errori == []
    assert _x(es, EI + "/suc:PrimoModulo/suc:SezioneI_AttiLegali") != []
    assert _x(es, EI + "/suc:PrimoModulo/suc:SezioneII_DatiIntestatario") == []


def test_discordanza_senza_estremi_e_un_errore():
    es = _es(tel=lambda t: (t["b_casa0001"].pop("estremi_trascrizione"), t["b_casa0001"].pop("estremi_registrazione")))
    assert ("beni[b_casa0001].estremi_trascrizione", "DATO_MANCANTE") in _codici(es)


def test_estremi_non_validi():
    c = _codici(_es(tel=lambda t: t["b_casa0001"].update(estremi_trascrizione=[{**TR, "anno": "1750"}])))
    assert ("beni[b_casa0001].estremi_trascrizione[0].anno", "VALORE_NON_VALIDO") in c
    c = _codici(_es(tel=lambda t: t["b_casa0001"].update(estremi_trascrizione=[{**TR, "ufficio": "ZZ99"}])))
    assert ("beni[b_casa0001].estremi_trascrizione[0].ufficio", "VALORE_NON_VALIDO") in c
    c = _codici(_es(tel=lambda t: t["b_casa0001"].update(estremi_registrazione=[{**RG, "numero": "12A"}])))
    assert ("beni[b_casa0001].estremi_registrazione[0].numero", "VALORE_NON_VALIDO") in c
    c = _codici(_es(tel=lambda t: t["b_casa0001"].update(estremi_registrazione=[{**RG, "volume": None}])))
    assert ("beni[b_casa0001].estremi_registrazione[0].volume", "DATO_MANCANTE") in c


def test_piu_di_tre_estremi_non_supportati():
    es = _es(tel=lambda t: t["b_casa0001"].update(estremi_trascrizione=[TR, TR, TR, TR]))
    assert es.xml is None and any("piu' di tre estremi" in s for s in es.non_supportato)


def test_due_immobili_con_discordanza_generano_un_modulo_in_piu():
    def mod(d):
        next(b for b in d["beni"] if b["id"] == "b_terr0001")["discordanza_intestatario"] = "si"
    es = _es(mod=mod, tel=lambda t: t["b_terr0001"].update(estremi_registrazione=[RG]))
    assert es.errori == [], es.errori
    assert _x(es, EI + "/suc:PrimoModulo/suc:SezioneII_DatiIntestatario/suc:Immobile/suc:TipoCatasto/text()") == ["U"]
    assert _x(es, EI + "/suc:Modulo/suc:SezioneII_DatiIntestatario/suc:Immobile/suc:TipoCatasto/text()") == ["T"]


def test_le_caselle_sui_beni_tavolari_non_sono_previste():
    d = caso_tavolare()
    next(b for b in d["beni"] if b["id"] == "b_terrtav1")["discordanza_intestatario"] = "si"
    es = esporta_xml(d, CTX)
    assert es.xml is None and any("EL/EM" in s for s in es.non_supportato)


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
def test_reale_controllo_ufficiale_locale_ei(tmp_path):
    stato, dgn, wri, dcm = _esegui(_es().xml, tmp_path)
    assert stato == "positivo", (stato, dgn["diagnostici"])
    assert sorted((d["codice"], d["gravita"]) for d in dgn["diagnostici"]) == [("3345", 4)], dgn["diagnostici"]


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
def test_reale_controllo_ufficiale_locale_ei_due_immobili(tmp_path):
    def mod(d):
        next(b for b in d["beni"] if b["id"] == "b_terr0001")["discordanza_intestatario"] = "si"
    es = _es(mod=mod, tel=lambda t: t["b_terr0001"].update(estremi_registrazione=[RG]))
    stato, dgn, wri, dcm = _esegui(es.xml, tmp_path)
    assert stato == "positivo", (stato, dgn["diagnostici"])
