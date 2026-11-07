"""Usufrutto (08) e nuda proprieta' (02) su un bene in piena proprieta' del defunto: dati SINTETICI.

Fonti: Fascicolo I pp. PDF 24-25 (quota 1/1 per ciascun diritto, valore quota, esempio 2025); D.Lgs. 123/2025 artt. 99 e
102, allegato 4 (coefficienti per eta'). Scheda: docs/regole/usufrutto.md."""
import copy
from datetime import date
from fractions import Fraction

import pytest
from lxml import etree

import telematico_casi as T
from successioni.telematico import usufrutto as USU
from successioni.telematico.esporta import esporta_xml
from test_telematico_controllo import NS, _esegui, _motivo_salto

SALTO = _motivo_salto()
DEV = "//suc:Devoluzione"


def test_esempio_del_fascicolo_2025():
    """Fascicolo I p. PDF 25: 200.000 x 50% posseduto; EA1 nuda 1/1, EA2 usufrutto 1/2 (19 anni), EA3 usufrutto 1/2 (25)."""
    righe = [{"id": "ea1", "diritto": "2", "quota": Fraction(1), "coefficiente": None},
             {"id": "ea2", "diritto": "8", "quota": Fraction(1, 2), "coefficiente": USU.coefficiente(19)},
             {"id": "ea3", "diritto": "8", "quota": Fraction(1, 2), "coefficiente": USU.coefficiente(25)}]
    r = USU.valori(100000, righe)
    assert not r["errori"]
    assert r["valori"] == {"ea2": 47500, "ea3": 45000, "ea1": 7500}


def test_esempio_nuda_proprieta_p31():
    """Fascicolo I p. PDF 31: coefficiente 20, 100.000 di quota: nuda proprieta' 50.000 (eta' 64-66)."""
    assert USU.coefficiente(65) == 20
    r = USU.valori(100000, [{"id": "u", "diritto": "8", "quota": Fraction(1), "coefficiente": 20},
                            {"id": "n", "diritto": "2", "quota": Fraction(1), "coefficiente": None}])
    assert r["valori"] == {"u": 50000, "n": 50000}


@pytest.mark.parametrize("anni,coef", [(0, 38), (20, 38), (21, 36), (45, 32), (46, 30), (66, 20), (82, 10), (99, 4),
                                       (100, None)])
def test_prospetto_allegato_4(anni, coef):
    assert USU.coefficiente(anni) == coef


def test_eta_compiuta_al_decesso():
    assert USU.eta(date(1970, 3, 11), date(2025, 3, 10)) == 54
    assert USU.eta(date(1970, 3, 10), date(2025, 3, 10)) == 55


def test_quote_incomplete_segnalate():
    r = USU.valori(1000, [{"id": "u", "diritto": "8", "quota": Fraction(1, 2), "coefficiente": 20},
                          {"id": "n", "diritto": "2", "quota": Fraction(1), "coefficiente": None}])
    assert r["errori"] and not r["valori"]


def _caso(diritto_anna="8", diritto_luca="2", nascita_anna="1970-01-01", decesso=None):
    c = copy.deepcopy(T.caso_testamento())
    for d in c["devoluzioni"]:
        if d["bene_id"] == "b_casa0001":
            d["quota"] = {"num": 1, "den": 1}
            d["diritto"] = diritto_anna if d["persona_id"] == "p_anna0001" else diritto_luca
    for p in c["persone"]:
        if p["id"] == "p_anna0001":
            p["data_nascita"] = nascita_anna
        if decesso and p["ruolo"] == "defunto":
            p["data_decesso"] = decesso
    return c


def _valori_quota(es):
    x = etree.fromstring(es.xml)
    out = {}
    for d in x.xpath("//suc:QuadroEC//suc:Devoluzione", namespaces=NS):
        diritto = d.xpath("suc:CodiceDiritto_Rip/text()", namespaces=NS)[0]
        out[diritto] = d.xpath("suc:Quota/suc:QuotaValore/text()", namespaces=NS)[0]
    return out


def _valore_casa(c):
    return int(next(b for b in c["beni"] if b["id"] == "b_casa0001")["valore"])


def test_export_usufrutto_e_nuda_proprieta():
    c = _caso()
    es = esporta_xml(c, T.contesto_caso_a10())
    assert es.completo, ([e.messaggio for e in es.errori], es.non_supportato, [m.messaggio for m in es.quadri_mancanti])
    v = _valore_casa(c)
    # Anna nata il 1/1/1970, decesso 2025: 55 anni -> coefficiente 26; usufrutto = v x 2,5% x 26
    usu = Fraction(v) * Fraction(25, 1000) * 26
    q = _valori_quota(es)
    assert Fraction(q["8"].replace(",", ".")) == usu
    assert Fraction(q["2"].replace(",", ".")) == v - usu
    assert not [a for a in es.avvisi if a.codice == "SAGGIO_USUFRUTTO_DA_VERIFICARE"]   # decesso 2025: saggio letto


def test_usufrutto_senza_data_di_nascita_bloccato():
    c = _caso(nascita_anna=None)
    for p in c["persone"]:
        if p["id"] == "p_anna0001":
            p.pop("data_nascita", None)
    es = esporta_xml(c, T.contesto_caso_a10())
    assert not es.completo


def test_decesso_2026_avviso_sul_saggio():
    c = _caso(decesso="2026-02-10")
    es = esporta_xml(c, T.contesto_caso_a10(data_riferimento=date(2026, 3, 1)))
    assert any(a.codice == "SAGGIO_USUFRUTTO_DA_VERIFICARE" for a in es.avvisi), [a.codice for a in es.avvisi]


def test_decesso_prima_del_2025_non_supportato():
    c = _caso(decesso="2024-06-10")
    es = esporta_xml(c, T.contesto_caso_a10(scopo="bozza_tecnica"))
    assert any("2025" in n for n in es.non_supportato)


def test_altri_diritti_distinti_restano_non_supportati():
    c = _caso(diritto_anna="7")          # uso: non gestito
    es = esporta_xml(c, T.contesto_caso_a10(scopo="bozza_tecnica"))
    assert any("diverso dal diritto del defunto" in n for n in es.non_supportato)


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
def test_controllo_ufficiale_usufrutto_e_nuda(tmp_path):
    es = esporta_xml(_caso(), T.contesto_caso_a10())
    assert es.completo
    stato, dgn, _, _ = _esegui(es.xml, tmp_path)
    assert stato == "positivo", dgn
