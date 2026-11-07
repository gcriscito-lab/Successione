"""Pagamenti: crediti d'imposta (EF7, EF13, EF18bis col. 4, EH sezione III), rimborsi nelle sostitutive e sanzioni/interessi dichiarati
dal professionista (EF, Sezione VI) con le dichiarazioni tardive (src/successioni/telematico/pagamenti.py, quadri_efgh.py).

Regole dalle fonti: XSD (annotazioni di CreditoImposta, SezioneVI_SanzioniInteressi, SezioneIII_CreditoImposta, ImportoDaVersare) e
Fascicolo I pp. PDF 41-44, 47-49. Ogni caso positivo e' stato accettato dal controllo ufficiale SUC13 2.3.1 eseguito in locale il
2026-11-06 (dati sintetici, nessun invio); le alterazioni sono respinte."""
import copy
import datetime

import pytest
from lxml import etree

from telematico_casi import caso_a10, contesto_caso_a10
from successioni.telematico.esporta import esporta_xml
from test_telematico_controllo import _esegui, _motivo_salto

SALTO = _motivo_salto()
D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"
ACQ = {"ufficio_registrazione": "795", "serie": "1T", "numero_registrazione": "555", "data_registrazione": "2024-02-10"}
ACQ2 = {"ufficio_registrazione": "795", "serie": "1T", "numero_registrazione": "556", "data_registrazione": "2025-08-01"}
VEN = {"ufficio_registrazione": "795", "serie": "1T", "numero_registrazione": "777", "data_registrazione": "2025-06-10"}
TEMPESTIVO = datetime.date(2026, 3, 9)
CREDITO_REGISTRO = dict(credito_tipologia="1", credito_imposta="6000", credito_acquisto=ACQ, credito_tipologia_2="1",
                        credito_imposta_2="6200", credito_acquisto_2=ACQ2)


def caso(altro=True, **dich):
    d = copy.deepcopy(caso_a10())
    if altro:       # rigo EG8 «Altro»: dichiarazione sostitutiva con i requisiti del credito
        d["documenti_ref"].append({"id": "dr_altro01", "_origine": {}, "allegato_id": "al_testam", "tipo_eg": "Altro", "finalita": "dsan"})
    d["opzioni"]["telematico"]["dichiarazione"].update(dich)
    return d


def caso_grosso(data_decesso="2025-03-10", **dich):
    """Conto da 2.400.000 euro: imposta di successione dovuta (22.396 euro)."""
    d = caso(**dich)
    d["beni"][2]["valore"] = "2400000"
    d["persone"][0]["data_decesso"] = data_decesso
    return d


def sostitutiva(d, **dich):
    d["opzioni"]["tipo_dichiarazione"] = "sostitutiva"
    d["opzioni"]["telematico"]["dichiarazione"].update(codice_sostitutiva="2", prima_anno="2026", prima_volume="88888",
                                                         prima_numero="1", **dich)
    d["opzioni"]["telematico"]["dichiarazione"].pop("versamento", None)
    return d


def esporta(d, completo=True, **ctx):
    es = esporta_xml(d, contesto_caso_a10(**ctx))
    if completo:
        assert es.completo, [e.messaggio for e in es.errori] + es.non_supportato + [m.messaggio for m in es.quadri_mancanti]
    return es


def xp(es, percorso):
    doc = etree.fromstring(es.xml)
    return doc.xpath(f"{D}/{percorso}/text()", namespaces={k: v for k, v in doc.nsmap.items() if k})


def codici(es):
    return {(e.codice, e.percorso.rsplit(".", 1)[-1]) for e in es.errori}


def alterato(es, percorso, valore=None, rimuovi=False) -> bytes:
    doc = etree.fromstring(es.xml)
    ns = {k: v for k, v in doc.nsmap.items() if k}
    for e in doc.xpath(f"{D}/{percorso}", namespaces=ns)[:1]:
        if rimuovi:
            e.getparent().remove(e)
        else:
            e.text = valore
    return etree.tostring(doc, xml_declaration=True, encoding="UTF-8")


