"""EF per successioni aperte prima del 2025 (dal 2006-10-03): imposte ipotecaria e catastale, tassa ipotecaria e bollo senza la
sezione V-bis (l'imposta di successione la liquida l'ufficio). Misura fissa 200 euro dal 2014-01-01, 168 dal 2006-10-03 al
2013-12-31.

Fonti: Fascicolo I pp. PDF 9, 39 (decorrenze e misura fissa) e 46; annotazioni XSD di QuadroEF (obbligatorieta' con EA e immobili),
di SezioneVBis_ImpostaSuccessione («non puo' essere presente per le successioni aperte prima del 01/01/2025») e delle imposte fisse
(«168 ... 200 dal 01/01/2014»). Il controllo ufficiale SUC13 2.3.1 eseguito in locale il 2026-11-05 accetta tutti i casi positivi e
respinge 200 per un decesso del 2013 e 168 per uno del 2024 (la misura fissa dipende davvero dalla data del decesso)."""
import copy
from datetime import date

import pytest
from lxml import etree

from telematico_casi import caso_a10, contesto_caso_a10
from successioni.telematico.esporta import esporta_xml
from test_conservatorie import caso_comuni
from test_ef_minimo_fisso import piccolo
from test_ef_soli_terreni import solo_terreni
from test_telematico_controllo import _esegui, _motivo_salto
from test_telematico_prima_casa import caso_prima_casa

EF = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione/suc:QuadroEF"
FR = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione/suc:Frontespizio"


def con_data(d, data):
    d = copy.deepcopy(d)
    for p in d["persone"]:
        if p.get("ruolo") == "defunto":
            p["data_decesso"] = data
    return d


def esporta(d, data, **ctx):
    es = esporta_xml(con_data(d, data), contesto_caso_a10(**ctx))
    assert es.completo, [e.messaggio for e in es.errori] + es.non_supportato + [m.messaggio for m in es.quadri_mancanti]
    return es


def v(es, xp, base=EF):
    doc = etree.fromstring(es.xml)
    return doc.xpath(f"{base}/{xp}/text()", namespaces={k: x for k, x in doc.nsmap.items() if k})


def avvisi(es):
    return {a.codice for a in es.avvisi}


# ---- struttura: nessuna sezione V-bis, totale e frontespizio coerenti ---------------------------------------------------------
@pytest.mark.parametrize("data", ["2024-12-31", "2024-03-10", "2020-06-01", "2016-03-10", "2014-01-01", "2013-12-31", "2013-03-10",
                                  "2006-10-03"])
def test_senza_vbis_e_totali(data):
    es = esporta(caso_a10(), data)
    assert not v(es, "suc:SezioneVBis_ImpostaSuccessione") and b"SezioneVBis" not in es.xml
    assert v(es, "suc:SezioneI_ImpostaIpotecaria/suc:ImpostaProporzionale/*") == ["141000", "2820"]
    assert v(es, "suc:SezioneII_ImpostaCatastale/suc:ImpostaProporzionale/*") == ["141000", "1410"]
    assert v(es, "suc:TotaleDaVersare") == ["4435,00"]                # 2820 + 1410 + 120 + 85, nessuna imposta di successione
    assert v(es, "suc:Frontespizio/suc:ImportoDaVersare", FR.rsplit("/", 1)[0]) == ["4435,00"]


def test_dal_2025_la_vbis_resta():
    es = esporta(caso_a10(), "2025-01-01")
    assert v(es, "suc:SezioneVBis_ImpostaSuccessione/suc:ImpostaNonDovuta") == ["1"]


def test_prima_del_2006_resta_bloccato():
    es = esporta_xml(con_data(piccolo(), "2006-10-02"), contesto_caso_a10())
    assert es.xml is None and not es.completo
    # lo blocca gia' la validazione della data (annotazione XSD di DataDecesso: «maggiore del 2 ottobre 2006»)
    assert any("2 ottobre 2006" in e.messaggio for e in es.errori)


# ---- misura fissa per periodo ------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("data,fissa", [("2013-12-31", 168), ("2014-01-01", 200), ("2006-10-03", 168), ("2024-03-10", 200)])
def test_minimo_fisso_per_periodo(data, fissa):
    es = esporta(piccolo(), data)               # 7.000 euro: ipotecaria 140, catastale 70, dovuto al minimo fisso
    assert v(es, "suc:SezioneI_ImpostaIpotecaria/suc:ImpostaProporzionale/*") == ["7000", "140"]
    assert v(es, "suc:SezioneI_ImpostaIpotecaria/suc:ImpostaIpotecariaDovuta") == [str(fissa)]
    assert v(es, "suc:SezioneII_ImpostaCatastale/suc:ImpostaCatastaleDovuta") == [str(fissa)]
    assert v(es, "suc:TotaleDaVersare") == [f"{2 * fissa + 205},00"]


