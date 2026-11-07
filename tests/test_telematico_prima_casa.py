"""Agevolazione prima casa (codici P, X, Z; EH Sezione II; EF4): regole da ``docs/regole/prima_casa.md`` (fonti: annotazioni XSD
SUC13_20250702 e Fascicolo I). Casi positivi e negativi; il controllo SUC13 locale e' eseguito se configurato
(SUCCESSIONI_JAVA, SUCCESSIONI_CONTROLLI_SUC13), altrimenti le prove 'reale' sono saltate con il motivo. Dati SINTETICI."""
from __future__ import annotations

import copy
from datetime import date

import pytest
from lxml import etree

from successioni.telematico import importa
from successioni.telematico.calcolo import calcola_da_xml
from successioni.telematico.esporta import esporta_xml
from telematico_casi import (ALLEGATI_A10, FIXTURE, PRIMA_CASA_DICH, aggiungi_fabbricato, caso_prima_casa,
                             contesto)
from test_telematico_controllo import NS, _esegui, _motivo_salto

D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"
EF = D + "/suc:QuadroEF"
EH2 = D + "/suc:QuadroEH/suc:PrimoModulo/suc:SezioneII_AgevPrimaCasa"
ALLEGATI = {**ALLEGATI_A10,
            "al_prima": {"percorso": str(FIXTURE / "allegati" / "albero_genealogico.pdf"), "nome": "prima_casa.pdf"},
            "al_ident": {"percorso": str(FIXTURE / "allegati" / "albero_genealogico.pdf"), "nome": "identita.pdf"}}
CTX = contesto(allegati=ALLEGATI, data_riferimento=date(2025, 9, 1))
SALTO = pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")


def _es(d):
    return esporta_xml(d, CTX)


def _x(es, xp):
    return etree.fromstring(es.xml).xpath(xp, namespaces=NS)


def _tel(d):
    return d["opzioni"]["telematico"]


def _agev(d, did, codice):
    _tel(d).setdefault("devoluzioni", {})[did] = {"agevolazioni": codice}


def _senza_terreno(d):
    d["beni"] = [b for b in d["beni"] if b["id"] != "b_terr0001"]
    d["devoluzioni"] = [v for v in d["devoluzioni"] if v["bene_id"] != "b_terr0001"]
    _tel(d)["beni"].pop("b_terr0001")


def _con_documenti_luca(d):
    d["documenti_ref"] += [
        {"id": "dr_prima01", "_origine": {}, "allegato_id": "al_prima", "tipo_eg": "PrimaCasa",
         "finalita": "Richiesta prima casa (sintetica)"},
        {"id": "dr_ident01", "_origine": {}, "allegato_id": "al_ident", "tipo_eg": "DocumentiIdentita",
         "finalita": "Documento d'identita' (sintetico)"}]


def caso_p_x():
    d = caso_prima_casa()
    aggiungi_fabbricato(d, "b_garage01", "C/6", "10000", "7", anna="X")
    return d


def caso_p_z():
    d = caso_prima_casa()
    aggiungi_fabbricato(d, "b_casa0002", "A/3", "40000", "8", anna="Z")
    _tel(d)["dichiarazione"]["prima_casa"]["impegno_unione_catastale"] = True
    return d


def caso_p_altro_soggetto():
    """Anna (dichiarante) chiede P sulla casa 1; Luca chiede P su una seconda casa: richiesta EG9 + documento d'identita'."""
    d = caso_prima_casa()
    aggiungi_fabbricato(d, "b_casa0002", "A/3", "40000", "8", luca="P")
    _con_documenti_luca(d)
    return d


def caso_solo_prima_casa():
    d = caso_prima_casa()
    _senza_terreno(d)
    return d


def caso_luca_dichiarante_non_richiedente():
    """Solo Luca (non dichiarante) chiede P: nessuna Sezione II del quadro EH."""
    d = caso_prima_casa()
    _tel(d).pop("devoluzioni")
    _tel(d)["dichiarazione"].pop("prima_casa")
    _agev(d, "d_casaluca", "P")
    _con_documenti_luca(d)
    return d


