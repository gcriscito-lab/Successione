"""Albero genealogico generato dai dati (quadro EG, rigo EG6). Dati SINTETICI.

Fonti: Fascicolo I p. PDF 6 «Quali documenti occorrono» (nome, cognome, luogo e data di nascita del coniuge e dei beneficiari
parenti) e p. PDF 49 (rigo EG6 obbligatorio, PDF/A); XSD QuadroEG/AlberoGenealogico (un solo documento). docs/regole/albero_genealogico.md
"""
from datetime import date

import pytest
from pypdf import PdfReader
from starlette.testclient import TestClient

from successioni import albero_genealogico as AG
from successioni import pdfa
from successioni.archivio import Archivio
from successioni.errori import DatiNonValidi
from successioni.servizio import Servizio
from successioni.web import crea_app
from test_pdfa import crea_pdf

gs_ok = pytest.mark.skipif(not pdfa.trova_gs() or not pdfa._icc(), reason="Ghostscript non disponibile")
OGGI = date(2026, 11, 7)


def P(i, **c):
    return {"op": "upsert", "coll": "persone", "id": i, "campi": c}


DEFUNTO = P("p_def0001", ruolo="defunto", cognome="Sintetico", nome="Mario", luogo_nascita="Roma", data_nascita="1940-01-01",
            data_decesso="2025-03-10", codice_fiscale="SNTMRA40A01H501X")
DICH = P("p_dic0001", ruolo="presentatore", cognome="Dichiarante", nome="Carla", codice_fiscale="DCHCRL60A41H501Z")


def figlio(i, nome, **k):
    return P(i, ruolo="erede", cognome="Sintetico", nome=nome, luogo_nascita="Roma", data_nascita="1970-02-02",
             grado_parentela="02", tipo_soggetto="1", **k)


CONIUGE = P("p_con0001", ruolo="erede", cognome="Coniugata", nome="Anna", luogo_nascita="Milano", data_nascita="1945-05-05",
            grado_parentela="01", sesso="F", tipo_soggetto="1")


def modello(*persone):
    sv_dati = {"persone": [dict(op["campi"], id=op["id"]) for op in persone], "opzioni": {}}
    return AG.costruisci(sv_dati, oggi=OGGI)


def pdf_testo(m, tmp_path):
    f = tmp_path / "a.pdf"
    AG.genera_pdf(m, f)
    return "\n".join(pg.extract_text() for pg in PdfReader(f).pages)


def test_figli(tmp_path):
    m = modello(DEFUNTO, figlio("p_fig0001", "Luca"), figlio("p_fig0002", "Sara", sesso="F"), DICH)
    assert [n["nome"] for n in m["rami"]["discendenti"]] == ["Luca", "Sara"]
    assert m["coniugi"] == [] and m["mancanti"] == []
    t = pdf_testo(m, tmp_path)
    for s in ("Sintetico Mario", "Sintetico Luca", "Sintetico Sara", "nata a Roma il 02/02/1970", "02 - Figlio/a",
              "Redatto il 07/11/2026", "Dichiarante Carla", "deceduto/a il 10/03/2025", "nessun coniuge"):
        assert s in t, s


def test_coniuge_e_figli(tmp_path):
    m = modello(DEFUNTO, CONIUGE, figlio("p_fig0001", "Luca"), DICH)
    assert [n["nome"] for n in m["coniugi"]] == ["Anna"]
    assert m["rami"]["discendenti"][0]["nome"] == "Luca"
    t = pdf_testo(m, tmp_path)
    assert "CONIUGE" in t and "Coniugata Anna" in t and "nata a Milano il 05/05/1945" in t


def test_rappresentazione_premorto(tmp_path):
    m = modello(DEFUNTO, figlio("p_fig0001", "Luca"),
                P("p_pre0001", ruolo="altro", cognome="Sintetico", nome="Paolo", codice_fiscale="SNTPLA72B02H501X",
                  luogo_nascita="Roma", data_nascita="1972-02-02", data_decesso="2020-01-01"),
                P("p_nip0001", ruolo="erede", cognome="Sintetico", nome="Giulia", luogo_nascita="Napoli", data_nascita="1995-03-03",
                  grado_parentela="04", tipo_soggetto="1", rappresentato_cf="SNTPLA72B02H501X", rappresentato_grado="02"),
                DICH)
    disc = m["rami"]["discendenti"]
    assert [n["nome"] for n in disc] == ["Luca", "Paolo"]
    paolo = disc[1]
    assert paolo["rappresentato"] and paolo["qualita"] == "premorto/a il 01/01/2020"
    assert [f["nome"] for f in paolo["figli"]] == ["Giulia"]
    t = pdf_testo(m, tmp_path)
    assert "premorto/a il 01/01/2020" in t and "succede per rappresentazione di Sintetico Paolo" in t


