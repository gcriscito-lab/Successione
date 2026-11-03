"""Rilevamento di Ghostscript, veraPDF e profilo ICC: precedenza della variabile d'ambiente, valori non validi, nessuno strumento.
Nessuno strumento viene eseguito; il filesystem e' simulato (glob e which)."""
import pytest

from successioni import pdfa


@pytest.fixture(autouse=True)
def _ambiente_pulito(monkeypatch):
    for v in ("SUCCESSIONI_ICC", "SUCCESSIONI_GS", "SUCCESSIONI_VERAPDF"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setattr(pdfa.glob, "glob", lambda pattern: [])
    monkeypatch.setattr(pdfa.shutil, "which", lambda nome: None)


def test_icc_variabile_valida_ha_la_precedenza(monkeypatch, tmp_path):
    f = tmp_path / "mio.icc"
    f.write_bytes(b"x")
    monkeypatch.setenv("SUCCESSIONI_ICC", str(f))
    monkeypatch.setattr(pdfa.glob, "glob", lambda pattern: ["altro.icc"])
    assert pdfa._icc() == str(f)


def test_icc_variabile_su_file_inesistente_e_ignorata(monkeypatch, tmp_path):
    monkeypatch.setenv("SUCCESSIONI_ICC", str(tmp_path / "manca.icc"))
    assert pdfa._icc() is None
    monkeypatch.setattr(pdfa.glob, "glob", lambda pattern: ["trovato.icc"] if pattern.endswith("srgb.icc") else [])
    assert pdfa._icc() == "trovato.icc"


def test_icc_senza_variabile_e_senza_file_e_none():
    assert pdfa._icc() is None


def test_icc_cerca_anche_in_c_gs(monkeypatch):
    visti = []

    def finto(pattern):
        visti.append(pattern)
        return []
    monkeypatch.setattr(pdfa.glob, "glob", finto)
    pdfa._icc()
    assert any(p.startswith("C:/gs/") and p.endswith("iccprofiles/srgb.icc") for p in visti), visti
    assert any(p.startswith("C:/Program Files/gs/") for p in visti)


def test_icc_cerca_il_primo_modello_che_corrisponde(monkeypatch):
    monkeypatch.setattr(pdfa.glob, "glob", lambda pattern: ["primo.icc", "secondo.icc"] if pattern.startswith("C:/gs/") else [])
    assert pdfa._icc() == "primo.icc"


def test_icc_variabile_vuota_equivale_a_non_impostata(monkeypatch):
    monkeypatch.setenv("SUCCESSIONI_ICC", "")
    assert pdfa._icc() is None


@pytest.mark.parametrize("variabile,funzione,nomi", [
    ("SUCCESSIONI_GS", pdfa.trova_gs, ("gs", "gswin64c", "gswin32c")),
    ("SUCCESSIONI_VERAPDF", pdfa.trova_verapdf, ("verapdf",)),
])
def test_strumenti_nessuno_trovato(monkeypatch, variabile, funzione, nomi):
    assert funzione() is None
    monkeypatch.setenv(variabile, "inesistente")
    assert funzione() is None


@pytest.mark.parametrize("variabile,funzione,nome_path", [
    ("SUCCESSIONI_GS", pdfa.trova_gs, "gswin64c"),
    ("SUCCESSIONI_VERAPDF", pdfa.trova_verapdf, "verapdf"),
])
def test_strumenti_variabile_e_percorso(monkeypatch, variabile, funzione, nome_path):
    monkeypatch.setattr(pdfa.shutil, "which", lambda n: "RISOLTO:" + n if n in ("MIO", nome_path) else None)
    monkeypatch.setenv(variabile, "MIO")
    assert funzione() == "RISOLTO:MIO"                  # la variabile ha la precedenza
    monkeypatch.setenv(variabile, "non-risolvibile")
    assert funzione() == "RISOLTO:" + nome_path          # ripiego sul PATH
    monkeypatch.delenv(variabile)
    assert funzione() == "RISOLTO:" + nome_path


def test_ghostscript_cerca_i_tre_nomi_in_ordine(monkeypatch):
    chiesti = []
    monkeypatch.setattr(pdfa.shutil, "which", lambda n: chiesti.append(n))
    pdfa.trova_gs()
    assert chiesti == ["gs", "gswin64c", "gswin32c"]


@pytest.mark.parametrize("variabile,funzione,primo_nome", [
    ("SUCCESSIONI_GS", pdfa.trova_gs, "gs"),
    ("SUCCESSIONI_VERAPDF", pdfa.trova_verapdf, "verapdf"),
])
def test_la_variabile_batte_il_path_anche_quando_il_path_trova_lo_strumento(monkeypatch, variabile, funzione, primo_nome):
    monkeypatch.setattr(pdfa.shutil, "which", lambda n: "R:" + n)        # tutti i nomi risolvibili
    assert funzione() == "R:" + primo_nome                                 # senza variabile: il primo nome del PATH
    monkeypatch.setenv(variabile, "MIO")
    assert funzione() == "R:MIO"                                           # con la variabile: la variabile per prima
