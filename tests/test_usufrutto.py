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


@pytest.mark.parametrize("imposta", [None, "3000"])
def test_immobile_estero_con_imposta_estera_e_diritti_distinti(imposta):
    """DET.estero: IE = imposta estera x quota di devoluzione (guida al calcolo pp. 7-8). Con usufrutto 1/1 e nuda proprieta'
    1/1 le quote sommano a 2: l'imposta estera sarebbe detratta due volte. Il caso e' bloccato come non supportato; senza
    imposta estera l'immobile estero con diritti distinti resta esportabile."""
    from test_beni_esteri import ctx, immobile_estero
    c = _caso()
    bid = immobile_estero(c, "EC", valore="60000", imposta=imposta)
    for d in c["devoluzioni"]:
        if d["bene_id"] == bid:
            d["quota"] = {"num": 1, "den": 1}
            d["diritto"] = "8" if d["persona_id"] == "p_anna0001" else "2"
    es = esporta_xml(c, ctx())
    msg = [n for n in es.non_supportato if "imposta versata all'estero" in n and "diritti distinti" in n]
    if imposta:
        assert msg and not es.completo, es.non_supportato
    else:
        assert not msg
        assert es.completo, ([e.messaggio for e in es.errori], es.non_supportato)


def test_messaggio_arrotondamento_con_diritti_distinti():
    """Il valore quota della nuda proprieta' non e' valore x quota: il messaggio di arrotondamento indica la regola usata."""
    c = _caso()
    next(b for b in c["beni"] if b["id"] == "b_casa0001")["valore"] = "126001"
    for d in c["devoluzioni"]:
        if d["bene_id"] == "b_casa0001" and d["persona_id"] == "p_luca0001":
            d["quota"] = {"num": 1, "den": 3}
    c["devoluzioni"].append({"id": "d_casaann2", "_origine": {}, "bene_id": "b_casa0001", "persona_id": "p_anna0001",
                             "quota": {"num": 2, "den": 3}, "diritto": "2"})
    es = esporta_xml(c, T.contesto_caso_a10())
    assert es.completo, ([e.messaggio for e in es.errori], es.non_supportato)
    arr = [a.messaggio for a in es.avvisi if a.codice == "ARROTONDAMENTO_VALORE_QUOTA"]
    assert arr and all("diritto 2" in m and "meno la parte del diritto che lo grava" in m for m in arr), arr
    assert not any(m.startswith("valore quota 126001 x") for m in arr)


def _caso_per_legge(diritto_anna="8", diritto_luca="2"):
    """caso_a10 (devoluzione per legge) con la casa devoluta ad Anna e Luca con diritti distinti 1/1 ciascuno."""
    c = copy.deepcopy(T.caso_a10())
    for d in c["devoluzioni"]:
        if d["bene_id"] == "b_casa0001":
            d["quota"] = {"num": 1, "den": 1}
            d["diritto"] = diritto_anna if d["persona_id"] == "p_anna0001" else diritto_luca
    for p in c["persone"]:
        if p["id"] == "p_anna0001":
            p["data_nascita"] = "1970-01-01"
    return c


def test_usufrutto_e_nuda_per_legge_bloccati():
    """Annotazione XSD di CodiceDiritto_Rip (fornituraSUC13_v1.xsd): con devoluzione per legge i codici diritto della
    sezione devoluzione devono coincidere con quello del defunto: usufrutto e nuda proprieta' distinti sono bloccati."""
    es = esporta_xml(_caso_per_legge(), T.contesto_caso_a10())
    assert not es.completo
    err = [e for e in es.errori if e.codice == "REGOLA_CODICE_DIRITTO"]
    assert len(err) == 2, [(e.codice, e.messaggio) for e in es.errori]
    assert all("CodiceDiritto_Rip" in e.fonte for e in err)


def test_usufrutto_per_legge_ammesso_con_legge_estera():
    c = _caso_per_legge()
    c["opzioni"]["telematico"]["dichiarazione"]["legge_estera"] = True
    es = esporta_xml(c, T.contesto_caso_a10(scopo="bozza_tecnica"))
    assert not [e for e in es.errori if e.codice == "REGOLA_CODICE_DIRITTO"]


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
def test_controllo_ufficiale_per_legge_codici_coincidenti(tmp_path):
    """Lo stesso caso corretto per legge (codice diritto 1 e quote dell'allegato 5, come in caso_a10) e' accettato dal
    controllo ufficiale eseguito in locale; la variante con 8/2 non produce piu' un file «completo»."""
    assert not esporta_xml(_caso_per_legge(), T.contesto_caso_a10()).completo
    es = esporta_xml(copy.deepcopy(T.caso_a10()), T.contesto_caso_a10())
    assert es.completo, [e.messaggio for e in es.errori]
    stato, dgn, _, _ = _esegui(es.xml, tmp_path)
    assert stato == "positivo", dgn
