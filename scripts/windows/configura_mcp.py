"""Configurazione del server MCP di Successioni per Claude Desktop e Claude Code (Windows).

    python\\python.exe -s app\\configura_mcp.py                       stampa JSON e comando, non modifica nulla
    python\\python.exe -s app\\configura_mcp.py --scrivi-claude-desktop
        aggiunge/aggiorna la voce "successioni" in %APPDATA%\\Claude\\claude_desktop_config.json
        (copia di sicurezza del file precedente; le altre voci restano invariate)

Formato e percorsi dalla documentazione ufficiale consultata il 2026-11-01:
- Claude Desktop: https://modelcontextprotocol.io/docs/develop/connect-local-servers (chiave "mcpServers",
  "command", "args"; file %APPDATA%\\Claude\\claude_desktop_config.json; riavvio completo dell'app).
- Claude Code: https://code.claude.com/docs/en/mcp (`claude mcp add [opzioni] <nome> -- <comando> [argomenti]`,
  `--scope user`, `--env CHIAVE=valore`; "env" nelle voci JSON).
Il server e' sempre il processo Windows del pacchetto: usa lo stesso archivio dell'interfaccia.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import avvia_successioni as A  # noqa: E402

NOME = "successioni"


def eseguibile_python() -> Path:
    """Nel pacchetto: <radice>\\python\\python.exe. Altrove (prove): l'interprete corrente."""
    p = A.RADICE / "python" / "python.exe"
    return p if p.exists() else Path(sys.executable)


def voce_server(cartella_dati: str | None = None) -> dict:
    v = {"command": str(eseguibile_python()), "args": ["-s", str(A.QUI / "avvia_successioni.py"), "mcp"]}
    if cartella_dati:
        v["env"] = {"SUCCESSIONI_DATA": cartella_dati}
    return v


def blocco_claude_desktop(voce: dict, nome: str = NOME) -> dict:
    return {"mcpServers": {nome: voce}}


def _q(s: str) -> str:
    """Argomento tra virgolette doppie per cmd.exe e PowerShell (i percorsi Windows non contengono virgolette)."""
    if '"' in s:
        raise ValueError("percorso con virgolette non supportato")
    return f'"{s}"'


def comando_claude_code(voce: dict, nome: str = NOME, scope: str = "user") -> str:
    parti = ["claude", "mcp", "add"]
    for k, v in (voce.get("env") or {}).items():
        parti += ["--env", f"{k}={_q(v)}"]
    parti += ["--transport", "stdio", "--scope", scope, nome, "--", _q(voce["command"])]
    parti += [_q(a) if (" " in a or "\\" in a or "/" in a) else a for a in voce["args"]]
    return " ".join(parti)


def file_claude_desktop() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise SystemExit("APPDATA non impostata: indicare il file con --file")
    return Path(appdata) / "Claude" / "claude_desktop_config.json"


def unisci_claude_desktop(percorso: Path, voce: dict, nome: str = NOME) -> dict:
    """Aggiunge o aggiorna una sola voce. Non sovrascrive un file non leggibile. Idempotente."""
    attuale: dict = {}
    if percorso.exists():
        testo = percorso.read_text(encoding="utf-8-sig")
        if testo.strip():
            try:
                attuale = json.loads(testo)
            except ValueError as e:
                raise SystemExit(f"{percorso} non e' JSON valido ({e}): correggerlo prima, il file non e' stato toccato")
        if not isinstance(attuale, dict):
            raise SystemExit(f"{percorso}: contenuto inatteso (non e' un oggetto JSON); file non modificato")
    server = attuale.get("mcpServers")
    if server is None:
        server = attuale["mcpServers"] = {}
    if not isinstance(server, dict):
        raise SystemExit(f"{percorso}: 'mcpServers' non e' un oggetto; file non modificato")
    if server.get(nome) == voce:
        return {"file": str(percorso), "modificato": False, "copia": None}
    copia = None
    if percorso.exists():
        copia = percorso.with_name(f"{percorso.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(percorso, copia)
    server[nome] = voce
    percorso.parent.mkdir(parents=True, exist_ok=True)
    tmp = percorso.with_name(percorso.name + ".tmp")
    tmp.write_text(json.dumps(attuale, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(percorso)
    return {"file": str(percorso), "modificato": True, "copia": str(copia) if copia else None}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="configura_mcp")
    ap.add_argument("--scrivi-claude-desktop", action="store_true")
    ap.add_argument("--file", help="file di configurazione di Claude Desktop (predefinito: %%APPDATA%%\\Claude\\...)")
    ap.add_argument("--con-cartella-dati", action="store_true",
                    help="scrive SUCCESSIONI_DATA nella voce (deve coincidere con quella dell'interfaccia)")
    ap.add_argument("--nome", default=NOME)
    a = ap.parse_args(argv)
    A.prepara_ambiente()
    dati = str(A.cartella_dati()) if a.con_cartella_dati else None
    voce = voce_server(dati)
    print("== Claude Desktop: voce da inserire in claude_desktop_config.json (Impostazioni > Sviluppatore > Modifica config)")
    print(json.dumps(blocco_claude_desktop(voce, a.nome), indent=2, ensure_ascii=False))
    print()
    print("== Claude Code (PowerShell o Prompt dei comandi), per tutti i progetti dell'utente:")
    print(comando_claude_code(voce, a.nome))
    print()
    print(f"Cartella dati usata dall'interfaccia: {A.cartella_dati()}")
    if a.scrivi_claude_desktop:
        r = unisci_claude_desktop(Path(a.file) if a.file else file_claude_desktop(), voce, a.nome)
        print(json.dumps(r, ensure_ascii=False))
        if r["modificato"]:
            print("Chiudere completamente Claude Desktop (anche dall'area di notifica) e riaprirlo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
