"""Frontespizio: caselle (legge estera, eventi eccezionali, opzione art. 24-bis, beneficio d'inventario, residenza estera del defunto, casi
particolari, decorrenza), dichiarazione integrativa codice 3 (solo frontespizio ed EG) e codici carica 2, 3, 4, 7 del presentatore.
Fonti: XSD fornituraSUC13_v1.xsd (FrontespizioSUC_Type, QuadroEH, QuadroEG), Fascicolo I pp. PDF 11-15 e 45. I casi positivi sono stati
accettati dal controllo ufficiale SUC13 2.3.1 eseguito in locale il 2026-11-05 (dati sintetici; non e' una verifica con l'Agenzia)."""
import copy
from datetime import date

import pytest
from lxml import etree

from telematico_casi import (CF_LUCA, caso_a10, caso_testamento, caso_testamento_legatario, contesto_caso_a10)
from successioni.telematico.esporta import esporta_xml
from successioni.telematico.identificativi import genera_cf_sintetico
from test_telematico_controllo import _esegui, _motivo_salto

SALTO = _motivo_salto()
CF_PAOLO = "VRDPLA80C03H501A"
TEMPESTIVO = date(2026, 3, 9)


def esporta(d, cf_fornitore=None, **kw):
    cf = cf_fornitore or d["opzioni"]["telematico"]["dichiarazione"]["versamento"]["cf_titolare"]
    kw.setdefault("data_riferimento", TEMPESTIVO)
    return esporta_xml(d, contesto_caso_a10(cf_fornitore=cf, **kw))


def ok(es):
    assert es.completo, [e.messaggio for e in es.errori] + es.non_supportato + [m.messaggio for m in es.quadri_mancanti]
    return es


def codici(es):
    return {e.codice for e in es.errori}


def controllo(es, tmp_path):
    stato, dgn, wri, _ = _esegui(es.xml, tmp_path)
    assert stato == "positivo", (dgn["diagnostici"], wri[:1200])
    assert [x["codice"] for x in dgn["diagnostici"]] in ([], ["3345"])          # al piu' l'avviso sull'attestazione
    return dgn


def dich(d):
    return d["opzioni"]["telematico"]["dichiarazione"]


def con_doc(d, did, tipo):
    d["documenti_ref"].append({"id": did, "_origine": {}, "allegato_id": "al_testam", "tipo_eg": tipo, "finalita": "documento (sintetico)"})
    return d


def x(es, xp):
    doc = etree.fromstring(es.xml)
    return doc.xpath(xp, namespaces={k: v for k, v in doc.nsmap.items() if k})


D = "//suc:Dichiarazione"
SALTA = pytest.mark.skipif(SALTO is not None, reason=SALTO or "")


# ============================================================================================= caselle del frontespizio
def caso_casella(nome):
    d = copy.deepcopy(caso_a10())
    if nome == "eventi":
        con_doc(d, "dr_altro01", "Altro")
    dich(d).update({"legge": {"legge_estera": True}, "eventi": {"eventi_eccezionali": True}, "opzione": {"data_opzione": "2020-05-10"},
                    "inventario": {"beneficio_inventario": True}, "res1": {"residenza_estera_defunto": "1"},
                    "res2": {"residenza_estera_defunto": "2"}, "casi": {"casi_particolari": True}}.get(nome, {}))
    if nome == "decorrenza":
        dich(d)["presentatore"]["data_decorrenza"] = "2026-03-20"
    return d


@SALTA
@pytest.mark.parametrize("nome", ["legge", "eventi", "opzione", "inventario", "res1", "res2", "casi", "decorrenza"])
@pytest.mark.java
def test_caselle_accettate_dal_controllo(nome, tmp_path):
    es = ok(esporta(caso_casella(nome)))
    controllo(es, tmp_path)


