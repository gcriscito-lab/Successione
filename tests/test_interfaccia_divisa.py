"""Interfaccia divisa in piu' file (21/11/2026): nessuno script dimenticato, avvio per ultimo, nessuna dichiarazione globale doppia."""
import re
import shutil
import subprocess

import pytest

from gui_js import STATIC, script_interfaccia


def test_index_carica_tutti_gli_script_una_volta_e_avvio_per_ultimo():
    elencati = script_interfaccia()
    presenti = sorted(p.name for p in STATIC.glob("*.js") if p.name != "layout.js")
    assert sorted(elencati) == presenti, "ogni .js di static/ (tranne layout.js) va caricato in index.html, una volta sola"
    assert len(elencati) == len(set(elencati))
    assert elencati[0] == "app.js" and elencati[-1] == "avvio.js"
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert html.index("/static/avvio.js") < html.index("/static/layout.js")


def test_ogni_file_in_modalita_rigorosa_e_init_solo_in_avvio():
    for nome in script_interfaccia():
        testo = (STATIC / nome).read_text(encoding="utf-8")
        assert testo.startswith('"use strict";'), nome
        chiamate = re.findall(r"^init\(\);", testo, re.M)
        assert len(chiamate) == (1 if nome == "avvio.js" else 0), nome


def test_nessuna_dichiarazione_globale_in_due_file():
    # con script classici const/let/class globali doppie bloccano l'avvio; una function doppia sostituirebbe la prima in silenzio
    visti: dict[str, str] = {}
    for nome in script_interfaccia():
        for m in re.finditer(r"^(?:async\s+)?(?:function\s*\*?\s*|const\s+|let\s+|class\s+)([A-Za-z_$][\w$]*)",
                             (STATIC / nome).read_text(encoding="utf-8"), re.M):
            assert m.group(1) not in visti, f"{m.group(1)} dichiarato in {visti.get(m.group(1))} e in {nome}"
            visti[m.group(1)] = nome


@pytest.mark.skipif(not shutil.which("node"), reason="Node.js non installato")
def test_sintassi_di_ogni_file():
    for nome in script_interfaccia() + ["layout.js"]:
        r = subprocess.run(["node", "--check", str(STATIC / nome)], capture_output=True, text=True)
        assert r.returncode == 0, (nome, r.stderr)
