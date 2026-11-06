"""Strumenti esterni dell'utente: componente di controllo SUC13, Desktop Telematico, Entratel-Multifile; diagnosi dell'ambiente.

Tutto in sola lettura: si guardano file e cartelle, non si esegue nulla dell'Agenzia e non si leggono credenziali, certificati o i
file ``.cfg`` di Multifile (che possono contenere dati di accesso).

- ``versione_controllo_installata``: versione e data del componente leggendo le costanti di ``MSUC13.class`` nel JAR (non serve avviare Java).
- ``confronta_versione``: confronto con la versione provata da questo programma (``VERSIONE_CONTROLLO_PROVATA``).
- ``desktop_telematico`` / ``multifile``: percorso configurato (impostazioni) oppure rilevato nelle posizioni consuete.
- ``istruzioni_invio``: passi di invio con i percorsi reali.
- ``diagnosi``: elenco di voci (ok / avviso / errore) con il rimedio, usata dall'interfaccia e dal MCP.
"""
from __future__ import annotations

import os
import platform
import re
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# Versione del controllo con cui questo programma e' stato provato (fonti/Programma e controlli/ControlliSUC13.jnlp, 2026-11-01).
VERSIONE_CONTROLLO_PROVATA = ("2.3.1", "11/03/2026")
_CLASSE_VERSIONE = "it/finanze/entrate/sco/main/MSUC13.class"
ENV_DESKTOP_TELEMATICO = "SUCCESSIONI_DESKTOP_TELEMATICO"
ENV_MULTIFILE = "SUCCESSIONI_ENTRATEL_MULTIFILE"


# ------------------------------------------------------------------------------------------- versione del controllo
def _utf8_costanti(dati: bytes):
    """Stringhe UTF-8 del constant pool (tag 1, lunghezza 2 byte): basta una scansione, la lunghezza si verifica."""
    for m in re.finditer(rb"\x01(..)", dati, re.S):
        n = int.from_bytes(m.group(1), "big")
        if 3 <= n <= 40:
            t = dati[m.end():m.end() + n]
            if len(t) == n:
                yield t.decode("latin-1")


def versione_controllo_installata(cartella_jar: Path | str | None) -> dict | None:
    """``{"versione": "2.3.1", "data": "11/03/2026"}`` dalle costanti di MSUC13.class, oppure ``None`` se non rilevabile."""
    if not cartella_jar:
        return None
    jar = Path(cartella_jar) / "controlliXMLREG2013.jar"
    try:
        with zipfile.ZipFile(jar) as z:
            dati = z.read(_CLASSE_VERSIONE)
    except (OSError, KeyError, zipfile.BadZipFile):
        return None
    versioni = [t for t in _utf8_costanti(dati) if re.fullmatch(r"\d+\.\d+\.\d+", t)]
    date = [t for t in _utf8_costanti(dati) if re.fullmatch(r"\d\d/\d\d/\d{4}", t)]
    if not versioni:
        return None
    return {"versione": versioni[0], "data": date[0] if date else None}


def _chiave_versione(v: str) -> tuple:
    return tuple(int(x) for x in v.split("."))


def _data(d: str | None):
    try:
        return datetime.strptime(d, "%d/%m/%Y").date() if d else None
    except ValueError:
        return None


def confronta_versione(installata: dict | None, nota: tuple[str, str] = VERSIONE_CONTROLLO_PROVATA) -> dict:
    """Stato: ``aggiornata`` | ``piu_vecchia`` | ``piu_recente`` | ``sconosciuta``, con un messaggio in italiano."""
    if not installata:
        return {"stato": "sconosciuta", "messaggio": "Versione del componente di controllo non rilevabile."}
    v, d = installata["versione"], installata.get("data")
    nome = f"{v}" + (f" del {d}" if d else "")
    atteso = f"{nota[0]} del {nota[1]}"
    try:
        cmp = (_chiave_versione(v), _data(d) or datetime.min.date()) , (_chiave_versione(nota[0]), _data(nota[1]) or datetime.min.date())
    except ValueError:
        return {"stato": "sconosciuta", "messaggio": f"Versione del componente non interpretabile: {nome}."}
    if cmp[0] == cmp[1]:
        return {"stato": "aggiornata", "messaggio": f"Componente di controllo {nome}: e' la versione con cui il programma e' stato provato."}
    if cmp[0] < cmp[1]:
        return {"stato": "piu_vecchia", "messaggio": f"Componente di controllo {nome}, piu' vecchio di quello provato ({atteso}): "
                "aggiornalo dal sito dell'Agenzia (ControlliSUC13.jnlp) prima di usare l'esito come riferimento."}
    return {"stato": "piu_recente", "messaggio": f"Componente di controllo {nome}, piu' recente di quello provato ({atteso}): puo' avere regole "
            "nuove; ripeti i controlli e confronta gli esiti."}