def test_xml_delle_caselle():
    assert x(ok(esporta(caso_casella("legge"))), f"{D}/suc:Frontespizio/suc:TipoDichiarazione/suc:Devoluzione/suc:LeggeEstera/text()") == ["1"]
    es = ok(esporta(caso_casella("eventi")))
    assert x(es, f"{D}/suc:Frontespizio/suc:TipoDichiarazione/suc:EventiEccezionali/text()") == ["1"]
    es = ok(esporta(caso_casella("opzione")))
    assert x(es, f"{D}/suc:Frontespizio/suc:TipoDichiarazione/suc:DataOpzione/text()") == ["10052020"]
    es = ok(esporta(caso_casella("inventario")))
    assert x(es, f"{D}/suc:Frontespizio/suc:Beneficiari/suc:AccettazioneConBeneficioInventario/text()") == ["1"]
    es = ok(esporta(caso_casella("res2")))
    assert x(es, f"{D}/suc:Frontespizio/suc:DatiDefunto/suc:UlterioriDati/suc:ResidenzaEstera/text()") == ["2"]
    es = ok(esporta(caso_casella("decorrenza")))
    assert x(es, f"{D}/suc:Frontespizio/suc:Presentatore/suc:DecorrenzaTerminePresentazione/text()") == ["20032026"]


def test_casi_particolari_tassa_ipotecaria_65_per_circoscrizione():
    """Fascicolo I p. PDF 45: con la casella «non dar corso alle volture» la tassa ipotecaria e' di 65 euro per circoscrizione; con 120 il
    controllo ufficiale respinge (diagnostico 3076)."""
    es = ok(esporta(caso_casella("casi")))
    assert x(es, f"{D}/suc:QuadroEF/suc:SezioneIII_TassaIpotecaria/*/text()") == ["1", "65"]
    assert x(es, f"{D}/suc:Frontespizio/suc:CasiParticolari/suc:CasiParticolari/text()") == ["1"]
    base = ok(esporta(caso_a10()))
    assert x(base, f"{D}/suc:QuadroEF/suc:SezioneIII_TassaIpotecaria/*/text()") == ["1", "120"]


@SALTA
@pytest.mark.java
def test_casi_particolari_con_120_e_respinto(tmp_path):
    es = ok(esporta(caso_casella("casi")))
    alterato = es.xml.replace(b">65<", b">120<", 1)
    assert alterato != es.xml
    stato, dgn, _, _ = _esegui(alterato, tmp_path, rapporto=False)
    assert stato == "negativo" and any(d["codice"] == "3076" for d in dgn["diagnostici"])


def test_eventi_eccezionali_richiedono_il_rigo_altro():
    d = copy.deepcopy(caso_a10())
    dich(d)["eventi_eccezionali"] = True
    es = esporta(d)
    assert not es.completo and any(m.percorso == "quadro[EG].Altro" for m in es.quadri_mancanti)


@pytest.mark.parametrize("chiave,valore", [
    ("data_opzione", "2016-12-31"),             # non inferiore al 1 gennaio 2017
    ("data_opzione", "2026-03-10"),             # anteriore al decesso (2026-03-10)
    ("data_opzione", "non-una-data"),
    ("residenza_estera_defunto", "3"),
    ("eventi_eccezionali", "2"),
    ("legge_estera", "si"),
])
def test_valori_non_validi(chiave, valore):
    d = copy.deepcopy(caso_a10())
    dich(d)[chiave] = valore
    es = esporta(d)
    assert es.xml is None and es.errori


def test_decorrenza_non_puo_precedere_il_decesso():
    d = copy.deepcopy(caso_a10())
    dich(d)["presentatore"]["data_decorrenza"] = "2025-03-09"        # il decesso di caso_a10 e' del 2025-03-10
    assert "REGOLA_DECORRENZA_TERMINE" in codici(esporta(d))


# ============================================================================================ integrativa (codice 3)
def caso_integrativa(base=caso_a10, extra=None):
    d = copy.deepcopy(base())
    d["opzioni"]["tipo_dichiarazione"] = "sostitutiva"
    dich(d).update(codice_sostitutiva="3", prima_anno="2026", prima_volume="88888", prima_numero="123")
    dich(d).update(extra or {})
    return d


