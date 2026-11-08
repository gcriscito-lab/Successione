"""Impostazioni del programma: percorsi degli strumenti esterni (Java, controllo SUC13, Ghostscript, veraPDF, qpdf, profilo ICC,
fonti) e tempo massimo del controllo, con stato di rilevamento e salvataggio nel file di configurazione.

Il file e' lo stesso letto dall'avviatore (`scripts/windows/avvia_successioni.py`, variabile `SUCCESSIONI_CONFIG`; in
mancanza, `configurazione.json` nella cartella dei dati). Contiene le variabili elencate in `VOCI` e le preferenze
grafiche validate nella sezione `interfaccia` (non diventano variabili d'ambiente).
Nessuna credenziale, certificato o password vi puo' essere scritto: una chiave non elencata e' rifiutata.

Una modifica vale subito (si aggiorna l'ambiente del processo) e al prossimo avvio; se all'avvio esiste una variabile
d'ambiente esterna con lo stesso nome, quella prevale sul file (regola dell'avviatore). La cartella dei dati si mostra ma non si cambia da qui, perche' cambiarla a
programma aperto nasconderebbe le pratiche esistenti.
"""
from __future__ import annotations

import json
import os
import time
import threading
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
    ("SUCCESSIONI_DESKTOP_TELEMATICO", "Cartella di Desktop Telematico", "cartella",
     "Serve per dare istruzioni di invio con i percorsi giusti (Autentica e Invio si fanno nello strumento ufficiale). Se vuota, il programma "
     "la cerca nelle posizioni consuete (es. C:\\DesktopTelematico\\DesktopTelematico)."),
    ("SUCCESSIONI_ENTRATEL_MULTIFILE", "Cartella di Entratel-Multifile", "cartella",
     "Facoltativa: alternativa a Desktop Telematico per autenticare e inviare. Deve contenere la sottocartella prog."),
    ("SUCCESSIONI_BACKUP", "Cartella dei backup", "cartella",
     "Dove si salvano le copie di sicurezza. Per proteggersi da un guasto del disco scegli un'altra unita' o un disco esterno; "
     "se vuota, accanto alla cartella dei dati."),
    ("SUCCESSIONI_FONTI", "Cartella delle fonti ufficiali", "cartella", "Specifiche e moduli dell'Agenzia usati dal programma."),
)
CHIAVI = {v[0]: v for v in VOCI}
_ESEMPIO = {"SUCCESSIONI_JAVA": "java.exe", "SUCCESSIONI_GS": "gswin64c.exe", "SUCCESSIONI_VERAPDF": "verapdf.bat",
            "SUCCESSIONI_QPDF": "qpdf.exe", "SUCCESSIONI_ICC": "srgb.icc"}
MINIMO_TIMEOUT, MASSIMO_TIMEOUT = 10, 7200
INTERFACCIA_DEFAULT = {"tema": "sistema", "font": "sistema", "dimensione": 14,
                       "interlinea": "normale", "larghezza_pannello": 360, "larghezza_nav": 240,
                       # personalizzazione dell'app
                       "accento": "predefinito", "densita": "normale", "contrasto": "normale", "movimento": "normale",
                       "avvio": "elenco", "nome_studio": "", "quadri_predefiniti": [],
                       # versione 0.3: pannello della riga a destra (come prima) o sotto l'elenco, a tutta larghezza
                       "disposizione": "destra", "altezza_pannello": 380}
LUNGHEZZA_NOME_STUDIO = 60
QUADRI_SCEGLIBILI = ("EA", "EB", "EC", "ER", "ED", "EF", "EG", "EH", "EI", "EL", "EM", "EN", "EO", "EP", "EQ")
# Intervalli (minimo, massimo) in pixel dei valori numerici; "dimensione" e' la grandezza del carattere.
INTERVALLI_INTERFACCIA = {"dimensione": (12, 22), "larghezza_pannello": (280, 760), "larghezza_nav": (180, 480),
                          "altezza_pannello": (200, 900)}