def test_rappresentato_senza_dati_non_inventa(tmp_path):
    m = modello(DEFUNTO, P("p_nip0001", ruolo="erede", cognome="Sintetico", nome="Giulia", luogo_nascita="Napoli",
                           data_nascita="1995-03-03", grado_parentela="04", tipo_soggetto="1",
                           rappresentato_cf="SNTPLA72B02H501X", rappresentato_grado="02"))
    capo = m["rami"]["discendenti"][0]
    assert capo["cognome"] is None and capo["codice_fiscale"] == "SNTPLA72B02H501X"
    assert "non indicato" in capo["qualita"]
    t = pdf_testo(m, tmp_path)
    assert "SNTPLA72B02H501X" in t and "dati anagrafici del rappresentato non presenti" in t


def test_fratelli_e_nipoti_di_fratello(tmp_path):
    m = modello(DEFUNTO,
                P("p_fra0001", ruolo="erede", cognome="Sintetico", nome="Bruno", luogo_nascita="Roma", data_nascita="1942-01-01",
                  grado_parentela="10", tipo_soggetto="1"),
                P("p_sor0001", ruolo="erede", cognome="Sintetico", nome="Lia", luogo_nascita="Roma", data_nascita="1944-01-01",
                  grado_parentela="11", tipo_soggetto="1", sesso="F"),
                P("p_nif0001", ruolo="erede", cognome="Sintetico", nome="Ugo", luogo_nascita="Bari", data_nascita="1980-01-01",
                  grado_parentela="15", tipo_soggetto="1", rappresentato_cf="SNTGNN45A01H501X", rappresentato_grado="10"))
    coll = m["rami"]["collaterali"]
    assert [n["nome"] or n["codice_fiscale"] for n in coll] == ["Bruno", "Lia", "SNTGNN45A01H501X"]
    assert coll[2]["figli"][0]["nome"] == "Ugo"
    t = pdf_testo(m, tmp_path)
    assert "Fratelli, sorelle" in t and "10 - Fratello/sorella germano" in t and "Sintetico Ugo" in t


def test_rinunciatario_e_suoi_rappresentanti(tmp_path):
    rin = figlio("p_rin0001", "Dario", codice_fiscale="SNTDRA70B02H501X")
    rin["campi"].update(tipo_soggetto="3", rinuncia=True)
    m = modello(DEFUNTO, figlio("p_fig0001", "Luca"), rin,
                P("p_nip0001", ruolo="erede", cognome="Sintetico", nome="Ivo", luogo_nascita="Roma", data_nascita="2000-01-01",
                  grado_parentela="04", tipo_soggetto="1", rappresentato_cf="SNTDRA70B02H501X", rappresentato_grado="02"))
    disc = m["rami"]["discendenti"]
    dario = next(n for n in disc if n["nome"] == "Dario")
    assert dario["qualita"] == "rinunciatario/a all'eredita'" and [f["nome"] for f in dario["figli"]] == ["Ivo"]
    t = pdf_testo(m, tmp_path)
    assert "rinunciatario/a all'eredita'" in t and "Sintetico Ivo" in t


def test_dati_mancanti_dichiarati(tmp_path):
    m = modello(P("p_def0001", ruolo="defunto", cognome="Sintetico", nome="Mario"),
                P("p_ere0001", ruolo="erede", cognome="Senzadati", nome="Eva"),
                P("p_leg0001", ruolo="legatario", denominazione="Ente Sintetico"))
    manc = {x["soggetto"]: x["dati"] for x in m["mancanti"]}
    assert manc["Sintetico Mario"] == ["luogo di nascita", "data di nascita", "data del decesso"]
    assert manc["Senzadati Eva"] == ["luogo di nascita", "data di nascita", "grado di parentela"]
    assert "Ente Sintetico" not in manc                     # ente: nessun dato di nascita richiesto
    assert m["dichiarante"] is None
    t = pdf_testo(m, tmp_path)
    assert "Dati da completare" in t and "non indicato nella pratica" in t
    assert "dichiarante: non indicato" in t
    assert "1940" not in t                                   # nessuna data inventata


def test_senza_defunto_rifiuta():
    with pytest.raises(DatiNonValidi):
        AG.costruisci({"persone": [{"id": "p_x", "ruolo": "erede", "cognome": "A"}]})


def _pratica(tmp_path, *extra):
    sv = Servizio(Archivio(tmp_path / "d"))
    pid = sv.crea_pratica("Albero", iniziali=[DEFUNTO, CONIUGE, figlio("p_fig0001", "Luca"), DICH, *extra])["pratica_id"]
    return sv, pid


def _eg6(sv, pid):
    return [r for r in sv.leggi(pid)["dati"]["documenti_ref"] if r["tipo_eg"] == "AlberoGenealogico"]


