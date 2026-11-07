"""Esegue tutte le prove dell'interfaccia nel browser (Playwright per Node) su dati SINTETICI.

Uso, dalla radice del repository:
    .venv\\Scripts\\python.exe tests\\e2e\\esegui_tutti.py

Requisiti una tantum: Node.js, `npm install -g playwright`, `npx playwright install chromium`.
Crea un archivio nuovo in build/gui_fix_data, avvia tests/e2e/server.py sulla porta 8813,
prepara le fixture, lancia ogni script e chiude il server. Nessun invio o controllo ufficiale.
"""
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATI = ROOT / "build" / "gui_fix_data"
PROVE = ["gui_flusso", "gui_regressioni", "gui_cf_tardivo", "gui_layout_20261103", "gui_aspetto", "gui_review_20261103", "gui_valore_catastale", "gui_review2", "gui_albero", "gui_miglioramenti_replica", "gui_guida", "gui_calcolatrice", "gui_review3"]


def _attendi_server(url="http://127.0.0.1:8813/", secondi=60):
    fine = time.time() + secondi
    while time.time() < fine:
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except urllib.error.HTTPError:
            return                                  # risponde (anche 401): il server e' su
        except OSError:
            time.sleep(0.5)
    raise SystemExit("Il server di prova non risponde sulla porta 8813.")


def main():
    npm = shutil.which("npm")
    if not npm or not shutil.which("node"):
        raise SystemExit("Node.js non trovato: installalo prima di eseguire le prove.")
    node_path = subprocess.run([npm, "root", "-g"], capture_output=True, text=True, check=True).stdout.strip()
    shutil.rmtree(DATI, ignore_errors=True)
    (ROOT / "build" / "gui_review_fixture.json").unlink(missing_ok=True)
    env = {**os.environ, "SUCCESSIONI_DATA": str(DATI), "PYTHONPATH": str(ROOT / "src"), "NODE_PATH": node_path}
    server = subprocess.Popen([sys.executable, str(ROOT / "tests/e2e/server.py")], cwd=ROOT, env=env)
    esiti = {}
    try:
        _attendi_server()
        subprocess.run([sys.executable, str(ROOT / "tests/e2e/prepara_review.py")], cwd=ROOT, env=env, check=True)
        for nome in PROVE:
            args = ["node", f"tests/e2e/{nome}.js"] + ([f"build/{nome}.png"] if nome == "gui_flusso" else [])
            r = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", timeout=300)
            esiti[nome] = r.returncode == 0
            print(f"{'PASSATO' if esiti[nome] else 'FALLITO'}  {nome}")
            if r.returncode:
                print((r.stdout + r.stderr)[-2000:])
    finally:
        server.terminate()
        server.wait(timeout=10)
    falliti = [n for n, ok in esiti.items() if not ok]
    print(f"\n{len(esiti) - len(falliti)}/{len(PROVE)} prove dell'interfaccia passate (dati sintetici, browser Chromium).")
    sys.exit(1 if falliti or len(esiti) < len(PROVE) else 0)


if __name__ == "__main__":
    main()
