"""Importazione SUC13: i dati del quadro EF/EH DICHIARATI dal professionista (sanzioni e interessi della Sezione VI, tempistica,
rateazione e acconto di EF18ter, crediti d'imposta di EF7/EF13/EF18bis ed EH Sezione III) si importano nelle chiavi che
l'esportazione usa, cosi' la riesportazione e' identica; se il quadro EF ricalcolato differisce dall'originale c'e' un avviso con i
due valori (difetto emerso il 2026-11-07 su una tardiva reale: ImportoDaVersare sceso senza avviso). Dati SINTETICI."""
import datetime

import pytest
from lxml import etree

from successioni.archivio import Archivio
from successioni.servizio import Servizio
from successioni.telematico.esporta import esporta_xml
from successioni.telematico.importa import NS, importa_xml
from telematico_casi import contesto_caso_a10
from test_pagamenti_crediti import ACQ, ACQ2, CREDITO_REGISTRO, TEMPESTIVO, VEN, caso, caso_grosso

OGGI = datetime.date(2026, 11, 1)          # data predefinita di contesto_caso_a10: tardiva per i decessi del 2025-03-10


def _d2024(**dich):
    d = caso(**dich)
    d["persone"][0]["data_decesso"] = "2024-03-10"
    return d


CASI = {
    "tardiva_successione_e_ipotecaria": (lambda: caso_grosso(tempistica_pagamento="2", sanzione_successione="500.00",
                                                             interessi_successione="40.00", sanzione_ipotecaria="150.50",
                                                             interessi_ipotecaria="20.10"), OGGI),
    "tardiva_sanzione_nulla": (lambda: caso_grosso(tempistica_pagamento="2", sanzione_successione="0", interessi_successione="0"), OGGI),
    "sanzioni_ipocatastali_2024": (lambda: _d2024(sanzione_ipotecaria="150.50", interessi_ipotecaria="20.10",
                                                  sanzione_catastale="75.25", interessi_catastale="10.05"), OGGI),
    "sanzioni_tassa_e_bollo": (lambda: caso(sanzione_tassa_ipotecaria="10.00", interessi_bollo="1.50"), OGGI),
    "tardiva_rateale": (lambda: caso_grosso(tempistica_pagamento="2", pagamento_rateale=8, acconto="5000",
                                            sanzione_successione="500.00", interessi_successione="40.00"), OGGI),
    "tempestiva_rateale_tempistica_1": (lambda: caso_grosso(tempistica_pagamento="1", pagamento_rateale=8, acconto="5000"), TEMPESTIVO),
    "credito_ef7_con_vendita": (lambda: caso(credito_ipotecaria="1000", credito_vendita=VEN, **CREDITO_REGISTRO), OGGI),
    "credito_tipologia_3": (lambda: caso(credito_ipotecaria="1000", credito_imposta="5000", credito_tipologia="3",
                                         credito_acquisto=ACQ), OGGI),
    "credito_su_successione": (lambda: caso_grosso(tempistica_pagamento="2", credito_ipotecaria="2820", credito_catastale="1410",
                                                   credito_successione="1000", **CREDITO_REGISTRO), TEMPESTIVO),
}


def _esporta(d, data):
    es = esporta_xml(d, contesto_caso_a10(data_riferimento=data))
    assert es.completo, [e.messaggio for e in es.errori] + [m.messaggio for m in es.quadri_mancanti]
    return es


@pytest.fixture
def sv(tmp_path):
    return Servizio(Archivio(tmp_path / "dati"))


def _ef(xml: bytes):
    d = etree.fromstring(xml).xpath("//suc:Fornitura/suc:Dichiarazione", namespaces=NS)[0]
    return (etree.tostring(d.find(f"{{{NS['suc']}}}QuadroEF")),
            d.xpath("suc:Frontespizio/suc:ImportoDaVersare/text()", namespaces=NS))


@pytest.mark.parametrize("nome", sorted(CASI))
def test_andata_e_ritorno_identica_con_dati_dichiarati_di_ef_eh(sv, nome):
    costruisci, data = CASI[nome]
    d = costruisci()
    originale = _esporta(d, data)
    r = sv.importa_xml_telematico(originale.xml)
    dati = sv.leggi(r["pratica_id"])["dati"]
    dati["documenti_ref"] = d["documenti_ref"]                         # gli allegati si riacquisiscono
    dati["opzioni"]["telematico"]["dichiarazione"]["dichiara_copie_conformi"] = True
    nuovo = esporta_xml(dati, contesto_caso_a10(data_riferimento=data))
    assert nuovo.errori == [], [e.messaggio for e in nuovo.errori]
    assert _ef(nuovo.xml) == _ef(originale.xml)                        # quadro EF (Sezione VI inclusa) e ImportoDaVersare
    assert nuovo.xml == originale.xml
    # alla stessa data della riesportazione nessun avviso di differenza
    assert not [a for a in importa_xml(originale.xml, data_riferimento=data)["avvisi"] if "QuadroEF" in a or "ImportoDaVersare" in a]


