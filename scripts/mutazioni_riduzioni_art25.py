"""Mutation testing delle riduzioni art. 25 (docs/regole/riduzioni_art25.md, sezione «Mutation testing»).

Per ogni mutazione: copia di ``src`` in una cartella temporanea, una sostituzione di testo in un file sorgente, esecuzione di
``tests/test_telematico_riduzioni_art25.py`` (e di ``test_telematico_calcolo.py``) con ``PYTHONPATH`` sulla copia mutata. Una
mutazione e' UCCISA se almeno un test fallisce; SOPRAVVISSUTA se tutti passano (esito che richiede un nuovo test).

Uso (dalla radice del repository, con l'interprete del progetto):
    python scripts/mutazioni_riduzioni_art25.py [--reale] [--tmp C:/sx/mut] [numero ...]

``--reale`` mantiene attive le variabili SUCCESSIONI_JAVA / SUCCESSIONI_CONTROLLI_SUC13 dell'ambiente (prove con il controllo
ufficiale locale, molto piu' lente); senza, le prove 'reale' sono saltate e si usano i confronti con il calcolo a mano.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
RA = "src/successioni/telematico/riduzioni_art25.py"
CA = "src/successioni/telematico/calcolo.py"
ES = "src/successioni/telematico/esporta.py"
QE = "src/successioni/telematico/quadri_efgh.py"

#: (descrizione, file, testo originale, testo mutato)
MUTAZIONI = [
    ("coefficiente L 0,5 -> 0,4", RA, '"L": Fraction(5, 10), "Q": Fraction(4, 10)', '"L": Fraction(4, 10), "Q": Fraction(4, 10)'),
    ("coefficiente art. 25 codice 1: 0,5 -> 0,4", RA, '"1": Fraction(5, 10), "2"', '"1": Fraction(4, 10), "2"'),
    ("coefficiente art. 25 codice 5: 0,1 -> 0,2", RA, '"5": Fraction(1, 10)}\n#: coefficienti L', '"5": Fraction(2, 10)}\n#: coefficienti L'),
    ("soglia R/F 103.291 -> 103.292", RA, "SOGLIA_RF = Fraction(103291)", "SOGLIA_RF = Fraction(103292)"),
    ("calcolo esatto: nessun tetto alla soglia R/F", CA,
     "base = qv if r[\"agev\"] in (\"L\", \"Q\") else min(qv, RA.SOGLIA_RF)", "base = qv"),
    ("calcolo esatto: Q trattato come R/F (tetto)", CA,
     "base = qv if r[\"agev\"] in (\"L\", \"Q\") else", "base = qv if r[\"agev\"] in (\"L\",) else"),
    ("calcolo esatto: art. 25 senza il rapporto valore quota / valore cespite", CA,
     "out[\"art25\"] += r[\"vps\"] * qv / r[\"valore\"] * rapporto", "out[\"art25\"] += r[\"vps\"] * rapporto"),
    ("calcolo: ISN senza sottrarre le riduzioni", CA, "isn = max(isl - rid, Fraction(0))", "isn = max(isl, Fraction(0))"),
    ("calcolo: candidato componente senza riduzioni", CA, "isn_c = max(isl_c - rid_c, Fraction(0))", "isn_c = max(isl_c, Fraction(0))"),
    ("componente: art. 25 a 2 decimali invece di 3", CA, "_half_up(_C_COMP_25[r[\"rid\"]] * base, 3)", "_half_up(_C_COMP_25[r[\"rid\"]] * base, 2)"),
    ("componente: rapporto art. 25 a 5 decimali invece di 6", CA, "r10, r6 = _half_up(isl / qe, 10), _half_up(isl / qe, 6)",
     "r10, r6 = _half_up(isl / qe, 10), _half_up(isl / qe, 5)"),
    ("componente: rapporto L/Q/R/F a 4 decimali invece di 10", CA, "r10, r6 = _half_up(isl / qe, 10),", "r10, r6 = _half_up(isl / qe, 4),"),
    ("componente: R oltre soglia senza arrotondamento a 2 decimali", CA,
     "                if a == \"R\":\n                    out[a] = _half_up(out[a], 2)", "                if a == \"R\":\n                    pass"),
    ("componente: R/F oltre soglia usa il valore della quota", CA,
     "out[a] += RA.SOGLIA_RF * r10 * _C_COMP_AGEV[a]", "out[a] += qv * r10 * _C_COMP_AGEV[a]"),
    ("calcolo: valore prec. succ. uguale al valore non ammesso", CA, "or _num(vps) > _num(valore):", "or _num(vps) >= _num(valore):"),
    ("calcolo: due righe R ammesse", CA, "            if n > 1:\n                motivi.append", "            if n > 5:\n                motivi.append"),
    ("export: valore prec. succ. uguale al valore non ammesso", RA, "if valore is None or int(s) > int(valore):", "if valore is None or int(s) >= int(valore):"),
    ("export: F ammesso anche nel quadro EB", RA, '"F": ("EC", "EM")}\n#: quadri supportati', '"F": ("EB", "EC", "EM")}\n#: quadri supportati'),
    ("export: grado 10 ammesso per F", RA, '"F": {"01", "02", "03", "04", "5A", "5B", "06", "7A", "7B"}',
     '"F": {"01", "02", "03", "04", "5A", "5B", "06", "7A", "7B", "10"}'),
    ("export: grado 21 ammesso per R", RA, '"9B", "10", "11"},\n         "F"', '"9B", "10", "11", "21"},\n         "F"'),
    ("export: esclusivita' sempre violata", RA, "            if cod - {c}:", "            if cod:"),
    ("export: dichiarante e non dichiarante scambiati", RA, "persona_dich = r[\"persona_id\"] == dich", "persona_dich = r[\"persona_id\"] != dich"),
    ("export: nessun allegato EG11 richiesto", RA, "                x.ra_eg = True", "                pass"),
    ("export: nessun allegato Altro per R", RA, "            x.ra_altro = True", "            pass"),
    ("export: Riduzioni non emesse nella devoluzione", ES, "                riga_dev[\"Riduzioni\"] = self.rid_dev[did]", "                pass"),
    ("export: protocollo L di 6 caratteri ammesso", RA, "if not 7 <= len(str(l[\"num_protocollo\"])) <= 16:", "if not 6 <= len(str(l[\"num_protocollo\"])) <= 16:"),
    ("export: Q ammesso nel quadro EC", RA, 'QUADRI_SUPPORTATI = {"L": ("EB", "EC", "EL", "EM"), "Q": ("EN", "EO"),',
     'QUADRI_SUPPORTATI = {"L": ("EB", "EC", "EL", "EM"), "Q": ("EC", "EN", "EO"),'),
    ("export: ValorePrecSucc senza controllo di positivita'", RA, "if len(s) > 13 or int(s) <= 0:", "if len(s) > 13:"),
]


def esegui(numero: int, desc: str, file: str, orig: str, nuovo: str, tmp: Path, reale: bool) -> str:
    dest = tmp / f"m{numero:02d}"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(RADICE / "src", dest / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    f = dest / file
    testo = f.read_text(encoding="utf-8")
    if testo.count(orig) != 1:
        return f"ERRORE: il testo originale compare {testo.count(orig)} volte in {file}"
    f.write_text(testo.replace(orig, nuovo, 1), encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(dest / "src"), str(RADICE / "tests")]), "TMP": str(tmp),
           "TEMP": str(tmp), "PYTHONDONTWRITEBYTECODE": "1"}
    if not reale:
        env.pop("SUCCESSIONI_JAVA", None)
        env.pop("SUCCESSIONI_CONTROLLI_SUC13", None)
    r = subprocess.run([sys.executable, "-m", "pytest", "tests/test_telematico_riduzioni_art25.py",
                        "tests/test_telematico_calcolo.py", "-x", "-q", "-p", "no:cacheprovider",
                        f"--basetemp={tmp / ('t%02d' % numero)}"], cwd=RADICE, env=env, capture_output=True, text=True)
    ultima = [r_ for r_ in r.stdout.strip().splitlines() if r_.strip()][-1:] or ["?"]
    return ("UCCISA" if r.returncode != 0 else "SOPRAVVISSUTA") + f" ({ultima[0]})"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reale", action="store_true")
    ap.add_argument("--tmp", default="C:/sx/mut")
    ap.add_argument("numeri", nargs="*", type=int)
    a = ap.parse_args()
    tmp = Path(a.tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    sopravvissute = 0
    for n, (desc, file, orig, nuovo) in enumerate(MUTAZIONI, 1):
        if a.numeri and n not in a.numeri:
            continue
        esito = esegui(n, desc, file, orig, nuovo, tmp, a.reale)
        print(f"{n:02d} {desc}: {esito}", flush=True)
        sopravvissute += esito.startswith(("SOPRAVVISSUTA", "ERRORE"))
    print(f"mutazioni: {len(MUTAZIONI) if not a.numeri else len(a.numeri)}, sopravvissute o errate: {sopravvissute}")
    return 1 if sopravvissute else 0


if __name__ == "__main__":
    raise SystemExit(main())
