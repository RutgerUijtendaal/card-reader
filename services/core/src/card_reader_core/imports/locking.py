from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from hashlib import sha256

from filelock import FileLock, Timeout

from card_reader_core.config.settings import settings


@contextmanager
def try_import_job_lock(job_id: str) -> Iterator[bool]:
    """Exclude live processing from recovery; the OS releases ownership on process exit."""
    directory = settings.storage_root_dir / "uploads" / ".parser-locks"
    directory.mkdir(parents=True, exist_ok=True)
    key = sha256(job_id.encode()).hexdigest()
    lock = FileLock(directory / f"{key}.lock")
    try:
        lock.acquire(timeout=0)
    except Timeout:
        yield False
        return
    try:
        yield True
    finally:
        # Let filelock manage its platform-specific descriptor and lock-file lifecycle.
        lock.release()
