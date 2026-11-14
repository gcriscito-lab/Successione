"""Immobili dal PDF delle «Risultanze catastali» di Entratel (14/11/2026). Dati SINTETICI: i PDF di prova sono generati da
tests/fixture_catasto/genera_risultanze.js con la stessa impaginazione della pagina di Entratel salvata dal browser, con
codice fiscale e immobili inventati."""
from pathlib import Path

import pytest
from starlette.testclient import TestClient

import telematico_casi as T
from successioni import anonimizza as AN
from successioni.archivio import Archivio
from successioni.collegamenti import catasto as K
from successioni.collegamenti import visura_pdf as VP
from successioni.errori import DatiNonValidi
from successioni.servizio import Servizio
from successioni.web import crea_app

CARTELLA = Path(__file__).parent / "fixture_catasto"
FABBRICATI = (CARTELLA / "risultanze_fabbricati_sintetico.pdf").read_bytes()
TERRENI = (CARTELLA / "risultanze_terreni_sintetico.pdf").read_bytes()
CODICI = {"ROMA": ("H501", "RM"), "TIVOLI": ("L182", "RM")}


def _comune(nome, sigla):
    return CODICI.get(nome, (None, sigla))


@pytest.fixture(autouse=True)
def _comuni_senza_componente(monkeypatch):
    # il codice catastale dal nome usa le tabelle del componente ufficiale: nelle prove si sostituiscono con un elenco fisso
    monkeypatch.setattr(VP, "_cerca_comune_ufficiale", _comune)


def test_fabbricati_letti_colonna_per_colonna():
    r = VP.leggi(FABBRICATI)
    assert (r["catasto"], r["codice_fiscale"], r["provincia"], r["aggiornamento"]) == ("F", T.CF_DEFUNTO, "ROMA", "09/11/2026")
    assert r["segnalazioni"] == [] and len(r["immobili"]) == 4
    a, b, c, d = r["immobili"]
    # titolarita' su due righe, subalterno e zona assenti: le colonne vuote restano vuote
    assert (a["foglio"], a["particella"], a.get("subalterno"), a.get("zona")) == ("17", "41", None, None)
    assert a["titolarita"][0]["quota"] == {"num": 7, "den": 200} and a["titolarita"][0]["diritto"] == "1"
    assert (a["categoria"], a["classe"], a["consistenza"], a["rendita"]) == ("A/4", "02", "2.5", "61.30")
    # zona e categoria impilate, importo su due righe, esponente del m² che non diventa la consistenza
    assert (b["subalterno"], b["zona"], b["categoria"], b["consistenza"], b["unita_consistenza"], b["rendita"]) == \
        ("12", "1", "C/6", "18", "m²", "143.10")
    assert b["codice_comune"] == "H501" and b["provincia"] == "RM" and b["indirizzo"] == "VICOLO ESEMPIO Piano S2"
    # sezione, nuda proprieta', usufrutto, migliaia
    assert (c["sezione"], c["titolarita"][0]["diritto"], c["titolarita"][0]["quota"], c["rendita"]) == \
        ("A", "2", {"num": 1, "den": 2}, "1512.40")
    assert d["titolarita"][0]["diritto"] == "8" and d["codice_comune"] == "L182"
    assert any("sola provincia di ROMA" in x for x in r["limiti"]) and any("non alla data del decesso" in x for x in r["limiti"])


def test_terreni_con_reddito_e_deduzioni():
    r = VP.leggi(TERRENI)
    assert r["catasto"] == "T" and len(r["immobili"]) == 3
    a, b, c = r["immobili"]
    assert (a["qualita"], a["classe"], a["superficie"], a["reddito_dominicale"], a["reddito_agrario"]) == \
        ("CAST FRUTTO", "04", "740", "0.31", "0.52")
    assert b["reddito_dominicale"] == "8.12" and b["reddito_dominicale_con_deduzioni"] is True
    assert c["classe"] == "U" and c["titolarita"][0]["quota"] == {"num": 1, "den": 1}