def positivo(xml, tmp_path):
    stato, dgn, wri, _ = _esegui(xml, tmp_path)
    assert stato == "positivo", (dgn["diagnostici"], wri[:900])
    assert [x["codice"] for x in dgn["diagnostici"]] == ["3345"]      # solo l'avviso sull'attestazione


def negativo(xml, tmp_path):
    stato, dgn, _, _ = _esegui(xml, tmp_path, rapporto=False)
    assert stato == "negativo", dgn["diagnostici"]
    return {x["codice"] for x in dgn["diagnostici"]}


# =================================================================================================== crediti d'imposta
def test_credito_su_imposta_ipotecaria():
    es = esporta(caso(credito_ipotecaria="1000", credito_vendita=VEN, **CREDITO_REGISTRO))
    s1 = "suc:QuadroEF/suc:SezioneI_ImpostaIpotecaria"
    assert xp(es, f"{s1}/suc:ImpostaIpotecariaDovuta") == ["2820"] and xp(es, f"{s1}/suc:CreditoImposta") == ["1000"]
    assert xp(es, f"{s1}/suc:ImpostaIpotecariaDaVersare") == ["1820"]           # EF8 = EF5 - EF6 - EF7
    assert xp(es, "suc:QuadroEF/suc:TotaleDaVersare") == ["3435,00"]            # 1820 + 1410 + 120 + 85
    # sezione III di EH: primo rigo nel primo modulo (con firma), secondo nel modulo successivo (tipologia 1: almeno due righi)
    eh = "suc:QuadroEH/suc:PrimoModulo/suc:SezioneIII_CreditoImposta"
    assert xp(es, f"{eh}/suc:TipologiaImposta") == ["1"] and xp(es, f"{eh}/suc:Imposta") == ["6000"]
    assert xp(es, "suc:QuadroEH/suc:Modulo/suc:SezioneIII_CreditoImposta/suc:Imposta") == ["6200"]


def test_credito_oltre_l_ipotecaria_passa_alla_catastale():
    es = esporta(caso(credito_ipotecaria="2820", credito_catastale="400", **CREDITO_REGISTRO))
    assert xp(es, "suc:QuadroEF/suc:SezioneI_ImpostaIpotecaria/suc:ImpostaIpotecariaDaVersare") == []     # EF8 = 0
    assert xp(es, "suc:QuadroEF/suc:SezioneII_ImpostaCatastale/suc:CreditoImposta") == ["400"]
    assert xp(es, "suc:QuadroEF/suc:SezioneII_ImpostaCatastale/suc:ImpostaCatastaleDaVersare") == ["1010"]
    assert xp(es, "suc:QuadroEF/suc:TotaleDaVersare") == ["1215,00"]                                      # 1010 + 120 + 85


def test_credito_che_azzera_ipotecaria_e_catastale():
    es = esporta(caso(credito_ipotecaria="2820", credito_catastale="1410", **CREDITO_REGISTRO))
    assert xp(es, "suc:QuadroEF/suc:TotaleDaVersare") == ["205,00"]                                      # solo EF15 + EF16


def test_credito_tipologia_3_ha_un_solo_rigo():
    es = esporta(caso(credito_ipotecaria="1000", credito_imposta="5000", credito_tipologia="3", credito_acquisto=ACQ))
    assert xp(es, "suc:QuadroEH/suc:PrimoModulo/suc:SezioneIII_CreditoImposta/suc:TipologiaImposta") == ["3"]
    assert xp(es, "suc:QuadroEH/suc:Modulo/suc:SezioneIII_CreditoImposta") == []


