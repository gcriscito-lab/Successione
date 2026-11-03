#!/usr/bin/env python3
"""Esegue piu' compiti per agenti gratuiti in parallelo (ognuno con `lancia.py`, in una propria copia isolata del repository).

Uso (servono FREELLMAPI_BASE_URL, FREELLMAPI_KEY e FREELLMAPI_MODEL nell'ambiente, come per `lancia.py`):
  python scripts/agenti_gratuiti/lancia_lotto.py C25 C26 C27 --parallelo 4 [--max-iter 3] [--out build/agenti]

Il parallelismo e' limitato perche' i servizi gratuiti rispondono 429 sotto carico (il lanciatore riprova da solo). La chiave
non viene mai stampata. Ogni compito e' indipendente: l'esito del lotto e' una tabella con il codice di uscita e la causa
prevalente scritta da `lancia.py` in CONSEGNA.md. Il coordinatore rivede ogni consegna prima di integrarla.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

QUI = Path(__file__).resolve().parent
RADICE = QUI.parents[1]
LANCIA = QUI / "lancia.py"
PAUSA_AVVIO_S = 3.0        # distanzia le partenze: ogni compito crea una copia git e fa la prima richiesta


def lancia_compito(cid: str, out: Path, max_iter: int) -> int:
    """Esegue un compito e restituisce il codice di uscita di `lancia.py` (sottoprocesso, senza shell)."""
    out.mkdir(parents=True, exist_ok=True)
    with open(out / f"{cid}.log", "w", encoding="utf-8") as log:
        return subprocess.run([sys.executable, str(LANCIA), cid, "--max-iter", str(max_iter), "--out", str(out)],
                              stdout=log, stderr=subprocess.STDOUT, cwd=RADICE).returncode


def causa(out: Path, cid: str) -> str:
    """Riga 'Causa prevalente...' dell'ultima CONSEGNA.md del compito, se c'e'."""
    for cartella in sorted(out.glob(f"{cid}*"), key=lambda p: p.stat().st_mtime, reverse=True):
        f = cartella / "CONSEGNA.md"
        if f.is_file():
            m = re.search(r"^.*Causa prevalente[^\n]*$", f.read_text(encoding="utf-8"), re.M)
            return m.group(0).strip(" -*") if m else "consegna senza causa indicata"
    return "nessuna consegna prodotta (vedi il log)"


def esegui_lotto(compiti: list[str], parallelo: int, out: Path, max_iter: int = 3, esegui=lancia_compito,
                 pausa_s: float = PAUSA_AVVIO_S) -> list[tuple[str, int, str]]:
    """Esegue i compiti con al piu' `parallelo` contemporanei. Restituisce [(compito, codice, causa)] nell'ordine dato."""
    if parallelo < 1:
        raise ValueError("parallelo deve essere almeno 1")
    if len(set(compiti)) != len(compiti):
        raise ValueError("compiti duplicati nell'elenco")

    def uno(i_cid):
        i, cid = i_cid
        time.sleep(pausa_s * (i % parallelo))
        try:
            codice = esegui(cid, out, max_iter)
        except Exception as e:      # un guasto imprevisto di un compito non deve fermare gli altri
            return cid, 99, f"errore del lanciatore: {type(e).__name__}: {str(e)[:150]}"
        return cid, codice, causa(out, cid)

    with ThreadPoolExecutor(max_workers=parallelo) as ex:
        return list(ex.map(uno, enumerate(compiti)))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("compiti", nargs="+", help="identificativi, es. C25 C26")
    ap.add_argument("--parallelo", type=int, default=4)
    ap.add_argument("--max-iter", type=int, default=3)
    ap.add_argument("--out", default=str(RADICE / "build" / "agenti"))
    a = ap.parse_args(argv)
    risultati = esegui_lotto(a.compiti, a.parallelo, Path(a.out), a.max_iter)
    for cid, codice, c in risultati:
        print(f"{cid:5} {'OK ' if codice == 0 else 'NO '} {c}")
    ok = sum(1 for _, codice, _ in risultati if codice == 0)
    print(f"{ok} su {len(risultati)} compiti con verifiche passate")
    return 0 if ok == len(risultati) else 1


if __name__ == "__main__":
    raise SystemExit(main())