@SALTA
@pytest.mark.parametrize("base", [caso_a10, caso_testamento, caso_testamento_legatario])
@pytest.mark.java
def test_integrativa_accettata_dal_controllo(base, tmp_path):
    es = ok(esporta(caso_integrativa(base)))
    controllo(es, tmp_path)
    figli = [etree.QName(c).localname for c in x(es, D)[0]]
    assert figli == ["Frontespizio", "QuadroEG"]                                   # nient'altro
    assert x(es, f"{D}/suc:Frontespizio/suc:TipoDichiarazione/suc:DichiarazioneSostitutiva/text()") == ["3"]
    assert [etree.QName(c).localname for c in x(es, f"{D}/suc:Frontespizio/suc:FirmaModello/*")] == ["CasellaEG", "FirmaDichiarante"]
    assert "INTEGRATIVA_SOLO_FRONTESPIZIO_EG" in {a.codice for a in es.avvisi}


def test_integrativa_senza_documenti_non_completa():
    d = caso_integrativa()
    d["documenti_ref"] = []
    es = esporta(d)
    assert not es.completo and any(m.percorso.startswith("quadro[EG]") for m in es.quadri_mancanti)


@pytest.mark.parametrize("extra,codice", [
    ({"prima_numero": None}, "DATO_MANCANTE"),
    ({"ipotecaria_versata": "100"}, "VALORE_NON_VALIDO"),                          # nessuna imposta si liquida con il codice 3
    ({"prima_volume": "1"}, "VALORE_NON_VALIDO"),
])
def test_integrativa_dati_non_validi(extra, codice):
    es = esporta(caso_integrativa(extra=extra))
    assert es.xml is None and codice in codici(es)


# =========================================================================================== codici carica del presentatore
def con_presentatore(d, nome, cognome, carica, rappresentato=None, extra=None):
    cf = genera_cf_sintetico(cognome, nome, "M", "1965-06-06", "H501")
    d["persone"] = [p for p in d["persone"] if p.get("ruolo") != "presentatore"]
    d["persone"].append({"id": "p_pres0001", "_origine": {}, "cognome": cognome, "nome": nome, "codice_fiscale": cf,
                         "data_nascita": "1965-06-06", "luogo_nascita": "Roma", "ruolo": "presentatore"})
    tel = d["opzioni"]["telematico"]
    tel["persone"]["p_pres0001"] = {"sesso": "M", "provincia_nascita": "RM"}
    pres = {"codice_carica": carica, "telefono": "0612345678"}
    if rappresentato:
        pres["rappresentato_cf"] = rappresentato
    pres.update(extra or {})
    tel["dichiarazione"]["presentatore"] = pres
    tel["dichiarazione"]["versamento"]["cf_titolare"] = cf
    return d


def carica_2():
    d = copy.deepcopy(caso_testamento_legatario())
    dich(d)["presentatore"] = {"persona_id": "p_paolo001", "codice_carica": "2", "telefono": "0612345678"}
    dich(d)["versamento"]["cf_titolare"] = CF_PAOLO
    return d


def carica_3():
    return con_presentatore(copy.deepcopy(caso_testamento_legatario()), "Carlo", "Verdi", "3", CF_PAOLO)


def carica_4():
    return con_presentatore(copy.deepcopy(caso_a10()), "Giorgio", "Rossi", "4", CF_LUCA)


def carica_4_estero():
    return con_presentatore(copy.deepcopy(caso_a10()), "Giorgio", "Rossi", "4", CF_LUCA,
                            {"residente_estero": {"codice_stato": "029", "stato": "FRANCIA", "localita": "PARIGI", "indirizzo": "RUE EXEMPLE 1"}})


def carica_7():
    d = con_presentatore(copy.deepcopy(caso_testamento()), "Franco", "Neri", "7")
    con_doc(d, "dr_dsost01", "DichSost")
    con_doc(d, "dr_ident01", "DocumentiIdentita")
    return d


