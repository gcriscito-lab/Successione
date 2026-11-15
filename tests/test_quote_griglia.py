"""Griglia delle quote e agevolazioni guidate (layout ripreso da DEAS, 15/11/2026). Dati sintetici (telematico_casi)."""
import pytest

import telematico_casi as T
from successioni import anonimizza as AN
from successioni.archivio import Archivio
from successioni.errori import ConflittoRevisione, DatiNonValidi
from successioni.servizio import Servizio


def _servizio(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    pid = sv.crea_pratica("Successione ROSSI MARIO", iniziali=AN.operazioni(T.caso_completo()))["pratica_id"]
    return sv, pid


def _riga(g, bene_id, diritto="1"):
    return next(r for r in g["righe"] if r["bene_id"] == bene_id and r["diritto"] == diritto)


def test_griglia_legge_le_devoluzioni_per_bene_e_diritto(tmp_path):
    sv, pid = _servizio(tmp_path)
    g = sv.quote_griglia(pid)
    assert [c["id"] for c in g["colonne"]] == ["p_anna0001", "p_luca0001"]
    casa = _riga(g, "b_casa0001")
    assert casa["celle"]["p_anna0001"]["quota"] == "1/2" and casa["somma"] == "1/1" and casa["esito"] == "completa"
    # «proprieta» e «1» sono lo stesso diritto: una sola riga per il terreno
    assert [r["diritto"] for r in g["righe"] if r["bene_id"] == "b_terr0001"] == ["1"]
    assert casa["quadro"] == "EC" and casa["quota_defunto"] == "1/1" and casa["diritto_testo"]
    assert g["fuori_griglia"] == []


def test_salva_crea_modifica_e_toglie_in_una_revisione(tmp_path):
    sv, pid = _servizio(tmp_path)
    p = sv.leggi(pid)
    rev, n_dev = p["revisione"], len(p["dati"]["devoluzioni"])
    r = sv.quote_salva(pid, rev, [
        {"bene_id": "b_casa0001", "persona_id": "p_anna0001", "diritto": "1", "quota": "2/3"},
        {"bene_id": "b_casa0001", "persona_id": "p_luca0001", "diritto": "1", "quota": "1/3"},
        {"bene_id": "b_terr0001", "persona_id": "p_luca0001", "diritto": "1", "quota": ""},
    ])
    assert r["revisione"] == rev + 1 and r["modifiche"] == 3
    casa = _riga(r["griglia"], "b_casa0001")
    assert casa["celle"]["p_anna0001"]["quota"] == "2/3" and casa["esito"] == "completa"
    terr = _riga(r["griglia"], "b_terr0001")
    assert set(terr["celle"]) == {"p_anna0001"} and terr["esito"] == "incompleta" and terr["manca"] == "1/2"
    assert len(sv.leggi(pid)["dati"]["devoluzioni"]) == n_dev - 1
    # cella nuova: riga di devoluzione creata con il diritto indicato
    r2 = sv.quote_salva(pid, rev + 1, [{"bene_id": "b_terr0001", "persona_id": "p_luca0001", "diritto": "1", "quota": {"num": 1, "den": 2}}])
    nuova = [d for d in sv.leggi(pid)["dati"]["devoluzioni"] if d["bene_id"] == "b_terr0001" and d["persona_id"] == "p_luca0001"]
    assert len(nuova) == 1 and nuova[0]["quota"] == {"num": 1, "den": 2} and nuova[0]["diritto"] == "1"
    assert _riga(r2["griglia"], "b_terr0001")["esito"] == "completa"


def test_salva_invariato_non_crea_revisione_e_controlla_la_revisione(tmp_path):
    sv, pid = _servizio(tmp_path)
    rev = sv.leggi(pid)["revisione"]
    r = sv.quote_salva(pid, rev, [{"bene_id": "b_casa0001", "persona_id": "p_anna0001", "diritto": "proprieta", "quota": "2/4"}])
    assert r["modifiche"] == 0 and sv.leggi(pid)["revisione"] == rev
    with pytest.raises(ConflittoRevisione):
        sv.quote_salva(pid, rev - 1, [{"bene_id": "b_casa0001", "persona_id": "p_anna0001", "diritto": "1", "quota": "1/2"}])


@pytest.mark.parametrize("cella, msg", [
    ({"bene_id": "b_nessuno", "persona_id": "p_anna0001", "diritto": "1", "quota": "1/2"}, "bene inesistente"),
    ({"bene_id": "b_casa0001", "persona_id": "p_defunto1", "diritto": "1", "quota": "1/2"}, "defunto"),
    ({"bene_id": "b_casa0001", "persona_id": "p_anna0001", "diritto": "", "quota": "1/2"}, "diritto mancante"),
    ({"bene_id": "b_casa0001", "persona_id": "p_anna0001", "diritto": "1", "quota": "3/2"}, "maggiore di 1"),
    ({"bene_id": "b_casa0001", "persona_id": "p_anna0001", "diritto": "1", "quota": "mezzo"}, "quota non valida"),
])
def test_salva_rifiuta_celle_errate_senza_scrivere(tmp_path, cella, msg):
    sv, pid = _servizio(tmp_path)
    rev = sv.leggi(pid)["revisione"]
    with pytest.raises(DatiNonValidi, match=msg):
        sv.quote_salva(pid, rev, [{"bene_id": "b_casa0001", "persona_id": "p_luca0001", "diritto": "1", "quota": "1/3"}, cella])
    assert sv.leggi(pid)["revisione"] == rev


def test_salva_rifiuta_righe_doppie_e_celle_ripetute(tmp_path):
    sv, pid = _servizio(tmp_path)
    rev = sv.leggi(pid)["revisione"]
    sv.aggiorna(pid, rev, [{"op": "upsert", "coll": "devoluzioni",
                            "campi": {"bene_id": "b_casa0001", "persona_id": "p_anna0001", "diritto": "1", "quota": "1/4"}}])
    g = sv.quote_griglia(pid)
    assert _riga(g, "b_casa0001")["esito"] == "righe_doppie" and _riga(g, "b_casa0001")["doppie"] == ["p_anna0001"]
    with pytest.raises(DatiNonValidi, match="righe per lo stesso bene"):
        sv.quote_salva(pid, rev + 1, [{"bene_id": "b_casa0001", "persona_id": "p_anna0001", "diritto": "1", "quota": "1/2"}])
    c = {"bene_id": "b_terr0001", "persona_id": "p_anna0001", "diritto": "1", "quota": "1/2"}
    with pytest.raises(DatiNonValidi, match="due volte"):
        sv.quote_salva(pid, rev + 1, [c, dict(c, diritto="proprieta")])


def test_bene_senza_devoluzioni_compare_vuoto(tmp_path):
    sv, pid = _servizio(tmp_path)
    rev = sv.leggi(pid)["revisione"]
    sv.aggiorna(pid, rev, [{"op": "upsert", "coll": "beni", "id": "b_nuovo001",
                            "campi": {"tipo": "fabbricato", "comune": "Roma", "foglio": "1", "particella": "2", "diritto": "1",
                                      "quota_defunto": "1/1"}}])
    r = _riga(sv.quote_griglia(pid), "b_nuovo001")
    assert r["esito"] == "vuota" and r["celle"] == {} and r["somma"] == "0/1"


# ------------------------------------------------------------------ agevolazioni guidate
def test_agevolazioni_guidate_elenca_codici_con_i_quadri(tmp_path):
    sv, pid = _servizio(tmp_path)
    g = sv.agevolazioni_guidate(pid)
    q = {c["valore"]: c["quadri"] for c in g["codici"]}
    assert q["P"] == ["EC"] and q["X"] == ["EC"] and "EN" in q["Q"] and set(q["F"]) == {"EC", "EM"}
    casa = next(b for b in g["beni"] if b["bene_id"] == "b_casa0001")
    assert casa["quadro"] == "EC" and {x["persona_id"] for x in casa["beneficiari"]} == {"p_anna0001", "p_luca0001"}


def test_applica_scrive_sulle_righe_e_toglie(tmp_path):
    sv, pid = _servizio(tmp_path)
    rev = sv.leggi(pid)["revisione"]
    r = sv.agevolazione_applica(pid, rev, "p", ["b_casa0001"], ["p_anna0001"])
    assert r["revisione"] == rev + 1 and r["applicate"] == 1 and r["cambiate"] == 1 and r["senza_devoluzione"] == []
    sup = sv.leggi(pid)["dati"]["opzioni"]["telematico"]["devoluzioni"]
    assert sup["d_casaanna"]["agevolazioni"] == "P" and "d_casaluca" not in sup
    assert _riga(sv.quote_griglia(pid), "b_casa0001")["celle"]["p_anna0001"]["agevolazione"] == "P"
    # stessa scelta: nessuna nuova revisione
    assert sv.agevolazione_applica(pid, rev + 1, "P", ["b_casa0001"], ["p_anna0001"])["cambiate"] == 0
    assert sv.leggi(pid)["revisione"] == rev + 1
    # codice vuoto: tolto, e il supplemento vuoto sparisce
    sv.agevolazione_applica(pid, rev + 1, "", ["b_casa0001"], ["p_anna0001"])
    assert "devoluzioni" not in (sv.leggi(pid)["dati"]["opzioni"].get("telematico") or {})


def test_applica_segnala_coppie_senza_riga_e_rifiuta_quadri_non_supportati(tmp_path):
    sv, pid = _servizio(tmp_path)
    rev = sv.leggi(pid)["revisione"]
    sv.quote_salva(pid, rev, [{"bene_id": "b_terr0001", "persona_id": "p_luca0001", "diritto": "1", "quota": ""}])
    r = sv.agevolazione_applica(pid, rev + 1, "R", ["b_terr0001"], ["p_anna0001", "p_luca0001"])
    assert r["applicate"] == 1 and r["senza_devoluzione"] == [{"bene_id": "b_terr0001", "persona_id": "p_luca0001"}]
    rev = sv.leggi(pid)["revisione"]
    with pytest.raises(DatiNonValidi, match="solo nei quadri EC"):
        sv.agevolazione_applica(pid, rev, "P", ["b_terr0001"], ["p_anna0001"])
    with pytest.raises(DatiNonValidi, match="non proposto"):
        sv.agevolazione_applica(pid, rev, "Y", ["b_casa0001"], ["p_anna0001"])
    with pytest.raises(DatiNonValidi, match="nessuna riga di devoluzione"):
        sv.agevolazione_applica(pid, rev, "R", ["b_terr0001"], ["p_luca0001"])
    with pytest.raises(DatiNonValidi, match="almeno un bene"):
        sv.agevolazione_applica(pid, rev, "P", [], ["p_anna0001"])
    assert sv.leggi(pid)["revisione"] == rev


def test_api_web_griglia_e_agevolazioni(tmp_path):
    from starlette.testclient import TestClient
    from successioni.web import crea_app
    sv, pid = _servizio(tmp_path)
    c = TestClient(crea_app(sv, token="tok123", ammetti_host_di_prova=True), base_url="http://testserver")
    c.get("/", params={"t": "tok123"})
    g = c.get(f"/api/pratiche/{pid}/quote-griglia").json()
    r = c.post(f"/api/pratiche/{pid}/quote-griglia", json={"revisione_attesa": g["revisione"], "celle": [
        {"bene_id": "b_casa0001", "persona_id": "p_anna0001", "diritto": "1", "quota": "1/3"}]})
    assert r.status_code == 200 and r.json()["modifiche"] == 1
    bad = c.post(f"/api/pratiche/{pid}/quote-griglia", json={"revisione_attesa": r.json()["revisione"], "celle": []})
    assert bad.status_code == 422 and "celle" in bad.text
    a = c.get(f"/api/pratiche/{pid}/agevolazioni-guidate").json()
    r2 = c.post(f"/api/pratiche/{pid}/agevolazioni-guidate", json={"revisione_attesa": a["revisione"], "codice": "P",
                                                                   "beni": ["b_casa0001"], "persone": ["p_luca0001"]})
    assert r2.status_code == 200 and r2.json()["cambiate"] == 1
    t = c.get(f"/api/pratiche/{pid}/termine")
    assert t.status_code == 200 and t.json()["termine"]["base"] == "decesso"


def test_termine_della_pratica_aperta(tmp_path):
    from datetime import date
    from successioni import cruscotto as CRU
    sv, pid = _servizio(tmp_path)
    decesso = next(p["data_decesso"] for p in sv.leggi(pid)["dati"]["persone"] if p["ruolo"] == "defunto")
    t = CRU.termine_pratica(sv, pid, oggi=date(2026, 11, 15))["termine"]
    assert t == CRU._termine(decesso, date(2026, 11, 15)) and t["base"] == "decesso"
