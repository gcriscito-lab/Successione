"""Impostazioni del programma: percorsi degli strumenti esterni (Java, controllo SUC13, Ghostscript, veraPDF, qpdf, profilo ICC,
fonti) e tempo massimo del controllo, con stato di rilevamento e salvataggio nel file di configurazione.

Il file e' lo stesso letto dall'avviatore (`scripts/windows/avvia_successioni.py`, variabile `SUCCESSIONI_CONFIG`; in
mancanza, `configurazione.json` nella cartella dei dati). Contiene SOLO le variabili elencate in `VOCI`: percorsi e un numero.
Nessuna credenziale, certificato o password vi puo' essere scritto: una chiave non elencata e' rifiutata.

Una modifica vale subito (si aggiorna l'ambiente del processo) e al prossimo avvio; se all'avvio esiste una variabile
d'ambiente esterna con lo stesso nome, quella prevale sul file (regola dell'avviatore). La cartella dei dati si mostra ma non si cambia da qui, perche' cambiarla a
programma aperto nasconderebbe le pratiche esistenti.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from pathlib import Path

from .errori import DatiNonValidi

# chiave, etichetta, tipo (file | cartella | numero | sola_lettura), spiegazione
VOCI: tuple[tuple[str, str, str, str], ...] = (
    ("SUCCESSIONI_DATA", "Cartella dei dati", "sola_lettura",
     "Dove sono pratiche e allegati. Si cambia solo all'avvio, con la variabile d'ambiente SUCCESSIONI_DATA."),
    ("SUCCESSIONI_JAVA", "Java (java.exe)", "file",
     "Serve al controllo ufficiale SUC13. Il componente ufficiale e' provato con Java 8."),
    ("SUCCESSIONI_CONTROLLI_SUC13", "Cartella del controllo SUC13", "cartella",
     "Cartella con i JAR del controllo scaricati dal sito dell'Agenzia (controlliXMLREG2013.jar e gli altri)."),
    ("SUCCESSIONI_CONTROLLI_TIMEOUT", "Tempo massimo del controllo (secondi)", "numero",
     "Da 10 a 7200. Predefinito 600."),
    ("SUCCESSIONI_GS", "Ghostscript", "file", "Conversione dei documenti in PDF/A."),
    ("SUCCESSIONI_VERAPDF", "veraPDF", "file", "Verifica indipendente della conformita' PDF/A."),
    ("SUCCESSIONI_QPDF", "qpdf", "file", "Controlli strutturali e suddivisione dei PDF."),
    ("SUCCESSIONI_ICC", "Profilo colore sRGB (.icc)", "file", "Di solito rilevato da Ghostscript; serve alla conversione PDF/A."),
    ("SUCCESSIONI_FONTI", "Cartella delle fonti ufficiali", "cartella", "Specifiche e moduli dell'Agenzia usati dal programma."),
)
CHIAVI = {v[0]: v for v in VOCI}
_ESEMPIO = {"SUCCESSIONI_JAVA": "java.exe", "SUCCESSIONI_GS": "gswin64c.exe", "SUCCESSIONI_VERAPDF": "verapdf.bat",
            "SUCCESSIONI_QPDF": "qpdf.exe", "SUCCESSIONI_ICC": "srgb.icc"}
MINIMO_TIMEOUT, MASSIMO_TIMEOUT = 10, 7200
# Nome del file ammesso per ciascuno strumento: l'impostazione sceglie QUALE programma eseguire, quindi non si accetta un
# eseguibile qualunque (es. cmd.exe o calc.exe al posto di Java). Il controllo e' sul nome, non sul contenuto del file.
NOMI_AMMESSI = {
    "SUCCESSIONI_JAVA": re.compile(r"java(w)?(\.exe)?", re.I),
    "SUCCESSIONI_GS": re.compile(r"gs(win(32|64))?c?(\.exe)?", re.I),
    "SUCCESSIONI_VERAPDF": re.compile(r"verapdf(\.(bat|cmd|exe|sh))?", re.I),
    "SUCCESSIONI_QPDF": re.compile(r"qpdf(\.exe)?", re.I),
    "SUCCESSIONI_ICC": re.compile(r".+\.(icc|icm)", re.I),
}


def file_configurazione() -> Path:
    env = os.environ.get("SUCCESSIONI_CONFIG")
    if env:
        return Path(env)
    from .archivio import cartella_dati
    return cartella_dati() / "configurazione.json"


def _leggi_file() -> dict:
    """Tutto il contenuto del file (anche chiavi non note: si conservano), o {} se manca o non e' leggibile."""
    try:
        d = json.loads(file_configurazione().read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def _leggi_file_stretto() -> dict:
    """Come `_leggi_file`, ma un file che esiste e non e' un oggetto JSON valido e' un errore: riscriverlo cancellerebbe in
    silenzio le impostazioni che contiene."""
    p = file_configurazione()
    if not p.exists():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        raise DatiNonValidi(f"il file di configurazione {p} non e' leggibile ({type(e).__name__}): correggerlo o rimuoverlo "
                            "prima di salvare, per non perdere le impostazioni che contiene") from None
    if not isinstance(d, dict):
        raise DatiNonValidi(f"il file di configurazione {p} non contiene un oggetto JSON: correggerlo o rimuoverlo prima di salvare")
    return d


def _esiste(tipo: str, valore: str) -> bool:
    if tipo == "cartella":
        return Path(valore).is_dir()
    if tipo == "file":
        return Path(valore).is_file() or bool(shutil.which(valore))
    return True


def _dettaglio(chiave: str, valore: str | None) -> tuple[bool, str]:
    """(a posto?, descrizione) con le stesse funzioni che il programma usa per trovare lo strumento."""
    from . import pdfa
    from .documenti import dimensioni
    if chiave == "SUCCESSIONI_DATA":
        from .archivio import cartella_dati
        return True, str(cartella_dati())
    if chiave == "SUCCESSIONI_JAVA":
        from .collegamenti.controllo import ConfigControllo
        j = ConfigControllo.da_ambiente().java
        return (True, f"in uso: {j}") if j else (False, "Java non trovato: il controllo ufficiale non e' eseguibile")
    if chiave == "SUCCESSIONI_CONTROLLI_SUC13":
        from .collegamenti import controllo
        if not valore:
            return False, "non impostata: il controllo ufficiale non e' eseguibile"
        try:
            richiesti = controllo.jar_richiesti()
        except (OSError, ValueError):
            return Path(valore).is_dir(), "cartella presente; elenco dei JAR richiesti non verificabile (fonti non trovate)"
        mancanti = [j for j in richiesti if not (Path(valore) / j).is_file()]
        return (not mancanti, "tutti i JAR richiesti sono presenti" if not mancanti
                else f"mancano {len(mancanti)} di {len(richiesti)} JAR: " + ", ".join(mancanti[:4]) + (" ..." if len(mancanti) > 4 else ""))
    if chiave == "SUCCESSIONI_CONTROLLI_TIMEOUT":
        return True, f"{valore or 600} secondi"
    trovato = {"SUCCESSIONI_GS": pdfa.trova_gs, "SUCCESSIONI_VERAPDF": pdfa.trova_verapdf,
               "SUCCESSIONI_QPDF": dimensioni.trova_qpdf, "SUCCESSIONI_ICC": pdfa._icc}.get(chiave)
    if trovato is not None:
        t = trovato()
        return (True, f"in uso: {t}") if t else (False, "non trovato")
    if chiave == "SUCCESSIONI_FONTI":
        from .collegamenti import controllo
        p = controllo.percorso_jnlp()
        return (p.is_file(), f"in uso: {controllo._radice_fonti()}" if p.is_file() else f"fonti non trovate in {controllo._radice_fonti()}")
    return True, ""


def stato() -> dict:
    """Impostazioni correnti, con origine del valore e stato di rilevamento di ciascuno strumento."""
    nel_file = _leggi_file()
    voci = []
    for chiave, etichetta, tipo, nota in VOCI:
        valore = os.environ.get(chiave) or None
        if valore is None:
            origine = "non impostato"
        elif chiave in nel_file and nel_file[chiave] == valore:
            origine = "file di configurazione"
        else:
            origine = "ambiente o rilevamento automatico"
        ok, descr = _dettaglio(chiave, valore)
        voci.append({"chiave": chiave, "etichetta": etichetta, "tipo": tipo, "nota": nota, "valore": valore,
                     "salvato": nel_file.get(chiave) if isinstance(nel_file.get(chiave), str) else None,
                     "origine": origine, "a_posto": ok, "dettaglio": descr,
                     "modificabile": tipo != "sola_lettura"})
    return {"file": str(file_configurazione()), "voci": voci}


def _valida(chiave: str, valore) -> str:
    voce = CHIAVI.get(chiave)
    if voce is None:
        raise DatiNonValidi(f"impostazione sconosciuta: {chiave!r}", ammesse=[v[0] for v in VOCI if v[2] != "sola_lettura"])
    if voce[2] == "sola_lettura":
        raise DatiNonValidi(f"{voce[1]}: non modificabile da qui", chiave=chiave)
    if not isinstance(valore, str):
        raise DatiNonValidi(f"{voce[1]}: atteso un testo", chiave=chiave)
    v = valore.strip().strip('"')
    if not v:
        return ""
    if "\x00" in v or "\n" in v or "\r" in v:
        raise DatiNonValidi(f"{voce[1]}: caratteri non ammessi nel percorso", chiave=chiave)
    if voce[2] == "numero":
        try:
            n = int(v)
        except ValueError:
            raise DatiNonValidi(f"{voce[1]}: atteso un numero intero", chiave=chiave) from None
        if not MINIMO_TIMEOUT <= n <= MASSIMO_TIMEOUT:
            raise DatiNonValidi(f"{voce[1]}: da {MINIMO_TIMEOUT} a {MASSIMO_TIMEOUT} secondi", chiave=chiave)
        return str(n)
    if not _esiste(voce[2], v):
        raise DatiNonValidi(f"{voce[1]}: {'cartella' if voce[2] == 'cartella' else 'file'} non trovato: {v}", chiave=chiave)
    nome = NOMI_AMMESSI.get(chiave)
    if nome is not None and not nome.fullmatch(Path(v).name):
        raise DatiNonValidi(f"{voce[1]}: il file deve avere il nome dello strumento (es. {_ESEMPIO[chiave]}), non {Path(v).name!r}",
                            chiave=chiave)
    return v


def salva(modifiche: dict) -> dict:
    """Applica e salva le modifiche (valore vuoto = rimuove l'impostazione). Tutto o niente: se un valore e' errato non si
    scrive nulla. Restituisce lo stato aggiornato piu' gli eventuali `avvisi`."""
    if not isinstance(modifiche, dict) or not modifiche:
        raise DatiNonValidi("nessuna modifica indicata")
    nuove = {k: _valida(k, v) for k, v in modifiche.items()}
    contenuto = _leggi_file_stretto()
    avvisi = []
    for k, v in nuove.items():
        if v:
            contenuto[k] = v
        else:
            contenuto.pop(k, None)
    destinazione = file_configurazione()
    try:
        destinazione.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=destinazione.parent, suffix=".tmp", delete=False) as f:
            json.dump(contenuto, f, ensure_ascii=False, indent=2)
            temp = Path(f.name)
        os.replace(temp, destinazione)
    except OSError as e:
        raise DatiNonValidi(f"impossibile scrivere il file di configurazione {destinazione}: {e}") from None
    for k, v in nuove.items():
        attuale = os.environ.get(k)
        if v:
            os.environ[k] = v
        elif attuale is not None:
            os.environ.pop(k, None)
            avvisi.append(f"{CHIAVI[k][1]}: rimossa; al prossimo avvio puo' essere rilevata di nuovo in automatico")
    r = stato()
    r["avvisi"] = avvisi
    return r
