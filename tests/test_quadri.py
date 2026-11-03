import pytest
from successioni import quadri as Q
from successioni.archivio import Archivio
from successioni.servizio import Servizio


@pytest.fixture
def sv(tmp_path):
    return Servizio(Archivio(tmp_path / "d"))


def op(coll, id=None, **campi):
    return {"op": "upsert", "coll": coll, **({"id": id} if id else {}), "campi": campi}


def test_stati_e_mappatura_quadri(sv):
    pid = sv.crea_pratica("X")["pratica_id"]
    sv.aggiorna(pid, 1, [
        op("persone", "p_aaaa1111", cognome="Rossi", ruolo="defunto", codice_fiscale="RSSMRA50A01H501X"),
        op("persone", "p_bbbb2222", cognome="Rossi", ruolo="erede"),
        op("beni", "b_cccc3333", tipo="terreno", foglio="1", particella="2"),
        op("beni", "b_dddd4444", tipo="fabbricato"),            # catastali incompleti -> rilievo in EC
    ])
    st = {q["id"]: q for q in sv.quadri(pid)["quadri"]}
    assert st["AN"]["stato"] == "compilato" and st["EA"]["righe"] == 1
    assert st["EB"]["stato"] == "compilato" and st["EC"]["stato"] == "rilievi" and st["EC"]["rilievi"] == 1
    assert st["ED"]["stato"] == "vuoto" and st["EF"]["stato"] == "inattivo"


def test_quadro_non_supportato_blocca_finalizzazione_senza_perdere_dati(sv):
    pid = sv.crea_pratica("X")["pratica_id"]
    r = sv.aggiorna(pid, 1, [{"op": "set", "sezione": "opzioni", "campi": {"quadri_attivi": ["EA", "EI"]}},
                             op("persone", "p_aaaa1111", cognome="R", ruolo="defunto", codice_fiscale="RSSMRA50A01H501X")])
    v = sv.verifica(pid)
    assert not v["finalizzabile"]
    assert any(x["codice"] == "QUADRO_NON_SUPPORTATO" and "EI" in x["percorso"] for x in v["rilievi"])
    assert sv.leggi(pid)["dati"]["opzioni"]["quadri_attivi"] == ["EA", "EI"]      # bozza conservata
    assert {q["id"]: q["stato"] for q in sv.quadri(pid)["quadri"]}["EI"] == "non_supportato"


def test_dati_in_quadro_non_attivo_segnalati(sv):
    pid = sv.crea_pratica("X")["pratica_id"]
    sv.aggiorna(pid, 1, [{"op": "set", "sezione": "opzioni", "campi": {"quadri_attivi": ["EA"]}},
                         op("beni", "b_cccc3333", tipo="terreno", foglio="1", particella="2")])
    assert "DATI_IN_QUADRO_NON_ATTIVO" in [r["codice"] for r in sv.verifica(pid)["rilievi"]]
