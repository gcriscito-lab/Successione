"""Pulizia dei temporanei (pulizia.py): elimina solo il temporaneo vecchio dentro la cartella dei dati."""
import os
import time
from pathlib import Path

import pytest

from successioni import pulizia
from successioni.archivio import Archivio
from successioni.blocchi import blocco_file
from successioni.servizio import Servizio


@pytest.fixture(autouse=True)
def _config(monkeypatch, tmp_path):
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(tmp_path / "cfg" / "configurazione.json"))


def vecchio(p: Path, ore=48):
    t = time.time() - ore * 3600
    os.utime(p, (t, t))


def scrivi(p: Path, n=10, ore=None):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x" * n)
    if ore:
        vecchio(p, ore)
    return p


def collega(legame: Path, destinazione: Path):
    """Collegamento simbolico o, su Windows senza privilegi, giunzione di cartella (mklink /J)."""
    try:
        os.symlink(destinazione, legame, target_is_directory=True)
    except (OSError, NotImplementedError):
        if os.name != "nt":
            pytest.skip("collegamenti simbolici non disponibili")
        import subprocess
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(legame), str(destinazione)], capture_output=True)
        if r.returncode != 0:
            pytest.skip("ne' collegamenti simbolici ne' giunzioni disponibili")


def prepara(base: Path):
    base.mkdir(parents=True, exist_ok=True)
    (base / "archivio.sqlite3").write_bytes(b"db")
    scrivi(base / "allegati" / "ab" / ("ab" + "0" * 62), 5, 500)       # allegato definitivo vecchio
    scrivi(base / "elaborati" / "pr_1" / "abc.xml", 7, 500)            # elaborato definitivo vecchio
    scrivi(base / "elaborati" / "pr_1" / "modello_abc.pdf", 7, 500)
    scrivi(base / "configurazione.json", 3, 500)
    return base


def test_elimina_vecchi_e_conserva_recenti(tmp_path):
    base = prepara(tmp_path / "dati")
    vec = scrivi(base / "lavoro" / "controlli" / "ctl_a-1234567890ab" / "in" / "F.xml", 100, 48)
    vecchio(vec.parent.parent)
    vecchio(vec.parent)
    rec = scrivi(base / "lavoro" / "controlli" / "ctl_b-1234567890ac" / "in" / "F.xml", 50)
    tmp_v = scrivi(base / "elaborati" / "pr_1" / "x.xml.tmp", 20, 48)
    tmp_r = scrivi(base / "allegati" / "ab" / "y.tmp", 20)
    r = pulizia.pulisci(base)
    assert r["eseguita"] and r["eliminati"] == 2 and r["byte_liberati"] == 120
    assert not vec.parent.parent.exists() and not tmp_v.exists()
    assert rec.exists() and tmp_r.exists()


def test_preferenza_disattivata_e_forzata(tmp_path):
    from successioni import impostazioni
    base = prepara(tmp_path / "dati")
    tmp = scrivi(base / "elaborati" / "pr_1" / "x.tmp", 9, 48)
    impostazioni.salva({}, preferenze_nuove={"pulizia_automatica": False})
    r = pulizia.pulisci(base)
    assert not r["eseguita"] and "disattivata" in r["motivo"] and tmp.exists()
    assert pulizia.pulisci_silenziosa(base)["eseguita"] is False
    r = pulizia.pulisci(base, forzata=True)
    assert r["eseguita"] and r["eliminati"] == 1 and not tmp.exists()


def test_eta_parametrica_e_preferenza_ore(tmp_path):
    from successioni import impostazioni
    base = prepara(tmp_path / "dati")
    tmp = scrivi(base / "elaborati" / "p" / "x.tmp", 4, 5)             # 5 ore
    assert pulizia.pulisci(base)["eliminati"] == 0                      # predefinito: 24 ore
    impostazioni.salva({}, preferenze_nuove={"pulizia_ore": 2})
    assert pulizia.pulisci(base)["eliminati"] == 1 and not tmp.exists()
    scrivi(base / "elaborati" / "p" / "y.tmp", 4, 5)
    assert pulizia.pulisci(base, eta_ore=10)["eliminati"] == 0