def test_credito_sull_imposta_di_successione():
    es = esporta(caso_grosso(tempistica_pagamento="2", credito_ipotecaria="2820", credito_catastale="1410", credito_successione="1000",
                             **CREDITO_REGISTRO), data_riferimento=TEMPESTIVO)
    ic = "suc:QuadroEF/suc:SezioneVBis_ImpostaSuccessione/suc:ImpostaCalcolata"
    assert xp(es, f"{ic}/suc:Imposta") == ["22396"] and xp(es, f"{ic}/suc:CreditoImposta") == ["1000"]
    assert xp(es, f"{ic}/suc:ImpostaDaVersare") == ["21396"]                                             # EF18bis col. 5
    assert xp(es, "suc:QuadroEF/suc:TotaleDaVersare") == ["21601,00"]                                    # 21396 + 120 + 85


@pytest.mark.parametrize("dich,atteso", [
    (dict(credito_ipotecaria="1000"), ("DATO_MANCANTE", "credito_tipologia")),
    (dict(credito_ipotecaria="1000", credito_tipologia="1", credito_imposta="6000", credito_acquisto=ACQ),
     ("DATO_MANCANTE", "credito_tipologia_2")),                                      # tipologia 1 o 2: due righi (messaggio 3386)
    (dict(credito_ipotecaria="1000", credito_tipologia="4", credito_acquisto=ACQ), ("VALORE_NON_VALIDO", "credito_tipologia")),
    (dict(credito_ipotecaria="1000", credito_tipologia="3", credito_imposta="5000"), ("DATO_MANCANTE", "credito_acquisto")),
    (dict(credito_ipotecaria="1000", **{**CREDITO_REGISTRO, "credito_tipologia_2": "3"}), ("VALORE_NON_VALIDO", "credito_tipologia_2")),
    (dict(credito_ipotecaria="7000", **CREDITO_REGISTRO), ("VALORE_NON_VALIDO", "credito_imposta")),     # oltre la minore delle imposte
    (dict(credito_ipotecaria="1.5", credito_tipologia="3", credito_acquisto=ACQ), ("VALORE_NON_VALIDO", "credito_ipotecaria")),
    (dict(credito_catastale="100", **CREDITO_REGISTRO), ("DATI_INCOERENTI", "credito_ipotecaria")),      # EH III richiede EF7
    (dict(credito_ipotecaria="1000", credito_catastale="100", **CREDITO_REGISTRO), ("DATI_INCOERENTI", "credito_catastale")),
    (dict(credito_ipotecaria="2820", credito_catastale="1500", **CREDITO_REGISTRO), ("DATI_INCOERENTI", "credito_catastale")),
    (dict(credito_ipotecaria="1000", **{**CREDITO_REGISTRO, "credito_vendita": {**VEN, "data_registrazione": "2024-01-01"}}),
     ("DATI_INCOERENTI", "data_registrazione")),                                      # vendita anteriore all'acquisto
])
def test_dati_del_credito_non_validi(dich, atteso):
    es = esporta(caso(**dich), completo=False)
    assert es.xml is None and atteso in codici(es), codici(es)


def test_credito_sulla_successione_solo_dopo_aver_azzerato_la_catastale():
    es = esporta(caso_grosso(tempistica_pagamento="2", credito_ipotecaria="2820", credito_successione="1000", **CREDITO_REGISTRO),
                 completo=False, data_riferimento=TEMPESTIVO)
    assert es.xml is None and ("DATI_INCOERENTI", "credito_successione") in codici(es)


def test_credito_sulla_successione_prima_del_2025_non_esiste():
    d = caso(credito_ipotecaria="1000", credito_successione="500", **CREDITO_REGISTRO)
    d["persone"][0]["data_decesso"] = "2024-03-10"
    es = esporta(d, completo=False)
    assert es.xml is None and ("DATI_INCOERENTI", "credito_successione") in codici(es)


def test_credito_richiede_la_dichiarazione_sostitutiva_nel_rigo_eg8():
    es = esporta(caso(altro=False, credito_ipotecaria="1000", **CREDITO_REGISTRO), completo=False)
    assert es.xml is None and any(m.percorso == "quadro[EG].Altro" for m in es.quadri_mancanti)