@pytest.mark.parametrize("data,fissa", [("2013-03-10", 168), ("2024-03-10", 200)])
def test_prima_casa_per_periodo(data, fissa):
    es = esporta_xml(con_data(caso_prima_casa(), data), contesto_caso_a10())
    assert es.completo, [e.messaggio for e in es.errori] + [m.messaggio for m in es.quadri_mancanti]
    assert v(es, "suc:SezioneI_ImpostaIpotecaria/suc:PrimaCasa/suc:PrimaCasa_Imposta") == [str(fissa)]
    assert v(es, "suc:SezioneII_ImpostaCatastale/suc:ImpostaCatastaleFissa") == [str(fissa)]
    assert v(es, "suc:SezioneI_ImpostaIpotecaria/suc:ImpostaIpotecariaDovuta") == [str(600 + fissa)]
    assert v(es, "suc:SezioneII_ImpostaCatastale/suc:ImpostaCatastaleDovuta") == [str(300 + fissa)]


@pytest.mark.parametrize("data,atteso", [
    ("2022-05-20", (["200"], ["200"], ["605,00"])),      # soli terreni non edificabili, imposte sotto il minimo
    ("2013-05-20", (["168"], ["168"], ["541,00"])),
])
def test_soli_terreni_per_periodo(data, atteso):
    es = esporta(solo_terreni("3000"), data)
    got = (v(es, "suc:SezioneI_ImpostaIpotecaria/suc:ImpostaProporzionale/suc:ImpostaProporzionale_Imposta"),
           v(es, "suc:SezioneII_ImpostaCatastale/suc:ImpostaProporzionale/suc:ImpostaProporzionale_Imposta"),
           v(es, "suc:TotaleDaVersare"))
    assert got == atteso


def test_soli_terreni_valori_fiscali_prima_del_2025():
    es = esporta(solo_terreni("100000"), "2022-05-20")        # valore fiscale inferiore alle imposte: 2/3 e 1/3
    assert v(es, "suc:SezioneI_ImpostaIpotecaria/suc:ImpostaProporzionale/suc:ImpostaProporzionale_Imposta") == ["463"]
    assert v(es, "suc:SezioneII_ImpostaCatastale/suc:ImpostaProporzionale/suc:ImpostaProporzionale_Imposta") == ["231"]


# ---- sostitutive e piu' comuni con decesso storico ---------------------------------------------------------------------------
@pytest.mark.parametrize("data,codice,ip,cat,totale", [
    ("2013-03-10", "1", 168, 168, "541,00"),     # codice 1: non meno della misura fissa dell'epoca (168), nuova trascrizione
    ("2013-03-10", "2", 68, 118, "186,00"),      # codice 2: nessuna circoscrizione
    ("2020-03-10", "1", 200, 200, "605,00"),
    ("2020-03-10", "2", 100, 150, "250,00"),
])
def test_sostitutiva_con_decesso_storico(data, codice, ip, cat, totale):
    d = con_data(piccolo(), data)
    d["opzioni"]["tipo_dichiarazione"] = "sostitutiva"
    d["opzioni"]["telematico"]["dichiarazione"].update(codice_sostitutiva=codice, prima_anno="2021", prima_volume="88888",
                                                       prima_numero="1", ipotecaria_versata="100", catastale_versata="50")
    es = esporta_xml(d, contesto_caso_a10())
    assert es.completo, [e.messaggio for e in es.errori] + [m.messaggio for m in es.quadri_mancanti]
    assert v(es, "suc:SezioneI_ImpostaIpotecaria/suc:ImpostaIpotecariaDaVersare") == [str(ip)]
    assert v(es, "suc:SezioneII_ImpostaCatastale/suc:ImpostaCatastaleDaVersare") == [str(cat)]
    assert v(es, "suc:TotaleDaVersare") == [totale]


def test_due_comuni_con_decesso_storico():
    pytest.importorskip("successioni.telematico.conservatorie")
    from successioni.telematico import conservatorie as CO
    if CO.tabella() is None:
        pytest.skip("componente di controllo SUC13 non configurato")
    es = esporta(caso_comuni(("H501", "RM"), ("F205", "MI")), "2018-03-10")
    assert v(es, "suc:SezioneIII_TassaIpotecaria/*") == ["2", "240"]
    assert v(es, "suc:TotaleDaVersare") == ["4640,00"]


# ---- avvisi -----------------------------------------------------------------------------------------------------------------
def test_dichiarazione_tardiva_avvisa_che_sanzioni_e_interessi_non_sono_calcolati():
    es = esporta(caso_a10(), "2016-03-10")                           # contesto: presentazione 2026-11-01
    assert "EF_TARDIVA_SANZIONI_NON_CALCOLATE" in avvisi(es)
    assert not v(es, "suc:SezioneVI_SanzioniInteressi")


