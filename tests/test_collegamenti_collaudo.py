"""Comandi di collaudo riprendibili (area 3): uscita JSON, stesso archivio, nessun invio."""
import json
from pathlib import Path

import pytest

import successioni.collegamenti.collaudo as K
import successioni.collegamenti.controllo as C

FIX = Path(C.__file__).parent / "fixture" / "controllo_reale_20261101"


@pytest.fixture(autouse=True)
def senza_componente(monkeypatch):
    monkeypatch.delenv(C.ENV_JAR, raising=False)
    monkeypatch.setenv(C.ENV_JAVA, "java-inesistente-per-test")


def esegui(capsys, *argv):
    assert K.main(list(argv)) == 0
    return json.loads(capsys.readouterr().out)


def test_ambiente_e_controllo_manuale_riprendibile(tmp_path, capsys):
    amb = esegui(capsys, "ambiente")
    assert amb["controllo_suc13"]["pronto"] is False and len(amb["jar_richiesti"]) == 15
    a = str(tmp_path / "arch")
    r = esegui(capsys, "--archivio", a, "controllo", "--xml", str(FIX / "frontespizio.xml"))
    assert r["esito"] == "da_collaudare" and r["stato"] == "attesa_diagnostico"
    r2 = esegui(capsys, "--archivio", a, "registra-diagnostico", "--job", r["job_id"], "--dgn",
                str(FIX / "frontespizio.dgn"), "--log", str(FIX / "frontespizio_logSchema.xml"), "--wri",
                str(FIX / "frontespizio.wri"), "--non-prima-di", "2026-11-01T09:00:00+00:00",
                "--conferma-associazione")   # registrazione del 2026-11-01, nome di un controllo di un altro archivio
    assert r2["esito"] == "fallito" and r2["stato_controllo"] == "negativo" and r2["versione_controllo"] == "2.3.1"
    st = esegui(capsys, "--archivio", a, "stato", "--job", r["job_id"])
    assert st["stato"] == "completato"


def test_catasto_avvia_da_collaudare(tmp_path, capsys):
    r = esegui(capsys, "--archivio", str(tmp_path / "a"), "catasto-avvia", "--pratica", "pr_1", "--cf",
               "RSSMRA40A01H501X")
    assert r["esito"] == "da_collaudare" and r["dettaglio"]["stato"] == "attesa_utente"


def test_impronte_di_riferimento_coprono_il_jnlp():
    assert set(K.IMPRONTE_20261101) == set(C.jar_richiesti())
