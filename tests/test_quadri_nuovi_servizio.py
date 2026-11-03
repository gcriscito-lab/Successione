"""I quadri EO, EP, EQ, EN, EL, EM non sono piu' «non supportati» attraverso il servizio; EI resta non supportato."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from telematico_casi import caso_azienda, caso_mezzi, caso_tavolare, caso_titoli  # noqa: E402
from test_elaborati import ops_da_caso  # noqa: E402
from successioni.archivio import Archivio  # noqa: E402
from successioni.servizio import Servizio  # noqa: E402

CASI = [("EO", caso_titoli), ("EP", caso_mezzi), ("EQ", caso_mezzi), ("EN", caso_azienda), ("EL", caso_tavolare), ("EM", caso_tavolare)]


def _pratica(tmp_path, caso):
    s = Servizio(Archivio(tmp_path / "dati"))
    return s, s.crea_pratica("Caso sintetico", iniziali=ops_da_caso(caso()))["pratica_id"]


@pytest.mark.parametrize("quadro,caso", CASI)
def test_quadro_nuovo_non_e_non_supportato(tmp_path, quadro, caso):
    s, pid = _pratica(tmp_path, caso)
    stati = {q["id"]: q["stato"] for q in s.quadri(pid)["quadri"]}
    assert stati[quadro] != "non_supportato", stati
    rilievi = s.verifica(pid)["rilievi"]
    assert not [r for r in rilievi if r["codice"] == "QUADRO_NON_SUPPORTATO" and quadro in str(r)], rilievi


def test_ei_resta_non_supportato(tmp_path):
    s, pid = _pratica(tmp_path, caso_titoli)
    ei = {q["id"]: q for q in s.quadri(pid)["quadri"]}["EI"]
    assert ei["stato"] in ("inattivo", "non_supportato") and ei.get("supportato") is False, ei


def test_modifica_di_un_titolo_cambia_revisione_e_impronta(tmp_path):
    s, pid = _pratica(tmp_path, caso_titoli)
    prima = s.leggi(pid)
    r = s.aggiorna(pid, prima["revisione"], [{"op": "upsert", "coll": "beni", "id": "b_azioni01", "campi": {"valore": "11000"}}])
    dopo = s.leggi(pid)
    assert dopo["revisione"] == prima["revisione"] + 1 == r["revisione"]
    assert dopo["impronta_dichiarativa"] != prima["impronta_dichiarativa"]


def test_un_bene_in_provincia_tavolare_passa_da_eb_a_el(tmp_path):
    s, pid = _pratica(tmp_path, caso_tavolare)
    dati = s.leggi(pid)["dati"]
    assert {b["id"] for b in dati["beni"] if b.get("provincia") == "BZ"} == {"b_terrtav1", "b_fabbtav1"}
    stati = {q["id"]: q["stato"] for q in s.quadri(pid)["quadri"]}
    assert stati["EL"] != "inattivo" and stati["EM"] != "inattivo"