# ============================================================================================ sanzioni e interessi (Sezione VI)
def test_sezione_vi_e_importo_da_versare():
    d = caso(sanzione_ipotecaria="150.50", interessi_ipotecaria="20.10", sanzione_catastale="75.25", interessi_catastale="10.05")
    d["persone"][0]["data_decesso"] = "2024-03-10"                      # prima del 2025: nessuna V-bis, imposte ipocatastali tardive
    es = esporta(d)
    vi = "suc:QuadroEF/suc:SezioneVI_SanzioniInteressi"
    assert xp(es, f"{vi}/suc:ImpostaIpotecaria/*") == ["150,50", "20,10"]
    assert xp(es, f"{vi}/suc:TotaleDaVersare/*") == ["225,75", "30,15"]               # EF24 col. 1 e 2
    assert xp(es, "suc:QuadroEF/suc:TotaleDaVersare") == ["4435,00"]                  # EF19: solo i tributi
    assert xp(es, "suc:Frontespizio/suc:ImportoDaVersare") == ["4690,90"]             # EF19 + EF24 col. 1 + col. 2
    assert "EF_TARDIVA_SANZIONI_NON_CALCOLATE" not in {a.codice for a in es.avvisi}   # i dati sono dichiarati: niente avviso


def test_sanzioni_su_tassa_ipotecaria_e_bollo():
    es = esporta(caso(sanzione_tassa_ipotecaria="10.00", interessi_bollo="1.50"))
    vi = "suc:QuadroEF/suc:SezioneVI_SanzioniInteressi"
    assert xp(es, f"{vi}/suc:TassaIpotecaria/*") == ["10,00"] and xp(es, f"{vi}/suc:ImpostaBollo/*") == ["1,50"]
    assert xp(es, f"{vi}/suc:TotaleDaVersare/*") == ["10,00", "1,50"]


@pytest.mark.parametrize("dich", [dict(sanzione_ipotecaria="-1"), dict(interessi_catastale="1.234"), dict(sanzione_bollo="abc")])
def test_importi_di_sanzioni_non_validi(dich):
    es = esporta(caso(**dich), completo=False)
    assert es.xml is None and any(c == "VALORE_NON_VALIDO" for c, _ in codici(es))


def test_sanzioni_senza_il_relativo_importo_da_versare():
    es = esporta(caso(sanzione_successione="100"), completo=False)           # imposta di successione non dovuta
    assert es.xml is None and ("DATI_INCOERENTI", "sanzione_successione") in codici(es)


# ------------------------------------------------------------------------------------------------ dichiarazioni tardive
def test_tardiva_con_imposta_di_successione_e_sanzioni_dichiarate():
    es = esporta(caso_grosso(tempistica_pagamento="2", sanzione_successione="500.00", interessi_successione="40.00",
                             sanzione_ipotecaria="150.50", interessi_ipotecaria="20.10"))
    vi = "suc:QuadroEF/suc:SezioneVI_SanzioniInteressi"
    assert xp(es, f"{vi}/suc:ImpostaSuccessione/*") == ["500,00", "40,00"]
    assert xp(es, f"{vi}/suc:TotaleDaVersare/*") == ["650,50", "60,10"]
    assert xp(es, "suc:QuadroEF/suc:TotaleDaVersare") == ["26831,00"]                 # 22396 + 2820 + 1410 + 120 + 85
    assert xp(es, "suc:Frontespizio/suc:ImportoDaVersare") == ["27541,60"]            # + 650,50 + 60,10


def test_tardiva_con_sanzione_nulla_dichiarata_e_ammessa():
    es = esporta(caso_grosso(tempistica_pagamento="2", sanzione_successione="0", interessi_successione="0"))
    assert xp(es, "suc:QuadroEF/suc:SezioneVI_SanzioniInteressi/suc:ImpostaSuccessione/*") == ["0,00", "0,00"]


