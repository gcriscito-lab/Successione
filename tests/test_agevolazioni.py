"""Agevolazioni A, C, D, E, G, H, M, N (src/successioni/telematico/agevolazioni.py). Dati sintetici.

Regole dalle fonti: annotazioni XSD di Devoluzione/Agevolazioni e di QuadroEF/QuadroEE, Fascicolo I p. PDF 57 (quadro sinottico),
guida di calcolo p. 1 (QE senza i righi A, D, C, G, N, E, H). Ogni caso positivo e' stato accettato dal controllo ufficiale SUC13
2.3.1 eseguito in locale il 2026-11-05 (dati sintetici, nessun invio)."""
import copy
from datetime import date

import pytest
from lxml import etree

from telematico_casi import ALLEGATI_A10, caso_a10, caso_azienda, contesto, contesto_caso_a10
from successioni.telematico.esporta import esporta_xml
from successioni.telematico.identificativi import genera_cf_sintetico
from test_telematico_controllo import _esegui, _motivo_salto

SALTO = _motivo_salto()
D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"
EH_A = {"dichiara_requisiti": True, "a": {"num_protocollo": "1234567890", "data": "2026-01-10"}}
EH_FLAG = {"dichiara_requisiti": True}


def caso(codici, dich=None, modif=None):
    d = copy.deepcopy(caso_a10())
    tel = d["opzioni"]["telematico"]
    for did, c in codici.items():
        tel.setdefault("devoluzioni", {}).setdefault(did, {})["agevolazioni"] = c
    if dich:
        tel["dichiarazione"].update(dich)
    if modif:
        modif(d)
    return d


def altro(d):
    d["documenti_ref"].append({"id": "dr_altro01", "_origine": {}, "allegato_id": "al_testam", "tipo_eg": "Altro",
                               "finalita": "dichiarazione sostitutiva (sintetica)"})


def esporta(d, ctx=None, completo=True):
    es = esporta_xml(d, ctx or contesto_caso_a10())
    if completo:
        assert es.completo, [e.messaggio for e in es.errori] + es.non_supportato + [m.messaggio for m in es.quadri_mancanti]
    return es


def v(es, xp):
    doc = etree.fromstring(es.xml)
    return doc.xpath(xp, namespaces={k: x for k, x in doc.nsmap.items() if k})


def controllo_positivo(es, tmp_path):
    stato, dgn, wri, _ = _esegui(es.xml, tmp_path)
    assert stato == "positivo", (dgn["diagnostici"], wri[:900])
    assert [x["codice"] for x in dgn["diagnostici"]] == ["3345"]       # solo l'avviso sull'attestazione


def errori(es):
    return {(e.codice, e.percorso) for e in es.errori}


# ------------------------------------------------------------------------------------------------------------- EF / EE
def test_n_resta_nella_base_proporzionale():
    es = esporta(caso({"d_terranna": "N", "d_terrluca": "N"}))
    assert v(es, f"{D}/suc:QuadroEF/suc:SezioneI_ImpostaIpotecaria/suc:ImpostaProporzionale/*/text()") == ["141000", "2820"]
    assert v(es, f"{D}/suc:QuadroEF/suc:TotaleDaVersare/text()") == ["4435,00"]


def test_m_blocco_ef3_e_imposta_fissa():
    es = esporta(caso({"d_terranna": "M"}))             # l'agevolazione si estende all'intero bene (annotazione AgevolazioneM_Valore)
    ef = f"{D}/suc:QuadroEF"
    assert v(es, f"{ef}/suc:SezioneI_ImpostaIpotecaria/suc:AgevolazioneM/*/text()") == ["15000", "200"]
    assert v(es, f"{ef}/suc:SezioneI_ImpostaIpotecaria/suc:ImpostaProporzionale/*/text()") == ["126000", "2520"]
    assert v(es, f"{ef}/suc:SezioneI_ImpostaIpotecaria/suc:ImpostaIpotecariaDovuta/text()") == ["2720"]
    assert v(es, f"{ef}/suc:SezioneII_ImpostaCatastale/suc:ImpostaProporzionale/*/text()") == ["126000", "1260"]   # catastale esente
    assert v(es, f"{ef}/suc:TotaleDaVersare/text()") == ["4185,00"]


def test_a_esclusa_da_ee_e_richiesta_nel_quadro_eh():
    es = esporta(caso({"d_terranna": "A"}, {"riduzioni_art25": EH_A}))
    assert v(es, f"{D}/suc:QuadroEE/suc:TotaleValoreImmobili/text()") == ["126000"]            # 141000 - 15000
    assert v(es, f"{D}/suc:QuadroEF/suc:SezioneI_ImpostaIpotecaria/suc:ImpostaProporzionale/*/text()") == ["141000", "2820"]
    a = f"{D}/suc:QuadroEH/suc:PrimoModulo/suc:SezioneIV_AltreAgevRiduz/suc:EsenzioneImpostaSuccessione/suc:AgevolazTipoA"
    assert v(es, f"{a}/suc:FlagA/text()") == ["1"] and v(es, f"{a}/suc:NumProtocollo/text()") == ["1234567890"]