# ------------------------------------------------------------------------------------------------ casi positivi
def test_p_ef4_e_sezione_ii():
    es = _es(caso_prima_casa())
    assert (es.errori, es.non_supportato, es.quadri_mancanti) == ([], [], []) and es.completo
    # codice P sulla sola riga della richiedente (l'agevolazione si estende all'altra riga senza codice)
    assert _x(es, D + "/suc:QuadroEC//suc:Devoluzione/suc:Agevolazioni/text()") == ["P"]
    s1 = EF + "/suc:SezioneI_ImpostaIpotecaria"
    assert _x(es, s1 + "/suc:PrimaCasa/*/text()") == ["1", "126000", "200"]          # EF4: numero, valore quote, 1 x 200
    assert _x(es, s1 + "/suc:ImpostaProporzionale/*/text()") == ["30000", "600"]     # EF1 solo sul terreno
    assert _x(es, s1 + "/suc:ImpostaIpotecariaDovuta/text()") == ["800"]             # EF5 = EF1 + EF4 col. 3
    s2 = EF + "/suc:SezioneII_ImpostaCatastale"
    assert _x(es, s2 + "/suc:ImpostaProporzionale/*/text()") == ["30000", "300"]
    assert _x(es, s2 + "/suc:ImpostaCatastaleFissa/text()") == ["200"]               # EF10 = EF4 col. 3
    assert _x(es, s2 + "/suc:ImpostaCatastaleDovuta/text()") == ["500"]
    assert _x(es, EF + "/suc:TotaleDaVersare/text()") == ["1505,00"]                 # 800 + 500 + 120 + 85
    assert _x(es, D + "/suc:Frontespizio/suc:ImportoDaVersare/text()") == ["1505,00"]
    # Sezione II del quadro EH: immobile principale uguale al rigo EC, dichiarazioni a, b, c
    assert _x(es, EH2 + "/suc:ImmobilePrincipale/suc:DatiCatastali/*/text()") == ["100", "200", "3"]
    assert _x(es, EH2 + "/suc:ImmobilePrincipale/suc:Luogo/suc:CodiceComune/text()") == ["H501"]
    assert _x(es, EH2 + "/suc:Opzioni/suc:FlagComuneResidenza/text()") == ["1"]
    assert _x(es, EH2 + "/suc:FlagNessunaAltraCasaComune/text()") == ["1"]
    assert _x(es, EH2 + "/suc:AltraCasa/suc:FlagNessunaAltraCasa/text()") == ["1"]
    assert _x(es, EH2 + "/suc:FirmaDichiarante/text()") == ["1"]
    assert _x(es, EH2 + "/suc:FlagContigui") == [] and _x(es, EH2 + "/suc:ImmobileContiguo") == []
    assert es.mappa["quadro:EF"]["calcoli"]["EF4"]["numero"] == 1
    assert "p. PDF 41" in es.mappa["quadro:EF"]["calcoli"]["EF4"]["fonte"]


def test_la_prima_casa_non_cambia_asse_ne_imposta_di_successione():
    # P non e' tra i codici che escludono quote dalla QE (guida p. 1) ne' tra le riduzioni (guida p. 5)
    senza = caso_prima_casa()
    _tel(senza).pop("devoluzioni")
    _tel(senza)["dichiarazione"].pop("prima_casa")
    a, b = _es(caso_prima_casa()), _es(senza)
    assert a.errori == [] and b.errori == []
    assert _x(a, D + "/suc:QuadroEE/*/text()") == _x(b, D + "/suc:QuadroEE/*/text()")
    ra, rb = calcola_da_xml(a.xml), calcola_da_xml(b.xml)
    assert ra.stato == rb.stato == "completato" and ra.imposta_ef18bis == rb.imposta_ef18bis


def test_senza_prima_casa_ef_invariato():
    d = caso_prima_casa()
    _tel(d).pop("devoluzioni")
    _tel(d)["dichiarazione"].pop("prima_casa")
    es = _es(d)
    assert es.errori == [] and _x(es, EF + "//suc:PrimaCasa") == [] and _x(es, EF + "//suc:ImpostaCatastaleFissa") == []
    assert _x(es, EF + "/suc:SezioneI_ImpostaIpotecaria/suc:ImpostaProporzionale/*/text()") == ["156000", "3120"]
    assert _x(es, EH2) == [] and "EF4" not in es.mappa["quadro:EF"]["calcoli"]


