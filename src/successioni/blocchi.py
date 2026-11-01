"""Lock di processo rilasciato dal sistema anche in caso di arresto improvviso."""
from contextlib import contextmanager
import os


@contextmanager
def blocco_file(percorso):
    """Restituisce False se un altro esecutore possiede il lock; non attende."""
    percorso.parent.mkdir(parents=True, exist_ok=True)
    with percorso.open('a+b') as f:
        if f.seek(0, os.SEEK_END) == 0:
            f.write(b'0')
            f.flush()
        f.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            yield False
            return
        try:
            yield True
        finally:
            f.seek(0)
            if os.name == 'nt':
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f, fcntl.LOCK_UN)
