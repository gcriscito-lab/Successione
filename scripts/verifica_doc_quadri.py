#!/usr/bin/env python3
"""Verifica meccanica di un documento sui quadri scritto da un agente: ogni quadro e' citato, nessun identificativo inventato.

Uso: python scripts/verifica_doc_quadri.py docs/GUIDA_QUADRI.md
Controlla: (1) ogni id di ``quadri.QUADRI`` compare nel testo; (2) ogni `identificativo_con_trattino_basso` in backtick compare
nei sorgenti (src/), nella matrice di copertura o nei test (nessun campo o funzione inventati). Esce con codice 1 se fallisce."""
from __future__ import annotations

import re
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RADICE / "src"))
from successioni.quadri import QUADRI  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    testo = Path(sys.argv[1]).read_text(encoding="utf-8")
    problemi = []
    for q in (x for x in QUADRI if x['id'].startswith('E')):
        if not re.search(rf"\b{re.escape(q['id'])}\b", testo):
            problemi.append(f"quadro {q['id']} non citato")
    corpus = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for pat in ("src/**/*.py", "tests/*.py", "docs/MATRICE_COPERTURA.md")
                       for p in RADICE.glob(pat))
    for tok in sorted(set(re.findall(r"`([a-z][a-z0-9]*(?:_[a-z0-9]+)+)`", testo))):
        if tok not in corpus:
            problemi.append(f"identificativo `{tok}` non trovato nei sorgenti, nei test o nella matrice")
    for p in problemi:
        print("PROBLEMA:", p)
    print("verifica documento:", "FALLITA" if problemi else "ok")
    return 1 if problemi else 0


if __name__ == "__main__":
    sys.exit(main())