def test_non_tocca_db_allegati_elaborati_definitivi(tmp_path):
    base = prepara(tmp_path / "dati")
    scrivi(base / "elaborati" / "pr_1" / "x.tmp", 1, 48)
    pulizia.pulisci(base, eta_ore=0)
    assert (base / "archivio.sqlite3").exists() and (base / "configurazione.json").exists()
    assert (base / "allegati" / "ab" / ("ab" + "0" * 62)).exists()
    assert (base / "elaborati" / "pr_1" / "abc.xml").exists() and (base / "elaborati" / "pr_1" / "modello_abc.pdf").exists()


def test_non_esce_da_base_con_symlink(tmp_path):
    base = prepara(tmp_path / "dati")
    fuori = tmp_path / "fuori"
    scrivi(fuori / "vecchio.tmp", 11, 48)
    scrivi(fuori / "controlli_x" / "f.xml", 11, 48)
    (base / "lavoro").mkdir()
    for legame in (base / "lavoro" / "controlli", base / "elaborati" / "legame"):
        collega(legame, fuori)
    pulizia.pulisci(base, eta_ore=0)
    assert (fuori / "vecchio.tmp").exists() and (fuori / "controlli_x" / "f.xml").exists()


def test_lock_attivo_preservato(tmp_path):
    base = prepara(tmp_path / "dati")
    lock = base / "lavoro" / "lock" / "ctl_a.lock"
    d = scrivi(base / "lavoro" / "controlli" / "ctl_a-1234567890ab" / "in" / "F.xml", 30, 48)
    vecchio(d.parent.parent)
    vecchio(d.parent)
    with blocco_file(lock) as acquisito:
        assert acquisito
        vecchio(lock)
        with blocco_file(lock) as secondo:
            if secondo:
                pytest.skip("lock rientranti su questa piattaforma: prova non significativa")
            r = pulizia.pulisci(base, eta_ore=0)
        assert r["eliminati"] == 0 and d.exists() and lock.exists()
    r = pulizia.pulisci(base, eta_ore=0)                                 # lock rilasciato: ora si pulisce
    assert r["eliminati"] >= 1 and not d.parent.parent.exists()


def test_errore_su_un_file_non_fa_fallire(tmp_path, monkeypatch):
    base = prepara(tmp_path / "dati")
    scrivi(base / "elaborati" / "a.tmp", 3, 48)
    scrivi(base / "elaborati" / "b.tmp", 3, 48)
    orig = Path.unlink

    def instabile(self, *a, **k):
        if self.name == "a.tmp":
            raise PermissionError("in uso")
        return orig(self, *a, **k)
    monkeypatch.setattr(Path, "unlink", instabile)
    r = pulizia.pulisci(base, eta_ore=0)
    assert r["eseguita"] and r["eliminati"] == 1 and (base / "elaborati" / "a.tmp").exists()


def test_base_inesistente_e_silenziosa(tmp_path):
    assert pulizia.pulisci(tmp_path / "manca")["eseguita"] is False
    assert pulizia.pulisci_silenziosa(tmp_path / "manca")["eseguita"] is False


def test_api_pulizia_e_aggancio_all_avvio(tmp_path):
    from starlette.testclient import TestClient
    from successioni.web import crea_app
    s = Servizio(Archivio(tmp_path / "a"))
    tmp = scrivi(s.arch.base / "elaborati" / "x.tmp", 8, 48)
    with TestClient(crea_app(s, token="t", ammetti_host_di_prova=True)) as cl:
        time.sleep(0.5)                                                  # pulizia all'avvio in un thread
        r = cl.post("/api/pulizia?t=t", json={})
    assert not tmp.exists()
    assert r.status_code == 200 and r.json()["eseguita"] is True