def test_tardiva_senza_importi_resta_bloccata():
    es = esporta(caso_grosso(tempistica_pagamento="2"), completo=False)
    assert es.xml is None and any("sanzione_successione" in m.messaggio for m in es.quadri_mancanti)


def test_tardiva_entro_i_90_giorni_con_tempistica_1_senza_sanzioni():
    # Fascicolo I p. PDF 48: codice 1 ammesso se si presenta entro i 90 giorni dal termine; l'imposta si paga nei termini
    es = esporta(caso_grosso(tempistica_pagamento="1"), data_riferimento=datetime.date(2026, 4, 1))
    assert xp(es, "suc:QuadroEF/suc:SezioneVBis_ImpostaSuccessione/suc:ImpostaCalcolata/suc:TempisticaPagamento") == ["1"]


def test_tardiva_oltre_i_90_giorni_richiede_il_pagamento_contestuale():
    es = esporta(caso_grosso(tempistica_pagamento="1", sanzione_successione="500.00"), completo=False)
    assert es.xml is None and ("DATI_INCOERENTI", "tempistica_pagamento") in codici(es)
    assert not any(c == "DATI_INCOERENTI" and p == "sanzione_successione" for c, p in codici(es))      # niente errore a cascata


# ==================================================================================== imposta gia' versata superiore al dovuto
def test_imposta_di_successione_versata_oltre_il_riliquidato():
    d = sostitutiva(caso_grosso(tempistica_pagamento="2", successione_versata="30000", ipotecaria_versata="2820", catastale_versata="1410"))
    es = esporta(d, data_riferimento=datetime.date(2026, 3, 1))
    ic = "suc:QuadroEF/suc:SezioneVBis_ImpostaSuccessione/suc:ImpostaCalcolata"
    assert xp(es, f"{ic}/suc:ImpostaVersata") == ["22396"] and xp(es, f"{ic}/suc:ImpostaDaVersare") == []      # tetto: l'imposta calcolata
    assert "ECCEDENZA_IMPOSTA_VERSATA_DA_RIMBORSARE" in {a.codice for a in es.avvisi}
    assert any("7604" in a.messaggio for a in es.avvisi)                                                         # 30000 - 22396


def test_imposta_ipotecaria_versata_oltre_la_dovuta():
    es = esporta(sostitutiva(caso(ipotecaria_versata="3000", catastale_versata="1410")))
    assert xp(es, "suc:QuadroEF/suc:SezioneI_ImpostaIpotecaria/suc:ImpostaIpotecariaVersata") == ["3000"]
    assert xp(es, "suc:QuadroEF/suc:SezioneI_ImpostaIpotecaria/suc:ImpostaIpotecariaDaVersare") == []
    assert any(a.codice == "ECCEDENZA_IMPOSTA_VERSATA_DA_RIMBORSARE" and "180" in a.messaggio for a in es.avvisi)