@SALTA
@pytest.mark.parametrize("caso", [carica_2, carica_3, carica_4, carica_4_estero, carica_7], ids=lambda f: f.__name__)
@pytest.mark.java
def test_cariche_accettate_dal_controllo(caso, tmp_path):
    es = ok(esporta(caso()))
    controllo(es, tmp_path)


def test_xml_cariche():
    es = ok(esporta(carica_4()))
    assert x(es, f"{D}/suc:Frontespizio/suc:Presentatore/suc:CodiceCarica/text()") == ["4"]
    assert x(es, f"{D}/suc:Frontespizio/suc:Presentatore/suc:CodiceFiscaleRappresentato/text()") == [CF_LUCA]
    assert x(es, f"{D}/suc:QuadroEH/suc:PrimoModulo/suc:SezioneI_DichSost/suc:Dichiarante/suc:FlagAssenzaDichiarante/text()") == ["1"]
    es = ok(esporta(carica_2()))
    assert x(es, f"{D}/suc:QuadroEH/suc:PrimoModulo/suc:SezioneI_DichSost/suc:Dichiarante/suc:PresenzaDichiarante/text()") == ["1"]
    es = ok(esporta(carica_7()))
    assert not x(es, f"{D}/suc:QuadroEH")                                         # annotazione: non presente con codice carica 7


@pytest.mark.parametrize("carica", ["9"])      # 5, 6 e 8 sono ora supportate: tests/test_cariche_trust.py
def test_cariche_non_supportate_restano_bloccate(carica):
    d = copy.deepcopy(caso_a10())
    dich(d)["presentatore"]["codice_carica"] = carica
    es = esporta(d)
    assert es.xml is None and any("codice_carica=" + carica in n for n in es.non_supportato)


@pytest.mark.parametrize("modifica,codice", [
    (lambda d: dich(d)["presentatore"].pop("rappresentato_cf"), "DATO_MANCANTE"),                 # carica 4 senza rappresentato
    (lambda d: dich(d)["presentatore"].update(rappresentato_cf="RSSMRA40A01H501K"), "REGOLA_RAPPRESENTATO"),  # = defunto
    (lambda d: dich(d)["presentatore"].update(rappresentato_cf="NONVALIDO"), "VALORE_NON_VALIDO"),
])
def test_carica_4_dati_non_validi(modifica, codice):
    d = carica_4()
    modifica(d)
    assert codice in codici(esporta(d))


def test_rappresentato_vietato_con_carica_1():
    d = copy.deepcopy(caso_a10())
    dich(d)["presentatore"]["rappresentato_cf"] = CF_LUCA
    assert "DATI_INCOERENTI" in codici(esporta(d))


def test_carica_2_richiede_testamento_e_tipo_legatario():
    d = carica_2()
    dich(d).pop("devoluzione_per_testamento")
    dich(d)["devoluzione_per_legge"] = True
    assert "REGOLA_CARICA_LEGATARIO" in codici(esporta(d))
    d = carica_2()
    dich(d)["presentatore"] = {"persona_id": "p_anna0001", "codice_carica": "2", "telefono": "0612345678"}   # un erede: tipo 1
    assert "REGOLA_PRESENTATORE" in codici(esporta(d))


def test_carica_7_richiede_il_testamento():
    d = carica_7()
    dich(d).pop("devoluzione_per_testamento")
    dich(d)["devoluzione_per_legge"] = True
    dich(d).pop("testamento", None)
    assert "REGOLA_CARICA_ESECUTORE" in codici(esporta(d))


def test_carica_7_richiede_la_dichiarazione_sostitutiva_eg1():
    d = carica_7()
    d["documenti_ref"] = [r for r in d["documenti_ref"] if r["tipo_eg"] != "DichSost"]
    es = esporta(d)
    assert not es.completo and any(m.percorso == "quadro[EG].DichSost" for m in es.quadri_mancanti)
