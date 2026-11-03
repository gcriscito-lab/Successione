"""Lanciatore in parallelo dei compiti per agenti gratuiti: ordine dei risultati, limite di concorrenza, causa letta dalla consegna."""
import importlib.util
import threading
import time
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("lancia_lotto", RADICE / "scripts" / "agenti_gratuiti" / "lancia_lotto.py")
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)


def test_risultati_nell_ordine_dato_e_limite_di_concorrenza(tmp_path):
    attivi, massimo, blocco = 0, 0, threading.Lock()

    def finto(cid, out, max_iter):
        nonlocal attivi, massimo
        with blocco:
            attivi += 1
            massimo = max(massimo, attivi)
        time.sleep(0.05)
        with blocco:
            attivi -= 1
        return 0 if cid != "C3" else 1

    r = L.esegui_lotto(["C1", "C2", "C3", "C4", "C5", "C6"], 2, tmp_path, esegui=finto, pausa_s=0)
    assert [x[0] for x in r] == ["C1", "C2", "C3", "C4", "C5", "C6"]
    assert [x[1] for x in r] == [0, 0, 1, 0, 0, 0]
    assert 1 <= massimo <= 2


def test_parallelo_non_valido_e_compiti_duplicati(tmp_path):
    with pytest.raises(ValueError, match="almeno 1"):
        L.esegui_lotto(["C1"], 0, tmp_path, esegui=lambda *a: 0)
    with pytest.raises(ValueError, match="duplicati"):
        L.esegui_lotto(["C1", "C1"], 2, tmp_path, esegui=lambda *a: 0)


def test_causa_dall_ultima_consegna(tmp_path):
    vecchia = tmp_path / "C7-1"
    vecchia.mkdir()
    (vecchia / "CONSEGNA.md").write_text("- Causa prevalente del mancato esito: vecchia\n", encoding="utf-8")
    time.sleep(0.05)
    nuova = tmp_path / "C7-2"
    nuova.mkdir()
    (nuova / "CONSEGNA.md").write_text("- Causa prevalente del mancato esito: nessun problema\n", encoding="utf-8")
    assert L.causa(tmp_path, "C7") == "Causa prevalente del mancato esito: nessun problema"
    assert "nessuna consegna" in L.causa(tmp_path, "C8")
    (tmp_path / "C9-1").mkdir()
    (tmp_path / "C9-1" / "CONSEGNA.md").write_text("niente\n", encoding="utf-8")
    assert L.causa(tmp_path, "C9") == "consegna senza causa indicata"


def test_un_guasto_di_un_compito_non_ferma_gli_altri(tmp_path):
    def finto(cid, out, max_iter):
        if cid == "C2":
            raise RuntimeError("guasto")
        return 0

    r = L.esegui_lotto(["C1", "C2", "C3"], 2, tmp_path, esegui=finto, pausa_s=0)
    assert [(c, k) for c, k, _ in r] == [("C1", 0), ("C2", 99), ("C3", 0)]
    assert "RuntimeError: guasto" in r[1][2]