def test_pdf_non_riconosciuti():
    with pytest.raises(DatiNonValidi):
        VP.leggi(b"non un pdf")
    altro = (Path(__file__).parent / "fixture_telematico" / "allegati" / "albero_genealogico.pdf").read_bytes()
    with pytest.raises(DatiNonValidi, match="Risultanze catastali"):
        VP.leggi(altro)


def _servizio(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    pid = sv.crea_pratica("Successione ROSSI MARIO", iniziali=AN.operazioni(T.caso_completo()))["pratica_id"]
    return sv, pid


def test_carica_proponi_e_applica_senza_doppioni(tmp_path):
    sv, pid = _servizio(tmp_path)
    beni_prima = len(sv.leggi(pid)["dati"]["beni"])
    st = sv.visura_carica(pid, FABBRICATI, nome="fabbricati.pdf")
    st = sv.visura_carica(pid, TERRENI, nome="terreni.pdf")            # i due PDF si sommano
    assert len(st["immobili"]) == 7 and len(st["file"]) == 2 and st["avvisi"] == []
    assert {i["esito"] for i in st["immobili"]} == {"nuovi"}
    codici = {s["codice"] for s in st["proposta"]["segnalazioni"]}
    assert "SITUAZIONE_AL_DECESSO" in codici and "LIMITE_DEL_SERVIZIO" in codici
    scelti = [i["chiave"] for i in st["immobili"] if i["catasto"] == "F"][:2] + \
             [i["chiave"] for i in st["immobili"] if i["catasto"] == "T"][:1]
    rev = sv.leggi(pid)["revisione"]
    r = sv.visura_applica(pid, rev, scelti, chiave="visura-1")
    assert r["applicate"] == 3
    p = sv.leggi(pid)
    beni = p["dati"]["beni"]
    assert len(beni) == beni_prima + 3
    nuovo = next(b for b in beni if b.get("foglio") == "28" and b.get("particella") == "777")
    assert (nuovo["tipo"], nuovo["categoria"], nuovo["rendita"], nuovo["classe"], nuovo["zona_censuaria"],
            nuovo["codice_comune"]) == ("fabbricato", "C/6", "143.10", "04", "1", "H501")
    assert nuovo["quota_defunto"] == {"num": 1, "den": 1} and nuovo["_origine"]["foglio"] == "acquisito"
    terreno = next(b for b in beni if b.get("foglio") == "12" and b.get("particella") == "301")
    assert terreno["tipo"] == "terreno" and terreno["reddito_dominicale"] == "0.31"
    # stessa scelta di nuovo: nessun bene in piu'
    st = sv.visura_stato(pid)
    assert {i["esito"] for i in st["immobili"] if i["chiave"] in scelti} == {"invariati"}
    sv.visura_applica(pid, p["revisione"], scelti, chiave="visura-2")
    assert len(sv.leggi(pid)["dati"]["beni"]) == beni_prima + 3


def test_serve_il_codice_fiscale_del_defunto_e_un_pdf(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    pid = sv.crea_pratica("Vuota")["pratica_id"]
    with pytest.raises(DatiNonValidi, match="codice fiscale del defunto"):
        sv.visura_carica(pid, FABBRICATI)
    sv2, pid2 = _servizio(tmp_path / "b")
    with pytest.raises(DatiNonValidi, match="PDF"):
        sv2.visura_carica(pid2, b"testo")
    assert sv2.visura_stato(pid2)["job_id"] is None
    with pytest.raises(DatiNonValidi, match="nessuna visura"):
        sv2.visura_applica(pid2, 1, ["x"])


def test_pdf_non_riconosciuto_resta_conservato(tmp_path):
    ad = K.CatastoEntratelAdattatore(Archivio(tmp_path / "d"))
    r = ad.avvia("pr_1", {"soggetto_cf": T.CF_DEFUNTO})
    altro = (Path(__file__).parent / "fixture_telematico" / "allegati" / "albero_genealogico.pdf").read_bytes()
    r = ad.registra_originale(r.job_id, altro, formato="pdf", fonte="altro.pdf")
    assert r.stato == K.ATTESA_UTENTE and len(r.artefatti) == 1 and "non riconosciuto" in r.azione_richiesta


def test_api_carica_stato_applica(tmp_path):
    sv, pid = _servizio(tmp_path)
    cl = TestClient(crea_app(sv, token="tok123", ammetti_host_di_prova=True), base_url="http://testserver")
    cl.get("/", params={"t": "tok123"})
    assert cl.get(f"/api/pratiche/{pid}/visure").json()["immobili"] == []
    r = cl.post(f"/api/pratiche/{pid}/visure", params={"nome": "fabbricati.pdf"}, content=FABBRICATI)
    assert r.status_code == 200 and len(r.json()["immobili"]) == 4
    chiave = r.json()["immobili"][0]["chiave"]
    r = cl.post(f"/api/pratiche/{pid}/visure/applica",
                json={"revisione_attesa": sv.leggi(pid)["revisione"], "selezione": [chiave], "chiave": "api-1"})
    assert r.status_code == 200 and r.json()["applicate"] == 1


# ------------------------------------------------------------------ piccole comodita' (14/11/2026)
def test_duplica_pratica_conserva_dati_e_origini(tmp_path):
    sv, pid = _servizio(tmp_path)
    sv.visura_carica(pid, FABBRICATI)
    st = sv.visura_stato(pid)
    sv.visura_applica(pid, sv.leggi(pid)["revisione"], [st["immobili"][0]["chiave"]])
    orig = sv.leggi(pid)["dati"]
    r = sv.duplica_pratica(pid, "Sostitutiva", chiave="dup-1")
    assert r["titolo"] == "Sostitutiva" and r["pratica_id"] != pid and "preventivo e parcella" in r["non_copiati"]
    assert sv.duplica_pratica(pid, "Sostitutiva", chiave="dup-1")["ripetuta"] is True
    copia = sv.leggi(r["pratica_id"])["dati"]
    assert copia["beni"] == orig["beni"] and copia["persone"] == orig["persone"]      # origini comprese
    assert any(b["_origine"].get("foglio") == "acquisito" for b in copia["beni"])
    assert copia["documenti_ref"] == []
    assert sv.duplica_pratica(pid)["titolo"].startswith("Copia di ")


def test_ordina_righe_e_beni_per_comune_e_foglio(tmp_path):
    sv, pid = _servizio(tmp_path)
    st = sv.visura_carica(pid, FABBRICATI)
    sv.visura_applica(pid, sv.leggi(pid)["revisione"], [i["chiave"] for i in st["immobili"]])
    p = sv.leggi(pid)
    ids = [b["id"] for b in p["dati"]["beni"]]
    # sposta l'ultima riga in cima
    sv.aggiorna(pid, p["revisione"], [{"op": "ordina", "coll": "beni", "ids": [ids[-1]] + ids[:-1]}])
    assert [b["id"] for b in sv.leggi(pid)["dati"]["beni"]] == [ids[-1]] + ids[:-1]
    with pytest.raises(DatiNonValidi, match="una sola volta"):
        sv.aggiorna(pid, sv.leggi(pid)["revisione"], [{"op": "ordina", "coll": "beni", "ids": ids[:-1]}])
    sv.ordina_beni(pid, sv.leggi(pid)["revisione"], "EC")
    ec = [b for b in sv.leggi(pid)["dati"]["beni"] if b.get("tipo") == "fabbricato"]
    chiavi = [(b.get("comune") or "", b.get("sezione") or "", int(b["foglio"]), int(b["particella"])) for b in ec]
    assert chiavi == sorted(chiavi)
    with pytest.raises(DatiNonValidi, match="nessun bene"):
        sv.ordina_beni(pid, sv.leggi(pid)["revisione"], "EQ")
