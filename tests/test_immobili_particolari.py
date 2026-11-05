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


# --------------------------------------------------------------------------------------------------------- rendita proposta
def _altro(d, allegato="al_testam"):
    d["documenti_ref"].append({"id": "dr_altro01", "_origine": {}, "allegato_id": allegato, "tipo_eg": "Altro", "finalita": "dichiarazione sostitutiva"})


def rendita_proposta(valore="si", rendita="1500.00", categoria=None, con_eg=True):
    d = caso_a10()
    casa = next(b for b in d["beni"] if b["id"] == "b_casa0001")
    casa["rendita_proposta"] = valore
    if rendita is None:
        casa.pop("rendita", None)
    else:
        casa["rendita"] = rendita
    if categoria:
        casa["categoria"] = categoria
    if con_eg:
        _altro(d)
    return esporta_xml(d, contesto_caso_a10(data_riferimento=date(2026, 3, 9)))


def test_rendita_proposta_scrive_determinazione_rendita():
    es = completo(rendita_proposta())
    ec = D + "/suc:QuadroEC"
    assert x(es, ec + "//*[local-name()='RenditaCatastale']/text()") == ["1500,00"]
    assert x(es, ec + "//*[local-name()='DeterminazioneRendita']/text()") == ["1"]


def test_rendita_proposta_no_non_scrive_nulla():
    es = completo(rendita_proposta("no", con_eg=False))
    assert not x(es, D + "/suc:QuadroEC//*[local-name()='DeterminazioneRendita']")


def test_rendita_proposta_richiede_la_dichiarazione_in_eg():
    es = rendita_proposta(con_eg=False)
    assert not es.completo and any(m.percorso == "quadro[EG].Altro" for m in es.quadri_mancanti)


@pytest.mark.parametrize("rendita,categoria", [(None, None), ("1500.00", "F3")])
def test_rendita_proposta_blocchi(rendita, categoria):
    es = rendita_proposta(rendita=rendita, categoria=categoria)
    assert es.xml is None and any(e.codice in ("REGOLA_RENDITA_PROPOSTA", "DATO_MANCANTE", "REGOLA_RENDITA") for e in es.errori)


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
@pytest.mark.parametrize("rendita,categoria", [("1500.00", None), ("890.45", "A/3"), ("2210.10", "A/7")])
def test_rendita_proposta_controllo_ufficiale(tmp_path, rendita, categoria):
    positivo(completo(rendita_proposta(rendita=rendita, categoria=categoria)), tmp_path)


# --------------------------------------------------------------------------------------------------------------- graffati (EC)
def graffati(voci, sezione=None):
    d = caso_a10()
    d["opzioni"]["telematico"]["beni"]["b_casa0001"]["graffati"] = voci
    if sezione:
        next(b for b in d["beni"] if b["id"] == "b_casa0001")["sezione"] = sezione
    return esporta_xml(d, contesto_caso_a10(data_riferimento=date(2026, 3, 9)))


G1 = {"foglio": "100", "particella": "201", "subalterno": "1"}
G2 = {"foglio": "100", "particella": "202"}
G3 = {"foglio": "101", "particella": "55", "subalterno": "7"}
G4 = {"foglio": "101", "particella": "56", "subalterno": "2"}


@pytest.mark.parametrize("voci", [[G1], [G1, G2], [G1, G2, G3, G4]])
def test_graffati_scrive_immobili_graffati(voci):
    es = completo(graffati(voci))
    g = x(es, D + "/suc:QuadroEC//*[local-name()='ImmobiliGraffati']")
    assert len(g) == len(voci)
    particelle = x(es, D + "/suc:QuadroEC//*[local-name()='Graffati']//*[local-name()='Particella']/text()")
    assert particelle == [v["particella"] for v in voci]


def test_graffati_con_sezione_urbana_obbligatoria():
    sez = [{**G1, "sezione": "AB"}]
    es = completo(graffati(sez, sezione="AB"))
    assert x(es, D + "/suc:QuadroEC//*[local-name()='Graffati']//*[local-name()='SezioneUrbana']/text()") == ["AB"]
    es = graffati([G1], sezione="AB")          # sezione dell'immobile principale ma non del graffato
    assert es.xml is None and any(e.percorso.endswith("graffati[0]") for e in es.errori)
    es = graffati(sez)                          # sezione indicata ma l'immobile principale non ha la sezione
    assert es.xml is None and any(e.percorso.endswith("graffati[0]") for e in es.errori)


def test_graffati_duplicati_e_oltre_quattro_bloccati():
    es = graffati([G1, G1])
    assert es.xml is None and any(e.codice == "REGOLA_GRAFFATI" for e in es.errori)
    es = graffati([G1, G2, G3, G4, {"foglio": "9", "particella": "9"}])
    assert es.xml is None and any("piu' di quattro immobili graffati" in s for s in es.non_supportato)


def test_graffati_dati_mancanti():
    es = graffati([{"foglio": "100"}])
    assert es.xml is None and any(e.codice == "DATO_MANCANTE" for e in es.errori)


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
@pytest.mark.parametrize("voci,sezione", [([G1], None), ([G1, G2, G3, G4], None), ([{**G1, "sezione": "AB"}, {**G3, "sezione": "AB"}], "AB")])
def test_graffati_controllo_ufficiale(tmp_path, voci, sezione):
    positivo(completo(graffati(voci, sezione)), tmp_path)
