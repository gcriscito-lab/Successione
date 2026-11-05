"""Immobili particolari (pacchetto 5): EI con piu' di tre estremi (Continuazione), rendita proposta, graffati, immobili aziendali.
Ogni caso positivo e' stato accettato dal controllo ufficiale SUC13 2.3.1 eseguito in locale il 2026-11-05 (dati sintetici)."""
import copy
from datetime import date

import pytest
from lxml import etree

from successioni.telematico.esporta import esporta_xml
from telematico_casi import caso_a10, caso_voltura, contesto_caso_a10
from test_telematico_controllo import NS, _esegui, _motivo_salto

D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"
EI = D + "/suc:QuadroEI_new"
CTX = contesto_caso_a10(data_riferimento=date(2025, 9, 1))
SALTO = _motivo_salto()


def x(es, xp):
    return etree.fromstring(es.xml).xpath(xp, namespaces=NS)


def completo(es):
    assert es.completo, ([e.messaggio for e in es.errori], es.non_supportato, [m.messaggio for m in es.quadri_mancanti])
    return es


def positivo(es, tmp_path):
    stato, dgn, wri, _ = _esegui(es.xml, tmp_path)
    assert stato == "positivo", (dgn["diagnostici"], wri[:1200])
    assert [d["codice"] for d in dgn["diagnostici"]] == ["3345"], dgn["diagnostici"]      # solo l'avviso sull'attestazione


# --------------------------------------------------------------------------------------------------- EI: piu' di tre estremi
def _tr(n):
    return [{"ufficio": "RM10", "registro_particolare": str(10000 + i), "anno": str(2005 + i)} for i in range(n)]


def _rg(n):
    return [{"ufficio": "795", "anno": str(2010 + i), "volume": "88888", "numero": str(100 + i)} for i in range(n)]


def ei(n_tr, n_rg):
    d = caso_voltura()
    t = d["opzioni"]["telematico"]["beni"]["b_casa0001"]
    t["estremi_trascrizione"], t["estremi_registrazione"] = _tr(n_tr), _rg(n_rg)
    return esporta_xml(d, CTX)


@pytest.mark.parametrize("n_tr,n_rg,moduli", [(4, 1, 2), (2, 5, 2), (6, 2, 2), (4, 4, 2), (7, 7, 3), (3, 3, 1)])
def test_ei_continuazione_sui_moduli_successivi(n_tr, n_rg, moduli):
    es = completo(ei(n_tr, n_rg))
    primo = EI + "/suc:PrimoModulo/suc:SezioneII_DatiIntestatario"
    altri = EI + "/suc:Modulo/suc:SezioneII_DatiIntestatario"
    assert len(x(es, primo + "/suc:EstremiTrascrizione")) == min(n_tr, 3)
    assert len(x(es, primo + "/suc:EstremiRegistrazione")) == min(n_rg, 3)
    assert len(x(es, altri)) == moduli - 1
    assert len(x(es, primo + "/suc:Continuazione")) == (1 if moduli > 1 else 0)
    assert len(x(es, EI + "//suc:EstremiTrascrizione")) == n_tr and len(x(es, EI + "//suc:EstremiRegistrazione")) == n_rg
    assert not x(es, altri + "/suc:Immobile"), "i moduli di continuazione non riportano i dati dell'immobile"
    assert not x(es, altri + "/suc:FirmaDichiarante")
    # solo l'ultimo modulo non ha la casella continuazione
    assert len(x(es, EI + "//suc:Continuazione")) == moduli - 1


@pytest.mark.parametrize("n_tr,n_rg", [(3, 4), (3, 5), (5, 3)])
def test_ei_continuazione_non_esprimibile_resta_bloccata(n_tr, n_rg):
    """Entrambe le liste piene nel primo modulo e overflow di una sola: l'XSD lo ammette ma il controllo ufficiale lo scarta."""
    es = ei(n_tr, n_rg)
    assert es.xml is None and any("modulo di continuazione deve contenere almeno un estremo di ciascun tipo" in s for s in es.non_supportato)


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
@pytest.mark.parametrize("n_tr,n_rg", [(4, 1), (2, 5), (6, 2), (4, 4), (7, 7)])
def test_ei_continuazione_controllo_ufficiale(tmp_path, n_tr, n_rg):
    positivo(completo(ei(n_tr, n_rg)), tmp_path)


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
def test_ei_continuazione_senza_la_casella_e_respinta(tmp_path):
    """Negativo: tolta la casella Continuazione il controllo respinge gli estremi del modulo successivo."""
    es = completo(ei(4, 1))
    xml = es.xml.replace(b"<Continuazione>1</Continuazione>", b"", 1)
    if xml == es.xml:
        import re
        xml = re.sub(rb"<(?:\w+:)?Continuazione>1</(?:\w+:)?Continuazione>", b"", es.xml, count=1)
    assert xml != es.xml
    stato, dgn, _, _ = _esegui(xml, tmp_path)
    assert stato == "negativo", dgn["diagnostici"]
