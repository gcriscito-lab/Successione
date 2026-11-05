#!/usr/bin/env python3
"""Controllo con mutazioni: altera il codice di un modulo un punto alla volta e verifica che i test falliscano.

Uso:
  python scripts/verifica_mutazioni.py src/successioni/documenti/base64.py tests/test_documenti_base64_extra.py [--funzioni f1,f2]
         [--max N] [--timeout S]

Per ogni mutazione (confronti ==/!=/</<=/>/>=, and/or, True/False, +/-, costanti intere +1, `not`, return di un valore -> None)
esegue pytest sul file di test indicato e riporta se e' stata UCCISA (test falliti) o e' SOPRAVVISSUTA (test verdi: il test non
prova quel comportamento, oppure la mutazione e' equivalente e va motivata). Si muta una copia di src: il repository non viene toccato.
Le mutazioni che rendono il modulo non importabile (errore di sintassi) sono scartate, non contate come uccise.
Uscita 0 solo se nessuna mutazione sopravvive. Non sostituisce la lettura dei sopravvissuti: sono l'elenco di lavoro.
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
OPERATORI = [(" == ", " != "), (" != ", " == "), (" <= ", " < "), (" >= ", " > "), (" < ", " <= "), (" > ", " >= "),
             (" and ", " or "), (" or ", " and "), (" + ", " - "), (" - ", " + "), ("True", "False"), ("False", "True")]


def intervalli_funzioni(sorgente: str, nomi: set[str] | None) -> list[tuple[int, int]]:
    alb = ast.parse(sorgente)
    out = []
    for n in ast.walk(alb):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and (nomi is None or n.name in nomi):
            out.append((n.lineno, n.end_lineno))
    return out


def candidati(righe: list[str], intervalli: list[tuple[int, int]]) -> list[tuple[int, str, str]]:
    """(numero riga 1-based, riga originale, riga mutata). Salta commenti, docstring evidenti e righe di import."""
    out = []
    for i, r in enumerate(righe, 1):
        if not any(a <= i <= b for a, b in intervalli):
            continue
        s = r.strip()
        if not s or s.startswith(("#", '"""', "'''", "import ", "from ")) or "noqa: mut" in r:
            continue
        codice = r.split("  #")[0] if "  #" in r else r
        for a, b in OPERATORI:
            if a in codice:
                out.append((i, r, r.replace(a, b, 1)))
        m = re.search(r"\breturn (?!None\b)(.+)", codice)
        if m:
            out.append((i, r, r[:m.start()] + "return None"))
        if re.search(r"\bnot ", codice):
            out.append((i, r, re.sub(r"\bnot ", "", codice, count=1) + r[len(codice):]))
        m = re.search(r"(?<![\w.\"'])(\d+)(?![\w.\"'])", codice)
        if m and not s.startswith(("def ", "class ")):
            out.append((i, r, r[:m.start()] + str(int(m.group(1)) + 1) + r[m.end():]))
    return out


def esegui_test(test: str, timeout: int, env: dict, src: Path) -> int | None:
    """pytest sul file di test, con il codice preso dalla COPIA `src` (l'ini del progetto fissa pythonpath=src: lo si sostituisce)."""
    try:
        return subprocess.run([sys.executable, "-m", "pytest", test, "-q", "-x", "-p", "no:cacheprovider", "-o", f"pythonpath={src}",
                               f"--basetemp={env['TMP']}/vm"], cwd=RADICE, env=env, capture_output=True, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("modulo")
    ap.add_argument("test")
    ap.add_argument("--funzioni", default="", help="solo queste funzioni (separate da virgola); predefinito: tutte")
    ap.add_argument("--max", type=int, default=400)
    ap.add_argument("--timeout", type=int, default=120)
    a = ap.parse_args(argv)
    modulo_orig = (RADICE / a.modulo) if not Path(a.modulo).is_absolute() else Path(a.modulo)
    originale = modulo_orig.read_text(encoding="utf-8")
    # Si muta una COPIA di src (in TMP): il repository non viene mai toccato, nemmeno se un'altra sessione lo sta modificando.
    copia = Path(os.environ.get("TMP", "C:/sx")) / "vm_copia"
    shutil.rmtree(copia, ignore_errors=True)
    shutil.copytree(RADICE / "src", copia / "src", ignore=shutil.ignore_patterns("__pycache__"))
    modulo = copia / "src" / modulo_orig.relative_to(RADICE / "src")
    righe = originale.split("\n")
    nomi = {n for n in a.funzioni.split(",") if n} or None
    muts = candidati(righe, intervalli_funzioni(originale, nomi))[: a.max]
    env = {**os.environ, "TMP": os.environ.get("TMP", "C:/sx"), "TEMP": os.environ.get("TEMP", "C:/sx")}
    env.pop("PYTHONPATH", None)
    src = copia / "src"
    if esegui_test(a.test, a.timeout, env, src) != 0:
        print("ATTENZIONE: i test non sono verdi sul codice originale: nessuna mutazione eseguita.")
        return 2
    vivi, uccise, scartate = [], 0, 0
    try:
        for n, orig, mut in muts:
            if mut == orig:
                continue
            nuove = righe[:]
            nuove[n - 1] = mut
            testo = "\n".join(nuove)
            try:
                ast.parse(testo)
            except SyntaxError:
                scartate += 1
                continue
            modulo.write_text(testo, encoding="utf-8")
            rc = esegui_test(a.test, a.timeout, env, src)
            if rc == 0:
                vivi.append((n, orig.strip(), mut.strip()))
                print(f"SOPRAVVISSUTA riga {n}: {orig.strip()}  ->  {mut.strip()}")
            else:
                uccise += 1
    finally:
        shutil.rmtree(copia, ignore_errors=True)
    print(f"mutazioni: {uccise} uccise, {len(vivi)} sopravvissute, {scartate} scartate (sintassi)")
    return 0 if not vivi else 1


if __name__ == "__main__":
    raise SystemExit(main())
