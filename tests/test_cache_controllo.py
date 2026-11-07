"""La cache dei test per il controllo ufficiale (tests/_cache_controllo.py) restituisce le stesse uscite del componente."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

import _cache_controllo as CACHE
from successioni.collegamenti import controllo as C


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setenv(CACHE.ENV_CARTELLA, str(tmp_path / "cache"))
    monkeypatch.delenv(CACHE.ENV_SENZA_CACHE, raising=False)
    return tmp_path / "cache"


def _lavoro(radice: Path, nome: str, xml: bytes) -> Path:
    for d in ("in", "out", "tmp"):
        (radice / d).mkdir(parents=True, exist_ok=True)
    (radice / "in" / f"{nome}.xml").write_bytes(xml)
    return radice


def _argv(radice: Path, nome: str, dcm: bool = True) -> list[str]:
    a = ["java-finto", "-Djava.awt.headless=true", f"-Djava.io.tmpdir={radice / 'tmp'}", "-cp", "nessuno.jar",
         C.CLASSE_CONTROLLO, f"in/{nome}.xml", f"out/{nome}.xml"]
    return a + ([f"out/{nome}.dcm"] if dcm else [])


class Finto:
    """Componente simulato: scrive .dgn (col nome del file, come il vero) e _logSchema.xml; consuma l'input col DCM."""

    def __init__(self, scaduto=False):
        self.chiamate, self.scaduto = 0, scaduto

    def __call__(self, argv, cwd, timeout):
        self.chiamate += 1
        i = argv.index(C.CLASSE_CONTROLLO)
        inp, out = argv[i + 1], Path(argv[i + 2])
        dati = (cwd / inp).read_bytes()
        (cwd / out.parent / f"{out.stem}.dgn").write_bytes(f"0****  {inp}\n1 {len(dati)}\n".encode())
        (cwd / out.parent / f"{out.stem}_logSchema.xml").write_bytes(b"<EsitoFornitura/>")
        if len(argv) > i + 3:
            (cwd / argv[i + 3]).write_bytes(b"DCM" + dati)
            (cwd / inp).unlink()
        return C.Processo(None if self.scaduto else 0, f"letto {inp}".encode(), b"", 1.5, scaduto=self.scaduto)


def test_riuso_con_nome_sostituito_e_input_consumato(cache, tmp_path):
    f = Finto()
    n1, n2 = "ctl_" + "a" * 24, "ctl_" + "b" * 24
    a = _lavoro(tmp_path / "a", n1, b"<x/>")
    p1 = CACHE.esegui(_argv(a, n1), a, 600, f)
    b = _lavoro(tmp_path / "b", n2, b"<x/>")
    p2 = CACHE.esegui(_argv(b, n2), b, 600, f)
    assert f.chiamate == 1                                   # seconda volta: uscite riusate
    assert (b / "out" / f"{n2}.dgn").read_bytes() == (a / "out" / f"{n1}.dgn").read_bytes().replace(
        n1.encode(), n2.encode())
    assert (b / "out" / f"{n2}.dcm").read_bytes() == b"DCM<x/>"
    assert not (b / "in" / f"{n2}.xml").exists()              # come il componente: copia consumata col DCM
    assert (p2.codice_uscita, p2.stdout) == (p1.codice_uscita, p1.stdout.replace(n1.encode(), n2.encode()))


def test_input_diverso_o_forma_diversa_non_riusa(cache, tmp_path):
    f = Finto()
    a = _lavoro(tmp_path / "a", "F", b"<x/>")
    CACHE.esegui(_argv(a, "F"), a, 600, f)
    b = _lavoro(tmp_path / "b", "F", b"<y/>")
    CACHE.esegui(_argv(b, "F"), b, 600, f)
    c = _lavoro(tmp_path / "c", "F", b"<x/>")
    CACHE.esegui(_argv(c, "F", dcm=False), c, 600, f)
    assert f.chiamate == 3


