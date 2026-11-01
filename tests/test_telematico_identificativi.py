"""Codice fiscale e IBAN: replica Python confrontata con i componenti ufficiali (checkCF_PIVA.jar,
controlliXMLREG2013.jar) ESEGUITI il 2026-11-01 (esiti registrati in tests/fixture_telematico/).

Senza SUCCESSIONI_CONTROLLI_SUC13 si confronta con le registrazioni; con la variabile impostata si riesegue anche il
componente. Dati sintetici: i codici non sono attribuiti a persone reali (nessuna verifica in Anagrafe tributaria).
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from successioni.telematico import identificativi as I

FIX = Path(__file__).parent / "fixture_telematico"
JAR = os.environ.get("SUCCESSIONI_CONTROLLI_SUC13")


def _lotto():
    righe = []
    for r in (FIX / "cf_lotto.tsv").read_text(encoding="utf-8").splitlines():
        if r.strip():
            c = r.split("\t")
            g, m, a = c[3].split("/")
            righe.append((c[0], c[1], c[2], f"{a}-{m}-{g}", c[4], c[5]))
    return righe


def _esiti(testo: str) -> dict[str, dict]:
    out = {}
    for r in testo.splitlines():
        c = r.split("\t")
        if len(c) == 4 and c[1].startswith("parziale="):
            out[c[0]] = {"parziale": c[1][9:], "checkdigit": c[2] == "checkdigit=true", "pf": c[3].endswith("true")}
    return out


def test_cf_generatore_uguale_al_componente_registrato():
    esiti = _esiti((FIX / "cf_lotto_esito_componente.txt").read_text(encoding="utf-8"))
    lotto = _lotto()
    assert len(esiti) == len(lotto) == 33
    validi = 0
    for cognome, nome, sesso, data, comune, cf in lotto:
        e = esiti[cf]
        generato = I.genera_cf_sintetico(cognome, nome, sesso, data, comune)
        # primi 15 caratteri = CodiceFiscale.getCodiceFiscale del componente (che accoda sempre 'A')
        assert generato[:15] == e["parziale"], (cognome, nome)
        # carattere di controllo: stesso giudizio di U1CheckDigit.controllaCheckDigit
        assert I.cf_persona_fisica_valido(cf) is e["checkdigit"], cf
        if e["checkdigit"]:
            assert generato == cf and e["pf"]
            validi += 1
        else:
            assert generato != cf  # i tre codici errati del lotto (caratteri di controllo alterati)
    assert validi == 30


def test_cf_errati_e_lettere_non_gestite():
    assert not I.cf_persona_fisica_valido("RSSMRA40A01H501W")
    assert I.carattere_controllo("RSSMRA40A01H501") == "K"
    assert not I.cf_persona_fisica_valido("rssmra40a01h501")
    with pytest.raises(ValueError):
        I.genera_cf_sintetico("Øster", "Ana", "F", "1990-01-01", "Z101")  # lettera fuori dalla tabella ufficiale
    with pytest.raises(ValueError):
        I.genera_cf_sintetico("Rossi", "Ana", "X", "1990-01-01", "H501")


def test_iban_modulo_97_come_il_componente_registrato():
    for r in (FIX / "iban_esito_componente.txt").read_text(encoding="utf-8").splitlines():
        iban, cd = r.split("\t")[:2]
        assert I.iban_modulo_97_valido(iban) is (cd == "isCheckDigitValid=true"), iban
    assert I.cifre_controllo_iban("IT", "A0123456789000000001234") == "57"


@pytest.mark.skipif(not JAR or not Path(JAR).is_dir() or not shutil.which("java"),
                    reason="componenti ufficiali non configurati (SUCCESSIONI_CONTROLLI_SUC13)")
def test_reale_lotto_cf_rieseguito_con_il_componente(tmp_path):
    out = subprocess.run(["java", "-Dfile.encoding=UTF-8", "-cp", str(Path(JAR) / "*"),
                          str(FIX / "VerificaComponenti.java"), "lotto", str(FIX / "cf_lotto.tsv")],
                         capture_output=True, text=True, timeout=300, env={**os.environ, "JAVA_TOOL_OPTIONS": ""})
    assert out.returncode == 0, out.stderr
    assert _esiti(out.stdout) == _esiti((FIX / "cf_lotto_esito_componente.txt").read_text(encoding="utf-8"))
