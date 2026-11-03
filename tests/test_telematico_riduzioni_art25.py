"""Riduzioni dell'art. 25 (codici 1-5 con valore precedenti successioni) e agevolazioni L, Q, R, F: regole da
``docs/regole/riduzioni_art25.md`` (fonti: XSD SUC13_20250702, Fascicolo I, guida al calcolo pp. 5-7). Dati SINTETICI.

- Il calcolo e' confrontato con un calcolo INDIPENDENTE scritto a mano nel test (``Fraction``, formule della guida, valori
  letterali verificabili con carta e penna) e non con il codice di ``calcolo.py``.
- Il controllo ufficiale SUC13 locale (SUCCESSIONI_JAVA, SUCCESSIONI_CONTROLLI_SUC13; stessa preparazione di
  ``test_telematico_controllo.py``) e' eseguito sui casi positivi (nessuno scarto) e su negativi. Il componente
  ricalcola l'imposta (diagnostico 3454/3481 se EF18bis non corrisponde): l'importo intero dichiarato e' confermato
  con la prova «EF18bis +1 e -1 scartato». Senza le variabili le prove 'reale' sono saltate con il motivo.
"""
from __future__ import annotations

import copy
from datetime import date
from decimal import ROUND_HALF_UP, Decimal as Dc, localcontext
from fractions import Fraction as Fr

import pytest
from lxml import etree

from successioni.telematico.calcolo import calcola, calcola_da_xml, riduzioni_componente, riduzioni_esatte
from successioni.telematico.esporta import esporta_xml
from telematico_casi import (FIXTURE, ALLEGATI_A10, aggiungi_fabbricato, caso_a10, caso_azienda, caso_mezzi,
                             caso_tavolare, caso_titoli, contesto)
from test_telematico_calcolo import _fratelli
from test_telematico_controllo import NS, _esegui, _motivo_salto

D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"
PDF = {"percorso": str(FIXTURE / "allegati" / "albero_genealogico.pdf")}
ALLEGATI = {**ALLEGATI_A10, "al_rid": {**PDF, "nome": "riduzioni.pdf"}, "al_ident": {**PDF, "nome": "identita.pdf"},
            "al_altro": {**PDF, "nome": "attestazione.pdf"}}
CTX = contesto(allegati=ALLEGATI, data_riferimento=date(2026, 3, 9))   # decesso 2025-03-10: entro i 12 mesi
SALTO = pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
SUCC_PREC = {"ufficio": "795", "anno": "2024", "volume": "88888", "numero": "123"}
DICH_ART25 = {"dichiara_requisiti": True, "successione_precedente": SUCC_PREC}
DICH_Q = {"dichiara_requisiti": True}
DICH_L = {"dichiara_requisiti": True, "l": {"num_protocollo": "PROT-001", "data": "2025-09-01"}}
ANNA_EA, LUCA_EA = "1/1", "1/2"      # rigo/modulo del quadro EA (Anna = dichiarante)


def _tel(d):
    return d["opzioni"]["telematico"]


def _dich(d):
    return _tel(d)["dichiarazione"]


def base(casa="2400000"):
    """caso_a10 (due figli, 1/2 ciascuno, grado 02) con la casa a ``casa`` euro: oltre la franchigia di 1.000.000 per erede."""
    d = caso_a10()
    d["beni"][0]["valore"] = casa
    _dich(d)["tempistica_pagamento"] = "2"
    return d


def valore(d, bid, v):
    next(b for b in d["beni"] if b["id"] == bid)["valore"] = v


def rid(d, did, agevolazioni=None, riduzioni=None):
    voce = {k: v for k, v in (("agevolazioni", agevolazioni), ("riduzioni", riduzioni)) if v}
    _tel(d).setdefault("devoluzioni", {})[did] = voce


def vps(d, bid, v):
    _tel(d)["beni"].setdefault(bid, {})["valore_prec_succ"] = v


def doc(d, did, allegato, tipo):
    d["documenti_ref"].append({"id": did, "_origine": {}, "allegato_id": allegato, "tipo_eg": tipo, "finalita": "sintetico"})


def con_eg(d, altro=False):
    doc(d, "dr_rid0001", "al_rid", "RiduzioniImposteSuccessione")
    doc(d, "dr_ident01", "al_ident", "DocumentiIdentita")
    if altro:
        doc(d, "dr_altro01", "al_altro", "Altro")


def _es(d, ctx=CTX):
    return esporta_xml(d, ctx)


def _x(es, xp):
    return etree.fromstring(es.xml).xpath(xp, namespaces=NS)


def _codici(es):
    return {e.codice for e in es.errori}


def _ok(es):
    assert (es.errori, es.non_supportato, es.quadri_mancanti) == ([], [], []) and es.completo, \
        (es.errori, es.non_supportato, es.quadri_mancanti)


# ----------------------------------------------------------------------------------- calcolo indipendente a mano
def isl_figlio(qe, qp):
    """Guida pp. 3-5 per un figlio (grado 02): AN = QE - QP; QN = AN - 1.000.000 (franchigia); nessun denaro (QDN = 0), PR =
    10% di QN; QTI = QN + PR; ISL = QTI x 4%."""
    qn = Fr(qe) - qp - 1_000_000
    return (qn + qn / 10) * Fr(4, 100)