# ------------------------------------------------------------------------------ Desktop Telematico ed Entratel-Multifile
def _candidati(nomi: tuple[str, ...]) -> list[Path]:
    radici: list[Path] = []
    for v in ("SystemDrive", "ProgramFiles", "ProgramFiles(x86)", "USERPROFILE", "LOCALAPPDATA"):
        e = os.environ.get(v)
        if e:
            radici.append(Path(e if v != "SystemDrive" else e + "\\"))
    out: list[Path] = []
    for r in radici:
        for n in nomi:
            out += [r / n, r / n / n]
    return out


def _e_desktop_telematico(p: Path) -> bool:
    return p.is_dir() and any((p / n).is_file() for n in ("DesktopTelematico.exe", "desktoptelematico.exe"))


def _e_multifile(p: Path) -> bool:
    return p.is_dir() and (p / "prog").is_dir()


def desktop_telematico() -> dict:
    """``{"cartella": ..., "eseguibile": ..., "origine": "impostazione"|"rilevato"|None}``."""
    conf = os.environ.get(ENV_DESKTOP_TELEMATICO)
    if conf and _e_desktop_telematico(Path(conf)):
        return {"cartella": conf, "eseguibile": str(Path(conf) / "DesktopTelematico.exe"), "origine": "impostazione"}
    for c in _candidati(("DesktopTelematico",)):
        if _e_desktop_telematico(c):
            return {"cartella": str(c), "eseguibile": str(c / "DesktopTelematico.exe"), "origine": "rilevato"}
    return {"cartella": None, "eseguibile": None, "origine": None}


def multifile() -> dict:
    conf = os.environ.get(ENV_MULTIFILE)
    if conf and _e_multifile(Path(conf)):
        return {"cartella": conf, "origine": "impostazione"}
    for c in _candidati(("Entratel-Multifile", "EntratelMultifile", "Multifile")):
        if _e_multifile(c):
            return {"cartella": str(c), "origine": "rilevato"}
    return {"cartella": None, "origine": None}


def rilevamento(chiave: str) -> str | None:
    """Percorso rilevato automaticamente per le impostazioni di questo modulo (``None`` se non trovato)."""
    if chiave == ENV_DESKTOP_TELEMATICO:
        return desktop_telematico()["cartella"]
    if chiave == ENV_MULTIFILE:
        return multifile()["cartella"]
    return None


def controllo_cartella(chiave: str, valore: str) -> tuple[bool, str]:
    """(ok, dettaglio) per le due impostazioni di questo modulo."""
    p = Path(valore)
    if chiave == ENV_DESKTOP_TELEMATICO:
        return (True, f"trovato DesktopTelematico.exe in {valore}") if _e_desktop_telematico(p) else (False, "non contiene DesktopTelematico.exe")
    if chiave == ENV_MULTIFILE:
        return (True, f"trovata la cartella prog in {valore}") if _e_multifile(p) else (False, "non contiene la sottocartella prog di Entratel-Multifile")
    return True, ""