def test_scaduto_non_conservato_e_tempo_massimo_rispettato(cache, tmp_path):
    a = _lavoro(tmp_path / "a", "F", b"<x/>")
    CACHE.esegui(_argv(a, "F"), a, 600, Finto(scaduto=True))
    f = Finto()
    b = _lavoro(tmp_path / "b", "F", b"<x/>")
    CACHE.esegui(_argv(b, "F"), b, 600, f)
    assert f.chiamate == 1                                   # l'esecuzione scaduta non era stata conservata
    c = _lavoro(tmp_path / "c", "F", b"<x/>")
    CACHE.esegui(_argv(c, "F"), c, 1, f)                      # tempo massimo < durata registrata: componente reale
    assert f.chiamate == 2


def test_disattivabile(cache, tmp_path, monkeypatch):
    monkeypatch.setenv(CACHE.ENV_SENZA_CACHE, "1")
    f = Finto()
    for d in ("a", "b"):
        w = _lavoro(tmp_path / d, "F", b"<x/>")
        CACHE.esegui(_argv(w, "F"), w, 600, f)
    assert f.chiamate == 2 and not cache.exists()


def test_data_del_rapporto_aggiornata():
    from datetime import date
    oggi = date.today()
    assert CACHE._data_odierna(b"   Data: 1/11/2026\nx") == f"   Data: {oggi.day}/{oggi.month}/{oggi.year}\nx".encode()


# --------------------------------------------------------------------------- confronto con il componente reale
from test_telematico_controllo import _a10, _esegui_reale, _motivo_salto, JAR, JAVA  # noqa: E402


def _normalizza(ruolo: str, b: bytes) -> bytes:
    if ruolo == "log":   # percorso del file temporaneo della JVM, diverso a ogni esecuzione
        return re.sub(rb"<sc:IdentificativoFornitura>.*?</sc:IdentificativoFornitura>", b"", b)
    if ruolo == "wri":
        return re.sub(rb"Data:\s*\d{1,2}/\d{1,2}/\d{4}", b"Data:", b, count=1)
    return b


@pytest.mark.java
@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
def test_stesse_uscite_con_e_senza_cache(cache, tmp_path, monkeypatch):
    """Sullo stesso XML (nomi di job diversi): prima esecuzione reale che popola la cache, seconda reale a cache
    disattivata, terza dalla cache. La terza coincide con la seconda salvo il file temporaneo nel _logSchema.xml e la
    data del rapporto."""
    xml = _a10().xml
    cp = str(Path(JAR) / "*")
    uscite = {}
    riusi = CACHE.statistiche["riusi"]
    for giro, nome, senza in (("popola", "ctl_" + "1" * 24, ""), ("reale", "ctl_" + "2" * 24, "1"),
                              ("cache", "ctl_" + "3" * 24, "")):
        monkeypatch.setenv(CACHE.ENV_SENZA_CACHE, senza)
        w = _lavoro(tmp_path / giro, nome, xml)
        base = [JAVA, "-Djava.awt.headless=true", f"-Djava.io.tmpdir={w / 'tmp'}", "-cp", cp]
        CACHE.esegui(base + [C.CLASSE_CONTROLLO, f"in/{nome}.xml", f"out/{nome}.xml", f"out/{nome}.dcm"], w, 600,
                     _esegui_reale)
        CACHE.esegui(base + [C.CLASSE_RAPPORTO, f"out/{nome}.dgn", "1"], w, 600, _esegui_reale)
        uscite[giro] = {r: _normalizza(r, (w / "out" / f"{nome}{s}").read_bytes().replace(nome.encode(), b"<NOME>"))
                        for r, s in (("dgn", ".dgn"), ("log", "_logSchema.xml"), ("wri", ".wri"), ("dcm", ".dcm"))}
        uscite[giro]["input_presente"] = (w / "in" / f"{nome}.xml").exists()
    assert CACHE.statistiche["riusi"] == riusi + 2           # .dgn/_logSchema/.dcm e .wri del terzo giro
    assert uscite["cache"] == uscite["reale"]
    dgn = C.leggi_dgn(C.decodifica(uscite["cache"]["dgn"]))
    assert C.valuta(dgn, C.leggi_esito_fornitura(uscite["cache"]["log"], valida=False))[0] == "positivo"