def euro_atteso(totale: Fr) -> int:
    """Totale arrotondato al centesimo e poi all'euro, HALF_UP (politica 'esatta' del calcolo)."""
    def hu(f, c):
        k = Fr(10) ** c
        return ((f * k + Fr(1, 2)) // 1) / k
    return int(hu(hu(totale, 2), 0))


def valori(r, rigo):
    b = next(b for b in r.beneficiari if b.rigo_ea == rigo)
    return {p.sigla: Fr(p.valore) for p in b.passaggi}


def verifica_calcolo(es, atteso_a, atteso_l, tot):
    """RID e ISN dei due figli (a mano) e importo EF18bis; entrambi i candidati di arrotondamento danno lo stesso intero."""
    r = calcola_da_xml(es.xml)
    assert r.stato == "completato", r.motivi
    for rigo, (isl, rid_) in (("1/1", atteso_a), ("1/2", atteso_l)):
        v = valori(r, rigo)
        assert (v["ISL"], v["RID"], v["ISN"]) == (isl, rid_, isl - rid_)
    assert r.candidati["esatta"]["imposta_ef18bis"] == r.candidati["componente_ispezionato"]["imposta_ef18bis"] \
        == r.imposta_ef18bis == euro_atteso(tot)
    assert Fr(r.candidati["esatta"]["totale_esatto"]) == tot
    return r


def verifica_controllo(es, tmp_path, atteso_intero):
    """Controllo ufficiale locale: nessuno scarto con l'importo dichiarato; scarto (3454) con +1 e -1."""
    stato, dgn, wri, dcm = _esegui(es.xml, tmp_path / "ok")
    assert stato == "positivo", (dgn["diagnostici"], wri[-1500:])
    assert sorted((q["codice"], q["gravita"]) for q in dgn["diagnostici"]) == [("3345", 4)] and dcm
    dich = f"<suc:Imposta>{atteso_intero}<"
    assert es.xml.decode().count(dich) == 1
    for delta in (1, -1):
        xml = es.xml.decode().replace(dich, f"<suc:Imposta>{atteso_intero + delta}<").encode()
        stato, dgn, wri, _ = _esegui(xml, tmp_path / f"d{delta}")
        assert stato == "negativo" and "3454" in {q["codice"] for q in dgn["diagnostici"]}, (delta, dgn["diagnostici"])


# ================================================================================================ L (dichiarante)
def caso_l():
    d = base()
    rid(d, "d_casaanna", agevolazioni="L")
    _dich(d)["riduzioni_art25"] = copy.deepcopy(DICH_L)
    return d


def test_l_dichiarante_export_e_calcolo_a_mano():
    es = _es(caso_l())
    _ok(es)
    # rigo EC: Agevolazioni = L sulla sola riga di Anna; EH, Sezione IV, AgevolazTipoL (XSD) con firma
    assert _x(es, D + "/suc:QuadroEC//suc:Devoluzione/suc:Agevolazioni/text()") == ["L"]
    iv = D + "/suc:QuadroEH/suc:PrimoModulo/suc:SezioneIV_AltreAgevRiduz"
    assert _x(es, iv + "/suc:EsenzioneImpostaSuccessione/suc:AgevolazTipoL/*/text()") == ["1", "PROT-001", "01092025"]
    assert _x(es, iv + "/suc:EsenzioneImpostaSuccessione/suc:FirmaDichiarante/text()") == ["1"]
    assert _x(es, iv + "/suc:Agevolazioni") == [] and _x(es, iv + "/suc:Riduzioni") == []
    assert _x(es, D + "/suc:QuadroEG/suc:RiduzioniImposteSuccessione") == []
    # a mano: QE = 1.200.000 (casa) + 7.500 (terreno) + 10.000 (conto) = 1.217.500 per entrambi; QP 17.000 e 15.000
    isl_a, isl_l = isl_figlio(1_217_500, 17_000), isl_figlio(1_217_500, 15_000)
    assert (isl_a, isl_l) == (8822, 8910)                          # 4% di 220.550 e di 222.750
    rid_a = Fr(1_200_000) * isl_a / 1_217_500 * Fr(1, 2)           # guida p. 6: r = valore quota agevolata x ISL / QE; x 0,5
    r = verifica_calcolo(es, (isl_a, rid_a), (isl_l, 0), isl_a - rid_a + isl_l)
    assert r.imposta_ef18bis == 13384
    assert _x(es, D + "/suc:QuadroEF/suc:SezioneVBis_ImpostaSuccessione/suc:ImpostaCalcolata/suc:Imposta/text()") == ["13384"]


@SALTO
def test_reale_l_dichiarante(tmp_path):
    verifica_controllo(_es(caso_l()), tmp_path, 13384)


def test_esempio_della_guida_con_agevolazione_l():
    """Guida pp. 5-6: due fratelli (QE 200.000, ISL 6.567); il primo immobile e' vincolato dopo l'apertura (L): r = 125.000 x
    6.567 / 200.000 = 4.104,375 e Rid.agevL = r x 0,5 = 2.052,1875 (la guida espone 4.104,38 e 2.052,19)."""
    d = _fratelli()
    for dv in d["devoluzioni"]:      # id univoci: la seconda casa non condivide gli id della prima
        if dv["bene_id"] == "b_casa0002":
            dv["id"] = dv["id"].replace("casa", "cas2")
    for pid in ("anna", "luca"):
        rid(d, f"d_casa{pid}", agevolazioni="L")
    r = calcola(d)
    assert r.stato == "completato", r.motivi
    for rigo in ("1/1", "1/2"):
        v = valori(r, rigo)
        assert v["ISL"] == 6567 and v["QE"] == 200_000
        assert v["Rid.agevL"] == Fr(125_000 * 6567, 200_000) / 2 == Fr("2052.1875")
        assert v["ISN"] == 6567 - Fr("2052.1875")
    # totale a mano: 2 x 4.514,8125 = 9.029,625 -> 9.029,63 -> 9.030 (esatta); componente: 4.514,81 + 4.514,81 (HALF_UP per addendo)
    assert r.candidati["esatta"]["totale_esatto"] == "9029.625" and r.candidati["esatta"]["totale_centesimi"] == "9029.63"
    assert r.candidati["componente_ispezionato"]["totale_centesimi"] == "9029.62"
    assert r.imposta_ef18bis == 9030
    assert any("centesimo" in n for n in r.note)       # i candidati differiscono al centesimo: non validato


# ================================================================================================ art. 25 comma 1
def caso_art25(codice="2", prec="600000"):
    """Codice ``codice`` su tutti i righi della casa (2.400.000), con ``prec`` come valore precedenti successioni."""
    d = base()
    rid(d, "d_casaanna", riduzioni=codice)
    rid(d, "d_casaluca", riduzioni=codice)
    vps(d, "b_casa0001", prec)
    con_eg(d)
    _dich(d)["riduzioni_art25"] = copy.deepcopy(DICH_ART25)
    return d


@pytest.mark.parametrize("codice,coeff", [("1", Fr(5, 10)), ("2", Fr(4, 10)), ("3", Fr(3, 10)), ("4", Fr(2, 10)), ("5", Fr(1, 10))])
def test_art25_codici_1_5_a_mano(codice, coeff):
    es = _es(caso_art25(codice))
    _ok(es)
    # Riduzioni sulle due righe della devoluzione, ValorePrecSucc sul rigo EC (dopo Valore)
    assert _x(es, D + "/suc:QuadroEC//suc:Devoluzione/suc:Riduzioni/text()") == [codice, codice]
    assert _x(es, D + "/suc:QuadroEC/suc:Modulo/suc:Fabbricati[1]/suc:ValorePrecSucc/text()") == ["600000"]
    iv = D + "/suc:QuadroEH/suc:PrimoModulo/suc:SezioneIV_AltreAgevRiduz/suc:Riduzioni"
    assert _x(es, iv + "/suc:UfficioTerritoriale/text()") == ["795"]
    assert _x(es, iv + "/suc:EstremiDichiarazionePrecedente/*/text()") == ["2024", "88888", "123"]
    assert len(_x(es, D + "/suc:QuadroEG/suc:RiduzioniImposteSuccessione/suc:RiduzioniImposteSuccessioneAll")) == 1
    isl_a, isl_l = isl_figlio(1_217_500, 17_000), isl_figlio(1_217_500, 15_000)
    # guida p. 7: r25 = (VPS x valore quota con art. 25 / valore cespite) x ISL / QE = (600.000 x 1.200.000 / 2.400.000) x ISL / QE;
    # Rid.art25 = r25 x coefficiente del codice
    rid_a = Fr(600_000) * 1_200_000 / 2_400_000 * isl_a / 1_217_500 * coeff
    rid_l = Fr(600_000) * 1_200_000 / 2_400_000 * isl_l / 1_217_500 * coeff
    r = verifica_calcolo(es, (isl_a, rid_a), (isl_l, rid_l), isl_a + isl_l - rid_a - rid_l)
    assert valori(r, "1/1")["Rid.art25"] == rid_a
    if codice == "2":
        assert r.imposta_ef18bis == 15984


@SALTO
def test_reale_art25_codice_2(tmp_path):
    verifica_controllo(_es(caso_art25("2")), tmp_path, 15984)


def test_art25_donazione_precedente_in_eh():
    d = caso_art25()
    _dich(d)["riduzioni_art25"] = {"dichiara_requisiti": True,
                                   "donazione_precedente": {"ufficio": "795", "serie": "1T", "numero": "456", "sottonumero": "2"}}
    es = _es(d)
    _ok(es)
    iv = D + "/suc:QuadroEH/suc:PrimoModulo/suc:SezioneIV_AltreAgevRiduz/suc:Riduzioni"
    assert _x(es, iv + "/suc:EstremiDonazionePrecedente/*/text()") == ["795", "1T", "456", "2"]
    assert _x(es, iv + "/suc:UfficioTerritoriale") == []        # solo con gli estremi della dichiarazione precedente


# art. 25 sugli altri quadri (la formula non dipende dal quadro): caso, righi di devoluzione, bene, valore prec. succ., atteso
def _caso_eb():
    d = base()
    for p in ("anna", "luca"):
        rid(d, f"d_terr{p}", riduzioni="1")
    vps(d, "b_terr0001", "10000")
    return d, 15_000, 7_500, 1_217_500


def _caso_er():
    d = base()
    for p in ("anna", "luca"):
        rid(d, f"d_cont{p}", riduzioni="3")
    vps(d, "b_conto001", "8000")
    return d, 20_000, 10_000, 1_217_500


def _caso_en():
    d = caso_azienda()
    valore(d, "b_azien001", "1000000")
    _dich(d)["tempistica_pagamento"] = "2"
    valore(d, "b_casa0001", "2400000")
    for p in ("anna", "luca"):
        rid(d, f"d_azien{p}", riduzioni="4")
    vps(d, "b_azien001", "300000")
    return d, 1_000_000, 500_000, 1_717_500


def _caso_eo():
    d = caso_titoli()
    valore(d, "b_casa0001", "2400000")
    _dich(d)["tempistica_pagamento"] = "2"
    for p in ("anna", "luca"):
        rid(d, f"d_azion{p}", riduzioni="5")
    vps(d, "b_azioni01", "4000")
    return d, 10_000, 5_000, 1_225_500


def _caso_ep():
    d = caso_mezzi()
    valore(d, "b_casa0001", "2400000")
    _dich(d)["tempistica_pagamento"] = "2"
    for p in ("anna", "luca"):
        rid(d, f"d_aereo{p}", riduzioni="2")
    vps(d, "b_aereo001", "20000")
    return d, 30_000, 15_000, 1_238_500


def _caso_eq():
    d = caso_mezzi()
    valore(d, "b_casa0001", "2400000")
    _dich(d)["tempistica_pagamento"] = "2"
    for p in ("anna", "luca"):
        rid(d, f"d_barca{p}", riduzioni="1")
    vps(d, "b_barca001", "9000")
    return d, 12_000, 6_000, 1_238_500


def _caso_el_em(bene, did, v, codice, prec):
    d = caso_tavolare()
    valore(d, "b_fabbtav1", "2400000")
    _dich(d)["tempistica_pagamento"] = "2"
    for p in ("anna", "luca"):
        rid(d, f"{did}{p}", riduzioni=codice)
    vps(d, bene, prec)
    return d


QUADRI_ART25 = {
    "EB": (_caso_eb, "b_terr0001", Fr(1, 2), "10000"),
    "ER": (_caso_er, "b_conto001", Fr(3, 10), "8000"),
    "EN": (_caso_en, "b_azien001", Fr(2, 10), "300000"),
    "EO": (_caso_eo, "b_azioni01", Fr(1, 10), "4000"),
    "EP": (_caso_ep, "b_aereo001", Fr(4, 10), "20000"),
    "EQ": (_caso_eq, "b_barca001", Fr(5, 10), "9000"),
}


@pytest.mark.parametrize("quadro", sorted(QUADRI_ART25))
def test_art25_negli_altri_quadri_a_mano(quadro):
    caso, bene, coeff, prec = QUADRI_ART25[quadro]
    d, valore_cespite, qv, qe = caso()
    con_eg_e_eh(d)
    es = _es(d)
    _ok(es)
    # QE di ciascun figlio (a mano): casa 1.200.000 + terreno 7.500 + conto 10.000 + quote degli altri beni aggiunti dal caso
    isl_a, isl_l = isl_figlio(qe, 17_000), isl_figlio(qe, 15_000)
    # r25 = (VPS x valore quota / valore cespite) x ISL / QE; Rid = r25 x coefficiente
    rid_a = Fr(int(prec)) * qv / valore_cespite * isl_a / qe * coeff
    rid_l = Fr(int(prec)) * qv / valore_cespite * isl_l / qe * coeff
    verifica_calcolo(es, (isl_a, rid_a), (isl_l, rid_l), isl_a + isl_l - rid_a - rid_l)


@SALTO
@pytest.mark.parametrize("quadro", sorted(QUADRI_ART25))
def test_reale_art25_negli_altri_quadri(quadro, tmp_path):
    caso, bene, coeff, prec = QUADRI_ART25[quadro]
    d, valore_cespite, qv, qe = caso()
    con_eg_e_eh(d)
    es = _es(d)
    _ok(es)
    verifica_controllo(es, tmp_path, calcola_da_xml(es.xml).imposta_ef18bis)


def con_eg_e_eh(d):
    con_eg(d)
    _dich(d)["riduzioni_art25"] = copy.deepcopy(DICH_ART25)


@pytest.mark.parametrize("quadro", ["EL", "EM"])
def test_art25_tavolari(quadro):
    if quadro == "EL":
        d = _caso_el_em("b_terrtav1", "d_terrt", 8000, "1", "4000")
        valore_cespite, qv, prec, coeff, ancora = 8_000, 4_000, 4_000, Fr(5, 10), 0
    else:
        d = _caso_el_em("b_fabbtav1", "d_fabbt", 2_400_000, "3", "100000")
        valore_cespite, qv, prec, coeff, ancora = 2_400_000, 1_200_000, 100_000, Fr(3, 10), 0
    con_eg_e_eh(d)
    es = _es(d)
    _ok(es)
    # quote: terreno 4.000 + fabbricato 1.200.000 + conto 10.000 = 1.214.000 per entrambi (caso tavolare: nessun immobile romano)
    qe = 4_000 + 1_200_000 + 10_000
    isl_a, isl_l = isl_figlio(qe, 17_000), isl_figlio(qe, 15_000)
    rid_a = Fr(prec) * qv / valore_cespite * isl_a / qe * coeff
    rid_l = Fr(prec) * qv / valore_cespite * isl_l / qe * coeff
    verifica_calcolo(es, (isl_a, rid_a), (isl_l, rid_l), isl_a + isl_l - rid_a - rid_l)


@SALTO
@pytest.mark.parametrize("quadro", ["EL", "EM"])
def test_reale_art25_tavolari(quadro, tmp_path):
    d = _caso_el_em("b_terrtav1", "d_terrt", 8000, "1", "4000") if quadro == "EL" else \
        _caso_el_em("b_fabbtav1", "d_fabbt", 2_400_000, "3", "100000")
    con_eg_e_eh(d)
    es = _es(d)
    _ok(es)
    verifica_controllo(es, tmp_path, calcola_da_xml(es.xml).imposta_ef18bis)


# ================================================================================================ Q (aziende, EN)
def caso_q():
    d = caso_azienda()
    valore(d, "b_azien001", "1000000")
    valore(d, "b_casa0001", "2400000")
    _dich(d)["tempistica_pagamento"] = "2"
    rid(d, "d_azienanna", agevolazioni="Q")
    rid(d, "d_azienluca", agevolazioni="Q")
    con_eg(d)
    _dich(d)["riduzioni_art25"] = copy.deepcopy(DICH_Q)
    return d


def test_q_azienda_a_mano():
    es = _es(caso_q())
    _ok(es)
    assert _x(es, D + "/suc:QuadroEN//suc:Devoluzione/suc:Agevolazioni/text()") == ["Q", "Q"]
    iv = D + "/suc:QuadroEH/suc:PrimoModulo/suc:SezioneIV_AltreAgevRiduz"
    assert _x(es, iv + "/suc:Agevolazioni/*/text()") == ["1", "1"]      # FlagQ e firma del dichiarante
    assert len(_x(es, D + "/suc:QuadroEG/suc:RiduzioniImposteSuccessione/suc:RiduzioniImposteSuccessioneAll")) == 1
    # QE = 1.200.000 + 7.500 + 10.000 + 500.000 (azienda 1/2) = 1.717.500; ISL 30.822 e 30.910
    isl_a, isl_l = isl_figlio(1_717_500, 17_000), isl_figlio(1_717_500, 15_000)
    assert (isl_a, isl_l) == (30822, 30910)
    rid_a = Fr(500_000) * isl_a / 1_717_500 * Fr(4, 10)             # guida p. 6: Rid.agevQ = r x 0,4
    rid_l = Fr(500_000) * isl_l / 1_717_500 * Fr(4, 10)
    r = verifica_calcolo(es, (isl_a, rid_a), (isl_l, rid_l), isl_a + isl_l - rid_a - rid_l)
    assert r.imposta_ef18bis == 54543


@SALTO
def test_reale_q_azienda(tmp_path):
    verifica_controllo(_es(caso_q()), tmp_path, 54543)


# ================================================================================================ R ed F
def caso_r(terreno="400000"):
    """R sui due righi del terreno (EB). Attestazione allegata al quadro EG (rigo EG8)."""
    d = base()
    valore(d, "b_terr0001", terreno)
    rid(d, "d_terranna", agevolazioni="R")
    rid(d, "d_terrluca", agevolazioni="R")
    doc(d, "dr_altro01", "al_altro", "Altro")
    return d


def test_r_sopra_soglia_a_mano():
    es = _es(caso_r())
    _ok(es)
    assert _x(es, D + "/suc:QuadroEB//suc:Devoluzione/suc:Agevolazioni/text()") == ["R", "R"]
    assert _x(es, D + "/suc:QuadroEH/suc:PrimoModulo/suc:SezioneIV_AltreAgevRiduz") == []     # nessuna sezione per R
    # quota terreno 200.000 > 103.291: Rid.agevR = (103.291 x ISL / QE) x 0,4 (guida p. 6)
    qe = 1_200_000 + 200_000 + 10_000
    isl_a, isl_l = isl_figlio(qe, 17_000), isl_figlio(qe, 15_000)
    assert (isl_a, isl_l) == (17292, 17380)
    rid_a = Fr(103_291) * isl_a / qe * Fr(4, 10)
    rid_l = Fr(103_291) * isl_l / qe * Fr(4, 10)
    r = verifica_calcolo(es, (isl_a, rid_a), (isl_l, rid_l), isl_a + isl_l - rid_a - rid_l)
    assert r.imposta_ef18bis == 33656


def test_r_sotto_soglia_a_mano():
    d = caso_r("150000")        # quota 75.000 <= 103.291: Rid.agevR = r x 0,4
    es = _es(d)
    _ok(es)
    qe = 1_200_000 + 75_000 + 10_000
    isl_a, isl_l = isl_figlio(qe, 17_000), isl_figlio(qe, 15_000)
    rid_a = Fr(75_000) * isl_a / qe * Fr(4, 10)
    rid_l = Fr(75_000) * isl_l / qe * Fr(4, 10)
    verifica_calcolo(es, (isl_a, rid_a), (isl_l, rid_l), isl_a + isl_l - rid_a - rid_l)


@SALTO
@pytest.mark.parametrize("terreno", ["400000", "150000"])
def test_reale_r(terreno, tmp_path):
    es = _es(caso_r(terreno))
    verifica_controllo(es, tmp_path, calcola_da_xml(es.xml).imposta_ef18bis)


def caso_f(sopra=True):
    """F sui due righi di un fabbricato (EC): sopra soglia la casa da 2.400.000; sotto soglia una seconda casa da 150.000."""
    d = base()
    if sopra:
        rid(d, "d_casaanna", agevolazioni="F")
        rid(d, "d_casaluca", agevolazioni="F")
    else:
        aggiungi_fabbricato(d, "b_casa0002", "A/3", "150000", "8", anna="F", luca="F")
    return d


def test_f_sopra_soglia_a_mano():
    es = _es(caso_f())
    _ok(es)
    assert _x(es, D + "/suc:QuadroEC//suc:Devoluzione/suc:Agevolazioni/text()") == ["F", "F"]
    isl_a, isl_l = isl_figlio(1_217_500, 17_000), isl_figlio(1_217_500, 15_000)
    rid_a = Fr(103_291) * isl_a / 1_217_500 * Fr(4, 10)
    rid_l = Fr(103_291) * isl_l / 1_217_500 * Fr(4, 10)
    verifica_calcolo(es, (isl_a, rid_a), (isl_l, rid_l), isl_a + isl_l - rid_a - rid_l)


def test_f_sotto_soglia_a_mano():
    es = _es(caso_f(False))
    _ok(es)
    qe = 1_200_000 + 75_000 + 7_500 + 10_000
    isl_a, isl_l = isl_figlio(qe, 17_000), isl_figlio(qe, 15_000)
    assert (isl_a, isl_l) == (12122, 12210)
    rid_a = Fr(75_000) * isl_a / qe * Fr(4, 10)
    rid_l = Fr(75_000) * isl_l / qe * Fr(4, 10)
    verifica_calcolo(es, (isl_a, rid_a), (isl_l, rid_l), isl_a + isl_l - rid_a - rid_l)


@SALTO
@pytest.mark.parametrize("sopra", [True, False])
def test_reale_f(sopra, tmp_path):
    es = _es(caso_f(sopra))
    _ok(es)
    verifica_controllo(es, tmp_path, calcola_da_xml(es.xml).imposta_ef18bis)


# ================================================================================================ L: altro beneficiario
def test_l_di_beneficiario_diverso_dal_dichiarante_usa_eg11():
    d = base()
    rid(d, "d_casaluca", agevolazioni="L")      # Luca non e' il dichiarante: nessuna Sezione IV, allegato EG11
    con_eg(d)
    es = _es(d)
    _ok(es)
    assert _x(es, D + "/suc:QuadroEH/suc:PrimoModulo/suc:SezioneIV_AltreAgevRiduz") == []
    assert len(_x(es, D + "/suc:QuadroEG/suc:RiduzioniImposteSuccessione/suc:RiduzioniImposteSuccessioneAll")) == 1
    isl_a, isl_l = isl_figlio(1_217_500, 17_000), isl_figlio(1_217_500, 15_000)
    rid_l = Fr(1_200_000) * isl_l / 1_217_500 * Fr(1, 2)
    verifica_calcolo(es, (isl_a, 0), (isl_l, rid_l), isl_a + isl_l - rid_l)


@SALTO
def test_reale_l_altro_beneficiario(tmp_path):
    d = base()
    rid(d, "d_casaluca", agevolazioni="L")
    con_eg(d)
    es = _es(d)
    verifica_controllo(es, tmp_path, calcola_da_xml(es.xml).imposta_ef18bis)


# ================================================================================================ negativi: export
def _errore_con(es, codice, percorso=None):
    return [e for e in es.errori if e.codice == codice and (percorso is None or e.percorso == percorso)]


def test_neg_valore_prec_succ_maggiore_del_valore():
    d = caso_art25(prec="3000000")
    es = _es(d)
    e = _errore_con(es, "REGOLA_VALORE_PREC_SUCC", "beni[b_casa0001].valore_prec_succ")
    assert e and "non puo' essere superiore" in e[0].messaggio and "ValorePrecSucc" in e[0].fonte and es.xml is None


def test_neg_riduzione_senza_valore_prec_succ():
    d = caso_art25()
    del _tel(d)["beni"]["b_casa0001"]["valore_prec_succ"]
    es = _es(d)
    assert _errore_con(es, "REGOLA_RIDUZIONI_ART25", "beni[b_casa0001]")


def test_neg_valore_prec_succ_senza_riduzione():
    d = caso_art25()
    _tel(d)["devoluzioni"] = {}
    es = _es(d)
    assert _errore_con(es, "REGOLA_RIDUZIONI_ART25", "beni[b_casa0001]")


def test_neg_riduzione_solo_su_un_rigo_della_devoluzione():
    d = caso_art25()
    _tel(d)["devoluzioni"].pop("d_casaluca")
    es = _es(d)
    e = _errore_con(es, "REGOLA_RIDUZIONI_ART25", "beni[b_casa0001]")
    assert e and "stesso valore in tutti i righi" in e[0].messaggio


def test_neg_codice_riduzione_non_valido():
    d = caso_art25("6")
    es = _es(d)
    assert _errore_con(es, "VALORE_NON_VALIDO", "devoluzioni[d_casaanna].riduzioni") and es.xml is None


def test_neg_f_nel_quadro_eb_e_l_nel_quadro_en():
    d = base()
    rid(d, "d_terranna", agevolazioni="F")
    es = _es(d)
    e = _errore_con(es, "REGOLA_AGEVOLAZIONE_QUADRO", "devoluzioni[d_terranna].agevolazioni")
    assert e and "EC, EM" in e[0].messaggio and "annotazione" in e[0].fonte
    d = caso_azienda()
    rid(d, "d_azienanna", agevolazioni="L")
    assert _errore_con(_es(d), "REGOLA_AGEVOLAZIONE_QUADRO", "devoluzioni[d_azienanna].agevolazioni")


def test_neg_grado_di_parentela_non_ammesso():
    d = base()
    _tel(d)["persone"]["p_luca0001"]["grado_parentela"] = "21"      # cugino: R ammesso solo per i gradi dell'annotazione XSD
    d["persone"][2]["relazione_con_defunto"] = "21"
    valore(d, "b_terr0001", "400000")
    rid(d, "d_terrluca", agevolazioni="R")
    es = _es(d)
    e = _errore_con(es, "REGOLA_AGEVOLAZIONE_GRADO", "devoluzioni[d_terrluca].agevolazioni")
    assert e and "21" in e[0].messaggio


def test_neg_l_esclude_altre_agevolazioni_sullo_stesso_bene():
    d = caso_l()
    aggiungi_fabbricato(d, "b_casa0002", "A/3", "150000", "8", anna="L", luca="P")
    es = _es(d)
    assert _errore_con(es, "REGOLA_AGEVOLAZIONE_ESCLUSIVA", "beni[b_casa0002]")


def test_neg_dati_eh_mancanti_o_incompleti():
    d = caso_l()
    del _dich(d)["riduzioni_art25"]
    es = _es(d)
    assert _errore_con(es, "DATO_MANCANTE", "opzioni.telematico.dichiarazione.riduzioni_art25") and es.xml is None
    d = caso_l()
    _dich(d)["riduzioni_art25"]["dichiara_requisiti"] = False
    assert _errore_con(_es(d), "DATO_MANCANTE", "opzioni.telematico.dichiarazione.riduzioni_art25.dichiara_requisiti")
    d = caso_l()
    _dich(d)["riduzioni_art25"]["l"]["num_protocollo"] = "ABC123"        # da 7 a 16 caratteri (controllo ufficiale, 3128)
    e = _errore_con(_es(d), "VALORE_NON_VALIDO", "opzioni.telematico.dichiarazione.riduzioni_art25.l.num_protocollo")
    assert e and "3128" in e[0].fonte
    d = caso_art25()
    _dich(d)["riduzioni_art25"] = {"dichiara_requisiti": True}          # mancano gli estremi della precedente
    assert _errore_con(_es(d), "DATO_MANCANTE", "opzioni.telematico.dichiarazione.riduzioni_art25")


def test_neg_sezione_eh_senza_richiesta_del_dichiarante():
    d = base()
    _dich(d)["riduzioni_art25"] = copy.deepcopy(DICH_L)
    assert _errore_con(_es(d), "DATI_INCOERENTI", "opzioni.telematico.dichiarazione.riduzioni_art25")


def test_neg_allegati_obbligatori_mancanti():
    d = caso_art25()
    d["documenti_ref"] = [x for x in d["documenti_ref"] if x["id"] not in ("dr_rid0001", "dr_ident01")]
    es = _es(d)
    m = {e.percorso for e in es.quadri_mancanti}
    assert {"quadro[EG].RiduzioniImposteSuccessione", "quadro[EG].DocumentiIdentita"} <= m and not es.completo
    d = caso_r()
    d["documenti_ref"] = [x for x in d["documenti_ref"] if x["id"] != "dr_altro01"]
    assert "quadro[EG].Altro" in {e.percorso for e in _es(d).quadri_mancanti}


@pytest.mark.parametrize("mod,testo", [
    (lambda d: rid(d, "d_casaanna", agevolazioni="F", riduzioni="2"), "stessa riga"),
    (lambda d: rid(d, "d_contanna", agevolazioni="L"), "non supportato"),                  # L in ER
    (lambda d: (rid(d, "d_casaanna", agevolazioni="Q")), "Q nel quadro EC"),                # Q su fabbricato non aziendale
    (lambda d: (rid(d, "d_terranna", agevolazioni="R"), rid(d, "d_terrluca", agevolazioni="R"),
                rid(d, "d_casaanna", agevolazioni="R")), "2 righe con codice R"),
    (lambda d: (rid(d, "d_casaanna", agevolazioni="G")), "non supportata"),
])
def test_neg_casi_non_supportati_bloccano_l_esportazione(mod, testo):
    d = base()
    d["beni"][1]["valore"] = "400000"
    mod(d)
    # terreno e casa: il secondo R richiede un secondo rigo per Anna
    es = _es(d)
    assert es.xml is None and es.non_supportato, (es.errori, es.non_supportato)
    assert any(testo in n or "agevolazione" in n or "riduzione" in n for n in es.non_supportato), es.non_supportato


def test_neg_riduzione_su_cespite_dn_non_supportata():
    d = base()
    d["beni"].append({"id": "b_denaro01", "_origine": {}, "tipo": "disponibilita_finanziaria", "descrizione": "Denaro",
                      "valore": "5000", "diritto": "1", "quota_defunto": "1/1"})
    _tel(d)["beni"]["b_denaro01"] = {"tipo_cespite": "DN", "valore_prec_succ": "1000"}
    for p in ("anna", "luca"):
        d["devoluzioni"].append({"id": f"d_denaro{p}", "_origine": {}, "bene_id": "b_denaro01",
                                 "persona_id": f"p_{p}0001", "quota": {"num": 1, "den": 2}, "diritto": "1"})
        rid(d, f"d_denaro{p}", riduzioni="2")
    es = _es(d)
    assert es.xml is None and any("DN" in n for n in es.non_supportato)


# ================================================================================================ scale del componente
def _dec(x) -> Dc:
    return Dc(x)            # Decimal(float) = new BigDecimal(double): espansione decimale esatta del double


def _scala(x: Dc, cifre: int) -> Dc:
    return x.quantize(Dc(1).scaleb(-cifre), rounding=ROUND_HALF_UP)


ISL_T, QE_T = 8822, 1_217_500        # rapporto ISL / QE = 0,0072462...: le scale del componente incidono sul risultato


@pytest.fixture
def precisione_alta():
    with localcontext() as ctx:
        ctx.prec = 200            # BigDecimal.multiply e' esatto: nessun arrotondamento a 28 cifre
        yield


def test_scale_del_componente_art25_e_l_q_r_f_con_decimal_indipendente(precisione_alta):
    """Controllo delle scale lette con ispezione statica di AgevolazioniRiduzioni (docs/regole/riduzioni_art25.md §3), con
    aritmetica ``Decimal`` (altro motore rispetto alle ``Fraction`` del calcolo): rapporto a 10 decimali (a 6 per l'art. 25),
    (VPS x quota / valore) a 6 decimali, coefficiente ``double`` (0,4 = 0,40000000000000002220...), art. 25 a 3 decimali,
    somma di R oltre soglia a 2 decimali."""
    r10 = _scala(Dc(ISL_T) / Dc(QE_T), 10)
    r6 = _scala(Dc(ISL_T) / Dc(QE_T), 6)
    righe = [{"qv": Fr(1_200_000), "agev": "L", "rid": None, "valore": Fr(0), "vps": Fr(0)}]
    assert riduzioni_componente(righe, Fr(ISL_T), Fr(QE_T))["L"] == Fr(Dc(1_200_000) * r10 * _dec(0.5))
    righe = [{"qv": Fr(500_000), "agev": "Q", "rid": None, "valore": Fr(0), "vps": Fr(0)}]
    assert riduzioni_componente(righe, Fr(ISL_T), Fr(QE_T))["Q"] == Fr(Dc(500_000) * r10 * _dec(0.4))
    righe = [{"qv": Fr(75_000), "agev": "F", "rid": None, "valore": Fr(0), "vps": Fr(0)}]       # sotto soglia
    assert riduzioni_componente(righe, Fr(ISL_T), Fr(QE_T))["F"] == Fr(Dc(75_000) * r10 * _dec(0.4))
    righe = [{"qv": Fr(200_000), "agev": "F", "rid": None, "valore": Fr(0), "vps": Fr(0)}]      # sopra soglia, nessun arrotondamento
    assert riduzioni_componente(righe, Fr(ISL_T), Fr(QE_T))["F"] == Fr(Dc(103_291) * r10 * _dec(0.4))
    righe = [{"qv": Fr(200_000), "agev": "R", "rid": None, "valore": Fr(0), "vps": Fr(0)}]      # sopra soglia: somma a 2 decimali
    atteso_r = _scala(Dc(103_291) * r10 * _dec(0.4), 2)
    assert atteso_r != Dc(103_291) * r10 * _dec(0.4)
    assert riduzioni_componente(righe, Fr(ISL_T), Fr(QE_T))["R"] == Fr(atteso_r)
    for codice, c in (("1", 0.5), ("2", 0.4), ("3", 0.3), ("4", 0.2), ("5", 0.1)):
        righe = [{"qv": Fr(1_200_000), "agev": None, "rid": codice, "valore": Fr(2_400_000), "vps": Fr(600_000)}]
        base_ = _scala(Dc(600_000) * Dc(1_200_000) / Dc(2_400_000), 6) * r6
        atteso = _scala(_dec(c) * base_, 3)
        assert riduzioni_componente(righe, Fr(ISL_T), Fr(QE_T))["art25"] == Fr(atteso), codice
    # valori con cifre significative oltre il secondo decimale: la scala a 3 decimali si distingue da quella a 2
    distinti = 0
    for codice, c in (("1", 0.5), ("2", 0.4), ("3", 0.3), ("4", 0.2), ("5", 0.1)):
        righe = [{"qv": Fr(1_200_003), "agev": None, "rid": codice, "valore": Fr(2_400_001), "vps": Fr(600_007)}]
        base_ = _scala(Dc(600_007) * Dc(1_200_003) / Dc(2_400_001), 6) * r6
        atteso = _scala(_dec(c) * base_, 3)
        distinti += atteso != _scala(_dec(c) * base_, 2)
        assert riduzioni_componente(righe, Fr(ISL_T), Fr(QE_T))["art25"] == Fr(atteso), codice
    assert distinti >= 1


def test_esatta_e_componente_coincidono_entro_un_centesimo_sui_casi_a_mano():
    righe = [{"qv": Fr(1_200_000), "agev": None, "rid": "2", "valore": Fr(2_400_000), "vps": Fr(600_000)},
             {"qv": Fr(200_000), "agev": "R", "rid": None, "valore": Fr(0), "vps": Fr(0)}]
    e = riduzioni_esatte(righe, Fr(ISL_T), Fr(QE_T))
    c = riduzioni_componente(righe, Fr(ISL_T), Fr(QE_T))
    assert e["art25"] == Fr(600_000) * Fr(1_200_000) / 2_400_000 * ISL_T / QE_T * Fr(4, 10)
    assert e["R"] == Fr(103_291) * ISL_T / QE_T * Fr(4, 10)
    for k in e:
        assert abs(e[k] - c[k]) < Fr(1, 100), k


def test_valore_prec_succ_uguale_al_valore_e_ammesso_zero_no():
    d = caso_art25(prec="2400000")           # XSD: «non puo' essere superiore al campo valore»
    es = _es(d)
    _ok(es)
    r = calcola_da_xml(es.xml)
    assert r.stato == "completato"
    d = caso_art25(prec="0")
    assert _errore_con(_es(d), "VALORE_NON_VALIDO", "beni[b_casa0001].valore_prec_succ")


def test_neg_f_grado_fratello_non_ammesso():
    d = base()
    _tel(d)["persone"]["p_luca0001"]["grado_parentela"] = "10"      # fratello: ammesso per R, non per F (annotazione XSD)
    d["persone"][2]["relazione_con_defunto"] = "10"
    rid(d, "d_casaluca", agevolazioni="F")
    assert _errore_con(_es(d), "REGOLA_AGEVOLAZIONE_GRADO", "devoluzioni[d_casaluca].agevolazioni")


# ================================================================================================ negativi: calcolo sul file
def _muta(xml: bytes, fn) -> bytes:
    doc_ = etree.fromstring(xml)
    fn(doc_)
    return etree.tostring(doc_)


def _rm(doc_, xp):
    for e in doc_.xpath(xp, namespaces=NS):
        e.getparent().remove(e)


@pytest.mark.parametrize("mod", [
    lambda d: _rm(d, D + "/suc:QuadroEC//suc:ValorePrecSucc"),                               # riduzione senza valore prec. succ.
    lambda d: _rm(d, D + "/suc:QuadroEC//suc:Devoluzione/suc:Riduzioni"),                    # valore prec. succ. senza riduzione
    lambda d: d.xpath(D + "/suc:QuadroEC//suc:ValorePrecSucc", namespaces=NS)[0].__setattr__("text", "3000000"),
    lambda d: d.xpath(D + "/suc:QuadroEC//suc:Devoluzione", namespaces=NS)[0].append(
        etree.fromstring('<suc:Agevolazioni xmlns:suc="urn:www.agenziaentrate.gov.it:specificheTecniche:sco:suc:v1">F'
                         '</suc:Agevolazioni>')),                                          # F e riduzione sulla stessa riga
])
def test_calcolo_sul_file_non_supporta_i_casi_incoerenti(mod):
    es = _es(caso_art25())
    r = calcola_da_xml(_muta(es.xml, mod))
    assert r.stato == "non_supportato" and r.imposta_ef18bis is None, r.stato


def test_calcolo_r_su_due_righi_dello_stesso_beneficiario_non_supportato():
    d = base()
    valore(d, "b_terr0001", "400000")
    aggiungi_fabbricato(d, "b_casa0002", "A/3", "150000", "8", anna="F", luca="F")
    rid(d, "d_terranna", agevolazioni="R")
    es = esporta_xml(d, contesto(allegati=ALLEGATI, scopo="bozza_tecnica", data_riferimento=date(2026, 3, 9)))
    r = calcola_da_xml(es.xml)
    assert r.stato == "completato"            # R una volta e F una volta: ammesso
    xml = _muta(es.xml, lambda x: x.xpath(D + "/suc:QuadroEC//suc:Devoluzione/suc:Agevolazioni", namespaces=NS)[0]
                .__setattr__("text", "R"))
    xml = _muta(xml, lambda x: x.xpath(D + "/suc:QuadroEC//suc:Devoluzione/suc:Agevolazioni", namespaces=NS)[0]
                .__setattr__("text", "R"))
    assert calcola_da_xml(xml).stato == "non_supportato"      # R sul fabbricato e R sul terreno per Anna: due righe R


# ================================================================================================ negativi: controllo ufficiale
def _mut_reale(es, fn, tmp_path, nome):
    stato, dgn, wri, _ = _esegui(_muta(es.xml, fn), tmp_path / nome)
    return stato, {q["codice"] for q in dgn["diagnostici"]}, wri


def _vps_testo(d, v):
    d.xpath(D + "/suc:QuadroEC//suc:ValorePrecSucc", namespaces=NS)[0].text = v


@SALTO
@pytest.mark.parametrize("nome,mod,codice,testo", [
    ("senza_vps", lambda d: _rm(d, D + "/suc:QuadroEC//suc:ValorePrecSucc"), "3488", "obbligatorio in"),
    ("vps_maggiore", lambda d: _vps_testo(d, "3000000"), "3301", "maggiore del campo valore"),
    ("riduzione_solo_anna", lambda d: _rm(d, D + "/suc:QuadroEC//suc:Devoluzione[suc:IdentificazioneSoggetto/suc:Rigo='2']"
                                           "/suc:Riduzioni"), "3489", "obbligatorio in tutti i righi"),
    ("senza_eg11", lambda d: _rm(d, D + "/suc:QuadroEG/suc:RiduzioniImposteSuccessione"), "3241", "Allegato EG 11"),
    ("senza_sezione_eh", lambda d: _rm(d, D + "/suc:QuadroEH/suc:PrimoModulo/suc:SezioneIV_AltreAgevRiduz"), "3248",
     "deve essere compilata"),
])
def test_reale_art25_negativi(nome, mod, codice, testo, tmp_path):
    es = _es(caso_art25())
    stato, codici, wri = _mut_reale(es, mod, tmp_path, nome)
    assert stato == "negativo" and codice in codici, (codici, wri[-1200:])
    assert testo in wri


@SALTO
def test_reale_l_senza_sezione_eh_e_senza_eg11(tmp_path):
    es = _es(caso_l())
    stato, codici, wri = _mut_reale(es, lambda d: _rm(d, D + "/suc:QuadroEH/suc:PrimoModulo/suc:SezioneIV_AltreAgevRiduz"),
                                    tmp_path, "l_senza_eh")
    assert stato == "negativo" and {"3243", "3290"} <= codici
    assert "agevolazioni uguali a L o A" in wri


@SALTO
def test_reale_l_con_p_su_altro_rigo_dello_stesso_bene(tmp_path):
    es = _es(caso_l())

    def f(d):
        d.xpath(D + "/suc:QuadroEC//suc:Devoluzione[suc:IdentificazioneSoggetto/suc:Rigo='2']/suc:CodiceDiritto_Rip",
                namespaces=NS)[0].addnext(etree.fromstring(
                    '<suc:Agevolazioni xmlns:suc="urn:www.agenziaentrate.gov.it:specificheTecniche:sco:suc:v1">P'
                    '</suc:Agevolazioni>'))
    stato, codici, wri = _mut_reale(es, f, tmp_path, "l_con_p")
    assert stato == "negativo" and {"3076", "3228"} <= codici
    assert "soltanto una delle seguenti tipologie" in wri


@SALTO
def test_reale_q_su_fabbricato_non_aziendale_e_protocollo_l_corto(tmp_path):
    # l'export rifiuta Q su un fabbricato (non supportato): si cambia il codice nel file valido del caso L e si verifica lo
    # scarto del componente ufficiale
    es = _es(caso_l())

    def f(d):
        dv = d.xpath(D + "/suc:QuadroEC//suc:Devoluzione/suc:Agevolazioni", namespaces=NS)[0]
        dv.text = "Q"
    stato, codici, wri = _mut_reale(es, f, tmp_path, "q_su_ec")
    assert stato == "negativo" and "3333" in codici
    assert "terreni o fabbricati che" in wri and "non siano beni aziendali" in wri
    stato, codici, wri = _mut_reale(es, lambda d: d.xpath(D + "//suc:NumProtocollo", namespaces=NS)[0].__setattr__("text", "ABC123"),
                                    tmp_path, "protocollo_corto")
    assert stato == "negativo" and "3128" in codici and "compreso tra 7 e 16" in wri