def istruzioni_invio(nome_file: str | None = None, impronta: str | None = None, percorso_xml: str | None = None,
                     percorso_dcm: str | None = None) -> str:
    """Passi dell'invio reale con i percorsi degli strumenti dell'utente. Il programma NON trasmette."""
    dt, mf = desktop_telematico(), multifile()
    righe = ["Invio da eseguire con gli strumenti ufficiali (questo programma NON trasmette e non usa le tue credenziali):"]
    righe.append("1. Esporta il file indicato senza modificarlo" + (f": {nome_file}" if nome_file else "") + (f" (SHA-256 {impronta})" if impronta else "") + ".")
    if percorso_xml:
        righe.append(f"   XML: {percorso_xml}")
    if percorso_dcm:
        righe.append(f"   File controllato (.dcm): {percorso_dcm}")
    if dt["cartella"]:
        righe.append(f"2. Desktop Telematico ({'impostato' if dt['origine'] == 'impostazione' else 'rilevato'}): avvia {dt['eseguibile']}; controllo SUC13 -> "
                     "file controllato (.dcm) -> Autentica (.ccf) -> Invia. Se il controllo del Desktop Telematico da' errori, fermati.")
    else:
        righe.append("2. Desktop Telematico non rilevato: indica la cartella in Impostazioni -> Strumenti e percorsi. Procedura: controllo SUC13 -> "
                     "file controllato (.dcm) -> Autentica (.ccf) -> Invia.")
    if mf["cartella"]:
        base = Path(mf["cartella"])
        righe.append(f"3. In alternativa Entratel-Multifile ({'impostato' if mf['origine'] == 'impostazione' else 'rilevato'}): copia il .dcm in "
                     f"{base / 'file_da_autenticare'}; esegui {base / 'prog' / 'runAutentica.bat'}; poi il .ccf va in {base / 'file_da_inviare'} "
                     f"ed esegui {base / 'prog' / 'runInvio.bat'}. Le credenziali restano nei file di configurazione dello strumento: il programma non li legge. "
                     "(Procedura dalla ricognizione del manuale v1.1.1: verificala con la versione installata.)")
    righe.append("4. Registra l'esito nel programma con la riconciliazione: protocollo assegnato, oppure il file .esi di Multifile, oppure la dichiarazione "
                 "verificata che l'invio non e' avvenuto.")
    righe.append("Finche' l'esito non e' riconciliato non e' possibile avviare un altro tentativo per questa copia.")
    return "\n".join(righe)


# ------------------------------------------------------------------------------------------------------------ diagnosi
def _voce(nome: str, stato: str, dettaglio: str, rimedio: str | None = None) -> dict:
    return {"nome": nome, "stato": stato, "dettaglio": dettaglio, "rimedio": rimedio}


def _claude_mcp(dati: Path) -> list[dict]:
    import json
    out = []
    p = Path.home() / ".claude.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8-sig"))
        voce = (d.get("mcpServers") or {}).get("successioni")
        if voce:
            usata = ((voce.get("env") or {}).get("SUCCESSIONI_DATA") or "")
            ok = usata and Path(usata).resolve() == dati.resolve()
            out.append(_voce("Claude Code (MCP)", "ok" if ok else "avviso",
                             f"server 'successioni' registrato; cartella dati: {usata or 'predefinita'}",
                             None if ok else "La cartella dati del server MCP e' diversa da quella di questa interfaccia: Claude vedrebbe altre pratiche. "
                                             "Riconfigura con docs/CONFIGURAZIONE_MCP.md."))
        else:
            out.append(_voce("Claude Code (MCP)", "info", "server 'successioni' non registrato in Claude Code", "docs/CONFIGURAZIONE_MCP.md"))
    except (OSError, ValueError):
        out.append(_voce("Claude Code (MCP)", "info", "configurazione di Claude Code non trovata", "docs/CONFIGURAZIONE_MCP.md"))
    cd = Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json" if os.environ.get("APPDATA") else None
    if cd is not None:
        try:
            d = json.loads(cd.read_text(encoding="utf-8-sig"))
            out.append(_voce("Claude Desktop (MCP)", "ok" if (d.get("mcpServers") or {}).get("successioni") else "info",
                             "server 'successioni' presente" if (d.get("mcpServers") or {}).get("successioni") else "server 'successioni' non presente"))
        except (OSError, ValueError):
            out.append(_voce("Claude Desktop (MCP)", "info", "configurazione di Claude Desktop non trovata"))
    return out


