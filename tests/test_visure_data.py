"""Data della visura catastale: avviso (o blocco) per visure mancanti di data o piu' vecchie di N giorni. Fascicolo I pp. PDF 20 e 28.
Il campo e' un dato interno: non entra nell'XML e non e' segnalato come «campo non esportato»."""
from datetime import date, timedelta

import pytest

from successioni import impostazioni
from successioni.archivio import Archivio
from successioni.quadri import rilievi_visure
from successioni.servizio import Servizio
from test_correzioni_codex import pratica_con_allegati


@pytest.fixture(autouse=True)
def _isola(monkeypatch, tmp_path):
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(tmp_path / "cfg" / "configurazione.json"))


def _giorni_fa(n):
    return (date.today() - timedelta(days=n)).isoformat()


def _imposta_visure(s, pid, data):
    d = s.leggi(pid)
    ops = [{"op": "upsert", "coll": "beni", "id": b["id"], "campi": {"data_visura": data}}
           for b in d["dati"]["beni"] if b.get("tipo") in ("fabbricato", "terreno")]
    s.aggiorna(pid, d["revisione"], ops)


def test_funzione_pura_mancante_vecchia_e_recente():
    dati = {"beni": [{"id": "a", "tipo": "fabbricato"}, {"id": "b", "tipo": "terreno", "data_visura": _giorni_fa(200)},
                     {"id": "c", "tipo": "terreno", "data_visura": _giorni_fa(30)},
                     {"id": "d", "tipo": "disponibilita_finanziaria"}], "opzioni": {}}
    r = {x.percorso: x for x in rilievi_visure(dati, 90)}
    assert set(r) == {"beni[a].data_visura", "beni[b].data_visura"}
    assert r["beni[a].data_visura"].codice == "VISURA_SENZA_DATA"
    assert r["beni[b].data_visura"].codice == "VISURA_VECCHIA" and "200" in r["beni[b].data_visura"].messaggio
    assert "pp. PDF 20 e 28" in r["beni[b].data_visura"].fonte
    assert [x.codice for x in rilievi_visure({"beni": [{"id": "b", "tipo": "terreno", "data_visura": _giorni_fa(200)}], "opzioni": {}}, 365)] == []


def test_avviso_non_impedisce_la_finalizzazione(tmp_path):
    s, pid = pratica_con_allegati(tmp_path / "a")
    assert s.esporta(pid)["completo"]
    v = s.verifica(pid)
    assert {a["codice"] for a in v["avvisi"]} == {"VISURA_SENZA_DATA"} and v["esito"] == "ok" and v["finalizzabile"]
    _imposta_visure(s, pid, _giorni_fa(200))
    assert s.esporta(pid)["completo"]
    v = s.verifica(pid)
    assert {a["codice"] for a in v["avvisi"]} == {"VISURA_VECCHIA"} and v["finalizzabile"] and not v["rilievi"]
    assert s.quadri(pid)["avvisi"] == v["avvisi"]
    _imposta_visure(s, pid, _giorni_fa(10))
    assert s.esporta(pid)["completo"] and s.verifica(pid)["avvisi"] == []


def test_blocco_se_richiesto(tmp_path):
    impostazioni.salva({}, preferenze_nuove={"visura_blocca": True})
    s, pid = pratica_con_allegati(tmp_path / "a")
    assert s.esporta(pid)["completo"]
    v = s.verifica(pid)
    assert v["esito"] == "rilievi" and not v["finalizzabile"] and v["avvisi"] == []
    assert {r["codice"] for r in v["rilievi"]} == {"VISURA_SENZA_DATA"}
    _imposta_visure(s, pid, _giorni_fa(5))
    assert s.esporta(pid)["completo"]
    assert s.verifica(pid)["finalizzabile"]


def test_soglia_configurabile(tmp_path):
    s, pid = pratica_con_allegati(tmp_path / "a")
    _imposta_visure(s, pid, _giorni_fa(100))
    assert {a["codice"] for a in s.verifica(pid)["avvisi"]} == {"VISURA_VECCHIA"}
    impostazioni.salva({}, preferenze_nuove={"avviso_visura_giorni": 120})
    assert s.verifica(pid)["avvisi"] == []


def test_data_visura_non_va_nell_xml_ne_tra_i_campi_non_esportati(tmp_path):
    s, pid = pratica_con_allegati(tmp_path / "a")
    _imposta_visure(s, pid, _giorni_fa(5))
    r = s.esporta(pid)
    assert r["completo"] and not r["errori"] and not r["non_supportato"]
    xml, _ = s.file_export(pid)
    assert b"data_visura" not in xml.lower() and _giorni_fa(5).replace("-", "").encode() not in xml