SCELTE_INTERFACCIA = {"tema": ("sistema", "chiaro", "scuro", "seppia"),
                      "font": ("sistema", "segoe", "arial", "verdana", "georgia", "consolas"),
                      "interlinea": ("compatta", "normale", "ampia"),
                      "accento": ("predefinito", "blu", "verde", "viola", "arancio", "rosso", "grafite"),
                      "densita": ("compatta", "normale", "ampia"), "contrasto": ("normale", "alto"),
                      "movimento": ("normale", "ridotto"), "avvio": ("elenco", "ultima"),
                      "disposizione": ("destra", "sotto")}


def _valida_interfaccia(valori: dict) -> dict:
    if not isinstance(valori, dict):
        raise DatiNonValidi("preferenze dell'interfaccia: atteso un oggetto")
    for k, v in valori.items():
        if k not in INTERFACCIA_DEFAULT:
            raise DatiNonValidi(f"preferenza dell'interfaccia sconosciuta: {k}")
        if k == "nome_studio":
            if not isinstance(v, str) or len(v) > LUNGHEZZA_NOME_STUDIO or any(ord(c) < 32 for c in v):
                raise DatiNonValidi(f"nome_studio: testo di al massimo {LUNGHEZZA_NOME_STUDIO} caratteri, senza a capo")
        elif k == "quadri_predefiniti":
            if (not isinstance(v, list) or any(q not in QUADRI_SCEGLIBILI for q in v) or len(set(v)) != len(v)):
                raise DatiNonValidi("quadri_predefiniti: elenco senza ripetizioni di quadri fra " + ", ".join(QUADRI_SCEGLIBILI))
        elif k in SCELTE_INTERFACCIA:
            if v not in SCELTE_INTERFACCIA[k]:
                raise DatiNonValidi(f"{k}: valore non ammesso")
        else:
            minimo, massimo = INTERVALLI_INTERFACCIA[k]
            if isinstance(v, bool) or not isinstance(v, int) or not minimo <= v <= massimo:
                raise DatiNonValidi(f"{k}: indicare un intero da {minimo} a {massimo}")
    return {k: (list(v) if isinstance(v, list) else v) for k, v in valori.items()}


def preferenze_interfaccia(contenuto: dict) -> dict:
    valori = contenuto.get("interfaccia", {})
    try:
        return {**INTERFACCIA_DEFAULT, **_valida_interfaccia(valori)}
    except DatiNonValidi:
        return INTERFACCIA_DEFAULT.copy()
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
    if chiave in ("SUCCESSIONI_DESKTOP_TELEMATICO", "SUCCESSIONI_ENTRATEL_MULTIFILE"):
        from . import strumenti
        if not valore:
            return False, "non trovato nelle posizioni consuete (facoltativo: serve per le istruzioni di invio)"
        return strumenti.controllo_cartella(chiave, valore)
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


# Preferenze di operativita' e sicurezza (sezione "preferenze" del file di configurazione).
#   pulizia_automatica  bool    elimina i file temporanei e di lavoro (copie di XML, uscite del controllo) piu' vecchi di pulizia_ore
#   pulizia_ore         int     eta' minima in ore dei file temporanei da eliminare (1-720)
#   avviso_visura_giorni int    avvisa se la visura catastale di un bene e' piu' vecchia di tanti giorni (30-365; il Fascicolo chiede 90)
#   visura_blocca       bool    se vero, una visura vecchia o senza data blocca la finalizzazione invece di essere solo un avviso
#   mcp_sola_lettura    bool    Claude (MCP) puo' leggere ma non modificare pratiche, file e archivio
PREFERENZE_DEFAULT = {"pulizia_automatica": True, "pulizia_ore": 24, "avviso_visura_giorni": 90, "visura_blocca": False,
                      "mcp_sola_lettura": False}
INTERVALLI_PREFERENZE = {"pulizia_ore": (1, 720), "avviso_visura_giorni": (30, 365)}


