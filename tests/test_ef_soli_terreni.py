"""EF con soli terreni (EB): regola dei valori fiscali (annotazioni XSD ImpostaProporzionale_Imposta di EF1 ed EF9; Fascicolo I
pp. PDF 40 e 43). Valore fiscale = somma dei redditi dominicali x quota del defunto x 112,5. Se e' inferiore alla somma delle
imposte proporzionali, EF1 = 2/3 e EF9 = 1/3 del valore fiscale; altrimenti imposta proporzionale con minimo 200 nella colonna 2.
Ogni caso e' stato accettato dal controllo ufficiale SUC13 2.3.1 eseguito in locale il 2026-11-05 (dati sintetici)."""
import copy

import pytest
from lxml import etree

from telematico_casi import caso_a10, contesto_caso_a10
from successioni.telematico.esporta import esporta_xml
from test_telematico_controllo import _esegui, _motivo_salto

EF = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione/suc:QuadroEF"


def solo_terreni(valore, rd=None, tipologia="3"):
    d = copy.deepcopy(caso_a10())
    d["beni"] = [b for b in d["beni"] if b["id"] != "b_casa0001"]
    d["devoluzioni"] = [x for x in d["devoluzioni"] if x["bene_id"] != "b_casa0001"]
    d["passivita"] = [p for p in d["passivita"] if p["id"] == "ps_medic01"]
    t = d["opzioni"]["telematico"]
    t["passivita"] = {k: v for k, v in t["passivita"].items() if k == "ps_medic01"}
    del t["beni"]["b_casa0001"]
    d["beni"][0]["valore"] = valore
    t["beni"]["b_terr0001"]["tipologia_terreno"] = tipologia
    if rd:
        t["beni"]["b_terr0001"]["reddito_dominicale"] = rd
    return d


def esporta(d):
    es = esporta_xml(d, contesto_caso_a10())
    assert es.completo, [e.messaggio for e in es.errori] + es.non_supportato + [m.messaggio for m in es.quadri_mancanti]
    return es


def col2(es):
    doc = etree.fromstring(es.xml)
    ns = {k: v for k, v in doc.nsmap.items() if k}
    f = lambda xp: doc.xpath(f"{EF}/{xp}/text()", namespaces=ns)
    return (f("suc:SezioneI_ImpostaIpotecaria/suc:ImpostaProporzionale/suc:ImpostaProporzionale_Imposta"),
            f("suc:SezioneII_ImpostaCatastale/suc:ImpostaProporzionale/suc:ImpostaProporzionale_Imposta"),
            f("suc:TotaleDaVersare"))


# reddito dominicale 12,34 x 1/2 x 112,5 = 694,125 (valore fiscale)
@pytest.mark.parametrize("valore,rd,atteso", [
    ("15000", None, (["300"], ["200"], ["705,00"])),        # vf 694 > 450 (300+150): imposta ordinaria, catastale al minimo 200
    ("3000", None, (["200"], ["200"], ["605,00"])),         # imposte sotto il minimo di 200 nella colonna 2
    ("100000", None, (["463"], ["231"], ["899,00"])),       # vf 694 < 3000: 2/3 e 1/3 del valore fiscale
    ("100000", "0.50", (["19"], ["9"], ["233,00"])),        # valore fiscale minuscolo: nessun minimo
    ("20000", None, (["400"], ["200"], ["805,00"])),        # vf 694 > 600: imposta ordinaria
])
def test_soli_terreni_non_edificabili(valore, rd, atteso):
    assert col2(esporta(solo_terreni(valore, rd))) == atteso


@pytest.mark.parametrize("valore,atteso", [
    ("3000", (["60"], ["30"], ["605,00"])),                 # edificabile: imposta ordinaria, minimo 200 solo nel dovuto
    ("100000", (["2000"], ["1000"], ["3205,00"])),
])
def test_terreni_edificabili_regola_ordinaria(valore, atteso):
    assert col2(esporta(solo_terreni(valore, tipologia="1"))) == atteso


def test_reddito_dominicale_mancante_blocca():
    d = solo_terreni("100000")
    del d["opzioni"]["telematico"]["beni"]["b_terr0001"]["reddito_dominicale"]
    es = esporta_xml(d, contesto_caso_a10())
    assert es.xml is None and any("reddito dominicale" in m.messaggio for m in es.quadri_mancanti + [])


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
@pytest.mark.parametrize("valore,rd,tip", [("15000", None, "3"), ("100000", None, "3"), ("100000", "0.50", "3"),
                                           ("3000", None, "1"), ("100000", None, "1")])
@pytest.mark.java
def test_controllo_ufficiale_locale(tmp_path, valore, rd, tip):
    es = esporta(solo_terreni(valore, rd, tip))
    stato, dgn, wri, _ = _esegui(es.xml, tmp_path)
    assert stato == "positivo", (dgn["diagnostici"], wri[:900])