def test_chiavi_importate():
    es = _esporta(caso_grosso(tempistica_pagamento="2", pagamento_rateale=8, acconto="5000", sanzione_successione="500.00",
                              interessi_successione="40.00", sanzione_ipotecaria="150.50"), OGGI)
    dich = importa_xml(es.xml, data_riferimento=OGGI)["operazioni"][-1]["campi"]["telematico"]["dichiarazione"]
    assert {k: dich[k] for k in ("tempistica_pagamento", "pagamento_rateale", "acconto", "sanzione_successione",
                                 "interessi_successione", "sanzione_ipotecaria")} == {
        "tempistica_pagamento": "2", "pagamento_rateale": 8, "acconto": "5000", "sanzione_successione": "500.00",
        "interessi_successione": "40.00", "sanzione_ipotecaria": "150.50"}
    assert "interessi_ipotecaria" not in dich

    es = _esporta(caso(credito_ipotecaria="1000", credito_vendita=VEN, **CREDITO_REGISTRO), OGGI)
    dich = importa_xml(es.xml, data_riferimento=OGGI)["operazioni"][-1]["campi"]["telematico"]["dichiarazione"]
    assert dich["credito_ipotecaria"] == "1000"
    assert (dich["credito_tipologia"], dich["credito_imposta"], dich["credito_tipologia_2"], dich["credito_imposta_2"]) == (
        "1", "6000", "1", "6200")
    assert dich["credito_acquisto"] == ACQ and dich["credito_acquisto_2"] == ACQ2 and dich["credito_vendita"] == VEN


def _alterato(xml: bytes, percorso: str, valore: str) -> bytes:
    doc = etree.fromstring(xml)
    for e in doc.xpath(f"//suc:Fornitura/suc:Dichiarazione/{percorso}", namespaces=NS):
        e.text = valore
    return etree.tostring(doc, xml_declaration=True, encoding="UTF-8")


def test_avviso_se_importo_da_versare_ricalcolato_diverso():
    es = _esporta(caso_grosso(tempistica_pagamento="2", sanzione_successione="500.00", interessi_successione="40.00"), OGGI)
    originale = _ef(es.xml)[1][0]
    assert originale == "27371,00"                                     # EF19 26831 + sanzioni 500 + interessi 40
    xml = _alterato(es.xml, "suc:Frontespizio/suc:ImportoDaVersare", "99999,99")
    xml = _alterato(xml, "suc:QuadroEF/suc:TotaleDaVersare", "88888,00")
    avvisi = importa_xml(xml, data_riferimento=OGGI)["avvisi"]
    imp = [a for a in avvisi if a.startswith("ImportoDaVersare")]
    assert len(imp) == 1 and "originale 99999,99" in imp[0] and f"ricalcolato {originale}" in imp[0]
    ef = [a for a in avvisi if a.startswith("QuadroEF ricalcolato")]
    assert len(ef) == 1 and "TotaleDaVersare: originale 88888,00, ricalcolato 26831,00" in ef[0]


def test_avviso_se_il_quadro_ef_non_e_ricalcolabile():
    """Rateazione con tempistica 1 indicata nei termini, riesportata oltre i 90 giorni: il quadro EF non si genera piu'."""
    es = _esporta(caso_grosso(tempistica_pagamento="1", pagamento_rateale=8, acconto="5000"), TEMPESTIVO)
    avvisi = importa_xml(es.xml, data_riferimento=OGGI)["avvisi"]
    msg = [a for a in avvisi if a.startswith("QuadroEF non ricalcolabile")]
    assert len(msg) == 1 and "ImportoDaVersare 4435,00" in msg[0] and "TotaleDaVersare 4435,00" in msg[0]


def test_dato_dichiarato_di_ef_non_importato_e_segnalato():
    es = _esporta(caso(), OGGI)
    doc = etree.fromstring(es.xml)
    s1 = doc.xpath("//suc:QuadroEF/suc:SezioneI_ImpostaIpotecaria", namespaces=NS)[0]
    v = etree.SubElement(s1, f"{{{NS['suc']}}}ImpostaIpotecariaVersata")
    v.text = "100"
    avvisi = importa_xml(etree.tostring(doc), data_riferimento=OGGI)["avvisi"]
    # revisione 2 (2026-11-07): EF6 (imposta gia' versata) e' importata per le sostitutive; in una prima dichiarazione resta
    # un avviso esplicito perche' la riesportazione non la scrive
    assert any("SezioneI_ImpostaIpotecaria/ImpostaIpotecariaVersata = 100 in una prima dichiarazione" in a for a in avvisi), avvisi
    v.tag = f"{{{NS['suc']}}}CampoNonRicalcolato"
    avvisi = importa_xml(etree.tostring(doc), data_riferimento=OGGI)["avvisi"]
    assert any("SezioneI_ImpostaIpotecaria/CampoNonRicalcolato = 100 non importato" in a for a in avvisi), avvisi


def test_sezione_eh_non_importata_e_dichiarata():
    es = _esporta(caso(), OGGI)
    doc = etree.fromstring(es.xml)
    pm = doc.xpath("//suc:QuadroEH/suc:PrimoModulo", namespaces=NS)[0]
    sez = etree.SubElement(pm, f"{{{NS['suc']}}}SezioneIV_AltreAgevRiduz")
    etree.SubElement(sez, f"{{{NS['suc']}}}Qualsiasi").text = "1"
    r = importa_xml(etree.tostring(doc), data_riferimento=OGGI)
    # revisione 2 (2026-11-07): la Sezione IV si importa (riduzioni_art25); il campo che non si legge resta elencato
    assert ("QuadroEH SezioneIV_AltreAgevRiduz: campi non importati, da reinserire: PrimoModulo/SezioneIV_AltreAgevRiduz/"
            "Qualsiasi = 1") in r["non_importato"], r["non_importato"]
