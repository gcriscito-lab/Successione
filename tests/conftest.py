"""Configurazione comune dei test: cache del controllo ufficiale, marcatore «java», rilevamento dei test che avviano Java.

Comandi (dettagli in docs/TEST.md):
    pytest -m "not java"                          giro rapido quotidiano, senza il componente Java
    pytest -n 4                                   suite completa in parallelo (pytest-xdist), con la cache
    SUCCESSIONI_TEST_SENZA_CACHE=1 pytest         verifica completa prima di una consegna (Java sempre eseguito)
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _cache_controllo as CACHE  # noqa: E402

_corrente: dict = {"item": None, "java": False}
_senza_marcatore: list[str] = []
_con_java: list[str] = []


def _e_java(args) -> bool:
    try:
        primo = args if isinstance(args, (str, bytes, os.PathLike)) else args[0]
        nome = os.path.basename(os.fsdecode(primo)).lower()
    except (IndexError, TypeError):
        return False
    if isinstance(args, (str, bytes)):           # riga di comando unica (raro)
        nome = nome.split()[0] if nome.split() else nome
    if not isinstance(args, (str, bytes, os.PathLike)) and len(args) == 2 and args[1] == "-version":
        return False                             # sola lettura della versione (condizioni di salto, impronta)
    return nome in ("java", "java.exe", "javaw", "javaw.exe")


_PopenOriginale = subprocess.Popen


class _PopenOsservato(_PopenOriginale):
    """Annota il test che avvia Java (per segnalare i test senza marcatore «java»); per il resto identico."""

    def __init__(self, args, *a, **k):
        if _corrente["item"] is not None and _e_java(args):
            _corrente["java"] = True
        super().__init__(args, *a, **k)


def _installa_cache_adattatore() -> None:
    """L'adattatore usa ``esecutore_reale`` quando nessun esecutore e' iniettato: lo si avvolge con la cache (il job
    resta un'esecuzione reale, non 'simulazione'). ``java -version`` e' memorizzato per processo."""
    from successioni.collegamenti import controllo as C
    reale = C.esecutore_reale
    versioni: dict = {}

    def esecutore_con_cache(argv, cwd, timeout):
        if len(argv) == 2 and argv[1] == "-version":
            chiave = (argv[0], os.environ.get("JAVA_TOOL_OPTIONS"))
            if chiave not in versioni:
                p = reale(argv, cwd, timeout)
                if p.codice_uscita != 0 or p.scaduto:
                    return p
                versioni[chiave] = p
            return versioni[chiave]
        return CACHE.esegui(argv, cwd, timeout, reale)

    esecutore_con_cache.__wrapped__ = reale
    C.esecutore_reale = esecutore_con_cache


def pytest_configure(config):
    subprocess.Popen = _PopenOsservato
    _installa_cache_adattatore()


def pytest_runtest_setup(item):
    _corrente["item"], _corrente["java"] = item, False


def pytest_runtest_teardown(item):
    if _corrente["java"]:
        _con_java.append(item.nodeid)
        if item.get_closest_marker("java") is None:
            _senza_marcatore.append(item.nodeid)
    _corrente["item"], _corrente["java"] = None, False


def pytest_sessionfinish(session):
    elenco = os.environ.get("SUCCESSIONI_TEST_ELENCO_JAVA")
    if elenco and _con_java:
        with open(elenco, "a", encoding="utf-8") as f:
            f.write("".join(n + "\n" for n in _con_java))


def pytest_terminal_summary(terminalreporter):
    s = CACHE.statistiche
    if s["riusi"] or s["esecuzioni"]:
        stato = "attiva" if CACHE.attiva() else f"disattivata ({CACHE.ENV_SENZA_CACHE}=1)"
        terminalreporter.write_line(f"cache del controllo ufficiale {stato} ({CACHE.cartella()}): "
                                    f"{s['riusi']} risultati riusati, {s['esecuzioni']} esecuzioni reali di Java")
    # Su un PC senza Java 8 o senza i JAR i test del controllo ufficiale si saltano: lo si dice in chiaro, con i motivi,
    # perche' una suite «verde» in quel caso NON prova il controllo ufficiale.
    motivi: dict[str, int] = {}
    for rep in terminalreporter.stats.get("skipped", []):
        lr = rep.longrepr
        motivo = lr[2] if isinstance(lr, tuple) and len(lr) == 3 else str(lr)
        motivo = motivo.removeprefix("Skipped: ")
        if any(p in motivo for p in ("Java", "java", "SUCCESSIONI_CONTROLLI", "controllo ufficiale", "controllo SUC13",
                                     "conservatorie")):
            motivi[motivo] = motivi.get(motivo, 0) + 1
    if motivi:
        terminalreporter.section("controllo ufficiale SUC13 NON eseguito", sep="!", red=True)
        for m, n in sorted(motivi.items(), key=lambda x: -x[1]):
            terminalreporter.write_line(f"{n} test saltati: {m}")
        terminalreporter.write_line("Configurare Java 8 e i JAR (docs/TEST.md) prima di considerare verificato l'export.")
    if _senza_marcatore:
        terminalreporter.section("test che avviano Java senza il marcatore «java»", sep="-", yellow=True)
        for n in _senza_marcatore:
            terminalreporter.write_line(n)
