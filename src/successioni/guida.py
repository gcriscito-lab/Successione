"""Guida in linea: le istruzioni ufficiali dell'Agenzia (copie in ``fonti/``, mai modificate) aperte alla pagina giusta, e le
informazioni sul programma (versioni, componenti, novita').

Le pagine sono pagine del PDF (il visualizzatore del browser le apre con ``#page=N``), ricavate dai titoli dei paragrafi dei
fascicoli il 2026-11-07. I file serviti sono solo quelli elencati in ``fonti/manifest.json`` e con l'impronta registrata.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
FONTI = RADICE / "fonti"
NOVITA = RADICE / "docs" / "NOVITA.md"

#: documento -> (titolo, percorso relativo a fonti/, descrizione)
DOCUMENTI = {
    "fascicolo1": ("Istruzioni - Fascicolo 1", "Istruzioni/Succ_FASCICOLO_I_Nov_23.pdf",
                   "Istruzioni ufficiali: dati generali, quadri EA-EI, liquidazione, allegati con codici e tabelle."),
    "fascicolo2": ("Istruzioni - Fascicolo 2", "Istruzioni/Succ_FASCICOLO_II_Nov_23.pdf",
                   "Quadri EL, EM (sistema tavolare), EN aziende, EO titoli, EP aeromobili, EQ navi."),
    "modello": ("Modello di dichiarazione", "Istruzioni/Modello Successione (1).pdf", "Il modello ufficiale da compilare."),
    "modifiche_istruzioni": ("Modifiche alle istruzioni", "Istruzioni/Elenco modifiche istruzioni fascicolo 1.pdf",
                             "Elenco delle modifiche al Fascicolo 1."),
    "specifiche": ("Specifiche tecniche SUC13", "Specifiche tecniche/Specifiche_SUC13_20250702.pdf",
                   "Tracciato del file telematico e regole di controllo."),
    "calcolo": ("Passaggi per il calcolo dell'imposta", "Specifiche tecniche/All. Specifiche tecniche (passaggi calcolo imposta di successione).pdf",
                "Allegato alle specifiche: come si calcola l'imposta di successione."),
    "modifiche_specifiche": ("Modifiche alle specifiche tecniche", "Specifiche tecniche/Elenco modifiche specifiche tecniche_15-07-2025.pdf",
                             "Elenco delle modifiche alle specifiche del 15/07/2025."),
}

#: argomenti: (titolo, documento, pagina PDF, quadro collegato o None)
ARGOMENTI = [
    ("Termini di presentazione", "fascicolo1", 4, None),
    ("Quali documenti occorrono", "fascicolo1", 6, None),
    ("Dati generali e frontespizio", "fascicolo1", 11, "AN"),
    ("Dati del defunto", "fascicolo1", 13, "AN"),
    ("Quadro EA - Eredi, chiamati, legatari", "fascicolo1", 17, "EA"),
    ("Quadro EB - Terreni", "fascicolo1", 20, "EB"),
    ("Devoluzione e valore quota (usufrutto, nuda proprietà)", "fascicolo1", 24, "DV"),
    ("Agevolazioni sui beni (prima casa e altre)", "fascicolo1", 25, None),
    ("Quadro EC - Fabbricati", "fascicolo1", 28, "EC"),
    ("Diritto di abitazione del coniuge", "fascicolo1", 31, None),
    ("Quadro ER - Rendite, crediti e altri beni", "fascicolo1", 33, "ER"),
    ("Quadro ED - Passività", "fascicolo1", 36, "ED"),
    ("Quadro EE - Prospetto riepilogativo", "fascicolo1", 39, "EE"),
    ("Quadro EF - Liquidazione delle imposte", "fascicolo1", 39, "EF"),
    ("Pagamento rateale", "fascicolo1", 48, None),
    ("Sanzioni e interessi", "fascicolo1", 49, None),
    ("Quadro EG - Documenti allegati", "fascicolo1", 49, "EG"),
    ("Quadro EH - Dichiarazioni sostitutive, agevolazioni", "fascicolo1", 51, "EH"),
    ("Quadro EI - Voltura catastale", "fascicolo1", 54, "EI"),
    ("Allegato 1 - Grado di parentela", "fascicolo1", 55, None),
    ("Allegato 2 - Agevolazioni e riduzioni", "fascicolo1", 56, None),
    ("Allegato 3 - Codici categoria e natura", "fascicolo1", 65, None),
    ("Allegato 4 - Codici diritto", "fascicolo1", 67, None),
    ("Allegato 5 - Devoluzione per legge", "fascicolo1", 69, None),
    ("Quadro EL - Terreni tavolari", "fascicolo2", 2, "EL"),
    ("Quadro EM - Fabbricati tavolari", "fascicolo2", 5, "EM"),
    ("Quadro EN - Aziende", "fascicolo2", 9, "EN"),
    ("Quadro EO - Titoli e quote sociali", "fascicolo2", 10, "EO"),
    ("Quadro EP - Aeromobili", "fascicolo2", 14, "EP"),
    ("Quadro EQ - Navi e imbarcazioni", "fascicolo2", 15, "EQ"),
]


def _manifest() -> dict[str, dict]:
    try:
        m = json.loads((FONTI / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {f["path"].removeprefix("fonti/"): f for f in m.get("files", [])}


def elenco() -> dict:
    man = _manifest()
    docs = []
    for k, (tit, rel, descr) in DOCUMENTI.items():
        p = FONTI / rel
        docs.append({"id": k, "titolo": tit, "descrizione": descr, "disponibile": p.is_file() and rel in man})
    disp = {d["id"] for d in docs if d["disponibile"]}
    argomenti = [{"titolo": t, "documento": d, "pagina": pg, "quadro": q} for t, d, pg, q in ARGOMENTI if d in disp]
    return {"documenti": docs, "argomenti": argomenti,
            "nota": "Copie dei documenti ufficiali dell'Agenzia delle Entrate fornite con il programma (fonti/manifest.json). "
                    "Le pagine indicate sono quelle del PDF."}


def file_documento(doc_id: str) -> bytes:
    """Il PDF ufficiale, solo se elencato nel manifest e con la stessa impronta (nessun file arbitrario dal disco)."""
    from .errori import NonTrovato
    if doc_id not in DOCUMENTI:
        raise NonTrovato("documento della guida non trovato")
    rel = DOCUMENTI[doc_id][1]
    voce = _manifest().get(rel)
    p = FONTI / rel
    if not voce or not p.is_file():
        raise NonTrovato("documento ufficiale non presente in questa installazione")
    dati = p.read_bytes()
    if hashlib.sha256(dati).hexdigest() != voce.get("sha256"):
        raise NonTrovato("il documento ufficiale non corrisponde all'impronta registrata: non viene mostrato")
    return dati


def _commit() -> dict | None:
    try:
        r = subprocess.run(["git", "-C", str(RADICE), "log", "-1", "--format=%h|%cs"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and "|" in r.stdout:
            h, d = r.stdout.strip().split("|", 1)
            return {"commit": h, "data": d}
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def informazioni(arch=None) -> dict:
    """Versioni e componenti, come la finestra «Informazioni» di ogni programma (componenti dalla diagnosi dell'ambiente)."""
    from . import __version__
    from .versioni import versioni
    from . import strumenti
    try:
        diag = strumenti.diagnosi(arch)
        componenti = [{"nome": v.get("nome"), "esito": v.get("stato"), "dettaglio": v.get("dettaglio")} for v in diag.get("voci", [])]
    except Exception as e:      # la finestra informazioni non deve mai fallire
        componenti = [{"nome": "Diagnosi", "esito": "avviso", "dettaglio": f"non disponibile: {e}"}]
    novita = NOVITA.read_text(encoding="utf-8") if NOVITA.is_file() else ""
    return {"programma": "Successioni", "versione": __version__, "versioni": versioni(), "build": _commit(),
            "python": platform.python_version(), "sistema": platform.platform(terse=True), "componenti": componenti,
            "archivio": str(arch.base) if arch is not None else None, "novita": novita,
            "avvertenza": "Il programma prepara la dichiarazione; i controlli interni non sostituiscono il controllo ufficiale "
                          "dell'Agenzia delle Entrate né la verifica del professionista."}
