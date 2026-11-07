"""Archivio unico: SQLite (WAL) + allegati content-addressed nella stessa cartella dati.

Piu' processi (GUI, server MCP) aprono lo STESSO file: stato, revisioni e job vivono qui,
non nel processo del client. Ogni scrittura e' una transazione IMMEDIATE.
"""
from __future__ import annotations

import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

SCHEMA_VERSIONE = 1
NOME_CONFIGURAZIONE = "configurazione.json"

DDL = """
CREATE TABLE IF NOT EXISTS pratiche(
  id TEXT PRIMARY KEY, titolo TEXT NOT NULL, creata TEXT NOT NULL, aggiornata TEXT NOT NULL,
  revisione INTEGER NOT NULL, dati TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS revisioni(
  pratica_id TEXT NOT NULL REFERENCES pratiche(id), n INTEGER NOT NULL, ts TEXT NOT NULL,
  autore TEXT NOT NULL, canale TEXT NOT NULL, chiave TEXT, sommario TEXT NOT NULL, dati TEXT NOT NULL,
  PRIMARY KEY(pratica_id, n));
CREATE TABLE IF NOT EXISTS richieste(
  chiave TEXT PRIMARY KEY, pratica_id TEXT, operazione TEXT NOT NULL, impronta TEXT NOT NULL,
  risposta TEXT NOT NULL, ts TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS allegati(
  id TEXT PRIMARY KEY, pratica_id TEXT NOT NULL REFERENCES pratiche(id), nome TEXT NOT NULL,
  sha256 TEXT NOT NULL, bytes INTEGER NOT NULL, percorso TEXT NOT NULL,
  ruolo TEXT NOT NULL CHECK(ruolo IN ('originale','derivato')), origine_id TEXT,
  tipo_eg TEXT, finalita TEXT, persona_id TEXT, analisi TEXT, rapporto TEXT, ts TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS job(
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
        # Il passaggio a WAL di un file nuovo puo' restituire "database is locked" senza attendere il busy_timeout se un
        # altro processo (GUI e MCP avviati insieme) lo sta facendo nello stesso istante: si riprova per un tempo limitato.
        for tentativo in range(100):
            try:
                c.execute("PRAGMA journal_mode=WAL")
                break
            except sqlite3.OperationalError as e:
                if "locked" not in str(e) or tentativo == 99:
                    c.close()
                    raise
                time.sleep(0.05)
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA busy_timeout=10000")
        return c

    def _migra(self):
        """Crea lo schema se manca. GUI e server MCP possono partire insieme su un archivio nuovo: la versione si rilegge
        DENTRO la transazione IMMEDIATE (chi arriva secondo aspetta il lock e trova lo schema gia' creato) e le tabelle
        si creano con IF NOT EXISTS."""
        c = self._apri()
        try:
            if c.execute("PRAGMA user_version").fetchone()[0] == 0:
                c.execute("BEGIN IMMEDIATE")
                try:
                    if c.execute("PRAGMA user_version").fetchone()[0] == 0:
                        for stmt in filter(None, (s.strip() for s in DDL.split(";"))):
                            c.execute(stmt)
                        c.execute(f"PRAGMA user_version={SCHEMA_VERSIONE}")
                except BaseException:
                    c.execute("ROLLBACK")
                    raise
                c.execute("COMMIT")
            v = c.execute("PRAGMA user_version").fetchone()[0]
            if v > SCHEMA_VERSIONE:
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
        self._copia_configurazione(dest)
        return dest

    def _copia_configurazione(self, dest: Path) -> str:
        """Copia nel backup ``configurazione.json`` (profilo dello studio, preferenze come la sola lettura di Claude, aspetto,
        percorsi degli strumenti), FILTRATA con ``impostazioni.VOCI_BACKUP``: le chiavi non note e SUCCESSIONI_DATA restano
        fuori. Il file non contiene credenziali (``impostazioni.salva`` rifiuta chiavi non elencate); il filtro protegge
        anche da chiavi scritte a mano. Un file illeggibile non blocca il backup: si salta."""
        import json
        from . import impostazioni
        f = impostazioni.percorso_configurazione(self.base)
        if not f.is_file():
            return "assente"
        try:
            filtrato = impostazioni.contenuto_per_backup(json.loads(f.read_text(encoding="utf-8-sig")))
        except (OSError, ValueError):
            filtrato = None
        if filtrato is None:
            return "non_valida"
        (dest / NOME_CONFIGURAZIONE).write_text(json.dumps(filtrato, ensure_ascii=False, indent=2), encoding="utf-8")
        return "copiata"

    def e_vuoto(self) -> bool:
        with self.lettura() as c:
            for tabella in ('pratiche', 'revisioni', 'richieste', 'allegati', 'job'):
                if c.execute(f"SELECT COUNT(*) FROM {tabella}").fetchone()[0]:
                    return False
        return not any(p.is_file() for cart in ("allegati", "elaborati") if (self.base / cart).exists()
                       for p in (self.base / cart).rglob("*"))

    def ripristina(self, sorgente: Path | str) -> dict:
        """Ripristina un backup (database, allegati, elaborati, configurazione) in questo archivio, che DEVE essere vuoto.

        Non sovrascrive mai dati esistenti: per ripristinare su un archivio in uso, usare una cartella dati nuova. La
        destinazione puo' contenere solo le voci che il programma crea da solo (``VOCI_AUTOMATICHE``, cartelle senza file).
        La configurazione del backup va in ``<destinazione>/configurazione.json``, salvo che ne esista gia' una (conservata).
        Se il programma usa un file indicato da SUCCESSIONI_CONFIG (avviatore Windows), quello non viene toccato: la copia
        ripristinata resta nella cartella dati come riferimento. Esito: ``{'configurazione': assente | ripristinata |
        conservata_destinazione | non_valida_ignorata}``."""
        import shutil
        import tempfile
        from .errori import RipristinoNonAmmesso
        from .integrita import verifica_copia
        sorg = Path(sorgente).resolve()
        esito = {'configurazione': 'assente'}
        if not (sorg / "archivio.sqlite3").is_file():
            raise RipristinoNonAmmesso("la cartella indicata non contiene un backup (manca archivio.sqlite3)", sorgente=str(sorg))
        if not self.e_vuoto():
            raise RipristinoNonAmmesso("l'archivio di destinazione contiene gia' dati: ripristina in una cartella dati nuova", destinazione=str(self.base))
        estranei = self._estranei()
        if estranei:
            raise RipristinoNonAmmesso('la destinazione contiene altri file o cartelle: usare una cartella dati nuova',
                                       voci=estranei)
        try:
            verifica_copia(sorg, SCHEMA_VERSIONE)
            base = self.base.resolve()
            # Tutti i target della preparazione e degli spostamenti sono figli del
            # medesimo parent esplicitamente risolto (anche su Windows).
            parent = base.parent
            with tempfile.TemporaryDirectory(prefix='.successioni-ripristino-', dir=parent) as tmp:
                stage = Path(tmp).resolve() / 'dati'
                precedente = Path(tmp).resolve() / 'precedente-vuoto'
                if not stage.is_relative_to(parent) or not precedente.is_relative_to(parent) or base == parent:
                    raise RipristinoNonAmmesso('destinazione di ripristino non valida')
                stage.mkdir()
                shutil.copyfile(sorg / 'archivio.sqlite3', stage / 'archivio.sqlite3')
                for cart in ('allegati', 'elaborati'):
                    if (sorg / cart).exists():
                        shutil.copytree(sorg / cart, stage / cart)
                verifica_copia(stage, SCHEMA_VERSIONE)
                if not self.e_vuoto():
                    raise RipristinoNonAmmesso('la destinazione e’ stata popolata durante la preparazione')
                if self._estranei():
                    raise RipristinoNonAmmesso('altri file aggiunti alla destinazione durante la preparazione')
                # configurazione: si conserva quella gia' presente nella destinazione (mai sovrascritta); altrimenti si
                # ripristina quella del backup, rifiltrata
                if (base / NOME_CONFIGURAZIONE).is_file():
                    shutil.copyfile(base / NOME_CONFIGURAZIONE, stage / NOME_CONFIGURAZIONE)
                    esito['configurazione'] = 'conservata_destinazione'
                elif (sorg / NOME_CONFIGURAZIONE).is_file():
                    esito['configurazione'] = self._ripristina_configurazione(sorg / NOME_CONFIGURAZIONE,
                                                                              stage / NOME_CONFIGURAZIONE)
                if (base / 'ingresso').is_dir():
                    (stage / 'ingresso').mkdir(exist_ok=True)
                # Il ripristino richiede una destinazione nuova, senza client aperti.
                # Se la preparazione fallisce, il database originale non e' mai toccato.
                base.rename(precedente)
                try:
                    stage.rename(base)
                except BaseException:
                    precedente.rename(base)
                    raise
        except (OSError, ValueError, sqlite3.Error) as e:
            raise RipristinoNonAmmesso(f'backup non ripristinato: {e}') from e
        return esito

    #: voci create da sole dal programma, ammesse nella destinazione di un ripristino: ``allegati``/``elaborati`` e
    #: ``ingresso`` solo se senza file (``e_vuoto`` e ``_estranei`` lo controllano); ``configurazione.json`` (impostazioni
    #: salvate nella nuova cartella) e' ammessa e viene conservata.
    VOCI_AUTOMATICHE = frozenset({'archivio.sqlite3', 'archivio.sqlite3-wal', 'archivio.sqlite3-shm', 'allegati',
                                  'elaborati', 'ingresso', NOME_CONFIGURAZIONE})

    def _estranei(self) -> list[str]:
        """Voci della cartella dati che impediscono il ripristino (vuoto = nessuna)."""
        out = []
        for p in self.base.iterdir():
            if p.name not in self.VOCI_AUTOMATICHE:
                out.append(p.name)
            elif p.name == 'ingresso' and (not p.is_dir() or any(x.is_file() for x in p.rglob('*'))):
                out.append(p.name)
            elif p.name == NOME_CONFIGURAZIONE and not p.is_file():
                out.append(p.name)
        return out

    @staticmethod
    def _ripristina_configurazione(sorgente: Path, dest: Path) -> str:
        import json
        from . import impostazioni
        try:
            filtrato = impostazioni.contenuto_per_backup(json.loads(sorgente.read_text(encoding='utf-8-sig')))
        except (OSError, ValueError):
            filtrato = None
        if filtrato is None:
            return 'non_valida_ignorata'
        dest.write_text(json.dumps(filtrato, ensure_ascii=False, indent=2), encoding='utf-8')
        return 'ripristinata'