def test_genera_collega_rigo_eg6_e_rigenera(tmp_path):
    sv, pid = _pratica(tmp_path)
    r = sv.genera_albero_genealogico(pid, oggi=OGGI)
    assert r["esito"] == "generato" and len(_eg6(sv, pid)) == 1
    assert _eg6(sv, pid)[0]["allegato_id"] == r["allegato_id"]
    dati, _ = sv.file_allegato(r["allegato_id"])
    assert dati[:5] == b"%PDF-"
    # dati invariati: nessuna nuova versione
    assert sv.genera_albero_genealogico(pid)["esito"] == "gia_aggiornato"
    assert sv.stato_albero_genealogico(pid)["aggiornato"] is True
    # dati modificati: l'albero risulta da rigenerare; la rigenerazione sostituisce il file e toglie il precedente
    rev = sv.leggi(pid)["revisione"]
    sv.aggiorna(pid, rev, [figlio("p_fig0002", "Nuova")])
    assert sv.stato_albero_genealogico(pid)["aggiornato"] is False
    r2 = sv.genera_albero_genealogico(pid, oggi=OGGI)
    assert r2["esito"] == "generato" and r2["allegato_id"] != r["allegato_id"]
    assert [x["allegato_id"] for x in _eg6(sv, pid)] == [r2["allegato_id"]]
    ids = {a["id"] for a in sv.elenca_allegati(pid)}
    assert r["allegato_id"] not in ids and r2["allegato_id"] in ids
    assert all((a["analisi"] or {}).get("generato") for a in sv.elenca_allegati(pid))
    dati2, _ = sv.file_allegato(r2["allegato_id"])
    (tmp_path / "x.pdf").write_bytes(dati2)
    t = "\n".join(pg.extract_text() for pg in PdfReader(tmp_path / "x.pdf").pages)
    assert "Sintetico Nuova" in t and "Coniugata Anna" in t


def test_albero_manuale_non_si_sostituisce_senza_conferma(tmp_path):
    sv, pid = _pratica(tmp_path)
    crea_pdf(sv.cartella_ingresso / "albero_studio.pdf", 1)
    a = sv.acquisisci_da_ingresso(pid, "albero_studio.pdf", tipo_eg="AlberoGenealogico")
    sv.aggiorna(pid, sv.leggi(pid)["revisione"], [{"op": "upsert", "coll": "documenti_ref", "id": "dr_manuale1",
                                                   "campi": {"allegato_id": a["allegato_id"], "tipo_eg": "AlberoGenealogico"}}])
    rev = sv.leggi(pid)["revisione"]
    r = sv.genera_albero_genealogico(pid)
    assert r["esito"] == "conferma_richiesta" and r["manuali"][0]["allegato_id"] == a["allegato_id"]
    assert sv.leggi(pid)["revisione"] == rev and len(sv.elenca_allegati(pid)) == 1      # nulla cambiato
    r = sv.genera_albero_genealogico(pid, sostituisci_manuale=True, oggi=OGGI)
    assert r["esito"] == "generato"
    assert [x["allegato_id"] for x in _eg6(sv, pid)] == [r["allegato_id"]]
    assert a["allegato_id"] in {x["id"] for x in sv.elenca_allegati(pid)}             # il file manuale resta


def test_web_e_anteprima(tmp_path):
    sv, pid = _pratica(tmp_path)
    c = TestClient(crea_app(sv, token="tk", ammetti_host_di_prova=True))
    h = {"x-successioni-token": "tk"}
    st = c.get(f"/api/pratiche/{pid}/albero-genealogico", headers=h).json()
    assert st["righi_eg6"] == [] and st["modello"]["defunto"]["nome"] == "Mario"
    r = c.post(f"/api/pratiche/{pid}/albero-genealogico", headers=h, json={}).json()
    assert r["esito"] == "generato"
    f = c.get(f"/api/allegati/{r['allegato_id']}/file", headers=h)
    assert f.status_code == 200 and f.headers["content-type"] == "application/pdf" and f.content[:5] == b"%PDF-"
    assert c.get(f"/api/allegati/{r['allegato_id']}/file").status_code == 401


@gs_ok
def test_pdfa_valido(tmp_path):
    sv, pid = _pratica(tmp_path)
    r = sv.genera_albero_genealogico(pid, oggi=OGGI)
    assert r["pdfa"] is True
    riga = next(a for a in sv.elenca_allegati(pid) if a["id"] == r["allegato_id"])
    assert riga["ruolo"] == "derivato"
    if not pdfa.trova_verapdf():
        pytest.skip("veraPDF non configurato: conformita' PDF/A non verificabile")
    assert r["validazione"] == "conforme"