def diagnosi(archivio=None) -> dict:
    """Diagnosi dell'ambiente. Restituisce ``{"voci": [...], "esito": "ok"|"avvisi"|"non_utilizzabile", "riepilogo": str}``."""
    from . import impostazioni
    from .archivio import cartella_dati
    voci: list[dict] = []
    voci.append(_voce("Sistema", "ok", f"{platform.platform()} · Python {sys.version.split()[0]}"))
    dati = Path(archivio.base) if archivio is not None else cartella_dati()
    try:
        dati.mkdir(parents=True, exist_ok=True)
        prova = dati / ".diagnosi.tmp"
        prova.write_text("ok", encoding="utf-8")
        prova.unlink()
        libero = shutil.disk_usage(dati).free // (1024 * 1024)
        voci.append(_voce("Cartella dei dati", "ok" if libero > 500 else "avviso",
                          f"{dati} · scrivibile · spazio libero {libero} MB", None if libero > 500 else "Poco spazio libero: libera spazio prima di allegare documenti."))
    except OSError as e:
        voci.append(_voce("Cartella dei dati", "errore", f"{dati} non scrivibile ({e})", "Scegli una cartella scrivibile con SUCCESSIONI_DATA."))
    # strumenti dalle impostazioni (stesso rilevamento del pannello)
    s = impostazioni.stato()
    for v in s["voci"]:
        if v["chiave"] in ("SUCCESSIONI_DATA", ENV_DESKTOP_TELEMATICO, ENV_MULTIFILE):
            continue
        facoltativo = v["chiave"] in ("SUCCESSIONI_QPDF", "SUCCESSIONI_ICC", "SUCCESSIONI_FONTI", "SUCCESSIONI_BACKUP", "SUCCESSIONI_CONTROLLI_TIMEOUT")
        stato = "ok" if v["a_posto"] else ("info" if facoltativo else "errore")
        voci.append(_voce(v["etichetta"], stato, v["dettaglio"], None if v["a_posto"] else v["nota"]))
    # versione del componente di controllo
    cart = os.environ.get("SUCCESSIONI_CONTROLLI_SUC13")
    inst = versione_controllo_installata(cart)
    conf = confronta_versione(inst)
    voci.append(_voce("Versione del controllo SUC13", {"aggiornata": "ok", "piu_vecchia": "avviso", "piu_recente": "avviso", "sconosciuta": "info"}[conf["stato"]],
                      conf["messaggio"], "Scarica la versione corrente da https://jws.agenziaentrate.it (ControlliSUC13.jnlp)." if conf["stato"] == "piu_vecchia" else None))
    dt, mf = desktop_telematico(), multifile()
    voci.append(_voce("Desktop Telematico", "ok" if dt["cartella"] else "info", f"{dt['eseguibile']} ({dt['origine']})" if dt["cartella"] else "non rilevato",
                      None if dt["cartella"] else "Serve per Autentica e Invio: indica la cartella in Impostazioni -> Strumenti e percorsi."))
    voci.append(_voce("Entratel-Multifile", "ok" if mf["cartella"] else "info", f"{mf['cartella']} ({mf['origine']})" if mf["cartella"] else "non rilevato",
                      None if mf["cartella"] else "Facoltativo: alternativa a Desktop Telematico per autenticare e inviare."))
    # backup
    if archivio is not None:
        from . import backup_archivio as BK
        elenco = BK.elenco(archivio)
        if not elenco:
            voci.append(_voce("Backup", "avviso", f"nessun backup in {BK.cartella_backup(archivio)}", "Crea un backup da Impostazioni -> Backup."))
        else:
            eta = (datetime.now() - datetime.fromisoformat(elenco[0]["creato"])).days
            voci.append(_voce("Backup", "ok" if eta <= 7 else "avviso", f"ultimo backup {elenco[0]['creato'].replace('T', ' ')} ({eta} giorni fa) in {BK.cartella_backup(archivio)}",
                              None if eta <= 7 else "L'ultimo backup e' vecchio: creane uno."))
    voci += _claude_mcp(dati)
    errori = [v for v in voci if v["stato"] == "errore"]
    avvisi = [v for v in voci if v["stato"] == "avviso"]
    esito = "non_utilizzabile" if errori else ("avvisi" if avvisi else "ok")
    riepilogo = {"ok": "Tutto a posto.", "avvisi": f"{len(avvisi)} avvisi da guardare.", "non_utilizzabile": f"{len(errori)} problemi da risolvere."}[esito]
    return {"data": datetime.now().isoformat(timespec="seconds"), "voci": voci, "esito": esito, "riepilogo": riepilogo}
