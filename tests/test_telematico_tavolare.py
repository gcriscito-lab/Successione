"""Quadri EL ed EM (sistema tavolare): XML completo, instradamento per provincia, regole delle annotazioni, EF senza
circoscrizioni, controllo SUC13 locale (dati sintetici; Bolzano: comune amministrativo A952, comune catastale 613)."""
from datetime import date

import pytest
from lxml import etree

from successioni import quadri as Q
from successioni.telematico.esporta import esporta_xml
from telematico_casi import caso_tavolare, contesto_caso_a10
from test_telematico_controllo import NS, _esegui, _motivo_salto

D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"
CTX = contesto_caso_a10(data_riferimento=date(2025, 9, 1))


def _es(id_=None, **mod):
    d = caso_tavolare()
    if id_:
        b = next(x for x in d["beni"] if x["id"] == id_)
        for k, v in mod.items():
            b.pop(k, None) if v is None else b.update({k: v})
    return esporta_xml(d, CTX)


def _codici(es):
    return {(e.percorso, e.codice) for e in es.errori}


def test_instradamento_per_provincia_e_flag():
    assert Q.quadro_di("beni", {"tipo": "terreno", "provincia": "BZ"}) == "EL"
    assert Q.quadro_di("beni", {"tipo": "fabbricato", "provincia": "tn"}) == "EM"
    assert Q.quadro_di("beni", {"tipo": "fabbricato", "provincia": "RM"}) == "EC"
    assert Q.quadro_di("beni", {"tipo": "terreno", "provincia": "BL", "sistema_tavolare": "si"}) == "EL"
    assert Q.quadro_di("beni", {"tipo": "terreno", "provincia": "BL"}) == "EB"


def test_xml_completo_tavolare_e_ef_senza_circoscrizioni():
    es = _es()
    assert es.errori == [] and es.non_supportato == [] and es.quadri_mancanti == [], (es.errori, es.non_supportato)
    doc = etree.fromstring(es.xml)
    t = lambda xp: doc.xpath(D + xp, namespaces=NS)
    assert t("/suc:QuadroEL/suc:Modulo/suc:TerreniTavolare/suc:DatiTerreniTavolare/reg:DatiTerreni/reg:PartitaTavolare/text()") == ["1234"]
    assert t("/suc:QuadroEL/suc:Modulo/suc:TerreniTavolare/suc:LuogoTavolare/reg:CodiceComuneCatastale/text()") == ["613"]
    assert t("/suc:QuadroEM/suc:Modulo/suc:FabbricatiTavolare/suc:DatiFabbricatiTavolare/reg:DatiFabbricati/reg:PartitaTavolare/text()") == ["5678"]
    assert t("/suc:QuadroEE/suc:TotaleValoreImmobili/text()") == ["98000"]
    assert t("/suc:Frontespizio/suc:CasiParticolari/suc:CasiParticolari/text()") == ["1"]
    assert t("/suc:QuadroEF/suc:SezioneIII_TassaIpotecaria") == [] and t("/suc:QuadroEF/suc:SezioneIV_ImpostaBollo") == []
    # EF1 comprende EL ed EM; EF9 (catastale) esclude i terreni tavolari
    assert t("/suc:QuadroEF/suc:SezioneI_ImpostaIpotecaria/suc:ImpostaProporzionale/suc:ImpostaProporzionale_Imponibile/text()") == ["98000"]
    assert t("/suc:QuadroEF/suc:SezioneII_ImpostaCatastale/suc:ImpostaProporzionale/suc:ImpostaProporzionale_Imponibile/text()") == ["90000"]


def test_partita_tavolare_obbligatoria_per_i_terreni():
    assert ("beni[b_terrtav1].partita_tavolare", "DATO_MANCANTE") in _codici(_es("b_terrtav1", partita_tavolare=None))


def test_comune_catastale_solo_per_tn_e_bz():
    es = _es("b_terrtav1", provincia="GO")
    assert ("beni[b_terrtav1].comune_catastale", "DATI_INCOERENTI") in _codici(es)
    assert ("beni[b_terrtav1].codice_comune_catastale", "VALORE_NON_VALIDO") in _codici(
        _es("b_terrtav1", codice_comune_catastale="99999"))


def test_provincia_non_tavolare_nel_quadro_tavolare():
    es = _es("b_terrtav1", provincia="RM", sistema_tavolare="si")
    assert ("beni[b_terrtav1].provincia", "VALORE_NON_VALIDO") in _codici(es)


def test_mutuo_sul_fabbricato_tavolare_usa_il_progressivo_em():
    es = _es()
    doc = etree.fromstring(es.xml)
    q = doc.xpath(D + "/suc:QuadroED//suc:ProgressivoCespite/suc:Quadro/text()", namespaces=NS)
    assert q == ["EM"]


def test_senza_devoluzione_e_un_errore():
    d = caso_tavolare()
    d["devoluzioni"] = [x for x in d["devoluzioni"] if x["bene_id"] != "b_fabbtav1"]
    es = esporta_xml(d, CTX)
    assert es.xml is None and any(e.codice == "DEVOLUZIONE_MANCANTE" for e in es.errori)


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
@pytest.mark.java
def test_reale_controllo_ufficiale_locale_tavolare(tmp_path):
    stato, dgn, wri, dcm = _esegui(_es().xml, tmp_path)
    assert stato == "positivo", (stato, dgn["diagnostici"])
    assert sorted((d["codice"], d["gravita"]) for d in dgn["diagnostici"]) == [("3345", 4)], dgn["diagnostici"]
