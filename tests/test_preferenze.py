"""Preferenze di operativita' e sicurezza (impostazioni.preferenze / salva)."""
import json

import pytest

from successioni import impostazioni
from successioni.errori import DatiNonValidi


@pytest.fixture(autouse=True)
def _config(monkeypatch, tmp_path):
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(tmp_path / "cfg" / "configurazione.json"))
    monkeypatch.delenv("SUCCESSIONI_MCP_SOLA_LETTURA", raising=False)


def test_predefiniti():
    p = impostazioni.preferenze()
    assert p == {"pulizia_automatica": True, "pulizia_ore": 24, "avviso_visura_giorni": 90, "visura_blocca": False,
                 "mcp_sola_lettura": False}


def test_salvataggio_parziale_conserva_le_altre_e_il_resto_del_file(tmp_path):
    impostazioni.salva({}, profilo={"cf": "RSSMRA40A01H501K"})
    impostazioni.salva({}, preferenze_nuove={"mcp_sola_lettura": True})
    impostazioni.salva({}, preferenze_nuove={"pulizia_ore": 48})
    p = impostazioni.preferenze()
    assert p["mcp_sola_lettura"] is True and p["pulizia_ore"] == 48 and p["avviso_visura_giorni"] == 90
    contenuto = json.loads((tmp_path / "cfg" / "configurazione.json").read_text(encoding="utf-8"))
    assert contenuto["profilo"]["cf"] == "RSSMRA40A01H501K"            # il profilo non viene perso
    assert impostazioni.stato()["preferenze"] == p


@pytest.mark.parametrize("pref", [{"sconosciuta": True}, {"pulizia_ore": 0}, {"pulizia_ore": 721}, {"pulizia_ore": "24"},
                                  {"avviso_visura_giorni": 29}, {"avviso_visura_giorni": True},
                                  {"mcp_sola_lettura": "si"}, {"visura_blocca": 1}])
def test_valori_non_validi_rifiutati(pref):
    with pytest.raises(DatiNonValidi):
        impostazioni.salva({}, preferenze_nuove=pref)
    assert impostazioni.preferenze()["pulizia_ore"] == 24             # nulla e' stato scritto


def test_valore_non_valido_nel_file_e_ignorato(tmp_path):
    f = tmp_path / "cfg" / "configurazione.json"
    f.parent.mkdir()
    f.write_text(json.dumps({"preferenze": {"pulizia_ore": -5, "mcp_sola_lettura": True, "x": 1}}), encoding="utf-8")
    p = impostazioni.preferenze()
    assert p["pulizia_ore"] == 24 and p["mcp_sola_lettura"] is True


def test_variabile_d_ambiente_forza_la_sola_lettura(monkeypatch):
    impostazioni.salva({}, preferenze_nuove={"mcp_sola_lettura": False})
    monkeypatch.setenv("SUCCESSIONI_MCP_SOLA_LETTURA", "1")
    assert impostazioni.preferenze()["mcp_sola_lettura"] is True
