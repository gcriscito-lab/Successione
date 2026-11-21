"""Testo dell'interfaccia per i test che cercano funzioni o stringhe nel codice JavaScript.

Dal 21/11/2026 app.js e' diviso in piu' file per argomento: i test leggono tutti gli script elencati in index.html, nello stesso
ordine in cui li carica il browser (layout.js escluso: e' un file a se', con test propri)."""
import re
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "src" / "successioni" / "static"


def script_interfaccia() -> list[str]:
    """Nomi dei file caricati da index.html prima di layout.js, in ordine."""
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    nomi = re.findall(r'<script src="/static/([^"]+\.js)"></script>', html)
    return [n for n in nomi if n != "layout.js"]


def testo_interfaccia() -> str:
    return "\n".join((STATIC / n).read_text(encoding="utf-8") for n in script_interfaccia())
