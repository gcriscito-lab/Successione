"""Importazione SUC13: il valore quota (QuotaValore) di ogni riga di devoluzione e' ricalcolato dalla riesportazione e confrontato
con l'originale (avviso con i due valori oltre il centesimo, docs/regole/dubbio_arrotondamento.md § 7); il cambio d'ordine del
quadro EA fra file e riesportazione (esporta.ordina_ea) e' segnalato come per i righi dei beni. Dati SINTETICI."""
import copy

from lxml import etree

import telematico_casi as T
from successioni.telematico.esporta import esporta_xml
from successioni.telematico.importa import NS, importa_xml
from test_usufrutto import _caso

OGGI = T.contesto_caso_a10().data_riferimento


def _xml_usufrutto():
    c = _caso()
    for b in c["beni"]:
        if b["id"] == "b_casa0001":
            b["valore"] = "126000"       # usufrutto 55 anni: 126.000 x 2,5% x 26 = 81.900
    es = esporta_xml(c, T.contesto_caso_a10())
    assert es.completo, [e.messaggio for e in es.errori]
    return es.xml


def _valori(xml):
    doc = etree.fromstring(xml)
    return doc, doc.xpath("//suc:QuadroEC//suc:Devoluzione/suc:Quota/suc:QuotaValore", namespaces=NS)


def test_quota_valore_identico_nessun_avviso():
    xml = _xml_usufrutto()
    _, qv = _valori(xml)
    assert "81900,00" in [e.text for e in qv]
    avvisi = importa_xml(xml, data_riferimento=OGGI)["avvisi"]
    assert not [a for a in avvisi if a.startswith("QuotaValore")], avvisi


def test_quota_valore_alterato_segnalato_con_i_due_valori():
    doc, qv = _valori(_xml_usufrutto())
    for e in qv:
        if e.text == "81900,00":
            e.text = "75600,00"
    xml = etree.tostring(doc, xml_declaration=True, encoding="UTF-8")
    avvisi = [a for a in importa_xml(xml, data_riferimento=OGGI)["avvisi"] if a.startswith("QuotaValore")]
    assert len(avvisi) == 1, avvisi
    assert "originale 75600,00" in avvisi[0] and "ricalcolato 81900,00" in avvisi[0]
    assert "QuadroEC modulo 1 rigo 1" in avvisi[0] and "diritto 8" in avvisi[0]


def test_differenza_entro_il_centesimo_non_segnalata():
    doc, qv = _valori(_xml_usufrutto())
    for e in qv:
        if e.text == "81900,00":
            e.text = "81900,01"
    xml = etree.tostring(doc, xml_declaration=True, encoding="UTF-8")
    assert not [a for a in importa_xml(xml, data_riferimento=OGGI)["avvisi"] if a.startswith("QuotaValore")]


def _scambia_ea(xml: bytes) -> bytes:
    """Scambia i primi due soggetti del quadro EA e aggiorna tutti i riferimenti Rigo/Modulo (stessi dati, ordine diverso)."""
    doc = etree.fromstring(xml)
    mod = doc.xpath("//suc:QuadroEA/suc:Modulo", namespaces=NS)[0]
    s1, s2 = mod.xpath("suc:Soggetto", namespaces=NS)[:2]
    i1, i2 = mod.index(s1), mod.index(s2)
    mod.remove(s2)
    mod.insert(i1, s2)
    assert mod.index(s1) == i2
    for ids in doc.xpath("//suc:IdentificazioneSoggetto[suc:Modulo='1']", namespaces=NS):
        r = ids.find(f"{{{NS['suc']}}}Rigo")
        r.text = {"1": "2", "2": "1"}.get(r.text, r.text)
    return etree.tostring(doc, xml_declaration=True, encoding="UTF-8")


def test_ordine_ea_diverso_segnalato():
    es = esporta_xml(copy.deepcopy(T.caso_a10()), T.contesto_caso_a10())
    assert not [a for a in importa_xml(es.xml, data_riferimento=OGGI)["avvisi"] if a.startswith("QuadroEA")]
    avvisi = [a for a in importa_xml(_scambia_ea(es.xml), data_riferimento=OGGI)["avvisi"] if a.startswith("QuadroEA")]
    assert len(avvisi) == 1 and "2 soggetti su" in avvisi[0], avvisi