def test_p_con_pertinenza_x():
    es = _es(caso_p_x())
    assert (es.errori, es.non_supportato, es.quadri_mancanti) == ([], [], []) and es.completo
    # X non si conta nel numero degli immobili (EF4 col. 1 = 1), ma il suo valore e' nella colonna 2
    assert _x(es, EF + "/suc:SezioneI_ImpostaIpotecaria/suc:PrimaCasa/*/text()") == ["1", "136000", "200"]
    assert _x(es, EH2 + "/suc:Pertinenza/suc:DatiCatastali/reg:Subalterno/text()") == ["7"]
    assert _x(es, EF + "/suc:SezioneII_ImpostaCatastale/suc:ImpostaCatastaleFissa/text()") == ["200"]


def test_p_con_immobile_contiguo_z():
    es = _es(caso_p_z())
    assert (es.errori, es.non_supportato, es.quadri_mancanti) == ([], [], []) and es.completo
    # Z in presenza di P non si conta (annotazione PrimaCasa_Numero: Z solo in assenza di P)
    assert _x(es, EF + "/suc:SezioneI_ImpostaIpotecaria/suc:PrimaCasa/*/text()") == ["1", "166000", "200"]
    assert _x(es, EH2 + "/suc:ImmobileContiguo/suc:DatiCatastali/reg:Subalterno/text()") == ["8"]
    assert _x(es, EH2 + "/suc:FlagContigui/text()") == ["1"]


def test_p_di_un_beneficiario_diverso_dal_dichiarante():
    es = _es(caso_p_altro_soggetto())
    assert (es.errori, es.non_supportato, es.quadri_mancanti) == ([], [], []) and es.completo
    # due immobili con P (casa 1 della dichiarante, casa 2 di Luca): EF4 col. 1 = 2
    assert _x(es, EF + "/suc:SezioneI_ImpostaIpotecaria/suc:PrimaCasa/*/text()") == ["2", "166000", "400"]
    assert _x(es, EF + "/suc:SezioneII_ImpostaCatastale/suc:ImpostaCatastaleFissa/text()") == ["400"]
    assert _x(es, D + "/suc:QuadroEG/suc:PrimaCasa/suc:PrimaCasaNum/text()") == ["1"]
    # la Sezione II riguarda solo l'immobile del dichiarante
    assert _x(es, EH2 + "/suc:ImmobilePrincipale/suc:DatiCatastali/reg:Subalterno/text()") == ["3"]


def test_solo_beni_prima_casa_senza_ef1():
    es = _es(caso_solo_prima_casa())
    assert (es.errori, es.non_supportato, es.quadri_mancanti) == ([], [], []) and es.completo
    s1 = EF + "/suc:SezioneI_ImpostaIpotecaria"
    assert _x(es, s1 + "/suc:ImpostaProporzionale") == []
    assert _x(es, s1 + "/suc:ImpostaIpotecariaDovuta/text()") == ["200"]
    assert _x(es, EF + "/suc:SezioneII_ImpostaCatastale/suc:ImpostaCatastaleDovuta/text()") == ["200"]
    assert _x(es, EF + "/suc:TotaleDaVersare/text()") == ["605,00"]


def test_solo_un_beneficiario_non_dichiarante_senza_sezione_ii():
    es = _es(caso_luca_dichiarante_non_richiedente())
    assert (es.errori, es.non_supportato, es.quadri_mancanti) == ([], [], []) and es.completo
    assert _x(es, EH2) == [] and _x(es, D + "/suc:QuadroEG/suc:PrimaCasa") != []


# ------------------------------------------------------------------------------------------------ casi negativi
def _errori(es):
    return {(e.percorso, e.codice) for e in es.errori}


def _blocco(d):
    es = _es(d)
    assert es.xml is None
    return es


def test_categorie_escluse_a1_a8_a9():
    for cat in ("A/1", "A/8", "A/9"):
        d = caso_prima_casa()
        next(b for b in d["beni"] if b["id"] == "b_casa0001")["categoria"] = cat
        es = _blocco(d)
        assert ("devoluzioni[d_casaanna].agevolazioni", "REGOLA_PRIMA_CASA_CATEGORIA") in _errori(es), cat
        assert "p. PDF 60" in next(e.fonte for e in es.errori if e.codice == "REGOLA_PRIMA_CASA_CATEGORIA")


