from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import sqlite3
import time

from django.db import connection


@contextmanager
def monitoring_reads() -> Iterator[None]:
    """Bound diagnostic reads without changing the application's normal lock policy."""
    connection.ensure_connection()
    raw = connection.connection
    if not isinstance(raw, sqlite3.Connection):
        raise RuntimeError("Monitoring requires the configured SQLite backend.")
    previous_timeout = raw.execute("PRAGMA busy_timeout").fetchone()[0]
    previous_readonly = raw.execute("PRAGMA query_only").fetchone()[0]
    deadline = time.monotonic() + 3.0
    raw.execute("PRAGMA busy_timeout=500")
    raw.execute("PRAGMA query_only=ON")
    raw.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
    try:
        yield
    finally:
        raw.set_progress_handler(None, 0)
        raw.execute(f"PRAGMA query_only={int(previous_readonly)}")
        raw.execute(f"PRAGMA busy_timeout={int(previous_timeout)}")