def _valida_preferenze(p) -> dict:
    if not isinstance(p, dict):
        raise DatiNonValidi("preferenze: atteso un oggetto")
    for k, v in p.items():
        if k not in PREFERENZE_DEFAULT:
            raise DatiNonValidi(f"preferenza sconosciuta: {k}", ammesse=list(PREFERENZE_DEFAULT))
        if isinstance(PREFERENZE_DEFAULT[k], bool):
            if not isinstance(v, bool):
                raise DatiNonValidi(f"{k}: atteso vero o falso")
        else:
            minimo, massimo = INTERVALLI_PREFERENZE[k]
            if isinstance(v, bool) or not isinstance(v, int) or not minimo <= v <= massimo:
                raise DatiNonValidi(f"{k}: indicare un intero da {minimo} a {massimo}")
    return dict(p)


def percorso_configurazione(cartella_dati: Path | str | None = None) -> Path:
    """File di configurazione in uso per la cartella dati indicata (SUCCESSIONI_CONFIG prevale)."""
    env = os.environ.get("SUCCESSIONI_CONFIG")
    return Path(env) if env else (Path(cartella_dati) / "configurazione.json" if cartella_dati else file_configurazione())


def sola_lettura_da_ambiente() -> bool:
    return os.environ.get("SUCCESSIONI_MCP_SOLA_LETTURA", "").strip().lower() in ("1", "true", "si", "yes")


def leggi_preferenze(cartella_dati: Path | str | None = None) -> tuple[dict, str | None]:
    """(preferenze con i predefiniti, problema). ``problema`` e' None se il file manca o e' valido; altrimenti descrive perche'
    il file esiste ma non si legge, non e' un oggetto JSON o ha una sezione/valore di preferenza non valido. Chi deve essere
    prudente (server MCP: sola lettura) usa ``problema`` per scegliere il comportamento sicuro (fail-closed)."""
    f = percorso_configurazione(cartella_dati)
    valori = dict(PREFERENZE_DEFAULT)
    problema = None
    try:
        testo = f.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        testo = None
    except OSError as e:
        testo, problema = None, f"il file di configurazione {f} non e' leggibile ({type(e).__name__})"
    if testo is not None:
        try:
            d = json.loads(testo)
        except ValueError:
            d, problema = None, f"il file di configurazione {f} non contiene JSON valido"
        if d is not None and not isinstance(d, dict):
            problema = f"il file di configurazione {f} non contiene un oggetto JSON"
        elif isinstance(d, dict):
            grezzi = d.get("preferenze", {})
            if not isinstance(grezzi, dict):
                problema = f"nel file di configurazione {f} la sezione 'preferenze' non e' un oggetto"
                grezzi = {}
            for k, v in grezzi.items():
                try:
                    _valida_preferenze({k: v})
                    valori[k] = v
                except DatiNonValidi as e:
                    if k == "mcp_sola_lettura":         # il valore che governa la sicurezza deve essere leggibile
                        problema = f"nel file di configurazione {f} la preferenza mcp_sola_lettura non e' valida ({e.messaggio})"
    if sola_lettura_da_ambiente():
        valori["mcp_sola_lettura"] = True
    return valori, problema


def preferenze(cartella_dati: Path | str | None = None) -> dict:
    """Preferenze correnti con i predefiniti (valori non validi nel file sono ignorati). Si leggono ad ogni chiamata, cosi' una
    modifica dal pannello vale subito anche per il server MCP. La variabile d'ambiente SUCCESSIONI_MCP_SOLA_LETTURA=1 prevale.
    Per sapere se il file e' illeggibile o non valido usare ``leggi_preferenze`` (il server MCP va allora in sola lettura)."""
    return leggi_preferenze(cartella_dati)[0]


# Voci del file di configurazione copiate nel backup (elenco chiuso): percorsi degli strumenti, aspetto, profilo dello studio e
# preferenze. Escluse le chiavi non note (potrebbero contenere qualunque cosa, anche segreti scritti a mano) e
# SUCCESSIONI_DATA (dopo un ripristino punterebbe alla vecchia cartella dei dati).
VOCI_BACKUP = frozenset(k for k in CHIAVI if k != "SUCCESSIONI_DATA") | {"interfaccia", "profilo", "preferenze"}