@pytest.mark.parametrize("cat", ["A/10", "A/11", "C/6", "D/1"])
def test_categorie_non_classificate_dalle_fonti_non_supportate(cat):
    d = caso_prima_casa()
    b = next(b for b in d["beni"] if b["id"] == "b_casa0001")
    b["categoria"] = cat
    if cat[0] in "CD":
        b["consistenza"] = None
        _tel(d)["beni"]["b_casa0001"].pop("consistenza")
        if cat[0] == "D":
            b.pop("rendita")
    es = _es(d)
    assert es.xml is None and any("non classificano questa categoria" in s for s in es.non_supportato), \
        (es.errori, es.non_supportato)


def test_x_su_categoria_non_pertinenziale():
    d = caso_prima_casa()
    aggiungi_fabbricato(d, "b_casa0002", "A/3", "40000", "8", anna="X")
    # X senza P dello stesso soggetto e' un secondo errore: qui interessa la categoria
    assert ("devoluzioni[d_casa0002_anna].agevolazioni", "REGOLA_PRIMA_CASA_CATEGORIA") in _errori(_blocco(d))


def test_x_senza_p_dello_stesso_soggetto():
    d = caso_prima_casa()
    _tel(d).pop("devoluzioni")
    _tel(d)["dichiarazione"].pop("prima_casa")
    aggiungi_fabbricato(d, "b_garage01", "C/6", "10000", "7", anna="X")
    assert ("persone[p_anna0001]", "REGOLA_PRIMA_CASA_X_SENZA_P") in _errori(_blocco(d))


def test_due_pertinenze_della_stessa_categoria():
    d = caso_p_x()
    aggiungi_fabbricato(d, "b_garage02", "C/6", "10000", "9", anna="X")
    assert ("persone[p_anna0001]", "REGOLA_PRIMA_CASA_X_CATEGORIA") in _errori(_blocco(d))


def test_tre_pertinenze_di_categorie_diverse_ammesse():
    d = caso_p_x()
    aggiungi_fabbricato(d, "b_cantina1", "C/2", "5000", "9", anna="X")
    aggiungi_fabbricato(d, "b_tettoia1", "C/7", "4000", "10", anna="X")
    es = _es(d)
    assert es.errori == [] and es.non_supportato == []
    assert _x(es, EH2 + "/suc:Pertinenza/suc:DatiCatastali/reg:Subalterno/text()") == ["9", "7", "10"]  # C/2, C/6, C/7


def test_p_su_due_immobili_dello_stesso_soggetto():
    d = caso_prima_casa()
    aggiungi_fabbricato(d, "b_casa0002", "A/3", "40000", "8", anna="P")
    assert ("persone[p_anna0001]", "REGOLA_PRIMA_CASA_P_UNICO") in _errori(_blocco(d))


def test_p_su_terreno_non_ammesso():
    d = caso_prima_casa()
    _agev(d, "d_terranna", "P")
    _tel(d)["devoluzioni"]["d_casaanna"] = {"agevolazioni": "P"}
    assert ("devoluzioni[d_terranna].agevolazioni", "REGOLA_AGEVOLAZIONE_QUADRO") in _errori(_blocco(d))


def test_codici_non_supportati_bloccano():
    for codice in ("Y",):
        d = caso_prima_casa()
        _agev(d, "d_casaanna", codice)
        _tel(d)["dichiarazione"].pop("prima_casa")
        es = _blocco(d)
        assert any(f"agevolazioni={codice}: agevolazione non supportata" in s for s in es.non_supportato), codice
    d = caso_prima_casa()                      # G: ora gestita, ma solo nel quadro EN (tests/test_agevolazioni.py)
    _agev(d, "d_casaanna", "G")
    _tel(d)["dichiarazione"].pop("prima_casa")
    assert any("agevolazioni=G nel quadro EC: non supportato" in s for s in _blocco(d).non_supportato)
    d = caso_prima_casa()
    _agev(d, "d_casaanna", "K")
    assert ("devoluzioni[d_casaanna].agevolazioni", "VALORE_NON_VALIDO") in _errori(_blocco(d))


def test_z_senza_p_o_di_altro_soggetto_non_supportato():
    d = caso_prima_casa()
    _tel(d).pop("devoluzioni")
    _tel(d)["dichiarazione"].pop("prima_casa")
    aggiungi_fabbricato(d, "b_casa0002", "A/3", "40000", "8", anna="Z")
    es = _blocco(d)
    assert any("agevolazione Z senza P" in s for s in es.non_supportato)
    d = caso_p_z()
    aggiungi_fabbricato(d, "b_casa0003", "A/3", "40000", "9", luca="Z")
    _agev(d, "d_casa0003_luca", "Z")
    es = _blocco(d)
    assert any("senza P dello stesso soggetto" in s or "diverso dal dichiarante" in s for s in es.non_supportato)