@pytest.mark.parametrize("codice,imponibile", [("C", "133500"), ("E", "133500")])
def test_c_e_esenti_da_ipotecaria_e_catastale(codice, imponibile):
    es = esporta(caso({"d_terranna": codice}, {"riduzioni_art25": EH_FLAG}))
    assert v(es, f"{D}/suc:QuadroEF/suc:SezioneI_ImpostaIpotecaria/suc:ImpostaProporzionale/*/text()")[0] == imponibile
    assert v(es, f"{D}/suc:QuadroEF/suc:SezioneII_ImpostaCatastale/suc:ImpostaProporzionale/*/text()")[0] == imponibile
    flag = f"{D}/suc:QuadroEH/suc:PrimoModulo/suc:SezioneIV_AltreAgevRiduz/suc:Agevolazioni/suc:Flag{codice}/text()"
    assert v(es, flag) == ["1"]


def test_d_su_fabbricato_esente():
    es = esporta(caso({"d_casaanna": "D"}, {"riduzioni_art25": EH_FLAG}))
    assert v(es, f"{D}/suc:QuadroEF/suc:SezioneI_ImpostaIpotecaria/suc:ImpostaProporzionale/*/text()")[0] == "78000"   # 141000 - 63000


def test_h_esente_e_richiede_il_documento_nel_quadro_eg():
    es = esporta(caso({"d_casaanna": "H"}, modif=altro))
    assert v(es, f"{D}/suc:QuadroEF/suc:SezioneI_ImpostaIpotecaria/suc:ImpostaProporzionale/*/text()")[0] == "78000"
    es = esporta(caso({"d_casaanna": "H"}), completo=False)                         # senza il rigo EG8 «Altro»
    assert not es.completo and any(m.percorso == "quadro[EG].Altro" for m in es.quadri_mancanti)


def test_g_solo_in_en_e_sotto_i_40_anni():
    cf = genera_cf_sintetico("Rossi", "Anna", "F", "1995-05-05", "H501")

    def giovane(d):
        for p in d["persone"]:
            if p["id"] == "p_anna0001":
                p["data_nascita"], p["codice_fiscale"] = "1995-05-05", cf
        d["opzioni"]["telematico"]["dichiarazione"]["versamento"]["cf_titolare"] = cf
        d["opzioni"]["telematico"].setdefault("devoluzioni", {})["d_azienanna"] = {"agevolazioni": "G"}
    d = copy.deepcopy(caso_azienda())
    giovane(d)
    assert esporta(d, contesto(allegati=ALLEGATI_A10, cf_fornitore=cf)).completo
    d = copy.deepcopy(caso_azienda())                                                # Anna ha 55 anni al decesso
    d["opzioni"]["telematico"].setdefault("devoluzioni", {})["d_azienanna"] = {"agevolazioni": "G"}
    es = esporta(d, completo=False)
    assert es.xml is None and ("REGOLA_AGEVOLAZIONE_G_ETA", "devoluzioni[d_azienanna].agevolazioni") in errori(es)
    es = esporta(caso({"d_terranna": "G"}), completo=False)                          # G su terreni: richiede il bene aziendale
    assert es.xml is None and any("agevolazioni=G nel quadro EB: non supportato" in s for s in es.non_supportato)


# ------------------------------------------------------------------------------------------------ regole dell'XSD
def test_richiesta_di_altro_beneficiario_richiede_l_allegato_eg():
    es = esporta(caso({"d_terrluca": "A"}), completo=False)                          # Luca non e' il dichiarante
    assert any(m.percorso == "quadro[EG].RiduzioniImposteSuccessione" for m in es.quadri_mancanti)
    es = esporta(caso({"d_terrluca": "C"}), completo=False)
    assert any(m.percorso == "quadro[EG].AgevolazioniImposteIpocatastali" for m in es.quadri_mancanti)


def test_dati_della_sezione_iv_obbligatori_per_il_dichiarante():
    es = esporta(caso({"d_terranna": "A"}), completo=False)
    assert ("DATO_MANCANTE", "opzioni.telematico.dichiarazione.riduzioni_art25") in errori(es)


def test_una_sola_tipologia_esclusiva_per_bene():
    es = esporta(caso({"d_terranna": "M", "d_terrluca": "N"}), completo=False)
    assert any(c == "REGOLA_AGEVOLAZIONE_ESCLUSIVA" for c, _ in errori(es))


def test_quadro_e_grado_non_ammessi():
    es = esporta(caso({"d_terranna": "H"}), completo=False)                          # H: solo EC ed EM
    assert ("REGOLA_AGEVOLAZIONE_QUADRO", "devoluzioni[d_terranna].agevolazioni") in errori(es)

    def fratelli(d):
        for p in d["persone"]:
            if p["id"] in ("p_anna0001", "p_luca0001"):
                p["relazione_con_defunto"] = "10"
                d["opzioni"]["telematico"]["persone"][p["id"]]["grado_parentela"] = "10"
    es = esporta(caso({"d_terranna": "N"}, modif=fratelli), completo=False)         # N non spetta ai fratelli
    assert ("REGOLA_AGEVOLAZIONE_GRADO", "devoluzioni[d_terranna].agevolazioni") in errori(es)