def contenuto_per_backup(contenuto) -> dict | None:
    """Copia filtrata (solo ``VOCI_BACKUP``) di un contenuto di configurazione; None se non e' un oggetto."""
    if not isinstance(contenuto, dict):
        return None
    return {k: v for k, v in contenuto.items() if k in VOCI_BACKUP}


# Profilo dello studio: dati del fornitore (chi presenta il file) applicati come predefiniti alle nuove pratiche.
CHIAVI_PROFILO = ("cf", "tipo", "impegno_codice")


def _valida_profilo(p) -> dict:
    from .telematico import formati as F
    if not isinstance(p, dict):
        raise DatiNonValidi("profilo dello studio: atteso un oggetto")
    for k in p:
        if k not in CHIAVI_PROFILO:
            raise DatiNonValidi(f"profilo dello studio: campo sconosciuto {k!r}", ammessi=list(CHIAVI_PROFILO))
    out: dict = {}
    if p.get("cf") not in (None, ""):
        try:
            out["cf"] = F.cf(p["cf"])
        except F.ValoreXml as e:
            raise DatiNonValidi(f"profilo dello studio: codice fiscale non valido ({e})") from None
    if p.get("tipo") not in (None, ""):
        if str(p["tipo"]) not in ("1", "10"):
            raise DatiNonValidi("profilo dello studio: tipo fornitore 1 (dichiarante) o 10 (intermediario)")
        out["tipo"] = str(p["tipo"])
    if p.get("impegno_codice") not in (None, ""):
        if str(p["impegno_codice"]) not in ("1", "2"):
            raise DatiNonValidi("profilo dello studio: impegno a trasmettere 1 o 2")
        out["impegno_codice"] = str(p["impegno_codice"])
    return out


def nome_studio(cartella_dati: Path | str | None = None) -> str:
    """Nome dello studio dalle preferenze dell'interfaccia, letto dal file di configurazione accanto ai dati indicati (lo
    stesso usato da preferenze e profilo): con un archivio di prova si stampa il nome di quell'archivio, non di un altro."""
    env = os.environ.get("SUCCESSIONI_CONFIG")
    f = Path(env) if env else (Path(cartella_dati) / "configurazione.json" if cartella_dati else file_configurazione())
    try:
        conf = json.loads(f.read_text(encoding="utf-8-sig"))
        return preferenze_interfaccia(conf if isinstance(conf, dict) else {}).get("nome_studio", "") or ""
    except (OSError, ValueError, DatiNonValidi):
        return ""


def profilo_studio(cartella_dati: Path | str | None = None) -> dict:
    """Profilo salvato (vuoto se assente o non valido). Si legge dal file di configurazione accanto ai dati indicati."""
    env = os.environ.get("SUCCESSIONI_CONFIG")
    f = Path(env) if env else (Path(cartella_dati) / "configurazione.json" if cartella_dati else file_configurazione())
    try:
        d = json.loads(f.read_text(encoding="utf-8-sig"))
        return _valida_profilo(d.get("profilo", {})) if isinstance(d, dict) else {}
    except (OSError, ValueError, DatiNonValidi):
        return {}


def _componente_controllo() -> dict:
    from . import strumenti
    inst = strumenti.versione_controllo_installata(os.environ.get("SUCCESSIONI_CONTROLLI_SUC13"))
    return {"installata": inst, "provata": {"versione": strumenti.VERSIONE_CONTROLLO_PROVATA[0], "data": strumenti.VERSIONE_CONTROLLO_PROVATA[1]},
            **strumenti.confronta_versione(inst)}


