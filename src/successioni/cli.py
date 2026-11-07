"""Avvio da collegamento: `successioni` apre l'interfaccia locale; sottocomandi di servizio."""
from __future__ import annotations

import argparse
import sys

from .archivio import Archivio


def main(argv=None):
    ap = argparse.ArgumentParser(prog="successioni")
    sub = ap.add_subparsers(dest="cmd")
    g = sub.add_parser("gui", help="avvia l'interfaccia locale (predefinito)")
    g.add_argument("--porta", type=int, default=8765)
    g.add_argument("--no-browser", action="store_true")
    sub.add_parser("mcp", help="avvia il server MCP (stdio)")
    b = sub.add_parser("backup", help="copia coerente di database e allegati")
    b.add_argument("destinazione")
    r = sub.add_parser("ripristina", help="ripristina un backup in una cartella dati NUOVA (non sovrascrive mai dati esistenti)")
    r.add_argument("backup"); r.add_argument("--destinazione", required=True)
    c = sub.add_parser("converti-pdfa", help="converte un PDF in PDF/A-1b e riporta l'esito della validazione")
    c.add_argument("origine"); c.add_argument("destinazione")
    a = ap.parse_args(argv)
    cmd = a.cmd or "gui"
    if cmd == "gui":
        from .web import avvia
        avvia(getattr(a, "porta", 8765), not getattr(a, "no_browser", False))
    elif cmd == "mcp":
        from .mcp_server import main as m
        m()
    elif cmd == "backup":
        print(Archivio().backup(a.destinazione))
    elif cmd == "ripristina":
        from .errori import ErroreServizio
        try:
            Archivio(a.destinazione).ripristina(a.backup)
        except ErroreServizio as e:
            print("Ripristino non eseguito:", e.messaggio, file=sys.stderr)
            return 2
        print("Backup ripristinato in", a.destinazione)
    elif cmd == "converti-pdfa":
        from . import pdfa
        r = pdfa.converti_in_pdfa(a.origine, a.destinazione)
        print(r)
        if r["comando_ok"]:
            print(pdfa.analizza_pdf(a.destinazione))
            print(pdfa.valida_pdfa(a.destinazione).get("esito"), "(veraPDF richiesto per 'conforme')")
        return 0 if r["comando_ok"] else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