def test_z_di_luca_con_p_di_luca_non_supportato():
    d = caso_luca_dichiarante_non_richiedente()
    aggiungi_fabbricato(d, "b_casa0002", "A/3", "40000", "8", luca="Z")
    es = _blocco(d)
    assert any("diverso dal dichiarante" in s for s in es.non_supportato), es.non_supportato


def test_due_z_non_supportati():
    d = caso_p_z()
    aggiungi_fabbricato(d, "b_casa0003", "A/4", "40000", "9", anna="Z")
    assert any("piu' immobili con agevolazione Z" in s for s in _blocco(d).non_supportato)


def test_em_tavolare_non_supportato():
    from telematico_casi import caso_tavolare
    d = caso_tavolare()
    _tel(d).setdefault("devoluzioni", {})
    fab = next(v for v in d["devoluzioni"] if v["bene_id"] == "b_fabbtav1")
    _tel(d)["devoluzioni"][fab["id"]] = {"agevolazioni": "P"}
    es = esporta_xml(d, contesto(allegati=ALLEGATI, data_riferimento=date(2025, 9, 1)))
    assert es.xml is None and any("quadro EM" in s and "prima casa" in s for s in es.non_supportato)


def test_richiesta_di_altro_soggetto_senza_allegati_e_incompleta():
    d = caso_luca_dichiarante_non_richiedente()
    d["documenti_ref"] = [v for v in d["documenti_ref"] if v["tipo_eg"] not in ("PrimaCasa", "DocumentiIdentita")]
    es = _es(d)
    assert es.errori == [] and es.completo is False
    assert {m.percorso for m in es.quadri_mancanti} == {"quadro[EG].PrimaCasa", "quadro[EG].DocumentiIdentita"}
    assert es.xml is None   # scopo 'completo': nessun file senza gli allegati obbligatori


def test_dati_della_sezione_ii_obbligatori():
    d = caso_prima_casa()
    _tel(d)["dichiarazione"].pop("prima_casa")
    assert ("opzioni.telematico.dichiarazione.prima_casa", "DATO_MANCANTE") in _errori(_blocco(d))
    for chiave, errore in (("dichiara_requisiti", "DATO_MANCANTE"), ("requisito_comune", "DATO_MANCANTE"),
                           ("nessuna_altra_casa_comune", "DATO_MANCANTE"), ("altra_casa", "DATO_MANCANTE")):
        d = caso_prima_casa()
        _tel(d)["dichiarazione"]["prima_casa"].pop(chiave)
        assert (f"opzioni.telematico.dichiarazione.prima_casa.{chiave}", errore) in _errori(_blocco(d)), chiave
    d = caso_prima_casa()
    _tel(d)["dichiarazione"]["prima_casa"]["requisito_comune"] = "estero"
    assert ("opzioni.telematico.dichiarazione.prima_casa.requisito_comune", "VALORE_NON_VALIDO") in _errori(_blocco(d))
    d = caso_prima_casa()
    _tel(d)["dichiarazione"]["prima_casa"]["altra_casa"] = "forse"
    assert ("opzioni.telematico.dichiarazione.prima_casa.altra_casa", "VALORE_NON_VALIDO") in _errori(_blocco(d))
    d = caso_prima_casa()
    _tel(d)["dichiarazione"]["prima_casa"]["nessuna_altra_casa_comune"] = False
    assert ("opzioni.telematico.dichiarazione.prima_casa.nessuna_altra_casa_comune",
            "REGOLA_PRIMA_CASA_REQUISITO") in _errori(_blocco(d))
    d = caso_prima_casa()
    _tel(d)["dichiarazione"]["prima_casa"]["extra"] = 1
    assert any("prima_casa.extra: chiave non gestita" in s for s in _blocco(d).non_supportato)


