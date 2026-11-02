"""Test di regressione dei rilievi della revisione indipendente (R1, R2, R3, R4, R6, R8, R9). Dati sintetici."""
import json
import sys
from pathlib import Path

import pytest
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent))
from successioni.archivio import Archivio
from successioni.errori import DatiNonValidi
from successioni.servizio import Servizio
from successioni.web import crea_app


@pytest.fixture
def sv(tmp_path):
    return Servizio(Archivio(tmp_path / "d"))


def up(coll, id=None, **campi):
    return {"op": "upsert", "coll": coll, **({"id": id} if id else {}), "campi": campi}


def test_r4_id_non_modificabile_da_campi(sv):
    pid = sv.crea_pratica("X")["pratica_id"]
    sv.aggiorna(pid, 1, [up("persone", "p_aaaa1111", cognome="A"), up("persone", "p_bbbb2222", cognome="B")])
    for canale in ("gui", "mcp"):
        with pytest.raises(DatiNonValidi):
            sv.aggiorna(pid, 2, [{"op": "upsert", "coll": "persone", "id": "p_aaaa1111", "campi": {"id": "p_bbbb2222"}}], canale=canale)
    assert [e["id"] for e in sv.leggi(pid)["dati"]["persone"]] == ["p_aaaa1111", "p_bbbb2222"]


def test_r3_origine_non_aggirabile_da_campi(sv):
    pid = sv.crea_pratica("X")["pratica_id"]
    sv.aggiorna(pid, 1, [up("persone", "p_aaaa1111", cognome="A")])
    with pytest.raises(DatiNonValidi):
        sv.aggiorna(pid, 2, [up("persone", "p_aaaa1111", _origine={})], canale="mcp")
    with pytest.raises(DatiNonValidi):                       # prima: TypeError non gestito
        sv.aggiorna(pid, 2, [up("persone", "p_aaaa1111", _origine="x")], canale="mcp")


def test_r2_sostitutiva_non_finalizzabile(sv):
    pid = sv.crea_pratica("X")["pratica_id"]
    sv.aggiorna(pid, 1, [{"op": "set", "sezione": "opzioni", "campi": {"tipo_dichiarazione": "sostitutiva"}}])
    v = sv.verifica(pid)
    assert not v["finalizzabile"]
    assert "SOSTITUTIVA_NON_SUPPORTATA" in [r["codice"] for r in v["rilievi"]]


def test_r1_finalizzabile_richiede_file_xml_completo(sv):
    from test_elaborati import ops_da_caso
    from telematico_casi import caso_completo
    pid = sv.crea_pratica("X", iniziali=ops_da_caso(caso_completo()))["pratica_id"]
    q = sv.quadri(pid)
    assert q["esito"] == "ok" or q["rilievi"] is not None
    assert q["finalizzabile"] is False                         # nessun file completo e aggiornato: non finalizzabile
    assert any(b["codice"] == "FILE_XML_COMPLETO_NON_DISPONIBILE" for b in sv.verifica(pid)["blocchi_finalizzazione"])


def test_r6_backup_include_elaborati_e_ripristino(sv, tmp_path):
    from test_elaborati import ops_da_caso
    from telematico_casi import caso_completo
    pid = sv.crea_pratica("X", iniziali=ops_da_caso(caso_completo()))["pratica_id"]
    r = sv.esporta(pid, cf_fornitore="RSSNNA70A41H501X", scopo="bozza_tecnica")
    dest = sv.arch.backup(tmp_path / "bk")
    assert (dest / r["percorso"]).read_bytes() == (sv.arch.base / r["percorso"]).read_bytes()
    nuovo = Archivio(tmp_path / "ripristinato")
    nuovo.ripristina(dest)
    sv2 = Servizio(nuovo)
    assert sv2.leggi(pid) == sv.leggi(pid)
    assert (nuovo.base / r["percorso"]).exists()
    st = sv2.stato_elaborati(pid)
    assert st["export"]["stato"] == "aggiornato"


def test_r6_ripristino_non_sovrascrive_archivio_non_vuoto(sv, tmp_path):
    sv.crea_pratica("X")
    dest = sv.arch.backup(tmp_path / "bk")
    from successioni.errori import RipristinoNonAmmesso
    with pytest.raises(RipristinoNonAmmesso):
        sv.arch.ripristina(dest)                               # destinazione con dati: rifiutato
    with pytest.raises(RipristinoNonAmmesso):
        Archivio(tmp_path / "vuota").ripristina(tmp_path / "non_un_backup")


def test_r8_date_impossibili_rifiutate(sv):
    pid = sv.crea_pratica("X")["pratica_id"]
    with pytest.raises(DatiNonValidi):
        sv.aggiorna(pid, 1, [up("persone", "p_aaaa1111", data_nascita="2025-02-30")])
    sv.aggiorna(pid, 1, [up("persone", "p_aaaa1111", data_nascita="2024-02-29")])


def test_r9_json_malformato_422_e_host_di_prova_non_ammesso(tmp_path):
    s = Servizio(Archivio(tmp_path / "d"))
    app = crea_app(s, token="T")
    c = TestClient(app, base_url="http://testserver")
    assert c.get("/api/pratiche", params={"t": "T"}).status_code == 403          # 'testserver' non ammesso di default
    app2 = crea_app(s, token="T", ammetti_host_di_prova=True)
    c2 = TestClient(app2, base_url="http://testserver")
    assert c2.get("/api/pratiche", params={"t": "T"}).status_code == 200
    r = c2.post("/api/pratiche", content=b"{non json", headers={"content-type": "application/json"}, params={"t": "T"})
    assert r.status_code == 422 and r.json()["codice"] == "RICHIESTA_NON_VALIDA"
    r = c2.post("/api/pratiche", json={}, params={"t": "T"})                     # manca 'titolo'
    assert r.status_code == 422


def test_r20_dati_dell_export_ora_sono_campi_del_modello(sv):
    """Sesso, provincia, codici comune ecc. si impostano con gli stessi strumenti degli altri campi (GUI e MCP)."""
    pid = sv.crea_pratica("X")["pratica_id"]
    sv.aggiorna(pid, 1, [up("persone", "p_aaaa1111", cognome="A", sesso="F", provincia_nascita="RM", grado_parentela="02"),
                         up("beni", "b_bbbb2222", tipo="fabbricato", codice_comune="H501", classe="3", reddito_dominicale="12.34")])
    d = sv.leggi(pid)["dati"]
    assert d["persone"][0]["sesso"] == "F" and d["beni"][0]["codice_comune"] == "H501"
    with pytest.raises(DatiNonValidi):                       # valore non ammesso per il sesso: errore sul campo
        sv.aggiorna(pid, 2, [up("persone", "p_aaaa1111", sesso="X")])


def test_r20_il_valore_dell_entita_ha_precedenza_su_opzioni_telematico(sv):
    from successioni.telematico import supplemento as SU
    pid = sv.crea_pratica("X")["pratica_id"]
    sv.aggiorna(pid, 1, [up("persone", "p_aaaa1111", cognome="A", sesso="F"),
                         {"op": "set", "sezione": "opzioni", "campi": {"telematico": {"persone": {"p_aaaa1111": {"sesso": "M"}}}}}])
    d = sv.leggi(pid)["dati"]
    assert SU.attr(d, "persone", d["persone"][0], "sesso") == "F"
