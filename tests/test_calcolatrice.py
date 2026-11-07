"""Calcolatrice rapida (calcolatrice.py): stime coerenti con i motori verificati, nessuna scrittura in archivio. Dati SINTETICI."""
import asyncio
import json
from datetime import date
from fractions import Fraction

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


FRATELLI = [{"grado": "10"}, {"grado": "10"}]


def test_importi_con_centesimi_arrotondati_all_euro():
    # review del 07/11/2026 sera: 150.000,50 e 1.234,56 davano «non stimabile» con il messaggio tecnico di DatoNP_Type
    r = C.stima({"data_decesso": "2025-03-10", "eredi": FRATELLI, "immobili": [{"valore": "150.000,50"}],
                 "altri_beni": [{"valore": "10.000,49"}], "passivita": [{"importo": "1.234,56"}]}, oggi=OGGI)
    assert r["stato"] == "stimato" and r["non_stimabile"] == [], r
    nota = next(n for n in r["note"] if n.startswith("Importi arrotondati"))
    assert "150.000,50 € → 150.001 €" in nota and "10.000,49 € → 10.000 €" in nota and "1.234,56 € → 1.235 €" in nota
    # 1.235 non si divide in euro interi fra due eredi: per la sola stima 1.234, dichiarato
    assert any("multipli di 2" in n and "1.235 € → 1.234 €" in n for n in r["note"])
    assert any("Fascicolo I, p. PDF 22" in a and "p. PDF 38" in a for a in r["assunzioni"])
    # stessi importi gia' interi: stessa stima
    r2 = C.stima({"data_decesso": "2025-03-10", "eredi": FRATELLI, "immobili": [{"valore": "150001"}],
                  "altri_beni": [{"valore": "10000"}], "passivita": [{"importo": "1234"}]}, oggi=OGGI)
    assert r2["totale"] == r["totale"] and imposte(r2) == imposte(r)


def test_valore_zero_con_messaggio_chiaro():
    with pytest.raises(C.DatiNonValidi, match="almeno 1 euro"):
        C.stima({"data_decesso": "2025-03-10", "eredi": FRATELLI, "immobili": [{"valore": "0"}]}, oggi=OGGI)
    with pytest.raises(C.DatiNonValidi, match="almeno 1 euro"):
        C.stima({"data_decesso": "2025-03-10", "eredi": FRATELLI, "immobili": [{"valore": "0,40"}]}, oggi=OGGI)
    r = C.stima({"data_decesso": "2025-03-10", "eredi": FRATELLI, "altri_beni": [{"valore": "0"}, {"valore": "5000"}],
                 "passivita": [{"importo": "0"}]}, oggi=OGGI)
    assert r["stato"] == "stimato"
    assert any("pari a zero" in n and "altro bene 1" in n and "passività 1" in n for n in r["note"])


