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
@pytest.mark.java
def test_ei_continuazione_controllo_ufficiale(tmp_path, n_tr, n_rg):
    positivo(completo(ei(n_tr, n_rg)), tmp_path)


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
@pytest.mark.java
def test_ei_continuazione_senza_la_casella_e_respinta(tmp_path):
    """Negativo: tolta la casella Continuazione il controllo respinge gli estremi del modulo successivo."""
    es = completo(ei(4, 1))
    xml = es.xml.replace(b"<Continuazione>1</Continuazione>", b"", 1)
    if xml == es.xml:
        import re
        xml = re.sub(rb"<(?:\w+:)?Continuazione>1</(?:\w+:)?Continuazione>", b"", es.xml, count=1)
    assert xml != es.xml
    stato, dgn, _, _ = _esegui(xml, tmp_path, rapporto=False)
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
@pytest.mark.java
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
@pytest.mark.java
def test_graffati_controllo_ufficiale(tmp_path, voci, sezione):
    positivo(completo(graffati(voci, sezione)), tmp_path)


# ------------------------------------------------------------------------------------------------- immobili aziendali (EB/EC + EN)
from telematico_casi import caso_azienda  # noqa: E402


def aziendale(immobili=("b_casa0001",), valore_az="20000", collegati=None, mod=None):
    d = copy.deepcopy(caso_azienda())
    for bid in immobili:
        next(b for b in d["beni"] if b["id"] == bid)["bene_aziendale"] = "si"
    d["opzioni"]["telematico"]["beni"].setdefault("b_azien001", {})["immobili_aziendali"] = list(immobili if collegati is None else collegati)
    next(b for b in d["beni"] if b["id"] == "b_azien001")["valore"] = valore_az
    d["opzioni"]["telematico"]["dichiarazione"]["tempistica_pagamento"] = "2"
    if mod:
        mod(d)
    return esporta_xml(d, contesto_caso_a10(data_riferimento=date(2026, 3, 9)))


def test_immobile_aziendale_scrive_casella_e_collegamento():
    es = completo(aziendale())
    assert x(es, D + "/suc:QuadroEC//suc:BeneAziendale/text()") == ["1"]
    ia = D + "/suc:QuadroEN//suc:ImmobiliAziendali"
    assert x(es, ia + "/suc:Quadro/text()") == ["EC"]
    assert x(es, ia + "/suc:Identificativo/suc:Rigo/text()") == ["1"] and x(es, ia + "/suc:Identificativo/suc:Modulo/text()") == ["1"]


def test_ee_esclude_gli_immobili_aziendali_dal_totale_immobili():
    senza = completo(esporta_xml(caso_azienda(), contesto_caso_a10(data_riferimento=date(2026, 3, 9))))
    con = completo(aziendale())
    tot = lambda es: int(x(es, D + "/suc:QuadroEE//suc:TotaleValoreImmobili/text()")[0])
    assert tot(senza) - tot(con) == 126000          # il valore della casa non e' piu' fra gli immobili (e' compreso nell'azienda)


def test_due_immobili_aziendali_in_un_collegamento():
    es = completo(aziendale(("b_casa0001", "b_terr0001")))
    assert x(es, D + "/suc:QuadroEN//suc:ImmobiliAziendali/suc:Quadro/text()") == ["EC", "EB"] or \
        sorted(x(es, D + "/suc:QuadroEN//suc:ImmobiliAziendali/suc:Quadro/text()")) == ["EB", "EC"]


def test_immobile_aziendale_non_collegato_o_collegamento_errato():
    es = aziendale(collegati=[])
    assert es.xml is None and any(e.codice == "IMMOBILE_AZIENDALE_NON_COLLEGATO" for e in es.errori)
    es = aziendale(immobili=(), collegati=["b_casa0001"])        # collegato ma senza la casella
    assert es.xml is None and any(e.codice == "RIFERIMENTO_INESISTENTE" for e in es.errori)
    es = aziendale(collegati=["b_casa0001", "b_casa0001"])
    assert es.xml is None and any(e.codice == "REGOLA_IMMOBILI_AZIENDALI" for e in es.errori)


def test_immobile_aziendale_senza_quadro_en():
    d = copy.deepcopy(caso_a10())
    next(b for b in d["beni"] if b["id"] == "b_casa0001")["bene_aziendale"] = "si"
    es = esporta_xml(d, contesto_caso_a10(data_riferimento=date(2026, 3, 9)))
    assert es.xml is None and any(e.codice == "QUADRO_EN_OBBLIGATORIO" for e in es.errori)


def test_immobile_aziendale_con_agevolazione_non_ammessa():
    def mod(d):
        d["opzioni"]["telematico"].setdefault("devoluzioni", {})["d_casaanna"] = {"agevolazioni": "P"}
    es = aziendale(mod=mod)
    assert es.xml is None and any(e.codice == "REGOLA_BENE_AZIENDALE" for e in es.errori)


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
@pytest.mark.parametrize("immobili,valore_az", [(("b_casa0001",), "20000"), (("b_casa0001", "b_terr0001"), "20000"), (("b_casa0001",), "3000000")])
@pytest.mark.java
def test_immobile_aziendale_controllo_ufficiale(tmp_path, immobili, valore_az):
    positivo(completo(aziendale(immobili, valore_az)), tmp_path)


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
@pytest.mark.java
def test_immobile_aziendale_imposta_alterata_respinta(tmp_path):
    """Con l'imposta di successione dovuta il controllo verifica il calcolo: un'imposta alterata viene respinta."""
    es = completo(aziendale(valore_az="3000000"))
    imposta = x(es, D + "/suc:QuadroEF//suc:ImpostaCalcolata/suc:Imposta/text()")[0]
    xml = es.xml.replace(f">{imposta}<".encode(), f">{int(imposta) + 100}<".encode())
    assert xml != es.xml
    stato, dgn, _, _ = _esegui(xml, tmp_path, rapporto=False)
    assert stato == "negativo", dgn["diagnostici"]


# ------------------------------------------------------------------------------------------ diritto di abitazione (casi in
# tests/test_diritto_abitazione.py)
def test_diritto_abitazione_senza_coniuge_errore_esplicito():
    d = caso_a10()
    next(b for b in d["beni"] if b["id"] == "b_casa0001")["diritto_abitazione"] = "1"
    es = esporta_xml(d, contesto_caso_a10(data_riferimento=date(2026, 3, 9)))
    assert es.xml is None and any(e.codice == "REGOLA_DIRITTO_ABITAZIONE" for e in es.errori)


def test_senza_coniuge_nessun_avviso_sul_diritto_di_abitazione():
    es = completo(esporta_xml(caso_a10(), contesto_caso_a10(data_riferimento=date(2026, 3, 9))))
    assert "DIRITTO_ABITAZIONE_DA_VERIFICARE" not in {a.codice for a in es.avvisi}


def test_con_coniuge_e_abitazione_compare_l_avviso():
    d = caso_a10()
    d["opzioni"]["telematico"]["dichiarazione"]["stato_civile"] = "2"            # vedovo: ammette un coniuge fra i soggetti EA
    anna = next(p for p in d["persone"] if p["id"] == "p_anna0001")
    anna["relazione_con_defunto"] = "01"
    d["opzioni"]["telematico"]["persone"]["p_anna0001"]["grado_parentela"] = "01"
    es = esporta_xml(d, contesto_caso_a10(data_riferimento=date(2026, 3, 9)))
    assert "DIRITTO_ABITAZIONE_DA_VERIFICARE" in {a.codice for a in es.avvisi}, ([e.messaggio for e in es.errori], es.non_supportato)
