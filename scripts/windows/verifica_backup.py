"""Verifica una copia (backup) o una cartella dati di Successioni, in sola lettura.

    python\\python.exe -s app\\verifica_backup.py <cartella>                 rapporto JSON
    python\\python.exe -s app\\verifica_backup.py <cartella> --confronta <altra cartella>

Controlla: integrita' SQLite (PRAGMA integrity_check), versione dello schema, pratiche/revisioni/allegati/job,
presenza e impronta SHA-256 di ogni allegato registrato e dei file citati dai job (XML esportati, artefatti).
`--confronta` confronta due cartelle (es. originale e ripristino): pratiche, revisioni, impronte dei dati, allegati.
Non apre l'archivio in scrittura e non crea file nella cartella verificata.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path, PureWindowsPath


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _rel(base: Path, percorso: str) -> Path:
    """I percorsi registrati su Windows possono contenere '\\': si normalizzano per poterli verificare ovunque."""
    if "\\" in percorso:
        return base.joinpath(*PureWindowsPath(percorso).parts)
    return base / percorso


def _descrittori(obj):
    """Descrittori di file {percorso, sha256} annidati nei risultati dei job."""
    if isinstance(obj, dict):
        if isinstance(obj.get("percorso"), str) and (obj.get("sha256") or obj.get("xml_sha256")):
            yield obj["percorso"], obj.get("sha256") or obj.get("xml_sha256")
        for v in obj.values():
            yield from _descrittori(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _descrittori(v)


def _apri_sola_lettura(db: Path) -> sqlite3.Connection:
    """Copia di backup (nessun -wal): immutable=1, nessun file creato. Cartella in uso (-wal presente): sola
    lettura ordinaria, che legge anche le modifiche ancora nel WAL."""
    wal = db.with_name(db.name + "-wal")
    opz = "mode=ro" if wal.exists() else "mode=ro&immutable=1"
    return sqlite3.connect(f"{db.resolve().as_uri()}?{opz}", uri=True)


def verifica(cartella: Path | str) -> dict:
    base = Path(cartella)
    db = base / "archivio.sqlite3"
    out = {"cartella": str(base), "esito": None, "problemi": []}
    if not db.exists():
        out["esito"] = "danneggiato"
        out["problemi"].append("archivio.sqlite3 assente")
        return out
    if (base / "archivio.sqlite3-wal").exists() and (base / "archivio.sqlite3-wal").stat().st_size > 0:
        out["problemi"].append("file -wal presente: e' una cartella dati in uso, non una copia; chiudere il programma "
                               "oppure usare 'successioni backup'")
    c = _apri_sola_lettura(db)
    c.row_factory = sqlite3.Row
    try:
        integ = [r[0] for r in c.execute("PRAGMA integrity_check")]
        out["integrita_db"] = "ok" if integ == ["ok"] else integ[:10]
        if integ != ["ok"]:
            out["problemi"].append("integrity_check non superato")
        out["schema"] = c.execute("PRAGMA user_version").fetchone()[0]
        pratiche = [dict(r) for r in c.execute("SELECT id, titolo, revisione, dati FROM pratiche ORDER BY id")]
        out["pratiche"] = [{"id": p["id"], "titolo": p["titolo"], "revisione": p["revisione"],
                            "sha256_dati": hashlib.sha256(p["dati"].encode()).hexdigest()} for p in pratiche]
        out["revisioni"] = c.execute("SELECT COUNT(*) FROM revisioni").fetchone()[0]
        rev_per = {r[0]: r[1] for r in c.execute("SELECT pratica_id, MAX(n) FROM revisioni GROUP BY pratica_id")}
        for p in pratiche:
            if rev_per.get(p["id"]) != p["revisione"]:
                out["problemi"].append(f"pratica {p['id']}: revisione {p['revisione']} senza voce in cronologia")
        allegati = [dict(r) for r in c.execute("SELECT id, pratica_id, nome, sha256, bytes, percorso, ruolo FROM allegati "
                                               "ORDER BY id")]
        mancanti, alterati, win = [], [], 0
        for a in allegati:
            win += "\\" in a["percorso"]
            f = _rel(base, a["percorso"])
            if not f.exists():
                mancanti.append(a["percorso"])
            elif sha256_file(f) != a["sha256"]:
                alterati.append(a["percorso"])
        out["allegati"] = {"righe": len(allegati), "file_verificati": len(allegati) - len(mancanti) - len(alterati),
                           "mancanti": mancanti, "alterati": alterati, "percorsi_con_backslash": win,
                           "elenco": [{k: a[k] for k in ("id", "pratica_id", "nome", "sha256", "ruolo")} for a in allegati]}
        job_file = {"citati": 0, "mancanti": [], "alterati": []}
        for r in c.execute("SELECT id, tipo, risultato FROM job"):
            try:
                ris = json.loads(r["risultato"] or "{}")
            except ValueError:
                continue
            for perc, h in _descrittori(ris):
                job_file["citati"] += 1
                f = _rel(base, perc)
                if not f.exists():
                    job_file["mancanti"].append(f"{r['tipo']}: {perc}")
                elif sha256_file(f) != h:
                    job_file["alterati"].append(f"{r['tipo']}: {perc}")
        out["file_dei_job"] = job_file
        out["job"] = c.execute("SELECT COUNT(*) FROM job").fetchone()[0]
    finally:
        c.close()
    if mancanti or alterati:
        out["problemi"].append(f"allegati mancanti {len(mancanti)}, alterati {len(alterati)}")
    if job_file["mancanti"] or job_file["alterati"]:
        out["problemi"].append(f"file dei job (XML esportati, diagnostici) mancanti {len(job_file['mancanti'])}, "
                               f"alterati {len(job_file['alterati'])}")
    if out.get("integrita_db") != "ok" or alterati:
        out["esito"] = "danneggiato"
    elif mancanti or job_file["mancanti"] or job_file["alterati"]:
        out["esito"] = "incompleto"
    else:
        out["esito"] = "integro"
    return out


def confronta(a: dict, b: dict) -> list[str]:
    diff = []
    for chiave in ("schema", "revisioni", "job"):
        if a.get(chiave) != b.get(chiave):
            diff.append(f"{chiave}: {a.get(chiave)} != {b.get(chiave)}")
    if a.get("pratiche") != b.get("pratiche"):
        diff.append("pratiche (id, titolo, revisione o dati) diverse")
    if (a.get("allegati") or {}).get("elenco") != (b.get("allegati") or {}).get("elenco"):
        diff.append("elenco allegati diverso")
    return diff


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="verifica_backup")
    ap.add_argument("cartella")
    ap.add_argument("--confronta", metavar="ALTRA")
    a = ap.parse_args(argv)
    r = verifica(a.cartella)
    if a.confronta:
        r2 = verifica(a.confronta)
        r = {"prima": r, "seconda": r2, "differenze": confronta(r, r2)}
        print(json.dumps(r, indent=1, ensure_ascii=False))
        return 1 if r["differenze"] or r["prima"]["esito"] == "danneggiato" or r["seconda"]["esito"] == "danneggiato" else 0
    print(json.dumps(r, indent=1, ensure_ascii=False))
    return 0 if r["esito"] == "integro" else 1


if __name__ == "__main__":
    sys.exit(main())