def test_vendita_altra_casa_e_altri_requisiti_comune():
    for req, flag in (("attivita", "FlagComuneAttivita"), ("stabilire_residenza", "FlagCambioResidenza")):
        d = caso_prima_casa()
        _tel(d)["dichiarazione"]["prima_casa"].update(requisito_comune=req, altra_casa="vendita")
        es = _es(d)
        assert es.errori == [] and _x(es, EH2 + f"/suc:Opzioni/suc:{flag}/text()") == ["1"]
        assert _x(es, EH2 + "/suc:AltraCasa/suc:FlagVenditaAltraCasa/text()") == ["1"]


def test_z_richiede_impegno_unione_catastale():
    d = caso_p_z()
    _tel(d)["dichiarazione"]["prima_casa"].pop("impegno_unione_catastale")
    assert ("opzioni.telematico.dichiarazione.prima_casa.impegno_unione_catastale", "DATO_MANCANTE") in _errori(_blocco(d))


def test_sezione_ii_senza_p_del_dichiarante_e_incoerente():
    d = caso_luca_dichiarante_non_richiedente()
    _tel(d)["dichiarazione"]["prima_casa"] = dict(PRIMA_CASA_DICH)
    assert ("opzioni.telematico.dichiarazione.prima_casa", "DATI_INCOERENTI") in _errori(_blocco(d))


def test_chiave_non_gestita_nel_supplemento_devoluzioni():
    d = caso_prima_casa()
    _tel(d)["devoluzioni"]["d_casaanna"]["campo_inesistente"] = "1"
    es = _blocco(d)
    assert any("devoluzioni[d_casaanna].campo_inesistente" in s for s in es.non_supportato)


def test_imposta_proporzionale_residua_sotto_la_fissa_ora_coperta():
    # 300 / 150 euro < 200: colonna 2 = imposta calcolata; con la prima casa il dovuto include gia' la fissa del rigo EF4
    d = caso_prima_casa()
    next(b for b in d["beni"] if b["id"] == "b_terr0001")["valore"] = "15000"
    es = _es(d)
    assert es.errori == [] and es.completo and not es.quadri_mancanti


def test_sezione_urbana_riportata_nella_sezione_ii():
    d = caso_prima_casa()
    next(b for b in d["beni"] if b["id"] == "b_casa0001")["sezione"] = "AB"
    es = _es(d)
    assert es.errori == []
    assert _x(es, D + "/suc:QuadroEC//reg:SezioneUrbana/text()") == ["AB"] or _x(es, D + "/suc:QuadroEC//suc:SezioneUrbana/text()") == ["AB"]
    assert _x(es, EH2 + "/suc:ImmobilePrincipale/suc:SezioneUrbana/text()") == ["AB"]


def test_valore_quote_prima_casa_non_intero_arrotondato_all_euro():
    # tre figli con quota 1/3 su un fabbricato da 126001 euro: 3 x 42000,33 = 126000,99, somma non intera. Dal 2026-11-07 la
    # somma e' arrotondata all'euro nel rigo EF4 col. 2 (docs/regole/dubbio_arrotondamento.md §7; tests/test_quote_non_intere.py)
    from successioni.telematico.identificativi import genera_cf_sintetico
    d = caso_prima_casa()
    tel = _tel(d)
    d["persone"].append({"id": "p_figlio003", "_origine": {}, "cognome": "Rossi", "nome": "Bruno",
                         "codice_fiscale": genera_cf_sintetico("Rossi", "Bruno", "M", "1975-01-01", "H501"),
                         "data_nascita": "1975-01-01", "luogo_nascita": "Roma", "ruolo": "erede"})
    tel["persone"]["p_figlio003"] = {"sesso": "M", "provincia_nascita": "RM", "grado_parentela": "02"}
    next(b for b in d["beni"] if b["id"] == "b_casa0001")["valore"] = "126001"
    d["devoluzioni"] = []
    for bid in ("b_casa0001", "b_terr0001", "b_conto001"):
        for pid in ("p_anna0001", "p_luca0001", "p_figlio003"):
            d["devoluzioni"].append({"id": f"d_{bid[2:6]}{pid[2:]}", "_origine": {}, "bene_id": bid, "persona_id": pid,
                                     "quota": "1/3", "diritto": "1"})
    tel.pop("devoluzioni")
    _agev(d, "d_casaanna0001", "P")
    tel["passivita"]["ps_mutuo01"]["ripartizione"] = [{"persona_id": p, "quota": "1/3"}
                                                       for p in ("p_anna0001", "p_luca0001", "p_figlio003")]
    es = _es(d)
    assert es.errori == [] and es.non_supportato == [], (es.errori, es.non_supportato)
    assert not [m for m in es.quadri_mancanti if m.percorso == "quadro[EF]"], [m.messaggio for m in es.quadri_mancanti]
    assert _x(es, EF + "/suc:SezioneI_ImpostaIpotecaria/suc:PrimaCasa/suc:AgevolazionePX_Valore/text()") == ["126001"]
    assert any(a.codice == "ARROTONDAMENTO_SOMMA_VALORI_QUOTA" and "126000,99" in a.messaggio for a in es.avvisi)


