"""Personalizzazione dell'app (sezione `interfaccia` delle impostazioni): accento, densita', contrasto, movimento, avvio, nome dello
studio, quadri predefiniti per le nuove pratiche."""
import pytest

from successioni import impostazioni
from successioni.errori import DatiNonValidi


@pytest.fixture(autouse=True)
def _config(monkeypatch, tmp_path):
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(tmp_path / "cfg" / "configurazione.json"))


def test_predefiniti_della_personalizzazione():
    p = impostazioni.preferenze_interfaccia({})
    assert (p["accento"], p["densita"], p["contrasto"], p["movimento"], p["avvio"], p["nome_studio"], p["quadri_predefiniti"]) == (
        "predefinito", "normale", "normale", "normale", "elenco", "", [])


def test_salvataggio_e_rilettura():
    impostazioni.salva({}, interfaccia={"accento": "verde", "densita": "compatta", "contrasto": "alto", "movimento": "ridotto",
                                        "avvio": "ultima", "nome_studio": "Studio Rossi & Associati",
                                        "quadri_predefiniti": ["EA", "EB", "EC", "ED", "EF"]})
    p = impostazioni.stato()["interfaccia"]
    assert p["accento"] == "verde" and p["contrasto"] == "alto" and p["avvio"] == "ultima"
    assert p["nome_studio"] == "Studio Rossi & Associati" and p["quadri_predefiniti"] == ["EA", "EB", "EC", "ED", "EF"]
    assert p["tema"] == "sistema"                                       # le altre preferenze non cambiano


@pytest.mark.parametrize("valori", [
    {"accento": "fucsia"}, {"densita": "enorme"}, {"contrasto": "medio"}, {"movimento": 1}, {"avvio": "casuale"},
    {"nome_studio": "x" * 61}, {"nome_studio": "riga1\nriga2"}, {"nome_studio": 5},
    {"quadri_predefiniti": ["EA", "ZZ"]}, {"quadri_predefiniti": ["EA", "EA"]}, {"quadri_predefiniti": "EA"},
    {"sconosciuta": "x"},
])
def test_valori_non_validi_rifiutati(valori):
    with pytest.raises(DatiNonValidi):
        impostazioni.salva({}, interfaccia=valori)
    assert impostazioni.stato()["interfaccia"]["accento"] == "predefinito"   # nulla e' stato scritto


def test_vuoto_e_consentito_per_nome_e_quadri():
    impostazioni.salva({}, interfaccia={"nome_studio": "Studio", "quadri_predefiniti": ["EA"]})
    impostazioni.salva({}, interfaccia={"nome_studio": "", "quadri_predefiniti": []})
    p = impostazioni.stato()["interfaccia"]
    assert p["nome_studio"] == "" and p["quadri_predefiniti"] == []