def test_dichiarazione_tempestiva_senza_avviso():
    es = esporta(caso_a10(), "2024-12-01", data_riferimento=date(2025, 6, 1))
    assert "EF_TARDIVA_SANZIONI_NON_CALCOLATE" not in avvisi(es)


def test_dati_di_pagamento_non_applicabili_prima_del_2025_sono_segnalati():
    d = copy.deepcopy(caso_a10())
    d["opzioni"]["telematico"]["dichiarazione"].update(tempistica_pagamento="2", pagamento_rateale=4, acconto="5000")
    es = esporta(d, "2024-03-10")
    assert "DATO_NON_APPLICABILE_PRIMA_DEL_2025" in avvisi(es)
    assert b"PagamentoRateale" not in es.xml and b"TempisticaPagamento" not in es.xml
    # dal 2025 gli stessi dati non sono ignorati: senza imposta di successione da versare la rateazione e' respinta
    es = esporta_xml(con_data(d, "2025-03-10"), contesto_caso_a10(data_riferimento=date(2025, 6, 1)))
    assert es.xml is None and any("pagamento rateale" in e.messaggio for e in es.errori)


# ---- controllo ufficiale locale ----------------------------------------------------------------------------------------------
@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
@pytest.mark.parametrize("nome,costruisci,data", [
    ("a10_2024", caso_a10, "2024-03-10"),
    ("a10_2016", caso_a10, "2016-03-10"),
    ("a10_2013", caso_a10, "2013-03-10"),
    ("minimo_fisso_2013", piccolo, "2013-03-10"),
    ("minimo_fisso_2024", piccolo, "2024-03-10"),
    ("soli_terreni_2022", lambda: solo_terreni("3000"), "2022-05-20"),
    ("soli_terreni_vf_2013", lambda: solo_terreni("100000"), "2013-05-20"),
    ("prima_casa_2013", caso_prima_casa, "2013-03-10"),
    ("prima_casa_2024", caso_prima_casa, "2024-03-10"),
])
@pytest.mark.java
def test_controllo_ufficiale_positivo(tmp_path, nome, costruisci, data):
    es = esporta_xml(con_data(costruisci(), data), contesto_caso_a10())
    assert es.completo
    stato, dgn, wri, _ = _esegui(es.xml, tmp_path)
    assert stato == "positivo", (dgn["diagnostici"], wri[:900])
    assert [x["codice"] for x in dgn["diagnostici"]] == ["3345"]       # solo l'avviso sull'attestazione


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
@pytest.mark.parametrize("codice", ["1", "2"])
@pytest.mark.parametrize("data", ["2013-03-10", "2020-03-10"])
@pytest.mark.java
def test_controllo_ufficiale_sostitutive_storiche(tmp_path, data, codice):
    d = con_data(piccolo(), data)
    d["opzioni"]["tipo_dichiarazione"] = "sostitutiva"
    d["opzioni"]["telematico"]["dichiarazione"].update(codice_sostitutiva=codice, prima_anno="2021", prima_volume="88888",
                                                       prima_numero="1", ipotecaria_versata="100", catastale_versata="50")
    es = esporta_xml(d, contesto_caso_a10())
    assert es.completo
    stato, dgn, wri, _ = _esegui(es.xml, tmp_path)
    assert stato == "positivo", (dgn["diagnostici"], wri[:900])


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
@pytest.mark.parametrize("data,da,a", [("2013-03-10", b">168<", b">200<"), ("2024-03-10", b">200<", b">168<")])
@pytest.mark.java
def test_controllo_ufficiale_respinge_la_misura_fissa_di_un_altro_periodo(tmp_path, data, da, a):
    es = esporta_xml(con_data(piccolo(), data), contesto_caso_a10())
    xml = es.xml.replace(da, a)
    assert xml != es.xml
    stato, dgn, _, _ = _esegui(xml, tmp_path, rapporto=False)
    assert stato == "negativo" and any(x["codice"] == "3076" for x in dgn["diagnostici"]), dgn["diagnostici"]


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
@pytest.mark.java
def test_controllo_ufficiale_respinge_il_totale_alterato(tmp_path):
    es = esporta_xml(con_data(piccolo(), "2016-03-10"), contesto_caso_a10())
    xml = es.xml.replace(b"605,00", b"600,00")
    assert xml != es.xml
    stato, dgn, _, _ = _esegui(xml, tmp_path, rapporto=False)
    assert stato == "negativo" and any(x["codice"] == "1012" for x in dgn["diagnostici"]), dgn["diagnostici"]
