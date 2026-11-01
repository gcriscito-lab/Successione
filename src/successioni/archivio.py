"""Archivio unico: SQLite (WAL) + allegati content-addressed nella stessa cartella dati.

Piu' processi (GUI, server MCP) aprono lo STESSO file: stato, revisioni e job vivono qui,
non nel processo del client. Ogni scrittura e' una transazione IMMEDIATE.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA_VERSIONE = 1

DDL = """
CREATE TABLE pratiche(
  id TEXT PRIMARY KEY, titolo TEXT NOT NULL, creata TEXT NOT NULL, aggiornata TEXT NOT NULL,
  revisione INTEGER NOT NULL, dati TEXT NOT NULL);
CREATE TABLE revisioni(
  pratica_id TEXT NOT NULL REFERENCES pratiche(id), n INTEGER NOT NULL, ts TEXT NOT NULL,
  autore TEXT NOT NULL, canale TEXT NOT NULL, chiave TEXT, sommario TEXT NOT NULL, dati TEXT NOT NULL,
  PRIMARY KEY(pratica_id, n));
CREATE TABLE richieste(
  chiave TEXT PRIMARY KEY, pratica_id TEXT, operazione TEXT NOT NULL, impronta TEXT NOT NULL,
  risposta TEXT NOT NULL, ts TEXT NOT NULL);
CREATE TABLE allegati(
  id TEXT PRIMARY KEY, pratica_id TEXT NOT NULL REFERENCES pratiche(id), nome TEXT NOT NULL,
  sha256 TEXT NOT NULL, bytes INTEGER NOT NULL, percorso TEXT NOT NULL,
  ruolo TEXT NOT NULL CHECK(ruolo IN ('originale','derivato')), origine_id TEXT,
  tipo_eg TEXT, finalita TEXT, persona_id TEXT, analisi TEXT, rapporto TEXT, ts TEXT NOT NULL);
CREATE TABLE job(
  id TEXT PRIMARY KEY, tipo TEXT NOT NULL, pratica_id TEXT, stato TEXT NOT NULL,
  input TEXT, risultato TEXT, errore TEXT, creato TEXT NOT NULL, aggiornato TEXT NOT NULL);
"""


def cartella_dati() -> Path:
    env = os.environ.get("SUCCESSIONI_DATA")
    if env:
        return Path(env)
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Successioni"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "successioni"


class Archivio:
    def __init__(self, base: Path | str | None = None):
        self.base = Path(base) if base else cartella_dati()
        self.base.mkdir(parents=True, exist_ok=True)
        (self.base / "allegati").mkdir(exist_ok=True)
        self.db_path = self.base / "archivio.sqlite3"
        self._migra()

    def _apri(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA busy_timeout=10000")
        return c

    def _migra(self):
        c = self._apri()
        try:
            v = c.execute("PRAGMA user_version").fetchone()[0]
            if v == 0:
                c.execute("BEGIN IMMEDIATE")
                for stmt in filter(None, (s.strip() for s in DDL.split(";"))):
                    c.execute(stmt)
                c.execute(f"PRAGMA user_version={SCHEMA_VERSIONE}")
                c.execute("COMMIT")
            elif v > SCHEMA_VERSIONE:
                raise RuntimeError(f"archivio creato da una versione piu' recente (schema {v})")
        finally:
            c.close()

    @contextmanager
    def lettura(self):
        c = self._apri()
        try:
            yield c
        finally:
            c.close()

    @contextmanager
    def transazione(self):
        """Scrittura atomica: tutto o niente."""
        c = self._apri()
        try:
            c.execute("BEGIN IMMEDIATE")
            try:
                yield c
            except BaseException:
                c.execute("ROLLBACK")
                raise
            else:
                c.execute("COMMIT")
        finally:
            c.close()

    def percorso_allegato(self, sha256: str) -> Path:
        d = self.base / "allegati" / sha256[:2]
        d.mkdir(parents=True, exist_ok=True)
        return d / sha256

    def backup(self, destinazione: Path | str) -> Path:
        """Copia coerente di database + allegati in una cartella (database via API di backup SQLite)."""
        import shutil
        dest = Path(destinazione)
        dest.mkdir(parents=True, exist_ok=True)
        src = self._apri()
        try:
            out = sqlite3.connect(dest / "archivio.sqlite3")
            try:
                src.backup(out)
            finally:
                out.close()
        finally:
            src.close()
        for cart in ("allegati", "elaborati"):          # file elaborati inclusi: lo stato dell'export li richiama
            if (self.base / cart).exists():
                shutil.copytree(self.base / cart, dest / cart, dirs_exist_ok=True)
        return dest

    def e_vuoto(self) -> bool:
        with self.lettura() as c:
            if c.execute("SELECT COUNT(*) FROM pratiche").fetchone()[0]:
                return False
        return not any(p.is_file() for cart in ("allegati", "elaborati") if (self.base / cart).exists()
                       for p in (self.base / cart).rglob("*"))

    def ripristina(self, sorgente: Path | str) -> None:
        """Ripristina un backup (database, allegati, elaborati) in questo archivio, che DEVE essere vuoto.

        Non sovrascrive mai dati esistenti: per ripristinare su un archivio in uso, usare una cartella dati nuova."""
        import shutil
        from .errori import RipristinoNonAmmesso
        sorg = Path(sorgente)
        if not (sorg / "archivio.sqlite3").is_file():
            raise RipristinoNonAmmesso("la cartella indicata non contiene un backup (manca archivio.sqlite3)", sorgente=str(sorg))
        if not self.e_vuoto():
            raise RipristinoNonAmmesso("l'archivio di destinazione contiene gia' dati: ripristina in una cartella dati nuova", destinazione=str(self.base))
        src = sqlite3.connect(sorg / "archivio.sqlite3")
        try:
            versione = src.execute("PRAGMA user_version").fetchone()[0]
            if versione > SCHEMA_VERSIONE:
                raise RipristinoNonAmmesso(f"il backup proviene da una versione piu' recente (schema {versione})")
            dst = self._apri()
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()
        for cart in ("allegati", "elaborati"):
            if (sorg / cart).exists():
                shutil.copytree(sorg / cart, self.base / cart, dirs_exist_ok=True)
