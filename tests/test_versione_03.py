"""Versione 0.3 (densita' e velocita' di inserimento): preferenze nuove dell'interfaccia. Le parti nel browser (pannello sotto,
scheda compatta, vista unica degli immobili, Alt+1…9, Invio al campo successivo) sono in tests/e2e/gui_versione_03.js."""
import json
from pathlib import Path

import pytest

from successioni import impostazioni as IM

STATIC = Path(__file__).resolve().parents[1] / "src" / "successioni" / "static"


def test_predefiniti_invariati(tmp_path, monkeypatch):
    """Le novita' si attivano dalle Impostazioni: chi non le sceglie vede l'interfaccia di prima."""
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(tmp_path / "configurazione.json"))
    i = IM.stato()["interfaccia"]
    assert i["disposizione"] == "destra" and i["densita"] == "normale" and i["altezza_pannello"] == 380


def test_disposizione_e_altezza_validate(tmp_path, monkeypatch):
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(tmp_path / "configurazione.json"))
    IM.salva({}, {"disposizione": "sotto", "altezza_pannello": 420})
    assert {k: IM.stato()["interfaccia"][k] for k in ("disposizione", "altezza_pannello")} == {"disposizione": "sotto", "altezza_pannello": 420}
    for chiave, sbagliato in (("disposizione", "sinistra"), ("altezza_pannello", 199), ("altezza_pannello", 901), ("altezza_pannello", True)):
        prima = (tmp_path / "configurazione.json").read_text()
        with pytest.raises(IM.DatiNonValidi):
            IM.salva({}, {chiave: sbagliato})
        assert (tmp_path / "configurazione.json").read_text() == prima


def test_configurazione_vecchia_senza_chiavi_nuove(tmp_path, monkeypatch):
    """Un file di configurazione scritto dalla 0.2 (senza disposizione) resta valido e prende i predefiniti."""
    f = tmp_path / "configurazione.json"
    f.write_text(json.dumps({"interfaccia": {"densita": "compatta", "larghezza_pannello": 400}}), encoding="utf-8")
    monkeypatch.setenv("SUCCESSIONI_CONFIG", str(f))
    i = IM.stato()["interfaccia"]
    assert i["densita"] == "compatta" and i["larghezza_pannello"] == 400 and i["disposizione"] == "destra"


def test_interfaccia_conosce_le_stesse_preferenze():
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    predef = js.split("const ASPETTO_DEFAULT = {")[1].split("};")[0]
    for k, v in IM.INTERFACCIA_DEFAULT.items():
        assert k + ":" in predef.replace(" ", ""), k
    assert "disposizione: 'destra'" in predef and "altezza_pannello: 380" in predef
    css = (STATIC / "app.css").read_text(encoding="utf-8")
    assert ':root[data-disposizione="sotto"] .app.conIns' in css and ':root[data-densita="compatta"] .ins .campi-scheda .rg' in css
