"""A02 su Linux: pratica con allegati, backup con il comando reale, ripristino in una cartella nuova, confronto.

Il ripristino segue la procedura sicura del manuale (copia della cartella di backup come nuova cartella dati):
non esiste ancora un comando `ripristina` (proposta in docs/PROPOSTE_installazione.md). Prova locale: il
collaudo A02 su Windows resta da eseguire (docs/INSTALLAZIONE_WINDOWS.md, prova riprendibile).
"""
import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

RADICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RADICE / "scripts" / "windows"))
sys.path.insert(0, str(Path(__file__).parent))
VB = importlib.import_module("verifica_backup")
from telematico_casi import caso_completo  # noqa: E402
from successioni import pdfa  # noqa: E402
from successioni.archivio import Archivio  # noqa: E402
from successioni.servizio import Servizio  # noqa: E402

CF_FORN = "RSSNNA70A41H501X"


def _pdf(percorso: Path, pagine: int):
    c = canvas.Canvas(str(percorso), pagesize=A4)
    for i in range(pagine):
        c.drawString(72, 760, f"Certificato sintetico - pagina {i + 1} - Citta' di prova")
        c.showPage()
    c.save()


def _ops(d: dict) -> list[dict]:
    ops = []
    for coll in ("persone", "beni", "devoluzioni", "passivita", "documenti_ref"):
        for e in d.get(coll, []):
            ops.append({"op": "upsert", "coll": coll, "id": e["id"],
                        "campi": {k: v for k, v in e.items() if k not in ("id", "_origine")}})
    ops.append({"op": "set", "sezione": "opzioni", "campi": dict(d.get("opzioni", {}))})
    return ops


@pytest.fixture(scope="module")
def scenario(tmp_path_factory):
    radice = tmp_path_factory.mktemp("a02")
    d1 = radice / "Studio Bianchi è" / "dati originali"
    sv = Servizio(Archivio(d1))
    pid = sv.crea_pratica("Successione sintetica A02", iniziali=_ops(caso_completo()))["pratica_id"]
    rev = sv.leggi(pid)["revisione"]
    sv.aggiorna(pid, rev, [{"op": "set", "sezione": "note", "campi": {"promemoria": "via MCP"}}],
                chiave="a02-mcp-1", autore="assistente", canale="mcp")
    pdf = radice / "certificato di morte è.pdf"
    _pdf(pdf, 3)
    orig = sv.acquisisci_file(pid, pdf, tipo_eg="certificato", finalita="prova A02")
    derivato = sv.prepara_pdfa(orig["allegato_id"]) if pdfa.trova_gs() else None
    export = sv.esporta(pid, cf_fornitore=CF_FORN, scopo="bozza_tecnica")
    backup = radice / "Backup del 1 novembre" / "Successioni"
    env = {k: v for k, v in os.environ.items() if not k.startswith("SUCCESSIONI_")}
    env["SUCCESSIONI_DATA"] = str(d1)
    r = subprocess.run([sys.executable, "-m", "successioni.cli", "backup", str(backup)], env=env,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    d2 = radice / "PC nuovo" / "Successioni ripristinata"          # procedura sicura: copia della cartella
    shutil.copytree(backup, d2)
    return {"d1": d1, "d2": d2, "backup": backup, "pid": pid, "orig": orig, "derivato": derivato,
            "export": export, "stdout_backup": r.stdout}


def test_a02_backup_integro_e_ripristino_identico(scenario):
    v_backup = VB.verifica(scenario["backup"])
    assert v_backup["integrita_db"] == "ok"
    assert v_backup["allegati"]["mancanti"] == [] and v_backup["allegati"]["alterati"] == []
    assert v_backup["allegati"]["file_verificati"] == v_backup["allegati"]["righe"] >= 1
    assert VB.confronta(VB.verifica(scenario["d1"]), VB.verifica(scenario["d2"])) == []


def test_a02_pratica_revisioni_e_allegati_riaperti_dopo_ripristino(scenario):
    a, b = Servizio(Archivio(scenario["d1"])), Servizio(Archivio(scenario["d2"]))
    pid = scenario["pid"]
    pa, pb = a.leggi(pid), b.leggi(pid)
    assert pa == pb and pb["dati"]["note"]["promemoria"] == "via MCP"
    assert a.revisioni(pid) == b.revisioni(pid) and [r["canale"] for r in b.revisioni(pid)] == ["gui", "mcp"]
    la, lb = a.elenca_allegati(pid), b.elenca_allegati(pid)
    assert [(x["allegato_id"], x["sha256"], x["ruolo"]) for x in la] == \
           [(x["allegato_id"], x["sha256"], x["ruolo"]) for x in lb]
    with Archivio(scenario["d2"]).lettura() as c:
        percorsi = [r["percorso"] for r in c.execute("SELECT percorso FROM allegati")]
    for perc in percorsi:                                      # pagine identiche in ogni file ripristinato
        f1, f2 = scenario["d1"] / perc, scenario["d2"] / perc
        assert f1.read_bytes() == f2.read_bytes()
        assert len(PdfReader(f2).pages) == len(PdfReader(f1).pages) == 3
    # revisione comune anche dopo il ripristino: la prima modifica parte dalla revisione salvata
    r = b.aggiorna(pid, pb["revisione"], [{"op": "set", "sezione": "note", "campi": {"dopo": "ripristino"}}])
    assert r["revisione"] == pb["revisione"] + 1


def test_a02_interfaccia_sul_ripristino(scenario):
    from starlette.testclient import TestClient
    from successioni.web import crea_app
    app = crea_app(Servizio(Archivio(scenario["d2"])), token="t", porta=8765)
    with TestClient(app) as cl:
        r = cl.get(f"/api/pratiche/{scenario['pid']}?t=t")
        assert r.status_code == 200 and r.json()["titolo"] == "Successione sintetica A02"
        assert len(cl.get(f"/api/pratiche/{scenario['pid']}/allegati?t=t").json()) >= 1


@pytest.mark.xfail(strict=True, reason="difetto D1 (docs/PROPOSTE_installazione.md): il backup copia solo "
                                       "database e allegati/, non elaborati/ dove sono gli XML esportati")
def test_a02_xml_esportato_presente_dopo_ripristino(scenario):
    exp = scenario["export"]
    assert exp["generato"] and (scenario["d1"] / exp["percorso"]).exists()
    assert (scenario["d2"] / exp["percorso"]).exists()


def test_a02_verifica_backup_segnala_i_file_dei_job_mancanti(scenario):
    """Finche' D1 e' aperto, lo strumento di verifica deve dirlo invece di dichiarare il backup integro."""
    v = VB.verifica(scenario["backup"])
    if (scenario["backup"] / scenario["export"]["percorso"]).exists():
        assert v["esito"] == "integro"
    else:
        assert v["esito"] == "incompleto"
        assert any(scenario["export"]["percorso"] in m for m in v["file_dei_job"]["mancanti"])


def test_verifica_backup_rileva_allegato_alterato(tmp_path, scenario):
    copia = tmp_path / "copia alterata"
    shutil.copytree(scenario["backup"], copia)
    with Archivio(copia).lettura() as c:
        perc = c.execute("SELECT percorso FROM allegati LIMIT 1").fetchone()[0]
    f = copia / perc
    f.write_bytes(f.read_bytes()[:-10] + b"0123456789")
    v = VB.verifica(copia)
    assert v["esito"] == "danneggiato" and perc in v["allegati"]["alterati"]
