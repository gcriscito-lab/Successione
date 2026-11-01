"""Verifica di una copia chiusa dell'archivio, senza modificarla (solo stdlib)."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path, PurePosixPath


def descrittori(obj):
    if isinstance(obj, dict):
        if isinstance(obj.get('percorso'), str) and (obj.get('sha256') or obj.get('xml_sha256')):
            yield obj['percorso'], obj.get('sha256') or obj['xml_sha256'], obj.get('bytes')
        for v in obj.values():
            yield from descrittori(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from descrittori(v)


def verifica_copia(base: Path, versione: int) -> None:
    """Solleva ValueError se DB, riferimenti o byte non formano un archivio integro."""
    base = base.resolve()
    db = base / 'archivio.sqlite3'
    wal = base / 'archivio.sqlite3-wal'
    if wal.exists() and wal.stat().st_size:
        raise ValueError('la sorgente contiene un WAL attivo: creare un backup con il comando dedicato')
    c = sqlite3.connect(db.as_uri() + '?mode=ro&immutable=1', uri=True)
    try:
        if c.execute('PRAGMA user_version').fetchone()[0] != versione:
            raise ValueError('versione dello schema del backup non compatibile')
        if c.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise ValueError('integrita SQLite non superata')
        if c.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('riferimenti del database non integri')
        # Verifica anche che siano presenti le tabelle attese, non soltanto user_version.
        for nome in ('pratiche', 'revisioni', 'richieste', 'job', 'allegati'):
            c.execute(f'SELECT COUNT(*) FROM {nome}').fetchone()
        refs = list(c.execute('SELECT percorso,sha256,bytes FROM allegati'))
        for (risultato,) in c.execute('SELECT risultato FROM job'):
            refs.extend(descrittori(json.loads(risultato or '{}')))
        for percorso, atteso, dimensione in refs:
            rel = PurePosixPath(percorso.replace('\\', '/'))
            if rel.is_absolute() or '..' in rel.parts or not rel.parts or rel.parts[0] not in ('allegati', 'elaborati'):
                raise ValueError('percorso di documento fuori dall’archivio')
            p = base.joinpath(*rel.parts).resolve()
            if not p.is_relative_to(base) or not p.is_file():
                raise ValueError(f'documento mancante nel backup: {percorso}')
            if dimensione is not None and p.stat().st_size != dimensione:
                raise ValueError(f'dimensione del documento alterata: {percorso}')
            with p.open('rb') as f:
                h = hashlib.file_digest(f, 'sha256').hexdigest()
            if h != atteso:
                raise ValueError(f'impronta del documento alterata: {percorso}')
    finally:
        c.close()
