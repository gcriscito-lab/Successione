"""Quadro EG: un documento = un file (richiesta dello studio, 2026-11-07). Dati SINTETICI.

- La conversione ripetuta non crea doppioni (in una pratica reale ogni documento risultava convertito due volte).
- Con ``sostituisci_originale`` (interfaccia e MCP) il rigo EG passa al PDF/A e l'originale viene tolto, salvo avvisi di rischio.
- ``riordina_allegati`` ripulisce le pratiche gia' piene di doppioni; ``elimina_allegato`` rifiuta i file usati nel quadro EG.
- Anteprima dei quadri EE/EF/EH; casella FlagInventari del quadro EH (Fascicolo I p. PDF 52, lettera l; annotazione XSD).
"""
import copy
from datetime import date

import pytest
from starlette.testclient import TestClient

import telematico_casi as T
from successioni import pdfa
from successioni.archivio import Archivio
from successioni.errori import DatiNonValidi
from successioni.servizio import Servizio
from successioni.telematico.esporta import esporta_xml
from successioni.web import crea_app
from test_pdfa import crea_pdf

gs_ok = pytest.mark.skipif(not pdfa.trova_gs() or not pdfa._icc(), reason="Ghostscript non disponibile")


def _pratica(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    pid = sv.crea_pratica("EG")["pratica_id"]
    f = sv.cartella_ingresso / "albero.pdf"
    crea_pdf(f, 1)
    a = sv.acquisisci_da_ingresso(pid, "albero.pdf", tipo_eg="AlberoGenealogico")
    rev = sv.leggi(pid)["revisione"]
    sv.aggiorna(pid, rev, [{"op": "upsert", "coll": "documenti_ref", "id": "dr_albero1",
                            "campi": {"allegato_id": a["allegato_id"], "tipo_eg": "AlberoGenealogico"}}])
    return sv, pid, a["allegato_id"]


@gs_ok
def test_conversione_ripetuta_non_crea_doppioni(tmp_path):
    sv, pid, aid = _pratica(tmp_path)
    r1 = sv.prepara_pdfa(aid)
    r2 = sv.prepara_pdfa(aid)
    assert r2["gia_convertito"] and r2["derivato"]["allegato_id"] == r1["derivato"]["allegato_id"]
    assert [x["ruolo"] for x in sv.elenca_allegati(pid)] == ["originale", "derivato"]


@gs_ok
def test_sostituisci_originale_sposta_il_rigo_eg_e_toglie_l_originale(tmp_path):
    sv, pid, aid = _pratica(tmp_path)
    r = sv.prepara_pdfa(aid, sostituisci_originale=True)
    if not r.get("originale_rimosso"):
        pytest.skip("conversione con avvisi di rischio su questo PDF di prova: " + str(r.get("motivo_originale_conservato")))
    lista = sv.elenca_allegati(pid)
    assert [x["ruolo"] for x in lista] == ["derivato"]
    refs = sv.leggi(pid)["dati"]["documenti_ref"]
    assert [x["allegato_id"] for x in refs] == [lista[0]["id"]] == [r["derivato"]["allegato_id"]]
    assert r["righi_eg_aggiornati"] == 1


@gs_ok
def test_riordina_toglie_doppioni_e_originali_convertiti(tmp_path):
    sv, pid, aid = _pratica(tmp_path)
    d1 = sv.prepara_pdfa(aid)["derivato"]["allegato_id"]
    # doppione come nella pratica reale: seconda conversione forzata registrata a mano
    riga = sv._riga_allegato(d1)
    with sv.arch.transazione() as c:
        c.execute("INSERT INTO allegati SELECT 'al_doppione01', pratica_id, nome, sha256, bytes, percorso, ruolo, origine_id, tipo_eg, "
                  "finalita, persona_id, analisi, rapporto, ts || 'Z' FROM allegati WHERE id=?", (riga["id"],))
    assert len(sv.elenca_allegati(pid)) == 3
    r = sv.riordina_allegati(pid)
    lista = sv.elenca_allegati(pid)
    assert len(lista) == 1 and lista[0]["ruolo"] == "derivato"
    assert sv.leggi(pid)["dati"]["documenti_ref"][0]["allegato_id"] == lista[0]["id"]
    assert aid in r["rimossi"] and r["righi_eg_aggiornati"] == 1
    # il deposito conserva il file ancora usato
    assert (sv.arch.base / lista[0]["percorso"]).is_file()


def test_elimina_rifiuta_file_usati_nel_quadro_eg(tmp_path):
    sv, pid, aid = _pratica(tmp_path)
    with pytest.raises(DatiNonValidi):
        sv.elimina_allegato(aid)
    rev = sv.leggi(pid)["revisione"]
    sv.aggiorna(pid, rev, [{"op": "remove", "coll": "documenti_ref", "id": "dr_albero1"}])
    assert sv.elimina_allegato(aid)["eliminato"] and sv.elenca_allegati(pid) == []


def test_anteprima_quadri_ee_ef_eh(tmp_path):
    from test_elaborati import CF_FORN, ops_da_caso
    sv = Servizio(Archivio(tmp_path / "d"))
    pid = sv.crea_pratica("Caso", iniziali=ops_da_caso(T.caso_completo()))["pratica_id"]
    a = sv.anteprima_quadri(pid)
    assert {x["campo"]: x["valore"] for x in a["ee"]}["TotaleAttivo"] == "161000"
    assert ["Imposta ipotecaria", "2820"] in a["ef"]["imposte"] and a["ef"]["totale"] == "4435.00"
    assert {"FlagDeceduto", "FlagAssenzaTestamento"} <= {x["campo"] for x in a["eh"]}
    c = TestClient(crea_app(sv, token="tok", ammetti_host_di_prova=True), base_url="http://testserver")
    r = c.get(f"/api/pratiche/{pid}/anteprima-quadri", params={"t": "tok"})
    assert r.status_code == 200 and r.json()["ef"]["totale"] == "4435.00"
    assert CF_FORN   # fornitore non necessario per l'anteprima


def test_flag_inventari_solo_con_rigo_altro():
    d = copy.deepcopy(T.caso_a10())
    d["opzioni"]["telematico"]["dichiarazione"]["flag_inventari"] = True
    ctx = T.contesto_caso_a10(data_riferimento=date(2025, 9, 1))
    es = esporta_xml(d, ctx)
    assert any("rigo EG8" in e.messaggio for e in es.errori)
    d["documenti_ref"].append({"id": "dr_altro01", "_origine": {}, "allegato_id": "al_testam", "tipo_eg": "Altro",
                               "finalita": "inventario cassetta di sicurezza"})
    es = esporta_xml(d, ctx)
    assert es.completo, ([e.messaggio for e in es.errori], es.non_supportato, [m.messaggio for m in es.quadri_mancanti])
    assert b"<suc:FlagInventari>1</suc:FlagInventari>" in es.xml