def test_passivita_predefinita_e_mutuo_sull_immobile_scelto():
    # senza tipo: 12 (altre passivita'), che non richiede il cespite; anche senza immobili
    senza = C.stima({"data_decesso": "2025-03-10", "eredi": FRATELLI, "altri_beni": [{"valore": "300000"}]}, oggi=OGGI)
    r = C.stima({"data_decesso": "2025-03-10", "eredi": FRATELLI, "altri_beni": [{"valore": "300000"}],
                 "passivita": [{"importo": "10000"}]}, oggi=OGGI)
    assert r["stato"] == "stimato" and r["non_stimabile"] == []
    # 10.000 di passivita' in meno nella base, con la presunzione del 10% per denaro e conti (motore calcolo.py): 11.000 al 6%
    assert imposte(senza)["Imposta di successione"] - imposte(r)["Imposta di successione"] == 660
    # mutuo (tipo 3) senza immobile: errore chiaro, non «non stimabile»
    with pytest.raises(C.DatiNonValidi, match="immobile del mutuo.*aggiungere prima l'immobile"):
        C.stima({"data_decesso": "2025-03-10", "eredi": FRATELLI, "altri_beni": [{"valore": "1000"}],
                 "passivita": [{"tipo": "3", "importo": "1000"}]}, oggi=OGGI)
    with pytest.raises(C.DatiNonValidi, match="non esiste il numero 3"):
        C.stima({"data_decesso": "2025-03-10", "eredi": FRATELLI, "immobili": [{"valore": "1000"}],
                 "passivita": [{"tipo": "3", "importo": "1000", "immobile": 3}]}, oggi=OGGI)
    # mutuo sul secondo immobile (il fabbricato), non sul primo (terreno): stesse imposte del caso con il solo valore netto
    base = {"data_decesso": "2025-03-10", "eredi": FRATELLI,
            "immobili": [{"tipo": "terreno", "valore": "10000"}, {"valore": "300000"}]}
    r = C.stima({**base, "passivita": [{"tipo": "3", "importo": "20000", "immobile": 2}]}, oggi=OGGI)
    assert r["stato"] == "stimato", r
    dati = C._pratica(C.leggi_richiesta({**base, "passivita": [{"tipo": "3", "importo": "20000", "immobile": 2}]}, OGGI),
                      [Fraction(1, 2)] * 2)
    assert dati["opzioni"]["telematico"]["passivita"]["ps_pas000"]["bene_id"] == "b_imm001"
    # tipo 4 (debiti verso banche) su un altro bene
    dati = C._pratica(C.leggi_richiesta({"data_decesso": "2025-03-10", "eredi": FRATELLI, "altri_beni": [{"valore": "5000"}],
                                         "passivita": [{"tipo": "4", "importo": "100", "altro_bene": 1}]}, OGGI),
                      [Fraction(1, 2)] * 2)
    assert dati["opzioni"]["telematico"]["passivita"]["ps_pas000"]["bene_id"] == "b_alt000"
    with pytest.raises(C.DatiNonValidi, match="tipo non previsto"):
        C.leggi_richiesta({"data_decesso": "2025-03-10", "eredi": FRATELLI, "passivita": [{"tipo": "99", "importo": "1"}]}, OGGI)


def test_limiti_e_dati_non_oggetto():
    base = {"data_decesso": "2025-03-10", "altri_beni": [{"valore": "1000"}]}
    with pytest.raises(C.DatiNonValidi, match="al massimo 50 passività"):
        C.leggi_richiesta({**base, "eredi": FRATELLI, "passivita": [{"importo": "1"}] * 2000}, OGGI)
    with pytest.raises(C.DatiNonValidi, match="al massimo 30 eredi"):
        C.leggi_richiesta({**base, "eredi": [{"grado": "10"}] * 31}, OGGI)
    with pytest.raises(C.DatiNonValidi, match="al massimo 50 beni"):
        C.leggi_richiesta({**base, "eredi": FRATELLI, "immobili": [{"valore": "1"}] * 26, "altri_beni": [{"valore": "1"}] * 25},
                          OGGI)
    with pytest.raises(C.DatiNonValidi, match="voce 1: dati non validi"):
        C.leggi_richiesta({**base, "eredi": ["02"]}, OGGI)
    with pytest.raises(C.DatiNonValidi, match="atteso un elenco"):
        C.leggi_richiesta({**base, "eredi": "02"}, OGGI)
    with pytest.raises(C.DatiNonValidi, match="atteso un oggetto"):
        C.stima("02", oggi=OGGI)
    assert C.leggi_richiesta({**base, "eredi": [{"grado": "10"}] * 30}, OGGI)["eredi"]


@pytest.mark.parametrize("valore, atteso", [(True, True), ("true", True), ("si", True), ("Sì", True), (1, True),
                                            (False, False), ("false", False), ("no", False), ("", False), (None, False)])
def test_disabile_come_testo(valore, atteso):
    c = C.leggi_richiesta({"data_decesso": "2025-03-10", "eredi": [{"grado": "02", "disabile": valore}]}, OGGI)
    assert c["eredi"][0]["disabile"] is atteso


def test_disabile_non_riconosciuto_rifiutato():
    with pytest.raises(C.DatiNonValidi, match="disabilità grave: valore non valido"):
        C.leggi_richiesta({"data_decesso": "2025-03-10", "eredi": [{"grado": "02", "disabile": "forse"}]}, OGGI)


