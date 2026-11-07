"""Calcolatrice rapida (calcolatrice.py): stime coerenti con i motori verificati, nessuna scrittura in archivio. Dati SINTETICI."""
import asyncio
import json
from datetime import date

import pytest
from mcp.client import Client
from starlette.testclient import TestClient

from successioni import calcolatrice as C
from successioni.archivio import Archivio
from successioni.mcp_server import STRUMENTI_LETTURA, costruisci
from successioni.servizio import Servizio
from successioni.web import crea_app

OGGI = date(2026, 11, 7)
T = "tok-calc"


def imposte(r: dict) -> dict:
    return {x["voce"]: int(x["importo"]) for x in r["imposte"]}


def test_caso_del_confronto_col_compilatore_ufficiale():
    # tests/test_confronto_compilatore_ufficiale.py: due fratelli, fabbricato 300.000, decesso 10/03/2025
    r = C.stima({"data_decesso": "2025-03-10", "eredi": [{"grado": "10"}, {"grado": "10"}],
                 "immobili": [{"valore": "300000"}]}, oggi=OGGI)
    assert r["stato"] == "stimato" and r["non_stimabile"] == []
    assert imposte(r) == {"Imposta di successione": 6600, "Imposta ipotecaria": 6000, "Imposta catastale": 3000,
                          "Tassa ipotecaria": 120, "Imposta di bollo": 85}
    assert r["totale"] == "15805"
    assert [e["imposta"] for e in r["eredi"]] == ["3.300 €", "3.300 €"]
    assert all(e["franchigia"] == "100.000 €" and e["aliquota"] == "6%" for e in r["eredi"])
    assert r["avvertenza"] == "Stima: non sostituisce la dichiarazione né il controllo ufficiale."
    assert r["quote_di_legge"] == ["1/2", "1/2"]
    sigle = [p["sigla"] for p in r["eredi"][0]["passaggi"]]
    assert sigle[:2] == ["QE", "QP"] and "FR" in sigle and sigle[-1] == "ISN"


def test_stessa_stima_con_quote_esplicite_e_importi_all_italiana():
    r = C.stima({"data_decesso": "2025-03-10", "eredi": [{"grado": "10", "quota": "1/2"}, {"grado": "10", "quota": "1/2"}],
                 "immobili": [{"valore": "300.000"}]}, oggi=OGGI)
    assert imposte(r)["Imposta di successione"] == 6600


def test_coniuge_e_figli_sotto_franchigia():
    # coniuge + 2 figli (1/3 ciascuno, Allegato 5), 900.000 di conto: 300.000 a testa, sotto la franchigia di 1.000.000
    r = C.stima({"data_decesso": "2025-06-01", "eredi": [{"grado": "01"}, {"grado": "02"}, {"grado": "02"}],
                 "altri_beni": [{"tipo": "CR", "valore": "900000"}]}, oggi=OGGI)
    assert r["stato"] == "stimato"
    assert r["quote_di_legge"] == ["1/3", "1/3", "1/3"]
    assert imposte(r)["Imposta di successione"] == 0
    assert "Imposta ipotecaria" in imposte(r) and imposte(r)["Imposta ipotecaria"] == 0
    assert all(e["franchigia"] == "1.000.000 €" and e["aliquota"] == "4%" for e in r["eredi"])


def test_figli_oltre_franchigia_e_disabilita():
    # due figli, 2.400.000 di conto (1.200.000 a testa); il secondo con disabilita' grave (franchigia 1.500.000)
    r = C.stima({"data_decesso": "2025-06-01", "eredi": [{"grado": "02"}, {"grado": "02", "disabile": True}],
                 "altri_beni": [{"tipo": "CR", "valore": "2400000"}]}, oggi=OGGI)
    e1, e2 = r["eredi"]
    assert e1["franchigia"] == "1.000.000 €" and e2["franchigia"] == "1.500.000 €"
    assert e2["imposta"] == "0 €"
    # stesso valore con calcola() della pratica completa: QE 1.200.000 - FR 1.000.000 = 200.000; PR 10% = 20.000; 4% di 220.000
    assert e1["imposta"] == "8.800 €" and imposte(r)["Imposta di successione"] == 8800


def test_prima_casa_e_valore_catastale_proposto():
    r = C.stima({"data_decesso": "2025-06-01", "eredi": [{"grado": "01"}, {"grado": "02"}, {"grado": "02"}],
                 "immobili": [{"valore": "250000", "prima_casa": True}, {"rendita": "800", "categoria": "A/3"}]}, oggi=OGGI)
    assert r["valori_catastali"][1]["valore_catastale"] == "100800"      # 800 x 1,05 x 120
    i = imposte(r)
    assert i["Imposta ipotecaria"] == 2016 + 200 and i["Imposta catastale"] == 1008 + 200
    assert any("Prima casa" in p for p in r["passaggi"])