# --------------------------------------------------------------------------- imposta di successione (guida p. 1)
def con_imposta(codici, dich=None):
    d = caso(codici, dich)
    d["beni"][2]["valore"] = "2400000"       # conto
    d["beni"][1]["valore"] = "1000000"       # terreno
    d["opzioni"]["telematico"]["dichiarazione"]["tempistica_pagamento"] = "2"
    return d


def imposta(es):
    return int(v(es, f"{D}/suc:QuadroEF/suc:SezioneVBis_ImpostaSuccessione/suc:ImpostaCalcolata/suc:Imposta/text()")[0])


CTX = dict(data_riferimento=date(2026, 3, 9))


@pytest.mark.parametrize("codici,atteso", [
    ({}, 65736),                                                        # nessuna agevolazione
    ({"d_terranna": "N", "d_terrluca": "N"}, 21736),                    # S esente: 1.000.000 escluso dalle quote
    ({"d_terranna": "M", "d_terrluca": "M"}, 65736),                    # M: S dovuta
])
def test_l_imposta_di_successione_esclude_i_righi_esenti(codici, atteso):
    es = esporta(con_imposta(codici), contesto_caso_a10(**CTX))
    assert imposta(es) == atteso


def test_l_esenzione_riguarda_solo_la_quota_che_la_richiede():
    es = esporta(con_imposta({"d_terranna": "C"}, {"riduzioni_art25": EH_FLAG}), contesto_caso_a10(**CTX))
    assert imposta(es) == 43736


# ------------------------------------------------------------------------ controllo ufficiale locale (SUC13 2.3.1)
@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
@pytest.mark.parametrize("nome,costruisci", [
    ("n", lambda: caso({"d_terranna": "N", "d_terrluca": "N"})),
    ("m", lambda: caso({"d_terranna": "M"})),
    ("a", lambda: caso({"d_terranna": "A"}, {"riduzioni_art25": EH_A})),
    ("c", lambda: caso({"d_terranna": "C"}, {"riduzioni_art25": EH_FLAG})),
    ("e", lambda: caso({"d_terranna": "E"}, {"riduzioni_art25": EH_FLAG})),
    ("d_fabbricato", lambda: caso({"d_casaanna": "D"}, {"riduzioni_art25": EH_FLAG})),
    ("h", lambda: caso({"d_casaanna": "H"}, modif=altro)),
    ("h_entrambi", lambda: caso({"d_casaanna": "H", "d_casaluca": "H"}, modif=altro)),
    ("n_con_imposta", lambda: con_imposta({"d_terranna": "N", "d_terrluca": "N"})),
    ("c_con_imposta", lambda: con_imposta({"d_terranna": "C"}, {"riduzioni_art25": EH_FLAG})),
    ("m_con_imposta", lambda: con_imposta({"d_terranna": "M", "d_terrluca": "M"})),
])
@pytest.mark.java
def test_controllo_ufficiale_accetta(tmp_path, nome, costruisci):
    ctx = contesto_caso_a10(**CTX) if nome.endswith("imposta") else None
    controllo_positivo(esporta(costruisci(), ctx), tmp_path)


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
@pytest.mark.java
def test_controllo_ufficiale_g_ed_d_in_en(tmp_path):
    cf = genera_cf_sintetico("Rossi", "Anna", "F", "1995-05-05", "H501")
    for cod in ("G", "D"):
        d = copy.deepcopy(caso_azienda())
        for p in d["persone"]:
            if p["id"] == "p_anna0001":
                p["data_nascita"], p["codice_fiscale"] = "1995-05-05", cf
        d["opzioni"]["telematico"]["dichiarazione"]["versamento"]["cf_titolare"] = cf
        d["opzioni"]["telematico"].setdefault("devoluzioni", {})["d_azienanna"] = {"agevolazioni": cod}
        if cod == "D":
            d["opzioni"]["telematico"]["dichiarazione"]["riduzioni_art25"] = EH_FLAG
        controllo_positivo(esporta(d, contesto(allegati=ALLEGATI_A10, cf_fornitore=cf)), tmp_path / cod)


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
@pytest.mark.java
def test_controllo_ufficiale_respinge_una_base_sbagliata(tmp_path):
    es = esporta(caso({"d_terranna": "C"}, {"riduzioni_art25": EH_FLAG}))
    sbagliato = es.xml.replace(b">133500<", b">141000<")           # il rigo C rimesso nella base proporzionale
    assert sbagliato != es.xml
    stato, dgn, _, _ = _esegui(sbagliato, tmp_path, rapporto=False)
    assert stato == "negativo" and any(x["gravita"] == 16 for x in dgn["diagnostici"]), dgn["diagnostici"]   # errore bloccante