def test_data_nel_futuro_rispetto_a_oggi_e_termine():
    with pytest.raises(C.DatiNonValidi, match="nel futuro"):
        C.stima({"data_decesso": "2026-11-08", "eredi": FRATELLI, "altri_beni": [{"valore": "1"}]}, oggi=OGGI)
    # con oggi passato come parametro vale la data indicata, non quella del sistema
    assert C.leggi_richiesta({"data_decesso": "2026-11-08", "eredi": FRATELLI}, date(2026, 12, 1))
    # termine: dodici mesi dal decesso, stesso calcolo di cruscotto._termine (Prossime azioni)
    from successioni.cruscotto import _termine
    for dd in (date(2025, 3, 10), date(2024, 2, 29), date(2025, 12, 31)):
        assert C.termine_ordinario(dd).isoformat() == _termine(dd.isoformat(), OGGI)["data"]
    assert C._data_riferimento(date(2025, 11, 7), OGGI) == OGGI
    assert C._data_riferimento(date(2025, 3, 10), OGGI) == date(2026, 3, 10)
    # decesso esattamente dodici mesi fa: ancora nei termini, nessuna nota di termine scaduto
    r = C.stima({"data_decesso": "2025-11-07", "eredi": FRATELLI, "altri_beni": [{"valore": "1000"}]}, oggi=OGGI)
    assert not any("scaduto" in n for n in r["note"])
    r = C.stima({"data_decesso": "2025-11-06", "eredi": FRATELLI, "altri_beni": [{"valore": "1000"}]}, oggi=OGGI)
    assert any("scaduto il 06/11/2026" in n for n in r["note"])


def test_rotta_web_e_mcp_con_dati_non_oggetto(tmp_path, monkeypatch):
    sv = Servizio(Archivio(tmp_path / "d"))
    c = TestClient(crea_app(sv, token=T, ammetti_host_di_prova=True), base_url="http://testserver")
    c.get("/", params={"t": T})
    r = c.post("/api/calcolatrice", json={"data_decesso": "2025-03-10", "eredi": ["02"], "altri_beni": [{"valore": "1"}]})
    assert r.status_code == 422 and "dati non validi" in r.text
    r = c.post("/api/calcolatrice", json={"data_decesso": "2025-03-10", "eredi": FRATELLI,
                                          "passivita": [{"importo": "1"}] * 2000})
    assert r.status_code == 422 and "al massimo 50" in r.text
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(tmp_path / "cfg" / "configurazione.json"))

    async def scenario():
        async with Client(costruisci(sv)) as cl:
            a = await cl.call_tool("successioni_stima_imposte", {
                "data_decesso": "2025-03-10", "eredi": FRATELLI, "altri_beni": [{"valore": "1000"}],
                "passivita": [{"importo": "1"}] * 60})
            b = await cl.call_tool("successioni_stima_imposte", {
                "data_decesso": "2025-03-10", "eredi": FRATELLI, "altri_beni": [{"valore": "1000"}],
                "passivita": [{"importo": "1"}], "immobili": [{"valore": "1"}] * 51})
            return a, b
    a, b = asyncio.run(scenario())
    assert a.is_error and "al massimo 50 passività" in a.content[0].text
    assert b.is_error and "al massimo 50" in b.content[0].text


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


def test_richiesta_non_oggetto_e_mcp_con_voce_non_oggetto(tmp_path):
    """Messaggi in italiano anche quando la richiesta intera (web) o una voce (MCP) non e' un oggetto."""
    import asyncio
    from mcp.client import Client
    from starlette.testclient import TestClient
    from successioni.archivio import Archivio
    from successioni.mcp_server import costruisci
    from successioni.servizio import Servizio
    from successioni.web import crea_app
    sv = Servizio(Archivio(tmp_path / "d"))
    c = TestClient(crea_app(sv, token="tk", porta=8765), base_url="http://127.0.0.1:8765", follow_redirects=False)
    c.get("/", params={"t": "tk"})
    r = c.post("/api/calcolatrice", json=["02"], headers={"Origin": "http://127.0.0.1:8765"})
    assert r.status_code == 422 and "oggetto" in r.json()["messaggio"]

    async def scenario():
        async with Client(costruisci(sv)) as cl:
            return await cl.call_tool("successioni_stima_imposte", {"data_decesso": "2025-03-10", "eredi": ["02"]})
    res = asyncio.run(scenario())
    testo = res.content[0].text
    assert res.is_error and "Input should be" not in testo
