"""Calcolo dell'imposta di successione (guida ufficiale, successioni aperte dal 2025-01-01).

I valori attesi dell'esempio provengono dalla guida (All. Specifiche tecniche ... passaggi calcolo, pp. 2-5), non da
calcoli fatti a memoria. Esito: controllo locale; il confronto con il software ufficiale resta 'da_collaudare'.
"""
from __future__ import annotations

from successioni.telematico.calcolo import calcola, calcola_da_xml
from successioni.telematico.esporta import esporta_xml

from telematico_casi import CF_ANNA, CF_LUCA, caso_completo, contesto


def _fratelli() -> dict:
    """Esempio della guida (p. 1-5): due fratelli germani eredi in parti uguali di due immobili (250.000 e 150.000,
    quadro EC), denaro 5.000 (ER, DN), passivita' 1.000 ripartita in parti uguali.

    Limite del modello comune: una passivita' ha un solo persona_id, quindi la passivita' da 1.000 ripartita 1/2 e 1/2
    e' rappresentata con due righe da 500 (QP per erede identico: 500)."""
    d = caso_completo()
    tel = d["opzioni"]["telematico"]
    tel["dichiarazione"]["stato_civile"] = "1"
    for p in d["persone"][1:]:
        p["relazione_con_defunto"] = "10"
    tel["persone"]["p_anna0001"]["grado_parentela"] = "10"
    casa2 = dict(d["beni"][0], id="b_casa0002", subalterno="4", valore="150000")
    d["beni"][0]["valore"] = "250000"
    d["beni"] = [d["beni"][0], casa2,
                 {"id": "b_denaro01", "_origine": {}, "tipo": "disponibilita_finanziaria", "descrizione": "Denaro contante",
                  "valore": "5000", "diritto": "1", "quota_defunto": "1/1"}]
    tel["beni"] = {"b_casa0001": tel["beni"]["b_casa0001"], "b_casa0002": dict(tel["beni"]["b_casa0001"]),
                   "b_denaro01": {"tipo_cespite": "DN"}}
    d["devoluzioni"] = [{"id": f"d_{b[2:6]}{p[2:6]}", "_origine": {}, "bene_id": b, "persona_id": p, "quota": "1/2",
                         "diritto": "1"}
                        for b in ("b_casa0001", "b_casa0002", "b_denaro01") for p in ("p_anna0001", "p_luca0001")]
    d["passivita"] = [{"id": f"ps_{p[2:6]}0001", "_origine": {}, "descrizione": "Debito", "importo": "500",
                       "persona_id": p} for p in ("p_anna0001", "p_luca0001")]
    tel["passivita"] = {f"ps_{p[2:6]}0001": {"tipo": "12", "estremi_documento": "Atto 1", "data_documento": "2024-12-01",
                                             "possesso": "1/1"} for p in ("p_anna0001", "p_luca0001")}
    return d


def _valori(b):
    return {p.sigla: p.valore for p in b.passaggi}


def test_esempio_guida_senza_riduzioni_ne_estero():
    r = calcola(_fratelli())
    assert r.stato == "completato", r.motivi
    assert r.esito_collaudo == "da_collaudare"
    assert len(r.beneficiari) == 2
    for b in r.beneficiari:
        v = _valori(b)
        # guida p. 2: QE 200.000, QDN 2.500; p. 3: QP 500, AN 202.000; p. 4: FR 100.000, QN 102.000, PR 7.450,
        # QTI 109.450; p. 5: AL 6%, ISL 6.567
        assert {k: v[k] for k in ("QE", "QDN", "QP", "AN", "FR", "QN", "PR", "QTI", "AL", "ISL")} == {
            "QE": "200000", "QDN": "2500", "QP": "500", "AN": "202000", "FR": "100000", "QN": "102000",
            "PR": "7450", "QTI": "109450", "AL": "0.06", "ISL": "6567"}
        assert all(p.fonte for p in b.passaggi)
    # senza le parti L ed estero dell'esempio l'ISN coincide con l'ISL; totale per due eredi
    assert r.imposta_ef18bis == 13134
    assert r.candidati["esatta"]["imposta_ef18bis"] == r.candidati["componente_ispezionato"]["imposta_ef18bis"]


