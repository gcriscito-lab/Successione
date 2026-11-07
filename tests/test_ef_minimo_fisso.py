"""EF: imposta proporzionale inferiore alla fissa (200 euro). Colonna 2 = imposta calcolata; il minimo di 200 euro vale solo
nel totale dovuto (annotazioni XSD ImpostaIpotecariaDovuta/ImpostaCatastaleDovuta). Il controllo ufficiale SUC13 2.3.1, eseguito
in locale il 2026-11-05, respinge 200 nella colonna 2 («valore corretto 140») e accetta questa forma."""
import copy

import pytest
from lxml import etree

from telematico_casi import caso_a10, contesto_caso_a10
from successioni.telematico.esporta import esporta_xml
from test_telematico_controllo import _esegui, _motivo_salto

D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione/suc:QuadroEF"


def piccolo(casa="5000", terreno="2000"):
    d = copy.deepcopy(caso_a10())
    d["beni"][0]["valore"], d["beni"][1]["valore"] = casa, terreno
    d["passivita"] = [p for p in d["passivita"] if p["id"] == "ps_medic01"]       # il mutuo supererebbe l'attivo
    t = d["opzioni"]["telematico"]["passivita"]
    d["opzioni"]["telematico"]["passivita"] = {k: v for k, v in t.items() if k == "ps_medic01"}
    return d


def v(es, xp):
    doc = etree.fromstring(es.xml)
    return doc.xpath(f"{D}/{xp}/text()", namespaces={k: x for k, x in doc.nsmap.items() if k})


def test_proporzionale_sotto_la_fissa():
    es = esporta_xml(piccolo(), contesto_caso_a10())
    assert es.completo, [e.messaggio for e in es.errori] + es.non_supportato + [m.messaggio for m in es.quadri_mancanti]
    # 7.000 euro: ipotecaria 2% = 140, catastale 1% = 70 -> colonna 2 invariata, dovuto minimo 200 + 200
    assert v(es, "suc:SezioneI_ImpostaIpotecaria/suc:ImpostaProporzionale/*") == ["7000", "140"]
    assert v(es, "suc:SezioneI_ImpostaIpotecaria/suc:ImpostaIpotecariaDovuta") == ["200"]
    assert v(es, "suc:SezioneI_ImpostaIpotecaria/suc:ImpostaIpotecariaDaVersare") == ["200"]
    assert v(es, "suc:SezioneII_ImpostaCatastale/suc:ImpostaProporzionale/*") == ["7000", "70"]
    assert v(es, "suc:SezioneII_ImpostaCatastale/suc:ImpostaCatastaleDovuta") == ["200"]
    assert v(es, "suc:TotaleDaVersare") == ["605,00"]            # 200 + 200 + 120 + 85


def test_sopra_la_fissa_invariato():
    es = esporta_xml(piccolo("126000", "15000"), contesto_caso_a10())
    assert es.completo and v(es, "suc:SezioneI_ImpostaIpotecaria/suc:ImpostaIpotecariaDovuta") == ["2820"]


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
@pytest.mark.java
def test_controllo_ufficiale_locale(tmp_path):
    es = esporta_xml(piccolo(), contesto_caso_a10())
    stato, dgn, wri, _ = _esegui(es.xml, tmp_path)
    assert stato == "positivo", (dgn["diagnostici"], wri[:900])
    # variante secondo la lettura del Fascicolo (200 nella colonna 2): il controllo la respinge
    xml = es.xml.replace(b">140<", b">200<", 1)
    assert xml != es.xml
    stato2, dgn2, _, _ = _esegui(xml, tmp_path / "ko", rapporto=False)
    assert stato2 == "negativo" and any(x["codice"] == "3076" for x in dgn2["diagnostici"]), dgn2["diagnostici"]