def stato() -> dict:
    """Impostazioni correnti, con origine del valore e stato di rilevamento di ciascuno strumento."""
    nel_file = _leggi_file()
    voci = []
    for chiave, etichetta, tipo, nota in VOCI:
        valore = os.environ.get(chiave) or None
        rilevato = False
        if valore is None and chiave in ("SUCCESSIONI_DESKTOP_TELEMATICO", "SUCCESSIONI_ENTRATEL_MULTIFILE"):
            from . import strumenti
            valore = strumenti.rilevamento(chiave)
            rilevato = valore is not None
        if rilevato:
            origine = "rilevato nelle posizioni consuete"
        elif valore is None:
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
    pref, problema = leggi_preferenze()
    # problema_configurazione: None se il file manca o e' valido; altrimenti il motivo (l'interfaccia usa i predefiniti e lo
    # mostra; il server MCP in questo caso si considera in sola lettura)
    return {"file": str(file_configurazione()), "voci": voci, "interfaccia": preferenze_interfaccia(nel_file),
            "profilo": profilo_studio(), "preferenze": pref, "problema_configurazione": problema,
            "componente_controllo": _componente_controllo()}


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
    if chiave in ("SUCCESSIONI_DESKTOP_TELEMATICO", "SUCCESSIONI_ENTRATEL_MULTIFILE"):
        from . import strumenti
        ok, descr = strumenti.controllo_cartella(chiave, v)
        if not ok:
            raise DatiNonValidi(f"{voce[1]}: {descr}", chiave=chiave)
    nome = NOMI_AMMESSI.get(chiave)
    if nome is not None and not nome.fullmatch(Path(v).name):
        raise DatiNonValidi(f"{voce[1]}: il file deve avere il nome dello strumento (es. {_ESEMPIO[chiave]}), non {Path(v).name!r}",
                            chiave=chiave)
    return v


_SALVATAGGIO = threading.Lock()


def _sostituisci(temp: Path, destinazione: Path) -> None:
    """os.replace con pochi tentativi: su Windows fallisce se nello stesso istante un altro thread o processo sta leggendo
    il file (le richieste dell'interfaccia ora girano in parallelo)."""
    for tentativo in range(20):
        try:
            os.replace(temp, destinazione)
            return
        except PermissionError:
            if tentativo == 19:
                raise
            time.sleep(0.05)


def salva(modifiche: dict, interfaccia: dict | None = None, profilo: dict | None = None,
          preferenze_nuove: dict | None = None) -> dict:
    """Applica e salva le modifiche (valore vuoto = rimuove l'impostazione). Tutto o niente: se un valore e' errato non si
    scrive nulla. Restituisce lo stato aggiornato piu' gli eventuali `avvisi`. Un salvataggio alla volta: leggere, unire e
    riscrivere il file in parallelo perderebbe le modifiche dell'altro (per esempio due larghezze salvate di seguito)."""
    with _SALVATAGGIO:
        return _salva(modifiche, interfaccia, profilo, preferenze_nuove)


def _salva(modifiche: dict, interfaccia: dict | None = None, profilo: dict | None = None,
           preferenze_nuove: dict | None = None) -> dict:
    if not isinstance(modifiche, dict) or (not modifiche and not interfaccia and profilo is None and preferenze_nuove is None):
        raise DatiNonValidi("nessuna modifica indicata")
    nuove = {k: _valida(k, v) for k, v in modifiche.items()}
    aspetto = _valida_interfaccia(interfaccia) if interfaccia is not None else None
    nuovo_profilo = _valida_profilo(profilo) if profilo is not None else None
    nuove_pref = _valida_preferenze(preferenze_nuove) if preferenze_nuove is not None else None
    contenuto = _leggi_file_stretto()
    if nuove_pref is not None:
        contenuto["preferenze"] = {k: v for k, v in {**(contenuto.get("preferenze") or {}), **nuove_pref}.items()
                                   if k in PREFERENZE_DEFAULT}
    if nuovo_profilo is not None:
        if nuovo_profilo:
            contenuto["profilo"] = nuovo_profilo
        else:
            contenuto.pop("profilo", None)
    if aspetto is not None:
        contenuto["interfaccia"] = {**preferenze_interfaccia(contenuto), **aspetto}
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
        _sostituisci(temp, destinazione)
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
