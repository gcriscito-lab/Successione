"""Quadri EE ed EH letti dal file con la struttura del modello (revisione del 15/11/2026). Dati sintetici (telematico_casi)."""
from lxml import etree

import telematico_casi as T
from successioni import anonimizza as AN
from successioni import riepilogo_ee_eh as RIE
from successioni.archivio import Archivio
from successioni.servizio import Servizio
from successioni.telematico.esporta import esporta_xml


def _quadri(caso):
    es = esporta_xml(caso, T.contesto_caso_a10())
    assert es.xml is not None, [e.messaggio for e in es.errori]
    r = etree.fromstring(es.xml)
    loc = lambda e: etree.QName(e).localname  # noqa: E731
    ee = [{"campo": loc(e), "valore": e.text.strip()} for q in r.iter() if loc(q) == "QuadroEE"
          for e in q.iter() if len(e) == 0 and (e.text or "").strip()]
    eh = next((q for q in r.iter() if loc(q) == "QuadroEH"), None)
    return ee, eh


def _voce(eh, lettera):
    return next(v for v in eh["sezioni"][0]["voci"] if v.get("lettera") == lettera)


def test_ee_otto_righi_nell_ordine_del_modello():
    ee, _ = _quadri(T.caso_mezzi())
    righi = RIE.righi_ee(ee)
    assert [r["rigo"] for r in righi] == [f"EE{i}" for i in range(1, 9)]
    per = {r["rigo"]: r for r in righi}
    # EE4 (aeromobili e navi) prima compariva col nome tecnico dell'elemento
    assert per["EE4"]["campo"] == "TotaleValoreAereiNavi" and per["EE4"]["valore"] and per["EE4"]["quadri"] == ["EP", "EQ"]
    assert per["EE2"]["valore"] is None and per["EE6"]["totale"] and per["EE8"]["totale"]
    assert int(per["EE6"]["valore"]) - int(per["EE7"]["valore"]) == int(per["EE8"]["valore"])
    assert {r["campo"] for r in righi} >= {x["campo"] for x in ee}, "ogni elemento del file ha il suo rigo"


def test_eh_sezione_i_con_lettere_eredi_e_testamento():
    _, q = _quadri(T.caso_testamento())
    eh = RIE.sezioni_eh(q)
    assert eh["dichiarante"]["codice_fiscale"] == T.CF_ANNA and eh["dichiarante"]["codice_carica"] == "1"
    assert [s["sezione"] for s in eh["sezioni"]] == ["I", "II", "III", "IV"]
    assert eh["sezioni"][0]["presente"] and not eh["sezioni"][1]["presente"] and eh["sezioni"][1]["nota"]
    a = _voce(eh, "a")
    assert ["Data del decesso", "10/03/2025"] in a["dati"]
    b = _voce(eh, "b")
    assert [r[0] for r in b["tabella"]["righe"]] == ["EH1", "EH2"] and "incluso me dichiarante" in b["scelta"]
    c = _voce(eh, "c")
    assert c["registrazioni"] and ["Serie", "1T"] in c["registrazioni"][0] and ["Data", "10/04/2025"] in c["registrazioni"][0]
    assert _voce(eh, "e")["scelta"].startswith("Non esistono") and _voce(eh, "f")["scelta"].startswith("Nessuno")
    assert "passività" in _voce(eh, "l")["scelta"]


def test_eh_navi_aeromobili_aziende_e_prima_casa():
    _, q = _quadri(T.caso_mezzi())
    m = [v for v in RIE.sezioni_eh(q)["sezioni"][0]["voci"] if v.get("lettera") == "m"]
    assert [v["dove"] for v in m] == ["EQ", "EP"] and ["Numero di iscrizione", "98765"] in m[0]["dati"]
    _, q = _quadri(T.caso_azienda())
    i = _voce(RIE.sezioni_eh(q), "i")
    assert ["Data di deposito", "30/06/2025"] in i["dati"] and ["Camera di commercio", "ROMA"] in i["dati"]
    _, q = _quadri(T.caso_prima_casa())
    s2 = RIE.sezioni_eh(q)["sezioni"][1]
    assert s2["presente"] and s2["voci"][0]["titolo"] == "Immobile principale" and ["Foglio", "100"] in s2["voci"][0]["dati"]
    assert any(x.startswith("a) ") for x in s2["voci"][-1]["elenco"])


def test_eh_assente():
    assert RIE.sezioni_eh(None) == {"dichiarante": None, "sezioni": []}


def test_anteprima_quadri_restituisce_righi_ee_e_dettaglio_eh(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    pid = sv.crea_pratica("Successione ROSSI MARIO", iniziali=AN.operazioni(T.caso_completo()))["pratica_id"]
    r = sv.anteprima_quadri(pid)
    assert [x["rigo"] for x in r["ee_righi"]] == [f"EE{i}" for i in range(1, 9)]
    assert r["ee_righi"][0]["valore"] == next(x["valore"] for x in r["ee"] if x["campo"] == "TotaleValoreImmobili")
    if r["eh"]:       # EH calcolato: anche il dettaglio per sezioni
        assert r["eh_dettaglio"]["sezioni"][0]["voci"]