def test_piu_circoscrizioni():
    r = C.stima({"data_decesso": "2025-03-10", "eredi": [{"grado": "10"}, {"grado": "10"}],
                 "immobili": [{"valore": "300000"}], "circoscrizioni": 3}, oggi=OGGI)
    assert imposte(r)["Tassa ipotecaria"] == 360 and imposte(r)["Imposta di bollo"] == 255


def test_decesso_prima_del_2025_non_stimabile_per_la_successione():
    r = C.stima({"data_decesso": "2024-05-01", "eredi": [{"grado": "02"}], "immobili": [{"valore": "100000"}]}, oggi=OGGI)
    assert r["stato"] == "parziale"
    assert "Imposta di successione" not in imposte(r)
    assert any("2025-01-01" in m and "ufficio" in m for m in r["non_stimabile"])
    assert imposte(r)["Imposta ipotecaria"] == 2000


def test_casi_non_coperti_restano_non_stimabili_con_motivo():
    # quote non indicate e gradi fuori dalle quote di legge coperte (zio)
    r = C.stima({"data_decesso": "2025-03-10", "eredi": [{"grado": "21"}], "altri_beni": [{"valore": "1000"}]}, oggi=OGGI)
    assert r["stato"] == "non_stimabile" and r["imposte"] == [] and r["non_stimabile"]
    # immobile senza valore e senza rendita
    r = C.stima({"data_decesso": "2025-03-10", "eredi": [{"grado": "02"}], "immobili": [{}]}, oggi=OGGI)
    assert r["stato"] == "non_stimabile" and "immobile 1" in r["non_stimabile"][0]


def test_dati_non_validi():
    for richiesta in ({}, {"data_decesso": "2025-03-10", "eredi": []},
                      {"data_decesso": "2025-03-10", "eredi": [{"grado": "XX"}], "altri_beni": [{"valore": "1"}]},
                      {"data_decesso": "2025-03-10", "eredi": [{"grado": "02", "quota": "1/3"}], "altri_beni": [{"valore": "1"}]}):
        with pytest.raises(C.DatiNonValidi):
            C.stima(richiesta, oggi=OGGI)


def test_pratica_iniziale_senza_dati_inventati():
    p = C.pratica_iniziale({"data_decesso": "2025-03-10", "eredi": [{"grado": "10", "nome": "Anna"}, {"grado": "10"}]})
    assert p["data_decesso"] == "2025-03-10"
    assert [o["campi"] for o in p["operazioni"]] == [
        {"ruolo": "erede", "grado_parentela": "10", "relazione_con_defunto": "10", "nome": "Anna"},
        {"ruolo": "erede", "grado_parentela": "10", "relazione_con_defunto": "10"}]


def _file(base):
    return sorted(str(p.relative_to(base)) for p in base.rglob("*") if p.is_file())


def test_rotta_web_non_scrive_nell_archivio(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    c = TestClient(crea_app(sv, token=T, ammetti_host_di_prova=True), base_url="http://testserver")
    c.get("/", params={"t": T})
    prima = _file(tmp_path)
    r = c.post("/api/calcolatrice", json={"data_decesso": "2025-03-10", "eredi": [{"grado": "10"}, {"grado": "10"}],
                                          "immobili": [{"valore": "300000"}]})
    assert r.status_code == 200, r.text
    assert imposte(r.json())["Imposta di successione"] == 6600
    assert c.post("/api/calcolatrice", json={"data_decesso": "x"}).status_code == 422
    assert c.post("/api/calcolatrice", json={"azione": "pratica_iniziale", "data_decesso": "2025-03-10",
                                             "eredi": [{"grado": "02"}]}).json()["operazioni"]
    assert _file(tmp_path) == prima and sv.elenca() == []
    assert c.post("/api/calcolatrice", json={}, headers={"origin": "http://evil.example"}).status_code == 403


def test_strumento_mcp_in_sola_lettura(tmp_path, monkeypatch):
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(tmp_path / "cfg" / "configurazione.json"))
    monkeypatch.setenv("SUCCESSIONI_MCP_SOLA_LETTURA", "1")          # funziona anche con Claude in sola lettura
    assert "stima_imposte" in STRUMENTI_LETTURA
    sv = Servizio(Archivio(tmp_path / "d"))
    prima = _file(tmp_path)

    async def scenario():
        async with Client(costruisci(sv)) as cl:
            return await cl.call_tool("successioni_stima_imposte", {
                "data_decesso": "2025-03-10", "eredi": [{"grado": "10"}, {"grado": "10"}], "immobili": [{"valore": "300000"}]})
    res = asyncio.run(scenario())
    assert not res.is_error
    sc = res.structured_content
    d = sc.get("result", sc) if isinstance(sc, dict) else json.loads(res.content[0].text)
    assert imposte(d)["Imposta di successione"] == 6600 and d["avvertenza"].startswith("Stima")
    assert _file(tmp_path) == prima and sv.elenca() == []