def test_importazione_legge_le_agevolazioni():
    es = _es(caso_prima_casa())
    # dalla revisione 2 (07/11/2026) l'importazione legge Agevolazioni nelle stesse chiavi dell'export
    ops = importa.importa_xml(es.xml)
    assert "'agevolazioni': 'P'" in repr(ops)


def test_calcolo_blocca_ancora_le_altre_agevolazioni():
    es = _es(caso_prima_casa())
    xml = es.xml.replace(b"<suc:Agevolazioni>P</suc:Agevolazioni>", b"<suc:Agevolazioni>K</suc:Agevolazioni>")   # codice inesistente
    r = calcola_da_xml(xml)
    assert r.stato != "completato" and any(m.codice == "CALCOLO_NON_SUPPORTATO" for m in r.motivi)


# ------------------------------------------------------------------------------- controllo ufficiale locale (SUC13 2.3.1)
def _controllo(xml: bytes, tmp_path):
    stato, dgn, _wri, _dcm = _esegui(xml, tmp_path, rapporto=False)
    return stato, sorted((x["codice"], x["gravita"], x["campo"]) for x in dgn["diagnostici"])


CASI_POSITIVI = {"p": caso_prima_casa, "p_x": caso_p_x, "p_z": caso_p_z, "p_altro_soggetto": caso_p_altro_soggetto,
                 "solo_prima_casa": caso_solo_prima_casa, "non_dichiarante": caso_luca_dichiarante_non_richiedente}


@SALTO
@pytest.mark.parametrize("nome", sorted(CASI_POSITIVI))
@pytest.mark.java
def test_reale_controllo_ufficiale_positivo(nome, tmp_path):
    es = _es(CASI_POSITIVI[nome]())
    assert es.errori == [] and es.xml
    stato, diag = _controllo(es.xml, tmp_path)
    assert stato == "positivo" and diag == [("3345", 4, "XXX01")], diag


def _senza(xml: str, apri: str) -> str:
    a = xml.index(f"<suc:{apri}>")
    b = xml.index(f"</suc:{apri}>") + len(f"</suc:{apri}>")
    return xml[:a] + xml[b:]


# ogni negativo altera il file esportato in un punto della prima casa e deve essere scartato dal controllo ufficiale
NEGATIVI = {
    "imposta_ef4_errata": (lambda s: s.replace("<suc:PrimaCasa_Imposta>200<", "<suc:PrimaCasa_Imposta>400<"),
                           {"3076"}),
    "valore_quote_ef4_errato": (lambda s: s.replace("<suc:AgevolazionePX_Valore>126000<", "<suc:AgevolazionePX_Valore>100000<"),
                                {"3120"}),
    "catastale_fissa_errata": (lambda s: s.replace("<suc:ImpostaCatastaleFissa>200<", "<suc:ImpostaCatastaleFissa>400<"),
                               {"3076"}),
    "sezione_ii_assente": (lambda s: _senza(s, "SezioneII_AgevPrimaCasa"), {"3330", "3006", "3340", "3383", "3365"}),
    "dichiarazione_b_assente": (lambda s: s.replace("<suc:FlagNessunaAltraCasaComune>1</suc:FlagNessunaAltraCasaComune>", ""),
                                {"3365"}),
}


@SALTO
@pytest.mark.parametrize("nome", sorted(NEGATIVI))
@pytest.mark.java
def test_reale_controllo_ufficiale_negativo(nome, tmp_path):
    modifica, attesi = NEGATIVI[nome]
    es = _es(caso_prima_casa())
    xml = modifica(es.xml.decode("utf-8"))
    assert xml != es.xml.decode("utf-8")
    stato, diag = _controllo(xml.encode("utf-8"), tmp_path)
    assert stato == "negativo", diag
    codici = {c for c, g, _ in diag if g >= 16}
    assert codici == attesi, diag
