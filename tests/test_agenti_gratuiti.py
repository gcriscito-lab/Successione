"""Lanciatore degli agenti gratuiti: protezioni e flusso, con un servizio FINTO in locale (simulazione, non FreeLLMAPI)."""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "agenti_gratuiti"))
import lancia as L  # noqa: E402

CHIAVE = "freellmapi-CHIAVE-DI-PROVA-NON-REALE-0123456789"
TEST_NUOVO = "def test_prova_agente():\n    assert 1 + 1 == 2\n"


class Finto:
    def __init__(self, risposte):
        self.risposte, self.richieste = list(risposte), []
        finto = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"data": [{"id": "auto"}, {"id": "modello-x"}]}).encode())

            def do_POST(self):
                n = int(self.headers.get("Content-Length", 0))
                finto.richieste.append((self.headers.get("Authorization"), json.loads(self.rfile.read(n))))
                r = finto.risposte.pop(0) if finto.risposte else finto.risposte_ultima
                finto.risposte_ultima = r
                self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"choices": [{"message": {"content": r}}]}).encode())

        self.srv = HTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_port}/v1"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def chiudi(self):
        self.srv.shutdown()


@pytest.fixture
def ambiente(monkeypatch):
    def imposta(url):
        monkeypatch.setenv("FREELLMAPI_BASE_URL", url); monkeypatch.setenv("FREELLMAPI_KEY", CHIAVE)
        monkeypatch.setenv("FREELLMAPI_MODEL", "auto")
    return imposta


def test_percorso_sicuro_accetta_solo_i_file_consentiti():
    ammessi = ["tests/test_valori_schema_extra.py", "docs/MANUALE_BREVE.md"]
    assert L.percorso_sicuro("docs/MANUALE_BREVE.md", ammessi) == "docs/MANUALE_BREVE.md"
    for cattivo in ("src/successioni/servizio.py", "../x", "/etc/passwd", "C:\\x", "docs/../src/x.py", "", None, "docs/MANUALE_BREVE.md\x00"):
        assert L.percorso_sicuro(cattivo, ammessi) is None


def test_compito_c4_file_consentiti_e_nuovi():
    c = L.leggi_compito("C4")
    assert c["ammessi"] == ["tests/test_valori_schema_extra.py"] and "tests/test_valori_schema_extra.py" in c["nuovi"]


def test_dry_run_non_chiama_il_servizio(capsys):
    assert L.main(["C4", "--dry-run"]) == 0
    assert "File consentiti" in capsys.readouterr().out


def test_senza_variabili_non_parte(monkeypatch, capsys):
    for v in ("FREELLMAPI_BASE_URL", "FREELLMAPI_KEY", "FREELLMAPI_MODEL"):
        monkeypatch.delenv(v, raising=False)
    assert L.main(["C4"]) == 2 and "mancanti" in capsys.readouterr().err


def test_elenco_modelli(ambiente, capsys):
    f = Finto([])
    try:
        ambiente(f.url)
        assert L.main(["--modelli"]) == 0
        assert "modello-x" in capsys.readouterr().out
    finally:
        f.chiudi()


def test_flusso_completo_patch_consegna_e_chiave_mai_scritta(ambiente, tmp_path):
    risposta = json.dumps({"modifiche": [{"file": "tests/test_valori_schema_extra.py", "contenuto": TEST_NUOVO}], "note": "ok"})
    f = Finto([risposta])
    try:
        ambiente(f.url)
        rc = L.main(["C4", "--out", str(tmp_path), "--max-iter", "2"])
    finally:
        f.chiudi()
    assert rc == 0
    cart = next(tmp_path.iterdir())
    patch = (cart / "consegna.patch").read_text()
    assert "tests/test_valori_schema_extra.py" in patch and "test_prova_agente" in patch
    cons = (cart / "CONSEGNA.md").read_text()
    assert "codice 0" in cons and "verifiche passate" in cons
    assert f.richieste[0][0] == f"Bearer {CHIAVE}"                       # la chiave viene usata solo nell'intestazione
    for p in cart.iterdir():
        assert CHIAVE not in p.read_text()                               # mai scritta nei risultati


def test_file_non_consentito_rifiutato_e_non_applicato(ambiente, tmp_path):
    risposta = json.dumps({"modifiche": [
        {"file": "src/successioni/servizio.py", "contenuto": "raise SystemExit('manomesso')\n"},
        {"file": "tests/test_valori_schema_extra.py", "contenuto": TEST_NUOVO}], "note": ""})
    f = Finto([risposta])
    try:
        ambiente(f.url)
        L.main(["C4", "--out", str(tmp_path), "--max-iter", "1"])
    finally:
        f.chiudi()
    cart = next(tmp_path.iterdir())
    patch = (cart / "consegna.patch").read_text()
    assert "servizio.py" not in patch and "manomesso" not in patch
    assert "file non consentito" in (cart / "CONSEGNA.md").read_text()


def test_risposta_non_json_non_produce_modifiche(ambiente, tmp_path):
    f = Finto(["non sono json"])
    try:
        ambiente(f.url)
        rc = L.main(["C4", "--out", str(tmp_path), "--max-iter", "2"])
    finally:
        f.chiudi()
    assert rc == 1                                                       # da rivedere: nessuna patch
    assert (next(tmp_path.iterdir()) / "consegna.patch").read_text().strip() == ""


def test_servizio_non_raggiungibile_messaggio_chiaro(ambiente, tmp_path, capsys):
    ambiente("http://127.0.0.1:9/v1")                                    # porta chiusa
    rc = L.main(["C4", "--out", str(tmp_path), "--max-iter", "1"])
    assert rc == 1
    assert "non raggiungibile" in (next(tmp_path.iterdir()) / "CONSEGNA.md").read_text()