def test_caso_sintetico_figli_sotto_franchigia():
    r = calcola(caso_completo())
    assert r.stato == "completato"
    assert r.imposta_ef18bis == 0
    assert any("10 euro" in n for n in r.note)


def _cugini(valore: int) -> dict:
    d = caso_completo()
    tel = d["opzioni"]["telematico"]
    tel["dichiarazione"]["stato_civile"] = "1"
    for p in d["persone"][1:]:
        p["relazione_con_defunto"] = "21"
    tel["persone"]["p_anna0001"]["grado_parentela"] = "21"
    d["beni"] = [{"id": "b_conto001", "_origine": {}, "tipo": "disponibilita_finanziaria", "descrizione": "Conto",
                  "valore": str(valore), "diritto": "1", "quota_defunto": "1/1"}]
    tel["beni"] = {"b_conto001": {"tipo_cespite": "CR"}}
    d["devoluzioni"] = [
        {"id": "d_aaaa0001", "_origine": {}, "bene_id": "b_conto001", "persona_id": "p_anna0001", "quota": "1/3",
         "diritto": "1"},
        {"id": "d_bbbb0001", "_origine": {}, "bene_id": "b_conto001", "persona_id": "p_luca0001", "quota": "2/3",
         "diritto": "1"}]
    d["passivita"] = []
    del tel["passivita"]
    return d


def test_divergenza_aperta_quando_l_arrotondamento_cambia_l_importo():
    """Valore 150159 ripartito 1/3 - 2/3 tra due cugini (6%, nessuna franchigia): totale esatto 9910,494 -> 9910;
    replica del componente (PR e ISL al centesimo HALF_UP) 9910,50 -> 9911. Il caso non e' finalizzabile."""
    r = calcola(_cugini(150159))
    assert r.stato == "divergenza_aperta"
    assert r.imposta_ef18bis is None
    assert r.candidati["esatta"]["imposta_ef18bis"] == 9910
    assert r.candidati["componente_ispezionato"]["imposta_ef18bis"] == 9911
    assert r.motivi and r.motivi[0].codice == "ARROTONDAMENTO_NON_DEFINITO"


def test_decesso_anteriore_al_2025_non_supportato():
    d = caso_completo()
    d["persone"][0]["data_decesso"] = "2024-12-31"
    r = calcola(d)
    assert r.stato == "non_supportato"
    assert any(m.codice == "CALCOLO_NON_APPLICABILE" for m in r.motivi)


def test_agevolazioni_nel_file_non_supportate():
    es = esporta_xml(caso_completo(), contesto(scopo="bozza_tecnica"))
    xml = es.xml.replace(b"<suc:CodiceDiritto_Rip>1</suc:CodiceDiritto_Rip>",
                         b"<suc:CodiceDiritto_Rip>1</suc:CodiceDiritto_Rip><suc:Agevolazioni>K</suc:Agevolazioni>", 1)   # codice inesistente
    r = calcola_da_xml(xml)
    assert r.stato == "non_supportato"


def test_dati_incompleti():
    d = caso_completo()
    d["opzioni"]["telematico"]["dichiarazione"]["stato_civile"] = None
    r = calcola(d)
    assert r.stato == "dati_incompleti" and r.motivi


def test_franchigia_disabilita_e_presunzione_esclusa_con_beni_inventariati():
    d = _cugini(150159)
    d["opzioni"]["telematico"]["persone"]["p_anna0001"]["portatore_handicap"] = True
    d["opzioni"]["telematico"]["beni"]["b_conto001"]["tipo_cespite"] = "BI"
    r = calcola(d)
    v = {b.codice_fiscale: _valori(b) for b in r.beneficiari}
    anna, luca = v[CF_ANNA], v[CF_LUCA]
    assert anna["FR"] == "1500000" and anna["QN"] == "0"  # guida p. 3: 1.500.000 a prescindere dal grado
    assert luca["FR"] == "0" and luca["PR"] == "0"         # cugino: nessuna franchigia; BI -> niente presunzione
    assert luca["ISL"] == "6006.36"                        # 100106 x 6%
    assert r.imposta_ef18bis == 6006