# ===================================================================================== controllo ufficiale SUC13 locale
@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
@pytest.mark.parametrize("nome,costruisci", [
    ("credito_ef7_con_vendita", lambda: (caso(credito_ipotecaria="1000", credito_vendita=VEN, **CREDITO_REGISTRO), {})),
    ("credito_ef7_ef13", lambda: (caso(credito_ipotecaria="2820", credito_catastale="400", **{**CREDITO_REGISTRO, "credito_tipologia": "2",
                                                                                              "credito_tipologia_2": "2"}), {})),
    ("credito_azzera_ipocatastali", lambda: (caso(credito_ipotecaria="2820", credito_catastale="1410", **CREDITO_REGISTRO), {})),
    ("credito_tipologia_3", lambda: (caso(credito_ipotecaria="1000", credito_imposta="5000", credito_tipologia="3", credito_acquisto=ACQ), {})),
    ("credito_su_successione", lambda: (caso_grosso(tempistica_pagamento="2", credito_ipotecaria="2820", credito_catastale="1410",
                                                    credito_successione="1000", **CREDITO_REGISTRO), {"data_riferimento": TEMPESTIVO})),
    ("sanzioni_ipocatastali_2024", lambda: (_d2024(sanzione_ipotecaria="150.50", interessi_ipotecaria="20.10", sanzione_catastale="75.25",
                                                   interessi_catastale="10.05"), {})),
    ("tardiva_con_successione", lambda: (caso_grosso(tempistica_pagamento="2", sanzione_successione="500.00", interessi_successione="40.00",
                                                     sanzione_ipotecaria="150.50", interessi_ipotecaria="20.10"), {})),
    ("tardiva_entro_90_giorni", lambda: (caso_grosso(tempistica_pagamento="1"), {"data_riferimento": datetime.date(2026, 4, 1)})),
    ("sanzioni_tassa_e_bollo", lambda: (caso(sanzione_tassa_ipotecaria="10.00", interessi_bollo="1.50"), {})),
    ("successione_versata_oltre", lambda: (sostitutiva(caso_grosso(tempistica_pagamento="2", successione_versata="30000",
                                                                    ipotecaria_versata="2820", catastale_versata="1410")),
                                           {"data_riferimento": datetime.date(2026, 3, 1)})),
    ("ipotecaria_versata_oltre", lambda: (sostitutiva(caso(ipotecaria_versata="3000", catastale_versata="1410")), {})),
])
@pytest.mark.java
def test_controllo_ufficiale_locale_positivo(tmp_path, nome, costruisci):
    d, ctx = costruisci()
    es = esporta(d, **ctx)
    positivo(es.xml, tmp_path)


def _d2024(**dich):
    d = caso(**dich)
    d["persone"][0]["data_decesso"] = "2024-03-10"
    return d


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
@pytest.mark.java
def test_controllo_respinge_il_credito_non_scalato_dall_imposta(tmp_path):
    es = esporta(caso(credito_ipotecaria="1000", **CREDITO_REGISTRO))
    positivo(es.xml, tmp_path / "ok")
    # EF7 ridotto a 900 lasciando EF8 a 1820 (= 2820 - 1000): i righi non quadrano piu'
    negativo(alterato(es, "suc:QuadroEF/suc:SezioneI_ImpostaIpotecaria/suc:CreditoImposta", "900"), tmp_path / "ko")


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
@pytest.mark.java
def test_controllo_respinge_un_solo_rigo_di_acquisto_con_tipologia_1(tmp_path):
    es = esporta(caso(credito_ipotecaria="1000", **CREDITO_REGISTRO))
    codici_diag = negativo(alterato(es, "suc:QuadroEH/suc:Modulo/suc:SezioneIII_CreditoImposta", rimuovi=True), tmp_path)
    assert "3386" in codici_diag                       # «almeno 2 righi di acquisti»: e' il motivo del secondo rigo nel modello


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
@pytest.mark.java
def test_controllo_respinge_importo_da_versare_senza_sanzioni(tmp_path):
    es = esporta(_d2024(sanzione_ipotecaria="150.50", interessi_ipotecaria="20.10"))
    positivo(es.xml, tmp_path / "ok")
    codici_diag = negativo(alterato(es, "suc:Frontespizio/suc:ImportoDaVersare", "4435,00"), tmp_path / "ko")    # senza EF24
    assert "3376" in codici_diag


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
@pytest.mark.java
def test_controllo_respinge_totale_sanzioni_alterato(tmp_path):
    es = esporta(_d2024(sanzione_ipotecaria="150.50", sanzione_catastale="75.25"))
    negativo(alterato(es, "suc:QuadroEF/suc:SezioneVI_SanzioniInteressi/suc:TotaleDaVersare/suc:TotaleDaVersare_Sanzioni", "999,00"), tmp_path)
