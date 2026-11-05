"""Backup verificato, profilo dello studio e versioni registrate con l'export (preparazione prima pratica reale)."""
import time

import pytest

from successioni import backup_archivio as BK, impostazioni
from successioni.archivio import Archivio
from successioni.errori import DatiNonValidi
from successioni.servizio import Servizio
from test_correzioni_codex import pratica_con_allegati


@pytest.fixture(autouse=True)
def _isola(monkeypatch, tmp_path):
    monkeypatch.delenv("SUCCESSIONI_BACKUP", raising=False)
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(tmp_path / "cfg" / "configurazione.json"))


def test_backup_manuale_verificato_e_ripristinabile(tmp_path):
    s, pid = pratica_con_allegati(tmp_path / "a")
    b = s.backup_archivio("prova")
    assert b["verificato"] and not b["automatico"]
    assert (tmp_path / "a" / "Successioni-backup" / "dati" / b["nome"] / "archivio.sqlite3").is_file()
    nuovo = Archivio(tmp_path / "ripristinato")
    nuovo.ripristina(b["percorso"])
    s2 = Servizio(nuovo)
    assert s2.leggi(pid)["titolo"] == s.leggi(pid)["titolo"]
    assert [x["nome"] for x in s.elenco_backup()["backup"]] == [b["nome"]]


def test_backup_automatico_prima_dell_export_con_limite_di_frequenza(tmp_path):
    s, pid = pratica_con_allegati(tmp_path / "a")
    r1 = s.esporta(pid)
    assert r1["backup"]["eseguito"] and r1["backup"]["automatico"] and r1["backup"]["verificato"]
    r2 = s.esporta(pid)
    assert not r2["backup"]["eseguito"] and "recente" in r2["backup"]["motivo"]


def test_potatura_dei_backup_automatici(tmp_path, monkeypatch):
    s, pid = pratica_con_allegati(tmp_path / "a")
    monkeypatch.setattr(BK, "MAX_AUTOMATICI", 2)
    for i in range(4):
        BK.crea(s.arch, f"t{i}", automatico=True)
        time.sleep(1.05)
    assert len([b for b in BK.elenco(s.arch) if b["automatico"]]) == 2


def test_backup_fallito_non_blocca_l_export(tmp_path, monkeypatch):
    s, pid = pratica_con_allegati(tmp_path / "a")

    def guasto(*a, **k):
        raise DatiNonValidi("disco pieno")
    monkeypatch.setattr(BK, "crea", guasto)
    r = s.esporta(pid)
    assert r["completo"] and not r["backup"]["eseguito"] and "disco pieno" in r["backup"]["errore"]


def test_versioni_registrate_con_l_export(tmp_path):
    s, pid = pratica_con_allegati(tmp_path / "a")
    r = s.esporta(pid)
    assert r["versioni"]["regole"] and r["versioni"]["specifiche_suc"] == "SUC13_20250702" and r["versioni"]["applicazione"]
    assert s.stato_elaborati(pid)["export"]["versioni"] == r["versioni"]


def test_profilo_studio_predefinito_per_le_nuove_pratiche(tmp_path):
    impostazioni.salva({}, profilo={"cf": "RSSMRA40A01H501K", "tipo": "10", "impegno_codice": "2"})
    s = Servizio(Archivio(tmp_path / "a"))
    pid = s.crea_pratica("Nuova")["pratica_id"]
    assert s.leggi(pid)["dati"]["opzioni"]["fornitore"] == {"cf": "RSSMRA40A01H501K", "tipo": "10", "impegno_codice": "2"}
    # un fornitore indicato in creazione prevale sul profilo
    ops = [{"op": "set", "sezione": "opzioni", "campi": {"fornitore": {"cf": "RSSNNA70A41H501J", "tipo": "1"}}}]
    pid2 = s.crea_pratica("Altra", iniziali=ops)["pratica_id"]
    assert s.leggi(pid2)["dati"]["opzioni"]["fornitore"]["cf"] == "RSSNNA70A41H501J"
    impostazioni.salva({}, profilo={})                      # svuotato: nessun predefinito
    assert "fornitore" not in s.leggi(s.crea_pratica("Terza")["pratica_id"])["dati"]["opzioni"]


@pytest.mark.parametrize("profilo", [{"cf": "NONVALIDO"}, {"tipo": "7"}, {"impegno_codice": "9"}, {"altro": "x"}])
def test_profilo_non_valido_rifiutato(profilo):
    with pytest.raises(DatiNonValidi):
        impostazioni.salva({}, profilo=profilo)
