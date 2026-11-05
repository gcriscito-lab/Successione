"""Stampa del modello ministeriale SUC13 compilato, prodotta dal codice Java ufficiale del componente di controllo.

Il PDF e' l'overlay dei valori sui modelli PDF dell'Agenzia (template Jasper del componente), ottenuto dallo stesso XML del file
telematico: nessun posizionamento dei campi e' riscritto qui. Richiede il componente configurato (``SUCCESSIONI_CONTROLLI_SUC13``)
e Java 8 (``SUCCESSIONI_JAVA``), come il controllo ufficiale. Il driver ``java/StampaModello.java`` e' compilato da
``scripts/compila_stampa.py``; la classe compilata e' versionata.

Perimetro e limiti: la stampa e' un prodotto LOCALE; la fedelta' visiva va verificata per i quadri usati (gli allegati EG compaiono
come flag, non come pagine). Non e' una verifica con l'Agenzia ne' una firma.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..errori import DatiNonValidi
from .controllo import ENV_JAR, ENV_JAVA

DIR_CLASSE = Path(__file__).resolve().parent / "java"
CLASSE = "StampaModello"
FONTE = ("componente di controllo SUC13 2.3.1 (print-model-1.2.jar, suc-converter-1.0.jar, ResSUC13.jar): "
         "PrintModel/SUCConverter, verificato il 2026-11-05")


@dataclass
class StampaModello:
    pdf: bytes
    pagine: int
    log: str


def disponibile(env: dict | None = None) -> str | None:
    """``None`` se la stampa si puo' eseguire, altrimenti il motivo."""
    env = os.environ if env is None else env
    if not (env.get(ENV_JAVA) or shutil.which("java")):
        return "Java non trovato (SUCCESSIONI_JAVA)"
    cart = env.get(ENV_JAR)
    if not cart or not (Path(cart) / "print-model-1.2.jar").is_file():
        return "componente di controllo SUC13 non configurato o senza il modulo di stampa (SUCCESSIONI_CONTROLLI_SUC13)"
    if not (DIR_CLASSE / f"{CLASSE}.class").is_file():
        return "driver di stampa non compilato (scripts/compila_stampa.py)"
    return None


def genera(xml: bytes, *, timeout: int = 300, env: dict | None = None) -> StampaModello:
    """PDF del modello compilato dall'XML. ``DatiNonValidi`` se l'ambiente manca o la stampa non riesce."""
    env = os.environ if env is None else env
    perche = disponibile(env)
    if perche:
        raise DatiNonValidi("stampa del modello non disponibile: " + perche)
    java = env.get(ENV_JAVA) or shutil.which("java")
    cp = os.pathsep.join([str(DIR_CLASSE), str(Path(env[ENV_JAR]) / "*")])
    with tempfile.TemporaryDirectory(prefix="stampa_") as t:
        lavoro = Path(t)
        (lavoro / "in.xml").write_bytes(xml)
        try:
            p = subprocess.run([java, "-Djava.awt.headless=true", f"-Djava.io.tmpdir={lavoro}", "-cp", cp, CLASSE,
                                "in.xml", "out.pdf"], cwd=lavoro, capture_output=True, timeout=timeout, check=False,
                               env={**os.environ, "JAVA_TOOL_OPTIONS": ""})
        except subprocess.TimeoutExpired:
            raise DatiNonValidi("stampa del modello: tempo scaduto", timeout_s=timeout) from None
        out = lavoro / "out.pdf"
        log = (p.stdout + p.stderr).decode("utf-8", "replace")
        if p.returncode != 0 or not out.is_file() or not out.read_bytes().startswith(b"%PDF"):
            raise DatiNonValidi("stampa del modello non riuscita", codice_uscita=p.returncode, log=log[-1500:])
        pdf = out.read_bytes()
    from pypdf import PdfReader
    import io
    return StampaModello(pdf, len(PdfReader(io.BytesIO(pdf)).pages), log[-4000:])
